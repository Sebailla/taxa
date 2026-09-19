/**
 * TreeRow — single disclosure row in the visible taxonomy tree
 * (ODD-VTREE-002 / ODD-NTP-003 / ODD-NTP-004 / ODD-NTP-005 /
 * ODD-TDDISC-001).
 *
 * Renders one taxon as a real block element (NOT a `display: contents`
 * placeholder) so the depth indent applies to the WHOLE identity +
 * disclosure block, not just the name cell. The legacy
 * `web/tree.js::renderNodeRow` uses `padding-left: ${16 + depth *
 * 24}px` on a flex row container; the React port mirrors that
 * contract byte-for-byte so the indentation staircase stays in
 * lock-step with the native oracle on CoL / WoRMS / Freshwater
 * and across source switches.
 *
 * The disclosure control is a `<button>` with `aria-expanded` for
 * expandable rows; species / subspecies leaves carry a `•` glyph
 * (no chevron), are `disabled`, and stamp `data-action="select"`
 * so the ODD-NTP-005 selection handler dispatches directly on
 * them. Higher ranks stamp `data-action="toggle-expand"` and the
 * lazy child-fetch is owned by `TaxonomyTree` so state transitions
 * stay inside the single client island.
 *
 * ODD-NTP-005 — native selection / focus / breadcrumb:
 *   - The row accepts `onSelect`, `focused`, `selected`, and
 *     `pulseNonce` props from the parent. Selection is
 *     orthogonal to expansion: clicking a leaf dispatches the
 *     `select` action (which the parent maps to `handleSelect`)
 *     WITHOUT toggling expansion; clicking a non-leaf keeps the
 *     existing expansion state intact. The selected row paints
 *     a primary-tinted background + left border (matching the
 *     legacy `web/index.html::.tree-row.selected` cascade); the
 *     focused row paints a subtle surface-container-low tint +
 *     outline border (matching `web/index.html::.tree-row.focused`).
 *     `pulseNonce` triggers a one-shot pulse animation on the
 *     freshly selected row (mirrors the legacy
 *     `web/nav.js::select-from-search` `search-pulse` affordance).
 *   - The row registers its DOM node via `registerRowRef` so the
 *     parent's `scrollIntoView({ block: "nearest" })` call after
 *     `select` lands on the right element even when the same id
 *     was already focused.
 *
 * ODD-NTP-003 — identity block carries:
 *   - disclosure chevron / leaf dot (▾ / ▸ / •)
 *   - rank badge (uppercase, tracked Raleway, native density)
 *   - scientific name (italic for genus + below; roman for higher
 *     ranks — mirrors `web/format.js::scientificNameClass`)
 *   - depth-sensitive size/weight (root row uses the larger
 *     `font-h1` treatment; descendants stay on `font-body-lg`)
 *   - extinction line-through opacity for `is_extinct === true`
 *   - authorship on the title/aria-label (no inline authorship
 *     span — the native tree moves it into the row's hover
 *     affordance)
 *
 * ODD-NTP-004 — native row identity and source affordances:
 *   - `data-realm` attribute (computed from `taxon.path` via
 *     `realmForPath`) so the realm tint in `src/app/globals.css`
 *     can color the scientific-name span per domain / kingdom
 *   - status dot (accepted / synonym / unknown) — colored dot with
 *     a hover title; mirrors `web/format.js::statusDot`
 *   - source info affordance — small info glyph whose tooltip
 *     names the source identity (CoL-only / WoRMS-only /
 *     WoRMS cross-link). Renders only when the legacy
 *     `sourceInfoTooltip` predicate returns a string.
 *   - per-row materialize indicator — green folder glyph when
 *     `research_path_exists === true`. ODD-NTP-004 explicitly
 *     defers the desktop / file endpoints; the indicator is a
 *     visual state only (no click handler).
 *   - species-count badge — formatted via `speciesCountBadge`
 *     (5 / 3k / 2.5M thresholds) with a hover title that carries
 *     the full binomial + count context
 *   - kebab trigger (`more_vert`) + kebab menu — collapses the
 *     per-row "View details" / "Open folder" / "View on WoRMS"
 *     actions into a single menu that opens on click. ODD-NTP-005
 *     enables "View details" (the action maps to `onSelect`,
 *     which the navigation slice genuinely backs); "Open folder"
 *     stays disabled until the Folder tab + desktop file
 *     endpoints ship (detail-panel / desktop file actions still
 *     lack React backing).
 *
 * ODD-TDDISC-001 — discoverable row-level detail action:
 *   - Every row renders a compact Material Symbols `visibility`
 *     icon button (`data-action="open-details"`) that calls
 *     `onSelect(taxon.id)` directly. The button uses the
 *     existing `.tree-search-icon` class whitelisted under
 *     TAXONOMY_OWNED_BY_3C_B in `tests/test_research_styles.py`,
 *     so no new top-level CSS selector is introduced. The
 *     explicit `aria-label` / `title` keep the icon-led
 *     affordance accessible to screen readers and mouse-hover
 *     users alike.
 *   - The kebab menu's selection item is RENAMED from "Search
 *     online" to "View details" (label only — the
 *     `data-action="open-searches"` contract stays so the parent
 *     keeps routing through `handleKebabAction(id,
 *     "open-searches")`). The kebab item icon switches from
 *     `search` to `visibility` so the icon-led affordance is
 *     consistent with the new row-level button. Both routes
 *     converge on the same selection primitive, so source
 *     switches, breadcrumb activation, and per-taxon active-tab
 *     memory all keep working byte-for-byte.
 *
 * spec.md rule 4: depends on the taxonomy domain (`Taxon`,
 * `Rank`) and the sibling tree-state helpers + the row-format
 * helpers. Imports stay inside the presentation layer to avoid
 * the barrel cycle (the barrel re-exports `TaxonomyTree`, which
 * would loop back here).
 */
