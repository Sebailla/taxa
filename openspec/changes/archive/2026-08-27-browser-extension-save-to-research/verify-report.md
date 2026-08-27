# Verify Report: browser-extension-save-to-research

## Status

**PASS** — both PRs of the chained delivery merged to main.

## What shipped

### PR 1 of 2 — backend (#53, commit 69653f6)

Squash-merged to main. Adds the `POST /api/taxon/{taxon_id}/save-url` endpoint, the supporting helpers (`_is_private_or_reserved_ip`, `_sanitize_filename`, `_save_url_to_research`), the `SaveUrlRequest` Pydantic model, the `saveUrl()` client in `web/api.js`, and 15 test cases in `tests/test_api_save_url.py`. Also updated `tests/test_smoke.py` to include the new endpoint in the OpenAPI `expected_paths`.

### PR 2 of 2 — extension files (#54, commit 4df3b57)

Squash-merged to main. Ships the MV3 extension:

- `extension/manifest.json` — minimal permissions (`activeTab`, `contextMenus`, `storage`, `scripting`, `notifications`), single host permission for `localhost:8765`.
- `extension/content.js` — captures taxon selections via `[data-taxon-id]` click listener, debounced 250 ms.
- `extension/background.js` — service worker; registers the context menu on install + onStartup; updates reactively on `currentTaxon` changes; POSTs to the backend on click; surfaces success / failure via `chrome.notifications` + a brief toolbar badge.
- `extension/icons/icon-{16,48,128}.png` — placeholder green squares (81-327 bytes each). Real icons are a follow-up.
- `extension/README.md` + `docs/extension.md` — install, use, permissions, filename convention, known limitations, manual smoke checklist, FAQ.

## Acceptance criteria (from proposal.md + spec.md)

| AC | Status | Evidence |
| --- | --- | --- |
| Backend: `POST /api/taxon/{id}/save-url` registered, returns 200, writes file to disk | ✅ | `tests/test_api_save_url.py::test_save_url_happy_path_pdf` passes |
| 404 when Research path not materialized | ✅ | `test_save_url_404_no_folder` passes |
| 404 for non-existent taxon | ✅ | `test_save_url_404_no_taxon` passes |
| 400 for private/reserved IP (RFC1918, loopback, link-local, unresolvable) | ✅ | `test_save_url_400_private_ip_literal`, `..._loopback`, `..._link_local`, `..._unresolvable` all pass |
| 413 for response > 50 MB; no file written | ✅ | `test_save_url_413_size_cap` passes |
| 415 for non-allowlisted Content-Type | ✅ | `test_save_url_415_disallowed_type` passes |
| 502 for origin 4xx/5xx with auth-required / not-found distinction | ✅ | `test_save_url_502_origin_401`, `..._origin_404` pass |
| Filename sanitization (path traversal, special chars) | ✅ | `test_save_url_sanitization_traversal`, `..._special_chars` pass |
| Collision appends `__<timestamp>`, never overwrites | ✅ | `test_save_url_collision` passes |
| `?source=freshwater` works | ✅ | `test_save_url_special_source` passes |
| Extension: MV3 with minimal permissions, single host permission | ✅ | manifest.json validates; perms = activeTab, contextMenus, storage, scripting, notifications; host = `http://localhost:8765/*` |
| Extension: content script captures taxon, debounced | ✅ | content.js writes to `chrome.storage.local` with 250 ms debounce; manual smoke in README |
| Extension: context menu reflects current taxon or disabled | ✅ | background.js: `refreshMenu()` updates on `storage.onChanged`; entry is `enabled: !!currentTaxon` |
| Extension: `?Closes #52` body + `Closes #51` in PR 1 | ✅ | both PRs closed their issues on merge |
| `pytest tests/test_api_save_url.py` → all green | ✅ | 15 passed |
| `pytest tests/test_web_toggle.py tests/test_smoke.py tests/test_api_materialize.py tests/test_api_save_url.py` → 63 passed, 8 skipped, 0 regressions | ✅ | confirmed post-merge |
| Manual smoke checklist (install + right-click on PDF/image/HTML) | ✅ documented | in `extension/README.md`; not automatable without a real Chrome harness |

## Test plan evidence

- `pytest tests/test_api_save_url.py -v` → 15 passed, 0 failed
- `pytest tests/test_web_toggle.py tests/test_smoke.py tests/test_api_materialize.py tests/test_api_save_url.py -q` → 63 passed, 8 skipped, 0 failed
- CI on both PRs: `Smoke tests: completed (success)`

## Open questions (from spec phase) — resolved

- **Content-type allowlist:** confirmed (9 types in `_SAVE_URL_ALLOWED_TYPES`).
- **Filename suggestion:** the extension sends the link's `<a download>` attr, the URL's last segment, or the page title (in that order). The backend sanitizes; the user can rename later.
- **Settings panel:** deferred. v1 is the context-menu entry only.
- **Polling endpoint:** deferred. v1 ships without `/recent-saves`. The user can manually refresh the Browser tab.
- **Packaging:** v1 ships unpacked. The user loads it via `chrome://extensions` developer mode. Chrome Web Store publishing is a follow-up.

## Known limitations (documented in extension/README.md + docs/extension.md)

- No paywall bypass.
- No Chrome Web Store publishing yet (local install only).
- No Firefox port (trivial manifest tweaks; not done).
- No bidirectional sync.
- MV3 service-worker lifecycle: in-flight saves can be lost if the worker is killed.
- DNS rebinding: a small race window between IP check and actual connection (Python GIL is the constraint).

## Follow-up actions for the orchestrator

- Archive this change: `openspec/changes/archive/2026-08-27-browser-extension-save-to-research/`.
- The `design.md §2.4` mentions `urllib.request`'s lack of a hard size cap, implemented manually. Confirmed working in the tests.
- If Chrome Web Store publishing is wanted in the future, follow-up change.

## Carry-forward context for future changes

- The save-url endpoint's `_save_url_to_research()` is the canonical pattern for server-side fetch + write under `Research/`. Reuse it for any future "save URL to disk" feature (e.g., the eventual `/recent-saves` polling endpoint).
- The content-type allowlist + size cap are good defaults for any user-driven file ingestion. Use the same constants (`_SAVE_URL_ALLOWED_TYPES`, `_SAVE_URL_MAX_BYTES`) for any future "ingest URL" endpoint.
- The SSRF check (`_is_private_or_reserved_ip`) is the canonical private-IP guard for this codebase. Reuse it rather than duplicating.
- The MV3 service worker pattern in `extension/background.js` (context menu + storage.onChanged + chrome.notifications) is a good template for future taxa browser integrations.
- The content script pattern in `extension/content.js` (delegated click listener on document.body + debounce + storage.local write) is a good template for future "watch taxa DOM" extensions.

## Engram observation IDs

| Artifact | Topic key | Obs id |
| --- | --- | --- |
| Init (cached from prior session) | `sdd-init/taxa` | 4217 |
| Preflight for this change | `sdd-preflight/browser-extension-save-to-research` | 4343 |
| PR 1 backend summary | TBD | TBD |
| This verify report | TBD | TBD |
| Archive report (next) | TBD | TBD |
