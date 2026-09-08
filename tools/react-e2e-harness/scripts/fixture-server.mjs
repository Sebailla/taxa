#!/usr/bin/env node
// tools/react-e2e-harness/scripts/fixture-server.mjs — PR 5c.2-B.1b-ii-a.
//
// Hermetic in-process Node fixture API for the isolated React FileExplorer
// harness. Mirrors the production FastAPI shape for the two FileExplorer
// endpoints so the React viewer renders identically against the fixture or
// `make api`. Pure Node built-ins only (node:http / node:buffer); zero npm
// deps; caller-chosen or OS-assigned port (never 8765); only synthetic
// taxon id 1 served; unknown routes / unknown taxon / traversal / URL-
// encoded traversal all rejected fail-closed. Importable by the composition
// slice (5c.2-B.1b-ii-b) AND runnable as a CLI for the hermetic test slice.

import { createServer } from "node:http";
import { Buffer } from "node:buffer";

export const FIXTURE_SCHEMA = "taxa.react-e2e-fixture/1";
export const HARNESS_TAXON_ID = 1;
export const HARNESS_TAXON_NAME = "Taxa Harness Fixture";
export const HARNESS_TAXON_PATH = "Fixture";
export const FIXTURE_FS_ROOT = "/fixture/taxon-1";

// Mirror api/server.py::_CONTENT_TYPE_BY_EXT.
const CONTENT_TYPE_BY_EXT = Object.freeze({
  pdf: "application/pdf", epub: "application/epub+zip",
  html: "text/html", htm: "text/html",
  md: "text/markdown", txt: "text/plain",
  doc: "application/msword",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  xls: "application/vnd.ms-excel",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
});
export { CONTENT_TYPE_BY_EXT };

// Deterministic in-memory fixture corpus. Path is "/" separated; folder
// shape is derived from the file list.
const FIXTURE_MODIFIED = "2026-09-09T00:00:00.000Z";
const FIXTURE_CORPUS = Object.freeze([
  Object.freeze({ path: "index.html", body: Buffer.from(
    "<!doctype html>\n<title>Fixture Index</title>\n<h1>Taxa Fixture Index</h1>\n", "utf8") }),
  Object.freeze({ path: "notes.md", body: Buffer.from(
    "# Fixture notes\n\nDeterministic Markdown fixture.\n", "utf8") }),
  Object.freeze({ path: "readme.txt", body: Buffer.from(
    "Taxa fixture README.\nDeterministic plain-text fixture.\n", "utf8") }),
  Object.freeze({ path: "paper.pdf", body: Buffer.from(
    "%PDF-1.4\n% Taxa fixture PDF — minimal valid header.\n", "binary") }),
  Object.freeze({ path: "Papers/lynx.pdf", body: Buffer.from(
    "%PDF-1.4\n% Taxa fixture PDF nested under Papers/ — recursive walk target.\n", "binary") }),
]);

function httpError(status, detail) { const e = new Error(detail); e.httpStatus = status; e.detail = detail; return e; }

// safeResolve() mirrors api/server.py::_safe_resolve(): reject empty /
// NUL / malformed-percent / absolute / .. / .; explicit segment join so
// mixed separators cannot escape; strict-parent check.
function safeResolve(requested) {
  if (typeof requested !== "string" || requested.length === 0) throw httpError(400, "Path is empty");
  if (requested.includes("\0")) throw httpError(400, "Path contains NUL byte");
  let decoded;
  try { decoded = decodeURIComponent(requested); }
  catch { throw httpError(400, "Path has malformed URL encoding"); }
  if (decoded.length === 0) throw httpError(400, "Path is empty");
  if (decoded.startsWith("/") || /^[a-zA-Z]:[\\/]/.test(decoded)) throw httpError(400, "Path escapes research root");
  const segments = decoded.split(/[\\/]+/).filter((s) => s.length > 0);
  if (segments.some((s) => s === ".." || s === ".")) throw httpError(400, "Path escapes research root");
  const candidate = (FIXTURE_FS_ROOT + "/" + segments.join("/")).replace(/\\/g, "/");
  const prefix = FIXTURE_FS_ROOT + "/";
  if (!(candidate === FIXTURE_FS_ROOT || candidate.startsWith(prefix))) throw httpError(400, "Path escapes research root");
  return { decoded, candidate };
}

