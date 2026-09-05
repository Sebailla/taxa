// Taxonomy domain — canonical types, pure invariants, and source-aware
// parent-chain walker. spec.md rule 4 keeps this layer free of browser,
// HTTP, framework, and cross-layer references. design.md pins the field
// set + rank union verbatim; 5a.1 EXTENDS the predecessor with the
// source-aware walker while every prior export stays byte-identical.

export type Rank =
  | "kingdom"
  | "phylum"
  | "class"
  | "order"
  | "family"
  | "genus"
  | "species"
  | "subspecies";

export interface Taxon {
  readonly id: number;
  readonly name: string;
  readonly rank: Rank;
  readonly authorship: string | null;
  readonly parent_id: number | null;
}

/** Eight ranks in taxonomic order — exposed so call sites sort by rank
 *  without re-declaring the sequence. */
export const RANK_ORDER: readonly Rank[] = [
  "kingdom",
  "phylum",
  "class",
  "order",
  "family",
  "genus",
  "species",
  "subspecies",
] as const;

/** Type-narrowing predicate: is `value` one of the eight known ranks? */
export function isValidRank(value: unknown): value is Rank {
  return (
    typeof value === "string" &&
    (RANK_ORDER as readonly string[]).includes(value)
  );
}

/** Type-narrowing predicate: does `taxon` carry every required field
 *  with the correct type + content? Does NOT enforce deeper constraints
 *  (e.g. "subspecies must have a species parent"); those belong above
 *  the domain layer. */
export function isValidTaxon(value: unknown): value is Taxon {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === "number" &&
    Number.isInteger(v.id) &&
    typeof v.name === "string" &&
    v.name.length > 0 &&
    isValidRank(v.rank) &&
    (v.authorship === null || typeof v.authorship === "string") &&
    (v.parent_id === null ||
      (typeof v.parent_id === "number" && Number.isInteger(v.parent_id)))
  );
}

/** Compare two ranks by taxonomic breadth: negative if `a` is broader
 *  than `b`, zero if equal, positive if `a` is narrower. */
export function compareRanks(a: Rank, b: Rank): number {
  return RANK_ORDER.indexOf(a) - RANK_ORDER.indexOf(b);
}

// ---------------------------------------------------------------------------
// 5a.1 — source-aware walker surface.
// ---------------------------------------------------------------------------

/** A taxonomic tree can be walked against any of three sources. Each
 *  source carries its own parent pointer on the same record, so the
 *  walker dispatches on `source` to pick the right pointer. */
export type TreeSource = "col" | "worms" | "freshwater";

/** Type-narrowing predicate for the tree-source literal union. */
export function isValidTreeSource(value: unknown): value is TreeSource {
  return value === "col" || value === "worms" || value === "freshwater";
}

/** Wire shape returned by the typed fetch API. The domain collapses
 *  the legacy backend payload into a single readonly record so every
 *  consumer above sees one canonical type per taxon id. */
export interface TaxonRecord {
  readonly id: number;
  readonly scientific_name: string;
  readonly rank: Rank;
  readonly parent_id: number | null;
  readonly worms_parent_id: number | null;
  readonly freshwater_parent_id: number | null;
  readonly status: string;
  readonly is_extinct: boolean;
  readonly species_count: number;
  readonly path: string | null;
  readonly coldp_id: string | null;
  readonly worms_id: string | null;
  readonly freshwater_id: string | null;
  readonly vernaculars: readonly unknown[];
  readonly research_path_exists: boolean | null;
}

/** One step in a breadcrumb trail. Pure projection of the canonical
 *  record — no rendering concerns, no source state. */
export interface BreadcrumbSegment {
  readonly id: number;
  readonly name: string;
  readonly rank: Rank;
}

/** Selects the parent pointer that corresponds to the chosen source.
 *  Returns `null` for the root taxon in that source and `null` when the
 *  pointer field is unset (e.g. a CoL record with no WoRMS parent). */
export function parentIdOf(
  record: TaxonRecord,
  source: TreeSource,
): number | null {
  switch (source) {
    case "col":         return record.parent_id;
    case "worms":       return record.worms_parent_id;
    case "freshwater":  return record.freshwater_parent_id;
  }
}

/** Walk `startId` up the `source` parent pointers until one of:
 *    - the root (parent pointer is `null`),
 *    - a dangling pointer (parent id absent from `byId`),
 *    - a cycle (a previously visited id),
 *    - the hard cap (`MAX_CHAIN`) on a corrupted graph.
 *  Returns the chain ordered root-first (root ancestor at index 0,
 *  `startId` at the last index). Pure: no I/O, no globals. */
export function walkParentChain(
  startId: number,
  source: TreeSource,
  byId: ReadonlyMap<number, TaxonRecord>,
): TaxonRecord[] {
  const MAX_CHAIN = 100;
  const visited = new Set<number>();
  const order: TaxonRecord[] = [];
  let current: number | null = startId;
  while (current !== null && order.length < MAX_CHAIN) {
    if (visited.has(current)) break;
    const record = byId.get(current);
    if (!record) break;
    visited.add(current);
    order.push(record);
    current = parentIdOf(record, source);
  }
  return order.reverse();
}