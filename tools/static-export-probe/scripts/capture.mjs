#!/usr/bin/env node
// tools/static-export-probe/scripts/capture.mjs — see DESIGN.md.
// All-or-nothing: lockfile, npm ci, build, parity, serve, Playwright, audit, hash-guard.

import { createHash } from "node:crypto";
import { createServer } from "node:http";
import { createReadStream, existsSync, rmSync, statSync } from "node:fs";
import { mkdir, readFile, readdir, rename, writeFile } from "node:fs/promises";
import { pipeline } from "node:stream/promises";
import { dirname, relative, resolve } from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
const FIXTURE = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const REPO = resolve(FIXTURE, "..", "..");
const OUT = resolve(FIXTURE, "out");
const ARTIFACT = resolve(FIXTURE, "evidence", "static-export-probe.json");

const PINNED = { next: "16.3.3", react: "19.2.8", "react-dom": "19.2.8" };
const STITCH = { project: "11813286795400731874", screen: "ec543a4cec974c2e82085a5e0406334a" };
const FORBIDDEN_PORT = 8765;
const SAMPLES = 3;
const TIMEOUT_MS = 15000;
const ALLOWED = [
  "tools/static-export-probe/node_modules",
  "tools/static-export-probe/.next",
  "tools/static-export-probe/out",
];

const log = (...a) => console.log("[capture]", ...a);
const fail = (msg, ctx) => {
  console.error(`[capture] FAIL: ${msg}${ctx ? " " + JSON.stringify(ctx) : ""}`);
  try { if (existsSync(ARTIFACT)) rmSync(ARTIFACT, { force: true }); } catch {}
  process.exit(1);
};
const buildIdExpected = () => createHash("sha256").update(`next@${PINNED.next}|react@${PINNED.react}|react-dom@${PINNED["react-dom"]}`).digest("hex").slice(0, 16);

