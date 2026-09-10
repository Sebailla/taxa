"""Token / base / dark-mode parity tests for PR 3c-a (CSS slice).

CSS re-split child 1/4 (positions 3-6/16 in the chain: 3c-a → 3c-b → 3c-c → 3c-d).
PR 3c-a owns the CSS foundation: ``@import "tailwindcss";``, the ``@theme`` block
with every legacy ``:root`` token + ``--realm-*`` family + ``--color-*`` namespace
aliases, the ``[data-theme="dark"]`` block, the ``@layer base`` resets, and
the ``import "./globals.css";`` seam in ``src/app/layout.tsx``. The remaining
1,963 legacy lines are partitioned across PRs 3c-b (taxonomy), 3c-c
(research / chrome), and 3c-d (animations / utilities + final parity).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GLOBALS_CSS = REPO_ROOT / "src" / "app" / "globals.css"
LAYOUT_TSX = REPO_ROOT / "src" / "app" / "layout.tsx"

# Legacy :root (light) — source: web/index.html:39-53. Token + hex value, byte-equal.
LIGHT_TOKENS: dict[str, str] = {
    "primary": "#1d7ea9", "accent": "#176587", "surface": "#ffffff",
    "elevated": "#bbbbbb", "on-surface": "#333333", "on-surface-variant": "#555555",
    "outline": "#bbbbbb", "outline-variant": "#d9d9d9",
    "surface-container-low": "#fafafa", "surface-container": "#f5f5f5",
    "surface-container-high": "#eeeeee", "surface-container-highest": "#e8e8e8",
}
# Legacy --realm-* (saturated pastel; identical hue light + dark). Source: web/index.html:59-66.
REALM_TOKENS: dict[str, str] = {
    "realm-bacteria": "#5ebd9b", "realm-archaea": "#e07466",
    "realm-viruses": "#e8c547", "realm-animalia": "#a57fcb",
    "realm-fungi": "#5b9bd5", "realm-plantae": "#7cb669",
    "realm-chromista": "#e89b4f", "realm-other": "#d49ab6",
}
# Legacy [data-theme="dark"] palette — same names as LIGHT (sans realm), different values. Source: web/index.html:77-91.
DARK_TOKENS: dict[str, str] = {
    "primary": "#4aa3d0", "accent": "#6cb8db", "surface": "#1a1d23",
    "elevated": "#2a2e36", "on-surface": "#e6e8ec", "on-surface-variant": "#a0a4ac",
    "outline": "#4a4e56", "outline-variant": "#353941",
    "surface-container-low": "#1e2128", "surface-container": "#232730",
    "surface-container-high": "#2a2f38", "surface-container-highest": "#313742",
}


def _read(path: Path) -> str:
    if not path.is_file():
        pytest.fail(f"required file missing: {path}")
    return path.read_text(encoding="utf-8")


def _block(text: str, opener: str) -> str:
    """Return body of the FIRST ``opener { … }`` block. Strips CSS comments
    first so the doc-comment ``[data-theme="dark"]`` example doesn't terminate
    the scan at the wrong brace. Uses a balanced-brace scan — none of the
    blocks we extract (``@theme`` / ``@layer base`` / ``[data-theme="dark"]``)
    carry nested braces in PR 3c-a's scope."""
    stripped = re.sub(r"/\*[\s\S]*?\*/", "", text)
    m = re.search(re.escape(opener) + r"\s*\{", stripped)
    if not m:
        return ""
    depth, cursor = 1, m.end()
    while cursor < len(stripped) and depth > 0:
        ch = stripped[cursor]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        cursor += 1
    return stripped[m.end():cursor - 1] if depth == 0 else ""


# ---- file presence (RED gate) ------------------------------------------------------

def test_globals_css_exists():
    assert GLOBALS_CSS.is_file(), (
        f"missing {GLOBALS_CSS.relative_to(REPO_ROOT)} — PR 3c-a.2 must author globals.css"
    )


