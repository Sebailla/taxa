#!/usr/bin/env node
// Node runtime guard for `make api`. Reads package.json::engines.node and exits 1
// if process.versions.node is below the floor. Refactored in 3a.8 to read the
// floor dynamically — a future bump is a single-file change.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const pkg = JSON.parse(readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "..", "package.json"), "utf8"));
const SPEC = pkg?.engines?.node;
if (typeof SPEC !== "string" || !SPEC.trim()) {
  console.error("[check-runtime] package.json::engines.node is missing or empty");
  process.exit(1);
}

// Parse the floor out of any semver-shaped range spec (>=X.Y.Z, ^X.Y.Z, X.Y.Z, X.Y).
const bare = String(SPEC).trim().replace(/^[~^]/, "");
const FLOOR = bare.match(/>=?\s*(\d+(?:\.\d+)*)/)?.[1] ?? bare.match(/^(\d+(?:\.\d+)*)/)?.[1];
if (!FLOOR) throw new Error(`cannot parse floor from ${JSON.stringify(SPEC)}`);
const observed = process.versions.node.replace(/^v/, "").split(".").map(Number);
const required = FLOOR.split(".").map(Number);
let cmp = 0;
for (let i = 0; i < 3; i++) {
  if (observed[i] !== required[i]) { cmp = observed[i] > required[i] ? 1 : -1; break; }
}
if (cmp < 0) {
  console.error(`[check-runtime] Node ${process.versions.node} is below the required ${FLOOR} floor (package.json::engines.node = ${JSON.stringify(SPEC)}). Upgrade Node per .nvmrc.`);
  process.exit(1);
}
console.log(`[check-runtime] Node ${process.versions.node} >= ${FLOOR} OK (engines.node = ${JSON.stringify(SPEC)})`);
process.exit(0);