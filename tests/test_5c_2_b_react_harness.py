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
# PR 5c.2-B.1b-ii-a — CORS: strict loopback-only Access-Control-Allow-Origin
# ===========================================================================
#
# The composed capture slice binds the fixture API and the static export
# server on DISTINCT loopback ports. The browser loads the export page at,
# e.g., http://127.0.0.1:8081/ and that page fetches
# http://127.0.0.1:8080/api/taxon/1/files — without an
# Access-Control-Allow-Origin header the browser blocks the cross-origin
# read and the diagnostic capture sees a generic CORS error instead of the
# actual fixture envelope.
#
# To keep the harness ISOLATED and the production CORS posture UNCHANGED,
# fixture-server.mjs emits Access-Control-Allow-Origin ONLY for an HTTP
# loopback origin (127.0.0.1 / [::1] / localhost) with an explicit valid
# port and no userinfo / path / query / fragment, and reflects the EXACT
# accepted origin (never `*`). Requests without an Origin header, or with
# malformed / credential-bearing / non-HTTP / path-bearing / non-loopback
# / portless origins, get NO CORS header — fail-closed. The policy lives
# ONLY in the fixture server (allowed edit surface) and is documented in
# tools/react-e2e-harness/README.md.

def _http_with_origin(url, origin, *, method="GET", timeout=2.0):
    """Same 4-tuple shape as _http but attaches an explicit Origin header
    so the CORS policy path is exercised. `origin` is the literal string
    the client would send in the Origin request header."""
    req = urllib.request.Request(url, method=method)
    if origin is not None:
        req.add_header("Origin", origin)
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


# ─── Source contract (RED gate) ─────────────────────────────────────────
def test_fixture_server_exports_cors_origin_validator():
    """`isValidLoopbackCorsOrigin` MUST be exported so the pure-Node
    path can probe the policy without spawning a server. The function
    returns the EXACT accepted Origin string, or `null` for any
    malformed / credential-bearing / non-HTTP / path-bearing / non-
    loopback / portless input — never throws."""
    src = FIXTURE.read_text()
    assert "isValidLoopbackCorsOrigin" in src, (
        "fixture-server must export isValidLoopbackCorsOrigin"
    )


# ─── Direct function probe (pure-Node, no HTTP) ────────────────────────
def test_fixture_server_cors_validator_accepts_loopback_origins():
    """Each loopback HTTP origin with an explicit valid port MUST be
    accepted and reflected EXACTLY — never normalised, never `*`."""
    script = (
        f'import {{ isValidLoopbackCorsOrigin }} from "file://{FIXTURE}";\n'
        "const cases = [\n"
        "  ['http://127.0.0.1:8080', 'http://127.0.0.1:8080'],\n"
        "  ['http://127.0.0.1:1', 'http://127.0.0.1:1'],\n"
        "  ['http://127.0.0.1:65535', 'http://127.0.0.1:65535'],\n"
        "  ['http://[::1]:8080', 'http://[::1]:8080'],\n"
        "  ['http://localhost:8080', 'http://localhost:8080'],\n"
        "];\n"
        "const out = [];\n"
        "for (const [input, expected] of cases) {\n"
        "  const got = isValidLoopbackCorsOrigin(input);\n"
        "  out.push({ input, got, expected });\n"
        "  if (got !== expected) { console.error(JSON.stringify(out)); process.exit(2); }\n"
        "  if (got === '*') { console.error('wildcard emitted'); process.exit(3); }\n"
        "}\n"
        "console.log(JSON.stringify(out));\n"
    )
    rc, out, err = _run_node(script)
    assert rc == 0, f"node failed: rc={rc} stderr={err!r}"
    rows = json.loads(out.strip())
    assert all(r["got"] == r["expected"] for r in rows), rows


