"""Focused hermetic tests for PR 5c.2-B.1b-ii-a (React FileExplorer fixture).

`tools/react-e2e-harness/scripts/fixture-server.mjs` is a pure-Node
in-process HTTP fixture for the isolated React FileExplorer harness,
serving the production `/api/taxon/1/files` + `/files/serve?path=…` shape.
Zero npm deps; caller-chosen or OS-assigned port (never 8765); only
taxon id 1; unknown routes / unknown taxon / invalid traversal all
rejected fail-closed. Strict TDD: subprocess a Node fixture per test,
probe via Python HTTP. No Playwright / Chromium / FastAPI / SQLite.
Composition slice (5c.2-B.1b-ii-b), hermetic driver tests, e2e selector
modernization, legacy deletion, G4 aggregation, G3 Tier-2 / G6 / PR 3e
cutover all remain deferred.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tools" / "react-e2e-harness" / "scripts" / "fixture-server.mjs"
HARNESS_TAXON_ID = 1


def _free_port():
    with socket.socket() as s: s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


def _http(url, *, method="GET", timeout=2.0):
    """(status, headers-lower, body-bytes, parsed-json-or-None). 4xx surfaces
    as `(e.code, headers, body, parsed)`; transport errors raise."""
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body, headers, status = resp.read(), {k.lower(): v for k, v in resp.headers.items()}, resp.status
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        headers = {k.lower(): v for k, v in (e.headers or {}).items()}; status = e.code
    parsed = None
    if "application/json" in headers.get("content-type", "").lower():
        try: parsed = json.loads(body)
        except Exception: parsed = None
    return status, headers, body, parsed


def _spawn(port):
    env = {**os.environ, "NODE_NO_WARNINGS": "1"}
    return subprocess.Popen(["node", str(FIXTURE), "--port", str(port), "--host", "127.0.0.1"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)


def _wait_ready(proc, port, base, *, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            _, err = proc.communicate(timeout=1)
            raise RuntimeError(f"fixture exited early rc={proc.returncode} stderr={err.decode(errors='replace')!r}")
        try:
            s, _, _, _ = _http(f"{base}/api/taxon/1/files", timeout=0.2)
            if s in (200, 404): return
        except Exception: pass
        time.sleep(0.05)
    proc.kill(); _, err = proc.communicate(timeout=1)
    raise RuntimeError(f"fixture not ready on port {port}; stderr={err.decode(errors='replace')!r}")


@pytest.fixture
def fx():
    port = _free_port(); base = f"http://127.0.0.1:{port}"; proc = _spawn(port); _wait_ready(proc, port, base)
    try: yield {"port": port, "base": base, "proc": proc}
    finally:
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=2)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=2)


# ─── Source contract (RED gate) ─────────────────────────────────────────
def test_module_exists_and_exports_start_server():
    """Fixture module exists at the locked path AND exports startServer so
    the next composition slice can spawn/teardown in-process."""
    assert FIXTURE.is_file(), f"missing: {FIXTURE}"
    assert "startServer" in FIXTURE.read_text(), "must export startServer"


def test_module_parses_with_node_check():
    """`node --check` succeeds so any subsequent import is safe."""
    proc = subprocess.run(["node", "--check", str(FIXTURE)], capture_output=True, text=True)
    assert proc.returncode == 0, f"node --check failed: {proc.stderr}"


def test_module_has_zero_npm_dependencies():
    """Bare specifiers (no `node:` prefix, no relative path) are a
    fail-closed violation — the harness must stay zero-dep."""
    for line in FIXTURE.read_text().splitlines():
        s = line.strip()
        if not s.startswith("import ") or " from " not in s: continue
        spec = s.split(" from ", 1)[1].strip().rstrip(";").strip("'\"")
        if spec.startswith(("node:", "./", "../")): continue
        pytest.fail(f"fixture imports non-built-in: {line!r}")


# ─── Start/stop lifecycle ───────────────────────────────────────────────
def test_serves_on_caller_chosen_port(fx):
    """startServer honours the explicit caller-provided port (no global hardcoded default)."""
    s, _, _, _ = _http(f"{fx['base']}/api/taxon/1/files"); assert s == 200


def test_os_assigned_ports_are_unique_legacy(fx):
    """Legacy companion: two starts on caller-reserved ports stay independent.
    Retained as a smoke check that reserving + binding a specific port works;
    the strict `--port 0` exercise lives in the next test."""
    p2 = _free_port(); assert p2 != fx["port"]
    p = _spawn(p2); b = f"http://127.0.0.1:{p2}"
    try:
        _wait_ready(p, p2, b)
        assert fx["proc"].poll() is None and p.poll() is None
        s1, _, _, _ = _http(f"{fx['base']}/api/taxon/1/files")
        s2, _, _, _ = _http(f"{b}/api/taxon/1/files")
        assert s1 == 200 and s2 == 200
    finally:
        if p.poll() is None: p.terminate(); p.wait(timeout=2)


def test_os_assigned_port_zero_binds_and_is_distinct(fx):
    """`--port 0` MUST let the OS assign a port, the CLI MUST print the
    bound port on stdout, and two such starts MUST receive distinct,
    reachable ports — the previous test only reserved a port number, it
    never exercised the actual OS-assignment path."""
    env = {**os.environ, "NODE_NO_WARNINGS": "1"}
    observed = []
    procs = []
    try:
        for _ in range(2):
            p = subprocess.Popen(
                ["node", str(FIXTURE), "--port", "0", "--host", "127.0.0.1"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
            )
            assert p.stdout is not None, "subprocess.PIPE was not wired to stdout"
            line = p.stdout.readline().decode("utf-8", errors="replace").strip()
            m = re.search(r"port=(\d+)", line)
            assert m is not None, f"fixture did not print `port=…` on stdout: {line!r}"
            port = int(m.group(1))
            assert port > 0 and port < 65536, f"OS-assigned port out of range: {port}"
            procs.append(p); observed.append(port)
            # The bound port must actually serve the envelope (reachable).
            s, _, _, _ = _http(f"http://127.0.0.1:{port}/api/taxon/1/files")
            assert s == 200, f"OS-assigned port {port} not reachable"
        assert observed[0] != observed[1], (
            f"two `--port 0` starts collided on {observed[0]!r}; "
            "OS-assigned ports must be distinct"
        )
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
                try: p.wait(timeout=2)
                except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=2)


def test_stop_releases_port(fx):
    """Stopping the fixture frees the port (no stale listener)."""
    port = fx["port"]; fx["proc"].terminate(); fx["proc"].wait(timeout=2)
    with pytest.raises(Exception):
        with socket.create_connection(("127.0.0.1", port), timeout=0.5): pass


# ─── /api/taxon/1/files envelope ───────────────────────────────────────
def test_files_envelope_has_production_shape(fx):
    """Envelope matches `FilesEnvelope` from research-file.ts: exists,
    taxon_id, taxon_name, taxon_path, filesystem_path, subpath, root.
    Folders before files; both case-insensitive. Every file carries the
    wire shape (name, path, extension, size, modified)."""
    s, h, _, p = _http(f"{fx['base']}/api/taxon/1/files")
    assert s == 200 and "application/json" in h["content-type"].lower()
    for k in ("exists", "taxon_id", "taxon_name", "taxon_path",
              "filesystem_path", "subpath", "root"):
        assert k in p, f"missing envelope key: {k}"
    assert p["exists"] is True and p["taxon_id"] == HARNESS_TAXON_ID and p["subpath"] is None
    root = p["root"]; assert root["type"] == "folder" and root["path"] == ""
    children = root["children"]; assert len(children) >= 4
    folder_names = [c["name"] for c in children if c["type"] == "folder"]
    file_names = [c["name"] for c in children if c["type"] == "file"]
    assert folder_names == sorted(folder_names, key=str.casefold)
    assert file_names == sorted(file_names, key=str.casefold)
    # Contract: folders precede files (within every folder, recursively).
    # The previous test only checked intra-bucket ordering — a single
    # folder at index 3 with files at indices 0..2 would silently pass.
    folder_indices = [i for i, c in enumerate(children) if c["type"] == "folder"]
    file_indices = [i for i, c in enumerate(children) if c["type"] == "file"]
    assert folder_indices and file_indices, "fixture must contain both folders and files"
    assert max(folder_indices) < min(file_indices), (
        f"folders must precede files; got child types in order: "
        f"{[c['type'] for c in children]}"
    )
    exts = {c["extension"] for c in children if c["type"] == "file"}
    for need in ("html", "md", "txt", "pdf"):
        assert need in exts, f"fixture missing .{need}; got {exts}"
    folders = [c for c in children if c["type"] == "folder"]
    assert folders and folders[0]["children"] and folders[0]["children"][0]["type"] == "file"
    for c in children:
        if c["type"] != "file": continue
        assert isinstance(c["size"], int) and c["size"] >= 0 and "T" in c["modified"]


# ─── /files/serve content types ────────────────────────────────────────
@pytest.mark.parametrize("filename,expected_ct", [
    ("index.html", "text/html"), ("notes.md", "text/markdown"),
    ("readme.txt", "text/plain"), ("paper.pdf", "application/pdf"),
])
def test_serve_returns_correct_content_type(fx, filename, expected_ct):
    """Each fixture format returns the matching Content-Type (mirrors
    api/server.py::_CONTENT_TYPE_BY_EXT) and Content-Disposition: inline;
    filename="<basename>". PDF fixture starts with the %PDF- magic."""
    s, h, body, _ = _http(f"{fx['base']}/api/taxon/1/files/serve?path={urllib.parse.quote(filename)}")
    assert s == 200
    assert h["content-type"].lower().startswith(expected_ct)
    cd = h.get("content-disposition", "")
    assert cd.startswith("inline;") and f'filename="{filename}"' in cd
    assert len(body) > 0
    if expected_ct == "application/pdf": assert body[:5] == b"%PDF-"


# ─── /serve traversal / fail-closed ─────────────────────────────────────
@pytest.mark.parametrize("encoded,label", [
    ("..", "dotdot"), ("../../etc/passwd", "subpath"),
    ("%2Fetc%2Fpasswd", "absolute"), ("%2E%2E%2Fpasswd", "encoded"),
])
def test_serve_traversal_fail_closed(fx, encoded, label):
    """path='..' / '../../etc/passwd' / '/etc/passwd' / URL-encoded '../'
    all return 400 with a clear fail-closed detail. No decoding bypass."""
    s, _, _, p = _http(f"{fx['base']}/api/taxon/1/files/serve?path={encoded}")
    assert s == 400, f"{label}: status={s}"
    detail = (p or {}).get("detail", "")
    assert "escapes" in detail.lower() or "invalid" in detail.lower(), detail


def test_serve_missing_path_rejected(fx):
    """No `path` query parameter → 400. Never silently serves the root."""
    s, _, _, p = _http(f"{fx['base']}/api/taxon/1/files/serve"); assert s == 400 and p and p.get("detail")


def test_serve_unknown_file_inside_root_returns_404(fx):
    """A path that resolves INSIDE the root but doesn't exist → 404."""
    s, _, _, p = _http(f"{fx['base']}/api/taxon/1/files/serve?path=missing.txt")
    assert s == 404 and "not found" in (p or {}).get("detail", "").lower()


