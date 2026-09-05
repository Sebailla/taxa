"""Focused tests for the G4 capture producer (slice 1 + capture-2).

Scope (parent task — capture-only URL-parametrized producer; isolated pinned
Node/Lighthouse workspace; minimal deterministic corpus; versioned SQLite
fixture with hash; raw reports/logs unversioned under parity-reports/):
  - `tools/g4-capture/scripts/capture.mjs` — URL-parametrized producer;
    atomic write; provenance recorded; manifest snapshot alongside evidence;
    `--dry-run` skips browser execution for hermetic test coverage.
  - `tests/fixtures/g4/corpus/{manifest.json,index.html}` — deterministic
    corpus with versioned hash pinned in the manifest.
  - `tests/fixtures/g4/sqlite/{MANIFEST.json,taxa-fixture.db,
    taxa-fixture.db.sha256}` — versioned SQLite fixture with hash.
  - `.gitignore` ignores `parity-reports/`, `tools/g4-capture/node_modules/`,
    and `tools/g4-capture/out/`.

Slice 1 ships the producer framework + dry-run capture. Capture-2 adds the
real Lighthouse runner (dynamic `lighthouse` + `chrome-launcher`, fixed
configuration/categories, deterministic mapped LHR evidence, execution
provenance). The runner is injected in tests so no real browser is required.
Approach A / B / C atomic-cut selection is NOT made here; static export
remains unselected.
"""
from __future__ import annotations

import base64
import hashlib
import importlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
CAPTURE = REPO_ROOT / "tools" / "g4-capture"
SCRIPT = CAPTURE / "scripts" / "capture.mjs"
ASGI = CAPTURE / "scripts" / "g4_asgi.py"
PKG = CAPTURE / "package.json"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "g4"
CORPUS_MANIFEST = FIXTURES / "corpus" / "manifest.json"
CORPUS_INDEX = FIXTURES / "corpus" / "index.html"
SQLITE_MANIFEST = FIXTURES / "sqlite" / "MANIFEST.json"
SQLITE_DB = FIXTURES / "sqlite" / "taxa-fixture.db"
SQLITE_HASH = FIXTURES / "sqlite" / "taxa-fixture.db.sha256"
CAPTURE_URL = "http://127.0.0.1:8765/index.html"
# CANONICAL_PORT keeps module-level URL constants stable for non-server tests.
# Tests that actually need a live server use the `g4_server` fixture, which
# overrides this constant via `_capture_url()` so each test process gets a
# distinct, OS-allocated port and cannot accidentally hit a stale listener.
CANONICAL_PORT = 8765
# Required taxon columns for API compatibility - mirrors the schema used by
# tests/test_api_materialize.py + tests/test_api_file_explorer.py so the
# minimal G4 fixture can be served through api.server without server-side
# changes (api/server.py s _row_to_taxon reads every column in REQUIRED_TAXON_COLUMNS).
REQUIRED_TAXON_COLUMNS: tuple[str, ...] = (
    "id", "parent_id", "rank", "status", "scientific_name", "authorship",
    "path", "species_count", "accepted_id", "is_extinct",
    "coldp_id", "worms_id", "worms_parent_id",
    "freshwater_id", "freshwater_parent_id",
)


def _run(args, **kwargs):
    return subprocess.run(["node", str(SCRIPT), *args], capture_output=True, text=True, **kwargs)


# Snapshot api.server module state BEFORE any test in this module imports
# tools.g4-capture.scripts.g4_asgi (which mutates api.server.app.router.routes
# at import time by inserting a /index.html corpus route). Without this snapshot
# the launcher's mutation would leak into other test modules that import
# api.server in the same pytest process. Captured eagerly at module load time
# because g4_asgi imports api.server transitively the first time it's touched.
from api import server as _api_server_snapshot
_ORIGINAL_APP_ROUTES = list(_api_server_snapshot.app.router.routes)
_ORIGINAL_DB_PATH = _api_server_snapshot.DB_PATH
_ORIGINAL_RESEARCH_DIR = _api_server_snapshot.RESEARCH_DIR
del _api_server_snapshot


@pytest.fixture(scope="module", autouse=True)
def _restore_api_server_paths():
    """Keep the launcher test's module-global rewiring inside this module."""
    from api import server
    yield
    server.DB_PATH = _ORIGINAL_DB_PATH
    server.RESEARCH_DIR = _ORIGINAL_RESEARCH_DIR
    # Restore the routes that g4_asgi.py's import-time mutation may have added.
    # We replace the entire list (not slice-assign) so any inserted corpus route
    # is dropped even if a test re-imported g4_asgi after a prior teardown.
    server.app.router.routes[:] = _ORIGINAL_APP_ROUTES


def _run_capture_with_runner(tmp_path, *, synthetic_lhr=None, runner_throws=False,
                              runner_invocation=None, dry_run=False,
                              fetch_response=None, manifest_path=None):
    """Hermetic helper: write a Node wrapper that imports capture.mjs and calls
    it with an injected runner. Captures stdout/stderr/returncode. No real
    browser is launched; the runner is replaced by a closure over the supplied
    `synthetic_lhr`. `fetch_response` defaults to the real corpus bytes with
    status 200 so capture()'s pre-runner verification step succeeds.

    `manifest_path` lets a test point the wrapper at a custom on-disk manifest
    (e.g. one whose entry.expectedContentSha256 matches an intentionally mutated
    body, so the SHA check passes and the DOM-marker check is the one that
    fails). Defaults to the canonical CORPUS_MANIFEST.
    """
    out_dir = tmp_path / "out"
    invocation_log = tmp_path / "_invocations.json"
    log_literal = json.dumps(str(invocation_log))
    manifest_path = manifest_path or CORPUS_MANIFEST
    if fetch_response is None:
        fetch_response = {
            "status": 200,
            "body_b64": base64.b64encode(CORPUS_INDEX.read_bytes()).decode("ascii"),
        }
    fetch_status = int(fetch_response["status"])
    fetch_b64_lit = json.dumps(fetch_response["body_b64"])
    if runner_throws:
        runner_impl = "throw new Error('synthetic runner failure');"
    else:
        runner_impl = (
            f"const __lhr = {json.dumps(synthetic_lhr or {})};\n"
            f"await __log({{ runnerArgs: __runnerArgs }});\n"
            f"return __lhr;"
        )
    script = (
        "import { capture, readJson } from "
        + json.dumps("file://" + str(SCRIPT))
        + ";\n"
        f"const manifest = await readJson({json.dumps(str(manifest_path))});\n"
        f"const __invocationLogPath = {log_literal};\n"
        f"const __fetchStatus = {fetch_status};\n"
        f"const __fetchBodyB64 = {fetch_b64_lit};\n"
        "const __fetchBuf = new Uint8Array(Buffer.from(__fetchBodyB64, 'base64'));\n"
        "const __log = async (entry) => {\n"
        "  const fs = await import('node:fs/promises');\n"
        "  let arr = [];\n"
        "  try { arr = JSON.parse(await fs.readFile(__invocationLogPath, 'utf8')); } catch {}\n"
        "  arr.push(entry);\n"
        "  await fs.writeFile(__invocationLogPath, JSON.stringify(arr));\n"
        "};\n"
        "const __args = {\n"
        "  url: " + json.dumps(CAPTURE_URL) + ",\n"
        "  manifest,\n"
        f"  outDir: {json.dumps(str(out_dir))},\n"
        f"  dryRun: {'true' if dry_run else 'false'},\n"
        "  fetchFn: async (__url) => ({\n"
        "    status: __fetchStatus,\n"
        "    async arrayBuffer() {\n"
        "      return __fetchBuf.buffer.slice(__fetchBuf.byteOffset, __fetchBuf.byteOffset + __fetchBuf.byteLength);\n"
        "    },\n"
        "  }),\n"
        "  runLighthouse: async (__runnerArgs) => {\n"
        "    " + runner_impl + "\n"
        "  },\n"
        "};\n"
        "await capture(__args);\n"
    )
    wrapper = tmp_path / "_runner_wrapper.mjs"
    wrapper.write_text(script)
    proc = subprocess.run(["node", str(wrapper)], capture_output=True, text=True,
                          env={**os.environ, "NODE_NO_WARNINGS": "1"})
    invocations = []
    if invocation_log.is_file():
        try:
            invocations = json.loads(invocation_log.read_text())
        except Exception:
            invocations = []
    return proc, out_dir, invocations


