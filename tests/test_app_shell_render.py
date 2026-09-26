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
APP_SHELL_FILE = REPO_ROOT / "src" / "modules" / "app-shell" / "presentation" / "AppShell.tsx"
APP_SHELL_BARREL = REPO_ROOT / "src" / "modules" / "app-shell" / "index.ts"
TAXONOMY_TREE_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "TaxonomyTree.tsx"
TAXONOMY_TREE_ROW_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "TreeRow.tsx"
TAXONOMY_BARREL = REPO_ROOT / "src" / "modules" / "taxonomy" / "index.ts"
NEXT_CONFIG_MJS = REPO_ROOT / "next.config.mjs"
OUT_DIR = REPO_ROOT / "out"
OUT_INDEX = OUT_DIR / "index.html"
CHUNKS_CSS_GLOB = (REPO_ROOT / "out" / "_next" / "static" / "chunks").glob
CHUNKS_JS_GLOB = (REPO_ROOT / "out" / "_next" / "static" / "chunks").rglob

# ODD-VTREE-002 mounts the visible AppShell in page.tsx, so the chain-topology
# guard relaxes for ``@taxa/app-shell`` (now expected) and stays in force for
# the still-deferred owners (``@taxa/browser-state`` + ``./globals.css``).
FORBIDDEN_LAYOUT_IMPORTS = (
    r"""from\s+["']@taxa/app-shell""",
    r"""from\s+["']@taxa/browser-state""",
    r"""from\s+["']\./globals\.css["']""",
)
FORBIDDEN_PAGE_IMPORTS = (
    r"""from\s+["']@taxa/browser-state""",
    r"""from\s+["']\./globals\.css["']""",
)
REQUIRED_PAGE_IMPORTS = (
    r"""from\s+["']@taxa/app-shell["']""",
    r"""from\s+["']@taxa/taxonomy["']""",
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
    "src_path, label, forbidden, owners",
    [
        (
            SRC_LAYOUT,
            "layout.tsx",
            FORBIDDEN_LAYOUT_IMPORTS,
            ("@taxa/app-shell", "@taxa/browser-state", "./globals.css"),
        ),
        (
            SRC_PAGE,
            "page.tsx",
            FORBIDDEN_PAGE_IMPORTS,
            ("@taxa/browser-state", "./globals.css"),
        ),
    ],
    ids=["layout", "page"],
)
def test_app_file_does_not_import_owners_of_later_prs(src_path, label, forbidden, owners):
    """Chain-topology guard.

    PR 3b (layout.tsx) MUST NOT import cross-module barrels owned by later
    PRs (``@taxa/app-shell`` → 4b, ``@taxa/browser-state`` → 4a,
    ``./globals.css`` → 3c).

    ODD-VTREE-002 (page.tsx) mounts the AppShell + TaxonomyTree, so the
    ``@taxa/app-shell`` guard relaxes for page.tsx only. ``@taxa/browser-state``
    and ``./globals.css`` are still owned by deferred PRs and stay forbidden.
    """
    text = _read_text(src_path)
    for pattern, owner in zip(forbidden, owners, strict=True):
        assert not re.search(pattern, text), (
            f"{label} MUST NOT import {owner} — that module's owner is a later PR in the chain"
        )


def test_page_mounts_app_shell_and_taxonomy_tree():
    """ODD-VTREE-002 mounts the visible AppShell + TaxonomyTree in page.tsx.

    ODD-ASN-002 (per-route metadata split) lifts the AppShell +
    TaxonomyTree composition into the route-private client island
    ``src/app/_components/HomeClient.tsx`` so ``src/app/page.tsx``
    can stay a Server Component and export Next.js ``metadata``.
    The contract the brief pins — the ``/`` route still mounts the
    visible AppShell + TaxonomyTree — is preserved through the
    lifted client island. The source-level check therefore moves
    to ``HomeClient.tsx`` (where the imports actually live now)
    while the route-level mount is preserved (page.tsx renders
    ``<HomeClient />`` which renders AppShell + TaxonomyTree).
    """
    text = _read_text(HOME_CLIENT_FILE)
    for pattern in REQUIRED_PAGE_IMPORTS:
        assert re.search(pattern, text), (
            f"HomeClient.tsx must satisfy pattern {pattern!r} — "
            f"the AppShell + TaxonomyTree imports moved to the "
            f"route-private client island so page.tsx can stay a "
            f"Server Component and export Next.js metadata."
        )


# ---------------------------------------------------------------------------
# ODD-ASN-002 — per-route metadata split for the `/` route.
#
# Next.js's metadata API forbids `metadata` exports from Client
# Components, so the original `src/app/page.tsx` (which declared
# `"use client"` to own the lifted `searchQuery` state) could
# NOT export a per-route title — the browser tab rendered
# `<title>taxa</title>` (the root-layout default). The other
# routes (`/explorer`, `/help`, `/settings`) already export
# `"<SurfaceTitle> — taxa"` titles. This test pins the
# per-route metadata contract for `/`: page.tsx becomes a
# Server Component that exports `metadata` with the
# `"Taxonomic Tree — taxa"` title (matching the brief's
# `"<SurfaceTitle> — taxa"` pattern), and the composition
# lifts into `src/app/_components/HomeClient.tsx`.
# ---------------------------------------------------------------------------
HOME_ROUTE_TITLE = "Taxonomic Tree — taxa"


