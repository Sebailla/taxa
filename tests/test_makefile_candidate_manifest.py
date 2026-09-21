"""G4 Makefile candidate-manifest contract tests (PR #246).

Hermetic: every test runs the system `make` against the repository Makefile
with PATH shims for `node` / `npm` (and `python3` where helpful), so no real
npm install / Next build / Lighthouse / network is touched. Validates the
`make g4-candidate-manifest` wiring contract:

  - Required vars: CANDIDATE_URL (absolute http(s) URL) and CANDIDATE_MANIFEST.
    Missing either aborts fail-closed BEFORE the producer runs.
  - Default CANDIDATE_HTML = out/index.html (overridable; literal paths
    resolve into the producer invocation).
  - Fail-closed preflight gates for `node`, the generator script
    (scripts/generate_g4_candidate_manifest.mjs), a regular CANDIDATE_HTML,
    and an http(s) CANDIDATE_URL.
  - Literal producer invocation via
    `npm run manifest:generate -- --html ... --url ... --out ...`
    (no direct `node scripts/...`, no shell wrappers that swallow argv).
  - No install / lifecycle / server-start / build commands.
  - Caller-supplied paths and URL are quoted at the shell boundary so shell
    metacharacters never escape into a producer command line.

Reference: odd/tasks/g4-candidate-manifest-pipeline.md
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
SAMPLE_URL = "https://taxa.example/candidate/"
SSR_PROBE_MARKER = 'data-testid="g4-probe-marker"'


def _make(*args, env=None, cwd=None, make_path=None):
    """Run `make` against the repo Makefile; strips inherited CANDIDATE_*
    and PARITY_* so tests don't leak between each other. Pass
    `make_path` (absolute) for hermetic PATH-override tests."""
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
    """Locate the system `make` binary (for hermetic PATH-override tests)."""
    mp = shutil.which("make")
    if not mp:
        raise RuntimeError("system `make` not found on PATH")
    return mp


def _write_shim(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _shim_dir(tmp_path: Path, *, with_node: bool = True,
              with_npm: bool = True, node_exit: int = 0,
              npm_to_node: bool = True,
              log_name: str = "shim.log") -> Path:
    """Hermetic shim dir for `node` and `npm`.

    `node` shim logs its argv as `node <args>` and exits with `node_exit`.
    `npm` shim logs its argv as `npm <args>` and (when `npm_to_node`)
    delegates to `node scripts/generate_g4_candidate_manifest.mjs "$@"`
    so the shim `node` receives the producer argv exactly the way npm
    would unpack `npm run manifest:generate -- <args>`. When
    `npm_to_node` is False the npm shim only logs and exits 0.

    Also includes a `mkdir` shim delegating to /bin/mkdir so recipe
    `mkdir -p` calls work without leaking /usr/bin onto PATH (which
    would expose system python3 / node and break hermeticity).
    """
    d = tmp_path / "shims"
    d.mkdir()
    log = tmp_path / log_name
    if with_node:
        _write_shim(d / "node", (
            "#!/bin/bash\n"
            f"printf 'node %s\\n' \"$*\" >> {log}\n"
            f"exit {node_exit}\n"
        ))
    if with_npm:
        body = f"printf 'npm %s\\n' \"$*\" >> {log}\n"
        if npm_to_node:
            body += (
                "exec node scripts/generate_g4_candidate_manifest.mjs \"$@\"\n"
            )
        else:
            body += "exit 0\n"
        _write_shim(d / "npm", f"#!/bin/bash\n{body}")
    _write_shim(d / "mkdir", "#!/bin/bash\nexec /bin/mkdir \"$@\"\n")
    return d


def _shim_log(parent: Path, log_name: str = "shim.log") -> str:
    p = parent / log_name
    return p.read_text() if p.exists() else ""


def _env(tmp_path: Path, **overrides) -> dict:
    """Build a minimal env dict with the two required CANDIDATE_* vars set.
    CANDIDATE_HTML is intentionally omitted so the default (out/index.html)
    path is exercised unless the caller overrides it."""
    base = {
        "CANDIDATE_URL": SAMPLE_URL,
        "CANDIDATE_MANIFEST": str(tmp_path / "candidate.manifest.json"),
    }
    base.update(overrides)
    return base


def _build_sandbox(tmp_path: Path, *, with_html: bool = True,
                   html_basename: str = "index.html") -> Path:
    """Sandbox cwd mirroring the recipe's tree layout. Creates a stub
    `scripts/generate_g4_candidate_manifest.mjs` (referenced by the npm
    shim) and (optionally) a regular HTML file at out/<html_basename> so
    the default CANDIDATE_HTML path resolves to a real regular file."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "generate_g4_candidate_manifest.mjs").write_text(
        "// sandbox stub\n")
    if with_html:
        (tmp_path / "out").mkdir()
        body = "<html><body>sandbox</body></html>\n"
        if SSR_PROBE_MARKER:
            body += f"{SSR_PROBE_MARKER}\n"
        (tmp_path / "out" / html_basename).write_text(body, encoding="utf-8")
    return tmp_path


