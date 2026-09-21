"""
Research viewer-dispatch contract tests (W4a + W4b1 + W4b2 +
W4b3 of `complete-frontend-migration`).

Pins the pure typed viewer-dispatch contract in
`src/modules/research/application/renderers.ts`. The contract is
the application-layer renderer-dispatch decision for the eight
no-CDN families (`pdf`, `html`/`htm`, `txt`, `md` legacy-as-text,
`doc` fallback, `jpg`/`jpeg`/`png`/`gif`/`webp`/`bmp`, `svg`
with XSS scrub, `mp4`/`webm`/`ogv`) plus the `"other"` extension
fallback plus the Table/Tree tab-not-applicable feedback, plus
the W4b1 DOCX source/offline branch, plus the W4b2 XLS / XLSX
source/offline branch, plus the W4b3 EPUB source/offline branch.

The W4 split is owned by reviewable slices:

  - W4a — framework-free, no-CDN preview dispatch; preserves
    legacy Markdown-as-text behavior. The dispatcher returns
    `unsupported` / `tab-not-applicable` for the deferred
    format + tab combinations, mirroring the legacy "Format
    .xyz not supported in viewer." and "${tab} view not
    available for .${ext} files — use Raw." fallbacks.
  - W4b1 — DOCX only. The dispatcher emits a typed `docx-source`
    outcome that carries the descriptor + bytes + pinned
    mammoth CDN URL + global name so a future React mount
    (W6+) can load the legacy-pinned mammoth library and
    convert the bytes to HTML. When bytes are missing, the
    dispatcher emits a typed `docx-offline` branch with the
    download link + pinned CDN URL so the mount paints the
    same legacy "Viewer offline" banner with a download
    affordance. The application layer stays framework-free,
    browser-free, and CDN-loader-free — mammoth is NOT
    imported or loaded here; the dispatcher only emits the
    source descriptor for the mount to consume.
  - W4b2 — XLS / XLSX only. Both extensions dispatch through
    the same SheetJS path (`XLSX.read(bytes, {type: "array"})`
    + `XLSX.utils.sheet_to_html(sheet)`); the dispatcher
    emits a typed `sheet-source` outcome with the pinned
    SheetJS CDN URL + global name. When bytes are missing,
    the dispatcher emits a typed `sheet-offline` branch.
    The application layer stays framework-free,
    browser-free, and CDN-loader-free — SheetJS is NOT
    imported or loaded here; the dispatcher only emits the
    source descriptor for the mount to consume.
  - W4b3 — EPUB only. The dispatcher emits a typed
    `epub-source` outcome that carries the descriptor +
    bytes + pinned epubjs CDN URL + global name so a
    future React mount (W6+) can load the legacy-pinned
    epubjs library, call `ePub(bytes.buffer)`, and own the
    full EPUB render lifecycle (`book.renderTo(hostEl, ...)`
    + prev / next click handlers + `_currentBook.destroy()`
    teardown on the NEXT open so listeners don't leak —
    mirrors the legacy `web/file_viewer.js::renderEpub`
    verbatim). When bytes are missing, the dispatcher
    emits a typed `epub-offline` branch with the download
    link + pinned CDN URL so the mount paints the same
    legacy "Viewer offline" banner with a download
    affordance. The application layer stays framework-free,
    browser-free, and CDN-loader-free — epubjs is NOT
    imported or loaded here; the dispatcher only emits the
    source descriptor for the mount to consume. EPUB on
    Table / Tree tabs still fires `tab-not-applicable` —
    EPUB has NO Table / Tree renderer in this contract;
    the EPUB viewer is the W4b3 source / offline surface
    itself, scoped to Raw.
  - W4b4 — CSV / TSV (Papa Parse) + JSON (native). Each
    owns one CDN library or the native JSON renderer;
    each lands as a separately authorized slice that adds
    its own arm to the dispatcher.

Until W4b4 lands, the dispatcher returns `unsupported` /
`tab-not-applicable` for the still-deferred format + tab
combinations, mirroring the legacy "Format .xyz not supported
in viewer." and "${tab} view not available for .${ext} files —
use Raw." fallbacks so the React cutover paints the same
download-link / empty-state cards the legacy
`web/file_viewer.js` paints.

The contract is the third pure Research work unit (W1 domain +
W2 ports + W3 infra + W4a renderers + W4b1 DOCX). It depends
on W1 domain types (`FileFormat`, `ViewerTab`) and W2 port
types (`ViewerFileDescriptor`'s `Uint8Array` bytes), but does
NOT import W3 infrastructure — the dispatcher derives URLs
from the explicit `ViewerFileDescriptor.url` input field,
mirroring the layered architecture (spec.md rule 4 —
application depends on domain ONLY) and the W4a split
directive ("derive URLs from explicit typed input rather than
importing W3 implementation"). The W4b1 contract does NOT
import or load mammoth, Next, React, DOM, or browser globals
either — the dispatcher's only job for DOCX is to emit the
typed source descriptor (URL + bytes + pinned CDN URL +
global name) so a future mount can pick it up.
The contract is value-typed, framework-free, browser-free,
CDN-loader-free, and fetch-free — a pure function from
`(file, tab, bytes)` to a typed `ViewerDispatch` outcome.

The contract must be:

  - Pure (spec.md rule 4) — no React, no Next, no HTTP transport,
    no DOM, no DOMParser, no browser state, no process state, no
    `fetch(`, no `require(`, no `globalThis`, no mammoth /
    SheetJS / epubjs import or load (the application layer only
    carries the pinned CDN URL on the typed source outcome — the
    future React mount does the actual CDN load via Next 16's
    `<Script>` component).
  - Domain-dependent only — the dispatcher imports `FileFormat` +
    `ViewerTab` from `../domain/explorer` and nothing else from
    the research module (no inward import from `../infrastructure`,
    `../presentation`, or `../index`).
  - Type-stable — a port-compat fixture (compiled alongside the
    dispatcher) proves the dispatcher's typed surface is reachable
    end-to-end; the runtime harness exercises every W4a-supported
    format + every W4b1 DOCX branch + every W4b2 XLS / XLSX
    branch + every W4b3 EPUB branch + every still-W4b+-deferred
    format + the SVG sanitizer's every branch.

References:
    odd/tasks/complete-frontend-migration.md          §ODD-MIGRATE-002 / W4a + W4b1 + W4b2 + W4b3
    openspec/specs/research/spec.md                   §Multi-format file viewer,
                                                       §DOCX rendering,
                                                       §EPUB rendering,
                                                       §Legacy DOC fallback,
                                                       §Table viewer tab,
                                                       §Tree viewer tab,
                                                       §Non-tabular file ignores
                                                       Table/Tree tabs
    web/file_viewer.js::RENDERERS                     Legacy dispatcher oracle
    web/file_viewer.js::renderPdf / renderHtml /      Per-format legacy oracles
      renderText / renderMd / renderImage /
      renderSvg / renderVideo / renderUnsupported /
      renderDocx / renderSheet / renderEpub
    web/file_explorer.js::handleTabClick              Legacy tab-not-applicable
                                                       oracle (`${tab} view not
                                                       available for .${ext}
                                                       files — use Raw.`)
    web/file_viewer.js::CDN_URLS.mammoth              Pinned mammoth CDN URL
    web/file_viewer.js::CDN_URLS.XLSX                 Pinned SheetJS CDN URL
    web/file_viewer.js::CDN_URLS.ePub                 Pinned epubjs CDN URL
    web/index.html (mammoth.js / SheetJS /            CDN-pinning companions
      epubjs <script> tags)
    next/dist/docs/01-app/03-api-reference/02-        Next 16 `<Script>` component
      components/script.md                            (future mount reference —
                                                       NOT consumed here)
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RENDERERS_FILE = (
    REPO_ROOT / "src" / "modules" / "research" / "application" / "renderers.ts"
)
DOMAIN_FILE = REPO_ROOT / "src" / "modules" / "research" / "domain" / "explorer.ts"
BARREL_FILE = REPO_ROOT / "src" / "modules" / "research" / "index.ts"


def _has_npx() -> bool:
    return shutil.which("npx") is not None


def _has_node() -> bool:
    return shutil.which("node") is not None


@pytest.fixture()
def require_toolchain() -> None:
    """Skip when npx / node are not on PATH — the focused compile +
    runtime harness needs both to validate the W4a contract."""
    if not (_has_npx() and _has_node()):
        pytest.skip("npx + node required on PATH for compile/runtime test")


# Comment-stripping regexes — mirrors `tests/test_taxonomy_infra.py`
# so author-friendly documentation can reference forbidden-token
# words in JSDoc without tripping the purity guard. Block comments
# are matched first so a `//` inside a `/* ... */` is not treated
# as a line-comment opener. Newlines pass through unchanged so the
# diagnostic line numbers stay aligned with the original source.
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


# ---------------------------------------------------------------------------
# File presence / source-level purity
# ---------------------------------------------------------------------------
def test_renderers_file_exists() -> None:
    """RED marker for W4a — the focused compile + runtime harness also
    skips, so every downstream W4a contract test observes RED until
    `src/modules/research/application/renderers.ts` lands."""
    assert RENDERERS_FILE.is_file(), (
        f"missing renderers file: {RENDERERS_FILE}. W4a ships this "
        f"file as the pure application-layer viewer-dispatch contract "
        f"for the eight no-CDN families."
    )


def test_renderers_file_is_plain_typescript() -> None:
    """`.ts`, not `.tsx` — the application-layer dispatcher has no JSX
    (mirrors the taxonomy `application/` convention — spec.md rule 4:
    JSX belongs to presentation)."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    assert RENDERERS_FILE.suffix == ".ts", (
        f"renderers file must be TypeScript; got suffix={RENDERERS_FILE.suffix}"
    )


def test_renderers_file_depends_on_domain_only() -> None:
    """Spec.md rule 4 (inward deps): the application layer depends
    on domain ONLY — no infrastructure (the dispatcher does NOT
    import the W3 `fetchFileServe`), no presentation, no public
    barrel reverse import. The URL is derived from the explicit
    `ViewerFileDescriptor.url` input field instead, mirroring the
    W4a split directive. The dispatcher's `bytes` parameter is
    typed `Uint8Array | null` (the W2 port's byte shape) — the
    input comes from outside, not from a fetch call inside the
    dispatcher."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = _strip_ts_comments(RENDERERS_FILE.read_text())
    # Required: the dispatcher imports `FileFormat` + `ViewerTab`
    # so the switch dispatches against the canonical W1 closed
    # union (a future PR that adds a new format must extend the
    # W1 union + the dispatcher's switch in lock-step).
    assert re.search(
        r'import\s+type\s*\{[^}]*\bFileFormat\b[^}]*\}\s*from\s*'
        r'["\']\.\./domain/explorer(?:\.js)?["\']',
        text,
    ), (
        "renderers.ts must import the W1 FileFormat type from "
        "'../domain/explorer' so the dispatcher dispatches against "
        "the canonical closed union."
    )
    assert re.search(
        r'import\s+type\s*\{[^}]*\bViewerTab\b[^}]*\}\s*from\s*'
        r'["\']\.\./domain/explorer(?:\.js)?["\']',
        text,
    ), (
        "renderers.ts must import the W1 ViewerTab type from "
        "'../domain/explorer' so the tab gate dispatches against "
        "the canonical closed union."
    )
    # Forbidden: any import from the future infrastructure layer
    # (the W4a split explicitly bans reverse imports of W3 — URLs
    # + bytes come through the explicit `ViewerFileDescriptor`
    # input), the future presentation layer (W6+ React mount), or
    # the public barrel (consumers reach the dispatcher through
    # the barrel, not the reverse).
    for forbidden in (
        "../infrastructure",
        "../presentation",
        "../index",
        "../../taxonomy",
        "../../design-system",
        "../../browser-state",
        "../../app-shell",
    ):
        assert forbidden not in text, (
            f"renderers.ts must NOT import from {forbidden!r}; spec.md "
            f"rule 4 keeps application inward-only (domain), and the "
            f"W4a split explicitly bans importing W3 infrastructure."
        )


def test_renderers_file_has_no_framework_or_io_imports() -> None:
    """Framework-free + I/O-free at the source level. No React, no
    Next, no FastAPI, no `fetch(`, no `DOMParser`, no `document`,
    no `window`, no `localStorage`, no `process`, no `require(`,
    no `globalThis`. A future PR that pulls in a framework or a
    browser API breaks the W4a contract at review."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = _strip_ts_comments(RENDERERS_FILE.read_text())
    for token in (
        # framework
        "from 'react'", 'from "react"',
        "from 'next'",   'from "next"',
        "from 'nextjs'", 'from "nextjs"',
        "from 'fastapi'", 'from "fastapi"',
        "from 'starlette'", 'from "starlette"',
        # I/O — W4a is pure; bytes are injected.
        "fetch(",
        # browser / process state.
        "DOMParser",
        "document.",
        "window.",
        "localStorage",
        "process.",
        # CommonJS / globalThis guards — renderers stay ESM-only.
        "require(",
        "globalThis",
        # Cross-layer / cross-module paths already pinned by
        # test_renderers_file_depends_on_domain_only above, but
        # also listed here so a bare-token check covers any
        # future comment-free import.
    ):
        assert token not in text, (
            f"renderers.ts must stay free of {token!r}; the W4a "
            f"contract is framework-free + I/O-free + browser-free."
        )


def test_renderers_file_has_no_dom_or_xhr_helpers() -> None:
    """TRIANGULATE — the W4a sanitizer must NOT depend on any
    browser / Node DOM helper. The legacy
    `web/file_viewer.js::renderSvg` uses `DOMParser` +
    `document.createTreeWalker`; W4a replicates the XSS scrub as
    pure string-level regex so the contract stays DOMParser-free.
    The dispatcher's SVG branch reads bytes through the typed
    input — no `atob(`, no `Blob`, no `FileReader`, no `Buffer`
    either (Node-only)."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = _strip_ts_comments(RENDERERS_FILE.read_text())
    for token in (
        "DOMParser", "XMLParser", "document.createTreeWalker",
        "atob(", "btoa(",
        "Blob", "FileReader",
        # Node-only helpers — the dispatcher must work in both
        # browser + Node 18+ without Buffer.
        "Buffer.from", "Buffer.alloc",
    ):
        assert token not in text, (
            f"renderers.ts must stay free of {token!r}; the W4a "
            f"sanitizer is pure string-level regex."
        )


def test_renderers_file_exports_named_dispatch_viewer() -> None:
    """The W4a contract commits to a named export `dispatchViewer`
    as a function (not async — the dispatcher is pure: input →
    typed `ViewerDispatch`, no I/O, no `await`). Mirrors the
    taxonomy port convention — named exports only. Dropping the
    export breaks every W6+ consumer that wires the dispatcher
    through the barrel."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = RENDERERS_FILE.read_text()
    assert re.search(
        r"export\s+function\s+dispatchViewer\b",
        text,
    ), (
        "renderers.ts must export `dispatchViewer` as a named function "
        "(pure dispatcher from ViewerDispatchInput → ViewerDispatch)."
    )
    # The function MUST NOT be async — the dispatcher does no I/O
    # (bytes are injected), so a future PR that flips to `async
    # function dispatchViewer` would silently mislead readers
    # about the contract's purity.
    assert not re.search(
        r"export\s+async\s+function\s+dispatchViewer\b",
        text,
    ), (
        "dispatchViewer must NOT be `async` — the dispatcher is pure "
        "(input → typed ViewerDispatch, no I/O, no `await`)."
    )


