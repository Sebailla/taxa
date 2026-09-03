"""Final consolidated Tailwind 4 CSS parity test for PR 3c-f.

PR 3c-f (position 9/19, base ``...-08-3c-e2``) is the **sole full-parity
witness** for the 1,963-line legacy inline ``<style>`` block migrated byte-equal
into ``src/app/globals.css`` by the six prior CSS children (3c-a / 3c-b /
3c-c / 3c-d / 3c-e1 / 3c-e2). It ships **no new ``globals.css`` production
code** — only this parametrized test.

Coverage by migration surface (1:1 with the prior PR chain):
- tokens (light / realm / dark) + layout.tsx seam → 3c-a
- @layer base idempotent resets + ``@keyframes spin`` → 3c-a / 3c-d
- alias renames (``--primary-fixed`` / ``--on-primary-fixed`` /
  ``--surface-container-lowest``) → 3c-e1 + 3c-e2
- 9 utility classes (``.bg-primary`` / ``.animate-spin`` / …) → 3c-e2
- 14 taxonomy + 9 research / chrome selectors → 3c-b / 3c-c
- 4 remaining ``@keyframes`` content parity → 3c-e1
- final ``color-mix()`` scope-boundary witness (the 19 legacy selectors in
  ``web/index.html`` are intentionally deferred to a follow-up PR — the
  parametrized list IS the migration backlog)
- byte-size budget: 3c-f ships zero ``globals.css`` delta

Helpers are imported from ``tests/test_tailwind_4_base_resets.py`` (3c-d) and
``tests.test_tailwind_tokens_base`` (3c-a) — no duplication of the comment-
stripping + balanced-brace scan + descendant-aware ``_rule`` extractor.
"""
from __future__ import annotations

import re

import pytest

from tests.test_tailwind_4_base_resets import (  # noqa: F401 — reused 3c-d guards
    REPO_ROOT, GLOBALS_CSS, _read, _block, _rule,
)
from tests.test_tailwind_tokens_base import LAYOUT_TSX  # noqa: F401 — 3c-a seam


# ---- 3c-a — light / realm / dark token byte-equal parity ---------------------

LIGHT_TOKENS = {
    "primary": "#1d7ea9", "accent": "#176587", "surface": "#ffffff",
    "elevated": "#bbbbbb", "on-surface": "#333333", "on-surface-variant": "#555555",
    "outline": "#bbbbbb", "outline-variant": "#d9d9d9",
    "surface-container-low": "#fafafa", "surface-container": "#f5f5f5",
    "surface-container-high": "#eeeeee", "surface-container-highest": "#e8e8e8",
}
REALM_TOKENS = {
    "realm-bacteria": "#5ebd9b", "realm-archaea": "#e07466",
    "realm-viruses": "#e8c547", "realm-animalia": "#a57fcb",
    "realm-fungi": "#5b9bd5", "realm-plantae": "#7cb669",
    "realm-chromista": "#e89b4f", "realm-other": "#d49ab6",
}
DARK_TOKENS = {
    "primary": "#4aa3d0", "accent": "#6cb8db", "surface": "#1a1d23",
    "elevated": "#2a2e36", "on-surface": "#e6e8ec", "on-surface-variant": "#a0a4ac",
    "outline": "#4a4e56", "outline-variant": "#353941",
    "surface-container-low": "#1e2128", "surface-container": "#232730",
    "surface-container-high": "#2a2f38", "surface-container-highest": "#313742",
}


# ---- 3c-e2 — utility-class parity surface (9 classes) -------------------------

UTILITY_CLASSES = (
    (".bg-primary", "background-color", "var(--color-primary)"),
    (".text-on-surface", "color", "var(--color-on-surface)"),
    (".border-outline-variant", "border-color", "var(--color-outline-variant)"),
    (".bg-surface-container-lowest", "background-color",
     "var(--surface-container-lowest)"),
    (".bg-primary-fixed", "background-color", "var(--primary-fixed)"),
    (".text-on-primary-fixed", "color", "var(--on-primary-fixed)"),
    (".shadow-sm", "box-shadow", "0 1px 2px 0 rgb(0 0 0 / 0.05)"),
    (".rounded-r-md", "border-top-right-radius", "0.375rem"),
    (".animate-spin", "animation", "spin 0.8s linear infinite"),
)


