# Proposal: migrate-nextjs-tailwind4

## Intent

The current `taxa` frontend is a 6,345-line single-page vanilla-JS app
served by FastAPI on a single local port (8765). It mixes bespoke CSS,
client-side state, and progressive enhancement with no bundler, no
React, no router. This change replaces that frontend with a Next.js
(App Router) + React + Tailwind 4 stack in one delivery, while
keeping FastAPI as the single local origin and the `/api/*` contract
byte-identical where possible. The migration removes long-standing
technical debt (no type-safety, monolithic JS, manual DOM diffing
via `render()` re-stamps) and unblocks parity work for the Chrome
extension and future routes (Settings, About, Help).

## Scope

### In Scope

- Next.js 16 (App Router) app under `src/app/` rendering the full
  single-screen UI: header tabs, tree, breadcrumb, detail panel,
  file-explorer, file-viewer, dialogs, banners, settings, help.
- React 19 functional components replacing `web/*.js` modules one
  to one where possible.
- Tailwind 4 CSS-first config in `src/app/globals.css` with
  `@theme { … }` containing every design token currently in
  `tailwind.config.js` and the inline `:root` block.
- FastAPI keeps serving the built static output at
  `http://127.0.0.1:8765/`; single-origin contract preserved.
- Browser-local state and preferences (theme, tree source, last
  selected taxon, kebab menu state) migrated from the `state`
  singleton to React state/context, with a small adapter that
  hydrates from `localStorage` on first render.
- Accessibility: every currently-shipped interactive element keeps
  its ARIA semantics and keyboard parity (no regression vs current
  Playwright suite).
- Functional parity: every visible user flow (browse, search,
  materialize, preview, open folder, save URL, view files across
  PDF/HTML/MD/TXT/DOCX/XLSX/EPUB/JSON/image/video) behaves
  identically to the legacy build; performance regression ≤ 0%.
- Minimal dependency set: `next@^16`, `react@^19`, `react-dom@^19`,
  `tailwindcss`, `@tailwindcss/cli` (for the legacy CSS build
  transition only), TypeScript `>=5.1.0` toolchain. Each addition
  is justified.
- Runtime compatibility: the build and dev tooling MUST run on
  Node.js `>=20.9.0` (Next.js 16 hard requirement) and MUST be
  authored against TypeScript `>=5.1.0`. Exact pinned versions
  for Next.js 16 and Tailwind 4 are recorded in
  `openspec/changes/migrate-nextjs-tailwind4/design.md` (Spanish
  mirror under
  `documents-es/openspec/changes/migrate-nextjs-tailwind4/design-es.md`),
  §§"Runtime Engine Contract", "Dependency Surface", "§1
  Server Responsibility Boundary Decision".
- Rollback plan: `git revert` of the single migration PR restores
  the vanilla build; `web/dist/tailwind.css` regenerates from the
  rolled-back source.

### Server Responsibility Boundary (Next.js ↔ FastAPI)

The boundary between the Next.js runtime and the FastAPI server is
**evaluated and decided** during this migration. The exploration
enumerated three viable approaches:

| Approach | Next.js role | FastAPI role | Single-port contract |
|----------|--------------|--------------|----------------------|
| **A — Static export under FastAPI** | `next build` → `out/`; FastAPI's `StaticFiles` mount serves it. No SSR / route handlers / server components. | Sole HTTP origin on `127.0.0.1:8765`; serves frontend + `/api/*`. `StaticFiles` mount at `api/server.py:1815` repointed at `out/` once recorded. | **Preserved.** |
| **B — Full Next.js dev server, two ports** | `next dev` on port 3000; `rewrites()` proxies `/api/*` to FastAPI. Real SSR, server components, `next/font`. | FastAPI on 8765 only for `/api/*`; CORS allowlist widens to include `localhost:3000`. `StaticFiles` mount becomes dead code in dev. | **Broken.** Extension `host_permissions` must widen. |
| **C — Phased hybrid** | Phase 1: Tailwind 4 only on vanilla JS. Phase 2: Next.js pre-rendering into `web/dist/`. Phase 3: incremental React hydration behind a feature flag. Phase 4: retire vanilla. | Sole origin throughout; `web/dist/*` mount kept compatible. | **Preserved throughout.** |

**Constraints any chosen approach MUST honour:**

- Single local origin / single port (`127.0.0.1:8765`) — no second
  dev server port introduced in this change.
