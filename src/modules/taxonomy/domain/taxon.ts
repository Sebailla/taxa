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
//
// ODD-VTREE-002 (live-API correction): the live `/api/domains` payload
// exposes a `Viruses` row whose DB rank is `unranked` (CoL surfaces
// unranked clades at the root when no kingdom has been asserted), and
// its child payload carries viral `realm` rows (Adnaviria, Duplodnaviria,
// Riboviria, …) — both ranks are real wire data the previous union
// rejected, so the canonical projection threw on every live root load.
// `realm` slots into the broadest-first ordering between `superdomain`
// and `kingdom`; `unranked` sits AFTER the named ranked sequence
// because it carries NO asserted taxonomic breadth (an `unranked` clade
// can be a sibling of a kingdom, a genus, or anything in between).

export type Rank =
  | "collection"   // synthetic freshwater root (api/server.py CASE -1)
  | "root"         // alternate freshwater-root label used in some fixtures
  | "domain"       // CoL domains (Archaea, Bacteria, Eukaryota, Viruses)
  | "superdomain"  // Biota (WoRMS root, returned by /api/domains)
  | "realm"        // ICNV viral realms (Adnaviria, Riboviria, …) — broader than kingdom, narrower than superdomain
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
  | "form"
  | "unranked";    // CoL unranked clades — NO asserted taxonomic breadth; sorts after every named rank

export interface Taxon {
  readonly id: number;
  readonly name: string;
  readonly rank: Rank;
  readonly authorship: string | null;
  readonly parent_id: number | null;
}

/** Twenty-three ranks in taxonomic order — broadest-first, so
 *  `compareRanks(a, b) < 0` exactly when `a` is broader than `b`.
 *  Matches the breadth ordering used by `web/format.js::RANK_ORDER`
 *  (collection → … → form) and the FastAPI SQL `RANK_ORDER` CASE in
 *  `api/server.py` (collection = -1, domain = 0, kingdom = 1, …).
 *  Layout: synthetic / overlay roots first (collection, root, domain,
 *  superdomain), then `realm` (viral clade broader than kingdom;
 *  ODD-VTREE-002), then Linnaean ranks breadth-by-breadth (kingdom,
 *  subkingdom, phylum, subphylum, class, subclass, order, suborder,
 *  family, subfamily, genus, subgenus, species, subspecies), then the
 *  infraspecific tail (variety, subvariety, form), then `unranked`
 *  LAST because it carries NO asserted taxonomic breadth (it sorts
 *  below every named rank and cannot meaningfully be compared on the
 *  broadest-first axis — `compareRanks` still produces a deterministic
 *  order, but the gap is structural, not taxonomic). Every rank the
 *  FastAPI `/api/domains`, `/api/taxon/{id}`, and
 *  `/api/taxon/{id}/children` endpoints can return is represented —
 *  the union of `api/server.py` SQL `RANK_ORDER`,
 *  `etl/load_freshwater.py` `KNOWN_RANKS`, and the ranks used in
 *  committed test fixtures (tests/test_api_freshwater.py,
 *  tests/test_api_materialize.py, plus the live ODD-VTREE-002 evidence
 *  that `Viruses` rows carry `unranked` and viral realms carry
 *  `realm`). Indexes do NOT match the pre-ODD-VTREE-001 legacy eight;
 *  consumers that need a stable positional handle must read it from
 *  this array at runtime (e.g. `TaxonDetailViewModel.rankIndex`
 *  already calls `RANK_ORDER.indexOf(...)`). Exposed so call sites
 *  sort by rank without re-declaring the sequence. */
export const RANK_ORDER: readonly Rank[] = [
  // Synthetic / overlay roots — broadest, sort above every Linnaean rank.
  "collection",
  "root",
  "domain",
  "superdomain",
  // Viral realms (ODD-VTREE-002) — broader than kingdom, narrower than superdomain.
  "realm",
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
  // Infraspecific tail — narrowest named ranks.
  "variety",
  "subvariety",
  "form",
  // Breadth-less tail (ODD-VTREE-002) — sorts below every named rank;
  // ordering relative to other `unranked` rows falls back to name.
  "unranked",
] as const;

/** Type-narrowing predicate: is `value` one of the ranks in
 *  `RANK_ORDER`? Returns true iff `value` is a string present in the
 *  ordered rank list (currently twenty-three entries; ODD-VTREE-001
 *  added the named ranks, ODD-VTREE-002 added `realm` + `unranked`). */
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
