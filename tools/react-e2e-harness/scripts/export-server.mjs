#!/usr/bin/env node
// tools/react-e2e-harness/scripts/export-server.mjs — PR 5c.2-B.1b-ii-b.
//
// Hermetic in-process Node static-export HTTP server for the isolated React
// harness. Caller-supplied absolute `--root`; `/` maps to `index.html`;
// exact files below root served with appropriate Content-Type (HTML/JS/MJS/
// CSS/JSON/images/fonts fall back to application/octet-stream); HEAD mirrors
// GET headers with no body; traversal / directory leakage / unknown paths
// fail-closed (404). Pure Node built-ins (`node:http` + `node:fs/promises`
// + `node:path` + `node:url`); zero npm deps; caller-chosen port
// (`--port N`) or OS-assigned (`--port 0`); loopback host default
// `127.0.0.1`; never hard-codes 8765 or any root-specific path. Importable
// by the composition slice via `startServer({port, host, root}) →
// {schema, root, host, port, baseUrl, server, close}` AND runnable as a
// CLI for the hermetic test slice. `--root` is mandatory AND absolute AND
// must point at an existing directory — any other shape exits non-zero
// before binding a listener (fail-closed).

import { createServer } from "node:http";
import { stat, readFile } from "node:fs/promises";
import { resolve, isAbsolute, normalize, join, sep, extname } from "node:path";

export const EXPORT_SERVER_SCHEMA = "taxa.react-e2e-export-server/1";
export const EXPORT_SERVER_DEFAULT_HOST = "127.0.0.1";

// Mirrors the static-export Content-Type conventions used by Next.js +
// the harness's own served assets. Unknown extensions fall back to
// `application/octet-stream` so the browser treats them as downloads.
const CONTENT_TYPE_BY_EXT = Object.freeze({
  ".html": "text/html; charset=utf-8",
  ".htm": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".mjs": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".svg": "image/svg+xml; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".otf": "font/otf",
});
const DEFAULT_CONTENT_TYPE = "application/octet-stream";

// safeJoin() mirrors the same defensive posture as fixture-server.mjs:
// reject traversal segments (`..` / `.`) BEFORE any join; explicit segment
// split so mixed separators cannot escape; strict-parent check after join
// so a successful decode cannot resolve outside the root via symlink-style
// tricks. Returns the absolute file path on success, or `null` on any
// traversal / decoding failure (the caller then 404s — fail-closed).
function safeJoin(rootAbs, urlPath) {
  // urlPath has already had the pathname extracted (no query/fragment).
  // Strip the leading slash (URL paths always start with `/`).
  let decoded;
  try { decoded = decodeURIComponent(urlPath); }
  catch { return null; }
  // Normalize Windows backslashes up-front so `Papers%5Cfile.html` does
  // not produce a literal `\Papers\file.html` we then miss.
  const stripped = decoded.replace(/^[/\\]+/, "").replace(/\\/g, "/");
  if (stripped.length === 0) return null;
  const segments = stripped.split("/").filter((s) => s.length > 0);
  if (segments.some((s) => s === ".." || s === ".")) return null;
  const rel = segments.join(sep);
  const candidate = normalize(join(rootAbs, rel));
  // Strict-parent check: candidate must be rootAbs itself OR start with
  // `rootAbs + sep`. The trailing sep prevents `/foo` from passing when
  // root is `/foobar`.
  const rootWithSep = rootAbs.endsWith(sep) ? rootAbs : rootAbs + sep;
  if (candidate !== rootAbs && !candidate.startsWith(rootWithSep)) return null;
  return candidate;
}

// contentTypeFor() maps a file's extension to the matching Content-Type.
// Unknown extensions (e.g. `.bin`) fall back to `application/octet-stream`
// so the browser treats them as binary downloads.
function contentTypeFor(filePath) {
  const ext = extname(filePath).toLowerCase();
  return CONTENT_TYPE_BY_EXT[ext] || DEFAULT_CONTENT_TYPE;
}

