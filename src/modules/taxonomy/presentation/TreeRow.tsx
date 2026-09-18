/**
 * TreeRow — single disclosure row in the visible taxonomy tree
 * (ODD-VTREE-002 / ODD-NTP-003).
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
 *   - extinction line-through opacity for `is_extinct === true`
 *   - authorship on the title/aria-label (no inline authorship
 *     span — the native tree moves it into the row's hover
 *     affordance; ODD-NTP-004 introduces the kebab slot that hosts
 *     it later)
 *
 * spec.md rule 4: depends on the taxonomy domain (`Taxon`,
 * `Rank`) and the sibling tree-state helpers. Imports stay inside
 * the presentation layer to avoid the barrel cycle (the barrel
 * re-exports `TaxonomyTree`, which would loop back here).
 */
import type { Rank, Taxon } from "../domain/taxon";
import {
  isExpanded,
  isLeafRank,
} from "./tree-state";
import type { TreeState } from "./tree-state";

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
const ITALIC_RANKS: ReadonlySet<Rank> = new Set<Rank>([
  "genus", "subgenus", "species", "subspecies",
  "variety", "subvariety", "form",
]);

function rankLabel(rank: Rank): string {
  return rank.charAt(0).toUpperCase() + rank.slice(1);
}

function scientificNameClassFor(rank: Rank): string {
  return ITALIC_RANKS.has(rank)
    ? "scientific-name"
    : "scientific-name scientific-name--roman";
}

export interface TreeRowProps {
  readonly taxon: Taxon;
  readonly depth: number;
  readonly state: TreeState;
  readonly onToggle: (id: number) => void;
}

export default function TreeRow({
  taxon,
  depth,
  state,
  onToggle,
}: TreeRowProps): React.ReactElement {
  const expanded = isExpanded(state, taxon.id);
  const knownLeaf = isLeafRank(taxon.rank);
  const indentPx = depth * ROW_INDENT_PX;
  const paddingLeft = ROW_BASE_PADDING_PX + indentPx;

  // Disclosure glyph — leaves get a small dot so the row doesn't
  // look like it has children to expand; expandable rows show the
  // canonical ▾ (expanded) / ▸ (collapsed) triangle. Glyphs are
  // chosen over the material-symbols webfont so the static export
  // doesn't have to ship the icon font slice — the native tree
  // used `material-symbols-outlined` for the same icons, but the
  // legacy cascade already hoists the icon font on every page; the
  // React cutover can adopt the same convention in ODD-NTP-004
  // when the kebab slot lands. For now the ASCII glyphs render
  // identical across every locale and theme.
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

  // Real block layout (replaces the previous `display: contents`
  // grid trick). Every cell inside the row inherits the depth
  // indent via `padding-left`; the chevron container reserves a
  // fixed 24px slot so disclosure glyphs line up across depths.
  return (
    <div
      className="tree-row flex items-center w-full px-4 py-row-padding-y relative hover:bg-surface-container-low transition-colors"
      data-taxon-id={taxon.id}
      data-action={action}
      data-rank={taxon.rank}
      data-depth={depth}
      data-expanded={knownLeaf ? undefined : String(expanded)}
      data-leaf={knownLeaf ? "true" : undefined}
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
          className={`${scientificNameClassFor(taxon.rank)} truncate ${
            taxon.is_extinct ? "line-through opacity-70" : ""
          }`}
          title={nameTitle ?? undefined}
          aria-label={nameTitle ?? undefined}
        >
          {taxon.name}
        </span>
      </button>
    </div>
  );
}

/** Re-export so other presentation-layer helpers (notably the
 *  tier-header slot) can render the italic/roman modifier without
 *  importing the internal `ITALIC_RANKS` set directly. */
export { ITALIC_RANKS };