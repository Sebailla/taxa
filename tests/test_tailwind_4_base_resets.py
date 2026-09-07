"""Base / reset / global state-affordance parity tests for PR 3c-d (CSS slice).

PR 3c-d (position 6/18, narrowed by the 2026-09-02 corrective addendum;
supersedes the old monolithic 3c-d per PR #150 / PR #151) owns ONLY the
**base / reset / global state affordances** under ``@layer base``:

- ``@keyframes spin`` (the loading-state animation the design system uses
  for materialise spinners and any future loading affordance).
- The ``body { overscroll-behavior: none; }`` reset (idempotent with
  PR 3c-a — iOS / macOS Safari rubber-band suppression).
- The ``main > :first-child { margin-top: 0 !important; }`` reset (idem­
  potent with PR 3c-a; the ``main > :last-child`` reset ships too).

**OUT of scope for 3c-d** (these belong to PR 3c-e or PR 3c-f):

- Utility classes — ``.bg-primary``, ``.text-on-surface``,
  ``.border-outline-variant``, ``.bg-surface-container-lowest``,
  ``.shadow-sm``, ``.rounded-r-md``, ``.bg-primary-fixed``,
  ``.text-on-primary-fixed``, ``.animate-spin``, … (3c-e).
- Component-scoped ``color-mix()`` rules — every ``color-mix(in srgb,
  var(--token) X%, transparent)`` line inside a specific component class
  belongs under ``@layer components`` (3c-e, or earlier 3c-b / 3c-c).
- The final consolidated parity test ``tests/test_tailwind_4_parity.py``
  (3c-f).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GLOBALS_CSS = REPO_ROOT / "src" / "app" / "globals.css"

# PR 3c-b taxonomy selectors — 3c-d MUST NOT move them into @layer base.
TAXONOMY_OWNED_BY_3C_B: tuple[str, ...] = (
    ".taxa-tree", ".tree-row", ".kebab", ".kebab-menu",
    ".tree-search-icon", ".materialize-indicator", ".detail-panel",
    ".tab-strip", ".tab-button", ".overview-tab", ".breadcrumb",
    ".scientific-name", ".authorship", ".species-count",
)
# PR 3c-c research / chrome selectors — 3c-d MUST NOT move them into @layer base.
RESEARCH_CHROME_OWNED_BY_3C_C: tuple[str, ...] = (
    ".search-tab", ".search-category-section", ".search-link-list",
    ".search-link", ".folder-tab", ".header-browser-tab",
    ".research-explorer", ".file-explorer-pane", ".file-viewer-pane",
)
# PR 3c-e utility-class surface — 3c-d MUST NOT add these to @layer base.
# `.animate-spin` pairs with @keyframes spin but is itself a component-scoped
# utility — the merged task explicitly assigns it to 3c-e.
UTILITY_CLASSES_OWNED_BY_3C_E: tuple[str, ...] = (
    ".bg-primary", ".text-on-surface", ".border-outline-variant",
    ".bg-surface-container-lowest", ".shadow-sm", ".rounded-r-md",
    ".bg-primary-fixed", ".text-on-primary-fixed", ".animate-spin",
)


def _read(path: Path) -> str:
    if not path.is_file():
        pytest.fail(f"required file missing: {path}")
    return path.read_text(encoding="utf-8")


def _block(text: str, opener: str) -> str:
    """Body of the FIRST ``opener { … }`` block. Strips CSS comments first
    so doc-comment ``[data-theme="dark"]`` examples don't terminate the
    scan at the wrong brace. Balanced-brace scan; the blocks this test
    extracts (``@layer base`` / ``@layer components``) carry no nested
    braces in 3c-d's scope."""
    stripped = re.sub(r"/\*[\s\S]*?\*/", "", text)
    m = re.search(re.escape(opener) + r"\s*\{", stripped)
    if not m:
        return ""
    depth, cursor = 1, m.end()
    while cursor < len(stripped) and depth > 0:
        depth += 1 if stripped[cursor] == "{" else (-1 if stripped[cursor] == "}" else 0)
        cursor += 1
    return stripped[m.end():cursor - 1] if depth == 0 else ""


def _rule(body: str, sel: str) -> str:
    """First ``sel { … }`` body inside ``body`` (handles descendants + pseudo)."""
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


# ---- 3c-d.1 — file + @layer base presence -----------------------------------------

def test_globals_css_exists():
    assert GLOBALS_CSS.is_file(), f"missing {GLOBALS_CSS.relative_to(REPO_ROOT)}"


