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


# ---- PR 3c-ii taxonomy selector catalogue --------------------------------------
# OpenSpec 3c-ii.1 R — root + state selectors per the canonical taxonomy
# tree / detail styling slice. PR 3c-ii lands these under ``@layer base``
# (in source order, matching the legacy inline-style cascade). ``.kebab``
# and ``.kebab-menu`` base selectors are EXTRACTED to ``@layer components``
# per OpenSpec 3c-ii.5 (stable layer name for the React ``<Kebab>``
# component in PR 5a) and live in ``KEBAB_COMPONENT_SELECTORS`` below.
TAXONOMY_SELECTORS = (
    # tier-group header + load-all
    ".tier-header", ".load-all",
    # search-results + search-hit + tag-*
    "#search-results", ".search-hit",
    ".tag-vernacular", ".tag-scientific", ".tag-authorship",
    # tree-source-toggle + rank-badge
    ".tree-source-toggle", ".tree-source-btn", ".rank-badge",
    # scientific-name + roman modifier
    ".scientific-name", ".scientific-name--roman",
    # detail-panel + closing + detail-card + detail-header
    "#detail-panel", ".detail-card", ".detail-header",
    # detail-section + overview-* + detail-item + means-*
    ".detail-section", ".detail-section h3", ".detail-section .count",
    ".overview-section", ".overview-rank",
    ".overview-grid", ".overview-row", ".overview-label",
    ".overview-value", ".overview-chain", ".overview-chain-segment",
    ".detail-item",
    ".means-native", ".means-introduced",
    ".means-uncertain", ".means-unknown",
    # search-pulse + detail-tabs + detail-tab
    ".search-pulse", ".detail-tabs", ".detail-tab",
    # search-icon-btn + materialize-btn
    ".search-icon-btn", ".materialize-btn",
    # kebab variants (OpenSpec 3c-ii.5 — base selectors extracted,
    # .kebab-menu.open rides along for cascade correctness; the rest
    # of the variants + state selectors stay in ``@layer base``)
    ".kebab-trigger", ".kebab-item",
    ".kebab-item-label",
    # materialize-modal-* + materialize-tab-*
    ".materialize-tab-content", ".materialize-tab-loading",
    ".materialize-tab-error",
    ".materialize-modal-section-title", ".materialize-modal-list",
    ".materialize-modal-list-item", ".materialize-modal-marker",
    ".materialize-modal-marker-exists", ".materialize-modal-marker-new",
    ".materialize-modal-segment-path", ".materialize-modal-counts",
    ".materialize-modal-info-banner", ".materialize-modal-actions",
    ".materialize-modal-btn", ".materialize-modal-btn-primary",
    ".materialize-modal-btn-secondary", ".materialize-modal-path-actions",
)

# OpenSpec 3c-ii.5 — kebab base selectors extracted into ``@layer
# components`` so the React ``<Kebab>`` component in PR 5a can consume
# them via a stable layer name. The ``.kebab { ... }`` and
# ``.kebab-menu { ... }`` base blocks live here; the ``.kebab-menu.open``
# state selector rides along so it correctly wins over the
# ``.kebab-menu { display: none }`` base rule via source order inside
# the same layer (cascade correction). Other variants + state
# selectors stay in ``@layer base``.
KEBAB_COMPONENT_SELECTORS = (".kebab", ".kebab-menu", ".kebab-menu.open")

