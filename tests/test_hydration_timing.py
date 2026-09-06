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
import os
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
# Phase 6a -- G5 hydration baseline closure
# ---------------------------------------------------------------------------
#
# Authoritative Phase 6a contract:
#   * measure_hydration.py accepts BOTH the legacy single-positional
#     invocation AND a new `--baseline <path> --candidate <path>` mode
#     that emits a regression report.
#   * `--baseline` + `--candidate` exits 0 only when BOTH metrics
#     (initial paint, interaction latency) regress <= 0 %. Anything
#     else is fail-closed (exit code 4, never silently green).
#   * `--report-out <path>` writes a machine-readable JSON report so
#     the apply worker can attach it to apply-progress.md without
#     parsing stdout.
#   * reconstruct_hydration_baseline.py emits a schema-conformant
#     artifact OR fails closed with a clearly-labelled blocker when
#     Playwright/Chromium is unavailable (never fabricates numbers).
#   * g5_close.sh is the runtime harness: it must be executable,
#     must write versioned evidence under
#     `openspec/changes/complete-taxa-frontend-migration/evidence/g5/`,
#     and must record an environmental blocker in `status.json`
#     when capture cannot run (G5 stays blocked).
#
# These tests pin the harness contract. None of them fabricate real
# numbers; the captured artifact fixtures below are schema-correct
# test inputs (NOT evidence).
RECONSTRUCT_SCRIPT = REPO_ROOT / "scripts" / "reconstruct_hydration_baseline.py"
CANDIDATE_CAPTURE_SCRIPT = REPO_ROOT / "scripts" / "capture_hydration_candidate.py"
G5_CLOSE_SH = REPO_ROOT / "scripts" / "g5_close.sh"
G5_EVIDENCE_DIR = (
    REPO_ROOT
    / "openspec"
    / "changes"
    / "complete-taxa-frontend-migration"
    / "evidence"
    / "g5"
)


def _poisoned_env(tmp_path: Path) -> dict:
    """Return a subprocess env that shadows the system playwright package
    with an ImportError-raising stub so the subprocess fails-closed on
    any script that tries `import playwright`.

    Mirrors the approach used by the
    ``test_reconstruct_hydration_baseline_fails_closed_without_playwright``
    test; centralised here so the candidate-capture + g5_close.sh
    tests share the same rig. ``tmp_path`` must already exist.
    """
    poison = tmp_path / "playwright_poison"
    poison.mkdir(exist_ok=True)
    (poison / "playwright.py").write_text(
        "raise ImportError(\n"
        "    'playwright hidden by test poison env'\n"
        ")\n"
    )
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
        "PYTHONPATH": str(poison),
        "PYTHONNOUSERSITE": "1",
    }


def _write_artifact(
    path: Path,
    *,
    build: str,
    first_paint_ms: float,
    tree_first_paint_ms: float,
    tree_first_interactive_ms: float,
    dom_content_loaded_ms: float | None = None,
) -> None:
    """Helper: emit a schema-conformant hydration artifact to `path`.

    Defaults `dom_content_loaded_ms` to first_paint_ms + 20 so callers
    only have to vary the metrics under test. This fixture is for
    SCRIPT CONTRACTS only -- never cited as real G5 evidence.
    """
    if dom_content_loaded_ms is None:
        dom_content_loaded_ms = first_paint_ms + 20.0
    path.write_text(
        json.dumps(
            {
                "captured_at": "2026-09-05T00:00:00Z",
                "build": build,
                "route": "/",
                "server_shell": {
                    "first_paint_ms": first_paint_ms,
                    "dom_content_loaded_ms": dom_content_loaded_ms,
                },
                "client_render": {
                    "tree_first_paint_ms": tree_first_paint_ms,
                    "tree_first_interactive_ms": tree_first_interactive_ms,
                },
                "console_warnings": [],
            },
            indent=2,
        )
    )


# measure_hydration.py -- baseline / candidate flag mode -------------------


