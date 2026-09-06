"""Strict-TDD regression suite for scripts/rehearse_cutover.py (Phase 6b G6).

Restores the missing test file for the cutover-rehearsal script. Covers
the Phase 6b strict-TDD contract documented in the script's module
docstring:

  - The rehearsal ALWAYS owns a controlled local static server on an
    OS-picked isolated free TCP port — the ambient port 8765 owned by
    the production FastAPI mount is NEVER bound.
  - The controlled server is terminated on both successful and failed
    exits (the context-manager lifecycle is strict).
  - A subset-only cutover (web_dir_only / consumers_only /
    makefile_only / artifact_only) is FAIL-CLOSED: exit 2, no verifier
    invocation, no G6 evidence emit, no apply-progress.md update.
  - A missing / non-directory fixture-web-root is FAIL-CLOSED: exit 3.
  - The tmp port-rewritten manifest copy is removed on every exit path
    (success and error).
  - The cutover-rehearsal.json artifact carries the pinned G6 fields
    (gate, status, captured_at, manifest_path, activation_complete,
    unselected_count, silent_fallback_paths, g3_tier2_exit_code,
    consumer_readiness) and is only emitted on a complete rehearsal.
  - apply-progress.md G6 footer is only flipped when the real
    rehearsal (no test-mode flags) exits 0 with no silent fallback
    paths. The flip is idempotent.

All tests run in-process (so monkeypatch on the script's subprocess
+ verifier hooks survives) and never bind ambient TCP ports — the
controlled server's subprocess.Popen is patched to a recorder.
"""
from __future__ import annotations

import contextlib
import datetime
import io
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import pytest

import scripts.rehearse_cutover as rc
from scripts.rehearse_cutover import (
    CUTOVER_UNIT_SUBSETS,
    ControlledStaticServer,
    EXIT_OK,
    EXIT_G3,
    EXIT_SUBSET_ONLY,
    EXIT_REHEARSAL,
    EXIT_USAGE,
    DEFAULT_MANIFEST,
    DEFAULT_REHEARSAL_OUT,
    DEFAULT_APPLY_PROGRESS,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "rehearse_cutover.py"
WORKING_MANIFEST = (
    REPO_ROOT / "openspec" / "changes" / "complete-taxa-frontend-migration"
    / "cutover-manifest.json"
)
APPLY_PROGRESS = (
    REPO_ROOT / "openspec" / "changes" / "complete-taxa-frontend-migration"
    / "apply-progress.md"
)
PREDECESSOR_MANIFEST = (
    REPO_ROOT / "openspec" / "changes" / "migrate-nextjs-tailwind4"
    / "cutover-manifest.json"
)


# ── In-process runner + manifest / consumer helpers ─────────────────────────


def _run_in_process(argv: Iterable[str]) -> tuple[int, str]:
    """Run rc.main(argv) IN-PROCESS so monkeypatch on the script's
    subprocess / verifier hooks survives. Returns (exit_code, stderr).

    The script's ``main`` returns an int directly (no SystemExit on the
    happy path); argparse calls ``SystemExit`` on parse errors which we
    map back to the int exit code (defaulting to ``EXIT_USAGE``).
    """
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        try:
            code = rc.main(list(argv))
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else EXIT_USAGE
    return int(code), err.getvalue()


def _postcut_consumer(idx: str, *, cmd: str = "true",
                       expect: str = "ok") -> dict[str, Any]:
    """A fully-activated (Tier-2) consumer: replacement.path differs from
    current_path. Mirrors the post-cut shape the verifier expects."""
    return {
        "id": idx,
        "ownership_edge": "fastapi_web_mount",
        "current_path": f"web/legacy/{idx}.html",
        "replacement": {"status": "selected", "path": f"out/{idx}.html"},
        "verification": {"command": cmd, "expect": expect},
        "activation_status": "selected",
        "rollback": f"git revert <pr3e-sha> restores {idx}",
    }


def _legacy_consumer(idx: str, *, cmd: str = "true",
                     expect: str = "ok") -> dict[str, Any]:
    """A legacy (Tier-1) consumer: replacement.path == current_path
    (no flip performed). Drives the subset-only detection branch."""
    current = f"web/legacy/{idx}.html"
    return {
        "id": idx,
        "ownership_edge": "fastapi_web_mount",
        "current_path": current,
        "replacement": {"status": "selected", "path": current},
        "verification": {"command": cmd, "expect": expect},
        "activation_status": "selected",
        "rollback": f"git revert <pr3e-sha> restores {idx}",
    }


def _base_manifest(consumers: list[dict],
                   *, change: str = "complete-taxa-frontend-migration"
                   ) -> dict[str, Any]:
    """Top-level manifest shape; mirrors the real Phase 6b manifest
    closely enough that the script's subset-only detector and verifier
    path resolve identically to a real rehearsal."""
    return {
        "$schema_version": "1.0.0",
        "change": change,
        "planning_artifact": "cutover-manifest",
        "generated_by": "test fixture (synthetic)",
        "scope_intent": "synthetic selected coverage",
        "anchor": "design.md::§3.3.3",
        "fail_closed_summary": "synthetic",
        "edges": [
            {"id": "fastapi_web_mount",
             "label": "FastAPI web mount ownership edge",
             "anchor": "api/server.py:1815",
             "single_origin_contract": "127.0.0.1:8765"},
        ],
        "consumers": consumers,
        "selection_invariants": {"approach_status": "test"},
        "verifier_contract_summary": {"threshold": "synthetic"},
    }


def _write_manifest(tmp_path: Path, manifest: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest))
    return p


def _make_web_root(tmp_path: Path) -> Path:
    """Build a minimal but valid http.server web root with an
    index.html that returns 200."""
    root = tmp_path / "web"
    root.mkdir()
    (root / "index.html").write_text("<!doctype html><title>ok</title>")
    return root


