# React E2E harness

Isolated private workspace (PR **5c.2-B.1a** + **5c.2-B.1b-i**) for capturing a live React `FileExplorer` mount against a caller-provided **already-running** HTTP origin. Unreachable from production by design.

## Scope

- Next.js scaffold mounts `FileExplorer` from `@taxa/research` against a deterministic synthetic non-null taxon id (`1`); `next build` produces `out/index.html`.
- Capture CLI (`scripts/run.mjs`) + Chromium navigation runner (`scripts/chromium-driver.mjs`) drive the explicit origin and write an atomic, timestamped JSON evidence artifact under `<outputRoot>/<UTC-timestamp>/evidence.json` on success only.

## Usage

```bash
# 1. Build the static export.
npm ci && npm run build

# 2. Serve out/ over plain HTTP on any port (caller's choice;
#    no default port is baked into the harness).
( cd out && python3 -m http.server 8765 ) &

# 3. Capture. Both flags are mandatory; --origin must be http(s)
#    with no path; --output-root is the parent of the timestamped
#    run directory.
npm run capture -- \
    --origin      http://127.0.0.1:8765 \
    --output-root ../../parity-reports/react-e2e
```

Failure modes that **do not** produce an evidence artifact (fail-closed): missing `--origin` / `--output-root`; `file://`, non-http(s), or origin paths; output collisions; 5xx / network / navigation / timeout errors from Chromium; React data-contract assertion failures (`data-harness-root`, `data-harness-surface`, non-null `data-harness-taxon-id`, `[data-explorer="ready"]`, both `[data-pane]` slots, `input[data-search-input]`, at least one `[data-file-path]`).

## Deferred (out of scope here)

Fixture API server, export HTTP server, `make capture-react-e2e`, hermetic driver tests, production source/API changes, legacy E2E selector modernization + `web/*.{html,js,css}` + `tailwind.config.js` legacy deletion, and G4 aggregation. **G4 / G3 Tier-2 / cutover remain blocked**; this PR is not a G4 flip.
