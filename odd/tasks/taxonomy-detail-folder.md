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
- [ ] ODD-TDFOLDER-001 Implement native Folder contract and UI.
- [ ] ODD-TDFOLDER-002 Verify and publish Folder slice.

## Progress
Created after legacy/API mapping and explicit filesystem UX decisions.