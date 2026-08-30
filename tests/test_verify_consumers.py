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
    """Build one well-formed consumer dict for synthetic manifests."""
    return {"id": idx, "ownership_edge": "fastapi_web_mount",
            "current_path": f"web/legacy/{idx}.html",
            "replacement": {"status": repl_status, "path": repl_path},
            "verification": {"command": cmd, "expect": expect},
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
    <NEW_PORT> matches the port captured in the http.server argv."""
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
         "--serve", "--fixture-web-root", str(fixture_root)])
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
