# Apply Progress: complete-taxa-frontend-migration

> Hybrid-mode persistence artifact. Mirrors the structured
> apply-progress in Engram (`topic_key` =
> `sdd/complete-taxa-frontend-migration/apply-progress`).
>
> **Initial state (2026-09-02)**: every sub-PR under Approach A
> (`tasks.md` Phases 3a–6c + PR 3e) is **reconstruction pending**.
> No child PR has been opened yet. The tracker branch
> `docs/complete-taxa-frontend-migration-plan` already exists and
> holds the planning artifacts; it is the **only** branch that will
> target `develop`, and it stays **draft / no-merge** until the whole
> chain is reviewed and integrated. Nothing has been delivered to
> `develop` yet. The pre-flight
> gate table (§Pre-flight gate for PR 3e) records the carried
> status of G1, G2, G3 Tier-1 (all PASS recorded from the
> predecessor) and the closure status of G4, G5, G6 (all three
> deferred to Phase 6 validation work).
>
> **Approach A is FINAL** (locked 2026-09-02, recorded in
> `design.md::§1`); no override path is open. **Predecessor
> `migrate-nextjs-tailwind4/` is frozen** — every sub-PR in this
> change MUST leave `openspec/changes/migrate-nextjs-tailwind4/**`
> byte-identical (branch-protection rejects any PR that edits
> it).

---

## Reconstruction State

| Sub-PR | Scope | LoC budget (authored) | Source files | Status |
|--------|-------|-----------------------|--------------|--------|
| PR 3a | App Router entry + TS toolchain | ~175 | `src/app/{layout,page}.tsx` + `next.config.mjs` + `tests/test_app_shell_render.py` (new) | reconstruction pending |
| PR 3b | Design tokens + Tailwind 4 `@theme` | ~230 | `src/app/globals.css` (new, `@import "tailwindcss"` + `@theme` + `@layer base`) + `src/modules/design-system/{infrastructure/index.ts,presentation/Icon.tsx,presentation/Button.tsx}` (new) + `tests/test_tailwind_4_parity.py` (new) + `tests/test_design_system_purity.py` (new) | reconstruction pending |
| PR 3c | Build pipeline + runtime check | ~180 | `Makefile` (modified, `api:` + `css:` targets rewritten; legacy `make css` Tailwind-3.4 step retired) + `scripts/check-runtime.mjs` (new, Node ≥ 20.9.0 enforcement) + `package.json` (modified, `next@^16` / `react@^19` / `tailwindcss@^4` / TS toolchain / `engines.node`) + `tests/test_make_api_build.py` (new) | reconstruction pending |
| PR 3d | `WEB_DIR` repoint + AC-21 reader | ~190 | `api/server.py` (modified, 1-line delta at line 54 + minimal `next/font` preload middleware) + `src/data/search-engines.js` (new, byte copy of `web/search_urls.js` with `SEARCH_ENGINES` named export) + `tests/test_smoke.py` (modified, `open()` path update) + `tests/test_static_mount.py` (new) | reconstruction pending |
| PR 4a | Typed store + 4 read + 4 write | ~180 | `src/modules/browser-state/{domain/keys.ts,infrastructure/store.ts,index.ts}` (new) + `tests/test_browser_state_keys.py` (new) | reconstruction pending |
| PR 4b | Hydration guard + Playwright zero-warnings | ~90 | `src/modules/app-shell/{presentation/AppShell.tsx,infrastructure/page-chrome.tsx}` (new) + `tests/test_hydration_console.py` (new, Playwright) | reconstruction pending |
| PR 5a | Taxonomy module port | ~280 | `src/modules/taxonomy/{domain/taxon.ts,infrastructure/api.ts,application/useTaxonTree.ts,presentation/{Tree,DetailPanel,Breadcrumb}.tsx}` (new + extension) + `tests/test_taxonomy_infra.py` (new) | reconstruction pending |
| PR 5b | Research module port + CDN pin | ~360 | `src/modules/research/{domain/{research-file,engine,file-node}.ts,infrastructure/{api,search-engines}.{ts,js},application/{useFileExplorer,useFileViewer}.ts,presentation/{FileExplorer,FileViewer,RawTableTreeTabs,MetaStrip,BreadcrumbPanel,Banners}.tsx}` (new) + `tests/test_research_infra.py` (new) | reconstruction pending |
| PR 5c | E2E selectors + `data-*` contract + delete legacy | ~200 | `tests/test_e2e_file_explorer.py` (modified, DOM selector update) + `tests/test_web_toggle.py` (modified, theme toggle update) + `tests/test_evidence_baseline.py` (modified, legacy roster assertion flips to "absent") + `web/{index.html,index.css}` deletion + `web/{app,state,api,tree,breadcrumb,detail,nav,dom,banner,help,keymap,settings,search,file_explorer,file_viewer,format,search_urls}.js` deletion (18 files) + `tailwind.config.js` deletion + `web/dist/tailwind.css` no longer tracked | reconstruction pending |
| Phase 6a | G5 hydration baseline closure | ~50 (mostly measurement) | `scripts/reconstruct_hydration_baseline.py` (new) + `scripts/g5_close.sh` (new) + `web/dist/evidence-baseline.json` (regenerated, schema-pinned by `tests/test_hydration_timing.py`) + `apply-progress.md` §Change log delta | reconstruction pending (validation work after candidate path) |
| Phase 6b | G6 cutover rehearsal | ~120 | `scripts/rehearse_cutover.py` (new) + `tests/test_rehearse_cutover.py` (new) + `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json` (working copy; predecessor copy stays byte-identical frozen) + `apply-progress.md` §Change log delta | reconstruction pending (validation work after candidate path) |
| Phase 6c | G4 Playwright + Lighthouse parity | ~20 (mostly measurement) | `scripts/g4_measure.sh` (new) + `out/g4-parity-report.json` (Playwright + Lighthouse artifact) + `apply-progress.md` §Change log delta | reconstruction pending (validation work after candidate path) |
| PR 3e | Atomic cutover | ~120 (mostly `apply-progress.md` delta) | `apply-progress.md` (gate-status footer flip + change-log entry) + re-runs of `tests/test_verify_consumers.py`, `tests/test_verify_build.py`, `make api`, `make smoke` | reconstruction pending (gated on all six gates green) |

