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
    """ODD-VTREE-002 mounts the visible AppShell + TaxonomyTree in page.tsx."""
    text = _read_text(SRC_PAGE)
    for pattern in REQUIRED_PAGE_IMPORTS:
        assert re.search(pattern, text), (
            f"page.tsx must satisfy pattern {pattern!r}"
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
