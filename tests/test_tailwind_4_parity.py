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
# Legacy ``web/index.html`` (retired in PR #171, read-only). The
# canonical Settings view block lives at lines 1833-1969 (the legacy
# inline <style> block inside the @layer base wrapper). The settings
# slice reads the legacy selectors as a hardcoded catalogue (the
# existing 3c-iv-viewer slice pattern) so the test does NOT depend on
# the file being checked out in the worktree; the constant stays here
# for documentation + a future sanity-check helper.
WEB_INDEX_HTML = REPO_ROOT / "web" / "index.html"


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
    # 3c-iv — animations / utilities / final parity. PR 3c-iv-keyframes
    # (position 7/22) ships the five legacy @keyframes + the .animate-spin
    # utility; those are now LIVE and were removed from this guard so the
    # deferred list still reflects what is NOT yet shipped. The viewer /
    # settings / colors surfaces (.bg-primary / .bg-primary-fixed /
    # .text-on-primary-fixed / .bg-surface-container-lowest / .shadow-sm /
    # .rounded-r-md / .border-outline-variant) stay deferred — PR 3c-iv
    # was replanned into five slices and each surface still has its own
    # downstream PR.
    ".bg-primary", ".bg-primary-fixed",
    ".text-on-primary-fixed", ".bg-surface-container-lowest",
    ".shadow-sm", ".rounded-r-md", ".border-outline-variant",
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
    # kebab item variants (the React <Kebab> emits
    # .kebab-item + .kebab-item-label — both live). The legacy
    # .kebab-trigger className was DEAD code per PR 5.6 (React
    # <Kebab> stamps data-action="toggle-kebab" instead of a
    # className); the .kebab trigger bridge is asserted via the
    # new PR 5.6.1 ``.kebab > button[data-action="toggle-kebab"]``
    # selector.
    ".kebab-item", ".kebab-item-label",
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
# NOTE (PR 5.6): the taxonomy ``.tree-row[data-realm="..."]``
# realm-tinted selectors were DEAD code per PR 5.6 (the React
# ``<Tree>`` does not stamp ``data-realm`` on taxonomy rows; only the
# React ``<FileExplorer>`` stamps ``data-realm`` on
# ``.fex-row.folder`` rows inside the ``.research-explorer`` parent).
# The three tests below were REPURPOSED in PR 5.6 to assert the
# dead-code ABSENCE (the legacy realm-tinted rules are removed from
# the source CSS as part of the safe resolution). The LIVE
# realm-tinted selectors stay asserted via the 3c-iii.6 + 3c-iii.9
# ``.fex-row.folder[data-realm]`` tests lower in this file.

def test_globals_css_declares_default_realm_other_scientific_name():
    """PR 5.6 repurpose — the legacy
    ``.tree-row[data-realm] .scientific-name { color: var(--realm-other); }``
    selector was DEAD code (the React ``<Tree>`` does not stamp
    ``data-realm`` on taxonomy rows). PR 5.6 resolves it safely by
    REMOVING it from the source CSS. This test now asserts the
    dead-code absence — the rule MUST NOT appear anywhere in
    ``src/app/globals.css`` post-5.6. The LIVE realm-tinted default
    (``.fex-row.folder[data-realm] .fex-icon`` + ``.fex-label``) is
    asserted separately in 3c-iii.6."""
    text = _strip_comments(_read(GLOBALS_CSS))
    assert not re.search(
        r"\.tree-row\[data-realm\]\s+\.scientific-name\s*\{",
        text,
    ), (
        "PR 5.6 MUST NOT carry the dead .tree-row[data-realm] "
        ".scientific-name default-tint rule (React <Tree> does not "
        "stamp data-realm on taxonomy rows; resolved safely in PR 5.6)"
    )


def test_realm_tinted_scientific_name_uses_realm_token():
    """PR 5.6 repurpose — the per-realm
    ``.tree-row[data-realm="<realm>"] .scientific-name`` overrides
    were DEAD code (no React component stamps ``data-realm`` on
    taxonomy rows). PR 5.6 resolves them safely by REMOVING them
    from the source CSS. This test now asserts the dead-code
    absence for every realm — none of the seven per-realm override
    rules MAY appear anywhere in ``src/app/globals.css`` post-5.6.
    The LIVE per-realm tints ride on the
    ``.fex-row.folder[data-realm="<realm>"]`` selectors inside the
    ``.research-explorer`` parent (asserted separately in
    ``test_3c_iii_realm_tinted_folder_chrome_uses_realm_token``)."""
    text = _strip_comments(_read(GLOBALS_CSS))
    leaked = []
    for realm, _ in REALM_TAXONOMY_PAIRS:
        selector = f'.tree-row[data-realm="{realm}"] .scientific-name'
        if re.search(re.escape(selector) + r"\s*\{", text):
            leaked.append(realm)
    assert not leaked, (
        f"PR 5.6 MUST NOT carry the dead .tree-row[data-realm=\"<realm>\"] "
        f".scientific-name per-realm overrides (React <Tree> does not "
        f"stamp data-realm on taxonomy rows); leaked realms: {leaked!r}"
    )


