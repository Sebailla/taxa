# Proposal: Browser Extension — Send to Research

## Why

After the Folder tab's Copy path + Open in Finder feature (#50) shipped, users can route files from external search results into the per-taxon Research folder with a single click. The remaining friction is that the user has to:

1. Click a search engine button in taxa → opens new tab (Scholar, ResearchGate, GBIF, etc.)
2. Find what they want, click right → Save as → paste the path → confirm
3. **OR** open the folder in Finder → save from browser → drag from Downloads

That works, but step 2 (Save as) is still 4-6 clicks with a context switch. The extension eliminates those clicks: from any browser tab, right-click → "Send to taxa: <taxon>" → the file lands in the right folder automatically. Same UX as a "Send to Evernote" or "Save to Google Drive" extension.

## What it does

MV3 Chrome/Firefox extension that adds a context-menu entry to the current tab:

1. **Capture the current taxon from taxa.** The extension injects a content script into `localhost:8765` (where taxa runs). When the user selects a taxon in taxa's tree, the content script writes `{id, scientific_name}` to `chrome.storage.local`.

2. **Right-click → "Send to taxa: <scientific_name>"**. The background service worker reads the URL + suggested filename from the active tab, POSTs to a new taxa endpoint, and surfaces the result via the toolbar badge.

3. **Backend saves the file server-side.** A new `POST /api/taxon/{id}/save-url` endpoint fetches the URL server-side (with size + content-type allowlists), writes the file under `Research/<chain>/<filename>__<taxon-id>.<ext>`, and returns `{ok, absolute_path, size, content_type}`.

4. **Toast in taxa when the save completes.** The taxa web client polls (or the backend pushes via WebSocket) so the user gets confirmation without leaving the external page.

## What it does NOT do

- **Doesn't bypass auth.** If a paper is behind a paywall, the server-side fetch fails (no cookies, no auth headers) → toast: "Could not save: authentication required". No workaround attempted.
- **Doesn't scrape search results.** The extension saves URLs the user explicitly right-clicks on, not automated capture of every link on the page.
- **Doesn't replace taxa's own server-side fetch (Camino A).** Camino A (Copy path + Open in Finder) stays. Camino B adds a more polished flow for the common case.
- **Doesn't publish to Chrome Web Store yet.** Local unpacked install only (developer mode). Publishing comes later if the user wants.
- **Doesn't auto-retry on transient failures.** One attempt, then toast the error.

## Scope

**In scope (this change):**

- MV3 browser extension: manifest, background service worker, content script, popup HTML/JS, icons (placeholder).
- `POST /api/taxon/{id}/save-url` endpoint with allowlists + size cap + filename sanitization.
- `web/api.js`: small `saveUrl(taxonId, url, suggestedFilename)` client.
- Taxa polling endpoint (optional) so the taxa UI can refresh the Browser tab when a save lands from another tab.
- Tests for the new endpoint (happy path, auth-fail, size-cap, content-type reject, path-escape).
- Manual smoke checklist for the extension (extension E2E is hard to automate without a real Chrome).

**Out of scope:**

- Chrome Web Store publishing + signing.
- Firefox port (manifest tweaks; trivially port later).
- Bidirectional sync (extension ↔ taxa's taxon selection). Capture-only is enough.
- Server-side proxy for paywalled content.
- WebSocket push for save completion (use polling; cheaper, no infra change).
- Localized UI strings (English only for v1).

## Risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Server-side fetch exposes taxa to SSRF | Medium | Allowlist by content-type (PDF, image, HTML, JSON); cap size at 50 MB; cap timeout at 30s; log all requests; reject internal-network IPs (RFC1918, link-local, loopback) at the fetch layer. |
| Auth-required resources return 4xx → user confusion | High | Clear error toast: "Authentication required — save from the browser manually". |
| Filename collisions on disk | Medium | `<original>__<taxon-id>.<ext>` suffix; if collision, append `__<timestamp>`. Never overwrite. |
| Extension targets wrong taxon (stale storage) | Low | Content script writes on every `selectTaxon()` call (verified via taxa's already-instrumented click handler). Storage value is read fresh at context-menu click time. |
| taxa isn't running when user right-clicks | Medium | Check `http://localhost:8765/api/health` in the background before sending the POST. If unreachable, toast "taxa not running". |
| Manifest V3 service worker is killed between user actions | High | Use `chrome.storage.session` for in-flight requests + idempotency keys. Service worker re-hydrates on the next click. |
| Paywalled content scraping (legal/ToS) | High | Hard rule: only save URLs the user explicitly right-clicks on. No background harvesting. Document this in the extension description + README. |

## Acceptance criteria

- [ ] User can install the extension in Chrome developer mode.
- [ ] User can select a taxon in taxa and see the context-menu entry update to "Send to taxa: <scientific_name>".
- [ ] User can right-click a PDF / image / HTML page in another tab and have it land in `Research/<chain>/<filename>__<taxon-id>.<ext>`.
- [ ] Backend rejects internal-network URLs (RFC1918, link-local, loopback) with HTTP 400.
- [ ] Backend rejects oversized responses (>50 MB) with HTTP 413.
- [ ] Backend rejects non-allowlisted content-types with HTTP 415.
- [ ] Backend rejects auth-required URLs (4xx response from origin) with HTTP 502 + a clear detail message.
- [ ] Filenames with `..`, `/`, or other path-traversal chars are sanitized server-side.
- [ ] `pytest tests/test_api_save_url.py` → all green; no regressions in existing 48 tests.
- [ ] Manual smoke (documented checklist) covers the install + right-click flow on at least 3 distinct file types.

## Deliverables

- `extension/` directory: manifest.json, background.js, content.js, popup.html, popup.js, icons/ (placeholder PNGs)
- `extension/README.md`: install + use instructions
- `api/server.py`: new `_save_url_to_research()` helper + `POST /api/taxon/{id}/save-url` endpoint
- `web/api.js`: new `saveUrl()` client
- `tests/test_api_save_url.py`: new test file
- `docs/extension.md`: user-facing docs (install steps, browser support, known limitations)

## Open questions for spec phase

- What's the exact content-type allowlist? (PDF, JPEG, PNG, GIF, SVG, HTML, JSON, plain text? Binary unknown?)
- Should the filename suggestion prefer the page `<title>` over the URL slug?
- Does the extension need its own opt-in settings panel, or is the context-menu entry sufficient for v1?
- Should the polling endpoint be a new GET (`/api/taxon/{id}/recent-saves?since=...`) or piggyback on an existing one?
- Will the user accept dev-mode install friction, or do they want a packaged .crx + signed build for distribution?
