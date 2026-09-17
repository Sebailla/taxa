// Taxonomy domain — canonical `Rank` + `Taxon` types and pure invariants.
// spec.md rule 4: domain stays free of presentation, application, browser,
// HTTP, framework, or infrastructure. design.md §Interfaces/Contracts pins
// the field set verbatim; the rank union grew (ODD-VTREE-001) to match
// every rank that `/api/domains`, `/api/taxon/{id}`, and
// `/api/taxon/{id}/children` can return — the FastAPI server's SQL
// `RANK_ORDER` (api/server.py) plus the rank strings the committed test
// fixtures insert into `taxon` (see tests/test_api_freshwater.py and
// tests/test_api_materialize.py). Wire ranks outside this union are
// rejected by `isValidTaxon` rather than coerced — the FastAPI endpoints
// return DB rows verbatim, so the union is the source of truth.

export type Rank =
  | "collection"   // synthetic freshwater root (api/server.py CASE -1)
  | "root"         // alternate freshwater-root label used in some fixtures
  | "domain"       // CoL domains (Archaea, Bacteria, Eukaryota, Viruses)
  | "superdomain"  // Biota (WoRMS root, returned by /api/domains)
  | "kingdom"
  | "subkingdom"
  | "phylum"
  | "subphylum"
  | "class"
  | "subclass"
  | "order"
  | "suborder"
  | "family"
  | "subfamily"
  | "genus"
  | "subgenus"
  | "species"
  | "subspecies"
  | "variety"
  | "subvariety"
  | "form";

export interface Taxon {
  readonly id: number;
  readonly name: string;
  readonly rank: Rank;
  readonly authorship: string | null;
  readonly parent_id: number | null;
}

/** Twenty-one ranks in taxonomic order — broadest-first, so
 *  `compareRanks(a, b) < 0` exactly when `a` is broader than `b`.
 *  Matches the breadth ordering used by `web/format.js::RANK_ORDER`
 *  (collection → … → form) and the FastAPI SQL `RANK_ORDER` CASE in
 *  `api/server.py` (collection = -1, domain = 0, kingdom = 1, …).
 *  Layout: synthetic / overlay roots first (collection, root, domain,
 *  superdomain), then Linnaean ranks breadth-by-breadth (kingdom,
 *  subkingdom, phylum, subphylum, class, subclass, order, suborder,
 *  family, subfamily, genus, subgenus, species, subspecies), then the
 *  infraspecific tail (variety, subvariety, form). Every rank the
 *  FastAPI `/api/domains`, `/api/taxon/{id}`, and
 *  `/api/taxon/{id}/children` endpoints can return is represented —
 *  the union of `api/server.py` SQL `RANK_ORDER`,
 *  `etl/load_freshwater.py` `KNOWN_RANKS`, and the ranks used in
 *  committed test fixtures (tests/test_api_freshwater.py,
 *  tests/test_api_materialize.py). Indexes do NOT match the
 *  pre-ODD-VTREE-001 legacy eight; consumers that need a stable
 *  positional handle must read it from this array at runtime
 *  (e.g. `TaxonDetailViewModel.rankIndex` already calls
 *  `RANK_ORDER.indexOf(...)`). Exposed so call sites sort by rank
 *  without re-declaring the sequence. */
export const RANK_ORDER: readonly Rank[] = [
  // Synthetic / overlay roots — broadest, sort above every Linnaean rank.
  "collection",
  "root",
  "domain",
  "superdomain",
  // Linnaean ranks — broadest to narrowest.
  "kingdom",
  "subkingdom",
  "phylum",
  "subphylum",
  "class",
  "subclass",
  "order",
  "suborder",
  "family",
  "subfamily",
  "genus",
  "subgenus",
  "species",
  "subspecies",
  // Infraspecific tail — narrowest.
  "variety",
  "subvariety",
  "form",
] as const;

/** Type-narrowing predicate: is `value` one of the ranks in
 *  `RANK_ORDER`? Returns true iff `value` is a string present in the
 *  ordered rank list (currently twenty-one entries; see ODD-VTREE-001). */
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
