"""Research / chrome styles parity tests for PR 3c-c (CSS slice).

PR 3c-c owns the nine research / chrome selectors under ``@layer components``:
``.search-tab`` (+ descendants), ``.folder-tab``, ``.header-browser-tab``, and
``.research-explorer`` (+ descendants). PR 3c-d owns the final Tailwind 4
parity surface.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GLOBALS_CSS = REPO_ROOT / "src" / "app" / "globals.css"
LEGACY_SEARCH_URLS_JS = REPO_ROOT / "web" / "search_urls.js"
LEGACY_DETAIL_JS = REPO_ROOT / "web" / "detail.js"

# PR 3c-c — the 9 research / chrome selectors.
#
# ODD-PHASE3 update: `.header-browser-tab`, `.research-explorer`,
# `.file-explorer-pane`, and `.file-viewer-pane` are REMOVED
# (the React ResearchExplorer mount collapsed the wrapper into
# the W6.4 panes + the Browser-tab nav entry is gone in the
# React cutover — the cascade rules lost every consumer). The
# remaining 5 selectors are the search-tab + folder-tab surface
# the React mount still carries.
RESEARCH_CHROME_SELECTORS: tuple[str, ...] = (
    ".search-tab", ".search-category-section", ".search-link-list",
    ".search-link", ".folder-tab",
)
# PR 3c-b taxonomy selectors — PR 3c-c MUST NOT add new top-level declarations
# of any of these (chain-topology guard). ODD-NTP-002 (native source selector
# on the taxonomy tree) extends this set with the two native-tree class
# hooks mirrored from `web/index.html::.tree-source-toggle`. ODD-NTP-003
# (native tree structure, tier paging, and disclosure behavior) extends
# the set with the eight native-tree class hooks mirrored from
# `web/index.html` (`.tier-header`, `.load-all`), `web/tree.js`
# (`.rank-badge`), and the native collapse-all
# affordance (`.tree-collapse-all` + `.collapse-all-btn`) plus the
# `.tree-source-toggle-wrapper` wrapper introduced to share the 8px
# vertical rhythm with the collapse-all button row, and the
# `.scientific-name--roman` ICZN-roman modifier.
#
# ODD-PHASE3 update: `.tree-row-status` is REMOVED. The
# `data-row-status="loading" / "error"` attribute is still set on
# the consumer element (TaxonomyTree.tsx), but the consumer no
# longer carries the `.tree-row-status` class — the
# `<Badge variant="subtle">` primitive replaced the manual cascade.
TAXONOMY_OWNED_BY_3C_B: tuple[str, ...] = (
    ".taxa-tree", ".tree-row", ".kebab", ".kebab-menu",
    ".tree-search-icon", ".materialize-indicator", ".detail-panel",
    ".tab-strip", ".tab-button", ".overview-tab", ".breadcrumb",
    ".scientific-name", ".authorship", ".species-count",
    # ODD-NTP-002 — native source selector on the taxonomy tree.
    ".tree-source-toggle", ".tree-source-btn",
    # ODD-NTP-003 — native tree structure + tier paging + disclosure.
    ".rank-badge", ".scientific-name--roman", ".tier-header",
    ".load-all", ".tree-collapse-all", ".collapse-all-btn",
    ".tree-source-toggle-wrapper",
)
# PR 3c-e2 utility-class surface — the seven legacy utility classes that
# ship as top-level rules under ``@layer components`` (see
# ``tests/test_tailwind_4_utilities.py::UTILITY_CLASSES_3C_E2``). They are
# neither taxonomy (3c-b) nor research / chrome (3c-c) selectors, so the
# chain-topology guard below whitelists EXACTLY these seven — anything else
# is still a leak.
#
# ODD-PHASE3 update: `.bg-primary-fixed`, `.rounded-r-md`, and
# `.text-on-primary-fixed` are REMOVED. The Phase 2 migrations
# eliminated the legacy callers (the React shell + row affordances
# use the Tailwind utility surface directly; the
# `<Button variant=…>` + `<Badge variant=…>` primitives centralize
# the chroming). The cascade rules lost every consumer.
UTILITY_CLASSES_OWNED_BY_3C_E2: tuple[str, ...] = (
    ".animate-spin", ".bg-primary",
    ".bg-surface-container-lowest", ".border-outline-variant",
    ".shadow-sm", ".text-on-surface",
)
# W6.1 + W6.2 — Browser-tab file explorer cascade. Migrated
# byte-equal from the legacy `web/index.html::.fex-*` inline
# `<style>` block (shell, panes, header, rows, children,
# meta strip, tab strip, snippet frame, snippet buttons,
# snippet dots, search input + clear + mode + hide-empty
# controls, No-matches card, search-match row paint, image
# / video / table / JSON viewer widgets, realm tint
# selectors). The chain-topology guard below whitelists the
# `.fex-*` bases; descendant + attribute selectors are
# reachable via the base rule in the alphabetic cascade.
FEX_EXPLORER_BASES: tuple[str, ...] = (
    ".fex-children",
    ".fex-csv-scroller", ".fex-csv-table",
    ".fex-empty-state",
    ".fex-image", ".fex-image-advisory", ".fex-image-frame",
    ".fex-json-caret", ".fex-json-children", ".fex-json-key",
    ".fex-json-node", ".fex-json-summary", ".fex-json-tree",
    ".fex-meta-spacer", ".fex-meta-strip",
    ".fex-row", ".fex-row-wrap",
    ".fex-search-clear", ".fex-search-empty",
    ".fex-search-hide-empty-btn", ".fex-search-icon",
    ".fex-search-input", ".fex-search-mode-btn",
    ".fex-search-row", ".fex-search-toggles",
    ".fex-shell",
    # W64C-XLS-003 — XLS / XLSX SheetJS viewer cascade.
    # Picker wrapper + label + select-styled button + table
    # host. The cascade mirrors the legacy
    # `web/file_viewer.js::renderSheet` shape verbatim
    # (the picker reuses the existing `.fex-snippet-btn`
    # for its visual affordance; the dedicated
    # `.fex-sheet-*` wrappers carry the layout + spacing).
    ".fex-sheet-picker", ".fex-sheet-picker-label",
    ".fex-sheet-table-host", ".fex-sheet-host",
    # W64D-EPUB-004 — EPUB viewer cascade. The W64D React
    # mount materializes EPUBs through Next 16's `<Script>`
    # loader + the pinned epubjs CDN (`EPUBJS_CDN_URL` +
    # `EPUBJS_GLOBAL_NAME = "ePub"` — the case-sensitive
    # UMD global). The legacy `web/file_viewer.js::
    # renderEpub` shape is mirrored byte-for-byte: the
    # outer host is a vertical flex that lays out the
    # book render host + the prev/next navigation row;
    # the dedicated `.fex-epub-*` wrappers carry the
    # layout + spacing + the host `min-h-[480px]` floor
    # (so the paged book has a stable target to render
    # into regardless of viewport). The `.fex-epub-*`
    # selectors sit AFTER `.fex-empty-state` (since
    # `e`mpty < `e`pub alphabetically) and BEFORE
    # `.fex-image` in the alphabetic chain.
    ".fex-epub-host", ".fex-epub-frame", ".fex-epub-nav",
    ".fex-snippet-body",
    ".fex-snippet-btn", ".fex-snippet-dots",
    ".fex-snippet-frame", ".fex-snippet-title",
    ".fex-splitter",
    ".fex-tab-strip",
    ".fex-tree-header", ".fex-tree-header-search",
    ".fex-tree-leaf", ".fex-tree-pane",
    ".fex-tree-truncated",
    ".fex-video-el", ".fex-video-frame",
    ".fex-viewer-pane",
)
# ODD-ASN-002 — AppShell frame selectors. The new shell frame
# (header / footer / nav / global search / brand / skip link)
# lands under `@layer components` between `.animate-spin` and
# `.authorship`. The selectors are part of a new top-level
# concern (the shell) — neither the PR 3c-b taxonomy set nor
# the PR 3c-c research / chrome set, so the chain-topology
# guard below whitelists them via this dedicated tuple. The
# intra-family order MUST stay alphabetical (the
# `test_top_level_selectors_are_alphabetically_ordered`
# contract — see also the 3c-c.4 refactor contract below).
APP_SHELL_SELECTORS: tuple[str, ...] = (
    ".app-shell-brand",
    ".app-shell-footer",
    ".app-shell-footer-col--center",
    ".app-shell-footer-col--left",
    ".app-shell-footer-col--right",
    ".app-shell-footer-shortcut-legend",
    ".app-shell-global-search",
    ".app-shell-global-search-input",
    ".app-shell-nav",
    ".app-shell-nav-link",
    ".app-shell-nav-link--active",
    ".app-shell-skip-link",
)
# Search tab category sections in fixed order, matching
# ``web/search_urls.js::CATEGORIES``.
SEARCH_TAB_CATEGORIES_IN_ORDER: tuple[str, ...] = (
    "General", "Taxonomic", "Academic", "Multimedia", "Documents",
)
# Global Browser explorer must NOT carry a taxon-scoping descendant selector.
TAXON_SCOPE_FORBIDDEN: tuple[str, ...] = (
    r"\[data-taxon(?:-id)?[^\]]*\]",
    r"\.taxon-row",
    r"\.taxon-id",
    r"\.tree-row\.selected",
)


def _read(path: Path) -> str:
    if not path.is_file():
        pytest.fail(f"required file missing: {path}")
    return path.read_text(encoding="utf-8")


def _block(text: str, opener: str, *, keep_comments: bool = False) -> str:
    """Body of the FIRST ``opener { … }`` block. ``keep_comments`` preserves
    ``/* … */`` blocks (needed for the category-label test)."""
    stripped = text if keep_comments else re.sub(r"/\*[\s\S]*?\*/", "", text)
    m = re.search(re.escape(opener) + r"\s*\{", stripped)
    if not m:
        return ""
    depth, cursor = 1, m.end()
    while cursor < len(stripped) and depth > 0:
        if stripped[cursor] == "{":
            depth += 1
        elif stripped[cursor] == "}":
            depth -= 1
        cursor += 1
    return stripped[m.end():cursor - 1] if depth == 0 else ""


def _rule(body: str, sel: str) -> str:
    """First ``sel { … }`` body inside ``body`` (descendants + pseudo OK)."""
    pat = re.compile(r"(?:^|[\s,{}>+~])" + re.escape(sel) + r"(?=[\s,{:>+~]|$)")
    m = pat.search(body)
    if not m:
        return ""
    cursor = m.end()
    while cursor < len(body) and body[cursor] != "{":
        cursor += 1
    if cursor >= len(body):
        return ""
    depth, end = 1, cursor + 1
    while end < len(body) and depth > 0:
        depth += 1 if body[end] == "{" else (-1 if body[end] == "}" else 0)
        end += 1
    return body[cursor + 1:end - 1] if depth == 0 else ""


def _top_level(body: str) -> list[str]:
    """Top-level (depth-0) selector heads, pseudo-classes stripped."""
    heads: list[str] = []
    depth, cursor, start = 0, 0, 0
    while cursor < len(body):
        ch = body[cursor]
        if ch == "{":
            if depth == 0:
                head = re.sub(r"[:].*$", "", body[start:cursor].strip().split(",", 1)[0]).strip()
                if head.startswith("."):
                    heads.append(head)
            depth += 1
            cursor += 1
            start = cursor
        elif ch == "}":
            depth -= 1
            cursor += 1
            start = cursor
        else:
            if ch == ";" and depth == 0:
                start = cursor + 1
            cursor += 1
    return heads


# ---- 3c-c.1 — file presence + every selector resolves --------------------------

def test_globals_css_exists():
    assert GLOBALS_CSS.is_file(), f"missing {GLOBALS_CSS.relative_to(REPO_ROOT)}"


def test_globals_css_declares_layer_components_block():
    """``@layer components { … }`` MUST already exist (PR 3c-b ships it)."""
    assert re.search(r"@layer\s+components\s*\{", _read(GLOBALS_CSS))


@pytest.mark.parametrize("selector", RESEARCH_CHROME_SELECTORS)
def test_layer_components_declares_every_research_chrome_selector(selector):
    """3c-c.1 — every research / chrome selector MUST resolve to a non-empty
    block under ``@layer components`` (top-level OR descendant)."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    assert _rule(body, selector).strip(), (
        f"@layer components must declare {selector} with a non-empty block"
    )


