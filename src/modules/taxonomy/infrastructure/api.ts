// Taxonomy infrastructure — typed adapter for FastAPI taxon endpoints.
// spec.md rule 4: infrastructure → domain (inward). The barrel
// re-exports fetchTaxon, fetchChildren, fetchDomains, and
// TaxonomyApiError. Wire `scientific_name` projects onto domain `name`;
// `isValidTaxon` rejects ranks outside the domain `Rank` union
// deterministically (no coercion — ODD-VTREE-001).
//
// ODD-NTP-001 (native-tree-parity data layer): every legacy tree
// field from the FastAPI `Taxon` payload survives the wire → domain
// projection. `fromWire` reads `coldp_id`, `worms_id`, `freshwater_id`,
// `freshwater_parent_id`, `status`, `is_extinct`, `path`,
// `species_count`, and `research_path_exists` verbatim, and preserves
// FastAPI's nullability: a missing or `null` wire value projects as
// `null`, never coerced to zero / empty string / another source. The
// FastAPI wire does NOT expose `worms_parent_id` (the WoRMS overlay
// column is used internally by `api/server.py::get_children` and
// read from the client cache in `web/nav.js`, but is not on the
// public wire shape), so the canonical `Taxon` does NOT carry a
// `worms_parent_id` field — inventing one would leak a private
// server column into the client contract. WoRMS source-aware parent
// ancestry must be built from attached tree edges (walking back
// through `worms_id IS NOT NULL` children already loaded into the
// cache) until/unless the API exposes the field in a separately
// authorized backend change.
//
// ODD-NTP-001 (source-aware helpers): the public `TaxonomySource`
// type + `FetchDomainsOptions` interface let callers append the
// exact optional query value `source=col|worms|freshwater` to both
// `/api/domains` and `/api/taxon/{id}/children`. The parameter is
// omitted when no source is supplied so the default CoL request
// shape is byte-identical to the pre-ODD-NTP-001 contract.
//
// ODD-TDFOLDER-001 — preview / materialize / open-folder typed
// contracts. The FastAPI server exposes three materialize-related
// endpoints (`api/server.py::materialize_research_folder_preview`,
// `::materialize_research_folder`, `::open_research_folder`); the
// React port projects each response through the canonical
// `MaterializePreview` / `MaterializeResult` / `OpenFolderResult`
// interfaces so the Folder tab UI never reconstructs / sanitises
// paths client-side (the server is the source of truth for the
// `research_dir`, `relative_path`, `absolute_path`, and per-
// segment `exists`/`is_dir`/`is_new` flags). The React port
// forwards the `source` query parameter verbatim so Freshwater /
// WoRMS hierarchies walk the right parent column, and uses POST
// for the two side-effecting endpoints (materialize + open-folder)
// so the server-side `mkdir` / `subprocess.Popen` calls are
// explicit about their filesystem impact. The wire `segments`
// payload is preserved verbatim — the React renderer is a
// for-each over the response array (no client-side grouping /
// filtering / pagination), mirroring how `SynonymName` /
// `DistributionEntry` already preserve their server ordering
// (ODD-TDSYN-001 + ODD-TDDIST-001). The materialize preview
// response carries `all_exist` so the React port can branch on a
// single instance-of check (no client-side recomputation of the
// new-vs-existing segment counts).
//
// ODD-TDDIST-001 — distribution wire → domain projection. Every
// legacy distribution field exposed on the FastAPI wire survives
// the projection: `id`, `area`, nullable `gazetteer`, nullable
// `establishment_means`, nullable `degree_of_establishment`. The
// UI only renders `establishment_means` + `area` (per the
// ODD-TDDIST-001 user constraint: "do not render gazetteer or
// degree") but the canonical projection MUST carry every wire
// field so a future server-composed gazetteer tooltip /
// degree-derived affordance does not require a coordinated React
// update — mirroring how `SynonymName.status` survives even
// though `SynonymTab` does not render it (ODD-TDSYN-001). Wire
// ordering (`ORDER BY establishment_means, area`) is preserved
// verbatim — the React port's render loop is a for-each over the
// response array and never sorts / groups / filters / paginates
// client-side (per the ODD-TDDIST-001 user constraint: "do not
// group/filter/sort").

import { isValidTaxon } from "../domain/taxon";
import type { Taxon } from "../domain/taxon";

type FetchLike = (
  input: string,
  init?: { method?: string },
) => Promise<{ ok: boolean; status: number; statusText: string; json: () => Promise<unknown> }>;

export interface FetchOptions {
  fetch?: FetchLike;
  baseUrl?: string;
}

/** Public source qualifier — `col` = Catalogue of Life (default),
 *  `worms` = World Register of Marine Species, `freshwater` =
 *  Freshwater Fishes overlay. Mirrors the FastAPI `/api/taxon/{id}/children`
 *  `source` query parameter (`api/server.py`) and the legacy
 *  `state.treeSource` (`web/state.js`). ODD-NTP-001: re-exported
 *  from the taxonomy barrel so React callers can type the option
 *  without a deep import. */
export type TaxonomySource = "col" | "worms" | "freshwater";

export interface FetchChildrenOptions extends FetchOptions {
  source?: TaxonomySource;
}

/** ODD-NTP-001: `fetchDomains` accepts the same `source` option as
 *  `fetchChildren`. The FastAPI `/api/domains` endpoint
 *  (`api/server.py`) currently ignores the parameter (it returns
 *  every root regardless of source), but the React helper forwards
 *  it so future server-side filtering / a future server change
 *  does not require a coordinated React update. */
export interface FetchDomainsOptions extends FetchOptions {
  source?: TaxonomySource;
}

export class TaxonomyApiError extends Error {
  readonly status: number | null;
  readonly cause: unknown;
  constructor(message: string, opts: { status?: number | null; cause?: unknown } = {}) {
    super(message);
    this.name = "TaxonomyApiError";
    this.status = opts.status ?? null;
    this.cause = opts.cause;
  }
}

function defaultFetch(): FetchLike {
  const fn = (globalThis as { fetch?: FetchLike }).fetch;
  if (!fn) {
    throw new TaxonomyApiError(
      "no fetch implementation available — pass opts.fetch outside a browser/Node\u226518",
    );
  }
  return fn;
}