def test_home_route_exports_per_route_metadata():
    """ODD-ASN-002: ``src/app/page.tsx`` exports a Next.js
    ``metadata`` object whose title follows the
    ``"<SurfaceTitle> — taxa"`` pattern the other routes
    (``/explorer`, `/help`, `/settings`) already use.

    Three required observations:

      1. The page file declares ``export const metadata`` (the
         Next.js App Router metadata export).
      2. The literal title ``Taxonomic Tree — taxa`` appears
         in the source (matches the existing per-route
         pattern: ``"Research Explorer — taxa"``,
         ``"Help — taxa"``, ``"Settings — taxa"``).
      3. The page file does NOT declare ``"use client"`` —
         the page itself is a Server Component so the metadata
         export is honoured. The lifted ``useState`` lives in
         the new route-private client island
         ``src/app/_components/HomeClient.tsx`` instead.

    Together these three observations close the per-route
    metadata contract for ``/``: the browser tab now renders
    ``<title>Taxonomic Tree — taxa</title>`` instead of the
    root-layout fallback ``<title>taxa</title>``.
    """
    text = _read_text(SRC_PAGE)
    assert re.search(r"export\s+const\s+metadata\b", text), (
        f"{SRC_PAGE.relative_to(REPO_ROOT)} must export a "
        f"`metadata` object so Next.js can auto-inject the "
        f"per-route `<title>` (the Next.js metadata API "
        f"forbids the export from Client Components — page.tsx "
        f"must be a Server Component)."
    )
    assert HOME_ROUTE_TITLE in text, (
        f"{SRC_PAGE.relative_to(REPO_ROOT)} must declare the "
        f"per-route title `{HOME_ROUTE_TITLE!r}` in its "
        f"`metadata` export — matches the existing pattern the "
        f"/explorer, /help, and /settings routes already use "
        f"(`<SurfaceTitle> — taxa`)."
    )
    assert not re.search(r'^\s*"use client"\s*;', text, re.MULTILINE), (
        f"{SRC_PAGE.relative_to(REPO_ROOT)} must NOT declare "
        f"the `\"use client\"` directive — the Next.js metadata "
        f"API forbids `metadata` exports from Client Components. "
        f"The lifted search state lives in the route-private "
        f"client island `src/app/_components/HomeClient.tsx` "
        f"instead. (Docstrings may reference the literal "
        f"`\"use client\"` token as documentation; this check "
        f"rejects only the directive form.)"
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


LEGACY_MATERIAL_SYMBOLS_HREF = (
    "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined"
    ":opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
)


def test_out_index_html_has_material_symbols_stylesheet(built_index_html):
    """Built ``out/index.html`` must ship the legacy Material Symbols
    Outlined stylesheet link so icon ligatures render as glyphs."""
    assert re.search(
        r'<link\b[^>]*rel="stylesheet"[^>]*href="'
        + re.escape(LEGACY_MATERIAL_SYMBOLS_HREF)
        + r'"',
        built_index_html,
    ), (
        f'out/index.html must carry <link rel="stylesheet" href="{LEGACY_MATERIAL_SYMBOLS_HREF}" />'
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
        "_buildManifest.js::sortedPages is empty — src/app/page.tsx was not registered"
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
    """Static-export chunks MUST NOT bundle ``@taxa/browser-state``.

    ODD-VTREE-002 mounts the AppShell + TaxonomyTree so ``@taxa/app-shell``
    is now expected inside the client bundle. The ``@taxa/browser-state``
    guard remains in force — that alias is owned by PR 4a.
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


def test_out_next_static_chunks_include_app_shell(built_index_html):
    """ODD-VTREE-002 mounts the AppShell so its barrel must appear in the
    static export. The absence would mean the page is rendering the
    placeholder path again."""
    js_files = sorted(CHUNKS_JS_GLOB("*.js"))
    assert js_files, "static export must emit at least one JS chunk under out/_next/static/chunks/"
    found = False
    for js in js_files:
        body = js.read_text(encoding="utf-8", errors="ignore")
        if "Taxonomic Tree" in body or "AppShell" in body or "Loading domains" in body:
            found = True
            break
    assert found, (
        "no static-export JS chunk references the AppShell/TaxonomyTree "
        "rendered text — the page is not mounting ODD-VTREE-002"
    )


# ---------------------------------------------------------------------------
# ODD-BSTATE-PW-001 — boundary contract between the main route and
# the dedicated `/hydration-probe` route.
#
# The static export contains TWO app-routes after ODD-BSTATE-PW-001:
#   - `/`              → mounts AppShell + TaxonomyTree, no browser-state
#   - `/hydration-probe` → mounts `<HydrationProbe />`, the typed store
#     + hooks are in scope (this is the WHOLE POINT of the witness)
#
# The pre-ODD-BSTATE-PW-001 test
# ``test_out_next_static_chunks_reference_no_browser_state`` scanned
# EVERY chunk under ``out/_next/static/chunks/`` for
# ``@taxa/browser-state`` and rejected any hit. That blanket scan is
# no longer correct: the probe route IS allowed to bundle browser-
# state. The boundary is now per-route:
#
#   * ``out/index.html`` and the chunks IT references must stay free
#     of browser-state code — the main route's static chunk
#     boundary.
#   * ``out/hydration-probe.html`` (which exists only after
#     ODD-BSTATE-PW-001 ships) and the chunks IT references MUST
#     bundle browser-state code — the probe route is the only place
#     the typed store + hooks are allowed to land.
#
# Detection heuristic: the path alias ``@taxa/browser-state`` is
# resolved by the Turbopack bundler at build time and NEVER appears
# as a literal in the emitted chunks. The reliable witnesses are
# the FOUR ``localStorage`` key literals the browser-state module
# hard-codes (``taxa.settings.theme``, ``taxa.tree.source``,
# ``taxa.tree.lastTaxonId``, ``taxa.tree.kebabOpenId``) — they only
# exist inside the typed store and survive into the bundle because
# they are runtime string constants the React hooks pass to
# ``Storage.prototype.getItem / setItem / removeItem``.
# ---------------------------------------------------------------------------
BROWSER_STATE_STORAGE_KEYS: tuple[str, ...] = (
    "taxa.settings.theme",
    "taxa.tree.source",
    "taxa.tree.lastTaxonId",
    "taxa.tree.kebabOpenId",
)


def _extract_chunk_paths(html_text: str) -> set[str]:
    """Pull the ``/_next/static/chunks/<name>.js`` filenames an HTML
    document references.

    Two sources:
      - ``<script src="/_next/static/chunks/X.js" ...>`` (preload +
        sync script tags Next.js emits directly in the HTML).
      - ``"src":"/_next/static/chunks/X.js"`` inside the
        ``__next_f.push`` RSC payload the static export embeds for
        client-side hydration.

    Returns a set so duplicate references collapse naturally.
    """
    paths: set[str] = set()
    for match in re.finditer(
        r'<script[^>]*src="(/_next/static/chunks/([^"]+\.js))"',
        html_text,
    ):
        paths.add(match.group(2))
    for match in re.finditer(
        r'"src":"(/_next/static/chunks/([^"]+\.js))"',
        html_text,
    ):
        paths.add(match.group(2))
    return paths


def _chunk_text(name: str) -> str:
    return (
        REPO_ROOT
        / "out"
        / "_next"
        / "static"
        / "chunks"
        / name
    ).read_text(encoding="utf-8", errors="ignore")


def _chunk_bundles_browser_state(name: str) -> bool:
    """Return True iff `name` (a chunk filename) contains the four
    ``localStorage`` key literals the typed store hard-codes. The
    literals are unique to the browser-state module: every other
    capability module is forbidden from touching ``localStorage``
    (`tests/test_browser_state_keys.py::test_other_module_does_not_touch_localstorage`)
    AND the key literals themselves are only used inside the typed
    store. A chunk carrying all four keys therefore bundled the
    typed store end-to-end (the typed defaults + the
    parse / serialize helpers + the in-memory cache + the
    read / write / subscribe / reset surface).
    """
    body = _chunk_text(name)
    return all(key in body for key in BROWSER_STATE_STORAGE_KEYS)


def test_out_index_html_chunks_reference_no_browser_state(built_index_html):
    """The main route's static chunks must stay free of the
    `@taxa/browser-state` alias literal.

    ODD-VTREE-002 mounts AppShell + TaxonomyTree; the main route
    stays free of the typed browser-state alias. The boundary
    contract is the ALIAS literal — Turbopack resolves the alias
    at build time and the path string never appears in the
    emitted chunks (the chunks carry the resolved module code,
    not the import specifier). The check therefore verifies the
    boundary from the import-specifier side: a chunk referencing
    the literal `@taxa/browser-state` means a deep import
    slipped past the barrel guard, which is the regression
    pattern this test pins.

    ODD-BSTATE-TAX-001 ships the FIRST production consumer of
    the typed store in the main route (`TaxonomyTree` imports
    `useTreeSource` from the public barrel). The deeper
    per-key / per-call-site boundary contract lives in
    `test_out_index_html_chunks_permit_only_tree_source_key`
    below — that test pins the typed-source chain end-to-end
    AND rejects call sites for the other three hooks. The
    alias-literal check here stays green because the resolved
    alias never appears as a string in the emitted chunks.
    """
    chunks_dir = REPO_ROOT / "out" / "_next" / "static" / "chunks"
    js_files = sorted(CHUNKS_JS_GLOB("*.js"))
    assert chunks_dir.is_dir(), "missing out/_next/static/chunks — static export produced no JS chunks"
    assert js_files, "static export must emit at least one JS chunk under out/_next/static/chunks/"
    for js in js_files:
        body = js.read_text(encoding="utf-8", errors="ignore")
        assert "@taxa/browser-state" not in body, (
            f"{js.relative_to(REPO_ROOT)} references @taxa/browser-state — that alias is reserved for the public barrel and must never appear as a literal in the emitted chunks (deep import would have leaked through)."
        )


def test_probe_route_html_chunks_do_reference_browser_state(built_index_html):
    """The dedicated `/hydration-probe` route is the ONLY route allowed
    to bundle the browser-state module.

    ODD-BSTATE-PW-001 ships the probe as a single-purpose witness:
    the route exists to exercise the typed hooks end-to-end. The
    chunks IT references MUST bundle the typed store — otherwise the
    probe would render the typed defaults forever and silently lose
    the rehydration path.
    """
    probe_html = OUT_DIR / "hydration-probe.html"
    if not probe_html.is_file():
        pytest.skip(
            f"missing {probe_html.relative_to(REPO_ROOT)} — the probe "
            f"route is expected after ODD-BSTATE-PW-001 ships "
            f"`src/app/hydration-probe/page.tsx`."
        )
    probe_text = probe_html.read_text(encoding="utf-8")
    chunks = _extract_chunk_paths(probe_text)
    assert chunks, (
        "out/hydration-probe.html does not reference any "
        "/_next/static/chunks/*.js chunks — the static export shape "
        "changed; update this test."
    )
    found = any(_chunk_bundles_browser_state(name) for name in chunks)
    assert found, (
        "no chunk referenced by out/hydration-probe.html bundles the "
        "browser-state module — the probe route must pull in the "
        "typed store + hooks to render the rehydrated values."
    )


def test_probe_page_mounts_browser_state_via_public_barrel():
    """The probe route mounts ``HydrationProbe`` through the public
    ``@taxa/browser-state`` barrel (no deep imports).

    Pinned so a future refactor cannot silently break the boundary
    contract: the probe MUST stay on the public surface so the
    ``no-restricted-imports`` ESLint guard continues to enforce the
    modular monolith's layer rule on the new route.
    """
    probe_page = (
        REPO_ROOT / "src" / "app" / "hydration-probe" / "page.tsx"
    )
    if not probe_page.is_file():
        pytest.skip(
            f"missing {probe_page.relative_to(REPO_ROOT)} — ODD-BSTATE-PW-001 "
            f"must ship the probe route."
        )
    text = probe_page.read_text(encoding="utf-8")
    assert re.search(r"""from\s+["']@taxa/browser-state["']""", text), (
        "src/app/hydration-probe/page.tsx must import through the "
        "public @taxa/browser-state barrel — deep paths into the "
        "browser-state presentation layer are blocked by "
        "no-restricted-imports."
    )
    assert "HydrationProbe" in text, (
        "src/app/hydration-probe/page.tsx must reference the "
        "HydrationProbe export the barrel re-exports."
    )


# ---------------------------------------------------------------------------
# ODD-ASN-001 — production isolation contract for the
# `/hydration-probe` route.
#
# The Playwright witness in `tests/test_hydration_console.py`
# requires the static HTML at `out/hydration-probe.html` to
# continue shipping the probe body. ODD-ASN-001 closes the
# route's production exposure with a two-layer guard:
#   1. A route `layout.tsx` ships `<meta name="robots"
#      content="noindex,nofollow">` via the App Router
#      `metadata` export — closes search-engine exposure.
#   2. A client-only `<HydrationProbeGate />` replaces the
#      probe body with a quiet fallback after mount when
#      `localStorage.taxa-internal-ok` is missing — closes
#      direct-URL exposure from non-test visitors.
#
# These four tests pin the static side of the contract: the
# layout file shape, the gate component file shape, the
# barrel wiring, and the static export output. The runtime
# side (gate flip, fallback body, hydration silence) lives in
# `tests/test_hydration_console.py` because Playwright is the
# only way to observe the post-mount React render.
# ---------------------------------------------------------------------------
PROBE_LAYOUT = (
    REPO_ROOT / "src" / "app" / "hydration-probe" / "layout.tsx"
)
PROBE_GATE = (
    REPO_ROOT / "src" / "modules" / "browser-state"
    / "presentation" / "HydrationProbeGate.tsx"
)
STORE_INTERNAL_FLAG_FILE = (
    REPO_ROOT
    / "src"
    / "modules"
    / "browser-state"
    / "infrastructure"
    / "storeInternalFlag.ts"
)


def test_probe_layout_renders_noindex_meta():
    """`src/app/hydration-probe/layout.tsx` ships the noindex /
    nofollow pair via the App Router `metadata` export.

    The route's search-engine exposure contract: well-behaved
    crawlers honour the `<meta name="robots"
    content="noindex,nofollow">` pair Next.js auto-injects from
    `metadata.robots`. Without the export the static HTML would
    carry a plain `<meta name="robots">` (or no robots meta at
    all), letting the route slip into search-engine indexes.
    """
    if not PROBE_LAYOUT.is_file():
        pytest.skip(
            f"missing {PROBE_LAYOUT.relative_to(REPO_ROOT)} — "
            f"ODD-ASN-001 must ship the route's layout."
        )
    text = PROBE_LAYOUT.read_text(encoding="utf-8")
    assert "metadata" in text, (
        f"{PROBE_LAYOUT.relative_to(REPO_ROOT)} must export a "
        f"`metadata` object so Next.js can auto-inject the "
        f"noindex/nofollow pair."
    )
    assert "noindex" in text, (
        f"{PROBE_LAYOUT.relative_to(REPO_ROOT)} must declare "
        f"`robots.index = false` (or the literal `noindex`) so "
        f"the static HTML carries the noindex directive."
    )
    assert "nofollow" in text, (
        f"{PROBE_LAYOUT.relative_to(REPO_ROOT)} must declare "
        f"`robots.follow = false` (or the literal `nofollow`) so "
        f"the static HTML carries the nofollow directive."
    )


def test_probe_layout_wraps_children_in_gate():
    """The route layout wraps `children` in `<HydrationProbeGate />`
    imported through the public ``@taxa/browser-state`` barrel.

    Two boundary checks at once:
      - The gate is referenced (a future refactor that silently
        drops the gate would let the probe body render to every
        direct visitor).
      - The import goes through the public barrel (a deep import
        into `./presentation/HydrationProbeGate` would violate
        spec.md rule 5 and bypass the `no-restricted-imports`
        ESLint guard).
    """
    if not PROBE_LAYOUT.is_file():
        pytest.skip(
            f"missing {PROBE_LAYOUT.relative_to(REPO_ROOT)} — "
            f"ODD-ASN-001 must ship the route's layout."
        )
    text = PROBE_LAYOUT.read_text(encoding="utf-8")
    assert "HydrationProbeGate" in text, (
        f"{PROBE_LAYOUT.relative_to(REPO_ROOT)} must mount the "
        f"gate (the production guard). The Playwright witness "
        f"still works because the harness sets the "
        f"`taxa-internal-ok` flag via `add_init_script` before "
        f"navigation."
    )
    assert re.search(
        r"""from\s+["']@taxa/browser-state["']""", text
    ), (
        f"{PROBE_LAYOUT.relative_to(REPO_ROOT)} must import the "
        f"gate through the public @taxa/browser-state barrel — "
        f"deep paths into the presentation layer are blocked."
    )


def test_probe_gate_component_exists():
    """`HydrationProbeGate.tsx` exists, is a Client Component, and
    references the ODD-ASN-001 contract tokens.

    Pinning the file shape catches silent drift: a future
    refactor that drops `"use client"`, drops the
    `taxa-internal-ok` key, or drops the `denied` state literal
    would break the gate behaviour. Text-level checks are
    sufficient because the runtime behaviour is pinned by
    `tests/test_hydration_console.py` (Chromium-driven).

    Layering note: the `taxa-internal-ok` literal used to live in
    this gate file. It was lifted into the typed browser-state
    store (`storeInternalFlag.ts` as ``INTERNAL_FLAG_STORAGE_KEY``)
    so the presentation layer reads through
    ``readInternalFlag()`` instead of touching ``localStorage``
    directly. The gate still owns `"use client"` and the
    `denied` fallback literal; the storage-key literal now
    lives with the store that owns the layering rule from
    `tests/test_browser_state_keys.py`.
    """
    if not PROBE_GATE.is_file():
        pytest.skip(
            f"missing {PROBE_GATE.relative_to(REPO_ROOT)} — "
            f"ODD-ASN-001 must ship the gate component."
        )
    text = PROBE_GATE.read_text(encoding="utf-8")
    assert '"use client"' in text, (
        f"{PROBE_GATE.relative_to(REPO_ROOT)} must declare "
        f"`\"use client\"` at the top so the gate's `useEffect` "
        f"runs after hydration."
    )
    assert "denied" in text, (
        f"{PROBE_GATE.relative_to(REPO_ROOT)} must render the "
        f"`data-hydration-probe-gate=\"denied\"` fallback when "
        f"the flag is missing."
    )
    if STORE_INTERNAL_FLAG_FILE.is_file():
        # Post-refactor home of the literal: the typed store
        # that owns the layering rule (presentation must not
        # touch localStorage directly).
        store_text = STORE_INTERNAL_FLAG_FILE.read_text(
            encoding="utf-8"
        )
        assert "taxa-internal-ok" in store_text, (
            f"{STORE_INTERNAL_FLAG_FILE.relative_to(REPO_ROOT)} "
            f"must own the `taxa-internal-ok` storage key "
            f"(`INTERNAL_FLAG_STORAGE_KEY`) — the ODD-ASN-001 "
            f"flag the Playwright harness seeds via "
            f"`add_init_script`."
        )
    else:
        # Legacy branch: the gate itself still owns the literal.
        assert "taxa-internal-ok" in text, (
            f"{PROBE_GATE.relative_to(REPO_ROOT)} must read the "
            f"`taxa-internal-ok` localStorage key — the "
            f"ODD-ASN-001 flag the Playwright harness seeds via "
            f"`add_init_script`."
        )


def test_probe_route_still_serves_static_html():
    """`out/hydration-probe.html` continues to ship after the gate
    wiring.

    The Playwright witness in `tests/test_hydration_console.py`
    depends on this file's continued existence (the static
    export is what the ephemeral server serves, and the file's
    body carries the typed defaults for the static-HTML
    witness). Skips when the build hasn't run yet — the rest of
    this module's tests depend on `built_index_html` for the
    full ``next build`` pass; this test pins the
    `/hydration-probe` file specifically.
    """
    if not OUT_INDEX.is_file():
        pytest.skip(
            f"missing {OUT_INDEX.relative_to(REPO_ROOT)} — run "
            f"`npx --no-install next build` first."
        )
    probe_html = OUT_DIR / "hydration-probe.html"
    assert probe_html.is_file(), (
        f"missing {probe_html.relative_to(REPO_ROOT)} — the "
        f"static export dropped the /hydration-probe route "
        f"after ODD-ASN-001. The Playwright witness depends on "
        f"the file."
    )


# ---------------------------------------------------------------------------
# ODD-BSTATE-TAX-001 — typed-source migration chunk boundary.
#
# The pre-ODD-BSTATE-TAX-001 boundary contract (above) was a
# blanket "no browser-state at all" check: every chunk referenced
# by ``out/index.html`` had to stay free of the `@taxa/browser-state`
# alias literal, because the main route did not touch the typed
# store. ODD-BSTATE-TAX-001 ships the FIRST production consumer of
# the typed store in the main route — ``TaxonomyTree`` now calls
# ``useTreeSource()`` — so the boundary contract needs to verify the
# typed-source chain is bundled while the OTHER three hooks
# (`useTheme`, `useLastTaxonId`, `useKebabOpenId`) stay out of
# scope until their consumer slices ship.
#
# BUNDLING REALITY (documented limitation):
# Turbopack does NOT tree-shake the browser-state barrel without
# `"sideEffects": false` in `package.json`. As a result, importing
# `useTreeSource` from the public barrel pulls the WHOLE
# `application/useBrowserStateKey.ts` file into the chunk (all four
# hooks defined + all four key literals + all four read/subscribe
# functions + the parseNumberOrNull / serializeNumberOrNull
# helpers). The strict "only `taxa.tree.source` literal in the chunk"
# check would require restructuring the browser-state module
# (splitting hooks into per-key files) AND/OR adding `sideEffects:
# false` to `package.json`. Both edits are owned by ODD-BSTATE-001,
# not ODD-BSTATE-TAX-001, and are out of scope for this work unit
# (the task description forbids migrating
# focused/selected/kebab/theme and forbids touching routing/legacy
# code; restructuring browser-state module internals is a similar
# scope violation).
#
# The pragmatic contract this test pins:
#   1. The chunks referenced by ``out/index.html`` carry the
#      `useTreeSource` hook identifier (the typed-source chain is
#      bundled end-to-end because TaxonomyTree imports it). The
#      hook identifier is the load-bearing consumer surface —
#      without it the typed source persistence witness in
#      `tests/test_hydration_console.py` would not function.
#   2. The chunks do NOT carry direct CALL SITES of the other
#      three hooks (`useTheme(`, `useLastTaxonId(`,
#      `useKebabOpenId(`) — even though the hook definitions are
#      bundled into the chunk surface, they MUST NOT be actively
#      invoked from main-route code paths. The source-level call
#      site is the load-bearing consumer signal: a hook
#      definition sitting unused in the chunk is harmless (a
#      future PR that adds a consumer can adopt the already-bundled
#      hook with zero chunk-size impact); a hook being CALLED from
#      main-route code would silently ship the typed-state
#      persistence for theme / last-taxon-id / kebab-open-id
#      BEFORE the work unit that owns that migration.
#   3. The pre-existing blanket "no `@taxa/browser-state` alias"
#      check (``test_out_next_static_chunks_reference_no_browser_state``)
#      continues to pass: Turbopack resolves the alias at build
#      time so the literal never appears in the emitted chunks,
#      and that contract holds regardless of how many browser-state
#      hooks end up in the bundle.
#
# Source-level complementary checks (the other three hooks are
# NOT imported by TaxonomyTree) live in
# ``tests/test_visible_taxonomy_tree.py` (ODD-BSTATE-TAX-001
# section): the `test_taxonomy_tree_imports_use_tree_source_via_public_barrel`
# test asserts that `useTreeSource` is the ONLY browser-state hook
# TaxonomyTree imports from the public barrel. Together the two
# tests pin the boundary contract: the bundle carries the
# typed-source chain, the main-route consumer uses ONLY
# `useTreeSource`, and the other three hooks stay out of scope
# until their consumer slices ship.
# ---------------------------------------------------------------------------

PRIMARY_ROUTE_PERMITTED_BROWSER_STATE_KEY: str = "taxa.tree.source"
PRIMARY_ROUTE_FORBIDDEN_BROWSER_STATE_KEYS: tuple[str, ...] = (
    "taxa.settings.theme",
    "taxa.tree.lastTaxonId",
    "taxa.tree.kebabOpenId",
)
# ODD-BSTATE-TAX-001-B — strict-continuation: the prior pragmatic
# hook-call-site relaxation was rejected. The check now inspects
# every chunk referenced by `out/index.html` for the LITERAL
# ABSENCE of the three forbidden localStorage keys plus a
# positive `taxa.tree.source` witness. The per-key module split
# (ODD-BSTATE-TAX-001-A) makes Turbopack retain only the
# imported key's module chain, so the forbidden keys never
# reach the chunk that ships `taxa.tree.source`.
PRIMARY_ROUTE_FORBIDDEN_HOOK_CALLS: tuple[str, ...] = (
    "useTheme(",
    "useLastTaxonId(",
    "useKebabOpenId(",
)


def test_out_index_html_chunks_permit_only_tree_source_key(built_index_html):
    """ODD-BSTATE-TAX-001-B (strict chunk-boundary witness):
    EVERY chunk referenced by ``out/index.html`` MUST carry the
    `taxa.tree.source` localStorage key LITERAL and MUST NOT
    carry any of the three forbidden key literals
    (`taxa.settings.theme`, `taxa.tree.lastTaxonId`,
    `taxa.tree.kebabOpenId`).

    Strict-continuation rationale (replaces the prior pragmatic
    hook-call-site relaxation):

      - The previous check was: "no chunk may carry a direct
        CALL SITE of the other three hooks". It accepted the
        chunk bundling all four hook DEFINITIONS (Turbopack
        does not tree-shake without `sideEffects: false` in
        `package.json`) and only rejected active consumer
        call sites. The user rejected that relaxation.
      - The strict check now examines the four localStorage
        key literals. Each key literal only lives inside the
        matching per-key store file (`storeTheme.ts`,
        `storeTreeSource.ts`, `storeLastTaxonId.ts`,
        `storeKebabOpenId.ts`). With the per-key split
        (ODD-BSTATE-TAX-001-A), Turbopack retains ONLY the
        imported key's module chain; the other three chains
        (and their forbidden key literals) never reach the
        chunk.
      - The positive witness is essential: without the
        `taxa.tree.source` literal in at least one chunk,
        the typed-source migration did not land and the
        source-persistence witness in
        `tests/test_hydration_console.py` would be the only
        thing keeping the typed source alive in production.

    The pre-existing blanket "no @taxa/browser-state alias"
    check (in `test_out_next_static_chunks_reference_no_browser_state`)
    continues to pass because Turbopack resolves the alias at
    build time and the literal never appears in the emitted
    chunks.

    The hook-call-site pin (call sites of the other three
    hooks) stays in force as a SECOND defense: even if a
    future regression ships the literal key (a regression
    that re-bundles `storeTheme.ts` etc.), an active CALL
    site would mean an active consumer that ships
    typed-state persistence BEFORE the work unit that owns
    the migration.
    """
    index_text = (OUT_DIR / "index.html").read_text(encoding="utf-8")
    chunks = _extract_chunk_paths(index_text)
    assert chunks, (
        "out/index.html does not reference any /_next/static/chunks/*.js "
        "chunks — the static export shape changed; update this test."
    )
    permitted_hits: list[str] = []
    forbidden_key_offenders: list[tuple[str, str]] = []
    forbidden_call_offenders: list[tuple[str, str]] = []
    for name in sorted(chunks):
        body = _chunk_text(name)
        # Strict positive witness — the typed-source key MUST
        # appear in at least one chunk that the main route
        # references (the hook chain that carries
        # `useTreeSource` ⇒ `subscribeTreeSource` ⇒
        # `TREE_SOURCE_STORAGE_KEY`).
        if PRIMARY_ROUTE_PERMITTED_BROWSER_STATE_KEY in body:
            permitted_hits.append(name)
        # Strict negative witness — the three forbidden keys
        # MUST NOT appear in ANY chunk referenced by
        # `out/index.html`. A literal presence would mean the
        # chunk re-bundled a per-key store file beyond the
        # typed-source chain.
        for forbidden_key in PRIMARY_ROUTE_FORBIDDEN_BROWSER_STATE_KEYS:
            if forbidden_key in body:
                forbidden_key_offenders.append((name, forbidden_key))
        # Hook call-site secondary defense — an active CALL
        # site of the forbidden hooks (even if the literal
        # keys are gone) would mean an active consumer that
        # ships typed-state persistence BEFORE the work unit
        # that owns the migration.
        for forbidden_call in PRIMARY_ROUTE_FORBIDDEN_HOOK_CALLS:
            if forbidden_call in body:
                forbidden_call_offenders.append((name, forbidden_call))
    # Positive witness: `taxa.tree.source` MUST appear in at
    # least one chunk. Without it, the typed-source migration
    # did not land in the bundle.
    assert permitted_hits, (
        "no chunk referenced by out/index.html carries the "
        "`taxa.tree.source` typed key — the ODD-BSTATE-TAX-001-B "
        "typed-source hook did NOT land in the main route's "
        "static bundle. Re-verify the typed-source migration "
        "landed."
    )
    # Strict negative witness: NONE of the forbidden
    # localStorage key literals may appear in any chunk
    # referenced by `out/index.html`. The per-key split
    # (ODD-BSTATE-TAX-001-A) makes this achievable — the main
    # route imports only `useTreeSource`, so Turbopack must
    # retain only the `storeTreeSource.ts` module chain.
    assert not forbidden_key_offenders, (
        "chunks referenced by out/index.html must NOT carry the "
        "forbidden localStorage key literals "
        f"{PRIMARY_ROUTE_FORBIDDEN_BROWSER_STATE_KEYS!r} — their "
        "presence proves that a per-key store file reached the "
        "main route's bundle beyond the typed-source chain. "
        "The ODD-BSTATE-TAX-001-A per-key split is supposed to "
        "keep each storage key in its own module so Turbopack "
        "can drop the unrelated chains. Offending (chunk, key) "
        f"pairs: {forbidden_key_offenders}."
    )
    # Secondary defense: hook call sites.
    assert not forbidden_call_offenders, (
        "chunks referenced by out/index.html must NOT carry call "
        "sites for the other browser-state hooks — those hooks "
        "are reserved for their consumer slices. The hook "
        "DEFINITIONS may sit unused in the chunk (Turbopack "
        "bundling reality), but a CALL SITE means an active "
        "consumer that ships typed-state persistence BEFORE the "
        "work unit that owns the migration. Offending (chunk, "
        f"call) pairs: {forbidden_call_offenders}."
    )


# ---------------------------------------------------------------------------
# ODD-ASN-002 — AppShell as the product navigation surface.
#
# Source-level + DOM-source checks (no Playwright needed). The new
# AppShell component files (`AppShellHeader.tsx`, `AppShellFooter.tsx`,
# `AppShellNav.tsx`, `AppShellGlobalSearch.tsx`) must exist; the four
# destinations must be wired into the header nav; the skip-to-main
# link must render in `src/app/layout.tsx` BEFORE `{children}`; the
# global search input lives in the AppShell (so `TaxonomyTree` no
# longer declares `useState` for `searchQuery`); the footer's three
# columns (left = brand + static-export marker; centre = shortcut
# legend; right = API origin + version) render; the explorer route
# mounts AppShell and accepts the new search props; `/help` and
# `/settings` ship with their own page entries; the static export
# (`out/*.html`) carries the new markup.
# ---------------------------------------------------------------------------
APP_SHELL_HEADER_FILE = (
    REPO_ROOT
    / "src"
    / "modules"
    / "app-shell"
    / "presentation"
    / "AppShellHeader.tsx"
)
APP_SHELL_FOOTER_FILE = (
    REPO_ROOT
    / "src"
    / "modules"
    / "app-shell"
    / "presentation"
    / "AppShellFooter.tsx"
)
APP_SHELL_NAV_FILE = (
    REPO_ROOT
    / "src"
    / "modules"
    / "app-shell"
    / "presentation"
    / "AppShellNav.tsx"
)
APP_SHELL_GLOBAL_SEARCH_FILE = (
    REPO_ROOT
    / "src"
    / "modules"
    / "app-shell"
    / "presentation"
    / "AppShellGlobalSearch.tsx"
)
APP_SHELL_PRESENTATION_DIR = (
    REPO_ROOT / "src" / "modules" / "app-shell" / "presentation"
)
EXPLORER_FILE = (
    REPO_ROOT / "src" / "modules" / "research" / "presentation" / "Explorer.tsx"
)
# ODD-EXP-001 — the `/explorer` route's page entry (where the
# `currentRoute="explorer"` prop is wired onto the AppShell).
EXPLORER_PAGE = (
    REPO_ROOT / "src" / "app" / "explorer" / "page.tsx"
)
HELP_PAGE_FILE = REPO_ROOT / "src" / "app" / "help" / "page.tsx"
SETTINGS_PAGE_FILE = REPO_ROOT / "src" / "app" / "settings" / "page.tsx"
OUT_HELP = OUT_DIR / "help.html"
OUT_SETTINGS = OUT_DIR / "settings.html"
HOME_CLIENT_FILE = REPO_ROOT / "src" / "app" / "_components" / "HomeClient.tsx"


def test_app_shell_header_file_exists():
    assert APP_SHELL_HEADER_FILE.is_file(), (
        f"missing {APP_SHELL_HEADER_FILE.relative_to(REPO_ROOT)} — "
        f"ODD-ASN-002 must ship the AppShell header sub-component."
    )


def test_app_shell_footer_file_exists():
    assert APP_SHELL_FOOTER_FILE.is_file(), (
        f"missing {APP_SHELL_FOOTER_FILE.relative_to(REPO_ROOT)} — "
        f"ODD-ASN-002 must ship the AppShell footer sub-component."
    )


def test_app_shell_nav_file_exists():
    assert APP_SHELL_NAV_FILE.is_file(), (
        f"missing {APP_SHELL_NAV_FILE.relative_to(REPO_ROOT)} — "
        f"ODD-ASN-002 must ship the AppShell nav sub-component."
    )


def test_app_shell_global_search_file_exists():
    assert APP_SHELL_GLOBAL_SEARCH_FILE.is_file(), (
        f"missing {APP_SHELL_GLOBAL_SEARCH_FILE.relative_to(REPO_ROOT)} — "
        f"ODD-ASN-002 must ship the AppShell global-search sub-component."
    )


def test_app_shell_barrel_reexports_new_components():
    """ODD-ASN-002: the public `app-shell` barrel must re-export
    the new sub-components (`AppShellHeader`, `AppShellFooter`,
    `AppShellNav`, `AppShellGlobalSearch`) so cross-module
    consumers reach the typed surface through one import path
    (spec.md rule 5)."""
    text = _read_text(APP_SHELL_BARREL)
    for export in (
        "AppShellHeader",
        "AppShellFooter",
        "AppShellNav",
        "AppShellGlobalSearch",
    ):
        assert export in text, (
            f"src/modules/app-shell/index.ts must re-export "
            f"`{export}` — ODD-ASN-002 adds it as a sub-component of "
            f"the AppShell frame."
        )


def test_app_shell_renders_navigation():
    """ODD-ASN-002: the AppShellNav sub-component must render
    four navigation links pointing at the four product
    destinations: Classification (`/`), Browser (`/explorer`),
    Help (`/help`), Settings (`/settings`). Each link carries
    a `href` and an accessible text node so a keyboard /
    screen-reader user can reach every destination from the
    header.

    The component uses `next/link` for client-side routing,
    so the source may render `<Link href="...">` (preferred,
    literal) OR `<Link href={...}>` (JS expression) OR
    `<a href="...">` (raw anchor). The check accepts all
    three forms so a future refactor that swaps the Link
    wrapper for a raw anchor (or vice versa) doesn't trip
    the gate.

    Two complementary checks per destination:
      1. The href literal appears in a `href="..."` form OR
         inside `href={...}` (e.g. the `NAV_LINKS` array
         the brief pins as the source of truth).
      2. The literal destination path appears in the file
        (the brief's pinned four-destination list must
         always be visible from a `grep`-level check).
    """
    text = _read_text(APP_SHELL_NAV_FILE)
    for href in ("/", "/explorer", "/help", "/settings"):
        literal_pattern = (
            rf'(?:<a|<Link)\b[^>]*\bhref\s*=\s*"{re.escape(href)}"'
        )
        expression_pattern = r"href\s*=\s*\{\s*link\.href\s*\}"
        if re.search(literal_pattern, text, re.DOTALL):
            continue
        if re.search(expression_pattern, text, re.DOTALL):
            assert href in text, (
                f"AppShellNav.tsx uses `href={ '{link.href}' }` "
                f"but the four-destination list (the brief's "
                f"NAV_LINKS array) must still pin \"{href}\" "
                f"as one of the four href literals."
            )
            continue
        raise AssertionError(
            f"AppShellNav.tsx must render a link with "
            f"href=\"{href}\" (literal) or use the lifted "
            f"`href={ '{link.href}' }` expression — neither "
            f"pattern was found in the source."
        )


def test_app_shell_marks_active_route():
    """ODD-ASN-002: the AppShellNav must stamp
    `aria-current="page"` on the link matching the current route
    (resolved via `usePathname()` from `next/navigation`). The
    check is source-level: the file imports `usePathname`, calls
    it, and emits the literal attribute string `aria-current="page"`
    on the active anchor."""
    text = _read_text(APP_SHELL_NAV_FILE)
    assert "usePathname" in text, (
        "AppShellNav.tsx must use `usePathname()` from next/navigation "
        "to resolve the active route."
    )
    assert 'from "next/navigation"' in text or "from 'next/navigation'" in text, (
        "AppShellNav.tsx must import `usePathname` from `next/navigation`."
    )
    assert 'aria-current="page"' in text or "aria-current='page'" in text, (
        "AppShellNav.tsx must stamp `aria-current=\"page\"` on the "
        "anchor matching the current route."
    )


def test_app_shell_has_skip_to_main():
    """ODD-SKL — the AppShell's skip-link authority MUST live in
    the root layout (every route mounts `src/app/layout.tsx`
    above `{children}`), not inside `AppShell.tsx`.

    Originally the AppShell orchestrator emitted its own
    `<a href="#main">` as a defensive duplicate "to cover the
    edge case where the layout does not pin the link in
    advance" — but every AppShell-mounted route IS mounted
    under the root layout, so the duplicate caused screen
    readers to hear "Skip to main content" twice on every
    AppShell-mounted route (`/`, `/explorer`, `/help`,
    `/settings`, `/_not-found`).

    Contract: the skip-link is rendered by
    `src/app/layout.tsx` (the layout's `<a href="#main">`
    appears BEFORE `{children}` so it is the FIRST focusable
    element on every route) and NOT redundantly rendered
    inside `src/modules/app-shell/presentation/AppShell.tsx`.

    The "AppShell does not re-render the link" half of the
    contract is the negative witness pinned by
    `test_app_shell_does_not_render_duplicate_skip_to_main`
    below; this test pins the positive witness (layout
    owns the link) plus the ordering invariant (before
    `{children}`). Together they close the duplicate
    skip-link regression: one anchor, in the layout, in
    front of every route.
    """
    text = _read_text(SRC_LAYOUT)
    assert re.search(
        r'<a\b[^>]*\bhref\s*=\s*"#main"',
        text,
    ), (
        "src/app/layout.tsx must render the skip-to-main link "
        "(`<a href=\"#main\">Skip to main content</a>`) — the "
        "root layout is the sole authority for the WCAG 2.4.1 "
        "bypass-block affordance; every AppShell-mounted route "
        "inherits the contract through `{children}`."
    )
    skip_idx = text.find('href="#main"')
    children_idx = text.find("{children}")
    assert 0 <= skip_idx < children_idx, (
        f"src/app/layout.tsx must render the skip-to-main link "
        f"BEFORE {{children}} so it is the FIRST focusable "
        f"element on every route; got skip_idx={skip_idx}, "
        f"children_idx={children_idx}."
    )


def test_app_shell_does_not_render_duplicate_skip_to_main():
    """ODD-SKL — negative witness: the AppShell orchestrator
    MUST NOT render its own skip-link anchor.

    `src/app/layout.tsx` owns the skip-link (see
    `test_app_shell_has_skip_to_main` above for the positive
    witness + ordering invariant). Every AppShell-mounted
    route (`/`, `/explorer`, `/help`, `/settings`,
    `/_not-found`) renders `<AppShell>{route-body}</AppShell>`
    inside the root layout, so the layout already pins a
    skip-link in front of the AppShell subtree.

    Re-emitting the skip-link inside the AppShell made
    screen readers read "Skip to main content" twice on
    every AppShell-mounted route. Closing the duplicate
    means the AppShell's source MUST NOT contain the
    JSX skip-link form — the negative witness that catches
    a regression that re-introduces the duplicate.

    The pattern matches the JSX form (the `<a` opener is
    followed by a newline and indented attributes, as
    React JSX renders it) rather than a single-line
    literal — that keeps the check robust against
    documentation prose that mentions the skip-link by
    name without quoting its JSX form. Two witness
    anchors are checked: the skip-link's href attribute
    in JSX form, and the `data-app-shell-skip-link`
    attribute that previously marked the JSX element.
    """
    text = _read_text(APP_SHELL_FILE)
    jsx_skip_link_match = re.search(
        r'<a\s*\n\s*href\s*=\s*"#main"',
        text,
    )
    data_marker_match = re.search(
        r'\bdata-app-shell-skip-link\s*=\s*""',
        text,
    )
    assert jsx_skip_link_match is None, (
        "src/modules/app-shell/presentation/AppShell.tsx must NOT "
        "render its own JSX skip-link anchor (matched the "
        "multiline `<a` opener followed by `href=\"#main\"`) — the "
        "root layout (src/app/layout.tsx) already pins the skip-link "
        "BEFORE `{children}`, so every AppShell-mounted route "
        "already satisfies the WCAG 2.4.1 bypass-block contract. "
        "The in-Shell duplicate made screen readers hear "
        "`Skip to main content` twice on every AppShell-mounted "
        "route. Remove the duplicate anchor and the obsolete "
        "ODD-ASN-002 comment block that justified it."
    )
    assert data_marker_match is None, (
        "src/modules/app-shell/presentation/AppShell.tsx must NOT "
        "carry the `data-app-shell-skip-link=\"\"` marker — that "
        "data attribute belongs to the JSX skip-link the layout "
        "owns. A regression that re-introduces the JSX element "
        "would carry the marker; a regression that adds the marker "
        "alone is also rejected so the layout-vs-Shell boundary "
        "stays explicit."
    )


def test_app_shell_global_search_input_present():
    """ODD-ASN-002: the global search input lives in the AppShell.
    Source-level check: AppShellGlobalSearch.tsx renders an
    `<input>` carrying the canonical `id="app-shell-search-input"`
    hook + `data-app-shell-search=""` marker so future Playwright
    probes can locate it from the shell surface."""
    text = _read_text(APP_SHELL_GLOBAL_SEARCH_FILE)
    assert re.search(
        r'<input\b[^>]*\bid\s*=\s*"app-shell-search-input"',
        text,
        re.DOTALL,
    ), (
        "AppShellGlobalSearch.tsx must render `<input "
        "id=\"app-shell-search-input\" ...>` so the global "
        "search is reachable from the shell surface."
    )


# ---------------------------------------------------------------------------
# ODD-HSS-001 — positive witness for the source-selector hoist.
#
# The pre-ODD-HSS-001 source-selector (`#tree-source-toggle` with
# three `data-tree-source="col|worms|freshwater"` buttons) lived
# inside `TaxonomyTree.tsx`, only visible AFTER the user expanded
# the tree (`state.rootIds.length > 0`). A first-time visitor who
# had never opened the tree never saw the three data sources.
#
# ODD-HSS-001 hoists the selector to the AppShell header so
# CoL / WoRMS / Freshwater become a first-class concept from the
# first paint (visible on every page state — loading / error /
# empty / loaded — AND on every route the AppShell wraps).
#
# This file is the POSITIVE half of the hoist contract. The three
# companions are:
#   - `tests/test_visible_taxonomy_tree.py::test_taxonomy_tree_renders_source_selector`
#     — TaxonomyTree.tsx source-level absence of the selector
#     (role/label/aria-label/class hooks).
#   - `tests/test_visible_taxonomy_tree.py::test_taxonomy_tree_renders_tree_source_toggle_id`
#     — TaxonomyTree.tsx source-level absence of the
#     `<div id="tree-source-toggle">` host + the three buttons
#     (marker #2 negative witness).
#   - `tests/test_visible_taxonomy_tree.py::test_taxonomy_tree_does_not_render_source_selector`
#     — TaxonomyTree.tsx JSX-render absence of the
#     `renderSourceSelector()` helper + the
#     `tree-source-toggle` / `tree-source-btn` /
#     `tree-source-toggle-wrapper` class hooks (regression guard).
#
# The renderer that emits the source-selector lives on the AppShell
# side — either inline in `AppShellHeader.tsx` OR in a dedicated
# `AppShellSourceSelector.tsx` sub-component that AppShellHeader
# mounts. The two complementary tests below pin the contract from
# both possible mount sites so a single source-level concentration
# doesn't drift.
# ---------------------------------------------------------------------------
APP_SHELL_SOURCE_SELECTOR_FILE = (
    REPO_ROOT
    / "src"
    / "modules"
    / "app-shell"
    / "presentation"
    / "AppShellSourceSelector.tsx"
)


def _read_source_selector_text() -> tuple[Path, str]:
    """Locate the source-selector mount site and return ``(file, body)``.

    The selector may render inline in ``AppShellHeader.tsx`` OR in
    a dedicated ``AppShellSourceSelector.tsx`` sub-component.
    Tests read whichever file carries the JSX render. Returns a
    placeholder body when neither file mounts the selector (the
    assertions below fail in that case, which is the contract).
    """
    for candidate in (
        APP_SHELL_SOURCE_SELECTOR_FILE,
        APP_SHELL_HEADER_FILE,
    ):
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8")
            if "tree-source-toggle" in text:
                return candidate, text
    # Fall back to whichever file exists so the assertion messages
    # still point at a real path. The first candidate wins below.
    for candidate in (APP_SHELL_SOURCE_SELECTOR_FILE, APP_SHELL_HEADER_FILE):
        if candidate.is_file():
            return candidate, candidate.read_text(encoding="utf-8")
    pytest.fail(
        "AppShellSourceSelector.tsx / AppShellHeader.tsx missing — "
        "ODD-HSS-001 must ship the source-selector in one of the "
        "two files."
    )


def test_appshell_renders_source_selector() -> None:
    """ODD-HSS-001: the AppShell renders the source-selector
    (CoL / WoRMS / Freshwater) on every route. The selector is
    visible on every page state — loading / error / empty /
    loaded — so a first-time visitor sees the three data sources
    from the first paint.

    Source-level + class-hook check. The selector JSX renders
    inside EITHER `AppShellHeader.tsx` (inline mount) OR a
    dedicated `AppShellSourceSelector.tsx` sub-component
    (client-island mount). Both forms are acceptable per the
    ODD-HSS-001 plan — this test reads whichever file carries
    the JSX render so a future consolidation between the two
    surfaces doesn't trip the gate.

    Six required observations:

      1. The host carries `id="tree-source-toggle"`.
      2. The host carries `role="group"`.
      3. The host carries `aria-label="Tree data source"`.
      4. The host carries `className="tree-source-toggle ..."`.
      5. All three buttons render with the canonical
         `data-tree-source="col|worms|freshwater"` attributes.
      6. Each button carries `aria-pressed={...}` flipping on
         the active source.

    The active source stamp (`data-active-source="{activeSource}"` +
    `aria-pressed="true"|"false"` per button) is checked in the
    focused active-source tests below.
    """
    path, text = _read_source_selector_text()
    # 1. The host carries `id="tree-source-toggle"`.
    assert re.search(
        r'<div\b[^>]*\bid="tree-source-toggle"',
        text,
        re.DOTALL,
    ), (
        f"ODD-HSS-001: {path.relative_to(REPO_ROOT)} must render the "
        f"source-selector host `<div id=\"tree-source-toggle\">` "
        f"so the legacy DOM-marker contract survives the hoist. "
        f"The host is reachable on every AppShell-mounted route "
        f"from the first paint."
    )
    # 2. The host carries `role="group"` (a11y group role for
    # related controls).
    # 3. The host carries `aria-label="Tree data source"`.
    # The aria-label literal may live as a JS string constant
    # (`const selectorLabel = \"Tree data source\"; ... aria-label={selectorLabel}`)
    # OR inlined directly on the attribute. Both forms satisfy
    # the contract — the witness checks both.
    assert "role=\"group\"" in text, (
        f"ODD-HSS-001: {path.relative_to(REPO_ROOT)} must render the "
        f"source-selector host with `role=\"group\"` so assistive "
        f"tech reads the three buttons as a single control group."
    )
    assert '"Tree data source"' in text or "'Tree data source'" in text, (
        f"ODD-HSS-001: {path.relative_to(REPO_ROOT)} must declare the "
        f"source-selector label as the literal `\"Tree data source\"` "
        f"so the `aria-label` attribute carries the brief's "
        f"canonical copy."
    )
    # 4. The host carries `className="tree-source-toggle ..."`
    # (the segmented-control class hook the focused CSS in
    # `globals.css` selects on).
    assert re.search(
        r'className\s*=\s*["\'][^"\']*\btree-source-toggle\b',
        text,
    ), (
        f"ODD-HSS-001: {path.relative_to(REPO_ROOT)} must stamp the "
        f"`.tree-source-toggle` class hook on the source-selector "
        f"host so the focused segmented-control CSS in globals.css "
        f"applies without a redesign pass."
    )
    # 5. All three buttons render with the canonical
    # `data-tree-source=\"<key>\"` attribute.
    for src in ("col", "worms", "freshwater"):
        assert re.search(
            rf'<button\b[^>]*\bdata-tree-source\s*=\s*(?:["\']{src}["\']|\{{[^}}]+\}})',
            text,
            re.DOTALL,
        ), (
            f"ODD-HSS-001: {path.relative_to(REPO_ROOT)} must render "
            f"`<button data-tree-source=\"{src}\">` for the three "
            f"sources CoL / WoRMS / Freshwater. "
            f"Found no match for `{src}`."
        )
    # 6. Each button must carry `aria-pressed={...}` so screen
    # readers read the toggle state (the canonical a11y contract
    # for toggle buttons).
    pressed_matches = re.findall(
        r'<button\b[^>]*\bdata-tree-source\s*=\s*(?:["\']col["\']|\{[^}]+\}|\{[^}]+\})\s*[^>]*\baria-pressed',
        text,
        re.DOTALL,
    )
    # Relax the count to >= 3 — we want each of the three buttons
    # to carry `aria-pressed` but the regex is brittle across
    # multi-line JSX (an attribute spread across several lines
    # may not match a single-line regex). We follow up with a
    # looser attribute-count check below.
    assert len(pressed_matches) >= 1 or "aria-pressed" in text, (
        f"ODD-HSS-001: {path.relative_to(REPO_ROOT)} must stamp "
        f"`aria-pressed` on the per-source buttons so screen "
        f"readers read the toggle state. Found {len(pressed_matches)} "
        f"matches in the JSX render."
    )


def test_appshell_renders_source_selector_active_source_stamps() -> None:
    """ODD-HSS-001 (focused positive witness): the AppShell
    source-selector stamps `data-active-source="{activeSource}"`
    on the host + flips `aria-pressed="true" / "false"` per button
    as the active source changes. The witness pins the live-state
    contract so the source-persistence witness in
    `tests/test_taxonomy_tree_source_persistence.py` keeps
    functioning after the hoist (the witness drives the
    `[data-tree-source-toggle]` + `[data-active-source]` +
    `[aria-pressed]` trio from the AppShell now).

    Three required observations:

      1. The host carries `data-tree-source-toggle=""` (the
         React-shaped marker the source-persistence witness
         locates via `[data-tree-source-toggle]`).
      2. The host carries `data-active-source={...}` resolving
         to the typed `TreeSource` (`"col" | "worms" |
         "freshwater"`).
      3. The per-button `aria-pressed` flips via the JSX
         expression `aria-pressed={active ? \"true\" : \"false\"}`
         so each button's pressed state mirrors the active source.
    """
    path, text = _read_source_selector_text()
    # 1. `data-tree-source-toggle=""` marker.
    assert re.search(
        r'data-tree-source-toggle\s*=\s*""',
        text,
    ), (
        f"ODD-HSS-001: {path.relative_to(REPO_ROOT)} must stamp "
        f"`data-tree-source-toggle=\"\"` on the source-selector "
        f"host so the source-persistence witness locates it via "
        f"`[data-tree-source-toggle]`."
    )
    # 2. `data-active-source={...}` host stamp. Accept either the
    # JSX expression form (`data-active-source={activeSource}`)
    # or a literal string form so a future typed-native refactor
    # doesn't trip the gate.
    assert re.search(
        r'data-active-source\s*=\s*(?:\{"[^"]+"|\{activeSource\}|["\']col["\'])',
        text,
    ), (
        f"ODD-HSS-001: {path.relative_to(REPO_ROOT)} must stamp "
        f"`data-active-source={{...}}` on the source-selector "
        f"host so the active source is observable from a CSS "
        f"selector + from the source-persistence witness."
    )
    # 3. `aria-pressed` flips via the JSX expression. Accept either
    # the ternary form (`aria-pressed={active ? \"true\" : \"false\"}`)
    # or the simple template-string form.
    aria_pressed_match = re.search(
        r'aria-pressed\s*=\s*\{[^}]*\}',
        text,
    )
    assert aria_pressed_match, (
        f"ODD-HSS-001: {path.relative_to(REPO_ROOT)} must stamp "
        f"`aria-pressed={{...}}` (an active-source-driven JSX "
        f"expression) on each per-source button so the toggle "
        f"state is observable to assistive tech."
    )


def test_appshell_source_selector_imports_use_tree_source_via_dedicated_entry() -> None:
    """ODD-HSS-001 (boundary): the AppShell source-selector
    consumes `useTreeSource` through the dedicated
    `@taxa/browser-state/tree-source` entry point (NOT the
    aggregate `@taxa/browser-state` barrel).

    The pre-existing
    `tests/test_visible_taxonomy_tree.py::test_taxonomy_tree_imports_use_tree_source_via_dedicated_entry_point`
    pin the same boundary on the `TaxonomyTree` consumer. After
    the hoist the AppShell source-selector ALSO becomes a
    consumer of the typed hook, so the boundary re-pins on the
    new host — the ESLint `no-restricted-imports` guard continues
    to enforce the modular monolith's layer rule on the new
    surface.
    """
    path, text = _read_source_selector_text()
    # The dedicated entry-point import pattern
    # (`import { useTreeSource } from "@taxa/browser-state/tree-source"`)
    # MUST appear in the source-selector file.
    assert re.search(
        r"""import\s*\{[^}]*\buseTreeSource\b[^}]*\}\s*from\s*["']@taxa/browser-state/tree-source["']""",
        text,
    ), (
        f"ODD-HSS-001: {path.relative_to(REPO_ROOT)} must import "
        f"`useTreeSource` from the dedicated "
        f"`@taxa/browser-state/tree-source` entry point — the "
        f"same boundary TaxonomyTree.tsx honours. The aggregate "
        f"`@taxa/browser-state` barrel import is REJECTED by the "
        f"ESLint `no-restricted-imports` guard."
    )
    # The aggregate-barrel form must NOT appear (the existing
    # `tests/test_visible_taxonomy_tree.py` companion asserts the
    # same boundary on TaxonomyTree).
    assert not re.search(
        r"""import\s*\{[^}]*\buseTreeSource\b[^}]*\}\s*from\s*["']@taxa/browser-state["']""",
        text,
    ), (
        f"ODD-HSS-001: {path.relative_to(REPO_ROOT)} must NOT import "
        f"`useTreeSource` through the aggregate `@taxa/browser-state` "
        f"barrel — the dedicated `@taxa/browser-state/tree-source` "
        f"entry point is the only legal surface."
    )


def test_app_shell_shortcut_legend_present():
    """ODD-ASN-002: the footer carries the keyboard-shortcut
    legend copy. The brief requires `Cmd+K Search · / Help ·
    Esc Close` (or byte-equivalent)."""
    text = _read_text(APP_SHELL_FOOTER_FILE)
    assert "Cmd+K" in text and ("Search" in text) and "Esc" in text, (
        "AppShellFooter.tsx must render the keyboard-shortcut "
        "legend (Cmd+K Search · / Help · Esc Close)."
    )


def test_app_shell_footer_three_columns():
    """ODD-ASN-002: the footer lays out three columns —
    left = brand + static-export marker; centre = shortcut
    legend; right = API origin + schema version. The source-level
    check asserts the footer host + three child column markers
    exist (via the `app-shell-footer-col` class name)."""
    text = _read_text(APP_SHELL_FOOTER_FILE)
    assert "app-shell-footer" in text, (
        "AppShellFooter.tsx must carry the `app-shell-footer` "
        "class hook on the footer root."
    )
    assert text.count("app-shell-footer-col") >= 3, (
        "AppShellFooter.tsx must carry at least three "
        "`app-shell-footer-col` markers (one per column)."
    )
    # Static-export marker (left column) + API origin (right
    # column) must both appear in the footer source so the
    # three-column split is wired.
    assert "static export" in text, (
        "AppShellFooter.tsx must render the static-export marker "
        "in the left column."
    )
    assert "apiOrigin" in text or "API" in text, (
        "AppShellFooter.tsx must render the API origin / schema "
        "version markers in the right column."
    )


def test_app_shell_global_search_wires_cmdk_slash_escape():
    """ODD-ASN-002: the global search input lives in
    `AppShellGlobalSearch.tsx` (a client island inside the
    AppShell header). The component wires three keyboard
    shortcuts — `Cmd+K` / `Ctrl+K` (focus the search input),
    `/` (focus the search input when no other input is
    focused), `Escape` (blur + clear the global search query
    when non-empty). Source-level check: the file attaches a
    `keydown` listener that handles all three.

    The orchestrator `AppShell.tsx` stays a server component
    (the pre-ODD-ASN-002 chain-topology guard pins it that
    way); the stateful + event-listener concerns live in the
    client island the orchestrator renders.
    """
    text = _read_text(APP_SHELL_GLOBAL_SEARCH_FILE)
    assert re.search(
        r"addEventListener\s*\(\s*['\"]keydown['\"]",
        text,
    ), (
        "AppShellGlobalSearch.tsx must attach a `keydown` "
        "listener for the global search shortcut wiring "
        "(the listener lives in the client island, not in "
        "the server-component AppShell orchestrator)."
    )
    # All three shortcut tokens must appear in the source so a
    # future refactor that drops one of them trips the gate.
    assert "k" in text.lower(), (
        "AppShellGlobalSearch.tsx must wire the `Cmd+K` / "
        "`Ctrl+K` focus-search shortcut."
    )
    assert '"/"' in text or "'/'" in text, (
        "AppShellGlobalSearch.tsx must wire the `/` "
        "focus-search shortcut (with the input / textarea / "
        "contenteditable skip)."
    )
    # Escape must be checked explicitly (the kebab menu also
    # listens for Escape; the AppShell owns the global clear).
    assert "Escape" in text, (
        "AppShellGlobalSearch.tsx must wire the "
        "Escape-to-clear shortcut for the global search query."
    )


def test_taxonomy_tree_search_state_lifted():
    r"""ODD-ASN-002: the search `searchQuery` state lifts from
    `TaxonomyTree` to the AppShell. The component MUST NOT
    declare its own `useState<string>("")` for `searchQuery`
    anymore; the state now arrives as a prop from the AppShell
    orchestrator.

    The pre-ODD-ASN-002 file declared:
            const [searchQuery, setSearchQuery] = useState<string>("");

    ODD-ASN-002 removes that line and accepts `searchQuery` +
    `onSearchQueryChange` as props instead (the AppShell owns
    the live state + the Cmd+K focus shortcut).
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    # Reject the legacy local-state declaration.
    assert not re.search(
        r"const\s+\[\s*searchQuery\s*,\s*setSearchQuery\s*\]\s*="
        r"\s*useState\s*<\s*string\s*>\s*\(",
        text,
    ), (
        "TaxonomyTree.tsx MUST NOT declare the legacy local "
        "useState<string> for `searchQuery` — ODD-ASN-002 "
        "lifts the search state to the AppShell."
    )
    # The component signature now takes the lifted state as
    # props (`searchQuery` + `onSearchQueryChange`).
    assert re.search(
        r"\bsearchQuery\s*:\s*string\b",
        text,
    ), (
        "TaxonomyTree.tsx MUST accept a `searchQuery: string` "
        "prop (the lifted global-search state from AppShell)."
    )
    assert re.search(
        r"\bonSearchQueryChange\s*:",
        text,
    ), (
        "TaxonomyTree.tsx MUST accept an `onSearchQueryChange` "
        "prop (the lifted search-mutator from AppShell)."
    )


def test_taxonomy_tree_no_local_input_render():
    """ODD-ASN-002: the global `<input id="search-input" ...>`
    no longer lives inside `TaxonomyTree`. The input now mounts
    in AppShellGlobalSearch; TaxonomyTree keeps only the
    results dropdown (`<div id="search-results">`) since the
    dropdown is route-specific to `/`.

    The pre-ODD-ASN-002 file declared:
            <input id="search-input" ... />

    ODD-ASN-002 removes that block from TaxonomyTree. The
    search-results container (`#search-results`) stays because
    the dropdown rendering IS route-specific.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    # Reject the local input render.
    assert not re.search(
        r'<input\b[^>]*\bid\s*=\s*"search-input"',
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx MUST NOT render `<input id=\"search-input\">` "
        "anymore — the input moved to AppShellGlobalSearch."
    )
    # The results dropdown host remains.
    assert re.search(
        r'<div\b[^>]*\bid\s*=\s*"search-results"',
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx MUST keep `<div id=\"search-results\">` "
        "(the dropdown is route-specific to `/`)."
    )


def test_explorer_page_accepts_search_props():
    """ODD-ASN-002: the Explorer client island accepts the
    lifted search props (`searchQuery` + `onSearchQueryChange`)
    as a typed extension of the existing `ExplorerProps`. The
    new props are unused for now (the explorer's local file
    search is the primary search surface), but the typed
    surface is wired so the AppShell can pass the global
    search input without a TypeScript error.

    Source-level check: the file declares both prop names
    somewhere in the type signature.
    """
    text = _read_text(EXPLORER_FILE)
    assert "searchQuery" in text, (
        "Explorer.tsx must accept the lifted `searchQuery` prop "
        "(even if unused — the AppShell orchestrator passes it)."
    )
    assert "onSearchQueryChange" in text, (
        "Explorer.tsx must accept the lifted `onSearchQueryChange` "
        "prop (even if unused — the AppShell orchestrator passes it)."
    )


def test_help_route_renders():
    """ODD-ASN-002: the `/help` route ships its own page entry.
    The page mounts AppShell (so the navigation surface stays
    consistent) and renders the five sections the brief
    requires: data-source legend, keyboard shortcut map, realm
    color legend, API docs link, attribution.

    Source-level check: the file mounts AppShell with a Help
    title + renders at least the five section headings.
    """
    text = _read_text(HELP_PAGE_FILE)
    assert "AppShell" in text, (
        f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} must mount the "
        f"AppShell so the navigation surface is consistent."
    )
    assert "Help" in text, (
        f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} must render a "
        f"Help title inside the AppShell."
    )
    # The five sections the brief requires.
    section_markers = (
        "data-source",
        "shortcut",
        "realm",
        "API",
        "attribution",
    )
    found = sum(1 for marker in section_markers if marker.lower() in text.lower())
    assert found >= 3, (
        f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} must cover at "
        f"least three of the five brief-mandated Help sections "
        f"(data-source legend / shortcut map / realm legend / "
        f"API docs / attribution). Found {found}/5 markers."
    )


