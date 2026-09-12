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
        else:
            self.send_response(404); self.end_headers()


@pytest.fixture()
def hermetic_server(tmp_path):
    """One document + one /api/ endpoint, deterministic."""
    page = (b"<!doctype html><html><head><title>g4 hermetic</title></head>"
            b"<body><div id=t>ok</div>"
            b"<script>fetch('/api/health').then(r=>r.json()).catch(()=>{});"
            b"</script></body></html>")
    _Handler.index_html = page
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