const run = (cmd, args, cwd = FIXTURE, env = {}) =>
  new Promise((res, rej) => {
    const p = spawn(cmd, args, {
      cwd,
      env: { ...process.env, ...env, NEXT_TELEMETRY_DISABLED: "1" },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let out = "", err = "";
    p.stdout.on("data", (c) => (out += c));
    p.stderr.on("data", (c) => (err += c));
    p.on("error", rej);
    p.on("close", (code) => res({ code, out, err }));
  });

const readJson = (p) => readFile(p, "utf8").then(JSON.parse);

const isAllowedPath = (p) => ALLOWED.some((d) => p === d || p.startsWith(d + "/"));

// Whole-repository content-hash baseline: walks every regular file under
// REPO and records path -> sha256. Skips .git/ and allowlist subtrees
// (node_modules/, .next/, out/, evidence/) since the capture is
// permitted to mutate only those surfaces. Detects content changes,
// additions, and deletions even when paths were already dirty/untracked
// before capture — unlike a git-status-only snapshot.
async function snapshotRepo() {
  const files = new Map();
  async function walk(dir) {
    for (const e of await readdir(dir, { withFileTypes: true })) {
      if (e.isSymbolicLink()) continue;
      const full = resolve(dir, e.name), rel = relative(REPO, full);
      if (e.isDirectory()) {
        if (e.name !== ".git" && !isAllowedPath(rel)) await walk(full);
      } else if (e.isFile()) {
        const h = createHash("sha256");
        await pipeline(createReadStream(full), h);
        files.set(rel, h.digest("hex"));
      }
    }
  }
  await walk(REPO);
  return files;
}

async function checkForbidden(baseline) {
  const cur = await snapshotRepo();
  const v = [];
  for (const p of baseline.keys())
    if (!cur.has(p) && !isAllowedPath(p)) v.push({ status: "deleted", path: p, reason: "outside-allowlist" });
  for (const [p, h] of cur) {
    const before = baseline.get(p);
    if (before === h || isAllowedPath(p)) continue;
    v.push({ status: before === undefined ? "added" : "modified", path: p, reason: "outside-allowlist" });
  }
  return v;
}

async function validateLockfile() {
  const lockPath = resolve(FIXTURE, "package-lock.json");
  if (!existsSync(lockPath)) fail("package-lock.json missing");
  const lock = await readJson(lockPath);
  if (!lock.packages) fail("lockfile missing `packages` tree");
  for (const [name, want] of Object.entries(PINNED)) {
    const e = lock.packages[`node_modules/${name}`];
    if (!e) fail(`lockfile missing ${name}`);
    if (e.version !== want) fail(`lockfile pin mismatch ${name}`, { want, got: e.version });
  }
}

async function npmCi() {
  const { code, err } = await run("npm", ["ci", "--no-audit", "--no-fund", "--prefer-offline"]);
  if (code !== 0) fail("npm ci failed", { code, stderr: err.slice(-2000) });
}

async function nextBuild() {
  for (const d of [resolve(FIXTURE, ".next"), OUT]) if (existsSync(d)) rmSync(d, { recursive: true, force: true });
  const { code, err } = await run("npx", ["next", "build"]);
  if (code !== 0) fail("next build failed", { code, stderr: err.slice(-2000) });
  if (!existsSync(OUT) || !statSync(OUT).isDirectory()) fail("out/ not produced");
}

async function readResolved() {
  const out = {};
  for (const name of Object.keys(PINNED)) {
    const p = resolve(FIXTURE, "node_modules", name, "package.json");
    if (!existsSync(p)) fail(`node_modules/${name}/package.json missing after npm ci`);
    out[name] = (await readJson(p)).version;
  }
  return out;
}

async function checkBuildId() {
  const want = buildIdExpected();
  const idFile = resolve(FIXTURE, ".next", "BUILD_ID");
  if (!existsSync(idFile)) fail(".next/BUILD_ID missing — generateBuildId did not run");
  const actual = (await readFile(idFile, "utf8")).trim();
  if (actual !== want) fail("BUILD_ID mismatch", { want, got: actual });
  if (!existsSync(resolve(OUT, "_next", "static", want))) fail(`out/_next/static/${want} missing — static assets not keyed by buildId`);
  return { expected: want, actual };
}

function startServer() {
  const CT = { ".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8" };
  return new Promise((res, rej) => {
    const server = createServer((req, r) => {
      let p = decodeURIComponent((req.url ?? "/").split("?")[0]);
      if (p === "/") p = "/index.html";
      const fp = resolve(OUT, "." + p);
      if (!fp.startsWith(OUT)) { r.statusCode = 403; return r.end(); }
      if (!existsSync(fp)) { r.statusCode = 404; return r.end(); }
      const ext = fp.slice(fp.lastIndexOf("."));
      r.setHeader("Content-Type", CT[ext] ?? "application/octet-stream");
      createReadStream(fp).pipe(r);
    });
    server.on("error", rej);
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      if (!addr || typeof addr === "string") return rej(new Error("no address"));
      if (addr.port === FORBIDDEN_PORT) return rej(new Error(`forbidden port ${FORBIDDEN_PORT}`));
      res({ server, port: addr.port });
    });
  });
}

async function collectSamples(srv) {
  const url = `http://127.0.0.1:${srv.port}/`;
  const hydrated = () => Boolean(document.querySelector('[data-testid="probe-marker"]')?.textContent?.includes("hydrated"));
  const { chromium } = await import("playwright");
  const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  try {
    const page = await (await browser.newContext()).newPage();
    const t0 = Date.now();
    const resp = await page.goto(url, { waitUntil: "load", timeout: TIMEOUT_MS });
    if (!resp) fail("page.goto returned no response");
    const status = resp.status();
    const domLoadedAtMs = Date.now() - t0;
    await page.waitForFunction(hydrated, { timeout: TIMEOUT_MS });
    const hydrationAtMs = Date.now() - t0;
    const markerText = (await page.locator('[data-testid="probe-marker"]').textContent()) ?? "";
    const provenanceText = (await page.locator('[data-testid="probe-provenance"]').textContent()) ?? "";
    const reload = [];
    for (let i = 0; i < SAMPLES; i++) {
      const rt = Date.now();
      await page.reload({ waitUntil: "load", timeout: TIMEOUT_MS });
      await page.waitForFunction(hydrated, { timeout: TIMEOUT_MS });
      reload.push(Date.now() - rt);
    }
    if (!markerText.includes("hydrated")) fail("hydration marker never reached 'hydrated'");
    if (reload.length !== SAMPLES) fail("missing reload samples", { got: reload.length });
    return { url, status, domLoadedAtMs, hydrationAtMs, reloadTimingsMs: reload, markerText, provenanceText };
  } finally {
    await browser.close();
  }
}

