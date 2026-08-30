"""
G2 candidate-foundation contract tests — see design.md §3.3.2.1.

Pins the AUTHORED contract for the self-contained, NON-activation build
root at `tools/g2-candidate/`. Does NOT select Approach A / B / C. Does
NOT wire FastAPI, `web/`, CI, root `package.json`, Makefile, or
`extension/manifest.json`. The strict-TDD G2 verifier (a separate work
unit) will assert the BUILD-TIME contract against `<candidate-root>/out/`;
THIS module asserts the config-and-isolation contract that makes the
verifier possible. Tests do NOT require a real Next.js install.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
CANDIDATE_ROOT = REPO_ROOT / "tools" / "g2-candidate"
PACKAGE_JSON = CANDIDATE_ROOT / "package.json"
PACKAGE_LOCK = CANDIDATE_ROOT / "package-lock.json"
NEXT_CONFIG_MJS = CANDIDATE_ROOT / "next.config.mjs"
APP_DIR = CANDIDATE_ROOT / "app"
LAYOUT_JS = APP_DIR / "layout.js"
PAGE_JS = APP_DIR / "page.js"
GLOBALS_CSS = APP_DIR / "globals.css"

# Pinned by design.md §3.3.2.1 (the only canonical source).
PINNED_NEXT = "16.3.3"
PINNED_REACT = "19.2.8"
PINNED_REACT_DOM = "19.2.8"
NODE_MIN = ">=20.9.0"

# Matches a real `from "next/font/..."` import (not the words in a comment).
NEXT_FONT_IMPORT_RE = re.compile(r"""from\s+["']next/font(?:\.[a-z]+|\b)""")


