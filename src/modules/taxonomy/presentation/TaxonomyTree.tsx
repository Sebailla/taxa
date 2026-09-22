"use client";

/**
 * TaxonomyTree — visible taxonomy tree (ODD-VTREE-002 / ODD-NTP-002 /
 * ODD-NTP-003 / ODD-NTP-004 / ODD-NTP-005).
 *
 * Client island. Fetches root domains on mount through the canonical
 * `fetchDomains` helper from `@taxa/taxonomy`, renders collapsed root
 * rows, and lazily loads children through `fetchChildren`. Pure
 * tree-state transitions go through the `tree-state.ts` helpers.
 *
 * ODD-NTP-005 — native source-aware in-tree navigation:
 *   - The React tree now owns focused / selected navigation state
 *     (mirrors the legacy `web/state.js::focused` + `selected` pair).
 *   - `select` on a leaf / `focus-segment` on a breadcrumb ancestor
 *     drives both `focused` and `selected` to the chosen id. Clicking
 *     a row NEVER breaks an existing expansion — selection is
 *     orthogonal to expansion, matching the legacy oracle.
 *   - `select` is the row-level kebab "View details" action too
 *     (RENAMED from "Search online" in ODD-TDDISC-001 for
 *     discoverability — the `data-action="open-searches"`
 *     contract stays so the parent keeps routing through
 *     `handleSelect`), so the kebab item lands here: it just
 *     calls `handleSelect(id)` and closes the open kebab menu.
 *     The "Open folder" item (rendered only when
 *     `hasMaterializedFolder(taxon)` is true) is enabled by
 *     ODD-OPENFOLDER-001: the handler pins the per-taxon active
 *     tab to "folder" before delegating to `handleSelect(id)`,
 *     mirroring `web/nav.js::open-folder-tab` byte-for-byte.
 *     ODD-TDDISC-001 ALSO
 *     adds a compact Material Symbols `visibility` icon control
 *     on every row (`data-action="open-details"`) that calls
 *     `onSelect(taxon.id)` directly — the discoverable
 *     detail-panel entry point that the kebab rename alone
 *     cannot provide.
 *   - Source switches clear focused + selected + every
 *     source-bound React state (roots, child cache, expanded set,
 *     load status, showAll, per-row error, kebab). Mirrors the
 *     legacy `web/nav.js::tree-source toggle` reset byte-for-byte.
 *   - Collapse-all clears expanded + showAll + kebab, but
 *     PRESERVES focused + selected (the legacy `collapseAll` does
 *     not clear them). Selection is independent of expansion.
 *   - The native-style breadcrumb above the tree is rendered from
 *     `walkBreadcrumbForSource(state.focused, activeSource, state)`,
 *     which dispatches on the active source internally:
 *       * CoL reads `Taxon.parent_id`
 *       * Freshwater reads `Taxon.freshwater_parent_id`
 *       * WoRMS reconstructs ancestry from `deriveWoRMSEdges(state)`,
 *         a reverse index derived from `childIdsByParent` that only
 *         carries source-safe WoRMS edges (the FastAPI wire does
 *         not expose `worms_parent_id`; see ODD-NTP-001 note in
 *         `domain/taxon.ts`).
 *     The breadcrumb truncates at the focused taxon when no source-
 *     safe ancestors are cached, applies the 30-hop cycle cap, and
 *     never crosses source boundaries.
 *   - Breadcrumb activation routes through `handleFocusSegment(id)`:
 *     expand-ancestors + focused = id + selected = id. The walker
 *     never fabricates edges: it only expands ids that already
 *     exist in the cached `childIdsByParent` map (a row can only
 *     become a parent of another row if the user previously
 *     attached its children under the active source).
 *   - Native scroll/focus intent: pressing `select` scrolls the
 *     focused row into view (block: "nearest") so the legacy "row
 *     comes from search" affordance carries forward as a single
 *     `scrollIntoView` call. Browser capability governs whether
 *     the scroll is smooth or instant.
 *
 * ODD-NTP-002 — native source parity:
 *   - The legacy native tree exposes three independent source views
 *     (CoL / WoRMS / Freshwater) with a segmented control inside
 *     the tree surface. The React tree mirrors that contract: a
 *     compact selector renders inside the tree section, CoL starts
 *     active, WoRMS always appears, Freshwater appears only when
 *     the fetched root payload contains at least one row with a
 *     non-null `freshwater_id`.
 *   - Source filtering happens client-side against the already-fetched
 *     raw root response (FastAPI `/api/domains` currently ignores
 *     the `source` query parameter; ODD-NTP-001 documents the
 *     contract). The raw root cache survives a source switch so the
 *     user sees an instant roots re-display, not a refetch.
 *   - Child requests go through canonical
 *     `fetchChildren(id, { source: activeSource })` and apply the
 *     same `sourceMatches` predicate before attachment. Foreign
 *     rows from a previous source's hierarchy never enter the
 *     visible child list.
 *   - A source switch clears every source-bound piece of state
 *     (roots, child cache, expanded set, load status, showAll,
 *     per-row error, focused, selected, kebab) before re-displaying
 *     the new source's roots. The raw root cache SURVIVES the
 *     switch.
 *
 * ODD-NTP-003 — native structural parity:
 *   - Each taxon renders as a real block row (not a
 *     `display: contents` grid placeholder) so the depth indent
 *     applies to the WHOLE identity + disclosure block.
 *   - Loaded children are grouped by native rank tier
 *     (`groupChildrenByRank`) and rendered with native tier
 *     headers — one header per rank group with `count > 1`,
 *     sitting at depth+1, with a "Load N more" affordance that
 *     calls `toggleShowAll(state, parentId, rank)`. The
 *     PAGE_SIZE=5 staircase matches the legacy
 *     `web/state.js::PAGE_SIZE` constant.
 *   - Source-specific auto-unroll: when `activeSource === "worms"`
 *     or `"freshwater"`, expanding a node adds
 *     `${parentId}::${rank}` to `showAll` for every child rank.
 *     CoL view keeps the PAGE_SIZE staircase.
 *   - Native collapse-all control clears both the expanded set AND
 *     every `showAll` flag, returning the tree to a flat roots-
 *     only view.
 *   - Leaf disclosure: species / subspecies rows render with a
 *     `•` glyph (no chevron), are `disabled`, and stamp
 *     `data-action="select"` so the ODD-NTP-005 selection handler
 *     dispatches directly on them. Higher ranks render with
 *     ▾/▸ and stamp `data-action="toggle-expand"`.
 *
 * ODD-NTP-004 — native row identity and source affordances:
 *   - Ported pure native row formatting, realm tint, status /
 *     extinction / count / source / folder indicators, source
 *     tooltip / cross-link, and accessible kebab state. The
 *     "View on WoRMS" kebab item is wired (anchor + target).
 *     "View details" (RENAMED from "Search online" in
 *     ODD-TDDISC-001 for discoverability; the
 *     `data-action="open-searches"` contract stays) is wired in
 *     ODD-NTP-005 to call `handleSelect(id)`. "Open folder"
 *     (rendered only for materialized rows) is enabled by
 *     ODD-OPENFOLDER-001: the handler routes through the
 *     selection/focus primitive AND pins the per-taxon active
 *     tab to "folder", mirroring `web/nav.js::open-folder-tab`
 *     byte-for-byte.
 *
 * Base URL comes from `process.env.NEXT_PUBLIC_TAXA_API_ORIGIN`
 * (inlined at build time). The variable is unset for production
 * static exports — requests stay relative / same-origin so the
 * future FastAPI `out/` mount can serve `/api/domains` from the
 * same origin.
 *
 * Accessibility:
 *   - initial loading → `role="status"`
 *   - initial error → `role="alert"` with a "Retry" button
 *   - empty roots → quiet "No domains returned" copy
 *   - per-row child-load error → inline `role="alert"` with retry
 *   - source selector → `role="group"` with `aria-pressed` on each
 *     button
 *   - tier header "Load N more" → `role="button"` with `aria-label`
 *   - collapse-all control → `disabled` + `aria-disabled` when no
 *     expansion exists
 *   - breadcrumb → `aria-label="Active taxonomy path"` with each
 *     segment rendered as a button (focusable + keyboard
 *     activatable) and the focused taxon rendered as text
 *
 * spec.md rule 4: presentation → taxonomy module. The recursive
 * row flattening lives here so the `.taxa-tree` block layout can
 * stack each row + its tier headers + its visible children as a
 * vertical sequence at the right depth.
 */
