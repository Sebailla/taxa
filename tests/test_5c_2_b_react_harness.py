"""Focused hermetic tests for PR 5c.2-B.1b-ii-a (React FileExplorer fixture).

`tools/react-e2e-harness/scripts/fixture-server.mjs` is a pure-Node
in-process HTTP fixture for the isolated React FileExplorer harness,
serving the production `/api/taxon/1/files` + `/files/serve?path=…` shape.
`tools/react-e2e-harness/scripts/export-server.mjs` (PR 5c.2-B.1b-ii-b) is
a pure-Node static-export HTTP server: caller-supplied absolute export
root, `/` maps to `index.html`, exact files below root with appropriate
Content-Type (HTML/JS/MJS/CSS/JSON/images/fonts fallback binary), HEAD
mirrors GET headers with no body, traversal/directory leakage/unknown
paths fail-closed. Zero npm deps; caller-chosen or OS-assigned port
(never 8765); loopback-only default. Strict TDD: subprocess a Node server
per test, probe via Python HTTP. No Playwright / Chromium / FastAPI /
SQLite. Hermetic capture-driver tests, e2e selector modernization, legacy
deletion, G4 aggregation, G3 Tier-2 / G6 / PR 3e cutover all remain
deferred.
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
EXPORT_SERVER = REPO_ROOT / "tools" / "react-e2e-harness" / "scripts" / "export-server.mjs"
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



# ===========================================================================
# PR 5c.2-B.1b-ii-b — hermetic static-export HTTP server
# ===========================================================================
#
# `tools/react-e2e-harness/scripts/export-server.mjs` is a pure-Node
# static-export HTTP server for the isolated React harness. Caller-supplied
# absolute export root; `/` maps to `index.html`; exact files below root
# served with appropriate Content-Type; HEAD mirrors GET headers with no
# body; traversal / directory leakage / unknown paths fail-closed. Zero npm
# deps; caller-chosen or OS-assigned port; loopback default. No Playwright /
# Chromium / FastAPI / SQLite / production network. Each test creates a temp
# export tree via `tmp_path` — no Next build, no production fixtures, no
# Makefile target.

def _spawn_export(root, port):
    env = {**os.environ, "NODE_NO_WARNINGS": "1"}
    return subprocess.Popen(
        ["node", str(EXPORT_SERVER), "--port", str(port),
         "--host", "127.0.0.1", "--root", str(root)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
    )

def _wait_export_ready(proc, port, base, *, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            _, err = proc.communicate(timeout=1)
            raise RuntimeError(
                f"export-server exited early rc={proc.returncode} "
                f"stderr={err.decode(errors='replace')!r}"
            )
        try:
            s, _, _, _ = _http(f"{base}/", timeout=0.2)
            if s in (200, 404):
                return
        except Exception:
            pass
        time.sleep(0.05)
    proc.kill()
    _, err = proc.communicate(timeout=1)
    raise RuntimeError(
        f"export-server not ready on port {port}; "
        f"stderr={err.decode(errors='replace')!r}"
    )

@pytest.fixture
def exptree(tmp_path):
    """Tiny static-export tree: one file per supported MIME family plus a
    nested sub-directory (so we can probe exact-file-below-root vs
    directory-leakage behaviour)."""
    (tmp_path / "index.html").write_bytes(
        b"<!doctype html>\n<title>Export Index</title>\n"
    )
    (tmp_path / "app.js").write_bytes(b"console.log('app');\n")
    (tmp_path / "app.mjs").write_bytes(b"console.log('app mjs');\n")
    (tmp_path / "style.css").write_bytes(b"body { color: red; }\n")
    (tmp_path / "data.json").write_bytes(b'{"hello":"world"}\n')
    # 8-byte PNG signature followed by zeros — just enough to be a file.
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    # wOF2 magic + zeros (just enough to be a file).
    (tmp_path / "font.woff2").write_bytes(b"wOF2" + b"\x00" * 12)
    # Unknown extension — must fall back to application/octet-stream.
    (tmp_path / "weird.bin").write_bytes(b"\xff\x00\xff\x00\xff")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.html").write_bytes(b"<title>Nested</title>\n")
    return tmp_path

@pytest.fixture
def exp(exptree):
    """Spawn export-server on a free port against `exptree`; teardown."""
    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    proc = _spawn_export(exptree, port)
    _wait_export_ready(proc, port, base)
    try:
        yield {"port": port, "base": base, "proc": proc, "root": exptree}
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)

# ─── Source contract (RED gate) ────────────────────────────────────────
def test_export_server_module_exists_and_exports_start_server():
    """Export-server module exists AND exports startServer so the
    composition slice can spawn/teardown in-process."""
    assert EXPORT_SERVER.is_file(), f"missing: {EXPORT_SERVER}"
    assert "startServer" in EXPORT_SERVER.read_text(), (
        "must export startServer"
    )

def test_export_server_module_parses_with_node_check():
    """`node --check` succeeds so any subsequent import is safe."""
    proc = subprocess.run(
        ["node", "--check", str(EXPORT_SERVER)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, (
        f"node --check failed: {proc.stderr}"
    )

def test_export_server_module_has_zero_npm_dependencies():
    """Bare specifiers (no `node:` prefix, no relative path) are a
    fail-closed violation — the harness server must stay zero-dep."""
    for line in EXPORT_SERVER.read_text().splitlines():
        s = line.strip()
        if not s.startswith("import ") or " from " not in s:
            continue
        spec = s.split(" from ", 1)[1].strip().rstrip(";").strip("\'\"")
        if spec.startswith(("node:", "./", "../")):
            continue
        pytest.fail(f"export-server imports non-built-in: {line!r}")

# ─── CLI gating (root is mandatory + absolute) ─────────────────────────
def test_export_server_missing_root_rejected(tmp_path):
    """A non-existent `--root` MUST make the CLI exit non-zero with a clear
    error line — no silent fallback, no auto-create."""
    bogus = tmp_path / "does-not-exist"
    proc = subprocess.run(
        ["node", str(EXPORT_SERVER), "--port", str(_free_port()),
         "--host", "127.0.0.1", "--root", str(bogus)],
        capture_output=True, text=True, timeout=5,
    )
    assert proc.returncode != 0, (
        f"missing root must be rejected; got rc=0; "
        f"stderr={proc.stderr!r}"
    )

def test_export_server_no_root_flag_rejected():
    """`--root` is mandatory; omitting it MUST exit non-zero."""
    proc = subprocess.run(
        ["node", str(EXPORT_SERVER), "--port", str(_free_port()),
         "--host", "127.0.0.1"],
        capture_output=True, text=True, timeout=5,
    )
    assert proc.returncode != 0, (
        f"missing --root must be rejected; got rc=0; "
        f"stderr={proc.stderr!r}"
    )

def test_export_server_relative_root_rejected():
    """`--root` MUST be absolute; a relative path MUST exit non-zero."""
    proc = subprocess.run(
        ["node", str(EXPORT_SERVER), "--port", str(_free_port()),
         "--host", "127.0.0.1", "--root", "relative/dir"],
        capture_output=True, text=True, timeout=5,
    )
    assert proc.returncode != 0, (
        f"relative root must be rejected; got rc=0; "
        f"stderr={proc.stderr!r}"
    )

# ─── Start/stop lifecycle ──────────────────────────────────────────────
def test_export_server_serves_on_caller_chosen_port(exp):
    """startServer honours the explicit caller-provided port (no global
    hardcoded default; nothing hardcodes 8765)."""
    s, _, _, _ = _http(f"{exp['base']}/")
    assert s == 200

def test_export_server_os_assigned_port_zero_binds_and_is_distinct(exptree):
    """`--port 0` MUST let the OS assign a port, the CLI MUST print the
    bound port on stdout, and two such starts MUST receive distinct,
    reachable ports."""
    env = {**os.environ, "NODE_NO_WARNINGS": "1"}
    observed = []
    procs = []
    try:
        for _ in range(2):
            p = subprocess.Popen(
                ["node", str(EXPORT_SERVER), "--port", "0",
                 "--host", "127.0.0.1", "--root", str(exptree)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
            )
            assert p.stdout is not None, (
                "subprocess.PIPE was not wired to stdout"
            )
            line = p.stdout.readline().decode("utf-8", errors="replace").strip()
            m = re.search(r"port=(\d+)", line)
            assert m is not None, (
                f"export-server did not print `port=…` on stdout: {line!r}"
            )
            port = int(m.group(1))
            assert port > 0 and port < 65536, (
                f"OS-assigned port out of range: {port}"
            )
            procs.append(p)
            observed.append(port)
            s, _, _, _ = _http(f"http://127.0.0.1:{port}/")
            assert s == 200, f"OS-assigned port {port} not reachable"
        assert observed[0] != observed[1], (
            f"two `--port 0` starts collided on {observed[0]!r}; "
            "OS-assigned ports must be distinct"
        )
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=2)

def test_export_server_stop_releases_port(exp):
    """Stopping the export server frees the port (no stale listener)."""
    port = exp["port"]
    exp["proc"].terminate()
    exp["proc"].wait(timeout=2)
    with pytest.raises(Exception):
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            pass

# ─── `/` mapping ───────────────────────────────────────────────────────
def test_export_server_root_serves_index_html(exp):
    """`GET /` MUST return the export root's `index.html` with
    `Content-Type: text/html` — the harness browser loads the React app at
    the origin root, so `/` must resolve to the entry document."""
    s, h, body, _ = _http(f"{exp['base']}/")
    assert s == 200
    ct = h.get("content-type", "").lower()
    assert ct.startswith("text/html"), (
        f"GET / must be text/html; got {h.get('content-type')!r}"
    )
    assert b"<title>Export Index</title>" in body, (
        f"GET / must serve root index.html; body={body!r}"
    )

# ─── Content-Type per family ───────────────────────────────────────────
@pytest.mark.parametrize("relpath,expected_ct_prefix", [
    ("/index.html", "text/html"),
    ("/app.js", "application/javascript"),
    ("/app.mjs", "application/javascript"),
    ("/style.css", "text/css"),
    ("/data.json", "application/json"),
    ("/logo.png", "image/png"),
    ("/font.woff2", "font/woff2"),
])
def test_export_server_content_type(exp, relpath, expected_ct_prefix):
    """Each supported extension maps to the matching Content-Type prefix
    (HTML / JS / MJS / CSS / JSON / image / font). The harness's static
    export tree contains exactly these families; the server must serve every
    one of them with the right Content-Type so the browser picks the right
    parser."""
    s, h, body, _ = _http(f"{exp['base']}{relpath}")
    assert s == 200, f"{relpath}: status={s}"
    ct = h.get("content-type", "").lower()
    assert ct.startswith(expected_ct_prefix.lower()), (
        f"{relpath}: expected Content-Type prefix {expected_ct_prefix!r}; "
        f"got {h.get('content-type')!r}"
    )
    assert body, f"{relpath}: empty body"

def test_export_server_unknown_extension_falls_back_to_octet_stream(exp):
    """An unknown extension must fall back to `application/octet-stream`
    (binary) so the browser treats it as a download rather than rendering
    it as text."""
    s, h, body, _ = _http(f"{exp['base']}/weird.bin")
    assert s == 200
    assert h.get("content-type", "").lower().startswith(
        "application/octet-stream"
    ), (
        f"unknown extension must fall back to binary; "
        f"got {h.get('content-type')!r}"
    )
    assert body == b"\xff\x00\xff\x00\xff"

def test_export_server_nested_file_under_root(exp):
    """Exact files below the root are served recursively —
    `/sub/nested.html` must resolve to the file inside the `sub/`
    directory."""
    s, h, body, _ = _http(f"{exp['base']}/sub/nested.html")
    assert s == 200
    assert "text/html" in h.get("content-type", "").lower()
    assert b"<title>Nested</title>" in body

# ─── HEAD mirrors GET ──────────────────────────────────────────────────
def test_export_server_head_mirrors_get_headers(exp):
    """HEAD MUST return Content-Type + Content-Length matching GET (and no
    body) so probes can size the response without consuming it."""
    s_get, h_get, get_body, _ = _http(f"{exp['base']}/index.html")
    s_head, h_head, head_body, _ = _http(
        f"{exp['base']}/index.html", method="HEAD",
    )
    assert s_get == 200 and s_head == 200
    assert h_head.get("content-type") == h_get.get("content-type"), (
        f"HEAD Content-Type must equal GET; "
        f"HEAD={h_head.get('content-type')!r} "
        f"GET={h_get.get('content-type')!r}"
    )
    assert h_head.get("content-length") == h_get.get("content-length"), (
        f"HEAD Content-Length must equal GET; "
        f"HEAD={h_head.get('content-length')!r} "
        f"GET={h_get.get('content-length')!r}"
    )
    assert h_head.get("content-length") == str(len(get_body)), (
        "HEAD Content-Length must equal real body length"
    )
    assert head_body == b"", "HEAD must not return a body"

# ─── Traversal / fail-closed ───────────────────────────────────────────
@pytest.mark.parametrize("encoded,label", [
    ("..", "dotdot"),
    ("../../etc/passwd", "subpath"),
    ("%2Fetc%2Fpasswd", "absolute"),
    ("%2E%2E%2Fpasswd", "encoded"),
])
def test_export_server_traversal_fail_closed(exp, encoded, label):
    """`..` / `../../etc/passwd` / `/etc/passwd` / URL-encoded `../` all 404
    — the static server MUST NOT serve anything outside the root, and MUST
    NOT decode-then-serve any traversal pattern."""
    s, _, _, _ = _http(f"{exp['base']}/{encoded}")
    assert s == 404, f"{label}: traversal must 404; got {s}"

def test_export_server_directory_not_served(exp):
    """`/sub/` resolves to a directory inside the root; the server MUST
    404 it (no listing, no auto-append of `index.html` unless the URL path
    explicitly maps to it). No directory leakage."""
    s, _, _, _ = _http(f"{exp['base']}/sub/")
    assert s == 404, f"directory listing must 404; got {s}"

def test_export_server_unknown_route_returns_404(exp):
    """An exact path below the root that does not exist 404s — the server
    MUST NOT silently fall through to `index.html` (that would break React
    Router's deep-link handling)."""
    s, _, _, _ = _http(f"{exp['base']}/no-such-file.html")
    assert s == 404

# ─── Method guard ──────────────────────────────────────────────────────
def test_export_server_post_returns_405_with_allow(exp):
    """POST MUST return exactly 405 with `Allow: GET, HEAD` — the static
    export server is read-only; anything else must fail-closed."""
    s, h, _, _ = _http(f"{exp['base']}/index.html", method="POST")
    assert s == 405, f"POST must be exactly 405; got {s}"
    assert h.get("allow", "").upper().replace(" ", "") == "GET,HEAD", (
            f"POST must advertise `Allow: GET, HEAD`; "
            f"got {h.get('allow')!r}"
        )


# ===========================================================================
# PR 5c.2-B.1b-ii-c — hermetic composition slice (composeCapture + CLI driver)
# ===========================================================================
#
# `tools/react-e2e-harness/scripts/composed-capture.mjs` is the composition
# orchestrator wiring fixture-server.mjs (5c.2-B.1b-ii-a) + export-server.mjs
# (5c.2-B.1b-ii-b) + capture() (5c.2-B.1b-i) into one in-process + CLI driver.
# No npm deps; caller provides `--output-root`; never hard-codes ports;
# loopback-only host binding; taxon id restricted to the synthetic `1` the
# harness app + fixture serve; reverse-order cleanup on failure.
# Hermetic: subprocess a Node ESM probe; no Playwright / Chromium / FastAPI /
# SQLite / network. Injected `buildFn` / `captureFn` / `startFixtureFn` /
# `startExportFn` keep the orchestrator runnable without real npm build,
# real `playwright`, or external server modules.

COMPOSED_CAPTURE = REPO_ROOT / "tools" / "react-e2e-harness" / "scripts" / "composed-capture.mjs"
FIXTURE_SERVER = REPO_ROOT / "tools" / "react-e2e-harness" / "scripts" / "fixture-server.mjs"
EXPORT_SERVER = REPO_ROOT / "tools" / "react-e2e-harness" / "scripts" / "export-server.mjs"


def _run_node(script, *, timeout=10.0):
    """Run a Node ESM script via stdin; return (rc, stdout, stderr)."""
    p = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True, text=True, timeout=timeout,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    return p.returncode, p.stdout, p.stderr


# ─── Source contract (RED gate) ─────────────────────────────────────────
def test_composed_capture_module_exists_and_exports_compose_capture():
    """Composition module exists at the locked path AND exports
    `composeCapture` so the `make capture-react-e2e` target can spawn it.
    RED: pre-5c.2-B.1b-ii-c the file was absent and the import failed."""
    assert COMPOSED_CAPTURE.is_file(), f"missing: {COMPOSED_CAPTURE}"
    assert "composeCapture" in COMPOSED_CAPTURE.read_text(), "must export composeCapture"


def test_composed_capture_module_parses_with_node_check():
    """`node --check` succeeds so any subsequent import is safe."""
    p = subprocess.run(
        ["node", "--check", str(COMPOSED_CAPTURE)],
        capture_output=True, text=True,
    )
    assert p.returncode == 0, f"node --check failed: {p.stderr}"


def test_composed_capture_module_has_zero_npm_dependencies():
    """Bare specifiers (no `node:` prefix, no relative path) are a
    fail-closed violation — the harness must stay zero-dep."""
    for line in COMPOSED_CAPTURE.read_text().splitlines():
        s = line.strip()
        if not s.startswith("import ") or " from " not in s:
            continue
        spec = s.split(" from ", 1)[1].strip().rstrip(";").strip("'\"")
        if spec.startswith(("node:", "./", "../")):
            continue
        pytest.fail(f"composed-capture imports non-built-in: {line!r}")


# ─── CLI gating ─────────────────────────────────────────────────────────
def test_composed_capture_cli_missing_output_root_rejected():
    """No `--output-root` → CLI MUST exit non-zero with a clear error line.
    RED: pre-5c.2-B.1b-ii-c the file was absent and Node exited with a
    `MODULE_NOT_FOUND` style error before the explicit `missing
    --output-root` check existed."""
    p = subprocess.run(
        ["node", str(COMPOSED_CAPTURE)],
        capture_output=True, text=True, timeout=5,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    assert p.returncode != 0, (
        f"missing --output-root must be rejected; got rc=0; "
        f"stderr={p.stderr!r}"
    )
    combined = (p.stderr + p.stdout).lower()
    assert "output-root" in combined, (
        f"error line must name `--output-root`; got stderr={p.stderr!r}"
    )


def test_composed_capture_cli_rejects_non_loopback_host():
    """`--host 0.0.0.0` MUST exit non-zero BEFORE binding any listener."""
    p = subprocess.run(
        ["node", str(COMPOSED_CAPTURE),
         "--output-root", "/tmp/cap-cc-host", "--host", "0.0.0.0"],
        capture_output=True, text=True, timeout=5,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    assert p.returncode != 0, f"non-loopback host must be rejected; rc=0 stderr={p.stderr!r}"
    combined = (p.stderr + p.stdout).lower()
    assert "loopback" in combined, (
        f"error must mention loopback-only; got stderr={p.stderr!r}"
    )


def test_composed_capture_cli_rejects_other_taxon_id():
    """`--taxon-id 2` MUST exit non-zero (harness serves only id 1)."""
    p = subprocess.run(
        ["node", str(COMPOSED_CAPTURE),
         "--output-root", "/tmp/cap-cc-taxon", "--taxon-id", "2"],
        capture_output=True, text=True, timeout=5,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    assert p.returncode != 0, f"taxon-id 2 must be rejected; rc=0 stderr={p.stderr!r}"
    combined = (p.stderr + p.stdout).lower()
    assert "taxon" in combined, (
        f"error must mention taxon; got stderr={p.stderr!r}"
    )


# ─── Validation primitives ──────────────────────────────────────────────
def test_composed_capture_validate_taxon_id_accepts_one_only():
    """`validateTaxonId(\"1\")` → 1; every other positive integer / zero /
    negative / non-numeric input MUST throw before any server binds."""
    script = (
        f'import {{ validateTaxonId }} from "file://{COMPOSED_CAPTURE}";\n'
        "const one = validateTaxonId('1');\n"
        "if (one !== 1) { console.error('returned ' + one); process.exit(2); }\n"
        "for (const bad of ['2', '42', '0', '-1', 'abc', '1.5', '']) {\n"
        "  try { validateTaxonId(bad); console.error('accepted ' + JSON.stringify(bad)); process.exit(3); }\n"
        "  catch (e) { /* expected */ }\n"
        "}\n"
        "console.log('ok');\n"
    )
    rc, out, err = _run_node(script)
    assert rc == 0, f"node failed: rc={rc} stderr={err!r}"


def test_composed_capture_validate_host_loopback_only():
    """`validateHost` accepts 127.0.0.1 / ::1 / localhost and the default;
    EVERY other host MUST throw before any server binds."""
    script = (
        f'import {{ validateHost }} from "file://{COMPOSED_CAPTURE}";\n'
        "for (const good of ['127.0.0.1', '::1', 'localhost']) {\n"
        "  if (validateHost(good) !== good) { console.error('rejected ' + good); process.exit(2); }\n"
        "}\n"
        "if (validateHost(undefined) !== '127.0.0.1') { console.error('default failed'); process.exit(4); }\n"
        "for (const bad of ['0.0.0.0', '10.0.0.1', '192.168.1.1', 'example.com', 'evil']) {\n"
        "  try { validateHost(bad); console.error('accepted ' + bad); process.exit(3); }\n"
        "  catch (e) { /* expected */ }\n"
        "}\n"
        "console.log('ok');\n"
    )
    rc, out, err = _run_node(script)
    assert rc == 0, f"node failed: rc={rc} stderr={err!r}"


# ─── In-process orchestration ───────────────────────────────────────────
def test_composed_capture_in_process_orchestration_with_synthetic_output_and_injected_capture(tmp_path):
    """`composeCapture` with a synthetic `out/index.html` + injected
    `buildFn` (no real `npm run build`) + injected `captureFn` (no real
    Chromium) returns the structured result; both real fixture / export
    servers bind loopback-only on OS-assigned ports and serve traffic."""
    harness = tmp_path / "harness"; harness.mkdir()
    out_dir = harness / "out"; out_dir.mkdir()
    (out_dir / "index.html").write_bytes(b"<title>synthetic harness</title>")
    capture = tmp_path / "capture"; capture.mkdir()
    script = (
        f'import {{ composeCapture, COMPOSED_CAPTURE_SCHEMA }} from "file://{COMPOSED_CAPTURE}";\n'
        f'const result = await composeCapture({{\n'
        f'  harnessDir: "{harness}",\n'
        f'  outputRoot: "{capture}",\n'
        "  buildFn: async () => ({ ok: true, stdout: 'synthetic', stderr: '' }),\n"
        "  captureFn: async ({ origin, outputRoot }) => {\n"
        "    if (!origin.startsWith('http://127.0.0.1:')) { console.error('bad origin ' + origin); process.exit(2); }\n"
        "    return { runDir: outputRoot + '/synthetic-run', evidence: { synthetic: true, origin } };\n"
        "  },\n"
        "});\n"
        "process.stdout.write(JSON.stringify({\n"
        "  schema: result.schema,\n"
        "  taxonId: result.taxonId,\n"
        "  fixtureBase: result.fixture.baseUrl,\n"
        "  exportBase: result.export.baseUrl,\n"
        "  captureRunDir: result.capture.runDir,\n"
        "  captureEvidence: result.capture.evidence,\n"
        "}) + '\\n');\n"
    )
    rc, out_s, err_s = _run_node(script, timeout=15.0)
    assert rc == 0, f"node failed: rc={rc} stderr={err_s!r} stdout={out_s!r}"
    payload = json.loads(out_s.strip())
    assert payload["schema"] == "taxa.react-e2e-composed-capture/1"
    assert payload["taxonId"] == HARNESS_TAXON_ID
    assert payload["fixtureBase"].startswith("http://127.0.0.1:")
    assert payload["exportBase"].startswith("http://127.0.0.1:")
    assert payload["captureEvidence"]["synthetic"] is True


def test_composed_capture_build_bypass_no_out_index_html_fails_closed(tmp_path):
    """Injected `buildFn` claims success but does NOT write
    `out/index.html`. `composeCapture` MUST throw BEFORE starting the
    export server or invoking `captureFn`; no evidence published;
    fixture port is still released on the way out."""
    harness = tmp_path / "harness"; harness.mkdir()  # NO out/!
    capture = tmp_path / "capture"; capture.mkdir()
    script = (
        f'import {{ composeCapture }} from "file://{COMPOSED_CAPTURE}";\n'
        "let exportStarted = false;\n"
        "let captureStarted = false;\n"
        "try {\n"
        f'  await composeCapture({{\n'
        f'    harnessDir: "{harness}",\n'
        f'    outputRoot: "{capture}",\n'
        "    buildFn: async () => ({ ok: true, stdout: '', stderr: '' }),\n"
        "    captureFn: async () => { captureStarted = true; return { runDir: 'x', evidence: {} }; },\n"
        f'    startExportFn: async (opts) => {{\n'
        "      exportStarted = true;\n"
        f'      const mod = await import("file://{EXPORT_SERVER}");\n'
        "      return mod.startServer(opts);\n"
        "    },\n"
        "  });\n"
        "  console.error('expected throw, got success'); process.exit(2);\n"
        "} catch (e) {\n"
        "  console.log(JSON.stringify({ error: e.message, exportStarted, captureStarted }));\n"
        "}\n"
    )
    rc, out_s, err_s = _run_node(script, timeout=10.0)
    assert rc == 0, f"node failed: rc={rc} stderr={err_s!r}"
    payload = json.loads(out_s.strip())
    assert "index.html" in payload["error"].lower(), (
        f"error must reference index.html; got {payload['error']!r}"
    )
    assert payload["exportStarted"] is False, (
        "export server MUST NOT start when build lacks out/index.html"
    )
    assert payload["captureStarted"] is False, (
        "captureFn MUST NOT run on build bypass"
    )


def test_composed_capture_reverse_order_cleanup_on_capture_failure(tmp_path):
    """`captureFn` throws → both fixture + export are closed; the export
    is closed BEFORE the fixture (reverse-order cleanup, per the nested
    `finally` blocks in `composeCapture`). Spies track close-call order
    via `startFixtureFn` / `startExportFn` injection seams."""
    harness = tmp_path / "harness"; harness.mkdir()
    out_dir = harness / "out"; out_dir.mkdir()
    (out_dir / "index.html").write_bytes(b"<title>synthetic harness</title>")
    capture = tmp_path / "capture"; capture.mkdir()
    script = (
        f'import {{ composeCapture }} from "file://{COMPOSED_CAPTURE}";\n'
        "let seq = 0;\n"
        "let fixtureCloseSeq = null;\n"
        "let exportCloseSeq = null;\n"
        "const startFixtureFn = async (opts) => {\n"
        f'  const mod = await import("file://{FIXTURE_SERVER}");\n'
        "  const h = await mod.startServer(opts);\n"
        "  return { ...h, async close() { fixtureCloseSeq = ++seq; await h.close(); } };\n"
        "};\n"
        "const startExportFn = async (opts) => {\n"
        f'  const mod = await import("file://{EXPORT_SERVER}");\n'
        "  const h = await mod.startServer(opts);\n"
        "  return { ...h, async close() { exportCloseSeq = ++seq; await h.close(); } };\n"
        "};\n"
        "try {\n"
        f'  await composeCapture({{\n'
        f'    harnessDir: "{harness}",\n'
        f'    outputRoot: "{capture}",\n'
        "    buildFn: async () => ({ ok: true }),\n"
        "    captureFn: async () => { throw new Error('capture intentionally failed'); },\n"
        "    startFixtureFn, startExportFn,\n"
        "  });\n"
        "  console.error('expected throw'); process.exit(2);\n"
        "} catch (e) {\n"
        "  console.log(JSON.stringify({ error: e.message, exportCloseSeq, fixtureCloseSeq }));\n"
        "}\n"
    )
    rc, out_s, err_s = _run_node(script, timeout=15.0)
    assert rc == 0, f"node failed: rc={rc} stderr={err_s!r}"
    payload = json.loads(out_s.strip())
    assert "capture intentionally failed" in payload["error"]
    assert payload["exportCloseSeq"] is not None, (
        "export.close() was never called on capture failure"
    )
    assert payload["fixtureCloseSeq"] is not None, (
        "fixture.close() was never called on capture failure"
    )
    assert payload["exportCloseSeq"] < payload["fixtureCloseSeq"], (
        f"reverse-order cleanup violated: export.close() must precede "
        f"fixture.close(); got export={payload['exportCloseSeq']} "
        f"fixture={payload['fixtureCloseSeq']}"
    )