function url(baseUrl: string, path: string): string {
  // ODD-MIGRATE-006 carveout (API origin default): the static
  // export at `out/` ships WITHOUT a `.env` file, so the React
  // build's `process.env.NEXT_PUBLIC_TAXA_API_ORIGIN` resolves to
  // `undefined` and the `?? ""` fallback in
  // `src/modules/taxonomy/presentation/TaxonomyTree.tsx` collapses
  // to an empty `baseUrl`. The path itself already starts with
  // `/api/...` (the FastAPI endpoint shape), so the legacy
  // concat-style helper produced the correct relative URL
  // (`""` + `"/api/domains"` = `"/api/domains"`) when baseUrl was
  // empty. Naively substituting `/api` for the empty baseUrl
  // (the literal "default it to `/api`" reading) would yield
  // `/api/api/domains`, which 404s. The adapter therefore absorbs
  // the empty-string edge case by returning the path as-is: the
  // runtime default becomes the relative `/api` (FastAPI's
  // `/api/*` routes match without the trailing-slash side effect
  // `new URL("", currentLocation)` introduces), and the path's
  // own `/api/` prefix is preserved verbatim. The same
  // path-as-is semantic applies to the post-f708a15 source
  // `?? "/api"` because that baseUrl duplicates the path's
  // leading segment — concatenating would otherwise duplicate the
  // `/api` prefix. When the env var IS configured (local dev with
  // `NEXT_PUBLIC_TAXA_API_ORIGIN=http://x`), the caller-supplied
  // baseUrl wins verbatim (existing concat behaviour, trailing-
  //-slash trim included).
  if (baseUrl === "" || baseUrl === "/api") return path;
  return baseUrl.replace(/\/+$/, "") + path;
}

async function readJson(r: { json: () => Promise<unknown> }): Promise<unknown> {
  try { return await r.json(); }
  catch (cause) {
    throw new TaxonomyApiError(
      "taxonomy API returned malformed JSON: " + String((cause as Error)?.message ?? cause),
      { cause },
    );
  }
}

/** Wire → domain projection. Every legacy tree field exposed on
 *  the FastAPI wire is read verbatim; missing-or-`null` wire values
 *  default to `null` so FastAPI's nullability is preserved (never
 *  coerced to zero / empty string / another source). ODD-NTP-001.
 *  The string id `coldp_id` is preserved as a string (`Optional[str]`
 *  in FastAPI); the integer ids (`worms_id`, `freshwater_id`,
 *  `freshwater_parent_id`, `species_count`) are validated by
 *  `isValidTaxon` for `Number.isInteger` so a wire string `"42"` or
 *  float `1.5` would be rejected (FastAPI's Pydantic layer would
 *  catch these first). `worms_parent_id` is NOT projected — the
 *  FastAPI wire does not expose it, so a canonical `Taxon` cannot
 *  carry it without leaking a private server column into the
 *  client contract. */
function fromWire(payload: unknown, context: string): Taxon {
  if (typeof payload !== "object" || payload === null) {
    throw new TaxonomyApiError(
      `taxonomy API ${context} returned a non-object payload: ` +
      (payload === null ? "null" : typeof payload),
    );
  }
  const v = payload as Record<string, unknown>;
  const candidate: Taxon = {
    id: v["id"] as number,
    name: v["scientific_name"] as string,
    rank: v["rank"] as Taxon["rank"],
    authorship: (v["authorship"] as string | null) ?? null,
    parent_id: (v["parent_id"] as number | null) ?? null,
    coldp_id: (v["coldp_id"] as string | null) ?? null,
    worms_id: (v["worms_id"] as number | null) ?? null,
    freshwater_id: (v["freshwater_id"] as number | null) ?? null,
    freshwater_parent_id: (v["freshwater_parent_id"] as number | null) ?? null,
    status: (v["status"] as string | null) ?? null,
    is_extinct: typeof v["is_extinct"] === "boolean" ? v["is_extinct"] : null,
    path: (v["path"] as string | null) ?? null,
    species_count: (v["species_count"] as number | null) ?? null,
    research_path_exists:
      typeof v["research_path_exists"] === "boolean"
        ? v["research_path_exists"]
        : null,
  };
  if (!isValidTaxon(candidate)) {
    throw new TaxonomyApiError(
      `taxonomy API ${context} returned an invalid Taxon: domain contract violated`,
    );
  }
  return candidate;
}

/** Shared list-shape projection: read a JSON array and validate each
 *  element through `fromWire`. Used by `fetchChildren` and
 *  `fetchDomains` so a non-array payload, a per-element shape mismatch,
 *  and an unsupported rank all surface as `TaxonomyApiError`. The
 *  caller-supplied `context` is interpolated into every error message
 *  for parity with `fromWire`. */
function fromWireList(
  payload: unknown,
  context: string,
): readonly Taxon[] {
  if (!Array.isArray(payload)) {
    throw new TaxonomyApiError(
      `taxonomy API ${context} returned a non-array payload: ` + typeof payload,
    );
  }
  return payload.map((element, i) => fromWire(element, `${context}[${i}]`));
}

