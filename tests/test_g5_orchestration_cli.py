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


def test_slice_total_under_400_lines():
    """Bounded scope guard: CLI + tests must stay ≤ 400 lines (no scope drift)."""
    cli_text = SCRIPT.read_text(encoding="utf-8")
    assert cli_text.startswith("#!/usr/bin/env python")
    cli_lines = sum(1 for _ in cli_text.splitlines())
    this_lines = sum(1 for _ in Path(__file__).read_text(encoding="utf-8").splitlines())
    total = cli_lines + this_lines
    assert total <= 400, f"CLI + tests total is {total} lines; budget is 400"


def test_script_does_not_modify_child_b():
    """Slice 1 only imports Child B for constants; it must NOT mutate it."""
    text = SCRIPT.read_text(encoding="utf-8")
    forbidden = "scripts/orchestrate_g5_legacy.py"
    assert f'open({forbidden!r}' not in text and f'Path({forbidden!r}' not in text, (
        f"CLI must not touch {forbidden} as a file")
    assert ("import scripts.orchestrate_g5_legacy" in text
            or "from scripts import orchestrate_g5_legacy" in text), (
            "Slice 1 CLI must import Child B for defaults")
    assert "capture_hydration" not in text, (
        "Slice 1 must not import capture_hydration; defer to seam-wiring slice")


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
