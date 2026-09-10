#!/usr/bin/env node
// Node runtime guard for `make api` (PR 3d handoff).
//
// Reads package.json::engines.node and exits 1 if process.versions.node is
// below the floor. Refactored in 3a.8 to read the floor dynamically — a future
// bump is a single-file change. 3d adds:
//
//   1. Pure parser functions (`parseFloor`, `parseVersion`, `compareVersions`)
//      extracted so the comparison can be table-driven without dependency install
//      and without spawning a subprocess.
//   2. A `--selftest` mode that runs the canonical 3d edge matrix
//      (20.8.0 reject; 20.9.0 / 20.10.0 / 22.0.0 / v26.8.1 accept) against the
//      pure parser and prints per-case OK/FAIL. Exits 0 if every case matches
//      the expected disposition, 1 otherwise.
//   3. A machine-readable error code on stderr
//      (`[check-runtime] code=NODE_BELOW_FLOOR required=<X.Y.Z> actual=<vA.B.C>
//      message=<human>`) so callers / CI can grep the structured fields
//      without parsing free-form prose.
//
// The CLI flow (default invocation) is unchanged from 3a.8 — only the
// rejection-line format gains the `code=NODE_BELOW_FLOOR required=... actual=...`
// prefix.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Parse the floor triple out of any semver-shaped range spec
 * (`>=X.Y.Z`, `^X.Y.Z`, `X.Y.Z`, `X.Y`). Pure — no I/O.
 *
 * @param {unknown} spec  The raw `package.json::engines.node` value.
 * @returns {string}      The floor triple as a dotted string (e.g. `"20.9.0"`).
 */
export function parseFloor(spec) {
  if (typeof spec !== "string" || !spec.trim()) {
    throw new Error("package.json::engines.node is missing or empty");
  }
  const bare = String(spec).trim().replace(/^[~^]/, "");
  const FLOOR =
    bare.match(/>=?\s*(\d+(?:\.\d+)*)/)?.[1] ??
    bare.match(/^(\d+(?:\.\d+)*)/)?.[1];
  if (!FLOOR) throw new Error(`cannot parse floor from ${JSON.stringify(spec)}`);
  return FLOOR;
}

/**
 * Parse a Node version string (`"20.9.0"`, `"v26.8.1"`) into a 3-tuple of
 * numbers. Missing trailing parts become 0 (so `"20"` → `[20, 0, 0]`). Pure.
 *
 * @param {string} s  A version string, optionally prefixed with `v`.
 * @returns {[number, number, number]}
 */
export function parseVersion(s) {
  return String(s).replace(/^v/, "").split(".").map((n) => Number(n) || 0);
}

/**
 * Compare a required floor against an observed version. Pure.
 *
 * @returns {-1 | 0 | 1}  -1 if observed<required, 0 if equal, 1 if observed>required.
 */
export function compareVersions(required, observed) {
  const r = parseVersion(required);
  const o = parseVersion(observed);
  let cmp = 0;
  for (let i = 0; i < 3; i++) {
    if (o[i] !== r[i]) {
      cmp = o[i] > r[i] ? 1 : -1;
      break;
    }
  }
  return cmp;
}

// CLI / selftest dispatch. Runs only when this module is the entry point
// (i.e. invoked directly by `node scripts/check-runtime.mjs ...`).
const isMain = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain && process.argv.includes("--selftest")) {
  // Canonical 3d edge matrix for the pure parser. Run without dependency
  // install and without spawning a subprocess.
  const FLOOR = "20.9.0";
  const CASES = [
    { version: "20.8.0",  expect: "reject" },
    { version: "20.9.0",  expect: "accept" },
    { version: "20.10.0", expect: "accept" },
    { version: "22.0.0",  expect: "accept" },
    { version: "v26.8.1", expect: "accept" },
  ];
  let failed = 0;
  for (const c of CASES) {
    const cmp = compareVersions(FLOOR, c.version);
    const observed = cmp < 0 ? "reject" : "accept";
    const ok = observed === c.expect;
    console.log(`[check-runtime selftest] floor=${FLOOR} version=${c.version} expected=${c.expect} observed=${observed} ${ok ? "OK" : "FAIL"}`);
    if (!ok) failed++;
  }
  if (failed > 0) {
    console.error(`[check-runtime selftest] code=SELFTEST_FAILED failed=${failed} total=${CASES.length}`);
    process.exit(1);
  }
  console.log(`[check-runtime selftest] code=SELFTEST_PASSED cases=${CASES.length}`);
  process.exit(0);
}

if (isMain) {
  const pkg = JSON.parse(readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "..", "package.json"), "utf8"));
  const SPEC = pkg?.engines?.node;
  let FLOOR;
  try {
    FLOOR = parseFloor(SPEC);
  } catch (err) {
    console.error(`[check-runtime] code=ENGINES_NODE_MISSING message=${err?.message ?? err}`);
    process.exit(1);
  }
  const observedRaw = process.versions.node;
  const cmp = compareVersions(FLOOR, observedRaw);
  if (cmp < 0) {
    console.error(
      `[check-runtime] code=NODE_BELOW_FLOOR required=${FLOOR} actual=${observedRaw} ` +
      `message=Node ${observedRaw} is below the required ${FLOOR} floor ` +
      `(package.json::engines.node = ${JSON.stringify(SPEC)}). Upgrade Node per .nvmrc.`
    );
    process.exit(1);
  }
  console.log(
    `[check-runtime] code=OK required=${FLOOR} actual=${observedRaw} ` +
    `engines.node=${JSON.stringify(SPEC)} message=Node ${observedRaw} >= ${FLOOR}`
  );
  process.exit(0);
}
