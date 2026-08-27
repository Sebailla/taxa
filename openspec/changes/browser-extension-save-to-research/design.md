# Design: Browser Extension — Send to Research

## Architecture

The extension is a 3-component system that talks to one new backend endpoint. The boundaries are deliberately small: the extension is a thin client, the backend is the source of truth, and taxa's existing web client stays untouched.

```
┌──────────────────────────────────────────────────────────────────────┐
│ Browser (Chrome / Firefox)                                            │
│                                                                       │
│  ┌──────────────────┐    ┌──────────────────┐    ┌────────────────┐   │
│  │  content.js      │    │  background.js   │    │  popup.html    │   │
│  │  (taxa tab only) │    │  (service worker)│    │  (optional)    │   │
│  │                  │    │                  │    │                │   │
│  │ - watches        │    │ - context menu   │    │ - status badge │   │
│  │   [data-taxon-id]│───▶│ - storage sync   │    │ - last-saved   │   │
│  │   click events   │    │ - POST to taxa   │    │   path         │   │
│  │ - debounced 250ms│    │ - notifications  │    │                │   │
│  │                  │    │                  │    │                │   │
│  └──────────────────┘    └────────┬─────────┘    └────────────────┘   │
│         │                        │                                    │
│         │ chrome.storage.local   │ chrome.notifications               │
│         ▼                        ▼                                    │
│  ┌──────────────────┐    ┌──────────────────┐                          │
│  │ currentTaxon:    │    │ fetch() to       │                          │
│  │  {id, sci_name}  │    │ localhost:8765   │                          │
│  └──────────────────┘    └────────┬─────────┘                          │
└────────────────────────────────────┼──────────────────────────────────┘
                                     │
                                     ▼ HTTP
┌──────────────────────────────────────────────────────────────────────┐
│ taxa (FastAPI)                                                        │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ POST /api/taxon/{id}/save-url?source=col|worms|freshwater      │ │
│  │   body: {url, suggested_filename}                              │ │
│  │                                                                │ │
│  │   1. validate URL (scheme + private-IP reject)                 │ │
│  │   2. resolve Research/<chain>/ via _build_segments             │ │
│  │   3. require target_dir exists (else 404)                       │ │
│  │   4. stream GET origin (30s/60s, 50MB cap)                      │ │
│  │   5. validate Content-Type (allowlist, else 415)                 │ │
│  │   6. sanitize filename + append __<taxon_id>                    │ │
│  │   7. handle collision (append __<timestamp>)                   │ │
│  │   8. write to disk                                              │ │
│  │   9. log {taxon_id, source, url, content_type, size, status}   │ │
│  │  10. return {ok, absolute_path, size, content_type}             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  Uses:                                                                │
│   - urllib.request (no new dep; same as existing code)               │
│   - socket.getaddrinfo (for SSRF check on resolved IP)               │
│   - pathlib (already imported)                                        │
│   - logging (already imported)                                        │
└──────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼ writes to
                          ./Research/<chain>/<file>__<id>.<ext>
```

## Component breakdown

### 1. Extension (`extension/`)

#### 1.1 `manifest.json`

```json
{
  "manifest_version": 3,
  "name": "taxa: Save to Research",
  "version": "0.1.0",
  "description": "Right-click → 'Send to taxa' to save a URL's content into the active taxon's Research folder.",
  "permissions": ["activeTab", "contextMenus", "storage", "scripting", "notifications"],
  "host_permissions": ["http://localhost:8765/*"],
  "background": { "service_worker": "background.js" },
  "content_scripts": [{
    "matches": ["http://localhost:8765/*"],
    "js": ["content.js"],
    "run_at": "document_idle"
  }],
  "action": {
    "default_popup": "popup.html",
    "default_title": "Send current tab to taxa",
    "default_icon": {
      "16": "icons/icon-16.png",
      "48": "icons/icon-48.png",
      "128": "icons/icon-128.png"
    }
  },
  "icons": {
    "16": "icons/icon-16.png",
    "48": "icons/icon-48.png",
    "128": "icons/icon-128.png"
  }
}
```