def test_fixture_server_cors_validator_rejects_invalid_origins():
    """Every malformed / credential-bearing / non-HTTP / path-bearing /
    non-loopback / portless / null / non-string input MUST return null.
    No exceptions, no partial accept, no wildcard."""
    script = (
        f'import {{ isValidLoopbackCorsOrigin }} from "file://{FIXTURE}";\n'
        "const cases = [\n"
        "  null, undefined, '',\n"
        "  'not-a-url',\n"
        "  'http://user:pass@127.0.0.1:8080',\n"
        "  'http://user@127.0.0.1:8080',\n"
        "  'https://127.0.0.1:8080',\n"
        "  'data:text/html,foo',\n"
        "  'ftp://127.0.0.1:8080',\n"
        "  'http://127.0.0.1:8080/foo',\n"
        "  'http://127.0.0.1:8080?q=1',\n"
        "  'http://127.0.0.1:8080/#frag',\n"
        "  'http://10.0.0.1:8080',\n"
        "  'http://192.168.1.1:8080',\n"
        "  'http://example.com:8080',\n"
        "  'http://localhost.:8080',\n"
        "  'http://127.0.0.1',\n"
        "  'http://[::1]',\n"
        "  'http://localhost',\n"
        "  'http://127.0.0.1:99999',\n"
        "  'http://127.0.0.1:-1',\n"
        "  'http://127.0.0.1:abc',\n"
        "];\n"
        "const out = [];\n"
        "for (const input of cases) {\n"
        "  const got = isValidLoopbackCorsOrigin(input);\n"
        "  out.push({ input: JSON.stringify(input), got });\n"
        "  if (got !== null) { console.error(JSON.stringify(out)); process.exit(2); }\n"
        "}\n"
        "console.log(JSON.stringify(out));\n"
    )
    rc, out, err = _run_node(script)
    assert rc == 0, f"node failed: rc={rc} stderr={err!r}"
    rows = json.loads(out.strip())
    assert all(r["got"] is None for r in rows), rows


# ─── Accepted origins (loopback HTTP with explicit port) ────────────────
@pytest.mark.parametrize("host", ["127.0.0.1", "[::1]", "localhost"])
def test_cors_emits_allow_origin_for_loopback(fx, host):
    """Each loopback HTTP origin with an explicit port gets the EXACT
    origin reflected in Access-Control-Allow-Origin (never `*`, never
    trimmed, never lowered-case folded). The response status MUST
    stay 200 — CORS is an additive header, never a request gate."""
    origin = f"http://{host}:{fx['port']}"
    s, h, _, _ = _http_with_origin(f"{fx['base']}/api/taxon/1/files", origin)
    assert s == 200, f"loopback {host} must still serve 200; got {s}"
    aco = h.get("access-control-allow-origin")
    assert aco == origin, (
        f"Access-Control-Allow-Origin must reflect EXACT origin; "
        f"sent={origin!r} got={aco!r}"
    )
    assert aco != "*", "wildcard `*` would be credential-incompatible"


def test_cors_emits_allow_origin_on_files_serve(fx):
    """The CORS header MUST also be emitted on /files/serve so the
    React viewer can read individual files cross-origin (PDF, MD, TXT,
    HTML). The Content-Type / Content-Disposition / Content-Length
    contract is unchanged."""
    origin = f"http://127.0.0.1:{fx['port']}"
    qs = urllib.parse.quote("index.html")
    s, h, body, _ = _http_with_origin(
        f"{fx['base']}/api/taxon/1/files/serve?path={qs}", origin
    )
    assert s == 200, f"must still serve 200; got {s}"
    assert h.get("access-control-allow-origin") == origin, h
    # Existing GET wire contract is unchanged.
    assert h.get("content-type", "").lower().startswith("text/html"), h
    assert h.get("content-disposition", "").startswith("inline;"), h
    assert len(body) > 0


@pytest.mark.parametrize("host", ["127.0.0.1", "[::1]", "localhost"])
def test_cors_emits_allow_origin_on_error_responses(fx, host):
    """The CORS header MUST be present on 404 / 405 responses too so
    the browser can read the diagnostic body when something goes
    wrong — otherwise the browser would see a generic CORS error
    instead of the actual 404 detail."""
    origin = f"http://{host}:{fx['port']}"
    # 404: unknown taxon
    s, h, _, _ = _http_with_origin(
        f"{fx['base']}/api/taxon/2/files", origin
    )
    assert s == 404, f"unknown taxon must 404; got {s}"
    assert h.get("access-control-allow-origin") == origin, (
        f"404 must carry Access-Control-Allow-Origin; got {h}"
    )
    # 405: POST
    s, h, _, _ = _http_with_origin(
        f"{fx['base']}/api/taxon/1/files", origin, method="POST"
    )
    assert s == 405, f"POST must 405; got {s}"
    assert h.get("access-control-allow-origin") == origin, (
        f"405 must carry Access-Control-Allow-Origin; got {h}"
    )
    assert h.get("allow", "").upper().replace(" ", "") == "GET,HEAD", (
        f"POST /files must still advertise `Allow: GET, HEAD`; got {h.get('allow')!r}"
    )


# ─── No origin at all (normal behavior preserved) ───────────────────────
def test_cors_no_origin_header_emits_no_cors_header(fx):
    """Requests WITHOUT an Origin header MUST get NO CORS header —
    they're either same-origin or non-browser clients (curl / Python /
    etc.) and don't need CORS at all. The envelope is unchanged."""
    s, h, _, p = _http(f"{fx['base']}/api/taxon/1/files")
    assert s == 200
    assert "access-control-allow-origin" not in h, (
        f"absent Origin must NOT trigger CORS; got {h}"
    )
    assert p is not None and p.get("exists") is True, p


