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
TAXONOMY_TREE_STATE_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "tree-state.ts"
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


# ---------------------------------------------------------------------------
# ODD-NTP-003 — native structural parity for the visible tree.
#
# - TreeRow renders a REAL block element (not `display: contents`) so the
#   depth indent applies to the whole identity + disclosure block.
# - The native 24px indent staircase is preserved at every depth.
# - Tier headers are rendered for groups with `count > 1` and live at
#   depth+1 (matching the legacy `web/tree.js::renderTierHeader`).
# - "Load N more" / "Load all" affordances route through the source-aware
#   tree-state helpers (`setShowAll` / `toggleShowAll`).
# - The native collapse-all control clears both expanded + showAll.
# - Leaf behavior: species / subspecies rows carry `data-action="select"`
#   and a `•` glyph; higher ranks carry `data-action="toggle-expand"`.
# - WoRMS / Freshwater auto-unroll fires on every expansion.
# ---------------------------------------------------------------------------

def test_tree_row_renders_a_real_block() -> None:
    """ODD-NTP-003: TreeRow must render as a real block element so the
    depth indent applies to the entire identity + disclosure block
    (legacy `web/tree.js::renderNodeRow` uses `flex items-center
    w-full` with `padding-left: ${16 + indentPx}px`). The previous
    `display: contents` grid flattening is gone — only the name
    cell took the depth indent under that layout, which made the
    React tree visually flattened compared to the legacy oracle."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    # Strip both /* ... */ and // ... comments so docstring
    # references to the legacy cascade ("NOT a `display: contents`
    # placeholder") don't trip the substring check. We only care
    # about runtime CSS values or JSX `style={{ display: "contents"
    # }}` literals.
    stripped = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    stripped = re.sub(r"^\s*//.*$", "", stripped, flags=re.MULTILINE)
    assert "display: contents" not in stripped, (
        "ODD-NTP-003: TreeRow.tsx must NOT use `display: contents` "
        "(in JSX, inline style, or CSS) — the row must be a real "
        "block element so depth indents the whole identity + "
        "disclosure block."
    )
    # The row carries `padding-left: 16 + depth * 24` (or the
    # equivalent `${ROW_BASE_PADDING_PX + depth * ROW_INDENT_PX}px`
    # template literal).
    assert re.search(r"paddingLeft.*16\s*\+\s*depth\s*\*\s*24|paddingLeft.*ROW_BASE", text), (
        "ODD-NTP-003: TreeRow.tsx must compute padding-left as "
        "`16 + depth * 24` (matches legacy `web/tree.js::renderNodeRow`)."
    )
    # ROW_INDENT_PX = 24 is the canonical indent step.
    assert "ROW_INDENT_PX = 24" in text, (
        "ODD-NTP-003: TreeRow.tsx must expose ROW_INDENT_PX = 24 "
        "(legacy 24px indent step)."
    )


def test_tree_row_disclosure_glyphs_match_native() -> None:
    """ODD-NTP-003: leaf rows carry a `•` glyph (no chevron); higher
    ranks show `▾` (expanded) / `▸` (collapsed). Mirrors
    `web/tree.js::chevronFor` which used a small `•` marker for
    species / subspecies and `arrow_drop_down` / `chevron_right`
    for higher ranks."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    # Leaf dot + the two chevron glyphs must all appear in the
    # disclosure block.
    assert '"•"' in text, (
        "ODD-NTP-003: TreeRow.tsx must render a `•` glyph for leaves."
    )
    assert '"▾"' in text, (
        "ODD-NTP-003: TreeRow.tsx must render `▾` for expanded rows."
    )
    assert '"▸"' in text, (
        "ODD-NTP-003: TreeRow.tsx must render `▸` for collapsed rows."
    )


def test_tree_row_stamps_data_action_per_rank() -> None:
    """ODD-NTP-003: leaves stamp `data-action="select"`; higher ranks
    stamp `data-action="toggle-expand"`. Mirrors
    `web/tree.js::renderNodeRow`'s `data-action` contract so the
    future ODD-NTP-005 selection handler dispatches correctly."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert re.search(
        r'data-action\s*=\s*\{?\s*(?:knownLeaf\s*\?\s*["\']select["\']|"select")',
        text,
    ), (
        "ODD-NTP-003: TreeRow.tsx must stamp data-action=\"select\" for leaves."
    )
    assert '"toggle-expand"' in text or "'toggle-expand'" in text, (
        "ODD-NTP-003: TreeRow.tsx must stamp data-action=\"toggle-expand\" for higher ranks."
    )


def test_tree_row_stamps_depth_and_leaf_attributes() -> None:
    """ODD-NTP-003: rows expose `data-depth` and `data-leaf` for the
    future ODD-NTP-004 affordance surface + a11y tooling. Mirrors
    the legacy `web/tree.js::renderNodeRow` data-attribute
    contract."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "data-depth=" in text, (
        "ODD-NTP-003: TreeRow.tsx must stamp data-depth on each row."
    )
    assert "data-leaf=" in text, (
        "ODD-NTP-003: TreeRow.tsx must stamp data-leaf on leaf rows."
    )


