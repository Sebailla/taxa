"""
Research domain contract tests (W1 of `complete-frontend-migration`).

Pins the canonical pure-typed Research domain contract introduced in
W1: `ExplorerState`, `ViewerTab`, `FileFormat`, `SearchState`, plus
`createInitialExplorerState()` and the supporting tree-node types the
explorer carries in `state.explorer.tree`.

The contract is the foundation every later explorer work unit
(W2–W6: ports / search / renderers) builds on, so this test guards
the public typed surface verbatim:

  - `ExplorerState` mirrors the legacy `web/state.js::state.explorer`
    shape (`rootTaxonId`, `tree`, `openFilePath`, `openFileFormat`,
    `viewerTab`, `search`) so the React cutover can read/write the
    same fields under the same types.
  - `ViewerTab` is the closed literal `"Raw" | "Table" | "Tree"` that
    matches the legacy `web/file_explorer.js::openFile` tab strip
    (and the canonical `openspec/specs/research/spec.md` "Tree viewer
    tab" requirement).
  - `FileFormat` is the file-extension identifier the legacy
    `state.explorer.openFileFormat` carries (e.g. "pdf", "epub",
    "csv", "tsv", "json", "md", "html", "txt", "doc", "docx",
    "xls", "xlsx"). Typed as a string union of the
    renderer-dispatching extensions plus an `OtherFileFormat`
    fallback so the legacy "Format .xyz not supported in viewer"
    contract survives a typed projection.
  - `SearchState` mirrors `web/state.js::state.explorer.search`
    (`{ query: "", mode: "filter", hideEmpty: true }`) so the React
    tree-search behaviour (file + spec.md "Tree search" requirement)
    can read/write the same fields without runtime coercion.
  - `createInitialExplorerState()` returns the W1-initial state —
    `rootTaxonId: null`, `tree: null`, `openFilePath: null`,
    `openFileFormat: null`, `viewerTab: "Raw"`, and the search
    defaults `{ query: "", mode: "filter", hideEmpty: true }`. The
    legacy `web/state.js::initialExplorerShape()` is the source of
    truth — W1 must reproduce it byte-for-byte so a future W6
    React mount replacing the legacy `mount()` reset produces the
    exact same fresh state.

The test asserts (1) the canonical file path exists, (2) the source
stays free of framework / I/O tokens (spec.md rule 4 — same purity
guard as `tests/test_domain_purity.py`), (3) the file compiles in
strict mode against the ES2022 library only (no DOM, no React, no
Next, no FastAPI), and (4) the compiled module returns the correct
observable behaviour at runtime under Node.

Spec.md rule 4 (domain purity) — verified via source-level guards
mirroring `tests/test_domain_purity.py::FORBIDDEN_TOKENS`. The W1
file ships only pure TypeScript types + a factory function; no
fetch, no React import, no `localStorage`, no `document`, no
`window`, no `process`.

References:
    odd/tasks/complete-frontend-migration.md          §ODD-MIGRATE-002 / W1
    openspec/specs/research/spec.md                   §Tree viewer tab,
                                                       §Tree search,
                                                       §Switching taxon
                                                       clears the explorer state
    web/state.js::initialExplorerShape()              Legacy parity oracle
    web/file_explorer.js                              Legacy viewer tabs + search
                                                       semantics (Raw / Table /
                                                       Tree, filter/highlight
                                                       mode, hideEmpty).
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAIN_FILE = REPO_ROOT / "src" / "modules" / "research" / "domain" / "explorer.ts"


# Comment-stripping regexes — mirrors `tests/test_domain_purity.py` so
# author-friendly documentation can reference forbidden-token words
# (e.g. "the browser-state module", "the legacy renderers") without
# tripping the purity guard. Block comments are matched first so a
# `//` inside a `/* ... */` is not treated as a line comment opener.
# Each substitution replaces comment characters with spaces (newlines
# pass through), so diagnostic line numbers stay aligned with the
# original source.
_BLOCK_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/")
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _blank_match(match: re.Match[str]) -> str:
    """Replace every character in a match with a space; keep newlines
    intact so line numbers stay aligned with the original source."""
    return re.sub(r"[^\n]", " ", match.group(0))


def _strip_ts_comments(text: str) -> str:
    """Remove line and block comments (including JSDoc) from `text`,
    preserving line numbers so caller diagnostics stay accurate."""
    text = _BLOCK_COMMENT_RE.sub(_blank_match, text)
    text = _LINE_COMMENT_RE.sub(_blank_match, text)
    return text

# Pinned ViewerTab literal — mirrors the legacy tab strip wired by
# `web/file_explorer.js::openFile` (the three buttons in the order
# the spec's tab strip enumerates). A future PR that drops any tab
# breaks the React cutover's wired surface.
EXPECTED_VIEWER_TABS: tuple[str, ...] = ("Raw", "Table", "Tree")

# Pinned SearchMode literal — mirrors `web/state.js::state.explorer.search.mode`
# where `runSearch()` switches between "filter" (hide non-matches) and
# "highlight" (paint matches). Adding a third mode would be a spec
# change; the closed union keeps the typed surface honest.
EXPECTED_SEARCH_MODES: tuple[str, ...] = ("filter", "highlight")

# Pinned FileFormat literal — the renderer-dispatching extensions the
# legacy `web/file_viewer.js` table enumerates, plus an
# `OtherFileFormat` fallback for the "Format .xyz not supported in
# viewer" contract. A future PR that drops any of these (e.g. moves
# "epub" to OtherFileFormat) would silently regress the typed viewer
# surface; the pinned tuple keeps the union honest.
EXPECTED_FILE_FORMATS: tuple[str, ...] = (
    # Document renderer family — `file_viewer.js::renderPdf`, etc.
    "pdf", "epub",
    # Plain / marked-up text family.
    "html", "htm", "md", "txt",
    # Legacy MS Word / OOXML family.
    "doc", "docx",
    # Spreadsheet family (Table tab on .xls/.xlsx is dispatched via
    # SheetJS, but the FileFormat union still names them so the viewer
    # can render the Raw iframe + meta strip — see
    # `web/file_viewer.js::renderXls`).
    "xls", "xlsx",
    # Tabular data (Table tab renderer).
    "csv", "tsv",
    # JSON (Tree tab renderer).
    "json",
    # Image family (rendered via `<img>` / inline SVG — see
    # `web/file_viewer.js::renderImage`).
    "jpg", "jpeg", "png", "gif", "webp", "bmp", "svg",
    # Video family (rendered via `<video>` — see
    # `web/file_viewer.js::renderVideo`).
    "mp4", "webm", "ogv",
)


def _has_npx() -> bool:
    return shutil.which("npx") is not None


def _has_node() -> bool:
    return shutil.which("node") is not None


@pytest.fixture()
def require_toolchain() -> None:
    if not (_has_npx() and _has_node()):
        pytest.skip("npx + node required on PATH for compile/runtime test")


# ---------------------------------------------------------------------------
# File presence / source-level purity — no compiler required
# ---------------------------------------------------------------------------
def test_domain_file_exists() -> None:
    """`src/modules/research/domain/explorer.ts` exists at the canonical
    path W1 ships. RED marker: before the file lands, this assertion
    fails outright.
    """
    assert DOMAIN_FILE.is_file(), (
        f"missing domain file: {DOMAIN_FILE}. W1 ships this file."
    )


def test_domain_file_is_plain_typescript() -> None:
    """`.ts`, not `.tsx` — domain stays plain types (spec.md rule 4,
    design.md §Interfaces/Contracts). JSX belongs to presentation."""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    assert DOMAIN_FILE.suffix == ".ts", (
        f"domain file must be TypeScript; got suffix={DOMAIN_FILE.suffix}"
    )


def test_domain_file_has_no_framework_or_io_imports() -> None:
    """Spec.md rule 4: domain stays free of presentation, application,
    browser, HTTP, framework, or infrastructure. Source-level guard
    mirrors `tests/test_domain_purity.py::test_domain_ts_files_have_no_forbidden_token`
    — catches accidental `from 'react'` / `from 'next/...'` /
    `fetch(...)` / `localStorage.*` / `document.*` / `window.*` /
    `process.*` references before they reach review.
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = _strip_ts_comments(DOMAIN_FILE.read_text())
    # Same token list as `tests/test_domain_purity.py::FORBIDDEN_TOKENS`,
    # reduced to the categories a W1 Research-domain file would
    # realistically trip on. Comments are stripped so author-friendly
    # documentation can reference forbidden-token words (e.g.
    # "browser-state module", "the legacy `localStorage` reader") in
    # JSDoc without tripping the guard — mirrors the existing
    # taxonomy-domain purity test.
    forbidden_tokens = (
        # framework
        "react", "next", "nextjs",
        "fastapi", "starlette", "pydantic",
        # I/O / network
        "fetch(",
        # browser
        "localStorage", "document.", "window.",
        # node process
        "process.",
    )
    for token in forbidden_tokens:
        assert token not in text, (
            f"explorer.ts must stay free of {token!r}; spec.md rule 4 "
            f"forbids framework / I/O references in the domain layer."
        )


