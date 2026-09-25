// Research presentation — pure typed helpers for the
// Browser-tab Explorer's working-set persistence
// (EXPLORER-PERSIST of
// `odd/tasks/explorer-orientation-state.md`).
//
// spec.md rule 4 keeps the framework-free kernel
// (`./explorer-state`) free of browser / I/O state. This
// file is the pure companion: it owns the parse /
// serialize / validate lifecycle for the typed
// `PersistedExplorerState` shape + the bound caps + the
// version literal + the storage key constant. The helpers
// stay framework-free + I/O-free (no `localStorage` /
// `globalThis.localStorage` / `window.localStorage` /
// `sessionStorage` references anywhere) so the focused test
// harness exercises them under Node without a browser.
//
// ODD-BSTATE-EXPLORER-PERSIST (architecture correction) —
// the previous W6.4 design owned the raw localStorage I/O
// inside this file. The correction moves every
// `localStorage.{getItem,setItem,removeItem}` call behind the
// canonical per-key browser-state store
// (`infrastructure/storeExplorerState.ts`) so the Research
// module is free of `localStorage.*` references. The raw
// `taxa.fex.explorerState` key and every storage operation
// are owned by `@taxa/browser-state`; this file contains
// only pure helpers. The follow-on Explorer integration
// will consume the hydration-safe browser-state hook through
// the public Research barrel.
//
// What stayed in this file (the research-side pure
// surface):
//   - The `EXPLORER_STATE_STORAGE_KEY` constant
//     (`"taxa.fex.explorerState"`) — pinned byte-for-byte
//     so the focused test harness can assert the literal
//     value end-to-end. The canonical literal declaration
//     stays in `browser-state/domain/keys.ts`; this local
//     mirror is the documentation/test seam.
//   - Local mirrors of the version and bound caps. The
//     source-level parity tests compare these literals with
//     their canonical browser-state declarations.
//   - The `PersistedExplorerState` interface — a local
//     structural mirror of the canonical store type, kept
//     local so the isolated helper has no runtime dependency.
//   - The `createEmptyPersistedExplorerState` factory —
//     a local pure factory for a fresh empty record.
//   - The `serializeExplorerState` helper — pure
//     serializer that throws when the record exceeds
//     `MAX_EXPLORER_STATE_BYTES`.
//   - The `parseExplorerState` helper — pure parser that
//     returns `null` on every malformed / future-version /
//     wrong-typed / out-of-bounds shape.
//   - The `collectAllTreePaths` helper — pure tree walker
//     that collects every folder + file path; the
//     `validateAgainstTree` helper delegates to it so the
//     path-collection logic lives in one place.
//   - The `validateAgainstTree` helper — pure tree-
//     validation walker that discards stale expanded /
//     selected paths, sets a stale selectedPath to
//     `null`, AND collapses duplicate expanded paths to
//     a single entry in stable first-seen order.
//
// EXPLORER-PERSIST contract:
//
//   1. Persist the working set — search query, selected
//      path, expanded folder paths — in ONE raw
//      localStorage key (`taxa.fex.explorerState`, owned
//      by the canonical per-key browser-state store). The
//      key mirrors the W6.3 Splitter's `taxa.fex.treeWidth`
//      decision: a single raw localStorage key per the
//      user-authorized decision.
//
//   2. Versioned record — the persisted payload carries an
//      explicit `version` literal
//      (`EXPLORER_STATE_STORAGE_VERSION`) so a future PR
//      that reshapes the shape can bump the version + add
//      a parse guard instead of silently corrupting an in-
//      flight user's record.
//
//   3. Bounded — every persisted field carries a hard cap
//      (`MAX_QUERY_LENGTH`, `MAX_SELECTED_PATH_LENGTH`,
//      `MAX_EXPANDED_PATHS`, `MAX_EXPLORER_STATE_BYTES`)
//      so a pathological user / a malformed record / a
//      quota blow-up is rejected at the boundary instead of
//      silently bloating localStorage.
//
//   4. Validated against the freshly loaded tree — the
//      `validateAgainstTree` helper discards stale expanded
//      paths, clears a stale `selectedPath`, AND collapses
//      duplicate expanded paths to a single entry in stable
//      first-seen order (a session that re-expanded a folder
//      across multiple post-mount clicks, or a future PR
//      that hand-merges two persisted records, sees a
//      deterministic expanded set that mirrors the user's
//      original expansion intent). The follow-on React
//      integration applies it after the tree loads.
//
//   5. Storage-error tolerant — the browser-state store
//      routes storage access through safe helpers that swallow
//      quota, SecurityError, disabled-storage, and SSR failures.
//      The user keeps working in the current session; only
//      persistence is lost.
//
//   6. Hydration-safe restore sequencing — the follow-on
//      Explorer integration uses `useExplorerState`; its server
//      and hydration snapshots are `null`, and it surfaces the
//      persisted/default record after hydration. Once the tree
//      loads, the mount applies `validateAgainstTree` without a
//      direct storage read in the Explorer render path.
//
// Privacy caveat — the user explicitly chose browser-local
// persistence after being informed that taxon names + paths
// may be sensitive (the EXPLORER-PERSIST decision inverts
// the previous W1 constraint). The data stays on this
// browser; no server transmission is added. The domain
// layer's `SearchState` JSDoc was updated to reflect this
// decision.
//
// spec.md rule 5 keeps cross-module imports anchored at the
// public barrel. The helpers + constants are re-exported
// through `src/modules/research/index.ts` so cross-module
// consumers reach the EXPLORER-PERSIST surface through
// `@taxa/research`.