# ─── Fail-closed: unknown taxon / unknown route / wrong method ─────────
def test_unknown_taxon_files_returns_404(fx):
    """GET /api/taxon/2/files returns 404 — only taxon id 1 is known."""
    s, _, _, p = _http(f"{fx['base']}/api/taxon/2/files")
    assert s == 404 and "not found" in (p or {}).get("detail", "").lower()


def test_unknown_taxon_serve_returns_404(fx):
    """GET /api/taxon/2/files/serve returns 404 — same single-taxon guard."""
    s, _, _, p = _http(f"{fx['base']}/api/taxon/2/files/serve?path=index.html")
    assert s == 404 and "not found" in (p or {}).get("detail", "").lower()


def test_unknown_route_returns_404(fx):
    """Routes outside the two-file whitelist return 404, not the envelope."""
    s, _, _, _ = _http(f"{fx['base']}/api/taxon/1/materialize"); assert s == 404


def test_post_to_files_endpoint_returns_405_with_allow(fx):
    """POST /files MUST return exactly 405 with `Allow: GET, HEAD` —
    read-only fixture. The previous `s in (405, 404)` accepted a stray
    404 and accepted missing/wrong Allow headers."""
    s, h, _, _ = _http(f"{fx['base']}/api/taxon/1/files", method="POST")
    assert s == 405, f"POST /files must be exactly 405; got {s}"
    assert h.get("allow", "").upper().replace(" ", "") == "GET,HEAD", (
        f"POST /files must advertise `Allow: GET, HEAD`; got {h.get('allow')!r}"
    )


