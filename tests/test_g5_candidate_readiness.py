"""G5 provisional candidate-readiness child — see design.md §3.3.5 (provisional scope).
Hermetic loopback-only Node static server `tools/g2-candidate/scripts/serve-output.mjs`
plus a Python-invoked readiness verifier recording + validating: candidate
output root, BUILD-INVENTORY.json SHA-256, route `/` HTTP 200 HTML, loopback URL
+ timestamp, successful declared + discovered JS/CSS fetches. Diagnostic /
provisional only — no claim of final product equivalence or cutover.
"""
from __future__ import annotations
import hashlib, http.client, json, os, re, shutil, socket, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVE_OUTPUT = REPO_ROOT / "tools" / "g2-candidate" / "scripts" / "serve-output.mjs"
MIME_JS_RE = re.compile(r"^application/javascript\b|^text/javascript\b")
MIME_CSS_RE = re.compile(r"^text/css\b")

# --- subprocess / port helpers --------------------------------------------------

def _free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def _node():
    n = shutil.which("node")
    if not n: pytest.skip("node not on PATH")
    return n

def _spawn(root: Path, *args: str) -> subprocess.Popen:
    return subprocess.Popen([_node(), str(SERVE_OUTPUT), str(root), *args],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env={**os.environ, "NODE_NO_WARNINGS": "1"})