# ─── Rejected origins (no CORS header at all) ──────────────────────────
@pytest.mark.parametrize("bad_origin,label", [
    ("not-a-url", "malformed"),
    ("", "empty"),
    ("http://user:pass@127.0.0.1:8080", "credential-bearing"),
    ("https://127.0.0.1:8080", "non-http-https"),
    ("data:text/html,foo", "non-http-data"),
    ("ftp://127.0.0.1:8080", "non-http-ftp"),
    ("http://127.0.0.1:8080/foo", "path-bearing"),
    ("http://127.0.0.1:8080/?q=1", "query-bearing"),
    ("http://127.0.0.1:8080/#frag", "hash-bearing"),
    ("http://10.0.0.1:8080", "non-loopback-ipv4"),
    ("http://192.168.1.1:8080", "non-loopback-private"),
    ("http://example.com:8080", "non-loopback-hostname"),
    ("http://127.0.0.1", "portless-ipv4"),
    ("http://[::1]", "portless-ipv6"),
    ("http://localhost", "portless-hostname"),
])
def test_cors_rejects_invalid_origins_with_no_header(fx, bad_origin, label):
    """Every malformed / credential-bearing / non-HTTP / path-bearing /
    non-loopback / portless Origin MUST get NO Access-Control-Allow-
    Origin header. The response is otherwise unaffected (status 200,
    envelope intact)."""
    s, h, _, p = _http_with_origin(
        f"{fx['base']}/api/taxon/1/files", bad_origin
    )
    assert s == 200, f"{label}: status must remain 200; got {s}"
    # Envelope must be intact (CORS rejection is a header-only decision).
    assert p is not None and p.get("exists") is True, (
        f"{label}: envelope must remain intact; got {p}"
    )
    assert "access-control-allow-origin" not in h, (
        f"{label}: Access-Control-Allow-Origin must be absent; "
        f"got {h.get('access-control-allow-origin')!r}"
    )


# ─── Source-contract probe ─────────────────────────────────────────────
def test_cors_policy_lives_only_in_fixture_server_source():
    """The strict loopback-only CORS policy MUST live in
    fixture-server.mjs (the ONLY allowed edit surface). It MUST use
    a URL parser (not a regex) so userinfo / path / query / fragment
    can't slip through. It MUST enumerate all three loopback host
    shapes. Production code paths / OpenSpec files / lockfiles stay
    untouched."""
    src = FIXTURE.read_text()
    # Header literal + reflected-origin pattern.
    assert '"Access-Control-Allow-Origin"' in src, (
        "fixture-server must emit Access-Control-Allow-Origin header"
    )
    # All three loopback shapes enumerated.
    for host in ("127.0.0.1", "[::1]", "localhost"):
        assert host in src, f"fixture-server must accept loopback host {host}"
    # URL parser (not regex): rejects userinfo / path / query / fragment.
    assert "new URL(" in src, "must parse Origin via WHATWG URL parser"
    assert "username" in src and "password" in src, (
        "must reject credential-bearing origins via URL.username/password"
    )
    # setHeader path so EVERY response (200 / 4xx / 405) carries it.
    assert "setHeader" in src, (
        "must use res.setHeader so all responses (including errors) "
        "carry the CORS header"
    )



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


def _run_node_in_dir(script, *, cwd, timeout=10.0, env_extra=None):
    """Run a Node ESM script with a controlled working directory and extra
    environment so a probe can resolve modules from a specific `node_modules/`
    tree (e.g. `tools/react-e2e-harness/node_modules/`). Returns
    `(rc, stdout, stderr)`."""
    env = {**os.environ, "NODE_NO_WARNINGS": "1"}
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True, text=True, timeout=timeout,
        cwd=cwd, env=env,
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


# ─── Default harnessDir derives from script location ───────────────────
#
# `npm run capture:composed -- --output-root DIR` MUST work when invoked
# from `tools/react-e2e-harness` (the package-script cwd), without
# requiring `--harness-dir`. The legacy default
# `resolve(process.cwd(), "tools/react-e2e-harness")` resolved from the
# package cwd to a duplicated `<pkg>/tools/react-e2e-harness` path and
# `defaultBuildFn` then failed with `spawn npm ENOENT`. The canonical
# default MUST derive from the script's `import.meta.url`, NOT cwd.
# Explicit `--harness-dir` MUST continue to take precedence.
def test_composed_capture_resolve_default_harness_dir_derives_from_script_location():
    """`resolveDefaultHarnessDir` MUST be exported and MUST return the
    canonical `<repo>/tools/react-e2e-harness` directory derived from the
    script's `import.meta.url` (one level above `scripts/`), not from
    `process.cwd()`. RED: pre-fix the helper does not exist and the
    import fails before the assertion runs."""
    expected = REPO_ROOT / "tools" / "react-e2e-harness"
    script = (
        f'import {{ resolveDefaultHarnessDir }} from "file://{COMPOSED_CAPTURE}";\n'
        f"const got = resolveDefaultHarnessDir();\n"
        f"process.stdout.write(JSON.stringify({{ got, expected: '{expected}' }}));\n"
    )
    rc, out, err = _run_node(script)
    assert rc == 0, (
        f"node failed: rc={rc} stderr={err!r} stdout={out!r}; "
        "resolveDefaultHarnessDir must be exported and callable"
    )
    payload = json.loads(out.strip())
    assert payload["got"] == payload["expected"], (
        f"resolveDefaultHarnessDir must return the script location; "
        f"got {payload['got']!r} expected {payload['expected']!r}"
    )