import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import {
  BREADCRUMB_MAX_HOPS,
  fetchChildren,
  fetchDomains,
  fetchSearches,
  fetchVernaculars,
  fetchSynonyms,
  fetchDistribution,
  openFolder,
  materializeResearch,
  previewMaterialize,
  walkBreadcrumbForSource,
} from "@taxa/taxonomy";
// ODD-BSTATE-TAX-001 — the CoL / WoRMS / Freshwater selector
// moved from local React state to the typed browser-state store
// (`useTreeSource`). The hook returns the typed `col` default on
// SSR + the first client render (so React's hydration guard never
// trips on a stored value) and the stored value on the post-mount
// render. The typed default lives in the browser-state module's
// domain layer so every consumer agrees on the first-render
// value. The local `DEFAULT_SOURCE` constant was retired — the
// typed store is the single source of truth.
//
// ODD-BSTATE-TAX-002 — strict-continuation: the main route
// imports `useTreeSource` through the dedicated
// `@taxa/browser-state/tree-source` entry point (NOT through the
// aggregate `@taxa/browser-state` barrel). The aggregate barrel
// re-exports every per-key hook + store + the reset aggregate,
// and Turbopack groups the four per-key stores into a shared
// chunk that the main route ends up referencing — which fails
// the strict chunk-boundary witness in
// `tests/test_app_shell_render.py::test_out_index_html_chunks_permit_only_tree_source_key`.
// The dedicated entry point re-exports ONLY the typed-source
// surface so the strict chunk-boundary contract holds.
import { useTreeSource } from "@taxa/browser-state/tree-source";
import type {
  DistributionEntry,
  MaterializePreview,
  OpenFolderResult,
  SearchLink,
  SynonymName,
  TaxonomySource,
  VernacularName,
} from "@taxa/taxonomy";
import type { BreadcrumbSegment } from "./breadcrumb-path";
import type { Rank, Taxon } from "../domain/taxon";
import DetailPanel, {
  DEFAULT_DETAIL_TAB,
} from "./DetailPanel";
import type { DetailTabKey } from "./DetailPanel";
import type { SearchTabStatus } from "./SearchTab";
import type { SynonymTabStatus } from "./SynonymTab";
import type { VernacularTabStatus } from "./VernacularTab";
import type { DistributionTabStatus } from "./DistributionTab";
import type {
  FolderCopyStatus,
  FolderCreateStatus,
  FolderOpenStatus,
  FolderTabStatus,
} from "./FolderTab";
import {
  EMPTY_TREE_STATE,
  attachChildrenForSource,
  autoUnrollForSource,
  availableSourcesFor,
  childIds,
  clearExpansion,
  expandedTierCount,
  groupChildrenByRank,
  isExpanded,
  loadStatus,
  resetSourceState,
  setLoadStatus,
  setShowAll,
  sourceMatches,
  toggleExpand,
  withRootsForSource,
} from "./tree-state";
import type {
  NodeLoadStatus,
  RankGroup,
  TreeSource,
  TreeState,
} from "./tree-state";
import TreeRow from "./TreeRow";

type RootStatus = "idle" | "loading" | "loaded" | "error" | "empty";

interface RootState {
  readonly status: RootStatus;
  readonly message: string | null;
}

interface RawRoots {
  /** The canonical fetched root payload, unfiltered. Preserved across
   *  source switches so flipping between CoL / WoRMS / Freshwater does
   *  not refetch `/api/domains`. Mirrors the legacy
   *  `web/state.js::roots` cache shape. */
  readonly taxa: readonly Taxon[];
}

/** Inlined at build time by Next.js. Defaults to the relative
 *  same-origin path `"/api"` so the React static export (which does
 *  NOT receive `NEXT_PUBLIC_TAXA_API_ORIGIN` from a `.env` file
 *  shipped at `out/`) calls `fetchDomains({ baseUrl: "/api" })`
 *  instead of resolving an empty string into an absolute URL with a
 *  trailing-slash side effect that breaks FastAPI route matching. */
const TAXA_API_ORIGIN: string =
  process.env.NEXT_PUBLIC_TAXA_API_ORIGIN ?? "/api";

function messageFor(err: unknown, prefix: string): string {
  const detail = err instanceof Error ? err.message : String(err);
  return `${prefix}: ${detail}`;
}

function rankPluralFor(rank: Rank): string {
  const irregular: Partial<Record<Rank, string>> = {
    phylum: "phyla",
    class: "classes",
    family: "families",
    genus: "genera",
    variety: "varieties",
    subphylum: "subphyla",
    subclass: "subclasses",
    subfamily: "subfamilies",
    subgenus: "subgenera",
    suborder: "suborders",
    subkingdom: "subkingdoms",
    subvariety: "subvarieties",
  };
  if (irregular[rank]) return irregular[rank]!;
  const label = rank.charAt(0).toUpperCase() + rank.slice(1);
  return `${label}s`;
}

