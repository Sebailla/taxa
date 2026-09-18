/**
 * TreeRow — single disclosure row in the visible taxonomy tree
 * (ODD-VTREE-002 / ODD-NTP-003 / ODD-NTP-004).
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
 * so the future ODD-NTP-005 selection handler can dispatch
 * directly on them. Higher ranks stamp `data-action="toggle-expand"`
 * and the lazy child-fetch is owned by `TaxonomyTree` so state
 * transitions stay inside the single client island.
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
 *     per-row "Search online" / "Open folder" / "View on WoRMS"
 *     actions into a single menu that opens on click. Items
 *     whose backing React behavior exists stay enabled; items
 *     whose backing handler is deferred to ODD-NTP-005 render
 *     with `disabled` + `aria-disabled="true"` so the user sees
 *     them as clearly unavailable rather than silently wired to
 *     the wrong endpoint. Keyboard dismissal (Escape) + click-
 *     outside dismissal are owned by `TaxonomyTree`.
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
  /** Active tree source — drives the source-info tooltip branch
   *  (CoL-only vs WoRMS-only vs cross-link). Mirrors the legacy
   *  `web/tree.js::renderNodeRow::sourceTooltipText` source-aware
   *  decision. */
  readonly activeSource: TreeSource;
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
   *  item. The parent dispatches `open-searches` / `open-folder-tab`
   *  once those land in ODD-NTP-005; for ODD-NTP-004 only
   *  `view-on-worms` is wired (it just navigates to the WoRMS
 *  URL). */
  readonly onKebabAction: (
    id: number,
    action: "open-searches" | "open-folder-tab" | "view-on-worms",
  ) => void;
}

export default function TreeRow({
  taxon,
  depth,
  state,
  onToggle,
  activeSource,
  kebabOpenId,
  onToggleKebab,
  onKebabAction,
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

  const action = knownLeaf ? "select" : "toggle-expand";
  const ariaExpanded = knownLeaf ? undefined : expanded;
  const ariaLabel = knownLeaf
    ? `${rankLabel(taxon.rank)} ${taxon.name} (leaf)`
    : `${expanded ? "Collapse" : "Expand"} ${rankLabel(taxon.rank)} ${taxon.name}`;
  const nameTitle = taxon.authorship
    ? `${taxon.name} ${taxon.authorship}`
    : null;

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
      className="tree-row flex items-center w-full px-4 py-row-padding-y relative hover:bg-surface-container-low transition-colors"
      data-taxon-id={taxon.id}
      data-action={action}
      data-rank={taxon.rank}
      data-depth={depth}
      data-expanded={knownLeaf ? undefined : String(expanded)}
      data-leaf={knownLeaf ? "true" : undefined}
      data-realm={realm}
      data-materialized={isMaterialized ? "true" : undefined}
      data-status={taxon.status ?? "unknown"}
      style={{ paddingLeft: `${paddingLeft}px` }}
    >
      <div className="flex items-center justify-center w-6 h-6 mr-2 text-on-surface-variant">
        <span aria-hidden="true" className="text-[18px] select-none">
          {disclosure}
        </span>
      </div>
      <button
        type="button"
        className="flex items-center gap-3 flex-1 min-w-0 text-left bg-transparent border-0 p-0 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
        aria-expanded={ariaExpanded}
        aria-label={ariaLabel}
        data-taxon-disclosure={knownLeaf ? "leaf" : "expandable"}
        onClick={knownLeaf ? undefined : () => onToggle(taxon.id)}
        disabled={knownLeaf}
      >
        <span className="rank-badge uppercase tracking-[0.1em] px-2 py-0.5 rounded text-on-surface-variant bg-surface-container-highest">
          {rankLabel(taxon.rank)}
        </span>
        <span
          className={`${scientificNameDepthClass(depth)} ${scientificNameClass(taxon.rank)} truncate ${
            taxon.is_extinct ? "line-through opacity-70" : ""
          }`}
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
            {/* "Search online" — DEFERRED to ODD-NTP-005. Renders
                with `disabled` + `aria-disabled="true"` so the
                user sees the action is clearly unavailable
                rather than silently wired to a non-existent
                React handler. */}
            <button
              type="button"
              className="kebab-item"
              data-action="open-searches"
              data-taxon-id={taxonIdStr}
              role="menuitem"
              disabled
              aria-disabled="true"
              title="Search online (deferred to ODD-NTP-005)"
              onClick={(ev) => {
                ev.stopPropagation();
                onKebabAction(taxon.id, "open-searches");
              }}
            >
              <span
                aria-hidden="true"
                className="material-symbols-outlined text-[16px] text-on-surface-variant"
              >
                search
              </span>
              <span className="kebab-item-label">Search online</span>
            </button>
            {/* "Open folder" — DEFERRED to ODD-NTP-005. Renders
                ONLY when `hasMaterializedFolder(taxon)` is true
                (the legacy oracle showed the action only when the
                root→taxon folder was on disk; ODD-NTP-004 mirrors
                that gate so the menu doesn't surface the action
                for taxa whose folder hasn't been materialized
                yet). The item stays `disabled` until ODD-NTP-005
                wires the React handler. */}
            {isMaterialized ? (
              <button
                type="button"
                className="kebab-item"
                data-action="open-folder-tab"
                data-taxon-id={taxonIdStr}
                role="menuitem"
                disabled
                aria-disabled="true"
                title="Open folder (deferred to ODD-NTP-005)"
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