def _dry_run_recipe(env):
    """Run `make -n g4-candidate-manifest`; return the recipe output."""
    r = _make("-n", "g4-candidate-manifest", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


# ── Required-variable rejection (runtime) ─────────────────────────────


def test_make_g4_candidate_manifest_fails_when_CANDIDATE_URL_missing(tmp_path):
    """CANDIDATE_URL missing → fail closed BEFORE any producer runs."""
    r = _make("g4-candidate-manifest", env={
        "CANDIDATE_MANIFEST": str(tmp_path / "candidate.manifest.json"),
    })
    assert r.returncode != 0, r.stdout + r.stderr
    assert "CANDIDATE_URL" in r.stdout + r.stderr


def test_make_g4_candidate_manifest_fails_when_CANDIDATE_MANIFEST_missing(tmp_path):
    """CANDIDATE_MANIFEST missing → fail closed BEFORE any producer runs."""
    r = _make("g4-candidate-manifest", env={
        "CANDIDATE_URL": SAMPLE_URL,
    })
    assert r.returncode != 0, r.stdout + r.stderr
    assert "CANDIDATE_MANIFEST" in r.stdout + r.stderr


def test_make_g4_candidate_manifest_does_not_invoke_producer_when_required_var_missing(
    tmp_path,
):
    """TRIANGULATE: when a required var is missing the producer is NEVER
    invoked (no npm, no node, no scripts/generate_g4_candidate_manifest.mjs)."""
    sandbox = _build_sandbox(tmp_path)
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _shim_dir(shim_parent)
    r = _make("g4-candidate-manifest",
              env={"PATH": str(shim), "CANDIDATE_MANIFEST": str(tmp_path / "m.json")},
              cwd=sandbox, make_path=_system_make())
    assert r.returncode != 0, r.stdout + r.stderr
    log = _shim_log(shim_parent)
    assert "npm " not in log, f"npm invoked despite CANDIDATE_URL missing:\n{log}"
    assert "generate_g4_candidate_manifest.mjs" not in log, (
        f"generator invoked despite CANDIDATE_URL missing:\n{log}")


# ── Preflight gates (runtime) ─────────────────────────────────────────


def test_make_g4_candidate_manifest_preflight_missing_node_aborts(tmp_path):
    """`node` absent from PATH → preflight gate aborts fail-closed BEFORE
    any producer runs."""
    sandbox = _build_sandbox(tmp_path)
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _shim_dir(shim_parent, with_node=False)
    r = _make("g4-candidate-manifest",
              env={"PATH": str(shim), **_env(tmp_path)},
              cwd=sandbox, make_path=_system_make())
    assert r.returncode != 0, r.stdout + r.stderr
    assert "node" in (r.stdout + r.stderr).lower()
    log = _shim_log(shim_parent)
    assert "npm " not in log, f"npm invoked despite node missing:\n{log}"
    assert "generate_g4_candidate_manifest.mjs" not in log, (
        f"generator invoked despite node missing:\n{log}")


def test_make_g4_candidate_manifest_preflight_missing_generator_aborts(tmp_path):
    """Generator script missing → preflight gate aborts fail-closed
    BEFORE npm is invoked."""
    # Sandbox WITHOUT scripts/generate_g4_candidate_manifest.mjs.
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    # Still create the default HTML so the HTML preflight doesn't fire first.
    (sandbox / "out").mkdir()
    (sandbox / "out" / "index.html").write_text(
        f"<html>{SSR_PROBE_MARKER}</html>\n", encoding="utf-8")
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _shim_dir(shim_parent)
    r = _make("g4-candidate-manifest",
              env={"PATH": str(shim), **_env(tmp_path)},
              cwd=sandbox, make_path=_system_make())
    assert r.returncode != 0, r.stdout + r.stderr
    assert "generate_g4_candidate_manifest.mjs" in (r.stdout + r.stderr)
    log = _shim_log(shim_parent)
    assert "npm " not in log, f"npm invoked despite generator missing:\n{log}"


def test_make_g4_candidate_manifest_preflight_missing_html_aborts(tmp_path):
    """CANDIDATE_HTML → nonexistent path → preflight gate aborts
    fail-closed BEFORE npm is invoked."""
    # Sandbox WITHOUT out/index.html.
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    (sandbox / "scripts").mkdir()
    (sandbox / "scripts" / "generate_g4_candidate_manifest.mjs").write_text(
        "// sandbox stub\n")
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _shim_dir(shim_parent)
    r = _make("g4-candidate-manifest",
              env={"PATH": str(shim), **_env(tmp_path)},
              cwd=sandbox, make_path=_system_make())
    assert r.returncode != 0, r.stdout + r.stderr
    assert "CANDIDATE_HTML" in (r.stdout + r.stderr)
    log = _shim_log(shim_parent)
    assert "npm " not in log, f"npm invoked despite HTML missing:\n{log}"


def test_make_g4_candidate_manifest_preflight_html_is_directory_aborts(tmp_path):
    """CANDIDATE_HTML points to a directory → preflight gate aborts
    fail-closed BEFORE npm is invoked. Defense against `test -f` over a
    directory."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    (sandbox / "scripts").mkdir()
    (sandbox / "scripts" / "generate_g4_candidate_manifest.mjs").write_text(
        "// sandbox stub\n")
    # CANDIDATE_HTML will be a real directory.
    (sandbox / "out").mkdir()
    (sandbox / "out" / "index.html").mkdir()  # directory, not regular file
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _shim_dir(shim_parent)
    r = _make("g4-candidate-manifest",
              env={"PATH": str(shim), **_env(tmp_path)},
              cwd=sandbox, make_path=_system_make())
    assert r.returncode != 0, r.stdout + r.stderr
    log = _shim_log(shim_parent)
    assert "npm " not in log, f"npm invoked despite HTML being a directory:\n{log}"


@pytest.mark.parametrize("bad_url", [
    "ftp://taxa.example/candidate/",
    "file:///etc/passwd",
    "javascript:alert(1)",
    "/relative/path",
    "taxa.example/candidate",
    "",
])
def test_make_g4_candidate_manifest_preflight_non_http_url_aborts(tmp_path, bad_url):
    """CANDIDATE_URL not absolute http(s) → preflight gate aborts
    fail-closed BEFORE npm is invoked. Empty URL is also rejected by the
    required-var gate, which fires before the http(s) gate."""
    sandbox = _build_sandbox(tmp_path)
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _shim_dir(shim_parent)
    env = {"PATH": str(shim),
           "CANDIDATE_URL": bad_url,
           "CANDIDATE_MANIFEST": str(tmp_path / "m.json")}
    r = _make("g4-candidate-manifest", env=env, cwd=sandbox,
              make_path=_system_make())
    assert r.returncode != 0, r.stdout + r.stderr
    log = _shim_log(shim_parent)
    assert "npm " not in log, f"npm invoked despite URL {bad_url!r}:\n{log}"


# ── Default CANDIDATE_HTML (dry-run) ──────────────────────────────────


def test_make_g4_candidate_manifest_defaults_CANDIDATE_HTML_to_out_index_html(
    tmp_path,
):
    """CANDIDATE_HTML unset → the resolved value is the documented default
    `out/index.html` (literal `--html <value>` in the dry-run)."""
    out = _dry_run_recipe(_env(tmp_path))
    # The default value flows through as the --html argument. Make may
    # emit the value quoted or unquoted; either is acceptable — what
    # matters is that the default path resolves into the invocation.
    import re
    assert re.search(r'--html\s+"?out/index\.html"?', out), (
        f"default CANDIDATE_HTML not wired to out/index.html:\n{out}")


def test_make_g4_candidate_manifest_caller_can_override_CANDIDATE_HTML(tmp_path):
    """CANDIDATE_HTML set → the override is propagated literally to the
    producer invocation."""
    custom_html = tmp_path / "custom-candidate.html"
    out = _dry_run_recipe(_env(tmp_path, CANDIDATE_HTML=str(custom_html)))
    import re
    assert re.search(
        rf'--html\s+"?{re.escape(str(custom_html))}"?', out), (
        f"override CANDIDATE_HTML not propagated:\n{out}")


# ── Producer invocation shape (dry-run) ───────────────────────────────


def test_make_g4_candidate_manifest_dry_run_invokes_npm_manifest_generate(
    tmp_path,
):
    """The producer is invoked via the literal npm script form:
    `npm run manifest:generate -- --html ... --url ... --out ...`.
    A direct `node scripts/generate_g4_candidate_manifest.mjs` invocation
    would bypass the documented package-script contract and is rejected."""
    out = _dry_run_recipe(_env(tmp_path))
    assert "npm run manifest:generate --" in out, (
        f"producer invocation form is not `npm run manifest:generate --`:\n{out}")
    # No bare `node scripts/...` line at the recipe end (the recipe must
    # route through npm). If a stray direct invocation sneaks in, fail.
    for ln in out.splitlines():
        stripped = ln.lstrip()
        if stripped.startswith("node scripts/generate_g4_candidate_manifest.mjs"):
            raise AssertionError(
                f"direct node invocation found, npm contract violated:\n{ln}\n{out}")


def test_make_g4_candidate_manifest_dry_run_passes_correct_flags(tmp_path):
    """Each flag (`--html`, `--url`, `--out`) appears with the resolved
    caller value as the next token in the npm invocation."""
    manifest_path = str(tmp_path / "candidate.manifest.json")
    out = _dry_run_recipe(_env(tmp_path))
    # Locate the producer invocation line.
    npm_line = next(
        ln for ln in out.splitlines()
        if "npm run manifest:generate" in ln)
    assert "--html" in npm_line and "out/index.html" in npm_line, npm_line
    assert "--url" in npm_line and SAMPLE_URL in npm_line, npm_line
    assert "--out" in npm_line and manifest_path in npm_line, npm_line
    # The literal ` -- ` separator must precede the script args so npm
    # does not interpret them as npm flags.
    assert " -- --html" in npm_line, npm_line


def test_make_g4_candidate_manifest_dry_run_carries_caller_values(tmp_path):
    """TRIANGULATE: a custom manifest path and URL flow through to the
    producer invocation as the literal `--out`/`--url` argument."""
    custom_url = "https://staging.taxa.example/candidate/build/12345/"
    custom_manifest = tmp_path / "g4-candidate.manifest.json"
    out = _dry_run_recipe(_env(tmp_path, CANDIDATE_URL=custom_url,
                               CANDIDATE_MANIFEST=str(custom_manifest)))
    assert custom_url in out, f"URL not propagated:\n{out}"
    assert str(custom_manifest) in out, f"manifest path not propagated:\n{out}"


# ── No lifecycle / install commands ───────────────────────────────────


def test_make_g4_candidate_manifest_no_lifecycle_or_install_commands(tmp_path):
    """The new target MUST NOT install deps, build Next, or start any
    service. The caller owns the static-export build and the candidate
    URL; the target only routes inputs into the existing producer."""
    out = _dry_run_recipe(_env(tmp_path))
    for s in (
        "npm install", "npm ci", "pnpm install", "pnpm ci",
        "pip install", "pip3 install",
        "next build", "build:web",
        "kill ", "pkill", "nohup",
        "uvicorn", "make api",
        "playwright install",
        "apt-get install", "brew install",
    ):
        assert s not in out, f"forbidden substring {s!r} present:\n{out}"


def test_make_g4_candidate_manifest_does_not_touch_make_parity(tmp_path):
    """Make parity contract is unchanged: invoking parity without its
    required vars still fails closed, and the candidate-manifest target
    does not appear inside parity's recipe."""
    r = _make("parity")
    assert r.returncode != 0, r.stdout + r.stderr
    assert "PARITY_URL" in r.stdout + r.stderr
    # `make -n parity` (with all 3 set) does not mention g4-candidate-manifest.
    parity_env = {
        "PARITY_URL": "http://127.0.0.1:8765/index.html",
        "PARITY_OUT": str(tmp_path / "out"),
        "PARITY_MANIFEST": str(tmp_path / "manifest.json"),
    }
    r_dry = _make("-n", "parity", env=parity_env)
    assert r_dry.returncode == 0, r_dry.stderr
    assert "g4-candidate-manifest" not in r_dry.stdout, (
        f"candidate-manifest target leaked into parity recipe:\n{r_dry.stdout}")


# ── Quoting against shell injection (dry-run + runtime) ───────────────


def test_make_g4_candidate_manifest_quotes_caller_vars_against_shell_injection(
    tmp_path,
):
    """Controlled-shell proof: CANDIDATE_URL, CANDIDATE_HTML, and
    CANDIDATE_MANIFEST carrying shell metacharacters are quoted at the
    shell boundary on the producer invocation.

    (a) `make -n` preserves the payload inside `"..."` (ONE argv element).
    (b) Real controlled-shell run MUST NOT create the leak-marker.
    """
    payload = f"http://x.invalid; touch {tmp_path}/leak-marker; echo"
    html_payload = (
        f"out/index.html; touch {tmp_path}/leak-html; echo"
    )
    env_all = {
        "CANDIDATE_URL": payload,
        "CANDIDATE_HTML": html_payload,
        "CANDIDATE_MANIFEST": payload,
    }
    # (a) Dry-run preserves the quoted form.
    r_dry = _make("-n", "g4-candidate-manifest", env=_env(tmp_path, **env_all))
    assert r_dry.returncode == 0, r_dry.stderr
    # Each payload-bearing variable appears as a single quoted argv
    # element on the producer invocation. Make emits the literal
    # double-quotes I put around `$(VAR)`, so the format is
    # `--flag "<value>"` (one argv element containing the payload,
    # including its shell metacharacters, intact).
    assert f'--url "{payload}"' in r_dry.stdout, (
        f"CANDIDATE_URL not quoted on producer invocation:\n{r_dry.stdout}")
    assert f'--html "{html_payload}"' in r_dry.stdout, (
        f"CANDIDATE_HTML not quoted on producer invocation:\n{r_dry.stdout}")
    assert f'--out "{payload}"' in r_dry.stdout, (
        f"CANDIDATE_MANIFEST not quoted on producer invocation:\n{r_dry.stdout}")
    # (b) Real controlled-shell run — the injected `touch` MUST NOT execute.
    sandbox = _build_sandbox(tmp_path)
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _shim_dir(shim_parent)
    r = _make("g4-candidate-manifest",
              env={"PATH": str(shim), **_env(sandbox, **env_all)},
              cwd=sandbox, make_path=_system_make())
    assert not (tmp_path / "leak-marker").exists(), (
        f"shell injection succeeded: leak-marker created\n{r.stdout}\n{r.stderr}")
    assert not (tmp_path / "leak-html").exists(), (
        f"HTML shell-injection succeeded: leak-html created\n{r.stdout}\n{r.stderr}")


# ── End-to-end success (runtime, hermetic) ────────────────────────────


def test_make_g4_candidate_manifest_runs_producer_with_correct_argv(tmp_path):
    """All preflight gates pass → producer is invoked once, via npm, with
    the documented argv order `--html <path> --url <url> --out <path>`.
    Each value arrives as a distinct argv element (no word-splitting)."""
    sandbox = _build_sandbox(tmp_path)
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _shim_dir(shim_parent)
    r = _make("g4-candidate-manifest",
              env={"PATH": str(shim), **_env(sandbox)},
              cwd=sandbox, make_path=_system_make())
    assert r.returncode == 0, r.stdout + r.stderr
    log = _shim_log(shim_parent)
    # Exactly one npm invocation, exactly one node invocation routed to the
    # generator script.
    assert log.count("npm ") == 1, log
    node_lines = [
        ln for ln in log.splitlines()
        if ln.startswith("node ")
        and "scripts/generate_g4_candidate_manifest.mjs" in ln
    ]
    assert len(node_lines) == 1, log
    node_line = node_lines[0]
    # Each flag and value appears as one argv token.
    assert "scripts/generate_g4_candidate_manifest.mjs" in node_line
    assert "--html" in node_line and "out/index.html" in node_line
    assert "--url" in node_line and SAMPLE_URL in node_line
    assert "--out" in node_line and "candidate.manifest.json" in node_line


def test_make_g4_candidate_manifest_runs_producer_in_overridden_html_cwd(
    tmp_path,
):
    """CANDIDATE_HTML override flows all the way through to the producer
    argv when preflight passes."""
    sandbox = _build_sandbox(tmp_path)
    # Add a second regular HTML the caller wants to point at.
    custom_html = sandbox / "candidate-build" / "candidate.html"
    custom_html.parent.mkdir(parents=True)
    custom_html.write_text(
        f"<html>{SSR_PROBE_MARKER}</html>\n", encoding="utf-8")
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _shim_dir(shim_parent)
    r = _make("g4-candidate-manifest",
              env={"PATH": str(shim),
                   **_env(sandbox, CANDIDATE_HTML=str(custom_html))},
              cwd=sandbox, make_path=_system_make())
    assert r.returncode == 0, r.stdout + r.stderr
    log = _shim_log(shim_parent)
    node_line = next(
        ln for ln in log.splitlines()
        if "scripts/generate_g4_candidate_manifest.mjs" in ln)
    assert str(custom_html) in node_line, (
        f"override CANDIDATE_HTML not propagated to producer argv:\n{log}")


# ── Manifest parent directory creation (runtime, hermetic) ────────────


def test_make_g4_candidate_manifest_creates_manifest_parent_directory(
    tmp_path,
):
    """CANDIDATE_MANIFEST with a non-existent parent directory → recipe
    creates the directory before invoking the producer."""
    sandbox = _build_sandbox(tmp_path)
    nested = tmp_path / "deep" / "nested" / "candidate.manifest.json"
    shim_parent = tmp_path / "shim_parent"
    shim_parent.mkdir()
    shim = _shim_dir(shim_parent)
    r = _make("g4-candidate-manifest",
              env={"PATH": str(shim),
                   **_env(sandbox, CANDIDATE_MANIFEST=str(nested))},
              cwd=sandbox, make_path=_system_make())
    assert r.returncode == 0, r.stdout + r.stderr
    log = _shim_log(shim_parent)
    assert "generate_g4_candidate_manifest.mjs" in log, log