def test_taxonomy_tree_renders_tier_headers() -> None:
    """ODD-NTP-003: tier headers render for groups with `count > 1`,
    sitting at depth+1 (same indent as their children). Mirrors
    `web/tree.js::renderTierHeader` byte-for-byte."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "renderTierHeader" in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must declare a renderTierHeader helper."
    )
    assert 'data-tier-header=""' in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must stamp data-tier-header on tier headers."
    )
    assert 'data-tier-parent=' in text, (
        "ODD-NTP-003: tier header must carry data-tier-parent so the "
        "next iteration can identify which parent the tier belongs to."
    )
    assert 'data-tier-rank=' in text, (
        "ODD-NTP-003: tier header must carry data-tier-rank."
    )


def test_taxonomy_tree_load_more_routes_through_source_aware_helpers() -> None:
    """ODD-NTP-003: the "Load N more" affordance calls
    `setShowAll(state, parentId, rank, true)` via a
    `handleLoadMore(parentId, rank)` handler. Mirrors the legacy
    `web/nav.js::load-all` action."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "handleLoadMore" in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must declare a handleLoadMore helper."
    )
    assert "setShowAll" in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must use the setShowAll helper."
    )
    assert re.search(
        r"data-action\s*=\s*[\"\']load-all[\"\']",
        text,
    ), (
        "ODD-NTP-003: TaxonomyTree.tsx must stamp data-action=\"load-all\" "
        "on the tier-header 'Load N more' button."
    )


def test_taxonomy_tree_renders_collapse_all_control() -> None:
    """ODD-NTP-003: the native collapse-all control clears both
    `expandedIds` and `showAll`. Disabled when no expansion
    exists. Mirrors `web/nav.js::collapseAll` +
    `renderCollapseAllButton` byte-for-byte."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "handleCollapseAll" in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must declare a handleCollapseAll handler."
    )
    assert "clearExpansion" in text, (
        "ODD-NTP-003: handleCollapseAll must call clearExpansion "
        "(clears both expandedIds + showAll in one shot)."
    )
    assert 'id="collapse-all"' in text or 'id=\\"collapse-all\\"' in text, (
        "ODD-NTP-003: collapse-all button must carry id=\"collapse-all\" "
        "(matches the legacy `web/nav.js` selector)."
    )
    assert 'data-action="collapse-all"' in text or "data-action=\"collapse-all\"" in text, (
        "ODD-NTP-003: collapse-all button must stamp data-action=\"collapse-all\"."
    )


def test_taxonomy_tree_wires_auto_unroll_for_source() -> None:
    """ODD-NTP-003: WoRMS / Freshwater expansions auto-unroll
    every tier of the expanded node. Mirrors the legacy
    `web/nav.js::toggleExpand` predicate. The CoL view is a no-op
    so the PAGE_SIZE staircase stays snappy."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "autoUnrollForSource" in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must consume autoUnrollForSource."
    )
    # The auto-unroll helper must be called for at least one of the
    # two places the legacy oracle calls it (toggleExpand /
    # attachChildren). The CoL view must stay a no-op.
    assert re.search(
        r"(worms|freshwater).*autoUnrollForSource|autoUnrollForSource.*(?:worms|freshwater)",
        text,
        re.DOTALL,
    ), (
        "ODD-NTP-003: autoUnrollForSource must be gated on the WoRMS / "
        "Freshwater source (CoL view stays a no-op)."
    )


def test_taxonomy_tree_uses_group_children_by_rank() -> None:
    """ODD-NTP-003: the recursive render routes through
    `groupChildrenByRank` so rank grouping + source filtering +
    PAGE_SIZE staircase + showAll are all applied in the canonical
    pure helper. The component must NOT reinvent grouping logic."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "groupChildrenByRank" in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must consume groupChildrenByRank."
    )


def test_tree_state_source_file_exports_ntp_003_helpers() -> None:
    """ODD-NTP-003: tree-state.ts must export the full native
    structural surface: PAGE_SIZE constant, groupChildrenByRank,
    setShowAll / toggleShowAll / isShowAll, clearShowAll /
    clearExpansion, autoUnrollForSource, expandedTierCount,
    isLeafRank, and the `showAll` field on `TreeState`."""
    text = _read_text(TAXONOMY_TREE_STATE_FILE)
    for name in (
        "PAGE_SIZE", "groupChildrenByRank", "setShowAll",
        "toggleShowAll", "isShowAll", "clearShowAll",
        "clearExpansion", "autoUnrollForSource",
        "expandedTierCount", "isLeafRank", "RankGroup",
    ):
        assert re.search(
            rf"export\s+(?:async\s+)?function\s+{name}\b|"
            rf"export\s+const\s+{name}\b|"
            rf"export\s+interface\s+{name}\b|"
            rf"export\s+type\s+{name}\b",
            text,
        ), (
            f"ODD-NTP-003: tree-state.ts must export `{name}`."
        )
    assert "showAll" in text, (
        "ODD-NTP-003: tree-state.ts must carry a showAll field on TreeState."
    )


def test_tree_state_rank_group_contract() -> None:
    """ODD-NTP-003: the `RankGroup` type exposes rank + count +
    visibleIds + remaining + fullyShown — the exact fields the
    React component reads to render the tier header + visible
    children + Load N more affordance."""
    text = _read_text(TAXONOMY_TREE_STATE_FILE)
    for field in ("rank", "count", "visibleIds", "remaining", "fullyShown"):
        assert re.search(
            rf"readonly\s+{field}\s*:",
            text,
        ), (
            f"ODD-NTP-003: RankGroup must expose `{field}`."
        )


def test_out_index_html_omits_display_contents_in_tree_css(static_export) -> None:
    """ODD-NTP-003: the static export's CSS must NOT include
    `.tree-row { display: contents }` (the previous ODD-VTREE-002
    cascade). The new ODD-NTP-003 row is a real flex block so
    the depth indent applies to the whole identity block."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    assert css_chunks, "static export must emit at least one CSS chunk"
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    # The minified cascade concatenates `.tree-row{display:contents}`
    # into one block. Reject that single concat only — generic
    # `display:contents` references elsewhere (e.g. utility classes
    # outside the tree cascade) are not in scope of this assertion.
    assert ".tree-row{display:contents" not in css_body, (
        "ODD-NTP-003: static CSS must not include "
        "`.tree-row{display:contents}` (real block layout only)."
    )
    assert not re.search(
        r"\.tree-row\s*\{[^}]*display\s*:\s*contents",
        css_body,
    ), (
        "ODD-NTP-003: the .tree-row selector must use a block / flex "
        "display, not `display: contents`."
    )


