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


# ── 11. Slice 4 — canonical-manifest end-to-end regression pins ────────────
#
# Each pin LOCKS IN one specific contract that the rehearsal script holds
# against the canonical normalized manifest. None of these assertions
# existed before slice 4; together they form the regression net that
# keeps the cutover-rehearsal contract from drifting under future refactors.
# All assertions target the on-disk canonical manifest; the script is
# invoked in hermetic --dry-run mode and the resulting artifact is read
# back from <tmp>/cutover-rehearsal.json.
#
# Discipline note (strict TDD):
#   RED   — pin absent: contract unverified (captured in test-history).
#   GREEN — pin added, observed pass under canonical manifest.
#   TRIANGULATE — see negative triangulation in
#                 test_canonical_artifact_manifest_sha256_red_witness: an
#                 intentionally-wrong assertion that MUST fail, proving the
#                 sha256 pin can catch a real drift.

import hashlib as _hashlib
import re as _re


# Canonical artifact key set enforced by PR 4/6 + slice 4. NO `out_sha256`
# is permitted — the artifact is the script's self-description, not a
# re-hash of the output directory.
EXPECTED_KEY_SET = frozenset({
    "consumer_count",
    "consumer_ids",
    "manifest_path",
    "manifest_sha256",
    "mode",
    "out_dir",
    "rollback_executed",
    "validated_at",
    "validation_errors",
    "verification_executed",
})


def _sha256_file(p: Path) -> str:
    """sha256 hex digest of file bytes; mirrors scripts/rehearse_cutover._sha256."""
    return _hashlib.sha256(p.read_bytes()).hexdigest()


def _run_canonical(tmp_path: Path):
    """Invoke the script against the canonical manifest. Return
    (out_dir, body_dict, proc). Shared by every slice-4 pin."""
    assert CANONICAL_MANIFEST.is_file(), f"missing {CANONICAL_MANIFEST}"
    out = tmp_path / "out"
    r = _run(["--manifest", str(CANONICAL_MANIFEST), "--out", str(out), "--dry-run"])
    assert r.returncode == 0, f"canonical run MUST exit 0 (got {r.returncode}); stderr={r.stderr!r}"
    assert (out / REHEARSAL).is_file(), f"rehearsal artifact MUST be emitted; stderr={r.stderr!r}"
    return out, json.loads((out / REHEARSAL).read_text()), r


def _canonical_manifest_dict() -> dict:
    """Load the canonical manifest fresh from disk for side-by-side assertions."""
    return json.loads(CANONICAL_MANIFEST.read_text())


# 11a — manifest SHA pin


def test_canonical_artifact_manifest_sha256_matches_manifest_bytes(tmp_path):
    """GREEN: `manifest_sha256` MUST equal sha256 of the canonical manifest
    bytes. Pins the hash against future manifest edits and guards against
    silent re-pointing of `manifest_path`. Strict-TDD triangulation note:
    the canonical pin below was captured by running an intentionally-wrong
    SHA assertion (`expected = '0' * 64`) and observing the assertion fail
    with `expected(wrong) != got == real` — proof that this pin can catch
    a real drift. The wrong-SHA assertion is NOT retained in the file
    because it would permanently fail CI; its observed RED output is
    recorded in the slice-4 commit message."""
    out, body, _ = _run_canonical(tmp_path)
    expected = _sha256_file(CANONICAL_MANIFEST)
    assert body["manifest_sha256"] == expected, (
        f"manifest_sha256 MUST match sha256(manifest); expected={expected!r}, "
        f"got={body['manifest_sha256']!r}"
    )
    assert len(body["manifest_sha256"]) == 64, body["manifest_sha256"]


# 11b — manifest path pin


