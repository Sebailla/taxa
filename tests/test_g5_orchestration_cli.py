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
def test_slice_total_under_400_lines():
    cli_text = SCRIPT.read_text(encoding="utf-8")
    assert cli_text.startswith("#!/usr/bin/env python")
    cli_lines = sum(1 for _ in cli_text.splitlines())
    this_lines = sum(1 for _ in Path(__file__).read_text(encoding="utf-8").splitlines())
    assert cli_lines + this_lines <= 400


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