async function auditHtml() {
  const htmlPath = resolve(OUT, "index.html");
  if (!existsSync(htmlPath)) fail("out/index.html missing");
  const html = await readFile(htmlPath, "utf8");
  const n = (re) => (html.match(re) || []).length;
  const pIdx = html.indexOf(STITCH.project);
  const sIdx = html.indexOf(STITCH.screen);
  const checks = {
    background_white: /#FFFFFF/i.test(html),
    exactly_one_h1: n(/<h1\b/g) === 1,
    no_h2_to_h6: !/<h[2-6]\b/i.test(html),
    exactly_three_li: n(/<li\b/g) === 3,
    has_ul: n(/<ul\b/g) >= 1,
    has_main: n(/<main\b/g) >= 1,
    lang_attr_en: /<html\s+lang="en"/.test(html),
    no_chrome: !/<(nav|header|footer|section|article)\b/i.test(html),
    no_controls: !/<(button|input|select|textarea|form)\b/i.test(html),
    no_storage: !/localStorage|sessionStorage|indexedDB|document\.cookie/i.test(html),
    no_brand: !/--primary\b|--realm-/i.test(html),
    stitch_together: pIdx >= 0 && sIdx >= 0 && Math.abs(pIdx - sIdx) < 400,
  };
  for (const [k, ok] of Object.entries(checks)) if (!ok) fail(`HTML audit failed: ${k}`);
  return checks;
}

async function writeArtifact(payload) {
  await mkdir(resolve(FIXTURE, "evidence"), { recursive: true });
  const tmp = `${ARTIFACT}.tmp-${process.pid}`;
  try { await writeFile(tmp, JSON.stringify(payload, null, 2), "utf8"); await rename(tmp, ARTIFACT); }
  catch (err) { rmSync(tmp, { force: true }); throw err; }
}

async function main() {
  if (existsSync(ARTIFACT)) rmSync(ARTIFACT, { force: true });
  const baseline = await snapshotRepo();

  log("phase 1 — validate lockfile"); await validateLockfile();
  log("phase 2 — npm ci"); await npmCi();
  log("phase 3 — next build"); await nextBuild();
  log("phase 4 — resolved + buildId parity");
  const resolved = await readResolved();
  for (const [k, v] of Object.entries(PINNED)) if (resolved[k] !== v) fail(`${k} mismatch`, { want: v, got: resolved[k] });
  const buildId = await checkBuildId();

  log("phase 5 — loopback server");
  const srv = await startServer();
  let samples, audit;
  try {
    log("phase 6 — Playwright samples"); samples = await collectSamples(srv);
    log("phase 7 — HTML audit"); audit = await auditHtml();
  } finally { srv.server.close(); }

  log("phase 8 — forbidden-write check");
  const violations = await checkForbidden(baseline);
  if (violations.length > 0) fail("forbidden writes detected", { violations });

  log("phase 9 — atomic write");
  await writeArtifact({
    schema: "taxa.static-export-probe/1",
    generatedAt: new Date().toISOString(),
    pinned: PINNED,
    resolved,
    buildId,
    stitch: STITCH,
    samples,
    audit,
    node: process.version,
  });
  log(`DONE — wrote ${ARTIFACT}`);
  process.exit(0);
}

main().catch((err) => {
  console.error("[capture] unhandled", err);
  try { if (existsSync(ARTIFACT)) rmSync(ARTIFACT, { force: true }); } catch {}
  process.exit(1);
});
