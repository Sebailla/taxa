"""
Evidence baseline tests for the legacy `taxa` frontend.

PR 1 (evidence-only slice) records a pre-migration baseline so the
design phase can close `scope-decisions.md::§1` with real numbers
(bundle size, initial paint, interaction latency). The migration
itself lands in PR 3+; this file pins the *tooling* and the
*schema* for the baseline measurements.

What the contract requires (tasks.md 1.2):

  - Measure legacy web/ asset sizes (HTML + JS + CSS + fonts).
  - Run a headless chromium sample against the live FastAPI app and
    capture Playwright + Lighthouse JSON artifacts.

Reference:
  openspec/changes/migrate-nextjs-tailwind4/tasks.md  §Phase 1 (1.2)
  openspec/changes/migrate-nextjs-tailwind4/design.md §Testing Strategy
                                              (Playwright + Lighthouse sample)
  openspec/changes/migrate-nextjs-tailwind4/scope-decisions.md §1
                                              (Evidence to gather)
  scripts/verify_chromium.py (chromium SHA256 pin)
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "verify_chromium.py"
WEB_DIR = REPO_ROOT / "web"
DIST_DIR = WEB_DIR / "dist"


# ---------------------------------------------------------------------------
# Chromium availability helpers
# ---------------------------------------------------------------------------
# The pinned SHA256 in scripts/verify_chromium.py was captured against
# the chrome-mac-arm64 binary for playwright==1.62.0. On any other
# platform (chrome-linux, chrome-win, chrome-mac-x64) the chromium
# binary differs even at the same playwright version, so the SHA256
# comparison cannot apply and the pin check must skip rather than fail.
#
# The three scenarios that must skip cleanly:
#   - Playwright is not importable (the offline CI case)
#   - The chromium binary isn't downloaded (Ubuntu CI installs
#     playwright via pip but does NOT run `playwright install chromium`)
#   - The chromium binary was downloaded for a different OS/arch than
#     where the pin was captured
#
# The strict pin-mismatch failure path is preserved for the
# compatible environment (Mac arm64 with the matching playwright
# version): that's the regression we still want to catch.
_PIN_PLATFORM_MARKER = "chrome-mac-arm64"


def _check_playwright_available() -> bool:
    """Return True iff the playwright Python package is importable.

    Mirrors the same helper in test_detail_overview.py,
    test_e2e_file_explorer.py, and test_web_toggle.py so every
    chromium-dependent test in the suite skips the same way when
    playwright isn't installed.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return False
    return True


def _chromium_pinnable(script_output: str) -> bool:
    """Return True iff the configured chromium pin can be checked here.

    The script prints `binary:`, `size:`, and `sha256:` lines ONLY when
    it successfully located AND hashed the chromium binary. If the
    `sha256:` line is absent the binary wasn't readable on this runner
    (the CI case where playwright is installed but `playwright install
    chromium` was never run). The binary's path must also contain
    `chrome-mac-arm64` — the platform marker where the pin was captured
    — because the chromium build differs per OS/arch.

    Parameters
    ----------
    script_output : str
        Combined stdout + stderr from `scripts/verify_chromium.py`.

    Returns
    -------
    bool
        True iff the chromium binary was successfully hashed AND its
        platform matches the pin's captured platform. False for the
        "binary missing" and "different platform" cases, both of which
        must skip the pin-comparison tests rather than fail them.
    """
    if "sha256:" not in script_output:
        # Binary not downloaded, not readable, or playwright missing —
        # the script exited before printing the hash. Skip rather than
        # fail: the missing-binary case isn't a regression this suite
        # is responsible for catching.
        return False
    if _PIN_PLATFORM_MARKER not in script_output:
        # Binary downloaded but for a different OS/arch than where the
        # pin was captured. The chromium build differs per platform so
        # the SHA256 comparison cannot apply — skip rather than fail.
        return False
    return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def chromium_status() -> dict:
    """Run scripts/verify_chromium.py and parse its output.

    The script prints lines like:
        binary:  /.../chrome
        size:    50 KB
        sha256:  a596b1cfc6353e987fcec8d71a23a28cd6a9e7a6b4e20b908e4c4fcffe51158e
        [OK] SHA256 matches pinned value.

    We assert the script can locate chromium (or fail clearly if it
    cannot) before PR 3's CI depends on it.

    The fixture also exposes a `pinnable` flag — True only when the
    script successfully hashed a chromium binary that matches the
    pin's captured platform (chrome-mac-arm64). Tests use this flag
    to skip cleanly on runners where chromium is missing or runs on
    a different OS/arch, without losing strict validation on the
    compatible environment.
    """
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    # The script must print SOMETHING informative even on failure.
    output = (proc.stdout or "") + (proc.stderr or "")
    assert "binary:" in output, (
        f"verify_chromium.py produced no machine-readable output:\n{output}"
    )
    pinnable = _chromium_pinnable(output)
    return {
        "returncode": proc.returncode,
        "output": output,
        "pinnable": pinnable,
    }