import type { Rank, Taxon } from "../domain/taxon";
import {
  isExpanded,
  isLeafRank,
} from "./tree-state";
import type { TreeSource, TreeState } from "./tree-state";
import {
  hasMaterializedFolder,
  rankLabel,
  realmForPath,
  scientificNameClass,
  scientificNameDepthClass,
  speciesCountBadge,
  statusDotDescriptor,
  wormsUrlFor,
} from "./row-format";

/** Indent step — matches `web/tree.js::renderNodeRow`'s `depth * 24`
 *  staircase so the React tree's depth block aligns to the native
 *  oracle byte-for-byte. */
export const ROW_INDENT_PX = 24;

/** Base padding-left (matches legacy `16 + indentPx`) so depth=0
 *  rows share the same gutter the native tree uses. */
export const ROW_BASE_PADDING_PX = 16;

/** Ranks that should render the scientific name in italic type
 *  (ICZN convention: genus + below are italic; higher ranks and
 *  unranked clades are roman). Mirrors `web/format.js::ITALIC_RANKS`
 *  + `web/format.js::scientificNameClass`. */
export const ITALIC_RANKS: ReadonlySet<Rank> = new Set<Rank>([
  "genus", "subgenus", "species", "subspecies",
  "variety", "subvariety", "form",
]);