- Functional equivalence: every `/api/*` endpoint shape, payload,
  and behaviour stays identical (no path or payload breaking changes).
- Extension continuity: `extension/manifest.json::host_permissions`
  stays `["http://localhost:8765/*"]` in this change.
- Backend logic (`api/server.py`, SQLite/WAL, materialize flow, SSRF
  defence in `save-url`) is **not rewritten**, but the static-asset
  mount (`api/server.py:1815`) and any FastAPI middleware strictly
  needed to wire the chosen approach ARE in scope.

**Outcome**: this proposal does **not** pre-decide Approach A, B, or
C. The selected approach is recorded as a finalised decision in
`design.md` §1 once the spec/design phases have produced
concrete evidence (bundle size, hydration profile, Playwright
parity). The hard constraints above are the non-negotiables.
**G1 boundary decision** (FastAPI sole origin on `127.0.0.1:8765`;
`/api/*` and `extension/manifest.json::host_permissions` unchanged)
is recorded in `design.md::§1` and binds every Approach above.

### Out of Scope

- Backend rewrite: `api/server.py` route handlers, SQLite/WAL logic,
  materialize flow, SSRF defence in `save-url`, ETL pipeline. The
  FastAPI application code that backs `/api/*` is untouched; the
  only allowed server-side change is the minimum required to mount
  the new frontend output (e.g. repointing `WEB_DIR`, adding a
  build step to `make api`). Endpoint shapes stay identical
  (functional equivalence, no path or payload breaking changes).
- ETL pipeline: `etl/parse_textree`, `load_coldp`, `load_worms`,
  `load_freshwater`, migrations.
- Chrome extension parity (`extension/manifest.json`,
  `background.js`, `content.js`). Extension `host_permissions`
  stay on `http://localhost:8765/*`. A separate change tracks
  the React-aware adaptation plan.
- SEO (no metadata, sitemap, or robots work in this change).
- New routes (Settings, About, Help) beyond what the legacy UI
  exposes today.
- Pixel-level visual redesign (impeccable/Stitch review) — a
  follow-up, not a blocker.
- Coverage tooling (`coverage.available: false` is the current
  state; out of scope).

### Disposable Static-Export Probe (Evidence Only)

A bounded, **disposable** static-export probe slice is permitted
**only as an evidence-gathering exercise** while the
Next.js ↔ FastAPI server-responsibility decision remains open.
The probe is governed by these non-negotiables:

- **Unreachable from production**: the probe output is not served
  by FastAPI, not bound to `127.0.0.1:8765`, and not reachable
  from any shipped artifact (no extension `host_permissions`
  change, no `make api` integration, no release artifact).
- **No consumer change**: the `api/server.py:1815` `StaticFiles`
  mount, AC-21 search-engine contract consumers, and UI
  activation paths (`state` singleton, `localStorage` keys) stay
  untouched. The probe produces no consumer-visible surface.
- **Evidence only**: records `next build` size, hydration
  profile, and optional Playwright parity samples. It does not
  amend `design.md` §1 and does not pre-select Approach A.
- **Explicit discard / rollback**: the probe lives on a
  short-lived branch; `git branch -D` plus worktree removal
  restores the pre-probe state with no source/tests/config
  residue.
- **Cannot select static export alone**: probe evidence is
  necessary but not sufficient. Selecting Approach A requires a
  follow-up amendment to this proposal (or a successor change),
  reviewed against the recorded evidence; this proposal is not
  the selection point.

The probe does **not** modify "Out of Scope", "Approach", or
"Success Criteria", and introduces no source/tests/config change
in this PR. Its sole purpose is to convert the open
server-responsibility decision into evidence before finalising.

## Capabilities

### New Capabilities

- `frontend-runtime`: Next.js App Router single-screen app, SSR
  where compatible (initial route payload), client-side
  hydration of the interactive tree / detail / file-explorer
  components, all under FastAPI's static mount.
- `design-tokens`: Tailwind 4 `@theme` block + CSS variables
  (`--primary`, `--realm-*`, etc.) preserved verbatim so both
  utility classes and plain-CSS rules resolve.
- `browser-state-hydration`: React-aware migration of the legacy
  `state` singleton (`web/state.js`) into a typed store with
  explicit `localStorage` rehydration keys: `theme`,
  `tree-source`, `last-taxon-id`, `kebab-open-id`.

### Modified Capabilities

- `research`: API consumers migrate to `fetch` calls from React
  components / server components. No request/response shape
  changes; AC-21 contract test keeps reading `web/search_urls.js`
  unless the sdd-spec phase revises AC-21 explicitly.
