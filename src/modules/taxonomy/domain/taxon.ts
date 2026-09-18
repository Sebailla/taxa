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
//
// ODD-NTP-001 (native-tree-parity data layer): the canonical `Taxon`
// now carries every legacy tree field the FastAPI `Taxon` payload can
// surface, so the React projection does not drop identifiers
// (`coldp_id`, `worms_id`, `freshwater_id`), source-specific parent
// relations (`parent_id`, `freshwater_parent_id`), or UI metadata
// (`status`, `is_extinct`, `path`, `species_count`,
// `research_path_exists`). Nullability matches FastAPI exactly: a
// missing or null wire value projects as `null` rather than coerced
// to zero / empty string / another source — the source-aware parent
// chain in `web/nav.js` (legacy parity oracle) relies on
// `parent_id === null` to detect a CoL row that belongs only to the
// WoRMS / freshwater overlay, so coercing `null → 0` would silently
// break the chain. Every optional wire property is validated by
// `isValidTaxon` ONLY WHEN PRESENT — a minimal test-taxonomy
// constructor that omits the new fields still passes, so the existing
// view-model + tree-state harnesses (PR 5b / ODD-VTREE-001) keep
// working without modification.
//
// ODD-NTP-001 (no invented client field): the FastAPI `Taxon`
// Pydantic model (`api/server.py`) exposes `parent_id` and
// `freshwater_parent_id` but does NOT expose `worms_parent_id` —
// the WoRMS overlay column is used internally by the server
// (`api/server.py::get_children` `where = "worms_parent_id = ?"`)
// and the legacy `web/nav.js` reads `t.taxon.worms_parent_id` from
// its client-side cache, but it is not on the public wire shape.
// A canonical `Taxon` carrying an invented `worms_parent_id` would
// (a) be unreachable from any real fetch (always `null`), (b) leak
// a private server column into the client contract, and (c) require
// a future coordinated server + client change to ever populate.
// Source-aware parent ancestry for the WoRMS view must instead be
// built from attached tree edges (walking "who lists me as a child"
// through `worms_id IS NOT NULL` rows already loaded into the
// `tree-state.ts` cache) until/unless the API exposes a
// `worms_parent_id` field in a separately authorized backend change.

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

/** Canonical taxon record. Fields are typed to mirror the FastAPI
 *  `Taxon` Pydantic model in `api/server.py` (the native read-only
 *  authority; ODD-NTP-001 task constraint). Every newly modeled wire
 *  property is nullable so a missing or `null` wire value projects
 *  through `fromWire` (`infrastructure/api.ts`) without coercion —
 *  the source-aware parent chain in `web/nav.js` (legacy parity
 *  oracle) relies on `parent_id === null` to detect a CoL row that
 *  belongs only to the WoRMS / freshwater overlay, so coercing
 *  `null → 0` would silently break the chain.
 *
 *  Source-specific identifiers (`coldp_id`, `worms_id`, `freshwater_id`)
 *  carry every wire column the legacy tree reads for source filtering,
 *  so a future task (ODD-NTP-002) can dispatch the source filter on
 *  `state.treeSource` without round-tripping the API. Only the
 *  `freshwater_parent_id` source-specific parent relation is
 *  exposed by the FastAPI wire; the WoRMS overlay column is used
 *  internally by the server but is not on the public wire shape —
 *  WoRMS source-aware parent ancestry must be derived from attached
 *  tree edges until/unless the API exposes `worms_parent_id` in a
 *  separately authorized backend change (see the file header note).
 *
 *  UI metadata (`status`, `is_extinct`, `path`, `species_count`,
 *  `research_path_exists`) is what every legacy tree row renders
 *  — extinction line-through, species-count badge, materialize
 *  indicator, root→taxon path shortcut. They are typed nullable so
 *  legacy / minimal test fixtures that omit them still satisfy
 *  `isValidTaxon` when those fields are absent. */
