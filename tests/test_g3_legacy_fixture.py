"""Focused tests for the G3 legacy fixture (DB + tailwind + verifier).

Scope (parent task — fixture only, no product behavior changes):
  - `tools/g3-legacy-fixture/taxa.db` — pre-seeded SQLite (taxon + vernacular).
  - `tools/g3-legacy-fixture/web/dist/tailwind.css` — required asset.
  - `tools/g3-legacy-fixture/web/index.html` + 10 module stubs.
  - `tools/g3-legacy-fixture/scripts/check_http_status.py` — controlled
    verifier that parses `curl -w '%{http_code}'` output and validates the
    captured status code(s) against the consumer's `verification.expect`
    value (fail-closed on mismatch; curl exit 0 ≠ HTTP 200).
"""
from __future__ import annotations

import http.server
import sqlite3
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tools" / "g3-legacy-fixture"
WEB = FIXTURE / "web"
DB_PATH = FIXTURE / "taxa.db"
CHECK_HTTP = FIXTURE / "scripts" / "check_http_status.py"
SEED_DB = FIXTURE / "scripts" / "seed_db.py"
SIBLINGS = ("state", "api", "tree", "breadcrumb", "detail", "nav",
            "dom", "banner", "help", "keymap")


@pytest.fixture(scope="session")
def seeded_db() -> Path:
    SEED_DB.parent.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.is_file() or DB_PATH.stat().st_size == 0:
        subprocess.run([sys.executable, str(SEED_DB), str(DB_PATH)],
                       check=True, capture_output=True)
    return DB_PATH


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        pass


@pytest.fixture(scope="session")
def served_legacy():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    s.close()
    handler = lambda *a, **kw: _SilentHandler(*a, directory=str(WEB), **kw)
    server = http.server.HTTPServer(("127.0.0.1", port), handler)
    th = threading.Thread(target=server.serve_forever, daemon=True); th.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try: urllib.request.urlopen(f"{base}/index.html", timeout=1).read(); break
        except OSError: time.sleep(0.05)
    try: yield base
    finally: server.shutdown(); th.join(timeout=5)


def _check(command: str, expected: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CHECK_HTTP), command, expected],
                          capture_output=True, text=True, check=False)


def _count(db, table):
    if table not in {"taxon", "vernacular"}:
        raise ValueError(f"unsupported fixture table: {table}")
    return sqlite3.connect(db).execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]


# ── DB fixture tests ─────────────────────────────────────────────────
def test_fixture_db_exists(seeded_db):
    assert DB_PATH.is_file() and DB_PATH.stat().st_size > 0


def test_fixture_db_has_taxon_and_vernacular(seeded_db):
    assert _count(seeded_db, "taxon") >= 1
    assert _count(seeded_db, "vernacular") >= 1


def test_fixture_db_no_orphan_vernaculars(seeded_db):
    """Every vernacular.taxon_id must resolve to a taxon row."""
    conn = sqlite3.connect(seeded_db)
    orphans = conn.execute(
        "SELECT v.taxon_id FROM vernacular v "
        "LEFT JOIN taxon t ON t.id = v.taxon_id WHERE t.id IS NULL"
    ).fetchall(); conn.close()
    assert orphans == [], f"orphan vernaculars: {orphans}"


def test_fixture_db_tiger_links_to_panthera_tigris(seeded_db):
    """Spot-check: 'Tiger' → Panthera tigris, language=eng, country=US."""
    conn = sqlite3.connect(seeded_db)
    row = conn.execute(
        "SELECT t.scientific_name, v.language, v.country FROM vernacular v "
        "JOIN taxon t ON t.id = v.taxon_id WHERE v.name = 'Tiger'"
    ).fetchone(); conn.close()
    assert row == ("Panthera tigris", "eng", "US"), row


# ── Web asset tests ──────────────────────────────────────────────────
def test_tailwind_asset_present_and_nonempty():
    p = WEB / "dist" / "tailwind.css"
    assert p.is_file() and p.stat().st_size > 100


def test_index_html_references_tailwind_and_app_js():
    html = (WEB / "index.html").read_text()
    assert 'rel="stylesheet"' in html and "dist/tailwind.css" in html
    assert 'type="module"' in html and "app.js" in html


def test_app_js_present_and_imports_all_10_sibling_modules():
    src = (WEB / "app.js").read_text()
    for m in SIBLINGS:
        assert f"{m}.js" in src, f"app.js missing import of {m}.js"
        assert (WEB / f"{m}.js").is_file(), f"missing {m}.js"


# ── Controlled verifier HTTP-status enforcement tests ────────────────
def test_check_http_accepts_matching_status(served_legacy):
    base = served_legacy
    r = _check(f"curl -sS -o /dev/null -w '%{{http_code}}' {base}/index.html", "200")
    assert r.returncode == 0, r.stderr


def test_check_http_rejects_404_against_expect_200(served_legacy):
    """curl prints 404 but exits 0 → controlled verifier must reject (fail-closed)."""
    base = served_legacy
    r = _check(f"curl -sS -o /dev/null -w '%{{http_code}}' {base}/missing.html", "200")
    assert r.returncode != 0, r.stderr
    assert "404" in r.stderr or "mismatch" in r.stderr.lower(), r.stderr


