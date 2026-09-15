#!/usr/bin/env node
// tools/g4-capture/scripts/capture.mjs — G4 capture producer (slice 1 + capture-2 + capture-3).
// URL-parametrized; isolated Node/Lighthouse workspace; no server startup;
// no product changes. Atomic output to `out/`; provenance recorded; manifest
// snapshot alongside evidence.
//   slice 1   — producer framework + dry-run capture
//   capture-2 — real Lighthouse runner: dynamic `lighthouse` + `chrome-launcher`
//               with a fixed configuration/categories and a deterministic
//               mapping from LHR to evidence; runner failure MUST NOT publish
//               or replace the output directory (fail-closed).
//   capture-3 — pre-runner verification of the target URL (status + raw
//               sha256 + DOM marker from the corpus manifest) AND a
//               rollback-safe atomicWrite that preserves the prior complete
//               output via a sibling-backup strategy when the final rename
//               fails. Verification failure prevents runner invocation and
//               evidence publication; it applies to dry-run too.
//   capture-5 — G5 raw-LHR seam: captureRawLhr() returns the unmodified raw
//               LHR (identity) plus provenance for future G5 publishers.
//               Validates URL + malformed runner output BEFORE returning.
//               Additive — capture()'s existing G4 runner path stays intact
//               (no rerouting through the seam). Forwarding manifestEntry by
//               reference lets future G5 publishers correlate raw LHRs with
//               the corpus manifest entry that drove the capture.
// See tools/g4-capture/README.md.

import { existsSync, mkdirSync, renameSync, rmSync } from "node:fs";
import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { dirname, isAbsolute, relative, resolve } from "node:path";
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
  // Capture-integrity contract: every entry must pin a non-empty DOM marker.
  // An empty marker would let verifyTarget silently skip the check and defeat
  // the integrity guard, so we refuse the manifest up front.
  const marker = entry.expectedDOMMarker;
  if (typeof marker !== "string" || marker.length === 0) {
    fail("manifest entry missing expectedDOMMarker", { url });
  }
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