def test_post_to_files_serve_returns_405_with_allow(fx):
    """POST /files/serve MUST return exactly 405 with `Allow: GET, HEAD` —
    symmetric contract with `/files`."""
    s, h, _, _ = _http(
        f"{fx['base']}/api/taxon/1/files/serve?path=index.html", method="POST"
    )
    assert s == 405, f"POST /files/serve must be exactly 405; got {s}"
    assert h.get("allow", "").upper().replace(" ", "") == "GET,HEAD", (
        f"POST /files/serve must advertise `Allow: GET, HEAD`; "
        f"got {h.get('allow')!r}"
    )


# ─── Method = HEAD must mirror GET headers (no body) ───────────────────
def test_head_on_files_endpoint_mirrors_get_headers(fx):
    """HEAD /files MUST return Content-Type + Content-Length matching GET
    (and no body). The previous handler sent an empty 200 with no
    metadata — clients can't tell envelope size without GET."""
    s_get, h_get, get_body, _ = _http(f"{fx['base']}/api/taxon/1/files")
    s_head, h_head, head_body, _ = _http(
        f"{fx['base']}/api/taxon/1/files", method="HEAD"
    )
    assert s_get == 200 and s_head == 200
    assert "application/json" in h_head.get("content-type", "").lower(), (
        f"HEAD /files must advertise JSON; got {h_head.get('content-type')!r}"
    )
    assert h_head.get("content-length") == h_get.get("content-length"), (
        f"HEAD Content-Length must equal GET Content-Length; "
        f"HEAD={h_head.get('content-length')!r} GET={h_get.get('content-length')!r}"
    )
    assert head_body == b"", "HEAD must not return a body"


