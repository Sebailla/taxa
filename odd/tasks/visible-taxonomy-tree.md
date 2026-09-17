# Deliver a visible taxonomy tree

## Objective
Replace the Next.js placeholder with a usable initial taxonomy shell and lazily expandable tree backed by the existing FastAPI API.

## Problem and rationale
The merged frontend pipeline builds and serves, but `src/app/page.tsx` only renders `taxa`. CSS, a taxonomy domain, and API helpers exist, yet no React shell or tree is mounted. The FastAPI `/api/domains` response includes real ranks such as `superdomain`, so the domain rank contract must represent API data faithfully before the tree can load.

## User decision
Expand the taxonomy `Rank` union to include real API ranks (including `superdomain`) rather than coercing or hiding those rows.

## Scope
- Extend taxonomy rank/domain validation and projections for API-supported ranks.
- Add `fetchDomains()` and pure tree state/source helpers.
- Mount a minimal accessible AppShell and lazy taxonomy tree in the App Router.
- Reuse existing Tailwind selectors; add no backend API routes and no new CSS selectors.
- Represent loading, error, empty, and per-row lazy-load failure states.

## Non-goals
- Detail panel, Overview/Search/Folder tabs, breadcrumb UI, kebab actions, research explorer, source switching, settings/theme controls, URL hash routing, backend changes, and legacy web deletion.

## Constraints
- Preserve FastAPI endpoint payloads and the frozen predecessor OpenSpec change.
- Use minimal Next client boundaries: only fetch/state-bearing components are client components.
- Ship the work as two focused PRs; completed units are committed and published, but never merged automatically.
- TDD mode: disabled/unknown; tests extend the repository's existing source/runtime harnesses.

## Delivery strategy
feature-branch chain; two PRs, each targeting `develop` sequentially after prior merge.

## Tasks
- [x] ODD-VTREE-001 Expand real API ranks and build the taxonomy data/state foundation.
  - Implementation: expanded `Rank` to 21 evidenced API/fixture ranks; added `fetchDomains()` and shared wire-list projection; added pure tree state and barrel exports; added focused rank/API/state tests.
  - Evidence: writer suite (84 tests) and independent relevant suite (48 tests) passed; `pnpm exec tsc --noEmit` and `git diff --check` passed.
  - Correction: independent review found and the worker fixed an inverted broadest-first `RANK_ORDER`; rank comparison now matches legacy formatting and FastAPI ordering.
  - Review: independent verifier approved. The coherent source/test diff remains ~678 lines, above the ~400 review guidance but not artificially splittable without separating one foundation contract.
  - Delivery: ready to commit and publish as PR A.
- [ ] ODD-VTREE-002 Mount the visible shell and interactive lazy taxonomy tree.
  - Scope: AppShell, health status island, TaxonomyTree/TreeRow, `page.tsx` integration, focused runtime/browser/build evidence.
  - Acceptance: local page has header/footer and root rows; expanding a root loads children; loading/error/empty states are accessible; static build passes.
  - Delivery: PR B, created only after PR A merges; split further if evidence exceeds review budget.
- [ ] ODD-VTREE-003 Verify each delivered slice and record evidence.
  - Acceptance: focused tests plus static build; browser evidence where environment permits; no out-of-scope paths.
- [ ] ODD-VTREE-004 Publish each completed slice.
  - Acceptance: conventional commits and PRs linking approved issue #74 with exactly one appropriate `type:*` label; no automatic merges.

## Progress
ODD-VTREE-001 is independently verified and published as PR #300 (`feat/taxonomy-tree-foundation` → `develop`), linked to approved issue #74 with `type:feature`. No UI has been mounted yet; ODD-VTREE-002 starts only after PR A merges.

## Next step
Wait for PR #300 Smoke tests and human merge; then create the visible-shell/tree branch from updated `develop`.
