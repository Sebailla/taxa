"""Strict-TDD contract tests for the PR 1/5 G6 rehearsal scaffold.

PR 1/5 ships a minimal scaffold only: a dry-run-only CLI that reads a JSON
manifest, refuses to run unless `--dry-run`, never executes
`verification.command` or `rollback`, and atomically writes a minimal
rehearsal artifact. Schema validation, path safety, shell parsing,
canonical end-to-end validation, and full G6 closure claims belong to
PRs 2–5 — they are explicitly NOT in this test file.

Three contract tests cover the PR 1/5 surface:

1. `test_refuses_to_run_without_dry_run_flag` — without `--dry-run`,
   the script exits non-zero, stderr mentions `--dry-run`, and no
   artifact is produced (no --execute variant is offered).
2. `test_dry_run_does_not_execute_verification_or_rollback` — sentinel
   `verification.command` / `rollback` strings that would touch a file
   if executed must NOT touch it under `--dry-run`; the artifact is
   still emitted.
3. `test_atomic_write_failure_leaves_no_partial_artifact` — when the
   atomic write cannot complete (parent path is a regular file), the
   script exits non-zero, no artifact is produced, and the original
   file content is preserved byte-for-byte.

The tests are hermetic: subprocess only, no services, no network, no
FastAPI, no port binding, no product-file mutation. The manifest used
for sentinel tests is synthesized in tmp_path; the canonical
`cutover-manifest.json` is NOT consumed by PR 1/5 tests (full canonical
end-to-end validation belongs to PR 4/5).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "rehearse_cutover.py"
REHEARSAL = "cutover-rehearsal.json"


def _run(argv):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        capture_output=True, text=True, check=False,
    )


def _manifest(consumer_id: str = "pr1-1",
              cmd: str = "echo ok",
              rollback: str = "echo rb") -> dict:
    """Minimal well-formed manifest (no schema validation in PR 1/5 —
    we only need a JSON object that argparse-level tests can supply).
    """
    return {
        "$schema_version": "1.0.0",
        "change": "migrate-nextjs-tailwind4",
        "consumers": [{
            "id": consumer_id,
            "verification": {"command": cmd, "expect": "ok"},
            "rollback": rollback,
        }],
    }


def _write_manifest(tmp_path: Path, m: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(m))
    return p


# ── 1. Refusal without --dry-run ────────────────────────────────────────────


def test_refuses_to_run_without_dry_run_flag(tmp_path):
    """The PR 1/5 slice is hermetic and dry-run-only. Without `--dry-run`
    the script MUST exit non-zero, stderr MUST mention `--dry-run`, and
    no `cutover-rehearsal.json` may be produced. No --execute variant
    is offered in this slice."""
    assert SCRIPT.is_file(), (
        f"missing {SCRIPT}; the PR 1/5 G6 scaffold must author "
        f"scripts/rehearse_cutover.py before this test can pass."
    )
    out = tmp_path / "out"
    mp = _write_manifest(tmp_path, _manifest())
    r = _run(["--manifest", str(mp), "--out", str(out)])
    assert r.returncode != 0, (
        f"without --dry-run the script MUST exit non-zero "
        f"(got {r.returncode}); stderr={r.stderr!r}"
    )
    assert "--dry-run" in r.stderr, (
        f"refusal message MUST mention --dry-run; stderr={r.stderr!r}"
    )
    assert not (out / REHEARSAL).is_file(), (
        f"no artifact may be produced when --dry-run is omitted; "
        f"stderr={r.stderr!r}"
    )


# ── 2. Sentinel commands are never executed under --dry-run ────────────────


def test_dry_run_does_not_execute_verification_or_rollback(tmp_path):
    """Dry-run MUST never execute `verification.command` or `rollback`,
    even when the manifest strings would mutate the world if executed.
    Sentinel file paths are chosen so any accidental subprocess exec
    would create them; their continued absence is the assertion. The
    artifact IS emitted (this is the happy path of the scaffold)."""
    assert SCRIPT.is_file(), (
        f"missing {SCRIPT}; the PR 1/5 G6 scaffold must author "
        f"scripts/rehearse_cutover.py before this test can pass."
    )
    out = tmp_path / "out"
    sentinel_v = tmp_path / "sentinel-verify"
    sentinel_r = tmp_path / "sentinel-rollback"
    sentinel_v_touch = f"touch {sentinel_v}"
    sentinel_r_touch = f"touch {sentinel_r}"
    m = _manifest(
        consumer_id="pr1-noexec",
        cmd=sentinel_v_touch,
        rollback=sentinel_r_touch,
    )
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out), "--dry-run"])
    assert r.returncode == 0, (
        f"--dry-run on a well-formed manifest MUST exit 0 "
        f"(got {r.returncode}); stderr={r.stderr!r}"
    )
    assert not sentinel_v.exists(), (
        "verification.command was executed under --dry-run "
        "(sentinel was touched); PR 1/5 contract forbids execution."
    )
    assert not sentinel_r.exists(), (
        "rollback was executed under --dry-run "
        "(sentinel was touched); PR 1/5 contract forbids execution."
    )
    assert (out / REHEARSAL).is_file(), (
        f"rehearsal artifact must be emitted on happy path; "
        f"stderr={r.stderr!r}"
    )
    body = json.loads((out / REHEARSAL).read_text())
    # The minimal artifact must record the no-execute invariants so
    # downstream PRs have a verifiable hook to assert against.
    assert body.get("verification_executed") is False, body
    assert body.get("rollback_executed") is False, body


# ── 3. Atomic-write failure leaves no partial artifact ─────────────────────


def test_atomic_write_failure_leaves_no_partial_artifact(tmp_path):
    """When the atomic write cannot complete (here: --out points at a
    path whose parent slot is occupied by a regular file), the script
    MUST exit non-zero, no `cutover-rehearsal.json` may appear, and the
    pre-existing file at that slot must remain byte-for-byte intact
    (no partial overwrite from a half-written temp file)."""
    assert SCRIPT.is_file(), (
        f"missing {SCRIPT}; the PR 1/5 G6 scaffold must author "
        f"scripts/rehearse_cutover.py before this test can pass."
    )
    # Occupy the would-be --out slot with a regular file. Any mkdir
    # or rename into this slot will fail; the script must propagate
    # the failure without leaking a partial artifact.
    occupied = tmp_path / "occupied"
    occupied.write_text("I am a file, not a directory.")
    mp = _write_manifest(tmp_path, _manifest(consumer_id="pr1-atomic"))
    r = _run(["--manifest", str(mp), "--out", str(occupied), "--dry-run"])
    assert r.returncode != 0, (
        f"atomic-write failure MUST propagate as non-zero exit "
        f"(got {r.returncode}); stderr={r.stderr!r}"
    )
    # The pre-existing regular file MUST be untouched (no rename
    # overwrite, no temp-file leak under it).
    assert occupied.is_file(), r.stderr
    assert occupied.read_text() == "I am a file, not a directory.", (
        "atomic-write failure MUST NOT partially overwrite the "
        "pre-existing file at the --out slot."
    )
    # No rehearsal artifact may have been produced elsewhere under
    # tmp_path (e.g. by some accidental fallback path).
    leftovers = [
        p for p in tmp_path.rglob(REHEARSAL)
        if p.is_file() and p != occupied
    ]
    assert not leftovers, (
        f"no cutover-rehearsal.json may appear after a failed write; "
        f"found leftovers={leftovers}; stderr={r.stderr!r}"
    )
    # No temp leftovers from the atomic write step itself.
    temp_leftovers = [
        p.name for p in tmp_path.rglob(".*")
        if p.is_file() and p.name.startswith(f".{REHEARSAL}")
    ]
    assert not temp_leftovers, (
        f"atomic-write failure MUST clean up its temp file; "
        f"found={temp_leftovers}; stderr={r.stderr!r}"
    )
