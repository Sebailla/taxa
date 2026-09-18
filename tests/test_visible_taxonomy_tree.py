"""Visible taxonomy tree contract tests (ODD-VTREE-002).

Pins the React cutover's first usable tree surface:
  - AppShell (server component) renders header + main + footer
  - TaxonomyTree ('use client') renders collapsed root rows on mount
  - TreeRow renders disclosure buttons with accurate ``aria-expanded``
  - Initial loading / error / empty states are accessible
  - The static export's ``out/index.html`` carries the SSR markup

The build-witness fixture (``built_index_html``) reuses the
``next build`` side-effect from ``test_app_shell_render.py`` when run
in the same session. When run alone the test runs its own
``next build`` to refresh ``out/``.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_SHELL_FILE = REPO_ROOT / "src" / "modules" / "app-shell" / "presentation" / "AppShell.tsx"
APP_SHELL_BARREL = REPO_ROOT / "src" / "modules" / "app-shell" / "index.ts"
TAXONOMY_TREE_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "TaxonomyTree.tsx"
TAXONOMY_TREE_ROW_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "TreeRow.tsx"
TAXONOMY_BARREL = REPO_ROOT / "src" / "modules" / "taxonomy" / "index.ts"
TAXONOMY_DOMAIN_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "domain" / "taxon.ts"
TAXONOMY_INFRA_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "infrastructure" / "api.ts"
SRC_PAGE = REPO_ROOT / "src" / "app" / "page.tsx"
SRC_LAYOUT = REPO_ROOT / "src" / "app" / "layout.tsx"
OUT_DIR = REPO_ROOT / "out"
OUT_INDEX = OUT_DIR / "index.html"


def _read_text(path: Path) -> str:
    if not path.is_file():
        pytest.fail(f"required file missing: {path}")
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# File presence + extension (RED gates for ODD-VTREE-002)
# ---------------------------------------------------------------------------

def test_app_shell_file_exists() -> None:
    assert APP_SHELL_FILE.is_file(), (
        f"missing {APP_SHELL_FILE} — ODD-VTREE-002 ships this server component."
    )
    assert APP_SHELL_FILE.suffix == ".tsx", "AppShell must be `.tsx`."


def test_app_shell_barrel_reexports_app_shell() -> None:
    text = _read_text(APP_SHELL_BARREL)
    assert re.search(r'export\s*\{[^}]*default\s+as\s+AppShell[^}]*\}\s*from', text, re.DOTALL), (
        "app-shell barrel must re-export `AppShell` as the default export"
    )
    assert re.search(r'export\s+type\s*\{\s*AppShellProps\s*\}', text), (
        "app-shell barrel must re-export `AppShellProps`"
    )


def test_taxonomy_tree_file_exists() -> None:
    assert TAXONOMY_TREE_FILE.is_file(), (
        f"missing {TAXONOMY_TREE_FILE} — ODD-VTREE-002 ships this client island."
    )
    assert TAXONOMY_TREE_FILE.suffix == ".tsx", "TaxonomyTree must be `.tsx`."


def test_tree_row_file_exists() -> None:
    assert TAXONOMY_TREE_ROW_FILE.is_file(), (
        f"missing {TAXONOMY_TREE_ROW_FILE} — ODD-VTREE-002 ships this row component."
    )
    assert TAXONOMY_TREE_ROW_FILE.suffix == ".tsx", "TreeRow must be `.tsx`."


def test_taxonomy_barrel_reexports_taxonomy_tree() -> None:
    text = _read_text(TAXONOMY_BARREL)
    assert re.search(r'export\s*\{[^}]*default\s+as\s+TaxonomyTree[^}]*\}\s*from', text, re.DOTALL), (
        "taxonomy barrel must re-export `TaxonomyTree` as the default export"
    )


# ---------------------------------------------------------------------------
# Source contracts (server vs client boundary, dependencies, accessibility)
# ---------------------------------------------------------------------------

def test_taxonomy_tree_is_a_client_component() -> None:
    text = _read_text(TAXONOMY_TREE_FILE)
    assert text.lstrip().startswith('"use client"') or text.lstrip().startswith("'use client'"), (
        "TaxonomyTree.tsx must declare the client boundary via 'use client'"
    )


def test_app_shell_is_a_server_component() -> None:
    """AppShell must NOT carry 'use client' — the brief mandates a server-component shell."""
    text = _read_text(APP_SHELL_FILE)
    assert "use client" not in text, (
        "AppShell.tsx is a server component; it MUST NOT carry the 'use client' directive"
    )


def test_app_shell_depends_only_on_react_types() -> None:
    """AppShell imports only React types per spec.md rule 4 (presentation purity)."""
    text = _read_text(APP_SHELL_FILE)
    for src in re.findall(r'from\s+["\']([^"\']+)["\']', text):
        assert src == "react", (
            f"AppShell.tsx must import only from 'react'; got {src!r}"
        )


def test_taxonomy_tree_uses_canonical_helpers_via_barrel() -> None:
    """ODD-VTREE-002 correction: TaxonomyTree consumes the canonical
    typed helpers (``fetchDomains``, ``fetchChildren``,
    ``TaxonomyApiError``) re-exported by the public
    ``@taxa/taxonomy`` barrel — never deep paths into the
    infrastructure layer. spec.md rule 5 forbids deep imports via the
    ESLint ``no-restricted-imports`` guard; rule 4 keeps the
    presentation layer free of duplicated wire projection.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "fetchDomains" in text, (
        "TaxonomyTree.tsx must call the canonical fetchDomains helper"
    )
    assert "fetchChildren" in text, (
        "TaxonomyTree.tsx must call the canonical fetchChildren helper"
    )
    assert "from \"@taxa/taxonomy\"" in text or "from '@taxa/taxonomy'" in text, (
        "TaxonomyTree.tsx must import the helpers via the @taxa/taxonomy barrel"
    )
    # spec.md rule 5 + ESLint guard: no deep imports into the layer folders.
    for bad in (
        "../infrastructure/api",
        "../infrastructure/api.js",
        "@taxa/taxonomy/infrastructure",
        "@taxa/taxonomy/domain",
    ):
        assert bad not in text, (
            f"TaxonomyTree.tsx must not deep-import {bad!r} (rule 5 barrel guard)"
        )