# ── Pinned workspace ──────────────────────────────────────────────
def test_pinned_dependencies_in_isolated_module():
    pkg = json.loads(PKG.read_text())
    deps = pkg.get("dependencies", {})
    assert deps.get("lighthouse"), "lighthouse must be pinned"
    assert deps.get("chrome-launcher"), "chrome-launcher must be pinned"
    for name, v in deps.items():
        assert not v.startswith(("^", "~")), f"{name}@{v} is not pinned"
    assert pkg.get("private") is True and pkg.get("type") == "module"


# ── Producer surface ──────────────────────────────────────────────
def test_capture_script_is_esm_library():
    assert SCRIPT.is_file(), f"missing: {SCRIPT}"
    src = SCRIPT.read_text()
    for sym in ("export function parseArgs", "export async function capture",
                "export function buildProvenance", "export async function atomicWrite",
                "export function validateManifest"):
        assert sym in src, f"missing export: {sym}"


def test_capture_rejects_missing_required_arg():
    r = _run([])
    assert r.returncode != 0 and "missing --url" in r.stderr


# ── Fixture corpus (deterministic HTML) ────────────────────────────
def test_corpus_manifest_validates_and_index_hash_matches():
    assert CORPUS_MANIFEST.is_file() and CORPUS_INDEX.is_file()
    m = json.loads(CORPUS_MANIFEST.read_text())
    assert m.get("schema") == "taxa.g4-capture.manifest/1"
    assert isinstance(m.get("entries"), list) and m["entries"]
    entry = next((e for e in m["entries"] if e.get("path") == "index.html"), None)
    assert entry is not None, "manifest must declare index.html"
    actual = hashlib.sha256(CORPUS_INDEX.read_bytes()).hexdigest()
    assert actual == entry["expectedContentSha256"], (
        f"corpus sha256 drift: got {actual}, want {entry['expectedContentSha256']}"
    )


# ── Fixture SQLite (versioned with hash) ──────────────────────────
def test_sqlite_manifest_db_and_hash_match():
    m = json.loads(SQLITE_MANIFEST.read_text())
    assert m.get("schema") == "taxa.g4-capture.sqlite-manifest/1"
    assert m.get("file") == "taxa-fixture.db"
    assert SQLITE_DB.is_file() and SQLITE_DB.stat().st_size > 0
    assert m["expectedSha256"] == SQLITE_HASH.read_text().strip()
    actual = hashlib.sha256(SQLITE_DB.read_bytes()).hexdigest()
    assert actual == m["expectedSha256"], (
        f"SQLite fixture sha256 drift: got {actual}, want {m['expectedSha256']}. "
        "Rebuild via tools/g4-capture/scripts/seed_fixture.py."
    )


# ── End-to-end dry-run (no browser) ───────────────────────────────
def test_capture_dry_run_writes_evidence_with_provenance(tmp_path, g4_server):
    # capture-3 added a pre-runner verification step that fetches the
    # target URL; the CLI therefore requires a live G4 server. The
    # fixture yields (url, manifest_path) for the ephemeral-port run.
    url, manifest_path = g4_server
    out = tmp_path / "out"
    r = _run(["--url", url,
              "--manifest", str(manifest_path), "--out", str(out), "--dry-run"])
    assert r.returncode == 0, r.stderr
    evidence = json.loads((out / "evidence.json").read_text())
    assert evidence["schema"] == "taxa.g4-capture.evidence/1"
    p = evidence["provenance"]
    assert p["schema"] == "taxa.g4-capture.provenance/1"
    assert p["nodeVersion"].startswith("v")
    snap = json.loads((out / "manifest.snapshot.json").read_text())
    assert snap == json.loads(manifest_path.read_text())


def test_capture_dry_run_rejects_url_not_in_manifest(tmp_path):
    out = tmp_path / "out"
    r = _run(["--url", "http://unknown.example.test/",
              "--manifest", str(CORPUS_MANIFEST), "--out", str(out), "--dry-run"])
    assert r.returncode != 0 and "url not in manifest" in r.stderr


# ── Triangulate: atomic-write + schema enforcement ─────────────────
def test_atomic_write_replaces_existing_outdir(tmp_path, g4_server):
    url, manifest_path = g4_server
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.txt").write_text("stale")
    r = _run(["--url", url,
              "--manifest", str(manifest_path), "--out", str(out), "--dry-run"])
    assert r.returncode == 0, r.stderr
    assert not (out / "stale.txt").exists(), "stale file must be replaced"
    assert (out / "evidence.json").is_file()


