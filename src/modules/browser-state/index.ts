/**
 * Public barrel for the `browser-state` capability module.
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via the `@taxa/browser-state` path alias defined in
 * `tsconfig.json`). Direct imports into the layer folders below are
 * blocked by `.eslintrc.cjs::no-restricted-imports`.
 *
 * ODD-BSTATE-TAX-001-A — per-key module split:
 *   - `domain/keys.ts`                  → typed `StorageKey` union +
 *                                          the canonical localStorage
 *                                          literals + the `Listener` /
 *                                          `Unsubscribe` types.
 *   - `domain/defaults.ts`              → typed defaults per key
 *                                          (theme: `"light"`,
 *                                          tree-source: `"col"`,
 *                                          last-taxon-id / kebab-open-id: `null`,
 *                                          explorer-state: empty record).
 *   - `domain/explorer-state.ts`        → typed `PersistedExplorerState`
 *                                          shape + the version literal +
 *                                          the `createEmptyPersistedExplorerState`
 *                                          factory (ODD-BSTATE-EXPLORER-PERSIST
 *                                          — the EXPLORER-PERSIST
 *                                          architecture correction
 *                                          extends the per-key family
 *                                          by one entry).
 *   - `infrastructure/storeTheme.ts`     → typed `readTheme` /
 *                                          `writeTheme` /
 *                                          `subscribeTheme` for the
 *                                          `taxa.settings.theme` key.
 *   - `infrastructure/storeTreeSource.ts`→ typed `readTreeSource` /
 *                                          `writeTreeSource` /
 *                                          `subscribeTreeSource` for
 *                                          the `taxa.tree.source` key
 *                                          (the FIRST production
 *                                          consumer of the typed store
 *                                          in the main route —
 *                                          `TaxonomyTree`).
 *   - `infrastructure/storeLastTaxonId.ts` → typed `readLastTaxonId` /
 *                                          `writeLastTaxonId` /
 *                                          `subscribeLastTaxonId`.
 *   - `infrastructure/storeKebabOpenId.ts` → typed `readKebabOpenId` /
 *                                          `writeKebabOpenId` /
 *                                          `subscribeKebabOpenId`.
 *   - `infrastructure/storeInternalFlag.ts` → typed `readInternalFlag` /
 *                                          `writeInternalFlag` /
 *                                          `subscribeInternalFlag` for
 *                                          the `taxa-internal-ok` key
 *                                          (ODD-ASN-001 — the
 *                                          `/hydration-probe` gate's
 *                                          witness flag; the Playwright
 *                                          harness sets it via
 *                                          `context.add_init_script`).
 *   - `infrastructure/storeExplorerState.ts` → typed `readExplorerState` /
 *                                          `writeExplorerState` /
 *                                          `subscribeExplorerState` /
 *                                          `clearExplorerState` for the
 *                                          `taxa.fex.explorerState` key
 *                                          (ODD-BSTATE-EXPLORER-PERSIST
 *                                          — the EXPLORER-PERSIST
 *                                          architecture correction
 *                                          routes the Browser-tab
 *                                          Explorer working-set
 *                                          persistence through the
 *                                          canonical per-key chain so
 *                                          the Research module is free
 *                                          of `localStorage.*`
 *                                          references).
 *   - `infrastructure/reset.ts`         → aggregate `reset()` that
 *                                          clears every key to its
 *                                          typed default AND removes
 *                                          every matching
 *                                          `localStorage` entry.
 *                                          The aggregate module is
 *                                          the one place where the
 *                                          per-key chains meet; the
 *                                          main route MUST NOT import
 *                                          it (the strict chunk-
 *                                          boundary contract only
 *                                          allows the typed-source
 *                                          chain into its bundle).
 *   - `application/useTheme.ts`         → hydration-safe React hook
 *                                          for the theme key.
 *   - `application/useTreeSource.ts`     → hydration-safe React hook
 *                                          for the tree-source key.
 *   - `application/useLastTaxonId.ts`   → hydration-safe React hook
 *                                          for the last-taxon-id key.
 *   - `application/useKebabOpenId.ts`   → hydration-safe React hook
 *                                          for the kebab-open-id key.
 *
 * Each hook imports from its matching store only. Turbopack
 * retention relies on the per-key separation: the main route
 * imports `useTreeSource`, so the tree-source chain stays in the
 * main route's chunk while the theme / last-taxon-id / kebab-open-id
 * chains are dropped. The strict chunk-boundary contract
 * (`tests/test_app_shell_render.py::test_out_index_html_chunks_permit_only_tree_source_key`)
 * pins the contract end-to-end.
 *
 * The barrel re-exports only the typed surface — no raw
 * `localStorage` getter/setter leaks through here, so cross-module
 * consumers cannot bypass the typed store.
 */
export {
  THEME_STORAGE_KEY,
  TREE_SOURCE_STORAGE_KEY,
  LAST_TAXON_ID_STORAGE_KEY,
  KEBAB_OPEN_ID_STORAGE_KEY,
  INTERNAL_FLAG_STORAGE_KEY,
  EXPLORER_STATE_STORAGE_KEY,
  ALL_STORAGE_KEYS,
} from "./domain/keys";
export type {
  StorageKey,
  Listener,
  Unsubscribe,
  Theme,
  TreeSource,
} from "./domain/keys";

