# G3 Legacy Fixture (diagnostic only)

Minimal, self-contained, disposable G3 legacy fixture for controlled
HTTP-status enforcement testing. **Not part of the product.** Unreachable
from production by design.

## Contents

| Path | Purpose |
|---|---|
| `taxa.db` | Pre-seeded SQLite: 10 `taxon` + 8 `vernacular` rows. Schema mirrors production v1+v2. |
| `web/index.html` | Minimal HTML referencing `dist/tailwind.css` + `app.js`. |
| `web/dist/tailwind.css` | Required CSS asset (manifest's `mount-runtime-link-tag-css-003` consumer). |
| `web/app.js` | Minimal entry importing 10 sibling module stubs. |
| `web/{state,api,tree,…}.js` | Module stubs (`export {};`). |
| `scripts/seed_db.py` | Rebuilds `taxa.db`. Idempotent. |
| `scripts/check_http_status.py` | Controlled verifier: parses `curl -w '%{http_code}'` output and validates against `expect`. Fail-closed on mismatch. |

## Scope boundary

- **In**: minimal DB + minimal `web/` + the controlled-verifier helper.
- **Out**: FastAPI, root `web/`, root `Makefile`, `extension/manifest.json`,
  product source. Does NOT select Approach A / B / C and does NOT activate
  any cutover.

## Rebuild & test

```sh
python tools/g3-legacy-fixture/scripts/seed_db.py
.venv/bin/python -m pytest tests/test_g3_legacy_fixture.py -v
```
