"""
Research /explorer mount contract tests (W6.1 of
`complete-frontend-migration`).

Pins the isolated `/explorer` route — the smallest non-CDN
React Explorer/Viewer mount built on the completed W1–W4b4
contracts. The mount ships five files:

  - `src/app/explorer/page.tsx`           — Server Component
                                             (passes only
                                             serializable props)
  - `src/modules/research/presentation/Explorer.tsx`
                                          — Client island
                                             (top-level
                                             lifecycle +
                                             recursive tree)
  - `src/modules/research/presentation/FileTree.tsx`
                                          — Client component
                                             (recursive
                                             folder/file rows)
  - `src/modules/research/presentation/Viewer.tsx`
                                          — Client component
                                             (non-CDN W4a
                                             viewer rendering)
  - `src/modules/research/presentation/ExplorerErrorBoundary.tsx`
                                          — Client component
                                             (component-level
                                             error boundary)
  - `src/modules/research/presentation/explorer-state.ts`
                                          — Pure state kernel
                                             (typed transitions
                                             + helper functions)
  - `src/modules/research/index.ts`        — Public barrel
                                             (re-exports the
                                             new components +
                                             kernel helpers +
                                             W1 domain types)

W6.1 contract (verbatim from the task brief):

  "Create the smallest non-CDN React Explorer/Viewer mount
   using the completed Research W1–W4b4 contracts. Read the
   tracker, W1–W4b4 barrels/contracts, current taxonomy
   client-island conventions, and installed Next docs already
   mapped. Technical correction: a Server Component cannot
   pass repository functions to a Client Component; the
   client island must construct/use the W3 adapter through
   the public `@taxa/research` barrel with same-origin base
   URL, while tests inject a repository only inside
   client/test boundaries. `/explorer/page.tsx` stays a
   Server Component and passes only serializable props.

   Include: initial tree load/retry/empty/error; recursive
   folder/file rows with accessible expand/select/
   double-click; non-CDN W4a viewer rendering; typed state
   and tab behavior; safe extension fallback; component-
   level error state; public barrel export. Keep the route
   isolated from `src/app/page.tsx`, legacy `web/`, FastAPI,
   browser state, search, splitter, materialization, CDN
   viewers, and cutover. Do not introduce new dependencies,
   no Next Script, no CDN/DOM parsing. Add focused hermetic
   tests and tracker progress marked pending independent
   verification. Run focused plus prior Research regression
   /type checks. Do not commit, push, PR, or edit outside
   declared surfaces."

The contract is the first React mount the Research module
ships. Every layer of the contract is pinned by a focused
test:

  - File presence (5 new files + the barrel update).
  - Server Component purity (`page.tsx` has NO `"use client"`
    directive and passes only the `apiOrigin: string` prop).
  - Client Component boundaries (Explorer / FileTree /
    Viewer / ExplorerErrorBoundary each declare
    `"use client"` at the top of the file).
  - Framework-free kernel (`explorer-state.ts` has no
    React / Next / FastAPI / Starlette / DOM / localStorage /
    process tokens — mirrors the W1 + W4a + W4b contract
    purity tests).
  - Barrel re-export contract (the W1 domain types, the
    W2 ports, the W3 adapter, the W4a–W4b4 renderers, the
    kernel helpers, and the four React components are all
    reachable through `@taxa/research`).
  - Strict isolated TypeScript compile (the state kernel +
    the W1 domain + the W4 renderers compile under
    `--lib ES2022` only — no DOM, no framework types).
  - Runtime harness (the pure state helpers execute
    correctly under Node — toggleExpansion round-trips,
    bytesRequiredForFormat matches the W6.1 contract,
    castFileFormat falls back to "other" for unknown
    extensions, buildServeUrl URL-encodes verbatim,
    enumerateFiles yields every file in depth-first order).
  - Project-wide strict typecheck (`tsc --noEmit
    --strict --project tsconfig.json` passes across the
    new files).
  - Isolation guard (the W6.1 mount does not import from
    `src/app/page.tsx`, `web/`, FastAPI, browser-state,
    app-shell internals, or any CDN-script surface).

References:
    odd/tasks/complete-frontend-migration.md            §ODD-MIGRATE-003 / W6.1
    openspec/specs/research/spec.md                     §Recursive directory
                                                          listing endpoint,
                                                          §Multi-format file
                                                          viewer
    api/server.py::list_research_root                   Tree-shape oracle
    api/server.py::serve_research_file                  File-serve oracle
    web/file_explorer.js::mount()                       Legacy tree fetcher
    web/file_explorer.js::renderFolderRow /
        renderFileRow / selectFolder / selectFile /
        openFile / renderTreePaneEmpty / renderTreePaneSkeleton
                                                       Legacy row + state
                                                          oracles
    web/file_viewer.js::renderPdf / renderHtml /
        renderAsPre / renderImage / renderSvg /
        renderVideo / renderUnsupported /
        renderOfflineBanner / renderImageError
                                                       Legacy renderer
                                                          oracles
    web/state.js::initialExplorerShape                  Legacy initial
                                                          state oracle
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_EXPLORER_PAGE = (
    REPO_ROOT / "src" / "app" / "explorer" / "page.tsx"
)
RESEARCH_DIR = REPO_ROOT / "src" / "modules" / "research"
EXPLORER_STATE_FILE = (
    RESEARCH_DIR / "presentation" / "explorer-state.ts"
)
EXPLORER_FILE = RESEARCH_DIR / "presentation" / "Explorer.tsx"
FILE_TREE_FILE = RESEARCH_DIR / "presentation" / "FileTree.tsx"
VIEWER_FILE = RESEARCH_DIR / "presentation" / "Viewer.tsx"
ERROR_BOUNDARY_FILE = (
    RESEARCH_DIR / "presentation" / "ExplorerErrorBoundary.tsx"
)
BARREL_FILE = RESEARCH_DIR / "index.ts"
DOMAIN_FILE = RESEARCH_DIR / "domain" / "explorer.ts"
RENDERERS_FILE = RESEARCH_DIR / "application" / "renderers.ts"

# Comment-stripping regexes — mirrors `tests/test_domain_purity.py`
# so author-friendly documentation can reference forbidden-token
# words (e.g. "the React mount", "the browser-state module") in
# JSDoc without tripping the application-layer purity guard.
_BLOCK_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/")
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _strip_ts_comments(text: str) -> str:
    """Remove line + block comments (including JSDoc) from `text`,
    preserving line numbers so caller diagnostics stay accurate."""
    text = _BLOCK_COMMENT_RE.sub(
        lambda m: re.sub(r"[^\n]", " ", m.group(0)),
        text,
    )
    text = _LINE_COMMENT_RE.sub(
        lambda m: re.sub(r"[^\n]", " ", m.group(0)),
        text,
    )
    return text


def _split_top_level_args(body: str) -> list[str]:
    """Split a function-argument body by top-level commas,
    respecting nested parens, braces, brackets, and string
    literals. Used by the FileTree folder-row handler
    separation test to extract the 5th + 6th arguments of
    `renderFolderRow(...)` so the test can verify that the
    select slot (6th arg) does NOT route back into the
    expand handler (`onToggleExpand`). Naive
    `body.split(",")` would break on `(folderPath) =>
    onToggleExpand(folderPath),` lambdas; this helper walks
    the string with a depth + string-literal stack so the
    split stays correct at every nesting level. The
    companion strict typecheck + project-wide tsc gate
    guarantees the helper sees structurally valid JSX —
    the test never has to parse a half-typed signature.
    """
    args: list[str] = []
    depth = 0
    start = 0
    in_str: str | None = None
    for i, c in enumerate(body):
        if in_str is not None:
            if c == in_str and (i == 0 or body[i - 1] != "\\"):
                in_str = None
            continue
        if c in '"\'':
            in_str = c
            continue
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        elif c == "," and depth == 0:
            args.append(body[start:i])
            start = i + 1
    if start < len(body):
        args.append(body[start:])
    return args


@pytest.fixture()
def require_toolchain() -> None:
    """Skip when npx / node are not on PATH — the focused compile +
    runtime harness needs both to validate the kernel."""
    if not (shutil.which("npx") and shutil.which("node")):
        pytest.skip("npx + node required on PATH for compile/runtime test")


# Forbidden tokens for the presentation state kernel. Spec.md
# rule 4: presentation depends on domain ONLY — no framework,
# no I/O, no browser state, no HTTP transport. The list mirrors
# the W4a purity guard (`tests/test_research_renderers.py::
# _FORBIDDEN`) but ADDS the React / JSX guard because the W4a
# dispatcher is intentionally framework-free while the W6.1
# state kernel stays framework-free too (only the React
# components in `Explorer.tsx` / `Viewer.tsx` / etc. use
# React). The kernel is the typed hand-off surface so a
# future presentation-only slice can import it through the
# barrel and compile it in isolation under `--lib ES2022`.
# Comments are stripped before scanning so JSDoc can
# reference forbidden-token words.
_KERNEL_FORBIDDEN: tuple[str, ...] = (
    # framework (the kernel is intentionally framework-free)
    "from 'react'", 'from "react"',
    "from 'next'",   'from "next"',
    "from 'nextjs'", 'from "nextjs"',
    "from 'fastapi'", 'from "fastapi"',
    "from 'starlette'", 'from "starlette"',
    # I/O — kernel is pure.
    "fetch(",
    # browser / process state.
    "DOMParser",
    "document.",
    "window.",
    "localStorage",
    "process.",
    # CommonJS / globalThis guards — kernel stays ESM-only.
    "require(",
    "globalThis",
    # Reverse deep imports — kernel depends on domain only.
    "../infrastructure",
    "../presentation",
    "../index",
    "../../taxonomy",
    "../../design-system",
    "../../browser-state",
    "../../app-shell",
)


# Forbidden tokens for the Server Component `page.tsx`. The
# page must NOT import from `@taxa/research/presentation/*`
# (the client-island deep imports), NOT pass repository
# functions to a Client Component, NOT import from
# `@taxa/browser-state` or any non-barrel surface. The page
# stays free of `"use client"` (it's a Server Component) +
# free of any I/O / framework / CDN surface.
_PAGE_FORBIDDEN: tuple[str, ...] = (
    # No "use client" — page.tsx is a Server Component.
    "\"use client\"", "'use client'",
    # No deep imports into the presentation layer.
    "@taxa/research/presentation",
    "src/modules/research/presentation",
    # No FastAPI / Starlette / CDN imports.
    "fastapi", "starlette",
    "cdn.jsdelivr.net",
    # No direct fetch() call (Server Components can fetch,
    # but the W6.1 page does not — the client island
    # owns the network lifecycle).
    "fetch(",
)


# ---------------------------------------------------------------------------
# File presence + extension contracts.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "path,label,suffix",
    [
        (APP_EXPLORER_PAGE, "page.tsx", ".tsx"),
        (EXPLORER_STATE_FILE, "explorer-state.ts", ".ts"),
        (EXPLORER_FILE, "Explorer.tsx", ".tsx"),
        (FILE_TREE_FILE, "FileTree.tsx", ".tsx"),
        (VIEWER_FILE, "Viewer.tsx", ".tsx"),
        (ERROR_BOUNDARY_FILE, "ExplorerErrorBoundary.tsx", ".tsx"),
    ],
)
def test_w6_1_file_present(path: Path, label: str, suffix: str) -> None:
    """Every W6.1 file lands at the canonical path with the
    canonical extension. RED marker: before the file lands,
    this assertion fails outright so the focused compile
    + runtime harness also skip. The pure kernel uses
    `.ts` (no JSX); every React component uses `.tsx`
    (JSX + `"use client"` boundary)."""
    assert path.is_file(), (
        f"missing W6.1 file: {path} (label={label}). The W6.1 "
        f"mount ships this file as one of the five-layer "
        f"contract."
    )
    assert path.suffix == suffix, (
        f"W6.1 {label} must have extension {suffix!r} (got "
        f"{path.suffix!r}). The pure kernel uses .ts (no JSX); "
        f"the React components use .tsx (JSX)."
    )


# ---------------------------------------------------------------------------
# Server Component purity — page.tsx stays a Server Component
# and passes only serializable props.
# ---------------------------------------------------------------------------
def test_explorer_page_is_server_component() -> None:
    """`/explorer/page.tsx` MUST be a Server Component (no
    `"use client"` directive). The page is the only Server
    Component in the W6.1 mount — every consumer below is a
    Client Component. A future PR that accidentally adds
    `"use client"` to the page would silently move the
    initial render to the browser and break the static-
    export contract (Next 16's `output: "export"` requires
    the route entry to be a Server Component)."""
    if not APP_EXPLORER_PAGE.is_file():
        pytest.skip("explorer page not present yet")
    text = APP_EXPLORER_PAGE.read_text()
    assert "\"use client\"" not in text, (
        "page.tsx must NOT declare 'use client' — the route is "
        "a Server Component. The W6.1 contract pins this so the "
        "static-export entry stays server-rendered."
    )
    assert "'use client'" not in text, (
        "page.tsx must NOT declare 'use client' (single-quoted) "
        "either — the W6.1 Server Component contract is exact."
    )


def test_explorer_page_passes_only_serializable_props() -> None:
    """The page MUST pass only serializable props to the
    `Explorer` client island. A Server Component cannot pass
    repository functions to a Client Component (React's
    RSC payload is JSON-serializable only) — the W3
    adapter is constructed inside the client island through
    the public `@taxa/research` barrel with the same-origin
    base URL. This guard catches a future PR that
    accidentally tries to pass a function (e.g. a
    `fetchFiles` reference) through the boundary.

    The check scans for `Explorer.*props` patterns that
    include non-serializable shapes (functions, class
    instances). Strings + numbers + booleans + plain
    objects are the only allowed shape. The `apiOrigin`
    prop is a plain string."""
    if not APP_EXPLORER_PAGE.is_file():
        pytest.skip("explorer page not present yet")
    text = APP_EXPLORER_PAGE.read_text()
    # The Explorer prop must be a string literal or a
    # bare identifier that resolves to a string. The W6.1
    # mount hard-codes the same-origin base URL via the
    # `apiOrigin` prop — the page passes the literal
    # `"/api"` to keep the W3 adapter same-origin.
    assert "apiOrigin" in text, (
        "page.tsx must pass an `apiOrigin` string prop to the "
        "Explorer client island."
    )
    # The page MUST NOT pass any function-shaped prop.
    for forbidden in (
        "fetchFiles={", "fetchFileServe={",
        "dispatchViewer={", "sanitizeSvgMarkup={",
    ):
        assert forbidden not in text, (
            f"page.tsx must NOT pass {forbidden!r} as a prop — "
            f"Server Components cannot pass repository functions "
            f"to Client Components. The W6.1 contract pins this; "
            f"the W3 adapter is constructed inside the client "
            f"island through the public barrel."
        )


def test_explorer_page_isolated_from_other_routes() -> None:
    """The `/explorer` page must NOT import from
    `src/app/page.tsx` (the existing main index route) and
    must NOT mutate the legacy `web/` directory. The W6.1
    mount is isolated — a future cutover would land in a
    separately authorized release boundary. Comments are
    stripped before scanning so JSDoc can reference the
    legacy `web/` directory as documentation without
    tripping the isolation guard."""
    if not APP_EXPLORER_PAGE.is_file():
        pytest.skip("explorer page not present yet")
    text = _strip_ts_comments(APP_EXPLORER_PAGE.read_text())
    for forbidden in (
        "../page", "./page", "../page.tsx",
        "@taxa/app-shell/presentation/AppShell",
        "src/modules/app-shell",
        "web/", "../web", "@taxa/web",
    ):
        assert forbidden not in text, (
            f"page.tsx must NOT touch {forbidden!r} — the W6.1 "
            f"mount is isolated from the existing taxonomy "
            f"entry point and the legacy `web/` directory."
        )


def test_explorer_page_purity() -> None:
    """`page.tsx` stays free of forbidden tokens (no
    FastAPI / Starlette / CDN / direct `fetch()` /
    no `<Script>` import / no `@taxa/browser-state`). The
    route is the Server-Component entry — the client island
    owns the network lifecycle and the CDN-script surface
    (which is out of scope for W6.1)."""
    if not APP_EXPLORER_PAGE.is_file():
        pytest.skip("explorer page not present yet")
    text = APP_EXPLORER_PAGE.read_text()
    for token in _PAGE_FORBIDDEN:
        assert token not in text, (
            f"page.tsx must stay free of {token!r}; the W6.1 "
            f"Server Component contract forbids it."
        )


# ---------------------------------------------------------------------------
# Client Component boundary — every React presentation file
# declares `"use client"` at the top.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "path",
    [EXPLORER_FILE, FILE_TREE_FILE, VIEWER_FILE, ERROR_BOUNDARY_FILE],
)
def test_w6_1_react_component_declares_use_client(path: Path) -> None:
    """Every W6.1 React component MUST declare `"use client"`
    at the top of the file (above the imports). The
    directive establishes the Client Component boundary so
    the React tree below can use `useState` / `useEffect` /
    `useCallback` / event handlers / etc. The W6.1 mount's
    Server-Component entry (`page.tsx`) is the boundary
    parent; the four React components are the boundary
    children."""
    if not path.is_file():
        pytest.skip(f"{path.name} not present yet")
    text = path.read_text()
    # The directive must be at the very top (above the
    # first import). Tolerates leading whitespace.
    head = text.lstrip()
    assert head.startswith(("\"use client\"", "'use client'")), (
        f"{path.name} must declare 'use client' at the top of "
        f"the file (above the imports). The W6.1 Client "
        f"Component boundary contract pins this so the React "
        f"tree below can use the React hooks + event handlers."
    )


# ---------------------------------------------------------------------------
# Folder-row handler separation — FileTree keeps the row's
# single-click select handler distinct from the chevron +
# keyboard ArrowRight/ArrowLeft expand handler, so a
# single-click on the folder row selects (highlights) without
# expanding.
# ---------------------------------------------------------------------------
def test_w6_1_file_tree_folder_row_separates_select_from_expand() -> None:
    """W6.1 folder-row contract: a single-click on the folder
    row selects / highlights the folder (mirrors the legacy
    `web/file_explorer.js::selectFolder` shape — highlight-
    only, never opens any file); the chevron click + the
    `ArrowRight` / `ArrowLeft` keyboard keys toggle
    expansion. The W6.1 mount MUST wire the row's `onClick`
    to a DISTINCT select handler (not the expand handler),
    keep `stopPropagation` on the chevron + folder-icon
    spans so a chevron click does NOT also fire the row's
    select signal, and preserve the keyboard expansion
    contract verbatim.

    Comments are stripped before scanning so JSDoc can
    reference the legacy handler names (`selectFolder`,
    `onToggleExpand`) without tripping the guard. This
    guards against a regression where the call sites of
    `renderFolderRow(...)` were silently wired to the
    same handler as the chevron, causing a single-click to
    expand AND select — the bug the W6.1 contract
    explicitly forbids (and the bug the row's docblock
    already pins the inverse of).
    """
    if not FILE_TREE_FILE.is_file():
        pytest.skip("FileTree.tsx not present yet")
    text = _strip_ts_comments(FILE_TREE_FILE.read_text())

    # 1. Row's onClick MUST invoke onSelectFolder — single-click
    #    selects/highlights (no expansion). The chevron + Arrow
    #    keys still drive expansion; the row click must NOT
    #    trigger onToggleExpand.
    row_onclick = re.search(
        r'onClick=\{[^}]*onSelectFolder\(',
        text,
    )
    assert row_onclick, (
        "FileTree folder row's onClick must call "
        "onSelectFolder (the single-click = select signal). "
        "The chevron click + ArrowRight/ArrowLeft still drive "
        "expansion; the row click must NOT trigger "
        "onToggleExpand."
    )

    # 2. Chevron + folder-icon spans MUST stopPropagation
    #    before calling onToggleExpand — the chevron click is
    #    the EXPLICIT expand toggle and must not bubble into
    #    the row's select handler.
    chevron_with_stop = re.search(
        r'stopPropagation\(\);?\s*onToggleExpand\(',
        text,
    )
    assert chevron_with_stop, (
        "FileTree chevron (and folder-icon) spans must call "
        "onToggleExpand with stopPropagation so a chevron "
        "click does NOT also fire the row's select handler. "
        "The chevron is the explicit expand toggle, separate "
        "from the row-click select signal."
    )

    # 3. ArrowRight/ArrowLeft MUST call onToggleExpand (the
    #    keyboard expansion contract is preserved verbatim).
    for arrow_key in ("ArrowRight", "ArrowLeft"):
        arrow_pattern = re.search(
            rf"ev\.key\s*===\s*[\"']{arrow_key}[\"']"
            r"[\s\S]{0,140}?onToggleExpand\(",
            text,
        )
        assert arrow_pattern, (
            f"FileTree folder row's keydown handler must call "
            f"onToggleExpand when ev.key === '{arrow_key}'. "
            f"ArrowRight/ArrowLeft toggle expansion; ArrowLeft "
            f"on an already-expanded folder collapses it."
        )

    # 4. Enter MUST call onSelectFolder (the keyboard activation
    #    contract for the folder row — mirrors the legacy
    #    `Enter` activates selection pattern).
    enter_pattern = re.search(
        r"ev\.key\s*===\s*[\"']Enter[\"'][\s\S]{0,140}?"
        r"onSelectFolder\(",
        text,
    )
    assert enter_pattern, (
        "FileTree folder row's keydown handler must call "
        "onSelectFolder when ev.key === 'Enter'. Enter "
        "activates the folder row's selection (mirrors the "
        "legacy `Enter` activates selection pattern)."
    )

    # 5. Every call site of renderFolderRow MUST pass a
    #    distinct select handler to the 6th argument — NOT
    #    onToggleExpand (directly OR via a thin wrapping
    #    lambda). Catches the historical bug where the 6th
    #    argument was wired to `onToggleExpand` (directly or
    #    as `(folderPath) => onToggleExpand(folderPath)`), so
    #    single-click on the folder row silently routed to
    #    expansion.
    #
    #    The negative lookbehind skips the `function
    #    renderFolderRow(` DECLARATION (its 5th argument is
    #    type-annotated `onToggleExpand: (path: string) =>
    #    void`, not the bare `onToggleExpand` identifier the
    #    call sites pass). The declaration's contract is
    #    pinned separately by the rest of the suite (the
    #    signature must take exactly 7 arguments in order).
    calls = list(re.finditer(
        r"(?<!function )renderFolderRow\s*\(",
        text,
    ))
    assert calls, (
        "renderFolderRow must be called at least once "
        "(the recursive folder-row render is the W6.1 "
        "mount's tree contract)."
    )
    for call_idx, m in enumerate(calls):
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            i += 1
        body = text[start:i - 1]
        args = _split_top_level_args(body)
        assert len(args) >= 7, (
            f"renderFolderRow call #{call_idx + 1} must take "
            f"7 arguments; got {len(args)}: {args!r}. The "
            f"recursive folder-row render signature is "
            f"fixed at 7 positional arguments by the W6.1 "
            f"folder-row contract."
        )
        arg5 = args[4].strip()
        arg6 = args[5].strip()
        assert arg5 == "onToggleExpand", (
            f"renderFolderRow call #{call_idx + 1}: 5th arg "
            f"must be the expand handler `onToggleExpand`; "
            f"got {arg5!r}. The 5th argument is the expansion "
            f"slot; chevron + ArrowRight/ArrowLeft wire "
            f"through it."
        )
        assert "onToggleExpand" not in arg6, (
            f"renderFolderRow call #{call_idx + 1}: 6th arg "
            f"must be a select handler (NOT onToggleExpand). "
            f"Got {arg6!r}. The historical bug wired the "
            f"6th arg to onToggleExpand (directly or via a "
            f"wrapping lambda), so single-click on the folder "
            f"row silently routed to expansion. The fix "
            f"wires the 6th arg to a distinct select "
            f"handler so single-click selects/highlights "
            f"without expanding."
        )

    # 6. The default FileTree component MUST track internal
    #    folder-selection state via `useState`. The W6.1
    #    `FileTreeProps` surface stays unchanged (no new
    #    `onSelectFolder` prop), so folder highlight lives
    #    in local state inside the component. This is the
    #    pin that catches a future PR that removes the
    #    internal-state mechanism and reverts to letting
    #    Explorer's `selectedPath` drive folder highlight
    #    (which would force the Explorer to expose folder
    #    selection state and break the FileTreeProps
    #    isolation contract).
    assert "useState" in text, (
        "FileTree must use useState to track internal "
        "folder-selection highlight state. The W6.1 "
        "FileTreeProps surface stays unchanged; folder "
        "selection lives locally inside the component so "
        "single-click can select without expanding and "
        "without expanding the prop API."
    )


# ---------------------------------------------------------------------------
# W6.2 Escape-clears-tree synchronously — Explorer.tsx must
# flush the debounced query in the same Escape handler so the
# FileTree `useEffect` fires `restoreTreeMutation` immediately,
# not 200 ms later. Mirrors the legacy
# `web/file_explorer.js::wireSearch()` Escape branch that
# calls `runSearch("")` synchronously in the same handler.
# ---------------------------------------------------------------------------
def test_w6_2_explorer_escape_clears_debounce_synchronously() -> None:
    """W6.2 Escape contract: pressing Escape synchronously
    restores the tree, NOT 200 ms after the debounce
    flushes. The legacy `web/file_explorer.js::wireSearch()`
    Escape branch reads:

        if (e.key === "Escape" && input.value) {
          e.preventDefault();
          input.value = "";
          runSearch("");  // synchronous, NOT through setTimeout
        }

    so a tap of Escape restores the tree in the same handler
    regardless of where the 200 ms input-debounce timer is.
    The React equivalent MUST clear BOTH `searchQuery` (the
    live input value) AND `debouncedQuery` (the value the
    `searchAnnotation` `useMemo` depends on) inside the same
    Escape branch so the FileTree `useEffect` flips
    `searchAnnotation === null` and calls
    `restoreTreeMutation()` on the next render — without
    waiting for the debounce `useEffect`'s 200 ms timer to
    fire.

    The harness verifies the AST shape: the Escape branch
    in `handleSearchKeyDown` MUST call `setDebouncedQuery`
    with an empty string alongside the existing
    `setSearchQuery("")` call. Typed input keeps the full
    200 ms debounce path (the existing `useEffect` keyed
    on `[searchQuery]` is unchanged); only Escape bypasses
    it. Comments are stripped before scanning so the
    docblock can quote the legacy `runSearch("")` shape
    without tripping the assertion.
    """
    if not EXPLORER_FILE.is_file():
        pytest.skip("Explorer.tsx not present yet")
    text = _strip_ts_comments(EXPLORER_FILE.read_text())
    # Match the Escape branch: from the `ev.key === "Escape"`
    # guard through the closing `}` of the `if`. The window
    # is greedy so the captured body spans every line of the
    # `if` block (the assertion below slices [:600] to bound
    # it for the per-line checks).
    escape_block = re.search(
        r"ev\.key\s*===\s*[\"']Escape[\"'][\s\S]*?\n\s*\}",
        text,
    )
    assert escape_block, (
        "Explorer.tsx must keep a synchronous Escape branch "
        "inside `handleSearchKeyDown` that clears the input "
        "value (`setSearchQuery(\"\")`). The legacy "
        "`web/file_explorer.js::wireSearch()` Escape branch "
        "is the reference shape."
    )
    block = escape_block.group(0)
    # End the captured block at the next `}` that closes
    # the `if`. The legacy's branch is a 4-line conditional;
    # the React equivalent adds one extra line
    # (`setDebouncedQuery("")`). A 600-char window is wide
    # enough to span the addition while still being narrow
    # enough to NOT cross into the next callback.
    window = block[:600]
    assert "setDebouncedQuery" in window, (
        "Explorer.tsx Escape branch must call "
        "`setDebouncedQuery(\"\")` synchronously alongside "
        "`setSearchQuery(\"\")` so the `searchAnnotation` "
        "`useMemo` flips to `null` on the next render and "
        "the FileTree `useEffect` calls `restoreTreeMutation` "
        "without waiting for the 200 ms debounce timer. The "
        "legacy `runSearch(\"\")` is called synchronously "
        "in the same handler — the React equivalent must "
        "not wait for the input-debounce `setTimeout`."
    )
    # The Escape handler MUST still call setSearchQuery("")
    # (the input-clear contract is preserved verbatim).
    assert "setSearchQuery(\"\")" in window, (
        "Explorer.tsx Escape branch must call "
        "`setSearchQuery(\"\")` so the input value clears "
        "on the next render (mirrors the legacy "
        "`input.value = \"\"` shape)."
    )
    # The Escape handler MUST still call preventDefault so
    # any ancestor Escape handler (browser back, etc.) does
    # not also fire (mirrors the legacy `e.preventDefault()`).
    assert "preventDefault" in window, (
        "Explorer.tsx Escape branch must call "
        "`ev.preventDefault()` so an ancestor Escape handler "
        "does not also fire (mirrors the legacy "
        "`e.preventDefault()` shape)."
    )
    # The Escape handler MUST guard on a non-empty query
    # (the legacy `&& input.value` branch — pressing Escape
    # with an empty input is a no-op).
    assert "searchQuery !== \"\"" in window, (
        "Explorer.tsx Escape branch must guard on "
        "`searchQuery !== \"\"` so pressing Escape with an "
        "empty input is a no-op (mirrors the legacy "
        "`&& input.value` shape)."
    )


def test_w6_2_explorer_has_no_dead_empty_annotation_handle() -> None:
    """W6.2 contract — Explorer.tsx MUST NOT carry the dead
    `emptyAnnotation` useMemo + `void emptyAnnotation` block
    that was leftover from an earlier draft. The factory
    `createEmptySearchAnnotation` returns a fresh
    `{matches, ancestors}` annotation, but the React mount
    never threads it anywhere (FileTree compares
    `searchAnnotation === null` for the "no active query"
    case, not an empty annotation handle). The dead block
    adds noise + a `noUnusedLocals` hazard. The kernel's
    `createEmptySearchAnnotation` is still exported through
    `@taxa/research` (the barrel re-export test pins this)
    so a future consumer can reach it through the public
    surface.

    The harness verifies three negative shapes:

      1. No `emptyAnnotation` identifier in the file body
         (the dead local).
      2. No `void emptyAnnotation` expression (the explicit
         "I know I'm unused" suppression).
      3. The `createEmptySearchAnnotation` import is NOT
         pulled into Explorer.tsx (the helper is unused at
         the mount level — a future consumer reaches it
         through the barrel, not via a deep import into
         Explorer.tsx).

    Comments are stripped before scanning so the docblock
    can reference the dead name without tripping the guard.
    """
    if not EXPLORER_FILE.is_file():
        pytest.skip("Explorer.tsx not present yet")
    text = _strip_ts_comments(EXPLORER_FILE.read_text())
    assert "emptyAnnotation" not in text, (
        "Explorer.tsx must NOT carry a local `emptyAnnotation` "
        "useMemo + `void emptyAnnotation` block — the factory "
        "is unused at the mount level (FileTree compares "
        "`searchAnnotation === null`, not an empty annotation "
        "handle). The dead block is leftover from an earlier "
        "draft and adds `noUnusedLocals` hazard."
    )
    # The Explorer.tsx import surface must NOT pull
    # `createEmptySearchAnnotation` from `@taxa/research` —
    # the helper is reachable through the barrel for future
    # consumers but the mount itself never calls it. A
    # reverse import here would be a regression.
    assert "createEmptySearchAnnotation" not in text, (
        "Explorer.tsx must NOT import `createEmptySearchAnnotation` "
        "from `@taxa/research` — the helper is unused at the "
        "mount level and the dead local was removed. The "
        "helper stays reachable through the barrel for future "
        "consumers."
    )


# ---------------------------------------------------------------------------
# Framework-free kernel — explorer-state.ts has no React / Next
# / FastAPI / DOM / localStorage / process tokens.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("token", _KERNEL_FORBIDDEN)
def test_explorer_state_kernel_is_framework_free(
    token: str, require_toolchain: None,
) -> None:
    """`explorer-state.ts` stays free of framework / I/O /
    browser-state tokens. The kernel is the typed hand-off
    surface between the React mount and the rest of the
    capability module; it must compile under `--lib ES2022`
    only (no DOM, no React types). Comments are stripped
    so JSDoc can reference forbidden-token words."""
    if not EXPLORER_STATE_FILE.is_file():
        pytest.skip("explorer-state.ts not present yet")
    text = _strip_ts_comments(EXPLORER_STATE_FILE.read_text())
    assert token not in text, (
        f"explorer-state.ts must stay free of {token!r}; the "
        f"W6.1 kernel is framework-free + I/O-free + "
        f"browser-free. spec.md rule 4 keeps presentation "
        f"inward-only (domain)."
    )


def test_explorer_state_kernel_imports_only_from_domain_and_application(
    require_toolchain: None,
) -> None:
    """Spec.md rule 4: presentation depends on domain (and
    the application layer for typed type-only imports). The
    kernel's only imports are from `../domain/explorer`
    (the W1 domain) + `../application/renderers` (the W4a–
    W4b4 typed dispatch surface) — no reverse deep imports
    from `../infrastructure`, `../presentation`, or
    `../index` (the public barrel)."""
    if not EXPLORER_STATE_FILE.is_file():
        pytest.skip("explorer-state.ts not present yet")
    text = EXPLORER_STATE_FILE.read_text()
    for src in re.findall(r'from\s+["\']([^"\']+)["\']', text):
        # Allow type-only imports into the W4a–W4b4
        # application layer (the kernel needs the typed
        # `ViewerDispatch` discriminated union). Domain
        # imports are the primary surface.
        if not src.startswith(("../domain/", "../application/")):
            raise AssertionError(
                f"explorer-state.ts imports from {src!r}; must be "
                f"`../domain/*` or `../application/*` only (spec.md "
                f"rule 4)."
            )


def test_explorer_state_kernel_uses_named_exports(
    require_toolchain: None,
) -> None:
    """The kernel commits to named exports only — every
    public surface (createInitialLoadStatus,
    createInitialViewerState, bytesRequiredForFormat,
    castFileFormat, buildServeUrl, enumerateFiles,
    toggleExpansion, withExpanded, annotateMatches,
    createEmptySearchAnnotation) is exported as a named
    symbol. The barrel re-export test (below) depends on
    these names being stable. W6.2 extends the W6.1 set
    with the pure search helpers."""
    if not EXPLORER_STATE_FILE.is_file():
        pytest.skip("explorer-state.ts not present yet")
    text = EXPLORER_STATE_FILE.read_text()
    for name in (
        "createInitialLoadStatus",
        "createInitialViewerState",
        "bytesRequiredForFormat",
        "castFileFormat",
        "buildServeUrl",
        "enumerateFiles",
        "toggleExpansion",
        "withExpanded",
        "annotateMatches",
        "createEmptySearchAnnotation",
    ):
        pattern = rf"export\s+(?:async\s+)?function\s+{name}\b"
        assert re.search(pattern, text), (
            f"explorer-state.ts must export `{name}` as a named "
            f"function (the W6.1 / W6.2 typed hand-off surface)."
        )


def test_explorer_state_kernel_uses_named_type_exports(
    require_toolchain: None,
) -> None:
    """The kernel commits to named type exports too —
    `ExplorerLoadStatus` + `ViewerState` +
    `SearchAnnotation` are the typed view-models the
    React mount reads. All three must be declared with
    `export type` OR `export interface` so the focused
    compile (CJS module output) strips them at build
    time. (The W6.1 kernel uses `export type` for the
    discriminated union + `export interface` for the
    typed view-model — both shapes qualify. W6.2
    adds `SearchAnnotation` as `export interface`.)"""
    if not EXPLORER_STATE_FILE.is_file():
        pytest.skip("explorer-state.ts not present yet")
    text = EXPLORER_STATE_FILE.read_text()
    for type_name in ("ExplorerLoadStatus", "ViewerState", "SearchAnnotation"):
        assert re.search(
            rf"export\s+(?:type|interface)\s+{type_name}\b", text,
        ), (
            f"explorer-state.ts must export `{type_name}` as a "
            f"named `export type` or `export interface` (the W6.1 "
            f"/ W6.2 typed view-model)."
        )


# ---------------------------------------------------------------------------
# Barrel re-export contract — every W6.1 public symbol is
# reachable through `@taxa/research`.
# ---------------------------------------------------------------------------
def test_barrel_reexports_w6_1_components() -> None:
    """The public barrel MUST re-export the four React
    components as default exports so cross-module consumers
    (the `src/app/explorer/page.tsx` route) can mount the
    Explorer through `@taxa/research`. A future PR that
    flips to a named export would break the route's
    `import { Explorer } from "@taxa/research"` pattern."""
    if not BARREL_FILE.is_file():
        pytest.skip("barrel not present yet")
    text = BARREL_FILE.read_text()
    for component in (
        "Explorer",
        "Viewer",
        "FileTree",
        "ExplorerErrorBoundary",
    ):
        assert re.search(
            rf'export\s+\{{[^}}]*default\s+as\s+{component}\b',
            text,
        ), (
            f"barrel must re-export `{component}` as a default "
            f"export so cross-module consumers can mount it "
            f"through `import {{ {component} }} from "
            f"\"@taxa/research\"`."
        )


def test_barrel_reexports_w6_1_kernel_helpers() -> None:
    """The public barrel MUST re-export every pure kernel
    helper so the React mount reaches the typed surface
    through `@taxa/research` only. spec.md rule 5 forbids
    reverse deep imports into the presentation layer.
    W6.2 extends the W6.1 set with the pure search
    helpers `annotateMatches` + `createEmptySearchAnnotation`."""
    if not BARREL_FILE.is_file():
        pytest.skip("barrel not present yet")
    text = BARREL_FILE.read_text()
    for helper in (
        "createInitialLoadStatus",
        "createInitialViewerState",
        "bytesRequiredForFormat",
        "castFileFormat",
        "buildServeUrl",
        "enumerateFiles",
        "annotateMatches",
        "createEmptySearchAnnotation",
        "toggleExpansion",
        "withExpanded",
    ):
        assert helper in text, (
            f"barrel must re-export the kernel helper `{helper}`."
        )


def test_barrel_reexports_w6_1_kernel_types() -> None:
    """The public barrel MUST re-export the kernel's typed
    view-models (`ExplorerLoadStatus`, `ViewerState`,
    `SearchAnnotation`). The React mount reads these
    through `@taxa/research`. W6.2 extends the W6.1
    surface with `SearchAnnotation` so the FileTree's
    `useEffect` can reach the typed `{matches,
    ancestors}` shape without a reverse deep import."""
    if not BARREL_FILE.is_file():
        pytest.skip("barrel not present yet")
    text = BARREL_FILE.read_text()
    for type_name in ("ExplorerLoadStatus", "ViewerState", "SearchAnnotation"):
        assert re.search(
            rf"export\s+type\s+[^}}]*\b{type_name}\b", text,
        ), (
            f"barrel must re-export the typed `{type_name}` "
            f"view-model."
        )


def test_barrel_reexports_w1_domain_types() -> None:
    """The public barrel MUST re-export the W1 domain types
    so the React mount reaches the typed shape through
    `@taxa/research` only. The barrel is the single typed
    hand-off surface between the presentation layer and
    the rest of the capability module — a future PR that
    drops a domain type from the barrel forces the React
    layer to import from `../domain/explorer` (which is
    blocked by ESLint `no-restricted-imports`)."""
    if not BARREL_FILE.is_file():
        pytest.skip("barrel not present yet")
    text = BARREL_FILE.read_text()
    for type_name in (
        "ExplorerTree",
        "ExplorerTreeNode",
        "ExplorerFolderNode",
        "ExplorerFileNode",
        "ViewerTab",
        "FileFormat",
    ):
        assert type_name in text, (
            f"barrel must re-export the W1 domain type "
            f"`{type_name}`."
        )


# ---------------------------------------------------------------------------
# Compile + runtime contract — strict isolated TypeScript
# compile of the state kernel + W1 domain + W4 renderers +
# a runtime harness that exercises every pure state helper.
# ---------------------------------------------------------------------------
def _run_tsc_isolated(
    out_dir: Path,
    sources: list[Path],
    extra: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Compile the W6.1 sources (W1 domain + W4a–W4b4
    renderers + W6.1 presentation state kernel) in
    isolation. Flags mirror the W4a / W4b1–W4b4 / W1
    contract: `--strict`, `--target ES2022`, `--module
    commonjs` (so Node can `require` the output),
    `--lib ES2022` (no DOM — the kernel stays framework-
    free)."""
    return subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--strict",
            "--target", "ES2022",
            "--module", "commonjs",
            "--lib", "ES2022",
            "--skipLibCheck",
            "--esModuleInterop",
            "--rootDir", "src/modules/research",
            "--outDir", str(out_dir),
            *[str(p) for p in sources],
            *(extra or []),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture()