// async resolveServeTarget() translates an HTTP request URL to an
// existing regular file on disk under `rootAbs`. Returns
// `{absPath, size}` on success or `null` for any rejection (no file, no
// traversal, directory not served, unknown route). NEVER throws.
async function resolveServeTarget(rootAbs, urlPath) {
  // `/` (and empty path) maps to `index.html` inside the root — the
  // harness browser loads the React app at the origin root.
  let candidate;
  if (urlPath === "/" || urlPath === "") {
    candidate = join(rootAbs, "index.html");
  } else {
    const joined = safeJoin(rootAbs, urlPath);
    if (joined === null) return null;
    candidate = joined;
  }
  let st;
  try { st = await stat(candidate); }
  catch { return null; }
  // Fail-closed on directory leakage: we MUST NOT serve directory
  // listings, and we MUST NOT auto-append `index.html` to directory
  // requests (that's what explicit `/` → `index.html` is for).
  if (!st.isFile()) return null;
  return { absPath: candidate, size: st.size };
}

function sendBuffer(res, status, body, extraHeaders) {
  const headers = {
    "content-type": "text/plain; charset=utf-8",
    "content-length": String(body.length),
    "cache-control": "no-store",
    ...(extraHeaders || {}),
  };
  res.writeHead(status, headers);
  res.end(body);
}

function sendError(res, status, detail) {
  const body = Buffer.from(detail, "utf8");
  sendBuffer(res, status, body, { "content-type": "text/plain; charset=utf-8" });
}

async function handleRequest(req, res, ctx) {
  // Parse the request URL MANUALLY (no `new URL()`) because the WHATWG URL
  // parser normalizes `..` segments, which would silently turn `GET /..` into
  // `GET /` and let the client escape via that route. We want the raw
  // path including any `..` / `.` segments so `safeJoin` can fail-closed
  // on them. Strip query (`?…`) and fragment (`#…`) by their LITERAL
  // characters — the request URL carries them unencoded (clients encode
  // them as `%3F` / `%23` when they want them in the path).
  const rawUrl = req.url || "/";
  let pathname = rawUrl;
  const qIdx = pathname.indexOf("?");
  if (qIdx >= 0) pathname = pathname.slice(0, qIdx);
  const fIdx = pathname.indexOf("#");
  if (fIdx >= 0) pathname = pathname.slice(0, fIdx);
  if (pathname === "" || pathname[0] !== "/") pathname = "/" + pathname;

  // Method guard: only GET / HEAD are accepted. POST / PUT / DELETE / etc.
  // return 405 with `Allow: GET, HEAD` (the static server is read-only).
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, { "allow": "GET, HEAD", "content-length": "0" });
    res.end();
    return;
  }
  const headOnly = req.method === "HEAD";

  // Resolve the on-disk target. Any failure (traversal / unknown path /
  // directory leakage) returns 404 — never auto-fallback, never leak.
  const target = await resolveServeTarget(ctx.rootAbs, pathname);
  if (target === null) {
    sendError(res, 404, "Not found");
    return;
  }

  // Read the body. We could stat-then-read but `readFile` already
  // surfaces ENOENT as a rejection; the previous stat guarantees we hit
  // a regular file but the read can still fail mid-flight.
  let body;
  try { body = await readFile(target.absPath); }
  catch { sendError(res, 500, "Read error"); return; }

  const ct = contentTypeFor(target.absPath);
  const headers = {
    "content-type": ct,
    "content-length": String(body.length),
    "cache-control": "no-store",
  };
  res.writeHead(200, headers);
  // HEAD MUST mirror GET's wire headers (Content-Type + Content-Length)
  // WITHOUT a body — the response body itself is empty per HTTP
  // semantics for HEAD. Clients use Content-Length to size the GET body
  // without consuming it.
  if (headOnly) { res.end(); return; }
  res.end(body);
}

