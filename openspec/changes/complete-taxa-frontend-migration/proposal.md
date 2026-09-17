# Proposal: complete-taxa-frontend-migration

> **Phase**: sdd-init seed. Successor to `migrate-nextjs-tailwind4`.
> The total Taxa frontend migration is user-authorized; this change is
> its OpenSpec/SDD home. **No application code is authored by this
> seed.** Spec / design / tasks phases elaborate from here.

## TL;DR

- **Goal**: complete the total Taxa frontend migration that
  `migrate-nextjs-tailwind4` planned but did not finish. One shipping
  frontend, no parallel pre-cut, under the same FastAPI origin on
  `127.0.0.1:8765`.
- **Backend is non-negotiable**: FastAPI + SQLite (WAL) stay as the
  sole backend/origin. `/api/*` payload shapes stay byte-identical.
  The Chrome extension keeps
  `host_permissions: ["http://localhost:8765/*"]`.
- **Stack target**: Next.js 16 (App Router) + React 19 + Tailwind 4 —
  the same stack the predecessor planned. No framework switch in this
  change.
- **Approach default**: Approach A — `next build` → `out/` served by
  FastAPI's `StaticFiles` mount (single origin preserved). Spec phase
  may override A in favour of B or C only with evidence-anchored
  rationale citing the G2 / G5 numbers already produced.
- **Evidence reuse**: G1 (single origin) is recorded. G2 (build
  profile), G3 (consumer manifest), G4 (chromium baseline), G5
  (hydration probe), G6 (consumer dry-run) artifacts from the
  predecessor are imported as **history**, not re-derived. The
  predecessor's `proposal.md` / `spec.md` / `design.md` /
  `tasks.md` / `apply-progress.md` / `cutover-manifest.json` /
  `specs/modular-architecture/spec.md` are read-only inputs.

## Successor status

| Field | Value |
| --- | --- |
| Predecessor | `migrate-nextjs-tailwind4` |
| Relationship | Successor — this change inherits the goal; the predecessor is frozen as planning history. |
| Editable in this change? | **No.** Files under `openspec/changes/migrate-nextjs-tailwind4/` MUST NOT be modified. |
| Referenced as | Evidence base for the Approach A/B/C decision and for the G1–G6 evidence gates. |
| Evidence state on intake | G1 PASS recorded; G2 / G3 / G4 / G5 / G6 status carried verbatim from `migrate-nextjs-tailwind4/apply-progress.md`. |

The successor does not re-derive the chromium baseline, the
build-profile emitter, the hydration probe, or the consumer dry-run
verifier. Those artifacts already live under the predecessor and are
read by the spec / design phases of this change as planning history.

## Backend contract (non-negotiable)

Any proposed change that violates a row in this table is out of scope
and must be raised in a separate change.

| Surface | Constraint | Source |
| --- | --- | --- |
| Origin | `http://127.0.0.1:8765` only | G1 (single-origin) |
| Port | 8765 only; no second dev-server port | G1 |
| `/api/*` shapes | Byte-identical to current FastAPI | Functional equivalence rule |
| Extension `host_permissions` | `["http://localhost:8765/*"]` unchanged | Continuity rule |
| SQLite mode | WAL; read-only API connections | Repo convention (`openspec/sdd-init.md`) |
| ETL pipeline | Unchanged in this change | Predecessor out-of-scope |
| Materialize flow, `save-url` SSRF defence | Unchanged in this change | Predecessor out-of-scope |

## Scope

### In scope

- Total frontend migration to Next.js 16 + React 19 + Tailwind 4,
  replacing the on-disk `web/` vanilla-JS app under Approach A
  (default).
- One shipping frontend. The parallel pre-cut legacy build is
  retired at activation — no dual-build state in this change's apply
  phase.
- FastAPI origin preserved on `127.0.0.1:8765`. Minimal `api/server.py`
  edits are allowed only for `WEB_DIR` repointing and any middleware
  strictly required to mount the new frontend output. Route handlers
  are not rewritten.
- AC-21 search-engine contract test preserved
  (`web/search_urls.js` may move under `src/data/`; byte shape
  preserved unless spec phase explicitly revises).
- Browser-local state (`theme`, `tree-source`, `last-taxon-id`,
  `kebab-open-id`) migrated deterministically into a typed store with
  one read site + one write site per key.
- Modular-architecture constraints from the predecessor's
  `specs/modular-architecture/spec.md` apply unchanged.

### Out of scope

- Backend rewrite: `api/server.py` route handlers, SQLite/WAL logic,
  materialize flow, SSRF defence in `save-url`.
- ETL pipeline: `etl/parse_textree`, `load_coldp`, `load_worms`,
  `load_freshwater`, migrations.
- Chrome extension parity work — separate change tracks any
  React-aware extension adaptation.
- SEO / metadata / sitemap / robots work.
- New routes (Settings, About, Help) beyond what the legacy UI
  exposes today.
- Coverage tooling (`coverage.available: false` is the current state).
- Visual redesign (impeccable / Stitch follow-up, not a blocker).
- Editing or "completing" the predecessor's change directory. The
  predecessor is **frozen**, not finalized.
