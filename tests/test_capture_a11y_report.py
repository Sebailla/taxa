"""G4 a11y producer-adapter tests. Hermetic filesystem only — no network.
Adapter consumes only the current tools/g4-capture/scripts/capture.mjs
evidence.json contract. Exit codes: 0 ok; 1 usage; 2 evidence missing;
3 malformed; 4 invalid score; 5 invalid timestamp; 6 write."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "capture_a11y_report.py"
VERIFY_PARITY = REPO_ROOT / "scripts" / "verify_parity.py"
ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"
SCHEMA_VERSION = "1.0.0"


def _run(args, *, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd or REPO_ROOT, capture_output=True, text=True, check=False,
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime(ISO_FMT)


def _evidence(*, captured_at: str | None = None, score: object = 0.92) -> dict:
    """Build an evidence.json dict mirroring the capture.mjs contract.
    `captured_at` defaults to recent (within 30-day staleness window)."""
    if captured_at is None:
        captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.123Z")
    return {
        "schema": "taxa.g4-capture.evidence/1",
        "url": "http://127.0.0.1:8765/index.html",
        "capturedAt": captured_at,
        "manifestEntry": {},
        "provenance": {
            "schema": "taxa.g4-capture.provenance/1",
            "nodeVersion": "v20.0.0", "lighthouseVersion": "12.2.1",
            "chromeVersion": "120.0.6099.71", "host": "ci",
            "capturedAt": captured_at,
        },
        "lighthouse": {
            "finalUrl": "http://127.0.0.1:8765/index.html",
            "fetchTime": captured_at,
            "categories": {
                "performance": {"score": 0.95, "title": "Performance"},
                "accessibility": {"score": score, "title": "Accessibility"},
                "best-practices": {"score": 0.92, "title": "Best Practices"},
                "seo": {"score": 1.0, "title": "SEO"},
            },
            "audits": {},
        },
    }


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload))


def test_usage_exit_on_no_args():
    """No-argument invocation must exit 1 (invalid CLI)."""
    assert _run([]).returncode == 1

def test_emits_a11y_with_schema_and_score(tmp_path):
    """Score preserved verbatim (no scaling); fractional seconds stripped."""
    evidence = tmp_path / "evidence.json"
    _write(evidence, _evidence(score=0.85,
                               captured_at="2026-05-12T12:00:00.123Z"))
    out_dir = tmp_path / "out"
    r = _run(["--evidence", str(evidence), "--out-dir", str(out_dir)])
    assert r.returncode == 0, r.stderr
    doc = json.loads((out_dir / "a11y.json").read_text())
    assert doc["schema_version"] == SCHEMA_VERSION
    assert doc["score"] == 0.85, f"score must NOT be scaled; got {doc['score']!r}"
    assert doc["captured_at"] == "2026-05-12T12:00:00Z", (
        f"fractional seconds must be stripped; got {doc['captured_at']!r}"
    )


def test_end_to_end_validates_through_verify_parity(tmp_path):
    """Round trip: a11y.json + four placeholder reports pass verify_parity.py."""
    _write(tmp_path / "evidence.json", _evidence(score=0.92))
    out_dir = tmp_path / "out"
    r = _run(["--evidence", str(tmp_path / "evidence.json"),
              "--out-dir", str(out_dir)])
    assert r.returncode == 0, r.stderr
    for name, doc in (
        ("navigation", {"paths": [{"path": "/", "status": 200}]}),
        ("api", {"endpoints": [{"path": "/api/health", "status": 200}]}),
        ("search", {"queries": [{"query": "trout", "result_count": 5}]}),
        ("browser-state", {"keys": {
            "last-taxon-id": None, "tree-source": None,
            "selected-realm": None, "version-banner-dismissed": None,
        }}),
    ):
        (out_dir / f"{name}.json").write_text(json.dumps({
            "schema_version": SCHEMA_VERSION, "captured_at": _now_iso(), **doc,
        }))
    vp = subprocess.run(
        [sys.executable, str(VERIFY_PARITY),
         "--legacy-dir", str(out_dir), "--candidate-dir", str(out_dir),
         "--output", str(tmp_path / "agg"), "--max-staleness-days", "30"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert vp.returncode == 0, f"verify_parity rejected: stderr={vp.stderr}"


def test_missing_evidence_file_exits_2(tmp_path):
    out_dir = tmp_path / "out"
    r = _run(["--evidence", str(tmp_path / "no-such.json"),
              "--out-dir", str(out_dir)])
    assert r.returncode == 2, r.stderr
    assert not (out_dir / "a11y.json").exists()


def test_malformed_evidence_json_exits_3(tmp_path):
    (tmp_path / "evidence.json").write_text("{not valid json")
    r = _run(["--evidence", str(tmp_path / "evidence.json"),
              "--out-dir", str(tmp_path / "out")])
    assert r.returncode == 3, r.stderr
    assert not ((tmp_path / "out") / "a11y.json").exists()


def test_evidence_not_object_exits_3(tmp_path):
    (tmp_path / "evidence.json").write_text("[1, 2, 3]")
    r = _run(["--evidence", str(tmp_path / "evidence.json"),
              "--out-dir", str(tmp_path / "out")])
    assert r.returncode == 3, r.stderr
    assert not ((tmp_path / "out") / "a11y.json").exists()


def test_missing_accessibility_category_exits_4(tmp_path):
    payload = _evidence()
    payload["lighthouse"]["categories"] = {
        "performance": {"score": 0.9, "title": "P"},
        "best-practices": {"score": 0.9, "title": "BP"},
        "seo": {"score": 0.9, "title": "SEO"},
    }
    _write(tmp_path / "evidence.json", payload)
    r = _run(["--evidence", str(tmp_path / "evidence.json"),
              "--out-dir", str(tmp_path / "out")])
    assert r.returncode == 4, r.stderr
    assert not ((tmp_path / "out") / "a11y.json").exists()


@pytest.mark.parametrize("bad_score", [None, True, "0.92"])
def test_invalid_score_exits_4(tmp_path, bad_score):
    """Score null, bool, or string must exit 4 (bool tricky: True is int in Python)."""
    _write(tmp_path / "evidence.json", _evidence(score=bad_score))
    r = _run(["--evidence", str(tmp_path / "evidence.json"),
              "--out-dir", str(tmp_path / "out")])
    assert r.returncode == 4, r.stderr
    assert not ((tmp_path / "out") / "a11y.json").exists()


def test_missing_captured_at_exits_5(tmp_path):
    payload = _evidence()
    del payload["capturedAt"]
    _write(tmp_path / "evidence.json", payload)
    r = _run(["--evidence", str(tmp_path / "evidence.json"),
              "--out-dir", str(tmp_path / "out")])
    assert r.returncode == 5, r.stderr
    assert not ((tmp_path / "out") / "a11y.json").exists()


def test_invalid_timestamp_exits_5(tmp_path):
    _write(tmp_path / "evidence.json", _evidence(captured_at="not-an-iso-string"))
    r = _run(["--evidence", str(tmp_path / "evidence.json"),
              "--out-dir", str(tmp_path / "out")])
    assert r.returncode == 5, r.stderr
    assert not ((tmp_path / "out") / "a11y.json").exists()


def test_atomic_write_replaces_existing_a11y(tmp_path):
    """Pre-existing a11y.json MUST be replaced atomically with the new payload."""
    _write(tmp_path / "evidence.json", _evidence(score=0.85))
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    stale = out_dir / "a11y.json"
    stale.write_text(json.dumps({
        "schema_version": "wrong", "captured_at": "1970-01-01T00:00:00Z",
        "score": -1.0,
    }))
    r = _run(["--evidence", str(tmp_path / "evidence.json"),
              "--out-dir", str(out_dir)])
    assert r.returncode == 0, r.stderr
    doc = json.loads(stale.read_text())
    assert doc["score"] == 0.85 and doc["schema_version"] == SCHEMA_VERSION


def test_write_failure_exits_6_no_partial(tmp_path):
    """Directory at a11y.json blocks os.replace → exit 6, no temp files."""
    _write(tmp_path / "evidence.json", _evidence(score=0.92))
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "a11y.json").mkdir()
    r = _run(["--evidence", str(tmp_path / "evidence.json"),
              "--out-dir", str(out_dir)])
    assert r.returncode == 6, r.stderr
    leftovers = [p.name for p in out_dir.iterdir()
                 if p.name.startswith(".a11y.json.")]
    assert leftovers == [], f"atomic write must clean up temp files; got {leftovers}"


# TRIANGULATE


@pytest.mark.parametrize("score, ts_in, ts_out", [
    (0, "2026-09-10T12:00:00Z", "2026-09-10T12:00:00Z"),
    (1, "2026-09-10T12:00:00Z", "2026-09-10T12:00:00Z"),
    (0.923456789, "2026-09-10T12:00:00.500Z", "2026-09-10T12:00:00Z"),
])
def test_score_boundaries_and_timestamp_verbatim(tmp_path, score, ts_in, ts_out):
    """TRIANGULATE: boundary scores (0, 1) + float precision preserved;
    captured_at without fractional seconds is verbatim passthrough."""
    _write(tmp_path / "evidence.json", _evidence(score=score, captured_at=ts_in))
    r = _run(["--evidence", str(tmp_path / "evidence.json"),
              "--out-dir", str(tmp_path / "out")])
    assert r.returncode == 0, r.stderr
    doc = json.loads(((tmp_path / "out") / "a11y.json").read_text())
    assert doc["score"] == score, f"score={score} must be preserved; got {doc['score']!r}"
    assert doc["captured_at"] == ts_out


def test_dry_run_synthetic_evidence_works(tmp_path):
    """TRIANGULATE: capture.mjs --dry-run sets synthetic=true + omits fetchTime."""
    payload = _evidence(score=0.95, captured_at="2026-09-10T12:00:00.123Z")
    payload["lighthouse"]["synthetic"] = True
    payload["lighthouse"].pop("fetchTime", None)
    _write(tmp_path / "evidence.json", payload)
    r = _run(["--evidence", str(tmp_path / "evidence.json"),
              "--out-dir", str(tmp_path / "out")])
    assert r.returncode == 0, r.stderr
    doc = json.loads(((tmp_path / "out") / "a11y.json").read_text())
    assert doc["score"] == 0.95
    assert doc["captured_at"] == "2026-09-10T12:00:00Z"