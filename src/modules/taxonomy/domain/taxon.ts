// Taxonomy domain — canonical `Rank` + `Taxon` types and pure invariants.
// spec.md rule 4: domain stays free of presentation, application, browser,
// HTTP, framework, or infrastructure. design.md §Interfaces/Contracts pins
// the field set + rank union verbatim.

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
 *  (e.g. "subspecies must have a species parent"); those belong to the
 *  application layer. */
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
