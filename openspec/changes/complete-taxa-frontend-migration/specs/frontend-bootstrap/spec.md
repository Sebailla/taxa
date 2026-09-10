# Frontend Bootstrap Specification

> Domain: `frontend-bootstrap`. Modified per the proposal but no
> canonical spec exists yet, so this file is a **full new domain
> spec** (per OpenSpec workflow step 3). Authored under
> `complete-taxa-frontend-migration`. The canonical home is the
> change folder; archive copies this file verbatim into
> `openspec/specs/frontend-bootstrap/spec.md` at activation.

## Purpose

The frontend bootstrap binds the new Next.js static export to
FastAPI's existing `StaticFiles` mount, wires the `make api` build
pipeline so the build artifact exists before uvicorn binds the
port, and enforces the runtime / Node-version contract. The
contract preserved against the legacy build is **single-origin
ownership of `127.0.0.1:8765`** — `WEB_DIR` is repointed, the
mount signature stays unchanged, the uvicorn bind stays unchanged,
and there is no silent fallback to the legacy vanilla build on
failure.

## Requirements

### Requirement: `WEB_DIR` repointed at the Next.js static export

The system MUST repoint the `WEB_DIR` constant at
`api/server.py:54` to the directory produced by `next build`, and
the rest of the FastAPI source MUST stay unchanged.

#### Scenario: `WEB_DIR` resolves to the static export

- GIVEN `api/server.py:54` declares `WEB_DIR = Path(__file__).parent.parent / "web"`
- WHEN the apply worker ships the cutover
- THEN `WEB_DIR` resolves to `<repo-root>/out/` (the Next.js
  static export)
- AND the rest of `api/server.py` is byte-identical except for the
  `WEB_DIR` constant declaration and any middleware strictly
  required to wire Approach A

#### Scenario: Mount signature stays unchanged

- GIVEN `api/server.py:1815` declares
  `app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")`
- WHEN the apply worker ships the cutover
- THEN the mount signature stays byte-identical
- AND the `html=True` SPA fallback stays byte-identical
- AND no second mount is introduced

### Requirement: No second dev-server port

The system MUST bind uvicorn to `127.0.0.1:8765` and MUST NOT open
any second dev-server port.

#### Scenario: `make api` binds only 8765

- GIVEN `make api` invokes `next build` then uvicorn
- WHEN the apply worker inspects the open listeners
- THEN uvicorn is bound to `127.0.0.1:8765`
- AND no second uvicorn / Next.js dev server / Node process is
  bound to any other TCP port
- AND the Chrome extension `host_permissions` stays at
  `["http://localhost:8765/*"]`

#### Scenario: No second origin in the extension manifest

- GIVEN `extension/manifest.json::host_permissions` is
  `["http://localhost:8765/*"]` and `content_scripts.matches` is
  `["http://localhost:8765/*"]`
- WHEN the apply worker ships the cutover
- THEN `host_permissions` is unchanged
- AND `content_scripts.matches` is unchanged
- AND no second origin, no new port, no new URL is added to the
  extension manifest

### Requirement: Build pipeline runs before uvicorn

The system MUST ensure the Next.js build artifact exists before
uvicorn binds the port, with no silent fallback to legacy.

#### Scenario: `make api` runs `next build` first

- GIVEN the `Makefile::api` target
- WHEN the user runs `make api`
- THEN the target invokes the Next.js build step first
- AND only after `next build` exits `0` does the target invoke
  uvicorn
- AND if `next build` exits non-zero, the target exits non-zero
  **before** uvicorn binds

#### Scenario: Missing build artifact fails fast

- GIVEN a clean clone (no `out/` directory exists)
- WHEN the user runs `make api`
- THEN the build step runs and produces `out/`
- AND uvicorn only binds after `out/index.html` and
  `out/_next/static/chunks/**` exist with non-zero bytes
- AND there is **no** quiet fallback to the legacy `web/` files

#### Scenario: Node runtime version check

- GIVEN `package.json::engines.node` is `">=20.9.0"`
- WHEN the user runs `make api`
- THEN `scripts/check-runtime.mjs` runs first
- AND the check exits non-zero if `node --version` is below
  `20.9.0`
- AND the Makefile target exits non-zero **before** uvicorn
  binds on Node version mismatch

### Requirement: Active-consumer manifest atomicity

The system MUST update every active consumer enumerated in the
predecessor's `design.md::§3.1` in the same release as the
`WEB_DIR` repoint.

#### Scenario: All 26 §3.1 consumers updated together

- GIVEN the predecessor's `design.md::§3.1` enumerates 21 active
  consumers of the FastAPI web mount and 5 active consumers of
  `web/search_urls.js`
