# Design: Static-Export Probe — Disposable Diagnostic Shell

## Scope of this artifact

This is the **design-only companion** for the Stitch static-export
probe screen already generated for project `11813286795400731874`,
screen `ec543a4cec974c2e82085a5e0406334a`. It captures the approved
disposable diagnostic shell, pins the Stitch identifiers, defines the
audit criteria, and explicitly forbids production linkage or
product-UI reuse. It is a documentation artifact, not a code
artifact: it delivers zero source code, zero tests, zero
configuration, zero build wiring, and zero changes under `web/`,
`api/`, `Makefile`, `package.json`, `extension/manifest.json`,
`tests/`, `etl/`, `src/`, `openspec/`, or `documents-es/`. It does
not pre-select Approach A / B / C in `design.md` §1 — §1 stays
**Abierta / Basada-en-evidencia**.

---

## Authority

The probe is governed by the five non-negotiables of
`openspec/changes/migrate-nextjs-tailwind4/proposal.md::Disposable
Static-Export Probe (Evidence Only)` (commit `866a55d`, PR #91):

| # | Non-negotiable | How this design honors it |
|---|---|---|
| 1 | **Unreachable from production** | Probe output is not served by FastAPI, not bound to `127.0.0.1:8765`, and not reachable from any shipped artifact (no extension `host_permissions` change, no `make api` integration, no release artifact). |
| 2 | **No consumer change** | `api/server.py:1847` `StaticFiles` mount, AC-21 search-engine contract consumers, and UI activation paths (`state` singleton, `localStorage` keys) stay untouched. The probe produces no consumer-visible surface. |
| 3 | **Evidence only** | The probe records `next build` size, hydration profile, and optional Playwright parity samples. It does not amend `design.md` §1 and does not pre-select Approach A. |
| 4 | **Explicit discard / rollback** | The probe lives on a short-lived branch (`docs/static-export-probe-design`); `git branch -D` plus worktree removal restores the pre-probe state with no source/tests/config residue. |
| 5 | **Cannot select static export alone** | Selecting Approach A requires a follow-up amendment to the proposal (or a successor change), reviewed against the recorded evidence; this proposal is not the selection point. |

Architectural citations: `proposal.md::Disposable Static-Export Probe`,
`design.md::§1 Decisión de frontera de responsabilidad del servidor
(Next.js ↔ FastAPI)`, `specs/modular-architecture/spec.md::regla 7`.
No conflict with `specs/modular-architecture/spec.md` rules 1–6 has
been identified at the design level; the probe adds zero surface.

---

## Probe identifiers (pinned)

| Field | Value |
|---|---|
| Stitch project ID | `11813286795400731874` |
| Stitch screen ID | `ec543a4cec974c2e82085a5e0406334a` |

If either ID drifts, the probe must be regenerated against the new
pair and this artifact amended; the old pair is then retired and the
audit log records the swap. The two IDs MUST appear together on any
regenerated artifact.

---

## Approved disposable diagnostic shell

The screen is a single, **static**, non-interactive diagnostic
shell. It exists only to communicate its own existence and
provenance; it carries no product UI, no brand, no navigation, no
controls, no data, and no persistence.

### Visual contract

| Region | Allowed | Forbidden |
|---|---|---|
| Page background | Solid white (`#FFFFFF`) — the one and only background color. | Gradients, images, brand-tinted surfaces, dark mode, `color-mix()` tricks. |
| Container | A single **centered** card with a visible 1 px border, generous padding, max width suited for readability (no fixed pixel value; responsive within the card). | Nested cards, decorative frames, shadows that imitate product chrome, animated transitions. |
| H1 | Exactly one `<h1>` describing the diagnostic nature (e.g. *"Static-export probe (diagnostic only)"* or equivalent neutral phrasing). | Subheadings (`<h2>`–`<h6>`), marketing copy, project name, version banner. |
| Explanation | One short paragraph (1–3 sentences) stating the screen is a disposable diagnostic, is not part of the product, and does not collect data. | Brand voice, persona language, calls to action, links to product surfaces. |
| Status rows | Exactly **three** rows, each a short neutral label + value (e.g. *Role: diagnostic*, *Scope: evidence only*, *Production: unreachable*). Static copy only. | More or fewer rows, dynamic values, progress bars, sparklines, charts. |

### High contrast, semantics, focus

- **High contrast**: body text ≥ 4.5:1 and card border ≥ 3:1 against white (WCAG 2.1 AA).
- **Semantics**: a single `<main>` wraps the card; the H1 is the only heading; the three status rows are an unordered list `<ul>` of three `<li>` items; no `<section>` / `<article>` / `<nav>` / `<header>` / `<footer>` masquerading as product chrome.
- **Focus**: no interactive controls, so document tab order is trivial; the H1 is the first focusable text node for assistive tech; the explanation and list read in source order. No skip-links, no focus traps, no `:focus-visible` styling that mimics product affordances.
- **Language**: `<html lang="...">` matches the explanation's language; no idioms or marketing tone.

---

## Audit criteria (negative inventory + checklist)

Run this checklist against the regenerated probe HTML / JSON. Every
box MUST be checked; any unchecked box is a defect and triggers
regeneration. The list is the migration contract for any future
swap of the Stitch project/screen pair.

**Stitch provenance**

- [ ] Stitch project ID present and equal to `11813286795400731874`
- [ ] Stitch screen ID present and equal to `ec543a4cec974c2e82085a5e0406334a`
- [ ] The two IDs appear together (same document / same JSON node)

**Shell structure**

- [ ] Background is solid white (`#FFFFFF`); no gradients, images, or brand-tinted surfaces
- [ ] Exactly one centered card with a visible border
- [ ] Exactly one `<h1>`, no `<h2>`–`<h6>`
- [ ] Explanation paragraph present, neutral, names the diagnostic-only role
- [ ] Exactly three status rows in a single `<ul>` of three `<li>` items; static copy only

**No brand / nav / controls / data / persistence**

- [ ] No brand: no logo, wordmark, slogan, product name, or `--primary` / `--realm-*` color token
- [ ] No navigation: no header bar, side rail, breadcrumb, tabs, or footer links
- [ ] No controls: no buttons, inputs, selects, toggles, sliders, dialogs, or menus
- [ ] No data: no taxonomy nodes, search engines, build-profile numbers, hydration timings, or env values
- [ ] No persistence: no `localStorage` / `sessionStorage` / cookies / IndexedDB reads or writes; no analytics or telemetry

**No product wiring**

- [ ] No imports from `web/app.js`, `web/api.js`, `web/state.js`, or any path under `src/modules/`
- [ ] No calls to FastAPI's `/api/*`; no content-script selectors matching the Chrome extension

**Production isolation**

- [ ] Probe HTML is **not** served by FastAPI; **not** bound to `127.0.0.1:8765`; **not** reachable from `http://localhost:8765/*` (verified by absence from `api/server.py:1847` `StaticFiles` mount and from `extension/manifest.json::host_permissions`)
- [ ] `git branch -D docs/static-export-probe-design` plus worktree removal leaves `origin/develop` byte-identical (no source / tests / config / `openspec/` / `documents-es/` residue)

**Accessibility**

- [ ] Body text contrast ≥ 4.5:1 against white; card border contrast ≥ 3:1
- [ ] `<html lang="...">` matches the explanation's language
- [ ] No `<section>` / `<article>` / `<nav>` / `<header>` / `<footer>` imitating product chrome

---

## Out of scope

Any application source code, test, or configuration file; any change
to `web/`, `api/`, `Makefile`, `package.json`,
`extension/manifest.json`, `tests/`, `etl/`, `src/`, `openspec/`, or
`documents-es/`; any wiring into FastAPI, the Chrome extension, the
smoke suite, or the release artifact; any pre-selection of Approach
A / B / C (`design.md::§1` stays **Abierta / Basada-en-evidencia**);
any persistence layer, telemetry, analytics, or third-party script;
any future iteration of the shell (one screen, one design, one audit
pass).

---

## Rollback boundary

This work unit adds only two untracked files:

```text
tools/static-export-probe/DESIGN.md
documents-es/static-export-probe-design-es.md
```

Both live on branch `docs/static-export-probe-design`. Reverting
means deleting both files from the worktree, then `git branch -D
docs/static-export-probe-design` plus worktree removal. No file under
`src/`, `web/`, `api/`, `tests/`, `etl/`, `openspec/`,
`documents-es/` (except the new mirror), `Makefile`, `package.json`,
or `extension/manifest.json` is touched; `origin/develop` is
restored byte-identically.

---

## Reference set

| § of this design | Citation |
|---|---|
| Five non-negotiables | `openspec/changes/migrate-nextjs-tailwind4/proposal.md::Disposable Static-Export Probe (Evidence Only)` |
| §1 decision state | `openspec/changes/migrate-nextjs-tailwind4/design.md::§1 Decisión de frontera de responsabilidad del servidor (Next.js ↔ FastAPI)` |
| Architectural rules | `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md::regla 7` |
| Probe identifiers | Stitch project `11813286795400731874`, screen `ec543a4cec974c2e82085a5e0406334a` |
| Production-linkage guard | `api/server.py:1847` `StaticFiles` mount, `extension/manifest.json::host_permissions` |
| Consumer guard | AC-21 `tests/test_smoke.py::test_search_engine_contract` (unchanged) |
| Spanish mirror | `documents-es/static-export-probe-design-es.md` |

---

`status: complete (design-only work unit; no source/tests/config added; production linkage forbidden by design; §1 decision remains evidence-bound)`
