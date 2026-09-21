"""Hermetic tests for ``scripts/generate_g4_candidate_manifest.mjs``.

Approved issue #246 — restore the offline G4 candidate-manifest generator.
The generator runs in three phases:

  1. Validate argv (URL / HTML / manifest paths).
  2. Validate the HTML file (exists, non-empty, contains the literal
     ``data-testid="g4-probe-marker"`` substring) and the candidate
     URL (clean HTTP(S) only).
  3. Compute SHA-256 of the raw HTML bytes, build a manifest with
     schema ``taxa.g4-capture.manifest/1`` and a single entry carrying
     ``url``, ``path`` (HTML basename), ``expectedContentSha256``,
     ``expectedStatus`` (200) and ``expectedDOMMarker``, then write
     ONLY the manifest atomically (write to a sibling tmp file, then
     ``rename`` to the final path). Any pre-existing sibling file is
    left untouched.

The script is exercised end-to-end via ``node`` against a temporary
working tree; no Next build, no server, no fixture under version
control. Failure modes (missing args, missing marker, bad URL, empty
HTML, etc.) MUST exit non-zero BEFORE writing the manifest or running
``make parity``.

Reference: ``odd/tasks/g4-candidate-manifest-develop.md`` and the G4
capture consumer contract in ``tools/g4-capture/scripts/capture.mjs``.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "generate_g4_candidate_manifest.mjs"

# Locked schema + marker — the G4 capture consumer
# (``tools/g4-capture/scripts/capture.mjs``) refuses manifests that
# diverge from either of these constants.
MANIFEST_SCHEMA = "taxa.g4-capture.manifest/1"
EXPECTED_DOM_MARKER = 'data-testid="g4-probe-marker"'

SAMPLE_URL = "http://127.0.0.1:8765/index.html"
SAMPLE_HTTPS_URL = "https://taxa.example/index.html"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_html(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def _valid_html(marker: str = EXPECTED_DOM_MARKER) -> str:
    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <title>G4 candidate</title>\n"
        "</head>\n"
        "<body>\n"
        f"  <span hidden {marker} />\n"
        "</body>\n"
        "</html>\n"
    )


def _run_node(*args: str, cwd: Path | None = None,
              env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the generator script with ``node``; strip PARITY_* + candidate
    variables so leftover env cannot influence the run."""
    full_env = os.environ.copy()
    for k in (
        "PARITY_URL", "PARITY_OUT", "PARITY_MANIFEST",
        "PARITY_QUERIES", "PARITY_QUERIES_FILE",
        "CANDIDATE_URL", "CANDIDATE_HTML", "CANDIDATE_MANIFEST",
    ):
        full_env.pop(k, None)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["node", str(SCRIPT), *args],
        cwd=cwd or REPO_ROOT, env=full_env,
        capture_output=True, text=True, check=False,
    )


def _setup_html(tmp_path: Path, html_body: str | None = None) -> Path:
    html = tmp_path / "index.html"
    _write_html(html, html_body if html_body is not None else _valid_html())
    return html


def _run_valid(tmp_path: Path, *, html_body: str | None = None,
               url: str = SAMPLE_URL,
               manifest_path: Path | None = None) -> Path:
    """Drive a happy-path invocation; return the written manifest path."""
    html = _setup_html(tmp_path, html_body)
    manifest = manifest_path or (tmp_path / "manifest.json")
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", url,
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode == 0, (
        f"expected exit 0, got {r.returncode}\n"
        f"stdout: {r.stdout}\nstderr: {r.stderr}"
    )
    return manifest


# ---------------------------------------------------------------------------
# Argument validation (RED gate — script must reject missing args)
# ---------------------------------------------------------------------------


def test_script_exists() -> None:
    """The generator script MUST exist on the allowed edit surface."""
    assert SCRIPT.is_file(), (
        f"missing {SCRIPT.relative_to(REPO_ROOT)} — approved issue #246 "
        f"requires the offline generator on the current branch."
    )


def test_missing_required_arg_exits_nonzero(tmp_path: Path) -> None:
    """No args → fail closed with a stderr message naming a missing flag."""
    r = _run_node()
    assert r.returncode != 0, r.stdout + r.stderr
    combined = (r.stdout + r.stderr).lower()
    assert "missing" in combined or "required" in combined, (
        f"expected a 'missing/required' diagnostic, got: {r.stdout + r.stderr}"
    )


def test_missing_candidate_url_exits_nonzero(tmp_path: Path) -> None:
    """Missing --candidate-url → fail closed, manifest NOT written."""
    html = _setup_html(tmp_path)
    manifest = tmp_path / "manifest.json"
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode != 0, r.stdout + r.stderr
    assert not manifest.exists(), "manifest must NOT be written on failure"