def test_domain_file_does_not_import_other_modules() -> None:
    """Spec.md rule 4 (inward deps): domain → self only. A future PR
    that pulls `@taxa/taxonomy`, `@taxa/browser-state`, or
    `@taxa/app-shell` into the Research domain would create a
    cross-module domain dependency — the layered rule keeps Research
    domain free to define its own types without inheriting any
    other module's contract. Comments are stripped so JSDoc can
    reference these module names without tripping the guard —
    mirrors `tests/test_domain_purity.py`."""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = _strip_ts_comments(DOMAIN_FILE.read_text())
    for forbidden in (
        "@taxa/taxonomy",
        "@taxa/research/application",
        "@taxa/research/infrastructure",
        "@taxa/research/presentation",
        "@taxa/browser-state",
        "@taxa/app-shell",
        "@taxa/design-system",
    ):
        assert forbidden not in text, (
            f"research/domain explorer.ts must not import {forbidden!r} "
            f"(spec.md rule 4 — domain stays free of other modules / "
            f"downstream layers)."
        )


def test_domain_file_exports_required_names() -> None:
    """W1 commits to the named exports `ExplorerState`, `ViewerTab`,
    `FileFormat`, `SearchState`, `ExplorerTree`, plus
    `createInitialExplorerState` as the public factory. Dropping any
    of these breaks the React cutover's typed surface (W2–W6 build
    on the same exports). The barrel re-export breaks on a default
    export, so we pin named exports only.
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    for name in (
        "ExplorerState", "ViewerTab",
        "FileFormat", "SearchState", "ExplorerTree",
        "createInitialExplorerState",
    ):
        pattern = (
            rf"export\s+(?:interface|type|const|function)\s+{name}\b"
            rf"|export\s+\{{\s*{name}\b"
        )
        assert re.search(pattern, text), (
            f"explorer.ts must export `{name}` as a named interface, "
            f"type alias, const, function, or named re-export."
        )


def test_domain_file_viewer_tab_literal_lists_all_three_tabs() -> None:
    """ViewerTab is the closed union `"Raw" | "Table" | "Tree"`. The
    three literals MUST appear in `explorer.ts` so a future PR cannot
    silently rename one (e.g. `"Raw" → "Source"`) without breaking
    this assertion. Mirrors `web/file_explorer.js::openFile`'s tab
    strip and `openspec/specs/research/spec.md` "Tree viewer tab".
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    for tab in EXPECTED_VIEWER_TABS:
        assert f'"{tab}"' in text, (
            f"explorer.ts ViewerTab union must include {tab!r}."
        )