import type {
  ExplorerTreeNode,
  ExplorerTree,
} from "../domain/explorer";
// ODD-BSTATE-EXPLORER-PERSIST — the typed shape, version,
// caps, and empty-record factory stay local so the pure
// helper compiles without a runtime browser-state import.
// Source-level parity tests compare the shared key/version/
// cap literals with canonical declarations; the runtime
// harness checks helper behavior.
/** Local mirror of the canonical version literal; the source
 *  parity test pins both declarations. */
export const EXPLORER_STATE_STORAGE_VERSION = 1;

/** Local structural mirror of the canonical persisted record. */
export interface PersistedExplorerState {
  readonly version: number;
  readonly query: string;
  readonly selectedPath: string | null;
  readonly expandedPaths: readonly string[];
}

/** Create a fresh empty record for the pure helper surface. */
export function createEmptyPersistedExplorerState(): PersistedExplorerState {
  return {
    version: EXPLORER_STATE_STORAGE_VERSION,
    query: "",
    selectedPath: null,
    expandedPaths: [],
  };
}

// ---- Bound constants + version + storage key ----

/** Raw localStorage key for the EXPLORER-PERSIST record.
 *  Pinned byte-for-byte against the W6.3 Splitter's
 *  `taxa.fex.treeWidth` convention: a single global key
 *  per the user-authorized decision. The canonical literal
 *  declaration lives in `browser-state/domain/keys.ts`;
 *  this local mirror keeps the pure Node harness isolated.
 *  `test_w6_4_storage_key_matches_canonical_browser_state_literal`
 *  compares the two declarations. */
export const EXPLORER_STATE_STORAGE_KEY = "taxa.fex.explorerState";

/** Hard byte cap on the serialized record. A pathological
 *  user (a deeply nested tree path that exceeds the cap)
 *  is rejected at the boundary instead of silently
 *  bloating localStorage. The cap is a sane localStorage
 *  value (≤ 1 MiB) so the persisted record stays well
 *  under every browser's practical per-origin quota.
 *  64 KiB leaves headroom for future PRs without
 *  overflowing the quota. */
export const MAX_EXPLORER_STATE_BYTES = 65536;

/** Hard cap on the number of expanded folder paths in
 *  the persisted record. A pathological user (a session
 *  that expanded every folder in a 10k-folder tree) is
 *  rejected at the boundary instead of silently bloating
 *  localStorage. The cap is well above a realistic user's
 *  working set (typical session < 100 expanded folders). */
export const MAX_EXPANDED_PATHS = 1000;

/** Hard cap on the search-query string length. The
 *  legacy search input accepts arbitrary strings; the cap
 *  is a defensive bound on the persisted record so a
 *  pathological user (a 1 MiB paste) is rejected at the
 *  boundary instead of silently bloating localStorage.
 *  256 chars is well above a realistic search query. */
