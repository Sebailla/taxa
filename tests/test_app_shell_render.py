"""App Router static-export contract tests for PR 3b.

Pins the G2 contract (design.md §3.3.2.1): ``next build`` with
``output: "export"`` produces ``out/index.html`` carrying ``<html lang="en">``,
the responsive viewport meta, and the Raleway ``<link rel="preload">`` emitted
by ``next/font/google``.

Strict-TDD contract for PR 3b (Phase 3b App Router static export). MUST fail
on a fresh PR-3b branch (no ``src/app/{layout,page}.tsx`` or
``next.config.mjs`` yet). Subsequent PRs (3c Tailwind, 4a/4b browser state,
5a/5b/5c ports) extend the markup contract; they do NOT alter this baseline.

Chain-topology guard: PR 3b MUST NOT import ``@taxa/app-shell`` (PR 4b),
``@taxa/browser-state`` (PR 4a), or ``./globals.css`` (PR 3c) — those owners
are later in the chain and an import here would invert its dependency order.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_LAYOUT = REPO_ROOT / "src" / "app" / "layout.tsx"
SRC_PAGE = REPO_ROOT / "src" / "app" / "page.tsx"
NEXT_CONFIG_MJS = REPO_ROOT / "next.config.mjs"
OUT_DIR = REPO_ROOT / "out"
OUT_INDEX = OUT_DIR / "index.html"
CHUNKS_CSS_GLOB = (REPO_ROOT / "out" / "_next" / "static" / "chunks").glob
CHUNKS_JS_GLOB = (REPO_ROOT / "out" / "_next" / "static" / "chunks").rglob

# Per-file forbidden imports — chain-topology guard for the migrated
# modular monolith.
#
# PR 4b integrates the AppShell into the App Router host. The integration
# seam lives in ``src/app/layout.tsx`` (the layout wraps ``{children}`` in
# ``<AppShell>...</AppShell>``). Layouts are allowed to import
# ``@taxa/app-shell``; pages are NOT — ``src/app/page.tsx`` must remain a
# pure content component (the AppShell is composed once at the layout level
# and every descendant inherits it). ``@taxa/browser-state`` stays
# transitive-only (the layout reaches the typed store via the AppShell, not
# via a direct import).
LAYOUT_FORBIDDEN_IMPORTS: tuple[tuple[str, str], ...] = (
    (r"""from\s+["']@taxa/browser-state""", "@taxa/browser-state"),
    (r"""from\s+["']\./globals\.css["']""", "./globals.css"),
)
PAGE_FORBIDDEN_IMPORTS: tuple[tuple[str, str], ...] = (
    (r"""from\s+["']@taxa/app-shell""", "@taxa/app-shell"),
    (r"""from\s+["']@taxa/browser-state""", "@taxa/browser-state"),
    (r"""from\s+["']\./globals\.css["']""", "./globals.css"),
)


def _read_text(path: Path) -> str:
    if not path.is_file():
        pytest.fail(f"required file missing: {path}")
    return path.read_text(encoding="utf-8")


def _parse_next_config() -> dict | None:
    """Pick the G2 knobs out of ``next.config.mjs`` by regex.

    Avoids spawning ``node`` so the test stays inside the PR-3b allowed edit
    surfaces (no helper file under ``scripts/``). The file MUST be a top-level
    ESM module whose default export is an object literal; Next.js does not
    pre-process these fields. Returns ``None`` when the file is missing.
    """
    if not NEXT_CONFIG_MJS.is_file():
        return None
    text = NEXT_CONFIG_MJS.read_text(encoding="utf-8")
    out: dict = {}
    m = re.search(r"""\boutput\s*:\s*["']([^"']+)["']""", text)
    if m:
        out["output"] = m.group(1)
    m = re.search(r"""\bimages\s*:\s*\{[^}]*\bunoptimized\s*:\s*(true|false)""", text, re.DOTALL)
    if m:
        out["images"] = {"unoptimized": m.group(1) == "true"}
    m = re.search(r"""\btrailingSlash\s*:\s*(true|false)""", text)
    if m:
        out["trailingSlash"] = m.group(1) == "true"
    m = re.search(r"""\breactStrictMode\s*:\s*(true|false)""", text)
    if m:
        out["reactStrictMode"] = m.group(1) == "true"
    if not out:
        pytest.fail(
            "next.config.mjs has no recognised G2 knob (output / images / "
            "trailingSlash / reactStrictMode)"
        )
    return out