def test_canonical_artifact_manifest_path_pinned(tmp_path):
    """GREEN: `manifest_path` MUST echo the resolved canonical manifest path
    verbatim. Pins the path echo so downstream tooling can recover it
    without re-deriving."""
    out, body, _ = _run_canonical(tmp_path)
    expected = str(CANONICAL_MANIFEST.resolve())
    assert body["manifest_path"] == expected, (
        f"manifest_path MUST be {expected!r}; got={body['manifest_path']!r}"
    )


# 11c — ordered 26 unique IDs pin


def test_canonical_artifact_ordered_26_unique_consumer_ids(tmp_path):
    """GREEN: `consumer_ids` MUST list exactly 26 unique IDs, in canonical
    declaration order. Pins the §3.1 consumer roster identity."""
    out, body, _ = _run_canonical(tmp_path)
    canonical = _canonical_manifest_dict()
    expected_ids = [c["id"] for c in canonical["consumers"]
                    if isinstance(c, dict) and isinstance(c.get("id"), str)]
    assert len(expected_ids) == 26, (
        f"canonical manifest MUST list 26 consumers; got {len(expected_ids)}"
    )
    assert body["consumer_ids"] == expected_ids, (
        "consumer_ids MUST equal canonical declaration order; "
        f"diff={list(zip(expected_ids, body['consumer_ids']))}"
    )
    assert len(set(body["consumer_ids"])) == 26, (
        f"all 26 consumer_ids MUST be unique; got={body['consumer_ids']!r}"
    )


# 11d — Tier-1 selected invariants pin


def test_canonical_artifact_tier1_selection_invariants(tmp_path):
    """GREEN: Tier-1 legacy pre-cut selection MUST hold against the canonical
    manifest: every consumer's `activation_status` and `replacement.status`
    is 'selected', `all_replacements_unselected` is False, and
    `legacy_pre_cut_selection_status.active` is True. Pins the G3 Tier-1
    PASS contract — no consumer may silently flip back to unselected."""
    canonical = _canonical_manifest_dict()
    consumers = canonical["consumers"]
    for c in consumers:
        cid = c.get("id")
        assert c.get("activation_status") == "selected", (
            f"Tier-1 invariant: every consumer MUST be activation_status=selected; "
            f"consumer={cid!r}"
        )
        assert c.get("replacement", {}).get("status") == "selected", (
            f"Tier-1 invariant: every consumer MUST be replacement.status=selected; "
            f"consumer={cid!r}"
        )
    inv = canonical["selection_invariants"]
    assert inv.get("all_replacements_unselected") is False, (
        "Tier-1 invariant: all_replacements_unselected MUST be False after Tier-1 selection"
    )
    assert inv.get("legacy_pre_cut_selection_status", {}).get("active") is True, (
        "Tier-1 invariant: legacy_pre_cut_selection_status.active MUST be True"
    )


# 11e — UTC timestamp pin


_ISO8601_UTC_RE = _re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def test_canonical_artifact_validated_at_is_utc_iso8601(tmp_path):
    """GREEN: `validated_at` MUST be an ISO 8601 UTC timestamp ending in
    '+00:00' (or 'Z'). Pins the timestamp format so downstream tooling can
    parse it without locale gymnastics."""
    out, body, _ = _run_canonical(tmp_path)
    ts = body["validated_at"]
    assert isinstance(ts, str), ts
    assert ts.endswith("+00:00") or ts.endswith("Z"), (
        f"validated_at MUST be UTC (suffix +00:00 or Z); got={ts!r}"
    )
    assert _ISO8601_UTC_RE.match(ts), (
        f"validated_at MUST be ISO 8601 calendar+time+offset; got={ts!r}"
    )


# 11f — dry-run mode pin


def test_canonical_artifact_mode_is_dry_run(tmp_path):
    """GREEN: `mode` MUST be exactly 'dry-run'. No --execute variant is
    offered in this slice; PR 5/6 closure may add a separate non-dry-run
    surface but MUST introduce a different mode string."""
    out, body, _ = _run_canonical(tmp_path)
    assert body["mode"] == "dry-run", body
    # Belt-and-braces: nothing else in the script's allowed surface should
    # ever sneak into `mode` without an explicit slice.
    assert body["mode"] in {"dry-run"}, (
        f"mode MUST be one of the canonical rehearsal surface set; got={body['mode']!r}"
    )


