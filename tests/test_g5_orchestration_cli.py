"""Hermetic strict-TDD tests for Slices 1–14 of
``scripts/run_g5_orchestration.py``.

Slices 1–13 ship the bounded CLI surface, the seam factories (lifecycle /
collector / bridge / planner / publisher) and the ``build_default_seams``
plumbing. Slice 14 (adapted from ``e232a7c``) drops the deferred-seams
seam-assembly helper, wires every ``make_*()`` factory directly through
``main()`` into ``scripts.orchestrate_g5_legacy.run_orchestration``, and
maps the orchestration error taxonomy to specific exit codes.

All tests are hermetic (in-process; no subprocess / network / browser /
Node). Each test that needs to exercise CLI dispatch monkeypatches the
five ``make_*()`` factories AND ``og.run_orchestration`` so the assertion
is about CLI behavior, not orchestrator internals (already covered by
Child B's tests).
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


def _common_args(tmp_path: Path) -> list[str]:
    return ["--target-url", f"{BASE}/", "--out", str(tmp_path / "out"),
            "--iterations", "10"]


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


# ── surface / dry-run / parse / validate (preserved from 7f01b9a) ───────
def test_module_surface():
    import importlib
    importlib.reload(cli)
    for n in ("EXIT_OK", "EXIT_USAGE", "EXIT_VALIDATION",
              "EXIT_READINESS", "EXIT_COLLECTOR", "EXIT_BRIDGE",
              "EXIT_ORCHESTRATION",
              "main", "make_lifecycle", "make_collector", "make_bridge",
              "make_planner", "make_publisher"):
        assert hasattr(cli, n), f"missing public symbol: {n}"


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


# ── budget guard + subprocess smoke (no real subprocess/browser/network) ─
def test_slice_total_under_1700_lines():
    """Cumulative ergonomics guard: CLI + tests ≤ 1700 (Slices 1–15 + 16).
    Slice 1 was 800; the +300 relaxation is for Slice 14 behavior
    contracts (success dispatch + error taxonomy + bridge-script override),
    not synthetic. The +200 further relaxation is for Slice 15
    bridge-timeout advisory contracts (sentinel envelope, stderr advisory,
    orchestrator accumulation, CLI flag validation). The +400 further
    relaxation is for the bridge-advisory publication contracts (CLI
    docstring update, orchestrator threading, planner backward-compat
    probe, hermetic plan-entry tests, success-summary counter,
    byte-identical backward-compat test). This is CUMULATIVE ergonomics
    only; the per-PR delta budget remains ≤ 400 raw changed lines."""
    cli_text = SCRIPT.read_text(encoding="utf-8")
    assert cli_text.startswith("#!/usr/bin/env python")
    cli_lines = sum(1 for _ in cli_text.splitlines())
    this_lines = sum(1 for _ in Path(__file__).read_text(encoding="utf-8").splitlines())
    assert cli_lines + this_lines <= 1700, (
f"CLI + tests total is {cli_lines + this_lines} lines; budget is 1700")


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


# ── Slice 14: success dispatch + error taxonomy + bridge-script override ──
# All Slice 14 tests are hermetic (in-process; no subprocess / network /
# browser / Node). Each monkeypatches the 5 seam factories AND
# ``og.run_orchestration`` so the assertion is about CLI behavior,
# not orchestrator internals (already covered by Child B's tests).


class _FakeLifecycleAdapter:
    """Minimal duck-typed lifecycle for dispatch tests (records start/stop)."""
    def __init__(self):
        self.base_url = "http://fake"
        self._ctx: object | None = None
        self.start_calls = self.stop_calls = 0
    def start(self) -> None:
        self._ctx = "active"; self.start_calls += 1
    def stop(self) -> None:
        if self._ctx is not None: self.stop_calls += 1; self._ctx = None


def _patch_all_factories(monkeypatch):
    """Replace the 5 make_* factories with deterministic fakes. Returns a
    dict exposing ``<name>_kwargs`` (factory kwargs) and ``<name>_closure``
    (callable returned, for identity vs orchestrator)."""
    cap: dict = {}
    lc = _FakeLifecycleAdapter()
    cap["lifecycle_sentinel"] = lc

    def _lc(**kw):
        cap["lifecycle_kwargs"] = dict(kw); return lc

    def _col(**kw):
        cap["collector_kwargs"] = dict(kw)
        def c(*, target_url, iterations, dom_marker_selector):
            cap["collector_call"] = (target_url, iterations, dom_marker_selector)
            return {"schema": "taxa.g5-capture.legacy/1",
                    "samples": [], "iterations": iterations}
        cap["collector_closure"] = c; return c

    def _br(**kw):
        cap["bridge_kwargs"] = dict(kw)
        def b(url):
            cap["bridge_call"] = url
            return {"schema": "taxa.g5-raw-lhr.envelope/1", "url": url,
                    "lhr": {}, "provenance": {}}
        cap["bridge_closure"] = b; return b

    def _pl(**kw):
        cap["planner_kwargs"] = dict(kw)
        def p(*, playwright_raws, lighthouse_raws, manifest_snapshot,
                  legacy_hydration_metadata):
            cap["planner_call"] = (len(playwright_raws), len(lighthouse_raws))
            return {"schema": "taxa.g5-publication.evidence-manifest/1", "files": []}
        cap["planner_closure"] = p; return p

    def _pub(**kw):
        cap["publisher_kwargs"] = dict(kw)
        def u(plan, out_dir):
            cap["publisher_call"] = (plan, out_dir)
        cap["publisher_closure"] = u; return u

    for name, fn in (("make_lifecycle", _lc), ("make_collector", _col),
                         ("make_bridge", _br), ("make_planner", _pl),
                         ("make_publisher", _pub)):
        monkeypatch.setattr(cli, name, fn)
    return cap


def test_dry_run_never_constructs_or_calls_seams(monkeypatch, tmp_path):
    """``--dry-run`` must NOT construct any factory AND must NOT call
    ``og.run_orchestration`` (the deferred rejection is gone)."""
    exec_calls: list[str] = []
    def spy(name):
        def f(**kw):
            exec_calls.append(name)
            raise AssertionError(f"{name} must not run during dry-run")
        return f
    for n in ("lifecycle", "collector", "bridge", "planner", "publisher"):
        monkeypatch.setattr(cli, f"make_{n}", spy(n))
    monkeypatch.setattr(cli.og, "run_orchestration",
                        lambda **kw: exec_calls.append("orch") or 1/0)
    rc = cli.main(_common_args(tmp_path) + ["--dry-run"])
    assert rc == cli.EXIT_OK
    assert exec_calls == [], f"dry-run touched seams: {exec_calls}"


def test_non_dry_run_threads_cli_values(monkeypatch, tmp_path):
    """Successful dispatch threads every CLI value into factories and into
    ``og.run_orchestration`` (same instances returned by factories, not rebuilt)."""
    cap = _patch_all_factories(monkeypatch)
    orch: dict = {}

    def fake_run(**kw):
        orch.update(dict(kw))
        kw["lifecycle"].start(); kw["lifecycle"].stop()
        return {"schema": "taxa.g5-orchestrator.legacy/1",
                "published_at": "2025-01-01T00:00:00Z",
                "target_url": kw["target_url"],
                "iterations": kw["iterations"],
                "out_dir": str(kw["out_dir"]),
                "plan_schema": "taxa.g5-publication.evidence-manifest/1",
                "plan_files": 0}
    monkeypatch.setattr(cli.og, "run_orchestration", fake_run)

    real_dir = tmp_path / "real-dir"; real_dir.mkdir()
    bridge_script = tmp_path / "bridge.mjs"; bridge_script.write_text("// b\n")

    rc = cli.main(["--target-url", f"{BASE}/some/path",
                   "--out", str(tmp_path / "out"),
                   "--host", "127.0.0.1", "--port", "8123",
                   "--cwd", str(real_dir),
                   "--health-path", "/api/health",
                   "--health-timeout-s", "12.0",
                   "--health-interval-s", "0.1",
                   "--terminate-grace-s", "7.0",
                   "--bridge-script", str(bridge_script),
                   "--iterations", "10",
                   "--dom-marker-selector", "#x"])
    assert rc == cli.EXIT_OK

    lc = cap["lifecycle_kwargs"]
    assert (lc["host"], lc["port"], lc["cwd"], lc["health_path"]) == (
        "127.0.0.1", 8123, real_dir.resolve(), "/api/health")
    assert (lc["health_timeout_s"], lc["health_interval_s"],
            lc["terminate_grace_s"]) == (12.0, 0.1, 7.0)

    assert Path(cap["bridge_kwargs"]["bridge_script"]) == bridge_script

    # Orchestrator receives the EXACT instances returned by factories
    assert orch["lifecycle"] is cap["lifecycle_sentinel"]
    assert orch["collector"] is cap["collector_closure"]
    assert orch["bridge"] is cap["bridge_closure"]
    assert orch["planner"] is cap["planner_closure"]
    assert orch["publisher"] is cap["publisher_closure"]

    # Orchestrator receives CLI-level kwargs (resolved out_dir, etc.)
    assert orch["target_url"] == f"{BASE}/some/path"
    assert Path(orch["out_dir"]) == (tmp_path / "out").resolve()
    assert (orch["iterations"], orch["dom_marker_selector"]) == (10, "#x")


def test_non_dry_run_emits_success_summary_and_exits_zero(
    monkeypatch, tmp_path, capsys,
):
    """Non-dry-run success emits a one-line summary from the orchestrator
    descriptor and exits 0."""
    _patch_all_factories(monkeypatch)
    monkeypatch.setattr(cli.og, "run_orchestration",
                        lambda **kw: (kw["lifecycle"].start(),
                                          kw["lifecycle"].stop(),
                                          {"schema": "taxa.g5-orchestrator.legacy/1",
                                           "published_at": "2025-01-01T00:00:00Z",
                                           "target_url": kw["target_url"],
                                           "iterations": kw["iterations"],
                                           "out_dir": str(kw["out_dir"]),
                                           "plan_schema": "x",
                                           "plan_files": 7})[2])
    rc = cli.main(_common_args(tmp_path))
    assert rc == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "success" in out
    assert f"{BASE}/" in out and "10" in out  # target_url + iterations
    assert str((tmp_path / "out").resolve()) in out and "7" in out


@pytest.mark.parametrize("exc_factory,expected_rc,label", [
    (lambda: og.ReadinessError("r"), cli.EXIT_READINESS, "readiness"),
    (lambda: TimeoutError("t"), cli.EXIT_READINESS, "timeout"),
    (lambda: og.CollectorError("c"), cli.EXIT_COLLECTOR, "collector"),
    (lambda: og.BridgeError("b"), cli.EXIT_BRIDGE, "bridge"),
    (lambda: og.OrchestrationError("o"), cli.EXIT_ORCHESTRATION, "other"),
    (lambda: ValueError("v"), cli.EXIT_VALIDATION, "value"),
    (lambda: RuntimeError("u"), cli.EXIT_VALIDATION, "unknown"),
])
def test_error_taxonomy_maps_to_expected_exit_code(
    monkeypatch, tmp_path, exc_factory, expected_rc, label,
):
    """Readiness/Timeout→3, Collector→4, Bridge→5, other Orchestration→6,
    ValueError/unknown fail closed to 2."""
    _patch_all_factories(monkeypatch)
    monkeypatch.setattr(cli.og, "run_orchestration",
                        lambda **kw: (_ for _ in ()).throw(exc_factory()))
    assert cli.main(_common_args(tmp_path)) == expected_rc


def test_exit_code_constants_match_documented_contract():
    """Slice 14 exit codes: 3 readiness / 4 collector / 5 bridge / 6 other."""
    assert (cli.EXIT_OK, cli.EXIT_USAGE, cli.EXIT_VALIDATION) == (0, 1, 2)
    assert (cli.EXIT_READINESS, cli.EXIT_COLLECTOR,
            cli.EXIT_BRIDGE, cli.EXIT_ORCHESTRATION) == (3, 4, 5, 6)


def test_bridge_script_override_does_not_execute_at_construction(
    monkeypatch, tmp_path,
):
    """``make_bridge(bridge_script=...)`` captures the script at construction
    but never touches subprocess / which (argv only matters at invocation)."""
    bscript = tmp_path / "custom.mjs"; bscript.write_text("// b\n")
    exec_calls: list[str] = []
    monkeypatch.setattr(cli.subprocess, "run",
                        lambda *a, **kw: exec_calls.append("run"))
    monkeypatch.setattr(cli.shutil, "which",
                        lambda name: exec_calls.append("which") or "/usr/bin/node")
    assert callable(cli.make_bridge(bridge_script=bscript))
    assert exec_calls == []


def test_bridge_script_override_threads_into_argv_when_invoked(
    monkeypatch, tmp_path,
):
    """When the default closure is invoked, argv[1] is the supplied
    ``bridge_script`` (NOT ``og.DEFAULT_BRIDGE_SCRIPT``)."""
    bscript = tmp_path / "custom.mjs"; bscript.write_text("// b\n")
    captured: dict = {}
    def fake_run(argv, **kw):
        captured["argv"] = list(argv)
        return type("R", (), {"returncode": 0,
                                   "stdout": '{"schema":"taxa.g5-raw-lhr.envelope/1",'
                                              '"url":"x","lhr":{},"provenance":{}}\n',
                                   "stderr": ""})()
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/node")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    cli.make_bridge(bridge_script=bscript)("http://x")
    assert captured["argv"] == ["/usr/bin/node", str(bscript), "--url", "http://x"]


def test_bridge_default_uses_default_bridge_script(monkeypatch):
    """Without ``bridge_script=``, default bridge uses ``og.DEFAULT_BRIDGE_SCRIPT``."""
    captured: dict = {}
    def fake_run(argv, **kw):
        captured["argv"] = list(argv)
        return type("R", (), {"returncode": 0,
                                   "stdout": '{"schema":"taxa.g5-raw-lhr.envelope/1",'
                                              '"url":"x","lhr":{},"provenance":{}}\n',
                                   "stderr": ""})()
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/node")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    cli.make_bridge()("http://x")
    assert captured["argv"] == ["/usr/bin/node", str(og.DEFAULT_BRIDGE_SCRIPT),
"--url", "http://x"]


def test_dry_run_with_bridge_script_does_not_invoke_substrates(
        monkeypatch, tmp_path,
    ):
        """``--dry-run --bridge-script <real-file>`` validates the bridge path
        but never invokes subprocess / which (bridge closure is never built)."""
        bscript = tmp_path / "real-bridge.mjs"; bscript.write_text("// b\n")
        exec_calls: list[str] = []
        monkeypatch.setattr(cli.subprocess, "run",
                            lambda *a, **kw: exec_calls.append("run"))
        monkeypatch.setattr(cli.shutil, "which",
                            lambda name: exec_calls.append("which") or "/u/n")
        monkeypatch.setattr(cli, "make_bridge",
                            lambda **kw: exec_calls.append("bridge") or (lambda u: {}))
        rc = cli.main(["--target-url", f"{BASE}/", "--out", str(tmp_path / "out"),
                       "--iterations", "10", "--bridge-script", str(bscript),
                       "--dry-run"])
        assert rc == cli.EXIT_OK
        assert exec_calls == [], f"dry-run touched substrates: {exec_calls}"


# ── Slice 15: bridge-timeout advisory ───────────────────────────────
# Bounds the bridge subprocess call so a hung Lighthouse bridge cannot
# block forever. On timeout the closure emits a stderr advisory and
# returns a schema-conformant sentinel envelope (advisory provenance).
# Orchestrator accumulates optional ``bridge_advisories`` only when at
# least one timeout happens. ``--bridge-timeout-s`` defaults to 30.0
# and must be positive; dry-run never touches any substrate.

def test_bridge_timeout_s_default_constant():
    """Default bridge timeout is 30.0 seconds (bounded bridge)."""
    assert cli.DEFAULT_BRIDGE_TIMEOUT_S == 30.0

@pytest.mark.parametrize("val,expected_in_msg", [
    ("0", "bridge-timeout-s"),
    ("-1.0", "bridge-timeout-s"),
    ("-30.0", "bridge-timeout-s"),
])
def test_bad_bridge_timeout_exits_validation(capsys, val, expected_in_msg):
    rc = cli.main(["--target-url", f"{BASE}/", "--out", "/tmp/x",
                   "--bridge-timeout-s", val])
    assert rc == cli.EXIT_VALIDATION
    err = capsys.readouterr().err
    assert expected_in_msg in err

def test_good_bridge_timeout_passes_validation(capsys, tmp_path):
    rc = cli.main(["--target-url", f"{BASE}/", "--out", str(tmp_path / "out"),
                   "--bridge-timeout-s", "5.0", "--dry-run"])
    assert rc == cli.EXIT_OK

def test_dry_run_with_bridge_timeout_s_does_not_invoke_substrates(
    monkeypatch, tmp_path,
):
    """``--dry-run --bridge-timeout-s`` validates but never invokes
    subprocess / which / make_bridge."""
    exec_calls: list[str] = []
    monkeypatch.setattr(cli.subprocess, "run",
                        lambda *a, **kw: exec_calls.append("run"))
    monkeypatch.setattr(cli.shutil, "which",
                        lambda name: exec_calls.append("which") or "/u/n")
    monkeypatch.setattr(cli, "make_bridge",
                        lambda **kw: exec_calls.append("bridge") or (lambda u: {}))
    rc = cli.main(["--target-url", f"{BASE}/", "--out", str(tmp_path / "out"),
                   "--iterations", "10",
                   "--bridge-timeout-s", "5.0", "--dry-run"])
    assert rc == cli.EXIT_OK
    assert exec_calls == [], f"dry-run touched substrates: {exec_calls}"

def test_help_text_mentions_bridge_timeout_s(capsys):
    rc = cli.main(["--help"])
    assert rc == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "--bridge-timeout-s" in out
    assert "30" in out

def test_make_bridge_default_timeout_is_30s(monkeypatch):
    """``make_bridge()`` captures ``bridge_timeout_s=30.0`` and binds it
    to the closure (visible as a kwarg captured at construction)."""
    captured: dict = {}
    def fake_run(argv, **kw):
        captured["kwargs"] = dict(kw)
        return type("R", (), {"returncode": 0,
                                   "stdout": '{"schema":"taxa.g5-raw-lhr.envelope/1",'
                                              '"url":"x","lhr":{},"provenance":{}}\n',
                                   "stderr": ""})()
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/node")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    bridge = cli.make_bridge()
    bridge("http://x")
    assert captured["kwargs"].get("timeout") == cli.DEFAULT_BRIDGE_TIMEOUT_S
    assert captured["kwargs"]["timeout"] == 30.0

def test_make_bridge_threads_bridge_timeout_kwarg(monkeypatch):
    """``make_bridge(bridge_timeout_s=...)`` threads the supplied value
    into the closure as ``subprocess.run(timeout=...)``."""
    captured: dict = {}
    def fake_run(argv, **kw):
        captured["kwargs"] = dict(kw)
        return type("R", (), {"returncode": 0,
                                   "stdout": '{"schema":"taxa.g5-raw-lhr.envelope/1",'
                                              '"url":"x","lhr":{},"provenance":{}}\n',
                                   "stderr": ""})()
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/node")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    bridge = cli.make_bridge(bridge_timeout_s=7.5)
    bridge("http://x")
    assert captured["kwargs"].get("timeout") == 7.5

def test_make_bridge_returns_sentinel_envelope_on_timeout(
    monkeypatch, capsys,
):
    """When subprocess.run raises TimeoutExpired the closure must return
    a schema-conformant sentinel envelope with an ``advisory`` field,
    NOT raise ``BridgeError`` (non-blocking)."""
    def fake_run(argv, **kw):
        raise subprocess.TimeoutExpired(cmd=list(argv), timeout=kw.get("timeout") or 0.0)
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/node")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    bridge = cli.make_bridge(bridge_timeout_s=2.0)
    env = bridge("http://example.test/foo")
    assert env["schema"] == "taxa.g5-raw-lhr.envelope/1"
    assert env["url"] == "http://example.test/foo"
    assert isinstance(env["lhr"], dict) and env["lhr"]
    assert isinstance(env.get("provenance"), dict)
    assert isinstance(env.get("advisory"), dict)
    adv = env["advisory"]
    assert adv.get("kind") == "bridge_timeout"
    assert adv.get("timeout_s") == 2.0
    # stderr advisory emitted
    err = capsys.readouterr().err
    assert "bridge timeout" in err.lower()
    assert "http://example.test/foo" in err

def test_make_bridge_does_not_raise_bridge_error_on_timeout(monkeypatch):
    """Timeout does NOT raise BridgeError — that's the whole point of the
    non-blocking contract. Existing BridgeError contract (missing node,
    non-zero exit, bad JSON) is preserved."""
    def fake_run(argv, **kw):
        raise subprocess.TimeoutExpired(cmd=list(argv), timeout=kw.get("timeout") or 0.0)
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/node")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    bridge = cli.make_bridge(bridge_timeout_s=1.0)
    # MUST NOT raise
    env = bridge("http://x")
    assert env["schema"] == "taxa.g5-raw-lhr.envelope/1"

def test_make_bridge_missing_node_still_raises_bridge_error(monkeypatch):
    """Existing BridgeError contract is preserved when 'node' is missing."""
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    bridge = cli.make_bridge(bridge_timeout_s=5.0)
    with pytest.raises(og.BridgeError, match="node"):
        bridge("http://x")

def test_make_bridge_non_zero_exit_still_raises_bridge_error(monkeypatch):
    """Existing BridgeError contract is preserved for non-zero exit."""
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/node")
    monkeypatch.setattr(cli.subprocess, "run",
                        lambda *a, **kw: type("R", (), {
                            "returncode": 1, "stdout": "", "stderr": "boom"})())
    bridge = cli.make_bridge(bridge_timeout_s=5.0)
    with pytest.raises(og.BridgeError, match="exited 1"):
        bridge("http://x")

def test_non_dry_run_threads_bridge_timeout_s_into_factory(
    monkeypatch, tmp_path,
):
    """CLI threads ``--bridge-timeout-s`` into ``make_bridge`` factory."""
    cap = _patch_all_factories(monkeypatch)
    monkeypatch.setattr(cli.og, "run_orchestration",
                        lambda **kw: {"schema": "taxa.g5-orchestrator.legacy/1",
                                          "published_at": "2025-01-01T00:00:00Z",
                                          "target_url": kw["target_url"],
                                          "iterations": kw["iterations"],
                                          "out_dir": str(kw["out_dir"]),
                                          "plan_schema": "x",
                                          "plan_files": 0})
    rc = cli.main(_common_args(tmp_path) + ["--bridge-timeout-s", "12.5"])
    assert rc == cli.EXIT_OK
    assert cap["bridge_kwargs"].get("bridge_timeout_s") == 12.5

def test_non_dry_run_threads_default_bridge_timeout_into_factory(
    monkeypatch, tmp_path,
):
    """Without ``--bridge-timeout-s``, factory receives the default."""
    cap = _patch_all_factories(monkeypatch)
    monkeypatch.setattr(cli.og, "run_orchestration",
                        lambda **kw: {"schema": "taxa.g5-orchestrator.legacy/1",
                                          "published_at": "2025-01-01T00:00:00Z",
                                          "target_url": kw["target_url"],
                                          "iterations": kw["iterations"],
                                          "out_dir": str(kw["out_dir"]),
                                          "plan_schema": "x",
                                          "plan_files": 0})
    rc = cli.main(_common_args(tmp_path))
    assert rc == cli.EXIT_OK
    assert cap["bridge_kwargs"].get("bridge_timeout_s") == cli.DEFAULT_BRIDGE_TIMEOUT_S

def test_bridge_timeout_orchestrator_accumulates_advisories(
    monkeypatch, tmp_path, capsys,
):
    """When the bridge always returns sentinel envelopes, the orchestrator
    descriptor accumulates ``bridge_advisories`` and the CLI prints
    a stderr advisory per timeout. Exit code is 0 (non-blocking)."""
    def fake_run(argv, **kw):
        raise subprocess.TimeoutExpired(cmd=list(argv), timeout=kw.get("timeout") or 0.0)
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/node")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    def fake_collector(*, target_url, iterations, dom_marker_selector):
        samples = []
        for i in range(iterations):
            samples.append({
                "iteration": i, "captured_at": "t",
                "navigation": {"response_start_ms": 0,
                                  "dom_content_loaded_ms": 0,
                                  "load_event_ms": 0,
                                  "redirect_count": 0, "status": 200},
                "paint": {"first_paint_ms": 0,
                            "first_contentful_paint_ms": 0},
                "dom_marker": {"selector": "#x", "found": True, "count": 1,
                                  "first_text": "x", "wait_ms": 0},
                "console": [],
            })
        return {"schema": "taxa.g5-capture.legacy/1",
                "samples": samples, "iterations": iterations}
    monkeypatch.setattr(cli, "make_collector", lambda **kw: fake_collector)
    def fake_planner(**kw):
        return {"schema": "taxa.g5-publication.evidence-manifest/1", "files": []}
    monkeypatch.setattr(cli, "make_planner", lambda **kw: fake_planner)
    monkeypatch.setattr(cli, "make_publisher", lambda **kw: (lambda p, o: None))
    monkeypatch.setattr(cli, "make_lifecycle",
                        lambda **kw: _FakeLC())

    rc = cli.main(_common_args(tmp_path) + ["--bridge-timeout-s", "1.0"])
    assert rc == cli.EXIT_OK
    err = capsys.readouterr().err
    assert "bridge timeout" in err.lower()


# ── Slice 16: bridge-advisory publication ─────────────────────────────
# The orchestrator accumulates bridge_advisories (when bounded bridge
# subprocesses time out) and the planner persists them atomically as
# ``raw/bridge-advisories.json`` through the existing evidence
# publication plan. None/empty produces a byte-identical plan and no
# file. Hermetic tests verify the CLI dispatches through the real
# planner contract, dry-run stays isolated, and backward compat with
# older planner signatures is preserved.


def test_cli_docstring_header_includes_slice_16():
    """The CLI docstring header MUST mention Slice 16 (bridge-advisory
    publication) so reviewers can locate the bounded surface."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "Slice 16" in text, (
        "CLI docstring header must enumerate Slice 16 (it currently "
        "only enumerates Slices 1–15).")
    assert "bridge_advisories" in text, (
        "CLI docstring must reference the bridge_advisories contract.")