def test_out_index_html_has_tier_header_css(static_export) -> None:
    """ODD-NTP-003: the static export's CSS must define the
    `.tier-header` and `.load-all` rules so the native tier
    grouping renders identically to the legacy oracle."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    assert ".tier-header" in css_body, (
        "ODD-NTP-003: static CSS must define the .tier-header rule."
    )
    assert ".load-all" in css_body, (
        "ODD-NTP-003: static CSS must define the .load-all rule."
    )
    assert "collapse-all-btn" in css_body or ".collapse-all-btn" in css_body or "tree-collapse-all" in css_body, (
        "ODD-NTP-003: static CSS must define the .collapse-all-btn / "
        ".tree-collapse-all rule for the native collapse-all control."
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
# ODD-NTP-004 — native row identity + source affordances.
#
# - TreeRow carries `data-realm` (computed from `taxon.path`) so the
#   CSS realm-tint cascade in `src/app/globals.css` can colour the
#   scientific-name span per domain / kingdom.
# - TreeRow renders the status dot (accepted / synonym / unknown).
# - TreeRow renders the source info affordance (CoL-only /
#   WoRMS-only / cross-link) when the legacy `sourceInfoTooltip`
#   predicate returns a string. Renders nothing otherwise.
# - TreeRow renders the materialize indicator when
#   `research_path_exists === true` (or the propagated cache hits).
#   ODD-NTP-004 defers the desktop / file endpoints; the indicator
#   is a pure visual state with no click handler.
# - TreeRow renders the species-count badge via `speciesCountBadge`.
# - TreeRow renders the kebab trigger + menu structure. Items
#   whose backing React behavior exists stay enabled; items whose
#   backing handler is deferred to ODD-NTP-005 render with
#   `disabled` + `aria-disabled="true"`.
# - TreeRow carries the depth-sensitive scientific-name class so the
#   root row gets the larger `font-h1` treatment and descendants
#   stay on `font-body-lg`.
# ---------------------------------------------------------------------------

def test_tree_row_renders_data_realm_attribute() -> None:
    """ODD-NTP-004: every row must stamp `data-realm` (derived from
    `taxon.path` via `realmForPath`) so the CSS realm-tint cascade
    can colour the scientific-name span per domain / kingdom.
    Mirrors `web/tree.js::renderNodeRow::realm` byte-for-byte."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "data-realm" in text, (
        "ODD-NTP-004: TreeRow.tsx must stamp data-realm on every row."
    )
    assert "realmForPath" in text, (
        "ODD-NTP-004: TreeRow.tsx must compute the realm via realmForPath."
    )


def test_tree_row_renders_status_dot() -> None:
    """ODD-NTP-004: every row renders a status dot with the canonical
    class hooks (`status-dot`, `status-dot-{accepted|synonym|unknown}`)
    so the CSS in `src/app/globals.css` carries the colour cascade.
    Mirrors `web/tree.js::renderNodeRow::statusDot`. The dot also
    carries a `data-status-dot` attribute for tests + tooling."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "status-dot" in text, (
        "ODD-NTP-004: TreeRow.tsx must render the .status-dot element."
    )
    assert "statusDotDescriptor" in text, (
        "ODD-NTP-004: TreeRow.tsx must consume the statusDotDescriptor helper."
    )
    assert "data-status-dot" in text, (
        "ODD-NTP-004: status dot must stamp data-status-dot for tests."
    )


def test_tree_row_renders_source_info_affordance() -> None:
    """ODD-NTP-004: the source info glyph renders ONLY when the
    legacy `sourceInfoTooltip` predicate returns a string (CoL-only
    in CoL view; WoRMS-only or cross-link in WoRMS / Freshwater
    view). Renders nothing otherwise. Mirrors `web/tree.js::
    renderNodeRow::sourceInfo` byte-for-byte."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "source-info" in text, (
        "ODD-NTP-004: TreeRow.tsx must render the .source-info glyph."
    )
    assert "data-source-info" in text, (
        "ODD-NTP-004: source info glyph must stamp data-source-info."
    )


def test_tree_row_renders_materialize_indicator() -> None:
    """ODD-NTP-004: the materialize indicator renders when
    `research_path_exists === true`. The visual is a green folder
    glyph with an accessible label. ODD-NTP-004 explicitly defers
    the desktop / file endpoints, so the indicator has no click
    handler."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "materialize-indicator" in text, (
        "ODD-NTP-004: TreeRow.tsx must render the .materialize-indicator glyph."
    )
    assert "data-materialize-indicator" in text, (
        "ODD-NTP-004: materialize indicator must stamp data-materialize-indicator."
    )
    assert "hasMaterializedFolder" in text, (
        "ODD-NTP-004: TreeRow.tsx must consume the hasMaterializedFolder helper."
    )


def test_tree_row_renders_species_count_badge() -> None:
    """ODD-NTP-004: the species-count badge renders when
    `taxon.species_count` is truthy. Mirrors `web/tree.js::
    renderNodeRow::speciesCountBadge` — formatted via the row-format
    helper with the canonical 5 / 3k / 2.5M thresholds. The badge
    carries a hover title that includes the binomial + count
    context."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "species-count-badge" in text, (
        "ODD-NTP-004: TreeRow.tsx must render the .species-count-badge element."
    )
    assert "speciesCountBadge" in text, (
        "ODD-NTP-004: TreeRow.tsx must consume the speciesCountBadge helper."
    )
    assert "data-species-count" in text, (
        "ODD-NTP-004: species count badge must stamp data-species-count."
    )