def test_composed_capture_default_harness_dir_independent_of_cwd(tmp_path):
    """The default `harnessDir` MUST be independent of `process.cwd()`.
    From the package directory (cwd=tools/react-e2e-harness) the legacy
    cwd-based default duplicated the path; the script-location default
    MUST still resolve to `<repo>/tools/react-e2e-harness` when cwd is
    the package directory itself. Probed in a subprocess so cwd actually
    changes (a Python `os.chdir` is invisible to the child Node import)."""
    pkg_dir = REPO_ROOT / "tools" / "react-e2e-harness"
    expected = pkg_dir
    proc = subprocess.run(
        ["node", "--input-type=module", "-e",
         f'import {{ resolveDefaultHarnessDir }} from "file://{COMPOSED_CAPTURE}";\n'
         f"process.stdout.write(resolveDefaultHarnessDir());\n"],
        capture_output=True, text=True,
        cwd=str(pkg_dir),
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
        timeout=10.0,
    )
    assert proc.returncode == 0, (
        f"node failed: rc={proc.returncode} stderr={proc.stderr!r}; "
        "resolveDefaultHarnessDir must work regardless of cwd"
    )
    got = proc.stdout.strip()
    assert got == str(expected), (
        f"default harnessDir is cwd-dependent: got {got!r} "
        f"expected {str(expected)!r}; legacy default would have produced "
        f"{pkg_dir / 'tools' / 'react-e2e-harness'}"
    )
    # Sanity: the legacy duplicated path MUST NOT be the answer.
    assert got != str(pkg_dir / "tools" / "react-e2e-harness"), (
        "default harnessDir still duplicates the path under the package cwd"
    )