export default function TaxonomyTree(): React.ReactElement {
  // ODD-BSTATE-TAX-001 — the CoL / WoRMS / Freshwater selector
  // now reads + writes through the typed browser-state store via
  // `useTreeSource()`. The hook returns the typed default
  // (`"col"`) on SSR + the first client render, so React's
  // hydration guard never trips on a stored value; the stored
  // value rehydrates on the post-mount render. The setter is a
  // stable callback (React identity preserved across renders)
  // that mirrors the typed `writeTreeSource` surface. The local
  // `TreeSource` type literal union is structurally compatible
  // with the browser-state `TreeSource` type so a cast is NOT
  // required at the boundary.
  const [activeSource, setActiveSource] = useTreeSource();
  const [rawRoots, setRawRoots] = useState<RawRoots | null>(null);
  const [state, setState] = useState<TreeState>(EMPTY_TREE_STATE);
  const [root, setRoot] = useState<RootState>({
    status: "idle",
    message: null,
  });
  // ODD-NTP-004 — kebab open state. Lives at the tree level so a
  // click-outside / Escape dismisses every open menu at once and
  // the visible tree carries only one open kebab at a time.
  const [kebabOpenId, setKebabOpenId] = useState<number | null>(null);
  // ODD-NTP-005 — focused + selected navigation state. Mirrors the
  // legacy `web/state.js::focused` + `selected` pair. `focused`
  // drives the breadcrumb; `selected` is the row the user has
  // committed to (used by the detail panel + URL hash in the
  // legacy oracle; the React cutover keeps both fields for the
  // upcoming ODD-NTP-007 detail panel but currently only paints
  // the focused / selected row affordances).
  const [focused, setFocused] = useState<number | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  // ODD-TDO-001 — per-taxon active-tab memory. The legacy
  // `web/state.js::activeTab` is a `{[taxonId]: tabKey}` map; the
  // React port mirrors the same shape so the user lands on the
  // last-tab-they-used when re-selecting a previously selected
  // taxon. The default is `DEFAULT_DETAIL_TAB` (`"overview"`) for
  // any newly selected taxon; the map is reset whenever the
  // source switches (a stale tab key from the previous source's
  // cache has no meaning under the new one).
  const [perTaxonActiveTab, setPerTaxonActiveTab] = useState<
    Map<number, DetailTabKey>
  >(() => new Map());
  // ODD-TDS-001 — per-taxon search-link cache. Mirrors the
  // `perTaxonActiveTab` shape so re-selecting a previously selected
  // taxon lands on the cached result without a round trip; the
  // eager-fetch-on-selection effect below fires the request the
  // moment a taxon becomes the active selection, so clicking the
  // Search tab paints the rendered link grid instantly. A source
  // switch clears the cache (a stale link list from the previous
  // source has no meaning under the new one — the URLs themselves
  // are taxon-name-based and source-agnostic, but clearing keeps
  // the panel contract aligned with the other source-bound caches).
  // Status is the discriminated-union shape the SearchTab consumes:
  //   idle    — no request issued yet (default for never-selected taxa)
  //   loading — request in flight
  //   loaded  — server-composed links cached; empty array allowed
  //   error   — last attempt failed; retry available
  const [searchesByTaxonId, setSearchesByTaxonId] = useState<
    Map<number, SearchTabStatus>
  >(() => new Map());
  // ODD-TDV-001 — per-taxon vernacular cache. Same shape as the
  // search-link cache so the DetailPanel contract stays symmetric
  // across the Search and Vernaculars tabs. Source switch
  // behaviour DIFFERS from the search-link cache: the
  // `/api/taxon/{id}/vernaculars` endpoint is source-AGNOSTIC
  // (mirrors the legacy `web/detail.js::loadDetail` payload which
  // is also source-agnostic), so a previously cached vernacular
  // payload stays valid under a new active source. The cache
  // therefore survives `handleSourceChange` so re-selecting the
  // same taxon after a source switch is also instant. The
  // `handleSourceChange` callback intentionally does NOT clear
  // this map. Status is the discriminated-union shape the
  // VernacularTab consumes (idle / loading / loaded / empty /
  // error — byte-identical to `SearchTabStatus`).
  const [vernacularsByTaxonId, setVernacularsByTaxonId] = useState<
    Map<number, VernacularTabStatus>
  >(() => new Map());
  // ODD-TDSYN-001 — per-taxon synonyms cache. Same shape as the
  // vernacular cache so the DetailPanel contract stays symmetric
  // across the Vernaculars and Synonyms tabs. The
  // `/api/taxon/{id}/synonyms` endpoint is source-AGNOSTIC
  // (mirrors the legacy `web/detail.js::loadDetail` payload —
  // the FastAPI SQL pre-filters by `parent_id = taxon_id AND
  // status != 'accepted'` regardless of the active tree source),
  // so a previously cached synonym payload stays valid under a
  // new active source. The cache therefore survives
  // `handleSourceChange` so re-selecting the same taxon after a
  // source switch is also instant. The `handleSourceChange`
  // callback intentionally does NOT clear this map (mirrors the
  // ODD-TDV-001 source-agnostic retention contract). Status is
  // the discriminated-union shape the SynonymTab consumes
  // (idle / loading / loaded / empty / error — byte-identical to
  // `SearchTabStatus` + `VernacularTabStatus`).
  const [synonymsByTaxonId, setSynonymsByTaxonId] = useState<
    Map<number, SynonymTabStatus>
  >(() => new Map());
  // ODD-TDDIST-001 — per-taxon distribution cache. Same shape as
  // the vernacular + synonyms caches so the DetailPanel contract
  // stays symmetric across the Vernaculars, Synonyms, and
  // Distribution tabs. The `/api/taxon/{id}/distribution` endpoint
  // is source-AGNOSTIC (mirrors the legacy `web/detail.js::loadDetail`
  // payload — the FastAPI SQL filters by `taxon_id = ?` regardless
  // of the active tree source), so a previously cached distribution
  // payload stays valid under a new active source. The cache
  // therefore survives `handleSourceChange` so re-selecting the
  // same taxon after a source switch is also instant. The
  // `handleSourceChange` callback intentionally does NOT clear
  // this map (mirrors the ODD-TDV-001 + ODD-TDSYN-001
  // source-agnostic retention contract). Status is the
  // discriminated-union shape the DistributionTab consumes
  // (idle / loading / loaded / empty / error — byte-identical to
  // `SearchTabStatus` + `VernacularTabStatus` + `SynonymTabStatus`).
  const [distributionByTaxonId, setDistributionByTaxonId] = useState<
    Map<number, DistributionTabStatus>
  >(() => new Map());
  // ODD-TDFOLDER-001 — per-taxon folder cache. Mirrors the
  // distribution cache byte-for-byte: the parent owns the cache
  // so re-selecting a previously selected taxon lands on the
  // cached preview without a round trip; the eager-fetch-on-
  // selection contract fires the request the moment a taxon
  // becomes the active selection. Status is the discriminated-
  // union shape the FolderTab consumes (idle / loading /
  // loaded / error). The cache is INVALIDATED on source
  // switches — unlike the source-AGNOSTIC
  // vernaculars/synonyms/distribution caches, the materialize
  // preview walks the active source's parent column, so a
  // stale preview under CoL yields a different chain under
  // WoRMS when the parent_id columns diverge. The
  // `handleSourceChange` callback calls
  // `setFolderByTaxonId(new Map())` to enforce the contract.
  const [folderByTaxonId, setFolderByTaxonId] = useState<
    Map<number, FolderTabStatus>
  >(() => new Map());
  // ODD-TDFOLDER-001 — per-taxon create-status + open-status +
  // copy-status side-effect states. Lives at the tree level
  // (not inside FolderTab) so the cache + the side-effect
  // transitions share the same React render frame as the rest
  // of the detail panel. The create status survives until the
  // user clicks Create again or switches taxa (mirrors how the
  // search cache survives across deselects); the open + copy
  // statuses clear when the user closes the panel OR switches
  // sources / taxa (they're ephemeral affordances — the user
  // does not need to see "Opened with `open`" after they
  // navigated away).
  const [folderCreateByTaxonId, setFolderCreateByTaxonId] = useState<
    Map<number, FolderCreateStatus>
  >(() => new Map());
  const [folderOpenByTaxonId, setFolderOpenByTaxonId] = useState<
    Map<number, FolderOpenStatus>
  >(() => new Map());
  const [folderCopyByTaxonId, setFolderCopyByTaxonId] = useState<
    Map<number, FolderCopyStatus>
  >(() => new Map());
  // ODD-TDFOLDER-001 — in-tab create-confirmation gate. When
  // `true`, the FolderTab renders the Confirm row instead of
  // the bare CTA. Lives at the tree level so a source switch /
  // taxon switch clears the gate (the stale confirmation has
  // no meaning under the new source / taxon). The renderer
  // never sets the gate directly; the user must click the
  // bare CTA to arm it.
  const [folderCreateArmedByTaxonId, setFolderCreateArmedByTaxonId] = useState<
    Map<number, boolean>
  >(() => new Map());
  // ODD-NTP-005 — ref to the most recently selected row so the
  // scroll-into-view call after `select` lands on the right DOM
  // node even when the same id was already focused. The ref is
  // a Map keyed by taxon id so multiple rows can keep their
  // last-known DOM nodes (selection only ever targets one id at
  // a time, but the map gives the component a stable read point
  // that survives React's reconciliation).
  const rowRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  // ODD-NTP-005 — select-pulse trigger. Bumped on every successful
  // `select` so the row renders a brief pulse affordance (mirrors
  // the legacy `web/nav.js::select-from-search` `search-pulse`
  // animation). The pulse expires after one render frame so the
  // animation can re-fire on rapid repeat-selects.
  const [pulseNonce, setPulseNonce] = useState<number>(0);

  // ODD-NTP-005 — derive the source-safe breadcrumb from the
  // cached tree state. Recomputed every render so source switches,
  // child attachments, and focus changes all reflect in the
  // rendered breadcrumb without a stale-snapshot race. The walker
  // returns `[]` when `focused` is null, so the React render
  // collapses to an empty breadcrumb host without a conditional.
  const breadcrumbSegments = useMemo<readonly BreadcrumbSegment[]>(() => {
    if (focused === null) return [];
    return walkBreadcrumbForSource(focused, activeSource, state);
  }, [focused, activeSource, state]);

  // `loadRoots` fetches `/api/domains` ONCE on mount. It deliberately
  // does NOT close over `activeSource` — the source filter is
  // applied by the `rawRoots + activeSource` effect below.
  const loadRoots = useCallback(async () => {
    setRoot({ status: "loading", message: null });
    try {
      const taxa = await fetchDomains({ baseUrl: TAXA_API_ORIGIN });
      if (taxa.length === 0) {
        setRawRoots(null);
        setState(EMPTY_TREE_STATE);
        setRoot({ status: "empty", message: null });
      } else {
        setRawRoots({ taxa });
        setRoot({ status: "loaded", message: null });
      }
    } catch (err) {
      setRoot({
        status: "error",
        message: messageFor(err, "Could not load taxonomy domains"),
      });
    }
  }, []);

  useEffect(() => {
    void loadRoots();
  }, [loadRoots]);

  // ODD-NTP-004 — Escape dismisses any open kebab menu. Mirrors
  // the legacy `web/nav.js::keydown` listener.
  useEffect(() => {
    if (kebabOpenId === null) return;
    const onKeyDown = (ev: KeyboardEvent): void => {
      if (ev.key === "Escape") setKebabOpenId(null);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [kebabOpenId]);

  // ODD-NTP-004 — click-outside dismisses any open kebab menu.
  useEffect(() => {
    if (kebabOpenId === null) return;
    const onMouseDown = (ev: MouseEvent): void => {
      const target = ev.target;
      if (!(target instanceof Element)) {
        setKebabOpenId(null);
        return;
      }
      if (target.closest(".kebab")) return;
      setKebabOpenId(null);
    };
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, [kebabOpenId]);

  // Apply the active source to the raw root payload. Fires when
  // (a) `rawRoots` first becomes non-null after a successful
  // fetch, or (b) `activeSource` changes mid-session.
  useEffect(() => {
    if (!rawRoots) return;
    setState((prev) =>
      withRootsForSource(resetSourceState(prev), rawRoots.taxa, activeSource),
    );
  }, [activeSource, rawRoots]);

  const loadChildren = useCallback(
    async (id: number) => {
      setState((prev) => setLoadStatus(prev, id, "loading"));
      try {
        const kids = await fetchChildren(id, {
          baseUrl: TAXA_API_ORIGIN,
          source: activeSource as TaxonomySource,
        });
        setState((prev) => {
          const attached = attachChildrenForSource(
            prev, id, kids, activeSource,
          );
          if (isExpanded(attached, id) &&
              (activeSource === "worms" || activeSource === "freshwater")) {
            return autoUnrollForSource(attached, id, activeSource);
          }
          return attached;
        });
      } catch (err) {
        setState((s) => setLoadStatus(s, id, "error"));
        setRoot(() => ({
          status: "loaded",
          message: messageFor(err, `Could not load children of taxon ${id}`),
        }));
      }
    },
    [activeSource],
  );

  const handleToggle = useCallback(
    (id: number) => {
      const wasExpanded = isExpanded(state, id);
      const knownChildren = childIds(state, id);
      if (wasExpanded) {
        setState((prev) => {
          const collapsed = toggleExpand(prev, id);
          return collapseNodeTiers(collapsed, id);
        });
      } else {
        setState((prev) => toggleExpand(prev, id));
        if (knownChildren.length === 0) {
          void loadChildren(id);
        } else {
          setState((prev) => autoUnrollForSource(prev, id, activeSource));
        }
      }
    },
    [state, activeSource, loadChildren],
  );

  const handleRetryChild = useCallback(
    (id: number) => {
      void loadChildren(id);
    },
    [loadChildren],
  );

  // ODD-TDS-001 — per-taxon search-link loader. Reads the cached
  // `searchesByTaxonId` map and skips the round trip if a previous
  // load already landed (loaded or errored) for the same taxon.
  // The eager-fetch-on-selection effect below triggers this callback
  // on every selection change so the cache stays warm by the time
  // the user clicks the Search tab. The callback also fires from
  // the SearchTab's Retry button so a transient failure (network
  // blip, 5xx) is recoverable without a fresh taxon selection.
  const loadSearches = useCallback(
    async (id: number) => {
      // Already cached (loaded OR errored) — no round trip.
      // A fresh `error` is treated as cacheable so the user can
      // manually trigger the retry via the panel button rather
      // than re-select the taxon.
      const current = searchesByTaxonId.get(id);
      if (current && (current.kind === "loaded" || current.kind === "error")) {
        return;
      }
      setSearchesByTaxonId((prev) => {
        const next = new Map(prev);
        next.set(id, { kind: "loading" });
        return next;
      });
      try {
        const links: readonly SearchLink[] = await fetchSearches(id, {
          baseUrl: TAXA_API_ORIGIN,
        });
        setSearchesByTaxonId((prev) => {
          const next = new Map(prev);
          if (links.length === 0) {
            next.set(id, { kind: "empty" });
          } else {
            next.set(id, { kind: "loaded", links });
          }
          return next;
        });
      } catch (err) {
        setSearchesByTaxonId((prev) => {
          const next = new Map(prev);
          next.set(id, {
            kind: "error",
            message: messageFor(err, `Could not load search links of taxon ${id}`),
          });
          return next;
        });
      }
    },
    // `searchesByTaxonId` is intentionally NOT in the deps: the
    // callback reads the latest cache through the functional
    // updater, so listing it would force a fresh `loadSearches`
    // identity on every cache mutation and re-trigger the
    // eager-fetch effect below. The callback identity is stable
    // across cache mutations so the effect stays a one-shot
    // per-selection-change fire.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  // ODD-TDV-001 — per-taxon vernacular loader. Reads the cached
  // `vernacularsByTaxonId` map and skips the round trip if a
  // previous load already landed (loaded / empty / errored) for
  // the same taxon. The eager-fetch-on-selection effect below
  // triggers this callback on every selection change so the
  // cache stays warm by the time the user clicks the Vernaculars
  // tab. The callback also fires from the VernacularTab's Retry
  // button so a transient failure (network blip, 5xx) is
  // recoverable without a fresh taxon selection. The callback
  // intentionally does NOT depend on `activeSource` — the
  // `/api/taxon/{id}/vernaculars` endpoint is source-agnostic
  // (mirrors the legacy `web/detail.js::loadDetail` payload
  // shape), so the cache survives source switches.
  const loadVernaculars = useCallback(
    async (id: number) => {
      const current = vernacularsByTaxonId.get(id);
      if (
        current &&
        (current.kind === "loaded" ||
          current.kind === "empty" ||
          current.kind === "error")
      ) {
        return;
      }
      setVernacularsByTaxonId((prev) => {
        const next = new Map(prev);
        next.set(id, { kind: "loading" });
        return next;
      });
      try {
        const names: readonly VernacularName[] = await fetchVernaculars(id, {
          baseUrl: TAXA_API_ORIGIN,
          limit: 200,
        });
        setVernacularsByTaxonId((prev) => {
          const next = new Map(prev);
          if (names.length === 0) {
            next.set(id, { kind: "empty" });
          } else {
            next.set(id, { kind: "loaded", names });
          }
          return next;
        });
      } catch (err) {
        setVernacularsByTaxonId((prev) => {
          const next = new Map(prev);
          next.set(id, {
            kind: "error",
            message: messageFor(err, `Could not load vernaculars of taxon ${id}`),
          });
          return next;
        });
      }
    },
    // `vernacularsByTaxonId` is intentionally NOT in the deps: the
    // callback reads the latest cache through the functional
    // updater, so listing it would force a fresh `loadVernaculars`
    // identity on every cache mutation and re-trigger the
    // eager-fetch effect below. The callback identity is stable
    // across cache mutations so the effect stays a one-shot
    // per-selection-change fire (same rationale as
    // `loadSearches`).
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  // ODD-TDSYN-001 — per-taxon synonyms loader. Reads the cached
  // `synonymsByTaxonId` map and skips the round trip if a
  // previous load already landed (loaded / empty / errored) for
  // the same taxon. The eager-fetch-on-selection effect below
  // triggers this callback on every selection change so the
  // cache stays warm by the time the user clicks the Synonyms
  // tab. The callback also fires from the SynonymTab's Retry
  // button so a transient failure (network blip, 5xx) is
  // recoverable without a fresh taxon selection. The callback
  // intentionally does NOT depend on `activeSource` — the
  // `/api/taxon/{id}/synonyms` endpoint is source-agnostic
  // (mirrors the legacy `web/detail.js::loadDetail` payload
  // shape), so the cache survives source switches (the
  // `handleSourceChange` callback deliberately does NOT call
  // `setSynonymsByTaxonId(new Map())`, mirroring the
  // ODD-TDV-001 source-agnostic retention contract).
  const loadSynonyms = useCallback(
    async (id: number) => {
      const current = synonymsByTaxonId.get(id);
      if (
        current &&
        (current.kind === "loaded" ||
          current.kind === "empty" ||
          current.kind === "error")
      ) {
        return;
      }
      setSynonymsByTaxonId((prev) => {
        const next = new Map(prev);
        next.set(id, { kind: "loading" });
        return next;
      });
      try {
        const names: readonly SynonymName[] = await fetchSynonyms(id, {
          baseUrl: TAXA_API_ORIGIN,
          limit: 200,
        });
        setSynonymsByTaxonId((prev) => {
          const next = new Map(prev);
          if (names.length === 0) {
            next.set(id, { kind: "empty" });
          } else {
            next.set(id, { kind: "loaded", names });
          }
          return next;
        });
      } catch (err) {
        setSynonymsByTaxonId((prev) => {
          const next = new Map(prev);
          next.set(id, {
            kind: "error",
            message: messageFor(err, `Could not load synonyms of taxon ${id}`),
          });
          return next;
        });
      }
    },
    // `synonymsByTaxonId` is intentionally NOT in the deps: the
    // callback reads the latest cache through the functional
    // updater, so listing it would force a fresh `loadSynonyms`
    // identity on every cache mutation and re-trigger the
    // eager-fetch effect below. The callback identity is stable
    // across cache mutations so the effect stays a one-shot
    // per-selection-change fire (same rationale as
    // `loadSearches` + `loadVernaculars`).
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  // ODD-TDDIST-001 — per-taxon distribution loader. Reads the
  // cached `distributionByTaxonId` map and skips the round trip
  // if a previous load already landed (loaded / empty / errored)
  // for the same taxon. The eager-fetch-on-selection effect
  // below triggers this callback on every selection change so
  // the cache stays warm by the time the user clicks the
  // Distribution tab. The callback also fires from the
  // DistributionTab's Retry button so a transient failure
  // (network blip, 5xx) is recoverable without a fresh taxon
  // selection. The callback intentionally does NOT depend on
  // `activeSource` — the `/api/taxon/{id}/distribution`
  // endpoint is source-agnostic (mirrors the legacy
  // `web/detail.js::loadDetail` payload shape), so the cache
  // survives source switches (the `handleSourceChange` callback
  // deliberately does NOT call `setDistributionByTaxonId(new
  // Map())`, mirroring the ODD-TDV-001 + ODD-TDSYN-001
  // source-agnostic retention contract).
  const loadDistribution = useCallback(
    async (id: number) => {
      const current = distributionByTaxonId.get(id);
      if (
        current &&
        (current.kind === "loaded" ||
          current.kind === "empty" ||
          current.kind === "error")
      ) {
        return;
      }
      setDistributionByTaxonId((prev) => {
        const next = new Map(prev);
        next.set(id, { kind: "loading" });
        return next;
      });
      try {
        const entries: readonly DistributionEntry[] = await fetchDistribution(id, {
          baseUrl: TAXA_API_ORIGIN,
          limit: 200,
        });
        setDistributionByTaxonId((prev) => {
          const next = new Map(prev);
          if (entries.length === 0) {
            next.set(id, { kind: "empty" });
          } else {
            next.set(id, { kind: "loaded", entries });
          }
          return next;
        });
      } catch (err) {
        setDistributionByTaxonId((prev) => {
          const next = new Map(prev);
          next.set(id, {
            kind: "error",
            message: messageFor(err, `Could not load distribution of taxon ${id}`),
          });
          return next;
        });
      }
    },
    // `distributionByTaxonId` is intentionally NOT in the deps:
    // the callback reads the latest cache through the functional
    // updater, so listing it would force a fresh `loadDistribution`
    // identity on every cache mutation and re-trigger the
    // eager-fetch effect below. The callback identity is stable
    // across cache mutations so the effect stays a one-shot
    // per-selection-change fire (same rationale as
    // `loadSearches` + `loadVernaculars` + `loadSynonyms`).
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  // ODD-TDFOLDER-001 — per-taxon materialize-preview loader.
  // Reads the cached `folderByTaxonId` map and skips the round
  // trip if a previous load already landed (loaded or errored)
  // for the same taxon. The eager-fetch-on-selection effect
  // below triggers this callback on every selection change so
  // the cache stays warm by the time the user clicks the
  // Folder tab. The callback also fires from the FolderTab's
  // Retry button so a transient failure (network blip, 5xx) is
  // recoverable without a fresh taxon selection. The callback
  // CLOSES OVER `activeSource` (unlike `loadSearches` /
  // `loadVernaculars` / `loadSynonyms` / `loadDistribution`,
  // which are source-AGNOSTIC) — the materialize preview walks
  // the active source's parent column, so a cache hit under
  // CoL is stale when the user switches to WoRMS. The
  // `handleSourceChange` callback clears the cache to enforce
  // the source-aware invalidation contract.
  const loadFolderPreview = useCallback(
    async (id: number) => {
      const current = folderByTaxonId.get(id);
      if (current && (current.kind === "loaded" || current.kind === "error")) {
        return;
      }
      setFolderByTaxonId((prev) => {
        const next = new Map(prev);
        next.set(id, { kind: "loading" });
        return next;
      });
      try {
        const preview: MaterializePreview = await previewMaterialize(id, {
          baseUrl: TAXA_API_ORIGIN,
          source: activeSource as TaxonomySource,
        });
        setFolderByTaxonId((prev) => {
          const next = new Map(prev);
          next.set(id, { kind: "loaded", preview });
          return next;
        });
      } catch (err) {
        setFolderByTaxonId((prev) => {
          const next = new Map(prev);
          next.set(id, {
            kind: "error",
            message: messageFor(err, `Could not load folder preview of taxon ${id}`),
          });
          return next;
        });
      }
    },
    // `folderByTaxonId` is intentionally NOT in the deps: the
    // callback reads the latest cache through the functional
    // updater, so listing it would force a fresh
    // `loadFolderPreview` identity on every cache mutation
    // and re-trigger the eager-fetch effect below. The
    // callback identity is stable across cache mutations so
    // the effect stays a one-shot per-selection-change fire
    // (same rationale as `loadSearches` + `loadVernaculars` +
    // `loadSynonyms` + `loadDistribution`). `activeSource` IS
    // in the deps because the callback closes over it (the
    // source parameter is forwarded verbatim to the wire).
    [activeSource],
  );

  // ODD-TDFOLDER-001 — materialize-create handler. POSTs the
  // canonical `materializeResearch` request, then refreshes
  // the preview cache so the next render sees a fresh
  // `loaded` preview with `all_exist === true` and the
  // path-actions row replaces the create row. The handler is
  // guarded against a stale `selected` change mid-flight: if
  // the user switches taxa while the POST is in flight, the
  // success handler no-ops the cache refresh (the preview
  // belongs to the old taxon — switching it under the new
  // taxon would show a misleading "all_exist" banner for the
  // wrong path). The create-status state machine transitions
  // idle → creating → created | error so the renderer can
  // disable the CTA + paint inline success / error copy.
  const handleCreateResearchFolders = useCallback(
    async () => {
      if (selected === null) return;
      const taxonId = selected;
      setFolderCreateByTaxonId((prev) => {
        const next = new Map(prev);
        next.set(taxonId, { kind: "creating" });
        return next;
      });
      try {
        const result = await materializeResearch(taxonId, {
          baseUrl: TAXA_API_ORIGIN,
          source: activeSource as TaxonomySource,
        });
        // The user might have switched taxa mid-flight. The
        // success handler must not overwrite the create
        // status for the now-selected taxon (the success
        // belongs to the old taxon). We only commit when the
        // stored `selected` still matches the taxon we acted
        // on. The preview refresh is similarly guarded so a
        // stale source-switch race cannot leak the new
        // preview under the old taxon.
        const stillSelected = selected === taxonId;
        if (stillSelected) {
          setFolderCreateByTaxonId((prev) => {
            const next = new Map(prev);
            next.set(taxonId, { kind: "created", result });
            return next;
          });
          // Refresh the preview so the path-actions row
          // replaces the create row on the next render. We
          // short-circuit the cache by deleting the previous
          // entry so `loadFolderPreview` re-issues the GET;
          // a fresh preview will paint `all_exist === true`.
          setFolderByTaxonId((prev) => {
            const next = new Map(prev);
            next.delete(taxonId);
            return next;
          });
          void loadFolderPreview(taxonId);
        }
      } catch (err) {
        if (selected === taxonId) {
          setFolderCreateByTaxonId((prev) => {
            const next = new Map(prev);
            next.set(taxonId, {
              kind: "error",
              message: messageFor(err, `Could not materialize folders for taxon ${taxonId}`),
            });
            return next;
          });
        }
      } finally {
        // Disarm the gate regardless of outcome so the
        // renderer drops back to the bare CTA (the success
        // path replaces it with the path-actions row, the
        // error path lets the user re-arm).
        setFolderCreateArmedByTaxonId((prev) => {
          const next = new Map(prev);
          next.delete(taxonId);
          return next;
        });
      }
    },
    [selected, activeSource, loadFolderPreview],
  );

  // ODD-TDFOLDER-001 — create-confirmation gate armers. The
  // user clicks the bare CTA → `handleArmCreate` flips the
  // gate to true → the renderer paints the Confirm row. The
  // user clicks Cancel OR the bare CTA again (re-arm is
  // idempotent) → `handleDisarmCreate` flips it back to
  // false. The gate is per-taxon so a re-select lands on the
  // bare CTA again (mirrors the search-link cache contract
  // that re-selecting a previously selected taxon lands on
  // the cached result — the gate is not part of the cache,
  // it lives in its own map so the cache stays read-only).
  const handleArmCreate = useCallback(() => {
    if (selected === null) return;
    setFolderCreateArmedByTaxonId((prev) => {
      const next = new Map(prev);
      next.set(selected, true);
      return next;
    });
  }, [selected]);

  const handleDisarmCreate = useCallback(() => {
    if (selected === null) return;
    setFolderCreateArmedByTaxonId((prev) => {
      const next = new Map(prev);
      next.delete(selected);
      return next;
    });
  }, [selected]);

  // ODD-TDFOLDER-001 — open-folder handler. POSTs the
  // canonical `openFolder` request; on success the
  // `folderOpenByTaxonId[taxonId]` entry becomes `opened`
  // carrying the canonical `OpenFolderResult` so the
  // renderer can paint the inline "Opened with `open`:
  // <relative_path>" copy. A 404 (folder not yet
  // materialized) surfaces as a `TaxonomyApiError`; the
  // renderer's inline error copy shows the failure message
  // and the user can re-issue via the path-actions row.
  const handleOpenResearchFolder = useCallback(async () => {
    if (selected === null) return;
    const taxonId = selected;
    setFolderOpenByTaxonId((prev) => {
      const next = new Map(prev);
      next.set(taxonId, { kind: "opening" });
      return next;
    });
    try {
      const result: OpenFolderResult = await openFolder(taxonId, {
        baseUrl: TAXA_API_ORIGIN,
        source: activeSource as TaxonomySource,
      });
      setFolderOpenByTaxonId((prev) => {
        const next = new Map(prev);
        next.set(taxonId, { kind: "opened", result });
        return next;
      });
    } catch (err) {
      if (selected === taxonId) {
        setFolderOpenByTaxonId((prev) => {
          const next = new Map(prev);
          next.set(taxonId, {
            kind: "error",
            message: messageFor(err, `Could not open folder for taxon ${taxonId}`),
          });
          return next;
        });
      }
    }
  }, [selected, activeSource]);

  // ODD-TDFOLDER-001 — copy-path handler. Reads the cached
  // `folderByTaxonId[selected]` payload, extracts
  // `preview.absolute_path` verbatim (the server is the
  // source of truth — the renderer never sees the clipboard
  // API directly, the parent owns the transport), and writes
  // it through `navigator.clipboard.writeText`. A clipboard
  // failure (NotAllowedError when the page lacks user
  // activation, or a SecurityError when the page is served
  // over a non-secure context) is caught gracefully — the
  // `folderCopyByTaxonId[taxonId]` entry becomes `error`
  // carrying the failure message so the renderer paints the
  // inline "Could not copy path: …" copy and the user can
  // retry without a tab refresh (the legacy
  // `web/detail.js::renderFolderTab::copyBtn` `showToast`
  // affordance lives here as inline copy — no new toast
  // dependency is required, per the ODD-TDFOLDER-001 user
  // constraint: "Use inline success/error states only; no new
  // toast dependency or transient notification system").
  const handleCopyResearchPath = useCallback(async () => {
    if (selected === null) return;
    const taxonId = selected;
    const cached = folderByTaxonId.get(taxonId);
    const path =
      cached && cached.kind === "loaded" ? cached.preview.absolute_path : null;
    if (path === null || path === undefined) return;
    try {
      if (
        typeof navigator === "undefined" ||
        !navigator.clipboard ||
        typeof navigator.clipboard.writeText !== "function"
      ) {
        throw new Error("clipboard API not available in this context");
      }
      await navigator.clipboard.writeText(path);
      setFolderCopyByTaxonId((prev) => {
        const next = new Map(prev);
        next.set(taxonId, { kind: "copied" });
        return next;
      });
    } catch (err) {
      if (selected === taxonId) {
        setFolderCopyByTaxonId((prev) => {
          const next = new Map(prev);
          next.set(taxonId, {
            kind: "error",
            message: messageFor(err, `Could not copy path for taxon ${taxonId}`),
          });
          return next;
        });
      }
    }
  }, [selected, folderByTaxonId]);

  const handleSourceChange = useCallback((next: TreeSource) => {
    if (next === activeSource) return;
    // ODD-NTP-005: a source switch clears focused + selected in
    // addition to the source-bound React state (the legacy
    // `web/nav.js::tree-source toggle` reset clears every
    // navigation field). Without this clear the breadcrumb would
    // briefly render the previous source's ancestor chain after
    // the source switch, then re-derive against the new cache.
    setState((prev) => resetSourceState(prev));
    setRoot((prev) => ({ status: prev.status, message: null }));
    setKebabOpenId(null);
    setFocused(null);
    setSelected(null);
    // ODD-TDS-001: a source switch also clears the per-taxon
    // search-link cache so the panel cannot render a stale URL
    // set from a previous source's selected taxon. The URLs
    // themselves are taxon-name-based and source-agnostic, but
    // clearing the cache keeps the panel contract aligned with
    // the other source-bound caches (focused / selected /
    // per-taxon-active-tab).
    setSearchesByTaxonId(new Map());
    // ODD-TDFOLDER-001: a source switch INVALIDATES the
    // per-taxon folder cache so the panel cannot render a
    // stale preview from the previous source. The materialize
    // preview walks the active source's parent column, so a
    // stale CoL preview yields a different chain under WoRMS
    // when the parent_id columns diverge — the
    // source-AGNOSTIC retention contract that protects the
    // vernaculars / synonyms / distribution caches does NOT
    // apply here. The folder-create / folder-open /
    // folder-copy side-effect states are also cleared so a
    // stale "Opened with `open`" message cannot bleed into
    // the next source's selection. The folder-create-armed
    // gate is cleared so the next source's first render
    // lands on the bare CTA.
    setFolderByTaxonId(new Map());
    setFolderCreateByTaxonId(new Map());
    setFolderOpenByTaxonId(new Map());
    setFolderCopyByTaxonId(new Map());
    setFolderCreateArmedByTaxonId(new Map());
    setActiveSource(next);
  }, [activeSource]);

  const handleLoadMore = useCallback(
    (parentId: number, rank: Rank) => {
      setState((prev) => setShowAll(prev, parentId, rank, true));
    },
    [],
  );

  const handleCollapseAll = useCallback(() => {
    // ODD-NTP-005: collapse-all preserves focused + selected (the
    // legacy `web/nav.js::collapseAll` does the same — collapsing
    // the tree does not clear the user's navigation intent).
    setState((prev) => clearExpansion(prev));
    setKebabOpenId(null);
  }, []);

  // ODD-NTP-005 — kebab trigger handler.
  const handleToggleKebab = useCallback((id: number) => {
    setKebabOpenId((prev) => (prev === id ? null : id));
  }, []);

  // ODD-TDO-001 — per-taxon active-tab memory primitives. The legacy
  // `web/state.js::activeTab` map survives every selection;
  // re-selecting a taxon lands the user on the last tab they used
  // for it (or the default for new taxa). The React port mirrors
  // the same shape. Reads always default to `DEFAULT_DETAIL_TAB`
  // so a freshly selected taxon lands on Overview.
  const getActiveTabFor = useCallback(
    (taxonId: number): DetailTabKey => {
      return perTaxonActiveTab.get(taxonId) ?? DEFAULT_DETAIL_TAB;
    },
    [perTaxonActiveTab],
  );

  const handleTabChange = useCallback(
    (taxonId: number, tab: DetailTabKey) => {
      setPerTaxonActiveTab((prev) => {
        const current = prev.get(taxonId);
        if (current === tab) return prev;
        const next = new Map(prev);
        next.set(taxonId, tab);
        return next;
      });
    },
    [],
  );

  // ODD-TDO-001 — close handler. Mirrors the legacy
  // `web/nav.js::close-detail` action: clears the selection so the
  // detail panel unmounts on the next render. The kebab + focused
  // states are NOT cleared (they belong to the tree surface, not
  // the detail surface; the legacy oracle keeps them too).
  const handleCloseDetail = useCallback(() => {
    setSelected(null);
  }, []);

  // ODD-NTP-005 — kebab item action handler. With ODD-NTP-005 the
  // navigation slice genuinely backs `open-searches` (select the
  // taxon). ODD-OPENFOLDER-001 enables `open-folder-tab` for
  // materialized rows: the handler pins the per-taxon active tab
  // to "folder" BEFORE `handleSelect(id)` runs so the detail panel
  // lands on the Folder tab on first render — matching the legacy
  // `web/nav.js::open-folder-tab` byte-for-byte (which set
  // `state.focused = id`, `state.activeTab[id] = "folder"`, then
  // `selectTaxon(id)`). `handleSelect` closes the kebab as a side
  // effect, so the menu dismissal contract stays intact. The
  // kebab item is rendered only for materialized rows on the
  // TreeRow side (`hasMaterializedFolder(taxon)` predicate stays
  // intact), so this handler is safe to dispatch unconditionally
  // on the action name.
  const handleKebabAction = useCallback(
    (
      id: number,
      action: "open-searches" | "open-folder-tab" | "view-on-worms",
    ) => {
      if (action === "open-searches") {
        // Mirrors the legacy `web/nav.js::open-searches` handler:
        // sets focused + selected so the breadcrumb rebuilds and
        // the row picks up the focused / selected affordances.
        handleSelect(id);
        return;
      }
      if (action === "open-folder-tab") {
        // ODD-OPENFOLDER-001 — pin the active tab to "folder"
        // first (matches `state.activeTab[id] = "folder"` in
        // `web/nav.js`), then select + focus the taxon via the
        // navigation primitive. The functional updater keeps the
        // per-taxon map immutable so React's render cycle stays
        // pure; `handleSelect` closes the kebab as a side effect
        // so the menu dismissal contract is preserved.
        setPerTaxonActiveTab((prev) => {
          const next = new Map(prev);
          next.set(id, "folder");
          return next;
        });
        handleSelect(id);
        return;
      }
      if (action === "view-on-worms") {
        // The anchor + target="_blank" already navigates; this
        // handler is the future hook for analytics / log lines.
      }
      setKebabOpenId(null);
    },
    // `handleSelect` is stable by useCallback identity; listing
    // it explicitly keeps the exhaustive-deps lint quiet.
    // `setPerTaxonActiveTab` uses the functional updater form so
    // the callback identity stays stable across cache mutations.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  // ODD-NTP-005 — selection primitive. Sets focused + selected to
  // `id` and triggers a pulse animation. Selection is ORTHOGONAL
  // to expansion: selecting a leaf never toggles expansion (leaves
  // have no children); selecting a non-leaf keeps the existing
  // expansion state intact. Mirrors the legacy
  // `web/nav.js::selectTaxon` predicate (focused = id, selected =
  // id; no expansion mutation).
  const handleSelect = useCallback(
    (id: number) => {
      if (!Number.isFinite(id)) return;
      // Close the kebab if the selected row had one open — the
      // legacy `selectTaxon` renders a fresh tree, and an open
      // kebab over the focused row would otherwise linger past
      // the select.
      setKebabOpenId(null);
      setFocused(id);
      setSelected(id);
      // Bump the pulse nonce so a freshly rendered row plays the
      // one-shot pulse animation. The nonce is a monotonic
      // counter; rows read it via `data-pulse-nonce` so the
      // `animation` property can re-trigger by toggling the
      // class.
      setPulseNonce((prev) => prev + 1);
    },
    [],
  );

  // ODD-NTP-005 — scroll the selected row into view. Browser
  // capability governs smoothness: `block: "nearest"` only
  // scrolls when the row is fully out of view, so a row the
  // user can already see stays put.
  useEffect(() => {
    if (selected === null) return;
    const el = rowRefs.current.get(selected);
    if (!el) return;
    // `scrollIntoView` is on the legacy `web/dom.js::scrollTaxonBelowCard`
    // helper, but the React cutover does not carry the sticky
    // detail card yet (the card lands in a future PR). Plain
    // `block: "nearest"` is the closest equivalent — it scrolls
    // the row into the viewport when it falls outside, never
    // centring it across the viewport.
    el.scrollIntoView({ block: "nearest", behavior: "auto" });
  }, [selected, pulseNonce]);

  // ODD-NTP-005 — expand the source-safe ancestor chain of `id`
  // so the breadcrumb activation reveals the row the user
  // clicked. The walker only expands ids already present in the
  // cached `childIdsByParent` map (a row can only become a parent
  // of another row if the user previously attached its children
  // under the active source); ids absent from the cache are
  // skipped so the chain stays source-safe. The walker is bounded
  // at `BREADCRUMB_MAX_HOPS` hops; the WoRMS reverse index comes
  // from the same `deriveWoRMSEdges` the breadcrumb walker uses,
  // so the expanded chain is byte-identical to the breadcrumb
  // path the user sees above the tree.
  const expandAncestorsOf = useCallback(
    async (id: number) => {
      const segments = walkBreadcrumbForSource(id, activeSource, state);
      // Walk oldest-first so we expand the chain root → leaf in
      // the same order the breadcrumb renders. Each ancestor is
      // already cached on the breadcrumb walk; only an ancestor
      // whose parent has the focused row in its cached
      // `childIdsByParent` attachment can become a "parent" in
      // the active source's view, so the expansion is source-safe
      // by construction.
      for (const seg of segments) {
        if (seg.id === id) continue;
        if (isExpanded(state, seg.id)) continue;
        // Load children if the cache is empty. Skip silently
        // when the cache already has no children (the row is a
        // source-safe leaf).
        if (childIds(state, seg.id).length === 0) {
          await loadChildren(seg.id);
        }
        setState((prev) => toggleExpand(prev, seg.id));
        if (activeSource === "worms" || activeSource === "freshwater") {
          setState((prev) => autoUnrollForSource(prev, seg.id, activeSource));
        }
      }
    },
    [activeSource, state, loadChildren],
  );

  // ODD-NTP-005 — breadcrumb segment activation. Replicates the
  // legacy `web/nav.js::focus-segment` handler: expand the
  // ancestors of the chosen segment + focus + select it.
  const handleFocusSegment = useCallback(
    async (id: number) => {
      if (!Number.isFinite(id)) return;
      setKebabOpenId(null);
      // `expandAncestorsOf` is async (loadChildren round trips);
      // we don't await so the click feels instant — the row
      // starts to expand on the next render frame, and the
      // focus + select apply immediately so the breadcrumb + row
      // affordances reflect the click before the children load.
      void expandAncestorsOf(id);
      setFocused(id);
      setSelected(id);
      setPulseNonce((prev) => prev + 1);
    },
    [expandAncestorsOf],
  );

  // ODD-NTP-005 — breadcrumb home click. Mirrors the legacy
  // `web/nav.js::focus-home` handler: clear focused + selected
  // (no expansion mutation — `collapseAll` is its own button).
  const handleFocusHome = useCallback(() => {
    setKebabOpenId(null);
    setFocused(null);
    setSelected(null);
  }, []);

  // ODD-TDS-001 — eager-fetch-on-selection contract. Whenever
  // `selected` becomes a non-null taxon id, fire the canonical
  // `fetchSearches` round trip so the Search tab activation
  // paints the link grid instantly. Re-selecting the same taxon
  // is a no-op (the `loadSearches` callback short-circuits on
  // `loaded` / `error` cached entries). Closing the panel
  // (selected → null) does NOT clear the cache — the cached
  // result survives across deselects so re-selecting the same
  // taxon later is also instant (mirrors how `perTaxonActiveTab`
  // memory survives across deselects).
  useEffect(() => {
    if (selected === null) return;
    void loadSearches(selected);
  }, [selected, loadSearches]);

  // ODD-TDV-001 — eager-fetch-on-selection contract for the
  // Vernaculars tab. Mirrors the SearchTab eager-fetch effect
  // byte-for-byte: whenever `selected` becomes a non-null taxon
  // id, fire the canonical `fetchVernaculars(id, { limit: 200 })`
  // round trip so the Vernaculars tab activation paints the
  // rendered `Vernacular names` header + count + per-row chips
  // + name span instantly. Re-selecting the same taxon is a
  // no-op (the `loadVernaculars` callback short-circuits on
  // `loaded` / `empty` / `error` cached entries). Closing the
  // panel (selected → null) does NOT clear the cache — the
  // cached result survives across deselects AND across source
  // switches (the `/api/taxon/{id}/vernaculars` endpoint is
  // source-agnostic, so the previously cached payload stays
  // valid under the new active source).
  useEffect(() => {
    if (selected === null) return;
    void loadVernaculars(selected);
  }, [selected, loadVernaculars]);

  // ODD-TDSYN-001 — eager-fetch-on-selection contract for the
  // Synonyms tab. Mirrors the Vernaculars eager-fetch effect
  // byte-for-byte: whenever `selected` becomes a non-null taxon
  // id, fire the canonical `fetchSynonyms(id, { limit: 200 })`
  // round trip so the Synonyms tab activation paints the
  // rendered `Synonyms` header + count + the per-row rank chip
  // + italic-or-roman scientific name + optional `.authorship`
  // span instantly. Re-selecting the same taxon is a no-op (the
  // `loadSynonyms` callback short-circuits on `loaded` /
  // `empty` / `error` cached entries). Closing the panel
  // (selected → null) does NOT clear the cache — the cached
  // result survives across deselects AND across source
  // switches (the `/api/taxon/{id}/synonyms` endpoint is
  // source-agnostic — the SQL pre-filters by
  // `parent_id = taxon_id AND status != 'accepted'`
  // regardless of the active tree source — so the previously
  // cached payload stays valid under the new active source).
  useEffect(() => {
    if (selected === null) return;
    void loadSynonyms(selected);
  }, [selected, loadSynonyms]);

  // ODD-TDDIST-001 — eager-fetch-on-selection contract for the
  // Distribution tab. Mirrors the Synonyms eager-fetch effect
  // byte-for-byte: whenever `selected` becomes a non-null taxon
  // id, fire the canonical `fetchDistribution(id, { limit: 200 })`
  // round trip so the Distribution tab activation paints the
  // rendered `Distribution` header + count + the per-row
  // establishment-means chip + area text instantly.
  // Re-selecting the same taxon is a no-op (the `loadDistribution`
  // callback short-circuits on `loaded` / `empty` / `error`
  // cached entries). Closing the panel (selected → null) does
  // NOT clear the cache — the cached result survives across
  // deselects AND across source switches (the
  // `/api/taxon/{id}/distribution` endpoint is source-agnostic
  // — the FastAPI SQL filters by `taxon_id = ?` regardless of
  // the active tree source — so the previously cached payload
  // stays valid under the new active source).
  useEffect(() => {
    if (selected === null) return;
    void loadDistribution(selected);
  }, [selected, loadDistribution]);

  // ODD-TDFOLDER-001 — eager-fetch-on-selection contract for
  // the Folder tab. Mirrors the distribution eager-fetch effect
  // byte-for-byte: whenever `selected` becomes a non-null taxon
  // id, fire the canonical `previewMaterialize(id, { source:
  // activeSource })` round trip so the Folder tab activation
  // paints the rendered preview + segment list + count summary
  // instantly. Re-selecting the same taxon is a no-op (the
  // `loadFolderPreview` callback short-circuits on `loaded` /
  // `error` cached entries). Closing the panel (selected → null)
  // does NOT clear the cache — the cached result survives across
  // deselects so re-selecting the same taxon later is also
  // instant. Unlike the source-AGNOSTIC search / vernaculars /
  // synonyms / distribution caches, the preview cache is
  // source-AWARE and is invalidated by `handleSourceChange`
  // (the `folderByTaxonId` map is cleared alongside the other
  // source-bound resets).
  useEffect(() => {
    if (selected === null) return;
    void loadFolderPreview(selected);
  }, [selected, loadFolderPreview, activeSource]);

  /** Source selector metadata. Recomputed only when the raw root
   *  payload changes. */
  const availableSources = useMemo<readonly TreeSource[]>(() => {
    if (!rawRoots) return ["col", "worms"];
    return availableSourcesFor(rawRoots.taxa);
  }, [rawRoots]);

  /** Collapse-all affordance state. */
  const collapseAllEnabled = expandedTierCount(state) > 0;

  /** ODD-NTP-005 — render the native-style breadcrumb above the
   *  tree. The home glyph clears focused + selected; each
   *  intermediate ancestor segment is a clickable button that
   *  expands ancestors + focuses + selects that segment; the
   *  last segment (the focused taxon itself) renders as text so
   *  the breadcrumb doesn't include a "go to myself" affordance.
   *  Mirrors `web/breadcrumb.js::renderBreadcrumb` byte-for-byte
   *  except the legacy `chevron_right` icon is replaced with a
   *  unicode `›` so the breadcrumb renders identically without
   *  a material-symbols webfont. */
  const renderBreadcrumb = (): ReactNode => {
    if (focused === null || breadcrumbSegments.length === 0) {
      return null;
    }
    return (
      <nav
        id="breadcrumb"
        className="breadcrumb breadcrumb-host flex items-center gap-2 px-4 py-2 text-body-sm text-on-surface-variant min-w-0 overflow-x-auto"
        aria-label="Active taxonomy path"
        data-breadcrumb=""
        data-breadcrumb-source={activeSource}
        data-breadcrumb-length={breadcrumbSegments.length}
        data-breadcrumb-max-hops={BREADCRUMB_MAX_HOPS}
      >
        <button
          type="button"
          className="breadcrumb-home hover:text-primary transition-colors flex items-center gap-1"
          data-action="focus-home"
          title="Clear focus (go to tree root)"
          aria-label="Clear focus (go to tree root)"
          onClick={handleFocusHome}
        >
          <span aria-hidden="true" className="text-[16px]">⌂</span>
          <span className="sr-only">Home</span>
        </button>
        {breadcrumbSegments.map((seg, i) => {
          const isLast = i === breadcrumbSegments.length - 1;
          const rankCls = seg.rank === "species" || seg.rank === "subspecies" ||
            seg.rank === "genus" || seg.rank === "subgenus" ||
            seg.rank === "variety" || seg.rank === "subvariety" ||
            seg.rank === "form"
            ? "scientific-name"
            : "scientific-name scientific-name--roman";
          return (
            <Fragment key={seg.id}>
              <span aria-hidden="true" className="text-[14px] text-on-surface-variant">›</span>
              {isLast ? (
                <span
                  className={`breadcrumb-current text-on-surface font-medium ${rankCls}`}
                  aria-current="page"
                  data-breadcrumb-segment={seg.id}
                  data-breadcrumb-rank={seg.rank}
                  data-breadcrumb-last="true"
                >
                  {seg.name}
                </span>
              ) : (
                <button
                  type="button"
                  className={`breadcrumb-segment hover:text-primary transition-colors ${rankCls}`}
                  data-action="focus-segment"
                  data-taxon-id={seg.id}
                  data-breadcrumb-segment={seg.id}
                  data-breadcrumb-rank={seg.rank}
                  onClick={() => void handleFocusSegment(seg.id)}
                >
                  {seg.name}
                </button>
              )}
            </Fragment>
          );
        })}
      </nav>
    );
  };

  const renderSourceSelector = (): ReactNode => {
    const selectorLabel = "Tree data source";
    return (
      <div
        className="tree-source-toggle"
        role="group"
        aria-label={selectorLabel}
        data-tree-source-toggle=""
        data-active-source={activeSource}
        style={{ gridColumn: "1 / -1" }}
      >
        {availableSources.map((src) => {
          const active = src === activeSource;
          const label =
            src === "col" ? "CoL" : src === "worms" ? "WoRMS" : "Freshwater";
          return (
            <button
              key={src}
              type="button"
              className={`tree-source-btn${active ? " active" : ""}`}
              data-tree-source={src}
              aria-pressed={active ? "true" : "false"}
              onClick={() => handleSourceChange(src)}
            >
              {label}
            </button>
          );
        })}
      </div>
    );
  };

  /** ODD-NTP-003 — native collapse-all control. */
  const renderCollapseAllInline = (): ReactNode => (
    <div
      className="tree-collapse-all"
      data-collapse-all=""
    >
      <button
        id="collapse-all"
        type="button"
        className={`collapse-all-btn flex items-center gap-1 text-body-sm px-3 py-1.5 rounded-lg border border-outline-variant bg-surface transition-colors ${
          collapseAllEnabled
            ? "text-on-surface hover:bg-surface-container-low"
            : "opacity-40 cursor-not-allowed"
        }`}
        onClick={handleCollapseAll}
        disabled={!collapseAllEnabled}
        aria-disabled={!collapseAllEnabled}
        title="Collapse all expanded nodes"
        data-action="collapse-all"
      >
        <span aria-hidden="true" className="text-[18px] select-none">⊟</span>
        <span>Collapse all</span>
      </button>
    </div>
  );

  const renderRowStatus = (
    tree: TreeState,
    id: number,
    depth: number,
  ): ReactNode => {
    const status: NodeLoadStatus = loadStatus(tree, id);
    const taxon = tree.nodes.get(id);
    if (!taxon) return null;
    const paddingLeft = 16 + (depth + 1) * 24;
    if (status === "loading") {
      return (
        <p
          role="status"
          className="px-4 py-2 text-sm text-on-surface-variant"
          style={{ paddingLeft: `${paddingLeft}px` }}
          data-row-status="loading"
          data-row-status-for={id}
        >
          Loading children…
        </p>
      );
    }
    if (status === "error") {
      return (
        <div
          role="alert"
          className="flex items-center gap-3 px-4 py-2 text-sm"
          style={{ paddingLeft: `${paddingLeft}px` }}
          data-row-status="error"
          data-row-status-for={id}
        >
          <span className="text-on-surface">Could not load children.</span>
          <button
            type="button"
            className="rounded-md border border-outline-variant bg-surface px-2 py-1 text-xs font-medium text-on-surface hover:bg-surface-container-low"
            onClick={() => handleRetryChild(id)}
          >
            Retry
          </button>
        </div>
      );
    }
    return null;
  };

  /** ODD-NTP-003 — native tier header. */
  const renderTierHeader = (
    parentId: number,
    group: RankGroup,
    depth: number,
  ): ReactNode | null => {
    if (group.count <= 1) return null;
    const indentPx = (depth + 1) * 24;
    return (
      <div
        className="tier-header"
        data-tier-header=""
        data-tier-parent={parentId}
        data-tier-rank={group.rank}
        data-tier-count={group.count}
        style={{ marginLeft: `${indentPx}px` }}
      >
        <h2 className="flex items-center gap-2 font-semibold text-base text-on-surface tracking-wide">
          <span aria-hidden="true" className="text-[20px] text-on-surface-variant">▾</span>
          {rankPluralFor(group.rank)} ({group.count})
        </h2>
        {group.remaining > 0 ? (
          <button
            type="button"
            className="load-all"
            data-action="load-all"
            data-parent-id={parentId}
            data-rank={group.rank}
            data-remaining={group.remaining}
            onClick={() => handleLoadMore(parentId, group.rank)}
            aria-label={`Load ${group.remaining} more ${rankPluralFor(group.rank)}`}
          >
            Load {group.remaining} more
          </button>
        ) : null}
      </div>
    );
  };

  /** ODD-NTP-005 — register a row's DOM node so the
   *  `scrollIntoView` call after `select` can target it. The
   *  ref map is keyed by taxon id; rows clean up their entries
   *  on unmount so the map doesn't leak. */
  const registerRowRef = useCallback(
    (id: number, node: HTMLDivElement | null) => {
      if (node === null) {
        rowRefs.current.delete(id);
      } else {
        rowRefs.current.set(id, node);
      }
    },
    [],
  );

  /** ODD-NTP-003 — recursive native tree renderer. */
  const renderRows = (
    tree: TreeState,
    parentId: number | null,
    depth: number,
  ): ReactNode => {
    const ids =
      parentId === null
        ? tree.rootIds
        : (tree.childIdsByParent.get(parentId) ?? []);
    const items: ReactNode[] = [];
    for (const id of ids) {
      const taxon = tree.nodes.get(id);
      if (!taxon) continue;
      const expanded = isExpanded(tree, id);
      const status: NodeLoadStatus = loadStatus(tree, id);
      items.push(
        <Fragment key={id}>
          <TreeRow
            taxon={taxon}
            depth={depth}
            state={tree}
            onToggle={handleToggle}
            onSelect={handleSelect}
            activeSource={activeSource}
            focused={focused}
            selected={selected}
            kebabOpenId={kebabOpenId}
            onToggleKebab={handleToggleKebab}
            onKebabAction={handleKebabAction}
            registerRowRef={registerRowRef}
            pulseNonce={pulseNonce}
          />
          {expanded && status === "loading" ? renderRowStatus(tree, id, depth) : null}
          {expanded && status === "error" ? renderRowStatus(tree, id, depth) : null}
          {expanded ? renderTiers(tree, id, depth) : null}
        </Fragment>,
      );
    }
    return <>{items}</>;
  };

  /** ODD-NTP-003 — tier-group renderer. */
  const renderTiers = (
    tree: TreeState,
    parentId: number,
    depth: number,
  ): ReactNode => {
    const groups = groupChildrenByRank(tree, parentId, activeSource);
    if (groups.length === 0) return null;
    const items: ReactNode[] = [];
    for (const group of groups) {
      const header = renderTierHeader(parentId, group, depth);
      if (header) items.push(header);
      for (const childId of group.visibleIds) {
        const child = tree.nodes.get(childId);
        if (!child) continue;
        const expanded = isExpanded(tree, childId);
        const status: NodeLoadStatus = loadStatus(tree, childId);
        items.push(
          <Fragment key={childId}>
            <TreeRow
              taxon={child}
              depth={depth + 1}
              state={tree}
              onToggle={handleToggle}
              onSelect={handleSelect}
              activeSource={activeSource}
              focused={focused}
              selected={selected}
              kebabOpenId={kebabOpenId}
              onToggleKebab={handleToggleKebab}
              onKebabAction={handleKebabAction}
              registerRowRef={registerRowRef}
              pulseNonce={pulseNonce}
            />
            {expanded && status === "loading" ? renderRowStatus(tree, childId, depth + 1) : null}
            {expanded && status === "error" ? renderRowStatus(tree, childId, depth + 1) : null}
            {expanded ? renderTiers(tree, childId, depth + 1) : null}
          </Fragment>,
        );
      }
    }
    return <>{items}</>;
  };

  return (
    <section aria-label="Taxonomic tree" className="taxa-tree">
      {(root.status === "idle" || root.status === "loading") && (
        <p
          role="status"
          className="px-2 py-6 text-center text-on-surface-variant"
          style={{ gridColumn: "1 / -1" }}
        >
          Loading domains…
        </p>
      )}
      {root.status === "error" && (
        <div
          role="alert"
          className="flex flex-col items-center gap-3 px-2 py-6"
          style={{ gridColumn: "1 / -1" }}
        >
          <p className="text-on-surface">Could not load taxonomy domains.</p>
          {root.message && (
            <p className="text-sm text-on-surface-variant">{root.message}</p>
          )}
          <button
            type="button"
            className="rounded-md border border-outline-variant bg-surface px-3 py-1.5 text-sm font-medium text-on-surface hover:bg-surface-container-low"
            onClick={() => void loadRoots()}
          >
            Retry
          </button>
        </div>
      )}
      {root.status === "empty" && (
        <p
          role="status"
          className="px-2 py-6 text-center text-on-surface-variant"
          style={{ gridColumn: "1 / -1" }}
        >
          No taxonomy domains returned by the API.
        </p>
      )}
      {(root.status === "loaded" || root.status === "idle") &&
        state.rootIds.length > 0 && (
          <>
            {renderBreadcrumb()}
            <div className="tree-source-toggle-wrapper">
              {renderSourceSelector()}
              {renderCollapseAllInline()}
            </div>
            <div
              className="taxa-tree-with-detail grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px] gap-4 items-start"
              data-tree-with-detail=""
              data-has-selection={selected !== null ? "true" : "false"}
            >
              <div
                className="taxa-tree-rows min-w-0"
                data-tree-rows=""
              >
                {renderRows(state, null, 0)}
              </div>
              {(() => {
                if (selected === null) return null;
                const taxon = state.nodes.get(selected);
                if (!taxon) return null;
                const activeTab = getActiveTabFor(selected);
                const searchStatus: SearchTabStatus =
                  searchesByTaxonId.get(selected) ?? { kind: "idle" };
                const vernacularStatus: VernacularTabStatus =
                  vernacularsByTaxonId.get(selected) ?? { kind: "idle" };
                const synonymStatus: SynonymTabStatus =
                  synonymsByTaxonId.get(selected) ?? { kind: "idle" };
                const distributionStatus: DistributionTabStatus =
                  distributionByTaxonId.get(selected) ?? { kind: "idle" };
                // ODD-TDFOLDER-001 — read the folder preview +
                // side-effect + armed-gate state for the
                // currently selected taxon. The preview cache
                // is source-aware (cleared by handleSourceChange
                // alongside the other source-bound resets); the
                // create / open / copy status maps + the
                // create-armed gate live in their own maps so
                // they survive across deselects alongside the
                // preview cache, and the parent owns the gate so
                // a source switch clears it (the stale
                // confirmation has no meaning under the new
                // source).
                const folderStatus: FolderTabStatus =
                  folderByTaxonId.get(selected) ?? { kind: "idle" };
                const folderCreateStatus: FolderCreateStatus =
                  folderCreateByTaxonId.get(selected) ?? { kind: "idle" };
                const folderOpenStatus: FolderOpenStatus =
                  folderOpenByTaxonId.get(selected) ?? { kind: "idle" };
                const folderCopyStatus: FolderCopyStatus =
                  folderCopyByTaxonId.get(selected) ?? { kind: "idle" };
                const folderCreateArmed: boolean =
                  folderCreateArmedByTaxonId.get(selected) ?? false;
                return (
                  <DetailPanel
                    taxon={taxon}
                    state={state}
                    activeSource={activeSource}
                    activeTab={activeTab}
                    onTabChange={(tab) => handleTabChange(selected, tab)}
                    onFocusSegment={handleFocusSegment}
                    onClose={handleCloseDetail}
                    searchStatus={searchStatus}
                    onRetrySearches={() => void loadSearches(selected)}
                    vernacularStatus={vernacularStatus}
                    onRetryVernaculars={() => void loadVernaculars(selected)}
                    synonymStatus={synonymStatus}
                    onRetrySynonyms={() => void loadSynonyms(selected)}
                    distributionStatus={distributionStatus}
                    onRetryDistribution={() => void loadDistribution(selected)}
                    folderStatus={folderStatus}
                    onRetryFolderPreview={() => void loadFolderPreview(selected)}
                    onArmCreate={handleArmCreate}
                    onDisarmCreate={handleDisarmCreate}
                    onCreateResearchFolders={() =>
                      void handleCreateResearchFolders()
                    }
                    onOpenResearchFolder={() =>
                      void handleOpenResearchFolder()
                    }
                    onCopyResearchPath={() => void handleCopyResearchPath()}
                    folderCreateStatus={folderCreateStatus}
                    folderOpenStatus={folderOpenStatus}
                    folderCopyStatus={folderCopyStatus}
                    folderCreateArmed={folderCreateArmed}
                  />
                );
              })()}
            </div>
          </>
        )}
      {root.status === "loaded" && root.message && (
        <p
          role="alert"
          className="mt-2 rounded-md border border-outline-variant bg-surface px-3 py-2 text-sm text-on-surface-variant"
          style={{ gridColumn: "1 / -1" }}
        >
          {root.message}
        </p>
      )}
    </section>
  );
}

/** ODD-NTP-003 — clear the showAll entries keyed to a collapsing
 *  node so a later re-expand starts from the PAGE_SIZE staircase. */
function collapseNodeTiers(state: TreeState, parentId: number): TreeState {
  const prefix = `${parentId}::`;
  let next: Set<string> = new Set(state.showAll);
  let mutated = next.size !== state.showAll.size;
  if (!mutated) {
    for (const key of state.showAll) {
      if (key.startsWith(prefix)) {
        mutated = true;
        break;
      }
    }
  }
  if (!mutated) return state;
  if (next.size !== state.showAll.size) {
    next = new Set(state.showAll);
  }
  for (const key of state.showAll) {
    if (key.startsWith(prefix)) {
      next.delete(key);
    }
  }
  return { ...state, showAll: next };
}

// Re-export `sourceMatches` so consumers using the React tree can
// compose the same predicate without a deep import.
export { sourceMatches };