def test_missing_candidate_manifest_exits_nonzero(tmp_path: Path) -> None:
    """Missing --candidate-manifest → fail closed."""
    html = _setup_html(tmp_path)
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", SAMPLE_URL,
    )
    assert r.returncode != 0, r.stdout + r.stderr


# ---------------------------------------------------------------------------
# HTML validation
# ---------------------------------------------------------------------------


def test_missing_html_file_exits_nonzero(tmp_path: Path) -> None:
    """Nonexistent HTML → fail closed, manifest NOT written."""
    html = tmp_path / "does_not_exist.html"
    manifest = tmp_path / "manifest.json"
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", SAMPLE_URL,
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode != 0, r.stdout + r.stderr
    assert not manifest.exists(), "manifest must NOT be written on failure"


def test_empty_html_file_exits_nonzero(tmp_path: Path) -> None:
    """Zero-byte HTML → fail closed (the consumer contract requires a
    non-empty HTML; the marker check would otherwise pass on an empty
    string iff the substring matched vacuously, but the contract pins
    non-empty as a hard requirement)."""
    html = tmp_path / "empty.html"
    html.write_text("", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", SAMPLE_URL,
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode != 0, r.stdout + r.stderr
    assert not manifest.exists(), "manifest must NOT be written on failure"


def test_html_missing_marker_exits_nonzero(tmp_path: Path) -> None:
    """HTML without the literal marker → fail closed with a diagnostic
    naming the missing marker, manifest NOT written."""
    html = tmp_path / "no_marker.html"
    _write_html(html, (
        "<!doctype html><html><body><h1>no marker here</h1></body></html>"
    ))
    manifest = tmp_path / "manifest.json"
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", SAMPLE_URL,
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode != 0, r.stdout + r.stderr
    assert "g4-probe-marker" in r.stderr or "marker" in r.stderr.lower(), (
        f"expected diagnostic naming the marker, got: {r.stderr}"
    )
    assert not manifest.exists(), "manifest must NOT be written on failure"


def test_html_marker_is_literal_substring(tmp_path: Path) -> None:
    """Marker must be the LITERAL substring ``data-testid="g4-probe-marker"``
    (matching ``tools/g4-capture/scripts/capture.mjs::verifyTarget`` which
    does a literal substring check on the raw bytes). A nearby but
    different test-id MUST be rejected."""
    html = tmp_path / "near_miss.html"
    _write_html(html, (
        "<!doctype html><html><body>"
        "<span data-testid='g4-probe-marker-extra'></span>"
        "</body></html>"
    ))
    manifest = tmp_path / "manifest.json"
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", SAMPLE_URL,
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode != 0, r.stdout + r.stderr
    assert not manifest.exists(), "manifest must NOT be written on failure"


# ---------------------------------------------------------------------------
# URL validation (clean HTTP(S))
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_url", [
    "ftp://taxa.example/index.html",
    "file:///tmp/index.html",
    "javascript:alert(1)",
    "data:text/html,<h1>x</h1>",
    "ws://taxa.example/",
    "",
])
def test_non_http_url_exits_nonzero(tmp_path: Path, bad_url: str) -> None:
    """Non-HTTP(S) URLs (or empty URL) MUST fail closed BEFORE writing."""
    html = _setup_html(tmp_path)
    manifest = tmp_path / "manifest.json"
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", bad_url,
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode != 0, r.stdout + r.stderr
    assert not manifest.exists(), "manifest must NOT be written on failure"


def test_https_url_is_accepted(tmp_path: Path) -> None:
    """HTTPS URLs MUST be accepted by the same clean-URL gate."""
    manifest = _run_valid(tmp_path, url=SAMPLE_HTTPS_URL)
    payload = json.loads(manifest.read_text())
    assert payload["entries"][0]["url"] == SAMPLE_HTTPS_URL


def test_malformed_url_exits_nonzero(tmp_path: Path) -> None:
    """Unparseable URL (whitespace inside host) → fail closed."""
    html = _setup_html(tmp_path)
    manifest = tmp_path / "manifest.json"
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", "http://exa mple.com/index.html",
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode != 0, r.stdout + r.stderr
    assert not manifest.exists(), "manifest must NOT be written on failure"


# ---------------------------------------------------------------------------
# Happy path: schema + entry fields
# ---------------------------------------------------------------------------


def test_writes_valid_manifest_with_required_schema(tmp_path: Path) -> None:
    """Valid input → manifest with schema ``taxa.g4-capture.manifest/1``
    and a single non-empty ``entries`` array."""
    manifest = _run_valid(tmp_path)
    payload = json.loads(manifest.read_text())
    assert payload["schema"] == MANIFEST_SCHEMA
    entries = payload["entries"]
    assert isinstance(entries, list) and entries


