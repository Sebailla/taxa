"""Taxonomy tree + inline Overview/DetailPanel styles parity test for PR 3c-b.

PR 3c-b owns the taxonomy selectors under ``@layer components``: tree
(``.taxa-tree`` / ``.tree-row`` / ``.kebab`` / ``.tree-search-icon`` /
``.materialize-indicator``), detail panel (``.detail-panel`` /
``.tab-strip`` / ``.overview-tab`` / ``.breadcrumb``), and Overview body
(``.scientific-name`` / ``.authorship`` / ``.species-count``). The
remaining partitions live in PR 3c-c (research / chrome) and PR 3c-d
(animations / utilities + final parity).
"""
import re
from pathlib import Path

import pytest

GLOBALS_CSS = Path(__file__).resolve().parent.parent / "src" / "app" / "globals.css"

TAXONOMY_SELECTORS: tuple[str, ...] = (
    ".taxa-tree", ".tree-row", ".kebab", ".kebab-menu",
    ".tree-search-icon", ".materialize-indicator", ".detail-panel",
    ".tab-strip", ".tab-button", ".overview-tab", ".breadcrumb",
    ".scientific-name", ".authorship", ".species-count",
)
FORBIDDEN_SELECTORS: tuple[str, ...] = (  # owned by PR 3c-c
    ".search-tab", ".search-category-section", ".search-link-list",
    ".search-link", ".folder-tab", ".header-browser-tab",
    ".research-explorer", ".file-explorer-pane", ".file-viewer-pane",
)

_TEXT = re.sub(r"/\*[\s\S]*?\*/", "", GLOBALS_CSS.read_text(encoding="utf-8"))


def _block(opener: str) -> str:
    """Body of the FIRST ``opener { … }`` (balanced-brace scan)."""
    m = re.search(re.escape(opener) + r"\s*\{", _TEXT)
    if not m:
        return ""
    depth, cursor = 1, m.end()
    while cursor < len(_TEXT) and depth > 0:
        depth += 1 if _TEXT[cursor] == "{" else (-1 if _TEXT[cursor] == "}" else 0)
        cursor += 1
    return _TEXT[m.end():cursor - 1] if depth == 0 else ""


def _rule(body: str, sel: str) -> str:
    """First ``sel { … }`` body inside ``body`` (handles descendants + pseudo-classes)."""
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
    """Top-level (depth-0) selector heads inside a layer body, pseudo-classes stripped."""
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
            if ch == ";" and depth == 0:
                start = cursor + 1
            cursor += 1
    return heads

# ---- @layer components — presence + taxonomy selectors -----------------------

def test_globals_css_declares_layer_components_block():
    assert re.search(r"@layer\s+components\s*\{", _TEXT), (
        "globals.css must declare @layer components { ... } (PR 3c-b)"
    )


@pytest.mark.parametrize("selector", TAXONOMY_SELECTORS)
def test_layer_components_declares_every_taxonomy_selector(selector):
    """Every taxonomy selector MUST resolve to a non-empty declaration block
    under ``@layer components`` (top-level OR descendant of a collapsed parent)."""
    body = _block("@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    assert _rule(body, selector).strip(), (
        f"@layer components must declare {selector} with a non-empty block (PR 3c-b)"
    )


@pytest.mark.parametrize("selector", TAXONOMY_SELECTORS)
def test_layer_base_does_not_own_taxonomy_selectors(selector):
    """Chain-topology guard: taxonomy selectors MUST live under
    ``@layer components``, NOT ``@layer base`` (PR 3c-a resets + PR 3c-d)."""
    body = _block("@layer base")
    if not body:
        return
    assert not re.search(r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"(?=[\s,{:>+~]|$)", body), (
        f"{selector} MUST NOT live under @layer base — taxonomy belongs under @layer components"
    )


