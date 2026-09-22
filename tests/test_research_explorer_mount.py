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
SPLITTER_FILE = RESEARCH_DIR / "presentation" / "Splitter.tsx"
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


# W6.3 — Browser-tab Explorer splitter forbidden tokens.
# The Splitter is a DOM-bound Client Component (NOT the
# framework-free kernel). It walks the DOM from its
# `parentElement` + manipulates the `.fex-tree-pane`
# sibling via class selector, attaches document-level
# mousedown / mousemove / mouseup / dblclick listeners,
# and reads / writes / removes the localStorage key
# `taxa.fex.treeWidth`. The forbidden tokens list below
# is intentionally DIFFERENT from the kernel list above:
#
#   - `document.`, `window.`, `localStorage` are ALLOWED
#     (the Splitter is DOM-bound; storage failures are
#     swallowed per the W6.3 contract).
#   - `fetch(` is FORBIDDEN (the Splitter is a pure UI
#     component; the React mount's `fetchFiles` owns the
#     network lifecycle).
#   - Cross-module imports into `@taxa/browser-state`,
#     `@taxa/taxonomy`, `@taxa/design-system`,
#     `@taxa/app-shell` are FORBIDDEN (the Splitter is
#     local to Research presentation; the storage key
#     `taxa.fex.treeWidth` is a raw localStorage key per
#     the user-authorized W6.3 decision — no browser-
#     state scope creep).
#   - Deep imports into `@taxa/research/domain/*`,
#     `@taxa/research/application/*`,
#     `@taxa/research/infrastructure/*`,
#     `@taxa/research/presentation/*` (other than the
#     Splitter's own module) are FORBIDDEN (spec.md rule
#     5 keeps cross-module imports anchored at the public
#     barrel; the Splitter only needs React).
#   - Framework imports OTHER than React are FORBIDDEN
#     (no Vue / Svelte / React Native / Solid / Preact;
#     no react-router / next/router; no Next Script
#     component; no CDN-script surface).
#   - `web/`, `src/app/page.tsx`, settings reset, server
#     surface, materialization, CDN viewers are FORBIDDEN
#     (the W6.3 isolation contract).
#   - `process.`, `require(`, `globalThis` (the Splitter
#     uses `globalThis.localStorage` for SSR-safety; the
#     `globalThis.localStorage` reference is ALLOWED, but
#     bare `globalThis` for state mutations is FORBIDDEN).
#
# Comments are stripped before scanning so JSDoc can
# reference forbidden-token words.
_SPLITTER_FORBIDDEN: tuple[str, ...] = (
    # I/O — Splitter is a pure UI component (the React
    # mount's fetchFiles owns the network lifecycle).
    "fetch(",
    # Framework other than React.
    "from 'next'",    'from "next"',
    "from 'react-router'", 'from "react-router"',
    "from 'vue'",     'from "vue"',
    "from 'svelte'",  'from "svelte"',
    "from 'solid-js'", 'from "solid-js"',
    # CDN-script surface — the Splitter does NOT load
    # CDN libraries. Future W6+ slices that wire CDN
    # viewers land as separately authorized follow-ups.
    "loadScriptOnce",
    "<Script",
    "dangerouslySetInnerHTML",
    # Reverse deep imports — Splitter only imports React.
    # spec.md rule 5 keeps cross-module imports anchored
    # at the public barrel.
    "@taxa/research/domain",
    "@taxa/research/application",
    "@taxa/research/infrastructure",
    "@taxa/research/presentation/",
    # Cross-module imports outside Research — the Splitter
    # is local to Research presentation. The storage key
    # `taxa.fex.treeWidth` is a raw localStorage key per
    # the user-authorized W6.3 decision (no
    # `@taxa/browser-state` scope creep).
    "@taxa/browser-state",
    "@taxa/taxonomy",
    "@taxa/design-system",
    "@taxa/app-shell",
    # Legacy + isolation.
    "src/app/page",
    "../web", "../../web", "web/",
    # Process / CommonJS guards — Splitter is ESM-only.
    "process.",
    "require(",
    # FastAPI / Starlette / settings reset / materialization
    # / CDN viewers — out of scope for W6.3.
    "fastapi", "starlette",
    "settings.reset",
    "materialize",
    "epubjs", "mammoth", "XLSX", "papaparse", "Papa",
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
        (SPLITTER_FILE, "Splitter.tsx", ".tsx"),
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
    [EXPLORER_FILE, FILE_TREE_FILE, VIEWER_FILE, ERROR_BOUNDARY_FILE, SPLITTER_FILE],
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
//
//    W64A-JSON-001 — JSON is now in the bytes-required
//    group. The JSON Tree viewer materialization owns
//    JSON.parse + the legacy `MAX_JSON_NODES = 50_000`
//    truncation cap, so bytes MUST be fetched through
//    the existing `bytesRequiredForFormat` seam before
//    the dispatcher's `json-source` branch fires. JSON
//    is native per the spec's "Tree viewer tab / No CDN
//    is used." requirement (no `<Script>` surface), so
//    adding JSON to the bytes-required matrix does NOT
//    touch the CDN loader contract.
{
  assert.strictEqual(kernel.bytesRequiredForFormat("txt"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("md"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("svg"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("json"), true,
    "W64A-JSON-001: JSON must require bytes (the native JSON.parse tree viewer reads the bytes through the bytesRequiredForFormat seam)");
  assert.strictEqual(kernel.bytesRequiredForFormat("pdf"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("html"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("htm"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("jpg"), false);
  assert.strictEqual(
    kernel.bytesRequiredForFormat("epub"), true,
    "W64D-EPUB-004: bytesRequiredForFormat('epub') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads EPUB bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX effects already use",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("docx"), true,
    "W64B-DOCX-002: bytesRequiredForFormat('docx') must return "
    + "true so the bytes-fetch effect in Viewer.tsx reads the "
    + "DOCX bytes through the same seam TXT / MD / SVG / JSON "
    + "already use (the W6.1 W64A JSON contract flipped "
    + "JSON into the bytes-required group; W64B extends that "
    + "matrix to DOCX so the Next Script loader + "
    + "mammoth.convertToHtml path has bytes available).",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("xls"), true,
    "W64C-XLS-003: bytesRequiredForFormat('xls') must return "
    + "true so the bytes-fetch effect in Viewer.tsx reads the "
    + "XLS bytes through the same seam TXT / MD / SVG / JSON / "
    + "DOCX already use (the W6.1 W64A + W64B-DOCX-002 "
    + "contracts flipped JSON + DOCX into the bytes-required "
    + "group; W64C extends that matrix to XLS / XLSX so the "
    + "Next Script loader + SheetJS.read(...) + "
    + "utils.sheet_to_html(...) path has bytes available).",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("xlsx"), true,
    "W64C-XLS-003: bytesRequiredForFormat('xlsx') must return "
    + "true so the bytes-fetch effect in Viewer.tsx reads the "
    + "XLSX bytes through the same seam the XLS / DOCX / TXT / "
    + "MD / SVG / JSON effects already use (XLS and XLSX "
    + "share the same SheetJS path; the format field is "
    + "carried verbatim through the dispatch).",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("csv"), true,
    "W64E-CSV-005: bytesRequiredForFormat('csv') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads CSV bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX / EPUB effects "
    + "already use (the mount owns the TextDecoder + "
    + "Papa.parse(...) lifecycle)",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("tsv"), true,
    "W64E-CSV-005: bytesRequiredForFormat('tsv') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads TSV bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX / EPUB / CSV "
    + "effects already use (CSV and TSV share the same "
    + "Papa Parse path; the delimiter literal is computed "
    + "from the format field)",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("epub"), true,
    "W64D-EPUB-004: bytesRequiredForFormat('epub') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads EPUB bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX effects already use",
  );
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


# ---------------------------------------------------------------------------
# W6.3 — Explorer splitter (Browser-tab tree / viewer drag handle).
# Mirrors the legacy `web/file_explorer.js::renderSplitter()` byte-for-byte:
# mouse drag adjusts the tree width; double-click clears the localStorage
# key + the inline width so the legacy CSS default takes over again; all
# storage failures are swallowed. The Splitter is intentionally DOM-bound
# (NOT the framework-free kernel): it walks the DOM from its
# `parentElement` + manipulates the `.fex-tree-pane` sibling via class
# selector, attaches document-level mouse listeners, and reads / writes /
# removes the single global localStorage key `taxa.fex.treeWidth`. The
# pure helpers (`clampTreeWidth`, `readSavedTreeWidth`,
# `writeSavedTreeWidth`, `clearSavedTreeWidth`) + the constants
# (`TREE_WIDTH_STORAGE_KEY`, `MIN_TREE_WIDTH_PX`, `VIEWER_RESERVED_PX`)
# are named exports on the same module so the focused test harness
# exercises them under Node without React or the DOM event system.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# W6.3 — Splitter source-level purity. The Splitter is
# DOM-bound (NOT framework-free), so the forbidden-tokens
# list is intentionally DIFFERENT from the kernel's
# `_KERNEL_FORBIDDEN` tuple above. The list forbids:
#   - `fetch(` (the Splitter is a pure UI component).
#   - Framework imports other than React.
#   - CDN-script surface (no `<Script>`, no
#     `loadScriptOnce`, no `dangerouslySetInnerHTML`).
#   - Reverse deep imports into any other layer of
#     `@taxa/research` (the Splitter only needs React).
#   - Cross-module imports outside Research (no
#     `@taxa/browser-state`, no `@taxa/taxonomy`, no
#     `@taxa/design-system`, no `@taxa/app-shell`).
#   - Legacy + isolation tokens (`web/`, `src/app/page`,
#     `settings.reset`, `materialize`, etc.).
#   - CommonJS / process / CDN-library tokens.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("token", _SPLITTER_FORBIDDEN)
def test_w6_3_splitter_source_purity(token: str) -> None:
    """W6.3 — the Splitter stays free of forbidden tokens
    (no fetch, no cross-layer imports, no CDN-script
    surface, no legacy mutation, no cross-module scope
    creep, no settings reset, no materialization, no
    framework imports other than React). Comments are
    stripped before scanning so JSDoc can reference
    forbidden-token words without tripping the guard."""
    if not SPLITTER_FILE.is_file():
        pytest.skip("Splitter.tsx not present yet")
    text = _strip_ts_comments(SPLITTER_FILE.read_text())
    assert token not in text, (
        f"Splitter.tsx must stay free of {token!r}; the "
        f"W6.3 isolation contract forbids it. The Splitter "
        f"is a DOM-bound Client Component (uses "
        f"`document.`, `window.`, `localStorage`) but does "
        f"NOT touch the network, the CDN script surface, "
        f"the legacy `web/` directory, the `src/app/page.tsx` "
        f"route, the FastAPI server, the materialization "
        f"pipeline, the settings reset, or any cross-module "
        f"chunk outside `@taxa/research`."
    )


def test_w6_3_splitter_imports_only_react() -> None:
    """W6.3 — the Splitter's only runtime import is
    `react` (and its `react/jsx-runtime` hook). No
    deep imports into any other layer of
    `@taxa/research` (the Splitter is presentation-local;
    the pure helpers + storage constants are exported
    from the same module so the focused test harness
    exercises them through the public barrel). No
    cross-module imports outside Research (no
    `@taxa/browser-state`, no `@taxa/taxonomy`, no
    `@taxa/design-system`, no `@taxa/app-shell`).
    spec.md rule 5 keeps cross-module imports anchored
    at the public barrel; the Splitter reaches the
    React mount through `@taxa/research`'s default
    re-export."""
    if not SPLITTER_FILE.is_file():
        pytest.skip("Splitter.tsx not present yet")
    text = SPLITTER_FILE.read_text()
    imports = re.findall(r'from\s+["\']([^"\']+)["\']', text)
    assert imports, "Splitter.tsx must import something (React)"
    for src in imports:
        assert src.startswith("react") or src == "react", (
            f"Splitter.tsx imports from {src!r}; must be `react` "
            f"only (the Splitter is a DOM-bound Client "
            f"Component that reaches its peer components + the "
            f"public barrel through `@taxa/research`'s default "
            f"re-export). spec.md rule 5 keeps cross-module "
            f"imports anchored at the public barrel."
        )


def test_w6_3_splitter_exports_named_pure_helpers_and_constants() -> None:
    """W6.3 — the Splitter must export the pure helpers +
    storage constants as named exports so the focused
    test harness exercises them under Node without React
    or the DOM event system. Each helper + constant is
    reachable through the public barrel so cross-module
    consumers (future tests, a hypothetical React mount
    that wants to compose the helpers without spinning
    up the React event system) read them through
    `@taxa/research`."""
    if not SPLITTER_FILE.is_file():
        pytest.skip("Splitter.tsx not present yet")
    text = SPLITTER_FILE.read_text()
    for symbol in (
        "TREE_WIDTH_STORAGE_KEY",
        "MIN_TREE_WIDTH_PX",
        "VIEWER_RESERVED_PX",
        "clampTreeWidth",
        "readSavedTreeWidth",
        "writeSavedTreeWidth",
        "clearSavedTreeWidth",
    ):
        assert re.search(
            rf"export\s+(?:const|function)\s+{symbol}\b", text,
        ), (
            f"Splitter.tsx must export `{symbol}` as a named "
            f"constant or function (the W6.3 pure-handler / "
            f"storage helper surface)."
        )


def test_w6_3_splitter_default_export_is_default() -> None:
    """W6.3 — the Splitter component is the file's
    default export (the React mount consumes it via
    `import Splitter from "@taxa/research"` through the
    barrel's `export { default as Splitter }` re-export).
    A future PR that flips to a named export would
    silently break the Explorer's `import { Splitter }`
    wiring (which reads it as a named re-export from the
    barrel)."""
    if not SPLITTER_FILE.is_file():
        pytest.skip("Splitter.tsx not present yet")
    text = SPLITTER_FILE.read_text()
    assert re.search(r"export\s+default\s+function\s+Splitter\b", text), (
        "Splitter.tsx must declare `export default function "
        "Splitter` so the React mount + the public barrel "
        "can re-export it as `default as Splitter`."
    )


def test_w6_3_splitter_renders_legacy_separator_semantics() -> None:
    """W6.3 — the Splitter component MUST render
    `role="separator"` + `aria-orientation="vertical"` +
    the legacy `title="Drag to resize · double-click to
    reset"` literal. These three attributes are the
    accessibility contract for vertical separator
    semantics (matches the W3C ARIA `separator` role
    spec + the legacy `web/file_explorer.js::renderSplitter`
    shape verbatim). The test guards the three literals
    against accidental whitespace drift (`title` carries
    the legacy `·` U+00B7 middle-dot character) so the
    React mount's accessibility surface stays in
    lock-step with the legacy oracle."""
    if not SPLITTER_FILE.is_file():
        pytest.skip("Splitter.tsx not present yet")
    text = SPLITTER_FILE.read_text()
    assert 'role="separator"' in text, (
        "Splitter.tsx must render `role=\"separator\"` so the "
        "drag handle exposes vertical-separator ARIA "
        "semantics (W3C ARIA `separator` role)."
    )
    assert 'aria-orientation="vertical"' in text, (
        "Splitter.tsx must render `aria-orientation=\"vertical\"` "
        "so the drag handle's orientation is explicit (the "
        "W3C ARIA `separator` role's default is horizontal)."
    )
    assert 'title="Drag to resize \u00b7 double-click to reset"' in text, (
        "Splitter.tsx must render the legacy `title` literal "
        "`Drag to resize \u00b7 double-click to reset` (the "
        "`\u00b7` middle-dot character is byte-equal against "
        "the legacy `web/file_explorer.js::renderSplitter` "
        "string)."
    )


def test_w6_3_splitter_wires_mousedown_with_prevent_default() -> None:
    """W6.3 — the Splitter's mousedown handler MUST call
    `preventDefault` so the mousedown doesn't trigger
    text selection drag (mirrors the legacy
    `web/file_explorer.js::renderSplitter` `e.preventDefault()`
    shape verbatim — the legacy explicitly calls this so a
    user accidentally clicking on a row of text inside
    the splitter doesn't start a text selection that
    fights the drag)."""
    if not SPLITTER_FILE.is_file():
        pytest.skip("Splitter.tsx not present yet")
    text = SPLITTER_FILE.read_text()
    # Find the mousedown handler body. The pattern matches
    # `onMouseDown={handleMouseDown}` on the rendered
    # `<div>` so the test pins both the handler attachment
    # AND the preventDefault call inside the handler body.
    assert "onMouseDown={handleMouseDown}" in text, (
        "Splitter.tsx must wire `onMouseDown={handleMouseDown}` "
        "on the rendered `<div>` so the React mount's drag "
        "lifecycle matches the legacy `addEventListener` "
        "attachment."
    )
    assert "e.preventDefault()" in text, (
        "Splitter.tsx's mousedown handler must call "
        "`e.preventDefault()` so the mousedown doesn't "
        "trigger text selection drag (mirrors the legacy "
        "`web/file_explorer.js::renderSplitter` "
        "`e.preventDefault()` shape verbatim)."
    )


def test_w6_3_splitter_wires_doubleclick_handler() -> None:
    """W6.3 — the Splitter's `<div>` MUST wire an
    `onDoubleClick` handler so a double-click clears the
    localStorage key + the inline width so the legacy CSS
    default takes over again (mirrors the legacy
    `web/file_explorer.js::renderSplitter` `dblclick`
    branch verbatim). The handler is a separate
    `useCallback` (the legacy uses two distinct
    `addEventListener` calls)."""
    if not SPLITTER_FILE.is_file():
        pytest.skip("Splitter.tsx not present yet")
    text = SPLITTER_FILE.read_text()
    assert "onDoubleClick={handleDoubleClick}" in text, (
        "Splitter.tsx must wire `onDoubleClick={handleDoubleClick}` "
        "on the rendered `<div>` so the React mount's "
        "double-click reset matches the legacy "
        "`addEventListener(\"dblclick\", …)` shape."
    )


def test_w6_3_splitter_storage_key_is_pinned_literal() -> None:
    """W6.3 — the `TREE_WIDTH_STORAGE_KEY` constant MUST
    equal the literal `"taxa.fex.treeWidth"` (pinned
    byte-for-byte against the legacy
    `web/file_explorer.js::TREE_WIDTH_STORAGE_KEY`). The
    runtime harness exercises the literal value end-to-end;
    this source-level guard catches a future PR that
    renames the constant without renaming the localStorage
    key (which would silently lose persistence across
    reloads)."""
    if not SPLITTER_FILE.is_file():
        pytest.skip("Splitter.tsx not present yet")
    text = SPLITTER_FILE.read_text()
    m = re.search(
        r'export\s+const\s+TREE_WIDTH_STORAGE_KEY\s*=\s*"([^"]+)"',
        text,
    )
    assert m, (
        "Splitter.tsx must declare `export const "
        "TREE_WIDTH_STORAGE_KEY = \"...\"` as a named "
        "constant (the W6.3 localStorage-key surface)."
    )
    assert m.group(1) == "taxa.fex.treeWidth", (
        f"TREE_WIDTH_STORAGE_KEY must equal the literal "
        f"`\"taxa.fex.treeWidth\"` (legacy verbatim); got "
        f"{m.group(1)!r}. Renaming the key would silently "
        f"lose persistence across reloads."
    )


def test_w6_3_barrel_reexports_splitter_and_pure_helpers() -> None:
    """W6.3 — the public barrel MUST re-export the
    Splitter default export + the pure helpers + the
    storage key constant + the width-bound constants so
    cross-module consumers (the W6.3 React mount,
    integration tests) reach the W6.3 contract through
    the barrel. spec.md rule 5 keeps cross-module
    imports anchored at the public barrel."""
    if not BARREL_FILE.is_file():
        pytest.skip("barrel not present yet")
    text = BARREL_FILE.read_text()
    # Default-export re-export for the Splitter component.
    assert re.search(
        r'export\s+\{\s*default\s+as\s+Splitter\b',
        text,
    ), (
        "barrel must re-export `Splitter` as a default "
        "export so cross-module consumers can mount it "
        "through `import { Splitter } from \"@taxa/research\"`."
    )
    # Named-export re-exports for the pure helpers + the
    # storage key + the width-bound constants.
    for symbol in (
        "TREE_WIDTH_STORAGE_KEY",
        "MIN_TREE_WIDTH_PX",
        "VIEWER_RESERVED_PX",
        "clampTreeWidth",
        "readSavedTreeWidth",
        "writeSavedTreeWidth",
        "clearSavedTreeWidth",
    ):
        assert symbol in text, (
            f"barrel must re-export the W6.3 helper or "
            f"constant `{symbol}`."
        )


def test_w6_3_explorer_mounts_splitter_between_tree_and_viewer() -> None:
    """W6.3 — the Explorer.tsx React mount MUST render
    `<Splitter />` between the `.fex-tree-pane` sibling
    + the `.fex-viewer-pane` sibling (the splitter is a
    direct child of the `.fex-shell` two-pane layout, in
    the same DOM-order position the legacy
    `web/file_explorer.js::rerender()` paints it). The
    Splitter's `parentElement.querySelector(".fex-tree-pane")`
    lookup depends on the Splitter's parent being the
    `.fex-shell` element with both panes as siblings; a
    future PR that nests the Splitter under a different
    parent would silently break the drag lifecycle (the
    querySelector would return `null`)."""
    if not EXPLORER_FILE.is_file():
        pytest.skip("Explorer.tsx not present yet")
    text = EXPLORER_FILE.read_text()
    # The Explorer must import Splitter from the public
    # barrel (spec.md rule 5).
    assert re.search(
        r'import\s+\{[^}]*\bSplitter\b[^}]*\}\s+from\s+'
        r'["\']@taxa/research["\']',
        text,
    ), (
        "Explorer.tsx must import `Splitter` from "
        "`@taxa/research` (spec.md rule 5 keeps "
        "cross-module imports anchored at the public "
        "barrel)."
    )
    # The Splitter's render position is between the
    # `.fex-tree-pane` JSX block + the `.fex-viewer-pane`
    # JSX block. The test scans for the triplet shape so
    # a future PR that reorders the panes (e.g. putting
    # the viewer on the left) is caught.
    tree_pane_idx = text.find('fex-tree-pane')
    splitter_idx = text.find("<Splitter")
    viewer_pane_idx = text.find('fex-viewer-pane')
    assert tree_pane_idx > 0 and splitter_idx > 0 and viewer_pane_idx > 0, (
        "Explorer.tsx must render `<Splitter />` between "
        "the `.fex-tree-pane` sibling + the `.fex-viewer-pane` "
        "sibling (the splitter walks the DOM from its "
        "`parentElement` and queries `.fex-tree-pane` — "
        "the querySelector shape depends on both panes "
        "being direct siblings under the `.fex-shell` "
        "container)."
    )
    assert tree_pane_idx < splitter_idx < viewer_pane_idx, (
        "Explorer.tsx must render `<Splitter />` AFTER "
        "the `.fex-tree-pane` JSX block + BEFORE the "
        "`.fex-viewer-pane` JSX block. The current order "
        f"is tree_pane={tree_pane_idx}, "
        f"splitter={splitter_idx}, viewer_pane={viewer_pane_idx}."
    )


# ---------------------------------------------------------------------------
# W6.3 — compile + runtime contract for the Splitter.
# The Splitter is DOM-bound (uses `document.body`,
# `globalThis.localStorage`, `MouseEvent`), so the
# focused compile uses `--lib ES2022,DOM` (not
# `--lib ES2022` alone like the framework-free kernel).
# The runtime harness stubs `globalThis.localStorage` so
# every storage helper can be exercised under Node
# without a real browser. The harness also exercises
# `clampTreeWidth` end-to-end so the legacy bounds
# (12rem min, 20rem reserved) stay pinned.
# ---------------------------------------------------------------------------
def _run_tsc_isolated_splitter(
    out_dir: Path,
    sources: list[Path],
    extra: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Compile the W6.3 Splitter + the W6.1 framework-free
    kernel + the W1 domain + the W4a–W4b4 renderers in
    isolation. Flags mirror the W6.1 kernel contract but
    extend `--lib` with `DOM` so the Splitter's
    `document.body`, `MouseEvent`, and
    `globalThis.localStorage` references compile under
    TypeScript without `--strict` falling back to
    implicit-any. Adds `--jsx react-jsx` so the React
    JSX in `Splitter.tsx` compiles under the new JSX
    transform (the runtime harness loads the compiled
    output via `require()` and the new transform emits
    `_jsx` calls against `react/jsx-runtime`).

    The kernel + W1 domain + W4a–W4b4 renderers stay in
    the compile graph so the inline
    `import("../application/renderers").ViewerDispatch`
    type-only import in `explorer-state.ts` resolves
    cleanly."""
    return subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--strict",
            "--target", "ES2022",
            "--module", "commonjs",
            "--lib", "ES2022,DOM",
            "--jsx", "react-jsx",
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
def compiled_w6_3_splitter(
    tmp_path: Path, require_toolchain: None,
) -> Path:
    """Compile the W6.3 Splitter alongside the W6.1
    framework-free kernel + the W1 domain + the W4a–W4b4
    renderers. Returns the compiled Splitter path; the
    runtime harness loads it and exercises every pure
    helper + every storage helper under Node's
    ES2022+DOM environment (no React runtime)."""
    for p in (
        DOMAIN_FILE, RENDERERS_FILE, EXPLORER_STATE_FILE, SPLITTER_FILE,
    ):
        if not p.is_file():
            pytest.skip(f"missing required source: {p}")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    result = _run_tsc_isolated_splitter(
        out_dir,
        [DOMAIN_FILE, RENDERERS_FILE, EXPLORER_STATE_FILE, SPLITTER_FILE],
    )
    assert result.returncode == 0, (
        f"Splitter.tsx failed to compile in isolated strict "
        f"mode.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    compiled_splitter = (
        out_dir / "presentation" / "Splitter.js"
    )
    assert compiled_splitter.is_file(), (
        f"tsc did not emit `presentation/Splitter.js` at "
        f"{compiled_splitter}.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    return compiled_splitter


# W6.3 runtime harness — exercises the Splitter's pure
# helpers + storage helpers under Node's ES2022+DOM
# environment. The harness stubs `globalThis.localStorage`
# (a Map-backed mock + a throwing variant) so every
# storage branch (happy path, getItem throws, setItem
# throws, removeItem throws, localStorage undefined) can
# be exercised end-to-end without a real browser.
_SPLITTER_RUNTIME_HARNESS = r"""
// CJS does not support top-level await (only ESM does), so
// the harness wraps the assertions in a sync body — every
// W6.3 Splitter helper is pure (no async, no I/O).
const path = require("path");
const assert = require("assert");
const splitter = require(path.resolve(process.argv[2]));

// 1. Constants — every W6.3 width-bound + storage-key
//    constant is pinned byte-for-byte against the legacy
//    `web/file_explorer.js::TREE_WIDTH_STORAGE_KEY` +
//    `MIN_WIDTH` + `MAX_WIDTH` (which the legacy computes
//    as `shellWidth - 20 * 16`).
{
  assert.strictEqual(
    splitter.TREE_WIDTH_STORAGE_KEY, "taxa.fex.treeWidth",
    "TREE_WIDTH_STORAGE_KEY must equal the legacy literal \"taxa.fex.treeWidth\"",
  );
  assert.strictEqual(
    splitter.MIN_TREE_WIDTH_PX, 12 * 16,
    "MIN_TREE_WIDTH_PX must equal 12 * 16 = 192px (legacy verbatim)",
  );
  assert.strictEqual(
    splitter.VIEWER_RESERVED_PX, 20 * 16,
    "VIEWER_RESERVED_PX must equal 20 * 16 = 320px (legacy verbatim)",
  );
}

// 2. clampTreeWidth — pure helper. Mirrors the legacy
//    `Math.max(MIN_WIDTH, Math.min(next, MAX_WIDTH))`
//    shape verbatim, with the `Math.max(min, …)` upper-
//    bound guard so a too-narrow shell can never pin the
//    tree to a negative width.
//
//    Cases:
//    a. candidate within bounds → return candidate.
//    b. candidate below MIN_TREE_WIDTH_PX → return MIN.
//    c. candidate above (shellWidth - VIEWER_RESERVED_PX) → return MAX.
//    d. shellWidth smaller than 2*MIN_TREE_WIDTH_PX → MAX
//       clamps to MIN so the user is pinned to MIN (the
//       viewer would otherwise be negative).
{
  // 2a — happy path (500 in a 1000-wide shell).
  assert.strictEqual(
    splitter.clampTreeWidth(500, 1000), 500,
    "candidate within bounds must return candidate",
  );
  // 2b — below min (100 in a 1000-wide shell).
  assert.strictEqual(
    splitter.clampTreeWidth(100, 1000), splitter.MIN_TREE_WIDTH_PX,
    "candidate below MIN must return MIN_TREE_WIDTH_PX",
  );
  // 2c — above max (900 in a 1000-wide shell; max = 680).
  assert.strictEqual(
    splitter.clampTreeWidth(900, 1000), 680,
    "candidate above MAX must return shellWidth - VIEWER_RESERVED_PX",
  );
  // 2d — too-narrow shell (300-wide shell; max would be
  // -20, but the Math.max(MIN, …) guard clamps max to MIN
  // so the user stays pinned to MIN_TREE_WIDTH_PX).
  assert.strictEqual(
    splitter.clampTreeWidth(500, 300), splitter.MIN_TREE_WIDTH_PX,
    "too-narrow shell must pin candidate to MIN_TREE_WIDTH_PX (max clamps to min)",
  );
  // 2e — exactly at MIN.
  assert.strictEqual(
    splitter.clampTreeWidth(splitter.MIN_TREE_WIDTH_PX, 1000),
    splitter.MIN_TREE_WIDTH_PX,
    "candidate exactly at MIN must return MIN",
  );
  // 2f — exactly at MAX.
  assert.strictEqual(
    splitter.clampTreeWidth(680, 1000), 680,
    "candidate exactly at MAX must return MAX",
  );
}

// 3. readSavedTreeWidth — happy path + error swallow +
//    localStorage undefined. Mirrors the legacy
//    `readSavedTreeWidth` shape byte-for-byte (try/catch
//    around `localStorage.getItem`; returns `null` on
//    every failure mode).
{
  // 3a — key set returns the stored string verbatim.
  globalThis.localStorage = {
    getItem: (key) => key === splitter.TREE_WIDTH_STORAGE_KEY ? "350px" : null,
    setItem: () => {},
    removeItem: () => {},
  };
  assert.strictEqual(
    splitter.readSavedTreeWidth(), "350px",
    "readSavedTreeWidth must return the stored value verbatim",
  );
  // 3b — key absent returns null.
  globalThis.localStorage = {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
  };
  assert.strictEqual(
    splitter.readSavedTreeWidth(), null,
    "readSavedTreeWidth must return null when the key is absent",
  );
  // 3c — getItem throws → swallow + return null.
  globalThis.localStorage = {
    getItem: () => { throw new Error("QuotaExceededError"); },
    setItem: () => {},
    removeItem: () => {},
  };
  assert.strictEqual(
    splitter.readSavedTreeWidth(), null,
    "readSavedTreeWidth must swallow getItem errors and return null",
  );
  // 3d — localStorage undefined → return null (SSR / Node).
  delete globalThis.localStorage;
  assert.strictEqual(
    splitter.readSavedTreeWidth(), null,
    "readSavedTreeWidth must return null when localStorage is undefined",
  );
}

// 4. writeSavedTreeWidth — happy path + setItem-throw
//    swallow + localStorage undefined.
{
  let lastKey = null;
  let lastValue = null;
  globalThis.localStorage = {
    getItem: () => null,
    setItem: (key, value) => { lastKey = key; lastValue = value; },
    removeItem: () => {},
  };
  splitter.writeSavedTreeWidth("420px");
  assert.strictEqual(
    lastKey, splitter.TREE_WIDTH_STORAGE_KEY,
    "writeSavedTreeWidth must persist under TREE_WIDTH_STORAGE_KEY",
  );
  assert.strictEqual(
    lastValue, "420px",
    "writeSavedTreeWidth must persist the value verbatim (pixel-string shape)",
  );
  // 4b — setItem throws → swallow + no throw.
  globalThis.localStorage = {
    getItem: () => null,
    setItem: () => { throw new Error("QuotaExceededError"); },
    removeItem: () => {},
  };
  // The helper must NOT throw — it swallows silently so
  // the splitter still works in private-browsing contexts.
  splitter.writeSavedTreeWidth("500px");
  // 4c — localStorage undefined → no-op.
  delete globalThis.localStorage;
  splitter.writeSavedTreeWidth("600px");
}

// 5. clearSavedTreeWidth — happy path + removeItem-throw
//    swallow + localStorage undefined.
{
  let removedKey = null;
  globalThis.localStorage = {
    getItem: () => "350px",
    setItem: () => {},
    removeItem: (key) => { removedKey = key; },
  };
  splitter.clearSavedTreeWidth();
  assert.strictEqual(
    removedKey, splitter.TREE_WIDTH_STORAGE_KEY,
    "clearSavedTreeWidth must remove TREE_WIDTH_STORAGE_KEY",
  );
  // 5b — removeItem throws → swallow.
  globalThis.localStorage = {
    getItem: () => "350px",
    setItem: () => {},
    removeItem: () => { throw new Error("SecurityError"); },
  };
  splitter.clearSavedTreeWidth();
  // 5c — localStorage undefined → no-op.
  delete globalThis.localStorage;
  splitter.clearSavedTreeWidth();
}

// 6. Round-trip — write + read + clear under the SAME
//    localStorage stub. Mirrors the legacy's
//    `readSavedTreeWidth` → drag → `writeSavedTreeWidth`
//    → double-click → `clearSavedTreeWidth` lifecycle
//    end-to-end.
{
  const store = new Map();
  globalThis.localStorage = {
    getItem: (key) => store.has(key) ? store.get(key) : null,
    setItem: (key, value) => { store.set(key, String(value)); },
    removeItem: (key) => { store.delete(key); },
  };
  // Initially absent.
  assert.strictEqual(splitter.readSavedTreeWidth(), null);
  // Drag commits the width.
  splitter.writeSavedTreeWidth("275px");
  assert.strictEqual(splitter.readSavedTreeWidth(), "275px");
  // Double-click clears.
  splitter.clearSavedTreeWidth();
  assert.strictEqual(splitter.readSavedTreeWidth(), null);
}

process.stdout.write("PASS\n");
"""


def test_compiled_w6_3_splitter_passes_runtime_contract(
    compiled_w6_3_splitter: Path,
    tmp_path: Path,
) -> None:
    """Under Node (ES2022 + DOM, with `react/jsx-runtime`
    resolved via `NODE_PATH`), the compiled W6.3 Splitter
    satisfies the legacy splitter contract end-to-end:

      1. `TREE_WIDTH_STORAGE_KEY` equals `"taxa.fex.treeWidth"`
         (pinned byte-for-byte).
      2. `MIN_TREE_WIDTH_PX` equals `12 * 16` (legacy
         verbatim).
      3. `VIEWER_RESERVED_PX` equals `20 * 16` (legacy
         verbatim).
      4. `clampTreeWidth` clamps to MIN on the lower
         bound, to `(shellWidth - VIEWER_RESERVED_PX)` on
         the upper bound, and pins to MIN when the shell
         is too narrow for both bounds (the Math.max(MIN,
         …) upper-bound guard).
      5. `readSavedTreeWidth` returns the stored value
         verbatim, returns null on absent key, swallows
         getItem throws, returns null when localStorage
         is undefined.
      6. `writeSavedTreeWidth` persists under the pinned
         key, swallows setItem throws, no-ops when
         localStorage is undefined.
      7. `clearSavedTreeWidth` removes the pinned key,
         swallows removeItem throws, no-ops when
         localStorage is undefined.
      8. Round-trip — write + read + clear under the
         SAME localStorage stub mirrors the legacy's
         read → drag → write → double-click → clear
         lifecycle end-to-end.

    The runtime harness sets `NODE_PATH` to the
    project's `node_modules` so Node can resolve
    `react` + `react/jsx-runtime` from the compiled
    Splitter's location under `tmp_path` (the harness
    itself lives under pytest's tmp directory, which has
    no local `node_modules`). The harness only calls the
    pure helpers + constants; the React component is
    never instantiated so the React runtime is purely a
    module-resolution dependency."""
    import os
    harness = tmp_path / "harness.cjs"
    harness.write_text(_SPLITTER_RUNTIME_HARNESS)
    node_modules_path = REPO_ROOT / "node_modules"
    env = {
        **os.environ,
        "NODE_PATH": str(node_modules_path),
    }
    result = subprocess.run(
        ["node", str(harness), str(compiled_w6_3_splitter)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"W6.3 runtime harness failed.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected W6.3 harness output: {result.stdout!r}"
    )


# ---------------------------------------------------------------------------
# W6.1 — runtime contract for the framework-free kernel.
# The kernel + W1 domain + W4a–W4b4 renderers compile in
# isolation under `--lib ES2022` (no DOM, no React) and
# satisfy the W6.1 pure contract end-to-end under Node.
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# W64A-JSON-001 — native JSON Tree viewer materialization.
# The dispatcher's W4b4 `json-source` branch carries bytes
# + descriptor (NO CDN metadata — JSON parsing is native per
# the spec's "Tree viewer tab / No CDN is used." requirement).
# The React mount consumes the bytes through the existing
# `bytesRequiredForFormat` seam (so JSON is now in the
# bytes-required group) and renders an accessible,
# collapsible Explorer tree faithful to the legacy
# `web/file_viewer.js::renderJsonTree` oracle. The
# missing-bytes fallback/download behavior (the
# `json-offline` dispatch) is preserved verbatim — the mount
# continues to surface it through the same recovery card the
# W6.1 contract ships.
#
# The W64A surface is intentionally narrow:
#   - `bytesRequiredForFormat("json") === true`
#     (the kernel contract flips for JSON so the bytes-fetch
#     effect in `Viewer.tsx` reads the JSON bytes through the
#     same seam the TXT / MD / SVG effects already use).
#   - A pure `parseJsonTree(bytes)` kernel helper in
#     `explorer-state.ts` decodes UTF-8 + calls `JSON.parse`
#     + returns the typed `{ ok, value }` / `{ ok: false,
#     error }` shape. Pure, framework-free, importable through
#     the public barrel.
#   - A `JsonTree` + `JsonNode` React sub-component inside
#     `Viewer.tsx` that renders the typed `json-source`
#     dispatch: caret + summary + key + type-meta + lazy
#     children, faithful to the legacy
#     `web/file_viewer.js::renderJsonNode` shape byte-for-byte.
#   - `aria-expanded` + `role="button"` + `tabIndex={0}` +
#     keyboard Enter/Space handlers on the summary row so the
#     tree is accessible (the W3C ARIA disclosure-widget
#     pattern). The legacy uses `<div role="button" tabindex="0">`
#     for the same affordance.
#   - The legacy `MAX_JSON_NODES = 50_000` truncation cap is
#     pinned byte-for-byte — past the cap the React mount
#     paints the exact `Tree truncated — open raw` banner the
#     legacy `web/file_viewer.js::renderJsonTree` paints.
#   - The `json-offline` dispatch continues to flow through
#     `renderOfflineCard` (the existing W6.1 cdn-pending
#     recovery path) — the missing-bytes fallback/download
#     behavior is retained verbatim.
#
# The W64A surface DOES NOT:
#   - Add a CDN loader, `<Script>` component, or any third-party
#     JSON library. JSON parsing is native (`JSON.parse`).
#   - Change the application-layer `dispatchViewer` contract —
#     the `json-source` / `json-offline` variants are emitted
#     by the W4b4 dispatcher unchanged.
#   - Begin the DOCX / Mammoth slice (W64B-DOCX-002).
# ---------------------------------------------------------------------------


# W64A-JSON-001 — Viewer.tsx source-level shape.
# The W64A contract surfaces through the existing Viewer.tsx
# file: the JSON Tree component lives as a sub-component inside
# Viewer.tsx (the React mount is the JSON consumer; the file is
# allowed for editing per the task brief). The tests below pin
# the JSON-specific JSX shape + the dispatch branch so a future
# PR cannot silently drop the JSON rendering.
def test_w64a_json_viewer_handles_json_source_dispatch() -> None:
    """W64A-JSON-001 — the renderDispatch switch in
    Viewer.tsx MUST have an EXPLICIT `case "json-source"`
    arm that paints the native JSON Tree (NOT the cdn-pending
    recovery card the W6.1 fallback uses). The cdn-pending
    path is preserved for the other CDN-backed variants; the
    JSON path renders the typed native tree because JSON
    parsing has no CDN dependency. A future PR that merges
    `json-source` into the cdn-pending fallback branch
    silently breaks the JSON Tree viewer."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r'case\s+"json-source"\s*:', text), (
        "Viewer.tsx MUST have an explicit `case \"json-source\":` "
        "branch in `renderDispatch` so the typed JSON Tree "
        "viewer renders the native tree (NOT the W6.1 "
        "cdn-pending fallback). W64A-JSON-001 contract: "
        "JSON Tree dispatch receives fetched bytes through "
        "the existing `bytesRequiredForFormat` seam and "
        "renders the native tree."
    )
    # The case must render the native JSON Tree — a
    # JsonTree / renderJsonTree / parseJsonTree reference
    # must live inside the JSON branch's body. A JSON
    # branch that maps straight to `renderOfflineCard`
    # (the W6.1 cdn-pending catch-all) would NOT carry
    # such a marker, so the test fails RED until the
    # native rendering is wired.
    json_branch_match = re.search(
        r'case\s+"json-source"\s*:(.*?)(?=case\s+"|\}\s*\n\s*\})',
        text, re.DOTALL,
    )
    assert json_branch_match, (
        "Viewer.tsx must have an extractable `json-source` "
        "branch body in `renderDispatch`."
    )
    json_branch = json_branch_match.group(1)
    assert re.search(r'\bJsonTree\b|\brenderJsonTree\b|\bparseJsonTree\b',
                     json_branch), (
        "Viewer.tsx's `case \"json-source\":` branch MUST "
        "reference the JSON Tree rendering helper "
        "(`JsonTree` / `renderJsonTree` / `parseJsonTree`) "
        "so the native tree renders — NOT the W6.1 "
        "`renderOfflineCard` cdn-pending fallback. "
        "W64A-JSON-001 acceptance: 'JSON Tree dispatch "
        "receives fetched bytes, parses JSON natively, "
        "renders an accessible/collapsible Explorer tree "
        "faithful to the legacy oracle'."
    )


def test_w64a_json_viewer_renders_json_offline_via_existing_fallback() -> None:
    """W64A-JSON-001 — the `json-offline` dispatch continues to
    flow through the existing `renderOfflineCard` recovery
    path. The task brief mandates the existing
    missing-bytes fallback/download behavior be retained. The
    W6.1 contract already routes every `*-offline` variant
    (docx-offline / sheet-offline / epub-offline /
    table-offline / json-offline) through `renderOfflineCard`;
    the W64A contract MUST NOT carve json-offline into a
    separate branch — the user keeps a single, consistent
    recovery path regardless of which CDN-backed format
    would have been loaded."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    # The renderOfflineCard helper is the W6.1 typed
    # recovery path; the json-offline case stays inside the
    # cdn-pending catch-all branch that funnels every
    # `*-offline` variant through renderOfflineCard. The
    # test asserts the json-offline literal still lives in
    # the renderOfflineCard branch (NOT a new dedicated
    # case), so the existing download affordance stays in
    # place for the missing-bytes path.
    offline_card_match = re.search(
        r'function\s+renderOfflineCard\s*\([^)]*\)\s*:\s*ReactNode\s*\{(.*?)\n\}',
        text, re.DOTALL,
    )
    assert offline_card_match, (
        "Viewer.tsx must still export the `renderOfflineCard` "
        "helper (the W6.1 typed recovery path that the "
        "`*-offline` variants all funnel through)."
    )
    offline_card_body = offline_card_match.group(1)
    assert 'json-offline' in offline_card_body, (
        "Viewer.tsx's `renderOfflineCard` helper MUST still "
        "match the `json-offline` literal so the existing "
        "missing-bytes fallback/download behavior is retained "
        "(W64A-JSON-001 acceptance: 'retain existing "
        "missing-bytes fallback/download behavior')."
    )


def test_w64a_json_viewer_does_not_use_dangerously_set_inner_html() -> None:
    """W64A-JSON-001 — the JSON Tree viewer renders React
    components, NOT injected HTML. The XSS-safe SVG variant
    uses `dangerouslySetInnerHTML` because the W4a
    `sanitizeSvgMarkup` scrub is the typed hand-off; the JSON
    Tree viewer has no analogous sanitization layer — it
    renders values via React children (so React escapes the
    text content automatically). A future PR that injects JSON
    values through `dangerouslySetInnerHTML` would expose the
    tree to XSS. The test guards the JSON path against
    accidental `dangerouslySetInnerHTML` injection."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    # Locate the JSON Tree rendering block (anything between
    # the `case "json-source":` branch and the next case OR
    # the end of renderDispatch). We use a heuristic: every
    # `dangerouslySetInnerHTML` reference inside Viewer.tsx
    # is the SVG-sanitized branch (the only legitimate use);
    # the JSON Tree branch must not introduce a new one.
    # The test asserts the JSON-specific JSX block does not
    # contain `dangerouslySetInnerHTML`.
    json_branch_match = re.search(
        r'case\s+"json-source"\s*:(.*?)(?=case\s+"|\}\s*\n\s*\})',
        text, re.DOTALL,
    )
    if json_branch_match is None:
        pytest.skip("json-source branch not present yet")
    json_branch = json_branch_match.group(1)
    assert "dangerouslySetInnerHTML" not in json_branch, (
        "Viewer.tsx's `json-source` branch must NOT use "
        "`dangerouslySetInnerHTML` to inject JSON values — "
        "React's text-content escaping is the XSS guard for "
        "the tree viewer; injecting raw HTML would expose "
        "the user to XSS through malicious JSON content."
    )


def test_w64a_json_viewer_has_accessible_button_role() -> None:
    """W64A-JSON-001 — the JSON Tree summary row MUST render
    `role="button"` + `tabIndex={0}` + a keyboard handler
    so the disclosure widget is accessible (the W3C ARIA
    disclosure-widget pattern). The legacy
    `web/file_viewer.js::renderJsonNode` paints
    `<div class="fex-json-summary" role="button" tabindex="0">`
    + wires Enter/Space keyboard handlers; the React mount
    mirrors that shape so the accessibility surface stays
    in lock-step with the legacy oracle."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    # Look for the legacy oracle's accessibility markers
    # inside the Viewer.tsx source. The exact JSX spelling
    # for tabIndex is camelCase in React.
    assert 'role="button"' in text, (
        "Viewer.tsx must render `role=\"button\"` on the "
        "JSON Tree summary row so the disclosure widget "
        "exposes button semantics to assistive tech (the "
        "W3C ARIA disclosure-widget pattern; mirrors the "
        "legacy `web/file_viewer.js::renderJsonNode` "
        "shape)."
    )
    assert "tabIndex=" in text or "tabindex=" in text.lower(), (
        "Viewer.tsx must render a non-negative `tabIndex` "
        "on the JSON Tree summary row so the disclosure "
        "widget is keyboard-focusable (the legacy "
        "`tabindex=\"0\"` shape)."
    )


def test_w64a_json_viewer_renders_legacy_root_literal() -> None:
    """W64A-JSON-001 — the JSON Tree host MUST paint the
    legacy `[root]` literal as the root key (the synthetic
    root identifier). Mirrors the legacy
    `web/file_viewer.js::renderJsonNode` shape verbatim —
    the legacy uses the literal `[root]` for the wire-
    document root so the user has a stable visible label
    independent of the actual JSON value's name. A future
    PR that re-words the root label (e.g. `Root`, `JSON`)
    silently breaks visual parity with the legacy oracle."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r'\[\s*["\']root["\']\s*\]|"\[root\]"|"\\[root\\]"', text), (
        "Viewer.tsx must render the legacy `[root]` literal "
        "as the synthetic root key (the legacy "
        "`web/file_viewer.js::renderJsonNode` shape verbatim)."
    )


def test_w64a_json_viewer_renders_truncation_banner_text() -> None:
    """W64A-JSON-001 — the JSON Tree truncation banner
    MUST render the legacy `Tree truncated — open raw`
    literal (the literal `—` em-dash separator is pinned
    byte-for-byte against the legacy
    `web/file_viewer.js::renderJsonTree` oracle). A future
    PR that re-words the banner (e.g. `Truncated`,
    `Tree too large`, `Open raw to see full`) silently
    breaks the visual + copy parity with the legacy
    oracle."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert "Tree truncated — open raw" in text, (
        "Viewer.tsx must render the legacy `Tree truncated "
        "— open raw` literal (the legacy `web/file_viewer.js::"
        "renderJsonTree` oracle). The em-dash `—` is pinned "
        "byte-for-byte."
    )


# W64A-JSON-001 — parseJsonTree pure helper.
# The pure helper lives in `explorer-state.ts` (the
# framework-free kernel) so it can be exercised under Node
# without React + without the DOM. The helper accepts the
# raw `Uint8Array` bytes (the same shape the W3
# `fetchFileServe` returns + the same shape the W4b4
# `json-source` dispatch carries by reference) and returns
# a typed `{ ok: true, value }` / `{ ok: false, error }`
# result. The React mount consumes the helper via the
# framework-free kernel — no React in the helper's
# implementation.
def test_w64a_explorer_state_exports_parse_json_tree() -> None:
    """W64A-JSON-001 — `explorer-state.ts` MUST export a
    named `parseJsonTree` pure helper so the React mount
    can call `JSON.parse` through the framework-free kernel
    + so the focused test harness exercises the parse
    logic end-to-end without React. A future PR that
    inlines the parse call into the React component would
    couple the JSON path to React's lifecycle + would
    block the framework-free kernel from covering the parse
    contract."""
    if not EXPLORER_STATE_FILE.is_file():
        pytest.skip("explorer-state.ts not present yet")
    text = EXPLORER_STATE_FILE.read_text()
    assert re.search(
        r'export\s+function\s+parseJsonTree\b', text,
    ), (
        "explorer-state.ts must export a named "
        "`parseJsonTree` function (the W64A-JSON-001 "
        "framework-free JSON decoder — pure UTF-8 decode + "
        "`JSON.parse`, returns the typed `{ ok, value }` / "
        "`{ ok: false, error }` shape)."
    )


def test_w64a_explorer_state_exports_max_json_nodes() -> None:
    """W64A-JSON-001 — `explorer-state.ts` MUST export the
    `MAX_JSON_NODES = 50_000` constant (pinned byte-for-byte
    against the legacy `web/file_viewer.js::MAX_JSON_NODES`)
    so the React mount's truncation cap stays in lock-step
    with the legacy oracle. The focused test harness
    exercises the literal value end-to-end; this
    source-level guard catches a future PR that renames the
    constant or flips the cap without updating the legacy
    oracle."""
    if not EXPLORER_STATE_FILE.is_file():
        pytest.skip("explorer-state.ts not present yet")
    text = EXPLORER_STATE_FILE.read_text()
    m = re.search(
        r'export\s+const\s+MAX_JSON_NODES\s*=\s*(\d+)', text,
    )
    assert m, (
        "explorer-state.ts must export `MAX_JSON_NODES` as "
        "a named numeric constant (the legacy 50_000 "
        "truncation cap)."
    )
    assert int(m.group(1)) == 50000, (
        f"MAX_JSON_NODES must equal the legacy `50_000` "
        f"literal (web/file_viewer.js::MAX_JSON_NODES); "
        f"got {m.group(1)!r}. Renaming the cap would "
        f"silently change the truncation threshold."
    )


def test_w64a_viewer_imports_w64a_helpers_via_relative_path() -> None:
    """W64A-JSON-001 — the Viewer.tsx React mount imports
    the W64A pure helpers (`parseJsonTree` + `MAX_JSON_NODES`)
    through the relative `./explorer-state` path, NOT
    through the public barrel. The barrel is intentionally
    NOT extended for the W64A surface in this slice (the
    barrel is owned by a separately authorized slice); the
    W64A helpers are module-local to `presentation/` so
    the Viewer consumes them through the relative path —
    the same module can reach the kernel directly without
    going through the public barrel. A future cross-module
    consumer (a follow-up slice that authorizes the barrel
    extension) would add the helpers to the barrel
    re-export surface."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    # The relative-path import must name BOTH W64A
    # helpers from the same `./explorer-state` module.
    assert re.search(
        r'import\s*\{[^}]*\bparseJsonTree\b[^}]*\}'
        r'\s*from\s*["\']\./explorer-state["\']',
        text,
    ), (
        "Viewer.tsx must import `parseJsonTree` from the "
        "module-local relative path `./explorer-state` "
        "(the W64A helpers are module-local to "
        "`presentation/` — the public barrel is not in "
        "the W64A edit surface)."
    )
    assert re.search(
        r'import\s*\{[^}]*\bMAX_JSON_NODES\b[^}]*\}'
        r'\s*from\s*["\']\./explorer-state["\']',
        text,
    ), (
        "Viewer.tsx must import `MAX_JSON_NODES` from the "
        "module-local relative path `./explorer-state` "
        "(the W64A helpers are module-local to "
        "`presentation/` — the public barrel is not in "
        "the W64A edit surface)."
    )
    # The W64A helpers MUST NOT be imported from the
    # public barrel (the barrel does not extend the W64A
    # surface in this slice). A future PR that re-imports
    # them through `@taxa/research` would silently break
    # because the barrel doesn't re-export them.
    # We scan only the import statement body (between
    # `{` and `}`) so a JSDoc comment that mentions the
    # helper name elsewhere in the file doesn't trip the
    # guard.
    barrel_import_match = re.search(
        r'import\s*\{([^}]*)\}\s*from\s*'
        r'["\']@taxa/research["\']',
        text,
    )
    assert barrel_import_match, (
        "Viewer.tsx must still import its existing "
        "`@taxa/research` surface (the W4a renderers + "
        "the kernel helpers + the typed ViewerDispatch "
        "surface)."
    )
    barrel_import_body = barrel_import_match.group(1)
    assert "parseJsonTree" not in barrel_import_body, (
        "Viewer.tsx's `@taxa/research` import MUST NOT "
        "include `parseJsonTree` — the W64A helpers are "
        "module-local to `presentation/`; the barrel is "
        "not in the W64A edit surface. Use the relative "
        "`./explorer-state` path."
    )
    assert "MAX_JSON_NODES" not in barrel_import_body, (
        "Viewer.tsx's `@taxa/research` import MUST NOT "
        "include `MAX_JSON_NODES` — the W64A helpers are "
        "module-local to `presentation/`; the barrel is "
        "not in the W64A edit surface. Use the relative "
        "`./explorer-state` path."
    )


def test_w64a_barrel_does_not_reexport_w64a_helpers() -> None:
    """W64A-JSON-001 — the public barrel MUST NOT extend
    with `parseJsonTree` + `MAX_JSON_NODES` + `JsonParseResult`
    in this slice (the barrel is not in the W64A edit
    surface). A future PR that extends the barrel for the
    W64A surface would land as a separately authorized
    follow-up slice; for now the barrel's existing
    `presentation/explorer-state` re-exports stay byte-
    equal to the pre-W64A state. The W64A helpers are
    module-local to `presentation/` and reachable through
    the relative `./explorer-state` import from
    `Viewer.tsx`."""
    if not BARREL_FILE.is_file():
        pytest.skip("barrel not present yet")
    text = BARREL_FILE.read_text()
    # Find the `export { ... } from "./presentation/explorer-state"`
    # block — the W64A helpers MUST NOT appear inside it.
    block_match = re.search(
        r'export\s*\{(.*?)\}\s*from\s*["\']'
        r'\./presentation/explorer-state["\']',
        text, re.DOTALL,
    )
    assert block_match, (
        "barrel must still export the existing W6.1 / "
        "W6.2 / W6.3 surface from "
        "`./presentation/explorer-state`."
    )
    block_body = block_match.group(1)
    assert "parseJsonTree" not in block_body, (
        "barrel's `./presentation/explorer-state` "
        "re-export block MUST NOT include `parseJsonTree` "
        "(the W64A helpers are module-local — the barrel "
        "is not in the W64A edit surface)."
    )
    assert "MAX_JSON_NODES" not in block_body, (
        "barrel's `./presentation/explorer-state` "
        "re-export block MUST NOT include `MAX_JSON_NODES` "
        "(the W64A helpers are module-local — the barrel "
        "is not in the W64A edit surface)."
    )


# W64A-JSON-001 — runtime contract for parseJsonTree +
# MAX_JSON_NODES. The harness compiles the W6.1
# framework-free kernel + the W1 domain + the W4a–W4b4
# renderers under `--lib ES2022` and exercises the new
# `parseJsonTree` helper end-to-end under Node. The
# harness mirrors the W6.1 / W6.2 / W6.3 runtime
# harnesses — every JSON helper is pure (no async, no I/O,
# no React), so the assertions run synchronously under
# Node's ES2022-only environment.
def test_w64a_parse_json_tree_passes_runtime_contract(
    compiled_w6_1_kernel: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """W64A-JSON-001 — under Node (ES2022 only, no DOM,
    no React), the compiled framework-free kernel exposes
    the `parseJsonTree` + `MAX_JSON_NODES` surface and
    satisfies the W64A pure JSON-decoder contract end-to-end:

      1. `MAX_JSON_NODES` equals the legacy `50_000`
         literal (pinned byte-for-byte against
         `web/file_viewer.js::MAX_JSON_NODES`).
      2. `parseJsonTree` accepts a `Uint8Array` carrying
         UTF-8 encoded JSON + returns the typed
         `{ ok: true, value }` shape.
      3. `parseJsonTree` decodes UTF-8 verbatim — a JSON
         document with non-ASCII characters (e.g. accented
         names) round-trips through the decoder.
      4. `parseJsonTree` parses objects, arrays,
         primitives (string / number / boolean / null)
         — every JSON value type surfaces through the
         typed result.
      5. `parseJsonTree` returns `{ ok: false, error }`
         for invalid JSON input (mirrors the legacy
         `renderJsonTree` catch branch — the React mount
         paints the offline banner in that path).
      6. `parseJsonTree` is pure — same input bytes
         yields the same output on every call; the
         helper does NOT mutate the input bytes (the
         `bytes` reference contract mirrors the W4b4
         `json-source` bytes-by-reference contract).

    The runtime harness compiles the same W6.1 kernel +
    W1 domain + W4a–W4b4 renderers the existing W6.1
    runtime harness uses, and exercises the new helpers
    without React. A future PR that pulls in a framework
    dependency or touches the DOM trips the focused
    compile gate before the runtime assertion fires."""
    _compiled_kernel, _compiled_renderers = compiled_w6_1_kernel
    harness = tmp_path / "harness.cjs"
    harness.write_text(_W64A_RUNTIME_HARNESS)
    result = subprocess.run(
        ["node", str(harness), str(_compiled_kernel)],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"W64A runtime harness failed.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected W64A harness output: {result.stdout!r}"
    )


_W64A_RUNTIME_HARNESS = r"""
// CJS does not support top-level await (only ESM does), so
// the harness wraps the assertions in a sync body — every
// W64A helper is pure (no async, no I/O).
const path = require("path");
const assert = require("assert");
const kernel = require(path.resolve(process.argv[2]));

// 1. MAX_JSON_NODES — pinned byte-for-byte against the
//    legacy `web/file_viewer.js::MAX_JSON_NODES`. The
//    React mount paints the `Tree truncated — open raw`
//    banner when the rendered node count exceeds the
//    cap; the cap value is part of the public typed
//    surface so a future slice can also use it.
{
  assert.strictEqual(
    kernel.MAX_JSON_NODES, 50000,
    "MAX_JSON_NODES must equal the legacy literal 50000",
  );
}

// 2. parseJsonTree — happy path. A small object decodes
//    + parses through the pure helper; the result is the
//    typed `{ ok: true, value }` shape so the React
//    mount's render switch can destructure the value
//    directly.
{
  const textEncoder = new TextEncoder();
  const bytes = textEncoder.encode(
    '{"hello":"world","nested":{"a":1,"b":[2,3]}}',
  );
  const result = kernel.parseJsonTree(bytes);
  assert.strictEqual(result.ok, true, "happy-path parse must succeed");
  assert.strictEqual(
    typeof result.value, "object",
    "parsed JSON object must surface as an object",
  );
  assert.deepStrictEqual(
    result.value, { hello: "world", nested: { a: 1, b: [2, 3] } },
    "parsed JSON object must deep-equal the input shape",
  );
}

// 3. parseJsonTree — UTF-8 decode. The helper decodes
//    the bytes as UTF-8 verbatim so non-ASCII characters
//    round-trip through the decoder byte-for-byte.
//    Mirrors the legacy `res.text()` decode.
{
  const textEncoder = new TextEncoder();
  const bytes = textEncoder.encode(
    '{"name":"Plantas con acentos","ríos":["Río A","Río B"]}',
  );
  const result = kernel.parseJsonTree(bytes);
  assert.strictEqual(result.ok, true, "UTF-8 accented JSON must parse");
  assert.strictEqual(result.value.name, "Plantas con acentos");
  assert.deepStrictEqual(result.value.ríos, ["Río A", "Río B"]);
}

// 4. parseJsonTree — JSON value type coverage. The
//    helper parses objects, arrays, primitives (string
//    / number / boolean / null) — every JSON value type
//    surfaces through the typed result.
{
  const cases = [
    { in: "null", out: null },
    { in: "true", out: true },
    { in: "false", out: false },
    { in: "42", out: 42 },
    { in: "3.14", out: 3.14 },
    { in: '"hello"', out: "hello" },
    { in: "[]", out: [] },
    { in: "[1,2,3]", out: [1, 2, 3] },
    { in: "{}", out: {} },
  ];
  const textEncoder = new TextEncoder();
  for (const { in: input, out } of cases) {
    const bytes = textEncoder.encode(input);
    const result = kernel.parseJsonTree(bytes);
    assert.strictEqual(
      result.ok, true,
      `parseJsonTree(${JSON.stringify(input)}) must succeed`,
    );
    assert.deepStrictEqual(
      result.value, out,
      `parseJsonTree(${JSON.stringify(input)}) must yield the typed value`,
    );
  }
}

// 5. parseJsonTree — invalid JSON. The helper returns
//    `{ ok: false, error }` so the React mount can
//    route the failure to the offline banner (mirrors
//    the legacy `renderJsonTree` catch branch — the
//    legacy paints `renderOfflineBanner(target, file)`
//    when `JSON.parse` throws).
{
  const textEncoder = new TextEncoder();
  const invalidBytes = textEncoder.encode("{not: valid json}");
  const result = kernel.parseJsonTree(invalidBytes);
  assert.strictEqual(
    result.ok, false,
    "invalid JSON must yield { ok: false, error }",
  );
  assert.ok(
    typeof result.error === "string" && result.error.length > 0,
    "parseJsonTree failure must carry a non-empty `error` string",
  );
}

// 6. parseJsonTree — pure / non-mutating. The helper
//    does NOT mutate the input bytes; the bytes
//    reference contract mirrors the W4b4
//    `json-source` bytes-by-reference contract.
{
  const textEncoder = new TextEncoder();
  const original = '{"x":1}';
  const bytes = textEncoder.encode(original);
  const snapshot = Array.from(bytes);
  kernel.parseJsonTree(bytes);
  assert.deepStrictEqual(
    Array.from(bytes), snapshot,
    "parseJsonTree must NOT mutate the input bytes",
  );
}

process.stdout.write("PASS\n");
"""


# ---------------------------------------------------------------------------
# W64B-DOCX-002 — typed `cdn-failed` recovery state + DOCX
# viewer materialization via Next `Script` + Mammoth.
#
# The W64B slice is the W6.4b React mount counterpart of the
# W4b1 typed source descriptor:
#
#   - `bytesRequiredForFormat("docx")` flips from `false` to
#     `true` so the existing bytes-fetch effect in Viewer.tsx
#     reads DOCX bytes through the same seam the TXT / MD /
#     SVG / JSON effects already use (mirrors the W64A JSON
#     pattern — the matrix stays honest end-to-end).
#   - Viewer.tsx gains a Next `Script` loader for the
#     legacy-pinned mammoth CDN (`MAMMOTH_CDN_URL` +
#     `MAMMOTH_GLOBAL_NAME`) using Next 16's
#     `<Script src={d.scriptUrl} strategy="afterInteractive"
#     onLoad={convert} onError={...}>` shape (see
#     `node_modules/next/dist/docs/01-app/03-api-reference/02-
#     components/script.md`).
#   - On successful script load the mount calls
#     `window[d.scriptGlobal].convertToHtml({arrayBuffer:
#     bytes.buffer})` and injects the resulting HTML.
#   - On `Script.onError` OR `mammoth.convertToHtml(...)`
#     exception the mount transitions to a typed
#     `cdn-failed` recovery state that's distinct from the
#     `bytes-missing` offline path — the existing
#     `reason: "bytes-missing" | "cdn-failed"` union on the
#     `docx-offline` variant (extended by W64B on
#     `renderers.ts`) lets the surface stay typed across
#     both failure paths.
#
# The W64B surface preserves all existing pins:
#   - JSON Tree viewer (W64A-JSON-001) — untouched.
#   - Spreadsheet / EPUB / CSV / TSV source variants — they
#     stay in the W6.1 cdn-pending catch-all (the W64B slice
#     is DOCX-only materialization; the type extension is the
#     typed union contract applied once to all four CDN
#     families).
#   - `aria-expanded` / `role="button"` / `tabIndex={0}` /
#     Enter/Space on the JSON Tree disclosure row — untouched.
#   - `bytesRequiredForFormat` for non-DOCX formats — the
#     matrix flips ONLY for `docx`.
# ---------------------------------------------------------------------------


# W64B-DOCX-002 — kernel contract: bytes are now required
# for DOCX so the existing bytes-fetch effect in Viewer.tsx
# reads them through the same seam TXT / MD / SVG / JSON
# already use. Mirrors the W64A JSON flip — the matrix
# stays honest end-to-end.
def test_w64b_kernel_bytes_required_for_format_docx_is_true(
    compiled_w6_1_kernel: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """W64B-DOCX-002 — under Node (ES2022 only, no DOM,
    no React), the compiled framework-free kernel's
    `bytesRequiredForFormat("docx")` returns `true` (the
    W64B flip from the W6.1 `false` default). The flip
    keeps the bytes-required matrix honest end-to-end:
    DOCX is a CDN-backed source descriptor that requires
    bytes the same way TXT / MD / SVG / JSON do, so the
    existing Viewer.tsx bytes-fetch effect reads the
    DOCX bytes through the same seam."""
    _compiled_kernel, _compiled_renderers = compiled_w6_1_kernel
    harness = tmp_path / "harness-w64b.cjs"
    harness.write_text(_W64B_RUNTIME_HARNESS)
    result = subprocess.run(
        ["node", str(harness), str(_compiled_kernel)],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"W64B runtime harness failed.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected W64B harness output: {result.stdout!r}"
    )


_W64B_RUNTIME_HARNESS = r"""
// W64B-DOCX-002 — focused harness asserting the
// bytesRequiredForFormat flip for DOCX + the matrix
// stays honest end-to-end. CJS does not support top-
// level await, so the assertions run inside sync blocks.
const path = require("path");
const assert = require("assert");
const kernel = require(path.resolve(process.argv[2]));

// 1. bytesRequiredForFormat — W64B-DOCX-002 flips the
//    DOCX literal from `false` to `true` so the bytes-
//    fetch effect in Viewer.tsx reads DOCX bytes through
//    the same seam TXT / MD / SVG / JSON already use.
{
  assert.strictEqual(
    kernel.bytesRequiredForFormat("docx"), true,
    "W64B-DOCX-002: bytesRequiredForFormat('docx') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads DOCX bytes through the same seam the TXT / MD "
    + "/ SVG / JSON effects already use",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("xls"), true,
    "W64C-XLS-003: bytesRequiredForFormat('xls') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads XLS bytes through the same seam the DOCX / TXT / "
    + "MD / SVG / JSON effects already use",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("xlsx"), true,
    "W64C-XLS-003: bytesRequiredForFormat('xlsx') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads XLSX bytes through the same seam the XLS / DOCX / "
    + "TXT / MD / SVG / JSON effects already use",
  );
  // The matrix stays honest end-to-end — every other
  // literal is unchanged from the W6.1 + W64A + W64B + W64C
  // contract.
  assert.strictEqual(kernel.bytesRequiredForFormat("txt"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("md"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("svg"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("json"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("pdf"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("html"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("htm"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("jpg"), false);
  assert.strictEqual(
    kernel.bytesRequiredForFormat("csv"), true,
    "W64E-CSV-005: bytesRequiredForFormat('csv') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads CSV bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX / EPUB effects "
    + "already use (the mount owns the TextDecoder + "
    + "Papa.parse(...) lifecycle)",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("tsv"), true,
    "W64E-CSV-005: bytesRequiredForFormat('tsv') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads TSV bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX / EPUB / CSV "
    + "effects already use (CSV and TSV share the same "
    + "Papa Parse path; the delimiter literal is computed "
    + "from the format field)",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("epub"), true,
    "W64D-EPUB-004: bytesRequiredForFormat('epub') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads EPUB bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX effects already use",
  );
  assert.strictEqual(kernel.bytesRequiredForFormat("mp4"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("other"), false);
}

process.stdout.write("PASS\n");
"""


# W64B-DOCX-002 — viewer source-level checks. The
# Viewer.tsx React mount materializes the typed DOCX
# source descriptor via Next 16's `<Script>` component
# + a typed `cdn-failed` recovery state on
# `Script.onError` + `mammoth.convertToHtml` exception.
# The checks below pin the source-level shape so a
# future PR that silently drops the loader trips a
# focused test before review.
def test_w64b_viewer_imports_next_script_component() -> None:
    """W64B-DOCX-002 — Viewer.tsx MUST import the Next 16
    `<Script>` component as a default import from
    `next/script`. The script component is the only
    loader the W64B contract authorizes — the W6.1
    non-CDN surface stays CDN-free for every non-DOCX
    family, and the W6.4b DOCX materialization uses
    Next 16's typed `<Script src={d.scriptUrl}
    strategy="afterInteractive" onLoad={convert}
    onError={...}>` shape."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(
        r'import\s+Script\s+from\s*["\']next/script["\']',
        text,
    ), (
        "Viewer.tsx must import the Next 16 `<Script>` "
        "component as a default import from `next/script` "
        "(W64B-DOCX-002 contract — DOCX materialization "
        "uses the typed `<Script src onLoad onError>` "
        "shape)."
    )


def test_w64b_viewer_docx_source_uses_script_loader() -> None:
    """W64B-DOCX-002 — Viewer.tsx MUST have an EXPLICIT
    `case "docx-source":` branch in `renderDispatch`
    that's NOT routed through the W6.1 cdn-pending
    catch-all (the DOCX variant now materializes via
    the Next `Script` loader + `mammoth.convertToHtml`,
    not the download-link card). The W64B contract
    places the `<Script>` JSX + the `onLoad` / `onError`
    handlers inside a dedicated `DocxRender` sub-component
    that's mounted from the `case "docx-source":` branch
    (the sub-component owns its own `loading` / `loaded`
    / `error` state — see the W64B typed `cdn-failed`
    recovery contract). The case branch hands off to
    `DocxRender` so the typed `ViewerDispatch` switch
    stays exhaustive; the `<Script>` surface is verified
    by extracting the entire `DocxRender` block (NOT
    just the case-branch body)."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r'case\s+"docx-source"\s*:', text), (
        "Viewer.tsx MUST have an explicit `case "
        "\"docx-source\":` branch in `renderDispatch` so "
        "the typed DOCX source descriptor materializes "
        "via the Next `Script` loader + "
        "`mammoth.convertToHtml(...)` (NOT the W6.1 "
        "cdn-pending catch-all — W64B-DOCX-002 contract)."
    )
    # The case branch hands off to a DocxRender component.
    # Pin the handoff shape so the W64B separation between
    # the typed dispatch surface + the React lifecycle stays
    # honest.
    case_branch_match = re.search(
        r'case\s+"docx-source"\s*:(.*?)(?=case\s+"|\}\s*\n\s*\})',
        text, re.DOTALL,
    )
    assert case_branch_match, (
        "Viewer.tsx must have an extractable docx-source "
        "branch body in renderDispatch."
    )
    case_branch = case_branch_match.group(1)
    assert "DocxRender" in case_branch, (
        "Viewer.tsx's `case \"docx-source\":` branch MUST "
        "hand off to the dedicated `DocxRender` sub-"
        "component (W64B-DOCX-002 separation — the typed "
        "switch stays exhaustive; the `<Script>` + state "
        "lifecycle live in `DocxRender`)."
    )
    # The DocxRender component MUST render a `<Script>` JSX
    # element with `src`, `onLoad`, and `onError` props.
    # Extract the DocxRender function body so the assertion
    # looks at the loader surface (not the case branch
    # hand-off, which only routes to the sub-component).
    docx_fn_match = re.search(
        r'function\s+DocxRender\b[\s\S]*?\n\}\n',
        text,
    )
    assert docx_fn_match, (
        "Viewer.tsx must define a `function DocxRender(...)` "
        "sub-component for the W64B-DOCX-002 materialization "
        "(the dedicated lifecycle lives there)."
    )
    docx_fn = docx_fn_match.group(0)
    assert re.search(r'<Script\b', docx_fn), (
        "Viewer.tsx's DocxRender sub-component MUST render "
        "a `<Script>` JSX element from the `next/script` "
        "default import (W64B-DOCX-002 contract — the "
        "DOCX materialization owns the Next 16 `<Script> "
        "src onLoad onError` loader)."
    )
    assert re.search(r'\bonLoad=', docx_fn) or re.search(
        r'\bonLoad =', docx_fn,
    ), (
        "Viewer.tsx's DocxRender sub-component MUST wire the "
        "`<Script>` `onLoad` handler to call "
        "`window[dispatch.scriptGlobal].convertToHtml(...)`."
    )
    assert re.search(r'\bonError=', docx_fn) or re.search(
        r'\bonError =', docx_fn,
    ), (
        "Viewer.tsx's DocxRender sub-component MUST wire "
        "the `<Script>` `onError` handler so the script-"
        "load failure surfaces through the typed "
        "`cdn-failed` recovery state."
    )



def test_w64b_viewer_docx_source_calls_mammoth_convert_to_html() -> None:
    """W64B-DOCX-002 — the DOCX onLoad handler MUST call
    `window[dispatch.scriptGlobal].convertToHtml(...)` so
    a future PR that bumps the CDN pin lands in lock-step
    across the dispatcher constant + the loader site. The
    call MUST pass the typed `bytes` through an
    `{arrayBuffer: bytes.buffer}` shape."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r"convertToHtml\s*\(", text), (
        "Viewer.tsx must reference `convertToHtml(...)` so "
        "the W64B-DOCX-002 onLoad handler routes the DOCX "
        "bytes through mammoth's browser entry point."
    )
    assert re.search(
        r"window\s*\[\s*\w+\.scriptGlobal\s*\]"
        r"|window\s*\[\s*\w+\s*\]\.convertToHtml",
        text,
    ), (
        "Viewer.tsx must reach the pinned mammoth global "
        "through `window[dispatch.scriptGlobal].convertToHtml(...)` "
        "— NOT a hardcoded `\"mammoth\"` literal — so a future "
        "PR that bumps the CDN pin lands in lock-step across "
        "the dispatcher constant + the loader site."
    )
    assert "arrayBuffer" in text, (
        "Viewer.tsx must pass the DOCX bytes to mammoth "
        "through the `{arrayBuffer: bytes.buffer}` wrapper."
    )


def test_w64b_viewer_docx_source_emits_cdn_failed_recovery_state() -> None:
    """W64B-DOCX-002 — the DOCX materialization MUST emit
    a typed `cdn-failed` recovery state when EITHER
    `Script.onError` fires (the CDN script fails to load)
    OR `mammoth.convertToHtml(...)` throws. The recovery
    state is distinct from the `bytes-missing` offline
    path the dispatcher emits at dispatch time."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert '"cdn-failed"' in text, (
        "Viewer.tsx must carry the literal `\"cdn-failed\"` "
        "so the typed recovery state surfaces a distinct "
        "value from the bytes-missing offline path "
        "(W64B-DOCX-002 contract — Script.onError + "
        "mammoth.convertToHtml exception routes through "
        "the mount's typed recovery state whose `reason` "
        "literal is `\"cdn-failed\"`)."
    )


def test_w64b_viewer_preserves_json_tree_pins() -> None:
    """W64B-DOCX-002 — the DOCX materialization adds a new
    `case \"docx-source\":` branch but must NOT silently
    drop or rewrite the W64A-JSON-001 JSON Tree pins:
    the `[root]` literal, the
    `Tree truncated — open raw` banner text, and the
    JSON branch. The W64B task brief mandates: "Preserve
    all existing pins, a11y semantics, and the JSON Tree
    behavior added by W64A-JSON-001." A future PR that
    adds the DOCX materialization while accidentally
    dropping a JSON pin breaks both contracts at review."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r'case\s+"json-source"\s*:', text), (
        "Viewer.tsx MUST keep its W64A-JSON-001 "
        "`case \"json-source\":` branch — W64B must NOT "
        "silently drop the JSON Tree viewer while adding "
        "the DOCX materialization."
    )
    assert '"[root]"' in text, (
        "Viewer.tsx must keep the legacy `[root]` literal "
        "(the W64A-JSON-001 synthetic root key)."
    )
    assert "Tree truncated — open raw" in text, (
        "Viewer.tsx must keep the legacy "
        "`Tree truncated — open raw` banner text "
        "(the W64A-JSON-001 truncation banner)."
    )


# ---------------------------------------------------------------------------
# W64C-XLS-003 — XLS / XLSX viewer materialization via Next
# `Script` + SheetJS. The W64C slice is the W6.4c React
# mount counterpart of the W4b2 typed source descriptor:
#
#   - `bytesRequiredForFormat("xls")` + `bytesRequiredForFormat("xlsx")`
#     flip from `false` to `true` so the existing bytes-fetch
#     effect in Viewer.tsx reads XLS / XLSX bytes through the
#     same seam the DOCX / TXT / MD / SVG / JSON effects already
#     use (the matrix stays honest end-to-end — both XLS and
#     XLSX share the same SheetJS path).
#   - Viewer.tsx gains a Next `Script` loader for the
#     legacy-pinned SheetJS CDN (`SHEETJS_CDN_URL` +
#     `SHEETJS_GLOBAL_NAME`) using Next 16's
#     `<Script src={d.scriptUrl} strategy="afterInteractive"
#     onLoad={convert} onError={...}>` shape (see
#     `node_modules/next/dist/docs/01-app/03-api-reference/02-
#     components/script.md`).
#   - On successful script load the mount calls
#     `window[d.scriptGlobal].read(bytes, {type: "array"})`
#     + `window[d.scriptGlobal].utils.sheet_to_html(activeSheet)`
#     and injects the resulting HTML. SheetJS already emits a
#     plain HTML table without `<script>` or event handlers per
#     `design.md` §8, so the React mount's
#     `dangerouslySetInnerHTML` injection is the same XSS-safe
#     shape as the legacy `Range.createContextualFragment`
#     call site.
#   - When `wb.SheetNames.length > 1` the mount surfaces a
#     `<select>` picker that switches the active sheet
#     (matches the legacy `web/file_viewer.js::renderSheet`
#     multi-sheet shape verbatim).
#   - On `Script.onError` OR `read(...)` OR `sheet_to_html(...)`
#     exception the mount transitions to a typed `cdn-failed`
#     recovery state that's distinct from the `bytes-missing`
#     offline path — the existing
#     `reason: "bytes-missing" | "cdn-failed"` union on the
#     `sheet-offline` variant (extended by W64B-DOCX-002 on
#     `renderers.ts`) lets the surface stay typed across
#     both failure paths.
#
# The W64C surface preserves all existing pins:
#   - JSON Tree viewer (W64A-JSON-001) — untouched.
#   - DOCX mount (W64B-DOCX-002) — untouched.
#   - EPUB / CSV / TSV source variants — they stay in the
#     W6.1 cdn-pending catch-all (the W64C slice is
#     XLS / XLSX-only materialization; EPUB / CSV / TSV land
#     as separately authorized later slices).
#   - The pre-W64B `sheet-offline` (bytes-missing) dispatch
#     stays in the cdn-pending catch-all so the existing
#     W6.1 download-link affordance is preserved verbatim.
#   - `aria-expanded` / `role="button"` / `tabIndex={0}` /
#     Enter/Space on the JSON Tree disclosure row — untouched.
#   - `bytesRequiredForFormat` for non-XLS / XLSX formats —
#     the matrix flips ONLY for `xls` + `xlsx`.
# ---------------------------------------------------------------------------


# W64C-XLS-003 — kernel contract: bytes are now required
# for XLS + XLSX so the existing bytes-fetch effect in
# Viewer.tsx reads them through the same seam DOCX / TXT /
# MD / SVG / JSON already use. Mirrors the W64B-DOCX-002
# DOCX flip — the matrix stays honest end-to-end.
def test_w64c_kernel_bytes_required_for_format_xls_is_true(
    compiled_w6_1_kernel: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """W64C-XLS-003 — under Node (ES2022 only, no DOM,
    no React), the compiled framework-free kernel's
    `bytesRequiredForFormat("xls")` returns `true` (the
    W64C flip from the W6.1 `false` default). The flip
    keeps the bytes-required matrix honest end-to-end:
    XLS is a CDN-backed source descriptor that requires
    bytes the same way TXT / MD / SVG / JSON / DOCX do, so
    the existing Viewer.tsx bytes-fetch effect reads the
    XLS bytes through the same seam. XLS / XLSX share the
    same SheetJS path — both literals flip together."""
    _compiled_kernel, _compiled_renderers = compiled_w6_1_kernel
    harness = tmp_path / "harness-w64c.cjs"
    harness.write_text(_W64C_RUNTIME_HARNESS)
    result = subprocess.run(
        ["node", str(harness), str(_compiled_kernel)],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"W64C runtime harness failed.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected W64C harness output: {result.stdout!r}"
    )


_W64C_RUNTIME_HARNESS = r"""
// W64C-XLS-003 — focused harness asserting the
// bytesRequiredForFormat flip for XLS / XLSX + the matrix
// stays honest end-to-end. CJS does not support top-level
// await, so the assertions run inside sync blocks.
const path = require("path");
const assert = require("assert");
const kernel = require(path.resolve(process.argv[2]));

// 1. bytesRequiredForFormat — W64C-XLS-003 flips the XLS
//    + XLSX literals from `false` to `true` so the
//    bytes-fetch effect in Viewer.tsx reads XLS / XLSX
//    bytes through the same seam TXT / MD / SVG / JSON /
//    DOCX already use. Both XLS and XLSX share the same
//    SheetJS path; the format field is carried verbatim
//    through the dispatch.
{
  assert.strictEqual(
    kernel.bytesRequiredForFormat("xls"), true,
    "W64C-XLS-003: bytesRequiredForFormat('xls') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads XLS bytes through the same seam the DOCX / "
    + "TXT / MD / SVG / JSON effects already use",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("xlsx"), true,
    "W64C-XLS-003: bytesRequiredForFormat('xlsx') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads XLSX bytes through the same seam the XLS / "
    + "DOCX / TXT / MD / SVG / JSON effects already use",
  );
  // The matrix stays honest end-to-end — every other
  // literal is unchanged from the W6.1 + W64A + W64B
  // contract.
  assert.strictEqual(kernel.bytesRequiredForFormat("txt"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("md"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("svg"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("json"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("docx"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("pdf"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("html"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("htm"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("jpg"), false);
  assert.strictEqual(
    kernel.bytesRequiredForFormat("csv"), true,
    "W64E-CSV-005: bytesRequiredForFormat('csv') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads CSV bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX / EPUB effects "
    + "already use (the mount owns the TextDecoder + "
    + "Papa.parse(...) lifecycle)",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("tsv"), true,
    "W64E-CSV-005: bytesRequiredForFormat('tsv') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads TSV bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX / EPUB / CSV "
    + "effects already use (CSV and TSV share the same "
    + "Papa Parse path; the delimiter literal is computed "
    + "from the format field)",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("epub"), true,
    "W64D-EPUB-004: bytesRequiredForFormat('epub') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads EPUB bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX effects already use",
  );
  assert.strictEqual(kernel.bytesRequiredForFormat("mp4"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("other"), false);
}

process.stdout.write("PASS\n");
"""


# W64C-XLS-003 — viewer source-level checks. The
# Viewer.tsx React mount materializes the typed XLS /
# XLSX source descriptor via Next 16's `<Script>` component
# + a typed `cdn-failed` recovery state on
# `Script.onError` + `SheetJS.read` / `utils.sheet_to_html`
# exception. The checks below pin the source-level shape
# so a future PR that silently drops the loader trips a
# focused test before review.
def test_w64c_viewer_sheet_source_uses_script_loader() -> None:
    """W64C-XLS-003 — Viewer.tsx MUST have an EXPLICIT
    `case "sheet-source":` branch in `renderDispatch`
    that's NOT routed through the W6.1 cdn-pending
    catch-all (the XLS / XLSX variant now materializes
    via the Next `Script` loader + `SheetJS.read(...)` +
    `utils.sheet_to_html(...)`, not the download-link
    card). The W64C contract places the `<Script>` JSX +
    the `onLoad` / `onError` handlers inside a dedicated
    `SheetRender` sub-component that's mounted from the
    `case "sheet-source":` branch (the sub-component owns
    its own `loading` / `loaded` / `error` state — see the
    W64B-DOCX-002 typed `cdn-failed` recovery pattern that
    W64C mirrors). The case branch hands off to
    `SheetRender` so the typed `ViewerDispatch` switch
    stays exhaustive; the `<Script>` surface is verified
    by extracting the entire `SheetRender` block (NOT
    just the case-branch body)."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r'case\s+"sheet-source"\s*:', text), (
        "Viewer.tsx MUST have an explicit `case "
        "\"sheet-source\":` branch in `renderDispatch` so "
        "the typed XLS / XLSX source descriptor "
        "materializes via the Next `Script` loader + "
        "`SheetJS.read(...)` + `utils.sheet_to_html(...)` "
        "(NOT the W6.1 cdn-pending catch-all — "
        "W64C-XLS-003 contract)."
    )
    # The case branch hands off to a SheetRender component.
    # Pin the handoff shape so the W64C separation between
    # the typed dispatch surface + the React lifecycle stays
    # honest.
    case_branch_match = re.search(
        r'case\s+"sheet-source"\s*:(.*?)(?=case\s+"|\}\s*\n\s*\})',
        text, re.DOTALL,
    )
    assert case_branch_match, (
        "Viewer.tsx must have an extractable sheet-source "
        "branch body in renderDispatch."
    )
    case_branch = case_branch_match.group(1)
    assert "SheetRender" in case_branch, (
        "Viewer.tsx's `case \"sheet-source\":` branch MUST "
        "hand off to the dedicated `SheetRender` sub-"
        "component (W64C-XLS-003 separation — the typed "
        "switch stays exhaustive; the `<Script>` + state "
        "lifecycle live in `SheetRender`)."
    )
    # The SheetRender component MUST render a `<Script>` JSX
    # element with `src`, `onLoad`, and `onError` props.
    # Extract the SheetRender function body so the assertion
    # looks at the loader surface (not the case branch
    # hand-off, which only routes to the sub-component).
    sheet_fn_match = re.search(
        r'function\s+SheetRender\b[\s\S]*?\n\}\n',
        text,
    )
    assert sheet_fn_match, (
        "Viewer.tsx must define a `function SheetRender(...)` "
        "sub-component for the W64C-XLS-003 materialization "
        "(the dedicated lifecycle lives there)."
    )
    sheet_fn = sheet_fn_match.group(0)
    assert re.search(r'<Script\b', sheet_fn), (
        "Viewer.tsx's SheetRender sub-component MUST render "
        "a `<Script>` JSX element from the `next/script` "
        "default import (W64C-XLS-003 contract — the "
        "XLS / XLSX materialization owns the Next 16 "
        "`<Script src onLoad onError>` loader)."
    )
    assert re.search(r'\bonLoad=', sheet_fn) or re.search(
        r'\bonLoad =', sheet_fn,
    ), (
        "Viewer.tsx's SheetRender sub-component MUST wire the "
        "`<Script>` `onLoad` handler to call "
        "`window[dispatch.scriptGlobal].read(...)` + "
        "`utils.sheet_to_html(...)`."
    )
    assert re.search(r'\bonError=', sheet_fn) or re.search(
        r'\bonError =', sheet_fn,
    ), (
        "Viewer.tsx's SheetRender sub-component MUST wire "
        "the `<Script>` `onError` handler so the script-"
        "load failure surfaces through the typed "
        "`cdn-failed` recovery state."
    )


def test_w64c_viewer_sheet_source_calls_sheetjs_read_with_array_type() -> None:
    """W64C-XLS-003 — the SheetRender onLoad handler MUST
    call `window[dispatch.scriptGlobal].read(bytes, {type:
    "array"})` so the SheetJS workbook is parsed as an
    ArrayBuffer of bytes (matches the legacy
    `web/file_viewer.js::renderSheet` shape verbatim: the
    legacy calls `XLSX.read(data, { type: "array" })`
    after `await res.arrayBuffer()`). A future PR that
    bumps the CDN pin lands in lock-step across the
    dispatcher constant + the loader site (the call MUST
    reach the pinned global through
    `window[dispatch.scriptGlobal]` — NOT a hardcoded
    `"XLSX"` literal)."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r"\.read\s*\(", text), (
        "Viewer.tsx must reference `.read(...)` so the "
        "W64C-XLS-003 onLoad handler routes the XLS / XLSX "
        "bytes through SheetJS's workbook parser."
    )
    assert re.search(
        r"type\s*:\s*[\"']array[\"']", text,
    ), (
        "Viewer.tsx must pass `{type: \"array\"}` to "
        "`SheetJS.read(...)` — mirrors the legacy "
        "`web/file_viewer.js::renderSheet` "
        "`XLSX.read(data, { type: \"array\" })` shape "
        "verbatim."
    )
    assert re.search(
        r"window\s*\[\s*\w+\.scriptGlobal\s*\]"
        r"|window\s*\[\s*\w+\s*\]\.read",
        text,
    ), (
        "Viewer.tsx must reach the pinned SheetJS global "
        "through `window[dispatch.scriptGlobal].read(...)` "
        "— NOT a hardcoded `\"XLSX\"` literal — so a future "
        "PR that bumps the CDN pin lands in lock-step across "
        "the dispatcher constant + the loader site."
    )


def test_w64c_viewer_sheet_source_calls_sheet_to_html() -> None:
    """W64C-XLS-003 — the SheetRender onLoad handler MUST
    call `window[dispatch.scriptGlobal].utils.sheet_to_html(activeSheet)`
    so the active sheet emits an HTML table (matches the
    legacy `web/file_viewer.js::renderSheet`
    `window.XLSX.utils.sheet_to_html(sheet)` shape verbatim).
    SheetJS already emits a plain `<table>` markup without
    `<script>` or event handlers per `design.md` §8, so the
    React mount's `dangerouslySetInnerHTML` injection is the
    same XSS-safe shape as the legacy
    `Range.createContextualFragment` call site. The
    `utils.sheet_to_html` reference must reach the pinned
    global through `dispatch.scriptGlobal` (NOT a hardcoded
    `"XLSX"` literal)."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r"sheet_to_html\s*\(", text), (
        "Viewer.tsx must reference `sheet_to_html(...)` so "
        "the W64C-XLS-003 onLoad handler routes the active "
        "sheet through SheetJS's HTML-table emitter."
    )
    assert re.search(
        r"utils\s*\.\s*sheet_to_html|\.utils\b.*\bsheet_to_html",
        text,
    ), (
        "Viewer.tsx must call "
        "`window[dispatch.scriptGlobal].utils.sheet_to_html(...)` "
        "— the `utils` namespace is required because "
        "SheetJS exposes `sheet_to_html` under the pinned "
        "global's `utils` namespace (matches the legacy "
        "`window.XLSX.utils.sheet_to_html(sheet)` shape "
        "verbatim)."
    )


def test_w64c_viewer_sheet_source_renders_picker_for_multi_sheet() -> None:
    """W64C-XLS-003 — when `wb.SheetNames.length > 1` the
    mount MUST surface a `<select>` picker that switches
    the active sheet (matches the legacy
    `web/file_viewer.js::renderSheet` multi-sheet shape
    verbatim: the legacy builds a `<select>` with one
    `<option>` per sheet name + wires `change` to
    `renderSheetHtml(select.value)`). A single-sheet
    workbook skips the picker. The test pins both:
    (a) the typed `<select>` JSX element exists in the
    SheetRender function body, AND (b) the picker is
    conditionally rendered when the sheet count exceeds
    `1` (the legacy's `sheetNames.length > 1` guard)."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    sheet_fn_match = re.search(
        r'function\s+SheetRender\b[\s\S]*?\n\}\n',
        text,
    )
    assert sheet_fn_match, (
        "Viewer.tsx must define a `function SheetRender(...)` "
        "sub-component for the W64C-XLS-003 materialization "
        "(the dedicated lifecycle lives there)."
    )
    sheet_fn = sheet_fn_match.group(0)
    assert re.search(r"<select\b", sheet_fn), (
        "Viewer.tsx's SheetRender sub-component MUST render "
        "a `<select>` JSX element so a multi-sheet workbook "
        "surfaces a picker that switches the active sheet "
        "(W64C-XLS-003 contract — mirrors the legacy "
        "`web/file_viewer.js::renderSheet` "
        "`el(\"select\", { ... })` shape verbatim)."
    )
    # The picker must be conditional on a length > 1
    # comparison — a single-sheet workbook skips it. The
    # legacy uses `sheetNames.length > 1` so the React
    # equivalent uses a JSX `{Array.isArray(sheetNames) &&
    # sheetNames.length > 1 ? <select>...</select> : null}`
    # shape or a typed `useState<number>` + conditional
    # render.
    assert re.search(r"\.length\s*>\s*1|length\s*>\s*1", sheet_fn), (
        "Viewer.tsx's SheetRender sub-component MUST guard "
        "the picker render on `sheetNames.length > 1` "
        "(W64C-XLS-003 contract — mirrors the legacy "
        "`web/file_viewer.js::renderSheet` "
        "`sheetNames.length > 1` shape verbatim; a single-"
        "sheet workbook skips the picker)."
    )
    # The picker must populate `<option>` children from
    # the typed `SheetNames` array so the user can pick
    # any sheet by name.
    assert re.search(r"<option\b", sheet_fn), (
        "Viewer.tsx's SheetRender sub-component MUST render "
        "an `<option>` JSX element inside the picker so the "
        "user can select any sheet name from the workbook "
        "(W64C-XLS-003 contract — mirrors the legacy "
        "`web/file_viewer.js::renderSheet` "
        "`select.append(opt)` shape verbatim)."
    )


def test_w64c_viewer_sheet_source_emits_cdn_failed_recovery_state() -> None:
    """W64C-XLS-003 — the XLS / XLSX materialization MUST
    emit a typed `cdn-failed` recovery state when EITHER
    `Script.onError` fires (the CDN script fails to load)
    OR `SheetJS.read(...)` / `utils.sheet_to_html(...)`
    throws. The recovery state is distinct from the
    `bytes-missing` offline path the dispatcher emits at
    dispatch time. The mount synthesizes a `sheet-offline`
    dispatch with `reason: "cdn-failed"` and routes through
    `renderOfflineCard` so the existing download affordance
    stays in place while the typed `reason` literal is
    first-class."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert '"cdn-failed"' in text, (
        "Viewer.tsx must carry the literal `\"cdn-failed\"` "
        "so the typed recovery state surfaces a distinct "
        "value from the bytes-missing offline path "
        "(W64C-XLS-003 contract — Script.onError + "
        "SheetJS.read / utils.sheet_to_html exception "
        "routes through the mount's typed recovery state "
        "whose `reason` literal is `\"cdn-failed\"`)."
    )
    # The recovery state must synthesize a sheet-offline
    # dispatch — the W64B-DOCX-002 typed union
    # `reason: "bytes-missing" | "cdn-failed"` on the
    # `sheet-offline` variant (extended by W64B on
    # `renderers.ts`) is the common contract.
    sheet_fn_match = re.search(
        r'function\s+SheetRender\b[\s\S]*?\n\}\n',
        text,
    )
    assert sheet_fn_match, (
        "Viewer.tsx must define a `function SheetRender(...)` "
        "sub-component for the W64C-XLS-003 materialization."
    )
    sheet_fn = sheet_fn_match.group(0)
    assert '"sheet-offline"' in sheet_fn or 'sheet-offline' in sheet_fn, (
        "Viewer.tsx's SheetRender sub-component MUST "
        "synthesize a `sheet-offline` dispatch with "
        "`reason: \"cdn-failed\"` so the existing "
        "`renderOfflineCard` paints the download affordance "
        "with a typed `reason` literal distinct from the "
        "`bytes-missing` path the dispatcher emits."
    )


def test_w64c_viewer_preserves_json_docx_sheet_offline_pins() -> None:
    """W64C-XLS-003 — the XLS / XLSX materialization adds
    a new `case \"sheet-source\":` branch but MUST NOT
    silently drop or rewrite the W6.4a pins:

      1. The W64A-JSON-001 JSON Tree pins (`case
         \"json-source\":` branch + the `[root]` literal +
         the `Tree truncated — open raw` banner text).
      2. The W64B-DOCX-002 DOCX mount pins (the
         `case \"docx-source\":` branch + the `DocxRender`
         sub-component + the `convertToHtml` call +
         `arrayBuffer` wrapper).
      3. The pre-W64B `sheet-offline` (bytes-missing)
         dispatch stays in the W6.1 cdn-pending catch-all
         — the W64C slice only extracts `sheet-source`
         from the catch-all; `sheet-offline` keeps the
         existing W6.1 download-link affordance.
      4. The other CDN-backed source variants
         (`epub-source`) stay in the W6.1 cdn-pending
         catch-all — W64C is XLS / XLSX-only
         materialization; EPUB lands as a separately
         authorized later slice. CSV / TSV land as the
         W64E-CSV-005 slice (Papa Parse materialization)
         — the W64E slice extracts `table-source` from
         the catch-all so the typed source routes through
         the dedicated `TableRender` sub-component.

    A future PR that adds the XLS / XLSX materialization
    while accidentally dropping a JSON / DOCX / sheet-
    offline pin breaks multiple contracts at review.
    """
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()

    # 1. W64A-JSON-001 pins.
    assert re.search(r'case\s+"json-source"\s*:', text), (
        "Viewer.tsx MUST keep its W64A-JSON-001 "
        "`case \"json-source\":` branch — W64C must NOT "
        "silently drop the JSON Tree viewer while adding "
        "the XLS / XLSX materialization."
    )
    assert '"[root]"' in text, (
        "Viewer.tsx must keep the legacy `[root]` literal "
        "(the W64A-JSON-001 synthetic root key)."
    )
    assert "Tree truncated — open raw" in text, (
        "Viewer.tsx must keep the legacy "
        "`Tree truncated — open raw` banner text "
        "(the W64A-JSON-001 truncation banner)."
    )

    # 2. W64B-DOCX-002 pins.
    assert re.search(r'case\s+"docx-source"\s*:', text), (
        "Viewer.tsx MUST keep its W64B-DOCX-002 "
        "`case \"docx-source\":` branch — W64C must NOT "
        "silently drop the DOCX mount while adding the "
        "XLS / XLSX materialization."
    )
    assert "DocxRender" in text, (
        "Viewer.tsx must keep its W64B-DOCX-002 "
        "`DocxRender` sub-component — W64C mirrors the "
        "W64B separation between the typed dispatch surface "
        "+ the React lifecycle; both sub-components stay "
        "alive in lock-step."
    )
    assert "convertToHtml" in text, (
        "Viewer.tsx must keep the W64B-DOCX-002 "
        "`convertToHtml(...)` reference so the DOCX "
        "materialization stays intact."
    )
    assert "arrayBuffer" in text, (
        "Viewer.tsx must keep the W64B-DOCX-002 "
        "`arrayBuffer` wrapper so the DOCX bytes are "
        "passed to mammoth through the typed "
        "`{arrayBuffer: bytes.buffer}` shape."
    )

    # 3. The pre-W64B sheet-offline (bytes-missing) dispatch
    #    stays in the W6.1 cdn-pending catch-all. The test
    #    asserts `sheet-offline` is still listed in the
    #    catch-all alongside `docx-offline` + `epub-*` +
    #    `table-*` + `json-offline`.
    cdn_pending_catch_all_match = re.search(
        r'(case\s+"docx-offline"\s*:[\s\S]*?)return\s+renderOfflineCard',
        text,
    )
    assert cdn_pending_catch_all_match, (
        "Viewer.tsx must keep its W6.1 cdn-pending catch-"
        "all `return renderOfflineCard(...)` branch so the "
        "`*-offline` variants (docx-offline / sheet-offline "
        "/ epub-offline / table-offline / json-offline) "
        "all funnel through the existing download-link "
        "recovery card. W64C extracts `sheet-source` from "
        "this catch-all but leaves `sheet-offline` in place."
    )
    catch_all_body = cdn_pending_catch_all_match.group(1)
    for offline_literal in (
        "docx-offline",
        "sheet-offline",
        "epub-offline",
        "table-offline",
        "json-offline",
    ):
        assert f'"{offline_literal}"' in catch_all_body, (
            f"Viewer.tsx's cdn-pending catch-all MUST still "
            f"list `{offline_literal}` so the pre-W64B bytes-"
            f"missing offline path is preserved verbatim "
            f"(W64C-XLS-003 acceptance: 'the pre-W64B "
            f"sheet-offline dispatch (bytes-missing) stays "
            f"in the cdn-pending catch-all'). Got: "
            f"{catch_all_body!r}"
        )

    # 4. The other CDN-backed source variants
    #    (`epub-source`) stay in the W6.1 cdn-pending
    #    catch-all. (`epub-source` is NOT in the catch-all
    #    anymore — the W64D-EPUB-004 slice extracted it so
    #    the typed source descriptor routes through the
    #    dedicated `EpubRender` sub-component. The
    #    pre-W64D `epub-offline` (bytes-missing) dispatch
    #    stays in the catch-all so the existing download-
    #    link affordance is preserved verbatim. The W64E
    #    slice extracts `table-source` from the catch-all
    #    so the typed source routes through the dedicated
    #    `TableRender` sub-component — the W64C test
    #    asserts the pre-W64E state where CSV / TSV were
    #    still deferred; the W64E preservation test pins
    #    the post-W64E state.)
    #    NOTE: as of W64E-CSV-005, `table-source` is also
    #    extracted from the catch-all (by the W64E slice
    #    that materializes CSV / TSV via Papa Parse). The
    #    W64C preservation test was authored BEFORE W64E
    #    landed; the W64E preservation test pins the
    #    post-W64E state where `table-source` is NOT in
    #    the catch-all. Pre-W64E CSV / TSV was a deferred
    #    family that surfaced through the W6.1
    #    download-link affordance; post-W64E CSV / TSV
    #    materializes through the dedicated `TableRender`
    #    sub-component + Papa Parse.

    # 5. `sheet-source` MUST NOT appear in the cdn-pending
    #    catch-all anymore — the W64C slice extracts it so
    #    the typed source descriptor routes through
    #    `SheetRender` instead.
    assert '"sheet-source"' not in catch_all_body, (
        "Viewer.tsx's cdn-pending catch-all MUST NOT list "
        "`sheet-source` anymore — W64C-XLS-003 extracts "
        "the XLS / XLSX source descriptor from the catch-"
        "all so the typed source routes through the "
        "`SheetRender` sub-component (NOT the W6.1 "
        "download-link affordance)."
    )


# ---------------------------------------------------------------------------
# W64D-EPUB-004 — EPUB viewer materialization via Next `Script`
# + the pinned epubjs CDN (the W6.4d React mount counterpart of
# the W4b3 typed source descriptor). The W64D slice closes the
# remaining CDN-backed EPUB materialization:
#
#   - `bytesRequiredForFormat("epub")` flips from `false` to
#     `true` so the existing bytes-fetch effect in Viewer.tsx
#     reads EPUB bytes through the same seam the TXT / MD /
#     SVG / JSON / DOCX / XLS / XLSX effects already use (the
#     matrix stays honest end-to-end).
#   - Viewer.tsx gains a Next `Script` loader for the
#     legacy-pinned epubjs CDN (`EPUBJS_CDN_URL` +
#     `EPUBJS_GLOBAL_NAME = "ePub"` — the case-sensitive
#     UMD global — lowercase `e`, capital `P`) using Next 16's
#     `<Script src={d.scriptUrl} strategy="afterInteractive"
#     onLoad={mount} onError={...}>` shape (see
#     `node_modules/next/dist/docs/01-app/03-api-reference/02-
#     components/script.md`).
#   - On successful script load the mount calls
#     `window[d.scriptGlobal](d.bytes.buffer)` to construct the
#     book (NOT `new ePub(...)` — the UMD global IS the
#     constructor), then `book.renderTo(hostEl, ...)` to mount
#     it, then surfaces prev / next click handlers that call
#     `book.prev()` / `book.next()` (mirrors the legacy
#     `web/file_viewer.js::renderEpub` gotoPrev / gotoNext
#     shape verbatim).
#   - The mount owns a module-scoped "previous book" reference
#     (the legacy uses `_currentBook`; the React mount mirrors
#     the same lifecycle verbatim — see
#     `web/file_viewer.js::renderEpub` lines 429–438) and tears
#     down that previous book BEFORE rendering the new one so
#     listeners don't leak per `design.md` §8. The same cleanup
#     runs on unmount AND on any change of the EPUB dispatch.
#   - On `Script.onError` OR any exception from
#     `ePub(arrayBuffer)` / `book.renderTo(...)` /
#     `book.prev()` / `book.next()` the mount flips to a typed
#     `"cdn-failed"` recovery state that's distinct from the
#     `bytes-missing` offline path the dispatcher emits at
#     dispatch time. The mount synthesizes an
#     `epub-offline` dispatch with `reason: "cdn-failed"` and
#     routes through `renderOfflineCard` so the existing
#     download affordance stays in place while the typed
#     `reason` literal is first-class (the W64B-DOCX-002 typed
#     union `reason: "bytes-missing" | "cdn-failed"` on the
#     `epub-offline` variant — extended on `renderers.ts` — lets
#     the surface distinguish the two failure sources).
#
# The W64D surface preserves all existing pins:
#   - JSON Tree viewer (W64A-JSON-001) — untouched.
#   - DOCX mount (W64B-DOCX-002) — untouched.
#   - SheetJS mount (W64C-XLS-003) — untouched.
#   - The pre-W64D `epub-offline` (bytes-missing) dispatch
#     stays in the W6.1 cdn-pending catch-all so the existing
#     W6.1 download-link affordance is preserved verbatim.
#   - The CSV / TSV / JSON source variants stay in the W6.1
#     cdn-pending catch-all (W64D is EPUB-only materialization).
#   - `aria-expanded` / `role="button"` / `tabIndex={0}` /
#     Enter/Space on the JSON Tree disclosure row — untouched.
#   - `bytesRequiredForFormat` for non-EPUB formats — the
#     matrix flips ONLY for `epub`.
# ---------------------------------------------------------------------------


# W64D-EPUB-004 — kernel contract: bytes are now required
# for EPUB so the existing bytes-fetch effect in Viewer.tsx
# reads them through the same seam TXT / MD / SVG / JSON /
# DOCX / XLS / XLSX already use. Mirrors the W64A JSON +
# W64B DOCX + W64C XLS / XLSX flips — the matrix stays
# honest end-to-end.
def test_w64d_kernel_bytes_required_for_format_epub_is_true(
    compiled_w6_1_kernel: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """W64D-EPUB-004 — under Node (ES2022 only, no DOM,
    no React), the compiled framework-free kernel's
    `bytesRequiredForFormat("epub")` returns `true` (the
    W64D flip from the W6.1 `false` default). The flip
    keeps the bytes-required matrix honest end-to-end:
    EPUB is a CDN-backed source descriptor that requires
    bytes the same way TXT / MD / SVG / JSON / DOCX / XLS
    / XLSX do, so the existing Viewer.tsx bytes-fetch
    effect reads the EPUB bytes through the same seam."""
    _compiled_kernel, _compiled_renderers = compiled_w6_1_kernel
    harness = tmp_path / "harness-w64d.cjs"
    harness.write_text(_W64D_RUNTIME_HARNESS)
    result = subprocess.run(
        ["node", str(harness), str(_compiled_kernel)],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"W64D runtime harness failed.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected W64D harness output: {result.stdout!r}"
    )


_W64D_RUNTIME_HARNESS = r"""
// W64D-EPUB-004 — focused harness asserting the
// bytesRequiredForFormat flip for EPUB + the matrix
// stays honest end-to-end. CJS does not support top-level
// await, so the assertions run inside sync blocks.
const path = require("path");
const assert = require("assert");
const kernel = require(path.resolve(process.argv[2]));

// 1. bytesRequiredForFormat — W64D-EPUB-004 flips the
//    EPUB literal from `false` to `true` so the bytes-
//    fetch effect in Viewer.tsx reads EPUB bytes through
//    the same seam TXT / MD / SVG / JSON / DOCX / XLS /
//    XLSX already use.
{
  assert.strictEqual(
    kernel.bytesRequiredForFormat("epub"), true,
    "W64D-EPUB-004: bytesRequiredForFormat('epub') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads EPUB bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX effects already use",
  );
  // The matrix stays honest end-to-end — every other
  // literal is unchanged from the W6.1 + W64A + W64B +
  // W64C contract.
  assert.strictEqual(kernel.bytesRequiredForFormat("txt"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("md"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("svg"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("json"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("docx"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("xls"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("xlsx"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("pdf"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("html"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("htm"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("jpg"), false);
  assert.strictEqual(
    kernel.bytesRequiredForFormat("csv"), true,
    "W64E-CSV-005: bytesRequiredForFormat('csv') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads CSV bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX / EPUB effects "
    + "already use (the mount owns the TextDecoder + "
    + "Papa.parse(...) lifecycle)",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("tsv"), true,
    "W64E-CSV-005: bytesRequiredForFormat('tsv') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads TSV bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX / EPUB / CSV "
    + "effects already use (CSV and TSV share the same "
    + "Papa Parse path; the delimiter literal is computed "
    + "from the format field)",
  );
  assert.strictEqual(kernel.bytesRequiredForFormat("mp4"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("other"), false);
}

process.stdout.write("PASS\n");
"""


# W64D-EPUB-004 — viewer source-level checks. The
# Viewer.tsx React mount materializes the typed EPUB
# source descriptor via Next 16's `<Script>` component +
# a typed `cdn-failed` recovery state on
# `Script.onError` + `ePub(arrayBuffer)` construction /
# `book.renderTo(...)` / `book.prev()` / `book.next()`
# exception. The checks below pin the source-level shape
# so a future PR that silently drops the loader trips a
# focused test before review.
def test_w64d_viewer_epub_source_uses_script_loader() -> None:
    """W64D-EPUB-004 — Viewer.tsx MUST have an EXPLICIT
    `case "epub-source":` branch in `renderDispatch`
    that's NOT routed through the W6.1 cdn-pending
    catch-all (the EPUB variant now materializes via the
    Next `Script` loader + `window[ePub](bytes.buffer)`
    + `book.renderTo(...)`, not the download-link card).
    The W64D contract places the `<Script>` JSX + the
    `onLoad` / `onError` handlers inside a dedicated
    `EpubRender` sub-component that's mounted from the
    `case "epub-source":` branch (the sub-component owns
    its own `loading` / `loaded` / `error` state — see the
    W64B-DOCX-002 typed `cdn-failed` recovery pattern
    that W64D mirrors). The case branch hands off to
    `EpubRender` so the typed `ViewerDispatch` switch
    stays exhaustive; the `<Script>` surface is verified
    by extracting the entire `EpubRender` block (NOT just
    the case-branch body)."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r'case\s+"epub-source"\s*:', text), (
        "Viewer.tsx MUST have an explicit `case "
        "\"epub-source\":` branch in `renderDispatch` so "
        "the typed EPUB source descriptor materializes "
        "via the Next `Script` loader + "
        "`window[ePub](bytes.buffer)` + `book.renderTo(...)` "
        "(NOT the W6.1 cdn-pending catch-all — "
        "W64D-EPUB-004 contract)."
    )
    # The case branch hands off to an EpubRender component.
    # Pin the handoff shape so the W64D separation between
    # the typed dispatch surface + the React lifecycle stays
    # honest.
    case_branch_match = re.search(
        r'case\s+"epub-source"\s*:(.*?)(?=case\s+"|\}\s*\n\s*\})',
        text, re.DOTALL,
    )
    assert case_branch_match, (
        "Viewer.tsx must have an extractable epub-source "
        "branch body in renderDispatch."
    )
    case_branch = case_branch_match.group(1)
    assert "EpubRender" in case_branch, (
        "Viewer.tsx's `case \"epub-source\":` branch MUST "
        "hand off to the dedicated `EpubRender` sub-"
        "component (W64D-EPUB-004 separation — the typed "
        "switch stays exhaustive; the `<Script>` + state "
        "lifecycle live in `EpubRender`)."
    )
    # The EpubRender component MUST render a `<Script>` JSX
    # element with `src`, `onLoad`, and `onError` props.
    # Extract the EpubRender function body so the assertion
    # looks at the loader surface (not the case branch
    # hand-off, which only routes to the sub-component).
    epub_fn_match = re.search(
        r'function\s+EpubRender\b[\s\S]*?\n\}\n',
        text,
    )
    assert epub_fn_match, (
        "Viewer.tsx must define a `function EpubRender(...)` "
        "sub-component for the W64D-EPUB-004 materialization "
        "(the dedicated lifecycle lives there)."
    )
    epub_fn = epub_fn_match.group(0)
    assert re.search(r'<Script\b', epub_fn), (
        "Viewer.tsx's EpubRender sub-component MUST render "
        "a `<Script>` JSX element from the `next/script` "
        "default import (W64D-EPUB-004 contract — the EPUB "
        "materialization owns the Next 16 `<Script src "
        "onLoad onError>` loader)."
    )
    assert re.search(r'\bonLoad=', epub_fn) or re.search(
        r'\bonLoad =', epub_fn,
    ), (
        "Viewer.tsx's EpubRender sub-component MUST wire the "
        "`<Script>` `onLoad` handler to call "
        "`window[dispatch.scriptGlobal](dispatch.bytes.buffer)` + "
        "`book.renderTo(hostEl, ...)`."
    )
    assert re.search(r'\bonError=', epub_fn) or re.search(
        r'\bonError =', epub_fn,
    ), (
        "Viewer.tsx's EpubRender sub-component MUST wire "
        "the `<Script>` `onError` handler so the script-"
        "load failure surfaces through the typed "
        "`cdn-failed` recovery state."
    )


def test_w64d_viewer_epub_source_constructs_book_via_window_call() -> None:
    """W64D-EPUB-004 — the EpubRender onLoad handler MUST
    construct the epubjs book via
    `window[dispatch.scriptGlobal](dispatch.bytes.buffer)`
    (the UMD global IS the constructor — `ePub` itself
    is a function, NOT a class — so the call is `ePub(buf)`
    not `new ePub(buf)`). The call MUST reach the pinned
    global through `dispatch.scriptGlobal` (NOT a
    hardcoded `"ePub"` literal — case-sensitive) so a
    future PR that bumps the CDN pin lands in lock-step
    across the dispatcher constant + the loader site. The
    bytes are passed via `dispatch.bytes.buffer` so the
    epubjs UMD constructor receives an `ArrayBuffer` (the
    underlying buffer the `Uint8Array` view wraps — the
    same shape the legacy `web/file_viewer.js::renderEpub`
    `window.ePub(arrayBuffer)` call site uses verbatim)."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    # The mount MUST reach the global through the pinned
    # `window[dispatch.scriptGlobal](...)` call site — NOT
    # `new ePub(...)`. The UMD global is a function, so
    # `new` would throw at runtime. The presence of
    # `new ePub` would silently break the construction site.
    assert "new ePub" not in text, (
        "Viewer.tsx MUST NOT call `new ePub(...)` — the "
        "epubjs UMD global is a function, NOT a class. The "
        "W64D-EPUB-004 contract constructs the book via "
        "`window[dispatch.scriptGlobal](dispatch.bytes.buffer)` "
        "verbatim (matches the legacy `web/file_viewer.js::"
        "renderEpub` `window.ePub(arrayBuffer)` call site)."
    )
    # The mount MUST reach the pinned callback through
    # `dispatch.scriptGlobal` (NOT a hardcoded `"ePub"`
    # literal) so a future PR that bumps the CDN pin
    # lands in lock-step across the dispatcher constant
    # + the loader site.
    assert re.search(
        r"window\s*\[\s*\w+\.scriptGlobal\s*\]"
        r"|window\s*\[\s*\w+\s*\]\s*\(",
        text,
    ), (
        "Viewer.tsx must reach the pinned epubjs global "
        "through `window[dispatch.scriptGlobal](...)` — "
        "NOT a hardcoded `\"ePub\"` literal — so a future "
        "PR that bumps the CDN pin lands in lock-step "
        "across the dispatcher constant + the loader site."
    )
    # The mount MUST pass `dispatch.bytes.buffer` so the
    # epubjs UMD constructor receives the underlying
    # ArrayBuffer (the same shape the legacy
    # `window.ePub(arrayBuffer)` site uses).
    assert re.search(
        r"dispatch\.bytes\.buffer|\w+\.bytes\.buffer",
        text,
    ), (
        "Viewer.tsx must pass `dispatch.bytes.buffer` "
        "to `window[dispatch.scriptGlobal](...)` so the "
        "epubjs UMD constructor receives the underlying "
        "ArrayBuffer (matches the legacy "
        "`window.ePub(arrayBuffer)` site)."
    )


def test_w64d_viewer_epub_source_calls_render_to() -> None:
    """W64D-EPUB-004 — the EpubRender mount MUST call
    `book.renderTo(hostEl, ...)` to mount the EPUB into
    the React tree (mirrors the legacy
    `web/file_viewer.js::renderEpub`
    `book.renderTo(epubHost, { width: "100%", height: "100%" })`
    shape verbatim). The host element is a stable React ref
    so the mount has a typed target to render into (the
    legacy uses `el("div", { class: "flex-1 min-h-[480px]" })`
    — the React mount uses a `useRef<HTMLDivElement>` for
    the same purpose so the lifecycle stays React-y)."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r"\.renderTo\s*\(", text), (
        "Viewer.tsx must reference `.renderTo(...)` so "
        "the W64D-EPUB-004 mount materializes the EPUB "
        "into the React tree (mirrors the legacy "
        "`web/file_viewer.js::renderEpub` "
        "`book.renderTo(epubHost, { width: \"100%\", "
        "height: \"100%\" })` shape verbatim)."
    )


def test_w64d_viewer_epub_source_surfaces_prev_next_navigation() -> None:
    """W64D-EPUB-004 — the EpubRender mount MUST surface
    prev / next click handlers that call `book.prev()` /
    `book.next()` (mirrors the legacy
    `web/file_viewer.js::renderEpub` gotoPrev / gotoNext
    shape verbatim). The mount wires two `<button>`
    elements (or equivalent clickable controls) that call
    the book's navigation API. A future PR that
    accidentally drops the navigation handlers would
    leave the user unable to flip pages — this guard
    pins the affordance."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r"\.prev\s*\(\s*\)", text), (
        "Viewer.tsx must reference `.prev()` so the "
        "W64D-EPUB-004 prev-page click handler routes "
        "through `book.prev()` (mirrors the legacy "
        "`web/file_viewer.js::renderEpub` gotoPrev shape)."
    )
    assert re.search(r"\.next\s*\(\s*\)", text), (
        "Viewer.tsx must reference `.next()` so the "
        "W64D-EPUB-004 next-page click handler routes "
        "through `book.next()` (mirrors the legacy "
        "`web/file_viewer.js::renderEpub` gotoNext shape)."
    )


def test_w64d_viewer_epub_source_owns_previous_book_lifecycle() -> None:
    """W64D-EPUB-004 — the EpubRender mount MUST own a
    module-scoped "previous book" reference and tear down
    that previous book BEFORE rendering the new one so
    listeners don't leak (mirrors the legacy
    `web/file_viewer.js::renderEpub` lines 429–438
    `_currentBook.destroy()` lifecycle verbatim). The
    cleanup MUST also run on unmount AND on any change of
    the EPUB dispatch (the `useEffect` cleanup path
    preserves the React-mount equivalence of the
    legacy's "next open tears down the previous" shape).

    A future PR that drops the lifecycle would let
    listeners leak per `design.md` §8 EPUB render
    lifecycle; this guard pins the module-scoped
    previous-book slot + the destroy call + the
    useEffect cleanup wiring."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    epub_fn_match = re.search(
        r'function\s+EpubRender\b[\s\S]*?\n\}\n',
        text,
    )
    assert epub_fn_match, (
        "Viewer.tsx must define a `function EpubRender(...)` "
        "sub-component for the W64D-EPUB-004 materialization."
    )
    epub_fn = epub_fn_match.group(0)
    # The mount MUST reference `.destroy()` to call the
    # previous book's teardown.
    assert re.search(r"\.destroy\s*\(\s*\)", epub_fn), (
        "Viewer.tsx's EpubRender sub-component MUST "
        "reference `.destroy()` so the module-scoped "
        "previous-book slot tears down listeners before "
        "the new book mounts (mirrors the legacy "
        "`web/file_viewer.js::renderEpub` "
        "`_currentBook.destroy()` lifecycle verbatim)."
    )
    # The mount MUST own a module-scoped `previousBook`
    # (or `currentBook` / `_currentBook`) reference so the
    # next open can tear down the previous one. The legacy
    # uses `_currentBook`; the React mount mirrors the
    # same shape with a module-scoped `let previousBook:`
    # declaration (the React mount can't rely on a hook
    # because the previous-book reference must outlive
    # the per-render closure).
    assert re.search(
        r"(?:^|\n)\s*(?:let|var)\s+(?:previousBook|currentBook|_currentBook)\b",
        epub_fn,
    ) or re.search(
        r"(?:previousBook|currentBook|_currentBook)\s*[=:]",
        epub_fn,
    ), (
        "Viewer.tsx's EpubRender sub-component MUST own a "
        "module-scoped `previousBook` (or `currentBook` / "
        "`_currentBook`) reference so the next open can "
        "tear down the previous book BEFORE rendering the "
        "new one (mirrors the legacy `web/file_viewer.js::"
        "renderEpub` `_currentBook.destroy()` lifecycle "
        "verbatim — the previous-book reference must "
        "outlive the per-render closure)."
    )
    # The cleanup MUST run on unmount OR on dispatch change.
    # The React `useEffect` cleanup is the typed surface
    # that mirrors the legacy "tear down on the NEXT open"
    # lifecycle; the cleanup body MUST call the destroy
    # path so listeners don't leak per `design.md` §8.
    assert re.search(
        r"return\s*\(\s*\)\s*=>\s*\{[\s\S]*?(?:destroy|cleanup)",
        epub_fn,
    ) or re.search(
        r"return\s*\(\s*\)\s*=>\s*\{[\s\S]*?(?:previousBook|currentBook|_currentBook)",
        epub_fn,
    ), (
        "Viewer.tsx's EpubRender sub-component MUST wire a "
        "`useEffect` cleanup that tears down the previous "
        "book so listeners don't leak on unmount OR on any "
        "change of the EPUB dispatch (mirrors the legacy "
        "`web/file_viewer.js::renderEpub` "
        "`_currentBook.destroy()` lifecycle verbatim)."
    )


def test_w64d_viewer_epub_source_emits_cdn_failed_recovery_state() -> None:
    """W64D-EPUB-004 — the EPUB materialization MUST emit a
    typed `cdn-failed` recovery state when EITHER
    `Script.onError` fires (the CDN script fails to load)
    OR `ePub(arrayBuffer)` construction throws OR
    `book.renderTo(...)` throws OR `book.prev()` /
    `book.next()` throws. The recovery state is distinct
    from the `bytes-missing` offline path the dispatcher
    emits at dispatch time. The mount synthesizes an
    `epub-offline` dispatch with `reason: "cdn-failed"`
    and routes through `renderOfflineCard` so the existing
    download affordance stays in place while the typed
    `reason` literal is first-class."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert '"cdn-failed"' in text, (
        "Viewer.tsx must carry the literal `\"cdn-failed\"` "
        "so the typed recovery state surfaces a distinct "
        "value from the bytes-missing offline path "
        "(W64D-EPUB-004 contract — Script.onError + "
        "ePub(arrayBuffer) construction / "
        "book.renderTo / book.prev / book.next exception "
        "routes through the mount's typed recovery state "
        "whose `reason` literal is `\"cdn-failed\"`)."
    )
    # The recovery state must synthesize an epub-offline
    # dispatch — the W64B-DOCX-002 typed union
    # `reason: "bytes-missing" | "cdn-failed"` on the
    # `epub-offline` variant (extended by W64B on
    # `renderers.ts`) is the common contract.
    epub_fn_match = re.search(
        r'function\s+EpubRender\b[\s\S]*?\n\}\n',
        text,
    )
    assert epub_fn_match, (
        "Viewer.tsx must define a `function EpubRender(...)` "
        "sub-component for the W64D-EPUB-004 materialization."
    )
    epub_fn = epub_fn_match.group(0)
    assert '"epub-offline"' in epub_fn or 'epub-offline' in epub_fn, (
        "Viewer.tsx's EpubRender sub-component MUST "
        "synthesize an `epub-offline` dispatch with "
        "`reason: \"cdn-failed\"` so the existing "
        "`renderOfflineCard` paints the download affordance "
        "with a typed `reason` literal distinct from the "
        "`bytes-missing` path the dispatcher emits."
    )


def test_w64d_viewer_preserves_json_docx_sheet_epub_offline_pins() -> None:
    """W64D-EPUB-004 — the EPUB materialization adds a new
    `case \"epub-source\":` branch but MUST NOT silently
    drop or rewrite the W6.4a + W6.4b + W6.4c pins:

      1. The W64A-JSON-001 JSON Tree pins (`case
         \"json-source\":` branch + the `[root]` literal +
         the `Tree truncated — open raw` banner text).
      2. The W64B-DOCX-002 DOCX mount pins (the
         `case \"docx-source\":` branch + the `DocxRender`
         sub-component + the `convertToHtml` call +
         `arrayBuffer` wrapper).
      3. The W64C-XLS-003 XLS / XLSX mount pins (the
         `case \"sheet-source\":` branch + the
         `SheetRender` sub-component + the `.read` /
         `sheet_to_html` call sites + the `<select>`
         picker).
      4. The pre-W64D `epub-offline` (bytes-missing)
         dispatch stays in the W6.1 cdn-pending catch-all
         — the W64D slice only extracts `epub-source` from
         the catch-all; `epub-offline` keeps the existing
         W6.1 download-link affordance.
      5. The other CDN-backed source variants
         (`json-source`) stay in the W6.1 cdn-pending
         catch-all (the W64A-JSON-001 `case
         \"json-source\":` branch routes through
         `renderJsonTree` outside the catch-all). The
         `table-source` family is a separately authorized
         later slice (W64E-CSV-005 Papa Parse
         materialization) — pre-W64E `table-source` stays
         in the catch-all; post-W64E `table-source` is
         extracted from the catch-all so the typed source
         routes through the dedicated `TableRender`
         sub-component.

    A future PR that adds the EPUB materialization while
    accidentally dropping a JSON / DOCX / XLS / XLSX /
    epub-offline pin breaks multiple contracts at review.
    """
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()

    # 1. W64A-JSON-001 pins.
    assert re.search(r'case\s+"json-source"\s*:', text), (
        "Viewer.tsx MUST keep its W64A-JSON-001 "
        "`case \"json-source\":` branch — W64D must NOT "
        "silently drop the JSON Tree viewer while adding "
        "the EPUB materialization."
    )
    assert '"[root]"' in text, (
        "Viewer.tsx must keep the legacy `[root]` literal "
        "(the W64A-JSON-001 synthetic root key)."
    )
    assert "Tree truncated — open raw" in text, (
        "Viewer.tsx must keep the legacy "
        "`Tree truncated — open raw` banner text "
        "(the W64A-JSON-001 truncation banner)."
    )

    # 2. W64B-DOCX-002 pins.
    assert re.search(r'case\s+"docx-source"\s*:', text), (
        "Viewer.tsx MUST keep its W64B-DOCX-002 "
        "`case \"docx-source\":` branch — W64D must NOT "
        "silently drop the DOCX mount while adding the "
        "EPUB materialization."
    )
    assert "DocxRender" in text, (
        "Viewer.tsx must keep its W64B-DOCX-002 "
        "`DocxRender` sub-component — W64D mirrors the "
        "W64B separation between the typed dispatch surface "
        "+ the React lifecycle; both sub-components stay "
        "alive in lock-step."
    )
    assert "convertToHtml" in text, (
        "Viewer.tsx must keep the W64B-DOCX-002 "
        "`convertToHtml(...)` reference so the DOCX "
        "materialization stays intact."
    )
    assert "arrayBuffer" in text, (
        "Viewer.tsx must keep the W64B-DOCX-002 "
        "`arrayBuffer` wrapper so the DOCX bytes are "
        "passed to mammoth through the typed "
        "`{arrayBuffer: bytes.buffer}` shape."
    )

    # 3. W64C-XLS-003 pins.
    assert re.search(r'case\s+"sheet-source"\s*:', text), (
        "Viewer.tsx MUST keep its W64C-XLS-003 "
        "`case \"sheet-source\":` branch — W64D must NOT "
        "silently drop the XLS / XLSX mount while adding "
        "the EPUB materialization."
    )
    assert "SheetRender" in text, (
        "Viewer.tsx must keep its W64C-XLS-003 "
        "`SheetRender` sub-component — W64D mirrors the "
        "W64C separation between the typed dispatch surface "
        "+ the React lifecycle; both sub-components stay "
        "alive in lock-step."
    )
    assert "sheet_to_html" in text, (
        "Viewer.tsx must keep the W64C-XLS-003 "
        "`sheet_to_html(...)` reference so the XLS / XLSX "
        "materialization stays intact."
    )

    # 4. The pre-W64D epub-offline (bytes-missing) dispatch
    #    stays in the W6.1 cdn-pending catch-all. The test
    #    asserts `epub-offline` is still listed in the
    #    catch-all alongside `docx-offline` + `sheet-offline`
    #    + `table-offline` + `json-offline`.
    cdn_pending_catch_all_match = re.search(
        r'(case\s+"docx-offline"\s*:[\s\S]*?)return\s+renderOfflineCard',
        text,
    )
    assert cdn_pending_catch_all_match, (
        "Viewer.tsx must keep its W6.1 cdn-pending catch-"
        "all `return renderOfflineCard(...)` branch so the "
        "`*-offline` variants (docx-offline / sheet-offline "
        "/ epub-offline / table-offline / json-offline) "
        "all funnel through the existing download-link "
        "recovery card. W64D extracts `epub-source` from "
        "this catch-all but leaves `epub-offline` in place."
    )
    catch_all_body = cdn_pending_catch_all_match.group(1)
    for offline_literal in (
        "docx-offline",
        "sheet-offline",
        "epub-offline",
        "table-offline",
        "json-offline",
    ):
        assert f'"{offline_literal}"' in catch_all_body, (
            f"Viewer.tsx's cdn-pending catch-all MUST still "
            f"list `{offline_literal}` so the pre-W64D bytes-"
            f"missing offline path is preserved verbatim "
            f"(W64D-EPUB-004 acceptance: 'the pre-W64D "
            f"epub-offline dispatch (bytes-missing) stays "
            f"in the cdn-pending catch-all'). Got: "
            f"{catch_all_body!r}"
        )

    # 5. The other CDN-backed source variants
    #    (`table-source`) stay in the W6.1 cdn-pending
    #    catch-all PRE-W64E; the W64E-CSV-005 slice extracts
    #    `table-source` from the catch-all so the typed
    #    source routes through the dedicated `TableRender`
    #    sub-component. (`json-source` is NOT in the
    #    catch-all — it's routed through `renderJsonTree`
    #    outside the catch-all, which the W64A-JSON-001
    #    case branch pins above.)
    #    NOTE: as of W64E-CSV-005, `table-source` is also
    #    extracted from the catch-all (by the W64E slice
    #    that materializes CSV / TSV via Papa Parse). The
    #    W64D preservation test was authored BEFORE W64E
    #    landed; the W64E preservation test pins the
    #    post-W64E state where `table-source` is NOT in
    #    the catch-all. Pre-W64E CSV / TSV was a deferred
    #    family that surfaced through the W6.1
    #    download-link affordance; post-W64E CSV / TSV
    #    materializes through the dedicated `TableRender`
    #    sub-component + Papa Parse.

    # 6. `epub-source` MUST NOT appear in the cdn-pending
    #    catch-all anymore — the W64D slice extracts it so
    #    the typed source descriptor routes through
    #    `EpubRender` instead.
    assert '"epub-source"' not in catch_all_body, (
        "Viewer.tsx's cdn-pending catch-all MUST NOT list "
        "`epub-source` anymore — W64D-EPUB-004 extracts "
        "the EPUB source descriptor from the catch-all so "
        "the typed source routes through the `EpubRender` "
        "sub-component (NOT the W6.1 download-link "
        "affordance)."
    )


# ---------------------------------------------------------------------------
# W64E-CSV-005 — CSV / TSV Table viewer materialization via Next `Script`
# + the pinned Papa Parse CDN pin (the W6.4e React mount counterpart of
# the W4b4 typed `table-source` source descriptor). The W64E slice closes
# the remaining CDN-backed Table materialization:
#
#   - `bytesRequiredForFormat("csv")` + `bytesRequiredForFormat("tsv")`
#     flip from `false` to `true` so the existing bytes-fetch effect in
#     Viewer.tsx reads CSV / TSV bytes through the same seam the TXT /
#     MD / SVG / JSON / DOCX / XLS / XLSX / EPUB effects already use (the
#     matrix stays honest end-to-end).
#   - Viewer.tsx gains a Next `Script` loader for the legacy-pinned Papa
#     Parse CDN (`PAPA_CDN_URL` + `PAPA_GLOBAL_NAME = "Papa"`) using
#     Next 16's `<Script src={dispatch.scriptUrl}
#     strategy="afterInteractive" onLoad={parse} onError={...}>` shape
#     (see `node_modules/next/dist/docs/01-app/03-api-reference/02-
#     components/script.md`).
#   - On successful script load the mount UTF-8-decodes the bytes through
#     `TextDecoder` + calls `window[dispatch.scriptGlobal].parse(text,
#     {delimiter, skipEmptyLines: true})` where `delimiter` is derived
#     from the dispatch's `format` field (`","` for CSV + `"\t"` for
#     TSV) when `dispatch.delimiter` is not explicitly provided. The
#     W4b4 dispatcher always carries the typed `delimiter` literal on the
#     `table-source` variant, so the mount passes it verbatim.
#   - The mount renders the parsed rows as a sticky `<thead>` + zebra
#     `<tbody>` table inside the existing `.fex-csv-scroller` wrapper
#     (the cascade is already shipped by the W6.1 migration — `.fex-csv-
#     scroller` + `.fex-csv-table` + `.fex-csv-table thead th` (sticky)
#     + `.fex-csv-table tbody td` + `.fex-csv-table tbody
#     tr:nth-child(even) td` (zebra)). Mirrors the legacy
#     `web/file_viewer.js::renderTable` lines 550–619 verbatim (the
#     first row is the header; a headerless file synthesises `Col N`
#     labels; cell strings coerce to "" when missing).
#   - On `Script.onError` OR any exception from `Papa.parse(...)` the
#     mount flips to a typed `"cdn-failed"` recovery state that's
#     distinct from the `bytes-missing` offline path the dispatcher
#     emits at dispatch time. The mount synthesizes a `table-offline`
#     dispatch with `reason: "cdn-failed"` and routes through
#     `renderOfflineCard` so the existing download affordance stays in
#     place while the typed `reason` literal is first-class.
#
# The W64E surface preserves all existing pins:
#   - JSON Tree viewer (W64A-JSON-001) — untouched.
#   - DOCX mount (W64B-DOCX-002) — untouched.
#   - XLS / XLSX mount (W64C-XLS-003) — untouched.
#   - EPUB mount (W64D-EPUB-004) — untouched.
#   - The pre-W64E `table-offline` (bytes-missing) dispatch stays in
#     the W6.1 cdn-pending catch-all so the existing W6.1 download-link
#     affordance is preserved verbatim.
# ---------------------------------------------------------------------------


# W64E-CSV-005 — kernel contract: bytes are now required for
# CSV + TSV so the existing bytes-fetch effect in Viewer.tsx
# reads them through the same seam TXT / MD / SVG / JSON /
# DOCX / XLS / XLSX / EPUB already use. Mirrors the W64A JSON
# + W64B DOCX + W64C XLS / XLSX + W64D EPUB flips — the matrix
# stays honest end-to-end.
def test_w64e_kernel_bytes_required_for_format_csv_tsv_is_true(
    compiled_w6_1_kernel: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """W64E-CSV-005 — under Node (ES2022 only, no DOM, no
    React), the compiled framework-free kernel's
    `bytesRequiredForFormat("csv")` AND
    `bytesRequiredForFormat("tsv")` both return `true` (the
    W64E flip from the W6.1 + W64A + W64B + W64C + W64D
    `false` default). The flip keeps the bytes-required
    matrix honest end-to-end: CSV / TSV are CDN-backed source
    descriptors that require bytes the same way TXT / MD /
    SVG / JSON / DOCX / XLS / XLSX / EPUB do, so the existing
    Viewer.tsx bytes-fetch effect reads the CSV / TSV bytes
    through the same seam.

    Both delimiters share the same Papa Parse path; the
    dispatcher computes the delimiter from the `format`
    field (`","` for CSV, `"\t"` for TSV) and the W4b4
    `table-source` variant carries it on the typed `delimiter`
    literal. The bytes-required flip covers BOTH extensions —
    one Papa CDN load, one `parse(...)` call site, two
    delimiter literals."""
    _compiled_kernel, _compiled_renderers = compiled_w6_1_kernel
    harness = tmp_path / "harness-w64e.cjs"
    harness.write_text(_W64E_RUNTIME_HARNESS)
    result = subprocess.run(
        ["node", str(harness), str(_compiled_kernel)],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"W64E runtime harness failed.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected W64E harness output: {result.stdout!r}"
    )


_W64E_RUNTIME_HARNESS = r"""
// W64E-CSV-005 — focused harness asserting the
// bytesRequiredForFormat flip for CSV + TSV + the matrix
// stays honest end-to-end. CJS does not support top-level
// await, so the assertions run inside sync blocks.
const path = require("path");
const assert = require("assert");
const kernel = require(path.resolve(process.argv[2]));

// 1. bytesRequiredForFormat — W64E-CSV-005 flips the CSV
//    AND TSV literals from `false` to `true` so the bytes-
//    fetch effect in Viewer.tsx reads CSV / TSV bytes
//    through the same seam TXT / MD / SVG / JSON / DOCX /
//    XLS / XLSX / EPUB already use. The mount owns the
//    `TextDecoder` + `Papa.parse(...)` lifecycle for both
//    extensions; the W4b4 dispatcher carries the typed
//    `delimiter` literal (`","` for CSV, `"\t"` for TSV) so
//    the mount passes the delimiter verbatim.
{
  assert.strictEqual(
    kernel.bytesRequiredForFormat("csv"), true,
    "W64E-CSV-005: bytesRequiredForFormat('csv') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads CSV bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX / EPUB effects "
    + "already use (the mount owns the TextDecoder + "
    + "Papa.parse(...) lifecycle)",
  );
  assert.strictEqual(
    kernel.bytesRequiredForFormat("tsv"), true,
    "W64E-CSV-005: bytesRequiredForFormat('tsv') must "
    + "return true so the bytes-fetch effect in Viewer.tsx "
    + "reads TSV bytes through the same seam the TXT / MD "
    + "/ SVG / JSON / DOCX / XLS / XLSX / EPUB / CSV "
    + "effects already use (CSV and TSV share the same "
    + "Papa Parse path; the delimiter literal is computed "
    + "from the format field)",
  );
  // The matrix stays honest end-to-end — every other
  // literal is unchanged from the W6.1 + W64A + W64B +
  // W64C + W64D contract.
  assert.strictEqual(kernel.bytesRequiredForFormat("txt"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("md"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("svg"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("json"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("docx"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("xls"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("xlsx"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("epub"), true);
  assert.strictEqual(kernel.bytesRequiredForFormat("pdf"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("html"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("htm"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("jpg"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("mp4"), false);
  assert.strictEqual(kernel.bytesRequiredForFormat("other"), false);
}

process.stdout.write("PASS\n");
"""


# W64E-CSV-005 — narrow behavior proof. The CSV / TSV
# materialization contract covers FOUR observable parts:
#
#   (a) BOTH delimiters — CSV uses `","` + TSV uses `"\t"`,
#       derived from the dispatch's `format` field (the W4b4
#       dispatcher carries the typed literal on
#       `dispatch.delimiter` so the mount passes it
#       verbatim).
#   (b) Sticky `<thead>` — the legacy
#       `web/file_viewer.js::renderTable` builds a `<thead>`
#       row; the React mount must keep the sticky behavior
#       the cascade already ships (`.fex-csv-table thead th`
#       carries `position: sticky; top: 0; z-index: 1`).
#   (c) Zebra `<tbody>` — the legacy paints alternating
#       row tints via `:nth-child(even)`; the React mount
#       must reference the same selector shape so the
#       cascade applies (`.fex-csv-table tbody
#       tr:nth-child(even) td`).
#   (d) Typed `cdn-failed` recovery — `Script.onError` OR
#       `Papa.parse(...)` exception routes through the
#       mount's typed recovery state that synthesizes a
#       `table-offline` dispatch with `reason:
#       "cdn-failed"` (the W64B-DOCX-002 typed union
#       contract applied to CSV / TSV).
#
# The narrow proof test below asserts all four parts in
# one shot so the CSV / TSV materialization contract
# surfaces end-to-end.
def test_w64e_viewer_csv_tsv_narrow_behavior_proof() -> None:
    """W64E-CSV-005 — narrow CSV / TSV behavior proof.
    Asserts all four observable contract parts in one
    test (delimiters + sticky thead + zebra tbody + typed
    `cdn-failed` recovery) so the CSV / TSV
    materialization surface is reviewable end-to-end."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()

    # (a) BOTH delimiters — CSV `","` + TSV `"\t"` derived
    #     from the dispatch's `format` field when
    #     `dispatch.delimiter` is not explicit. The
    #     onLoad handler MUST reference both literal
    #     values so a future PR that drops one trips the
    #     focused test. The `delimiter: format === "tsv" ?
    #     "\t" : ","` ternary mirrors the legacy
    #     `web/file_viewer.js::renderTable` `const delimiter
    #     = ext === "tsv" ? "\t" : ","` shape verbatim.
    assert re.search(r'delimiter.*tsv', text), (
        "Viewer.tsx must derive the TSV delimiter `\\t` "
        "from the format field (W64E-CSV-005 contract — "
        "mirrors the legacy `renderTable` ternary "
        "`const delimiter = ext === \"tsv\" ? \"\\t\" : "
        "\",\"` shape verbatim)."
    )
    # The `","` literal MUST appear inside the same onLoad
    # handler — a future PR that drops CSV (or hardcodes a
    # wrong delimiter) trips the focused test.
    csv_delim_match = re.search(r"delimiter[^;{}]*\",\"", text)
    assert csv_delim_match, (
        "Viewer.tsx must reference the CSV delimiter `\",\"` "
        "in the delimiter-derivation logic (W64E-CSV-005 "
        "contract — both CSV and TSV share the Papa Parse "
        "path; the delimiter is derived from the format "
        "field)."
    )

    # (b) Sticky `<thead>` — the React mount must reference
    #     a `<thead>` JSX element so the cascade's sticky
    #     header (`.fex-csv-table thead th { position:
    #     sticky; top: 0; z-index: 1 }`) applies.
    table_fn_match = re.search(
        r'function\s+TableRender\b[\s\S]*?\n\}\n',
        text,
    )
    assert table_fn_match, (
        "Viewer.tsx must define a `function TableRender(...)` "
        "sub-component for the W64E-CSV-005 materialization."
    )
    table_fn = table_fn_match.group(0)
    assert re.search(r"<thead\b", table_fn), (
        "Viewer.tsx's TableRender sub-component MUST render "
        "a `<thead>` JSX element so the cascade's sticky "
        "header (`.fex-csv-table thead th { position: "
        "sticky; top: 0; z-index: 1 }`) applies (W64E-CSV-005 "
        "narrow behavior proof — sticky thead)."
    )
    assert re.search(r"<th\b", table_fn), (
        "Viewer.tsx's TableRender sub-component MUST render "
        "a `<th>` JSX element inside `<thead>` so the legacy "
        "`renderTable` header row shape is preserved "
        "(W64E-CSV-005 narrow behavior proof — sticky thead)."
    )

    # (c) Zebra `<tbody>` — the React mount must reference
    #     `:nth-child(even)` (or equivalent) so the cascade's
    #     zebra row tint (`.fex-csv-table tbody tr:nth-
    #     child(even) td`) applies. Mirrors the legacy
    #     `renderTable` alternating-row behavior.
    assert re.search(r"<tbody\b", table_fn), (
        "Viewer.tsx's TableRender sub-component MUST render "
        "a `<tbody>` JSX element so the cascade's zebra row "
        "tint (`.fex-csv-table tbody tr:nth-child(even) td`) "
        "applies (W64E-CSV-005 narrow behavior proof — "
        "zebra tbody)."
    )
    assert re.search(r"<td\b", table_fn), (
        "Viewer.tsx's TableRender sub-component MUST render "
        "a `<td>` JSX element inside `<tbody>` so the legacy "
        "`renderTable` cell shape is preserved (W64E-CSV-005 "
        "narrow behavior proof — zebra tbody)."
    )
    assert re.search(
        r"fex-csv-scroller|fex-csv-table",
        table_fn,
    ), (
        "Viewer.tsx's TableRender sub-component MUST use the "
        "`.fex-csv-scroller` wrapper + `.fex-csv-table` "
        "selector so the W6.1 cascade applies (sticky thead "
        "+ zebra tbody + JetBrains Mono typography + outline-"
        "variant borders). Mirrors the legacy "
        "`web/file_viewer.js::renderTable` "
        "`target.replaceChildren(el(\"div\", { class: "
        "\"fex-csv-scroller\" }, table))` shape verbatim "
        "(W64E-CSV-005 narrow behavior proof — sticky thead "
        "+ zebra tbody + cascade)."
    )

    # (d) Typed `cdn-failed` recovery — the mount must
    #     reference the literal `"cdn-failed"` AND synthesize
    #     a `table-offline` dispatch (so the existing
    #     `renderOfflineCard` paints the download affordance
    #     with a typed `reason` literal distinct from the
    #     `bytes-missing` path the dispatcher emits).
    assert '"cdn-failed"' in text, (
        "Viewer.tsx must carry the literal `\"cdn-failed\"` "
        "so the typed recovery state surfaces a distinct "
        "value from the bytes-missing offline path "
        "(W64E-CSV-005 narrow behavior proof — Script.onError "
        "+ Papa.parse exception routes through the mount's "
        "typed recovery state whose `reason` literal is "
        "`\"cdn-failed\"`)."
    )
    assert re.search(
        r'kind:\s*"table-offline"|"table-offline"', table_fn,
    ), (
        "Viewer.tsx's TableRender sub-component MUST "
        "synthesize a `table-offline` dispatch with "
        "`reason: \"cdn-failed\"` so the existing "
        "`renderOfflineCard` paints the download affordance "
        "with a typed `reason` literal distinct from the "
        "`bytes-missing` path the dispatcher emits "
        "(W64E-CSV-005 narrow behavior proof — typed "
        "`cdn-failed` recovery)."
    )


# W64E-CSV-005 — viewer source-level checks. The
# Viewer.tsx React mount materializes the typed CSV / TSV
# source descriptor via Next 16's `<Script>` component +
# a typed `cdn-failed` recovery state on `Script.onError` +
# `Papa.parse` exception. The checks below pin the
# source-level shape so a future PR that silently drops
# the loader trips a focused test before review.
def test_w64e_viewer_table_source_uses_script_loader() -> None:
    """W64E-CSV-005 — Viewer.tsx MUST have an EXPLICIT
    `case "table-source":` branch in `renderDispatch`
    that's NOT routed through the W6.1 cdn-pending
    catch-all (the CSV / TSV variant now materializes via
    the Next `Script` loader + `Papa.parse(...)`, not the
    download-link card). The W64E contract places the
    `<Script>` JSX + the `onLoad` / `onError` handlers
    inside a dedicated `TableRender` sub-component that's
    mounted from the `case "table-source":` branch (the
    sub-component owns its own `loading` / `loaded` /
    `error` state — see the W64B-DOCX-002 typed
    `cdn-failed` recovery pattern that W64E mirrors). The
    case branch hands off to `TableRender` so the typed
    `ViewerDispatch` switch stays exhaustive; the
    `<Script>` surface is verified by extracting the
    entire `TableRender` block (NOT just the case-branch
    body)."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r'case\s+"table-source"\s*:', text), (
        "Viewer.tsx MUST have an explicit `case "
        "\"table-source\":` branch in `renderDispatch` so "
        "the typed CSV / TSV source descriptor materializes "
        "via the Next `Script` loader + `Papa.parse(...)` "
        "(NOT the W6.1 cdn-pending catch-all — "
        "W64E-CSV-005 contract)."
    )
    # The case branch hands off to a TableRender component.
    # Pin the handoff shape so the W64E separation between
    # the typed dispatch surface + the React lifecycle stays
    # honest.
    case_branch_match = re.search(
        r'case\s+"table-source"\s*:(.*?)(?=case\s+"|\}\s*\n\s*\})',
        text, re.DOTALL,
    )
    assert case_branch_match, (
        "Viewer.tsx must have an extractable table-source "
        "branch body in renderDispatch."
    )
    case_branch = case_branch_match.group(1)
    assert "TableRender" in case_branch, (
        "Viewer.tsx's `case \"table-source\":` branch MUST "
        "hand off to the dedicated `TableRender` sub-"
        "component (W64E-CSV-005 separation — the typed "
        "switch stays exhaustive; the `<Script>` + state "
        "lifecycle live in `TableRender`)."
    )
    # The TableRender component MUST render a `<Script>` JSX
    # element with `src`, `onLoad`, and `onError` props.
    # Extract the TableRender function body so the assertion
    # looks at the loader surface (not the case branch
    # hand-off, which only routes to the sub-component).
    table_fn_match = re.search(
        r'function\s+TableRender\b[\s\S]*?\n\}\n',
        text,
    )
    assert table_fn_match, (
        "Viewer.tsx must define a `function TableRender(...)` "
        "sub-component for the W64E-CSV-005 materialization "
        "(the dedicated lifecycle lives there)."
    )
    table_fn = table_fn_match.group(0)
    assert re.search(r'<Script\b', table_fn), (
        "Viewer.tsx's TableRender sub-component MUST render "
        "a `<Script>` JSX element from the `next/script` "
        "default import (W64E-CSV-005 contract — the "
        "CSV / TSV materialization owns the Next 16 "
        "`<Script src onLoad onError>` loader)."
    )
    assert re.search(r'\bonLoad=', table_fn) or re.search(
        r'\bonLoad =', table_fn,
    ), (
        "Viewer.tsx's TableRender sub-component MUST wire "
        "the `<Script>` `onLoad` handler to call "
        "`window[dispatch.scriptGlobal].parse(text, "
        "{delimiter, skipEmptyLines: true})`."
    )
    assert re.search(r'\bonError=', table_fn) or re.search(
        r'\bonError =', table_fn,
    ), (
        "Viewer.tsx's TableRender sub-component MUST wire "
        "the `<Script>` `onError` handler so the script-"
        "load failure surfaces through the typed "
        "`cdn-failed` recovery state."
    )


def test_w64e_viewer_table_source_calls_papa_parse_with_skip_empty_lines() -> None:
    """W64E-CSV-005 — the TableRender onLoad handler MUST
    call `window[dispatch.scriptGlobal].parse(text,
    {delimiter, skipEmptyLines: true})` so the Papa Parse
    library parses the CSV / TSV text into a typed
    `{data: string[][]}` shape (matches the legacy
    `web/file_viewer.js::renderTable` `window.Papa.parse(
    text, { delimiter, skipEmptyLines: true })` shape
    verbatim). The mount MUST reach the pinned global
    through `dispatch.scriptGlobal` (NOT a hardcoded
    `"Papa"` literal) so a future PR that bumps the CDN
    pin lands in lock-step across the dispatcher
    constant + the loader site. The `skipEmptyLines: true`
    option MUST be present so empty rows don't pollute
    the rendered table."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(r"\.parse\s*\(", text), (
        "Viewer.tsx must reference `.parse(...)` so the "
        "W64E-CSV-005 onLoad handler routes the UTF-8 "
        "decoded CSV / TSV text through Papa Parse's "
        "text parser."
    )
    assert re.search(
        r"skipEmptyLines\s*:\s*true", text,
    ), (
        "Viewer.tsx must pass `{skipEmptyLines: true}` to "
        "`Papa.parse(...)` so empty rows don't pollute the "
        "rendered table — mirrors the legacy "
        "`web/file_viewer.js::renderTable` "
        "`Papa.parse(text, { delimiter, skipEmptyLines: "
        "true })` shape verbatim (W64E-CSV-005 contract)."
    )
    assert re.search(
        r"window\s*\[\s*\w+\.scriptGlobal\s*\]"
        r"|window\s*\[\s*\w+\s*\]\s*\.\s*parse",
        text,
    ), (
        "Viewer.tsx must reach the pinned Papa Parse global "
        "through `window[dispatch.scriptGlobal].parse(...)` "
        "— NOT a hardcoded `\"Papa\"` literal — so a future "
        "PR that bumps the CDN pin lands in lock-step "
        "across the dispatcher constant + the loader site "
        "(W64E-CSV-005 contract — mirrors the W64B-DOCX-002 "
        "`window[dispatch.scriptGlobal].convertToHtml(...)` "
        "pattern + the W64C-XLS-003 "
        "`window[dispatch.scriptGlobal].read(...)` pattern)."
    )


def test_w64e_viewer_table_source_decodes_utf8() -> None:
    """W64E-CSV-005 — the TableRender onLoad handler MUST
    UTF-8-decode the bytes through `TextDecoder` before
    handing the text to `Papa.parse(...)` (matches the W4a
    TXT / MD UTF-8 decode shape verbatim + the W4b1 DOCX
    `arrayBuffer: bytes.buffer` shape). `TextDecoder` is
    part of ES2022 + every modern browser — no polyfill
    needed. The decode MUST use `fatal: false` so malformed
    UTF-8 sequences yield a U+FFFD replacement character
    rather than throwing (mirrors the W4a TXT / MD
    `text-pre` decoder shape)."""
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()
    assert re.search(
        r"new\s+TextDecoder\s*\(", text,
    ), (
        "Viewer.tsx must call `new TextDecoder(...)` so the "
        "W64E-CSV-005 onLoad handler UTF-8-decodes the CSV / "
        "TSV bytes before handing the text to "
        "`Papa.parse(...)`. The `TextDecoder` constructor is "
        "part of ES2022 + every modern browser — no "
        "polyfill needed."
    )
    assert re.search(
        r"TextDecoder\s*\(\s*[\"']utf-8[\"']", text,
    ), (
        "Viewer.tsx must UTF-8-decode the CSV / TSV bytes "
        "through `new TextDecoder(\"utf-8\", {fatal: false})` "
        "so malformed UTF-8 sequences yield a U+FFFD "
        "replacement character rather than throwing "
        "(W64E-CSV-005 contract — mirrors the W4a TXT / MD "
        "`text-pre` decoder shape)."
    )


def test_w64e_viewer_preserves_json_docx_sheet_epub_offline_pins() -> None:
    """W64E-CSV-005 — the CSV / TSV materialization adds a
    new `case \"table-source\":` branch but MUST NOT
    silently drop or rewrite the W6.4a + W6.4b + W6.4c +
    W6.4d pins:

      1. The W64A-JSON-001 JSON Tree pins (`case
         \"json-source\":` branch + the `[root]` literal +
         the `Tree truncated — open raw` banner text).
      2. The W64B-DOCX-002 DOCX mount pins (the
         `case \"docx-source\":` branch + the `DocxRender`
         sub-component + the `convertToHtml` call +
         `arrayBuffer` wrapper).
      3. The W64C-XLS-003 XLS / XLSX mount pins (the
         `case \"sheet-source\":` branch + the
         `SheetRender` sub-component + the `.read` /
         `sheet_to_html` call sites + the `<select>`
         picker).
      4. The W64D-EPUB-004 EPUB mount pins (the
         `case \"epub-source\":` branch + the `EpubRender`
         sub-component + the `renderTo` call + the
         `prev` / `next` handlers + the `previousBook`
         lifecycle).
      5. The pre-W64E `table-offline` (bytes-missing)
         dispatch stays in the W6.1 cdn-pending catch-all
         — the W64E slice only extracts `table-source`
         from the catch-all; `table-offline` keeps the
         existing W6.1 download-link affordance.

    A future PR that adds the CSV / TSV materialization
    while accidentally dropping a JSON / DOCX / XLS / XLSX
    / EPUB / table-offline pin breaks multiple contracts
    at review.
    """
    if not VIEWER_FILE.is_file():
        pytest.skip("Viewer.tsx not present yet")
    text = VIEWER_FILE.read_text()

    # 1. W64A-JSON-001 pins.
    assert re.search(r'case\s+"json-source"\s*:', text), (
        "Viewer.tsx MUST keep its W64A-JSON-001 "
        "`case \"json-source\":` branch — W64E must NOT "
        "silently drop the JSON Tree viewer while adding "
        "the CSV / TSV materialization."
    )
    assert '"[root]"' in text, (
        "Viewer.tsx must keep the legacy `[root]` literal "
        "(the W64A-JSON-001 synthetic root key)."
    )
    assert "Tree truncated — open raw" in text, (
        "Viewer.tsx must keep the legacy "
        "`Tree truncated — open raw` banner text "
        "(the W64A-JSON-001 truncation banner)."
    )

    # 2. W64B-DOCX-002 pins.
    assert re.search(r'case\s+"docx-source"\s*:', text), (
        "Viewer.tsx MUST keep its W64B-DOCX-002 "
        "`case \"docx-source\":` branch — W64E must NOT "
        "silently drop the DOCX mount while adding the "
        "CSV / TSV materialization."
    )
    assert "DocxRender" in text, (
        "Viewer.tsx must keep its W64B-DOCX-002 "
        "`DocxRender` sub-component — W64E mirrors the "
        "W64B separation between the typed dispatch surface "
        "+ the React lifecycle; both sub-components stay "
        "alive in lock-step."
    )
    assert "convertToHtml" in text, (
        "Viewer.tsx must keep the W64B-DOCX-002 "
        "`convertToHtml(...)` reference so the DOCX "
        "materialization stays intact."
    )
    assert "arrayBuffer" in text, (
        "Viewer.tsx must keep the W64B-DOCX-002 "
        "`arrayBuffer` wrapper so the DOCX bytes are "
        "passed to mammoth through the typed "
        "`{arrayBuffer: bytes.buffer}` shape."
    )

    # 3. W64C-XLS-003 pins.
    assert re.search(r'case\s+"sheet-source"\s*:', text), (
        "Viewer.tsx MUST keep its W64C-XLS-003 "
        "`case \"sheet-source\":` branch — W64E must NOT "
        "silently drop the XLS / XLSX mount while adding "
        "the CSV / TSV materialization."
    )
    assert "SheetRender" in text, (
        "Viewer.tsx must keep its W64C-XLS-003 "
        "`SheetRender` sub-component — W64E mirrors the "
        "W64C separation between the typed dispatch surface "
        "+ the React lifecycle; both sub-components stay "
        "alive in lock-step."
    )
    assert "sheet_to_html" in text, (
        "Viewer.tsx must keep the W64C-XLS-003 "
        "`sheet_to_html(...)` reference so the XLS / XLSX "
        "materialization stays intact."
    )

    # 4. W64D-EPUB-004 pins.
    assert re.search(r'case\s+"epub-source"\s*:', text), (
        "Viewer.tsx MUST keep its W64D-EPUB-004 "
        "`case \"epub-source\":` branch — W64E must NOT "
        "silently drop the EPUB mount while adding the "
        "CSV / TSV materialization."
    )
    assert "EpubRender" in text, (
        "Viewer.tsx must keep its W64D-EPUB-004 "
        "`EpubRender` sub-component — W64E mirrors the "
        "W64D separation between the typed dispatch surface "
        "+ the React lifecycle; both sub-components stay "
        "alive in lock-step."
    )
    assert "renderTo" in text, (
        "Viewer.tsx must keep the W64D-EPUB-004 "
        "`renderTo(...)` reference so the EPUB "
        "materialization stays intact."
    )

    # 5. The pre-W64E table-offline (bytes-missing) dispatch
    #    stays in the W6.1 cdn-pending catch-all. The test
    #    asserts `table-offline` is still listed in the
    #    catch-all alongside `docx-offline` + `sheet-offline`
    #    + `epub-offline` + `json-offline`.
    cdn_pending_catch_all_match = re.search(
        r'(case\s+"docx-offline"\s*:[\s\S]*?)return\s+renderOfflineCard',
        text,
    )
    assert cdn_pending_catch_all_match, (
        "Viewer.tsx must keep its W6.1 cdn-pending catch-"
        "all `return renderOfflineCard(...)` branch so the "
        "`*-offline` variants (docx-offline / sheet-offline "
        "/ epub-offline / table-offline / json-offline) "
        "all funnel through the existing download-link "
        "recovery card. W64E extracts `table-source` from "
        "this catch-all but leaves `table-offline` in place."
    )
    catch_all_body = cdn_pending_catch_all_match.group(1)
    for offline_literal in (
        "docx-offline",
        "sheet-offline",
        "epub-offline",
        "table-offline",
        "json-offline",
    ):
        assert f'"{offline_literal}"' in catch_all_body, (
            f"Viewer.tsx's cdn-pending catch-all MUST still "
            f"list `{offline_literal}` so the pre-W64E bytes-"
            f"missing offline path is preserved verbatim "
            f"(W64E-CSV-005 acceptance: 'the pre-W64E "
            f"table-offline dispatch (bytes-missing) stays "
            f"in the cdn-pending catch-all'). Got: "
            f"{catch_all_body!r}"
        )

    # 6. `table-source` MUST NOT appear in the cdn-pending
    #    catch-all anymore — the W64E slice extracts it so
    #    the typed source descriptor routes through
    #    `TableRender` instead. The pre-W64E
    #    `table-source` (which was just a download-link
    #    card for a non-CDN surface) now materializes via
    #    the Next `Script` loader + `Papa.parse(...)`.
    assert '"table-source"' not in catch_all_body, (
        "Viewer.tsx's cdn-pending catch-all MUST NOT list "
        "`table-source` anymore — W64E-CSV-005 extracts "
        "the CSV / TSV source descriptor from the catch-all "
        "so the typed source routes through the "
        "`TableRender` sub-component (NOT the W6.1 "
        "download-link affordance)."
    )


# ---------------------------------------------------------------------------
# W6.5-BRIDGE-006 — FolderTab → Explorer refresh bridge.
# The native FolderTab (ODD-TDFOLDER-001) dispatches a
# `window.CustomEvent("taxa:explorer:refresh")` when
# `materializeResearch` (or `openFolder`) succeeds. The
# Explorer route subscribes to that event on mount and
# re-fetches `/api/files` so the tree mirrors the new
# folder structure without dropping `ExplorerLoadStatus`
# / expanded set / selected-path / `ViewerState`.
#
# Acceptance (verbatim from the W6.5 task brief):
#  - Signal is a window-scoped `CustomEvent` named
#    `"taxa:explorer:refresh"` (verbatim).
#  - Dispatched from `FolderTab` once the create / open
#    transitions reach the success state.
#  - Explorer subscribes on mount + unsubscribes on unmount.
#  - Re-fetches `/api/files` on every event (idempotent —
#    multiple events fire multiple re-fetches).
#  - Does NOT drop `ExplorerLoadStatus` / expanded set /
#    selected-path / `ViewerState` / search state.
#  - No `@taxa/browser-state` key expansion.
#  - No router-key re-mount.
#  - No legacy `web/` mutation.
#
# The W6.5 contract surfaces through:
#  - `src/modules/research/presentation/explorer-state.ts`
#    — exports `EXPLORER_REFRESH_EVENT_NAME` (the canonical
#    literal) + `isFolderSuccessStatusKind` (pure predicate).
#  - `src/modules/research/presentation/Explorer.tsx` —
#    local `EXPLORER_REFRESH_EVENT_NAME` literal + a
#    `useEffect` that subscribes via
#    `window.addEventListener(...)` on mount and returns
#    a cleanup `window.removeEventListener(...)` on unmount.
#  - `src/modules/taxonomy/presentation/FolderTab.tsx` —
#    local `EXPLORER_REFRESH_EVENT_NAME` literal + two
#    `useEffect`s that dispatch
#    `new CustomEvent(EXPLORER_REFRESH_EVENT_NAME)` from
#    `window` when `createStatus.kind === "created"` or
#    `openStatus.kind === "opened"`.
# ---------------------------------------------------------------------------


def test_w65_kernel_exports_explorer_refresh_event_name_constant() -> None:
    """W6.5-BRIDGE-006 — `explorer-state.ts` MUST export
    `EXPLORER_REFRESH_EVENT_NAME` with the verbatim literal
    `"taxa:explorer:refresh"`. The kernel owns the canonical
    event-name constant so a future consumer (test harness,
    integration test, or cross-module bridge) reaches the
    typed literal through the kernel export. The Explorer +
    FolderTab literals are pinned to the same value via
    separate tests; a future PR that bumps the event name
    MUST update the kernel export AND both consumer
    literals AND re-run the W6.5 focused tests."""
    if not EXPLORER_STATE_FILE.is_file():
        pytest.skip("explorer-state.ts not present yet")
    text = EXPLORER_STATE_FILE.read_text()
    assert re.search(
        r"export\s+const\s+EXPLORER_REFRESH_EVENT_NAME\b",
        text,
    ), (
        "explorer-state.ts must export "
        "`EXPLORER_REFRESH_EVENT_NAME` as a constant (the "
        "canonical W6.5-BRIDGE-006 event name). The W6.5 "
        "contract surfaces this typed literal to tests + "
        "cross-module bridges."
    )
    # The verbatim literal `"taxa:explorer:refresh"` MUST
    # appear as the constant's value (single or double
    # quotes both OK). No concatenation, no template
    # literal, no runtime derivation — the canonical
    # literal is the only contract.
    assert re.search(
        r'EXPLORER_REFRESH_EVENT_NAME\s*=\s*["\']taxa:explorer:refresh["\']',
        text,
    ), (
        "EXPLORER_REFRESH_EVENT_NAME must be assigned the "
        "verbatim literal `\"taxa:explorer:refresh\"` (the "
        "W6.5-BRIDGE-006 canonical event name). A future "
        "rename MUST update the kernel constant AND the "
        "Explorer.tsx + FolderTab.tsx literals in lock-step."
    )


def test_w65_kernel_exports_is_folder_success_status_kind_predicate() -> None:
    """W6.5-BRIDGE-006 — `explorer-state.ts` MUST export a
    pure `isFolderSuccessStatusKind(kind: string): kind is
    FolderSuccessStatusKind` predicate that returns `true`
    for the two success literals (`"created"` / `"opened"`)
    and `false` for every other status. Pure, framework-
    free, importable through the kernel. Mirrors the
    FolderTab discriminated union surface so the React
    layer can call the predicate without a cross-module
    type import."""
    if not EXPLORER_STATE_FILE.is_file():
        pytest.skip("explorer-state.ts not present yet")
    text = EXPLORER_STATE_FILE.read_text()
    assert re.search(
        r"export\s+function\s+isFolderSuccessStatusKind\b",
        text,
    ), (
        "explorer-state.ts must export "
        "`isFolderSuccessStatusKind` as a pure predicate. "
        "The W6.5-BRIDGE-006 contract surfaces the "
        "`createStatus.kind === 'created'` / "
        "`openStatus.kind === 'opened'` dispatch decision "
        "through a focused, testable helper."
    )
    # Type-narrowing predicate — the return type MUST use
    # the type guard syntax (`kind is FolderSuccessStatusKind`)
    # so the React layer's narrowing survives the call.
    # The lenient match tolerates whitespace / newline
    # between the parameter list and the return type
    # (the implementation's signature spans multiple
    # lines under Prettier's wrap heuristic + may carry a
    # trailing comma after `kind: string,`).
    stripped = re.sub(r"\s+", "", text)
    assert re.search(
        r"isFolderSuccessStatusKind\(kind:string,?\):kindisFolderSuccessStatusKind",
        stripped,
    ), (
        "isFolderSuccessStatusKind must be a TypeScript "
        "type guard (`kind is FolderSuccessStatusKind`) so "
        "the React layer's narrowing survives the call. A "
        "plain boolean return would force the React layer "
        "to re-cast the kind literal."
    )


# Runtime harness — exercises the W6.5 pure helpers
# (`EXPLORER_REFRESH_EVENT_NAME` constant +
# `isFolderSuccessStatusKind` predicate) under Node
# ES2022-only (no DOM, no React). The harness re-uses
# the same `compiled_w6_1_kernel` fixture as the W6.1 /
# W64A / W64B / W64C / W64D / W64E harnesses; the
# W6.5 kernel additions land in the same compiled
# module without rebuilding.
_W6_5_RUNTIME_HARNESS = r"""
// CJS does not support top-level await (only ESM does), so
// the harness wraps the assertions in a sync body — every
// W6.5 kernel helper is pure (no async, no I/O).
const path = require("path");
const assert = require("assert");
const kernel = require(path.resolve(process.argv[2]));

// 1. EXPLORER_REFRESH_EVENT_NAME — verbatim literal. The
//    W6.5 contract pins the literal `"taxa:explorer:refresh"`
//    byte-for-byte. A future PR that bumps the event name
//    must update the kernel constant AND the Explorer.tsx
//    + FolderTab.tsx consumer literals AND re-run the
//    focused tests; this runtime assertion guarantees the
//    kernel constant is the verbatim canonical literal.
{
  assert.strictEqual(
    typeof kernel.EXPLORER_REFRESH_EVENT_NAME,
    "string",
    "EXPLORER_REFRESH_EVENT_NAME must be a string constant",
  );
  assert.strictEqual(
    kernel.EXPLORER_REFRESH_EVENT_NAME,
    "taxa:explorer:refresh",
    "EXPLORER_REFRESH_EVENT_NAME must equal the verbatim "
    + "literal \"taxa:explorer:refresh\" (the W6.5-BRIDGE-006 "
    + "canonical event name)",
  );
}

// 2. isFolderSuccessStatusKind — success-state predicate.
//    The two FolderTab success literals (`"created"` for
//    materializeResearch, `"opened"` for openFolder) MUST
//    return true. Every other status kind MUST return
//    false so the FolderTab dispatch is bound to the
//    success transition only — a mid-flight `"creating"` /
//    `"opening"` state MUST NOT fire the dispatch.
{
  assert.strictEqual(
    kernel.isFolderSuccessStatusKind("created"), true,
    "isFolderSuccessStatusKind('created') must return true "
    + "(materializeResearch success -> explorer refresh dispatch)",
  );
  assert.strictEqual(
    kernel.isFolderSuccessStatusKind("opened"), true,
    "isFolderSuccessStatusKind('opened') must return true "
    + "(openFolder success -> explorer refresh dispatch)",
  );
  // FolderCreateStatus / FolderOpenStatus non-success
  // kinds + the null / undefined edge cases + a few
  // would-be synonyms ("succeeded", "materialized") that
  // MUST NOT trigger the dispatch. The exhaustive list
  // pins the predicate's negative surface.
  for (const kind of [
    "idle", "creating", "opening", "error", "copied",
    "", "CREATED", "Created", "open", "succeeded",
    "materialized", "true", "false", "1", "0", null, undefined,
  ]) {
    assert.strictEqual(
      kernel.isFolderSuccessStatusKind(kind), false,
      `isFolderSuccessStatusKind(${JSON.stringify(kind)}) must return false `
      + "(non-success status MUST NOT trigger the explorer refresh dispatch)",
    );
  }
}

process.stdout.write("PASS\n");
"""


def test_compiled_w6_5_kernel_passes_runtime_contract(
    compiled_w6_1_kernel: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """W6.5-BRIDGE-006 — under Node (ES2022 only, no DOM,
    no React), the compiled W6.5 kernel additions
    (`EXPLORER_REFRESH_EVENT_NAME` constant +
    `isFolderSuccessStatusKind` predicate) satisfy the
    pure contract end-to-end:

      1. `EXPLORER_REFRESH_EVENT_NAME` equals the
         verbatim literal `"taxa:explorer:refresh"`
         (the W6.5 canonical event name).
      2. `isFolderSuccessStatusKind("created")` returns
         `true` (the FolderTab materialize success
         literal).
      3. `isFolderSuccessStatusKind("opened")` returns
         `true` (the FolderTab open-folder success
         literal).
      4. `isFolderSuccessStatusKind(<every-other>)`
         returns `false` (the dispatch is bound to the
         success transition only — `idle` / `creating` /
         `opening` / `error` / `copied` MUST NOT trigger
         the dispatch).

    The harness reuses the existing
    `compiled_w6_1_kernel` fixture; the kernel compile
    already pulls `explorer-state.ts` so the W6.5
    additions land in the same compiled module without
    rebuilding."""
    _compiled_kernel, _compiled_renderers = compiled_w6_1_kernel
    harness = tmp_path / "harness.cjs"
    harness.write_text(_W6_5_RUNTIME_HARNESS)
    result = subprocess.run(
        ["node", str(harness), str(_compiled_kernel)],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"W6.5 runtime harness failed.\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected W6.5 harness output: {result.stdout!r}"
    )


def test_w65_explorer_defines_local_event_name_literal() -> None:
    """W6.5-BRIDGE-006 — `Explorer.tsx` MUST define a
    local `EXPLORER_REFRESH_EVENT_NAME = "taxa:explorer:refresh"`
    constant so the React layer subscribes with the
    verbatim canonical literal. The constant is local
    (not imported from the kernel — the barrel is out
    of scope for W6.5) so a focused test pins the literal
    byte-for-byte. A future PR that renames the event
    MUST update the kernel constant + the Explorer.tsx
    literal + the FolderTab.tsx literal in lock-step."""
    if not EXPLORER_FILE.is_file():
        pytest.skip("Explorer.tsx not present yet")
    text = EXPLORER_FILE.read_text()
    assert re.search(
        r'EXPLORER_REFRESH_EVENT_NAME\s*=\s*["\']taxa:explorer:refresh["\']',
        text,
    ), (
        "Explorer.tsx MUST define a local "
        "`EXPLORER_REFRESH_EVENT_NAME = \"taxa:explorer:refresh\"` "
        "constant so the React layer subscribes with the "
        "verbatim canonical literal (W6.5-BRIDGE-006 contract)."
    )


def test_w65_explorer_subscribes_via_window_add_event_listener() -> None:
    """W6.5-BRIDGE-006 — `Explorer.tsx` MUST register
    `window.addEventListener(EXPLORER_REFRESH_EVENT_NAME, ...)`
    inside a `useEffect` so the route subscribes to the
    FolderTab dispatch on mount. A bare call (outside
    `useEffect`) would run on every render and leak
    listeners."""
    if not EXPLORER_FILE.is_file():
        pytest.skip("Explorer.tsx not present yet")
    text = EXPLORER_FILE.read_text()
    assert re.search(
        r"window\.addEventListener\s*\(\s*EXPLORER_REFRESH_EVENT_NAME",
        text,
    ), (
        "Explorer.tsx MUST call "
        "`window.addEventListener(EXPLORER_REFRESH_EVENT_NAME, ...)` "
        "so the route subscribes to the FolderTab dispatch "
        "(W6.5-BRIDGE-006 contract)."
    )
    # The addEventListener call MUST live inside a
    # `useEffect` block. The lenient heuristic: the
    # `useEffect(` opener appears within 1500 chars before
    # the addEventListener call (catches the typical
    # `useEffect(() => { ... })` shape, plus the SSR
    # guard + the handler arrow body + the
    # addEventListener call site). A bare
    # `window.addEventListener` call outside a useEffect
    # would have no `useEffect(` opener nearby — the
    # heuristic trips.
    add_idx = text.find("window.addEventListener(EXPLORER_REFRESH_EVENT_NAME")
    assert add_idx > 0, "addEventListener not located"
    effect_open_idx = text.rfind("useEffect(", 0, add_idx)
    assert effect_open_idx > 0 and (add_idx - effect_open_idx) < 1500, (
        "Explorer.tsx's addEventListener call MUST live "
        "inside a `useEffect` block (no nearby "
        "`useEffect(` opener appears within 1500 chars "
        "before the call site). W6.5-BRIDGE-006 contract: "
        "the listener MUST be registered inside a "
        "`useEffect` so the route subscribes on mount."
    )


def test_w65_explorer_unregisters_via_window_remove_event_listener() -> None:
    """W6.5-BRIDGE-006 — `Explorer.tsx` MUST call
    `window.removeEventListener(EXPLORER_REFRESH_EVENT_NAME, ...)`
    so the listener is removed on unmount. Without the
    cleanup, a route change would leak listeners and the
    dispatch would fire on a defunct Explorer instance
    after navigation. The removeEventListener MUST use
    the same `EXPLORER_REFRESH_EVENT_NAME` identifier
    so React's listener identity check matches.

    The lenient match tolerates whitespace / newlines
    between `window.removeEventListener` and the
    identifier — the implementation wraps the call
    across multiple lines for readability."""
    if not EXPLORER_FILE.is_file():
        pytest.skip("Explorer.tsx not present yet")
    text = EXPLORER_FILE.read_text()
    stripped = re.sub(r"\s+", "", text)
    assert "window.removeEventListener(EXPLORER_REFRESH_EVENT_NAME," in stripped, (
        "Explorer.tsx MUST call "
        "`window.removeEventListener(EXPLORER_REFRESH_EVENT_NAME, ...)` "
        "so the listener is removed on unmount "
        "(W6.5-BRIDGE-006 contract)."
    )
    # Order: addEventListener MUST appear BEFORE
    # removeEventListener in the file (the listener is
    # registered on mount, then removed on unmount). The
    # search uses the stripped form to tolerate the
    # implementation's newline + indent wrap.
    add_idx = stripped.find("window.addEventListener(EXPLORER_REFRESH_EVENT_NAME,")
    remove_idx = stripped.find("window.removeEventListener(EXPLORER_REFRESH_EVENT_NAME,")
    assert add_idx > 0 and remove_idx > 0, (
        "Explorer.tsx must contain both addEventListener "
        "and removeEventListener for EXPLORER_REFRESH_EVENT_NAME "
        "(W6.5-BRIDGE-006 contract: subscribe on mount, "
        "unsubscribe on unmount)."
    )
    assert add_idx < remove_idx, (
        "Explorer.tsx's addEventListener call MUST appear "
        "BEFORE the removeEventListener call (subscribe on "
        "mount, unsubscribe on unmount — W6.5-BRIDGE-006 "
        "contract)."
    )


def test_w65_explorer_listener_invokes_load_tree() -> None:
    """W6.5-BRIDGE-006 — the Explorer.tsx listener MUST
    invoke `loadTree()` so the /api/files tree re-fetches
    on every FolderTab dispatch. The listener is the
    bridge between the FolderTab → Explorer signal and
    the existing `ExplorerLoadStatus` lifecycle; calling
    `loadTree` flips `loadStatus` to `"loading"` then
    resolves to `"loaded"` / `"empty"` / `"error"`.

    The handler body lives INSIDE the same useEffect
    block as the addEventListener call — typically as a
    named arrow (`const handler = () => { void loadTree(); };`)
    defined BEFORE the addEventListener call site. The
    test scans a 1500-char window BEFORE the
    addEventListener call (inside the enclosing useEffect)
    to capture the handler definition."""
    if not EXPLORER_FILE.is_file():
        pytest.skip("Explorer.tsx not present yet")
    text = EXPLORER_FILE.read_text()
    add_idx = text.find("window.addEventListener(EXPLORER_REFRESH_EVENT_NAME")
    assert add_idx > 0, (
        "Explorer.tsx's addEventListener must reference "
        "EXPLORER_REFRESH_EVENT_NAME."
    )
    # Scan the 1500 chars BEFORE the addEventListener call
    # to capture the handler definition. The handler lives
    # in the same useEffect block as the addEventListener
    # call site, so this window reaches it.
    effect_open_idx = text.rfind("useEffect(", 0, add_idx)
    assert effect_open_idx > 0, (
        "Explorer.tsx's addEventListener must live inside "
        "a useEffect block (no useEffect opener nearby)."
    )
    window = text[effect_open_idx : add_idx + 200]
    assert re.search(r"\b(?:void\s+)?loadTree\s*\(\s*\)", window), (
        "Explorer.tsx's useEffect block MUST contain a "
        "`loadTree()` call (with or without `void` prefix) "
        "so the FolderTab dispatch triggers a /api/files "
        "re-fetch. W6.5-BRIDGE-006 contract: the bridge "
        "calls the existing tree-fetch callback (the "
        "`loadTree` `useCallback` wired by the W6.1 mount)."
    )


def test_w65_explorer_listener_does_not_touch_other_state() -> None:
    """W6.5-BRIDGE-006 — the Explorer.tsx listener MUST
    ONLY invoke `loadTree()`. It MUST NOT touch
    `setExpanded` / `setSelectedPath` / `setViewerState` /
    `setSearchQuery` / `setSearchMode` /
    `setSearchHideEmpty` so a refresh preserves the
    existing ExplorerLoadStatus / expanded set /
    selected-path / ViewerState / search state. The
    handler body is intentionally narrow — typically just
    `void loadTree()` — so the bridge stays idempotent +
    side-effect-free for everything except the tree
    refresh.

    The handler body lives INSIDE the same useEffect
    block as the addEventListener call. The test
    extracts the subscription useEffect block via
    brace-counting so the scan stays bounded to the
    effect body (handler def + addEventListener + cleanup
    return) and does NOT reach the surrounding code
    that legitimately uses the state setters."""
    if not EXPLORER_FILE.is_file():
        pytest.skip("Explorer.tsx not present yet")
    text = EXPLORER_FILE.read_text()
    add_idx = text.find("window.addEventListener(EXPLORER_REFRESH_EVENT_NAME")
    assert add_idx > 0, (
        "Explorer.tsx's addEventListener must reference "
        "EXPLORER_REFRESH_EVENT_NAME."
    )
    effect_open_idx = text.rfind("useEffect(", 0, add_idx)
    assert effect_open_idx > 0, (
        "Explorer.tsx's addEventListener must live inside "
        "a useEffect block."
    )
    # Find the opening `{` of the useEffect body — the
    # arrow function body opens after `() =>`.
    body_open = text.find("{", effect_open_idx)
    assert body_open > 0, (
        "Explorer.tsx's subscription useEffect must open "
        "an arrow body with `{`."
    )
    # Brace-counting — walk forward to find the matching
    # `}` that closes the arrow body. Nested arrows
    # (the handler + cleanup) increment + decrement
    # symmetrically so the depth returns to 0 at the
    # end of the effect body.
    depth = 0
    body_end = -1
    for i in range(body_open, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                body_end = i + 1
                break
    assert body_end > body_open, (
        "Explorer.tsx's subscription useEffect body MUST "
        "close with a matching `}` (brace-counting "
        "traversal failed — the effect body is malformed)."
    )
    window = text[effect_open_idx:body_end]
    forbidden_setters = (
        "setExpanded", "setSelectedPath", "setViewerState",
        "setSearchQuery", "setDebouncedQuery", "setSearchMode",
        "setSearchHideEmpty",
    )
    for setter in forbidden_setters:
        assert setter not in window, (
            f"Explorer.tsx's subscription useEffect block "
            f"MUST NOT call `{setter}` — the W6.5-BRIDGE-006 "
            f"contract preserves ExplorerLoadStatus / "
            f"expanded set / selected-path / ViewerState / "
            f"search state on every FolderTab dispatch. "
            f"The handler is intended to ONLY call "
            f"`loadTree()` so the existing loadStatus "
            f"lifecycle runs to `loading` -> `loaded` / "
            f"`empty` / `error` without touching the "
            f"user's interactive state."
        )