export const MAX_QUERY_LENGTH = 256;

/** Hard cap on the selected-path string length. Tree
 *  paths are bounded by FastAPI's `_walk_tree` depth
 *  cap; the cap is a defensive bound on the persisted
 *  record so a pathological payload is rejected at the
 *  boundary instead of silently bloating localStorage.
 *  1024 chars is well above a realistic tree path. */
export const MAX_SELECTED_PATH_LENGTH = 1024;

// ---- Pure helpers (framework-free, I/O-free) ----

/** Pure helper: serialize a `PersistedExplorerState`
 *  into the canonical JSON string the storage layer
 *  writes. Throws when the serialized record exceeds
 *  `MAX_EXPLORER_STATE_BYTES` — the caller is responsible
 *  for catching + discarding the throw.
 *
 *  Note: the canonical browser-state writer
 *  (`infrastructure/storeExplorerState.ts::writeExplorerState`)
 *  does NOT call this helper. It independently validates
 *  the input against every canonical cap (version, query
 *  type + length, selectedPath type + length,
 *  expandedPaths type + length, AND a `serialized.length
 *  * 3 > MAX_EXPLORER_STATE_BYTES` byte-size check) and
 *  silently `return`s on any violation — no throw, no
 *  `safeSetItem`, no listener fire. The writer's
 *  independent bounds guard is the persistence-boundary
 *  guarantee (a defensive caller cannot smuggle an
 *  oversized record through the typed store); this
 *  helper's throw is a SEPARATE, defensive check that
 *  fires only when a caller invokes the helper directly
 *  (e.g. a future presentation-only consumer or an
 *  integration test). The byte-size checks intentionally
 *  overlap as defense in depth: the store guards typed
 *  writes, while this helper guards direct serialization
 *  calls and reports an error.
 *
 *  The serializer writes the version literal verbatim so
 *  `parseExplorerState` can read + validate it. The
 *  `expandedPaths` array is preserved verbatim (no
 *  sorting, no dedup at the serialization layer — a
 *  hand-merged or replayed record can carry duplicates;
 *  `validateAgainstTree` collapses them with stable
 *  first-seen-order dedup at the read boundary because
 *  the persisted order is irrelevant to the React mount
 *  but the first-seen order IS the user's expansion
 *  intent).
 *
 *  Pure function (modulo the size-cap throw): same input
 *  always yields the same output. Lives here (NOT in the
 *  storage helpers) so the focused test harness exercises
 *  it under Node without `globalThis.localStorage`. */
export function serializeExplorerState(
  state: PersistedExplorerState,
): string {
  const serialized = JSON.stringify(state);
  // UTF-16 byte length is a conservative estimate of the
  // JSON's wire byte size (the JSON wire format is ASCII
  // for non-extended ASCII text, and a UTF-16 code unit
  // is exactly 2 bytes; the multiplier 3 covers the worst
  // case of multibyte UTF-8 expansion). The check fires
  // BEFORE the write so the caller never commits an
  // oversized record.
  const approxBytes = serialized.length * 3;
  if (approxBytes > MAX_EXPLORER_STATE_BYTES) {
    throw new Error(
      `PersistedExplorerState exceeds MAX_EXPLORER_STATE_BYTES ` +
      `(${approxBytes} > ${MAX_EXPLORER_STATE_BYTES})`,
    );
  }
  return serialized;
}