# W6.3 — every Browser-tab explorer splitter selector MUST
# resolve to a non-empty block under @layer components. The
# W6.3 contract extends the cascade with the vertical
# drag-handle selectors the React splitter mounts between
# the tree pane + the viewer pane: base + ::after hit-area
# extension + :hover + .dragging compound state +
# focus-visible keyboard a11y ring. Mirrors the legacy
# `web/index.html::.fex-splitter` rules byte-equal so the
# React mount's visual contract stays in lock-step with the
# legacy oracle.
W6_3_SPLITTER_SELECTORS: tuple[str, ...] = (
    ".fex-splitter",
    ".fex-splitter::after",
    ".fex-splitter:hover",
    ".fex-splitter.dragging",
    ".fex-splitter:focus-visible",
)


@pytest.mark.parametrize("selector", W6_3_SPLITTER_SELECTORS)
def test_layer_components_declares_every_w6_3_splitter_selector(selector):
    """W6.3 — every Browser-tab splitter selector MUST resolve
    to a non-empty block under @layer components. Catches a
    future PR that drops the splitter cascade (the drag handle
    would silently lose its col-resize cursor + primary-color
    tint + hit-area extension) or moves it under @layer base
    (the Tailwind 4 utility surface could override the
    splitter's affordance at runtime).
    """
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    assert _rule(body, selector).strip(), (
        f"@layer components must declare {selector} with a non-empty block"
    )


