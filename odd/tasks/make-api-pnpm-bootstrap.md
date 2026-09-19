# Align API startup with pnpm

## Objective
Make `make api` start the legacy FastAPI server without running npm installation on every invocation, while preserving an explicit CSS build workflow.

## Scope
- Replace npm-based CSS bootstrap with the repository's pnpm lockfile workflow.
- Ensure `make api` does not install Node dependencies as a prerequisite.
- Add narrow Makefile contract coverage and validate immediate API startup.

## Non-goals
- React/FastAPI production cutover, dependency upgrades, package-lock migration, or altering user-owned `next-env.d.ts` drift.

## Tasks
- [x] ODD-MAP-001 Separate API startup from frontend dependency installation.
  - Outcome: `Makefile` `api:` target no longer depends on `css:`; the Uvicorn invocation runs immediately. `css:` now uses `pnpm install --frozen-lockfile` + `pnpm run build:css`, aligned with `pnpm-lock.yaml` (ODD-TW-001 lockfile). CSS build stays explicit and separate.
  - Evidence: `make -n api` produces a single line `.venv/bin/python3 -m uvicorn api.server:app --host 127.0.0.1 --port 8765` with no `pnpm install`, `npm install`, or `build:css` leakage. `tests/test_makefile_api.py` adds 10 hermetic dry-run + contract assertions covering target/dependency/script/lockfile invariants (all passing). Live `make api` started Uvicorn on port 8765, `/api/health` returned `{"status":"ok","taxa":5680524,...}` within 2 s, and the process was terminated cleanly (port freed).
- [x] ODD-MAP-002 Verify and publish the tooling repair.
  - Verification: independent verifier approved; 192 related tests and Makefile dry-run contracts passed.
  - Delivery: PR #317 (`fix/make-api-pnpm-bootstrap` → `develop`) merged via commit `ed6d4a4`.

## Progress
ODD-MAP-001 and ODD-MAP-002 are merged to `develop` through PR #317 (commit `ed6d4a4`). The unrelated Next-generated `next-env.d.ts` drift remains deliberately excluded.

## Next step
The ODD slice is closed. Read [`openspec/changes/complete-taxa-frontend-migration/SUPERSEDED.md`](../openspec/changes/complete-taxa-frontend-migration/SUPERSEDED.md) for the delivered-evidence summary and the remaining production cutover gap (`web/` to built `out/`, FastAPI mount, legacy removal, validation gates).