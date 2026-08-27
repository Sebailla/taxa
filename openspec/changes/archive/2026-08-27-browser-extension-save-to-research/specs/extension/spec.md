# Spec: Browser Extension — Send to Research

## Overview

A Manifest V3 browser extension that adds a right-click "Send to taxa: <taxon>" context-menu entry to any browser tab. When invoked, the extension posts the active tab's URL to a new `taxa` backend endpoint that fetches the resource server-side and writes it under `Research/<chain>/`. The current taxon is captured from the open `taxa` tab via a content script and stored in `chrome.storage.local`.

This is **Camino B** in the user-facing research-saving flow: the user can already copy paths and open Finder from the Folder tab (Camino A, #50), but the extension removes the 4-6 remaining manual clicks for the common case.

## Requirements

### R1: Manifest and permissions

**R1.1** The extension must declare Manifest V3 (`"manifest_version": 3`).

**R1.2** The extension must request only the minimum permissions needed:

- `"activeTab"` — read the URL of the tab the user is interacting with.
- `"contextMenus"` — add the right-click entry.
- `"storage"` — persist the current taxon between service-worker suspensions.
- `"scripting"` — inject the content script into the taxa tab.
- `"host_permissions": ["http://localhost:8765/*"]` — talk to the local taxa backend.

No broad `<all_urls>` permission. No remote-script permission. No `webRequest` / `declarativeNetRequest`.

**R1.3** The extension must NOT require any background network calls to remote servers. The only network endpoint is the user's local `taxa` instance.

**Scenarios:**

- **R1.S1 (Install):** GIVEN the extension's `dist/` folder is unpacked into Chrome's `chrome://extensions` developer mode → WHEN the user clicks "Load unpacked" → THEN the extension installs without errors and the toolbar icon appears.
- **R1.S2 (Permission grant):** GIVEN the extension is installed → WHEN the user first triggers the context menu → THEN Chrome shows a one-time permission grant prompt for the requested permissions. (Active tab permissions are user-gesture-bound; no install-time warning.)
- **R1.S3 (Permission audit):** GIVEN a reviewer inspects `manifest.json` → THEN the only host permission is `http://localhost:8765/*` (no `<all_urls>`, no remote origins).

### R2: Taxon capture from the open taxa tab

**R2.1** A content script (`content.js`) must inject into every page matching `http://localhost:8765/*` on document idle.

**R2.2** The content script must listen for `taxa`'s `selectTaxon(id)` action — observed via a delegated `click` handler on `[data-taxon-id]` rows, or a custom event dispatched by `taxa`'s `nav.js`. The captured payload must include at minimum `{id: number, scientific_name: string}`.

**R2.3** On every successful capture, the content script must write the payload to `chrome.storage.local` under the key `currentTaxon`:

```js
chrome.storage.local.set({ currentTaxon: { id, scientific_name, capturedAt: Date.now() } });
```

**R2.4** If no taxon has been selected yet, `currentTaxon` must be `undefined` (or absent). The extension must NOT default to a placeholder taxon.

**R2.5** The content script must debounce rapid successive captures (a user clicking 5 rows in a second) so the storage write is at most once per 250 ms.

**Scenarios:**

- **R2.S1 (Capture on click):** GIVEN the extension is installed and the user has `taxa` open at `localhost:8765` → WHEN the user clicks a taxon row in the tree → THEN `chrome.storage.local.currentTaxon` is updated to that taxon's `{id, scientific_name}` within 250 ms.
- **R2.S2 (No taxon selected):** GIVEN `taxa` is open but no taxon has been clicked → WHEN the user right-clicks in another tab → THEN the context-menu entry is disabled or absent (see R3.4).
- **R2.S3 (Multi-tab):** GIVEN the user has `taxa` open in tab A and a paper in tab B → WHEN the user clicks a different taxon in tab A, then right-clicks in tab B → THEN the context menu reflects the most recent taxon selection.
- **R2.S4 (tab closed):** GIVEN `taxa` is closed → WHEN the user right-clicks elsewhere → THEN the context-menu entry is disabled (no stale taxon from yesterday's session).

### R3: Context menu integration

**R3.1** On extension install, the background service worker must register a single context menu entry via `chrome.contextMenus.create()` with:

- `id`: `"send-to-taxa"`
- `title`: dynamic — defaults to `"Send to taxa: <none selected>"`, updates to `"Send to taxa: <scientific_name>"` when a taxon is captured.
- `contexts`: `["link", "page", "image", "video", "audio"]`
- `enabled`: `false` when no taxon is captured, `true` when one is.

**R3.2** The context menu title must update reactively when `chrome.storage.local.currentTaxon` changes. The background worker listens to `chrome.storage.onChanged` and calls `chrome.contextMenus.update()`.

**R3.3** On context-menu click (`chrome.contextMenus.onClicked`), the background worker must:

1. Read `currentTaxon` from `chrome.storage.local`.
2. Read the active tab's URL via `chrome.tabs.query({ active: true, currentWindow: true })`.
3. Read the active tab's title (for filename suggestion).
4. POST to `http://localhost:8765/api/taxon/<id>/save-url` with body `{url, suggested_filename}`.
5. Surface the result via a toolbar badge update + a `chrome.notifications` notification (no toast injection into the external page).

**R3.4** If no taxon is captured, the context-menu click handler must be a no-op and show a notification: "Open taxa and select a taxon first."

**Scenarios:**

- **R3.S1 (Happy path):** GIVEN a taxon is captured and the user right-clicks a PDF link in another tab → WHEN the user clicks "Send to taxa: <scientific_name>" → THEN a notification appears within 3 s: "Saved to Research/<chain>/<file>__<taxon-id>.<ext>".
- **R3.S2 (No taxon):** GIVEN no taxon is captured → WHEN the user right-clicks → THEN the entry is disabled (greyed out in the menu).
- **R3.S3 (External page context):** GIVEN a paper PDF is open in a tab → WHEN the user right-clicks the page background (not a link) → THEN the context-menu entry uses the tab's URL (the PDF itself).
- **R3.S4 (Link context):** GIVEN a search results page with a link to a PDF → WHEN the user right-clicks the link → THEN the context-menu entry uses the link's `srcUrl` (not the page's URL).

### R4: Backend save endpoint

**R4.1** New endpoint: `POST /api/taxon/{taxon_id}/save-url?source=col|worms|freshwater` (default `col`).

Request body (JSON):

```json
{ "url": "https://example.com/paper.pdf", "suggested_filename": "paper.pdf" }
```

Response (200):

```json
{ "ok": true, "absolute_path": "/abs/path/Research/.../paper__12345.pdf", "size": 12345, "content_type": "application/pdf" }
```

**R4.2** The endpoint must:

1. Validate `url` is a syntactically valid HTTP/HTTPS URL.
2. Resolve the target Research path via the same `_build_segments(conn, taxon_id, source)` chain used by `/materialize`.
3. Compute `target_dir = RESEARCH_DIR/<chain>`. If `target_dir` doesn't exist on disk, return 404 (the user must materialize first, same UX as `/open-folder`).
4. Validate the URL host is NOT in any private/reserved range (RFC1918, link-local, loopback, multicast, reserved). Return 400 if it is.
5. Issue a streaming GET to the URL with a 30 s connect timeout and 60 s read timeout.
6. Cap the response body at 50 MB. If the cap is hit, return 413.
7. Validate the `Content-Type` header is in the allowlist: `application/pdf`, `image/jpeg`, `image/png`, `image/gif`, `image/svg+xml`, `text/html`, `text/plain`, `application/json`, `application/octet-stream` (catch-all for unknown binary). Return 415 otherwise.
8. Stream the body to `target_dir/<safe_filename>`, where `safe_filename` is computed from `suggested_filename` (sanitized) + `__<taxon_id>` + extension (from content-type or original URL).
9. On any 4xx/5xx response from the origin, return 502 with the origin's status + a clear `detail` field ("Authentication required" / "Not found" / "Server error").

**R4.3** Filename sanitization:

- Strip any directory components (treat `/` and `\` as separators; take the last segment).
- Replace any character outside `[A-Za-z0-9._-]` with `_`.
- Reject names that start with `.` (hidden files).
- If the sanitized name is empty, fall back to `download_<timestamp>.<ext>`.
- Append `__<taxon_id>` before the extension.
- If the final path already exists, append `__<timestamp>` before the extension. Never overwrite.

**R4.4** Logging: every save attempt is logged with `{taxon_id, source, url, content_type, size, status, absolute_path}`. No PII beyond the URL itself.

**Scenarios:**

- **R4.S1 (Happy path PDF):** GIVEN a taxon with the Research path materialized → WHEN the backend receives a valid POST with a public PDF URL → THEN it returns 200 with `{ok: true, absolute_path, size, content_type: "application/pdf"}` and the file is on disk.
- **R4.S2 (404 not materialized):** GIVEN a taxon whose Research path doesn't exist on disk → WHEN the endpoint receives any POST → THEN it returns 404 with `detail: "Materialize the folder first"`.
- **R4.S3 (400 SSRF):** GIVEN a POST with `url: "http://192.168.1.1/admin"` or `"http://localhost:6379"` or `"http://169.254.169.254/"` → THEN it returns 400 with `detail: "URL points to a private or reserved network range"`.
- **R4.S4 (413 size cap):** GIVEN a POST whose response would exceed 50 MB → THEN it returns 413 with `detail: "Response exceeds 50 MB cap"` and writes nothing to disk.
- **R4.S5 (415 content-type):** GIVEN a POST whose response has `Content-Type: text/csv` → THEN it returns 415 with `detail: "Content-Type not in allowlist"`.
- **R4.S6 (502 auth-required):** GIVEN a POST whose origin returns 401 → THEN the endpoint returns 502 with `detail: "Origin returned 401 — authentication required"`.
- **R4.S7 (502 not-found):** GIVEN a POST whose origin returns 404 → THEN the endpoint returns 502 with `detail: "Origin returned 404 — resource moved or deleted"`.
- **R4.S8 (Filename sanitization):** GIVEN a POST with `suggested_filename: "../../../etc/passwd"` → THEN the saved file is named `passwd__<id>` (no `..`, no path traversal).
- **R4.S9 (Collision):** GIVEN a save that would write to an existing path → THEN the file is written with a `__<timestamp>` suffix and the original file is not modified.
- **R4.S10 (Non-existent taxon):** GIVEN a POST to `/api/taxon/999999999/save-url` where taxon 999999999 doesn't exist → THEN it returns 404.

### R5: Taxa client (web) integration

**R5.1** New `web/api.js::saveUrl(taxonId, url, suggestedFilename)` function. Same error pattern as `materializeResearch()`: throw with the FastAPI `detail` on non-OK responses.

**R5.2** (Optional) Polling endpoint `GET /api/taxon/{id}/recent-saves?since=<timestamp>` returning `{saves: [{absolute_path, size, content_type, saved_at}]}`. The taxa web client can poll this every 5 s when the Browser tab is mounted and refresh the explorer when a new save arrives. v1 ships WITHOUT this; it's a "nice to have" tracked as a follow-up.

**R5.3** (Optional) When the extension's notification fires, the next time the user switches to `taxa`, the Browser tab refreshes. Implementation: rely on the user coming back; no cross-tab event plumbing in v1.

**Scenarios:**

- **R5.S1 (Save from extension, refresh on return):** GIVEN the user is on `taxa` Browser tab showing a folder, then switches to scholar, saves a paper, switches back → WHEN they look at the Browser tab → THEN the new file is visible (after a manual refresh OR on tab re-mount). v1 accepts the manual refresh.

### R6: Error handling & user feedback

**R6.1** The extension must surface every backend error to the user via a `chrome.notifications` notification with a clear, actionable message:

- 400 SSRF → "Cannot save: that URL is on a private network."
- 404 not materialized → "Cannot save: open taxa and click Create on the Folder tab first."
- 413 size cap → "Cannot save: the file is larger than 50 MB."
- 415 content-type → "Cannot save: the file type (<content-type>) is not supported."
- 502 auth-required → "Cannot save: the resource requires authentication. Try saving from the browser directly."
- 502 other → "Cannot save: the source returned <status>. Try again or save manually."
- Network error (taxa not running) → "Cannot save: taxa is not running at localhost:8765."

**R6.2** The notification must include the absolute path of any successful save so the user can find the file even if the Browser tab is stale.

**R6.3** Every notification must auto-dismiss after 8 s. Clicking the notification focuses the `taxa` tab if open (uses `chrome.tabs.query({ url: "http://localhost:8765/*" })`).

**Scenarios:**

- **R6.S1 (Success):** GIVEN a successful save → THEN a notification "Saved to Research/<chain>/<file> (12.3 KB)" appears and auto-dismisses after 8 s. Clicking it focuses the `taxa` tab.
- **R6.S2 (Failure clarity):** GIVEN any failed save → THEN the notification's message is one of the strings in R6.1, not a raw "Error: 500".

### R7: File naming

**R7.1** The `__<taxon_id>` suffix is mandatory and never optional. The reasoning: when a user is collecting papers across multiple taxa (e.g., they have a baseline folder of parasites for several hosts), the suffix keeps the per-taxon destination unambiguous even if the suggested filename is generic ("paper.pdf", "fig1.png").

**R7.2** The extension's `suggested_filename` is a hint, not a contract. The backend computes the actual filename server-side. The user controls the hint via:

- The `<a download="filename.pdf">` attribute, if present.
- The Content-Disposition header on the URL response.
- The URL's last path segment.
- The page `<title>` (sanitized).

**R7.3** Whichever the user explicitly right-clicked is preferred:

- A link → the link's `download` attr or the URL's last segment.
- An image → the image's alt text or URL.
- The page itself → the Content-Disposition filename or the URL's last segment.

**Scenarios:**

- **R7.S1 (Link with download attr):** GIVEN a link `<a download="smith-2024.pdf" href="https://...">` → THEN the saved file is `smith-2024__<taxon_id>.pdf`.
- **R7.S2 (Link without download attr):** GIVEN a link with no download attr → THEN the saved file is `<last-path-segment>__<taxon_id>.<ext>`.
- **R7.S3 (Page with Content-Disposition):** GIVEN a URL whose response has `Content-Disposition: attachment; filename="..."` → THEN that filename is used as the basis for the saved file.
- **R7.S4 (Page without anything):** GIVEN a generic page URL like `https://example.com/article/12345` → THEN the saved file is `12345__<taxon_id>` + extension guessed from content-type.
- **R7.S5 (Suffix collision):** GIVEN two saves with identical suggested names for the same taxon → THEN the second is written as `<name>__<taxon_id>__<timestamp>.<ext>`.

### R8: Security

**R8.1** The backend MUST reject URLs whose host resolves to any of:

- RFC1918 ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
- Loopback (`127.0.0.0/8`, `::1`)
- Link-local (`169.254.0.0/16`, `fe80::/10`)
- Multicast (`224.0.0.0/4`, `ff00::/8`)
- Reserved (`0.0.0.0/8`, `192.0.0.0/24`, `192.0.2.0/24`, `198.18.0.0/15`, `198.51.100.0/24`, `203.0.113.0/24`, `240.0.0.0/4`)
- IPv6 unique-local (`fc00::/7`)

The check happens on the resolved IP, not the hostname string, to defeat DNS rebinding.

**R8.2** The backend MUST reject HTTPS URLs with self-signed or expired certificates (the existing `httpx` / `requests` defaults already do this; no relaxation).

**R8.3** The backend MUST log all save attempts (R4.4) so the user can audit what was saved where.

**R8.4** The extension MUST NOT execute any code from the response body. The backend serves only file bytes; the extension never `eval`s, never `innerHTML`s the response, never opens the saved file.

**R8.5** The extension MUST NOT attempt to bypass the origin's CORS or CSP. The backend fetch is server-to-origin, so CORS doesn't apply. CSP is the origin's policy, not ours.

**Scenarios:**

- **R8.S1 (Private IP rejected):** GIVEN a POST with `url: "http://10.0.0.5/foo.pdf"` → THEN the endpoint returns 400 even if the user's machine has a service on that IP.
- **R8.S2 (DNS rebinding defended):** GIVEN a POST with a hostname that resolves to a private IP → THEN the endpoint still returns 400 (it checks the resolved IP, not the hostname).
- **R8.S3 (No code execution):** GIVEN a save of an HTML file with embedded `<script>` tags → THEN the extension never executes the script; the file is saved as bytes.

## Acceptance criteria

- [ ] R1: Manifest v3, minimal permissions, only `localhost:8765` host.
- [ ] R2: Content script captures taxon selection, writes to storage, debounced.
- [ ] R3: Context menu reflects current taxon (or disabled if none), responds to right-click, posts to backend.
- [ ] R4: Backend endpoint validates URL (SSRF, size, content-type, auth), fetches, writes file with sanitized name + `__<taxon_id>` suffix.
- [ ] R5: `web/api.js::saveUrl()` client follows the existing error pattern.
- [ ] R6: Every backend outcome has a user-facing notification with a clear, actionable message.
- [ ] R7: Filename includes the mandatory `__<taxon_id>` suffix.
- [ ] R8: SSRF defenses verified against RFC1918 + loopback + DNS rebinding test cases.
- [ ] `pytest tests/test_api_save_url.py` → all green; no regressions in the 48 existing tests.
- [ ] Manual smoke checklist (in `docs/extension.md`) covers install + right-click flow on at least 3 distinct file types.

## Out of scope (deferred)

- Chrome Web Store publishing.
- Firefox port.
- Bidirectional sync (extension ↔ taxa).
- Server-side proxy for paywalled content.
- WebSocket push for save completion.
- Localized UI strings.
- `web/api.js` polling endpoint (`/recent-saves`) — tracked as a follow-up.
