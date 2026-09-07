#!/usr/bin/env node
// tools/g4-capture/scripts/parity_navigation.mjs — G4 parity-navigation producer.
// First G4 parity slice (navigation-only; api/search/a11y/browser-state pending).
//
// User-approved decisions (slice contract):
//   - Navigation-only report; the other four remain pending.
//   - Playwright is the browser driver. Runner is dynamic-imported from
//     the isolated tools/g4-capture/node_modules/ workspace so the test
//     harness stays free of browser deps until the real path runs.
//   - Both legacy and candidate HTTP origins driven in one invocation;
//     each side gets its own timestamped run directory.
//   - Run-directory names use UTC seconds-precision timestamps of the form
//     YYYY-MM-DDTHH-MM-SSZ (filename-safe; colon replaced with hyphen).
//     `captured_at` JSON value uses the seconds-precision Z form per
//     scripts/verify_parity.py::ISO_FMT.
//   - Fail-closed on missing/invalid origins, unavailable runner, 5xx or
//     network errors on either side, manifest path mismatch, output
//     collision; no `file://` targets are accepted.
//   - `navigation.json` shape matches the versioned common header and
//     the navigation record list in scripts/verify_parity.py.

import { existsSync, mkdirSync, renameSync, rmSync } from "node:fs";
import { readFile, writeFile } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import os from "node:os";

// Versioned common header — must equal scripts/verify_parity.py::SCHEMA_VERSION.
export const SCHEMA_VERSION = "1.0.0";
// Producer-side schemas (separate from the verify_parity common header).
export const NAVIGATION_SCHEMA = "taxa.g4-parity.navigation/1";
export const RUN_SCHEMA = "taxa.g4-parity.run/1";
export const MANIFEST_SCHEMA = "taxa.g4-parity.navigation-manifest/1";

const log = (...a) => console.log("[parity-navigation]", ...a);
const fail = (msg, ctx) => {
  console.error(
    `[parity-navigation] FAIL: ${msg}${ctx ? " " + JSON.stringify(ctx) : ""}`,
  );
  process.exit(1);
};

// ── UTC timestamp helpers ────────────────────────────────────────────────────

// Run-directory timestamp: YYYY-MM-DDTHH-MM-SSZ (filename-safe; colon replaced
// with hyphen because Windows rejects ':' in path components).
export function utcRunTimestamp(now = new Date()) {
  const iso = now.toISOString();           // 2026-09-08T15:30:45.123Z
  const head = iso.slice(0, 19);            // 2026-09-08T15:30:45
  return `${head.replace(/:/g, "-")}Z`;     // 2026-09-08T15-30-45Z
}

// captured_at JSON value: seconds-precision Z form matching
// scripts/verify_parity.py::ISO_FMT = "%Y-%m-%dT%H:%M:%SZ".
export function utcCapturedAt(now = new Date()) {
  return `${now.toISOString().slice(0, 19)}Z`; // 2026-09-08T15:30:45Z
}

// ── CLI argument parsing ─────────────────────────────────────────────────────

export function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === "--legacy-origin") args.legacyOrigin = argv[++i];
    else if (k === "--candidate-origin") args.candidateOrigin = argv[++i];
    else if (k === "--paths") args.paths = argv[++i];
    else if (k === "--manifest") args.manifestPath = argv[++i];
    else if (k === "--output-root") args.outputRoot = argv[++i];
    else if (k === "--help" || k === "-h") {
      console.log(
        "Usage: parity_navigation.mjs --legacy-origin URL --candidate-origin URL " +
        "--paths /a,/b [--manifest PATH] --output-root DIR",
      );
      process.exit(0);
    } else fail(`unknown argument: ${k}`);
  }
  // Use the user-visible kebab-case flag name in the missing-arg error so
  // the message matches the CLI the user typed.
  const required = [
    ["legacyOrigin", "legacy-origin"],
    ["candidateOrigin", "candidate-origin"],
    ["paths", "paths"],
    ["outputRoot", "output-root"],
  ];
  for (const [key, flag] of required) {
    if (!args[key]) fail(`missing --${flag}`);
  }
  return args;
}

// ── Origin + path validation ─────────────────────────────────────────────────

// Origin validation: must parse as an http(s) URL with no path component
// (controlled HTTP transport — no `file://`, no per-path origins).
export function validateOrigin(origin, label = "origin") {
  if (!origin || typeof origin !== "string") {
    throw new Error(`invalid origin: ${label} must be a non-empty string`);
  }
  let parsed;
  try {
    parsed = new URL(origin);
  } catch {
    throw new Error(`invalid origin: ${label} ${JSON.stringify(origin)} is not a valid URL`);
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error(
      `invalid origin: ${label} ${JSON.stringify(origin)} must use http(s):// (got ${parsed.protocol})`,
    );
  }
  if (parsed.pathname !== "/" && parsed.pathname !== "") {
    throw new Error(
      `invalid origin: ${label} ${JSON.stringify(origin)} must not include a path; got ${parsed.pathname}`,
    );
  }
  // Strip trailing slash so URL joining produces clean "...//index.html".
  return origin.replace(/\/$/, "");
}

