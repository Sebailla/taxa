"""
Hydration timing tests for the legacy `taxa` frontend.

PR 1b.3a pinned the positional `validate <artifact>` contract and the
6-key hydration schema. PR 1b.3c (this slice) extends
`scripts/measure_hydration.py` with a hermetic capture mode and pins
that surface here. The original 11 tests stay green unchanged.

Reference:
  openspec/changes/migrate-nextjs-tailwind4/design.md §3.3.5 (G5)
  openspec/changes/migrate-nextjs-tailwind4/design.md §Open Questions
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "measure_hydration.py"


@pytest.fixture()
def hydration_artifact(tmp_path: Path) -> Path:
    """Synthetic hydration JSON artifact (PR 1b.3a fixture shape)."""
    fixture = tmp_path / "hydration.json"
    fixture.write_text(
        json.dumps(
            {
                "captured_at": "2026-08-28T00:00:00Z",
                "build": "legacy",
                "route": "/",
                "server_shell": {
                    "first_paint_ms": 80.0,
                    "dom_content_loaded_ms": 100.0,
                },
                "client_render": {
                    "tree_first_paint_ms": 220.0,
                    "tree_first_interactive_ms": 350.0,
                },
                "console_warnings": [],
            },
            indent=2,
        )
    )
    return fixture


@pytest.fixture()
def hydration_artifact_with_warnings(tmp_path: Path) -> Path:
    """Synthetic artifact carrying a hydration-style console warning."""
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


@pytest.fixture()
def minimal_candidate_root(tmp_path: Path) -> Path:
    """Self-contained candidate web root for the hermetic capture.

    Lives in `tmp_path` so tests do not touch the real
    `tools/g3-legacy-fixture/web/` or the production `web/`.
    """
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "index.html").write_text(
        "<!doctype html>\n"
        "<html><head>\n"
        '  <link rel="stylesheet" href="dist/tailwind.css">\n'
        "</head><body>\n"
        '  <div id="tree-view"></div>\n'
        '  <script type="module" src="app.js"></script>\n'
        "</body></html>\n"
    )
    (root / "dist").mkdir()
    (root / "dist" / "tailwind.css").write_text(
        "/* synthetic css for hermetic g5 baseline capture */\n"
        "body { color: black; }\n"
    )
    (root / "app.js").write_text(
        "// synthetic app.js for hermetic g5 baseline capture\n"
        "const el = document.getElementById('tree-view');\n"
        "if (el) el.appendChild(document.createTextNode('hi'));\n"
    )
    return root


def _run_script(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# PR 1b.3a contract (validate mode) — every test must stay green
# ---------------------------------------------------------------------------
def test_measure_hydration_script_exists():
    assert SCRIPT.exists(), f"missing hydration measurement script: {SCRIPT}"


def test_measure_hydration_exits_zero_on_valid_artifact(hydration_artifact: Path):
    """Script exits 0 on a valid hydration JSON."""
    result = _run_script(str(hydration_artifact))
    assert result.returncode == 0, (
        f"exited {result.returncode}.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )


def test_measure_hydration_exits_one_on_no_arguments():
    """No-argument invocation must exit 1 (PR 1b.3a contract).

    `argparse.error()` defaults to exit 2; the script overrides
    that to preserve the original "no-arg → exit 1" behaviour.
    """
    result = _run_script()
    assert result.returncode == 1, (
        f"no-argument must exit 1; got {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "usage" in result.stderr.lower()


def test_measure_hydration_exits_nonzero_on_missing_file(tmp_path: Path):
    """Missing artifact must abort non-zero with a clear stderr."""
    result = _run_script(str(tmp_path / "no-such.json"))
    assert result.returncode != 0
    assert result.stderr.strip()


def test_measure_hydration_reports_delta(hydration_artifact: Path):
    """Script reports the 140 ms client-vs-server delta (220 − 80)."""
    result = _run_script(str(hydration_artifact))
    assert result.returncode == 0, result.stderr
    output = result.stdout + result.stderr
    assert "140" in output, output


def test_measure_hydration_flags_console_warnings(
    hydration_artifact_with_warnings: Path,
):
    """Script surfaces `hydration`-style console warnings in its output."""
    result = _run_script(str(hydration_artifact_with_warnings))
    output = (result.stdout + result.stderr).lower()
    assert "warning" in output or "hydration" in output


def test_hydration_artifact_schema_keys_present(hydration_artifact: Path):
    """Artifact carries the 6-key schema design cites in §1 evidence."""
    doc = json.loads(hydration_artifact.read_text())
    for key in (
        "captured_at",
        "build",
        "route",
        "server_shell",
        "client_render",
        "console_warnings",
    ):
        assert key in doc, f"missing key {key!r}"


def test_hydration_artifact_server_shell_keys(hydration_artifact: Path):
    """server_shell records first_paint_ms + dom_content_loaded_ms."""
    doc = json.loads(hydration_artifact.read_text())
    shell = doc["server_shell"]
    assert "first_paint_ms" in shell
    assert "dom_content_loaded_ms" in shell
    for key, val in shell.items():
        assert isinstance(val, (int, float)) and val >= 0, (
            f"server_shell.{key} must be non-negative numeric; got {val!r}"
        )


def test_hydration_artifact_client_render_keys(hydration_artifact: Path):
    """client_render records tree_first_paint + tree_first_interactive."""
    doc = json.loads(hydration_artifact.read_text())
    render = doc["client_render"]
    assert "tree_first_paint_ms" in render
    assert "tree_first_interactive_ms" in render
    for key, val in render.items():
        assert isinstance(val, (int, float)) and val >= 0


def test_hydration_artifact_console_warnings_is_a_list(
    hydration_artifact: Path,
):
    """console_warnings is a list of strings (possibly empty)."""
    doc = json.loads(hydration_artifact.read_text())
    warnings = doc["console_warnings"]
    assert isinstance(warnings, list)
    for w in warnings:
        assert isinstance(w, str)


def test_measure_hydration_exits_nonzero_on_malformed_json(tmp_path: Path):
    """Malformed JSON must abort non-zero with a JSON-parsing stderr hint."""
    bad = tmp_path / "bad.json"
    bad.write_text("{ not: valid json ")
    result = _run_script(str(bad))
    assert result.returncode != 0
    assert "parse" in result.stderr.lower() or "json" in result.stderr.lower()


def test_measure_hydration_exits_nonzero_on_schema_violation(tmp_path: Path):
    """Schema violation must abort non-zero with a clear stderr hint."""
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(
        json.dumps(
            {
                "captured_at": "2026-08-28T00:00:00Z",
                "build": "legacy",
            }
        )
    )
    result = _run_script(str(incomplete))
    assert result.returncode != 0
    stderr = result.stderr.lower()
    assert "schema" in stderr or "missing" in stderr


# ---------------------------------------------------------------------------
# G5 closure-path step 1 — hermetic capture mode (PR 1b.3c additions)
# ---------------------------------------------------------------------------
def test_measure_hydration_capture_writes_baseline_artifact(
    tmp_path: Path,
    minimal_candidate_root: Path,
) -> None:
    """Capture writes a valid baseline + provenance at the requested path."""
    out = tmp_path / "baselines" / "legacy-web-2026-08-26.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--baseline",
            str(out),
            "--candidate",
            str(minimal_candidate_root),
            "--iterations",
            "10",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists(), "capture must write the baseline artifact"
    doc = json.loads(out.read_text())
    for key in (
        "captured_at",
        "build",
        "route",
        "server_shell",
        "client_render",
        "console_warnings",
        "provenance",
    ):
        assert key in doc, f"missing key {key!r}"
    prov = doc["provenance"]
    for prov_key in ("schema", "command_line", "iterations", "captured_at"):
        assert prov_key in prov, f"provenance missing {prov_key!r}"
    assert prov["iterations"] == 10
    assert prov["schema"] == "taxa.g5-hydration-baseline/1"
    assert "--baseline" in prov["command_line"]


def test_measure_hydration_capture_is_byte_reproducible(
    tmp_path: Path,
    minimal_candidate_root: Path,
) -> None:
    """Two captures against the same root → byte-identical modulo wall-clock.

    The closure-path (1) acceptance test: same input → same artifact
    bytes (except `captured_at` + the user-supplied `--baseline`
    argument recorded in `provenance.command_line`).
    """
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--candidate",
        str(minimal_candidate_root),
        "--iterations",
        "10",
    ]
    subprocess.run(
        [*cmd, "--baseline", str(first)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    subprocess.run(
        [*cmd, "--baseline", str(second)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    a = json.loads(first.read_text())
    b = json.loads(second.read_text())
    a.pop("captured_at", None)
    b.pop("captured_at", None)
    if isinstance(a.get("provenance"), dict):
        a["provenance"].pop("captured_at", None)
        a["provenance"].pop("command_line", None)
    if isinstance(b.get("provenance"), dict):
        b["provenance"].pop("captured_at", None)
        b["provenance"].pop("command_line", None)
    assert a == b, "two captures must be byte-identical (excluding wall-clock)"


def test_measure_hydration_capture_fails_on_missing_candidate(
    tmp_path: Path,
) -> None:
    """--candidate pointing at a non-existent root must fail (fail-closed)."""
    out = tmp_path / "out.json"
    missing = tmp_path / "does-not-exist"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--baseline",
            str(out),
            "--candidate",
            str(missing),
            "--iterations",
            "10",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert not out.exists(), "must NOT write output on missing candidate"


def test_measure_hydration_capture_validates_written_artifact(
    tmp_path: Path,
    minimal_candidate_root: Path,
) -> None:
    """After capture, the positional validator must accept the written file."""
    out = tmp_path / "baseline.json"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--baseline",
            str(out),
            "--candidate",
            str(minimal_candidate_root),
            "--iterations",
            "10",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    validate = subprocess.run(
        [sys.executable, str(SCRIPT), str(out)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate.returncode == 0, (
        "validator must accept the freshly written baseline; got exit="
        + str(validate.returncode)
    )


def test_measure_hydration_capture_requires_candidate(
    tmp_path: Path,
) -> None:
    """--baseline without --candidate must fail with exit 1 (PR 1b.3a contract).

    Argparse defaults to exit 2 for missing required args; the script
    overrides that to preserve the legacy "usage error → exit 1" map.
    """
    out = tmp_path / "out.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--baseline",
            str(out),
            "--iterations",
            "10",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert not out.exists(), "must NOT write output without --candidate"

# ---------------------------------------------------------------------------
# G5 precondition contract (design.md §3.3.5) — slice 3 reconstruction
# ---------------------------------------------------------------------------
# Slice 1 (PR #216) added the hermetic --baseline --candidate --iterations
# capture mode. Slice 3 layers the FAIL-CLOSED precondition contract on top:
# --iterations must equal exactly 10; --baseline must be a writable path
# (non-existent, or an existing regular file — but NOT an existing
# directory) with an existing parent directory; --candidate must be an
# existing directory; the three flags must appear together. On any
# precondition failure the script exits non-zero, emits no capture
# artifact, and never claims G5 pass. Capture, raw evidence schema, and
# delta calculation land in the closure-path steps 2–4 (PR3d+).
#
# This section adapts the precondition contract tests from source commit
# `7dcfea4` ("feat(g5): enforce hydration capture preconditions (#132)")
# onto the current develop — which already carries the slice-1 capture
# pipeline. The legacy positional `validate <artifact>` contract is
# preserved verbatim by `test_g5_cli_legacy_positional_path_preserved`.
G5_EXPECTED_ITERATIONS = 10
EXIT_G5_PRECONDITION = 10


@pytest.fixture()
def g5_baseline_output(tmp_path: Path) -> Path:
    """Where the G5 capture would write its baseline (does NOT pre-exist).

    Tests assert the path remains untouched after a precondition failure.
    """
    return tmp_path / "should-not-exist-by-default.json"


@pytest.fixture()
def g5_baseline_existing_file(tmp_path: Path) -> Path:
    """An existing JSON file that the capture is allowed to overwrite.

    Used by precondition-pass tests where the slice is allowed to write
    a real capture artifact on top of this stub.
    """
    p = tmp_path / "pre-existing-baseline.json"
    p.write_text("{}\n", encoding="utf-8")
    return p


@pytest.fixture()
def g5_candidate_root(tmp_path: Path) -> Path:
    """Self-contained candidate web root for the precondition tests."""
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "index.html").write_text(
        "<!doctype html><html><body>g5 precondition fixture</body></html>\n"
    )
    return root


def _parity_reports_hydration() -> list[Path]:
    """Return any hydration.json artifacts under parity-reports/ (untracked).

    The current slice-1 capture writes the baseline to the user-provided
    --baseline path, NOT to `parity-reports/<date>/hydration.json` — so a
    non-empty result here would mean the script bypassed `--baseline` and
    auto-emitted into the canonical G5 artifact location, which the
    precondition contract forbids.
    """
    base = REPO_ROOT / "parity-reports"
    return sorted(base.rglob("hydration.json")) if base.exists() else []


def test_g5_cli_requires_all_three_flags_together() -> None:
    """RED — zero G5 flags must fail closed; no artifact; no G5 pass claim."""
    before = _parity_reports_hydration()
    result = _run_script()
    after = _parity_reports_hydration()
    assert result.returncode != 0, (
        f"expected non-zero exit; got {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "g5 pass" not in (result.stdout + result.stderr).lower()
    assert after == before, f"hydration artifact emitted: {after}"


def test_g5_cli_iterations_must_equal_ten(
    g5_baseline_output: Path,
    g5_candidate_root: Path,
) -> None:
    """RED — --iterations must be exactly 10; any other value fails closed."""
    assert not g5_baseline_output.exists()
    before = _parity_reports_hydration()
    result = _run_script(
        "--baseline",
        str(g5_baseline_output),
        "--candidate",
        str(g5_candidate_root),
        "--iterations",
        "5",
    )
    after = _parity_reports_hydration()
    assert result.returncode != 0, (
        f"expected non-zero exit; got {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert "10" in combined, (
        f"stderr/stdout must mention required iterations=10; got {combined!r}"
    )
    assert "g5 pass" not in combined
    assert after == before, f"hydration artifact emitted: {after}"
    assert not g5_baseline_output.exists(), (
        f"precondition failed but output was written at {g5_baseline_output}"
    )


def test_g5_cli_candidate_must_exist(
    g5_baseline_output: Path,
    tmp_path: Path,
) -> None:
    """RED — --candidate must point at an existing build-root directory."""
    assert not g5_baseline_output.exists()
    before = _parity_reports_hydration()
    result = _run_script(
        "--baseline",
        str(g5_baseline_output),
        "--candidate",
        str(tmp_path / "no-such-candidate"),
        "--iterations",
        "10",
    )
    after = _parity_reports_hydration()
    assert result.returncode != 0, (
        f"expected non-zero exit; got {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert "candidate" in combined, (
        f"stderr/stdout must mention candidate; got {combined!r}"
    )
    assert "g5 pass" not in combined
    assert after == before, f"hydration artifact emitted: {after}"
    assert not g5_baseline_output.exists(), (
        f"precondition failed but output was written at {g5_baseline_output}"
    )


def test_g5_cli_preconditions_pass_does_not_claim_g5_pass(
    g5_baseline_output: Path,
    g5_candidate_root: Path,
) -> None:
    """TRIANGULATE — with all preconditions met, the slice must NOT claim
    G5 pass. The capture itself is allowed to write the baseline (per the
    slice-1 closure-path step 1 disposition), but the precondition contract
    guarantees that no output ever claims `G5 pass`.

    G5 stays `blocked — comparison not yet attempted` until closure-path
    steps 2 (candidate-side capture) + 3 (joining) + 4 (±10 % assertion)
    all close (design.md §3.3.5). The precondition slice cannot flip G5
    to `passed` on its own.
    """
    before = _parity_reports_hydration()
    result = _run_script(
        "--baseline",
        str(g5_baseline_output),
        "--candidate",
        str(g5_candidate_root),
        "--iterations",
        "10",
    )
    after = _parity_reports_hydration()
    combined = (result.stdout + result.stderr).lower()
    assert "g5 pass" not in combined, (
        f"preconditions met but output still claims G5 pass; got {combined!r}"
    )
    assert after == before, (
        f"unexpected parity-reports hydration emission (the slice must "
        f"only ever emit to the explicit --baseline path): {after}"
    )


def test_g5_cli_only_one_flag_fails_closed(g5_baseline_output: Path) -> None:
    """TRIANGULATE — providing one of three G5 flags must fail closed
    (not silently default to legacy mode or auto-fill the others).
    """
    before = _parity_reports_hydration()
    result = _run_script("--baseline", str(g5_baseline_output))
    after = _parity_reports_hydration()
    assert result.returncode != 0, (
        f"single flag must fail closed; got {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "g5 pass" not in (result.stdout + result.stderr).lower()
    assert after == before, f"hydration artifact emitted: {after}"
    assert not g5_baseline_output.exists()


def test_g5_cli_two_of_three_flags_fails_closed(
    g5_baseline_output: Path,
    g5_candidate_root: Path,
) -> None:
    """TRIANGULATE — two of three flags (missing --iterations) must fail
    closed. The contract is that the three flags MUST appear together;
    argparse's `default=1` for `--iterations` does NOT satisfy this —
    the precondition check requires the literal value 10.
    """
    before = _parity_reports_hydration()
    result = _run_script(
        "--baseline",
        str(g5_baseline_output),
        "--candidate",
        str(g5_candidate_root),
    )
    after = _parity_reports_hydration()
    assert result.returncode != 0, (
        f"two flags must fail closed; got {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "g5 pass" not in (result.stdout + result.stderr).lower()
    assert after == before, f"hydration artifact emitted: {after}"
    assert not g5_baseline_output.exists()


def test_g5_cli_baseline_must_not_be_an_existing_directory(
    g5_candidate_root: Path,
    tmp_path: Path,
) -> None:
    """TRIANGULATE — --baseline pointing at an existing directory (not a
    regular file path) must fail closed with the G5 precondition wording,
    not a downstream "cannot rename temp file → directory" surprise.
    """
    baseline_dir = tmp_path / "baseline-is-a-dir"
    baseline_dir.mkdir()
    before = _parity_reports_hydration()
    result = _run_script(
        "--baseline",
        str(baseline_dir),
        "--candidate",
        str(g5_candidate_root),
        "--iterations",
        "10",
    )
    after = _parity_reports_hydration()
    assert result.returncode != 0, (
        f"dir-as-baseline must fail closed; got {result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert "g5 pass" not in combined
    assert "baseline" in combined, (
        f"stderr/stdout must mention baseline; got {combined!r}"
    )
    assert after == before, f"hydration artifact emitted: {after}"
    # The directory must remain untouched (no spurious temp files inside).
    assert baseline_dir.is_dir()
    assert not any(baseline_dir.iterdir()), (
        f"precondition failed but temp file leaked into {baseline_dir}"
    )


def test_g5_cli_legacy_positional_path_preserved(hydration_artifact: Path) -> None:
    """TRIANGULATE — the legacy positional CLI path must remain intact
    after the precondition slice is added. The script must still
    validate a positional hydration JSON artifact and exit zero on a
    valid one.
    """
    result = _run_script(str(hydration_artifact))
    assert result.returncode == 0, (
        f"legacy positional path broken by G5 slice; "
        f"got exit={result.returncode}, stderr={result.stderr}"
    )