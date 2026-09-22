// Research infrastructure — typed adapter for FastAPI's research
// endpoints. spec.md rule 4: infrastructure → domain (inward). The
// barrel re-exports `fetchFiles`, `fetchFileServe`, and
// `ExplorerApiError`. The wire projection preserves every legacy
// tree field exposed by `api/server.py::_walk_tree` (folder →
// `{name, path, type, children}`; file → `{name, path, type,
// extension, size, modified}`) verbatim; FastAPI nullability
// preserved (a wire `null` projects as `null` — never coerced).
//
// ODD-MIGRATE-002 W3 contract (verbatim from the work-unit file):
//
//   "Ship the Research infrastructure adapter that satisfies
//    `ExplorerRepository` structurally via TypeScript's function
//    subtyping (the wider signatures with transport-level fetch /
//    baseUrl are silently dropped on the narrower port signature,
//    same as the merged taxonomy adapter satisfies
//    `TaxonomyRepository`). Provide `fetchFiles` (GET /api/files
//    → ExplorerTree) and `fetchFileServe` (GET /api/files/serve
//    → typed bytes + Content-Type + filename), both with an
//    injectable fetch + baseUrl. Add a named `ExplorerApiError`,
//    validated wire projection, encoded path query, typed file
//    bytes, verbatim Content-Type, parsed filename, and clear
//    HTTP / malformed-response errors. Update the Research public
//    barrel. Add focused hermetic pytest contract tests with
//    injected fetch + strict isolated TypeScript/Node harness."
//
// The adapter's wider signatures — `fetchFiles(opts?: FetchOptions)`
// and `fetchFileServe(request, opts?: FetchOptions)` — are
// structurally assignable to the narrower port signatures
// (`fetchFiles(): Promise<ExplorerTree>` and
// `fetchFileServe(request): Promise<ExplorerFileServeResult>`) via
// TypeScript's function-subtyping contract: an extra optional
// parameter is allowed because callers of the port will simply
// omit it (mirrors the merged taxonomy adapter pattern — see
// `tests/test_taxonomy_infra.py::_run_tsc_isolated` + the runtime
// port-compat mirror). The W3 compile-time port-compat fixture
// (`tests/test_research_infra.py::_PORT_COMPAT_FIXTURE`) and the
// runtime mirror in `_RUNTIME_HARNESS` pin this contract end-to-end
// — a future PR that widens the port signature without widening
// the adapter (or vice versa) trips the focused compile gate
// before runtime, then trips the runtime harness on the next
// assertion.
//
// The transport options mirror the taxonomy infra contract
// (`FetchOptions` carries optional `fetch` + `baseUrl`). The
// default `fetch` resolves through `globalThis.fetch` (the
// standard WHATWG fetch on Node 18+ and every modern browser);
// falling back to `globalThis.fetch` keeps the W3 helper ergonomic
// for the future W6 React mount without forcing every caller to
// thread a fetch reference through the DI container. A future
// cross-origin / cookie-aware deployment can swap in a custom
// fetch through `opts.fetch` without a coordinated adapter
// change.
//
// All FastAPI safety contracts land on the W3 adapter unchanged —
// the server is the source of truth for path-traversal rejection
// (400), missing research root (404), missing file (404), and
// oversized file (413). The adapter surfaces every server-side
// failure as a typed `ExplorerApiError` with the HTTP status
// preserved on `error.status`, so the future W4 renderer can
// branch on a single `instanceof` check without losing the
// diagnostic context the server composed.

import type {
  ExplorerTree,
  ExplorerTreeNode,
  ExplorerFolderNode,
  ExplorerFileNode,
} from "../domain/explorer";
import type {
  ExplorerFileServeRequest,
  ExplorerFileServeResult,
} from "../application/ports";

