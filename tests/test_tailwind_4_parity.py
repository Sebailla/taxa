"""PR 3c-i focused parity test — tokens / base / dark mode slice.

PR 3c-i (position 3/16) ships the foundation slice of the 3c sub-sequence:
``@import "tailwindcss"`` + ``@theme`` block with every legacy :root
token (12 light + 8 --realm-*) + ``[data-theme="dark"]`` cascade that
redefines the 12 canonical names (realm hues stay identical between
light + dark) + ``@layer base`` with html / body / ``main > :first-child``
resets + global ``:focus-visible`` selectors.

PRs 3c-ii / 3c-iii / 3c-iv extend this file with their own narrow slices
(taxonomy tree + detail, Search / Folder / Browser styling, animations
+ utilities + final CSS parity). They are NOT pre-asserted here so the
3c-i review focus stays narrow.

Full-parity witness for the entire 3c sub-sequence will land with PR 3c-iv.
The byte-equal hex value contract for each token is covered by the existing
``tests/test_tailwind_tokens_base.py``; this test asserts the narrow
PR 3c-i contract only (presence + non-empty declarations).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GLOBALS_CSS = REPO_ROOT / "src" / "app" / "globals.css"
LAYOUT_TSX = REPO_ROOT / "src" / "app" / "layout.tsx"


def _read(path: Path) -> str:
    if not path.is_file():
        pytest.fail(f"required file missing: {path}")
    return path.read_text(encoding="utf-8")


def _strip_comments(text: str) -> str:
    """Strip ``/* ... */`` doc-comment blocks so a docstring example
    ``[data-theme="dark"]`` does not terminate the scan at the wrong brace."""
    return re.sub(r"/\*[\s\S]*?\*/", "", text)


def _block(text: str, opener: str) -> str:
    """Body of the FIRST ``opener { … }`` block. Balanced-brace scan.

    NB: Tailwind 4 @layer rules with the ``@layer base { … }`` opener use
    this same shape. The 3c-i slice has no nested braces inside the @theme
    block, the [data-theme="dark"] block, or the @layer base block, so a
    single-level scan is sufficient."""
    stripped = _strip_comments(text)
    m = re.search(re.escape(opener) + r"\s*\{", stripped)
    if not m:
        return ""
    depth, cursor = 1, m.end()
    while cursor < len(stripped) and depth > 0:
        depth += 1 if stripped[cursor] == "{" else (
            -1 if stripped[cursor] == "}" else 0
        )
        cursor += 1
    return stripped[m.end():cursor - 1] if depth == 0 else ""


# ---- PR 3c-i token catalogue (from web/index.html legacy inline <style>) ------
# Legacy :root block (light palette + realm family). PR 3c-i ships these as
# the foundation so plain-CSS `var(--primary)` references resolve. The
# byte-equal hex values live in tests/test_tailwind_tokens_base.py (existing
# 3c-a focus); here we assert non-emptiness so the 3c-i slice's narrow
# contract is enforced.

LIGHT_TOKENS = (
    "primary", "accent", "surface", "elevated", "on-surface",
    "on-surface-variant", "outline", "outline-variant",
    "surface-container-low", "surface-container",
    "surface-container-high", "surface-container-highest",
)

REALM_TOKENS = (
    "realm-bacteria", "realm-archaea", "realm-viruses", "realm-animalia",
    "realm-fungi", "realm-plantae", "realm-chromista", "realm-other",
)


# ==============================================================================
# Tests
# ==============================================================================

# ---- 3c-i.1 — file presence + Tailwind 4 directive + layout seam --------------

def test_globals_css_exists_and_imports_tailwindcss():
    """PR 3c-i MUST ship ``src/app/globals.css`` with the Tailwind 4
    ``@import "tailwindcss";`` directive so the cascade flows through
    ``next build`` (the directive is the Tailwind 4 entry point — Tailwind
    3's ``@tailwind base/components/utilities`` directives are gone)."""
    assert GLOBALS_CSS.is_file(), f"missing {GLOBALS_CSS.relative_to(REPO_ROOT)}"
    text = _read(GLOBALS_CSS)
    assert re.search(r"""@import\s+["']tailwindcss["']\s*;""", text), (
        'globals.css must @import "tailwindcss" (Tailwind 4 entry point)'
    )


def test_layout_tsx_imports_globals_css():
    """PR 3c-i seam closure: ``src/app/layout.tsx`` MUST import
    ``./globals.css`` so the Tailwind 4 directives flow into the Next.js
    static-export build. (Without the import, Next.js skips the file and
    the cascade is empty.)"""
    text = _read(LAYOUT_TSX)
    assert re.search(r"""import\s+["']\./globals\.css["']\s*;""", text), (
        'src/app/layout.tsx must import "./globals.css" (PR 3c-i seam)'
    )


def test_layout_tsx_does_not_change_unrelated_structure():
    """PR 3c-i MAY add the ``import "./globals.css";`` line + the comment
    for the 3c-i dependency-defect-fix seam, but MUST NOT touch the
    unrelated layout surface (AppShell import, ``<html lang>`` attribute,
    Raleway preload, metadata + viewport exports)."""
    text = _read(LAYOUT_TSX)
    assert "from \"@taxa/app-shell\"" in text
    assert re.search(r"<AppShell>\{children\}</AppShell>", text)
    assert "lang=\"en\"" in text
    assert "Raleway" in text and "next/font/google" in text


# ---- 3c-i.2 — @theme block carries every legacy :root token (non-empty) -------

def test_globals_css_declares_theme_block():
    """``@theme { ... }`` MUST exist for Tailwind 4's namespace resolution."""
    text = _read(GLOBALS_CSS)
    assert re.search(r"@theme\s*\{", text), (
        "globals.css must declare an @theme { ... } block (Tailwind 4 namespace)"
    )


@pytest.mark.parametrize("token", LIGHT_TOKENS)
def test_theme_declares_light_token_with_non_empty_value(token):
    """Every legacy :root light token MUST be declared inside ``@theme``
    with a non-empty value (the byte-equal witness lives in
    ``tests/test_tailwind_tokens_base.py``). The 12-token roster mirrors
    the legacy ``:root { --primary ... --surface-container-highest }`` block
    in ``web/index.html`` lines 41-58."""
    body = _block(_read(GLOBALS_CSS), "@theme")
    assert body, "globals.css must declare an @theme { ... } block"
    pattern = r"--" + re.escape(token) + r"\s*:\s*[^;]+?\s*;"
    assert re.search(pattern, body), (
        f"@theme must declare --{token} with a non-empty value (3c-i light slice)"
    )


@pytest.mark.parametrize("token", REALM_TOKENS)
def test_theme_declares_realm_token_with_non_empty_value(token):
    """Every ``--realm-*`` token MUST be declared inside ``@theme`` with a
    non-empty value. The 8-token realm family mirrors the legacy
    ``--realm-bacteria ... --realm-other`` block in ``web/index.html``.
    Realm hues stay identical in light + dark mode (only the neutral
    family inverts)."""
    body = _block(_read(GLOBALS_CSS), "@theme")
    assert body, "globals.css must declare an @theme { ... } block"
    pattern = r"--" + re.escape(token) + r"\s*:\s*[^;]+?\s*;"
    assert re.search(pattern, body), (
        f"@theme must declare --{token} with a non-empty value (3c-i realm slice)"
    )


def test_theme_does_not_define_color_namespace_aliases_outside_3c_i_scope():
    """PR 3c-i is the ``tokens / base / dark mode`` slice ONLY. The
    ``--color-*`` Tailwind 4 utility aliases are NOT shipped by 3c-i —
    they land with PR 3c-iv's design-system barrel + final CSS parity
    step. Pre-asserting them in 3c-i would silently reserve the namespace
    for a later PR and block review of each sub-PR's narrow scope."""
    body = _block(_read(GLOBALS_CSS), "@theme")
    assert body, "globals.css must declare an @theme { ... } block"
    leaked = [t for t in (*LIGHT_TOKENS, *REALM_TOKENS)
              if re.search(r"--color-" + re.escape(t) + r"\s*:", body)]
    assert not leaked, (
        f"@theme MUST NOT declare --color-* aliases in PR 3c-i; "
        f"leaked: {leaked!r} — those land with PR 3c-iv"
    )


# ---- 3c-i.3 — [data-theme="dark"] cascade overrides the canonical names -------

def test_globals_css_declares_dark_cascade_block():
    """Legacy settings theme toggle stamps ``[data-theme="dark"]`` on
    ``<html>`` (see ``web/settings.js``). The dark cascade MUST live under
    the explicit ``[data-theme="dark"]`` selector so the toggle continues
    to drive the swap (``@media (prefers-color-scheme: dark)`` would be
    ignored)."""
    text = _read(GLOBALS_CSS)
    assert re.search(r"""\[data-theme=["']dark["']\]\s*\{""", text), (
        'globals.css must declare a [data-theme="dark"] { ... } cascade block'
    )


@pytest.mark.parametrize("token", LIGHT_TOKENS)
def test_dark_cascade_redefines_canonical_token_with_non_empty_value(token):
    """Every one of the 12 canonical light tokens MUST be redefined under
    ``[data-theme="dark"]`` with a non-empty value (the dark-mode cascade
    inverts the neutral family; realm hues stay identical and are NOT
    redefined — that is the contract)."""
    body = _block(_read(GLOBALS_CSS), '[data-theme="dark"]')
    assert body, 'globals.css must declare a [data-theme="dark"] { ... } cascade'
    pattern = r"--" + re.escape(token) + r"\s*:\s*[^;]+?\s*;"
    assert re.search(pattern, body), (
        f'[data-theme="dark"] must redefine --{token} with a non-empty value '
        f'(3c-i dark-mode cascade)'
    )


def test_dark_cascade_does_not_redefine_realm_hues():
    """The dark cascade MUST NOT redefine any ``--realm-*`` token — realm
    hues stay identical between light + dark mode by design (only the
    neutral family inverts; redefining realm hues would shift the realm
    tree-row tints visually in dark mode and break the design contract)."""
    body = _block(_read(GLOBALS_CSS), '[data-theme="dark"]')
    assert body, 'globals.css must declare a [data-theme="dark"] { ... } cascade'
    leaked = [t for t in REALM_TOKENS
              if re.search(r"--" + re.escape(t) + r"\s*:", body)]
    assert not leaked, (
        f'[data-theme="dark"] MUST NOT redefine --realm-*; leaked: {leaked!r}'
    )


# ---- 3c-i.4 — @layer base carries the specified base resets -------------------

def test_globals_css_declares_layer_base_block():
    """``@layer base { ... }`` MUST exist (Tailwind 4 base layer). The
    html / body / main > :first-child resets AND the global focus-visible
    selectors land here in PR 3c-i (per the OpenSpec 3c-i slice)."""
    text = _read(GLOBALS_CSS)
    assert re.search(r"@layer\s+base\s*\{", text), (
        "globals.css must declare an @layer base { ... } block (Tailwind 4 base)"
    )


def test_layer_base_resets_html_and_body_margin_and_padding():
    """html, body { margin: 0; padding: 0; } MUST live under @layer base
    in source order (matches the legacy inline <style> block in
    ``web/index.html`` lines 14-22)."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    pattern = (
        r"html\s*,\s*body\s*\{[^}]*margin\s*:\s*0\s*;"
        r"[^}]*padding\s*:\s*0\s*;[^}]*\}"
    )
    assert re.search(pattern, body, re.DOTALL), (
        "@layer base must reset html, body { margin: 0; padding: 0; } (3c-i base reset)"
    )


def test_layer_base_sets_body_overscroll_behavior_none():
    """body { overscroll-behavior: none; } MUST live under @layer base
    (legacy ``web/index.html`` line 23) so iOS / macOS Safari's rubber-band
    doesn't fight the SPA scroll."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    assert re.search(
        r"body\s*\{[^}]*overscroll-behavior\s*:\s*none\s*;[^}]*\}",
        body, re.DOTALL,
    ), "@layer base must set body { overscroll-behavior: none; } (3c-i base reset)"