**Sub-PR count**: 13 (4 bootstrap + 2 browser-state + 3 capability
ports + 3 Phase 6 validation + 1 atomic cutover).

**Total authored**: ~2,225 LoC across the 13 sub-PRs. Largest
sub-PR is **5b** at ~360 LoC (under 400-line budget with -40 LoC
headroom; **no `size:exception` required**).

### Reconstruction order (deterministic, sequential along the chain)

```
3a → 3b → 3c → 3d → 4a → 4b → 5a → 5b → 5c → 6a (G5) → 6b (G6) → 6c (G4 measurement) → 3e (atomic cutover, gated)
```

**Chain strategy: `feature-branch-chain`** (user-selected). The
existing `docs/complete-taxa-frontend-migration-plan` branch is the
**tracker**: draft / no-merge, and the **only** PR that targets
`develop`. Child PR 3a targets the tracker; every later child targets
its **immediate predecessor branch**. This supersedes the
`AGENTS.md` §4 direct-to-`develop` default for this change.

| Position | Sub-PR | Branch | Base (PR target) |
|---|---|---|---|
| Tracker | — | `docs/complete-taxa-frontend-migration-plan` | `develop` — **draft / no-merge** |
| 1 / 13 | 3a | `feat/complete-taxa-frontend-migration-01-3a` | `docs/complete-taxa-frontend-migration-plan` (tracker) |
| 2 / 13 | 3b | `feat/complete-taxa-frontend-migration-02-3b` | `feat/complete-taxa-frontend-migration-01-3a` |
| 3 / 13 | 3c | `feat/complete-taxa-frontend-migration-03-3c` | `feat/complete-taxa-frontend-migration-02-3b` |
| 4 / 13 | 3d | `feat/complete-taxa-frontend-migration-04-3d` | `feat/complete-taxa-frontend-migration-03-3c` |
| 5 / 13 | 4a | `feat/complete-taxa-frontend-migration-05-4a` | `feat/complete-taxa-frontend-migration-04-3d` |
| 6 / 13 | 4b | `feat/complete-taxa-frontend-migration-06-4b` | `feat/complete-taxa-frontend-migration-05-4a` |
| 7 / 13 | 5a | `feat/complete-taxa-frontend-migration-07-5a` | `feat/complete-taxa-frontend-migration-06-4b` |
| 8 / 13 | 5b | `feat/complete-taxa-frontend-migration-08-5b` | `feat/complete-taxa-frontend-migration-07-5a` |
| 9 / 13 | 5c | `feat/complete-taxa-frontend-migration-09-5c` | `feat/complete-taxa-frontend-migration-08-5b` |
| 10 / 13 | 6a | `feat/complete-taxa-frontend-migration-10-6a` | `feat/complete-taxa-frontend-migration-09-5c` |
| 11 / 13 | 6b | `feat/complete-taxa-frontend-migration-11-6b` | `feat/complete-taxa-frontend-migration-10-6a` |
| 12 / 13 | 6c | `feat/complete-taxa-frontend-migration-12-6c` | `feat/complete-taxa-frontend-migration-11-6b` |
| 13 / 13 | 3e | `feat/complete-taxa-frontend-migration-13-3e` | `feat/complete-taxa-frontend-migration-12-6c` |

