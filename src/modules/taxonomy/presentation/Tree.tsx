"use client";

// Tree — taxonomic tree renderer (PR 5a.2 + 5a.4). Ports the legacy
// `web/tree.js` row layout (one `.tree-row` per node). Selection is
// controlled by the parent (`useTaxonTree`); per-row kebab is the
// real `Kebab` component (5a.4), which exposes the `Search online`
// action and bubbles its `onSearchOnline` callback back to `page.tsx`
// so the DetailPanel can be forced to the Search tab even for
// top-level taxa. Styling rides on PR 3c-b's `@layer components`
// selectors.

import type { ReactElement } from "react";

import { type TaxonTreeNode } from "@taxa/taxonomy";

import { Kebab } from "./Kebab";

export interface TreeProps {
  readonly root: TaxonTreeNode | null;
  readonly selectedId: number | null;
  readonly onSelect: (id: number) => void;
  readonly onSearchOnline?: (taxonId: number) => void;
}

export function Tree({ root, selectedId, onSelect, onSearchOnline }: TreeProps): ReactElement {
  if (root === null) {
    return (
      <div className="taxa-tree" role="tree" aria-busy="true">
        <div className="tree-row" role="treeitem" aria-disabled="true">
          <span className="authorship">loading…</span>
        </div>
      </div>
    );
  }
  return (
    <div className="taxa-tree" role="tree" data-selected={selectedId ?? ""}>
      <TreeNodeView node={root} depth={0}
                    selectedId={selectedId} onSelect={onSelect}
                    onSearchOnline={onSearchOnline} />
    </div>
  );
}

interface TreeNodeViewProps {
  readonly node: TaxonTreeNode;
  readonly depth: number;
  readonly selectedId: number | null;
  readonly onSelect: (id: number) => void;
  readonly onSearchOnline?: (taxonId: number) => void;
}

function TreeNodeView({ node, depth, selectedId, onSelect, onSearchOnline }: TreeNodeViewProps): ReactElement {
  const isSelected = node.id === selectedId;
  return (
    <>
      <div role="treeitem" aria-selected={isSelected}
           aria-level={depth + 1} className="tree-row"
           data-taxon-id={node.id} data-rank={node.rank}
           data-selected={isSelected ? "true" : "false"}
           onClick={() => onSelect(node.id)}>
        <span className="authorship">{node.rank}</span>
        <span className="scientific-name">{node.name}</span>
        <span className="authorship">{"\u00A0"}</span>
        <span className="species-count">
          <Kebab taxonId={node.id} onSearchOnline={onSearchOnline} />
        </span>
      </div>
      {node.children.map((child) => (
        <TreeNodeView key={child.id} node={child} depth={depth + 1}
                      selectedId={selectedId} onSelect={onSelect}
                      onSearchOnline={onSearchOnline} />
      ))}
    </>
  );
}