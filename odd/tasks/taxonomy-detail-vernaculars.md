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
- [ ] ODD-TDV-001 Implement native Vernaculars data contract and UI.
- [ ] ODD-TDV-002 Verify and publish Vernaculars slice.

## Progress
Created after source mapping and user decisions.

## Next step
Implement ODD-TDV-001.