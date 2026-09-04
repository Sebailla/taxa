"""Taxonomy 5a.2 contract tests — mounted Tree + Breadcrumb (PR 5a.2).

Pins slice 5a.2: React hook + presentation components + barrels +
minimal AppShell page mount. The per-row kebab is the REAL `Kebab`
menu (PR 5a.4) backed by the `useKebab` local-state hook — `KebabStub`
(5a.2 inert glyph) is relegated to a backward-compat barrel re-export
and is no longer mounted by page.tsx. The page renders `DetailPanel`
(5a.3) instead of the `TaxonDetailPlaceholder` that 5a.2 shipped.
Predecessor 5a.1 contracts stay byte-identical.
"""
from __future__ import annotations
import re, shutil, subprocess
from pathlib import Path
import pytest

R = Path(__file__).resolve().parent.parent
T = R / "src" / "modules" / "taxonomy"
APP = T / "application" / "useTaxonTree.ts"
HOOK = T / "application" / "useTaxonTreeHook.ts"
PRES = T / "presentation"
TREE, BREAD = PRES / "Tree.tsx", PRES / "Breadcrumb.tsx"
KEBAB, USE_KEBAB = PRES / "Kebab.tsx", PRES / "useKebab.ts"
DETAIL = PRES / "DetailPanel.tsx"
PRES_IDX, BARREL, PAGE = PRES / "index.ts", T / "index.ts", R / "src" / "app" / "page.tsx"
COMPONENTS = ("Tree", "Breadcrumb", "Kebab", "DetailPanel")


@pytest.mark.parametrize("path", [HOOK, TREE, BREAD, KEBAB, USE_KEBAB, DETAIL, PRES_IDX])
def test_files_present(path: Path) -> None:
    assert path.is_file(), f"missing {path} (PR 5a.2 + 5a.3 + 5a.4 surface)"

@pytest.mark.parametrize("name", COMPONENTS)
def test_both_barrels_reexport(name: str) -> None:
    for f, label in ((PRES_IDX, "presentation/index.ts"),
                     (BARREL, "taxonomy/index.ts")):
        assert re.search(rf"\b{name}\b", f.read_text()), \
            f"{label} must re-export {name!r}"

def test_useTaxonTree_has_react_hook() -> None:
    text = HOOK.read_text()
    assert re.search(r"""from\s+["']react["']""", text) and "useState" in text
    assert re.search(r"export\s+function\s+useTaxonTree\b", text)
    # 5a.1 contract: framework-free useTaxonTree.ts stays pure.
    app_text = APP.read_text()
    for tok in ("loadTaxonTree", "buildBreadcrumb", "TaxonTreeNode",
                "BreadcrumbViewModel"):
        assert tok in app_text, f"predecessor {tok!r} must stay byte-identical"
    assert '"react"' not in app_text and "'react'" not in app_text

def test_kebab_has_real_menu_body() -> None:
    """PR 5a.4 lands the real kebab menu in `Kebab.tsx`; `KebabStub` is
    backward-compat only and is no longer mounted by page.tsx. Pin the
    real menu's trigger + label so the e2e harness keeps targeting the
    right selector (the e2e + screenshot corpus relies on these data-
    actions to find the kebab + the `Search online` item).
    """
    text = KEBAB.read_text()
    assert re.search(r'data-action=["\']toggle-kebab["\']', text), \
        "Kebab.tsx must stamp data-action=\"toggle-kebab\" on the trigger"
    assert "Search online" in text, \
        "Kebab.tsx must render the literal label \"Search online\""
    # `kebab-menu` is the CSS class (PR 3c-b); source defines it via the
    # `KEbab_MENU_CLASS` constant so a literal `.kebab-menu` substring
    # won't appear — assert the constant + the menu container's className
    # bind instead.
    assert re.search(r'KEbab_MENU_CLASS\s*=\s*["\']kebab-menu["\']', text), \
        "Kebab.tsx must declare KEbab_MENU_CLASS = \"kebab-menu\""
    assert re.search(r'\$\{KEbab_MENU_CLASS\}\s+open', text), \
        "Kebab.tsx must bind the menu className with `${KEbab_MENU_CLASS} open`"

def test_page_mounts_presentation_via_barrel() -> None:
    text = PAGE.read_text()
    assert re.search(r"""from\s+["']@taxa/taxonomy["']""", text)
    for tok in COMPONENTS:
        assert tok in text, f"page.tsx must reach {tok} via the barrel"

def test_presentation_layer_children_are_valid() -> None:
    allowed = {".gitkeep", "index.ts", "Tree.tsx", "Breadcrumb.tsx",
               "Kebab.tsx", "useKebab.ts",
               "KebabStub.tsx", "TaxonDetailPlaceholder.tsx",
               "DetailPanel.tsx", "FolderTabStub.tsx", "OverviewTab.tsx",
               "SearchTabStub.tsx", "TabStrip.tsx"}
    extra = {p.name for p in PRES.iterdir()} - allowed
    assert not extra

# Type-check witness — tmp tsconfig + sibling-worktree @types. Skips
# when `tsc` or sibling types are unavailable.
_SIBLINGS = ("/Users/sebailla/Developer/taxa-worktrees/complete-taxa-frontend-migration-13-5a-1-domain-api", "/Users/sebailla/Developer/taxa-worktrees/complete-taxa-frontend-migration-12-4b", "/Users/sebailla/Developer/taxa-worktrees/complete-taxa-frontend-migration-11-4a")


@pytest.fixture(scope="module")
def tsc_rc(tmp_path_factory) -> int:
    bin_path = shutil.which("tsc")
    if bin_path is None:
        pytest.skip("tsc not on PATH")
    type_root = next((Path(s) / "node_modules" / "@types" for s in _SIBLINGS
                      if (Path(s) / "node_modules" / "@types").is_dir()), None)
    if type_root is None:
        pytest.skip("no sibling @types")
    tmp = tmp_path_factory.mktemp("tsc")
    cfg = tmp / "tsconfig.json"
    sources = ",".join(f'"{p}"' for p in [APP, HOOK, TREE, BREAD, KEBAB, DETAIL,
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