No `web_accessible_resources` (we don't expose anything to the page). No `content_security_policy` overrides.

#### 1.2 `content.js` (~80 lines)

Responsibilities:

- Inject into every `localhost:8765/*` page on `document_idle`.
- Listen for clicks on `[data-taxon-id]` rows (delegated on `document.body`).
- Extract `{id, scientific_name}` from the closest `[data-taxon-id]` attribute and the row's name span.
- Debounce 250 ms before writing to `chrome.storage.local`.
- Listen for `taxa`'s custom event `taxa:taxon-selected` (preferred path) if `taxa` ever adds one. v1 ships with the click-listener fallback only.

Pseudocode:

```js
let writeTimer = null;
let pending = null;

function schedule(payload) {
  pending = payload;
  if (writeTimer) return;
  writeTimer = setTimeout(() => {
    chrome.storage.local.set({ currentTaxon: pending });
    writeTimer = null;
  }, 250);
}

document.body.addEventListener("click", (e) => {
  const row = e.target.closest("[data-taxon-id]");
  if (!row) return;
  const id = parseInt(row.getAttribute("data-taxon-id"), 10);
  const nameEl = row.querySelector("[data-taxon-name], .scientific-name, .taxon-name");
  if (!Number.isFinite(id) || !nameEl) return;
  schedule({ id, scientific_name: nameEl.textContent.trim(), capturedAt: Date.now() });
});
```

#### 1.3 `background.js` (~150 lines)

Responsibilities:

- Register the context menu on `chrome.runtime.onInstalled` and `chrome.runtime.onStartup`.
- Listen to `chrome.storage.onChanged` and update the context menu title + enabled state.
- On `chrome.contextMenus.onClicked`, dispatch the save request.
- POST to `http://localhost:8765/api/taxon/<id>/save-url`.
- Show a `chrome.notifications` notification with the result.
- Update the toolbar badge with a check / X icon briefly.

Pseudocode:

```js
const TAXA_BASE = "http://localhost:8765";
const MENU_ID = "send-to-taxa";

async function refreshMenu(currentTaxon) {
  const title = currentTaxon
    ? `Send to taxa: ${currentTaxon.scientific_name}`
    : "Send to taxa: (no taxon selected — open taxa and click a row)";
  await chrome.contextMenus.update(MENU_ID, {
    title,
    enabled: !!currentTaxon,
  });
}

chrome.runtime.onInstalled.addListener(async () => {
  await chrome.contextMenus.create({
    id: MENU_ID,
    title: "Send to taxa: (no taxon selected)",
    contexts: ["link", "page", "image", "video", "audio"],
  });
  const { currentTaxon } = await chrome.storage.local.get("currentTaxon");
  await refreshMenu(currentTaxon);
});

chrome.storage.onChanged.addListener((changes) => {
  if (changes.currentTaxon) refreshMenu(changes.currentTaxon.newValue);
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const { currentTaxon } = await chrome.storage.local.get("currentTaxon");
  if (!currentTaxon) {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon-48.png",
      title: "taxa: no taxon selected",
      message: "Open taxa and select a taxon first.",
    });
    return;
  }

  const url = info.linkUrl || info.srcUrl || info.pageUrl || tab.url;
  const suggested = info.linkText || tab.title || url.split("/").pop() || "download";

  try {
    const r = await fetch(`${TAXA_BASE}/api/taxon/${currentTaxon.id}/save-url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, suggested_filename: suggested }),
    });
    const body = await r.json();
    if (r.ok) {
      chrome.notifications.create({
        type: "basic",
        iconUrl: "icons/icon-48.png",
        title: `Saved to ${currentTaxon.scientific_name}`,
        message: `${body.absolute_path}\n(${formatSize(body.size)}, ${body.content_type})`,
      });
      chrome.action.setBadgeText({ text: "✓" });
      chrome.action.setBadgeBackgroundColor({ color: "#15803d" });
      setTimeout(() => chrome.action.setBadgeText({ text: "" }), 3000);
    } else {
      chrome.notifications.create({
        type: "basic",
        iconUrl: "icons/icon-48.png",
        title: "Cannot save",
        message: humanizeError(r.status, body.detail),
      });
      chrome.action.setBadgeText({ text: "✗" });
      chrome.action.setBadgeBackgroundColor({ color: "#b91c1c" });
      setTimeout(() => chrome.action.setBadgeText({ text: "" }), 3000);
    }
  } catch (err) {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon-48.png",
      title: "Cannot save",
      message: `taxa is not running at ${TAXA_BASE}.`,
    });
  }
});