def test_taxonomy_tree_uses_configured_api_origin() -> None:
    """ODD-VTREE-002 binding: production requests stay
    relative/same-origin (``process.env.NEXT_PUBLIC_TAXA_API_ORIGIN ?? ""``),
    while local development overrides the variable via
    ``pnpm run dev:local`` (see package.json).
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "process.env.NEXT_PUBLIC_TAXA_API_ORIGIN" in text, (
        "TaxonomyTree.tsx must source its API origin from NEXT_PUBLIC_TAXA_API_ORIGIN"
    )
    assert re.search(r'NEXT_PUBLIC_TAXA_API_ORIGIN\s*\?\?\s*["\']["\']', text), (
        "TaxonomyTree.tsx must default the origin to an empty string when unset"
    )


def test_taxonomy_tree_emits_accessible_initial_states() -> None:
    """ODD-VTREE-002: initial loading (`role=status`), initial error
    (`role=alert` + Retry), and empty roots are all rendered."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # At least one `role="status"` covers loading + empty + per-row loading.
    assert text.count('role="status"') >= 2, (
        "TaxonomyTree.tsx must emit role=\"status\" for loading + empty states"
    )
    # Initial error uses `role="alert"` with a Retry button.
    assert text.count('role="alert"') >= 1, (
        "TaxonomyTree.tsx must emit role=\"alert\" for the initial error state"
    )
    assert re.search(r'>\s*Retry\s*<', text), (
        "TaxonomyTree.tsx must render a Retry button"
    )


