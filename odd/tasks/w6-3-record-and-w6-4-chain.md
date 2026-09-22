# W6.3 record correction and W6.4 chain

## Objective
Reconcile the completed W6.3 Explorer splitter evidence in the migration tracker, then deliver the chained Research viewer-materialization slices (W6.4a JSON + DOCX already merged; W6.4b XLS/XLSX next; remaining preview families + refresh bridge deferred).

## Problem and rationale
The merged tracker was stale on W6.3; correcting it prevented the next slice from running on false status. Each chained W6.4 slice must keep its typed `cdn-failed` recovery, preserve every existing W1–W6.3 pin, and stage its work, tests, styles, and tracker evidence together before merging.

## Scope
- Reconcile the W6.3 tracker evidence (already complete).
- Author + verify + commit + merge the W6.4a JSON + DOCX viewer materialization slice (already merged as PR #364).
- Author + verify + commit + merge the W6.4b XLS/XLSX viewer materialization slice (SheetJS via Next `Script` with a multi-sheet picker).
- Defer remaining preview families (EPUB via epubjs, CSV/TSV via Papa Parse) and the Explorer refresh bridge to separately authorized slices.
- Preserve `odd/tasks/g4-integration-delivery.md` unchanged and untracked.

## Constraints
- W6.4 work touches only the mapped Research presentation/application/test/style surfaces and the migration tracker.
- No legacy edits, dependency changes, FastAPI/API changes, browser-state expansion, Explorer refresh bridge, or cutover changes.
- The JSON renderer stays native; DOCX uses the existing pinned Mammoth contract through Next `Script`.
- RDD is disabled for this clone.
- Strict TDD with pytest is required for every chained W6.4 work-unit commit.

## Delivery strategy
Feature-branch chain. Each W6.4 work-unit commit owns its preview family, its typed `cdn-failed` recovery, and its preservation guarantees. Push, PR, and merge remain user-authorized per ordinary delivery flow.

## Tasks
- [x] W63-RECORD-001 Reconcile the stale W6.3 tracker evidence.
  - Evidence: recorded commit `9cfb2b9`, independent verification (48 focused tests + strict TypeScript), and merged PR #363 at `7895668`; structural readback confirmed the corrected paragraph.

- [x] W64A-JSON-001 Implement native JSON Tree viewer materialization.
  - Evidence: implemented, independently verified (14 W64A tests + 227 full Research tests, strict TypeScript, Impeccable detector on Viewer + globals), locally committed on `feat/explorer-viewer-json-docx`.

- [x] W64B-DOCX-002 Implement DOCX/Mammoth viewer materialization.
  - Evidence: implemented, independently verified (11 W64B tests + 238 full Research tests, strict TypeScript, Impeccable detector clean), locally committed as `2fbf24e`, PR #364 merged at `574b6d9`, local develop fast-forwarded.

- [x] W64C-XLS-003 Author + verify + commit XLS/XLSX viewer materialization.
  - Evidence: implemented, independently verified (15 W64C tests + 253 Research regression tests, strict TypeScript, Impeccable detector with only the two pre-existing `.tree-row` findings), locally committed as `78aeb5e`, PR #365 merged at `24b7da1`, local develop fast-forwarded.

- [ ] W64D-DEFER-004 Defer remaining preview families + the Explorer refresh bridge.
  - Route: parent-authorized separate slices for EPUB + CSV/TSV (Papa Parse) and the Folder-tab → Explorer refresh bridge (`CustomEvent`, new browser-state key, or router-key re-mount per a future architecture decision).

- [x] W64D-EPUB-004 Author + verify + commit EPUB viewer materialization.
  - Evidence: implemented, independently verified (14 W64D tests + 267 Research regression tests, strict TypeScript, Impeccable detector with only the two pre-existing `.tree-row` findings), locally committed as `6a2b845`, PR #366 merged at `2a3cf0a`, local develop fast-forwarded.

- [x] W64E-CSV-005 Author + verify + commit CSV/TSV Table viewer materialization.
  - Evidence: implemented, independently verified (6 W64E tests + 273 Research regression tests, strict TypeScript, Impeccable detector with only the two pre-existing `.tree-row` findings), locally committed as `10b8217`, PR #367 merged at `ddbf5b8`, local develop fast-forwarded.

- [x] W65-BRIDGE-006 Author + verify + commit Explorer refresh bridge.
  - Evidence: implemented, independently verified (13 W6.5 tests + 413 full Research + Taxonomy regression tests, strict TypeScript, Impeccable detector clean), locally committed as `ccc8c79`, PR #368 merged at `aac6ded`, local develop fast-forwarded.

- [x] W65-MAP-007 Read-only map of ODD-MIGRATE-004 AC-21 + consumer manifest.
  - Evidence: read-only mapping complete. Verified AC-21 readers + 17-entry live engine catalog; React taxonomy search port already merged (ODD-TDS-001); consumer table enumerates every active consumer, comment-only reference, React bridge test, and forbidden surface. Open product decisions captured: literal location (KEEP vs MOVE), legacy `web/detail.js` scope, manifest artifact format, and 17-vs-14 engine count drift.

- [ ] W65-MANIFEST-008 Author + verify the AC-21 consumer manifest artifact.
  - Route: delegated worker; multi-file write rule (tests only — no production source edits).
  - Allowed edit surfaces: `tests/test_search_engine_consumer_manifest.py` (new hermetic pytest), `odd/tasks/complete-frontend-migration.md`.
  - Acceptance: KEEP the `web/search_urls.js` literal at its current location; produce a single hermetic `tests/test_search_engine_consumer_manifest.py` that enumerates every active consumer of `web/search_urls.js` + verifies AC-21 `test_search_engine_contract`, the `LEGACY_SEARCH_URLS_JS` test constant, the React `search-categories.ts` + `SearchTab.tsx` purity, and `api/server.py::_SEARCH_ENGINES` mirror integrity. Tracker bullet records the manifest evidence.
  - Verification: focused pytest group + full Research + Taxonomy regression + smoke + strict TypeScript + one Impeccable detector pass.
  - Commit: user-authorized local work-unit commit + push + PR + merge.

## Progress
- W63-RECORD-001 done.
- W64A-JSON-001 done; PR #364 merged.
- W64B-DOCX-002 done; PR #364 merged.
- W64C-XLS-003 done; PR #365 merged.
- W64D-EPUB-004 done; PR #366 merged.
- W64E-CSV-005 done; PR #367 merged.
- W65-BRIDGE-006 done; PR #368 merged.
- W65-MAP-007 done (read-only AC-21 + consumer manifest map; user selected KEEP).
- W65-MANIFEST-008 selected as next.

## Next step
Delegate W65-MANIFEST-008.