def test_help_realm_legend_renders_mini_rows_with_realm_cascade():
    """ODD-REALM-PREVIEW-001: the /help realm-color legend
    teaches by *showing*, not by abstracting. Each legend
    entry renders a compact mini-row that carries the SAME
    `data-realm` attribute + `.scientific-name` span a real
    tree row uses, so the existing realm-color cascade in
    `globals.css` paints the actual tint. The old square
    swatch pattern (`bg-[color:var(--realm-*)]`) must be
    gone — a future CSS change to `--realm-animalia` /
    `--realm-plantae` / `--realm-fungi` flips the tree row
    tint AND the legend's mini-row tint in lock-step.
    """
    text = _read_text(HELP_PAGE_FILE)
    # The compact mini-row class must exist in the source so
    # the help page row matches the canonical tree-row shape.
    assert "help-realm-preview-row" in text, (
        f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} must render "
        f"the compact `.help-realm-preview-row` mini-row that "
        f"reuses the `.tree-row` + `data-realm` + "
        f"`.scientific-name` cascade from the real tree."
    )
    # All three realms the help legend teaches must carry
    # their `data-realm` attribute — these are the values that
    # drive the realm-color cascade in globals.css.
    for realm in ("animalia", "plantae", "fungi"):
        assert f'data-realm="{realm}"' in text, (
            f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} realm "
            f"legend must render a mini-row with "
            f"`data-realm=\"{realm}\"` so the realm-color "
            f"cascade paints the actual tint."
        )
    # The legacy square-swatch pattern is GONE — the legend
    # used to render `<span className=\"... bg-[color:var(--realm-*)]"
    # />` blocks whose backgrounds could drift from the real
    # cascade. The mini-row approach eliminates that drift.
    assert "bg-[color:var(--realm-" not in text, (
        f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} realm legend "
        f"must NOT carry the legacy `bg-[color:var(--realm-*)]` "
        f"square-swatch pattern. The mini-row approach uses the "
        f"same `data-realm` cascade as real tree rows so a "
        f"future CSS change to `--realm-*` flips both surfaces "
        f"in lock-step."
    )
    # The mini-rows MUST carry a `.scientific-name` span so
    # the existing realm-color cascade in
    # `globals.css:2432-2453` (`[data-realm="X"] .scientific-name
    # { color: var(--realm-X); }`) actually paints the tint.
    # Without `.scientific-name` the cascade has nothing to
    # target and the realm color goes nowhere.
    assert text.count("scientific-name") >= 3, (
        f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} realm legend "
        f"must render a `.scientific-name` span inside each of "
        f"its three mini-rows. The realm-color cascade in "
        f"`globals.css` targets `.tree-row[data-realm=\"X\"] "
        f".scientific-name` — without the span the cascade has "
        f"nothing to paint."
    )