export interface TreeRowProps {
  readonly taxon: Taxon;
  readonly depth: number;
  readonly state: TreeState;
  readonly onToggle: (id: number) => void;
  /** ODD-NTP-005 — selection handler. Called on leaf disclosure
   *  clicks (`data-action="select"`) and on the kebab "Search
   *  online" item. Mirrors the legacy `web/nav.js::selectTaxon`
   *  primitive — the parent owns focused + selected state and
   *  never touches expansion here. */
  readonly onSelect: (id: number) => void;
  /** Active tree source — drives the source-info tooltip branch
   *  (CoL-only vs WoRMS-only vs cross-link). Mirrors the legacy
   *  `web/tree.js::renderNodeRow::sourceTooltipText` source-aware
   *  decision. */
  readonly activeSource: TreeSource;
  /** ODD-NTP-005 — focused taxon id (drives the breadcrumb).
   *  Paints the focused row with a subtle surface-container-low
   *  tint + outline border. Mirrors
   *  `web/tree.js::renderNodeRow::rowClassFor(isFocused=true)`. */
  readonly focused: number | null;
  /** ODD-NTP-005 — selected taxon id (drives the row highlight +
   *  detail-panel + URL hash in the legacy oracle). Paints the
   *  selected row with the primary-tinted background + left
   *  border. Mirrors
   *  `web/tree.js::renderNodeRow::rowClassFor(isSelected=true)`. */
  readonly selected: number | null;
  /** Identifier of the row whose kebab menu is currently open, or
   *  `null` when every kebab is closed. Owned by `TaxonomyTree` so
   *  only one kebab can be open at a time across the whole tree. */
  readonly kebabOpenId: number | null;
  /** Toggle the kebab for `id`. Called by the kebab trigger button
   *  (`<button data-action="toggle-kebab">`). The parent owns the
   *  state so click-outside / Escape dismissal live at the tree
   *  level. */
  readonly onToggleKebab: (id: number) => void;
  /** Kebab item action handler. Called by every enabled kebab menu
   *  item. With ODD-NTP-005 the navigation slice genuinely backs
   *  `open-searches` (which delegates to `onSelect`); `open-folder-tab`
   *  remains deferred until the Folder tab + desktop file endpoints
   *  ship; `view-on-worms` is wired via anchor + target. */
  readonly onKebabAction: (
    id: number,
    action: "open-searches" | "open-folder-tab" | "view-on-worms",
  ) => void;
  /** ODD-NTP-005 — register the row's DOM node so the parent's
   *  `scrollIntoView({ block: "nearest" })` call after `select`
   *  can target it. Called on mount with the ref + on unmount
   *  with `null`. The parent owns the ref map; this callback is
   *  stable across renders via `useCallback`. */
  readonly registerRowRef: (id: number, node: HTMLDivElement | null) => void;
  /** ODD-NTP-005 — monotonic counter that triggers the row's
   *  one-shot pulse animation. The parent bumps the nonce on
   *  every successful `select` so the freshly focused row plays
   *  the legacy `web/nav.js::select-from-search` `search-pulse`
   *  affordance once. */
  readonly pulseNonce: number;
}