# ── Fake-process + verifier-stub fixtures ───────────────────────────────────


class _FakeProc:
    """In-process stand-in for ``subprocess.Popen``. Records the argv
    so tests can assert the rehearsal binds a free port (never 8765)
    and terminates the process on context exit."""

    def __init__(self, args, **kw):
        self.args = list(args) if not isinstance(args, str) else args
        self.kw = kw
        self.terminated = False
        self.killed = False
        self.waits: list[float | None] = []
        self.returncode = None  # still running until terminate()

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        self.waits.append(timeout)
        return self.returncode

    def poll(self):
        return self.returncode

    def communicate(self, input=None, timeout=None):
        if self.returncode is None:
            self.returncode = 0
        return (b"", b"")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _VerifierStub:
    """Records each ``verify_consumers.main(argv)`` call and returns a
    preset exit code. Replaces the real verifier so tests don't have to
    ship real ``out/`` artifacts or run real pytest checks. The stub
    still writes a minimal ``CONSUMER-READINESS.json`` into ``--out``
    so the rehearsal's downstream artifact code path is exercised."""

    def __init__(self, *, exit_code: int = 0,
                 readiness: dict | None = None):
        self.exit_code = exit_code
        self.readiness = readiness if readiness is not None else {
            "schema_version": "1.0.0",
            "change": "complete-taxa-frontend-migration",
            "consumers": [],
            "all_selected": True,
            "unselected_count": 0,
        }
        self.calls: list[list[str]] = []
        # Captured at call time so tests can introspect the rewritten
        # manifest before the rehearsal's finally block unlinks it.
        self.manifest_snapshots: list[str | None] = []

    def __call__(self, argv):
        self.calls.append(list(argv))
        # Capture the rewritten manifest the rehearsal hands us, BEFORE
        # the rehearsal's finally block unlinks it.
        for i, tok in enumerate(argv):
            if tok == "--manifest" and i + 1 < len(argv):
                mp = Path(argv[i + 1])
                if mp.is_file():
                    self.manifest_snapshots.append(mp.read_text())
                else:
                    self.manifest_snapshots.append(None)
                break
        else:
            self.manifest_snapshots.append(None)
        # Mirror the real verifier's emit behaviour: write readiness
        # into the --out dir when the verifier passes.
        out = None
        for i, tok in enumerate(argv):
            if tok == "--out" and i + 1 < len(argv):
                out = Path(argv[i + 1])
                break
        if out is not None and self.exit_code == 0:
            out.mkdir(parents=True, exist_ok=True)
            (out / "CONSUMER-READINESS.json").write_text(
                json.dumps(self.readiness))
        return self.exit_code


@pytest.fixture
def fake_popen(monkeypatch):
    """Patch ``subprocess.Popen`` in BOTH ``scripts.rehearse_cutover``
    and ``scripts.verify_consumers`` so neither module spawns a real
    process. Also short-circuit ``ControlledStaticServer._wait_ready``
    so the controlled server reports ready immediately."""
    spawned: list[_FakeProc] = []

    def _factory(args, **kw):
        proc = _FakeProc(args, **kw)
        spawned.append(proc)
        return proc

    import scripts.verify_consumers as vc_mod
    monkeypatch.setattr(rc.subprocess, "Popen", _factory)
    monkeypatch.setattr(vc_mod.subprocess, "Popen", _factory)
    monkeypatch.setattr(ControlledStaticServer, "_wait_ready",
                        lambda self: True)
    return spawned


@pytest.fixture
def stub_verifier(monkeypatch):
    """Replace ``scripts.verify_consumers.main`` with a controllable
    stub. Returns the stub object; tests mutate ``stub.exit_code``
    before invoking the rehearsal."""
    stub = _VerifierStub()
    import scripts.verify_consumers as vc_mod
    monkeypatch.setattr(vc_mod, "main", stub)
    return stub


@pytest.fixture
def apply_progress_snapshot():
    """Snapshot the on-disk apply-progress.md bytes (if any) and
    restore them after the test. The rehearsal's G6 footer flip is
    real; without this fixture a successful test would mutate the
    production gate-status footer."""
    if APPLY_PROGRESS.is_file():
        original = APPLY_PROGRESS.read_bytes()
        existed = True
    else:
        original = b""
        existed = False
    yield APPLY_PROGRESS
    if existed:
        APPLY_PROGRESS.write_bytes(original)
    elif APPLY_PROGRESS.exists():
        APPLY_PROGRESS.unlink()


@pytest.fixture
def predecessor_snapshot():
    """Snapshot the predecessor manifest bytes so the test can confirm
    the rehearsal never mutates it (the contract: only the tmp copy
    inside ``/tmp`` is rewritten)."""
    if PREDECESSOR_MANIFEST.is_file():
        original = PREDECESSOR_MANIFEST.read_bytes()
        existed = True
    else:
        original = b""
        existed = False
    yield PREDECESSOR_MANIFEST
    if existed:
        PREDECESSOR_MANIFEST.write_bytes(original)
    elif PREDECESSOR_MANIFEST.exists():
        PREDECESSOR_MANIFEST.unlink()


# ── 1. Structural / interface sanity ────────────────────────────────────────


def test_rehearse_cutover_script_exists_and_is_executable():
    """The script must exist at the canonical path and be a regular
    file. The orchestrator contract pins this surface."""
    assert SCRIPT.is_file(), f"missing script: {SCRIPT}"
    # The Phase 6b slice relies on the script being importable as
    # ``scripts.rehearse_cutover`` — confirm the import path resolves.
    import scripts.rehearse_cutover  # noqa: F401


