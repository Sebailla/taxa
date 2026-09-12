"""G4 candidate-manifest producer-adapter tests — hermetic filesystem only.
No network, no Chromium, no live server.

Adapter: scripts/generate_g4_candidate_manifest.mjs (Node CLI).
Contract: --html <out/index.html> --url <http(s) URL> --out <path>. Validate
everything up front, then publish one entry {url, path, expectedContentSha256,
expectedStatus:200, expectedDOMMarker:'data-testid="g4-probe-marker"'}. `path`
is the HTML path relative to cwd when possible, else the supplied html
basename. Atomic temp+rename. Refuse (non-zero exit, no output) for: missing
args, missing/non-regular html, non-http(s) URL, raw-html bytes lacking the
exact marker, existing --out (file OR symlink), write failure.

Tests do NOT touch tools/g4-capture/scripts/capture.mjs — that file is a
downstream consumer owned by an earlier G4 slice.
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
LAYOUT = REPO_ROOT / "src" / "app" / "layout.tsx"
OUT_INDEX = REPO_ROOT / "out" / "index.html"

MARKER_TOKEN = 'data-testid="g4-probe-marker"'
SCHEMA_VERSION = "taxa.g4-capture.manifest/1"
GOOD_URL = "https://taxa.example/candidate/"


def _write_html(tmp_path: Path, *, marker=MARKER_TOKEN,
                basename="index.html", subdir: str | None = None) -> Path:
    """Fixture HTML; marker=None = no-marker case; subdir parents the file."""
    if subdir:
        (tmp_path / subdir).mkdir(parents=True, exist_ok=True)
    p = (tmp_path / subdir / basename) if subdir else (tmp_path / basename)
    body = "<html><body>host</body></html>\n"
    if marker:
        body += f"{marker}\n"
    p.write_text(body, encoding="utf-8")
    return p


def _run(args, *, cwd, env=None):
    full_env = os.environ.copy()
    full_env.pop("NODE_ENV", None)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["node", str(SCRIPT), *args], cwd=str(cwd),
        capture_output=True, text=True, check=False,
        env=full_env, timeout=60,
    )


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        pytest.fail(f"invalid JSON in {path}: {exc}")
        raise


# Pattern matching one element carrying all three attributes together
# (in either attribute order). Pins the SSR marker contract.
_MARKER_ELEMENT_RE = re.compile(
    r'<\w+\b[^>]*\bdata-testid="g4-probe-marker"[^>]*\b'
    r'(?:aria-hidden="true"[^>]*\bhidden\b|hidden\b[^>]*\baria-hidden="true")'
    r'[^>]*?/?>',
    re.DOTALL,
)


# CLI — happy path
def test_cli_emits_well_formed_manifest_with_correct_sha256(tmp_path):
    html = _write_html(tmp_path)
    out_manifest = tmp_path / "candidate.manifest.json"
    r = _run(["--html", str(html), "--url", GOOD_URL,
              "--out", str(out_manifest)], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    doc = _read_json(out_manifest)
    assert doc["schema"] == SCHEMA_VERSION
    assert isinstance(doc.get("entries"), list) and len(doc["entries"]) == 1
    entry = doc["entries"][0]
    assert entry["url"] == GOOD_URL
    assert entry["path"] == "index.html"  # POSIX-relative to cwd
    assert entry["expectedStatus"] == 200
    assert entry["expectedDOMMarker"] == MARKER_TOKEN
    assert entry["expectedContentSha256"] == hashlib.sha256(html.read_bytes()).hexdigest()


def test_cli_writes_posix_relative_path_for_nested_html(tmp_path):
    html = _write_html(tmp_path, subdir="candidate-build/out")
    r = _run(["--html", str(html), "--url", "http://127.0.0.1:8765/",
              "--out", str(tmp_path / "candidate.manifest.json")], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert _read_json(tmp_path / "candidate.manifest.json")["entries"][0]["path"] == "candidate-build/out/index.html"


# CLI — fail-closed guards
def test_cli_rejects_html_missing_exact_marker(tmp_path):
    html = _write_html(tmp_path, marker=None)
    out_manifest = tmp_path / "candidate.manifest.json"
    r = _run(["--html", str(html), "--url", GOOD_URL,
              "--out", str(out_manifest)], cwd=tmp_path)
    assert r.returncode != 0, r.stdout
    assert not out_manifest.exists()
    assert not any(p.name.startswith("candidate.manifest.json.")
                   for p in tmp_path.iterdir()), "temp staging files must not leak"


@pytest.mark.parametrize("near_token", [
    'data-testid="g4-probe-markerx"',   # trailing char differs
    'data-testid="G4-probe-marker"',    # case differs
    'data-testid="g4-probe-marker "',   # trailing whitespace
    "data-testid=g4-probe-marker",      # missing quotes
    "data-testid='g4-probe-marker'",    # single-quoted attribute
])
def test_cli_rejects_similar_only_token(tmp_path, near_token):
    # capture.mjs performs substring include() verification, so any candidate
    # HTML whose bytes lack the literal `data-testid="g4-probe-marker"` would
    # silently slip through. The exact-marker guard exists to prevent that.
    html = _write_html(tmp_path, marker=near_token)
    out_manifest = tmp_path / "candidate.manifest.json"
    r = _run(["--html", str(html), "--url", GOOD_URL,
              "--out", str(out_manifest)], cwd=tmp_path)
    assert r.returncode != 0, f"{near_token!r} must be rejected; stdout={r.stdout!r}"
    assert not out_manifest.exists()


@pytest.mark.parametrize("bad_url", [
    "", "https://", "taxa.example/candidate", "ftp://taxa.example/candidate",
    "javascript:alert(1)", "file:///etc/passwd", "/relative/path",
    "//taxa.example/candidate",
])
def test_cli_rejects_non_http_url(tmp_path, bad_url):
    r = _run(["--html", str(_write_html(tmp_path)), "--url", bad_url,
              "--out", str(tmp_path / "candidate.manifest.json")], cwd=tmp_path)
    assert r.returncode != 0, f"{bad_url!r} must be rejected"
    assert not (tmp_path / "candidate.manifest.json").exists()


def test_cli_rejects_missing_or_non_regular_html(tmp_path):
    out_manifest = tmp_path / "candidate.manifest.json"
    # Missing file
    r = _run(["--html", str(tmp_path / "missing.html"),
              "--url", GOOD_URL, "--out", str(out_manifest)], cwd=tmp_path)
    assert r.returncode != 0 and not out_manifest.exists()
    # Directory (not a regular file)
    r = _run(["--html", str(tmp_path), "--url", GOOD_URL,
              "--out", str(out_manifest)], cwd=tmp_path)
    assert r.returncode != 0 and not out_manifest.exists()


@pytest.mark.parametrize("existing", ["file", "symlink"])
def test_cli_refuses_to_overwrite_existing_out(tmp_path, existing):
    """Both a regular file AND a symlink at --out must trigger the no-overwrite
    guard. Existing bytes must be preserved verbatim on refusal."""
    out_manifest = tmp_path / "candidate.manifest.json"
    if existing == "file":
        out_manifest.write_text('{"sentinel":"must-not-be-overwritten"}', encoding="utf-8")
        sentinel_path = out_manifest
    else:
        target = tmp_path / "real-manifest.json"
        target.write_text('{"sentinel":"symlinked"}', encoding="utf-8")
        out_manifest.symlink_to(target)
        sentinel_path = target
    sentinel = sentinel_path.read_text(encoding="utf-8")
    r = _run(["--html", str(_write_html(tmp_path)), "--url", GOOD_URL,
              "--out", str(out_manifest)], cwd=tmp_path)
    assert r.returncode != 0, f"overwrite({existing}) must be refused; stdout={r.stdout!r}"
    assert sentinel_path.read_text(encoding="utf-8") == sentinel


@pytest.mark.parametrize("fail_at", ["write", "rename"])
def test_cli_atomic_failure_leaves_no_partial_output(tmp_path, fail_at):
    # Test-only hook G4_CANDIDATE_FAIL_AT stages a synthetic failure inside
    # the atomic-publish step. No manifest may appear at --out, and no temp
    # file may be left behind on either failure path.
    out_manifest = tmp_path / "candidate.manifest.json"
    r = _run(["--html", str(_write_html(tmp_path)), "--url", GOOD_URL,
              "--out", str(out_manifest)], cwd=tmp_path,
             env={"G4_CANDIDATE_FAIL_AT": fail_at})
    assert r.returncode != 0, f"injected {fail_at} failure must yield non-zero exit"
    assert not out_manifest.exists()
    leftovers = [p for p in tmp_path.iterdir()
                 if p.name.startswith("candidate.manifest.json.")]
    assert not leftovers, f"injected {fail_at} failure leaked staged files: {leftovers}"


def test_cli_creates_parent_dirs_only_after_all_validation(tmp_path):
    # On success: missing parent dirs under --out are created. On validation
    # failure: NO new directories are created under the failure path. The
    # no-parents-on-failure guard prevents racing a half-written tree before
    # every other gate has actually fired.
    nested_ok = tmp_path / "fresh" / "deeply" / "nested" / "candidate.manifest.json"
    html = _write_html(tmp_path)
    r = _run(["--html", str(html), "--url", GOOD_URL,
              "--out", str(nested_ok)], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert nested_ok.is_file()
    nested_bad = tmp_path / "fresh2" / "deeply" / "nested" / "candidate.manifest.json"
    r = _run(["--html", str(html), "--url", "not-a-url",
              "--out", str(nested_bad)], cwd=tmp_path)
    assert r.returncode != 0
    assert not nested_bad.parent.exists(), "Parents must NOT be created on validation failure."


@pytest.mark.parametrize("missing", ["--html", "--url", "--out"])
def test_cli_rejects_missing_required_arg(tmp_path, missing):
    html = _write_html(tmp_path)
    out_manifest = tmp_path / "candidate.manifest.json"
    base = {"--html": str(html), "--url": GOOD_URL, "--out": str(out_manifest)}
    args = [v for k, v in base.items() if k != missing]
    r = _run(args, cwd=tmp_path)
    assert r.returncode != 0, f"missing {missing} must be rejected; stdout={r.stdout!r}"
    assert not out_manifest.exists()


# Build witness — the candidate's actual built HTML must carry the marker
def test_layout_root_carries_exact_marker_attributes():
    # layout.tsx emits one SSR element with all three attributes co-located
    # on the same tag: data-testid="g4-probe-marker", aria-hidden="true", AND
    # the `hidden` attribute. Downstream capture.mjs probes this exact element.
    if not LAYOUT.is_file():
        pytest.fail(f"{LAYOUT} missing — cannot pin SSR marker contract.")
    assert _MARKER_ELEMENT_RE.search(LAYOUT.read_text(encoding="utf-8")), (
        "layout.tsx must contain a single JSX element carrying "
        'data-testid="g4-probe-marker", aria-hidden="true", AND `hidden` '
        "together. The byte-exact marker is what capture.mjs probes."
    )


def test_candidate_build_output_contains_hidden_accessible_safe_marker():
    # Built out/index.html must carry the byte-exact marker. Skipped when the
    # build hasn't produced the static export (CI cold cache) — we do NOT spawn
    # `npm run build:web` from this test to keep the suite hermetic.
    if not OUT_INDEX.is_file():
        pytest.skip(
            f"{OUT_INDEX} missing — candidate build has not produced the "
            "static export. Re-run after `npm run build:web` to witness the "
            "marker in the built HTML."
        )
    raw = OUT_INDEX.read_text(encoding="utf-8")
    assert MARKER_TOKEN in raw, (
        f"Built {OUT_INDEX} is missing the exact {MARKER_TOKEN!r} marker. "
        "Either the layout didn't render the SSR marker or the build is stale."
    )
    assert _MARKER_ELEMENT_RE.search(raw), (
        "Built out/index.html must include the SSR marker element with "
        "`hidden` AND `aria-hidden=\"true\"` together (in either order) on "
        "the same tag. The element is the G4 probe target — non-user-visible "
        "AND reachable to capture.mjs's DOM probe."
    )