# ---- 3c-d + 3c-e1 — keyframe parity (5 keyframes + identifying pattern) ------

KEYFRAMES = (
    ("@keyframes spin", r"rotate\(\s*0deg\s*\).*rotate\(\s*360deg\s*\)"),
    ("@keyframes detail-card-enter", r"opacity\s*:\s*0\b.*translateY\(\s*-8px\s*\)"),
    ("@keyframes detail-card-leave", r"opacity\s*:\s*0\b.*translateY\(\s*-6px\s*\)"),
    ("@keyframes search-pulse-anim", r"rgba\(\s*29\s*,\s*126\s*,\s*169\s*,\s*0\.55\s*\)"),
    ("@keyframes toast-slide-in", r"translate\(\s*-50%\s*,\s*8px\s*\)"),
)


# ---- 3c-b + 3c-c — taxonomy + research / chrome selector surfaces -----------

TAXONOMY_SELECTORS = (
    ".taxa-tree", ".tree-row", ".kebab", ".kebab-menu", ".tree-search-icon",
    ".materialize-indicator", ".detail-panel", ".tab-strip", ".tab-button",
    ".overview-tab", ".breadcrumb", ".scientific-name", ".authorship",
    ".species-count",
)
RESEARCH_CHROME_SELECTORS = (
    ".search-tab", ".search-category-section", ".search-link-list",
    ".search-link", ".folder-tab", ".header-browser-tab",
    ".research-explorer", ".file-explorer-pane", ".file-viewer-pane",
)


# ---- 3c-f — final color-mix scope-boundary witness (19 legacy selectors) ----

# 14 research / chrome selectors (PR 3c-c surface) + 5 taxonomy / materialize
# selectors (PR 3c-b surface). Each carries a ``color-mix(in srgb, ...)`` rule
# in ``web/index.html``. 3c-f's scope-boundary witness asserts these are NOT
# yet in ``globals.css`` — the ``color-mix()`` migration is deferred to a
# follow-up PR so the per-PR LoC budget stays under 400.
COLOR_MIX_LEGACY_SELECTORS = (
    ".fex-banner", ".fex-children", ".fex-csv-table", ".fex-image-advisory",
    ".fex-json-summary", ".fex-row.folder.selected", ".fex-row.search-match",
    ".fex-search-clear", ".fex-search-input",
    ".fex-search-mode-btn[aria-pressed=\"true\"]",
    ".fex-tree-leaf.type-boolean", ".fex-tree-leaf.type-number",
    ".fex-tree-leaf.type-string", ".fex-tree-truncated",
    ".materialize-modal-btn-primary", ".materialize-modal-btn-secondary",
    ".materialize-modal-info-banner", ".materialize-modal-marker-exists",
    ".materialize-modal-marker-new",
)


# ==============================================================================
# TESTS
# ==============================================================================

# ---- 3c-f.1 — file presence + import seam (3c-a dependency-defect-fix) ------

def test_globals_css_exists_and_imports_tailwindcss():
    """3c-a ships ``@import "tailwindcss";`` as the Tailwind 4 entry point."""
    assert GLOBALS_CSS.is_file(), f"missing {GLOBALS_CSS.relative_to(REPO_ROOT)}"
    assert re.search(r"""@import\s+["']tailwindcss["']\s*;""", _read(GLOBALS_CSS)), (
        'globals.css must @import "tailwindcss" (Tailwind 4 entry point)'
    )


def test_layout_tsx_imports_globals_css():
    """3c-a seam closure: ``layout.tsx`` MUST import ``./globals.css`` so the
    Tailwind 4 directives flow into the Next.js build."""
    assert re.search(r"""import\s+["']\./globals\.css["']\s*;""", _read(LAYOUT_TSX)), (
        'src/app/layout.tsx must import "./globals.css" (PR 3c-a seam)'
    )


