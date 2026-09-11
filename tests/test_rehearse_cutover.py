"""Strict-TDD contract tests for the G6 cutover-rehearsal scaffold.

PR 1/6 ships the minimal scaffold only: a dry-run-only CLI that reads a
JSON manifest, refuses to run unless `--dry-run`, never executes
`verification.command` or `rollback`, and atomically writes a minimal
rehearsal artifact.

PR 4/6 extends the scaffold with fail-closed manifest-schema validation
that delegates path / shell checks to the PR 2/6 helpers
`validate_repo_relative_path` + `parse_shell_text` (no duplicated
logic). Required top-level fields + `consumers` list shape, all seven
required consumer fields (`id`, `ownership_edge`, `current_path`,
`replacement`, `verification`, `activation_status`, `rollback`), unique
consumer IDs, strict `current_path` / `replacement.path`, and parseable
`verification.command` / `rollback` are all validated. On full success
the artifact carries `consumer_ids` (one per consumer, in declaration
order) and `validation_errors: []`; on any validation failure the
script exits non-zero and emits no `cutover-rehearsal.json` (fail
closed). The canonical normalized manifest
(`openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`)
MUST exit 0 and emit a 26-consumer artifact on PR 4/6. Full G6
closure claims belong to PR 5/6.

The tests are hermetic: subprocess only, no services, no network, no
FastAPI, no port binding, no product-file mutation. The canonical
manifest is consumed only by the PR 4/6 canonical happy-path test; the
synthesized in-tmp_path manifest is used by every other contract test.
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
CANONICAL_MANIFEST = (
    REPO_ROOT / "openspec" / "changes" / "migrate-nextjs-tailwind4"
    / "cutover-manifest.json"
)

assert SCRIPT.is_file(), f"missing {SCRIPT}; the PR 1/6 G6 scaffold must author scripts/rehearse_cutover.py before these tests can run"


def _run(argv):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        capture_output=True, text=True, check=False,
    )


def _manifest(consumer_id: str = "pr4-1",
              cmd: str = "echo ok",
              rollback: str = "echo rb") -> dict:
    """Schema-valid manifest (PR 4/6 contract): carries all seven required
    consumer fields plus valid path + shell text for the canonical PR 2/6
    helpers. Broken cases mutate a copy."""
    return {
        "$schema_version": "1.0.0",
        "change": "migrate-nextjs-tailwind4",
        "consumers": [{
            "id": consumer_id,
            "ownership_edge": "fastapi_web_mount",
            "current_path": "src/foo/bar.ts",
            "replacement": {"status": "selected", "path": "src/foo/bar.ts"},
            "verification": {"command": cmd, "expect": "ok"},
            "activation_status": "selected",
            "rollback": rollback,
        }],
    }


def _write_manifest(tmp_path: Path, m: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(m))
    return p


def _run_manifest(tmp_path: Path, m: dict):
    """Write manifest, run the CLI under `--dry-run`, return (out_dir, proc).
    Shared by every PR 4/6 contract test to remove repeated boilerplate."""
    out = tmp_path / "out"
    mp = _write_manifest(tmp_path, m)
    return out, _run(["--manifest", str(mp), "--out", str(out), "--dry-run"])


def _assert_fail_closed(out, r, needle: str):
    """Assert the canonical fail-closed contract: non-zero exit, stderr names
    `needle`, and no `cutover-rehearsal.json` is emitted. Every PR 4/6 schema
    test shares this triple — pinning it once keeps the tests concise."""
    assert r.returncode != 0, f"MUST fail closed (got exit {r.returncode}); stderr={r.stderr!r}"
    assert needle in r.stderr, f"stderr MUST mention {needle!r}; stderr={r.stderr!r}"
    assert not (out / REHEARSAL).is_file(), f"no artifact may be emitted on schema failure; stderr={r.stderr!r}"


# ── 1. Refusal without --dry-run ────────────────────────────────────────────


def test_refuses_to_run_without_dry_run_flag(tmp_path):
    """The PR 1/6 slice is hermetic and dry-run-only. Without `--dry-run`
    the script MUST exit non-zero, stderr MUST mention `--dry-run`, and
    no `cutover-rehearsal.json` may be produced. No --execute variant
    is offered in this slice."""
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


# ── 4. Schema validation: top-level required fields (PR 4/6) ─────────────


@pytest.mark.parametrize(
    "missing_field",
    ["$schema_version", "change", "consumers"],
)
def test_schema_fails_closed_on_missing_top_level_field(tmp_path, missing_field):
    """Missing top-level required fields MUST fail closed."""
    m = _manifest()
    m.pop(missing_field, None)
    out, r = _run_manifest(tmp_path, m)
    _assert_fail_closed(out, r, missing_field)


# ── 5. Schema validation: `consumers` must be a list (PR 4/6) ────────────


@pytest.mark.parametrize(
    "bad_consumers",
    [None, "consumers-as-string", 42, {"not": "a list"}],
)
def test_schema_fails_closed_when_consumers_not_a_list(tmp_path, bad_consumers):
    """Non-list `consumers` MUST fail closed (PR 4/6 fail-closed promotion)."""
    m = _manifest()
    m["consumers"] = bad_consumers
    out, r = _run_manifest(tmp_path, m)
    _assert_fail_closed(out, r, "consumers")


# ── 6. Schema validation: per-consumer required fields (PR 4/6) ──────────


@pytest.mark.parametrize(
    "missing_field",
    [
        "id", "ownership_edge", "current_path", "replacement",
        "verification", "activation_status", "rollback",
    ],
)
def test_schema_fails_closed_on_missing_consumer_field(tmp_path, missing_field):
    """Each consumer MUST carry all seven required fields."""
    m = _manifest()
    m["consumers"][0].pop(missing_field, None)
    out, r = _run_manifest(tmp_path, m)
    _assert_fail_closed(out, r, missing_field)


# ── 7. Schema validation: duplicate consumer IDs (PR 4/6) ───────────────


def test_schema_fails_closed_on_duplicate_consumer_id(tmp_path):
    """Duplicate consumer ids MUST fail closed (stable-identity contract)."""
    out = tmp_path / "out"
    m = _manifest(consumer_id="pr4-dup")
    m["consumers"].append({
        "id": "pr4-dup", "ownership_edge": "fastapi_web_mount",
        "current_path": "src/other/file.ts",
        "replacement": {"status": "selected", "path": "src/other/file.ts"},
        "verification": {"command": "echo ok", "expect": "ok"},
        "activation_status": "selected", "rollback": "echo rb",
    })
    mp = _write_manifest(tmp_path, m)
    r = _run(["--manifest", str(mp), "--out", str(out), "--dry-run"])
    _assert_fail_closed(out, r, "duplicate")
    assert "pr4-dup" in r.stderr, f"stderr MUST name the duplicate id value; stderr={r.stderr!r}"


# ── 8. Schema validation: invalid current_path / replacement.path (PR 4/6) ──


@pytest.mark.parametrize(
    "field,bad_path",
    [
        ("current_path", "../etc/passwd"),
        ("current_path", "/abs/path.ts"),
        ("current_path", "src/foo$bar.ts"),
        ("replacement", "src/foo$bar.ts"),
        ("replacement", "/abs/path.ts"),
        ("replacement", "a/b/../c"),
    ],
)
def test_schema_fails_closed_on_invalid_path(tmp_path, field, bad_path):
    """`current_path` AND `replacement.path` MUST pass `validate_repo_relative_path` (PR 2/6)."""
    m = _manifest()
    if field == "current_path":
        m["consumers"][0]["current_path"] = bad_path
    else:
        m["consumers"][0]["replacement"]["path"] = bad_path
    out, r = _run_manifest(tmp_path, m)
    needle = "replacement.path" if field == "replacement" else "current_path"
    _assert_fail_closed(out, r, needle)


# ── 9. Schema validation: malformed shell text (PR 4/6) ─────────────────


@pytest.mark.parametrize(
    "shell_field,bad_text",
    [
        ("verification.command", "echo 'unclosed"),
        ("verification.command", "echo a\x00b"),
        ("verification.command", "   "),
        ("rollback", "echo 'unclosed"),
        ("rollback", "echo a\x00b"),
        ("rollback", "   "),
    ],
)
def test_schema_fails_closed_on_malformed_shell_text(tmp_path, shell_field, bad_text):
    """`verification.command` AND `rollback` MUST pass `parse_shell_text` (PR 2/6)."""
    m = _manifest()
    if "." in shell_field:
        container, key = shell_field.split(".", 1)
        m["consumers"][0][container][key] = bad_text
    else:
        m["consumers"][0][shell_field] = bad_text
    out, r = _run_manifest(tmp_path, m)
    _assert_fail_closed(out, r, shell_field.split(".")[-1])


# ── 10. Canonical happy-path: real normalized manifest (PR 4/6) ─────────


def test_canonical_happy_path_emits_artifact_for_all_26_consumers(tmp_path):
    """Canonical happy-path pin: exit 0, artifact emitted, 26 consumer_ids + empty validation_errors."""
    assert CANONICAL_MANIFEST.is_file(), f"missing {CANONICAL_MANIFEST}"
    out = tmp_path / "out"
    r = _run(["--manifest", str(CANONICAL_MANIFEST), "--out", str(out), "--dry-run"])
    assert r.returncode == 0, f"canonical happy-path MUST exit 0 (got {r.returncode}); stderr={r.stderr!r}"
    assert (out / REHEARSAL).is_file(), f"rehearsal artifact MUST be emitted; stderr={r.stderr!r}"
    body = json.loads((out / REHEARSAL).read_text())
    ids = body.get("consumer_ids")
    assert isinstance(ids, list) and len(ids) == 26, f"MUST carry 26 consumer_ids; got type={type(ids).__name__}"
    assert len(set(ids)) == 26, f"all 26 consumer_ids MUST be unique; got={ids!r}"
    assert body.get("validation_errors") == [], f"MUST carry empty validation_errors; got={body.get('validation_errors')!r}"
    assert body.get("consumer_count") == 26, body
    # PR 1/6 dry-run invariants remain binding under PR 4/6.
    assert body.get("verification_executed") is False, body
    assert body.get("rollback_executed") is False, body
