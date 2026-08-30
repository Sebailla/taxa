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


def test_unselected_real_manifest_fails_closed_no_artifact(tmp_path):
    """Real merged manifest has every consumer unselected → exit non-zero,
    NO CONSUMER-READINESS.json emitted (G3 fail-closed invariant)."""
    out = tmp_path / "out"
    r = _run(["--manifest", str(MANIFEST), "--out", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / "CONSUMER-READINESS.json").is_file(), r.stderr
    assert "unselected" in r.stderr or "selection" in r.stderr.lower(), r.stderr


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