def test_validate_manifest_rejects_wrong_schema(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema": "wrong.schema/0", "entries": []}))
    r = _run(["--url", "http://127.0.0.1:8765/index.html",
              "--manifest", str(bad), "--out", str(tmp_path / "out"), "--dry-run"])
    # Validation rejects the manifest before any URL fetch, so no live
    # G4 server is needed.
    assert r.returncode != 0 and "schema mismatch" in r.stderr


# ── G4 capture-2: real Lighthouse runner (hermetic via injected runner) ──
# The capture-2 contract adds a real runner (dynamic lighthouse +
# chrome-launcher) with a fixed configuration/categories and a deterministic
# mapping from the LHR to evidence. To stay hermetic we inject a synthetic
# LHR; no real browser is launched in these tests.
SYNTHETIC_LHR = {
    "finalUrl": "http://127.0.0.1:8765/index.html",
    "lighthouseVersion": "12.2.1",
    "userAgent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36"
    ),
    "fetchTime": "2025-01-01T00:00:00.000Z",
    "runWarnings": ["z warning", "a warning"],
    "categories": {
        "performance": {"score": 0.95, "title": "Performance"},
        "accessibility": {"score": 1.0, "title": "Accessibility"},
        "best-practices": {"score": 0.92, "title": "Best Practices"},
        "seo": {"score": 1.0, "title": "SEO"},
        "extra-category": {"score": 0.5, "title": "Extra"},  # must be filtered out
    },
    "audits": {
        "first-contentful-paint": {
            "id": "first-contentful-paint", "title": "FCP",
            "score": 0.9, "displayValue": "0.5 s",
        },
        "unused-javascript": {
            "id": "unused-javascript", "title": "Unused JS", "score": 1.0,
        },
    },
}


def test_real_run_maps_synthetic_lhr_deterministically(tmp_path):
    """Real-run path (capture-2): injected runner returns a synthetic LHR;
    capture must map it deterministically — fixed category set, sorted
    runWarnings, and execution provenance parsed from the LHR
    (lighthouseVersion, chromeVersion from userAgent)."""
    proc, out_dir, invocations = _run_capture_with_runner(
        tmp_path, synthetic_lhr=SYNTHETIC_LHR, dry_run=False
    )
    assert proc.returncode == 0, proc.stderr
    assert out_dir.is_dir(), "evidence must be written on success"
    evidence = json.loads((out_dir / "evidence.json").read_text())
    lhr = evidence["lighthouse"]
    # Runner was invoked exactly once with the expected arguments.
    assert len(invocations) == 1
    invocation = invocations[0]["runnerArgs"]
    assert invocation["url"] == CAPTURE_URL
    assert invocation["manifestEntry"]["url"] == CAPTURE_URL
    # Fixed categories only, in fixed order.
    assert list(lhr["categories"].keys()) == [
        "performance", "accessibility", "best-practices", "seo",
    ]
    assert lhr["categories"]["performance"] == {"score": 0.95, "title": "Performance"}
    assert "extra-category" not in lhr["categories"], (
        "categories outside the fixed set must be filtered out"
    )
    # runWarnings sorted for determinism.
    assert lhr["runWarnings"] == ["a warning", "z warning"], (
        "runWarnings must be sorted deterministically"
    )
    # LHR pass-through fields.
    assert lhr["finalUrl"] == SYNTHETIC_LHR["finalUrl"]
    assert lhr["lighthouseVersion"] == "12.2.1"
    assert lhr["userAgent"] == SYNTHETIC_LHR["userAgent"]
    assert lhr["fetchTime"] == SYNTHETIC_LHR["fetchTime"]
    assert "first-contentful-paint" in lhr["audits"]
    # Provenance parsed from the synthetic LHR.
    prov = evidence["provenance"]
    assert prov["schema"] == "taxa.g4-capture.provenance/1"
    assert prov["lighthouseVersion"] == "12.2.1"
    assert prov["chromeVersion"].startswith("120.0.6099.71"), (
        "chromeVersion must be parsed from userAgent; got "
        f"{prov['chromeVersion']!r}"
    )
    assert prov["nodeVersion"].startswith("v")
    # Manifest snapshot still alongside evidence.
    snap = json.loads((out_dir / "manifest.snapshot.json").read_text())
    assert snap == json.loads(CORPUS_MANIFEST.read_text())


def test_real_runner_failure_does_not_publish_or_replace_output(tmp_path):
    """Capture-2 contract: if the injected runner throws, capture must NOT
    write evidence.json or manifest.snapshot.json, and must NOT replace a
    pre-existing outDir. Atomic publish semantics preserved."""
    out_dir_pre = tmp_path / "out"
    out_dir_pre.mkdir()
    stale = out_dir_pre / "stale.txt"
    stale.write_text("stale evidence")
    proc, out_dir, _ = _run_capture_with_runner(
        tmp_path, runner_throws=True
    )
    assert proc.returncode != 0, (
        f"runner failure must propagate non-zero; got stdout={proc.stdout!r} "
        f"stderr={proc.stderr!r}"
    )
    assert "synthetic runner failure" in proc.stderr, (
        "underlying runner error must surface in stderr"
    )
    # No evidence files written.
    assert not (out_dir / "evidence.json").exists(), (
        "evidence.json must NOT be written when the runner fails"
    )
    assert not (out_dir / "manifest.snapshot.json").exists(), (
        "manifest.snapshot.json must NOT be written when the runner fails"
    )
    # Pre-existing outDir must NOT have been replaced.
    assert stale.is_file() and stale.read_text() == "stale evidence", (
        "pre-existing outDir contents must be left untouched on runner failure"
    )


def test_real_run_exposes_fixed_categories_and_lighthouse_config():
    """Capture-2 contract: the runner exports a fixed set of categories and
    a fixed Lighthouse configuration; any other consumer (CLI, tests) can
    rely on these being stable."""
    src = SCRIPT.read_text()
    for sym in ("export function fixedLighthouseConfig",
                "export function fixedCategories",
                "export function mapLhr",
                "export async function runLighthouse"):
        assert sym in src, f"missing export: {sym}"
    # Fixed categories list is exported and matches the locked set.
    proc = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"import {{ fixedCategories }} from 'file://{SCRIPT}';\n"
         "process.stdout.write(JSON.stringify(fixedCategories()));"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == [
        "performance", "accessibility", "best-practices", "seo",
    ], "fixedCategories() must return the locked four-category set"
    # Fixed config exposes a Lighthouse-shaped settings object with the
    # same locked category list pinned into onlyCategories.
    proc = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"import {{ fixedLighthouseConfig, fixedCategories }} from 'file://{SCRIPT}';\n"
         "const cfg = fixedLighthouseConfig();\n"
         "const out = {\n"
         "  cats: cfg.settings.onlyCategories,\n"
         "  formFactor: cfg.settings.formFactor,\n"
         "  same: JSON.stringify(cfg.settings.onlyCategories)\n"
         "       === JSON.stringify(fixedCategories())\n"
         "};\n"
         "process.stdout.write(JSON.stringify(out));"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["cats"] == ["performance", "accessibility", "best-practices", "seo"]
    assert out["same"] is True, (
        "fixedLighthouseConfig().settings.onlyCategories must equal fixedCategories()"
    )
    assert out["formFactor"] in ("desktop", "mobile"), (
        f"formFactor must be set deterministically; got {out['formFactor']!r}"
    )


