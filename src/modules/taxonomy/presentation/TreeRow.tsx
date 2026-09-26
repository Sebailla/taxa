/**
 * TreeRow — single disclosure row in the visible taxonomy tree
 * (ODD-VTREE-002 / ODD-NTP-003 / ODD-NTP-004 / ODD-NTP-005 /
 * ODD-TAPOPUP-001).
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
 * ODD-PHASE2 — design-system cutover (post-PR #385):
 *   The row density collapsed from 9 visible elements to 5
 *   (disclosure + rank Badge + name + status+count Badge +
 *   kebab IconButton). The materialize indicator +
 *   source-info glyph + row-level `visibility` icon button all
 *   collapsed into the kebab menu / name span title.
 *
 * ODD-TAPOPUP-001 — taxon-action popup replaces the kebab menu:
 *   The pre-popup kebab menu carried two conditional items
 *   ("Open folder" for materialized rows + "View on WoRMS" for
 *   WoRMS rows). Both items are GONE — the popup replaces the
 *   sticky detail rail and the user-selected four tabs
 *   (Synonyms / Distribution / Search / Folder) subsume the
 *   menu shortcuts. Clicking the row-level kebab IconButton
 *   now opens the popup directly via the canonical
 *   `onToggleKebab(id)` callback (which the parent wires to
 *   `handleSelect(id)` so the selection primitive is the
 *   single source of truth for popup-open).
 *
 *   The kebab IconButton advertises the popup target via
 *   `aria-haspopup="dialog"` (was `aria-haspopup="menu"` in
 *   the pre-popup kebab menu) + `aria-expanded={selected ===
 *   taxon.id ? "true" : "false"}` so assistive tech sees the
 *   popup's open state for that row. The kebab-trigger CSS
 *   discoverability hook (passive-hint opacity + hover/focus
 *   reveal) is restored by adding the `kebab-trigger` class
 *   hook to the IconButton's className chain.
 *
 *   The "Open folder" kebab item is gone (the Folder tab in
 *   the popup owns the create/open flow). The "View on WoRMS"
 *   shortcut is gone (the WoRMS badge was an Overview-tab
 *   affordance; the popup drops the Overview tab). The
 *   materialize indicator stays as a `data-materialized`
 *   attribute on the row surface so the Folder tab knows
 *   whether the row is materialized.
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
 *   - rank badge (the `<Badge variant="subtle" uppercase>` primitive
 *     centralizes the previous `rank-badge` inline span + the
 *     var(--surface-container-highest) hue)
 *   - scientific name (italic for genus + below; roman for higher
 *     ranks — mirrors `web/format.js::scientificNameClass`).
 *     The source-info tooltip collapses into the name span's
 *     `title` attribute (the previous `source-info` glyph + the
 *     `data-source-info` attribute are gone).
 *   - depth-sensitive size/weight (root row uses the larger
 *     `font-h1` treatment; descendants stay on `font-body-lg`)
 *   - extinction line-through opacity for `is_extinct === true`
 *   - authorship on the title/aria-label (no inline authorship
 *     span — the native tree moves it into the row's hover
 *     affordance)
 *
 * ODD-NTP-004 — per-row affordances (post-PHASE2 surface):
 *   - `data-realm` attribute (computed from `taxon.path` via
 *     `realmForPath`) so the realm tint in `src/app/globals.css`
 *     can color the scientific-name span per domain / kingdom.
 *   - status indicator (accepted / synonym / unknown) — inline span
 *     inside the new status+count Badge; coloured via Tailwind
 *     utilities (`bg-green-500` / `bg-amber-500` / `bg-on-surface-variant`).
 *     The previous `.status-dot-{accepted,synonym,unknown}` CSS rules
 *     are gone (removed in ODD-TRE-003 globals.css cleanup).
 *   - species count + JetBrains Mono — rendered inside the same
 *     Badge composite. The previous `.species-count-badge` rule is
 *     gone (the new Badge centralizes the treatment).
 *   - kebab trigger via `<IconButton variant="subtle">` with
 *     `kebab-trigger` class hook (the CSS discoverability
 *     cascade is wired via the `kebab-trigger` class). The
 *     kebab menu is GONE in ODD-TAPOPUP-001 — the trigger
 *     opens the popup directly.
 *
 * spec.md rule 4: depends on the taxonomy domain (`Taxon`,
 * `Rank`) and the sibling tree-state helpers + the row-format
 * helpers. Imports stay inside the presentation layer to avoid
 * the barrel cycle (the barrel re-exports `TaxonomyTree`, which
 * would loop back here).
 */
