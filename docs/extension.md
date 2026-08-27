# Browser extension — "Send to Research"

> **Status:** v0.1.0 (unpacked; local install only).

A Manifest V3 Chrome/Firefox extension that adds a right-click "Send to taxa: &lt;taxon&gt;" entry to any browser tab. When invoked, the extension posts the active tab's URL (or the right-clicked link's URL) to a local `taxa` instance, which fetches the resource server-side and writes it to the active taxon's Research folder.

## Why this exists

The Folder tab's **Copy path** + **Open in Finder** buttons (added in [#50](https://github.com/Sebailla/taxa/pull/50)) reduced the friction of routing external search results into the per-taxon Research folder, but the user still has to manually save + drag. The extension eliminates those manual steps: from any browser tab, right-click → "Send to taxa: &lt;taxon&gt;" → the file lands in the right folder automatically.

It's the **Camino B** flow in the broader research-saving UX, complementing (not replacing) Camino A.

## How it works

1. **Taxon capture.** The extension injects a content script into `http://localhost:8765/*`. When the user clicks a taxon row, the content script writes `{id, scientific_name}` to `chrome.storage.local` (debounced 250 ms).
2. **Context menu.** The background service worker registers a single context-menu entry, "Send to taxa: &lt;scientific_name&gt;", and updates its title reactively when the captured taxon changes. The entry is disabled when no taxon is selected.
3. **Save.** On context-menu click, the worker POSTs the target URL to `POST /api/taxon/{id}/save-url?source=col`. The backend fetches the URL server-side, validates it (SSRF, content-type, size), sanitizes the filename, and writes the response body to `Research/&lt;chain&gt;/&lt;name&gt;__&lt;id&gt;.&lt;ext&gt;`.
4. **Notification.** The worker surfaces success or failure via `chrome.notifications` and a brief toolbar badge (green ✓ for 3 s on success, red ✗ on failure).

## Filename convention

The backend always saves as:

```
<sanitized-name>__<taxon-id>.<extension>
```

- `<sanitized-name>` comes from the `<a download>` attribute, the URL's last segment, or the page title (in that order). Sanitization replaces any character outside `[A-Za-z0-9._-]` with `_` and drops leading dots.
- `<taxon-id>` is mandatory so the per-taxon destination stays unambiguous even when suggested names collide.
- `<extension>` comes from the response's `Content-Type`, not from the suggested filename. This is more reliable than trusting the caller's guess.
- On collision, a `__&lt;timestamp&gt;` suffix is appended. The original file is **never** overwritten.

## Install

The extension is not yet on the Chrome Web Store. To install it locally:

1. Clone the repository: `git clone https://github.com/Sebailla/taxa.git`
2. Open `chrome://extensions` in Chrome.
3. Enable **Developer mode** (top-right toggle).
4. Click **Load unpacked** and select `extension/` from the repo.
5. The toolbar icon appears. No install-time permission prompt; Chrome asks for `activeTab` and `notifications` on first use.

To update after a code change: click the **Reload** button on `chrome://extensions`.

## Supported browsers

- **Chrome 120+** (Manifest V3). Tested.
- **Firefox 109+** — Manifest V3 is supported but Firefox expects `"background": {"scripts": [...]}` instead of `{"service_worker": "..."}`. A Firefox port is a trivial follow-up.

## Permissions

| Permission | Why |
| --- | --- |
| `activeTab` | Read the URL of the tab the user is interacting with. |
| `contextMenus` | Add the right-click entry. |
| `storage` | Persist the current taxon between service-worker suspensions. |
| `scripting` | Inject the content script into the taxa tab. |
| `notifications` | Show the save result. |
| `host_permissions: http://localhost:8765/*` | Talk to the local taxa backend. |

No `<all_urls>`, no remote scripts, no `webRequest` / `declarativeNetRequest`. The extension cannot read or modify any page outside `localhost:8765`.

## Known limitations (v1)

- **No paywall bypass.** If a paper is behind a paywall or requires auth, the server-side fetch returns 401/403 and the extension surfaces an actionable error. No workaround attempted.
- **No Chrome Web Store publishing yet.** Local install only (developer mode). Publishing is a follow-up.
- **No Firefox port.** See "Supported browsers" above.
- **No bidirectional sync.** The extension captures which taxon is current; taxa does not learn which other tabs the user has open.
- **MV3 service-worker lifecycle.** The worker can be killed by the browser between clicks. The extension re-hydrates on the next context-menu open, but an in-flight save can be lost.
- **DNS rebinding has a small race window.** The backend resolves the hostname once and checks the IP; a clever rebinding attack could re-resolve between the check and the actual connection. Document the limit; a proper fix requires a custom socket-level connect.

## Manual smoke checklist

After installing:

- [ ] Open `taxa` and click a taxon. The context menu in another tab shows "Send to taxa: &lt;name&gt;".
- [ ] Right-click a PDF link on a search results page → click the entry → file lands in `Research/&lt;chain&gt;/&lt;name&gt;__&lt;id&gt;.pdf`.
- [ ] Right-click a JPG image on a page → file lands in `Research/&lt;chain&gt;/&lt;name&gt;__&lt;id&gt;.jpg` (or `.jpeg`).
- [ ] Right-click a page background (no link) → uses the tab's URL.
- [ ] Right-click without a taxon selected → menu entry is disabled.
- [ ] Right-click when `taxa` is not running → notification: "Cannot save: taxa is not running at <http://localhost:8765>."
- [ ] Right-click a paywalled PDF → notification: "Cannot save: ... authentication required."

## Files

- `extension/manifest.json` — MV3 manifest with minimal permissions.
- `extension/content.js` — injected into `localhost:8765/*`; captures taxon selections.
- `extension/background.js` — service worker; manages the context menu and saves.
- `extension/icons/icon-{16,48,128}.png` — placeholder toolbar icons (solid green square; real icons are a follow-up).
- `extension/README.md` — same content as this page, with browser-specific install details.
- `api/server.py` — the new `POST /api/taxon/{id}/save-url` endpoint that does the actual fetch + write (shipped in [#53](https://github.com/Sebailla/taxa/pull/53)).

## Related

- OpenSpec artifacts: `openspec/changes/browser-extension-save-to-research/`
- Backend PR: [#53](https://github.com/Sebailla/taxa/pull/53) — adds the `save-url` endpoint, helpers, and tests.
- Camino A (Copy path + Open in Finder): [#50](https://github.com/Sebailla/taxa/pull/50).