def test_manifest_entry_carries_consumer_required_fields(tmp_path: Path) -> None:
    """Each entry MUST carry every consumer-required field. ``capture.mjs``
    refuses entries missing any of these."""
    html_body = _valid_html()
    html = tmp_path / "candidate.html"
    _write_html(html, html_body)
    manifest = tmp_path / "manifest.json"
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", SAMPLE_URL,
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    payload = json.loads(manifest.read_text())
    entry = payload["entries"][0]
    assert entry["url"] == SAMPLE_URL
    assert entry["path"] == "candidate.html"  # HTML basename
    assert entry["expectedStatus"] == 200
    assert entry["expectedDOMMarker"] == EXPECTED_DOM_MARKER
    # SHA-256 is 64 lowercase hex chars.
    assert re.fullmatch(r"[0-9a-f]{64}", entry["expectedContentSha256"]), (
        f"expected 64-char lowercase hex sha256, got {entry['expectedContentSha256']!r}"
    )


def test_manifest_sha256_matches_raw_html_bytes(tmp_path: Path) -> None:
    """SHA-256 in the manifest MUST match the on-disk HTML bytes exactly.
    Same algorithm and encoding as the G4 capture consumer."""
    html_body = _valid_html()
    html = tmp_path / "candidate.html"
    _write_html(html, html_body)
    expected_sha = hashlib.sha256(html.read_bytes()).hexdigest()
    manifest = _run_valid(tmp_path, html_body=html_body)
    payload = json.loads(manifest.read_text())
    assert payload["entries"][0]["expectedContentSha256"] == expected_sha


def test_manifest_path_field_uses_html_basename(tmp_path: Path) -> None:
    """``path`` MUST be the HTML file basename (matches the corpus fixture
    convention so ``make parity`` correlates entry.path to fixture files)."""
    html = tmp_path / "subdir" / "index.html"
    html.parent.mkdir()
    _write_html(html, _valid_html())
    manifest = tmp_path / "manifest.json"
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", SAMPLE_URL,
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    payload = json.loads(manifest.read_text())
    assert payload["entries"][0]["path"] == "index.html"


def test_manifest_url_matches_candidate_url_exactly(tmp_path: Path) -> None:
    """Entry URL MUST be the literal --candidate-url value (no
    normalization, no trailing-slash mutation)."""
    target = "https://Taxa.Example:8443/sub/index.html?v=1"
    manifest = _run_valid(tmp_path, url=target)
    payload = json.loads(manifest.read_text())
    assert payload["entries"][0]["url"] == target


# ---------------------------------------------------------------------------
# Atomic write — only the manifest is touched
# ---------------------------------------------------------------------------


def test_atomic_write_preserves_sibling_files(tmp_path: Path) -> None:
    """Pre-existing files in the manifest's parent directory MUST be left
    byte-for-byte untouched (atomic-write contract — only the named
    output is published)."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    sibling = out_dir / "evidence.json"
    original_bytes = b'{"schema":"existing","keep":true}\n'
    sibling.write_bytes(original_bytes)
    manifest = out_dir / "candidate.manifest.json"
    html = _setup_html(tmp_path)
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", SAMPLE_URL,
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert sibling.read_bytes() == original_bytes, (
        "atomic-write contract violated — sibling evidence.json was "
        "modified even though only the manifest was requested."
    )
    # Manifest was written and parses.
    payload = json.loads(manifest.read_text())
    assert payload["schema"] == MANIFEST_SCHEMA


def test_atomic_write_creates_missing_parent_dir(tmp_path: Path) -> None:
    """Parent directory of the manifest path MUST be created on demand."""
    manifest = tmp_path / "nested" / "deeper" / "manifest.json"
    html = _setup_html(tmp_path)
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", SAMPLE_URL,
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert manifest.is_file(), f"manifest not written at {manifest}"


def test_atomic_write_does_not_leave_tmp_files(tmp_path: Path) -> None:
    """Successful run MUST NOT leave any sibling .tmp-* files behind in
    the manifest's parent directory."""
    manifest = tmp_path / "manifest.json"
    html = _setup_html(tmp_path)
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", SAMPLE_URL,
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    leftovers = [
        p for p in manifest.parent.iterdir()
        if p.name != manifest.name and ".tmp-" in p.name
    ]
    assert not leftovers, f"atomic write leaked temp files: {leftovers}"


def test_atomic_write_overwrites_prior_manifest_atomically(tmp_path: Path) -> None:
    """Re-running the generator MUST replace the prior manifest with the
    new one (atomic overwrite). Old payload is gone; new payload parses."""
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(b'{"stale":true}\n')
    html = _setup_html(tmp_path)
    r = _run_node(
        "--candidate-html", str(html),
        "--candidate-url", SAMPLE_URL,
        "--candidate-manifest", str(manifest),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    payload = json.loads(manifest.read_text())
    assert payload["schema"] == MANIFEST_SCHEMA
    assert "stale" not in payload
