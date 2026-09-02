# Browser State Hydration Specification

> Domain: `browser-state-hydration`. New domain. Authored under
> `complete-taxa-frontend-migration`. The canonical home is the change
> folder; archive copies this file verbatim into
> `openspec/specs/browser-state-hydration/spec.md` at activation.

## Purpose

Browser-local state (`theme`, `tree-source`, `last-taxon-id`,
`kebab-open-id`) is migrated from the legacy `web/state.js`
singleton into a **typed store** with one read site + one write
site per key. Storage reads happen inside `useEffect` behind a
`mounted` flag so the first paint defaults to the empty state and
React's hydration guard never trips. The contract preserved
against the legacy build is **deterministic, single-site state
mutation** — every preference survives a page reload, every key
has exactly one owner in the source tree, and the typed store
emits typed events so subscribers don't have to parse raw
`localStorage` strings.

## Requirements

### Requirement: Typed store with one read site + one write site per key

The system MUST define a typed store that owns four
`localStorage` keys and exposes exactly one read site and one
write site per key.

#### Scenario: Store shape

- GIVEN the apply worker authors `src/modules/browser-state/{store,keys,defaults}.ts`
- WHEN the store is initialised
- THEN it exposes the four keys below with the listed types
- AND each key has exactly one `read` function (typed) and one
  `write` function (typed) exported from the public barrel

| Key (logical) | `localStorage` key | Type | Default |
| --- | --- | --- | --- |
| `theme` | `taxa.settings.theme` | `"light" \| "dark"` | OS `prefers-color-scheme` fallback, `light` when unavailable |
| `tree-source` | `taxa.tree.source` | `"col" \| "worms" \| "freshwater"` | `"col"` |
| `last-taxon-id` | `taxa.tree.lastTaxonId` | `number \| null` | `null` |
| `kebab-open-id` | `taxa.tree.kebabOpenId` | `number \| null` | `null` |

#### Scenario: One read site per key

- GIVEN the typed store is in scope
- WHEN the apply worker greps `src/modules/browser-state/` for
  `localStorage.getItem(...)` calls
- THEN exactly four call sites exist — one per key
- AND each call site reads the matching `localStorage` key
- AND no other module (`src/modules/taxonomy/**`,
  `src/modules/research/**`, `src/modules/app-shell/**`,
  `src/modules/design-system/**`) reads `localStorage` directly

#### Scenario: One write site per key

- GIVEN the typed store is in scope
- WHEN the apply worker greps `src/modules/browser-state/` for
  `localStorage.setItem(...)` and `localStorage.removeItem(...)`
  calls
- THEN exactly four call sites exist — one per key
- AND each call site writes the matching `localStorage` key
- AND no other module writes `localStorage` directly
- AND `removeItem` is invoked from the same module that owns the
  write site (e.g. the reset-tree-width control in settings
  delegates to the store)

### Requirement: Hydration guard against server / client mismatch

The system MUST defer every `localStorage` read until **after**
the first paint, behind a `mounted` flag, so React's hydration
guard never trips.

#### Scenario: First paint defaults to the empty state

- GIVEN the React tree mounts for the first time
- WHEN the initial render fires
- THEN the `mounted` flag is `false`
- AND every `read` site returns the typed default (not the
  `localStorage` value)
- AND the tree structure defaults to the empty state
- AND the URL does not yet reflect a `last-taxon-id`

#### Scenario: `useEffect` rehydrates and triggers a follow-up render

- GIVEN the first paint completed with the empty state
- WHEN the apply worker's `useEffect` runs
- THEN each of the four `read` sites is invoked exactly once
- AND the typed store rehydrates the matching state slot
- AND a follow-up render applies the rehydrated state
- AND the URL is updated to the `last-taxon-id` taxon if one is
  stored
- AND the active tree-source, theme, and kebab-open-id match the
  stored values

#### Scenario: No hydration warning in the browser console

- GIVEN the chromium fixture is loaded
- WHEN the apply worker inspects the browser console after the
  first paint + rehydration cycle
- THEN no React hydration-mismatch warning fires
- AND no `Warning: Text content did not match` warning fires
- AND no `Warning: Expected server HTML to contain` warning
  fires

### Requirement: Typed subscribers

The system MUST expose a typed subscriber API so that consumers
(`AppShell`, the tree, the detail panel, the settings view) can
listen for changes without re-reading `localStorage`.

#### Scenario: `subscribe` returns an unsubscribe

- GIVEN a consumer subscribes to one of the four keys
- WHEN the typed store mutates the key
- THEN the consumer's subscriber fires synchronously with the
  new typed value
- AND the consumer can unsubscribe via the returned callback
- AND no consumer re-reads `localStorage` directly to learn of the
  change

#### Scenario: Subscribers do not leak across mounts

- GIVEN a consumer component mounts, subscribes, then unmounts
- WHEN the consumer unmounts
- THEN the subscriber is removed from the store's listener list
- AND no stale listener fires after unmount

### Requirement: Quota / private-browsing safety

The system MUST swallow `localStorage` exceptions (private mode,
quota exceeded) and fall back to the typed default.

#### Scenario: `localStorage` throws on read

- GIVEN `localStorage.getItem` throws (private browsing)
- WHEN a `read` site fires
- THEN the store returns the typed default
- AND no uncaught exception propagates
- AND the application continues to render with the empty state

#### Scenario: `localStorage` throws on write

- GIVEN `localStorage.setItem` throws (quota exceeded, private
  mode)
- WHEN a `write` site fires
- THEN the store swallows the exception
- AND the in-memory state still updates (so the UI reflects the
  change for the current session)
- AND the next page reload returns to the typed default (no
  persistent write happened)

### Requirement: Reset / clear affordance

The system MUST expose a typed `reset` affordance that clears
every key to its typed default and removes the matching
`localStorage` entries.

#### Scenario: Reset clears every key

- GIVEN the user triggers the reset affordance from the settings
  view
- WHEN the typed store's `reset()` fires
- THEN each of the four keys is set to its typed default
- AND each `localStorage` entry is removed
- AND the subscribers fire synchronously with the new defaults
- AND the UI re-renders to reflect the empty state

#### Scenario: Reset persists across reloads

- GIVEN the user triggered `reset()` and then reloaded the page
- WHEN the apply worker inspects `localStorage`
- THEN none of the four `taxa.*` keys are present
- AND the rehydrated state is the typed default for every slot

## Notes

- The four keys in this spec are the canonical list. The legacy
  `taxa.fex.treeWidth` key (used by the splitter) is **out of
  scope** for this domain and stays owned by the file explorer
  module — the apply phase must not move that key into the typed
  store under this spec.
- The barrel
  `src/modules/browser-state/index.ts` exports only the four
  `read` functions, the four `write` functions, the `subscribe`
  function, the `reset` function, the typed defaults, and the
  typed listener type. **No** raw `localStorage` getter/setter is
  exported.
- The modular-architecture spec rule 4 still applies: the
  `browser-state` **domain** layer is plain TypeScript types
  (no `localStorage`, no `window`, no `document`); the
  `browser-state` **infrastructure** layer owns the actual
  `localStorage` calls; the `browser-state` **presentation** /
  **application** layers consume the typed API only.