// Research application — typed ExplorerRepository port for the
// Browser-tab file-explorer data source. spec.md rule 4:
// application depends on domain ONLY; presentation depends on
// this port; infrastructure satisfies it via TypeScript
// structural subtyping. Application stays pure: no React, no
// Next, no HTTP transport, no DOM, no browser state, no process
// state.
//
// ODD-MIGRATE-002 W2 contract (verbatim from the work-unit file):
//
//   "Define the typed ExplorerRepository port that describes
//    file-tree retrieval (GET /api/files → ExplorerTree) and
//    safe file serving input/output (GET /api/files/serve →
//    typed bytes + content-type + filename). Use W1 domain
//    types. No fetch, no browser APIs, no React, no renderers,
//    no CSS, no UI, no state storage."
//
// That contract is this file's only job. W3 ships the
// infrastructure adapter that satisfies the port (via structural
// function subtyping — the adapter's wider signatures with
// transport-level fetch / baseUrl / signal are silently ignored
// when assigned to the narrower port signature, the same way the
// merged taxonomy adapter satisfies `TaxonomyRepository`); W6+
// mounts the React UI that consumes the port through DI / a
// provider. Both consumers build on this surface without
// reshaping it: dropping a field, narrowing a literal, or
// adding a framework import would silently regress every typed
// consumer, so the contract is pinned by
// `tests/test_research_application.py`.
//
// ODD-MIGRATE-002 W2 source-of-truth mapping:
//
//   Method            FastAPI oracle                              Type
//   ----------------  ------------------------------------------ ----------------
//   fetchFiles        api/server.py::list_research_root          ExplorerTree
//   fetchFileServe    api/server.py::serve_research_file         ExplorerFileServeResult
//
// The two endpoints are the Browser-tab's only data-source
// contract — `web/file_explorer.js::mount()` always fetches the
// global Research tree via `GET /api/files` (it does NOT depend
// on the selected taxon), and `web/file_explorer.js::serveUrl()`
// always builds the file-serve URL against `/api/files/serve`
// (the per-taxon endpoint stays in the API for callers that
// still need a taxon's materialised subtree). The port's two
// methods map 1:1 to those two endpoints so the React cutover
// can wire the same typed surface.

import type { ExplorerTree } from "../domain/explorer";

/** Safe file-serving request — typed input shape for
 *  `/api/files/serve?path=<rel>`. Mirrors the legacy
 *  `web/file_explorer.js::serveUrl(relativePath)` argument
 *  verbatim: `path` is the file's location RELATIVE to the
 *  global Research root (`RESEARCH_DIR`).
 *
 *  The FastAPI server enforces the safety contract
 *  (`api/server.py::serve_research_file`):
 *
 *    - `path` is constrained to 1..4096 chars via
 *      `Query(min_length=1, max_length=4096)` so accidental
 *      empty paths return 422 and very-long paths can't reach
 *      the filesystem call.
 *    - `_safe_resolve()` rejects `..` traversal, absolute paths,
 *      and symlink escapes with HTTP 400 + `detail: "Path
 *      escapes research root"`.
 *    - The research folder itself must exist on disk — a missing
 *      folder returns 404 + `detail: "Research root not found"`.
 *    - The candidate must be a regular file (`is_file()`) —
 *      folders, devices, and broken symlinks return 404 +
 *      `detail: "File not found"`.
 *    - Files larger than `_STREAM_CAP_BYTES` (100 MB) return
 *      413 with a detail naming the cap and the actual size.
 *
 *  The application port accepts any `string` here — the
 *  infrastructure adapter validates the constraint + forwards
 *  the request (so a requester passing `"../../etc/passwd"`
 *  reaches the server's safety net and surfaces as a typed
 *  error from the future adapter, never a client-side crash).
 *  A future port extension could introduce a `SafeFileServePath`
 *  brand type to push the validation upstream, but that would
 *  force every caller to construct a branded literal before the
 *  request reaches the adapter — with no real safety benefit,
 *  because the server is the source of truth for path
 *  validation and rejects every unsafe input regardless of how
 *  the client types it. The server is the safety net; the port
 *  describes the SHAPE, not the validation policy.
 *
 *  The field is `readonly` so a caller cannot mutate the
 *  request between construction and dispatch (mirrors the
 *  readonly contract on `ExplorerState.openFilePath` from W1 —
 *  `tests/test_research_domain.py::
 *  test_domain_file_explorer_state_fields_are_readonly`). A
 *  renderer that overwrites the path would break the
 *  wire-shaped contract the FastAPI server relies on for the
 *  path-traversal-safety check. */
export interface ExplorerFileServeRequest {
  readonly path: string;
}