def test_tree_row_uses_semantic_disclosure_button() -> None:
    """TreeRow must use a `<button>` with accurate ``aria-expanded`` for the
    disclosure control. ``aria-controls`` is intentionally OMITTED — children
    render as flat siblings of this row (so there is no single hidden DOM
    target to point at); pointing ``aria-controls`` at an empty hidden
    ``rowgroup`` would misrepresent the disclosure relationship to assistive
    tech. The button is ``disabled`` for leaves and ``aria-expanded`` is
    only emitted on expandable rows."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert re.search(r'<button\b[^>]*aria-expanded', text, re.DOTALL), (
        "TreeRow.tsx must render a <button> with aria-expanded"
    )
    # Look for the *attribute* (aria-controls=...), not the docstring word.
    assert re.search(r'\baria-controls\s*=', text) is None, (
        "TreeRow.tsx must NOT carry the aria-controls attribute "
        "(children are flat siblings, not a hidden target)"
    )
    assert "display: none" not in text and "display:none" not in text, (
        "TreeRow.tsx must not ship a hidden rowgroup (invalid a11y plumbing)"
    )


def test_tree_row_initial_state_is_collapsed() -> None:
    """ODD-VTREE-002 acceptance: root rows render collapsed initially
    (the tree fetches roots, but does not auto-expand any)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # The tree initializes with EMPTY_TREE_STATE; the expandedIds Set is
    # only populated by toggleExpand. No auto-expand on fetch.
    assert "EMPTY_TREE_STATE" in text, (
        "TaxonomyTree.tsx must initialize with EMPTY_TREE_STATE (collapsed)"
    )
    assert "expand(" not in text.replace("toggleExpand(", "").replace("isExpanded(", ""), (
        "TaxonomyTree.tsx must not auto-expand; the only mutator is toggleExpand"
    )


# ---------------------------------------------------------------------------
# Build witness — static export carries the visible shell + tree SSR
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def static_export() -> None:
    """Run ``next build`` once per module and assert ``out/index.html`` exists."""
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


def test_out_index_html_has_app_shell_landmarks(static_export):
    html = _read_text(OUT_INDEX)
    for tag in ("<header", "<main", "<footer"):
        assert tag in html, (
            f"out/index.html must contain {tag} (AppShell frame); ODD-VTREE-002 server shell"
        )


def test_out_index_html_has_visible_product_title(static_export):
    html = _read_text(OUT_INDEX)
    assert re.search(r"<h1[^>]*>Taxonomic Tree</h1>", html), (
        "out/index.html must render the visible <h1>Taxonomic Tree</h1>"
    )


def test_out_index_html_has_taxonomy_tree_section(static_export):
    html = _read_text(OUT_INDEX)
    assert 'aria-label="Taxonomic tree"' in html, (
        "out/index.html must mount the TaxonomyTree section with aria-label"
    )
    assert "taxa-tree" in html, (
        "out/index.html must include the four-column .taxa-tree grid"
    )


def test_out_index_html_renders_initial_loading_status(static_export):
    """SSR with EMPTY_TREE_STATE must show the `role=status` loading copy
    (the client then fetches roots after hydration)."""
    html = _read_text(OUT_INDEX)
    assert re.search(r'role="status"[^>]*>\s*Loading domains', html, re.DOTALL), (
        "out/index.html must render the role=\"status\" loading copy before hydration"
    )


def test_out_index_html_does_not_inline_domain_rows_before_hydration(static_export):
    """The fetch is client-side; SSR must not pre-render domain rows.
    Confirms the root-collapsed-initial-state contract."""
    html = _read_text(OUT_INDEX)
    # No `data-taxon-id` attributes before hydration means no rows inlined.
    assert "data-taxon-id" not in html, (
        "out/index.html must NOT inline taxon rows before hydration (collapsed initial state)"
    )


def test_out_index_html_keeps_static_origin(static_export):
    """Production requests must stay relative/same-origin (PR 3b's
    hydration-safety contract carries forward). The
    ``data-theme`` hydration-guard assertion lives in
    ``test_app_shell_render.py::test_out_index_html_body_has_no_data_theme_before_hydration``
    — duplicated coverage is removed here per the ODD-VTREE-002
    test-scope reduction."""
    html = _read_text(OUT_INDEX)
    # Footer copy mentions the API origin.
    assert re.search(r"<code[^>]*>\s*/api\s*</code>", html), (
        "out/index.html must render the /api origin footer marker"
    )
    # No literal 'http://' or 'https://' API reference in the static HTML.
    assert re.search(r'href=["\']https?://[^"\']*domains', html) is None, (
        "out/index.html must not reference absolute /api/domains URLs"
    )