def compiled_w6_1_kernel(
    tmp_path: Path, require_toolchain: None,
) -> tuple[Path, Path]:
    """Compile the W6.1 state kernel alongside the W1
    domain + the W4a–W4b4 renderers. The kernel imports
    `import("../application/renderers").ViewerDispatch`
    (a type-only inline import), so the W4 layer must
    be in the compile graph for the inline type to
    resolve. Returns (compiled-kernel path, compiled-
    renderers path) — the runtime harness loads both."""
    for p in (
        DOMAIN_FILE, RENDERERS_FILE, EXPLORER_STATE_FILE,
    ):
        if not p.is_file():
            pytest.skip(f"missing required source: {p}")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    result = _run_tsc_isolated(
        out_dir,
        [DOMAIN_FILE, RENDERERS_FILE, EXPLORER_STATE_FILE],
    )
    assert result.returncode == 0, (
        f"explorer-state.ts failed to compile in isolated "
        f"strict mode.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    compiled_kernel = (
        out_dir / "presentation" / "explorer-state.js"
    )
    compiled_renderers = (
        out_dir / "application" / "renderers.js"
    )
    compiled_domain = out_dir / "domain" / "explorer.js"
    for path, label in (
        (compiled_kernel, "presentation/explorer-state.js"),
        (compiled_renderers, "application/renderers.js"),
        (compiled_domain, "domain/explorer.js"),
    ):
        assert path.is_file(), (
            f"tsc did not emit `{label}` at {path}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return compiled_kernel, compiled_renderers


# Runtime harness — exercises the pure state helpers under
# Node (ES2022 only, no DOM). The harness is hermetic (no
# React, no DOM, no fetch) and runs every W6.1 helper end-
# to-end: toggleExpansion round-trips a fresh Set,
# bytesRequiredForFormat matches the W6.1 contract, cast
# of unknown extensions falls back to "other", buildServeUrl
# URL-encodes verbatim, enumerateFiles yields every file in
# depth-first order.
_RUNTIME_HARNESS = r"""
// CJS does not support top-level await (only ESM does), so
// the harness wraps the assertions in a sync body — every
// W6.1 kernel helper is pure (no async, no I/O).
const path = require("path");
const assert = require("assert");
const kernel = require(path.resolve(process.argv[2]));

// 1. toggleExpansion — pure Set transition. Adding then
//    removing the same folder round-trips to the original
//    empty set; the result is a NEW Set (not a shared
//    reference). The mount's `useState` updater relies on
//    the new-set shape so React's reconciliation stays
//    deterministic.
{
  const empty = new Set();
  const a = kernel.toggleExpansion(empty, "Animalia");
  assert.strictEqual(a.size, 1, "toggleExpansion must add the folder");
  assert.ok(a.has("Animalia"), "added folder must be present");
  const b = kernel.toggleExpansion(a, "Animalia");
  assert.strictEqual(b.size, 0, "toggleExpansion must remove an existing folder");
  assert.notStrictEqual(a, b, "toggleExpansion must return a new Set");
}

// 2. withExpanded — pure multi-folder add. The result
//    starts from the input set + adds every folder in
//    order. The mount's auto-expand-on-first-render effect
//    uses this helper.
{
  const initial = new Set(["Animalia"]);
  const next = kernel.withExpanded(
    initial, ["Plantae", "Fungi", "Chromista"],
  );
  assert.strictEqual(next.size, 4, "withExpanded must add every folder");
  for (const p of ["Animalia", "Plantae", "Fungi", "Chromista"]) {
    assert.ok(next.has(p), `withExpanded must include ${p}`);
  }
}

// 3. bytesRequiredForFormat — W6.1 contract: bytes are
//    required ONLY for TXT / MD / SVG (the formats that
//    feed the W4a `text-pre` + `svg-sanitized` variants).
//    Every other W4a family passes the URL straight
//    through to the renderer without reading bytes. EPUB
//    falls into the "no bytes" branch because the W6.1
//    mount does not wire the CDN library — bytes, if
//    fetched, would just trigger the offline branch.
{
  assert.strictEqual(kernel.bytesRequiredForFormat("txt"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("md"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("svg"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("pdf"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("html"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("htm"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("jpg"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("epub"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("docx"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("xlsx"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("csv"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("json"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("mp4"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("other"), false);
}

// 4. castFileFormat — typed cast with "other" fallback.
//    The cast is exhaustive against the W1 `FileFormat`
//    union; unknown extensions fall through to `"other"`.
{
  assert.strictEqual(kernel.castFileFormat("pdf"), "pdf");
  assert.strictEqual(kernel.castFileFormat("MD"), "md", "must lowercase the extension");
  assert.strictEqual(kernel.castFileFormat("zip"), "other", "unknown extension must fall through to other");
  assert.strictEqual(kernel.castFileFormat(null), "other", "null must fall through to other");
  assert.strictEqual(kernel.castFileFormat(""), "other", "empty string must fall through to other");
  assert.strictEqual(kernel.castFileFormat("JPG"), "jpg", "must lowercase the extension");
}

// 5. buildServeUrl — pure URL builder. Mirrors the legacy
//    `web/file_explorer.js::serveUrl(relativePath)` shape
//    byte-for-byte (URL-encode verbatim; trim trailing
//    slash on baseUrl). The mount hands the URL to
//    `<iframe>` / `<img>` / `<video>` + the W3 adapter.
{
  const a = kernel.buildServeUrl("/api", "Animalia/Mammalia.pdf");
  assert.strictEqual(
    a,
    "/api/api/files/serve?path=Animalia%2FMammalia.pdf",
    "buildServeUrl must join baseUrl + /api/files/serve + encoded path",
  );
  // The trailing slash on baseUrl is trimmed (idempotent
  // join).
  const b = kernel.buildServeUrl("/api/", "Foo bar.pdf");
  assert.strictEqual(
    b,
    "/api/api/files/serve?path=Foo%20bar.pdf",
    "buildServeUrl must trim trailing slash on baseUrl",
  );
  // Spaces round-trip cleanly (URL-encodes verbatim).
  const c = kernel.buildServeUrl("", "with spaces/and accénts.pdf");
  assert.ok(
    c.includes("with%20spaces"),
    "buildServeUrl must URL-encode spaces verbatim",
  );
}

// 6. enumerateFiles — recursive depth-first walker. Every
//    file under the tree yields one entry; folder nodes
//    contribute no entry of their own.
{
  const tree = {
    type: "folder",
    name: "root",
    path: "",
    children: [
      {
        type: "folder",
        name: "Animalia",
        path: "Animalia",
        children: [
          { type: "file", name: "Mammalia.pdf", path: "Animalia/Mammalia.pdf",
            extension: "pdf", size: 100, modified: "2024-01-01T00:00:00" },
          { type: "file", name: "Aves.txt", path: "Animalia/Aves.txt",
            extension: "txt", size: 200, modified: "2024-01-01T00:00:00" },
        ],
      },
      {
        type: "folder",
        name: "Plantae",
        path: "Plantae",
        children: [
          { type: "file", name: "Rosa.md", path: "Plantae/Rosa.md",
            extension: "md", size: 300, modified: "2024-01-01T00:00:00" },
        ],
      },
    ],
  };
  const files = kernel.enumerateFiles(tree);
  assert.strictEqual(files.length, 3, "enumerateFiles must yield every file");
  const paths = files.map((f) => f.path);
  assert.deepStrictEqual(
    paths,
    [
      "Animalia/Mammalia.pdf",
      "Animalia/Aves.txt",
      "Plantae/Rosa.md",
    ],
    "enumerateFiles must walk depth-first pre-order",
  );
  // Each entry carries the full file node (the mount
  // uses `node` for the format cast + the bytes fetch).
  assert.strictEqual(files[0].node.extension, "pdf");
  assert.strictEqual(files[1].node.size, 200);
}

// 7. W6.2 — createEmptySearchAnnotation — returns a
//    fresh annotation with empty Sets on every call so a
//    consumer can mutate locally without bleeding into a
//    sibling. The factory must return TWO distinct Set
//    instances per call (matches + ancestors are not
//    shared references).
{
  const a = kernel.createEmptySearchAnnotation();
  const b = kernel.createEmptySearchAnnotation();
  assert.strictEqual(a.matches.size, 0, "matches must start empty");
  assert.strictEqual(a.ancestors.size, 0, "ancestors must start empty");
  assert.notStrictEqual(a.matches, b.matches, "matches is a fresh Set");
  assert.notStrictEqual(a.ancestors, b.ancestors, "ancestors is a fresh Set");
}

// 8. W6.2 — annotateMatches — null/empty/whitespace
//    query paths yield the empty annotation (the React
//    layer short-circuits on this shape without burning
//    the recursive walker).
{
  const tree = {
    type: "folder",
    name: "root",
    path: "",
    children: [
      { type: "file", name: "Mammalia.pdf", path: "Mammalia.pdf",
        extension: "pdf", size: 100, modified: "2024-01-01T00:00:00" },
    ],
  };
  const empty1 = kernel.annotateMatches(tree, "");
  assert.strictEqual(empty1.matches.size, 0);
  assert.strictEqual(empty1.ancestors.size, 0);
  const empty2 = kernel.annotateMatches(tree, "   ");
  assert.strictEqual(empty2.matches.size, 0);
  assert.strictEqual(empty2.ancestors.size, 0);
  const empty3 = kernel.annotateMatches(null, "Mammalia");
  assert.strictEqual(empty3.matches.size, 0);
  assert.strictEqual(empty3.ancestors.size, 0);
}

// 9. W6.2 — annotateMatches — case-insensitive substring
//    match against `name` + `path`. A folder whose own
//    name matches ends up in `matches` AND its descendants
//    stay OUT of `matches` (they land in `ancestors` only
//    when a descendant itself matches). Mirrors the
//    legacy `web/file_explorer.js::_annotateMatches` shape
//    byte-for-byte.
{
  const tree = {
    type: "folder",
    name: "root",
    path: "",
    children: [
      {
        type: "folder",
        name: "Animalia",
        path: "Animalia",
        children: [
          { type: "file", name: "Mammalia.pdf", path: "Animalia/Mammalia.pdf",
            extension: "pdf", size: 100, modified: "2024-01-01T00:00:00" },
          { type: "file", name: "Aves.txt", path: "Animalia/Aves.txt",
            extension: "txt", size: 200, modified: "2024-01-01T00:00:00" },
        ],
      },
      {
        type: "folder",
        name: "Plantae",
        path: "Plantae",
        children: [
          { type: "file", name: "Rosa.md", path: "Plantae/Rosa.md",
            extension: "md", size: 300, modified: "2024-01-01T00:00:00" },
        ],
      },
    ],
  };
  // 9a — query "mammalia" matches by name (case-insensitive)
  const a = kernel.annotateMatches(tree, "mammalia");
  assert.strictEqual(a.matches.size, 1, "mammalia must match Mammalia.pdf by name");
  assert.ok(a.matches.has("Animalia/Mammalia.pdf"));
  assert.strictEqual(a.ancestors.size, 1, "Animalia folder must be an ancestor");
  assert.ok(a.ancestors.has("Animalia"));

  // 9b — query "rosa" matches by name (case-insensitive).
  //      Rosa.md's name contains the needle directly; the
  //      Plantae folder is the ancestor (post-order promotion)
  //      because Rosa.md is a descendant hit. Confirms the
  //      post-order ancestor promotion contract: a folder
  //      with at least one matching descendant ends up in
  //      `ancestors` even when its own name does NOT
  //      contain the needle.
  const b = kernel.annotateMatches(tree, "rosa");
  assert.ok(b.matches.has("Plantae/Rosa.md"));
  assert.ok(b.ancestors.has("Plantae"));
  assert.strictEqual(b.ancestors.size, 1);

  // 9c — multi-match query "Animalia" hits the Animalia
  //      folder by name + the nested Mammalia.pdf +
  //      Aves.txt by path substring (descendant paths
  //      inherit the parent's path). Plantae + Rosa.md
  //      have no overlap.
  const c = kernel.annotateMatches(tree, "Animalia");
  assert.ok(c.matches.has("Animalia"), "Animalia folder matches by name");
  assert.ok(c.matches.has("Animalia/Mammalia.pdf"), "descendants match by path");
  assert.ok(c.matches.has("Animalia/Aves.txt"));
  assert.strictEqual(c.matches.size, 3);

  // 9d — synthetic-root path stays out of `ancestors`.
  //      The test root has path "" (the React mount wraps
  //      the wire tree root in a synthetic folder node),
  //      so even when a descendant matches, the root
  //      itself never appears in `ancestors`.
  assert.strictEqual(c.ancestors.size, 0, "synthetic root path is not in ancestors");
}

// 10. W6.2 — annotateMatches — query with spaces /
//     accents round-trips through the path substring
//     match (the legacy `web/file_explorer.js` checks
//     `path.toLowerCase().includes(needle)` so URL-encoded
//     paths + accented names are matched byte-for-byte
//     at the substring level — no URL-decoding).
{
  const tree = {
    type: "folder",
    name: "root",
    path: "",
    children: [
      {
        type: "folder",
        name: "Fungi with accents",
        path: "Fungi with accents",
        children: [
          { type: "file", name: "Mushroom.txt",
            path: "Fungi with accents/Mushroom.txt",
            extension: "txt", size: 1, modified: "2024-01-01T00:00:00" },
        ],
      },
    ],
  };
  const accented = kernel.annotateMatches(tree, "Fungi with accents");
  assert.ok(accented.matches.has("Fungi with accents"));
  assert.ok(accented.ancestors.size === 0);
}

process.stdout.write("PASS\n");
"""


def test_compiled_w6_1_kernel_passes_runtime_contract(
    compiled_w6_1_kernel: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """Under Node (ES2022 only, no DOM, no React), the
    compiled W6.1 state kernel + the W1 domain + the
    W4a–W4b4 renderers together satisfy the W6.1 pure
    contract end-to-end:

      1. `toggleExpansion` round-trips a fresh Set (the
         React mount's `useState` updater relies on the
         new-set shape).
      2. `withExpanded` adds every folder in order.
      3. `bytesRequiredForFormat` matches the W6.1
         contract (true for TXT / MD / SVG only; false for
         every other W4a family + EPUB / DOCX / XLSX /
         CSV / JSON + `other`).
      4. `castFileFormat` falls back to `"other"` for
         unknown / null / empty extensions; lowercases
         case-mismatched extensions.
      5. `buildServeUrl` URL-encodes verbatim (mirrors
         the legacy `serveUrl`); trims trailing slash on
         `baseUrl`.
      6. `enumerateFiles` yields every file in depth-first
         pre-order; folder nodes contribute no entry.

    The runtime harness exercises every helper under
    Node's ES2022-only environment (no DOM, no React
    types) so a future PR that pulls in a framework
    dependency trips the focused compile gate before the
    runtime assertion fires."""
    _compiled_kernel, _compiled_renderers = compiled_w6_1_kernel
    harness = tmp_path / "harness.cjs"
    harness.write_text(_RUNTIME_HARNESS)
    result = subprocess.run(
        ["node", str(harness), str(_compiled_kernel)],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"runtime harness failed.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected harness output: {result.stdout!r}"
    )


# ---------------------------------------------------------------------------
# Project-wide strict typecheck — the W6.1 mount compiles
# against the project's tsconfig (not just the focused
# isolated strict flags). A future PR that breaks a
# downstream consumer (other presentation components,
# the page.tsx route, the cross-module barrel re-exports)
# is caught here.
# ---------------------------------------------------------------------------
def test_project_wide_strict_typecheck_for_w6_1_mount(
    require_toolchain: None,
) -> None:
    """Strict typecheck of `src/app/explorer/page.tsx` +
    `src/modules/research/` against the project's tsconfig
    flags (`strict`, `noUncheckedIndexedAccess`,
    `noUnusedLocals`, `noUnusedParameters`,
    `noImplicitReturns`, `noFallthroughCasesInSwitch`).
    The compile is `--noEmit` so no output touches the
    worktree; it only validates that the W6.1 mount
    compiles cleanly under the project's full strict mode
    flag set. The test skips when `node_modules` is
    missing — the `next` plugin the project tsconfig
    pulls in needs `@types/next` / `next` installed (see
    `package.json`)."""
    if not (
        APP_EXPLORER_PAGE.is_file()
        and EXPLORER_STATE_FILE.is_file()
        and EXPLORER_FILE.is_file()
    ):
        pytest.skip("W6.1 mount files not present yet")
    if not (REPO_ROOT / "node_modules").is_dir():
        pytest.skip(
            "node_modules not installed — strict typecheck "
            "requires next types"
        )
    # Compile `src/modules/research/**` + the new
    # `src/app/explorer/page.tsx` under the project's
    # full strict mode flag set. The compile uses
    # `--project tsconfig.json` so the path-alias map
    # (`@taxa/*`) is honored — a standalone tsc with
    # individual files does NOT resolve path aliases, so
    # `@taxa/research` would surface as "module not found"
    # and the downstream React components would compile
    # against `any` for the imported types. The
    # `tsconfig.json` `noEmit: true` setting prevents
    # accidental writes; the focused compile flag set
    # here mirrors the project's flag set verbatim.
    tsconfig = REPO_ROOT / "tsconfig.json"
    assert tsconfig.is_file(), (
        f"missing tsconfig.json at {tsconfig}. The strict "
        f"typecheck needs the project's tsconfig for path "
        f"alias resolution."
    )
    result = subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--noEmit",
            "--project", str(tsconfig),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"strict typecheck of W6.1 mount failed.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