def test_cli_orchestrator_threads_advisories_to_real_planner(monkeypatch, tmp_path):
    """When the bridge returns sentinel envelopes (timeout), the
    orchestrator threads ``bridge_advisories`` through to the real
    ``capture_hydration.plan_evidence_publication`` and the resulting
    plan carries exactly ONE ``raw/bridge-advisories.json`` entry."""
    from scripts import capture_hydration as ch

    def fake_run(argv, **kw):
        raise subprocess.TimeoutExpired(cmd=list(argv),
                                            timeout=kw.get("timeout") or 0.0)

    monkeypatch.setattr(cli.shutil, "which",
                        lambda name: "/usr/bin/node")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    def fake_collector(**kw):
        def c(*, target_url, iterations, dom_marker_selector):
            samples = []
            for i in range(iterations):
                samples.append({
                    "iteration": i, "captured_at": "t",
                    "navigation": {"response_start_ms": 0,
                                      "dom_content_loaded_ms": 0,
                                      "load_event_ms": 0,
                                      "redirect_count": 0, "status": 200},
                    "paint": {"first_paint_ms": 0,
                                "first_contentful_paint_ms": 0},
                    "dom_marker": {"selector": "#x", "found": True,
                                      "count": 1, "first_text": "x",
                                      "wait_ms": 0},
                    "console": [],
                })
            return {"schema": ch.SCHEMA, "samples": samples,
                    "iterations": iterations}
        return c

    monkeypatch.setattr(cli, "make_collector", fake_collector)
    captured: dict = {}
    real_planner = ch.plan_evidence_publication

    def spy_planner(**kw):
        captured["bridge_advisories"] = kw.get("bridge_advisories")
        captured["keys"] = sorted(kw.keys())
        return real_planner(**kw)

    monkeypatch.setattr(cli, "make_planner", lambda **kw: spy_planner)
    monkeypatch.setattr(cli, "make_publisher",
                        lambda **kw: (lambda p, o: None))
    monkeypatch.setattr(cli, "make_lifecycle",
                        lambda **kw: _FakeLC())
    rc = cli.main(_common_args(tmp_path) + ["--bridge-timeout-s", "1.0"])
    assert rc == cli.EXIT_OK
    assert captured["bridge_advisories"] is not None
    assert len(captured["bridge_advisories"]) == 10
    assert all(isinstance(a, dict) for a in captured["bridge_advisories"])
    assert "bridge_advisories" in captured["keys"]


