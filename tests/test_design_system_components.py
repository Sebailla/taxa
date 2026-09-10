"""Phase 3c-iv-barrel design-system `<Icon>` + `<Button>` contract tests.

Pins PR 3c-iv-barrel (openspec/changes/complete-taxa-frontend-migration/tasks.md
§"Phase 3c-iv-barrel"). File-grep based so the test seam matches
`tests/test_design_system_tab_strip.py`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
DS = REPO / "src" / "modules" / "design-system"
DS_PRES = DS / "presentation"
DS_ICON = DS_PRES / "Icon.tsx"
DS_BUTTON = DS_PRES / "Button.tsx"
DS_PRES_INDEX = DS_PRES / "index.ts"
DS_BARREL = DS / "index.ts"
DS_INFRA_INDEX = DS / "infrastructure" / "index.ts"

# Frozen Material Symbols Outlined glyph catalogue (must stay symmetric
# with the `IconName` literal union in `Icon.tsx`).
FROZEN_GLYPHS: tuple[str, ...] = (
    "search", "folder_open", "folder", "chevron_right", "expand_more",
    "close", "settings", "help", "science", "science_off", "download",
)


def test_required_files_exist() -> None:
    """Icon.tsx + Button.tsx + infrastructure/index.ts must land."""
    for path in (DS_ICON, DS_BUTTON, DS_INFRA_INDEX):
        assert path.is_file(), f"missing {path.relative_to(REPO)}"


def test_icon_exports_required_symbols() -> None:
    """Icon must export `Icon` + `IconName` + `IconProps`."""
    src = DS_ICON.read_text(encoding="utf-8")
    for tok in ("Icon", "IconName", "IconProps"):
        assert re.search(rf"export\b[\s\S]{{0,40}}\b{tok}\b", src) \
               or re.search(rf"export\s+(?:type\s+|interface\s+)?\b{tok}\b", src), \
            f"design-system Icon must export {tok!r}"


def test_icon_name_type_accepts_every_frozen_glyph() -> None:
    """Every frozen glyph MUST appear in `IconName` so a typo at the
    call site is a compile-time error."""
    src = DS_ICON.read_text(encoding="utf-8")
    missing = [g for g in FROZEN_GLYPHS if f'"{g}"' not in src]
    assert not missing, f"IconName union is missing frozen glyphs: {missing!r}"


def test_icon_renders_span_with_glyph_text() -> None:
    """`<Icon>` renders `<span class="material-symbols-outlined">` with
    `{name}` as text content (Material Symbols Outlined is a text
    ligature) so the existing `globals.css` rules keep matching."""
    src = DS_ICON.read_text(encoding="utf-8")
    assert re.search(r"<span\b", src)
    assert re.search(r"[\"']material-symbols-outlined[\"']", src)
    assert "{name}" in src


def test_icon_is_accessible() -> None:
    """Icon accepts `className?` + `aria-label?`. When labelled, it
    promotes to `role="img"`. Default decorative state: `aria-hidden="true"`."""
    src = DS_ICON.read_text(encoding="utf-8")
    assert re.search(r"\bclassName\??\s*:\s*string\b", src)
    assert re.search(r"[\"']?aria-label[\"']?\s*\??\s*:\s*string\b", src)
    assert re.search(r'role\s*=\s*[\'"]img[\'"]', src)
    assert re.search(r'aria-hidden\s*=\s*[\'"]true[\'"]', src)


def test_button_exports_required_symbols() -> None:
    """Button must export `Button` + `ButtonProps`."""
    src = DS_BUTTON.read_text(encoding="utf-8")
    for tok in ("Button", "ButtonProps"):
        assert re.search(rf"export\b[\s\S]{{0,40}}\b{tok}\b", src) \
               or re.search(rf"export\s+(?:type\s+|interface\s+)?\b{tok}\b", src), \
            f"design-system Button must export {tok!r}"


def test_button_defaults_type_to_button() -> None:
    """`<Button>` MUST default `type="button"`. The native `<button>`
    defaults to `type="submit"` inside a `<form>` — a top-5 React a11y
    footgun."""
    src = DS_BUTTON.read_text(encoding="utf-8")
    assert re.search(
        r"type\??\s*:\s*[\"']button[\"']\s*\|\s*[\"']submit[\"']\s*\|\s*[\"']reset[\"']",
        src,
    ), "Button must declare `type?: 'button' | 'submit' | 'reset'`"
    assert re.search(r"\btype\s*=\s*[\"']button[\"']", src)


def test_button_accepts_canonical_props() -> None:
    """Canonical native-button contract: `onClick` + `disabled` +
    `children`. Native spread handles `aria-label` / `data-*`."""
    src = DS_BUTTON.read_text(encoding="utf-8")
    for tok in ("onClick", "disabled", "children"):
        assert tok in src, f"Button must accept the {tok!r} prop"


def test_button_renders_fex_snippet_btn_class() -> None:
    """`<Button>` stamps `.fex-snippet-btn` so the existing
    `.research-explorer .fex-snippet-btn` / `:hover` / `:disabled`
    rules keep matching."""
    assert re.search(r"[\"']fex-snippet-btn[\"']", DS_BUTTON.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "path,tokens",
    [
        (DS_PRES_INDEX, ("Icon", "Button", "IconName", "IconProps", "ButtonProps")),
        (DS_INFRA_INDEX, ("Icon", "Button")),
        (DS_BARREL, ("Icon", "Button", "IconName", "IconProps", "ButtonProps",
                     "TabStrip", "TabDefinition", "TabStripProps")),
    ],
    ids=["presentation-barrel", "infrastructure-barrel", "public-barrel"],
)
def test_barrel_reexports_expected_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    """Every barrel MUST re-export the expected token set so consumers
    reach Icon / Button / TabStrip via `@taxa/design-system`."""
    src = path.read_text(encoding="utf-8")
    missing = [t for t in tokens if t not in src]
    assert not missing, f"{path.relative_to(REPO)} missing re-exports: {missing!r}"


def test_public_barrel_preserves_tab_strip_export() -> None:
    """Regression guard — the 5b.4 TabStrip export MUST stay in the
    public barrel. 3c-iv-barrel is additive, never destructive."""
    src = DS_BARREL.read_text(encoding="utf-8")
    for tok in ("TabStrip", "TabDefinition", "TabStripProps"):
        assert tok in src, f"public barrel must keep {tok!r}"