// Loose fetch shape — covers the real WHATWG `fetch` AND every
// stub used by the hermetic test harness. The adapter only
// relies on the fields below; everything else on the real
// `Response` is ignored. Keeping the type local (not exported)
// avoids leaking the loose shape into the public barrel — the
// canonical `Response` type is implicit on the real fetch.
type FetchLike = (
  input: string,
  init?: { method?: string },
) => Promise<{
  ok: boolean;
  status: number;
  statusText: string;
  headers: { get(name: string): string | null };
  json: () => Promise<unknown>;
  arrayBuffer: () => Promise<ArrayBuffer>;
}>;

/** Public transport options — mirrors the `FetchOptions` shape
 *  used by `src/modules/taxonomy/infrastructure/api.ts` so the
 *  React port drives both adapters through a uniform DI surface.
 *  `fetch` lets the W4 renderer (and the hermetic test harness)
 *  inject a stubbed fetch; `baseUrl` lets the same adapter reach
 *  the FastAPI server from a non-root origin (e.g. a Next.js
 *  static export served under `/explorer/` while the API lives
 *  at `/api/`). Omitting both options resolves `fetch` through
 *  `globalThis.fetch` and `baseUrl` to `""` (relative origin). */
export interface FetchOptions {
  fetch?: FetchLike;
  baseUrl?: string;
}

/** Named adapter error. Mirrors `TaxonomyApiError` shape
 *  (`src/modules/taxonomy/infrastructure/api.ts`): the constructor
 *  accepts an optional `{ status, cause }` so HTTP failures
 *  preserve the server's status code (renderers can branch on
 *  `err.status === 404` for "missing folder" without parsing
 *  the message string) and so the original fetch failure (e.g.
 *  a `SyntaxError` from `response.json()`) is reachable through
 *  `err.cause` for diagnostic logging. The class is `extends
 *  Error` so `instanceof Error` narrows correctly under React's
 *  error boundaries. A future extension could carry a `code`
 *  discriminator (e.g. "missing-root", "path-escape",
 *  "oversized-file") if the W4 renderer needs to branch on the
 *  specific server-side contract; today the typed `status`
 *  covers every error path the FastAPI server emits. */
export class ExplorerApiError extends Error {
  readonly status: number | null;
  readonly cause: unknown;
  constructor(
    message: string,
    opts: { status?: number | null; cause?: unknown } = {},
  ) {
    super(message);
    this.name = "ExplorerApiError";
    this.status = opts.status ?? null;
    this.cause = opts.cause;
  }
}

/** Default fetch resolver — reads `globalThis.fetch` (the
 *  standard WHATWG fetch on Node 18+ and every modern browser).
 *  Throws `ExplorerApiError` (NOT a raw `TypeError`) when no
 *  fetch implementation is available so the future W4 renderer
 *  sees the same typed error shape regardless of whether the
 *  failure was a transport problem or a missing-runtime
 *  problem. The error carries `status: null` because no HTTP
 *  round trip happened. Mirrors the taxonomy adapter's
 *  `defaultFetch` helper byte-for-byte so the React port can
 *  share one DI configuration across both adapters. */
function defaultFetch(): FetchLike {
  const fn = (globalThis as { fetch?: FetchLike }).fetch;
  if (!fn) {
    throw new ExplorerApiError(
      "no fetch implementation available — pass opts.fetch outside a browser/Node\u226518",
    );
  }
  return fn;
}

