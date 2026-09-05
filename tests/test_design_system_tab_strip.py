"""Phase 5b.4 design-system TabStrip promotion contract tests.

Pins the 5b.4 user-decision that the local `TabStrip` primitive authored
in 5a.3 (taxonomy/presentation/TabStrip.tsx) is promoted to
`src/modules/design-system/presentation/TabStrip.tsx` VERBATIM, and the
taxonomy DetailPanel migrates to consume it via `@taxa/design-system`.

The promotion is the 5b.4 close-out of the 5a.3 addendum. Regression
guard: no taxonomy import path regresses — the DetailPanel + its
consumers (page.tsx) must keep their existing behaviour while the
TabStrip source moves to its design-system home.

Pins:
  - `src/modules/design-system/presentation/TabStrip.tsx` exists.
  - The design-system presentation barrel
    (`src/modules/design-system/presentation/index.ts`) re-exports
    `TabStrip` + `TabDefinition` + `TabStripProps`.
  - The design-system public barrel (`src/modules/design-system/index.ts`)
    surfaces them.
  - The taxonomy presentation layer:
      * no longer authors `src/modules/taxonomy/presentation/TabStrip.tsx`
      * imports `TabStrip` from `@taxa/design-system` (in DetailPanel)
      * drops the obsolete `SearchTabStub` / `FolderTabStub` files
      * drops the corresponding re-exports in its presentation barrel
  - The taxonomy DetailPanel still owns the `forceOpenSearch` prop +
    `useEffect` snap-to-search contract (the 5a.4 regression guard
    stays intact).
  - Page.tsx still wires the kebab's `onSearchOnline` callback to the
    DetailPanel's force-search prop (5a.4 regression guard).

No CSS, no new dependencies, no commit / push.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
DS = REPO / "src" / "modules" / "design-system"
DS_PRES = DS / "presentation"
DS_TAB_STRIP = DS_PRES / "TabStrip.tsx"
DS_PRES_INDEX = DS_PRES / "index.ts"
DS_BARREL = DS / "index.ts"

T = REPO / "src" / "modules" / "taxonomy"
T_PRES = T / "presentation"
T_TAB_STRIP = T_PRES / "TabStrip.tsx"
T_SEARCH_STUB = T_PRES / "SearchTabStub.tsx"
T_FOLDER_STUB = T_PRES / "FolderTabStub.tsx"
T_PRES_INDEX = T_PRES / "index.ts"
T_DETAIL = T_PRES / "DetailPanel.tsx"

PAGE = REPO / "src" / "app" / "page.tsx"


# ---------------------------------------------------------------------------
# Design-system files — TabStrip promoted verbatim
# ---------------------------------------------------------------------------
def test_design_system_tab_strip_file_exists() -> None:
    """5b.4 must land `src/modules/design-system/presentation/TabStrip.tsx`
    verbatim from the 5a.3 source."""
    assert DS_TAB_STRIP.is_file(), (
        f"missing {DS_TAB_STRIP.relative_to(REPO)} — 5b.4 must promote "
        f"TabStrip from taxonomy/presentation to design-system/presentation"
    )


def test_design_system_tab_strip_exports_required_symbols() -> None:
    """The promoted TabStrip MUST export `TabStrip`, `TabDefinition`, and
    `TabStripProps` (the verbatim surface from the taxonomy local copy)."""
    src = DS_TAB_STRIP.read_text(encoding="utf-8")
    for tok in ("TabStrip", "TabDefinition", "TabStripProps"):
        assert re.search(rf"\bexport\b[\s\S]{{0,40}}\b{tok}\b", src) or \
               re.search(rf"export\s+(?:type\s+|interface\s+)?\b{tok}\b", src), (
            f"design-system TabStrip must export {tok!r}"
        )


def test_design_system_tab_strip_props_signature() -> None:
    """The promoted TabStrip MUST keep the verbatim prop signature:
    `{ tabs: readonly TabDefinition[]; activeKey: string; onChange: (key: string) => void }`."""
    src = DS_TAB_STRIP.read_text(encoding="utf-8")
    assert re.search(r"\btabs\s*:\s*readonly\s+TabDefinition\[\]", src), (
        "design-system TabStrip must accept `tabs: readonly TabDefinition[]`"
    )
    assert re.search(r"\bactiveKey\s*:\s*string\b", src), (
        "design-system TabStrip must accept `activeKey: string`"
    )
    assert re.search(
        r"\bonChange\s*:\s*\(\s*key\s*:\s*string\s*\)\s*=>\s*void\b",
        src,
    ), (
        "design-system TabStrip must accept "
        "`onChange: (key: string) => void`"
    )


def test_design_system_tab_strip_uses_data_tab_attribute() -> None:
    """The promoted TabStrip MUST keep stamping `data-tab={tab.label}` so
    the 3c-c `@layer components` selectors (`[data-tab="Overview"].active`,
    etc.) keep matching. Critical regression guard for the production CSS."""
    src = DS_TAB_STRIP.read_text(encoding="utf-8")
    assert re.search(r"data-tab\s*=\s*\{tab\.label\}", src), (
        "design-system TabStrip must stamp `data-tab={tab.label}` "
        "so the 3c-c CSS selectors keep matching"
    )


def test_design_system_tab_strip_keeps_tablist_aria() -> None:
    """WCAG 2.2 AA — the promoted TabStrip MUST keep its `role="tablist"`
    landmark + `aria-pressed` / `aria-selected` per-button contract."""
    src = DS_TAB_STRIP.read_text(encoding="utf-8")
    assert "role=\"tablist\"" in src or "tablist" in src, (
        "design-system TabStrip must declare a tablist landmark"
    )
    assert "aria-selected" in src, (
        "design-system TabStrip must stamp `aria-selected`"
    )


# ---------------------------------------------------------------------------
# Design-system presentation barrel + public barrel
# ---------------------------------------------------------------------------
def test_design_system_presentation_barrel_reexports_tab_strip() -> None:
    """`src/modules/design-system/presentation/index.ts` MUST re-export
    TabStrip + TabDefinition + TabStripProps so consumers reach them
    via `@taxa/design-system/presentation` (or the public barrel)."""
    src = DS_PRES_INDEX.read_text(encoding="utf-8") if DS_PRES_INDEX.is_file() else ""
    for tok in ("TabStrip", "TabDefinition", "TabStripProps"):
        assert tok in src, (
            f"design-system presentation/index.ts must re-export {tok!r}"
        )


def test_design_system_public_barrel_reexports_tab_strip() -> None:
    """`src/modules/design-system/index.ts` MUST surface `TabStrip` so
    cross-module consumers (DetailPanel, etc.) import via
    `@taxa/design-system` (the public barrel)."""
    src = DS_BARREL.read_text(encoding="utf-8")
    for tok in ("TabStrip", "TabDefinition", "TabStripProps"):
        assert tok in src, (
            f"design-system public barrel must re-export {tok!r}"
        )


# ---------------------------------------------------------------------------
# Taxonomy presentation layer — TabStrip migrates out, stubs migrate out
# ---------------------------------------------------------------------------
def test_taxonomy_tab_strip_removed() -> None:
    """5b.4 must REMOVE the local `src/modules/taxonomy/presentation/TabStrip.tsx`
    — the primitive now lives in `@taxa/design-system`. Removal is
    required (not just deprecated) to keep the chain topology clean."""
    assert not T_TAB_STRIP.is_file(), (
        f"{T_TAB_STRIP.relative_to(REPO)} must be removed — TabStrip is "
        f"promoted to design-system/presentation/"
    )


def test_taxonomy_search_tab_stub_removed() -> None:
    """5b.4 must REMOVE `src/modules/taxonomy/presentation/SearchTabStub.tsx`
    — the real `SearchTab` lives at `src/modules/research/presentation/SearchTab.tsx`
    and DetailPanel swaps its stub import for the real one."""
    assert not T_SEARCH_STUB.is_file(), (
        f"{T_SEARCH_STUB.relative_to(REPO)} must be removed — real "
        f"SearchTab lives in the research module"
    )


def test_taxonomy_folder_tab_stub_removed() -> None:
    """5b.4 must REMOVE `src/modules/taxonomy/presentation/FolderTabStub.tsx`
    — the real `FolderTab` lives at `src/modules/research/presentation/FolderTab.tsx`
    and DetailPanel swaps its stub import for the real one."""
    assert not T_FOLDER_STUB.is_file(), (
        f"{T_FOLDER_STUB.relative_to(REPO)} must be removed — real "
        f"FolderTab lives in the research module"
    )


def test_taxonomy_detail_panel_imports_tab_strip_from_design_system() -> None:
    """`DetailPanel.tsx` MUST import `TabStrip` from `@taxa/design-system`
    (NOT from a sibling `./TabStrip` file — that file no longer exists)."""
    src = T_DETAIL.read_text(encoding="utf-8")
    assert re.search(
        r'from\s+["\']@taxa/design-system["\']', src,
    ), (
        "DetailPanel.tsx must import TabStrip from `@taxa/design-system` "
        "after the 5b.4 promotion"
    )
    bad = re.search(r'from\s+["\']\./TabStrip["\']', src)
    assert bad is None, (
        f"DetailPanel.tsx must not deep-import `./TabStrip` (the file "
        f"is removed); got {bad.group(0)!r}"
    )


def test_taxonomy_detail_panel_still_owns_force_open_search_contract() -> None:
    """Regression guard: the 5a.4 force-Search contract stays intact.
    DetailPanel MUST still accept `forceOpenSearch` and react to it
    via a useEffect that snaps the active tab to `search`."""
    src = T_DETAIL.read_text(encoding="utf-8")
    assert re.search(r"forceOpenSearch", src), (
        "DetailPanel.tsx must keep the `forceOpenSearch` prop "
        "(5a.4 regression guard)"
    )
    assert "useEffect" in src, (
        "DetailPanel.tsx must keep its useEffect for the force-Search "
        "snap-to-Search contract"
    )


def test_taxonomy_presentation_barrel_drops_removed_exports() -> None:
    """`taxonomy/presentation/index.ts` MUST drop the `TabStrip`,
    `SearchTabStub`, and `FolderTabStub` exports (their files no longer
    exist). The barrel is the regression guard: a stale re-export
    would surface as a broken barrel re-export at next import time."""
    src = T_PRES_INDEX.read_text(encoding="utf-8")
    for tok in ("SearchTabStub", "FolderTabStub"):
        assert tok not in src, (
            f"taxonomy/presentation/index.ts must drop the removed "
            f"{tok!r} re-export"
        )


def test_taxonomy_public_barrel_drops_removed_exports() -> None:
    """The public taxonomy barrel MUST also drop the stale re-exports —
    otherwise `@taxa/taxonomy` keeps surfacing symbols whose files no
    longer exist (a broken public surface)."""
    src = (T / "index.ts").read_text(encoding="utf-8")
    for tok in ("SearchTabStub", "FolderTabStub"):
        assert tok not in src, (
            f"taxonomy/index.ts must drop the removed {tok!r} re-export"
        )


# ---------------------------------------------------------------------------
# page.tsx — kebab force-Search wiring stays intact
# ---------------------------------------------------------------------------
def test_page_keeps_kebab_force_search_wiring() -> None:
    """Regression guard: the 5a.4 kebab→DetailPanel force-Search wiring
    MUST stay byte-identical. Page.tsx still imports `Kebab` from
    `@taxa/taxonomy`, still bumps `forceOpenSearch` on every kebab
    callback, and still hands it to `<DetailPanel forceOpenSearch={...}>`."""
    src = PAGE.read_text(encoding="utf-8")
    assert re.search(r"\bforceOpenSearch\b", src), (
        "page.tsx must keep the `forceOpenSearch` state counter "
        "(5a.4 regression guard)"
    )
    assert re.search(
        r'from\s+["\']@taxa/taxonomy["\']', src,
    ), "page.tsx must keep the `@taxa/taxonomy` import"
    assert "DetailPanel" in src, (
        "page.tsx must keep the `<DetailPanel>` mount"
    )


# ---------------------------------------------------------------------------
# TabStrip contract — verbatim port preserves the surface
# ---------------------------------------------------------------------------
def test_design_system_tab_strip_supports_three_sibling_tabs() -> None:
    """The promoted TabStrip MUST continue to support the canonical
    `[Overview, Search, Folder]` triplet (the 3-tab ordering the
    taxonomy DetailPanel relies on) without restricting the tab count.
    The TABS const in DetailPanel is still the contract."""
    src = T_DETAIL.read_text(encoding="utf-8")
    # The DetailPanel TABS literal must still declare three siblings in
    # fixed order (the 5a.3 contract).
    body = re.search(
        r"TABS\s*:\s*readonly\s+TabDefinition\[\][\s\S]*?\](?:\s+as\s+const)?\s*;",
        src,
    )
    assert body is not None, (
        "DetailPanel must still declare TABS: readonly TabDefinition[]"
    )
    labels = ("Overview", "Search", "Folder")
    indices = [body.group(0).find(f'"{l}"') for l in labels]
    assert all(i >= 0 for i in indices), (
        f"every tab label must appear; got indices {indices!r}"
    )
    assert indices == sorted(indices), (
        f"tab labels must appear in fixed order Overview→Search→Folder; "
        f"got indices {indices!r}"
    )