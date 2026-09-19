# SUPERSEDED — complete-taxa-frontend-migration

> **Status**: this OpenSpec change was **never executed as planned**.
> The 16-child PR #143 chain (`feat/complete-taxa-frontend-migration-NN-XXX`)
> stayed in draft and is **superseded by direct-to-develop ODD deliveries**.
> PR #143 will be **closed without merge** after this documentation is
> published. This directory is preserved as planning history.
>
> The concise reader record for the actual delivery is this file. The
> sibling `proposal.md`, `design.md`, `spec.md`, `tasks.md`, and
> `apply-progress.md` describe a plan that was not executed.

## Delivered evidence (merged to `origin/develop`)

The taxonomy-tree slices were delivered as focused PRs, each scoped under
the 400-line review budget and merged into `develop` directly.

| PR | Slice | ODD tracker |
| --- | --- | --- |
| #299 | Tailwind v4 / Next.js 16 pipeline repair | `odd/tasks/repair-tailwind-next-pipeline.md` |
| #300 | Tree data foundation (rank union, `fetchDomains`) | `odd/tasks/visible-taxonomy-tree.md` |
| #301 | Mounted visible tree on real FastAPI CORS | `odd/tasks/visible-taxonomy-tree.md` |
| #302 | Source-aware wire contract preserved | `odd/tasks/native-tree-parity.md` |
| #306 | Native tree structure, tier paging, disclosure | `odd/tasks/native-tree-parity.md` |
| #307 | Native row identity, source/status indicators | `odd/tasks/native-tree-parity.md` |
| #308 | Source-aware selection, focus, breadcrumbs | `odd/tasks/native-tree-parity.md` |
| #309 | Detail panel Overview tab | `odd/tasks/taxonomy-detail-overview.md` |
| #310 | Detail panel Search tab | `odd/tasks/taxonomy-detail-search.md` |
| #317 | `make api` no longer triggers `pnpm install` | `odd/tasks/make-api-pnpm-bootstrap.md` |
| #318 | Detail panel Distribution tab | `odd/tasks/taxonomy-detail-distribution.md` |
| #322 | Discoverable `View details` icon + kebab label | `odd/tasks/taxonomy-detail-discoverability.md` |
| #323 | Open-folder kebab action wired | (already reconciled) |

PR #303 (`feat/native-tree-source-selector`) was **closed without merge**;
its source-selector work was carried forward by the merged #306 / #307 /
#308 tree chain. PR #305 (a first rebased source-selector attempt) was
merged briefly before PR #306's structure rebased subsumed its work.

The ODD feature chain also covered Vernaculars (#311–#313), Synonyms
(#314–#316), and Folder (#319–#321). Those trackers were reconciled in
commit `3683cf1` (`docs(odd): reconcile taxonomy detail deliveries`).

## Explicitly NOT claimed

- The React frontend replaces the legacy `web/` app in production.
- FastAPI now serves `out/` as the mounted static root.
- The legacy `web/` files have been retired.
- The G4 / G5 / G6 validation gates from this change have closed.
- The acceptance criteria in `spec.md` (functional parity, single-origin
  invariants, browser-state hydration, Tailwind 4 parity, accessibility,
  predecessor-frozen, rollback unit) have been verified against the
  React cutover.
- The content of `proposal.md` / `design.md` / `spec.md` / `tasks.md` /
  `apply-progress.md` is current.

## Remaining separate production cutover gap

Out of scope for the ODD deliveries above and tracked separately:

- `next build` producing `out/` as part of `make api`.
- FastAPI `api/server.py::WEB_DIR` repoint from `web/` to `out/`.
- Static `StaticFiles` mount verification on `127.0.0.1:8765`.
- Retirement of the on-disk `web/` vanilla-JS app.
- AC-21 search-engine contract reader path migration.
- Browser-local state typed store (`theme`, `tree-source`,
  `last-taxon-id`, `kebab-open-id`) inside `src/modules/browser-state/`.
- Predecessor `migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
  rules 1–7 enforcement against the merged React code.
- Validation gate closure (G4 Playwright + Lighthouse parity, G5
  hydration baseline, G6 cutover rehearsal).

## Pointers

- Current ODD trackers: `odd/tasks/*.md` (see the table above).
- Frozen predecessor: `openspec/changes/migrate-nextjs-tailwind4/`.