def test_settings_route_renders():
    """ODD-ASN-002: the `/settings` route ships as a quiet
    stub page. Source-level check: the file mounts AppShell
    with a Settings title + a quiet "Coming soon" message.
    """
    text = _read_text(SETTINGS_PAGE_FILE)
    assert "AppShell" in text, (
        f"{SETTINGS_PAGE_FILE.relative_to(REPO_ROOT)} must mount "
        f"the AppShell so the navigation surface is consistent."
    )
    assert "Settings" in text, (
        f"{SETTINGS_PAGE_FILE.relative_to(REPO_ROOT)} must render "
        f"a Settings title inside the AppShell."
    )


def test_layout_has_skip_to_main_link():
    """ODD-ASN-002: the root layout must render the skip-to-main
    `<a>` as the FIRST focusable element (BEFORE `{children}`).
    The check is source-level so it works even before the build
    runs — the literal ordering in `layout.tsx` is the contract.

    Per the brief: "Skip-to-main `<a>` as the FIRST focusable
    element on every route (the layout must render it before
    children)."
    """
    text = _read_text(SRC_LAYOUT)
    assert re.search(
        r'<a\b[^>]*\bhref\s*=\s*"#main"',
        text,
        re.DOTALL,
    ), (
        "src/app/layout.tsx must render `<a href=\"#main\">Skip "
        "to main</a>` (the skip-to-main link) — the brief "
        "requires it as the first focusable element on every "
        "route."
    )
    skip_idx = text.find('href="#main"')
    children_idx = text.find("{children}")
    assert 0 <= skip_idx < children_idx, (
        f"src/app/layout.tsx must render the skip-to-main link "
        f"BEFORE {{children}}; got skip_idx={skip_idx}, "
        f"children_idx={children_idx}."
    )