def test_real_run_map_lhr_throws_on_non_object():
    """Triangulate: mapLhr must reject non-object LHRs deterministically so
    bad input cannot slip through into evidence.json."""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"import {{ mapLhr }} from 'file://{SCRIPT}';\n"
         "try { mapLhr(null); process.exit(11); }"
         " catch (e) { process.stdout.write(e.message); }"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "lhr" in proc.stdout.lower(), (
        f"mapLhr(null) error must mention 'lhr'; got {proc.stdout!r}"
    )


def test_cli_without_dry_run_fails_closed_until_real_runner_invoked(tmp_path, g4_server):
    """Capture-2 contract: when --dry-run is omitted, the CLI must invoke
    the real chrome-launcher + lighthouse runner. With the live G4 server
    in place, verifyTarget passes and the runner is the next step. In this
    hermetic test (no browser available) the run is expected to fail
    closed with no evidence.json published."""
    url, manifest_path = g4_server
    out = tmp_path / "out"
    r = _run(["--url", url,
              "--manifest", str(manifest_path), "--out", str(out)])
    # We do NOT require a real browser to be available; we only require
    # that no silent partial write happens. Either the run succeeds (a
    # real browser happened to be available, evidence.json MUST carry the
    # mapped structure) OR it fails closed (no evidence.json published).
    if r.returncode != 0:
        assert not (out / "evidence.json").exists(), (
            "failed CLI runs must not publish evidence"
        )
    else:
        assert (out / "evidence.json").is_file()
        evidence = json.loads((out / "evidence.json").read_text())
        assert "categories" in evidence["lighthouse"]
        assert evidence["provenance"]["schema"] == "taxa.g4-capture.provenance/1"


# ── Triangulate: edge-case LHR mapping + helper contracts ───────────────
def test_map_lhr_with_minimal_lhr_yields_empty_locked_categories():
    """mapLhr on a minimal/empty LHR produces deterministic empty evidence:
    no warnings, only the four fixed categories (all `null` scores), and
    null passthrough fields. No extraneous keys leak in."""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"import {{ mapLhr }} from 'file://{SCRIPT}';\n"
         "const r = mapLhr({});\n"
         "process.stdout.write(JSON.stringify(r));"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["runWarnings"] == []
    assert list(out["categories"].keys()) == [
        "performance", "accessibility", "best-practices", "seo",
    ]
    for cid, cat in out["categories"].items():
        assert cat["score"] is None and cat["title"] == cid, (
            f"empty LHR category {cid!r} must be null score + id title; got {cat!r}"
        )
    assert out["finalUrl"] is None
    assert out["lighthouseVersion"] is None
    assert out["userAgent"] is None
    assert out["fetchTime"] is None
    assert out["audits"] == {}


def test_map_lhr_drops_categories_outside_fixed_set():
    """mapLhr must drop any category id outside the locked four-category set
    (Lighthouse 12.x can emit `pwa`, `pwa-installable`, etc.). The dropped
    categories must NOT survive into evidence."""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"import {{ mapLhr }} from 'file://{SCRIPT}';\n"
         "const r = mapLhr({ categories: {\n"
         "  performance: { score: 0.5, title: 'Performance' },\n"
         "  pwa: { score: 0.1, title: 'PWA' },\n"
         "  seo: { score: 1.0, title: 'SEO' },\n"
         "}});\n"
         "process.stdout.write(JSON.stringify(Object.keys(r.categories).sort()));"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == [
        "accessibility", "best-practices", "performance", "seo",
    ], "non-fixed categories must be dropped"


def test_chrome_version_from_user_agent_handles_missing_and_weird_inputs():
    """chromeVersionFromUserAgent must never throw and must return 'unknown'
    for anything that does not contain a Chrome/VERSION token."""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"import {{ chromeVersionFromUserAgent }} from 'file://{SCRIPT}';\n"
         "const cases = [\n"
         "  'Mozilla/5.0 ... Chrome/120.0.6099.71 Safari/537.36',\n"
         "  'HeadlessChrome/130.0.0.0',\n"
         "  '',\n"
         "  null,\n"
         "  undefined,\n"
         "  42,\n"
         "  'no chrome here',\n"
         "];\n"
         "const out = cases.map((c) => [String(c), chromeVersionFromUserAgent(c)]);\n"
         "process.stdout.write(JSON.stringify(out));"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    rows = json.loads(proc.stdout)
    # First row: well-formed Chrome UA extracts the major version.
    assert rows[0][1] == "120.0.6099.71"
    # HeadlessChrome UA also matches (regex picks up 'Chrome/' suffix).
    assert rows[1][1] == "130.0.0.0"
    # Empty / null / undefined / non-string / no-Chrome all collapse to 'unknown'.
    for label, val in rows[2:]:
        assert val == "unknown", f"case {label!r} must map to 'unknown', got {val!r}"


def test_fixed_categories_returns_fresh_copy_not_module_state():
    """fixedCategories() must return a fresh array — mutating the returned
    array must not affect subsequent calls or the runner config."""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"import {{ fixedCategories, fixedLighthouseConfig }} from 'file://{SCRIPT}';\n"
         "const a = fixedCategories();\n"
         "a.push('pwa');\n"
         "const b = fixedCategories();\n"
         "const cfg = fixedLighthouseConfig();\n"
         "const out = {\n"
         "  bLen: b.length,\n"
         "  cfgLen: cfg.settings.onlyCategories.length,\n"
         "  same: JSON.stringify(b) === JSON.stringify(cfg.settings.onlyCategories),\n"
         "};\n"
         "process.stdout.write(JSON.stringify(out));\n"
         ],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["bLen"] == 4, (
        f"mutating the first call must not leak into the second; got b.length={out['bLen']}"
    )
    assert out["cfgLen"] == 4, (
        f"fixedLighthouseConfig().settings.onlyCategories must also stay at 4; "
        f"got {out['cfgLen']}"
    )
    assert out["same"] is True, (
        "fixedLighthouseConfig().settings.onlyCategories must equal fixedCategories()"
    )


def test_map_lhr_run_warnings_sorted_deterministically_across_runs():
    """Two invocations of mapLhr on the same warning set must produce the
    same sorted order — determinism is required for downstream hashing."""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"import {{ mapLhr }} from 'file://{SCRIPT}';\n"
         "const lhr = { runWarnings: ['c', 'a', 'b'] };\n"
         "const r1 = JSON.stringify(mapLhr(lhr).runWarnings);\n"
         "const r2 = JSON.stringify(mapLhr({ ...lhr, runWarnings: ['b', 'c', 'a'] }).runWarnings);\n"
         "process.stdout.write(r1 + '|' + r2);"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    r1, r2 = proc.stdout.split("|")
    assert r1 == r2 == '["a","b","c"]', (
        f"runWarnings must sort to the same order regardless of input order; "
        f"got {r1!r} vs {r2!r}"
    )

