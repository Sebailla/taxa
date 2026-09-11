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