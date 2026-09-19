# Restore taxonomy detail Folder

## Objective
Port the native DetailPanel Folder tab to React, including safe preview, materialization, opening, and copying of taxonomy research folders.

## Decisions
- Invalidate preview cache when source changes; preview paths are source-specific.
- Require an explicit confirmation before creating folders, intentionally safer than legacy.
- Render accumulated native paths per segment.
- Use inline success/error states only; no new toast dependency or transient notification system.
- Defer Browser refresh after create and tree kebab-folder wiring to their dedicated surfaces.
- Deliver as one cohesive PR; renderer, side-effect handlers, cache, CSS, and tests form one behavior unit.

## Scope
- Typed materialize-preview, materialize, and open-folder FastAPI client contracts.
- Enable Folder tab with loading/error/preview/create/open/copy/confirmation states.
- Source-aware preview cache, create refresh, clipboard handling, native accumulated path display, and focused tests.

## Non-goals
Backend/legacy changes, Browser tab refresh, tree kebab action, new toast dependency, folder filters, and production cutover.

## Tasks
- [x] ODD-TDFOLDER-001 Implement native Folder contract and UI.
- [x] ODD-TDFOLDER-002 Verify and publish Folder slice.

## Progress
- ODD-TDFOLDER-001 is implemented on `develop`: `api.ts` defines validated preview/materialize/open contracts; `TaxonomyTree.tsx` owns the source-aware preview and side-effect state; `DetailPanel.tsx` enables and wires the tab; `FolderTab.tsx` renders loading, retryable error, preview, confirmation, create, open, copy, and accumulated-path states; `globals.css` supplies the scoped presentation styles. Focused contracts and UI coverage are included in `tests/test_taxonomy_infra.py` and `tests/test_visible_taxonomy_tree.py`.
- ODD-TDFOLDER-002 was published through the merged tracker/contracts/UI PR chain (#319–#321; commits `f4f1c07`, `bb38615`, `9fc5b37`, merged to `develop` via `ed9184e`, `c4428d9`, and `32ec9a3`). Independent read-only verification on current `develop` passed 260 focused tests and 168 module-boundary tests. The optional API smoke, parity harness, and Next static build were not run in this reconciliation pass.

## Next step
Choose the next unimplemented taxonomy-detail slice or reconcile the remaining historical ODD trackers before starting new implementation.