// Public lifecycle (importable surface for the composition slice).
export async function startServer({ port = 0, host = EXPORT_SERVER_DEFAULT_HOST, root } = {}) {
  // Validate `root` BEFORE binding: mandatory, absolute, existing, and
  // a directory. Any failure throws synchronously so the composition
  // slice sees a clear error rather than a listener that's bound to
  // something else.
  if (typeof root !== "string" || root.length === 0) {
    throw new Error("--root is required (absolute path to an existing export directory)");
  }
  if (!isAbsolute(root)) {
    throw new Error(`--root must be an absolute path; got ${JSON.stringify(root)}`);
  }
  const rootAbs = resolve(root);
  let rootStat;
  try { rootStat = await stat(rootAbs); }
  catch (err) {
    throw new Error(`--root does not exist: ${rootAbs} (${err && err.code ? err.code : "stat failed"})`);
  }
  if (!rootStat.isDirectory()) {
    throw new Error(`--root is not a directory: ${rootAbs}`);
  }

  const ctx = { rootAbs, host };
  const server = createServer((req, res) => {
    // Always funnel through a single async handler so 500s never crash
    // the listener and so HEAD / GET share the same resolve path.
    handleRequest(req, res, ctx).catch((err) => {
      // Last-resort guard: the handler's own try/catch should catch
      // everything, but if something escapes, send a 500 instead of
      // closing the socket mid-response.
      try { sendError(res, 500, "Internal error"); }
      catch { try { res.end(); } catch { /* socket gone */ } }
      // Surface the error on stderr so the harness CLI flag it loudly.
      process.stderr.write(`[export-server.mjs] unhandled: ${err && err.message ? err.message : String(err)}\n`);
    });
  });

  await new Promise((resolveBind, rejectBind) => {
    const onError = (err) => { server.removeListener("listening", onListening); rejectBind(err); };
    const onListening = () => { server.removeListener("error", onError); resolveBind(); };
    server.once("error", onError);
    server.once("listening", onListening);
    server.listen(port, host);
  });

  const addr = server.address();
  const actualPort = typeof addr === "object" && addr ? addr.port : port;
  return {
    schema: EXPORT_SERVER_SCHEMA,
    root: rootAbs,
    host,
    port: actualPort,
    baseUrl: `http://${host}:${actualPort}`,
    server,
    async close() {
      await new Promise((resolveClose) => server.close(() => resolveClose()));
    },
  };
}
export async function stopServer(handle) {
  if (handle && typeof handle.close === "function") await handle.close();
}

// CLI entry: `node export-server.mjs --root PATH [--port N] [--host HOST]`.
function parseCliArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === "--port") {
      const n = Number(argv[++i]);
      if (!Number.isFinite(n) || n < 0 || n > 65535) {
        throw new Error(`--port must be 0..65535 (got ${JSON.stringify(argv[i])})`);
      }
      args.port = n;
    } else if (k === "--host") {
      args.host = argv[++i];
    } else if (k === "--root") {
      args.root = argv[++i];
    } else if (k === "--help" || k === "-h") {
      console.log("Usage: export-server.mjs --root PATH [--port N] [--host HOST]");
      process.exit(0);
    } else {
      throw new Error(`unknown argument: ${k}`);
    }
  }
  return args;
}

async function main() {
  const args = parseCliArgs(process.argv.slice(2));
  const port = Number.isFinite(args.port) ? args.port : 0;
  const host = typeof args.host === "string" && args.host.length > 0 ? args.host : EXPORT_SERVER_DEFAULT_HOST;
  const handle = await startServer({ port, host, root: args.root });
  process.stdout.write(
    `export-server:ready schema=${EXPORT_SERVER_SCHEMA} port=${handle.port} root=${handle.root} baseUrl=${handle.baseUrl}\n`
  );
  let shuttingDown = false;
  const shutdown = async (sig) => {
    if (shuttingDown) return;
    shuttingDown = true;
    try { await handle.close(); } catch { /* ignore */ }
    process.stdout.write(`export-server:stopped signal=${sig}\n`);
    process.exit(0);
  };
  process.once("SIGINT", () => shutdown("SIGINT"));
  process.once("SIGTERM", () => shutdown("SIGTERM"));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    process.stderr.write(`[export-server.mjs] FAIL: ${err && err.message ? err.message : String(err)}\n`);
    process.exit(1);
  });
}