@pytest.mark.parametrize("selector", W6_3_SPLITTER_SELECTORS)
def test_layer_base_does_not_own_w6_3_splitter_selectors(selector):
    """W6.3 — splitter selectors MUST live under @layer
    components, NOT @layer base. The splitter cascade is a
    React-mount surface (PR 3c-c contract); Tailwind 4
    utilities (PR 3c-e) must still be able to override via
    @layer components. The same guard pattern as the W6.1
    research / chrome selectors."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    if not body:
        return
    assert not re.search(r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"(?=[\s,{:>+~]|$)", body), (
        f"{selector} MUST NOT live under @layer base; the splitter "
        f"cascade is a @layer components surface."
    )


# W64C-XLS-003 — XLS / XLSX SheetJS viewer cascade. The
# W64C slice extends the W6.4b cascade with the XLS / XLSX
# multi-sheet picker + table host selectors. Mirrors the
# legacy `web/file_viewer.js::renderSheet` shape verbatim:
# the picker is rendered conditionally on `SheetNames.length
# > 1` and reuses the existing `.fex-snippet-btn` styling
# for the `<select>` element. The dedicated `.fex-sheet-*`
# wrappers carry the layout + spacing. Every W64C selector
# lives under `@layer components` (the W6.4b React-mount
# surface contract) and is whitelisted in
# `FEX_EXPLORER_BASES` so the chain-topology guard stays
# green.
W64C_SHEET_SELECTORS: tuple[str, ...] = (
    ".fex-sheet-host",
    ".fex-sheet-picker",
    ".fex-sheet-picker-label",
    ".fex-sheet-table-host",
)


@pytest.mark.parametrize("selector", W64C_SHEET_SELECTORS)
def test_layer_components_declares_every_w64c_sheet_selector(selector):
    """W64C-XLS-003 — every XLS / XLSX SheetJS viewer
    selector MUST resolve to a non-empty block under
    `@layer components`. Catches a future PR that drops the
    sheet cascade (the picker / table host would silently
    lose its layout) or moves it under `@layer base` (the
    Tailwind 4 utility surface could override the sheet
    affordance at runtime). The same guard pattern as the
    W6.3 splitter cascade."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    assert _rule(body, selector).strip(), (
        f"@layer components must declare {selector} with a non-empty block"
    )