def test_realm_selected_focused_scientific_name_uses_primary_token():
    """PR 5.6 repurpose — the legacy
    ``.tree-row.selected .scientific-name, .tree-row.focused
    .scientific-name { color: var(--primary); }`` override was DEAD
    code (the React ``<Tree>`` stamps ``data-selected`` instead of
    a ``.selected`` className on the active row). PR 5.6 resolves
    it safely by REMOVING it from the source CSS. This test now
    asserts the dead-code absence. The LIVE selected-row state is
    asserted via the new ``.tree-row[data-selected="true"]`` rule
    in PR 5.6 (asserted in ``test_5_6_tree_row_data_selected_true_has_visible_state_change``)."""
    text = _strip_comments(_read(GLOBALS_CSS))
    assert not re.search(
        r"\.tree-row\.selected\s+\.scientific-name\s*,\s*"
        r"\.tree-row\.focused\s+\.scientific-name\s*\{",
        text,
    ), (
        "PR 5.6 MUST NOT carry the dead .tree-row.selected "
        ".scientific-name, .tree-row.focused .scientific-name override "
        "(React <Tree> stamps data-selected instead of .selected "
        "className; resolved safely in PR 5.6)"
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
    3c-iv planned surface.

    NB the guard is scoped to the 3c-iii slice window (positions
    4–5/22). PR 3c-iv-keyframes (position 7/22) was authorised to
    ship the five legacy animation rules verbatim; the now-live
    keyframes are asserted by ``test_3c_iv_keyframes_resolves_with_legacy_signature``
    + ``test_3c_iv_keyframes_appear_after_layer_base_closing_brace``
    lower in this file. The guard intent — "no keyframes during the
    3c-iii slice window" — is preserved by pinning the slice-window
    marker (the assertions below still trip if a future PR adds
    keyframes BEFORE the 3c-iv-keyframes slice lands)."""
    # The 3c-iii slice is closed; the assertion is retained as a
    # defensive guard so a future edit that adds an EXTRA keyframe
    # (beyond the 3c-iv-keyframes catalogue) trips the review focus.
    text = _strip_comments(_read(GLOBALS_CSS))
    live_keyframes = {
        # PR 3c-iv-keyframes — five legacy animation rules (LIVE).
        "@keyframes detail-card-enter", "@keyframes detail-card-leave",
        "@keyframes search-pulse-anim", "@keyframes materialize-spin",
        "@keyframes toast-slide-in",
    }
    declared = set(re.findall(r"@keyframes\s+[\w-]+", text))
    drifted = declared - live_keyframes
    assert not drifted, (
        "PR 3c-iii MUST NOT introduce keyframes beyond the "
        "PR 3c-iv-keyframes catalogue; drifted: "
        f"{sorted(drifted)!r} — only the five legacy rules listed "
        "in the catalogue are authorised to ship in the 3c-iv slice"
    )


def test_3c_iii_no_3c_iv_utility_class_top_level_rules():
    """3c-iii.8 — PR 3c-iii MUST NOT introduce top-level rules for
    the 3c-iv utility-class surface (``@keyframes spin`` +
    ``.bg-primary``, ``.bg-primary-fixed``, ``.text-on-primary-fixed``,
    ``.bg-surface-container-lowest``, ``.shadow-sm``, ``.rounded-r-md``,
    ``.border-outline-variant``). Those land with PR 3c-iv per the
    design; pre-asserting them in 3c-iii would silently reserve the
    namespace and block the per-PR review focus on the utility-class
    slice. (PR 3c-iv is the design-system barrel + utility-class
    surface that owns those rules.)

    NB ``.animate-spin`` was promoted out of this guard in PR
    3c-iv-keyframes (position 7/22) when the materialize-spin
    utility class landed. The remaining seven surfaces still belong
    to PR 3c-iv-colors (10/22) and stay deferred."""
    text = _strip_comments(_read(GLOBALS_CSS))
    leaked = [
        s for s in (
            ".bg-primary", ".bg-primary-fixed",
            ".text-on-primary-fixed", ".bg-surface-container-lowest",
            ".shadow-sm", ".rounded-r-md", ".border-outline-variant",
        )
        if re.search(r"(?:^|[\s,{}>+~])" + re.escape(s) + r"\s*\{", text)
    ]
    assert not leaked, (
        f"PR 3c-iii MUST NOT introduce top-level utility-class rules; "
        f"leaked: {leaked!r} — those land with PR 3c-iv-colors"
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


# ==============================================================================
# PR 5.6 — DOM↔CSS structural parity repair (position 5.6/18)
# ==============================================================================
# The React-emitted taxonomy / detail hooks landed via PR 5a + 5b but the
# CSS-only repair for the structural selectors (.taxa-tree / .tree-row /
# .tab-strip / .tab-button / .overview-tab / .breadcrumb /
# .breadcrumb-segment / .breadcrumb-link / .detail-body / .detail-close /
# .species-count / .authorship / .materialize-indicator + the kebab
# selector bridge .kebab > button[data-action="toggle-kebab"]) was deferred
# until the cascade + base + research chrome slices were stable.
#
# PR 5.6 ships the CSS-only repair under ``@layer components`` so the
# React-emitted hooks paint as visibly structural + interactive (the
# @layer base slice carries the legacy inline-style cascade, but the
# bare React-component CSS lives in @layer components per the 3c-b +
# 3c-c refactor contract). The dead ``.tree-row[data-realm="..."]``
# realm-tinted selectors are resolved safely (the React ``<Tree>``
# does not stamp ``data-realm`` on taxonomy rows — those selectors
# cannot match today's DOM and are deleted as part of the repair).
#
# The .kebab > button[data-action="toggle-kebab"] selector bridge is
# the CSS-only contract for the React <Kebab> trigger (PR 5a.4
# emitted ``data-action="toggle-kebab"`` so the existing e2e harness
# + the kebab menu open/close flow keep working — the CSS rides the
# new descendant selector so the legacy ``.kebab-trigger`` className
# (no longer emitted) is retired cleanly).

# ---- 5.6 catalogue ----------------------------------------------------------

# React-emitted structural hooks that the CSS-only repair binds. Each
# entry MUST resolve to a non-empty declaration block under
# ``@layer components`` (the React-component CSS layer). The
# kebab selector bridge (.kebab > button[data-action="toggle-kebab"])
# is the selector that consumes the React <Kebab> trigger; the bare
# ``.kebab { ... }`` + ``.kebab-menu { ... }`` base selectors stay
# under @layer components per OpenSpec 3c-ii.5.
PR_5_6_REACT_HOOKS: tuple[str, ...] = (
    # taxonomy tree
    ".taxa-tree",
    ".tree-row",
    ".tree-search-icon",
    # detail panel
    ".detail-panel",
    ".detail-body",
    ".detail-close",
    # tab strip (collapsed .tab-strip > .tab-button descendant rule)
    ".tab-strip",
    ".tab-button",
    # overview content
    ".overview-tab",
    # breadcrumb
    ".breadcrumb",
    ".breadcrumb-segment",
    ".breadcrumb-link",
    # content text
    ".species-count",
    ".authorship",
    ".materialize-indicator",
)

# The bare ``.scientific-name`` selector is emitted by the React
# <Tree> / <Breadcrumb> / <OverviewTab> components as the
# italic-flavoured scientific-name span. PR 5.6 moves the base rule
# from @layer base into @layer components so the React component CSS
# layer owns the emitted hook (the ``.scientific-name--roman``
# modifier stays in @layer base per the prior 3c-ii contract; it
# wins via specificity regardless of layer).
PR_5_6_SCIENTIFIC_NAME_HOOKS: tuple[str, ...] = (
    ".scientific-name",
    ".scientific-name--roman",
)

# State selectors the React components emit and the CSS-only repair
# must visibly resolve. Each one corresponds to a React-emitted
# data-attribute or className-driven state.
PR_5_6_STATE_SELECTORS: tuple[str, ...] = (
    ".tree-row[data-selected=\"true\"]",
    ".tree-row:hover",
    ".tree-row:focus-visible",
    # tab strip collapsed descendant
    ".tab-strip > .tab-button",
    ".tab-strip > .tab-button.active",
    ".tab-strip > .tab-button:hover",
    ".tab-strip > .tab-button:focus-visible",
    # kebab base collapsed descendant
    ".kebab > .kebab-menu",
    # kebab selector bridge for the React <Kebab> trigger
    ".kebab > button[data-action=\"toggle-kebab\"]",
)

# ---- 5.6.1 — every React hook resolves under @layer components -------------

@pytest.mark.parametrize("selector", PR_5_6_REACT_HOOKS)
def test_5_6_react_hook_resolves_under_layer_components(selector):
    """5.6.1 — every React-emitted structural hook MUST resolve to a
    non-empty declaration block under ``@layer components``. The
    bare ``.scientific-name`` / ``.scientific-name--roman`` rules
    land here too (moved from @layer base in PR 5.6; the React
    component CSS layer owns the emitted hook). The CSS-only
    repair binds these hooks so the React-emitted taxonomy /
    detail DOM paints as visibly structural + interactive."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... } block"
    own_block = re.compile(
        r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"\s*\{[^}]*\S[^}]*\}"
    )
    assert own_block.search(body), (
        f"@layer components MUST declare {selector} with a non-empty "
        f"block (PR 5.6 React-emitted hook catalogue)"
    )


@pytest.mark.parametrize("selector", PR_5_6_SCIENTIFIC_NAME_HOOKS)
def test_5_6_scientific_name_resolves_under_layer_components(selector):
    """5.6.1 — the bare ``.scientific-name`` + ``.scientific-name--roman``
    rules live under ``@layer components`` (moved from @layer base in
    PR 5.6). The React component CSS layer owns the emitted hook; the
    ``.scientific-name--roman`` modifier wins over the bare rule via
    specificity regardless of layer."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... } block"
    own_block = re.compile(
        r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"\s*\{[^}]*\S[^}]*\}"
    )
    assert own_block.search(body), (
        f"@layer components MUST declare {selector} with a non-empty "
        f"block (PR 5.6 scientific-name hook relocated from @layer base)"
    )


@pytest.mark.parametrize("selector", PR_5_6_STATE_SELECTORS)
def test_5_6_state_selector_resolves_under_layer_components(selector):
    """5.6.1 — every React-emitted state selector (data-selected +
    :hover + :focus-visible + the kebab selector bridge + the tab-strip
    collapsed descendant) MUST resolve to a non-empty declaration
    block under ``@layer components``. The state selectors are the
    interactive surface of the CSS-only repair: visible selection
    feedback on the active tree row, hover/focus affordances on the
    tab buttons, and the kebab trigger bridge that the React <Kebab>
    ``data-action="toggle-kebab"`` button consumes."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... } block"
    own_block = re.compile(
        r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"\s*\{[^}]*\S[^}]*\}"
    )
    assert own_block.search(body), (
        f"@layer components MUST declare {selector} with a non-empty "
        f"block (PR 5.6 state selector catalogue)"
    )


# ---- 5.6.2 — taxonomic realm dead-selector resolution ----------------------

def test_5_6_taxonomic_realm_rules_are_resolved_safely():
    """5.6.2 — the ``.tree-row[data-realm="..."]`` realm-tinted
    selectors in @layer base cannot match today's DOM (the React
    ``<Tree>`` does not stamp ``data-realm`` on taxonomy rows; only
    the React ``<FileExplorer>`` stamps ``data-realm`` on
    ``.fex-row.folder`` rows). PR 5.6 resolves the dead selectors
    safely by REMOVING them from the source CSS — leaving them in
    the cascade would have leaked forward-looking code into a
    surface that no React component consumes today, and the
    ``.tree-row[data-realm] .scientific-name`` selector text
    collides with the React-emitted ``.scientific-name`` hook
    (which moves to @layer components in PR 5.6.1).

    NB the LIVE realm-tinted selectors ``.fex-row.folder[data-realm="..."]``
    stay in @layer components inside the ``.research-explorer``
    parent rule — the React <FileExplorer> consumes them via the
    stable parent selector. Only the TAXONOMY ``.tree-row[data-realm]``
    rules are resolved (asserted below)."""
    text = _strip_comments(_read(GLOBALS_CSS))
    # The default ``.tree-row[data-realm] .scientific-name`` selector.
    dead_default = re.search(
        r"\.tree-row\[data-realm\]\s+\.scientific-name\s*\{[^}]*"
        r"var\s*\(\s*--realm-other\s*\)[^}]*\}",
        text,
    )
    assert dead_default is None, (
        "PR 5.6 MUST resolve the .tree-row[data-realm] .scientific-name "
        "default-tint rule safely (the React <Tree> does not stamp "
        "data-realm on taxonomy rows; this selector cannot match "
        "today's DOM and is dead code per PR 5.6)"
    )
    # Each per-realm override ``.tree-row[data-realm=\"<realm>\"] .scientific-name``.
    for realm in (
        "bacteria", "archaea", "viruses", "animalia", "fungi",
        "plantae", "chromista",
    ):
        dead = re.search(
            re.escape(f'.tree-row[data-realm="{realm}"] .scientific-name')
            + r"\s*\{[^}]*\S[^}]*\}",
            text,
        )
        assert dead is None, (
            f"PR 5.6 MUST resolve the dead .tree-row[data-realm=\"{realm}\"] "
            f".scientific-name per-realm tint rule (cannot match today's DOM; "
            f"the React <Tree> does not stamp data-realm on taxonomy rows)"
        )
    # The selected/focused override ``.tree-row.selected .scientific-name,
    # .tree-row.focused .scientific-name`` — also dead (React emits
    # ``data-selected`` instead of a ``.selected`` className).
    dead_selected = re.search(
        r"\.tree-row\.selected\s+\.scientific-name\s*,\s*"
        r"\.tree-row\.focused\s+\.scientific-name\s*\{",
        text,
    )
    assert dead_selected is None, (
        "PR 5.6 MUST resolve the dead .tree-row.selected .scientific-name, "
        ".tree-row.focused .scientific-name override rule (React emits "
        "data-selected=\"true\" instead of a .selected className; the legacy "
        "selected/focused selector cannot match today's DOM)"
    )


def test_5_6_kebab_trigger_classname_is_resolved_safely():
    """5.6.2 — the ``.kebab-trigger`` className + the
    ``.tree-row:hover/selected/focus-within .kebab-trigger`` rules
    in @layer base cannot match today's DOM (the React <Kebab>
    component stamps ``data-action="toggle-kebab"`` on the trigger
    button — it does NOT stamp a ``.kebab-trigger`` className).
    PR 5.6 resolves the dead className + the dead descendant
    selectors safely by REMOVING them from the source CSS — the
    new ``.kebab > button[data-action="toggle-kebab"]`` selector
    bridge (asserted separately above) is the CSS-only contract
    for the React <Kebab> trigger."""
    text = _strip_comments(_read(GLOBALS_CSS))
    # Bare ``.kebab-trigger { ... }`` base rule — the className is
    # not emitted by any React component.
    assert not re.search(
        r"(?:^|[\s,{}>+~])\.kebab-trigger\s*\{", text,
    ), (
        "PR 5.6 MUST resolve the dead .kebab-trigger className rule safely "
        "(React <Kebab> stamps data-action=\"toggle-kebab\" on the trigger "
        "button — the className is not emitted anywhere in src/)"
    )
    # Descendant rules that reference the dead className.
    for dead in (
        ".tree-row:hover .kebab-trigger",
        ".tree-row.selected .kebab-trigger",
        ".tree-row:focus-within .kebab-trigger",
        ".kebab-trigger:focus-visible",
    ):
        assert not re.search(
            r"(?:^|[\s,{}>+~])" + re.escape(dead) + r"\s*\{", text,
        ), (
            f"PR 5.6 MUST resolve the dead {dead} descendant rule safely "
            f"(.kebab-trigger className is not emitted by any React component)"
        )


# ---- 5.6.3 — collapsed descendant refactor contract ------------------------

def test_5_6_kebab_and_kebab_menu_collapse_into_descendant_rule():
    """5.6.3 — the ``.kebab > .kebab-menu`` collapsed descendant rule
    MUST exist under ``@layer components`` (the 3c-b.4 refactor
    contract carried forward into PR 5.6). The collapsed descendant
    keeps the cascade deterministic — the React <Kebab> mounts the
    menu inside the kebab container so the descendant rule wins."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... } block"
    assert re.search(r"\.kebab\s*>\s*\.kebab-menu", body), (
        "@layer components MUST collapse .kebab + .kebab-menu into "
        ".kebab > .kebab-menu (PR 5.6 descendant collapse refactor)"
    )


def test_5_6_tab_strip_and_tab_button_collapse_into_descendant_rule():
    """5.6.3 — the ``.tab-strip > .tab-button`` collapsed descendant
    rule MUST exist under ``@layer components`` (the 3c-b.4 refactor
    contract carried forward into PR 5.6). The React <TabStrip>
    mounts each ``<button class="tab-button">`` inside the
    ``<div class="tab-strip">`` container, so the descendant rule
    scopes the tab-button declarations to the canonical parent."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... } block"
    assert re.search(r"\.tab-strip\s*>\s*\.tab-button", body), (
        "@layer components MUST collapse .tab-strip + .tab-button into "
        ".tab-strip > .tab-button (PR 5.6 descendant collapse refactor)"
    )


# ---- 5.6.4 — triangulation: state invariants --------------------------------

def test_5_6_tree_row_data_selected_true_has_visible_state_change():
    """5.6.4 — triangulation: the ``.tree-row[data-selected="true"]``
    state selector MUST carry at least one declaration that visually
    distinguishes the selected row from the unselected row (e.g.
    background-color, font-weight, color, or border). The React
    ``<Tree>`` stamps ``data-selected="true"`` on the active row
    (see Tree.tsx) so the selector must drive a visible state change
    — without it the user has no visual feedback for selection."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... } block"
    # Extract the ``.tree-row[data-selected="true"] { ... }`` block
    # body via a balanced-brace scan.
    m = re.search(
        r"\.tree-row\[data-selected=[\"\']true[\"\']\]\s*\{",
        body,
    )
    assert m, (
        "@layer components MUST declare .tree-row[data-selected=\"true\"] "
        "{ ... } (PR 5.6.4 selected-row state invariant)"
    )
    depth, cursor = 1, m.end()
    while cursor < len(body) and depth > 0:
        depth += 1 if body[cursor] == "{" else (
            -1 if body[cursor] == "}" else 0
        )
        cursor += 1
    block_body = body[m.end():cursor - 1]
    # Must contain at least one visible-state property (background-color,
    # color, font-weight, border, padding). ``font-style: italic`` is
    # the React ``<Tree>``'s scientific-name styling and would be
    # meaningless here; assert a non-italic, non-default property.
    assert re.search(
        r"(background(?:-color)?|color|font-weight|border|padding)\s*:",
        block_body,
    ), (
        ".tree-row[data-selected=\"true\"] MUST carry a visible-state "
        "declaration (PR 5.6.4 selected-row state invariant — without "
        "background/color/font-weight/border, the selected row is "
        "indistinguishable from unselected rows)"
    )


def test_5_6_tab_button_active_state_has_visible_state_change():
    """5.6.4 — triangulation: the ``.tab-strip > .tab-button.active``
    state selector MUST carry at least one visible-state declaration
    (background-color, color, border, font-weight). The React
    ``<TabStrip>`` stamps ``active`` on the active tab button so the
    user has a visible indicator of the current tab. Without the
    state selector the tab chrome is indistinguishable across
    Overview / Search / Folder."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... } block"
    m = re.search(
        r"\.tab-strip\s*>\s*\.tab-button\.active\s*\{", body,
    )
    assert m, (
        "@layer components MUST declare .tab-strip > .tab-button.active "
        "{ ... } (PR 5.6.4 active-tab state invariant)"
    )
    depth, cursor = 1, m.end()
    while cursor < len(body) and depth > 0:
        depth += 1 if body[cursor] == "{" else (
            -1 if body[cursor] == "}" else 0
        )
        cursor += 1
    block_body = body[m.end():cursor - 1]
    assert re.search(
        r"(background(?:-color)?|color|font-weight|border)\s*:",
        block_body,
    ), (
        ".tab-strip > .tab-button.active MUST carry a visible-state "
        "declaration (PR 5.6.4 active-tab state invariant)"
    )


def test_5_6_breadcrumb_segment_is_chainable():
    """5.6.4 — triangulation: the ``.breadcrumb-segment`` selector
    MUST be a flex/grid/inline-flex row container so multiple
    segments chain horizontally (the legacy ``<span class="breadcrumb-segment">``
    per-rank segments + the ``>`` separator sibling render
    side-by-side). Without the row layout the segments stack
    vertically and the breadcrumb is unreadable."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... } block"
    m = re.search(
        r"(?:^|[\s,{}>+~])\.breadcrumb-segment\s*\{", body,
    )
    assert m, (
        "@layer components MUST declare .breadcrumb-segment { ... } "
        "(PR 5.6.4 chainable-breadcrumb triangulation)"
    )
    depth, cursor = 1, m.end()
    while cursor < len(body) and depth > 0:
        depth += 1 if body[cursor] == "{" else (
            -1 if body[cursor] == "}" else 0
        )
        cursor += 1
    block_body = body[m.end():cursor - 1]
    assert re.search(r"display\s*:\s*(?:flex|inline-flex|grid)", block_body), (
        ".breadcrumb-segment MUST declare display: flex|inline-flex|grid "
        "(PR 5.6.4 chainable-breadcrumb triangulation — segments must "
        "chain horizontally)"
    )


def test_5_6_detail_body_is_scrollable_container():
    """5.6.4 — triangulation: the ``.detail-body`` selector MUST be
    a scrollable container (overflow-y: auto + max-height) so the
    Overview / Search / Folder body scrolls independently of the
    sticky detail header. The React <DetailPanel> mounts the
    body inside the scroll viewport; without overflow the body
    grows unbounded and breaks the sticky header contract."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... } block"
    m = re.search(
        r"(?:^|[\s,{}>+~])\.detail-body\s*\{", body,
    )
    assert m, (
        "@layer components MUST declare .detail-body { ... } "
        "(PR 5.6.4 scrollable-body triangulation)"
    )
    depth, cursor = 1, m.end()
    while cursor < len(body) and depth > 0:
        depth += 1 if body[cursor] == "{" else (
            -1 if body[cursor] == "}" else 0
        )
        cursor += 1
    block_body = body[m.end():cursor - 1]
    assert re.search(
        r"overflow(?:-y|-x)?\s*:\s*(?:auto|scroll)", block_body,
    ), (
        ".detail-body MUST declare overflow(-y|-x)?: auto|scroll "
        "(PR 5.6.4 scrollable-body triangulation)"
    )


def test_5_6_kebab_selector_bridge_targets_button_data_action():
    """5.6.4 — triangulation: the CSS-only repair MUST carry the
    ``.kebab > button[data-action="toggle-kebab"]`` selector bridge
    that consumes the React <Kebab> trigger. The bridge MUST
    resolve to a non-empty declaration block (visible affordance
    for the trigger button). The React <Kebab> component stamps
    ``data-action="toggle-kebab"`` on the trigger so the legacy
    Playwright / e2e harness keeps matching — the bridge is the
    CSS-only contract for that data-action."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare @layer components { ... } block"
    m = re.search(
        r"\.kebab\s*>\s*button\[data-action=[\"\']toggle-kebab[\"\']\]\s*\{",
        body,
    )
    assert m, (
        "@layer components MUST declare .kebab > button[data-action="
        "\"toggle-kebab\"] { ... } (PR 5.6.4 React <Kebab> trigger "
        "selector bridge)"
    )
    depth, cursor = 1, m.end()
    while cursor < len(body) and depth > 0:
        depth += 1 if body[cursor] == "{" else (
            -1 if body[cursor] == "}" else 0
        )
        cursor += 1
    block_body = body[m.end():cursor - 1]
    assert block_body.strip(), (
        ".kebab > button[data-action=\"toggle-kebab\"] MUST carry a "
        "non-empty declaration (PR 5.6.4 selector bridge must paint)"
    )


# ---- 5.6.5 — slice-scope guard: PR 5.6 MUST NOT bleed into later children --

def test_5_6_does_not_introduce_at_rules_outside_layer_declarations():
    """5.6.5 — PR 5.6 MUST NOT introduce any new ``@keyframes`` or
    other at-rules in the CSS-only repair (those land with PR 3c-iv
    per the 3c sub-sequence design). The only at-rules in
    ``src/app/globals.css`` post-5.6 stay the pre-existing
    ``@import`` / ``@theme`` / ``@layer`` directives. NB ``@keyframes``
    was added to the allowed set in PR 3c-iv-keyframes (position 7/22)
    when the five legacy animation rules landed — the guard must NOT
    false-positive on the now-live keyframes that the materialize
    spinner + detail / search / toast animations consume."""
    text = _strip_comments(_read(GLOBALS_CSS))
    at_rules = re.findall(r"@\w[\w-]*", text)
    allowed = {"@import", "@theme", "@layer", "@keyframes"}
    leaked = [r for r in at_rules if r not in allowed]
    assert not leaked, (
        f"PR 5.6 MUST NOT introduce new at-rules beyond @import / "
        f"@theme / @layer / @keyframes; leaked: {sorted(set(leaked))!r}"
    )


def test_5_6_keeps_color_mix_scoped_to_research_explorer():
    """5.6.5 — the 3c-iii colour-mix scoping invariant survives
    PR 5.6 unchanged. The CSS-only repair lives under @layer
    components alongside the 3c-iii research-explorer chrome;
    PR 5.6 MUST NOT introduce any ``color-mix()`` calls of its
    own (the CSS-only repair uses solid token references, NOT
    alpha mixing)."""
    text = _strip_comments(_read(GLOBALS_CSS))
    # All color-mix calls must already be inside .research-explorer
    # descendant rules per the 3c-iii.9 invariant; PR 5.6's new
    # rules sit OUTSIDE that parent and MUST NOT carry colour-mix.
    call_positions = [m.start() for m in re.finditer(r"color-mix\s*\(", text)]
    assert call_positions, (
        "PR 3c-iii MUST use color-mix() calls (asserted separately); "
        "this test pins the scoping for PR 5.6"
    )
    bad = []
    for pos in call_positions:
        cursor = pos - 1
        while cursor >= 0 and text[cursor] != "}":
            cursor -= 1
        selector_chunk = text[cursor + 1:pos].strip()
        first_sel = re.split(r"\s*,\s*", selector_chunk, maxsplit=1)[0].strip()
        if not first_sel.startswith(".research-explorer"):
            bad.append((pos, first_sel))
    assert not bad, (
        f"PR 5.6 MUST NOT introduce color-mix() calls outside "
        f".research-explorer (3c-iii.9 scoping invariant carries forward); "
        f"drifted selectors: {bad!r}"
    )


# ==============================================================================
# PR 3c-iv-keyframes (position 7/22) — five legacy `@keyframes` + `.animate-spin`
# ==============================================================================
# Legacy source of truth: ``web/index.html`` (retired in PR #171, read-only).
# Ships the five legacy animation rules + ``.animate-spin`` utility verbatim.
# ``.animate-spin`` references ``materialize-spin`` (NOT ``spin``). Top-level
# rules per the legacy cascade. Viewer / settings / colors surfaces stay
# deferred (preserved in ``LATER_CHILD_SURFACES`` above).

# Canonical PR 3c-iv-keyframes catalogue — name + (from-signature, to-signature)
# regex pinning the verbatim legacy property values. A refactor that swaps
# any signature would silently drift the React animation curve.
KEYFRAMES_3C_IV = (
    ("detail-card-enter",
     r"opacity\s*:\s*0\b.*translateY\(\s*-8px\s*\)\s+scale\(\s*0\.995\s*\)",
     r"opacity\s*:\s*1\b.*translateY\(\s*0\s*\)\s+scale\(\s*1\s*\)"),
    ("detail-card-leave",
     r"opacity\s*:\s*1\b.*translateY\(\s*0\s*\)\s+scale\(\s*1\s*\)",
     r"opacity\s*:\s*0\b.*translateY\(\s*-6px\s*\)\s+scale\(\s*0\.995\s*\)"),
    ("search-pulse-anim",
     r"rgba\(\s*29\s*,\s*126\s*,\s*169\s*,\s*0\.55\s*\)",
     r"rgba\(\s*29\s*,\s*126\s*,\s*169\s*,\s*0\s*\)"),
    ("materialize-spin",
     r"transform\s*:\s*rotate\(\s*0(?:deg)?\s*\)",
     r"transform\s*:\s*rotate\(\s*360deg\s*\)"),
    ("toast-slide-in",
     r"opacity\s*:\s*0\b.*translate\(\s*-50%\s*,\s*8px\s*\)",
     r"opacity\s*:\s*1\b.*translate\(\s*-50%\s*,\s*0\s*\)"),
)


def _keyframe_body(text: str, name: str) -> str:
    """Balanced-brace scan for the body of ``@keyframes <name> { ... }``."""
    m = re.search(r"@keyframes\s+" + re.escape(name) + r"\s*\{", text)
    if not m:
        return ""
    depth, cursor = 1, m.end()
    while cursor < len(text) and depth > 0:
        depth += 1 if text[cursor] == "{" else (-1 if text[cursor] == "}" else 0)
        cursor += 1
    return text[m.end():cursor - 1] if depth == 0 else ""


def _top_rule_body(text: str, selector: str) -> str:
    """Balanced-brace scan for the body of the FIRST top-level
    ``<selector> { ... }`` rule (matched at CSS-token boundaries)."""
    m = re.search(r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"\s*\{", text)
    if not m:
        return ""
    depth, cursor = 1, m.end()
    while cursor < len(text) and depth > 0:
        depth += 1 if text[cursor] == "{" else (-1 if text[cursor] == "}" else 0)
        cursor += 1
    return text[m.end():cursor - 1] if depth == 0 else ""


# ---- 3c-iv-keyframes.1 — presence + legacy signature -----------------------

@pytest.mark.parametrize("name,from_sig,to_sig", KEYFRAMES_3C_IV)
def test_3c_iv_keyframes_resolves_with_legacy_signature(name, from_sig, to_sig):
    """Each legacy ``@keyframes`` MUST carry the verbatim ``from`` /
    ``to`` (or ``0%`` / ``100%``) property signatures from
    ``web/index.html``. DOTALL matching so compound
    ``translateY(...) scale(...)`` + ``opacity`` declarations are matched
    together."""
    text = _strip_comments(_read(GLOBALS_CSS))
    body = _keyframe_body(text, name)
    assert body, f"globals.css MUST declare @keyframes {name} {{ ... }} (PR 3c-iv-keyframes.1)"
    assert re.search(from_sig, body, re.DOTALL), (
        f"@keyframes {name} MUST carry the legacy from/0% signature"
    )
    assert re.search(to_sig, body, re.DOTALL), (
        f"@keyframes {name} MUST carry the legacy to/100% signature"
    )


def test_3c_iv_animate_spin_resolves_with_materialize_spin_linkage():
    """``.animate-spin`` MUST resolve to a non-empty block whose
    ``animation`` shorthand references ``materialize-spin`` (NOT the
    renamed ``spin`` alias) at the legacy 0.8s linear infinite timing."""
    text = _read(GLOBALS_CSS)
    body = _top_rule_body(text, ".animate-spin")
    assert body, "globals.css MUST declare .animate-spin { ... } (PR 3c-iv-keyframes.2)"
    assert re.search(r"animation\s*:\s*materialize-spin\b", body), (
        ".animate-spin MUST reference materialize-spin via animation"
    )
    assert re.search(r"0\.8s", body) and re.search(r"linear", body), (
        ".animate-spin MUST keep the legacy 0.8s linear infinite timing"
    )


# ---- 3c-iv-keyframes.3 — source order + cascade position --------------------

def test_3c_iv_keyframes_appear_after_layer_base_closing_brace():
    """Every legacy ``@keyframes`` MUST appear as a top-level rule
    AFTER ``@layer base { ... }`` closes (legacy ``web/index.html``
    cascade). Top-level rules win against ``@layer base`` rules of the
    same specificity."""
    text = _read(GLOBALS_CSS)
    base_open = re.search(r"@layer\s+base\s*\{", text)
    assert base_open, "globals.css must declare @layer base"
    depth, cursor = 1, base_open.end()
    while cursor < len(text) and depth > 0:
        depth += 1 if text[cursor] == "{" else (-1 if text[cursor] == "}" else 0)
        cursor += 1
    base_close_pos = cursor - 1 if depth == 0 else -1
    assert base_close_pos > 0, "@layer base must have a balanced closing brace"
    for name, _, _ in KEYFRAMES_3C_IV:
        m = re.search(r"@keyframes\s+" + re.escape(name) + r"\s*\{", text)
        assert m, f"@keyframes {name} missing (PR 3c-iv-keyframes.3)"
        assert m.start() > base_close_pos, (
            f"@keyframes {name} MUST appear AFTER @layer base closes"
        )


def test_3c_iv_animate_spin_appears_after_keyframes_materialize_spin():
    """``.animate-spin`` MUST appear AFTER ``@keyframes materialize-spin``
    in source order (the definition must precede its consumer)."""
    text = _read(GLOBALS_CSS)
    keyframe_m = re.search(r"@keyframes\s+materialize-spin\s*\{", text)
    spin_m = re.search(r"(?:^|[\s,{}>+~])\.animate-spin\s*\{", text)
    assert keyframe_m, "@keyframes materialize-spin missing"
    assert spin_m, ".animate-spin missing"
    assert spin_m.start() > keyframe_m.start(), (
        ".animate-spin MUST appear AFTER @keyframes materialize-spin"
    )


# ---- 3c-iv-keyframes.4 — slice-scope guard ----------------------------------

def test_3c_iv_keyframes_does_not_pre_assert_viewer_settings_colors_surfaces():
    """Slice-scope guard: PR 3c-iv-keyframes ships ONLY the five
    ``@keyframes`` + ``.animate-spin``. MUST NOT pre-define viewer /
    settings / colors surfaces (those land with 3c-iv-viewer / settings
    / colors in the replan)."""
    text = _strip_comments(_read(GLOBALS_CSS))
    leaked = [s for s in LATER_CHILD_SURFACES if _appears_as_css_token(text, s)]
    assert not leaked, (
        f"PR 3c-iv-keyframes MUST NOT pre-define viewer / settings / "
        f"colors surfaces; leaked: {leaked!r}"
    )


# ---- 3c-iv-keyframes.5 — negative-case triangulation ------------------------

def test_3c_iv_keyframes_does_not_introduce_renamed_spin_keyframe():
    """The renamed ``@keyframes spin`` MUST NOT appear — the legacy
    ``web/index.html`` used the materialise-prefixed name and the 3c-iv
    replan restores that name verbatim. A future rename would leave
    ``.animate-spin`` pointing at nothing."""
    text = _strip_comments(_read(GLOBALS_CSS))
    assert not re.search(r"@keyframes\s+spin\b", text), (
        "globals.css MUST NOT carry a renamed `@keyframes spin` "
        "(PR 3c-iv-keyframes.5 — legacy `materialize-spin` is authoritative)"
    )


def test_3c_iv_animate_spin_does_not_reference_renamed_spin_alias():
    """``.animate-spin`` MUST reference ``materialize-spin`` and MUST NOT
    reference a bare ``spin`` alias (checked via negative lookbehind to
    skip the ``materialize-`` prefix substring)."""
    text = _read(GLOBALS_CSS)
    body = _top_rule_body(text, ".animate-spin")
    assert body, ".animate-spin missing"
    assert re.search(r"\bmaterialize-spin\b", body), (
        ".animate-spin MUST reference `materialize-spin`"
    )
    assert not re.search(r"(?<!materialize-)\bspin\b", body), (
        ".animate-spin MUST NOT reference a bare `spin` alias"
    )


@pytest.mark.parametrize("name", [k[0] for k in KEYFRAMES_3C_IV])
def test_3c_iv_keyframes_is_top_level_not_inside_any_layer(name):
    """Each legacy ``@keyframes`` MUST be a TOP-LEVEL rule — NOT nested
    inside ``@layer base`` / ``@layer components``. The legacy cascade
    placed them at the top so every layer could reach them. The test
    walks backward from each declaration and asserts the nearest
    enclosing at-rule is NOT a layer directive."""
    text = _read(GLOBALS_CSS)
    m = re.search(r"@keyframes\s+" + re.escape(name) + r"\s*\{", text)
    assert m, f"@keyframes {name} missing"
    cursor = m.start() - 1
    while cursor >= 0:
        if text[cursor] == "}":
            depth, c = 1, cursor - 1
            while c >= 0 and depth > 0:
                if text[c] == "}":
                    depth += 1
                elif text[c] == "{":
                    depth -= 1
                c -= 1
            cursor = c
            continue
        if text[cursor] == "{":
            preceding = text[:cursor].rstrip()
            assert not re.search(
                r"@layer\s+(?:base|components)\s*$", preceding,
            ), (
                f"@keyframes {name} MUST be a top-level rule "
                f"(NOT nested inside @layer base / components)"
            )
            break
        cursor -= 1


def test_3c_iv_animate_spin_is_top_level_not_inside_any_layer():
    """``.animate-spin`` MUST be a TOP-LEVEL rule — NOT nested inside
    any ``@layer`` block. As a utility class, it wins against any
    same-specificity component-scoped animation override."""
    text = _read(GLOBALS_CSS)
    m = re.search(r"(?:^|[\s,{}>+~])\.animate-spin\s*\{", text)
    assert m, ".animate-spin missing"
    cursor = m.start() - 1
    while cursor >= 0:
        if text[cursor] == "}":
            depth, c = 1, cursor - 1
            while c >= 0 and depth > 0:
                if text[c] == "}":
                    depth += 1
                elif text[c] == "{":
                    depth -= 1
                c -= 1
            cursor = c
            continue
        if text[cursor] == "{":
            preceding = text[:cursor].rstrip()
            assert not re.search(
                r"@layer\s+(?:base|components)\s*$", preceding,
            ), (
                ".animate-spin MUST be a top-level rule "
                "(NOT nested inside @layer base / components)"
            )
            break
        cursor -= 1


# ==============================================================================
# PR 3c-iv-viewer (position 8/22) — image + video viewer CSS parity
# ==============================================================================
# Legacy source of truth: ``web/index.html`` lines 1750–1822 (retired in
# PR #171, read-only). Ships the image + video viewer frames under the
# ``.research-explorer`` descendant contract that PR 3c-iii.5 already
# locked for file-explorer chrome (the React ``<FileViewer>`` in PR 5b
# consumes them via the same stable parent selector name). The viewer
# frames reuse the 3c-i tokens (``--surface-container-low``,
# ``--outline-variant``, ``--on-surface``, ``--primary``) + the 3c-iii.9
# ``color-mix()`` relaxation (the legacy ``.fex-image-advisory`` background
# carries the primary-tinted alpha the cascade depends on). Settings /
# colors surfaces stay deferred to PR 3c-iv-settings + PR 3c-iv-colors
# (the existing ``LATER_CHILD_SURFACES`` guard still protects them).

# Canonical PR 3c-iv-viewer selector catalogue — the five viewer frame
# selectors + the legacy ``.fex-image-advisory`` icon descendant.
VIEWER_3C_IV_SELECTORS = (
    ".fex-image-frame",
    ".fex-image",
    ".fex-image-advisory",
    ".fex-image-advisory .material-symbols-outlined",
    ".fex-video-frame",
    ".fex-video-el",
)


def _viewer_descendant_body(text: str, descendant: str) -> str:
    """Balanced-brace body for the FIRST ``.research-explorer <desc> { ... }``
    rule in ``text``. Used to assert viewer-frame visual + responsive
    signatures against the legacy cascade."""
    desc_escaped = re.escape(descendant).replace(re.escape("."), r"\.")
    m = re.search(
        r"(?:^|[\s,{}>+~])" + re.escape(RESEARCH_EXPLORER_PARENT)
        + r"\s+" + desc_escaped + r"\s*\{",
        text,
    )
    if not m:
        return ""
    depth, cursor = 1, m.end()
    while cursor < len(text) and depth > 0:
        depth += 1 if text[cursor] == "{" else (
            -1 if text[cursor] == "}" else 0
        )
        cursor += 1
    return text[m.end():cursor - 1] if depth == 0 else ""


def _layer_components_block_for(text: str, target_pos: int) -> bool:
    """Return True iff ``target_pos`` lives inside an ``@layer components``
    block. The file carries two ``@layer components`` blocks (3c-ii taxonomy
    selectors then 3c-iii research-explorer chrome); the helper walks
    every block in source order so it does NOT false-positive against
    the FIRST block when the target lives in the SECOND."""
    cursor = 0
    while True:
        m = re.search(r"@layer\s+components\s*\{", text[cursor:])
        if not m:
            return False
        open_pos = cursor + m.start()
        depth, c = 1, cursor + m.end()
        while c < len(text) and depth > 0:
            depth += 1 if text[c] == "{" else (
                -1 if text[c] == "}" else 0
            )
            c += 1
        close_pos = c - 1 if depth == 0 else -1
        if close_pos < 0:
            return False
        if open_pos < target_pos < close_pos:
            return True
        cursor = close_pos + 1


# ---- 3c-iv-viewer.1 — presence: every viewer selector MUST resolve --------

@pytest.mark.parametrize("selector", VIEWER_3C_IV_SELECTORS)
def test_3c_iv_viewer_selector_resolves_to_non_empty_declaration(selector):
    """3c-iv-viewer.1 (R) — every legacy viewer selector MUST resolve to a
    non-empty declaration block. Fails on the post-PR-3c-iv-keyframes
    base because no viewer selectors exist yet."""
    text = _read(GLOBALS_CSS)
    own_block = re.compile(
        r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"\s*\{[^}]*\S[^}]*\}"
    )
    list_item = re.compile(
        r"(?:^|[\s,{}>+~])" + re.escape(selector)
        + r"\s*,\s*[^{}]*?\{[^}]*\S[^}]*\}"
    )
    assert own_block.search(text) or list_item.search(text), (
        f"globals.css MUST declare {selector} with a non-empty block "
        f"(PR 3c-iv-viewer.1)"
    )


# ---- 3c-iv-viewer.3 — visual / responsive signatures (image + video) -------

def test_3c_iv_viewer_image_signatures():
    """3c-iv-viewer.3 (T) — the image viewer chain (frame + img + advisory +
    advisory-icon) MUST carry the legacy visual + responsive signatures:
    ``.fex-image-frame`` is a flex container with ``min-height: 320px`` and
    ``overflow: auto`` (the frame owns the scroll surface so the inner
    image shrinks via ``object-contain``); ``.fex-image`` carries
    ``max-width: 100%`` + ``max-height: 70vh`` + ``object-fit: contain``
    (responsive shrink that preserves aspect ratio); ``.fex-image-advisory``
    carries the legacy ``color-mix`` tinted background + tinted border
    (the big-file warning the cascade depends on); the advisory icon
    carries the legacy primary tint (``color: var(--primary)`` +
    ``font-size: 16px``) consistent with the design system."""
    text = _read(GLOBALS_CSS)
    frame = _viewer_descendant_body(text, ".fex-image-frame")
    assert frame and re.search(r"display\s*:\s*flex\b", frame) \
        and re.search(r"min-height\s*:\s*320px\b", frame) \
        and re.search(r"overflow\s*:\s*auto\b", frame) \
        and re.search(r"1px\s+solid\s+var\(--outline-variant\)", frame), (
        ".fex-image-frame MUST carry `display: flex` + `min-height: 320px` "
        "+ `overflow: auto` + 1px outline-variant border "
        "(PR 3c-iv-viewer.3)"
    )
    image = _viewer_descendant_body(text, ".fex-image")
    assert image and re.search(r"max-width\s*:\s*100%", image) \
        and re.search(r"max-height\s*:\s*70vh\b", image) \
        and re.search(r"object-fit\s*:\s*contain\b", image), (
        ".fex-image MUST carry `max-width: 100%` + `max-height: 70vh` + "
        "`object-fit: contain` (PR 3c-iv-viewer.3)"
    )
    advisory = _viewer_descendant_body(text, ".fex-image-advisory")
    assert advisory and re.search(
        r"background\s*:\s*color-mix\(\s*in\s+srgb\s*,\s*var\(--primary\)\s+8%\s*,\s*var\(--surface\)\s*\)",
        advisory,
    ) and re.search(
        r"border\s*:\s*1px\s+solid\s+color-mix\(\s*in\s+srgb\s*,\s*var\(--primary\)\s+24%\s*,\s*var\(--outline-variant\)\s*\)",
        advisory,
    ) and re.search(r"color\s*:\s*var\(--on-surface\)", advisory), (
        ".fex-image-advisory MUST carry the legacy color-mix tinted "
        "background + border + `color: var(--on-surface)` "
        "(PR 3c-iv-viewer.3)"
    )
    icon = _viewer_descendant_body(
        text, ".fex-image-advisory .material-symbols-outlined",
    )
    assert icon and re.search(r"color\s*:\s*var\(--primary\)", icon) \
        and re.search(r"font-size\s*:\s*16px\b", icon), (
        ".fex-image-advisory .material-symbols-outlined MUST carry "
        "`color: var(--primary)` + `font-size: 16px` (PR 3c-iv-viewer.3)"
    )


def test_3c_iv_viewer_video_signatures():
    """3c-iv-viewer.3 (T) — the video viewer chain (frame + el) MUST carry
    the legacy visual + responsive signatures: ``.fex-video-frame`` is a
    flex container with ``background: #000`` (the legacy letterbox),
    ``min-height: 320px`` (prevents thumbnail collapse), and
    ``overflow: hidden`` (the video letterbox clips overflow);
    ``.fex-video-el`` mirrors the image viewer cap (``max-width: 100%`` +
    ``max-height: 70vh``) and carries the ``#000`` background so the
    black bars are seamless during load."""
    text = _read(GLOBALS_CSS)
    frame = _viewer_descendant_body(text, ".fex-video-frame")
    assert frame and re.search(r"display\s*:\s*flex\b", frame) \
        and re.search(r"background\s*:\s*#000\b", frame) \
        and re.search(r"min-height\s*:\s*320px\b", frame) \
        and re.search(r"overflow\s*:\s*hidden\b", frame), (
        ".fex-video-frame MUST carry `display: flex` + `background: #000` "
        "+ `min-height: 320px` + `overflow: hidden` (PR 3c-iv-viewer.3)"
    )
    el = _viewer_descendant_body(text, ".fex-video-el")
    assert el and re.search(r"max-width\s*:\s*100%", el) \
        and re.search(r"max-height\s*:\s*70vh\b", el) \
        and re.search(r"background\s*:\s*#000\b", el), (
        ".fex-video-el MUST carry `max-width: 100%` + `max-height: 70vh` "
        "+ `background: #000` (PR 3c-iv-viewer.3)"
    )


# ---- 3c-iv-viewer.4 — nesting / layer contract -----------------------------

@pytest.mark.parametrize("descendant", VIEWER_3C_IV_SELECTORS)
def test_3c_iv_viewer_frames_collapse_into_research_explorer_inside_layer_components(descendant):
    """3c-iv-viewer.4 (Refactor) — every viewer frame selector MUST live as
    a DESCENDANT of ``.research-explorer`` AND inside the
    ``@layer components`` block. Mirrors the 3c-iii.5 refactor contract
    for file-explorer chrome so the React ``<FileViewer>`` in PR 5b can
    consume the CSS via the stable ``.research-explorer`` parent
    selector name. The helper ``_layer_components_block_for`` walks
    every ``@layer components`` block in source order (the file carries
    two: 3c-ii taxonomy then 3c-iii research-explorer) so the assertion
    does NOT false-positive against the 3c-ii block when the viewer
    lives in the 3c-iii block."""
    text = _read(GLOBALS_CSS)
    desc_escaped = re.escape(descendant).replace(re.escape("."), r"\.")
    pattern = (
        r"(?:^|[\s,{}>+~])" + re.escape(RESEARCH_EXPLORER_PARENT)
        + r"\s+" + desc_escaped + r"(?:\s*\{|\s*,)"
    )
    m = re.search(pattern, text)
    assert m, (
        f"{descendant} MUST be a descendant rule of {RESEARCH_EXPLORER_PARENT} "
        f"(PR 3c-iv-viewer.4 — collapse viewer frames into the parent so "
        f"the React <FileViewer> consumes them via the stable selector)"
    )
    assert _layer_components_block_for(text, m.start()), (
        f"{descendant} MUST live inside @layer components "
        f"(descendant@{m.start()}) — the 3c-iv-viewer refactor step "
        f"relocates the viewer frames under the stable layer name"
    )


def test_3c_iv_viewer_frames_follow_existing_research_explorer_chrome():
    """3c-iv-viewer.4 (Refactor) — source-order invariant: the viewer
    frames MUST appear AFTER the existing 3c-iii chrome (the last
    rule in the layer is the legacy ``.fex-tree-truncated
    .material-symbols-outlined``). Cascade source order matters inside
    a single ``@layer components`` block: later rules win against
    earlier rules of equal specificity."""
    text = _read(GLOBALS_CSS)
    last_chrome_m = re.search(
        r"\.research-explorer\s+\.fex-tree-truncated\s+\.material-symbols-outlined\s*\{",
        text,
    )
    assert last_chrome_m, (
        "the legacy 3c-iii .fex-tree-truncated .material-symbols-outlined "
        "selector MUST exist (3c-iii cascade contract — pre-condition "
        "for the 3c-iv-viewer source-order invariant)"
    )
    for selector in VIEWER_3C_IV_SELECTORS:
        desc_escaped = re.escape(selector).replace(re.escape("."), r"\.")
        m = re.search(
            r"(?:^|[\s,{}>+~])" + re.escape(RESEARCH_EXPLORER_PARENT)
            + r"\s+" + desc_escaped + r"\s*\{",
            text,
        )
        assert m, (
            f"{selector} MUST be a descendant rule of .research-explorer "
            f"(PR 3c-iv-viewer.4 — pre-condition)"
        )
        assert m.start() > last_chrome_m.start(), (
            f"{selector} MUST appear AFTER the existing 3c-iii chrome "
            f"(.fex-tree-truncated .material-symbols-outlined at "
            f"{last_chrome_m.start()}; viewer at {m.start()}) — source "
            f"order inside @layer components matters for the cascade"
        )


# ---- 3c-iv-viewer.5 — deferred Settings/colors guard preserved -------------

def test_3c_iv_viewer_does_not_pre_assert_settings_or_colors_surfaces():
    """3c-iv-viewer deferred guard: the viewer CSS MUST NOT pre-define
    settings / colors surfaces (``LATER_CHILD_SURFACES``). Those still
    land with PR 3c-iv-settings (9/22) + PR 3c-iv-colors (10/22)."""
    text = _strip_comments(_read(GLOBALS_CSS))
    leaked = [s for s in LATER_CHILD_SURFACES if _appears_as_css_token(text, s)]
    assert not leaked, (
        f"PR 3c-iv-viewer MUST NOT pre-define settings / colors surfaces; "
        f"those stay deferred to PR 3c-iv-settings + PR 3c-iv-colors; "
        f"leaked: {leaked!r}"
    )


# ==============================================================================
# PR 3c-iv-settings (position 9/22) — Settings view CSS parity
# ==============================================================================
# Legacy source of truth: ``web/index.html`` lines 1833-1969 (retired
# in PR #171, read-only). Ships the 20 legacy Settings view selectors
# under ``@layer base`` per OpenSpec 3c-iv-settings.2, alphabetized
# with the ``.settings-theme-btn-active`` / ``:hover`` pair pinned
# immediately before ``.settings-action-btn`` (per OpenSpec
# 3c-iv-settings.4) so the colors child slice (PR 3c-iv-colors, 10/22)
# can locate ``.settings-theme-btn-active`` via a single prefix scan
# that terminates at the first match.
#
# Tokens reuse the 3c-i family (``--surface-container-low``,
# ``--outline-variant``, ``--primary``, ``--on-surface``,
# ``--on-surface-variant``); the selectors land verbatim — no new
# tokens, no ``--color-*`` namespace aliases, no utility-class
# additions. The colors surface stays deferred to PR 3c-iv-colors
# (10/22) and is still protected by ``LATER_CHILD_SURFACES``.

# Canonical PR 3c-iv-settings selector catalogue — the 20 legacy
# Settings selectors in the source order PR 3c-iv-settings ships.
# ``.settings-theme-btn-active`` + ``:hover`` are pinned at the TOP of
# the list (immediately before ``.settings-action-btn``) per the
# colors-slice prefix-scan contract; the remaining 18 selectors are
# alphabetical (canonical CSS groups sibling variants — the ``:hover``
# + ``.material-symbols-outlined`` descendants — adjacent to their
# base selector so the cascade wires them as a unit).
SETTINGS_3C_IV_SELECTORS = (
    # Pinned at top — colors slice prefix-scan seam (OpenSpec 3c-iv-settings.4).
    ".settings-theme-btn-active",
    ".settings-theme-btn-active:hover",
    # Alphabetical rest (with variants grouped next to their base selector).
    ".settings-action-btn",
    ".settings-action-btn .material-symbols-outlined",
    ".settings-action-btn:hover",
    ".settings-header",
    ".settings-link-btn",
    ".settings-link-btn .material-symbols-outlined",
    ".settings-link-btn:hover",
    ".settings-list",
    ".settings-row",
    ".settings-row-control",
    ".settings-row-description",
    ".settings-row-text",
    ".settings-row-title",
    ".settings-shell",
    ".settings-theme-btn",
    ".settings-theme-btn .material-symbols-outlined",
    ".settings-theme-btn:hover",
    ".settings-theme-toggle",
)


# ---- 3c-iv-settings.1 — selector catalogue resolves under @layer base -----

@pytest.mark.parametrize("selector", SETTINGS_3C_IV_SELECTORS)
def test_3c_iv_settings_selector_resolves_under_layer_base(selector):
    """3c-iv-settings.1 R — every canonical Settings selector MUST resolve
    to a non-empty declaration block under ``@layer base`` in
    ``src/app/globals.css``. The Settings view reuses the legacy 3c-i
    token surface (``--surface-container-low``, ``--outline-variant``,
    ``--primary``, ``--on-surface``, ``--on-surface-variant``) and the
    selectors land under ``@layer base`` per OpenSpec 3c-iv-settings.2
    so the cascade order matches the legacy inline-style block (the
    React ``<SettingsView>`` in a downstream PR consumes them via
    stable selector names).

    The block scan is whole-document (not scoped to a single rule) so
    descendant + descendant-of-descendant rules resolve through the
    parent block. NB the pattern accepts comma-separated selector lists
    (``.a, .b { ... }``) — the canonical CSS form for grouping sibling
    rules that share the same declaration block."""
    text = _read(GLOBALS_CSS)
    own_block = re.compile(
        r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"\s*\{[^}]*\S[^}]*\}"
    )
    list_item = re.compile(
        r"(?:^|[\s,{}>+~])" + re.escape(selector)
        + r"\s*,\s*[^{}]*?\{[^}]*\S[^}]*\}"
    )
    assert own_block.search(text) or list_item.search(text), (
        f"globals.css MUST declare {selector} with a non-empty block "
        f"(PR 3c-iv-settings.1 Settings selector catalogue)"
    )


def test_3c_iv_settings_selectors_resolve_inside_layer_base_block():
    """3c-iv-settings.1 R — every canonical Settings selector MUST
    resolve to a non-empty declaration block under the ``@layer base``
    block specifically (NOT inside ``@layer components`` and NOT as a
    top-level rule). The Settings view lives at the same cascade layer
    as the legacy body / html / focus-visible base resets — the React
    ``<SettingsView>`` relies on the layer's specificity + cascade
    position so utility-class overrides stay honest. (Defense in
    depth against a refactor that sweeps the Settings block into
    ``@layer components`` and breaks the layer contract.)"""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    missing = [
        s for s in SETTINGS_3C_IV_SELECTORS
        if not re.search(
            r"(?:^|[\s,{}>+~])" + re.escape(s) + r"\s*\{[^}]*\S[^}]*\}",
            body,
        )
    ]
    assert not missing, (
        f"@layer base MUST declare every Settings selector with a "
        f"non-empty body (PR 3c-iv-settings.1 — the Settings view lives "
        f"at the same cascade layer as the legacy base resets); "
        f"missing: {missing!r}"
    )


# ---- 3c-iv-settings.3 — triangulation: row layout + active + link hover --

def test_3c_iv_settings_row_carries_flex_row_centered_padding_border():
    """3c-iv-settings.3 T — ``.settings-row`` MUST carry flex-row
    (``display: flex`` — flex-direction defaults to ``row``),
    centered alignment (``align-items: center``), padding, and a
    visible border delineator. The legacy inline-style block uses a
    full ``border: 1px solid var(--outline-variant)`` (NOT
    ``border-bottom`` — the spec's ``border-bottom`` triangulation is
    a permissive catch-all; the assertion accepts both ``border:`` and
    ``border-bottom:`` shapes so the legacy-parity contract + a future
    refactor that swaps to ``border-bottom`` both pass)."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    m = re.search(r"\.settings-row\s*\{", body)
    assert m, (
        "@layer base MUST declare .settings-row { ... } "
        "(PR 3c-iv-settings.3 row layout triangulation)"
    )
    depth, cursor = 1, m.end()
    while cursor < len(body) and depth > 0:
        depth += 1 if body[cursor] == "{" else (
            -1 if body[cursor] == "}" else 0
        )
        cursor += 1
    block_body = body[m.end():cursor - 1]
    assert re.search(r"display\s*:\s*flex\b", block_body), (
        ".settings-row MUST carry `display: flex` (PR 3c-iv-settings.3 "
        "row layout triangulation — the row is a flex container that "
        "lays the label/description text on the left + the control on "
        "the right via justify-content: space-between)"
    )
    assert re.search(r"align-items\s*:\s*center\b", block_body), (
        ".settings-row MUST carry `align-items: center` (PR 3c-iv-settings.3 "
        "centered alignment triangulation — the label + control align "
        "vertically centered so the row chrome reads as a unit)"
    )
    assert re.search(r"padding\s*:", block_body), (
        ".settings-row MUST carry a `padding:` declaration "
        "(PR 3c-iv-settings.3 row padding triangulation — the legacy "
        "uses 16px so the text has breathing room inside the bordered "
        "card chrome)"
    )
    # Accept ``border:`` / ``border-bottom:`` / ``border-top:`` /
    # ``border-left:`` / ``border-right:`` so the legacy
    # ``border: 1px solid var(--outline-variant)`` parity contract +
    # the spec's ``border-bottom`` triangulation both pass. The
    # assertion pins the presence of ANY border-side declaration
    # (matches the spec's intent — the row must read as a visibly
    # delineated card, regardless of which side carries the line).
    assert re.search(
        r"border(?:-bottom|-top|-left|-right)?\s*:", block_body,
    ), (
        ".settings-row MUST carry a `border[-bottom|-top|-left|-right]:` "
        "declaration (PR 3c-iv-settings.3 row border delineator — the "
        "legacy uses a full `border: 1px solid var(--outline-variant)`; "
        "a future refactor may swap to `border-bottom` and the "
        "assertion stays green for both shapes)"
    )


def test_3c_iv_settings_theme_btn_active_has_visible_tinted_background():
    """3c-iv-settings.3 T — ``.settings-theme-btn-active`` MUST carry a
    visible-state background that tints the active theme button (the
    legacy inline-style block uses ``background: var(--primary)`` +
    the inverse ``color: var(--surface)`` so the active light / dark
    / system theme button reads as visibly tinted). The assertion
    accepts any non-default background (var / color / gradient / tint
    variant) so a future refactor that swaps the primary literal for
    a tint-mix variant still passes — only ``transparent`` + ``none``
    are excluded."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    m = re.search(r"\.settings-theme-btn-active\s*\{", body)
    assert m, (
        "@layer base MUST declare .settings-theme-btn-active { ... } "
        "(PR 3c-iv-settings.3 active-theme state triangulation)"
    )
    depth, cursor = 1, m.end()
    while cursor < len(body) and depth > 0:
        depth += 1 if body[cursor] == "{" else (
            -1 if body[cursor] == "}" else 0
        )
        cursor += 1
    block_body = body[m.end():cursor - 1]
    bg_match = re.search(
        r"background(?:-color)?\s*:\s*([^;]+)", block_body,
    )
    assert bg_match, (
        ".settings-theme-btn-active MUST carry a `background(-color):` "
        "declaration (PR 3c-iv-settings.3 active-theme state "
        "triangulation — the active theme button must read as visibly "
        "tinted so the user can tell which theme is selected)"
    )
    bg_value = bg_match.group(1).strip().split()[0]
    assert bg_value not in ("transparent", "none"), (
        f".settings-theme-btn-active background MUST be a visible "
        f"tint (got `{bg_value}`; PR 3c-iv-settings.3 — the legacy uses "
        f"`background: var(--primary)` + the inverse "
        f"`color: var(--surface)` so the active theme reads as tinted)"
    )


def test_3c_iv_settings_link_btn_hover_has_visible_state():
    """3c-iv-settings.3 T — ``.settings-link-btn:hover`` MUST carry a
    visible-state declaration (the legacy inline-style block uses
    ``background: var(--surface-container-low)`` so the link button
    reads as interactively hoverable; without the hover state the
    React ``<SettingsLink>`` exposes no affordance that the user can
    click). The assertion accepts any non-default background so a
    future refactor that swaps to a tint-mix variant still passes."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    m = re.search(r"\.settings-link-btn:hover\s*\{", body)
    assert m, (
        "@layer base MUST declare .settings-link-btn:hover { ... } "
        "(PR 3c-iv-settings.3 link-button hover state triangulation)"
    )
    depth, cursor = 1, m.end()
    while cursor < len(body) and depth > 0:
        depth += 1 if body[cursor] == "{" else (
            -1 if body[cursor] == "}" else 0
        )
        cursor += 1
    block_body = body[m.end():cursor - 1]
    assert re.search(r"background(?:-color)?\s*:", block_body), (
        ".settings-link-btn:hover MUST carry a visible "
        "`background(-color):` declaration (PR 3c-iv-settings.3 — the "
        "hover state must read as interactive so the React "
        "<SettingsLink> exposes a hover affordance the user can click)"
    )


# ---- 3c-iv-settings.4 — refactor: alphabetization + prefix-scan seam -------

def test_3c_iv_settings_theme_btn_active_appears_before_settings_action_btn():
    """3c-iv-settings.4 Refactor — the ``.settings-theme-btn-active``
    declaration MUST appear in source order BEFORE the
    ``.settings-action-btn`` declaration (per OpenSpec 3c-iv-settings.4)
    so the colors child slice (PR 3c-iv-colors, 10/22) can locate
    ``.settings-theme-btn-active`` via a single ``re.search(...)``
    prefix scan that terminates at the first match. A colors-slice
    scan that uses ``text.find(".settings-theme-btn-active")`` would
    otherwise find the wrong selector if the alphabetization placed
    ``.settings-action-btn*`` first.

    The assertion scans the WHOLE document (not the @layer base block
    only) so a future refactor that splits the Settings block across
    layers still trips the source-order invariant if the active-theme
    selector moves below ``.settings-action-btn``."""
    text = _strip_comments(_read(GLOBALS_CSS))
    active_m = re.search(r"\.settings-theme-btn-active\s*\{", text)
    action_m = re.search(r"\.settings-action-btn\s*\{", text)
    assert active_m, (
        "globals.css MUST declare .settings-theme-btn-active { ... } "
        "(PR 3c-iv-settings.4 prefix-scan seam)"
    )
    assert action_m, (
        "globals.css MUST declare .settings-action-btn { ... } "
        "(PR 3c-iv-settings.4 prefix-scan seam)"
    )
    assert active_m.start() < action_m.start(), (
        ".settings-theme-btn-active MUST appear BEFORE .settings-action-btn "
        "in source order (PR 3c-iv-settings.4 prefix-scan seam — the "
        "colors slice locates the active theme button via a prefix scan "
        "that terminates at the first match; if .settings-action-btn "
        "appears first, the scan returns the wrong position)"
    )


def test_3c_iv_settings_selectors_are_alphabetized_after_prefix_pin():
    """3c-iv-settings.4 Refactor — the 18 Settings selectors that are
    NOT pinned at the top MUST be alphabetized in source order
    (``.settings-theme-btn-active*`` pair pinned first; everything
    else alphabetical with ``:hover`` / ``.material-symbols-outlined``
    descendants grouped adjacent to their base selector). The
    alphabetization lets the colors slice locate any single Settings
    selector via a deterministic prefix scan that returns the
    expected index.

    The assertion checks the canonical sort order over the SECOND
    slice of the catalogue (everything after the
    ``.settings-theme-btn-active:hover`` pinned pair). The
    ``:hover`` / ``.material-symbols-outlined`` descendant groups
    stay adjacent to their base selector — the alphabetical sort
    treats ``.settings-action-btn`` (and its descendants) as a unit,
    and the same for ``.settings-link-btn`` + ``.settings-theme-btn``."""
    text = _strip_comments(_read(GLOBALS_CSS))
    # Build the list of (selector, source-position) pairs in source order.
    positions = []
    for selector in SETTINGS_3C_IV_SELECTORS:
        m = re.search(
            r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"\s*\{", text,
        )
        assert m, (
            f"globals.css MUST declare {selector} {{ ... }} "
            f"(PR 3c-iv-settings.4 alphabetization triangulation)"
        )
        positions.append((selector, m.start()))
    # The catalogue is the canonical source order; assert the actual
    # source order matches the catalogue (positions are monotonically
    # increasing).
    actual_order = [s for s, _ in sorted(positions, key=lambda p: p[1])]
    assert actual_order == list(SETTINGS_3C_IV_SELECTORS), (
        f"Settings selectors MUST be alphabetized in source order with "
        f"the .settings-theme-btn-active* pair pinned at the top "
        f"(PR 3c-iv-settings.4 — colors slice prefix-scan seam). "
        f"Expected order: {list(SETTINGS_3C_IV_SELECTORS)!r}; "
        f"actual order: {actual_order!r}"
    )


# ---- 3c-iv-settings.5 — slice-scope guard ----------------------------------

def test_3c_iv_settings_does_not_pre_assert_colors_surfaces():
    """3c-iv-settings deferred guard: the Settings CSS MUST NOT
    pre-define colors surfaces (``LATER_CHILD_SURFACES``). The Tailwind
    ``--color-*`` namespace aliases + the utility-class parity land
    with PR 3c-iv-colors (10/22); pre-asserting them here would
    silently reserve the namespace and block the per-PR review focus
    on the colors slice."""
    text = _strip_comments(_read(GLOBALS_CSS))
    leaked = [s for s in LATER_CHILD_SURFACES if _appears_as_css_token(text, s)]
    assert not leaked, (
        f"PR 3c-iv-settings MUST NOT pre-define colors surfaces; "
        f"those stay deferred to PR 3c-iv-colors; leaked: {leaked!r}"
    )