@pytest.mark.parametrize("selector", FORBIDDEN_SELECTORS)
def test_layer_components_does_not_own_research_or_chrome_selectors(selector):
    """``.search-tab`` / ``.folder-tab`` / ``.header-browser-tab`` /
    ``.research-explorer`` / … belong to PR 3c-c (research / chrome)."""
    body = _block("@layer components")
    if not body:
        return
    assert not re.search(r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"(?=[\s,{:>+~]|$)", body), (
        f"{selector} belongs to PR 3c-c (research / chrome), not PR 3c-b"
    )

# ---- binding design contracts -----------------------------------------------

def test_overview_tab_is_always_visible():
    """``Overview`` is always available/visible per the user-selected policy.
    CSS MUST NOT hide ``.overview-tab`` (``display: none`` /
    ``visibility: hidden`` / ``[hidden]`` / ``aria-hidden``)."""
    body = _block("@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    overview = _rule(body, ".overview-tab")
    assert overview.strip(), "@layer components must declare .overview-tab"
    assert not re.search(r"display\s*:\s*none|visibility\s*:\s*hidden|\[hidden\]|aria-hidden", overview, re.IGNORECASE), (
        ".overview-tab MUST NOT hide itself — user-selected policy binds Overview as always visible"
    )


def test_tab_strip_references_all_three_tab_labels():
    """Three tabs in fixed order: ``Overview`` / ``Search`` / ``Folder``,
    all reachable from every selection. ``Search`` + ``Folder`` styling
    is owned by PR 3c-c; the tab-strip scaffolding ships in PR 3c-b."""
    body = _block("@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    for label in ("Overview", "Search", "Folder"):
        assert re.search(rf"\b{label}\b", body), (
            f"@layer components must reference the {label!r} tab label (binding design contract)"
        )


def test_breadcrumb_uses_jetbrains_mono():
    """The breadcrumb renders scientific-name segments in monospace so rank
    / segment separators align vertically. The ``next/font/google`` pipeline
    loads ``JetBrains Mono`` (Raleway / JetBrains Mono / Material Symbols
    Outlined preload from PR 3b)."""
    body = _block("@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    breadcrumb = _rule(body, ".breadcrumb")
    assert breadcrumb.strip(), "@layer components must declare .breadcrumb"
    assert "JetBrains Mono" in breadcrumb, (
        ".breadcrumb must declare font-family: \"JetBrains Mono\", monospace"
    )
    assert re.search(r"font-family\s*:[^;]*monospace", breadcrumb), (
        ".breadcrumb must declare a monospace font-family fallback chain"
    )

# ---- 3c-b.4 refactor contract -----------------------------------------------

def test_top_level_selectors_are_alphabetically_ordered():
    """Refactor contract (tasks.md :: 3c-b.4): top-level selectors MUST be
    in alphabetical order so future CSS re-splits have a deterministic
    anchor (cascade matches design.md §Design tokens)."""
    body = _block("@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    heads = _top_level(body)
    assert heads, "@layer components must declare >= 1 selector"
    assert heads == sorted(heads), (
        f"@layer components top-level selectors MUST be alphabetically ordered; got {heads!r}, expected {sorted(heads)!r}"
    )


def test_kebab_and_kebab_menu_collapse_into_descendant_rule():
    """3c-b.4 refactor: ``.kebab`` + ``.kebab-menu`` collapse into a single
    ``.kebab > .kebab-menu`` rule."""
    body = _block("@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    assert re.search(r"\.kebab\s*>\s*\.kebab-menu", body), (
        "@layer components must collapse .kebab + .kebab-menu into .kebab > .kebab-menu (3c-b.4 refactor contract)"
    )


def test_tab_strip_and_tab_button_collapse_into_descendant_rule():
    """3c-b.4 refactor: ``.tab-strip`` + ``.tab-button`` collapse into a
    single ``.tab-strip > .tab-button`` rule."""
    body = _block("@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    assert re.search(r"\.tab-strip\s*>\s*\.tab-button", body), (
        "@layer components must collapse .tab-strip + .tab-button into .tab-strip > .tab-button (3c-b.4 refactor contract)"
    )
