"""Strict-TDD contract tests for scripts/verify_consumers.py (G3 verifier).

Covers the G3 manifest contract: fail-closed unless every consumer is fully
selected; atomically emit CONSUMER-READINESS.json only when every selected
verifier check passes. Tests use synthetic selected tmp manifests only;
real pytest invocation is reserved for non-G3 work units.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "verify_consumers.py"
MANIFEST = REPO_ROOT / "openspec" / "changes" / "migrate-nextjs-tailwind4" / "cutover-manifest.json"


def _run(argv, *, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPT), *argv],
                          capture_output=True, text=True, check=False, cwd=cwd)


def _readiness(out: Path) -> dict:
    p = out / "CONSUMER-READINESS.json"
    assert p.is_file(), f"no readiness at {p}"
    return json.loads(p.read_text())


def _consumer(*, idx: str, cmd: str = ":", expect: str = "ok",
              repl_status: str = "selected", repl_path: str = "/new/path",
              activation: str = "selected") -> dict:
    """Build one well-formed consumer dict. Non-HTTP expectations
    get a benign structured assertion; HTTP-shape skip it."""
    import re
    ver: dict = {"command": cmd, "expect": expect}
    if not re.match(r"^\s*\d{3}(\s+for\s+each)?\s*$", expect.strip()):
        ver["assertions"] = [{"type": "stdout_regex", "pattern": ".*",
                              "min_matches": 0, "max_matches": 2**31 - 1}]
    return {"id": idx, "ownership_edge": "fastapi_web_mount",
            "current_path": f"web/legacy/{idx}.html",
            "replacement": {"status": repl_status, "path": repl_path},
            "verification": ver,
            "activation_status": activation,
            "rollback": f"git revert <pr3e-sha> restores {idx}"}


def _base_manifest(consumers: list[dict], change: str = "migrate-nextjs-tailwind4") -> dict:
    """Build one well-formed top-level manifest for synthetic use."""
    return {"$schema_version": "1.0.0", "change": change,
            "planning_artifact": "cutover-manifest",
            "generated_by": "test fixture (synthetic)",
            "scope_intent": "synthetic selected coverage",
            "anchor": "design.md::§3.3.3",
            "fail_closed_summary": "synthetic",
            "edges": [{"id": "fastapi_web_mount",
                       "label": "FastAPI web mount ownership edge",
                       "anchor": "api/server.py:1815",
                       "single_origin_contract": "127.0.0.1:8765"}],
            "consumers": consumers,
            "selection_invariants": {"approach_status": "test"},
            "verifier_contract_summary": {"threshold": "synthetic"}}


def _write_manifest(tmp_path: Path, manifest: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest))
    return p


def test_legacy_selected_real_manifest_fails_closed_without_runtime_readiness(tmp_path):
    """The legacy-selected manifest still fails closed without runtime readiness."""
    out = tmp_path / "out"
    r = _run(["--manifest", str(MANIFEST), "--out", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / "CONSUMER-READINESS.json").is_file(), r.stderr


def test_synthetic_partial_unselected_fails_closed(tmp_path):
    """Two consumers; one unselected → fail-closed, no artifact, no check runs."""
    out = tmp_path / "out"
    m = _base_manifest([_consumer(idx="a-1"),
                        _consumer(idx="a-2", activation="unselected")])
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "a-2" in r.stderr and "unselected" in r.stderr


def test_synthetic_replacement_unselected_fails_closed(tmp_path):
    """activation selected but replacement.status unselected → fail-closed."""
    out = tmp_path / "out"
    m = _base_manifest([_consumer(idx="a-1"),
                        _consumer(idx="a-2", repl_status="unselected",
                                  repl_path="")])
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "a-2" in r.stderr and "replacement.status unselected" in r.stderr


def test_synthetic_selected_passing_checks_emit_atomic_artifact(tmp_path):
    """All selected, all checks pass → CONSUMER-READINESS.json emitted atomically
    (no temp leftover) with one entry per consumer and all_selected=True."""
    out = tmp_path / "out"
    cs = [_consumer(idx=f"a-{i}") for i in range(3)]
    m = _base_manifest(cs)
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode == 0, r.stderr
    body = _readiness(out)
    assert body["all_selected"] is True
    assert {c["id"] for c in body["consumers"]} == {"a-0", "a-1", "a-2"}
    leftovers = [p.name for p in out.rglob("*")
                 if p.is_file() and p.name.startswith(".CONSUMER-READINESS")]
    assert not leftovers, leftovers


def test_synthetic_selected_with_failing_check_no_artifact(tmp_path):
    """All consumers selected schema-wise, but one verification.command
    exits non-zero → fail-closed: exit non-zero, no artifact, no temp leftover."""
    out = tmp_path / "out"
    cs = [_consumer(idx="ok-1"),
          _consumer(idx="boom", cmd="false"),
          _consumer(idx="ok-2")]
    m = _base_manifest(cs)
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "boom" in r.stderr and "exited 1" in r.stderr
    temps = [p.name for p in out.rglob("*")
             if p.is_file() and p.name.startswith(".CONSUMER-READINESS")]
    assert not temps, temps


def test_synthetic_selected_multi_check_failures_all_reported(tmp_path):
    """Two failing checks → both consumer IDs appear in stderr (partial
    readiness is impossible; every check is independently gated)."""
    out = tmp_path / "out"
    cs = [_consumer(idx="boom-a", cmd="false"),
          _consumer(idx="boom-b", cmd="sh -c 'exit 7'")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "boom-a" in r.stderr and "boom-b" in r.stderr


def test_duplicate_consumer_ids_fail_closed(tmp_path):
    """Schema rejects duplicate consumer IDs (G3 unique-ID rule)."""
    out = tmp_path / "out"
    m = _base_manifest([_consumer(idx="dup-1"), _consumer(idx="dup-1")])
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "duplicate consumer id" in r.stderr


def test_missing_required_top_level_field_fails_closed(tmp_path):
    """A manifest missing a required top-level field (e.g. 'consumers' replaced
    by 'cons') is rejected; no artifact; stderr names the missing field."""
    out = tmp_path / "out"
    m = _base_manifest([_consumer(idx="a-1")])
    m["cons"] = m.pop("consumers")
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "consumers" in r.stderr


@pytest.mark.parametrize("missing", [
    "id", "ownership_edge", "current_path", "replacement",
    "verification", "activation_status", "rollback",
])
def test_missing_per_consumer_field_fails_closed(tmp_path, missing):
    """Per-consumer required fields are validated; missing → fail-closed."""
    out = tmp_path / "out"
    c = _consumer(idx="a-1"); del c[missing]
    m = _base_manifest([c])
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert missing in r.stderr or "missing required field" in r.stderr


def test_invalid_json_manifest_fails_with_no_artifact(tmp_path):
    """Corrupt JSON → fail-closed, no artifact, stderr names JSONDecodeError."""
    out = tmp_path / "out"
    p = tmp_path / "manifest.json"
    p.write_text("{ this is not json")
    r = _run(["--manifest", str(p), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "JSON" in r.stderr


def test_missing_manifest_arg_fails():
    """--manifest missing → usage error, no artifact write attempted."""
    r = _run(["--out", "/tmp/does-not-matter"])
    assert r.returncode != 0
    assert "usage" in r.stderr.lower() or "manifest" in r.stderr.lower()


def test_synthetic_selected_emits_zero_temp_leftovers(tmp_path):
    """Happy path leaves zero dot-prefixed temp artifacts (atomic emit)."""
    out = tmp_path / "out"
    cs = [_consumer(idx=f"a-{i}") for i in range(5)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode == 0, r.stderr
    temps = [p.name for p in out.rglob("*")
             if p.is_file() and p.name.startswith(".")]
    assert not temps, temps


# ── G3 slice: venv-aware pytest command execution ─────────────────────
def _write_fake_python(base: Path, name: str = "python") -> Path:
    """Write a POSIX shell script that records its post-script argv to
    the path stored in env var $RECORDER (JSON) and exits 0."""
    base.mkdir(parents=True, exist_ok=True)
    p = base / name
    p.write_text(
        "#!/bin/sh\n"
        "RECORDER=\"$RECORDER\" exec python3 -c 'import json,os,sys; "
        "json.dump(sys.argv[1:], open(os.environ[\"RECORDER\"], \"w\"))' \"$@\"\n"
    )
    p.chmod(0o755)
    return p


def test_venv_aware_pytest_uses_venv_python_when_provided(
        tmp_path, monkeypatch):
    """When `--venv <python>` is set, a verification.command starting with
    the bare token `pytest` is rewritten to `<python> -m pytest ...` so
    the project's venv python (not whatever `pytest` resolves to on PATH)
    is the one that runs the test."""
    recorder = tmp_path / "argv.json"
    monkeypatch.setenv("RECORDER", str(recorder))
    venv_python = _write_fake_python(tmp_path / "venv_bin")
    out = tmp_path / "out"
    cs = [_consumer(idx="py-1", cmd="pytest -q tests/foo.py")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    r = _run(["--manifest", str(mp), "--out", str(out),
              "--venv", str(venv_python)])
    assert r.returncode == 0, r.stderr
    argv = json.loads(recorder.read_text())
    # Recorder is invoked as: <python> -m pytest -q tests/foo.py
    assert argv == ["-m", "pytest", "-q", "tests/foo.py"], argv


def test_find_venv_python_preserves_symlink_path(tmp_path):
    """A venv python may be a symlink; preserve it so Python keeps its venv."""
    import scripts.verify_consumers as vc
    target = _write_fake_python(tmp_path / "target")
    link = tmp_path / ".venv" / "bin" / "python"
    link.parent.mkdir(parents=True)
    link.symlink_to(target)
    assert vc.find_venv_python(tmp_path) == link

def test_venv_aware_pytest_unchanged_when_venv_not_provided(tmp_path):
    """Without `--venv`, the verifier does NOT rewrite `pytest` commands
    (fail-closed: bare `pytest` on PATH may be wrong; venv-aware mode is
    strictly opt-in via the flag)."""
    out = tmp_path / "out"
    cs = [_consumer(idx="py-1", cmd="pytest -q tests/foo.py")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()


def test_venv_aware_pytest_does_not_rewrite_unrelated_prefix(tmp_path,
                                                             monkeypatch):
    """A command that merely contains `pytest` mid-string (e.g. the path
    `tests/pytest_legacy`) is NOT rewritten. Only the bare leading token
    `pytest` triggers the rewrite. Asserted by recording: if a rewrite
    had fired, the fake python would be invoked and write the recorder;
    since no rewrite happens, the recorder file MUST NOT exist."""
    recorder = tmp_path / "argv.json"
    monkeypatch.setenv("RECORDER", str(recorder))
    venv_python = _write_fake_python(tmp_path / "venv_bin")
    out = tmp_path / "out"
    # Benign command that exits 0; contains `pytest` mid-string only.
    cs = [_consumer(idx="py-1", cmd="echo tests/pytest_legacy_marker")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    r = _run(["--manifest", str(mp), "--out", str(out),
              "--venv", str(venv_python)])
    assert r.returncode == 0, r.stderr
    assert not recorder.exists(), (
f"recorder was written → a rewrite fired for an unrelated "
f"command. Content: {recorder.read_text() if recorder.exists() else None!r}")


# ── G3 slice: controlled local server lifecycle ───────────────────────
def _run_in_process(argv, *, monkeypatch=None):
    """Run verify_consumers.main() IN-PROCESS so monkeypatch on
    LocalServer / subprocess survives. Returns (rc, stderr_text)."""
    import scripts.verify_consumers as vc
    import contextlib, io
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = vc.main(argv)
    return rc, err.getvalue()


@pytest.fixture
def fake_local_server(monkeypatch):
    """Patch subprocess.Popen AND LocalServer._wait_ready so the
    controlled lifecycle runs without spawning uvicorn. The returned
    list is the sequence of FakeProc objects spawned (in-process)."""
    spawned = []

    class _FakeProc:
        def __init__(self, args, **kw):
            self.args = list(args)
            self.terminated = False
            self.killed = False
            self.waits = 0
            self.returncode = 0  # mimic successful exit
            spawned.append(self)
        def terminate(self): self.terminated = True
        def kill(self): self.killed = True
        def wait(self, timeout=None):
            self.waits += 1; return self.returncode
        def poll(self):
                return self.returncode  # 3.14 subprocess.run uses poll() only
        def communicate(self, input=None, timeout=None):
            self.returncode = 0
            return (b"", b"")
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False

    import scripts.verify_consumers as vc
    monkeypatch.setattr(vc.subprocess, "Popen", _FakeProc)
    monkeypatch.setattr(vc.LocalServer, "_wait_ready", lambda self: True)
    yield spawned


def test_serve_flag_spawns_local_server_before_checks_and_terminates(
        tmp_path, fake_local_server):
    """With `--serve`, the verifier:
      - spawns the local uvicorn server BEFORE any verification check,
      - terminates it AFTER every check completes (in `finally`-equivalent
        via LocalServer.__exit__).
    The uvicorn command shape is python -m uvicorn api.server:app."""
    out = tmp_path / "out"
    cs = [_consumer(idx=f"a-{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out), "--serve"])
    assert rc == 0, err
    # Filter to uvicorn spawns (every check command also goes through the
    # patched Popen; we only care about server spawns).
    server_spawns = [p for p in fake_local_server
                     if "uvicorn" in p.args]
    assert len(server_spawns) == 1, server_spawns
    proc = server_spawns[0]
    assert proc.terminated, "server must be terminated on clean exit"
    argv = proc.args
    assert "uvicorn" in argv and "api.server:app" in argv, argv


def test_serve_disabled_does_not_spawn_local_server(tmp_path,
                                                   fake_local_server):
    """Without `--serve`, the verifier MUST NOT spawn a local server
    (controlled lifecycle is strictly opt-in)."""
    out = tmp_path / "out"
    cs = [_consumer(idx=f"a-{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out)])
    assert rc == 0, err
    server_spawns = [p for p in fake_local_server
                     if "uvicorn" in p.args]
    assert server_spawns == [], server_spawns


def test_serve_flag_server_not_ready_exits_fail_closed(
        tmp_path, monkeypatch):
    """If the local server fails the healthcheck within the ready timeout,
    the verifier exits non-zero (EXIT_SERVER) and emits NO artifact
    (G3 fail-closed invariant preserved)."""
    import scripts.verify_consumers as vc

    class _FakeProc:
        def __init__(self, args, **kw):
            self.args = list(args)
            self.returncode = 0
        def terminate(self): pass
        def kill(self): pass
        def wait(self, timeout=None): return 0
        def poll(self): return 0
        def communicate(self, input=None, timeout=None):
            self.returncode = 0
            return (b"", b"")
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False

    monkeypatch.setattr(vc.subprocess, "Popen", _FakeProc)
    monkeypatch.setattr(vc.LocalServer, "_wait_ready", lambda self: False)

    out = tmp_path / "out"
    cs = [_consumer(idx="a-1")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out), "--serve"])
    assert rc != 0, err
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "ready" in err.lower(), err


# ── G3 slice: controlled fixture-serve on isolated port ───────────────
# The G3 verifier's `--serve` mode (uvicorn + FastAPI on 8765) is the
# production-runtime branch. The next G3 step is to additionally support
# a controlled **fixture-serve** branch: spawn `python -m http.server`
# against the merged self-contained fixture's `web/` directory on an
# ISOLATED free port (auto-picked via OS), so verification commands can
# be validated without touching the production FastAPI mount. The
# fixture's legacy port (8765) is rewritten to the new isolated port
# so manifest consumers continue to validate.


def _capture_popen(monkeypatch):
    """Install a Popen fake that records every spawn into a list. Used
    by the fixture-serve tests so we can assert both the http.server
    argv shape AND the verification-command rewriting in one shot."""
    import scripts.verify_consumers as vc
    captured = []

    class _CaptureProc:
        def __init__(self, args, **kw):
            self.args = list(args)
            self.returncode = 0
            captured.append(self)
        def terminate(self): pass
        def kill(self): pass
        def wait(self, timeout=None): return 0
        def poll(self): return 0
        def communicate(self, input=None, timeout=None):
            self.returncode = 0
            return (b"", b"")
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False

    monkeypatch.setattr(vc.subprocess, "Popen", _CaptureProc)
    monkeypatch.setattr(vc.LocalServer, "_wait_ready", lambda self: True)
    return captured


def test_fixture_web_root_spawns_python_http_server_not_uvicorn(
        tmp_path, monkeypatch):
    """With `--serve --fixture-web-root <dir>`, the controlled server is
    `python -m http.server <port> --directory <dir>`, NOT uvicorn. The
    new fixture-serve mode is wired in alongside the existing --serve
    uvicorn path so neither branch regresses the other."""
    out = tmp_path / "out"
    fixture_root = tmp_path / "fixture_web"
    fixture_root.mkdir()
    cs = [_consumer(idx=f"a-{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    captured = _capture_popen(monkeypatch)
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out),
         "--serve", "--fixture-web-root", str(fixture_root)])
    assert rc == 0, err
    http_servers = [p for p in captured if "http.server" in p.args]
    assert len(http_servers) == 1, [p.args for p in captured]
    argv = http_servers[0].args
    # Shape: <py> -m http.server <port> --directory <root>
    assert "-m" in argv and "http.server" in argv, argv
    assert "--directory" in argv, argv
    dir_idx = argv.index("--directory")
    assert argv[dir_idx + 1] == str(fixture_root), argv
    # Negative: NOT uvicorn (controlled fixture path is mutually exclusive
    # with the FastAPI mount path).
    assert "uvicorn" not in argv, argv


def test_fixture_web_root_uses_isolated_free_port_not_8765(
        tmp_path, monkeypatch):
    """The fixture-serve mode MUST bind to an isolated free port picked
    by the OS at probe time — NOT the legacy 8765. Asserted by: the
    http.server argv's port token is a positive integer, and ':8765'
    does not appear in the spawned argv."""
    out = tmp_path / "out"
    fixture_root = tmp_path / "fixture_web"
    fixture_root.mkdir()
    cs = [_consumer(idx="a-1")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    captured = _capture_popen(monkeypatch)
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out),
         "--serve", "--fixture-web-root", str(fixture_root)])
    assert rc == 0, err
    http_servers = [p for p in captured if "http.server" in p.args]
    assert len(http_servers) == 1
    argv = http_servers[0].args
    port_idx = argv.index("http.server") + 1
    port_token = argv[port_idx]
    assert port_token.isdigit(), f"port token not numeric: {port_token!r}"
    assert int(port_token) > 0, port_token
    assert int(port_token) <= 65535, port_token
    # Critical: must NOT be the legacy 8765 (isolated port invariant).
    assert "8765" not in argv, argv


def test_fixture_web_root_healthcheck_uses_isolated_port_and_index(
        tmp_path, monkeypatch):
    """The healthcheck URL for the fixture-serve mode MUST use the
    isolated port with `/index.html` (the fixture's known-good asset).
    This is what `_wait_ready` polls before releasing the verifier."""
    import scripts.verify_consumers as vc
    captured = _capture_popen(monkeypatch)
    seen = {}
    def _capture(self):
        seen["url"] = self.healthcheck
        seen["port"] = self.port
        return True
    monkeypatch.setattr(vc.LocalServer, "_wait_ready", _capture)

    out = tmp_path / "out"
    fixture_root = tmp_path / "fixture_web"
    fixture_root.mkdir()
    cs = [_consumer(idx="a-1")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out),
         "--serve", "--fixture-web-root", str(fixture_root)])
    assert rc == 0, err
    assert "url" in seen, "healthcheck never observed"
    assert "port" in seen, "port never observed"
    url = seen["url"]
    port = seen["port"]
    assert url == f"http://127.0.0.1:{port}/index.html", url
    assert port != 8765, port
    assert 0 < port <= 65535, port


def test_fixture_web_root_rewrites_verification_commands_to_isolated_port(
        tmp_path, monkeypatch):
    """When fixture-serve picks an isolated port, the verifier MUST
    rewrite each consumer's `verification.command` so the legacy
    `:8765` URL targets the new port. Without rewriting, the curl
    command would hit nothing and the check would fail spuriously.

    Asserted by: a recorder captures the shell command actually run.
    After rewriting, the URL says `127.0.0.1:<NEW_PORT>`, where
    <NEW_PORT> matches the port captured in the http.server argv.

    NOTE: HTTP-shape `expect` triggers wrapping through the controlled
    HTTP-status verifier (PR3d slice); the wrapper passes the rewritten
    URL as a quoted argument, so the new port URL is still observable
    inside the captured shell command string."""
    out = tmp_path / "out"
    fixture_root = tmp_path / "fixture_web"
    fixture_root.mkdir()
    legacy_cmd = ("curl -sS -o /dev/null -w '%{http_code}' "
                  "http://127.0.0.1:8765/index.html")
    cs = [_consumer(idx="legacy-1", cmd=legacy_cmd, expect="200")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    captured = _capture_popen(monkeypatch)
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out),
         "--serve", "--fixture-web-root", str(fixture_root),
         "--repo-root", str(REPO_ROOT)])
    assert rc == 0, err

    # The new port is the token right after 'http.server' in argv.
    http_servers = [p for p in captured if "http.server" in p.args]
    assert len(http_servers) == 1
    argv = http_servers[0].args
    new_port = argv[argv.index("http.server") + 1]
    assert new_port.isdigit() and new_port != "8765", argv

    # Find the verification check spawn: shell command '/bin/sh -c <cmd>'.
    check_spawns = [p for p in captured if p.args[:1] == ["/bin/sh"]]
    assert len(check_spawns) == 1, [p.args for p in captured]
    cmd = check_spawns[0].args[2]
    # Original 8765 must be gone; new port must be present.
    assert "127.0.0.1:8765" not in cmd, cmd
    assert f"127.0.0.1:{new_port}/index.html" in cmd, cmd


def test_fixture_web_root_missing_directory_fails_closed(
        tmp_path, monkeypatch):
    """If `--fixture-web-root <missing>` is provided, the verifier exits
    non-zero (fail-closed) and emits no CONSUMER-READINESS.json. We must
    not silently fall back to no-server or to a wrong directory."""
    captured = _capture_popen(monkeypatch)
    out = tmp_path / "out"
    missing = tmp_path / "does_not_exist"
    cs = [_consumer(idx="a-1")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out),
         "--serve", "--fixture-web-root", str(missing)])
    assert rc != 0, err
    assert not (out / "CONSUMER-READINESS.json").is_file()
    # No http.server spawn should have happened.
    http_servers = [p for p in captured if "http.server" in p.args]
    assert http_servers == [], [p.args for p in captured]
    # Stderr must mention the missing fixture (failure message present).
    assert ("fixture" in err.lower() or "does not exist" in err.lower()
            or "not a directory" in err.lower()), err


def test_fixture_web_root_without_serve_flag_does_not_spawn_server(
        tmp_path, monkeypatch):
    """`--fixture-web-root` without `--serve` is a no-op: the controlled
    lifecycle remains strictly opt-in via `--serve`. No http.server
    spawn, no port rewriting — the verifier behaves exactly as if
    `--fixture-web-root` were absent (benign synthetic consumers pass,
    http consumers would fail closed by their own logic)."""
    out = tmp_path / "out"
    fixture_root = tmp_path / "fixture_web"
    fixture_root.mkdir()
    cs = [_consumer(idx="a-1", cmd=":")]  # benign, no http needed
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    captured = _capture_popen(monkeypatch)
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out),
         "--fixture-web-root", str(fixture_root)])
    assert rc == 0, err
    http_servers = [p for p in captured if "http.server" in p.args]
    assert http_servers == [], [p.args for p in captured]


def test_fixture_web_root_server_terminates_on_clean_exit(
        tmp_path, monkeypatch):
    """Triangulate: the fixture-serve process is terminated on context
    exit (mirrors the existing uvicorn lifecycle). We track `terminate`
    and `wait` calls via a custom proc subclass."""
    import scripts.verify_consumers as vc
    spawned = []

    class _TrackProc:
        def __init__(self, args, **kw):
            self.args = list(args)
            self.terminated = False
            self.waited = False
            spawned.append(self)
        def terminate(self): self.terminated = True
        def kill(self): pass
        def wait(self, timeout=None):
            self.waited = True; return 0
        def poll(self): return 0
        def communicate(self, input=None, timeout=None):
            self.returncode = 0
            return (b"", b"")
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False

    monkeypatch.setattr(vc.subprocess, "Popen", _TrackProc)
    monkeypatch.setattr(vc.LocalServer, "_wait_ready", lambda self: True)

    out = tmp_path / "out"
    fixture_root = tmp_path / "fixture_web"
    fixture_root.mkdir()
    cs = [_consumer(idx="a-1")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out),
         "--serve", "--fixture-web-root", str(fixture_root)])
    assert rc == 0, err
    http_servers = [p for p in spawned if "http.server" in p.args]
    assert len(http_servers) == 1, [p.args for p in spawned]
    proc = http_servers[0]
    assert proc.terminated, "fixture http.server must be terminated on clean exit"
    assert proc.waited, "fixture http.server must be waited after terminate"


def test_fixture_web_root_isolated_port_avoids_8765_when_8765_in_use(
        tmp_path, monkeypatch):
    """Triangulate: even when 8765 is already in use (synthetic: bind
    it for the duration of the test), the fixture-serve mode MUST NOT
    bind 8765. Asserted by: the picked port differs from 8765 AND the
    verifier still passes (synthetic benign consumers)."""
    import socket as _socket
    captured = _capture_popen(monkeypatch)
    blocker = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    blocker.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 0)
    out = tmp_path / "out"
    fixture_root = tmp_path / "fixture_web"
    fixture_root.mkdir()
    try:
        try:
            blocker.bind(("127.0.0.1", 8765))
        except OSError:
            pytest.skip("8765 unavailable in this environment "
"(in use by another process); cannot assert "
"the isolated-port invariant locally.")
        blocker.listen(1)
        cs = [_consumer(idx="a-1")]
        mp = _write_manifest(tmp_path, _base_manifest(cs))
        rc, err = _run_in_process(
            ["--manifest", str(mp), "--out", str(out),
             "--serve", "--fixture-web-root", str(fixture_root)])
        assert rc == 0, err
        http_servers = [p for p in captured if "http.server" in p.args]
        assert len(http_servers) == 1
        argv = http_servers[0].args
        port = argv[argv.index("http.server") + 1]
        assert port != "8765", argv
    finally:
        blocker.close()


    # ── G3 slice: HTTP-shaped verification.expect enforcement ────────────
# The verifier previously trusted `verification.command`'s shell exit
# code alone — which is a bug because `curl -w '%{http_code}'` exits 0
# even when the server returns 404 (the connection succeeded). The G3
# manifest's `expect` field is HTTP-shaped (`"200"`, `"200 for each"`)
# for every static-mount consumer; non-HTTP expects (`"ok"`,
# `"1 passed"`, `"all passed"`) remain shell-exit-only. The verifier
# MUST detect HTTP-shape expectations and route the check through the
# controlled HTTP-status verifier (`tools/g3-legacy-fixture/scripts/
# check_http_status.py`) so the actual status code is validated. Any
# 404-vs-200 mismatch MUST fail-closed.

def test_http_shaped_expect_wraps_command_with_check_http_status(
        tmp_path, monkeypatch):
    """When a consumer's `expect` matches HTTP-shape ('200'), the
    verifier MUST route its `command` through the controlled
    HTTP-status verifier script (not just trust the shell exit).
    Asserted by: the actual shell command spawned contains the
    check_http_status.py path AND the original curl command AND the
    expected value `200`. Non-HTTP expectations ('ok') MUST NOT be
    wrapped."""
    captured = _capture_popen(monkeypatch)
    out = tmp_path / "out"
    legacy_cmd = ("curl -sS -o /dev/null -w '%{http_code}' "
                  "http://127.0.0.1:8765/index.html")
    cs = [_consumer(idx="http-1", cmd=legacy_cmd, expect="200"),
          _consumer(idx="benign-1", cmd=":", expect="ok")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    # Point --repo-root at the actual repo so the controlled helper
    # is discoverable (tmp_path is unrelated to the repo tree).
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out),
         "--repo-root", str(REPO_ROOT)])
    assert rc == 0, err
    # Find the shell-spawned verification checks.
    check_spawns = [p for p in captured if p.args[:1] == ["/bin/sh"]]
    assert len(check_spawns) == 2, [p.args for p in captured]
    wrapped = [s for s in check_spawns if "check_http_status" in s.args[2]]
    assert len(wrapped) == 1, [s.args for s in check_spawns]
    argv = wrapped[0].args[2]
    # Wrapper passes the original curl command and the expected value.
    assert "127.0.0.1:8765/index.html" in argv, argv
    assert "'200'" in argv or " 200 " in argv or argv.endswith(" 200"), argv
    # Negative: the benign consumer (expect='ok') is NOT wrapped.
    benign = [s for s in check_spawns if "check_http_status" not in s.args[2]]
    assert len(benign) == 1, [s.args for s in check_spawns]
    assert benign[0].args[2] == ":", benign[0].args


def test_http_shaped_expect_for_each_wraps_command_with_check_http_status(
        tmp_path, monkeypatch):
    """When `expect` is `'200 for each'` (loop-shape), the verifier
    MUST route the command through the controlled HTTP-status
    verifier so every emitted status code in the curl loop is
    validated, not just the shell exit."""
    captured = _capture_popen(monkeypatch)
    out = tmp_path / "out"
    loop_cmd = ("for m in state api; do "
                "curl -sS -o /dev/null -w '%{http_code}' "
                "http://127.0.0.1:8765/$m.js; done")
    cs = [_consumer(idx="loop-1", cmd=loop_cmd, expect="200 for each")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out),
         "--repo-root", str(REPO_ROOT)])
    assert rc == 0, err
    check_spawns = [p for p in captured if p.args[:1] == ["/bin/sh"]]
    assert len(check_spawns) == 1
    argv = check_spawns[0].args[2]
    assert "check_http_status" in argv, argv
    assert "for m in state api" in argv, argv
    assert "'200 for each'" in argv or "200 for each" in argv, argv


def test_http_shaped_expect_404_fail_closed(tmp_path, monkeypatch):
    """FAIL-CLOSED — when the actual HTTP status does not match the
    HTTP-shaped expectation, the controlled HTTP-status verifier exits
    non-zero and the G3 verifier propagates that exit (no
    CONSUMER-READINESS.json emitted).

    Setup: stage a fake `check_http_status.py` under a synthetic
    `tools/g3-legacy-fixture/scripts/` tree and point `--repo-root`
    at the synthetic root. The fake script exits 3 unconditionally
    (simulating a status mismatch). We deliberately do NOT patch
    subprocess.Popen — the verifier MUST actually spawn the fake
    script and observe its real non-zero exit code."""
    # Stage a fake check_http_status.py in a path the verifier
    # auto-discovers. We do this by writing into a fake
    # `tools/g3-legacy-fixture/scripts/check_http_status.py` relative
    # to a fake repo root.
    fake_root = tmp_path / "fake_tools"
    (fake_root / "tools" / "g3-legacy-fixture" / "scripts").mkdir(
        parents=True, exist_ok=True)
    fake_script = (fake_root / "tools" / "g3-legacy-fixture" / "scripts"
                   / "check_http_status.py")
    fake_script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stderr.write('[fake] simulated 404 mismatch\\n')\n"
        "sys.exit(3)\n"
    )
    fake_script.chmod(0o755)
    out = tmp_path / "out"
    legacy_cmd = ("curl -sS -o /dev/null -w '%{http_code}' "
                  "http://127.0.0.1:8765/index.html")
    cs = [_consumer(idx="mismatch-1", cmd=legacy_cmd, expect="200")]
    m = _base_manifest(cs)
    mp = fake_root / "manifest.json"
    mp.write_text(json.dumps(m))
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out),
         "--repo-root", str(fake_root)])
    assert rc != 0, (rc, err)
    assert not (out / "CONSUMER-READINESS.json").is_file()
    # Stderr must mention the simulated mismatch (the controlled
    # helper script was actually invoked AND its non-zero exit was
    # surfaced back to the verifier's caller).
    assert "mismatch" in err.lower(), err


def test_non_http_expect_preserves_shell_exit_only(tmp_path, monkeypatch):
    """Triangulate: when `expect` is non-HTTP-shape (`ok`, `1 passed`,
    `all passed`, or arbitrary text), the verifier MUST NOT wrap the
    command in check_http_status.py — shell exit code is the only
    gate. This preserves the existing pytest/grep consumers which
    rely on shell-only semantics."""
    captured = _capture_popen(monkeypatch)
    out = tmp_path / "out"
    cs = [
        _consumer(idx="benign-1", cmd=":", expect="ok"),
        _consumer(idx="benign-2", cmd=":", expect="1 passed"),
        _consumer(idx="benign-3", cmd=":", expect="all passed"),
        _consumer(idx="benign-4", cmd=":",
                  expect="three matches at lines 2180, 2188, 2194"),
    ]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out)])
    assert rc == 0, err
    check_spawns = [p for p in captured if p.args[:1] == ["/bin/sh"]]
    assert len(check_spawns) == 4
    # None of the non-HTTP consumers should have invoked the wrapper.
    wrapped = [s for s in check_spawns
               if "check_http_status" in s.args[2]]
    assert wrapped == [], [s.args for s in wrapped]


def test_http_shaped_expect_without_check_http_status_script_fails_closed(
        tmp_path, monkeypatch):
    """When `expect` is HTTP-shape but the controlled
    check_http_status.py helper is NOT discoverable (no fixture
    tools/, no opt-in override), the verifier MUST fail closed
    instead of silently trusting the shell exit. This protects
    against the original bug returning in any environment where the
    helper is absent (e.g. a CI runner without the fixture tree)."""
    import scripts.verify_consumers as vc
    # Force find_check_http_status_script to return None.
    monkeypatch.setattr(vc, "find_check_http_status_script",
                        lambda rp: None)
    out = tmp_path / "out"
    legacy_cmd = ("curl -sS -o /dev/null -w '%{http_code}' "
                  "http://127.0.0.1:8765/index.html")
    cs = [_consumer(idx="orphan-1", cmd=legacy_cmd, expect="200")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(out)])
    assert rc != 0, err
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "http-status" in err.lower() or "check_http_status" in err.lower(), err


# ── Follow-up 29: --repo-root CWD, --http-status-script, assertions ──
def _consumer_with_assertions(idx, cmd, expect, assertions):
    c = _consumer(idx=idx, cmd=cmd, expect=expect)
    c["verification"]["assertions"] = assertions
    return c


def _write_fake_helper(tmp_path, env_var):
    fake = tmp_path / "fake_helper.py"
    fake.write_text("#!/usr/bin/env python3\n"
                    "import os, sys\n"
                    f"open(os.environ['{env_var}'], 'w').write('invoked')\n"
                    "sys.exit(0)\n")
    fake.chmod(0o755)
    return fake


def _cwd_consumer(idx, expect_cwd):
    import re
    return _consumer_with_assertions(
        idx=idx,
        cmd=("python3 -c 'import os; "
              "cwd = os.getcwd(); "
              "open(os.environ[\"CWD_RECORDER\"], \"w\").write(cwd); "
              "print(cwd)'"),
        expect="ok",
        assertions=[{"type": "stdout_regex",
                     "pattern": re.escape(expect_cwd),
                     "min_matches": 1, "max_matches": 1}])


@pytest.mark.parametrize("use_repo_root,cid", [
    (True, "cwd-flag-1"),
    (False, "cwd-legacy-1"),
], ids=["explicit", "omitted"])
def test_repo_root_flag_cwd_behavior(tmp_path, monkeypatch, use_repo_root, cid):
    project = tmp_path / "temp_project"
    caller_cwd_dir = tmp_path / "caller_dir"
    manifest_dir = tmp_path / "manifest_dir"
    for d in (project, caller_cwd_dir, manifest_dir):
        d.mkdir()
    cwd_marker = tmp_path / "cwd.out"
    monkeypatch.setenv("CWD_RECORDER", str(cwd_marker))
    if use_repo_root:
        expected_cwd = str(project)
        mp = _write_manifest(tmp_path, _base_manifest(
            [_cwd_consumer(cid, expected_cwd)]))
        argv = ["--manifest", str(mp), "--out", str(tmp_path / "out"),
                "--repo-root", str(project)]
    else:
        expected_cwd = str(caller_cwd_dir)
        mp = manifest_dir / "manifest.json"
        mp.write_text(json.dumps(_base_manifest(
            [_cwd_consumer(cid, expected_cwd)])))
        argv = ["--manifest", str(mp), "--out", str(tmp_path / "out")]
    monkeypatch.chdir(caller_cwd_dir)
    rc, err = _run_in_process(argv)
    assert rc == 0, err
    recorded = cwd_marker.read_text().strip()
    assert recorded == expected_cwd, recorded


@pytest.mark.parametrize("scenario", [
    "override", "no_assertions",
], ids=["override_auto_discovery", "http_shape_no_assertions"])
def test_http_status_script_flag(tmp_path, monkeypatch, scenario):
    marker = tmp_path / "helper_invoked.marker"
    monkeypatch.setenv("HELPER_MARKER", str(marker))
    fake_helper = _write_fake_helper(tmp_path, "HELPER_MARKER")
    if scenario == "override":
        project_root = tmp_path / "project_no_helper"
        project_root.mkdir()
        cs = [_consumer(idx="opt-1",
                        cmd="curl -sS -o /dev/null -w '%{http_code}' "
                            "http://127.0.0.1:8765/index.html",
                        expect="200")]
        mp = _write_manifest(tmp_path, _base_manifest(cs))
        argv = ["--manifest", str(mp), "--out", str(tmp_path / "out"),
                "--repo-root", str(project_root),
                "--http-status-script", str(fake_helper)]
    else:
        cs = [_consumer(idx="http-shape-no-assertions-1",
                        cmd="printf '200\\n'", expect="200 for each")]
        cs[0]["verification"].pop("assertions", None)
        mp = _write_manifest(tmp_path, _base_manifest(cs))
        argv = ["--manifest", str(mp), "--out", str(tmp_path / "out"),
                "--http-status-script", str(fake_helper)]
    rc, err = _run_in_process(argv)
    assert rc == 0, err
    assert marker.exists(), f"stderr: {err}"
    assert marker.read_text() == "invoked", marker.read_text()


@pytest.mark.parametrize("bad,cmd,min_passed,should_pass,cid,scenario", [
    ([{"type": "stdout_regex", "pattern": "hello", "min_matches": 2, "max_matches": 2}],
     "printf 'hello\\nworld\\nhello\\n'", 0, True, "regex-pass", "regex"),
    ([{"type": "stdout_regex", "pattern": "hello", "min_matches": 3, "max_matches": 5}],
     "printf 'hello\\nworld\\n'", 0, False, "regex-under", "regex"),
    ([{"type": "stdout_regex", "pattern": "hello", "min_matches": 1, "max_matches": 2}],
     "printf 'hello\\nhello\\nhello\\nhello\\n'", 0, False, "regex-over", "regex"),
    ([{"type": "unknown_kind", "pattern": "x"}], ":", 0, False, "malformed-type", "malformed"),
    ([{"type": "stdout_regex", "min_matches": 1, "max_matches": 1}], ":", 0, False,
     "malformed-no-pat", "malformed"),
    ([{"type": "pytest_summary", "max_skipped": 0}], ":", 0, False,
     "malformed-no-min", "malformed"),
    ([{"type": "pytest_summary", "min_passed": 3, "max_skipped": 0}],
     "printf 'note: 3 passed are expected\\n'", 3, False, "pytest-not-summary", "pytest"),
    ([{"type": "pytest_summary", "min_passed": 3, "max_skipped": 0}],
     "printf '===== 3 passed, 2 skipped in 0.04s =====\\n'", 3, False, "pytest-skip", "pytest"),
    ([{"type": "stdout_regex", "pattern": "passed", "min_matches": 1, "max_matches": 1},
      {"type": "pytest_summary", "min_passed": 5, "max_skipped": 0}],
     "printf '===== 5 passed, 0 skipped in 0.04s =====\\n'", 5, True, "and-pass", "combined"),
    ([{"type": "stdout_regex", "pattern": "passed", "min_matches": 1, "max_matches": 1},
      {"type": "pytest_summary", "min_passed": 5, "max_skipped": 0}],
     "printf '1 passed, 0 skipped\\n'", 5, False, "and-fail", "combined"),
    ([{"type": "stdout_regex", "pattern": ".*", "min_matches": 0, "max_matches": 999}],
     "exit 7", 0, False, "cmd-fail-1", "nonzero"),
    (None, ":", 0, False, "no-assert-1", "missing"),
], ids=["regex-pass", "regex-under", "regex-over", "unknown_type",
        "missing_pattern", "missing_min_passed", "pytest-not-summary",
        "pytest-skip", "both-pass", "one-fails", "cmd-nonzero",
        "no-assertions"])
def test_assertions_structured_evaluation(tmp_path, bad, cmd, min_passed,
                                            should_pass, cid, scenario):
    if scenario == "missing":
        cs = [_consumer(idx=cid, cmd=cmd, expect="ok")]
        cs[0]["verification"].pop("assertions", None)
    else:
        cs = [_consumer_with_assertions(idx=cid, cmd=cmd, expect="ok", assertions=bad)]
    out = tmp_path / "out"
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    if should_pass:
        assert r.returncode == 0, r.stderr
    else:
        assert r.returncode != 0, r.stderr
        assert not (out / "CONSUMER-READINESS.json").is_file()
        assert cid in r.stderr


# ── Follow-up 30: blocked-gate contract for selected consumers ──

def _blocked_consumer(idx, reason="<reason>", status="blocked"):
    return {"id": idx, "ownership_edge": "fastapi_web_mount",
            "current_path": f"web/legacy/{idx}.html",
            "replacement": {"status": "selected", "path": "/new/path"},
            "verification": {"command": "printf 'ok\\n'", "expect": "ok",
                             "assertions": [{"type": "stdout_regex", "pattern": "^ok$",
                                             "min_matches": 1, "max_matches": 1}],
                             "status": status, "blocked_reason": reason},
            "activation_status": "selected",
            "rollback": f"git revert <pr3e-sha> restores {idx}"}


def test_blocked_status_unknown_value_fails_schema_validation(tmp_path):
    out = tmp_path / "out"
    mp = _write_manifest(tmp_path, _base_manifest(
        [_blocked_consumer(idx="bad-1", status="not-real")]))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode == 4 and not (out / "CONSUMER-READINESS.json").is_file()
    assert "bad-1" in r.stderr, r.stderr


def test_blocked_reason_missing_fails_schema_validation(tmp_path):
    out = tmp_path / "out"
    c = _blocked_consumer(idx="no-reason-1")
    del c["verification"]["blocked_reason"]
    mp = _write_manifest(tmp_path, _base_manifest([c]))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode == 4 and not (out / "CONSUMER-READINESS.json").is_file()
    assert "no-reason-1" in r.stderr and "blocked_reason" in r.stderr


def test_blocked_reason_blank_fails_schema_validation(tmp_path):
    out = tmp_path / "out"
    mp = _write_manifest(tmp_path, _base_manifest(
        [_blocked_consumer(idx="blank-reason-1", reason="   ")]))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode == 4 and not (out / "CONSUMER-READINESS.json").is_file()
    assert "blank-reason-1" in r.stderr, r.stderr


def test_blocked_reason_without_blocked_status_fails_schema_validation(tmp_path):
    out = tmp_path / "out"
    c = _blocked_consumer(idx="orphan-1")
    c["verification"].pop("status", None)
    mp = _write_manifest(tmp_path, _base_manifest([c]))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode == 4 and not (out / "CONSUMER-READINESS.json").is_file()
    assert "orphan-1" in r.stderr, r.stderr


def test_blocked_status_explicit_null_fails_schema_validation(tmp_path):
    out = tmp_path / "out"
    c = _blocked_consumer(idx="null-status-1")
    c["verification"]["status"] = None
    del c["verification"]["blocked_reason"]
    mp = _write_manifest(tmp_path, _base_manifest([c]))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode == 4 and not (out / "CONSUMER-READINESS.json").is_file()
    assert "null-status-1" in r.stderr and "verification.status" in r.stderr


def test_blocked_consumer_fails_closed_with_id_and_reason_diagnostic(tmp_path):
    # Pop `assertions` to prove blocked needs none; OLD→rc4, NEW→rc5.
    out = tmp_path / "out"
    reason = "size budget not accepted for #18"
    c = _blocked_consumer(idx="block-18", reason=reason)
    c["verification"].pop("assertions", None)
    assert c["replacement"]["status"] == "selected"
    assert c["activation_status"] == "selected"
    mp = _write_manifest(tmp_path, _base_manifest([c]))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode == 5, r.stderr
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "block-18" in r.stderr and reason in r.stderr


def test_blocked_preflight_short_circuits_before_server_start(
        tmp_path, monkeypatch):
    import scripts.verify_consumers as vc
    mp = _write_manifest(tmp_path, _base_manifest(
        [_blocked_consumer(idx="block-pre-srv", reason="<r>")]))
    entered = []
    def _fail_enter(self):
        entered.append(self)
        raise RuntimeError("blocked preflight should run before LocalServer")
    monkeypatch.setattr(vc.LocalServer, "__enter__", _fail_enter)
    rc, _ = _run_in_process(
        ["--manifest", str(mp), "--out", str(tmp_path / "out"), "--serve"])
    assert rc != 0 and not (tmp_path / "out" / "CONSUMER-READINESS.json").is_file()
    assert entered == []


def test_blocked_preflight_short_circuits_before_any_consumer_command(
        tmp_path, monkeypatch):
    import scripts.verify_consumers as vc
    cs = [_consumer(idx="passing-1", cmd=": (must not run)"),
          _blocked_consumer(idx="block-20", reason="<r>")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    recorder = []
    def _fake_run(cmd, **kw):
        recorder.append(cmd)
        return (0, "ok\n")
    monkeypatch.setattr(vc, "_run_check_with_stdout", _fake_run)
    rc, _ = _run_in_process(["--manifest", str(mp), "--out", str(tmp_path / "out")])
    assert rc != 0 and not (tmp_path / "out" / "CONSUMER-READINESS.json").is_file()
    assert recorder == []


# ── Follow-up 31: valid blocked gates surface before unrelated
# non-HTTP assertion-schema failures ───────────────────────────

def test_blocked_short_circuits_before_unblocked_assertion_schema(
        tmp_path, monkeypatch):
    """Follow-up 31: when the manifest carries at least one valid
    blocked consumer alongside an unblocked non-HTTP consumer whose
    `verification.assertions` are absent, the verifier MUST:

      1. validate base manifest structure and every blocked
         status/reason first,
      2. report each blocked ID and reason in stderr,
      3. return EXIT_CHECK (5), NOT EXIT_MANIFEST (4),
      4. emit NO CONSUMER-READINESS.json,
      5. skip unrelated non-HTTP assertion-schema validation, and
      6. not discover helpers/venvs, not construct LocalServer, not
         execute any consumer command.

    The pre-blocked validation pass MUST NOT mask the missing
    assertion on the unblocked consumer — the blocked preflight is
    the contract the verifier honors, and EXIT_CHECK is the right
    semantic for an admitted blocked gate, not EXIT_MANIFEST.

    Synthetic manifest, fake seams only (no sockets or subprocess
    consumer runs)."""
    import scripts.verify_consumers as vc
    reason_18 = "no explicit JS/CSS size budget accepted"
    reason_20 = "G5 evidence and capture authorization unresolved"
    # Two valid blocked consumers (mirror Follow-up 30 #18/#20) plus
    # one unblocked non-HTTP consumer with NO assertions key — this
    # is the unrelated assertion-schema failure that previously
    # forced EXIT_MANIFEST before the blocked preflight could fire.
    cs = [
        _blocked_consumer(idx="block-18", reason=reason_18),
        _blocked_consumer(idx="block-20", reason=reason_20),
        # Unblocked non-HTTP consumer missing assertions.
        _consumer(idx="unblocked-1", cmd=": (must not run)"),
    ]
    cs[2]["verification"].pop("assertions", None)
    assert cs[2]["verification"].get("status") != "blocked"
    mp = _write_manifest(tmp_path, _base_manifest(cs))

    # Fake seams: any call into LocalServer, helpers, or consumer
    # command runners must fail loudly so the test detects bypass.
    entered_server = []
    def _fail_enter(self):
        entered_server.append(self)
        raise RuntimeError("LocalServer must not start when blocked "
                           "preflight short-circuits")
    monkeypatch.setattr(vc.LocalServer, "__enter__", _fail_enter)

    consumer_runs = []
    def _fake_run_with_stdout(cmd, **kw):
        consumer_runs.append(cmd)
        return (0, "ok\n")
    def _fake_run(cmd, **kw):
        consumer_runs.append(cmd)
        return 0
    monkeypatch.setattr(vc, "_run_check_with_stdout",
                        _fake_run_with_stdout)
    monkeypatch.setattr(vc, "_run_check", _fake_run)

    helper_calls = []
    monkeypatch.setattr(vc, "find_venv_python",
                        lambda rp: helper_calls.append("venv") or None)
    monkeypatch.setattr(vc, "find_check_http_status_script",
                        lambda rp: helper_calls.append("helper") or None)

    rc, err = _run_in_process(
        ["--manifest", str(mp), "--out", str(tmp_path / "out"),
         "--serve"])
    # Outcome: EXIT_CHECK (5), not EXIT_MANIFEST (4).
    assert rc == 5, (rc, err)
    # All blocked IDs/reasons surface in stderr.
    assert "block-18" in err, err
    assert reason_18 in err, err
    assert "block-20" in err, err
    assert reason_20 in err, err
    # The unblocked missing-assertion diagnostic must NOT bypass the
    # blocked gate: the verifier honors the valid blockers, and
    # EXIT_CHECK is the contract (no EXIT_MANIFEST leak).
    assert "unblocked-1" not in err, err
    assert "verification.assertions" not in err, err
    # No readiness artifact.
    assert not (tmp_path / "out" / "CONSUMER-READINESS.json").is_file()
    # No server/helper/venv discovery, no consumer command ran.
    assert entered_server == [], entered_server
    assert consumer_runs == [], consumer_runs
    assert helper_calls == [], helper_calls


def test_no_blocker_unblocked_missing_assertions_still_fails_manifest(
        tmp_path):
    """Triangulate: with NO valid blocked consumer, an unblocked
    non-HTTP consumer missing `verification.assertions` MUST still
    fail closed with EXIT_MANIFEST (4). The Follow-up 31 reorder
    only short-circuits when valid blockers exist; without blockers
    the verifier preserves the existing fail-closed behavior for
    missing/malformed assertions."""
    out = tmp_path / "out"
    cs = [_consumer(idx="unblocked-2", cmd=":")]
    cs[0]["verification"].pop("assertions", None)
    assert cs[0]["verification"].get("status") != "blocked"
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode == 4, r.stderr
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "unblocked-2" in r.stderr, r.stderr
    assert "verification.assertions" in r.stderr, r.stderr


def test_malformed_blocked_status_still_fails_schema_before_short_circuit(
        tmp_path):
    """Triangulate: a malformed `verification.status` (not the
    string "blocked") MUST still fail base schema validation
    (EXIT_MANIFEST) and must NOT be confused with a valid blocker.
    The Follow-up 31 reorder is fail-closed: schema errors never
    bypass EXIT_MANIFEST, regardless of any other consumer shape."""
    out = tmp_path / "out"
    cs = [_blocked_consumer(idx="bad-status-1", status="not-real")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode == 4, r.stderr
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "bad-status-1" in r.stderr, r.stderr
