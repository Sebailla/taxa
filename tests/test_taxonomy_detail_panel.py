"""Taxonomy 5a.3 + 5a.4 contract tests — DetailPanel + Overview + Kebab.

Pins 5a.3: DetailPanel shell with a ["Overview", "Search", "Folder"] tab
strip (local activation, fixed order, three siblings always reachable,
Overview always visible) plus Overview body.

Pins 5a.4: real Kebab menu per row (data-action="toggle-kebab" trigger +
"Search online" item with data-action="open-searches"); DetailPanel
accepts a force-tab contract (Search online on a top-level taxon MUST
NOT land on Overview). Real Search/Folder bodies (5b) are intentionally
absent — the in-5a stub still renders.
"""
from __future__ import annotations
import re, shutil, subprocess
from pathlib import Path
import pytest

R = Path(__file__).resolve().parent.parent
T = R / "src" / "modules" / "taxonomy"
PRES = T / "presentation"
DS = R / "src" / "modules" / "design-system"
DS_PRES = DS / "presentation"
DS_TABSTRIP = DS_PRES / "TabStrip.tsx"
DETAIL = PRES / "DetailPanel.tsx"
OVERVIEW = PRES / "OverviewTab.tsx"
KEBAB = PRES / "Kebab.tsx"
USE_KEBAB = PRES / "useKebab.ts"
PRES_IDX = PRES / "index.ts"
BARREL = T / "index.ts"
PAGE = R / "src" / "app" / "page.tsx"
NEW_COMPONENTS = ("TabStrip", "DetailPanel", "OverviewTab")
KEBAB_COMPONENTS = ("Kebab", "useKebab")


# --- file presence + barrel re-export --------------------------------

@pytest.mark.parametrize("path", [DS_TABSTRIP, DETAIL, OVERVIEW])
def test_files_present(path: Path) -> None:
    assert path.is_file(), f"missing {path} (PR 5a.3 / 5b.4)"


@pytest.mark.parametrize("name", NEW_COMPONENTS)
def test_both_barrels_reexport(name: str) -> None:
    # `TabStrip` lives in `@taxa/design-system` (promoted in 5b.4);
    # it does NOT belong in `@taxa/taxonomy`. The taxonomy barrel
    # exposes `DetailPanel` + `OverviewTab` only.
    if name == "TabStrip":
        ds_barrel = (DS / "index.ts").read_text(encoding="utf-8")
        assert re.search(r"\bTabStrip\b", ds_barrel), (
            f"design-system barrel must re-export {name!r}"
        )
        return
    for f, label in ((PRES_IDX, "presentation/index.ts"),
                     (BARREL, "taxonomy/index.ts")):
        assert re.search(rf"\b{name}\b", f.read_text()), \
            f"{label} must re-export {name!r}"


def test_page_mounts_detail_panel_via_barrel() -> None:
    text = PAGE.read_text()
    assert re.search(r"""from\s+["']@taxa/taxonomy["']""", text)
    assert "DetailPanel" in text, "page.tsx must mount DetailPanel (PR 5a.3)"
    assert "TaxonDetailPlaceholder" not in text, \
        "page.tsx must NOT keep TaxonDetailPlaceholder after 5a.3 mount"


# --- TabStrip + DetailPanel contract ---------------------------------

def test_detailpanel_pins_tab_order_overview_search_folder() -> None:
    text = DETAIL.read_text()
    body = re.search(
        r"TABS\s*:\s*readonly\s+TabDefinition\[\][\s\S]*?\](?:\s+as\s+const)?\s*;",
        text)
    assert body is not None, \
        "DetailPanel must declare TABS: readonly TabDefinition[] = [...]"
    src = body.group(0)
    idx_overview = src.find('"Overview"')
    idx_search = src.find('"Search"')
    idx_folder = src.find('"Folder"')
    assert idx_overview != -1 and idx_search != -1 and idx_folder != -1
    assert idx_overview < idx_search < idx_folder, \
        f"must be Overview → Search → Folder; got {src!r}"