/** Compose a URL by joining `baseUrl` and `path`. Mirrors the
 *  taxonomy helper byte-for-byte so the React port sees the
 *  same URL-construction convention across adapters. The
 *  trailing-slash trim keeps the join idempotent when the
 *  caller passes a baseUrl with a trailing slash (e.g. a
 *  reverse-proxy mount like `https://api.example.com/`). The
 *  `path` argument is assumed to begin with `/` (the FastAPI
 *  routes are absolute under the API origin); the helper does
 *  NOT normalize the path itself — caller-supplied query strings
 *  (`/api/files/serve?path=…`) pass through unchanged.
 *
 *  ODD-MIGRATE-006 carveout (API origin default) — symmetric
 *  with the taxonomy infra helper (PR #378): the static export
 *  at `out/` ships WITHOUT a `.env` file, so the React build's
 *  `process.env.NEXT_PUBLIC_TAXA_API_ORIGIN` resolves to
 *  `undefined` and the consumer's `?? "/api"` fallback can hand
 *  us the literal `"/api"` baseUrl. The path itself already
 *  starts with `/api/...` (the FastAPI endpoint shape), so the
 *  legacy concat-style helper would otherwise duplicate the
 *  leading `/api` segment (`"/api"` + `"/api/files"` =
 *  `"/api/api/files"`, which 404s against FastAPI's
 *  `/api/files` route). The adapter therefore absorbs BOTH the
 *  empty-string edge case AND the literal `"/api"` baseUrl as
 *  equivalent relative-baseUrl indicators — when `baseUrl` is
 *  either `""` (the legacy env-var fallback) or `"/api"` (the
 *  post-f708a15 fallback), the helper returns the path as-is
 *  so the resulting URL stays `/api/files` instead of
 *  `/api/api/files`. Any other non-empty baseUrl (e.g.
 *  `http://127.0.0.1:8765`) keeps the existing concat +
 *  trailing-slash trim behaviour. Both literals are pinned as
 *  a single intentional behaviour by the
 *  `test_infra_file_url_builder_absorbs_relative_baseurl_literals`
 *  test, so a future PR that bumps either literal must update
 *  the test alongside the helper. */
function url(baseUrl: string, path: string): string {
  if (baseUrl === "" || baseUrl === "/api") return path;
  return baseUrl.replace(/\/+$/, "") + path;
}

/** Read a JSON body. Wraps the underlying `response.json()` in
 *  `ExplorerApiError` so a syntax-error from the parser surfaces
 *  as the typed error shape (mirrors the taxonomy helper
 *  `readJson`). The original parser error is preserved on
 *  `err.cause` for diagnostic logging — the Future W4 renderer
 *  logs the raw cause verbatim, the typed `status: null`
 *  signals that no HTTP round-trip happened (vs. a 5xx which
 *  carries the real status). */
async function readJson(
  r: { json: () => Promise<unknown> },
): Promise<unknown> {
  try {
    return await r.json();
  } catch (cause) {
    throw new ExplorerApiError(
      "research API returned malformed JSON: " +
        String((cause as Error)?.message ?? cause),
      { cause },
    );
  }
}

/** Wire → domain projection for `ExplorerTree`. Mirrors the
 *  FastAPI `api/server.py::list_research_root` response
 *  field-for-field: `exists` (boolean), `root` (recursive
 *  `ExplorerTreeNode | null`), `filesystem_path` (string).
 *  The server preserves FastAPI nullability:
 *
 *    - When the research root is a directory on disk, the
 *      server returns `{ exists: true, root: <node>, filesystem_path: <abs> }`.
 *    - When the research root is missing or not a directory,
 *      the server returns 200 with
 *      `{ exists: false, root: null, filesystem_path: <abs> }` —
 *      the W4 renderer renders the empty-state from this shape
 *      (distinct from a 404 `taxon not found` path).
 *
 *  Every wire field projects verbatim — `exists` is NOT
 *  coerced to truthy/falsy; `root` is NOT synthesized when
 *  missing; `filesystem_path` is NOT coerced to a relative
 *  path. Any wire mismatch (non-object payload, missing
 *  `exists`, missing `filesystem_path`, root out-of-sync with
 *  `exists`) surfaces as `ExplorerApiError` so a per-field
 *  shape drift cannot slip past the projection layer (mirrors
 *  `fromWire` in the taxonomy adapter). */