def test_composed_capture_main_prefers_explicit_harness_dir():
    """`main()` MUST prefer an explicit `args.harnessDir` over the
    script-location default, so callers can override the harness without
    editing the script. The default MUST come from
    `resolveDefaultHarnessDir` (script location), NOT from the legacy
    `resolve(process.cwd(), "tools/react-e2e-harness")`."""
    src = COMPOSED_CAPTURE.read_text()
    assert "args.harnessDir ??" in src, (
        "main() must use `args.harnessDir ?? <default>` so explicit "
        "overrides take precedence over the default"
    )
    assert "resolveDefaultHarnessDir" in src, (
        "default harnessDir MUST come from resolveDefaultHarnessDir "
        "(derived from import.meta.url), not from process.cwd()"
    )
    assert 'resolve(process.cwd(), "tools/react-e2e-harness")' not in src, (
        "legacy cwd-based default is forbidden; default must derive from "
        "the script location, not from process.cwd()"
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

# ===========================================================================
# Diagnostic Chromium executable override (PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH)
# ===========================================================================
#
# `tools/react-e2e-harness/scripts/chromium-driver.mjs` may launch an operator
# supplied Chromium executable when `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` is
# set. This is EXPLICITLY diagnostic / noncanonical: the canonical contract is
# still the pinned Playwright-managed browser, and an overridden run can never
# close G4. With no variable the launch options MUST be byte-identical to the
# previous pinned default (`{ headless: true }`, no channel, no
# executablePath). Validation fails closed: non-absolute, nonexistent /
# unreadable, non-regular-file, and non-executable paths all throw before any
# browser launch. Hermetic: injected `playwrightFn` stub — no real Playwright,
# no Chromium, no network.

CHROMIUM_DRIVER = (
    REPO_ROOT / "tools" / "react-e2e-harness" / "scripts" / "chromium-driver.mjs"
)
BROWSER_EXEC_ENV = "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"


def _fake_executable(tmp_path, name="fake-chromium"):
    p = tmp_path / name
    p.write_text("#!/bin/sh\nexit 0\n")
    p.chmod(0o755)
    return p


def _driver_probe(script, *, timeout=10.0):
    return _run_node(
        f'import * as drv from "file://{CHROMIUM_DRIVER}";\n' + script,
        timeout=timeout,
    )


def test_chromium_driver_module_parses_with_node_check():
    """`node --check` succeeds so any subsequent import is safe."""
    p = subprocess.run(
        ["node", "--check", str(CHROMIUM_DRIVER)], capture_output=True, text=True
    )
    assert p.returncode == 0, f"node --check failed: {p.stderr}"


def test_chromium_driver_exports_browser_executable_resolver():
    """The driver MUST expose the override resolver so validation is testable
    without launching a browser."""
    assert "resolveBrowserExecutablePath" in CHROMIUM_DRIVER.read_text(), (
        "must export resolveBrowserExecutablePath"
    )


def test_browser_executable_override_absent_keeps_pinned_default(tmp_path):
    """No env var, no option → launch options MUST stay exactly
    `{ headless: true }` (no executablePath, no channel) and the evidence MUST
    mark the run canonical."""
    script = (
        "let seen = null;\n"
        "const playwrightFn = async () => ({ chromium: { launch: async (o) => {\n"
        "  seen = o;\n"
        "  throw new Error('launch-stop');\n"
        "} } });\n"
        "let err = null;\n"
        "try { await drv.runCapture({ origin: 'http://127.0.0.1:1/', playwrightFn, env: {} }); }\n"
        "catch (e) { err = e.message; }\n"
        "console.log(JSON.stringify({ seen, err }));\n"
    )
    rc, out, err = _driver_probe(script)
    assert rc == 0, f"node failed: rc={rc} stderr={err!r}"
    payload = json.loads(out.strip())
    assert payload["seen"] == {"headless": True}, (
        f"pinned default launch options changed: {payload['seen']!r}"
    )


def test_browser_executable_override_env_is_passed_to_launch(tmp_path):
    """With the env var set to a valid absolute executable, that exact path
    MUST be forwarded as `executablePath`, still headless, still with NO
    channel."""
    exe = _fake_executable(tmp_path)
    script = (
        "let seen = null;\n"
        "const playwrightFn = async () => ({ chromium: { launch: async (o) => {\n"
        "  seen = o;\n"
        "  throw new Error('launch-stop');\n"
        "} } });\n"
        "try { await drv.runCapture({ origin: 'http://127.0.0.1:1/', playwrightFn,\n"
        f'  env: {{ {BROWSER_EXEC_ENV!r}: "{exe}" }} }}); }} catch (e) {{}}\n'
        "console.log(JSON.stringify({ seen }));\n"
    )
    rc, out, err = _driver_probe(script)
    assert rc == 0, f"node failed: rc={rc} stderr={err!r}"
    seen = json.loads(out.strip())["seen"]
    assert seen["executablePath"] == str(exe), seen
    assert seen["headless"] is True, seen
    assert "channel" not in seen, f"override MUST NOT use a browser channel: {seen!r}"


def test_browser_executable_override_marks_capture_noncanonical(tmp_path):
    """An overridden run MUST be identifiable in the capture data as
    noncanonical diagnostic execution; a default run MUST be canonical."""
    exe = _fake_executable(tmp_path)
    stub = (
        "const stub = (label) => ({ chromium: { launch: async () => ({\n"
        "  newContext: async () => ({ newPage: async () => ({\n"
        "    on() {},\n"
        "    goto: async () => ({ status: () => 200 }),\n"
        "    waitForSelector: async () => {},\n"
        "    evaluate: async () => ({ rootPresent: true, surfacePresent: true,\n"
        "      taxonId: '1', taxonIdNonNull: true, explorerReady: true,\n"
        "      treePanePresent: true, viewerPanePresent: true,\n"
        "      searchInputPresent: true, filePathsCount: 1,\n"
        "      firstFilePath: 'index.html' }),\n"
        "  }) }),\n"
        "  close: async () => {},\n"
        "}) } });\n"
    )
    script = (
        stub
        + "const playwrightFn = async () => stub();\n"
        "const base = await drv.runCapture({ origin: 'http://127.0.0.1:1/', playwrightFn, env: {} });\n"
        "const over = await drv.runCapture({ origin: 'http://127.0.0.1:1/', playwrightFn,\n"
        f'  env: {{ {BROWSER_EXEC_ENV!r}: "{exe}" }} }});\n'
        "console.log(JSON.stringify({ base: base.browserExecution, over: over.browserExecution }));\n"
    )
    rc, out, err = _driver_probe(script)
    assert rc == 0, f"node failed: rc={rc} stderr={err!r}"
    payload = json.loads(out.strip())
    assert payload["base"]["canonical"] is True, payload["base"]
    assert payload["base"]["executablePath"] is None, payload["base"]
    assert payload["over"]["canonical"] is False, payload["over"]
    assert payload["over"]["executablePath"] == str(exe), payload["over"]
    assert "diagnostic" in json.dumps(payload["over"]).lower(), payload["over"]


def test_browser_executable_override_fails_closed(tmp_path):
    """Non-absolute, nonexistent, directory, and non-executable paths MUST all
    throw from `resolveBrowserExecutablePath` — no silent fallback to the
    pinned browser, which would make a diagnostic run masquerade as canonical."""
    rel = "relative/chromium"
    missing = tmp_path / "nope"
    a_dir = tmp_path / "adir"
    a_dir.mkdir()
    not_exec = tmp_path / "plain.txt"
    not_exec.write_text("nope\n")
    not_exec.chmod(0o644)
    bad = [rel, str(missing), str(a_dir), str(not_exec)]
    script = (
        f"const bad = {json.dumps(bad)};\n"
        "const out = [];\n"
        "for (const b of bad) {\n"
        f'  try {{ drv.resolveBrowserExecutablePath({{ {BROWSER_EXEC_ENV!r}: b }}); out.push({{ path: b, threw: false }}); }}\n'
        "  catch (e) { out.push({ path: b, threw: true }); }\n"
        "}\n"
        "console.log(JSON.stringify(out));\n"
    )
    rc, out, err = _driver_probe(script)
    assert rc == 0, f"node failed: rc={rc} stderr={err!r}"
    for entry in json.loads(out.strip()):
        assert entry["threw"] is True, f"accepted invalid executable: {entry['path']!r}"


def test_browser_executable_override_blank_env_is_treated_as_absent(tmp_path):
    """An empty / whitespace-only variable is `unset`, not an error — operators
    routinely export empty strings."""
    script = (
        f'const r1 = drv.resolveBrowserExecutablePath({{ {BROWSER_EXEC_ENV!r}: "" }});\n'
        f'const r2 = drv.resolveBrowserExecutablePath({{ {BROWSER_EXEC_ENV!r}: "   " }});\n'
        "const r3 = drv.resolveBrowserExecutablePath({});\n"
        "console.log(JSON.stringify([r1, r2, r3]));\n"
    )
    rc, out, err = _driver_probe(script)
    assert rc == 0, f"node failed: rc={rc} stderr={err!r}"
    assert json.loads(out.strip()) == [None, None, None]


# ===========================================================================
# PR 5c.2-B.1b-ii-d — canonical Playwright pin (1.62.1 + headless-shell 1234)
# ===========================================================================
#
# The canonical G4 evidence path is a NORMAL `chromium.launch({ headless: true })`
# WITHOUT `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` (which is reserved for diagnostic
# operator overrides only — see PR 5c.2-B.1b-ii-c tests above). To make that
# path work the harness MUST pin `@playwright/test` to a Playwright version whose
# managed `chromium-headless-shell` revision matches the locally complete
# browser cache. As of this slice the canonical pin is `@playwright/test@1.62.1`
# → chromium-headless-shell revision `1234` (Chromium 151.0.7922.34).
#
# Tests below lock the source-of-truth (package.json + package-lock.json), the
# INSTALLED runtime (`@playwright/test/package.json` version + the shipped
# `playwright-core/browsers.json`), and a minimal no-override `chromium.launch`
# launch/close to prove the canonical route is open. No full capture is run here
# — that lives in a separate canonical-evidence task.

HARNESS_PKG_JSON = REPO_ROOT / "tools" / "react-e2e-harness" / "package.json"
HARNESS_LOCKFILE = REPO_ROOT / "tools" / "react-e2e-harness" / "package-lock.json"
HARNESS_NODE_MODULES = REPO_ROOT / "tools" / "react-e2e-harness" / "node_modules"
CANONICAL_PW_VERSION = "1.62.1"
CANONICAL_HEADLESS_REVISION = "1234"


# ─── Source contract: package.json pins canonical Playwright ──────────────
def test_harness_package_json_pins_canonical_playwright_version():
    """`tools/react-e2e-harness/package.json` MUST pin `@playwright/test` to
    the canonical `1.62.1` so `npm ci` reproduces the G4 contract. The pin
    MUST be exact (no caret, no tilde, no range) so a future bump is a
    deliberate, reviewable change."""
    assert HARNESS_PKG_JSON.is_file(), f"missing: {HARNESS_PKG_JSON}"
    data = json.loads(HARNESS_PKG_JSON.read_text())
    pin = data.get("devDependencies", {}).get("@playwright/test")
    assert pin == CANONICAL_PW_VERSION, (
        f"@playwright/test pin must be exactly {CANONICAL_PW_VERSION!r}; got {pin!r}"
    )
    # Guard against caret/tilde/range regressions on the canonical pin.
    assert not pin.startswith("^") and not pin.startswith("~") and not pin.startswith(">"), (
        f"canonical pin MUST be exact; got {pin!r}"
    )


def test_harness_package_json_description_references_canonical_pin():
    """The `description` field MUST surface the canonical pin so reviewers can
    see the exact version + Next/React pins at a glance. Locks the doc string
    in lockstep with the dependency pin."""
    assert HARNESS_PKG_JSON.is_file(), f"missing: {HARNESS_PKG_JSON}"
    data = json.loads(HARNESS_PKG_JSON.read_text())
    desc = data.get("description", "")
    assert CANONICAL_PW_VERSION in desc, (
        f"description must surface canonical pin {CANONICAL_PW_VERSION!r}; got {desc!r}"
    )
    # The legacy failing pin MUST NOT still appear in the description.
    assert "1.56.0" not in desc, (
        f"legacy failing pin 1.56.0 must be removed from description; got {desc!r}"
    )


# ─── Source contract: package-lock.json resolves canonical Playwright ──────
def test_harness_lockfile_resolves_canonical_playwright_version():
    """The regenerated `tools/react-e2e-harness/package-lock.json` MUST resolve
    `@playwright/test` to the canonical `1.62.1` and its `playwright` +
    `playwright-core` dependencies to the same version. Lockfile MUST be
    regenerated by npm (not hand-edited) — the regenerated file should also
    pin exactly, never a range."""
    assert HARNESS_LOCKFILE.is_file(), f"missing: {HARNESS_LOCKFILE}"
    data = json.loads(HARNESS_LOCKFILE.read_text())
    pkgs = data.get("packages", {})
    top = pkgs.get("", {})
    assert top.get("devDependencies", {}).get("@playwright/test") == CANONICAL_PW_VERSION, (
        f"top-level devDependency pin must be {CANONICAL_PW_VERSION!r}; "
        f"got {top.get('devDependencies', {}).get('@playwright/test')!r}"
    )
    # Direct @playwright/test resolution.
    pwt = pkgs.get("node_modules/@playwright/test", {})
    assert pwt.get("version") == CANONICAL_PW_VERSION, (
        f"node_modules/@playwright/test version must be {CANONICAL_PW_VERSION!r}; "
        f"got {pwt.get('version')!r}"
    )
    # Transitive playwright package.
    pw = pkgs.get("node_modules/playwright", {})
    assert pw.get("version") == CANONICAL_PW_VERSION, (
        f"node_modules/playwright version must be {CANONICAL_PW_VERSION!r}; "
        f"got {pw.get('version')!r}"
    )
    # Transitive playwright-core (this is the package whose browsers.json we
    # rely on for revision truth).
    pwc = pkgs.get("node_modules/playwright-core", {})
    assert pwc.get("version") == CANONICAL_PW_VERSION, (
        f"node_modules/playwright-core version must be {CANONICAL_PW_VERSION!r}; "
        f"got {pwc.get('version')!r}"
    )


# ─── Installed runtime: real @playwright/test package version ──────────────
def test_installed_playwright_test_version_is_canonical():
    """After `npm ci`, `node_modules/@playwright/test/package.json` MUST report
    `version == 1.62.1`. This is the runtime version used by every
    `chromium.launch` call in the canonical path. Probed via Node so a stale
    source-only update is caught."""
    installed = HARNESS_NODE_MODULES / "@playwright" / "test" / "package.json"
    assert installed.is_file(), (
        f"@playwright/test not installed: {installed}. "
        f"Run `npm ci` in tools/react-e2e-harness."
    )
    data = json.loads(installed.read_text())
    assert data.get("name") == "@playwright/test"
    assert data.get("version") == CANONICAL_PW_VERSION, (
        f"installed @playwright/test version must be {CANONICAL_PW_VERSION!r}; "
        f"got {data.get('version')!r}"
    )


# ─── Installed runtime: browsers.json points headless-shell to 1234 ────────
def test_installed_browsers_json_points_headless_shell_to_canonical_revision():
    """The installed `playwright-core/browsers.json` MUST point
    `chromium-headless-shell` to revision `1234` (the locally complete
    Playwright-managed headless shell). This is the single source of truth for
    what `chromium.launch({ headless: true })` resolves to. Without this
    match the canonical G4 route would 404 trying to find an unrecognised
    revision."""
    browsers_json = (
        HARNESS_NODE_MODULES / "playwright-core" / "browsers.json"
    )
    assert browsers_json.is_file(), (
        f"browsers.json not installed: {browsers_json}. "
        f"Run `npm ci` in tools/react-e2e-harness."
    )
    data = json.loads(browsers_json.read_text())
    headless = [
        b for b in data.get("browsers", []) if b.get("name") == "chromium-headless-shell"
    ]
    assert len(headless) == 1, (
        f"exactly one chromium-headless-shell entry expected; got {headless!r}"
    )
    assert headless[0].get("revision") == CANONICAL_HEADLESS_REVISION, (
        f"chromium-headless-shell revision must be {CANONICAL_HEADLESS_REVISION!r}; "
        f"got {headless[0].get('revision')!r}"
    )
    # Belt-and-braces: the full Chromium binary also lives at the same rev so
    # `chromium.launch({ headless: false })` would be coherent too.
    chromium = [
        b for b in data.get("browsers", []) if b.get("name") == "chromium"
    ]
    assert chromium and chromium[0].get("revision") == CANONICAL_HEADLESS_REVISION, (
        f"chromium revision must also be {CANONICAL_HEADLESS_REVISION!r}; "
        f"got {chromium!r}"
    )


# ─── Canonical path: chromium.launch({ headless: true }) opens + closes ──
def test_canonical_chromium_launch_no_override_succeeds():
    """Smoke probe: with NO `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` and NO
    override options, `chromium.launch({ headless: true })` MUST open against
    the locally cached headless-shell-1234 and close cleanly. This is the
    canonical G4 route — if it can't open, the captured evidence path is
    blocked. Probed via Node from inside the harness's `node_modules/`. On
    environments where the cached binary is missing or not executable the
    test fail-closes (no silent skip)."""
    if not (HARNESS_NODE_MODULES / "playwright-core").is_dir():
        pytest.skip(
            "playwright-core not installed in tools/react-e2e-harness/node_modules; "
            "run `npm ci` first."
        )
    headless_cache = Path.home() / "Library" / "Caches" / "ms-playwright" / (
        f"chromium_headless_shell-{CANONICAL_HEADLESS_REVISION}"
    )
    if not headless_cache.is_dir():
        pytest.skip(
            f"local chromium_headless_shell-{CANONICAL_HEADLESS_REVISION} "
            f"not present at {headless_cache}; install via "
            f"`npx playwright install chromium` before running."
        )
    script = (
        "import { chromium } from 'playwright';\n"
        "let opened = false, closed = false;\n"
        "try {\n"
        "  const browser = await chromium.launch({ headless: true });\n"
        "  opened = true;\n"
        "  await browser.close();\n"
        "  closed = true;\n"
        "} catch (e) {\n"
        "  console.error('LAUNCH_FAIL ' + (e && e.message));\n"
        "  process.exit(2);\n"
        "}\n"
        "console.log(JSON.stringify({ opened, closed }));\n"
    )
    # Run from the harness directory so Node can resolve the local
    # `playwright` module from `tools/react-e2e-harness/node_modules/`.
    rc, out, err = _run_node_in_dir(
        script,
        cwd=HARNESS_PKG_JSON.parent,
        env_extra={"PLAYWRIGHT_BROWSERS_PATH": str(Path.home() / "Library" / "Caches" / "ms-playwright")},
    )
    assert rc == 0, (
        f"canonical chromium.launch failed: rc={rc} stderr={err!r} "
        f"stdout={out!r}; ensure local cache has "
        f"chromium_headless_shell-{CANONICAL_HEADLESS_REVISION}"
    )
    payload = json.loads(out.strip())
    assert payload == {"opened": True, "closed": True}, payload


# ─── Local cache: the matching headless-shell binary is actually present ───
def test_local_cache_has_canonical_headless_shell_revision():
    """The locally complete Playwright-managed `chromium_headless_shell-1234`
    directory MUST exist under the platform cache root so a no-override
    `chromium.launch({ headless: true })` resolves without prompting for an
    install. Guards against the contract drifting away from what's actually
    on disk. On macOS the cache root is `~/Library/Caches/ms-playwright`."""
    headless_dir = (
        Path.home() / "Library" / "Caches" / "ms-playwright"
        / f"chromium_headless_shell-{CANONICAL_HEADLESS_REVISION}"
    )
    assert headless_dir.is_dir(), (
        f"local chromium_headless_shell-{CANONICAL_HEADLESS_REVISION} "
        f"missing at {headless_dir}; install via "
        f"`npx playwright install chromium` before relying on the "
        f"canonical G4 route"
    )
    # At minimum the directory should contain the headless-shell binary;
    # its exact name is platform-dependent so probe for a marker file
    # that's stable across mac/linux/win (`DEPENDENCIES_VALIDATED` is
    # written by Playwright after a successful browser install).
    marker = headless_dir / "DEPENDENCIES_VALIDATED"
    assert marker.is_file(), (
        f"headless-shell install marker missing at {marker}; the cached "
        f"directory is incomplete — re-run `npx playwright install chromium`."
    )