@pytest.mark.parametrize("selector", W64C_SHEET_SELECTORS)
def test_layer_base_does_not_own_w64c_sheet_selectors(selector):
    """W64C-XLS-003 — XLS / XLSX SheetJS viewer selectors
    MUST live under `@layer components`, NOT `@layer base`.
    The sheet cascade is a React-mount surface (PR 3c-c
    contract); Tailwind 4 utilities (PR 3c-e) must still be
    able to override via `@layer components`. The same
    guard pattern as the W6.3 splitter selectors."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    if not body:
        return
    assert not re.search(r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"(?=[\s,{:>+~]|$)", body), (
        f"{selector} MUST NOT live under @layer base; the "
        f"XLS / XLSX sheet cascade is a @layer components "
        f"surface."
    )


# ---- 3c-c.3 (a) — layer partition guard ----------------------------------------

@pytest.mark.parametrize("selector", RESEARCH_CHROME_SELECTORS)
def test_layer_base_does_not_own_research_chrome_selectors(selector):
    """3c-c.3 (a) — research / chrome selectors MUST live under
    ``@layer components``, NOT ``@layer base`` (PR 3c-d owns ``@layer base``)."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    if not body:
        return
    assert not re.search(r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"(?=[\s,{:>+~]|$)", body)


def test_layer_components_research_chrome_block_does_not_leak_taxonomy():
    """PR 3c-c MUST NOT introduce a new top-level taxonomy selector — every
    top-level rule's base selector MUST belong to PR 3c-b, PR 3c-c, the
    seven PR 3c-e2 utility classes, or the W6.1+W6.2 Browser-tab
    `.fex-*` explorer bases (see `FEX_EXPLORER_BASES`).

    ODD-PHASE3 update: `.header-browser-tab`, `.research-explorer`,
    `.file-explorer-pane`, `.file-viewer-pane`, `.tree-row-status`,
    `.bg-primary-fixed`, `.rounded-r-md`, `.text-on-primary-fixed`,
    `.fex-banner`, `.fex-snippet-actions` are REMOVED from the
    allowlist (and from the cascade itself) — the cascade rules
    lost every consumer during the Phase 2 migrations."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    allowed = (
        set(TAXONOMY_OWNED_BY_3C_B)
        | set(UTILITY_CLASSES_OWNED_BY_3C_E2)
        | set(FEX_EXPLORER_BASES)
        | set(APP_SHELL_SELECTORS)
        | {
            ".folder-tab",
            ".search-tab",
            ".synonym-tab", ".vernacular-tab", ".distribution-tab",
        }
    )
    for head in _top_level(body):
        m = re.match(r"^\.([^\s:>+~\.\[]+)", head)
        base = f".{m.group(1)}" if m else head
        assert base in allowed, (
            f"top-level @layer components rule starts with {base!r} — neither a "
            f"PR 3c-b taxonomy selector, a PR 3c-c research/chrome selector, "
            f"a PR 3c-e2 utility class, nor a W6.1+W6.2 `.fex-*` explorer base"
        )


# ---- 3c-c.3 (b) — Search tab category sections in fixed order ------------------

def test_search_tab_categories_render_in_fixed_order():
    """3c-c.3 (b) — Search tab category labels MUST appear in fixed order
    ``General`` → ``Taxonomic`` → ``Academic`` → ``Multimedia`` → ``Documents``
    inside ``@layer components`` (matches ``web/search_urls.js::CATEGORIES``)."""
    raw_body = _block(_read(GLOBALS_CSS), "@layer components", keep_comments=True)
    assert raw_body, "globals.css must declare @layer components { ... }"
    legacy = _read(LEGACY_SEARCH_URLS_JS)
    assert "CATEGORIES" in legacy, "web/search_urls.js must export CATEGORIES"
    positions: list[int] = []
    for label in SEARCH_TAB_CATEGORIES_IN_ORDER:
        assert label in legacy, f"legacy CATEGORIES must include {label!r}"
        m = re.search(re.escape(label), raw_body)
        assert m, f"@layer components must reference the {label!r} label"
        positions.append(m.start())
    assert positions == sorted(positions), (
        f"category labels must appear in fixed order; got positions {positions!r}"
    )


# ---- 3c-c.3 (c) — secure outbound-link attributes ------------------------------

def test_search_link_anchor_carries_target_blank():
    """3c-c.3 (c) — every ``SearchLinkList`` anchor MUST carry
    ``target="_blank"`` (legacy ``web/detail.js::renderSearchesTab``)."""
    assert re.search(r'target\s*:\s*["\']_blank["\']', _read(LEGACY_DETAIL_JS))


def test_search_link_anchor_carries_noopener_noreferrer_rel():
    """3c-c.3 (c) — outbound anchors carry ``rel="noopener noreferrer"``
    (secure form, WoRMS enrichment badge at ``web/detail.js:691``)."""
    assert re.search(r'rel\s*:\s*["\']noopener\s+noreferrer["\']', _read(LEGACY_DETAIL_JS))


# ---- 3c-c.3 (d) — FolderTab rendered separately from SearchTab -----------------

def test_folder_tab_is_distinct_from_search_tab():
    """3c-c.3 (d) — ``.folder-tab`` MUST be a SEPARATE top-level rule from
    ``.search-tab`` (no shared ``display: none`` / ``visibility: hidden`` /
    ``[hidden]`` / ``aria-hidden`` collapse)."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    folder_block = _rule(body, ".folder-tab")
    search_block = _rule(body, ".search-tab")
    assert folder_block.strip() and search_block.strip(), (
        "@layer components must declare both .folder-tab and .search-tab"
    )
    combined = folder_block + "\n" + search_block
    assert not re.search(
        r"display\s*:\s*none|visibility\s*:\s*hidden|\[hidden\]|aria-hidden",
        combined, re.IGNORECASE,
    ), ".folder-tab and .search-tab MUST stay distinct (no shared hidden collapse)"
    heads = _top_level(body)
    assert ".folder-tab" in heads and ".search-tab" in heads


