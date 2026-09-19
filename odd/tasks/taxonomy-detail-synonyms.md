# Restore taxonomy detail Synonyms

## Objective
Port the native DetailPanel Synonyms tab to React, exposing canonical synonym records from the dedicated FastAPI endpoint.

## Decisions
- Keep the React always-visible tab pattern with loading, empty, error, and retry states.
- Request `limit=200`; respect server ordering and do not render wire `status`.
- Keep the per-taxon cache across source switches, matching the source-agnostic legacy endpoint behavior.
- Use `SynonymName`, `.synonym-tab`, and scoped rank-chip CSS, mirroring Vernaculars conventions.

## Scope
- Add typed `/api/taxon/{id}/synonyms?limit=200` projection.
- Enable and eagerly load Synonyms tab per selection.
- Render native header/count and rank/scientific-name/authorship rows.
- Preserve Overview, Search, Vernaculars, tree navigation and active-tab memory.

## Non-goals
Backend/legacy changes; source filtering; client sorting/pagination; status UI; synonym linking; Folder/Distribution; production cutover.

## Tasks
- [ ] ODD-TDSYN-001 Implement native Synonyms data contract and UI.
- [ ] ODD-TDSYN-002 Verify and publish Synonyms slice.

## Progress
Created after source mapping. No implementation is written yet.