Children merge **in order** into the tracker; as each child merges,
the next is retargeted onto the tracker (GitHub retargets
automatically when the base branch is merged and deleted). The
tracker accumulates the full feature and merges to `develop` only
after PR 3e — the last child — lands.

**Phase 6 (6a, 6b, 6c) is validation work**, not a migration
objective. It runs **after** the complete candidate path (3a–5c)
is green and accumulated on the tracker, and **before** PR 3e can
land. Phase 6 may ship as three chain links (the default:
positions 10 / 11 / 12) or collapse into a single child PR at
position 10, depending on the maintainer's `ask-on-risk` decision;
collapsing shortens the chain without changing the topology (the
batch still targets the PR 5c branch, and PR 3e still targets the
last Phase 6 link). The combined LoC is ~190 authored + ~120
measurement artifact, comfortably under the 400-line budget.

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
  each sub-PR: created fresh from that sub-PR's **base branch** in
  the chain table above — the tracker
  (`docs/complete-taxa-frontend-migration-plan`) for PR 3a, the
  immediate predecessor branch for every later child. Never from
  `origin/develop` directly: a worktree cut from `develop` produces
  a polluted diff. Name pattern:
  `taxa-worktrees/complete-taxa-frontend-migration-<sub-pr-id>`.

### Reconstruction manifest (per sub-PR)

For each sub-PR, the apply worker MUST:

1. Create a new worktree from that sub-PR's **base branch** (see
   the chain table in §Reconstruction order — the tracker for PR 3a,
   the immediate predecessor branch for every later child), named
   `taxa-worktrees/complete-taxa-frontend-migration-<sub-pr-id>`.
2. Copy only the files listed for that sub-PR in `tasks.md`
   §Per-task evidence (`Source files` column above) into the new
   worktree using `cp -p`. No edits on copy.
3. Run the focused test command (see the per-sub-PR task rows in
   `tasks.md` §"Per-task evidence"). It MUST pass before any
   commit.
4. Run the runtime harness (see same table). It MUST exit 0 /
   return the expected output.
5. Conventional Commit with English subject (no AI trailer). PR
   body in Spanish per `AGENTS.md` §Hard Rules: `## Resumen`,
   `## Cambios`, `## Validación`, `## Lo que NO cambió`.
6. Open the PR against that sub-PR's **base branch** (never
   `develop`) via the `branch-pr` skill. Append a `## Chain Context`
   section (Chain / Tracker PR / Position / Base / Depends on /
   Follow-up / Review budget / Starts at / Ends with) plus a
   dependency diagram marking the current PR with `📍`. The Chain
   Context section is **appended** to the repo PR template — it does
   not replace `## Resumen` / `## Cambios` / `## Validación` /
   `## Lo que NO cambió`.
