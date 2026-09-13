#!/usr/bin/env node
// scripts/generate_g4_candidate_manifest.mjs — G4 candidate manifest producer.
// Emits a single-entry `taxa.g4-capture.manifest/1` describing the candidate
// static-export HTML, pinned to its raw SHA-256 and to a canonical DOM probe
// marker that the downstream capture.mjs verifier uses to detect drift.
//
//   --html  Existing HTML file (e.g. out/index.html) — must be a regular file.
//   --url   Absolute http(s) candidate URL the entry pins.
//   --out   Target manifest path. Refuses to overwrite an existing file.
//
// Validation runs UPFRONT, before any parent directory is created or any
// staging file is written. Published atomically via temp + rename so a mid-
// write failure never yields a partial manifest at --out. Test-only hook
// `G4_CANDIDATE_FAIL_AT=write|rename` lets the hermetic test suite exercise
// the atomic-publish failure path without relaxing any product-side
// validation — the hook only injects failure into the very last stage, after
// every other guard has already passed.

import {
  existsSync, mkdirSync, readFileSync, renameSync, rmSync, statSync, writeFileSync,
} from "node:fs";
import { createHash } from "node:crypto";
import {
  basename, dirname, isAbsolute, relative, resolve, sep,
} from "node:path";

const SCHEMA = "taxa.g4-capture.manifest/1";
const MARKER = 'data-testid="g4-probe-marker"';
const TEST_HOOK = "G4_CANDIDATE_FAIL_AT";

const TAG = "[generate-g4-candidate-manifest]";
const log = (...a) => console.log(TAG, ...a);

function fail(msg, ctx) {
  console.error(`${TAG} FAIL: ${msg}`,
    ctx !== undefined ? JSON.stringify(ctx) : "");
  process.exit(1);
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === "--html") args.html = argv[++i];
    else if (k === "--url") args.url = argv[++i];
    else if (k === "--out") args.out = argv[++i];
    else fail(`unknown argument: ${k}`);
  }
  for (const k of ["html", "url", "out"]) {
    if (typeof args[k] !== "string" || args[k].length === 0) {
      fail(`missing or empty --${k}`);
    }
  }
  return args;
}

function validateUrl(u) {
  let parsed;
  try { parsed = new URL(u); }
  catch { fail(`--url must be an absolute http(s) URL; got ${JSON.stringify(u)}`); }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    fail(`--url must be an absolute http(s) URL; got ${JSON.stringify(u)}`);
  }
}

// POSIX-relative HTML path under cwd when possible; basename fallback otherwise.
function relativeHtmlPath(htmlAbsPath) {
  const rel = relative(process.cwd(), htmlAbsPath);
  if (!rel || rel === "" || rel.startsWith("..") || isAbsolute(rel)) {
    return basename(htmlAbsPath).split(sep).join("/");
  }
  return rel.split(sep).join("/");
}

function readRawHtml(htmlArg) {
  let abs;
  try { abs = resolve(htmlArg); }
  catch (err) { fail(`--html unresolvable: ${JSON.stringify(htmlArg)}`, { error: err.message }); }
  let raw;
  try {
    const st = statSync(abs);
    if (!st.isFile()) fail(`--html is not a regular file: ${JSON.stringify(htmlArg)}`);
    raw = readFileSync(abs); // raw bytes; do NOT pass an encoding
  } catch (err) {
    if (err && err.code === "ENOENT") fail(`--html not found: ${JSON.stringify(htmlArg)}`);
    fail(`--html unreadable: ${JSON.stringify(htmlArg)}`, { error: err.message });
  }
  return { abs, raw };
}

function buildEntry({ url, htmlAbsPath, rawBytes }) {
  return {
    url,
    path: relativeHtmlPath(htmlAbsPath),
    expectedContentSha256: createHash("sha256").update(rawBytes).digest("hex"),
    expectedStatus: 200,
    expectedDOMMarker: MARKER,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  // Run every gate BEFORE creating parents or staging any file.
  validateUrl(args.url);
  const { abs: htmlAbsPath, raw: rawHtmlBytes } = readRawHtml(args.html);
  const u8 = rawHtmlBytes instanceof Uint8Array ? rawHtmlBytes : Buffer.from(rawHtmlBytes);
  if (!u8.includes(Buffer.from(MARKER, "utf8"))) {
    fail(`--html raw bytes lack the exact marker ${JSON.stringify(MARKER)}`);
  }
  let outAbsPath;
  try { outAbsPath = resolve(args.out); }
  catch (err) { fail(`--out unresolvable: ${JSON.stringify(args.out)}`, { error: err.message }); }
  if (existsSync(outAbsPath)) {
    fail(`--out already exists; refusing to overwrite: ${JSON.stringify(args.out)}`);
  }
  const entry = buildEntry({ url: args.url, htmlAbsPath, rawBytes: u8 });
  const payload = `${JSON.stringify({ schema: SCHEMA, entries: [entry] }, null, 2)}\n`;
  // All validation has passed. NOW we may touch the filesystem beyond --html.
  const tmp = `${outAbsPath}.tmp-${process.pid}-${Date.now()}`;
  mkdirSync(dirname(outAbsPath), { recursive: true });
  const failAt = process.env[TEST_HOOK];
  if (failAt === "write") throw new Error(`${TEST_HOOK}=write (test-injected)`);
  writeFileSync(tmp, payload);
  if (failAt === "rename") {
    try { rmSync(tmp, { force: true }); } catch {}
    throw new Error(`${TEST_HOOK}=rename (test-injected)`);
  }
  renameSync(tmp, outAbsPath);
  log(`wrote ${outAbsPath}`);
}

main().catch((err) => {
  console.error(err && err.message ? err.message : String(err));
  process.exit(1);
});