function fromWireTree(payload: unknown, context: string): ExplorerTree {
  if (typeof payload !== "object" || payload === null) {
    throw new ExplorerApiError(
      `research API ${context} returned a non-object payload: ` +
        (payload === null ? "null" : typeof payload),
    );
  }
  const v = payload as Record<string, unknown>;
  if (typeof v.exists !== "boolean") {
    throw new ExplorerApiError(
      `research API ${context} returned an invalid ExplorerTree: domain contract violated (exists)`,
    );
  }
  if (typeof v.filesystem_path !== "string") {
    throw new ExplorerApiError(
      `research API ${context} returned an invalid ExplorerTree: domain contract violated (filesystem_path)`,
    );
  }
  // When `exists` is true, `root` MUST be a non-null object
  // (the server returns the tree inline). When `exists` is
  // false, `root` MUST be `null`. The server-side invariant
  // is enforced here as a defensive check — a wire mismatch
  // signals a server-side regression that the W4 renderer
  // cannot recover from, so we surface it as a typed error
  // rather than silently rendering the empty-state.
  if (v.exists) {
    if (v.root === null || typeof v.root !== "object") {
      throw new ExplorerApiError(
        `research API ${context} returned an invalid ExplorerTree: root must be present when exists=true`,
      );
    }
  } else {
    if (v.root !== null) {
      throw new ExplorerApiError(
        `research API ${context} returned an invalid ExplorerTree: root must be null when exists=false`,
      );
    }
  }
  return {
    exists: v.exists,
    root: v.exists ? fromWireNode(v.root, `${context}.root`) : null,
    filesystem_path: v.filesystem_path,
  };
}

/** Wire → domain projection for a single recursive
 *  `ExplorerTreeNode` (folder | file). The recursion matches
 *  the FastAPI `_walk_tree` shape exactly (the server inlines
 *  the full subtree in one response — no lazy children, no N+1
 *  round trips, per `openspec/specs/research/spec.md` "Recursive
 *  directory listing endpoint"). Folder nodes carry
 *  `{name, path, type: "folder", children: ExplorerTreeNode[]}`;
 *  file nodes carry
 *  `{name, path, type: "file", extension: string, size: number, modified: string}`.
 *  Every wire field projects verbatim (the `path` is the file's
 *  position relative to the research root — `web/file_explorer.js::serveUrl`
 *  URL-encodes this verbatim into the `/api/files/serve?path=…`
 *  request). The `extension` field is the lowercase extension
 *  without the leading dot — `FileFormat` casting lives at the
 *  W4 renderer boundary (NOT here), so the typed contract
 *  accepts any string the wire can carry (a `null` extension
 *  would surface as `null` — coercing to `"other"` would
 *  silently swallow missing fields). */
function fromWireNode(
  payload: unknown,
  context: string,
): ExplorerTreeNode {
  if (typeof payload !== "object" || payload === null) {
    throw new ExplorerApiError(
      `research API ${context} returned a non-object node: ` +
        (payload === null ? "null" : typeof payload),
    );
  }
  const v = payload as Record<string, unknown>;
  if (typeof v.name !== "string" || typeof v.path !== "string") {
    throw new ExplorerApiError(
      `research API ${context} returned an invalid ExplorerTreeNode: missing name/path`,
    );
  }
  if (v.type === "folder") {
    if (!Array.isArray(v.children)) {
      throw new ExplorerApiError(
        `research API ${context} returned an invalid ExplorerFolderNode: missing children`,
      );
    }
    const children: ExplorerTreeNode[] = [];
    for (let i = 0; i < v.children.length; i++) {
      children.push(fromWireNode(v.children[i], `${context}.children[${i}]`));
    }
    const node: ExplorerFolderNode = {
      name: v.name,
      path: v.path,
      type: "folder",
      children,
    };
    return node;
  }
  if (v.type === "file") {
    if (
      typeof v.extension !== "string" ||
      typeof v.size !== "number" ||
      !Number.isInteger(v.size) ||
      v.size < 0 ||
      typeof v.modified !== "string"
    ) {
      throw new ExplorerApiError(
        `research API ${context} returned an invalid ExplorerFileNode: missing/invalid fields`,
      );
    }
    const node: ExplorerFileNode = {
      name: v.name,
      path: v.path,
      type: "file",
      extension: v.extension,
      size: v.size,
      modified: v.modified,
    };
    return node;
  }
  throw new ExplorerApiError(
    `research API ${context} returned an invalid ExplorerTreeNode: unknown type ${String(v.type)}`,
  );
}