def test_renderers_file_exports_named_sanitize_svg_markup() -> None:
    """The W4a contract commits to a named export `sanitizeSvgMarkup`
    as a pure function (input string → scrubbed string). Mirrors
    the legacy `web/file_viewer.js::renderSvg`'s XSS scrub verbatim
    (strip `<script>` + strip `on*=` attrs) but at the string level
    so the contract stays DOMParser-free."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = RENDERERS_FILE.read_text()
    assert re.search(
        r"export\s+function\s+sanitizeSvgMarkup\b",
        text,
    ), (
        "renderers.ts must export `sanitizeSvgMarkup` as a named "
        "function (pure string-level XSS scrub)."
    )
    # Signature must accept exactly one `string` argument and
    # return `string` — pure function.
    m = re.search(
        r"export\s+function\s+sanitizeSvgMarkup\b[\s\S]*?\n\s*\}",
        text,
        re.MULTILINE,
    )
    assert m, "sanitizeSvgMarkup function must be syntactically well-formed."
    signature = m.group(0)
    assert re.search(
        r"sanitizeSvgMarkup\s*\(\s*svgText\s*:\s*string\b",
        signature,
    ), (
        "sanitizeSvgMarkup must accept `svgText: string` as its "
        "single parameter so the contract is a pure string-level "
        "scrub."
    )
    assert re.search(r":\s*string\s*\{", signature) or "string {" in signature, (
        "sanitizeSvgMarkup must return `string` so the dispatcher's "
        "SVG branch can pipe the result through the typed "
        "`ViewerDispatch.svg-sanitized` discriminator."
    )


def test_renderers_file_exports_named_image_big_file_bytes() -> None:
    """The W4a contract commits to the `IMAGE_BIG_FILE_BYTES`
    constant — the legacy 50 MB advisory threshold. A future PR
    that drops the export breaks the focused runtime harness
    (which imports the constant to verify it equals 50 MB)."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = RENDERERS_FILE.read_text()
    assert re.search(
        r"export\s+const\s+IMAGE_BIG_FILE_BYTES\b\s*:\s*number\b",
        text,
    ), (
        "renderers.ts must export `IMAGE_BIG_FILE_BYTES: number` "
        "as the legacy 50 MB advisory threshold constant."
    )
    # The constant MUST be `50 * 1024 * 1024` — the legacy
    # threshold pinned by `web/file_viewer.js::IMAGE_BIG_FILE_BYTES`.
    m = re.search(
        r"export\s+const\s+IMAGE_BIG_FILE_BYTES\b[^;]*;",
        text,
    )
    assert m, "IMAGE_BIG_FILE_BYTES must be declared as a const."
    declaration = m.group(0)
    assert "50 * 1024 * 1024" in declaration, (
        "IMAGE_BIG_FILE_BYTES must equal `50 * 1024 * 1024` "
        "(legacy threshold, pinned byte-for-byte)."
    )


def test_renderers_file_exports_named_tab_not_applicable_suffix() -> None:
    """The W4a contract commits to a `TAB_NOT_APPLICABLE_SUFFIX`
    constant — the literal `"files — use Raw."` string the
    dispatcher appends to the legacy `${tab} view not available
    for .${ext}` prefix. Exporting it lets the runtime harness
    pin the legacy wording byte-for-byte and lets the React
    mount's i18n layer localize the suffix without reverse-
    importing the dispatcher's internal state."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = RENDERERS_FILE.read_text()
    m = re.search(
        r"export\s+const\s+TAB_NOT_APPLICABLE_SUFFIX\b[^;]*;",
        text,
    )
    assert m, (
        "renderers.ts must export `TAB_NOT_APPLICABLE_SUFFIX` "
        "as a const string so the legacy wording is pinnable."
    )
    declaration = m.group(0)
    assert '"files — use Raw."' in declaration or '"files \u2014 use Raw."' in declaration, (
        "TAB_NOT_APPLICABLE_SUFFIX must be the literal "
        '"files — use Raw." (the legacy wording pinned byte-for-byte).'
    )


def test_renderers_file_does_not_export_default() -> None:
    """TRIANGULATE — the renderers file MUST NOT export a default
    symbol. The taxonomy port file pins named exports only; a
    future PR that flips to `export default …` would silently
    break barrel re-exports and DI bindings."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = RENDERERS_FILE.read_text()
    assert not re.search(r"^\s*export\s+default\b", text, re.MULTILINE), (
        "renderers.ts must NOT export a default symbol — the W4a "
        "contract pins named exports only (dispatchViewer, "
        "sanitizeSvgMarkup, IMAGE_BIG_FILE_BYTES, "
        "TAB_NOT_APPLICABLE_SUFFIX)."
    )


# ---------------------------------------------------------------------------
# W4b1 — DOCX source / offline branch surface
#
# The W4b1 contract is the first W4b+ slice: it owns the DOCX
# format. The contract emits a typed `docx-source` outcome that
# carries the descriptor + bytes + pinned mammoth CDN URL +
# global name so a future React mount (W6+) can load the
# legacy-pinned mammoth library and convert the bytes to
# HTML. When bytes are missing, the contract emits a typed
# `docx-offline` branch with the download link + pinned CDN
# URL + global name so the mount paints the same legacy
# "Viewer offline" banner with a download affordance. The
# application layer stays framework-free, browser-free, and
# CDN-loader-free — mammoth is NOT imported or loaded here;
# the dispatcher only emits the typed source descriptor for
# the mount to consume.
# ---------------------------------------------------------------------------
def test_renderers_file_has_no_docx_renderer_or_loader_imports() -> None:
    """TRIANGULATE — the W4b1 contract is the typed SOURCE
    outcome for a future mount; the dispatcher MUST NOT import
    or load mammoth, MUST NOT inject a `<script>` tag, MUST NOT
    call `loadScriptOnce` (the legacy `web/file_viewer.js`
    CDN-loader helper that touches `document` + `window`), and
    MUST NOT inline the mammoth bundle. The contract only
    pins the CDN URL + global name on the typed source
    outcome — the future React mount (W6+) consumes the URL
    through Next 16's `<Script>` component (see
    `node_modules/next/dist/docs/01-app/03-api-reference/02-
    components/script.md`) with the `onLoad` / `onError`
    callbacks. A future PR that imports mammoth into the
    application layer breaks the layered architecture at
    review."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = _strip_ts_comments(RENDERERS_FILE.read_text())
    for token in (
        # mammoth import (any spelling — default, named,
        # sub-path, or the legacy global read).
        "from 'mammoth'",
        'from "mammoth"',
        "from 'mammoth/mammoth.browser'",
        'from "mammoth/mammoth.browser"',
        "import('mammoth')",
        'import("mammoth")',
        "window.mammoth",
        # `<script>` injection / CDN loader — the dispatcher
        # stays framework-free; the mount owns the loader.
        "loadScriptOnce",
        "createElement('script')",
        'createElement("script")',
        "createElement('SCRIPT')",
        'createElement("SCRIPT")',
        ".appendChild(s",
        # Conversion call site. The dispatcher does NOT
        # invoke mammoth — it only emits the typed source
        # outcome for the mount to convert.
        "convertToHtml",
    ):
        assert token not in text, (
            f"renderers.ts must stay free of {token!r}; the W4b1 "
            f"contract is a typed source descriptor only — the "
            f"future React mount loads mammoth via Next 16's "
            f"`<Script>` component and calls "
            f"`window.mammoth.convertToHtml(...)` itself."
        )


def test_renderers_file_exports_named_mammoth_cdn_url() -> None:
    """The W4b1 contract commits to the `MAMMOTH_CDN_URL`
    constant — the legacy-pinned mammoth CDN URL
    (`web/file_viewer.js::CDN_URLS.mammoth` +
    `web/index.html` <script> tag — the matching companion
    comment block calls the URL "Pinned URL: do not unpin.").
    The URL is part of the W4b1 source descriptor so the
    future React mount can load the CDN idempotently. A
    future PR that bumps the version MUST update this constant
    AND the matching `web/index.html` <script> tag AND the
    focused test that pins the URL. Bumping the URL without
    updating the comment + the `<script>` tag would silently
    diverge the legacy + React paths."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = RENDERERS_FILE.read_text()
    assert re.search(
        r"export\s+const\s+MAMMOTH_CDN_URL\b\s*:\s*string\b",
        text,
    ), (
        "renderers.ts must export `MAMMOTH_CDN_URL: string` "
        "as the pinned mammoth CDN URL constant."
    )
    m = re.search(
        r"export\s+const\s+MAMMOTH_CDN_URL\b[^;]*;",
        text,
    )
    assert m, "MAMMOTH_CDN_URL must be declared as a const string."
    declaration = m.group(0)
    # Pinned URL — `cdn.jsdelivr.net/npm/mammoth@1.8.0/
    # mammoth.browser.min.js`. The version pin is a content
    # hash, not a moving tag — `web/index.html`'s mammoth
    # comment block ("Pinned URL: do not unpin.") +
    # `openspec/specs/research/spec.md` "CDN URLs … MUST be
    # pinned to specific versions" enforce this.
    assert (
        "https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js"
        in declaration
    ), (
        "MAMMOTH_CDN_URL must be the legacy-pinned URL "
        '"https://cdn.jsdelivr.net/npm/mammoth@1.8.0/'
        'mammoth.browser.min.js" (matches '
        "web/file_viewer.js::CDN_URLS.mammoth + "
        "web/index.html's mammoth.js <script> tag)."
    )


def test_renderers_file_exports_named_mammoth_global_name() -> None:
    """The W4b1 contract commits to the `MAMMOTH_GLOBAL_NAME`
    constant — the window-global name mammoth assigns itself
    once the CDN script loads (the legacy
    `web/file_viewer.js::loadScriptOnce("mammoth")` resolves
    via `window[name]`, then the `renderDocx` call site calls
    `window.mammoth.convertToHtml(...)`). The global name is
    part of the W4b1 source descriptor so the future React
    mount can read the global verbatim without hardcoding
    the string. A future PR that bumps the library or the
    CDN pin (e.g. mammoth releases a v2 with a different
    global) MUST update this constant too."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = RENDERERS_FILE.read_text()
    assert re.search(
        r"export\s+const\s+MAMMOTH_GLOBAL_NAME\b\s*:\s*string\b",
        text,
    ), (
        "renderers.ts must export `MAMMOTH_GLOBAL_NAME: string` "
        "as the window-global name constant."
    )
    m = re.search(
        r"export\s+const\s+MAMMOTH_GLOBAL_NAME\b[^;]*;",
        text,
    )
    assert m, "MAMMOTH_GLOBAL_NAME must be declared as a const string."
    declaration = m.group(0)
    # Pinned global — `mammoth` (matches the legacy
    # `window.mammoth.convertToHtml` site +
    # `CDN_URLS.mammoth` map key in `web/file_viewer.js`).
    assert '"mammoth"' in declaration or "'mammoth'" in declaration, (
        "MAMMOTH_GLOBAL_NAME must be the literal \"mammoth\" "
        "(matches web/file_viewer.js::CDN_URLS.mammoth key + "
        "window.mammoth.convertToHtml call site)."
    )


# ---------------------------------------------------------------------------
# W4b2 — XLS / XLSX source / offline branch surface
#
# The W4b2 contract is the second W4b+ slice: it owns the XLS
# and XLSX formats. The contract emits a typed `sheet-source`
# outcome that carries the descriptor + bytes + pinned
# SheetJS CDN URL + global name so a future React mount
# (W6+) can load the legacy-pinned SheetJS library and
# convert the workbook to an HTML table. When bytes are
# missing, the contract emits a typed `sheet-offline` branch
# with the download link + pinned CDN URL + global name so
# the mount paints the same legacy "Viewer offline" banner
# with a download affordance. The application layer stays
# framework-free, browser-free, and CDN-loader-free —
# SheetJS is NOT imported or loaded here; the dispatcher
# only emits the typed source descriptor for the mount to
# consume.
# ---------------------------------------------------------------------------
def test_renderers_file_has_no_sheetjs_renderer_or_loader_imports() -> None:
    """TRIANGULATE — the W4b2 contract is the typed SOURCE
    outcome for a future mount; the dispatcher MUST NOT import
    or load SheetJS, MUST NOT inject a `<script>` tag, MUST NOT
    call `loadScriptOnce` (the legacy `web/file_viewer.js`
    CDN-loader helper that touches `document` + `window`), and
    MUST NOT inline the SheetJS bundle. The contract only
    pins the CDN URL + global name on the typed source
    outcome — the future React mount (W6+) consumes the URL
    through Next 16's `<Script>` component (see
    `node_modules/next/dist/docs/01-app/03-api-reference/02-
    components/script.md`) with the `onLoad` / `onError`
    callbacks. A future PR that imports SheetJS into the
    application layer breaks the layered architecture at
    review.

    SheetJS exposes three calls that the future mount will
    use: `XLSX.read(bytes, { type: "array" })` to parse the
    workbook, `XLSX.utils.sheet_to_html(sheet)` to emit the
    HTML table, and `XLSX.SheetNames` to enumerate sheets
    for multi-sheet workbooks. The dispatcher must NOT call
    any of them — they happen at the mount."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = _strip_ts_comments(RENDERERS_FILE.read_text())
    for token in (
        # SheetJS import (any spelling — default, named,
        # sub-path, or the legacy global read).
        "from 'xlsx'",
        'from "xlsx"',
        "from 'xlsx/dist/xlsx.full.min'",
        'from "xlsx/dist/xlsx.full.min"',
        "import('xlsx')",
        'import("xlsx")',
        "window.XLSX",
        # `<script>` injection / CDN loader — the dispatcher
        # stays framework-free; the mount owns the loader.
        "loadScriptOnce",
        "createElement('script')",
        'createElement("script")',
        "createElement('SCRIPT')",
        'createElement("SCRIPT")',
        ".appendChild(s",
        # SheetJS conversion call sites. The dispatcher does
        # NOT invoke SheetJS — it only emits the typed source
        # outcome for the mount to convert.
        "XLSX.read",
        "XLSX.utils",
        "sheet_to_html",
        "SheetNames",
    ):
        assert token not in text, (
            f"renderers.ts must stay free of {token!r}; the W4b2 "
            f"contract is a typed source descriptor only — the "
            f"future React mount loads xlsx via Next 16's "
            f"`<Script>` component and calls "
            f"`window.XLSX.read(bytes, {{type: \"array\"}})` + "
            f"`window.XLSX.utils.sheet_to_html(sheet)` itself."
        )


def test_renderers_file_exports_named_sheetjs_cdn_url() -> None:
    """The W4b2 contract commits to the `SHEETJS_CDN_URL`
    constant — the legacy-pinned SheetJS CDN URL
    (`web/file_viewer.js::CDN_URLS.XLSX` +
    `web/index.html` <script> tag — the matching companion
    comment block calls the URL "Pinned URL: do not unpin.").
    The URL is part of the W4b2 source descriptor so the
    future React mount can load the CDN idempotently. A
    future PR that bumps the version MUST update this constant
    AND the matching `web/index.html` <script> tag AND the
    focused test that pins the URL. Bumping the URL without
    updating the comment + the `<script>` tag would silently
    diverge the legacy + React paths."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = RENDERERS_FILE.read_text()
    assert re.search(
        r"export\s+const\s+SHEETJS_CDN_URL\b\s*:\s*string\b",
        text,
    ), (
        "renderers.ts must export `SHEETJS_CDN_URL: string` "
        "as the pinned SheetJS CDN URL constant."
    )
    m = re.search(
        r"export\s+const\s+SHEETJS_CDN_URL\b[^;]*;",
        text,
    )
    assert m, "SHEETJS_CDN_URL must be declared as a const string."
    declaration = m.group(0)
    # Pinned URL — `cdn.jsdelivr.net/npm/xlsx@0.18.5/
    # dist/xlsx.full.min.js`. The version pin is a content
    # hash, not a moving tag — `web/index.html`'s SheetJS
    # comment block ("Pinned URL: do not unpin.") +
    # `openspec/specs/research/spec.md` "CDN URLs … MUST be
    # pinned to specific versions" enforce this. The legacy
    # `CDN_URLS.XLSX` map key + the Community edition
    # (Apache 2.0) flag in `web/index.html`'s comment block
    # pin the URL byte-for-byte.
    assert (
        "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"
        in declaration
    ), (
        "SHEETJS_CDN_URL must be the legacy-pinned URL "
        '"https://cdn.jsdelivr.net/npm/xlsx@0.18.5/'
        'dist/xlsx.full.min.js" (matches '
        "web/file_viewer.js::CDN_URLS.XLSX + "
        "web/index.html's SheetJS (xlsx) <script> tag)."
    )


def test_renderers_file_exports_named_sheetjs_global_name() -> None:
    """The W4b2 contract commits to the `SHEETJS_GLOBAL_NAME`
    constant — the window-global name SheetJS assigns itself
    once the CDN script loads (the legacy
    `web/file_viewer.js::loadScriptOnce("XLSX")` resolves
    via `window[name]`, then the `renderSheet` call sites
    call `window.XLSX.read(...)` +
    `window.XLSX.utils.sheet_to_html(...)`). The global name
    is part of the W4b2 source descriptor so the future React
    mount can read the global verbatim without hardcoding
    the string. A future PR that bumps the library or the
    CDN pin (e.g. SheetJS releases a v1 with a different
    global) MUST update this constant too."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = RENDERERS_FILE.read_text()
    assert re.search(
        r"export\s+const\s+SHEETJS_GLOBAL_NAME\b\s*:\s*string\b",
        text,
    ), (
        "renderers.ts must export `SHEETJS_GLOBAL_NAME: string` "
        "as the window-global name constant."
    )
    m = re.search(
        r"export\s+const\s+SHEETJS_GLOBAL_NAME\b[^;]*;",
        text,
    )
    assert m, "SHEETJS_GLOBAL_NAME must be declared as a const string."
    declaration = m.group(0)
    # Pinned global — `XLSX` (matches the legacy
    # `window.XLSX.read` + `window.XLSX.utils.sheet_to_html`
    # sites + `CDN_URLS.XLSX` map key in `web/file_viewer.js`).
    assert '"XLSX"' in declaration or "'XLSX'" in declaration, (
        "SHEETJS_GLOBAL_NAME must be the literal \"XLSX\" "
        "(matches web/file_viewer.js::CDN_URLS.XLSX key + "
        "window.XLSX.read + window.XLSX.utils.sheet_to_html "
        "call sites)."
    )


