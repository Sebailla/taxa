"use client";

// Tree — taxonomic tree renderer (PR 5a.2). Ports the legacy
// `web/tree.js` row layout (one `.tree-row` per node). Selection is
// controlled by the parent (`useTaxonTree`); per-row kebab is
// `KebabStub` (real menu body lands in 5a.4). Styling rides on PR
// 3c-b's `@layer components` selectors.

import type { ReactElement } from "react";

import { type TaxonTreeNode } from "@taxa/taxonomy";

import { KebabStub } from "./KebabStub";

export interface TreeProps {
  readonly root: TaxonTreeNode | null;
  readonly selectedId: number | null;
  readonly onSelect: (id: number) => void;
}

export function Tree({ root, selectedId, onSelect }: TreeProps): ReactElement {
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
                    selectedId={selectedId} onSelect={onSelect} />
    </div>
  );
}

interface TreeNodeViewProps {
  readonly node: TaxonTreeNode;
  readonly depth: number;
  readonly selectedId: number | null;
  readonly onSelect: (id: number) => void;
}

function TreeNodeView({ node, depth, selectedId, onSelect }: TreeNodeViewProps): ReactElement {
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
          <KebabStub taxonId={node.id} />
        </span>
      </div>
      {node.children.map((child) => (
        <TreeNodeView key={child.id} node={child} depth={depth + 1}
                      selectedId={selectedId} onSelect={onSelect} />
      ))}
    </>
  );
}