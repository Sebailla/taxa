#!/usr/bin/env node
// tools/g4-capture/scripts/g5_raw_lhr_bridge.mjs — G5 raw-LHR bridge.
//
// ESM bridge around captureRawLhr (capture.mjs) that returns a single
// JSON-safe envelope: { schema, url, lhr, provenance } where:
//   - schema = "taxa.g5-raw-lhr.envelope/1"
//   - lhr is the runner's raw LHR BY IDENTITY (unmodified, unnormalized)
//   - provenance is parsed by captureRawLhr (node/lighthouse/chrome)
//
// The library seam accepts an injected runner so tests never launch
// Lighthouse/Chrome. The one-shot CLI accepts only --url <url>, emits
// exactly one JSON object on stdout, and writes errors to stderr with a
// nonzero exit code on invalid args or runner failure.
//
// No files are written, no server is started, no corpus validation runs,
// no categories are mapped, and no Python is imported. Additive — the G4
// evidence contract and the capture.mjs surface stay untouched.

import {
  captureRawLhr,
  runLighthouse as defaultRunLighthouse,
} from "./capture.mjs";

const ENVELOPE_SCHEMA = "taxa.g5-raw-lhr.envelope/1";

// Accepts ONLY --url. Missing/empty/duplicate --url and any other flag
// throw a deterministic error fragment. No --manifest, --out, --dry-run,
// --iterations, or any other capture-surface flag is accepted here.
export function parseBridgeArgs(argv) {
  let url = null;
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === "--url") {
      if (url !== null) throw new Error("--url specified more than once");
      const v = argv[++i];
      if (typeof v !== "string" || v.length === 0) {
        throw new Error("--url requires a non-empty value");
      }
      url = v;
    } else {
      throw new Error(`unknown argument: ${k}`);
    }
  }
  if (url === null) throw new Error("missing --url");
  return { url };
}

// Build the canonical G5 raw-LHR envelope. Reuses captureRawLhr for LHR
// validation, version parsing, and provenance construction — no duplicated
// logic. The runner parameter is the injectable seam (defaults to the
// real runLighthouse from capture.mjs).
export async function buildLhrEnvelope({
  url,
  runLighthouse = defaultRunLighthouse,
  manifestEntry,
} = {}) {
  const { lhr, provenance } = await captureRawLhr({
    url,
    runLighthouse,
    manifestEntry,
  });
  return { schema: ENVELOPE_SCHEMA, url, lhr, provenance };
}

// CLI entry point. Parses argv, builds the envelope via the injected
// runLighthouse seam, and emits exactly one JSON object on stdout. Any
// failure surfaces to stderr with a nonzero exit code. process.exit is
// monkey-patchable via the optional deps parameter for hermetic tests.
export async function main(
  argv = process.argv.slice(2),
  { runLighthouse = defaultRunLighthouse, exit = process.exit } = {},
) {
  let args;
  try {
    args = parseBridgeArgs(argv);
  } catch (err) {
    process.stderr.write(`[g5-bridge] FAIL: ${err.message}\n`);
    exit(1);
    return;
  }
  let envelope;
  try {
    envelope = await buildLhrEnvelope({ url: args.url, runLighthouse });
  } catch (err) {
    const msg = err && err.message ? err.message : String(err);
    process.stderr.write(`[g5-bridge] FAIL: ${msg}\n`);
    exit(1);
    return;
  }
  process.stdout.write(`${JSON.stringify(envelope)}\n`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
