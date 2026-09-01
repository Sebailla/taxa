"""Focused tests for the G3 legacy fixture (DB + tailwind + verifier) + G5 markers.

Scope (parent task — fixture only, no product behavior changes):
  - `tools/g3-legacy-fixture/taxa.db` — pre-seeded SQLite (taxon + vernacular).
  - `tools/g3-legacy-fixture/web/dist/tailwind.css` — required asset.
  - `tools/g3-legacy-fixture/web/index.html` + 10 module stubs.
  - `tools/g3-legacy-fixture/scripts/check_http_status.py` — controlled
    verifier that parses `curl -w '%{http_code}'` output and validates the
    captured status code(s) against the consumer's `verification.expect`
    value (fail-closed on mismatch; curl exit 0 ≠ HTTP 200).

G5 slice (chain PR 1) — deterministic hydration-readiness markers:
  - `web/index.html` carries four `data-testid` markers
    (`g5-shell-ready`, `g5-tree-ready`, `g5-search-ready`,
    `g5-keymap-ready`) as the deterministic contract for chain PR 2's
    Playwright capture to consume.
  - `web/app.js` flips `document.body.dataset.state` to
    `g5-keymap-ready` once the boot sequence wires the keyboard handler.
  - `web/tree.js` flips `#tree-view[data-state="ready"]` after the
    placeholder is in the DOM.
  The controlled FastAPI launcher that mounts the fixture is chain PR 2
  territory (restored from a preserved external patch) and is exercised
  by its own test module — not here.
"""
from __future__ import annotations

import html.parser
import http.server
import socket
import sqlite3
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


# ── G5 slice: deterministic hydration-readiness markers (chain PR 1) ──────
# The G5 hydration baseline (design.md §3.3.5) needs deterministic markers
# the chain PR 2 Playwright + Lighthouse capture can diff baseline-vs-candidate
# against. This PR ships the markers themselves; the controlled FastAPI
# launcher that mounts the fixture is chain PR 2 territory (restored from a
# preserved external patch).
G5_HYDRATION_MARKERS = (
    "g5-shell-ready",
    "g5-tree-ready",
    "g5-keymap-ready",
    "g5-search-ready",
)


def test_g5_index_html_has_all_hydration_readiness_markers():
    """The fixture's index.html MUST carry `data-testid` markers for each
    of the G5 hydration readiness signals. Chain PR 2 reads these markers
    via Playwright; the marker names are the public contract."""
    html = (FIXTURE / "web" / "index.html").read_text()
    for marker in G5_HYDRATION_MARKERS:
        assert f'data-testid="{marker}"' in html, (
            f"index.html missing G5 hydration marker "
            f"data-testid={marker!r}; chain PR 2 reads it via Playwright"
        )


class _HydrationMarkerFinder(html.parser.HTMLParser):
    """Walk the parsed DOM and record per-element `data-testid` attrs.

    Unlike a browser, html.parser does NOT dedupe duplicate attributes per
    the HTML5 spec — it preserves every (name, value) pair it reads. That
    is exactly what we want here: the regression guard below catches
    source-level bugs where two data-testid attrs share one element (a
    browser would silently keep only the first and break the all-four
    marker contract for chain PR 2's capture)."""
    def __init__(self):
        super().__init__()
        self.per_element_testids: list[tuple[str, list[str]]] = []
        self.testids: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = [v for k, v in attrs if k == "data-testid" and v]
        self.per_element_testids.append((tag, values))
        self.testids.extend(values)


def test_g5_index_html_hydration_markers_unique_in_parsed_dom():
    """Regression guard: every G5 hydration-readiness `data-testid` MUST
    be observable in the parsed DOM (visible to Playwright), AND no
    element may carry more than one `data-testid` attribute.

    Browsers drop subsequent duplicate attrs per HTML5 spec, so a fixture
    that relies on duplicate attributes exposes only the first to
    Playwright — silently breaking the all-four-marker contract. The
    file-level substring check above cannot detect this masking; only
    parsing the DOM can.

    Historical regression: index.html originally carried both
    `data-testid="g5-shell-ready"` and `data-testid="g5-keymap-ready"` on
    `<body>`. The substring marker test passed, but Playwright only saw
    the first attribute. This test catches that."""
    html = (FIXTURE / "web" / "index.html").read_text()
    finder = _HydrationMarkerFinder()
    finder.feed(html)
    for marker in G5_HYDRATION_MARKERS:
        assert finder.testids.count(marker) == 1, (
            f"data-testid={marker!r} must appear exactly once in the "
            f"parsed DOM; got {finder.testids.count(marker)} "
            f"(parsed markers: {finder.testids!r})"
        )
    duplicates = [
        (tag, vals)
        for tag, vals in finder.per_element_testids
        if len(vals) > 1
    ]
    assert duplicates == [], (
        "index.html has elements with duplicate data-testid attrs; "
        "browsers keep only the first per HTML5 spec, which silently "
        "disables the later marker for Playwright. Found: "
        f"{duplicates!r}"
    )