# ---- 3c-c.3 (e) — global Browser explorer (NOT taxon-scoped) -------------------
#
# ODD-PHASE3 update: `.header-browser-tab` + `.research-explorer`
# are REMOVED (the cascade rules lost every consumer — the React
# ResearchExplorer mount collapsed into the W6.4 panes + the
# Browser-tab nav entry is gone in the React cutover). The
# taxon-scoping guard is preserved here so the rule stays
# documented in case a future React surface re-introduces one of
# these wrappers; the corresponding selectors must NOT reappear
# (see `ODD_PHASE3_REMOVED_SELECTORS` below).

@pytest.mark.parametrize("selector", [".header-browser-tab", ".research-explorer"])
def test_odd_phase3_global_browser_explorer_selectors_are_removed(selector):
    """ODD-PHASE3 — `.header-browser-tab` + `.research-explorer`
    were the original PR 3c-c.3 (e) taxon-scoping guard
    selectors. Phase 3 removed both cascade rules (zero
    non-comment references in src/ after Phase 2). The guard
    is preserved as a negative-witness assertion so a future
    PR that re-introduces one of them trips this test before
    review."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    assert selector not in re.findall(r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"\b", body), (
        f"ODD-PHASE3: globals.css @layer components MUST NOT declare "
        f"the removed selector {selector!r} — it lost every consumer "
        f"in Phase 2 + was removed by the Phase 3 audit."
    )


# ---- 3c-c.4 — refactor contracts (alphabetise + collapse) ---------------------

def test_top_level_selectors_are_alphabetically_ordered():
    """3c-c.4 — top-level selectors MUST be alphabetical (cascade matches
    design.md §Design tokens; mirrors the PR 3c-b contract)."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    heads = _top_level(body)
    assert heads, "@layer components must declare >= 1 selector"
    assert heads == sorted(heads), (
        f"top-level selectors MUST be alphabetical; got {heads!r}"
    )