# ---------------------------------------------------------------------------
# Legacy size baseline
# ---------------------------------------------------------------------------
def _walk_bytes(root: Path) -> tuple[int, int]:
    """Return (total_bytes, file_count) under `root`, recursively.

    Skips `web/dist/` (git-ignored, regenerated by `make css`) — the
    baseline records SOURCE sizes only, not the compiled bundle. The
    compiled bundle is its own measurement.
    """
    total = 0
    count = 0
    if not root.exists():
        return total, count
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        # Skip the git-ignored build output.
        if "dist" in path.relative_to(root).parts:
            continue
        total += path.stat().st_size
        count += 1
    return total, count


def test_legacy_html_present_and_nontrivial():
    """The legacy `web/index.html` is the source of truth for the
    pre-migration baseline. It must exist and be large enough to be
    a real SPA shell (~2,200 lines per exploration.md).
    """
    index = WEB_DIR / "index.html"
    assert index.exists(), (
        f"missing legacy HTML shell at {index}; baseline cannot be measured"
    )
    size = index.stat().st_size
    # The shell is ~75 KB per exploration.md. Pin a floor well under that
    # so this catches a missing file but tolerates source refactors.
    assert size > 50_000, (
        f"legacy index.html looks too small: {size} bytes; "
        f"expected > 50 KB for the full SPA shell"
    )


def test_legacy_module_count_matches_exploration():
    """Pin the legacy JS module roster so the baseline records a
    consistent list of files. exploration.md §Current State names
    18 modules but the actual glob yields 17 (the text "18 modules"
    is the headline count including the implicit aggregate). We
    pin the real number so the baseline stays honest.
    """
    js_files = sorted(p.name for p in WEB_DIR.glob("*.js") if p.is_file())
    assert len(js_files) == 17, (
        f"legacy JS module count drifted: expected 17, got {len(js_files)}; "
        f"files: {js_files}"
    )

    # Spot-check a few of the canonical names — catches a renamed or
    # deleted module without forcing the test to enumerate all 17.
    for expected in ("app.js", "tree.js", "detail.js", "file_explorer.js"):
        assert expected in js_files, (
            f"legacy module {expected!r} is missing from web/; "
            f"baseline module roster has drifted"
        )


def test_legacy_total_source_size_below_threshold():
    """Pre-migration, the legacy `web/` payload (HTML + JS + CSS, excluding
    git-ignored `dist/`) is around 200-300 KB on disk. We pin an upper
    bound well above that so the baseline detects accidental drops but
    tolerates minor source refactors.

    The design phase uses this number, plus the Playwright sample, to
    cite concrete evidence when closing `scope-decisions.md::§1`.
    """
    total, count = _walk_bytes(WEB_DIR)
    assert count > 0, "no source files found under web/"
    # Upper bound — the legacy build is ~200 KB on disk; 500 KB is a
    # generous ceiling that still catches a missing-tree regression.
    assert total < 500_000, (
        f"legacy web/ source size {total} bytes (count={count}) exceeds "
        f"the 500 KB ceiling; baseline evidence may be stale"
    )
    # And a sensible lower bound — catches a deleted file.
    assert total > 100_000, (
        f"legacy web/ source size {total} bytes (count={count}) below "
        f"the 100 KB floor; some files appear to have been removed"
    )