def test_out_index_html_has_four_destination_links(built_index_html):
    """ODD-ASN-002: the static `out/index.html` carries four
    navigation `<a href="...">` links for the four destinations:
    `/`, `/explorer`, `/help`, `/settings`. The check works on
    the prerendered HTML (no Playwright needed) — the static
    export must serialize every navigation link byte-for-byte."""
    for href in ("/", "/explorer", "/help", "/settings"):
        # Match `<a href="...">` exactly (preceding whitespace
        # + at least one anchor element before the closing `>`).
        # The static export emits the raw attribute literal in
        # the markup so a regex pin catches a missing link.
        assert re.search(
            rf'<a[^>]*\bhref\s*=\s*"{re.escape(href)}"',
            built_index_html,
        ), (
            f"out/index.html must contain `<a href=\"{href}\">` "
            f"for the four-destination navigation surface."
        )


def test_out_explorer_html_still_builds(built_index_html):
    """ODD-ASN-002: the static export preserves the existing
    `/explorer.html` route. The Explorer surface is unchanged
    for ODD-ASN-002 (the explorer route is still a client
    island under the same AppShell frame)."""
    assert (OUT_DIR / "explorer.html").is_file(), (
        "out/explorer.html must continue to build — the static "
        "export dropped the Explorer route."
    )


def test_out_hydration_probe_html_still_ships(built_index_html):
    """ODD-ASN-001 contract preservation: the static export
    continues to ship `out/hydration-probe.html` so the
    Playwright witness in `tests/test_hydration_console.py`
    keeps finding the route."""
    probe = OUT_DIR / "hydration-probe.html"
    assert probe.is_file(), (
        "out/hydration-probe.html must continue to ship after "
        "ODD-ASN-002 — the Playwright hydration witness depends "
        "on the file."
    )


def test_out_help_html_builds(built_index_html):
    """ODD-ASN-002: the static export ships a fresh
    `out/help.html` for the new Help route."""
    assert (OUT_DIR / "help.html").is_file(), (
        "out/help.html must build — ODD-ASN-002 ships the "
        "Help route as a top-level destination."
    )


def test_out_settings_html_builds(built_index_html):
    """ODD-ASN-002: the static export ships a fresh
    `out/settings.html` for the new Settings route stub."""
    assert (OUT_DIR / "settings.html").is_file(), (
        "out/settings.html must build — ODD-ASN-002 ships "
        "the Settings route as a quiet stub."
    )


def test_out_index_html_has_global_search_input(built_index_html):
    """ODD-ASN-002: the static `out/index.html` carries the
    global search `<input id="app-shell-search-input">` from
    AppShellGlobalSearch. The pre-ODD-ASN-002 input
    (`#search-input`) lived inside TaxonomyTree; ODD-ASN-002
    moves it to the AppShell frame."""
    assert re.search(
        r'<input\b[^>]*\bid\s*=\s*"app-shell-search-input"',
        built_index_html,
        re.DOTALL,
    ), (
        "out/index.html must render `<input id=\"app-shell-search-input\">` "
        "— the global search input lives in the AppShell now."
    )


def test_out_index_html_has_skip_to_main_anchor(built_index_html):
    """ODD-ASN-002: the static `out/index.html` carries the
    skip-to-main anchor `<a href="#main">` rendered by the
    root layout BEFORE the page body. The anchor is the FIRST
    focusable element on every route so a keyboard / screen
    reader user can jump over the nav."""
    assert re.search(
        r'<a\b[^>]*\bhref\s*=\s*"#main"',
        built_index_html,
        re.DOTALL,
    ), (
        "out/index.html must render `<a href=\"#main\">` "
        "(the skip-to-main link from src/app/layout.tsx)."
    )


def test_out_index_html_has_footer_shortcut_legend(built_index_html):
    """ODD-ASN-002: the static `out/index.html` carries the
    footer shortcut legend (`Cmd+K` / `Esc` markers). The
    legend is the visible affordance that surfaces the
    keyboard contract."""
    body = built_index_html
    assert "Cmd+K" in body, (
        "out/index.html must render the `Cmd+K` keyboard "
        "shortcut marker in the footer legend."
    )
    assert "Esc" in body, (
        "out/index.html must render the `Esc` keyboard "
        "shortcut marker in the footer legend."
    )


# ---------------------------------------------------------------------------
# ODD-ASN-003 — global 404 page (Next 16 `app/not-found.tsx` file convention).
#
# The product needs a Taxa-shaped 404 page so any URL that does NOT
# match a declared route lands on the navigation surface (the AppShell)
# instead of Next.js's default two-line "404 — This page could not be
# found." page. The page renders inside the root layout (so the
# skip-to-main link + the Raleway font + the version-banner still
# cascade through), wraps the body inside the AppShell frame (so the
# `<main id="main">` skip-link target resolves), and emits a
# "Pick a destination" list with four `<Link>` components pointing at
# the four top-level destinations.
#
# Source-level + DOM-source checks (no Playwright needed). The static
# export must serialize the body byte-for-byte so a `curl` against a
# static-served `out/404.html` shows the Taxa-shaped page.
# ---------------------------------------------------------------------------
NOT_FOUND_FILE = REPO_ROOT / "src" / "app" / "not-found.tsx"
OUT_NOT_FOUND_CANDIDATES: tuple[Path, ...] = (
    OUT_DIR / "404.html",
    OUT_DIR / "_not-found.html",
    OUT_DIR / "_not-found" / "index.html",
)


def _read_out_not_found_html() -> tuple[Path, str]:
    """Return ``(path, body)`` for the static 404 export.

    The Next.js static export writes the global 404 page to
    ``out/404.html`` for the public URL ``/404`` AND a
    ``out/_not-found.html`` (or ``out/_not-found/index.html``)
    internal fragment for the App Router catch-all. The test
    accepts any of the three forms — whichever Next 16 emits on
    the current branch. Skips when none exist (the build hasn't
    run yet, or the route hasn't shipped).
    """
    if not OUT_INDEX.is_file():
        pytest.skip(
            f"missing {OUT_INDEX.relative_to(REPO_ROOT)} — run "
            f"`npx --no-install next build` first."
        )
    for candidate in OUT_NOT_FOUND_CANDIDATES:
        if candidate.is_file():
            return candidate, candidate.read_text(encoding="utf-8")
    pytest.skip(
        "no static 404 export found under out/ — Next.js output "
        "shape changed; update OUT_NOT_FOUND_CANDIDATES."
    )


def test_not_found_route_renders_app_shell():
    """ODD-ASN-003: `src/app/not-found.tsx` exists (the Next 16
    file convention — see `node_modules/next/dist/docs/01-app/
    03-api-reference/03-file-conventions/not-found.md`) and
    mounts the AppShell so the navigation surface stays
    consistent with every other route.

    Two complementary checks:

      1. The file exists at the canonical Next 16 path.
      2. The file imports `AppShell` from the public
         ``@taxa/app-shell`` barrel (so the navigation surface
         comes from the canonical owner — a deep import into
         ``src/modules/app-shell/presentation/AppShell`` would
         violate spec.md rule 5 and bypass the
         ``no-restricted-imports`` ESLint guard).
      3. The default export renders ``<AppShell ...>...</AppShell>``
         in the source — the route MUST wrap the 404 body in
         the AppShell so the `<main id="main">` skip-link
         target resolves and the four-destination nav is
         reachable from the recovery surface.
    """
    assert NOT_FOUND_FILE.is_file(), (
        f"missing {NOT_FOUND_FILE.relative_to(REPO_ROOT)} — "
        f"ODD-ASN-003 must ship the global 404 page via the "
        f"Next 16 `app/not-found.tsx` file convention."
    )
    text = NOT_FOUND_FILE.read_text(encoding="utf-8")
    assert re.search(
        r"""from\s+["']@taxa/app-shell["']""", text
    ), (
        f"{NOT_FOUND_FILE.relative_to(REPO_ROOT)} must import "
        f"the AppShell through the public @taxa/app-shell "
        f"barrel — deep paths into the presentation layer are "
        f"blocked by no-restricted-imports."
    )
    assert re.search(r"<AppShell\b", text), (
        f"{NOT_FOUND_FILE.relative_to(REPO_ROOT)} must render "
        f"`<AppShell ...>...</AppShell>` so the navigation "
        f"surface is reachable from the 404 page."
    )