def test_tree_row_renders_kebab_trigger() -> None:
    """ODD-NTP-004: every row renders a kebab trigger button with
    `data-action="toggle-kebab"` + `aria-haspopup="menu"` +
    `aria-expanded` so the visual weight stays low for full-tree
    scrolls and the menu state is observable by assistive tech."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "kebab-trigger" in text, (
        "ODD-NTP-004: TreeRow.tsx must render the .kebab-trigger button."
    )
    assert '"toggle-kebab"' in text or "'toggle-kebab'" in text, (
        "ODD-NTP-004: kebab trigger must stamp data-action=\"toggle-kebab\"."
    )
    assert "aria-haspopup" in text, (
        "ODD-NTP-004: kebab trigger must declare aria-haspopup=\"menu\"."
    )
    assert "aria-expanded" in text, (
        "ODD-NTP-004: kebab trigger must declare aria-expanded."
    )


def test_tree_row_renders_kebab_menu_items() -> None:
    """ODD-NTP-004: the kebab menu carries the three legacy actions:
    'Search online' / 'Open folder' / 'View on WoRMS'. Items whose
    backing React behavior is deferred to ODD-NTP-005 render with
    `disabled` + `aria-disabled="true"` so the user sees them as
    clearly unavailable rather than silently wired to the wrong
    endpoint. Mirrors the legacy `web/tree.js::renderNodeRow::
    kebabItems` ordering byte-for-byte.

    ODD-NTP-004 explicitly enables ONLY `View on WoRMS` (the
    `<a target="_blank">` anchor doesn't need a React handler);
    `Search online` and `Open folder` stay disabled until ODD-NTP-005
    wires the corresponding React behavior."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "kebab-menu" in text, (
        "ODD-NTP-004: TreeRow.tsx must render the .kebab-menu container."
    )
    assert '"open-searches"' in text or "'open-searches'" in text, (
        "ODD-NTP-004: kebab menu must carry the open-searches data-action."
    )
    assert '"open-folder-tab"' in text or "'open-folder-tab'" in text, (
        "ODD-NTP-004: kebab menu must carry the open-folder-tab data-action."
    )
    assert "wormsUrlFor" in text, (
        "ODD-NTP-004: TreeRow.tsx must consume the wormsUrlFor helper."
    )
    # The "View on WoRMS" item renders as an <a> with target="_blank".
    assert 'target="_blank"' in text, (
        "ODD-NTP-004: 'View on WoRMS' must render as <a target=\"_blank\">."
    )
    # Deferred actions render with `disabled` + `aria-disabled="true"`.
    assert "aria-disabled" in text, (
        "ODD-NTP-004: deferred kebab items must carry aria-disabled."
    )


def test_tree_row_carries_depth_sensitive_name_class() -> None:
    """ODD-NTP-004: the scientific-name span carries a
    depth-sensitive class (`scientific-name-depth-0` for the root
    row, `scientific-name-depth-n` for descendants) so the CSS in
    `src/app/globals.css` can apply the larger `font-h1` treatment
    on root rows and the smaller `font-body-lg` on descendants.
    Mirrors the legacy `web/tree.js::nameClassFor` helper. The
    class string is generated by the row-format
    `scientificNameDepthClass` helper; the CSS rule ships in
    `src/app/globals.css` and is verified separately by the
    `out_index_html_has_row_affordance_styles` static-export
    witness."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "scientificNameDepthClass" in text, (
        "ODD-NTP-004: TreeRow.tsx must consume the scientificNameDepthClass helper."
    )
    # The depth-sensitive class MUST reach the JSX output. The
    # helper concatenates `scientific-name scientific-name-depth-0`
    # for depth === 0 and `scientific-name scientific-name-depth-n`
    # otherwise, so we assert on the helper call site + the literal
    # `scientific-name-depth-0` / `scientific-name-depth-n` strings
    # in the source. The literal strings actually live in the
    # row-format helper (which the React component imports); both
    # locations are verified by the runtime row-format harness.
    row_format_text = _read_text(REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "row-format.ts")
    assert "scientific-name-depth-0" in row_format_text, (
        "ODD-NTP-004: row-format.ts must generate the depth-0 class."
    )
    assert "scientific-name-depth-n" in row_format_text, (
        "ODD-NTP-004: row-format.ts must generate the depth-n class."
    )


def test_taxonomy_tree_manages_kebab_state() -> None:
    """ODD-NTP-004: TaxonomyTree owns the kebab state (which row's
    kebab menu is currently open). The state is passed down to
    TreeRow via `kebabOpenId` so click-outside / Escape dismissal
    live at the tree level. Mirrors the legacy
    `web/nav.js::closeAllKebabMenus` predicate (only one kebab
    open at a time)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "kebabOpenId" in text, (
        "ODD-NTP-004: TaxonomyTree.tsx must own the kebabOpenId state."
    )
    assert "handleToggleKebab" in text, (
        "ODD-NTP-004: TaxonomyTree.tsx must declare a handleToggleKebab handler."
    )
    assert "handleKebabAction" in text, (
        "ODD-NTP-004: TaxonomyTree.tsx must declare a handleKebabAction handler."
    )
    assert "setKebabOpenId" in text, (
        "ODD-NTP-004: TaxonomyTree.tsx must update kebabOpenId via setKebabOpenId."
    )