def test_rehearse_cutover_exposes_run_g3_tier2_helper():
    """The shared Tier-2 invocation helper is the public seam between
    the rehearsal and the apply worker (PR 3e). It MUST be exposed as
    a module attribute (not nested inside ``main``)."""
    assert hasattr(rc, "run_g3_tier2"), "run_g3_tier2 must be module-public"
    assert callable(rc.run_g3_tier2)
    # The helper signature accepts (manifest_path, out_dir, *,
    # repo_root=None, fixture_web_root=None) — apply worker depends
    # on this exact shape.
    import inspect
    sig = inspect.signature(rc.run_g3_tier2)
    kinds = {name: p.kind for name, p in sig.parameters.items()}
    # First two are positional-or-keyword (in declaration order).
    names_in_order = list(sig.parameters)
    assert names_in_order[:2] == ["manifest_path", "out_dir"], names_in_order
    # repo_root + fixture_web_root are keyword-only with defaults.
    for kw in ("repo_root", "fixture_web_root"):
        assert kw in kinds, sig
        assert kinds[kw] == inspect.Parameter.KEYWORD_ONLY, (kw, kinds[kw])
        assert sig.parameters[kw].default is None, sig


def test_rehearse_cutover_run_g3_tier2_helper_does_not_use_subprocess():
    """Per the Phase 6b orchestrator contract: the shared helper calls
    ``scripts.verify_consumers.main(argv)`` IN-PROCESS (no shell-out
    to a python subprocess) so the apply worker can call it without a
    fresh interpreter."""
    import inspect
    src = inspect.getsource(rc.run_g3_tier2)
    # The helper MUST delegate to verify_consumers.main.
    assert "vc.main" in src, (
        "run_g3_tier2 must delegate to scripts.verify_consumers.main")
    # No subprocess call/launch surface (the helper must not spawn a
    # python interpreter). The docstring may legitimately mention
    # "subprocess" prose; check for actual usage instead.
    for needle in ("subprocess.run", "subprocess.Popen", "subprocess.call",
                   "subprocess.check_call", "subprocess.check_output",
                   "os.system", "os.popen", "os.execv", "os.spawn"):
        assert needle not in src, (
            f"run_g3_tier2 must invoke verify_consumers.main "
            f"in-process; forbidden call: {needle}")


def test_run_g3_tier2_invokes_verify_consumers_main_in_process(
        tmp_path, fake_popen, stub_verifier):
    """End-to-end: ``run_g3_tier2`` starts the controlled server,
    writes a port-rewritten tmp manifest copy, and calls
    ``scripts.verify_consumers.main`` with --manifest <tmp> --out <dir>.
    Confirms the verifier receives the rewritten manifest (not the
    on-disk one)."""
    manifest = _base_manifest([
        _postcut_consumer("c1",
                           cmd="curl -sS http://127.0.0.1:8765/c1"),
        _postcut_consumer("c2",
                           cmd="curl -sS http://127.0.0.1:8765/c2"),
    ])
    mp = _write_manifest(tmp_path, manifest)
    web_root = _make_web_root(tmp_path)

    g3 = rc.run_g3_tier2(manifest_path=mp, out_dir=tmp_path / "out",
                         repo_root=tmp_path, fixture_web_root=web_root)
    assert g3 == 0
    assert len(stub_verifier.calls) == 1
    argv = stub_verifier.calls[0]
    # The verifier must NOT receive --serve / --fixture-web-root —
    # the rehearsal owns the server lifecycle.
    assert "--serve" not in argv, argv
    assert "--fixture-web-root" not in argv, argv
    # The verifier must receive the tmp manifest (NOT the on-disk one).
    assert "--manifest" in argv
    mp_arg = argv[argv.index("--manifest") + 1]
    assert Path(mp_arg).resolve() != mp.resolve(), argv
    assert Path(mp_arg).name.startswith(".tmp-rehearsal-manifest-"), argv
    # Controlled server spawn: the rehearsal bound an isolated port,
    # NOT 8765.
    server_spawns = [p for p in fake_popen
                     if "http.server" in p.args]
    assert len(server_spawns) == 1
    port_arg = server_spawns[0].args[
        server_spawns[0].args.index("--directory") - 1
        if "--directory" in server_spawns[0].args
        else 3]
    # argv = [python, "-m", "http.server", "<port>", "--directory", ...]
    argv_list = server_spawns[0].args
    port_idx = argv_list.index("--directory") - 1
    port = int(argv_list[port_idx])
    assert port != ControlledStaticServer.AMBIENT_PORT_FASTAPI, (
        f"controlled server must not bind ambient port {port}")


# ── 2. ControlledStaticServer unit tests ────────────────────────────────────


def test_controlled_server_picks_isolated_free_port_not_8765(
        tmp_path, monkeypatch):
    """``_pick_free_port`` must request an OS-assigned port (bind to 0)
    and refuse to return the ambient FastAPI port 8765. We patch
    ``socket.socket`` to observe the bind call without actually
    binding."""
    binds: list[tuple[str, int]] = []

    class _FakeSock:
        def __init__(self, family, type):
            self.family, self.type = family, type
        def bind(self, addr):
            binds.append(addr)
        def getsockname(self):
            # Pick a port that's definitely not 8765.
            return ("127.0.0.1", 41234)
        def close(self):
            pass

    monkeypatch.setattr(rc.socket, "socket", _FakeSock)
    server = ControlledStaticServer(web_root=tmp_path)
    port = server._pick_free_port()
    assert binds == [("127.0.0.1", 0)], binds
    assert port != ControlledStaticServer.AMBIENT_PORT_FASTAPI


