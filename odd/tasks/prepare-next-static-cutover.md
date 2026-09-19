# Prepare a reversible Next static-export cutover

## Objective
Prove that the current Next frontend can be built and served as static assets without changing FastAPI's legacy `web/` mount or deleting legacy files.

## User decision
Use a reversible preparation unit before the production cutover. The cohesive test, tracker, and generated-evidence ignore rules total 413 added lines; the user accepted a size exception rather than splitting its contract from its evidence.

## Scope
- Add automated static-export and isolated static-mount contracts for `out/`.
- Capture build-inventory and cutover-rehearsal evidence without changing production routing.
- Preserve `WEB_DIR = web`, `Makefile::api`, AC-21 reader, and all legacy files.

## Non-goals
- Repointing FastAPI to `out/`, changing `make api`, or deleting `web/`.
- Porting AC-21, Browser state, or unimplemented research features.
- Closing G4, G5, or G6 validation gates.

## Allowed edit surfaces
- `.gitignore`
- `tests/test_static_export_contract.py`
- `odd/tasks/prepare-next-static-cutover.md`

## Tasks
- [x] ODD-CUTPREP-001 Add a static-export contract without production cutover.
  - `tests/test_static_export_contract.py` pins the `next.config.mjs`
    G2 keys (`output: "export"`, `images.unoptimized: true`,
    `trailingSlash: false`, `reactStrictMode: true`), generates a
    deterministic synthetic `out/` in `tmp_path`, serves it through an
    isolated `ThreadingHTTPServer` on an ephemeral 127.0.0.1 port, and
    proves `/`, a hashed `_next/static/chunks/*.js`, and a hashed
    `_next/static/chunks/*.css` are reachable. The test never imports
    or mutates `api.server`, never changes `WEB_DIR`, never alters the
    `Makefile`, and never deletes legacy assets. A read-only optional
    test validates the repo-root `out/` shape when present (skips
    cleanly otherwise). 8/8 tests pass.
- [x] ODD-CUTPREP-002 Run build/rehearsal evidence and independently verify the preparation.
  - Evidence: independent verification passed 8 static-export tests, 104 legacy mount/fixture guards, `pnpm exec next build`, `scripts/verify_build.py --out out --node-min 20.9.0`, and `scripts/rehearse_cutover.py --dry-run` (26 consumers, no validation errors, non-executing). `WEB_DIR` remains `web`; production routing files and legacy assets were unchanged. `.gitignore` now keeps the reproducible `build.log`, `docs/g6/`, and `out/` evidence local-only.
  - Work-unit commit: `test(cutover): prepare static export evidence`.

## Next step
Use this preparation evidence as an input to the separate prerequisite and production-cutover units; do not repoint FastAPI or retire `web/` until their gates are closed.

## Acceptance criteria
- The test proves `next.config.mjs` remains configured for static export and validates a generated `out/` without touching FastAPI's mounted directory.
- `pnpm exec next build` and `scripts/verify_build.py` succeed at the repository root.
- A temporary isolated static server proves the exported entry HTML and hashed JS/CSS assets are reachable.
- `scripts/rehearse_cutover.py --dry-run` succeeds; its result remains explicitly non-executing.
- Reproducible build and rehearsal evidence remains local-only and ignored.
- Existing legacy mount and fixture tests remain green.
