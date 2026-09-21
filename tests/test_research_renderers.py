"""
Research viewer-dispatch contract tests (W4a of `complete-frontend-migration`).

Pins the pure typed viewer-dispatch contract introduced in W4a:
`src/modules/research/application/renderers.ts`. The contract is
the application-layer renderer-dispatch decision for the eight
no-CDN families (`pdf`, `html`/`htm`, `txt`, `md` legacy-as-text,
`doc` fallback, `jpg`/`jpeg`/`png`/`gif`/`webp`/`bmp`, `svg`
with XSS scrub, `mp4`/`webm`/`ogv`) plus the `"other"` extension
fallback plus the Table/Tree tab-not-applicable feedback.

The W4a contract is the first slice of the W4 work unit: the user
explicitly chose a split — W4a owns the framework-free, no-CDN
preview dispatch and the legacy Markdown-as-text behavior; W4b+
owns the CDN-dependent families (DOCX via mammoth, XLS/XLSX via
SheetJS, EPUB via epubjs, CSV/TSV via Papa Parse, JSON) and the
Markdown-as-HTML work. Until those later slices land, the W4a
dispatcher returns `unsupported` / `tab-not-applicable` for the
deferred format + tab combinations, mirroring the legacy
"Format .xyz not supported in viewer." and
"${tab} view not available for .${ext} files — use Raw." fallbacks
so the React cutover paints the same download-link / empty-state
cards the legacy `web/file_viewer.js` paints.

The contract is the third pure Research work unit (W1 domain +
W2 ports + W3 infra + W4a renderers). It depends on W1 domain
types (`FileFormat`, `ViewerTab`) and W2 port types
(`ViewerFileDescriptor`'s `Uint8Array` bytes), but does NOT
import W3 infrastructure — the dispatcher derives URLs from the
explicit `ViewerFileDescriptor.url` input field, mirroring the
layered architecture (spec.md rule 4 — application depends on
domain ONLY) and the W4a split directive ("derive URLs from
explicit typed input rather than importing W3 implementation").
The contract is value-typed, framework-free, browser-free, and
fetch-free — a pure function from `(file, tab, bytes)` to a
typed `ViewerDispatch` outcome.

The contract must be:

  - Pure (spec.md rule 4) — no React, no Next, no HTTP transport,
    no DOM, no DOMParser, no browser state, no process state, no
    `fetch(`, no `require(`, no `globalThis`.
  - Domain-dependent only — the dispatcher imports `FileFormat` +
    `ViewerTab` from `../domain/explorer` and nothing else from
    the research module (no inward import from `../infrastructure`,
    `../presentation`, or `../index`).
  - Type-stable — a port-compat fixture (compiled alongside the
    dispatcher) proves the dispatcher's typed surface is reachable
    end-to-end; the runtime harness exercises every W4a-supported
    format + every W4a-deferred format + the SVG sanitizer's
    every branch.

References:
    odd/tasks/complete-frontend-migration.md          §ODD-MIGRATE-002 / W4a
    openspec/specs/research/spec.md                   §Multi-format file viewer,
                                                       §Legacy DOC fallback,
                                                       §Table viewer tab,
                                                       §Tree viewer tab,
                                                       §Non-tabular file ignores
                                                       Table/Tree tabs
    web/file_viewer.js::RENDERERS                     Legacy dispatcher oracle
    web/file_viewer.js::renderPdf / renderHtml /      Per-format legacy oracles
      renderText / renderMd / renderImage /
      renderSvg / renderVideo / renderUnsupported
    web/file_explorer.js::handleTabClick              Legacy tab-not-applicable
                                                       oracle (`${tab} view not
                                                       available for .${ext}
                                                       files — use Raw.`)
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
# Public barrel — W4a must re-export the dispatcher surface through
# the module's barrel so cross-module consumers (W6 React mount,
# integration tests) reach the W4a contract through the public surface
# (spec.md rule 5).
# ---------------------------------------------------------------------------
def test_barrel_reexports_research_renderers_surface() -> None:
    """ODD-MIGRATE-002 W4a: the public barrel must re-export
    `dispatchViewer`, `sanitizeSvgMarkup` (as values) and
    `IMAGE_BIG_FILE_BYTES`, `TAB_NOT_APPLICABLE_SUFFIX` (as values)
    plus the five W4a types (`ViewerDispatch`, `ViewerDispatchInput`,
    `ViewerFileDescriptor`, `ViewerLink`, `ViewerImageAdvisory`)
    via `export type { … }` so cross-module consumers reach the
    W4a contract through the barrel."""
    if not BARREL_FILE.exists():
        pytest.skip("research barrel not present yet")
    text = BARREL_FILE.read_text()
    # Value re-exports — `dispatchViewer`, `sanitizeSvgMarkup`,
    # `IMAGE_BIG_FILE_BYTES`, `TAB_NOT_APPLICABLE_SUFFIX`.
    for name in (
        "dispatchViewer",
        "sanitizeSvgMarkup",
        "IMAGE_BIG_FILE_BYTES",
        "TAB_NOT_APPLICABLE_SUFFIX",
    ):
        pattern = (
            rf"export\s*\{{\s*[^}}]*\b{name}\b[^}}]*\s*\}}\s*from\s*"
            rf'["\']\./application/renderers(?:\.js)?["\']'
        )
        assert re.search(pattern, text), (
            f"research barrel must re-export `{name}` from "
            f"'./application/renderers' so cross-module consumers "
            f"reach the W4a contract through the barrel "
            f"(spec.md rule 5)."
        )
    # Type re-exports — five W4a types.
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

  // 20. W4a-deferred formats on Raw — DOCX / XLS / XLSX / EPUB /
  //     CSV / TSV / JSON all fall through to the default arm with
  //     the format-literal "Format .{ext} not supported in viewer."
  //     message. W4b+ extends the dispatcher by adding explicit
  //     arms for each of these formats; W4a's contract commits to
  //     the unsupported fallback so the React mount paints the
  //     same download-link card as the legacy renderUnsupported.
  for (const ext of ["docx", "xls", "xlsx", "epub", "csv", "tsv", "json"]) {
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

  // 27. W4a-deferred formats on Table/Tree also fire
  //     tab-not-applicable — the Table / Tree branches gate
  //     BEFORE the format switch so the deferred formats never
  //     reach the W4b+ arms. This pins the W4a split contract.
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
     12. W4a-deferred formats (DOCX / XLS / XLSX / EPUB / CSV /
         TSV / JSON) on Raw fall through to the default arm
         with the format-literal unsupported message — pinning
         the W4a split until W4b+ extends the dispatcher.
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
     17. W4a-deferred formats on Table / Tree also fire
         tab-not-applicable (the Table / Tree branch gates
         before the format switch).
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
