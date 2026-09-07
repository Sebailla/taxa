# G4 capture (slice 1 + capture-2)

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

## Slice 2 — real Lighthouse runner

The slice-2 contract adds a real runner to the producer without changing the
slice-1 CLI surface or the `--dry-run` path. The runner is **dynamic** —
`lighthouse` and `chrome-launcher` are imported lazily inside `runLighthouse`
so the slice-1 `--dry-run` and the test harness stay free of browser deps
until the real path is exercised.

### Fixed configuration (locked)

- **Categories:** `performance`, `accessibility`, `best-practices`, `seo`.
  Exposed via `fixedCategories()`; pinned in
  `FIXED_LIGHTHOUSE_CONFIG.settings.onlyCategories`.
- **Form factor:** `desktop` with frozen `screenEmulation` (1350×940 @1×) and
  `throttling` (40 ms RTT, 10 240 kbps throughput, 1× CPU). Mobile throttling
  is deliberately not used so audit scores are deterministic across hosts.
- **`extends: "lighthouse:default"`** fills in any unspecified setting.

Exposed helpers (importable from `capture.mjs`):

| Symbol | Purpose |
| --- | --- |
| `fixedCategories()` | Returns a fresh copy of the locked four-category set. |
| `fixedLighthouseConfig()` | Returns a deep clone of the locked config object. |
| `chromeVersionFromUserAgent(ua)` | Parses the Chrome version from a Lighthouse `userAgent` (returns `"unknown"` if absent). |
| `mapLhr(lhr)` | Deterministic LHR → evidence mapping (locked categories, sorted warnings, throws on non-object input). |
| `runLighthouse({ url, manifestEntry })` | Real runner: dynamic-imports `lighthouse` + `chrome-launcher`, launches headless Chrome, runs the fixed config, returns the raw LHR. |

### Deterministic mapped evidence

`mapLhr()` produces a stable evidence payload:

- Always emits **all four** fixed-category slots, in fixed order, with
  `score: null` for any slot the runner's LHR omitted — so downstream hashers
  see a stable key set regardless of which audits Lighthouse actually scored.
- Sorts `runWarnings` lexicographically so the same warning set yields the
  same byte order across runs.
- Throws on non-object input so a malformed runner cannot silently write
  `null` evidence.

### Execution provenance

`provenance.chromeVersion` is parsed from `LHR.userAgent`
(`chromeVersionFromUserAgent`). `provenance.lighthouseVersion` is read from
`LHR.lighthouseVersion`. Both are written into `evidence.json::provenance`
alongside `nodeVersion`, `host`, and `capturedAt`.

### Failure semantics (fail-closed)

If the runner throws (no browser, lighthouse not installed, chrome-launcher
failure, LHR missing, etc.) the rejection propagates out of `capture()` before
`atomicWrite()` runs. The pre-existing `--out` directory is left untouched
and no `evidence.json` / `manifest.snapshot.json` is published. Verified by
`test_real_runner_failure_does_not_publish_or_replace_output` (hermetic —
inject a runner that throws).

## Scope

**In (slice 1):** producer framework, manifest validation, atomic write,
provenance recording, dry-run capture, versioned SQLite fixture, deterministic
HTML corpus, isolated pinned workspace.

