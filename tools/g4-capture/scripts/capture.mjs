#!/usr/bin/env node
// tools/g4-capture/scripts/capture.mjs — G4 capture producer (slice 1 + capture-2).
// URL-parametrized; isolated Node/Lighthouse workspace; no server startup;
// no product changes. Atomic output to `out/`; provenance recorded; manifest
// snapshot alongside evidence.
//   slice 1   — producer framework + dry-run capture
//   capture-2 — real Lighthouse runner: dynamic `lighthouse` + `chrome-launcher`
//               with a fixed configuration/categories and a deterministic
//               mapping from LHR to evidence; runner failure MUST NOT publish
//               or replace the output directory (fail-closed).
// See tools/g4-capture/README.md.

import { existsSync, mkdirSync, renameSync, rmSync } from "node:fs";
import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import os from "node:os";

const SCHEMA = "taxa.g4-capture.evidence/1";
const MANIFEST_SCHEMA = "taxa.g4-capture.manifest/1";

// Locked set of Lighthouse categories. The slice-2 contract pins this list;
// any change requires a contract PR.
const FIXED_CATEGORIES = Object.freeze([
  "performance",
  "accessibility",
  "best-practices",
  "seo",
]);

// Headless Chrome flags for chrome-launcher. Frozen for reproducibility:
//   --headless=new       — Chrome's modern headless mode (Lighthouse 12.x default)
//   --no-sandbox         — required when running as root or in some CI containers
//   --disable-gpu        — suppress GPU init warnings under headless
//   --disable-dev-shm-usage — avoid /dev/shm exhaustion in CI containers
const CHROME_FLAGS = Object.freeze([
  "--headless=new",
  "--no-sandbox",
  "--disable-gpu",
  "--disable-dev-shm-usage",
]);

// Matches the Chrome/MAJOR.MINOR.BUILD.PATCH token inside a Lighthouse
// `userAgent` string. Used by `chromeVersionFromUserAgent` below.
const CHROME_VERSION_RE = /Chrome\/(\d+\.\d+\.\d+\.\d+)/;

// Fixed Lighthouse configuration. Reproducible across runs and platforms:
//   - onlyCategories locks the scored set to the four-category list above
//   - formFactor=desktop + frozen screenEmulation/throttling keeps the audit
//     scoring deterministic (mobile throttling would yield different numbers)
//   - `extends: lighthouse:default` fills in any unspecified setting
const FIXED_LIGHTHOUSE_CONFIG = Object.freeze({
  extends: "lighthouse:default",
  settings: Object.freeze({
    onlyCategories: [...FIXED_CATEGORIES],
    formFactor: "desktop",
    throttlingMethod: "simulate",
    screenEmulation: Object.freeze({
      mobile: false,
      width: 1350,
      height: 940,
      deviceScaleFactor: 1,
      disabled: false,
    }),
    throttling: Object.freeze({
      rttMs: 40,
      throughputKbps: 10240,
      cpuSlowdownMultiplier: 1,
      requestLatencyMs: 0,
      downloadThroughputKbps: 0,
      uploadThroughputKbps: 0,
    }),
  }),
});

const log = (...a) => console.log("[capture]", ...a);
const fail = (msg, ctx) => {
  console.error(
    `[capture] FAIL: ${msg}${ctx ? " " + JSON.stringify(ctx) : ""}`,
  );
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
  for (const k of ["url", "manifest", "out"])
    if (!args[k]) fail(`missing --${k}`);
  return args;
}

export async function readJson(p) {
  try {
    return JSON.parse(await readFile(p, "utf8"));
  } catch (error) {
    fail("cannot read JSON", { path: String(p), error: error.message });
  }
}

export function validateManifest(manifest, url) {
  if (!manifest || manifest.schema !== MANIFEST_SCHEMA)
    fail("manifest schema mismatch", { want: MANIFEST_SCHEMA });
  const entry = (manifest.entries ?? []).find((e) => e.url === url);
  if (!entry) fail("url not in manifest.entries", { url });
  return entry;
}

export function buildProvenance({
  lighthouseVersion = "unknown",
  chromeVersion = "unknown",
  nodeVersion = process.version,
} = {}) {
  return {
    schema: "taxa.g4-capture.provenance/1",
    nodeVersion,
    lighthouseVersion,
    chromeVersion,
    host: os.hostname(),
    capturedAt: new Date().toISOString(),
  };
}

// ── Public slice-2 surface ─────────────────────────────────────────────

// `fixedCategories()` returns the locked four-category set (a fresh copy so
// callers cannot mutate the module-level freeze).
export function fixedCategories() {
  return [...FIXED_CATEGORIES];
}

// `fixedLighthouseConfig()` returns a deep clone of the locked config so
// callers cannot mutate module state.
export function fixedLighthouseConfig() {
  try {
    return JSON.parse(JSON.stringify(FIXED_LIGHTHOUSE_CONFIG));
  } catch (error) {
    fail("cannot clone fixed Lighthouse config", { error: error.message });
  }
}

