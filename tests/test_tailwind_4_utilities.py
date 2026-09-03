"""Utility-class + alias parity tests for PR 3c-e1 (CSS slice).

PR 3c-e1 (position 7/19; the 3c-e1/e2 no-loss re-split per PR #154)
owns ONLY the **alias renames + remaining ``@keyframes``**:

- ``primary-fixed -> primary`` and ``on-primary-fixed -> on-primary``
  CSS-custom-property aliases declared under ``globals.css::@layer
  components`` (preserve the legacy surface against the upstream
  ``primary`` / ``on-primary`` tokens shipped by PR 3c-a).
- The four remaining ``@keyframes`` blocks (not yet shipped by
  PR 3c-d's ``@keyframes spin``): ``detail-card-enter``,
  ``detail-card-leave``, ``search-pulse-anim``, ``toast-slide-in``
  — declared under ``globals.css::@layer base`` in source order
  AFTER the existing resets and ``@keyframes spin``.

**OUT of scope for 3c-e1** (these belong to PR 3c-e2 or PR 3c-f):

- Utility classes — ``.bg-primary``, ``.text-on-surface``,
  ``.border-outline-variant``, ``.bg-surface-container-lowest``,
  ``.shadow-sm``, ``.rounded-r-md``, ``.bg-primary-fixed``,
  ``.text-on-primary-fixed``, ``.animate-spin``, … (3c-e2).
- Component-scoped ``color-mix()`` rules — every ``color-mix(in
  srgb, var(--token) X%, transparent)`` line inside a specific
  component class belongs under ``@layer components`` (3c-e2, or
  3c-f alone owns the full-parity witness for ``color-mix()``).
- The final consolidated parity test
  ``tests/test_tailwind_4_parity.py`` (3c-f).

This test file **reuses the 3c-d guards** (selector-resolution +
source-order helpers) imported from
``tests/test_tailwind_4_base_resets.py`` rather than duplicating
them.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.test_tailwind_4_base_resets import (  # noqa: F401 — reused 3c-d guards
    REPO_ROOT,
    GLOBALS_CSS,
    _read,
    _block,
    _rule,
)

# PR 3c-e1 alias renames — the two CSS-custom-property aliases that
# preserve the legacy `primary-fixed -> primary` and
# `on-primary-fixed -> on-primary` mapping. The aliases MUST live
# under `@layer components` (NOT `@layer base`).
ALIAS_RENAMES_3C_E1: tuple[str, ...] = (
    "--primary-fixed",
    "--on-primary-fixed",
)
# PR 3c-e1 remaining @keyframes — the four keyframes not yet shipped
# by PR 3c-d's `@keyframes spin`. These MUST live under `@layer
# base` (NOT `@layer components`).
REMAINING_KEYFRAMES_3C_E1: tuple[str, ...] = (
    "detail-card-enter",
    "detail-card-leave",
    "search-pulse-anim",
    "toast-slide-in",
)
# PR 3c-e2 utility-class surface — 3c-e1 MUST NOT add these (the
# utility-class migration is the 3c-e2 slice).
UTILITY_CLASSES_OWNED_BY_3C_E2: tuple[str, ...] = (
    ".bg-primary", ".text-on-surface", ".border-outline-variant",
    ".bg-surface-container-lowest", ".shadow-sm", ".rounded-r-md",
    ".bg-primary-fixed", ".text-on-primary-fixed", ".animate-spin",
)


# ---- 3c-e1.1 — alias renames live under @layer components -------------------

@pytest.mark.parametrize("custom_prop", ALIAS_RENAMES_3C_E1)
def test_layer_components_declares_alias_rename(custom_prop):
    """3c-e1.1 — ``--primary-fixed`` / ``--on-primary-fixed`` MUST be
    declared under ``@layer components`` so the alias-to-upstream-token
    resolution survives the dark-mode ``data-theme`` flip and the
    component cascade order."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare an @layer components { ... } block"
    pattern = (
        r":root\s*\{[^}]*"
        + re.escape(custom_prop)
        + r"\s*:\s*var\(--(?:on-)?primary\)\s*;"
        + r"[^}]*\}"
    )
    assert re.search(pattern, body, re.DOTALL), (
        f"@layer components must declare a :root {{ {custom_prop}: "
        f"var(--primary); ... }} alias block (PR 3c-e1.1 — "
        f"primary-fixed -> primary alias)"
    )


