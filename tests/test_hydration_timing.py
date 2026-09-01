"""
Hydration timing tests for the legacy `taxa` frontend.

PR 1 (evidence-only slice) records the legacy hydration profile
(tree first-paint vs server-shell) so the design phase can close
`scope-decisions.md::§1` with a concrete answer to the third
blocking measurement in `design.md` §Open Questions:

    "Hydration cost on `taxonomy/tree`: SSR empty-tree vs first-paint
     client tree. RED test in `tests/test_hydration.py` (no console
     `hydration` warnings under Playwright)."

The legacy `taxa` app is NOT a hydration-based React app — it's a
vanilla ES module pipeline that `app.js::boot()` runs after
parsing. There's no SSR vs client-hydrate delta because there's no
SSR. PR 1's job is to record:

    1. Server-shell first-paint time (the legacy `web/index.html`
       static body painted before any `<script type="module">` runs).
    2. Tree first-paint time (the legacy `tree.js` pipeline's first
       render of `<div id="tree-view">`).
    3. The delta between (1) and (2). This is the analogue of
       "hydration cost" for a vanilla app: how much latency the
       client-side render pipeline adds on top of the static shell.

The script `scripts/measure_hydration.py` reads from a captured
JSON artifact (the schema is pinned here) and emits a console
table; PR 1's tests pin the schema and assert the script exits
zero on a valid artifact.

Reference:
  openspec/changes/migrate-nextjs-tailwind4/tasks.md  §Phase 1 (1.3)
  openspec/changes/migrate-nextjs-tailwind4/design.md §Open Questions
                                              (Hydration cost on taxonomy/tree)
  openspec/changes/migrate-nextjs-tailwind4/design.md §Testing Strategy
                                              (Browser-state console check)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "measure_hydration.py"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def hydration_artifact(tmp_path: Path) -> Path:
    """Synthetic hydration JSON artifact for the legacy `taxa` app.

    PR 3's Playwright + Lighthouse sample will populate this from the
    migrated build; PR 1's job is to pin the schema so the design
    phase has a stable shape to cite when closing §1.
    """
    fixture = tmp_path / "hydration.json"
    fixture.write_text(
        json.dumps(
            {
                "captured_at": "2026-08-28T00:00:00Z",
                "build": "legacy",
                "route": "/",
                "server_shell": {
                    "first_paint_ms": 80.0,        # the static HTML body
                    "dom_content_loaded_ms": 100.0,
                },
                "client_render": {
                    # tree.js + app.js::boot() until <div id="tree-view">
                    # has at least one child node.
                    "tree_first_paint_ms": 220.0,
                    "tree_first_interactive_ms": 350.0,
                },
                "console_warnings": [],  # legacy emits no "hydration" warning
            },
            indent=2,
        )
    )
    return fixture


@pytest.fixture()
def hydration_artifact_with_warnings(tmp_path: Path) -> Path:
    """Synthetic artifact with a hydration-style console warning.

    Used by the negative-path test to pin the script's behavior when
    the captured data carries a `hydration` warning — PR 4's gate
    fails on the migrated app if it emits one.
    """
    fixture = tmp_path / "hydration-warn.json"
    fixture.write_text(
        json.dumps(
            {
                "captured_at": "2026-08-28T00:00:00Z",
                "build": "migrated",
                "route": "/",
                "server_shell": {
                    "first_paint_ms": 60.0,
                    "dom_content_loaded_ms": 80.0,
                },
                "client_render": {
                    "tree_first_paint_ms": 180.0,
                    "tree_first_interactive_ms": 300.0,
                },
                "console_warnings": [
                    "Warning: Text content did not match. "
                    "Server: %s Client: %s",
                ],
            },
            indent=2,
        )
    )
    return fixture


# ---------------------------------------------------------------------------
# Test the script
# ---------------------------------------------------------------------------
def _run_script(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_measure_hydration_script_exists():
    """scripts/measure_hydration.py must exist (pinned in tasks.md 1.3)."""
    assert SCRIPT.exists(), f"missing hydration measurement script: {SCRIPT}"


def test_measure_hydration_exits_zero_on_valid_artifact(hydration_artifact: Path):
    """The script must exit zero when given a valid hydration JSON.

    PR 1 evidence capture uses this script to validate the artifact
    schema before recording it in `scope-decisions.md::§1`.
    """
    result = _run_script(str(hydration_artifact))
    assert result.returncode == 0, (
        f"measure_hydration.py exited {result.returncode} on a valid "
        f"artifact.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_measure_hydration_exits_nonzero_on_missing_file(tmp_path: Path):
    """Negative path: a missing artifact must abort with non-zero exit
    and a clear stderr — PR 3's CI cannot silently accept an absent
    hydration capture.
    """
    missing = tmp_path / "no-such-hydration.json"
    result = _run_script(str(missing))
    assert result.returncode != 0, (
        f"script should fail on missing artifact; got exit="
        f"{result.returncode}.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert result.stderr.strip(), "script must write a diagnostic to stderr"


def test_measure_hydration_reports_delta(hydration_artifact: Path):
    """The script must report the client-vs-server delta in human-readable
    form (e.g. print the tree_first_paint_ms minus first_paint_ms) so
    the design phase can quote the number verbatim in §1.
    """
    result = _run_script(str(hydration_artifact))
    assert result.returncode == 0, result.stderr
    # tree_first_paint_ms=220, first_paint_ms=80 → delta 140ms.
    # The script is allowed to format this however it likes (table, json,
    # plain text); the contract is that the number 140 appears in stdout.
    output = result.stdout + result.stderr
    assert "140" in output, (
        f"script must report the 140ms client-vs-server delta; got:\n"
        f"{output}"
    )


def test_measure_hydration_flags_console_warnings(
    hydration_artifact_with_warnings: Path,
):
    """The script must flag any `hydration` console warnings — the
    negative-path gate for PR 4's `tests/test_hydration_console.py`
    (Playwright) is: zero warnings on the migrated build.
    """
    result = _run_script(str(hydration_artifact_with_warnings))
    # Exit zero is fine — the script is informational. The contract is
    # that it MUST surface the warning in its output so a reviewer
    # notices it during §1 evidence review.
    output = (result.stdout + result.stderr).lower()
    assert "warning" in output or "hydration" in output, (
        f"script must surface console_warnings in its output; got:\n"
        f"{result.stdout}\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# Schema contract
# ---------------------------------------------------------------------------
def test_hydration_artifact_schema_keys_present(hydration_artifact: Path):
    """Pin the schema that PR 3's Playwright + Lighthouse sample must
    populate. The contract keys are the ones design cites in
    `scope-decisions.md::§1` evidence.
    """
    doc = json.loads(hydration_artifact.read_text())
    for key in (
        "captured_at",
        "build",
        "route",
        "server_shell",
        "client_render",
        "console_warnings",
    ):
        assert key in doc, f"hydration artifact missing key {key!r}"


def test_hydration_artifact_server_shell_keys(hydration_artifact: Path):
    """server_shell must record first_paint_ms and dom_content_loaded_ms.

    `first_paint_ms` is the analogue of the migrated app's SSR
    shell-first-paint. `dom_content_loaded_ms` is the moment the
    static body is fully parsed. Both are cited by design in §1.
    """
    doc = json.loads(hydration_artifact.read_text())
    shell = doc["server_shell"]
    assert "first_paint_ms" in shell, "server_shell.first_paint_ms missing"
    assert "dom_content_loaded_ms" in shell, (
        "server_shell.dom_content_loaded_ms missing"
    )
    for key, val in shell.items():
        assert isinstance(val, (int, float)) and val >= 0, (
            f"server_shell.{key} must be non-negative numeric; got {val!r}"
        )


def test_hydration_artifact_client_render_keys(hydration_artifact: Path):
    """client_render must record tree_first_paint_ms and
    tree_first_interactive_ms.

    `tree_first_paint_ms` is the moment `<div id="tree-view">` has at
    least one child node. `tree_first_interactive_ms` is the moment
    click handlers are wired up. The delta from `first_paint_ms` is
    the legacy analogue of "hydration cost".
    """
    doc = json.loads(hydration_artifact.read_text())
    render = doc["client_render"]
    assert "tree_first_paint_ms" in render, (
        "client_render.tree_first_paint_ms missing"
    )
    assert "tree_first_interactive_ms" in render, (
        "client_render.tree_first_interactive_ms missing"
    )
    for key, val in render.items():
        assert isinstance(val, (int, float)) and val >= 0, (
            f"client_render.{key} must be non-negative numeric; "
            f"got {val!r}"
        )


def test_hydration_artifact_console_warnings_is_a_list(
    hydration_artifact: Path,
):
    """console_warnings must be a list of strings (possibly empty).

    PR 4's gate is "zero hydration warnings"; the schema records
    the captured list verbatim so PR 1's evidence is reviewable.
    """
    doc = json.loads(hydration_artifact.read_text())
    warnings = doc["console_warnings"]
    assert isinstance(warnings, list), (
        f"console_warnings must be a list; got {type(warnings).__name__}"
    )
    for w in warnings:
        assert isinstance(w, str), (
            f"each console warning must be a string; got {w!r}"
        )


def test_measure_hydration_exits_nonzero_on_malformed_json(tmp_path: Path):
    """Triangulation: malformed JSON must abort with a non-zero exit
    and a clear stderr message — a partial capture that PR 3's CI
    silently accepted would be worse than a hard failure.

    Real behavior: exit code 3 (the documented "schema violation"
    code path, since a non-JSON root fails the JSON parse before
    the schema check).
    """
    bad = tmp_path / "bad.json"
    bad.write_text("{ not: valid json ")
    result = _run_script(str(bad))
    assert result.returncode != 0, (
        f"script should fail on malformed JSON; got exit={result.returncode}"
    )
    assert "parse" in result.stderr.lower() or "json" in result.stderr.lower(), (
        f"stderr should mention JSON parsing; got:\n{result.stderr}"
    )


def test_measure_hydration_exits_nonzero_on_schema_violation(tmp_path: Path):
    """Triangulation: a JSON object that loads but is missing required
    top-level keys must fail with exit code 3 (schema violation).

    Catches a regression where the script silently accepts an
    incomplete capture (e.g. PR 3's Playwright run timed out before
    recording `console_warnings`).
    """
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(
        json.dumps(
            {
                "captured_at": "2026-08-28T00:00:00Z",
                "build": "legacy",
                # route, server_shell, client_render, console_warnings omitted
            }
        )
    )
    result = _run_script(str(incomplete))
    assert result.returncode != 0, (
        f"script should fail on incomplete schema; got exit="
        f"{result.returncode}"
    )
    # Stderr should enumerate the missing keys.
    stderr = result.stderr.lower()
    assert "schema" in stderr or "missing" in stderr, (
        f"stderr should mention schema violation; got:\n{result.stderr}"
    )



# ---------------------------------------------------------------------------
# G5 CLI precondition contract (design.md §3.3.5)
# ---------------------------------------------------------------------------
# Required flags: --baseline, --candidate, --iterations 10 (all three
# together). On any precondition failure the script exits non-zero,
# emits no comparison artifact, and never claims G5 pass. Capture and
# delta calculation land in later slices.
G5_EXPECTED_ITERATIONS = 10


@pytest.fixture()
def g5_baseline_json(tmp_path: Path) -> Path:
    p = tmp_path / "baseline.json"
    p.write_text("{}\n", encoding="utf-8")
    return p


@pytest.fixture()
def g5_candidate_root(tmp_path: Path) -> Path:
    root = tmp_path / "candidate"
    root.mkdir()
    return root


def _run_g5(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False)


def _parity_reports_hydration() -> list[Path]:
    base = REPO_ROOT / "parity-reports"
    return sorted(base.rglob("hydration.json")) if base.exists() else []


def test_g5_cli_requires_all_three_flags_together():
    """Zero G5 flags must fail closed; no artifact; no G5 pass claim."""
    before = _parity_reports_hydration()
    result = _run_g5()
    after = _parity_reports_hydration()
    assert result.returncode != 0, f"expected non-zero; got {result.returncode}"
    assert "g5 pass" not in (result.stdout + result.stderr).lower()
    assert after == before, f"hydration artifact emitted: {after}"


def test_g5_cli_iterations_must_equal_ten(
    g5_baseline_json: Path, g5_candidate_root: Path,
):
    """--iterations must be exactly 10; any other value fails closed."""
    before = _parity_reports_hydration()
    result = _run_g5(
        "--baseline", str(g5_baseline_json),
        "--candidate", str(g5_candidate_root),
        "--iterations", "5",
    )
    after = _parity_reports_hydration()
    assert result.returncode != 0, f"expected non-zero; got {result.returncode}"
    combined = (result.stdout + result.stderr).lower()
    assert "10" in combined, f"must mention required iterations=10; got {combined!r}"
    assert "g5 pass" not in combined
    assert after == before, f"hydration artifact emitted: {after}"


def test_g5_cli_baseline_must_exist(
    g5_candidate_root: Path, tmp_path: Path,
):
    """--baseline must point at an existing file on disk."""
    before = _parity_reports_hydration()
    result = _run_g5(
        "--baseline", str(tmp_path / "no-such-baseline.json"),
        "--candidate", str(g5_candidate_root),
        "--iterations", "10",
    )
    after = _parity_reports_hydration()
    assert result.returncode != 0, f"expected non-zero; got {result.returncode}"
    combined = (result.stdout + result.stderr).lower()
    assert "baseline" in combined, f"must mention baseline; got {combined!r}"
    assert "g5 pass" not in combined
    assert after == before, f"hydration artifact emitted: {after}"


def test_g5_cli_candidate_must_exist(
    g5_baseline_json: Path, tmp_path: Path,
):
    """--candidate must point at an existing build-root directory."""
    before = _parity_reports_hydration()
    result = _run_g5(
        "--baseline", str(g5_baseline_json),
        "--candidate", str(tmp_path / "no-such-candidate"),
        "--iterations", "10",
    )
    after = _parity_reports_hydration()
    assert result.returncode != 0, f"expected non-zero; got {result.returncode}"
    combined = (result.stdout + result.stderr).lower()
    assert "candidate" in combined, f"must mention candidate; got {combined!r}"
    assert "g5 pass" not in combined
    assert after == before, f"hydration artifact emitted: {after}"


def test_g5_cli_preconditions_pass_does_not_claim_g5_pass(
    g5_baseline_json: Path, g5_candidate_root: Path,
):
    """TRIANGULATE: with all preconditions met, the slice must NOT claim
    G5 pass and must NOT emit a comparison artifact.

    The precondition slice only validates CLI surface; capture, raw
    evidence schema, and delta calculation land in later slices.
    """
    before = _parity_reports_hydration()
    result = _run_g5(
        "--baseline", str(g5_baseline_json),
        "--candidate", str(g5_candidate_root),
        "--iterations", "10",
    )
    after = _parity_reports_hydration()
    combined = (result.stdout + result.stderr).lower()
    assert "g5 pass" not in combined, f"must not claim G5 pass; got {combined!r}"
    assert after == before, f"hydration artifact emitted: {after}"


# --- TRIANGULATE: invalid combinations of the G5 flag trio --------------
def test_g5_cli_only_one_flag_fails_closed(
    g5_baseline_json: Path, g5_candidate_root: Path,
):
    """TRIANGULATE: providing one of three G5 flags must fail closed
    (not silently default to legacy mode or auto-fill the others)."""
    before = _parity_reports_hydration()
    result = _run_g5("--baseline", str(g5_baseline_json))
    after = _parity_reports_hydration()
    assert result.returncode != 0, f"single flag must fail closed; got {result.returncode}"
    assert "g5 pass" not in (result.stdout + result.stderr).lower()
    assert after == before, f"hydration artifact emitted: {after}"


def test_g5_cli_two_of_three_flags_fails_closed(
    g5_baseline_json: Path, g5_candidate_root: Path,
):
    """TRIANGULATE: two of three flags (missing --iterations) must fail
    closed. The contract is that the three flags MUST appear together."""
    before = _parity_reports_hydration()
    result = _run_g5(
        "--baseline", str(g5_baseline_json),
        "--candidate", str(g5_candidate_root),
    )
    after = _parity_reports_hydration()
    assert result.returncode != 0, f"two flags must fail closed; got {result.returncode}"
    assert "g5 pass" not in (result.stdout + result.stderr).lower()
    assert after == before, f"hydration artifact emitted: {after}"


def test_g5_cli_baseline_must_be_file_not_directory(
    g5_candidate_root: Path, tmp_path: Path,
):
    """TRIANGULATE: --baseline pointing at a directory (not a regular
    file) must fail closed. The contract is baseline is a JSON file."""
    baseline_dir = tmp_path / "baseline-is-a-dir"
    baseline_dir.mkdir()
    before = _parity_reports_hydration()
    result = _run_g5(
        "--baseline", str(baseline_dir),
        "--candidate", str(g5_candidate_root),
        "--iterations", "10",
    )
    after = _parity_reports_hydration()
    assert result.returncode != 0, f"dir-as-baseline must fail closed; got {result.returncode}"
    assert "g5 pass" not in (result.stdout + result.stderr).lower()
    assert after == before, f"hydration artifact emitted: {after}"


def test_g5_cli_legacy_positional_path_preserved(hydration_artifact: Path):
    """TRIANGULATE: the legacy positional CLI path must remain intact
    after the G5 slice is added. The script must still validate a
    positional hydration JSON artifact and exit zero on a valid one.
    """
    result = _run_g5(str(hydration_artifact))
    assert result.returncode == 0, (
        f"legacy positional path broken by G5 slice; "
        f"got exit={result.returncode}, stderr={result.stderr}"
    )