def test_globals_css_declares_layer_base_block():
    """``@layer base { … }`` MUST exist (PR 3c-a ships the scaffold; PR 3c-d
    finalises it with the spin keyframe)."""
    assert re.search(r"@layer\s+base\s*\{", _read(GLOBALS_CSS)), (
        "globals.css must declare an @layer base { ... } block"
    )


# ---- 3c-d.2 — @keyframes spin -----------------------------------------------------

def test_layer_base_declares_keyframes_spin():
    """3c-d.2 — ``@keyframes spin`` MUST live under ``@layer base``."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    rule = _rule(body, "@keyframes spin")
    assert rule.strip(), (
        "@layer base must declare @keyframes spin with a non-empty block "
        "(PR 3c-d.2 — global loading-state affordance)"
    )


def test_layer_base_keyframes_spin_rotates_full_circle():
    """3c-d.2 — the spin keyframe MUST rotate from 0deg to 360deg so it
    can drive the linear infinite spinner animation."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    rule = _rule(body, "@keyframes spin")
    assert rule.strip(), "@layer base must declare @keyframes spin (PR 3c-d.2)"
    assert re.search(r"from\s*\{[^}]*transform\s*:\s*rotate\(\s*0deg\s*\)", rule), (
        "@keyframes spin must start at transform: rotate(0deg) (PR 3c-d.2)"
    )
    assert re.search(r"to\s*\{[^}]*transform\s*:\s*rotate\(\s*360deg\s*\)", rule), (
        "@keyframes spin must end at transform: rotate(360deg) (PR 3c-d.2)"
    )


# ---- 3c-d.2 — idempotent parity for existing body / first-child resets -----------

def test_layer_base_idempotent_html_body_margin_padding_reset():
    """3c-d.2 — idempotent parity: the html,body margin+padding reset that
    PR 3c-a ships MUST still be present under @layer base."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    pattern = r"html\s*,\s*body\s*\{[^}]*margin\s*:\s*0\s*;[^}]*padding\s*:\s*0\s*;[^}]*\}"
    assert re.search(pattern, body, re.DOTALL), (
        "@layer base must keep html, body { margin: 0; padding: 0; } "
        "(PR 3c-d.2 idempotent parity for PR 3c-a)"
    )


def test_layer_base_idempotent_body_overscroll_behavior_none():
    """3c-d.2 — idempotent parity: body overscroll-behavior: none from PR
    3-a MUST still be present (iOS / macOS Safari rubber-band suppression).
    Direct ``body { ... overscroll-behavior: none; ... }`` regex so the
    ``html, body { ... }`` combined reset does not shadow the rule."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    assert re.search(
        r"body\s*\{[^}]*overscroll-behavior\s*:\s*none\s*;[^}]*\}",
        body, re.DOTALL,
    ), (
        "@layer base must keep body { overscroll-behavior: none; } "
        "(PR 3c-d.2 idempotent parity for PR 3c-a)"
    )


def test_layer_base_idempotent_main_first_child_margin_top_zero():
    """3c-d.2 — idempotent parity: main > :first-child margin-top reset
    from PR 3c-a MUST still be present under @layer base."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    assert re.search(
        r"main\s*>\s*:first-child\s*\{[^}]*margin-top\s*:\s*0\s*!important\s*;[^}]*\}",
        body, re.DOTALL,
    ), "@layer base must keep main > :first-child { margin-top: 0 !important; } (PR 3c-d.2 idempotent parity)"


def test_layer_base_idempotent_main_last_child_margin_bottom_zero():
    """3c-d.2 — idempotent parity: main > :last-child margin-bottom reset
    from PR 3c-a MUST still be present (symmetric pair with first-child)."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    assert re.search(
        r"main\s*>\s*:last-child\s*\{[^}]*margin-bottom\s*:\s*0\s*!important\s*;[^}]*\}",
        body, re.DOTALL,
    ), "@layer base must keep main > :last-child { margin-bottom: 0 !important; } (PR 3c-d.2 idempotent parity)"


# ---- 3c-d.3 — layer ownership guards ----------------------------------------------

@pytest.mark.parametrize("selector", TAXONOMY_OWNED_BY_3C_B)
def test_layer_base_does_not_own_taxonomy_selectors(selector):
    """3c-d.3 — chain-topology guard: PR 3c-b taxonomy selectors MUST live
    under ``@layer components``, NOT ``@layer base``."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    if not body:
        return
    assert not re.search(r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"(?=[\s,{:>+~]|$)", body), (
        f"{selector} MUST NOT live under @layer base — taxonomy belongs "
        f"under @layer components (PR 3c-b)"
    )


@pytest.mark.parametrize("selector", RESEARCH_CHROME_OWNED_BY_3C_C)
def test_layer_base_does_not_own_research_chrome_selectors(selector):
    """3c-d.3 — chain-topology guard: PR 3c-c research / chrome selectors
    MUST live under ``@layer components``, NOT ``@layer base``."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    if not body:
        return
    assert not re.search(r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"(?=[\s,{:>+~]|$)", body), (
        f"{selector} MUST NOT live under @layer base — research/chrome "
        f"belongs under @layer components (PR 3c-c)"
    )