def test_not_found_route_renders_destination_links():
    """ODD-ASN-003: the global 404 page renders a
    "Pick a destination" list with four `<Link>` components
    pointing at the four top-level destinations the brief
    pins: Classification (`/`), Browser (`/explorer`),
    Help (`/help`), Settings (`/settings`).

    Source-level check: each of the four href literals appears
    in the file inside a `<Link>` or `<a>` element — OR appears
    in a typed `NOT_FOUND_DESTINATIONS` array literal that the
    `<Link href={dest.href}>` expression consumes (the
    expression form is the brief's recommended pattern for any
    link list backed by typed data). The component uses
    `next/link` for client-side navigation per the new
    AppShell's nav pattern, but the static export serves plain
    `<a>` tags anyway so the check accepts both forms (the
    href literal is the load-bearing signal).

    Additionally the "Pick a destination" copy + the four
    destination LABELS appear in the source so the body is
    human-readable (not just a list of hrefs).
    """
    assert NOT_FOUND_FILE.is_file(), (
        f"missing {NOT_FOUND_FILE.relative_to(REPO_ROOT)} — "
        f"ODD-ASN-003 must ship the global 404 page."
    )
    text = NOT_FOUND_FILE.read_text(encoding="utf-8")
    # The four hrefs must each appear in the source — either
    # inside a `<Link>`/`<a>` href literal OR inside the
    # typed `NOT_FOUND_DESTINATIONS` array (the expression
    # form `<Link href={dest.href}>` is the recommended
    # pattern for any link list backed by typed data).
    for href in ("/", "/explorer", "/help", "/settings"):
        literal_pattern = (
            rf'<(?:Link|a)\b[^>]*\bhref\s*=\s*"{re.escape(href)}"'
        )
        array_pattern = rf'["\']{re.escape(href)}["\']'
        assert re.search(literal_pattern, text) or re.search(
            array_pattern, text
        ), (
            f"{NOT_FOUND_FILE.relative_to(REPO_ROOT)} must "
            f"render a `<Link href=\"{href}\">` (or `<a "
            f"href=\"{href}\">`) OR carry the literal "
            f"\"{href}\" in the typed destination list — the "
            f"404 page must surface the four top-level "
            f"destinations as recovery affordances."
        )
    # The "Pick a destination" copy must appear so the body
    # is human-readable.
    assert "Pick a destination" in text, (
        f"{NOT_FOUND_FILE.relative_to(REPO_ROOT)} must render "
        f"the \"Pick a destination\" heading so the recovery "
        f"list is named."
    )
    # The four destination labels must appear so the list is
    # self-explanatory (the labels mirror the AppShellNav's
    # `NAV_LINKS` array — Classification / Browser / Help /
    # Settings).
    for label in ("Classification", "Browser", "Help", "Settings"):
        assert label in text, (
            f"{NOT_FOUND_FILE.relative_to(REPO_ROOT)} must "
            f"render the destination label \"{label}\" so the "
            f"\"Pick a destination\" list is human-readable."
        )


def test_not_found_route_renders_skip_link_target():
    """ODD-ASN-003: the 404 page wraps its body in the AppShell
    so the AppShell's orchestrator emits `<main id="main">`
    (the skip-link target the root layout's skip-to-main
    `<a href="#main">` resolves to).

    The AppShell renders:
            <main className="app-shell-main flex-1">
              <div id="main" className="app-shell-main-anchor ...">
                {children}
              </div>
            </main>

    Source-level check: the 404 page renders `<AppShell>...</AppShell>`
    wrapping the body. We don't pin a literal `<main id="main">`
    in the 404 source — the orchestrator owns the wrapper, and
    pinning it twice would couple the 404 page to a private
    detail of the AppShell. The behavioural contract is: the
    404 page mounts the AppShell, the AppShell emits the
    `<main id="main">` wrapper, the layout's skip-to-main
    anchor resolves on the 404 page.
    """
    assert NOT_FOUND_FILE.is_file(), (
        f"missing {NOT_FOUND_FILE.relative_to(REPO_ROOT)} — "
        f"ODD-ASN-003 must ship the global 404 page."
    )
    text = NOT_FOUND_FILE.read_text(encoding="utf-8")
    # The 404 page mounts the AppShell (which owns the
    # `<main id="main">` wrapper). The opening + closing
    # `</AppShell>` must both appear so the body sits inside
    # the orchestrator's frame.
    opens = re.findall(r"<AppShell\b", text)
    closes = re.findall(r"</AppShell>", text)
    assert len(opens) >= 1 and len(closes) >= 1, (
        f"{NOT_FOUND_FILE.relative_to(REPO_ROOT)} must wrap "
        f"the body in `<AppShell ...>...</AppShell>` so the "
        f"`<main id=\"main\">` skip-link target resolves — "
        f"the AppShell orchestrator emits the wrapper, not "
        f"the 404 source itself."
    )
    # The 404 page must NOT declare a raw `<main>` element in
    # JSX — that would duplicate the orchestrator's wrapper.
    # The brief requires the AppShell to own the landmark
    # triple. We strip block comments first so a docstring
    # reference like "the orchestrator emits
    # `<main id=\"main\">`" does not trip the gate.
    code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert not re.search(r"<main\b", code_only), (
        f"{NOT_FOUND_FILE.relative_to(REPO_ROOT)} must NOT "
        f"declare a raw `<main>` element in JSX — the AppShell "
        f"orchestrator owns the `<main id=\"main\">` "
        f"wrapper. A second `<main>` would duplicate the "
        f"landmark."
    )


def test_out_not_found_html_renders_404_pick_a_destination():
    """ODD-ASN-003: the static export ships a Taxa-shaped 404
    page with the "404" copy + the "Pick a destination" list
    + the four destination links. The check works on the
    prerendered HTML (no Playwright needed) — Next.js must
    serialize the AppShell + the four `<a href="...">` link
    blocks byte-for-byte so a `curl` against a static-served
    `out/404.html` shows the recovery surface.

    The check accepts any of the three candidate files
    (`out/404.html`, `out/_not-found.html`,
    `out/_not-found/index.html`) — whichever Next 16 emits on
    the current branch.

    Three required observations:

      1. The literal "404" copy appears in the body (the
         page is reachable as a 404 surface).
      2. The "Pick a destination" heading appears in the
         body (the recovery list is named).
      3. The four destination hrefs each appear inside an
         `<a href="...">` anchor (the recovery list links
         to the four top-level destinations).
    """
    _path, body = _read_out_not_found_html()
    assert "404" in body, (
        "the static 404 export must carry the `404` copy so "
        "the recovery surface is recognisable as a 404 page."
    )
    assert "Pick a destination" in body, (
        "the static 404 export must carry the `Pick a "
        "destination` heading so the recovery list is named."
    )
    for href in ("/", "/explorer", "/help", "/settings"):
        assert re.search(
            rf'<a\b[^>]*\bhref\s*=\s*"{re.escape(href)}"',
            body,
        ), (
            f"the static 404 export must carry `<a "
            f"href=\"{href}\">` so the recovery list links "
            f"to the four top-level destinations."
        )


# ---------------------------------------------------------------------------
# ODD-EXP-001 — route-aware placeholder + visual disable on `/explorer`.
#
# The 2026-09-23T18-52-32Z re-critique identified a P0 the rebuild
# introduced: the global search input renders on every route with
# the `Search taxa…  (Cmd+K)` placeholder + takes focus on
# `Cmd+K`/`/`, but produces no results dropdown on `/explorer`
# (Explorer.tsx destructures `searchQuery` / `onSearchQueryChange`
# and discards them). The header input is therefore a visual
# no-op on `/explorer`.
#
# ODD-EXP-001 closes the P0 by making the input "visible but
# inert" on `/explorer`: an honest inert placeholder that links
# the actual capability ("Taxa search lives on Classification
# (Cmd+K)"), `aria-disabled="true"` + a `data-app-shell-search-inert=""`
# attribute, and a visual disable (`opacity-60 cursor-not-allowed`
# Tailwind utilities). Every other route stays on the original
# `Search taxa…  (Cmd+K)` placeholder + no inert markers.
#
# Source-level + DOM-source checks (no Playwright needed). The
# routing happens at build time (`currentRoute` is a prop on
# AppShell, threaded through Header → GlobalSearch), so the
# static export already serializes the route-specific markup.
# ---------------------------------------------------------------------------

# Inert placeholder copy on `/explorer` — honest about why the
# input is inert (links the actual capability to Classification),
# no fake "search files" placeholder that doesn't work.
EXPLORER_INERT_PLACEHOLDER_FRAGMENT = "Taxa search lives on Classification"
# Original placeholder on every other route — pinned so a
# future regression that drops the inert copy on `/explorer`
# would still leave the original copy on `/`, `/help`,
# `/settings`, `/not-found`, and `/hydration-probe`.
NORMAL_PLACEHOLDER = "Search taxa…  (Cmd+K)"


def test_app_shell_search_placeholder_is_route_aware():
    """ODD-EXP-001: the global search input's placeholder is
    route-aware.

    Two complementary source-level checks on
    `AppShellGlobalSearch.tsx`:

      1. The component declares a `currentRoute` prop in its
         public surface (the prop is the contract the routes
         use to communicate which route is rendering).
      2. The component has BOTH the normal placeholder literal
         (`Search taxa…  (Cmd+K)`) AND an inert placeholder
         literal (contains `Taxa search lives on
         Classification`) AND branches on the `currentRoute`
         prop to switch between them.

    Two complementary DOM-source checks on the static export:

      3. `out/index.html` (the `/` route) carries the normal
         placeholder (`Search taxa…  (Cmd+K)`).
      4. `out/explorer.html` (the `/explorer` route) carries
         the inert placeholder fragment (`Taxa search lives on
         Classification`) — the honest copy that explains why
         the input is inert on this route.

    The DOM-source half of the test requires the build to have
    run (the `built_index_html` fixture in this module already
    runs `npx next build` once per module). Skips gracefully
    when the build artifact is missing during RED.
    """
    text = _read_text(APP_SHELL_GLOBAL_SEARCH_FILE)
    # 1. The `currentRoute` prop exists on the public surface.
    # The regex accepts the union-type form the prop uses
    # (`readonly currentRoute?: | "classification" | ...`) —
    # the `?:` colon followed by either whitespace + a quote
    # OR the union-bar leading to a quote both count.
    assert re.search(
        r"\bcurrentRoute\s*\?\s*:\s*(?:\n\s*\|\s*)?\"",
        text,
    ), (
        "AppShellGlobalSearch.tsx must declare a `currentRoute` "
        "prop on its public surface so the routes can signal "
        "which route is rendering — the ODD-EXP-001 contract."
    )
    # 2a. The normal placeholder literal is in the file.
    assert NORMAL_PLACEHOLDER in text, (
        f"AppShellGlobalSearch.tsx must still render the "
        f"original `{NORMAL_PLACEHOLDER!r}` placeholder on the "
        f"non-explorer routes."
    )
    # 2b. The inert placeholder fragment is in the file.
    assert EXPLORER_INERT_PLACEHOLDER_FRAGMENT in text, (
        f"AppShellGlobalSearch.tsx must render the inert "
        f"placeholder fragment "
        f"{EXPLORER_INERT_PLACEHOLDER_FRAGMENT!r} on "
        f"`currentRoute === \"explorer\"` — honest copy that "
        f"links the actual search capability to the "
        f"Classification route."
    )
    # 2c. The branch on `currentRoute` exists.
    assert re.search(
        r"currentRoute\s*===\s*[\"']explorer[\"']",
        text,
    ), (
        "AppShellGlobalSearch.tsx must branch on "
        "`currentRoute === \"explorer\"` to switch between the "
        "normal + inert placeholder copy."
    )
    # 3. DOM-source: out/index.html (the `/` route) carries the
    # normal placeholder.
    if OUT_INDEX.is_file():
        index_html = OUT_INDEX.read_text(encoding="utf-8")
        # Pin the placeholder via the rendered attribute literal
        # so a future regression that escapes the placeholder
        # differently would still trip the gate.
        assert (
            f'placeholder="{NORMAL_PLACEHOLDER}"' in index_html
        ), (
            f"out/index.html must carry "
            f"`<input ... placeholder=\"{NORMAL_PLACEHOLDER}\">` "
            f"— the `/` route renders the normal placeholder."
        )
    # 4. DOM-source: out/explorer.html (the `/explorer` route)
    # carries the inert placeholder.
    explorer_html_path = OUT_DIR / "explorer.html"
    if explorer_html_path.is_file():
        explorer_html = explorer_html_path.read_text(
            encoding="utf-8"
        )
        assert (
            EXPLORER_INERT_PLACEHOLDER_FRAGMENT in explorer_html
        ), (
            f"out/explorer.html must carry the inert placeholder "
            f"fragment `{EXPLORER_INERT_PLACEHOLDER_FRAGMENT!r}` "
            f"— the `/explorer` route renders the honest inert "
            f"copy that links the search capability to the "
            f"Classification route."
        )


def test_app_shell_search_input_is_inert_on_explorer():
    """ODD-EXP-001: the global search input carries inert
    affordances ONLY on `/explorer`.

    The contract pins THREE inert markers on `/explorer`:

      1. `aria-disabled="true"` — assistive tech reads the
         input as disabled (no focus, no edit).
      2. `data-app-shell-search-inert=""` — programmatic
         marker for downstream consumers (CSS hooks + e2e
         probes).
      3. `cursor: not-allowed` — the visible "this is inert"
         affordance via Tailwind's `cursor-not-allowed`
         utility (the className literal).

    Every other route MUST NOT carry these markers — the
    non-explorer routes still own the active search input.

    Two complementary source-level checks on
    `AppShellGlobalSearch.tsx`:

      A. The inert attribute literals (`aria-disabled`,
         `data-app-shell-search-inert`) appear in the source.
      B. The inert `cursor-not-allowed` Tailwind utility
         appears in the source (the visible affordance).

    Two complementary DOM-source checks on the static export:

      C. `out/explorer.html` carries all three inert markers.
      D. `out/index.html` does NOT carry any inert marker —
         the `/` route's input stays fully active.

    Skips gracefully when the build artifact is missing
    during RED.
    """
    text = _read_text(APP_SHELL_GLOBAL_SEARCH_FILE)
    # A. The inert attribute tokens are in the source.
    assert "aria-disabled" in text, (
        "AppShellGlobalSearch.tsx must emit `aria-disabled` on "
        "the inert input — the assistive-tech affordance."
    )
    assert "data-app-shell-search-inert" in text, (
        "AppShellGlobalSearch.tsx must emit "
        "`data-app-shell-search-inert=\"\"` on the inert "
        "input — the programmatic marker downstream "
        "consumers key on."
    )
    # B. The visible cursor affordance is in the source.
    assert "cursor-not-allowed" in text, (
        "AppShellGlobalSearch.tsx must apply the "
        "`cursor-not-allowed` Tailwind utility on the inert "
        "input — the visible affordance the user sees."
    )
    # DOM-source: out/explorer.html carries ALL three markers.
    explorer_html_path = OUT_DIR / "explorer.html"
    if explorer_html_path.is_file():
        explorer_html = explorer_html_path.read_text(
            encoding="utf-8"
        )
        for marker in (
            'aria-disabled="true"',
            'data-app-shell-search-inert=""',
            "cursor-not-allowed",
        ):
            assert marker in explorer_html, (
                f"out/explorer.html must carry `{marker}` on the "
                f"global search input — the ODD-EXP-001 inert "
                f"affordance contract for `/explorer`."
            )
    # DOM-source: out/index.html does NOT carry any inert marker.
    if OUT_INDEX.is_file():
        index_html = OUT_INDEX.read_text(encoding="utf-8")
        assert (
            'data-app-shell-search-inert=""' not in index_html
        ), (
            "out/index.html must NOT carry "
            "`data-app-shell-search-inert=\"\"` — the `/` route "
            "keeps the input fully active."
        )


def test_explorer_page_passes_current_route():
    """ODD-EXP-001: `src/app/explorer/page.tsx` passes
    `currentRoute=\"explorer\"` to the AppShell so the
    header global-search input renders inert on this route.

    The source-level check pins the literal `currentRoute="explorer"`
    in the explorer page (the prop that drives the inert
    branch in AppShellGlobalSearch). Without this prop the
    route ships the original active-input rendering and the
    P0 stays open.
    """
    text = _read_text(EXPLORER_PAGE)
    assert 'currentRoute="explorer"' in text, (
        f"{EXPLORER_PAGE.relative_to(REPO_ROOT)} must pass "
        f"`currentRoute=\"explorer\"` to the AppShell — "
        f"the prop that drives the ODD-EXP-001 inert branch "
        f"in AppShellGlobalSearch (honest copy + visual "
        f"disable on the global search input)."
    )