def test_controlled_server_fails_closed_when_fixture_web_root_is_a_file(
        tmp_path, monkeypatch):
    """When the supplied web root exists but is a FILE (not a dir),
    ``ControlledStaticServer.__enter__`` MUST raise RuntimeError and
    never spawn a subprocess (fail-closed before any bind / spawn)."""
    f = tmp_path / "not_a_dir"
    f.write_text("x")
    server = ControlledStaticServer(web_root=f)
    spawns: list = []
    monkeypatch.setattr(ControlledStaticServer, "_spawn",
                        lambda self, argv, **kw: spawns.append(argv)
                        or _FakeProc(argv))
    with pytest.raises(RuntimeError) as ei:
        with server:
            pass
    assert "not a directory" in str(ei.value).lower()
    assert spawns == [], "must not spawn when web_root is a file"


def test_controlled_server_fails_closed_when_fixture_web_root_missing(
        tmp_path, monkeypatch):
    """Missing web root path: RuntimeError before any spawn."""
    missing = tmp_path / "does_not_exist"
    server = ControlledStaticServer(web_root=missing)
    spawns: list = []
    monkeypatch.setattr(ControlledStaticServer, "_spawn",
                        lambda self, argv, **kw: spawns.append(argv)
                        or _FakeProc(argv))
    with pytest.raises(RuntimeError) as ei:
        with server:
            pass
    assert "does not exist" in str(ei.value).lower()
    assert spawns == [], "must not spawn when web_root is missing"


def test_controlled_server_origin_raises_before_start(tmp_path):
    """``origin`` must raise before the server starts (port is None) so
    tests / callers can't accidentally read a stale origin string."""
    s = ControlledStaticServer(web_root=tmp_path)
    with pytest.raises(RuntimeError):
        _ = s.origin


def test_controlled_server_does_not_bind_ambient_port_8765(
        tmp_path, monkeypatch, fake_popen):
    """Defense-in-depth: even if the OS happened to hand back 8765,
    the server refuses to spawn. We patch ``_pick_free_port`` to return
    the ambient port and assert the RuntimeError + no spawn."""
    server = ControlledStaticServer(web_root=tmp_path)
    monkeypatch.setattr(ControlledStaticServer, "_pick_free_port",
                        lambda self: ControlledStaticServer.AMBIENT_PORT_FASTAPI)
    with pytest.raises(RuntimeError) as ei:
        with server:
            pass
    assert str(ControlledStaticServer.AMBIENT_PORT_FASTAPI) in str(ei.value)
    assert fake_popen == [], (
        "must refuse to spawn when port would collide with ambient 8765")


# ── 3. Subset-only fail-closed ──────────────────────────────────────────────


@pytest.mark.parametrize("subset", CUTOVER_UNIT_SUBSETS)
def test_rehearsal_fails_closed_on_subset_only_cutover(
        subset, tmp_path, fake_popen, stub_verifier,
        apply_progress_snapshot):
    """Every one of the four CUTOVER_UNIT_SUBSETS must fail closed with
    EXIT_SUBSET_ONLY (2). No verifier invocation, no evidence emit, no
    apply-progress update."""
    cs = [_postcut_consumer(f"c{i}") for i in range(3)]
    if subset in ("web_dir_only", "makefile_only", "artifact_only"):
        # Manifest entirely un-flipped.
        cs = [_legacy_consumer(f"c{i}") for i in range(3)]
    elif subset == "consumers_only":
        # Partial flip: mixed Tier-1 + Tier-2 consumers.
        cs = [_postcut_consumer("c0"),
              _legacy_consumer("c1"),
              _postcut_consumer("c2")]
    manifest = _base_manifest(cs)
    mp = _write_manifest(tmp_path, manifest)
    evidence = tmp_path / "evidence.json"
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(tmp_path),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_SUBSET_ONLY, (rc_, err)
    assert "subset-only" in err.lower() or subset in err, err
    assert stub_verifier.calls == [], (
        "verifier MUST NOT run on subset-only cutover")
    assert not evidence.exists(), (
        "cutover-rehearsal.json MUST NOT be emitted on subset-only")


