"""G4 parity Makefile Slice A + Slice B — strict-TDD hermetic tests.

Slice A — parse-time contract: ``.PHONY`` declaration, defaults, and
parse-time fail-closed gates for PARITY_URL, PARITY_OUT, PARITY_MANIFEST.

Slice B — recipe preflight (python3 + node on PATH; the three Slice C
producer scripts present) and output-directory creation. Slice B does
NOT invoke any producer and does NOT consume PARITY_QUERIES (those land
in Slice C).

Hermetic: tests use ``make -n`` for static inspection and execute the
recipe only with isolated PATH / tmp_path to keep failure-path assertions
free of network calls, real captures, or repo mutation.
"""
from __future__ import annotations

import os, shutil, subprocess
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


# ── Slice B: recipe preflight (python3 + node + three producer scripts) ──
#
# These tests inspect the recipe body printed by ``make -n parity`` so the
# preflight contract stays purely textual: presence of ``command -v`` for
# python3 + node, ``test -f`` presence checks for each producer script, and
# ``mkdir -p $(PARITY_OUT)``. They do NOT execute the recipe, so the
# preflight ordering and the Slice C guard are observable without touching
# the host toolchain.


def _recipe_lines(*, extra_vars=()):
    """Return the recipe body printed by ``make -n parity`` (one line per
    shell command, leading tab stripped, blank lines dropped).

    BASE_VARS must satisfy the Slice A parse-time gates. ``extra_vars`` lets
    callers layer optional settings (e.g. PARITY_QUERIES) without losing
    BASE_VARS.
    """
    r = _make(["-n", "parity", *BASE_VARS, *extra_vars])
    assert r.returncode == 0, (
        f"make -n parity should succeed with BASE_VARS; "
        f"rc={r.returncode}, stderr={r.stderr!r}"
    )
    out = []
    for ln in r.stdout.splitlines():
        stripped = ln.lstrip("\t")
        if stripped.strip():
            out.append(stripped)
    return out


def test_parity_recipe_preflight_checks_python3():
    """Recipe must verify python3 is on PATH (Slice B preflight)."""
    lines = _recipe_lines()
    matches = [ln for ln in lines if "command -v python3" in ln]
    assert matches, (
        f"recipe must contain `command -v python3` preflight; got lines={lines!r}"
    )


def test_parity_recipe_preflight_checks_node():
    """Recipe must verify node is on PATH (Slice B preflight)."""
    lines = _recipe_lines()
    matches = [ln for ln in lines if "command -v node" in ln]
    assert matches, (
        f"recipe must contain `command -v node` preflight; got lines={lines!r}"
    )


@pytest.mark.parametrize("script_path", [
    "scripts/capture_parity_reports.py",
    "scripts/capture_a11y_report.py",
    "tools/g4-capture/scripts/capture.mjs",
])
def test_parity_recipe_preflight_checks_producer_script(script_path):
    """Each Slice C producer script must be gated by a ``test -f`` presence
    check. This is a presence check, NOT an invocation — Slice B does not
    run the producers.
    """
    lines = _recipe_lines()
    matches = [ln for ln in lines if script_path in ln]
    assert matches, (
        f"recipe must contain a presence check for {script_path!r}; "
        f"got lines={lines!r}"
    )
    for ln in matches:
        assert ln.lstrip().startswith("test -f "), (
            f"each mention of {script_path!r} must be a `test -f` presence "
            f"check, not an invocation; got non-presence-check line {ln!r}"
        )


def test_parity_recipe_creates_output_dir():
    """Recipe must `mkdir -p $(PARITY_OUT)` so Slice C can publish into it.

    ``make -n`` expands ``$(PARITY_OUT)`` in the printed recipe, so we pass a
    unique value via ``extra_vars`` and assert the expanded form is present.
    """
    unique_out = "parity-reports/__test-mkdir-marker__"
    lines = _recipe_lines(extra_vars=(f"PARITY_OUT={unique_out}",))
    matches = [
        ln for ln in lines
        if "mkdir -p" in ln and unique_out in ln
    ]
    assert matches, (
        f"recipe must contain `mkdir -p $(PARITY_OUT)` (expanded to "
        f"{unique_out!r}); got lines={lines!r}"
    )


# ── Slice C guard: producer invocations + PARITY_QUERIES stay out of Slice B ──


@pytest.mark.parametrize("script_path,interpreter", [
    ("scripts/capture_parity_reports.py", "python3"),
    ("scripts/capture_a11y_report.py", "python3"),
    ("tools/g4-capture/scripts/capture.mjs", "node"),
])
def test_parity_recipe_does_not_invoke_producer(script_path, interpreter):
    """Slice B must NOT invoke any producer script — each producer path may
    appear ONLY in a ``test -f <path>`` presence check line. Any line that
    names both the interpreter AND the producer script as arguments is a
    Slice C invocation and must not exist yet.
    """
    lines = _recipe_lines()
    invocations = [
        ln for ln in lines
        if interpreter in ln and script_path in ln
        and not ln.lstrip().startswith("test -f ")
    ]
    assert not invocations, (
        f"Slice C guard: recipe must NOT invoke `{interpreter} {script_path}`; "
        f"got invocations={invocations!r}, full lines={lines!r}"
    )


