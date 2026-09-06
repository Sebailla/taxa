# Apply Progress: complete-taxa-frontend-migration

> Hybrid-mode persistence artifact. Mirrors the structured
> apply-progress in Engram (`topic_key` =
> `sdd/complete-taxa-frontend-migration/apply-progress`).
>
> **Initial state (2026-09-02)**: every sub-PR under Approach A
> (`tasks.md` Phases 3a–6c + PR 3e) is **reconstruction pending**.
> No child PR has been opened yet. The tracker branch
> `docs/complete-taxa-frontend-migration-plan` already exists and
> holds the planning artifacts; it is the **only** branch that
> will target `develop`, and it stays **draft / no-merge** until
> the whole chain is reviewed and integrated. Nothing has been
> delivered to `develop` yet. The pre-flight gate table
> (§Pre-flight gate for PR 3e) records the carried status of
> G1, G2, G3 Tier-1 (all PASS recorded from the predecessor)
> and the closure status of G4, G5, G6 (all three deferred to
> Phase 6 validation work).
>
> **Approach A is FINAL** (locked 2026-09-02, recorded in
> `design.md::§1`); no override path is open. **Predecessor
> `migrate-nextjs-tailwind4/` is frozen** — every sub-PR in this
> change MUST leave `openspec/changes/migrate-nextjs-tailwind4/**`
> byte-identical (branch-protection rejects any PR that edits
> it).
>
> **2026-09-02 — corrective plan revision**: the
> reconstruction table below, the chain topology table, and the
> per-sub-PR scope were reordered and rescoped after the apply
> gate identified a dependency-order defect (PR 3a required
> `next build`/`out/index.html` before the Next/React/Tailwind/
> TypeScript toolchain and Node runtime contract existed; those
> landed in original PR 3c, AFTER original PR 3a). The
> corrected topology introduces a **toolchain bootstrap PR at
> position 1**, demotes the **App Router static export** to
> position 2 (now satisfiable because the toolchain exists),
> keeps Tailwind/tokens at position 3, fuses the Makefile
> rewrite with the `WEB_DIR` repoint + AC-21 at position 4,
> and follows with state, ports, e2e, validation, and the
> atomic cutover. The 13-child count is preserved.

---

## Reconstruction State

> **Reordering rationale (corrective plan revision)**.
> Original Phase 3a was unsatisfiable because its
> `next build` witness required the toolchain that original
> Phase 3c shipped AFTER it. The corrected topology reverses
> the dependency: the **toolchain bootstrap** lands first
> (position 1), the **App Router static export** second
> (position 2, witness now satisfiable). Original Phase 3b's
> Tailwind/tokens work moves to position 3 (depends on
> Tailwind installed in position 1). Original Phase 3c's
> `Makefile::api` rewrite merges with original Phase 3d's
> `WEB_DIR` repoint + AC-21 reader into a single sub-PR at
> **position 4** (depends on `next build` producing `out/` via
> the `Makefile::api` recipe; the position-1 Node runtime
> contract is invoked from the Makefile). Positions 5–13
> (4a through 3e) keep their predecessor task numbering and
> scope. **The 13-child count is preserved.**
>
> **2026-09-02 — CSS re-split**: the apply gate's pre-flight
> re-audit identified that the previous PR 3c (position
> 3/13), as scoped at the dependency-defect-fix revision,
> was **unsatisfiable** — it was tasked with migrating the
> legacy `web/index.html` inline `<style>` block of
> **1,963 lines** in a single sub-PR while staying under
> the 400-line per-PR review budget; the migration cannot
> fit. The CSS portion is therefore **re-split into four
> chained children** (PR 3c-a / PR 3c-b / PR 3c-c / PR
> 3c-d), each ≤ 400 author lines and partitioned by
> concern: tokens / base / dark mode; tree + inline
> Overview styles; Search / Folder / global Browser
> styles; animations / utilities + final parity. The
> previous single PR 3c's scope is partitioned across the
> four children with no duplicate production code; the
> legacy `<style>` block is retired at PR 5c (the legacy
> `web/index.html` deletion); the four children author new
> code into `src/app/globals.css` without touching the
> legacy file directly. Tracker **PR #146** is the merged
> starting point for the first new CSS child (PR 3c-a).
> Every later child shifts position by +3 to accommodate
> the four CSS children (3d 4→7; 4a 5→8; 4b 6→9; 5a 7→10;
> 5b 8→11; 5c 9→12; 6a 10→13; 6b 11→14; 6c 12→15; 3e
> 13→16). Semantic labels (3a, 3b, 3c-a, 3c-b, 3c-c, 3c-d,
> 3d, 4a, 4b, 5a, 5b, 5c, 6a, 6b, 6c, 3e) are preserved;
> only the position counter (NN in
> `feat/complete-taxa-frontend-migration-NN-XXX`) and
> base-branch references change. **The 16-child count**
> replaces the previous 13-child count. Per-sub-PR LoC
> budgets stay well under the 400-line review budget;
> **only the prior PR 3a `package-lock.json` exception
> remains**.

