#!/usr/bin/env node
// scripts/generate_g4_candidate_manifest.mjs
//
// Offline G4 candidate-manifest generator (approved issue #246).
//
// Validates an already-built candidate HTML file and a candidate URL,
// then atomically writes a strict manifest with schema
// `taxa.g4-capture.manifest/1` whose single entry carries every
// consumer-required field for `tools/g4-capture/scripts/capture.mjs`:
//   - url                  (literal --candidate-url value, no normalization)
//   - path                 (HTML basename; mirrors corpus fixture convention)
//   - expectedContentSha256 (raw HTML bytes sha256, hex)
//   - expectedStatus       (200, pinned)
//   - expectedDOMMarker    (`data-testid="g4-probe-marker"`, pinned)
//
// The script is OFFLINE: it never starts a server, never builds Next,
// never installs dependencies. It reads the HTML from disk, validates,
// computes the hash, writes the manifest, exits.
//
// Usage:
//   node scripts/generate_g4_candidate_manifest.mjs \
//     --candidate-html <path> \
//     --candidate-url  <http(s) URL> \
//     --candidate-manifest <output path>
//
// Failure modes (all exit 1 BEFORE writing the manifest or running any
// downstream producer):
//   * Missing/unknown CLI flag.
//   * HTML file missing or empty.
//   * HTML file missing the literal `data-testid="g4-probe-marker"`
//     substring (the same gate `capture.mjs::verifyTarget` enforces).
//   * Candidate URL is not a clean http(s) URL (rejects file://,
//     javascript:, data:, ws://, ftp://, empty string, unparseable).
//
// Atomic write: the manifest is written to a sibling `.tmp-<pid>-<ts>`
// file, then `rename`'d to its final path. Pre-existing files in the
// same directory are NEVER touched. The parent directory is created
// if missing.
//
// Reference: odd/tasks/g4-candidate-manifest-develop.md.

import { readFile, writeFile, mkdir, rename, access, constants } from "node:fs/promises";
import { createHash } from "node:crypto";
import { basename, dirname, resolve } from "node:path";

const MANIFEST_SCHEMA = "taxa.g4-capture.manifest/1";
const EXPECTED_STATUS = 200;
const EXPECTED_DOM_MARKER = 'data-testid="g4-probe-marker"';

// Pinned CLI flag set; unknown flags fail closed.
const KNOWN_FLAGS = new Set([
  "--candidate-html",
  "--candidate-url",
  "--candidate-manifest",
]);

const fail = (msg, ctx) => {
  const suffix = ctx ? " " + JSON.stringify(ctx) : "";
  console.error(`[generate-g4-candidate-manifest] FAIL: ${msg}${suffix}`);
  process.exit(1);
};

const log = (...a) => console.log("[generate-g4-candidate-manifest]", ...a);

// ---------------------------------------------------------------------------
// CLI parsing
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const args = { _: [], known: {} };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k.startsWith("--")) {
      if (!KNOWN_FLAGS.has(k)) {
        fail("unknown flag", { flag: k });
      }
      const v = argv[++i];
      if (v === undefined) {
        fail("flag requires a value", { flag: k });
      }
      args.known[k.slice(2)] = v;
    } else {
      args._.push(k);
    }
  }
  return args;
}

function requireFlags(args) {
  for (const k of ["candidate-html", "candidate-url", "candidate-manifest"]) {
    if (typeof args.known[k] !== "string" || args.known[k].length === 0) {
      fail(`missing --${k}`);
    }
  }
}

// ---------------------------------------------------------------------------
// HTML validation
// ---------------------------------------------------------------------------

async function validateHtml(htmlPath) {
  let buf;
  try {
    await access(htmlPath, constants.R_OK);
  } catch (err) {
    fail("candidate HTML is not readable", {
      path: htmlPath,
      error: err.message,
    });
  }
  try {
    buf = await readFile(htmlPath);
  } catch (err) {
    fail("cannot read candidate HTML", {
      path: htmlPath,
      error: err.message,
    });
  }
  if (!buf || buf.length === 0) {
    fail("candidate HTML is empty", { path: htmlPath });
  }
  const text = new TextDecoder("utf-8", { fatal: false }).decode(buf);
  if (!text.includes(EXPECTED_DOM_MARKER)) {
    fail("candidate HTML missing the G4 probe marker", {
      path: htmlPath,
      marker: EXPECTED_DOM_MARKER,
    });
  }
  return buf;
}

// ---------------------------------------------------------------------------
// URL validation (clean HTTP(S))
// ---------------------------------------------------------------------------

function validateUrl(rawUrl) {
  if (typeof rawUrl !== "string" || rawUrl.length === 0) {
    fail("candidate URL must be a non-empty string");
  }
  // Reject whitespace + control characters up front — the WHATWG URL
  // parser is permissive about some whitespace, but a capture-time URL
  // with hidden control bytes would never resolve consistently.
  // eslint-disable-next-line no-control-regex
  if (/[\s\u0000-\u001f\u007f]/.test(rawUrl)) {
    fail("candidate URL contains whitespace or control characters", {
      url: rawUrl,
    });
  }
  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch (err) {
    fail("candidate URL is not parseable", {
      url: rawUrl,
      error: err.message,
    });
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    fail("candidate URL must be clean HTTP(S)", {
      url: rawUrl,
      got: parsed.protocol,
    });
  }
  // Reject URLs with credentials embedded — capture-time must be
  // anonymous so evidence provenance stays unambiguous.
  if (parsed.username || parsed.password) {
    fail("candidate URL must not embed credentials", { url: rawUrl });
  }
  return rawUrl;
}

// ---------------------------------------------------------------------------
// Manifest construction
// ---------------------------------------------------------------------------

function buildManifest({ url, htmlPath, sha256Hex }) {
  return {
    schema: MANIFEST_SCHEMA,
    entries: [
      {
        url,
        path: basename(htmlPath),
        expectedContentSha256: sha256Hex,
        expectedStatus: EXPECTED_STATUS,
        expectedDOMMarker: EXPECTED_DOM_MARKER,
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// Atomic write — only the named manifest is published
// ---------------------------------------------------------------------------

async function atomicWriteManifest(manifestPath, manifest) {
  const absPath = resolve(manifestPath);
  const parent = dirname(absPath);
  await mkdir(parent, { recursive: true });
  const tmp = `${absPath}.tmp-${process.pid}-${Date.now()}`;
  try {
    await writeFile(tmp, JSON.stringify(manifest, null, 2) + "\n", "utf8");
    await rename(tmp, absPath);
  } catch (err) {
    // Best-effort cleanup of the staged tmp on failure.
    try {
      const { unlink } = await import("node:fs/promises");
      await unlink(tmp);
    } catch {
      // tmp may already be gone or never created; swallow.
    }
    fail("cannot write manifest", {
      path: absPath,
      error: err.message,
    });
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const args = parseArgs(process.argv.slice(2));
  requireFlags(args);
  const htmlPath = args.known["candidate-html"];
  const url = validateUrl(args.known["candidate-url"]);
  const manifestPath = args.known["candidate-manifest"];

  const buf = await validateHtml(htmlPath);
  const sha256Hex = createHash("sha256").update(buf).digest("hex");
  const manifest = buildManifest({ url, htmlPath, sha256Hex });
  await atomicWriteManifest(manifestPath, manifest);
  log(`wrote manifest to ${manifestPath}`);
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : err);
  process.exit(1);
});
