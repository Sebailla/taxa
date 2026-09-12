"""G4 producer tests — combined navigation + /api/ capture (PR3d slice).

Reference: design.md §3.3.4 (G4) and the schema pinned by
scripts/verify_parity.py. Hermetic http.server fixture serves a
deterministic page that fires one document load + one /api/ XHR so no
live API / network is required. Playwright availability is probed the
same way as tests/test_e2e_file_explorer.py — CI without a browser
skips cleanly. Exit-code contract: 1 usage, 2 browser, 3 zero nav, 4 write.
"""
from __future__ import annotations

import http.server
import json
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "capture_parity_reports.py"
VERIFY_PARITY = REPO_ROOT / "scripts" / "verify_parity.py"
ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"
SCHEMA_VERSION = "1.0.0"


def _free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close(); return port


def _wait_ready(url: str, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1): return True
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            time.sleep(0.05)
    return False


def _playwright_importable() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


_NEEDS_BROWSER = pytest.mark.skipif(
    not _playwright_importable(),
    reason="playwright not installed (pip install playwright)",
)


class _Handler(http.server.BaseHTTPRequestHandler):
    index_html: bytes = b""
    api_body: bytes = b'{"ok":true}'
    # Per-query result counts for /api/search — keys are the decoded `q` values.
    search_counts: dict[str, int] = {}

    def log_message(self, *args, **kwargs):
        return

    def do_GET(self):  # noqa: N802 — http.server convention
        if self.path in ("/", "/index.html"):
            body = self.index_html
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)
        elif self.path == "/api/health":
            body = self.api_body
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)
        elif self.path.startswith("/api/search"):
            q = parse_qs(urlparse(self.path).query, keep_blank_values=True).get("q", [""])[0]
            count = self.search_counts.get(q, 0)
            body = json.dumps({"count": count}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)
        else:
            self.send_response(404); self.end_headers()


_SEARCH_QUERIES = ("cat", "dog", "cat species", "cat&dog")


def _build_hermetic_page() -> bytes:
    """Page that fires /api/health plus a /api/search?q=<enc> fetch for each
    known query. encodeURIComponent URL-encodes the wire form so the server
    sees q=cat%20species, q=cat%26dog, etc."""
    fetches = b"fetch('/api/health').then(r=>r.json()).catch(()=>{});"
    for q in _SEARCH_QUERIES:
        # json.dumps produces a valid JS string literal (handles &, spaces, etc.).
        fetches += (
            b"fetch('/api/search?q=' + encodeURIComponent("
            + json.dumps(q).encode()
            + b")).then(r=>r.json()).catch(()=>{});"
        )
    return (
        b"<!doctype html><html><head><title>g4 hermetic</title></head>"
        b"<body><div id=t>ok</div><script>" + fetches + b"</script></body></html>"
    )


@pytest.fixture()
def hermetic_server(tmp_path):
    """One document + /api/health + /api/search?q=<query> endpoints, deterministic.
    The default page fires fetches for the four known _SEARCH_QUERIES so any
    subset can be requested via --queries."""
    _Handler.index_html = _build_hermetic_page()
    _Handler.search_counts = {
        "cat": 5, "dog": 12, "cat species": 7, "cat&dog": 42,
    }
    port = _free_port()
    server = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    th = threading.Thread(target=server.serve_forever, daemon=True); th.start()
    base = f"http://127.0.0.1:{port}"
    try:
        if not _wait_ready(f"{base}/index.html"):
            raise RuntimeError("hermetic server failed to start")
        yield base
    finally:
        server.shutdown(); th.join(timeout=3)


@pytest.fixture()
def hermetic_factory(tmp_path):
    """Factory for hermetic servers with custom page + search_counts. Yields
    a callable that returns the base URL; teardown shuts the server down."""
    started: list[tuple[http.server.HTTPServer, threading.Thread]] = []

    def _start(*, page: bytes, search_counts: dict[str, int] | None = None) -> str:
        _Handler.index_html = page
        if search_counts is not None:
            _Handler.search_counts = search_counts
        port = _free_port()
        server = http.server.HTTPServer(("127.0.0.1", port), _Handler)
        th = threading.Thread(target=server.serve_forever, daemon=True)
        th.start()
        base = f"http://127.0.0.1:{port}"
        started.append((server, th))
        if not _wait_ready(f"{base}/index.html"):
            raise RuntimeError("hermetic factory server failed to start")
        return base

    yield _start
    for server, th in started:
        server.shutdown(); th.join(timeout=3)


