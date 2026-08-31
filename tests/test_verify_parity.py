"""Strict-TDD contract tests for scripts/verify_parity.py (G4 parity aggregator).

Three chained commits:
  - PR1: directory preflight, versioned common-header schema
    (schema_version + captured_at), atomic aggregate emission.
  - PR2: per-report structural validation, pairwise comparators,
    regression-driven gate closing at EXIT_REGRESSION.
  - PR3: hardening + triangulation tests (CLI defaults, edge cases,
    write-failure handling, symmetric regression scenarios).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "verify_parity.py"
REPORT_NAMES = ("navigation", "api", "search", "a11y", "browser-state")
AGGREGATE_NAME = "parity-aggregate.json"
SCHEMA_VERSION = "1.0.0"
REQUIRED_BROWSER_STATE_KEYS = frozenset({
    "last-taxon-id", "tree-source", "selected-realm", "version-banner-dismissed",
})


def _run(argv, *, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPT), *argv],
                          capture_output=True, text=True, check=False, cwd=cwd)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _days_ago_iso(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _minimal_payload(*, captured_at: str | None = None) -> dict:
    """Header-only payload used by preflight + common-schema tests."""
    return {"schema_version": SCHEMA_VERSION,
            "captured_at": captured_at or _now_iso()}


def _navigation(*, captured_at: str | None = None,
                paths: list[dict] | None = None) -> dict:
    return {
        **_minimal_payload(captured_at=captured_at),
        "paths": paths if paths is not None else [
            {"path": "/", "status": 200},
            {"path": "/species", "status": 200},
            {"path": "/api/health", "status": 200},
        ],
    }


def _api(*, captured_at: str | None = None,
         endpoints: list[dict] | None = None) -> dict:
    return {
        **_minimal_payload(captured_at=captured_at),
        "endpoints": endpoints if endpoints is not None else [
            {"path": "/api/health", "status": 200},
            {"path": "/api/species", "status": 200},
        ],
    }


def _search(*, captured_at: str | None = None,
            queries: list[dict] | None = None) -> dict:
    return {
        **_minimal_payload(captured_at=captured_at),
        "queries": queries if queries is not None else [
            {"query": "trout", "result_count": 12},
            {"query": "salmon", "result_count": 7},
        ],
    }


def _a11y(*, captured_at: str | None = None, score: float = 92.0) -> dict:
    return {**_minimal_payload(captured_at=captured_at), "score": score}


def _browser_state(*, captured_at: str | None = None,
                   keys: dict | None = None) -> dict:
    return {
        **_minimal_payload(captured_at=captured_at),
        "keys": keys if keys is not None else {
            "last-taxon-id": "tx-001",
            "tree-source": "freshwater",
            "selected-realm": "freshwater",
            "version-banner-dismissed": True,
        },
    }


def _write_reports(root: Path, overrides: dict | None = None) -> Path:
    """Write all five reports under ``root``. Per-report overrides win.

    ``overrides`` is keyed by report name (with hyphens).
    """
    root.mkdir(parents=True, exist_ok=True)
    overrides = overrides or {}
    builders = {
        "navigation": _navigation,
        "api": _api,
        "search": _search,
        "a11y": _a11y,
        "browser-state": _browser_state,
    }
    for name in REPORT_NAMES:
        payload = overrides.get(name) or builders[name]()
        (root / f"{name}.json").write_text(json.dumps(payload))
    return root


def _aggregate(out: Path) -> dict:
    p = out / AGGREGATE_NAME
    assert p.is_file(), f"no aggregate at {p}"
    return json.loads(p.read_text())


def test_legacy_dir_missing_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = tmp_path / "does_not_exist"
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr


def test_candidate_dir_missing_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate = tmp_path / "does_not_exist"
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr


@pytest.mark.parametrize("missing", REPORT_NAMES)
def test_report_missing_in_legacy_fails_closed(tmp_path, missing):
    out = tmp_path / "out"
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    for name in REPORT_NAMES:
        if name != missing:
            (legacy / f"{name}.json").write_text(json.dumps(_minimal_payload()))
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr
    assert missing in r.stderr, r.stderr


@pytest.mark.parametrize("missing", REPORT_NAMES)
def test_report_missing_in_candidate_fails_closed(tmp_path, missing):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    for name in REPORT_NAMES:
        if name != missing:
            (candidate / f"{name}.json").write_text(json.dumps(_minimal_payload()))
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr
    assert missing in r.stderr, r.stderr


def test_wrong_schema_version_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    bad = json.loads((legacy / "navigation.json").read_text())
    bad["schema_version"] = "0.9.0"
    (legacy / "navigation.json").write_text(json.dumps(bad))
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr
    assert "schema_version" in r.stderr, r.stderr


def test_missing_schema_version_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    bad = json.loads((legacy / "navigation.json").read_text())
    bad.pop("schema_version")
    (legacy / "navigation.json").write_text(json.dumps(bad))
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr


def test_stale_legacy_capture_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    bad = json.loads((legacy / "navigation.json").read_text())
    bad["captured_at"] = _days_ago_iso(10)
    (legacy / "navigation.json").write_text(json.dumps(bad))
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr
    assert "stale" in r.stderr.lower() or "stale" in r.stdout.lower(), r.stderr


def test_complete_pass_emits_aggregate_atomically(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode == 0, r.stderr
    agg = _aggregate(out)
    assert agg["schema_version"] == SCHEMA_VERSION
    assert agg["overall_status"] == "passed"
    assert set(agg["reports"]) == set(REPORT_NAMES)
    for name in REPORT_NAMES:
        assert agg["reports"][name]["status"] == "passed", name
        assert agg["reports"][name]["reasons"] == [], name
    assert agg["legacy_dir"].endswith("legacy")
    assert agg["candidate_dir"].endswith("candidate")
    assert "generated_at" in agg
    datetime.strptime(agg["generated_at"], "%Y-%m-%dT%H:%M:%SZ")


def test_help_exits_zero(tmp_path):
    r = _run(["--help"])
    assert r.returncode == 0, r.stderr
    assert "legacy-dir" in r.stdout
    assert "candidate-dir" in r.stdout


def test_missing_required_args_fails_usage(tmp_path):
    r = _run([])
    assert r.returncode != 0
    assert "usage" in (r.stderr + r.stdout).lower()


def test_navigation_path_set_mismatch_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate_nav = _navigation(paths=[
        {"path": "/", "status": 200},
        # missing /species; added /extra
        {"path": "/extra", "status": 200},
        {"path": "/api/health", "status": 200},
    ])
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"navigation": candidate_nav})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr
    assert "navigation" in r.stderr, r.stderr


def test_navigation_status_mismatch_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate_nav = _navigation(paths=[
        {"path": "/", "status": 200},
        {"path": "/species", "status": 500},   # regression
        {"path": "/api/health", "status": 200},
    ])
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"navigation": candidate_nav})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr


def test_api_endpoint_mismatch_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate_api = _api(endpoints=[
        {"path": "/api/health", "status": 200},
        {"path": "/api/species", "status": 404},   # regression
    ])
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"api": candidate_api})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr
    assert "api" in r.stderr, r.stderr


def test_search_query_count_mismatch_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate_search = _search(queries=[
        {"query": "trout", "result_count": 12},
        {"query": "salmon", "result_count": 0},   # regression: was 7
    ])
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"search": candidate_search})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr


def test_browser_state_key_set_mismatch_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate_bs = _browser_state(keys={
        "last-taxon-id": "tx-001",
        "tree-source": "freshwater",
        "selected-realm": "freshwater",
        # missing version-banner-dismissed
    })
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"browser-state": candidate_bs})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr
    assert "browser-state" in r.stderr, r.stderr


def test_partial_pass_does_not_emit_aggregate(tmp_path):
    """A single threshold failure MUST close the gate; no aggregate written."""
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"a11y": _a11y(score=80.0)})   # regression vs 92.0
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr


def test_multiple_reports_failing_aggregates_reasons(tmp_path):
    """Simultaneous regressions in two reports must close the gate and
    surface every reason in stderr; no aggregate is emitted."""
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy",
                            overrides={"a11y": _a11y(score=95.0)})
    candidate_bs = _browser_state(keys={
        "last-taxon-id": "tx-001",
        "tree-source": "marine",  # value drift
        "selected-realm": "freshwater",
        "version-banner-dismissed": True,
    })
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"a11y": _a11y(score=70.0),
                                          "browser-state": candidate_bs})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file()
    assert "a11y" in r.stderr and "browser-state" in r.stderr, r.stderr


# ── PR3: hardening + triangulation tests ─────────────────────────────────


def test_a11y_score_below_legacy_fails_closed(tmp_path):
    """a11y score strictly below legacy is a regression."""
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy",
                            overrides={"a11y": _a11y(score=95.0)})
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"a11y": _a11y(score=80.0)})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr
    assert "a11y" in r.stderr, r.stderr


def test_a11y_score_just_above_legacy_passes(tmp_path):
    """A candidate a11y score strictly greater than legacy passes."""
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy",
                            overrides={"a11y": _a11y(score=88.0)})
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"a11y": _a11y(score=88.5)})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode == 0, r.stderr


def test_a11y_score_equal_to_legacy_passes(tmp_path):
    """Equal a11y scores are NOT a regression."""
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy",
                            overrides={"a11y": _a11y(score=90.0)})
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"a11y": _a11y(score=90.0)})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode == 0, r.stderr


def test_browser_state_value_mismatch_fails_closed(tmp_path):
    """A value drift in any browser-state key closes the gate."""
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate_bs = _browser_state(keys={
        "last-taxon-id": "tx-001",
        "tree-source": "marine",      # regression: was freshwater
        "selected-realm": "freshwater",
        "version-banner-dismissed": True,
    })
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"browser-state": candidate_bs})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr


def test_malformed_json_in_legacy_navigation_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    (legacy / "navigation.json").write_text("{ this is : not json")
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr
    assert "navigation" in r.stderr, r.stderr


def test_stale_candidate_capture_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"a11y": _a11y(captured_at=_days_ago_iso(30))})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr


def test_max_staleness_days_overrides_default(tmp_path):
    """A 5-day-old capture passes with --max-staleness-days 10."""
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy",
                            overrides={"navigation":
                                _navigation(captured_at=_days_ago_iso(5))})
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out), "--max-staleness-days", "10"])
    assert r.returncode == 0, r.stderr


def test_max_staleness_days_accepts_float(tmp_path):
    """--max-staleness-days is a float; fractional days are accepted."""
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy",
                            overrides={"navigation":
                                _navigation(captured_at=_days_ago_iso(0.6))})
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out), "--max-staleness-days", "0.5"])
    assert r.returncode != 0, r.stderr
    assert not (out / AGGREGATE_NAME).is_file(), r.stderr


def test_non_object_json_in_navigation_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    (legacy / "navigation.json").write_text(json.dumps(["not", "an", "object"]))
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr


def test_non_string_path_in_navigation_fails_closed(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    (legacy / "navigation.json").write_text(json.dumps({
        "schema_version": SCHEMA_VERSION, "captured_at": _now_iso(),
        "paths": [{"path": 123, "status": 200}],
    }))
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr


def test_required_browser_state_keys_are_enforced(tmp_path):
    """A browser-state report missing a required design.md key fails closed."""
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate_bs = _browser_state(keys={
        "last-taxon-id": "tx-001",
        "tree-source": "freshwater",
        # missing selected-realm + version-banner-dismissed
        "version-banner-dismissed": True,
    })
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"browser-state": candidate_bs})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert "selected-realm" in r.stderr or "browser-state" in r.stderr, r.stderr


def test_legacy_missing_required_key_is_a_schema_error(tmp_path):
    """Mirror symmetry: LEGACY missing a required browser-state key fails closed."""
    out = tmp_path / "out"
    legacy_bs = _browser_state(keys={
        "last-taxon-id": "tx-001",
        "tree-source": "freshwater",
        "selected-realm": "freshwater",
        # missing version-banner-dismissed
    })
    legacy = _write_reports(tmp_path / "legacy",
                            overrides={"browser-state": legacy_bs})
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0, r.stderr
    assert "legacy" in r.stderr and "browser-state" in r.stderr, r.stderr
    assert not (out / AGGREGATE_NAME).is_file()


def test_no_partial_aggregate_left_on_failure(tmp_path):
    """Verifier MUST NOT leave a stale ``parity-aggregate.json`` behind on failure."""
    out = tmp_path / "out"
    out.mkdir()
    (out / AGGREGATE_NAME).write_text('{"legacy": "stale"}')
    legacy = _write_reports(tmp_path / "legacy")
    candidate = _write_reports(tmp_path / "candidate",
                               overrides={"a11y": _a11y(score=50.0)})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode != 0
    body = (out / AGGREGATE_NAME).read_text()
    assert body == '{"legacy": "stale"}', (
        "verifier must not overwrite a pre-existing aggregate on failure"
    )


def test_aggregate_output_default_is_cwd(tmp_path, monkeypatch):
    """With no --output flag, the aggregate is written to the cwd."""
    monkeypatch.chdir(tmp_path)
    legacy = _write_reports(tmp_path / "legacy")
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate)])
    assert r.returncode == 0, r.stderr
    assert (tmp_path / AGGREGATE_NAME).is_file()


def test_empty_reports_pass_schema(tmp_path):
    """Empty-but-valid ``paths``, ``endpoints``, ``queries`` lists are accepted."""
    out = tmp_path / "out"
    legacy = _write_reports(
        tmp_path / "legacy",
        overrides={"navigation": _navigation(paths=[]),
                   "api": _api(endpoints=[]),
                   "search": _search(queries=[])})
    candidate = _write_reports(
        tmp_path / "candidate",
        overrides={"navigation": _navigation(paths=[]),
                   "api": _api(endpoints=[]),
                   "search": _search(queries=[])})
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode == 0, r.stderr


def test_unknown_flag_fails_usage(tmp_path):
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out), "--no-such-flag"])
    assert r.returncode != 0


def test_aggregate_is_parseable_json_with_all_keys(tmp_path):
    """The emitted aggregate MUST be valid JSON and carry all required keys."""
    out = tmp_path / "out"
    legacy = _write_reports(tmp_path / "legacy")
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode == 0, r.stderr
    p = out / AGGREGATE_NAME
    body = p.read_text()
    parsed = json.loads(body)
    for key in ("schema_version", "generated_at", "legacy_dir",
                "candidate_dir", "max_staleness_days", "reports",
                "overall_status"):
        assert key in parsed, (key, parsed)
    assert parsed["overall_status"] == "passed"


def test_aggregate_write_failure_closes_gate(tmp_path):
    """If the output directory cannot be created, the verifier exits non-zero
    (exit code 5) and emits no aggregate. We force a real OS failure by
    pointing --output at a path whose parent component is a regular file,
    so ``mkdir(parents=True, exist_ok=True)`` raises ``FileExistsError`` /
    ``NotADirectoryError``.
    """
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    out = blocker / "out"  # parent path component is a regular file
    legacy = _write_reports(tmp_path / "legacy")
    candidate = _write_reports(tmp_path / "candidate")
    r = _run(["--legacy-dir", str(legacy), "--candidate-dir", str(candidate),
              "--output", str(out)])
    assert r.returncode == 5, r.stderr
    assert "aggregate write failed" in r.stderr, r.stderr
    assert blocker.read_text() == "not a directory"
