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
RESEARCH_CHROME_SELECTORS: tuple[str, ...] = (
    ".search-tab", ".search-category-section", ".search-link-list",
    ".search-link", ".folder-tab", ".header-browser-tab",
    ".research-explorer", ".file-explorer-pane", ".file-viewer-pane",
)
# PR 3c-b taxonomy selectors — PR 3c-c MUST NOT add new top-level declarations
# of any of these (chain-topology guard).
TAXONOMY_OWNED_BY_3C_B: tuple[str, ...] = (
    ".taxa-tree", ".tree-row", ".kebab", ".kebab-menu",
    ".tree-search-icon", ".materialize-indicator", ".detail-panel",
    ".tab-strip", ".tab-button", ".overview-tab", ".breadcrumb",
    ".scientific-name", ".authorship", ".species-count",
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
        if stripped[cursor] == "{": depth += 1
        elif stripped[cursor] == "}": depth -= 1
        cursor += 1
    return stripped[m.end():cursor - 1] if depth == 0 else ""


def _rule(body: str, sel: str) -> str:
    """First ``sel { … }`` body inside ``body`` (descendants + pseudo OK)."""
    pat = re.compile(r"(?:^|[\s,{}>+~])" + re.escape(sel) + r"(?=[\s,{:>+~]|$)")
    m = pat.search(body)
    if not m:
        return ""
    cursor = m.end()
    while cursor < len(body) and body[cursor] != "{": cursor += 1
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
            depth += 1; cursor += 1; start = cursor
        elif ch == "}":
            depth -= 1; cursor += 1; start = cursor
        else:
            if ch == ";" and depth == 0: start = cursor + 1
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
    top-level rule's base selector MUST belong to PR 3c-b or PR 3c-c."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    allowed = set(TAXONOMY_OWNED_BY_3C_B) | {
        ".folder-tab", ".header-browser-tab", ".research-explorer", ".search-tab",
    }
    for head in _top_level(body):
        m = re.match(r"^\.([^\s:>+~\.\[]+)", head)
        base = f".{m.group(1)}" if m else head
        assert base in allowed, (
            f"top-level @layer components rule starts with {base!r} — neither a "
            f"PR 3c-b taxonomy selector nor a PR 3c-c research/chrome selector"
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

@pytest.mark.parametrize("selector", [".header-browser-tab", ".research-explorer"])
def test_global_browser_explorer_does_not_carry_taxon_descendant(selector):
    """3c-c.3 (e) — ``.header-browser-tab`` AND ``.research-explorer`` MUST NOT
    carry a descendant selector that scopes the explorer to a specific taxon."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    occurrences = list(re.finditer(
        r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"\b[^;{}]*", body
    ))
    assert occurrences, f"@layer components must declare {selector}"
    for m in occurrences:
        chunk = m.group(0)
        for forbidden in TAXON_SCOPE_FORBIDDEN:
            assert not re.search(forbidden, chunk), (
                f"{selector} MUST NOT carry a taxon-scoping descendant selector "
                f"(forbidden pattern {forbidden!r}); got: {chunk!r}"
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
    (".research-explorer", (".file-explorer-pane", ".file-viewer-pane")),
])
def test_parent_collapses_descendants_into_single_rule(parent, children):
    """3c-c.4 — ``.search-tab`` + ``.research-explorer`` collapse their
    respective descendant selectors (3c-c.4 refactor contract)."""
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