// Validate the paths list: non-empty, each starts with '/', and (if a
// manifest is supplied) every declared path appears in manifest.paths.
export function validatePaths({ paths, manifest }) {
  if (!Array.isArray(paths) || paths.length === 0) {
    throw new Error("paths: must be a non-empty list");
  }
  for (const p of paths) {
    if (typeof p !== "string" || !p.startsWith("/")) {
      throw new Error(
        `paths: each entry must be a path starting with '/'; got ${JSON.stringify(p)}`,
      );
    }
  }
  if (manifest) {
    if (!manifest || manifest.schema !== MANIFEST_SCHEMA) {
      throw new Error(
        `manifest schema mismatch: want ${MANIFEST_SCHEMA}, got ${manifest && manifest.schema}`,
      );
    }
    const declared = new Set(manifest.paths ?? []);
    for (const p of paths) {
      if (!declared.has(p)) {
        throw new Error(`paths: path mismatch: ${JSON.stringify(p)} not declared in manifest`);
      }
    }
  }
  return paths;
}

// ── Default Playwright-based runner ──────────────────────────────────────────

// Lazy-imports Playwright so the test harness stays free of browser deps
// until the real path is exercised. Each path is visited via page.goto;
// the resulting status is captured from the browser response. A network
// error or non-HTTP status surfaces as `status: 0`.
export async function defaultRunNavigation({ origin, paths }) {
  const playwright = await import("playwright");
  const browser = await playwright.chromium.launch({ headless: true });
  const results = [];
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    for (const path of paths) {
      let status = 0;
      try {
        const response = await page.goto(`${origin}${path}`, {
          waitUntil: "load", timeout: 30000,
        });
        if (response) status = response.status();
      } catch { /* network/timeout/4xx-as-throw — surface as 0 */ }
      results.push({ path, status });
    }
  } finally {
    try { await browser.close(); } catch { /* already closed */ }
  }
  return results;
}

// ── Atomic write helpers ─────────────────────────────────────────────────────

// Reject any file name whose resolved path escapes the staging dir. Absolute
// paths and `..`-ladder names would otherwise let evidence files leak.
function _resolveUnderStaging(stagingRoot, name) {
  if (!name || typeof name !== "string") {
    throw new Error(`atomicWrite: file name must be a non-empty string`);
  }
  if (isAbsolute(name)) {
    throw new Error(`atomicWrite: file name must be relative: ${JSON.stringify(name)}`);
  }
  const resolved = resolve(stagingRoot, name);
  const rel = relative(stagingRoot, resolved);
  if (rel === "" || rel.startsWith("..") || isAbsolute(rel)) {
    throw new Error(
      `atomicWrite: file name ${JSON.stringify(name)} resolves outside staging dir`,
    );
  }
  return resolved;
}

// Rollback-safe staged-rename: relocate any existing `outDir` aside into a
// sibling backup, stage the new payload into a sibling tmp dir, then rename
// tmp → outDir. If the final rename fails, restore from the backup so the
// prior output stays readable. Mirrors tools/g4-capture/scripts/capture.mjs
// so both slices share the same atomic-write contract.
async function atomicWrite(outDir, files, { rename = renameSync } = {}) {
  const tmp = `${outDir}.tmp-${process.pid}-${Date.now()}`;
  const backup = `${outDir}.bak-${process.pid}-${Date.now()}`;
  let hadExisting = false;
  if (existsSync(outDir)) { rename(outDir, backup); hadExisting = true; }
  let staged = false;
  try {
    mkdirSync(tmp, { recursive: true });
    for (const [name, content] of Object.entries(files)) {
      const p = _resolveUnderStaging(tmp, name);
      mkdirSync(dirname(p), { recursive: true });
      await writeFile(p, content, "utf8");
    }
    rename(tmp, outDir);
    staged = true;
  } catch (err) {
    if (hadExisting) {
      try {
        if (existsSync(outDir)) rmSync(outDir, { recursive: true, force: true });
        rename(backup, outDir);
      } catch {}
    }
    try { if (existsSync(tmp)) rmSync(tmp, { recursive: true, force: true }); } catch {}
    throw err;
  }
  if (hadExisting && staged) {
    try { rmSync(backup, { recursive: true, force: true }); } catch {}
  }
}

// ── Capture orchestration ────────────────────────────────────────────────────

// Run one side through the injected `runFn`. Fail-closed gate: any 5xx
// status or status == 0 (network error, navigation timeout) raises.
async function _driveSide({ side, origin, paths, runFn }) {
  const results = await runFn({ side, origin, paths });
  if (!Array.isArray(results)) {
    throw new Error(`navigation failure: ${side} runner returned non-array`);
  }
  for (const r of results) {
    if (!r || typeof r !== "object") {
      throw new Error(`navigation failure: ${side} runner emitted non-object entry`);
    }
    if (typeof r.path !== "string" || typeof r.status !== "number") {
      throw new Error(`navigation failure: ${side} runner emitted malformed entry ${JSON.stringify(r)}`);
    }
    if (r.status === 0 || r.status >= 500) {
      throw new Error(`navigation failure: ${side} ${r.path} status ${r.status}`);
    }
  }
  return results;
}