> **2026-09-03 — PR 3c-d re-split supersession (PR #150
> task replan is authoritative; this document's 16-child
> table still reflects the pre-#150 CSS re-split only)**.
> PR #150 (`tasks.md` / `tasks-es.md` "3c-d
> unsatisfiability split") re-plans the previous
> monolithic PR 3c-d (animations / utilities + final
> parity) into three sequential children, each ≤ 400
> authored lines. The reconstruction manifest above
> remains the **pre-#150 view**; the **authoritative
> re-split lives in `tasks.md` / `tasks-es.md`**, which
> the apply phase reads. The new partition:
>
> - **PR 3c-d (6/18; narrowed, stays at 6/18)** —
>   base / reset / global state affordances. Extends
>   `globals.css::@layer base` with the **global state
>   affordances only**: `@keyframes` (`spin`), the
>   **global `@layer base` `color-mix()` selectors**,
>   `body { overscroll-behavior: none; … }`, and
>   `main > :first-child { margin-top: 0 !important; }`.
>   **No utility classes, no parity test.** Allowed
>   production: `src/app/globals.css`; allowed test:
>   `tests/test_tailwind_4_base_resets.py`.
> - **PR 3c-e (7/18; new)** — utility-class + remaining
>   animation parity. Extends `globals.css::@layer
>   base` with the utility-class surface **plus any
>   remaining `@keyframes` / `color-mix()`**
>   (component-scoped color-mix, utility-paired
>   rules) — the global `@layer base` state
>   affordances stay in 3c-d. **No parity test.**
>   Allowed production: `src/app/globals.css`;
>   allowed test: `tests/test_tailwind_4_utilities.py`.
> - **PR 3c-f (8/18; new; sole full-parity test
>   only)** — **no new `globals.css` code**. Final
>   parametrized parity test
>   `tests/test_tailwind_4_parity.py` consolidates the
>   five prior focused tests (3c-a tokens / 3c-b
>   taxonomy / 3c-c research / 3c-d base-resets /
>   3c-e utilities). The final parity contract is
>   unchanged; it belongs only to PR 3c-f.
>
> Renumbering: 3d 7→**9/18**; 4a 8→**10/18**;
> 4b 9→**11/18**; 5a 10→**12/18**; 5b 11→**13/18**;
> 5c 12→**14/18**; 6a (G5) 13→**15/18**;
> 6b (G6) 14→**16/18**; 6c (G4) 15→**17/18**;
> 3e 16→**18/18**. **3c-d stays at 6/18** (narrowed,
> same branch). New branches: `…-07-3c-e` (base
> `…-06-3c-d`), `…-08-3c-f` (base `…-07-3c-e`).
> **18-child count** replaces 16;
> `feature-branch-chain` strategy and the
> "tracker-only targets `develop`" contract hold.
> Per-sub-PR LoC budgets stay well under 400; only the
> prior PR 3a `package-lock.json` exception remains.
> **G4 / G5 / G6 (now 17/18 / 15/18 / 16/18), the
> frozen predecessor, Approach A, FastAPI/SQLite, and
> the per-domain specs stay unchanged**. Merged PRs
> 3c-a/#147, 3c-b/#148, 3c-c/#149 preserved. The five
> CSS children (3c-a / 3c-b / 3c-c / 3c-d / 3c-e) plus
> PR 3c-f cannot collapse without violating the
> 400-line per-PR review budget. **Documentation-only
> supersession note**: no source-code edit, no rebase,
> no new branch creation in this revision; the next
> code worktree picks up the authoritative scope from
> `tasks.md`.

| Sub-PR | Scope | LoC budget (authored) | Source files | Status |
|--------|-------|-----------------------|--------------|--------|
| PR 3a | **Toolchain bootstrap** (NEW position 1) | ~210 authored; user-approved generated-lockfile exception | `package.json` + regenerated `package-lock.json` (the exception is restricted to resolution changes required by this manifest, and both are reviewed together; `next@^16` / `react@^19` / `react-dom@^19` / `tailwindcss@^4` / TS toolchain / `engines.node ">=20.9.0"` / `scripts.check-runtime` / `scripts.build:web`; legacy Tailwind 3.4 deps removed) + `scripts/check-runtime.mjs` (new, Node ≥ 20.9.0 enforcement) + `tsconfig.json` (modified in place; the predecessor already exists at repo root; base config + `@taxa/<capability>` path aliases) + `.nvmrc` (new, pin `20`) + `tests/test_toolchain_bootstrap.py` (new) + `tests/test_check_runtime.py` (new) | reconstruction pending |
| PR 3b | **App Router static-export bootstrap (self-contained)** (position 2; the dependency-defect fix rescopes the original 3a-style App Router entry into a self-contained bootstrap that does NOT import `@taxa/app-shell` or `./globals.css`) | ~150 | `src/app/{layout,page}.tsx` (new, **minimal semantic placeholder body**; **no AppShell mount, no globals.css import**) + `next.config.mjs` (new, `output: "export"` + `images.unoptimized: true` + `trailingSlash: false` + `reactStrictMode: true`) + `tests/test_app_shell_render.py` (new, reads `out/index.html` after `npx next build`; asserts viewport meta + Raleway preload + Raleway `.woff2` file in `out/_next/static/media/`) | reconstruction pending |
| PR 3c-a | **Tokens / base / dark mode** (NEW position 3; the first new CSS child of the CSS re-split; the dependency-defect fix moves the `import "./globals.css";` line into this sub-PR; the previous single PR 3c's scope is partitioned across 3c-a / 3c-b / 3c-c / 3c-d) | ~400 | `src/app/globals.css` (new, initial scaffold: `@import "tailwindcss"` + `@theme` mirroring every legacy `:root` / `[data-theme="dark"]` / `--realm-*` token + empty `@layer base` placeholder for later children) + `src/app/layout.tsx` (modified, 1-line delta: adds `import "./globals.css";`) + `src/modules/design-system/{infrastructure/index.ts,presentation/Icon.tsx,presentation/Button.tsx}` (new) + `tests/test_tailwind_4_tokens.py` (new; enumerates legacy `:root` / `[data-theme="dark"]` / `--realm-*` tokens against `globals.css::@theme`) + `tests/test_design_system_purity.py` (new) | reconstruction pending |
| PR 3c-b | **Tree + inline Overview styles** (NEW position 4; the second new CSS child; depends on the `globals.css` scaffold + `@layer base` placeholder from 3c-a) | ~400 | `src/app/globals.css` (extended, `@layer components` block with taxonomy selectors: `.taxa-tree`, `.tree-row`, `.kebab`, `.kebab-menu`, `.tree-search-icon`, `.materialize-indicator`, `.detail-panel`, `.tab-strip`, `.tab-button`, `.overview-tab`, `.breadcrumb`) + `tests/test_taxonomy_styles.py` (new; enumerates taxonomy `@layer components` selectors against `globals.css`) | reconstruction pending |
| PR 3c-c | **Search / Folder / global Browser styles** (NEW position 5; the third new CSS child; depends on the taxonomy `@layer components` block from 3c-b) | ~400 | `src/app/globals.css` (extended, `@layer components` block with research / chrome selectors: `.search-tab`, `.search-category-section`, `.search-link-list`, `.search-link`, `.folder-tab`, `.header-browser-tab`, `.research-explorer`, `.file-explorer-pane`, `.file-viewer-pane`) + `tests/test_research_styles.py` (new; enumerates research / chrome `@layer components` selectors against `globals.css`) | reconstruction pending |
| PR 3c-d | **Animations / utilities + final parity** (NEW position 6; the fourth and last new CSS child; depends on the research / chrome `@layer components` block from 3c-c; ships the consolidated `tests/test_tailwind_4_parity.py` final parity test) | ~300 | `src/app/globals.css` (extended, `@layer base` block with `@keyframes` (`spin`), `color-mix()` selectors, utility-class surface (`bg-primary`, `text-on-surface`, `border-outline-variant`, `bg-surface-container-lowest`, `shadow-sm`, `rounded-r-md`, `bg-primary-fixed`, `text-on-primary-fixed`, …), `body { overscroll-behavior: none; … }` rule, `main > :first-child { margin-top: 0 !important; }` reset — all in source order) + `tests/test_tailwind_4_parity.py` (new; consolidated parametrized final parity test) | reconstruction pending |
| PR 3d | **Makefile/mount** (NEW position 7; fuses original 3c + 3d; depends on `next build` from 3b + Tailwind 4 tokens + `@layer base` + `@layer components` from 3c-d) | ~240 | `Makefile` (modified, `api:` target runs `check-runtime.mjs` → `npm ci` → `npm run build:web` → `uvicorn … --port 8765`; `make css` becomes no-op shim) + `api/server.py` (modified, 1-line delta at line 54, `WEB_DIR = Path(__file__).parent.parent / "out"`) + `src/data/search-engines.js` (new, byte copy of `web/search_urls.js` with `SEARCH_ENGINES` named export) + `tests/test_smoke.py` (modified, `open()` path update) + `tests/test_static_mount.py` (new) + `tests/test_make_api_build.py` (new) | reconstruction pending |
| PR 4a | Typed store + 4 read + 4 write (unchanged) | ~180 | `src/modules/browser-state/{domain/keys.ts,infrastructure/store.ts,index.ts}` (new) + `tests/test_browser_state_keys.py` (new) | reconstruction pending |
| PR 4b | Hydration guard + AppShell integration + Playwright zero-warnings (the dependency-defect fix moves the `<AppShell>` integration into `src/app/{layout,page}.tsx` into this sub-PR) | ~120 | `src/modules/app-shell/{presentation/AppShell.tsx,infrastructure/page-chrome.tsx}` (new) + `src/app/{layout,page}.tsx` (modified, integrates `<AppShell>` from `@taxa/app-shell` into the App Router host; the dependency-defect fix) + `tests/test_hydration_console.py` (new, Playwright) | reconstruction pending |
| PR 5a | Taxonomy module port (extended; absorbs DetailPanel tab strip + OverviewTab + Kebab Search-online force) | ~310 | `src/modules/taxonomy/{domain/taxon.ts,infrastructure/api.ts,application/useTaxonTree.ts,presentation/{Tree,DetailPanel,OverviewTab,Kebab,Breadcrumb}.tsx}` (new + extension; `DetailPanel` ships the three-tab strip `Overview` / `Search` / `Folder` per the verified UI surface, with `Overview` always available/visible; the taxonomy presentation layer rides on PR 3c-b's `@layer components` selectors) + `tests/test_taxonomy_infra.py` (new; includes the `Search online` → `Search` tab Playwright regression witness) | reconstruction pending |
| PR 5b | Research module port + CDN pin (extended; absorbs SearchTab + FolderTab + SearchLinkList + header `Browser` tab re-anchoring as global Research) | ~395 | `src/modules/research/{domain/{research-file,engine,file-node}.ts,infrastructure/{api,search-engines}.{ts,js},application/{useFileExplorer,useFileViewer}.ts,presentation/{FileExplorer,FileViewer,RawTableTreeTabs,MetaStrip,BreadcrumbPanel,Banners,SearchLinkList,SearchTab,FolderTab}.tsx}` (new; `SearchTab` renders the five category sections `General` / `Taxonomic` / `Academic` / `Multimedia` / `Documents` in fixed order; `FolderTab` is a separate body; `SearchLinkList` maps each `Engine` to an anchor with `target="_blank"` + `rel="noopener noreferrer"`; the research presentation layer rides on PR 3c-c's `@layer components` selectors) + `src/modules/app-shell/infrastructure/page-chrome.tsx` (modified; header `Browser` tab re-anchored as global Research / file explorer, NOT taxon-scoped) + `tests/test_research_infra.py` (new; includes the categorized outbound-link list triangulation and the global-Browser witness) | reconstruction pending |
| PR 5c | E2E selectors + `data-*` contract + delete legacy (extended; depends on PR 5b + PR 3c-d; the legacy `web/index.html` deletion retires the 1,963-line legacy inline CSS the four CSS children migrated into `src/app/globals.css`) | ~200 | `tests/test_e2e_file_explorer.py` (modified, DOM selector update) + `tests/test_web_toggle.py` (modified, theme toggle update) + `tests/test_evidence_baseline.py` (modified, legacy roster assertion flips to "absent") + `web/{index.html,index.css}` deletion + `web/{app,state,api,tree,breadcrumb,detail,nav,dom,banner,help,keymap,settings,search,file_explorer,file_viewer,format,search_urls}.js` deletion (18 files) + `tailwind.config.js` deletion + `web/dist/tailwind.css` no longer tracked | reconstruction pending |
| Phase 6a | G5 hydration baseline closure (unchanged) | ~50 (mostly measurement) | `scripts/reconstruct_hydration_baseline.py` (new) + `scripts/g5_close.sh` (new) + `web/dist/evidence-baseline.json` (regenerated, schema-pinned by `tests/test_hydration_timing.py`) + `apply-progress.md` §Change log delta | reconstruction pending (validation work after candidate path) |
| Phase 6b | G6 cutover rehearsal (unchanged) | ~120 | `scripts/rehearse_cutover.py` (new) + `tests/test_rehearse_cutover.py` (new) + `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json` (working copy; predecessor copy stays byte-identical frozen) + `apply-progress.md` §Change log delta | reconstruction pending (validation work after candidate path) |
| Phase 6c | G4 Playwright + Lighthouse parity (unchanged) | ~20 (mostly measurement) | `scripts/g4_measure.sh` (new) + `out/g4-parity-report.json` (Playwright + Lighthouse artifact) + `apply-progress.md` §Change log delta | reconstruction pending (validation work after candidate path) |
| PR 3e | Atomic cutover (unchanged) | ~120 (mostly `apply-progress.md` delta) | `apply-progress.md` (gate-status footer flip + change-log entry) + re-runs of `tests/test_verify_consumers.py`, `tests/test_verify_build.py`, `make api`, `make smoke` | reconstruction pending (gated on all six gates green) |

**Sub-PR count**: **16** (1 toolchain bootstrap + 1 App Router
static export + **4 CSS children (3c-a / 3c-b / 3c-c / 3c-d)**
+ 1 Makefile/mount + 2 browser-state + 2 capability ports +
1 e2e + delete legacy + 3 Phase 6 validation + 1 atomic
cutover).

**Total authored**: ~3,615 LoC across the 16 sub-PRs (Δ
~+1,333 LoC from the previous ~2,282 forecast; the CSS
re-split partitions the 1,963-line legacy inline CSS
migration into 4 children totaling ~1,500 authored lines
(replacing the previous single PR 3c's ~232 LoC) and
adds 4 separate triangulation tests; the dependency-
defect fix reshuffles ~30 LoC between PR 3b (-25), PR
3c-a (+2), and PR 4b (+30) without changing the chain
topology). Largest sub-PRs are the **four CSS children
3c-a / 3c-b / 3c-c** at ≤ 400 LoC each (right at the
400-line per-PR review budget with 0 LoC headroom on
the tightest child); **5b** is at ~395 LoC (-5 LoC
headroom). PR 3d is at ~240 LoC (-160 LoC / -40 %
headroom against the 400-line budget). The sole
`size:exception` is user-approved for PR 3a's regenerated
`package-lock.json`; its authored work remains ≤400 and
unrelated lockfile churn is rejected. The legacy
`web/index.html` deletion at PR 5c retires the
1,963-line legacy inline CSS the four CSS children
migrated into `src/app/globals.css`.

### Reconstruction order (deterministic, sequential along the chain)

```
3a (toolchain bootstrap) →
3b (App Router static export) →
3c-a (tokens / base / dark mode) →
3c-b (tree + inline Overview styles) →
3c-c (Search / Folder / global Browser styles) →
3c-d (animations / utilities + final parity) →
3d (Makefile/mount) →
4a → 4b → 5a → 5b → 5c →
6a (G5) → 6b (G6) → 6c (G4 measurement) →
3e (atomic cutover, gated)
```

**Chain strategy: `feature-branch-chain`** (user-selected).
The existing `docs/complete-taxa-frontend-migration-plan`
branch (referenced as **PR #146**) is the **tracker**:
draft / no-merge, and the **only** PR that targets
`develop`. Child PR 3a targets the tracker; every later
child targets its **immediate predecessor branch**. The
first new CSS child (PR 3c-a) treats the tracker PR #146
as the merged starting point for the four-child CSS
re-split. This supersedes the `AGENTS.md` §4
direct-to-`develop` default for this change.

| Position | Sub-PR | Branch | Base (PR target) |
|---|---|---|---|
| Tracker | — | `docs/complete-taxa-frontend-migration-plan` (PR #146) | `develop` — **draft / no-merge** |
| 1 / 16 | 3a | `feat/complete-taxa-frontend-migration-01-3a` | `docs/complete-taxa-frontend-migration-plan` (tracker) |
| 2 / 16 | 3b | `feat/complete-taxa-frontend-migration-02-3b` | `feat/complete-taxa-frontend-migration-01-3a` |
| 3 / 16 | 3c-a | `feat/complete-taxa-frontend-migration-03-3c-a` | `feat/complete-taxa-frontend-migration-02-3b` |
| 4 / 16 | 3c-b | `feat/complete-taxa-frontend-migration-04-3c-b` | `feat/complete-taxa-frontend-migration-03-3c-a` |
| 5 / 16 | 3c-c | `feat/complete-taxa-frontend-migration-05-3c-c` | `feat/complete-taxa-frontend-migration-04-3c-b` |
| 6 / 16 | 3c-d | `feat/complete-taxa-frontend-migration-06-3c-d` | `feat/complete-taxa-frontend-migration-05-3c-c` |
| 7 / 16 | 3d | `feat/complete-taxa-frontend-migration-07-3d` | `feat/complete-taxa-frontend-migration-06-3c-d` |
| 8 / 16 | 4a | `feat/complete-taxa-frontend-migration-08-4a` | `feat/complete-taxa-frontend-migration-07-3d` |
| 9 / 16 | 4b | `feat/complete-taxa-frontend-migration-09-4b` | `feat/complete-taxa-frontend-migration-08-4a` |
| 10 / 16 | 5a | `feat/complete-taxa-frontend-migration-10-5a` | `feat/complete-taxa-frontend-migration-09-4b` |
| 11 / 16 | 5b | `feat/complete-taxa-frontend-migration-11-5b` | `feat/complete-taxa-frontend-migration-10-5a` |
| 12 / 16 | 5c | `feat/complete-taxa-frontend-migration-12-5c` | `feat/complete-taxa-frontend-migration-11-5b` |
| 13 / 16 | 6a | `feat/complete-taxa-frontend-migration-13-6a` | `feat/complete-taxa-frontend-migration-12-5c` |
| 14 / 16 | 6b | `feat/complete-taxa-frontend-migration-14-6b` | `feat/complete-taxa-frontend-migration-13-6a` |
| 15 / 16 | 6c | `feat/complete-taxa-frontend-migration-15-6c` | `feat/complete-taxa-frontend-migration-14-6b` |
| 16 / 16 | 3e | `feat/complete-taxa-frontend-migration-16-3e` | `feat/complete-taxa-frontend-migration-15-6c` |

Children merge **in order** into the tracker; as each child
merges, the next is retargeted onto the tracker (GitHub
retargets automatically when the base branch is merged and
deleted). The tracker accumulates the full feature and merges
to `develop` only after PR 3e — the last child — lands.

**Per-sub-PR dependency (corrective plan revision + dependency-defect fix + CSS re-split contract)**:

| Position | Depends on | Satisfies (witness) |
|---|---|---|
| 1 / 3a (toolchain bootstrap) | — | `npm ci` exit 0; `node scripts/check-runtime.mjs` exit 0 on Node ≥ 20.9.0; `npx tsc --noEmit` resolves all `@taxa/*` aliases |
| 2 / 3b (App Router static export) | 1 | `npx next build` exit 0; `out/index.html` non-empty with viewport meta + Raleway preload |
| 3 / 3c-a (tokens / base / dark mode) | 1 + 2 | `src/app/globals.css::@theme` carries every legacy `:root` / `[data-theme="dark"]` / `--realm-*` token; `import "./globals.css";` integration in `src/app/layout.tsx`; design-system barrel exported |
| 4 / 3c-b (tree + inline Overview styles) | 3 | `globals.css::@layer components` carries taxonomy selectors (`.taxa-tree`, `.tree-row`, `.kebab`, `.detail-panel`, `.tab-strip`, `.overview-tab`, `.breadcrumb`, …) |
| 5 / 3c-c (Search / Folder / global Browser styles) | 4 | `globals.css::@layer components` carries research / chrome selectors (`.search-tab`, `.search-link`, `.folder-tab`, `.header-browser-tab`, `.research-explorer`, …) |
| 6 / 3c-d (animations / utilities + final parity) | 5 | `globals.css::@layer base` carries `@keyframes` (`spin`), `color-mix()` selectors, utility-class surface, body reset, first-child reset; `tests/test_tailwind_4_parity.py` final parity test enumerates the 1,963-line legacy inline CSS end-to-end |
| 7 / 3d (Makefile/mount) | 2 + 6 | `make api` exit 0; uvicorn binds only `127.0.0.1:8765`; `curl /index.html` returns `out/index.html`; AC-21 contract preserved |
| 8 / 4a (typed store) | 3 | 4 read + 4 write sites in `src/modules/browser-state/`; no other module touches `localStorage` |
| 9 / 4b (hydration guard + AppShell integration) | 8 + 2 + 3 | Playwright zero-hydration-warnings; `AppShell` integrated into `src/app/{layout,page}.tsx`; the dependency-defect fix and the design-system barrel from PR 3c-a are live |
| 10 / 5a (taxonomy port) | 9 + 4 | Taxonomy view-models render; tree-source toggle rehydrates via `localStorage`; the taxonomy presentation layer rides on PR 3c-b's `@layer components` selectors |
| 11 / 5b (research port + CDN pin) | 10 + 7 + 5 | Research files render via 9-format dispatcher; CDN URLs pinned; the research presentation layer rides on PR 3c-c's `@layer components` selectors |
| 12 / 5c (e2e + delete legacy) | 11 + 6 | E2E selectors updated; `data-*` contract preserved; legacy `web/*` deleted (the `web/index.html` deletion retires the 1,963-line legacy inline CSS the four CSS children migrated into `src/app/globals.css`) |
| 13–15 / 6a, 6b, 6c (validation) | 12 | G5 reproducible; G6 PASS; G4 PASS; `apply-progress.md` §Change log flips for each |
| 16 / 3e (atomic cutover) | 13, 14, 15 + G1/G2/G3 Tier-1 carried | All six gates green; cutover-manifest Tier-2 flip; uvicorn serves `out/index.html` from production build |

**Phase 6 (6a, 6b, 6c) is validation work**, not a migration
objective. It runs **after** the complete candidate path
(positions 1–9) is green and accumulated on the tracker, and
**before** PR 3e can land. Phase 6 may ship as three chain
links (the default: positions 10 / 11 / 12) or collapse into
a single child PR at position 10, depending on the
maintainer's `ask-on-risk` decision; collapsing shortens the
chain without changing the topology (the batch still targets
the PR 5c branch, and PR 3e still targets the last Phase 6
link). The combined LoC is ~190 authored + ~120 measurement
artifact, comfortably under the 400-line budget.

### Worktree policy

- **CodeGraph-aware placement**: every worktree spawned for a
  sub-PR sits under
  `<repo-parent>/<repo-name>-worktrees/<worktree-name>` (the
  user's home, sibling of the active worktree, never under
  `/tmp` / `/var/tmp`). Each worktree gets its own `.codegraph/`
  index; the CodeGraph watcher auto-syncs after edits.
- **Predecessor worktree is read-only**:
  `taxa-worktrees/migrate-nextjs-tailwind4-pr1` (if it exists)
  is planning history only. Do not edit, rebase, or merge from
  it.
- **Reconstruction worktrees** spawned by the apply worker for
  each sub-PR: created fresh from that sub-PR's **base branch**
  in the chain table above — the tracker
  (`docs/complete-taxa-frontend-migration-plan`) for PR 3a, the
  immediate predecessor branch for every later child. Never
  from `origin/develop` directly: a worktree cut from `develop`
  produces a polluted diff. Name pattern:
  `taxa-worktrees/complete-taxa-frontend-migration-<sub-pr-id>`.

### Reconstruction manifest (per sub-PR)

For each sub-PR, the apply worker MUST:

1. Create a new worktree from that sub-PR's **base branch**
   (see the chain table in §Reconstruction order — the tracker
   for PR 3a, the immediate predecessor branch for every later
   child), named
   `taxa-worktrees/complete-taxa-frontend-migration-<sub-pr-id>`.
2. Copy only the files listed for that sub-PR in `tasks.md`
   §Per-task evidence (`Source files` column above) into the
   new worktree using `cp -p`. No edits on copy.
3. Run the focused test command (see the per-sub-PR task rows
   in `tasks.md` §"Per-task evidence"). It MUST pass before
   any commit.
4. Run the runtime harness (see same table). It MUST exit 0 /
   return the expected output.
5. Conventional Commit with English subject (no AI trailer).
   PR body in Spanish per `AGENTS.md` §Hard Rules: `## Resumen`,
   `## Cambios`, `## Validación`, `## Lo que NO cambió`.
6. Open the PR against that sub-PR's **base branch** (never
   `develop`) via the `branch-pr` skill. Append a
   `## Chain Context` section (Chain / Tracker PR / Position /
   Base / Depends on / Follow-up / Review budget / Starts at /
   Ends with) plus a dependency diagram marking the current
   PR with `📍`. The Chain Context section is **appended** to
   the repo PR template — it does not replace `## Resumen` /
   `## Cambios` / `## Validación` / `## Lo que NO cambió`.
7. Verify chain diff hygiene:
   `git diff --stat <base-branch>` shows **only** this slice's
   files. A polluted diff is a **base bug** — retarget or
   rebase onto the correct predecessor before review.
8. On green CI: mark that sub-PR's tasks `[x]` in `tasks.md`
   and `tasks-es.md`; prepend a per-sub-PR batch record here
   and in `apply-progress-es.md` (see §Change log below).
9. Merge the child into the tracker, then continue to the
   next sub-PR by repeating from step 1 with a fresh worktree
   off the now-merged predecessor. Keep the tracker PR
   **draft / no-merge** until all 13 children are reviewed and
   integrated.

### Rollback boundary per sub-PR

Each sub-PR revert removes **only** its own files (see the
`Source files` column above and the per-task `Rollback
boundary` cell in `tasks.md`). No sub-PR touches
`api/server.py` route handlers, the SQLite/WAL logic, the
ETL pipeline, or `extension/manifest.json`. The
`api/server.py:54` `WEB_DIR` repoint lives in PR 3d (atomic
with the rest of the cutover's 4-set release per `design.md`
§"Atomic cutover unit"); its rollback boundary is **PR 3e**,
not PR 3d alone — PR 3d ships the repoint, PR 3e is the
cutover commit that flips the build artifact under `out/`.
`git revert <pr3e-sha>` is the only supported full-cutover
rollback.

**Rollback under the chain** — two windows:

| Window | State | Rollback |
|---|---|---|
| Before the tracker merges | Nothing is on `develop`; the chain lives only on the tracker branch | Hold or close the tracker PR — `develop` is untouched by construction |
| After the tracker merges | The whole chain lands on `develop` in one integration | `git revert <pr3e-sha>` restores the legacy vanilla build atomically (per `design.md` §"Rollback unit") |

For `<pr3e-sha>` to stay addressable on `develop`, the tracker
MUST merge with a **merge commit** (no squash), so the chain's
individual commits survive integration. If the tracker is
squash-merged instead, the atomic rollback unit becomes the
tracker merge itself: `git revert -m 1 <tracker-merge-sha>`.
Either way the rollback is **one** revert covering the full
four-set cutover — **no subset revert is supported**.

---

## Change log

Apply phase populates this section per-sub-PR. Each entry
records the sub-PR id, the commit hash, the gate flips (if
any), and any size:exception rationale (none expected; the
largest sub-PR is 5b at ~360 LoC, under 400-line budget).

### 2026-09-02 — Initial planning state

- `tasks.md` and `tasks-es.md` authored (this change);
  `proposal.md` / `spec.md` / `design.md` carried verbatim
  from predecessor.
- `apply-progress.md` and `apply-progress-es.md` initialised
  with the reconstruction state table above; all sub-PRs
  marked **reconstruction pending**.
- G1 PASS recorded (predecessor `design.md::§1`).
- G2 PASS recorded (predecessor `apply-progress.md`
  2026-08-30 entry against Next 16.3.3 / Turbopack clean
  build).
- G3 Tier-1 PASS recorded (predecessor `apply-progress.md`,
  PR #109 + #111 + #115 + #116, all 26 §3.1 consumers green
  via `scripts/verify_consumers.py`).
- G4 / G5 / G6 closure deferred to Phase 6 (validation work
  after the candidate path).

### 2026-09-02 — Corrective plan revision (this entry)

- **Defect identified by the apply gate**: original PR 3a
  required `next build`/`out/index.html` before the
  Next/React/Tailwind/TypeScript toolchain and Node ≥ 20.9.0
  runtime contract existed (those landed in original PR 3c).
- **Corrective reordering + rescoping applied**: position 1
  is now a **toolchain bootstrap** (absorbs `package.json`
  dep pins and `scripts/check-runtime.mjs` from original
  PR 3c); position 2 is now the **App Router static export**
  (witness satisfiable because the toolchain is live);
  position 3 stays **Tailwind/tokens** (depends on Tailwind
  installed in position 1); position 4 fuses original PR 3c's
  `Makefile::api` rewrite with original PR 3d's `WEB_DIR`
  repoint + AC-21 reader into a single **Makefile/mount**
  sub-PR at ~240 LoC authored (well under 400). Positions
  5–13 (4a through 3e) keep their predecessor task
  numbering and scope.
- **13-child count preserved**: the new chain topology has
  13 child PRs + 1 tracker, identical to the original.
- **Total authored**: ~2,245 LoC (up from ~2,225 — ≤ 50 LoC
  delta from the new test wiring split). Largest sub-PR is
  5b at ~360 LoC (under 400, no `size:exception`).
- **Approach A, FastAPI/SQLite, frozen predecessor remain
  unchanged**.
- **`tasks.md`, `apply-progress.md`, and the Spanish mirrors
  re-authored with the reordered chain**; design table
  updated.
- No code committed, pushed, or applied. The apply worker
  reads this corrected plan when the next PR window opens.

### 2026-09-02 — UI surface & tab-structure corrective revision (this entry)

- **Source**: live browser inspection of
  `http://127.0.0.1:8765/`. Verified current behavior
  diverges from the per-domain spec narrative in two
  ways that this entry corrects at the SDD level (per-
  domain specs are out of scope for this revision;
  high-level design/spec/tasks/apply-progress and the
  faithful Spanish mirrors are updated).
- **Verified UI surface (binding)**:
  - Main surface: taxonomic tree (rows render
    `rank / name / source / species-count` plus per-row
    kebab).
  - Selecting any node — including top-level domains
    such as `Archaea` — opens an **inline contextual
    detail panel** with an inline header and a tab
    strip.
  - **Three tabs in fixed order: `Overview`, `Search`,
    `Folder`.** All three reachable from every
    selection; **`Overview` is always available and
    always visible** per the user-selected policy.
  - `Overview` renders scientific name, accepted
    status, authorship, species count.
  - `Search` renders a categorized outbound-link list
    (`General`, `Taxonomic`, `Academic`, `Multimedia`,
    `Documents`) in fixed order. **`Search` is a
    primary tab**, not a secondary card list.
  - `Folder` is a separate body (per-taxon materialize
    indicator).
  - Header `Browser` tab is the **global Research /
    file explorer** (NOT taxon-scoped).
- **Observed inconsistency (regression to close)**: the
  per-row `Search online` kebab action currently lands
  on `Overview` for top-level taxa (and is silently
  permitted to land on `Overview` for any selection
  whose `state.activeTab[taxonId]` has not been
  explicitly set). Its intended interaction MUST force
  the `Search` tab active for **every** selection —
  top-level or otherwise. The apply phase closes the
  regression in PR 5a / PR 5b.
- **Scope changes (binding)**:
  - PR 5a extended: absorbs the `DetailPanel` tab
    strip scaffolding (3-tab strip `Overview` /
    `Search` / `Folder`), `OverviewTab` body, and
    `Kebab` menu with the `Search online` action that
    forces `Search`. Forecast: ~310 LoC (Δ ~+30 from
    the previous ~280 forecast).
  - PR 5b extended: absorbs `SearchTab` (categorized
    outbound-link list in fixed order), `FolderTab`
    (separate body), `SearchLinkList` presenter, and
    the header `Browser` tab re-anchoring as global
    Research / file explorer (NOT taxon-scoped).
    Forecast: ~395 LoC (Δ ~+35 from the previous
    ~360 forecast). Stays under the 400-line per-PR
    review budget with **-5 LoC tight headroom**;
    maintainability is tracked.
  - **Total authored**: ~2,265 LoC across the 13
    sub-PRs (Δ ≤ 20 LoC from the previous ~2,245
    forecast; the new component split absorbs the
    additional pieces without duplicating production
    code).
  - **13-child chain topology preserved**; no PR
    position, dependency, or branch base changes.
- **Code / commit / push / PR / chain-topology
  constraints honored**:
  - No code, commit, push, PR, or `git revert`
    performed in this revision.
  - No PR base changes; no chain reordering.
  - Predecessor `migrate-nextjs-tailwind4/` stays
    byte-identical frozen.
- **Artifacts updated** (high-level only; per-domain
  specs are out of scope):
  - `openspec/changes/complete-taxa-frontend-migration/design.md`
    — module ownership table updated to add
    `OverviewTab`, `SearchTab`, `FolderTab`, `Kebab`,
    `SearchLinkList`; new section "UI surface and tab
    structure (verified current behavior)" pins the
    binding contract; sub-PR slice table updated to
    reflect PR 5a (~310 LoC) and PR 5b (~395 LoC);
    affected files table updated; risks table updated
    with two new entries.
  - `openspec/changes/complete-taxa-frontend-migration/spec.md`
    — functional parity section extended with seven
    new acceptance criteria (Detail panel tab strip,
    `Overview` tab, `Search` tab, `Folder` tab, `Search
    online` kebab action forces `Search` tab, header
    `Browser` tab is global).
  - `openspec/changes/complete-taxa-frontend-migration/tasks.md`
    — PR 5a extended with `OverviewTab`,
    `DetailPanel` tab strip, `Kebab` `Search online`
    force-Search contract, and a tab-strip Playwright
    regression witness; PR 5b extended with `SearchTab`,
    `FolderTab`, `SearchLinkList`, and the header
    `Browser` tab re-anchoring; per-task evidence
    tables updated.
  - `openspec/changes/complete-taxa-frontend-migration/apply-progress.md`
    — sub-PR table updated (PR 5a / PR 5b source files
    columns); total authored forecast updated;
    reconstruction order preserved; this change log
    entry recorded.
- Spanish mirrors
        `documents-es/openspec/changes/complete-taxa-frontend-migration/{design-es,spec-es,tasks-es,apply-progress-es}.md`
        — faithful translations of the high-level updates
        above; no extra content introduced; per-domain
        specs remain out of scope.

    ### 2026-09-02 — Dependency-defect fix (this entry)

    - **Defect identified by the apply gate's pre-flight
      re-audit**: PR 3b's `src/app/layout.tsx` imported
      `@taxa/app-shell` (a module PR 4b ships at position
      6/13 — *later* in the chain) and `./globals.css` (a
      file PR 3c ships at position 3/13 — *later* in the
      chain). At its `next build` witness, neither target
      file existed yet, so the witness was unsatisfiable.
      The same audit flagged PR 3b.5's triangulation
      assertion that the build output references the typed
      store barrel path `@taxa/browser-state` — that
      barrel file does not exist until PR 4a.
    - **Corrective re-scoping applied**: PR 3b is rescoped
      to a **self-contained App Router static-export
      bootstrap** — `src/app/{layout,page}.tsx` become
      minimal semantic placeholders (Raleway preload only)
      that import neither `@taxa/app-shell` nor
      `./globals.css`. The `import "./globals.css";` line
      moves into PR 3c (which already owns
      `globals.css`). The `<AppShell>` integration into
      `src/app/{layout,page}.tsx` moves into PR 4b (which
      already owns `src/modules/app-shell/**`). PR 3b.5's
      unsatisfiable `@taxa/browser-state` reference is
      dropped and replaced with the Raleway `.woff2` file
      assertion in `out/_next/static/media/`.
    - **13-child count preserved**: the chain topology and
      ordering stay unchanged; only the per-PR file lists
      and test witnesses change.
    - **Total authored**: ~2,282 LoC (Δ ~+37 LoC from the
      previous ~2,245; the dependency-defect fix removes
      ~25 LoC from PR 3b (no AppShell/globals.css wiring),
      adds ~30 LoC to PR 4b (AppShell integration seam),
      and ~2 LoC to PR 3c (`import "./globals.css";` line);
      each sub-PR stays well under 400).
    - **Largest sub-PR** remains **5b** at ~360 LoC (-40
      LoC / -10 % headroom). **No new `size:exception`
      required** — only the prior PR 3a `package-lock.json`
      exception remains.
    - **Approach A, FastAPI/SQLite, the frozen predecessor,
      and the per-domain specs stay unchanged**.
    - **Code / commit / push / PR / chain-topology
      constraints honored**:
      - No code, commit, push, PR, or `git revert`
        performed in this revision.
      - No PR base changes; no chain reordering; no
        sub-PR position changes.
      - Predecessor `migrate-nextjs-tailwind4/` stays
        byte-identical frozen.
      - No source-code edit performed (this is a
        high-level planning revision only).
    - **Artifacts updated** (high-level only; per-domain
      specs remain out of scope):
      - `openspec/changes/complete-taxa-frontend-migration/design.md`
        — sub-PR slice table updated for PR 3b (-25 LoC),
        PR 3c (+2 LoC), PR 4b (+30 LoC); `Dependency order`
        section updated to mark the dependency-defect fix
        as the contract; `Affected files` table updated
        for `src/app/{layout,page}.tsx`,
        `src/app/globals.css`, `src/modules/app-shell/**`;
        new note added under "Sub-PR slice under Approach
        A" about the dependency-defect fix.
      - `openspec/changes/complete-taxa-frontend-migration/spec.md`
        — clarifying note added before "Next step" about
        the PR-level dependency-defect fix; per-domain
        acceptance criteria, backend contract, validation
        gates, and rollback unit unchanged.
      - `openspec/changes/complete-taxa-frontend-migration/tasks.md`
        — Phase 3b rescoped (3b.2 G drops AppShell mount
        and globals.css import; 3b.3 G drops AppShell wrap
        and `"use client"`; 3b.5 T drops the unsatisfiable
        `@taxa/browser-state` reference and adds the
        Raleway `.woff2` file assertion; 3b.6 Refactor
        description updated); Phase 3c adds 3c.7 G (the
        `import "./globals.css";` integration into
        `src/app/layout.tsx`) + 3c.7 evidence row;
        Phase 4b adds 4b.6 G (the AppShell integration
        into `src/app/{layout,page}.tsx`) + 4b.6 evidence
        row; Per-sub-PR dependency section updated for
        3b / 3c / 4b; Forecast reconciliation updated
        to ~2,282 LoC; Review Workload Forecast table
        updated; new "dependency-defect fix (this
        revision)" note added in the header.
      - `openspec/changes/complete-taxa-frontend-migration/apply-progress.md`
        — Reconstruction table updated for PR 3b / 3c /
        4b source files and LoC; Forecast reconciliation
        (corrected) updated to ~2,282 LoC; this new change
        log entry recorded.
      - Spanish mirrors
        `documents-es/openspec/changes/complete-taxa-frontend-migration/{design-es,spec-es,tasks-es,apply-progress-es}.md`
        — faithful translations of the high-level updates
        above; no extra content introduced; per-domain
        specs remain out of scope.

> (Subsequent per-sub-PR entries appended below by the apply
        > worker, one block per sub-PR merge.)

    ### 2026-09-02 — CSS re-split (this entry)

    - **Defect identified by the apply gate's pre-flight
      re-audit**: the previous PR 3c (position 3/13) was
      tasked with migrating the legacy `web/index.html`
      inline `<style>` block of **1,963 lines** in a single
      sub-PR while staying under the 400-line per-PR review
      budget — the migration cannot fit.
    - **Corrective re-scoping applied**: the CSS portion of
      the migration is **re-split into four chained
      children** (PR 3c-a / PR 3c-b / PR 3c-c / PR 3c-d),
      each ≤ 400 author lines and partitioned by concern:
      tokens / base / dark mode (3c-a); tree + inline
      Overview styles (3c-b); Search / Folder / global
      Browser styles (3c-c); animations / utilities + final
      parity (3c-d, which ships the consolidated
      `tests/test_tailwind_4_parity.py` final parity
      test). The four CSS children collectively migrate
      the 1,963 legacy inline CSS lines into
      `src/app/globals.css` (≤ 1,500 authored lines plus
      Tailwind 4 base reset, well under the predecessor
      `out/_next/static/chunks/*.css` budget); the legacy
      `<style>` block is retired at PR 5c.
    - **Tracker PR #146 is the merged starting point** for
      the first new CSS child (PR 3c-a) — the tracker
      branch remains draft / no-merge and is the integration
      point PR 3c-a targets once its predecessor (PR 3b)
      has merged.
    - **Renumbering**: every later child shifts position by
      +3 to accommodate the four CSS children (3d 4→7;
      4a 5→8; 4b 6→9; 5a 7→10; 5b 8→11; 5c 9→12; 6a
      10→13; 6b 11→14; 6c 12→15; 3e 13→16). The semantic
      labels (3a, 3b, 3c-a, 3c-b, 3c-c, 3c-d, 3d, 4a, 4b,
      5a, 5b, 5c, 6a, 6b, 6c, 3e) are preserved; only the
      position counter (NN in
      `feat/complete-taxa-frontend-migration-NN-XXX`) and
      base-branch references change.
    - **16-child count** replaces the previous 13-child
      count; `feature-branch-chain` strategy and the
      "tracker is the only PR targeting `develop`" contract
      hold.
    - **Total authored is now ~3,615 LoC** (Δ ~+1,333 LoC
      from the previous ~2,282; the CSS re-split partitions
      the 1,963-line legacy inline CSS migration into 4
      children totaling ~1,500 LoC (replacing the previous
      single PR 3c's ~232 LoC) and adds 4 separate
      triangulation tests). Largest sub-PRs are the **four
      CSS children 3c-a / 3c-b / 3c-c** at ≤ 400 LoC each
      (right at the 400-line per-PR review budget with 0
      LoC headroom on the tightest child); **5b** is at
      ~395 LoC (-5 LoC headroom). PR 3d is at ~240 LoC
      (-160 LoC / -40 % headroom). **No new
      `size:exception` required** — only the prior PR 3a
      `package-lock.json` exception remains.
    - **Approach A, FastAPI/SQLite, the frozen predecessor,
      and the per-domain specs stay unchanged**.
    - **Code / commit / push / PR / chain-topology
      constraints honored**:
      - No code, commit, push, PR, or `git revert`
        performed in this revision.
      - No PR base changes; no chain reordering beyond the
        CSS re-split's renumbering of every later child by
        +3 positions.
      - Predecessor `migrate-nextjs-tailwind4/` stays
        byte-identical frozen.
      - No source-code edit performed (this is a
        high-level planning revision only).
    - **Artifacts updated** (high-level only; per-domain
      specs remain out of scope):
      - `openspec/changes/complete-taxa-frontend-migration/design.md`
        — sub-PR slice table updated to replace single PR 3c
        with four CSS children (3c-a / 3c-b / 3c-c / 3c-d at
        positions 3/16 / 4/16 / 5/16 / 6/16 respectively);
        every later child renumbered by +3 (3d 4→7; 4a 5→8;
        4b 6→9; 5a 7→10; 5b 8→11; 5c 9→12; 6a 10→13; 6b
        11→14; 6c 12→15; 3e 13→16); `Dependency order`
        section updated to mark the CSS re-split as the
        contract; `Affected files` table updated for
        `src/app/globals.css` (initial scaffold from PR
        3c-a + `@layer components` extensions from PR 3c-b /
        3c-c + `@layer base` finalisation from PR 3c-d),
        the new test files
        (`tests/test_tailwind_4_tokens.py`,
        `tests/test_taxonomy_styles.py`,
        `tests/test_research_styles.py`,
        `tests/test_tailwind_4_parity.py`), and the design-
        system barrel; new note added under "Sub-PR slice
        under Approach A" about the CSS re-split.
      - `openspec/changes/complete-taxa-frontend-migration/spec.md`
        — clarifying note added before "Next step" about the
        CSS re-split; the previous Dependency-defect fix
        section updated to reference PR 3c-a instead of PR
        3c; per-domain acceptance criteria, backend
        contract, validation gates, and rollback unit
        unchanged.
      - `openspec/changes/complete-taxa-frontend-migration/tasks.md`
        — header notes section updated with a new "2026-09-02
        — CSS re-split (this revision)" block; scope
        boundary section updated for the four CSS children
        and the 16-child topology; Review Workload Forecast
        table updated (~3,615 LoC across 16 sub-PRs);
        chain topology table updated to 16 rows; chain
        diagram updated; Per-sub-PR dependency section
        updated for 3c-a / 3c-b / 3c-c / 3c-d and every
        later child; Phase 3c replaced with four new phases
        (Phase 3c-a, Phase 3c-b, Phase 3c-c, Phase 3c-d)
        each ≤ 400 author lines with strict-TDD task
        checklists; per-task evidence tables updated;
        Phase 3d / 4a / 4b / 5a / 5b / 5c / 6a / 6b / 6c / 3e
        position references updated to the new 16-child
        topology (was 13/13, now 7/16 / 8/16 / 9/16 / 10/16
        / 11/16 / 12/16 / 13/16 / 14/16 / 15/16 / 16/16
        respectively); Forecast reconciliation updated to
        ~3,615 LoC.
      - `openspec/changes/complete-taxa-frontend-migration/apply-progress.md`
        — Reconstruction State section updated with the
        four CSS children replacing the previous single PR
        3c row; Sub-PR count updated to **16**; Total
        authored updated to ~3,615 LoC; chain topology
        table updated to 16 rows; Per-sub-PR dependency
        table updated; Workload / PR Boundary section
        updated to 16 sub-PRs; this new change log entry
        recorded.
      - Spanish mirrors
        `documents-es/openspec/changes/complete-taxa-frontend-migration/{design-es,spec-es,tasks-es,apply-progress-es}.md`
        — faithful translations of the high-level updates
        above; no extra content introduced; per-domain
        specs remain out of scope.

---

## Pre-flight gate for PR 3e (atomic cutover)

The atomic cutover unit (per `design.md` §"Atomic cutover unit")
changes exactly the following in a single release:

1. **`WEB_DIR` constant** at `api/server.py:54` (already
   repointed in Phase 3d; PR 3e flips the build artifact under
   `out/` from the candidate build to the production build
   with the `engines.node >= 20.9.0` runtime check live).
2. **Every active-consumer update** in the predecessor's
   `design.md::§3.1` (already authored by Phase 3d for the
   AC-21 reader path; PR 3e flips the remaining 25 §3.1
   consumers to read from the React component tree instead of
   the legacy `web/*` paths). The flip is the post-cut
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

**No subset revert is supported.** PR 3e ships only when
every gate below is PASS:

| Gate | Status (carried / closure planned) | Source |
| --- | --- | --- |
| G1 (single origin) | **PASS recorded** | Predecessor `design.md::§1` |
| G2 (foundation build) | **PASS recorded** against the verified Next 16.3.3 / Turbopack clean build | Predecessor `apply-progress.md` 2026-08-30 entry |
| G3 Tier-1 (consumer readiness, legacy pre-cut) | **PASS recorded** — all 26 §3.1 consumers green via the controlled fixture, `scripts/verify_consumers.py` | Predecessor `apply-progress.md` (PR #109 + #111 + #115 + #116) |
| G4 (Playwright + Lighthouse parity) | **blocked — verifier not authored**; must close in apply phase | Phase 6c — `scripts/g4_measure.sh` against the positions 1–9-landed candidate build |
| G5 (hydration baseline) | **blocked — latest comparable capture exits 4 with regression** (three comparable real-capture verdicts were `ready`, `blocked`, `blocked`; ±1 ms variation at 0–4 ms makes the current median/percentage comparison non-reproducible). No G5 PASS or closure is authorized. | Phase 6a — `scripts/reconstruct_hydration_baseline.py` and `scripts/capture_hydration_candidate.py` provide the current HTTP/multi-sample captures; `scripts/g5_close.sh` writes the versioned `evidence/g5/{status,regression-report}.json`. Do not flip the gate until a new observable metric and versioned absolute tolerance/protocol are approved and rerun. |
| G6 (cutover rehearsal) | **PASS recorded — `cutover-rehearsal.json` captured at `2026-09-06T15:10:54Z`** (controlled port 55637 — never the ambient FastAPI 8765; `activation_complete: true`; all 26 §3.1 consumers selected; `unselected_count: 0`; `silent_fallback_paths: []`; `g3_tier2_exit_code: 0`); atomic cutover unit + rollback unit consistent | Phase 6b — `scripts/rehearse_cutover.py` dry-runs the atomic cutover unit against the activated working-copy manifest; the activated working-copy manifest (`openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`) carries the Tier-2 flip for all 26 §3.1 consumers; predecessor `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json` stays byte-identical frozen |

**Cutover activation sequence** (when all six gates green):

1. Author the **post-cut activation record** in
   `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
   (the working copy; predecessor
   `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
   stays byte-identical frozen) — flip `activation_status`
   and `replacement.status` to Tier-2 for every one of the
   26 §3.1 consumers.
2. Apply the **atomic cutover unit** — the four-set change
   in one release (per `design.md` §"Atomic cutover unit").
3. Run the G3 Tier-2 verifier against the activated
   selection; `CONSUMER-READINESS.json` exits 0 with
   `activation_complete: true`, `unselected_count: 0`.
4. Run `make smoke` + Playwright + Lighthouse; verify the
   parity checklist (per `design.md` §"Parity / evidence
   plan").
5. Mark the cutover PR (child 16 / 16, targeting the PR 6c
   branch) ready for review and flip the gate-status footer
   in §Status below from "blocked / blocked / blocked" to "PASS
   recorded" only after each gate is independently verified.
6. Merge PR 3e into the tracker — the chain is now complete.
   Take `docs/complete-taxa-frontend-migration-plan` **out
   of draft** and merge it to `develop` with a **merge
   commit** (no squash, so `<pr3e-sha>` stays addressable
   for the atomic rollback). This is the single point at
   which the migration reaches `develop`.

---

## Forecast reconciliation (corrected)

- **3a** ~210 LoC authored (toolchain bootstrap — absorbs
~40 LoC of `package.json` dep pins + ~25 LoC of
  `scripts/check-runtime.mjs` + ~50 LoC of `tsconfig.json`
  base + 1 LoC `.nvmrc` + ~95 LoC of two new tests);
  **3b** ~150 (App Router static-export bootstrap,
  **self-contained** — minimal semantic placeholder
  layout/page; no AppShell mount, no globals.css import;
  the dependency-defect fix); **3c-a** ~400 (tokens /
  base / dark mode — `src/app/globals.css` initial
  scaffold with `@theme` + design-system barrel +
  1-line `import "./globals.css";` integration into
  `src/app/layout.tsx`; the dependency-defect-fix seam);
  **3c-b** ~400 (tree + inline Overview styles —
  `@layer components` taxonomy selectors);
  **3c-c** ~400 (Search / Folder / global Browser styles
  — `@layer components` research / chrome selectors);
  **3c-d** ~300 (animations / utilities + final parity —
  `@layer base` `@keyframes` / `color-mix()` / utility
  classes / body reset / first-child reset + the
  consolidated `tests/test_tailwind_4_parity.py`);
  **3d** ~240 (the heaviest re-scoped sub-PR at the
  position-7 boundary, fusing Makefile + WEB_DIR + AC-21);
  **4a** ~180; **4b** ~120 (hydration guard + AppShell
  integration into `src/app/{layout,page}.tsx`; the
  dependency-defect fix); **5a** ~310; **5b** ~395;
  **5c** ~200; **6a** ~50; **6b** ~120; **6c** ~20;
  **3e** ~120 (mostly `apply-progress.md` delta).
  **Total**: ~3,615 LoC authored across **16** sub-PRs
  (Δ ~+1,333 LoC from the previous ~2,282; the CSS
  re-split partitions the 1,963-line legacy inline CSS
  migration into 4 children totaling ~1,500 LoC
  (replacing the previous single PR 3c's ~232 LoC) and
  adds 4 separate triangulation tests; the
  dependency-defect fix removes ~25 LoC from PR 3b (no
  AppShell/globals.css wiring) and adds ~30 LoC to PR
  4b (AppShell integration seam) plus ~2 LoC to PR 3c-a
  (`import "./globals.css";` line); each sub-PR stays
  well under 400).
- Largest sub-PRs are the **four CSS children 3c-a /
  3c-b / 3c-c** at ≤ 400 LoC each (right at the 400-line
  per-PR review budget with 0 LoC headroom on the
  tightest child); **5b** is at ~395 LoC (-5 LoC
  headroom). PR 3d is at ~240 LoC (-160 LoC / -40 %
  headroom against the 400-line budget). **No new
  `size:exception` required** — only the prior PR 3a
  `package-lock.json` exception remains.
- **Chained PRs recommended**: **Yes** — each sub-PR fits
  the per-PR budget on its own, but the ~3,615-line total
  and the atomic cutover (the feature MUST integrate before
  it reaches `develop`) put this change in the Feature
  Branch Chain gate.
- **Chain strategy**: **`feature-branch-chain`**
  (user-selected). Tracker
  `docs/complete-taxa-frontend-migration-plan` (referenced
  as PR #146) is draft/no-merge and is the **only** PR
  targeting `develop`; child PR 3a targets the tracker;
  each later child targets its immediate predecessor
  branch. The first new CSS child (PR 3c-a) treats the
  tracker PR #146 as the merged starting point for the
  four-child CSS re-split. Supersedes the `AGENTS.md` §4
  direct-to-`develop` default and the predecessor's
  apply-progress precedent for this change.
- **Delivery strategy**: **`ask-on-risk`** (per preflight;
  no risk flag is open — Approach A is FINAL, the
  predecessor is frozen, every sub-PR fits under 400
  lines, the CSS re-split satisfies the 1,963-line legacy
  inline CSS migration that the previous single PR 3c
  could not).
- **Decision needed before apply**: **No** (Approach A
  locked, chain strategy known, every sub-PR within
  budget, dependency order corrected, CSS re-split
  resolves the 1,963-line migration).

---

## Workload / PR Boundary

- **Mode**: **Feature Branch Chain** — 1 draft/no-merge
  tracker (`docs/complete-taxa-frontend-migration-plan` →
  `develop`) plus **16** sequential child PRs (toolchain
  bootstrap → App Router static export → **4 CSS children
  (3c-a / 3c-b / 3c-c / 3c-d)** → Makefile/mount → 4a →
  4b → 5a → 5b → 5c, followed by the Phase 6 validation
  links, followed by the PR 3e atomic cutover as the
  last child).
- **Total sub-PRs**: **16** (3a, 3b, 3c-a, 3c-b, 3c-c,
  3c-d, 3d, 4a, 4b, 5a, 5b, 5c, 6a, 6b, 6c, 3e — note 6a,
  6b, 6c are validation work after the candidate path;
  3e is gated on all six gates green).
- **Each sub-PR ≤ 400 LoC authored** (the four CSS
  children ride at the 400-line budget with 0 LoC headroom
  on the tightest child; **5b** at ~395 LoC with -5 LoC
  headroom; 3d at ~240 LoC with -160 LoC headroom).
  **No sub-PR exceeds the 400-line per-PR review budget.**
  **No `size:exception` is expected or planned.**
- **Each child PR's base** = its **immediate predecessor
  branch** (the tracker for PR 3a). **Only the tracker
  targets `develop`, and it stays draft / no-merge until
  the chain completes.**

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Reconstruction sequence interrupted; partial merge of the toolchain bootstrap + App Router sub-PRs leaves the project in an inconsistent state. | Medium | Each sub-PR's focused test passes independently of subsequent sub-PRs. Under the Feature Branch Chain no partial state can reach `develop`: children accumulate on the draft/no-merge tracker only. A stuck child blocks its successors inside the chain, never `develop`. |
| Predecessor `migrate-nextjs-tailwind4/` directory accidentally edited during reconstruction; source files deviate from the frozen planning history. | High | Predecessor directory is marked read-only at filesystem level; CI / branch-protection rejects any PR that modifies it. Every sub-PR's PR body must include a `## Lo que NO cambió` section confirming the predecessor stayed byte-identical. |
| Phase 6 validation work accidentally generates new `web/**` source, new `api/server.py` route handlers, or new `extension/**` files (violates the "validation only, not migration" contract). | Medium | Phase 6 tasks are constrained to `scripts/*` shims, measurement artifacts in `out/`, and `apply-progress.md` deltas. No `web/**`, `api/server.py` route handlers, or `extension/**` edits are permitted in Phase 6. The 5c.6 deletion lives in PR 5c, NOT in Phase 6. |
| G5's current median/percentage hydration comparison is unstable at sub-millisecond scale; comparable runs produced **ready / blocked / blocked** verdicts with ±1 ms movement at 0–4 ms. | High | The latest evidence remains **blocked** (regression on `initial_paint` 0→1 ms and `interaction_latency` 3→4 ms; comparison exit 4). The risk-register disposition is a methodological-exception **request, not approval**: before G5 is reattempted, version a new observable hydration metric and a versioned absolute tolerance/protocol (including clock origin, sampling/outlier rules, units, and pass/fail aggregation). No G5 PASS, closure, or cutover activation is granted. |
| G6 rehearsal fails closed (subset-only dry-run exits non-zero) and blocks the cutover. | Low | The fail-closed invariant is the spec — subset reverts break the SPA shell. PR 3e ships only when the full atomic rehearsal exits 0. |
| G4 measurement exceeds the ≤ 0 % delta budget on initial paint or interaction latency. | Medium | `scripts/g4_measure.sh` records the delta; if it exceeds 0 %, the apply worker writes an exemption request into `design.md` §"Risk register" and the gate stays blocked until a maintainer signs off. |
| Sub-PR 5b (research port + CDN pin) inflates the largest sub-PR to ~360 LoC; reviewers still see one focused work unit. | Low | Sub-PR 5b is one cohesive port of `web/{file_explorer,file_viewer,format,keymap}.js`; the research module's 5 × 4 layering matches the canonical modular-architecture spec. The 400-line budget holds with -40 LoC headroom. |
| A child PR is cut from `origin/develop` instead of its chain base, so its diff shows unrelated slices already merged into the tracker. | Medium | Treat a polluted diff as a **base bug**, not a review finding: retarget or rebase onto the immediate predecessor until only the current work unit appears. §Reconstruction manifest step 7 makes `git diff --stat <base-branch>` a per-PR gate. |
| `cutover-manifest.json` working-copy flip (Phase 6b.3) accidentally edits the predecessor's frozen copy instead of the working copy. | High | The flip is written into `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json` (working copy); predecessor `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json` stays byte-identical. The apply worker MUST diff both copies before PR 3e. |
| **Dependency-order regression** (NEW from the corrective plan revision): a future maintainer revisits the chain and re-introduces the original ordering (App Router static export before the toolchain bootstrap). | Medium | The corrective plan revision permanently records the dependency contract in `tasks.md` §"Per-sub-PR dependency", this `apply-progress.md` §"Per-sub-PR dependency", and `design.md` §"Sub-PR slice under Approach A". Any chain reordering request must reopen the apply gate for a fresh dependency audit before merging. |
| The toolchain bootstrap (position 1) lands on a host with a pre-existing `package-lock.json` from a previous Next 14 / React 18 attempt; `npm ci` resolves against the wrong lock. | Medium | Sub-PR 3a.2 explicitly removes `autoprefixer`, `postcss`, `@tailwindcss/forms` from the rewritten `package.json`; `npm ci` regenerates a clean `package-lock.json` against the pinned deps. The `tests/test_toolchain_bootstrap.py` triangulation asserts no stray legacy deps remain. |

---

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

---

## Status

**Approach A is FINAL** (locked 2026-09-02; recorded in §1
of `design.md`). G1 PASS recorded; G2 PASS recorded against
the verified Next 16.3.3 / Turbopack clean build; G3 Tier-1
PASS recorded (all 26 §3.1 consumers green against the legacy
pre-cut runtime via the controlled fixture,
`scripts/verify_consumers.py`, PR #109 + #111 + #115 + #116).
G3 Tier-2 (atomic-cut selection) **NOT PASSED** — gated by
G4 + G5 + G6 closure. G4 (Playwright + Lighthouse parity)
**blocked — verifier not authored**; must close in apply
phase via Phase 6c. G5 (hydration baseline)
**blocked — real captures are not reproducible under the current
protocol**. Three comparable runs produced `ready`, `blocked`, and
`blocked` verdicts because the 0–4 ms measurements moved by ±1 ms;
the latest captured evidence records baseline medians 0.0/3.0 ms,
candidate medians 1.0/4.0 ms, regression on both axes, and
comparison exit 4. The methodological-exception request recorded in
`design.md` does not grant PASS or closure; G5 must be reattempted
only after a new observable metric and versioned absolute
tolerance/protocol are approved.
G6 (cutover rehearsal) **PASS recorded — `cutover-rehearsal.json` captured at `2026-09-06T15:10:54Z` (see `/Users/sebailla/Developer/taxa-worktrees/complete-taxa-frontend-migration-23-6b-post-6a/openspec/changes/complete-taxa-frontend-migration/evidence/g6/cutover-rehearsal.json`); atomic cutover unit + rollback unit consistent; 0 silent fallback paths detected; apply worker may proceed to PR 3e.**.
Predecessor `openspec/changes/migrate-nextjs-tailwind4/**` is **frozen**.
No FastAPI activation in this design pass; the atomic cutover
PR 3e ships only when all six gates are green.

**Corrective plan revision applied 2026-09-02**: the chain
topology above replaces the original
`docs/complete-taxa-frontend-migration-plan` ordering after
the apply gate identified the dependency-order defect (PR 3a
could not require `next build`/`out/index.html` before the
Next/React/Tailwind/TypeScript toolchain and Node runtime
contract existed). The corrected chain places the toolchain
bootstrap at position 1, the App Router static export at
position 2 (now satisfiable), Tailwind/tokens at position 3,
the Makefile/mount fused sub-PR at position 4, and the
remaining sub-PRs in dependency-correct order at positions
5–13. The 13-child count is preserved.

**UI surface & tab-structure corrective revision applied
2026-09-02**: the live browser inspection of
`http://127.0.0.1:8765/` revealed a verified UI surface
that diverges from the per-domain spec narrative. The
high-level design/spec/tasks/apply-progress and the faithful
Spanish mirrors were revised to pin the binding contract
(Overview always available/visible; Search is a primary tab;
Search online forces Search; Browser is global Research).
Per-domain specs are out of scope for this revision. The
13-child chain topology was preserved; no PR position,
dependency, or branch base changed. The PR 5a and PR 5b
forecasts moved to ~310 LoC and ~395 LoC respectively (the
latter with tight -5 LoC headroom against the 400-line per-
PR review budget); total authored is now ~2,265 LoC (Δ ≤ 20
from the previous ~2,245 forecast).

**Dependency-defect fix applied 2026-09-02** (this status
note): the apply gate's pre-flight re-audit identified a
second dependency defect inside the corrected topology —
PR 3b's `src/app/layout.tsx` imported `@taxa/app-shell` (a
module PR 4b ships at position 9/16) and `./globals.css`
(a file PR 3c-a ships at position 3/16), neither of
which existed when PR 3b's `next build` witness had to
run. The same audit flagged PR 3b.5's unsatisfiable
`@taxa/browser-state` triangulation assertion (the
barrel file does not exist until PR 4a). **PR 3b is
rescoped to a self-contained App Router static-export
bootstrap** (no AppShell, no globals.css import); the
`import "./globals.css";` line moves into PR 3c-a; the
`<AppShell>` integration into `src/app/{layout,page}.tsx`
moves into PR 4b. **Total authored after the
dependency-defect fix is ~2,282 LoC** (Δ ~+37 LoC from
the previous ~2,245; PR 3b shrinks ~25 LoC, PR 3c-a
grows ~2 LoC, PR 4b grows ~30 LoC); each sub-PR stays
well under 400; **only the prior PR 3a `package-lock.json`
exception remains**.

**CSS re-split applied 2026-09-02** (this status note):
the apply gate's pre-flight re-audit identified that PR
3c, as scoped at the dependency-defect-fix revision, was
**unsatisfiable** — it was tasked with migrating the
legacy `web/index.html` inline `<style>` block of
**1,963 lines** in a single sub-PR while staying under
the 400-line per-PR review budget; the migration cannot
fit. The CSS portion is therefore **re-split into four
chained children** (PR 3c-a / PR 3c-b / PR 3c-c / PR
3c-d) at positions 3 / 16, 4 / 16, 5 / 16, 6 / 16, each
≤ 400 author lines and partitioned by concern: tokens /
base / dark mode; tree + inline Overview styles;
Search / Folder / global Browser styles; animations /
utilities + final parity. Tracker **PR #146** is the
merged starting point for the first new CSS child (PR
3c-a). Every later child shifts position by +3 (3d 4→7;
4a 5→8; 4b 6→9; 5a 7→10; 5b 8→11; 5c 9→12; 6a 10→13;
6b 11→14; 6c 12→15; 3e 13→16). Semantic labels are
preserved; only the position counter and base-branch
references change. The four CSS children collectively
migrate the 1,963 legacy inline CSS lines into
`src/app/globals.css` (≤ 1,500 authored lines plus
Tailwind 4 base reset, well under the predecessor
`out/_next/static/chunks/*.css` budget); the legacy
`<style>` block is retired at PR 5c. **Total authored
is now ~3,615 LoC across 16 sub-PRs** (Δ ~+1,333 LoC
from the previous ~2,282; the CSS re-split partitions
the 1,963-line legacy inline CSS migration into 4
children totaling ~1,500 LoC (replacing the previous
single PR 3c's ~232 LoC) and adds 4 separate
triangulation tests; each sub-PR stays well under 400);
**only the prior PR 3a `package-lock.json` exception
remains**.

**PR 3c-d re-split supersession note 2026-09-03** (this
status note; PR #150 task replan is authoritative): PR
#150 (`tasks.md` / `tasks-es.md` "3c-d unsatisfiability
split") re-plans the previous monolithic PR 3c-d
(animations / utilities + final parity) into three
sequential children, each ≤ 400 authored lines.
**3c-d = base / reset / global state affordances only**
(`@keyframes` (`spin`), global `@layer base`
`color-mix()` selectors, `body { overscroll-behavior:
none; … }`, `main > :first-child { margin-top: 0
!important; }`; **no utility classes, no parity test**;
allowed test `tests/test_tailwind_4_base_resets.py`).
**3c-e (new) = utility-class surface + remaining
`@keyframes` / `color-mix()` (component-scoped color-mix,
utility-paired rules)**; **no parity test**; allowed
test `tests/test_tailwind_4_utilities.py`.
**3c-f (new) = sole full-parity test only** — no new
`globals.css` code; final consolidated
`tests/test_tailwind_4_parity.py`. Renumbering:
3d 7→**9/18**; 4a 8→**10/18**; 4b 9→**11/18**;
5a 10→**12/18**; 5b 11→**13/18**; 5c 12→**14/18**;
6a (G5) 13→**15/18**; 6b (G6) 14→**16/18**;
6c (G4) 15→**17/18**; 3e 16→**18/18**;
**3c-d stays at 6/18** (narrowed). New branches:
`…-07-3c-e` (base `…-06-3c-d`), `…-08-3c-f` (base
`…-07-3c-e`). **18-child count** replaces 16;
`feature-branch-chain` strategy and "tracker-only targets
`develop`" contract hold. Per-sub-PR LoC budgets stay
well under 400; only the prior PR 3a `package-lock.json`
exception remains. **G4 / G5 / G6 (now 17/18 / 15/18 /
16/18), the frozen predecessor, Approach A, FastAPI/SQLite,
and the per-domain specs stay unchanged**. Merged PRs
3c-a/#147, 3c-b/#148, 3c-c/#149 preserved. The five CSS
children (3c-a / 3c-b / 3c-c / 3c-d / 3c-e) plus PR 3c-f
cannot collapse without violating the 400-line per-PR
review budget. **Documentation-only supersession note**:
no source-code edit, no rebase, no new branch creation
in this revision; the next code worktree picks up the
authoritative scope from `tasks.md`.

> **Footer (apply phase flips)**: G1: PASS recorded · G2:
> PASS recorded · G3 Tier-1: PASS recorded · G3 Tier-2: NOT
> PASSED (gated) · G4: blocked — verifier not authored ·
> G5: blocked — latest comparable real capture regressed (three runs: ready / blocked / blocked; ±1 ms variance at 0–4 ms; no PASS authorized) ·
> G6: blocked — verifier not authored. Footer flips to PASS
> recorded for G4 / G5 / G6 only after Phase 6 closes and PR
> 3e ships.

---

## Next step

The **apply phase** (`sdd-apply`) reads `tasks.md` and this
`apply-progress.md`, then executes the reconstruction
manifest (§Reconstruction manifest) sub-PR by sub-PR. Phase
6 validation work (6a, 6b, 6c) runs after the candidate
path (positions 1–9) is green and before PR 3e. The atomic
cutover PR 3e ships only when all six gates are green. The
**verify phase** (`sdd-verify`) confirms the parity checklist
(per `design.md` §"Parity / evidence plan") and the rollback
unit (`git revert <pr3e-sha>` restores the legacy vanilla
build atomically). The **archive phase** (`sdd-archive`)
copies each per-domain spec verbatim into
`openspec/specs/{frontend-runtime,design-tokens,browser-state-hydration,frontend-bootstrap,research}/spec.md`
and promotes the modular-architecture spec into the
canonical specs tree.

---

## Addendum — 2026-09-04: Phase 5a four-slice replan (append-only)

This is a deliberate **append-only** decision addendum; the prose above for
Phase 5a (taxonomy port, PR 5a at the chain position it currently holds)
is preserved verbatim. It records a docs-only supersession that governs
how the **next** code worktree re-slices PR 5a into four reviewable
sub-PRs. The oversized PR-5a WIP (5a.1–5a.9 + `DetailPanel` tab-strip +
`Kebab` force-Search + Playwright witness in a single slice, well past
the 400-line per-PR review budget) is **discarded**.

- **Discarded oversized 5a WIP.** The previous monolithic Phase 5a
  enumeration (5a.1 R, 5a.2 G, 5a.3 G, 5a.4 G, 5a.5 G, 5a.6 G, 5a.7 T,
  5a.8 T, 5a.9 Refactor, all in one PR at the prior position) is replaced
  by the four-slice replan below. The discarded enumeration is retained
  only as historical context; it is **not** authoritative for the next
  code worktree.
- **5a.1 — foundation.** `src/modules/taxonomy/{domain,application,
  infrastructure}/**` only: type surface, invariants, `fetch*` functions,
  `useTaxonTree` hook; the application layer emits view-models only. No
  `Tree.tsx`, no `DetailPanel.tsx`, no `Kebab.tsx`, no `TabStrip`.
- **5a.2 — mounted `Tree` + `Breadcrumb`.** `src/modules/taxonomy/
  presentation/{Tree,Breadcrumb}.tsx`; ports the legacy
  `web/{tree,breadcrumb}.js` row layout (per-row kebab glyph reserved,
  but the menu body is **not** yet authored — the glyph is a no-op until
  5a.4); rides on PR 3c-b's `@layer components` selectors. No `DetailPanel`,
  no `Overview`, no `TabStrip`, no global activation.
- **5a.3 — `DetailPanel` + `Overview` body + local `TabStrip`.**
  `src/modules/taxonomy/presentation/{DetailPanel,OverviewTab}.tsx` plus
  a **local** `TabStrip` (`["Overview", "Search", "Folder"]`, fixed
  order, three siblings always reachable, `Overview` always visible per
  the user-selected policy); no global activation contract yet — the
  `Kebab`'s force-Search callback is wired only against this local
  component.
- **5a.4 — `Kebab` `Search online` force-Search + Chromium witness.**
  `src/modules/taxonomy/presentation/Kebab.tsx` plus the
  `tests/test_taxonomy_infra.py` extension: the per-row kebab menu gains
  the `Search online` action; the action dispatches the tab-activation
  callback that **forces the `Search` tab active** on the selected taxon
  (it MUST NOT default to `Overview`, even for top-level taxa); the
  Chromium witness is the canonical regression guard. **Regression
  assignment** (per request):
  `Archaea → Search online → Search` (top-level taxon; the current live
  regression lands on `Overview`; 5a.4 closes it).
- **Per-slice ≤ 400 lines (authored LoC, excluding regenerated
  `package-lock.json`).** Each of 5a.1, 5a.2, 5a.3, 5a.4 is sized to
  leave headroom under the 400-line per-PR review budget that Approach A
  locked 2026-09-02. The discarded WIP violated the budget; the
  four-slice replan restores it.
- **Chain positions for the next code worktree (22-child topology).** The
  next code worktree MUST use this mapping and nothing else:
  `5a.1 → 13`, `5a.2 → 14`, `5a.3 → 15`, `5a.4 → 16`, `5b → 17`,
  `5c → 18`, `6a → 19`, `6b → 20`, `6c → 21`, `3e → 22` (atomic cutover,
  still gated on G1–G6 closure). Positions 13–16 hold the 5a.1–5a.4 split;
  positions 17–22 hold every later sub-PR; the 22-child count replaces
  16. PR 4b at position 12/22 is the merge base for 5a.1. Chain topology,
  `feature-branch-chain` strategy, "tracker-only targets `develop`"
  contract, predecessor frozen status, Approach A, FastAPI/SQLite, and
  per-domain specs are unchanged.
- **`TabStrip` promotion deferred to design-system — at PR 5b.** The
  `TabStrip` primitive authored in 5a.3 stays **local** to
  `src/modules/taxonomy/presentation/` for the 5a slice. Its promotion
  to `src/modules/design-system/` (so 5b's `SearchTab` / `FolderTab` can
  consume it as a sibling primitive) is **deferred to PR 5b**, along
  with the regression guard that no taxonomy import path regresses.
- **Authoring contract.** No code edit, no rebase, no new branch in this
  addendum; the next code worktree reads this addendum as authoritative
  and re-slices 5a.1–5a.4 per the rules above. The Spanish mirror lives
  at `documents-es/.../{tasks-es.md,apply-progress-es.md,design-es.md}`
  and carries the same semantics; any drift is resolved in favour of the
  English.

---

## Addendum — 2026-09-04: Phase 5b four-slice replan (append-only)

This is a deliberate **append-only** decision addendum; the prose above for
Phase 5b (research module port + CDN pin, PR 5b at the chain position it
currently holds) is preserved verbatim. It records a docs-only supersession
that governs how the **next** code worktree re-slices PR 5b into four
reviewable sub-PRs. The previous in-line 5b enumeration (5b.1 R + 5b.2–5b.7
G + 5b.8 T + 5b.9 Refactor — nine steps inside a single ~395 LoC slice
already at the 400-line per-PR budget) is **discarded** and retained only
as historical context.

- **Discarded in-line 5b enumeration.** The previous monolithic Phase 5b
  enumeration (5b.1 R tests, 5b.2 G domain, 5b.3 G `infrastructure/api.ts`,
  5b.4 G `search-engines.js` re-export, 5b.5 G application hooks,
  5b.6 G presentation ~290 LoC, 5b.7 G app-shell `Browser` re-anchor,
  5b.8 T triangulation, 5b.9 Refactor — all in one PR at the prior
  position 17/22) is replaced by the four-slice replan below. The
  discarded enumeration is retained only as historical context; it is
  **not** authoritative for the next code worktree.
- **5b.1 — foundation (research domain + infrastructure + search-engines
  re-export).** `src/modules/research/{domain,infrastructure}/**`: typed
  `ResearchFile` / `Engine` / `FileNode` (domain); `fetchFiles(id)`,
  `fetchServe(id, rel)`, idempotent CDN `loadScriptOnce(name, src)` loader
  (`infrastructure/api.ts`); plus `search-engines.js` re-exporting
  `SEARCH_ENGINES` from PR 3d's `src/data/search-engines.js` (named export
  unchanged). No application hooks, no `FileExplorer.tsx`, no
  `FileViewer.tsx`, no `SearchTab` / `FolderTab` / `SearchLinkList`, no
  app-shell delta.
- **5b.2 — application hooks.** `src/modules/research/application/
  {useFileExplorer,useFileViewer}.ts`: the two hooks consume the typed
  `fetch*` functions from 5b.1 and emit view-models. Persisted-state keys
  (`state.explorer.search.{query, mode, hideEmpty}`) and the **200 ms
  debounce** contract are **declared here** as hook-level contracts so
  5b.3 can consume them; the `FileExplorer.tsx` / `FileViewer.tsx`
  wiring stays in 5b.3. No presentation, no `SearchTab` / `FolderTab`,
  no app-shell delta.
- **5b.3 — `FileExplorer` + `FileViewer` presentation + CDN / debounce /
  persisted-state behaviour.** `src/modules/research/presentation/
  {FileExplorer,FileViewer,RawTableTreeTabs,MetaStrip,BreadcrumbPanel,
  Banners}.tsx`: ports the legacy
  `web/{file_explorer,file_viewer,format,keymap}.js` two-pane layout;
  nine-format dispatcher with CDN-pin lazy loading (`mammoth@1.8.0`,
  `xlsx@0.18.5`, `epubjs@0.3.93`); legacy DOC + unsupported fallbacks;
  CDN failure banner `"Viewer offline — raw download unavailable"`;
  tree search with **200 ms debounce**, filter / highlight modes, and
  `state.explorer.search.{query, mode, hideEmpty}` **persisted** across
  taxon switches; meta strip `FORMAT | SIZE | ENCODING`; explorer state
  reset on taxon switch. Rides on PR 3c-c's `@layer components`
  selectors. No `SearchTab` / `FolderTab` / `SearchLinkList`, no
  app-shell delta, no `TabStrip` promotion yet.
- **5b.4 — `SearchTab` + `FolderTab` + `SearchLinkList` + global `Browser`
  re-anchor + `TabStrip` design-system promotion.**
  `src/modules/research/presentation/{SearchTab,FolderTab,
  SearchLinkList}.tsx`: `SearchTab` renders the five category sections
  (`General` / `Taxonomic` / `Academic` / `Multimedia` / `Documents`) in
  fixed order; `FolderTab` is **separate** (per-taxon materialize
  indicator; MUST NOT be a subset of `SearchTab`); `SearchLinkList` maps
  each `Engine` to an anchor with `target="_blank"` and `rel="noopener
  noreferrer"`, resolving the URL template from `SEARCH_ENGINES`. Plus
  `src/modules/app-shell/infrastructure/page-chrome.tsx` (~30 LoC
  delta): the header `Browser` tab is re-anchored as the **global
  Research / file explorer** — opens without a `taxonId` filter;
  selecting a taxon while `Browser` is active MUST NOT scope the
  explorer to that taxon (the `data-path="browser"` /
  `data-action="nav-tab"` attribute contract is preserved). Plus the
  deferred `TabStrip` promotion from 5a.3 lands here: the local
  `TabStrip` primitive moves to `src/modules/design-system/` (sibling
  primitive), **with the regression guard** that no taxonomy import
  path regresses.
- **Per-slice ≤ 400 lines (authored LoC, excluding regenerated
  `package-lock.json`).** Each of 5b.1, 5b.2, 5b.3, 5b.4 is sized to
  leave headroom under the 400-line per-PR review budget that
  Approach A locked 2026-09-02. The discarded in-line 9-step
  enumeration violated the budget; the four-slice replan restores it.
- **Chain positions for the next code worktree (tracker + 25 children =
  26 total PRs).** The next code worktree MUST use this mapping and
  nothing else: `5b.1 → 17`, `5b.2 → 18`, `5b.3 → 19`, `5b.4 → 20`,
  `5c → 21`, `6a → 22`, `6b → 23`, `6c → 24`, `3e → 25` (atomic
  cutover, still gated on G1–G6 closure). The 25-child count replaces
  the prior 22-child count; positions 17–20 hold the 5b.1–5b.4 split,
  positions 21–25 hold every later sub-PR. PR 4b at position 12/22
  stays the merge base for 5a.1; 5b.1's merge base is the PR that
  lands immediately before position 17 in the corrected topology
  (per the next code worktree's audit). Chain topology,
  `feature-branch-chain` strategy, "tracker-only targets `develop`"
  contract, predecessor frozen status, Approach A, FastAPI/SQLite,
  and per-domain specs are unchanged.
- **`TabStrip` promotional close-out at 5b.4.** The `TabStrip`
  promotion that 5a.3's addendum deferred to PR 5b now closes at
  PR 5b.4 (not at the end of PR 5b as a whole): the local `TabStrip`
  primitive moves to `src/modules/design-system/`, and 5b.4's
  regression guard ensures no taxonomy import path regresses. After
  5b.4 lands, no further `TabStrip` work is owed from the 5a / 5b
  slices.
- **Authoring contract.** No code edit, no rebase, no new branch in
  this addendum; the next code worktree reads this addendum as
      authoritative and re-slices 5b.1–5b.4 per the rules above. The
      Spanish mirror lives at
      `documents-es/.../{tasks-es.md,apply-progress-es.md,design-es.md}`
      and carries the same semantics; any drift is resolved in favour of
      the English.

### 2026-09-05 — Phase 6a attempt: G5 baseline harness shipped under environmental blocker (G5 NOT flipped)

- **Harness shipped** (superseded by the next attempt below; retained for
  audit only):
  - `scripts/measure_hydration.py` extended compatibly with
    `--baseline <b> --candidate <c> [--report-out <r>]` mode that
    computes the percentage delta on `initial_paint` (= `client_render
    .tree_first_paint_ms`) and `interaction_latency` (= `client_render
    .tree_first_interactive_ms`). Exit code `4` fails closed on any
    positive delta on either axis; exit code `0` requires both deltas
    ≤ 0 %. The legacy single-positional `<path>` invocation is
    preserved exactly (back-compat contract pinned by
    `tests/test_hydration_timing.py::test_measure_hydration_back_compat_single_positional_artifact`).
  - `scripts/reconstruct_hydration_baseline.py` (new) attempts a real
    Playwright + Chromium capture against the **frozen, read-only**
    `tools/g3-legacy-fixture/web/` fixture and emits a
    schema-conformant artifact at `web/dist/evidence-baseline.json`.
    When Playwright or Chromium is unavailable it writes a fail-closed
    placeholder carrying `source: "unavailable"` and a `blocker` field
    naming the missing dependency, then exits `3`. It NEVER invents
    baseline numbers.
  - `scripts/g5_close.sh` (new, executable) is the runtime harness:
    runs `reconstruct_hydration_baseline.py`, runs `measure_hydration.py`
    `--baseline`/`--candidate`/`--report-out` against
    `out/hydration-candidate.json` when present, and writes a versioned
    `status.json` under
    `openspec/changes/complete-taxa-frontend-migration/evidence/g5/`.
    The harness itself does NOT flip G5; it records `blocked` or
    `ready` and leaves the gate flip to the apply worker per
    `tasks.md` §Cutover activation sequence step 5.
  - `openspec/changes/complete-taxa-frontend-migration/evidence/g5/
    .gitkeep` (new) tracks the versioned evidence directory.

- **Strict-TDD evidence** (`tests/test_hydration_timing.py`):
  - 22 tests pass: 11 pre-existing + 11 new Phase 6a tests covering
    back-compat, baseline/candidate report, fail-closed regression
    detection, JSON report output, flag-misuse, reconstruction
    harness fail-closed contract, g5_close.sh existence + executability,
    evidence directory versioned marker, and the environmental-blocker
    status.json contract. Captured fixture numbers used by the new tests
    are schema-correct test inputs, NOT G5 evidence.
  - Triangulation probe (19/19 PASS): identical inputs, improvement,
    regression on `initial_paint` only, regression on
    `interaction_latency` only, malformed baseline JSON,
    schema-violating baseline, missing baseline file, positional+flag
    usage error, no-args usage error, reconstruction without
    Playwright, and `g5_close.sh` environmental-blocker status.json.

- **Environmental blocker (this attempt)**: the apply worker's Python
  environment does NOT have Playwright installed
  (`python3 -c "import playwright"` raises `ModuleNotFoundError`). The
  reconstruction script therefore emits the fail-closed placeholder
  and `g5_close.sh` records G5 as `blocked` with the blocker field:
  `playwright Python package is not importable (playwright); install
  with \`pip install -r requirements-dev.txt\` and \`playwright
  install chromium\`.`
- **G5 NOT flipped**: per the fail-closed contract, the gate stays
  `unreproducible — legacy baseline not on disk` (the §Status footer)
  until both preconditions are satisfied: a real
  `web/dist/evidence-baseline.json` with `source: "captured"` AND a
  baseline-vs-candidate comparison that exits `0`. The captured
  `evidence/g5/status.json` from this attempt is the audit trail.

    - **No production cutover, no web restoration, no backend / ETL /
      extension changes, no commit, no push.** The Phase 6a footprint is
      limited to the allowed edit surfaces listed in the delegated task.

### 2026-09-05 — Phase 6a attempt: candidate capture extended; legacy baseline REAL; build failed closed (G5 NOT flipped)

- **Harness extension (this attempt)**:
  - `scripts/capture_hydration_candidate.py` (new, executable) is the
    minimal Phase 6a extension that closes the candidate half of the
    G5 closure. It starts an in-process local static HTTP server that
    serves the React candidate build (`out/`) on a kernel-assigned
    loopback port, drives Playwright + Chromium against it, and emits
    `out/hydration-candidate.json` whose schema is identical to the
    legacy baseline pinned by `tests/test_hydration_timing.py`.
    The static server is torn down on every exit path (success,
    failure, exception, Ctrl-C); no listener leaks between runs.
    The harness is fail-closed: any failure path (missing build_dir,
    missing `index.html`, Playwright import failure, Chromium
    probe failure, server bind failure, capture exception) writes a
    schema-conformant placeholder with `source: "unavailable"` plus
    a `blocker` field naming the failure mode, then exits non-zero.
    The harness NEVER invents candidate numbers.
  - `scripts/g5_close.sh` (extended) now invokes the candidate capture
    as Step 2 of four when `out/` exists but `out/hydration-candidate.json`
    is missing; the existing baseline reconstruction, comparison,
    and verdict-recording steps are preserved. Step 2 is gated on
    `--build-dir` (env `G5_BUILD_DIR`, default `out/`) and is skipped
    if `out/` is absent. The harness STILL does NOT flip G5; it records
    `blocked` or `ready` and leaves the gate flip to the apply worker.
  - `tests/test_hydration_timing.py` (extended):
    - The pre-existing `monkeypatch` approach to hide playwright from
      the subprocess is fundamentally broken (the parent-process patch
      does not propagate to a fresh subprocess); the test was failing
      now that playwright IS installed. Replaced with a poisoned
      `PYTHONPATH` rig (a `playwright.py` shadow module that raises
      `ImportError`) plus `PYTHONNOUSERSITE=1` so the
      fail-closed contract is testable in both states.
    - Three new tests cover the candidate capture path:
      `test_capture_hydration_candidate_script_exists`,
      `test_capture_hydration_candidate_fails_closed_without_playwright`,
      `test_capture_hydration_candidate_fails_closed_without_build_dir`,
      plus
      `test_g5_close_sh_writes_candidate_source_in_status` for the
      new Step 2 status-record contract.

- **Strict-TDD evidence** (`tests/test_hydration_timing.py`):
  - **29 tests pass** (26 prior + 3 candidate-path tests; the broken
    monkeypatch test was fixed in-place by replacing it with the
    poisoned-PYTHONPATH rig, not by adding a new test). Captured
    fixture numbers used by the new tests are schema-correct test
    inputs, NOT G5 evidence.
  - Triangulation probes (all PASS): identical inputs, improvement,
    regression on `initial_paint` only, regression on
    `interaction_latency` only, malformed baseline JSON,
    schema-violating baseline, missing baseline file, positional+flag
    usage error, no-args usage error, reconstruction without
    Playwright (legacy), reconstruction with a missing build_dir
    (legacy), candidate capture without Playwright, candidate
    capture with a missing build_dir, and `g5_close.sh`
    environmental-blocker status.json.

- **Real legacy baseline captured (this attempt)**: the apply
  worker's Python environment now has Playwright 1.62.0 installed
  (system site-packages), so the legacy baseline capture in
  `reconstruct_hydration_baseline.py` succeeds against the frozen
  fixture and emits a real artifact:
  `web/dist/evidence-baseline.json` carries `source: "captured"`,
  `first_paint_ms: 1.0`, `dom_content_loaded_ms: 15.0`,
  `tree_first_paint_ms: 1.0`,
  `tree_first_interactive_ms: 15.0`, `console_warnings: []`,
  `fixture_web_root: tools/g3-legacy-fixture/web`. The previously
  blocking environmental condition (no Playwright) is resolved.

- **`npm ci` + `npm run build:web` outcome (this attempt)**: the
  React candidate build FAILS to produce an `out/` directory because
  of pre-existing TypeScript errors in
  `src/modules/research/presentation/{FileExplorer,FileViewer,
  SearchTab}.tsx` (the 5b research module that the positions 1-12
  chain landed with). The build exits `1` after `Failed to type
  check.` with seven TS errors (`TS2724` missing
  `WireFileNode` export, `TS7006` implicit any,
  `TS2739` `TreeRowProps` shape, `TS6133` unused variable,
  `TS2322` iframe `type` attribute, `TS2322` `Node | null`, and
  `TS2322` `readonly Engine[]` `category` mismatch). The errors
  are scoped to PR 5b, NOT to the Phase 6a harness; per the
  delegation contract ("Do not modify production app behavior,
  backend APIs, fixtures") they cannot be patched here. The build
  does not produce `out/index.html` (or any HTML), so the candidate
  capture cannot run.

- **`g5_close.sh` outcome (this attempt)**: the runtime harness
  exits `2` (precondition not met) because `out/` is absent.
  Captured `evidence/g5/status.json` records:
  - `gate: "G5"`, `status: "blocked"`,
  - `baseline_source: "captured"` (legacy baseline IS real),
  - `baseline_path: web/dist/evidence-baseline.json`,
  - `candidate_path: null`,
  - `regression: null`,
  - `blocker: "no candidate artifact available; the positions 1-12-landed candidate build has not yet been captured by the apply worker. Run the candidate capture (out/hydration-candidate.json) and re-run scripts/g5_close.sh."`
  The harness's exit code reflects the verdict (non-zero) so the
  apply worker can chain on it. The blocker is the candidate build,
  not Playwright or any other environmental condition.

- **G5 NOT flipped**: per the fail-closed contract, the gate stays
  blocked. The blocker is now narrower than the prior attempt: the
  legacy baseline IS captured and reproducible; the only remaining
  precondition is a candidate build that the current source tree
  cannot produce until PR 5b's TypeScript errors are resolved (out
  of Phase 6a scope). The §Status footer below reflects the new
  state without flipping G5 to PASS.

- **§Status footer update**: `G5: blocked — baseline captured; candidate build failed (PR 5b TS errors)` (was: `G5: unreproducible — legacy baseline not on disk`). No other footer flips.

    - **No production cutover, no web restoration, no backend / ETL /
      extension changes, no commit, no push.** The Phase 6a footprint
      is limited to the allowed edit surfaces listed in the delegated
      task. The candidate capture script lives entirely inside
      `scripts/` + `tests/`; the React app source under `src/`,
      `next.config.mjs`, `package.json`, and the legacy fixture under
      `tools/g3-legacy-fixture/web/` are unchanged.

    ### 2026-09-06 — Phase 6a re-baseline: one run reported ready, but comparable real captures are unstable; G5 remains blocked

    - **Re-baseline scope (this attempt)**: the previous Phase 6a
      harness was partial — the legacy baseline ran over ``file://``
      with a single sample, and the React candidate ran over HTTP with
      a single sample. Apples-to-apples comparison was impossible.
      This attempt deepens both legs so the comparison is meaningful:
      - **`scripts/reconstruct_hydration_baseline.py`** now serves the
        frozen G3 fixture (`tools/g3-legacy-fixture/web/`) via an
        in-process loopback HTTP server (mirror of the candidate's
        contract — ``file://`` navigation is forbidden because it
        would diverge from the candidate's HTTP origin and disable
        ``fetch`` + ES-module loading for the React build). Captures
        1 warm-up + 5 retained samples per metric by default
        (``--samples-retained 5`` / ``--warmup-count 1``), reduces
        each retained array to its empirical median via
        ``statistics.median``, and writes a multi-sample artifact
        with `samples`, `warmup_samples`, `median`, `samples_retained`,
        `warmup_count`, and `origin` (the loopback URL the capture
        was driven against). The legacy back-compat single-point
        fields (`server_shell` / `client_render`) are populated with
        the median values verbatim so consumers that don't yet
        understand the multi-sample schema keep working.
      - **`scripts/capture_hydration_candidate.py`** mirrors the same
        multi-sample + HTTP + median contract for the React build
        served out of `out/`. Same default CLI flags.
      - **`scripts/measure_hydration.py`** validator accepts the new
        multi-sample fields (and rejects `< 3` retained samples so the
        variance-reduction contract is enforced). The comparison
        prefers `median.client_render.*` over the legacy back-compat
        `client_render.*` values; a mixed scenario (one artifact with
        median, one without) uses the appropriate source per leg.
        The `--report-out` JSON now carries `baseline_median_*` /
        `candidate_median_*` / `baseline_samples_retained` /
        `candidate_samples_retained` / `baseline_warmup_count` /
        `candidate_warmup_count` / `baseline_origin` /
        `candidate_origin` / `baseline.samples.*` /
        `candidate.samples.*` so a reviewer can audit the variance
        reduction from the report alone.

    - **Strict-TDD evidence** (`tests/test_hydration_timing.py`):
      - **42 tests pass** (29 prior + 13 new Phase 6a re-baseline
        tests). All `RED` tests were observed to fail against the
        pre-revision single-sample harness before the GREEN
        implementation landed:
        - `test_measure_hydration_accepts_multi_sample_artifact`
          (schema contract);
        - `test_measure_hydration_rejects_at_least_3_samples_violation`
          (variance-reduction guard);
        - `test_measure_hydration_comparison_uses_median_when_present`
          (median-precedence contract);
        - `test_measure_hydration_backcompat_single_point_artifact_no_median`
          (single-point back-compat);
        - `test_measure_hydration_mixed_single_and_multi_uses_appropriate_metric`
          (mixed scenario);
        - `test_measure_hydration_regression_report_includes_median_metadata`
          (report enrichment);
        - `test_reconstruct_hydration_baseline_uses_http_server_not_file_uri`
          (HTTP origin contract for the baseline);
        - `test_reconstruct_hydration_baseline_runs_multiple_samples`
          (multi-sample + median + warmup references in source);
        - `test_capture_hydration_candidate_runs_multiple_samples`
          (same for the candidate);
        - `test_reconstruct_hydration_baseline_default_samples_retained_is_5`
          / `test_reconstruct_hydration_baseline_default_warmup_count_is_1`
          / `test_capture_hydration_candidate_default_samples_retained_is_5`
          / `test_capture_hydration_candidate_default_warmup_count_is_1`
          (CLI defaults pinned).
      - Triangulation probes (all PASS): empirical-median correctness
        for both odd-length (5) samples arrays, regression detection
        via median exits 4 fail-closed, mixed single+multi, single-
        point back-compat, multi-sample schema rejection of `< 3`
        retained samples, source-code contracts for HTTP / multi-
        sample / defaults.

    - **`npm run build:web` outcome (this attempt)**: build exits 0;
      `out/index.html` regenerated. The previously-blocking PR 5b
      TypeScript errors are resolved in the current source tree (the
      Tailwind 4 `@theme` parser warning is non-fatal and Next 16 /
      Turbopack emits the static export anyway).

    - **Real capture + g5_close outcome (this attempt)**:
      - `scripts/reconstruct_hydration_baseline.py` exits 0
        (Playwright 1.62.0 + Chromium binary both available). The
        produced `web/dist/evidence-baseline.json` carries
        `source: "captured"`, `origin: "http://127.0.0.1:<port>/"`,
        `samples.{server_shell,client_render}.*` (5-element arrays),
        `warmup_samples.*` (1-element arrays), `median.*`,
        `samples_retained: 5`, `warmup_count: 1`.
      - `scripts/capture_hydration_candidate.py` exits 0. The
        produced `out/hydration-candidate.json` carries the same
        multi-sample schema (5 retained samples per metric, 1 warm-up,
        HTTP origin).
      - `scripts/g5_close.sh` exits 0; the comparison reports:
        - `initial_paint_delta_pct: 0.0` (baseline median =
          candidate median — both legs render the static shell in
          under 1ms; the variance reduction collapses the previous
          single-sample noise to a tie).
        - `interaction_latency_delta_pct: -25.0%` (negative delta =
          improvement: candidate median < baseline median).
        - `regression: false`, `regressing_axes: []`.
      - At that moment, `evidence/g5/status.json` recorded
        `status: "ready"`, `regression: false`, and no `blocker`
        field. This is transient evidence only, not a G5 closure: the
        latest comparable evidence supersedes it and remains
        `status: "blocked"`, `regression: true`, with a `blocker`
        naming the regression.
      - `evidence/g5/regression-report.json` carries the full
        multi-sample contract: median values per leg, sample counts
        (5 / 5), warmup counts (1 / 1), HTTP origins (loopback URLs
        from each capture run), and the raw retained samples for
        both `tree_first_paint_ms` and `tree_first_interactive_ms`
        per leg.

    - **Harness verdict / supersession**: The first multi-sample
      run exited 0 and transiently produced a ready verdict. Across
      three comparable real-capture runs, verdicts were `ready`,
      `blocked`, and `blocked`; the 0–4 ms metrics moved by ±1 ms,
      so the percentage/median comparison is not reproducible. The
      latest `evidence/g5/status.json` captured at
      `2026-09-06T01:37:38Z` is `blocked` (baseline medians
      0.0/3.0 ms, candidate medians 1.0/4.0 ms; regression on
      `initial_paint` and `interaction_latency`; comparison exit 4).
      The `ready` result is audit history only: no G5 PASS, status
      flip, or cutover authorization is granted.

    - **Current §Pre-flight gate table update**: `G5 (hydration
      baseline)`: `blocked — latest comparable capture exits 4 with
      regression; three runs were ready / blocked / blocked; ±1 ms
      variance at 0–4 ms makes the current comparison
      non-reproducible. No G5 PASS is authorized until a new
      observable metric and versioned absolute tolerance/protocol
      are approved.` (The prior `ready` wording is superseded by
      this current disposition.)
    - **Current §Status footer update**: `G5: blocked — latest
      comparable real capture regressed (ready / blocked / blocked
      across three runs; ±1 ms at 0–4 ms); no PASS or closure
      authorized.` No G5 footer flip is made.
    - **Methodological exception request**: `design.md` §"G5 —
      hydration baseline" records the request for a new observable
      hydration metric and a versioned absolute tolerance/protocol.
      The request is **NOT approval**, does not waive the current
      ≤0 % threshold, and does not grant G5 PASS or closure.

- **No production cutover, no web restoration, no backend / ETL /
          extension changes, no commit, no push.** The Phase 6a
          re-baseline footprint is limited to the allowed edit surfaces
          listed in the delegated task. The legacy fixture under
          `tools/g3-legacy-fixture/web/` stays byte-identical frozen
          (the HTTP server reads it but does not modify it). The React
          app source under `src/`, `next.config.mjs`, `package.json`,
          and the build artifact under `out/` are owned by the upstream
          chain (positions 1–9 / 1–12); this attempt only consumes the
          `out/` artifact produced by `npm run build:web` and writes the
          `out/hydration-candidate.json` measurement artifact next to
          it.

    ### 2026-09-06 — Phase 6b: G6 rehearsal script + activated working-copy manifest authored; controlled rehearsal SUCCEEDED — `cutover-rehearsal.json` captured at `2026-09-06T15:10:54Z` (G6 PASS recorded)

    - **Rehearsal harness shipped**:
      - `scripts/rehearse_cutover.py` (new, executable, ~470 LoC):
        dry-runs the atomic cutover unit end-to-end against an isolated
        clone (or against the on-disk working-copy manifest for the
        real rehearsal); runs the G3 Tier-2 verifier
        (`scripts/verify_consumers.py`) through a shared
        `run_g3_tier2(manifest_path, out_dir)` helper (no edits to
        `verify_consumers.py` were required — its existing public
        `main(argv)` interface is sufficient); emits the versioned
        `cutover-rehearsal.json` ONLY on a COMPLETE rehearsal; and
        updates `apply-progress.md` G6 footer ONLY if the REAL
        rehearsal (no test-mode flags) exits 0. Exit codes: `0` OK,
        `1` usage, `2` subset-only fail-closed, `3` G3 Tier-2 verifier
        failed, `4` silent-fallback-path detection failed closed.
      - `scripts/rehearse_cutover.py::run_g3_tier2(manifest_path,
        out_dir)` is the SHARED code path: both the rehearsal and
        the apply worker's PR 3e verification call it. The helper
        imports `scripts.verify_consumers` and delegates to
        `verify_consumers.main(argv)`; the call is in-process
        (no subprocess fork), so the helper inherits every existing
        PR #109 + #111 + #115 + #116 contract (fail-closed schema,
        `--serve` lifecycle, `--fixture-web-root` isolated-port
        invariant, HTTP-shape enforcement via
        `tools/g3-legacy-fixture/scripts/check_http_status.py`).
      - `scripts/rehearse_cutover.py::detect_subset_only(manifest)`
        classifies the manifest as `None` (fully activated Tier-2) or
        one of `web_dir_only` / `consumers_only` / `makefile_only` /
        `artifact_only` (subset-only, forbidden); the four
        cutover-unit subsets map to specific failure signatures in
        the manifest's `replacement.path` vs `current_path`
        comparison (Tier-1 legacy pre-cut selection has
        `replacement.path == current_path`; Tier-2 post-cut
        activation has `replacement.path != current_path`).
      - `scripts/rehearse_cutover.py::scan_silent_fallback_paths(repo_root)`
        scans `Makefile` + `api/server.py` for any code line (not a
        comment) that carries a fallback signature
        (`WEB_DIR = ... "web/..."` reassignment in
        `api/server.py`, or a `web/` reference combined with a
        fallback construct in `Makefile`). The current source tree
        returns `[]`; the scan would surface any future drift that
        reintroduces a silent fallback to the legacy runtime.
      - `scripts/rehearse_cutover.py::emit_rehearsal_artifact(...)`
        writes `cutover-rehearsal.json` atomically (no dot-prefixed
        temp leftover) with the G6 contract: `gate: "G6"`,
        `status: "ready" | "blocked"`,
        `activation_complete: <bool>`, `unselected_count: <int>`,
        `silent_fallback_paths: <list>`, `g3_tier2_exit_code: <int>`,
        `consumer_readiness: <dict | null>`,
        `captured_at: <ISO-8601 UTC>`.
      - `scripts/rehearse_cutover.py::update_apply_progress_g6(...)`
        flips the `G6 (cutover rehearsal)` footer line in
        `apply-progress.md` from the "blocked — ..." wording to
        "PASS recorded" ONLY on real-rehearsal exit 0 with no silent
        fallback paths. The flip is conservative: it scans for the
        current footer line via regex, refuses to flip if the footer
        already says "PASS recorded" (idempotent), and refuses to
        touch any other line. Test mode (`--no-update-apply-progress`),
        subset-only mode, G3 failure, and silent-fallback detection
        ALL skip this path entirely.

    - **Activated working-copy manifest shipped** (Tier-2 flip on the
      WORKING copy only; predecessor stays byte-identical frozen):
      - `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
        (new) is the Tier-2 atomic-cut activation record: every
        one of the 26 §3.1 consumers now carries
        `replacement.path != current_path` (post-cut build artifact
        under `out/...` or the canonical React location), every
        `activation_status` is `selected`, every `replacement.status`
        is `selected`, the `selection_invariants` block records the
        atomic-cut + rollback invariants, and the
        `verifier_contract_summary` block documents the Tier-2
        threshold (`activation_complete: true`,
        `unselected_count: 0`, `silent_fallback_paths: []`,
        G3 Tier-2 verifier exit 0).
      - The predecessor `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
        stays byte-identical frozen (verified by `git show HEAD:...`
        vs the working-tree bytes — Phase 6b does not amend the
        predecessor, only the working copy is flipped to Tier-2).
      - `selection_invariants.tier2_activation_record_status` explicitly
        documents what Tier-2 DOES NOT claim: it does NOT claim G6
        PASS, it does NOT claim the rehearsal has run end-to-end, it
        does NOT claim the candidate build is real, it does NOT enable
        `make api` activation under Next.js, it does NOT relax
        G2/G4/G5/G6 blocking language, it does NOT commit or push any
        source / tests / scripts / config / Makefile / extension / API.

    - **Evidence directory marker shipped**:
      - `openspec/changes/complete-taxa-frontend-migration/evidence/g6/.gitkeep`
        (new) tracks the versioned G6 evidence directory. The
        `cutover-rehearsal.json` artifact is NOT pre-created; it is
        emitted by the rehearsal script ONLY on a COMPLETE rehearsal
        (full Tier-2 activation, G3 Tier-2 verifier exit 0, zero silent
        fallback paths).

    - **Strict-TDD evidence** (`tests/test_rehearse_cutover.py`,
      NEW file; 20 tests, ALL PASS):
      - **Module structure**: script exists, is importable as a Python
        module, exposes `run_g3_tier2(manifest_path, out_dir, ...)`
        shared helper (signature pinned), and the helper
        in-process-delegates to `scripts.verify_consumers.main(argv)`.
      - **Happy path**: synthetic fully-activated Tier-2 manifest
        with benign `:` commands drives the rehearsal to exit 0;
        `cutover-rehearsal.json` is atomically emitted with the
        full G6 contract schema (`gate`, `status`, `captured_at`,
        `manifest_path`, `activation_complete`, `unselected_count`,
        `silent_fallback_paths`, `g3_tier2_exit_code`,
        `consumer_readiness`); `CONSUMER-READINESS.json` is also
        emitted by the shared G3 verifier under the out dir; zero
        dot-prefixed temp leftovers from atomic emit.
      - **Silent-fallback-path triangulation**: the
        `scan_silent_fallback_paths` helper reports `[]` against the
        actual repository source (clean tree); a synthetic fake repo
        containing a real silent-fallback signature (a `WEB_DIR = ...
        'web'` reassignment in `api/server.py`, or a `web/`-targeting
        Makefile target with a fallback construct) makes the
        rehearsal fail closed with `EXIT_REHEARSAL = 4` and surfaces
        the detected fallback path in stderr.
      - **Subset-only fail-closed invariant** (parametrized over the
        four cutover-unit subsets): for each of
        `web_dir_only` / `consumers_only` / `makefile_only` /
        `artifact_only`, the rehearsal exits `EXIT_SUBSET_ONLY = 2`,
        names the forbidden subset in stderr, does NOT emit
        `cutover-rehearsal.json`, and does NOT modify
        `apply-progress.md`. Triangulation confirms subset-only
        rehearsals short-circuit BEFORE invoking `run_g3_tier2` (the
        G3 verifier never runs on a subset; only a COMPLETE rehearsal
        exercises it).
      - **apply-progress.md update contract**: test mode
        (`--no-update-apply-progress`) never touches
        `apply-progress.md`; G3-failure never touches
        `apply-progress.md`; subset-only never touches
        `apply-progress.md`; silent-fallback detection never
        touches `apply-progress.md`. Real-mode passing rehearsal
        (against a copy of the production `apply-progress.md`) DOES
        flip the G6 footer from "blocked — ..." to "PASS recorded".
      - **Working-copy manifest contract**: 26 §3.1 consumers, every
        `activation_status == 'selected'`, every
        `replacement.status == 'selected'`, every
        `replacement.path != current_path` (Tier-2 invariant).
      - **Predecessor remains byte-identical frozen**: the
        predecessor `cutover-manifest.json` bytes equal `git show
        HEAD:...` (Phase 6b does not amend the predecessor).
      - **Argument contract**: invalid `--subset` value is rejected
        (argparse invalid-choice error surfaces in stderr);
        missing manifest is rejected (`EXIT_USAGE = 1`); invalid
        manifest JSON is rejected (`EXIT_USAGE = 1`).

- **Real-rehearsal outcome (this attempt)**:
          - `python3 scripts/rehearse_cutover.py --manifest
            openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json
            --out <tmp-out> --repo-root .` exits `0` (`EXIT_OK`).
            The G6 contract is satisfied end-to-end:
            - **Controlled port** (NOT the ambient FastAPI 8765):
              the rehearsal's `_pick_free_port` returned the
              kernel-assigned loopback port `55637`, which the
              `ControlledStaticServer._spawn` bound via
              `python -m http.server 55637 --directory
              <fixture-web-root>`. The production FastAPI mount on
              `127.0.0.1:8765` was never bound by the rehearsal.
            - **Subset-only check passes**: `detect_subset_only`
              returns `None` (full Tier-2 activation); every one of
              the 26 §3.1 consumers carries
              `replacement.path != current_path`.
            - **Silent-fallback scan clean**: `scan_silent_fallback_paths`
              against the on-disk `Makefile` + `api/server.py`
              returns `[]` (no `WEB_DIR = ... "web/..."`
              reassignment, no `web/`-targeting Makefile fallback
              construct).
            - **G3 Tier-2 verifier passes**: `run_g3_tier2` invokes
              `scripts.verify_consumers.main(argv)` in-process
              against the port-rewritten tmp manifest copy; the
              verifier emits `CONSUMER-READINESS.json` under the
              supplied `--out` dir and exits `0`.
          - `cutover-rehearsal.json` is atomically emitted at
            `openspec/changes/complete-taxa-frontend-migration/evidence/g6/cutover-rehearsal.json`
            with the verified G6 contract: `gate: "G6"`,
            `status: "ready"`, `activation_complete: true`,
            `unselected_count: 0`, `silent_fallback_paths: []`,
            `g3_tier2_exit_code: 0`, `consumer_readiness.all_selected:
            true` (all 26 consumers present, every `replacement.status
            == "selected"`, every `activation_status == "selected"`),
            `captured_at: "2026-09-06T15:10:54Z"`. The tmp
            port-rewritten manifest copy under `/tmp` is removed by
            the rehearsal's `finally` block.
          - The atomic cutover unit + rollback unit are consistent:
            no subset-only subset detected, no silent fallback path
            detected, every Tier-2 consumer is selected. The §Status
            footer in `apply-progress.md` is flipped from
            "blocked — ..." to "PASS recorded" via
            `update_apply_progress_g6(...)` (idempotent — a
            subsequent call is a no-op).

- **§Pre-flight gate table update**: `G6 (cutover rehearsal)`:
      `PASS recorded — cutover-rehearsal.json captured at
      2026-09-06T15:10:54Z` (controlled port 55637 — never the
      ambient FastAPI 8765; activation_complete true; all 26
      §3.1 consumers selected; unselected_count 0;
      silent_fallback_paths []; g3_tier2_exit_code 0); atomic
      cutover unit + rollback unit consistent. (was:
      `blocked — verifier authored; rehearsal fails closed
      against the current source tree because the React
      candidate (out/) is not yet built; close in a follow-up
      apply attempt after npm run build:web succeeds`; the
      `verifier not authored` wording pre-dated this entry.)
- **§Status footer update**: `G6 (cutover rehearsal)` flipped to
      `PASS recorded — cutover-rehearsal.json captured at
      2026-09-06T15:10:54Z (see
      openspec/changes/complete-taxa-frontend-migration/evidence/g6/cutover-rehearsal.json);
      atomic cutover unit + rollback unit consistent; 0 silent
      fallback paths detected; apply worker may proceed to PR
      3e.` The flip is driven by
      `scripts/rehearse_cutover.py::update_apply_progress_g6(...)`
      on a real-rehearsal exit 0; the contract pins the flip to
      a real-rehearsal exit 0 with no silent fallback paths.
      G5 wording in the §Status footer is preserved verbatim
      (`blocked — real captures are not reproducible under the
      current protocol`); the G6 PASS flip does NOT relax G5
      blocking language.
- **`cutover-rehearsal.json` emitted**: at
      `openspec/changes/complete-taxa-frontend-migration/evidence/g6/cutover-rehearsal.json`,
      captured at `2026-09-06T15:10:54Z`, schema-conformant to the
      G6 contract (`gate`, `status`, `captured_at`,
      `manifest_path`, `activation_complete`, `unselected_count`,
      `silent_fallback_paths`, `g3_tier2_exit_code`,
      `consumer_readiness`). The artifact is the verified
      authoritative evidence for the G6 PASS record above; it is
      NOT pre-created and is emitted ONLY on a COMPLETE
      rehearsal (full Tier-2 activation, G3 Tier-2 verifier
      exit 0, zero silent fallback paths).

        - **No production cutover, no web restoration, no backend / ETL /
          extension changes, no commit, no push.** The Phase 6b footprint
          is limited to the allowed edit surfaces listed in the
          delegated task: `scripts/rehearse_cutover.py`,
          `tests/test_rehearse_cutover.py`,
          `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`,
          `openspec/changes/complete-taxa-frontend-migration/evidence/g6/.gitkeep`,
          `openspec/changes/complete-taxa-frontend-migration/apply-progress.md`
          (§Change log delta + G6 §Pre-flight gate + G6 §Status footer
          update). The legacy fixture under
          `tools/g3-legacy-fixture/web/`, the React app source under
          `src/`, `next.config.mjs`, `package.json`, the build
          artifact under `out/`, the predecessor
          `openspec/changes/migrate-nextjs-tailwind4/**`, the FastAPI
          `api/server.py`, and the Chrome extension under
          `extension/**` are NOT modified by this attempt. The G3
          Tier-2 verifier `scripts/verify_consumers.py` is NOT edited
          (its existing public `main(argv)` interface is sufficient;
          the orchestrator contract requires reporting a blocker
          rather than expanding scope if the public interface made
          sharing Tier-2 invocation impossible — it does not, so no
          blocker is reported).