- WHEN the apply worker ships the cutover
- THEN every active consumer is updated in the same release unit
- AND no consumer remains "active" against a path the cutover
  deletes
- AND the cutover-manifest.json `activation_status` flips to
  `selected` for every consumer that the cutover activates

#### Scenario: AC-21 contract test still green

- GIVEN `tests/test_smoke.py::test_search_engine_contract`
  (AC-21) reads the search-engines literal
- WHEN the apply worker ships the cutover
- THEN the test still passes
- AND if the literal moved from `web/search_urls.js` to
  `src/data/search-engines.js`, the test's `open()` path is
  updated in the same release
- AND the byte shape (key, label, with_authorship, ordering)
  stays identical to the legacy literal
- AND the server-side mirror at `api/server.py::_SEARCH_ENGINES`
  stays byte-identical to the literal's matching fields

### Requirement: Tailwind 4 CSS-first config replaces `tailwind.config.js`

The system MUST delete `tailwind.config.js` and replace it with
the Tailwind 4 CSS-first `@theme` block inside `globals.css`.

#### Scenario: `tailwind.config.js` deleted at activation

- GIVEN `tailwind.config.js` ships in the legacy `package.json`
- WHEN the apply worker ships the cutover
- THEN `tailwind.config.js` is deleted
- AND the Tailwind 4 `@theme` block lives in `globals.css`
- AND the package.json removes `autoprefixer`, `postcss`,
  `@tailwindcss/forms`
- AND the package.json adds `tailwindcss@^4`, `next@^16`,
  `react@^19`, `react-dom@^19`, the TS toolchain (`typescript@>=5.1.0`,
  `@types/react@^19`, `@types/react-dom@^19`, `@types/node`)

### Requirement: Atomic cutover unit

The system MUST change the cutover unit atomically — a single
release unit changes the `WEB_DIR` constant, every active
consumer, the build pipeline, and the build artifact together.

#### Scenario: Cutover is one release

- GIVEN the predecessor's `design.md::§1` records the atomic
  cutover as a single release unit
- WHEN the apply worker ships the cutover
- THEN the following change together in one release:

  1. `WEB_DIR` constant in `api/server.py:54`.
  2. Every active-consumer update enumerated in the
     predecessor's `design.md::§3.1` (imports, the AC-21 reader
     path, every test consumer).
  3. The `Makefile::api` and `Makefile::web` targets.
  4. The build artifact (`out/`) itself.

- AND no partial cutover is supported under this domain

#### Scenario: Subset revert is not supported

- GIVEN the cutover landed atomically
- WHEN the maintainer reverts only one of the four sets
- THEN the system is broken (consumers reference deleted paths,
  the SPA shell or AC-21 contract test fails)
- AND `git revert <cutover-sha>` is the **only** supported
  rollback path

### Requirement: Rollback unit

The system MUST support rollback by a single `git revert` that
restores the legacy vanilla build atomically.

#### Scenario: `git revert <cutover-sha>` restores the legacy build

- GIVEN the cutover landed
- WHEN the maintainer runs `git revert <cutover-sha>`
- THEN `web/index.html`, `web/app.js`, the 18 `web/*.js` modules,
  `web/dist/tailwind.css`, and `tailwind.config.js` are restored
  atomically
- AND `package.json` reverts to the legacy dependency state
- AND `npm ci` reproduces the legacy lock
- AND `make api` regenerates `web/dist/tailwind.css` from the
  reverted source
- AND `make smoke` returns to the pre-migration baseline (63
  passed, 8 skipped on the same fixture set)

#### Scenario: No data migration required

- GIVEN no DB schema change ships in this change
- WHEN the maintainer runs `git revert <cutover-sha>`
- THEN no data migration is required to roll back
- AND `data/db/taxa.db` is unchanged by the cutover and the
  rollback

#### Scenario: Extension continuity through rollback

- GIVEN the extension talks to `http://localhost:8765` before,
  during, and after the cutover
- WHEN the maintainer runs `git revert <cutover-sha>`
- THEN the extension keeps working without a `manifest.json`
  update
- AND `host_permissions` stays at
  `["http://localhost:8765/*"]`

## Notes

- The predecessor's `design.md::§1` ("G1 boundary decision
  recorded") and `design.md::§3.1` ("Active-consumer inventory")
  are imported as planning history — this domain spec mirrors
  them, it does not re-derive them.
- The cutover-manifest.json at
  `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
  is the machine-readable source of truth for the 26 active
  consumers. Activation flips `activation_status` from
  `selected` (legacy pre-cut) to a post-cut activation record;
  the apply phase owns that flip.
- The proposal's "Out of scope" list (backend rewrite, ETL
  pipeline, SEO, new routes, coverage tooling, visual redesign)
  applies to this domain unchanged.