// Fail-closed path-outcome drift guard: when both sides visit the same path,
// the (path, status) outcomes MUST agree exactly. The verifier also catches
// drift, but the producer must surface it at write time so a broken run
// never publishes a "clean" navigation.json on either side.
function _enforceDriftClosure(legacyResults, candidateResults) {
  if (legacyResults.length !== candidateResults.length) {
    throw new Error(
      `navigation drift: legacy produced ${legacyResults.length} entries, candidate produced ${candidateResults.length}`,
    );
  }
  for (let i = 0; i < legacyResults.length; i++) {
    const l = legacyResults[i];
    const c = candidateResults[i];
    if (l.path !== c.path || l.status !== c.status) {
      throw new Error(
        `navigation drift: path ${JSON.stringify(l.path)} legacy=${l.status} candidate=${c.status}`,
      );
    }
  }
}

function _buildRunJson({ runTimestamp, capturedAt, nodeVersion, playwrightVersion }) {
  return {
    schema: RUN_SCHEMA, runTimestamp, capturedAt,
    nodeVersion, playwrightVersion: playwrightVersion ?? "unknown",
    host: os.hostname(),
  };
}

function _buildNavigationJson({ capturedAt, results }) {
  return {
    schema: NAVIGATION_SCHEMA,
    schema_version: SCHEMA_VERSION,
    captured_at: capturedAt,
    paths: results,
  };
}

// Public capture entry point. Accepts an injected `runFn` so hermetic tests
// can simulate network failures, 5xx responses, and exact result drift
// without a real browser or live network.
export async function capture({
  legacyOrigin, candidateOrigin, paths, manifest = null, outputRoot,
  runFn = defaultRunNavigation, now = () => new Date(),
}) {
  // 1. Validate origins + paths. Each failure throws synchronously before
  //    any directory creation, so a rejected run never leaves staging siblings.
  const legacy = validateOrigin(legacyOrigin, "legacy-origin");
  const candidate = validateOrigin(candidateOrigin, "candidate-origin");
  if (legacy === candidate) {
    throw new Error("legacy-origin and candidate-origin must differ");
  }
  validatePaths({ paths, manifest });
  // 2. Drive both sides through the injected runner. Any per-side throw
  //    (e.g. ECONNREFUSED) propagates up before any write.
  const legacyResults = await _driveSide({ side: "legacy", origin: legacy, paths, runFn });
  const candidateResults = await _driveSide({ side: "candidate", origin: candidate, paths, runFn });
  // 3. Per-path drift guard: identical (path, status) on both sides.
  _enforceDriftClosure(legacyResults, candidateResults);
  // 4. Resolve the timestamped run directory; reject if it already exists.
  const runTimestamp = utcRunTimestamp(now());
  const capturedAt = utcCapturedAt(now());
  const runDir = resolve(outputRoot, runTimestamp);
  if (existsSync(runDir)) {
    throw new Error(`output collision: ${runDir} already exists`);
  }
  // 5. Atomic write — both side dirs together under the same run timestamp.
  //    If either write fails, the rollback-safe staged-rename restores
  //    whatever was previously at `runDir` (none, on first run).
  const runJson = _buildRunJson({ runTimestamp, capturedAt, nodeVersion: process.version });
  const legacyDir = resolve(runDir, "legacy");
  const candidateDir = resolve(runDir, "candidate");
  const writeSide = async (sideDir, sideResults) => atomicWrite(sideDir, {
    "navigation.json": JSON.stringify(_buildNavigationJson({ capturedAt, results: sideResults }), null, 2),
    "manifest.snapshot.json": JSON.stringify(manifest, null, 2),
    "run.json": JSON.stringify(runJson, null, 2),
  });
  await writeSide(legacyDir, legacyResults);
  await writeSide(candidateDir, candidateResults);

  return {
    runTimestamp, capturedAt, runDir, legacyRunDir: legacyDir, candidateRunDir: candidateDir,
    legacyNavigation: _buildNavigationJson({ capturedAt, results: legacyResults }),
    candidateNavigation: _buildNavigationJson({ capturedAt, results: candidateResults }),
  };
}

async function _loadManifest(manifestPath) {
  if (!manifestPath) return null;
  try {
    return JSON.parse(await readFile(manifestPath, "utf8"));
  } catch (err) {
    fail(`cannot read manifest: ${err.message}`, { path: String(manifestPath) });
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const manifest = await _loadManifest(args.manifestPath);
  const paths = String(args.paths).split(",").map((p) => p.trim()).filter(Boolean);
  await capture({
    legacyOrigin: args.legacyOrigin,
    candidateOrigin: args.candidateOrigin,
    paths, manifest, outputRoot: args.outputRoot,
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => { console.error(err); process.exit(1); });
}