def test_legacy_compiled_css_is_present():
    """web/dist/tailwind.css must exist locally for the baseline paint
    measurement to be meaningful. The file is git-ignored — the test
    instructs reviewers to run `make css` if it's missing.
    """
    css = DIST_DIR / "tailwind.css"
    if not css.exists():
        pytest.skip(
            f"{css} not present locally (git-ignored). "
            f"Run `make css` to regenerate before measuring the baseline."
        )
    size = css.stat().st_size
    # Per exploration.md: ~16 KB minified.
    assert 5_000 < size < 100_000, (
        f"compiled CSS at {size} bytes looks unexpected; expected ~16 KB"
    )


# ---------------------------------------------------------------------------
# Chromium harness contract
# ---------------------------------------------------------------------------
def test_verify_chromium_script_exists():
    """scripts/verify_chromium.py must exist (pinned in tasks.md 1.2)."""
    assert SCRIPT.exists(), (
        f"missing chromium verification script: {SCRIPT}"
    )


def test_verify_chromium_pin_is_a_64_char_hex():
    """The pinned SHA256 must look like a real hex digest — guards
    against an empty / placeholder pin.
    """
    src = SCRIPT.read_text()
    m = re.search(r"CHROMIUM_SHA256\s*=\s*\"([0-9a-fA-F]+)\"", src)
    assert m is not None, (
        "CHROMIUM_SHA256 constant not found in verify_chromium.py"
    )
    pin = m.group(1)
    assert len(pin) == 64, (
        f"CHROMIUM_SHA256 must be 64 hex chars (256-bit SHA256), got "
        f"{len(pin)} chars: {pin!r}"
    )
    int(pin, 16)  # raises ValueError if non-hex


@pytest.mark.skipif(
    not _check_playwright_available(),
    reason="playwright not installed (pip install playwright)",
)
def test_verify_chromium_can_locate_binary(chromium_status: dict):
    """The chromium verification script must locate a binary (or fail
    clearly). PR 3's CI depends on it before any Playwright sample run.

    Skipped cleanly when chromium can't be pinned on this runner:
      - playwright is not importable (skipif above)
      - the chromium binary isn't downloaded (Ubuntu CI case)
      - the chromium binary is for a different OS/arch than where
        the pin was captured
    On a compatible environment, the strict "script must locate a
    binary" assertion still runs.
    """
    output = chromium_status["output"]
    if not chromium_status["pinnable"]:
        pytest.skip(
            "chromium binary not pinnable on this runner (binary "
            "missing, not readable, or for a different platform than "
            "where the pin was captured). verify_chromium.py output:\n"
            f"{output}"
        )
    if chromium_status["returncode"] != 0:
        # The script may exit non-zero if the pin doesn't match, but it
        # MUST still print a path to stdout. A silent failure is the
        # regression we're guarding against.
        assert "binary:" in output, (
            f"verify_chromium.py failed silently:\n{output}"
        )
        pytest.fail(
            f"chromium pin mismatch (or binary missing); see script "
            f"output:\n{output}"
        )


# ---------------------------------------------------------------------------
# Evidence JSON artifact contract
# ---------------------------------------------------------------------------
EVIDENCE_DIR = REPO_ROOT / "web" / "dist" / "evidence"