def _read_json(path: Path) -> dict:
    if not path.is_file():
        pytest.fail(f"missing JSON file: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        pytest.fail(f"invalid JSON in {path}: {exc}")


def _load_next_config() -> dict | None:
    """Evaluate next.config.mjs as ESM and return its default export.
    Returns None if Node or the file is missing — callers skip.
    Fails via pytest.fail on evaluation errors so a broken config is loud."""
    if not shutil.which("node") or not NEXT_CONFIG_MJS.is_file():
        return None
    script = (
        "const m = await import(" + json.dumps(str(NEXT_CONFIG_MJS)) + ");\n"
        "process.stdout.write(JSON.stringify(m.default));\n"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=CANDIDATE_ROOT, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"failed to evaluate {NEXT_CONFIG_MJS} as ESM: "
                    f"{result.stderr.strip() or '(no stderr)'}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"{NEXT_CONFIG_MJS} default export is not JSON-serializable: "
                    f"{result.stdout!r} ({exc})")


def _iter_candidate_text_files() -> list[Path]:
    """Walk AUTHORED candidate content only. Skips vendor (`node_modules/`),
    build cache (`.next/`), output (`out/`), and the size:exception
    lockfile — none of these get reviewed or committed."""
    if not CANDIDATE_ROOT.is_dir():
        return []
    skip_dirs = {"node_modules", ".next", "out"}
    out: list[Path] = []
    for path in sorted(CANDIDATE_ROOT.rglob("*")):
        if not path.is_file() or path.name == "package-lock.json":
            continue
        if any(p in skip_dirs for p in path.relative_to(CANDIDATE_ROOT).parts):
            continue
        try:
            path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        out.append(path)
    return out


# Workspace layout

@pytest.mark.parametrize(
    "path",
    [CANDIDATE_ROOT, PACKAGE_JSON, NEXT_CONFIG_MJS, APP_DIR,
     LAYOUT_JS, PAGE_JS, GLOBALS_CSS],
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_candidate_workspace_layout_is_present(path: Path):
    """`tools/g2-candidate/` is laid out per design.md §3.3.2.1."""
    assert path.is_file() or path.is_dir(), (
        f"missing required candidate path: {path}. "
        f"design.md §3.3.2.1 pins the workspace shape."
    )


# package.json contract

def test_package_json_has_exact_pinned_versions():
    """Next 16.3.3 / React 19.2.8 / react-dom 19.2.8 — exact pins, no ranges."""
    pkg = _read_json(PACKAGE_JSON)
    deps = pkg.get("dependencies") or {}
    assert deps.get("next") == PINNED_NEXT, (
        f"next must be pinned exactly to {PINNED_NEXT}; got {deps.get('next')!r}")
    assert deps.get("react") == PINNED_REACT, (
        f"react must be pinned exactly to {PINNED_REACT}; got {deps.get('react')!r}")
    assert deps.get("react-dom") == PINNED_REACT_DOM, (
        f"react-dom must be pinned exactly to {PINNED_REACT_DOM}; "
        f"got {deps.get('react-dom')!r}")


def test_package_json_declares_engine_node_minimum():
    """`engines.node >= 20.9.0` (Next.js 16 hard requirement)."""
    pkg = _read_json(PACKAGE_JSON)
    node_engine = (pkg.get("engines") or {}).get("node")
    assert node_engine == NODE_MIN, (
        f"engines.node must be {NODE_MIN!r} for Next.js 16; got {node_engine!r}")


def test_package_json_is_private_and_isolated():
    """`private:true`, no `workspaces`, no `devDependencies` — disposable, isolated, minimal."""
    pkg = _read_json(PACKAGE_JSON)
    assert pkg.get("private") is True, (
        "tools/g2-candidate/package.json must declare private:true")
    assert "workspaces" not in pkg, (
        "candidate must NOT declare npm workspaces (isolation contract)")
    deps = set((pkg.get("dependencies") or {}).keys())
    assert deps == {"next", "react", "react-dom"}, (
        f"dependencies must be exactly {{next, react, react-dom}}; "
        f"got {sorted(deps)}")
    dev = pkg.get("devDependencies")
    assert not dev, (
        f"devDependencies must be empty; got {sorted((dev or {}).keys())}")


def test_package_json_build_script_invokes_next_build():
    """`scripts.build` runs `next build` — the agreed build command."""
    pkg = _read_json(PACKAGE_JSON)
    build = (pkg.get("scripts") or {}).get("build", "")
    assert build.strip() == "next build", (
        f"scripts.build must be exactly 'next build' (design.md §3.3.2.1); "
        f"got {build!r}")


def test_package_json_name_matches_candidate_role():
    """Name reflects the candidate role and doesn't impersonate production."""
    pkg = _read_json(PACKAGE_JSON)
    name = pkg.get("name") or ""
    assert "g2-candidate" in name, (
        f"name should reflect the candidate role; got {name!r}")
    assert name not in ("taxa-web", "taxa-web-static"), (
        f"candidate must not impersonate a production package name; got {name!r}")


# next.config.mjs contract

def test_next_config_evaluates_and_has_required_knobs():
    """Evaluate next.config.mjs as ESM and assert the three required knobs
    with exact values: `output: "export"`, `images.unoptimized: true`,
    `trailingSlash: false`."""
    cfg = _load_next_config()
    if cfg is None:
        pytest.skip("node unavailable or next.config.mjs not present yet")
    assert cfg.get("output") == "export", (
        f"output must be 'export' (static export); got {cfg.get('output')!r}")
    assert (cfg.get("images") or {}).get("unoptimized") is True, (
        f"images.unoptimized must be true; got "
        f"{(cfg.get('images') or {}).get('unoptimized')!r}")
    assert cfg.get("trailingSlash") is False, (
        f"trailingSlash must be false; got {cfg.get('trailingSlash')!r}")


def test_next_config_does_not_promote_alternative_output_modes():
    """Triangulation: must NOT use 'standalone' or other non-static modes."""
    cfg = _load_next_config()
    if cfg is None:
        pytest.skip("node unavailable or next.config.mjs not present yet")
    forbidden = {"standalone", "server", "experimental-serverless"}
    output = cfg.get("output")
    assert output not in forbidden, (
        f"output must remain 'export'; got {output!r} "
        f"(forbidden: {sorted(forbidden)})")


# App shell

@pytest.mark.parametrize("path", [LAYOUT_JS, PAGE_JS], ids=lambda p: p.name)
def test_candidate_app_component_is_a_server_component(path: Path):
    """Layout and page stay server components (no 'use client')."""
    text = path.read_text()
    assert '"use client"' not in text and "'use client'" not in text, (
        f"{path} must stay a server component.")


def test_layout_imports_globals_css():
    """Imports `./globals.css` so the build emits a CSS bundle under
    `out/_next/static/css/` (or Next 16's equivalent co-located chunk)."""
    assert "./globals.css" in LAYOUT_JS.read_text(), (
        f"{LAYOUT_JS} must import './globals.css' so the build ships a CSS bundle.")


def test_globals_css_is_a_real_stylesheet():
    text = GLOBALS_CSS.read_text()
    assert text.strip(), f"{GLOBALS_CSS} must contain at least one CSS rule."
    assert "body" in text or ":root" in text or "html" in text, (
        f"{GLOBALS_CSS} should target body/:root/html so the export ships a "
        f"meaningful CSS bundle.")


def test_candidate_does_not_use_next_font():
    """`next/font` is contractually out of scope. Static fonts are a
    CONDITIONAL asset class (only emitted if `next/font` is used)."""
    for path in (LAYOUT_JS, PAGE_JS):
        match = NEXT_FONT_IMPORT_RE.search(path.read_text())
        assert match is None, (
            f"{path} must not import next/font — found: {match.group(0)!r}")


def test_candidate_app_dir_has_no_subroutes():
    """Triangulation: exactly one `page.js` (root); no extra routes."""
    page_files = list(APP_DIR.rglob("page.js"))
    assert page_files == [PAGE_JS], (
        f"app/ should contain exactly one page.js ({PAGE_JS}); "
        f"found {[str(p.relative_to(REPO_ROOT)) for p in page_files]}")


# Isolation — candidate must NOT wire production surfaces

ISOLATION_NEEDLES = (
    # Production code paths must not be imported from the candidate.
    'from "../api', 'from "../../api',
    'from "../src/', 'from "../web/', 'from "../../web/',
    'from "../extension', 'from "../../extension',
    # Sibling diagnostic probe must not be reused as a candidate dep.
    "tools/static-export-probe",
    # CI workflows must not be referenced (build wiring is owned by Makefile).
    "github/workflows",
    # Verifier scripts are out of scope for this work unit.
    "verify_build.py", "emit_build_profile.mjs",
)


@pytest.mark.parametrize("needle", ISOLATION_NEEDLES, ids=lambda n: n)
def test_candidate_sources_do_not_reference_production_paths(needle: str):
    """No candidate file may reference production surfaces (api/, src/,
    web/, extension/, CI) or sibling probes — design.md §3.3.2.1 requires
    the candidate is isolated and non-activation."""
    offenders = [
        str(p.relative_to(REPO_ROOT))
        for p in _iter_candidate_text_files()
        if needle in p.read_text()
    ]
    assert not offenders, (
        f"candidate must not reference {needle!r}; offenders: {offenders}")


def test_candidate_does_not_promote_a_taxa_package_name():
    """Triangulation: candidate name MUST NOT collide with the root
    package.json name — prevents accidental npm-aliasing if imported
    elsewhere."""
    pkg = _read_json(PACKAGE_JSON)
    name = pkg.get("name") or ""
    root_pkg_path = REPO_ROOT / "package.json"
    if not root_pkg_path.is_file():
        pytest.skip("root package.json not present")
    root_name = (_read_json(root_pkg_path).get("name") or "")
    assert name != root_name, (
        f"candidate package name {name!r} must NOT match the root "
        f"package.json name; rename the candidate.")


# package-lock.json — present iff npm ci exited 0

def test_package_lock_is_present_after_npm_ci():
    """Presence of the lockfile is the contract proof that `npm ci` succeeded."""
    assert PACKAGE_LOCK.is_file(), (
        f"missing {PACKAGE_LOCK}. design.md §3.3.2.1 grants the size:exception "
        f"ONLY when npm ci exits 0; if this test fails, either npm ci failed "
        f"(lockfile must not be committed) or the lockfile is being skipped.")


def test_package_lock_pins_candidate_name():
    """Lockfile names the candidate workspace so a reviewer can tell at a
    glance which package tree this lockfile is for."""
    lock = _read_json(PACKAGE_LOCK)
    name = lock.get("name")
    assert name and "g2-candidate" in str(name), (
        f"package-lock.json name should reflect the candidate role; got {name!r}")