def test_taxonomy_tree_dismisses_kebab_on_source_switch() -> None:
    """ODD-NTP-004: a source switch clears every open kebab so a
    menu never lingers over a row that has been re-projected under
    a different source. Mirrors the legacy `web/nav.js::
    tree-source toggle` reset (which cleared the kebab as part of
    the source-bound state reset)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # The handler must reset kebabOpenId alongside the source-bound
    # reset state. The body may contain nested `{ ... }` from
    # `setState((prev) => ...)` updater tuples; anchor on the
    # literal `setKebabOpenId(null)` call site instead of trying to
    # match braces.
    handle_idx = text.find("const handleSourceChange")
    assert handle_idx != -1, (
        "TaxonomyTree.tsx must declare handleSourceChange."
    )
    # Find the next occurrence of `setActiveSource(next);` which is
    # the last line of the handler body. Use that as a tail anchor.
    set_active_idx = text.find("setActiveSource(next);", handle_idx)
    assert set_active_idx != -1, (
        "TaxonomyTree.tsx must call setActiveSource(next) in handleSourceChange."
    )
    body = text[handle_idx:set_active_idx]
    assert "setKebabOpenId(null)" in body, (
        "ODD-NTP-004: handleSourceChange must close the open kebab "
        "as part of the source-bound reset."
    )


def test_taxonomy_tree_dismisses_kebab_on_collapse_all() -> None:
    """ODD-NTP-004: the collapse-all control also clears the open
    kebab so a menu never lingers over a row that has been
    collapsed."""
    text = _read_text(TAXONOMY_TREE_FILE)
    handle_idx = text.find("const handleCollapseAll")
    assert handle_idx != -1, (
        "TaxonomyTree.tsx must declare handleCollapseAll."
    )
    # Anchor on the `clearExpansion` call site (must be present in
    # the body) and the `setKebabOpenId(null)` reset.
    assert "setKebabOpenId(null)" in text[handle_idx:handle_idx + 800], (
        "ODD-NTP-004: handleCollapseAll must close the open kebab."
    )


def test_taxonomy_tree_handles_escape_keypress() -> None:
    """ODD-NTP-004: pressing Escape closes every open kebab.
    Mirrors the legacy `web/nav.js::keydown` listener (a single
    document-level handler closes the menu on Escape)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert '"keydown"' in text or "'keydown'" in text, (
        "ODD-NTP-004: TaxonomyTree.tsx must register a keydown listener."
    )
    assert "Escape" in text, (
        "ODD-NTP-004: TaxonomyTree.tsx must listen for the Escape key."
    )


def test_taxonomy_tree_handles_click_outside() -> None:
    """ODD-NTP-004: clicking outside the open kebab closes it.
    Mirrors the legacy `web/nav.js::closeAllKebabMenus` predicate
    (clicking outside the open `.kebab-menu` closes the menu).
    The handler is only attached when a kebab is open so the
    document-level touchpoint is removed as soon as the menu
    closes."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert '"mousedown"' in text or "'mousedown'" in text, (
        "ODD-NTP-004: TaxonomyTree.tsx must register a mousedown listener."
    )
    assert '".kebab"' in text or "'\\.kebab'" in text or "closest('.kebab')" in text, (
        "ODD-NTP-004: click-outside handler must skip clicks on .kebab descendants."
    )


def test_out_index_html_has_kebab_styles(static_export) -> None:
    """ODD-NTP-004: the static export's CSS must define the
    `.kebab-trigger` / `.kebab-menu` / `.kebab-item` / `.kebab`
    rules so the native kebab affordance renders identically to
    the legacy oracle."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    assert ".kebab-trigger" in css_body, (
        "ODD-NTP-004: static CSS must define the .kebab-trigger rule."
    )
    assert ".kebab-menu" in css_body, (
        "ODD-NTP-004: static CSS must define the .kebab-menu rule."
    )
    assert ".kebab-item" in css_body, (
        "ODD-NTP-004: static CSS must define the .kebab-item rule."
    )


