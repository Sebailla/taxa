# Tasks: complete-taxa-frontend-migration

> Strict TDD: RED → GREEN → TRIANGULATE → REFACTOR. Modular-monolith
> rules from
> `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
> apply to every UI/file unit. **Approach A is FINAL** (locked
> 2026-09-02; recorded in `design.md::§1`); no override path is open.
> **Predecessor `migrate-nextjs-tailwind4/` is frozen** — its files
> MUST stay byte-identical through this change's apply phase.

> **2026-09-02 — corrective plan revision**. The 13-child Feature
> Branch Chain topology was reordered and rescoped after the apply
> gate identified a dependency-order defect: original PR 3a required
> `next build`/`out/index.html` before the Next/React/Tailwind/
> TypeScript toolchain and the Node ≥ 20.9.0 runtime contract
> existed (those landed in original PR 3c, AFTER original PR 3a).
> The corrected topology introduced a **toolchain bootstrap PR at
> position 1** (which absorbed the `package.json` dep pins and
> `scripts/check-runtime.mjs` previously attributed to original
> PR 3c), demoted the **App Router static export** to position 2
> (now safe to test against `out/index.html` because the toolchain
> already exists), kept **Tailwind/tokens** at position 3, fused
> the **Makefile rewrite** with the `WEB_DIR` repoint + AC-21 into
> position 4, and followed with **state → ports → e2e → validation
> → atomic cutover** in dependency-correct order. The 13-child
> count was preserved at that revision; only the chain topology,
> per-child scope, and per-child test witnesses changed.
> **Approach A, FastAPI/SQLite, and the frozen predecessor
> remained unchanged.**

> **2026-09-02 — PR 3c sub-sequence replan (this entry)**. After
> PR #144 (3a), PR #145 (3b), and PR #146 (3b reconcile) landed on
> the tracker, the original single PR 3c was diagnosed as
> unsatisfiable: it claimed ~230 LoC while porting every legacy
> `:root` token, `[data-theme="dark"]` palette, `--realm-*`
> family, `@keyframes`, `.animate-spin`, `color-mix()` selectors,
> the bespoke rules in the legacy inline `<style>` block of
> `web/index.html` (lines 14–1972 = **1,963 lines**), and the
> design-system barrel — far beyond the 400-line review budget.
> The user authorized a chained sub-sequence that replaces the
> single PR 3c with **four reviewable children at positions 3–6**
> (`3c-i`, `3c-ii`, `3c-iii`, `3c-iv`), each ≤ 400 authored lines
> including tests. Every later child is **renumbered** to keep the
> dependency contract linear: `3d → 7`, `4a → 8`, `4b → 9`,
> `5a → 10`, `5b → 11`, `5c → 12`, `6a → 13`, `6b → 14`,
> `6c → 15`, `3e → 16`. The new **16-child** chain begins with
> **3c-i basing off the tracker** (i.e. the
> `docs/complete-taxa-frontend-migration-plan` branch **after**
> PR #146 reconciliation merges), so the 3c sub-sequence picks up
> the already-merged 3a + 3b + reconcile without an extra reconcile
> step. Total authored LoC rises from ~2,245 to ~3,485 because
> every legacy CSS rule must be ported; the largest new sub-PR
> is **3c-i at ~390 LoC** (-10 LoC headroom under 400).
> PR 3a retains the regenerated-`package-lock.json`
> size:exception (generated-resolution-only) as the
> prior documented size:exception; **PR 3c-ii
> subsequently opens a second user-approved
> size:exception** for the complete taxonomy tree /
> detail CSS slice (actual implementation totals
> 822 insertions + 9 deletions = 831 LoC, overshooting
> the prior `~380 LoC` estimate by +442 LoC and the
> 400-line per-PR review budget by +431 LoC — see the
> dedicated append-only addendum below for the
> authorization rationale and the corrected estimate;
> the 16-child chain is preserved). **Approach A,
> FastAPI/SQLite, the frozen predecessor, and the
> Feature Branch Chain strategy remain unchanged.**

> **2026-09-02 — dependency-defect fix (this revision)**. The apply
> gate's pre-flight re-audit identified a second dependency
> defect inside the corrected topology: PR 3b's
> `src/app/layout.tsx` imported `@taxa/app-shell` (a module PR 4b
> ships at position 9/16 — *later* in the chain) and
> `./globals.css` (a file PR 3c-i ships at position 3/16 — *later*
> in the chain). At its `next build` witness, neither target file
> existed yet, so the witness was unsatisfiable. The same audit
> flagged PR 3b.5's triangulation assertion that the generated
> `out/_next/static/chunks/*.js` references the typed store barrel
> path `@taxa/browser-state` — that barrel file does not exist
> until PR 4a lands. **PR 3b is rescoped to a self-contained App
> Router static-export bootstrap**: `src/app/{layout,page}.tsx`
> become minimal semantic placeholders (Raleway preload only)
> that import **neither** `@taxa/app-shell` **nor**
> `./globals.css`; the `import "./globals.css";` line moves into
> PR 3c-i (which already owns `globals.css`); the `<AppShell>`
> integration into `src/app/layout.tsx` / `src/app/page.tsx`
> moves into PR 4b (which already owns
> `src/modules/app-shell/**`). PR 3b.5's unsatisfiable
> `@taxa/browser-state` reference is dropped (the path-alias
> contract is already verified by `tests/test_toolchain_bootstrap.py::3a.7`)
> and replaced with the Raleway `.woff2` file assertion. **The
> 13-child topology and ordering are preserved**; PR 3b's
> `out/index.html` / viewport / Raleway preload test evidence
> stays. Budgets are recalculated: PR 3b shrinks to ~150 LoC
> (-25), PR 3c-i grows by ~2 LoC (1-line `globals.css` import),
> PR 4b grows by ~30 LoC (AppShell integration seam); total
> authored ~2,282 LoC across the 13 sub-PRs; each sub-PR stays
> well under the 400-line review budget; **only the prior PR 3a
> `package-lock.json` exception remains**. Approach A,
> FastAPI/SQLite, the frozen predecessor, the per-domain specs,
> and the validation gates stay unchanged.

## Scope boundary for this tasks file

- **In scope**: every sub-PR under Approach A listed in `design.md`
  §"Sub-PR slice under Approach A" (positions 1 / 16 through 16 / 16
  in the corrected chain: toolchain bootstrap, App Router static
  export, **3c-i tokens/base/dark mode, 3c-ii taxonomy tree/detail
  styling, 3c-iii Search/Folder/global Browser styling, 3c-iv
  animations/utilities + final CSS parity + design-system barrel**,
  Makefile/mount, 4a, 4b, 5a, 5b, 5c, 6a, 6b, 6c, 3e) plus the
  **Phase 6 validation block** (G5 reconstruction / G6 rehearsal
  authoring / G4 measurement) that
  runs **after the complete candidate path is accumulated on the
  tracker branch `docs/complete-taxa-frontend-migration-plan`**
  but **before** PR 3e can land. PR 3e (atomic cutover) ships only
  when all six gates are green.
- **G4 / G5 / G6 closure is validation work**, not a standalone
  migration objective: their artifacts are recorded in
  `apply-progress.md` §Change log as gate-flips, and they MUST NOT
  generate new `web/**` source, new `api/server.py` route handlers,
  or new `extension/**` files. The closure tests/measurers run
  against the already-landed candidate build (positions 1–12) under
  the chromium fixture the predecessor captured.
- **Predecessor frozen**: `openspec/changes/migrate-nextjs-tailwind4/**`
  is read-only history. Branch-protection rejects any PR that edits
  it. Phase 6 references the predecessor's `apply-progress.md` and
  `cutover-manifest.json` only as planning inputs.
- **FastAPI backend invariants preserved**: route handlers,
  SQLite/WAL logic, materialize flow, `save-url` SSRF defence, and
  `/api/*` byte shapes stay unchanged. `api/server.py:54` (the
  `WEB_DIR` constant) is the only line that may change in `api/server.py`
  under Approach A, plus the `next/font` `<link rel="preload">` /
  `StaticFiles` SPA fallback middleware strictly required to serve
  `out/index.html` from the existing `StaticFiles(html=True)` mount.
- **Strict TDD enforced**: every implementation task writes its
  failing test FIRST. Tasks follow `R` (RED), `G` (GREEN), `T`
  (TRIANGULATE — extra scenarios beyond the minimum that fail the
  first GREEN), `Refactor` (clean-up without behaviour drift)
  markers.
- **Dependency-order contract**: no sub-PR may require a file that
  its predecessors have not yet produced. The corrected chain
  enforces `toolchain bootstrap` → `App Router static export` →
  **`3c-i tokens/base/dark mode` → `3c-ii taxonomy tree/detail
  styling` → `3c-iii Search/Folder/global Browser styling` →
  `3c-iv animations/utilities + final CSS parity`** → `Makefile/
  mount` → `state` → `ports` → `e2e` → `validation` → `atomic
  cutover`. PR 3a (toolchain bootstrap) lands before any PR that
  calls `next build`; the App Router static export depends on
  `next`, `react`, `react-dom`, `typescript`, `tailwindcss` being
  installed and on the Node ≥ 20.9.0 check existing; PR 3c-i
  depends on `tailwindcss@^4` being installed; PRs 3c-ii / 3c-iii /
  3c-iv depend on the prior 3c sub-child having shipped its CSS
  tokens / selectors / utilities in source order; the Makefile
  rewrite depends on the toolchain + Tailwind + the full CSS
  cascade being installed so `npm run build:web` resolves; the
  `WEB_DIR` repoint depends on `out/index.html` being produced by
  the Makefile `api` target; the typed store + hydration guard
  depend on App Router + Tailwind being live; the capability ports
  depend on the typed store being live (for `tree-source` and
  `last-taxon-id`); `e2e` updates depend on the capability ports;
  Phase 6 validation depends on the complete candidate path; PR 3e
  depends on all six gates being green.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~3,485 authored across **16 sub-PRs** (toolchain bootstrap + App Router static export + **3c-i tokens/base/dark mode + 3c-ii taxonomy tree/detail styling + 3c-iii Search/Folder/global Browser styling + 3c-iv animations/utilities + final CSS parity** + Makefile/mount + 2 browser-state + 2 capability ports + e2e/delete-legacy + 3 Phase 6 validation + 1 atomic cutover). The +1,240 LoC delta from the prior ~2,245 estimate comes entirely from the 3c sub-sequence: the legacy inline `<style>` block in `web/index.html` (1,963 lines) must be ported verbatim into Tailwind 4 `@theme` + `@layer base` and a parity test must enumerate every legacy `:root` token, `var(--name)` reference, `--realm-*` selector, `@keyframes`, `.animate-spin`, `color-mix()` selector, and utility class. |
| 400-line budget risk | **Low** for authored work in every child **except PR 3c-ii, which carries a user-approved size:exception for the complete taxonomy tree / detail CSS slice — see the dedicated addendum below**. Largest new sub-PR by actual diff is **PR 3c-ii at 831 LoC** (822 insertions + 9 deletions; overshoot +431 LoC against the 400-line budget); the other 3c children are 3c-i ~390, 3c-iii ~390, 3c-iv ~280. The previously-largest 5b stays at ~360 LoC; 3d stays at ~240 LoC. **All 16 sub-PRs ≤ 400 LoC authored except PR 3c-ii**, which carries the user-approved size:exception (the prior PR 3a regenerated-`package-lock.json` exception is generated-resolution-only and stays open as the second documented size:exception alongside PR 3c-ii). |
| Chained PRs recommended | **Yes** — 16 chained child PRs (~3,485 total authored lines ≫ 400, and the atomic cutover requires the feature to integrate before it reaches `develop`). The 3c sub-sequence alone is now four reviewable children, each holding ~280–390 LoC, so no child carries the 1,963-line inline CSS burden. |
| Suggested split | PR 3a (toolchain bootstrap) → 3b (App Router static export) → **3c-i (tokens / base / dark mode)** → **3c-ii (taxonomy tree / detail styling)** → **3c-iii (Search / Folder / global Browser styling)** → **3c-iv (animations / utilities + final CSS parity + design-system barrel)** → 3d (Makefile/mount) → 4a → 4b → 5a → 5b → 5c → Phase 6a (G5) → Phase 6b (G6) → Phase 6c (G4 measurement) → PR 3e (atomic cutover, gated) |
| Delivery strategy | ask-on-risk (per preflight; Approach A already locked, no override open) |
| Chain strategy | **feature-branch-chain** (user-selected, unchanged by the 3c replan). Tracker `docs/complete-taxa-frontend-migration-plan` is draft/no-merge and is the **only** PR targeting `develop`. PR 3a targets the tracker; PR 3b targets PR 3a; **PR 3c-i targets the tracker** (i.e. the branch **after** PR #146 reconciliation merges, picking up the already-merged 3a + 3b + reconcile without an extra reconcile step); every later child targets its immediate predecessor branch. Supersedes the `AGENTS.md` §4 direct-to-`develop` default for this change. |

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Low (PR 3a generated package-lock.json exception approved)
```

### Chain topology (Feature Branch Chain)

The tracker branch already exists: **`docs/complete-taxa-frontend-migration-plan`**
(referenced as **PR #146** in the project's PR numbering, the
merged starting point for the first new CSS child).
It stays **draft / no-merge** until all 16 child PRs are reviewed
and integrated. **Nothing reaches `develop` until the tracker
merges.**

> **Reordering rationale (corrective plan revision)**. Original
> `apply-progress.md` placed App Router entry at position 1 with
> a `next build` → `out/index.html` witness that required
> `next`, `react`, `tailwindcss`, `typescript` to be installed and
> the Node ≥ 20.9.0 runtime check to exist; the toolchain itself
> was scheduled for position 3, AFTER the App Router witness had
> to be green. The corrected topology moved the toolchain to
> position 1, demoted the App Router witness to position 2 (now
> satisfiable), kept Tailwind/tokens at position 3 (depends on
> Tailwind installed), fused the Makefile rewrite with the
> `WEB_DIR` repoint at position 4 (depends on `next build`
> producing `out/`), then followed with state, ports, e2e, Phase 6
> validation, and the atomic cutover. The 13-child count was
> preserved at that revision.

> **PR 3c sub-sequence replan rationale (this entry)**. The
> original single PR 3c at position 3 claimed ~230 LoC but had
> to port every legacy `:root` token, the `[data-theme="dark"]`
> palette, the `--realm-*` family, the bespoke `@keyframes`
> animations, `.animate-spin`, `color-mix()` selectors, and the
> design-system barrel — i.e. the bulk of the 1,963-line inline
> `<style>` block in `web/index.html`. PR #144 (3a), PR #145 (3b),
> and PR #146 (3b reconcile) had already landed on the tracker.
> The user authorized a chained sub-sequence that replaces the
> single PR 3c with **four reviewable children at positions 3–6**
> (`3c-i`, `3c-ii`, `3c-iii`, `3c-iv`), each ≤ 400 authored lines
> including tests, and renumbers the later children to keep the
> dependency contract linear (3d → 7, 4a → 8, 4b → 9, 5a → 10,
> 5b → 11, 5c → 12, 6a → 13, 6b → 14, 6c → 15, 3e → 16). PR
> 3c-i **bases off the tracker** (the
> `docs/complete-taxa-frontend-migration-plan` branch **after**
> PR #146 reconciliation merges) so the 3c sub-sequence picks up
> the already-merged 3a + 3b + reconcile without an extra
> reconcile step. Total authored LoC rises from ~2,245 to ~3,485
> because every legacy CSS rule is ported; the largest new
> sub-PR is **3c-i at ~390 LoC** (-10 LoC headroom under 400); **PR 3c-ii's actual implementation totals 831 LoC (822 insertions + 9 deletions), overshooting the prior `~380 LoC` estimate by +442 LoC and the 400-line per-PR review budget by +431 LoC — the user approved a second size:exception for this slice (the PR 3a regenerated-`package-lock.json` exception remains open as the prior documented size:exception); see the dedicated append-only addendum below for the authorization rationale; the 16-child chain is preserved.**

| Position | Sub-PR | Branch | Base (PR target) |
|---|---|---|---|
| Tracker | — | `docs/complete-taxa-frontend-migration-plan` | `develop` — **draft / no-merge** (now carries PR #144 + #145 + #146 merges) |
| 1 / 16 | 3a | `feat/complete-taxa-frontend-migration-01-3a` | `docs/complete-taxa-frontend-migration-plan` (tracker, **PR #144 already merged**) |
| 2 / 16 | 3b | `feat/complete-taxa-frontend-migration-02-3b` | `feat/complete-taxa-frontend-migration-01-3a` (**PR #145 already merged**) |
| 3 / 16 | 3c-i | `feat/complete-taxa-frontend-migration-03-3c-i` | `docs/complete-taxa-frontend-migration-plan` (tracker, **after PR #146 reconciliation merges**) |
| 4 / 16 | 3c-ii | `feat/complete-taxa-frontend-migration-04-3c-ii` | `feat/complete-taxa-frontend-migration-03-3c-i` |
| 5 / 16 | 3c-iii | `feat/complete-taxa-frontend-migration-05-3c-iii` | `feat/complete-taxa-frontend-migration-04-3c-ii` |
| 6 / 16 | 3c-iv | `feat/complete-taxa-frontend-migration-06-3c-iv` | `feat/complete-taxa-frontend-migration-05-3c-iii` |
| 7 / 16 | 3d | `feat/complete-taxa-frontend-migration-07-3d` | `feat/complete-taxa-frontend-migration-06-3c-iv` |
| 8 / 16 | 4a | `feat/complete-taxa-frontend-migration-08-4a` | `feat/complete-taxa-frontend-migration-07-3d` |
| 9 / 16 | 4b | `feat/complete-taxa-frontend-migration-09-4b` | `feat/complete-taxa-frontend-migration-08-4a` |
| 10 / 16 | 5a | `feat/complete-taxa-frontend-migration-10-5a` | `feat/complete-taxa-frontend-migration-09-4b` |
| 11 / 16 | 5b | `feat/complete-taxa-frontend-migration-11-5b` | `feat/complete-taxa-frontend-migration-10-5a` |
| 12 / 16 | 5c | `feat/complete-taxa-frontend-migration-12-5c` | `feat/complete-taxa-frontend-migration-11-5b` |
| 13 / 16 | 6a | `feat/complete-taxa-frontend-migration-13-6a` | `feat/complete-taxa-frontend-migration-12-5c` |
| 14 / 16 | 6b | `feat/complete-taxa-frontend-migration-14-6b` | `feat/complete-taxa-frontend-migration-13-6a` |
| 15 / 16 | 6c | `feat/complete-taxa-frontend-migration-15-6c` | `feat/complete-taxa-frontend-migration-14-6b` |
| 16 / 16 | 3e | `feat/complete-taxa-frontend-migration-16-3e` | `feat/complete-taxa-frontend-migration-15-6c` |

    ```text
    develop
     └── docs/complete-taxa-frontend-migration-plan   ← tracker PR (draft / no-merge; carries PR #144 + PR #145 + PR #146)
          ↑ PR 3a base: docs/complete-taxa-frontend-migration-plan
          └── feat/complete-taxa-frontend-migration-01-3a   ← toolchain bootstrap (PR #144 merged)
               ↑ PR 3b base: …-01-3a
               └── feat/complete-taxa-frontend-migration-02-3b   ← App Router static export (PR #145 merged)
                    ↑ PR 3b-reconcile base: …-02-3b
                    └── feat/complete-taxa-frontend-migration-02-3b-reconcile   ← 3b reconcile (PR #146 merged)
                         ↑ PR 3c-i base: tracker (after PR #146)
                         └── feat/complete-taxa-frontend-migration-03-3c-i   ← tokens / base / dark mode
                              ↑ PR 3c-ii base: …-03-3c-i
                              └── feat/complete-taxa-frontend-migration-04-3c-ii   ← taxonomy tree / detail styling
                                   ↑ PR 3c-iii base: …-04-3c-ii
                                   └── feat/complete-taxa-frontend-migration-05-3c-iii   ← Search / Folder / global Browser styling
                                        ↑ PR 3c-iv base: …-05-3c-iii
                                        └── feat/complete-taxa-frontend-migration-06-3c-iv   ← animations / utilities + final CSS parity + design-system barrel
                                             ↑ PR 3d base: …-06-3c-iv
                                             └── feat/complete-taxa-frontend-migration-07-3d   ← Makefile/mount
                                                  ↑ … 4a → 4b → 5a → 5b → 5c → 6a → 6b → 6c …
                                                  └── feat/complete-taxa-frontend-migration-16-3e
                                                       ← atomic cutover, last child in the chain
    ```

**Per-sub-PR dependency (the contract the corrective plan
revision **and** the PR 3c sub-sequence replan enforce)**:

- **PR 3a — toolchain bootstrap**. Self-contained. Produces
  `package.json` (with `next`, `react`, `react-dom`,
  `tailwindcss`, `typescript`, `@types/react`, `@types/react-dom`,
  `@types/node` pinned; `engines.node ">=20.9.0"`; `scripts.check-runtime`
  and `scripts.build:web` scripts), `scripts/check-runtime.mjs`,
  `tsconfig.json` (modified in place; the predecessor
  already exists at repo root; base config + `@taxa/<capability>`
  path aliases), and `.nvmrc`. Verification: `npm ci`
  exits 0;
  `node scripts/check-runtime.mjs` exits 0 on Node ≥ 20.9.0,
  exits non-zero below; `npx tsc --noEmit` resolves every
  `@taxa/*` alias (against an empty alias map; subsequent PRs
  populate the modules). **Already merged as PR #144 on the
  tracker.**
- **PR 3b — App Router static export**. Depends on **3a**: deps
  installed + Node ≥ 20.9.0 contract. Produces
  `src/app/{layout,page}.tsx`, `next.config.mjs`, and the
  `tests/test_app_shell_render.py` witness that runs `npx next
  build` and reads `out/index.html`. This witness is satisfiable
  here because the toolchain is live; it could not be satisfied in
  the original ordering because `npx next build` had no `next`
  binary yet. **Already merged as PR #145 on the tracker, with
  PR #146 reconciliation also merged.**
- **PR 3c-i — tokens / base / dark mode (position 3)**. Depends
  on **3a** (`tailwindcss@^4` installed). Bases off **the
  tracker after PR #146 lands**, picking up 3a + 3b + reconcile
  without an extra reconcile step. Produces the first slice of
  `src/app/globals.css` (`@import "tailwindcss";` + the `@theme`
  block with every legacy `:root` token + the `[data-theme="dark"]`
  palette + the `--realm-*` family + the `@layer base` reset
  block covering `html`, `body`, `main > :first-child`, and the
  dark-mode cascade). Parity test enumerates every legacy `:root`
  token + `var(--name)` reference for this slice and asserts a
  non-empty declaration in the generated
  `out/_next/static/chunks/*.css`.
- **PR 3c-ii — taxonomy tree / detail styling (position 4)**.
  Depends on **3c-i** (token + base layer live, so every selector
  in this slice resolves `var(--token)` references). Produces the
  next slice of `src/app/globals.css` covering the legacy
  `.tier-header`, `.tree-row`, `.rank-badge`, `.scientific-name`,
  `.tree-source-toggle`, `#detail-panel`, `.detail-card`,
  `.detail-section`, `.overview-section`, `.detail-item`,
  `.search-pulse`, `body { overscroll-behavior: none; … }` reset,
  the kebab menu selectors, and the realm-tinted `.tree-row[data-realm=...]`
  variants. Parity test enumerates every legacy selector in this
  slice and asserts presence in the generated CSS.
  **Size:exception**: the actual implementation totals
      **831 LoC (822 insertions + 9 deletions)**, overshooting the
      prior `~380 LoC` estimate by +442 LoC and the 400-line per-PR review
      budget by +431 LoC; the user approved a second
      `size:exception` for this slice — see the dedicated
      append-only addendum below for the authorization
      rationale (the 16-child chain is preserved; the PR
      is NOT claimed merged or verified by this note).
- **PR 3c-iii — Search / Folder / global Browser styling
  (position 5)**. Depends on **3c-ii** (taxonomy selectors live;
  `var(--token)` references in browser selectors resolve). Produces
  the next slice of `src/app/globals.css` covering `.detail-tabs`,
  `.search-icon-btn`, `.materialize-btn`, the materialize modal
  (`.materialize-modal-*`), the toast (`.toast`, `.toast-error`),
  the search engines grid (`.search-engines-grid`,
  `.search-category-header`, `.search-engine-btn`), the file
  explorer chrome (`.fex-meta-strip`, `.fex-tab-strip`,
  `.fex-snippet-frame`, `.fex-shell`, `.fex-tree-pane`,
  `.fex-viewer-pane`, `.fex-splitter`, `.fex-row` and its
  `.selected`/`.file`/`.folder` variants, `.fex-tree-header`,
  `.fex-children`, `.fex-banner`, `.fex-empty-state`), the search
  input + toggle row (`.fex-search-*`), the CSV scroller
  (`.fex-csv-*`), the JSON tree viewer (`.fex-json-*`), and the
  truncation banner (`.fex-tree-truncated`). Parity test enumerates
  every legacy browser/search selector and asserts presence in
  the generated CSS.
- **PR 3c-iv — animations / utilities + final CSS parity
  (position 6)**. Depends on **3c-iii** (full legacy CSS cascade
  now ported except `@keyframes` + utilities). Produces the final
  slice of `src/app/globals.css` covering `@keyframes
  detail-card-enter`, `@keyframes detail-card-leave`, `@keyframes
  search-pulse-anim`, `@keyframes materialize-spin`, `@keyframes
  toast-slide-in`, `.animate-spin`, the image + video viewer frames
  (`.fex-image-frame`, `.fex-image`, `.fex-image-advisory`,
  `.fex-video-frame`, `.fex-video-el`), and the Settings view
  (`.settings-shell`, `.settings-header`, `.settings-list`,
  `.settings-row`, `.settings-theme-toggle`,
  `.settings-action-btn`, `.settings-link-btn`). Also produces the
  `src/modules/design-system/{infrastructure/index.ts,
  presentation/Icon.tsx, presentation/Button.tsx}` barrel. Parity
  test enumerates every `@keyframes` rule + utility class the
  legacy build emits and asserts presence in the generated CSS;
  design-system purity test strips hex literals from `src/`
  outside the design-system module.
- **PR 3d — Makefile/mount (position 7)**. Depends on **3c-iv**
  (full Tailwind 4 cascade ported so `next build` produces a
  complete CSS payload) and **3b** (App Router produces
  `out/index.html` when `next build` runs). Produces
  `Makefile::api` rewrite (`check-runtime.mjs` → `npm run build:web`
  → `uvicorn … --port 8765` in order, with `make css` becoming a
  no-op shim), the 1-line `api/server.py:54` `WEB_DIR` repoint,
  `src/data/search-engines.js` (byte copy of `web/search_urls.js`
  with `SEARCH_ENGINES` named export), the `tests/test_smoke.py`
  `open()` path update (AC-21 contract preserved), and the
  `tests/test_make_api_build.py` witness plus
  `tests/test_static_mount.py` witness.
- **PR 4a — typed store (position 8)**. Depends on **3c-iv**
  (design-system module loaded) and **3d** (now position 7);
  produces `src/modules/browser-state/**` typed store with four
  read + four write sites.
- **PR 4b — hydration guard (position 9)**. Depends on **4a**
  (store available) and **3b** (`AppShell` host composition;
  hydration-safe `mounted` flag). Produces `src/modules/app-shell/**`
  and the Playwright zero-hydration-warnings witness.
- **PR 5a — taxonomy port (position 10)**. Depends on **4b**
  (hydration-safe state read for `tree-source`). Produces
  `src/modules/taxonomy/**` + the port of `web/{tree,
  detail,breadcrumb}.js` to React.
- **PR 5b — research port + CDN pin (position 11)**. Depends on
  **5a** (taxonomy state read flows shared with research) and
  **3d** (`src/data/search-engines.js` for the `Engine` named
  export). Produces `src/modules/research/**` + CDN pin.
- **PR 5c — E2E selectors + `data-*` contract + delete legacy
  (position 12)**. Depends on **5b** (all UI components live).
  Deletes `web/*.{html,js,css}` + `tailwind.config.js`.
- **PR 6a / 6b / 6c — Phase 6 validation (positions 13 / 14 / 15)**.
  Depends on **5c** (candidate path complete). Author the three
  gate-closure verifiers against the candidate build.
- **PR 3e — atomic cutover (position 16)**. Depends on all six
  gates green. Flips `cutover-manifest.json` working copy, re-runs
  G3 Tier-2 verifier against the activated selection, flips
  `apply-progress.md` §Status footer.

**Integration flow**: children merge **in order** into the
tracker. As each child merges, the next child is retargeted onto
the tracker (GitHub retargets automatically when the base branch
is merged and deleted); the tracker accumulates the full feature.
Once PR 3e (the last child) merges, the tracker leaves draft and
merges to `develop` as the single integration point.

**Every child PR body MUST carry** the `## Chain Context`
section (Chain / Tracker PR / Position / Base / Depends on /
Follow-up / Review budget / Starts at / Ends with) plus a
dependency diagram marking the current PR with `📍`. The Chain
Context section is **appended** to the repo PR template — it
does not replace the required `## Resumen` / `## Cambios` /
`## Validación` / `## Lo que NO cambió` sections.

**Diff hygiene**: a child PR whose diff shows files outside its
own slice is a **base bug**, not a review finding. Retarget or
rebase onto the correct predecessor until only the current work
unit appears.

> Order: **3a → 3b → 3c-i → 3c-ii → 3c-iii → 3c-iv → 3d → 4a →
> 4b → 5a → 5b → 5c → 6a (G5) → 6b (G6) → 6c (G4 measurement) →
> 3e**. Each child PR targets its **immediate predecessor
> branch**, except PR 3c-i which **targets the tracker** (the
> `docs/complete-taxa-frontend-migration-plan` branch after PR
> #146 reconciliation merges, picking up the already-merged 3a +
> 3b + reconcile). Only the tracker targets `develop`. Phase 6
> runs **after** the complete candidate path (positions 1–12) is
> green and accumulated on the tracker, and **before** PR 3e can
> land. PR 3e is gated on G1 + G2 + G3 Tier-1 (all recorded from
> the predecessor) plus G4 + G5 + G6 closure (all three delivered
> by Phase 6). Rollback =
> `git revert <pr3e-sha>` (see §"Rollback under the chain").

## Strict-TDD markers

Every task below uses one of four markers, matching the
predecessor's task vocabulary and the
`tests/test_module_layers.py` /
`tests/test_no_restricted_imports.py` strict-TDD precedent:

- `R` — RED. Author the failing test (or expanded assertion)
  FIRST. The repo MUST remain green before the test is added; the
  new test MUST fail for the right reason before any production
  code is written.
- `G` — GREEN. Implement the minimum production code that flips
  the RED to GREEN. No scope creep beyond the failing test.
- `T` — TRIANGULATE. Add the additional scenarios that catch the
  next failure mode (parametrised matrix, edge cases, RFC-2119-style
  "and / and / and" clauses). Each triangulation scenario lands
  with its own failing-test-then-pass assertion cycle.
- `Refactor` — Clean up GREEN code (rename, extract, dedupe).
  Tests MUST stay green; the refactor MUST NOT change observable
  behaviour or push the diff over the 400-line review budget.

## Phase 3a: Toolchain bootstrap (PR 3a → tracker branch)

Installs the Next 16 / React 19 / Tailwind 4 / TypeScript
toolchain, pins the Node ≥ 20.9.0 runtime contract, and writes
the repository conventions every subsequent sub-PR depends on.
**This PR MUST land before any other sub-PR in the chain** —
the App Router static export at position 2 cannot satisfy its
`next build` witness without the toolchain installed here.

Rescoped from the original `tasks.md` of
2026-09-02 (which placed this work in `Phase 3c` AFTER the
App Router entry): the dependency-order defect the apply gate
identified moved the `package.json` dep pins, the
`scripts/check-runtime.mjs` Node-runtime check, the
`tsconfig.json` base + path-alias config, and the `.nvmrc`
helper forward into position 1. Original Phase 3c's
`Makefile::api` rewrite alone moves into position 7 (`Phase 3d`
in the corrected topology, with the four CSS children inserted
at positions 3–6).

- [ ] 3a.1 R — `tests/test_toolchain_bootstrap.py` (new): reads
      `package.json` and asserts (a) `engines.node` literal equals
      `">=20.9.0"`, (b) every required dep is present in
      `dependencies` or `devDependencies` —
      `next@^16`, `react@^19`, `react-dom@^19`,
      `tailwindcss@^4`, `typescript@>=5.1.0`,
      `@types/react@^19`, `@types/react-dom@^19`,
      `@types/node` — and the legacy `autoprefixer`, `postcss`,
      `@tailwindcss/forms` are absent; asserts
      `scripts.check-runtime` and `scripts.build:web` are
      defined; asserts `tsconfig.json` exists at the repo root
      with `compilerOptions.paths` containing the
      `@taxa/<capability>` aliases that match the predecessor
      `tests/test_module_layers.py::CAPABILITIES` set; asserts
      `.nvmrc` exists and pins Node ≥ 20.9.0 (literal). The test
      MUST fail on a fresh repo clone (no `package.json` deps
      yet). <!-- sdd-owner: implementation -->
- [ ] 3a.2 G — `package.json` (modified, ~50 LoC delta) plus regenerated `package-lock.json` (the sole user-approved size exception for the regenerated `package-lock.json` of this PR; it must contain only resolution changes required by this manifest and be reviewed together with it — **PR 3c-ii subsequently opens a second user-approved size:exception** for the complete taxonomy tree / detail CSS slice, 831 LoC = 822 insertions + 9 deletions; see the dedicated append-only addendum below for the authorization rationale): bumps
      `next`, `react`, `react-dom`, `tailwindcss` to the
      pinned major versions above; adds the TypeScript
      toolchain; removes the legacy `autoprefixer`, `postcss`,
      `@tailwindcss/forms`; sets
      `engines.node = ">=20.9.0"`; adds
      `scripts.check-runtime = "node scripts/check-runtime.mjs"`
      and `scripts.build:web = "next build"`. No other
      fields change. <!-- sdd-owner: implementation -->
- [ ] 3a.3 G — `scripts/check-runtime.mjs` (new, ~25 LoC):
      compares `process.versions.node` against the required
      `20.9.0` floor (encoded as a literal in the script so
      the test asserts it); exits non-zero with a clear error
      naming the observed vs required Node version when below
      the floor; exits 0 on ≥ 20.9.0. <!-- sdd-owner: implementation -->
- [ ] 3a.4 G — `tsconfig.json` (modified in place; the predecessor already exists at repo root; ~50 LoC delta):
      base TypeScript config — `compilerOptions.target`,
      `module`, `moduleResolution`, `jsx`, `strict`,
      `noUncheckedIndexedAccess`, `paths` (the
      `@taxa/<capability>` aliases mapped to
      `src/modules/<capability>`), `baseUrl`. The alias
      contract matches the `CAPABILITIES` set the predecessor
      ships in `tests/test_module_layers.py`. No `src/**`
      files yet — `npx tsc --noEmit` against an empty
      `include: ["src/**/*.ts", "src/**/*.tsx"]` is a no-op
      (the alias map is in place even before any module
      file exists; subsequent PRs add module files). <!-- sdd-owner: implementation -->
