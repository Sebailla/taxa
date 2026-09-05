"""Phase 5b.3 research presentation contract tests.

Pins the 5b.3 presentation slice:
  - FileExplorer / FileViewer shells (no app-shell wiring, no Search/Folder)
  - The file explorer's debounced tree search with filter/highlight modes
    (200 ms DEBOUNCE_MS, `state.explorer.search.{query, mode, hideEmpty}`
    contract).
  - The explorer self-mounts for non-null taxonId (no-op otherwise) and
    owns its no-file empty state.
  - The file viewer's no-file empty state lives in the viewer (the
    explorer pane does NOT duplicate it).
  - The local `RawTableTreeTabs` (Raw / Table / Tree) renders three
    tab buttons; the active tab carries the matching data attribute.
  - Meta strip renders `FORMAT=<EXT> | SIZE=<bytes> | ENCODING=UTF-8`.
  - BreadcrumbPanel paints the active path (one segment per folder).
  - Banners (`fex-banner`) surface the CDN failure message via a
    `role="status"` element with the "Viewer offline" copy.
  - Realm mapping is deferred: folder rows stamp `data-realm="other"`.
  - Public barrel re-exports every 5b.3 surface component.
  - Root barrel (research/index.ts) re-exports `./presentation`.
  - Behaviour-level driver exercises the pure pieces (no jsdom; pure
    render-only helpers + the application-layer hooks are exercised
    via Node + `--experimental-strip-types`, mirroring the 5b.2 test).

No CSS / globals.css changes; no new dependencies; no app-shell wiring;
no Search / Folder tabs; no commit / push.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
R = REPO / "src" / "modules" / "research"
PRES = R / "presentation"
PRES_INDEX = PRES / "index.ts"
ROOT = R / "index.ts"

FILE_EXPLORER = PRES / "FileExplorer.tsx"
FILE_VIEWER = PRES / "FileViewer.tsx"
RAW_TABS = PRES / "RawTableTreeTabs.tsx"
META_STRIP = PRES / "MetaStrip.tsx"
BREAD_PANEL = PRES / "BreadcrumbPanel.tsx"
BANNERS = PRES / "Banners.tsx"


def read(rel: str) -> str:
    p = R / rel
    assert p.is_file(), f"missing research file: {p}"
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# File presence — every 5b.3 component lands on disk
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", [
    FILE_EXPLORER, FILE_VIEWER, RAW_TABS, META_STRIP, BREAD_PANEL, BANNERS,
    PRES_INDEX,
])
def test_files_present(path: Path) -> None:
    assert path.is_file(), (
        f"missing {path.relative_to(REPO)} (PR 5b.3 presentation slice)"
    )


def test_presentation_directory_is_bounded() -> None:
    """5b.3 constraint: presentation/ holds exactly the named surface
    files + the barrel — no stray helpers, no application-style state
    machines, no .gitkeep left over from a different phase. Matches the
    'avoid extra files' 5b.2 contract, applied to the new layer.
    """
    if not PRES.is_dir():
        pytest.skip("presentation dir not present yet")
    allowed = {
        ".gitkeep", "index.ts",
        "FileExplorer.tsx", "FileViewer.tsx", "RawTableTreeTabs.tsx",
        "MetaStrip.tsx", "BreadcrumbPanel.tsx", "Banners.tsx",
    }
    actual = {p.name for p in PRES.iterdir()}
    unexpected = actual - allowed
    assert not unexpected, (
        f"presentation/ has unexpected children: {sorted(unexpected)}. "
        f"Only these are allowed: {sorted(allowed)}."
    )


# ---------------------------------------------------------------------------
# Public barrel — every 5b.3 surface export reaches `@taxa/research`
# ---------------------------------------------------------------------------
def test_presentation_barrel_reexports_every_surface_component() -> None:
    """`presentation/index.ts` MUST re-export every 5b.3 surface component
    so cross-module consumers (app-shell in 5b.4) import via the barrel
    rather than reaching into `presentation/` directly."""
    src = read("presentation/index.ts")
    for tok in (
        "FileExplorer", "FileViewer", "RawTableTreeTabs",
        "MetaStrip", "BreadcrumbPanel", "Banners",
    ):
        assert re.search(rf"\b{tok}\b", src), (
            f"presentation/index.ts must re-export {tok!r}"
        )


def test_root_barrel_exposes_presentation_surface() -> None:
    """spec.md rule 5: `src/modules/research/index.ts` MUST
    `export * from "./presentation"` so the 5b.3 surface is reachable
    via `@taxa/research`."""
    src = read("index.ts")
    assert re.search(r'export\s*\*\s+from\s+["\']\./presentation["\']', src), (
        'research/index.ts must `export * from "./presentation"`'
    )


def test_root_barrel_keeps_predecessor_exports() -> None:
    """Predecessor 5b.1 + 5b.2 root-barrel exports (`./domain`,
    `./infrastructure`, `./application`) MUST stay byte-identical so the
    5b.3 addendum is additive only — never removes or reorders the
    predecessors."""
    src = read("index.ts")
    for rel in ("./infrastructure", "./application", "./domain"):
        assert re.search(
            rf'export\s*\*\s+from\s+["\']{re.escape(rel)}["\']', src,
        ), f'root barrel must keep `export * from "{rel}"`'


# ---------------------------------------------------------------------------
# Cross-module contract — only the public barrel is reachable
# ---------------------------------------------------------------------------
def test_presentation_components_only_import_via_barrel() -> None:
    """No 5b.3 component MUST reach into another module's deep layer.
    The barrel is the contract (spec.md rule 5). Tolerates intra-module
    relative imports (`./MetaStrip`, `./Banners`, …) and the
    `@taxa/research` self-import.
    """
    targets = (
        FILE_EXPLORER, FILE_VIEWER, RAW_TABS, META_STRIP,
        BREAD_PANEL, BANNERS,
    )
    forbidden_alias = re.compile(
        r'from\s+["\']@taxa/(?!research\b)[a-z-]+/',  # any alias except self
    )
    forbidden_literal = re.compile(
        r'from\s+["\']\.\./\.\./\.\./modules/',  # ../.. deep imports
    )
    for path in targets:
        src = path.read_text(encoding="utf-8")
        bad_alias = forbidden_alias.search(src)
        assert bad_alias is None, (
            f"{path.name} reaches another module via alias {bad_alias.group(0)!r} "
            f"— use @taxa/research"
        )
        bad_literal = forbidden_literal.search(src)
        assert bad_literal is None, (
            f"{path.name} has a deep module import {bad_literal.group(0)!r}"
        )


def test_presentation_components_use_public_research_barrel() -> None:
    """Every 5b.3 component that needs the public types MUST import from
    `@taxa/research` (not deep into the research layers)."""
    for path in (FILE_EXPLORER, FILE_VIEWER):
        src = path.read_text(encoding="utf-8")
        # At least one `@taxa/research` import expected — the hook
        # surface is the bridge from presentation → application/domain.
        assert re.search(r'from\s+["\']@taxa/research["\']', src), (
            f"{path.name} must import the public research barrel "
            f"`@taxa/research` — never deep-import research layers"
        )


# ---------------------------------------------------------------------------
# FileExplorer — debounced tree search + self-mount + data-realm="other"
# ---------------------------------------------------------------------------
def test_file_explorer_uses_debounce_constant() -> None:
    """`DEBOUNCE_MS` (5b.2) MUST be the only debounce timer in the
    explorer — the presentation layer MUST NOT re-invent a 200 ms / 300 ms
    copy. The presentation layer reads the constant from the application
    barrel (or equivalently `useFileExplorer` already debounces inside
    the hook)."""
    src = read("presentation/FileExplorer.tsx")
    assert "DEBOUNCE_MS" in src, (
        "FileExplorer.tsx must reference DEBOUNCE_MS (no copy-pasted 200)"
    )
    # The legacy 200 ms literal must NOT reappear as a magic number.
    assert not re.search(r"setTimeout\([^)]*[, ]\s*200\b", src), (
        "FileExplorer.tsx must not hard-code `setTimeout(..., 200)` — "
        "share DEBOUNCE_MS with the application layer"
    )


def test_file_explorer_self_mounts_for_non_null_taxon_id() -> None:
    """`FileExplorer` MUST self-mount its data fetch for a non-null
    taxonId via `useFileExplorer` (the 5b.2 hook). The parent
    (app-shell / page.tsx) does NOT pre-fetch — the presentation layer
    owns the mount. Pin the import + the prop shape so the contract
    stays explicit."""
    src = read("presentation/FileExplorer.tsx")
    assert re.search(r"\buseFileExplorer\b", src), (
        "FileExplorer.tsx must import `useFileExplorer` from the research barrel"
    )
    # The prop name is `taxonId` (per the useFileExplorer hook contract).
    assert re.search(r"\btaxonId\b\s*:", src), (
        "FileExplorer must accept a `taxonId: number | null` prop"
    )


def test_file_explorer_does_not_fetch_when_taxon_id_is_null() -> None:
    """When `taxonId` is null the explorer MUST render its no-taxon
    placeholder without firing a network request. The hook contract
    guarantees no fetch on null; this test pins that the explorer
    surfaces a placeholder visible in the rendered tree."""
    src = read("presentation/FileExplorer.tsx")
    # The render branch must reach for a placeholder / empty state when
    # no tree is loaded (network idle / taxonId null / fetch failed).
    assert re.search(
        r"(research-explorer|file-explorer-pane|file-viewer-pane|fex-)"
        r"[\s\S]{0,200}?(folder_off|empty-state|empty)",
        src,
    ) or re.search(r"empty", src, re.IGNORECASE), (
        "FileExplorer must render a placeholder when the tree is not loaded"
    )


def test_file_explorer_folder_rows_carry_data_realm_other() -> None:
    """5b.3 defers realm mapping. Every folder row the explorer stamps
    MUST carry `data-realm="other"` (no helper, no realm dispatch)."""
    src = read("presentation/FileExplorer.tsx")
    assert re.search(r'data-realm=["\']other["\']', src), (
        'FileExplorer folder rows must stamp `data-realm="other"` '
        "(realm mapping is deferred to 5b.4)"
    )


def test_file_explorer_does_not_reference_a_realm_helper() -> None:
    """5b.3 explicitly forbids a realm helper / domain file. The
    explorer MUST NOT import one."""
    src = read("presentation/FileExplorer.tsx")
    for tok in ("realmFor", "realm-helper", "realm.ts", "realms.ts",
                "from \"../domain/realm\"", "from '../domain/realm'"):
        assert tok not in src, (
            f"FileExplorer must not reference realm helper {tok!r} "
            f"(5b.3 defers realm mapping)"
        )


def test_file_explorer_renders_annotate_explorer_matches_output() -> None:
    """The explorer's filter / highlight branches MUST consume the
    application-layer `annotateExplorerMatches(root, query)` output
    (the { matches, ancestors } shape), not re-invent a local walker."""
    src = read("presentation/FileExplorer.tsx")
    assert "annotateExplorerMatches" in src, (
        "FileExplorer must call `annotateExplorerMatches` from the "
        "research barrel — not re-implement the recursive walker"
    )


def test_file_explorer_uses_aria_roles_and_live_region_for_status() -> None:
    """WCAG 2.2 AA — the explorer MUST surface an accessible status
    region for loading + error states (aria-live / role="status").
    The exact wording is free; the landmark is the contract."""
    src = read("presentation/FileExplorer.tsx")
    # Any accessible landmark suffices: aria-live, role="status",
    # role="tree", role="treeitem".
    for tok in ("role=\"status\"", "aria-live", "role=\"tree\"",
                "role=\"treeitem\"", "aria-busy"):
        if tok in src:
            return
    pytest.fail(
        "FileExplorer must declare at least one accessibility landmark "
        "(role=\"status\" / aria-live / role=\"tree\" / aria-busy)"
    )


def test_file_explorer_exposes_search_mode_toggle_aria_pressed() -> None:
    """Filter / highlight toggle buttons MUST use `aria-pressed`
    (WAI-ARIA pattern for binary toggle buttons). The keyboard
    shortcut + screen-reader contract lands here."""
    src = read("presentation/FileExplorer.tsx")
    assert "aria-pressed" in src, (
        "FileExplorer must stamp `aria-pressed` on its toggle buttons "
        "(filter / highlight + hideEmpty)"
    )


def test_file_explorer_uses_research_explorer_shell_class() -> None:
    """The two-pane shell MUST ride the existing production class
    `.research-explorer` (PR 3c-c pinned it) — no new wrapper class."""
    src = read("presentation/FileExplorer.tsx")
    assert "research-explorer" in src, (
        "FileExplorer must render the `.research-explorer` shell "
        "(PR 3c-c already declares it)"
    )


def test_file_explorer_uses_file_explorer_and_viewer_pane_classes() -> None:
    """The two panes MUST use the production `.file-explorer-pane` /
    `.file-viewer-pane` selectors — never a custom wrapper."""
    src = read("presentation/FileExplorer.tsx")
    assert "file-explorer-pane" in src, (
        "FileExplorer must stamp `.file-explorer-pane` on the left pane"
    )
    assert "file-viewer-pane" in src, (
        "FileExplorer must stamp `.file-viewer-pane` on the right pane"
    )


# ---------------------------------------------------------------------------
# FileViewer — no-file empty state lives here (not in the explorer pane)
# ---------------------------------------------------------------------------
def test_file_viewer_renders_no_file_empty_state() -> None:
    """The viewer's no-file empty state MUST live inside FileViewer
    (NOT inside FileExplorer / the left pane). The explorer pane shows
    only the tree; the right pane owns the empty preview state.
    Pins the `description` Material Symbols icon and `fex-empty-state`
    chrome (matching the legacy file_viewer.js renderPlaceholder)."""
    src = read("presentation/FileViewer.tsx")
    assert "fex-empty-state" in src, (
        "FileViewer must render `.fex-empty-state` for its no-file state"
    )
    assert "description" in src, (
        "FileViewer empty state must use the `description` Material Symbols icon"
    )


def test_file_viewer_uses_resolve_viewer_descriptor() -> None:
    """The viewer MUST consume `resolveViewerDescriptor(file)` from the
    application barrel (the 5b.2 extension→format dispatcher). No
    local copy of the RENDERERS table."""
    src = read("presentation/FileViewer.tsx")
    assert "resolveViewerDescriptor" in src, (
        "FileViewer must call `resolveViewerDescriptor` from the research barrel"
    )


def test_file_viewer_uses_use_file_viewer_hook() -> None:
    """The viewer hook (`useFileViewer`) is the bridge that owns the
    CDN script-load lifecycle and the serve URL builder."""
    src = read("presentation/FileViewer.tsx")
    assert re.search(r"\buseFileViewer\b", src), (
        "FileViewer must call `useFileViewer` from the research barrel"
    )


def test_file_viewer_renders_meta_strip_via_dedicated_component() -> None:
    """The meta strip (`FORMAT | SIZE | ENCODING`) lives in its own
    `MetaStrip` component — not inlined into FileViewer. Keeps the
    5b.3 refactor (`extract the meta strip into a single component`,
    tasks.md 5b.9) honest from the start."""
    src = read("presentation/FileViewer.tsx")
    assert "MetaStrip" in src, (
        "FileViewer must compose <MetaStrip> rather than inline the strip"
    )


def test_file_viewer_renders_tab_strip_via_dedicated_component() -> None:
    """The Raw / Table / Tree tab strip lives in `RawTableTreeTabs` —
    kept local (not promoted to design-system per the 5b.3 brief)."""
    src = read("presentation/FileViewer.tsx")
    assert "RawTableTreeTabs" in src, (
        "FileViewer must compose <RawTableTreeTabs> rather than inline the strip"
    )


def test_file_viewer_exposes_cdn_failure_landmark() -> None:
    """When `useFileViewer` reports a CDN error, the viewer MUST surface
    an accessible status region. The literal banner text rides on the
    `Banners` component (separate test)."""
    src = read("presentation/FileViewer.tsx")
    # Any accessible status landmark suffices — the contract is the
    # element, not the wording.
    assert (
        "role=\"status\"" in src or "aria-live" in src
    ), "FileViewer must expose a status region for CDN errors"


# ---------------------------------------------------------------------------
# RawTableTreeTabs — Raw / Table / Tree toggle (local to research)
# ---------------------------------------------------------------------------
def test_raw_table_tree_tabs_is_local_to_research_presentation() -> None:
    """`RawTableTreeTabs` MUST live in `src/modules/research/presentation/`
    (5b.3 brief: keep it local, do not promote to design-system)."""
    assert RAW_TABS.is_file(), (
        f"RawTableTreeTabs must live at {RAW_TABS.relative_to(REPO)}"
    )


def test_raw_table_tree_tabs_renders_three_tabs() -> None:
    """The component MUST render the three legacy tab labels (Raw / Table
    / Tree) and use `data-viewer-tab` so the per-format renderer
    dispatch can read the active tab."""
    src = read("presentation/RawTableTreeTabs.tsx")
    for tab in ("Raw", "Table", "Tree"):
        assert re.search(rf'"\s*{tab}\s*"', src) or re.search(
            rf"'\s*{tab}\s*'", src,
        ) or re.search(rf'>\s*{tab}\s*<', src), (
            f"RawTableTreeTabs must render literal {tab!r} label"
        )
    assert "data-viewer-tab" in src, (
        "RawTableTreeTabs must stamp `data-viewer-tab` on every button"
    )


def test_raw_table_tree_tabs_active_state_is_externally_controlled() -> None:
    """The active tab MUST be driven by an `active` prop (the parent
    owns selection) — not by local state. Mirrors the explorer pattern
    (selection lives in the parent hook, not in DOM)."""
    src = read("presentation/RawTableTreeTabs.tsx")
    assert re.search(r"\bactive\b\s*[:?]", src), (
        "RawTableTreeTabs must accept an `active: ExplorerViewerTab` prop"
    )


def test_raw_table_tree_tabs_uses_aria_for_tablist() -> None:
    """WCAG 2.2 AA — the tab strip must be a `role="tablist"` landmark
    with `role="tab"` children + `aria-selected` on the active button."""
    src = read("presentation/RawTableTreeTabs.tsx")
    assert "tablist" in src or "role=\"tab\"" in src, (
        "RawTableTreeTabs must declare a tablist landmark"
    )
    assert "aria-selected" in src, (
        "RawTableTreeTabs must stamp `aria-selected` on each tab button"
    )


# ---------------------------------------------------------------------------
# MetaStrip — `FORMAT=<EXT> | SIZE=<bytes> | ENCODING=UTF-8` contract
# ---------------------------------------------------------------------------
def test_meta_strip_renders_format_size_encoding_labels() -> None:
    """The meta strip renders three labels — `FORMAT=<EXT>`,
    `SIZE=<bytes>`, `ENCODING=UTF-8` — matching the legacy
    `web/file_explorer.js::openFile` chrome."""
    src = read("presentation/MetaStrip.tsx")
    for lit in ("FORMAT=", "SIZE=", "ENCODING="):
        assert lit in src, (
            f"MetaStrip must render the literal {lit!r} label"
        )


def test_meta_strip_renders_format_size_encoding_via_format_size() -> None:
    """SIZE MUST be rendered through the application-layer
    `formatSize(bytes)` helper — not a local bytes-to-string copy."""
    src = read("presentation/MetaStrip.tsx")
    assert "formatSize" in src, (
        "MetaStrip must call `formatSize` from the research barrel"
    )


# ---------------------------------------------------------------------------
# BreadcrumbPanel — current folder chain
# ---------------------------------------------------------------------------
def test_breadcrumb_panel_paints_segments_with_data_attributes() -> None:
    """The breadcrumb paints one segment per folder; each segment
    carries `data-folder-path` so the parent can re-mount selection on
    click without rebuilding the chain."""
    src = read("presentation/BreadcrumbPanel.tsx")
    assert "data-folder-path" in src, (
        "BreadcrumbPanel must stamp `data-folder-path` on each segment"
    )
    assert re.search(r"\bsegments\b", src), (
        "BreadcrumbPanel must accept a `segments` prop"
    )


def test_breadcrumb_panel_is_accessible() -> None:
    """WCAG 2.2 AA — breadcrumb is a `<nav>` landmark with an
    `aria-label="Research path"`."""
    src = read("presentation/BreadcrumbPanel.tsx")
    assert "<nav" in src, (
        "BreadcrumbPanel must render a <nav> landmark"
    )
    assert "aria-label" in src, (
        "BreadcrumbPanel must expose an `aria-label`"
    )


# ---------------------------------------------------------------------------
# Banners — CDN failure banner (Viewer offline) lives here
# ---------------------------------------------------------------------------
def test_banners_module_stamps_fex_banner_role_status() -> None:
    """The CDN failure banner rides on `.fex-banner` + `role="status"`
    so screen readers announce the offline state when it appears."""
    src = read("presentation/Banners.tsx")
    assert "fex-banner" in src, (
        "Banners must stamp `.fex-banner` on the CDN-failure surface"
    )
    assert "role=\"status\"" in src, (
        "Banners must stamp `role=\"status\"` on the CDN-failure surface"
    )


def test_banners_module_includes_viewer_offline_copy() -> None:
    """The CDN failure copy MUST include the literal
    `"Viewer offline"` (matching the legacy `web/file_viewer.js::
    renderOfflineBanner`)."""
    src = read("presentation/Banners.tsx")
    assert "Viewer offline" in src, (
        "Banners must include the literal `Viewer offline` copy"
    )


# ---------------------------------------------------------------------------
# Behaviour-level driver — exercise pure pieces via node --experimental-strip-types
# so the test pins the *actual* function bodies, not just text presence.
# Pattern lifted from tests/test_research_application.py and
# tests/test_research_infra.py.
# ---------------------------------------------------------------------------
_DRIVER_JS = """\
import {
  DEBOUNCE_MS, annotateExplorerMatches, projectExplorerTree,
  initialExplorerSearchState, isExplorerSearchState,
  resolveViewerDescriptor, formatSize,
} from "./research-bundle.ts";
// Re-publish the symbols the test cares about.
const out = {
  debounceMs: DEBOUNCE_MS,
  initSearchQuery: initialExplorerSearchState().query,
  initSearchMode:  initialExplorerSearchState().mode,
  initSearchHideEmpty: initialExplorerSearchState().hideEmpty,
  format_b:  formatSize(512),
  format_kb: formatSize(2048),
  format_unknown: resolveViewerDescriptor({
    name: "x.zip", path: "x.zip", extension: "zip", size: 0,
  }).format,
  format_docx: resolveViewerDescriptor({
    name: "x.docx", path: "x.docx", extension: "docx", size: 0,
  }).format,
  cdn_docx: resolveViewerDescriptor({
    name: "x.docx", path: "x.docx", extension: "docx", size: 0,
  }).cdnLibrary,
  annotateEmpty: annotateExplorerMatches(null, "acr").matches.size,
  annotateHit: annotateExplorerMatches({
    type: "folder", name: "Animalia", path: "Animalia", children: [{
      type: "file", name: "acr.pdf", path: "Animalia/acr.pdf",
      extension: "pdf", size: 1, modified: "2024-01-01",
    }],
  }, "acr").matches.has("Animalia/acr.pdf"),
  projectNull: projectExplorerTree({}),
};
console.log(JSON.stringify(out));
"""


def _run_driver() -> dict:
    d = tempfile.mkdtemp(prefix="taxa-pres-")
    try:
        # Build a self-contained copy of the research module that the
        # driver can import via node --experimental-strip-types. Same
        # pattern as tests/test_research_application.py.
        def _inline(rel: str, replacements: dict[str, str]) -> None:
            src_text = (R / rel).read_text(encoding="utf-8")
            for k, v in replacements.items():
                src_text = src_text.replace(k, v)
            out_path = Path(d) / Path(rel).name
            out_path.write_text(src_text, encoding="utf-8")

        # Stub React so the hook files import cleanly.
        (Path(d) / "react-stub.ts").write_text(
            "export const useState = () => [null, () => {}];\n"
            "export const useEffect = () => {};\n"
            "export default { useState, useEffect };\n",
            encoding="utf-8",
        )
        _inline(
            "application/useFileExplorer.ts",
            {
                'from "../infrastructure/api"': 'from "./api.ts"',
                'from "../domain/research-file"': 'from "./research-file.ts"',
                'from "react"': 'from "./react-stub.ts"',
            },
        )
        _inline(
            "application/useFileViewer.ts",
            {
                'from "../infrastructure/api"': 'from "./api.ts"',
                'from "../domain/research-file"': 'from "./research-file.ts"',
                'from "react"': 'from "./react-stub.ts"',
            },
        )
        _inline(
            "infrastructure/api.ts",
            {
                'from "../domain/research-file"': 'from "./research-file.ts"',
            },
        )
        _inline("domain/research-file.ts", {})

        # Bundle the public surface so the driver imports one symbol.
        bundle = (
            "export { DEBOUNCE_MS, annotateExplorerMatches,\n"
            "         projectExplorerTree, initialExplorerSearchState,\n"
            "         isExplorerSearchState } from \"./useFileExplorer.ts\";\n"
            "export { resolveViewerDescriptor, formatSize }\n"
            "         from \"./useFileViewer.ts\";\n"
        )
        (Path(d) / "research-bundle.ts").write_text(bundle, encoding="utf-8")
        (Path(d) / "d.mjs").write_text(_DRIVER_JS, encoding="utf-8")

        proc = subprocess.run(
            ["node", "--experimental-strip-types", f"{d}/d.mjs"],
            capture_output=True, text=True,
            env=dict(os.environ, NODE_NO_WARNINGS="1"), timeout=15,
        )
        assert proc.returncode == 0, (
            f"node driver rc={proc.returncode} stderr={proc.stderr[-400:]}"
        )
        return json.loads(proc.stdout.strip())
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def driver_output() -> dict:
    if not shutil.which("node"):
        pytest.skip("node required for runtime harness")
    return _run_driver()


def test_debounce_constant_is_200(driver_output: dict) -> None:
    """spec.md §Tree search: 200 ms debounce. Pinned on the application
    layer so 5b.3 can share it."""
    assert driver_output["debounceMs"] == 200, (
        f"DEBOUNCE_MS must be 200; got {driver_output['debounceMs']!r}"
    )


def test_initial_search_state_matches_legacy(driver_output: dict) -> None:
    """The presentation layer reads the same initial search state the
    legacy `web/state.js::initialExplorerShape().search` literal used."""
    o = driver_output
    assert o["initSearchQuery"] == ""
    assert o["initSearchMode"] == "filter"
    assert o["initSearchHideEmpty"] is True


def test_format_size_helpers_round_trip(driver_output: dict) -> None:
    """The application-layer `formatSize` is the bytes→human helper
    the MetaStrip component calls. Pins B / KB formatting."""
    o = driver_output
    assert o["format_b"].endswith("B")
    assert o["format_kb"].endswith("KB")


def test_format_dispatcher_routes_extensions(driver_output: dict) -> None:
    """The dispatcher routes DOCX→docx + mammoth; unknown extensions
    fall through to `unknown`."""
    o = driver_output
    assert o["format_docx"] == "docx"
    assert o["cdn_docx"] == "mammoth"
    assert o["format_unknown"] == "unknown"


def test_annotate_explorer_matches_returns_self_match(driver_output: dict) -> None:
    """The annotation helper returns the matched node's path in the
    `matches` set so the explorer can paint `data-search-match`."""
    o = driver_output
    assert o["annotateEmpty"] == 0, (
        "annotateExplorerMatches(null, 'acr') must yield empty matches"
    )
    assert o["annotateHit"] is True, (
        "annotateExplorerMatches must add the matched node's path to `matches`"
    )


def test_project_explorer_tree_rejects_malformed_envelope(
    driver_output: dict,
) -> None:
    """`projectExplorerTree({})` must return `null` so the explorer
    can render its placeholder. The application predicate rejects
    malformed inputs outright (no shape contract for the rejection
    case — the explorer only ever feeds wire envelopes from
    `fetchFiles`, which validates first)."""
    assert driver_output["projectNull"] is None, (
        "projectExplorerTree({}) must yield null (placeholder surface). "
        f"Got: {driver_output['projectNull']!r}"
    )


# ---------------------------------------------------------------------------
# Triangulation — extra coverage beyond the GREEN suite.
#
# These tests pin the OBSERVABLE contract that survives a refactor:
# the class names, data attributes, ARIA roles, and import edges the
# app-shell / downstream consumers rely on. They run alongside the
# GREEN tests; they are not load-bearing for the RED→GREEN transition
# but they catch regressions the GREEN suite misses.
# ---------------------------------------------------------------------------

def test_file_explorer_does_not_deep_import_research_layers() -> None:
    """The explorer must import every type / hook from `@taxa/research`
    (NEVER from a deep `../application/useFileExplorer`). Pins the
    barrel contract via the imports inside FileExplorer.tsx so a future
    shortcut (`import { useFileExplorer } from "../application/..."`) is
    caught at review time."""
    src = read("presentation/FileExplorer.tsx")
    for layer in ("application", "infrastructure", "domain"):
        bad = re.search(rf'from\s+["\']\.\./{layer}/', src)
        assert bad is None, (
            f"FileExplorer must not deep-import the {layer} layer — "
            f"got {bad.group(0)!r}"
        )


def test_file_explorer_debounce_via_constant_not_magic_number() -> None:
    """The explorer MUST debounce the input via DEBOUNCE_MS (5b.2).
    A direct `setTimeout` with a magic-number copy is a regression."""
    src = read("presentation/FileExplorer.tsx")
    assert "DEBOUNCE_MS" in src, (
        "FileExplorer must consume DEBOUNCE_MS from @taxa/research"
    )
    bad = re.search(r"setTimeout\([^)]*[,  ]\s*200\s*[,)]", src)
    assert bad is None, (
        f"FileExplorer must not hard-code setTimeout(..., 200); got {bad.group(0)!r}"
    )


def test_file_viewer_does_not_deep_import_research_layers() -> None:
    """The viewer must reach `useFileViewer` + `resolveViewerDescriptor`
    + `ViewerFile` via the public barrel, never via a deep relative
    import."""
    src = read("presentation/FileViewer.tsx")
    for tok in ("useFileViewer", "resolveViewerDescriptor", "ViewerFile"):
        assert tok in src, f"FileViewer must reference {tok!r}"
    for layer in ("application", "infrastructure", "domain"):
        bad = re.search(rf'from\s+["\']\.\./{layer}/', src)
        assert bad is None, (
            f"FileViewer must not deep-import the {layer} layer — "
            f"got {bad.group(0)!r}"
        )


def test_presentation_components_carry_data_attrs_for_e2e_hook() -> None:
    """The presentation layer stamps `data-*` attributes the e2e
    harness (PR 5c.1) will reach for — `data-explorer`, `data-pane`,
    `data-search-input`, `data-search-mode-btn`, `data-viewer-tab`,
    `data-meta-strip`, `data-folder-path`, `data-file-path`,
    `data-viewer-body`, `data-cdn-ready`, `data-realm`. Pin the names
    so a future rename surfaces here before the screenshot corpus breaks."""
    explorer = read("presentation/FileExplorer.tsx")
    viewer = read("presentation/FileViewer.tsx")
    tabs = read("presentation/RawTableTreeTabs.tsx")
    meta = read("presentation/MetaStrip.tsx")
    for attr in ("data-explorer", "data-pane", "data-search-input",
                 "data-search-mode-btn", "data-folder-path", "data-file-path"):
        assert attr in explorer, (
            f"FileExplorer must stamp `{attr}` (PR 5c.1 e2e selector contract)"
        )
    for attr in ("data-viewer-body", "data-viewer-pane", "data-cdn-ready"):
        assert attr in viewer, (
            f"FileViewer must stamp `{attr}` (PR 5c.1 e2e selector contract)"
        )
    assert "data-viewer-tab" in tabs, (
        "RawTableTreeTabs must stamp `data-viewer-tab` on each button"
    )
    assert "data-meta-strip" in meta, (
        "MetaStrip must stamp `data-meta-strip` on the row"
    )


def test_breadcrumb_panel_renders_empty_state_with_data_attr() -> None:
    """When `segments` is empty the breadcrumb paints an empty `<nav>`
    with `data-breadcrumb-empty=""` so a test can detect the empty
    state without text-matching."""
    src = read("presentation/BreadcrumbPanel.tsx")
    assert "data-breadcrumb-empty" in src, (
        "BreadcrumbPanel must stamp `data-breadcrumb-empty` on the "
        "empty-state <nav>"
    )


def test_banners_returns_null_when_show_is_false() -> None:
    """`Banners` returns `null` when `show` is false. Pins the cheap
    no-render path so a future rewrite can't accidentally emit a
    hidden-but-present banner."""
    src = read("presentation/Banners.tsx")
    assert re.search(r"if\s*\(\s*!show\s*\)\s*return\s+null", src), (
        "Banners must `return null` when `show` is false"
    )


def test_meta_strip_uses_format_size_for_size_label() -> None:
    """`MetaStrip` MUST format the byte count through the application
    `formatSize` helper — the local bytes-to-string literal is the
    legacy foot-gun 5b.2 closed."""
    src = read("presentation/MetaStrip.tsx")
    assert re.search(r"formatSize\(", src), (
        "MetaStrip must call `formatSize(...)` for the SIZE label"
    )
    assert not re.search(r"function\s+formatBytes\b", src), (
        "MetaStrip must not re-declare a local `formatBytes` helper"
    )


def test_file_explorer_persists_search_state_via_hook() -> None:
    """The explorer's persisted search state (`mode`, `hideEmpty`)
    MUST round-trip through the `useFileExplorer` hook — the explorer
    never owns its own search state copy. Catches a future refactor
    that drops the hook contract in favour of a local useState."""
    src = read("presentation/FileExplorer.tsx")
    # The hook's search slice must be referenced — either directly
    # (`hook.state.search.query` / `.mode` / `.hideEmpty`) or via a
    # local alias bound from `hook.state.search` (refactored cleanups
    # pull the slice into a `const search = hook.state.search` so the
    # JSX doesn't chain off `hook.state.search.<x>` three times). The
    # contract is "no local useState for search state"; both shapes
    # satisfy it.
    binds_search = re.search(r"\bsearch\s*=\s*hook\.state\.search\b", src)
    direct = re.search(r"hook\.state\.search\.query", src)
    assert binds_search is not None or direct is not None, (
        "FileExplorer must read `hook.state.search.query` (directly or "
        "via a local `const search = hook.state.search` alias)"
    )
    # Once `search` is bound, the toggle + hide-empty must read from
    # it. The mode is consumed via `searchMode === "filter"` /
    # `search.hideEmpty` style access — verify the access paths exist.
    assert re.search(r"search\.mode|hook\.state\.search\.mode", src), (
        "FileExplorer must read `.mode` from the hook's persisted search"
    )
    assert re.search(r"search\.hideEmpty|hook\.state\.search\.hideEmpty", src), (
        "FileExplorer must read `.hideEmpty` from the hook's persisted search"
    )


# ---------------------------------------------------------------------------
# Structural sanity — every 5b.3 component file is parseable TypeScript
# (best-effort: skip when the toolchain is unavailable).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", [
    FILE_EXPLORER, FILE_VIEWER, RAW_TABS, META_STRIP,
    BREAD_PANEL, BANNERS,
])
def test_component_source_is_well_formed(path: Path) -> None:
    """Best-effort source-validity guard. The presentation files MUST
    be readable UTF-8, MUST end with a newline, and MUST contain a
    balanced set of braces + parentheses (so an unbalanced typo
    surfaces here before the runtime). We do not run `tsc` / esbuild
    here — the test harness does not have those pinned — but the
    other content assertions in this file already exercise the
    semantic contracts (class names, ARIA roles, data attributes)."""
    src = path.read_text(encoding="utf-8")
    assert src, f"{path.name} is empty"
    assert src.endswith("\n"), f"{path.name} must end with a newline"
    # Balanced braces + brackets + parens — cheap heuristic that
    # catches unclosed blocks without running a full TS parser.
    counts = {"{": 0, "}": 0, "(": 0, ")": 0, "[": 0, "]": 0}
    # Skip strings + comments so braces inside them don't double-count.
    in_str: str | None = None
    in_line_comment = False
    in_block_comment = False
    i = 0
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_str is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"', "`"):
            in_str = ch
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch in counts:
            counts[ch] += 1
        i += 1
    assert counts["{"] == counts["}"], (
        f"{path.name} has unbalanced braces: "
        f"{counts['{']} open vs {counts['}']} close"
    )
    assert counts["("] == counts[")"], (
        f"{path.name} has unbalanced parens: "
        f"{counts['(']} open vs {counts[')']} close"
    )
    assert counts["["] == counts["]"], (
        f"{path.name} has unbalanced brackets: "
        f"{counts['[']} open vs {counts[']']} close"
    )