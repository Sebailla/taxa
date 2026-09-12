"""G4 Makefile parity composition tests (PR base slice).

Hermetic: every test runs the system `make` against the repository Makefile
with PATH shims for `python3` / `node`, so no real Playwright / Lighthouse /
network / package install is touched. Validates the `make parity` external-URL
composition contract (PARITY_URL / PARITY_OUT / PARITY_MANIFEST required;
PARITY_QUERIES rejected; producer order; no lifecycle / install commands;
preflight gates; component atomicity boundaries; --queries omitted from the
base-slice producer). Reference: design.md §3.3.4 (G4).
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
SAMPLE_URL = "http://127.0.0.1:8765/index.html"


def _make(*args, env=None, cwd=None, make_path=None):
    """Run `make` against the repo Makefile; strips inherited PARITY_*.
    Pass `make_path` (absolute) for hermetic PATH-override tests."""
    full_env = os.environ.copy()
    for k in ("PARITY_URL", "PARITY_OUT", "PARITY_MANIFEST", "PARITY_QUERIES"):
        full_env.pop(k, None)
    if env:
        full_env.update(env)
    return subprocess.run(
        [make_path or "make", "-f", str(MAKEFILE), *args],
        cwd=cwd or REPO_ROOT, env=full_env,
        capture_output=True, text=True, check=False,
    )


def _system_make() -> str:
    """Locate the system `make` binary (for hermetic PATH-override tests)."""
    mp = shutil.which("make")
    if not mp:
        raise RuntimeError("system `make` not found on PATH")
    return mp


def _write_shim(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _shim_dir(tmp_path: Path, *, with_python3: bool = True,
              with_node: bool = True, python_exit: int = 0,
              node_exit: int = 0) -> Path:
    """Hermetic shim dir: python3 + node shims that log+exit (per config),
    plus a mkdir shim delegating to /bin/mkdir so `mkdir -p` works without
    pulling /usr/bin onto PATH (which would leak system python3/node)."""
    d = tmp_path / "shims"
    d.mkdir()
    log = tmp_path / "shim.log"
    if with_python3:
        _write_shim(d / "python3", (
            "#!/bin/bash\n"
            f"printf 'python3 %s\\n' \"$*\" >> {log}\n"
            f"exit {python_exit}\n"
        ))
    if with_node:
        _write_shim(d / "node", (
            "#!/bin/bash\n"
            f"printf 'node %s\\n' \"$*\" >> {log}\n"
            f"exit {node_exit}\n"
        ))
    _write_shim(d / "mkdir", "#!/bin/bash\nexec /bin/mkdir \"$@\"\n")
    return d


def _shim_log(parent: Path) -> str:
    p = parent / "shim.log"
    return p.read_text() if p.exists() else ""


def _env(tmp_path: Path, **overrides) -> dict:
    """Build a minimal env dict with the three required PARITY_* vars set."""
    base = {
        "PARITY_URL": SAMPLE_URL,
        "PARITY_OUT": str(tmp_path / "out"),
        "PARITY_MANIFEST": str(tmp_path / "manifest.json"),
    }
    base.update(overrides)
    return base


def _build_sandbox(tmp_path: Path) -> Path:
    """Sandbox cwd mirroring the recipe's tree layout (scripts/, tools/...).
    Each fake script is a no-op exit-0 so the preflight script checks pass."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "capture_parity_reports.py").write_text(
        "#!/bin/bash\nexit 0\n")
    (tmp_path / "scripts" / "capture_a11y_report.py").write_text(
        "#!/bin/bash\nexit 0\n")
    g4 = tmp_path / "tools" / "g4-capture"
    g4.mkdir(parents=True)
    (g4 / "scripts").mkdir()
    (g4 / "scripts" / "capture.mjs").write_text("// sandbox\n")
    (g4 / "node_modules").mkdir()
    return tmp_path