7. Verify chain diff hygiene: `git diff --stat <base-branch>` shows
   **only** this slice's files. A polluted diff is a **base bug** —
   retarget or rebase onto the correct predecessor before review.
8. On green CI: mark that sub-PR's tasks `[x]` in `tasks.md` and
   `tasks-es.md`; prepend a per-sub-PR batch record here and in
   `apply-progress-es.md` (see §Change log below).
9. Merge the child into the tracker, then continue to the next
   sub-PR by repeating from step 1 with a fresh worktree off the
   now-merged predecessor. Keep the tracker PR **draft / no-merge**
   until all 13 children are reviewed and integrated.

### Rollback boundary per sub-PR

Each sub-PR revert removes **only** its own files (see the
`Source files` column above and the per-task `Rollback boundary`
cell in `tasks.md`). No sub-PR touches `api/server.py` route
handlers, the SQLite/WAL logic, the ETL pipeline, or
`extension/manifest.json`. The `api/server.py:54` `WEB_DIR`
repoint lives in PR 3d (atomic with the rest of the cutover's
4-set release per `design.md` §"Atomic cutover unit"); its
rollback boundary is **PR 3e**, not PR 3d alone — PR 3d ships
the repoint, PR 3e is the cutover commit that flips the build
artifact under `out/`. `git revert <pr3e-sha>` is the only
supported full-cutover rollback.

**Rollback under the chain** — two windows:

| Window | State | Rollback |
|---|---|---|
| Before the tracker merges | Nothing is on `develop`; the chain lives only on the tracker branch | Hold or close the tracker PR — `develop` is untouched by construction |
| After the tracker merges | The whole chain lands on `develop` in one integration | `git revert <pr3e-sha>` restores the legacy vanilla build atomically (per `design.md` §"Rollback unit") |

For `<pr3e-sha>` to stay addressable on `develop`, the tracker MUST
merge with a **merge commit** (no squash), so the chain's individual
commits survive integration. If the tracker is squash-merged
instead, the atomic rollback unit becomes the tracker merge itself:
`git revert -m 1 <tracker-merge-sha>`. Either way the rollback is
**one** revert covering the full four-set cutover — **no subset
revert is supported**.

---

## Change log

Apply phase populates this section per-sub-PR. Each entry records
the sub-PR id, the commit hash, the gate flips (if any), and any
size:exception rationale (none expected; the largest sub-PR is 5b
at ~360 LoC, under 400-line budget).

### 2026-09-02 — Initial planning state

- `tasks.md` and `tasks-es.md` authored (this change); `proposal.md`
  / `spec.md` / `design.md` carried verbatim from predecessor.
- `apply-progress.md` and `apply-progress-es.md` initialised with
  the reconstruction state table above; all sub-PRs marked
  **reconstruction pending**.
- G1 PASS recorded (predecessor `design.md::§1`).
- G2 PASS recorded (predecessor `apply-progress.md` 2026-08-30
  entry against Next 16.3.3 / Turbopack clean build).
- G3 Tier-1 PASS recorded (predecessor `apply-progress.md`, PR
  #109 + #111 + #115 + #116, all 26 §3.1 consumers green via
  `scripts/verify_consumers.py`).
- G4 / G5 / G6 closure deferred to Phase 6 (validation work
  after the candidate path).

> (Subsequent per-sub-PR entries appended below by the apply
> worker, one block per sub-PR merge.)

---

## Pre-flight gate for PR 3e (atomic cutover)

The atomic cutover unit (per `design.md` §"Atomic cutover unit")
changes exactly the following in a single release:

1. **`WEB_DIR` constant** at `api/server.py:54` (already repointed
   in Phase 3d; PR 3e flips the build artifact under `out/` from
   the candidate build to the production build with the
   `engines.node >= 20.9.0` runtime check live).
