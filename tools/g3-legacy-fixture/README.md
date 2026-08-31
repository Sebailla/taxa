# G3 Legacy Fixture (diagnostic only)

Minimal, self-contained, disposable G3 legacy fixture for controlled
HTTP-status enforcement testing. **Not part of the product.** Unreachable
from production by design.

## Contents

| Path | Purpose |
|---|---|
| `taxa.db` | Pre-seeded SQLite: 10 `taxon` + 8 `vernacular` rows. Schema mirrors production v1+v2. |
| `web/index.html` | Minimal HTML referencing `dist/tailwind.css` + `app.js`. Carries G5 hydration-readiness `data-testid` markers (`g5-shell-ready`, `g5-tree-ready`, `g5-search-ready`, `g5-keymap-ready`). |
| `web/dist/tailwind.css` | Required CSS asset (manifest's `mount-runtime-link-tag-css-003` consumer). |
| `web/app.js` | Minimal entry importing 10 sibling module stubs. After import, flips `document.body.dataset.state` to `g5-keymap-ready` (G5 readiness signal). |
| `web/tree.js` | Module stub that flips `#tree-view[data-state="ready"]` after the DOM is available (G5 readiness signal). |
| `web/{state,api,breadcrumb,…}.js` | Module stubs (`export {};`). |
| `scripts/seed_db.py` | Rebuilds `taxa.db`. Idempotent. |
| `scripts/check_http_status.py` | Controlled verifier: parses `curl -w '%{http_code}'` output and validates against `expect`. Fail-closed on mismatch. |

## Slice 1 — G3 legacy pre-cut readiness (PASS via PR #116)

The G3 slice passes every `verification.command` against the controlled
fixture (`web/` served by `python -m http.server` on an isolated free
port via `--fixture-web-root`) with HTTP-shape fail-closed routing
through `scripts/check_http_status.py`. See PR #109 + #111 + #115 + #116
for the canonical 26 / 26 consumer PASS record.

## Slice 2 — G5 hydration-readiness markers (chain PR 1)

The G5 slice adds deterministic hydration-readiness markers to the
fixture's HTML/JS so chain PR 2 can record a baseline via Playwright
without depending on production `web/` bytes. The markers are the public
contract; the controlled FastAPI launcher that mounts the fixture is
restored from a preserved external patch in chain PR 2.

### Markers

| Marker | Where | Set by |
|---|---|---|
| `data-testid="g5-shell-ready"` | `<body>` (static) | `web/index.html` |
| `data-testid="g5-tree-ready"` | `<div id="tree-view">` (static) | `web/index.html` |
| `data-testid="g5-search-ready"` | `<input id="search">` (static) | `web/index.html` |
| `data-testid="g5-keymap-ready"` | `<span hidden>` near the top of `<body>` (static; its own element — body already carries `g5-shell-ready` and the HTML5 parser drops subsequent duplicate attributes, so a second `data-testid` on body would be silently lost) | `web/index.html` |
| `data-state="ready"` on `#tree-view` | dynamic | `web/tree.js` (DOMContentLoaded or now) |
| `data-state="g5-keymap-ready"` on `<body>` | dynamic | `web/app.js` (now or DOMContentLoaded) |

Markers are deterministic (no timestamps, no random ids) so chain PR 2's
baseline-vs-candidate diffs stay clean.

### Out of scope (chain PR 2 owns these)

- The controlled FastAPI launcher (`scripts/g5_legacy_asgi.py`).
- The actual `scripts/measure_hydration.py` producer.
- The Playwright + Lighthouse capture loop.
- The `parity-reports/<date>/hydration.json` schema + writer.
- The candidate-vs-baseline join + ±10% threshold assertion.

## Scope boundary

- **In (G3)**: minimal DB + minimal `web/` + the controlled-verifier helper.
- **In (G5 / chain PR 1)**: hydration-readiness markers in the fixture's
  HTML/JS + regression tests for them.
- **Out**: root `web/`, root `Makefile`, `extension/manifest.json`,
  product source, atomic cutover, Approach A / B / C selection,
  controlled FastAPI launcher, Lighthouse / Playwright capture.

## Rebuild & test

```sh
python tools/g3-legacy-fixture/scripts/seed_db.py
.venv/bin/python -m pytest tests/test_g3_legacy_fixture.py -v
```