def test_out_index_html_has_row_affordance_styles(static_export) -> None:
    """ODD-NTP-004: the static export's CSS must define every
    per-row affordance rule introduced in ODD-NTP-004
    (status-dot, source-info, materialize-indicator,
    species-count-badge, scientific-name-depth-0,
    scientific-name-depth-n, realm-tint cascade)."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    for selector in (
        ".status-dot",
        ".status-dot-accepted",
        ".status-dot-synonym",
        ".status-dot-unknown",
        ".source-info",
        ".materialize-indicator",
        ".species-count-badge",
        ".scientific-name-depth-0",
        ".scientific-name-depth-n",
    ):
        assert selector in css_body, (
            f"ODD-NTP-004: static CSS must define the {selector} rule."
        )
    # Realm-tint cascade (mirrors `web/index.html::.tree-row[data-realm="X"]
    # .scientific-name`). Seven canonical realms (the source form
    # uses unquoted attribute selectors `[data-realm=X]` which is
    # what Tailwind v4's minifier emits). The "other" fallback is
    # the `.tree-row[data-realm] .scientific-name` base rule.
    for realm in ("bacteria", "archaea", "viruses", "animalia",
                  "fungi", "plantae", "chromista"):
        assert f'data-realm={realm}' in css_body, (
            f"ODD-NTP-004: static CSS must define the realm tint for {realm!r}."
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


# ---------------------------------------------------------------------------
# ODD-NTP-005 — native source-aware in-tree navigation:
#   - Focused / selected navigation state lives at the React
#     component level (mirrors `web/state.js::focused` + `selected`).
#   - The breadcrumb above the tree renders the focused taxon's
#     ancestor chain via `walkBreadcrumbForSource(focused, source,
#     state)`. Each segment carries `data-breadcrumb-segment` +
#     `data-breadcrumb-rank`; intermediate segments are
#     `data-action="focus-segment"` buttons, the focused taxon is
#     plain text.
#   - Source switches clear focused + selected alongside the
#     source-bound React state (roots, child cache, expanded set,
#     load status, showAll, per-row error, kebab). Mirrors the
#     legacy `web/nav.js::tree-source toggle` reset byte-for-byte.
#   - Collapse-all preserves focused + selected (the legacy
#     `web/nav.js::collapseAll` does the same — selection is
#     independent of expansion).
#   - The kebab "Search online" item is ENABLED (the navigation
#     slice genuinely backs it). The "Open folder" item stays
#     `disabled` until the Folder tab + desktop file endpoints
#     ship (detail-panel / desktop file actions still lack React
#     backing).
# ---------------------------------------------------------------------------

def test_taxonomy_tree_renders_breadcrumb() -> None:
    """ODD-NTP-005: TaxonomyTree must render a breadcrumb above the
    tree source selector. Mirrors the legacy
    `web/index.html::#breadcrumb` cascade byte-for-byte."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # Breadcrumb host carries the canonical `id="breadcrumb"` so
    # downstream tooling + the legacy selector still apply. The
    # JSX literal `id="breadcrumb"` matches either the unescaped
    # JSX source OR the quoted form; the regex below accepts both.
    assert re.search(
        r'id\s*=\s*["\']breadcrumb["\']',
        text,
    ), (
        "ODD-NTP-005: TaxonomyTree.tsx must render a <nav id=\"breadcrumb\"> "
        "host so the legacy selector + downstream tooling keep applying."
    )
    assert "data-breadcrumb=" in text, (
        "ODD-NTP-005: breadcrumb host must carry data-breadcrumb for tests."
    )
    assert "data-breadcrumb-source=" in text, (
        "ODD-NTP-005: breadcrumb must stamp data-breadcrumb-source so "
        "tests can confirm source isolation."
    )
    assert "data-breadcrumb-length=" in text, (
        "ODD-NTP-005: breadcrumb must stamp data-breadcrumb-length so "
        "tests can confirm the rendered segment count."
    )
    assert "BREADCRUMB_MAX_HOPS" in text, (
        "ODD-NTP-005: TaxonomyTree.tsx must consume BREADCRUMB_MAX_HOPS "
        "so the 30-hop cycle cap surfaces in the rendered breadcrumb."
    )


def test_taxonomy_tree_uses_source_aware_breadcrumb_walker() -> None:
    """ODD-NTP-005: the breadcrumb walker dispatches on the active
    source internally. The component must consume
    `walkBreadcrumbForSource(focused, source, state)` from the
    canonical `breadcrumb-path` helper."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "walkBreadcrumbForSource" in text, (
        "ODD-NTP-005: TaxonomyTree.tsx must consume "
        "walkBreadcrumbForSource."
    )
    # The walker must be invoked with `activeSource` (NOT closed
    # over a stale source literal — the source filter is reactive).
    assert re.search(
        r"walkBreadcrumbForSource\([^)]*activeSource",
        text,
        re.DOTALL,
    ), (
        "ODD-NTP-005: walkBreadcrumbForSource must be invoked with "
        "the active source (reactive dispatch)."
    )


def test_taxonomy_tree_breadcrumb_segments_carry_action_attributes() -> None:
    """ODD-NTP-005: intermediate breadcrumb segments render as
    buttons carrying `data-action="focus-segment"` + `data-taxon-id`
    so the legacy click delegation stays compatible. The focused
    taxon itself renders as plain text (no "go to myself" affordance)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r'data-action\s*=\s*["\']focus-segment["\']',
        text,
    ), (
        "ODD-NTP-005: intermediate breadcrumb segments must stamp "
        "data-action=\"focus-segment\"."
    )
    assert re.search(
        r'data-action\s*=\s*["\']focus-home["\']',
        text,
    ), (
        "ODD-NTP-005: breadcrumb must stamp data-action=\"focus-home\" "
        "on the home glyph so the click delegation clears focus."
    )
    assert "data-breadcrumb-segment=" in text, (
        "ODD-NTP-005: each breadcrumb segment must stamp "
        "data-breadcrumb-segment={id}."
    )
    assert "data-breadcrumb-rank=" in text, (
        "ODD-NTP-005: each breadcrumb segment must stamp "
        "data-breadcrumb-rank={rank} for tests + a11y tooling."
    )


