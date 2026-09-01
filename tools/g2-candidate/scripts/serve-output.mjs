#!/usr/bin/env node
/**
 * tools/g2-candidate/scripts/serve-output.mjs — loopback-only, zero-dep
 * Node static server for an explicit G2 candidate `out/` root. Diagnostic /
 * provisional only (G5 provisional candidate-readiness child). NEVER a
 * candidate for FastAPI activation.
 *
 * Contract: `/` -> `<root>/index.html`; any file under `<root>` -> 200 with
 * matching MIME; `..` in URL -> 400; missing files -> 404; missing/non-dir
 * root -> exit non-zero (NO fallback, especially no `web/` fallback);
 * non-loopback hostname -> exit non-zero. Emits `listening <host>:<port>`.
 */
import { createServer } from "node:http";
import { stat, open } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";

const args = process.argv.slice(2);
if (args.length === 0) {
  process.stderr.write("usage: serve-output.mjs <root-dir> [--port N] [--hostname HOST]\n");
  process.exit(2);
}
const opts = { root: resolve(args[0]), port: 0, hostname: "127.0.0.1" };
for (let i = 1; i < args.length; i++) {
  if (args[i] === "--port") opts.port = Number(args[++i]);
  else if (args[i] === "--hostname") opts.hostname = args[++i];
}
const LOOPBACK = new Set(["127.0.0.1", "::1", "localhost"]);
if (!LOOPBACK.has(opts.hostname)) {
  process.stderr.write(`[serve-output] refusing non-loopback hostname: ${opts.hostname}\n`);
  process.exit(3);
}
let rootStat;
try { rootStat = await stat(opts.root); }
catch { process.stderr.write(`[serve-output] root missing: ${opts.root}\n`); process.exit(4); }
if (!rootStat.isDirectory()) {
  process.stderr.write(`[serve-output] root is not a directory: ${opts.root}\n`);
  process.exit(5);
}
const ROOT_PREFIX = opts.root + sep;
const MIME = {
  ".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8", ".mjs": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
  ".gif": "image/gif", ".webp": "image/webp", ".ico": "image/x-icon",
  ".txt": "text/plain; charset=utf-8", ".woff": "font/woff", ".woff2": "font/woff2",
  ".map": "application/json; charset=utf-8",
};
const mimeFor = (p) => MIME[extname(p).toLowerCase()] || "application/octet-stream";

function safeResolve(reqPath) {
  let decoded;
  try { decoded = decodeURIComponent(reqPath); } catch { return null; }
  const resolved = resolve(opts.root + sep + decoded.replace(/^\/+/, ""));
  if (resolved !== opts.root && !resolved.startsWith(ROOT_PREFIX)) return null;
  return resolved;
}
function reject400(res) {
  res.writeHead(400, { "Content-Type": "text/plain; charset=utf-8" });
  res.end("Bad Request: directory traversal rejected");
}
function notFound(res) {
  res.writeHead(404, { "Content-Type": "text/plain" }); res.end("Not Found");
}

const server = createServer(async (req, res) => {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, { "Content-Type": "text/plain" }); res.end("Method Not Allowed"); return;
  }
  // Inspect req.url BEFORE URL parse: Node/WHATWG normalize `/../` to `/`,
  // but `%2e%2e` survives; raw `includes("..")` rejects every form.
  const raw = req.url || "/";
  if (raw.includes("..")) { reject400(res); return; }
  let path;
  try { path = new URL(raw, "http://127.0.0.1").pathname; }
  catch { reject400(res); return; }
  // `/` and any trailing-slash directory serve `<root>/index.html`.
  if (path === "/" || path.endsWith("/")) path = (path === "/" ? "" : path) + "index.html";
  const target = safeResolve(path);
  if (target === null) { reject400(res); return; }
  let st;
  try { st = await stat(target); }
  catch { notFound(res); return; }
  if (st.isDirectory()) { notFound(res); return; }
  let fh;
  try {
    fh = await open(target, "r");
    const stream = fh.createReadStream();
    res.writeHead(200, { "Content-Type": mimeFor(target), "Content-Length": st.size,
                          "Connection": "close" });
    if (req.method === "HEAD") { stream.destroy(); fh.close(); res.end(); return; }
    stream.on("end", () => fh.close());
    stream.on("error", () => { try { fh.close(); } catch {} });
    stream.pipe(res);
  } catch {
    if (fh) try { fh.close(); } catch {}
    res.writeHead(500, { "Content-Type": "text/plain" }); res.end("Internal Server Error");
  }
});

server.on("error", (err) => {
  process.stderr.write(`[serve-output] server error: ${err.message}\n`);
  process.exit(6);
});
server.listen(opts.port, opts.hostname, () => {
  const addr = server.address();
  process.stdout.write(`listening ${opts.hostname}:${addr.port}\n`);
});
for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => {
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 500).unref();
  });
}