def test_cli_no_advisories_omits_kwarg_for_legacy_planner(monkeypatch, tmp_path):
    """Backward compat: when no bridge timeouts happen (so
    ``bridge_advisories`` is empty), the orchestrator MUST NOT pass
    the kwarg to a planner that does not accept it. Older fake
    planners pre-dating the bridge-advisory publication slice
    continue to work unchanged."""
    from scripts import capture_hydration as ch

    def fake_collector(**kw):
        def c(*, target_url, iterations, dom_marker_selector):
            samples = []
            for i in range(iterations):
                samples.append({
                    "iteration": i, "captured_at": "t",
                    "navigation": {"response_start_ms": 0,
                                      "dom_content_loaded_ms": 0,
                                      "load_event_ms": 0,
                                      "redirect_count": 0, "status": 200},
                    "paint": {"first_paint_ms": 0,
                                "first_contentful_paint_ms": 0},
                    "dom_marker": {"selector": "#x", "found": True,
                                      "count": 1, "first_text": "x",
                                      "wait_ms": 0},
                    "console": [],
                })
            return {"schema": ch.SCHEMA, "samples": samples,
                    "iterations": iterations}
        return c

    monkeypatch.setattr(cli, "make_collector", fake_collector)
    monkeypatch.setattr(cli, "make_bridge",
                        lambda **kw: (lambda u: {"schema":
                            "taxa.g5-raw-lhr.envelope/1",
                            "url": u, "lhr": {}, "provenance": {}}))
    captured: dict = {}

    def legacy_planner(*, playwright_raws, lighthouse_raws,
                          manifest_snapshot, legacy_hydration_metadata):
        captured["called"] = True
        captured["keys"] = sorted(set(locals().keys()))
        return {"schema": "taxa.g5-publication.evidence-manifest/1",
                "files": []}

    monkeypatch.setattr(cli, "make_planner", lambda **kw: legacy_planner)
    monkeypatch.setattr(cli, "make_publisher",
                        lambda **kw: (lambda p, o: None))
    monkeypatch.setattr(cli, "make_lifecycle",
                        lambda **kw: _FakeLC())
    rc = cli.main(_common_args(tmp_path))
    assert rc == cli.EXIT_OK
    assert captured.get("called") is True
    assert "bridge_advisories" not in captured["keys"]