2. **Every active-consumer update** in the predecessor's
   `design.md::§3.1` (already authored by Phase 3d for the AC-21
   reader path; PR 3e flips the remaining 25 §3.1 consumers to
   read from the React component tree instead of the legacy
   `web/*` paths). The flip is the post-cut activation record
   in
   `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
   (working copy; predecessor copy stays frozen).
3. **The `Makefile::api` and `Makefile::web` targets** (already
   rewritten by Phase 3c; PR 3e flips the legacy `make css`
   Tailwind-3.4 step from "regenerate `web/dist/tailwind.css`"
   to "exit 0 no-op" — the Tailwind 4 build lives inside
   `next build`).
4. **The build artifact** — the `out/` directory itself
   (`out/index.html`, `out/_next/static/chunks/**`,
   `out/.next/build-manifest.json`, the error-page classification
   if `404.html` / `500.html` is emitted). The artifact is
   regenerated by the production build at cutover time.

**No subset revert is supported.** PR 3e ships only when every
gate below is PASS:

| Gate | Status (carried / closure planned) | Source |
| --- | --- | --- |
| G1 (single origin) | **PASS recorded** | Predecessor `design.md::§1` |
| G2 (foundation build) | **PASS recorded** against the verified Next 16.3.3 / Turbopack clean build | Predecessor `apply-progress.md` 2026-08-30 entry |
| G3 Tier-1 (consumer readiness, legacy pre-cut) | **PASS recorded** — all 26 §3.1 consumers green via the controlled fixture, `scripts/verify_consumers.py` | Predecessor `apply-progress.md` (PR #109 + #111 + #115 + #116) |
| G4 (Playwright + Lighthouse parity) | **blocked — verifier not authored**; must close in apply phase | Phase 6c — `scripts/g4_measure.sh` against the Phase 5c-landed candidate build |
| G5 (hydration baseline) | **unreproducible — legacy baseline not on disk**; must be reconstructed or replaced during the apply phase | Phase 6a — `scripts/reconstruct_hydration_baseline.py` reads the predecessor's documented numbers from `design.md` §"Migration Evidence Baseline" |
| G6 (cutover rehearsal) | **blocked — verifier not authored**; must close in apply phase | Phase 6b — `scripts/rehearse_cutover.py` dry-runs the atomic cutover unit against the activated working-copy manifest |

**Cutover activation sequence** (when all six gates green):

1. Author the **post-cut activation record** in
   `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
   (the working copy; predecessor
   `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
   stays byte-identical frozen) — flip `activation_status` and
   `replacement.status` to Tier-2 for every one of the 26 §3.1
   consumers.
2. Apply the **atomic cutover unit** — the four-set change in
   one release (per `design.md` §"Atomic cutover unit").
3. Run the G3 Tier-2 verifier against the activated selection;
   `CONSUMER-READINESS.json` exits 0 with
   `activation_complete: true`, `unselected_count: 0`.
4. Run `make smoke` + Playwright + Lighthouse; verify the parity
   checklist (per `design.md` §"Parity / evidence plan").
5. Mark the cutover PR (child 13 / 13, targeting the PR 6c branch)
   ready for review and flip the gate-status footer in §Status below
   from "blocked / unreproducible / blocked" to "PASS recorded".
6. Merge PR 3e into the tracker — the chain is now complete. Take
   `docs/complete-taxa-frontend-migration-plan` **out of draft** and
   merge it to `develop` with a **merge commit** (no squash, so
   `<pr3e-sha>` stays addressable for the atomic rollback). This is
   the single point at which the migration reaches `develop`.

---

## Forecast reconciliation (carried from `tasks.md` §"Forecast reconciliation")

- **3a** ~175 LoC authored; **3b** ~230; **3c** ~180; **3d** ~190;
  **4a** ~180; **4b** ~90; **5a** ~280; **5b** ~360; **5c** ~200;
  **6a** ~50; **6b** ~120; **6c** ~20; **3e** ~120 (mostly
  `apply-progress.md` delta). **Total**: ~2,225 LoC authored
  across 13 sub-PRs.
- Largest sub-PR is **5b** at ~360 LoC, comfortably under the
  **400-line per-PR review budget** with -40 LoC (-10 %)
  headroom. **No `size:exception` required.**
- **Chained PRs recommended**: **Yes** — each sub-PR fits the
  per-PR budget on its own, but the ~2,225-line total and the
  atomic cutover (the feature MUST integrate before it reaches
  `develop`) put this change in the Feature Branch Chain gate.
- **Chain strategy**: **`feature-branch-chain`** (user-selected).
  Tracker `docs/complete-taxa-frontend-migration-plan` is
  draft/no-merge and is the **only** PR targeting `develop`;
  child PR 3a targets the tracker; each later child targets its
  immediate predecessor branch. Supersedes the `AGENTS.md` §4
  direct-to-`develop` default and the predecessor's
  apply-progress precedent for this change.
- **Delivery strategy**: **`ask-on-risk`** (per preflight; no
  risk flag is open — Approach A is FINAL, the predecessor is
  frozen, every sub-PR fits under 400 lines).
- **Decision needed before apply**: **No** (Approach A locked,
  chain strategy known, every sub-PR within budget).

---

## Workload / PR Boundary

- **Mode**: **Feature Branch Chain** — 1 draft/no-merge tracker
  (`docs/complete-taxa-frontend-migration-plan` → `develop`) plus
  13 sequential child PRs (Phase 3 + Phase 4 + Phase 5, followed
  by the Phase 6 validation links, followed by the PR 3e atomic
  cutover as the last child).
- **Total sub-PRs**: **13** (3a, 3b, 3c, 3d, 4a, 4b, 5a, 5b, 5c,
  6a, 6b, 6c, 3e — note 6a, 6b, 6c are validation work after
  the candidate path; 3e is gated on all six gates green).
- **Each sub-PR ≤ 360 LoC authored**; **no** sub-PR exceeds the
  400-line per-PR review budget. **No `size:exception` is
  expected or planned.**
- **Each child PR's base** = its **immediate predecessor branch**
  (the tracker for PR 3a). **Only the tracker targets `develop`,
  and it stays draft / no-merge until the chain completes.**

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Reconstruction sequence interrupted; partial merge of Phase 3 sub-PRs leaves the project in an inconsistent state. | Medium | Each sub-PR's focused test passes independently of subsequent sub-PRs. Under the Feature Branch Chain no partial state can reach `develop`: children accumulate on the draft/no-merge tracker only. A stuck child blocks its successors inside the chain, never `develop`. |
| Predecessor `migrate-nextjs-tailwind4/` directory accidentally edited during reconstruction; source files deviate from the frozen planning history. | High | Predecessor directory is marked read-only at filesystem level; CI / branch-protection rejects any PR that modifies it. Every sub-PR's PR body must include a `## Lo que NO cambió` section confirming the predecessor stayed byte-identical. |
| Phase 6 validation work accidentally generates new `web/**` source, new `api/server.py` route handlers, or new `extension/**` files (violates the "validation only, not migration" contract). | Medium | Phase 6 tasks are constrained to `scripts/*` shims, measurement artifacts in `out/`, and `apply-progress.md` deltas. No `web/**`, `api/server.py` route handlers, or `extension/**` edits are permitted in Phase 6. The 5c.6 deletion lives in PR 5c, NOT in Phase 6. |
| G5 reconstruction produces a baseline that drifts from the predecessor's documented numbers (the predecessor §3.3.5 audit lists the legacy baseline as **unreproducible**). | Medium | `scripts/reconstruct_hydration_baseline.py` reads the documented numbers verbatim from `openspec/changes/migrate-nextjs-tailwind4/design.md` §"Migration Evidence Baseline"; any drift is logged as a design.md risk-register update before G5 can flip. |
| G6 rehearsal fails closed (subset-only dry-run exits non-zero) and blocks the cutover. | Low | The fail-closed invariant is the spec — subset reverts break the SPA shell. PR 3e ships only when the full atomic rehearsal exits 0. |
| G4 measurement exceeds the ≤ 0 % delta budget on initial paint or interaction latency. | Medium | `scripts/g4_measure.sh` records the delta; if it exceeds 0 %, the apply worker writes an exemption request into `design.md` §"Risk register" and the gate stays blocked until a maintainer signs off. |
| Six new sub-PRs (3a–3d, 4a–4b) plus four (5a–5c) plus three validation (6a–6c) plus one cutover (3e) inflates the total PR count the maintainers review. | Low | Each sub-PR ≤ 360 LoC; review focus stays narrow; chain strategy is `feature-branch-chain` per the user's explicit selection, so each child is reviewed against its immediate predecessor and the reviewer never re-reads a landed slice. |
| A child PR is cut from `origin/develop` instead of its chain base, so its diff shows unrelated slices already merged into the tracker. | Medium | Treat a polluted diff as a **base bug**, not a review finding: retarget or rebase onto the immediate predecessor until only the current work unit appears. §Reconstruction manifest step 7 makes `git diff --stat <base-branch>` a per-PR gate. |
| `cutover-manifest.json` working-copy flip (Phase 6b.3) accidentally edits the predecessor's frozen copy instead of the working copy. | High | The flip is written into `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json` (working copy); predecessor `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json` stays byte-identical. The apply worker MUST diff both copies before PR 3e. |

---

## Predecessor freeze contract (binding)

Every sub-PR in Phases 3a–6c and PR 3e MUST satisfy:

- [ ] `git diff --stat origin/develop -- openspec/changes/migrate-nextjs-tailwind4/`
  shows zero changes. <!-- sdd-owner: parent -->
- [ ] `git diff --stat <immediate-base-branch>` shows **only** this
  slice's files (chain diff hygiene; a polluted diff is a base bug —
  retarget or rebase, do not review around it). <!-- sdd-owner: parent -->
- [ ] The PR's branch-protection check rejects any PR that
  modifies `openspec/changes/migrate-nextjs-tailwind4/**`. <!-- sdd-owner: parent -->
- [ ] The PR's CI / lint hook rejects the same. <!-- sdd-owner: parent -->

If a sub-PR accidentally edits the predecessor directory, the
sub-PR is **blocked** and the apply worker must revert the
accidental edit before the PR can merge. There is no
`size:exception` path for predecessor edits.

---

## Status

**Approach A is FINAL** (locked 2026-09-02; recorded in §1 of
`design.md`). G1 PASS recorded; G2 PASS recorded against the
verified Next 16.3.3 / Turbopack clean build; G3 Tier-1 PASS
recorded (all 26 §3.1 consumers green against the legacy pre-cut
runtime via the controlled fixture, `scripts/verify_consumers.py`,
PR #109 + #111 + #115 + #116). G3 Tier-2 (atomic-cut selection)
**NOT PASSED** — gated by G4 + G5 + G6 closure. G4 (Playwright +
Lighthouse parity) **blocked — verifier not authored**; must
close in apply phase via Phase 6c. G5 (hydration baseline)
**unreproducible — legacy baseline not on disk**; must be
reconstructed or replaced during apply phase via Phase 6a. G6
(cutover rehearsal) **blocked — verifier not authored**; must
close in apply phase via Phase 6b. Predecessor
`openspec/changes/migrate-nextjs-tailwind4/**` is **frozen**. No
FastAPI activation in this design pass; the atomic cutover PR 3e
ships only when all six gates are green.

> **Footer (apply phase flips)**: G1: PASS recorded · G2: PASS
> recorded · G3 Tier-1: PASS recorded · G3 Tier-2: NOT PASSED
> (gated) · G4: blocked — verifier not authored · G5:
> unreproducible — legacy baseline not on disk · G6: blocked —
> verifier not authored. Footer flips to PASS recorded for G4 /
> G5 / G6 only after Phase 6 closes and PR 3e ships.

---

## Next step

The **apply phase** (`sdd-apply`) reads `tasks.md` and this
`apply-progress.md`, then executes the reconstruction manifest
(§Reconstruction manifest) sub-PR by sub-PR. Phase 6 validation
work (6a, 6b, 6c) runs after the candidate path (3a–5c) is green
and before PR 3e. The atomic cutover PR 3e ships only when all
six gates are green. The **verify phase** (`sdd-verify`) confirms
the parity checklist (per `design.md` §"Parity / evidence plan")
and the rollback unit (`git revert <pr3e-sha>` restores the
legacy vanilla build atomically). The **archive phase**
(`sdd-archive`) copies each per-domain spec verbatim into
`openspec/specs/{frontend-runtime,design-tokens,browser-state-hydration,frontend-bootstrap,research}/spec.md`
and promotes the modular-architecture spec into the canonical
specs tree.