// buildTree() mirrors api/server.py::_walk_tree: folders first, then
// files; both sorted case-insensitive by name.
function buildTree() {
  const root = { type: "folder", name: HARNESS_TAXON_NAME, path: "", children: [] };
  const byPath = new Map([["", root]]);
  for (const entry of FIXTURE_CORPUS) {
    const parts = entry.path.split("/"); const fname = parts.pop();
    let acc = "", parent = root;
    for (const seg of parts) {
      acc = acc ? acc + "/" + seg : seg;
      let folder = byPath.get(acc);
      if (!folder) { folder = { type: "folder", name: seg, path: acc, children: [] }; byPath.set(acc, folder); parent.children.push(folder); }
      parent = folder;
    }
    const filePath = acc ? acc + "/" + fname : fname;
    parent.children.push({
      type: "file", name: fname, path: filePath,
      extension: fname.includes(".") ? fname.split(".").pop().toLowerCase() : "",
      size: entry.body.length, modified: FIXTURE_MODIFIED,
    });
  }
  const sortKey = (n) => [n.type === "folder" ? 0 : 1, n.name.toLowerCase()];
  const sortChildren = (node) => {
    if (node.type !== "folder") return;
    node.children.sort((a, b) => { const ka = sortKey(a), kb = sortKey(b); return ka[0] !== kb[0] ? ka[0] - kb[0] : ka[1] < kb[1] ? -1 : ka[1] > kb[1] ? 1 : 0; });
    for (const c of node.children) sortChildren(c);
  };
  sortChildren(root); return root;
}

const TREE = buildTree();
function findEntry(p) {
  // Normalize backslashes to forward slashes BEFORE the corpus lookup:
  // `safeResolve()` already joins segments with `/` (so `Papers\lynx.pdf`
  // and `Papers/lynx.pdf` produce the same `candidate`), but it returns
  // the ORIGINAL decoded string (which may still contain `\`) and the
  // corpus uses `/`-only paths. Without this normalization a perfectly
  // valid normalized fixture path like `Papers%5Clynx.pdf` would resolve
  // to `Papers\lynx.pdf` and spuriously 404.
  const normalized = p.replace(/\\/g, "/");
  for (const e of FIXTURE_CORPUS) if (e.path === normalized) return e;
  const lo = normalized.toLowerCase();
  for (const e of FIXTURE_CORPUS) if (e.path.toLowerCase() === lo) return e;
  return null;
}

function sendJson(res, status, payload, { headOnly = false } = {}) {
  const body = Buffer.from(JSON.stringify(payload), "utf8");
  res.writeHead(status, { "content-type": "application/json; charset=utf-8", "content-length": String(body.length), "cache-control": "no-store" });
  if (headOnly) { res.end(); return; }
  res.end(body);
}
function sendError(res, status, detail) { sendJson(res, status, { detail }); }

function handleFilesList(res, opts = {}) {
  sendJson(res, 200, { exists: true, taxon_id: HARNESS_TAXON_ID, taxon_name: HARNESS_TAXON_NAME, taxon_path: HARNESS_TAXON_PATH, filesystem_path: FIXTURE_FS_ROOT, subpath: null, root: TREE }, opts);
}

function handleFilesServe(res, urlObj, opts = {}) {
  const requested = urlObj.searchParams.get("path");
  if (requested === null || requested === "") { sendError(res, 400, "Missing 'path' query parameter"); return; }
  let resolved; try { resolved = safeResolve(requested); }
  catch (err) { sendError(res, err.httpStatus || 400, err.detail || "Invalid path"); return; }
  const entry = findEntry(resolved.decoded);
  if (!entry) { sendError(res, 404, "File not found"); return; }
  const basename = entry.path.split("/").pop();
  const ext = basename.includes(".") ? basename.split(".").pop().toLowerCase() : "";
  const contentType = CONTENT_TYPE_BY_EXT[ext] || "application/octet-stream";
  const charset = contentType.startsWith("text/") ? "; charset=utf-8" : "";
  // HEAD MUST mirror GET's wire headers (Content-Type, Content-Length,
  // Content-Disposition) so probes can size the body and pick a viewer
  // without consuming it — the response body itself is empty per HTTP
  // semantics. `opts.headOnly` is set by `handleRequest()` when method=HEAD.
  res.writeHead(200, { "content-type": contentType + charset, "content-length": String(entry.body.length), "content-disposition": `inline; filename="${basename}"`, "cache-control": "no-store" });
  if (opts.headOnly) { res.end(); return; }
  res.end(entry.body);
}