def _run(args, *, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd or REPO_ROOT, capture_output=True, text=True, check=False,
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime(ISO_FMT)


def _parse_iso(s: str) -> datetime:
    return datetime.strptime(s, ISO_FMT).replace(tzinfo=timezone.utc)


# CLI contract (no browser needed)
def test_script_exists():
    assert SCRIPT.is_file(), f"missing script: {SCRIPT}"


def test_exits_one_on_no_args():
    """No-argument invocation must exit 1 (invalid CLI)."""
    r = _run([])
    assert r.returncode == 1, r.stderr
    assert "usage" in (r.stdout + r.stderr).lower()


def test_exits_one_on_missing_url(tmp_path):
    """--out-dir without --url must exit 1."""
    r = _run(["--out-dir", str(tmp_path)])
    assert r.returncode == 1, r.stderr


def test_exits_one_on_missing_out_dir():
    """--url without --out-dir must exit 1."""
    r = _run(["--url", "http://127.0.0.1:1/"])
    assert r.returncode == 1, r.stderr


# schema + happy path (browser required)
@_NEEDS_BROWSER
def test_emits_navigation_and_api_atomically(tmp_path, hermetic_server):
    """Happy path: both reports emitted, atomic, schema-compliant."""
    out_dir = tmp_path / "reports"
    r = _run(["--url", f"{hermetic_server}/", "--out-dir", str(out_dir)])
    assert r.returncode == 0, f"stderr={r.stderr}\nstdout={r.stdout}"
    nav = out_dir / "navigation.json"
    api = out_dir / "api.json"
    assert nav.is_file() and api.is_file()
    assert sorted(p.name for p in out_dir.iterdir()) == ["api.json", "navigation.json"]
    nav_doc = json.loads(nav.read_text())
    api_doc = json.loads(api.read_text())
    for doc, key in ((nav_doc, "paths"), (api_doc, "endpoints")):
        assert doc["schema_version"] == SCHEMA_VERSION
        assert doc["captured_at"] == _parse_iso(doc["captured_at"]).strftime(ISO_FMT)
        assert isinstance(doc[key], list) and doc[key], f"{key} must be a non-empty list"
    assert any(p["path"] == "/" and p["status"] == 200 for p in nav_doc["paths"])
    assert any(e["path"] == "/api/health" and e["status"] == 200
               for e in api_doc["endpoints"])


@_NEEDS_BROWSER
def test_api_filter_only_captures_api_paths(tmp_path, hermetic_server):
    """Non-/api/ requests must NOT leak into api.json."""
    out_dir = tmp_path / "reports"
    r = _run(["--url", f"{hermetic_server}/", "--out-dir", str(out_dir)])
    assert r.returncode == 0, r.stderr
    api_doc = json.loads((out_dir / "api.json").read_text())
    nav_doc = json.loads((out_dir / "navigation.json").read_text())
    for endpoint in api_doc["endpoints"]:
        assert "/api/" in endpoint["path"], f"non-/api/ leaked: {endpoint}"
    for nav in nav_doc["paths"]:
        assert "/api/" not in nav["path"], f"/api/ leaked to nav: {nav}"


@_NEEDS_BROWSER
def test_output_validates_against_verify_parity(tmp_path, hermetic_server):
    """Emitted reports must round-trip through scripts/verify_parity.py
    as both legacy + candidate (other three reports are placeholders)."""
    out_dir = tmp_path / "legacy"
    r = _run(["--url", f"{hermetic_server}/", "--out-dir", str(out_dir)])
    assert r.returncode == 0, r.stderr
    # REQUIRED_BROWSER_STATE_KEYS in verify_parity.py — values are placeholders.
    for name, doc in (
        ("search", {"queries": [{"query": "q", "result_count": 1}]}),
        ("a11y", {"score": 1.0}),
        ("browser-state", {"keys": {"last-taxon-id": None, "tree-source": None,
            "selected-realm": None, "version-banner-dismissed": None}}),
    ):
        full = {"schema_version": SCHEMA_VERSION, "captured_at": _now_iso(), **doc}
        (out_dir / f"{name}.json").write_text(json.dumps(full))
    vp = subprocess.run(
        [sys.executable, str(VERIFY_PARITY),
         "--legacy-dir", str(out_dir), "--candidate-dir", str(out_dir),
         "--output", str(tmp_path / "agg"), "--max-staleness-days", "30"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert vp.returncode == 0, (
        f"verify_parity rejected the producer output.\n"
        f"stdout={vp.stdout}\nstderr={vp.stderr}"
    )


# fail-closed branches
@_NEEDS_BROWSER
def test_browser_failure_yields_no_output(tmp_path):
    """Unreachable --url must exit 2 (browser failure) and write nothing."""
    out_dir = tmp_path / "reports"
    bad_url = f"http://127.0.0.1:{_free_port()}/"
    r = _run(["--url", bad_url, "--out-dir", str(out_dir)])
    assert r.returncode == 2, (
        f"expected exit 2 on browser failure; got {r.returncode}.\nstderr={r.stderr}"
    )
    assert not out_dir.exists() or list(out_dir.iterdir()) == [], (
        "must NOT publish partial reports on browser failure"
    )


@_NEEDS_BROWSER
def test_write_failure_emits_no_partial_output(tmp_path, hermetic_server):
    """If writing fails mid-emit, neither report must land on disk."""
    out_dir = tmp_path / "reports"
    out_dir.mkdir()
    # Directory at navigation.json makes the atomic rename target fail.
    (out_dir / "navigation.json").mkdir()
    r = _run(["--url", f"{hermetic_server}/", "--out-dir", str(out_dir)])
    assert r.returncode == 4, (
        f"expected exit 4 on write failure; got {r.returncode}.\nstderr={r.stderr}"
    )
    assert not (out_dir / "api.json").exists(), (
        "must NOT leave api.json when navigation write fails"
    )


# ── search-only G4 extension (PR3e slice) ─────────────────────────────────
# The producer adds an explicit --queries flag and emits search.json when
# provided. When --queries is omitted, CLI flags and the precise two-report
# set (navigation.json + api.json) are preserved exactly.


@_NEEDS_BROWSER
def test_emits_search_when_queries_provided(tmp_path, hermetic_server):
    """Focused RED: --queries 'cat dog' must emit search.json with both
    queries in user order and result_counts parsed from /api/search bodies.
    navigation.json + api.json still emit, and search.json is appended
    atomically."""
    out_dir = tmp_path / "reports"
    r = _run(["--url", f"{hermetic_server}/", "--out-dir", str(out_dir),
              "--queries", "cat", "dog"])
    assert r.returncode == 0, f"stderr={r.stderr}\nstdout={r.stdout}"
    assert sorted(p.name for p in out_dir.iterdir()) == [
        "api.json", "navigation.json", "search.json",
    ], list(out_dir.iterdir())
    search_doc = json.loads((out_dir / "search.json").read_text())
    assert search_doc["schema_version"] == SCHEMA_VERSION
    assert search_doc["captured_at"] == _parse_iso(
        search_doc["captured_at"]).strftime(ISO_FMT)
    assert search_doc["queries"] == [
        {"query": "cat", "result_count": 5},
        {"query": "dog", "result_count": 12},
    ], search_doc["queries"]


@_NEEDS_BROWSER
def test_search_url_encoded_query_with_space(tmp_path, hermetic_server):
    """A user query with a space must match an /api/search?q=cat%20species
    response via URL-decoded exact comparison (not substring matching)."""
    out_dir = tmp_path / "reports"
    r = _run(["--url", f"{hermetic_server}/", "--out-dir", str(out_dir),
              "--queries", "cat species"])
    assert r.returncode == 0, f"stderr={r.stderr}\nstdout={r.stdout}"
    search_doc = json.loads((out_dir / "search.json").read_text())
    assert search_doc["queries"] == [
        {"query": "cat species", "result_count": 7},
    ], search_doc["queries"]


@_NEEDS_BROWSER
def test_search_special_char_query(tmp_path, hermetic_server):
    """A query containing `&` must round-trip through URL encoding
    (q=cat%26dog) and match the decoded value exactly."""
    out_dir = tmp_path / "reports"
    r = _run(["--url", f"{hermetic_server}/", "--out-dir", str(out_dir),
              "--queries", "cat&dog"])
    assert r.returncode == 0, f"stderr={r.stderr}\nstdout={r.stdout}"
    search_doc = json.loads((out_dir / "search.json").read_text())
    assert search_doc["queries"] == [
        {"query": "cat&dog", "result_count": 42},
    ], search_doc["queries"]


@_NEEDS_BROWSER
def test_search_exact_match_rejects_substring(tmp_path, hermetic_factory):
    """When only ?q=caterpillar is captured, --queries 'cat' must NOT
    substring-match it. Producer fails closed with no partial reports.
    Proves exact parsed-q matching, not substring matching."""
    page = (b"<!doctype html><html><body>"
            b"<script>fetch('/api/search?q=caterpillar').catch(()=>{});"
            b"</script></body></html>")
    base = hermetic_factory(page=page, search_counts={"caterpillar": 99})
    out_dir = tmp_path / "reports"
    r = _run(["--url", f"{base}/", "--out-dir", str(out_dir),
              "--queries", "cat"])
    assert r.returncode != 0, (
        f"expected failure when 'cat' has no exact /api/ match; "
        f"got {r.returncode}.\nstderr={r.stderr}"
    )
    if out_dir.exists():
        assert list(out_dir.iterdir()) == [], (
            f"must NOT emit partial reports on search mismatch: "
            f"{list(out_dir.iterdir())}"
        )


@_NEEDS_BROWSER
def test_no_queries_omits_search_json(tmp_path, hermetic_server):
    """PR #223 behavior is preserved exactly when --queries is omitted:
    the CLI must emit navigation.json + api.json only — no search.json."""
    out_dir = tmp_path / "reports"
    r = _run(["--url", f"{hermetic_server}/", "--out-dir", str(out_dir)])
    assert r.returncode == 0, f"stderr={r.stderr}\nstdout={r.stdout}"
    assert sorted(p.name for p in out_dir.iterdir()) == [
        "api.json", "navigation.json",
    ], list(out_dir.iterdir())
    assert not (out_dir / "search.json").exists(), (
        "search.json must NOT be emitted when --queries is omitted"
    )


@_NEEDS_BROWSER
def test_search_write_failure_rolls_back_all(tmp_path, hermetic_server):
    """When --queries is provided and search.json write fails, neither
    navigation.json nor api.json may remain on disk — full atomic rollback
    across the three-report set."""
    out_dir = tmp_path / "reports"
    out_dir.mkdir()
    # Block the search.json atomic-rename target so its write fails.
    (out_dir / "search.json").mkdir()
    r = _run(["--url", f"{hermetic_server}/", "--out-dir", str(out_dir),
              "--queries", "cat"])
    assert r.returncode == 4, (
        f"expected exit 4 on search write failure; got {r.returncode}.\n"
        f"stderr={r.stderr}"
    )
    assert not (out_dir / "navigation.json").exists(), (
        "must NOT leave navigation.json when search write fails"
    )
    assert not (out_dir / "api.json").exists(), (
        "must NOT leave api.json when search write fails"
    )


@_NEEDS_BROWSER
def test_search_validates_against_verify_parity(tmp_path, hermetic_server):
    """End-to-end round trip: emit all three reports with --queries, add
    a11y + browser-state placeholders, run verify_parity with
    legacy-dir == candidate-dir == out_dir, and assert exit 0. Proves the
    search.json shape satisfies verify_parity exactly."""
    out_dir = tmp_path / "reports"
    r = _run(["--url", f"{hermetic_server}/", "--out-dir", str(out_dir),
              "--queries", "cat", "dog"])
    assert r.returncode == 0, f"stderr={r.stderr}\nstdout={r.stdout}"
    for name, doc in (
        ("a11y", {"score": 1.0}),
        ("browser-state", {"keys": {"last-taxon-id": None, "tree-source": None,
            "selected-realm": None, "version-banner-dismissed": None}}),
    ):
        full = {"schema_version": SCHEMA_VERSION, "captured_at": _now_iso(), **doc}
        (out_dir / f"{name}.json").write_text(json.dumps(full))
    vp = subprocess.run(
        [sys.executable, str(VERIFY_PARITY),
         "--legacy-dir", str(out_dir), "--candidate-dir", str(out_dir),
         "--output", str(tmp_path / "agg"), "--max-staleness-days", "30"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert vp.returncode == 0, (
        f"verify_parity rejected the search producer output.\n"
        f"stdout={vp.stdout}\nstderr={vp.stderr}"
    )