def test_layer_base_resets_main_first_child_margin_top_to_zero():
    """main > :first-child { margin-top: 0 !important; } MUST live under
    @layer base (legacy ``web/index.html`` line 27) so Tailwind's default
    ``<main>`` child margins do not push the first child down."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    pattern = (
        r"main\s*>\s*:first-child\s*\{[^}]*"
        r"margin-top\s*:\s*0\s*!important\s*;[^}]*\}"
    )
    assert re.search(pattern, body, re.DOTALL), (
        "@layer base must reset main > :first-child { margin-top: 0 !important; } "
        "(3c-i base reset)"
    )


# ---- 3c-i.5 — slice-scope guards: 3c-ii / 3c-iii / 3c-iv MUST NOT bleed in ---

# Surface names reserved for LATER 3c children. PR 3c-i MUST NOT ship
# them. NB — matched at CSS-token boundaries so PR 3c-i's
# ``.tier-header:focus-visible`` and ``.load-all:focus-visible`` rules
# (per OpenSpec 3c-i.4) don't false-positive as 3c-ii bleed; only the
# bare ``.tier-header { ... }`` / ``.load-all { ... }`` rules that
# land with PR 3c-ii trip the guard.
LATER_CHILD_SURFACES = (
    # 3c-ii — taxonomy tree + detail styling
    ".scientific-name", "#search-results", ".search-hit",
    ".tree-source-toggle", ".rank-badge", "#detail-panel",
    ".detail-card", ".detail-header",
    # 3c-iii — Search / Folder / global Browser styling
    ".search-tab", ".search-category-section", ".folder-tab",
    ".header-browser-tab", ".research-explorer", ".file-explorer-pane",
    # 3c-iv — animations / utilities / final parity
    ".animate-spin", ".bg-primary", ".bg-primary-fixed",
    ".text-on-primary-fixed", ".bg-surface-container-lowest",
    ".shadow-sm", ".rounded-r-md", ".border-outline-variant",
    "@keyframes spin", "@keyframes detail-card-enter",
    "@keyframes detail-card-leave", "@keyframes search-pulse-anim",
    "@keyframes toast-slide-in",
)


def _appears_as_css_token(text: str, surface: str) -> bool:
    """Match ``surface`` as a standalone CSS token (avoiding substrings
    like ``.tier-header`` matching inside ``.tier-header:focus-visible``)."""
    if surface.startswith("@"):
        pattern = r"(?:^|\W)" + re.escape(surface) + r"(?=\W|$)"
    else:
        pattern = (
            r"(?:^|[\s,{}>+~])" + re.escape(surface) + r"(?=[\s,{:>+~]|$)"
        )
    return re.search(pattern, text) is not None


def test_globals_css_does_not_pre_assert_later_child_surfaces():
    """Strict TDD scope guard: PR 3c-i MUST NOT pre-assert any surface
    owned by 3c-ii / 3c-iii / 3c-iv (would block the per-PR review
    focus and silence drift in the sub-sequence)."""
    text = _strip_comments(_read(GLOBALS_CSS))
    leaked = [
        s for s in LATER_CHILD_SURFACES if _appears_as_css_token(text, s)
    ]
    assert not leaked, (
        f"PR 3c-i MUST NOT pre-define surfaces reserved for 3c-ii / 3c-iii / 3c-iv; "
        f"leaked: {leaked!r}"
    )


def test_globals_css_has_no_color_mix_rules_anywhere():
    """Even though ``color-mix()`` rules are scoped to 3c-iv's deferred
    migration follow-up, PR 3c-i MUST keep the file free of them so the
    next-child re-split never silently accepts color-mix drift inside
    the foundation layer."""
    text = _strip_comments(_read(GLOBALS_CSS))
    assert "color-mix" not in text, (
        "globals.css MUST NOT carry any color-mix() rule — that surface "
        "is owned by a follow-up PR"
    )