def _dry_run_recipe(env):
    """Run `make -n parity`; return the recipe output as a string."""
    r = _make("-n", "parity", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


# ── Required-variable rejection (runtime) ─────────────────────────────


def test_make_parity_fails_when_PARITY_URL_missing(tmp_path):
    """PARITY_URL missing → fail closed BEFORE any producer runs."""
    r = _make("parity", env={
        "PARITY_OUT": str(tmp_path / "out"),
        "PARITY_MANIFEST": str(tmp_path / "manifest.json"),
    })
    assert r.returncode != 0, r.stdout + r.stderr
    assert "PARITY_URL" in r.stdout + r.stderr


def test_make_parity_fails_when_PARITY_OUT_missing(tmp_path):
    """PARITY_OUT missing → fail closed BEFORE any producer runs."""
    r = _make("parity", env={
        "PARITY_URL": SAMPLE_URL,
        "PARITY_MANIFEST": str(tmp_path / "manifest.json"),
    })
    assert r.returncode != 0, r.stdout + r.stderr
    assert "PARITY_OUT" in r.stdout + r.stderr


def test_make_parity_fails_when_PARITY_MANIFEST_missing(tmp_path):
    """PARITY_MANIFEST missing → fail closed BEFORE any producer runs."""
    r = _make("parity", env={
        "PARITY_URL": SAMPLE_URL,
        "PARITY_OUT": str(tmp_path / "out"),
    })
    assert r.returncode != 0, r.stdout + r.stderr
    assert "PARITY_MANIFEST" in r.stdout + r.stderr


# ── Query rejection (base slice) ──────────────────────────────────────


def test_make_parity_fails_when_PARITY_QUERIES_nonempty(tmp_path):
    """PARITY_QUERIES non-empty → fail BEFORE any producer runs."""
    r = _make("parity", env=_env(tmp_path, PARITY_QUERIES="trout"))
    assert r.returncode != 0, r.stdout + r.stderr
    assert "PARITY_QUERIES" in r.stdout + r.stderr
    assert "capture_parity_reports.py" not in r.stdout


def test_make_parity_does_not_propagate_PARITY_QUERIES_to_shell(tmp_path):
    """TRIANGULATE: PARITY_QUERIES carrying shell metachars is never
    shell-expanded into a producer command line in this base slice."""
    dangerous = "foo; touch /tmp/parity-shell-leak-marker; rm -rf /tmp/x"
    r = _make("parity", env=_env(tmp_path, PARITY_QUERIES=dangerous))
    assert r.returncode != 0, r.stdout + r.stderr
    assert "PARITY_QUERIES" in r.stdout + r.stderr
    assert "/tmp/parity-shell-leak-marker" not in r.stdout
    assert dangerous not in r.stdout


# ── Command ordering & flags (dry-run) ────────────────────────────────


def test_make_parity_dry_run_emits_producers_in_correct_order(tmp_path):
    """Producers appear in documented order: nav/api → lighthouse → a11y.
    Search for the unique invocation prefix so preflight gate lines
    mentioning the script names are not matched."""
    out = _dry_run_recipe(_env(tmp_path))
    nav_pos = out.find("python3 scripts/capture_parity_reports.py")
    lh_pos = out.find("node scripts/capture.mjs")
    a11y_pos = out.find("python3 scripts/capture_a11y_report.py")
    assert nav_pos >= 0 and lh_pos >= 0 and a11y_pos >= 0, out
    assert nav_pos < lh_pos < a11y_pos, (
        f"order violated: nav={nav_pos} lh={lh_pos} a11y={a11y_pos}\n{out}")


def test_make_parity_dry_run_passes_correct_flags(tmp_path):
    """Each producer invocation carries the exact flags/args derived
    from the current source contracts."""
    out_dir = str(tmp_path / "out")
    manifest = str(tmp_path / "manifest.json")
    out = _dry_run_recipe(_env(tmp_path))
    lines = out.splitlines()
    nav_line = next(ln for ln in lines if "python3 scripts/capture_parity_reports.py" in ln)
    assert "--url" in nav_line and SAMPLE_URL in nav_line
    assert "--out-dir" in nav_line and out_dir in nav_line
    lh_line = next(ln for ln in lines if "node scripts/capture.mjs" in ln)
    assert "--url" in lh_line and SAMPLE_URL in lh_line
    assert "--manifest" in lh_line and manifest in lh_line
    assert "--out" in lh_line and out_dir in lh_line
    a11y_line = next(ln for ln in lines if "python3 scripts/capture_a11y_report.py" in ln)
    assert "--evidence" in a11y_line and "evidence.json" in a11y_line
    assert "--out-dir" in a11y_line and out_dir in a11y_line


def test_make_parity_dry_run_omits_queries_flag_for_capture_parity_reports(tmp_path):
    """Base-slice invariant: capture_parity_reports.py is invoked WITHOUT
    --queries. Search query support is deferred to the next PR."""
    out = _dry_run_recipe(_env(tmp_path))
    nav_line = next(
        ln for ln in out.splitlines()
        if "python3 scripts/capture_parity_reports.py" in ln
    )
    assert "--queries" not in nav_line


# ── No lifecycle / install commands ───────────────────────────────────


def test_make_parity_no_lifecycle_or_install_commands(tmp_path):
    """No server-start, no package-install, no kill / pkill / backgrounding.
    The base slice is an external-URL composition; the caller owns the
    server lifecycle. The recipe must not start/stop anything."""
    out = _dry_run_recipe(_env(tmp_path))
    for s in ("npm install", "pip install", "pip3 install",
              "kill ", "pkill", "nohup",
              "uvicorn", "make api", "make web"):
        assert s not in out, f"forbidden substring {s!r} present:\n{out}"


# ── Preflight gates ──────────────────────────────────────────────────


def test_make_parity_preflight_includes_required_checks(tmp_path):
    """Dry-run output MUST include every preflight gate the contract pins
    (env vars, tools, scripts, lighthouse node_modules)."""
    out = _dry_run_recipe(_env(tmp_path))
    for required in (
        "PARITY_URL is required",
        "PARITY_OUT is required",
        "PARITY_MANIFEST is required",
        "PARITY_QUERIES is not supported",
        "command -v python3",
        "command -v node",
        "scripts/capture_parity_reports.py",
        "tools/g4-capture/scripts/capture.mjs",
        "scripts/capture_a11y_report.py",
        "tools/g4-capture/node_modules",
    ):
        assert required in out, f"preflight gate missing: {required!r}\n{out}"


def test_make_parity_preflight_missing_python3_aborts(tmp_path):
    """`python3` absent from PATH → preflight gate aborts fail-closed
    BEFORE any producer runs. PATH is hermetic (shim dir only)."""
    shim = _shim_dir(tmp_path, with_python3=False, with_node=True)
    r = _make("parity", env={"PATH": str(shim), **_env(tmp_path)},
              make_path=_system_make())
    assert r.returncode != 0, r.stdout + r.stderr
    assert "python3" in (r.stdout + r.stderr).lower()
    log = _shim_log(tmp_path)
    for name in ("capture_parity_reports.py", "capture.mjs", "capture_a11y_report.py"):
        assert name not in log, f"{name} ran despite python3 missing:\n{log}"


def test_make_parity_preflight_missing_node_aborts(tmp_path):
    """`node` absent from PATH → preflight gate aborts fail-closed
    BEFORE any producer runs. PATH is hermetic."""
    shim = _shim_dir(tmp_path, with_python3=True, with_node=False)
    r = _make("parity", env={"PATH": str(shim), **_env(tmp_path)},
              make_path=_system_make())
    assert r.returncode != 0, r.stdout + r.stderr
    assert "node" in (r.stdout + r.stderr).lower()
    log = _shim_log(tmp_path)
    for name in ("capture_parity_reports.py", "capture.mjs", "capture_a11y_report.py"):
        assert name not in log, f"{name} ran despite node missing:\n{log}"


# ── Producer-failure stop (atomicity boundaries) ─────────────────────


def test_make_parity_producer_failure_stops_later_producers(tmp_path):
    """First producer fails → capture.mjs and capture_a11y_report.py MUST NOT
    run. Component atomicity boundaries preserved; no partial-report success.
    Runs from a sandbox cwd so recipe's hardcoded relative paths resolve."""
    sandbox = _build_sandbox(tmp_path)
    shim_parent = tmp_path / "shim_parent"; shim_parent.mkdir()
    shim = _shim_dir(shim_parent, python_exit=5)
    r = _make("parity", env={"PATH": str(shim), **_env(sandbox)},
              cwd=sandbox, make_path=_system_make())
    assert r.returncode != 0, r.stdout + r.stderr
    log = _shim_log(shim_parent)
    assert "capture_parity_reports.py" in log, log
    assert "capture.mjs" not in log, f"lighthouse ran despite failure:\n{log}"
    assert "capture_a11y_report.py" not in log, f"a11y ran despite failure:\n{log}"


def test_make_parity_all_components_succeed_in_order(tmp_path):
    """TRIANGULATE: every shim returns 0 → the three producers run in the
    documented order with the documented flags."""
    sandbox = _build_sandbox(tmp_path)
    shim_parent = tmp_path / "shim_parent"; shim_parent.mkdir()
    shim = _shim_dir(shim_parent)
    r = _make("parity", env={"PATH": str(shim), **_env(sandbox)},
              cwd=sandbox, make_path=_system_make())
    assert r.returncode == 0, r.stdout + r.stderr
    log = _shim_log(shim_parent)
    nav_pos = log.find("capture_parity_reports.py")
    lh_pos = log.find("capture.mjs")
    a11y_pos = log.find("capture_a11y_report.py")
    assert nav_pos >= 0 and lh_pos >= 0 and a11y_pos >= 0, log
    assert nav_pos < lh_pos < a11y_pos, (
        f"order violated: nav={nav_pos} lh={lh_pos} a11y={a11y_pos}\n{log}")
    a11y_line = log[log.index("python3 scripts/capture_a11y_report.py"):].splitlines()[0]
    assert "--evidence" in a11y_line and "evidence.json" in a11y_line


def test_make_parity_quotes_caller_vars_against_shell_injection(tmp_path):
    """Controlled-shell proof: PARITY_URL, PARITY_OUT, PARITY_MANIFEST
    are quoted at the shell boundary on the producer chain. Same
    payload injected into all three — if any site is unquoted, bash
    splits at ``;`` and runs the trailing ``touch``.
    (a) ``make -n`` preserves the payload inside ``"..."`` (ONE argv).
    (b) Real controlled-shell run MUST NOT create the leak-marker."""
    payload = f"http://x.invalid; touch {tmp_path}/leak-marker; echo"
    env_all = {"PARITY_URL": payload, "PARITY_OUT": payload,
               "PARITY_MANIFEST": payload}
    # (a) Dry-run preserves the quoted form.
    r_dry = _make("-n", "parity", env=_env(tmp_path, **env_all))
    assert r_dry.returncode == 0, r_dry.stderr
    assert f'"{payload}"' in r_dry.stdout, r_dry.stdout
    # (b) Real shell run — the injected `touch` MUST NOT execute.
    sandbox = _build_sandbox(tmp_path)
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _shim_dir(shim_parent)
    r = _make("parity", env={"PATH": str(shim), **_env(sandbox, **env_all)},
              cwd=sandbox, make_path=_system_make())
    assert not (tmp_path / "leak-marker").exists(), r.stderr