/** Safe file-serving result — typed output shape mirroring the
 *  FastAPI `/api/files/serve` response. Every field is
 *  `readonly` so the typed contract stays immutable end-to-end
 *  (mirrors the W1 readonly contract — see the request JSDoc).
 *
 *  - `content` — the file bytes as a `Uint8Array`. `Uint8Array`
 *    is the canonical byte type in ES2022 (the same type
 *    `fetch(...).arrayBuffer()` surfaces the body as in both
 *    the browser and Node 18+). The future infrastructure
 *    adapter reads `response.arrayBuffer()` and wraps it in a
 *    `Uint8Array` before returning. Each format renderer (W4)
 *    consumes the bytes via the typed `content` field:
 *    `<iframe>`/`<embed>` for binary families (PDF / EPUB /
 *    DOC / DOCX / XLS / XLSX), `TextDecoder` for text families
 *    (HTML / TXT / MD / CSV / TSV / JSON), `<img>` for image
 *    families, `<video>` for video families.
 *  - `contentType` — the server's `Content-Type` header value,
 *    matched per the extension table in
 *    `openspec/specs/research/spec.md` §Content-Type by
 *    extension (pdf / epub / html / htm / md / txt / doc /
 *    docx / xls / xlsx / `application/octet-stream` fallback).
 *    The string stays open (not a closed union) so the server
 *    is the source of truth for the exact MIME value — a
 *    future server change adding `application/xhtml+xml` or
 *    any other MIME lands without a coordinated React update.
 *  - `filename` — the basename the server emits via
 *    `Content-Disposition: inline; filename="<basename>"`.
 *    Used by the React `<a download>` affordance and the
 *    open-in-new-tab gesture (`web/file_explorer.js::
 *    openInNewTab`).
 *
 *  The result is a fresh value per call (the port contract is
 *  value-typed — see `tests/test_research_application.py::
 *  test_compiled_application_passes_runtime_contract` step 7
 *  for the independence check). The future adapter MUST return
 *  a new `Uint8Array` per call so a renderer that mutates the
 *  bytes cannot corrupt a concurrent consumer. */
export interface ExplorerFileServeResult {
  readonly content: Uint8Array;
  readonly contentType: string;
  readonly filename: string;
}

/** Application-layer port for the Browser-tab file-explorer
 *  data source. Mirrors the FastAPI `/api/files` +
 *  `/api/files/serve` endpoints (`api/server.py::
 *  list_research_root` + `::serve_research_file`). Structurally
 *  compatible with the future infrastructure adapter (W3+):
 *  the adapter's wider signatures — transport-level `fetch`,
 *  `baseUrl`, signal, etc. — are silently ignored when assigned
 *  to the narrower port signature, the same way the merged
 *  taxonomy adapter satisfies `TaxonomyRepository`
 *  (`tests/test_taxonomy_application.py::test_compiled_*
 *  application_passes_runtime_contract`).
 *
 *  - `fetchFiles()` — `GET /api/files` → `ExplorerTree`. The
 *    Browser tab's primary data source. Returns the recursive
 *    research-root tree (`{ exists, root, filesystem_path }`)
 *    or `{ exists: false, root: null }` when the research
 *    root is missing or not a directory (the frontend renders
 *    the empty-state from this state — distinct from the 404
 *    `taxon not found` path). The parameter list is empty —
 *    the FastAPI endpoint takes no query params today, and a
 *    future server-side filter lands as a separately authorized
 *    port extension (not a silent signature change).
 *  - `fetchFileServe(request)` — `GET /api/files/serve?path=<rel>`
 *    → `ExplorerFileServeResult`. The Browser tab renders the
 *    open file via the matching renderer (W4), which fetches
 *    the bytes via this method. The single parameter is the
 *    typed `ExplorerFileServeRequest`; future transport-level
 *    options belong to the infrastructure adapter signature
 *    and are dropped on the narrower port signature via
 *    TypeScript structural function subtyping.
 *
 *  The methods are declared in the contract order `fetchFiles`
 *  then `fetchFileServe` — mirrors the FastAPI endpoint
 *  convention and the Browser-tab consumption order (the tree
 *  fetches first on mount, then the file fetches when the user
 *  opens a row). A reordering has no runtime impact (TypeScript
 *  interfaces are unordered), but the source reads top-to-
 *  bottom the same way the Browser tab consumes the endpoints,
 *  which keeps the review-facing contract consistent.
 */
export interface ExplorerRepository {
  fetchFiles(): Promise<ExplorerTree>;
  fetchFileServe(
    request: ExplorerFileServeRequest,
  ): Promise<ExplorerFileServeResult>;
}

/** Stable string identity for DI containers / diagnostic
 *  guards. Mirrors `TAXONOMY_PORT_NAME` in
 *  `src/modules/taxonomy/application/ports.ts` — the literal
 *  matches the port interface name exactly so a future PR
 *  that renames the interface trips the
 *  `tests/test_research_application.py::
 *  test_application_ports_declares_port_name_constant` guard.
 *  Consumed by DI containers (W6+) and by diagnostic log lines
 *  that attribute failures to the right port. */
export const EXPLORER_PORT_NAME = "ExplorerRepository";
