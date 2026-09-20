# Single-command local development launcher

## Objective
Provide one local command that starts the FastAPI backend and the Next.js development server, then stops both reliably when the user exits.

## Problem
The current Next.js development flow requires two terminals: `make api` for FastAPI on port 8765 and `pnpm dev:local` for Next.js on port 3000. This is cumbersome and leaves child-process cleanup manual.

## Scope
- Add a standard-library Python supervisor at `scripts/dev.py`.
- Add `make dev` as the single public entry point.
- Keep `make api`, `pnpm dev`, and `pnpm dev:local` unchanged.
- Start FastAPI first, wait for `/api/health`, then start Next.js with `NEXT_PUBLIC_TAXA_API_ORIGIN=http://127.0.0.1:8765`.
- Forward SIGINT/SIGTERM and stop both child processes; propagate unexpected child failures.
- Add focused, hermetic tests and document the command.

## Constraints
- No new runtime dependency.
- Do not change the existing `make api` contract or port binding.
- The launcher must avoid reliance on GNU Make `.ONESHELL`, which is not portable to macOS GNU Make 3.81.
- No commit, push, or PR is authorized.

## TDD and delivery
- TDD mode: ordinary focused regression tests; source: repository test conventions.
- Delivery strategy: exception-ok — user selected one cohesive PR.
- Authored change: ~1,000 lines including the supervisor, hermetic lifecycle tests, docs, and this record. Size exception accepted because splitting the supervisor from its process-lifecycle proofs would reduce reviewability.

## Tasks
- [x] ODD-DEV-001 Add a hermetic supervisor contract test for readiness, cleanup, and failure propagation.
  - Route: delegated writer (multi-file write rule).
  - Evidence: observed RED (`ModuleNotFoundError: No module named 'scripts.dev'`) before the launcher existed; 17 focused tests now pass, including the keyword-only readiness regression.
- [~] ODD-DEV-002 Implement `scripts/dev.py` and expose it as `make dev`.
  - Route: delegated writer (multi-file write rule).
  - Status: implementation and focused static checks are GREEN. `scripts/dev.py` starts FastAPI, waits for `/api/health`, launches `pnpm run dev:local` with the local API origin, and stops both process groups. Parent readback found and repaired a default-path `TypeError`: `timeout_s` / `poll_s` are now passed by keyword to `wait_for_health` and are pinned by two regressions.
  - Evidence: `python3 -m pytest tests/test_dev_launcher.py -q` → 17 passed; `python3 -m pytest tests/test_makefile_api.py -q` → 10 passed; `make -n dev` → `.venv/bin/python3 scripts/dev.py`; `git diff --check` → clean; LSP → clean for Python files.
  - Pending: a fresh delegated verifier twice stalled in its shell tool without emitting evidence. Do not claim independently verified or run an unbounded `make dev`; next verification must use a timeout-bounded live smoke or repair the verifier runtime.
- [x] ODD-DEV-003 Document the single-command developer workflow.
  - Route: delegated writer (multi-file write rule).
  - Evidence: README now leads with `make dev`, names the Next.js (`localhost:3000`) and FastAPI (`127.0.0.1:8765`) URLs, and retains the `make api` fallback.

## Acceptance criteria
- `make dev` launches FastAPI on `127.0.0.1:8765` and Next.js on `localhost:3000` without a second terminal.
- The frontend is configured with `NEXT_PUBLIC_TAXA_API_ORIGIN=http://127.0.0.1:8765`.
- Ctrl-C stops both child processes.
- If either child exits unexpectedly, the other is stopped and the launcher exits non-zero.
- `make api` remains prerequisite-free and its existing test contracts stay intact.

## Progress
- Exploration complete: a Python supervisor is preferred over a Makefile shell recipe because the repository explicitly supports macOS GNU Make 3.81, where `.ONESHELL` is not reliable.
- Work-unit commit: `774f577` — `feat(dev): add unified local launcher` (supervisor, lifecycle tests, `make dev`, docs, and task record).
- Native assessment of `82e67db..774f577` is high risk due to a process boundary; it requires writer self-verification plus an independent verifier. Final independent/live verification remains pending because fresh verifier invocations stalled before returning evidence. Generated `next-env.d.ts` drift from local Next dev is intentionally excluded.
- User authorized a single size-exception PR for approved issue #74, but publication remains blocked until the required high-risk verification evidence exists.
