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
- [x] ODD-TDSYN-001 Implement native Synonyms data contract and UI.
- [x] ODD-TDSYN-002 Verify and publish Synonyms slice.

## Progress
- ODD-TDSYN-001 is implemented on `develop`: `api.ts` validates and projects `SynonymName` records through `fetchSynonyms`; `TaxonomyTree.tsx` eagerly loads the source-agnostic per-taxon cache; `DetailPanel.tsx` enables and dispatches the tab; `SynonymTab.tsx` renders loading, empty, retryable error, and loaded states with rank, scientific-name, and authorship rows while preserving server ordering and not rendering wire `status`; `globals.css` supplies the scoped rank-chip cascade. Focused contract, UI, and style coverage lives in `tests/test_taxonomy_infra.py`, `tests/test_visible_taxonomy_tree.py`, and `tests/test_research_styles.py`.
- ODD-TDSYN-002 was published through merged PRs #314–#316 (commits `1a07156`, `6747c65`, `ef145eb`, merged to `develop` via `61b710f`, `fd64fe2`, and `ea9bc09`). Independent read-only verification on current `develop` passed 18 synonym-focused tests and 421 related tests across the taxonomy contracts, UI, styles, module boundaries, domain purity, restricted imports, and app shell. The live API smoke and regenerated static export were not run during this reconciliation pass.

## Next step
Address the stale disabled tree kebab “Open folder” affordance as its own bounded behavior change, or reconcile the remaining historical taxonomy-detail trackers.