# ── Fixture SQLite: API-compatible columns + root coldp_id ───────────────
# The G4 capture producer serves api.server in front of the fixture SQLite
# (see test_g4_asgi_launcher_* below). api/server.py's _row_to_taxon reads
# every column listed in REQUIRED_TAXON_COLUMNS, so the fixture MUST carry
# each one (NULL where the fixture does not exercise that source). The root
# row (Eukaryota) MUST have coldp_id set so /api/domains returns it.
def _fixture_taxon_columns() -> set[str]:
    conn = sqlite3.connect(SQLITE_DB)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(taxon)").fetchall()}
    conn.close()
    return cols


def test_fixture_has_all_required_taxon_columns():
    """All API-required taxon columns must exist on the fixture DB; missing
    columns cause _row_to_taxon to raise sqlite3.OperationalError ('no such
    column: ...') the first time the API touches a row."""
    cols = _fixture_taxon_columns()
    missing = [c for c in REQUIRED_TAXON_COLUMNS if c not in cols]
    assert not missing, (
        f"fixture taxon table is missing API-required columns {missing!r}; "
        f"rebuild via tools/g4-capture/scripts/seed_fixture.py"
    )


def test_fixture_root_has_coldp_id():
    """The root row (Eukaryota, id=1) must carry coldp_id so /api/domains'
    WHERE clause (coldp_id IS NOT NULL OR worms_id=1 OR freshwater) returns
    it as the sole top-level domain."""
    conn = sqlite3.connect(SQLITE_DB)
    row = conn.execute(
        "SELECT id, scientific_name, coldp_id FROM taxon WHERE id = 1"
    ).fetchone()
    conn.close()
    assert row is not None, "fixture root (id=1) missing"
    assert row[1] == "Eukaryota", f"fixture root must be Eukaryota, got {row[1]!r}"
    assert row[2] is not None and row[2] != "", (
        f"fixture root must carry coldp_id so /api/domains returns it; got {row[2]!r}"
    )


# ── G4 ASGI launcher (controlled, minimal) ───────────────────────────────
# The launcher imports api.server and rewires only DB_PATH + RESEARCH_DIR to
# point at the G4-controlled fixture paths. All other api.server module
# globals (WEB_DIR, route registrations, middleware, etc.) MUST stay as
# api.server set them. The launcher is a hermetic test surface — production
# is unchanged.
def _import_g4_asgi():
    """Import the G4 ASGI launcher fresh in a subprocess so api.server's
    module state from previous tests cannot leak into the assertions below.
    Returns (returncode, stdout, stderr)."""
    py = sys.executable
    probe = (
        "import json, sys\n"
        f"sys.path.insert(0, {json.dumps(str(REPO_ROOT))})\n"
        "import api.server as srv\n"
        "import importlib\n"
        "mod = importlib.import_module('tools.g4-capture.scripts.g4_asgi')\n"
        "out = {\n"
        "  'db_path': str(srv.DB_PATH),\n"
        "  'research_dir': str(srv.RESEARCH_DIR),\n"
        "  'web_dir': str(srv.WEB_DIR),\n"
        "  'app_is_srv_app': mod.app is srv.app,\n"
        "}\n"
        "sys.stdout.write(json.dumps(out))\n"
    )
    return subprocess.run([py, "-c", probe], capture_output=True, text=True)


def test_g4_asgi_launcher_exists_and_imports():
    """The launcher must exist at tools/g4-capture/scripts/g4_asgi.py and
    be importable without errors (it imports api.server at module top — a
    missing dependency or syntax error must surface here)."""
    assert ASGI.is_file(), f"missing launcher: {ASGI}"
    src = ASGI.read_text()
    # The launcher must expose the ASGI app under the conventional `app` name
    # so uvicorn `tools.g4-capture.scripts.g4_asgi:app` works.
    assert "app" in src, "launcher must expose an ASGI app"
    proc = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, {json.dumps(str(REPO_ROOT))});\n"
         "import importlib;"
         "mod = importlib.import_module('tools.g4-capture.scripts.g4_asgi');\n"
         "assert mod.app is not None"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, (
        f"launcher must import cleanly; got stdout={proc.stdout!r} "
        f"stderr={proc.stderr!r}"
    )


def test_g4_asgi_launcher_rewires_db_path_and_research_dir_only():
    """The launcher MUST set api.server.DB_PATH and api.server.RESEARCH_DIR
    to the G4 fixture paths and MUST leave other api.server module globals
    (WEB_DIR) untouched. We probe via subprocess so api.server's in-process
    state from earlier tests cannot mask a leak."""
    proc = _import_g4_asgi()
    assert proc.returncode == 0, (
        f"subprocess failed; stderr={proc.stderr!r}"
    )
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["db_path"] == str(SQLITE_DB), (
        f"api.server.DB_PATH must point at the G4 fixture DB after import; "
        f"got {out['db_path']!r}"
    )
    # RESEARCH_DIR is redirected away from the production ./Research path.
    assert out["research_dir"] != str((REPO_ROOT / "Research").resolve()), (
        f"api.server.RESEARCH_DIR must NOT point at production Research; "
        f"got {out['research_dir']!r}"
    )
    assert "tests/fixtures/g4" in out["research_dir"] or out["research_dir"].endswith("g4"), (
        f"api.server.RESEARCH_DIR must be under the G4 fixture tree; "
        f"got {out['research_dir']!r}"
    )
    # WEB_DIR must NOT be touched — the launcher rewires only DB_PATH and
    # RESEARCH_DIR. Anything else would mean api/server.py was implicitly
    # modified, which the parent task forbids.
    expected_web_dir = str((REPO_ROOT / "out").resolve())
    assert out["web_dir"] == expected_web_dir, (
        f"launcher must NOT modify api.server.WEB_DIR "
        f"(production change forbidden); got {out['web_dir']!r}, want {expected_web_dir!r}"
    )
    # The re-exported `app` is the same FastAPI instance api.server built —
    # the launcher does not construct a duplicate.
    assert out["app_is_srv_app"] is True, (
        "launcher must re-export api.server.app, not build a new FastAPI()"
    )