def test_globals_css_imports_tailwindcss():
    assert re.search(r"""@import\s+["']tailwindcss["']\s*;""", _read(GLOBALS_CSS)), (
        'globals.css must @import "tailwindcss" (Tailwind 4 entry point)'
    )


# ---- @theme block — light + realm palette + --color-* namespace aliases -----------

def test_globals_css_declares_theme_block():
    text = _read(GLOBALS_CSS)
    assert re.search(r"@theme\s*\{", text), (
        "globals.css must declare an @theme { ... } block (Tailwind 4 namespace)"
    )


@pytest.mark.parametrize("name,hex_value", sorted(LIGHT_TOKENS.items()))
def test_globals_css_theme_declares_light_token_with_byte_equal_value_and_color_alias(name, hex_value):
    """Every legacy ``:root`` token MUST keep its original hex value in
    ``globals.css::@theme`` AND have a ``--color-<name>`` Tailwind namespace
    alias — both byte-equal migration and Tailwind 4 utility resolution."""
    body = _block(_read(GLOBALS_CSS), "@theme")
    assert body, "globals.css must declare an @theme { ... } block"
    legacy = f"--{name}: {hex_value}"
    alias = f"--color-{name}:"
    assert re.search(re.escape(legacy), body), (
        f"globals.css::@theme must declare {legacy} (byte-equal to legacy :root)"
    )
    assert re.search(re.escape(alias), body), (
        f"globals.css::@theme must declare {alias} (Tailwind 4 utility namespace)"
    )


@pytest.mark.parametrize("name,hex_value", sorted(REALM_TOKENS.items()))
def test_globals_css_theme_declares_realm_token_with_byte_equal_value_and_color_alias(name, hex_value):
    """Same byte-equal + alias contract for the ``--realm-*`` family so
    plain-CSS ``var(--realm-bacteria)`` references AND Tailwind utilities
    (bg-realm-animalia, text-realm-fungi, …) resolve."""
    body = _block(_read(GLOBALS_CSS), "@theme")
    assert body, "globals.css must declare an @theme { ... } block"
    legacy = f"--{name}: {hex_value}"
    alias = f"--color-{name}:"
    assert re.search(re.escape(legacy), body), (
        f"globals.css::@theme must declare {legacy} (byte-equal to legacy :root)"
    )
    assert re.search(re.escape(alias), body), (
        f"globals.css::@theme must declare {alias} (Tailwind 4 utility namespace)"
    )


# ---- [data-theme="dark"] palette ---------------------------------------------------

def test_globals_css_declares_dark_theme_block():
    """Legacy settings theme toggle stamps ``data-theme="dark"`` on ``<html>``
    (see ``web/settings.js``). The dark palette MUST live under the explicit
    ``[data-theme="dark"]`` selector — not under ``@media (prefers-color-scheme:
    dark)`` — so the toggle continues to drive the swap (design-tokens spec
    §"OS preference fallback" + §"Dark mode parity")."""
    assert re.search(r"""\[data-theme=["']dark["']\]\s*\{""", _read(GLOBALS_CSS)), (
        'globals.css must declare a [data-theme="dark"] { ... } block for the legacy settings theme toggle'
    )


@pytest.mark.parametrize("name,hex_value", sorted(DARK_TOKENS.items()))
def test_globals_css_dark_block_redefines_neutral_with_byte_equal_value(name, hex_value):
    """Every legacy dark neutral MUST keep its original hex value — byte-equal
    migration of the dark palette. Realm hues are NOT redefined here (they
    stay identical in dark mode)."""
    body = _block(_read(GLOBALS_CSS), '[data-theme="dark"]')
    assert body, 'globals.css must declare a [data-theme="dark"] { ... } block'
    expected = f"--{name}: {hex_value}"
    assert re.search(re.escape(expected), body), (
        f"globals.css[data-theme=\"dark\"] must redefine {expected} (byte-equal to legacy dark palette)"
    )