export {
  DEFAULT_THEME,
  DEFAULT_TREE_SOURCE,
  DEFAULT_LAST_TAXON_ID,
  DEFAULT_KEBAB_OPEN_ID,
  DEFAULT_EXPLORER_STATE,
} from "./domain/defaults";

// ODD-BSTATE-EXPLORER-PERSIST — re-export the typed
// `PersistedExplorerState` shape + the canonical empty-record
// factory so cross-module consumers reach the typed
// explorer-state surface through the public barrel. The
// shape lives in `domain/explorer-state.ts`; the version
// literal + the factory stay reachable through the public
// typed hand-off.
export {
  EXPLORER_STATE_STORAGE_VERSION,
  createEmptyPersistedExplorerState,
} from "./domain/explorer-state";
export type { PersistedExplorerState } from "./domain/explorer-state";

// ODD-BSTATE-TAX-001-A — per-key store re-exports. Each per-key
// store is re-exported from its own line so Turbopack can link
// only the imported chain. Reserving a single re-export block
// that aggregates every per-key store would pull every store into
// every consumer's chunk (the bundler tracks exports by file, not
// by re-export group), defeating the strict chunk boundary.
export {
  readTheme,
  writeTheme,
  subscribeTheme,
} from "./infrastructure/storeTheme";

export {
  readTreeSource,
  writeTreeSource,
  subscribeTreeSource,
} from "./infrastructure/storeTreeSource";

export {
  readLastTaxonId,
  writeLastTaxonId,
  subscribeLastTaxonId,
} from "./infrastructure/storeLastTaxonId";

export {
  readKebabOpenId,
  writeKebabOpenId,
  subscribeKebabOpenId,
} from "./infrastructure/storeKebabOpenId";

// ODD-ASN-001 — internal-flag store re-export. Mirrors the
// per-file rationale of the four sibling store re-exports above:
// each per-key store lives in its own file so Turbopack can
// retain only the imported chain. The gate
// (`presentation/HydrationProbeGate.tsx`) imports
// `readInternalFlag` from this barrel so the presentation layer
// stays free of `localStorage.*` references (the
// ODD-BSTATE-TAX-001 storage-ownership contract).
export {
  readInternalFlag,
  writeInternalFlag,
  subscribeInternalFlag,
} from "./infrastructure/storeInternalFlag";

// ODD-BSTATE-EXPLORER-PERSIST — explorer-state store re-export.
// Mirrors the per-file rationale of the five sibling store
// re-exports above: each per-key store lives in its own file so
// Turbopack can retain only the imported chain. The
// Browser-tab Explorer mount wires the typed chain through the
// public barrel so the storage module stays free of
// `localStorage.*` references (the ODD-BSTATE-TAX-001
// storage-ownership contract).
export {
  readExplorerState,
  writeExplorerState,
  subscribeExplorerState,
  clearExplorerState,
} from "./infrastructure/storeExplorerState";

export { reset } from "./infrastructure/reset";

// ODD-BSTATE-TAX-001-A — per-key hook re-exports. Same per-file
// rationale as the store re-exports above: each hook lives in its
// own file so Turbopack can drop the unrelated hooks from any
// consumer's chunk.
export { useTheme } from "./application/useTheme";
export { useTreeSource } from "./application/useTreeSource";
export { useLastTaxonId } from "./application/useLastTaxonId";
export { useKebabOpenId } from "./application/useKebabOpenId";

// ODD-BSTATE-PW-001 — one-line wiring edit (collateral to the new
// `presentation/HydrationProbe` component). Exposes the isolated
// hydration probe through the public barrel so the dedicated
// `/hydration-probe` route can mount it via
// `import { HydrationProbe } from "@taxa/browser-state";`. The
// no-restricted-imports guard rejects deep paths into the
// presentation layer; the barrel is the only legal consumer
// surface for cross-module mounts. The probe mounts the four
// per-key hooks together (theme / tree-source / last-taxon-id /
// kebab-open-id) so the probe route's bundle legitimately
// carries ALL four typed chains — the boundary contract is
// scoped to the main route (see
// `test_app_shell_render.py::test_out_index_html_chunks_permit_only_tree_source_key`).
export { default as HydrationProbe } from "./presentation/HydrationProbe";

// ODD-ASN-001 — production isolation gate for the dedicated
// `/hydration-probe` route. Lives next to the `HydrationProbe`
// re-export so the route's `layout.tsx` can mount the gate via
// `import { HydrationProbeGate } from "@taxa/browser-state";`
// without deep-linking into the presentation layer. The gate
// is the route's only client-side production guard; the
// search-engine side of the contract is enforced by the route
// layout's `metadata.robots` export (Next.js auto-injects the
// `<meta name="robots" content="noindex,nofollow">` pair).
export { default as HydrationProbeGate } from "./presentation/HydrationProbeGate";
