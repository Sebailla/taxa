# Restore taxonomy detail Search

## Objective
Port the native DetailPanel Search tab into React so a selected taxon exposes the server-composed research links in the legacy category order.

## User decision
Search is the next detail-panel slice after merged Overview. Folder, Vernaculars, Synonyms, and Distribution remain separate future slices.

## Scope
- Add a canonical typed projection for `GET /api/taxon/{id}/searches`.
- Enable the Search detail tab and load its links on selection using server-composed URLs only.
- Render native category grouping, loading, empty, error/retry, and secure external links.
- Preserve per-taxon active-tab state and all tree/Overview behavior.
- Add focused tests and local browser/API evidence.

## Non-goals
- Server, database, ETL, legacy-web, or search-engine catalog changes.
- Folder/Vernaculars/Synonyms/Distribution content, cache optimization, custom engines, or production cutover.

## Constraints
- `web/detail.js::renderSearchesTab`, `web/search_urls.js`, and FastAPI search-link payload are parity oracles.
- The client must never construct a search URL.
- Preserve layer boundaries: SearchTab receives data; infrastructure owns fetch/projection.
- TDD mode: disabled/unknown; run focused checks and browser evidence.
- Commit and open a PR when complete; no automatic merge.

## Tasks
- [x] ODD-TDS-001 Implement native Search tab data contract and UI.
  - Implementation: added typed server-link projection, pure native category bridge, enabled Search body, eager selection cache, retry/source-reset behavior, and secure external links.
  - Evidence: 309 focused tests, strict typecheck, and static build passed. Independent verification was interrupted by unrelated stale-stash pollution; the candidate was restored and the same checks passed again.
  - Delivery: ready to publish.
- [ ] ODD-TDS-002 Verify and publish Search slice.
  - Acceptance: focused tests, typecheck, static build, diff check, browser/API evidence, independent verification, conventional commit, and PR linked to issue #74 with exactly one `type:*` label.

## Progress
ODD-TDS-001 is verified and ready for PR delivery.

## Next step
Commit, open a PR to `develop`, then wait for CI and explicit merge authorization.