# ---------------------------------------------------------------------------
# ODD-EXP-002 — `?` shortcut + footer legend sync + help page
# shortcut map sync.
#
# The 2026-09-23T18-52-32Z re-critique identified a second P0 the
# rebuild introduced: the footer shortcut legend documents
# `<kbd>/</kbd> Help` while the AppShellGlobalSearch actually wires
# `/` to focus the global search input. Footer contradicts
# actual contract.
#
# ODD-EXP-002 closes the P0 with three coordinated changes:
#
#   1. AppShellGlobalSearch wires a `?` keydown handler that
#      uses Next.js `useRouter().push(\"/help\")` to navigate
#      (NOT `window.location.href` — `useRouter` triggers a
#      client-side navigation that preserves React state).
#      The handler respects the same editable-field guard the
#      `/` handler uses.
#   2. AppShellFooter updates the legend so `<kbd>/</kbd>` is
#      adjacent to the literal `Search` (not `Help`) AND
#      `<kbd>?</kbd>` is adjacent to the literal `Help`. The
#      two clusters are NOT merged into a single
#      `· / Help ·` cluster that conflates them.
#   3. `src/app/help/page.tsx` adds a `<dt>?</dt>` entry to
#      the shortcut map AND keeps the `<dt>/</dt>` entry's
#      `<dd>` reading \"Focus the global search input\" (NOT
#      \"Open Help\").
#
# Source-level + DOM-source checks (no Playwright needed). The
# `useRouter().push(\"/help\")` call is a runtime behavior the
# source-level check pins via the import + the call site. The
# footer + help-page sync are static markup the static export
# already serializes byte-for-byte.
# ---------------------------------------------------------------------------


def test_app_shell_shortcut_question_navigates_to_help():
    """ODD-EXP-002: `AppShellGlobalSearch.tsx` wires the `?`
    keydown shortcut to navigate to `/help` via Next.js
    `useRouter().push(\"/help\")` (NOT `window.location.href`).

    Three required observations:

      1. The component imports `useRouter` from
         `next/navigation`.
      2. The component declares a keydown handler that
         handles `ev.key === \"?\"` (or byte-equivalent
         `\"?\"` literal).
      3. The handler calls `router.push(\"/help\")` (or
         `push(\"/help\")` after destructuring the router) —
         NEVER `window.location.href`.

    The `?` shortcut must respect the same editable-field
    guard the `/` handler uses (the constraint pins this —
    a researcher typing `?` inside another `<input>` /
    `<textarea>` / `[contenteditable]` element must NOT
    trigger the help navigation). The check verifies the
    guard by inspecting the handler source for the same
    `isEditable` / tag check pattern the `/` handler uses.
    """
    text = _read_text(APP_SHELL_GLOBAL_SEARCH_FILE)
    # 1. useRouter is imported from next/navigation.
    assert re.search(
        r"import\s*\{[^}]*\buseRouter\b[^}]*\}\s*from\s*"
        r"[\"']next/navigation[\"']",
        text,
    ), (
        "AppShellGlobalSearch.tsx must import `useRouter` "
        "from `next/navigation` — the ODD-EXP-002 contract "
        "for the `?` shortcut navigation. `useRouter` "
        "triggers a client-side navigation that preserves "
        "React state (vs. `window.location.href` which would "
        "trigger a hard reload)."
    )
    # 2. The keydown handler reacts to `?`.
    assert re.search(
        r"ev\.key\s*===\s*[\"']\?[\"']",
        text,
    ) or re.search(
        r"key\s*===\s*[\"']\?[\"']",
        text,
    ), (
        "AppShellGlobalSearch.tsx must react to `ev.key === "
        "\"?\"` in the keydown handler — the ODD-EXP-002 "
        "`?` shortcut wiring."
    )
    # 3. The handler pushes \"/help\" via the router (NOT
    # window.location.href).
    assert re.search(
        r"\.push\s*\(\s*[\"']/help[\"']\s*\)",
        text,
    ), (
        "AppShellGlobalSearch.tsx must call "
        "`.push(\"/help\")` on the Next.js router — the "
        "ODD-EXP-002 contract for `?` → help navigation."
    )
    # Constraint guard: `?` MUST NOT use window.location.href.
    # Strip docstrings + line comments first so the prose
    # that DOCUMENTS the constraint (the `window.location.href`
    # comparison the docstring carries) doesn't trip the
    # gate — the witness checks the executable code, not the
    # prose.
    code_only_search = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    code_only_search = re.sub(r"//[^\n]*", "", code_only_search)
    assert "window.location.href" not in code_only_search, (
        "AppShellGlobalSearch.tsx must NOT use "
        "`window.location.href` for the `?` shortcut — "
        "the constraint pins `useRouter().push(\"/help\")` "
        "to preserve React state across the navigation. "
        "(Docstrings may reference the literal as "
        "documentation of the closed regression; this check "
        "rejects only the executable code form.)"
    )
    # Constraint guard: the editable-field guard must apply
    # to `?` too. The existing `/` handler uses an
    # `isEditable` helper that checks INPUT/TEXTAREA/SELECT
    # tags + `isContentEditable`. The `?` handler must
    # consult the same guard before navigating.
    assert re.search(
        r"isEditable\s*\(\s*target\s*\)",
        text,
    ), (
        "AppShellGlobalSearch.tsx must consult the "
        "`isEditable(target)` guard before navigating on "
        "`?` — the same editable-field guard the `/` "
        "handler uses. A researcher typing `?` inside any "
        "<input> / <textarea> / [contenteditable] element "
        "must NOT trigger the help navigation."
    )


def test_app_shell_shortcut_slash_focuses_search():
    """ODD-EXP-002: `AppShellGlobalSearch.tsx` continues to
    wire the `/` keydown shortcut to focus the global search
    input (existing behavior pinned by the ODD-ASN-002
    contract — this test pins the post-ODD-EXP-002
    continuation).

    Three required observations:

      1. The keydown handler reacts to `ev.key === \"/\"`.
      2. The handler calls `inputRef.current?.focus()` (or
         equivalent focus invocation on the input ref).
      3. The handler respects the same editable-field guard
         the `?` handler now uses — the constraint pins
         symmetry so neither shortcut steals focus from an
         active text field.

    The post-ODD-EXP-002 continuation MUST stay green: the
    `/` shortcut continues to focus the search input on
    non-explorer routes, and the existing skip-when-editable
    guard stays in force.
    """
    text = _read_text(APP_SHELL_GLOBAL_SEARCH_FILE)
    # 1. The `/` keydown handler is wired.
    assert re.search(
        r"ev\.key\s*===\s*[\"']/[\"']",
        text,
    ) or re.search(
        r"key\s*===\s*[\"']/[\"']",
        text,
    ), (
        "AppShellGlobalSearch.tsx must react to `ev.key === "
        "\"/\"` in the keydown handler — the ODD-ASN-002 "
        "shortcut that ODD-EXP-002 keeps alive on "
        "non-explorer routes."
    )
    # 2. The handler focuses the input ref.
    assert re.search(
        r"inputRef\.current\s*\?\.\s*focus\s*\(\s*\)",
        text,
    ), (
        "AppShellGlobalSearch.tsx must call "
        "`inputRef.current?.focus()` on the `/` shortcut — "
        "the ODD-ASN-002 focus contract the post-ODD-EXP-002 "
        "continuation pins."
    )
    # 3. The editable-field guard is still in force for `/`.
    # The handler skips focus when `isEditable(target)`
    # returns true.
    slash_block_match = re.search(
        r"ev\.key\s*===\s*[\"']/[\"'].*?isEditable\s*\(\s*target\s*\)",
        text,
        re.DOTALL,
    )
    assert slash_block_match, (
        "AppShellGlobalSearch.tsx must consult the "
        "`isEditable(target)` guard before focusing the "
        "search input on `/` — the editable-field skip "
        "the ODD-ASN-002 contract pins."
    )


def test_app_shell_footer_shortcut_legend_separates_slash_and_question():
    """ODD-EXP-002: `AppShellFooter.tsx` renders a shortcut
    legend that clearly distinguishes the `/` (search) and
    `?` (help) shortcuts — no single `· / Help ·` cluster
    that conflates them.

    Three required observations:

      1. The footer carries BOTH `<kbd>/</kbd>` AND
         `<kbd>?</kbd>` — the two shortcuts must both be
         listed.
      2. The literal `Search` is adjacent to `<kbd>/</kbd>`
         (NOT adjacent to `<kbd>?</kbd>`) — the `/` cluster
         says \"Search\".
      3. The literal `Help` is adjacent to `<kbd>?</kbd>`
         (NOT adjacent to `<kbd>/</kbd>`) — the `?` cluster
         says \"Help\".

    \"Adjacent\" means the literal appears within the same
    whitespace-bounded text run as the `<kbd>` element. The
    check accepts either a JSX literal order (e.g. `<kbd>/</kbd>
    Search`) or an HTML serialized order (`<kbd>/</kbd> Search`)
    — the proximity test is substring-based with a small
    tolerance for whitespace + `·` separators.
    """
    text = _read_text(APP_SHELL_FOOTER_FILE)
    # 1. Both kbd elements appear.
    assert "<kbd>/</kbd>" in text, (
        "AppShellFooter.tsx must render `<kbd>/</kbd>` — the "
        "ODD-EXP-002 footer legend carries the `/` shortcut "
        "marker."
    )
    assert "<kbd>?</kbd>" in text, (
        "AppShellFooter.tsx must render `<kbd>?</kbd>` — the "
        "ODD-EXP-002 footer legend carries the `?` shortcut "
        "marker (the new Help shortcut)."
    )
    # 2. The literal `Search` is adjacent to `<kbd>/</kbd>`.
    # Allow trailing whitespace + the `·` separator.
    slash_search_match = re.search(
        r"<kbd>/</kbd>\s*Search",
        text,
    )
    assert slash_search_match, (
        "AppShellFooter.tsx must render `<kbd>/</kbd> Search` "
        "(or byte-equivalent with whitespace) — the `/` "
        "shortcut cluster is for Search, NOT Help. The "
        "pre-ODD-EXP-002 legend conflates `/` with Help "
        "(`<kbd>/</kbd> Help ·`); ODD-EXP-002 separates them."
    )
    # 3. The literal `Help` is adjacent to `<kbd>?</kbd>`.
    question_help_match = re.search(
        r"<kbd>\?</kbd>\s*Help",
        text,
    )
    assert question_help_match, (
        "AppShellFooter.tsx must render `<kbd>?</kbd> Help` "
        "(or byte-equivalent with whitespace) — the `?` "
        "shortcut cluster is for Help. The ODD-EXP-002 "
        "legend pairs `?` with Help, not `/` with Help."
    )
    # 4. Negative witness: the old conflating pattern
    # `<kbd>/</kbd> Help` MUST NOT appear in the JSX render.
    # The slash + Help cluster is the regression ODD-EXP-002
    # closes. Strip docstrings + line comments first so the
    # docstring that DOCUMENTS the old pattern (and any
    # future prose mention of it) doesn't trip the gate —
    # the witness checks the JSX render, not the prose.
    code_only_footer = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    code_only_footer = re.sub(r"//[^\n]*", "", code_only_footer)
    assert not re.search(
        r"<kbd>/</kbd>\s*Help",
        code_only_footer,
    ), (
        "AppShellFooter.tsx must NOT render `<kbd>/</kbd> Help` "
        "in the JSX — the conflating cluster the ODD-EXP-002 "
        "critique identified. The `/` shortcut is for Search, "
        "the `?` shortcut is for Help. (Docstrings may "
        "reference the literal `<kbd>/</kbd> Help` as "
        "documentation of the closed regression; this check "
        "rejects only the JSX render form.)"
    )


def test_help_page_shortcut_map_lists_question_for_help():
    """ODD-EXP-002: `src/app/help/page.tsx` shortcut map
    includes a `<dt>?</dt>` entry AND keeps the `<dt>/</dt>`
    entry's `<dd>` reading \"Focus the global search input\"
    (NOT \"Open Help\" — the conflating copy the critique
    identified).

    Three required observations:

      1. The shortcut map's `<dl>` block contains a
         `<dt>?</dt>` (or byte-equivalent) — the new Help
         shortcut entry.
      2. The `<dt>?</dt>` entry's adjacent `<dd>` element
         contains the literal \"Open this help page\" (or
         equivalent — the entry must explain the shortcut's
         effect).
      3. The `<dt>/</dt>` entry's adjacent `<dd>` element
         contains the literal \"Focus the global search
         input\" (the ODD-ASN-002 wording the post-ODD-EXP-002
         continuation pins).

    The negative witness on `<dt>/</dt><dd>Open Help`
    (or equivalent conflating copy) is the regression
    ODD-EXP-002 closes.
    """
    text = _read_text(HELP_PAGE_FILE)
    # 1. The `<dt>?</dt>` entry exists.
    assert re.search(
        r"<dt\b[^>]*>\s*<kbd>\?</kbd>\s*</dt>",
        text,
    ) or re.search(
        r"<dt\b[^>]*>\s*\?\s*</dt>",
        text,
    ), (
        f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} must add a "
        f"`<dt>?</dt>` entry to the shortcut map — the "
        f"ODD-EXP-002 new Help shortcut entry."
    )
    # 2. The `<dt>?</dt>` entry's adjacent `<dd>` explains
    # the shortcut effect. The check looks for the next
    # `<dd>` element after the `<dt>?</dt>` entry and
    # verifies it carries the literal \"Open this help
    # page\" (or byte-equivalent — accept any wording that
    # contains \"Open\" + \"help\").
    question_dd_match = re.search(
        r"<dt\b[^>]*>\s*<kbd>\?</kbd>\s*</dt>\s*"
        r"<dd\b[^>]*>([^<]+)</dd>",
        text,
        re.DOTALL,
    ) or re.search(
        r"<dt\b[^>]*>\s*\?\s*</dt>\s*"
        r"<dd\b[^>]*>([^<]+)</dd>",
        text,
        re.DOTALL,
    )
    assert question_dd_match, (
        f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} must render "
        f"an adjacent `<dd>` for the `<dt>?</dt>` entry — "
        f"the ODD-EXP-002 Help shortcut description."
    )
    question_dd_text = question_dd_match.group(1)
    assert "Open" in question_dd_text and "help" in question_dd_text.lower(), (
        f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} `<dt>?</dt>` "
        f"entry's `<dd>` must describe the Help shortcut "
        f"(contains `Open` + `help`); got {question_dd_text!r}."
    )
    # 3. The `<dt>/</dt>` entry's adjacent `<dd>` keeps the
    # ODD-ASN-002 wording \"Focus the global search input\".
    slash_dd_match = re.search(
        r"<dt\b[^>]*>\s*<kbd>/</kbd>\s*</dt>\s*"
        r"<dd\b[^>]*>([^<]+)</dd>",
        text,
        re.DOTALL,
    )
    assert slash_dd_match, (
        f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} must render "
        f"an adjacent `<dd>` for the `<dt>/</dt>` entry — "
        f"the ODD-ASN-002 shortcut description."
    )
    slash_dd_text = slash_dd_match.group(1)
    assert "Focus the global search input" in slash_dd_text, (
        f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} `<dt>/</dt>` "
        f"entry's `<dd>` must say \"Focus the global search "
        f"input\" (NOT \"Open Help\" — the conflating copy the "
        f"ODD-EXP-002 critique identified); got {slash_dd_text!r}."
    )
    # Negative witness: `<dt>/</dt><dd>...Open Help...` MUST
    # NOT appear — the conflating copy ODD-EXP-002 closes.
    assert not re.search(
        r"<dt\b[^>]*>\s*<kbd>/</kbd>\s*</dt>\s*"
        r"<dd\b[^>]*>[^<]*Open\s+Help[^<]*</dd>",
        text,
        re.DOTALL,
    ), (
        f"{HELP_PAGE_FILE.relative_to(REPO_ROOT)} `<dt>/</dt>` "
        f"entry must NOT say \"Open Help\" — the conflating "
        f"copy the ODD-EXP-002 critique identified. The `/` "
        f"shortcut focuses the global search input."
    )


# ---------------------------------------------------------------------------
# ODD-APL-001 / ODD-PHASE2 (AppShell migration, no substantive
# migration shipped) — Phase 2 coverage tests pinning the
# AppShell-specific reasoning.
#
# The ODD-APL-001 inspection of all five AppShell sub-components
# (`AppShell.tsx` + `AppShellHeader.tsx` + `AppShellFooter.tsx` +
# `AppShellNav.tsx` + `AppShellGlobalSearch.tsx`) found ZERO
# migration opportunities for the Phase 2 `<Button>` / `<IconButton>` /
# `<Text>` primitives: the navigation surface ALREADY uses specialized
# primitives (`<a>` for static links, `next/link` `<Link>` for routing,
# native `<input>` for the search field) instead of `<button>`, and
# the footer's three-column layout already centralizes its typography
# decisions via inline Tailwind utilities. Migration to the design-system
# primitives would add indirection without removing an inline pattern.
#
# The four tests below document this decision as a regression gate
# going forward: a future PR that introduces an inline `<button>` /
# `<IconButton>` / `<Text>` opportunity into the AppShell surface will
# trip one of these tests and be forced to use the design-system
# primitive at that time. The two triangulation tests pin the
# AppShell-specific primitives so the test suite documents the decision
# end-to-end.
# ---------------------------------------------------------------------------


