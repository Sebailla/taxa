/**
 * TreeRow — single disclosure row in the visible taxonomy tree
 * (ODD-VTREE-002).
 *
 * Renders one taxon across the four columns of the `.taxa-tree`
 * grid (disclosure / rank / name / count slot). The disclosure button
 * toggles expansion; lazy child-fetch is owned by `TaxonomyTree` so
 * state changes stay inside the single client island.
 *
 * The disclosure button deliberately omits `aria-controls`. Children
 * are flattened as siblings of this row by `TaxonomyTree.renderRows`
 * so there is no single hidden DOM target to point at; the canonical
 * WAI-ARIA tree pattern keeps `aria-expanded` on the disclosure
 * button and lets assistive tech infer the disclosure relationship
 * from the rendered DOM order. Per-row loading/error affordances are
 * rendered as siblings by `TaxonomyTree` so the row stays focused
 * on its own disclosure contract.
 *
 * spec.md rule 4: depends on the taxonomy domain (`Taxon`) and the
 * sibling tree-state helpers. Imports stay inside the presentation
 * layer to avoid the barrel cycle (the barrel re-exports
 * `TaxonomyTree`, which would loop back here).
 */
import type { Taxon } from "../domain/taxon";
import {
  isExpanded,
} from "./tree-state";
import type { TreeState } from "./tree-state";

export interface TreeRowProps {
  readonly taxon: Taxon;
  readonly depth: number;
  readonly state: TreeState;
  readonly onToggle: (id: number) => void;
}

function rankLabel(rank: string): string {
  return rank.charAt(0).toUpperCase() + rank.slice(1);
}

function isLeafByRank(rank: Taxon["rank"]): boolean {
  return rank === "species" || rank === "subspecies";
}

export default function TreeRow({
  taxon,
  depth,
  state,
  onToggle,
}: TreeRowProps): React.ReactElement {
  const expanded = isExpanded(state, taxon.id);
  const knownLeaf = isLeafByRank(taxon.rank);
  const indent = `${depth * 1.25}rem`;
  const disclosure = knownLeaf
    ? "•"
    : expanded
      ? "▾"
      : "▸";

  return (
    <div className="tree-row" data-taxon-id={taxon.id}>
      <button
        type="button"
        className="flex items-center gap-2 border-b border-outline-variant px-2 py-2 text-left text-sm font-medium text-on-surface-variant hover:bg-surface-container-low focus:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-default disabled:hover:bg-transparent"
        aria-expanded={knownLeaf ? undefined : expanded}
        aria-label={
          knownLeaf
            ? `${rankLabel(taxon.rank)} ${taxon.name} (leaf)`
            : `${expanded ? "Collapse" : "Expand"} ${rankLabel(taxon.rank)} ${taxon.name}`
        }
        onClick={knownLeaf ? undefined : () => onToggle(taxon.id)}
        disabled={knownLeaf}
        style={{ gridColumn: "1 / 2" }}
      >
        <span aria-hidden="true" className="inline-block w-4 text-center">
          {disclosure}
        </span>
        <span className="text-xs uppercase tracking-[0.1em]">
          {rankLabel(taxon.rank)}
        </span>
      </button>
      <div
        className="border-b border-outline-variant px-2 py-2"
        style={{ gridColumn: "2 / 3", paddingLeft: indent }}
      >
        <span className="scientific-name">{taxon.name}</span>
        {taxon.authorship && (
          <span className="ml-2 text-xs text-on-surface-variant">
            {taxon.authorship}
          </span>
        )}
      </div>
      <div
        className="border-b border-outline-variant px-2 py-2 text-right text-xs text-on-surface-variant"
        style={{ gridColumn: "3 / 4" }}
      >
        {/* Source affordance slot — WoRMS / CoL pills land in a later PR. */}
      </div>
      <div
        className="border-b border-outline-variant px-2 py-2 text-right"
        style={{ gridColumn: "4 / 5" }}
      >
        <span className="species-count">—</span>
      </div>
    </div>
  );
}