/** Pure helper: parse a JSON string into a validated
 *  `PersistedExplorerState`. Returns `null` for every
 *  malformed / out-of-bounds / wrong-typed / future-
 *  version shape — the React layer treats `null` as "no
 *  persisted state, start fresh" so a corrupt record
 *  never crashes the mount.
 *
 *  Cases that return `null`:
 *   - `null` / `""` / non-JSON input (the JSON.parse
 *     catch + the type guard).
 *   - Oversized raw JSON (`raw.length * 3 >
 *     MAX_EXPLORER_STATE_BYTES`), rejected before parsing.
 *   - Record missing one of the required fields
 *     (`version` / `query` / `selectedPath` /
 *     `expandedPaths`).
 *   - Wrong field types (non-number version, non-string
 *     query, non-string-non-null selectedPath, non-array
 *     expandedPaths).
 *   - Future / unknown version (`version >
 *     EXPLORER_STATE_STORAGE_VERSION`).
 *   - Out-of-bounds values (query length >
 *     `MAX_QUERY_LENGTH`, selectedPath length >
 *     `MAX_SELECTED_PATH_LENGTH`, expandedPaths length >
 *     `MAX_EXPANDED_PATHS`, individual expanded path
 *     length > `MAX_SELECTED_PATH_LENGTH`, non-string
 *     entries in `expandedPaths`).
 *
 *  Pure function (modulo JSON.parse): same input always
 *  yields the same output. Lives here (NOT in the storage
 *  helpers) so the focused test harness exercises it
 *  under Node without `globalThis.localStorage`. */
export function parseExplorerState(
  raw: string | null,
): PersistedExplorerState | null {
  if (raw === null || raw === "") return null;
  // ODD-BSTATE-EXPLORER-PERSIST-BOUNDS — reject oversized raw
  // records BEFORE `JSON.parse` so a multi-MB paste never
  // reaches the parser and a quota-blow-up / stale-bloated
  // storage hydrates to the canonical empty default. The
  // wire-byte estimate mirrors the canonical browser-state
  // parser's guard
  // (`infrastructure/storeExplorerState.ts`):
  // `raw.length * 3` (UTF-16 code unit × 3 covers the worst
  // case of multibyte UTF-8 expansion). The check fires
  // immediately after the null/empty short-circuit so the
  // guard is the first defense-in-depth check on a non-
  // empty payload — the structural caps (query length,
  // selectedPath length, expandedPaths count, etc.) catch
  // shape violations AFTER parse; the raw-byte cap rejects
  // a multi-MB paste BEFORE parse so the parser never
  // spends cycles on a malformed-shape object.
  if (raw.length * 3 > MAX_EXPLORER_STATE_BYTES) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (
    typeof parsed !== "object" ||
    parsed === null ||
    Array.isArray(parsed)
  ) {
    return null;
  }
  const obj = parsed as Record<string, unknown>;
  // version — must be a number ≤ EXPLORER_STATE_STORAGE_VERSION.
  const version = obj.version;
  if (
    typeof version !== "number" ||
    !Number.isFinite(version) ||
    version > EXPLORER_STATE_STORAGE_VERSION
  ) {
    return null;
  }
  // query — must be a string within MAX_QUERY_LENGTH.
  const query = obj.query;
  if (typeof query !== "string") return null;
  if (query.length > MAX_QUERY_LENGTH) return null;
  // selectedPath — must be a string or null within
  // MAX_SELECTED_PATH_LENGTH.
  const selectedPath = obj.selectedPath;
  if (selectedPath !== null && typeof selectedPath !== "string") {
    return null;
  }
  if (
    typeof selectedPath === "string" &&
    selectedPath.length > MAX_SELECTED_PATH_LENGTH
  ) {
    return null;
  }
  // expandedPaths — must be an array of strings within
  // MAX_EXPANDED_PATHS; each path within
  // MAX_SELECTED_PATH_LENGTH.
  const expandedPaths = obj.expandedPaths;
  if (!Array.isArray(expandedPaths)) return null;
  if (expandedPaths.length > MAX_EXPANDED_PATHS) return null;
  for (const entry of expandedPaths) {
    if (typeof entry !== "string") return null;
    if (entry.length > MAX_SELECTED_PATH_LENGTH) return null;
  }
  // All checks passed — project the typed shape.
  return {
    version,
    query,
    selectedPath,
    expandedPaths: expandedPaths.slice(),
  };
}

