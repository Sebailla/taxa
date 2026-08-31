"""Focused tests for the G4 capture producer (slice 1).

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

Slice 1 ships the producer framework + dry-run capture. Real Lighthouse
execution is G4-capture-2. Approach A / B / C atomic-cut selection is NOT
made here; static export remains unselected.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
CAPTURE = REPO_ROOT / "tools" / "g4-capture"
SCRIPT = CAPTURE / "scripts" / "capture.mjs"
PKG = CAPTURE / "package.json"
LOCK = CAPTURE / "package-lock.json"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "g4"
CORPUS_MANIFEST = FIXTURES / "corpus" / "manifest.json"
CORPUS_INDEX = FIXTURES / "corpus" / "index.html"
SQLITE_MANIFEST = FIXTURES / "sqlite" / "MANIFEST.json"
SQLITE_DB = FIXTURES / "sqlite" / "taxa-fixture.db"
SQLITE_HASH = FIXTURES / "sqlite" / "taxa-fixture.db.sha256"


def _run(args, **kwargs):
    return subprocess.run(["node", str(SCRIPT), *args], capture_output=True, text=True, **kwargs)


# ── Pinned workspace ──────────────────────────────────────────────
def test_workspace_lockfile_pins_declared_dependencies():
    lock = json.loads(LOCK.read_text())
    root = lock["packages"][""]["dependencies"]
    assert root == json.loads(PKG.read_text())["dependencies"]


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