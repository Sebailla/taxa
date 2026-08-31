# G4 capture (slice 1)

URL-parametrized capture producer for the G4 Lighthouse parity evidence slice.
**Diagnostic, not part of the product.** Unreachable from production by design.

## Contract

- `tools/g4-capture/scripts/capture.mjs` — ESM library + CLI. Takes `--url`,
  `--manifest`, `--out`; optional `--dry-run`. Validates the URL against the
  manifest, runs (or dry-runs) Lighthouse, writes `evidence.json` +
  `manifest.snapshot.json` atomically to `--out`. Records provenance (node
  version, lighthouse version, chrome version, host, capturedAt).
- `tools/g4-capture/package.json` — pinned `lighthouse@12.2.1` +
  `chrome-launcher@1.2.1`. Private + ESM. Independent of root `node_modules/`.
- `tests/fixtures/g4/corpus/` — deterministic HTML corpus. `manifest.json`
  declares the URL + expected content sha256.
- `tests/fixtures/g4/sqlite/` — versioned SQLite fixture (`taxa-fixture.db`)
  seeded by `scripts/seed_fixture.py`; `MANIFEST.json` +
  `taxa-fixture.db.sha256` pin the expected hash.
- `parity-reports/` — unversioned. Raw Lighthouse reports, console logs, and
  atomic output live here (gitignored).

## Scope (slice 1)

**In:** producer framework, manifest validation, atomic write, provenance
recording, dry-run capture, versioned SQLite fixture, deterministic HTML
corpus, isolated pinned workspace.

**Out:** real Lighthouse execution (G4-capture-2), full
`scripts/verify_parity.py` + `tests/test_verify_parity.py` (G4-capture-3),
Approach A / B / C atomic-cut selection (evidence-gated by G2/G4/G5/G6 PASS;
static export remains unselected), `Makefile` target, CI wiring.

## Build & test

```sh
python tools/g4-capture/scripts/seed_fixture.py
.venv/bin/python -m pytest tests/test_capture_parity.py -v
```