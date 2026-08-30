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
- The probe must remain isolated from production consumers, API routes, and persisted user state.

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

WCAG 2.2 AA is the durable accessibility target for web surfaces.
