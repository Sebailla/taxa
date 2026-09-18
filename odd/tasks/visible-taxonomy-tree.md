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
- Present only collapsed root domains initially; load children lazily on explicit expansion.

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
  - Implementation: AppShell, TaxonomyTree/TreeRow, and `page.tsx` integration are present only on the feature branch.
  - Correction path: static export cannot use Next rewrites/proxy. Local preview will use a documented `NEXT_PUBLIC_TAXA_API_ORIGIN=http://127.0.0.1:8765` dev-only origin, while production static export retains relative `/api` for the future cutover.
  - Applied corrections: `page.tsx` now uses public barrels; the tree reuses canonical API helpers; disclosure no longer points at empty hidden targets; `dev:local` supplies the direct FastAPI origin.
  - Turbopack correction: converted the affected public-barrel and direct taxonomy `domain/taxon` paths to extensionless TypeScript imports; do not change the FastAPI production mount or legacy UI.
  - Mechanical correction (this turn): removed the remaining `.js` suffix from every `from "../domain/taxon.js"` import across the direct taxonomy-layer consumers — `application/view-models.ts` (type+value), `application/ports.ts` (type), `infrastructure/api.ts` (value+type), `presentation/tree-state.ts` (type), and `presentation/breadcrumb-path.ts` (type). Five files, seven import statements, type/value identity and ordering preserved. `next-env.d.ts` unchanged by hand (no `../domain/taxon` targets; Next auto-rewrote it to `.next/dev/types/*` during `next build`).
  - Verification: `pnpm exec tsc --noEmit` clean; `pnpm exec next build` produced the static export (`Route (app)` shows `○ /` and `○ /_not-found`); `git diff --check` clean; FastAPI on `127.0.0.1:8765` returned HTTP 200 for `/api/health`, `/api/domains`, `/api/taxon/1`, and `/api/taxon/1/children`; CORS preflight `OPTIONS /api/domains` from `Origin: http://127.0.0.1:3000` returned 200 with `access-control-allow-origin: http://127.0.0.1:3000` (matches the configured `^https?://(localhost|127\.0\.0\.1)(:\d+)?$` regex); `pnpm run dev:local` on port 3000 served `GET /` HTTP 200, the rendered HTML carried the `AppShell` header (`Taxonomic Tree`), the `<section aria-label="Taxonomic tree">` with the initial `Loading domains…` status, and the footer `apiOrigin=/api`. Processes stopped afterwards.
  - Live-rank correction: the contract now models `unranked` Viruses and `realm` children without coercion; `next-env.d.ts` matches HEAD and is excluded from the candidate.
  - Verification: independent browser evidence rendered six real collapsed roots through CORS and expanded Viruses into 35 children including seven realms; 121 focused tests, TypeScript, static build, and diff checks passed.
  - Review: independent verifier approved the cohesive PR B candidate (~1,139 lines including source/tests/path corrections). It exceeds the 400-line guidance but is the second and final planned visible-tree PR; splitting would ship an empty shell instead of an observable feature.
  - Delivery: ready to commit and publish.
- [x] ODD-VTREE-003 Verify each delivered slice and record evidence.
  - Evidence: PR A independently approved and merged. PR B independently approved with 121 focused tests, strict typecheck, static build, CORS/API probes, and Chromium root-load/expansion evidence.
- [ ] ODD-VTREE-004 Publish each completed slice.
  - Foundation: PR #300 merged.
  - Visible tree: committed as `feat(taxonomy): mount visible tree`; PR B publication is in progress.
  - Acceptance: PR links approved issue #74 with exactly one appropriate `type:*` label; no automatic merge.

## Progress
ODD-VTREE-001 merged as PR #300. ODD-VTREE-002 is independently verified and committed: local preview loads six collapsed real roots and expands Viruses through direct FastAPI CORS. No merge is authorized.

## Next step
Push `feat/visible-taxonomy-tree` and open PR B to `develop`, linked to approved issue #74 with `type:feature`.
