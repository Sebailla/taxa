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
    """The `make api` recipe body MUST couple the Next.js static-export
    build with the Uvicorn invocation in a single command. The legacy
    Tailwind `build:css` step is no longer part of `make api` because
    the static export at `out/` is the source of truth after the
    ODD-MIGRATE-006 atomic cutover.

    ODD-MIGRATE-006 (atomic cutover) pre-pinning: after commit (b) lands,
    `make api` couples `pnpm install` + `pnpm build` with the Uvicorn
    invocation in one recipe. The legacy `pnpm install` prohibition is
    carved out (the build step needs `pnpm install` to hydrate the
    workspace); the prohibitions on raw `npm install`, raw `npm run`,
    and the retired `build:css` script stay intact. Until commit (b)
    lands, the positive `pnpm install` + `pnpm build` assertions fail
    RED with "test expects post-cut state but production is still
    pre-cut" — the explicit carveout that re-anchors the assertion
    target to the build + uvicorn shape.
    """
    out = _dry_run_recipe("api")
    # The expected Uvicorn command MUST still be present (the API
    # server contract is unchanged — only the build prerequisite is
    # added in front of it).
    expected = ".venv/bin/python3 -m uvicorn api.server:app"
    assert expected in out, (
        f"uvicorn invocation missing from `make -n api`:\n{out}"
    )
    # Post-cut `pnpm install` IS required (the build step needs the
    # hydrated workspace). Carved out from the pre-cut prohibition so
    # the post-cut recipe couples install + build + uvicorn.
    assert "pnpm install" in out, (
        f"pnpm install missing from `make -n api` (post-cut "
        f"ODD-MIGRATE-006 build prerequisite required):\n{out}"
    )
    # Post-cut `pnpm build` IS required (the Next.js static export at
    # `out/` must be regenerated before the API server starts).
    assert "pnpm build" in out, (
        f"pnpm build missing from `make -n api` (post-cut "
        f"ODD-MIGRATE-006 static-export build required):\n{out}"
    )
    # No raw npm anywhere in the api recipe chain. The search regex uses
    # a word boundary so `pnpm install` / `pnpm build` do NOT match
    # `npm install` / `npm run` (the leading `p` of `pnpm` is outside
    # the boundary).
    npm_install = re.search(r"(?:^|\s)npm\s+install\b", out, re.MULTILINE)
    assert not npm_install, (
        f"npm install leaked into `make -n api`:\n{out}"
    )
    npm_run = re.search(r"(?:^|\s)npm\s+run\b", out, re.MULTILINE)
    assert not npm_run, (
        f"npm run leaked into `make -n api`:\n{out}"
    )
    # The legacy `build:css` Tailwind script is retired by the cutover —
    # the static export at `out/` replaces `web/dist/tailwind.css`.
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