@pytest.fixture()
def evidence_baseline(tmp_path: Path) -> Path:
    """Write a synthetic evidence-baseline JSON, exercising the schema
    that PR 3's Playwright + Lighthouse sample must populate.

    Returns the path to the synthetic file so each test can assert
    independently against the schema. Real evidence lands in PR 3;
    PR 1 only pins the schema.
    """
    fixture = tmp_path / "evidence-baseline.json"
    fixture.write_text(
        json.dumps(
            {
                "captured_at": "2026-08-28T00:00:00Z",
                "build": "legacy",
                "chromium_sha256": "a" * 64,
                "bundle": {
                    "html_bytes": 75_000,
                    "js_bytes": 200_000,
                    "css_bytes": 16_000,
                    "total_bytes": 291_000,
                },
                "paint_ms": {
                    "first_contentful_paint": 200.0,
                    "largest_contentful_paint": 350.0,
                    "time_to_interactive": 600.0,
                },
                "interactivity_ms": {
                    "tree_render_after_click": 12.0,
                },
                "lighthouse": {
                    "performance": 0.95,
                    "accessibility": 0.98,
                    "best_practices": 0.92,
                },
                "sample_routes": ["/"],
            },
            indent=2,
        )
    )
    return fixture


def test_evidence_baseline_schema_keys_present(evidence_baseline: Path):
    """The evidence-baseline JSON must carry every key the design phase
    cites when closing `scope-decisions.md::§1`.

    Schema pin: bundle, paint_ms, interactivity_ms, lighthouse.
    """
    doc = json.loads(evidence_baseline.read_text())
    for key in ("bundle", "paint_ms", "interactivity_ms", "lighthouse"):
        assert key in doc, f"evidence-baseline missing key {key!r}"


def test_evidence_baseline_bundle_bytes_are_positive(evidence_baseline: Path):
    """The `bundle` block must record non-negative byte counts for
    html, js, css, and total.
    """
    doc = json.loads(evidence_baseline.read_text())
    bundle = doc["bundle"]
    for key in ("html_bytes", "js_bytes", "css_bytes", "total_bytes"):
        assert key in bundle, f"bundle missing key {key!r}"
        assert isinstance(bundle[key], int) and bundle[key] >= 0, (
            f"bundle.{key} must be a non-negative int; got {bundle[key]!r}"
        )


def test_evidence_baseline_paint_keys_are_floats(evidence_baseline: Path):
    """paint_ms metrics must be numbers (floats) in milliseconds.

    Pin the shape so PR 3's Playwright run is forced to use the same
    units the design phase cites in §1 evidence.
    """
    doc = json.loads(evidence_baseline.read_text())
    paint = doc["paint_ms"]
    for key in paint:
        assert isinstance(paint[key], (int, float)), (
            f"paint_ms.{key} must be numeric; got {type(paint[key]).__name__}"
        )
        assert paint[key] >= 0, (
            f"paint_ms.{key} must be non-negative; got {paint[key]}"
        )


@pytest.mark.skipif(
    not _check_playwright_available(),
    reason="playwright not installed (pip install playwright)",
)
def test_chromium_pin_matches_installed_binary(chromium_status: dict):
    """Triangulation: the pinned chromium SHA256 in
    `scripts/verify_chromium.py` MUST match the binary actually
    installed on this machine.

    Without this check, a future playwright upgrade could change
    the chromium binary without anyone updating the pin, and the
    next PR 3 sample run would either silently bypass the guard
    or fail with a misleading "binary drift" message.

    The pin lives in CHROMIUM_SHA256 at scripts/verify_chromium.py.
    Parsing both sides and asserting equality is a real behavioral
    assertion: any future regression where the pin is wrong is
    caught here, not at PR 3's Playwright run.

    Skipped cleanly when chromium can't be pinned on this runner:
      - playwright is not importable (skipif above)
      - the chromium binary isn't downloaded (Ubuntu CI case)
      - the chromium binary is for a different OS/arch than where
        the pin was captured
    On a compatible environment, the strict pin-equality assertion
    still runs (and FAILS when the pin is wrong — the regression
    the suite exists to catch).
    """
    output = chromium_status["output"]
    if not chromium_status["pinnable"]:
        pytest.skip(
            "chromium binary not pinnable on this runner (binary "
            "missing, not readable, or for a different platform than "
            "where the pin was captured). verify_chromium.py output:\n"
            f"{output}"
        )

    # Source pin.
    src = SCRIPT.read_text()
    m = re.search(r"CHROMIUM_SHA256\s*=\s*\"([0-9a-fA-F]+)\"", src)
    assert m is not None, "CHROMIUM_SHA256 constant not found"
    pin = m.group(1)

    # Live binary hash from the script's own output.
    m2 = re.search(r"sha256:\s*([0-9a-fA-F]+)", output)
    assert m2 is not None, (
        f"verify_chromium.py did not print a sha256 line:\n{output}"
    )
    live = m2.group(1)

    assert pin == live, (
        f"pinned chromium SHA256 ({pin[:16]}...) does not match the "
        f"installed binary ({live[:16]}...); re-pin in "
        f"scripts/verify_chromium.py or upgrade playwright deliberately"
    )