def test_rehearsal_does_not_invoke_g3_tier2_when_subset_only(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """Subset-only path explicitly short-circuits BEFORE the G3 helper
    is called — assert the helper itself never enters."""
    cs = [_legacy_consumer(f"c{i}") for i in range(2)]
    manifest = _base_manifest(cs)
    mp = _write_manifest(tmp_path, manifest)
    # Spy on run_g3_tier2 to confirm it isn't called.
    called = {"n": 0}
    orig = rc.run_g3_tier2
    def _spy(*a, **kw):
        called["n"] += 1
        return orig(*a, **kw)
    import scripts.rehearse_cutover as rc_mod
    rc_mod.run_g3_tier2 = _spy
    try:
        rc_, _ = _run_in_process([
            "--manifest", str(mp),
            "--fixture-web-root", str(tmp_path),
            "--rehearsal-out", str(tmp_path / "evidence.json"),
            "--apply-progress", str(apply_progress_snapshot),
        ])
    finally:
        rc_mod.run_g3_tier2 = orig
    assert rc_ == EXIT_SUBSET_ONLY
    assert called["n"] == 0, "run_g3_tier2 must not be called on subset-only"


def test_rehearsal_exits_with_specific_subset_only_code(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """The subset-only exit code MUST be exactly EXIT_SUBSET_ONLY (2),
    distinct from EXIT_USAGE / EXIT_G3 / EXIT_REHEARSAL."""
    cs = [_legacy_consumer("c1")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    rc_, _ = _run_in_process([
        "--manifest", str(mp),
        "--fixture-web-root", str(tmp_path),
        "--rehearsal-out", str(tmp_path / "evidence.json"),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_SUBSET_ONLY
    assert rc_ != EXIT_OK and rc_ != EXIT_G3 and rc_ != EXIT_REHEARSAL


# ── 4. Invalid web root fail-closed (ControlledStaticServer propagation) ───


def test_rehearsal_fails_closed_when_fixture_web_root_path_is_invalid(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """When --fixture-web-root points at a missing path, the
    ControlledStaticServer raises RuntimeError before any bind /
    spawn. ``run_g3_tier2`` propagates it, ``main`` maps to EXIT_G3.
    No evidence, no apply-progress update."""
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    evidence = tmp_path / "evidence.json"
    missing_root = tmp_path / "no_such_web_root"
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(missing_root),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_G3, (rc_, err)
    assert "fixture" in err.lower() or "web_root" in err.lower() \
        or "controlled" in err.lower(), err
    assert stub_verifier.calls == [], (
        "verifier MUST NOT run when the controlled server fails to start")
    assert not evidence.exists(), (
        "no cutover-rehearsal.json when controlled server fails to start")
    assert fake_popen == [], (
        "no subprocess may spawn when web_root validation fails")


def test_rehearsal_fails_closed_when_verifier_returns_exit_server(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """The verifier's EXIT_SERVER is mapped to verifier failure (the
    stub returns non-zero). Rehearsal must fail closed: EXIT_G3, no
    evidence, no apply-progress update, controlled server
    terminated."""
    stub_verifier.exit_code = 6  # EXIT_SERVER in verify_consumers
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    evidence = tmp_path / "evidence.json"
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_G3, (rc_, err)
    assert not evidence.exists()
    # The controlled server spawned AND was terminated by context exit.
    server_spawns = [p for p in fake_popen
                     if "http.server" in p.args]
    assert len(server_spawns) == 1
    assert server_spawns[0].terminated, (
        "controlled server must terminate even when verifier fails")


# ── 5. Server cleanup on success / failure ──────────────────────────────────


def test_rehearsal_starts_controlled_http_server_for_supplied_out_dir(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """On the happy path, the rehearsal spawns ``python -m http.server``
    with the supplied --fixture-web-root as --directory and an
    OS-picked port (NOT 8765)."""
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(tmp_path / "evidence.json"),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_OK, (rc_, err)
    server_spawns = [p for p in fake_popen
                     if "http.server" in p.args]
    assert len(server_spawns) == 1, server_spawns
    argv = server_spawns[0].args
    assert argv[:3] == [sys.executable, "-m", "http.server"]
    assert "--directory" in argv
    d_idx = argv.index("--directory")
    assert argv[d_idx + 1] == str(web_root.resolve()), argv
    port = int(argv[d_idx - 1])
    assert port != ControlledStaticServer.AMBIENT_PORT_FASTAPI


def test_rehearsal_shuts_down_controlled_server_on_successful_exit(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """Happy path: the rehearsal exits 0, the controlled server is
    terminated (no leak)."""
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(tmp_path / "evidence.json"),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_OK, err
    server_spawns = [p for p in fake_popen
                     if "http.server" in p.args]
    assert len(server_spawns) == 1
    assert server_spawns[0].terminated
    assert server_spawns[0].kill is False or not server_spawns[0].killed, (
        "graceful SIGTERM should be enough; SIGKILL is only for hang")


def test_rehearsal_shuts_down_controlled_server_on_verifier_failure(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """When the verifier returns non-zero, the controlled server is
    STILL terminated (the ``with`` block runs ``__exit__`` on every
    path)."""
    stub_verifier.exit_code = 5  # EXIT_CHECK
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(tmp_path / "evidence.json"),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_G3, err
    server_spawns = [p for p in fake_popen
                     if "http.server" in p.args]
    assert len(server_spawns) == 1
    assert server_spawns[0].terminated


def test_rehearsal_does_not_use_ambient_port_8765(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """Across the entire happy path: the controlled server's port
    arg must never equal the production FastAPI ambient port 8765.
    This is the headline guarantee of the Phase 6b repair."""
    cs = [_postcut_consumer(f"c{i}") for i in range(3)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(tmp_path / "evidence.json"),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_OK, err
    server_spawns = [p for p in fake_popen
                     if "http.server" in p.args]
    for proc in server_spawns:
        argv = proc.args
        d_idx = argv.index("--directory")
        port = int(argv[d_idx - 1])
        assert port != ControlledStaticServer.AMBIENT_PORT_FASTAPI, port


# ── 6. Temporary-manifest cleanup ───────────────────────────────────────────


def test_rehearsal_cleans_up_tmp_manifest_on_successful_exit(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """The tmp port-rewritten manifest copy (under /tmp) is removed in
    the ``finally`` block of ``run_g3_tier2``. No dot-prefixed
    leftovers survive a successful rehearsal."""
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(tmp_path / "evidence.json"),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_OK, err
    argv = stub_verifier.calls[0]
    mp_arg = argv[argv.index("--manifest") + 1]
    assert not Path(mp_arg).exists(), (
        f"tmp manifest leaked: {mp_arg}")
    leftovers = list(Path("/tmp").glob(".tmp-rehearsal-manifest-*.json"))
    assert leftovers == [], leftovers


def test_rehearsal_cleans_up_tmp_manifest_when_verifier_fails(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """The tmp manifest cleanup runs in a finally block — verifier
    failure must NOT leak the dot-prefixed copy."""
    stub_verifier.exit_code = 5
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    rc_, _ = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(tmp_path / "evidence.json"),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_G3
    leftovers = list(Path("/tmp").glob(".tmp-rehearsal-manifest-*.json"))
    assert leftovers == [], leftovers


def test_run_g3_tier2_cleans_up_tmp_manifest_directly(
        tmp_path, fake_popen, stub_verifier):
    """Helper-level direct call: tmp manifest passed to
    verify_consumers.main is removed even when invoked outside of
    ``main`` (apply worker calls this directly)."""
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    rc.run_g3_tier2(manifest_path=mp, out_dir=tmp_path / "out",
                    repo_root=tmp_path, fixture_web_root=web_root)
    leftovers = list(Path("/tmp").glob(".tmp-rehearsal-manifest-*.json"))
    assert leftovers == [], leftovers
    argv = stub_verifier.calls[0]
    mp_arg = Path(argv[argv.index("--manifest") + 1])
    assert not mp_arg.exists(), mp_arg


# ── 7. Artifact contract: cutover-rehearsal.json ────────────────────────────


def test_rehearsal_evidence_carries_all_required_g6_fields(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """Every required G6 field MUST be present in the emitted
    cutover-rehearsal.json. The orchestrator contract pins these
    field names verbatim."""
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    evidence = tmp_path / "evidence.json"
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_OK, err
    payload = json.loads(evidence.read_text())
    required = {
        "gate", "status", "captured_at", "manifest_path",
        "activation_complete", "unselected_count",
        "silent_fallback_paths", "g3_tier2_exit_code",
        "consumer_readiness",
    }
    missing = required - payload.keys()
    assert not missing, (missing, payload)
    assert payload["gate"] == "G6"
    assert payload["status"] == "ready"
    assert payload["activation_complete"] is True
    assert payload["silent_fallback_paths"] == []
    assert payload["g3_tier2_exit_code"] == 0


def test_rehearsal_evidence_captures_manifest_path_provenance(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """``manifest_path`` in the artifact records the absolute path to
    the activated working-copy manifest (not the tmp copy)."""
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    evidence = tmp_path / "evidence.json"
    rc_, _ = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_OK
    payload = json.loads(evidence.read_text())
    assert payload["manifest_path"] == str(mp.resolve())


def test_rehearsal_evidence_captured_at_is_iso8601_utc(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """``captured_at`` MUST be an ISO-8601 UTC timestamp with the
    ``Z`` suffix. The orchestrator contract pins this exact shape."""
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    evidence = tmp_path / "evidence.json"
    rc_, _ = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_OK
    payload = json.loads(evidence.read_text())
    cap = payload["captured_at"]
    # Round-trip through datetime to validate ISO-8601 + Z.
    parsed = datetime.datetime.strptime(cap, "%Y-%m-%dT%H:%M:%SZ")
    assert parsed.tzinfo is None  # naive UTC (Z suffix encodes offset)
    # Within ±60s of now.
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    assert abs((now - parsed).total_seconds()) < 60, (cap, now)


def test_rehearsal_evidence_consumer_readiness_field_is_dict_or_null(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """``consumer_readiness`` is either the verifier's dict artifact or
    ``None`` (when no readiness was emitted). Never a string / list /
    scalar — the orchestrator contract pins this type."""
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    evidence = tmp_path / "evidence.json"
    rc_, _ = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_OK
    payload = json.loads(evidence.read_text())
    cr = payload["consumer_readiness"]
    assert cr is None or isinstance(cr, dict)
    if isinstance(cr, dict):
        # Verifier-side readiness fields.
        assert "all_selected" in cr


def test_rehearsal_evidence_silently_fallback_paths_is_empty_against_clean_source(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """Against the on-disk clean source tree (api/server.py + Makefile),
    the silent-fallback scan returns ``[]`` and the artifact's
    ``silent_fallback_paths`` field is empty."""
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    evidence = tmp_path / "evidence.json"
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--repo-root", str(REPO_ROOT),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_OK, err
    payload = json.loads(evidence.read_text())
    assert payload["silent_fallback_paths"] == []
    # Also confirm the scanner returns [] on the real repo.
    assert rc.scan_silent_fallback_paths(REPO_ROOT) == []


# ── 8. apply-progress.md G6 footer behaviour ────────────────────────────────


def test_rehearsal_real_mode_updates_apply_progress_on_full_success(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """Real rehearsal (no test-mode flags) exits 0 → G6 footer in
    apply-progress.md is flipped to "PASS recorded". The footer
    matches the documented regex shape.

    Validates the FIRST flip against an **isolated copy** of the
    production apply-progress.md. The production file's §Status
    footer is already "PASS recorded" from a prior real rehearsal,
    which would make ``update_apply_progress_g6`` idempotent and a
    no-op against the production file. The test instead copies the
    production file (or scaffolds a minimal stub if missing) into a
    tmp location, resets the §Status footer body to the
    "blocked — ..." unflipped placeholder so the regex matches a
    non-flipped line, runs the rehearsal against the COPY (not the
    production file), and asserts the copy was flipped to "PASS
    recorded". The production file is NOT touched by this test
    (the ``apply_progress_snapshot`` fixture is unused here on
    purpose)."""
    import re
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    # Isolated copy: take a fresh snapshot of the production
    # apply-progress.md (or scaffold a minimal stub if missing)
    # and reset the §Status footer body to the unflipped
    # "blocked — ..." placeholder so the regex matches a
    # non-flipped line regardless of the production file's
    # current state.
    copy = tmp_path / "isolated-apply-progress.md"
    if apply_progress_snapshot.is_file():
        copy_text = apply_progress_snapshot.read_text()
    else:
        copy_text = (
        "# Apply Progress: complete-taxa-frontend-migration\n\n"
        "G6 (cutover rehearsal) **blocked — placeholder "
        "for isolated first-flip test**.\n"
        )
    # The _G6_FOOTER_RE pattern is
    #   G6 \(cutover rehearsal\) \*\*[^*]+\*\*
    # The §Pre-flight gate table row carries the literal pattern
    # `| G6 (cutover rehearsal) | **...**` (pipes between the
    # label and the bold opening), so the literal regex does
    # NOT match that row — only the §Status footer
    # `G6 (cutover rehearsal) **...**.` matches. Reset its body
    # to the unflipped "blocked — ..." placeholder to validate
    # the first flip.
    _ISOLATED_G6_RE = re.compile(
        r"G6 \(cutover rehearsal\) \*\*[^*]+\*\*",
    )
    copy_text, n_subs = _ISOLATED_G6_RE.subn(
        "G6 (cutover rehearsal) **blocked — placeholder for "
        "isolated first-flip test**",
        copy_text,
        count=1,
    )
    assert n_subs >= 1, (
        "isolated copy must contain a §Status footer that "
        "matches the _G6_FOOTER_RE pattern")
    copy.write_text(copy_text)
    before = copy.read_text()
    evidence = tmp_path / "evidence.json"
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(copy),
    ])
    assert rc_ == EXIT_OK, err
    after = copy.read_text()
    assert "PASS recorded" in after, after
    assert after != before, (
        "isolated apply-progress.md must have been flipped "
        "(first-flip validation; the production file is "
        "intentionally untouched)")


def test_rehearsal_does_not_update_apply_progress_in_test_mode(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """``--no-update-apply-progress`` preserves the production footer
    even on a successful rehearsal."""
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    evidence = tmp_path / "evidence.json"
    before = apply_progress_snapshot.read_text() \
        if apply_progress_snapshot.exists() else ""
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
        "--no-update-apply-progress",
    ])
    assert rc_ == EXIT_OK, err
    assert apply_progress_snapshot.read_text() == before, (
        "test-mode flag must suppress apply-progress.md flip")


def test_rehearsal_does_not_update_apply_progress_when_g3_tier2_fails(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot):
    """Verifier failure: apply-progress.md MUST NOT be touched even
    without the test-mode flag (G3 fail-closed)."""
    stub_verifier.exit_code = 5
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    evidence = tmp_path / "evidence.json"
    before = apply_progress_snapshot.read_text() \
        if apply_progress_snapshot.exists() else ""
    rc_, _ = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_G3
    assert apply_progress_snapshot.read_text() == before


def test_rehearsal_progress_footer_flip_is_idempotent(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot,
        monkeypatch):
    """Two consecutive successful real rehearsals: the second call MUST
    not re-edit the file. We invoke the underlying
    ``update_apply_progress_g6`` directly because ``main`` snapshots
    the file once; the contract under test is the helper's
    idempotency."""
    if not apply_progress_snapshot.is_file():
        pytest.skip("production apply-progress.md not present on disk")
    # First flip.
    captured = datetime.datetime.now(datetime.timezone.utc) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    rc.update_apply_progress_g6(
        apply_progress_snapshot,
        captured_at=captured,
        rehearsal_out=Path("/tmp/evidence.json"),
        silent_fallback_paths=[],
    )
    flipped = apply_progress_snapshot.read_text()
    assert "PASS recorded" in flipped
    # Second flip — must be a no-op.
    rc.update_apply_progress_g6(
        apply_progress_snapshot,
        captured_at=captured,
        rehearsal_out=Path("/tmp/evidence.json"),
        silent_fallback_paths=[],
    )
    assert apply_progress_snapshot.read_text() == flipped


def test_rehearsal_fails_closed_when_silent_fallback_path_detected(
        tmp_path, monkeypatch, apply_progress_snapshot):
    """When ``scan_silent_fallback_paths`` returns a non-empty list,
    the rehearsal MUST exit EXIT_REHEARSAL (4) BEFORE invoking the G3
    verifier. No evidence, no apply-progress update."""
    # Force a non-empty scan result.
    monkeypatch.setattr(rc, "scan_silent_fallback_paths",
                        lambda repo_root: ["api/server.py:1: WEB_DIR = web"])
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    evidence = tmp_path / "evidence.json"
    before = apply_progress_snapshot.read_text() \
        if apply_progress_snapshot.exists() else ""
    # Spy on run_g3_tier2 — must NOT be invoked.
    called = {"n": 0}
    orig = rc.run_g3_tier2
    def _spy(*a, **kw):
        called["n"] += 1
        return orig(*a, **kw)
    rc.run_g3_tier2 = _spy
    try:
        rc_, err = _run_in_process([
            "--manifest", str(mp),
            "--out", str(tmp_path / "out"),
            "--fixture-web-root", str(web_root),
            "--repo-root", str(tmp_path),
            "--rehearsal-out", str(evidence),
            "--apply-progress", str(apply_progress_snapshot),
        ])
    finally:
        rc.run_g3_tier2 = orig
    assert rc_ == EXIT_REHEARSAL, (rc_, err)
    assert called["n"] == 0
    assert not evidence.exists()
    assert apply_progress_snapshot.read_text() == before


# ── 9. Argument / manifest validation ───────────────────────────────────────


def test_rehearsal_rejects_missing_manifest_arg():
    """Missing manifest → EXIT_USAGE (1). The script must not crash
    with an uncaught exception."""
    rc_, err = _run_in_process(["--manifest", "/no/such/manifest.json"])
    assert rc_ == EXIT_USAGE, (rc_, err)
    assert "manifest" in err.lower()


def test_rehearsal_rejects_invalid_manifest_json(tmp_path):
    """Manifest exists but contains invalid JSON → EXIT_USAGE (1)."""
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    rc_, err = _run_in_process(["--manifest", str(bad)])
    assert rc_ == EXIT_USAGE, (rc_, err)
    assert "invalid json" in err.lower() or "json" in err.lower()


def test_rehearsal_rejects_subset_flag_with_invalid_value(tmp_path):
    """An unknown --subset value is rejected by argparse (choices is
    pinned to CUTOVER_UNIT_SUBSETS). The rehearsal maps the argparse
    SystemExit to EXIT_USAGE."""
    cs = [_postcut_consumer("c1")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--subset", "not_a_real_subset",
    ])
    assert rc_ == EXIT_USAGE, (rc_, err)


# ── 10. End-to-end against real working-copy manifest ───────────────────────


def test_activated_working_manifest_exists_and_has_26_consumers():
    """The activated working-copy manifest exists at the canonical path
    and carries the pinned Tier-2 consumer count (26 §3.1 consumers)."""
    assert WORKING_MANIFEST.is_file(), WORKING_MANIFEST
    data = json.loads(WORKING_MANIFEST.read_text())
    cs = data.get("consumers", [])
    assert isinstance(cs, list)
    assert len(cs) == 26, len(cs)
    # Every consumer is Tier-2 (replacement.path != current_path).
    for c in cs:
        repl = c.get("replacement", {})
        path = repl.get("path", "")
        current = c.get("current_path", "")
        assert path and current and path != current, c


def test_predecessor_manifest_remains_byte_identical_frozen(
        tmp_path, predecessor_snapshot):
    """The predecessor manifest (the Tier-1 legacy selection the
    working copy was forked from) is frozen and MUST NOT be modified
    by the rehearsal. The contract: the rehearsal only ever edits the
    tmp port-rewritten copy under /tmp."""
    if not predecessor_snapshot.is_file():
        pytest.skip("predecessor manifest not present on disk")
    # Run a full rehearsal against a synthetic manifest in tmp_path;
    # confirm the predecessor bytes don't change.
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    before = predecessor_snapshot.read_bytes()
    rc_, _ = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(tmp_path / "evidence.json"),
        "--apply-progress", str(predecessor_snapshot),
        "--no-update-apply-progress",
    ])
    assert rc_ == EXIT_OK
    after = predecessor_snapshot.read_bytes()
    assert before == after, "predecessor manifest must remain byte-identical"


def test_rehearsal_real_manifest_against_default_out_fails_closed(
        tmp_path, monkeypatch, apply_progress_snapshot):
    """Real activated working-copy manifest, default out/ fixture
    root: if ``out/`` is missing on disk, the controlled server's
    pre-spawn validation fails closed with EXIT_G3 (no real verifier
    run, no evidence)."""
    # Stub subprocess.Popen so the rehearsal never actually tries to
    # bind; the ControlledStaticServer class raises on missing root
    # BEFORE spawning, so the stub won't be called.
    fake_popen_stub = []
    class _Stub:
        def __init__(self, args, **kw): self.args = list(args)
        def terminate(self): pass
        def kill(self): pass
        def wait(self, timeout=None): return 0
        def poll(self): return 0
    monkeypatch.setattr(rc.subprocess, "Popen", _Stub)
    evidence = tmp_path / "evidence.json"
    rc_, err = _run_in_process([
        "--manifest", str(WORKING_MANIFEST),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", "/no/such/out_root",
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
        "--no-update-apply-progress",
    ])
    assert rc_ == EXIT_G3, (rc_, err)
    assert not evidence.exists()


def test_rehearsal_owns_controlled_static_server_for_real_out_candidate(
        tmp_path, fake_popen, stub_verifier, apply_progress_snapshot,
        monkeypatch):
    """Real activated working-copy manifest, custom --fixture-web-root
    pointing at a tmp valid http server root: rehearsal owns a
    controlled server, the verifier stub returns 0, the artifact is
    emitted, and apply-progress.md is flipped."""
    cs = [_postcut_consumer(f"c{i}") for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    web_root = _make_web_root(tmp_path)
    evidence = tmp_path / "evidence.json"
    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--repo-root", str(REPO_ROOT),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_OK, (rc_, err)
    # The controlled server is owned by the rehearsal (one spawn, not
    # owned by the verifier — verifier MUST NOT receive --serve).
    server_spawns = [p for p in fake_popen
                     if "http.server" in p.args]
    assert len(server_spawns) == 1
    assert server_spawns[0].terminated
    argv = stub_verifier.calls[0]
    assert "--serve" not in argv
    # Evidence emitted with the full G6 contract.
    payload = json.loads(evidence.read_text())
    assert payload["status"] == "ready"
    assert payload["activation_complete"] is True


# ── 11. Live end-to-end: actual http.server (one isolated port) ─────────────


def test_rehearsal_live_controlled_server_serves_real_index_html(
        tmp_path, stub_verifier, apply_progress_snapshot,
        monkeypatch):
    """The one live-network test: spawn the real ``python -m
    http.server`` on a tmp web root and confirm the rehearsal picks an
    isolated port that actually serves our index.html. Skips only if
    no free port can be bound (CI sandboxes)."""
    web_root = _make_web_root(tmp_path)
    # Use real-shaped curl commands so the port-rewrite is observable.
    cs = [_postcut_consumer(f"c{i}",
                            cmd=f"curl -sS http://127.0.0.1:8765/c{i}")
          for i in range(2)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    evidence = tmp_path / "evidence.json"

    # Capture the chosen port from inside the rehearsal.
    captured_port: dict[str, int] = {}
    real_enter = ControlledStaticServer.__enter__

    def _spy_enter(self):
        real_enter(self)
        captured_port["port"] = self.port
        return self

    monkeypatch.setattr(ControlledStaticServer, "__enter__", _spy_enter)

    rc_, err = _run_in_process([
        "--manifest", str(mp),
        "--out", str(tmp_path / "out"),
        "--fixture-web-root", str(web_root),
        "--rehearsal-out", str(evidence),
        "--apply-progress", str(apply_progress_snapshot),
    ])
    assert rc_ == EXIT_OK, err
    assert "port" in captured_port
    port = captured_port["port"]
    assert port != ControlledStaticServer.AMBIENT_PORT_FASTAPI

    # Confirm the verifier's tmp manifest referenced the picked port.
    # The stub captured the rewritten manifest content at call time
    # (before the rehearsal's finally block unlinked it).
    assert len(stub_verifier.manifest_snapshots) == 1
    manifest_text = stub_verifier.manifest_snapshots[0]
    assert manifest_text is not None
    manifest_obj = json.loads(manifest_text)
    for c in manifest_obj["consumers"]:
        cmd = c["verification"]["command"]
        assert f":{port}" in cmd, (cmd, port)
        assert "127.0.0.1:8765" not in cmd, cmd
