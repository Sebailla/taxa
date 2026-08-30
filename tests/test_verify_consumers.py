"""Strict-TDD contract tests for scripts/verify_consumers.py (G3 verifier).

Covers the G3 manifest contract: fail-closed unless every consumer is fully
selected; atomically emit CONSUMER-READINESS.json only when every selected
verifier check passes. Tests use synthetic selected tmp manifests only;
real pytest invocation is reserved for non-G3 work units.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "verify_consumers.py"
MANIFEST = REPO_ROOT / "openspec" / "changes" / "migrate-nextjs-tailwind4" / "cutover-manifest.json"


def _run(argv, *, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPT), *argv],
                          capture_output=True, text=True, check=False, cwd=cwd)


def _readiness(out: Path) -> dict:
    p = out / "CONSUMER-READINESS.json"
    assert p.is_file(), f"no readiness at {p}"
    return json.loads(p.read_text())


def _consumer(*, idx: str, cmd: str = ":", expect: str = "ok",
              repl_status: str = "selected", repl_path: str = "/new/path",
              activation: str = "selected") -> dict:
    """Build one well-formed consumer dict for synthetic manifests."""
    return {"id": idx, "ownership_edge": "fastapi_web_mount",
            "current_path": f"web/legacy/{idx}.html",
            "replacement": {"status": repl_status, "path": repl_path},
            "verification": {"command": cmd, "expect": expect},
            "activation_status": activation,
            "rollback": f"git revert <pr3e-sha> restores {idx}"}


def _base_manifest(consumers: list[dict], change: str = "migrate-nextjs-tailwind4") -> dict:
    """Build one well-formed top-level manifest for synthetic use."""
    return {"$schema_version": "1.0.0", "change": change,
            "planning_artifact": "cutover-manifest",
            "generated_by": "test fixture (synthetic)",
            "scope_intent": "synthetic selected coverage",
            "anchor": "design.md::§3.3.3",
            "fail_closed_summary": "synthetic",
            "edges": [{"id": "fastapi_web_mount",
                       "label": "FastAPI web mount ownership edge",
                       "anchor": "api/server.py:1815",
                       "single_origin_contract": "127.0.0.1:8765"}],
            "consumers": consumers,
            "selection_invariants": {"approach_status": "test"},
            "verifier_contract_summary": {"threshold": "synthetic"}}


def _write_manifest(tmp_path: Path, manifest: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest))
    return p


def test_unselected_real_manifest_fails_closed_no_artifact(tmp_path):
    """Real merged manifest has every consumer unselected → exit non-zero,
    NO CONSUMER-READINESS.json emitted (G3 fail-closed invariant)."""
    out = tmp_path / "out"
    r = _run(["--manifest", str(MANIFEST), "--out", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / "CONSUMER-READINESS.json").is_file(), r.stderr
    assert "unselected" in r.stderr or "selection" in r.stderr.lower(), r.stderr


def test_synthetic_partial_unselected_fails_closed(tmp_path):
    """Two consumers; one unselected → fail-closed, no artifact, no check runs."""
    out = tmp_path / "out"
    m = _base_manifest([_consumer(idx="a-1"),
                        _consumer(idx="a-2", activation="unselected")])
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "a-2" in r.stderr and "unselected" in r.stderr


def test_synthetic_replacement_unselected_fails_closed(tmp_path):
    """activation selected but replacement.status unselected → fail-closed."""
    out = tmp_path / "out"
    m = _base_manifest([_consumer(idx="a-1"),
                        _consumer(idx="a-2", repl_status="unselected",
                                  repl_path="")])
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "a-2" in r.stderr and "replacement.status unselected" in r.stderr


def test_synthetic_selected_passing_checks_emit_atomic_artifact(tmp_path):
    """All selected, all checks pass → CONSUMER-READINESS.json emitted atomically
    (no temp leftover) with one entry per consumer and all_selected=True."""
    out = tmp_path / "out"
    cs = [_consumer(idx=f"a-{i}") for i in range(3)]
    m = _base_manifest(cs)
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode == 0, r.stderr
    body = _readiness(out)
    assert body["all_selected"] is True
    assert {c["id"] for c in body["consumers"]} == {"a-0", "a-1", "a-2"}
    leftovers = [p.name for p in out.rglob("*")
                 if p.is_file() and p.name.startswith(".CONSUMER-READINESS")]
    assert not leftovers, leftovers


def test_synthetic_selected_with_failing_check_no_artifact(tmp_path):
    """All consumers selected schema-wise, but one verification.command
    exits non-zero → fail-closed: exit non-zero, no artifact, no temp leftover."""
    out = tmp_path / "out"
    cs = [_consumer(idx="ok-1"),
          _consumer(idx="boom", cmd="false"),
          _consumer(idx="ok-2")]
    m = _base_manifest(cs)
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0, r.stderr
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "boom" in r.stderr and "exited 1" in r.stderr
    temps = [p.name for p in out.rglob("*")
             if p.is_file() and p.name.startswith(".CONSUMER-READINESS")]
    assert not temps, temps


def test_synthetic_selected_multi_check_failures_all_reported(tmp_path):
    """Two failing checks → both consumer IDs appear in stderr (partial
    readiness is impossible; every check is independently gated)."""
    out = tmp_path / "out"
    cs = [_consumer(idx="boom-a", cmd="false"),
          _consumer(idx="boom-b", cmd="sh -c 'exit 7'")]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "boom-a" in r.stderr and "boom-b" in r.stderr


def test_duplicate_consumer_ids_fail_closed(tmp_path):
    """Schema rejects duplicate consumer IDs (G3 unique-ID rule)."""
    out = tmp_path / "out"
    m = _base_manifest([_consumer(idx="dup-1"), _consumer(idx="dup-1")])
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "duplicate consumer id" in r.stderr


def test_missing_required_top_level_field_fails_closed(tmp_path):
    """A manifest missing a required top-level field (e.g. 'consumers' replaced
    by 'cons') is rejected; no artifact; stderr names the missing field."""
    out = tmp_path / "out"
    m = _base_manifest([_consumer(idx="a-1")])
    m["cons"] = m.pop("consumers")
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "consumers" in r.stderr


@pytest.mark.parametrize("missing", [
    "id", "ownership_edge", "current_path", "replacement",
    "verification", "activation_status", "rollback",
])
def test_missing_per_consumer_field_fails_closed(tmp_path, missing):
    """Per-consumer required fields are validated; missing → fail-closed."""
    out = tmp_path / "out"
    c = _consumer(idx="a-1"); del c[missing]
    m = _base_manifest([c])
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert missing in r.stderr or "missing required field" in r.stderr


def test_invalid_json_manifest_fails_with_no_artifact(tmp_path):
    """Corrupt JSON → fail-closed, no artifact, stderr names JSONDecodeError."""
    out = tmp_path / "out"
    p = tmp_path / "manifest.json"
    p.write_text("{ this is not json")
    r = _run(["--manifest", str(p), "--out", str(out)])
    assert r.returncode != 0
    assert not (out / "CONSUMER-READINESS.json").is_file()
    assert "JSON" in r.stderr


def test_missing_manifest_arg_fails():
    """--manifest missing → usage error, no artifact write attempted."""
    r = _run(["--out", "/tmp/does-not-matter"])
    assert r.returncode != 0
    assert "usage" in r.stderr.lower() or "manifest" in r.stderr.lower()


def test_synthetic_selected_emits_zero_temp_leftovers(tmp_path):
    """Happy path leaves zero dot-prefixed temp artifacts (atomic emit)."""
    out = tmp_path / "out"
    cs = [_consumer(idx=f"a-{i}") for i in range(5)]
    mp = _write_manifest(tmp_path, _base_manifest(cs))
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode == 0, r.stderr
    temps = [p.name for p in out.rglob("*")
             if p.is_file() and p.name.startswith(".")]
    assert not temps, temps