export interface Taxon {
  // CoL backbone fields — required id + name + rank + nullable
  // authorship / parent_id. The projection in `fromWire` reads
  // `scientific_name` from the wire and surfaces it as `name`.
  readonly id: number;
  readonly name: string;
  readonly rank: Rank;
  readonly authorship: string | null;
  readonly parent_id: number | null;
  // Source identifiers — every legacy tree source filter reads one
  // of these. `coldp_id` is a string (ColDP uses string keys);
  // `worms_id` / `freshwater_id` are integers (AphiaID, FW row id).
  // `null` means the taxon is not in that source.
  readonly coldp_id: string | null;
  readonly worms_id: number | null;
  readonly freshwater_id: number | null;
  // Source-specific parent relations — only `freshwater_parent_id`
  // is on the FastAPI wire (the Freshwater overlay hierarchy). The
  // WoRMS overlay column (`worms_parent_id`) is used internally by
  // the server but is NOT exposed on the public wire — see the
  // file header note. A WoRMS-only row carries `parent_id === null`
  // and the WoRMS parent is reached by walking back through the
  // children lists already loaded into the cache, not by reading a
  // canonical field.
  readonly freshwater_parent_id: number | null;
  // UI metadata — every legacy tree row paints at least one of
  // these. `status` (accepted/synonym/misapplied/…) drives the
  // detail panel + breadcrumb; `is_extinct` drives the
  // line-through opacity; `path` is the CoL-baked root→taxon path
  // the materialize modal reuses; `species_count` drives the
  // per-row badge; `research_path_exists` drives the per-row
  // materialize indicator on `/api/taxon/{id}/children` payloads.
  readonly status: string | null;
  readonly is_extinct: boolean | null;
  readonly path: string | null;
  readonly species_count: number | null;
  readonly research_path_exists: boolean | null;
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
 *  application layer.
 *
 *  ODD-NTP-001: required fields (`id`, `name`, `rank`, `authorship`,
 *  `parent_id`) are validated unconditionally — they are part of every
 *  legacy + wire payload. Optional wire properties
 *  (`coldp_id`, `worms_id`, `freshwater_id`, `freshwater_parent_id`,
 *  `status`, `is_extinct`, `path`, `species_count`,
 *  `research_path_exists`) are validated ONLY WHEN PRESENT so the
 *  existing minimal test-taxonomy constructor shape
 *  (`{ id, name, rank, authorship, parent_id }`) keeps passing
 *  without modification. A value of `null` on an optional wire
 *  property is accepted (it represents a wire-side "not in this
 *  source" / "not applicable" — coercing to zero or empty string
 *  would break the source-aware parent chain in `web/nav.js`).
 *  `worms_parent_id` is deliberately NOT a canonical field: the
 *  FastAPI wire does not expose it, so inventing it client-side
 *  would leak a private server column. See the file header. */
export function isValidTaxon(value: unknown): value is Taxon {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  // Required fields — always validated (ODD-VTREE-001 contract;
  // unchanged by ODD-NTP-001).
  if (
    !(typeof v.id === "number" && Number.isInteger(v.id) &&
      typeof v.name === "string" && v.name.length > 0 &&
      isValidRank(v.rank) &&
      (v.authorship === null || typeof v.authorship === "string") &&
      (v.parent_id === null ||
        (typeof v.parent_id === "number" && Number.isInteger(v.parent_id))))
  ) {
    return false;
  }
  // Optional wire properties — ODD-NTP-001. Each is validated only
  // when present, and `null` is accepted (FastAPI sends `null` for
  // "this source does not have a value for this field"). The integer
  // fields are checked for `Number.isInteger` so a wire-side `1.5`
  // or `"42"` is rejected, matching the FastAPI Pydantic constraints.
  for (const key of STRING_OPTIONAL_KEYS) {
    if (!hasOwn(v, key)) continue;
    const f = v[key];
    if (f !== null && typeof f !== "string") return false;
  }
  for (const key of INTEGER_OPTIONAL_KEYS) {
    if (!hasOwn(v, key)) continue;
    const f = v[key];
    if (f !== null && (typeof f !== "number" || !Number.isInteger(f))) {
      return false;
    }
  }
  for (const key of BOOLEAN_OPTIONAL_KEYS) {
    if (!hasOwn(v, key)) continue;
    const f = v[key];
    if (f !== null && typeof f !== "boolean") return false;
  }
  return true;
}

/** ODD-NTP-001: optional wire properties, grouped by validation rule.
 *  Kept module-local so `isValidTaxon` stays the single validation
 *  entry point and consumers cannot accidentally bypass it.
 *  `worms_parent_id` is intentionally absent — the FastAPI wire
 *  does not expose it (see file header), so the canonical projection
 *  cannot validate a field it has no business surfacing. */
const STRING_OPTIONAL_KEYS: readonly string[] = [
  "coldp_id", "status", "path",
];
const INTEGER_OPTIONAL_KEYS: readonly string[] = [
  "worms_id", "freshwater_id",
  "freshwater_parent_id",
  "species_count",
];
const BOOLEAN_OPTIONAL_KEYS: readonly string[] = [
  "is_extinct", "research_path_exists",
];

/** True iff `obj` carries `key` as an own property (not inherited).
 *  Used by `isValidTaxon` so the optional-wire-property validation
 *  only fires for keys the record explicitly sets — see ODD-NTP-001. */
function hasOwn(obj: Record<string, unknown>, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(obj, key);
}

/** Compare two ranks by taxonomic breadth: negative if `a` is broader
 *  than `b`, zero if equal, positive if `a` is narrower. */
export function compareRanks(a: Rank, b: Rank): number {
  return RANK_ORDER.indexOf(a) - RANK_ORDER.indexOf(b);
}
