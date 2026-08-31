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

import hashlib
import importlib
import json
import os
import sqlite3
import subprocess
import sys
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


def _run_capture_with_runner(tmp_path, *, synthetic_lhr=None, runner_throws=False,
                              runner_invocation=None, dry_run=False):
    """Hermetic helper: write a Node wrapper that imports capture.mjs and calls
    it with an injected runner. Captures stdout/stderr/returncode. No real
    browser is launched; the runner is replaced by a closure over the supplied
    `synthetic_lhr`. `runner_invocation` (if supplied) is a callable that
    receives (lhr, args) and may record invocations for assertion.
    """
    out_dir = tmp_path / "out"
    invocation_log = tmp_path / "_invocations.json"
    log_literal = json.dumps(str(invocation_log))
    if runner_throws:
        runner_impl = "throw new Error('synthetic runner failure');"
    else:
        runner_impl = (
            f"const __lhr = {json.dumps(synthetic_lhr or {})};\n"
            f"await __log({{ runnerArgs: __runnerArgs, args: __args }});\n"
            f"return __lhr;"
        )
    script = (
        "import { capture, readJson } from "
        + json.dumps("file://" + str(SCRIPT))
        + ";\n"
        f"const manifest = await readJson({json.dumps(str(CORPUS_MANIFEST))});\n"
        f"const __invocationLogPath = {log_literal};\n"
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
def test_capture_dry_run_writes_evidence_with_provenance(tmp_path):
    out = tmp_path / "out"
    r = _run(["--url", "http://127.0.0.1:8765/index.html",
              "--manifest", str(CORPUS_MANIFEST), "--out", str(out), "--dry-run"])
    assert r.returncode == 0, r.stderr
    evidence = json.loads((out / "evidence.json").read_text())
    assert evidence["schema"] == "taxa.g4-capture.evidence/1"
    p = evidence["provenance"]
    assert p["schema"] == "taxa.g4-capture.provenance/1"
    assert p["nodeVersion"].startswith("v")
    snap = json.loads((out / "manifest.snapshot.json").read_text())
    assert snap == json.loads(CORPUS_MANIFEST.read_text())


def test_capture_dry_run_rejects_url_not_in_manifest(tmp_path):
    out = tmp_path / "out"
    r = _run(["--url", "http://unknown.example.test/",
              "--manifest", str(CORPUS_MANIFEST), "--out", str(out), "--dry-run"])
    assert r.returncode != 0 and "url not in manifest" in r.stderr


# ── Triangulate: atomic-write + schema enforcement ─────────────────
def test_atomic_write_replaces_existing_outdir(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.txt").write_text("stale")
    r = _run(["--url", "http://127.0.0.1:8765/index.html",
              "--manifest", str(CORPUS_MANIFEST), "--out", str(out), "--dry-run"])
    assert r.returncode == 0, r.stderr
    assert not (out / "stale.txt").exists(), "stale file must be replaced"
    assert (out / "evidence.json").is_file()


def test_validate_manifest_rejects_wrong_schema(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema": "wrong.schema/0", "entries": []}))
    r = _run(["--url", "http://127.0.0.1:8765/index.html",
              "--manifest", str(bad), "--out", str(tmp_path / "out"), "--dry-run"])
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


def test_cli_without_dry_run_fails_closed_until_real_runner_invoked(tmp_path):
    """Capture-2 contract: when --dry-run is omitted, the CLI must invoke
    the real chrome-launcher + lighthouse runner. In this hermetic test
    (no browser available) the run is expected to fail closed with no
    evidence.json published."""
    out = tmp_path / "out"
    r = _run(["--url", "http://127.0.0.1:8765/index.html",
              "--manifest", str(CORPUS_MANIFEST), "--out", str(out)])
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
    expected_web_dir = str((REPO_ROOT / "web").resolve())
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