@pytest.mark.parametrize("parent,children", [
    (".search-tab", (".search-category-section", ".search-link-list", ".search-link")),
])
def test_parent_collapses_descendants_into_single_rule(parent, children):
    """3c-c.4 — ``.search-tab`` collapses its respective descendant
    selectors (3c-c.4 refactor contract).

    ODD-PHASE3 update: `.research-explorer` is REMOVED from the
    parametrize list (the cascade rule lost every consumer — the
    React ResearchExplorer mount collapsed into the W6.4 panes).
    The 3c-c.4 refactor contract still applies to the surviving
    `.search-tab` cascade."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    heads = _top_level(body)
    assert parent in heads, f"@layer components top-level MUST contain {parent}"
    for child in children:
        assert child not in heads, (
            f"{child} MUST be a descendant of {parent} (3c-c.4 refactor)"
        )
        assert re.search(
            re.escape(parent) + r"\b[^;{]*" + re.escape(child) + r"\b", body,
        ), (
            f"@layer components must collapse {parent} + {child} into a "
            f"descendant rule (3c-c.4)"
        )


# W64D-EPUB-004 — EPUB viewer cascade. The W64D slice
# extends the W6.4b cascade with the EPUB viewer
# selectors. Mirrors the legacy
# `web/file_viewer.js::renderEpub` shape verbatim: the
# host is a vertical flex + the `min-h-[480px]` floor
# (so the paged book has a stable target to render into
# regardless of viewport). Every W64D selector lives
# under `@layer components` (the W6.4b React-mount
# surface contract) and is whitelisted in
# `FEX_EXPLORER_BASES` so the chain-topology guard stays
# green.
W64D_EPUB_SELECTORS: tuple[str, ...] = (
    ".fex-epub-host",
    ".fex-epub-frame",
    ".fex-epub-nav",
)


@pytest.mark.parametrize("selector", W64D_EPUB_SELECTORS)
def test_layer_components_declares_every_w64d_epub_selector(selector):
    """W64D-EPUB-004 — every EPUB viewer selector MUST
    resolve to a non-empty block under `@layer components`.
    Catches a future PR that drops the EPUB cascade (the
    host / frame / nav would silently lose their layout +
    spacing) or moves it under `@layer base` (the Tailwind
    4 utility surface could override the EPUB affordance
    at runtime). The same guard pattern as the W64C
    SheetJS cascade."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    assert _rule(body, selector).strip(), (
        f"@layer components must declare {selector} with a non-empty block"
    )


@pytest.mark.parametrize("selector", W64D_EPUB_SELECTORS)
def test_layer_base_does_not_own_w64d_epub_selectors(selector):
    """W64D-EPUB-004 — EPUB viewer selectors MUST live
    under `@layer components`, NOT `@layer base`. The EPUB
    cascade is a React-mount surface (PR 3c-c contract);
    Tailwind 4 utilities (PR 3c-e) must still be able to
    override via `@layer components`. The same guard
    pattern as the W64C SheetJS selectors."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    if not body:
        return
    assert not re.search(r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"(?=[\s,{:>+~]|$)", body), (
        f"{selector} MUST NOT live under @layer base; the "
        f"EPUB cascade is a @layer components surface."
    )


# ---------------------------------------------------------------------------
# ODD-PHASE3 — globals.css cleanup after design-system extract.
#
# After Phase 1 (PR #385, design-system foundation) + Phase 2
# (PRs #386-#391, consumer migrations), several `@layer components`
# rules in `src/app/globals.css` lost every consumer. Phase 3 audits
# every rule + removes the dead ones (zero non-comment references in
# `src/`). The negative-witness assertions below pin the dead
# selectors as REMOVED — a future PR that re-introduces one of them
# trips this test before review.
#
# The 12 dead rules removed by ODD-PHASE3 (Phase 3 audit,
# `tests/test_research_styles.py::test_phase3_audit_documents_kept_selectors`
# + the `odd/tasks/phase3-globals-cleanup.md` plan):
#   - 3 utility classes (PR 3c-e2 surface that became unused):
#     `.bg-primary-fixed`, `.rounded-r-md`, `.text-on-primary-fixed`.
#   - 1 research / chrome top-level wrapper that lost its only
#     consumer (the React ResearchExplorer mount no longer carries
#     the wrapper class — the cascade collapsed into the W6.4
#     panes): `.research-explorer` (+ the `.file-explorer-pane` /
#     `.file-viewer-pane` descendants that lived under it).
#   - 1 Research/chrome header tab that lost its only consumer
#     (the Browser-tab navigation entry is gone in the React cutover):
#     `.header-browser-tab`.
#   - 2 `.fex-*` rules that became dead after Phase 2 (the
#     Banner / SnippetActions wrappers were inlined into their
#     parents; the Folder / Search / JSON consumers no longer
#     apply the dedicated wrappers):
#     `.fex-banner`, `.fex-snippet-actions`.
#   - 3 `.tree-row-status[*]` rules that became dead after the
#     TaxonomyTree migration (the `data-row-status="loading" /
#     "error"` attribute is still set, but the consumer element
#     no longer carries the `.tree-row-status` class):
#     `.tree-row-status` (+ the `.tree-row-status[data-row-status=…]`
#     descendants).
#
# These selectors MUST NOT reappear in `@layer components`. The
# audit tests at the bottom of this file assert every surviving
# rule has a non-comment reference in `src/`.
ODD_PHASE3_REMOVED_SELECTORS: tuple[str, ...] = (
    # PR 3c-e2 utility classes that lost their only consumer.
    ".bg-primary-fixed",
    ".rounded-r-md",
    ".text-on-primary-fixed",
    # PR 3c-c research / chrome wrappers that lost their consumer.
    ".research-explorer",
    ".file-explorer-pane",
    ".file-viewer-pane",
    ".header-browser-tab",
    # W6.1+W6.2 `.fex-*` wrappers inlined into parents.
    ".fex-banner",
    ".fex-snippet-actions",
    # ODD-NTP-003 native tree status wrapper — the consumer
    # element no longer carries the `.tree-row-status` class
    # (the `data-row-status` attribute is still set for the
    # a11y probe, but no element with the class is rendered).
    ".tree-row-status",
    ".tree-row-status[data-row-status=\"error\"]",
    ".tree-row-status[data-row-status=\"loading\"]",
)


@pytest.mark.parametrize("selector", ODD_PHASE3_REMOVED_SELECTORS)
def test_odd_phase3_removed_selectors_must_not_reappear(selector):
    """ODD-PHASE3 — every selector that lost every consumer in
    Phase 3 MUST NOT reappear in `@layer components` of
    `src/app/globals.css`. Pins the audit's removal decisions
    so a future PR that re-introduces a dead cascade trips
    this test before review."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    # Match the selector head as a top-level OR descendant
    # token (with optional whitespace between class names so
    # the compound `.tree-row-status[data-row-status="error"]`
    # pattern resolves correctly).
    pattern = re.escape(selector)
    assert not re.search(pattern, body), (
        f"ODD-PHASE3: globals.css @layer components MUST NOT declare "
        f"the removed selector {selector!r} — it has zero non-comment "
        f"references in src/ (Phase 3 audit)."
    )