def test_g4_asgi_launcher_serves_health_endpoint():
    """End-to-end: the launched app must serve /api/health against the
    fixture DB without crashing. Health exercises the rewired DB_PATH (the
    db() function reads DB_PATH at call time, so the launcher patch must
    take effect when the app handles a request)."""
    from fastapi.testclient import TestClient
    # Import here so the test can run in isolation and the launcher's
    # module-level api.server rewiring applies.
    import importlib
    mod = importlib.import_module("tools.g4-capture.scripts.g4_asgi")
    client = TestClient(mod.app)
    r = client.get("/api/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    # Stats come from the G4 fixture: 10 taxon + 8 vernacular rows.
    assert body["taxa"] == 10, f"expected 10 fixture taxa, got {body['taxa']!r}"
    assert body["vernaculars"] == 8, (
        f"expected 8 fixture vernaculars, got {body['vernaculars']!r}"
    )
    # The launcher rewires DB_PATH; the health payload must reflect that,
    # not the production data/db/taxa.db path.
    assert body["db"] == str(SQLITE_DB), (
        f"health.db must report the rewired fixture path; got {body['db']!r}"
    )


def test_g4_asgi_launcher_serves_domains_from_fixture_root():
    """Triangulate: /api/domains must return the G4 fixture's root
    (Eukaryota, coldp_id non-null) as the sole domain. This proves the
    launcher wires through end-to-end (DB_PATH → db() → SELECT)."""
    from fastapi.testclient import TestClient
    import importlib
    mod = importlib.import_module("tools.g4-capture.scripts.g4_asgi")
    client = TestClient(mod.app)
    r = client.get("/api/domains")
    assert r.status_code == 200, r.text
    domains = r.json()
    assert isinstance(domains, list) and domains, (
        f"fixture root must be returned by /api/domains; got {domains!r}"
    )
    assert len(domains) == 1, (
        f"fixture has one coldp_id-rooted domain (Eukaryota); got {len(domains)}: {domains!r}"
    )
    assert domains[0]["scientific_name"] == "Eukaryota"
    assert domains[0]["coldp_id"], (
        f"fixture root must carry coldp_id; got {domains[0]!r}"
    )


# ── G4 capture-3: target verification + rollback-safe atomicWrite +
#    ASGI corpus isolation ──────────────────────────────────────
# PR #124 follow-ups:
#   1. The G4 ASGI launcher must serve the pinned corpus index.html at
#      /index.html, never the mutable production web/index.html.
#   2. capture() must verify the served bytes/sha256/DOM marker from
#      the corpus manifest BEFORE the Lighthouse runner or atomicWrite.
#   3. atomicWrite must use a rollback-safe sibling-backup strategy so
#      a final-rename failure no longer destroys the prior outDir.


def _free_port():
    """Bind to port 0 to let the OS pick a free port, then release the
    socket. A small race remains; the readiness loop below also probes
    the HTTP body so it cannot falsely succeed against an unrelated
    process that happens to own the port."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def g4_server(monkeypatch, tmp_path):
    """Spin up the G4 ASGI launcher on a dynamically-allocated 127.0.0.1
    port. Yields ``(url, manifest_path)``; the manifest is a per-test copy
    of the corpus manifest with the ephemeral-port URL rewritten into every
    entry, so validateManifest accepts the URL. Readiness probes both the
    TCP socket AND the response body so it cannot falsely succeed against
    another process that happens to own the port.
    """
    import uvicorn
    mod = importlib.import_module("tools.g4-capture.scripts.g4_asgi")
    port = _free_port()
    config = uvicorn.Config(mod.app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1) as s:
                s.sendall(b"GET /index.html HTTP/1.0\r\nHost: localhost\r\n\r\n")
                s.settimeout(0.5)
                blob = b""
                while len(blob) < 8192:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    blob += chunk
                if b"G4 capture corpus" in blob:
                    break
        except (OSError, socket.timeout):
            pass
        time.sleep(0.05)
    else:
        server.should_exit = True
        t.join(timeout=2)
        raise RuntimeError(
            f"g4_server fixture: uvicorn did not serve G4 corpus on port {port} within 5s"
        )
    url = f"http://127.0.0.1:{port}/index.html"
    manifest = json.loads(CORPUS_MANIFEST.read_text())
    for entry in manifest["entries"]:
        entry["url"] = url
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr("tests.test_capture_parity.CAPTURE_URL", url, raising=False)
    try:
        yield url, manifest_path
    finally:
        server.should_exit = True
        t.join(timeout=5)


# ── ASGI: /index.html serves the corpus, never production web/ ──
def test_g4_asgi_serves_corpus_index_html_at_root_path():
    """The launcher MUST serve tests/fixtures/g4/corpus/index.html at
    /index.html — never the production web/index.html. Response bytes
    must hash to the manifest-declared sha256 and must contain the
    manifest-declared DOM marker. This is the integrity guard that
    prevents product drift in web/ from contaminating capture evidence."""
    entry = next(
        e for e in json.loads(CORPUS_MANIFEST.read_text())["entries"]
        if e["url"] == CAPTURE_URL
    )
    expected_sha = entry["expectedContentSha256"]
    expected_marker = entry["expectedDOMMarker"]
    from fastapi.testclient import TestClient
    mod = importlib.import_module("tools.g4-capture.scripts.g4_asgi")
    r = TestClient(mod.app).get("/index.html")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/html")
    assert hashlib.sha256(r.content).hexdigest() == expected_sha
    assert expected_marker in r.text
    # Catches "fell through to StaticFiles mount" regressions: if production
    # web/index.html exists and differs from the corpus, it MUST NOT have
    # been served.
    prod_index = REPO_ROOT / "web" / "index.html"
    if prod_index.is_file() and hashlib.sha256(prod_index.read_bytes()).hexdigest() != expected_sha:
        assert r.content != prod_index.read_bytes()


# ── capture(): target verification before runner / atomicWrite ──
# Three failure modes are exercised via the corpus manifest contract:
#   - entry.expectedStatus        (HTTP status)
#   - entry.expectedContentSha256 (raw response bytes sha256)
#   - entry.expectedDOMMarker     (literal substring of the body)
#
# The `marker` mode is special: the SHA check runs before the marker check,
# so to reach the marker branch we serve mutated bytes AND patch the
# manifest entry's `expectedContentSha256` to match the mutated bytes. The
# SHA check then passes and the marker check fires.
_CORPUS_BYTES = CORPUS_INDEX.read_bytes()
_CORPUS_MARKER = b'g4-probe-marker'  # raw substring (no quotes); marker attr has the wrapper

def _bad_fetch_response(mode, *, marker_strip_bytes=None):
    """Return a fetch_response dict that fails verification in the
    given mode. Used to exercise the three pre-runner guards.

    `marker_strip_bytes` (used by the "marker" mode) is the bytes that
    were mutated out of the response body so the caller can patch the
    manifest's expectedContentSha256 to match.
    """
    b64 = lambda b: base64.b64encode(b).decode("ascii")  # noqa: E731
    if mode == "status":
        return {"status": 500, "body_b64": b64(_CORPUS_BYTES), "mutated_bytes": _CORPUS_BYTES}
    if mode == "sha":
        mutated = bytearray(_CORPUS_BYTES)
        mutated[-1] = (mutated[-1] + 1) & 0xFF
        return {"status": 200, "body_b64": b64(bytes(mutated)), "mutated_bytes": bytes(mutated)}
    if mode == "marker":
        if marker_strip_bytes is None:
                raise ValueError("marker mode requires marker_strip_bytes")
        return {"status": 200, "body_b64": b64(marker_strip_bytes), "mutated_bytes": marker_strip_bytes}
    raise ValueError(f"unknown mode: {mode}")


def _patch_manifest_entry_for_mode(tmp_path, *, mutated_bytes):
    """Write a manifest in tmp_path whose entry.expectedContentSha256 is the
    SHA of `mutated_bytes` (everything else matches the corpus manifest).
    Returns the path to the patched manifest. Used so the SHA check passes
    and the next gate (status or marker) is the one that fails."""
    manifest = json.loads(CORPUS_MANIFEST.read_text())
    sha = hashlib.sha256(mutated_bytes).hexdigest()
    for entry in manifest["entries"]:
        if entry["url"] == CAPTURE_URL:
            entry["expectedContentSha256"] = sha
    path = tmp_path / "_patched_manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def _bad_for_mode(tmp_path, mode):
    """Build a (fetch_response, manifest_path) pair that fails verification
    in `mode`. The marker mode requires a custom manifest because the SHA
    check runs first; we patch the SHA so the marker check fires instead."""
    if mode == "marker":
        stripped = _CORPUS_BYTES.replace(_CORPUS_MARKER, b"g4-prob-marker")
        bad = _bad_fetch_response(mode, marker_strip_bytes=stripped)
        manifest_path = _patch_manifest_entry_for_mode(
            tmp_path, mutated_bytes=bad["mutated_bytes"],
        )
    else:
        bad = _bad_fetch_response(mode)
        manifest_path = None
    return bad, manifest_path


@pytest.mark.parametrize("mode", ["status", "sha", "marker"])
def test_capture_verification_failure_prevents_runner_publication_and_preserves_outdir(
    tmp_path, mode,
):
    """Pre-runner verification failure MUST (a) NOT invoke the runner,
    (b) NOT publish evidence.json / manifest.snapshot.json, and (c) leave
    any prior outDir intact (no evidence published, no .tmp-/.bak-
    siblings left behind). Triangulate: marker mode reaches the DOM-marker
    branch specifically."""
    bad, manifest_path = _bad_for_mode(tmp_path, mode)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    sentinel = json.dumps({"prior": "evidence", "kept": True})
    (out_dir / "evidence.json").write_text(sentinel)
    proc, _, invocations = _run_capture_with_runner(
        tmp_path,
        synthetic_lhr=SYNTHETIC_LHR,
        dry_run=False,
        fetch_response={"status": bad["status"], "body_b64": bad["body_b64"]},
        manifest_path=manifest_path,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode != 0 and invocations == []
    # No NEW evidence published: the prior sentinel file remains unchanged
    # (and no manifest.snapshot.json was created from the failed capture).
    assert (out_dir / "evidence.json").read_text() == sentinel
    assert not (out_dir / "manifest.snapshot.json").exists()
    siblings = [p for p in tmp_path.iterdir()
if p.name.startswith(("out.tmp-", "out.bak-"))]
    assert siblings == [], (
        f"failure ({mode}) must not leave staging/backup siblings; "
        f"found: {[str(s) for s in siblings]}"
    )
    assert "verifyTarget" in combined
    if mode == "marker":
        assert "DOM marker" in combined


def test_capture_verification_runs_before_runner_on_success(tmp_path):
    """Sanity: when verification succeeds (good fetch), the Lighthouse
    runner IS invoked. This proves verification is a precondition, not
    a replacement, for the runner — and that the runner receives the
    manifestEntry that validation already accepted."""
    proc, _, invocations = _run_capture_with_runner(
        tmp_path, synthetic_lhr=SYNTHETIC_LHR, dry_run=False,
        # default fetch_response (corpus bytes) — passes verification
    )
    assert proc.returncode == 0, proc.stderr
    assert len(invocations) == 1, (
        f"runner must be invoked exactly once on success; got {len(invocations)}"
    )
    invocation = invocations[0]["runnerArgs"]
    assert invocation["url"] == CAPTURE_URL
    assert invocation["manifestEntry"]["url"] == CAPTURE_URL
    # Evidence written as usual.
    out_dir = tmp_path / "out"
    assert (out_dir / "evidence.json").is_file()


def test_capture_dry_run_still_verifies_target(tmp_path):
    """Dry-run must also run the verification step — a malformed target
    must NOT publish synthetic evidence either. The runner isn't called
    in dry-run, but the verification still gates atomicWrite."""
    out_dir = tmp_path / "out"
    proc, _, _ = _run_capture_with_runner(
        tmp_path,
        dry_run=True,
        fetch_response=_bad_fetch_response("status"),
    )
    assert proc.returncode != 0, (
        f"dry-run verification failure must propagate; "
        f"got stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert not (out_dir / "evidence.json").exists()


    # ── atomicWrite: rollback-safe sibling-backup strategy ──
def _run_atomic_write(tmp_path, *, pre_create=False, fail_stage_rename=False):
    """Generate and run a Node wrapper that calls `atomicWrite(outDir, ...)`.
    When `pre_create` is True, outDir exists with a sentinel evidence.json.
    When `fail_stage_rename` is True, the injected `rename` throws on the
    tmp → outDir rename. The wrapper writes ``{err, renameCalls}`` JSON
    to stdout (or `{}` on success). Returns (proc, out_dir)."""
    out_dir = tmp_path / "out"
    if pre_create:
        out_dir.mkdir()
        (out_dir / "evidence.json").write_text(json.dumps({"prior": True}))
    fail_logic = (
        "      if (src.startsWith(outDir + '.tmp-')) {\n"
        "        throw new Error('simulated rename failure');\n"
        "      }\n"
    ) if fail_stage_rename else ""
    script = (
        "import { atomicWrite } from "
        + json.dumps("file://" + str(SCRIPT))
        + ";\n"
        "import * as fs from 'node:fs';\n"
        f"const outDir = {json.dumps(str(out_dir))};\n"
        "let renameCalls = 0;\n"
        "try {\n"
        "  await atomicWrite(outDir, {'evidence.json': 'NEW'}, {\n"
        "    rename: (src, dst) => {\n"
        "      renameCalls++;\n"
        + fail_logic +
        "      fs.renameSync(src, dst);\n"
        "    },\n"
        "  });\n"
        f"  process.stdout.write(JSON.stringify({{err: null, renameCalls}}));\n"
        "} catch (e) {\n"
        f"  process.stdout.write(JSON.stringify({{err: e.message, renameCalls}}));\n"
        "}\n"
    )
    wrapper = tmp_path / "_atomic_wrapper.mjs"
    wrapper.write_text(script)
    proc = subprocess.run(
        ["node", str(wrapper)], capture_output=True, text=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    return proc, out_dir


# ── atomicWrite scenarios (rollback-safe staged-rename) ──
@pytest.mark.parametrize("pre_create,fail_stage", [
    (True, True),    # failure: prior outDir exists, staged rename fails
    (True, False),   # success: prior outDir exists, no leftover siblings
    (False, False),  # success: fresh path, backup step is a no-op
])
def test_atomic_write_rollback_safe_scenarios(tmp_path, pre_create, fail_stage):
    """atomicWrite MUST keep the prior outDir readable on failure, leave no
    .tmp-/.bak- sibling behind across success OR failure, and skip the
    backup step when no prior outDir exists. The three cases parametrize
    the same node-wrapper helper."""
    proc, out_dir = _run_atomic_write(
        tmp_path, pre_create=pre_create, fail_stage_rename=fail_stage,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    if fail_stage:
        assert "simulated rename failure" in out["err"]
        assert out["renameCalls"] >= 2  # backup-rename + failing staged-rename
        assert json.loads((out_dir / "evidence.json").read_text()) == {"prior": True}, (
            "prior evidence.json must be preserved on rollback"
        )
    else:
        assert out["err"] is None
        assert (out_dir / "evidence.json").read_text() == "NEW"
    leftovers = [p for p in tmp_path.iterdir()
                 if p.name.startswith(("out.tmp-", "out.bak-"))]
    assert leftovers == [], (
        f"atomicWrite must leave no staging/backup siblings; "
        f"found: {[str(s) for s in leftovers]}"
    )


def test_capture_verification_failure_when_fetch_throws(tmp_path):
    """Triangulate: verifyTarget must surface a fetch-level error
    (e.g. server unreachable, DNS failure) as a verification failure so
    the runner is not invoked. Production failure mode when the G4 server
    is down."""
    out_dir = tmp_path / "out"
    wrapper = tmp_path / "_fetch_throws_wrapper.mjs"
    wrapper.write_text(
        "import { capture, readJson } from "
        + json.dumps("file://" + str(SCRIPT))
        + ";\n"
        f"const manifest = await readJson({json.dumps(str(CORPUS_MANIFEST))});\n"
        "let runnerCalled = false;\n"
        "try {\n"
        "  await capture({\n"
        f"    url: {json.dumps(CAPTURE_URL)},\n"
        "    manifest,\n"
        f"    outDir: {json.dumps(str(out_dir))},\n"
        "    dryRun: false,\n"
        "    runLighthouse: async () => { runnerCalled = true; return {}; },\n"
        "    fetchFn: async () => { throw new Error('ECONNREFUSED simulated'); },\n"
        "  });\n"
        "  process.exit(2);\n"
        "} catch (e) {\n"
        "  process.stdout.write(JSON.stringify({err: e.message, runnerCalled}));\n"
        "}\n"
    )
    proc = subprocess.run(
        ["node", str(wrapper)], capture_output=True, text=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    out = json.loads(proc.stdout)
    assert "verifyTarget" in out["err"] and "ECONNREFUSED simulated" in out["err"]
    assert out["runnerCalled"] is False
    assert not (out_dir / "evidence.json").exists()


    # ── atomicWrite: path-traversal rejection ─────────────────────────
def test_atomic_write_rejects_file_names_outside_staging(tmp_path):
    """Security: atomicWrite must refuse to write a file whose name resolves
    OUTSIDE the staging directory. Covers absolute names, parent-escape names,
    and empty / non-string names. The original outDir MUST remain untouched
    across all rejections."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "evidence.json").write_text("prior")
    bad_names = ["/etc/passwd", "../../escape.txt", ""]
    wrapper = tmp_path / "_escape.mjs"
    wrapper.write_text(
        "import { atomicWrite } from "
        + json.dumps("file://" + str(SCRIPT))
        + ";\n"
        f"const outDir = {json.dumps(str(out_dir))};\n"
        f"const badNames = {json.dumps(bad_names)};\n"
        "const results = [];\n"
        "for (const badName of badNames) {\n"
        "  try {\n"
        "    await atomicWrite(outDir, {[badName]: 'x'});\n"
        "    results.push({name: badName, threw: false});\n"
        "  } catch (e) {\n"
        "    results.push({name: badName, threw: true, err: e.message});\n"
        "  }\n"
        "}\n"
        "process.stdout.write(JSON.stringify(results));\n"
    )
    proc = subprocess.run(
        ["node", str(wrapper)], capture_output=True, text=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    results = json.loads(proc.stdout)
    assert len(results) == len(bad_names)
    for bad_name, result in zip(bad_names, results):
        assert result["threw"], f"atomicWrite must reject {bad_name!r}; got {result!r}"
        err = result["err"]
        assert any(s in err for s in ("outside staging dir", "must be relative", "non-empty string")), (
            f"{bad_name!r} must surface a path-traversal error; got {err!r}"
        )
    assert (out_dir / "evidence.json").read_text() == "prior"


# ── validateManifest: required expectedDOMMarker ─────────────────
def test_validate_manifest_rejects_empty_expected_dom_marker(tmp_path):
    """Capture-integrity contract: every manifest entry must pin a non-empty
    DOM marker. An empty marker would silently skip verifyTarget's check,
    defeating the integrity guard, so validateManifest must refuse such a
    manifest up front (and the CLI must propagate the failure)."""
    manifest = json.loads(CORPUS_MANIFEST.read_text())
    # Empty marker
    manifest["entries"][0]["expectedDOMMarker"] = ""
    bad = tmp_path / "empty_marker.json"
    bad.write_text(json.dumps(manifest))
    r = _run(["--url", CAPTURE_URL, "--manifest", str(bad),
              "--out", str(tmp_path / "out"), "--dry-run"])
    assert r.returncode != 0, (
        f"validateManifest must reject an entry with empty expectedDOMMarker; "
        f"got stdout={r.stdout!r} stderr={r.stderr!r}"
    )
    assert "expectedDOMMarker" in r.stderr or "DOM marker" in r.stderr, (
        f"empty-marker rejection error must name the missing field; "
        f"got stderr={r.stderr!r}"
    )
    # Missing key entirely (unrelated to empty string) is also rejected.
    del manifest["entries"][0]["expectedDOMMarker"]
    bad2 = tmp_path / "missing_marker.json"
    bad2.write_text(json.dumps(manifest))
    r2 = _run(["--url", CAPTURE_URL, "--manifest", str(bad2),
               "--out", str(tmp_path / "out2"), "--dry-run"])
    assert r2.returncode != 0, (
        "validateManifest must reject an entry missing expectedDOMMarker"
    )