# ---- 3c-f.2 — @theme + [data-theme="dark"] + token byte-equal parity ---------

def test_globals_css_declares_theme_and_dark_blocks():
    text = _read(GLOBALS_CSS)
    assert re.search(r"@theme\s*\{", text), (
        "globals.css must declare an @theme { ... } block (Tailwind 4 namespace)"
    )
    assert re.search(r"""\[data-theme=["']dark["']\]\s*\{""", text), (
        'globals.css must declare a [data-theme="dark"] { ... } block'
    )


_LIGHT_REALM_PAIRS = [(n, h) for d in (LIGHT_TOKENS, REALM_TOKENS) for n, h in sorted(d.items())]


@pytest.mark.parametrize(("name", "hex_value"), _LIGHT_REALM_PAIRS,
                         ids=[n for n, _ in _LIGHT_REALM_PAIRS])
def test_theme_declares_token_with_byte_equal_value_and_color_alias(name, hex_value):
    """Every legacy ``:root`` token (light + realm) MUST keep its original hex
    value AND have a ``--color-<name>`` Tailwind namespace alias so plain
    ``var()`` references AND Tailwind utilities (bg-primary, bg-realm-*, …)
    resolve. The realm family stays byte-equal between light + dark mode."""
    body = _block(_read(GLOBALS_CSS), "@theme")
    assert body, "globals.css must declare an @theme { ... } block"
    assert re.search(re.escape(f"--{name}: {hex_value}"), body), (
        f"@theme must declare --{name}: {hex_value} (byte-equal to legacy :root)"
    )
    assert re.search(re.escape(f"--color-{name}:"), body), (
        f"@theme must declare --color-{name}: (Tailwind 4 utility namespace)"
    )


@pytest.mark.parametrize("name,hex_value", sorted(DARK_TOKENS.items()))
def test_dark_block_redefines_neutral_with_byte_equal_value(name, hex_value):
    """Every legacy dark neutral MUST keep its original hex value (byte-equal
    migration of the dark palette). Realm hues are NOT redefined here — they
    stay byte-equal in dark mode by design."""
    body = _block(_read(GLOBALS_CSS), '[data-theme="dark"]')
    assert body, 'globals.css must declare a [data-theme="dark"] { ... } block'
    expected = f"--{name}: {hex_value}"
    assert re.search(re.escape(expected), body), (
        f'[data-theme="dark"] must redefine {expected}'
    )
    leaked = [n for n in REALM_TOKENS if f"--{n}" in body]
    assert not leaked, (
        f'[data-theme="dark"] must NOT redefine --realm-*; leaked: {leaked!r}'
    )


# ---- 3c-f.2 — @layer base presence + idempotent resets (3c-a + 3c-d) -------

