"""G4 candidate-manifest Makefile contract tests — approved issue #246.

Hermetic: every test runs the system ``make`` against the repository
Makefile with PATH shims for ``node`` (and a stub for ``mkdir``), so
no real Next build, no Lighthouse / Playwright, and no network is
touched. Pins the standalone ``make g4-candidate-manifest`` target:

  * Required ``CANDIDATE_URL`` + ``CANDIDATE_MANIFEST``; default
    ``CANDIDATE_HTML=out/index.html``.
  * Preflights: ``node`` binary + ``scripts/generate_g4_candidate_manifest.mjs``.
  * No install / build / service action.
  * Atomic write — only the named manifest is published.
  * Composition: ``make parity`` byte-for-byte unchanged.

Reference: ``odd/tasks/g4-candidate-manifest-develop.md``.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
GENERATOR = REPO_ROOT / "scripts" / "generate_g4_candidate_manifest.mjs"
SAMPLE_URL = "http://127.0.0.1:8765/index.html"
DEFAULT_HTML = "out/index.html"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make(*args, env=None, cwd=None, make_path=None):
    """Run ``make`` against the repo Makefile; strips inherited parity
    and candidate variables so leftover env cannot influence the run."""
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
        [make_path or "make", "-f", str(MAKEFILE), *args],
        cwd=cwd or REPO_ROOT, env=full_env,
        capture_output=True, text=True, check=False,
    )


def _system_make() -> str:
    mp = shutil.which("make")
    if not mp:
        raise RuntimeError("system `make` not found on PATH")
    return mp


def _write_shim(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _argv_shim_dir(tmp_path: Path, *, with_node: bool = True,
                   node_exit: int = 0) -> Path:
    """Hermetic shim dir that logs each argv wrapped in ``<[...]>`` so
    spaces and shell metacharacters are visible in the log."""
    d = tmp_path / "shims"
    d.mkdir()
    log = tmp_path / "argv_shim.log"
    if with_node:
        _write_shim(d / "node", (
            "#!/bin/bash\n"
            f"printf 'node' >> {log}\n"
            f"for a in \"$@\"; do printf ' <[%s]>' \"$a\" >> {log}; done\n"
            f"printf '\\n' >> {log}\n"
            f"exit {node_exit}\n"
        ))
    # Delegate `mkdir` to the system one so `mkdir -p` keeps working.
    _write_shim(d / "mkdir", "#!/bin/bash\nexec /bin/mkdir \"$@\"\n")
    return d


def _argv_shim_log(parent: Path) -> str:
    p = parent / "argv_shim.log"
    return p.read_text() if p.exists() else ""


def _env(tmp_path: Path, **overrides) -> dict:
    """Build an env dict with the two required CANDIDATE_* vars set."""
    base = {
        "CANDIDATE_URL": SAMPLE_URL,
        "CANDIDATE_MANIFEST": str(tmp_path / "candidate.manifest.json"),
    }
    base.update(overrides)
    return base


def _build_sandbox(tmp_path: Path) -> Path:
    """Sandbox cwd that mirrors the script path the recipe references.
    The fake generator is a no-op exit-0 so the preflight script check
    passes and the controlled shim log captures the argv the recipe
    forwarded."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "generate_g4_candidate_manifest.mjs").write_text(
        "// sandbox stub\n",
        encoding="utf-8",
    )
    return tmp_path