def test_g5_app_js_wires_keymap_ready_state():
    """app.js MUST register the G5 keymap-ready state on `document.body`
    when the boot sequence wires the keyboard handler. Without this,
    chain PR 2's Playwright capture cannot distinguish 'keymap wired'
    from 'keymap pending'."""
    src = (FIXTURE / "web" / "app.js").read_text()
    assert "g5-keymap-ready" in src, (
        "app.js must register a g5-keymap-ready state on document.body"
    )


def test_g5_tree_js_marks_tree_view_ready_after_render():
    """tree.js MUST mark `#tree-view[data-state='ready']` after the
    tree's first render. The marker is chain PR 2's signal for
    'tree first-paint reached'."""
    src = (FIXTURE / "web" / "tree.js").read_text()
    assert "tree-view" in src and "ready" in src, (
        "tree.js must wire the #tree-view data-state='ready' marker"
    )


# ── G5 launcher (chain PR 1) ─────────────────────────────────────────────
# The launcher (`tools/g3-legacy-fixture/scripts/g5_legacy_asgi.py`)
# mounts the fixture in front of `api.server.app`, rewiring
# `api.server.DB_PATH` to the fixture SQLite and prepending a
# `Mount("/")` so fixture static wins over the production root mount.
LAUNCHER_DIR = FIXTURE / "scripts"
LAUNCHER_NAME = "g5_legacy_asgi"


@pytest.fixture(scope="module")
def launcher_module():
    """Import the G5 launcher, snapshot+restore `api.server` state.

    The launcher rewires `api.server.DB_PATH` and inserts a `Mount`
    into `api.server.app.router.routes`. Without snapshot+restore,
    those mutations leak into the next collected test module:
    test_smoke's module-level `from api.server import DB_PATH`
    captures the pristine reference at load time, so the stale
    local `DB_PATH` (production path, not exists) lets
    `test_health_endpoint_returns_503_without_db` skip its
    DB-exists guard and fail the 503 expectation with the
    fixture-backed 200.
    """
    launcher_dir = str(LAUNCHER_DIR.resolve())
    if launcher_dir not in sys.path:
        sys.path.insert(0, launcher_dir)
    import importlib
    import api.server as _srv
    # Snapshot pristine state BEFORE the launcher's top-level code
    # mutates anything. `original_routes` is a shallow list copy so
    # the launcher's `_routes.insert(...)` doesn't mutate the snapshot.
    original_db_path = _srv.DB_PATH
    original_routes = list(_srv.app.router.routes)
    mod = importlib.import_module(LAUNCHER_NAME)
    yield mod
    # Restore pristine state. `importlib.reload(...)` tests below
    # may add multiple fixture Mounts; the snapshot is the pristine
    # list captured above so a single assignment suffices.
    _srv.DB_PATH = original_db_path
    _srv.app.router.routes = original_routes


@pytest.fixture(scope="module")
def launcher_client(launcher_module):
    from fastapi.testclient import TestClient
    return TestClient(launcher_module.app)


@pytest.mark.parametrize("case_id", [
    "import_contract_is_api_server_app",
    "web_dir_unchanged",
    "index_html_is_fixture_bytes",
    "api_health_uses_fixture_db",
    "missing_static_returns_404",
])
def test_g5_launcher_contract(case_id, launcher_module, launcher_client):
    """Compact contract block: the 5 launch-time guarantees chain PR 2
    relies on (import contract, WEB_DIR preserved, fixture static wins,
    /api/health reads fixture DB, missing static returns 404)."""
    import api.server as srv
    if case_id == "import_contract_is_api_server_app":
        assert launcher_module.app is srv.app, (
            f"launcher.app must be api.server.app "
            f"(got {launcher_module.app!r})"
        )
    elif case_id == "web_dir_unchanged":
        assert srv.WEB_DIR == REPO_ROOT / "web", (
            f"api.server.WEB_DIR must be unchanged "
            f"(got {srv.WEB_DIR}, expected {REPO_ROOT / 'web'})"
        )
        assert "g3-legacy-fixture" not in str(srv.WEB_DIR), (
            f"api.server.WEB_DIR must not reference fixture path "
            f"(got {srv.WEB_DIR})"
        )
    elif case_id == "index_html_is_fixture_bytes":
        r = launcher_client.get("/index.html")
        assert r.status_code == 200, r.status_code
        assert b"G3 legacy fixture" in r.content, (
            "/index.html must serve fixture bytes (G3 marker missing); "
            "fixture mount is not winning over the production root mount"
        )
    elif case_id == "api_health_uses_fixture_db":
        r = launcher_client.get("/api/health")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["db"].endswith("g3-legacy-fixture/taxa.db"), (
            f"/api/health must read fixture DB; got db={body.get('db')!r}"
        )
    else:  # missing_static_returns_404
        r = launcher_client.get("/not-in-fixture.html")
        assert r.status_code == 404, (
            f"missing static file must 404 (got {r.status_code})"
        )