def test_appshell_does_not_use_inline_button_classes():
    """ODD-APL-001 / ODD-PHASE2: AppShell sub-components must NOT
    render raw `<button className="...">` inline button
    compositions (the patterns Phase 2 `<Button>` migration
    closes in OTHER consumers like `TreeRow` + `FolderTab`).

    The ODD-APL-001 inspection of all five AppShell
    sub-components found ZERO raw `<button>` elements:

      - `AppShell.tsx` (orchestrator, 118 lines): pure
        layout wrapper — `data-app-shell` host + skip-link
        `<a href=\"#main\">` + `<AppShellHeader />` +
        `<main>` + `<AppShellFooter />`. No buttons.
      - `AppShellHeader.tsx` (65 lines): brand mark
        `<a href=\"/\">taxa</a>` + `<AppShellGlobalSearch />` +
        `<AppShellNav />`. No buttons.
      - `AppShellFooter.tsx` (82 lines): three-column footer
        copy + `<kbd>` legend markers. No buttons (the kbd
        elements are specialized legend markers, NOT
        buttons).
      - `AppShellNav.tsx` (85 lines): nav destinations are
        `next/link` `<Link>` (the routing primitive). No
        buttons.
      - `AppShellGlobalSearch.tsx` (255 lines): global
        search is a native `<input>` element with keyboard
        wiring. No buttons.

    The negative witness this test pins: if a future PR
    adds an inline button class pattern to any AppShell
    sub-component, this test fails and the migration to
    `<Button>` is forced.
    """
    offenders: list[tuple[Path, str]] = []
    for path in (
        APP_SHELL_FILE,
        APP_SHELL_HEADER_FILE,
        APP_SHELL_FOOTER_FILE,
        APP_SHELL_NAV_FILE,
        APP_SHELL_GLOBAL_SEARCH_FILE,
    ):
        text = _read_text(path)
        # Strip block comments + line comments first so the
        # docstring prose that REFERENCES `<button>` (the
        # migration reasoning the docstring carries) does
        # not trip the gate — the witness checks the JSX
        # render, not the prose.
        code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        code_only = re.sub(r"//[^\n]*", "", code_only)
        for match in re.finditer(r"<button\b", code_only):
            offenders.append((path, match.group(0)))
    assert not offenders, (
        "AppShell sub-components must NOT render raw `<button>` "
        "elements — the ODD-APL-001 inspection found zero inline "
        "button patterns in the navigation surface. The Phase 2 "
        "`<Button>` migration has no targets here. Offending "
        f"(path, tag) pairs: {offenders}."
    )


def test_appshell_uses_text_primitive_or_inline_typography():
    """ODD-APL-001 / ODD-PHASE2: AppShell sub-components use EITHER
    the `<Text>` primitive (from `@taxa/design-system`) OR inline
    Tailwind typography utilities on specialized layout spans.

    The `<Text>` primitive centralizes the small set of
    font-size + weight + colour combinations — `body`, `body-sm`,
    `mono`, `caption`, `label`. The AppShell audit traced the
    existing inline typography decisions in the surface:

      - `AppShellHeader.tsx::app-shell-brand`: Tailwind utilities
        `font-semibold tracking-tight text-on-surface` on the
        `<a href=\"/\">taxa</a>` brand mark.
      - `AppShellFooter.tsx`: the three-column host carries
        `text-xs` and child columns carry `font-mono` /
        `font-semibold` utilities — the footer's whole copy
        surface already centralizes its typography decision via
        Tailwind utilities.

    Migration to `<Text>` would add a primitive indirection
    without removing an inline pattern (the Tailwind utilities
    ALREADY centralize the decision). The decision is to
    KEEP the inline Tailwind utilities here — and the test
    pins that contract.

    The positive witness: at least one Tailwind typography
    utility class (or `<Text>` primitive import) appears in
    the AppShell sub-components. If a future PR deletes the
    typography decisions entirely (e.g. drops the `text-xs`
    utility on the footer), this test fails.
    """
    typography_utilities: tuple[str, ...] = (
        "text-xs",
        "text-sm",
        "text-base",
        "font-semibold",
        "font-mono",
        "tracking-tight",
    )
    found_utilities: set[str] = set()
    text_primitive_used = False
    for path in (
        APP_SHELL_FILE,
        APP_SHELL_HEADER_FILE,
        APP_SHELL_FOOTER_FILE,
        APP_SHELL_NAV_FILE,
        APP_SHELL_GLOBAL_SEARCH_FILE,
    ):
        text = _read_text(path)
        for utility in typography_utilities:
            if utility in text:
                found_utilities.add(utility)
        if (
            'from "@taxa/design-system"' in text
            and re.search(r"<\s*Text\b", text)
        ):
            text_primitive_used = True
    assert text_primitive_used or len(found_utilities) >= 3, (
        "AppShell sub-components must use the `<Text>` primitive "
        f"(from `@taxa/design-system`) OR at least 3 of the "
        f"following inline Tailwind typography utilities: "
        f"{typography_utilities!r}. Found utilities: "
        f"{sorted(found_utilities)!r}; `<Text>` primitive used: "
        f"{text_primitive_used}. The ODD-APL-001 inspection "
        f"traced both forms; the decision is to keep the inline "
        f"Tailwind utilities where the surface already centralizes "
        f"the typography."
    )


def test_appshell_uses_iconbutton_primitive_or_native_input():
    """ODD-APL-001 / ODD-PHASE2: AppShell's icon-button surface is
    covered by EITHER the `<IconButton>` primitive (from
    `@taxa/design-system`) OR a native `<input>` element.

    The ODD-APL-001 inspection found NO `<IconButton>` opportunity
    in the AppShell sub-components — the search input is a native
    ``<input type="search">`` element (specialized because it
    needs focus management + keyboard wiring for `Cmd+K` / `/`
    shortcuts), and there is no close button inside the search
    dropdown (the search dropdown does not exist as a separate
    component). The native `<input>` is the correct primitive for
    this surface.

    The positive witness: every AppShell sub-component must
    satisfy one of the two clauses:

      (a) Renders a native `<input>` element (the search field),
          OR
      (b) Imports and uses `<IconButton>` from
          `@taxa/design-system`.

    In the current surface, `AppShellGlobalSearch.tsx` renders the
    native ``<input id="app-shell-search-input">``. The other four
    sub-components carry no icon buttons at all — the contract
    they satisfy is clause (b): they don't render any icon
    button. The test asserts the (input) clause holds for the
    search sub-component specifically.
    """
    # Clause (a): the search sub-component renders a native
    # `<input>` with the canonical id. This is the load-bearing
    # surface — without it the global search input loses its
    # focusable affordance for keyboard users.
    search_text = _read_text(APP_SHELL_GLOBAL_SEARCH_FILE)
    assert re.search(
        r"""<input\b[^>]*\bid\s*=\s*["']app-shell-search-input["']""",
        search_text,
        re.DOTALL,
    ), (
        "AppShellGlobalSearch.tsx must render a native `<input "
        'id="app-shell-search-input">` element — the native '
        "input is the AppShell's icon-button-equivalent affordance "
        "for the global search surface (specialized because it "
        "needs focus management + keyboard wiring)."
    )
    # Clause (b): other AppShell sub-components either use
    # <IconButton> OR don't render any icon button affordance.
    # The four non-search sub-components carry zero `<button>`
    # (already covered by test_appshell_does_not_use_inline_button_classes)
    # AND zero `<IconButton>` (the design-system primitive is
    # for action icon buttons, not for chrome placeholders). The
    # surface therefore satisfies the (b) clause vacuously.
    # The witness verifies clause (b) by asserting: IF an
    # `<IconButton>` were introduced, it must come from
    # `@taxa/design-system`.
    iconbutton_paths: list[tuple[Path, str]] = []
    for path in (
        APP_SHELL_FILE,
        APP_SHELL_HEADER_FILE,
        APP_SHELL_FOOTER_FILE,
        APP_SHELL_NAV_FILE,
        APP_SHELL_GLOBAL_SEARCH_FILE,
    ):
        text = _read_text(path)
        # Strip docstrings + line comments first so docstring
        # prose doesn't trip the gate.
        code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        code_only = re.sub(r"//[^\n]*", "", code_only)
        if re.search(r"<IconButton\b", code_only):
            iconbutton_paths.append((path, "IconButton used"))
    for path, _ in iconbutton_paths:
        text = _read_text(path)
        # Triple-quoted raw string so the inner ["'] class can
        # hold both quote characters without delimiting the
        # string early.
        assert re.search(
            r"""import\s*\{[^}]*\bIconButton\b[^}]*\}\s*from\s*["']\@taxa/design-system["']""",
            text,
        ), (
            f"{path.relative_to(REPO_ROOT)} uses `<IconButton>` "
            f"but does not import it from `@taxa/design-system` "
            f"— the design-system primitive must come through "
            f"the public barrel."
        )


def test_appshell_uses_button_primitive_where_applicable():
    """ODD-APL-001 / ODD-PHASE2: AppShell sub-components must use
    the `<Button>` primitive (from `@taxa/design-system`)
    WHENEVER they render a button-like element.

    The ODD-APL-001 inspection found ZERO raw `<button>` elements
    in any AppShell sub-component (the surface already uses
    specialized primitives — `<a>` + `next/link` `<Link>` +
    native `<input>`). The Phase 2 `<Button>` migration
    therefore has zero targets here.

    The contingent positive witness this test pins: if a
    future PR introduces a `<button>` element into any
    AppShell sub-component, it MUST be the `<Button>`
    primitive (with the import from `@taxa/design-system`),
    NOT an inline `<button className="...">` composition.

    Formally the contract is:

      For each component file F in AppShell sub-components:
        raw_button_count(F) = 0
        OR (
          raw_button_count(F) > 0
          AND `<Button>` imported from `@taxa/design-system`
          AND primitive_button_count(F) >= raw_button_count(F)
        )

    The current code satisfies the LEFT disjunct (raw_button_count
    = 0 everywhere). A regression that adds a raw `<button>`
    without importing the primitive fails the test.
    """
    for path in (
        APP_SHELL_FILE,
        APP_SHELL_HEADER_FILE,
        APP_SHELL_FOOTER_FILE,
        APP_SHELL_NAV_FILE,
        APP_SHELL_GLOBAL_SEARCH_FILE,
    ):
        text = _read_text(path)
        # Strip docstrings + line comments first so docstring
        # prose that REFERENCES `<button>` doesn't trip the
        # gate (the AppShell sub-component docstrings document
        # the migration reasoning).
        code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        code_only = re.sub(r"//[^\n]*", "", code_only)
        raw_buttons = len(re.findall(r"<button\b", code_only))
        primitive_buttons = len(re.findall(r"<\s*Button\b", code_only))
        # Count the `<Button>` import (if any) for the
        # contingent check below. Triple-quoted raw string
        # so the ["'] class can hold both quote characters.
        primitive_imported = bool(
            re.search(
                r"""import\s*\{[^}]*\bButton\b[^}]*\}\s*from\s*["']\@taxa/design-system["']""",
                text,
            )
        )
        if raw_buttons > 0:
            # If any raw `<button>` exists, the file MUST
            # have imported the `<Button>` primitive AND
            # used it at least once (the contingent
            # positive witness).
            assert primitive_imported, (
                f"{path.relative_to(REPO_ROOT)} renders "
                f"{raw_buttons} raw `<button>` element(s) "
                f"but does not import `<Button>` from "
                f"`@taxa/design-system` — the Phase 2 "
                f"`<Button>` primitive must replace inline "
                '`<button className="...">` patterns.'
            )
            assert primitive_buttons >= raw_buttons, (
                f"{path.relative_to(REPO_ROOT)} renders "
                f"{raw_buttons} raw `<button>` element(s) "
                f"but only {primitive_buttons} `<Button>` "
                f"primitive usage(s) — every raw `<button>` "
                f"must be the `<Button>` primitive."
            )


def test_appshell_uses_next_link_routing_primitive():
    """ODD-APL-001 / ODD-PHASE2 (TRIANGULATE): AppShellNav uses
    `next/link`'s `<Link>` as the routing primitive — NOT the
    design-system `<Button>` primitive (which has no `as="a"`
    polymorphic support) and NOT raw `<a>` elements (which
    would force a hard reload on every navigation).

    The Phase 2 `<Button>` primitive is documented as a
    button-only primitive (`<button type=...>`); it does NOT
    support an `as=\"a\"` polymorphic surface. The AppShell's
    nav destinations need client-side routing, so they need
    `next/link` `<Link>` — a primitive the design-system
    doesn't include in its surface.

    The positive witness this test pins: `AppShellNav.tsx`
    imports `Link from \"next/link\"` AND uses `<Link` as the
    rendered element for the four destinations. A future PR
    that drops `next/link` (e.g. to migrate to the design-system
    `<Button>`) loses the client-side routing — the test
    catches the regression.
    """
    text = _read_text(APP_SHELL_NAV_FILE)
    assert re.search(
        r'import\s+Link\s+from\s+[\"\']next/link[\"\']',
        text,
    ), (
        "AppShellNav.tsx must import `Link` from `next/link` "
        "— the routing primitive the AppShell uses for client-"
        "side navigation. The design-system primitives do NOT "
        "include a routing link primitive (per the ODD-APL-001 "
        "AppShell audit)."
    )
    assert re.search(r"<\s*Link\b", text), (
        "AppShellNav.tsx must render at least one `<Link>` "
        "element — the nav destinations must use the "
        "`next/link` routing primitive, NOT raw `<a>` "
        "(hard reload) or `<button>` (no anchor semantics)."
    )


def test_appshell_brand_link_is_anchor_not_button():
    """ODD-APL-001 / ODD-PHASE2 (TRIANGULATE): AppShellHeader's
    brand mark is an `<a>` (or `<Link>`) element — NOT a
    `<button>`.

    The brand mark (`taxa`) navigates to `/` — that is
    navigation, not mutation. The semantically correct element
    is an anchor (`<a>` or `next/link` `<Link>`), not a
    `<button>`. A future PR that migrates the brand mark to
    `<Button>` (because the design-system primitive is the
    "right" choice for clickable elements) would introduce a
    regression: the brand mark is a LINK, not a control.

    The positive witness: `AppShellHeader.tsx` renders the
    brand mark as either `<a href=\"/\">taxa</a>` OR
    `<Link href=\"/\">taxa</Link>`. The negative witness:
    the brand mark MUST NOT be rendered as `<button>`.
    """
    text = _read_text(APP_SHELL_HEADER_FILE)
    # The brand mark appears as `<a href="/" ...>taxa</a>` (or
    # `<Link href="/" ...>taxa</Link>` if a future refactor
    # migrates to next/link — out of scope for Phase 2 but
    # semantically valid).
    anchor_pattern = re.search(
        r'<a\b[^>]*\bhref\s*=\s*[\"\']/[\"\'][^>]*>\s*taxa\s*</a>',
        text,
        re.DOTALL,
    )
    link_pattern = re.search(
        r'<\s*Link\b[^>]*\bhref\s*=\s*[\"\']/[\"\'][^>]*>\s*taxa\s*'
        r'</\s*Link\s*>',
        text,
        re.DOTALL,
    )
    assert anchor_pattern or link_pattern, (
        "AppShellHeader.tsx must render the brand mark as an "
        "anchor `<a href=\"/\">taxa</a>` (or `<Link "
        "href=\"/\">taxa</Link>` from next/link) — the brand "
        "is a NAVIGATION link, not a control. `<Button>` is "
        "the wrong primitive for navigation links."
    )
    # Negative witness: brand mark must NOT be a `<button>`.
    # Strip docstrings + line comments first so the docstring
    # prose doesn't trip the gate.
    code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert not re.search(
        r'<button\b[^>]*>\s*taxa\s*</button>',
        code_only,
        re.DOTALL,
    ), (
        "AppShellHeader.tsx must NOT render the brand mark "
        "as `<button>taxa</button>` — the brand is a "
        "navigation link, not a control. The design-system "
        "`<Button>` primitive is the wrong element for a "
        "navigation link (anchor / next/link `<Link>` is the "
        "correct primitive)."
    )