def test_tabstrip_emits_data_tab_attribute() -> None:
        # PR 5b.4 promotion: TabStrip moved from
    # `src/modules/taxonomy/presentation/TabStrip.tsx` to
    # `src/modules/design-system/presentation/TabStrip.tsx`. The
    # attribute contract is unchanged (3c-c CSS selectors still match).
        text = DS_TABSTRIP.read_text()
        assert re.search(r"data-tab\s*=\s*\{tab\.label\}", text), \
            "design-system TabStrip must stamp data-tab={tab.label} (CSS contract)"
        assert re.search(r'role\s*=\s*["\']tab["\']', text), \
            "design-system TabStrip must set role=\"tab\" for the a11y harness"
        assert "active" in text and "aria-pressed" in text, \
            "design-system TabStrip must apply .active + aria-pressed to the selected button"


def test_detailpanel_keeps_local_active_tab_state() -> None:
    text = DETAIL.read_text()
    assert "useState" in text, "DetailPanel must use useState"
    tabs = re.search(
        r"TABS\s*:\s*readonly\s+TabDefinition\[\][\s\S]*?\](?:\s+as\s+const)?\s*;",
        text)
    default_block = re.search(r"DEFAULT_TAB_KEY\s*=\s*[\"'](\w+)[\"']", text)
    assert tabs is not None and default_block is not None, \
        "DetailPanel must declare TABS + DEFAULT_TAB_KEY"
    first_key = re.search(r"\{\s*key\s*:\s*[\"'](\w+)[\"']", tabs.group(0))
    assert first_key is not None
    assert default_block.group(1) == first_key.group(1), \
        "DEFAULT_TAB_KEY must match first TABS entry"


def test_detailpanel_renders_all_three_tab_bodies_and_uses_selector() -> None:
    """All three tabs MUST be reachable from every selection; the panel
    uses `.detail-panel` + the harness `data-slot`."""
    text = DETAIL.read_text()
    for tok in ("OverviewTab", "SearchTabStub", "FolderTabStub"):
        assert tok in text, f"DetailPanel must render {tok!r}"
    assert re.search(r'className=["\']detail-panel["\']', text), \
        "DetailPanel must use the .detail-panel CSS selector (PR 3c-b)"
    assert 'data-slot="taxon-detail"' in text, \
        "DetailPanel must keep data-slot=\"taxon-detail\" for the harness"
    assert "selected" in text and "null" in text, \
        "DetailPanel must handle the no-selection branch"


def test_detailpanel_renders_exactly_one_body_per_active_key() -> None:
    """Triangulation: each body MUST be gated by `activeKey === "<key>"`
    ternary so only one body mounts at a time.

    PR 5b.4: the Search / Folder bodies are the `SearchTab` /
    `FolderTab` components from `@taxa/research` (not the
    obsolete `SearchTabStub` / `FolderTabStub` stubs)."""
    text = DETAIL.read_text()
    for key, body in (("overview", "OverviewTab"),
                      ("search", "SearchTab"),
                      ("folder", "FolderTab")):
        pat = re.compile(
            rf"activeKey\s*===\s*[\"']{key}[\"']\s*\?\s*<\s*{body}")
        assert pat.search(text), \
            f"DetailPanel must gate {body!r} behind activeKey === '{key}'"


# --- Overview + stub contract ----------------------------------------

def test_overview_tab_uses_overview_tab_class_and_taxonrecord_fields() -> None:
    text = OVERVIEW.read_text()
    assert re.search(r'className=["\']overview-tab["\']', text), \
        "OverviewTab must use the .overview-tab CSS selector (PR 3c-b)"
    for tok in ("scientific_name", "rank", "status",
                "is_extinct", "species_count"):
        assert tok in text, \
            f"OverviewTab must surface the {tok!r} field of TaxonRecord"


@pytest.mark.parametrize("body,cls", [
    ("SearchTab", "search-tab"),
    ("FolderTab", "folder-tab"),
])
def test_search_and_folder_bodies_use_correct_css_class(body: str, cls: str) -> None:
        """PR 5b.4: the SearchTab / FolderTab BODIES (not stubs) live in
        `src/modules/research/presentation/`. They ride the production
        `.search-tab` / `.folder-tab` CSS selectors 3c-c pinned for the
        detail-panel slots."""
        body_path = (R / "src" / "modules" / "research" / "presentation"
                     / f"{body}.tsx")
        assert body_path.is_file(), (
            f"missing {body_path.relative_to(R)} — PR 5b.4 must land "
            f"the real body"
        )
        text = body_path.read_text()
        assert re.search(rf'className=["\'][^"\']*{cls}', text), \
            f"{body}.tsx must use the .{cls} CSS selector (PR 3c-c)"


