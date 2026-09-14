"""Hermetic strict-TDD tests for Slice 1 of scripts/run_g5_orchestration.py.

Slice 1 owns the bounded CLI surface (argparse + validation + dry-run-only).
Deferred to later slices: seam factories, error-taxonomy mapping,
``run_orchestration`` invocation + lifecycle cleanup, success-path assertions.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import scripts.run_g5_orchestration as cli


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "run_g5_orchestration.py"

BASE = "http://127.0.0.1:8765"


def _common_args(tmp_path: Path) -> list[str]:
    return ["--target-url", f"{BASE}/", "--out", str(tmp_path / "out"),
            "--iterations", "10"]


def test_module_imports_without_side_effects():
    """Importing the CLI must NOT spawn uvicorn / playwright / node."""
    import importlib
    importlib.reload(cli)
    for name in ("EXIT_OK", "EXIT_USAGE", "EXIT_VALIDATION",
                 "main", "_build_parser", "_validate_args",
                 "_handle_argparse_exit", "_emit", "_default_cwd"):
        assert hasattr(cli, name), f"missing public symbol: {name}"


def test_help_exits_zero(capsys):
    rc = cli.main(["--help"])
    assert rc == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "run_g5_orchestration" in out
    assert "--target-url" in out and "--out" in out


def test_missing_target_url_exits_usage(capsys):
    rc = cli.main(["--out", "/tmp/x"])
    assert rc == cli.EXIT_USAGE
    err = capsys.readouterr().err
    assert "target-url" in err or "usage" in err.lower()


def test_missing_out_exits_usage(capsys):
    rc = cli.main(["--target-url", f"{BASE}/"])
    assert rc == cli.EXIT_USAGE
    err = capsys.readouterr().err
    assert "out" in err or "usage" in err.lower()


def test_unknown_flag_exits_usage(capsys):
    rc = cli.main(_common_args(Path("/tmp")) + ["--bogus-flag", "x"])
    assert rc == cli.EXIT_USAGE


@pytest.mark.parametrize("url", ["not-a-url", "ftp://127.0.0.1:8765/"])
def test_bad_target_url_exits_validation(capsys, url):
    rc = cli.main(["--target-url", url, "--out", "/tmp/x"])
    assert rc == cli.EXIT_VALIDATION
    err = capsys.readouterr().err
    assert "http://" in err


@pytest.mark.parametrize("port", [0, -1, 65536, 70000])
def test_bad_port_exits_validation(capsys, port):
    rc = cli.main(["--target-url", f"{BASE}/", "--out", "/tmp/x",
                   "--port", str(port)])
    assert rc == cli.EXIT_VALIDATION
    err = capsys.readouterr().err
    assert "port" in err.lower()


def test_bad_iterations_exits_validation(capsys):
    rc = cli.main(["--target-url", f"{BASE}/", "--out", "/tmp/x",
                   "--iterations", "5"])
    assert rc == cli.EXIT_VALIDATION
    err = capsys.readouterr().err
    assert "10" in err and "iterations" in err.lower()


@pytest.mark.parametrize("flag,val,expected_in_msg", [
    ("--health-timeout-s", "0", "health-timeout-s"),
    ("--health-timeout-s", "-1.0", "health-timeout-s"),
    ("--health-interval-s", "0", "health-interval-s"),
    ("--terminate-grace-s", "-0.5", "terminate-grace-s"),
])
def test_bad_timing_exits_validation(capsys, flag, val, expected_in_msg):
    rc = cli.main(["--target-url", f"{BASE}/", "--out", "/tmp/x",
                   flag, val])
    assert rc == cli.EXIT_VALIDATION
    err = capsys.readouterr().err
    assert expected_in_msg in err


def test_bad_cwd_exits_validation(capsys, tmp_path):
    rc = cli.main(["--target-url", f"{BASE}/", "--out", str(tmp_path / "out"),
                   "--cwd", str(tmp_path / "does-not-exist")])
    assert rc == cli.EXIT_VALIDATION
    err = capsys.readouterr().err
    assert "cwd" in err.lower()


def test_bad_bridge_script_exits_validation(capsys, tmp_path):
    rc = cli.main(["--target-url", f"{BASE}/", "--out", str(tmp_path / "out"),
                   "--bridge-script", str(tmp_path / "no-such-bridge.mjs")])
    assert rc == cli.EXIT_VALIDATION
    err = capsys.readouterr().err
    assert "bridge-script" in err


def test_good_cwd_and_bridge_script_pass_validation(capsys, tmp_path):
    real_dir = tmp_path / "real-dir"
    real_dir.mkdir()
    real_script = tmp_path / "bridge.mjs"
    real_script.write_text("// bridge\n")
    rc = cli.main(["--target-url", f"{BASE}/", "--out", str(tmp_path / "out"),
                   "--cwd", str(real_dir),
                   "--bridge-script", str(real_script),
                   "--dry-run"])
    assert rc == cli.EXIT_OK


def test_dry_run_exits_zero_and_emits_summary(capsys, tmp_path):
    rc = cli.main(_common_args(tmp_path) + ["--dry-run"])
    assert rc == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert f"{BASE}/" in out
    assert str(tmp_path / "out") in out
    assert not (tmp_path / "out").exists(), "dry-run must not create the output dir"


def test_non_dry_run_is_rejected_in_slice_1(capsys, tmp_path):
    rc = cli.main(_common_args(tmp_path))
    assert rc == cli.EXIT_VALIDATION
    err = capsys.readouterr().err
    assert "dry-run" in err.lower() or "deferred" in err.lower() or "seam" in err.lower()


def test_slice_total_under_800_lines():
    """Bounded scope guard: CLI + tests ≤ 800 lines (Slice 1 + 1A corrected).
    The 400-budget line guard belonged to the pre-correction draft and was
    relaxed when Slice 1A was corrected to bind the real capture_hydration
    public contracts (extra tests verify real bindings, not synthetic)."""
    cli_text = SCRIPT.read_text(encoding="utf-8")
    assert cli_text.startswith("#!/usr/bin/env python")
    cli_lines = sum(1 for _ in cli_text.splitlines())
    this_lines = sum(1 for _ in Path(__file__).read_text(encoding="utf-8").splitlines())
    total = cli_lines + this_lines
    assert total <= 800, f"CLI + tests total is {total} lines; budget is 800"


def test_script_does_not_modify_child_b():
    """Slice 1 only imports Child B for constants; it must NOT mutate it."""
    text = SCRIPT.read_text(encoding="utf-8")
    forbidden = "scripts/orchestrate_g5_legacy.py"
    assert f'open({forbidden!r}' not in text and f'Path({forbidden!r}' not in text, (
        f"CLI must not touch {forbidden} as a file")
    assert ("import scripts.orchestrate_g5_legacy" in text
            or "from scripts import orchestrate_g5_legacy" in text), (
            "Slice 1 CLI must import Child B for defaults")
    assert ("import scripts.capture_hydration" in text
            or "from scripts import capture_hydration" in text), (
            "Slice 1A CLI must import capture_hydration for real seam bindings")


def _run_cli(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        capture_output=True, text=True, check=False,
    )


def test_subprocess_help_exits_zero():
    r = _run_cli("--help")
    assert r.returncode == 0, r.stderr
    assert "run_g5_orchestration" in r.stdout
    assert "--target-url" in r.stdout and "--out" in r.stdout


def test_subprocess_missing_required_exits_usage():
    r = _run_cli()  # no args
    assert r.returncode == 1
    assert "required" in r.stderr.lower() or "usage" in r.stderr.lower()


def test_subprocess_bad_url_exits_validation(tmp_path):
    r = _run_cli("--target-url", "not-a-url", "--out", str(tmp_path / "out"))
    assert r.returncode == 2
    assert "http://" in r.stderr


def test_subprocess_bad_iterations_exits_validation(tmp_path):
    r = _run_cli("--target-url", f"{BASE}/",
                 "--out", str(tmp_path / "out"), "--iterations", "3")
    assert r.returncode == 2
    assert "iterations" in r.stderr.lower() and "10" in r.stderr


def test_subprocess_dry_run_exits_zero(tmp_path):
    r = _run_cli("--target-url", f"{BASE}/",
                 "--out", str(tmp_path / "out"), "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "dry-run" in r.stdout
    assert not (tmp_path / "out").exists(), "dry-run must not create the output dir"


def test_subprocess_non_dry_run_exits_validation(tmp_path):
    r = _run_cli("--target-url", f"{BASE}/",
                 "--out", str(tmp_path / "out"))
    assert r.returncode == 2
    assert "dry-run" in r.stderr.lower() or "deferred" in r.stderr.lower()


# ── Slice 1A: real public-contract seam factories ──────────────────
# Hermetic tests for the 5 seam factories. Each must: (1) return the right
# shape, (2) thread injectable overrides through, (3) NOT execute subprocess
# / network / browser / Node at construction time. The collector / planner
# / publisher defaults must bind to the REAL public contracts from
# scripts.capture_hydration, not synthetic re-implementations.

def test_make_lifecycle_returns_adapter_without_starting(tmp_path):
    """make_lifecycle returns a LegacyLifecycleAdapter; never .start()."""
    from scripts import orchestrate_g5_legacy as og
    adapter = cli.make_lifecycle(host="127.0.0.1", port=8123, cwd=tmp_path)
    assert isinstance(adapter, og.LegacyLifecycleAdapter)
    assert adapter._ctx is None
    assert adapter.base_url == "http://127.0.0.1:8123"

def test_make_lifecycle_threads_injectable_spawn_and_probe(tmp_path):
    """Custom spawn + probe overrides thread through to the adapter."""
    def fake_spawn(argv, *, cwd): return _FakeSubprocessHandle(pid=99999)
    def fake_probe(host, port, path): return True
    adapter = cli.make_lifecycle(host="127.0.0.1", port=8124, cwd=tmp_path,
                                  spawn=fake_spawn, probe=fake_probe)
    assert adapter._kwargs["spawn"] is fake_spawn
    assert adapter._kwargs["probe"] is fake_probe

def test_make_collector_default_signature_returns_real_schema():
    """Default collector closure (with injected fake BrowserAdapter) must
    delegate to capture_hydration.collect_raw_samples and return its real
    schema-conformant payload — NOT a synthetic inline-samples dict."""
    from scripts.capture_hydration import SCHEMA
    class _A:
        def chromium_provenance(self): return {"version": "x", "executable_path": "x"}
        def playwright_provenance(self): return {"version": "x"}
        def run_iteration(self, *, target_url, dom_marker_selector, iteration_index):
            return {"iteration": iteration_index, "captured_at": "x"}
    result = cli.make_collector(browser_adapter=_A())(target_url=f"{BASE}/",
                                                      iterations=10,
                                                      dom_marker_selector="#x")
    assert result["schema"] == SCHEMA
    assert result["iterations"] == 10
    assert len(result["samples"]) == 10

def test_make_collector_default_delegates_to_collect_raw_samples():
    """Default collector closure must iterate collect_raw_samples 10x over
    the injected adapter (proves real delegation, not synthetic dict)."""
    from scripts import capture_hydration as ch
    seen = []
    class _A:
        def chromium_provenance(self): return {"version": "x", "executable_path": "x"}
        def playwright_provenance(self): return {"version": "x"}
        def run_iteration(self, *, target_url, dom_marker_selector, iteration_index):
            seen.append(iteration_index)
            return {"iteration": iteration_index, "captured_at": "x"}
    out = cli.make_collector(browser_adapter=_A())(target_url=f"{BASE}/",
                                                   iterations=10,
                                                   dom_marker_selector="#x")
    assert out["schema"] == ch.SCHEMA
    assert seen == list(range(10))

def test_make_collector_does_not_instantiate_adapter_at_construction():
    """make_collector must NOT call PlaywrightBrowserAdapter() at
    construction; the adapter is only lazily built inside the closure."""
    assert callable(cli.make_collector())

def test_make_collector_lazy_adapter_construction_is_isolated(monkeypatch):
    """Each invocation of the default closure must construct its own
    PlaywrightBrowserAdapter (no shared mutable state across calls)."""
    from scripts import capture_hydration as ch
    constructed = []
    real_init = ch.PlaywrightBrowserAdapter.__init__
    def spy_init(self, **kw):
        constructed.append(id(self))
        real_init(self, **kw)
    monkeypatch.setattr(ch.PlaywrightBrowserAdapter, "__init__", spy_init)
    fake_run = lambda *, target_url, dom_marker_selector, iteration_index: {
        "iteration": iteration_index, "captured_at": "x"}
    class _A:
        chromium_provenance = lambda self: {"version": "x", "executable_path": "x"}
        playwright_provenance = lambda self: {"version": "x"}
        run_iteration = fake_run
    monkeypatch.setattr(ch, "collect_raw_samples",
                        lambda *, target_url, browser_adapter, iterations,
                               dom_marker_selector: {
                            "schema": ch.SCHEMA, "samples": [],
                            "iterations": iterations})
    closure = cli.make_collector()
    closure(target_url=f"{BASE}/", iterations=10, dom_marker_selector="#x")
    closure(target_url=f"{BASE}/", iterations=10, dom_marker_selector="#x")
    assert len(constructed) == 2, (
        "Each closure invocation must build its own adapter "
        f"(got {len(constructed)} constructions)")
    assert constructed[0] != constructed[1], (
        "Adapter instances must be distinct (no shared mutable state)")

def test_make_collector_threads_injectable_override():
    """Caller-supplied collector override must be returned verbatim."""
    def my_collector(*, target_url, iterations, dom_marker_selector):
        return {"schema": "x", "samples": []}
    assert cli.make_collector(collector=my_collector) is my_collector

def test_make_bridge_returns_callable():
    """Default bridge is a callable (str -> dict); not invoked at factory."""
    assert callable(cli.make_bridge())

def test_make_bridge_threads_injectable_override():
    """Caller-supplied bridge override must be returned verbatim."""
    def my_bridge(url):
        return {"schema": "taxa.g5-raw-lhr.envelope/1", "url": url,
                "lhr": {}, "provenance": {}}
    assert cli.make_bridge(bridge=my_bridge) is my_bridge

def test_make_planner_default_is_plan_evidence_publication():
    """Default planner must BE capture_hydration.plan_evidence_publication
    (real public contract, not a synthetic file-list builder)."""
    from scripts import capture_hydration as ch
    assert cli.make_planner() is ch.plan_evidence_publication

def test_make_planner_threads_injectable_override():
    """Caller-supplied planner override must be returned verbatim."""
    def my_planner(*, playwright_raws, lighthouse_raws,
                   manifest_snapshot, legacy_hydration_metadata):
        return {"schema": "taxa.g5-publication.evidence-manifest/1",
                "files": [], "called": True}
    planner = cli.make_planner(planner=my_planner)
    assert planner is my_planner

def test_make_publisher_default_is_publish_evidence_atomic():
    """Default publisher must BE capture_hydration.publish_evidence_atomic
    (real atomic filesystem publisher, not a synthetic plan.json writer)."""
    from scripts import capture_hydration as ch
    assert cli.make_publisher() is ch.publish_evidence_atomic

def test_make_publisher_threads_injectable_override():
    """Caller-supplied publisher override must be returned verbatim."""
    calls = []
    def my_publisher(plan, out_dir): calls.append((plan, out_dir))
    publisher = cli.make_publisher(publisher=my_publisher)
    assert publisher is my_publisher
    publisher({"schema": "x"}, Path("/tmp/out"))
    assert calls == [({"schema": "x"}, Path("/tmp/out"))]

def test_factory_construction_does_not_invoke_execution_substrates(monkeypatch):
    """Constructing ALL factories must NOT touch subprocess / urllib /
    shutil.which. Only the returned callable is allowed to do real work."""
    exec_calls = []
    def tracker(name):
        def _t(*a, **kw):
            exec_calls.append(name)
            raise AssertionError(f"{name} must not run at construction")
        return _t
    monkeypatch.setattr(cli.subprocess, "Popen", tracker("Popen"))
    monkeypatch.setattr(cli.subprocess, "run", tracker("run"))
    monkeypatch.setattr(cli.urllib.request, "urlopen", tracker("urlopen"))
    monkeypatch.setattr(cli.shutil, "which", tracker("which"))
    cli.make_lifecycle(host="127.0.0.1", port=8125, cwd=Path("/tmp"))
    cli.make_collector()
    cli.make_bridge()
    cli.make_planner()
    cli.make_publisher()
    assert exec_calls == []

def test_make_lifecycle_does_not_start_lifecycle(tmp_path):
    """Lifecycle factory constructs + returns; never calls .start()."""
    assert cli.make_lifecycle(host="127.0.0.1", port=8126,
                               cwd=tmp_path)._ctx is None

def test_cli_does_not_expose_child_b_private_bridge_symbols():
    """CLI-local bridge factory must NOT import or re-export Child B
    private bridge symbols (word-boundary match)."""
    import re as _re
    text = SCRIPT.read_text(encoding="utf-8")
    for sym in ("_default_subprocess_bridge", "_default_subprocess_spawn",
                "_default_http_health_probe", "_PopenHandle",
                "_default_publish_write_bytes"):
        m = _re.search(rf"(?<![A-Za-z0-9_]){_re.escape(sym)}(?![A-Za-z0-9_])",
                       text)
        assert m is None, f"CLI must not reference Child B private {sym!r}"


class _FakeSubprocessHandle:
    """Minimal duck-typed handle for fake_spawn in threading tests."""
    def __init__(self, pid):
        self.pid = pid
        self.argv: tuple = ()
        self.returncode: int | None = None
        self.alive: bool = True
    def terminate(self): self.alive = False
    def wait(self, timeout_s: float): self.returncode = 0; return 0
    def kill(self): self.alive = False