def _wait(proc: subprocess.Popen, port: int, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            _, err = proc.communicate(timeout=1)
            raise RuntimeError(f"server exited rc={proc.returncode} stderr={err.decode(errors='replace')}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25): return
        except OSError: time.sleep(0.02)
    raise RuntimeError(f"server did not listen on 127.0.0.1:{port}")

def _get(host: str, port: int, path: str):
    """Issue GET; return (status, content_type, body)."""
    c = http.client.HTTPConnection(host, port, timeout=2)
    try:
        c.request("GET", path); r = c.getresponse(); body = r.read()
        return r.status, (r.getheader("Content-Type") or ""), body
    finally: c.close()

def _terminate(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try: proc.wait(timeout=3)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=3)

# --- fixtures ------------------------------------------------------------------

@pytest.fixture
def output_tree(tmp_path: Path) -> Path:
    root, chunks, nested = tmp_path / "out", tmp_path / "out" / "_next" / "static" / "chunks", tmp_path / "out" / "nested"
    chunks.mkdir(parents=True); nested.mkdir(parents=True)
    (root / "index.html").write_text(
        "<!doctype html><title>g5</title>"
        "<script src=\"/_next/static/chunks/app.js\"></script>"
        "<link rel=\"stylesheet\" href=\"/_next/static/chunks/app.css\">")
    (chunks / "app.js").write_text("console.log('candidate');\n")
    (chunks / "app.css").write_text("body { color: #111; }\n")
    (nested / "asset.js").write_text("// nested\n")
    (nested / "asset.css").write_text(".x{color:red}\n")
    return root

@pytest.fixture
def build_inventory(output_tree: Path) -> Path:
    chunks = output_tree / "_next" / "static" / "chunks"
    inv = {"schema": "candidate-build-inventory", "node_version": "v26.8.1",
           "candidate_root": str(output_tree), "exit_code": 0, "missing_classes": [],
           "assets": [{"class": f"application_route_chunks_{ext}",
                       "path": f"_next/static/chunks/app.{ext}",
                       "bytes": (chunks / f"app.{ext}").stat().st_size,
                       "sha256": hashlib.sha256((chunks / f"app.{ext}").read_bytes()).hexdigest()}
                      for ext in ("js", "css")]}
    inv["assets"].insert(0, {"class": "application_route_html", "path": "index.html",
                             "bytes": (output_tree / "index.html").stat().st_size})
    (output_tree / "BUILD-INVENTORY.json").write_text(json.dumps(inv, indent=2))
    return output_tree / "BUILD-INVENTORY.json"

@pytest.fixture
def served(build_inventory: Path):
    port = _free_port(); proc = _spawn(build_inventory.parent, "--port", str(port))
    try: _wait(proc, port); yield f"http://127.0.0.1:{port}", port
    finally: _terminate(proc)

# --- the Python-invoked readiness verifier -------------------------------------

def verify_candidate_readiness(out_root: Path, base_url: str,
                               started_at: datetime) -> tuple[dict, list[str]]:
    """Record + validate candidate-readiness. Empty `errors` == pass. The
    record is JSON-serializable for persistence as
    `<out_root>/CANDIDATE-READINESS.json`."""
    host, port = (urlsplit(base_url).hostname or "127.0.0.1",
                  urlsplit(base_url).port or 0)
    errors: list[str] = []
    started = started_at.astimezone(timezone.utc).isoformat()
    verified = datetime.now(timezone.utc).isoformat()
    rec = {"schema": "g5-candidate-readiness", "candidate_output_root": str(out_root),
           "loopback_url": base_url, "loopback_host": host, "loopback_port": port,
           "started_at": started, "verified_at": verified}
    if not out_root.is_dir():
        errors.append(f"output_root_missing: {out_root}"); rec["passed"] = False; return rec, errors
    inv_path = out_root / "BUILD-INVENTORY.json"
    inv_rec = inv_sha = None
    if not inv_path.is_file(): errors.append(f"build_inventory_missing: {inv_path}")
    else:
        raw = inv_path.read_bytes(); inv_sha = hashlib.sha256(raw).hexdigest()
        try: inv_rec = json.loads(raw)
        except json.JSONDecodeError as exc: errors.append(f"build_inventory_invalid_json: {exc}")
    rec["build_inventory"] = {"path": str(inv_path), "sha256": inv_sha,
                              "node_version": (inv_rec or {}).get("node_version"),
                              "missing_classes": (inv_rec or {}).get("missing_classes"),
                              "exit_code": (inv_rec or {}).get("exit_code")}
    def record(label, path, klass="", suffix=""):
        """Issue a GET, build a per-asset record entry, append validation errors."""
        status, ct, body = _get(host, port, "/" + path.lstrip("/"))
        ct = ct.split(";")[0].strip()
        entry = {"class": klass, "path": path, "suffix": suffix, "status": status,
                 "content_type": ct, "served_bytes": len(body),
                 "sha256": hashlib.sha256(body).hexdigest()}
        if status != 200: errors.append(f"{label}_status:{path}:{status}")
        elif klass.endswith("_js") and not MIME_JS_RE.match(ct): errors.append(f"{label}_mime_js:{path}")
        elif klass.endswith("_css") and not MIME_CSS_RE.match(ct): errors.append(f"{label}_mime_css:{path}")
        return entry
    root_status, root_ct, root_body = _get(host, port, "/")
    rec["root_route"] = {"path": "/", "status": root_status, "content_type": root_ct,
                         "body_sha256": hashlib.sha256(root_body).hexdigest(),
                         "served_bytes": len(root_body)}
    if root_status != 200: errors.append(f"root_route_status:{root_status}:not_200")
    elif not root_body.lstrip().lower().startswith(b"<!doctype html"):
        errors.append("root_route_body_not_html")
    rec["declared_assets"] = [record("declared", a["path"], a.get("class", "")) for a in
                              (inv_rec or {}).get("assets", []) or []
                              if a.get("path", "") and a.get("class", "").endswith(("_js", "_css"))]
    discovered: list[dict] = []; on_disk: dict[str, Path] = {}
    chunks_dir = out_root / "_next" / "static" / "chunks"
    if chunks_dir.is_dir():
        for sub in chunks_dir.rglob("*"):
            if not sub.is_file() or sub.stat().st_size == 0 or sub.suffix not in (".js", ".css"): continue
            rel = sub.relative_to(out_root).as_posix()
            on_disk[rel] = sub
            discovered.append(record("discovered", rel, suffix=sub.suffix))
    rec["discovered_assets"] = discovered
    rec["discovered_count"] = len(on_disk)
    rec["discovered_served_count"] = sum(1 for d in discovered if d["status"] == 200)
    served_paths = {d["path"] for d in discovered if d["status"] == 200}
    for rel in on_disk:
        if rel not in served_paths: errors.append(f"discovered_asset_unfetched:{rel}")
    rec["passed"] = not errors
    return rec, errors

# --- server contract tests -----------------------------------------------------

def test_serve_output_script_present():
    """Canonical location per the allowed edit surface."""
    assert SERVE_OUTPUT.is_file(), f"missing {SERVE_OUTPUT}"

@pytest.mark.parametrize("path", ["/", "/index.html", "/_next/static/chunks/app.js",
                                   "/_next/static/chunks/app.css",
                                   "/nested/asset.js", "/nested/asset.css"])
def test_serve_output_serves_expected_paths(output_tree: Path, path: str):
    """`/`, `/index.html`, and arbitrarily nested assets return 200 with exact
    bytes and the matching MIME type."""
    port = _free_port(); proc = _spawn(output_tree, "--port", str(port))
    try:
        _wait(proc, port)
        status, ct, body = _get("127.0.0.1", port, path)
        assert status == 200, f"{path}: status={status}"
        rel = path.lstrip("/") or "index.html"
        assert body == (output_tree / rel).read_bytes(), f"{path}: bytes differ"
        ct = ct.split(";")[0].strip()
        if path.endswith(".js"): assert MIME_JS_RE.match(ct)
        elif path.endswith(".css"): assert MIME_CSS_RE.match(ct)
        else: assert ct == "text/html"
    finally: _terminate(proc)

@pytest.mark.parametrize("path", ["/../etc/passwd", "/nested/../../etc/passwd", "/a/./../../b"])
def test_serve_output_traversal_rejected(output_tree: Path, path: str):
    """Any URL containing `..` MUST be rejected with HTTP 400 — rejected on
    the raw URL before Node/WHATWG normalization collapses the path."""
    port = _free_port(); proc = _spawn(output_tree, "--port", str(port))
    try:
        _wait(proc, port)
        status, _, _ = _get("127.0.0.1", port, path); assert status == 400
    finally: _terminate(proc)

def test_serve_output_unknown_route_returns_404(output_tree: Path):
    """Missing files inside the root return 404 (not 200, not 403)."""
    port = _free_port(); proc = _spawn(output_tree, "--port", str(port))
    try:
        _wait(proc, port)
        status, _, _ = _get("127.0.0.1", port, "/no-such.html"); assert status == 404
    finally: _terminate(proc)

@pytest.mark.parametrize("case", ["missing_root", "root_is_file", "no_fallback_to_web"])
def test_serve_output_fail_closed_at_startup(tmp_path: Path, case: str):
    """Server MUST exit non-zero when the explicit root is missing OR a regular
    file, AND MUST NOT silently fall back to a sibling `web/` directory —
    diagnostic-candidate isolation requires the absence of any web/ fallback."""
    if case == "missing_root": root = tmp_path / "nope"
    elif case == "root_is_file":
        root = tmp_path / "afile"; root.write_text("not a dir")
    else:  # no_fallback_to_web: sibling web/ exists, out/ does not
        (tmp_path / "web").mkdir(); (tmp_path / "web" / "index.html").write_text("web")
        root = tmp_path / "out"
    port = _free_port(); proc = _spawn(root, "--port", str(port))
    try:
        rc = proc.wait(timeout=3); assert rc != 0, f"{case}: rc={rc}"
    except subprocess.TimeoutExpired:
        proc.kill(); proc.wait()
        pytest.fail(f"{case}: server hung (would imply web/ fallback)")

def test_serve_output_refuses_non_loopback_hostname(tmp_path: Path):
    """Server MUST refuse non-loopback hostnames (defence-in-depth)."""
    (tmp_path / "out").mkdir()
    proc = _spawn(tmp_path / "out", "--hostname", "0.0.0.0")
    try: rc = proc.wait(timeout=3); assert rc != 0
    except subprocess.TimeoutExpired:
        proc.kill(); proc.wait(); pytest.fail("server hung after non-loopback hostname")

# --- readiness-verifier tests --------------------------------------------------

def test_verifier_pass_on_healthy_candidate(served, output_tree):
    """Verifier MUST pass end-to-end: output root + inventory sha256 + root 200
    HTML + loopback URL/timestamp + declared + discovered JS/CSS. The record
    MUST be JSON-serializable (forms the readiness-artifact contract)."""
    base_url, port = served
    rec, errors = verify_candidate_readiness(output_tree, base_url, datetime.now(timezone.utc))
    assert errors == [], errors
    assert rec["passed"] is True
    assert rec["candidate_output_root"] == str(output_tree)
    assert rec["loopback_url"] == base_url
    assert rec["loopback_host"] == "127.0.0.1" and rec["loopback_port"] == port
    assert rec["root_route"]["status"] == 200
    assert rec["build_inventory"]["sha256"]
    assert rec["discovered_count"] >= 2
    declared_paths = {d["path"] for d in rec["declared_assets"]}
    assert declared_paths == {"_next/static/chunks/app.js", "_next/static/chunks/app.css"}
    assert all(d["status"] == 200 for d in rec["declared_assets"])
    on_disk = {sub.relative_to(output_tree).as_posix()
               for sub in (output_tree / "_next" / "static" / "chunks").rglob("*")
               if sub.is_file() and sub.suffix in (".js", ".css") and sub.stat().st_size > 0}
    assert on_disk == {d["path"] for d in rec["discovered_assets"] if d["status"] == 200}
    assert datetime.fromisoformat(rec["verified_at"]).tzinfo is not None
    json.dumps(rec)

@pytest.mark.parametrize("scenario,expected_prefix", [
    ("build_inventory_missing", "build_inventory_missing"),
    ("root_route_404", "root_route_status"),
    ("output_root_missing", "output_root_missing")])
def test_verifier_fail_closed_on_contract_violation(
        scenario, expected_prefix, tmp_path: Path, served, output_tree):
    """Fail-closed contract: the verifier emits `passed=False` (and an error
    tagged with the expected prefix) on missing inventory JSON, root route
    404, and missing output root. Success path is above."""
    if scenario == "build_inventory_missing":
        (output_tree / "BUILD-INVENTORY.json").unlink()
        root, base_url = output_tree, served[0]
    elif scenario == "root_route_404":
        # Sub-directory `output_tree`'s fixture doesn't claim (it creates
        # `tmp_path/out` via the always-evaluated signature).
        root = tmp_path / "empty_root"; root.mkdir()  # no index.html
        port = _free_port(); proc = _spawn(root, "--port", str(port))
        try:
            _wait(proc, port); base_url = f"http://127.0.0.1:{port}"
            rec, errors = verify_candidate_readiness(root, base_url, datetime.now(timezone.utc))
            assert any(e.startswith(expected_prefix) for e in errors), errors
            assert rec["passed"] is False
            return
        finally: _terminate(proc)
    else:  # output_root_missing — no HTTP fetch needed
        root, base_url = tmp_path / "nope", "http://127.0.0.1:1"
    rec, errors = verify_candidate_readiness(root, base_url, datetime.now(timezone.utc))
    assert any(e.startswith(expected_prefix) for e in errors), errors
    assert rec["passed"] is False
