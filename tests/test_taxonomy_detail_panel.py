"""Taxonomy 5a.3 contract tests — DetailPanel + Overview + local TabStrip.

Pins 5a.3: DetailPanel shell with a ["Overview", "Search", "Folder"] tab
strip (local activation, fixed order, three siblings always reachable,
Overview always visible) plus Overview body. Real Kebab force-Search
(5a.4) and real Search/Folder bodies (5b) are intentionally absent.
"""
from __future__ import annotations
import re, shutil, subprocess
from pathlib import Path
import pytest

R = Path(__file__).resolve().parent.parent
T = R / "src" / "modules" / "taxonomy"
PRES = T / "presentation"
TABSTRIP = PRES / "TabStrip.tsx"
DETAIL = PRES / "DetailPanel.tsx"
OVERVIEW = PRES / "OverviewTab.tsx"
SEARCH_STUB = PRES / "SearchTabStub.tsx"
FOLDER_STUB = PRES / "FolderTabStub.tsx"
PRES_IDX = PRES / "index.ts"
BARREL = T / "index.ts"
PAGE = R / "src" / "app" / "page.tsx"
NEW_COMPONENTS = ("TabStrip", "DetailPanel", "OverviewTab",
                  "SearchTabStub", "FolderTabStub")


# --- file presence + barrel re-export --------------------------------

@pytest.mark.parametrize("path", [TABSTRIP, DETAIL, OVERVIEW,
                                  SEARCH_STUB, FOLDER_STUB])
def test_files_present(path: Path) -> None:
    assert path.is_file(), f"missing {path} (PR 5a.3)"


@pytest.mark.parametrize("name", NEW_COMPONENTS)
def test_both_barrels_reexport(name: str) -> None:
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
    text = TABSTRIP.read_text()
    assert re.search(r"data-tab\s*=\s*\{tab\.label\}", text), \
        "TabStrip must stamp data-tab={tab.label} (CSS contract)"
    assert re.search(r'role\s*=\s*["\']tab["\']', text), \
        "TabStrip must set role=\"tab\" for the a11y harness"
    assert "active" in text and "aria-pressed" in text, \
        "TabStrip must apply .active + aria-pressed to the selected button"


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
    ternary so only one body mounts at a time."""
    text = DETAIL.read_text()
    for key, body in (("overview", "OverviewTab"),
                      ("search", "SearchTabStub"),
                      ("folder", "FolderTabStub")):
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


@pytest.mark.parametrize("stub,cls", [(SEARCH_STUB, "search-tab"),
                                     (FOLDER_STUB, "folder-tab")])
def test_search_and_folder_stubs_use_correct_css_class(stub: Path,
                                                     cls: str) -> None:
    text = stub.read_text()
    assert re.search(rf'className=["\'][^"\']*{cls}', text), \
        f"{stub.name} must use the .{cls} CSS selector (PR 3c-c)"


# --- presentation layer children + type check ------------------------

def test_presentation_layer_children_are_valid() -> None:
    allowed = {".gitkeep", "index.ts", "Tree.tsx", "Breadcrumb.tsx",
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
    sources = ",".join(f'"{p}"' for p in [TABSTRIP, DETAIL, OVERVIEW,
                                            SEARCH_STUB, FOLDER_STUB,
                                            PRES_IDX, BARREL, PAGE])
    cfg.write_text(
        '{"compilerOptions":{"target":"ES2022","module":"ESNext",'
        '"moduleResolution":"Bundler","jsx":"react-jsx",'
        '"lib":["ES2022","DOM","DOM.Iterable"],"skipLibCheck":true,'
        '"esModuleInterop":true,"strict":true,"noEmit":true,'
        f'"typeRoots":["{type_root}"],'
        f'"paths":{{"@taxa/taxonomy":["{T}"]}}}},'
        f'"include":[{sources}]}}'
    )
    proc = subprocess.run([bin_path, "--noEmit", "-p", str(cfg)],
                          cwd=str(R), capture_output=True, text=True,
                          check=False, timeout=120)
    if proc.returncode != 0:
        pytest.fail(f"tsc failed (rc={proc.returncode}).\nstderr:\n"
                    f"{proc.stderr[-1500:]}")
    return proc.returncode


def test_taxonomy_module_type_checks(tsc_rc: int) -> None:
    assert tsc_rc == 0