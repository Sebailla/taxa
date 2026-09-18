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