def test_measure_hydration_back_compat_single_positional_artifact(
    hydration_artifact: Path,
):
    """Back-compat: the legacy `script <path>` invocation must still
    exit 0 against a single artifact. Phase 6a extends the script but
    MUST NOT break PR 1b.3b's caller contract.
    """
    result = _run_script(str(hydration_artifact))
    assert result.returncode == 0, (
        f"single-positional invocation must keep working; got exit={result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # The original "delta_server_to_tree_first_paint_ms" header must
    # still appear (regression guard for the human-readable report).
    assert "delta_server_to_tree_first_paint_ms" in result.stdout, (
        f"back-compat report missing legacy header; got:\n{result.stdout}"
    )


def test_measure_hydration_baseline_candidate_emits_delta_report(tmp_path: Path):
    """When `--baseline` + `--candidate` are both supplied, the script
    must exit 0 (assuming no regression) and emit a comparison report
    naming BOTH the initial-paint delta and the interaction-latency
    delta. The contract is the report is in stdout so the apply
    worker can quote it verbatim in apply-progress.md.
    """
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_artifact(
        baseline,
        build="legacy",
        first_paint_ms=80.0,
        tree_first_paint_ms=220.0,
        tree_first_interactive_ms=350.0,
    )
    _write_artifact(
        candidate,
        build="migrated",
        first_paint_ms=80.0,
        tree_first_paint_ms=220.0,
        tree_first_interactive_ms=350.0,
    )
    result = _run_script(
        "--baseline", str(baseline), "--candidate", str(candidate),
    )
    assert result.returncode == 0, (
        f"baseline/candidate with 0% delta must exit 0; got "
        f"{result.returncode}.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    out = result.stdout + result.stderr
    assert "initial_paint" in out, (
        f"report must name initial_paint metric; got:\n{out}"
    )
    assert "interaction_latency" in out, (
        f"report must name interaction_latency metric; got:\n{out}"
    )


def test_measure_hydration_baseline_candidate_fails_closed_on_regression(
    tmp_path: Path,
):
    """FAIL-CLOSED core contract: when the candidate regresses > 0% on
    EITHER initial paint OR interaction latency, the script MUST exit
    non-zero with code 4 and surface the regression in stderr/stdout.
    """
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_artifact(
        baseline,
        build="legacy",
        first_paint_ms=80.0,
        tree_first_paint_ms=220.0,
        tree_first_interactive_ms=350.0,
    )
    # Candidate regresses +18% on tree_first_paint (260 vs 220).
    _write_artifact(
        candidate,
        build="migrated",
        first_paint_ms=80.0,
        tree_first_paint_ms=260.0,
        tree_first_interactive_ms=350.0,
    )
    result = _run_script(
        "--baseline", str(baseline), "--candidate", str(candidate),
    )
    assert result.returncode != 0, (
        f"baseline/candidate with regression MUST fail closed; got "
        f"exit={result.returncode}.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert result.returncode == 4, (
        f"regression exit code must be 4; got {result.returncode}.\n"
        f"stderr: {result.stderr}"
    )
    diag = (result.stdout + result.stderr).lower()
    assert "regression" in diag or "initial_paint" in diag, (
        f"regression diagnostic must name the regressing metric; got:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_measure_hydration_baseline_candidate_passes_on_improvement(
    tmp_path: Path,
):
    """Negative-axis triangulation: a candidate BETTER than baseline
    (negative delta) must exit 0.
    """
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_artifact(
        baseline,
        build="legacy",
        first_paint_ms=80.0,
        tree_first_paint_ms=220.0,
        tree_first_interactive_ms=350.0,
    )
    _write_artifact(
        candidate,
        build="migrated",
        first_paint_ms=60.0,
        tree_first_paint_ms=180.0,
        tree_first_interactive_ms=280.0,
    )
    result = _run_script(
        "--baseline", str(baseline), "--candidate", str(candidate),
    )
    assert result.returncode == 0, (
        f"improved candidate must exit 0; got {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_measure_hydration_baseline_candidate_writes_json_report(tmp_path: Path):
    """`--report-out <path>` must write a machine-readable JSON report."""
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_artifact(
        baseline,
        build="legacy",
        first_paint_ms=80.0,
        tree_first_paint_ms=220.0,
        tree_first_interactive_ms=350.0,
    )
    _write_artifact(
        candidate,
        build="migrated",
        first_paint_ms=80.0,
        tree_first_paint_ms=220.0,
        tree_first_interactive_ms=350.0,
    )
    report = tmp_path / "report.json"
    result = _run_script(
        "--baseline", str(baseline),
        "--candidate", str(candidate),
        "--report-out", str(report),
    )
    assert result.returncode == 0, (
        f"identical inputs should exit 0; got {result.returncode}.\n"
        f"stderr: {result.stderr}"
    )
    assert report.exists(), (
        f"--report-out did not write {report}.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    doc = json.loads(report.read_text())
    for key in ("initial_paint_delta_pct", "interaction_latency_delta_pct"):
        assert key in doc, f"report missing key {key!r}; got: {doc}"
        assert isinstance(doc[key], (int, float)), (
            f"report[{key!r}] must be numeric; got {type(doc[key]).__name__}"
        )
    assert "regression" in doc, f"report must carry regression verdict; got: {doc}"
    assert doc["regression"] is False, (
        f"identical inputs must report regression=false; got: {doc}"
    )


def test_measure_hydration_baseline_candidate_requires_both_flags(tmp_path: Path):
    """Fail-closed on misuse."""
    one = tmp_path / "one.json"
    _write_artifact(
        one, build="legacy",
        first_paint_ms=80.0,
        tree_first_paint_ms=220.0,
        tree_first_interactive_ms=350.0,
    )
    result = _run_script("--baseline", str(one))
    assert result.returncode != 0, (
        f"only --baseline must fail closed; got exit={result.returncode}"
    )
    assert "delta_server_to_tree_first_paint_ms" not in result.stdout, (
        f"single-flag invocation must not print legacy single-artifact "
        f"header; got:\n{result.stdout}"
    )


# reconstruct_hydration_baseline.py ----------------------------------------


def test_reconstruct_hydration_baseline_script_exists():
    """Phase 6a ships scripts/reconstruct_hydration_baseline.py."""
    assert RECONSTRUCT_SCRIPT.exists(), (
        f"missing reconstruction script: {RECONSTRUCT_SCRIPT}"
    )


def test_reconstruct_hydration_baseline_fails_closed_without_playwright(
    tmp_path: Path,
):
    """The reconstruction harness must NEVER fabricate baseline numbers.
    When Playwright is unavailable it must exit non-zero and emit a
    schema-conformant artifact flagged with `source: 'unavailable'`.
    """
    poison = tmp_path / "playwright_poison"
    poison.mkdir()
    (poison / "playwright.py").write_text(
        "raise ImportError(\n"
        "    'playwright hidden by test '\n"
        "    'reconstruct_hydration_baseline_fails_closed_without_playwright'\n"
        ")\n"
    )

    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "index.html").write_text("<!doctype html><title>x</title>")

    out = tmp_path / "evidence-baseline.json"
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
        "PYTHONPATH": str(poison),
        "PYTHONNOUSERSITE": "1",
    }
    result = subprocess.run(
        [
            sys.executable, str(RECONSTRUCT_SCRIPT),
            "--fixture-web-root", str(fixture),
            "--out", str(out),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, (
        f"without playwright the harness MUST fail closed; got exit={result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert out.exists(), (
        f"placeholder artifact must be written even on failure; missing "
        f"{out}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    doc = json.loads(out.read_text())
    assert doc.get("source") == "unavailable", (
        f"placeholder must self-label as source='unavailable'; got: {doc}"
    )
    assert "playwright" in result.stderr.lower(), (
        f"stderr must name the playwright blocker; got:\n{result.stderr}"
    )


# scripts/g5_close.sh -- runtime harness ------------------------------------


def test_g5_close_sh_exists_and_is_executable():
    """The runtime harness must exist and be executable."""
    assert G5_CLOSE_SH.exists(), f"missing harness: {G5_CLOSE_SH}"
    import stat
    mode = G5_CLOSE_SH.stat().st_mode
    assert mode & stat.S_IXUSR, (
        f"{G5_CLOSE_SH} must carry user-execute bit; got mode={oct(mode)}"
    )


def test_g5_evidence_directory_present_with_gitkeep():
    """Versioned evidence directory must exist and be tracked via a
    `.gitkeep` marker."""
    assert G5_EVIDENCE_DIR.is_dir(), (
        f"versioned evidence directory missing: {G5_EVIDENCE_DIR}"
    )
    assert (G5_EVIDENCE_DIR / ".gitkeep").exists(), (
        f"evidence directory must carry a tracked .gitkeep marker; "
        f"missing: {G5_EVIDENCE_DIR / '.gitkeep'}"
    )


def test_g5_close_sh_records_environmental_blocker(tmp_path: Path):
    """When Playwright is unavailable, `g5_close.sh` must record the
    blocker in `evidence/g5/status.json` rather than fabricate closure.
    """
    env = _poisoned_env(tmp_path)
    env["G5_STATUS_JSON"] = str(tmp_path / "status.json")
    env["G5_REPORT_JSON"] = str(tmp_path / "report.json")

    result = subprocess.run(
        ["bash", str(G5_CLOSE_SH)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    status_path = Path(env["G5_STATUS_JSON"])
    assert status_path.exists(), (
        f"g5_close.sh must write status.json; missing {status_path}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}\n"
        f"exit: {result.returncode}"
    )
    doc = json.loads(status_path.read_text())
    assert "gate" in doc and doc["gate"] == "G5", (
        f"status.json must self-identify as gate='G5'; got: {doc}"
    )
    assert doc.get("status") == "blocked", (
        f"status.json must record G5 as blocked under the environmental "
        f"blocker; got: {doc}"
    )
    assert "blocker" in doc, (
        f"status.json must carry a 'blocker' field; got: {doc}"
    )


# ---------------------------------------------------------------------------
# scripts/capture_hydration_candidate.py -- React build candidate capture
# ---------------------------------------------------------------------------


def test_capture_hydration_candidate_script_exists():
    """Phase 6a ships scripts/capture_hydration_candidate.py."""
    assert CANDIDATE_CAPTURE_SCRIPT.exists(), (
        f"missing candidate capture script: {CANDIDATE_CAPTURE_SCRIPT}"
    )


def test_capture_hydration_candidate_fails_closed_without_playwright(
    tmp_path: Path,
):
    """The candidate capture harness must NEVER invent candidate numbers."""
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "index.html").write_text(
        "<!doctype html><html><body>candidate</body></html>"
    )
    out = tmp_path / "hydration-candidate.json"
    env = _poisoned_env(tmp_path)

    result = subprocess.run(
        [
            sys.executable, str(CANDIDATE_CAPTURE_SCRIPT),
            "--build-dir", str(build_dir),
            "--out", str(out),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, (
        f"without playwright the candidate capture MUST fail closed; "
        f"got exit={result.returncode}.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert out.exists(), (
        f"placeholder artifact must be written even on failure; "
        f"missing {out}.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    doc = json.loads(out.read_text())
    assert doc.get("source") == "unavailable", (
        f"placeholder must self-label as source='unavailable'; got: {doc}"
    )
    assert "playwright" in result.stderr.lower(), (
        f"stderr must name the playwright blocker; got:\n{result.stderr}"
    )


def test_capture_hydration_candidate_fails_closed_without_build_dir(
    tmp_path: Path,
):
    """When the candidate build directory is missing, the harness must
    fail closed without invoking Playwright.
    """
    out = tmp_path / "hydration-candidate.json"
    result = subprocess.run(
        [
            sys.executable, str(CANDIDATE_CAPTURE_SCRIPT),
            "--build-dir", str(tmp_path / "does-not-exist"),
            "--out", str(out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, (
        f"missing build_dir MUST fail closed; got exit={result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert out.exists(), (
        f"placeholder artifact must be written even on missing "
        f"build_dir; missing {out}.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    doc = json.loads(out.read_text())
    assert doc.get("source") == "unavailable", (
        f"placeholder must self-label as source='unavailable'; got: {doc}"
    )
    assert "build_dir" in doc.get("blocker", ""), (
        f"blocker must name the missing build_dir; got:\n{doc}"
    )


def test_g5_close_sh_blocks_when_candidate_is_placeholder(tmp_path: Path):
    """Triangulation: when the candidate artifact exists but its
    ``source`` is NOT ``"captured"``, the harness MUST NOT compare it
    against the baseline.
    """
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "captured_at": "2026-09-05T00:00:00Z",
                "build": "legacy",
                "route": "/",
                "server_shell": {
                    "first_paint_ms": 3.0,
                    "dom_content_loaded_ms": 18.0,
                },
                "client_render": {
                    "tree_first_paint_ms": 3.0,
                    "tree_first_interactive_ms": 18.0,
                },
                "console_warnings": [],
                "source": "captured",
            },
            indent=2,
        )
    )

    candidate = tmp_path / "candidate.json"
    candidate.write_text(
        json.dumps(
            {
                "captured_at": "2026-09-05T00:00:00Z",
                "build": "migrated",
                "route": "/",
                "server_shell": {
                    "first_paint_ms": 0.0,
                    "dom_content_loaded_ms": 0.0,
                },
                "client_render": {
                    "tree_first_paint_ms": 0.0,
                    "tree_first_interactive_ms": 0.0,
                },
                "console_warnings": [],
                "source": "unavailable",
                "blocker": "synthetic placeholder for the source-gate test",
            },
            indent=2,
        )
    )

    env = {
        # Put homebrew Python first on PATH so `python3` in the harness
        # resolves to the interpreter that has playwright installed.
        # Without this the harness falls back to /usr/bin/python3
        # which has no playwright package.
        "PATH": "/opt/homebrew/opt/python@3.14/bin:/usr/bin:/bin",
        # Use the real user HOME so playwright finds its chromium cache
        # (the binary lives under $HOME/Library/Caches/ms-playwright/
        # on macOS). tmp_path would point playwright at a non-existent
        # cache and the harness would fail at the binary probe.
        "HOME": os.environ.get("HOME", "/tmp"),
        "G5_FIXTURE_WEB_ROOT": str(tmp_path / "fixture"),
        "G5_OUT": str(baseline),
        "G5_CANDIDATE": str(candidate),
        "G5_STATUS_JSON": str(tmp_path / "status.json"),
        "G5_REPORT_JSON": str(tmp_path / "report.json"),
        # Carry PYTHONPATH so the subprocess uses the same Python
        # interpreter + site-packages that the parent pytest has
        # (otherwise the harness falls back to /usr/bin/python3 which
        # has no playwright install).
        "PYTHONPATH": ":".join(
            [
                # User site-packages (where pip-installed playwright lives)
                "/Users/sebailla/Library/Python/3.14/lib/python/site-packages",
                # Homebrew + framework site-packages (defensive)
                "/opt/homebrew/lib/python3.14/site-packages",
                "/opt/homebrew/opt/python@3.14/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages",
                os.environ.get("PYTHONPATH", ""),
            ]
        ),
    }

    # Provide a real fixture so reconstruct_hydration_baseline.py's
    # pre-flight check passes (it short-circuits to "fixture missing"
    # without this). The harness still overwrites G5_OUT with whatever
    # the reconstruction script produces (captured or placeholder);
    # the test then drives the harness's source-gate logic on the
    # synthetic candidate placeholder.
    fixture_dir = tmp_path / "fixture"
    fixture_dir.mkdir()
    (fixture_dir / "index.html").write_text(
        "<!doctype html><title>x</title>"
    )

    result = subprocess.run(
        ["bash", str(G5_CLOSE_SH)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    status_path = Path(env["G5_STATUS_JSON"])
    assert status_path.exists(), (
        f"status.json must be written; missing.\nstdout: {result.stdout}"
        f"\nstderr: {result.stderr}"
    )
    doc = json.loads(status_path.read_text())
    assert doc.get("gate") == "G5", (
        f"status.json must self-identify as gate='G5'; got: {doc}"
    )
    assert doc.get("status") == "blocked", (
        f"status.json must record blocked status when candidate is "
        f"a placeholder; got: {doc}"
    )
    assert doc.get("candidate_source") == "unavailable", (
        f"status.json must surface candidate_source='unavailable'; "
        f"got: {doc}"
    )
    assert "synthetic placeholder" in doc.get("blocker", ""), (
        f"status.json blocker must echo the placeholder's blocker; "
        f"got: {doc}"
    )


def test_g5_close_sh_writes_candidate_source_in_status(tmp_path: Path):
    """When Step 2 of ``g5_close.sh`` produces a candidate artifact,
    the harness's final ``status.json`` must surface the candidate's
    ``source``.
    """
    env = _poisoned_env(tmp_path)
    env["G5_STATUS_JSON"] = str(tmp_path / "status.json")
    env["G5_REPORT_JSON"] = str(tmp_path / "report.json")

    result = subprocess.run(
        ["bash", str(G5_CLOSE_SH)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    status_path = Path(env["G5_STATUS_JSON"])
    assert status_path.exists(), (
        f"status.json must be written; missing.\nstdout: {result.stdout}"
        f"\nstderr: {result.stderr}"
    )
    doc = json.loads(status_path.read_text())
    assert doc.get("gate") == "G5", (
        f"status.json must self-identify as gate='G5'; got: {doc}"
    )
    assert doc.get("status") == "blocked", (
        f"status.json must record blocked status; got: {doc}"
    )
    assert doc.get("baseline_source") == "unavailable", (
        f"baseline_source must be 'unavailable' under the poison; "
        f"got: {doc}"
    )

# ---------------------------------------------------------------------------
# Phase 6a re-baseline — multi-sample + HTTP origin + median reduction
# ---------------------------------------------------------------------------
#
# The previous Phase 6a harness was partial: the baseline ran over
# ``file://`` and captured a single sample; the candidate ran over
# HTTP and captured a single sample. The re-baseline tightens both
# legs so the comparison is apples-to-apples:
#
#   * Both baseline AND candidate are served through loopback HTTP
#     (no file:// navigation; fetch + ES-module loading only work
#     over HTTP for the Next.js static export).
#   * Both capture ≥ 3 samples per metric with at least 1 warmup,
#     defaulting to 5 retained + 1 warmup.
#   * Each artifact records raw sample arrays + median metadata so
#     a reviewer can audit the variance reduction.
#   * The comparison uses the median (not raw samples, not the
#     back-compat single-point) when a ``median`` block is present.
#   * Single-point artifacts (the legacy schema) still validate
#     and the comparison falls back to the direct
#     ``client_render.*`` value, preserving PR 1b.3b's caller
#     contract.
#
# These tests are written in strict TDD order (RED → GREEN → TRIANGULATE):
# each must FAIL against the single-sample harness before the
# implementation below it lands.

def _write_multi_sample_artifact(
    path: Path,
    *,
    build: str,
    samples_first_paint: list,
    samples_dom_content_loaded: list | None = None,
    samples_tree_first_paint: list,
    samples_tree_first_interactive: list,
    warmup_first_paint: list | None = None,
    warmup_dom_content_loaded: list | None = None,
    warmup_tree_first_paint: list | None = None,
    warmup_tree_first_interactive: list | None = None,
    samples_retained: int = 5,
    warmup_count: int = 1,
    origin: str = "http://127.0.0.1:54321/",
) -> None:
    """Helper: emit a schema-conformant multi-sample hydration artifact.

    Mirrors what ``reconstruct_hydration_baseline.py`` and
    ``capture_hydration_candidate.py`` must produce after the
    re-baseline. Defaults the median values to the empirical median
    of each samples array so the contract (median = median(samples))
    holds for every fixture a test writes below.
    """
    if samples_dom_content_loaded is None:
        samples_dom_content_loaded = [v + 20.0 for v in samples_first_paint]
    if warmup_first_paint is None:
        warmup_first_paint = [samples_first_paint[0]]
    if warmup_dom_content_loaded is None:
        warmup_dom_content_loaded = [samples_dom_content_loaded[0]]
    if warmup_tree_first_paint is None:
        warmup_tree_first_paint = [samples_tree_first_paint[0]]
    if warmup_tree_first_interactive is None:
        warmup_tree_first_interactive = [samples_tree_first_interactive[0]]

    def _median(values: list) -> float:
        s = sorted(values)
        n = len(s)
        if n == 0:
                return 0.0
        if n % 2 == 1:
                return float(s[n // 2])
        return float((s[n // 2 - 1] + s[n // 2]) / 2.0)

    median_sp = _median(samples_first_paint)
    median_dcl = _median(samples_dom_content_loaded)
    median_tfp = _median(samples_tree_first_paint)
    median_tfi = _median(samples_tree_first_interactive)

    path.write_text(
        json.dumps(
{
"captured_at": "2026-09-06T00:00:00Z",
"build": build,
"route": "/",
# Phase 6a re-baseline: raw sample arrays
"samples": {
"server_shell": {
"first_paint_ms": list(samples_first_paint),
"dom_content_loaded_ms": list(samples_dom_content_loaded),
},
"client_render": {
"tree_first_paint_ms": list(samples_tree_first_paint),
"tree_first_interactive_ms": list(samples_tree_first_interactive),
},
},
"warmup_samples": {
"server_shell": {
"first_paint_ms": list(warmup_first_paint),
"dom_content_loaded_ms": list(warmup_dom_content_loaded),
},
"client_render": {
"tree_first_paint_ms": list(warmup_tree_first_paint),
"tree_first_interactive_ms": list(warmup_tree_first_interactive),
},
},
"samples_retained": samples_retained,
"warmup_count": warmup_count,
"median": {
"server_shell": {
"first_paint_ms": median_sp,
"dom_content_loaded_ms": median_dcl,
},
"client_render": {
"tree_first_paint_ms": median_tfp,
"tree_first_interactive_ms": median_tfi,
},
},
"origin": origin,
# Back-compat single-point fields (= median).
"server_shell": {
"first_paint_ms": median_sp,
"dom_content_loaded_ms": median_dcl,
},
"client_render": {
"tree_first_paint_ms": median_tfp,
"tree_first_interactive_ms": median_tfi,
},
"console_warnings": [],
"source": "captured",
},
indent=2,
        )
    )

# ------------------------------------------------------------------
# (A) Schema: multi-sample artifacts must validate
# ------------------------------------------------------------------
def test_measure_hydration_accepts_multi_sample_artifact(tmp_path: Path):
    """A multi-sample artifact (with `samples`, `median`, `warmup_samples`,
    `samples_retained`, `warmup_count`, `origin`) MUST validate against
    the schema with exit code 0. The legacy single-point validator
    rejects unknown top-level keys as schema violations; the
    re-baseline extends the validator to accept the new fields.
    """
    path = tmp_path / "multi.json"
    _write_multi_sample_artifact(
        path,
        build="legacy",
        samples_first_paint=[10.0, 11.0, 12.0, 13.0, 14.0],
        samples_tree_first_paint=[30.0, 31.0, 32.0, 33.0, 34.0],
        samples_tree_first_interactive=[40.0, 41.0, 42.0, 43.0, 44.0],
    )
    result = _run_script(str(path))
    assert result.returncode == 0, (
        f"multi-sample artifact must validate; got exit={result.returncode}"
        f"\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

def test_measure_hydration_rejects_at_least_3_samples_violation(tmp_path: Path):
    """Triangulation: a multi-sample artifact with fewer than 3 retained
    samples MUST fail validation (the whole point of re-baselining is
    variance reduction; ≥ 3 is the minimum statistical guard).
    """
    # 2 retained samples — fails the >=3 minimum.
    path = tmp_path / "few.json"
    path.write_text(
        json.dumps(
{
"captured_at": "2026-09-06T00:00:00Z",
"build": "legacy",
"route": "/",
"samples": {
"server_shell": {
"first_paint_ms": [10.0, 11.0],
"dom_content_loaded_ms": [12.0, 13.0],
},
"client_render": {
"tree_first_paint_ms": [14.0, 15.0],
"tree_first_interactive_ms": [16.0, 17.0],
},
},
"warmup_samples": {
"server_shell": {"first_paint_ms": [], "dom_content_loaded_ms": []},
"client_render": {"tree_first_paint_ms": [], "tree_first_interactive_ms": []},
},
"samples_retained": 2,
"warmup_count": 0,
"median": {
"server_shell": {"first_paint_ms": 10.5, "dom_content_loaded_ms": 12.5},
"client_render": {"tree_first_paint_ms": 14.5, "tree_first_interactive_ms": 16.5},
},
"origin": "http://127.0.0.1:54321/",
"server_shell": {"first_paint_ms": 10.5, "dom_content_loaded_ms": 12.5},
"client_render": {"tree_first_paint_ms": 14.5, "tree_first_interactive_ms": 16.5},
"console_warnings": [],
}
        )
    )
    result = _run_script(str(path))
    assert result.returncode != 0, (
        f"artifact with < 3 retained samples MUST fail validation; got "
        f"exit={result.returncode}\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )

# ------------------------------------------------------------------
# (B) Median is used in comparison when present
# ------------------------------------------------------------------
def test_measure_hydration_comparison_uses_median_when_present(tmp_path: Path):
    """When both baseline and candidate carry a ``median`` block, the
    comparison MUST compute deltas against the median values (not the
    raw samples, not the back-compat single-point values).

    The fixture is constructed so that the back-compat single-point
    values would imply a +0.1% regression (999 vs 1000), but the
    median values are identical (100 vs 100) — so the only way the
    comparison can exit 0 is by using the median.
    """
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    _write_multi_sample_artifact(
        baseline,
        build="legacy",
        samples_first_paint=[80.0, 81.0, 82.0, 83.0, 84.0],
        samples_tree_first_paint=[100.0, 100.0, 100.0, 100.0, 100.0],
        samples_tree_first_interactive=[200.0, 200.0, 200.0, 200.0, 200.0],
        origin="http://127.0.0.1:11111/",
    )
    _write_multi_sample_artifact(
        candidate,
        build="migrated",
        samples_first_paint=[80.0, 81.0, 82.0, 83.0, 84.0],
        samples_tree_first_paint=[100.0, 100.0, 100.0, 100.0, 100.0],
        samples_tree_first_interactive=[200.0, 200.0, 200.0, 200.0, 200.0],
        origin="http://127.0.0.1:22222/",
    )
    # Overwrite the back-compat single-point values to a divergent
    # +0.1% so we can detect whether the comparison uses the median
    # or the back-compat single-point field.
    for path, raw_first, raw_inter in (
        (baseline, 999.0, 999.0),
        (candidate, 1000.0, 1000.0),
    ):
        doc = json.loads(path.read_text())
        doc["client_render"]["tree_first_paint_ms"] = raw_first
        doc["client_render"]["tree_first_interactive_ms"] = raw_inter
        path.write_text(json.dumps(doc, indent=2))

    report = tmp_path / "report.json"
    result = _run_script(
        "--baseline", str(baseline),
        "--candidate", str(candidate),
        "--report-out", str(report),
    )
    assert result.returncode == 0, (
        f"identical medians must exit 0; got exit={result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    doc = json.loads(report.read_text())
    assert doc["initial_paint_delta_pct"] == 0.0, (
        f"median comparison must yield 0% delta; got {doc}"
    )
    assert doc["interaction_latency_delta_pct"] == 0.0, (
        f"median comparison must yield 0% delta; got {doc}"
    )

# ------------------------------------------------------------------
# (C) Back-compat: single-point artifacts (no `median` block) still work
# ------------------------------------------------------------------
def test_measure_hydration_backcompat_single_point_artifact_no_median(tmp_path: Path):
    """The legacy single-point schema (no ``median``, no ``samples``)
    MUST still validate and the comparison MUST fall back to the
    direct ``client_render.*`` values. Preserves PR 1b.3b's caller
    contract.
    """
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    _write_artifact(
        baseline,
        build="legacy",
        first_paint_ms=80.0,
        tree_first_paint_ms=220.0,
        tree_first_interactive_ms=350.0,
    )
    _write_artifact(
        candidate,
        build="migrated",
        first_paint_ms=80.0,
        tree_first_paint_ms=220.0,
        tree_first_interactive_ms=350.0,
    )
    result = _run_script(
        "--baseline", str(baseline),
        "--candidate", str(candidate),
    )
    assert result.returncode == 0, (
        f"single-point back-compat must exit 0; got exit={result.returncode}"
        f"\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

def test_measure_hydration_mixed_single_and_multi_uses_appropriate_metric(
    tmp_path: Path,
):
    """Mixed scenario: one artifact has ``median``, the other doesn't.
    The comparison MUST use the median for the multi-sample side and
    the direct value for the single-point side, and produce a 0 %
    delta when both metrics are equal.
    """
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    _write_multi_sample_artifact(
        baseline,
        build="legacy",
        samples_first_paint=[80.0] * 5,
        samples_tree_first_paint=[220.0] * 5,
        samples_tree_first_interactive=[350.0] * 5,
        origin="http://127.0.0.1:11111/",
    )
    _write_artifact(
        candidate,
        build="migrated",
        first_paint_ms=80.0,
        tree_first_paint_ms=220.0,
        tree_first_interactive_ms=350.0,
    )
    result = _run_script(
        "--baseline", str(baseline),
        "--candidate", str(candidate),
    )
    assert result.returncode == 0, (
        f"mixed single+multi must exit 0 when metrics match; got exit="
        f"{result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

# ------------------------------------------------------------------
# (D) Regression report enriches with median + raw samples metadata
# ------------------------------------------------------------------
def test_measure_hydration_regression_report_includes_median_metadata(
    tmp_path: Path,
):
    """`--report-out` MUST carry the median values + sample counts
    + warmup counts + origins + raw sample arrays so a reviewer can
    audit the variance reduction (per Phase 6a re-baseline contract:
    "emit raw sample arrays + median metadata").
    """
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    _write_multi_sample_artifact(
        baseline,
        build="legacy",
        samples_first_paint=[80.0, 81.0, 82.0, 83.0, 84.0],
        samples_tree_first_paint=[100.0, 100.0, 100.0, 100.0, 100.0],
        samples_tree_first_interactive=[200.0, 200.0, 200.0, 200.0, 200.0],
        samples_retained=5,
        warmup_count=1,
        origin="http://127.0.0.1:11111/",
    )
    _write_multi_sample_artifact(
        candidate,
        build="migrated",
        samples_first_paint=[80.0, 81.0, 82.0, 83.0, 84.0],
        samples_tree_first_paint=[100.0, 100.0, 100.0, 100.0, 100.0],
        samples_tree_first_interactive=[200.0, 200.0, 200.0, 200.0, 200.0],
        samples_retained=5,
        warmup_count=1,
        origin="http://127.0.0.1:22222/",
    )
    report = tmp_path / "report.json"
    result = _run_script(
        "--baseline", str(baseline),
        "--candidate", str(candidate),
        "--report-out", str(report),
    )
    assert result.returncode == 0, (
        f"identical inputs must exit 0; got exit={result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    doc = json.loads(report.read_text())
    # Median metadata
    assert doc.get("baseline_median_initial_paint_ms") == 100.0, (
        f"report must carry baseline_median_initial_paint_ms; got: {doc}"
    )
    assert doc.get("candidate_median_initial_paint_ms") == 100.0, (
        f"report must carry candidate_median_initial_paint_ms; got: {doc}"
    )
    assert doc.get("baseline_median_interaction_latency_ms") == 200.0, (
        f"report must carry baseline_median_interaction_latency_ms; got: {doc}"
    )
    assert doc.get("candidate_median_interaction_latency_ms") == 200.0, (
        f"report must carry candidate_median_interaction_latency_ms; got: {doc}"
    )
    # Sample counts
    assert doc.get("baseline_samples_retained") == 5, (
        f"report must carry baseline_samples_retained=5; got: {doc}"
    )
    assert doc.get("candidate_samples_retained") == 5, (
        f"report must carry candidate_samples_retained=5; got: {doc}"
    )
    assert doc.get("baseline_warmup_count") == 1, (
        f"report must carry baseline_warmup_count=1; got: {doc}"
    )
    assert doc.get("candidate_warmup_count") == 1, (
        f"report must carry candidate_warmup_count=1; got: {doc}"
    )
    # Origin (HTTP contract)
    assert doc.get("baseline_origin") == "http://127.0.0.1:11111/", (
        f"report must carry baseline_origin; got: {doc}"
    )
    assert doc.get("candidate_origin") == "http://127.0.0.1:22222/", (
        f"report must carry candidate_origin; got: {doc}"
    )
    # Raw sample arrays
    for leg in ("baseline", "candidate"):
        assert "samples" in doc[leg], (
f"report must carry raw samples for {leg}; got: {doc}"
        )
        assert doc[leg]["samples"]["tree_first_paint_ms"] == [
100.0, 100.0, 100.0, 100.0, 100.0,
        ], (
f"report must carry {leg}.samples.tree_first_paint_ms; got: {doc}"
        )
        assert doc[leg]["samples"]["tree_first_interactive_ms"] == [
200.0, 200.0, 200.0, 200.0, 200.0,
        ], (
f"report must carry {leg}.samples.tree_first_interactive_ms; got: {doc}"
        )

# ------------------------------------------------------------------
# (E) Source-code contract: HTTP baseline origin
# ------------------------------------------------------------------
def test_reconstruct_hydration_baseline_uses_http_server_not_file_uri():
    """The reconstruction script must serve the G3 fixture via an HTTP
    loopback server (mirror of the candidate's contract), NOT a
    ``file://`` URI. file:// disables fetch + ES-module loading for
    Next.js static exports and breaks the apples-to-apples comparison.

    This test reads the script source and asserts it (a) sets up an
    HTTP server and (b) does NOT navigate to file:// URIs.
    """
    source = RECONSTRUCT_SCRIPT.read_text()
    assert "HTTPServer" in source, (
        f"reconstruct_hydration_baseline.py must use "
        f"http.server.HTTPServer to serve the G3 fixture over "
        f"loopback HTTP; got source that lacks an HTTPServer reference."
    )
    # Must NOT construct a file:// URI via Path.as_uri().
    assert "as_uri()" not in source, (
        f"reconstruct_hydration_baseline.py must NOT use "
        f"Path.as_uri() (file:// navigation); got source that still "
        f"constructs file:// URIs."
    )
    assert '"./index.html"' not in source or "file://" not in source, (
        f"reconstruct_hydration_baseline.py must NOT navigate to a "
        f"file:// scheme; got source that mentions file://."
    )

# ------------------------------------------------------------------
# (F) Source-code contract: >=3 samples + median reduction
# ------------------------------------------------------------------
def test_reconstruct_hydration_baseline_runs_multiple_samples():
    """The reconstruction script must capture multiple samples and
    reduce them to a median (not take a single measurement). Variance
    reduction is the whole point of re-baselining.
    """
    source = RECONSTRUCT_SCRIPT.read_text()
    for needle, description in (
        ("samples", "samples array"),
        ("median", "median reduction"),
        ("warmup", "warmup tracking"),
    ):
        assert needle in source.lower(), (
f"reconstruct_hydration_baseline.py must reference "
f"{description!r}; got source that lacks it."
        )

def test_capture_hydration_candidate_runs_multiple_samples():
    """The candidate capture must also capture multiple samples,
    matching the baseline's sampling strategy.
    """
    source = CANDIDATE_CAPTURE_SCRIPT.read_text()
    for needle, description in (
        ("samples", "samples array"),
        ("median", "median reduction"),
        ("warmup", "warmup tracking"),
    ):
        assert needle in source.lower(), (
f"capture_hydration_candidate.py must reference "
f"{description!r}; got source that lacks it."
        )

# ------------------------------------------------------------------
# (G) Source-code contract: default 5 retained + 1 warmup
# ------------------------------------------------------------------
def test_reconstruct_hydration_baseline_default_samples_retained_is_5():
    """Default --samples-retained MUST be 5 (Phase 6a re-baseline
    contract: "default 5 retained samples with one warm-up")."""
    source = RECONSTRUCT_SCRIPT.read_text()
    assert "samples-retained" in source, (
        f"reconstruct_hydration_baseline.py must expose "
        f"--samples-retained flag; got source that lacks it."
    )
    # Verify default value is 5.
    assert "default=5" in source or "DEFAULT_SAMPLES_RETAINED = 5" in source, (
        f"reconstruct_hydration_baseline.py must default "
        f"--samples-retained to 5; got source that lacks a 5-default."
    )

def test_reconstruct_hydration_baseline_default_warmup_count_is_1():
    """Default --warmup-count MUST be 1 (Phase 6a re-baseline
    contract: "one warm-up" sample)."""
    source = RECONSTRUCT_SCRIPT.read_text()
    assert "warmup-count" in source, (
        f"reconstruct_hydration_baseline.py must expose "
        f"--warmup-count flag; got source that lacks it."
    )
    assert "default=1" in source or "DEFAULT_WARMUP_COUNT = 1" in source, (
        f"reconstruct_hydration_baseline.py must default --warmup-count "
        f"to 1; got source that lacks a 1-default."
    )

def test_capture_hydration_candidate_default_samples_retained_is_5():
    """Candidate capture must mirror the baseline's --samples-retained
    default of 5."""
    source = CANDIDATE_CAPTURE_SCRIPT.read_text()
    assert "samples-retained" in source, (
        f"capture_hydration_candidate.py must expose "
        f"--samples-retained flag; got source that lacks it."
    )
    assert "default=5" in source or "DEFAULT_SAMPLES_RETAINED = 5" in source, (
        f"capture_hydration_candidate.py must default --samples-retained "
        f"to 5; got source that lacks a 5-default."
    )

def test_capture_hydration_candidate_default_warmup_count_is_1():
    """Candidate capture must mirror the baseline's --warmup-count
    default of 1."""
    source = CANDIDATE_CAPTURE_SCRIPT.read_text()
    assert "warmup-count" in source, (
        f"capture_hydration_candidate.py must expose "
        f"--warmup-count flag; got source that lacks it."
    )
    assert "default=1" in source or "DEFAULT_WARMUP_COUNT = 1" in source, (
        f"capture_hydration_candidate.py must default --warmup-count "
        f"to 1; got source that lacks a 1-default."
    )

# ------------------------------------------------------------------
# (H) Triangulation: median computation correctness
# ------------------------------------------------------------------
def test_measure_hydration_median_field_is_empirical_median_of_samples(
    tmp_path: Path,
):
    """Triangulation: when an artifact carries ``samples`` +
    ``median``, the median values MUST be the empirical median of
    the sample arrays (for both odd and even-length lists).

    Guards against a regression where the median field is
    hard-coded or computed against the wrong array.
    """
    # 5-sample arrays (default): median is the middle element after sort.
    # samples_first_paint = [80, 81, 82, 83, 84] -> median 82
    # samples_tree_first_paint = [10, 30, 50, 70, 90] -> median 50
    # samples_tree_first_interactive = [200, 400, 600, 800, 1000] -> median 600
    samples_first_paint = [80.0, 81.0, 82.0, 83.0, 84.0]
    median_first_paint = 82.0
    samples_tree_first_paint = [10.0, 30.0, 50.0, 70.0, 90.0]
    median_tree_first_paint = 50.0
    samples_tree_first_interactive = [200.0, 400.0, 600.0, 800.0, 1000.0]
    median_tree_first_interactive = 600.0

    artifact_path = tmp_path / "median_check.json"
    artifact_path.write_text(
        json.dumps(
{
"captured_at": "2026-09-06T00:00:00Z",
"build": "legacy",
"route": "/",
"samples": {
"server_shell": {
"first_paint_ms": samples_first_paint,
"dom_content_loaded_ms": samples_first_paint,
},
"client_render": {
"tree_first_paint_ms": samples_tree_first_paint,
"tree_first_interactive_ms": samples_tree_first_interactive,
},
},
"warmup_samples": {
"server_shell": {
"first_paint_ms": [samples_first_paint[0]],
"dom_content_loaded_ms": [samples_first_paint[0]],
},
"client_render": {
"tree_first_paint_ms": [samples_tree_first_paint[0]],
"tree_first_interactive_ms": [samples_tree_first_interactive[0]],
},
},
"samples_retained": 5,
"warmup_count": 1,
"median": {
"server_shell": {
"first_paint_ms": median_first_paint,
"dom_content_loaded_ms": median_first_paint,
},
"client_render": {
"tree_first_paint_ms": median_tree_first_paint,
"tree_first_interactive_ms": median_tree_first_interactive,
},
},
"origin": "http://127.0.0.1:54321/",
"server_shell": {
"first_paint_ms": median_first_paint,
"dom_content_loaded_ms": median_first_paint,
},
"client_render": {
"tree_first_paint_ms": median_tree_first_paint,
"tree_first_interactive_ms": median_tree_first_interactive,
},
"console_warnings": [],
}
        )
    )

    # Compare against the candidate (both use same median values).
    candidate = tmp_path / "candidate.json"
    candidate.write_text(artifact_path.read_text())
    # Tweak candidate's `build` field.
    doc = json.loads(candidate.read_text())
    doc["build"] = "migrated"
    doc["origin"] = "http://127.0.0.1:22222/"
    candidate.write_text(json.dumps(doc))

    report = tmp_path / "report.json"
    result = _run_script(
        "--baseline", str(artifact_path),
        "--candidate", str(candidate),
        "--report-out", str(report),
    )
    assert result.returncode == 0, (
        f"identical empirical medians must exit 0; got exit="
        f"{result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    report_doc = json.loads(report.read_text())
    assert report_doc["initial_paint_delta_pct"] == 0.0
    assert report_doc["interaction_latency_delta_pct"] == 0.0
    # The report's median values must equal the empirical medians.
    assert report_doc["baseline_median_initial_paint_ms"] == median_tree_first_paint
    assert report_doc["baseline_median_interaction_latency_ms"] == median_tree_first_interactive
    assert report_doc["candidate_median_initial_paint_ms"] == median_tree_first_paint
    assert report_doc["candidate_median_interaction_latency_ms"] == median_tree_first_interactive

def test_measure_hydration_comparison_regression_uses_median_for_floats(
    tmp_path: Path,
):
    """Triangulation: a candidate whose median regresses > 0 % on
    EITHER axis MUST exit 4 (fail-closed) and the report must name
    the regressing axis. Guards the fail-closed invariant when
    artifacts carry the multi-sample block.
    """
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    # Baseline median tree_first_paint = 100; candidate = 130 (+30%).
    _write_multi_sample_artifact(
        baseline,
        build="legacy",
        samples_first_paint=[80.0] * 5,
        samples_tree_first_paint=[100.0] * 5,
        samples_tree_first_interactive=[200.0] * 5,
        origin="http://127.0.0.1:11111/",
    )
    _write_multi_sample_artifact(
        candidate,
        build="migrated",
        samples_first_paint=[80.0] * 5,
        samples_tree_first_paint=[130.0] * 5,
        samples_tree_first_interactive=[200.0] * 5,
        origin="http://127.0.0.1:22222/",
    )
    result = _run_script(
        "--baseline", str(baseline),
        "--candidate", str(candidate),
    )
    assert result.returncode == 4, (
        f"regression via median MUST exit 4; got exit={result.returncode}"
        f"\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    diag = (result.stdout + result.stderr).lower()
    assert "initial_paint" in diag, (
        f"regression must name initial_paint axis; got: {diag}"
    )