function humanizeError(status, detail) {
  if (status === 400) return `URL rejected: ${detail}`;
  if (status === 404) return `Folder not materialized: ${detail}`;
  if (status === 413) return `File too large: ${detail}`;
  if (status === 415) return `File type rejected: ${detail}`;
  if (status === 502) return `Source returned an error: ${detail}`;
  return `Error ${status}: ${detail || "unknown"}`;
}
```

#### 1.4 `popup.html` + `popup.js` (~50 lines combined)

Optional but useful: shows the last-saved path, the current taxon, and a "Test connection" button. Trivial implementation. v1 may ship without it and add later.

#### 1.5 `icons/icon-{16,48,128}.png`

Placeholder PNGs (we'll generate solid color squares with the letters "tx"). Production-quality icons are a follow-up.

#### 1.6 `README.md`

Install instructions, screenshots, FAQ, known limitations.

### 2. Backend (`api/server.py` additions)

#### 2.1 New helpers

```python
# Add to api/server.py imports
import ipaddress
import socket
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Module-level constants near the other config
_SAVE_URL_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
_SAVE_URL_CONNECT_TIMEOUT = 30  # seconds
_SAVE_URL_READ_TIMEOUT = 60  # seconds
_SAVE_URL_ALLOWED_TYPES = frozenset({
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/svg+xml",
    "text/html",
    "text/plain",
    "application/json",
    "application/octet-stream",
})
_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]
```

#### 2.2 `_is_private_or_reserved_ip(hostname) -> bool`

```python
def _is_private_or_reserved_ip(hostname: str) -> bool:
    """Resolve hostname (literal or DNS) and return True if any of the
    resolved IPs falls in a private or reserved range.

    DNS rebinding defense: we resolve once, and the actual fetch below
    uses the resolved IP directly (not the hostname) so a subsequent
    re-resolve to a public IP cannot smuggle a request past the check.
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return True  # treat unresolvable as "private" (fail closed)
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return True
        for net in _PRIVATE_NETS:
            if ip in net:
                return True
    return False
```

#### 2.3 `_sanitize_filename(name: str) -> str`

```python
def _sanitize_filename(name: str) -> str:
    """Take the last path segment, replace any char outside [A-Za-z0-9._-]
    with _, drop leading dots, fall back to a timestamped name if empty.
    """
    if not name:
        return ""
    # last segment only
    name = name.replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    cleaned = cleaned.lstrip(".")
    if not cleaned or cleaned in {".", ".."}:
        return ""
    return cleaned
```

#### 2.4 `_save_url_to_research(target_dir, url, suggested_filename, taxon_id) -> dict

Returns `{absolute_path, size, content_type}` or raises HTTPException.

```python
def _save_url_to_research(
    target_dir: Path, url: str, suggested_filename: str, taxon_id: int,
) -> dict:
    # 1. Validate scheme
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, f"unsupported scheme: {parsed.scheme!r}")
    if not parsed.hostname:
        raise HTTPException(400, "URL has no host")

    # 2. SSRF check
    if _is_private_or_reserved_ip(parsed.hostname):
        raise HTTPException(400, "URL points to a private or reserved network range")

    # 3. Fetch with timeouts + size cap
    req = Request(url, headers={"User-Agent": "taxa-save-url/0.1"})
    try:
        with urlopen(req, timeout=_SAVE_URL_CONNECT_TIMEOUT) as resp:
            content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if content_type not in _SAVE_URL_ALLOWED_TYPES:
                raise HTTPException(415, f"Content-Type not in allowlist: {content_type!r}")

            # Compute safe filename
            ext = mimetypes.guess_extension(content_type) or ""
            ext = ext.lstrip(".")
            base = _sanitize_filename(suggested_filename) or "download"
            base_with_id = f"{base}__{taxon_id}"
            candidate = target_dir / f"{base_with_id}{('.' + ext) if ext else ''}"

            if candidate.exists():
                ts = int(time.time())
                candidate = target_dir / f"{base_with_id}__{ts}{('.' + ext) if ext else ''}"

            # Stream with size cap
            total = 0
            with candidate.open("wb") as f:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > _SAVE_URL_MAX_BYTES:
                        f.close()
                        candidate.unlink(missing_ok=True)
                        raise HTTPException(413, f"Response exceeds {_SAVE_URL_MAX_BYTES // (1024*1024)} MB cap")
                    f.write(chunk)

            return {
                "absolute_path": str(candidate.resolve()),
                "size": total,
                "content_type": content_type,
            }
    except HTTPError as e:
        # Origin returned 4xx/5xx
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise HTTPException(502, f"Origin returned {e.code} — {detail}")
    except URLError as e:
        raise HTTPException(502, f"Could not reach origin: {e.reason}")
    except socket.timeout:
        raise HTTPException(504, f"Origin timed out after {_SAVE_URL_READ_TIMEOUT}s")
```

#### 2.5 New endpoint

```python
class SaveUrlRequest(BaseModel):
    url: str
    suggested_filename: str = ""

@app.post("/api/taxon/{taxon_id}/save-url")
def save_url_to_research(
    taxon_id: int,
    body: SaveUrlRequest,
    source: str = Query(default="col", pattern="^(col|worms|freshwater)$"),
):
    """Fetch a URL server-side and write the response body to the
    materialized Research folder for this taxon. See spec R4 for the
    full contract (validation, size cap, content-type allowlist,
    filename sanitization, error mapping).
    """
    with db() as conn:
        row = conn.execute(
            "SELECT id FROM taxon WHERE id = ?", (taxon_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(404, f"taxon {taxon_id} not found")
        sanitized = _build_segments(conn, taxon_id, source)

    target_dir = RESEARCH_DIR.joinpath(*sanitized)
    if not target_dir.exists():
        raise HTTPException(404, "Materialize the folder first")

    # Containment check (defense in depth, even though segments are sanitized)
    try:
        target_resolved = target_dir.resolve()
    except OSError as e:
        raise HTTPException(400, f"invalid path: {e}")
    if not target_resolved.is_relative_to(RESEARCH_DIR):
        raise HTTPException(400, "Path escapes research root")

    result = _save_url_to_research(
        target_resolved, body.url, body.suggested_filename, taxon_id,
    )
    logger.info(
        "save-url taxon_id=%s source=%s url=%s content_type=%s size=%s path=%s",
        taxon_id, source, body.url, result["content_type"],
        result["size"], result["absolute_path"],
    )
    return {
        "ok": True,
        "absolute_path": result["absolute_path"],
        "size": result["size"],
        "content_type": result["content_type"],
    }
```

### 3. Taxa client (`web/api.js` addition)

```js
async function saveUrl(taxonId, url, suggestedFilename = "", source = "col") {
  const r = await fetch(
    API + `/api/taxon/${taxonId}/save-url?source=${encodeURIComponent(source)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, suggested_filename: suggestedFilename }),
    },
  );
  if (!r.ok) {
    let detail = "";
    try {
      const body = await r.json();
      detail = body.detail || "";
    } catch {}
    throw new Error(
      `save-url ${taxonId} failed: ${r.status}${detail ? " " + detail : ""}`,
    );
  }
  return r.json();
}
```

Export it from `web/api.js` alongside the existing exports.

### 4. Tests (`tests/test_api_save_url.py`, new file)

Pattern follows `test_api_materialize.py` (in-memory SQLite + `TestClient`).

Coverage matrix:

| Test | What it asserts |
| --- | --- |
| `test_save_url_happy_path_pdf` | POST a public PDF URL, expect 200, file on disk, response shape |
| `test_save_url_404_no_folder` | Taxon exists but Research path not materialized → 404 |
| `test_save_url_404_no_taxon` | Taxon 999999999 doesn't exist → 404 |
| `test_save_url_400_private_ip_literal` | `http://10.0.0.1/x.pdf` → 400 |
| `test_save_url_400_loopback` | `http://127.0.0.1/x.pdf` → 400 |
| `test_save_url_400_link_local` | `http://169.254.169.254/x` → 400 |
| `test_save_url_400_unresolvable` | `http://does-not-exist-xyz.invalid/x` → 400 |
| `test_save_url_400_https_self_signed` | Self-signed cert → 400 or 502 (depends on cert validation) |
| `test_save_url_413_size_cap` | Mock 60 MB response → 413, no file written |
| `test_save_url_415_disallowed_type` | `text/csv` response → 415 |
| `test_save_url_502_origin_401` | Origin returns 401 → 502 with auth-required message |
| `test_save_url_502_origin_404` | Origin returns 404 → 502 with not-found message |
| `test_save_url_502_origin_500` | Origin returns 500 → 502 |
| `test_save_url_sanitization_traversal` | `suggested_filename: "../../../etc/passwd"` → file written as `passwd__<id>` |
| `test_save_url_sanitization_special_chars` | `suggested_filename: "a/b\\c<d>e | f*g?.pdf"` → file written with `_` substitutions |
| `test_save_url_collision` | Two saves with same suggested name → second is `__<timestamp>`-suffixed, original untouched |
| `test_save_url_special_source` | `?source=freshwater` works end-to-end |

Use a small fixture HTTP server (`http.server.HTTPServer` in a thread) to serve test files. The fixture serves a known PDF, an oversized body (via a `Content-Length` header that lies, or a generator), a 401, etc. The fixture also serves self-signed HTTPS for the cert-validation test.

## Data flow (happy path)

```
T+0s    User clicks a taxon row in taxa's tree (localhost:8765)
        └─ content.js click listener fires
           └─ 250 ms debounce
              └─ chrome.storage.local.set({currentTaxon: {id, sci_name}})

T+0.5s  chrome.storage.onChanged fires in background.js
        └─ chrome.contextMenus.update("send-to-taxa", {
             title: "Send to taxa: Homo sapiens",
             enabled: true,
           })

T+30s   User right-clicks a PDF link in another tab
        └─ context menu shows "Send to taxa: Homo sapiens"
        └─ User clicks the entry
           └─ chrome.contextMenus.onClicked fires
              └─ fetch POST http://localhost:8765/api/taxon/9606/save-url
                 body: {url: "https://example.com/paper.pdf", suggested_filename: "paper.pdf"}
T+31s     Server validates URL (no private IP) ✓
           Server validates Research path exists ✓
           Server GETs the URL (30s/60s timeouts, 50MB cap)
           Server validates Content-Type (application/pdf) ✓
           Server writes ./Research/Homo sapiens/paper__9606.pdf
           Server returns 200 {ok, absolute_path, size: 12345, content_type: "application/pdf"}
        └─ chrome.notifications.create: "Saved to Homo sapiens\n/Users/.../paper__9606.pdf"
        └─ chrome.action.setBadgeText("✓") for 3s
```

## Security boundaries

| Layer | Defense |
| --- | --- |
| Extension permissions | `activeTab` (user-gesture-bound, not always-on), `contextMenus`, `storage`, `scripting` (taxa only), `notifications`, `host_permissions: localhost:8765` only |
| Backend URL validation | Scheme allowlist (http/https), private-IP reject on resolved IP (DNS rebinding defense) |
| Backend response validation | Content-Type allowlist, size cap (50 MB), timeouts (30s/60s) |
| Backend file write | `_safe_resolve` containment check (defense in depth, even though `_build_segments` already sanitizes), filename sanitization (no `..`, no path separators), collision avoidance (timestamp suffix) |
| Extension → response | The extension never `eval`s, `innerHTML`s, or otherwise executes the response body. The response is bytes on disk; the user opens them with their own tool. |
| Logging | All save attempts logged server-side with `{taxon_id, source, url, content_type, size, status, absolute_path}`. No PII beyond the URL itself (user auth headers stripped server-side by `urllib.request` default). |

## Open questions for the spec phase → resolved

- **Content-type allowlist:** confirmed: PDF, JPEG, PNG, GIF, SVG, HTML, plain text, JSON, plus `application/octet-stream` as a binary catch-all. This covers the common case (PDFs from Scholar, images from search results, JSON from APIs).
- **Filename suggestion:** the extension sends the link's `<a download>` attribute, the URL's last segment, or the page title (in that order). The backend sanitizes; the user can rename later.
- **Settings panel:** deferred. v1 is the context-menu entry only. If the user wants a popup with status + last-saved path, that's a follow-up.
- **Polling endpoint:** deferred. v1 ships without `/recent-saves`. The user can manually refresh the Browser tab.
- **Packaging:** v1 ships unpacked. The user loads it via `chrome://extensions` developer mode. Chrome Web Store publishing is a follow-up.

## Risks specific to the implementation

| Risk | Mitigation |
| --- | --- |
| `urllib.request` doesn't natively stream the body with a hard size cap | Implement the cap manually in a loop (see `_save_url_to_research` above) |
| DNS rebinding: hostname resolves to public IP at validation time, private IP at fetch time | Resolve the hostname once and pass the IP directly to `urlopen` (skip DNS re-resolution) — or use a single `socket.create_connection((ip, port))` then build the HTTP request manually. The simpler defense: resolve once, cache the IP, and if the actual connection IP doesn't match, abort. For v1 we accept a small race window; document the known limit. |
| `urllib.request` doesn't validate TLS by default (uses `ssl.create_default_context()`) | The default context already rejects self-signed and expired certs. No code change. |
| Service worker killed mid-fetch (MV3 lifecycle) | Use `chrome.storage.session` to persist the in-flight save state. Re-hydrate on next click. v1 may accept that an in-flight save can be lost; document the limit. |
| Large icon files slow the install | Use small (16/48/128 px) placeholder PNGs. Real icons are a follow-up. |

## Out of scope (this design)

- Chrome Web Store publishing.
- Firefox port.
- Server-side proxy for paywalled content.
- WebSocket push for save completion.
- Polling endpoint for taxa to refresh Browser tab on save.
- Localized UI strings.
- Popup UI (status badge + last-saved path).