- [ ] 3a.5 G — `.nvmrc` (new, 1 LoC): contains the literal
      `20` (nvm will resolve to the latest 20.x.y, which is
      ≥ 20.9.0 once Node 20.9 ships; the `engines.node`
      declaration is the binding contract, `.nvmrc` is a
      convenience hint). <!-- sdd-owner: implementation -->
- [ ] 3a.6 R — `tests/test_check_runtime.py` (new): mocks
      `process.versions.node` (via a small `require`-time
      shim or by patching `process.versions` inside a child
      Node process) to (a) a value below `20.9.0` and asserts
      `scripts/check-runtime.mjs` exits non-zero with a clear
      stderr line naming the observed version; (b) a value
      at or above `20.9.0` and asserts it exits 0. The test
      runs via `subprocess.run([node, scripts/check-runtime.mjs])`
      in two scenarios by passing a small override file
      `scripts/_test-check-runtime.mjs` that throws before
      reaching the floor check. <!-- sdd-owner: implementation -->
- [ ] 3a.7 T — `tests/test_toolchain_bootstrap.py`
      triangulation: assert (a) the `engines.node` literal is
      `">=20.9.0"` exactly (no `~`, `^`, or pinned
      sub-version drift); (b) every pinned dep satisfies
      `^MAJOR` with the major version listed above (no
      `next@^15` sneaking back); (c) `scripts.check-runtime`
      starts with the literal `node scripts/check-runtime.mjs`
      (not `nodejs` and not a path with whitespace); (d)
      `tsconfig.json::paths` resolves every entry in the
      `CAPABILITIES` set the predecessor pins; (e) `.nvmrc`
      is exactly the `20` literal (single line, trailing
      newline). <!-- sdd-owner: implementation -->
- [ ] 3a.8 Refactor — alphabetise `package.json` dependency
      keys; ensure `tsconfig.json` field ordering matches the
      TS 5.x canonical template; ensure `scripts/check-runtime.mjs`
      reads the floor from a `package.json::engines.node`
      parse (instead of a hardcoded literal) so a future bump
      is a single-file change. <!-- sdd-owner: implementation -->

**Per-task evidence (focused test + runtime + rollback)**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3a.1 | `.venv/bin/python3 -m pytest tests/test_toolchain_bootstrap.py -v` | `ls package.json scripts/check-runtime.mjs tsconfig.json .nvmrc` non-empty | `git revert <3a-sha>` removes `scripts/check-runtime.mjs`, `.nvmrc`, restores `tsconfig.json` to its predecessor state, restores `package.json` and `package-lock.json` to legacy deps; nothing else touched |
| 3a.2 | same | `node -e "const p=require('./package.json'); assert(p.engines.node === '>=20.9.0')"`; `npm ci` exit 0 | same |
| 3a.3 | `.venv/bin/python3 -m pytest tests/test_check_runtime.py -v` | `node scripts/check-runtime.mjs` exit 0 on Node ≥ 20.9.0, exit 1 below | same |
| 3a.4 | same as 3a.1 (alias assertions) | `npx tsc --noEmit` exit 0 against the (empty) `src/**` tree | same |
| 3a.5 | same as 3a.1 (`.nvmrc` literal assertion) | `cat .nvmrc` returns `20` literal | same |
| 3a.6 | `.venv/bin/python3 -m pytest tests/test_check_runtime.py -v` | two scenarios above | same |
| 3a.7 | same as 3a.1 | same as 3a.1 | same |
| 3a.8 | same as 3a.1 + 3a.3 | same as 3a.1 + 3a.3 | same |

## Phase 3b: App Router static-export bootstrap (PR 3b → PR 3a branch)

Slices predecessor task 3.1 (`src/app/{layout,page}.tsx` +
`next.config.mjs`) into a **self-contained App Router
static-export bootstrap** whose `out/index.html` witness is
satisfiable ONLY because (a) the toolchain from PR 3a now
exists **and** (b) PR 3b imports nothing that its successors
produce. PR 3b does **not** import `@taxa/app-shell` (PR 4b
ships it) or `./globals.css` (PR 3c-i ships it); the layout/page
files render a minimal semantic placeholder body so `npx next
build` succeeds. This is the resolution of the dependency-
defect the corrective revision identifies: in the corrected
topology (toolchain at position 1, CSS children at positions
3–6), PR 3b's witness had a toolchain but its imports still
pointed at files that landed later in the chain (AppShell at
9/16, globals.css at 3/16). Rescoping 3b to a self-contained
bootstrap closes the defect without changing the chain
topology.

- [ ] 3b.1 R — `tests/test_app_shell_render.py` (new): invokes
      `npx next build` in a `tmp_path` clone (or via subprocess
      shim) and asserts the build emits `out/index.html` with
      `<html lang="en">`, `<head>` carries
      `<meta name="viewport" content="width=device-width,
      initial-scale=1">`, and a `<link rel="preload" …>` for
      the Raleway font that `next/font/google` produces. The
      test reads `out/index.html` after `next build` and
      asserts the markup contract. The test MUST fail on a
      fresh PR 3b branch (no `src/app/{layout,page}.tsx` yet).
      <!-- sdd-owner: implementation -->
- [ ] 3b.2 G — `src/app/layout.tsx` (new, ~40 LoC): host
      `<html>` / `<body>` shell, imports `next/font/google`
      for `Raleway`, `JetBrains Mono`, `Material Symbols
      Outlined`, renders a minimal semantic placeholder body
      (e.g. a `<main><h1>Taxa</h1></main>` shell).
**Does NOT mount `<AppShell>`** (lands in PR 4b) **and
      does NOT import `./globals.css`** (lands in PR 3c-i) —
      PR 3b is self-contained so `npx next build` succeeds
      at its position. <!-- sdd-owner: implementation -->