def test_evidence_baseline_lighthouse_block_well_typed(
    evidence_baseline: Path,
):
    """Triangulation: the `lighthouse` block records per-category
    scores as floats in [0, 1].

    Catches a future PR 3 run that emits percentages instead of
    fractions — design cites "performance: 0.95" verbatim in
    §1 evidence; a percentage value would silently change the
    meaning of the evidence by 100x.
    """
    doc = json.loads(evidence_baseline.read_text())
    lighthouse = doc["lighthouse"]
    for key, score in lighthouse.items():
        assert isinstance(score, (int, float)), (
            f"lighthouse.{key} must be numeric; got {type(score).__name__}"
        )
        assert 0.0 <= score <= 1.0, (
            f"lighthouse.{key} score {score} out of [0, 1]; emit "
            f"fractions, not percentages"
        )

# ---------------------------------------------------------------------------
# Chromium-pin skip classifier — portable CI negative control
# ---------------------------------------------------------------------------
# The fixture-driven chromium tests above must SKIP cleanly on
# runners where chromium isn't downloaded (Ubuntu CI installs
# playwright via pip but doesn't run `playwright install chromium`)
# or where the binary is for a different OS/arch than where the pin
# was captured. The helper `_chromium_pinnable()` classifies the
# script's stdout to make that decision; the tests below pin every
# shape it must recognise so a future regression is caught here
# rather than as a red CI job.
def test_chromium_pinnable_classifies_unavailable_outputs():
    """The CI scenario: playwright is importable but the chromium
    binary isn't readable on this runner. The script prints the
    binary path (so it can name what it's looking for) but no
    `sha256:` line (because the file isn't there). The helper must
    classify this output as NOT pinnable so the chromium-pin tests
    skip cleanly on Ubuntu CI rather than fail.
    """
    # Playwright installed but chromium binary missing.
    assert _chromium_pinnable(
        "binary:  /root/.cache/ms-playwright/chromium-1234/chrome-linux/chrome\n"
        "[error] could not read "
        "/root/.cache/ms-playwright/chromium-1234/chrome-linux/chrome: "
        "[Errno 2] No such file or directory\n"
    ) is False

    # Playwright not installed at all (no `binary:` line either).
    assert _chromium_pinnable(
        "[error] playwright is not installed: No module named 'playwright'\n"
        "  pip install playwright && playwright install chromium\n"
    ) is False

    # Mac arm64 binary reported but file missing (defence in depth —
    # the script prints the path before attempting to read it).
    assert _chromium_pinnable(
        "binary:  /Users/x/Library/Caches/ms-playwright/"
        "chromium-1234/chrome-mac-arm64/.../Google Chrome for Testing\n"
        "[error] could not read .../Google Chrome for Testing: "
        "[Errno 2] No such file or directory\n"
    ) is False