/** Parse the filename out of a Starlette `Content-Disposition`
 *  header. Starlette 0.41 builds the header from
 *  `format_header_param` and produces one of two shapes:
 *
 *    - `inline; filename="X"` — ASCII-safe names (the common
 *      case for Research folder basenames — taxon names are
 *      typically ASCII even when they include diacritics).
 *    - `inline; filename*=UTF-8''<percent-encoded>` — names
 *      with whitespace / unicode / quote / backslash, emitted
 *      per RFC 5987.
 *
 *  The parser tries the simple `filename="X"` form first, then
 *  falls back to the RFC 5987 form. A malformed header
 *  (neither shape present) returns `""` so the W4 renderer can
 *  decide whether to default to the request-path basename or
 *  to skip the `<a download>` attribute. The byte-identical
 *  legacy oracle `web/file_explorer.js::openInNewTab` builds
 *  the `<a download>` attribute from `file.name` (= the wire
 *  tree's `name` field) — the Content-Disposition filename is
 *  the server's source of truth for the basename AFTER
 *  `os.path.basename` resolves any trailing slashes / hidden
 *  files, which matches Starlette's emission. */
function parseContentDisposition(headerValue: string | null): string {
  if (!headerValue) return "";
  // Try the simple `filename="X"` first (the common case).
  const simple = /filename\s*=\s*"([^"]*)"/i.exec(headerValue);
  if (simple && simple[1]) return simple[1];
  // Fall back to RFC 5987 `filename*=UTF-8''<encoded>`. The
  // character-class regex tolerates both `UTF-8` and `utf-8`
  // (Starlette emits lowercase `utf-8`, but RFC 5987 specifies
  // uppercase — accepting both future-proofs against a
  // Starlette version bump that swaps casing).
  const ext = /filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]*)/i.exec(headerValue);
  if (ext && ext[1]) {
    try {
      return decodeURIComponent(ext[1]);
    } catch {
      return ext[1];
    }
  }
  return "";
}

/** Fetch the recursive file tree for the Browser tab's research
 *  root. Maps to `GET /api/files` (`api/server.py::
 *  list_research_root`). The wire payload mirrors the
 *  FastAPI response verbatim:
 *
 *    - `{ exists: true, root: <recursive tree>, filesystem_path: <abs> }`
 *      when the research root is a directory on disk.
 *    - `{ exists: false, root: null, filesystem_path: <abs> }`
 *      when the research root is missing or not a directory
 *      (the server returns 200 with this shape so the W4
 *      renderer renders the empty-state from this state —
 *      distinct from a 404 `taxon not found` path).
 *
 *  The adapter's wider signature `fetchFiles(opts?: FetchOptions)`
 *  satisfies the narrower port signature `fetchFiles(): Promise<ExplorerTree>`
 *  via TypeScript's function subtyping — the extra optional
 *  parameter is silently dropped on the narrower port
 *  signature (the same way the merged taxonomy adapter
 *  satisfies `TaxonomyRepository`).
 *
 *  HTTP non-OK surfaces as `ExplorerApiError` with the status
 *  code preserved on `err.status`. Malformed JSON, non-object
 *  payloads, and missing/invalid fields all surface as
 *  `ExplorerApiError` with `status: null` (no HTTP round trip
 *  was the failure source). */