def test_parity_recipe_does_not_propagate_queries():
    """PARITY_QUERIES is Slice C territory. Slice B must not reference it in
    any recipe line — neither the ``$(PARITY_QUERIES)`` form nor the
    ``--queries`` flag may appear.
    """
    r = _make([
        "-n", "parity",
        *BASE_VARS,
        "PARITY_QUERIES=tests/fixtures/g4/corpus/queries.json",
    ])
    assert r.returncode == 0, (
        f"setup: make -n parity with PARITY_QUERIES must succeed (Slice B does "
        f"not require it); rc={r.returncode}, stderr={r.stderr!r}"
    )
    combined = r.stdout + r.stderr
    assert "PARITY_QUERIES" not in combined, (
        f"Slice C guard: recipe must NOT reference PARITY_QUERIES in Slice B; "
        f"got combined={combined!r}"
    )
    assert "--queries" not in combined, (
        f"Slice C guard: recipe must NOT pass --queries in Slice B; "
        f"got combined={combined!r}"
    )


# ── Hermetic runtime: preflight fail-closed + happy-path mkdir ────────────
#
# These tests actually invoke ``make parity`` (no ``-n``). The preflight is
# expected to either abort on a missing tool or, on the happy path, create
# the output directory and exit 0. They use isolated PATH / tmp_path so the
# host repo and the host toolchain stay untouched.


def test_parity_preflight_fails_closed_when_python3_missing(tmp_path):
    """With an empty PATH, ``make parity`` must abort on the python3 check
    and stderr must name python3. mkdir and any later preflight must NOT
    run (the directory must NOT exist after the failed run).
    """
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    out = tmp_path / "out"
    r = _make(
        ["parity", *BASE_VARS, f"PARITY_OUT={out}"],
        env={"PATH": str(empty_bin)},
    )
    assert r.returncode != 0, (
        f"make parity must fail when python3 is missing from PATH; "
        f"got rc={r.returncode}, stdout={r.stdout!r}, stderr={r.stderr!r}"
    )
    assert "python3" in r.stderr, (
        f"preflight failure must mention python3; got stderr={r.stderr!r}"
    )
    assert not out.exists(), (
        f"preflight must abort BEFORE mkdir; {out} must not exist after "
        f"a python3-missing run"
    )


def test_parity_preflight_fails_closed_when_node_missing(tmp_path):
    """With python3 present but node missing, ``make parity`` must abort on
    the node check and stderr must name node. The python3 check (which runs
    first) must have passed — i.e. stderr must NOT mention python3 as the
    failure cause.
    """
    bin_with_python = tmp_path / "bin-with-python"
    bin_with_python.mkdir()
    real_python = shutil.which("python3")
    if not real_python:
        pytest.skip("python3 not available on PATH")
    try:
        (bin_with_python / "python3").symlink_to(real_python)
    except OSError as exc:
        pytest.skip(f"cannot symlink python3 from {real_python}: {exc}")
    out = tmp_path / "out"
    r = _make(
        ["parity", *BASE_VARS, f"PARITY_OUT={out}"],
        env={"PATH": str(bin_with_python)},
    )
    assert r.returncode != 0, (
        f"make parity must fail when node is missing from PATH; "
        f"got rc={r.returncode}, stdout={r.stdout!r}, stderr={r.stderr!r}"
    )
    assert "node" in r.stderr, (
        f"preflight failure must mention node; got stderr={r.stderr!r}"
    )
    assert "python3 not found" not in r.stderr, (
        f"python3 check must have passed (it runs first); got stderr={r.stderr!r}"
    )
    assert not out.exists(), (
        f"preflight must abort BEFORE mkdir; {out} must not exist after "
        f"a node-missing run"
    )


def test_parity_preflight_succeeds_and_creates_output_dir(tmp_path):
    """Happy path: full preflight passes, mkdir runs, exit 0, PARITY_OUT
    exists. Slice B does not invoke producers, so no producer output files
    are required (and none should appear).
    """
    if not shutil.which("python3"):
        pytest.skip("python3 not available on PATH")
    if not shutil.which("node"):
        pytest.skip("node not available on PATH")
    out = tmp_path / "parity-out"
    r = _make(["parity", *BASE_VARS, f"PARITY_OUT={out}"])
    assert r.returncode == 0, (
        f"make parity should succeed when preflight passes and PARITY_OUT is "
        f"a fresh directory; got rc={r.returncode}, "
        f"stdout={r.stdout!r}, stderr={r.stderr!r}"
    )
    assert out.is_dir(), (
        f"Slice B must `mkdir -p $(PARITY_OUT)`; expected {out} to exist as "
        f"a directory after `make parity`"
    )