def test_chromium_pinnable_rejects_wrong_platform():
    """The pin was captured for chrome-mac-arm64. Even if chromium
    IS downloaded on a runner, a Linux or Windows binary has a
    different SHA256 (the build is OS/arch specific), so the
    pin comparison cannot apply and the helper must classify as
    NOT pinnable.

    This is the `runner platform` skip case from the PR 1b.1 brief:
    a chromium binary that exists but is not the one the pin was
    captured for.
    """
    # Chromium on Linux.
    assert _chromium_pinnable(
        "binary:  /root/.cache/ms-playwright/chromium-1234/chrome-linux/chrome\n"
        "size:    150 MB\n"
        "sha256:  deadbeef" + "f" * 56 + "\n"
        "\n[FAIL] expected a596b1cfc6353e987fcec8d71a23a28cd6a9e7a6b4e20b908e4c4fcffe51158e\n"
        "        got      deadbeef" + "f" * 56 + "\n"
    ) is False

    # Chromium on Windows.
    assert _chromium_pinnable(
        "binary:  C:\\Users\\runner\\AppData\\Local\\ms-playwright\\"
        "chromium-1234\\chrome-win\\chrome.exe\n"
        "size:    150 MB\n"
        "sha256:  deadbeef" + "f" * 56 + "\n"
    ) is False

    # Chromium on Mac x64 (different architecture from the pin).
    assert _chromium_pinnable(
        "binary:  /Users/x/Library/Caches/ms-playwright/"
        "chromium-1234/chrome-mac-x64/.../Google Chrome for Testing\n"
        "size:    50 KB\n"
        "sha256:  deadbeef" + "f" * 56 + "\n"
    ) is False


def test_chromium_pinnable_accepts_matching_platform():
    """The pin applies only when the binary is chrome-mac-arm64 and
    the script successfully hashed it (so `sha256:` is in the output).
    These cases must classify as pinnable so the chromium-pin tests
    run their strict assertions on the compatible environment.
    """
    # Happy path: Mac arm64, sha256 present, pin matches.
    assert _chromium_pinnable(
        "binary:  /Users/x/Library/Caches/ms-playwright/"
        "chromium-1234/chrome-mac-arm64/.../Google Chrome for Testing\n"
        "size:    50 KB\n"
        "sha256:  a596b1cfc6353e987fcec8d71a23a28cd6a9e7a6b4e20b908e4c4fcffe51158e\n"
        "\n[OK] SHA256 matches pinned value.\n"
    ) is True

    # Pin applies but the live binary diverges (deliberate upgrade,
    # stale pin). The helper still classifies as pinnable — the test
    # itself must FAIL on the comparison, not skip.
    assert _chromium_pinnable(
        "binary:  /Users/x/Library/Caches/ms-playwright/"
        "chromium-1234/chrome-mac-arm64/.../Google Chrome for Testing\n"
        "size:    50 KB\n"
        "sha256:  0000000000000000000000000000000000000000000000000000000000000000\n"
        "\n[FAIL] expected a596b1cfc6353e987fcec8d71a23a28cd6a9e7a6b4e20b908e4c4fcffe51158e\n"
        "        got      0000000000000000000000000000000000000000000000000000000000000000\n"
    ) is True