function handleRequest(req, res) {
  let urlObj;
  try { urlObj = new URL(req.url, "http://127.0.0.1"); }
  catch { sendError(res, 400, "Malformed URL"); return; }
  const pathname = urlObj.pathname.replace(/\/+$/, "") || "/";
  // /files/serve MUST be matched BEFORE /files (longer prefix wins).
  const serveMatch = /^\/api\/taxon\/(\d+)\/files\/serve$/.exec(pathname);
  if (serveMatch) {
    if (serveMatch[1] !== String(HARNESS_TAXON_ID)) { sendError(res, 404, `taxon ${serveMatch[1]} not found`); return; }
    if (req.method !== "GET" && req.method !== "HEAD") { res.writeHead(405, { "allow": "GET, HEAD" }); res.end(); return; }
    // HEAD runs the SAME handler as GET (with headOnly=true) so it
    // computes the same Content-Type / Content-Length / Content-Disposition
    // as GET would, just without writing the body. Going through the full
    // handler also makes HEAD respect safeResolve / findEntry (so a HEAD
    // on a traversal path still 400s and a HEAD on a missing file still
    // 404s — mirroring GET's wire contract exactly).
    if (req.method === "HEAD") { handleFilesServe(res, urlObj, { headOnly: true }); return; }
    handleFilesServe(res, urlObj); return;
  }
  const treeMatch = /^\/api\/taxon\/(\d+)\/files$/.exec(pathname);
  if (treeMatch) {
    if (treeMatch[1] !== String(HARNESS_TAXON_ID)) { sendError(res, 404, `taxon ${treeMatch[1]} not found`); return; }
    if (req.method !== "GET" && req.method !== "HEAD") { res.writeHead(405, { "allow": "GET, HEAD" }); res.end(); return; }
    if (req.method === "HEAD") { handleFilesList(res, { headOnly: true }); return; }
    handleFilesList(res); return;
  }
  sendError(res, 404, "Not found");
}

// Public lifecycle (importable surface for the composition slice).
export async function startServer({ port = 0, host = "127.0.0.1" } = {}) {
  const server = createServer(handleRequest);
  await new Promise((resolve, reject) => {
    const onError = (err) => { server.removeListener("listening", onListening); reject(err); };
    const onListening = () => { server.removeListener("error", onError); resolve(); };
    server.once("error", onError);
    server.once("listening", onListening);
    server.listen(port, host);
  });
  const addr = server.address();
  const actualPort = typeof addr === "object" && addr ? addr.port : port;
  return {
    schema: FIXTURE_SCHEMA, taxonId: HARNESS_TAXON_ID, host,
    port: actualPort, baseUrl: `http://${host}:${actualPort}`, server,
    async close() { await new Promise((resolve) => server.close(() => resolve())); },
  };
}
export async function stopServer(handle) { if (handle && typeof handle.close === "function") await handle.close(); }

// CLI entry: `node fixture-server.mjs [--port N] [--host HOST]`.
function parseCliArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === "--port") { const n = Number(argv[++i]); if (!Number.isFinite(n) || n < 0 || n > 65535) throw new Error(`--port must be 0..65535 (got ${JSON.stringify(argv[i])})`); args.port = n; }
    else if (k === "--host") args.host = argv[++i];
    else if (k === "--help" || k === "-h") { console.log("Usage: fixture-server.mjs [--port N] [--host HOST]"); process.exit(0); }
    else throw new Error(`unknown argument: ${k}`);
  }
  return args;
}

async function main() {
  const args = parseCliArgs(process.argv.slice(2));
  const port = Number.isFinite(args.port) ? args.port : 0;
  const host = typeof args.host === "string" && args.host.length > 0 ? args.host : "127.0.0.1";
  const handle = await startServer({ port, host });
  process.stdout.write(`fixture-server:ready schema=${FIXTURE_SCHEMA} port=${handle.port} baseUrl=${handle.baseUrl}\n`);
  let shuttingDown = false;
  const shutdown = async (sig) => {
    if (shuttingDown) return; shuttingDown = true;
    try { await handle.close(); } catch { /* ignore */ }
    process.stdout.write(`fixture-server:stopped signal=${sig}\n`); process.exit(0);
  };
  process.once("SIGINT", () => shutdown("SIGINT"));
  process.once("SIGTERM", () => shutdown("SIGTERM"));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => { console.error(`[fixture-server.mjs] FAIL: ${err && err.message ? err.message : String(err)}`); process.exit(1); });
}