def test_domain_file_search_mode_literal_lists_both_modes() -> None:
    """SearchMode is the closed union `"filter" | "highlight"`.
    Mirrors `web/state.js::state.explorer.search.mode` where
    `runSearch()` switches between the two. A future PR that drops
    either breaks the React cutover's tree-search behaviour.
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    for mode in EXPECTED_SEARCH_MODES:
        assert f'"{mode}"' in text, (
            f"explorer.ts SearchState mode union must include {mode!r}."
        )


def test_domain_file_search_state_defaults_are_pinned() -> None:
    """`createInitialExplorerState()` MUST return the W1-initial
    search state — `{ query: "", mode: "filter", hideEmpty: true }`.
    Mirrors `web/state.js::initialExplorerShape()::search` byte-for-
    byte: empty string, filter mode, hideEmpty true. A future PR
    that flips any default (e.g. `mode: "highlight"`) silently
    changes every React mount's first-paint behaviour; this
    assertion pins the source-level defaults so the regression is
    caught at review.
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    # Defaults are reached via `createInitialExplorerState()` or the
    # `createInitialSearchState()` helper. Assert each literal is
    # present in the file body — the runtime harness below asserts
    # the wired value is exactly what we expect.
    assert re.search(r'query\s*:\s*""', text), (
        "createInitialExplorerState() must initialise search.query = \"\"."
    )
    assert re.search(r'mode\s*:\s*"filter"', text), (
        "createInitialExplorerState() must initialise search.mode = \"filter\"."
    )
    assert re.search(r'hideEmpty\s*:\s*true', text), (
        "createInitialExplorerState() must initialise search.hideEmpty = true."
    )


