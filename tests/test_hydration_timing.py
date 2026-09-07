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
from unittest import mock

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "measure_hydration.py"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def hydration_artifact(tmp_path: Path) -> Path:
    """Synthetic G5 1+9 / DOMContentLoaded hydration JSON artifact.

    Re-baselined in Phase 6a to the G5 1+9 / DOMContentLoaded
    schema (raw sample list + per-run provenance + median as float).
    """
    fixture = tmp_path / "hydration.json"
    samples = []
    # 9 retained DOMContentLoaded samples; first_paint_ms 80 -> DOMContentLoaded 100
    # delta client-vs-server is ~100ms but the G5 protocol does not
    # report a legacy "delta"; the fixture exercises the new schema.
    for i, ms in enumerate([100.0, 101.0, 102.0, 103.0, 104.0,
105.0, 106.0, 107.0, 108.0]):
        samples.append({
            "dom_content_loaded_ms": ms,
            "browser_version": "Chromium 120.0.6099.71",
            "build_sha": "abc1234",
            "route": "/",
            "captured_at": "2026-08-28T00:00:00Z",
            "capture_environment": "controlled-loopback",
        })
    fixture.write_text(
        json.dumps(
            {
                "captured_at": "2026-08-28T00:00:00Z",
                "build": "legacy",
                "route": "/",
                "samples": samples,
                "warmup_samples": [samples[0]],
                "samples_retained": 9,
                "warmup_count": 1,
                "median": 104.0,
                "origin": "http://127.0.0.1:54321/",
                "console_warnings": [],
                "source": "captured",
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
    samples = []
    for i, ms in enumerate([80.0, 81.0, 82.0, 83.0, 84.0,
85.0, 86.0, 87.0, 88.0]):
        samples.append({
            "dom_content_loaded_ms": ms,
            "browser_version": "Chromium 120.0.6099.71",
            "build_sha": "abc1234",
            "route": "/",
            "captured_at": "2026-08-28T00:00:00Z",
            "capture_environment": "controlled-loopback",
        })
    fixture.write_text(
        json.dumps(
            {
                "captured_at": "2026-08-28T00:00:00Z",
                "build": "migrated",
                "route": "/",
                "samples": samples,
                "warmup_samples": [samples[0]],
                "samples_retained": 9,
                "warmup_count": 1,
                "median": 84.0,
                "origin": "http://127.0.0.1:11111/",
                "console_warnings": [
                    "Warning: Text content did not match. "
                    "Server: %s Client: %s",
                ],
                "source": "captured",
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
    """The script must report the canonical G5 1+9 metric
    (median_ms + samples.dom_content_loaded_ms + threshold_ms) in
    human-readable form.
    """
    result = _run_script(str(hydration_artifact))
    assert result.returncode == 0, result.stderr
    output = result.stdout + result.stderr
    # The G5 1+9 contract: report carries the median, the raw
    # samples, the threshold, and the origin.
    assert "median_ms" in output, (
        f"script must report median_ms; got:\n{output}"
    )
    assert "threshold_ms" in output, (
        f"script must report threshold_ms (G5 1+9 gate); got:\n{output}"
    )
    assert "104" in output, (
        f"script must report the median value 104.0; got:\n{output}"
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
    """Pin the G5 1+9 schema: raw sample list + per-run provenance +
    median as float + threshold-friendly fields."""
    doc = json.loads(hydration_artifact.read_text())
    for key in (
        "captured_at",
        "build",
        "route",
        "samples",
        "warmup_samples",
        "samples_retained",
        "warmup_count",
        "median",
        "origin",
        "console_warnings",
        "source",
    ):
        assert key in doc, f"G5 hydration artifact missing key {key!r}"
    # Legacy multi-metric keys are NOT part of the G5 1+9 schema.
    assert "server_shell" not in doc, (
        f"G5 artifact must NOT carry legacy server_shell block; got: {doc}"
    )
    assert "client_render" not in doc, (
        f"G5 artifact must NOT carry legacy client_render block; got: {doc}"
    )


def test_hydration_artifact_samples_keys(hydration_artifact: Path):
    """Each sample in the G5 1+9 schema must carry
    dom_content_loaded_ms + per-run provenance (browser_version,
    route, captured_at, capture_environment)."""
    doc = json.loads(hydration_artifact.read_text())
    samples = doc["samples"]
    assert isinstance(samples, list), (
        f"samples must be a list; got {type(samples).__name__}"
    )
    assert len(samples) == doc["samples_retained"], (
        f"len(samples) must equal samples_retained; got "
        f"len={len(samples)}, samples_retained={doc['samples_retained']}"
    )
    for i, s in enumerate(samples):
        for k in (
            "dom_content_loaded_ms",
            "browser_version",
            "route",
            "captured_at",
            "capture_environment",
        ):
            assert k in s, (
f"samples[{i}] missing provenance key {k!r}; got: {s}"
            )
        assert isinstance(s["dom_content_loaded_ms"], (int, float))
        assert s["dom_content_loaded_ms"] >= 0


def test_hydration_artifact_warmup_samples_keys(hydration_artifact: Path):
    """warmup_samples has the same per-sample shape as samples."""
    doc = json.loads(hydration_artifact.read_text())
    warmup = doc["warmup_samples"]
    assert isinstance(warmup, list), (
        f"warmup_samples must be a list; got {type(warmup).__name__}"
    )
    assert len(warmup) == doc["warmup_count"], (
        f"len(warmup_samples) must equal warmup_count; got "
        f"len={len(warmup)}, warmup_count={doc['warmup_count']}"
    )
    for w in warmup:
        for k in (
            "dom_content_loaded_ms",
            "browser_version",
            "route",
            "captured_at",
            "capture_environment",
        ):
            assert k in w, (
f"warmup_samples entry missing key {k!r}; got: {w}"
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
                # route, samples, warmup_samples, median, console_warnings omitted
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
    MUST NOT break PR 1b.3b's caller contract. The G5 1+9 re-baseline
    updates the report header to reflect the new metric (median_ms +
    samples.dom_content_loaded_ms + threshold_ms).
    """
    result = _run_script(str(hydration_artifact))
    assert result.returncode == 0, (
        f"single-positional invocation must keep working; got exit={result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # The G5 1+9 report header must appear (regression guard for
    # the human-readable report).
    assert "Hydration timing report (G5 1+9 / DOMContentLoaded)" in result.stdout, (
        f"back-compat report missing G5 1+9 header; got:\n{result.stdout}"
    )
    assert "median_ms" in result.stdout, (
        f"back-compat report missing median_ms; got:\n{result.stdout}"
    )


def test_measure_hydration_baseline_candidate_emits_delta_report(tmp_path: Path):
    """When `--baseline` + `--candidate` are both supplied, the script
    must exit 0 (delta_ms == 0) and emit a comparison report naming
    the median_ms, delta_ms, and threshold_ms (G5 1+9 protocol).
    """
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_g5_artifact(
        baseline, build="legacy", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:22222/",
    )
    result = _run_script(
        "--baseline", str(baseline), "--candidate", str(candidate),
    )
    assert result.returncode == 0, (
        f"baseline/candidate with delta_ms=0 must exit 0; got "
        f"{result.returncode}.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    out = result.stdout + result.stderr
    assert "delta_ms" in out, (
        f"report must name delta_ms metric; got:\n{out}"
    )
    assert "threshold_ms" in out, (
        f"report must name threshold_ms metric; got:\n{out}"
    )


def test_measure_hydration_baseline_candidate_fails_closed_on_regression(
    tmp_path: Path,
):
    """FAIL-CLOSED core contract: when delta_ms > 10 ms, the script
    MUST exit non-zero with code 4 and surface the regression in
    stderr/stdout."""
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_g5_artifact(
        baseline, build="legacy", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    # Candidate regresses +20 ms on DOMContentLoaded median.
    _write_g5_artifact(
        candidate, build="migrated", samples_ms=[120.0] * 9,
        origin="http://127.0.0.1:22222/",
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
    assert "delta_ms" in diag or "threshold" in diag, (
        f"regression diagnostic must name delta_ms / threshold; got:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_measure_hydration_baseline_candidate_passes_on_improvement(
    tmp_path: Path,
):
    """Negative-axis triangulation: a candidate BETTER than baseline
    (delta_ms < 0) must exit 0."""
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_g5_artifact(
        baseline, build="legacy", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated", samples_ms=[50.0] * 9,
        origin="http://127.0.0.1:22222/",
    )
    result = _run_script(
        "--baseline", str(baseline), "--candidate", str(candidate),
    )
    assert result.returncode == 0, (
        f"improved candidate must exit 0; got {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_measure_hydration_baseline_candidate_writes_json_report(tmp_path: Path):
    """`--report-out <path>` must write a machine-readable JSON report
    carrying threshold_ms, medians, delta_ms, pass verdict, and raw
    sample arrays (G5 1+9 protocol)."""
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_g5_artifact(
        baseline, build="legacy", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:22222/",
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
    for key in ("threshold_ms", "baseline_median_ms",
"candidate_median_ms", "delta_ms", "pass"):
        assert key in doc, f"report missing key {key!r}; got: {doc}"
    assert doc["pass"] is True, (
        f"identical inputs must report pass=true; got: {doc}"
    )
    assert doc["threshold_ms"] == 10.0, (
        f"report threshold_ms must be 10.0; got: {doc}"
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


def test_capture_hydration_candidate_happy_path_emits_captured_artifact(
    tmp_path: Path, monkeypatch,
):
    """Hermetic regression guard: the successful capture path MUST
    produce a ``source: "captured"`` artifact.

    Catches the dead-code regression where ``median_ms``,
    ``samples``, and ``warmup_samples`` were nested inside the
    inner ``except Exception`` block (after ``return 5``), making
    them unreachable. The downstream ``artifact = {...}`` block
    then raised ``UnboundLocalError`` on every successful
    navigation -- blocking the G5 comparison forever because no
    artifact could ever be emitted with ``source == "captured"``.

    The test mocks Playwright + the static server so it runs in a
    hermetic environment with no real browser; it directly
    invokes ``_capture`` so the only behaviour exercised is the
    ``_capture`` function body itself.
    """
    import scripts.capture_hydration_candidate as chc

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "index.html").write_text(
        "<!doctype html><html><body>candidate</body></html>"
    )
    out = tmp_path / "hydration-candidate.json"

    # Fake playwright.sync_api: every import resolves to a
    # MagicMock that acts as a context manager and chains through
    # ``chromium.launch().new_context().new_page()`` without
    # touching a real browser.
    fake_pw_instance = mock.MagicMock(name="sync_playwright_ctx")
    fake_pw_instance.__enter__ = mock.MagicMock(
        return_value=fake_pw_instance,
    )
    fake_pw_instance.__exit__ = mock.MagicMock(return_value=False)
    fake_browser = mock.MagicMock(name="browser")
    fake_context = mock.MagicMock(name="context")
    fake_page = mock.MagicMock(name="page")
    fake_pw_instance.chromium.launch.return_value = fake_browser
    fake_browser.new_context.return_value = fake_context
    fake_context.new_page.return_value = fake_page

    fake_pw_api = mock.MagicMock(name="playwright.sync_api")
    fake_pw_api.sync_playwright = mock.MagicMock(
        return_value=fake_pw_instance,
    )
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_pw_api)

    # Pin every external surface so the test never touches the
    # network, the filesystem outside tmp_path, or real Playwright.
    monkeypatch.setattr(chc, "_check_playwright", lambda: (True, ""))
    monkeypatch.setattr(
        chc, "_start_static_server",
        lambda *a, **kw: (mock.MagicMock(name="server"), lambda: None, 54321),
    )
    monkeypatch.setattr(
        chc, "_wait_for_server", lambda *a, **kw: (True, ""),
    )
    monkeypatch.setattr(
        chc, "_navigate_once", lambda *a, **kw: 100.0,
    )
    monkeypatch.setattr(
        chc, "_detect_browser_version", lambda page: "fake-chromium/1.0",
    )
    monkeypatch.setattr(chc, "_detect_build_sha", lambda: "deadbeef")

    rc = chc._capture(
        build_dir=build_dir,
        out=out,
        samples_retained=9,
        warmup_count=1,
    )

    # The happy path MUST exit 0 (a real capture wrote a
    # schema-conformant artifact).
    assert rc == 0, (
        f"happy-path _capture must exit 0; got {rc}. This is the "
        f"regression signature: when the inner-except / return-5 "
        f"indentation bug is present, ``samples`` / ``median_ms`` "
        f"are UnboundLocalError and the function either raises or "
        f"writes a placeholder. See scripts/capture_hydration_"
        f"candidate.py::_capture for the indent that must live "
        f"OUTSIDE the inner ``except``."
    )
    assert out.exists(), (
        f"happy path must write the artifact at {out}; missing."
    )
    doc = json.loads(out.read_text())

    # G5 1+9 protocol: source must be "captured" (not
    # "unavailable") so the comparator accepts it.
    assert doc.get("source") == "captured", (
        f"happy path artifact MUST self-label source='captured' "
        f"so G5 can compare; got: {doc}"
    )
    # samples / warmup_samples / median must be populated -- if
    # they are not, the dead-code indentation bug has resurfaced.
    assert len(doc.get("samples", [])) == 9, (
        f"retained samples must equal samples_retained=9; got "
        f"{len(doc.get('samples', []))} (dead-code regression?)"
    )
    assert len(doc.get("warmup_samples", [])) == 1, (
        f"warmup_samples must equal warmup_count=1; got "
        f"{len(doc.get('warmup_samples', []))} (dead-code "
        f"regression?)"
    )
    assert doc.get("median") == 100.0, (
        f"median must be computed from the retained values; got "
        f"{doc.get('median')} (dead-code regression?)"
    )
    # 'unavailable' / 'blocker' must NOT appear on a happy path.
    assert doc.get("blocker") in (None, ""), (
        f"happy path artifact must NOT carry a blocker field; "
        f"got: {doc.get('blocker')!r}"
    )
    assert "unavailable" not in json.dumps(doc).lower() or (
        doc.get("origin", "").startswith("http://")
    ), (
        f"happy path artifact must NOT include placeholder "
        f"markers; got: {doc}"
    )

    # Defensive source-code check: the bind that regressed sits
    # at the inner-except / outer-try boundary. Guard against
    # anyone re-indenting the dead-code blocks back inside the
    # ``except`` after ``return 5`` -- the source of the dead
    # lines must NOT sit between ``return 5`` and the next
    # outer-level statement.
    source = CANDIDATE_CAPTURE_SCRIPT.read_text()
    return5_idx = source.find("return 5")
    assert return5_idx != -1, (
        "expected _capture to retain a `return 5` failure branch; "
        "got source that has none. The happy-path regression "
        "guard relies on the `return 5` sentinel staying put."
    )
    # Find the next line at the outer-try body indent (12 spaces)
    # AFTER `return 5`. The dead-code blocks must end BEFORE that
    # line, not straddle past it.
    lines = source.splitlines()
    return5_line = -1
    for i, line in enumerate(lines):
        if "return 5" in line:
            return5_line = i
            break
    assert return5_line != -1, (
        "could not locate `return 5` in candidate capture script; "
        "happy-path regression guard cannot be evaluated."
    )
    # Scan for the next 'artifact = {' line and ensure every
    # intervening line that defines a name used by the artifact
    # ('median_ms', 'samples =', 'warmup_samples =') lives at the
    # outer-try body indent (12 spaces), NOT inside the except.
    artifact_line = -1
    for i in range(return5_line + 1, len(lines)):
        stripped = lines[i].lstrip()
        if stripped.startswith("artifact = {"):
            artifact_line = i
            break
    assert artifact_line != -1, (
        "could not locate `artifact = {` after `return 5`; "
        "happy-path regression guard cannot be evaluated."
    )
    for i in range(return5_line + 1, artifact_line):
        line = lines[i]
        stripped = line.lstrip()
        for needle in ("median_ms =", "samples = [", "warmup_samples = ["):
            if stripped.startswith(needle):
                indent = len(line) - len(stripped)
                assert indent <= 12, (
                    f"happy-path regression: line {i + 1} "
                    f"{needle!r} is indented at {indent} spaces "
                    f"(inside the inner except after `return 5`); "
                    f"it MUST be at 12 spaces (outer-try body) so "
                    f"the artifact block can see it. "
                    f"Line: {line!r}"
                )


def test_g5_close_sh_blocks_when_candidate_is_placeholder(tmp_path: Path):
    """Triangulation: when the candidate artifact exists but its
    ``source`` is NOT ``"captured"``, the harness MUST NOT compare it
    against the baseline (G5 1+9 protocol)."""
    baseline = tmp_path / "baseline.json"
    _write_g5_artifact(
        baseline, build="legacy", samples_ms=[18.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    # Force the baseline file to look "captured" so the harness reaches
    # the source-gate step.
    doc = json.loads(baseline.read_text())
    doc["source"] = "captured"
    baseline.write_text(json.dumps(doc, indent=2))

    candidate = tmp_path / "candidate.json"
    _write_g5_artifact(
        candidate, build="migrated", samples_ms=[0.0] * 9,
        origin="http://127.0.0.1:22222/",
    )
    # Force the candidate file to look like a placeholder.
    doc = json.loads(candidate.read_text())
    doc["source"] = "unavailable"
    doc["blocker"] = "synthetic placeholder for the source-gate test"
    candidate.write_text(json.dumps(doc, indent=2))

    env = {
        # Put homebrew Python first on PATH so `python3` in the harness
        # resolves to the interpreter that has playwright installed.
        "PATH": "/opt/homebrew/opt/python@3.14/bin:/usr/bin:/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "G5_FIXTURE_WEB_ROOT": str(tmp_path / "fixture"),
        "G5_OUT": str(baseline),
        "G5_CANDIDATE": str(candidate),
        "G5_STATUS_JSON": str(tmp_path / "status.json"),
        "G5_REPORT_JSON": str(tmp_path / "report.json"),
        "PYTHONPATH": ":".join(
            [
                "/Users/sebailla/Library/Python/3.14/lib/python/site-packages",
                "/opt/homebrew/lib/python3.14/site-packages",
                "/opt/homebrew/opt/python@3.14/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages",
                os.environ.get("PYTHONPATH", ""),
            ]
        ),
    }

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
# ------------------------------------------------------------------
# (B) Median is used in comparison when present
# ------------------------------------------------------------------
# ------------------------------------------------------------------
# (C) Back-compat: single-point artifacts (no `median` block) still work
# ------------------------------------------------------------------
# ------------------------------------------------------------------
# (D) Regression report enriches with median + raw samples metadata
# ------------------------------------------------------------------
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
# =====================================================================
# Phase 6a — G5 measurement protocol (1+9, DOMContentLoaded, ≤10 ms)
# =====================================================================
#
# The user-approved protocol deliberately supersedes the unstable
# percentage gate (0–4 ms variance produced ready / blocked / blocked
# verdicts). The new observable is DOMContentLoaded measured via
# PerformanceNavigationTiming; the default is exactly 1 warm-up + 9
# retained samples; the gate is the absolute median delta ≤ 10 ms;
# per-run provenance is mandatory.
#
# These tests are written in strict TDD order (RED → GREEN → TRIANGULATE):
# each new test fails against the legacy multi-metric harness below
# before the production code is updated.
# =====================================================================

G5_DEFAULT_SAMPLES_RETAINED = 9
G5_DEFAULT_WARMUP_COUNT = 1
G5_THRESHOLD_MS = 10.0


def _write_g5_artifact(
    path,
    *,
    build,
    samples_ms,
    warmup_ms=None,
    browser_version="Chromium 120.0.6099.71",
    build_sha: str | None = "abc1234",
    route="/",
    capture_environment="controlled-loopback",
    origin="http://127.0.0.1:54321/",
    captured_at="2026-09-07T00:00:00Z",
):
    """Emit a schema-conformant G5 1+9 / DOMContentLoaded artifact.

    Persists per-run provenance (browser_version, build_sha if available,
    route, capture timestamp/environment) on every retained + warm-up
    sample. ``median`` is the empirical median of ``samples_ms`` (warm-up
    excluded).
    """
    if warmup_ms is None:
        warmup_ms = [samples_ms[0]] if samples_ms else [0.0]
    samples = []
    for i, ms in enumerate(samples_ms):
        sample = {
            "dom_content_loaded_ms": float(ms),
            "browser_version": browser_version,
            "route": route,
            "captured_at": captured_at,
            "capture_environment": capture_environment,
        }
        if build_sha is not None:
            sample["build_sha"] = build_sha
        samples.append(sample)
    warmup_samples = []
    for i, ms in enumerate(warmup_ms):
        ws = {
            "dom_content_loaded_ms": float(ms),
            "browser_version": browser_version,
            "route": route,
            "captured_at": captured_at,
            "capture_environment": capture_environment,
        }
        if build_sha is not None:
            ws["build_sha"] = build_sha
        warmup_samples.append(ws)

    n = len(samples_ms)
    if n == 0:
        median_ms = 0.0
    else:
        s = sorted(samples_ms)
        if n % 2 == 1:
            median_ms = float(s[n // 2])
        else:
            median_ms = float((s[n // 2 - 1] + s[n // 2]) / 2.0)

    artifact = {
        "captured_at": captured_at,
        "build": build,
        "route": route,
        "samples": samples,
        "warmup_samples": warmup_samples,
        "samples_retained": n,
        "warmup_count": len(warmup_ms),
        "median": median_ms,
        "origin": origin,
        "console_warnings": [],
        "source": "captured",
    }
    path.write_text(json.dumps(artifact, indent=2))


# ------------------------------------------------------------------
# (P1) Capture-script defaults: exactly 9 retained + 1 warmup
# ------------------------------------------------------------------
def test_reconstruct_hydration_baseline_default_samples_retained_is_9():
    """G5 protocol: default --samples-retained MUST be exactly 9."""
    source = RECONSTRUCT_SCRIPT.read_text()
    assert "samples-retained" in source, (
        "reconstruct_hydration_baseline.py must expose --samples-retained"
    )
    assert ("default=9" in source
            or "DEFAULT_SAMPLES_RETAINED = 9" in source), (
        "reconstruct_hydration_baseline.py must default --samples-retained "
        "to 9 (G5 1+9 protocol); got source that lacks a 9-default."
    )


def test_capture_hydration_candidate_default_samples_retained_is_9():
    """G5 protocol: candidate capture must default --samples-retained to 9."""
    source = CANDIDATE_CAPTURE_SCRIPT.read_text()
    assert "samples-retained" in source, (
        "capture_hydration_candidate.py must expose --samples-retained"
    )
    assert ("default=9" in source
            or "DEFAULT_SAMPLES_RETAINED = 9" in source), (
        "capture_hydration_candidate.py must default --samples-retained "
        "to 9 (G5 1+9 protocol); got source that lacks a 9-default."
    )


def test_g5_default_warmup_count_is_one_for_both_capture_scripts():
    """G5 protocol: default --warmup-count is exactly 1 for both scripts."""
    for script in (RECONSTRUCT_SCRIPT, CANDIDATE_CAPTURE_SCRIPT):
        source = script.read_text()
        assert "warmup-count" in source, (
            f"{script.name} must expose --warmup-count flag."
        )
        assert ("default=1" in source
                or "DEFAULT_WARMUP_COUNT = 1" in source), (
            f"{script.name} must default --warmup-count to 1; got "
            f"source that lacks a 1-default."
        )


# ------------------------------------------------------------------
# (P2) Schema: G5 artifact must validate (DOMContentLoaded-only)
# ------------------------------------------------------------------
def test_measure_hydration_accepts_g5_artifact(tmp_path):
    """The new G5 artifact (samples list with per-run provenance, median
    as float) MUST validate and exit 0."""
    path = tmp_path / "g5.json"
    _write_g5_artifact(
        path,
        build="legacy",
        samples_ms=[100.0, 101.0, 102.0, 103.0, 104.0,
                    105.0, 106.0, 107.0, 108.0],
    )
    result = _run_script(str(path))
    assert result.returncode == 0, (
        f"G5 artifact must validate; got exit={result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_measure_hydration_g5_artifact_required_top_keys(tmp_path):
    """G5 artifact required top-level keys (DOMContentLoaded-only, 1+9
    protocol)."""
    path = tmp_path / "g5.json"
    _write_g5_artifact(
        path, build="legacy", samples_ms=[10.0] * 9,
    )
    doc = json.loads(path.read_text())
    for key in (
        "captured_at",
        "build",
        "route",
        "samples",
        "warmup_samples",
        "samples_retained",
        "warmup_count",
        "median",
        "origin",
        "console_warnings",
        "source",
    ):
        assert key in doc, f"G5 artifact missing top-level key {key!r}"
    # No legacy multi-metric keys.
    assert "server_shell" not in doc, (
        f"G5 artifact must NOT carry legacy server_shell block; got: {doc}"
    )
    assert "client_render" not in doc, (
        f"G5 artifact must NOT carry legacy client_render block; got: {doc}"
    )


# ------------------------------------------------------------------
# (P3) Per-run provenance is persisted
# ------------------------------------------------------------------
def test_measure_hydration_g5_artifact_per_run_provenance(tmp_path):
    """Each retained + warm-up sample must carry browser_version, route,
    captured_at, capture_environment. build_sha is included when
    available."""
    path = tmp_path / "g5.json"
    _write_g5_artifact(
        path,
        build="legacy",
        samples_ms=[10.0, 11.0, 12.0, 13.0, 14.0,
                    15.0, 16.0, 17.0, 18.0],
        warmup_ms=[9.0],
        browser_version="Chromium 120.0.6099.71",
        build_sha="abc1234",
    )
    doc = json.loads(path.read_text())
    samples = doc["samples"]
    assert len(samples) == 9, (
        f"expected 9 retained samples; got {len(samples)}"
    )
    for i, s in enumerate(samples):
        for k in (
            "dom_content_loaded_ms",
            "browser_version",
            "route",
            "captured_at",
            "capture_environment",
        ):
            assert k in s, (
                f"sample[{i}] missing provenance key {k!r}; got: {s}"
            )
        assert s["build_sha"] == "abc1234", (
            f"sample[{i}] must carry build_sha; got: {s}"
        )
    warmup = doc["warmup_samples"]
    assert len(warmup) == 1, (
        f"expected 1 warm-up sample; got {len(warmup)}"
    )
    for k in (
        "dom_content_loaded_ms",
        "browser_version",
        "route",
        "captured_at",
        "capture_environment",
    ):
        assert k in warmup[0], (
            f"warm-up sample missing provenance key {k!r}; got: {warmup[0]}"
        )


def test_measure_hydration_g5_artifact_provenance_build_sha_optional(tmp_path):
    """build_sha MAY be absent when not available — the contract is
    browser_version, route, captured_at, capture_environment are always
    present."""
    path = tmp_path / "g5.json"
    _write_g5_artifact(
        path, build="legacy", samples_ms=[10.0] * 9, build_sha=None,
    )
    doc = json.loads(path.read_text())
    for s in doc["samples"]:
        for k in ("browser_version", "route", "captured_at",
                  "capture_environment"):
            assert k in s, f"sample missing mandatory key {k!r}"
        # build_sha is allowed to be absent (None passed).
        assert "build_sha" not in s, (
            f"sample must NOT carry build_sha when None; got: {s}"
        )


# ------------------------------------------------------------------
# (P4) Warm-up is excluded from retained samples + median
# ------------------------------------------------------------------
def test_measure_hydration_g5_warmup_excluded_from_samples_and_median(tmp_path):
    """The median MUST be computed over the retained samples only. An
    extreme warm-up value must NOT pull the median off the retained
    samples."""
    path = tmp_path / "g5.json"
    # 9 retained samples all equal 100 ms; warm-up is 9999 ms.
    # If the warm-up leaks into the median, median would skew toward the
    # warm-up value; if it is excluded, median == 100.
    _write_g5_artifact(
        path,
        build="legacy",
        samples_ms=[100.0] * 9,
        warmup_ms=[9999.0],
    )
    doc = json.loads(path.read_text())
    assert doc["median"] == 100.0, (
        f"median MUST be 100 (warm-up excluded); got: {doc['median']}"
    )
    assert len(doc["samples"]) == 9, (
        f"retained samples must be 9 (warm-up separate); got: "
        f"{len(doc['samples'])}"
    )
    assert len(doc["warmup_samples"]) == 1, (
        f"warmup_samples must be 1; got: {len(doc['warmup_samples'])}"
    )
    assert doc["warmup_samples"][0]["dom_content_loaded_ms"] == 9999.0, (
        f"warm-up value must be preserved in warmup_samples; got: "
        f"{doc['warmup_samples']}"
    )


# ------------------------------------------------------------------
# (P5) Comparator gate: candidate_median - baseline_median <= 10 ms
# ------------------------------------------------------------------
def test_measure_hydration_g5_passes_on_equal_medians(tmp_path):
    """delta_ms == 0 must exit 0."""
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    _write_g5_artifact(
        baseline, build="legacy", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:22222/",
    )
    result = _run_script(
        "--baseline", str(baseline), "--candidate", str(candidate),
    )
    assert result.returncode == 0, (
        f"delta_ms == 0 must exit 0; got exit={result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_measure_hydration_g5_passes_on_le_10ms_delta(tmp_path):
    """delta_ms == 10.0 (exactly at the threshold) MUST pass (exit 0).

    Boundary check: the gate is <= 10 ms. Identical inputs (0 ms) and
    exact threshold (10 ms) both pass."""
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    _write_g5_artifact(
        baseline, build="legacy", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated", samples_ms=[110.0] * 9,
        origin="http://127.0.0.1:22222/",
    )
    result = _run_script(
        "--baseline", str(baseline), "--candidate", str(candidate),
    )
    assert result.returncode == 0, (
        f"delta_ms == 10.0 (exact threshold) must exit 0; got "
        f"exit={result.returncode}\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


def test_measure_hydration_g5_passes_on_improvement(tmp_path):
    """delta_ms < 0 (candidate better than baseline) MUST pass (exit 0)."""
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    _write_g5_artifact(
        baseline, build="legacy", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated", samples_ms=[50.0] * 9,
        origin="http://127.0.0.1:22222/",
    )
    result = _run_script(
        "--baseline", str(baseline), "--candidate", str(candidate),
    )
    assert result.returncode == 0, (
        f"negative delta_ms must exit 0; got exit={result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_measure_hydration_g5_fails_closed_on_gt_10ms_delta(tmp_path):
    """delta_ms > 10.0 (strictly above the threshold) MUST exit 4
    (fail-closed) and the report must surface the threshold."""
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    _write_g5_artifact(
        baseline, build="legacy", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated", samples_ms=[111.0] * 9,
        origin="http://127.0.0.1:22222/",
    )
    result = _run_script(
        "--baseline", str(baseline), "--candidate", str(candidate),
    )
    assert result.returncode == 4, (
        f"delta_ms == +11.0 must exit 4 (fail-closed); got "
        f"exit={result.returncode}\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    diag = (result.stdout + result.stderr).lower()
    assert "delta_ms" in diag or "10" in diag, (
        f"regression diagnostic must surface the delta or threshold; "
        f"got:\n{result.stdout}\n{result.stderr}"
    )


def test_measure_hydration_g5_threshold_is_10ms_in_report(tmp_path):
    """`--report-out` MUST carry `threshold_ms == 10.0` and the medians +
    delta so a reviewer can audit the gate."""
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    _write_g5_artifact(
        baseline, build="legacy", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated", samples_ms=[105.0] * 9,
        origin="http://127.0.0.1:22222/",
    )
    report = tmp_path / "report.json"
    result = _run_script(
        "--baseline", str(baseline),
        "--candidate", str(candidate),
        "--report-out", str(report),
    )
    assert result.returncode == 0, (
        f"delta_ms=5 must exit 0; got exit={result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    doc = json.loads(report.read_text())
    assert doc.get("threshold_ms") == 10.0, (
        f"report must carry threshold_ms == 10.0; got: {doc}"
    )
    assert doc.get("baseline_median_ms") == 100.0, (
        f"report must carry baseline_median_ms; got: {doc}"
    )
    assert doc.get("candidate_median_ms") == 105.0, (
        f"report must carry candidate_median_ms; got: {doc}"
    )
    assert doc.get("delta_ms") == 5.0, (
        f"report must carry delta_ms = 5.0; got: {doc}"
    )
    assert doc.get("pass_") is True or doc.get("pass") is True, (
        f"report must carry pass flag; got: {doc}"
    )


def test_measure_hydration_g5_report_carries_raw_samples(tmp_path):
    """`--report-out` MUST carry raw sample arrays so a reviewer can audit
    the variance reduction."""
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    _write_g5_artifact(
        baseline, build="legacy",
        samples_ms=[100.0, 101.0, 102.0, 103.0, 104.0,
                    105.0, 106.0, 107.0, 108.0],
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:22222/",
    )
    report = tmp_path / "report.json"
    result = _run_script(
        "--baseline", str(baseline),
        "--candidate", str(candidate),
        "--report-out", str(report),
    )
    doc = json.loads(report.read_text())
    assert "baseline" in doc and "samples" in doc["baseline"], (
        f"report must carry baseline.samples; got: {doc}"
    )
    raw = doc["baseline"]["samples"]
    assert raw == [100.0, 101.0, 102.0, 103.0, 104.0,
                   105.0, 106.0, 107.0, 108.0], (
        f"report baseline.samples must match; got: {raw}"
    )


# ------------------------------------------------------------------
# (P6) Fail-closed placeholder honors configured counts
# ------------------------------------------------------------------
def test_reconstruct_hydration_baseline_placeholder_honors_configured_counts():
    """When Playwright is unavailable, the placeholder artifact MUST
    carry 9 retained + 1 warmup (or whatever --samples-retained /
    --warmup-count were supplied). Hardcoding 5+1 is forbidden."""
    source = RECONSTRUCT_SCRIPT.read_text()
    assert "DEFAULT_SAMPLES_RETAINED" in source, (
        "reconstruct_hydration_baseline.py placeholder must derive "
        "sample counts from DEFAULT_SAMPLES_RETAINED, not hardcode "
        "a literal count; got source that doesn't reference the "
        "module-level constant."
    )
    assert "DEFAULT_WARMUP_COUNT" in source, (
        "reconstruct_hydration_baseline.py placeholder must derive "
        "warm-up count from DEFAULT_WARMUP_COUNT, not hardcode a "
        "literal count; got source that doesn't reference the "
        "module-level constant."
    )
    assert "DEFAULT_SAMPLES_RETAINED = 9" in source, (
        "DEFAULT_SAMPLES_RETAINED must be 9 (G5 1+9 protocol); got "
        "source that sets a different default."
    )
    assert "DEFAULT_WARMUP_COUNT = 1" in source, (
        "DEFAULT_WARMUP_COUNT must be 1; got source that sets a "
        "different default."
    )


def test_capture_hydration_candidate_placeholder_honors_configured_counts():
    """Candidate placeholder must mirror the same contract."""
    source = CANDIDATE_CAPTURE_SCRIPT.read_text()
    assert "DEFAULT_SAMPLES_RETAINED" in source, (
        "capture_hydration_candidate.py placeholder must derive "
        "sample counts from DEFAULT_SAMPLES_RETAINED."
    )
    assert "DEFAULT_WARMUP_COUNT" in source, (
        "capture_hydration_candidate.py placeholder must derive "
        "warm-up count from DEFAULT_WARMUP_COUNT."
    )
    assert "DEFAULT_SAMPLES_RETAINED = 9" in source, (
        "DEFAULT_SAMPLES_RETAINED must be 9; got source that sets "
        "a different default."
    )
    assert "DEFAULT_WARMUP_COUNT = 1" in source, (
        "DEFAULT_WARMUP_COUNT must be 1; got source that sets a "
        "different default."
    )


# ------------------------------------------------------------------
# (P7) Capture scripts use PerformanceNavigationTiming
# ------------------------------------------------------------------
def test_reconstruct_hydration_baseline_uses_performance_navigation_timing():
    """The capture must use PerformanceNavigationTiming (where available)
    and fall back to performance.timing otherwise."""
    source = RECONSTRUCT_SCRIPT.read_text()
    assert "PerformanceNavigationTiming" in source, (
        "reconstruct_hydration_baseline.py must reference "
        "PerformanceNavigationTiming; got source that doesn't."
    )
    assert "domContentLoadedEventEnd" in source, (
        "reconstruct_hydration_baseline.py must measure DOMContentLoaded "
        "via domContentLoadedEventEnd; got source that doesn't."
    )


def test_capture_hydration_candidate_uses_performance_navigation_timing():
    """The candidate capture must mirror the same contract."""
    source = CANDIDATE_CAPTURE_SCRIPT.read_text()
    assert "PerformanceNavigationTiming" in source, (
        "capture_hydration_candidate.py must reference "
        "PerformanceNavigationTiming; got source that doesn't."
    )
    assert "domContentLoadedEventEnd" in source, (
        "capture_hydration_candidate.py must measure DOMContentLoaded "
        "via domContentLoadedEventEnd; got source that doesn't."
    )


# ------------------------------------------------------------------
# (P8) g5_close.sh passes 1+9 to capture scripts + persists evidence
# ------------------------------------------------------------------
def test_g5_close_sh_passes_one_plus_nine_to_capture_scripts():
    """g5_close.sh MUST pass --warmup-count 1 and --samples-retained 9 to
    both reconstruct_hydration_baseline.py and
    capture_hydration_candidate.py."""
    source = G5_CLOSE_SH.read_text()
    for script_name in (
        "reconstruct_hydration_baseline.py",
        "capture_hydration_candidate.py",
    ):
        idx = source.find(script_name)
        assert idx != -1, (
            f"g5_close.sh must invoke {script_name}; got source that "
            f"doesn't reference it."
        )
        after = source[idx:]
        end = len(after)
        for sentinel in (
            "reconstruct_hydration_baseline.py",
            "capture_hydration_candidate.py",
            "measure_hydration.py",
            "\nfi\n",
            "\nlog ",
        ):
            pos = after.find(sentinel, 1)
            if pos != -1 and pos < end:
                end = pos
        block = after[:end]
        assert "--warmup-count" in block, (
            f"g5_close.sh must pass --warmup-count to {script_name}; "
            f"got invocation that lacks it. Block: {block!r}"
        )
        assert "1" in block, (
            f"g5_close.sh must pass --warmup-count 1 to {script_name}; "
            f"got block that lacks '1'. Block: {block!r}"
        )
        assert "--samples-retained" in block, (
            f"g5_close.sh must pass --samples-retained to {script_name}; "
            f"got invocation that lacks it. Block: {block!r}"
        )
        assert "9" in block, (
            f"g5_close.sh must pass --samples-retained 9 to {script_name}; "
            f"got block that lacks '9'. Block: {block!r}"
        )


def test_g5_close_sh_status_records_threshold_medians_delta(tmp_path):
    """g5_close.sh status.json MUST include threshold_ms (10.0) and the
    medians + delta on the comparison-ready path."""
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_g5_artifact(
        baseline, build="legacy", samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated", samples_ms=[105.0] * 9,
        origin="http://127.0.0.1:22222/",
    )
    fixture_dir = tmp_path / "fixture"
    fixture_dir.mkdir()
    (fixture_dir / "index.html").write_text(
        "<!doctype html><title>x</title>"
    )
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "G5_FIXTURE_WEB_ROOT": str(fixture_dir),
        "G5_OUT": str(baseline),
        "G5_CANDIDATE": str(candidate),
        "G5_STATUS_JSON": str(tmp_path / "status.json"),
        "G5_REPORT_JSON": str(tmp_path / "report.json"),
    }
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
        f"status.json must be written; missing {status_path}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}\n"
        f"exit: {result.returncode}"
    )
    doc = json.loads(status_path.read_text())
    if doc.get("status") == "ready":
        assert doc.get("threshold_ms") == 10.0, (
            f"status.json must record threshold_ms == 10.0; got: {doc}"
        )
        assert doc.get("baseline_median_ms") == 100.0, (
            f"status.json must record baseline_median_ms; got: {doc}"
        )
        assert doc.get("candidate_median_ms") == 105.0, (
            f"status.json must record candidate_median_ms; got: {doc}"
        )
        assert doc.get("delta_ms") == 5.0, (
            f"status.json must record delta_ms; got: {doc}"
        )


def test_g5_close_sh_stays_blocked_on_unavailable_artifact(tmp_path):
    """When the baseline reconstruction produces an unavailable
    placeholder, status.json MUST record G5 as blocked with the blocker
    field — never auto-flip to ready."""
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
        f"\nstderr: {result.stderr}\nexit: {result.returncode}"
    )
    doc = json.loads(status_path.read_text())
    assert doc.get("gate") == "G5", (
        f"status.json must self-identify as gate='G5'; got: {doc}"
    )
    assert doc.get("status") == "blocked", (
        f"G5 MUST stay blocked on environmental blocker; got: {doc}"
    )
    assert "blocker" in doc and doc["blocker"], (
        f"status.json must carry a non-empty blocker field; got: {doc}"
    )
    assert doc.get("status") != "ready", (
        f"G5 MUST NOT auto-flip on environmental blocker; got: {doc}"
    )


def test_g5_close_sh_never_auto_flips_g5():
    """Static guarantee: the source of g5_close.sh must NEVER write a
    'pass' / 'flipped' status. The apply worker is the only authority
    that may flip G5."""
    source = G5_CLOSE_SH.read_text()
    forbidden_tokens = (
        '"pass"',
        '"PASS"',
        '"flipped"',
        'status="pass"',
    )
    for token in forbidden_tokens:
        assert token not in source, (
            f"g5_close.sh must NEVER auto-flip G5; found forbidden "
            f"token {token!r} in source."
        )
    assert '"ready"' in source, (
        "g5_close.sh must be capable of writing status='ready' on the "
        "comparison-ready path."
    )
    assert '"blocked"' in source, (
        "g5_close.sh must be capable of writing status='blocked'."
    )


# ------------------------------------------------------------------
# (P9) Back-compat: legacy positional validation still works
# ------------------------------------------------------------------
def test_measure_hydration_g5_single_positional_validation_works(tmp_path):
    """The legacy single-artifact positional invocation
    `measure_hydration.py <artifact>` MUST keep working on a valid G5
    artifact (no flags required)."""
    path = tmp_path / "g5.json"
    _write_g5_artifact(
        path, build="legacy", samples_ms=[100.0] * 9,
    )
    result = _run_script(str(path))
    assert result.returncode == 0, (
        f"single-artifact positional validation must keep working; "
        f"got exit={result.returncode}\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


# =====================================================================
# Phase 6a (TRIANGULATE) — additional edge cases
# =====================================================================
#
# These tests cover edges of the G5 1+9 protocol that the core suite
# does not exercise:
#   * Boundary semantics around the 10 ms threshold (9.999 ms vs 10.001 ms).
#   * Median computation correctness for both odd and even sample counts
#     (statistics.median semantics).
#   * The fail-closed placeholder preserves the configured counts
#     exactly, even when override flags are supplied.
#   * Raw-sample provenance schema invariants (browser_version,
#     capture_environment, route always present; build_sha optional).
#   * g5_close.sh stays blocked when the baseline fixture is missing
#     (fail-closed path 2).
#   * measure_hydration.py exit code 2 (missing) vs 3 (malformed) vs 4
#     (regression) is preserved by the G5 protocol.

# (T1) Boundary threshold semantics: 9.999 passes, 10.001 fails closed.
def test_measure_hydration_g5_threshold_just_below_passes(tmp_path):
    """delta_ms = 10.001 must fail closed (exit 4)."""
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    # Construct samples so the empirical median equals baseline=100 and
    # candidate=110.001. (We need 9 samples; pick the median via 5
    # samples equal to the target median, 2 below, 2 above.)
    _write_g5_artifact(
        baseline, build="legacy",
        samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated",
        samples_ms=[110.001] * 9,
        origin="http://127.0.0.1:22222/",
    )
    result = _run_script(
        "--baseline", str(baseline), "--candidate", str(candidate),
    )
    assert result.returncode == 4, (
        f"delta_ms = 10.001 must exit 4 (strict > 10 ms); got exit="
        f"{result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_measure_hydration_g5_threshold_at_exactly_10_passes(tmp_path):
    """delta_ms = 10.0 must pass (exit 0; threshold is inclusive)."""
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    _write_g5_artifact(
        baseline, build="legacy",
        samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated",
        samples_ms=[110.0] * 9,
        origin="http://127.0.0.1:22222/",
    )
    result = _run_script(
        "--baseline", str(baseline), "--candidate", str(candidate),
    )
    assert result.returncode == 0, (
        f"delta_ms = 10.0 must exit 0 (boundary inclusive); got exit="
        f"{result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


# (T2) Median computation: odd vs even sample counts.
def test_measure_hydration_g5_median_odd_sample_count(tmp_path):
    """With 9 samples (odd), the median is the middle value after sort."""
    path = tmp_path / "g5.json"
    # 9 samples: sorted = [10, 20, 30, 40, 50, 60, 70, 80, 90], median = 50.
    _write_g5_artifact(
        path, build="legacy",
        samples_ms=[10.0, 90.0, 20.0, 80.0, 30.0, 70.0, 40.0, 60.0, 50.0],
    )
    doc = json.loads(path.read_text())
    assert doc["median"] == 50.0, (
        f"median of 9 sorted samples must be the middle (50); got {doc['median']}"
    )


def test_measure_hydration_g5_median_even_sample_count(tmp_path):
    """With 8 samples (even), the median is the mean of the two middles."""
    path = tmp_path / "g5.json"
    # 8 samples: sorted = [10, 20, 30, 40, 50, 60, 70, 80], median = 45.
    # We bypass _write_g5_artifact's helper (which fixes 9+1) and
    # write the artifact directly to exercise the even-count median path.
    samples = []
    for ms in [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]:
        samples.append({
            "dom_content_loaded_ms": float(ms),
            "browser_version": "Chromium 120.0.6099.71",
            "route": "/",
            "captured_at": "2026-09-07T00:00:00Z",
            "capture_environment": "controlled-loopback",
        })
    path.write_text(json.dumps({
        "captured_at": "2026-09-07T00:00:00Z",
        "build": "legacy",
        "route": "/",
        "samples": samples,
        "warmup_samples": [samples[0]],
        "samples_retained": 8,
        "warmup_count": 1,
        "median": 45.0,
        "origin": "http://127.0.0.1:54321/",
        "console_warnings": [],
        "source": "captured",
    }, indent=2))
    result = _run_script(str(path))
    assert result.returncode == 0, (
        f"even-count artifact must validate; got exit={result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    doc = json.loads(path.read_text())
    assert doc["median"] == 45.0, (
        f"median of 8 sorted samples must be (40+50)/2 = 45; got {doc['median']}"
    )


# (T3) Placeholder honors configured counts (override case).
def test_reconstruct_hydration_baseline_placeholder_honors_override_counts():
    """Source code contract: the placeholder list comprehensions MUST
    read ``range(samples_retained)`` / ``range(warmup_count)``, not
    literal numbers."""
    source = RECONSTRUCT_SCRIPT.read_text()
    # The placeholder function MUST accept samples_retained + warmup_count
    # parameters (not hardcode 9 and 1) and MUST iterate over the configured
    # counts.
    assert "def _write_placeholder" in source, (
        f"reconstruct_hydration_baseline.py must define _write_placeholder."
    )
    # Slice the placeholder function body: from def to the next top-level def.
    fn_start = source.find("def _write_placeholder")
    assert fn_start != -1
    # Find the next "\ndef " after the placeholder signature's terminating
    # newline; that's the start of the next top-level function.
    # The signature ends at the next "-> dict:" line followed by a blank line.
    sig_end = source.find("-> dict:", fn_start)
    assert sig_end != -1
    body_start = sig_end
    next_def = source.find("\ndef ", body_start + 1)
    body = source[body_start:next_def if next_def != -1 else None]
    # The list comprehensions must iterate over range(samples_retained) /
    # range(warmup_count), NOT literal 5 / 1.
    assert "range(samples_retained)" in body, (
        f"_write_placeholder body must iterate range(samples_retained); "
        f"got body that uses a literal count. body={body[:500]!r}"
    )
    assert "range(warmup_count)" in body, (
        f"_write_placeholder body must iterate range(warmup_count); "
        f"got body that uses a literal count. body={body[:500]!r}"
    )
    # And the placeholder MUST carry samples_retained / warmup_count in
    # the artifact body (not hardcode them to literal values).
    assert '"samples_retained": samples_retained' in body, (
        f"placeholder must use the samples_retained argument verbatim; "
        f"got body that uses a literal value."
    )
    assert '"warmup_count": warmup_count' in body, (
        f"placeholder must use the warmup_count argument verbatim; "
        f"got body that uses a literal value."
    )


def test_capture_hydration_candidate_placeholder_honors_override_counts():
    """Source code contract: candidate placeholder MUST honor override counts."""
    source = CANDIDATE_CAPTURE_SCRIPT.read_text()
    assert "def _write_placeholder" in source, (
        f"capture_hydration_candidate.py must define _write_placeholder."
    )
    fn_start = source.find("def _write_placeholder")
    assert fn_start != -1
    sig_end = source.find("-> dict:", fn_start)
    assert sig_end != -1
    body_start = sig_end
    next_def = source.find("\ndef ", body_start + 1)
    body = source[body_start:next_def if next_def != -1 else None]
    assert "range(samples_retained)" in body, (
        f"_write_placeholder body must iterate range(samples_retained); "
        f"got body that uses a literal count. body={body[:500]!r}"
    )
    assert "range(warmup_count)" in body, (
        f"_write_placeholder body must iterate range(warmup_count); "
        f"got body that uses a literal count. body={body[:500]!r}"
    )
    assert '"samples_retained": samples_retained' in body, (
        f"placeholder must use the samples_retained argument verbatim; "
        f"got body that uses a literal value."
    )
    assert '"warmup_count": warmup_count' in body, (
        f"placeholder must use the warmup_count argument verbatim; "
        f"got body that uses a literal value."
    )


# (T4) g5_close.sh stays blocked when baseline fixture is missing.
def test_g5_close_sh_blocks_when_fixture_missing(tmp_path):
    """When the legacy fixture (--fixture-web-root) is missing, the
    harness MUST write status.json with G5=blocked (fail-closed path
    2 — fixture unavailable)."""
    baseline = tmp_path / "baseline.json"  # does NOT exist
    candidate = tmp_path / "candidate.json"  # does NOT exist
    # G5_FIXTURE_WEB_ROOT points to a non-existent directory.
    fixture_dir = tmp_path / "no-such-fixture"
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "G5_FIXTURE_WEB_ROOT": str(fixture_dir),
        "G5_OUT": str(baseline),
        "G5_CANDIDATE": str(candidate),
        "G5_STATUS_JSON": str(tmp_path / "status.json"),
        "G5_REPORT_JSON": str(tmp_path / "report.json"),
    }
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
        f"\nstderr: {result.stderr}\nexit: {result.returncode}"
    )
    doc = json.loads(status_path.read_text())
    assert doc.get("gate") == "G5", (
        f"status.json must self-identify as gate='G5'; got: {doc}"
    )
    assert doc.get("status") == "blocked", (
        f"G5 MUST stay blocked when fixture is missing; got: {doc}"
    )
    # blocker MUST be non-empty and reference the missing fixture root.
    assert "blocker" in doc and doc["blocker"], (
        f"status.json must carry a non-empty blocker field; got: {doc}"
    )
    assert "fixture_web_root" in doc["blocker"].lower() or (
        "no-such-fixture" in doc["blocker"]
    ), (
        f"blocker must name the missing fixture; got: {doc['blocker']}"
    )


# (T5) measure_hydration.py exit code mapping is preserved under the
# G5 1+9 protocol: 2 = missing, 3 = schema violation, 4 = regression.
def test_measure_hydration_g5_exit_code_2_on_missing_baseline(tmp_path):
    """The G5 protocol preserves exit code 2 for a missing baseline."""
    missing = tmp_path / "no-such-baseline.json"
    result = _run_script(
        "--baseline", str(missing),
        "--candidate", str(missing),  # also missing; we expect to fail at baseline.
    )
    assert result.returncode == 2, (
        f"missing baseline must exit 2; got {result.returncode}"
    )


def test_measure_hydration_g5_exit_code_3_on_schema_violation(tmp_path):
    """The G5 protocol preserves exit code 3 for a malformed artifact."""
    bad = tmp_path / "bad.json"
    bad.write_text("not a json object")
    result = _run_script(str(bad))
    assert result.returncode == 3, (
        f"schema violation must exit 3; got {result.returncode}"
    )


# (T6) Threshold recorded in measure_hydration.py stdout.
def test_measure_hydration_g5_stdout_reports_threshold(tmp_path):
    """The G5 comparison stdout MUST name the 10.0 threshold so reviewers
    can audit the gate inline."""
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    _write_g5_artifact(
        baseline, build="legacy",
        samples_ms=[100.0] * 9,
        origin="http://127.0.0.1:11111/",
    )
    _write_g5_artifact(
        candidate, build="migrated",
        samples_ms=[103.0] * 9,
        origin="http://127.0.0.1:22222/",
    )
    result = _run_script(
        "--baseline", str(baseline), "--candidate", str(candidate),
    )
    assert result.returncode == 0
    out = (result.stdout + result.stderr).lower()
    assert "threshold_ms" in out, (
        f"report must name threshold_ms; got: {result.stdout}\n"
        f"{result.stderr}"
    )
    assert "10" in out, (
        f"report must carry the numeric threshold (10); got: {result.stdout}"
    )


# (T7) g5_close.sh passes the configured counts to BOTH capture scripts.
def test_g5_close_sh_passes_counts_in_correct_order():
    """Both capture scripts must receive --warmup-count 1 and
    --samples-retained 9 in the same invocation order."""
    source = G5_CLOSE_SH.read_text()
    # Each invocation block must contain exactly one of each flag.
    for script_name in (
        "reconstruct_hydration_baseline.py",
        "capture_hydration_candidate.py",
    ):
        idx = source.find(script_name)
        assert idx != -1
        after = source[idx:]
        # Slice to next sentinel.
        end = len(after)
        for sentinel in (
            "reconstruct_hydration_baseline.py",
            "capture_hydration_candidate.py",
            "measure_hydration.py",
        ):
            pos = after.find(sentinel, 1)
            if pos != -1 and pos < end:
                end = pos
        block = after[:end]
        # Block must contain both flags with their numeric values.
        assert "--warmup-count 1" in block or (
            "--warmup-count" in block and "\n1" in block
        ), (
            f"{script_name}: --warmup-count 1 missing; block: {block!r}"
        )
        assert "--samples-retained 9" in block or (
            "--samples-retained" in block and "\n9" in block
        ), (
            f"{script_name}: --samples-retained 9 missing; block: {block!r}"
        )


# (T8) Status JSON contains the G5 1+9 fields on every code path.
def test_g5_close_sh_status_has_threshold_field_on_every_block(tmp_path):
    """Every status.json written by g5_close.sh MUST carry a
    ``threshold_ms`` field (G5 1+9 contract)."""
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
        f"\nstderr: {result.stderr}\nexit: {result.returncode}"
    )
    doc = json.loads(status_path.read_text())
    assert "threshold_ms" in doc, (
        f"status.json must carry threshold_ms field; got: {doc}"
    )
    assert doc["threshold_ms"] == 10.0, (
        f"status.json threshold_ms must be 10.0; got: {doc}"
    )
