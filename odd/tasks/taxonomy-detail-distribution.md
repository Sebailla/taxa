# Restore taxonomy detail Distribution

## Objective
Port the native DetailPanel Distribution tab to React, exposing canonical area and establishment-means records.

## Decisions
- Preserve legacy fallback: missing establishment means renders `unknown`.
- Render flat rows only; do not add gazetteer, degree, grouping, or filters.
- Keep source-agnostic per-taxon cache across source switches.
- Deliver as one cohesive PR with explicit size exception (~800 lines), as user selected.
- Include regenerated `next-env.d.ts` if it remains different from HEAD after verification, per repository Next rules.

## Scope
- Typed `/api/taxon/{id}/distribution?limit=200` projection.
- Eager selected-taxon cache and enabled Distribution tab.
- Native header/count, means chips, areas and loading/empty/error/retry states.
- Focused parity tests, static build, browser/API evidence.

## Non-goals
Backend/legacy changes; `only` filter UI, grouping, gazetteer/degree rendering, client sort/pagination, Folder, or production cutover.

## Tasks
- [x] ODD-TDDIST-001 Implement native Distribution contract and UI.
- [ ] ODD-TDDIST-002 Verify and publish Distribution slice.

## Progress
- ODD-TDDIST-001 implemented. Files: api.ts (DistributionEntry + fetchDistribution + FetchDistributionOptions + isValidDistribution + fromWireDistributionList), DetailPanel.tsx (Distribution tab enabled, distributionStatus + onRetryDistribution props wired, body dispatch on `activeTab === "distribution"`), DistributionTab.tsx (new pure renderer with DistributionTabStatus union + loading/empty/error/loaded/retry states + establishment-means chip with `unknown` fallback + area text), TaxonomyTree.tsx (distributionByTaxonId cache + loadDistribution callback + eager-fetch effect on `selected` change + handleSourceChange retains cache), index.ts (re-exports fetchDistribution + DistributionEntry + FetchDistributionOptions), globals.css (.distribution-tab cascade with alphabetical ordering under @layer components). Tests: test_taxonomy_infra.py (named-fn test, DistributionEntry + FetchDistributionOptions test, runtime harness for fetchDistribution: happy path, limit override, empty/non-OK/non-array/per-element-schema failures, type checks, id checks, JSON failures), test_visible_taxonomy_tree.py (18 new tests: file/client/canonical-projection/header+count/row-chip+area/loading/empty/error+retry/unknown-fallback/DetailPanel/enabled/body-dispatch/eager-fetch/cache/source-switch-retention/props-pass-through/barrel/CSS/static-export), test_research_styles.py (.distribution-tab whitelist). next-env.d.ts unchanged (drift resolved after validation). All 489 focused tests pass + TypeScript clean + next build succeeds.