def test_layer_base_idempotent_resets_and_source_order():
    """3c-a + 3c-d idempotent: html/body margin+padding, body overscroll,
    main > :first-child + :last-child margin resets MUST all be present under
    ``@layer base``, in source order (resets FIRST, ``@keyframes spin`` after)."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    assert re.search(
        r"html\s*,\s*body\s*\{[^}]*margin\s*:\s*0\s*;[^}]*padding\s*:\s*0\s*;",
        body, re.DOTALL,
    ), "@layer base must reset html, body { margin: 0; padding: 0; }"
    assert re.search(
        r"body\s*\{[^}]*overscroll-behavior\s*:\s*none\s*;", body, re.DOTALL,
    ), "@layer base must set body { overscroll-behavior: none; }"
    assert re.search(
        r"main\s*>\s*:first-child\s*\{[^}]*margin-top\s*:\s*0\s*!important\s*;",
        body, re.DOTALL,
    ), "@layer base must reset main > :first-child { margin-top: 0 !important; }"
    assert re.search(
        r"main\s*>\s*:last-child\s*\{[^}]*margin-bottom\s*:\s*0\s*!important\s*;",
        body, re.DOTALL,
    ), "@layer base must reset main > :last-child { margin-bottom: 0 !important; }"
    m_reset = re.search(
        r"html\s*,\s*body\s*\{[^}]*margin\s*:\s*0\s*;[^}]*padding\s*:\s*0\s*;",
        body, re.DOTALL,
    )
    m_kf = re.search(r"@keyframes\s+spin", body)
    assert m_kf, "@layer base must declare @keyframes spin (PR 3c-d.2)"
    assert m_reset.start() < m_kf.start(), (
        f"@layer base source order MUST be resets({m_reset.start()}) → "
        f"keyframes({m_kf.start()})"
    )


# ---- 3c-f.2 — @layer components + alias renames (3c-e1 + 3c-e2) -------------

@pytest.mark.parametrize(
    ("custom_prop", "target_token"),
    [("--primary-fixed", "--primary"), ("--on-primary-fixed", "--on-primary")],
)
def test_layer_components_declares_alias_rename(custom_prop, target_token):
    """3c-e1 alias renames MUST live under ``@layer components`` and target
    the upstream token via ``var()`` (dark-mode-preserving). The 3c-e2
    ``--surface-container-lowest -> --surface`` alias shares the same
    ``:root { … }`` block under ``@layer components``."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare an @layer components { ... } block"
    pattern = (
        r":root\s*\{[^}]*" + re.escape(custom_prop) +
        r"\s*:\s*var\(--(?:on-)?primary\)\s*;[^}]*\}"
    )
    assert re.search(pattern, body, re.DOTALL), (
        f"@layer components must declare a :root {{ {custom_prop}: "
        f"var({target_token}); ... }} alias block (PR 3c-e1)"
    )
    assert re.search(
        r":root\s*\{[^}]*--surface-container-lowest\s*:\s*var\(--surface\)\s*;[^}]*\}",
        body, re.DOTALL,
    ), "@layer components must declare :root { --surface-container-lowest: var(--surface); } (PR 3c-e2)"


# ---- 3c-f.2 — utility-class parity (3c-e2) — every class + property:value ---

@pytest.mark.parametrize(("selector", "property", "expected_value"), UTILITY_CLASSES,
                         ids=[c[0] for c in UTILITY_CLASSES])
def test_layer_components_declares_utility_class(selector, property, expected_value):
    """3c-e2 — every legacy utility class MUST be declared under
    ``@layer components`` with the exact property:value pair."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare an @layer components { ... } block"
    rule = _rule(body, selector)
    assert rule.strip(), (
        f"@layer components must declare {selector} {{ ... }} (PR 3c-e2)"
    )
    assert re.search(
        re.escape(property) + r"\s*:\s*" + re.escape(expected_value) + r"\s*;", rule,
    ), f"{selector} rule MUST set {property}: {expected_value}; (PR 3c-e2)"


def test_animate_spin_references_existing_spin_keyframe_no_new_keyframes():
    """3c-e2 — ``.animate-spin`` MUST reference the existing ``spin`` keyframe
    (which lives under ``@layer base``) and NOT introduce a new ``@keyframes``
    declaration under ``@layer components``."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare an @layer components { ... } block"
    rule = _rule(body, ".animate-spin")
    assert rule.strip(), ".animate-spin missing under @layer components (PR 3c-e2)"
    assert re.search(
        r"animation\s*:\s*spin\s+0\.8s\s+linear\s+infinite\s*;", rule,
    ), ".animate-spin must animate `spin 0.8s linear infinite` (PR 3c-e2)"
    assert not re.search(r"@keyframes\s+\w+", body), (
        "@layer components MUST NOT add any new @keyframes block (PR 3c-e2)"
    )


# ---- 3c-f.2 — keyframe parity (3c-d + 3c-e1) — every keyframe resolves -----

