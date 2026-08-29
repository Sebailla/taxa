#!/usr/bin/env node
/**
 * Emit a build profile JSON for the migrated Next.js frontend.
 *
 * PR 1 (evidence-only slice) introduces this tooling + the profile
 * schema. The actual `next build` output is produced by PR 3; this
 * script reads whatever build directory is on disk and writes
 * `web/dist/build-profile.json` with the schema pinned in
 * `openspec/changes/migrate-nextjs-tailwind4/tasks.md` §Phase 1
 * (1.1) and `design.md` §Architecture Decisions (Build profile row):
 *
 *     {
 *       "chunks":          [{ path: string, bytes: int, route?: string }, ...],
 *       "total_bytes":     int,
 *       "per_route_bytes": { "/": int, ... }
 *     }
 *
 * Usage:
 *     node scripts/emit_build_profile.mjs <build-dir> [output-path]
 *     node scripts/emit_build_profile.mjs --help
 *
 * Output path:
 *     - Explicit `[output-path]` argument wins.
 *     - Else $BUILD_PROFILE_OUT_DIR/build-profile.json (CI override).
 *     - Else web/dist/build-profile.json relative to repo root.
 *
 * Failure modes (all exit non-zero with a stderr message):
 *     - Missing build dir
 *     - Build dir exists but contains zero bytes of content
 *     - Output path is not writable
 *
 * Reference:
 *     openspec/changes/migrate-nextjs-tailwind4/tasks.md  §Phase 1  (1.1)
 *     openspec/changes/migrate-nextjs-tailwind4/design.md §Architecture Decisions
 */
import { readdir, stat, writeFile, mkdir, access, constants } from "node:fs/promises";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------
function usage() {
  process.stdout.write(
    [
      "usage: emit_build_profile.mjs <build-dir> [output-path]",
      "",
      "  <build-dir>    Path to the Next.js output directory (e.g. out/ or .next/).",
      "                 The script walks it recursively, summing bytes per file.",
      "  [output-path]  Where to write build-profile.json. Default:",
      "                 $BUILD_PROFILE_OUT_DIR/build-profile.json, or",
      "                 web/dist/build-profile.json (repo-root relative).",
      "",
      "Exits non-zero if <build-dir> is missing or empty.",
      "",
    ].join("\n"),
  );
}

const argv = process.argv.slice(2);
if (argv.length === 0 || argv.includes("-h") || argv.includes("--help")) {
  usage();
  process.exit(0);
}

const buildDir = argv[0];
const explicitOut = argv[1];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
async function exists(p) {
  try {
    await access(p, constants.R_OK);
    return true;
  } catch {
    return false;
  }
}

async function listFiles(root) {
  /** Recursively yield every regular file under `root`. */
  const out = [];
  async function walk(dir) {
    let entries;
    try {
      entries = await readdir(dir, { withFileTypes: true });
    } catch (err) {
      throw new Error(`cannot read ${dir}: ${err.message}`);
    }
    for (const entry of entries) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) {
        await walk(full);
      } else if (entry.isFile()) {
        out.push(full);
      }
      // Symlinks / devices ignored deliberately: deterministic walk only.
    }
  }
  await walk(root);
  return out;
}

/**
 * Map a chunk path (relative to build dir) to a logical route name.
 *
 * Heuristic — Next.js's static export puts the per-route HTML at
 * `<root>/<route>/index.html` and shared assets under `_next/static/`.
 * Underscore-prefixed paths (e.g. `_next/...`) are framework chrome and
 * roll up under `/`.
 *
 * Pinned here so PR 3's emitted profile matches the schema reviewers
 * already validated against this script.
 */
function routeOf(relPath) {
  const parts = relPath.split(sep);
  const first = parts[0];
  if (first && first.startsWith("_")) {
    return "/";
  }
  // If the path is `<route>/index.html`, the route is `<route>` (or "/").
  const idx = parts.indexOf("index.html");
  if (idx > 0) {
    const routeParts = parts.slice(0, idx);
    return "/" + routeParts.join("/");
  }
  return "/";
}

// ---------------------------------------------------------------------------
// Walk + compute
// ---------------------------------------------------------------------------
async function main() {
  if (!(await exists(buildDir))) {
    process.stderr.write(
      `[emit_build_profile] build dir not found or unreadable: ${buildDir}\n`,
    );
    process.exit(2);
  }
  const buildStat = await stat(buildDir);
  if (!buildStat.isDirectory()) {
    process.stderr.write(
      `[emit_build_profile] not a directory: ${buildDir}\n`,
    );
    process.exit(2);
  }

  const files = await listFiles(buildDir);
  if (files.length === 0) {
    process.stderr.write(
      `[emit_build_profile] build dir is empty: ${buildDir}\n` +
        `  (refusing to emit an empty profile; verify next build succeeded)\n`,
    );
    process.exit(3);
  }

  const chunks = [];
  let totalBytes = 0;
  const perRouteBytes = {};

  for (const absPath of files) {
    const s = await stat(absPath);
    const relPath = relative(buildDir, absPath);
    const route = routeOf(relPath);
    const descriptor = {
      path: relPath,
      bytes: s.size,
      route,
    };
    chunks.push(descriptor);
    totalBytes += s.size;
    perRouteBytes[route] = (perRouteBytes[route] ?? 0) + s.size;
  }

  // Stable ordering: sort chunks by path so the JSON diff is reviewable.
  chunks.sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
  const perRouteSorted = Object.fromEntries(
    Object.entries(perRouteBytes).sort(([a], [b]) =>
      a < b ? -1 : a > b ? 1 : 0,
    ),
  );

  const profile = {
    chunks,
    total_bytes: totalBytes,
    per_route_bytes: perRouteSorted,
    build_dir: buildDir,
    emitted_at: new Date().toISOString(),
  };

  // Resolve output path: explicit arg > env override > repo-root default.
  let outputPath;
  if (explicitOut) {
    outputPath = explicitOut;
  } else if (process.env.BUILD_PROFILE_OUT_DIR) {
    outputPath = join(process.env.BUILD_PROFILE_OUT_DIR, "build-profile.json");
  } else {
    const repoRoot = fileURLToPath(new URL("../", import.meta.url));
    outputPath = join(repoRoot, "web", "dist", "build-profile.json");
  }

  await mkdir(join(outputPath, ".."), { recursive: true });
  await writeFile(outputPath, JSON.stringify(profile, null, 2) + "\n", "utf8");
  process.stdout.write(
    `[emit_build_profile] wrote ${outputPath} ` +
      `(chunks=${chunks.length} total_bytes=${totalBytes} routes=${
        Object.keys(perRouteSorted).length
      })\n`,
  );
}

main().catch((err) => {
  process.stderr.write(`[emit_build_profile] fatal: ${err.message}\n`);
  if (err.stack) process.stderr.write(err.stack + "\n");
  process.exit(1);
});