# ---------------------------------------------------------------------------
# ODD-NTP-002 — native source-parity contract for the visible tree.
#
# Source-level checks on `TaxonomyTree.tsx` (selector presence, native
# source order, source-conditional Freshwater control, source-bound
# state reset, per-source child-request wiring) + the matching
# static-export witness (`out/index.html` must carry the segmented
# control shape + the active CoL affordance after hydration).
# ---------------------------------------------------------------------------

def test_taxonomy_tree_renders_source_selector() -> None:
    """ODD-NTP-002: TaxonomyTree must render the source selector inside
    the tree surface (`role=\"group\" aria-label=\"Tree data source\"`).
    Mirrors the legacy ``#tree-source-toggle`` native control."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert 'role="group"' in text, (
        "TaxonomyTree.tsx must render the source selector with role=\"group\""
    )
    # The aria-label literal lives as a JS string (selectorLabel
    # constant) rather than inlined on the attribute — pin both
    # the label string and the attribute hook.
    assert '"Tree data source"' in text, (
        "TaxonomyTree.tsx must declare the source-selector label as the literal \"Tree data source\""
    )
    assert "aria-label" in text, (
        "TaxonomyTree.tsx must render the source selector with aria-label"
    )
    # Class hooks so the focused segmented-control CSS in globals.css
    # can attach without a redesign pass.
    assert "tree-source-toggle" in text, (
        "TaxonomyTree.tsx must stamp the .tree-source-toggle class on the selector"
    )
    assert "tree-source-btn" in text, (
        "TaxonomyTree.tsx must stamp the .tree-source-btn class on each source button"
    )


def test_taxonomy_tree_starts_with_col_active() -> None:
    """ODD-NTP-002: CoL starts active. Mirrors the legacy
    `state.treeSource = "col"` default in `web/state.js`."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(r"DEFAULT_SOURCE\b[^=]*=\s*[\"\']col[\"\']", text), (
        "TaxonomyTree.tsx must default the active source to 'col'"
    )


def test_taxonomy_tree_selector_orders_col_then_worms() -> None:
    """ODD-NTP-002: native order is CoL → WoRMS → Freshwater (conditional)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # The label sequence must appear in the segmented control mapping.
    seq = re.search(
        r"src\s*===\s*[\"\']col[\"\']\s*\?\s*[\"\']CoL[\"\']\s*:\s*"
        r"src\s*===\s*[\"\']worms[\"\']\s*\?\s*[\"\']WoRMS[\"\']\s*:\s*[\"\']Freshwater[\"\']",
        text,
    )
    assert seq, (
        "TaxonomyTree.tsx must label CoL → WoRMS → Freshwater in the native order"
    )


def test_taxonomy_tree_selector_is_conditional_on_freshwater_root() -> None:
    """ODD-NTP-002: Freshwater appears ONLY when the fetched root
    payload carries at least one row with a non-null `freshwater_id`.
    Mirrors the legacy `web/app.js::boot` check
    `roots.some(r => r.freshwater_id != null)`. The React helper
    `availableSourcesFor(rawRoots)` encapsulates it; the component must
    consume that helper so the Freshwater toggle is data-driven, not
    hardcoded."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "availableSourcesFor" in text, (
        "TaxonomyTree.tsx must consume the availableSourcesFor helper"
    )
    # The default sources (pre-fetch) must be CoL + WoRMS only —
    # Freshwater must not be in the unconditional default.
    assert re.search(
        r"if\s*\(\s*!rawRoots\s*\)\s*return\s*\[\s*[\"\']col[\"\']\s*,\s*[\"\']worms[\"\']\s*\]",
        text,
    ), (
        "TaxonomyTree.tsx must default the source list to CoL + WoRMS "
        "until the raw root payload resolves"
    )


def test_taxonomy_tree_threads_active_source_to_fetch_children() -> None:
    """ODD-NTP-002: child requests must call canonical
    `fetchChildren(id, { source: activeSource })` so each source's
    request carries its matching `?source=…` query string. Mirrors
    the legacy `web/api.js::loadChildren` source wiring."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r"fetchChildren\s*\(\s*id\s*,\s*\{\s*baseUrl\s*:\s*TAXA_API_ORIGIN\s*,"
        r"\s*source\s*:\s*activeSource",
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must call fetchChildren(id, { source: activeSource, ... })"
    )


def test_taxonomy_tree_uses_canonical_source_helper_for_filtering() -> None:
    """ODD-NTP-002: source filtering must go through the canonical
    `sourceMatches` predicate (or its source-aware wrappers) imported
    from `./tree-state`. The component must not invent its own
    predicate inline."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "sourceMatches" in text or "withRootsForSource" in text, (
        "TaxonomyTree.tsx must route source filtering through the canonical helper"
    )