- `frontend-bootstrap`: `web/index.html` ceases to be the entry;
  the entry is `next build` output (`out/` or `.next/static`)
  served by FastAPI's existing `StaticFiles` mount.

## Approach

Approach (A / B / C) selection is **evidence-gated** by `design.md::§1`
(G2–G6); the conditional default is `next build` → `out/` served by FastAPI.
Tailwind 4 ships in the same delivery via its CSS-first config
(`@theme { … }`) replacing `tailwind.config.js` and the inline
`<style>` block; bespoke `:root` tokens migrate into
`src/app/globals.css` inside `@layer base` so cascade order
matches today. The 18 vanilla ES modules become ~18 React
functional components in `src/components/`, with server
components for the read-only header / footer / breadcrumb /
detail-card primitives and client components for tree, file
explorer, file viewer, and any stateful surface. The `state`
singleton becomes a typed store with `localStorage`
rehydration. AC-21 contract shape (`web/search_urls.js`
literal) stays put during the first delivery; if the spec
phase decides to relocate, AC-21 is amended before any source
move. Browser-local state keys are documented and migrated
deterministically (one key, one read site, one write site).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `web/index.html` | Removed | Replaced by `src/app/layout.tsx` + `src/app/page.tsx`. |
| `web/*.js` (18 modules, 6,345 LoC) | Removed | Rewritten as React components under `src/components/` and `src/lib/`. |
| `web/index.css` | Modified | Becomes `src/app/globals.css`; `@theme` block replaces `tailwind.config.js`. |
| `tailwind.config.js` | Removed | Tailwind 4 CSS-first config in `globals.css`. |
| `package.json` | Modified | Bumps to `next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss ^4.x`; removes `autoprefixer`, `postcss`; adds `@tailwindcss/cli`, TypeScript `>=5.1.0`, `@types/*`. Adds `engines.node: ">=20.9.0"` and pinned dev-time Node version. |
| `api/server.py:1815` (`app.mount("/", StaticFiles(...))`) | Modified | `WEB_DIR` constant repointed at the chosen Next.js output (`out/`, `web/dist/next-static/`, or equivalent) per the decided Approach in `design.md` §1. Any new middleware strictly needed to serve the chosen output is added here; route handlers are not rewritten. |
| `Makefile` | Modified | `make api` builds Next.js first (`make web` alias) then runs uvicorn; `make smoke` keeps the same surface. No second dev-server port is introduced. |
| `tests/test_smoke.py::test_search_engine_contract` | Modified | Reads `src/data/search-engines.ts` only if AC-21 is amended by sdd-spec; else the file keeps its `web/search_urls.js` shape under `src/data/`. |
| `tests/test_e2e_file_explorer.py`, `tests/test_web_toggle.py` | Modified | DOM selectors updated for the new component tree; `data-*` attribute contract preserved. |
| `extension/manifest.json` | Unchanged | `host_permissions: ["http://localhost:8765/*"]` stays as-is (deferred). |
| `openspec/changes/migrate-nextjs-tailwind4/design.md` | Migrate (PR 2a) | Pinned versions, dependency justification, finalised Next.js ↔ FastAPI server-responsibility decision (Approach A / B / C), PR 2a scoped layout decisions, and the `tsconfig.json` path-alias contract. Canonical home of every reference previously pointed at the now-superseded `scope-decisions.md` artefact. |
| `documents-es/openspec/changes/migrate-nextjs-tailwind4/design-es.md` | Migrate (PR 2a) | Faithful neutral/professional Spanish mirror of `design.md` per AGENTS.md. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tailwind 4 token namespace shift (`--color-primary` vs `--primary`) breaks plain-CSS `var(--primary)` references. | Medium | Alias names in `@theme` so the existing `--primary`, `--bg-surface`, `--realm-*` tokens resolve unchanged; parity test enumerates every `var(--token)` reference and asserts a non-empty declaration. |
| `color-mix()` cascade reordering in the 80 KB inline `<style>` block causes visual drift. | Medium | Migrate the bespoke rules into `globals.css` inside `@layer base` so source order matches; Playwright visual regression on the existing `tests/test_web_toggle.py` fixture. |
| AC-21 search-engine contract test fails because `web/search_urls.js` is no longer byte-identical. | Medium | Keep the JS literal under `src/data/search-engines.js` with the same shape; the test reads `open()` from the new path. Spec phase decides whether to amend AC-21. |
| Hydration mismatch from `localStorage` reads on server vs client. | Medium | Initial render uses a `mounted` flag; storage reads happen inside `useEffect`; tree structure defaults to the empty state on first paint. |
| Static export forfeits dynamic routes / image optimization used by future work. | Low | Acceptable for v1; document the trade-off in `design.md` §1; switching to full Next.js dev server (Approach B) is the next-change cost if needed. |
| Next.js + React dependency bundle size regresses initial paint (performance budget). | Low | `next build` profile captured before/after; Playwright + Lighthouse sample on the existing chromium fixture; ≤ 0% regression is the success criterion. |
| Single-port contract breaks if the extension's `host_permissions` change accidentally. | Low | Hard rule in `Makefile` and CI smoke check: `make api` only binds 8765; no second origin added; `manifest.json` is unchanged in this PR. |