def test_domain_file_viewer_tab_default_is_raw() -> None:
    """`createInitialExplorerState()` MUST return `viewerTab: "Raw"`
    as the default — mirrors `web/state.js::initialExplorerShape()`
    and the legacy `web/file_explorer.js` open-file default. A
    future PR that flips the default to `"Table"` or `"Tree"`
    silently changes every React mount's first-paint behaviour.
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    assert re.search(r'viewerTab\s*:\s*"Raw"', text), (
        "createInitialExplorerState() must initialise viewerTab = \"Raw\"."
    )


def test_domain_file_viewer_tab_literal_is_case_sensitive_raw() -> None:
    """TRIANGULATE: the ViewerTab literal MUST use capitalised
    `"Raw"` (NOT lowercase `"raw"`) — mirrors the legacy tab button
    text (`web/file_explorer.js::openFile` paints `el("button", …,
    "Raw")`). The legacy `openspec/specs/research/spec.md` "Switching
    taxon clears the explorer state" requirement also names
    `viewerTab = "Raw"` capitalised. A future PR that downcases the
    literal silently mismatches the React cutover's tab buttons
    (which read `state.explorer.viewerTab === "Raw"`)."""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = _strip_ts_comments(DOMAIN_FILE.read_text())
    # Assert `"Raw"` appears (capitalised) and `"raw"` does NOT
    # appear as a viewer-tab literal. We allow `"raw"` to appear in
    # other contexts (e.g. comments, identifiers) but the closed
    # union literal must stay capitalised.
    assert '"Raw"' in text, "ViewerTab union must use capitalised \"Raw\"."
    # Strip the `"Raw"` instances and re-check: a future PR that
    # silently introduces `"raw"` (lowercase) as a union member
    # would slip past the bare-`"Raw"` assertion.
    text_without_raw = text.replace('"Raw"', "")
    assert '"raw"' not in text_without_raw, (
        "ViewerTab union MUST NOT include lowercase \"raw\" — "
        "the legacy tab button text is capitalised."
    )


def test_domain_file_search_mode_literal_is_case_sensitive() -> None:
    """TRIANGULATE: the SearchState.mode literal MUST use lowercase
    `"filter"` / `"highlight"` (NOT capitalised) — mirrors the
    legacy `web/state.js::state.explorer.search.mode` defaults.
    The legacy `web/file_explorer.js::toggleSearchMode()` reads
    `state.explorer.search.mode === "filter"`, so a future PR that
    capitalises the literal silently breaks the React cutover's
    mode-toggle dispatch."""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = _strip_ts_comments(DOMAIN_FILE.read_text())
    for lower in ('"filter"', '"highlight"'):
        upper = lower.upper()
        assert lower in text, (
            f"SearchState.mode union must include {lower} (lowercase)."
        )
        # Strip the lowercase instances and re-check: a future PR
        # that introduces the capitalised form as a union member
        # would slip past the bare-lowercase assertion.
        text_without_lower = text.replace(lower, "")
        assert upper not in text_without_lower, (
            f"SearchState.mode union MUST NOT include {upper} — "
            f"the legacy mode literal is {lower} (lowercase)."
        )


def test_domain_file_file_format_union_lists_every_pinned_extension() -> None:
    """TRIANGULATE: the FileFormat closed union MUST name every
    pinned extension the legacy `web/file_viewer.js` dispatcher
    handles. A future PR that drops e.g. `"epub"` (a real legacy
    renderer branch) silently regresses the typed viewer surface —
    the union still type-checks, but the React cutover's renderer
    dispatch can no longer reach the EPUB arm.
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = _strip_ts_comments(DOMAIN_FILE.read_text())
    for ext in EXPECTED_FILE_FORMATS:
        assert f'"{ext}"' in text, (
            f"FileFormat union must include {ext!r}."
        )


