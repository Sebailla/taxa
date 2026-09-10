// Typed fetch surface for the taxonomy module (PR 5a.1).
//
// Every call takes `baseUrl` explicitly so the API layer stays
// framework-free: no globals, no implicit `fetch`, no React, no DOM.
// Callers (the application layer in 5a.1, the React hook in 5a.2) own
// the runtime `fetch` injection. Failures raise `NetworkError` so
// the consumer can distinguish transport failures from validation
// errors.

import type { TaxonRecord, TreeSource } from "../domain/taxon";

/** Raised when the typed fetch layer cannot complete a request. The
 *  HTTP status (when available) and the original cause ride along so
 *  callers can decide between retry, fallback, or surfaced toast. */
export class NetworkError extends Error {
  readonly status: number | null;
  readonly cause: unknown;
  constructor(message: string, status: number | null = null, cause: unknown = null) {
    super(message);
    this.name = "NetworkError";
    this.status = status;
    this.cause = cause;
  }
}

/** Resolved `fetch` shape — overridable for tests and SSR shims. */
export type FetchLike = (
  input: string,
  init?: { method?: string; headers?: Record<string, string> },
) => Promise<{ ok: boolean; status: number; json(): Promise<unknown> }>;

/** `globalThis.fetch` cast to `FetchLike`; throws if the runtime does
 *  not expose a fetch implementation. The application layer is
 *  expected to inject a real `FetchLike` for SSR + tests. */
export function defaultFetch(): FetchLike {
  const f = (globalThis as { fetch?: FetchLike }).fetch;
  if (!f) {
    throw new NetworkError("global fetch is not available in this runtime");
  }
  return f;
}

async function requestJson(
  fetchFn: FetchLike,
  url: string,
): Promise<unknown> {
  let response: Awaited<ReturnType<FetchLike>>;
  try {
    response = await fetchFn(url, { method: "GET" });
  } catch (cause) {
    throw new NetworkError(`request failed: ${url}`, null, cause);
  }
  if (!response.ok) {
    throw new NetworkError(
      `non-2xx response (${response.status}) for ${url}`,
      response.status,
    );
  }
  try {
    return await response.json();
  } catch (cause) {
    throw new NetworkError(`invalid JSON body for ${url}`, response.status, cause);
  }
}

/** Fetch a single taxon by id. Throws `NetworkError` on transport or
 *  non-2xx response. Returns a typed `TaxonRecord`. */
export async function fetchTaxon(
  baseUrl: string,
  id: number,
  fetchFn: FetchLike = defaultFetch(),
): Promise<TaxonRecord> {
  const body = await requestJson(fetchFn, `${baseUrl}/api/taxon/${id}`);
  if (!isTaxonRecord(body)) {
    throw new NetworkError(`malformed taxon body for id=${id}`);
  }
  return body;
}

/** Fetch every direct child of `parentId` in the given `source`.
 *  Throws `NetworkError` on transport or non-2xx response. */
export async function fetchChildren(
  baseUrl: string,
  parentId: number,
  source: TreeSource,
  fetchFn: FetchLike = defaultFetch(),
): Promise<readonly TaxonRecord[]> {
  const body = await requestJson(
    fetchFn,
    `${baseUrl}/api/taxon/${parentId}/children?source=${source}`,
  );
  if (!Array.isArray(body) || !body.every(isTaxonRecord)) {
    throw new NetworkError(
      `malformed children body for parentId=${parentId}, source=${source}`,
    );
  }
  return body;
}

/** Fetch the root "domains" — the small set of top-level taxa the
 *  legacy API exposes to bootstrap the tree view. Returns the typed
 *  id+name shape (no full record body — the caller re-issues
 *  `fetchTaxon` for any node it actually wants to render). */
export async function fetchDomains(
  baseUrl: string,
  fetchFn: FetchLike = defaultFetch(),
): Promise<readonly { readonly id: number; readonly name: string }[]> {
  const body = await requestJson(fetchFn, `${baseUrl}/api/taxonomy/domains`);
  if (!Array.isArray(body)) {
    throw new NetworkError("malformed domains body");
  }
  const out: { readonly id: number; readonly name: string }[] = [];
  for (const entry of body) {
    if (
      !entry || typeof entry !== "object" ||
      typeof (entry as { id?: unknown }).id !== "number" ||
      typeof (entry as { name?: unknown }).name !== "string"
    ) {
      throw new NetworkError("malformed domain entry");
    }
    out.push({ id: (entry as { id: number }).id, name: (entry as { name: string }).name });
  }
  return out;
}

/** Shape check used by the typed fetch functions above. Mirrors the
 *  domain `TaxonRecord` contract without importing the full predicate
 *  set — keep this layer dependency-free of the application surface. */
function isTaxonRecord(value: unknown): value is TaxonRecord {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === "number" &&
    typeof v.scientific_name === "string" &&
    typeof v.parent_id === "number" || v.parent_id === null
  ) && (
    typeof v.worms_parent_id === "number" || v.worms_parent_id === null
  ) && (
    typeof v.freshwater_parent_id === "number" || v.freshwater_parent_id === null
  );
}