## Rollback Plan

1. **PR-level revert**: `git revert <migration-sha>` restores
   the vanilla `web/` + `tailwind.config.js` + Tailwind 3.4 build
   pipeline. `package-lock.json` keeps the prior Node
   dependency state; `npm ci` reproduces the lock. `make api`
   regenerates `web/dist/tailwind.css` from the reverted source.
2. **Side effects**: AC-21 contract test reverts to its prior
   `open("web/search_urls.js")` read; backend tests are untouched.
3. **Production rollback** (if the migration reaches `main`):
   `git checkout <last-good-sha> -- web/ package.json
   package-lock.json Makefile src/ tests/`, reinstall via
   `npm ci && make css`, redeploy via the existing release
   process. No DB schema change ships in this change, so no
   data migration is required to roll back.
4. **Extension continuity**: extension talks to
   `http://localhost:8765` before, during, and after the
   rollback — no manifest update is required to revert.
5. **Verification after rollback**: `make smoke` returns to the
   pre-migration baseline (63 passed, 8 skipped on the same
   fixture set, plus existing Playwright runs).

## Dependencies

- `next@^16` (App Router; Next.js 16 is the target line and
  supports React `^19.0.0`).
- `react@^19`, `react-dom@^19` (matches the React major pinned
  by Next.js 16).
- `tailwindcss` ^4.x.
- `@tailwindcss/cli` (transitional only, if a non-Next build path
  is needed during migration).
- `typescript` `>=5.1.0`, `@types/react@^19`, `@types/react-dom@^19`,
  `@types/node` (TS toolchain, justified for typed React state
  and API client types; TypeScript `>=5.1.0` is the Next.js 16
  floor).
- `next/font` for Raleway, JetBrains Mono, Material Symbols
  Outlined (justification: existing fonts stay, no new icon
  set per the project's AGENTS.md).
- Runtime engine: Node.js `>=20.9.0` (Next.js 16 hard
  requirement). Recorded in `package.json::engines.node` when
  the rewrite lands with PR 3 task 3.4, and in
  `design.md` §"Runtime Engine Contract".
- No other runtime dependencies without explicit per-capability
  justification in `design.md` §"Dependency Surface".

## Success Criteria

- [ ] Functional parity: every user flow (browse, search,
      materialize, preview, open folder, save URL, view files
      across all supported formats) behaves identically to the
      legacy build.
- [ ] Performance: no regression in initial paint or
      interaction latency on the existing Playwright + Lighthouse
      sample (≤ 0% delta).
- [ ] Single local origin: `make api` binds only 8765; no second
      dev server port; extension `host_permissions` unchanged.
- [ ] All backend pytest tests still green (63 passed, 8 skipped
      baseline preserved).
- [ ] Playwright suite updated, still green against the new
      component tree; `data-*` attribute contract preserved.
- [ ] AC-21 search-engine contract test passes (file location
      may move, byte shape unchanged unless sdd-spec revises).
- [ ] Browser-local state and preferences migrate deterministically
      (theme, tree-source, last-taxon-id, kebab-open-id) with one
      read site and one write site per key.
- [ ] Accessibility: every ARIA role, label, and keyboard handler
      from the legacy build is preserved; axe scan has no new
      violations.
- [ ] Tailwind 4 parity: every utility class appearing in the
      legacy build resolves to a non-empty declaration in the new
      build; every `:root` token (`--primary`, `--realm-*`,
      etc.) resolves.
- [ ] Rollback: `git revert` of the single migration PR
      restores the legacy build with green smoke + Playwright.