def test_cli_success_summary_includes_bridge_advisories_count(
    monkeypatch, tmp_path, capsys,
):
    """When the orchestrator's descriptor carries bridge_advisories,
    the CLI success summary includes ``bridge_advisories=<count>``."""
    monkeypatch.setattr(cli, "make_lifecycle",
                        lambda **kw: _FakeLC())
    monkeypatch.setattr(cli, "make_collector", lambda **kw: _collector())
    monkeypatch.setattr(cli, "make_bridge", lambda **kw: _bridge())
    monkeypatch.setattr(cli, "make_planner", lambda **kw: _planner())
    monkeypatch.setattr(cli, "make_publisher", lambda **kw: _publisher())

    monkeypatch.setattr(cli.og, "run_orchestration",
                        lambda **kw: (kw["lifecycle"].start(),
                                          kw["lifecycle"].stop(),
                                          {"schema":
                                           "taxa.g5-orchestrator.legacy/1",
                                           "published_at":
                                           "2025-01-01T00:00:00Z",
                                           "target_url": kw["target_url"],
                                           "iterations": kw["iterations"],
                                           "out_dir": str(kw["out_dir"]),
                                           "plan_schema": "x",
                                           "plan_files": 0,
                                           "bridge_advisories":
                                           [{"iteration": i,
                                             "kind": "bridge_timeout",
                                             "reason": "x",
                                             "timeout_s": 1.0,
                                             "url": kw["target_url"]}
                                            for i in range(1, 11)]})[2])
    rc = cli.main(_common_args(tmp_path))
    assert rc == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "bridge_advisories=10" in out, (
        f"success summary MUST include bridge_advisories count; got: "
        f"{out!r}")


