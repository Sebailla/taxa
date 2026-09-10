// Taxonomy infrastructure — typed adapter for FastAPI taxon endpoints.
// spec.md rule 4: infrastructure → domain (inward). The barrel
// re-exports fetchTaxon, fetchChildren, and TaxonomyApiError. Wire
// `scientific_name` projects onto domain `name`; `isValidTaxon` rejects
// ranks outside the eight Linnaean ranks deterministically.

import { isValidTaxon } from "../domain/taxon.js";
import type { Taxon } from "../domain/taxon.js";

type FetchLike = (
  input: string,
  init?: { method?: string },
) => Promise<{ ok: boolean; status: number; statusText: string; json: () => Promise<unknown> }>;

export interface FetchOptions {
  fetch?: FetchLike;
  baseUrl?: string;
}

export interface FetchChildrenOptions extends FetchOptions {
  source?: "col" | "worms" | "freshwater";
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
  };
  if (!isValidTaxon(candidate)) {
    throw new TaxonomyApiError(
      `taxonomy API ${context} returned an invalid Taxon: domain contract violated`,
    );
  }
  return candidate;
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
  const q = opts.source ? `?source=${encodeURIComponent(opts.source)}` : "";
  const r = await f(url(opts.baseUrl ?? "", `/api/taxon/${id}/children${q}`));
  if (!r.ok) {
    throw new TaxonomyApiError(
      `taxonomy API GET /api/taxon/${id}/children failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  const payload = await readJson(r);
  if (!Array.isArray(payload)) {
    throw new TaxonomyApiError(
      `taxonomy API GET /api/taxon/${id}/children returned a non-array payload: ` + typeof payload,
    );
  }
  return payload.map((element, i) => fromWire(element, `/api/taxon/${id}/children[${i}]`));
}
