"""
Build profile contract tests for the Next.js ↔ FastAPI migration.

PR 1 (evidence-only slice) introduces the *tooling* and the *schema*
for the build profile JSON; the actual `next build` output lands in
PR 3. These tests pin the schema so design can close §1 of
`openspec/changes/migrate-nextjs-tailwind4/scope-decisions.md` once
PR 3 produces a real profile and design invokes `scripts/emit_build_profile.mjs`
against it.

What the contract requires (tasks.md 1.1 + design.md §Architecture
Decisions, "Build profile" row):

    web/dist/build-profile.json
        {
          "chunks": [...],          # list of chunk descriptors
          "total_bytes": int,       # sum of all chunk bytes
          "per_route_bytes": { ... } # map<route, int>
        }

The test exercises `scripts/emit_build_profile.mjs` against a
**fixture** build directory (synthetic chunks), and asserts the
emitted JSON satisfies the schema. A separate negative-path test
asserts the script exits non-zero when given an empty / missing
build directory — so PR 3's CI cannot accidentally accept a silent
empty profile.

Reference:
    openspec/changes/migrate-nextjs-tailwind4/tasks.md  §Phase 1  (1.1)
    openspec/changes/migrate-nextjs-tailwind4/design.md §Architecture Decisions
    openspec/changes/migrate-nextjs-tailwind4/specs/frontend-bootstrap/spec.md
                                              Requirement: Build profile captured
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "emit_build_profile.mjs"
OUTPUT_PATH = REPO_ROOT / "web" / "dist" / "build-profile.json"


# ---------------------------------------------------------------------------
# Fixture: a synthetic build directory shaped like Next.js's `.next/static`
# or `out/_next/static` output (whichever the chosen Approach in §1 lands on).
# PR 1 ships the schema; PR 3 ships the real build. Tests below work against
# the fixture, not a real build, so they're deterministic on a clean checkout.
# ---------------------------------------------------------------------------
@pytest.fixture()
def fixture_build_dir(tmp_path: Path) -> Path:
    """Create a synthetic next-build-like directory with deterministic chunks.

    Layout mimics Next.js's `out/_next/static/chunks/...` tree:
        build/
            index.html            # 1024 bytes
            _next/
                static/
                    chunks/
                        app-abc.js       # 4096 bytes
                        app-def.js       # 2048 bytes
                        framework-ghi.js # 8192 bytes
                    css/
                        app-abc.css      # 1024 bytes
    """
    build = tmp_path / "build"
    chunks = build / "_next" / "static" / "chunks"
    chunks.mkdir(parents=True)
    (chunks / "app-abc.js").write_bytes(b"a" * 4096)
    (chunks / "app-def.js").write_bytes(b"b" * 2048)
    chunks_css = build / "_next" / "static" / "css"
    chunks_css.mkdir(parents=True)
    (chunks_css / "app-abc.css").write_bytes(b"c" * 1024)
    framework = chunks / "framework-ghi.js"
    framework.write_bytes(b"d" * 8192)
    (build / "index.html").write_bytes(b"<html>" + b"e" * 1014)
    return build


def _run_script(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run scripts/emit_build_profile.mjs with the given args, capturing output.

    Uses the system node so the test fails clearly if node is missing.
    """
    return subprocess.run(
        ["node", str(SCRIPT), *args],
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# RED: these tests fail before scripts/emit_build_profile.mjs exists.
# GREEN: implement the script to emit JSON satisfying the schema.
# ---------------------------------------------------------------------------
def test_script_exists():
    """The emit_build_profile.mjs script must be created by task 1.1."""
    assert SCRIPT.exists(), (
        f"missing emit script: {SCRIPT}. Task 1.1 requires this script to exist."
    )


def test_emit_writes_profile_with_required_keys(tmp_path: Path, fixture_build_dir: Path):
    """`emit_build_profile.mjs <build-dir> <output-path>` writes JSON with
    the required top-level keys: chunks, total_bytes, per_route_bytes.
    """
    output = tmp_path / "build-profile.json"
    result = _run_script(str(fixture_build_dir), str(output))
    assert result.returncode == 0, (
        f"emit_build_profile.mjs exited {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert output.exists(), (
        f"output file not created at {output}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )

    profile = json.loads(output.read_text())

    # Schema: must contain the three contract keys (tasks.md 1.1 + design.md).
    assert "chunks" in profile, "profile missing required key 'chunks'"
    assert "total_bytes" in profile, "profile missing required key 'total_bytes'"
    assert "per_route_bytes" in profile, (
        "profile missing required key 'per_route_bytes'"
    )

    # The script may add extra metadata keys (build_dir, timestamp, ...),
    # but the three contract keys MUST be present and well-typed.
    assert isinstance(profile["chunks"], list), "'chunks' must be a list"
    assert isinstance(profile["total_bytes"], int), (
        "'total_bytes' must be an int"
    )
    assert isinstance(profile["per_route_bytes"], dict), (
        "'per_route_bytes' must be an object mapping route -> bytes"
    )


def test_emit_chunks_descriptors_are_well_typed(
    tmp_path: Path, fixture_build_dir: Path
):
    """Each chunk descriptor must carry a path and byte count.

    The exact descriptor shape is left to the script author (path, size,
    optional route / content-type). Tests assert only the minimum required
    fields so the script can evolve without breaking this contract.
    """
    output = tmp_path / "build-profile.json"
    result = _run_script(str(fixture_build_dir), str(output))
    assert result.returncode == 0, result.stderr

    profile = json.loads(output.read_text())
    chunks = profile["chunks"]
    assert chunks, "chunks list must be non-empty for a fixture with 4 files"

    for chunk in chunks:
        assert "path" in chunk, f"chunk descriptor missing 'path': {chunk}"
        assert isinstance(chunk["path"], str), f"chunk.path must be a string"
        assert "bytes" in chunk, f"chunk descriptor missing 'bytes': {chunk}"
        assert isinstance(chunk["bytes"], int) and chunk["bytes"] >= 0, (
            f"chunk.bytes must be a non-negative int: {chunk}"
        )


def test_emit_total_bytes_matches_sum_of_chunks(
    tmp_path: Path, fixture_build_dir: Path
):
    """total_bytes must equal the sum of all chunk bytes.

    Cross-check between the two contract fields — catches a script that
    computes one but not the other.
    """
    output = tmp_path / "build-profile.json"
    result = _run_script(str(fixture_build_dir), str(output))
    assert result.returncode == 0, result.stderr

    profile = json.loads(output.read_text())
    chunk_sum = sum(c["bytes"] for c in profile["chunks"])
    assert profile["total_bytes"] == chunk_sum, (
        f"total_bytes={profile['total_bytes']} != sum(chunks.bytes)={chunk_sum}"
    )


def test_emit_per_route_bytes_is_a_map_of_route_to_int(
    tmp_path: Path, fixture_build_dir: Path
):
    """per_route_bytes is a JSON object mapping each route name to bytes.

    A valid build has at least one route (the root '/'). Values must be ints.
    """
    output = tmp_path / "build-profile.json"
    result = _run_script(str(fixture_build_dir), str(output))
    assert result.returncode == 0, result.stderr

    profile = json.loads(output.read_text())
    routes = profile["per_route_bytes"]
    assert routes, "per_route_bytes must be non-empty"
    for route, size in routes.items():
        assert isinstance(route, str), f"route key must be a string: {route!r}"
        assert isinstance(size, int) and size >= 0, (
            f"route {route!r} has non-int/negative bytes: {size}"
        )


def test_emit_exits_nonzero_on_missing_build_dir(tmp_path: Path):
    """Negative path: an empty / missing build directory must abort with a
    non-zero exit and a clear stderr message.

    PR 3's CI must not silently accept an empty profile from a failed build.
    """
    output = tmp_path / "build-profile.json"
    missing = tmp_path / "no-such-build"
    result = _run_script(str(missing), str(output))
    assert result.returncode != 0, (
        f"script should fail on missing build dir; got exit={result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # Helpful stderr — reviewers should see WHY the script failed.
    assert result.stderr.strip(), "script must write a diagnostic to stderr"


def test_emit_help_lists_arguments(tmp_path: Path):
    """`emit_build_profile.mjs --help` (or no args) prints usage and exits 0.

    Pinned behavior so reviewers can discover the CLI surface.
    """
    result = _run_script("--help")
    assert result.returncode == 0, (
        f"--help should exit 0; got {result.returncode}.\n"
        f"stderr: {result.stderr}"
    )
    assert "usage" in (result.stdout + result.stderr).lower(), (
        "--help output should describe usage"
    )


def test_emit_per_route_bytes_groups_by_route(
    tmp_path: Path
):
    """Triangulation: per_route_bytes aggregates bytes by route, not by file.

    A multi-route fixture (e.g. `/` and `/about`) must surface as separate
    keys in `per_route_bytes`, with byte sums equal to the sum of files
    under each route's directory tree.

    This catches a script that silently rolls all routes into `/`.
    """
    build = tmp_path / "multi-route-build"
    build.mkdir()
    # Route `/`: index.html (50 bytes), chunk foo.js (100 bytes)
    (build / "index.html").write_bytes(b"x" * 50)
    foo = build / "_next" / "static" / "chunks"
    foo.mkdir(parents=True)
    (foo / "foo.js").write_bytes(b"y" * 100)
    # Route `/about`: about/index.html (60 bytes), chunk about.js (200 bytes)
    about = build / "about"
    about.mkdir()
    (about / "index.html").write_bytes(b"z" * 60)
    about_chunks = build / "_next" / "static" / "chunks" / "about"
    about_chunks.mkdir(parents=True)
    (about_chunks / "about.js").write_bytes(b"w" * 200)

    output = tmp_path / "profile.json"
    result = _run_script(str(build), str(output))
    assert result.returncode == 0, result.stderr

    profile = json.loads(output.read_text())

    # Both routes must appear in per_route_bytes with non-zero sizes.
    assert "/" in profile["per_route_bytes"], (
        f"root route missing: {profile['per_route_bytes']}"
    )
    assert "/about" in profile["per_route_bytes"], (
        f"/about route missing: {profile['per_route_bytes']}"
    )

    # Total = 50 + 100 + 60 + 200 = 410
    assert profile["total_bytes"] == 410, (
        f"total_bytes={profile['total_bytes']} expected 410"
    )

    # Sanity: at least 4 chunks enumerated
    assert len(profile["chunks"]) >= 4, (
        f"chunks list too short: {profile['chunks']}"
    )


def test_well_known_output_path_default(tmp_path: Path, fixture_build_dir: Path):
    """When called without an explicit output path, the script writes to the
    canonical path `web/dist/build-profile.json` (the path cited in
    tasks.md 1.1 and design.md §Architecture Decisions).

    Pinned so `make api` (PR 3) can rely on the canonical location.
    """
    # Override the canonical path via an env var so we don't pollute the
    # repo's web/dist/ on test runs. The contract: when WEB_DIST_DIR is set,
    # the script writes there; when unset, it writes to web/dist/.
    env_dir = tmp_path / "web_dist"
    env_dir.mkdir()
    result = subprocess.run(
        ["node", str(SCRIPT), str(fixture_build_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={
            **__import__("os").environ,
            "BUILD_PROFILE_OUT_DIR": str(env_dir),
        },
    )
    assert result.returncode == 0, result.stderr
    canonical = env_dir / "build-profile.json"
    assert canonical.exists(), (
        f"default-output location not honored: expected {canonical}.\n"
        f"stderr: {result.stderr}"
    )