# OpenSpec 3c-ii.2 — realm-tinted ``.tree-row[data-realm="<realm>"]
# .scientific-name`` selectors MUST reference ``var(--realm-<realm>)``
# verbatim (the realm hue round-trips through the family shipped by
# 3c-i.1). ``other`` is intentionally absent — the catch-all
# ``.tree-row[data-realm] .scientific-name { color: var(--realm-other); }``
# rule already covers the default tint (asserted separately below).
REALM_TAXONOMY_PAIRS = (
    ("bacteria", "realm-bacteria"), ("archaea", "realm-archaea"),
    ("viruses", "realm-viruses"), ("animalia", "realm-animalia"),
    ("fungi", "realm-fungi"), ("plantae", "realm-plantae"),
    ("chromista", "realm-chromista"),
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


# ==============================================================================
# PR 3c-ii — taxonomy tree / detail styling slice
# ==============================================================================
# Extends the 3c-i foundation with the canonical taxonomy selectors. Uses
# existing 3c-i tokens (no new ``@theme`` entries + no ``--color-*``
# aliases); preserves source order per OpenSpec 3c-ii.2; puts ``.kebab``
# + ``.kebab-menu`` base selectors into ``@layer components`` per
# OpenSpec 3c-ii.5. Asserts presence + non-empty declaration only —
# byte-equal value parity lives in ``tests/test_tailwind_tokens_base.py``.

# ---- 3c-ii.1 — taxonomy selectors live under @layer base --------------------

def test_taxonomy_selectors_resolve_under_layer_base():
    """Every canonical 3c-ii taxonomy selector MUST resolve to a
    non-empty declaration block under ``@layer base`` in
    ``src/app/globals.css``. ``@layer base`` is the OpenSpec-prescribed
    layer for the taxonomy surface (preserves the legacy inline-style
    cascade); the bare ``.kebab`` + ``.kebab-menu`` selectors are
    EXTRACTED to ``@layer components`` per OpenSpec 3c-ii.5 and live in
    the dedicated kebab-component test below."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    # Match each selector as a standalone CSS token, then require a
    # non-empty body (any character except whitespace or braces between
    # the opening ``{`` and the matching ``}``).
    missing = [
        s for s in TAXONOMY_SELECTORS
        if not re.search(
r"(?:^|[\s,{}>+~])" + re.escape(s) + r"\s*\{[^}]*\S[^}]*\}",
body,
        )
    ]
    assert not missing, (
        f"@layer base MUST declare every taxonomy selector with a non-empty "
        f"body (PR 3c-ii taxonomy selector slice); missing: {missing!r}"
    )


# ---- 3c-ii.2 — kebab base selectors extracted to @layer components ----------

def test_globals_css_declares_layer_components_block():
    """``@layer components { ... }`` MUST exist (Tailwind 4 components
    layer). The ``.kebab`` + ``.kebab-menu`` base selectors are extracted
    into this layer per OpenSpec 3c-ii.5 so the React ``<Kebab>``
    component in PR 5a can consume them via a stable layer name."""
    text = _read(GLOBALS_CSS)
    assert re.search(r"@layer\s+components\s*\{", text), (
        "globals.css must declare an @layer components { ... } block "
        "(PR 3c-ii.5 kebab extraction seam)"
    )


def test_kebab_base_selectors_resolve_under_layer_components():
    """``.kebab`` + ``.kebab-menu`` MUST live under ``@layer components``
    with a non-empty declaration — NOT under ``@layer base``. This is
    the OpenSpec 3c-ii.5 extraction that lets the React ``<Kebab>``
    component in PR 5a consume the CSS via a stable layer name.
    ``.kebab-menu.open`` also lives here so the open state correctly
    wins over the ``.kebab-menu { display: none }`` base rule via
    source order inside the same layer (cascade correction)."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare an @layer components { ... } block"
    missing = [
        s for s in KEBAB_COMPONENT_SELECTORS
        if not re.search(
r"(?:^|[\s,{}>+~])" + re.escape(s) + r"\s*\{[^}]*\S[^}]*\}",
body,
        )
    ]
    assert not missing, (
        f"@layer components MUST declare every kebab base selector with a "
        f"non-empty body (PR 3c-ii.5 kebab extraction); missing: {missing!r}"
    )


def test_kebab_base_selectors_do_not_live_under_layer_base():
    """The bare ``.kebab`` + ``.kebab-menu`` base selectors MUST live
    under ``@layer components`` (OpenSpec 3c-ii.5) — NOT under
    ``@layer base``. ``.kebab-menu.open`` also lives under
    ``@layer components`` for cascade correctness; the remaining
    variants + state selectors (``.kebab-trigger``, ``.kebab-item``,
    …) remain in ``@layer base``."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    # Look for the bare selectors at CSS-token boundaries followed by a
    # declaration block — not as part of a larger selector or descendant
    # rule. ``.kebab-menu.open`` carries ``.kebab-menu`` as a prefix
    # inside the selector list, so a token-boundary scan excludes it.
    leaked = [
        s for s in KEBAB_COMPONENT_SELECTORS
        if re.search(
r"(?:^|[\s,{}>+~])" + re.escape(s) + r"\s*\{",
body,
        )
    ]
    assert not leaked, (
        f"@layer base MUST NOT declare the bare {KEBAB_COMPONENT_SELECTORS!r} "
        f"selectors (those belong to @layer components per OpenSpec 3c-ii.5); "
        f"leaked: {leaked!r}"
    )


def test_kebab_variants_do_not_live_under_layer_components():
    """Kebab variants (``.kebab-trigger``, ``.kebab-item``,
    ``.kebab-item-label``) MUST remain in ``@layer base`` per
    OpenSpec 3c-ii.5 — the extraction is scoped to the bare base
    selectors plus the ``.kebab-menu.open`` cascade-corrected state
    selector (asserted separately via ``KEBAB_COMPONENT_SELECTORS``)
    only. This protects against a future refactor that sweeps the
    remaining kebab-related rules into ``@layer components``."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare an @layer components { ... } block"
    kebab_variants = (
        ".kebab-trigger",
        ".kebab-item", ".kebab-item-label",
    )
    leaked = [
        s for s in kebab_variants
        if re.search(
r"(?:^|[\s,{}>+~])" + re.escape(s) + r"\s*\{",
body,
        )
    ]
    assert not leaked, (
        f"@layer components MUST NOT declare kebab variants {kebab_variants!r} "
        f"(only the bare .kebab + .kebab-menu base selectors and the "
        f".kebab-menu.open cascade-corrected state selector belong here per "
        f"OpenSpec 3c-ii.5); leaked: {leaked!r}"
    )


# ---- 3c-ii.3 — realm-tinted scientific-name selectors round-trip via --realm-*

def test_globals_css_declares_default_realm_other_scientific_name():
    """The catch-all ``.tree-row[data-realm] .scientific-name { color:
    var(--realm-other); }`` selector MUST live under ``@layer base`` —
    it sets the default realm tint before the per-realm overrides."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    pattern = (
        r"\.tree-row\[data-realm\]\s+\.scientific-name\s*\{[^}]*"
        r"var\s*\(\s*--realm-other\s*\)[^}]*\}"
    )
    assert re.search(pattern, body), (
        "@layer base must declare .tree-row[data-realm] .scientific-name "
        "{ color: var(--realm-other); } (PR 3c-ii realm default tint)"
    )


def test_realm_tinted_scientific_name_uses_realm_token():
    """Each ``.tree-row[data-realm="<realm>"] .scientific-name`` selector
    MUST reference ``var(--realm-<realm>)`` verbatim — the realm hue
    round-trips through the ``--realm-*`` family shipped by 3c-i.1.
    ``other`` is intentionally absent — the catch-all rule already
    covers the default tint (asserted separately above)."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    missing = []
    for realm, token_name in REALM_TAXONOMY_PAIRS:
        selector = f'.tree-row[data-realm="{realm}"] .scientific-name'
        pattern = (
            re.escape(selector) + r"\s*\{[^}]*var\s*\(\s*--"
            + re.escape(token_name) + r"\s*\)[^}]*\}"
        )
        if not re.search(pattern, body):
            missing.append((realm, token_name))
    assert not missing, (
        f"@layer base MUST declare every realm-tinted selector with "
        f"var(--realm-<realm>); missing: {missing!r}"
    )


def test_realm_selected_focused_scientific_name_uses_primary_token():
    """``selected`` + ``focused`` ``.tree-row`` variants MUST override
    the realm tint with ``var(--primary)`` so the active row stays the
    clearest signal on the page (specificity tied with the per-realm
    selectors above, so source order resolves it)."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    pattern = (
        r"\.tree-row\.selected\s+\.scientific-name\s*,\s*"
        r"\.tree-row\.focused\s+\.scientific-name\s*\{[^}]*"
        r"var\s*\(\s*--primary\s*\)[^}]*\}"
    )
    assert re.search(pattern, body), (
        "@layer base must declare .tree-row.selected .scientific-name, "
        ".tree-row.focused .scientific-name { color: var(--primary); } "
        "(PR 3c-ii selected/focused realm override)"
    )


# ---- 3c-ii.4 — slice-scope guards: 3c-iii / 3c-iv MUST NOT bleed in ---------
# Deferred surfaces for LATER 3c children. PR 3c-ii MUST NOT ship them.
# The 8 3c-ii surfaces that USED to live in this guard were promoted out
# in this PR; the 3c-iii / 3c-iv surfaces stay deferred.

def test_globals_css_does_not_pre_assert_3c_iii_or_3c_iv_surfaces():
    """Strict TDD scope guard: PR 3c-ii MUST NOT pre-assert any surface
    owned by 3c-iii (Search / Folder / global Browser styling) or
    3c-iv (animations / utilities + final parity). Pre-asserting them
    would silently reserve their namespace and block the per-PR review
    focus across the rest of the 3c sub-sequence."""
    text = _strip_comments(_read(GLOBALS_CSS))
    leaked = [s for s in LATER_CHILD_SURFACES if _appears_as_css_token(text, s)]
    assert not leaked, (
        f"PR 3c-ii MUST NOT pre-define surfaces reserved for 3c-iii / 3c-iv; "
        f"leaked: {leaked!r}"
    )


def test_globals_css_has_no_color_mix_rules_in_3c_ii_slice():
    """PR 3c-ii MUST keep ``globals.css`` free of ``color-mix()`` rules
    — those land with PR 3c-iv's animation + utilities slice. The legacy
    taxonomy surface uses solid hex literals for the few non-token colors
    (tag tints, means badges); 3c-ii ports them byte-equal without
    re-introducing color-mix drift inside the base layer."""
    text = _strip_comments(_read(GLOBALS_CSS))
    assert "color-mix" not in text, (
        "globals.css MUST NOT carry any color-mix() rule in PR 3c-ii — "
        "those land with PR 3c-iv"
    )
