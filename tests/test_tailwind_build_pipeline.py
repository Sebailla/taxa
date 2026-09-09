"""Build-pipeline regression tests for PR 5.5 (Tailwind 4 / PostCSS repair).

The 3c sub-sequence (PR 3c-i / 3c-ii / 3c-iii) ships
``src/app/globals.css`` with ``@import "tailwindcss";`` and an ``@theme``
block carrying the legacy ``:root`` token palette. Without the
``@tailwindcss/postcss`` PostCSS plugin registered in
``postcss.config.mjs``, ``next build`` leaves the ``@theme { … }`` block
as a literal at-rule in the compiled CSS (the browser silently ignores
it — ``@theme`` is not a real CSS at-rule), no Tailwind preflight is
emitted, and the legacy cascade ships broken: every ``var(--primary)``
reference resolves to ``unset`` because the token was never emitted to
``:root``. This file is the regression test that catches that defect at
artifact level — by performing a REAL ``next build`` and reading the
generated CSS — rather than by relying on source-only inspection.

Pinned contract (PR 5.5, position 5.5/17 between PR 3c-iii and PR 3c-iv):

  1. ``next build`` exits 0 against the repo as configured after the
     repair.
  2. The compiled CSS bundle under ``out/_next/static/css/`` contains
     at least one Tailwind-produced signature that proves the PostCSS
     plugin ran: the canonical witness is the Tailwind 4 preflight
     universal-selector rule (``*, ::before, ::after { box-sizing:
     border-box; … }``), which is a stable, unique-by-construction
     artifact that only the ``@tailwindcss/postcss`` plugin emits.
  3. The compiled CSS bundle does NOT contain the literal at-rule
     ``@theme {`` — Tailwind 4 expands every ``@theme { … }`` block
     into a corresponding ``:root { … }`` declaration; a literal
     ``@theme {`` surviving into the bundle is the signature defect
     that proves the PostCSS plugin never ran and the browser will
     silently drop the entire token palette at runtime.
  4. The compiled CSS bundle does NOT contain the literal substring
     ``@import "tailwindcss"`` — that directive MUST be resolved by
     the PostCSS plugin and replaced with the actual Tailwind 4
     stylesheet contents (preflight + theme tokens + utility surface).
  5. The test cleans its generated build artifact so the working tree
     stays tidy — the test fixture owns the ``out/`` (and ``.next/``)
     directories for the duration of the run and removes them if (and
     only if) they did not exist before the test entered.

Reference: design.md §5.5 / tasks.md 5.5 / apply-progress.md PR 5.5 entry.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_GLOBALS_CSS = REPO_ROOT / "src" / "app" / "globals.css"
POSTCSS_CONFIG = REPO_ROOT / "postcss.config.mjs"
PACKAGE_JSON = REPO_ROOT / "package.json"
BUILD_OUT_DIR = REPO_ROOT / "out"
BUILD_CACHE_DIR = REPO_ROOT / ".next"

# Tailwind 4 / PostCSS plugin identifiers — pinned by package.json deps in PR 5.5.
REQUIRED_POSTCSS_PLUGIN = "@tailwindcss/postcss"

# Tailwind 4 preflight universal-selector rule. The rule is emitted by the
# @tailwindcss/postcss plugin as the FIRST ``@layer base { … }`` block in
# the resolved stylesheet; its canonical Tailwind 4 shape is
# ``*,:after,:before,::backdrop { box-sizing: border-box; border: 0 solid;
# margin: 0; padding: 0 }`` (note the single-colon pseudo-element
# spellings and the trailing ``::backdrop`` selector). If the compiled
# bundle does NOT contain this rule, the plugin never ran.
TAILWIND_PREFLIGHT_RE = re.compile(
    r"\*\s*,\s*:after\s*,\s*:before\s*,\s*::backdrop\s*\{[^}]*box-sizing\s*:\s*border-box",
    re.IGNORECASE,
)

# Literal unresolved @theme at-rule (the post-3c-i defect signature).
# Tailwind 4 expands every ``@theme { … }`` block into ``:root { … }``; a
# literal ``@theme {`` surviving into the bundle means the plugin never ran
# and the browser will drop the entire token palette at runtime.
LITERAL_THEME_AT_RULE_RE = re.compile(r"@theme\s*\{")

# Literal unresolved @import directive. Tailwind 4 inlines the entire
# ``@import "tailwindcss";`` directive (preflight + theme tokens + utility
# class surface) into the bundle; a literal ``@import "tailwindcss"``
# surviving means the plugin never ran.
LITERAL_IMPORT_RE = re.compile(r'@import\s+["\']tailwindcss["\']')


def _has_node() -> bool:
    return shutil.which("node") is not None


def _has_node_modules() -> bool:
    return (REPO_ROOT / "node_modules").is_dir()


def _has_next_cli() -> bool:
    """Locate the ``next`` binary inside ``node_modules/.bin/``."""
    return (REPO_ROOT / "node_modules" / ".bin" / "next").is_file()


@pytest.fixture(scope="module")
def build_artifact():
    """Run a REAL ``next build`` against the repo and yield the build dir.

    Skips when Node / ``node_modules`` / ``next`` CLI is unavailable so the
    test stays usable on a fresh clone that has not yet run ``npm ci`` —
    a separate ``make api`` run installs deps before the build pipeline
    is reproducible. The fixture cleans ``out/`` and ``.next/`` on
    teardown IF those directories did not exist before the test entered
    (so a developer who already has an ``out/`` from a prior build keeps
    theirs).
    """
    if not _has_node():
        pytest.skip("node not on PATH — install Node per .nvmrc first")
    if not _has_node_modules() or not _has_next_cli():
        pytest.skip(
            "node_modules / next CLI missing — run `npm ci` first; "
            "the build-pipeline test requires a real installed toolchain"
        )
    if not SRC_GLOBALS_CSS.is_file():
        pytest.fail(f"src/app/globals.css missing at {SRC_GLOBALS_CSS}")
    if not POSTCSS_CONFIG.is_file():
        pytest.fail(
            f"postcss.config.mjs missing at {POSTCSS_CONFIG} — "
            f"PR 5.5 ships @tailwindcss/postcss as the registered plugin"
        )

    out_existed = BUILD_OUT_DIR.exists()
    next_existed = BUILD_CACHE_DIR.exists()
    try:
        env = os.environ.copy()
        # Next 16 static export writes ``out/``; the build cache sits under
        # ``.next/``. We do not need to override either.
        proc = subprocess.run(
            ["node", "node_modules/.bin/next", "build"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
            check=False, env=env, timeout=600,
        )
        if proc.returncode != 0:
            pytest.fail(
                "next build exited non-zero before the CSS contract "
                "could be checked (defect is upstream of CSS inspection):\n"
                f"--- stdout ---\n{proc.stdout}\n"
                f"--- stderr ---\n{proc.stderr}"
            )
        yield BUILD_OUT_DIR
    finally:
        if not out_existed and BUILD_OUT_DIR.exists():
            shutil.rmtree(BUILD_OUT_DIR, ignore_errors=True)
        if not next_existed and BUILD_CACHE_DIR.exists():
            shutil.rmtree(BUILD_CACHE_DIR, ignore_errors=True)


def _css_files(out_dir: Path) -> list[Path]:
    """Locate compiled CSS bundles. Next 16 writes them under
    ``out/_next/static/css/`` OR, with Turbopack's chunked pipeline,
    ``out/_next/static/chunks/*.css`` — both shapes must be inspected
    so the regression survives a future build-pipeline change."""
    candidates: list[Path] = []
    css_dir = out_dir / "_next" / "static" / "css"
    chunks_dir = out_dir / "_next" / "static" / "chunks"
    for d in (css_dir, chunks_dir):
        if d.is_dir():
            candidates.extend(sorted(p for p in d.iterdir() if p.suffix == ".css"))
    return candidates


def _combined_css(out_dir: Path) -> str:
    files = _css_files(out_dir)
    return "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in files
    )


# ---------------------------------------------------------------------------
# RED-GREEN contract — the test pair below is the regression witness.
# ---------------------------------------------------------------------------


def test_next_build_emits_css_bundle_under_out_static(build_artifact):
    """``next build`` MUST produce at least one CSS bundle under
    ``out/_next/static/{css,chunks}/*.css``.

    The build pipeline is the only channel that ships the Tailwind 4
    stylesheet to FastAPI's StaticFiles mount (design.md §3.3.2.1 — G2
    contract). If no CSS file lands here, the React frontend ships with
    zero styles.
    """
    files = _css_files(build_artifact)
    assert files, (
        f"next build did NOT emit any CSS bundle under "
        f"{build_artifact / '_next' / 'static'}; the React "
        f"frontend would ship with zero styles"
    )


def test_compiled_css_contains_tailwind_preflight(build_artifact):
    """The compiled CSS MUST contain the Tailwind 4 preflight
    universal-selector rule — the canonical witness that
    ``@tailwindcss/postcss`` actually ran.

    Without the PostCSS plugin, Turbopack's default pipeline leaves the
    ``@import "tailwindcss";`` directive unresolved and the preflight is
    never emitted. The defect signature is a CSS bundle with zero
    ``box-sizing`` resets, no ``*, ::before, ::after`` universal
    selector, and the entire ``var(--token)`` cascade resolving to
    ``unset`` at runtime.
    """
    combined = _combined_css(build_artifact)
    assert TAILWIND_PREFLIGHT_RE.search(combined), (
        f"compiled CSS does NOT contain the Tailwind 4 preflight "
        f"universal-selector rule; @tailwindcss/postcss did not run "
        f"during next build. Most likely cause: postcss.config.mjs is "
        f"missing or does not register @tailwindcss/postcss. "
        f"Compiled CSS size: {len(combined)} bytes"
    )


def test_compiled_css_has_no_literal_theme_at_rule(build_artifact):
    """The compiled CSS MUST NOT contain the literal at-rule ``@theme {``.

    Tailwind 4 expands every ``@theme { … }`` block into a corresponding
    ``:root { … }`` declaration. A literal ``@theme {`` surviving into
    the bundle is the signature defect that proves the PostCSS plugin
    never ran — the browser silently drops the entire token palette
    because ``@theme`` is not a real CSS at-rule, and every legacy
    ``var(--primary)`` / ``var(--realm-*)`` reference resolves to
    ``unset`` at runtime.
    """
    combined = _combined_css(build_artifact)
    match = LITERAL_THEME_AT_RULE_RE.search(combined)
    assert match is None, (
        f"compiled CSS contains the LITERAL @theme at-rule "
        f"(position {match.start() if match else '?'}); "
        f"@tailwindcss/postcss did not expand it into :root. "
        f"The browser will silently drop every @theme token at runtime."
    )


def test_compiled_css_has_no_literal_tailwind_import(build_artifact):
    """The compiled CSS MUST NOT contain the literal substring
    ``@import "tailwindcss"``.

    Tailwind 4 inlines the entire ``@import "tailwindcss";`` directive
    (preflight + theme tokens + utility class surface) into the bundle.
    A literal ``@import "tailwindcss"`` surviving means the plugin never
    ran.
    """
    combined = _combined_css(build_artifact)
    match = LITERAL_IMPORT_RE.search(combined)
    assert match is None, (
        f"compiled CSS contains the LITERAL @import \"tailwindcss\" "
        f"directive (position {match.start() if match else '?'}); the "
        f"PostCSS plugin @tailwindcss/postcss is missing or did not run"
    )


# ---------------------------------------------------------------------------
# TRIANGULATE — negative-path / structural witnesses that protect the
# primary contract from accidental relaxation.
# ---------------------------------------------------------------------------


def test_triangulate_postcss_config_registers_tailwind_plugin_only():
    """``postcss.config.mjs`` MUST register ``@tailwindcss/postcss`` and
    MUST NOT register Tailwind 3-era plugins (``autoprefixer``,
    ``@tailwindcss/forms``) — the same ban ``tests/test_toolchain_bootstrap.py``
    enforces on the package.json dep side. This is the config-side
    triangulation: even if the dep were accidentally removed, the config
    would still pin the plugin; even if the config were accidentally
    expanded with legacy plugins, this test would catch it.
    """
    if not POSTCSS_CONFIG.is_file():
        pytest.fail(
            f"postcss.config.mjs missing at {POSTCSS_CONFIG} — PR 5.5 ships "
            f"the root postcss.config.mjs registering @tailwindcss/postcss"
        )
    raw = POSTCSS_CONFIG.read_text(encoding="utf-8")
    # Must reference the plugin (string or identifier).
    assert REQUIRED_POSTCSS_PLUGIN in raw, (
        f"postcss.config.mjs does not reference {REQUIRED_POSTCSS_PLUGIN!r}; "
        f"raw={raw!r}"
    )
    # Must NOT register Tailwind 3-era plugins.
    for forbidden in ("autoprefixer", "@tailwindcss/forms"):
        assert forbidden not in raw, (
            f"postcss.config.mjs registers the Tailwind 3-era plugin "
            f"{forbidden!r}; the PR 5.5 contract forbids legacy plugins. "
            f"raw={raw!r}"
        )


def test_triangulate_preflight_is_present_in_every_css_bundle(build_artifact):
    """The Tailwind 4 preflight rule MUST appear in every compiled CSS
    bundle — not just one. This catches the regression where Tailwind
    runs only on a subset of CSS imports (e.g. some globals.css chunks
    are processed, others bypass the plugin because the import chain
    doesn't reach them).
    """
    files = _css_files(build_artifact)
    assert files, "no compiled CSS files to inspect (precondition failed)"
    missing = [p for p in files if not TAILWIND_PREFLIGHT_RE.search(
        p.read_text(encoding="utf-8", errors="replace")
    )]
    assert not missing, (
        f"compiled CSS bundle(s) missing Tailwind preflight: "
        f"{[str(p.relative_to(REPO_ROOT)) for p in missing]}; "
        f"the plugin ran on a subset but not all bundles"
    )


def test_triangulate_theme_tokens_emitted_under_root_not_inside_theme_block(build_artifact):
    """The Tailwind-produced theme tokens MUST live under a ``:root``
    selector (Tailwind 4 expands every ``@theme { … }`` into ``:root { … }``).
    The legacy ``@theme { --primary: #1d7ea9; … }`` block MUST be expanded,
    not left in place. This is the byte-level confirmation that the
    PostCSS plugin's transformer ran on the @theme block end-to-end.
    """
    combined = _combined_css(build_artifact)
    # The legacy :root token palette includes #1d7ea9 (--primary). Tailwind 4
    # expands the @theme block into a ``@layer theme { :root, :host { …
    # --primary: #1d7ea9; … } }`` declaration (note the ``:root, :host``
    # selector list, not bare ``:root``). We pin the hex value (not the
    # CSS variable name) because the variable name depends on Tailwind 4's
    # expansion strategy and may vary across plugin versions.
    primary_hex_re = re.compile(
        r":root\s*,\s*:host\s*\{[^}]*--primary\s*:\s*#1d7ea9",
        re.IGNORECASE,
    )
    assert primary_hex_re.search(combined), (
        f"compiled CSS does NOT contain the legacy :root palette token "
        f"#1d7ea9 under a :root selector; the @theme block was not "
        f"expanded by @tailwindcss/postcss. Defect signature: the "
        f"hex value lives inside an unprocessed @theme block that the "
        f"browser will silently drop."
    )
