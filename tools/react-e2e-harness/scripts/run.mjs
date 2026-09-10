#!/usr/bin/env node
// tools/react-e2e-harness/scripts/run.mjs — PR 5c.2-B.1b-i capture CLI.
// Requires an EXPLICIT caller-provided already-running React export
// origin via --origin + --output-root. NO fixture API server, NO
// export HTTP server — deferred. The CLI delegates navigation to the
// injected `runFn` (defaults to ./chromium-driver.mjs) and writes an
// atomic, timestamped JSON evidence artifact on success ONLY.
//
// Fail-closed: missing flags, file://, non-http(s), origin paths,
// output collisions, and 5xx/network/navigation/contract errors
// propagate from `runFn`; atomicWrite is NEVER invoked on failure.

import { existsSync, mkdirSync, renameSync, rmSync } from "node:fs";
import { writeFile } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve } from "node:path";

import { runCapture } from "./chromium-driver.mjs";

const SCHEMA = "taxa.react-e2e.run/1";

// Filename-safe YYYY-MM-DDTHH-MM-SSZ.
export function utcRunTimestamp(now = new Date()) {
  const head = now.toISOString().slice(0, 19);
  return `${head.replace(/:/g, "-")}Z`;
}

export function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === "--origin") args.origin = argv[++i];
    else if (k === "--output-root") args.outputRoot = argv[++i];
    else if (k === "--help" || k === "-h") {
      console.log("Usage: run.mjs --origin URL --output-root DIR");
      process.exit(0);
    } else throw new Error(`unknown argument: ${k}`);
  }
  return args;
}

// Origin validation: http(s) with no path. Mirrors the
// parity_navigation contract so both drivers share origin rules.
export function validateOrigin(origin, label = "origin") {
  if (!origin || typeof origin !== "string") {
    throw new Error(`invalid origin: ${label} must be a non-empty string`);
  }
  let parsed;
  try { parsed = new URL(origin); } catch {
    throw new Error(`invalid origin: ${label} ${JSON.stringify(origin)} is not a valid URL`);
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error(`invalid origin: ${label} ${JSON.stringify(origin)} must use http(s):// (got ${parsed.protocol})`);
  }
  if (parsed.pathname !== "/" && parsed.pathname !== "") {
    throw new Error(`invalid origin: ${label} ${JSON.stringify(origin)} must not include a path; got ${parsed.pathname}`);
  }
  return origin.replace(/\/$/, "");
}

function _resolveUnderStaging(stagingRoot, name) {
  if (!name || typeof name !== "string") {
    throw new Error(`atomicWrite: file name must be a non-empty string`);
  }
  if (isAbsolute(name)) throw new Error(`atomicWrite: file name must be relative: ${JSON.stringify(name)}`);
  const resolved = resolve(stagingRoot, name);
  const rel = relative(stagingRoot, resolved);
  if (rel === "" || rel.startsWith("..") || isAbsolute(rel)) {
    throw new Error(`atomicWrite: file name ${JSON.stringify(name)} resolves outside staging dir`);
  }
  return resolved;
}

// Rollback-safe staged-rename; mirrors parity_navigation.mjs.
async function atomicWrite(outDir, files, { rename = renameSync } = {}) {
  const tmp = `${outDir}.tmp-${process.pid}-${Date.now()}`;
  const backup = `${outDir}.bak-${process.pid}-${Date.now()}`;
  let hadExisting = false;
  if (existsSync(outDir)) { rename(outDir, backup); hadExisting = true; }
  try {
    mkdirSync(tmp, { recursive: true });
    for (const [name, content] of Object.entries(files)) {
      const p = _resolveUnderStaging(tmp, name);
      mkdirSync(dirname(p), { recursive: true });
      await writeFile(p, content, "utf8");
    }
    rename(tmp, outDir);
  } catch (err) {
    if (hadExisting) {
      try { if (existsSync(outDir)) rmSync(outDir, { recursive: true, force: true }); rename(backup, outDir); } catch {}
    }
    try { if (existsSync(tmp)) rmSync(tmp, { recursive: true, force: true }); } catch {}
    throw err;
  }
  if (hadExisting) { try { rmSync(backup, { recursive: true, force: true }); } catch {} }
}

// Public capture entry. `runFn` + `now()` are injected so a future
// hermetic slice drives the CLI without a real browser/network.
export async function capture({
  origin, outputRoot, runFn = runCapture, now = () => new Date(),
}) {
  const cleanOrigin = validateOrigin(origin, "origin");
  if (!outputRoot || typeof outputRoot !== "string") {
    throw new Error("invalid outputRoot: must be a non-empty string");
  }
  const runTimestamp = utcRunTimestamp(now());
  const runDir = resolve(outputRoot, runTimestamp);
  if (existsSync(runDir)) throw new Error(`output collision: ${runDir} already exists`);
  // Delegate navigation BEFORE atomicWrite — any thrown error skips
  // the write so no evidence artifact is ever published on failure.
  const capturePayload = await runFn({ origin: cleanOrigin });
  const evidence = {
    schema: SCHEMA, runTimestamp, capturedAt: now().toISOString(),
    origin: cleanOrigin, nodeVersion: process.version, capture: capturePayload,
  };
  await atomicWrite(runDir, { "evidence.json": JSON.stringify(evidence, null, 2) });
  return { runDir, evidence };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.origin) throw new Error("missing --origin");
  if (!args.outputRoot) throw new Error("missing --output-root");
  await capture({ origin: args.origin, outputRoot: args.outputRoot });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error(`[run.mjs] FAIL: ${err && err.message ? err.message : String(err)}`);
    process.exit(1);
  });
}