/** Pure helper: collect every folder + file path under
 *  the supplied tree root. Returns a fresh `Set<string>`
 *  of every node's `path` field (the synthetic root
 *  carrying `path: ""` is omitted so the returned set
 *  never contains a phantom ancestor path). The walker
 *  uses an explicit stack so a deep tree (>1000 folders)
 *  never blows the JS call stack.
 *
 *  Pure function: same input always yields the same
 *  output. Lives here (NOT in the storage helpers) so the
 *  focused test harness exercises it under Node without
 *  `globalThis.localStorage`. The Explorer mount uses
 *  this helper for two distinct purposes:
 *   1. `validateAgainstTree` — filter the persisted
 *      `expandedPaths` + `selectedPath` against the
 *      freshly loaded tree.
 *   2. Post-mount click preservation — a user might
 *      expand a folder while the tree is still loading;
 *      the mount checks each post-mount expansion
 *      against this set so a stale persisted expansion
 *      is silently dropped without undoing a fresh
 *      click.
 *
 *  Returns an empty Set for a null tree (the React layer
 *  uses this to short-circuit the post-mount validation
 *  when the tree hasn't finished loading). */
export function collectAllTreePaths(
  tree: ExplorerTree | null,
): ReadonlySet<string> {
  if (tree === null || tree.root === null) return new Set();
  const paths = new Set<string>();
  const stack: ExplorerTreeNode[] = [tree.root];
  while (stack.length > 0) {
    const node = stack.pop();
    if (node === undefined) continue;
    if (node.path) paths.add(node.path);
    if (node.type === "folder" && Array.isArray(node.children)) {
      for (const c of node.children) stack.push(c);
    }
  }
  return paths;
}

/** Pure helper: validate the persisted record against the
 *  freshly loaded tree. Discards stale expanded paths
 *  (folders that no longer exist) AND collapses duplicate
 *  expanded paths to a single entry while preserving the
 *  FIRST occurrence's position (stable first-seen-order
 *  de-duplication). A `null` tree yields an empty record
 *  (the React layer uses the empty record to drive the
 *  initial state until the tree finishes loading — every
 *  expanded path is discarded, the selectedPath is reset
 *  to null).
 *
 *  The walker delegates to `collectAllTreePaths` so the
 *  path-collection logic lives in one place. The
 *  filter + stable-dedup steps use a local Set as a
 *  membership witness — the Set is NOT the source of
 *  truth for order (Set-iteration order is insertion
 *  order in JS, but the contract pins first-seen order
 *  explicitly so a future JS runtime that re-orders Set
 *  iteration does not silently change the persisted
 *  semantics).
 *
 *  Pure function: same `(record, tree)` always yields the
 *  same output. Lives here (NOT in the storage helpers)
 *  so the focused test harness exercises it under Node
 *  without `globalThis.localStorage`. */
export function validateAgainstTree(
  record: PersistedExplorerState,
  tree: ExplorerTree | null,
): PersistedExplorerState {
  if (tree === null || tree.root === null) {
    return {
      version: EXPLORER_STATE_STORAGE_VERSION,
      query: record.query,
      selectedPath: null,
      expandedPaths: [],
    };
  }
  const validPaths = collectAllTreePaths(tree);
  // Stable de-duplication: the persisted `expandedPaths`
  // array can carry the same valid path multiple times
  // (a session that re-expanded a folder across multiple
  // post-mount clicks, or a future PR that hand-merges
  // two persisted records). The filter step keeps only
  // the entries that exist in the freshly loaded tree;
  // the Set-based dedup step then collapses repeats to
  // a single entry while preserving the FIRST occurrence's
  // position (stable / first-seen order, NOT Set-insertion
  // order, so the React mount sees a deterministic expanded
  // set that mirrors the user's original expansion
  // intent). The Set is a local witness for membership,
  // not the source of truth for order.
  const seen = new Set<string>();
  const validExpandedPaths: string[] = [];
  for (const p of record.expandedPaths) {
    if (!validPaths.has(p)) continue;
    if (seen.has(p)) continue;
    seen.add(p);
    validExpandedPaths.push(p);
  }
  const validSelectedPath =
    record.selectedPath !== null && validPaths.has(record.selectedPath)
      ? record.selectedPath
      : null;
  return {
    version: EXPLORER_STATE_STORAGE_VERSION,
    query: record.query,
    selectedPath: validSelectedPath,
    expandedPaths: validExpandedPaths,
  };
}

// The public Research barrel exports the local interface
// declared above. The browser-state domain keeps its own
// structurally matching store type so this pure module has
// no runtime dependency on browser storage code.
