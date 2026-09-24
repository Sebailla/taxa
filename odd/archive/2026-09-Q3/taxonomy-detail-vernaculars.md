# Restore taxonomy detail Vernaculars

## Objective
Port the native DetailPanel Vernaculars tab to React, exposing localized common names from the dedicated FastAPI endpoint.

## Decisions
- Keep the React pattern: tab is always visible and renders loading, empty, error/retry, or loaded states.
- Request `limit=200` for legacy parity.
- Keep cache across source switches because the endpoint is source-agnostic.
- Use the native body header `Vernacular names` and display ISO language codes verbatim.

## Scope
- Add typed `GET /api/taxon/{id}/vernaculars?limit=200` projection.
- Enable and eagerly load the Vernaculars tab per selection.
- Render native item formatting: optional language/country chips and name, header/count, loading/empty/error/retry states.
- Preserve Overview, Search, tree navigation, and per-taxon tab memory.

## Non-goals
- Backend/legacy, source filtering, language filter UI, pagination, i18n expansion, Folder/Synonyms/Distribution, or production cutover.

## Constraints
- Legacy `web/detail.js` and CSS are parity oracles.
- Presentation receives data; infrastructure owns fetch/projection.
- Commit and PR when complete; no automatic merge.

## Tasks
- [x] ODD-TDV-001 Implement native Vernaculars data contract and UI.
- [x] ODD-TDV-002 Verify and publish Vernaculars slice.

## Progress
- ODD-TDV-001 is implemented on `develop`: `api.ts` validates and projects `VernacularName` records through `fetchVernaculars`; `TaxonomyTree.tsx` eagerly loads the source-agnostic per-taxon cache; `DetailPanel.tsx` enables and dispatches the tab; `VernacularTab.tsx` renders loading, empty, retryable error, and loaded states with verbatim language/country chips; `globals.css` supplies the scoped cascade. Focused contract, UI, and style coverage lives in `tests/test_taxonomy_infra.py`, `tests/test_visible_taxonomy_tree.py`, and `tests/test_research_styles.py`.
- ODD-TDV-002 was published through merged PRs #311–#313 (commits `e64ffff`, `0792961`, `1bccdea`, merged to `develop` via `fc13e07`, `b3787fc`, and `3c95b5c`). Independent read-only verification on current `develop` passed strict TypeScript checking plus 59 focused tests (17 Vernacular UI, 12 infrastructure, 30 styles). The live Next build, API smoke, and parity harness were not rerun during this reconciliation pass.

## Next step
Reconcile and close Synonyms as the dependent companion slice, or address the stale disabled tree kebab “Open folder” affordance as a separate change.