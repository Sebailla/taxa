"""Roman-named 3c parity test — tokens / base / dark mode / taxonomy /
Search / Folder / global Browser / file-explorer chrome slice.

The 3c sub-sequence ships in four chained children (PR 3c-i / 3c-ii /
3c-iii / 3c-iv, positions 3–6/16 of the broader
``complete-taxa-frontend-migration`` chain). This test file is the
canonical Roman-named contract for the sub-sequence:

  - **3c-i** (position 3/16) — ``@import "tailwindcss"`` + ``@theme``
    block (every legacy :root token: 12 light + 8 ``--realm-*``) +
    ``[data-theme="dark"]`` cascade + ``@layer base`` with html / body /
    ``main > :first-child`` resets + global ``:focus-visible`` selectors.
  - **3c-ii** (position 4/16) — taxonomy tree / detail selectors under
    ``@layer base`` (preserves the legacy inline-style cascade), kebab
    base selectors extracted to ``@layer components`` per OpenSpec
    3c-ii.5, realm-tinted ``.tree-row[data-realm="..."] .scientific-name``
    selectors referencing ``var(--realm-*)``.
  - **3c-iii** (position 5/16) — Search / Folder / global Browser /
    file-explorer chrome. Toast + materialize toast; search-engine grid
    + category headers + engine buttons + label spans; file-explorer
    chrome (``.fex-shell``, ``.fex-tree-pane``, ``.fex-viewer-pane``,
    ``.fex-splitter`` + drag states, ``.fex-row`` + hover + selected,
    ``.fex-tree-header``, ``.fex-children``, ``.fex-banner``,
    ``.fex-empty-state``, ``.fex-search-*`` + search-clear visibility
    invariant, ``.fex-csv-*``, ``.fex-json-*``, ``.fex-tree-truncated``);
    snippet toolbar (``.fex-meta-strip``, ``.fex-tab-strip``,
    ``.fex-snippet-frame``, ``.fex-snippet-btn`` + disabled);
    realm-tinted ``.fex-row.folder[data-realm="..."]`` variants
    referencing ``var(--realm-*)``. File-explorer chrome lives under
    ``@layer components`` per OpenSpec 3c-iii.5; the realm-tinted folder
    variants stay co-located with the ``.tree-row[data-realm="..."]``
    selectors in ``@layer base`` so the ``--realm-*`` round-trip stays
    in one place. The no-color-mix restriction from PR 3c-i / 3c-ii is
    relaxed enough to permit legacy 3c-iii ``color-mix(in srgb,
    var(--token) NN%, transparent)`` calls (those carry the
    focus / hover / drag-state alpha mixing the legacy inline-style
    block relies on).
  - **3c-iv** (position 6/16) — ``@keyframes`` rules (animation +
    utilities + final CSS parity + design-system barrel). The 3c-iv
    surface stays deferred and is the ONLY ``LATER_CHILD_SURFACES`` in
    this file.

Full-parity witness for the 3c-iv surface lands with PR 3c-iv.
The byte-equal hex value contract for each token is covered by the existing
``tests/test_tailwind_tokens_base.py``; this test asserts the narrow
Roman-named contract (presence + non-empty declarations + key state
invariants like the search-clear visibility rule and the realm token
round-trip).
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


# ---- 3c-i.5 — slice-scope guards: 3c-iv MUST NOT bleed in ----------------------

# Surface names reserved for the LATER 3c children. After PR 3c-iii lands
# only the 3c-iv surfaces remain deferred (animations + utility classes +
# final CSS parity). The six 3c-iii surfaces that used to live here were
# promoted out in this PR (``test_3c_iii_promotes_the_six_later_child_guarded_surfaces``
# asserts the promotion). Matched at CSS-token boundaries so PR 3c-i's
# ``.tier-header:focus-visible`` and ``.load-all:focus-visible`` rules
# don't false-positive as 3c-iv bleed; only the bare top-level rules
# trip the guard.
LATER_CHILD_SURFACES = (
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
    """3c-i foundation slice MUST keep its OWN surfaces free of
    ``color-mix()`` calls so the foundation layer (tokens + base +
    dark mode) never silently accepts color-mix drift. PR 3c-iii
    RELAXES this guard enough to permit legacy ``color-mix()`` calls
    on the file-explorer chrome focus / hover / drag-state alpha
    mixing; the relaxation is explicitly scoped via the
    ``test_3c_iii_uses_color_mix_for_legacy_calls`` and
    ``test_3c_iii_color_mix_is_legacy_in_srgb_shape`` assertions so
    any future 3c-i / 3c-ii slice that picks up ``color-mix()``
    drift still trips the foundation guard.

    Implementation: scan the ``@theme`` block + the
    ``[data-theme="dark"]`` block + the ``@layer base`` block. The
    ``@layer base`` block carries 3c-i + 3c-ii + 3c-iii rules, but
    the 3c-i + 3c-ii portion never carries ``color-mix()`` so any
    detection inside ``@layer base`` would be 3c-iii bleed (asserted
    separately via ``test_3c_iii_does_not_pre_assert_3c_iv_surfaces``).
    The ``@layer components`` block + any other top-level rules are
    outside the foundation scope and may carry ``color-mix()`` —
    that's the 3c-iii scope."""
    theme_body = _block(_read(GLOBALS_CSS), "@theme")
    dark_body = _block(_read(GLOBALS_CSS), '[data-theme="dark"]')
    base_body = _block(_read(GLOBALS_CSS), "@layer base")
    for layer_name, body in (
        ("@theme", theme_body), ("[data-theme=\"dark\"]", dark_body),
        ("@layer base", base_body),
    ):
        body = _strip_comments(body)
        assert "color-mix" not in body, (
            f"PR 3c-i foundation slice ({layer_name}) MUST NOT carry any "
            f"colour-mix() rule — the foundation has no legacy alpha-mixing "
            f"surface; 3c-iii owns the legacy colour-mix() call sites "
            f"(asserted separately)"
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


# ---- 3c-ii.4 — slice-scope guards: 3c-iv MUST NOT bleed in -----------------
# Deferred surfaces for the LATER 3c children. PR 3c-ii MUST NOT ship
# them. The eight 3c-ii surfaces that USED to live in this guard were
# promoted out in PR 3c-ii; the six 3c-iii surfaces were promoted out in
# PR 3c-iii (asserted separately); only the 3c-iv surfaces stay
# deferred.

def test_globals_css_does_not_pre_assert_3c_iv_surfaces():
    """Strict TDD scope guard: PR 3c-ii MUST NOT pre-assert any surface
    owned by 3c-iv (animations / utilities + final parity). Pre-asserting
    them would silently reserve their namespace and block the per-PR
    review focus across the rest of the 3c sub-sequence. (The 3c-iii
    surfaces are no longer in scope — they landed in PR 3c-iii, asserted
    separately.)"""
    text = _strip_comments(_read(GLOBALS_CSS))
    leaked = [s for s in LATER_CHILD_SURFACES if _appears_as_css_token(text, s)]
    assert not leaked, (
        f"PR 3c-ii MUST NOT pre-define surfaces reserved for 3c-iv; "
        f"leaked: {leaked!r}"
    )


def test_globals_css_has_no_color_mix_rules_in_3c_ii_slice():
    """PR 3c-ii MUST keep its OWN slice free of ``color-mix()`` rules —
    the legacy taxonomy surface uses solid hex literals for the few
    non-token colours (tag tints, means badges); 3c-ii ports them
    byte-equal without re-introducing colour-mix drift inside the
    base layer. (PR 3c-iii's colour-mix usage — focus / hover / drag
    alpha on the file-explorer chrome — is asserted separately via
    ``test_3c_iii_uses_color_mix_for_legacy_calls`` and stays scoped to
    the 3c-iii selectors.)

    Implementation: the 3c-ii slice lives under ``@layer base`` between
    the 3c-i focus-visible selectors (top of the layer) and the 3c-iii
    realm-tinted ``.fex-row.folder[data-realm="..."]`` variants (bottom
    of the layer). The colour-mix guard extracts the
    ``@layer base`` body + the ``@layer components`` body — the 3c-ii
    taxonomy selectors live in ``@layer base`` (no colour-mix there in
    the 3c-ii slice), and 3c-ii's ``.kebab`` + ``.kebab-menu`` base
    selectors live in ``@layer components`` (no colour-mix there in
    the 3c-ii slice). 3c-iii's colour-mix calls live in
    ``@layer components`` and ride on the 3c-iii selectors — those
    are NOT in 3c-ii's slice (asserted separately)."""
    base_body = _strip_comments(_block(_read(GLOBALS_CSS), "@layer base"))
    components_body = _strip_comments(_block(_read(GLOBALS_CSS), "@layer components"))
    # The kebab base selectors live in @layer components — assert
    # they're colour-mix-free in their slice (the 3c-iii colour-mix
    # calls ride on different selectors in the same layer).
    for layer_name, body in (
        ("@layer base", base_body),
        ("@layer components", components_body),
    ):
        assert "color-mix" not in body, (
            f"PR 3c-ii slice ({layer_name}) MUST NOT carry any colour-mix() "
            f"rule — those are scoped to PR 3c-iii (file-explorer chrome "
            f"focus / hover / drag-state alpha mixing). Detected "
            f"colour-mix() drift inside the 3c-ii slice"
        )


# ==============================================================================
# PR 3c-iii — Search / Folder / global Browser / file-explorer chrome slice
# ==============================================================================
# Extends the 3c-i / 3c-ii foundation with the canonical Search / Folder /
# global Browser / file-explorer chrome surface. Uses existing 3c-i tokens
# (no new ``@theme`` entries + no ``--color-*`` aliases); preserves
# source order per OpenSpec 3c-iii; puts file-explorer chrome under
# ``@layer components`` per OpenSpec 3c-iii.5 with the realm-tinted
# ``.fex-row.folder[data-realm="..."]`` selectors co-located with the
# ``.tree-row[data-realm="..."]`` selectors from 3c-ii (so the
# ``--realm-*`` round-trip stays in one place); allows the legacy
# 3c-iii ``color-mix()`` calls the focus / hover / drag-state alpha
# mixing on the file-explorer chrome relies on. Asserts presence +
# non-empty declaration + the key state invariants (search-clear
# visibility, realm token round-trip, splitter hover / dragging,
# aria-pressed search toggles).

# ---- 3c-iii selector catalogue ----------------------------------------------
# Canonical 3c-iii selectors. Grouped by concern so the per-concern test
# names tell the reviewer what surface the assertion guards.
#
# toast + materialize-toast — global toast surface
TOAST_SELECTORS = (".toast", ".toast-error")
# search engines grid + per-engine button + label span
SEARCH_ENGINE_SELECTORS = (
    ".search-engines-grid",
    ".search-category-header",
    ".search-category-header:first-child",
    ".search-category-header .material-symbols-outlined",
    ".search-engine-btn",
    ".search-engine-btn:hover",
    ".search-engine-btn:focus-visible",
    ".search-engine-btn:active",
    ".search-engine-btn .material-symbols-outlined",
    ".search-engine-btn:hover .material-symbols-outlined",
    ".search-engine-btn-label",
)
# search-tab parent + descendants (per the refactor contract, the parent
# collapses its children into a single rule). NB the children
# ``.search-category-section`` + ``.search-link-list`` + ``.search-link``
# + ``.search-link-label`` live inside ``.search-tab { ... }`` and are
# NOT separate top-level rules.
SEARCH_TAB_PARENT = ".search-tab"
SEARCH_TAB_DESCENDANTS = (
    ".search-category-section",
    ".search-link-list",
    ".search-link",
    ".search-link-label",
)
# folder-tab + per-action buttons (retry / create)
FOLDER_TAB_SELECTORS = (
    ".folder-tab",
    ".folder-tab-retry",
    ".folder-tab-create",
)
# global browser surface (.header-browser-tab + .header-browser-tab-host
# + the .research-explorer mega-block per OpenSpec 3c-iii.5)
HEADER_BROWSER_SELECTORS = (".header-browser-tab", ".header-browser-tab-host")
# research-explorer parent + descendants collapsed into a single rule
RESEARCH_EXPLORER_PARENT = ".research-explorer"
RESEARCH_EXPLORER_DESCENDANTS = (
    ".file-explorer-pane", ".file-viewer-pane",
)
# file-explorer chrome — ALL fex-* selectors live inside the
# .research-explorer parent rule per the 3c-iii.5 refactor. Asserted
# as descendants of .research-explorer (NOT separate top-level rules).
FEX_CHROME_SELECTORS = (
    # shell + panes + splitter (with hover / dragging states)
    ".fex-shell",
    ".fex-tree-pane", ".fex-viewer-pane",
    ".fex-splitter", ".fex-splitter::after",
    ".fex-splitter:hover", ".fex-splitter.dragging",
    # tree header + per-row chrome + per-row chevron / icon / label
    ".fex-tree-header", ".fex-tree-header h2",
    ".fex-row", ".fex-row:hover",
    ".fex-row .fex-chevron", ".fex-row .fex-icon",
    ".fex-row .fex-label", ".fex-row .fex-meta",
    # file-row selected (per-element overrides)
    ".fex-row.file.selected",
    ".fex-row.file.selected .fex-icon",
    ".fex-row.file.selected .fex-label",
    ".fex-row.file.selected .fex-meta",
    # folder-row selected
    ".fex-row.folder.selected",
    # generic realm-tinted folder row chrome (default tint + per-realm
    # tints; per-realm selectors round-trip via var(--realm-<realm>))
    ".fex-row.folder[data-realm] .fex-icon",
    ".fex-row.folder[data-realm] .fex-label",
    # children + banner + empty state chrome
    ".fex-children",
    ".fex-banner",
    ".fex-empty-state",
    ".fex-empty-state .fex-empty-state-icon",
    # tree-header-search + the search-row / search-icon / search-input /
    # search-clear / search-toggles / search-mode-btn / search-hide-empty-btn
    # + their focus / placeholder-shown / aria-pressed states
    ".fex-tree-header-search",
    ".fex-search-row",
    ".fex-search-row .fex-search-icon",
    ".fex-search-input", ".fex-search-input:focus",
    ".fex-search-clear",
    ".fex-search-clear:hover",
    ".fex-search-clear .material-symbols-outlined",
    ".fex-search-input:not(:placeholder-shown) ~ .fex-search-clear",
    ".fex-search-toggles",
    ".fex-search-mode-btn",
    ".fex-search-mode-btn .material-symbols-outlined",
    '.fex-search-mode-btn[aria-pressed="true"]',
    ".fex-search-hide-empty-btn",
    ".fex-search-hide-empty-btn .material-symbols-outlined",
    '.fex-search-hide-empty-btn[aria-pressed="true"]',
    # search-match row highlight + empty-search result state
    ".fex-row.search-match",
    ".fex-search-empty",
)
# snippet toolbar — meta strip + tab strip + snippet frame + snippet btn
SNIPPET_TOOLBAR_SELECTORS = (
    ".fex-meta-strip",
    ".fex-meta-strip > .fex-meta-spacer",
    ".fex-tab-strip",
    ".fex-tab-strip button",
    ".fex-tab-strip button.active",
    ".fex-snippet-frame",
    ".fex-snippet-title",
    ".fex-snippet-dots",
    ".fex-snippet-dots span",
    ".fex-snippet-dots .dot-r",
    ".fex-snippet-dots .dot-y",
    ".fex-snippet-dots .dot-g",
    ".fex-snippet-body",
    ".fex-snippet-actions",
    ".fex-snippet-btn",
    ".fex-snippet-btn:hover",
    ".fex-snippet-btn:disabled",
)
# CSV scroller — table + zebra + hover
FEX_CSV_SELECTORS = (
    ".fex-csv-scroller",
    ".fex-csv-table",
    ".fex-csv-table thead th",
    ".fex-csv-table tbody td",
    ".fex-csv-table tbody tr:nth-child(even) td",
    ".fex-csv-table tbody tr:hover td",
)
# JSON tree viewer — caret + summary + node states + leaf type pills
FEX_JSON_SELECTORS = (
    ".fex-json-tree",
    ".fex-json-children",
    ".fex-json-node",
    ".fex-json-summary",
    ".fex-json-summary:hover",
    ".fex-json-summary:focus-visible",
    ".fex-json-caret",
    ".fex-json-node.open > .fex-json-summary > .fex-json-caret",
    ".fex-json-key",
    ".fex-tree-leaf",
    ".fex-tree-leaf.type-string",
    ".fex-tree-leaf.type-number",
    ".fex-tree-leaf.type-boolean",
    ".fex-tree-leaf.type-null",
    ".fex-tree-leaf.type-meta",
)
# Truncation banner (fex-tree-truncated + the icon child)
FEX_TRUNCATED_SELECTORS = (
    ".fex-tree-truncated",
    ".fex-tree-truncated .material-symbols-outlined",
)

# All 3c-iii selectors flattened — used by the per-selector presence
# tests below. NB the descendants (SEARCH_TAB_DESCENDANTS +
# RESEARCH_EXPLORER_DESCENDANTS + FEX_CHROME_SELECTORS +
# SNIPPET_TOOLBAR_SELECTORS + FEX_CSV_SELECTORS + FEX_JSON_SELECTORS +
# FEX_TRUNCATED_SELECTORS) all live INSIDE their respective parent
# rule per the 3c-iii.5 refactor contract (asserted separately).
ALL_3C_III_SELECTORS = (
    *TOAST_SELECTORS,
    *SEARCH_ENGINE_SELECTORS,
    SEARCH_TAB_PARENT, *SEARCH_TAB_DESCENDANTS,
    *FOLDER_TAB_SELECTORS,
    *HEADER_BROWSER_SELECTORS,
    RESEARCH_EXPLORER_PARENT, *RESEARCH_EXPLORER_DESCENDANTS,
    *FEX_CHROME_SELECTORS,
    *SNIPPET_TOOLBAR_SELECTORS,
    *FEX_CSV_SELECTORS,
    *FEX_JSON_SELECTORS,
    *FEX_TRUNCATED_SELECTORS,
)

# Realm taxonomy pairs for the ``.fex-row.folder[data-realm="<realm>"]``
# tint selectors. Round-trips through the ``--realm-*`` family shipped by
# 3c-i.1 (mirror of ``REALM_TAXONOMY_PAIRS`` above for the taxonomy
# tree-row tints). ``other`` is intentionally absent — the catch-all
# ``.fex-row.folder[data-realm] .fex-icon`` +
# ``.fex-row.folder[data-realm] .fex-label`` rules already carry the
# default ``var(--realm-other)`` tint (asserted separately).
REALM_FOLDER_PAIRS = (
    ("bacteria", "realm-bacteria"), ("archaea", "realm-archaea"),
    ("viruses", "realm-viruses"), ("animalia", "realm-animalia"),
    ("fungi", "realm-fungi"), ("plantae", "realm-plantae"),
    ("chromista", "realm-chromista"),
)


# ---- 3c-iii.1 — selector catalogue resolves under @layer components -------

def test_3c_iii_promotes_the_six_later_child_guarded_surfaces():
    """3c-iii.1 promotion guard: PR 3c-iii MUST define every one of the
    six surfaces that used to live in the LATER_CHILD_SURFACES guard
    (``test_globals_css_does_not_pre_assert_later_child_surfaces`` was
    relaxed to keep ONLY the 3c-iv surfaces). Asserted at the bare
    top-level boundary so the relaxed guard can't false-positive on
    descendant rules inside ``.research-explorer`` or ``.search-tab``."""
    text = _strip_comments(_read(GLOBALS_CSS))
    promoted = (
        ".search-tab",
        ".search-category-section",
        ".folder-tab",
        ".header-browser-tab",
        ".research-explorer",
        ".file-explorer-pane",
    )
    missing = [
        s for s in promoted
        if not _appears_as_css_token(text, s)
    ]
    assert not missing, (
        f"PR 3c-iii MUST define every promoted surface from the "
        f"LATER_CHILD_SURFACES guard; missing: {missing!r}"
    )


def test_3c_iii_keeps_only_3c_iv_later_child_guards():
    """3c-iii.1 retention guard: after the 3c-iii promotion the only
    surfaces that MUST still be absent from globals.css are the 3c-iv
    deferred surfaces. The relaxed ``test_globals_css_does_not_pre_assert_later_child_surfaces``
    reference list now contains ONLY the 3c-iv surfaces, so this test
    verifies the expected bleed-prevention by re-running the same
    guard against the same ``LATER_CHILD_SURFACES`` constant the 3c-i
    + 3c-ii guards use. (Defense in depth: if a future edit re-adds a
    3c-iii surface to the deferred list, both this test and the 3c-i
    + 3c-ii guards stay green because they ALL inspect the same
    ``LATER_CHILD_SURFACES`` constant.)"""
    text = _strip_comments(_read(GLOBALS_CSS))
    leaked = [s for s in LATER_CHILD_SURFACES if _appears_as_css_token(text, s)]
    assert not leaked, (
        f"PR 3c-iii MUST NOT pre-define the remaining 3c-iv deferred "
        f"surfaces; leaked: {leaked!r}"
    )


@pytest.mark.parametrize("selector", ALL_3C_III_SELECTORS)
def test_3c_iii_selector_resolves_to_non_empty_declaration(selector):
    """3c-iii.1 — every canonical 3c-iii selector MUST resolve to a
    non-empty declaration block in ``src/app/globals.css``. The
    file-explorer chrome + snippet toolbar + CSV / JSON / truncated
    selectors all live inside their parent (``.search-tab`` or
    ``.research-explorer``) block per the 3c-iii.5 refactor
    contract (asserted separately). The block scan is
    whole-document (not scoped to a single ``@layer``) so descendant
    rules resolve through their parent block.

    NB the pattern accepts comma-separated selector lists (``.a, .b { ... }``)
    — the canonical CSS form for grouping sibling rules that share the same
    declaration block (e.g. ``.folder-tab-retry, .folder-tab-create``)."""
    text = _read(GLOBALS_CSS)
    # The selector either owns its own block (`<sel> { ... }`) OR is
    # part of a comma-separated selector list (`<sel>, <other> { ... }`).
    # The regex pattern below covers both shapes by accepting either
    # `<sel>\\s*\\{` (own block) or `<sel>,\\s*<other-selector>\\s*\\{`
    # (selector list).
    own_block = re.compile(
        r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"\s*\{[^}]*\S[^}]*\}"
    )
    list_item = re.compile(
        r"(?:^|[\s,{}>+~])" + re.escape(selector)
        + r"\s*,\s*[^{}]*?\{[^}]*\S[^}]*\}"
    )
    assert own_block.search(text) or list_item.search(text), (
        f"globals.css MUST declare {selector} with a non-empty block "
        f"(PR 3c-iii selector catalogue)"
    )


# ---- 3c-iii.2 — file-explorer chrome collapses into .research-explorer ----

@pytest.mark.parametrize("descendant", (
    *RESEARCH_EXPLORER_DESCENDANTS,
    *FEX_CHROME_SELECTORS,
    *SNIPPET_TOOLBAR_SELECTORS,
    *FEX_CSV_SELECTORS,
    *FEX_JSON_SELECTORS,
    *FEX_TRUNCATED_SELECTORS,
))
def test_3c_iii_file_explorer_chrome_collapses_into_research_explorer(descendant):
    """3c-iii.5 refactor contract: every file-explorer chrome selector
    (``fex-*`` / ``file-explorer-pane`` / ``file-viewer-pane`` /
    snippet toolbar / CSV scroller / JSON tree viewer / truncation
    banner) MUST live as a DESCENDANT of the ``.research-explorer``
    selector — NOT as its own top-level rule. The collapse pattern is
    ``.research-explorer <descendant>`` so the React ``<FileExplorer>``
    component in PR 5b can consume the CSS via a stable parent
    selector and so the cascade order matches the legacy inline-style
    block (the explorer chrome paints as a unit). CSS rules are
    siblings — the descendant rule is a SEPARATE ``{ ... }`` block from
    the parent rule, but its selector MUST start with
    ``.research-explorer`` so the cascade wires them together. The
    legacy ``test_research_styles.py`` uses the same pattern (descendant
    rule's selector text contains the parent selector + child selector
    as a concatenation — the React component consumes both via the
    stable parent selector name).

    NB the canonical CSS groups multiple descendants in a single
    comma-separated selector list (``<a>, <b>, <c> { ... }``) so the
    per-state chrome can share a single declaration block. The
    assertion accepts both own-block (``<sel> { ... }``) and
    selector-list (``<sel>, <other> { ... }``) shapes; the descendant
    MUST start the selector line after ``.research-explorer``."""
    text = _read(GLOBALS_CSS)
    assert re.search(
        r"(?:^|[\s,{}>+~])" + re.escape(RESEARCH_EXPLORER_PARENT)
        + r"\s*\{[^}]*\}",
        text,
    ), (
        f"globals.css MUST declare {RESEARCH_EXPLORER_PARENT} as a "
        f"top-level rule (PR 3c-iii parent contract)"
    )
    # The descendant selector may contain compound class lists
    # (``.fex-row.file.selected``), attribute selectors
    # (``[aria-pressed="true"]``), descendant chains
    # (``.fex-row .fex-chevron``), or interleaved attribute selectors
    # (``.fex-row.folder[data-realm] .fex-label``). Escape the
    # selector as-is so the ``[`` and ``]`` in attribute selectors
    # survive; ``re.escape`` quotes them so the regex still matches
    # the literal character class.
    head_escaped = re.escape(descendant).replace(re.escape("."), r"\.")
    # Selector must be followed by either:
    #   ``{`` (its own block), OR
    #   ``,`` followed by other selectors then ``{`` (selector list).
    pattern = (
        r"(?:^|[\s,{}>+~])" + re.escape(RESEARCH_EXPLORER_PARENT)
        + r"(?:\s+|\s*>\s*)" + head_escaped
        + r"(?:\s*\{|\s*,)"
    )
    assert re.search(pattern, text), (
        f"{descendant} MUST be a descendant rule of {RESEARCH_EXPLORER_PARENT} "
        f"(PR 3c-iii.5 refactor contract — collapse file-explorer chrome "
        f"into a single parent rule; the React <FileExplorer> consumes "
        f"the CSS via the stable parent selector name)"
    )


@pytest.mark.parametrize("descendant", SEARCH_TAB_DESCENDANTS)
def test_3c_iii_search_tab_collapses_descendants_into_single_rule(descendant):
    """3c-iii.5 refactor contract: every ``.search-tab`` descendant
    (``search-category-section`` + ``search-link-list`` + ``search-link``
    + ``search-link-label``) MUST live as a DESCENDANT of the
    ``.search-tab`` selector — NOT as its own top-level rule. The
    collapse pattern is ``.search-tab <descendant>`` so the React
    ``<SearchTab>`` + ``<SearchLinkList>`` components in PR 5b can
    consume the CSS via a stable parent selector and so the cascade
    order matches the legacy inline-style block.

    NB the canonical CSS groups ``.search-link`` + ``.search-link-label``
    in a single comma-separated selector list so the link chrome can
    share a single declaration block. The descendant selector MUST
    appear in the same rule selector chain as ``.search-tab``
    (possibly via intermediate descendants like
    ``.search-tab .search-link .search-link-label``)."""
    text = _read(GLOBALS_CSS)
    assert re.search(
        r"(?:^|[\s,{}>+~])" + re.escape(SEARCH_TAB_PARENT)
        + r"\s*\{[^}]*\}",
        text,
    ), (
        f"globals.css MUST declare {SEARCH_TAB_PARENT} as a top-level "
        f"rule (PR 3c-iii parent contract)"
    )
    desc_escaped = re.escape(descendant).replace(re.escape("."), r"\.")
    pattern = (
        r"(?:^|[\s,{}>+~])" + re.escape(SEARCH_TAB_PARENT)
        + r"[^,{]*" + desc_escaped
        + r"(?:\s*\{|\s*,)"
    )
    assert re.search(pattern, text), (
        f"{descendant} MUST be a descendant rule of {SEARCH_TAB_PARENT} "
        f"(PR 3c-iii.5 refactor contract — collapse search-tab chrome "
        f"into a single parent rule; the React <SearchTab> consumes "
        f"the CSS via the stable parent selector name)"
    )


# ---- 3c-iii.3 — search-clear visibility invariant ------------------------------

def test_3c_iii_search_clear_visibility_uses_placeholder_shown_sibling():
    """3c-iii.3 — the legacy ``.fex-search-clear`` visibility rule
    ``.fex-search-input:not(:placeholder-shown) ~ .fex-search-clear``
    MUST survive the migration verbatim (the React ``<FileExplorer>``
    input carries no controlled-value wiring — the rule paints the
    clear glyph ONLY when the input has a non-empty value, matching
    the legacy inline-style behaviour). The clear glyph stays hidden
    in the placeholder-only state and shows once the user starts
    typing."""
    text = _strip_comments(_read(GLOBALS_CSS))
    pattern = (
        r"\.fex-search-input:not\(\s*:placeholder-shown\s*\)\s*~\s*"
        r"\.fex-search-clear\s*\{[^}]*\S[^}]*\}"
    )
    assert re.search(pattern, text), (
        "globals.css MUST declare the .fex-search-input:not(:placeholder-shown) "
        "~ .fex-search-clear visibility rule verbatim (PR 3c-iii.3 "
        "search-clear visibility state invariant — the clear glyph "
        "must stay hidden when the input is empty and appear once the "
        "user types)"
    )


def test_3c_iii_search_clear_default_is_hidden_and_hover_reveals():
    """3c-iii.3 — ``.fex-search-clear`` MUST default to ``display: none``
    (so the placeholder-only state hides the glyph) and the hover
    state MUST have its own non-empty declaration so the clear button
    paints an interactive affordance on hover (the React presenter
    uses this as the affordance the user clicks to reset the search
    query)."""
    text = _read(GLOBALS_CSS)
    # The default .fex-search-clear { ... display: none; ... } rule.
    default_rule = re.search(
        r"\.fex-search-clear\s*\{[^}]*display\s*:\s*none[^}]*\}",
        text,
    )
    assert default_rule, (
        ".fex-search-clear MUST default to display: none (PR 3c-iii.3 "
        "search-clear default-hidden invariant — the React presenter "
        "relies on the :not(:placeholder-shown) sibling rule to "
        "reveal it)"
    )
    # The :hover variant (any non-empty declaration that includes a
    # background or opacity tweak; assertion is loose to allow any
    # legacy hover affordance the React presenter doesn't depend on).
    assert re.search(r"\.fex-search-clear:hover\s*\{[^}]*\S[^}]*\}", text), (
        ".fex-search-clear:hover MUST carry a non-empty declaration "
        "(PR 3c-iii.3 hover affordance)"
    )


# ---- 3c-iii.4 — search-mode aria-pressed state invariant ---------------------

def test_3c_iii_search_toggle_aria_pressed_state_has_non_empty_declaration():
    """3c-iii.4 — the ``[aria-pressed="true"]`` state selectors on the
    two search toggles (``fex-search-mode-btn`` + ``fex-search-hide-empty-btn``)
    MUST resolve to non-empty declarations so the active toggle stays
    visually distinct from the inactive one (the React
    ``<FileExplorer>`` toggles stamp ``aria-pressed="true"`` on the
    active button — without the state selector the toggle chrome is
    indistinguishable). NB the canonical CSS groups both
    ``aria-pressed="true"`` toggles in a single comma-separated block
    (``<mode>[aria-pressed="true"], <hide-empty>[aria-pressed="true"] { ... }``)
    to keep the active-state chrome consistent across the toggle pair;
    the assertion accepts both own-block and selector-list shapes."""
    text = _read(GLOBALS_CSS)
    for selector in (
        '.fex-search-mode-btn[aria-pressed="true"]',
        '.fex-search-hide-empty-btn[aria-pressed="true"]',
    ):
        own_block = re.compile(
            r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"\s*\{[^}]*\S[^}]*\}"
        )
        list_item = re.compile(
            r"(?:^|[\s,{}>+~])" + re.escape(selector)
            + r"\s*,\s*[^{}]*?\{[^}]*\S[^}]*\}"
        )
        assert own_block.search(text) or list_item.search(text), (
            f"globals.css MUST declare {selector} with a non-empty "
            f"block (PR 3c-iii.4 search-toggle aria-pressed state "
            f"invariant — the active toggle must read visually distinct)"
        )


# ---- 3c-iii.5 — splitter hover / dragging state invariant --------------------

def test_3c_iii_splitter_hover_and_dragging_states_have_non_empty_declaration():
    """3c-iii.5 — the file-explorer splitter MUST carry non-empty
    ``:hover`` + ``.dragging`` state declarations so the splitter
    chrome reads as interactive on hover and paints a drag indicator
    while the user resizes the panes. The legacy ``.fex-splitter``
    uses a ``::after`` pseudo-element for the drag handle; both the
    base + pseudo + hover + dragging variants MUST resolve to
    non-empty declarations so the React ``<FileExplorer>``'s
    splitter chrome stays consistent with the legacy inline-style
    block."""
    text = _read(GLOBALS_CSS)
    for selector in (
        ".fex-splitter",
        ".fex-splitter::after",
        ".fex-splitter:hover",
        ".fex-splitter.dragging",
    ):
        assert re.search(
            r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"\s*\{[^}]*\S[^}]*\}",
            text,
        ), (
            f"globals.css MUST declare {selector} with a non-empty "
            f"block (PR 3c-iii.5 splitter state invariant — the "
            f"splitter chrome + drag handle + hover + dragging states "
            f"all must paint)"
        )


# ---- 3c-iii.6 — realm-tinted fex-row.folder variants -------------------------

def test_3c_iii_declares_default_realm_other_folder_chrome():
    """3c-iii.6 — the catch-all ``.fex-row.folder[data-realm]``
    selectors for the icon + label MUST reference ``var(--realm-other)``
    so the default folder tint matches the realm hue (the per-realm
    overrides ride on top)."""
    text = _read(GLOBALS_CSS)
    missing = []
    for selector in (
        ".fex-row.folder[data-realm] .fex-icon",
        ".fex-row.folder[data-realm] .fex-label",
    ):
        pattern = (
            re.escape(selector) + r"\s*\{[^}]*var\s*\(\s*--realm-other\s*\)[^}]*\}"
        )
        if not re.search(pattern, text):
            missing.append(selector)
    assert not missing, (
        f"@layer components MUST declare the catch-all folder-tint "
        f"selectors with var(--realm-other); missing: {missing!r}"
    )


@pytest.mark.parametrize("realm,token_name", REALM_FOLDER_PAIRS)
def test_3c_iii_realm_tinted_folder_chrome_uses_realm_token(realm, token_name):
    """3c-iii.6 — each ``.fex-row.folder[data-realm="<realm>"]``
    selector (icon + label) MUST reference ``var(--realm-<realm>)``
    verbatim — the realm hue round-trips through the ``--realm-*``
    family shipped by 3c-i.1. ``other`` is intentionally absent —
    the catch-all rule already covers the default tint (asserted
    separately above)."""
    text = _read(GLOBALS_CSS)
    missing = []
    for selector in (
        f'.fex-row.folder[data-realm="{realm}"] .fex-icon',
        f'.fex-row.folder[data-realm="{realm}"] .fex-label',
    ):
        pattern = (
            re.escape(selector) + r"\s*\{[^}]*var\s*\(\s*--"
            + re.escape(token_name) + r"\s*\)[^}]*\}"
        )
        if not re.search(pattern, text):
            missing.append(selector)
    assert not missing, (
        f"@layer components MUST declare every realm-tinted "
        f"folder-chrome selector with var(--realm-<realm>); "
        f"missing: {missing!r}"
    )


# ---- 3c-iii.7 — color-mix relaxation scoped to legacy 3c-iii calls -----------

def test_3c_iii_uses_color_mix_for_legacy_calls():
    """3c-iii.7 — the file-explorer chrome relies on ``color-mix()``
    calls for the focus / hover / drag-state alpha mixing the legacy
    inline-style block uses (``.fex-search-input:focus`` +
    ``.fex-splitter:hover`` + ``.fex-splitter.dragging`` etc.).
    PR 3c-iii MUST carry at least one ``color-mix(in srgb, ...,
    transparent)`` call so the foundation slice (PR 3c-i) and the
    taxonomy slice (PR 3c-ii) stay color-mix-free while the
    3c-iii slice carries the legacy alpha mixing the cascade
    depends on."""
    text = _strip_comments(_read(GLOBALS_CSS))
    # Match either the full ``color-mix(in srgb, ..., transparent)``
    # shape the legacy inline-style block uses, or the bare
    # ``color-mix(`` opener (the legacy calls all use the ``in srgb``
    # interpolation method, but the assertion is intentionally loose
    # so a future 3c-iii refactor that swaps the interpolation method
    # doesn't false-positive).
    assert re.search(r"color-mix\s*\(", text), (
        "globals.css MUST carry at least one color-mix() call (PR "
        "3c-iii.7 — file-explorer chrome focus / hover / drag-state "
        "alpha mixing; the relaxation from PR 3c-i / 3c-ii's "
        "no-color-mix guard is explicit and scoped to the 3c-iii "
        "file-explorer chrome)"
    )


def test_3c_iii_color_mix_is_legacy_in_srgb_shape():
    """3c-iii.7 — every ``color-mix()`` call in the 3c-iii slice MUST
    use the legacy ``in srgb`` interpolation method (the legacy
    inline-style block uniformly uses ``color-mix(in srgb,
    var(--token) NN%, transparent)``). A future refactor that swaps
    to ``in oklab`` would silently drift the focus / hover alpha in
    dark mode; the assertion pins the legacy shape verbatim."""
    text = _strip_comments(_read(GLOBALS_CSS))
    # Capture the interpolation method — the canonical shape is
    # ``color-mix(in srgb, ...)`` so the regex matches ``in`` followed
    # by an interpolation-method identifier (``srgb`` / ``oklab`` /
    # ``oklch`` / ``display-p3`` etc.) before the comma. Drift
    # detection pins ``srgb`` so a future refactor that swaps the
    # interpolation method to ``oklab`` (or any other colour space)
    # trips the guard.
    matches = list(re.finditer(
        r"color-mix\s*\(\s*in\s+([a-zA-Z][\w-]*)\s*,", text,
    ))
    assert matches, (
        "PR 3c-iii MUST use color-mix() calls (asserted separately); "
        "this test pins the interpolation method"
    )
    bad = [m.group(1) for m in matches if m.group(1) != "srgb"]
    assert not bad, (
        f"every color-mix() call MUST use the legacy `in srgb` "
        f"interpolation method; drifted methods: {bad!r}"
    )


# ---- 3c-iii.8 — slice-scope guards: 3c-iv MUST NOT bleed in -----------------

def test_3c_iii_does_not_pre_assert_3c_iv_surfaces():
    """3c-iii.8 — PR 3c-iii MUST NOT pre-define any surface owned by
    3c-iv (animations / utility classes + final CSS parity). The
    ``LATER_CHILD_SURFACES`` constant now contains ONLY the 3c-iv
    deferred surfaces (the 3c-iii surfaces were promoted out in this
    PR). Re-running the same guard against the relaxed constant
    double-checks the per-PR review focus stays clean across the
    sub-sequence."""
    text = _strip_comments(_read(GLOBALS_CSS))
    leaked = [s for s in LATER_CHILD_SURFACES if _appears_as_css_token(text, s)]
    assert not leaked, (
        f"PR 3c-iii MUST NOT pre-define surfaces reserved for 3c-iv; "
        f"leaked: {leaked!r}"
    )


def test_3c_iii_no_keyframes_anywhere():
    """3c-iii.8 — PR 3c-iii MUST NOT introduce any ``@keyframes``
    rule — the animation surface (``@keyframes spin`` +
    ``@keyframes detail-card-enter`` + ``@keyframes detail-card-leave``
    + ``@keyframes search-pulse-anim`` + ``@keyframes toast-slide-in``)
    lands with PR 3c-iv per the design. A 3c-iii ``@keyframes`` rule
    would silently drift the animation cascade against the
    3c-iv planned surface."""
    text = _strip_comments(_read(GLOBALS_CSS))
    assert not re.search(r"@keyframes\s+", text), (
        "globals.css MUST NOT carry any @keyframes rule in PR 3c-iii — "
        "those land with PR 3c-iv (animations / utility classes + "
        "final CSS parity)"
    )


def test_3c_iii_no_3c_iv_utility_class_top_level_rules():
    """3c-iii.8 — PR 3c-iii MUST NOT introduce top-level rules for
    the 3c-iv utility-class surface (``.animate-spin``,
    ``.bg-primary``, ``.bg-primary-fixed``, ``.text-on-primary-fixed``,
    ``.bg-surface-container-lowest``, ``.shadow-sm``, ``.rounded-r-md``,
    ``.border-outline-variant``). Those land with PR 3c-iv per the
    design; pre-asserting them in 3c-iii would silently reserve the
    namespace and block the per-PR review focus on the utility-class
    slice. (PR 3c-iv is the design-system barrel + utility-class
    surface that owns those rules.)"""
    text = _strip_comments(_read(GLOBALS_CSS))
    leaked = [
        s for s in (
            ".animate-spin", ".bg-primary", ".bg-primary-fixed",
            ".text-on-primary-fixed", ".bg-surface-container-lowest",
            ".shadow-sm", ".rounded-r-md", ".border-outline-variant",
        )
        if re.search(r"(?:^|[\s,{}>+~])" + re.escape(s) + r"\s*\{", text)
    ]
    assert not leaked, (
        f"PR 3c-iii MUST NOT introduce top-level utility-class rules; "
        f"leaked: {leaked!r} — those land with PR 3c-iv"
    )


# ---- 3c-iii.9 — triangulation: color-mix scoping + realm integrity ---------

def test_3c_iii_color_mix_is_scoped_to_3c_iii_selectors():
    """3c-iii.9 — triangulation guard: every ``color-mix()`` call MUST
    appear inside a ``.research-explorer`` descendant rule (the only
    3c-iii surface that carries focus / hover / drag-state alpha mixing).
    A ``color-mix()`` call outside the ``.research-explorer`` selector
    would indicate drift — either into a 3c-iv surface (the
    3c-iv utility-class surface owns the relaxed colour-mix usage)
    or into a 3c-i / 3c-ii surface (which the foundation slice guard
    forbids). The 3c-iii scoping is the explicit relaxation the design
    authorised."""
    text = _strip_comments(_read(GLOBALS_CSS))
    # Find every color-mix call + the selector of the surrounding rule.
    # Pattern: back up from the color-mix call to the nearest ``{`` that
    # closes the selector of the enclosing rule.
    call_positions = [m.start() for m in re.finditer(r"color-mix\s*\(", text)]
    assert call_positions, (
        "PR 3c-iii MUST use color-mix() calls (asserted separately); "
        "this test pins the scoping"
    )
    bad = []
    for pos in call_positions:
        # Walk backwards from the call to find the preceding ``}`` (or
        # start of file); the text between that boundary and the next
        # ``{`` is the rule selector. Require it to start with
        # ``.research-explorer`` (the only 3c-iii surface that carries
        # colour-mix).
        preceding_end = pos
        cursor = pos - 1
        while cursor >= 0 and text[cursor] != "}":
            cursor -= 1
        selector_chunk = text[cursor + 1:pos].strip()
        # Pull just the first selector of the chunk (everything before
        # the first comma or whitespace-newline run that isn't part of
        # a selector combinator).
        first_sel = re.split(r"\s*,\s*", selector_chunk, maxsplit=1)[0].strip()
        if not first_sel.startswith(".research-explorer"):
            bad.append((pos, first_sel))
    assert not bad, (
        f"every color-mix() call MUST appear inside a .research-explorer "
        f"descendant rule (3c-iii.9 scoping invariant); drifted selectors: "
        f"{bad!r}"
    )


def test_3c_iii_realm_folder_tint_uses_var_realm_family_verbatim():
    """3c-iii.9 — triangulation guard: the realm folder tint rules MUST
    reference ``var(--realm-<realm>)`` verbatim — never literal hex
    values that would drift the realm palette away from the 3c-i
    ``--realm-*`` family. The seven ``other`` realms
    (``bacteria`` / ``archaea`` / ``viruses`` / ``animalia`` / ``fungi`` /
    ``plantae`` / ``chromista``) carry per-realm overrides; ``other`` is
    the catch-all default that lands in the ``[data-realm]`` selector."""
    text = _read(GLOBALS_CSS)
    # The seven per-realm overrides MUST round-trip via var(--realm-*).
    bad = []
    for realm in ("bacteria", "archaea", "viruses", "animalia",
                  "fungi", "plantae", "chromista"):
        # Pattern: ``.fex-row.folder[data-realm="<realm>"]`` (possibly
        # followed by a descendant like ``.fex-icon``) opens a rule
        # whose body references ``var(--realm-<realm>)`` — the realm
        # hue round-trip.
        selector = f'.fex-row.folder[data-realm="{realm}"]'
        pattern = (
            re.escape(selector)
            + r"(?:[^,{]*?)"
            + r"\{[^}]*var\s*\(\s*--realm-" + re.escape(realm)
            + r"\s*\)[^}]*\}"
        )
        if not re.search(pattern, text):
            bad.append(realm)
    assert not bad, (
        f"every realm-tinted .fex-row.folder[data-realm=\"<realm>\"] rule "
        f"MUST reference var(--realm-<realm>) verbatim (3c-iii.9 realm "
        f"integrity); drifted realms: {bad!r}"
    )