// `captureRawLhr()` is the G5 raw-LHR seam: a no-I/O helper that drives an
// injected runner, returns the unmodified raw LHR BY IDENTITY plus provenance
// parsed from it, and rejects missing url / malformed runner output BEFORE
// returning. The optional `manifestEntry` is forwarded to the runner by
// reference (the seam does not inspect it) so future G5 publishers can
// correlate raw LHRs with the corpus manifest entry that drove the capture.
// Additive — the dry-run + G4 mapped evidence paths are untouched.
export async function captureRawLhr({
  url,
  runLighthouse: runLighthouseFn,
  manifestEntry,
} = {}) {
  if (!url || typeof url !== "string") {
    throw new Error("captureRawLhr: url is required");
  }
  if (typeof runLighthouseFn !== "function") {
    throw new Error("captureRawLhr: runLighthouse must be a function");
  }
  const lhr = await runLighthouseFn({ url, manifestEntry });
  if (!lhr || typeof lhr !== "object" || Array.isArray(lhr)) {
    throw new Error(
      "captureRawLhr: runner returned malformed output (expected non-array object)",
    );
  }
  const provenance = buildProvenance({
    lighthouseVersion: lhr.lighthouseVersion ?? "unknown",
    chromeVersion: lhr.userAgent
      ? chromeVersionFromUserAgent(lhr.userAgent)
      : "unknown",
  });
  return { lhr, provenance };
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

// `verifyTarget()` re-fetches the capture URL and re-checks status, raw
// response sha256, and a declared DOM marker against the corpus manifest.
// Throws on any mismatch so the caller can fail closed BEFORE invoking the
// Lighthouse runner or publishing evidence. `fetchFn` is injectable so
// hermetic tests can exercise all failure modes without a live server.
export async function verifyTarget({ url, entry, fetchFn = globalThis.fetch }) {
  if (!entry || typeof entry !== "object") {
    throw new Error("verifyTarget: entry required");
  }
  const expectedStatus = entry.expectedStatus ?? 200;
  const expectedSha = entry.expectedContentSha256;
  const expectedMarker = entry.expectedDOMMarker;
  if (typeof expectedSha !== "string" || expectedSha.length === 0) {
    throw new Error(
      "verifyTarget: entry.expectedContentSha256 required (got empty)",
    );
  }
  let response;
  try {
    response = await fetchFn(url);
  } catch (err) {
    const msg = err && err.message ? err.message : String(err);
    throw new Error(`verifyTarget: fetch failed for ${url}: ${msg}`);
  }
  if (!response || typeof response.status !== "number") {
    throw new Error(
      `verifyTarget: invalid response for ${url} (missing status)`,
    );
  }
  if (response.status !== expectedStatus) {
    throw new Error(
      `verifyTarget: status mismatch for ${url}: expected ${expectedStatus}, got ${response.status}`,
    );
  }
  const buf = new Uint8Array(await response.arrayBuffer());
  const sha = createHash("sha256").update(buf).digest("hex");
  if (sha !== expectedSha) {
    throw new Error(
      `verifyTarget: sha256 mismatch for ${url}: expected ${expectedSha}, got ${sha}`,
    );
  }
  // validateManifest() already refuses an empty marker, so reaching this
  // branch with `expectedMarker` falsy would mean the validator was
  // bypassed. Defensive no-op in that case.
  if (
    expectedMarker &&
    !new TextDecoder("utf-8").decode(buf).includes(expectedMarker)
  ) {
    throw new Error(
      `verifyTarget: DOM marker ${JSON.stringify(expectedMarker)} not found in ${url}`,
    );
  }
}

// Reject any file name whose resolved path escapes the staging dir —
// absolute paths and `../`-ladder names would otherwise let evidence files
// be written outside `outDir` and breach the atomic-write contract.
function _resolveUnderStaging(stagingRoot, name) {
  if (!name || typeof name !== "string") {
    throw new Error(`atomicWrite: file name must be a non-empty string`);
  }
  if (isAbsolute(name)) {
    throw new Error(
      `atomicWrite: file name must be relative: ${JSON.stringify(name)}`,
    );
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

export async function atomicWrite(outDir, files, { rename = renameSync } = {}) {
  // Selective atomicWrite: replace only the payload-named files in
  // `outDir`, leaving any unrelated files (e.g. reports emitted by an
  // earlier producer under `make parity`) byte-for-byte untouched.
  // Strategy:
  //   1. Validate every payload name (path-traversal rejection) up
  //      front so a bad name throws before any filesystem mutation.
  //   2. For each payload name, relocate any pre-existing outDir/<name>
  //      to a per-file .bak- sibling so it can be restored on failure.
  //      Unrelated files in outDir are NOT moved.
  //   3. Stage the new payload in a sibling tmp dir under its final
  //      names, then rename each staged file into outDir (creating
  //      outDir if it does not exist yet). renameSync is atomic on the
  //      same filesystem, so each file is either fully-prior or
  //      fully-new — a partial write is impossible to observe.
  //   4. On failure: remove any staged-renames that already succeeded,
  //      then restore every per-file backup. Unrelated files are never
  //      touched.
  //   5. On success: drop the per-file backups and the tmp staging dir.
  // `rename` is injectable so tests can simulate a failed staged-rename.
  const names = Object.keys(files);
  // Up-front name validation — throws before touching the filesystem.
  for (const name of names) {
    _resolveUnderStaging(outDir, name);
  }
  const tmp = `${outDir}.tmp-${process.pid}-${Date.now()}`;
  // Per-file backups: outDir/<name> → outDir/<name>.bak-<pid>-<ts>
  // for each payload name that already exists. Unrelated files are
  // never touched.
  const backups = []; // [{originalPath, backupPath}]
  if (existsSync(outDir)) {
    try {
      for (const name of names) {
        const targetPath = resolve(outDir, name);
        if (existsSync(targetPath)) {
          const backupPath = `${targetPath}.bak-${process.pid}-${Date.now()}`;
          rename(targetPath, backupPath);
          backups.push({ originalPath: targetPath, backupPath });
        }
      }
    } catch (err) {
      // Mid-loop backup failure: restore every backup already taken,
      // then propagate the original error.
      for (const { originalPath, backupPath } of backups) {
        try {
          rename(backupPath, originalPath);
        } catch {}
      }
      throw err;
    }
  }
  // `stagedRenames` tracks names whose staged file has already been
  // moved into outDir — on failure, these new files must be removed
  // so the backup-restore path can leave outDir in its prior state.
  const stagedRenames = [];
  try {
    // Stage every payload file in a sibling tmp dir under its final name.
    mkdirSync(tmp, { recursive: true });
    for (const [name, content] of Object.entries(files)) {
      const p = _resolveUnderStaging(tmp, name);
      mkdirSync(dirname(p), { recursive: true });
      await writeFile(p, content, "utf8");
    }
    // Atomically move each staged file into outDir (creating outDir
    // if it does not exist yet).
    mkdirSync(outDir, { recursive: true });
    for (const name of names) {
      const stagedPath = _resolveUnderStaging(tmp, name);
      const finalPath = resolve(outDir, name);
      rename(stagedPath, finalPath);
      stagedRenames.push(name);
    }
  } catch (err) {
    // Failure path: undo staged renames (remove new files written
    // under payload names), then restore every per-file backup.
    for (const name of stagedRenames) {
      try {
        rmSync(resolve(outDir, name), { recursive: true, force: true });
      } catch {}
    }
    for (const { originalPath, backupPath } of backups) {
      try {
        if (existsSync(originalPath)) {
          rmSync(originalPath, { recursive: true, force: true });
        }
        rename(backupPath, originalPath);
      } catch {}
    }
    try {
      if (existsSync(tmp)) rmSync(tmp, { recursive: true, force: true });
    } catch {}
    throw err;
  }
  // Success path: drop per-file backups and the tmp staging dir.
  for (const { backupPath } of backups) {
    try {
      rmSync(backupPath, { recursive: true, force: true });
    } catch {}
  }
  try {
    if (existsSync(tmp)) rmSync(tmp, { recursive: true, force: true });
  } catch {}
}

export async function capture({
  url,
  manifest,
  outDir,
  dryRun,
  runLighthouse: runLighthouseFn,
  now = () => new Date().toISOString(),
  logger = log,
  fetchFn = globalThis.fetch,
}) {
  const entry = validateManifest(manifest, url);
  // Pre-runner verification (capture-3): re-fetch the target URL and
  // re-check status + raw sha256 + DOM marker against the corpus manifest
  // BEFORE invoking the Lighthouse runner or publishing evidence. This is
  // the integrity guard against a stale or drifting web/index.html — if
  // any check fails, throws so the runner is NEVER invoked and atomicWrite
  // is NEVER called. Applies to dry-run too.
  await verifyTarget({ url, entry, fetchFn });
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
