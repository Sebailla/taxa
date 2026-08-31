"""Strict-TDD contract tests for scripts/verify_parity.py (G4 parity aggregator).

PR1 slice: directory preflight, versioned common-header schema
(schema_version + captured_at), atomic aggregate emission. Per-report
structural validation + pairwise regression detection land in PR2;
triangulation tests land in PR3.
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