- Re-running the predecessor's G2 / G4 / G5 / G6 probes — their
  outputs are imported as-is.

## Approach

The predecessor deferred the Approach A / B / C decision to design
phase. This successor change adopts the **evidence-gated default**:
**Approach A — Static export under FastAPI**. `next build` produces
`out/`; FastAPI's existing `StaticFiles` mount serves it; no SSR /
route handlers / server components; single origin preserved.

**Default is A**, not B or C, because:

- G1 (single origin) is already recorded. Approach A honours G1
  trivially; B breaks it (two ports); C preserves it via phased
  rollout but adds review surface.
- The Chrome extension manifest stays unchanged under A.
- The `WEB_DIR` change is the minimum-edit path (`api/server.py:1815`
  `StaticFiles` mount repointed at `out/`).
- Spec / design phases may override A in favour of B or C only by
  citing the G2 build-profile numbers and G5 hydration numbers from
  the predecessor's `apply-progress.md`. Override is documented in
  `design.md::§1` of this change.

## Capabilities

### New capabilities

- `frontend-runtime`: Next.js App Router single-screen app,
  static-exported to `out/`, served by FastAPI's existing
  `StaticFiles` mount on `127.0.0.1:8765`.
- `design-tokens`: Tailwind 4 `@theme` block + CSS variables
  preserved verbatim from `web/index.html`'s bespoke `<style>` block
  and `tailwind.config.js`.
- `browser-state-hydration`: typed store with explicit `localStorage`
  rehydration keys (`theme`, `tree-source`, `last-taxon-id`,
  `kebab-open-id`), one read site + one write site per key.

### Modified capabilities

- `research`: API consumers migrate to `fetch` calls from React
  components / server components. No request/response shape changes;
  AC-21 contract test keeps reading `web/search_urls.js` unless the
  sdd-spec phase revises AC-21 explicitly.
- `frontend-bootstrap`: `web/index.html` ceases to be the entry; the
  entry is `out/index.html` (or `.next/static`-served equivalent)
  served by FastAPI.

### Unchanged capabilities (imported from predecessor)

- `modular-architecture`: `specs/modular-architecture/spec.md` from
  the predecessor applies unchanged. No second copy is authored.

## Affected areas

| Area | Impact | Note |
| --- | --- | --- |
| `web/index.html` | Removed | Replaced by `out/index.html` (Next.js static export). |
| `web/*.js` (18 modules, ~6,345 LoC) | Removed | Rewritten as React components under `src/components/`. |
| `web/index.css` | Modified | Becomes `src/app/globals.css`; `@theme` block replaces `tailwind.config.js`. |
| `tailwind.config.js` | Removed | Tailwind 4 CSS-first config in `globals.css`. |
| `package.json` | Modified | Bumps to `next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss ^4.x`; adds TS toolchain; `engines.node: ">=20.9.0"`. |
| `api/server.py` (mount point only) | Modified | `WEB_DIR` repointed at `out/`; route handlers untouched. |
| `Makefile` | Modified | `make api` builds Next.js first then runs uvicorn; `make smoke` surface unchanged. |
| `tests/test_smoke.py::test_search_engine_contract` | Possibly modified | If `web/search_urls.js` moves under `src/data/`, the test's `open()` path updates; byte shape preserved. |
| `tests/test_e2e_file_explorer.py`, `tests/test_web_toggle.py` | Modified | DOM selectors updated for the new component tree; `data-*` attribute contract preserved. |
| `extension/manifest.json` | Unchanged | `host_permissions` stays at `["http://localhost:8765/*"]`. |
| `openspec/changes/migrate-nextjs-tailwind4/**` | **Unchanged** | Frozen as planning history. This change does not edit it. |
| `documents-es/openspec/changes/complete-taxa-frontend-migration/**` | New (mirror) | Spanish mirror of this change's artifacts, per AGENTS.md bilingual convention. |

## Risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Approach A default is overridden by spec/design without fresh evidence. | Medium | Override MUST cite G2 (build profile) + G5 (hydration) numbers from the predecessor's `apply-progress.md`; override is logged in `design.md::§1` of this change. |
| Tailwind 4 token namespace shift (`--color-primary` vs `--primary`) breaks plain-CSS `var(--token)` references. | Medium | Alias names in `@theme` so existing `--primary`, `--bg-surface`, `--realm-*` tokens resolve unchanged; parity test enumerates every `var(--token)` reference and asserts a non-empty declaration. |
| `color-mix()` cascade reordering in the 80 KB inline `<style>` block causes visual drift. | Medium | Migrate bespoke rules into `globals.css` inside `@layer base` so source order matches; Playwright visual regression on the existing `tests/test_web_toggle.py` fixture. |
| AC-21 search-engine contract test fails because `web/search_urls.js` location moved. | Medium | Keep the literal under `src/data/search-engines.js` with the same shape; test reads `open()` from the new path. Spec phase decides whether to amend AC-21. |
| Hydration mismatch from `localStorage` reads on server vs client. | Medium | Initial render uses a `mounted` flag; storage reads happen inside `useEffect`; tree structure defaults to the empty state on first paint. |
| Static export forfeits dynamic routes / image optimization used by future work. | Low | Acceptable for v1; switching to full Next.js dev server (Approach B) is the next-change cost if needed. |
| Next.js + React dependency bundle size regresses initial paint (performance budget). | Low | `next build` profile captured before/after; Playwright + Lighthouse sample on the existing chromium fixture; ≤ 0% regression is the success criterion. |
| Single-port contract breaks if the extension's `host_permissions` change accidentally. | Low | Hard rule in Makefile + CI smoke check: `make api` only binds 8765; no second origin added; `manifest.json` is unchanged in this change. |
| Predecessor artifacts drift during this change's apply phase (someone edits `migrate-nextjs-tailwind4/`). | Low | CI / branch-protection rule: this change's PRs MUST NOT modify `openspec/changes/migrate-nextjs-tailwind4/**`; lint hook rejects. |