# 11g — out_dir + artifact path pin


def test_canonical_artifact_out_dir_and_artifact_path(tmp_path):
    """GREEN: `out_dir` MUST echo the --out directory verbatim, AND the
    artifact MUST be located at <out_dir>/cutover-rehearsal.json
    (atomic-write pin). Cross-check that the on-disk file matches the
    parsed body byte-for-byte so a stale temp file cannot masquerade as
    the canonical artifact."""
    out, body, _ = _run_canonical(tmp_path)
    expected_out = str(out.resolve())
    assert body["out_dir"] == expected_out, (
        f"out_dir MUST be {expected_out!r}; got={body['out_dir']!r}"
    )
    artifact_path = out / REHEARSAL
    assert artifact_path.is_file(), (
        f"cutover-rehearsal.json MUST live at <out>/cutover-rehearsal.json; "
        f"missing={artifact_path}"
    )
    on_disk = json.loads(artifact_path.read_text())
    assert on_disk == body, (
        "artifact on disk MUST equal the parsed body (no temp-file shadowing)"
    )


# 11h — exact key set / no out_sha256 pin


def test_canonical_artifact_exact_key_set_no_out_sha256(tmp_path):
    """GREEN: the artifact MUST carry EXACTLY the canonical key set.
    NO `out_sha256` is permitted (the artifact is the script's
    self-description, not a re-hash of the output directory). Any
    drift — extra keys, missing keys, or an `out_sha256` sneak-in —
    MUST be caught here before it can ride a downstream consumer."""
    out, body, _ = _run_canonical(tmp_path)
    actual_keys = frozenset(body.keys())
    assert actual_keys == EXPECTED_KEY_SET, (
        f"artifact keys MUST be exactly {sorted(EXPECTED_KEY_SET)}; "
        f"got={sorted(actual_keys)}; "
        f"missing={sorted(EXPECTED_KEY_SET - actual_keys)}; "
        f"extra={sorted(actual_keys - EXPECTED_KEY_SET)}"
    )
    assert "out_sha256" not in actual_keys, (
        "artifact MUST NOT carry out_sha256 (forbidden self-hash of out_dir)"
    )


# 11i — count consistency pin


def test_canonical_artifact_count_consistency(tmp_path):
    """GREEN: `consumer_count` MUST equal both len(consumer_ids) and the
    canonical manifest's `len(consumers)` (26). Pins count drift across
    refactors that could re-shape `consumer_ids` while leaving the count
    stale (or vice versa)."""
    out, body, _ = _run_canonical(tmp_path)
    canonical = _canonical_manifest_dict()
    expected_count = len(canonical["consumers"])
    assert body["consumer_count"] == expected_count, (
        f"consumer_count MUST equal len(manifest.consumers); "
        f"got={body['consumer_count']!r}, expected={expected_count!r}"
    )
    assert len(body["consumer_ids"]) == body["consumer_count"], (
        f"len(consumer_ids) MUST equal consumer_count; "
        f"consumer_count={body['consumer_count']}, len(consumer_ids)={len(body['consumer_ids'])}"
    )
    assert body["consumer_count"] == 26, body


# 11j — stable hash across two runs pin