def test_cli_dry_run_does_not_touch_bridge_advisories_path(
    monkeypatch, tmp_path,
):
    """``--dry-run`` MUST NOT touch any bridge_advisories path:
    substrate (Popen / urlopen / which) is not invoked; no orchestrator
    instance is constructed; dry-run stays isolated even with
    ``--bridge-timeout-s`` set."""
    exec_calls: list = []
    monkeypatch.setattr(cli.subprocess, "Popen",
                        lambda *a, **kw: exec_calls.append("Popen"))
    monkeypatch.setattr(cli.subprocess, "run",
                        lambda *a, **kw: exec_calls.append("run"))
    monkeypatch.setattr(cli.urllib.request, "urlopen",
                        lambda *a, **kw: exec_calls.append("urlopen"))
    monkeypatch.setattr(cli.shutil, "which",
                        lambda *a, **kw: exec_calls.append("which")
                        or "/usr/bin/node")
    monkeypatch.setattr(cli.og, "run_orchestration",
                        lambda **kw: exec_calls.append("run_orch"))
    rc = cli.main(_common_args(tmp_path) + ["--dry-run",
                                             "--bridge-timeout-s", "5.0"])
    assert rc == cli.EXIT_OK
    assert exec_calls == [], (
        f"dry-run touched substrates: {exec_calls}")