@pytest.mark.parametrize("filename,expected_ct", [
    ("index.html", "text/html"), ("paper.pdf", "application/pdf"),
])
def test_head_on_files_serve_mirrors_get_headers(fx, filename, expected_ct):
    """HEAD /files/serve MUST mirror GET's Content-Type + Content-Length
    (and Content-Disposition when present) so probes work without a body."""
    qs = urllib.parse.quote(filename)
    s_get, h_get, get_body, _ = _http(
        f"{fx['base']}/api/taxon/1/files/serve?path={qs}"
    )
    s_head, h_head, head_body, _ = _http(
        f"{fx['base']}/api/taxon/1/files/serve?path={qs}", method="HEAD"
    )
    assert s_get == 200 and s_head == 200, (
        f"GET/HEAD mismatch for {filename}: get={s_get} head={s_head}"
    )
    assert h_head.get("content-type", "").lower().startswith(expected_ct.lower()), (
        f"HEAD Content-Type for {filename} must start with {expected_ct!r}; "
        f"got {h_head.get('content-type')!r}"
    )
    assert h_head.get("content-length") == h_get.get("content-length"), (
        f"HEAD Content-Length must equal GET Content-Length for {filename}; "
        f"HEAD={h_head.get('content-length')!r} GET={h_get.get('content-length')!r}"
    )
    assert h_head.get("content-length") == str(len(get_body)), (
        f"HEAD Content-Length for {filename} must equal real body length"
    )
    assert head_body == b"", f"HEAD must not return a body for {filename}"


# ─── Backslash separator must normalize before lookup ──────────────────
def test_serve_normalizes_backslash_separator(fx):
    """URL-encoded backslash (`%5C` → `\\`) MUST be normalized to `/`
    before the corpus lookup, otherwise a request like
    `Papers%5Clynx.pdf` resolves to `Papers\\lynx.pdf` (which is NOT in
    the corpus) and spuriously 404s — a valid normalized fixture path
    never 404s."""
    s, h, body, _ = _http(
        f"{fx['base']}/api/taxon/1/files/serve?path=Papers%5Clynx.pdf"
    )
    assert s == 200, (
        f"backslash-normalized path must resolve to fixture entry; "
        f"got status={s}"
    )
    assert h.get("content-type", "").lower().startswith("application/pdf")
    assert body[:5] == b"%PDF-"
