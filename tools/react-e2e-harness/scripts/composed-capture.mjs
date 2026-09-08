#!/usr/bin/env node
// tools/react-e2e-harness/scripts/composed-capture.mjs — PR 5c.2-B.1b-ii-c.
// Composition orchestrator: fixture API (5c.2-B.1b-ii-a) + static export
// HTTP server (5c.2-B.1b-ii-b) + capture / chromium runner (5c.2-B.1b-i)
// wired into a reusable importable + CLI driver. No npm deps; pure Node
// built-ins; never hard-codes a port; CLI `--output-root` mandatory.
// Cleanup is reverse-order under nested `finally`; failures propagate
// without publishing evidence. Injection seams (buildFn / captureFn / now)
// let the hermetic test slice run without Playwright or real `npm run build`.

import { spawn } from "node:child_process";
import { access, constants } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { startServer as startFixture, HARNESS_TAXON_ID } from "./fixture-server.mjs";
import { startServer as startExport } from "./export-server.mjs";
import { capture as defaultCapture } from "./run.mjs";

export const COMPOSED_CAPTURE_SCHEMA = "taxa.react-e2e-composed-capture/1";
const DEFAULT_HOST = "127.0.0.1";
// Default harnessDir MUST derive from the script's `import.meta.url` (one
// level above `scripts/`), NOT from `process.cwd()`. The legacy cwd-based
// default duplicated the path when the CLI was invoked from the package
// directory (`npm run capture:composed -- --output-root DIR` runs with cwd =
// `tools/react-e2e-harness`) and `defaultBuildFn` then failed with
// `spawn npm ENOENT`. Explicit `--harness-dir` continues to take precedence.
export function resolveDefaultHarnessDir() {
  return resolve(dirname(fileURLToPath(import.meta.url)), "..");
}
// Loopback-only: composition never binds to an external/interface address.
// Mirrors fixture-server / export-server defaults (127.0.0.1) plus the IPv6
// loopback and the canonical hostname alias. Any other shape fails closed.
const LOOPBACK_HOSTS = Object.freeze(new Set(["127.0.0.1", "::1", "localhost"]));

export async function defaultBuildFn({ harnessDir, env }) {
  return await new Promise((resolveB, rejectB) => {
    const child = spawn("npm", ["run", "build"], {
      cwd: harnessDir, env: { ...process.env, ...(env || {}) },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "", stderr = "";
    child.stdout.on("data", (b) => { stdout += b.toString("utf8"); });
    child.stderr.on("data", (b) => { stderr += b.toString("utf8"); });
    child.on("error", rejectB);
    child.on("exit", (code) => {
      if (code === 0) resolveB({ ok: true, stdout, stderr });
      else rejectB(new Error(`defaultBuildFn: build failed exit=${code} stderr=${stderr.trim().slice(0, 4096)}`));
    });
  });
}

export async function defaultCaptureFn({ origin, outputRoot }) {
  return await defaultCapture({ origin, outputRoot });
}

export function parseCliArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === "--output-root") args.outputRoot = argv[++i];
    else if (k === "--harness-dir") args.harnessDir = argv[++i];
    else if (k === "--taxon-id") args.taxonId = argv[++i];
    else if (k === "--host") args.host = argv[++i];
    else if (k === "--help" || k === "-h") {
      console.log("Usage: composed-capture.mjs --output-root DIR [--harness-dir DIR] [--taxon-id N] [--host HOST]");
      process.exit(0);
    } else throw new Error(`unknown argument: ${k}`);
  }
  return args;
}

// safe positive-integer parser; rejects zero / float / sci / empty / whitespace.
export function validateTaxonId(raw, label = "taxonId") {
  if (raw === undefined || raw === null) return HARNESS_TAXON_ID;
  const s = typeof raw === "string" ? raw.trim() : String(raw).trim();
  if (s.length === 0) throw new Error(`invalid ${label}: must not be empty`);
  if (!/^\d+$/.test(s)) {
    throw new Error(`invalid ${label}: must match /^\\d+$/ (digits only); got ${JSON.stringify(raw)}`);
  }
  const n = Number(s);
  if (!Number.isInteger(n) || n <= 0 || n > Number.MAX_SAFE_INTEGER) {
    throw new Error(`invalid ${label}: out of safe-integer range; got ${JSON.stringify(raw)}`);
  }
  // Harness app + fixture serve ONLY synthetic taxon id 1
  // (see tools/react-e2e-harness/app/page.tsx::HARNESS_TAXON_ID and
  // fixture-server.mjs::HARNESS_TAXON_ID). Reject any other id so a
  // passing --taxon-id cannot silently produce a build that the
  // fixture/runner will reject at runtime.
  if (n !== HARNESS_TAXON_ID) {
    throw new Error(`invalid ${label}: harness app + fixture serve only taxon id ${HARNESS_TAXON_ID}; got ${n}`);
  }
  return n;
}