def test_check_http_loop_all_match(served_legacy):
    """A `for m in ... do curl ...` loop emitting 10 status codes validates
    each against the expected value (legacy pre-cut manifest pattern)."""
    base = served_legacy
    cmd = (f"for m in state api tree breadcrumb detail nav dom banner help keymap; do "
           f"curl -sS -o /dev/null -w '%{{http_code}}' {base}/$m.js; done")
    assert _check(cmd, "200 for each").returncode == 0


def test_check_http_loop_one_mismatch_rejected(served_legacy):
    """One missing module in the loop → curl emits 404 → verifier rejects."""
    base = served_legacy
    cmd = (f"for m in state api missing_module keymap; do "
           f"curl -sS -o /dev/null -w '%{{http_code}}' {base}/$m.js; done")
    r = _check(cmd, "200 for each")
    assert r.returncode != 0 and "404" in r.stderr, r.stderr


def test_check_http_for_each_suffix_normalised(served_legacy):
    """'200' and '200 for each' are equivalent expected values."""
    base = served_legacy
    r = _check(f"curl -sS -o /dev/null -w '%{{http_code}}' {base}/app.js", "200 for each")
    assert r.returncode == 0, r.stderr


def test_check_http_non_http_command_passes_when_shell_exits_0():
    """Non-HTTP commands (e.g. ':') → verifier falls back to shell exit only."""
    assert _check(":", "ok").returncode == 0


def test_check_http_rejects_value_mismatch(served_legacy):
    """Triangulate: 200 response is rejected when expected=300 (no false-positive)."""
    base = served_legacy
    r = _check(f"curl -sS -o /dev/null -w '%{{http_code}}' {base}/index.html", "300")
    assert r.returncode != 0 and "mismatch" in r.stderr.lower(), r.stderr


def test_check_http_usage_error_on_wrong_arg_count():
    r = subprocess.run([sys.executable, str(CHECK_HTTP)],
                       capture_output=True, text=True, check=False)
    assert r.returncode != 0 and "usage" in r.stderr.lower(), r.stderr
    # ── G3 slice: complete legacy fixture asset coverage ─────────────────
    # The cutover-manifest's `verification.command` curl loop for the
    # nav.js-imported modules (`mount-runtime-import-nav-js-modules-007`)
    # names 6 modules: detail, search, tree, state, api, dom. The
    # manifest additionally references 4 single-file consumers that
    # require settings.js, file_explorer.js, format.js, file_viewer.js
    # (consumers 006, 008, 009, 010, 011, 012). Together with the existing
    # 10 app.js-imported modules, every legacy asset referenced by the
    # manifest MUST be present in the fixture so the controlled verifier
    # can pass when the legacy runtime is faithfully reproduced.
LEGACY_NAVLESS_STUBS = (
    "settings", "search", "file_explorer", "format", "file_viewer",
)

def test_fixture_serves_all_legacy_manifest_referenced_stubs(served_legacy):
    """Every .js stub referenced by the manifest's HTTP-shaped
    verification commands is served by the fixture at HTTP 200.
    Catches a regression where the verifier would silently pass
    because curl exits 0 even on 404."""
    base = served_legacy
    for stub in LEGACY_NAVLESS_STUBS:
        with urllib.request.urlopen(f"{base}/{stub}.js", timeout=2) as r:
            assert r.status == 200, f"{stub}.js not served (got {r.status})"

def test_legacy_manifest_navjs_loop_validates_against_fixture(served_legacy):
    """The cutover-manifest's nav.js-imported modules loop
    (`for m in detail search tree state api dom; do curl ...`) MUST
    pass end-to-end against the fixture (all 200s)."""
    base = served_legacy
    cmd = (f"for m in detail search tree state api dom; do "
           f"curl -sS -o /dev/null -w '%{{http_code}}' {base}/$m.js; done")
    assert _check(cmd, "200 for each").returncode == 0

def test_legacy_manifest_combined_file_explorer_settings_validates(
        served_legacy):
    """The cutover-manifest's combined `curl ... && curl ...`
    consumer (008: file_explorer.js + settings.js) MUST validate
    end-to-end against the fixture."""
    base = served_legacy
    cmd = (f"curl -sS -o /dev/null -w '%{{http_code}}' "
           f"{base}/file_explorer.js && "
           f"curl -sS -o /dev/null -w '%{{http_code}}' {base}/settings.js")
    assert _check(cmd, "200 for each").returncode == 0

def test_legacy_manifest_single_file_assets_all_200(served_legacy):
    """The cutover-manifest's single-file consumers (format.js x2,
    file_explorer.js, file_viewer.js, settings.js) MUST all
    validate end-to-end against the fixture."""
    base = served_legacy
    for stub in LEGACY_NAVLESS_STUBS:
        r = _check(
            f"curl -sS -o /dev/null -w '%{{http_code}}' {base}/{stub}.js",
            "200")
        assert r.returncode == 0, f"{stub}.js not 200: {r.stderr}"