def test_taxonomy_tree_owns_focused_selected_navigation_state() -> None:
    """ODD-NTP-005: TaxonomyTree owns the focused + selected React
    state (mirrors `web/state.js::focused` + `selected`). Source
    switches reset both; collapse-all preserves both."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r"useState<number \| null>\(\s*null\s*\)",
        text,
    ), (
        "ODD-NTP-005: TaxonomyTree.tsx must own a useState<number|null> "
        "pair for focused + selected navigation state."
    )
    # Both `focused` and `selected` setters are used.
    assert "setFocused" in text, (
        "ODD-NTP-005: TaxonomyTree.tsx must expose setFocused."
    )
    assert "setSelected" in text, (
        "ODD-NTP-005: TaxonomyTree.tsx must expose setSelected."
    )


def test_taxonomy_tree_handle_select_sets_focused_and_selected() -> None:
    """ODD-NTP-005: `handleSelect(id)` is the selection primitive —
    sets focused + selected to `id`, closes the open kebab, and
    bumps the pulse nonce. Mirrors the legacy
    `web/nav.js::selectTaxon(id)` primitive byte-for-byte."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r"const\s+handleSelect\s*=\s*useCallback",
        text,
    ), (
        "ODD-NTP-005: TaxonomyTree.tsx must declare handleSelect as "
        "a useCallback."
    )
    handle_idx = text.find("const handleSelect")
    assert handle_idx != -1
    body = text[handle_idx:handle_idx + 800]
    assert "setFocused(id)" in body, (
        "ODD-NTP-005: handleSelect must call setFocused(id)."
    )
    assert "setSelected(id)" in body, (
        "ODD-NTP-005: handleSelect must call setSelected(id)."
    )
    assert "setKebabOpenId(null)" in body, (
        "ODD-NTP-005: handleSelect must close the open kebab "
        "(mirrors legacy selectTaxon's fresh-tree render)."
    )


def test_taxonomy_tree_source_change_clears_focused_and_selected() -> None:
    """ODD-NTP-005: source switches clear focused + selected in
    addition to the source-bound React state. Mirrors the legacy
    `web/nav.js::tree-source toggle` reset."""
    text = _read_text(TAXONOMY_TREE_FILE)
    handle_idx = text.find("const handleSourceChange")
    assert handle_idx != -1, (
        "TaxonomyTree.tsx must declare handleSourceChange."
    )
    body = text[handle_idx:handle_idx + 800]
    assert "setFocused(null)" in body, (
        "ODD-NTP-005: handleSourceChange must call setFocused(null) "
        "so the breadcrumb rebuilds against the new source's cache."
    )
    assert "setSelected(null)" in body, (
        "ODD-NTP-005: handleSourceChange must call setSelected(null) "
        "so the new source's detail-panel selection is clean."
    )


def test_taxonomy_tree_collapse_all_preserves_focused_and_selected() -> None:
    """ODD-NTP-005: collapse-all clears expanded + showAll + kebab
    but PRESERVES focused + selected (the legacy
    `web/nav.js::collapseAll` does the same — selection is
    independent of expansion)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    handle_idx = text.find("const handleCollapseAll")
    assert handle_idx != -1, (
        "TaxonomyTree.tsx must declare handleCollapseAll."
    )
    body = text[handle_idx:handle_idx + 600]
    assert "clearExpansion" in body, (
        "ODD-NTP-005: handleCollapseAll must call clearExpansion."
    )
    # Must NOT mutate focused + selected.
    assert "setFocused(null)" not in body, (
        "ODD-NTP-005: handleCollapseAll must NOT call setFocused(null); "
        "selection is independent of expansion."
    )
    assert "setSelected(null)" not in body, (
        "ODD-NTP-005: handleCollapseAll must NOT call setSelected(null); "
        "selection is independent of expansion."
    )


def test_taxonomy_tree_row_carries_selected_focused_attributes() -> None:
    """ODD-NTP-005: each row carries `data-selected` /
    `data-focused` attributes (or omits them when not selected /
    focused). The selected / focused CSS hooks live in
    `src/app/globals.css` under the canonical descendant guards."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "data-selected=" in text, (
        "ODD-NTP-005: TreeRow.tsx must stamp data-selected on the row."
    )
    assert "data-focused=" in text, (
        "ODD-NTP-005: TreeRow.tsx must stamp data-focused on the row."
    )


def test_tree_row_passes_on_select_focused_selected_to_props() -> None:
    """ODD-NTP-005: TreeRowProps surface accepts the new
    navigation props (onSelect, focused, selected,
    registerRowRef, pulseNonce) and the components consumes them
    to render the data attributes."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "onSelect" in text, (
        "ODD-NTP-005: TreeRow.tsx must consume onSelect."
    )
    assert "focused" in text, (
        "ODD-NTP-005: TreeRow.tsx must consume focused."
    )
    assert "selected" in text, (
        "ODD-NTP-005: TreeRow.tsx must consume selected."
    )
    assert "pulseNonce" in text, (
        "ODD-NTP-005: TreeRow.tsx must consume pulseNonce so the "
        "freshly-selected row plays the pulse animation once."
    )


def test_tree_row_search_online_is_enabled() -> None:
    """ODD-NTP-005: the kebab 'Search online' item is ENABLED. The
    navigation slice genuinely backs it: the item routes through
    `onKebabAction(id, 'open-searches')`, which the parent maps to
    `handleSelect(id)` (mirrors the legacy `web/nav.js::
    open-searches` handler). The kebab closes on dispatch so the
    click-outside / Escape dismissal stays consistent."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    # The "open-searches" data-action must NOT carry the ODD-NTP-004
    # deferral pair (`disabled` + `aria-disabled="true"`); with
    # ODD-NTP-005 the navigation slice backs the action and the
    # React handler routes through `onSelect`.
    match = re.search(
        r'data-action="open-searches"[\s\S]*?</button>',
        text,
    )
    assert match, "TreeRow.tsx must render the open-searches kebab item."
    body = match.group(0)
    assert "disabled" not in body, (
        "ODD-NTP-005: 'Search online' kebab item must NOT be disabled; "
        "the navigation slice genuinely backs it."
    )
    assert 'aria-disabled="true"' not in body, (
        "ODD-NTP-005: 'Search online' kebab item must NOT carry "
        "aria-disabled=\"true\"; the navigation slice genuinely backs it."
    )
    # The item handler routes through `onKebabAction(taxon.id, "open-searches")`,
    # which the parent maps to `handleSelect(id)`.
    assert re.search(
        r'onKebabAction\([^)]*"open-searches"',
        body,
    ), (
        "ODD-NTP-005: 'Search online' must call onKebabAction with "
        "'open-searches' (parent maps to handleSelect)."
    )


