# Delta for modular-architecture

## Purpose

User-approved constraint: the migrated application MUST follow a
**modular monolith with layered architecture**. Framework-neutral;
every other capability MUST stay consistent.

## Rules

1. **One deployable monolith** — no separately deployed frontend
   or backend service. Single FastAPI process; one HTTP origin
   `127.0.0.1:8765`; `extension/manifest.json::host_permissions`
   stays at `["http://localhost:8765/*"]`.
2. **Capability-aligned modules** — top-level modules named after
   business capabilities (`research`, `taxonomy`, `design-system`,
   `browser-state`). Technical names (`controllers`, `services`,
   `repositories`, `utils`, `helpers`, `common`, `shared`, `misc`)
   MUST NOT be the top-level partition.
3. **Four layers per module** — **presentation**, **application**,
   **domain**, **infrastructure**, all visible per module.
4. **Inward dependencies** — presentation → application →
   domain; infrastructure → domain. Domain MUST NOT depend on
   presentation, application, browser, HTTP, framework, or
   infrastructure. Application MUST NOT depend on presentation or
   infrastructure directly.
5. **Module public contracts** — barrel export, `index.ts`, or
   equivalent per module. Non-exported symbols are private.
   Cross-module deep imports rejected at build time via
   path-alias config or equivalent lint guard.
6. **Framework-neutral** — rules 1–5 hold for every candidate
   server-responsibility approach (Next.js static export under
   FastAPI, full Next.js dev server on a second port, phased
   hybrid). No layer or boundary rule is relaxed to fit a chosen
   framework boundary.
7. **§1 boundary compliance** — the chosen Next.js ↔ FastAPI
   boundary in `design.md::§1 Decision` MUST comply with rules
   1–5. The boundary stays evidence-based until design resolves
   it. Design MUST NOT relax any rule here.

## ADDED Requirements

### Requirement: One deployable monolith

The system MUST satisfy rule 1.

#### Scenario: Single deployable unit

- GIVEN the migration lands
- WHEN the orchestrator inspects deployable artefacts
- THEN exactly one deployable unit exists (FastAPI serving `/`
  and `/api/*`)
- AND no second container, process group, or service is required

### Requirement: Capability-aligned modules

The system MUST satisfy rule 2.

#### Scenario: Module names map to capabilities

- GIVEN the design phase lists the migrated source tree
- WHEN a reviewer maps each top-level module to one line
- THEN every name reads as a business capability
- AND no top-level name reads as a technical dumping ground

### Requirement: Four layers per module

The system MUST satisfy rule 3.

#### Scenario: Four layers present in every module

- GIVEN a capability module is inspected
- WHEN the orchestrator enumerates layer folders / files
- THEN presentation, application, domain, and infrastructure are
  each represented
- AND no layer is silently merged into another

### Requirement: Dependency direction is inward

The system MUST satisfy rule 4.

#### Scenario: Domain stays free of framework and I/O

- GIVEN the domain layer is inspected
- WHEN a reviewer greps it for `react`, `next`, `fastapi`,
  `fetch`, `localStorage`, `document.`, `window.`, `process.`,
  or HTTP request objects
- THEN no matches appear
- AND the domain layer compiles and unit-tests without booting
  Next.js, React, FastAPI, or any I/O subsystem

#### Scenario: Application does not import presentation

- GIVEN the application layer is inspected
- WHEN a reviewer greps it for presentation modules, React
  components, or JSX
- THEN no matches appear
- AND any view-model is plain data consumable by any presentation

### Requirement: Module boundaries and public contracts

The system MUST satisfy rule 5.

#### Scenario: Cross-module imports go through the public contract

- GIVEN module A imports from module B
- WHEN a reviewer traces the import path
- THEN the import resolves only through B's public contract
- AND the build-time guard rejects any deep import into B's
  private folders

### Requirement: Constraint applies to every server-responsibility approach

The system MUST satisfy rule 6.

#### Scenario: Constraint holds for every candidate approach

- GIVEN the proposal lists Approach A, B, and C
- WHEN the design phase evaluates each
- THEN rules 1–5 remain binding
- AND the chosen approach is recorded in `design.md::§1 Decision`
  citing this spec

### Requirement: Next.js ↔ FastAPI boundary must comply

The system MUST satisfy rule 7.

#### Scenario: Design cites the spec when closing the decision

- GIVEN the design phase finalises the Next.js ↔ FastAPI approach
- WHEN the decision lands in `design.md::§1 Decision`
- THEN the entry cites this spec by path as the architectural
  authority
- AND if design sees a conflict with any rule here, it is raised
  back to the proposal before implementation