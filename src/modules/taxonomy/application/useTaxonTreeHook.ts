"use client";

// React adapter for the taxonomy application layer (PR 5a.2).
// Owns the network boundary for the presentation layer; components
// never reach into `fetch*` directly. Loads the bootstrap `domains`
// payload on mount and projects through the framework-free view-
// model functions in `useTaxonTree.ts`. Real Kebab / Search-online
// wiring lands in 5a.4.

import { useEffect, useState } from "react";

import { type Rank, type TaxonRecord } from "../domain/taxon";
import {
  type BreadcrumbViewModel, type TaxonTreeNode,
  buildBreadcrumb, loadTaxonTree,
} from "./useTaxonTree";
import { type FetchLike, NetworkError, fetchDomains }
  from "../infrastructure/api";

/** Surface the `useTaxonTree` hook exposes to presentation components. */
export interface TaxonTreeHookState {
  readonly records: readonly TaxonRecord[];
  readonly tree: TaxonTreeNode | null;
  readonly breadcrumb: BreadcrumbViewModel | null;
  readonly selectedId: number | null;
  readonly setSelectedId: (id: number | null) => void;
  readonly loading: boolean;
  readonly error: NetworkError | null;
}

/** Options accepted by `useTaxonTree`. */
export interface UseTaxonTreeOptions {
  readonly baseUrl: string;
  readonly source: "col" | "worms" | "freshwater";
  readonly fetchFn?: FetchLike;
}

export function useTaxonTree(
  options: UseTaxonTreeOptions,
): TaxonTreeHookState {
  const { baseUrl, source, fetchFn } = options;
  const [records, setRecords] = useState<readonly TaxonRecord[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<NetworkError | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError(null);
    void (async () => {
      try {
        const domains = await fetchDomains(baseUrl, fetchFn);
        if (cancelled) return;
        setRecords(domains.map((d) => stubRecord(d.id, d.name)));
        setLoading(false);
      } catch (cause) {
        if (cancelled) return;
        setError(cause instanceof NetworkError
          ? cause
          : new NetworkError("useTaxonTree: bootstrap fetch failed",
                             null, cause));
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [baseUrl, source, fetchFn]);

  const rootId = selectedId ?? records[0]?.id ?? null;
  const tree = rootId !== null ? loadTaxonTree(records, rootId, source) : null;
  const breadcrumb = selectedId !== null
    ? buildBreadcrumb(records, selectedId, source) : null;

  return { records, tree, breadcrumb, selectedId, setSelectedId, loading, error };
}

function stubRecord(id: number, name: string): TaxonRecord {
  return {
    id, scientific_name: name, rank: "kingdom" as Rank,
    parent_id: null, worms_parent_id: null, freshwater_parent_id: null,
    status: "accepted", is_extinct: false, species_count: 0,
    path: null, coldp_id: null, worms_id: null, freshwater_id: null,
    vernaculars: [], research_path_exists: null,
  };
}