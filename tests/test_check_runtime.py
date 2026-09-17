"""Node runtime contract tests for `scripts/check-runtime.mjs` (PR 3a task 3a.6).

Mocks `process.versions.node` via `scripts/_test-check-runtime.mjs` (preloaded
with `node --import`) and asserts exit codes for both below-floor and
at/above-floor scenarios. The floor is read from `package.json::engines.node`
per the 3a.8 refactor.
"""
from __future__ import annotations
import os, re, shutil, subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECK_RUNTIME_SCRIPT = REPO_ROOT / "scripts" / "check-runtime.mjs"
TEST_OVERRIDE_SCRIPT = REPO_ROOT / "scripts" / "_test-check-runtime.mjs"
REQUIRED_NODE_FLOOR = "20.9.0"
NODE_VERSION_BELOW_FLOOR = "20.0.0"
NODE_VERSION_AT_FLOOR = "20.9.0"
NODE_VERSION_ABOVE_FLOOR = "21.0.0"

def _has_node() -> bool: return shutil.which("node") is not None

def _run_check_runtime(version_override: str | None) -> subprocess.CompletedProcess:
    """Invoke `scripts/check-runtime.mjs` with optional version mock."""
    if not _has_node(): pytest.skip("`node` not on PATH; skipping runtime harness test")
    if not CHECK_RUNTIME_SCRIPT.is_file(): pytest.fail(f"check-runtime.mjs missing at {CHECK_RUNTIME_SCRIPT}")
    if not TEST_OVERRIDE_SCRIPT.is_file(): pytest.fail(f"_test-check-runtime.mjs missing at {TEST_OVERRIDE_SCRIPT}")
    cmd = ["node", "--import", str(TEST_OVERRIDE_SCRIPT), str(CHECK_RUNTIME_SCRIPT)]
    env = os.environ.copy()
    if version_override is None: env.pop("TAXA_TEST_NODE_VERSION_OVERRIDE", None)
    else: env["TAXA_TEST_NODE_VERSION_OVERRIDE"] = version_override
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=30)


def test_check_runtime_script_exists():
    assert CHECK_RUNTIME_SCRIPT.is_file(), (
        f"check-runtime.mjs missing at {CHECK_RUNTIME_SCRIPT}. PR 3a task 3a.3 must create it."
    )

def test_test_override_script_exists():
    assert TEST_OVERRIDE_SCRIPT.is_file(), (
        f"_test-check-runtime.mjs missing at {TEST_OVERRIDE_SCRIPT}. PR 3a task 3a.6 must create it."
    )

def test_check_runtime_script_reads_floor_from_package_json():
    """REFACTORED (3a.8): script MUST read package.json::engines.node, NOT a hardcoded literal."""
    if not CHECK_RUNTIME_SCRIPT.is_file(): pytest.skip("check-runtime.mjs not present yet")
    source = CHECK_RUNTIME_SCRIPT.read_text(encoding="utf-8")
    assert "engines" in source and "node" in source, (
        "check-runtime.mjs must reference 'engines.node' (parse from package.json)."
    )
    assert "package.json" in source, "check-runtime.mjs must read package.json"
    # No hardcoded floor literal as a constant.
    hardcoded_pattern = re.compile(
        r'(?:const|let|var)\s+REQUIRED_NODE\s*=\s*["\']' + re.escape(REQUIRED_NODE_FLOOR) + r'["\']'
    )
    assert not hardcoded_pattern.search(source), (
        f"check-runtime.mjs must NOT hardcode the floor as a constant; "
        f"the 3a.8 refactor requires deriving it from package.json."
    )

def test_check_runtime_exits_nonzero_below_floor():
    """Below the floor: script MUST exit non-zero AND stderr names the observed version + required floor."""
    result = _run_check_runtime(NODE_VERSION_BELOW_FLOOR)
    assert result.returncode != 0, (
        f"check-runtime.mjs must exit non-zero below {REQUIRED_NODE_FLOOR}; "
        f"got exit={result.returncode}. stderr={result.stderr!r}"
    )
    assert NODE_VERSION_BELOW_FLOOR in result.stderr, (
        f"stderr must name the observed version {NODE_VERSION_BELOW_FLOOR}; got {result.stderr!r}."
    )
    assert REQUIRED_NODE_FLOOR in result.stderr, (
        f"stderr must name the required floor {REQUIRED_NODE_FLOOR}; got {result.stderr!r}."
    )

def test_check_runtime_exits_zero_at_floor():
    """Exactly 20.9.0 (the pinned floor): script MUST exit zero (floor is inclusive)."""
    result = _run_check_runtime(NODE_VERSION_AT_FLOOR)
    assert result.returncode == 0, (
        f"check-runtime.mjs must exit zero at the floor {REQUIRED_NODE_FLOOR}; "
        f"got exit={result.returncode}. stderr={result.stderr!r}"
    )

def test_check_runtime_exits_zero_above_floor():
    """Above 20.9.0 (e.g. 21.0.0): script MUST exit zero (floor is inclusive)."""
    result = _run_check_runtime(NODE_VERSION_ABOVE_FLOOR)
    assert result.returncode == 0, (
        f"check-runtime.mjs must exit zero above the floor {REQUIRED_NODE_FLOOR}; "
        f"got exit={result.returncode}. stderr={result.stderr!r}"
    )

def test_check_runtime_works_against_real_node():
    """`node scripts/check-runtime.mjs` (no override) MUST exit zero on the real host Node."""
    if not _has_node(): pytest.skip("`node` not on PATH")
    real_node_version = subprocess.check_output(["node", "--version"], text=True).strip()
    env = {k: v for k, v in os.environ.items() if k != "TAXA_TEST_NODE_VERSION_OVERRIDE"}
    result = subprocess.run(
        ["node", str(CHECK_RUNTIME_SCRIPT)],
        capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=30,
    )
    assert result.returncode == 0, (
        f"check-runtime.mjs must exit zero on the real host Node {real_node_version}; "
        f"got exit={result.returncode}. stderr={result.stderr!r}"
    )