@pytest.mark.parametrize("selector", UTILITY_CLASSES_OWNED_BY_3C_E)
def test_layer_base_does_not_own_3c_e_utility_classes(selector):
    """3c-d.3 — chain-topology guard: PR 3c-e utility classes (including
    ``.animate-spin`` which pairs with the ``spin`` keyframe but is itself
    a component-scoped utility) MUST NOT live under ``@layer base``."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    if not body:
        return
    assert not re.search(r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"(?=[\s,{:>+~]|$)", body), (
        f"{selector} MUST NOT live under @layer base — utility classes "
        f"belong to PR 3c-e"
    )


def test_layer_base_does_not_own_component_scoped_color_mix():
    """3c-d.3 — chain-topology guard: component-scoped ``color-mix()`` rules
    (nested inside ``.fex-*`` / ``.materialize-modal-*`` / ``.toast`` / …)
    MUST NOT be lifted into ``@layer base``. 3c-d owns the **global** ``@layer
    base`` state affordances only; every component-scoped ``color-mix()``
    belongs to PR 3c-b / 3c-c / 3c-e and MUST stay under ``@layer
    components``."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    if not body:
        return
    assert "color-mix" not in body, (
        "@layer base MUST NOT carry any color-mix() rule — component-scoped "
        "color-mix() belongs under @layer components (PR 3c-b / 3c-c / 3c-e)"
    )


# ---- 3c-d.3 — source order guards -------------------------------------------------

def test_layer_base_source_order_resets_then_keyframes():
    """3c-d.3 — source order: within ``@layer base``, the rules MUST appear in
    legacy-cascade order — the ``html, body`` margin+padding reset FIRST,
    then the ``@keyframes spin`` block LAST. Matches design.md §"Design
    tokens" cascade order requirement + the legacy ``<style>`` block ordering."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    m_reset = re.search(
        r"html\s*,\s*body\s*\{[^}]*margin\s*:\s*0\s*;[^}]*padding\s*:\s*0\s*;[^}]*\}",
        body, re.DOTALL,
    )
    assert m_reset, "@layer base must declare the html,body margin+padding reset (PR 3c-a)"
    assert body[:m_reset.start()].strip() == "", (
        "@layer base html,body { margin:0; padding:0; } MUST be the FIRST "
        "rule in @layer base"
    )
    m_keyframes = re.search(r"@keyframes\s+spin", body)
    assert m_keyframes, "@layer base must declare @keyframes spin (PR 3c-d.2)"
    assert m_reset.start() < m_keyframes.start(), (
        f"@layer base source order MUST be resets({m_reset.start()}) → "
        f"keyframes({m_keyframes.start()})"
    )


# ---- 3c-d.3 — triangulators (negative + boundary) --------------------------------

def test_layer_components_does_not_own_keyframes_spin():
    """Triangulator — ``@keyframes spin`` belongs to ``@layer base``
    (3c-d), NOT ``@layer components``. A future CSS re-split MUST NOT
    migrate it up the cascade by accident."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    if not body:
        return
    assert not re.search(r"@keyframes\s+spin\b", body), (
        "@layer components MUST NOT own @keyframes spin (PR 3c-d owns it under @layer base)"
    )


def test_globals_css_no_new_top_level_class_outside_layer_components_or_base():
    """3c-d.3 — chain-topology guard: 3c-d MUST NOT introduce a new
    top-level (outside any @layer block) component class or utility class
    on globals.css. Every rule 3c-d ships MUST live under ``@layer base``."""
    text = _read(GLOBALS_CSS)
    stripped = re.sub(r"/\*[\s\S]*?\*/", "", text)
    base_match = re.search(r"@layer\s+base\s*\{", stripped)
    components_match = re.search(r"@layer\s+components\s*\{", stripped)
    assert base_match and components_match, (
        "globals.css must declare both @layer base and @layer components"
    )
    base_end = stripped.find("}", base_match.end())
    assert base_end != -1, "@layer base must close before @layer components"
    between = stripped[base_end + 1:components_match.start()]
    leaked = re.findall(r"(?:^|[\s,{}>+~])(\.[A-Za-z][\w-]*)\s*\{", between)
    assert not leaked, (
        f"globals.css MUST NOT declare a top-level class outside @layer "
        f"base / @layer components; leaked: {leaked!r}"
    )