import type { ReactElement } from "react";
import { Badge, IconButton } from "@taxa/design-system";
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
   *  clicks (`data-action="select"`). Mirrors the legacy
   *  `web/nav.js::selectTaxon(id)` primitive — the parent owns
   *  focused + selected state and never touches expansion here. */
  readonly onSelect: (id: number) => void;
  /** Active tree source — the `nameTitle` tooltip already carries
   *  any source-aware context (authorship is included verbatim),
   *  so this prop is preserved for downstream consumers (the
   *  helper hierarchy in `tree-state.ts`). The row-collapse cuts
   *  the dedicated source-info glyph out of the JSX. */
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
  /** ODD-TAPOPUP-001 — kebab trigger callback. Called by the
   *  kebab `<IconButton>` (`data-action="toggle-kebab"`). The
   *  parent wires this to `handleSelect(id)` so the popup opens
   *  via the canonical selection primitive (the popup is
   *  `selected`-driven; the kebab-click is functionally
   *  equivalent to clicking the row's leaf disclosure). */
  readonly onToggleKebab: (id: number) => void;
  /** ODD-NTP-005 — register the row's DOM node so the parent's
   *  `scrollIntoView({ block: "nearest" })` call after `select`
   *  can target it. Called on mount with the ref + on unmount
   *  with `null`. The parent owns the ref map; this callback is
   *  stable across renders via `useCallback`. */
  readonly registerRowRef: (id: number, node: HTMLDivElement | null) => void;
  /** ODD-NTP-005 — monotonic counter that triggers the row's
   *  one-shot pulse animation. The parent bumps the nonce on
   *  every successful `select` so the row renders a brief
   *  pulse affordance (mirrors the legacy
   *  `web/nav.js::select-from-search` `search-pulse`
   *  affordance once). */
  readonly pulseNonce: number;
}

/** Maps the canonical `Taxon.status` enum to the matching inline
 *  Tailwind utility used by the status indicator. Mirrors the
 *  legacy `web/format.js::statusDot` colour map byte-for-byte
 *  (green-500 / amber-500 / on-surface-variant for the unknown
 *  fallback). The colour is now applied inline so the indicator no
 *  longer depends on the `.status-dot-{accepted,synonym,unknown}`
 *  CSS hooks — those rules were retired in the ODD-TRE-003
 *  globals.css cleanup. */
function statusDotColorClass(status: Taxon["status"]): string {
  switch (status) {
    case "accepted":
      return "bg-green-500";
    case "synonym":
      return "bg-amber-500";
    default:
      return "bg-on-surface-variant";
  }
}

