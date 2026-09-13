"""G4 parity Makefile Slice A + Slice B + Slice C — strict-TDD hermetic tests.

Slice A: parse-time contract (.PHONY, defaults, required-variable gates).
Slice B: recipe preflight (python3 + node + 3 producer scripts; mkdir).
Slice C: producer composition (Python capture → Node Lighthouse capture →
Python a11y adapter), safe optional PARITY_QUERIES via $(if ...), and
producer-failure atomicity (every producer invocation guarded by
``|| { ...; exit 1; }`` so a non-zero exit aborts before the next producer).

Hermetic: ``make -n`` for static inspection; runtime tests use isolated
PATH / tmp_path or a fake-repo shim with deterministic exit codes so no
network, Playwright, or Lighthouse launches happen.
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
# preflight ordering and the Slice C composition are observable without
# touching the host toolchain.


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
    check. The script path may ALSO appear in a Slice C invocation line,
    but AT LEAST ONE mention of each path must be a ``test -f`` line so
    the Slice B preflight contract (no invocation before presence-checked)
    is preserved.
    """
    lines = _recipe_lines()
    matches = [ln for ln in lines if script_path in ln]
    assert matches, (
        f"recipe must contain a presence check for {script_path!r}; "
        f"got lines={lines!r}"
    )
    presence_checks = [
        ln for ln in matches if ln.lstrip().startswith("test -f ")
    ]
    assert presence_checks, (
        f"recipe must contain a `test -f` presence check for {script_path!r}; "
        f"got matches={matches!r}"
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


# ── Slice C: producer composition (Python capture → Node Lighthouse → a11y adapter) ──
#
# The recipe must invoke the three producer scripts in the documented
# composition order, each with the right interpreter + flag surface.
# Inspect the recipe printed by ``make -n parity`` so the contract stays
# purely textual and observable without running the producers.


def test_parity_recipe_invokes_python_capture_first():
    """Python capture runs first with --url/--out-dir pointing at BASE_VARS values."""
    lines = _recipe_lines()
    invocations = [
        ln for ln in lines
        if "python3" in ln and "scripts/capture_parity_reports.py" in ln
        and not ln.lstrip().startswith("test -f ")
    ]
    assert invocations, f"recipe must invoke capture_parity_reports.py; got lines={lines!r}"
    line = invocations[0]
    for expected in ("http://127.0.0.1:8765/index.html", "parity-reports/2026-09-12"):
        assert expected in line, f"Python capture must reference {expected!r}; got {line!r}"
    assert "--url" in line and "--out-dir" in line, (
        f"Python capture must pass --url and --out-dir; got {line!r}"
    )


def test_parity_recipe_invokes_node_capture_second():
    """Node Lighthouse capture runs second with --url/--manifest/--out."""
    lines = _recipe_lines()
    invocations = [
        ln for ln in lines
        if "node" in ln and "tools/g4-capture/scripts/capture.mjs" in ln
        and not ln.lstrip().startswith("test -f ")
    ]
    assert invocations, f"recipe must invoke capture.mjs; got lines={lines!r}"
    line = invocations[0]
    for expected in (
        "http://127.0.0.1:8765/index.html",
        "parity-reports/2026-09-12",
        "tests/fixtures/g4/corpus/manifest.json",
    ):
        assert expected in line, f"Node capture must reference {expected!r}; got {line!r}"
    for flag in ("--url", "--manifest", "--out"):
        assert flag in line, f"Node capture must pass {flag}; got {line!r}"


def test_parity_recipe_invokes_a11y_adapter_third():
    """a11y adapter runs third, reading $(PARITY_OUT)/evidence.json."""
    lines = _recipe_lines()
    invocations = [
        ln for ln in lines
        if "python3" in ln and "scripts/capture_a11y_report.py" in ln
        and not ln.lstrip().startswith("test -f ")
    ]
    assert invocations, f"recipe must invoke capture_a11y_report.py; got lines={lines!r}"
    line = invocations[0]
    assert "parity-reports/2026-09-12/evidence.json" in line, (
        f"a11y must read evidence.json from $(PARITY_OUT); got {line!r}"
    )
    assert "--evidence" in line and "--out-dir" in line, (
        f"a11y must pass --evidence and --out-dir; got {line!r}"
    )


def test_parity_recipe_composition_order():
    """Invocations must be ordered Python capture → Node capture → a11y adapter."""
    lines = _recipe_lines()
    def first_idx(predicate):
        for i, ln in enumerate(lines):
            if predicate(ln):
                return i
        return -1
    py_idx = first_idx(lambda ln: "scripts/capture_parity_reports.py" in ln
                       and not ln.lstrip().startswith("test -f "))
    node_idx = first_idx(lambda ln: "tools/g4-capture/scripts/capture.mjs" in ln
                         and not ln.lstrip().startswith("test -f "))
    a11y_idx = first_idx(lambda ln: "scripts/capture_a11y_report.py" in ln
                         and not ln.lstrip().startswith("test -f "))
    assert py_idx >= 0 and node_idx >= 0 and a11y_idx >= 0, (
        f"all three producer invocations must exist; lines={lines!r}"
    )
    assert py_idx < node_idx < a11y_idx, (
        f"invocations must be in order Python → Node → a11y; "
        f"got py={py_idx}, node={node_idx}, a11y={a11y_idx}; lines={lines!r}"
    )


# ── Slice C: producer-failure atomicity (textual fail-closed guards) ─────


@pytest.mark.parametrize("script_path,interpreter", [
    ("scripts/capture_parity_reports.py", "python3"),
    ("tools/g4-capture/scripts/capture.mjs", "node"),
    ("scripts/capture_a11y_report.py", "python3"),
])
def test_parity_recipe_invocation_is_fail_closed(script_path, interpreter):
    """Each producer invocation must be guarded by ``|| { ... >&2; exit 1; }``
    so a non-zero exit aborts before the next producer runs (atomicity)."""
    lines = _recipe_lines()
    invocations = [
        ln for ln in lines
        if interpreter in ln and script_path in ln
        and not ln.lstrip().startswith("test -f ")
    ]
    assert invocations, f"recipe must invoke {interpreter} {script_path}; got lines={lines!r}"
    for ln in invocations:
        assert "||" in ln and "exit 1" in ln, (
            f"producer invocation must be guarded by `|| {{ ...; exit 1; }}`; got {ln!r}"
        )
        assert "echo" in ln and ">&2" in ln, (
            f"producer failure path must echo a diagnostic to stderr; got {ln!r}"
        )


# ── Slice C: safe optional PARITY_QUERIES propagation ─────────────────────


def test_parity_recipe_propagates_queries_when_set():
    """When PARITY_QUERIES is set, the Python capture must pass --queries <value>."""
    qpath = "tests/fixtures/g4/corpus/queries.json"
    lines = _recipe_lines(extra_vars=(f"PARITY_QUERIES={qpath}",))
    invocations = [
        ln for ln in lines
        if "scripts/capture_parity_reports.py" in ln
        and qpath in ln and "--queries" in ln
        and not ln.lstrip().startswith("test -f ")
    ]
    assert invocations, (
        f"recipe must pass --queries $(PARITY_QUERIES)={qpath!r}; got lines={lines!r}"
    )


def test_parity_recipe_omits_queries_flag_when_unset():
    """When PARITY_QUERIES is empty, the Python capture must NOT pass --queries."""
    lines = _recipe_lines()  # BASE_VARS leaves PARITY_QUERIES empty.
    invocations = [
        ln for ln in lines
        if "scripts/capture_parity_reports.py" in ln and "--queries" in ln
        and not ln.lstrip().startswith("test -f ")
    ]
    assert not invocations, (
        f"recipe must NOT pass --queries when PARITY_QUERIES is empty; got {lines!r}"
    )


# ── Hermetic runtime: preflight fail-closed + Slice B mkdir invariant ─────
#
# These tests actually invoke ``make parity`` (no ``-n``). The preflight is
# expected to either abort on a missing tool or, on the happy path, create
# the output directory. They use isolated PATH / tmp_path so the host repo
# and the host toolchain stay untouched.


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


def test_parity_preflight_succeeds_and_mkdir_runs(tmp_path):
    """Slice B invariant: when preflight passes, ``mkdir -p $(PARITY_OUT)``
    runs and PARITY_OUT exists. Slice C adds producer invocations AFTER
    mkdir; this test asserts only the Slice B invariant (the recipe exit
    code may legitimately be non-zero in a hermetic no-server environment
    because the Python capture would try to navigate the URL — that path
    is covered by the Slice C atomicity tests, not here).
    """
    if not shutil.which("python3"):
        pytest.skip("python3 not available on PATH")
    if not shutil.which("node"):
        pytest.skip("node not available on PATH")
    out = tmp_path / "parity-out"
    # We don't assert rc == 0: the recipe's preflight + mkdir runs before
    # any producer, and a subsequent producer may abort the shell. The
    # invariant under test is that mkdir has already executed.
    _make(["parity", *BASE_VARS, f"PARITY_OUT={out}"])
    assert out.is_dir(), (
        f"Slice B must `mkdir -p $(PARITY_OUT)` after preflight passes; "
        f"expected {out} to exist as a directory after `make parity`"
    )


# ── Slice C: producer-failure atomicity (real runtime, fake-repo shim) ────
#
# These tests actually invoke ``make parity`` (no ``-n``) against a fake-repo
# shim: a tmp directory that mirrors the real script layout but replaces ONE
# producer with a deterministic exit-code stub. The preflight ``test -f``
# checks see the stub (passes), but the producer invocation runs the stub.
# Each test forces ONE producer to fail and asserts the recipe aborts before
# the NEXT producer can run. Hermetic: no Playwright, no Lighthouse, no
# network. The real Makefile is exercised against its actual contracts.


def _build_fake_repo(tmp_path, *, fail_python=False, fail_node=False, fail_a11y=False):
    """Mirror the real script layout in tmp_path with deterministic exit-code
    stubs. Returns ``(fake_repo, out_dir)``. The Makefile is copied verbatim
    from REPO_ROOT (not modified); preflight ``test -f`` checks see the
    stubs and pass; the invocation runs the stub with the chosen exit code."""
    for tool in ("python3", "node", "make"):
        if not shutil.which(tool):
            pytest.skip(f"{tool} not available on PATH")
    fake_repo = tmp_path / "fake-repo"
    fake_repo.mkdir()
    shutil.copy(MAKEFILE, fake_repo / "Makefile")
    (fake_repo / "scripts").mkdir()
    (fake_repo / "tools" / "g4-capture" / "scripts").mkdir(parents=True)
    py_rc = 2 if fail_python else 0
    (fake_repo / "scripts" / "capture_parity_reports.py").write_text(
        "#!/usr/bin/env python3\nimport sys\n" f"sys.exit({py_rc})\n"
    )
    a11y_rc = 2 if fail_a11y else 0
    (fake_repo / "scripts" / "capture_a11y_report.py").write_text(
        "#!/usr/bin/env python3\nimport sys, os\n"
        f"open(os.path.join(os.environ.get('PARITY_OUT', '.'), 'a11y.json'), 'w').close()\n"
        f"sys.exit({a11y_rc})\n"
    )
    node_rc = 2 if fail_node else 0
    (fake_repo / "tools" / "g4-capture" / "scripts" / "capture.mjs").write_text(
        "import { writeFileSync } from 'node:fs';\n"
        "import { join } from 'node:path';\n"
        f"writeFileSync(join(process.env.PARITY_OUT || '.', 'evidence.json'), '{{}}');\n"
        f"process.exit({node_rc});\n"
    )
    return fake_repo, tmp_path / "parity-out"


def test_parity_recipe_aborts_when_python_capture_fails(tmp_path):
    """Python capture failure must abort BEFORE Node capture + a11y run."""
    fake_repo, out = _build_fake_repo(tmp_path, fail_python=True)
    r = _make(
        ["-f", str(fake_repo / "Makefile"), "parity",
         *BASE_VARS, f"PARITY_OUT={out}"],
        cwd=fake_repo, env={**os.environ, "PARITY_OUT": str(out)},
    )
    assert r.returncode != 0, f"recipe must abort; got rc={r.returncode}, stderr={r.stderr!r}"
    assert "capture_parity_reports.py" in r.stderr, f"stderr must name producer; got {r.stderr!r}"
    assert not (out / "evidence.json").exists(), "Node capture must NOT run after Python capture failure"
    assert not (out / "a11y.json").exists(), "a11y must NOT run after Python capture failure"


def test_parity_recipe_aborts_when_node_capture_fails(tmp_path):
    """Node capture (MIDDLE) failure must abort BEFORE a11y runs."""
    fake_repo, out = _build_fake_repo(tmp_path, fail_node=True)
    r = _make(
        ["-f", str(fake_repo / "Makefile"), "parity",
         *BASE_VARS, f"PARITY_OUT={out}"],
        cwd=fake_repo, env={**os.environ, "PARITY_OUT": str(out)},
    )
    assert r.returncode != 0, f"recipe must abort; got rc={r.returncode}, stderr={r.stderr!r}"
    assert "capture.mjs" in r.stderr, f"stderr must name Node producer; got {r.stderr!r}"
    assert not (out / "a11y.json").exists(), "a11y must NOT run after Node capture failure"


def test_parity_recipe_aborts_when_a11y_adapter_fails(tmp_path):
    """a11y (LAST) failure must surface as non-zero exit with stderr naming a11y."""
    fake_repo, out = _build_fake_repo(tmp_path, fail_a11y=True)
    r = _make(
        ["-f", str(fake_repo / "Makefile"), "parity",
         *BASE_VARS, f"PARITY_OUT={out}"],
        cwd=fake_repo, env={**os.environ, "PARITY_OUT": str(out)},
    )
    assert r.returncode != 0, f"recipe must abort; got rc={r.returncode}, stderr={r.stderr!r}"
    assert "capture_a11y_report.py" in r.stderr, f"stderr must name a11y; got {r.stderr!r}"