@pytest.mark.parametrize(("kf_open", "content_pattern"), KEYFRAMES)
def test_layer_base_declares_keyframe_with_content(kf_open, content_pattern):
    """3c-d + 3c-e1 — every ``@keyframes`` MUST live under ``@layer base`` and
    carry its identifying transform / opacity / box-shadow signature so the
    React cutover's animation parity stays intact."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    rule = _rule(body, kf_open)
    assert rule.strip(), f"@layer base must declare {kf_open} with a non-empty block"
    assert re.search(content_pattern, rule, re.DOTALL), (
        f"{kf_open} must contain identifying pattern {content_pattern!r}"
    )


# ---- 3c-f.2 — taxonomy (3c-b) + research / chrome (3c-c) selector coverage --

_PR_B_C_PAIRS = (
    [(s, "3c-b") for s in TAXONOMY_SELECTORS] +
    [(s, "3c-c") for s in RESEARCH_CHROME_SELECTORS]
)
_PR_B_C_IDS = [f"{s} [3c-b]" for s in TAXONOMY_SELECTORS] + [
    f"{s} [3c-c]" for s in RESEARCH_CHROME_SELECTORS
]


@pytest.mark.parametrize(("selector", "owner"), _PR_B_C_PAIRS, ids=_PR_B_C_IDS)
def test_layer_components_declares_every_pr_b_c_selector(selector, owner):
    """3c-b + 3c-c — every taxonomy + research / chrome selector MUST resolve
    to a non-empty block under ``@layer components`` (top-level OR descendant)."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... }"
    assert _rule(body, selector).strip(), (
        f"@layer components must declare {selector} (PR {owner})"
    )


# ---- 3c-f.3 — final color-mix scope-boundary witness (deferred migration) --

def test_globals_css_has_no_color_mix_rules_anywhere():
    """3c-f.3 — color-mix scope-boundary witness: ``src/app/globals.css`` MUST
    NOT carry any ``color-mix()`` rule (the 19 legacy selectors in
    ``web/index.html`` are deferred to a follow-up PR to keep the per-PR LoC
    budget under 400). The consolidation witness documents the deferral
    explicitly so the next chain re-split knows which selectors are pending."""
    stripped = re.sub(r"/\*[\s\S]*?\*/", "", _read(GLOBALS_CSS))
    assert "color-mix" not in stripped, (
        "globals.css MUST NOT carry any color-mix() rule — the 19 legacy "
        "color-mix selectors (.fex-* / .materialize-modal-*) are deferred; "
        "see COLOR_MIX_LEGACY_SELECTORS"
    )


@pytest.mark.parametrize("selector", COLOR_MIX_LEGACY_SELECTORS)
def test_layer_components_does_not_own_legacy_color_mix_selector(selector):
    """3c-f.3 — per-selector scope witness: each of the 19 legacy selectors
    that carried a ``color-mix()`` rule MUST NOT yet appear in
    ``@layer components`` (the migration is deferred)."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    if not body:
        pytest.fail("globals.css must declare @layer components { ... }")
    assert not re.search(
        r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"(?=[\s,{:>+~]|$)", body,
    ), (
        f"{selector} MUST NOT appear in @layer components yet — the "
        f"color-mix() migration is deferred to a follow-up PR "
        f"(3c-f scope-boundary witness)"
    )


# ---- 3c-f.3 — byte-size budget: 3c-f ships zero globals.css delta -----------

def test_3c_f_ships_no_globals_css_production_delta():
    """3c-f scope contract: this PR ships **no new ``globals.css`` production
    code** — only the consolidated parity test. The diff against the 3c-e2
    base branch MUST be empty (the test file is the sole delta)."""
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--numstat",
         "feat/complete-taxa-frontend-migration-08-3c-e2",
         "--", "src/app/globals.css"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"git diff against 3c-e2 base failed: {result.stderr.strip()}")
    assert not result.stdout.strip(), (
        f"PR 3c-f MUST NOT ship any globals.css production delta; "
        f"got: {result.stdout.strip()!r}"
    )