export async function fetchTaxon(
  id: number,
  opts: FetchOptions = {},
): Promise<Taxon> {
  if (!Number.isInteger(id) || id < 0) {
    throw new TaxonomyApiError(`fetchTaxon: id must be a non-negative integer; got ${id}`);
  }
  const f = opts.fetch ?? defaultFetch();
  const r = await f(url(opts.baseUrl ?? "", `/api/taxon/${id}`));
  if (!r.ok) {
    throw new TaxonomyApiError(
      `taxonomy API GET /api/taxon/${id} failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  return fromWire(await readJson(r), `/api/taxon/${id}`);
}

export async function fetchChildren(
  id: number,
  opts: FetchChildrenOptions = {},
): Promise<readonly Taxon[]> {
  if (!Number.isInteger(id) || id < 0) {
    throw new TaxonomyApiError(`fetchChildren: id must be a non-negative integer; got ${id}`);
  }
  const f = opts.fetch ?? defaultFetch();
  const q = sourceQuery(opts.source);
  const r = await f(url(opts.baseUrl ?? "", `/api/taxon/${id}/children${q}`));
  if (!r.ok) {
    throw new TaxonomyApiError(
      `taxonomy API GET /api/taxon/${id}/children failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  return fromWireList(await readJson(r), `/api/taxon/${id}/children`);
}

/** Build the optional `?source=…` suffix. Returns `""` when no
 *  source is supplied so the default CoL request stays byte-identical
 *  to the pre-ODD-NTP-001 URL shape (no trailing `?`, no empty
 *  fragment). ODD-NTP-001. */
function sourceQuery(source: TaxonomySource | undefined): string {
  return source ? `?source=${encodeURIComponent(source)}` : "";
}

/** Top-level domains returned by `GET /api/domains` — CoL domains
 *  (Archaea, Bacteria, Eukaryota, Viruses), the Biota WoRMS
 *  superdomain, and the synthetic Freshwater Fishes root. Returns the
 *  same `Taxon` projection as `fetchTaxon` / `fetchChildren`; a wire
 *  record carrying an unsupported rank (anything outside the
 *  `Rank` union) is rejected via `TaxonomyApiError`. Caller-supplied
 *  `baseUrl` follows the same convention as `fetchTaxon`.
 *
 *  ODD-NTP-001: accepts the same `source` option as `fetchChildren`.
 *  When supplied, the helper appends `?source=col|worms|freshwater`
 *  verbatim; when omitted, the URL stays `/api/domains` (byte-identical
 *  to the pre-ODD-NTP-001 contract). The FastAPI server may ignore
 *  the parameter on this endpoint — the helper forwards it anyway so
 *  the React call site stays uniform across both endpoints and any
 *  future server-side filtering lands without a React update. */
export async function fetchDomains(
  opts: FetchDomainsOptions = {},
): Promise<readonly Taxon[]> {
  const f = opts.fetch ?? defaultFetch();
  const q = sourceQuery(opts.source);
  const r = await f(url(opts.baseUrl ?? "", `/api/domains${q}`));
  if (!r.ok) {
    throw new TaxonomyApiError(
      `taxonomy API GET /api/domains failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  return fromWireList(await readJson(r), "/api/domains");
}

/** ODD-TDS-001 — canonical typed `SearchLink` projection. Mirrors
 *  the FastAPI `api/server.py::SearchLink` Pydantic model field-for-
 *  field. The server is the source of truth for the URL string
 *  (server-composed URL encoding at composition time) — `fetchSearches`
 *  preserves the wire `url` verbatim and never constructs / mutates
 *  / template-fills a URL locally. The legacy frontend kept a
 *  SEARCH_ENGINES constant that carried both URL definitions AND
 *  display-only metadata (icon, category); the server payload does
 *  NOT carry the icon / category fields, so the canonical
 *  `SearchLink` deliberately omits them. The React port's category
 *  bridge lives in `presentation/search-categories.ts` and maps
 *  engine keys to display-only metadata without ever touching the
 *  URL. */
export interface SearchLink {
  readonly engine: string;
  readonly label: string;
  readonly url: string;
}

/** Per-engine validator. Every required field must be present with
 *  the right type and a non-empty string content. The URL is
 *  validated as a non-empty string but NOT parsed — the server is
 *  the source of truth for URL encoding, and the React port must
 *  send the wire URL through `target="_blank" rel="noopener
 *  noreferrer"` exactly as the server composed it. Any wire
 *  mismatch (missing field, wrong type, empty engine/label/url)
 *  surfaces as `TaxonomyApiError` so a per-element shape drift
 *  cannot slip past the projection layer. */
function isValidSearchLink(value: unknown): value is SearchLink {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.engine === "string" && v.engine.length > 0 &&
    typeof v.label === "string" && v.label.length > 0 &&
    typeof v.url === "string" && v.url.length > 0
  );
}

/** ODD-TDS-001 — wire → domain projection for the search-link
 *  payload. Reads the JSON array and validates each element
 *  through `isValidSearchLink`. A non-array payload or a
 *  per-element shape mismatch surfaces as `TaxonomyApiError` so
 *  the SearchTab render loop can branch on a single instance/name
 *  check. Mirrors the `fromWireList` contract used by
 *  `fetchChildren` / `fetchDomains` for parity: the caller-supplied
 *  `context` is interpolated into every error message so log
 *  lines can attribute the failure to the right endpoint. */
function fromWireSearchList(
  payload: unknown,
  context: string,
): readonly SearchLink[] {
  if (!Array.isArray(payload)) {
    throw new TaxonomyApiError(
      `taxonomy API ${context} returned a non-array payload: ` + typeof payload,
    );
  }
  const out: SearchLink[] = [];
  for (let i = 0; i < payload.length; i++) {
    if (!isValidSearchLink(payload[i])) {
      throw new TaxonomyApiError(
        `taxonomy API ${context} returned an invalid SearchLink at index ${i}: domain contract violated`,
      );
    }
    out.push(payload[i] as SearchLink);
  }
  return out;
}

/** Public options surface for `fetchSearches`. Mirrors the
 *  `FetchOptions` interface (transport-level `fetch` + `baseUrl`)
 *  so the React port can drive the request with a stubbed fetch
 *  under test. No additional transport options — the search-links
 *  endpoint does not accept a `source=` qualifier (the URLs are
 *  composed against the taxon's `scientific_name` + `authorship`
 *  on the server side, regardless of the active source). */
export interface FetchSearchesOptions extends FetchOptions {}

/** ODD-TDS-001 — fetch the server-composed search-engine links for
 *  a single taxon. Mirrors `fetchTaxon` + `fetchChildren` in
 *  transport shape: id validation → fetch + status guard → JSON
 *  parsing → wire → domain projection. The wire shape is a JSON
 *  array of `SearchLink` objects (`engine`, `label`, `url`); the
 *  server returns 17 entries today (14 canonical search engines +
 *  3 curated destinations), but the React port's `SearchTab`
 *  only renders the subset that has a canonical category slot in
 *  the pure category bridge (`presentation/search-categories.ts`).
 *  URL preservation is byte-exact — the server's URL encoding
 *  flows through untouched. */
export async function fetchSearches(
  id: number,
  opts: FetchSearchesOptions = {},
): Promise<readonly SearchLink[]> {
  if (!Number.isInteger(id) || id < 0) {
    throw new TaxonomyApiError(`fetchSearches: id must be a non-negative integer; got ${id}`);
  }
  const f = opts.fetch ?? defaultFetch();
  const r = await f(url(opts.baseUrl ?? "", `/api/taxon/${id}/searches`));
  if (!r.ok) {
    throw new TaxonomyApiError(
      `taxonomy API GET /api/taxon/${id}/searches failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  return fromWireSearchList(await readJson(r), `/api/taxon/${id}/searches`);
}

/** ODD-TDV-001 — wire → domain projection for `/api/taxon/{id}/vernaculars`.
 *  Mirrors the FastAPI `api/server.py::Vernacular` Pydantic model
 *  field-for-field: `id`, `name`, nullable `language`, nullable `country`.
 *  The server preserves the FastAPI nullability: a wire `null`
 *  surfaces as `null` (never coerced to empty string or to a
 *  different language code), so the React `VernacularTab` can omit
 *  the language chip when the row carries `language: null` and the
 *  country chip when it carries `country: null`. The legacy
 *  `web/detail.js::loadDetail` fetches this exact endpoint and
 *  passes the raw rows into `buildDetailSection`; the React port
 *  uses the canonical projection so the byte-identical
 *  visual rendering (`.lang` + `.country` chips + name span)
 *  survives the cutover. */
export interface VernacularName {
  readonly id: number;
  readonly name: string;
  readonly language: string | null;
  readonly country: string | null;
}

/** Per-row validator. Every required field must be present with
 *  the right type and a non-empty string content for `name`. The
 *  nullable fields (`language`, `country`) MUST be either a string
 *  (the ISO code verbatim — the server preserves `""` as the
 *  "unknown language tag" sentinel that CoL ships) or `null` (the
 *  wire-side "no value"). Any wire mismatch (missing field, wrong
 *  type, empty `name`) surfaces as `TaxonomyApiError` so a
 *  per-element shape drift cannot slip past the projection layer. */
function isValidVernacular(value: unknown): value is VernacularName {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === "number" && Number.isInteger(v.id) &&
    typeof v.name === "string" && v.name.length > 0 &&
    (v.language === null || typeof v.language === "string") &&
    (v.country === null || typeof v.country === "string")
  );
}

/** ODD-TDV-001 — wire → domain projection for the vernaculars
 *  payload. Reads the JSON array and validates each element
 *  through `isValidVernacular`. A non-array payload or a
 *  per-element shape mismatch surfaces as `TaxonomyApiError` so
 *  the VernacularTab render loop can branch on a single
 *  instance/name check. Mirrors `fromWireSearchList` and
 *  `fromWireList` byte-for-byte: the caller-supplied `context` is
 *  interpolated into every error message so log lines can
 *  attribute the failure to the right endpoint. */
function fromWireVernacularList(
  payload: unknown,
  context: string,
): readonly VernacularName[] {
  if (!Array.isArray(payload)) {
    throw new TaxonomyApiError(
      `taxonomy API ${context} returned a non-array payload: ` + typeof payload,
    );
  }
  const out: VernacularName[] = [];
  for (let i = 0; i < payload.length; i++) {
    if (!isValidVernacular(payload[i])) {
      throw new TaxonomyApiError(
        `taxonomy API ${context} returned an invalid VernacularName at index ${i}: domain contract violated`,
      );
    }
    out.push(payload[i] as VernacularName);
  }
  return out;
}

/** Public options surface for `fetchVernaculars`. Mirrors the
 *  `FetchOptions` interface (transport-level `fetch` + `baseUrl`)
 *  so the React port can drive the request with a stubbed fetch
 *  under test. `limit` is forwarded verbatim as `?limit=N`; the
 *  legacy `/api/taxon/{id}/vernaculars?limit=200` request
 *  (`web/detail.js::loadDetail`) is the byte-identical default,
 *  so omitting the option keeps the React cutover's request
 *  shape aligned with the legacy oracle. The FastAPI endpoint
 *  clamps the limit server-side (`ge=1, le=500`); the React port
 *  does not re-validate the clamp because the server is the
 *  source of truth for HTTP error semantics. */
export interface FetchVernacularsOptions extends FetchOptions {
  readonly limit?: number;
}

/** ODD-TDV-001 — fetch the vernacular (common name) rows for a
 *  single taxon. Mirrors `fetchTaxon` + `fetchChildren` +
 *  `fetchSearches` in transport shape: id validation → fetch +
 *  status guard → JSON parsing → wire → domain projection. The
 *  wire shape is a JSON array of `VernacularName` objects
 *  (`id`, `name`, nullable `language`, nullable `country`);
 *  each row carries the verbatim ISO language / country code
 *  the server preserves, and the React port paints it through
 *  the `.lang` + `.country` chips byte-identically. This is the
 *  dedicated endpoint that backs the DetailPanel Vernaculars tab
 *  — the React port MUST NOT read `vernaculars` off the embedded
 *  `/api/taxon/{id}` payload (`api/server.py::Taxon.vernaculars`
 *  is not exposed on the public wire shape — only the dedicated
 *  `/api/taxon/{id}/vernaculars` endpoint returns the rows). */
export async function fetchVernaculars(
  id: number,
  opts: FetchVernacularsOptions = {},
): Promise<readonly VernacularName[]> {
  if (!Number.isInteger(id) || id < 0) {
    throw new TaxonomyApiError(`fetchVernaculars: id must be a non-negative integer; got ${id}`);
  }
  const f = opts.fetch ?? defaultFetch();
  const limit = opts.limit ?? 200;
  const query = `?limit=${encodeURIComponent(String(limit))}`;
  const r = await f(url(opts.baseUrl ?? "", `/api/taxon/${id}/vernaculars${query}`));
  if (!r.ok) {
    throw new TaxonomyApiError(
      `taxonomy API GET /api/taxon/${id}/vernaculars failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  return fromWireVernacularList(await readJson(r), `/api/taxon/${id}/vernaculars`);
}

/** ODD-TDSYN-001 — wire → domain projection for
 *  `/api/taxon/{id}/synonyms`. Mirrors the FastAPI
 *  `api/server.py::Synonym` Pydantic model field-for-field:
 *  `id`, `rank`, `scientific_name`, nullable `authorship`,
 *  `status`. The server preserves FastAPI nullability for the
 *  authorship column (CoL/TextTree rows can carry `null`
 *  authorship) and exposes `status` as a non-nullable string
 *  because the SQL pre-filters to rows where
 *  `status != 'accepted'` (`api/server.py::get_synonyms`). The
 *  React port preserves the wire rank / name / authorship /
 *  status values verbatim (the UI does NOT render the
 *  status field — see `presentation/SynonymTab.tsx` — but the
 *  projection MUST carry it so a future server-composed
 *  status-derived affordance does not need a coordinated React
 *  update). Ordering is server-driven (`ORDER BY rank,
 *  scientific_name`) — the React port's render loop is a
 *  for-each over the response array and never sorts / paginates
 *  the wire payload client-side. */
export interface SynonymName {
  readonly id: number;
  readonly rank: string;
  readonly scientific_name: string;
  readonly authorship: string | null;
  readonly status: string;
}

/** Per-row validator. Every required field must be present with
 *  the right type and a non-empty string content for `rank` and
 *  `scientific_name`. `status` is server-guaranteed non-null
 *  (the SQL pre-filter rejects accepted rows) and must be a
 *  non-empty string. The nullable `authorship` MUST be either a
 *  string (verbatim — the server passes CoL / TextTree through
 *  untouched) or `null` (the wire-side "no value"). Any wire
 *  mismatch (missing field, wrong type, empty rank / name /
 *  status) surfaces as `TaxonomyApiError` so a per-element
 *  shape drift cannot slip past the projection layer. */
function isValidSynonym(value: unknown): value is SynonymName {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === "number" && Number.isInteger(v.id) &&
    typeof v.rank === "string" && v.rank.length > 0 &&
    typeof v.scientific_name === "string" && v.scientific_name.length > 0 &&
    (v.authorship === null || typeof v.authorship === "string") &&
    typeof v.status === "string" && v.status.length > 0
  );
}

/** ODD-TDSYN-001 — wire → domain projection for the synonyms
 *  payload. Reads the JSON array and validates each element
 *  through `isValidSynonym`. A non-array payload or a
 *  per-element shape mismatch surfaces as `TaxonomyApiError`
 *  so the SynonymTab render loop can branch on a single
 *  instance / name check. Mirrors `fromWireSearchList` and
 *  `fromWireVernacularList` byte-for-byte: the caller-supplied
 *  `context` is interpolated into every error message so log
 *  lines can attribute the failure to the right endpoint. */
function fromWireSynonymList(
  payload: unknown,
  context: string,
): readonly SynonymName[] {
  if (!Array.isArray(payload)) {
    throw new TaxonomyApiError(
      `taxonomy API ${context} returned a non-array payload: ` + typeof payload,
    );
  }
  const out: SynonymName[] = [];
  for (let i = 0; i < payload.length; i++) {
    if (!isValidSynonym(payload[i])) {
      throw new TaxonomyApiError(
        `taxonomy API ${context} returned an invalid SynonymName at index ${i}: domain contract violated`,
      );
    }
    out.push(payload[i] as SynonymName);
  }
  return out;
}

/** Public options surface for `fetchSynonyms`. Mirrors the
 *  `FetchOptions` interface (transport-level `fetch` + `baseUrl`)
 *  so the React port can drive the request with a stubbed fetch
 *  under test. `limit` is forwarded verbatim as `?limit=N`; the
 *  legacy `/api/taxon/{id}/synonyms?limit=200` request
 *  (`web/detail.js::loadDetail`) is the byte-identical default,
 *  so omitting the option keeps the React cutover's request
 *  shape aligned with the legacy oracle. The FastAPI endpoint
 *  clamps the limit server-side (`ge=1, le=1000`); the React
 *  port does not re-validate the clamp because the server is
 *  the source of truth for HTTP error semantics. */
export interface FetchSynonymsOptions extends FetchOptions {
  readonly limit?: number;
}

/** ODD-TDSYN-001 — fetch the synonym (historical name) rows for
 *  a single taxon. Mirrors `fetchTaxon` + `fetchChildren` +
 *  `fetchSearches` + `fetchVernaculars` in transport shape: id
 *  validation → fetch + status guard → JSON parsing → wire →
 *  domain projection. The wire shape is a JSON array of
 *  `SynonymName` objects (`id`, `rank`, `scientific_name`,
 *  nullable `authorship`, `status`); each row preserves the
 *  verbatim rank / scientific_name / authorship / status values
 *  the server composes. The endpoint is source-AGNOSTIC
 *  (mirrors the legacy `web/detail.js::loadDetail` payload which
 *  is also source-agnostic — the legacy oracle only changes the
 *  selected taxon), so the React port's per-taxon cache
 *  survives source switches (the contract mirrors the
 *  `fetchVernaculars` source-agnostic retention). The wire
 *  ordering (`ORDER BY rank, scientific_name`) is preserved
 *  verbatim — the React port's render loop is a for-each over
 *  the response array and never sorts / paginates client-side. */
export async function fetchSynonyms(
  id: number,
  opts: FetchSynonymsOptions = {},
): Promise<readonly SynonymName[]> {
  if (!Number.isInteger(id) || id < 0) {
    throw new TaxonomyApiError(`fetchSynonyms: id must be a non-negative integer; got ${id}`);
  }
  const f = opts.fetch ?? defaultFetch();
  const limit = opts.limit ?? 200;
  const query = `?limit=${encodeURIComponent(String(limit))}`;
  const r = await f(url(opts.baseUrl ?? "", `/api/taxon/${id}/synonyms${query}`));
  if (!r.ok) {
    throw new TaxonomyApiError(
      `taxonomy API GET /api/taxon/${id}/synonyms failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  return fromWireSynonymList(await readJson(r), `/api/taxon/${id}/synonyms`);
}

/** ODD-TDDIST-001 — wire → domain projection for
 *  `/api/taxon/{id}/distribution`. Mirrors the FastAPI
 *  `api/server.py::DistributionEntry` Pydantic model field-for-
 *  field: `id`, `area`, nullable `gazetteer`, nullable
 *  `establishment_means`, nullable `degree_of_establishment`.
 *  The server preserves FastAPI nullability for the three
 *  nullable columns (CoL distribution rows may carry `null`
 *  gazetteer + `null` establishment_means + `null`
 *  degree_of_establishment). The `area` column is server-
 *  guaranteed non-null + non-empty (CoL NOT NULL constraint +
 *  the SQL only returns rows where `area IS NOT NULL AND
 *  area != ''`). The React port preserves every wire field
 *  verbatim — the UI only renders `establishment_means` +
 *  `area` (per the ODD-TDDIST-001 user constraint: "do not
 *  render gazetteer/degree or group/filter/sort") but the
 *  canonical projection MUST carry every wire field so a
 *  future server-composed gazetteer tooltip or
 *  degree-derived affordance does not require a coordinated
 *  React update — mirroring how `SynonymName.status`
 *  survives even though `SynonymTab` does not render it
 *  (ODD-TDSYN-001). Wire ordering
 *  (`ORDER BY establishment_means, area`) is preserved
 *  verbatim — the React port's render loop is a for-each
 *  over the response array and never sorts / groups /
 *  filters / paginates client-side (per the
 *  ODD-TDDIST-001 user constraint). */
export interface DistributionEntry {
  readonly id: number;
  readonly area: string;
  readonly gazetteer: string | null;
  readonly establishment_means: string | null;
  readonly degree_of_establishment: string | null;
}

/** Per-row validator. Every required field must be present
 *  with the right type and a non-empty string content for
 *  `area`. The three nullable fields (`gazetteer`,
 *  `establishment_means`, `degree_of_establishment`) MUST be
 *  either a string (verbatim — the server preserves CoL's
 *  nullable columns untouched) or `null` (the wire-side "no
 *  value"). Any wire mismatch (missing field, wrong type,
 *  empty `area`) surfaces as `TaxonomyApiError` so a
 *  per-element shape drift cannot slip past the projection
 *  layer. */
function isValidDistribution(value: unknown): value is DistributionEntry {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === "number" && Number.isInteger(v.id) &&
    typeof v.area === "string" && v.area.length > 0 &&
    (v.gazetteer === null || typeof v.gazetteer === "string") &&
    (v.establishment_means === null || typeof v.establishment_means === "string") &&
    (v.degree_of_establishment === null ||
      typeof v.degree_of_establishment === "string")
  );
}

/** ODD-TDDIST-001 — wire → domain projection for the
 *  distribution payload. Reads the JSON array and validates
 *  each element through `isValidDistribution`. A non-array
 *  payload or a per-element shape mismatch surfaces as
 *  `TaxonomyApiError` so the DistributionTab render loop can
 *  branch on a single instance/name check. Mirrors
 *  `fromWireSearchList`, `fromWireVernacularList`, and
 *  `fromWireSynonymList` byte-for-byte: the caller-supplied
 *  `context` is interpolated into every error message so
 *  log lines can attribute the failure to the right
 *  endpoint. */
function fromWireDistributionList(
  payload: unknown,
  context: string,
): readonly DistributionEntry[] {
  if (!Array.isArray(payload)) {
    throw new TaxonomyApiError(
      `taxonomy API ${context} returned a non-array payload: ` + typeof payload,
    );
  }
  const out: DistributionEntry[] = [];
  for (let i = 0; i < payload.length; i++) {
    if (!isValidDistribution(payload[i])) {
      throw new TaxonomyApiError(
        `taxonomy API ${context} returned an invalid DistributionEntry at index ${i}: domain contract violated`,
      );
    }
    out.push(payload[i] as DistributionEntry);
  }
  return out;
}

/** Public options surface for `fetchDistribution`. Mirrors the
 *  `FetchOptions` interface (transport-level `fetch` + `baseUrl`)
 *  so the React port can drive the request with a stubbed fetch
 *  under test. `limit` is forwarded verbatim as `?limit=N`; the
 *  legacy `/api/taxon/{id}/distribution?limit=200` request
 *  (`web/detail.js::loadDetail`) is the byte-identical default,
 *  so omitting the option keeps the React cutover's request
 *  shape aligned with the legacy oracle. The FastAPI endpoint
 *  clamps the limit server-side (`ge=1, le=1000`); the React
 *  port does not re-validate the clamp because the server is
 *  the source of truth for HTTP error semantics. */
export interface FetchDistributionOptions extends FetchOptions {
  readonly limit?: number;
}

/** ODD-TDDIST-001 — fetch the distribution (geographic range)
 *  rows for a single taxon. Mirrors `fetchTaxon` +
 *  `fetchChildren` + `fetchSearches` + `fetchVernaculars` +
 *  `fetchSynonyms` in transport shape: id validation → fetch +
 *  status guard → JSON parsing → wire → domain projection. The
 *  wire shape is a JSON array of `DistributionEntry` objects
 *  (`id`, `area`, nullable `gazetteer`, nullable
 *  `establishment_means`, nullable `degree_of_establishment`);
 *  each row preserves the verbatim CoL nullable columns the
 *  server passes through. The endpoint is source-AGNOSTIC
 *  (mirrors the legacy `web/detail.js::loadDetail` payload
 *  which is also source-agnostic — the legacy oracle only
 *  changes the selected taxon), so the React port's per-taxon
 *  cache survives source switches (the contract mirrors the
 *  `fetchVernaculars` + `fetchSynonyms` source-agnostic
 *  retention). The wire ordering
 *  (`ORDER BY establishment_means, area`) is preserved
 *  verbatim — the React port's render loop is a for-each over
 *  the response array and never sorts / groups / filters /
 *  paginates client-side (per the ODD-TDDIST-001 user
 *  constraint). The UI does NOT render the wire `gazetteer` or
 *  `degree_of_establishment` fields (per the ODD-TDDIST-001
 *  user constraint: "do not render gazetteer/degree or
 *  group/filter/sort"), but the canonical projection carries
 *  them so a future server-composed affordance does not
 *  require a coordinated React update. */
export async function fetchDistribution(
  id: number,
  opts: FetchDistributionOptions = {},
): Promise<readonly DistributionEntry[]> {
  if (!Number.isInteger(id) || id < 0) {
    throw new TaxonomyApiError(`fetchDistribution: id must be a non-negative integer; got ${id}`);
  }
  const f = opts.fetch ?? defaultFetch();
  const limit = opts.limit ?? 200;
  const query = `?limit=${encodeURIComponent(String(limit))}`;
  const r = await f(url(opts.baseUrl ?? "", `/api/taxon/${id}/distribution${query}`));
  if (!r.ok) {
    throw new TaxonomyApiError(
      `taxonomy API GET /api/taxon/${id}/distribution failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  return fromWireDistributionList(await readJson(r), `/api/taxon/${id}/distribution`);
}

/** ODD-TDFOLDER-001 — wire → domain projection for a single
 *  `materialize-preview` segment. Mirrors the FastAPI
 *  `api/server.py::materialize_research_folder_preview` per-segment
 *  payload field-for-field: `name`, `exists`, `is_dir`, `is_new`.
 *  The server preserves FastAPI nullability for every field; the
 *  React port preserves it too (no client-side coercion) so the
 *  renderer can branch on each flag's nullability independently.
 *  The cumulative path is NOT projected on the segment (the
 *  server builds it inside `_build_segments` + the `RESEARCH_DIR`
 *  join — the React port lets `MaterializePreview.research_dir` +
 *  `MaterializePreview.relative_path` carry the cumulative
 *  projection instead so the renderer does not reconstruct paths
 *  client-side). */
export interface MaterializePreviewSegment {
  readonly name: string;
  readonly exists: boolean;
  readonly is_dir: boolean;
  readonly is_new: boolean;
}

/** Per-segment validator. Every required field must be present with
 *  the right type and a non-empty string content for `name`. The
 *  three boolean fields MUST be booleans (the server preserves the
 *  Python `bool`/`is_dir()` result verbatim). Any wire mismatch
 *  surfaces as `TaxonomyApiError` so a per-element shape drift
 *  cannot slip past the projection layer. */
function isValidMaterializePreviewSegment(
  value: unknown,
): value is MaterializePreviewSegment {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.name === "string" && v.name.length > 0 &&
    typeof v.exists === "boolean" &&
    typeof v.is_dir === "boolean" &&
    typeof v.is_new === "boolean"
  );
}

/** ODD-TDFOLDER-001 — wire → domain projection for
 *  `/api/taxon/{id}/materialize-preview`. Mirrors the FastAPI
 *  `api/server.py::materialize_research_folder_preview` response
 *  field-for-field: `ok`, `taxon_id`, `scientific_name`,
 *  `research_dir`, `relative_path`, `absolute_path`, `segments[]`,
 *  `new_count`, `existing_count`, `all_exist`. The server is the
 *  source of truth for the `research_dir` absolute path + the
 *  `relative_path` + the `absolute_path` join — the React port
 *  preserves all three verbatim and never joins / sanitises /
 *  reconstructs paths client-side (the legacy
 *  `web/detail.js::renderFolderTab` likewise read `acc` straight
 *  from the wire `research_dir` + `seg.name`, but the React port
 *  delegates the cumulative-path join to the server via
 *  `relative_path` / `absolute_path` so the renderer never
 *  carries path-join logic). `all_exist` is server-computed
 *  (`new_count === 0`); the React renderer branches on the wire
 *  value verbatim. The `segments[]` payload preserves the server-
 *  side ordering (ancestor → focused taxon) — the renderer is a
 *  for-each over the response array and never sorts / groups /
 *  paginates client-side. */
export interface MaterializePreview {
  readonly ok: boolean;
  readonly taxon_id: number;
  readonly scientific_name: string;
  readonly research_dir: string;
  readonly relative_path: string;
  readonly absolute_path: string;
  readonly segments: readonly MaterializePreviewSegment[];
  readonly new_count: number;
  readonly existing_count: number;
  readonly all_exist: boolean;
}

/** Top-level preview validator. Every required field must be
 *  present with the right type. `ok` MUST be a boolean (the
 *  server is the source of truth for the response shape — a
 *  string `"true"` would be rejected here so the React port
 *  cannot silently bypass the projection). `taxon_id`,
 *  `new_count`, `existing_count` are non-negative integers;
 *  `scientific_name`, `research_dir`, `relative_path`,
 *  `absolute_path` are non-empty strings; `segments` is an array
 *  validated element-by-element through
 *  `isValidMaterializePreviewSegment`; `all_exist` is a boolean.
 *  Any wire mismatch surfaces as `TaxonomyApiError` so a
 *  per-field shape drift cannot slip past the projection layer. */
function isValidMaterializePreview(value: unknown): value is MaterializePreview {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.ok === "boolean" &&
    typeof v.taxon_id === "number" && Number.isInteger(v.taxon_id) && v.taxon_id >= 0 &&
    typeof v.scientific_name === "string" && v.scientific_name.length > 0 &&
    typeof v.research_dir === "string" && v.research_dir.length > 0 &&
    typeof v.relative_path === "string" && v.relative_path.length > 0 &&
    typeof v.absolute_path === "string" && v.absolute_path.length > 0 &&
    Array.isArray(v.segments) &&
    typeof v.new_count === "number" && Number.isInteger(v.new_count) && v.new_count >= 0 &&
    typeof v.existing_count === "number" && Number.isInteger(v.existing_count) && v.existing_count >= 0 &&
    typeof v.all_exist === "boolean"
  );
}

/** ODD-TDFOLDER-001 — wire → domain projection for the
 *  materialize-preview payload. Validates the top-level shape via
 *  `isValidMaterializePreview`, then validates each segment via
 *  `isValidMaterializePreviewSegment`. A non-object payload, a
 *  top-level shape mismatch, or a per-segment shape mismatch
 *  surfaces as `TaxonomyApiError` so the FolderTab render loop can
 *  branch on a single instance / name check. The caller-supplied
 *  `context` is interpolated into every error message so log
 *  lines can attribute the failure to the right endpoint (mirrors
 *  `fromWireDistributionList` / `fromWireSearchList` byte-for-
 *  byte). */
function fromWireMaterializePreview(
  payload: unknown,
  context: string,
): MaterializePreview {
  if (!isValidMaterializePreview(payload)) {
    throw new TaxonomyApiError(
      `taxonomy API ${context} returned an invalid MaterializePreview: domain contract violated`,
    );
  }
  const out: MaterializePreviewSegment[] = [];
  for (let i = 0; i < payload.segments.length; i++) {
    if (!isValidMaterializePreviewSegment(payload.segments[i])) {
      throw new TaxonomyApiError(
        `taxonomy API ${context} returned an invalid MaterializePreviewSegment at index ${i}: domain contract violated`,
      );
    }
    out.push(payload.segments[i] as MaterializePreviewSegment);
  }
  return { ...payload, segments: out };
}

/** ODD-TDFOLDER-001 — public options surface for
 *  `previewMaterialize`. Mirrors `FetchChildrenOptions` (transport-
 *  level `fetch` + `baseUrl` + optional `source`). The source
 *  selector selects which hierarchy to walk: "col" reads
 *  `parent_id`, "worms" reads `worms_parent_id`, "freshwater"
 *  reads `freshwater_parent_id`. Omitting the option keeps the
 *  default CoL request byte-identical to the legacy oracle (the
 *  FastAPI server's `source` query param defaults to "col" via
 *  `Query(default="col", pattern="^(col|worms|freshwater)$")`). */
export interface FetchMaterializePreviewOptions extends FetchOptions {
  source?: TaxonomySource;
}

/** ODD-TDFOLDER-001 — GET the materialize-preview payload for a
 *  single taxon. Mirrors the canonical GET-shape pattern used by
 *  `fetchDomains` / `fetchChildren` / `fetchSearches`: id
 *  validation → fetch + status guard → JSON parsing → wire →
 *  domain projection. The endpoint does NOT mutate the server
 *  filesystem (`api/server.py::materialize_research_folder_preview`
 *  builds the cumulative paths and reads `.exists()`/`.is_dir()`
 *  without `mkdir`); the React port forwards GET because the
 *  preview is purely informational (the user must confirm
 *  separately via `materializeResearch`). The wire `ok` field is
 *  preserved verbatim on the canonical `MaterializePreview`
 *  projection (the server is the source of truth for the
 *  response shape — the renderer does not branch on `ok` because
 *  a non-OK would surface as HTTP 5xx + `TaxonomyApiError`
 *  before reaching the projection layer). */
export async function previewMaterialize(
  id: number,
  opts: FetchMaterializePreviewOptions = {},
): Promise<MaterializePreview> {
  if (!Number.isInteger(id) || id < 0) {
    throw new TaxonomyApiError(
      `previewMaterialize: id must be a non-negative integer; got ${id}`,
    );
  }
  const f = opts.fetch ?? defaultFetch();
  const q = sourceQuery(opts.source);
  const r = await f(url(opts.baseUrl ?? "", `/api/taxon/${id}/materialize-preview${q}`));
  if (!r.ok) {
    throw new TaxonomyApiError(
      `taxonomy API GET /api/taxon/${id}/materialize-preview failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  return fromWireMaterializePreview(
    await readJson(r),
    `/api/taxon/${id}/materialize-preview`,
  );
}

/** ODD-TDFOLDER-001 — wire → domain projection for the
 *  materialize POST response. Mirrors the FastAPI
 *  `api/server.py::materialize_research_folder` response field-
 *  for-field: `ok`, `absolute_path`, `relative_path`,
 *  `folders_created`, `folders_existed`, `segments[]`. The server
 *  pre-splits the per-segment `segments[]` payload into a `string[]`
 *  (the FastAPI endpoint returns the sanitized list directly,
 *  NOT a list of objects like the preview endpoint does), so the
 *  projection surfaces it as `readonly segments: readonly string[]`
 *  — the renderer iterates the array verbatim, never joins
 *  paths client-side (mirrors how the preview's `relative_path`
 *  is the canonical join). `ok` is preserved verbatim; the
 *  React port does not branch on it because a non-OK would
 *  surface as HTTP non-2xx + `TaxonomyApiError`. */
export interface MaterializeResult {
  readonly ok: boolean;
  readonly absolute_path: string;
  readonly relative_path: string;
  readonly folders_created: number;
  readonly folders_existed: number;
  readonly segments: readonly string[];
}

/** Top-level materialize validator. Every required field must be
 *  present with the right type. `ok` MUST be a boolean;
 *  `folders_created` + `folders_existed` are non-negative integers
 *  (the server counts via `mkdir(parents=True, exist_ok=True)` +
 *  a `not d.exists()` pre-check); `absolute_path` + `relative_path`
 *  are non-empty strings (the server `.resolve()`s the target);
 *  `segments` is a non-empty array of non-empty strings (the
 *  FastAPI endpoint returns the sanitized ancestor chain + the
 *  taxon's own scientific_name). Any wire mismatch surfaces as
 *  `TaxonomyApiError` so a per-field shape drift cannot slip
 *  past the projection layer. */
function isValidMaterializeResult(value: unknown): value is MaterializeResult {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  if (
    typeof v.ok !== "boolean" ||
    typeof v.absolute_path !== "string" || v.absolute_path.length === 0 ||
    typeof v.relative_path !== "string" || v.relative_path.length === 0 ||
    typeof v.folders_created !== "number" ||
    !Number.isInteger(v.folders_created) || v.folders_created < 0 ||
    typeof v.folders_existed !== "number" ||
    !Number.isInteger(v.folders_existed) || v.folders_existed < 0
  ) return false;
  if (!Array.isArray(v.segments) || v.segments.length === 0) return false;
  for (const seg of v.segments) {
    if (typeof seg !== "string" || seg.length === 0) return false;
  }
  return true;
}

/** ODD-TDFOLDER-001 — public options surface for
 *  `materializeResearch`. Mirrors `FetchMaterializePreviewOptions`
 *  (the same source-aware forwarding contract). The endpoint is
 *  side-effecting (it creates folders under `RESEARCH_DIR`); the
 *  helper uses POST explicitly so the server's `mkdir` is
 *  advertised as a state change, not a read. */
export interface FetchMaterializeOptions extends FetchOptions {
  source?: TaxonomySource;
}

/** ODD-TDFOLDER-001 — POST the materialize request to create the
 *  root→taxon folder structure under `RESEARCH_DIR`. The endpoint
 *  is idempotent (`mkdir(parents=True, exist_ok=True)`); the
 *  React port treats a successful response as "folders were
 *  ensured on disk" without a follow-up GET. The wire response
 *  carries `folders_created` + `folders_existed` counts so the
 *  renderer can show "Created N / already existed M" inline copy
 *  without client-side counting. The method is forwarded as
 *  `POST` verbatim (mirrors the legacy
 *  `web/api.js::materializeResearch` `method: "POST"`); the
 *  React port does not retry on failure — the user must click
 *  the in-tab confirm button again. */
export async function materializeResearch(
  id: number,
  opts: FetchMaterializeOptions = {},
): Promise<MaterializeResult> {
  if (!Number.isInteger(id) || id < 0) {
    throw new TaxonomyApiError(
      `materializeResearch: id must be a non-negative integer; got ${id}`,
    );
  }
  const f = opts.fetch ?? defaultFetch();
  const q = sourceQuery(opts.source);
  const r = await f(url(opts.baseUrl ?? "", `/api/taxon/${id}/materialize${q}`), {
    method: "POST",
  });
  if (!r.ok) {
    throw new TaxonomyApiError(
      `taxonomy API POST /api/taxon/${id}/materialize failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  const payload = await readJson(r);
  if (!isValidMaterializeResult(payload)) {
    throw new TaxonomyApiError(
      `taxonomy API POST /api/taxon/${id}/materialize returned an invalid MaterializeResult: domain contract violated`,
    );
  }
  return payload;
}

/** ODD-TDFOLDER-001 — wire → domain projection for the
 *  open-folder POST response. Mirrors the FastAPI
 *  `api/server.py::open_research_folder` response field-for-
 *  field: `ok`, `absolute_path`, `relative_path`, `opened_with`.
 *  `opened_with` is the OS-binary name the server actually
 *  invoked (`"open"` on macOS, `"xdg-open"` on Linux,
 *  `"explorer"` on Windows — `api/server.py::_os_open_folder`
 *  returns the chosen binary verbatim). The React port surfaces
 *  it on the projection so a future server-composed affordance
 *  ("Opened with `open`" inline copy) can land without a
 *  coordinated client update. The `ok` field is preserved
 *  verbatim; the React port does not branch on it because a
 *  non-OK would surface as HTTP non-2xx + `TaxonomyApiError`. */
export interface OpenFolderResult {
  readonly ok: boolean;
  readonly absolute_path: string;
  readonly relative_path: string;
  readonly opened_with: string;
}

/** Top-level open-folder validator. Every required field must be
 *  present with the right type. `ok` MUST be a boolean;
 *  `absolute_path` + `relative_path` are non-empty strings (the
 *  server `.resolve()`s the target); `opened_with` is a non-empty
 *  string (the server returns `"open"` / `"xdg-open"` /
 *  `"explorer"` verbatim, so a wire `""` would be rejected here
 *  to keep the projection canonical). Any wire mismatch surfaces
 *  as `TaxonomyApiError` so a per-field shape drift cannot slip
 *  past the projection layer. */
function isValidOpenFolderResult(value: unknown): value is OpenFolderResult {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.ok === "boolean" &&
    typeof v.absolute_path === "string" && v.absolute_path.length > 0 &&
    typeof v.relative_path === "string" && v.relative_path.length > 0 &&
    typeof v.opened_with === "string" && v.opened_with.length > 0
  );
}

/** ODD-TDFOLDER-001 — public options surface for `openFolder`.
 *  Mirrors `FetchMaterializeOptions` (the same source-aware
 *  forwarding contract — the opened path differs across sources
 *  because the segment walk picks the right parent column). The
 *  endpoint is side-effecting (it `subprocess.Popen`s the OS
 *  file-manager binary); the helper uses POST explicitly so the
 *  spawn is advertised as a state change, not a read. */
export interface FetchOpenFolderOptions extends FetchOptions {
  source?: TaxonomySource;
}

/** ODD-TDFOLDER-001 — POST the open-folder request to launch the
 *  OS file manager (`open` / `xdg-open` / `explorer`) pointed at
 *  the materialized Research folder. The server spawns the
 *  subprocess detached from the API process
 *  (`api/server.py::_os_open_folder::start_new_session=True`)
 *  so closing the API does not close the file manager. The wire
 *  response carries `absolute_path` + `relative_path` + the
 *  `opened_with` binary name so the React port can render inline
 *  "Opened with `open`: <relative_path>" copy without a second
 *  round trip. A 404 surfaces as `TaxonomyApiError` so the
 *  FolderTab renderer shows the inline error copy + a Retry
 *  button (re-clicking triggers a fresh preview fetch first to
 *  guard against a stale all_exist=true preview). */
export async function openFolder(
  id: number,
  opts: FetchOpenFolderOptions = {},
): Promise<OpenFolderResult> {
  if (!Number.isInteger(id) || id < 0) {
    throw new TaxonomyApiError(
      `openFolder: id must be a non-negative integer; got ${id}`,
    );
  }
  const f = opts.fetch ?? defaultFetch();
  const q = sourceQuery(opts.source);
  const r = await f(url(opts.baseUrl ?? "", `/api/taxon/${id}/open-folder${q}`), {
    method: "POST",
  });
  if (!r.ok) {
    throw new TaxonomyApiError(
      `taxonomy API POST /api/taxon/${id}/open-folder failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  const payload = await readJson(r);
  if (!isValidOpenFolderResult(payload)) {
    throw new TaxonomyApiError(
      `taxonomy API POST /api/taxon/${id}/open-folder returned an invalid OpenFolderResult: domain contract violated`,
    );
  }
  return payload;
}