export default function TreeRow({
  taxon,
  depth,
  state,
  onToggle,
  onSelect,
  // `activeSource` stays on the `TreeRowProps` interface so the parent
  // TaxonomyTree can keep passing it byte-for-byte; the previous
  // source-info glyph (which read it) is gone and no JSX branch
  // consumes it now. The `_` prefix is the TS-friendly convention for
  // "intentionally unused while still wired to the interface".
  activeSource: _activeSource,
  focused,
  selected,
  onToggleKebab,
  registerRowRef,
  pulseNonce,
}: TreeRowProps): ReactElement {
  const expanded = isExpanded(state, taxon.id);
  const knownLeaf = isLeafRank(taxon.rank);
  const indentPx = depth * ROW_INDENT_PX;
  const paddingLeft = ROW_BASE_PADDING_PX + indentPx;

  // Disclosure glyph — leaves get a small dot so the row doesn't
  // look like it has children to expand; expandable rows show the
  // canonical ▾ (expanded) / ▸ (collapsed) triangle. ASCII glyphs
  // render identical across every locale and theme.
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
  // The name span's `title` collapses the authorship + source
  // identity into the native browser tooltip (the previous
  // dedicated source-info glyph is gone). When `taxon.authorship`
  // is empty the title is omitted so the cell stays compact.
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
  // `rankCls` is preserved for parity with the previous inline rank-
  // badge span + the ODD-DSE follow-up (DetailPanel migration will
  // thread `rankClassFor` through its rank-badge inline spans). The
  // new design-system `<Badge variant="subtle" uppercase>` primitive
  // centralizes the rank-badge treatment so the per-selection color
  // override is no longer applied at this site.
  void rankCls;
  const arrowColor =
    isSelected || isFocused ? "text-primary" : "text-on-surface-variant";
  const extinctCls = taxon.is_extinct ? "line-through opacity-70" : "";

  // ODD-NTP-004 — per-row affordances. The legacy web/tree.js helper
  // computes each branch from the taxon + active source; the React
  // port mirrors the exact predicate so the affordance surface stays
  // in lock-step with the native oracle. After ODD-PHASE2 the
  // materialize indicator + source info glyph + visibility icon
  // button are gone from the row surface (they collapsed into the
  // kebab menu / name span title); what remains is the status +
  // species count composite.
  const realm = realmForPath(taxon.path);
  const statusDot = statusDotDescriptor(taxon.status);
  const statusDotTitle = statusDot.title;
  const statusColorCls = statusDotColorClass(taxon.status);
  const speciesCountText = speciesCountBadge(taxon.species_count);
  // ODD-TAPOPUP-001 — the materialize indicator stays as a
  // `data-materialized` attribute on the row surface so the Folder
  // tab in the popup knows whether the row is already on disk (the
  // pre-popup kebab menu used the predicate for the conditional
  // "Open folder" item; the popup subsumes that affordance via the
  // Folder tab). The helper stays imported + consumed here so the
  // canonical row-affordance surface survives the popup cutover.
  const isMaterialized = hasMaterializedFolder(taxon);
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
        // ODD-RCTX-001 — right-click opens the taxon's URL in a
        // new tab. The URL `?taxon=ID` query param (added by
        // ODD-URLSTATE-001) carries the row's selection so the
        // new tab opens to the exact same selection state. The
        // handler suppresses the browser's context menu so the
        // right-click feels like a deliberate "open in new tab"
        // affordance instead of a native menu the user did not
        // ask for. The id is defensively validated with
        // `Number.isFinite` so a malformed row id never produces
        // an open redirect through `window.open`.
        onContextMenu={(ev) => {
          ev.preventDefault();
          if (!Number.isFinite(taxon.id) || !Number.isInteger(taxon.id) || taxon.id <= 0) {
            return;
          }
          // Build the URL with an explicit `window.location.origin`
          // prefix so the navigation is provably same-origin (the
          // id is the only dynamic component, defensively validated
          // with `Number.isFinite` / `Number.isInteger` / `id > 0`
          // so a malformed id never produces an open redirect).
          const url = `${window.location.origin}/?taxon=${taxon.id}`;
          window.open(url, "_blank", "noopener,noreferrer");
        }}
        disabled={knownLeaf}
      >
        {/* ODD-PHASE2 — rank badge via the design-system <Badge>
            primitive. Replaces the previous `rank-badge uppercase
            tracking-[0.1em] px-2 py-0.5 rounded ${rankCls}` span.
            The `subtle` variant carries the canonical
            `bg-surface text-on-surface-variant border
            border-outline-variant` palette; the `uppercase` flag
            keeps the rank-badge look (tracked Raleway + 11px +
            uppercase + px-2 py-0.5). */}
        <Badge variant="subtle" uppercase={true}>
          {rankLabel(taxon.rank)}
        </Badge>
        {/* ODD-PHASE2 — the `title` attribute is the single hover
            affordance for the authorship (and any source-info
            context previously carried by the dedicated glyph).
            Screen readers announce the same tooltip text. */}
        <span
          className={`${nameCls} truncate ${extinctCls} ${scientificNameClass(taxon.rank)}`}
          title={nameTitle ?? undefined}
          aria-label={nameTitle ?? undefined}
        >
          {taxon.name}
        </span>
      </button>
      <div className="meta-block flex items-center gap-2 shrink-0 ml-2">
        {/* ODD-PHASE2 — status dot + species-count composite Badge.
            Replaces the previous `.status-dot ${statusDot.className}`
            span + the `.species-count-badge font-mono-data` span.
            The Badge primitive centralizes the trailing-meta
            treatment; the indicator is now an inline `<span>` with
            Tailwind colour utilities (no CSS rule dependency). */}
        <Badge
          variant="subtle"
          uppercase={false}
          className="flex items-center gap-2"
        >
          <span
            className={`h-2 w-2 rounded-full ${statusColorCls}`}
            role="img"
            aria-label={statusDotTitle}
            title={statusDotTitle}
          />
          {speciesCountText ? (
            <span
              className="font-mono-data"
              title={`${speciesCountText.replace(/ spp\.$/, "")} species under ${taxon.name}`}
            >
              {speciesCountText}
            </span>
          ) : null}
        </Badge>
        {/* ODD-PHASE2 + ODD-TAPOPUP-001 — kebab trigger via the
            design-system <IconButton> primitive. Replaces the
            previous `.kebab-trigger material-symbols-outlined ...`
            button (the row-level `.tree-search-icon` `visibility`
            button was already removed in this collapse).

            ODD-TAPOPUP-001 — the kebab menu is GONE. The trigger
            opens the taxon-action popup directly via the canonical
            `onToggleKebab(id)` callback (which the parent wires
            to `handleSelect(id)`). The `kebab-trigger` class hook
            is restored so the existing CSS discoverability rule
            (passive-hint opacity + hover/focus reveal) is wired:
            the IconButton's className chain picks up the
            `margin-left / padding / border-radius / opacity /
            transition` declarations from `.kebab .kebab-trigger`.

            The trigger advertises the popup target via
            `aria-haspopup="dialog"` (was `aria-haspopup="menu"`
            in the pre-popup kebab menu). The `aria-expanded`
            attribute reflects the popup's open state for this
            row (`selected === taxon.id`). The `data-action=
            "toggle-kebab"` attribute stays so the selector +
            data-action delegation contract survives the React
            cutover. */}
        <div
          className="kebab"
          data-kebab-for={taxonIdStr}
        >
          <IconButton
            variant="subtle"
            aria-label={`More actions for ${taxon.name}`}
            title="More actions"
            aria-haspopup="dialog"
            aria-expanded={selected === taxon.id ? "true" : "false"}
            data-action="toggle-kebab"
            data-taxon-id={taxonIdStr}
            className="kebab-trigger"
            onClick={(ev) => {
              ev.stopPropagation();
              onToggleKebab(taxon.id);
            }}
          >
            <span aria-hidden="true" className="material-symbols-outlined">
              more_vert
            </span>
          </IconButton>
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
    // ODD-SBP-001-P3 (impeccable 2026-09-24): the colored left border
    // was removed in favor of a stronger bg tint. The Tailwind
    // utility classes (`bg-primary/5`, `border-l-[3px]`, `border-primary`)
    // are gone — the canonical bg + radius now lives in the CSS rule
    // alone (`.tree-row.selected { background: color-mix(... 8% ...);
    // border-radius: 0 0.5rem 0.5rem 0; }`).
    return "selected rounded-r-lg cursor-pointer";
  }
  if (isFocused) {
    // Same: focused row's bg + radius live in the CSS rule; the
    // Tailwind `bg-surface-container-low` is also gone (the CSS
    // owns the bg now, so this class only needs to identify the row).
    return "focused rounded-r-lg cursor-pointer";
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