**In (slice 2 / capture-2):** dynamic `lighthouse` + `chrome-launcher`
runner, fixed configuration/categories, deterministic `mapLhr()` mapping,
execution provenance (`chromeVersion` from LHR `userAgent`), hermetic tests
with injected synthetic LHR, fail-closed output on runner failure. `--dry-run`
is retained unchanged.

    **Out:** full `scripts/verify_parity.py` + `tests/test_verify_parity.py`
    (G4-capture-3), Approach A / B / C atomic-cut selection (evidence-gated by
    G2/G4/G5/G6 PASS; static export remains unselected), `Makefile` target, CI
    wiring.

    ## Slice 3 — G4 parity-navigation producer (first G4 parity slice)

    URL-parametrized parity producer that drives both a legacy and a candidate
    HTTP origin through declared navigation paths, and writes a fail-closed
    `navigation.json` per side. **Diagnostic, not part of the product.**

    - `tools/g4-capture/scripts/parity_navigation.mjs` — ESM library + CLI.
      Takes `--legacy-origin`, `--candidate-origin`, `--paths` (comma-separated),
      `--output-root`, optional `--manifest`; rejects `file://` and any
      non-http(s) origin; writes `<outputRoot>/<UTC-timestamp>/{legacy,
      candidate}/{navigation.json,manifest.snapshot.json,run.json}` atomically
      via the same sibling-backup strategy `capture.mjs` uses.
    - `navigation.json` schema matches `scripts/verify_parity.py`:
      `{schema_version: "1.0.0", captured_at: "YYYY-MM-DDTHH:MM:SSZ", paths:
      [{path: str, status: int}, ...]}`.
    - Run-directory names use `YYYY-MM-DDTHH-MM-SSZ` (filename-safe; the colon
      would not survive Windows paths); the `captured_at` value lives in the
      JSON and uses the seconds-precision Z form matching
      `scripts/verify_parity.py::ISO_FMT`.
    - Playwright is pinned alongside the existing `lighthouse` +
      `chrome-launcher` deps; the runner is dynamically imported inside
      `defaultRunNavigation` so the test harness stays free of browser deps
      until the real path runs.
    - Hermetic tests inject a synthetic `runFn` (and a fixed `now()`); no
      real browser, no live network, no installed chromium binary is required
      in CI.

    ### Fail-closed guards (slice 3)

    - **Missing/invalid origins**: rejects empty strings, `file://`, `ftp://`,
      `javascript:`, malformed URLs, and any origin that carries a path
      component (the transport is origin-only). Verified by
      `test_parity_navigation_validate_origin_rejects_non_http` +
      `test_parity_navigation_validate_origin_rejects_trailing_path`.
    - **Equal sides**: rejects `--legacy-origin == --candidate-origin` so a
      broken candidate can never silently "pass" against itself.
      `test_parity_navigation_capture_rejects_equal_origins`.
    - **Path mismatch**: when a manifest is supplied, every declared path
      MUST appear in `manifest.paths`. An undeclared path is rejected before
      any write. `test_parity_navigation_path_mismatch_rejected`.
    - **Unavailable runner / 5xx / network error**: if either side returns
      a 5xx status, status `0` (navigation timeout, network failure), or the
      injected runner throws, the run fails closed before any artifact is
      written. `test_parity_navigation_capture_rejects_5xx_from_either_side`
      + `test_parity_navigation_capture_rejects_network_failure`.
    - **Path-outcome drift**: identical `(path, status)` per side is required;
      a drift between legacy and candidate fails closed at the producer
      boundary so a broken run never publishes a "clean" navigation.json for
      either side. `test_parity_navigation_capture_path_outcome_drift_fails_closed`.
    - **Output collision**: refuses to overwrite a pre-existing
      `<outputRoot>/<UTC-timestamp>/` directory; the prior run stays intact.
      `test_parity_navigation_capture_rejects_output_collision`.

    ### Non-closing scope (still pending)

    The other four G4 reports (`api`, `search`, `a11y`, `browser-state`),
    the pairwise aggregator wiring (`scripts/verify_parity.py` already exists
    and validates the navigation schema), the umbrella `make parity` target,
    and the G4 gate flip all remain pending. This slice ships the navigation
    producer + the first hermetic test surface; G4 stays **blocked** in
    `apply-progress.md` until all five reports are captured.

    ## Build & test

    ```sh
    python tools/g4-capture/scripts/seed_fixture.py
    .venv/bin/python -m pytest tests/test_capture_parity.py -v
    ```

    Hermetic tests inject a synthetic LHR (or a runner that throws) — no real
    browser is required in CI. The new parity-navigation slice follows the
    same hermetic pattern (injected `runFn` + fixed `now()`).