// loopback / RFC-1123 hostname; rejects whitespace / control / shell-meta / slash / >253 chars.
export function validateHost(raw, fallback = DEFAULT_HOST) {
  if (raw === undefined || raw === null) return fallback;
  if (typeof raw !== "string") {
    throw new Error(`invalid host: must be a non-empty string; got ${JSON.stringify(raw)}`);
  }
  const s = raw.trim();
  if (s.length === 0 || s.length > 253) {
    throw new Error(`invalid host: length out of range; got ${JSON.stringify(raw)}`);
  }
  if (/[\r\n\0\s]/.test(s)) {
    throw new Error(`invalid host: must not contain whitespace / control chars; got ${JSON.stringify(raw)}`);
  }
  if (!/^[A-Za-z0-9._:-]+$/.test(s)) {
    throw new Error(`invalid host: only [A-Za-z0-9._:-] allowed; got ${JSON.stringify(raw)}`);
  }
  // Loopback-only binding: the composition driver must never expose the
  // harness on an external/interface address. 127.0.0.1 (IPv4 loopback),
  // ::1 (IPv6 loopback), and the canonical hostname alias are the only
  // acceptable shapes. Anything else fails closed BEFORE any server binds.
  if (!LOOPBACK_HOSTS.has(s)) {
    throw new Error(`invalid host: composition is loopback-only; got ${JSON.stringify(raw)} (expected one of: ${[...LOOPBACK_HOSTS].join(", ")})`);
  }
  return s;
}

export async function composeCapture({
  harnessDir,
  outputRoot,
  taxonId = HARNESS_TAXON_ID,
  host = DEFAULT_HOST,
  buildFn = defaultBuildFn,
  captureFn = defaultCaptureFn,
  // Injection seams for the hermetic test slice: defaults to the real
  // in-process startServer from the fixture / export modules so the
  // production composition path is unchanged. Tests can swap these for
  // spies that observe bind/close order.
  startFixtureFn = startFixture,
  startExportFn = startExport,
  now = () => new Date(),
} = {}) {
  if (typeof harnessDir !== "string" || harnessDir.length === 0) {
    throw new Error("invalid harnessDir: must be a non-empty string");
  }
  if (typeof outputRoot !== "string" || outputRoot.length === 0) {
    throw new Error("invalid outputRoot: must be a non-empty string");
  }
  const safeTaxonId = validateTaxonId(taxonId);
  const safeHost = validateHost(host);
  const absHarnessDir = resolve(harnessDir);
  const outDir = resolve(absHarnessDir, "out");

  // Step 1: bind fixture API on OS port 0.
  const fixtureHandle = await startFixtureFn({ port: 0, host: safeHost });
  let exportHandle = null;
  try {
    // Step 2: build with NEXT_PUBLIC_HARNESS_BASE_URL pinned to the fixture.
    await buildFn({
      harnessDir: absHarnessDir,
      env: { NEXT_PUBLIC_HARNESS_BASE_URL: fixtureHandle.baseUrl },
      now,
    });
    // Step 3: verify out/index.html (fail-closed).
    await access(resolve(outDir, "index.html"), constants.R_OK);
    // Step 4: bind static export server on OS port 0.
    exportHandle = await startExportFn({ port: 0, host: safeHost, root: outDir });
    try {
      // Step 5: invoke capture (chromium) runner with export origin.
      const captureResult = await captureFn({ origin: exportHandle.baseUrl, outputRoot, now });
      return {
        schema: COMPOSED_CAPTURE_SCHEMA, taxonId: safeTaxonId,
        harnessDir: absHarnessDir, outDir, now: now().toISOString(),
        fixture: { schema: fixtureHandle.schema, host: fixtureHandle.host, port: fixtureHandle.port, baseUrl: fixtureHandle.baseUrl },
        export: { schema: exportHandle.schema, root: exportHandle.root, host: exportHandle.host, port: exportHandle.port, baseUrl: exportHandle.baseUrl },
        capture: captureResult,
      };
    } finally {
      // Reverse-order cleanup: step 4 first.
      try { if (exportHandle) await exportHandle.close(); } catch { /* ignore */ }
    }
  } finally {
    // Reverse-order cleanup: step 1 last.
    try { await fixtureHandle.close(); } catch { /* ignore */ }
  }
}

async function main() {
  const args = parseCliArgs(process.argv.slice(2));
  if (!args.outputRoot) throw new Error("missing --output-root");
  const harnessDir = args.harnessDir ?? resolveDefaultHarnessDir();
  const result = await composeCapture({ harnessDir, outputRoot: args.outputRoot, taxonId: args.taxonId, host: args.host });
  process.stdout.write(
    `composed-capture:done schema=${result.schema} taxon=${result.taxonId} fixtureBase=${result.fixture.baseUrl} exportBase=${result.export.baseUrl} runDir=${result.capture.runDir}\n`
  );
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    process.stderr.write(`[composed-capture.mjs] FAIL: ${err && err.message ? err.message : String(err)}\n`);
    process.exit(1);
  });
}