def test_cli_orchestrator_legacy_planner_ignores_kwarg_on_timeout(
    monkeypatch, tmp_path,
):
    """End-to-end: the real orchestrator threads bridge_advisories
    ONLY when the planner signature accepts it. A legacy fake
    planner (without ``bridge_advisories`` in its signature) is
    invoked with the ORIGINAL 4 kwargs only, even when bridge
    timeouts happened. This protects pre-slice-16 test fixtures."""
    from scripts import capture_hydration as ch

    def fake_run(argv, **kw):
        raise subprocess.TimeoutExpired(cmd=list(argv),
                                            timeout=kw.get("timeout") or 0.0)

    monkeypatch.setattr(cli.shutil, "which",
                        lambda name: "/usr/bin/node")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    def fake_collector(**kw):
        def c(*, target_url, iterations, dom_marker_selector):
            samples = []
            for i in range(iterations):
                samples.append({
                    "iteration": i, "captured_at": "t",
                    "navigation": {"response_start_ms": 0,
                                      "dom_content_loaded_ms": 0,
                                      "load_event_ms": 0,
                                      "redirect_count": 0, "status": 200},
                    "paint": {"first_paint_ms": 0,
                                "first_contentful_paint_ms": 0},
                    "dom_marker": {"selector": "#x", "found": True,
                                      "count": 1, "first_text": "x",
                                      "wait_ms": 0},
                    "console": [],
                })
            return {"schema": ch.SCHEMA, "samples": samples,
                    "iterations": iterations}
        return c

    monkeypatch.setattr(cli, "make_collector", fake_collector)
    captured: dict = {}

    def legacy_planner(*, playwright_raws, lighthouse_raws,
                          manifest_snapshot, legacy_hydration_metadata):
        captured["legacy_called"] = True
        return {"schema": "taxa.g5-publication.evidence-manifest/1",
                "files": []}

    monkeypatch.setattr(cli, "make_planner", lambda **kw: legacy_planner)
    monkeypatch.setattr(cli, "make_publisher",
                        lambda **kw: (lambda p, o: None))
    monkeypatch.setattr(cli, "make_lifecycle",
                        lambda **kw: _FakeLC())
    rc = cli.main(_common_args(tmp_path) + ["--bridge-timeout-s", "1.0"])
    assert rc == cli.EXIT_OK
    assert captured.get("legacy_called") is True