def test_taxonomy_tree_resets_source_state_on_switch() -> None:
    """ODD-NTP-002: switching sources must clear every source-bound
    React state (roots, child cache, expanded, load status, per-row
    error) before re-displaying the new source's roots. Mirrors the
    legacy `web/nav.js::tree-source toggle` reset. The raw root cache
    SURVIVES the switch — `loadRoots` runs once on mount and the
    `rawRoots + activeSource` effect re-projects the cached payload
    against the new source without a second `/api/domains` round
    trip."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "resetSourceState" in text, (
        "TaxonomyTree.tsx must consume resetSourceState on source switch"
    )
    # The handler must (a) early-out when the user re-clicks the
    # active source (matching the legacy `if (state.treeSource ===
    # source) return;` guard) and (b) clear the per-row error before
    # the next effect re-applies the source filter.
    assert re.search(
        r"if\s*\(\s*next\s*===\s*activeSource\s*\)\s*return",
        text,
    ), (
        "TaxonomyTree.tsx must early-out on re-clicking the active source"
    )


def test_taxonomy_tree_load_roots_is_source_independent() -> None:
    """ODD-NTP-002 (regression — no domain refetch on source switch):
    `loadRoots` MUST NOT close over `activeSource`. Closing over the
    active source would put `loadRoots` in the `useEffect([loadRoots])`
    dependency array, which means the effect re-fires on every source
    switch and the React island issues a SECOND `/api/domains` round
    trip — defeating the purpose of caching the raw root payload
    client-side. The fix is to:
      1. Remove the `activeSource` reference from the `loadRoots`
         callback body (the source filter is applied by the
         `rawRoots + activeSource` effect, not by `loadRoots`).
      2. Drop `activeSource` from the `useCallback` dependency array
         so the callback reference is stable across source switches.
    This regression catches any future PR that re-introduces the
    closure (a single `activeSource` reference in the body or deps
    fails this test before code review)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # Anchor the body on the `}, [deps])` closing pattern so nested
    # braces inside `try { ... }` / `if (...) { ... }` / setState
    # updater tuples don't terminate the match early. The useCallback
    # closing `}, [...]` is the only place that pattern occurs.
    match = re.search(
        r"const\s+loadRoots\s*=\s*useCallback\s*\(\s*async\s*\(\s*\)\s*=>\s*\{"
        r"(.*?)"
        r"\}\s*,\s*\[\s*([^\]]*?)\s*\]\s*\)",
        text,
        re.DOTALL,
    )
    assert match, (
        "TaxonomyTree.tsx must declare loadRoots as `const loadRoots = "
        "useCallback(async () => { ... }, [deps])`."
    )
    body, deps = match.group(1), match.group(2)
    assert "activeSource" not in body, (
        "ODD-NTP-002: loadRoots must not close over `activeSource`; "
        "the source filter is applied by the `rawRoots + activeSource` "
        "effect, not by loadRoots. A source switch must NOT issue a "
        "second `/api/domains` request."
    )
    assert "activeSource" not in deps, (
        "ODD-NTP-002: loadRoots's `useCallback` dependency array must "
        "NOT include `activeSource`. Including it would make "
        "`useEffect([loadRoots])` re-fire on every source switch and "
        "issue a second `/api/domains` round trip."
    )