def test_phase3_audit_documents_kept_selectors():
    """ODD-PHASE3 — every `@layer components` rule that
    Phase 3 keeps MUST have at least one non-comment reference
    in `src/` (verified via `grep -rE` over the source tree).
    The audit pins the kept selectors explicitly so a future
    PR that drops a consumer trips this test before review.

    The audit found 12 dead rules (REMOVE) + 232 live rules
    (KEEP). The kept selectors below are the contractually
    load-bearing surfaces the React cutover relies on:
      - `.rank-badge` + `.authorship` — DetailPanel + SynonymTab
        inline-class fallbacks (Phase 2 keeps these as escape
        hatches; the design-system `<Badge>` primitive is the
        primary surface, but the legacy class names stay so
        downstream consumers don't have to rewrite their
        className= contracts).
      - 12 `.app-shell-*` selectors — the React AppShell mount
        carries them on header / footer / nav / global-search /
        skip-link elements.
      - The `.fex-*` cascade — the React Explorer + Viewer
        mounts carry the wrapper classes for panes, rows,
        snippet frame + buttons + dots, search controls, the
        SheetJS / EPUB viewers, the tree pane + JSON viewer,
        the empty-state card, and the splitter.
      - The `.tree-row` + descendants cascade — the React
        TreeRow mount carries the row + focused / selected
        modifiers + the realm-tint + pulse-nonce attributes.
      - The `.folder-tab` / `.synonym-tab` / `.vernacular-tab`
        / `.distribution-tab` / `.detail-panel` / `.overview-tab`
        / `.search-tab` cascades — the Phase 2 React tabs carry
        every wrapper class + descendant.
      - The PR 3c-e2 utility classes that survived (`.bg-primary`,
        `.bg-surface-container-lowest`, `.border-outline-variant`,
        `.shadow-sm`, `.text-on-surface`, `.animate-spin`) —
        used across the taxonomy tree, the detail panel, the
        kebab menu, the breadcrumb, the app shell, the row
        affordances, and the status / extinct / source chips.

    The test runs `grep -rE` via `bash` (the same command the
    audit used) and asserts every kept selector has >=1
    non-comment reference in `src/`. Comments are stripped on
    a per-line basis (single-line ``/* ... */`` + ``// ...``)
    so JSDoc-style block comments don't count as live refs.
    """
    import subprocess
    kept_selectors = (
        # Phase 2 escape hatches.
        ".rank-badge",
        ".authorship",
        # AppShell frame (12 selectors).
        ".app-shell-brand",
        ".app-shell-footer",
        ".app-shell-footer-col--center",
        ".app-shell-footer-col--left",
        ".app-shell-footer-col--right",
        ".app-shell-footer-shortcut-legend",
        ".app-shell-global-search",
        ".app-shell-global-search-input",
        ".app-shell-nav",
        ".app-shell-nav-link",
        ".app-shell-nav-link--active",
        ".app-shell-skip-link",
        # React-mount cascade (kept because the consumers carry
        # the classes — see the rule bodies + the React mount
        # code for the full evidence).
        ".detail-panel",
        ".overview-tab",
        ".distribution-tab",
        ".folder-tab",
        ".search-tab",
        ".synonym-tab",
        ".tab-strip",
        ".tree-row",
        ".tree-source-toggle",
        ".tree-source-toggle-wrapper",
        ".vernacular-tab",
        # PR 3c-e2 utility surface that survived Phase 3.
        ".animate-spin",
        ".bg-primary",
        ".bg-surface-container-lowest",
        ".border-outline-variant",
        ".shadow-sm",
        ".text-on-surface",
    )
    # Run grep -rE across src/ for every kept selector and
    # assert >=1 non-comment reference.
    for selector in kept_selectors:
        pattern = r"\b" + selector.lstrip(".") + r"\b"
        cmd = [
            "grep", "-rEn", "--include=*.ts", "--include=*.tsx",
            "--include=*.css", "--include=*.js", "--include=*.jsx",
            "--include=*.html", "--exclude=globals.css",
            pattern, "src/",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        non_comment = 0
        for line in result.stdout.splitlines():
            try:
                _, _, content = line.split(":", 2)
            except ValueError:
                continue
            stripped = re.sub(r"/\*.*?\*/", "", content)
            stripped = re.sub(r"//.*$", "", stripped)
            if re.search(pattern, stripped):
                non_comment += 1
        assert non_comment >= 1, (
            f"ODD-PHASE3: kept selector {selector!r} has zero "
            f"non-comment references in src/ — it should have been "
            f"REMOVED, not KEPT (Phase 3 audit failure)."
        )


def test_globals_css_no_dead_research_chrome_selectors():
    """ODD-PHASE3 — every `@layer components` rule in
    `src/app/globals.css` MUST have at least one non-comment
    reference in `src/`. The audit (run on
    `feat/phase3-globals-cleanup` atop `develop@146c71b`)
    walked all 244 rules + confirmed 11 were dead and 233
    were live. This test pins the post-audit invariant: any
    future PR that drops a consumer for an existing rule (so
    the rule becomes dead) trips this test before review,
    prompting a follow-up audit + removal in the same PR.

    The test excludes comments on a per-line basis (single-
    line ``/* ... */`` + ``// ...``) so JSDoc-style block
    comments don't count as live refs. The cascade rule's
    base selector is matched (compound `.x.y` → matches the
    `.x` base; descendant `.x .y` → matches `.x` since the
    descendant `.y` only requires `.x` exist somewhere in
    the source tree — the descendant cascade is reachable
    via the bare class when its parent is live).
    """
    import subprocess
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    # Strip block comments FIRST so the walker doesn't trip on
    # `;` characters inside comment text (a `;` inside a CSS
    # comment looks like a depth-0 terminator to a naive
    # brace walker). The selector audit only cares about the
    # rule structure — comments between rules are just
    # whitespace for the purpose of head extraction.
    body_for_walk = re.sub(r"/\*[\s\S]*?\*/", "", body)
    # Walk the @layer components body and extract every
    # top-level selector head. The walker mirrors the
    # `tests/test_research_styles.py::_top_level` helper
    # (kept local so the test is self-contained).
    heads: list[str] = []
    depth, cursor, start = 0, 0, 0
    while cursor < len(body_for_walk):
        ch = body_for_walk[cursor]
        if ch == "{":
            if depth == 0:
                raw = body_for_walk[start:cursor].strip()
                if raw:
                    head = raw.split(",", 1)[0].strip()
                    head = head.split(":", 1)[0].split("::", 1)[0]
                    head = head.split(">", 1)[0].split("~", 1)[0].split("+", 1)[0]
                    head = head.split(" ", 1)[0]
                    head = head.split("[", 1)[0]
                    # Compound `.x.y` → keep the first class (`.x`).
                    # Strip the leading dot.
                    head = head.strip()
                    if head.startswith("."):
                        head = head[1:]
                    # Keep only the first class of a compound.
                    head = head.split(".", 1)[0]
                    if head:
                        heads.append(head)
            depth += 1
            cursor += 1
            start = cursor
        elif ch == "}":
            depth -= 1
            cursor += 1
            start = cursor
        elif ch == ";" and depth == 0:
            cursor += 1
            start = cursor
        else:
            cursor += 1
    assert heads, "@layer components must declare >= 1 selector"
    # Run grep -rE across src/ for each head and assert
    # >=1 non-comment reference.
    for head in heads:
        pattern = r"\b" + re.escape(head) + r"\b"
        cmd = [
            "grep", "-rEn", "--include=*.ts", "--include=*.tsx",
            "--include=*.css", "--include=*.js", "--include=*.jsx",
            "--include=*.html", "--exclude=globals.css",
            pattern, "src/",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        non_comment = 0
        for line in result.stdout.splitlines():
            try:
                _, _, content = line.split(":", 2)
            except ValueError:
                continue
            stripped = re.sub(r"/\*.*?\*/", "", content)
            stripped = re.sub(r"//.*$", "", stripped)
            if re.search(pattern, stripped):
                non_comment += 1
        assert non_comment >= 1, (
            f"ODD-PHASE3: @layer components selector {head!r} "
            f"has zero non-comment references in src/ — the rule "
            f"is dead and MUST be removed (Phase 3 audit invariant)."
        )