export async function fetchFiles(
  opts: FetchOptions = {},
): Promise<ExplorerTree> {
  const f = opts.fetch ?? defaultFetch();
  const r = await f(url(opts.baseUrl ?? "", "/api/files"));
  if (!r.ok) {
    throw new ExplorerApiError(
      `research API GET /api/files failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  return fromWireTree(await readJson(r), "/api/files");
}

/** Serve a single file from the research root. Maps to
 *  `GET /api/files/serve?path=<encoded>` (`api/server.py::
 *  serve_research_file`). The server enforces the safety
 *  contract:
 *
 *    - `path` is constrained to 1..4096 chars via
 *      `Query(min_length=1, max_length=4096)` — accidental
 *      empty paths return 422 and very-long paths cannot
 *      reach the filesystem call.
 *    - `_safe_resolve()` rejects `..` traversal, absolute
 *      paths, and symlink escapes with HTTP 400 + detail
 *      `"Path escapes research root"`.
 *    - The research folder itself must exist on disk — a
 *      missing folder returns 404 + detail
 *      `"Research root not found"`.
 *    - The candidate must be a regular file (`is_file()`) —
 *      folders, devices, and broken symlinks return 404 +
 *      detail `"File not found"`.
 *    - Files larger than `_STREAM_CAP_BYTES` (100 MB) return
 *      413 with a detail naming the cap and the actual size.
 *
 *  The adapter URL-encodes the request path verbatim (mirrors
 *  `web/file_explorer.js::serveUrl(relativePath)`'s
 *  `encodeURIComponent` call). The result carries the file
 *  bytes as `Uint8Array` (canonical ES2022 byte type — same
 *  type `response.arrayBuffer()` surfaces as in both the
 *  browser and Node 18+), the verbatim `Content-Type` header
 *  value (so the server is the source of truth for the MIME
 *  — a future server change adding a new extension lands
 *  without a coordinated React update), and the parsed
 *  filename from the `Content-Disposition` header (Starlette
 *  emits `inline; filename="<basename>"` so the W4 renderer's
 *  `<a download>` attribute picks up the server-composed
 *  basename verbatim).
 *
 *  Each call returns a FRESH `Uint8Array` so the port
 *  contract stays value-typed — a renderer that mutates the
 *  bytes cannot corrupt a concurrent consumer (mirrors the
 *  W2 independence check — `tests/test_research_application.py::
 *  test_compiled_application_passes_runtime_contract` step 7).
 *
 *  The adapter's wider signature
 *  `fetchFileServe(request, opts?: FetchOptions)` satisfies
 *  the narrower port signature
 *  `fetchFileServe(request): Promise<ExplorerFileServeResult>`
 *  via TypeScript's function subtyping — the extra optional
 *  `opts` parameter is silently dropped on the narrower port
 *  signature.
 *
 *  HTTP non-OK surfaces as `ExplorerApiError` with the status
 *  code preserved on `err.status` — the W4 renderer can branch
 *  on `err.status === 404` for "missing folder" without
 *  parsing the message string. */
export async function fetchFileServe(
  request: ExplorerFileServeRequest,
  opts: FetchOptions = {},
): Promise<ExplorerFileServeResult> {
  const f = opts.fetch ?? defaultFetch();
  const query = `?path=${encodeURIComponent(request.path)}`;
  const r = await f(url(opts.baseUrl ?? "", `/api/files/serve${query}`));
  if (!r.ok) {
    throw new ExplorerApiError(
      `research API GET /api/files/serve failed: ${r.status} ${r.statusText}`,
      { status: r.status },
    );
  }
  const arrayBuffer = await r.arrayBuffer();
  const contentType = r.headers.get("content-type") ?? "";
  const filename = parseContentDisposition(
    r.headers.get("content-disposition"),
  );
  return {
    content: new Uint8Array(arrayBuffer),
    contentType,
    filename,
  };
}