# --- 5a.4 contracts ---------------------------------------------------
#
# 5a.4 introduces a real Kebab menu (replacing the inert KebabStub)
# plus a force-tab contract on DetailPanel so that clicking
# `Search online` in the kebab menu forces the Search tab active
# even for top-level taxa (the regression that lands on Overview
# by default).

@pytest.mark.parametrize("path", [KEBAB, USE_KEBAB])
def test_kebab_files_present(path: Path) -> None:
    assert path.is_file(), f"missing {path} (PR 5a.4)"


@pytest.mark.parametrize("name", KEBAB_COMPONENTS)
def test_both_barrels_reexport_kebab(name: str) -> None:
    for f, label in ((PRES_IDX, "presentation/index.ts"),
                     (BARREL, "taxonomy/index.ts")):
        assert re.search(rf"\b{name}\b", f.read_text()), \
            f"{label} must re-export {name!r} (PR 5a.4)"


def test_page_mounts_real_kebab_via_barrel() -> None:
    text = PAGE.read_text()
    assert re.search(r"""from\s+["']@taxa/taxonomy["']""", text), \
        "page.tsx must mount via @taxa/taxonomy barrel"
    assert "Kebab" in text and "KebabStub" not in text, \
        "page.tsx must mount the real Kebab (5a.4), NOT the inert KebabStub"


def test_kebab_emits_toggle_kebab_trigger_with_menuitem() -> None:
    """The kebab menu MUST expose:
      - data-action="toggle-kebab" (the per-row trigger)
      - data-action="open-searches" + label "Search online"
        (the menu item that drives the Search tab activation).
    Both reuse the legacy data-action values so the e2e + screenshot
    harness keeps matching them without new branches.
    """
    text = KEBAB.read_text()
    assert re.search(r'data-action=["\']toggle-kebab["\']', text), \
        "Kebab.tsx must stamp data-action=\"toggle-kebab\" on the trigger"
    assert re.search(r'data-action=["\']open-searches["\']', text), \
        "Kebab.tsx must stamp data-action=\"open-searches\" on the Search online item"
    assert "Search online" in text, \
        "Kebab.tsx must render the literal label \"Search online\""


def test_kebab_uses_local_open_state_via_usekebab_hook() -> None:
    """The kebab menu opens on click and closes on outside-click /
    ESC. State MUST live in `useKebab` (the new 5a.4 hook) — not as
    ad-hoc useState inside Kebab.tsx, which would make the menu
    impossible to test in isolation and would duplicate the legacy
    `web/nav.js` close-on-outside-click logic."""
    kebab_text = KEBAB.read_text()
    hook_text = USE_KEBAB.read_text()
    assert "useKebab" in kebab_text, \
        "Kebab.tsx must consume useKebab for open/close state"
    assert re.search(r"export\s+(?:default\s+)?function\s+useKebab\b", hook_text), \
        "useKebab.ts must export function useKebab"
    assert re.search(r"\bisOpen\b", hook_text) and "useState" in hook_text, \
        "useKebab.ts must own isOpen state via useState"


def test_detailpanel_exposes_force_search_contract() -> None:
    """DetailPanel MUST accept a force-tab prop so the kebab's
    `Search online` callback can switch the active tab to Search
    even for taxa where the default would be Overview.

    The contract is intentionally minimal: a single optional prop
    that, when truthy + changing, snaps the active tab to a
    caller-supplied key. 5b promotes the TabStrip to design-system
    and may replace this seam; 5a.4 only requires that it exists.
    """
    text = DETAIL.read_text()
    # The prop must be optional and shaped so callers can hand
    # `true` (force Search) without juggling an extra arg.
    assert re.search(r"force\s*OpenSearch\b", text, re.IGNORECASE), (
        "DetailPanel.tsx must declare a force-search prop "
        "(e.g. forceOpenSearch / forceSearch) so the kebab can "
        "snap the active tab to Search — even for taxa whose "
        "default would be Overview"
    )
    # DetailPanel must watch the prop and snap when it changes.
    assert "useEffect" in text, (
        "DetailPanel.tsx must use useEffect to react to the "
        "force-search prop changing (activeTab snaps to 'search')"
    )


def test_page_wires_kebab_searchonline_to_detailpanel_force_search() -> None:
    """page.tsx is the only place the kebab's Search online callback
    can reach DetailPanel (DetailPanel keeps state local per 5a.3
    design). The page MUST hand the kebab a callback that updates
    DetailPanel's force-search prop — otherwise the kebab button
    is a no-op and 5a.4's regression is closed in name only."""
    text = PAGE.read_text()
    assert re.search(r"onSearchOnline|openSearches|searchOnline", text), \
        "page.tsx must wire Kebab's onSearchOnline callback"
    assert re.search(r"force\s*OpenSearch", text, re.IGNORECASE), \
        "page.tsx must hand DetailPanel a force-search prop value"