@pytest.mark.parametrize("scenario", ["missing_db", "empty_db"])
def test_g5_launcher_fails_when_db_missing_or_empty(
        scenario, tmp_path, launcher_module):
    """Fail-closed: the launcher's DB validator rejects a missing or
    empty file with RuntimeError. The launcher's own import-time check
    already passed (the real fixture DB exists), so we exercise the
    validator with synthetic inputs here."""
    target = tmp_path / "taxa.db"
    if scenario == "empty_db":
        target.write_bytes(b"")
    with pytest.raises(RuntimeError, match="fail-closed"):
        launcher_module._require_nonempty_file(target, "fixture DB")


# ── G5 launcher: import-time fail-closed (not merely unit-call) ─────
# The previous block proves the validators work as units. The tests
# below prove the SAME validators are wired at module top-level
# (executed at `import g5_legacy_asgi` time, not just callable). We
# `importlib.reload` the launcher after monkey-patching one Path
# method so the real FIXTURE_DB / FIXTURE_WEB look missing/empty;
# reload re-runs top-level code → import-time check fires → RuntimeError.
# The DB check fires FIRST, before DB rewire and Mount insert, so a
# failed reload leaves `api.server.app.router.routes` unchanged.
def test_g5_launcher_fails_closed_at_import_when_db_missing(
        monkeypatch, launcher_module):
    """Import-time: missing FIXTURE_DB → RuntimeError on module load.
    Proves `_require_nonempty_file(FIXTURE_DB, ...)` is wired at top-level."""
    import importlib
    orig = Path.is_file
    def fake(self):
        if "g3-legacy-fixture/taxa.db" in str(self):
            return False
        return orig(self)
    monkeypatch.setattr(Path, "is_file", fake)
    with pytest.raises(RuntimeError, match="fail-closed"):
        importlib.reload(launcher_module)


def test_g5_launcher_fails_closed_at_import_when_db_empty(
        monkeypatch, launcher_module):
    """Import-time: empty FIXTURE_DB → RuntimeError on module load."""
    import importlib
    from types import SimpleNamespace
    orig = Path.stat
    def fake(self):
        if "g3-legacy-fixture/taxa.db" in str(self):
            return SimpleNamespace(st_size=0)
        return orig(self)
    monkeypatch.setattr(Path, "stat", fake)
    with pytest.raises(RuntimeError, match="fail-closed"):
        importlib.reload(launcher_module)


def test_g5_launcher_fails_closed_at_import_when_web_dir_missing(
        monkeypatch, launcher_module):
    """Import-time: missing FIXTURE_WEB → RuntimeError on module load.
    Proves `_require_nonempty_dir(FIXTURE_WEB, ...)` is wired at top-level."""
    import importlib
    orig = Path.is_dir
    def fake(self):
        if "g3-legacy-fixture/web" in str(self):
            return False
        return orig(self)
    monkeypatch.setattr(Path, "is_dir", fake)
    with pytest.raises(RuntimeError, match="fail-closed"):
        importlib.reload(launcher_module)


def test_g5_launcher_fails_closed_at_import_when_web_dir_empty(
        monkeypatch, launcher_module):
    """Import-time: empty FIXTURE_WEB (dir exists but iterdir() == []) →
    RuntimeError on module load."""
    import importlib
    orig = Path.iterdir
    def fake(self):
        if "g3-legacy-fixture/web" in str(self):
            return iter([])
        return orig(self)
    monkeypatch.setattr(Path, "iterdir", fake)
    with pytest.raises(RuntimeError, match="fail-closed"):
        importlib.reload(launcher_module)


def test_g5_launcher_no_route_pollution_after_failed_reload(
        monkeypatch, launcher_module):
    """Negative control: a failed import-time reload does NOT leave a
    second fixture `Mount` in `api.server.app.router.routes`. The DB
    check fires before the rewiring + insert, so the routes list stays
    exactly the size of the pre-reload baseline. Catches a regression
    where the check runs after the Mount insert."""
    import importlib
    orig = Path.is_file
    def fake(self):
        if "g3-legacy-fixture/taxa.db" in str(self):
            return False
        return orig(self)
    monkeypatch.setattr(Path, "is_file", fake)
    import api.server as srv
    before = len(srv.app.router.routes)
    with pytest.raises(RuntimeError, match="fail-closed"):
        importlib.reload(launcher_module)
    assert len(srv.app.router.routes) == before, (
        f"failed reload must not duplicate the fixture mount; "
        f"routes {before} → {len(srv.app.router.routes)}"
    )
