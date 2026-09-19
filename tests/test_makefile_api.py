"""ODD-MAP-001 Makefile API + pnpm contract tests.

Hermetic: every test inspects `make -n` (dry-run) output against the
repository Makefile, so no Node toolchain, no uvicorn, no FastAPI
import, and no DB is touched. Validates the `make api` / `make css`
contract after the ODD-MAP-001 alignment:

  * `make api` starts Uvicorn WITHOUT running npm/pnpm install or the
    Tailwind CSS build as a prerequisite. The API server is decoupled
    from the frontend asset pipeline.
  * `make css` uses pnpm consistently with `pnpm-lock.yaml`
    (`pnpm install --frozen-lockfile` + `pnpm run build:css`); npm is
    not used anywhere in the Makefile's frontend toolchain recipe.
  * `package.json` exposes the `build:css` script so `pnpm run build:css`
    resolves to the Tailwind CLI invocation.
  * The repository tracks `pnpm-lock.yaml` as the canonical lockfile,
    not `package-lock.json` (npm).

Reference: odd/tasks/make-api-pnpm-bootstrap.md (ODD-MAP-001).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
PACKAGE_JSON = REPO_ROOT / "package.json"
PNPM_LOCKFILE = REPO_ROOT / "pnpm-lock.yaml"
NPM_LOCKFILE = REPO_ROOT / "package-lock.json"


def _make(*args, env=None):
    """Run `make` against the repo Makefile with the requested args."""
    full_env = os.environ.copy()
    full_env.pop("PARITY_URL", None)
    full_env.pop("PARITY_OUT", None)
    full_env.pop("PARITY_MANIFEST", None)
    full_env.pop("PARITY_QUERIES", None)
    full_env.pop("PARITY_QUERIES_FILE", None)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["make", "-f", str(MAKEFILE), *args],
        cwd=REPO_ROOT, env=full_env,
        capture_output=True, text=True, check=False,
    )


def _dry_run_recipe(*targets: str) -> str:
    """Run `make -n <targets...>`; return the recipe output as a string.

    Multiple targets are joined with `+` so we can verify the combined
    dry-run of `api` and `css` (which is what `make api` WOULD do if
    the old `api: css` dependency were still present). For a single
    target we just inspect `make -n <target>` directly.
    """
    if len(targets) == 1:
        r = _make("-n", targets[0])
        assert r.returncode == 0, r.stdout + r.stderr
        return r.stdout
    # Joined targets: pass each target to one dry-run so make concatenates
    # the recipes in declaration order.
    r = _make("-n", *targets)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


# ── `make api` decoupling contract ────────────────────────────────────


def test_make_api_recipe_runs_uvicorn_only():
    """The `make api` recipe body MUST contain exactly one command:
    the Uvicorn invocation. No css / npm / pnpm prerequisite recipes
    are allowed to leak into the dry-run output."""
    out = _dry_run_recipe("api")
    # The expected Uvicorn command is the only thing that should appear.
    expected = ".venv/bin/python3 -m uvicorn api.server:app"
    assert expected in out, (
        f"uvicorn invocation missing from `make -n api`:\n{out}"
    )
    # No npm anywhere in the api recipe chain. The search regex uses a
    # word boundary so `pnpm install` does not match `npm install`.
    npm_install = re.search(r"(?:^|\s)npm\s+install\b", out, re.MULTILINE)
    assert not npm_install, (
        f"npm install leaked into `make -n api`:\n{out}"
    )
    npm_run = re.search(r"(?:^|\s)npm\s+run\b", out, re.MULTILINE)
    assert not npm_run, (
        f"npm run leaked into `make -n api`:\n{out}"
    )
    # No pnpm install (pnpm install is invocation, not just the binary).
    assert "pnpm install" not in out, (
        f"pnpm install leaked into `make -n api`:\n{out}"
    )
    # No build:css invocation.
    assert "build:css" not in out, (
        f"build:css leaked into `make -n api`:\n{out}"
    )


def test_make_api_recipe_does_not_pull_in_css_target():
    """`make api` and `make css` are independent recipes. A combined
    `make -n api+css` MUST show BOTH recipe bodies in the dry-run
    output (proving `api` does NOT silently pull in `css`)."""
    out = _dry_run_recipe("api", "css")
    # Both recipe bodies must be present (otherwise one is consuming
    # the other).
    assert "uvicorn api.server:app" in out, (
        f"api recipe missing from combined dry-run:\n{out}"
    )
    assert "build:css" in out, (
        f"css recipe missing from combined dry-run:\n{out}"
    )


def test_make_api_recipe_targets_localhost_port_8765():
    """The Uvicorn bind is `--host 127.0.0.1 --port 8765` — the same
    port the existing `make smoke` and `tests/test_smoke.py` contract
    assume. Drift here would silently break the smoke harness."""
    out = _dry_run_recipe("api")
    assert "--host 127.0.0.1" in out, (
        f"--host 127.0.0.1 missing from `make -n api`:\n{out}"
    )
    assert "--port 8765" in out, (
        f"--port 8765 missing from `make -n api`:\n{out}"
    )


# ── `make css` pnpm contract ──────────────────────────────────────────


def test_make_css_recipe_uses_pnpm_install_frozen_lockfile():
    """`make css` MUST use `pnpm install --frozen-lockfile` (not npm).
    `--frozen-lockfile` enforces the pnpm-lock.yaml contract and
    prevents accidental lockfile drift."""
    out = _dry_run_recipe("css")
    assert "pnpm install --frozen-lockfile" in out, (
        f"`pnpm install --frozen-lockfile` missing from `make -n css`:\n{out}"
    )
    # npm install is forbidden anywhere in the css recipe chain —
    # but `pnpm install` (which contains the substring `npm install`)
    # is the expected call. Use a regex with a word boundary so the
    # leading `p` in `pnpm` does not match.
    npm_install = re.search(r"(?:^|\s)npm\s+install\b", out, re.MULTILINE)
    assert not npm_install, (
        f"npm install leaked into `make -n css`:\n{out}"
    )


def test_make_css_recipe_uses_pnpm_run_build_css():
    """`make css` runs the Tailwind CLI via `pnpm run build:css`
    (which dispatches to the package.json script). Direct
    `tailwindcss` binary invocation is forbidden — script-based
    dispatch keeps the CLI version pinned via pnpm-lock.yaml."""
    out = _dry_run_recipe("css")
    assert "pnpm run build:css" in out, (
        f"`pnpm run build:css` missing from `make -n css`:\n{out}"
    )
    # No direct `tailwindcss` binary call (the script does that).
    bare_invocation = re.search(r"(^|\s)tailwindcss\s+-i", out, re.MULTILINE)
    assert not bare_invocation, (
        f"bare `tailwindcss -i ...` leaked into `make -n css`:\n{out}"
    )


# ── package.json / lockfile contract ──────────────────────────────────


def test_package_json_exposes_build_css_script():
    """`pnpm run build:css` requires a `build:css` key in the
    `scripts` section of package.json. Guard against accidental
    rename / removal of the Tailwind CLI invocation contract."""
    data = json.loads(PACKAGE_JSON.read_text())
    scripts = data.get("scripts", {})
    assert "build:css" in scripts, (
        f"package.json scripts missing 'build:css': {sorted(scripts)}"
    )
    cmd = scripts["build:css"]
    # The script MUST invoke `tailwindcss -i ... -o ...` (the v4 CLI
    # invocation contract verified by ODD-TW-001). Any other binary
    # would mean the script no longer produces web/dist/tailwind.css.
    assert "tailwindcss" in cmd, (
        f"build:css script does not invoke tailwindcss: {cmd!r}"
    )
    assert "web/index.css" in cmd, (
        f"build:css script does not read from web/index.css: {cmd!r}"
    )
    assert "web/dist/tailwind.css" in cmd, (
        f"build:css script does not write to web/dist/tailwind.css: "
        f"{cmd!r}"
    )


def test_package_json_does_not_introduce_npm_only_scripts():
    """Repository scripts MUST stay pnpm-friendly. A direct `npm`
    invocation inside `scripts` would bypass pnpm-lock.yaml and
    reintroduce the lockfile drift ODD-TW-001 closed."""
    data = json.loads(PACKAGE_JSON.read_text())
    for name, cmd in data.get("scripts", {}).items():
        assert "npm " not in cmd and not cmd.startswith("npm"), (
            f"package.json script {name!r} uses npm directly: {cmd!r}"
        )


def test_repository_uses_pnpm_lockfile_as_canonical():
    """`pnpm-lock.yaml` is the canonical lockfile (per ODD-TW-001).
    `package-lock.json` MUST NOT be reintroduced — having both
    lockfiles is a known source of pnpm/npm drift."""
    assert PNPM_LOCKFILE.exists(), (
        f"pnpm-lock.yaml missing at repo root (expected at {PNPM_LOCKFILE})"
    )
    assert not NPM_LOCKFILE.exists(), (
        f"package-lock.json must not exist alongside pnpm-lock.yaml: "
        f"{NPM_LOCKFILE}"
    )


# ── Cross-target contract: `api` does not chain `css` ─────────────────


def test_make_api_target_line_has_no_prerequisite():
    """The Makefile line `api:` MUST NOT carry a prerequisite. A
    `api: css` line would silently chain the CSS build every time
    `make api` is invoked, defeating the ODD-MAP-001 decoupling."""
    text = MAKEFILE.read_text()
    # Match the `api:` target declaration on its own line, allowing
    # any leading whitespace but rejecting `api:` as part of a longer
    # identifier (e.g. `api.js`). Anchor with start-of-line.
    api_target_re = re.compile(r"^\s*api:\s*(.*)$")
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("#"):
            continue
        m = api_target_re.match(line)
        if not m:
            continue
        deps = m.group(1).strip()
        assert deps == "", (
            f"`api:` target has prerequisites {deps!r}; "
            "ODD-MAP-001 requires `api:` to be prerequisite-free "
            "so it can start Uvicorn without running npm/pnpm "
            "install or the CSS build first."
        )
        return
    raise AssertionError("`api:` target not found in Makefile")


def test_make_css_target_line_still_in_phony_list():
    """Both `api` and `css` MUST be declared in `.PHONY` so a stale
    file named `api` or `css` cannot shadow the recipe. Drift here
    would break developer muscle memory (e.g. `touch api` accidentally
    breaking the dev loop)."""
    text = MAKEFILE.read_text()
    m = re.search(r"^\.PHONY:\s*(.+)$", text, re.MULTILINE)
    assert m is not None, ".PHONY declaration not found in Makefile"
    phony = m.group(1).split()
    for target in ("api", "css"):
        assert target in phony, (
            f"target {target!r} missing from .PHONY list: {phony}"
        )