def test_kebab_carries_data_taxon_id_for_open_searches_targeting() -> None:
    """The Search online menu item MUST carry data-taxon-id so the
    e2e harness (test_search_online_force_search.py + the legacy
    screenshot corpus) can locate it from a parent taxon-id."""
    text = KEBAB.read_text()
    # Find the open-searches button + assert data-taxon-id rides along.
    m = re.search(
        r"data-action\s*=\s*[\"']open-searches[\"'][\s\S]{0,300}?</button",
        text)
    assert m is not None, \
        "Kebab.tsx must render an open-searches <button> ..."
    snippet = m.group(0)
    assert re.search(r"data-taxon-id\s*=\s*\{", snippet), \
        "open-searches button must carry data-taxon-id (parent row's id)"


# --- presentation layer children + type check ------------------------

def test_presentation_layer_children_are_valid() -> None:
    allowed = {".gitkeep", "index.ts", "Tree.tsx", "Breadcrumb.tsx",
               "Kebab.tsx", "useKebab.ts",
               "KebabStub.tsx", "TaxonDetailPlaceholder.tsx",
               "TabStrip.tsx", "DetailPanel.tsx", "OverviewTab.tsx",
               "SearchTabStub.tsx", "FolderTabStub.tsx"}
    extra = {p.name for p in PRES.iterdir()} - allowed
    assert not extra, f"unexpected files in presentation/: {sorted(extra)}"


_SIBLINGS = ("/Users/sebailla/Developer/taxa-worktrees/complete-taxa-frontend-migration-13-5a-1-domain-api",
             "/Users/sebailla/Developer/taxa-worktrees/complete-taxa-frontend-migration-12-4b",
             "/Users/sebailla/Developer/taxa-worktrees/complete-taxa-frontend-migration-11-4a")


def _find_tsc() -> str | None:
    path = shutil.which("tsc")
    if path is not None:
        return path
    for sibling in _SIBLINGS:
        candidate = Path(sibling) / "node_modules" / "typescript" / "bin" / "tsc"
        if candidate.is_file():
            return str(candidate)
    return None


@pytest.fixture(scope="module")
def tsc_rc(tmp_path_factory) -> int:
    bin_path = _find_tsc()
    if bin_path is None:
        pytest.skip("tsc not on PATH and no sibling binary available")
    type_root = next((Path(s) / "node_modules" / "@types" for s in _SIBLINGS
                      if (Path(s) / "node_modules" / "@types").is_dir()), None)
    if type_root is None:
        pytest.skip("no sibling @types")
    tmp = tmp_path_factory.mktemp("tsc")
    cfg = tmp / "tsconfig.json"
    sources = ",".join(f'"{p}"' for p in [DETAIL, OVERVIEW,
                                          KEBAB, USE_KEBAB,
                                          PRES_IDX, BARREL, PAGE])
    cfg.write_text(
        '{"compilerOptions":{"target":"ES2022","module":"ESNext",'
        '"moduleResolution":"Bundler","jsx":"react-jsx",'
        '"lib":["ES2022","DOM","DOM.Iterable"],"skipLibCheck":true,'
        '"esModuleInterop":true,"strict":true,"noEmit":true,'
        f'"typeRoots":["{type_root}"],'
f'"paths":{{'
        f'"@taxa/taxonomy":["{T}"],'
        f'"@taxa/design-system":["{DS}"],'
f'"@taxa/research":["{R / "src" / "modules" / "research"}]"'
        f'}}}},'
        f'"include":[{sources}]}}'
    )
    proc = subprocess.run([bin_path, "--noEmit", "-p", str(cfg)],
                          cwd=str(R), capture_output=True, text=True,
                          check=False, timeout=120)
    if proc.returncode != 0:
        pytest.fail(f"tsc failed (rc={proc.returncode}).\nstdout:\n"
                    f"{proc.stdout[-1500:]}\nstderr:\n"
                    f"{proc.stderr[-1500:]}")
    return proc.returncode


def test_taxonomy_module_type_checks(tsc_rc: int) -> None:
    assert tsc_rc == 0