@pytest.mark.parametrize("custom_prop", ALIAS_RENAMES_3C_E1)
def test_layer_base_does_not_own_alias_renames(custom_prop):
    """3c-e1.3 — chain-topology guard: the alias renames belong to
    ``@layer components`` (3c-e1), NOT ``@layer base`` (3c-d). The
    base layer carries the global state affordances; the alias
    surface is a component-cascade concern."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    if not body:
        return
    assert not re.search(
        r"(?:^|[\s,{}>+~])" + re.escape(custom_prop) + r"(?=[\s,{:>+~=]|$)",
        body,
    ), (
        f"{custom_prop} MUST NOT live under @layer base — alias "
        f"renames belong to @layer components (PR 3c-e1.1)"
    )


# ---- 3c-e1.1 — remaining @keyframes live under @layer base -------------------

@pytest.mark.parametrize("kf_name", REMAINING_KEYFRAMES_3C_E1)
def test_layer_base_declares_remaining_keyframes(kf_name):
    """3c-e1.1 — the four remaining ``@keyframes`` (those not shipped
    by PR 3c-d's ``@keyframes spin``) MUST live under
    ``@layer base`` in source order AFTER the existing resets and
    ``@keyframes spin``."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    rule = _rule(body, f"@keyframes {kf_name}")
    assert rule.strip(), (
        f"@layer base must declare @keyframes {kf_name} with a "
        f"non-empty block (PR 3c-e1.1 — remaining keyframe surface)"
    )


@pytest.mark.parametrize("kf_name", REMAINING_KEYFRAMES_3C_E1)
def test_layer_components_does_not_own_remaining_keyframes(kf_name):
    """3c-e1.3 — chain-topology guard: the remaining ``@keyframes``
    belong to ``@layer base`` (3c-e1), NOT ``@layer components``
    (3c-e2). A future CSS re-split MUST NOT migrate them up the
    cascade by accident."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    if not body:
        return
    assert not re.search(r"@keyframes\s+" + re.escape(kf_name) + r"\b", body), (
        f"@layer components MUST NOT own @keyframes {kf_name} "
        f"(PR 3c-e1 owns it under @layer base)"
    )


# ---- 3c-e1.3 — triangulators (negative + boundary) ---------------------------

def test_layer_base_no_color_mix_after_alias_split():
    """3c-e1.3 — chain-topology guard: 3c-e1 MUST NOT introduce any
    ``color-mix()`` rule under either layer. Component-scoped
    ``color-mix()`` rules belong under ``@layer components`` in
    PR 3c-e2 or the final consolidated parity witness in PR 3c-f."""
    for layer in ("base", "components"):
        body = _block(_read(GLOBALS_CSS), f"@layer {layer}")
        if not body:
            continue
        assert "color-mix" not in body, (
            f"@layer {layer} MUST NOT carry any color-mix() rule "
            f"(PR 3c-e1 is alias + remaining keyframes only — "
            f"component color-mix() belongs to 3c-e2 / 3c-f)"
        )


@pytest.mark.parametrize("selector", UTILITY_CLASSES_OWNED_BY_3C_E2)
def test_no_utility_class_ships_in_3c_e1(selector):
    """3c-e1.3 — chain-topology guard: the legacy utility-class surface
    (``bg-primary``, ``text-on-surface``, ``bg-primary-fixed``, …)
    belongs to PR 3c-e2. 3c-e1 ships only aliases + remaining
    keyframes — a stray utility class here is a regression that
    would inflate the 3c-e2 budget."""
    text = _read(GLOBALS_CSS)
    stripped = re.sub(r"/\*[\s\S]*?\*/", "", text)
    base_match = re.search(r"@layer\s+base\s*\{", stripped)
    components_match = re.search(r"@layer\s+components\s*\{", stripped)
    assert base_match and components_match, (
        "globals.css must declare both @layer base and @layer components"
    )
    leaked = re.findall(
        r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"(?=[\s,{:>+~]|$)",
        stripped[base_match.end():components_match.start()],
    )
    components_end = stripped.find("}", components_match.end())
    assert components_end != -1, "@layer components must close"
    leaked.extend(re.findall(
        r"(?:^|[\s,{}>+~])" + re.escape(selector) + r"(?=[\s,{:>+~]|$)",
        stripped[components_match.start():components_end],
    ))
    assert not leaked, (
        f"{selector} MUST NOT ship in PR 3c-e1 — utility-class "
        f"migration is the 3c-e2 slice"
    )


# ---- 3c-e1.2 — alias target chain (dark-mode preservation) ------------------

@pytest.mark.parametrize(
    ("custom_prop", "target_token"),
    [
        ("--primary-fixed", "--primary"),
        ("--on-primary-fixed", "--on-primary"),
    ],
)
def test_alias_rename_targets_upstream_token(custom_prop, target_token):
    """3c-e1.2 — the alias MUST point at ``var(--primary)`` /
    ``var(--on-primary)`` (NOT a hardcoded hex / rgb literal) so the
    dark-mode ``[data-theme="dark"]`` override flips the alias target
    at use-time via the var() indirection. A hardcoded alias would
    freeze the dark-mode parity at the light value."""
    body = _block(_read(GLOBALS_CSS), "@layer components")
    assert body, "globals.css must declare an @layer components { ... } block"
    pattern = (
        r":root\s*\{[^}]*"
        + re.escape(custom_prop)
        + r"\s*:\s*var\(--(?:on-)?primary\)\s*;"
    )
    assert re.search(pattern, body, re.DOTALL), (
        f"{custom_prop} alias MUST target var({target_token}) "
        f"(PR 3c-e1.2 — dark-mode-preserving alias chain)"
    )


# ---- 3c-e1.2 — source order: remaining keyframes follow @keyframes spin -----

def test_remaining_keyframes_appear_after_keyframes_spin_in_layer_base():
    """3c-e1.2 — source order: within ``@layer base``, the four
    remaining ``@keyframes`` MUST appear AFTER the ``@keyframes spin``
    block shipped by PR 3c-d. This keeps the cascade deterministic
    and the source-order contract idempotent under the next PR's
    refactor (3c-e1.4 alphabetise-within-each-layer)."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    m_spin = re.search(r"@keyframes\s+spin\b", body)
    assert m_spin, "@layer base must declare @keyframes spin (PR 3c-d.2)"
    for kf_name in REMAINING_KEYFRAMES_3C_E1:
        m = re.search(r"@keyframes\s+" + re.escape(kf_name) + r"\b", body)
        assert m, (
            f"@layer base must declare @keyframes {kf_name} (PR 3c-e1.1)"
        )
        assert m.start() > m_spin.start(), (
            f"@keyframes {kf_name} ({m.start()}) MUST appear AFTER "
            f"@keyframes spin ({m_spin.start()}) in @layer base "
            f"(PR 3c-e1.2 source order)"
        )


# ---- 3c-e1.2 — keyframe content parity (each keyframe has its identifying frame) ----

def test_remaining_keyframes_have_identifying_frames():
    """3c-e1.2 — content parity: each remaining ``@keyframes`` MUST
    carry its identifying transform / opacity / box-shadow signature
    from the legacy ``web/index.html`` cascade so the React cutover's
    animation parity stays intact."""
    body = _block(_read(GLOBALS_CSS), "@layer base")
    assert body, "globals.css must declare an @layer base { ... } block"
    # detail-card-enter: opacity 0 → 1, translateY(-8px) → 0, scale(0.995) → 1.
    rule = _rule(body, "@keyframes detail-card-enter")
    assert rule, "@keyframes detail-card-enter missing (PR 3c-e1.1)"
    assert re.search(r"opacity\s*:\s*0\b", rule), (
        "@keyframes detail-card-enter must start at opacity: 0 (PR 3c-e1.2)"
    )
    assert re.search(r"translateY\(\s*-8px\s*\)", rule), (
        "@keyframes detail-card-enter must translateY(-8px) (PR 3c-e1.2)"
    )
    # detail-card-leave: opacity 1 → 0, translateY(0) → -6px.
    rule = _rule(body, "@keyframes detail-card-leave")
    assert rule, "@keyframes detail-card-leave missing (PR 3c-e1.1)"
    assert re.search(r"opacity\s*:\s*0\b", rule), (
        "@keyframes detail-card-leave must end at opacity: 0 (PR 3c-e1.2)"
    )
    assert re.search(r"translateY\(\s*-6px\s*\)", rule), (
        "@keyframes detail-card-leave must translateY(-6px) (PR 3c-e1.2)"
    )
    # search-pulse-anim: 0% / 100% box-shadow rgba(29, 126, 169, …).
    rule = _rule(body, "@keyframes search-pulse-anim")
    assert rule, "@keyframes search-pulse-anim missing (PR 3c-e1.1)"
    assert re.search(r"rgba\(\s*29\s*,\s*126\s*,\s*169\s*,\s*0\.55\s*\)", rule), (
        "@keyframes search-pulse-anim must start at rgba(29, 126, 169, 0.55) (PR 3c-e1.2)"
    )
    # toast-slide-in: opacity 0 → 1, translate(-50%, 8px) → 0.
    rule = _rule(body, "@keyframes toast-slide-in")
    assert rule, "@keyframes toast-slide-in missing (PR 3c-e1.1)"
    assert re.search(r"translate\(\s*-50%\s*,\s*8px\s*\)", rule), (
        "@keyframes toast-slide-in must translate(-50%, 8px) (PR 3c-e1.2)"
    )


# ---- 3c-e1.3 — byte-size budget (≤ 400 LoC delta per PR cumulative) ----------

def test_globals_css_byte_size_within_3c_e1_budget():
    """3c-e1.3 — byte-size budget: PR 3c-e1's ``src/app/globals.css``
    delta MUST stay within the 400-line per-PR review budget (the
    project's hard ceiling for any single sub-PR). Computed via git
    diff against the 3c-e1 base branch (PR 3c-d
    `feat/complete-taxa-frontend-migration-06-3c-d`). The spec budgets
    ~40 LoC for the alias + remaining-keyframes slice; the cumulative
    delta MUST NOT exceed 400 LoC."""
    import subprocess
    base = "feat/complete-taxa-frontend-migration-06-3c-d"
    # Use --numstat to count inserted/removed lines for globals.css only.
    result = subprocess.run(
        ["git", "diff", "--numstat", base, "--", "src/app/globals.css"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(
            f"git diff against {base!r} failed — base branch unavailable "
            f"in this checkout: {result.stderr.strip()}"
        )
    numstat = result.stdout.strip()
    if not numstat:
        pytest.skip(f"no diff against {base!r} (base branch not ancestor)")
    added, removed, _path = numstat.split()
    delta = int(added) + int(removed)
    assert delta <= 400, (
        f"PR 3c-e1 globals.css delta is {delta} lines "
        f"(+{added}/-{removed}) — exceeds the 400-line per-PR review budget"
    )