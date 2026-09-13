"""G4 parity Makefile Slice A — strict-TDD hermetic tests.

Validates the Slice A contract: ``.PHONY`` declaration, defaults, and
parse-time fail-closed gates for PARITY_URL, PARITY_OUT, PARITY_MANIFEST.
Recipes, preflight, and composition land in Slice B / Slice C.

Hermetic: tests use ``make -n`` (recipes printed, not executed). No real
producer, network call, or fixture is invoked.
"""
from __future__ import annotations

import os, subprocess
from pathlib import Path
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
PY_CAPTURE = "scripts/capture_parity_reports.py"
PY_A11Y = "scripts/capture_a11y_report.py"
NODE_CAPTURE = "tools/g4-capture/scripts/capture.mjs"
BASE_VARS = (
    "PARITY_URL=http://127.0.0.1:8765/index.html",
    "PARITY_OUT=parity-reports/2026-09-12",
    "PARITY_MANIFEST=tests/fixtures/g4/corpus/manifest.json",
)


def _make(args, *, env=None, cwd=None):
    """Invoke ``make`` against the repo's Makefile via its absolute path
    so the recipe's ``command -v ...`` checks see exactly the supplied PATH.
    """
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        ["/usr/bin/make", "-f", str(MAKEFILE), *args],
        capture_output=True, text=True,
        env=merged_env, cwd=cwd or REPO_ROOT,
    )


# ── Sanity ─────────────────────────────────────────────────────────────

def test_parity_target_is_declared_phony():
    """parity must be in .PHONY: so ``make parity`` always runs."""
    text = MAKEFILE.read_text()
    phony = [l for l in text.splitlines() if l.strip().startswith(".PHONY:")]
    assert phony, "Makefile has no .PHONY declaration"
    assert "parity" in " ".join(phony).split(), (
        f"parity must be in .PHONY:; got {phony!r}"
    )


# ── Required-variable fail-closed ordering ─────────────────────────────

@pytest.mark.parametrize("omit,expect_named", [
    ("PARITY_URL", "PARITY_URL"),
    ("PARITY_OUT", "PARITY_OUT"),
    ("PARITY_MANIFEST", "PARITY_MANIFEST"),
])
def test_parity_target_fails_closed_when_required_var_missing(omit, expect_named):
    """Each required variable must fail-closed at Make parse-time BEFORE
    any recipe line prints — Make aborts on ``$(error ...)`` without
    entering the recipe. The error message must name the missing variable.

    Producer-script path strings must never appear in combined output: a
    parse-time abort must not let any recipe line print, even a future
    Slice B / Slice C recipe that mentions those scripts. This guards the
    fail-closed invariant against future recipe additions.
    """
    kept = [v for v in BASE_VARS if not v.startswith(omit + "=")]
    r = _make(["-n", "parity", *kept])
    assert r.returncode != 0, (
        f"make -n parity must exit non-zero without {omit}; "
        f"got rc={r.returncode}, stderr={r.stderr!r}"
    )
    combined = r.stdout + r.stderr
    assert expect_named in combined, (
        f"error must name {expect_named!r}; got combined={combined!r}"
    )
    for needle in (PY_CAPTURE, PY_A11Y, NODE_CAPTURE):
        assert needle not in combined, (
            f"fail-closed violation: {needle!r} must NOT appear when "
            f"{omit} is missing; got combined={combined!r}"
        )