def test_canonical_artifact_manifest_sha256_stable_across_runs(tmp_path):
    """GREEN: `manifest_sha256` MUST be byte-stable across two independent
    rehearsals of the same canonical manifest. The hash MUST equal the
    sha256 of the manifest file at any time the manifest itself is
    unchanged. Pins determinism — a non-stable hash would defeat every
    downstream cache key derived from it."""
    out1 = tmp_path / "out1"
    r1 = _run(["--manifest", str(CANONICAL_MANIFEST), "--out", str(out1), "--dry-run"])
    assert r1.returncode == 0, f"first run MUST exit 0; stderr={r1.stderr!r}"
    sha1 = json.loads((out1 / REHEARSAL).read_text())["manifest_sha256"]
    out2 = tmp_path / "out2"
    r2 = _run(["--manifest", str(CANONICAL_MANIFEST), "--out", str(out2), "--dry-run"])
    assert r2.returncode == 0, f"second run MUST exit 0; stderr={r2.stderr!r}"
    sha2 = json.loads((out2 / REHEARSAL).read_text())["manifest_sha256"]
    expected = _sha256_file(CANONICAL_MANIFEST)
    assert sha1 == sha2 == expected, (
        f"manifest_sha256 MUST be stable across runs and equal to sha256(manifest); "
        f"run1={sha1!r}; run2={sha2!r}; expected={expected!r}"
    )


# ── 12. Slice 5 — canonical-artifact bounded-evidence pins (PR 5/6) ──────────
#
# Bounded-evidence contract: the canonical `cutover-rehearsal.json` is the
# script's self-description for the canonical dry-run ONLY. It carries
# exactly 10 keys (frozen by slice-4 `EXPECTED_KEY_SET`) and MUST NOT carry
# any Tier-2 / cutover-completion markers — it cannot be misread as Tier-2
# / cutover closure. This is the §3.3.6 `Disposition (2026-09-13 — G6
# slice 5 canonical dry-run artifact, bounded closure evidence)` contract.

FORBIDDEN_CLOSURE_MARKERS = frozenset({
    "tier_2_passed", "g3_tier2_passed", "g4_passed", "g5_passed",
    "cutover_complete", "rollback_rehearsed", "atomic_cut_executed",
    "fastapi_activated", "web_dir_repointed",
})


def test_canonical_artifact_bounded_evidence_no_tier2_or_cutover_markers(tmp_path):
    """GREEN: canonical artifact MUST NOT carry any Tier-2 / G3 / G4 / G5 /
    cutover-completion closure marker. The slice-4 `EXPECTED_KEY_SET` pin
    alone cannot catch a refactor that swaps `verification_executed: false`
    for `g3_tier2_passed: false` (both keys still satisfy the exact-key-set
    pin). This test pins the SEMANTIC intent: no closure-completion key
    may appear. Run on `feat/g6-rehearsal-schema-validation-2` at commit
    `e1fc5a4` against the canonical normalized manifest."""
    out, body, _ = _run_canonical(tmp_path)
    actual_keys = frozenset(body.keys())
    leaked_markers = actual_keys & FORBIDDEN_CLOSURE_MARKERS
    assert not leaked_markers, (
        f"canonical artifact MUST NOT carry any Tier-2 / cutover-completion "
        f"marker; leaked={sorted(leaked_markers)}; actual={sorted(actual_keys)}"
    )


def test_canonical_artifact_bounded_evidence_dry_run_only_no_execute_marker(tmp_path):
    """GREEN: canonical artifact's dry-run-only contract MUST hold jointly:
    `mode == "dry-run"` AND `verification_executed is False` AND
    `rollback_executed is False`. No `--execute` variant is offered in the
    PR 1/6–PR 5/6 G6 surface; the artifact cannot be misread as a real
    rehearsal that touched the world."""
    out, body, _ = _run_canonical(tmp_path)
    assert body.get("mode") == "dry-run", (
        f"mode MUST be 'dry-run'; got={body.get('mode')!r}"
    )
    assert body.get("verification_executed") is False, (
        f"verification_executed MUST be False; got={body.get('verification_executed')!r}"
    )
    assert body.get("rollback_executed") is False, (
        f"rollback_executed MUST be False; got={body.get('rollback_executed')!r}"
    )
