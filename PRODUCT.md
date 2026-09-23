# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Taxonomic researchers and collection managers who need to explore taxonomic records, supporting evidence, and associated scientific files.

## Product Purpose

Taxa makes taxonomic information and its scientific evidence explorable in one workflow. Success means users can move from a taxon to relevant searches and materials without losing context.

## Positioning

Taxa connects taxonomy, evidence-oriented search, and scientific files in one coherent exploration experience rather than treating them as disconnected tools.

## Operating Context

Users work in a browser with taxonomic hierarchies, search links, and file material. The disposable static-export probe is an internal evidence fixture and is unreachable from production.

## Capabilities and Constraints

- The product serves both research and collection-management workflows.
- The active production runtime remains the existing FastAPI-served experience until a future reviewed boundary decision.
- Static export is not selected by the disposable evidence probe.
- The /hydration-probe route's static HTML is shipped to every visitor, but a client-only gate (src/modules/browser-state/presentation/HydrationProbeGate.tsx) renders a quiet fallback ("Internal witness — not part of the product") to anyone who navigates without the `taxa-internal-ok` localStorage flag. The Playwright harness sets the flag via `addInitScript` before navigation. Search-engine exposure is closed via the route's `<meta name="robots" content="noindex,nofollow">`. A future FastAPI routing-level 404 is the deferred backend follow-up.
- The product surface includes four top-level destinations: Classification (`/`, taxonomy hierarchy + detail panel), Browser (`/explorer`, research file browser), Help (`/help`, data-source legend + shortcut map + realm color legend + API docs + attribution), Settings (`/settings`, stub for future slice). The AppShell renders the four destinations in the header with an active-state indicator via `usePathname()`. The /help and /settings pages ship as the W3-audited destinations for in-product onboarding.

## Evidence on Hand

- Existing taxonomic hierarchy, search-engine, and file-exploration workflows in the repository.
- A Stitch evidence-probe design: project `11813286795400731874`, screen `ec543a4cec974c2e82085a5e0406334a`.
- No claim of completed static-export, parity, or Lighthouse evidence.

## Product Principles

- Preserve scientific context across taxonomic exploration.
- Make evidence and associated material discoverable without inventing claims.
- Keep architecture changes reversible until validated by comparable evidence.
- Separate disposable diagnostics from production behavior.

## Accessibility & Inclusion

- WCAG 2.2 AA is the durable accessibility target for web surfaces. The AppShell renders a skip-to-main `<a>` as the first focusable element on every route; every page has a `<header>` / `<main>` / `<footer>` landmark triple; the navigation nav uses `aria-current="page"` for the active affordance; the global search shortcut (`Cmd+K` / `/`) is announced in a footer one-liner.
