// Typed fetch + CDN-loader surface for the research module (5b.1).
// CDN pins lifted verbatim from web/file_viewer.js.

import { isValidFilesEnvelope, type FilesEnvelope } from "../domain/research-file";

export class NetworkError extends Error {
  readonly status: number | null;
  readonly cause: unknown;
  constructor(msg: string, status: number | null = null, cause: unknown = null) {
    super(msg);
    this.name = "NetworkError";
    this.status = status;
    this.cause = cause;
  }
}

export type FetchLike = (
  input: string,
  init?: { method?: string; headers?: Record<string, string> },
) => Promise<{ ok: boolean; status: number; json(): Promise<unknown> }>;

export function defaultFetch(): FetchLike {
  const f = (globalThis as { fetch?: FetchLike }).fetch;
  if (!f) throw new NetworkError("global fetch is not available");
  return f;
}

/** GET `${baseUrl}/api/taxon/${taxonId}/files`. Returns the typed
 *  envelope `{exists, taxon_id, taxon_name, taxon_path,
 *  filesystem_path, subpath, root: WireFileNode | null}`. */
export async function fetchFiles(
  baseUrl: string, taxonId: number,
  fetchFn: FetchLike = defaultFetch(),
): Promise<FilesEnvelope> {
  const url = `${baseUrl}/api/taxon/${taxonId}/files`;
  let res: Awaited<ReturnType<FetchLike>>;
  try {
    res = await fetchFn(url, { method: "GET" });
  } catch (cause) {
    throw new NetworkError(`fetchFiles failed: ${url}`, null, cause);
  }
  if (!res.ok) throw new NetworkError(
    `non-2xx response (${res.status}) for ${url}`, res.status);
  const body = await res.json().catch((cause: unknown) => {
    throw new NetworkError(`invalid JSON body for ${url}`, res.status, cause);
  });
  if (!isValidFilesEnvelope(body)) {
    throw new NetworkError(`malformed response body for ${url}`);
  }
  return body;
}

/** Build `${baseUrl}/api/taxon/${taxonId}/files/serve?path=<encoded>`. */
export function fetchServe(baseUrl: string, taxonId: number, path: string): string {
  return `${baseUrl}/api/taxon/${taxonId}/files/serve?path=${encodeURIComponent(path)}`;
}

// CDN pins. DO NOT unpin — byte contract with web/file_viewer.js.
export const CDN_URLS = {
  mammoth: "https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js",
  XLSX:    "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js",
  ePub:    "https://cdn.jsdelivr.net/npm/epubjs@0.3.93/dist/epub.min.js",
  Papa:    "https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js",
} as const;
export const CDN_LIBRARIES: readonly string[] = [
  "mammoth", "XLSX", "ePub", "Papa",
];
const _scriptPromises = new Map<string, Promise<void>>();
const _loadedScripts = new Set<string>();

/** Mirrors legacy `web/file_viewer.js::loadScriptOnce`. The optional
 *  `src` override lets tests / callers bypass the CDN pin (e.g. for a
 *  local mirror or a test fixture) without mutating `CDN_URLS`. */
export function loadScriptOnce(name: string, src?: string): Promise<void> {
  if (_loadedScripts.has(name)) return Promise.resolve();
  const cached = _scriptPromises.get(name);
  if (cached) return cached;
  const pinned = (CDN_URLS as Record<string, string | undefined>)[name] ?? "";
  const finalSrc = src ?? pinned;
  const p = new Promise<void>((resolve, reject) => {
    const win = (globalThis as { window?: Window }).window
                ?? (globalThis as unknown as Window);
    const doc = win.document;
    if (!doc) { reject(new NetworkError(
      "loadScriptOnce: no document head available in this runtime")); return; }
    const s = doc.createElement("script") as HTMLScriptElement;
    s.src = finalSrc; s.defer = true;
    s.onload = () => { _loadedScripts.add(name); resolve(); };
    s.onerror = () => {
      _scriptPromises.delete(name);
      reject(new NetworkError(`Failed to load ${finalSrc}`));
    };
    doc.head?.appendChild(s);
  });
  _scriptPromises.set(name, p);
  return p;
}