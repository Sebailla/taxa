"""Hermetic strict-TDD tests for the bounded G5 orchestration CLI
(``scripts/run_g5_orchestration.py``). Slice 12 adapts commit ``7f01b9a``
onto current develop (Slices 1–11 ship lifecycle + orchestration entry +
default raw-Lighthouse bridge). ``--dry-run`` is preserved verbatim; the
deferred non-dry-run branch is fulfilled via a module-level
``build_default_seams`` factory that tests fully override.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import scripts.run_g5_orchestration as cli
import scripts.orchestrate_g5_legacy as og


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "run_g5_orchestration.py"
BASE = "http://127.0.0.1:8765"


# ── fakes ───────────────────────────────────────────────────────────────
class _FakeLC:
    def __init__(self):
        self.start_calls = self.stop_calls = 0
        self.base_url = BASE
    def start(self):
        self.start_calls += 1
    def stop(self):
        self.stop_calls += 1


def _collector(samples=None):
    def f(*, target_url, iterations, dom_marker_selector):
        s = list(samples) if samples else [{
            "iteration": i, "captured_at": "t0",
            "navigation": {"response_start_ms": 0.0,
                            "dom_content_loaded_ms": 10.0 + i,
                            "load_event_ms": 20.0 + i,
                            "redirect_count": 0, "status": 200},
            "paint": {"first_paint_ms": 5.0 + i,
                       "first_contentful_paint_ms": 6.0 + i},
            "dom_marker": {"selector": "#x", "found": True, "count": 1,
                            "first_text": "r", "wait_ms": 1.0 + i},
            "console": []} for i in range(iterations)]
        return {"schema": "taxa.g5-capture.legacy/1", "captured_at": "t0",
                "target_url": target_url, "iterations": iterations,
                "dom_marker_selector": dom_marker_selector,
                "provenance": {"schema": "taxa.g5-capture.legacy-provenance/1"},
                "samples": s}
    return f


def _bridge(envelopes=None):
    log: list = []
    pool = envelopes or [{"schema": "taxa.g5-raw-lhr.envelope/1",
        "lhr": {"lighthouseVersion": "12.2.1", "finalUrl": "",
                "userAgent": "x", "fetchTime": "t0", "runWarnings": [],
                "categories": {"performance": {"score": 0.9}}, "audits": {}},
        "provenance": {"schema": "g4-prov/1", "lighthouseVersion": "12.2.1",
                        "chromeVersion": "x", "nodeVersion": "v0"}}]
    def f(url):
        env = pool[min(len(log), len(pool) - 1)]
        log.append(url)
        return dict(env, url=url)
    return f


def _planner(captured=None):
    def f(*, playwright_raws, lighthouse_raws, manifest_snapshot,
            legacy_hydration_metadata):
        if captured is not None:
            captured.update(pw=len(playwright_raws), lh=len(lighthouse_raws))
        return {"schema": "taxa.g5-publication.evidence-manifest/1",
                "files": [{"kind": "playwright",
                            "path": f"raw/playwright/iter-{i:02d}.json",
                            "bytes": 1, "sha256": "0" * 64,
                            "canonical_json": "{}", "iteration": i}
                           for i in range(10)]}
    return f


def _publisher(captured=None):
    def f(plan, out_dir):
        if captured is not None:
            captured.update(plan_schema=plan.get("schema"),
                             out_dir=str(out_dir))
    return f


def _inject(monkeypatch, *, lc=None, coll=None, br=None, pl=None, pub=None,
             build_raises=None, pl_captured=None, pub_captured=None):
    def fake_builder(args):
        if build_raises is not None:
            raise build_raises
        return {"lifecycle": lc or _FakeLC(),
                "collector": coll or _collector(),
                "bridge": br or _bridge(),
                "planner": pl or _planner(captured=pl_captured),
                "publisher": pub or _publisher(captured=pub_captured)}
    monkeypatch.setattr(cli, "build_default_seams", fake_builder)


# ── surface / dry-run / parse / validate (preserved from 7f01b9a) ───────
def test_module_surface():
    import importlib
    importlib.reload(cli)
    for n in ("EXIT_OK", "EXIT_USAGE", "EXIT_VALIDATION", "EXIT_RUNTIME",
              "main", "build_default_seams"):
        assert hasattr(cli, n)


def test_help_exits_zero(capsys):
    assert cli.main(["--help"]) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "--target-url" in out and "--out" in out


@pytest.mark.parametrize("argv", [
    ["--out", "/tmp/x"], ["--target-url", BASE + "/"], []])
def test_missing_required_exits_usage(argv):
    assert cli.main(argv) == cli.EXIT_USAGE


@pytest.mark.parametrize("argv", [
    ["--target-url", "not-a-url", "--out", "/tmp/x"],
    ["--target-url", "ftp://127.0.0.1:8765/", "--out", "/tmp/x"],
    ["--target-url", BASE + "/", "--out", "/tmp/x", "--port", "0"],
    ["--target-url", BASE + "/", "--out", "/tmp/x", "--port", "65536"],
    ["--target-url", BASE + "/", "--out", "/tmp/x", "--iterations", "5"],
    ["--target-url", BASE + "/", "--out", "/tmp/x", "--health-timeout-s", "0"],
    ["--target-url", BASE + "/", "--out", "/tmp/x", "--terminate-grace-s", "-1"],
])
def test_validation_failures_exit_validation(argv, tmp_path):
    argv = [a if a != "/tmp/x" else str(tmp_path / "x") for a in argv]
    assert cli.main(argv) == cli.EXIT_VALIDATION


def test_bad_paths_exit_validation(capsys, tmp_path):
    a = cli.main(["--target-url", BASE + "/", "--out", str(tmp_path / "o"),
                   "--cwd", str(tmp_path / "nope")])
    b = cli.main(["--target-url", BASE + "/", "--out", str(tmp_path / "o"),
                   "--bridge-script", str(tmp_path / "no-bridge.mjs")])
    assert a == b == cli.EXIT_VALIDATION


def test_dry_run_exits_zero_without_side_effects(capsys, tmp_path):
    rc = cli.main(["--target-url", BASE + "/",
                   "--out", str(tmp_path / "out"),
                   "--iterations", "10", "--dry-run"])
    assert rc == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "dry-run" in out and BASE + "/" in out
    assert not (tmp_path / "out").exists()


# ── Slice-12 additions: real invocation via injected seams ───────────────
def test_non_dry_run_invokes_run_orchestration_with_injected_seams(
        capsys, tmp_path, monkeypatch):
    lc = _FakeLC()
    pub, pl = {}, {}
    _inject(monkeypatch, lc=lc, pl=_planner(captured=pl),
             pub=_publisher(captured=pub))
    rc = cli.main(["--target-url", BASE + "/",
                   "--out", str(tmp_path / "out"), "--iterations", "10"])
    assert rc == cli.EXIT_OK
    assert lc.start_calls == 1 and lc.stop_calls == 1
    assert pl == {"pw": 10, "lh": 10}
    assert pub["plan_schema"] == "taxa.g5-publication.evidence-manifest/1"
    assert "OK:" in capsys.readouterr().out


def test_orchestration_error_maps_to_runtime_exit(capsys, tmp_path, monkeypatch):
    def raising_planner(**kw):
        raise og.OrchestrationError("planner boom")
    _inject(monkeypatch, pl=raising_planner)
    rc = cli.main(["--target-url", BASE + "/",
                   "--out", str(tmp_path / "out"), "--iterations", "10"])
    assert rc == cli.EXIT_RUNTIME
    assert "planner boom" in capsys.readouterr().err


def test_seam_factory_failure_maps_to_runtime_exit(capsys, tmp_path, monkeypatch):
    _inject(monkeypatch, build_raises=RuntimeError("'node' binary not found"))
    rc = cli.main(["--target-url", BASE + "/",
                   "--out", str(tmp_path / "out"), "--iterations", "10"])
    assert rc == cli.EXIT_RUNTIME
    assert "node" in capsys.readouterr().err


# ── budget guard + subprocess smoke (no real subprocess/browser/network) ─
def test_slice_total_under_800_lines():
    """Bounded scope guard: CLI + tests ≤ 800 lines (Slice 12 + 13).
    The 400-budget guard belonged to the pre-correction Slice 1 draft and
    was relaxed when Slice 1A (source commit 9c8219b) introduced real
    capture_hydration public contracts (extra tests verify real bindings,
    not synthetic re-implementations). Slice 13 adapts the wiring onto
    current develop (Slices 1–12) which already had inline seam wiring."""
    cli_text = SCRIPT.read_text(encoding="utf-8")
    assert cli_text.startswith("#!/usr/bin/env python")
    cli_lines = sum(1 for _ in cli_text.splitlines())
    this_lines = sum(1 for _ in Path(__file__).read_text(encoding="utf-8").splitlines())
    assert cli_lines + this_lines <= 800, (
f"CLI + tests total is {cli_lines + this_lines} lines; budget is 800")


def _sub(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *argv],
                           capture_output=True, text=True, check=False)


def test_subprocess_help_exits_zero():
    r = _sub("--help")
    assert r.returncode == 0 and "run_g5_orchestration" in r.stdout


def test_subprocess_dry_run_exits_zero_without_side_effects(tmp_path):
        r = _sub("--target-url", BASE + "/", "--out", str(tmp_path / "out"),
                 "--dry-run")
        assert r.returncode == 0, r.stderr
        assert "dry-run" in r.stdout
        assert not (tmp_path / "out").exists()


# ── Slice 13: seam factories (CLI-local, public) ────────────────────────
# Each factory must: (1) return the right shape, (2) thread injectable
# overrides through, (3) NOT spawn / probe / browse / run-Node at
# construction time. The bridge default must be CLI-local (no Child B
# private symbol reach-through); collector / planner / publisher defaults
# must bind to REAL capture_hydration public contracts.

class _FakeSubprocessHandle:
    """Minimal duck-typed handle for fake_spawn in threading tests."""
    def __init__(self, pid):
        self.pid = pid
        self.argv: tuple = ()
        self.returncode: int | None = None
        self.alive: bool = True
    def terminate(self):
        self.alive = False
    def wait(self, timeout_s: float):
        self.returncode = 0
        return 0
    def kill(self):
        self.alive = False


def test_make_lifecycle_returns_adapter_without_starting(tmp_path):
    adapter = cli.make_lifecycle(host="127.0.0.1", port=8123, cwd=tmp_path)
    assert isinstance(adapter, og.LegacyLifecycleAdapter)
    assert adapter._ctx is None
    assert adapter.base_url == "http://127.0.0.1:8123"


def test_make_lifecycle_threads_injectable_spawn_and_probe(tmp_path):
    def fake_spawn(argv, *, cwd):
        return _FakeSubprocessHandle(pid=99999)
    def fake_probe(host, port, path):
        return True
    adapter = cli.make_lifecycle(host="127.0.0.1", port=8124, cwd=tmp_path,
                                  spawn=fake_spawn, probe=fake_probe)
    assert adapter._kwargs["spawn"] is fake_spawn
    assert adapter._kwargs["probe"] is fake_probe


def test_make_collector_default_signature_returns_real_schema():
    from scripts.capture_hydration import SCHEMA

    class _A:
        def chromium_provenance(self):
            return {"version": "x", "executable_path": "x"}
        def playwright_provenance(self):
            return {"version": "x"}
        def run_iteration(self, *, target_url, dom_marker_selector,
                          iteration_index):
            return {"iteration": iteration_index, "captured_at": "x"}

    result = cli.make_collector(browser_adapter=_A())(target_url=f"{BASE}/",
                                                      iterations=10,
                                                      dom_marker_selector="#x")
    assert result["schema"] == SCHEMA
    assert result["iterations"] == 10
    assert len(result["samples"]) == 10


def test_make_collector_default_delegates_to_collect_raw_samples():
    from scripts import capture_hydration as ch
    seen = []

    class _A:
        def chromium_provenance(self):
            return {"version": "x", "executable_path": "x"}
        def playwright_provenance(self):
            return {"version": "x"}
        def run_iteration(self, *, target_url, dom_marker_selector,
                          iteration_index):
            seen.append(iteration_index)
            return {"iteration": iteration_index, "captured_at": "x"}

    out = cli.make_collector(browser_adapter=_A())(target_url=f"{BASE}/",
                                                   iterations=10,
                                                   dom_marker_selector="#x")
    assert out["schema"] == ch.SCHEMA
    assert seen == list(range(10))


def test_make_collector_does_not_instantiate_adapter_at_construction():
    assert callable(cli.make_collector())


def test_make_collector_threads_injectable_override():
    def my_collector(*, target_url, iterations, dom_marker_selector):
        return {"schema": "x", "samples": []}
    assert cli.make_collector(collector=my_collector) is my_collector


def test_make_bridge_returns_callable():
    assert callable(cli.make_bridge())


def test_make_bridge_threads_injectable_override():
    def my_bridge(url):
        return {"schema": "taxa.g5-raw-lhr.envelope/1", "url": url,
                "lhr": {}, "provenance": {}}
    assert cli.make_bridge(bridge=my_bridge) is my_bridge


def test_make_planner_default_is_plan_evidence_publication():
    from scripts import capture_hydration as ch
    assert cli.make_planner() is ch.plan_evidence_publication


def test_make_planner_threads_injectable_override():
    def my_planner(*, playwright_raws, lighthouse_raws,
                   manifest_snapshot, legacy_hydration_metadata):
        return {"schema": "taxa.g5-publication.evidence-manifest/1",
                "files": [], "called": True}
    planner = cli.make_planner(planner=my_planner)
    assert planner is my_planner


def test_make_publisher_default_is_publish_evidence_atomic():
    from scripts import capture_hydration as ch
    assert cli.make_publisher() is ch.publish_evidence_atomic


def test_make_publisher_threads_injectable_override():
    calls = []

    def my_publisher(plan, out_dir):
        calls.append((plan, out_dir))

    publisher = cli.make_publisher(publisher=my_publisher)
    assert publisher is my_publisher
    publisher({"schema": "x"}, Path("/tmp/out"))
    assert calls == [({"schema": "x"}, Path("/tmp/out"))]


def test_factory_construction_does_not_invoke_execution_substrates(monkeypatch):
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
    assert cli.make_lifecycle(host="127.0.0.1", port=8126,
                               cwd=tmp_path)._ctx is None


def test_cli_does_not_reference_child_b_private_bridge_symbols():
    import re as _re
    text = SCRIPT.read_text(encoding="utf-8")
    for sym in ("_default_subprocess_bridge",):
        m = _re.search(
            rf"(?<![A-Za-z0-9_]){_re.escape(sym)}(?![A-Za-z0-9_])", text)
        assert m is None, (
            f"CLI must not reference Child B private {sym!r}; "
            "use cli.make_bridge() instead")


def test_build_default_seams_uses_cli_public_factories(tmp_path, monkeypatch):
    """build_default_seams must wire through the new public make_*()
    factories (lifecycle, collector, bridge) instead of inlining calls
    or reaching into Child B privates."""
    from scripts import capture_hydration as ch
    seen: dict = {}

    real_make_lc = cli.make_lifecycle
    real_make_coll = cli.make_collector
    real_make_br = cli.make_bridge

    def spy_lc(*, host, port, cwd, **kw):
        seen["lifecycle"] = (host, port, str(cwd))
        return real_make_lc(host=host, port=port, cwd=cwd, **kw)

    def spy_coll(**kw):
        seen["collector_factory_called"] = True
        return real_make_coll(**kw)

    def spy_br(**kw):
        seen["bridge_factory_called"] = True
        return real_make_br(**kw)

    monkeypatch.setattr(cli, "make_lifecycle", spy_lc)
    monkeypatch.setattr(cli, "make_collector", spy_coll)
    monkeypatch.setattr(cli, "make_bridge", spy_br)

    class _A:
        def chromium_provenance(self):
            return {"version": "x", "executable_path": "x"}
        def playwright_provenance(self):
            return {"version": "x"}
        def run_iteration(self, *, target_url, dom_marker_selector,
                          iteration_index):
            return {"iteration": iteration_index, "captured_at": "x"}

    monkeypatch.setattr(ch, "collect_raw_samples",
                        lambda *, target_url, browser_adapter, iterations,
                               dom_marker_selector: {
                            "schema": ch.SCHEMA,
                            "samples": [{"iteration": i, "captured_at": "x"}
                                        for i in range(iterations)],
                            "iterations": iterations})

    ns = cli._build_parser().parse_args([
        "--target-url", f"{BASE}/",
        "--out", str(tmp_path / "out"),
        "--iterations", "10",
        "--cwd", str(tmp_path)])
    seams = cli.build_default_seams(ns)
    assert isinstance(seams["lifecycle"], og.LegacyLifecycleAdapter)
    assert seen["lifecycle"] == ("127.0.0.1", 8765, str(tmp_path))
    assert seen["collector_factory_called"] is True
    assert seen["bridge_factory_called"] is True
    assert seams["planner"] is ch.plan_evidence_publication
    assert seams["publisher"] is ch.publish_evidence_atomic