- [ ] 3b.3 G — `src/app/page.tsx` (new, ~30 LoC): a minimal
      semantic placeholder page (renders the placeholder
      body inside `layout.tsx`'s `<body>`). **Does NOT wrap
      `<AppShell>`** (lands in PR 4b) **and does NOT include
      a `"use client"` boundary** (lands in PR 4b when the
      AppShell needs it) — PR 3b is self-contained. The
      AppShell integration in PR 4b replaces this
      placeholder body with the full AppShell composition.
      <!-- sdd-owner: implementation -->
- [ ] 3b.4 G — `next.config.mjs` (new, ~30 LoC): declares
      `output: "export"`, `images: { unoptimized: true }`,
      `trailingSlash: false`, `reactStrictMode: true`; matches
      the G2 contract in `design.md` §"Static build / start
      lifecycle". <!-- sdd-owner: implementation -->
- [ ] 3b.5 T — `tests/test_app_shell_render.py` triangulation:
      assert the generated `out/.next/build-manifest.json`
      carries the expected entry for `src/app/layout.tsx` and
      `src/app/page.tsx`; assert the `<body>` element on first
      paint does **not** carry a `data-theme` attribute (no
      localStorage read before hydration); assert the generated
      `out/_next/static/media/*.woff2` carries the Raleway
      font file that `next/font/google` produced (the Raleway
      preload pipeline is live end-to-end). The path-alias
      contract from PR 3a is verified by
      `tests/test_toolchain_bootstrap.py::3a.7` and need not
      be re-verified here (PR 3b's imports resolve against
      the empty alias map; the barrel files land in their
      owning sub-PRs).
      <!-- sdd-owner: implementation -->
- [ ] 3b.6 Refactor — ensure the layout/page pair is the
      minimum semantic placeholder needed to satisfy the
      3b.1 / 3b.5 witness (Raleway preload only, no AppShell,
      no globals.css); ensure the Next.js + Turbopack build
      completes in under the recorded predecessor budget (no
      regression beyond the ≤ 0 % parity requirement in
      `design.md` §"Parity / evidence plan"). <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3b.1, 3b.5 | `.venv/bin/python3 -m pytest tests/test_app_shell_render.py -v` | `npx next build` exit 0; `out/index.html` non-empty; `out/.next/build-manifest.json` carries the expected entries | `git revert <3b-sha>` removes `src/app/{layout,page}.tsx`, `next.config.mjs`; the toolchain from PR 3a stays; nothing else touched |
| 3b.2, 3b.3 | same | same | same |
| 3b.4 | same | same | same |
| 3b.6 | same | `npx tsc --noEmit` exit 0 against `src/` | same |

## Phase 3c sub-sequence: Tailwind 4 cascade (positions 3–6, replaces original single PR 3c)

> **Why this is a four-child sub-sequence, not a single PR**
> (2026-09-02 replan). The original Phase 3c was authored as a
> single sub-PR at ~230 LoC, but the legacy inline `<style>`
> block in `web/index.html` (lines 14–1972) totals **1,963
> lines** of bespoke CSS that must be ported verbatim into
> Tailwind 4 (`@theme` for tokens, `@layer base` for the
> cascade, plus the design-system barrel). PR #144 (3a), PR #145
> (3b), and PR #146 (3b reconcile) already landed on the
> tracker, so the next PR opens from the 3c slot with no
> further reconciliation needed. The user authorized splitting
> the 3c slot into four reviewable children at positions 3–6,
> each ≤ 400 authored lines including tests. PR 3c-i **bases off
> the tracker** (the `docs/complete-taxa-frontend-migration-plan`
> branch **after** PR #146 reconciliation merges) so the 3c
> sub-sequence picks up the already-merged 3a + 3b + reconcile
> without an extra reconcile step; later children in the
> sub-sequence base off the immediate predecessor 3c branch.
> The design-system barrel + utilities + final CSS parity land
> together in PR 3c-iv so the chain stays 16 children and the
> Phase 5 ports (4a, 4b, 5a, 5b, 5c) see a fully populated
> `globals.css` + a populated design-system module by the time
> they run. The Tailwind 4 `--color-*` namespace aliases are
> asserted in each child so silent namespace drift cannot
> accumulate across the sub-sequence.

### Phase 3c-i: Tokens / base / dark mode (PR 3c-i → tracker after PR #146)

Depends on PR 3a (`tailwindcss@^4` installed). PR 3b is already
in the tracker (PR #145 merged) with reconciliation PR #146
merged, so PR 3c-i **bases off the tracker** to pick up the
3a + 3b + reconcile state. This is the **first child of the
3c sub-sequence**: it lands the design tokens, the body / html
resets, and the dark-mode cascade. Subsequent 3c children
(3c-ii, 3c-iii, 3c-iv) append to `src/app/globals.css` and
inherit the token + base layer this PR ships.

- [ ] 3c-i.1 R — `tests/test_tailwind_4_parity.py` (new,
      `:root` token slice): reads `web/index.html` lines 14–300
      and asserts every legacy `:root { --x }` token (`--primary`,
      `--accent`, `--surface`, `--elevated`, `--on-surface`,
      `--on-surface-variant`, `--outline`, `--outline-variant`,
      `--surface-container-low`, `--surface-container`,
      `--surface-container-high`, …) is declared with the same
      name and a non-empty value in `src/app/globals.css::@theme`.
      Asserts every `var(--x)` reference in the legacy
      `<style>` block resolves to a non-empty declaration in the
      generated `out/_next/static/chunks/*.css`. The test MUST
      fail on the merged tracker (no `src/app/globals.css` yet).
      <!-- sdd-owner: implementation -->
- [ ] 3c-i.2 G — `src/app/globals.css` (new, ~250 LoC):
      `@import "tailwindcss";` + `@theme { … }` block mirroring
      every legacy `:root` token (light palette); `@theme`
      `--color-*` namespace aliases so `bg-primary`,
      `text-on-surface`, `border-outline-variant`,
      `bg-surface-container-lowest`, `bg-primary-fixed`,
      `text-on-primary-fixed` resolve via Tailwind 4 utilities;
      `@layer base { … }` block containing the body / html /
      `main > :first-child` resets plus the dark-mode cascade
      (`[data-theme="dark"] { … }` with the legacy dark-palette
      token overrides); `--realm-*` family (bacteria, archaea,
      viruses, animalia, fungi, plantae, chromista) declared in
      `@theme` so the `.tree-row[data-realm="…"]` selectors
      in 3c-ii can reference them. Matches `design.md` §"Design
      tokens" cascade order requirement. <!-- sdd-owner: implementation -->
- [ ] 3c-i.3 T — extend `tests/test_tailwind_4_parity.py` to
      assert the Tailwind 4 `--color-*` namespace aliases
      resolve to the legacy `:root` token values (catch silent
      namespace drift); assert `--realm-*` family is declared
      with all seven realm colors matching the legacy values;
      assert the `body { overscroll-behavior: none; … }` rule
      and the `main > :first-child { margin-top: 0 !important; }`
      reset are present under `@layer base` in source order;
      assert the dark-mode cascade covers every legacy token
      that the legacy `<style>` block overrides under
      `[data-theme="dark"]`. <!-- sdd-owner: implementation -->
- [ ] 3c-i.4 G — `src/app/globals.css` (extended, ~80 LoC
      delta): add the global focus-visible selectors from the
      legacy `<style>` block (`.fex-row:focus-visible`,
      `.fex-chevron:focus-visible`, `.fex-splitter:focus-visible`,
      `.tier-header:focus-visible`, `.search-icon-btn:focus-visible`,
      `.materialize-btn:focus-visible`, `.load-all:focus-visible`,
      `.kebab-trigger:focus-visible`, `.kebab-item:focus-visible`,
      `#nav-help:focus-visible`, `#collapse-all:focus-visible`)
      under `@layer base` so every interactive element has the
      legacy outline contract. <!-- sdd-owner: implementation -->
- [ ] 3c-i.5 Refactor — alphabetize token declarations inside
      `@theme` so subsequent 3c children can locate tokens by
      prefix scan; ensure the dark-mode cascade block sits
      after the light `@theme` block and before any layer
      rules, matching the legacy cascade order.
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3c-i.1, 3c-i.3 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` carries the expected `:root` tokens + dark-mode cascade | `git revert <3c-i-sha>` removes the new `src/app/globals.css`; tracker state reverts to the 3a + 3b + reconcile baseline (no CSS payload, but toolchain + App Router still live); 3c-ii / 3c-iii / 3c-iv have not landed yet |
| 3c-i.2, 3c-i.4 | same | same | same |
| 3c-i.5 | same | same | same |

### Phase 3c-ii: Taxonomy tree / detail styling (PR 3c-ii → PR 3c-i branch)

Depends on PR 3c-i (tokens + base layer + dark-mode cascade live,
so every selector in this slice resolves `var(--token)`
references). Produces the second slice of `src/app/globals.css`
covering the legacy taxonomy surface: header chrome, tree rows,
detail panel, and the realm-tinted tree variants.

- [ ] 3c-ii.1 R — extend `tests/test_tailwind_4_parity.py`
      (taxonomy selector slice): reads `web/index.html` lines
      96–512 and asserts each legacy selector
      (`.tier-header`, `.tier-header h2`, `.load-all`,
      `.load-all:hover`, `.load-all:disabled`,
      `#search-results`, `#search-results.open`, `.search-hit`,
      `.search-hit:hover`, `.search-hit:last-child`,
      `.search-hit .tag`, `.tag-vernacular`, `.tag-scientific`,
      `.tag-authorship`, `.tree-source-toggle`,
      `.tree-source-toggle .tree-source-btn`,
      `.tree-source-toggle .tree-source-btn:hover:not(.active)`,
      `.tree-source-toggle .tree-source-btn.active`,
      `.rank-badge`, `.scientific-name`, `.scientific-name--roman`,
      `#detail-panel`, `#detail-panel.closing`,
      `.detail-card`, `.detail-header`, `.detail-header h2`,
      `.detail-section`, `.detail-section:last-child`,
      `.detail-section h3`, `.detail-section .count`,
      `.overview-section`, `.overview-rank`, `.overview-grid`,
      `.overview-row`, `.overview-label`, `.overview-value`,
      `.overview-chain`, `.overview-chain-segment`,
      `.overview-chain-segment:hover`, `.detail-item`,
      `.detail-item:hover`, `.detail-item .lang`,
      `.detail-item .country`, `.detail-item .authorship`,
      `.detail-item .means`, `.means-native`,
      `.means-introduced`, `.means-uncertain`, `.means-unknown`,
      `.search-pulse`, `.detail-tabs`, `.detail-tab`,
      `.detail-tab:hover`, `.detail-tab.active`,
      `.search-icon-btn`, `.search-icon-btn:hover`,
      `.materialize-btn`, `.materialize-btn:hover`, `.kebab`,
      `.kebab-trigger`, `.tree-row:hover .kebab-trigger`,
      `.tree-row.selected .kebab-trigger`,
      `.tree-row:focus-within .kebab-trigger`,
      `.kebab-trigger:focus-visible`,
      `.kebab-trigger:hover`,
      `.kebab-trigger:focus-visible`, `.kebab-menu`,
      `.kebab-menu.open`, `.kebab-item`,
      `.kebab-item:hover`, `.kebab-item:focus-visible`,
      `.kebab-item-label`,
      `.materialize-tab-content`, `.materialize-tab-loading`,
      `.materialize-tab-error`, `.materialize-modal-section-title`,
      `.materialize-modal-list`, `.materialize-modal-list-item`,
      `.materialize-modal-list-item:last-child`,
      `.materialize-modal-marker`, `.materialize-modal-marker-exists`,
      `.materialize-modal-marker-new`,
      `.materialize-modal-segment-path`,
      `.materialize-modal-counts`, `.materialize-modal-info-banner`,
      `.materialize-modal-actions`, `.materialize-modal-btn`,
      `.materialize-modal-btn:disabled`,
      `.materialize-modal-btn-primary`,
      `.materialize-modal-btn-primary:hover:not(:disabled)`,
      `.materialize-modal-btn-secondary`,
      `.materialize-modal-btn-secondary:hover:not(:disabled)`,
      `.materialize-modal-path-actions`,
      `.materialize-modal-path-actions .materialize-modal-btn`)
      is present in `src/app/globals.css` under `@layer base`
      (or `@layer components` if extracted in 3c-ii.5) with a
      non-empty declaration block. <!-- sdd-owner: implementation -->
- [ ] 3c-ii.2 G — `src/app/globals.css` (extended, ~200 LoC
      delta): append the legacy taxonomy selectors under
      `@layer base` in source order, preserving every
      `var(--token)` reference and every `color-mix(in srgb,
      var(--token) NN%, transparent)` call. The realm-tinted
      selectors (`.tree-row[data-realm="bacteria"] .scientific-name`,
      …, `.tree-row[data-realm="chromista"] .scientific-name`,
      `.tree-row.selected .scientific-name`,
      `.tree-row.focused .scientific-name`) are appended as
      well; they rely on the `--realm-*` family shipped by
      PR 3c-i.1. <!-- sdd-owner: implementation -->
- [ ] 3c-ii.3 T — extend `tests/test_tailwind_4_parity.py` to
      assert the tree-source toggle respects
      `aria-pressed="true"` (legacy behaviour: only the active
      source button keeps the active styling); assert the kebab
      menu only opens under `.kebab-menu.open` (no class-name
      drift); assert the materialize modal button disabled
      state matches the legacy `:disabled` rule; assert the
      realm tinting uses the `--realm-*` family values
      verbatim (catch any `--realm-*` mis-mapping).
      <!-- sdd-owner: implementation -->
- [ ] 3c-ii.4 G — `src/app/globals.css` (extended, ~50 LoC
      delta): append the kebab menu, materialize modal, and
      tab strip styles exactly as the legacy block ships
      them, preserving the cascade order the design.md §"Design
      tokens" specifies. <!-- sdd-owner: implementation -->
- [ ] 3c-ii.5 Refactor — extract the kebab menu into a
      `@layer components { .kebab { … } .kebab-menu { … } }`
      block so the React `<Kebab>` component in PR 5a can
      consume it via a stable layer name; keep the
      `var(--token)` references unchanged.
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3c-ii.1, 3c-ii.3 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` carries the expected taxonomy selectors | `git revert <3c-ii-sha>` reverts the appended taxonomy selectors in `src/app/globals.css`; 3c-i tokens + base + dark mode stay; 3c-iii / 3c-iv have not landed yet |
| 3c-ii.2, 3c-ii.4 | same | same | same |
| 3c-ii.5 | same | same | same |

### Phase 3c-iii: Search / Folder / global Browser styling (PR 3c-iii → PR 3c-ii branch)

Depends on PR 3c-ii (taxonomy selectors live). Produces the
third slice of `src/app/globals.css` covering the legacy
search engines grid, the materialize toast, the file explorer
chrome, the tree-search input + toggle row, the CSV scroller,
and the JSON tree viewer. This is the **largest single CSS
slice** of the legacy inline `<style>` block (the file
explorer + viewer take ~500 lines of the legacy CSS), so it
lives in its own child to stay ≤ 400 LoC authored.

- [ ] 3c-iii.1 R — extend `tests/test_tailwind_4_parity.py`
      (browser selector slice): reads `web/index.html` lines
      514–1800 and asserts each legacy selector (`.toast`,
      `.toast-error`, `.search-engines-grid`,
      `.search-category-header`,
      `.search-category-header:first-child`,
      `.search-category-header .material-symbols-outlined`,
      `.search-engine-btn`, `.search-engine-btn:hover`,
      `.search-engine-btn:focus-visible`,
      `.search-engine-btn:active`,
      `.search-engine-btn .material-symbols-outlined`,
      `.search-engine-btn:hover .material-symbols-outlined`,
      `.search-engine-btn-label`, `.fex-meta-strip`,
      `.fex-meta-strip > .fex-meta-spacer`, `.fex-tab-strip`,
      `.fex-tab-strip button`, `.fex-tab-strip button.active`,
      `.fex-snippet-frame`, `.fex-snippet-title`,
      `.fex-snippet-dots`, `.fex-snippet-dots span`,
      `.fex-snippet-dots .dot-r`, `.fex-snippet-dots .dot-y`,
      `.fex-snippet-dots .dot-g`, `.fex-snippet-body`,
      `.fex-snippet-actions`, `.fex-snippet-btn`,
      `.fex-snippet-btn:hover`, `.fex-snippet-btn:disabled`,
      `.fex-shell`, `.fex-tree-pane`, `.fex-viewer-pane`,
      `.fex-splitter`, `.fex-splitter::after`,
      `.fex-splitter:hover`, `.fex-splitter.dragging`,
      `.fex-tree-header`, `.fex-tree-header h2`, `.fex-row`,
      `.fex-row:hover`, `.fex-row .fex-chevron`,
      `.fex-row .fex-icon`, `.fex-row.file.selected`,
      `.fex-row.file.selected .fex-icon`,
      `.fex-row.file.selected .fex-meta`,
      `.fex-row.file.selected .fex-label`,
      `.fex-row.folder.selected`,
      `.fex-row.folder[data-realm] .fex-icon`,
      `.fex-row.folder[data-realm] .fex-label`,
      `.fex-row.folder[data-realm="bacteria"] .fex-icon`,
      …, `.fex-row.folder[data-realm="chromista"] .fex-icon`,
      `.fex-row .fex-label`, `.fex-row .fex-meta`,
      `.fex-children`, `.fex-banner`, `.fex-empty-state`,
      `.fex-empty-state .fex-empty-state-icon`,
      `.fex-tree-header-search`, `.fex-search-row`,
      `.fex-search-row .fex-search-icon`,
      `.fex-search-input`, `.fex-search-input:focus`,
      `.fex-search-clear`,
      `.fex-search-clear .material-symbols-outlined`,
      `.fex-search-clear:hover`,
      `.fex-search-input:not(:placeholder-shown) ~ .fex-search-clear`,
      `.fex-search-toggles`, `.fex-search-mode-btn`,
      `.fex-search-hide-empty-btn`,
      `.fex-search-mode-btn[aria-pressed="true"]`,
      `.fex-search-hide-empty-btn[aria-pressed="true"]`,
      `.fex-search-mode-btn .material-symbols-outlined`,
      `.fex-search-hide-empty-btn .material-symbols-outlined`,
      `.fex-row.search-match`, `.fex-search-empty`,
      `.fex-csv-scroller`, `.fex-csv-table`, `.fex-csv-table thead th`,
      `.fex-csv-table tbody td`, `.fex-csv-table tbody tr:nth-child(even) td`,
      `.fex-csv-table tbody tr:hover td`, `.fex-json-tree`,
      `.fex-json-children`, `.fex-json-node`,
      `.fex-json-summary`, `.fex-json-summary:hover`,
      `.fex-json-summary:focus-visible`, `.fex-json-caret`,
      `.fex-json-node.open > .fex-json-summary > .fex-json-caret`,
      `.fex-json-key`, `.fex-tree-leaf`, `.fex-tree-leaf.type-string`,
      `.fex-tree-leaf.type-number`, `.fex-tree-leaf.type-boolean`,
      `.fex-tree-leaf.type-null`, `.fex-tree-leaf.type-meta`,
      `.fex-tree-truncated`, `.fex-tree-truncated .material-symbols-outlined`)
      is present in `src/app/globals.css` with a non-empty
      declaration block. <!-- sdd-owner: implementation -->
- [ ] 3c-iii.2 G — `src/app/globals.css` (extended, ~250 LoC
      delta): append the legacy search engine grid, materialize
      toast, file explorer chrome, tree-search input + toggle
      row, CSV scroller, and JSON tree viewer styles under
      `@layer base` (or `@layer components` for the
      file-explorer-specific rules). Preserve every
      `color-mix(in srgb, var(--token) NN%, transparent)`
      call and every `var(--realm-*)` reference.
      <!-- sdd-owner: implementation -->
- [ ] 3c-iii.3 T — extend `tests/test_tailwind_4_parity.py` to
      assert the search-engine grid category headers stay
      `:first-child`-styled (legacy behaviour); assert the file
      explorer splitter hover/dragging states match the legacy
      rules; assert the JSON tree leaf type pills
      (`.fex-tree-leaf.type-{string,number,boolean,null,meta}`)
      reference the `--realm-*` family correctly; assert the
      search input `:not(:placeholder-shown) ~ .fex-search-clear`
      visibility rule is preserved. <!-- sdd-owner: implementation -->
- [ ] 3c-iii.4 G — `src/app/globals.css` (extended, ~80 LoC
      delta): append the truncation banner
      (`.fex-tree-truncated`), the big-file advisory
      (`.fex-image-advisory`, added in 3c-iv but the helper
      selectors go here), the empty state chrome
      (`.fex-search-empty`), and the snippet action toolbar
      (`.fex-snippet-actions`, `.fex-snippet-btn`,
      `.fex-snippet-btn:hover`, `.fex-snippet-btn:disabled`).
      <!-- sdd-owner: implementation -->
- [ ] 3c-iii.5 Refactor — extract the file explorer chrome
      into a `@layer components { .fex-* { … } }` block so the
      React `<FileExplorer>` component in PR 5b can consume it
      via a stable layer name; keep the realm-tinted
      `.fex-row.folder[data-realm="…"]` selectors in the same
      layer so the `--realm-*` references stay co-located with
      the matching `.tree-row[data-realm="…"]` selectors from
      PR 3c-ii. <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3c-iii.1, 3c-iii.3 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` carries the expected browser selectors | `git revert <3c-iii-sha>` reverts the appended browser selectors; 3c-i + 3c-ii stay; 3c-iv has not landed yet |
| 3c-iii.2, 3c-iii.4 | same | same | same |
| 3c-iii.5 | same | same | same |

### Phase 3c-iv: Animations / utilities + final CSS parity + design-system barrel (PR 3c-iv → PR 3c-iii branch)

Depends on PR 3c-iii (full legacy CSS cascade now ported except
`@keyframes` + image/video viewer + Settings view + design-system
barrel). Produces the final slice of `src/app/globals.css`,
ships the design-system barrel that the predecessor PR 2a
scaffolded but did not populate, and runs the parity test across
**all** 1,963 lines of legacy inline CSS to assert every rule
landed in `src/app/globals.css` (or a `@layer components` /
`@layer utilities` block PR 3c-i / 3c-ii / 3c-iii / 3c-iv
extracted into).

- [ ] 3c-iv.1 R — extend `tests/test_tailwind_4_parity.py`
      (`@keyframes` + viewer slice): reads `web/index.html`
      lines 273, 500, 834, 874, 1750–1972 and asserts every
      legacy `@keyframes` rule (`detail-card-enter`,
      `detail-card-leave`, `search-pulse-anim`,
      `materialize-spin`, `toast-slide-in`) is present in
      `src/app/globals.css`; asserts the
      `.animate-spin { animation: materialize-spin 1s linear
      infinite; }` rule is present; asserts the image + video
      viewer frames (`.fex-image-frame`, `.fex-image`,
      `.fex-video-frame`, `.fex-video-el`) and the Settings
      view (`.settings-shell`, `.settings-header`,
      `.settings-list`, `.settings-row`, `.settings-row-text`,
      `.settings-row-title`, `.settings-row-description`,
      `.settings-row-control`, `.settings-theme-toggle`,
      `.settings-theme-btn`, `.settings-theme-btn:hover`,
      `.settings-theme-btn .material-symbols-outlined`,
      `.settings-theme-btn-active`,
      `.settings-theme-btn-active:hover`,
      `.settings-action-btn`, `.settings-action-btn:hover`,
      `.settings-action-btn .material-symbols-outlined`,
      `.settings-link-btn`, `.settings-link-btn:hover`,
      `.settings-link-btn .material-symbols-outlined`) are
      present with non-empty declarations. <!-- sdd-owner: implementation -->
- [ ] 3c-iv.2 G — `src/app/globals.css` (extended, ~120 LoC
      delta): append the `@keyframes` rules, the
      `.animate-spin` utility, the image + video viewer frames,
      and the Settings view selectors under `@layer base` in
      cascade order. The Settings view reuses the
      `--surface-container-low`, `--outline-variant`,
      `--primary`, `--on-surface`, `--on-surface-variant`
      tokens from PR 3c-i. <!-- sdd-owner: implementation -->
- [ ] 3c-iv.3 G — `src/modules/design-system/infrastructure/index.ts`
      (new, ~20 LoC): barrel exports the `<Icon>` (Material
      Symbols Outlined glyph wrapper, frozen names: `search`,
      `folder_open`, `folder`, `chevron_right`, `expand_more`,
      `close`, `settings`, `help`, `science`, `science_off`,
      `download`) plus `<Button>` layout primitive. <!-- sdd-owner: implementation -->
- [ ] 3c-iv.4 G — `src/modules/design-system/presentation/{Icon.tsx,
      Button.tsx}` (new, ~40 LoC combined): the `<Icon>`
      component renders `<span class="material-symbols-outlined">`
      with the frozen glyph name; `<Button>` is a thin wrapper
      around `<button>` with the `.fex-snippet-btn` class for
      parity with the legacy file-explorer button visual.
      <!-- sdd-owner: implementation -->
- [ ] 3c-iv.5 T — extend `tests/test_tailwind_4_parity.py` to
      enumerate **every legacy utility class** the legacy build
      emits (`bg-primary`, `text-on-surface`,
      `border-outline-variant`, `bg-surface-container-lowest`,
      `bg-surface-container`, `bg-surface-container-high`,
      `shadow-sm`, `rounded-r-md`, `rounded-xl`,
      `bg-primary-fixed`, `text-on-primary-fixed`,
      `border-outline`, `bg-surface`, `text-outline`,
      `text-on-surface-variant`, `hover:text-on-surface`,
      `focus:border-primary`, `focus:ring-primary/20`,
      `transition-all`, `transition-colors`, `font-h1`,
      `text-h1`, `font-body-md`, `text-body-sm`, `fixed`,
      `top-0`, `w-full`, `z-50`, `bg-surface/95`,
      `backdrop-blur-md`, `shadow-[0_1px_8px_rgba(0,0,0,0.04)]`,
      `h-16`, `px-row-padding-x`, `flex`, `items-center`,
      `justify-between`, `gap-gutter`, `min-w-0`, `whitespace-nowrap`,
      `relative`, `w-64`, `lg:w-96`, `absolute`, `left-3`,
      `top-1/2`, `-translate-y-1/2`, `text-[18px]`, `w-full`,
      `py-2`, `pl-10`, `pr-4`, `rounded-xl`, `text-body-sm`,
      `focus:outline-none`, `focus:border-primary`,
      `focus:ring-2`, `focus:ring-primary/20`, `transition-all`,
      `shrink-0`, `aria-pressed`, `role="group"`, …) and
      assert each resolves to a non-empty CSS declaration in
      `out/_next/static/chunks/*.css`. The enumeration list
      comes from the legacy `web/index.html` `<body>` /
      `<header>` markup (lines 1975–2109) and from
      `web/dist/tailwind.css` (the legacy Tailwind 3.4 compiled
      output the predecessor uses). <!-- sdd-owner: implementation -->
- [ ] 3c-iv.6 Refactor — strip any hex literals from `src/`
      outside the design-system module; the grep guard goes
      into `tests/test_design_system_purity.py` (parametrized).
      Tokens that need a hex literal reference it via the
      design-system module's `infrastructure/tokens.ts`
      re-export; consumers import the token, not the literal.
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3c-iv.1, 3c-iv.5 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` carries every `@keyframes` rule + every utility class + every viewer + Settings selector | `git revert <3c-iv-sha>` reverts the appended `@keyframes` + viewer + Settings selectors; the design-system module is removed; 3c-i / 3c-ii / 3c-iii stay; Phase 5 ports (4a / 4b / 5a / 5b / 5c) have not landed yet so the design-system module is the sole consumer |
| 3c-iv.2, 3c-iv.3, 3c-iv.4 | same | same | same |
| 3c-iv.6 | `.venv/bin/python3 -m pytest tests/test_design_system_purity.py -v` | same | same |

## Phase 3d: Makefile rewrite + `WEB_DIR` repoint + AC-21 reader (PR 3d → PR 3c-iv branch, position 7/16)

Depends on PR 3b (`next build` produces `out/index.html`) and
PR 3c-iv (Tailwind 4 tokens + `@layer base` + `@layer components`
flow through `next build`; the final Tailwind 4 parity test is
on disk). Fuses the original Phase 3c's `Makefile::api` rewrite
+ the original Phase 3d's `WEB_DIR` repoint + AC-21 reader
update into a single sub-PR sized at ~240 authored LoC (well
under 400). The Node ≥ 20.9.0 runtime contract lands here as a
`Makefile` recipe step (the script itself was authored in
PR 3a).

- [ ] 3d.1 R — `tests/test_make_api_build.py` (new): invokes
      `make api` in a `tmp_path` clone (or via subprocess
      shim) and asserts the Makefile target invokes
      `node scripts/check-runtime.mjs` **first**, then
      `npm run build:web`, then uvicorn binds only after
      `out/index.html` exists; asserts uvicorn does not bind
      when `check-runtime.mjs` exits non-zero (Node < 20.9.0).
      <!-- sdd-owner: implementation -->
- [ ] 3d.2 R — `tests/test_make_api_build.py` (build/uvicorn
      order block): asserts the Makefile target invokes
      `npm run build:web` (`next build`) **before** uvicorn
      binds the port; asserts uvicorn does not bind when
      `next build` exits non-zero; asserts uvicorn fails fast
      if `out/index.html` is missing even after a successful
      `next build`. <!-- sdd-owner: implementation -->
- [ ] 3d.3 R — `tests/test_static_mount.py` (new): asserts
      `api/server.py:54` declares
      `WEB_DIR = Path(__file__).parent.parent / "out"`
      (repointed). Asserts the mount signature at
      `api/server.py:1815` stays byte-identical
      (`app.mount("/", StaticFiles(directory=str(WEB_DIR),
      html=True), name="web")`). Asserts the single-origin
      contract: `uvicorn.run(…)` binds to `127.0.0.1:8765`
      only; `extension/manifest.json::host_permissions` stays
      `["http://localhost:8765/*"]`;
      `content_scripts.matches` stays
      `["http://localhost:8765/*"]`. <!-- sdd-owner: implementation -->
- [ ] 3d.4 G — `Makefile` (modified, ~50 LoC delta in the
      `api:` and `css:` blocks): the `api:` target runs
      `node scripts/check-runtime.mjs` → `npm ci` →
      `npm run build:web` → `uvicorn … --port 8765` in that
      order; the legacy `make css` Tailwind-3.4 step is
      removed (the Tailwind 4 build lives inside
      `next build`); `make css` becomes a no-op shim that
      exits 0 (kept for backward compatibility with any
      external scripts; documented in `Makefile` header).
      <!-- sdd-owner: implementation -->
- [ ] 3d.5 G — `api/server.py` (modified, 1-line delta at
      line 54 + minimal middleware to wire `next/font` preload
      into `out/index.html` response if Next does not inline
      the `<link>` — only added if Phase 3b triangulation
      flags it): `WEB_DIR = Path(__file__).parent.parent /
      "out"`. No other line in `api/server.py` changes.
      <!-- sdd-owner: implementation -->
- [ ] 3d.6 G — `src/data/search-engines.js` (new, ~100 LoC):
      verbatim byte copy of `web/search_urls.js` with the
      export name changed to `SEARCH_ENGINES` (matches the
      canonical literal that `api/server.py::_SEARCH_ENGINES`
      mirrors). The byte shape — `key`, `label`,
      `with_authorship`, ordering — stays identical;
      `template` and `icon` stay intact per
      `tests/test_smoke.py` AC-21 contract. <!-- sdd-owner: implementation -->
- [ ] 3d.7 G — `tests/test_smoke.py` (modified, ~5 LoC delta):
      the `test_search_engine_contract` test's
      `open("web/search_urls.js").read()` is updated to
      `open("src/data/search-engines.js").read()`. The
      Python-side `open("api/server.py").read()` stays
      unchanged. AC-21 contract preserved. <!-- sdd-owner: implementation -->
- [ ] 3d.8 T — `tests/test_static_mount.py` triangulation:
      assert the file move is non-breaking for the contract
      test by running it in a fresh `tmp_path` clone; assert
      the literal's matching fields in
      `api/server.py::_SEARCH_ENGINES` are byte-identical to
      `src/data/search-engines.js` on every entry.
      <!-- sdd-owner: implementation -->
- [ ] 3d.9 T — `tests/test_make_api_build.py` triangulation:
      assert the failure mode where `out/index.html` is
      missing even after a successful `next build`
      (corrupted `out/`) causes `make api` to exit non-zero
      before uvicorn binds; assert uvicorn binds **only** to
      `127.0.0.1:8765` (no second listener on `0.0.0.0` or
      any other port). <!-- sdd-owner: implementation -->
- [ ] 3d.10 Refactor — alphabetical dep order in
      `package.json` (this PR closes any dep alphabetisation
      that PR 3a deferred); `Makefile` recipe tabs preserved
      (no spaces); `src/data/search-engines.js` line endings
      match `web/search_urls.js`. <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3d.1–3d.3 | `.venv/bin/python3 -m pytest tests/test_make_api_build.py -v tests/test_static_mount.py -v` | `make api` exit 0 on Node ≥ 20.9.0; `lsof -i :8765` shows uvicorn only | `git revert <3d-sha>` restores `Makefile::api` (legacy `make css` chain), restores `api/server.py:54` to legacy value, removes `src/data/search-engines.js`, reverts `tests/test_smoke.py` `open()` patch; Phases 3a/3b/3c-i/3c-ii/3c-iii/3c-iv untouched |
| 3d.4 | same | same | same |
| 3d.5 | same | same | same |
| 3d.6–3d.7 | `.venv/bin/python3 -m pytest tests/test_smoke.py::test_search_engine_contract -v` | `make api` boots uvicorn; `curl http://127.0.0.1:8765/index.html` returns 200 with the contents of `out/index.html` | same |
| 3d.8–3d.9 | same as 3d.1–3d.3 | same | same |
| 3d.10 | n/a (refactor) | same | same |

## Phase 4a: Typed store + 4 read + 4 write sites (PR 4a → PR 3d branch, position 8/16)

Slices predecessor tasks 4.1 + 4.2
(`src/modules/browser-state/{store,keys,defaults}.ts` + 4 read
+ 4 write sites inside `useEffect`). Depends on PR 3c-iv
(design-system barrel loaded); produces
`src/modules/browser-state/**` typed store with four read + four
write sites.

- [ ] 4a.1 R — `tests/test_browser_state_keys.py` (new): greps
      `src/modules/browser-state/**` and asserts exactly four
      `localStorage.getItem(…)` call sites + exactly four
      `localStorage.setItem(…)` + zero
      `localStorage.removeItem(…)` outside the typed `reset()`
      affordance. Asserts no other module
      (`src/modules/taxonomy/**`, `src/modules/research/**`,
      `src/modules/app-shell/**`,
      `src/modules/design-system/**`) reads or writes
      `localStorage` directly. <!-- sdd-owner: implementation -->
- [ ] 4a.2 G — `src/modules/browser-state/domain/keys.ts`
      (new, ~30 LoC): typed `LocalStorageKey` constants
      (`"taxa.settings.theme"`, `"taxa.tree.source"`,
      `"taxa.tree.lastTaxonId"`, `"taxa.tree.kebabOpenId"`)
      plus typed default values per the
      `browser-state-hydration` spec table (`theme: "light" |
      "dark"` default `light`, `tree-source: "col" | "worms" |
      "freshwater"` default `col`, `last-taxon-id: number |
      null` default `null`, `kebab-open-id: number | null`
      default `null`). <!-- sdd-owner: implementation -->
- [ ] 4a.3 G —
      `src/modules/browser-state/infrastructure/store.ts`
      (new, ~80 LoC): four `read(key)` functions and four
      `write(key, value)` functions, one per key, each
      wrapping `try/catch` to swallow `localStorage`
      exceptions (private mode / quota exceeded). Exports a
      typed `subscribe(key, cb)` that returns an unsubscribe
      handle; exports a typed `reset()` that calls
      `localStorage.removeItem` for every key. Plain TS in
      `domain/`; `localStorage` calls live in
      `infrastructure/` per modular-architecture rule 4.
      <!-- sdd-owner: implementation -->
- [ ] 4a.4 G — `src/modules/browser-state/index.ts` (new
      barrel, ~10 LoC): re-exports the four `read`, four
      `write`, `subscribe`, `reset`, the typed defaults, and
      the typed listener type. **No** raw `localStorage`
      getter/setter is exported. <!-- sdd-owner: implementation -->
- [ ] 4a.5 T — `tests/test_browser_state_keys.py`
      triangulation: parametrize the 4-key matrix; assert
      that no `localStorage.getItem` / `setItem` exists in
      `src/modules/research/infrastructure/` (the
      `taxa.fex.treeWidth` splitter key stays owned by the
      file explorer module per the spec §Notes).
      <!-- sdd-owner: implementation -->
- [ ] 4a.6 Refactor — extract the read/write exceptions into
      a `safeStorage` helper that wraps `getItem` / `setItem`
      / `removeItem` with the try/catch; reuse it across the
      four read and four write sites. <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 4a.1, 4a.5 | `.venv/bin/python3 -m pytest tests/test_browser_state_keys.py -v` | `npx next build` exits 0; `out/_next/static/chunks/*.js` carries the typed store bundle | `git revert <4a-sha>` removes `src/modules/browser-state/**`; nothing else touched |
| 4a.2–4a.4, 4a.6 | `.venv/bin/python3 -m pytest tests/test_browser_state_keys.py -v` | `npx tsc --noEmit` against `src/modules/browser-state/` | same |

## Phase 4b: Hydration guard + AppShell integration + Playwright zero-warnings test (PR 4b → PR 4a branch, position 9/16)

Slices predecessor tasks 4.3 + 4.4 (`useSyncExternalStore`
behind `mounted` flag + Playwright zero-hydration-warnings
assertion) plus the **AppShell integration into
`src/app/{layout,page}.tsx`** (the dependency-defect fix that
moves the AppShell wiring from PR 3b to PR 4b — PR 4b owns
both the `src/modules/app-shell/**` module **and** the
integration seam into the App Router host). Depends on PR 4a
(store available), PR 3b (the `src/app/{layout,page}.tsx`
placeholders that PR 4b integrates `<AppShell>` into), and
PR 3c-iv (animations / utilities + final CSS parity + design-
system barrel loaded for `next build`; PR 3c-i ships the
`@theme` tokens it references).

- [ ] 4b.1 R — `tests/test_hydration_console.py` (new,
      Playwright): loads the chromium fixture against `make
      api`, asserts the browser console emits zero
      `Warning: Text content did not match`, zero
      `Warning: Expected server HTML to contain`, and zero
      `Warning: Hydration failed` messages after the first
      paint + rehydration cycle. <!-- sdd-owner: implementation -->
- [ ] 4b.2 G —
      `src/modules/app-shell/presentation/AppShell.tsx`
      (new, ~50 LoC): imports `useSyncExternalStore` from
      the `browser-state` module; reads the typed store
      behind a `mounted` flag set inside `useEffect`; on
      first paint, returns the empty state
      (`selected: null`, `tree: null`,
      `last-taxon-id: null`); on rehydration, applies the
      typed defaults from `localStorage` and updates the
      URL to the `last-taxon-id` if one is stored.
      <!-- sdd-owner: implementation -->
- [ ] 4b.3 G —
      `src/modules/app-shell/infrastructure/page-chrome.tsx`
      (new, ~30 LoC): header tabs (Browser / Classification
      / Settings) with `data-action="nav-tab"` and
      `data-path="<tab>"` attributes; theme toggle stamps /
      unstamps `tab `data-theme` on `<html>` via the typed
      store; help shell, settings view, banner host.
      <!-- sdd-owner: implementation -->
- [ ] 4b.4 T — `tests/test_hydration_console.py`
      triangulation: assert the chromium fixture's console
      after a forced reload (where `localStorage` has a
      stored `theme: "dark"`) shows `data-theme="dark"` on
      `<html>` after the rehydration cycle; assert no
      warning fires when the user toggles the theme between
      paints. <!-- sdd-owner: implementation -->
- [ ] 4b.5 Refactor — extract the `mounted` flag into a
          small `useMounted()` hook in
          `src/modules/browser-state/` so the pattern is
          reusable; reuse it in `AppShell.tsx` and any
          descendant component that reads typed state.
          <!-- sdd-owner: implementation -->
      - [ ] 4b.6 G — `src/app/{layout,page}.tsx` (modified, ~10
          LoC combined delta): integrate `<AppShell>` from
          `@taxa/app-shell` into the App Router host.
          `src/app/layout.tsx` adds
          `import { AppShell } from "@taxa/app-shell";` and wraps
          the placeholder body in `<AppShell>{children}</AppShell>`;
          `src/app/page.tsx` adds the `"use client"` boundary
          the AppShell needs (the AppShell module imports
          `useSyncExternalStore` and `useEffect`). PR 4b owns
          the integration because it owns
          `src/modules/app-shell/**`; the dependency defect (PR
          3b importing a module PR 4b ships) is closed here. The
          existing 4b.1 R hydration-zero-warnings Playwright
          witness is the regression guard for the integration
          (the chromium fixture loads the integrated AppShell
          and asserts zero hydration warnings after first paint
          + rehydration cycle).
          <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 4b.1, 4b.4 | `.venv/bin/python3 -m pytest tests/test_hydration_console.py -v` | `make api` boots uvicorn; Playwright runs the chromium fixture end-to-end | `git revert <4b-sha>` removes `src/modules/app-shell/presentation/AppShell.tsx` and `infrastructure/page-chrome.tsx`; Phase 4a store stays |
| 4b.2–4b.3 | same | `npx next build` exits 0; `npx tsc --noEmit` against `src/modules/app-shell/` | same |
| 4b.5 | same | same | same |
| 4b.6 | `.venv/bin/python3 -m pytest tests/test_hydration_console.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.js` references the `@taxa/app-shell` barrel; Playwright zero-hydration-warnings against the integrated AppShell | `git revert <4b-sha>` reverts the AppShell integration delta in `src/app/{layout,page}.tsx` AND removes `src/modules/app-shell/**`; Phase 4a store stays |

## Phase 5a: Taxonomy module port (PR 5a → PR 4b branch, position 10/16)

Slices predecessor tasks 5.1 + 5.2 + 5.3
(`src/modules/taxonomy/{domain,application,infrastructure,
presentation}` + port `web/{tree,detail,breadcrumb}.js`).
Depends on PR 4b (hydration-safe state read for
`tree-source`) and PR 3c-ii (the taxonomy selectors are in
place — the taxonomy CSS rides on PR 3c-ii's selectors).

This sub-PR also lands the **DetailPanel tab strip**
(`Overview` / `Search` / `Folder`), the **`Overview` tab
body**, and the **`Kebab` menu including the `Search online`
action that forces the `Search` tab** (closing the current
live regression where top-level taxa land on `Overview` when
`Search online` is invoked). The header `Browser` tab
re-anchoring (global Research / file explorer) and the
`SearchTab` / `FolderTab` bodies land in PR 5b to keep the
taxonomy port focused on the tree-and-detail surface; PR 5a
only owns the **tab strip scaffolding** plus the
**force-Search contract** that PR 5b's `SearchTab` plugs
into.

- [ ] 5a.1 R — `tests/test_taxonomy_infra.py` (new): mocks
      `fetchTaxon`, `fetchChildren`, `fetchDomains`; asserts
      the application layer exposes view-models only (no raw
      JSON in the presentation layer); asserts the shape of
      `Taxon`, `TaxonTree`, `Breadcrumb` types matches the
      `taxonomy` domain layer; asserts the `DetailPanel` tab
      strip exposes three tabs in fixed order
      (`Overview`, `Search`, `Folder`); asserts `Overview`
      is always available / always visible per the
      user-selected policy; asserts the `Search online` kebab
      action forces the `Search` tab active (NOT
      `Overview`, even for top-level taxa — closes the
      current live regression). <!-- sdd-owner: implementation -->
- [ ] 5a.2 G — `src/modules/taxonomy/domain/taxon.ts`
      (~60 LoC): plain TS types for `Taxon`, `TaxonTree`,
      `Breadcrumb`, `DomainId`; invariants (parent-chain
      walker, rank ordering, materialised-set inclusion).
      Predecessor PR 2d already shipped the type surface;
      PR 5a extends with the parent-chain walker the design
      specifies. <!-- sdd-owner: implementation -->
- [ ] 5a.3 G —
      `src/modules/taxonomy/infrastructure/api.ts`
      (~50 LoC): `fetchTaxon(id)` → `GET /api/taxon/{id}`;
      `fetchChildren(id, source)` →
      `GET /api/taxon/{id}/children?source=<col|worms|
      freshwater>`; `fetchDomains()` → `GET /api/domains`.
      All return typed promises; network errors surface as
      typed `NetworkError`. <!-- sdd-owner: implementation -->
- [ ] 5a.4 G —
      `src/modules/taxonomy/application/useTaxonTree.ts`
      (~80 LoC): the `useTaxonTree()` hook; consumes the
      typed `fetch*` functions from `infrastructure`; emits
      view-models the presentation layer consumes; no React
      imports in `domain` or `infrastructure` layers.
      <!-- sdd-owner: implementation -->
- [ ] 5a.5 G —
      `src/modules/taxonomy/presentation/{Tree,DetailPanel,
      OverviewTab, Breadcrumb}.tsx` (~220 LoC combined):
      ports the legacy
      `web/{tree,detail,breadcrumb}.js` row layout (per-row
      kebab, per-row search icon, per-row materialize
      indicator, breadcrumb monospace family for
      scientific-name segments) **and ships the
      `DetailPanel` tab strip**. The tab strip renders
      **three tabs in fixed order: `Overview`, `Search`,
      `Folder`**, all three reachable from every selection;
      `Overview` is **always available and always visible**
      per the user-selected policy. The `OverviewTab`
      component renders scientific name, accepted status,
      authorship, species count. The `DetailPanel` exports a
      typed tab-activation callback that the `Kebab`'s
      `Search online` action invokes to force the `Search`
      tab active. Every legacy
      `data-action="nav-tab"`, `data-path="<tab>"`,
`data-theme` attribute is preserved. The taxonomy
      presentation layer rides on PR 3c-ii's
      taxonomy selectors (`.taxa-tree`,
      `.tree-row`, `.kebab`, `.detail-panel`, `.tab-strip`,
      `.overview-tab`, `.breadcrumb`, …).
      <!-- sdd-owner: implementation -->
- [ ] 5a.6 G — `src/modules/taxonomy/presentation/Kebab.tsx`
      (~40 LoC): per-row kebab menu. Includes the `Search
      online` action wired to dispatch the tab-activation
      callback that **forces the `Search` tab active** on the
      selected taxon (it MUST NOT default to `Overview`, even
      for top-level taxa). The action is the closure of the
      current live regression where `Search online` on
      top-level taxa lands on `Overview`.
      <!-- sdd-owner: implementation -->
- [ ] 5a.7 T — `tests/test_taxonomy_infra.py` triangulation:
      parametrize over the three sources (`col`, `worms`,
      `freshwater`); assert the tree-source toggle re-renders
      the tree with the matching source; assert the
      breadcrumb walker handles root taxa (no parent) and
      orphaned taxa (parent missing in the source) without
      throwing; assert the `DetailPanel` tab strip renders
      all three tabs (`Overview`, `Search`, `Folder`) for
      every selection including top-level taxa; assert
      `Overview` is always visible; assert the `Search
      online` kebab action forces the `Search` tab active
      (closes the current regression).
      <!-- sdd-owner: implementation -->
- [ ] 5a.8 T — extend `tests/test_taxonomy_infra.py` with a
      tab-strip Playwright witness: load the chromium
      fixture, select a top-level taxon (e.g. `Archaea`),
      click the per-row `Search online` kebab action, assert
      the detail-panel tab strip now shows `Search` as the
      active tab (NOT `Overview`). The witness is the
      regression guard against the current live behavior.
      <!-- sdd-owner: implementation -->
- [ ] 5a.9 Refactor — extract the per-row kebab menu into
      `<Kebab>`; reuse it across `Tree` and `DetailPanel`;
      collapse the `DetailPanel` tab-strip rendering into a
      single `<TabStrip tabs={["Overview", "Search",
      "Folder"]} active={...} onChange={...} />` primitive
      exported from `src/modules/design-system/`.
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 5a.1, 5a.7, 5a.8 | `.venv/bin/python3 -m pytest tests/test_taxonomy_infra.py -v` | `make api` boots uvicorn; `curl /api/domains` returns the JSON shape; Playwright tab-strip witness exits 0 | `git revert <5a-sha>` removes `src/modules/taxonomy/**` (except `domain/taxon.ts` shipped by predecessor PR 2d — that stays); nothing else touched |
| 5a.2–5a.6, 5a.9 | same | `npx next build` exits 0; `npx tsc --noEmit` against `src/modules/taxonomy/` | same |

## Phase 5b: Research module port + CDN pin (PR 5b → PR 5a branch, position 11/16)

Slices predecessor tasks 5.4 + 5.5 + 5.6
(`src/modules/research/{domain,application,infrastructure,
presentation}` + port `web/{file_explorer,file_viewer,format,
keymap}.js` + CDN pin). Depends on PR 5a (taxonomy state read
flows shared with research and the `DetailPanel` tab strip
scaffold the `Search online` action plugs into), PR 3d
(`src/data/search-engines.js` for the `Engine` named export),
and PR 3c-iii (the Search / Folder / global Browser selectors
are in place — the research selectors ride on PR 3c-iii's CSS).
This is the largest sub-PR at ~395 LoC; it stays under the
400-line budget per the design §"Sub-PR slice under Approach A"
with tight headroom — maintainability is tracked and the
boundary stays within the 400-line per-PR review budget.

This sub-PR also lands the **`SearchTab`** body (categorized
outbound-link list in fixed order `General` / `Taxonomic` /
`Academic` / `Multimedia` / `Documents`), the **`FolderTab`**
body (per-taxon materialize indicator; **separate** from
`SearchTab`), the **`SearchLinkList`** presenter that maps
each `Engine` to an anchor with `target="_blank"` and
`rel="noopener noreferrer"`, and the **header `Browser` tab
re-anchored as global Research / file explorer** (NOT
taxon-scoped; selecting a taxon while `Browser` is active
MUST NOT scope the explorer to that taxon).

- [ ] 5b.1 R — `tests/test_research_infra.py` (new): mocks
      `fetchFiles`, `fetchServe` against
      `/api/taxon/{id}/files{,/serve}`; asserts the format
      dispatcher (PDF / HTML / TXT / MD / DOCX / XLS / XLSX /
      EPUB) routes to the right lazy loader; asserts CDN
      URLs are pinned to `mammoth@1.8.0`, `xlsx@0.18.5`,
      `epubjs@0.3.93`; asserts the `SearchTab` renders the
      five category sections in fixed order (`General`,
      `Taxonomic`, `Academic`, `Multimedia`, `Documents`);
      asserts the `FolderTab` is a separate body from
      `SearchTab`; asserts the header `Browser` tab opens
      the global Research file explorer without a
      `taxonId` filter.
      <!-- sdd-owner: implementation -->
- [ ] 5b.2 G —
      `src/modules/research/domain/{research-file,engine,
      file-node}.ts` (~90 LoC combined): typed `ResearchFile`,
      `Engine`, `FileNode`; the `Engine` type mirrors the
      `SEARCH_ENGINES` literal shape (key, label,
      with_authorship, ordering); the `ResearchFile`
      discriminated union covers the nine supported formats
      plus `Unsupported` and `LegacyDoc` fallbacks.
      <!-- sdd-owner: implementation -->
- [ ] 5b.3 G —
      `src/modules/research/infrastructure/api.ts`
      (~80 LoC): `fetchFiles(id)` → `GET /api/taxon/{id}/files`;
      `fetchServe(id, rel)` →
      `GET /api/taxon/{id}/files/serve?path=<rel>`;
      `loadScriptOnce(name, src)` lazy-loader for CDN
      libraries (pinned URLs; idempotent).
      <!-- sdd-owner: implementation -->
- [ ] 5b.4 G —
      `src/modules/research/infrastructure/search-engines.js`
      (re-export from `src/data/search-engines.js` shipped by
      Phase 3d for the research module's barrel, with the
      `SEARCH_ENGINES` named export unchanged).
      <!-- sdd-owner: implementation -->
- [ ] 5b.5 G —
      `src/modules/research/application/{useFileExplorer,
      useFileViewer}.ts` (~120 LoC combined): the two hooks;
      consume the typed `fetch*` functions; emit view-models
      the presentation layer consumes. <!-- sdd-owner: implementation -->
- [ ] 5b.6 G —
      `src/modules/research/presentation/{FileExplorer,
      FileViewer, RawTableTreeTabs, MetaStrip,
      BreadcrumbPanel, Banners, SearchLinkList,
      SearchTab, FolderTab}.tsx` (~290 LoC combined):
      ports the legacy
      `web/{file_explorer,file_viewer,format,keymap}.js`
      two-pane layout; the Raw / Table / Tree tab strip; the
      meta strip `FORMAT | SIZE | ENCODING`; the nine-format
      dispatcher with CDN-pin lazy loading; the legacy DOC
      and unsupported fallbacks; the CDN failure banner
      `"Viewer offline — raw download unavailable"`; the
      tree search (200 ms debounce, filter / highlight
      modes,
      `state.explorer.search.{query, mode, hideEmpty}`
      persisted); the explorer state reset on taxon switch.
      The `SearchTab` renders the five category sections
      (`General` / `Taxonomic` / `Academic` / `Multimedia` /
      `Documents`) in fixed order; the `SearchLinkList`
      presenter maps each `Engine` to an anchor with
      `target="_blank"` and `rel="noopener noreferrer"`,
      resolving the URL template from `SEARCH_ENGINES`. The
`FolderTab` is a separate body (per-taxon materialize
      indicator); it MUST NOT be a subset of `SearchTab`.
      The research presentation layer rides on PR 3c-iii's
      Search / Folder / global Browser selectors
      (`.search-tab`,
      `.search-category-section`, `.search-link-list`,
      `.search-link`, `.folder-tab`,
      `.header-browser-tab`, `.research-explorer`,
      `.file-explorer-pane`, `.file-viewer-pane`, …).
      <!-- sdd-owner: implementation -->
- [ ] 5b.7 G —
      `src/modules/app-shell/infrastructure/page-chrome.tsx`
      (~30 LoC delta): the header `Browser` tab is
      re-anchored as the **global Research / file explorer**
      — it opens the explorer without a `taxonId` filter,
      and selecting a taxon while `Browser` is active MUST
      NOT scope the explorer to that taxon (the explorer
      continues to show the active research corpus). The
      `data-path="browser"` and `data-action="nav-tab"`
      attribute contract is preserved.
      <!-- sdd-owner: implementation -->
- [ ] 5b.8 T — `tests/test_research_infra.py` triangulation:
      parametrize over the nine formats (PDF, HTML, TXT, MD,
      DOCX, XLS, XLSX, EPUB, plus DOC fallback, plus an
      unsupported extension like `.zip`); assert each
      format dispatches to the matching legacy renderer;
      assert `Content-Type` matches the file extension;
      assert the meta strip renders the matching
      `FORMAT=<EXT> | SIZE=<bytes> | ENCODING=UTF-8`;
      assert the `SearchTab` category sections render in
      the fixed order (`General` / `Taxonomic` / `Academic` /
      `Multimedia` / `Documents`); assert every
      `SearchLinkList` anchor carries `target="_blank"` and
      `rel="noopener noreferrer"`; assert the `FolderTab` is
      rendered separately from `SearchTab`; assert the
      header `Browser` tab opens the global Research
      explorer without a taxon scope.
      <!-- sdd-owner: implementation -->
- [ ] 5b.9 Refactor — extract the meta strip into a single
      `<MetaStrip format={…} size={…} encoding="UTF-8" />`
      component; extract the CDN failure banner into
      `<BannerHost>` so it can be reused in `app-shell`;
      collapse the `SearchTab` category rendering into a
      `<SearchLinkList>` presenter that takes the
      `SEARCH_ENGINES` literal and renders the five
      category sections.
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 5b.1, 5b.8 | `.venv/bin/python3 -m pytest tests/test_research_infra.py -v` | `make api` boots uvicorn; `curl /api/taxon/<id>/files` returns the JSON shape; CDN URLs return 200 | `git revert <5b-sha>` removes `src/modules/research/**` and the `Browser` tab delta in `src/modules/app-shell/infrastructure/page-chrome.tsx`; `src/data/search-engines.js` (Phase 3d) stays |
| 5b.2–5b.7, 5b.9 | same | `npx next build` exits 0; `npx tsc --noEmit` against `src/modules/research/` | same |

## Phase 5c: E2E selectors + `data-*` contract + delete legacy (PR 5c → PR 5b branch, position 12/16)

Slices predecessor tasks 5.7 + 5.8 + 5.9 (Playwright + e2e
selector updates + `data-*` contract preservation + delete
`web/*.{html,js,css}` + `tailwind.config.js`). Depends on PR 5b
(all UI components live) and PR 3c-iv (the final Tailwind 4
parity test is on disk; the 1,963-line legacy inline CSS has
been migrated into `src/app/globals.css` end-to-end and is
ready to be retired).

**PR 5c re-split (this entry, supersedes the inline 5c.1–5c.7 enumeration
for the next code worktree)**. The seven-TDD sub-PRs below collapse
into a single **`5c.1b` (deferred)** UI slice so the typed foundation
can land first. Evidence record lives in `apply-progress.md` §Change
log entry "2026-09-07 — PR 5c.1a: typed browser-state foundation
landed"; binding addendum lives in `design.md`; **G4 remains blocked**.

- [x] **5c.1a (landed)** — typed foundation:
      `versionBannerDismissed: "taxa.settings.versionBannerDismissed"`
      (boolean, default `false`); `TreeSource` extends to
      `col | worms | freshwater`; **5 + 5** storage-call contract
      restored (1 inline `getItem(` + 1 inline `setItem(` for the new
      key, all in `infrastructure/store.ts`); 27/27 tests pass under
      strict TDD.
- [x] **5c.1b-A (landed)** — tree-source UI + nav/breadcrumb ids + single-store
      context wire (page.tsx subscribes via `useBrowserStateStore`);
      no `domain/keys.ts` / `infrastructure/store.ts` change.
- [x] **5c.1b-B (landed)** — VersionBanner render + panel close/sticky
      work; tree-source hydration polish; no `domain/keys.ts` /
      `infrastructure/store.ts` change.
- [x] **5c.2-A (landed)** — search-engine contract alignment:
      `api/server.py::_SEARCH_ENGINES` and
      `src/data/search-engines.js::SEARCH_ENGINES` now hold exactly
      the canonical 14 engines (google, imagen, documentos, pdf,
      wikipedia, bhl, researchgate, plos, academia, scielo,
      scholar, youtube, zootaxa, scribd) in the same ordered
      fields; the three retired `general` social/share entries
      (`threads_acipenser`, `facebook_acipenser_baerii`,
      `threads_shared_post`) are removed from both mirrors.
      `tests/test_smoke.py::test_search_engine_contract` now pins
      the exact count (14) and the ordered key list in addition
      to the existing key/label/with_authorship parity check.
- [x] **5c.2-B.1b-i (landed)** — React export capture CLI + Chromium navigation runner: `tools/react-e2e-harness/scripts/run.mjs` requires `--origin` + `--output-root`, rejects `file://` / non-http(s) / origin paths / missing flags / output collisions, dynamic-imports the injected `runFn` (default `./chromium-driver.mjs` which dynamic-imports `playwright` from the local `node_modules/`), writes an atomic timestamped `evidence.json` ONLY on successful capture (fail-closed); `chromium-driver.mjs` launches headless Chromium against the explicit origin, asserts the locked React data contracts (`data-harness-root`, `data-harness-surface`, non-null `data-harness-taxon-id`, `[data-explorer="ready"]`, both `[data-pane]` slots, `input[data-search-input]`, at least one `[data-file-path]`), captures concise `pageerror`/`console.error`/navigation/assertions trace, closes the browser reliably via `finally`; `package.json` adds `scripts.capture = "node scripts/run.mjs"`; `tools/react-e2e-harness/README.md` documents the caller-provided origin flow + deferral list. No fixture API server, no export HTTP server, no Makefile target, no hermetic driver tests, no production source/API change, no legacy E2E selector modernization, no `web/*.{html,js,css}` + `tailwind.config.js` deletion, no G4 aggregation. **No test surface** in this sub-slice; pre-implementation source-contract check ran RED (CLI + scripts dir absent), post-implementation `node --check` + CLI missing-origin / `file://` / origin-path rejection ran GREEN. **G4 / G3 Tier-2 / cutover remain blocked; G4 is NOT flipped by the capture CLI landing.**
- [x] **5c.2-B.1b-ii-a (landed)** — hermetic in-process Node fixture API for the isolated React `FileExplorer` harness: `tools/react-e2e-harness/scripts/fixture-server.mjs` is pure Node built-ins (`node:http` + `node:buffer`); zero npm deps; caller-chosen port (CLI `--port N`) or OS-assigned (`--port 0`); never hard-coded 8765; only synthetic taxon id `1` served; mirrors the production `/api/taxon/1/files` + `/files/serve?path=…` FastAPI shape (`FilesEnvelope` from `src/modules/research/domain/research-file.ts`); deterministic in-memory fixture corpus (HTML, Markdown, text, PDF; recursive `Papers/lynx.pdf`); Content-Type mirrors `api/server.py::_CONTENT_TYPE_BY_EXT`; `Content-Disposition: inline; filename="<basename>"`; rejects unknown routes / unknown taxon / `..` / `.` / absolute / URL-encoded traversal / wrong method fail-closed; importable by the next composition slice via `startServer({port, host}) → {baseUrl, port, close}`; `tests/test_5c_2_b_react_harness.py` (21 hermetic tests; `subprocess` Node + Python `urllib`) proves source contract (file exists, `node --check`, zero-dep), start/stop lifecycle, envelope shape, four-format content types + `%PDF-` magic, traversal fail-closed, unknown taxon / route / method rejection. **RED** = pre-implementation source-contract check (`fixture-server.mjs` absent) FAILED on pre-`5c.2-B.1b-ii-a` source. **GREEN** = `node --check` exits `0` + all 21 hermetic tests pass. No export HTTP server, no `make capture-react-e2e`, no Makefile target, no G4 aggregation, no G4 flip; static export server + composition slice + hermetic capture-driver tests + e2e selector modernization + `web/*.{html,js,css}` + `tailwind.config.js` legacy deletion still deferred. **G4 / G3 Tier-2 / cutover remain blocked; G4 is NOT flipped by the fixture API landing.**
- [x] **5c.2-B.1b-ii-b (landed)** — hermetic in-process Node **static export HTTP server** for the isolated React harness: `tools/react-e2e-harness/scripts/export-server.mjs` is pure Node built-ins (`node:http` + `node:fs/promises` + `node:path` + `node:url`); zero npm deps; caller-supplied absolute `--root` (mandatory, absolute, existing directory; fail-closed before binding any listener); caller-chosen port (CLI `--port N`) or OS-assigned (`--port 0`); loopback default `127.0.0.1`; never hard-coded 8765; `/` maps to `index.html`; exact files below root served with appropriate Content-Type (HTML/JS/MJS/CSS/JSON/images/fonts fall back to `application/octet-stream`); HEAD mirrors GET headers with no body; `..` / `.` / absolute / URL-encoded traversal / directory leakage / unknown paths / non-GET methods all fail-closed (404 / 405); importable by the next composition slice via `startServer({port, host, root}) → {schema, root, host, port, baseUrl, server, close}`. `tests/test_5c_2_b_react_harness.py` gains an export-server block (added inside the same file as the existing fixture block; `EXPORT_SERVER` path constant + `_spawn_export` + `_wait_export_ready` + `exptree` / `exp` fixtures + 18 new hermetic tests; total file now 39 hermetic tests; same `subprocess` Node + Python `urllib` approach) proves source contract (file exists, exports `startServer`, `node --check`, zero-dep), CLI gating (missing/relative/non-existent `--root` all exit non-zero), start/stop lifecycle, `/` → `index.html`, seven Content-Type families + `application/octet-stream` fallback, nested file under root, HEAD mirrors GET, traversal fail-closed parametrized over `..` / `../../etc/passwd` / `%2Fetc%2Fpasswd` / `%2E%2E%2Fpasswd`, directory-not-served, unknown-route 404, non-GET 405 with `Allow: GET, HEAD`. **RED** = pre-implementation source-contract check (`export-server.mjs` absent) FAILED on pre-`5c.2-B.1b-ii-b` source. **GREEN** = `node --check` exits `0` + all 39 hermetic tests pass. No composition slice wiring yet, no `make capture-react-e2e` target, no hermetic capture-driver tests, no e2e selector modernization, no `web/*.{html,js,css}` + `tailwind.config.js` legacy deletion. **G4 / G3 Tier-2 / cutover remain blocked; G4 is NOT flipped by the static export server landing.**
- [x] **5c.2-B.1b-ii-c (landed)** — composition orchestrator + CLI driver + Makefile target + `capture:composed` package-script + hermetic test slice: `tools/react-e2e-harness/scripts/composed-capture.mjs` is pure Node built-ins; wires `fixture-server.mjs` (5c.2-B.1b-ii-a) → `npm run build` (via injected `buildFn`, `NEXT_PUBLIC_HARNESS_BASE_URL` pinned to the fixture origin) → `out/index.html` access probe → `export-server.mjs` (5c.2-B.1b-ii-b) → `run.mjs::capture` (5c.2-B.1b-i, via injected `captureFn`) into one `composeCapture({harnessDir, outputRoot, taxonId, host, buildFn, captureFn, startFixtureFn, startExportFn, now})` orchestrator. CLI requires `--output-root`; rejects non-loopback host (`0.0.0.0`, `10.0.0.1`, `example.com`, …) and any `--taxon-id` other than the synthetic `1` the harness app + fixture serve; both validation primitives (`validateTaxonId`, `validateHost`) exported for the test slice. Injected `startFixtureFn` / `startExportFn` defaults preserve the in-process startServer path while letting the hermetic test slice observe close-order. Never hard-codes a port (`--port 0` for both servers); reverse-order cleanup under nested `finally` (export closed before fixture). `Makefile::capture-react-e2e` requires `OUTPUT_ROOT` (no default; no production ports baked in) and forwards `HARNESS_DIR`; `package.json` adds `scripts.capture:composed = "node scripts/composed-capture.mjs"`. Test surface: `tests/test_5c_2_b_react_harness.py` gains a composition block (11 hermetic cases; `subprocess` Node + Python; no Playwright / Chromium / FastAPI / SQLite / network) covering source contract (file exists + `node --check` + zero-dep), CLI gating (`--output-root` mandatory; `--host 0.0.0.0` rejected; `--taxon-id 2` rejected), validation primitives (`validateTaxonId(\"1\") → 1`; every other positive integer / zero / negative / non-numeric throws; `validateHost` accepts `127.0.0.1` / `::1` / `localhost` and rejects everything else), in-process orchestration with synthetic `out/index.html` + injected `buildFn` + injected `captureFn` (returns structured `taxa.react-e2e-composed-capture/1` envelope with OS-assigned loopback baseUrls), build bypass → fail-closed (`buildFn` claims success but no `out/index.html` → `composeCapture` throws BEFORE starting the export server or invoking `captureFn`), and reverse-order cleanup on capture failure (spy-tracked `close()` sequence: export `seq=1`, fixture `seq=2`). **RED** = pre-`5c.2-B.1b-ii-c` source-contract check (composition module + injected `startFixtureFn`/`startExportFn` seams + tightened `validateTaxonId`/`validateHost`) would FAIL — observed live by disabling the `n !== HARNESS_TAXON_ID` check and confirming `test_composed_capture_validate_taxon_id_accepts_one_only` + `test_composed_capture_cli_rejects_other_taxon_id` go RED with a clear "taxon" assertion miss and the CLI falling through to a real `npm run build` invocation that surfaces the missing validation. **GREEN** = `node --check` exits `0` on `composed-capture.mjs` + all 65 hermetic tests pass (21 fixture + 27 export-server + 11 composition + 6 source-contract parametrized). **No browser runtime success claimed** (chromium-driver.mjs is reachable via the default `captureFn` but the composition test slice never invokes it; the in-process test fixture uses an injected capture stub that returns synthetic evidence); no G4 aggregation; no G3 Tier-2 flip; no legacy `web/*.{html,js,css}` + `tailwind.config.js` deletion. The narrower remainder of `5c.2-B` (hermetic capture-driver tests that drive `chromium-driver.mjs` end-to-end, e2e selector modernization on the new component tree, legacy `web/*.{html,js,css}` + `tailwind.config.js` deletion) is still deferred. **G4 / G3 Tier-2 / cutover remain blocked; G4 is NOT flipped by the composition landing** (no `scripts/verify_parity.py` end-to-end flip; no production build artifact; no browser runtime success; only the orchestrator + CLI + Makefile target + package script + hermetic test slice shipped).
- [ ] **5c.2-B remainder (deferred)** — hermetic capture-driver tests that drive `chromium-driver.mjs` end-to-end against a real fixture + export server (the composition test slice uses an injected capture stub; the full capture driver is not yet exercised), e2e selector modernization on the new component tree, `web/*.{html,js,css}` + `tailwind.config.js` legacy deletion. G4 / G3 Tier-2 / cutover remain blocked.

- [ ] 5c.1 R — `tests/test_e2e_file_explorer.py` (modified,
      the test exists but selectors predate the React
      component tree): assert every legacy selector
      (`data-action="nav-tab"`, `data-path="<tab>"`,
      `data-theme`, the per-row kebab attribute, the per-row
      search icon attribute, the per-row materialize
      indicator attribute, the meta strip data attributes)
      still resolves on the new component tree.
      <!-- sdd-owner: implementation -->
- [ ] 5c.2 R — `tests/test_web_toggle.py` (modified): assert
      the theme toggle persists via
      `localStorage.taxa.settings.theme` and stamps
      `data-theme` on `<html>`; assert the OS
      `prefers-color-scheme` media query is honoured as the
      default when no stored preference exists.
      <!-- sdd-owner: implementation -->
- [ ] 5c.3 G — `tests/test_e2e_file_explorer.py` (selector
      update, ~120 LoC delta): update every DOM selector to
      the new component tree (the `data-*` attribute
      contract is preserved; the underlying CSS classes
      change to Tailwind 4 utility classes). Re-run the
      chromium fixture against `make api`; capture the
      Playwright trace artifact. <!-- sdd-owner: implementation -->
- [ ] 5c.4 G — `tests/test_web_toggle.py` (selector update,
      ~80 LoC delta): same pattern as 5c.3 for the theme
      toggle. <!-- sdd-owner: implementation -->
- [ ] 5c.5 T — Playwright + Lighthouse harness integration:
      parameterize over the legacy chromium fixture URL
      paths (`/`, `/index.html`,
      `/_next/static/<h>.js`) and assert the chromium
      fixture's traces match the new component tree.
      <!-- sdd-owner: implementation -->
- [ ] 5c.6 G — `web/index.html` deletion (file removed from
      the repo); `web/{app,state,api,tree,breadcrumb,detail,
      nav,dom,banner,help,keymap,settings,search,
      file_explorer,file_viewer,format,search_urls}.js`
      deletion (18 files removed); `web/index.css` deletion;
      `web/dist/tailwind.css` no longer tracked
(regenerated by reverted `make css` after rollback,
      never by the new build); `tailwind.config.js`
      deletion. The `web/index.html` deletion retires the
      1,963-line legacy inline CSS the four CSS children
      (3c-i / 3c-ii / 3c-iii / 3c-iv) migrated into
      `src/app/globals.css`. <!-- sdd-owner: implementation -->
- [ ] 5c.7 Refactor —
      `tests/test_evidence_baseline.py`'s
      `test_legacy_module_count_matches_exploration` test
      gets updated to assert the legacy `web/*.js` roster
      is **absent** (the test stays in the suite as a
      regression guard against legacy vanilla modules
      sneaking back into the tree). <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 5c.1, 5c.3 | `.venv/bin/python3 -m pytest tests/test_e2e_file_explorer.py -v` | Playwright runs the chromium fixture end-to-end against `make api` | `git revert <5c-sha>` restores `web/*.{html,js,css}` + `tailwind.config.js`; the test selector updates revert; no `src/` change |
| 5c.2, 5c.4 | `.venv/bin/python3 -m pytest tests/test_web_toggle.py -v` | same | same |
| 5c.5 | same | same; Playwright trace + Lighthouse JSON emitted | same |
| 5c.6 | same | `make api` boots uvicorn; `ls web/` empty | same |
| 5c.7 | `.venv/bin/python3 -m pytest tests/test_evidence_baseline.py::test_legacy_module_count_matches_exploration -v` | same | same |

## Phase 6: Validation work (after complete candidate path, before PR 3e)

The candidate path is the complete set of sub-PRs at positions
1–12 (toolchain bootstrap, App Router static export, the four
CSS children 3c-i / 3c-ii / 3c-iii / 3c-iv, Makefile/mount, 4a,
4b, 5a, 5b, 5c) accumulated on the tracker branch
`docs/complete-taxa-frontend-migration-plan` (nothing has
reached `develop` yet — the tracker stays draft/no-merge until
the chain completes). Phase 6 runs **after** that, **before**
PR 3e. It is **validation work**, not a migration objective —
it does not generate new `web/**` source, new `api/server.py`
route handlers, or new `extension/**` files. Its artifacts are
recorded in `apply-progress.md` §Change log as gate-flips (G5
reproducible, G6 PASS, G4 PASS).

Phase 6 has three sub-steps (6a, 6b, 6c) — one per gate closure
— and they MAY ship as three chain links (the default:
positions 13 / 14 / 15) or collapse into a single child PR at
position 13 depending on whether `apply-progress.md` records
them together or apart. Collapsing shortens the chain but does
not change the topology: the batch still targets the PR 5c
branch and PR 3e still targets whatever the last Phase 6 link
is. The maintainer's `ask-on-risk` policy applies if the batch
exceeds the 400-line budget (estimated ~190 authored LoC split
across the three sub-steps; comfortably under).

### Phase 6a: G5 hydration baseline closure (PR 6a → PR 5c branch, position 13/16)

- [x] 6a.1 R — `tests/test_hydration_timing.py` (already
      shipped by predecessor PR 1b.3b): the test asserts
      `scripts/measure_hydration.py` exits non-zero when the
      legacy baseline JSON is missing or schema-invalid. The
      test stays; no production code change. New helper
      script `scripts/reconstruct_hydration_baseline.py`
      reads the predecessor's documented
      `delta_server_to_tree_first_paint_ms` numbers from
      `openspec/changes/migrate-nextjs-tailwind4/design.md`
      §"Migration Evidence Base" and emits
      `web/dist/evidence-baseline.json` with the same schema
      the hydration test pins. (Bound to the user-approved
      replacement protocol in earlier attempts.) <!-- sdd-owner: implementation -->
- [x] 6a.2 G — `scripts/reconstruct_hydration_baseline.py`
      (~50 LoC): reads the legacy baseline numbers verbatim
      from the predecessor's design.md (input is the
      markdown source parsed for the table; output is a JSON
      file matching the schema
      `tests/test_hydration_timing.py` pins). (Bound to the
      user-approved replacement protocol in earlier
      attempts; HTTP-served legacy fixture capture
      against `http://127.0.0.1:64809/` in the fresh
      capture.) <!-- sdd-owner: implementation -->
- [x] 6a.3 G — run `python scripts/measure_hydration.py
      --baseline web/dist/evidence-baseline.json --candidate
      out/` against the positions 1–12-landed candidate
      build; emit the new hydration JSON next to the
      baseline; record the delta in `apply-progress.md`
      §Change log. (Fresh capture under the user-approved
      replacement protocol: baseline median `3.3 ms`,
      candidate median `3.2 ms`, delta `−0.1 ms`, threshold
      `10 ms`, both `captured`; `scripts/g5_close.sh` exit
      `0`.) <!-- sdd-owner: implementation -->
- [x] 6a.4 T — assert the delta ≤ 0 % on initial paint and
      interaction latency; if it exceeds, fail closed and
      write the exemption request into `design.md` §"Risk
      register" before G5 can flip. (Fresh-protocol
      tolerance = absolute (candidate − baseline) ≤ 10 ms
      under the user-approved replacement protocol;
      satisfied; tolerance recorded in
      `evidence/g5/{status,regression-report}.json`. The
      previous ≤ 0 % percentage rule is superseded by the
      user-approved replacement protocol and is retained
      in `apply-progress.md` change log as audit history
      only.) <!-- sdd-owner: implementation -->
- [x] 6a.5 Refactor — collapse the script + run + assert into
      a single `scripts/g5_close.sh` shim that the apply
      worker invokes once and records the outcome in
      `apply-progress.md`. (`scripts/g5_close.sh` is the
      canonical capture harness; fresh capture under this
      script exited `0`; `apply-progress.md` 2026-09-07
      change log entry records the G5 closure. The legacy
      5+2 percentage/median rule is superseded and retained
      as audit history only; the methodological-exception
      **request** is superseded by the user-approved
      replacement protocol and the fresh protocol
      evidence.) <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 6a.1–6a.5 | `.venv/bin/python3 -m pytest tests/test_hydration_timing.py -v` | `scripts/g5_close.sh` exits 0; `apply-progress.md` §Change log records the gate flip | `git revert <6a-sha>` removes `scripts/reconstruct_hydration_baseline.py` and the `apply-progress.md` delta; the legacy baseline JSON stays (regenerated on the next 6a run) |

### Phase 6b: G6 cutover rehearsal (PR 6b → PR 6a branch, position 14/16)

- [ ] 6b.1 R — `tests/test_rehearse_cutover.py` (new):
      asserts `scripts/rehearse_cutover.py` exits 0 against
      the activated manifest; parametrize over the four
      cutover-unit subsets (`web_dir_only`, `consumers_only`,
      `makefile_only`, `artifact_only`) and assert the
      fail-closed invariant (a subset-only rehearsal
      **fails**). <!-- sdd-owner: implementation -->
- [ ] 6b.2 G — `scripts/rehearse_cutover.py` (~120 LoC):
      dry-runs the atomic cutover unit (WEB_DIR repoint + 26
      consumer updates + Makefile rewrite + `out/` build
      artifact) against a `tmp_path` clone of the candidate.
      Runs the G3 Tier-2 verifier
      (`scripts/verify_consumers.py`) against the activated
      manifest; emits `cutover-rehearsal.json` with
      `activation_complete: true`, `unselected_count: 0`,
      and `silent_fallback_paths: []`. Exits non-zero on any
      subset-only dry-run. <!-- sdd-owner: implementation -->
- [ ] 6b.3 G — flip every `activation_status` and
      `replacement.status` in
      `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
      from `selected` (legacy pre-cut, Tier-1) to the
      **post-cut activation record** (Tier-2) for every one
      of the 26 §3.1 consumers. The flip is a planning
      artifact authored by the apply worker in the same
      release as the rehearsal script. **Predecessor
      `cutover-manifest.json` lives under
      `migrate-nextjs-tailwind4/` (frozen directory) — the
      flip is written into a working copy at
      `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
      per the spec §"Cutover-manifest activation" guidance.**
      The working copy is what PR 3e reads at cutover time;
      the predecessor copy stays byte-identical (frozen).
      <!-- sdd-owner: implementation -->
- [ ] 6b.4 T — assert the rehearsal script reports zero
      silent fallback paths (no "fall back to legacy `web/`
      on build failure" code path exists in `Makefile::api`
      or `api/server.py`). <!-- sdd-owner: implementation -->
- [ ] 6b.5 Refactor — extract the G3 Tier-2 invocation into
      a small `run_g3_tier2(manifest, out)` helper so the
      rehearsal script and the apply worker's PR 3e
      verification share the same code path.
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 6b.1, 6b.4 | `.venv/bin/python3 -m pytest tests/test_rehearse_cutover.py -v` | `scripts/rehearse_cutover.py` exits 0 against the activated manifest; `cutover-rehearsal.json` carries `activation_complete: true` | `git revert <6b-sha>` removes `scripts/rehearse_cutover.py`, `tests/test_rehearse_cutover.py`, and the working `cutover-manifest.json` copy; no `src/` or `api/` change |
| 6b.2 | same | same | same |
| 6b.3 | `python scripts/verify_consumers.py --manifest openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json --out out/ --serve --fixture-web-root <candidate>` | G3 Tier-2 verifier exits 0; `CONSUMER-READINESS.json` reports all 26 §3.1 consumers `selected` | same |

### Phase 6c: G4 Playwright + Lighthouse parity measurement (PR 6c → PR 6b branch, position 15/16)

Phase 6c ships the G4 parity measurement end-to-end across the four
sub-reports (`navigation`, `api`, `search`, `a11y`, `browser-state`).
It is split into sub-slices; the **first** sub-slice is the
navigation-only producer (already landed — see slice 6c.0 below). The
remaining sub-slices (6c.2–6c.5) capture the other four reports.
**No sub-slice flips G4 to PASS**; the gate stays blocked until all five
reports are captured and the pairwise aggregator exits 0. The umbrella
`scripts/g4_measure.sh` lands last so the apply worker has a single entry
point.

#### Slice 6c.0 — navigation-only producer (landed, non-closing)

- [x] 6c.0.1 R — `tests/test_capture_parity.py` carries
      25 hermetic parity-navigation tests (injected
      `runFn` + fixed `now()`; no browser, no live network).
      <!-- sdd-owner: implementation -->
- [x] 6c.0.2 G — `tools/g4-capture/scripts/parity_navigation.mjs`
      (Playwright driver; dynamic-imported; isolated pinned
      `playwright@1.49.1` alongside `lighthouse@12.2.1` +
      `chrome-launcher@1.2.1`; no root dependency changes).
      Writes `<outputRoot>/<UTC-timestamp>/{legacy,candidate}/`
      atomically (sibling-backup strategy mirrors `capture.mjs`).
      <!-- sdd-owner: implementation -->
- [x] 6c.0.3 T — atomic output verified; both sides written
      in a single run; fail-closed on missing/invalid origins,
      unavailable runner, 5xx / network errors, manifest path
      mismatch, output collision, and per-path outcome drift.
      <!-- sdd-owner: implementation -->
- [x] 6c.0.4 Refactor — `make parity-navigation` accepts explicit
      `LEGACY_ORIGIN` / `CANDIDATE_ORIGIN` / `PATHS` /
      `MANIFEST` / `OUTPUT_ROOT`; no production ports baked in;
      no umbrella `make parity` yet. README documents the slice
      as non-closing.
      <!-- sdd-owner: implementation -->

#### Slice 6c.1+ — api / search / a11y / browser-state + gate flip (pending)

- [ ] 6c.1 R — `tests/test_e2e_file_explorer.py` (already
      updated by Phase 5c) and `tests/test_web_toggle.py`
      (already updated by Phase 5c): the tests stay; no
      production code change. The G4 measurement is the
      delta between the Phase 5c Playwright + Lighthouse
      trace on the new candidate build and the legacy
      chromium fixture the predecessor captured.
      <!-- sdd-owner: implementation -->
- [ ] 6c.2 G — run Playwright + Lighthouse against the
      positions 1–12-landed candidate build; capture
      `out/g4-parity-report.json` with the initial paint and
      interaction latency numbers. Record the delta in
      `apply-progress.md` §Change log. <!-- sdd-owner: implementation -->
- [ ] 6c.3 T — assert the delta ≤ 0 % on initial paint and
      interaction latency; if it exceeds, fail closed and
      write the exemption request into `design.md` §"Risk
      register" before G4 can flip. <!-- sdd-owner: implementation -->
- [ ] 6c.4 Refactor — extract the measurement into
      `scripts/g4_measure.sh` so the apply worker invokes it
      once and records the outcome in `apply-progress.md`.
      <!-- sdd-owner: implementation -->

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 6c.0 (landed) | `.venv/bin/python -m pytest tests/test_capture_parity.py -k parity_navigation -v` | `make parity-navigation` (no production ports baked in); `<outputRoot>/<UTC-timestamp>/{legacy,candidate}/{navigation,manifest.snapshot,run}.json`; `apply-progress.md` records slice 6c.0 as non-closing | `git revert <6c-sha>` removes the producer + tests + Makefile delta + lockfile delta; slice 6c.1–6c.4 stay untouched; no G4 / G3 Tier-2 / cutover-status flip |
| 6c.1–6c.4 (pending) | `.venv/bin/python3 -m pytest tests/test_e2e_file_explorer.py tests/test_web_toggle.py -v` | `scripts/g4_measure.sh` exits 0; `out/g4-parity-report.json` carries initial paint + interaction latency; `apply-progress.md` §Change log records the gate flip | `git revert <6c-sha>` removes the `apply-progress.md` delta; no `tests/` or `scripts/` change (the measurement script stays as a future regression guard) |

## Phase 3e: Atomic cutover (PR 3e → PR 6c branch, position 16/16, gated on all six gates green)

The atomic cutover unit (per `design.md` §"Atomic cutover unit")
changes **exactly the following** in a single release. **No
subset revert is supported.** PR 3e ships only when:

- [ ] **G1 PASS** (recorded from the predecessor).
      <!-- sdd-owner: parent -->
- [ ] **G2 PASS** (recorded against the verified Next 16.3.3 /
      Turbopack clean build; predecessor `apply-progress.md`
      2026-08-30 entry). <!-- sdd-owner: parent -->
- [ ] **G3 Tier-1 PASS** (recorded: all 26 §3.1 consumers
      green against the legacy pre-cut runtime via the
      controlled fixture and `scripts/verify_consumers.py`;
      PR #109 + #111 + #115 + #116).
      <!-- sdd-owner: parent -->
- [ ] **G4 PASS** (Phase 6c measured; recorded in
      `apply-progress.md` §Change log).
      <!-- sdd-owner: parent -->
- [ ] **G5 PASS recorded** (Phase 6a captured under the
      user-approved replacement protocol; recorded in
      `apply-progress.md` 2026-09-07 change log entry; fresh
      `evidence/g5/{status,regression-report}.json` with
      `status: "ready"`, `regression: false`, `pass: true`,
      baseline median `3.3 ms`, candidate median `3.2 ms`,
      delta `−0.1 ms`, threshold `10 ms`, both `captured`).
      <!-- sdd-owner: parent -->
- [ ] **G6 PASS** (Phase 6b rehearsed; recorded in
      `apply-progress.md` §Change log).
      <!-- sdd-owner: parent -->

If any gate is absent, failed, stale (> 7 days), or
incomparable, PR 3e is **blocked**, never success. The four-set
cutover:

1. **`WEB_DIR` constant** at `api/server.py:54` (already
   repointed in Phase 3d; PR 3e flips the build artifact under
   `out/` from the candidate build to the production build
   with the `engines.node >= 20.9.0` runtime check live).
2. **Every active-consumer update** in the predecessor's
   `design.md::§3.1` (already authored by Phase 3d for the
   AC-21 reader path; PR 3e flips the remaining 25 §3.1
   consumers to read from the React component tree instead
   of the legacy `web/*` paths). The flip is the post-cut
   activation record in
   `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
   (working copy; predecessor copy stays frozen).
3. **The `Makefile::api` and `Makefile::web` targets**
   (already rewritten by Phase 3d; PR 3e flips the legacy
   `make css` Tailwind-3.4 step from "regenerate
   `web/dist/tailwind.css`" to "exit 0 no-op" — the Tailwind
   4 build lives inside `next build`).
4. **The build artifact** — the `out/` directory itself
   (`out/index.html`, `out/_next/static/chunks/**`,
   `out/.next/build-manifest.json`, the error-page
   classification if `404.html` / `500.html` is emitted).
   The artifact is regenerated by the production build at
   cutover time.

The PR 3e task list (only after all six gates green):

- [ ] 3e.1 R — `tests/test_verify_consumers.py` (already
      shipped by predecessor PR #109 + #111 + #115 + #116):
      the test stays; PR 3e re-runs it against the activated
      manifest at
      `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`.
      <!-- sdd-owner: implementation -->
- [ ] 3e.2 G — run
      `python scripts/verify_consumers.py --manifest openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json
      --out out/` against the candidate build; assert
      `CONSUMER-READINESS.json` exits 0 with
      `activation_complete: true`, `unselected_count: 0`.
      <!-- sdd-owner: implementation -->
- [ ] 3e.3 G — re-run `make api` against the cutover build;
      assert uvicorn binds `127.0.0.1:8765` only; assert
      `curl http://127.0.0.1:8765/index.html` returns
      `out/index.html`; assert
      `extension/manifest.json::host_permissions` stays
      `["http://localhost:8765/*"]`.
      <!-- sdd-owner: implementation -->
- [ ] 3e.4 G — re-run `make smoke` against the cutover
      build; assert 63 passed, 8 skipped baseline preserved.
      <!-- sdd-owner: implementation -->
- [ ] 3e.5 G — flip the gate-status footer in
      `apply-progress.md` §Status from "blocked / blocked /
      blocked" (G4 / G6 / G3-Tier2 still blocked; G5 already
      PASS recorded under the user-approved replacement
      protocol) to "PASS recorded (G4 / G6 closed by Phase
      6c / 6b; G3 Tier-2 activated on PR 3e; G5 already
      PASS recorded under the user-approved replacement
      protocol in the 2026-09-07 change log entry)".
      <!-- sdd-owner: implementation -->
- [ ] 3e.6 T — `tests/test_verify_build.py` (already shipped
      by predecessor G2 evidence): the test stays; re-run
      against `out/BUILD-INVENTORY.json` from the cutover
      build; assert no asset class is missing.
      <!-- sdd-owner: implementation -->
- [ ] 3e.7 Refactor — `apply-progress.md` §Change log
      records the cutover commit hash, the gate-flip dates,
      and the G3 Tier-2 verifier output. <!-- sdd-owner: implementation -->

### Rollback under the chain

PR 3e is the **last child**, not a `develop` PR. Two rollback
windows exist:

| Window | State | Rollback |
|---|---|---|
| Before the tracker merges | Nothing is on `develop`; the cutover lives only on the tracker branch | Hold or close the tracker PR — `develop` is untouched by construction |
| After the tracker merges | The whole chain lands on `develop` in one integration | `git revert <pr3e-sha>` restores the legacy vanilla build atomically (per `design.md` §"Rollback unit") |

For `<pr3e-sha>` to stay addressable on `develop`, the tracker
 MUST land with a **merge commit** (no squash), so the chain's
individual commits survive integration. If the tracker is
squash-merged instead, the atomic rollback unit becomes the
tracker merge itself: `git revert -m 1 <tracker-merge-sha>`.
Either way the rollback is **one** revert covering the full
four-set cutover — **no subset revert is supported**.

**Per-task evidence**:

| Task | Focused test command | Runtime harness | Rollback boundary |
|------|----------------------|-----------------|-------------------|
| 3e.1–3e.2 | `.venv/bin/python3 -m pytest tests/test_verify_consumers.py -v` | G3 Tier-2 verifier exits 0; `CONSUMER-READINESS.json` carries `activation_complete: true` | `git revert <pr3e-sha>` restores the legacy vanilla build atomically (per `design.md` §"Rollback unit"): `web/index.html`, `web/app.js`, the 18 `web/*.js` modules, `web/dist/tailwind.css`, `tailwind.config.js`, the legacy `package.json` + `package-lock.json`, the legacy `Makefile::api`, the legacy `api/server.py:54` |
| 3e.3 | `curl http://127.0.0.1:8765/index.html` returns `out/index.html` | `make api` boots uvicorn on 8765; `lsof -i :8765` shows uvicorn only | same |
| 3e.4 | `make smoke` exits 0 | same | same |
| 3e.5 | n/a (planning artifact) | n/a | same |
| 3e.6 | `.venv/bin/python3 -m pytest tests/test_verify_build.py -v` | `out/BUILD-INVENTORY.json` carries no missing class | same |
| 3e.7 | n/a | n/a | same |

## Out of scope (per `AGENTS.md` and the proposal)

- **No `git push`, `git commit`, `gh pr create`, `git stash`**
  in this tasks phase. The apply phase owns those actions.
- **No new worktrees** — the apply worker creates worktrees per
  `AGENTS.md` §4.
- **No edits to `openspec/changes/migrate-nextjs-tailwind4/**`**
  (predecessor frozen).
- **No backend rewrite** (`api/server.py` route handlers,
  SQLite/WAL logic, materialize flow, SSRF defence in
  `save-url`).
- **No ETL pipeline edits** (`etl/parse_textree`,
  `etl/load_coldp`, `etl/load_worms`,
  `etl/load_freshwater`, migrations).
- **No Chrome extension parity work** — a separate change
  tracks any React-aware extension adaptation.
- **No SEO / metadata / sitemap / robots work**.
- **No new routes** (Settings, About, Help) beyond what the
  legacy UI exposes today.
- **No coverage tooling** (`coverage.available: false`).
- **No visual redesign** (impeccable / Stitch follow-up).
- **No single-PR consolidation of the four CSS children** —
  the 4-child sub-sequence is binding; do not collapse 3c-i /
  3c-ii / 3c-iii / 3c-iv into a single sub-PR (the previous
  single PR 3c was unsatisfiable because it tried to migrate
  the 1,963-line legacy inline CSS in one sub-PR under the
  400-line per-PR review budget).

## Predecessor freeze contract (binding)

Every sub-PR in Phases 3a–6c and PR 3e MUST satisfy:

- [ ] `git diff --stat origin/develop -- openspec/changes/migrate-nextjs-tailwind4/`
      shows zero changes. <!-- sdd-owner: parent -->
- [ ] `git diff --stat <immediate-base-branch>` shows **only**
      this slice's files (chain diff hygiene; a polluted diff is
      a base bug — retarget or rebase, do not review around it).
      <!-- sdd-owner: parent -->
- [ ] The PR's branch-protection check rejects any PR that
      modifies `openspec/changes/migrate-nextjs-tailwind4/**`.
      <!-- sdd-owner: parent -->
- [ ] The PR's CI / lint hook rejects the same.
      <!-- sdd-owner: parent -->

If a sub-PR accidentally edits the predecessor directory, the
sub-PR is **blocked** and the apply worker must revert the
accidental edit before the PR can merge. There is no
`size:exception` path for predecessor edits.

## Forecast reconciliation

> **2026-09-02 — PR 3c sub-sequence replan**: the original
> single PR 3c at ~230 LoC was unsatisfiable against the
> 1,963-line legacy inline `<style>` block. The 3c slot is
> now four reviewable children at positions 3–6. Total
> authored LoC rises from ~2,245 to ~3,485 (+1,240) because
> every legacy CSS rule is ported. The largest sub-PR is
> **3c-i at ~390 LoC** (-10 LoC headroom under 400). All 16
> children stay ≤ 400 LoC authored **except PR 3c-ii,
> which carries a user-approved size:exception** for
> the complete taxonomy tree / detail CSS slice
> (actual implementation totals 822 insertions + 9
> deletions = 831 LoC, overshooting the prior `~380 LoC`
> estimate by +442 LoC and the 400-line per-PR
> review budget by +431 LoC — see the dedicated append-only
> addendum below for the authorization rationale
> and the corrected estimate; the 16-child chain is
> preserved). PR 3a retains the regenerated-
> `package-lock.json` size:exception
> (generated-resolution-only) as the prior documented
> size:exception; **PR 3c-ii is now the second
> user-approved size:exception** alongside PR 3a.
> **Approach A, FastAPI/SQLite, the frozen predecessor,
> and the Feature Branch Chain strategy remain unchanged.**

- **3a** ~210 LoC authored (toolchain bootstrap — `package.json`
  dep pins + `scripts/check-runtime.mjs` + `tsconfig.json` base
  + `.nvmrc` + 2 new tests); **3b** ~175 (App Router entry —
  `src/app/{layout,page}.tsx` + `next.config.mjs` +
  `tests/test_app_shell_render.py`, now satisfiable because 3a
  installed Next); **3c-i** ~390 (tokens / base / dark mode +
  global focus-visible selectors + `@theme` + dark cascade);
**3c-ii** **831 actual (822 insertions + 9 deletions)** — **user-approved size:exception** (taxonomy tree / detail styling + kebab
  + materialize modal — actual implementation overshoots the prior `~380 LoC` estimate by +442 LoC and the 400-line per-PR review budget by +431 LoC; see addendum below for authorization rationale); **3c-iii** ~390 (Search / Folder /
  global Browser styling + file explorer chrome + CSV / JSON
  viewers); **3c-iv** ~280 (animations + image/video viewer
  frames + Settings view + design-system barrel +
  final utility-class parity); **3d** ~240 (Makefile rewrite +
  `WEB_DIR` repoint + AC-21 reader + 2 new tests, the heaviest
  of the re-scoped later children); **4a** ~180; **4b** ~90;
  **5a** ~280; **5b** ~360; **5c** ~200; **6a** ~50;
  **6b** ~120; **6c** ~20; **3e** ~120.
  **Total**: ~3,485 LoC authored across **16 sub-PRs** (up
  from ~2,245 across 13 sub-PRs; the +1,240 delta is the full
  port of the legacy inline `<style>` block).
- Largest sub-PR by plan is **3c-i at ~390 LoC authored**,
  with -10 LoC (-2.5 %) headroom against the **400-line
  per-PR review budget**. The previously-largest 5b is
  now second at ~360 LoC (-40 LoC, -10 % headroom).
  **All 16 sub-PRs ≤ 400 LoC authored except PR 3c-ii**,
  which carries a **user-approved `size:exception`** for
  the complete taxonomy tree / detail CSS slice (actual
  implementation totals **831 LoC = 822 insertions + 9
  deletions**, overshoot +431 LoC against the 400-line
  budget — see the dedicated addendum below for the
  authorization rationale; the PR 3a lockfile exception
  is generated-resolution-only and remains the first
  documented size:exception, with PR 3c-ii now the
  second).
- Heaviest of the 3c sub-children by plan is **3c-i at
  ~390 LoC**; **PR 3c-ii is the heaviest sub-PR by actual
  diff at 831 LoC** (user-approved size:exception, see
  above); the lightest is **3c-iv at ~280 LoC** (because
  the design-system barrel is small). Sub-PR **6c** is
  the smallest overall at ~20 LoC; the G4 measurement
  artifact
  is recorded in `apply-progress.md` rather than in a code
  diff.
- Phase 6 collectively (6a + 6b + 6c) totals ~190 LoC authored
  and ~120 LoC of measurement artifact. If the maintainer
  prefers a single chained batch for Phase 6, the combined
  LoC is still well under 400; if the maintainer prefers
  three separate sub-PRs for review focus, each is also
  under.
- **Chained PRs recommended: Yes** — each sub-PR fits the
  per-PR budget on its own, but the ~3,485-line total and the
  atomic cutover (the feature MUST integrate before it
  reaches `develop`) put this change in the Feature Branch
  Chain gate. The 3c sub-sequence itself is four chained
  children because the 1,963-line inline CSS must be ported
  verbatim into Tailwind 4 `@theme` + `@layer base` and that
  work does not fit under 400 LoC as a single PR.
- **Chain strategy: `feature-branch-chain`** (user-selected,
  unchanged by the 3c replan). Tracker
  `docs/complete-taxa-frontend-migration-plan` is
  draft/no-merge and is the **only** PR targeting `develop`;
  PR 3a targets the tracker (now merged as PR #144); PR 3b
  targets PR 3a (now merged as PR #145, with PR #146 reconcile
  also merged); **PR 3c-i targets the tracker** (after PR #146
  lands, picking up the already-merged 3a + 3b + reconcile
  without an extra reconcile step); every later 3c child
  targets its immediate predecessor 3c branch; every later
  post-3c child targets its immediate predecessor branch.
  This supersedes the `AGENTS.md` §4 direct-to-`develop`
  default and the predecessor's apply-progress precedent for
  this change.
- **Chain length: 16 child PRs + 1 tracker.** Review budget
  per child is the authored LoC listed above; the tracker
  carries no review budget of its own (it is the
accumulation point). The first new CSS child (PR 3c-i)
  treats the tracker PR #146 as the merged starting point
  for the four-child sub-sequence.
- **Delivery strategy: `ask-on-risk`** (per preflight; no risk
  flag is open — Approach A is FINAL, the predecessor is
  frozen, every sub-PR fits under 400 lines, the corrected
  chain satisfies the dependency order the apply gate
  identified as the defect, and the 3c sub-sequence replan
  satisfies the LoC budget the apply gate identified as
  unsatisfiable for the original single PR 3c).
- **Corrective plan revision + 3c sub-sequence replan
  overhead**: the reordering absorbed the work originally
  attributed to PR 3a, PR 3b, and PR 3c into the new
  positions 1, 2, 3, 4 (the original PR 3c itself was then
  replaced by the four-child 3c sub-sequence at positions
  3–6). The absolute authored line count moved from ~2,225
  (pre-correction) to ~2,245 (post-correction, single 3c)
  to ~3,485 (post-replan, four-child 3c sub-sequence) because
  the new split moves every legacy CSS rule out of the
  single 3c bucket and into a reviewable sub-sequence that
  the parity test can enumerate line-by-line. No production
  code is duplicated; the delta is test wiring + parity
  enumeration of every legacy selector.
- **Risk / decision (if maintainer prefers a flatter chain)**:
  positions 1–2 (toolchain bootstrap + App Router static
  export) could collapse into a single sub-PR at ~385 LoC
  authored — under 400 but tight. The 3c sub-sequence
  cannot collapse further: even the lightest pair (3c-i +
  3c-ii at ~770 LoC combined) exceeds the 400-line budget by
  ~93 %. The chain topology preserves the bootstrap as a
  separate review focus so the toolchain pins and the App
  Router contract can be reviewed independently; the 3c
  sub-sequence preserves the four CSS slices as separate
  review focuses so the token / base / dark cascade, the
  taxonomy surface, the browser / search / folder surface,
and the animations / utilities / design-system barrel can
  each be reviewed independently. Collapsing any 3c pair is
  not the default.

## Addendum — 2026-09-09: PR 3c-ii size:exception authorization (documentation-only; not merged or verified) (append-only)

- **PR 3c-ii size:exception authorized (this entry, opens a second user-approved size:exception alongside the prior PR 3a regenerated-`package-lock.json` exception; 16-child chain preserved; no other scope changes; the PR is NOT claimed merged or verified by this addendum)**. The user authorized a `size:exception` for PR 3c-ii because the actual implementation of the complete taxonomy tree / detail CSS slice required **822 insertions + 9 deletions = 831 LoC**, against the prior `~380 LoC` estimate recorded in this tasks file's "Review Workload Forecast", the PR 3c sub-sequence replan rationale callout above, the per-PR dependency description for PR 3c-ii, and the design.md "Sub-PR slice under Approach A" table — i.e. the actual implementation overshoots the 400-line per-PR review budget that Approach A locked on 2026-09-02 by +431 LoC. **Authorization rationale** (why a single reviewable PR is preferred over further slicing): (a) the taxonomy tree / detail selectors, the realm-tinted `.tree-row[data-realm="…"]` variants, the kebab menu / materialize modal selectors, the `#detail-panel` / `.detail-card` / `.detail-section` / `.overview-section` / `.detail-item` / `.search-pulse` / `.detail-tabs` / `.search-icon-btn` / `.materialize-btn` surface, and the parity-test slice in `tests/test_tailwind_4_parity.py` are inseparable from the 3c-i base layer (they must ship together so every selector resolves its `var(--token)` references against the live `:root` token slice); (b) splitting PR 3c-ii further into a 4c-i / 4c-ii pair would duplicate the `var(--token)` consumer surface across two PRs and force the later child to re-touch selectors the earlier child already locked; (c) the four-child 3c sub-sequence already minimised blast radius by splitting the 1,963-line legacy inline `<style>` into four reviewable siblings (3c-i / 3c-ii / 3c-iii / 3c-iv), so the present overshoot reflects the realistic CSS-port surface for the taxonomy tree / detail concern rather than a planning defect; (d) the `tests/test_tailwind_4_parity.py` enumeration of every taxonomy selector — the dominant contributor to the 831 LoC count — is itself an inseparable slice (splitting the enumerator across two PRs would leave a half-coherent test that nobody can review coherently and would still need to be re-merged at PR 5c). **The 16-child chain is preserved**: PR 3c-ii stays at position 4/16 with the same predecessor (`feat/complete-taxa-frontend-migration-03-3c-i`) and the same successor (`feat/complete-taxa-frontend-migration-05-3c-iii`); the per-PR dependency description, the corrected ordering, the Approach A lock, the FastAPI/SQLite foundation, the Feature Branch Chain strategy, the predecessor frozen status, the per-domain specs, every prior addendum (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c), and the user-approved replacement G5 protocol recorded in `design.md` are unchanged. **The PR is not claimed merged or verified by this addendum** — the size:exception only authorises a single reviewable PR against the established budget; review, CI, and merge follow the ordinary feature-branch-chain process. The corrected estimates (`831 LoC total: 822 insertions, 9 deletions`) supersede the prior `~380 LoC` figure in the four tables above; the inline `~380 (≤ 400; -20 LoC headroom)` budget in the sub-PR slice table becomes `831 (overshoot +431 LoC against the 400-line budget; user-approved size:exception for this PR)`; the Review Workload Forecast's `Largest new sub-PR is 3c-i at ~390 LoC` becomes `Largest new sub-PR by actual diff is PR 3c-ii at 831 LoC`; the `All 16 sub-PRs ≤ 400 LoC authored` line is annotated with `except PR 3c-ii, which carries a user-approved size:exception`; the `no new size:exception is opened` clause is annotated with `except for PR 3c-ii, which is now the second user-approved size:exception alongside PR 3a`. Spanish mirror (`documents-es/openspec/changes/complete-taxa-frontend-migration/tasks-es.md`) carries the same semantics; any drift is resolved in favour of the English. No code change; no rebase; no new branch; no commit/push; no PR open.

## Addendum — 2026-09-09: PR 3c-iii size:exception authorization (documentation-only; not merged or verified) (append-only)

- **PR 3c-iii size:exception authorized (this entry, opens a third user-approved size:exception alongside the prior PR 3a regenerated-`package-lock.json` exception AND the previously authorized PR 3c-ii taxonomy-tree CSS exception; 16-child chain preserved; PR 3c-iv surfaces deferred to the next child in the chain with unchanged scope; the PR is NOT claimed merged or verified by this addendum)**. The user authorized a `size:exception` for PR 3c-iii because the actual implementation of the complete Search / Folder / global Browser CSS slice required **1669 insertions and 66 deletions = 1735 review lines (net +1603)**, against the prior `~390 LoC` estimate recorded in this tasks file's "Review Workload Forecast", the PR 3c sub-sequence replan rationale callout above, the per-PR dependency description for PR 3c-iii, and the `design.md` "Sub-PR slice under Approach A" table — i.e. the actual implementation overshoots the 400-line per-PR review budget that Approach A locked on 2026-09-02 by **+1335 LoC** and the prior `~390 LoC` estimate by **+1345 LoC**. **What the PR actually preserves**: the **complete Search / Folder / global Browser selector catalogue** (`.toast` / `.toast-error`, `.search-engines-grid`, `.search-category-header`, `.search-engine-btn`, `.fex-meta-strip`, `.fex-tab-strip`, `.fex-snippet-frame`, `.fex-shell`, `.fex-tree-pane`, `.fex-viewer-pane`, `.fex-splitter`, `.fex-row` + `.selected` / `.file` / `.folder` variants, `.fex-tree-header`, `.fex-children`, `.fex-banner`, `.fex-empty-state`, `.fex-search-*`, `.fex-csv-*`, `.fex-json-*`, `.fex-tree-truncated`, per the 3c-iii scope enumeration in the per-PR dependency description above) and its **canonical parity contract** (`tests/test_research_styles.py` enumerates every Search / Folder / global Browser selector; `tests/test_tailwind_4_parity.py` extends its browser selector slice; every selector resolves to a non-empty declaration in `src/app/globals.css` and `out/_next/static/chunks/*.css`). **3c-iv surfaces deferred**: the `@keyframes` rules + `.animate-spin` + the image / video viewer frames + the Settings view selectors + the design-system barrel (`src/modules/design-system/{infrastructure/index.ts, presentation/Icon.tsx, presentation/Button.tsx}`) remain deferred to PR 3c-iv at position 6/16 with no scope change; PR 3c-iv's `~280 LoC` estimate is unchanged. **Authorization rationale** (why a single reviewable PR is preferred over further slicing): (a) the Search / Folder / global Browser selectors are inseparable from the 3c-i base layer (tokens + dark-mode cascade) AND from the 3c-ii taxonomy selectors (the research selectors `.search-tab` / `.folder-tab` / `.header-browser-tab` ride on the live `var(--token)` references that 3c-ii just shipped); they must ship together as a single CSS slice so every browser / research selector resolves its `var(--token)` references against the live base layer; (b) splitting PR 3c-iii further into a 4c-i / 4c-ii pair would duplicate the `var(--token)` consumer surface across two PRs and force the later child to re-touch selectors the earlier child already locked — duplicating the planning defect the four-child 3c sub-sequence already closed; (c) the four-child 3c sub-sequence already minimised blast radius by splitting the 1,963-line legacy inline `<style>` into four reviewable siblings (3c-i / 3c-ii / 3c-iii / 3c-iv), so the present overshoot reflects the realistic CSS-port surface for the Search / Folder / global Browser concern rather than a planning defect (the `~390 LoC` estimate under-counted the canonical parity-test enumeration of every browser selector, the `.fex-search-*` / `.fex-csv-*` / `.fex-json-*` family depth, and the `.fex-tree-pane` / `.fex-viewer-pane` / `.fex-splitter` / `.fex-banner` chrome dimensions); (d) the `tests/test_tailwind_4_parity.py` + `tests/test_research_styles.py` enumeration of every Search / Folder / global Browser selector — the dominant contributor to the 1735 review-line count — is itself an inseparable slice (splitting the enumerator across two PRs would leave a half-coherent test that nobody can review coherently and would still need to be re-merged at PR 5c). **The 16-child chain is preserved**: PR 3c-iii stays at position 5/16 with the same predecessor (`feat/complete-taxa-frontend-migration-04-3c-ii`) and the same successor (`feat/complete-taxa-frontend-migration-06-3c-iv`); PR 3c-iv stays at position 6/16 with the same `~280 LoC` estimate and unchanged scope; the per-PR dependency description, the corrected ordering, the Approach A lock, the FastAPI/SQLite foundation, the Feature Branch Chain strategy, the predecessor frozen status, the per-domain specs, **the existing PR 3c-ii size:exception stays open** (PR 3c-ii's 831 LoC overshoot is unchanged; this addendum does NOT modify, replace, or supersede the PR 3c-ii exception — both exceptions coexist on the same chain), every prior addendum (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c, 3c-ii), and the user-approved replacement G5 protocol recorded in `design.md` are unchanged. **The PR is not claimed merged or verified by this addendum** — the size:exception only authorises a single reviewable PR against the established budget; review, CI, and merge follow the ordinary feature-branch-chain process. The corrected estimates (`1735 review-line total: 1669 insertions, 66 deletions; net +1603; overshoot +1335 LoC against the 400-line budget and +1345 LoC against the prior ~390 LoC estimate; user-approved size:exception for this PR`) supersede the prior `~390 LoC` figure in the tables above; the inline `~390 (≤ 400; -10 LoC headroom)` budget in the sub-PR slice table becomes `1735 review lines (overshoot +1335 LoC against the 400-line budget and +1345 LoC against the prior ~390 LoC estimate; user-approved size:exception for this PR)`; the Review Workload Forecast's `Largest new sub-PR by actual diff is PR 3c-ii at 831 LoC` becomes `Largest new sub-PR by actual diff is PR 3c-iii at 1735 review lines (net +1603; overshoot +1335 LoC against the 400-line budget and +1345 LoC against the prior ~390 LoC estimate; user-approved size:exception), with PR 3c-ii second at 831 LoC (user-approved size:exception) and PR 3c-i third at ~390 LoC`; the `All 16 sub-PRs ≤ 400 LoC authored` line is annotated with `except PR 3c-ii (831 LoC) AND PR 3c-iii (1735 review lines), both of which carry user-approved size:exceptions`; the `no new size:exception is opened` clause is annotated with `except for PR 3c-ii (already authorized) AND PR 3c-iii (authorized by this entry), which are the second and third user-approved size:exceptions alongside PR 3a`. Spanish mirror (`documents-es/openspec/changes/complete-taxa-frontend-migration/tasks-es.md`) carries the same semantics; any drift is resolved in favour of the English. No code change; no rebase; no new branch; no commit/push; no PR open.

## Addendum — 2026-09-09: PR 5.5 Tailwind 4 / PostCSS pipeline repair (landed; the first post-3c sub-sequence repair child; 17-child chain; the fourth user-approved size:exception for the regenerated package-lock.json alongside PR 3a + PR 3c-ii + PR 3c-iii) (append-only)

- **PR 5.5 Tailwind 4 / PostCSS pipeline repair landed (this entry, inserts a new repair child between PR 3c-iii and PR 3c-iv, expands the chain from 16 children to 17 children, opens a fourth user-approved size:exception for this PR's regenerated `package-lock.json` alongside the existing PR 3a + PR 3c-ii + PR 3c-iii exceptions, and surfaces the G2 production-candidate evidence gap the prior chain left open; the PR is implemented in this worktree but is NOT claimed merged, NOT claimed G2-PASS, and NOT claimed browser-verified by this addendum)**. **Confirmed defect (root cause + observable signature at artifact level)**: PR 3c-i shipped `src/app/globals.css` with the canonical Tailwind 4 surface — `@import "tailwindcss";` followed by an `@theme { --primary: #1d7ea9; --accent: #176587; --surface: #ffffff; … --realm-bacteria: #5ebd9b; … }` block carrying every legacy `:root` / `[data-theme="dark"]` / `--realm-*` token. PR 3c-ii, PR 3c-iii, and the prior toolchain bootstrap PR 3a all consumed that surface under the assumption that `next build`'s default PostCSS pipeline would process `@import "tailwindcss"` and expand the `@theme { … }` block. **The assumption was wrong**: PR 3a added `tailwindcss@^4` as a top-level dep, but the project never registered a PostCSS plugin for it (no `postcss.config.mjs` at the repo root, no `@tailwindcss/postcss` dep). Turbopack's default PostCSS pipeline does NOT recognize `@import "tailwindcss";` as a Tailwind 4 directive and does NOT recognize `@theme { … }` as a CSS at-rule — the build emits a non-fatal `Unknown at rule: @theme` warning, leaves the `@theme { … }` block as a literal at-rule in the compiled CSS (the browser silently drops it because `@theme` is not a real CSS at-rule), and ships zero Tailwind preflight + zero `@tailwindcss/postcss`-expanded `:root` tokens. **Observed consequence (this worktree, base commit `6375927`, before PR 5.5)**: `next build` exits `0`, the legacy `.research-explorer` / `.fex-row` / `.tree-row` / `.tier-header` / `.load-all` / `.kebab` / `.search-tab` / `.folder-tab` / `.header-browser-tab` / `.fex-meta-strip` / `.fex-tab-strip` / `.fex-snippet-frame` / `.fex-csv-table` / `.fex-json-tree` / `.fex-tree-leaf` selectors ship (because they are plain CSS that does not need Tailwind processing), but **every `var(--primary)` / `var(--accent)` / `var(--surface)` / `var(--on-surface)` / `var(--realm-bacteria)` / `var(--realm-archaea)` / `var(--realm-viruses)` / `var(--realm-animalia)` / `var(--realm-fungi)` / `var(--realm-plantae)` / `var(--realm-chromista)` / `var(--realm-other)` reference inside those selectors resolves to `unset` at runtime** — the entire visual cascade is broken. The Tailwind 4 preflight (`*,:after,:before,::backdrop { box-sizing: border-box; border: 0 solid; margin: 0; padding: 0 }`) is absent; the Tailwind 4 utility class surface is absent; the `@keyframes spin { to { transform: rotate(360deg) } }` animation is absent. The compiled CSS bundle at `out/_next/static/chunks/391guka-hdllv.css` (Turbopack's chunked pipeline hash; this is the only CSS bundle `next build` emits for this repo) shrinks from **50,891 bytes** (with `@tailwindcss/postcss` running) to **35,093 bytes** (without it) — a ~31% shrink that is the defect's byte-level fingerprint. **What PR 5.5 ships (this worktree's edit surface)**: (1) `package.json` adds **two new top-level `dependencies` entries**: `"@tailwindcss/postcss": "^4.3.3"` (the official Tailwind 4 PostCSS plugin, resolved against the same `^4` major as the existing `tailwindcss` dep) and `"postcss": "^8.5.0"` (the runtime that `@tailwindcss/postcss` depends on — explicitly required now because PR 3a removed the legacy `postcss` top-level dep along with `autoprefixer` / `@tailwindcss/forms`, and the Tailwind 4 plugin needs a peer `postcss` to run). The Tailwind 3-era plugins (`autoprefixer`, `@tailwindcss/forms`) stay banned. (2) New file `postcss.config.mjs` at the repo root, `export default { plugins: { "@tailwindcss/postcss": {} } }` — a minimal ESM PostCSS config registering only the official Tailwind 4 plugin (no `autoprefixer`, no `@tailwindcss/forms`, no other legacy plugins). (3) Regenerated `package-lock.json` (this PR's regenerated lockfile is the **fourth user-approved size:exception** for this project, alongside the existing PR 3a + PR 3c-ii + PR 3c-iii exceptions — see the lockfile-exception paragraph below for the authorization rationale and the lockfile delta). (4) `tests/test_toolchain_bootstrap.py` is updated: `REQUIRED_DEPS_PRODUCTION` is expanded from `(("tailwindcss", "4"),)` to `(("tailwindcss", "4"), ("postcss", None), ("@tailwindcss/postcss", None))` so `postcss` and `@tailwindcss/postcss` are pinned as required production deps (major unconstrained because Tailwind 4 keeps them aligned with its own release cadence); `FORBIDDEN_LEGACY_DEPS` shrinks from `("autoprefixer", "postcss", "@tailwindcss/forms")` to `("autoprefixer", "@tailwindcss/forms")` so the Tailwind 3-era `autoprefixer` + `@tailwindcss/forms` ban stays open while `postcss` is now required (not banned). (5) New test surface `tests/test_tailwind_build_pipeline.py` — a focused regression test that performs a REAL `next build` against the repo, reads the compiled CSS bundle under `out/_next/static/{css,chunks}/*.css`, and asserts: (a) `next build` exits `0`; (b) at least one CSS bundle exists under the static-export path; (c) the Tailwind 4 preflight universal-selector rule (`*,:after,:before,::backdrop { box-sizing: border-box; … }`) is present in the compiled CSS — this is the canonical witness that `@tailwindcss/postcss` actually ran; (d) the literal at-rule `@theme {` is NOT present in the compiled CSS — a literal `@theme {` surviving is the signature defect that proves the plugin never expanded the `@theme` block into the `@layer theme { :root, :host { … } }` declaration the browser actually reads; (e) the literal substring `@import "tailwindcss"` is NOT present in the compiled CSS — a literal import surviving is the signature that the plugin never resolved the directive; (f) every CSS bundle contains the preflight (no subset leakage — the plugin ran on all bundles, not just one); (g) the legacy `:root` palette token `--primary: #1d7ea9` lives inside a `@layer theme { :root, :host { … } }` declaration (the canonical Tailwind 4 expansion shape, NOT inside a literal `@theme` block). The fixture cleans `out/` and `.next/` on teardown IF they did not exist before the test entered (so a developer who already has an `out/` from a prior build keeps theirs; the test owns its own artifact lifecycle). **Strict-TDD evidence observed in this worktree (RED → GREEN → TRIANGULATE)**: **RED** = pre-implementation, both the new test file's 7 cases AND the updated toolchain test's 2 new dep cases FAIL with the post-3c-iii base — `tests/test_tailwind_build_pipeline.py::test_next_build_emits_css_bundle_under_out_static` and 5 sibling tests ERROR with `postcss.config.mjs missing at … PR 5.5 ships @tailwindcss/postcss as the registered plugin`; `tests/test_tailwind_build_pipeline.py::test_triangulate_postcss_config_registers_tailwind_plugin_only` FAILS with `postcss.config.mjs missing at … PR 5.5 ships the root postcss.config.mjs registering @tailwindcss/postcss`; `tests/test_toolchain_bootstrap.py::test_required_dep_present_in_dependencies[postcss-None]` and `[postcss-None]` and `[@tailwindcss/postcss-None]` FAIL with `production dep 'postcss' missing from dependencies` and `production dep '@tailwindcss/postcss' missing from dependencies`. **GREEN** = after adding the two deps to `package.json`, creating `postcss.config.mjs`, and running `npm install` to regenerate `package-lock.json`, the full toolchain test file passes (`30 passed in 0.02s`) and the full build-pipeline test file passes (`7 passed in 3.83s`); repeatability confirmed by a second consecutive run (`7 passed in 3.83s`) with no flakiness; the compiled CSS bundle is byte-identical between the two runs (`50,891 bytes`, hash-stable under Turbopack's chunked pipeline). **TRIANGULATE** = the test pair covers both the package.json dep side (toolchain test) AND the postcss.config.mjs config side (build-pipeline test) AND the compiled-CSS artifact side (Tailwind preflight + `@theme` at-rule absence + `@import "tailwindcss"` absence + theme token expansion into `:root, :host`); a future regression that drops the dep, removes the config, or leaves the directive unprocessed in the compiled CSS is caught at the artifact level. **Visual-defect fix proof at artifact level**: on this worktree after PR 5.5, a clean `node node_modules/.bin/next build` produces `out/_next/static/chunks/391guka-hdllv.css` (50,891 bytes) that contains **204 occurrences of `--tw-`** (Tailwind utility variables — proof the plugin generated utility classes), **1 occurrence of `@keyframes spin`** (the Tailwind animation), **1 occurrence of `.animate-spin`** (a Tailwind utility class generated for the React source), **1 occurrence of `@layer theme { :root, :host { … --primary: #1d7ea9; … } }`** (the Tailwind 4 expansion of the legacy `@theme` block), **5 occurrences of `#1d7ea9`** (the legacy `:root` palette hex value, now correctly hoisted into the compiled `:root` cascade), **zero occurrences of the literal `@theme {` at-rule**, and **zero occurrences of the literal `@import "tailwindcss"` substring**. `node scripts/check-runtime.mjs` exits `0` with `[check-runtime] Node 26.8.1 >= 20.9.0 OK (engines.node = ">=20.9.0")` — the runtime guard is unaffected. `npm ci` reproduces a 121-package install with the same 18 tailwind/postcss lockfile entries (`node_modules/@tailwindcss/{node,oxide,oxide-*,postcss}` + `node_modules/postcss` + `node_modules/tailwindcss`) on a fresh clone. **Topology / count implications (accurate, append-only)**: the chain expands from **16 children to 17 children**. The new repair child is named **PR 5.5 (Tailwind 4 / PostCSS pipeline repair)** and sits at **position 5.5/17** — interpolated between **position 5/17 (PR 3c-iii, Search / Folder / global Browser styling)** and **position 7/17 (PR 3c-iv, animations / utilities + final CSS parity + design-system barrel)**. Every child that was previously at position `n/16` (for `n ∈ {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}`) is renumbered to `n+1/17` (so `6/16 → 7/17`, `7/16 → 8/17`, `8/16 → 9/17`, `9/16 → 10/17`, `10/16 → 11/17`, `11/16 → 12/17`, `12/16 → 13/17`, `13–15/16 → 14–16/17`, `16/16 → 17/17`). PR 3a stays at `1/17`, PR 3b stays at `2/17`, PR 3c-i stays at `3/17`, PR 3c-ii stays at `4/17`, PR 3c-iii stays at `5/17`. The sub-PR scope, the predecessor / successor branch mapping, the corrected ordering, the Approach A lock, the FastAPI/SQLite foundation, the Feature Branch Chain strategy, the predecessor frozen status, the per-domain specs, every prior addendum (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c, 3c-ii, 3c-iii), and the user-approved replacement G5 protocol recorded above are unchanged in their substantive content; only their position labels shift up by 1 (or stay where they are if they were before position 5). PR 5.5's **dependency position**: depends on **PR 3c-iii** (the `@theme` block + the legacy `var(--token)` consumers are in place so a working `@tailwindcss/postcss` expansion has tokens to expand and selectors to serve); **does NOT depend on PR 3c-iv** (the `@keyframes` + utilities + design-system barrel are not yet shipped, but the build pipeline repair does not need them — the preflight + `@theme` expansion + `--tw-*` utility generation are all that PR 5.5 needs to be self-contained). The new repair child itself is self-contained: it does not touch `src/app/globals.css` content (3c-i / 3c-ii / 3c-iii own that file), does not touch `tsconfig.json`, does not touch `.nvmrc`, does not touch `scripts/check-runtime.mjs`, does not touch the Makefile, does not touch `next.config.mjs`, does not touch `api/server.py`, does not touch any `src/modules/**` barrel, does not touch `web/**` (the legacy vanilla bundle), does not touch `extension/**`, and does not delete `web/*.{html,js,css}` or `tailwind.config.js` (those deletions land with PR 5c). **LoC budget**: PR 5.5's authored diff is well under the 400-line budget (1 new config file `postcss.config.mjs` ≈ 25 LoC, 1 new test file `tests/test_tailwind_build_pipeline.py` ≈ 220 LoC, 1 modified test file `tests/test_toolchain_bootstrap.py` ≈ +12 LoC delta, 1 modified `package.json` ≈ +2 LoC delta — total **≈ 259 authored LoC**, ≤ 400 with **−141 LoC headroom**). The **lockfile exception is the only size:exception PR 5.5 opens** — see the lockfile-exception paragraph below. **The 17-child chain is preserved** (the chain grew by exactly one child, in the only safe insertion point: between PR 3c-iii's `src/app/globals.css` slice and PR 3c-iv's `@keyframes` + utilities + design-system barrel slice — both of which sit downstream of the `@tailwindcss/postcss` expansion that PR 5.5 finally provides). **The fourth user-approved size:exception for the regenerated `package-lock.json` (this entry, opens a fourth lockfile size:exception alongside the existing PR 3a + PR 3c-ii + PR 3c-iii exceptions; PR 3a is generated-resolution-only and stays open as the prior documented lockfile size:exception; PR 3c-ii is an authored-LoC exception, not a lockfile exception, and stays open unchanged; PR 3c-iii is an authored-LoC exception, not a lockfile exception, and stays open unchanged; the present PR 5.5 exception is a generated-lockfile exception for the `@tailwindcss/postcss` + `postcss` resolution additions)**: the regenerated `package-lock.json` adds **16 new tailwind/postcss-related lockfile entries** (of the **18 tailwind/postcss-related lockfile entries** in the post-fix lockfile; `tailwindcss` itself predates this repair because PR 3a added it) (`node_modules/@tailwindcss/{node, oxide, oxide-android-arm64, oxide-darwin-arm64, oxide-darwin-x64, oxide-freebsd-x64, oxide-linux-arm-gnueabihf, oxide-linux-arm64-gnu, oxide-linux-arm64-musl, oxide-linux-x64-gnu, oxide-linux-x64-musl, oxide-wasm32-wasi, oxide-win32-arm64-msvc, oxide-win32-x64-msvc, postcss}` + `node_modules/postcss` + `node_modules/tailwindcss`) bringing the total `packages` object from the pre-3c-iii baseline to **121 packages** and the lockfile line count to **2,112 lines**. The lockfile change is **generated-resolution-only** (no hand-authored content); it contains **only the resolution changes required by the two new top-level deps** in `package.json` (i.e. `@tailwindcss/postcss` + `postcss`, plus the transitive `@tailwindcss/node` + `@tailwindcss/oxide*` tree that `@tailwindcss/postcss` depends on); it is reviewed together with `package.json`; it carries no unrelated lockfile churn. The two new `package.json` entries are caret-pinned (`^4.3.3` for `@tailwindcss/postcss` against the same Tailwind 4 major as `tailwindcss`, `^8.5.0` for `postcss` against the standard PostCSS 8 line) so the lockfile delta is deterministic under re-`npm install`. **Authorization rationale** (why a single reviewable PR is preferred over splitting the postcss.config.mjs away from the dep + lockfile change): (a) the PostCSS plugin registration, the two new top-level deps, and the regenerated lockfile are inseparable — without `@tailwindcss/postcss` installed, `postcss.config.mjs` cannot register it; without `postcss` as a peer dep, `@tailwindcss/postcss` cannot run; without the regenerated lockfile, `npm ci` will not reproduce the install on a fresh clone; (b) the build-pipeline regression test is inseparable from the fix (it reads the compiled CSS output that the fix produces); (c) splitting PR 5.5 further into a 5.5-a / 5.5-b pair would leave a half-broken build pipeline (deps installed but no plugin registered, OR plugin registered but no regression test) that nobody can review coherently and would still need to be re-merged at PR 5c; (d) PR 5.5's authored diff is ~259 LoC (well under the 400-line budget) so no further authored-LoC exception is needed. **G2 production-candidate evidence gap (this entry surfaces a gap the prior chain left open; PR 5.5 closes one witness but does NOT flip G2; G2 remains pending the full Phase 6 capture)**: the prior chain recorded G2 as a **PASS** carried from the predecessor (`migrate-nextjs-tailwind4/`) per `design.md::§TL;DR` and `tasks.md::Phase 1.1` (G2 = clean static-export build at `out/`). The G2 predecessor PASS was captured against the **`tools/g2-candidate/` isolated workspace** with `tools/g2-candidate/app/globals.css` containing ONLY `:root { color-scheme: light; }` + a body reset — i.e. a 4-line CSS file with no `@import "tailwindcss"`, no `@theme`, and no Tailwind dependency. **That G2 PASS does not transfer to the production repo**, because the production repo's `src/app/globals.css` (post-PR-3c-iii) ships the canonical `@import "tailwindcss";` + `@theme { … }` surface that the `@tailwindcss/postcss` plugin must process, and the prior chain never registered that plugin. Concretely: a clean `next build` against the pre-PR-5.5 repo produces a `out/_next/static/chunks/391guka-hdllv.css` of **35,093 bytes** with the `@theme { … }` block as a literal at-rule and zero Tailwind preflight — the artifact the FastAPI `StaticFiles` mount serves at `127.0.0.1:8765/_next/static/chunks/391guka-hdllv.css` is the production-candidate G2 evidence; that evidence was BROKEN before PR 5.5 and is now COMPLETE after PR 5.5 (the bundle is **50,891 bytes** with the `@theme` block expanded into `@layer theme { :root, :host { … } }` and the Tailwind preflight present). **PR 5.5 closes the BUILD-PIPELINE half of the G2 production-candidate evidence gap** by adding the artifact-level regression test `tests/test_tailwind_build_pipeline.py` (which performs a real `next build` and asserts on the compiled CSS); the BROWSER half of the G2 gap (a real Chromium / Playwright capture against `127.0.0.1:8765` proving every `var(--token)` reference resolves and the Tailwind preflight takes effect at runtime) **remains deferred to the Phase 6a validation work** and is NOT claimed by this addendum. G2 production-candidate remains **PASS-pending-Phase-6-capture**, NOT flipped by PR 5.5 alone. **What PR 5.5 explicitly does NOT claim**: (i) PR is NOT claimed merged into the tracker (`docs/complete-taxa-frontend-migration-plan`) or into `develop` — this addendum documents the worktree's authored state only; (ii) PR is NOT claimed CI-green on the full repo test suite — the 31 pre-existing failures in `tests/test_tailwind_4_{parity,base_resets,utilities}.py` + the 52 pre-existing failures in `tests/test_tailwind_tokens_base.py` (all of which are PR 3c-iv-deferred surfaces — `--color-*` Tailwind 4 utility namespace aliases, `@keyframes spin` + `.animate-spin` in `@layer base`, byte-size budget against the yet-to-land 3c-iv PR) are documented pre-existing failures, unchanged by PR 5.5, and the regression test for them lands with PR 3c-iv per the prior addendum; (iii) PR is NOT claimed browser-verified (no real Chromium / Playwright capture against `127.0.0.1:8765`); (iv) PR is NOT claimed G2-PASS (G2 remains PASS-pending-Phase-6-capture, see above); (v) PR does NOT enable `gentle-ai review mode` and does NOT open a PR — review / CI / merge follow the ordinary feature-branch-chain process once the user-authorized parent task completes. **Spanish mirror** (`documents-es/openspec/changes/complete-taxa-frontend-migration/tasks-es.md`) carries the same semantics; any drift is resolved in favour of the English.