def test_tree_row_open_folder_is_still_deferred() -> None:
    """ODD-NTP-005: the kebab 'Open folder' item stays `disabled`
    until the Folder tab + desktop file endpoints ship. Detail-panel
    / desktop file actions still lack React backing."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    match = re.search(
        r'data-action="open-folder-tab"[\s\S]*?</button>',
        text,
    )
    assert match, "TreeRow.tsx must render the open-folder-tab kebab item."
    body = match.group(0)
    assert "disabled" in body and 'aria-disabled="true"' in body, (
        "ODD-NTP-005: 'Open folder' kebab item must stay disabled + "
        "aria-disabled=\"true\" until the Folder tab + desktop file "
        "endpoints ship."
    )


def test_taxonomy_tree_handle_kebab_action_dispatches_search() -> None:
    """ODD-NTP-005: handleKebabAction routes 'open-searches' through
    `handleSelect(id)` (the navigation slice's selection primitive)
    and closes the kebab on dispatch."""
    text = _read_text(TAXONOMY_TREE_FILE)
    handle_idx = text.find("const handleKebabAction")
    assert handle_idx != -1, (
        "TaxonomyTree.tsx must declare handleKebabAction."
    )
    body = text[handle_idx:handle_idx + 800]
    assert 'open-searches' in body, (
        "ODD-NTP-005: handleKebabAction must branch on 'open-searches'."
    )
    assert "handleSelect(id)" in body, (
        "ODD-NTP-005: handleKebabAction must call handleSelect(id) "
        "for open-searches (the navigation slice's selection primitive)."
    )


def test_taxonomy_tree_handle_focus_segment_expands_ancestors() -> None:
    """ODD-NTP-005: handleFocusSegment(id) is the breadcrumb
    activation primitive. It must expand the ancestors of `id`
    (via the source-safe edge map) and focus + select the segment
    id. The expansion never fabricates edges — only already-attached
    source-safe rows become expandable."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r"const\s+handleFocusSegment\s*=\s*useCallback",
        text,
    ), (
        "ODD-NTP-005: TaxonomyTree.tsx must declare handleFocusSegment "
        "as a useCallback."
    )
    handle_idx = text.find("const handleFocusSegment")
    assert handle_idx != -1
    body = text[handle_idx:handle_idx + 1200]
    assert "expandAncestorsOf" in body or "expandAncestors" in body, (
        "ODD-NTP-005: handleFocusSegment must expand ancestors before "
        "focusing the segment."
    )
    assert "setFocused(id)" in body, (
        "ODD-NTP-005: handleFocusSegment must call setFocused(id)."
    )
    assert "setSelected(id)" in body, (
        "ODD-NTP-005: handleFocusSegment must call setSelected(id)."
    )


def test_taxonomy_tree_handle_focus_home_clears_navigation() -> None:
    """ODD-NTP-005: the breadcrumb home glyph clears focused +
    selected (mirrors the legacy `web/nav.js::focus-home` handler)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r"const\s+handleFocusHome\s*=\s*useCallback",
        text,
    ), (
        "ODD-NTP-005: TaxonomyTree.tsx must declare handleFocusHome."
    )
    handle_idx = text.find("const handleFocusHome")
    body = text[handle_idx:handle_idx + 400]
    assert "setFocused(null)" in body, (
        "ODD-NTP-005: handleFocusHome must call setFocused(null)."
    )
    assert "setSelected(null)" in body, (
        "ODD-NTP-005: handleFocusHome must call setSelected(null)."
    )


def test_out_index_html_has_breadcrumb_and_row_affordance_styles(static_export) -> None:
    """ODD-NTP-005: the static export's CSS must define the
    breadcrumb host + the per-row selected / focused / pulse
    affordances introduced in ODD-NTP-005. The selectors live
    under the existing `.breadcrumb` / `.tree-row` chains so the
    chain-topology guard in `tests/test_research_styles.py` keeps
    whitelisting them under the 3c-b taxonomy surface."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    # The breadcrumb has its own host class plus the descendant
    # classes for home / segment / current (nested under the
    # canonical `.breadcrumb` rule so the chain-topology guard
    # whitelists them).
    assert ".breadcrumb" in css_body, (
        "ODD-NTP-005: static CSS must define the .breadcrumb rule."
    )
    assert "breadcrumb-host" in css_body, (
        "ODD-NTP-005: static CSS must define the .breadcrumb-host "
        "modifier (sticky + JetBrains Mono cascade)."
    )
    assert ".breadcrumb-segment" in css_body or ".breadcrumb .breadcrumb-segment" in css_body, (
        "ODD-NTP-005: static CSS must define the .breadcrumb-segment rule."
    )
    # Row affordances.
    assert ".tree-row.selected" in css_body, (
        "ODD-NTP-005: static CSS must define the .tree-row.selected "
        "rule (primary-tinted background + 3px primary left border)."
    )
    assert ".tree-row.focused" in css_body, (
        "ODD-NTP-005: static CSS must define the .tree-row.focused "
        "rule (surface-container-low tint + 3px outline left border)."
    )
    assert ".tree-row[data-pulse-nonce]" in css_body, (
        "ODD-NTP-005: static CSS must define the "
        ".tree-row[data-pulse-nonce] pulse animation."
    )