def test_domain_file_folder_node_declares_required_fields() -> None:
    """TRIANGULATE: the ExplorerFolderNode interface MUST declare
    `{name, path, type, children}` verbatim — mirrors the FastAPI
    `_walk_tree` folder branch in `api/server.py`. A future PR that
    silently drops e.g. `children` (or renames `type` to `kind`)
    breaks the React cutover's recursive tree render before
    review.
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    m = re.search(
        r"export\s+interface\s+ExplorerFolderNode\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, "ExplorerFolderNode interface must be declared."
    block = m.group(0)
    for field in ("name", "path", "type", "children"):
        assert re.search(rf"\b{field}\b\s*:", block), (
            f"ExplorerFolderNode must declare `{field}` (api/server.py::_walk_tree)."
        )
    # The discriminator MUST be the literal `"folder"`.
    assert re.search(r'\btype\s*:\s*"folder"', block), (
        "ExplorerFolderNode.type must be the literal \"folder\"."
    )


def test_domain_file_file_node_declares_required_fields() -> None:
    """TRIANGULATE: the ExplorerFileNode interface MUST declare
    `{name, path, type, extension, size, modified}` verbatim —
    mirrors the FastAPI `_walk_tree` file branch. A future PR that
    silently drops e.g. `size` breaks the meta strip's
    `SIZE=<bytes>` chip before review.
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    m = re.search(
        r"export\s+interface\s+ExplorerFileNode\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, "ExplorerFileNode interface must be declared."
    block = m.group(0)
    for field in ("name", "path", "type", "extension", "size", "modified"):
        assert re.search(rf"\b{field}\b\s*:", block), (
            f"ExplorerFileNode must declare `{field}` (api/server.py::_walk_tree)."
        )
    # The discriminator MUST be the literal `"file"`.
    assert re.search(r'\btype\s*:\s*"file"', block), (
        "ExplorerFileNode.type must be the literal \"file\"."
    )


def test_domain_file_explorer_state_fields_are_readonly() -> None:
    """TRIANGULATE: every field on ExplorerState MUST be declared
    `readonly` so a future reducer / store can rely on immutable
    updates (W6 React mount). The legacy `web/state.js` state
    object is mutated in place, but the typed contract surfaces
    immutable updates so a future Zustand / Redux-style store can
    take advantage of structural sharing.
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    m = re.search(
        r"export\s+interface\s+ExplorerState\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, "ExplorerState interface must be declared."
    block = m.group(0)
    for field in (
        "rootTaxonId", "tree", "openFilePath",
        "openFileFormat", "viewerTab", "search",
    ):
        assert re.search(rf"\breadonly\s+{field}\b", block), (
            f"ExplorerState.{field} must be declared `readonly`."
        )


def test_domain_file_search_state_fields_are_readonly() -> None:
    """TRIANGULATE: every field on SearchState MUST be declared
    `readonly` — mirrors the ExplorerState readonly contract and
    keeps the typed surface immutable end-to-end.
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    m = re.search(
        r"export\s+interface\s+SearchState\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, "SearchState interface must be declared."
    block = m.group(0)
    for field in ("query", "mode", "hideEmpty"):
        assert re.search(rf"\breadonly\s+{field}\b", block), (
            f"SearchState.{field} must be declared `readonly`."
        )


def test_domain_file_does_not_export_default() -> None:
    """TRIANGULATE: the file MUST NOT export a default symbol.
    The barrel re-export breaks on a default export (W1 contract
    pins named exports only — see `test_domain_file_exports_required_names`).
    A future PR that flips to `export default …` would silently
    break the React cutover's typed import surface; this guard
    catches the regression at review.
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    assert not re.search(r"^\s*export\s+default\b", text, re.MULTILINE), (
        "explorer.ts must NOT export a default symbol — the W1 contract "
        "pins named exports only."
    )


def test_domain_file_tree_field_is_optional_on_explorer_state() -> None:
    """`ExplorerState.tree` MUST be typed nullable (`ExplorerTree | null`)
    — the initial state has `tree: null` and the runtime wires a
    fetched tree only after the explorer mounts. A future PR that
    drops the nullability (e.g. `tree: ExplorerTree`) would force
    every consumer to fabricate a tree-shaped placeholder before
    the explorer has fetched anything."""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    # The `ExplorerState` interface MUST declare `tree` as
    # `ExplorerTree | null`. Scan the ExplorerState block (a single
    # `interface ExplorerState { … }` declaration) so a search-replace
    # that mangles the field stays caught.
    m = re.search(
        r"export\s+interface\s+ExplorerState\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, "ExplorerState interface must be declared in explorer.ts."
    block = m.group(0)
    assert re.search(
        r"\btree\s*:\s*ExplorerTree\s*\|\s*null\b",
        block,
    ), (
        "ExplorerState.tree must be typed `ExplorerTree | null` "
        "(initial state is null; fetched tree replaces it)."
    )


def test_domain_file_file_format_default_is_null() -> None:
    """`ExplorerState.openFileFormat` MUST default to `null` and be
    typed `FileFormat | null`. The legacy state stores the file's
    extension as `openFileFormat` (`web/state.js::initialExplorerShape`),
    so the typed contract must mirror the nullability.
    """
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    m = re.search(
        r"export\s+interface\s+ExplorerState\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, "ExplorerState interface must be declared in explorer.ts."
    block = m.group(0)
    assert re.search(
        r"\bopenFileFormat\s*:\s*FileFormat\s*\|\s*null\b",
        block,
    ), (
        "ExplorerState.openFileFormat must be typed `FileFormat | null` "
        "(no file open at mount time)."
    )
    # The default `null` literal MUST also be reachable from
    # `createInitialExplorerState()`.
    assert re.search(r"openFileFormat\s*:\s*null", text), (
        "createInitialExplorerState() must initialise openFileFormat = null."
    )


# ---------------------------------------------------------------------------
# Compile in isolation — single file, strict mode, ES2022 only.
# ---------------------------------------------------------------------------
def _run_tsc_isolated(source: Path, out_dir: Path) -> subprocess.CompletedProcess:
    """Compile `explorer.ts` in isolation. Flags mirror project tsconfig +
    design.md §Interfaces/Contracts: `--strict`, `--target ES2022`,
    `--module commonjs` (so Node can `require` the output), `--lib
    ES2022` (no DOM — domain must not depend on browser types)."""
    return subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--strict",
            "--target", "ES2022",
            "--module", "commonjs",
            "--lib", "ES2022",
            "--skipLibCheck",
            "--esModuleInterop",
            "--outDir", str(out_dir),
            str(source),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


# Runtime harness — loaded by Node after tsc has emitted explorer.js.
# Exercises every externally observable export. The harness mirrors
# the ODD-MIGRATE-001 W1 contract: `createInitialExplorerState()`
# returns the legacy `web/state.js::initialExplorerShape()` byte-for-
# byte (rootTaxonId/tree/openFilePath/openFileFormat all null,
# viewerTab "Raw", search defaults "" / "filter" / true). The
# harness uses strict equality so a future PR that flips any default
# silently fails at compile time.
_HARNESS_SOURCE = r"""
const path = require("path");
const domain = require(path.resolve(process.argv[2]));
const cases = {
  createInitialExplorerState_returns_object:
    typeof domain.createInitialExplorerState === "function",
  // W1 mirror — every resetable field starts at null, viewerTab at
  // "Raw", search at the legacy defaults. Mirrors
  // web/state.js::initialExplorerShape().
  initial_root_taxon_id_is_null: (() => {
    const s = domain.createInitialExplorerState();
    return s !== null && typeof s === "object" && s.rootTaxonId === null;
  })(),
  initial_tree_is_null: (() => {
    const s = domain.createInitialExplorerState();
    return s.tree === null;
  })(),
  initial_open_file_path_is_null: (() => {
    const s = domain.createInitialExplorerState();
    return s.openFilePath === null;
  })(),
  initial_open_file_format_is_null: (() => {
    const s = domain.createInitialExplorerState();
    return s.openFileFormat === null;
  })(),
  initial_viewer_tab_is_raw: (() => {
    const s = domain.createInitialExplorerState();
    return s.viewerTab === "Raw";
  })(),
  // SearchState defaults — match legacy search contract verbatim.
  initial_search_query_is_empty_string: (() => {
    const s = domain.createInitialExplorerState();
    return s.search !== null
      && typeof s.search === "object"
      && s.search.query === "";
  })(),
  initial_search_mode_is_filter: (() => {
    const s = domain.createInitialExplorerState();
    return s.search.mode === "filter";
  })(),
  initial_search_hide_empty_is_true: (() => {
    const s = domain.createInitialExplorerState();
    return s.search.hideEmpty === true;
  })(),
  // Each call returns a NEW object — mutating one initial state
  // must not bleed into a sibling. Mirrors the legacy
  // `initialExplorerShape()` factory which returns a fresh literal
  // every call.
  initial_states_are_independent: (() => {
    const a = domain.createInitialExplorerState();
    const b = domain.createInitialExplorerState();
    a.viewerTab = "Table";
    a.search.query = "x";
    return b.viewerTab === "Raw" && b.search.query === "";
  })(),
  initial_search_objects_are_independent: (() => {
    const a = domain.createInitialExplorerState();
    const b = domain.createInitialExplorerState();
    a.search.hideEmpty = false;
    a.search.mode = "highlight";
    return b.search.hideEmpty === true && b.search.mode === "filter";
  })(),
};
const failed = Object.keys(cases).filter((k) => cases[k] !== true);
if (failed.length > 0) {
  process.stderr.write(
    "FAILED_CASES: " + JSON.stringify(failed) + "\n" +
    "ALL_CASES: " + JSON.stringify(cases) + "\n"
  );
  process.exit(1);
}
process.stdout.write("PASS\n");
"""


@pytest.fixture()
def compiled_domain(tmp_path: Path, require_toolchain: None) -> tuple[Path, Path]:
    """Compile `explorer.ts` to CommonJS in `tmp_path/build/`, write the
    Node harness, return the (compiled-module path, harness path)."""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    result = _run_tsc_isolated(DOMAIN_FILE, out_dir)
    assert result.returncode == 0, (
        f"explorer.ts failed to compile in isolated strict mode.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    compiled = out_dir / "explorer.js"
    assert compiled.is_file(), (
        f"tsc did not emit a compiled module at {compiled}. "
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    harness = tmp_path / "harness.cjs"
    harness.write_text(_HARNESS_SOURCE)
    return compiled, harness


def test_compiled_module_passes_runtime_contract(
    compiled_domain: tuple[Path, Path],
) -> None:
    """Loaded under Node (ES2022 only, no DOM), the compiled module
    returns the correct observable behaviour for every public export —
    catching type errors that become runtime exceptions, shape errors
    that pass strict mode but fail at runtime, and helpers that
    compile cleanly but return the wrong value. The harness checks
    the W1 contract end-to-end:

      1. `createInitialExplorerState` is exported as a function.
      2. Every resetable field defaults to `null`.
      3. `viewerTab` defaults to `"Raw"`.
      4. `search.{query, mode, hideEmpty}` defaults to
         `"", "filter", true` — the legacy byte-identical contract.
      5. Two calls return independent objects (no shared references
         — the legacy `initialExplorerShape()` returns a fresh literal
         on every call).
    """
    compiled, harness = compiled_domain
    result = subprocess.run(
        ["node", str(harness), str(compiled)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"runtime harness failed.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected harness output: {result.stdout!r}"
    )