@pytest.fixture(scope="module")
def built_index_html() -> str:
    """Run ``npx next build`` once per module and return the index.html body."""
    if not (REPO_ROOT / "node_modules" / ".bin" / "next").is_file() and shutil.which("next") is None:
        pytest.skip("next binary not installed — skip build witness during RED")
    proc = subprocess.run(
        ["npx", "--no-install", "next", "build"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"npx next build failed (rc={proc.returncode}); "
            f"stdout tail:\n{proc.stdout[-2000:]}\nstderr tail:\n{proc.stderr[-2000:]}"
        )
    if not OUT_INDEX.is_file():
        pytest.fail(f"next build did not produce {OUT_INDEX.relative_to(REPO_ROOT)}")
    return OUT_INDEX.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Source presence (RED gate)
# ---------------------------------------------------------------------------

def test_src_app_layout_exists():
    assert SRC_LAYOUT.is_file(), (
        f"missing {SRC_LAYOUT.relative_to(REPO_ROOT)} — PR 3b task 3b.2 must author the layout"
    )


def test_src_app_page_exists():
    assert SRC_PAGE.is_file(), (
        f"missing {SRC_PAGE.relative_to(REPO_ROOT)} — PR 3b task 3b.3 must author the page"
    )


def test_next_config_mjs_exists():
    assert NEXT_CONFIG_MJS.is_file(), (
        f"missing {NEXT_CONFIG_MJS.relative_to(REPO_ROOT)} — PR 3b task 3b.4 must author the config"
    )


# ---------------------------------------------------------------------------
# next.config.mjs contract (3b.4)
# ---------------------------------------------------------------------------

def test_next_config_output_is_export():
    cfg = _parse_next_config()
    if cfg is None:
        pytest.skip("next.config.mjs missing — skip during RED")
    assert cfg.get("output") == "export", (
        f"next.config.mjs must set output: 'export' (G2 contract); got {cfg.get('output')!r}"
    )


def test_next_config_images_unoptimized_true():
    cfg = _parse_next_config()
    if cfg is None:
        pytest.skip("next.config.mjs missing — skip during RED")
    images = cfg.get("images") or {}
    assert images.get("unoptimized") is True, (
        f"next.config.mjs must set images.unoptimized: true; got {images.get('unoptimized')!r}"
    )


def test_next_config_trailing_slash_false():
    cfg = _parse_next_config()
    if cfg is None:
        pytest.skip("next.config.mjs missing — skip during RED")
    assert cfg.get("trailingSlash") is False, (
        f"next.config.mjs must set trailingSlash: false; got {cfg.get('trailingSlash')!r}"
    )


def test_next_config_react_strict_mode_true():
    cfg = _parse_next_config()
    if cfg is None:
        pytest.skip("next.config.mjs missing — skip during RED")
    assert cfg.get("reactStrictMode") is True, (
        f"next.config.mjs must set reactStrictMode: true; got {cfg.get('reactStrictMode')!r}"
    )


# ---------------------------------------------------------------------------
# src/app/layout.tsx + src/app/page.tsx contracts (3b.1, 3b.5)
# ---------------------------------------------------------------------------

def test_layout_uses_next_font_for_raleway():
    text = _read_text(SRC_LAYOUT)
    if not text.strip():
        pytest.skip("layout.tsx is empty — skip during RED")
    assert re.search(r"""from\s+["']next/font/google["']""", text), (
        "layout.tsx must import from next/font/google"
    )
    assert re.search(r"\bRaleway\b", text), (
        "layout.tsx must reference the Raleway font (next/font/google)"
    )


@pytest.mark.parametrize(
    "src_path, label, forbidden_imports",
    [
        (SRC_LAYOUT, "layout.tsx", LAYOUT_FORBIDDEN_IMPORTS),
        (SRC_PAGE, "page.tsx", PAGE_FORBIDDEN_IMPORTS),
    ],
    ids=["layout", "page"],
)
def test_app_file_does_not_import_owners_of_later_prs(src_path, label, forbidden_imports):
    """Chain-topology guard: PR 3b MUST NOT import cross-module barrels
    owned by later PRs (``@taxa/app-shell`` → 4b, ``@taxa/browser-state`` →
    4a, ``./globals.css`` → 3c).

    PR 4b relaxes the layout guard for ``@taxa/app-shell`` — the
    AppShell integration seam lives in ``src/app/layout.tsx`` and the
    layout MUST reach the barrel. The page guard is unchanged: pages
    stay pure content components and inherit the AppShell from the
    layout, never importing it directly. ``@taxa/browser-state`` stays
    forbidden for both files — the typed store is consumed transitively
    via the AppShell, not via a direct barrel import. ``./globals.css``
    stays forbidden for both files (the layout uses the
    ``import "./globals.css"`` syntax, not ``from "./globals.css"``,
    so this regex never matches the G3-a layout import)."""
    text = _read_text(src_path)
    for pattern, owner in forbidden_imports:
        assert not re.search(pattern, text), (
            f"{label} MUST NOT import {owner} — that module's owner is a later PR in the chain"
        )


# ---------------------------------------------------------------------------
# Build witness — out/index.html (3b.1)
# ---------------------------------------------------------------------------

def test_out_index_html_has_html_lang_en(built_index_html):
    assert re.search(r"""<html\s[^>]*lang=["']en["']""", built_index_html), (
        'out/index.html must declare <html lang="en"> (G2 contract)'
    )


def test_out_index_html_has_viewport_meta(built_index_html):
    assert re.search(
        r"""<meta\s+name=["']viewport["']\s+content=["']width=device-width,\s*initial-scale=1["']""",
        built_index_html,
    ), (
        'out/index.html must declare <meta name="viewport" '
        'content="width=device-width, initial-scale=1"> (G2 contract)'
    )


def test_out_index_html_has_raleway_preload(built_index_html):
    """Next.js 16 hashes font URLs so the literal "Raleway" is NOT in the
    preload href. The G2 signature is the *combination* of (a) a Raleway CSS
    class on ``<html>``, (b) a ``<link rel="preload" as="font" type="font/woff2">``,
    and (c) ``@font-face{font-family:Raleway}`` rules in the CSS chunk.
    Asserting all three proves the preload IS for Raleway."""
    html_match = re.search(r"""<html\b[^>]*class=["']([^"']+)["']""", built_index_html)
    assert html_match, "out/index.html must carry a class attribute on <html>"
    assert "raleway" in html_match.group(1).lower(), (
        f"<html> must carry a Raleway CSS class from next/font/google; got {html_match.group(1)!r}"
    )
    assert re.search(
        r"""<link\b[^>]*rel=["']preload["'][^>]*as=["']font["'][^>]*type=["']font/woff2["']""",
        built_index_html,
    ), 'out/index.html must contain <link rel="preload" as="font" type="font/woff2">'
    css_chunks = sorted(CHUNKS_CSS_GLOB("*.css"))
    assert css_chunks, "static export must emit a CSS chunk under out/_next/static/chunks/"
    css_body = "\n".join(c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks)
    assert "@font-face" in css_body and "font-family:Raleway" in css_body, (
        "CSS chunk must declare @font-face rules for the Raleway family"
    )


# ---------------------------------------------------------------------------
# Build manifest + body / chunk purity (3b.5 triangulation)
# ---------------------------------------------------------------------------

def test_build_manifest_records_app_router_page(built_index_html):
    """Next 16 stages the manifest at ``out/_next/static/<buildId>/_buildManifest.js``.

    design.md §3.3.2.1 mentions ``out/.next/build-manifest.json`` — that path
    predates the static-export location change. The *contract* is unchanged:
    the App Router recognised the page and recorded it in ``sortedPages``.
    """
    candidates = list((OUT_DIR / "_next" / "static").glob("*/_buildManifest.js"))
    assert candidates, "missing out/_next/static/<buildId>/_buildManifest.js"
    text = candidates[0].read_text(encoding="utf-8")
    sorted_pages_match = re.search(r'"sortedPages"\s*:\s*\[([^\]]*)\]', text)
    assert sorted_pages_match, "_buildManifest.js must declare a sortedPages array"
    assert sorted_pages_match.group(1).strip(), (
        f"_buildManifest.js::sortedPages is empty — src/app/page.tsx was not registered"
    )


def test_out_index_html_body_has_no_data_theme_before_hydration(built_index_html):
    """First paint MUST NOT carry ``data-theme`` — localStorage reads are reserved for PR 4b.

    PR 3b's hydration-safety contract: pre-hydration markup cannot depend on
    persisted state, otherwise SSR and CSR diverge and React warns. The
    hydration-guard implementation lands with PR 4b; PR 3b's job is to
    guarantee the bootstrap doesn't pre-empt it.
    """
    body_match = re.search(r"<body[^>]*>", built_index_html)
    assert body_match, "out/index.html must contain a <body> opening tag"
    assert "data-theme" not in body_match.group(0), (
        f"<body> must not carry data-theme before hydration (PR 4b concern); got: {body_match.group(0)}"
    )


def test_out_next_static_chunks_reference_no_browser_state(built_index_html):
    """Static-export chunks MUST NOT bundle ``@taxa/browser-state`` imports.

    PR 4b relaxation: chunks MAY reference ``@taxa/app-shell`` because
    the AppShell integration seam lives in the layout. The chain-topology
    guard that survives this PR is the ``@taxa/browser-state`` alias —
    that import path stays behind the AppShell barrel and must never be
    inlined into the static-export chunks.
    """
    chunks_dir = REPO_ROOT / "out" / "_next" / "static" / "chunks"
    js_files = sorted(CHUNKS_JS_GLOB("*.js"))
    assert chunks_dir.is_dir(), "missing out/_next/static/chunks — static export produced no JS chunks"
    assert js_files, "static export must emit at least one JS chunk under out/_next/static/chunks/"
    for js in js_files:
        body = js.read_text(encoding="utf-8", errors="ignore")
        assert "@taxa/browser-state" not in body, (
            f"{js.relative_to(REPO_ROOT)} references @taxa/browser-state — that alias is reserved for PR 4a"
        )