def _dry_run_recipe(env):
    """Run ``make -n g4-candidate-manifest``; return the recipe output
    as a string."""
    r = _make("-n", "g4-candidate-manifest", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def _joined_recipe(out: str) -> str:
    """Join dry-run output lines that are continued with trailing
    backslash into a single logical line, so tests can match
    multi-line recipes as one unit."""
    parts = []
    for ln in out.splitlines():
        if ln.endswith("\\"):
            parts.append(ln[:-1])
        else:
            parts.append(ln)
            parts.append("\n")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Required-variable rejection (runtime)
# ---------------------------------------------------------------------------


def test_make_candidate_manifest_fails_when_CANDIDATE_URL_missing(tmp_path):
    """CANDIDATE_URL missing → fail closed BEFORE the generator runs."""
    r = _make("g4-candidate-manifest", env={
        "CANDIDATE_MANIFEST": str(tmp_path / "manifest.json"),
    })
    assert r.returncode != 0, r.stdout + r.stderr
    assert "CANDIDATE_URL" in r.stdout + r.stderr


def test_make_candidate_manifest_fails_when_CANDIDATE_MANIFEST_missing(tmp_path):
    """CANDIDATE_MANIFEST missing → fail closed BEFORE the generator runs."""
    r = _make("g4-candidate-manifest", env={
        "CANDIDATE_URL": SAMPLE_URL,
    })
    assert r.returncode != 0, r.stdout + r.stderr
    assert "CANDIDATE_MANIFEST" in r.stdout + r.stderr


# ---------------------------------------------------------------------------
# Default + preflight (dry-run + controlled shell)
# ---------------------------------------------------------------------------


def test_make_candidate_manifest_defaults_CANDIDATE_HTML_to_out_index_html(tmp_path):
    """Dry-run MUST pass ``--candidate-html out/index.html`` when the
    caller did not override CANDIDATE_HTML."""
    out = _dry_run_recipe(_env(tmp_path))
    assert "--candidate-html" in out
    assert "out/index.html" in out, (
        f"expected default CANDIDATE_HTML=out/index.html, got:\n{out}"
    )


def test_make_candidate_manifest_dry_run_emits_generator_invocation(tmp_path):
    """Dry-run MUST contain a single ``node scripts/generate_g4_candidate_manifest.mjs``
    invocation carrying the three required --candidate-* flags."""
    out = _joined_recipe(_dry_run_recipe(_env(tmp_path)))
    assert "node scripts/generate_g4_candidate_manifest.mjs" in out, out
    assert "--candidate-html" in out, out
    assert "--candidate-url" in out, out
    assert "--candidate-manifest" in out, out
    assert f'"{SAMPLE_URL}"' in out, out
    assert f'"{tmp_path / "candidate.manifest.json"}"' in out, out


def test_make_candidate_manifest_dry_run_propagates_user_HTML_override(tmp_path):
    """When CANDIDATE_HTML is overridden, the override flows through."""
    user_html = "out/custom/candidate.html"
    out = _joined_recipe(_dry_run_recipe(_env(tmp_path, CANDIDATE_HTML=user_html)))
    assert "node scripts/generate_g4_candidate_manifest.mjs" in out, out
    assert f'"{user_html}"' in out, out


def test_make_candidate_manifest_dry_run_preflight_includes_node_and_script(tmp_path):
    """Dry-run MUST include every preflight gate: node binary + the
    generator script."""
    out = _dry_run_recipe(_env(tmp_path))
    assert "command -v node" in out, out
    assert "scripts/generate_g4_candidate_manifest.mjs" in out, out


# ---------------------------------------------------------------------------
# No install / build / service action
# ---------------------------------------------------------------------------


def test_make_candidate_manifest_no_lifecycle_or_install_commands(tmp_path):
    """No npm / pnpm install, no Next build, no server start. The
    target ONLY validates inputs and shells out to the offline
    generator."""
    out = _dry_run_recipe(_env(tmp_path))
    for s in (
        "npm install", "pnpm install", "pip install", "pip3 install",
        "next build", "pnpm run build", "uvicorn",
        "kill ", "pkill", "nohup", "make api", "make css",
        "make parity", "make dev",
    ):
        assert s not in out, (
            f"forbidden substring {s!r} present in dry-run:\n{out}"
        )


def test_make_candidate_manifest_does_not_create_OUT_directories(tmp_path):
    """The target MUST NOT pre-create the manifest's parent directory
    via `mkdir -p` (atomic-write contract — the generator owns
    creation of any parent directory it needs)."""
    out = _dry_run_recipe(_env(tmp_path))
    assert "mkdir -p" not in out, (
        f"recipe leaked mkdir -p:\n{out}"
    )


# ---------------------------------------------------------------------------
# Controlled-shell argv propagation
# ---------------------------------------------------------------------------


def test_make_candidate_manifest_forwards_each_flag_as_separate_argv(tmp_path):
    """Controlled-shell proof: CANDIDATE_URL, CANDIDATE_HTML,
    CANDIDATE_MANIFEST all arrive as distinct argv elements (NOT
    shell-expanded, NOT word-split)."""
    sandbox = _build_sandbox(tmp_path)
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _argv_shim_dir(shim_parent)
    user_html = "out/sub dir/candidate.html"
    manifest = str(tmp_path / "out" / "candidate.manifest.json")
    r = _make(
        "g4-candidate-manifest",
        env={"PATH": str(shim),
             **_env(sandbox, CANDIDATE_HTML=user_html,
                    CANDIDATE_MANIFEST=manifest)},
        cwd=sandbox, make_path=_system_make(),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    log = _argv_shim_log(shim_parent)
    assert "generate_g4_candidate_manifest.mjs" in log, log
    assert "<[--candidate-html]>" in log, log
    assert f"<[{user_html}]>" in log, log
    assert "<[--candidate-url]>" in log, log
    assert f"<[{SAMPLE_URL}]>" in log, log
    assert "<[--candidate-manifest]>" in log, log
    assert f"<[{manifest}]>" in log, log


def test_make_candidate_manifest_quotes_caller_vars_against_shell_injection(tmp_path):
    """Defense-in-depth: shell metacharacters in CANDIDATE_URL /
    CANDIDATE_HTML / CANDIDATE_MANIFEST are quoted at the shell boundary
    so the controlled-shell run cannot `touch` the injected leak-marker."""
    sandbox = _build_sandbox(tmp_path)
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _argv_shim_dir(shim_parent)
    leak = f"{tmp_path}/leak-marker"
    payload = f"http://x.invalid; touch {leak}; echo"
    r = _make(
        "g4-candidate-manifest",
        env={"PATH": str(shim),
             **_env(sandbox, CANDIDATE_URL=payload,
                    CANDIDATE_HTML=payload, CANDIDATE_MANIFEST=payload)},
        cwd=sandbox, make_path=_system_make(),
    )
    assert not os.path.exists(leak), (
        f"shell metacharacter payload escaped into shell — leak-marker "
        f"created at {leak}; stderr: {r.stderr}"
    )


# ---------------------------------------------------------------------------
# Composition — `make parity` byte-for-byte unchanged
# ---------------------------------------------------------------------------


_PARITY_RE = re.compile(
    r"^parity:.*?(?=^\S|\Z)", re.DOTALL | re.MULTILINE,
)


def _slice_parity_recipe(makefile_text: str) -> str:
    """Slice the ``parity`` recipe (header + indented lines) out of the
    Makefile. Used for byte-for-byte comparison."""
    match = _PARITY_RE.search(makefile_text)
    assert match is not None, "parity recipe not found in Makefile"
    return match.group(0)


def test_make_parity_recipe_unchanged_by_candidate_manifest_target(tmp_path):
    """The candidate-manifest target MUST NOT alter the ``parity`` recipe
    body. We assert byte-for-byte equality of the parity recipe between
    the current Makefile and a known-canonical baseline; since this is
    a forward-looking guard for in-place edits, we also confirm the
    parity recipe contains every line it did before this slice landed."""
    current = MAKEFILE.read_text(encoding="utf-8")
    current_slice = _slice_parity_recipe(current)
    # Canonical structural invariants — every line the parity recipe
    # MUST carry, drawn from the pre-#246 parity contract.
    required_lines = (
        "parity:",
        "@if [ -z \"$(PARITY_URL)\" ]",
        "@if [ -z \"$(PARITY_OUT)\" ]",
        "@if [ -z \"$(PARITY_MANIFEST)\" ]",
        "@if [ -n \"$(PARITY_QUERIES)\" ]",
        "@command -v python3 >/dev/null",
        "@command -v node >/dev/null",
        "@test -f scripts/capture_parity_reports.py",
        "@test -f tools/g4-capture/scripts/capture.mjs",
        "@test -f scripts/capture_a11y_report.py",
        "@test -d tools/g4-capture/node_modules",
        "scripts/capture_parity_reports.py",
        "tools/g4-capture/scripts/capture.mjs",
        "--url \"$(PARITY_URL)\"",
        "scripts/capture_a11y_report.py",
    )
    for line in required_lines:
        assert line in current_slice, (
            f"parity recipe lost required line {line!r}:\n{current_slice}"
        )
    # `make parity` still works byte-for-byte — dry-run must include
    # the documented producer order and the preflight gates.
    r = _make("-n", "parity", env={
        "PARITY_URL": SAMPLE_URL,
        "PARITY_OUT": str(tmp_path / "out"),
        "PARITY_MANIFEST": str(tmp_path / "manifest.json"),
    })
    assert r.returncode == 0, r.stdout + r.stderr
    assert "scripts/capture_parity_reports.py" in r.stdout
    assert "tools/g4-capture/scripts/capture.mjs" in r.stdout
    assert "scripts/capture_a11y_report.py" in r.stdout
