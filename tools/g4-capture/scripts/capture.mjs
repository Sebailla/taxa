#!/usr/bin/env node
// tools/g4-capture/scripts/capture.mjs — G4 capture producer (slice 1).
// URL-parametrized; isolated Node/Lighthouse workspace; no server startup;
// no product changes. Atomic output to `out/`; provenance recorded; manifest
// snapshot alongside evidence. Slice 1 ships --dry-run; real Lighthouse is
// G4-capture-2. See tools/g4-capture/README.md.

import { existsSync, mkdirSync, renameSync, rmSync } from "node:fs";
import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import os from "node:os";

const SCHEMA = "taxa.g4-capture.evidence/1";
const MANIFEST_SCHEMA = "taxa.g4-capture.manifest/1";

const log = (...a) => console.log("[capture]", ...a);
const fail = (msg, ctx) => {
  console.error(`[capture] FAIL: ${msg}${ctx ? " " + JSON.stringify(ctx) : ""}`);
  process.exit(1);
};

export function parseArgs(argv) {
  const args = { dryRun: false };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === "--url") args.url = argv[++i];
    else if (k === "--manifest") args.manifest = argv[++i];
    else if (k === "--out") args.out = argv[++i];
    else if (k === "--dry-run") args.dryRun = true;
    else fail(`unknown argument: ${k}`);
  }
  for (const k of ["url", "manifest", "out"]) if (!args[k]) fail(`missing --${k}`);
  return args;
}

export async function readJson(p) { return JSON.parse(await readFile(p, "utf8")); }

export function validateManifest(manifest, url) {
  if (!manifest || manifest.schema !== MANIFEST_SCHEMA)
    fail("manifest schema mismatch", { want: MANIFEST_SCHEMA });
  const entry = (manifest.entries ?? []).find((e) => e.url === url);
  if (!entry) fail("url not in manifest.entries", { url });
  return entry;
}

export function buildProvenance({
  lighthouseVersion = "unknown", chromeVersion = "unknown", nodeVersion = process.version,
} = {}) {
  return {
    schema: "taxa.g4-capture.provenance/1",
    nodeVersion, lighthouseVersion, chromeVersion,
    host: os.hostname(), capturedAt: new Date().toISOString(),
  };
}

export async function atomicWrite(outDir, files) {
  // Atomic directory-rename. Write into a unique tmp dir, then rename onto
  // outDir in a single syscall. On any failure the tmp dir is removed and
  // outDir is left untouched (no partial state).
  const tmp = `${outDir}.tmp-${process.pid}-${Date.now()}`;
  try {
    mkdirSync(tmp, { recursive: true });
    for (const [name, content] of Object.entries(files)) {
      const p = resolve(tmp, name);
      mkdirSync(dirname(p), { recursive: true });
      await writeFile(p, content, "utf8");
    }
    if (existsSync(outDir)) rmSync(outDir, { recursive: true, force: true });
    renameSync(tmp, outDir);
  } catch (err) {
    try { rmSync(tmp, { recursive: true, force: true }); } catch {}
    throw err;
  }
}

export async function capture({
  url, manifest, outDir, dryRun, runLighthouse, now = () => new Date().toISOString(), logger = log,
}) {
  const entry = validateManifest(manifest, url);
  const lighthouseReport = dryRun
    ? { finalUrl: url, runWarnings: ["dry-run: lighthouse not executed"],
        audits: {}, synthetic: true, manifestEntryHash: entry.expectedContentSha256 ?? null }
    : await runLighthouse({ url, manifestEntry: entry });
  const provenance = buildProvenance({
    lighthouseVersion: lighthouseReport.lighthouseVersion ?? "unknown",
    chromeVersion: lighthouseReport.chromeVersion ?? "unknown",
  });
  const evidence = {
    schema: SCHEMA, url, capturedAt: now(),
    manifestEntry: entry, provenance, lighthouse: lighthouseReport,
  };
  await atomicWrite(outDir, {
    "evidence.json": JSON.stringify(evidence, null, 2),
    "manifest.snapshot.json": JSON.stringify(manifest, null, 2),
  });
  logger(`wrote evidence to ${outDir}`);
  return evidence;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const manifest = await readJson(args.manifest);
  await capture({
    url: args.url, manifest, outDir: args.out, dryRun: args.dryRun,
    runLighthouse: () => fail("real lighthouse capture not implemented in slice 1; use --dry-run"),
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => { console.error(err); process.exit(1); });
}