// Parse the Chrome version out of a Lighthouse `userAgent` string.
// Example: "Mozilla/5.0 ... Chrome/120.0.6099.71 Safari/537.36" → "120.0.6099.71".
// Returns "unknown" if the string is missing or unparseable so the producer
// never crashes the capture because of a missing UA field.
export function chromeVersionFromUserAgent(userAgent) {
  if (typeof userAgent !== "string") return "unknown";
  const m = userAgent.match(CHROME_VERSION_RE);
  return m ? m[1] : "unknown";
}

// Deterministic LHR → evidence mapping. Filters categories to the locked
// four-category set (in fixed order), sorts `runWarnings` lexicographically,
// and selects only the fields needed downstream. Throws on non-object input
// so a malformed runner cannot silently write `null` evidence.
export function mapLhr(lhr) {
  if (!lhr || typeof lhr !== "object" || Array.isArray(lhr)) {
    throw new Error("mapLhr: lhr must be a non-array object");
  }
  const sourceCategories = lhr.categories ?? {};
  // Always emit every fixed-category slot — even when the runner's LHR
  // omitted one (older Lighthouse, network failure, category disabled by
  // config) — so downstream hashers see a stable key set.
  const mappedCategories = {};
  for (const id of FIXED_CATEGORIES) {
    const c = sourceCategories[id];
    if (c && typeof c === "object") {
      mappedCategories[id] = {
        score: c.score ?? null,
        title: c.title ?? id,
      };
    } else {
      mappedCategories[id] = { score: null, title: id };
    }
  }
  const warnings = Array.isArray(lhr.runWarnings) ? [...lhr.runWarnings] : [];
  warnings.sort();
  return {
    finalUrl: lhr.finalUrl ?? null,
    lighthouseVersion: lhr.lighthouseVersion ?? null,
    userAgent: lhr.userAgent ?? null,
    fetchTime: lhr.fetchTime ?? null,
    runWarnings: warnings,
    categories: mappedCategories,
    audits: lhr.audits ?? {},
  };
}

// Build the synthetic "lighthouse" payload used by --dry-run. Kept in a
// helper so the shape stays in lockstep with `mapLhr()`.
function syntheticLighthouseReport(url, expectedContentSha256) {
  return {
    finalUrl: url,
    runWarnings: ["dry-run: lighthouse not executed"],
    audits: {},
    synthetic: true,
    manifestEntryHash: expectedContentSha256 ?? null,
  };
}

// Real Lighthouse runner. Dynamically imports `lighthouse` + `chrome-launcher`
// from the isolated `tools/g4-capture/node_modules/` workspace so the
// slice-1 dry-run path stays free of browser deps. Launches a headless
// Chrome, runs Lighthouse with the fixed configuration, kills Chrome, and
// returns the raw LHR. Errors propagate to the caller — `capture()` does NOT
// write evidence if this function rejects, preserving fail-closed output.
export async function runLighthouse({ url } = {}) {
  if (!url) throw new Error("runLighthouse: url is required");
  const lighthouseModule = await import("lighthouse");
  const lighthouse = lighthouseModule.default ?? lighthouseModule;
  const chromeLauncher = await import("chrome-launcher");
  const chrome = await chromeLauncher.launch({
    chromeFlags: [...CHROME_FLAGS],
  });
  try {
    // Lighthouse 12.x API: lighthouse(url, flags, config).
    //   - `port` and `output` are runtime flags
    //   - `extends` + `settings.onlyCategories` are config
    const result = await lighthouse(
      url,
      { port: chrome.port, output: "json", logLevel: "error" },
      fixedLighthouseConfig(),
    );
    if (!result || !result.lhr) {
      throw new Error("runLighthouse: lighthouse returned no LHR");
    }
    return result.lhr;
  } finally {
    try {
      await chrome.kill();
    } catch {
      // Chrome may already be dead (e.g. SIGKILL'd by the run). Swallow so
      // the original error from `lighthouse(...)` reaches the caller.
    }
  }
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
    try {
      rmSync(tmp, { recursive: true, force: true });
    } catch {}
    throw err;
  }
}

export async function capture({
  url,
  manifest,
  outDir,
  dryRun,
  runLighthouse: runLighthouseFn,
  now = () => new Date().toISOString(),
  logger = log,
}) {
  const entry = validateManifest(manifest, url);
  // Real-run path (slice 2): the injected runner returns the raw LHR; we
  // map it deterministically before persistence. If the runner throws,
  // control never reaches `atomicWrite`, so the existing outDir (if any)
  // is left untouched and no evidence file is published.
  const mapped = dryRun
    ? syntheticLighthouseReport(url, entry.expectedContentSha256)
    : mapLhr(await runLighthouseFn({ url, manifestEntry: entry }));
  // `manifestEntryHash` is preserved across both paths so downstream
  // verifiers can correlate evidence with the manifest snapshot.
  mapped.manifestEntryHash = entry.expectedContentSha256 ?? null;
  const provenance = buildProvenance({
    lighthouseVersion: mapped.lighthouseVersion ?? "unknown",
    chromeVersion: mapped.userAgent
      ? chromeVersionFromUserAgent(mapped.userAgent)
      : "unknown",
  });
  const evidence = {
    schema: SCHEMA,
    url,
    capturedAt: now(),
    manifestEntry: entry,
    provenance,
    lighthouse: mapped,
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
    url: args.url,
    manifest,
    outDir: args.out,
    dryRun: args.dryRun,
    runLighthouse,
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