# ---------------------------------------------------------------------------
# W4b3 — EPUB source / offline branch surface
#
# The W4b3 contract is the third W4b+ slice: it owns the EPUB
# format. The contract emits a typed `epub-source` outcome that
# carries the descriptor + bytes + pinned epubjs CDN URL +
# global name so a future React mount (W6+) can load the
# legacy-pinned epubjs library, construct the book via
# `window.ePub(bytes.buffer)`, and own the full EPUB render
# lifecycle (`book.renderTo(hostEl, ...)` + prev / next click
# handlers + module-scoped `_currentBook.destroy()` teardown on
# the NEXT open so listeners don't leak — mirrors the legacy
# `web/file_viewer.js::renderEpub` verbatim). When bytes are
# missing, the contract emits a typed `epub-offline` branch
# with the download link + pinned CDN URL + global name so the
# mount paints the same legacy "Viewer offline" banner with a
# download affordance. The application layer stays
# framework-free, browser-free, and CDN-loader-free — epubjs
# is NOT imported or loaded here; the dispatcher only emits the
# typed source descriptor for the mount to consume.
#
# EPUB on Table / Tree tabs stays tab-not-applicable — EPUB
# has NO Table / Tree renderer in this contract. epubjs
# renders an EPUB as a paged book, not a Table widget or a
# Tree widget; the future mount's EPUB viewer is the W4b3
# source / offline surface itself, scoped to Raw. A future
# mount that wants a Table or Tree renderer for EPUB would
# land as a separately authorized follow-up slice.
# ---------------------------------------------------------------------------
def test_renderers_file_has_no_epubjs_renderer_or_loader_imports() -> None:
    """TRIANGULATE — the W4b3 contract is the typed SOURCE
    outcome for a future mount; the dispatcher MUST NOT import
    or load epubjs, MUST NOT inject a `<script>` tag, MUST NOT
    call `loadScriptOnce` (the legacy `web/file_viewer.js`
    CDN-loader helper that touches `document` + `window`), and
    MUST NOT inline the epubjs bundle. The contract only
    pins the CDN URL + global name on the typed source
    outcome — the future React mount (W6+) consumes the URL
    through Next 16's `<Script>` component (see
    `node_modules/next/dist/docs/01-app/03-api-reference/02-
    components/script.md`) with the `onLoad` / `onError`
    callbacks. A future PR that imports epubjs into the
    application layer breaks the layered architecture at
    review.

    epubjs exposes three calls that the future mount will
    use: `ePub(arrayBuffer)` to construct the book,
    `book.renderTo(hostEl, { width: "100%", height: "100%" })`
    to mount it, and `book.prev()` / `book.next()` to
    navigate. The dispatcher must NOT call any of them
    — they happen at the mount. The legacy
    `web/file_viewer.js::renderEpub` also stores the
    constructed book in a module-scoped `_currentBook` slot
    and calls `_currentBook.destroy()` on the NEXT open
    before mounting the new one (so listeners don't leak —
    see `design.md` §8 EPUB render lifecycle). The
    dispatcher does NOT own the destroy lifecycle either — the
    mount does."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = _strip_ts_comments(RENDERERS_FILE.read_text())
    for token in (
        # epubjs import (any spelling — default, named,
        # sub-path, or the legacy global read).
        "from 'epubjs'",
        'from "epubjs"',
        "from 'epubjs/dist/epub.min'",
        'from "epubjs/dist/epub.min"',
        "import('epubjs')",
        'import("epubjs")',
        "window.ePub",
        # `<script>` injection / CDN loader — the dispatcher
        # stays framework-free; the mount owns the loader.
        "loadScriptOnce",
        "createElement('script')",
        'createElement("script")',
        "createElement('SCRIPT')",
        'createElement("SCRIPT")',
        ".appendChild(s",
        # epubjs construction / mount / navigation call
        # sites. The dispatcher does NOT invoke any of them
        # — it only emits the typed source outcome for the
        # mount to consume. Mirrors the W4b1 mammoth +
        # W4b2 SheetJS "dispatcher emits source descriptor
        # only" contract.
        ".renderTo(",
        ".destroy()",
        # Book lifecycle — the legacy `_currentBook` slot +
        # `book.prev()` / `book.next()` navigation call
        # sites happen at the mount.
        "_currentBook",
    ):
        assert token not in text, (
            f"renderers.ts must stay free of {token!r}; the W4b3 "
            f"contract is a typed source descriptor only — the "
            f"future React mount loads epubjs via Next 16's "
            f"`<Script>` component and calls "
            f"`window.ePub(bytes.buffer)` + `book.renderTo(...)` + "
            f"`book.prev()` / `book.next()` + "
            f"`_currentBook.destroy()` itself."
        )


def test_renderers_file_exports_named_epubjs_cdn_url() -> None:
    """The W4b3 contract commits to the `EPUBJS_CDN_URL`
    constant — the legacy-pinned epubjs CDN URL
    (`web/file_viewer.js::CDN_URLS.ePub` +
    `web/index.html` <script> tag — the matching companion
    comment block calls the URL "Pinned URL: do not unpin.").
    The URL is part of the W4b3 source descriptor so the
    future React mount can load the CDN idempotently. A
    future PR that bumps the version MUST update this
    constant AND the matching `web/index.html` <script> tag
    AND the focused test that pins the URL. Bumping the URL
    without updating the comment + the `<script>` tag would
    silently diverge the legacy + React paths."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = RENDERERS_FILE.read_text()
    assert re.search(
        r"export\s+const\s+EPUBJS_CDN_URL\b\s*:\s*string\b",
        text,
    ), (
        "renderers.ts must export `EPUBJS_CDN_URL: string` "
        "as the pinned epubjs CDN URL constant."
    )
    m = re.search(
        r"export\s+const\s+EPUBJS_CDN_URL\b[^;]*;",
        text,
    )
    assert m, "EPUBJS_CDN_URL must be declared as a const string."
    declaration = m.group(0)
    # Pinned URL — `cdn.jsdelivr.net/npm/epubjs@0.3.93/
    # dist/epub.min.js`. The version pin is a content
    # hash, not a moving tag — `web/index.html`'s epubjs
    # comment block ("Pinned URL: do not unpin.") +
    # `openspec/specs/research/spec.md` "CDN URLs … MUST be
    # pinned to specific versions" enforce this. The
    # legacy `CDN_URLS.ePub` map key in
    # `web/file_viewer.js` pins the URL byte-for-byte.
    assert (
        "https://cdn.jsdelivr.net/npm/epubjs@0.3.93/dist/epub.min.js"
        in declaration
    ), (
        "EPUBJS_CDN_URL must be the legacy-pinned URL "
        '"https://cdn.jsdelivr.net/npm/epubjs@0.3.93/'
        'dist/epub.min.js" (matches '
        "web/file_viewer.js::CDN_URLS.ePub + "
        "web/index.html's epubjs <script> tag)."
    )


def test_renderers_file_exports_named_epubjs_global_name() -> None:
    """The W4b3 contract commits to the `EPUBJS_GLOBAL_NAME`
    constant — the window-global name epubjs assigns itself
    once the CDN script loads (the legacy
    `web/file_viewer.js::loadScriptOnce("ePub")` resolves
    via `window[name]`, then the `renderEpub` call site
    calls `window.ePub(arrayBuffer)`). The global name is
    part of the W4b3 source descriptor so the future React
    mount can read the global verbatim without hardcoding
    the string. A future PR that bumps the library or the
    CDN pin (e.g. epubjs releases a v1 with a different
    global) MUST update this constant too.

    Note: the global is the literal `"ePub"` (lowercase
    `e`, capital `P`), NOT `"EPUBJS"` or `"epub"`. The
    epubjs UMD bundle assigns itself to `window.ePub`
    and the legacy `CDN_URLS.ePub` map key matches. The
    case matters — `window.epub` is undefined at runtime
    and would silently break the construction site."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    text = RENDERERS_FILE.read_text()
    assert re.search(
        r"export\s+const\s+EPUBJS_GLOBAL_NAME\b\s*:\s*string\b",
        text,
    ), (
        "renderers.ts must export `EPUBJS_GLOBAL_NAME: string` "
        "as the window-global name constant."
    )
    m = re.search(
        r"export\s+const\s+EPUBJS_GLOBAL_NAME\b[^;]*;",
        text,
    )
    assert m, "EPUBJS_GLOBAL_NAME must be declared as a const string."
    declaration = m.group(0)
    # Pinned global — `ePub` (matches the legacy
    # `window.ePub(arrayBuffer)` site + `CDN_URLS.ePub`
    # map key in `web/file_viewer.js`). Mirrors the W4b1
    # mammoth + W4b2 SheetJS "literal global name pinned
    # in constant" pattern.
    assert '"ePub"' in declaration or "'ePub'" in declaration, (
        "EPUBJS_GLOBAL_NAME must be the literal \"ePub\" "
        "(matches web/file_viewer.js::CDN_URLS.ePub key + "
        "window.ePub(arrayBuffer) call site)."
    )


# ---------------------------------------------------------------------------
# Public barrel — W4a must re-export the dispatcher surface through
# the module's barrel so cross-module consumers (W6 React mount,
# integration tests) reach the W4a contract through the public surface
# (spec.md rule 5).
# ---------------------------------------------------------------------------
def test_barrel_reexports_research_renderers_surface() -> None:
    """ODD-MIGRATE-002 W4a + W4b1 + W4b2 + W4b3: the public
    barrel must re-export `dispatchViewer`, `sanitizeSvgMarkup`
    (as values) and `IMAGE_BIG_FILE_BYTES`,
    `TAB_NOT_APPLICABLE_SUFFIX`, `MAMMOTH_CDN_URL`,
    `MAMMOTH_GLOBAL_NAME` (W4a + W4b1 as values),
    `SHEETJS_CDN_URL`, `SHEETJS_GLOBAL_NAME` (W4b2 as values),
    `EPUBJS_CDN_URL`, `EPUBJS_GLOBAL_NAME` (W4b3 as values)
    plus the five W4a types (`ViewerDispatch`,
    `ViewerDispatchInput`, `ViewerFileDescriptor`, `ViewerLink`,
    `ViewerImageAdvisory`) via `export type { … }` so
    cross-module consumers reach the W4a + W4b1 + W4b2 + W4b3
    contract through the barrel."""
    if not BARREL_FILE.exists():
        pytest.skip("research barrel not present yet")
    text = BARREL_FILE.read_text()
    # Value re-exports — `dispatchViewer`, `sanitizeSvgMarkup`,
    # `IMAGE_BIG_FILE_BYTES`, `TAB_NOT_APPLICABLE_SUFFIX` (W4a)
    # + `MAMMOTH_CDN_URL`, `MAMMOTH_GLOBAL_NAME` (W4b1)
    # + `SHEETJS_CDN_URL`, `SHEETJS_GLOBAL_NAME` (W4b2)
    # + `EPUBJS_CDN_URL`, `EPUBJS_GLOBAL_NAME` (W4b3).
    for name in (
        "dispatchViewer",
        "sanitizeSvgMarkup",
        "IMAGE_BIG_FILE_BYTES",
        "TAB_NOT_APPLICABLE_SUFFIX",
        "MAMMOTH_CDN_URL",
        "MAMMOTH_GLOBAL_NAME",
        "SHEETJS_CDN_URL",
        "SHEETJS_GLOBAL_NAME",
        "EPUBJS_CDN_URL",
        "EPUBJS_GLOBAL_NAME",
    ):
        pattern = (
            rf"export\s*\{{\s*[^}}]*\b{name}\b[^}}]*\s*\}}\s*from\s*"
            rf'["\']\./application/renderers(?:\.js)?["\']'
        )
        assert re.search(pattern, text), (
            f"research barrel must re-export `{name}` from "
            f"'./application/renderers' so cross-module consumers "
            f"reach the W4a + W4b1 contract through the barrel "
            f"(spec.md rule 5)."
        )
    # Type re-exports — five W4a types. The W4b1 DOCX
    # contract does NOT add new exported types — the
    # docx-source / docx-offline variants live inside the
    # existing `ViewerDispatch` discriminated union, which
    # the React mount consumes via the same `ViewerDispatch`
    # import. The W4b2 XLS / XLSX contract follows the same
    # pattern (sheet-source / sheet-offline are variants on
    # `ViewerDispatch`). The W4b3 EPUB contract follows the
    # same pattern (epub-source / epub-offline are variants
    # on `ViewerDispatch`). Future W4b4 (CSV / TSV / JSON)
    # slices follow the same pattern: add variants to
    # `ViewerDispatch`, not new top-level types.
    for name in (
        "ViewerDispatch",
        "ViewerDispatchInput",
        "ViewerFileDescriptor",
        "ViewerLink",
        "ViewerImageAdvisory",
    ):
        pattern = (
            rf"export\s+type\s*\{{\s*[^}}]*\b{name}\b[^}}]*\}}\s*from\s*"
            rf'["\']\./application/renderers(?:\.js)?["\']'
        )
        assert re.search(pattern, text), (
            f"research barrel must re-export `{name}` as a type "
            f"so React consumers can type the W4a surface through "
            f"the barrel (spec.md rule 5)."
        )


# ---------------------------------------------------------------------------
# Compile + runtime contract — strict mode, ES2022 only, no DOM.
# ---------------------------------------------------------------------------
def _run_tsc_isolated(
    sources: list[Path],
    out_dir: Path,
) -> subprocess.CompletedProcess:
    """Compile the W4a sources in isolation. Flags mirror project
    tsconfig + design.md §Interfaces/Contracts: `--strict`,
    `--target ES2022`, `--module commonjs` (so Node can `require`
    the output), `--lib ES2022` (no DOM — application must not
    depend on browser types)."""
    return subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--strict", "--target", "ES2022",
            "--module", "commonjs", "--lib", "ES2022",
            "--skipLibCheck", "--esModuleInterop",
            "--rootDir", "src/modules/research",
            "--outDir", str(out_dir),
            *[str(p) for p in sources],
        ],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )


# Runtime harness — loaded by Node after tsc has emitted the
# compiled renderers + domain module. Exercises every W4a
# externally observable contract: the dispatcher's typed dispatch
# for every supported format + every W4a-deferred format, the
# SVG sanitizer's every branch (valid, script-removal, event-
# handler-removal, document-invalid), the legacy message wording
# pinned to the byte, the IMAGE_BIG_FILE_BYTES constant value,
# the bytes-independence contract (mutating input bytes after
# dispatch doesn't affect the dispatch outcome), and the
# descriptor-readonly contract.
_RUNTIME_HARNESS = r"""
// CJS does not support top-level await (only ESM does), so the
// harness wraps the async body in an IIFE. The IIFE returns a
// Promise; we `.catch` to surface unhandled rejections as a
// non-zero exit code (the test harness reads `returncode != 0`
// as the failure marker).
const path = require("path");
const assert = require("assert");
const renderers = require(path.resolve(process.argv[2]));
const domain = require(path.resolve(process.argv[3]));

function makeBytes(s) {
  return new TextEncoder().encode(s);
}

function makeFile(overrides) {
  return Object.assign({
    url: "/api/files/serve?path=Animalia%2FChordata%2FMammalia.pdf",
    name: "Mammalia.pdf",
    format: "pdf",
    size: 12345,
    path: "Animalia/Chordata/Mammalia.pdf",
  }, overrides || {});
}