def test_globals_css_dark_block_does_not_redefine_realm_hues():
    """Realm hues are byte-equal between light and dark mode by design — only
    neutrals invert. The dark block MUST NOT redefine the ``--realm-*``
    family or the realm tints would drift visually in dark mode."""
    body = _block(_read(GLOBALS_CSS), '[data-theme="dark"]')
    assert body, 'globals.css must declare a [data-theme="dark"] { ... } block'
    leaked = [name for name in REALM_TOKENS if f"--{name}" in body]
    assert not leaked, (
        f"globals.css[data-theme=\"dark\"] must NOT redefine --realm-* tokens; leaked: {leaked!r}"
    )


# ---- @layer base — base resets -----------------------------------------------------

def test_globals_css_declares_layer_base_block():
    """html/body margin+padding reset, ``overscroll-behavior: none``, and
    ``main > :first-child`` / ``main > :last-child`` resets MUST live under
    ``@layer base`` so source order matches the legacy cascade."""
    assert re.search(r"@layer\s+base\s*\{", _read(GLOBALS_CSS)), (
        "globals.css must declare an @layer base { ... } block"
    )


def test_globals_css_layer_base_resets_html_and_body_margin_and_padding():
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    pattern = r"html\s*,\s*body\s*\{[^}]*margin\s*:\s*0\s*;[^}]*padding\s*:\s*0\s*;[^}]*\}"
    assert re.search(pattern, body, re.DOTALL), (
        "@layer base must reset html, body { margin: 0; padding: 0; } (legacy inline-style block reset)"
    )


def test_globals_css_layer_base_sets_body_overscroll_behavior_none():
    """Legacy body rule sets ``overscroll-behavior: none`` so iOS / macOS
    Safari's rubber-band doesn't fight the SPA scroll."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    assert re.search(r"body\s*\{[^}]*overscroll-behavior\s*:\s*none\s*;[^}]*\}", body, re.DOTALL), (
        "@layer base must set body { overscroll-behavior: none; } (legacy rubber-band suppression)"
    )


def test_globals_css_layer_base_resets_main_first_and_last_child_margins():
    """Legacy first/last-child resets flatten Tailwind's default margins on
    the children of ``<main>``."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    assert re.search(
        r"main\s*>\s*:first-child\s*\{[^}]*margin-top\s*:\s*0\s*!important\s*;[^}]*\}",
        body, re.DOTALL,
    ), "@layer base must reset main > :first-child { margin-top: 0 !important; }"
    assert re.search(
        r"main\s*>\s*:last-child\s*\{[^}]*margin-bottom\s*:\s*0\s*!important\s*;[^}]*\}",
        body, re.DOTALL,
    ), "@layer base must reset main > :last-child { margin-bottom: 0 !important; }"


# ---- layout.tsx — import integration (dependency-defect-fix seam) ------------------

def test_layout_tsx_imports_globals_css():
    """PR 3c-a closes the dependency-defect-fix seam: PR 3b's
    ``src/app/layout.tsx`` placeholder MUST NOT import ``./globals.css`` (PR
    3c-a ships the file). PR 3c-a adds the import here so the Tailwind 4
    ``@import "tailwindcss"`` directive flows into the Next.js build."""
    text = _read(LAYOUT_TSX)
    assert re.search(r"""import\s+["']\./globals\.css["']\s*;""", text), (
        'src/app/layout.tsx must import "./globals.css" so the Tailwind 4 '
        "@import \"tailwindcss\" directives flow into the Next.js build "
        "(PR 3c-a.3 dependency-defect-fix seam)"
    )


def test_layout_tsx_does_not_import_owners_of_later_prs():
    """Chain-topology guard: PR 3c-a MUST NOT import ``@taxa/app-shell``
    (PR 4b) or ``@taxa/browser-state`` (PR 4a) — those modules are later in
    the chain."""
    text = _read(LAYOUT_TSX)
    for forbidden, owner in (
        (r"""from\s+["']@taxa/app-shell""", "@taxa/app-shell (PR 4b)"),
        (r"""from\s+["']@taxa/browser-state""", "@taxa/browser-state (PR 4a)"),
    ):
        assert not re.search(forbidden, text), (
            f"src/app/layout.tsx MUST NOT import {owner} — that module's owner is a later PR in the chain"
        )