## Rollback plan

1. **PR-level revert**: `git revert <migration-sha>` restores the
   vanilla `web/` + `tailwind.config.js` + Tailwind 3.4 build
   pipeline. `package-lock.json` keeps the prior dependency state;
   `npm ci` reproduces the lock. `make api` regenerates
   `web/dist/tailwind.css` from the reverted source.
2. **Side effects**: AC-21 contract test reverts to its prior
   `open("web/search_urls.js")` read; backend tests are untouched.
3. **No data migration required**: no DB schema change ships in this
   change.
4. **Extension continuity**: extension talks to
   `http://localhost:8765` before, during, and after the rollback —
   no `manifest.json` update is required to revert.
5. **Predecessor frozen**: rolling back this change does NOT touch
   `openspec/changes/migrate-nextjs-tailwind4/**`. The predecessor
   stays as planning history.
6. **Verification after rollback**: `make smoke` returns to the
   pre-migration baseline (63 passed, 8 skipped on the same fixture
   set, plus existing Playwright runs).

## Dependencies

- `next@^16` (App Router; supports React `^19.0.0`).
- `react@^19`, `react-dom@^19`.
- `tailwindcss` ^4.x.
- `typescript` `>=5.1.0`, `@types/react@^19`,
  `@types/react-dom@^19`, `@types/node` (TS toolchain).
- `next/font` for Raleway, JetBrains Mono, Material Symbols Outlined
  (no new icon set).
- Runtime engine: Node.js `>=20.9.0` (Next.js 16 hard requirement).

## Delivery shape

- **Delivery strategy**: `ask-on-risk` (pre-existing).
- **Chain strategy**: `deferred` (per preflight; set to `auto-chain`
  if sdd-tasks proves the slice count exceeds the 400-line review
  budget).
- **Review budget**: 400 lines per PR.
- **Workload**: the predecessor's `tasks.md` enumerates 35 tasks
  across 14+ sub-PRs. This change re-slices them under Approach A
  and the deferred chain strategy; no sub-PR exceeds the 400-line
  budget.
- **Branch rule**: every sub-PR targets `develop`; branch names
  match `^(feat|fix|chore|...)/[a-z0-9._-]+$`.

## Success criteria

- [ ] Functional parity: every user flow (browse, search, materialize,
      preview, open folder, save URL, view files across all supported
      formats) behaves identically to the legacy build.
- [ ] Performance: no regression in initial paint or interaction
      latency on the existing Playwright + Lighthouse sample
      (≤ 0% delta).
- [ ] Single local origin: `make api` binds only 8765; no second
      dev-server port; extension `host_permissions` unchanged.
- [ ] Backend pytest tests stay green (63 passed, 8 skipped baseline).
- [ ] Playwright suite updated, still green against the new component
      tree; `data-*` attribute contract preserved.
- [ ] AC-21 search-engine contract test passes (file location may
      move; byte shape unchanged unless spec phase revises).
- [ ] Browser-local state and preferences migrate deterministically
      (theme, tree-source, last-taxon-id, kebab-open-id) with one
      read site + one write site per key.
- [ ] Tailwind 4 parity: every utility class and `:root` token
      resolves to a non-empty declaration.
- [ ] Accessibility: every ARIA role, label, and keyboard handler from
      the legacy build is preserved; axe scan has no new violations.
- [ ] Predecessor frozen: `openspec/changes/migrate-nextjs-tailwind4/**`
      is byte-identical before and after this change's apply phase.
- [ ] Rollback: `git revert` of the migration PR restores the legacy
      build with green smoke + Playwright.

## Next step

Spec phase (sdd-spec) reads this proposal plus the predecessor's
`design.md`, `apply-progress.md`, and `cutover-manifest.json`, then
either confirms Approach A or picks B / C with evidence-anchored
rationale. Spec output lands at
`openspec/changes/complete-taxa-frontend-migration/spec.md`. Design
phase then records the picked approach in
`openspec/changes/complete-taxa-frontend-migration/design.md::§1`
(final, not deferred).
