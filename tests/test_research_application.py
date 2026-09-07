"""Phase 5b.2 research application contract tests.

Pins the 5b.2 application-layer slice:
  - persisted Explorer search contract (query / mode / hideEmpty)
  - DEBOUNCE_MS = 200 (spec.md §Tree search debounce)
  - consumes 5b.1 typed fetch functions (fetchFiles, fetchServe)
  - framework-neutral view-model surface
  - format dispatcher + CDN-library selection for the file viewer
  - barrel re-exports + root barrel `export * from "./application"`
  - behaviour-level exercise via `node --experimental-strip-types`

No presentation / Search / Folder / app-shell work — strictly application
hooks, mirroring the taxonomy `useTaxonTree` convention inside the
literal allowed surfaces (two named modules + application barrel).
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
APP = R / "application"
APP_INDEX = APP / "index.ts"
ROOT = R / "index.ts"
USE_EXPLORER = APP / "useFileExplorer.ts"
USE_VIEWER = APP / "useFileViewer.ts"
INFRA_API = R / "infrastructure" / "api.ts"
DO_RES = R / "domain" / "research-file.ts"


def read(rel: str) -> str:
    p = R / rel
    assert p.is_file(), f"missing research file: {p}"
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# File presence
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", [USE_EXPLORER, USE_VIEWER, APP_INDEX])
def test_files_present(path: Path) -> None:
    assert path.is_file(), f"missing {path} (PR 5b.2 application slice)"


def test_application_directory_is_three_files_only() -> None:
        """5b.2 + 5b.4 constraint: 'avoid extra files'. The application
        directory MUST hold exactly the three named modules plus the
        barrel — no stale stub files from earlier PRs, no stray
        helpers, no .gitkeep. 5b.4 adds `useMaterializePreview.ts` (the
        typed materialize-preview + folder-creation hook)."""
        if not APP.is_dir():
            pytest.skip("application dir not present yet")
        allowed = {"index.ts", "useFileExplorer.ts", "useFileViewer.ts",
                   "useMaterializePreview.ts"}
        actual = {p.name for p in APP.iterdir()}
        unexpected = actual - allowed
        assert not unexpected, (
            f"application/ has unexpected children: {sorted(unexpected)}. "
            f"Only these are allowed: {sorted(allowed)}."
        )


# ---------------------------------------------------------------------------
# useFileExplorer.ts — persisted search contract + 5b.1 fetch consumption
# ---------------------------------------------------------------------------
def test_explorer_declares_debounce_constant() -> None:
    """spec.md §Tree search: 'debounce input by 200 ms'. The constant
    MUST be exported so the presentation layer (5b.3) shares the same
    timer rather than drifting its own copy."""
    src = read("application/useFileExplorer.ts")
    assert re.search(r"\bexport\s+const\s+DEBOUNCE_MS\s*=\s*200\b", src), (
        "useFileExplorer.ts must `export const DEBOUNCE_MS = 200`"
    )


def test_explorer_declares_search_state_shape() -> None:
    """Persisted Explorer search contract: `state.explorer.search`
    shape is `{ query, mode, hideEmpty }` per web/state.js. 5b.2 must
    declare the same shape on the view-model surface so the
    presentation layer (5b.3) can read/write without re-inventing it."""
    src = read("application/useFileExplorer.ts")
    for tok in ("query", "mode", "hideEmpty"):
        assert re.search(rf"\b{tok}\b\s*:", src), (
            f"useFileExplorer.ts must declare ExplorerSearchState.{tok}"
        )


def test_explorer_declares_search_modes_and_initial_shape() -> None:
    """`mode` is one of `"filter" | "highlight"`; `hideEmpty` defaults
    to `true`; the initial state is `{ query: "", mode: "filter",
    hideEmpty: true }` per web/state.js::initialExplorerShape."""
    src = read("application/useFileExplorer.ts")
    assert re.search(r'"filter"\s*\|\s*"highlight"', src), (
        'mode union must be "filter" | "highlight"'
    )
    assert re.search(r'mode\s*:\s*"filter"', src), (
        'initial mode must be "filter"'
    )
    assert re.search(r'hideEmpty\s*:\s*true', src), (
        "initial hideEmpty must be true"
    )
    assert re.search(r'query\s*:\s*""', src), (
        'initial query must be ""'
    )


def test_explorer_initial_state_helper_matches_legacy() -> None:
    """The exported `initialExplorerSearchState()` helper must yield the
    legacy `web/state.js::initialExplorerShape().search` literal exactly
    so the explorer state reset on taxon switch (spec.md §State Changes)
    produces the same starting point as the legacy app."""
    src = read("application/useFileExplorer.ts")
    assert re.search(
        r"\bexport\s+function\s+initialExplorerSearchState\s*\(\s*\)",
        src,
    ), "must export `initialExplorerSearchState()`"
    # Match the function body across lines. The signature has no
    # parameters, so we look for `() {` then capture everything up to
    # the matching closing brace via a depth-counted scan (regex only
    # would fail on nested braces in the literal). Tolerate a return
    # type annotation (`(): SomeType {`) between `)` and `{`.
    m = re.search(
        r"\bfunction\s+initialExplorerSearchState\s*\([^)]*\)[^{]*\{",
        src,
    )
    assert m is not None, "initialExplorerSearchState signature not found"
    start = m.end()
    depth, cursor = 1, start
    while cursor < len(src) and depth > 0:
        ch = src[cursor]
        if ch == "{": depth += 1
        elif ch == "}": depth -= 1
        cursor += 1
    assert depth == 0, "initialExplorerSearchState body braces unbalanced"
    body = src[start:cursor - 1]
    for lit in ('"filter"', "true", '""'):
        assert lit in body, (
            f"initialExplorerSearchState body must contain literal {lit!r}; "
            f"got: {body!r}"
        )


def test_explorer_consumes_5b1_typed_fetch() -> None:
    """5b.2 must consume the typed `fetchFiles` from
    `infrastructure/api.ts` — not re-implement its own fetch wrapper."""
    src = read("application/useFileExplorer.ts")
    assert "fetchFiles" in src, (
        "useFileExplorer.ts must consume `fetchFiles` from 5b.1"
    )
    assert re.search(r'from\s+["\']\.\./infrastructure(?:/api)?["\']', src), (
        "useFileExplorer.ts must import `fetchFiles` from "
        "`../infrastructure` (or `../infrastructure/api`) — not "
        "re-implement the HTTP boundary"
    )


def test_explorer_search_predicates_round_trip() -> None:
    """Type predicates `isExplorerSearchMode` / `isExplorerSearchState`
    must accept the legacy `{ query: "", mode: "filter", hideEmpty: true }`
    literal and reject malformed inputs."""
    src = read("application/useFileExplorer.ts")
    assert re.search(r"\bisExplorerSearchMode\b", src), (
        "must export `isExplorerSearchMode` predicate"
    )
    assert re.search(r"\bisExplorerSearchState\b", src), (
        "must export `isExplorerSearchState` predicate"
    )


def test_explorer_annotate_matches_helper_exported() -> None:
    """The pure `annotateExplorerMatches(root, query)` view-model
    function (the legacy `_annotateMatches` from web/file_explorer.js
    ported to a framework-free surface) MUST be exported so 5b.3 can
    consume it without depending on the React adapter."""
    src = read("application/useFileExplorer.ts")
    assert re.search(
        r"\bexport\s+function\s+annotateExplorerMatches\s*\(",
        src,
    ), "must export `annotateExplorerMatches(root, query)`"


def test_explorer_project_tree_helper_exported() -> None:
    """`projectExplorerTree(envelope)` projects a `FilesEnvelope` into
    a presentation-ready view model. Frames the `exists`/`root`/etc.
    fields so the renderer can read them without re-parsing."""
    src = read("application/useFileExplorer.ts")
    assert re.search(
        r"\bexport\s+function\s+projectExplorerTree\s*\(",
        src,
    ), "must export `projectExplorerTree(envelope)`"


def test_explorer_view_models_are_framework_neutral() -> None:
    """Pure view-model functions must not import React / useEffect /
    useState — the framework-neutrality contract that 5b.1 inherits
    from useTaxonTree.ts. (The React `useFileExplorer` hook CAN import
    react; this assertion targets the pure helpers only.)"""
    src = read("application/useFileExplorer.ts")
    # Walk every `export function X(...){` declaration and depth-scan
    # to find its body. We only check the listed pure helpers; the
    # `useFileExplorer` React hook is allowed to import React.
    PURE_NAMES = (
        "annotateExplorerMatches", "projectExplorerTree",
        "initialExplorerSearchState", "isExplorerSearchMode",
        "isExplorerSearchState",
    )
    bodies: list[str] = []
    for name in PURE_NAMES:
        m = re.search(
            rf"\bexport\s+function\s+{name}\s*\(", src,
        )
        assert m is not None, f"pure function {name!r} not found"
        sig_end = src.find("{", m.end())
        if sig_end < 0:
            continue
        depth, cursor = 1, sig_end + 1
        while cursor < len(src) and depth > 0:
            ch = src[cursor]
            if ch == "{": depth += 1
            elif ch == "}": depth -= 1
            cursor += 1
        bodies.append(src[sig_end + 1:cursor - 1])
    assert bodies, "no pure view-model function bodies found"
    for body in bodies:
        assert "useState" not in body, "pure function body must not use useState"
        assert "useEffect" not in body, "pure function body must not use useEffect"
        assert "react" not in body.lower(), (
            f"pure function body must not reference react; got: {body[:120]!r}"
        )


def test_explorer_hook_adapter_imports_react() -> None:
    """The client hook adapter `useFileExplorer` MUST be a React hook
    (per the orchestrator mapping: 'client hook adapters in the two
    named modules'). It must import from `react`."""
    src = read("application/useFileExplorer.ts")
    assert re.search(
        r'\bexport\s+function\s+useFileExplorer\s*\(',
        src,
    ), "must export `useFileExplorer` hook"
    assert re.search(
        r"""from\s+["']react["']""", src,
    ), "useFileExplorer hook must import from \"react\""
    # must drive state with a React primitive
    assert re.search(r"\buse(?:State|Effect|Reducer|Memo)\b", src), (
        "useFileExplorer must use at least one React state primitive"
    )


# ---------------------------------------------------------------------------
# useFileViewer.ts — format dispatcher + CDN library selection
# ---------------------------------------------------------------------------
def test_viewer_format_dispatcher_is_exported() -> None:
    """5b.2 viewer needs an extension→format dispatcher. The pure
    `resolveViewerDescriptor(file)` helper is the framework-free
    port of `web/file_viewer.js::RENDERERS[ext]`."""
    src = read("application/useFileViewer.ts")
    assert re.search(
        r"\bexport\s+function\s+resolveViewerDescriptor\s*\(",
        src,
    ), "must export `resolveViewerDescriptor`"


def test_viewer_dispatcher_uses_cdn_libraries_constant() -> None:
    """CDN library selection must reference the pinned `CDN_LIBRARIES`
    / `CDN_URLS` literal from infrastructure/api.ts so the 5b.3
    presentation layer can rely on the same set of libraries."""
    src = read("application/useFileViewer.ts")
    assert re.search(r"\bCDN_LIBRARIES\b|\bCDN_URLS\b", src), (
        "useFileViewer.ts must reference `CDN_LIBRARIES` or `CDN_URLS` "
        "from infrastructure/api.ts"
    )


def test_viewer_format_size_helper_exported() -> None:
    """Meta strip contract (`FORMAT | SIZE | ENCODING`) needs a
    deterministic bytes→human formatter. The pure `formatSize(bytes)`
    helper is the framework-free port of `web/file_viewer.js::formatSize`."""
    src = read("application/useFileViewer.ts")
    assert re.search(
        r"\bexport\s+function\s+formatSize\s*\(",
        src,
    ), "must export `formatSize(bytes)`"


def test_viewer_dispatcher_routes_cdn_formats() -> None:
    """resolveViewerDescriptor MUST return a CDN library name for the
    four CDN-backed formats (DOCX→mammoth, XLS/XLSX→XLSX, EPUB→ePub,
    CSV/TSV→Papa). The shape must be `{ format, cdnLibrary }`."""
    src = read("application/useFileViewer.ts")
    # The dispatcher should reference every CDN library as a literal
    for cdn in ("mammoth", "XLSX", "ePub", "Papa"):
        assert re.search(rf'"{cdn}"', src), (
            f"format dispatcher must reference CDN library \"{cdn}\""
        )
    # Should NOT depend on `document` / `window` (pure view model).
    assert "document." not in src, "useFileViewer.ts must be framework-neutral"
    assert "window." not in src, "useFileViewer.ts must be framework-neutral"


def test_viewer_consumes_5b1_fetch_serve() -> None:
    """`fetchServe(baseUrl, taxonId, path)` from 5b.1 must be reachable
    via the application layer's hook so the presentation component
    never reaches into `infrastructure/` directly."""
    src = read("application/useFileViewer.ts")
    assert "fetchServe" in src, (
        "useFileViewer.ts must consume `fetchServe` from 5b.1"
    )
    assert re.search(r'from\s+["\']\.\./infrastructure(?:/api)?["\']', src), (
        "useFileViewer.ts must import `fetchServe` from ../infrastructure"
    )


def test_viewer_hook_adapter_imports_react() -> None:
    """Mirror of test_explorer_hook_adapter_imports_react for the
    viewer module."""
    src = read("application/useFileViewer.ts")
    assert re.search(
        r'\bexport\s+function\s+useFileViewer\s*\(',
        src,
    ), "must export `useFileViewer` hook"
    assert re.search(
        r"""from\s+["']react["']""", src,
    ), "useFileViewer hook must import from \"react\""
    assert re.search(r"\buse(?:State|Effect|Reducer|Memo)\b", src), (
        "useFileViewer must use at least one React state primitive"
    )


# ---------------------------------------------------------------------------
# Barrels
# ---------------------------------------------------------------------------
def test_application_barrel_reexports_pure_and_hook_surface() -> None:
    """The application barrel MUST re-export the full 5b.2 surface so
    downstream consumers (`presentation/`, `app-shell/`) only ever
    import via `@taxa/research`."""
    src = read("application/index.ts")
    for tok in (
        "DEBOUNCE_MS",
        "ExplorerSearchState",
        "initialExplorerSearchState",
        "isExplorerSearchMode",
        "isExplorerSearchState",
        "annotateExplorerMatches",
        "projectExplorerTree",
        "useFileExplorer",
        "resolveViewerDescriptor",
        "formatSize",
        "useFileViewer",
    ):
        assert tok in src, f"application/index.ts must re-export {tok!r}"


def test_application_barrel_mirrors_taxonomy_convention() -> None:
    """Mirror of `src/modules/taxonomy/application/index.ts`. Both
    files re-export the pure view-model surface first, then the hook
    adapter surface, via two `export { ... } from "./..."` blocks."""
    src = read("application/index.ts")
    pure_block = re.search(
        r'export\s*\{[^}]*\}\s*from\s*["\']\./useFileExplorer["\']',
        src,
    )
    hook_block = re.search(
        r'export\s*\{[^}]*\}\s*from\s*["\']\./useFileViewer["\']',
        src,
    )
    assert pure_block is not None, (
        "application barrel must `export { ... } from \"./useFileExplorer\"` "
        "for the pure + explorer-hook surface (mirrors taxonomy convention)"
    )
    assert hook_block is not None, (
        "application barrel must `export { ... } from \"./useFileViewer\"` "
        "for the viewer surface (mirrors taxonomy convention)"
    )


def test_root_barrel_exposes_application_surface() -> None:
    """spec.md rule 5: cross-module consumers MUST import from the
    public barrel. The root `src/modules/research/index.ts` MUST add
    `export * from "./application"` so the 5b.2 surface is reachable
    via `@taxa/research` (without rewriting the root barrel's docblock
    beyond the minimal required addendum)."""
    src = read("index.ts")
    assert re.search(
        r'export\s*\*\s+from\s+["\']\./application["\']',
        src,
    ), 'research/index.ts must `export * from "./application"`'


def test_root_barrel_keeps_predecessor_exports() -> None:
    """Predecessor 5b.1 root-barrel exports (`./domain`,
    `./infrastructure`) MUST stay byte-identical. 5b.2 only ADDS the
    `./application` line — never removes or reorders the predecessors."""
    src = read("index.ts")
    assert re.search(
        r'export\s*\*\s+from\s+["\']\./domain["\']', src,
    ), 'root barrel must keep `export * from "./domain"`'
    assert re.search(
        r'export\s*\*\s+from\s+["\']\./infrastructure["\']', src,
    ), 'root barrel must keep `export * from "./infrastructure"`'


# ---------------------------------------------------------------------------
# Behaviour-level driver — exercise the pure view-model surface via Node
# so the test pins the *actual* function bodies, not just text presence.
# Pattern lifted from tests/test_research_infra.py::
# _exercise_fetch_files (node --experimental-strip-types against a tmp
# copy of the module so the test doesn't pollute the worktree with
# patched relative imports).
# ---------------------------------------------------------------------------
_DRIVER_JS = """\
import { initialExplorerSearchState,
         isExplorerSearchMode, isExplorerSearchState,
         annotateExplorerMatches, projectExplorerTree }
  from "./useFileExplorer.ts";
import { resolveViewerDescriptor, formatSize }
  from "./useFileViewer.ts";

// ---- Explorer search state ----------------------------------------------
const init   = initialExplorerSearchState();
const valid  = isExplorerSearchState(init);
const badQ   = isExplorerSearchState({ query: 7, mode: "filter", hideEmpty: true });
const badM   = isExplorerSearchState({ query: "", mode: "regex", hideEmpty: true });
const badH   = isExplorerSearchState({ query: "", mode: "filter", hideEmpty: "yes" });
const good   = isExplorerSearchState({ query: "acr", mode: "highlight", hideEmpty: false });
const modeF  = isExplorerSearchMode("filter");
const modeH  = isExplorerSearchMode("highlight");
const modeX  = isExplorerSearchMode("regex");

// ---- annotateExplorerMatches ---------------------------------------------
const folder = {
  type: "folder", name: "Animalia", path: "Animalia",
  children: [
    { type: "folder", name: "Arthropoda", path: "Animalia/Arthropoda",
      children: [
        { type: "file", name: "acr.pdf", path: "Animalia/Arthropoda/acr.pdf",
          extension: "pdf", size: 100, modified: "2024-01-01" },
        { type: "file", name: "bee.md",  path: "Animalia/Arthropoda/bee.md",
          extension: "md",  size: 50,  modified: "2024-01-01" },
      ] },
    { type: "file", name: "fish.txt", path: "Animalia/fish.txt",
      extension: "txt", size: 80, modified: "2024-01-01" },
  ] };
const empty = annotateExplorerMatches(null, "acr");
const noQ   = annotateExplorerMatches(folder, "");
const acr   = annotateExplorerMatches(folder, "acr");
const md    = annotateExplorerMatches(folder, "MD");    // case-insensitive
const bee   = annotateExplorerMatches(folder, "bee");

// ---- projectExplorerTree --------------------------------------------------
const env = {
  exists: true, taxon_id: 42, taxon_name: "Animalia", taxon_path: "Animalia",
  filesystem_path: "/srv", subpath: null, root: folder,
};
const vm = projectExplorerTree(env);
const vmNo = projectExplorerTree({ ...env, exists: false, root: null });
const vmRoot = projectExplorerTree({ ...env, root: null });

// ---- format dispatcher ----------------------------------------------------
const dPdf   = resolveViewerDescriptor({ name: "x.pdf",  path: "x.pdf",
                                          extension: "PDF",  size: 0 });
const dDocx  = resolveViewerDescriptor({ name: "x.docx", path: "x.docx",
                                          extension: "docx", size: 0 });
const dXls   = resolveViewerDescriptor({ name: "x.xls",  path: "x.xls",
                                          extension: "xls",  size: 0 });
const dXlsx  = resolveViewerDescriptor({ name: "x.xlsx", path: "x.xlsx",
                                          extension: "xlsx", size: 0 });
const dEpub  = resolveViewerDescriptor({ name: "x.epub", path: "x.epub",
                                          extension: "epub", size: 0 });
const dCsv   = resolveViewerDescriptor({ name: "x.csv",  path: "x.csv",
                                          extension: "csv",  size: 0 });
const dTsv   = resolveViewerDescriptor({ name: "x.tsv",  path: "x.tsv",
                                          extension: "tsv",  size: 0 });
const dJson  = resolveViewerDescriptor({ name: "x.json", path: "x.json",
                                          extension: "json", size: 0 });
const dPng   = resolveViewerDescriptor({ name: "x.png",  path: "x.png",
                                          extension: "png",  size: 0 });
const dDoc   = resolveViewerDescriptor({ name: "x.doc",  path: "x.doc",
                                          extension: "doc",  size: 0 });
const dZip   = resolveViewerDescriptor({ name: "x.zip",  path: "x.zip",
                                          extension: "zip",  size: 0 });

// ---- formatSize -----------------------------------------------------------
const sB  = formatSize(512);
const sKB = formatSize(2048);
const sMB = formatSize(5 * 1024 * 1024);
const sGB = formatSize(2 * 1024 * 1024 * 1024);
const sN  = formatSize(null);

const out = {
  // explorer
  init_query: init.query, init_mode: init.mode, init_hideEmpty: init.hideEmpty,
  valid, badQ, badM, badH, good, modeF, modeH, modeX,
  empty_matches: empty.matches.size, empty_ancestors: empty.ancestors.size,
  noQ_matches: noQ.matches.size,
  acr_matches: [...acr.matches].sort(),
  acr_ancestors: [...acr.ancestors].sort(),
  md_matches:   [...md.matches].sort(),
  md_ancestors: [...md.ancestors].sort(),
  bee_ancestors: [...bee.ancestors].sort(),
  vm_exists:    vm ? vm.exists : "null",
  vm_rootName:  vm && vm.root ? vm.root.name : "null",
  vmNo_exists:  vmNo ? vmNo.exists : "null",
  vmNo_root:    vmNo ? vmNo.root : "marker",
  vmRoot_exists: vmRoot ? vmRoot.exists : "null",
  vmRoot_root:  vmRoot ? vmRoot.root : "marker",
  // dispatcher
  dPdf_format:  dPdf.format,  dPdf_cdn:  dPdf.cdnLibrary,
  dDocx_format: dDocx.format, dDocx_cdn: dDocx.cdnLibrary,
  dXls_format:  dXls.format,  dXls_cdn:  dXls.cdnLibrary,
  dXlsx_format: dXlsx.format, dXlsx_cdn: dXlsx.cdnLibrary,
  dEpub_format: dEpub.format, dEpub_cdn: dEpub.cdnLibrary,
  dCsv_format:  dCsv.format,  dCsv_cdn:  dCsv.cdnLibrary,
  dTsv_format:  dTsv.format,  dTsv_cdn:  dTsv.cdnLibrary,
  dJson_format: dJson.format, dJson_cdn: dJson.cdnLibrary,
  dPng_format:  dPng.format,  dPng_cdn:  dPng.cdnLibrary,
  dDoc_format:  dDoc.format,  dDoc_cdn:  dDoc.cdnLibrary,
  dZip_format:  dZip.format,  dZip_cdn:  dZip.cdnLibrary,
  // formatSize
  sB, sKB, sMB, sGB, sN,
};
console.log(JSON.stringify(out));
"""


def _run_driver() -> dict:
    src_dir = R
    d = tempfile.mkdtemp(prefix="taxa-app-")
    try:
        # Copy the two pure-view-model / hook files verbatim (their
        # `../infrastructure/api` and `../domain/research-file` imports
        # resolve against the worktree, but Node's strip-types loader
        # needs every file in the same directory; copy the imports
        # in-line so the tmpdir is self-contained).
        def _inline(rel: str, replacements: dict[str, str]) -> None:
            text = (src_dir / rel).read_text(encoding="utf-8")
            for k, v in replacements.items():
                text = text.replace(k, v)
            (Path(d) / Path(rel).name).write_text(text, encoding="utf-8")

        # Stub `react` so the hook files import cleanly inside the
        # tmpdir. The driver only invokes pure functions, so the
        # stub bodies never need to behave like real React — they
        # just need to exist so the module resolves. Matches the
        # pattern used by tests/test_research_infra.py (driver
        # imports against a tmp copy).
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
        _inline(
            "domain/research-file.ts", {},
        )
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


def test_initial_search_state_matches_legacy(driver_output: dict) -> None:
    o = driver_output
    assert o["init_query"] == "", f"initial query must be ''; got {o['init_query']!r}"
    assert o["init_mode"] == "filter", (
        f"initial mode must be 'filter'; got {o['init_mode']!r}"
    )
    assert o["init_hideEmpty"] is True, (
        f"initial hideEmpty must be true; got {o['init_hideEmpty']!r}"
    )


def test_search_state_predicates_round_trip(driver_output: dict) -> None:
    o = driver_output
    assert o["valid"] is True, "initial state must validate"
    assert o["badQ"] is False, "non-string query must reject"
    assert o["badM"] is False, "unknown mode must reject"
    assert o["badH"] is False, "non-boolean hideEmpty must reject"
    assert o["good"] is True, "valid alternate state must accept"
    assert o["modeF"] is True and o["modeH"] is True, (
        '"filter" and "highlight" must validate'
    )
    assert o["modeX"] is False, '"regex" must reject'


def test_annotate_matches_self_and_ancestors(driver_output: dict) -> None:
    o = driver_output
    assert o["empty_matches"] == 0 and o["empty_ancestors"] == 0, (
        f"empty input must yield empty annotation; got {o}"
    )
    assert o["noQ_matches"] == 0, "empty query must yield no matches"
    # "acr" matches acr.pdf (self) + every ancestor that contains it
    assert "Animalia/Arthropoda/acr.pdf" in o["acr_matches"], o
    # Ancestors must include both the parent folder and the root
    assert "Animalia/Arthropoda" in o["acr_ancestors"], o
    assert "Animalia" in o["acr_ancestors"], o
    # Case-insensitive: "MD" matches bee.md via its extension-ish path
    assert any("bee.md" in p for p in o["md_matches"]), o
    # bee matches bee.md (self) + both ancestors
    assert "Animalia/Arthropoda/bee.md" in o["bee_ancestors"] or \
           "Animalia/Arthropoda" in o["bee_ancestors"], o


def test_project_explorer_tree_projects_envelope(driver_output: dict) -> None:
    o = driver_output
    assert o["vm_exists"] is True, "projectExplorerTree must surface `exists`"
    assert o["vm_rootName"] == "Animalia", (
        f"projectExplorerTree must surface root.name; got {o['vm_rootName']!r}"
    )
    # exists=false + root=null → view model keeps the surface but
    # exposes exists=false + root=null so the renderer can show the
    # "no corpus" state.
    assert o["vmNo_exists"] is False, (
        "projectExplorerTree({exists:false, root:null}) must yield exists=false"
    )
    assert o["vmNo_root"] is None, (
        f"projectExplorerTree must surface root=null when envelope.root "
        f"is null; got {o['vmNo_root']!r}"
    )
    # exists=true + root=null (corpus not materialised) → exists=true, root=null
    assert o["vmRoot_exists"] is True and o["vmRoot_root"] is None, o


def test_format_dispatcher_routes_extensions(driver_output: dict) -> None:
    o = driver_output
    # CDN-backed formats
    assert o["dPdf_format"] == "pdf", o
    assert o["dPdf_cdn"] is None, "PDF has no CDN dependency"
    assert o["dDocx_format"] == "docx" and o["dDocx_cdn"] == "mammoth", o
    assert o["dXls_format"] == "xls" and o["dXls_cdn"] == "XLSX", o
    assert o["dXlsx_format"] == "xlsx" and o["dXlsx_cdn"] == "XLSX", o
    assert o["dEpub_format"] == "epub" and o["dEpub_cdn"] == "ePub", o
    assert o["dCsv_format"] == "csv" and o["dCsv_cdn"] == "Papa", o
    assert o["dTsv_format"] == "tsv" and o["dTsv_cdn"] == "Papa", o
    # Native formats
    assert o["dJson_format"] == "json" and o["dJson_cdn"] is None, o
    # Images / videos group to "image" / "video" (the legacy RENDERERS
    # table shares one render function across every image extension
    # and one across every video extension).
    assert o["dPng_format"] == "image" and o["dPng_cdn"] is None, o
    # Unsupported / legacy fall through to "unknown"
    assert o["dDoc_format"] == "doc", o  # legacy DOC keeps its label
    assert o["dZip_format"] == "unknown", (
        f"unsupported ext must route to 'unknown'; got {o['dZip_format']!r}"
    )


def test_format_size_helper(driver_output: dict) -> None:
    o = driver_output
    assert o["sB"].endswith("B") and not o["sB"].endswith("KB"), o
    assert o["sKB"].endswith("KB"), o
    assert o["sMB"].endswith("MB"), o
    assert o["sGB"].endswith("GB"), o
    assert o["sN"] == "?", f"formatSize(null) must return '?'; got {o['sN']!r}"
