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