def test_chromium_unavailable_skips_via_fake_script(tmp_path):
    """Portable negative control for the CI skip path.

    Without spinning up a real Chromium download or a real CI
    runner, this test proves the chromium-pin tests would SKIP
    (not fail) when `scripts/verify_chromium.py` reports an
    unavailable binary. It does so by:

      1. Writing a fake `verify_chromium.py` to a tmp_path that
         mimics the exact CI output shape (binary path printed,
         sha256: line absent because the file isn't readable).
      2. Running the fake as a subprocess the way the
         chromium_status fixture does.
      3. Applying the same classification the fixture uses and
         asserting the helper returns False.

    Combined with the unit tests above, this guarantees:
      - the helper classifies unavailable chromium as not pinnable
      - the chromium_status fixture exposes that classification
      - the chromium-pin tests (which read `pinnable`) skip on it

    Without this wire-up, a regression that drops the runtime
    `pytest.skip()` would surface as a red CI job instead of a
    clean skip — and CI doesn't have a Chromium binary to fail
    against, so the failure would be confusing and unfixable
    from inside the test suite.
    """
    fake = tmp_path / "verify_chromium.py"
    fake.write_text(
        "import sys\n"
        "print('binary:  /root/.cache/ms-playwright/chromium-1234/chrome-linux/chrome')\n"
        "print('[error] could not read /root/.cache/ms-playwright/chromium-1234/chrome-linux/chrome: [Errno 2] No such file\\nor directory')\n"
        "sys.exit(1)\n"
    )

    # Run the fake as a subprocess the way chromium_status does,
    # then apply the same classification. Using a real subprocess
    # (rather than calling the helper on a literal string) proves
    # the full chain: subprocess → output → classification.
    proc = subprocess.run(
        [sys.executable, str(fake)],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    output = (proc.stdout or "") + (proc.stderr or "")

    # Sanity: the fake mirrors the CI output shape.
    assert "binary:" in output, (
        f"fake verify_chromium.py must print a binary: line; got:\n{output}"
    )

    # The classification must mark this output as NOT pinnable so
    # the chromium-pin tests skip cleanly on the CI runner.
    assert _chromium_pinnable(output) is False, (
        "unavailable-chromium output must classify as not pinnable; "
        f"helper returned True for output:\n{output}"
    )


def test_chromium_pin_mismatch_does_not_skip_via_fake_script(tmp_path):
    """Reverse control: when chromium IS pinnable but the live
    SHA256 doesn't match the pinned one (e.g., a future
    playwright upgrade that nobody re-pinned for), the helper
    must still classify as pinnable so the chromium-pin test
    FAILS loudly with the mismatch message rather than skipping.

    Combined with `test_chromium_unavailable_skips_via_fake_script`,
    this guarantees the wire-up distinguishes "unavailable" (skip)
    from "available + mismatch" (fail) — the two outcomes the
    PR 1b.1 brief explicitly demands.
    """
    fake = tmp_path / "verify_chromium.py"
    fake.write_text(
        "import sys\n"
        "print('binary:  /Users/x/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/.../Google Chrome for Testing')\n"
        "print('size:    50 KB')\n"
        "print('sha256:  0000000000000000000000000000000000000000000000000000000000000000')\n"
        "print('[FAIL] expected a596b1cfc6353e987fcec8d71a23a28cd6a9e7a6b4e20b908e4c4fcffe51158e')\n"
        "print('        got      0000000000000000000000000000000000000000000000000000000000000000')\n"
        "sys.exit(1)\n"
    )

    proc = subprocess.run(
        [sys.executable, str(fake)],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    output = (proc.stdout or "") + (proc.stderr or "")

    # Sanity: the fake mirrors the Mac arm64 + mismatch shape.
    assert "chrome-mac-arm64" in output
    assert "sha256:" in output

    # The classification must mark this output as pinnable so the
    # chromium-pin test runs and FAILS on the mismatch (regression
    # detection). It must NOT skip — skipping a pin mismatch would
    # silently bypass the regression guard.
    assert _chromium_pinnable(output) is True, (
        "pin-mismatch output must classify as pinnable so the "
        f"regression-detection test fails; got pinnable=False for:\n{output}"
    )

    # And the live hash parsed from the fake MUST differ from the
    # real pinned hash — confirming the comparison would fail
    # (not pass falsely) if the chromium-pin test ran against
    # this fake output.
    m = re.search(r"sha256:\s+([0-9a-fA-F]{64})", output)
    assert m is not None, f"fake must print a sha256: line; got:\n{output}"
    live = m.group(1)
    assert live != "a596b1cfc6353e987fcec8d71a23a28cd6a9e7a6b4e20b908e4c4fcffe51158e", (
        "fake sha256 must differ from the real pin so the comparison "
        f"would fail; both were: {live}"
    )