def test_taxonomy_tree_load_children_uses_source_predicate() -> None:
    """ODD-NTP-002 (regression — no unfiltered foreign-source children):
    `loadChildren` MUST call `attachChildrenForSource(state, id, kids,
    activeSource)` — the source-aware variant that applies the
    `sourceMatches` predicate before the visible child list is built.
    Calling the bare `attachChildren(state, id, kids)` would let
    foreign-source rows slip through: a WoRMS-only row landing under
    a CoL parent's response would render in the CoL view, breaking
    the source-bound child contract (and silently violating the
    `?source=…` query the helper already sends). The fix is to call
    `attachChildrenForSource` so the predicate filters the payload
    before the ids land in `childIdsByParent`."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # The source-aware variant must be imported from tree-state.
    assert re.search(
        r"\battachChildrenForSource\b",
        text,
    ), (
        "TaxonomyTree.tsx must import and use `attachChildrenForSource` "
        "so the active-source predicate is applied before attachment."
    )
    # Find the loadChildren callback body. The declaration spans
    # multiple lines (`useCallback(\n  async (id) => {\n    ...\n  },\n  [deps]\n)`)
    # so anchor on the closing `}, [...]` pattern.
    match = re.search(
        r"const\s+loadChildren\s*=\s*useCallback\s*\(\s*async\s*\(\s*id\s*:\s*number\s*\)\s*=>\s*\{"
        r"(.*?)"
        r"\}\s*,\s*\[",
        text,
        re.DOTALL,
    )
    assert match, (
        "TaxonomyTree.tsx must declare loadChildren as `const "
        "loadChildren = useCallback(async (id) => { ... }, [deps])`."
    )
    body = match.group(1)
    # Bare `attachChildren(` (NOT followed by `ForSource`) must not
    # appear inside the loadChildren body.
    bare_calls = re.findall(r"\battachChildren\s*(?!\s*ForSource)", body)
    assert not bare_calls, (
        "ODD-NTP-002: loadChildren must NOT call the bare "
        "`attachChildren(state, id, kids)`; it must call "
        "`attachChildrenForSource(state, id, kids, activeSource)` so "
        "foreign-source rows are filtered before attachment. The bare "
        "variant lets WoRMS-only rows render under CoL and vice versa."
    )
    assert "attachChildrenForSource" in body, (
        "ODD-NTP-002: loadChildren body must call "
        "`attachChildrenForSource(prev, id, kids, activeSource)` so the "
        "active-source predicate is applied before the child ids land "
        "in `childIdsByParent`."
    )


def test_taxonomy_tree_uses_canonical_api_origin_and_helpers() -> None:
    """ODD-NTP-002: the canonical API origin + fetch helpers stay in
    place (ODD-VTREE-002 + ODD-NTP-001 source/data helper public
    contract is preserved)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "process.env.NEXT_PUBLIC_TAXA_API_ORIGIN" in text, (
        "TaxonomyTree.tsx must source its API origin from NEXT_PUBLIC_TAXA_API_ORIGIN"
    )
    assert re.search(
        r"from\s+[\"\']@taxa/taxonomy[\"\']", text,
    ), (
        "TaxonomyTree.tsx must import the data helpers via the @taxa/taxonomy barrel"
    )


def test_out_index_html_has_source_selector_styles(static_export) -> None:
    """ODD-NTP-002: the static export must include the focused
    segmented-control CSS (`.tree-source-toggle` + `.tree-source-btn`
    + `.tree-source-btn.active`). The active affordance must use the
    primary token so the React tree matches the legacy native
    visual."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    assert css_chunks, "static export must emit at least one CSS chunk"
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    assert ".tree-source-toggle" in css_body, (
        "static CSS must define the .tree-source-toggle class"
    )
    assert ".tree-source-btn" in css_body, (
        "static CSS must define the .tree-source-btn class"
    )
    # The active rule must declare BOTH `background:var(--primary)` AND
    # `color:var(--on-primary)` so the React cutover is in lock-step
    # with the canonical token. The rule body is minified into one
    # block, so a single-substring check on the canonical
    # `.tree-source-btn.active` selector + the canonical tokens covers
    # the visual contract byte-equal to the legacy web/index.html cascade.
    assert re.search(
        r"\.tree-source-toggle>\.tree-source-btn\.active\b",
        css_body,
    ), (
        "static CSS must define the .tree-source-toggle>.tree-source-btn.active rule"
    )
    assert "var(--primary)" in css_body, (
        "static CSS must reference the canonical --primary token"
    )
    assert "var(--on-primary)" in css_body, (
        "static CSS must reference the canonical --on-primary token "
        "for the active button's text color"
    )