export default function TreeRow({
  taxon,
  depth,
  state,
  onToggle,
  onSelect,
  activeSource,
  focused,
  selected,
  kebabOpenId,
  onToggleKebab,
  onKebabAction,
  registerRowRef,
  pulseNonce,
}: TreeRowProps): React.ReactElement {
  const expanded = isExpanded(state, taxon.id);
  const knownLeaf = isLeafRank(taxon.rank);
  const indentPx = depth * ROW_INDENT_PX;
  const paddingLeft = ROW_BASE_PADDING_PX + indentPx;

  // Disclosure glyph — leaves get a small dot so the row doesn't
  // look like it has children to expand; expandable rows show the
  // canonical ▾ (expanded) / ▸ (collapsed) triangle. ASCII glyphs
  // render identical across every locale and theme; the material-
  // symbols webfont hook lives in `src/app/globals.css` (the kebab
  // trigger + status / source glyphs adopt the same convention).
  const disclosure = knownLeaf
    ? "•"
    : expanded
      ? "▾"
      : "▸";

  // ODD-NTP-005 — leaves dispatch `select`; non-leaves dispatch
  // `toggle-expand`. The selection primitive is orthogonal to
  // expansion: picking a leaf never expands (leaves have no
  // children); picking a non-leaf keeps the existing expansion
  // state intact, mirroring the legacy `web/nav.js::selectTaxon`
  // primitive byte-for-byte.
  const action = knownLeaf ? "select" : "toggle-expand";
  const ariaExpanded = knownLeaf ? undefined : expanded;
  const ariaLabel = knownLeaf
    ? `Select ${rankLabel(taxon.rank)} ${taxon.name} (leaf)`
    : `${expanded ? "Collapse" : "Expand"} ${rankLabel(taxon.rank)} ${taxon.name}`;
  const nameTitle = taxon.authorship
    ? `${taxon.name} ${taxon.authorship}`
    : null;

  // ODD-NTP-005 — selection / focus affordances. Selected wins
  // over focused; both win over the default hover tint. The
  // class strings mirror `web/tree.js::rowClassFor` /
  // `rankClassFor` / `nameClassFor` so the React cutover paints
  // the same affordances the legacy native tree does.
  const isSelected = selected === taxon.id;
  const isFocused = !isSelected && focused === taxon.id;
  const isPulsing = (isSelected || isFocused) && pulseNonce > 0;
  const rowCls = rowClassFor(isSelected, isFocused);
  const rankCls = rankClassFor(isSelected, isFocused);
  const nameCls = nameClassFor(isSelected, isFocused, depth);
  const arrowColor =
    isSelected || isFocused ? "text-primary" : "text-on-surface-variant";
  const extinctCls = taxon.is_extinct ? "line-through opacity-70" : "";

  // ODD-NTP-004 — per-row affordances. The legacy web/tree.js helper
  // computes each branch from the taxon + active source; the React
  // port mirrors the exact predicate so the affordance surface stays
  // in lock-step with the native oracle.
  const realm = realmForPath(taxon.path);
  const statusDot = statusDotDescriptor(taxon.status);
  const sourceTooltip = (() => {
    if (activeSource === "col" && taxon.coldp_id && !taxon.worms_id) {
      return `CoL-only — ColDP ID ${taxon.coldp_id} (no WoRMS match).`;
    }
    if (taxon.worms_id && activeSource !== "col") {
      const isWormsOnly = !taxon.coldp_id;
      return isWormsOnly
        ? `WoRMS-only — AphiaID ${taxon.worms_id} (no CoL match). Open in WoRMS.`
        : `WoRMS cross-link — AphiaID ${taxon.worms_id}. Open in WoRMS.`;
    }
    return null;
  })();
  const wormsUrl = wormsUrlFor(taxon);
  const speciesCountText = speciesCountBadge(taxon.species_count);
  const isMaterialized = hasMaterializedFolder(taxon);
  const kebabOpen = kebabOpenId === taxon.id;
  const taxonIdStr = String(taxon.id);

  return (
    <div
      ref={(node) => registerRowRef(taxon.id, node)}
      className={`tree-row group flex items-center w-full px-4 py-row-padding-y relative ${rowCls}`}
      data-taxon-id={taxon.id}
      data-action={action}
      data-rank={taxon.rank}
      data-depth={depth}
      data-expanded={knownLeaf ? undefined : String(expanded)}
      data-leaf={knownLeaf ? "true" : undefined}
      data-realm={realm}
      data-materialized={isMaterialized ? "true" : undefined}
      data-status={taxon.status ?? "unknown"}
      data-selected={isSelected ? "true" : undefined}
      data-focused={isFocused ? "true" : undefined}
      data-pulse-nonce={isPulsing ? pulseNonce : undefined}
      style={{ paddingLeft: `${paddingLeft}px` }}
    >
      <div className={`flex items-center justify-center w-6 h-6 mr-2 ${arrowColor}`}>
        <span aria-hidden="true" className="text-[18px] select-none">
          {disclosure}
        </span>
      </div>
      <button
        type="button"
        className="flex items-center gap-3 flex-1 min-w-0 text-left bg-transparent border-0 p-0 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
        aria-expanded={ariaExpanded}
        aria-label={ariaLabel}
        aria-pressed={isSelected ? "true" : undefined}
        data-taxon-disclosure={knownLeaf ? "leaf" : "expandable"}
        onClick={knownLeaf ? () => onSelect(taxon.id) : () => onToggle(taxon.id)}
        disabled={knownLeaf}
      >
        <span className={`rank-badge uppercase tracking-[0.1em] px-2 py-0.5 rounded ${rankCls}`}>
          {rankLabel(taxon.rank)}
        </span>
        <span
          className={`${nameCls} truncate ${extinctCls} ${scientificNameClass(taxon.rank)}`}
          title={nameTitle ?? undefined}
          aria-label={nameTitle ?? undefined}
        >
          {taxon.name}
        </span>
      </button>
      <div className="meta-block flex items-center gap-2 shrink-0 ml-2">
        {/* Per-row materialize indicator — pure visual state
            (ODD-NTP-004 defers the desktop / file endpoints).
            Renders as a green folder glyph with an accessible
            title so screen readers announce "Folder already on
            disk" without an action button. The visual class lives
            in `src/app/globals.css` and matches the legacy
            `web/index.html::.materialize-indicator` cascade. */}
        {isMaterialized ? (
          <span
            className="materialize-indicator material-symbols-outlined text-[16px]"
            role="img"
            aria-label={`Folder already on disk for ${taxon.name}`}
            title={`Folder already on disk for ${taxon.name}`}
            data-materialize-indicator=""
          >
            folder
          </span>
        ) : null}
        {/* Source info affordance — small info glyph whose tooltip
            describes the taxon's source identity. Renders ONLY
            when the source-info predicate returns a string
            (CoL-only / WoRMS-only / cross-link). The visual class
            lives in `src/app/globals.css`. */}
        {sourceTooltip ? (
          <span
            className="source-info material-symbols-outlined text-[14px] text-on-surface-variant"
            role="img"
            aria-label={sourceTooltip}
            title={sourceTooltip}
            data-source-info={activeSource}
          >
            info
          </span>
        ) : null}
        {/* Status dot — accepted (green) / synonym (amber) /
            unknown (outline). The hover title matches the legacy
            `web/format.js::statusDot` tooltip text. */}
        <span
          className={`status-dot ${statusDot.className.replace(/^status-dot\s*/, "")}`}
          role="img"
          aria-label={statusDot.title}
          title={statusDot.title}
          data-status-dot={taxon.status ?? "unknown"}
        />
        {/* Species-count badge — formatted via `speciesCountBadge`
            (5 / 3k / 2.5M thresholds). The hover title carries the
            full binomial + count context so users who want more
            detail can get it without opening the detail panel. */}
        {speciesCountText ? (
          <span
            className="species-count-badge font-mono-data"
            title={`${speciesCountText.replace(/ spp\.$/, "")} species under ${taxon.name}`}
            data-species-count={taxon.species_count ?? 0}
          >
            {speciesCountText}
          </span>
        ) : null}
        {/* ODD-TDDISC-001 — discoverable row-level detail action.
            The Material Symbols `visibility` glyph selects the taxon
            without toggling expansion (mirrors the legacy
            `web/nav.js::selectTaxon` primitive). The button reuses
            the `.tree-search-icon` class whitelisted under
            TAXONOMY_OWNED_BY_3C_B so the chain-topology guard stays
            green without a new top-level CSS rule. The explicit
            `aria-label` / `title` keep the icon-led affordance
            accessible to screen readers and mouse-hover users alike. */}
        <button
          type="button"
          className="tree-search-icon material-symbols-outlined text-[16px] text-on-surface-variant"
          data-action="open-details"
          data-taxon-id={taxonIdStr}
          aria-label={`View details for ${taxon.name}`}
          title="View details"
          onClick={(ev) => {
            ev.stopPropagation();
            onSelect(taxon.id);
          }}
        >
          visibility
        </button>
        {/* Kebab — single trigger per row that opens a menu with
            the per-row actions. Items whose backing React
            behavior exists stay enabled; items whose backing
            handler is deferred to ODD-NTP-005 render with
            `disabled` + `aria-disabled="true"` so the user sees
            them as clearly unavailable rather than silently wired
            to the wrong endpoint. The visual class lives in
            `src/app/globals.css` (`.kebab` + `.kebab-trigger` +
            `.kebab-menu` + `.kebab-item`). */}
        <div
          className="kebab"
          data-kebab-for={taxonIdStr}
          data-kebab-open={kebabOpen ? "true" : undefined}
        >
          <button
            type="button"
            className="kebab-trigger material-symbols-outlined text-[16px] text-on-surface-variant hover:text-primary transition-colors"
            data-action="toggle-kebab"
            data-taxon-id={taxonIdStr}
            aria-label={`More actions for ${taxon.name}`}
            aria-haspopup="menu"
            aria-expanded={kebabOpen ? "true" : "false"}
            title="More actions"
            onClick={(ev) => {
              ev.stopPropagation();
              onToggleKebab(taxon.id);
            }}
          >
            more_vert
          </button>
          <div
            className={`kebab-menu${kebabOpen ? " open" : ""}`}
            role="menu"
            data-kebab-menu-for={taxonIdStr}
          >
            {/* "View details" — RENAMED in ODD-TDDISC-001 from the
                legacy "Search online" label so the kebab action is
                discoverable as the detail-panel entry point. The
                data-action="open-searches" contract stays so the
                parent keeps routing through `handleKebabAction(id,
                "open-searches")` byte-for-byte (mirrors the legacy
                `web/nav.js::open-searches` handler). The kebab
                item icon switches from `search` to `visibility` so
                the icon-led affordance matches the new row-level
                button. Both routes converge on the same selection
                primitive. */}
            <button
              type="button"
              className="kebab-item"
              data-action="open-searches"
              data-taxon-id={taxonIdStr}
              role="menuitem"
              onClick={(ev) => {
                ev.stopPropagation();
                onKebabAction(taxon.id, "open-searches");
              }}
            >
              <span
                aria-hidden="true"
                className="material-symbols-outlined text-[16px] text-on-surface-variant"
              >
                visibility
              </span>
              <span className="kebab-item-label">View details</span>
            </button>
            {/* "Open folder" — DEFERRED. Renders ONLY when
                `hasMaterializedFolder(taxon)` is true (the legacy
                oracle showed the action only when the
                root→taxon folder was on disk) and stays
                `disabled` until the Folder tab + desktop file
                endpoints ship (detail-panel / desktop file
                actions still lack React backing). */}
            {isMaterialized ? (
              <button
                type="button"
                className="kebab-item"
                data-action="open-folder-tab"
                data-taxon-id={taxonIdStr}
                role="menuitem"
                disabled
                aria-disabled="true"
                title="Open folder (deferred — Folder tab + desktop file endpoints lack React backing)"
                onClick={(ev) => {
                  ev.stopPropagation();
                  onKebabAction(taxon.id, "open-folder-tab");
                }}
              >
                <span
                  aria-hidden="true"
                  className="material-symbols-outlined text-[16px] text-on-surface-variant"
                >
                  folder_open
                </span>
                <span className="kebab-item-label">Open folder</span>
              </button>
            ) : null}
            {/* "View on WoRMS" — ENABLED when `wormsUrlFor(taxon)`
                returns a URL. Renders as an `<a target="_blank">`
                that opens the canonical marinespecies.org URL.
                No React handler needed (anchor + target does the
                navigation), so this is the only kebab item with
                backing behavior in ODD-NTP-004. */}
            {wormsUrl ? (
              <a
                className="kebab-item"
                href={wormsUrl}
                target="_blank"
                rel="noopener noreferrer"
                role="menuitem"
                data-action="view-on-worms"
                data-taxon-id={taxonIdStr}
                onClick={() => onKebabAction(taxon.id, "view-on-worms")}
              >
                <span
                  aria-hidden="true"
                  className="material-symbols-outlined text-[16px] text-on-surface-variant"
                >
                  open_in_new
                </span>
                <span className="kebab-item-label">View on WoRMS</span>
              </a>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

// ODD-NTP-005 — row class helpers. Mirror `web/tree.js::rowClassFor`
// / `rankClassFor` / `nameClassFor` byte-for-byte so the React
// cutover paints the same selected / focused / default row
// affordances the legacy oracle does. Selected wins over focused
// wins over the default hover tint; the row's `rounded-r-lg`
// keeps the right corners soft but leaves the left edge (where
// the marker border lives) perfectly square — the border has
// nowhere to curve into.
//
// `selected` and `focused` are stable class names (NOT Tailwind
// utilities) so the realm-tint CSS in `src/app/globals.css` can
// override the `.scientific-name` color when a row is selected
// or focused — the realm hue would otherwise fight the
// primary-color treatment that the Tailwind `text-primary` class
// already applies.
function rowClassFor(isSelected: boolean, isFocused: boolean): string {
  if (isSelected) {
    return "selected bg-primary/5 border-l-[3px] border-primary rounded-r-lg cursor-pointer";
  }
  if (isFocused) {
    return "focused bg-surface-container-low border-l-[3px] border-outline rounded-r-lg cursor-pointer";
  }
  return "hover:bg-surface-container-low transition-colors rounded-r-lg cursor-pointer";
}

function rankClassFor(isSelected: boolean, isFocused: boolean): string {
  if (isSelected) return "text-primary bg-primary/10";
  if (isFocused) return "text-primary bg-primary/5";
  return "text-on-surface-variant bg-surface-container-highest";
}

function nameClassFor(
  isSelected: boolean,
  isFocused: boolean,
  depth: number,
): string {
  // Selected / focused branches compose the legacy Tailwind
  // treatment (`font-h1 text-h1 text-primary font-bold` /
  // `font-h1 text-h1 text-primary`) so the primary-color tint
  // overrides the realm-tint cascade without a separate CSS
  // rule. Depth branches delegate to the row-format
  // `scientificNameDepthClass` helper so the CSS rules in
  // `src/app/globals.css` (`.scientific-name-depth-0` /
  // `.scientific-name-depth-n`) carry the typography. The two
  // systems compose: the Tailwind `text-on-surface` defaults on
  // descendants land on top of the realm-tint cascade so the
  // species / family name stays legible at every depth.
  if (isSelected) return "font-h1 text-h1 text-primary font-bold";
  if (isFocused) return "font-h1 text-h1 text-primary";
  return `${scientificNameDepthClass(depth)} text-on-surface`;
}