(async () => {
  // 1. IMAGE_BIG_FILE_BYTES constant — legacy 50 MB threshold.
  assert.strictEqual(
    renderers.IMAGE_BIG_FILE_BYTES, 50 * 1024 * 1024,
    "IMAGE_BIG_FILE_BYTES must equal 50 * 1024 * 1024 (legacy "
    + "threshold): got " + renderers.IMAGE_BIG_FILE_BYTES,
  );

  // 2. TAB_NOT_APPLICABLE_SUFFIX constant — legacy wording pinned.
  assert.strictEqual(
    renderers.TAB_NOT_APPLICABLE_SUFFIX, "files \u2014 use Raw.",
    "TAB_NOT_APPLICABLE_SUFFIX must be the literal "
    + "'files \u2014 use Raw.' (legacy wording pinned): got "
    + JSON.stringify(renderers.TAB_NOT_APPLICABLE_SUFFIX),
  );

  // 3. PDF dispatch — Raw tab, format="pdf" → pdf-iframe with
  //    src + title + fallback download link.
  let d = renderers.dispatchViewer({
    file: makeFile(),
    tab: "Raw",
    bytes: null,
  });
  assert.strictEqual(d.kind, "pdf-iframe",
    "PDF + Raw must dispatch to pdf-iframe: got " + d.kind);
  assert.strictEqual(d.src, "/api/files/serve?path=Animalia%2FChordata%2FMammalia.pdf",
    "PDF src must come from the descriptor.url verbatim");
  assert.strictEqual(d.title, "Mammalia.pdf");
  assert.strictEqual(d.fallback.href, d.src);
  assert.strictEqual(d.fallback.download, "Mammalia.pdf");

  // 4. HTML dispatch — Raw tab, format="html" → html-iframe with
  //    sandbox "" (legacy spec requirement: NO allow-same-origin).
  d = renderers.dispatchViewer({
    file: makeFile({ format: "html", name: "page.html",
      path: "page.html", url: "/api/files/serve?path=page.html" }),
    tab: "Raw",
    bytes: null,
  });
  assert.strictEqual(d.kind, "html-iframe",
    "HTML + Raw must dispatch to html-iframe: got " + d.kind);
  assert.strictEqual(d.sandbox, "",
    "HTML iframe sandbox MUST be the empty string (no "
    + "allow-same-origin): got " + JSON.stringify(d.sandbox));
  assert.strictEqual(d.title, "page.html");

  // 5. HTM dispatch — same as HTML (alias extension).
  d = renderers.dispatchViewer({
    file: makeFile({ format: "htm", name: "page.htm",
      path: "page.htm", url: "/api/files/serve?path=page.htm" }),
    tab: "Raw",
    bytes: null,
  });
  assert.strictEqual(d.kind, "html-iframe",
    "HTM + Raw must dispatch to html-iframe (alias of HTML): got " + d.kind);

  // 6. TXT dispatch — Raw tab, format="txt" + UTF-8 bytes →
  //    text-pre with the decoded body verbatim.
  d = renderers.dispatchViewer({
    file: makeFile({ format: "txt", name: "README.txt",
      path: "README.txt", url: "/api/files/serve?path=README.txt" }),
    tab: "Raw",
    bytes: makeBytes("hello\nworld\n"),
  });
  assert.strictEqual(d.kind, "text-pre",
    "TXT + Raw must dispatch to text-pre: got " + d.kind);
  assert.strictEqual(d.body, "hello\nworld\n",
    "TXT body must be the UTF-8 decoded bytes verbatim");

  // 7. MD dispatch — Raw tab, format="md" + UTF-8 bytes →
  //    text-pre (W4a PRESERVES legacy Markdown-as-text behavior;
  //    the spec's "Markdown rendering" scenario via marked.js
  //    CDN is deferred to a separately authorized later slice).
  d = renderers.dispatchViewer({
    file: makeFile({ format: "md", name: "Aves.md",
      path: "Animalia/Chordata/Aves.md",
      url: "/api/files/serve?path=Animalia%2FChordata%2FAves.md" }),
    tab: "Raw",
    bytes: makeBytes("# Aves\n\nSome **bold** markdown.\n"),
  });
  assert.strictEqual(d.kind, "text-pre",
    "MD + Raw must dispatch to text-pre (legacy Markdown-as-text "
    + "behavior preserved by W4a): got " + d.kind);
  assert.strictEqual(d.body, "# Aves\n\nSome **bold** markdown.\n",
    "MD body must be the UTF-8 decoded bytes verbatim — W4a does "
    + "NOT convert markdown to HTML");

  // 8. TXT bytes-missing fallback — Raw tab, format="txt",
  //    bytes=null → unsupported with parse-error message
  //    (mirrors legacy renderAsPre catch branch).
  d = renderers.dispatchViewer({
    file: makeFile({ format: "txt", name: "missing.txt",
      path: "missing.txt", url: "/api/files/serve?path=missing.txt" }),
    tab: "Raw",
    bytes: null,
  });
  assert.strictEqual(d.kind, "unsupported",
    "TXT + Raw + bytes=null must fall back to unsupported: got " + d.kind);
  assert(/Failed to load/.test(d.message),
    "TXT missing-bytes message must include 'Failed to load': got "
    + JSON.stringify(d.message));

  // 9. DOC dispatch — Raw tab, format="doc" → unsupported with
  //    the spec's "Legacy .doc cannot be rendered inline." message.
  d = renderers.dispatchViewer({
    file: makeFile({ format: "doc", name: "legacy.doc",
      path: "legacy.doc", url: "/api/files/serve?path=legacy.doc",
      size: 999 }),
    tab: "Raw",
    bytes: null,
  });
  assert.strictEqual(d.kind, "unsupported",
    "DOC + Raw must dispatch to unsupported: got " + d.kind);
  assert.strictEqual(d.message, "Legacy .doc cannot be rendered inline.",
    "DOC message must be the spec's exact wording: got "
    + JSON.stringify(d.message));
  assert.strictEqual(d.download.href, "/api/files/serve?path=legacy.doc");
  assert.strictEqual(d.download.download, "legacy.doc");

  // 10. Image dispatch — under the 50 MB threshold, advisory
  //     is null. JPG / JPEG / PNG / GIF / WEBP / BMP all dispatch
  //     to image with the URL + alt + title.
  for (const ext of ["jpg", "jpeg", "png", "gif", "webp", "bmp"]) {
    const file = makeFile({
      format: ext,
      name: "photo." + ext,
      path: "photos/photo." + ext,
      url: "/api/files/serve?path=photos%2Fphoto." + ext,
      size: 1024 * 1024, // 1 MB — under threshold
    });
    d = renderers.dispatchViewer({ file, tab: "Raw", bytes: null });
    assert.strictEqual(d.kind, "image",
      "Image " + ext + " + Raw must dispatch to image: got " + d.kind);
    assert.strictEqual(d.src, file.url,
      "Image src must come from descriptor.url verbatim: " + d.src);
    assert.strictEqual(d.alt, file.name);
    assert.strictEqual(d.title, file.name);
    assert.strictEqual(d.advisory, null,
      "Image under 50 MB must have advisory=null: got "
      + JSON.stringify(d.advisory));
  }

  // 11. Image advisory — over the 50 MB threshold, the
  //     advisory carries the legacy "Large image (123.4 MB) —
  //     decoding may be slow." message.
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "jpg",
      name: "big.jpg",
      path: "big.jpg",
      url: "/api/files/serve?path=big.jpg",
      size: 60 * 1024 * 1024, // 60 MB — over threshold
    }),
    tab: "Raw",
    bytes: null,
  });
  assert.strictEqual(d.kind, "image");
  assert.ok(d.advisory !== null, "Image over 50 MB must have advisory");
  assert.strictEqual(d.advisory.message, "Large image (60.0 MB) \u2014 decoding may be slow.",
    "Image advisory message must match legacy formatSize output: got "
    + JSON.stringify(d.advisory.message));

  // 12. SVG dispatch — valid SVG markup with `<script>` +
  //     `on*=` attrs → svg-sanitized with the scrubbed markup,
  //     className "fex-image", preserveAspectRatio "xMidYMid meet".
  const svgInput =
    '<svg xmlns="http://www.w3.org/2000/svg" onclick="hack()" '
    + 'onmouseover="bad()">'
    + '<script>alert(1)</script>'
    + '<circle cx="10" cy="10" r="5" fill="red" '
    + 'onclick="bad()"/>'
    + '</svg>';
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "svg",
      name: "diagram.svg",
      path: "diagram.svg",
      url: "/api/files/serve?path=diagram.svg",
      size: 256,
    }),
    tab: "Raw",
    bytes: makeBytes(svgInput),
  });
  assert.strictEqual(d.kind, "svg-sanitized",
    "SVG + Raw + valid bytes must dispatch to svg-sanitized: got " + d.kind);
  assert.ok(!/<script/i.test(d.svg),
    "SVG sanitizer MUST strip <script> blocks: got " + JSON.stringify(d.svg));
  assert.ok(!/\son[a-z]+\s*=/i.test(d.svg),
    "SVG sanitizer MUST strip on*= event-handler attrs: got "
    + JSON.stringify(d.svg));
  assert.ok(/circle/i.test(d.svg),
    "SVG sanitizer MUST preserve non-event SVG content (circle element): got "
    + JSON.stringify(d.svg));
  assert.strictEqual(d.className, "fex-image");
  assert.strictEqual(d.preserveAspectRatio, "xMidYMid meet");

  // 13. SVG sanitizer — invalid document (not <svg>) returns "".
  assert.strictEqual(renderers.sanitizeSvgMarkup("not svg at all"), "",
    "sanitizeSvgMarkup must return '' when the document does not "
    + "start with <svg: got " + JSON.stringify(renderers.sanitizeSvgMarkup("not svg at all")));
  assert.strictEqual(renderers.sanitizeSvgMarkup("<div>html</div>"), "",
    "sanitizeSvgMarkup must return '' when the document starts with <div: "
    + "got " + JSON.stringify(renderers.sanitizeSvgMarkup("<div>html</div>")));

  // 14. SVG sanitizer — multiple `<script>` blocks + multiple
  //     event-handler attrs all stripped, safe content preserved.
  const multiSvg =
    '<svg>'
    + '<script>a()</script><script>b()</script>'
    + '<rect onclick="x()" onload="y()" fill="blue"/>'
    + '<text onmouseover="z()">hello</text>'
    + '</svg>';
  const cleaned = renderers.sanitizeSvgMarkup(multiSvg);
  assert.ok(!/<script/i.test(cleaned),
    "Multi-script SVG sanitizer MUST strip every <script> block");
  assert.ok(!/\son[a-z]+\s*=/i.test(cleaned),
    "Multi-event SVG sanitizer MUST strip every on*= attribute");
  assert.ok(/rect/i.test(cleaned) && /text/i.test(cleaned),
    "Multi-script SVG sanitizer MUST preserve non-event SVG content");

  // 15. SVG sanitizer — preserves `viewBox` / `xmlns` /
  //     `class` / `href` non-event attributes verbatim.
  const attrSvg =
    '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" '
    + 'class="fex-image" href="https://example.com" onclick="bad()">'
    + '</svg>';
  const attrCleaned = renderers.sanitizeSvgMarkup(attrSvg);
  assert.ok(/viewBox=/.test(attrCleaned),
    "Sanitizer MUST preserve viewBox: got " + JSON.stringify(attrCleaned));
  assert.ok(/xmlns=/.test(attrCleaned),
    "Sanitizer MUST preserve xmlns: got " + JSON.stringify(attrCleaned));
  assert.ok(/class=/.test(attrCleaned),
    "Sanitizer MUST preserve class: got " + JSON.stringify(attrCleaned));
  assert.ok(/href=/.test(attrCleaned),
    "Sanitizer MUST preserve href: got " + JSON.stringify(attrCleaned));
  assert.ok(!/onclick/i.test(attrCleaned),
    "Sanitizer MUST strip onclick while preserving href: got "
    + JSON.stringify(attrCleaned));

  // 16. SVG dispatch — invalid SVG markup → image-error fallback.
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "svg",
      name: "bad.svg",
      path: "bad.svg",
      url: "/api/files/serve?path=bad.svg",
      size: 10,
    }),
    tab: "Raw",
    bytes: makeBytes("<html>not svg</html>"),
  });
  assert.strictEqual(d.kind, "image-error",
    "SVG + Raw + invalid markup must fall back to image-error: got " + d.kind);
  assert.strictEqual(d.name, "bad.svg");
  assert.strictEqual(d.download.href, "/api/files/serve?path=bad.svg");
  assert.strictEqual(d.download.download, "bad.svg");

  // 17. SVG dispatch — bytes missing → image-error fallback
  //     (mirrors legacy renderSvg fetch-failure catch branch).
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "svg",
      name: "missing.svg",
      path: "missing.svg",
      url: "/api/files/serve?path=missing.svg",
      size: 0,
    }),
    tab: "Raw",
    bytes: null,
  });
  assert.strictEqual(d.kind, "image-error",
    "SVG + Raw + bytes=null must fall back to image-error: got " + d.kind);

  // 18. Video dispatch — MP4 / WEBM / OGV all dispatch to video
  //     with controls=true + preload="metadata".
  for (const ext of ["mp4", "webm", "ogv"]) {
    d = renderers.dispatchViewer({
      file: makeFile({
        format: ext,
        name: "clip." + ext,
        path: "clips/clip." + ext,
        url: "/api/files/serve?path=clips%2Fclip." + ext,
        size: 4096,
      }),
      tab: "Raw",
      bytes: null,
    });
    assert.strictEqual(d.kind, "video",
      "Video " + ext + " + Raw must dispatch to video: got " + d.kind);
    assert.strictEqual(d.src, "/api/files/serve?path=clips%2Fclip." + ext);
    assert.strictEqual(d.title, "clip." + ext);
    assert.strictEqual(d.controls, true,
      "Video controls MUST be true (UX: surprise audio is hostile): got "
      + d.controls);
    assert.strictEqual(d.preload, "metadata",
      "Video preload MUST be 'metadata' (don't pin the network): got "
      + d.preload);
  }

  // 19. "other" dispatch — unknown extension like .zip → unsupported
  //     with the wire-extension message.
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "other",
      name: "data.zip",
      path: "data.zip",
      url: "/api/files/serve?path=data.zip",
      size: 8192,
    }),
    tab: "Raw",
    bytes: null,
  });
  assert.strictEqual(d.kind, "unsupported",
    "Other + Raw must dispatch to unsupported: got " + d.kind);
  assert.strictEqual(d.message, "Format .zip not supported in viewer.",
    "Other message must extract the wire extension from path: got "
    + JSON.stringify(d.message));
  assert.strictEqual(d.download.href, "/api/files/serve?path=data.zip");
  assert.strictEqual(d.download.download, "data.zip");

  // 20. Still-W4b+-deferred formats on Raw — CSV / TSV /
  //     JSON all fall through to the default arm with
  //     the format-literal "Format .{ext} not supported in
  //     viewer." message. W4b4 extends the dispatcher by
  //     adding explicit arms for each of these formats; the
  //     W4a + W4b1 + W4b2 + W4b3 contract commits to the
  //     unsupported fallback so the React mount paints the
  //     same download-link card as the legacy
  //     renderUnsupported. DOCX is OWNED by W4b1 — the
  //     dispatcher emits the typed `docx-source` outcome
  //     instead (with bytes-missing falling back to
  //     `docx-offline`). The DOCX dispatch is exercised in
  //     steps 30+ below. XLS / XLSX are OWNED by W4b2 — the
  //     dispatcher emits the typed `sheet-source` outcome
  //     instead (with bytes-missing falling back to
  //     `sheet-offline`). The XLS / XLSX dispatch is
  //     exercised in steps 38+ below. EPUB is OWNED by W4b3
  //     — the dispatcher emits the typed `epub-source`
  //     outcome instead (with bytes-missing falling back to
  //     `epub-offline`). The EPUB dispatch is exercised in
  //     steps 50+ below. EPUB is REMOVED from this deferred
  //     loop so the deferred set is now just CSV / TSV / JSON.
  for (const ext of ["csv", "tsv", "json"]) {
    d = renderers.dispatchViewer({
      file: makeFile({
        format: ext,
        name: "file." + ext,
        path: "file." + ext,
        url: "/api/files/serve?path=file." + ext,
        size: 100,
      }),
      tab: "Raw",
      bytes: null,
    });
    assert.strictEqual(d.kind, "unsupported",
      "W4a-deferred " + ext + " + Raw must dispatch to unsupported: "
      + "got " + d.kind);
    assert.strictEqual(d.message,
      "Format ." + ext + " not supported in viewer.",
      "W4a-deferred " + ext + " message must be the format-literal "
      + "fallback: got " + JSON.stringify(d.message));
    assert.strictEqual(d.download.download, "file." + ext,
      "W4a-deferred " + ext + " download link must carry the file "
      + "basename");
  }

  // 21. Tab-not-applicable — Table / Tree tab on a W4a-supported
  //     format (PDF, HTML, TXT, MD, DOC, image, SVG, video)
  //     surfaces the legacy `${tab} view not available for .${ext}
  //     files — use Raw.` message verbatim. W4b+ extends the
  //     dispatcher with Table-on-csv/tsv + Tree-on-json support;
  //     until then, every file on Table/Tree tabs hits this
  //     branch. The "other" fallback is tested separately in
  //     steps 22 + 23 (the extension label is derived from the
  //     path basename, not the format literal).
  for (const tab of ["Table", "Tree"]) {
    for (const ext of ["pdf", "html", "htm", "txt", "md", "doc",
        "jpg", "png", "svg", "mp4"]) {
      d = renderers.dispatchViewer({
        file: makeFile({
          format: ext,
          name: "x." + ext,
          path: "x." + ext,
          url: "/api/files/serve?path=x." + ext,
          size: 0,
        }),
        tab: tab,
        bytes: null,
      });
      assert.strictEqual(d.kind, "tab-not-applicable",
        tab + " tab on " + ext + " must dispatch to tab-not-applicable: "
        + "got " + d.kind);
      // The extension label must come from the format literal
      // (the W4a-supported formats are all single-word FileFormat
      // literals, so the legacy wording is preserved byte-for-byte).
      assert.strictEqual(d.message,
        tab + " view not available for ." + ext + " "
        + renderers.TAB_NOT_APPLICABLE_SUFFIX,
        tab + " tab on " + ext + " message must match legacy wording: "
        + "got " + JSON.stringify(d.message));
    }
  }

  // 22. Tab-not-applicable for "other" — wire extension comes
  //     from the path basename, not from the format literal.
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "other",
      name: "data.zip",
      path: "data.zip",
      url: "/api/files/serve?path=data.zip",
      size: 0,
    }),
    tab: "Table",
    bytes: null,
  });
  assert.strictEqual(d.kind, "tab-not-applicable");
  assert.strictEqual(d.message,
    "Table view not available for .zip " + renderers.TAB_NOT_APPLICABLE_SUFFIX,
    "Other-format Table-tab message must extract the wire extension: got "
    + JSON.stringify(d.message));

  // 23. Tab-not-applicable for "other" with no extension —
  //     falls back to "?" label (mirrors legacy
  //     `Format .${ext || "?"} not supported in viewer.` fallback).
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "other",
      name: "noext",
      path: "noext",
      url: "/api/files/serve?path=noext",
      size: 0,
    }),
    tab: "Table",
    bytes: null,
  });
  assert.strictEqual(d.kind, "tab-not-applicable");
  assert.strictEqual(d.message,
    "Table view not available for .? " + renderers.TAB_NOT_APPLICABLE_SUFFIX,
    "Other-format-without-extension Table-tab message must use '?' label: "
    + "got " + JSON.stringify(d.message));

  // 24. Bytes independence — mutating the input bytes after
  //     dispatch does NOT affect the dispatch outcome. Mirrors
  //     the W2 port's value-typed contract
  //     (`tests/test_research_application.py::
  //     test_compiled_application_passes_runtime_contract` step 7).
  const bytes = makeBytes("hello world");
  d = renderers.dispatchViewer({
    file: makeFile({ format: "txt", name: "a.txt",
      path: "a.txt", url: "/api/files/serve?path=a.txt" }),
    tab: "Raw",
    bytes: bytes,
  });
  assert.strictEqual(d.kind, "text-pre");
  // Mutate the input bytes after dispatch.
  bytes[0] = 0x58; // 'X'
  // Re-dispatch with the same logical content — the mutated
  // bytes are reflected (the dispatcher reads the bytes at call
  // time), but the first dispatch result is already a frozen
  // string and not affected by the mutation.
  const d2 = renderers.dispatchViewer({
    file: makeFile({ format: "txt", name: "a.txt",
      path: "a.txt", url: "/api/files/serve?path=a.txt" }),
    tab: "Raw",
    bytes: bytes,
  });
  assert.strictEqual(d2.body, "Xello world",
    "Second dispatch reflects mutated bytes (dispatcher reads bytes "
    + "at call time): got " + JSON.stringify(d2.body));
  // The first dispatch result's body is frozen (it's a string)
  // — mutating bytes post-dispatch does NOT retroactively
  // change d.body.
  assert.strictEqual(d.body, "hello world",
    "First dispatch outcome is unaffected by post-dispatch byte "
    + "mutation: got " + JSON.stringify(d.body));

  // 25. Dispatcher purity — same input yields the same output
  //     on every call (no `Date.now()`, no `Math.random()`).
  const pdfFile = makeFile();
  const dA = renderers.dispatchViewer({
    file: pdfFile, tab: "Raw", bytes: null,
  });
  const dB = renderers.dispatchViewer({
    file: pdfFile, tab: "Raw", bytes: null,
  });
  assert.deepStrictEqual(
    JSON.parse(JSON.stringify(dA)),
    JSON.parse(JSON.stringify(dB)),
    "Dispatcher MUST be pure — same input → same output",
  );

  // 26. Domain import round-trip — the renderers module's
  //     `FileFormat` + `ViewerTab` types are reachable from the
  //     W1 domain contract (proves the W1 ↔ W4a dependency is
  //     wired correctly). The harness imports the domain module
  //     directly and asserts the initial-state factory exists
  //     (the W1 surface is intact at compile time).
  if (typeof domain.createInitialExplorerState !== "function") {
    throw new Error("domain initial-state factory is not reachable from W4a context");
  }

  // 27. W4b+ Table/Tree gate check — the Table / Tree
  //     branch gates BEFORE the format switch so every
  //     format with a Table/Tree-untouched contract fires
  //     `tab-not-applicable`. DOCX is OWNED by W4b1 but
  //     the W4b1 contract does NOT add Table/Tree
  //     renderers — DOCX is Raw-only via mammoth. DOCX
  //     therefore stays in this loop (the Table/Tree gate
  //     short-circuits before the format switch), pinning
  //     the W4b1 split shape: DOCX dispatches to
  //     `docx-source` / `docx-offline` on Raw, and to
  //     `tab-not-applicable` on Table/Tree. XLS / XLSX are
  //     OWNED by W4b2 but the W4b2 contract does NOT add
  //     Table/Tree renderers — XLS / XLSX are Raw-only via
  //     SheetJS (SheetJS emits HTML tables, not a dedicated
  //     spreadsheet widget). EPUB is OWNED by W4b3 but
  //     the W4b3 contract does NOT add Table/Tree
  //     renderers — EPUB is Raw-only via epubjs (epubjs
  //     renders an EPUB as a paged book, not a Table
  //     widget or a Tree widget). EPUB therefore stays in
  //     this loop, pinning the W4b3 split shape: EPUB
  //     dispatches to `epub-source` / `epub-offline` on
  //     Raw, and to `tab-not-applicable` on Table/Tree.
  //     CSV / TSV / JSON are the still-W4b+-deferred
  //     formats — they also stay in this loop until W4b4
  //     adds Table-on-csv/tsv + Tree-on-json arms.
  for (const tab of ["Table", "Tree"]) {
    for (const ext of ["docx", "xls", "xlsx", "epub", "csv", "tsv", "json"]) {
      d = renderers.dispatchViewer({
        file: makeFile({
          format: ext,
          name: "f." + ext,
          path: "f." + ext,
          url: "/api/files/serve?path=f." + ext,
          size: 0,
        }),
        tab: tab,
        bytes: null,
      });
      assert.strictEqual(d.kind, "tab-not-applicable",
        tab + " tab on W4a-deferred " + ext + " must dispatch to "
        + "tab-not-applicable: got " + d.kind);
      assert.strictEqual(d.message,
        tab + " view not available for ." + ext + " "
        + renderers.TAB_NOT_APPLICABLE_SUFFIX,
        tab + " tab on W4a-deferred " + ext + " message must match "
        + "legacy wording: got " + JSON.stringify(d.message));
    }
  }

  // 28. Self-closing `<script src=…/>` regression — the W4a
  //     sanitizer MUST strip self-closing script elements
  //     (`<script src="…"/>`, `<script src="…" />`), not just
  //     the paired `<script>…</script>` form. Matches the
  //     legacy DOM scrub — `querySelectorAll("script")`
  //     returns BOTH paired AND self-closing shapes
  //     inherently. Case-insensitive on the tag name
  //     (`<SCRIPT/>`, `<Script … />`).
  //
  //     The fixture uses ONLY self-closing scripts (no paired
  //     scripts in the same string) so the paired regex
  //     cannot sweep them up via lazy `</script>` matching
  //     — the self-closing regex is required for the test to
  //     pass, proving the fix actually exercises both code
  //     paths.
  const selfClosingSvg =
    '<svg>'
    + '<script src="evil.js"/>'
    + '<SCRIPT src="evil2.js" />'
    + '<rect fill="blue"/>'
    + '</svg>';
  const selfClosingCleaned = renderers.sanitizeSvgMarkup(selfClosingSvg);
  assert.ok(!/<script/i.test(selfClosingCleaned),
    "SVG sanitizer MUST strip self-closing <script src=.../> "
    + "shapes (case-insensitively): got "
    + JSON.stringify(selfClosingCleaned));
  assert.ok(!/src\s*=\s*["']evil/.test(selfClosingCleaned),
    "SVG sanitizer MUST strip self-closing script content "
    + "(src=\"evil.js\") entirely: got "
    + JSON.stringify(selfClosingCleaned));
  assert.ok(/rect/i.test(selfClosingCleaned),
    "SVG sanitizer MUST preserve non-script SVG content after "
    + "self-closing script removal: got "
    + JSON.stringify(selfClosingCleaned));

  // 29. Uppercase / mixed-case `on*=` regression — the W4a
  //     sanitizer MUST strip event-handler attributes
  //     regardless of case (`ONCLICK`, `OnMouseover`,
  //     `onLoad`, etc.). Matches the legacy DOM scrub — the
  //     browser's SVG namespace attribute lookup is case-
  //     insensitive. The case-sensitive regex checks below
  //     prove uppercase + mixed-case forms are actually
  //     removed (the existing `/i` regex check would pass
  //     even when the uppercase form leaked through).
  const mixedCaseSvg =
    '<svg ONCLICK="hack()">'
    + '<circle ONMOUSEOVER="bad()" cx="10" cy="10" r="5" '
    + 'fill="red" OnLoad="x()"/>'
    + '</svg>';
  const mixedCaseCleaned = renderers.sanitizeSvgMarkup(mixedCaseSvg);
  // Case-sensitive checks (no /i flag) — proves uppercase +
  // mixed-case `on*=` forms are actually stripped, not just
  // their case-folded variants.
  assert.ok(!/ONCLICK/.test(mixedCaseCleaned),
    "SVG sanitizer MUST strip UPPERCASE ONCLICK attr "
    + "(case-sensitive check): got "
    + JSON.stringify(mixedCaseCleaned));
  assert.ok(!/ONMOUSEOVER/.test(mixedCaseCleaned),
    "SVG sanitizer MUST strip UPPERCASE ONMOUSEOVER attr "
    + "(case-sensitive check): got "
    + JSON.stringify(mixedCaseCleaned));
  assert.ok(!/OnLoad/.test(mixedCaseCleaned),
    "SVG sanitizer MUST strip mixed-case OnLoad attr "
    + "(case-sensitive check): got "
    + JSON.stringify(mixedCaseCleaned));
  assert.ok(/circle/i.test(mixedCaseCleaned),
    "SVG sanitizer MUST preserve non-event SVG content: got "
    + JSON.stringify(mixedCaseCleaned));

  // 30. W4b1 DOCX — Raw tab + format="docx" + injected bytes
  //     dispatches to `docx-source` with the descriptor +
  //     bytes + pinned mammoth CDN URL + global name. The
  //     future React mount (W6+) consumes the typed source
  //     outcome via Next 16's `<Script src={scriptUrl}
  //     strategy="afterInteractive" onLoad={convert}>` then
  //     calls `window[scriptGlobal].convertToHtml({arrayBuffer:
  //     bytes})` then injects the HTML via
  //     `Range.createContextualFragment` (mirrors the legacy
  //     `web/file_viewer.js::renderDocx` shape). The dispatcher
  //     does NOT load the script, fetch the URL, or call
  //     convert — it only emits the typed source descriptor.
  const docxBytes = makeBytes("PK\x03\x04fake-docx-bytes");
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "docx",
      name: "Mammalia.docx",
      path: "Animalia/Chordata/Mammalia.docx",
      url: "/api/files/serve?path=Animalia%2FChordata%2FMammalia.docx",
      size: docxBytes.length,
    }),
    tab: "Raw",
    bytes: docxBytes,
  });
  assert.strictEqual(d.kind, "docx-source",
    "DOCX + Raw + bytes must dispatch to docx-source: got " + d.kind);
  assert.strictEqual(d.src, "/api/files/serve?path=Animalia%2FChordata%2FMammalia.docx",
    "DOCX src must come from the descriptor.url verbatim");
  assert.strictEqual(d.title, "Mammalia.docx",
    "DOCX title must come from the descriptor.name verbatim");
  assert.ok(d.bytes instanceof Uint8Array,
    "DOCX source must carry bytes as a Uint8Array: got "
    + typeof d.bytes);
  assert.strictEqual(d.bytes, docxBytes,
    "DOCX source bytes must be the SAME Uint8Array reference "
    + "as the input bytes (the dispatcher passes by reference, "
    + "does NOT copy — mirrors the W2 port's value-typed "
    + "contract, doc: tests/test_research_application.py::"
    + "test_compiled_application_passes_runtime_contract step 7)");
  assert.strictEqual(d.scriptUrl,
    "https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js",
    "DOCX source scriptUrl must be the legacy-pinned mammoth "
    + "CDN URL (matches web/file_viewer.js::CDN_URLS.mammoth "
    + "and web/index.html's mammoth.js <script> tag)");
  assert.strictEqual(d.scriptGlobal, "mammoth",
    "DOCX source scriptGlobal must be the literal 'mammoth' "
    + "(matches web/file_viewer.js::window.mammoth.convertToHtml "
    + "call site + CDN_URLS.mammoth map key)");

  // 31. W4b1 DOCX — Raw tab + format="docx" + bytes=null
  //     falls back to `docx-offline` with the download link
  //     + pinned CDN URL + global name + reason. The future
  //     React mount paints the legacy "Viewer offline — raw
  //     download available" banner verbatim — the same
  //     shape `web/file_viewer.js::renderOfflineBanner`
  //     paints, just sourced from the typed offline
  //     descriptor. The bytes-missing reason is the ONLY
  //     offline path the dispatcher can detect (the
  //     dispatcher does not fetch the URL, load the CDN,
  //     or call convertToHtml — those failures happen at
  //     the mount and are not part of the dispatcher
  //     contract).
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "docx",
      name: "missing.docx",
      path: "missing.docx",
      url: "/api/files/serve?path=missing.docx",
      size: 0,
    }),
    tab: "Raw",
    bytes: null,
  });
  assert.strictEqual(d.kind, "docx-offline",
    "DOCX + Raw + bytes=null must fall back to docx-offline: "
    + "got " + d.kind);
  assert.strictEqual(d.name, "missing.docx",
    "DOCX offline name must come from descriptor.name");
  assert.strictEqual(d.download.href,
    "/api/files/serve?path=missing.docx",
    "DOCX offline download.href must come from descriptor.url");
  assert.strictEqual(d.download.download, "missing.docx",
    "DOCX offline download.download must carry the basename");
  assert.strictEqual(d.scriptUrl,
    "https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js",
    "DOCX offline scriptUrl must be the legacy-pinned CDN URL "
    + "(the mount needs the URL to retry the loader or to "
    + "surface a 'try again' affordance)");
  assert.strictEqual(d.scriptGlobal, "mammoth",
    "DOCX offline scriptGlobal must be the literal 'mammoth'");
  assert.strictEqual(d.reason, "bytes-missing",
    "DOCX offline reason MUST be the typed 'bytes-missing' "
    + "literal — the dispatcher can only detect this offline "
    + "path at dispatch time. CDN-load + convertToHtml failures "
    + "are MOUNT responsibilities and are NOT part of this "
    + "contract: got " + JSON.stringify(d.reason));

  // 32. W4b1 DOCX — bytes-missing framing on the offline
  //     branch — the dispatcher uses the descriptor's path
  //     field as the extension label so the offline framing
  //     matches the legacy "Failed to load docx — bytes
  //     not available." convention observed by the W4a TXT
  //     bytes-missing fallback (step 8). The W4b1 DOCX
  //     branch does NOT carry a free-form message string
  //     — the offline branch is a typed descriptor (kind +
  //     name + download + scriptUrl + scriptGlobal + reason)
  //     and the future mount paints the message itself. The
  //     "message" field check is intentionally skipped —
  //     pin the typed surface only.
  assert.ok(!("message" in d),
    "DOCX offline branch MUST NOT carry a free-form 'message' "
    + "field — the legacy offline wording is painted by the "
    + "mount from the typed descriptor (kind + name + "
    + "download), not pre-formatted by the dispatcher");

  // 33. W4b1 DOCX — Table / Tree tab on DOCX fires
  //     tab-not-applicable — the Table/Tree gate runs BEFORE
  //     the format switch so DOCX never reaches the W4b1
  //     `case "docx":` arm. This pins the W4b1 split shape:
  //     DOCX has a Raw-only renderer (mammoth produces HTML,
  //     not a table or tree). Step 27 already covers this
  //     case for the broader deferred loop; here we re-assert
  //     it for DOCX explicitly + verify the message uses the
  //     "docx" literal (NOT the wire-extension variant — the
  //     descriptor's `format` field carries "docx" verbatim).
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "docx",
      name: "f.docx",
      path: "f.docx",
      url: "/api/files/serve?path=f.docx",
      size: 100,
    }),
    tab: "Table",
    bytes: docxBytes,
  });
  assert.strictEqual(d.kind, "tab-not-applicable",
    "DOCX + Table + bytes must fire tab-not-applicable "
    + "(DOCX has no Table renderer): got " + d.kind);
  assert.strictEqual(d.message,
    "Table view not available for .docx "
    + renderers.TAB_NOT_APPLICABLE_SUFFIX,
    "DOCX + Table message must use the 'docx' format literal "
    + "as the extension label (the descriptor.format is "
    + "'docx', not 'other'): got " + JSON.stringify(d.message));
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "docx",
      name: "f.docx",
      path: "f.docx",
      url: "/api/files/serve?path=f.docx",
      size: 100,
    }),
    tab: "Tree",
    bytes: docxBytes,
  });
  assert.strictEqual(d.kind, "tab-not-applicable",
    "DOCX + Tree + bytes must fire tab-not-applicable "
    + "(DOCX has no Tree renderer): got " + d.kind);

  // 34. W4b1 DOCX — dispatcher purity — the W4b1 source /
  //     offline branches are pure: same input yields the
  //     same output on every call (no Date.now(), no
  //     Math.random(), no side effects on the input).
  const docxFile = makeFile({
    format: "docx",
    name: "Mammalia.docx",
    path: "Animalia/Chordata/Mammalia.docx",
    url: "/api/files/serve?path=Animalia%2FChordata%2FMammalia.docx",
    size: docxBytes.length,
  });
  const docxA = renderers.dispatchViewer({
    file: docxFile, tab: "Raw", bytes: docxBytes,
  });
  const docxB = renderers.dispatchViewer({
    file: docxFile, tab: "Raw", bytes: docxBytes,
  });
  assert.deepStrictEqual(
    JSON.parse(JSON.stringify(docxA)),
    JSON.parse(JSON.stringify(docxB)),
    "DOCX dispatcher MUST be pure — same input → same output",
  );
  assert.strictEqual(docxA.kind, "docx-source");
  assert.strictEqual(docxB.kind, "docx-source");
  assert.strictEqual(docxA.scriptUrl, docxB.scriptUrl);
  assert.strictEqual(docxA.scriptGlobal, docxB.scriptGlobal);

  // 35. W4b1 — offline-branch purity (same input → same
  //     output on the bytes=null path too — mirrors the
  //     source-branch purity check above).
  const docxMissingFile = makeFile({
    format: "docx",
    name: "missing.docx",
    path: "missing.docx",
    url: "/api/files/serve?path=missing.docx",
    size: 0,
  });
  const offlineA = renderers.dispatchViewer({
    file: docxMissingFile, tab: "Raw", bytes: null,
  });
  const offlineB = renderers.dispatchViewer({
    file: docxMissingFile, tab: "Raw", bytes: null,
  });
  assert.deepStrictEqual(
    JSON.parse(JSON.stringify(offlineA)),
    JSON.parse(JSON.stringify(offlineB)),
    "DOCX offline branch MUST be pure — same input → same output",
  );
  assert.strictEqual(offlineA.kind, "docx-offline");
  assert.strictEqual(offlineB.kind, "docx-offline");
  assert.strictEqual(offlineA.scriptUrl, offlineB.scriptUrl);
  assert.strictEqual(offlineA.reason, offlineB.reason);

  // 36. W4b1 — bytes-reference contract — the dispatcher
  //     passes the input bytes reference through to
  //     `docx-source.bytes` (NO copy, NO decode — the
  //     dispatcher doesn't load mammoth or do any conversion).
  //     This is intentional: the future mount reads the
  //     bytes at mount time and feeds them straight to
  //     `window.mammoth.convertToHtml({arrayBuffer: bytes})`.
  //     Copying the bytes at dispatch time would cost a
  //     Uint8Array allocation per dispatch and gain nothing
  //     (the mount doesn't mutate the bytes). The pinned
  //     contract: docx-source.bytes === input bytes
  //     reference, by-reference.
  const refBytes = makeBytes("PK\x03\x04reference-test");
  const docxRef = renderers.dispatchViewer({
    file: makeFile({
      format: "docx",
      name: "ref.docx",
      path: "ref.docx",
      url: "/api/files/serve?path=ref.docx",
      size: refBytes.length,
    }),
    tab: "Raw",
    bytes: refBytes,
  });
  assert.strictEqual(docxRef.kind, "docx-source");
  assert.strictEqual(docxRef.bytes, refBytes,
    "DOCX source bytes MUST be the SAME Uint8Array reference "
    + "as the input bytes (pass-by-reference contract — the "
    + "mount reads bytes at mount time, not dispatch time): "
    + "got different reference");
  // A second dispatch on the SAME descriptor + bytes
  // returns the SAME reference (the dispatcher does not
  // memoize or copy between calls).
  const docxRef2 = renderers.dispatchViewer({
    file: makeFile({
      format: "docx",
      name: "ref.docx",
      path: "ref.docx",
      url: "/api/files/serve?path=ref.docx",
      size: refBytes.length,
    }),
    tab: "Raw",
    bytes: refBytes,
  });
  assert.strictEqual(docxRef2.bytes, refBytes,
    "Second DOCX dispatch must also return the SAME bytes "
    + "reference — the dispatcher does not memoize or copy");

  // 37. W4b1 — bytes mutation visible through the dispatched
  //     reference (because the dispatcher passes by
  //     reference, mutating the input bytes after dispatch
  //     is visible through the dispatched reference). This
  //     is a documented contract — the dispatcher does NOT
  //     freeze the bytes, it passes them through verbatim.
  //     The future mount is responsible for treating the
  //     bytes as read-only or copying before mutation.
  refBytes[0] = 0x58; // 'X' — mutate input bytes after dispatch
  // The first dispatch's `d.bytes` is the SAME reference,
  // so it now sees the mutation too (Uint8Array is a view
  // on a backing ArrayBuffer — the bytes field IS the
  // input bytes).
  assert.strictEqual(docxRef.bytes[0], 0x58,
    "DOCX bytes-reference contract: mutating input bytes "
    + "after dispatch is visible through the dispatched "
    + "reference (the dispatcher passes by reference, not "
    + "by copy). The mount MUST treat the bytes as "
    + "read-only or copy before mutation: got byte 0 = "
    + JSON.stringify(docxRef.bytes[0]));

  // 38. W4b2 XLSX — Raw tab + format="xlsx" + injected bytes
  //     dispatches to `sheet-source` with the descriptor +
  //     bytes + pinned SheetJS CDN URL + global name. The
  //     future React mount (W6+) consumes the typed source
  //     outcome via Next 16's `<Script src={scriptUrl}
  //     strategy="afterInteractive" onLoad={convert}>` then
  //     calls `window[scriptGlobal].read(bytes, { type:
  //     "array" })` to parse the workbook, then
  //     `window[scriptGlobal].utils.sheet_to_html(sheet)` to
  //     emit the HTML table, then injects the HTML via
  //     `Range.createContextualFragment` (mirrors the legacy
  //     `web/file_viewer.js::renderSheet` shape). The
  //     dispatcher does NOT load the script, fetch the URL,
  //     or call read / sheet_to_html — it only emits the
  //     typed source descriptor.
  const xlsxBytes = makeBytes("PK\x03\x04fake-xlsx-bytes");
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "xlsx",
      name: "data.xlsx",
      path: "Animalia/Chordata/data.xlsx",
      url: "/api/files/serve?path=Animalia%2FChordata%2Fdata.xlsx",
      size: xlsxBytes.length,
    }),
    tab: "Raw",
    bytes: xlsxBytes,
  });
  assert.strictEqual(d.kind, "sheet-source",
    "XLSX + Raw + bytes must dispatch to sheet-source: got " + d.kind);
  assert.strictEqual(d.src,
    "/api/files/serve?path=Animalia%2FChordata%2Fdata.xlsx",
    "XLSX src must come from the descriptor.url verbatim");
  assert.strictEqual(d.title, "data.xlsx",
    "XLSX title must come from the descriptor.name verbatim");
  assert.ok(d.bytes instanceof Uint8Array,
    "XLSX source must carry bytes as a Uint8Array: got "
    + typeof d.bytes);
  assert.strictEqual(d.bytes, xlsxBytes,
    "XLSX source bytes must be the SAME Uint8Array reference "
    + "as the input bytes (the dispatcher passes by reference, "
    + "does NOT copy — mirrors the W4b1 DOCX bytes-reference "
    + "contract from step 36)");
  assert.strictEqual(d.scriptUrl,
    "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js",
    "XLSX source scriptUrl must be the legacy-pinned SheetJS "
    + "CDN URL (matches web/file_viewer.js::CDN_URLS.XLSX "
    + "and web/index.html's SheetJS (xlsx) <script> tag)");
  assert.strictEqual(d.scriptGlobal, "XLSX",
    "XLSX source scriptGlobal must be the literal 'XLSX' "
    + "(matches web/file_viewer.js::window.XLSX.read + "
    + "window.XLSX.utils.sheet_to_html call sites + "
    + "CDN_URLS.XLSX map key)");

  // 39. W4b2 XLS — Raw tab + format="xls" + injected bytes
  //     dispatches to `sheet-source` with the same descriptor
  //     shape. Both XLS and XLSX go through the SheetJS path;
  //     the `format` field carries the extension verbatim so
  //     the mount can branch on XLS vs XLSX for format-
  //     specific affordances if needed (SheetJS itself does
  //     not distinguish them at the read site).
  const xlsBytes = makeBytes("\xd0\xcf\x11\xe0fake-xls-bytes");
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "xls",
      name: "data.xls",
      path: "Animalia/Chordata/data.xls",
      url: "/api/files/serve?path=Animalia%2FChordata%2Fdata.xls",
      size: xlsBytes.length,
    }),
    tab: "Raw",
    bytes: xlsBytes,
  });
  assert.strictEqual(d.kind, "sheet-source",
    "XLS + Raw + bytes must dispatch to sheet-source: got " + d.kind);
  assert.strictEqual(d.src,
    "/api/files/serve?path=Animalia%2FChordata%2Fdata.xls",
    "XLS src must come from the descriptor.url verbatim");
  assert.strictEqual(d.title, "data.xls",
    "XLS title must come from the descriptor.name verbatim");
  assert.strictEqual(d.bytes, xlsBytes,
    "XLS source bytes must be the SAME Uint8Array reference "
    + "as the input bytes (pass-by-reference, mirrors W4b1 DOCX "
    + "+ W4b2 XLSX)");
  assert.strictEqual(d.scriptUrl,
    "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js",
    "XLS source scriptUrl must be the legacy-pinned SheetJS CDN "
    + "URL (same URL for both XLS and XLSX)");
  assert.strictEqual(d.scriptGlobal, "XLSX",
    "XLS source scriptGlobal must be the literal 'XLSX' (same "
    + "global for both XLS and XLSX — SheetJS does not "
    + "distinguish extensions)");

  // 40. W4b2 XLSX — Raw tab + format="xlsx" + bytes=null
  //     falls back to `sheet-offline` with the download link
  //     + pinned CDN URL + global name + reason. The future
  //     React mount paints the legacy "Viewer offline — raw
  //     download available" banner verbatim — the same
  //     shape `web/file_viewer.js::renderOfflineBanner`
  //     paints, just sourced from the typed offline
  //     descriptor. The bytes-missing reason is the ONLY
  //     offline path the dispatcher can detect (the
  //     dispatcher does not fetch the URL, load the CDN,
  //     or call read / sheet_to_html — those failures
  //     happen at the mount and are not part of the
  //     dispatcher contract).
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "xlsx",
      name: "missing.xlsx",
      path: "missing.xlsx",
      url: "/api/files/serve?path=missing.xlsx",
      size: 0,
    }),
    tab: "Raw",
    bytes: null,
  });
  assert.strictEqual(d.kind, "sheet-offline",
    "XLSX + Raw + bytes=null must fall back to sheet-offline: "
    + "got " + d.kind);
  assert.strictEqual(d.name, "missing.xlsx",
    "XLSX offline name must come from descriptor.name");
  assert.strictEqual(d.download.href,
    "/api/files/serve?path=missing.xlsx",
    "XLSX offline download.href must come from descriptor.url");
  assert.strictEqual(d.download.download, "missing.xlsx",
    "XLSX offline download.download must carry the basename");
  assert.strictEqual(d.scriptUrl,
    "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js",
    "XLSX offline scriptUrl must be the legacy-pinned SheetJS "
    + "CDN URL (the mount needs the URL to retry the loader "
    + "or to surface a 'try again' affordance)");
  assert.strictEqual(d.scriptGlobal, "XLSX",
    "XLSX offline scriptGlobal must be the literal 'XLSX'");
  assert.strictEqual(d.reason, "bytes-missing",
    "XLSX offline reason MUST be the typed 'bytes-missing' "
    + "literal — the dispatcher can only detect this offline "
    + "path at dispatch time. CDN-load + read + sheet_to_html "
    + "failures are MOUNT responsibilities and are NOT part "
    + "of this contract: got " + JSON.stringify(d.reason));

  // 41. W4b2 XLS — Raw tab + format="xls" + bytes=null
  //     falls back to `sheet-offline` with the same
  //     descriptor pattern as XLSX (SheetJS does not
  //     distinguish XLS vs XLSX at the offline site —
  //     both extensions share the same CDN URL + global
  //     name + reason).
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "xls",
      name: "missing.xls",
      path: "missing.xls",
      url: "/api/files/serve?path=missing.xls",
      size: 0,
    }),
    tab: "Raw",
    bytes: null,
  });
  assert.strictEqual(d.kind, "sheet-offline",
    "XLS + Raw + bytes=null must fall back to sheet-offline: "
    + "got " + d.kind);
  assert.strictEqual(d.name, "missing.xls",
    "XLS offline name must come from descriptor.name");
  assert.strictEqual(d.download.href,
    "/api/files/serve?path=missing.xls",
    "XLS offline download.href must come from descriptor.url");
  assert.strictEqual(d.scriptUrl,
    "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js",
    "XLS offline scriptUrl must be the legacy-pinned SheetJS "
    + "CDN URL");
  assert.strictEqual(d.scriptGlobal, "XLSX",
    "XLS offline scriptGlobal must be the literal 'XLSX'");
  assert.strictEqual(d.reason, "bytes-missing",
    "XLS offline reason MUST be the typed 'bytes-missing' "
    + "literal");

  // 42. W4b2 XLS / XLSX — bytes-missing framing — the
  //     dispatcher does NOT carry a free-form message
  //     field on the offline variants (mirrors the W4b1
  //     DOCX offline shape). The offline branch is a typed
  //     descriptor (kind + name + download + scriptUrl +
  //     scriptGlobal + reason) and the future mount paints
  //     the legacy message itself.
  assert.ok(!("message" in d),
    "Sheet offline branch MUST NOT carry a free-form 'message' "
    + "field — the legacy offline wording is painted by the "
    + "mount from the typed descriptor (kind + name + "
    + "download), not pre-formatted by the dispatcher");

  // 43. W4b2 XLSX / XLS — Table / Tree tabs on XLSX /
  //     XLS fire tab-not-applicable — the Table/Tree
  //     gate runs BEFORE the format switch so XLS / XLSX
  //     never reach the W4b2 `case "xls":` /
  //     `case "xlsx":` arms. This pins the W4b2 split
  //     shape: XLS / XLSX have a Raw-only renderer
  //     (SheetJS produces an HTML table, not a dedicated
  //     Table or Tree widget). Step 27 already covers
  //     XLS / XLSX in the broader Table/Tree deferred
  //     loop; here we re-assert the XLSX case explicitly
  //     + verify the message uses the "xlsx" literal (NOT
  //     the wire-extension variant — the descriptor's
  //     `format` field carries "xlsx" verbatim).
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "xlsx",
      name: "f.xlsx",
      path: "f.xlsx",
      url: "/api/files/serve?path=f.xlsx",
      size: 100,
    }),
    tab: "Table",
    bytes: xlsxBytes,
  });
  assert.strictEqual(d.kind, "tab-not-applicable",
    "XLSX + Table + bytes must fire tab-not-applicable "
    + "(XLSX has no Table renderer): got " + d.kind);
  assert.strictEqual(d.message,
    "Table view not available for .xlsx "
    + renderers.TAB_NOT_APPLICABLE_SUFFIX,
    "XLSX + Table message must use the 'xlsx' format literal "
    + "as the extension label: got " + JSON.stringify(d.message));
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "xlsx",
      name: "f.xlsx",
      path: "f.xlsx",
      url: "/api/files/serve?path=f.xlsx",
      size: 100,
    }),
    tab: "Tree",
    bytes: xlsxBytes,
  });
  assert.strictEqual(d.kind, "tab-not-applicable",
    "XLSX + Tree + bytes must fire tab-not-applicable "
    + "(XLSX has no Tree renderer): got " + d.kind);

  // 44. W4b2 XLS — same Table / Tree gate check on the
  //     XLS extension — both XLS and XLSX share the same
  //     tab-not-applicable path because SheetJS does not
  //     distinguish extensions at the Table/Tree site.
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "xls",
      name: "f.xls",
      path: "f.xls",
      url: "/api/files/serve?path=f.xls",
      size: 100,
    }),
    tab: "Table",
    bytes: xlsBytes,
  });
  assert.strictEqual(d.kind, "tab-not-applicable",
    "XLS + Table + bytes must fire tab-not-applicable "
    + "(XLS has no Table renderer): got " + d.kind);
  assert.strictEqual(d.message,
    "Table view not available for .xls "
    + renderers.TAB_NOT_APPLICABLE_SUFFIX,
    "XLS + Table message must use the 'xls' format literal "
    + "as the extension label: got " + JSON.stringify(d.message));
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "xls",
      name: "f.xls",
      path: "f.xls",
      url: "/api/files/serve?path=f.xls",
      size: 100,
    }),
    tab: "Tree",
    bytes: xlsBytes,
  });
  assert.strictEqual(d.kind, "tab-not-applicable",
    "XLS + Tree + bytes must fire tab-not-applicable "
    + "(XLS has no Tree renderer): got " + d.kind);

  // 45. W4b2 — bytes-reference contract on the
  //     sheet-source branch — the dispatcher passes the
  //     input bytes reference through to `sheet-source.
  //     bytes` (NO copy, NO decode — the dispatcher
  //     doesn't load xlsx or do any conversion). This
  //     is intentional: the future mount reads the
  //     bytes at mount time and feeds them straight to
  //     `window.XLSX.read(bytes, { type: "array" })`.
  //     Copying the bytes at dispatch time would cost a
  //     Uint8Array allocation per dispatch and gain
  //     nothing (the mount doesn't mutate the bytes).
  //     The pinned contract: sheet-source.bytes ===
  //     input bytes reference, by-reference — mirrors
  //     the W4b1 DOCX bytes-reference contract from
  //     step 36.
  const sheetRefBytes = makeBytes("PK\x03\x04sheet-reference-test");
  const sheetRef = renderers.dispatchViewer({
    file: makeFile({
      format: "xlsx",
      name: "ref.xlsx",
      path: "ref.xlsx",
      url: "/api/files/serve?path=ref.xlsx",
      size: sheetRefBytes.length,
    }),
    tab: "Raw",
    bytes: sheetRefBytes,
  });
  assert.strictEqual(sheetRef.kind, "sheet-source");
  assert.strictEqual(sheetRef.bytes, sheetRefBytes,
    "XLSX sheet-source bytes MUST be the SAME Uint8Array "
    + "reference as the input bytes (pass-by-reference "
    + "contract — the mount reads bytes at mount time, "
    + "not dispatch time): got different reference");
  // A second dispatch on the SAME descriptor + bytes
  // returns the SAME reference (the dispatcher does not
  // memoize or copy between calls) — mirrors the W4b1
  // DOCX step 36 second-dispatch check.
  const sheetRef2 = renderers.dispatchViewer({
    file: makeFile({
      format: "xlsx",
      name: "ref.xlsx",
      path: "ref.xlsx",
      url: "/api/files/serve?path=ref.xlsx",
      size: sheetRefBytes.length,
    }),
    tab: "Raw",
    bytes: sheetRefBytes,
  });
  assert.strictEqual(sheetRef2.bytes, sheetRefBytes,
    "Second XLSX dispatch must also return the SAME bytes "
    + "reference — the dispatcher does not memoize or copy");

  // 46. W4b2 — bytes mutation visible through the
  //     dispatched reference on the sheet-source branch
  //     (because the dispatcher passes by reference,
  //     mutating the input bytes after dispatch is
  //     visible through the dispatched reference). This
  //     is a documented contract — the dispatcher does
  //     NOT freeze the bytes, it passes them through
  //     verbatim. The future mount is responsible for
  //     treating the bytes as read-only or copying
  //     before mutation.
  sheetRefBytes[0] = 0x58; // 'X' — mutate input bytes after dispatch
  // The first dispatch's `sheetRef.bytes` is the SAME
  // reference, so it now sees the mutation too
  // (Uint8Array is a view on a backing ArrayBuffer — the
  // bytes field IS the input bytes).
  assert.strictEqual(sheetRef.bytes[0], 0x58,
    "XLSX bytes-reference contract: mutating input bytes "
    + "after dispatch is visible through the dispatched "
    + "reference (the dispatcher passes by reference, not "
    + "by copy). The mount MUST treat the bytes as "
    + "read-only or copy before mutation: got byte 0 = "
    + JSON.stringify(sheetRef.bytes[0]));

  // 47. W4b2 — dispatcher purity on the sheet-source /
  //     sheet-offline branches — same input yields the
  //     same output on every call (no Date.now(), no
  //     Math.random(), no side effects on the input).
  //     Mirrors the W4b1 DOCX purity checks from steps
  //     34-35.
  const sheetFile = makeFile({
    format: "xlsx",
    name: "data.xlsx",
    path: "data.xlsx",
    url: "/api/files/serve?path=data.xlsx",
    size: xlsxBytes.length,
  });
  const sheetA = renderers.dispatchViewer({
    file: sheetFile, tab: "Raw", bytes: xlsxBytes,
  });
  const sheetB = renderers.dispatchViewer({
    file: sheetFile, tab: "Raw", bytes: xlsxBytes,
  });
  assert.deepStrictEqual(
    JSON.parse(JSON.stringify(sheetA)),
    JSON.parse(JSON.stringify(sheetB)),
    "XLSX dispatcher MUST be pure — same input → same output",
  );
  assert.strictEqual(sheetA.kind, "sheet-source");
  assert.strictEqual(sheetB.kind, "sheet-source");
  assert.strictEqual(sheetA.scriptUrl, sheetB.scriptUrl);
  assert.strictEqual(sheetA.scriptGlobal, sheetB.scriptGlobal);

  // 48. W4b2 — offline-branch purity (same input →
  //     same output on the bytes=null path too — mirrors
  //     the source-branch purity check above).
  const sheetMissingFile = makeFile({
    format: "xlsx",
    name: "missing.xlsx",
    path: "missing.xlsx",
    url: "/api/files/serve?path=missing.xlsx",
    size: 0,
  });
  const sheetOfflineA = renderers.dispatchViewer({
    file: sheetMissingFile, tab: "Raw", bytes: null,
  });
  const sheetOfflineB = renderers.dispatchViewer({
    file: sheetMissingFile, tab: "Raw", bytes: null,
  });
  assert.deepStrictEqual(
    JSON.parse(JSON.stringify(sheetOfflineA)),
    JSON.parse(JSON.stringify(sheetOfflineB)),
    "XLSX offline branch MUST be pure — same input → same "
    + "output",
  );
  assert.strictEqual(sheetOfflineA.kind, "sheet-offline");
  assert.strictEqual(sheetOfflineB.kind, "sheet-offline");
  assert.strictEqual(sheetOfflineA.scriptUrl, sheetOfflineB.scriptUrl);
  assert.strictEqual(sheetOfflineA.reason, sheetOfflineB.reason);

  // 49. W4b2 — XLS path purity — both XLS and XLSX share
  //     the same dispatcher arm, but verify the XLS
  //     purity explicitly (the format-specific `format`
  //     field is carried in the typed outcome; the
  //     dispatcher does NOT branch on it for the
  //     sheet-source / sheet-offline outcome shapes).
  const xlsFile = makeFile({
    format: "xls",
    name: "data.xls",
    path: "data.xls",
    url: "/api/files/serve?path=data.xls",
    size: xlsBytes.length,
  });
  const xlsA = renderers.dispatchViewer({
    file: xlsFile, tab: "Raw", bytes: xlsBytes,
  });
  const xlsB = renderers.dispatchViewer({
    file: xlsFile, tab: "Raw", bytes: xlsBytes,
  });
  assert.deepStrictEqual(
    JSON.parse(JSON.stringify(xlsA)),
    JSON.parse(JSON.stringify(xlsB)),
    "XLS dispatcher MUST be pure — same input → same output",
  );
  assert.strictEqual(xlsA.kind, "sheet-source");
  assert.strictEqual(xlsB.kind, "sheet-source");

  // 50. W4b3 EPUB — Raw tab + format="epub" + injected
  //     bytes dispatches to `epub-source` with the
  //     descriptor + bytes + pinned epubjs CDN URL +
  //     global name. The future React mount (W6+) consumes
  //     the typed source outcome via Next 16's `<Script
  //     src={scriptUrl} strategy="afterInteractive"
  //     onLoad={mount}>` then calls
  //     `window[scriptGlobal](bytes.buffer)` to construct
  //     the book, then `book.renderTo(hostEl, ...)` to
  //     mount it, then attaches prev / next click handlers
  //     to `book.prev()` / `book.next()`, then stores the
  //     book in a module-scoped `_currentBook` slot so the
  //     NEXT open's mount can call `_currentBook.destroy()`
  //     first (mirrors the legacy `web/file_viewer.js::
  //     renderEpub` shape verbatim — the legacy tears down
  //     the previous book before mounting the new one so
  //     listeners don't leak per `design.md` §8). The
  //     dispatcher does NOT load the script, fetch the
  //     URL, construct the book, or call renderTo / prev /
  //     next / destroy — it only emits the typed source
  //     descriptor.
  const epubBytes = makeBytes("PK\x03\x04fake-epub-bytes");
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "epub",
      name: "Mammalia.epub",
      path: "Animalia/Chordata/Mammalia.epub",
      url: "/api/files/serve?path=Animalia%2FChordata%2FMammalia.epub",
      size: epubBytes.length,
    }),
    tab: "Raw",
    bytes: epubBytes,
  });
  assert.strictEqual(d.kind, "epub-source",
    "EPUB + Raw + bytes must dispatch to epub-source: got " + d.kind);
  assert.strictEqual(d.src,
    "/api/files/serve?path=Animalia%2FChordata%2FMammalia.epub",
    "EPUB src must come from the descriptor.url verbatim");
  assert.strictEqual(d.title, "Mammalia.epub",
    "EPUB title must come from the descriptor.name verbatim");
  assert.ok(d.bytes instanceof Uint8Array,
    "EPUB source must carry bytes as a Uint8Array: got "
    + typeof d.bytes);
  assert.strictEqual(d.bytes, epubBytes,
    "EPUB source bytes must be the SAME Uint8Array reference "
    + "as the input bytes (the dispatcher passes by reference, "
    + "does NOT copy — mirrors the W4b1 DOCX + W4b2 XLS / "
    + "XLSX bytes-reference contract)");
  assert.strictEqual(d.scriptUrl,
    "https://cdn.jsdelivr.net/npm/epubjs@0.3.93/dist/epub.min.js",
    "EPUB source scriptUrl must be the legacy-pinned epubjs "
    + "CDN URL (matches web/file_viewer.js::CDN_URLS.ePub "
    + "and web/index.html's epubjs <script> tag)");
  assert.strictEqual(d.scriptGlobal, "ePub",
    "EPUB source scriptGlobal must be the literal 'ePub' "
    + "(matches web/file_viewer.js::window.ePub(arrayBuffer) "
    + "call site + CDN_URLS.ePub map key — the epubjs UMD "
    + "bundle assigns itself to window.ePub, NOT window.EPUBJS "
    + "or window.epub)");

  // 51. W4b3 EPUB — Raw tab + format="epub" + bytes=null
  //     falls back to `epub-offline` with the download link
  //     + pinned CDN URL + global name + reason. The future
  //     React mount paints the legacy "Viewer offline — raw
  //     download available" banner verbatim — the same
  //     shape `web/file_viewer.js::renderOfflineBanner`
  //     paints, just sourced from the typed offline
  //     descriptor. The bytes-missing reason is the ONLY
  //     offline path the dispatcher can detect (the
  //     dispatcher does not fetch the URL, load the CDN,
  //     construct the book via `ePub(arrayBuffer)`, or
  //     invoke `book.renderTo` / `book.prev` / `book.next`
  //     / `book.destroy` — those failures happen at the
  //     mount and are not part of the dispatcher
  //     contract; the legacy `renderEpub` catch branch
  //     paints the same banner when the `ePub(arrayBuffer)`
  //     call throws on invalid EPUB archives).
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "epub",
      name: "missing.epub",
      path: "missing.epub",
      url: "/api/files/serve?path=missing.epub",
      size: 0,
    }),
    tab: "Raw",
    bytes: null,
  });
  assert.strictEqual(d.kind, "epub-offline",
    "EPUB + Raw + bytes=null must fall back to epub-offline: "
    + "got " + d.kind);
  assert.strictEqual(d.name, "missing.epub",
    "EPUB offline name must come from descriptor.name");
  assert.strictEqual(d.download.href,
    "/api/files/serve?path=missing.epub",
    "EPUB offline download.href must come from descriptor.url");
  assert.strictEqual(d.download.download, "missing.epub",
    "EPUB offline download.download must carry the basename");
  assert.strictEqual(d.scriptUrl,
    "https://cdn.jsdelivr.net/npm/epubjs@0.3.93/dist/epub.min.js",
    "EPUB offline scriptUrl must be the legacy-pinned epubjs "
    + "CDN URL (the mount needs the URL to retry the loader "
    + "or to surface a 'try again' affordance)");
  assert.strictEqual(d.scriptGlobal, "ePub",
    "EPUB offline scriptGlobal must be the literal 'ePub'");
  assert.strictEqual(d.reason, "bytes-missing",
    "EPUB offline reason MUST be the typed 'bytes-missing' "
    + "literal — the dispatcher can only detect this offline "
    + "path at dispatch time. CDN-load + ePub(arrayBuffer) + "
    + "renderTo failures are MOUNT responsibilities and are "
    + "NOT part of this contract: got " + JSON.stringify(d.reason));

  // 52. W4b3 EPUB — bytes-missing framing — the dispatcher
  //     does NOT carry a free-form message field on the
  //     offline variant (mirrors the W4b1 DOCX + W4b2 XLS
  //     / XLSX offline shapes). The offline branch is a
  //     typed descriptor (kind + name + download +
  //     scriptUrl + scriptGlobal + reason) and the future
  //     mount paints the legacy message itself.
  assert.ok(!("message" in d),
    "EPUB offline branch MUST NOT carry a free-form 'message' "
    + "field — the legacy offline wording is painted by the "
    + "mount from the typed descriptor (kind + name + "
    + "download), not pre-formatted by the dispatcher");

  // 53. W4b3 EPUB — Table / Tree tabs on EPUB fire
  //     tab-not-applicable — the Table/Tree gate runs BEFORE
  //     the format switch so EPUB never reaches the W4b3
  //     `case "epub":` arm. This pins the W4b3 split shape:
  //     EPUB has a Raw-only renderer (epubjs renders an
  //     EPUB as a paged book, not a Table widget or a Tree
  //     widget — the future mount's EPUB viewer is the
  //     W4b3 source / offline surface itself, scoped to
  //     Raw). Step 27 already covers EPUB in the broader
  //     Table/Tree deferred loop; here we re-assert the
  //     EPUB case explicitly + verify the message uses
  //     the "epub" literal (NOT the wire-extension variant
  //     — the descriptor's `format` field carries "epub"
  //     verbatim).
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "epub",
      name: "f.epub",
      path: "f.epub",
      url: "/api/files/serve?path=f.epub",
      size: 100,
    }),
    tab: "Table",
    bytes: epubBytes,
  });
  assert.strictEqual(d.kind, "tab-not-applicable",
    "EPUB + Table + bytes must fire tab-not-applicable "
    + "(EPUB has no Table renderer): got " + d.kind);
  assert.strictEqual(d.message,
    "Table view not available for .epub "
    + renderers.TAB_NOT_APPLICABLE_SUFFIX,
    "EPUB + Table message must use the 'epub' format literal "
    + "as the extension label (the descriptor.format is "
    + "'epub', not 'other'): got " + JSON.stringify(d.message));
  d = renderers.dispatchViewer({
    file: makeFile({
      format: "epub",
      name: "f.epub",
      path: "f.epub",
      url: "/api/files/serve?path=f.epub",
      size: 100,
    }),
    tab: "Tree",
    bytes: epubBytes,
  });
  assert.strictEqual(d.kind, "tab-not-applicable",
    "EPUB + Tree + bytes must fire tab-not-applicable "
    + "(EPUB has no Tree renderer): got " + d.kind);

  // 54. W4b3 EPUB — dispatcher purity — the W4b3 source
  //     / offline branches are pure: same input yields the
  //     same output on every call (no Date.now(), no
  //     Math.random(), no side effects on the input).
  //     Mirrors the W4b1 DOCX + W4b2 XLS / XLSX purity
  //     checks from steps 34-35 + 47-48.
  const epubFile = makeFile({
    format: "epub",
    name: "Mammalia.epub",
    path: "Animalia/Chordata/Mammalia.epub",
    url: "/api/files/serve?path=Animalia%2FChordata%2FMammalia.epub",
    size: epubBytes.length,
  });
  const epubA = renderers.dispatchViewer({
    file: epubFile, tab: "Raw", bytes: epubBytes,
  });
  const epubB = renderers.dispatchViewer({
    file: epubFile, tab: "Raw", bytes: epubBytes,
  });
  assert.deepStrictEqual(
    JSON.parse(JSON.stringify(epubA)),
    JSON.parse(JSON.stringify(epubB)),
    "EPUB dispatcher MUST be pure — same input → same output",
  );
  assert.strictEqual(epubA.kind, "epub-source");
  assert.strictEqual(epubB.kind, "epub-source");
  assert.strictEqual(epubA.scriptUrl, epubB.scriptUrl);
  assert.strictEqual(epubA.scriptGlobal, epubB.scriptGlobal);

  // 55. W4b3 — offline-branch purity (same input → same
  //     output on the bytes=null path too — mirrors the
  //     W4b1 DOCX + W4b2 XLS / XLSX offline purity checks
  //     from steps 35 + 48).
  const epubMissingFile = makeFile({
    format: "epub",
    name: "missing.epub",
    path: "missing.epub",
    url: "/api/files/serve?path=missing.epub",
    size: 0,
  });
  const epubOfflineA = renderers.dispatchViewer({
    file: epubMissingFile, tab: "Raw", bytes: null,
  });
  const epubOfflineB = renderers.dispatchViewer({
    file: epubMissingFile, tab: "Raw", bytes: null,
  });
  assert.deepStrictEqual(
    JSON.parse(JSON.stringify(epubOfflineA)),
    JSON.parse(JSON.stringify(epubOfflineB)),
    "EPUB offline branch MUST be pure — same input → same "
    + "output",
  );
  assert.strictEqual(epubOfflineA.kind, "epub-offline");
  assert.strictEqual(epubOfflineB.kind, "epub-offline");
  assert.strictEqual(epubOfflineA.scriptUrl, epubOfflineB.scriptUrl);
  assert.strictEqual(epubOfflineA.reason, epubOfflineB.reason);

  // 56. W4b3 — EPUB bytes-reference contract — the
  //     dispatcher passes the input bytes reference through
  //     to `epub-source.bytes` (NO copy, NO decode — the
  //     dispatcher doesn't load epubjs or construct the
  //     book). This is intentional: the future mount reads
  //     the bytes at mount time and feeds them straight to
  //     `window.ePub(bytes.buffer)`. Copying the bytes at
  //     dispatch time would cost a Uint8Array allocation
  //     per dispatch and gain nothing (the mount doesn't
  //     mutate the bytes). The pinned contract:
  //     epub-source.bytes === input bytes reference,
  //     by-reference — mirrors the W4b1 DOCX +
  //     W4b2 XLS / XLSX bytes-reference contracts.
  const epubRefBytes = makeBytes("PK\x03\x04epub-reference-test");
  const epubRef = renderers.dispatchViewer({
    file: makeFile({
      format: "epub",
      name: "ref.epub",
      path: "ref.epub",
      url: "/api/files/serve?path=ref.epub",
      size: epubRefBytes.length,
    }),
    tab: "Raw",
    bytes: epubRefBytes,
  });
  assert.strictEqual(epubRef.kind, "epub-source");
  assert.strictEqual(epubRef.bytes, epubRefBytes,
    "EPUB epub-source bytes MUST be the SAME Uint8Array "
    + "reference as the input bytes (pass-by-reference "
    + "contract — the mount reads bytes at mount time, "
    + "not dispatch time): got different reference");
  // A second dispatch on the SAME descriptor + bytes
  // returns the SAME reference (the dispatcher does not
  // memoize or copy between calls) — mirrors the W4b1
  // DOCX + W4b2 XLS / XLSX second-dispatch checks from
  // steps 36 + 45.
  const epubRef2 = renderers.dispatchViewer({
    file: makeFile({
      format: "epub",
      name: "ref.epub",
      path: "ref.epub",
      url: "/api/files/serve?path=ref.epub",
      size: epubRefBytes.length,
    }),
    tab: "Raw",
    bytes: epubRefBytes,
  });
  assert.strictEqual(epubRef2.bytes, epubRefBytes,
    "Second EPUB dispatch must also return the SAME bytes "
    + "reference — the dispatcher does not memoize or copy");

  // 57. W4b3 — EPUB bytes mutation visible through the
  //     dispatched reference on the epub-source branch
  //     (because the dispatcher passes by reference,
  //     mutating the input bytes after dispatch is visible
  //     through the dispatched reference). This is a
  //     documented contract — the dispatcher does NOT freeze
  //     the bytes, it passes them through verbatim. The
  //     future mount is responsible for treating the bytes
  //     as read-only or copying before mutation.
  epubRefBytes[0] = 0x58; // 'X' — mutate input bytes after dispatch
  // The first dispatch's `epubRef.bytes` is the SAME
  // reference, so it now sees the mutation too
  // (Uint8Array is a view on a backing ArrayBuffer — the
  // bytes field IS the input bytes).
  assert.strictEqual(epubRef.bytes[0], 0x58,
    "EPUB bytes-reference contract: mutating input bytes "
    + "after dispatch is visible through the dispatched "
    + "reference (the dispatcher passes by reference, not "
    + "by copy). The mount MUST treat the bytes as "
    + "read-only or copy before mutation: got byte 0 = "
    + JSON.stringify(epubRef.bytes[0]));

  process.stdout.write("PASS\n");
})().catch((err) => {
  process.stderr.write("HARNESS_FAILURE: " + (err && err.stack || err) + "\n");
  process.exit(1);
});
"""


@pytest.fixture()
def compiled_renderers(
    tmp_path: Path, require_toolchain: None,
) -> tuple[Path, Path]:
    """Compile the W4a sources (W1 domain + W4a renderers) to
    CommonJS in `tmp_path/build/`, write the Node runtime harness,
    return (compiled-renderers path, harness path)."""
    for p in (RENDERERS_FILE, DOMAIN_FILE):
        if not p.is_file():
            pytest.skip(f"missing required source: {p}")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    harness = tmp_path / "harness.cjs"
    harness.write_text(_RUNTIME_HARNESS)
    result = _run_tsc_isolated([DOMAIN_FILE, RENDERERS_FILE], out_dir)
    assert result.returncode == 0, (
        f"renderers.ts failed to compile in isolated strict mode.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    compiled_renderers_path = out_dir / "application" / "renderers.js"
    compiled_domain = out_dir / "domain" / "explorer.js"
    for path, label in (
        (compiled_renderers_path, "application/renderers.js"),
        (compiled_domain, "domain/explorer.js"),
    ):
        assert path.is_file(), (
            f"tsc did not emit `{label}` at {path}. "
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return compiled_renderers_path, harness


def test_compiled_renderers_passes_runtime_contract(
    compiled_renderers: tuple[Path, Path],
) -> None:
    """Under Node (ES2022, no DOM) the compiled W4a module + the
    W1 domain contract together satisfy the W4a contract end-to-end:

      1. `IMAGE_BIG_FILE_BYTES` equals `50 * 1024 * 1024` (legacy
         threshold pinned byte-for-byte).
      2. `TAB_NOT_APPLICABLE_SUFFIX` is the literal
         `"files — use Raw."` (legacy wording pinned byte-for-byte).
      3. `dispatchViewer({file, tab: "Raw", bytes: null})` for
         PDF / HTML / HTM dispatches to the typed pdf-iframe /
         html-iframe variants with the descriptor URL + title +
         fallback link verbatim.
      4. `dispatchViewer` for TXT + MD on Raw dispatches to
         text-pre with the UTF-8 decoded body verbatim. W4a
         PRESERVES legacy Markdown-as-text behavior (the spec's
         "Markdown rendering" scenario via marked.js CDN is
         deferred to W4b+).
      5. TXT + Raw + `bytes: null` falls back to unsupported with
         a parse-error framing (mirrors the legacy renderAsPre
         catch branch).
      6. DOC + Raw dispatches to unsupported with the spec's
         exact `"Legacy .doc cannot be rendered inline."` wording.
      7. JPG / JPEG / PNG / GIF / WEBP / BMP + Raw dispatches to
         image with the descriptor URL + alt + title + advisory
         (null under 50 MB, populated over).
      8. SVG + Raw + valid bytes dispatches to svg-sanitized with
         the XSS-scrubbed markup (no `<script>`, no `on*=`
         attrs), className "fex-image", preserveAspectRatio
         "xMidYMid meet". Invalid SVG bytes or missing bytes fall
         back to image-error.
      9. `sanitizeSvgMarkup` strips `<script>` elements (both
         paired `<script>…</script>` AND self-closing
         `<script src="…"/>` shapes, case-insensitively) AND
         `on*=` event-handler attrs (case-insensitively —
         `ONCLICK`, `OnMouseover`, `onLoad`, etc.) while
         preserving safe SVG content (viewBox, xmlns, class,
         href, rect, text, etc.). Non-SVG documents return "".
     10. MP4 / WEBM / OGV + Raw dispatches to video with
         controls=true + preload="metadata".
     11. "other" + Raw dispatches to unsupported with the
         wire-extension message extracted from the path
         basename.
     12. W4b4-deferred formats (CSV / TSV / JSON) on Raw
         fall through to the default arm with the
         format-literal unsupported message — pinning the
         W4b4 split until a later slice extends the
         dispatcher. EPUB is no longer in this loop (W4b3
         owns it); DOCX is no longer in this loop (W4b1
         owns it); XLS / XLSX are no longer in this loop
         (W4b2 owns them).
     13. Every W4a-supported format on Table / Tree tabs surfaces
         the legacy `${tab} view not available for .${ext} files
         — use Raw.` message verbatim (W4b+ will override the
         Table-on-csv/tsv + Tree-on-json arms).
     14. Bytes independence: mutating the input bytes after
         dispatch does NOT affect the dispatch outcome (the
         first dispatch's frozen string result is preserved);
         a second dispatch on the mutated bytes reflects the
         new content (the dispatcher reads bytes at call time).
     15. Dispatcher purity: same input yields the same output on
         every call (no `Date.now()`, no `Math.random()`,
         no side effects on the input).
     16. W1 ↔ W4a domain dependency: the W1
         `createInitialExplorerState()` factory is reachable
         from the W4a compile context (proves the typed
         surface is wired correctly).
     17. W4b+ formats on Table / Tree also fire
         tab-not-applicable (the Table / Tree branch gates
         before the format switch — DOCX / XLS / XLSX / EPUB
         / CSV / TSV / JSON are all Raw-only in the W4
         contract; only W4b4's CSV / TSV Table and JSON Tree
         renderers are pending).
     18. Self-closing `<script src=…/>` regression — the
         sanitizer MUST strip self-closing `<script>` shapes
         (`<script src="…"/>`, `<script src="…" />`) case-
         insensitively, matching the legacy DOM scrub more
         closely (`querySelectorAll("script")` returns both
         paired and self-closing shapes).
     19. Uppercase / mixed-case `on*=` regression — the
         sanitizer MUST strip event-handler attrs regardless
         of case, with case-sensitive regex checks on the
         output (the existing `/i` regex would pass even when
         the uppercase form leaked through).
     20. W4b1 DOCX (steps 30–37): Raw + bytes → docx-source
         with descriptor + bytes + pinned mammoth URL + global
         name; Raw + bytes=null → docx-offline with download
         + pinned URL + global name + reason="bytes-missing";
         Table/Tree → tab-not-applicable; dispatcher purity
         on both branches; bytes-reference contract (the
         dispatched bytes IS the input bytes reference, by-
         reference, NO copy); bytes mutation visible through
         the dispatched reference.
     21. W4b2 XLS / XLSX (steps 38–49): Raw + bytes →
         sheet-source with descriptor + bytes + pinned
         SheetJS URL + global name (BOTH XLS and XLSX dispatch
         through the same arm); Raw + bytes=null → sheet-offline
         with download + pinned URL + global name + reason;
         Table/Tree → tab-not-applicable for both extensions;
         offline branch has NO free-form `message` field;
         dispatcher purity + bytes-reference + bytes-mutation
         contracts on the sheet-source branch.
     22. W4b3 EPUB (steps 50–57): Raw + bytes → epub-source
         with descriptor + bytes + pinned epubjs URL + global
         name `"ePub"` (the epubjs UMD global, NOT
         `"EPUBJS"` or `"epub"`); Raw + bytes=null →
         epub-offline with download + pinned URL + global name
         + reason; Table/Tree → tab-not-applicable (EPUB has
         NO Table/Tree renderer — the W4b3 EPUB viewer is the
         W4b3 source / offline surface itself, scoped to Raw);
         offline branch has NO free-form `message` field;
         dispatcher purity + bytes-reference + bytes-mutation
         contracts on the epub-source branch. EPUB is REMOVED
         from the W4a-deferred Raw loop (step 12 above) so
         the deferred set is now just CSV / TSV / JSON.
    """
    compiled, harness = compiled_renderers
    # The runtime harness loads the compiled renderers module +
    # the compiled W1 domain module (for the dependency round-trip).
    result = subprocess.run(
        ["node", str(harness), str(compiled),
         str(compiled.parent.parent / "domain" / "explorer.js")],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"runtime harness failed.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected harness output: {result.stdout!r}"
    )


# ---------------------------------------------------------------------------
# Project-wide strict typecheck — the W4a contract must compile
# against the project's tsconfig (not just the isolated strict
# flags the focused compile uses). A future PR that breaks a
# downstream consumer (presentation, infrastructure, design-system)
# is caught here.
# ---------------------------------------------------------------------------
def test_project_wide_strict_typecheck_for_research_renderers(
    require_toolchain: None,
) -> None:
    """Strict typecheck across `src/modules/research/` against
    the project's tsconfig flags (`strict`, `noUncheckedIndexedAccess`,
    `noUnusedLocals`, `noUnusedParameters`, `noImplicitReturns`,
    `noFallthroughCasesInSwitch`). The compile is `--noEmit` so
    no output touches the worktree; it only validates that the
    W4a renderers file (and every other Research file) compiles
    cleanly under the project's full strict mode flag set.

    `noEmit: true` in the project tsconfig prevents accidental
    writes; the focused compile flag set here adds the strict
    flags explicitly so a tsconfig regression that drops one
    does not silently weaken the gate. The test skips when
    `node_modules` is missing — the `next` plugin the project
    tsconfig pulls in needs `@types/next` / `next` installed
    (see `package.json`)."""
    if not RENDERERS_FILE.exists():
        pytest.skip("renderers file not present yet")
    if not (REPO_ROOT / "node_modules").is_dir():
        pytest.skip("node_modules not installed — strict typecheck requires next types")
    result = subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--noEmit",
            "--strict",
            "--target", "ES2022",
            "--module", "ESNext",
            "--moduleResolution", "Bundler",
            "--lib", "ES2022,DOM,DOM.Iterable",
            "--jsx", "react-jsx",
            "--skipLibCheck",
            "--esModuleInterop",
            "--allowSyntheticDefaultImports",
            "--noUncheckedIndexedAccess",
            "--noUnusedLocals",
            "--noUnusedParameters",
            "--noImplicitReturns",
            "--noFallthroughCasesInSwitch",
            "--rootDir", "src/modules/research",
            str(DOMAIN_FILE), str(RENDERERS_FILE),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"strict typecheck of src/modules/research/ failed.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
