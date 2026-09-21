"""
Research application contract tests (W2 of `complete-frontend-migration`).

Pins the typed ExplorerRepository port introduced in W2: the
application-layer contract that describes typed file-tree retrieval
(`fetchFiles()` → `ExplorerTree`) and safe file-serving input/output
(`fetchFileServe(request)` → typed bytes + Content-Type + filename)
using W1's `ExplorerTree` domain type.

The contract is the second of the six pure Research work units
(W1–W6 establish domain/ports/API/search/renderers; W7+ mount the
React UI). It is the foundation every later explorer work unit
builds on:

  - W3 infrastructure adapter — `src/modules/research/infrastructure/
    api.ts` — declares `fetchFiles` + `fetchFileServe` whose wider
    signatures (transport-level fetch, baseUrl, signal) satisfy
    `ExplorerRepository` via TypeScript structural function
    subtyping (mirrors how the merged taxonomy adapter satisfies
    `TaxonomyRepository` — `tests/test_taxonomy_application.py`).
  - W6 React mount — `src/modules/research/presentation/` —
    consumes `ExplorerRepository` through DI / a provider, never
    through the deep infra import (spec.md rule 5).

The port must be:

  - Pure (spec.md rule 4) — no React, no Next, no HTTP transport,
    no DOM, no browser state, no process state.
  - Domain-dependent only — the port imports `ExplorerTree` from
    `../domain/explorer` and nothing else from the research module
    (no inward import from `../infrastructure`, `../presentation`,
    `../index`, or any other module).
  - Structurally compatible with the future infrastructure adapter
    — a minimal mock implementing `ExplorerRepository` MUST compile
    against the port without explicit casts or annotations. A
    port-compat fixture (compiled alongside the port) proves the
    contract is implementable; the runtime harness then exercises
    the mock so the typed surface is verified end-to-end.

References:
    odd/tasks/complete-frontend-migration.md          §ODD-MIGRATE-002 / W2
    openspec/specs/research/spec.md                   §Recursive directory
                                                       listing endpoint,
                                                       §Path-traversal-safe
                                                       file streaming endpoint,
                                                       §Content-Type by extension
    api/server.py::list_research_root()               Tree-shape oracle
    api/server.py::serve_research_file()              File-serve oracle
    web/file_explorer.js::mount()                     Legacy tree fetcher
    web/file_explorer.js::serveUrl()                  Legacy serve URL
                                                       builder
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "src" / "modules" / "research" / "application"
PORTS_FILE = APP_DIR / "ports.ts"
DOMAIN_FILE = REPO_ROOT / "src" / "modules" / "research" / "domain" / "explorer.ts"


# Comment-stripping regexes — mirrors `tests/test_domain_purity.py` so
# author-friendly documentation can reference forbidden-token words
# (e.g. "the React lazy loader", "the browser-state module") in JSDoc
# without tripping the application-layer purity guard. Block comments
# are matched first so a `//` inside a `/* ... */` is not treated as
# a line-comment opener. Newlines pass through unchanged so the
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


# Forbidden tokens for the application layer. Spec.md rule 4:
# application depends on domain ONLY — no framework, no I/O, no
# browser state, no HTTP transport, no process state. The list mirrors
# `tests/test_taxonomy_application.py::_FORBIDDEN` and adds the
# category-level deep-import paths so a future PR that imports from
# the future `../infrastructure`, `../presentation`, or `../index`
# folders is caught at review (the rule that protects the layered
# architecture). Comments are stripped before scanning so author-
# friendly JSDoc never trips the guard.
_FORBIDDEN: tuple[str, ...] = (
    # framework
    "react", "next", "nextjs",
    "fastapi", "starlette", "pydantic",
    # I/O / network — application port describes the contract, not
    # the transport. The infrastructure layer (W3) owns fetch.
    "fetch(",
    # browser / process state — application is framework-free.
    "localStorage", "document.", "window.", "process.",
    # CommonJS / globalThis guards — application stays ESM-only.
    "require(", "globalThis",
    # Cross-layer deep imports — application depends on domain ONLY.
    # A future PR importing `../infrastructure/api.js`, `../presentation/
    # Explorer.tsx`, or `../index` (the public barrel — consumers
    # reach the application port through the barrel, never via a
    # reverse deep import) breaks spec.md rule 5.
    "../infrastructure", "../presentation", "../index",
    # Cross-module imports — research application is isolated from
    # sibling modules. Consumers compose at the barrel boundary, not
    # inside the application folder.
    "../../taxonomy", "../../design-system",
    "../../browser-state", "../../app-shell",
)


@pytest.fixture()
def require_toolchain() -> None:
    """Skip when npx / node are not on PATH — the focused compile +
    runtime harness needs both to validate the port contract."""
    if not (shutil.which("npx") and shutil.which("node")):
        pytest.skip("npx + node required on PATH for compile/runtime test")


# ---------------------------------------------------------------------------
# File presence + plain-TypeScript extension + spec.md rule 4 purity.
# ---------------------------------------------------------------------------
def test_application_ports_file_exists() -> None:
    """`src/modules/research/application/ports.ts` exists at the canonical
    path W2 ships. RED marker: before the file lands, this assertion
    fails outright — the focused compile + runtime harness also
    skips, so every downstream W2 contract test observes RED until
    the port file is authored.
    """
    assert PORTS_FILE.is_file(), (
        f"missing application port file: {PORTS_FILE}. W2 ships this "
        f"file as the typed ExplorerRepository contract."
    )


def test_application_ports_file_is_plain_typescript() -> None:
    """`.ts`, not `.tsx` — the application port is pure types +
    constants, no JSX. Mirrors the taxonomy `ports.ts` convention
    (spec.md rule 4 — JSX belongs to presentation)."""
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    assert PORTS_FILE.suffix == ".ts", (
        f"application port file must be TypeScript; got suffix={PORTS_FILE.suffix}"
    )


def test_application_ports_file_has_no_framework_or_io_tokens() -> None:
    """Spec.md rule 4 — the application port stays free of framework,
    I/O, browser, and process tokens. Source-level guard mirrors
    `tests/test_taxonomy_application.py::test_application_file_purity`
    so a future PR that imports `react`, `next`, `fetch(`, or
    `localStorage` is caught at review. Comments are stripped so
    JSDoc can reference forbidden-token words (e.g. "the React
    mount", "the legacy fetch consumer") without tripping the
    guard."""
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    text = _strip_ts_comments(PORTS_FILE.read_text())
    for token in _FORBIDDEN:
        assert token not in text, (
            f"ports.ts must stay free of {token!r}; spec.md rule 4 "
            f"forbids framework / I/O / cross-layer references in the "
            f"application layer."
        )


def test_application_ports_file_imports_only_from_domain() -> None:
    """Spec.md rule 4 (inward deps): application depends on domain
    ONLY. The port must import `ExplorerTree` (and any future
    shared domain helpers) from `../domain/explorer`; it MUST NOT
    import from `../infrastructure` (the future W3 adapter),
    `../presentation` (the future W6+ React mount), or `../index`
    (the public barrel — consumers reach the port through the
    barrel, never via a reverse deep import inside the module).
    A future PR that pulls the future infra adapter or React
    mount into the application layer breaks the layered rule at
    review. Mirrors `tests/test_taxonomy_application.py::
    test_application_file_purity::assert re.search(
    r'from\\s+[\"\\']\\.\\./domain/taxon...'`."""
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    text = _strip_ts_comments(PORTS_FILE.read_text())
    # Required: the port imports the W1 domain type so the file-tree
    # retrieval contract stays typed verbatim against the legacy
    # `web/state.js::state.explorer.tree` shape.
    assert re.search(
        r'from\s+["\']\.\./domain/explorer(?:\.js)?["\']',
        text,
    ), (
        "ports.ts must import the W1 domain contract from "
        "'../domain/explorer' so the typed surface stays anchored "
        "at the W1 ExplorerTree type."
    )
    # Forbidden: any import from the future infrastructure layer,
    # presentation layer, or the public barrel.
    for forbidden in (
        "../infrastructure", "../presentation", "../index",
    ):
        assert forbidden not in text, (
            f"ports.ts must NOT import from {forbidden!r}; spec.md "
            f"rule 4 keeps application layer inward-only (domain), "
            f"and rule 5 forbids reverse deep imports through the "
            f"barrel."
        )


# ---------------------------------------------------------------------------
# Port surface — source-level contracts.
# ---------------------------------------------------------------------------
def test_application_ports_declares_explorer_repository_interface() -> None:
    """W2 commits to a named export `ExplorerRepository` as a
    TypeScript interface — the port name follows the taxonomy
    convention (`TaxonomyRepository` — `tests/test_taxonomy_application.py::
    test_application_surface_contract`). Dropping the export breaks
    every W3+ consumer that wires the typed port through DI /
    a provider; this assertion pins the named interface so a
    future PR cannot silently rename it (e.g. `ResearchRepository`,
    `ResearchPort`) without breaking this guard.
    """
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    text = PORTS_FILE.read_text()
    assert re.search(
        r"export\s+interface\s+ExplorerRepository\b",
        text,
    ), (
        "ports.ts must declare `export interface ExplorerRepository` "
        "as the typed application-layer port for the Browser-tab "
        "file-explorer data source."
    )


def test_application_ports_declares_explorer_file_serve_request() -> None:
    """The safe file-serving INPUT shape — `ExplorerFileServeRequest`
    declares `{ readonly path: string }` so the Browser tab can pass
    the file's location relative to the research root to the future
    infrastructure adapter (mirrors `web/file_explorer.js::serveUrl`'s
    `encodeURIComponent(relativePath)` argument). The path string is
    the only required field; the FastAPI server enforces the safety
    contract (`api/server.py::serve_research_file`:
    `Query(min_length=1, max_length=4096)` + `_safe_resolve()`). A
    future PR that drops the `path` field breaks the adapter
    signature; adding a `taxonId` filter would land as a separately
    authorized change to the port.
    """
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    text = PORTS_FILE.read_text()
    m = re.search(
        r"export\s+interface\s+ExplorerFileServeRequest\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, (
        "ports.ts must declare `export interface ExplorerFileServeRequest` "
        "as the typed input shape for safe file serving."
    )
    block = m.group(0)
    assert re.search(r"\breadonly\s+path\s*:\s*string\b", block), (
        "ExplorerFileServeRequest must declare `readonly path: string` "
        "(the relative path inside the research root that the server's "
        "`/api/files/serve?path=...` endpoint accepts)."
    )


def test_application_ports_declares_explorer_file_serve_result() -> None:
    """The safe file-serving OUTPUT shape — `ExplorerFileServeResult`
    declares `{ readonly content: Uint8Array; readonly contentType: string;
    readonly filename: string }`. `content` carries the file bytes
    (`Uint8Array` is the ES2022 byte type — mirrors how
    `fetch(...).arrayBuffer()` surfaces the body); `contentType` is the
    server's Content-Type header value matched per the spec table
    (`openspec/specs/research/spec.md` §Content-Type by extension);
    `filename` is the basename the server emits via
    `Content-Disposition: inline; filename="<basename>"`. All three
    fields are `readonly` so the typed contract stays immutable
    end-to-end (mirrors `ExplorerState` / `ExplorerFileNode`
    readonly contract from W1 — `tests/test_research_domain.py::
    test_domain_file_explorer_state_fields_are_readonly`)."""
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    text = PORTS_FILE.read_text()
    m = re.search(
        r"export\s+interface\s+ExplorerFileServeResult\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, (
        "ports.ts must declare `export interface ExplorerFileServeResult` "
        "as the typed output shape for safe file serving."
    )
    block = m.group(0)
    # All three fields MUST be present and typed correctly.
    for field, type_re in (
        ("content", r"\breadonly\s+content\s*:\s*Uint8Array\b"),
        ("contentType", r"\breadonly\s+contentType\s*:\s*string\b"),
        ("filename", r"\breadonly\s+filename\s*:\s*string\b"),
    ):
        assert re.search(type_re, block), (
            f"ExplorerFileServeResult must declare `{field}` typed "
            f"against `{type_re}` — see the file-serving contract in "
            f"api/server.py::serve_research_file."
        )


def test_application_ports_declares_fetch_files_method() -> None:
    """The file-tree retrieval method — `fetchFiles(): Promise<ExplorerTree>`
    maps 1:1 to `GET /api/files` (`api/server.py::list_research_root`).
    The return type MUST be the W1 `ExplorerTree` domain interface
    (so the React mount reads the typed shape without coercion). The
    parameter list MUST be empty — the FastAPI endpoint takes no
    query params today, and a future server-side filter would land
    as a separately authorized port extension (not a silent signature
    change). Mirrors the taxonomy port convention
    (`fetchTaxon(id): Promise<Taxon>` — the adapter's wider transport
    options are dropped on the port signature)."""
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    text = PORTS_FILE.read_text()
    # Look for the method signature on the ExplorerRepository
    # interface. We scan the ExplorerRepository block so a
    # search-replace that mangles the field stays caught.
    m = re.search(
        r"export\s+interface\s+ExplorerRepository\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, (
        "ExplorerRepository interface must be declared in ports.ts."
    )
    block = m.group(0)
    # The signature may be single-line OR multi-line (the typical
    # prettier-formatted shape splits `fetchFiles(): Promise<...>`
    # across two lines). Match either form, tolerating whitespace
    # between tokens. The parameter list MUST be empty — a future
    # PR that adds a parameter would be a separately authorized
    # port extension.
    assert re.search(
        r"\bfetchFiles\s*\(\s*\)\s*:\s*Promise\s*<\s*ExplorerTree\s*>",
        block,
    ), (
        "ExplorerRepository.fetchFiles must be declared "
        "`fetchFiles(): Promise<ExplorerTree>` — maps 1:1 to "
        "GET /api/files (api/server.py::list_research_root)."
    )


def test_application_ports_declares_fetch_file_serve_method() -> None:
    """The safe file-serving method — `fetchFileServe(request:
    ExplorerFileServeRequest): Promise<ExplorerFileServeResult>`
    maps 1:1 to `GET /api/files/serve?path=<rel>`
    (`api/server.py::serve_research_file`). The single parameter
    MUST be the typed request shape; the return type MUST be the
    typed result shape. Future transport-level options (fetch,
    baseUrl, signal) belong to the infrastructure adapter
    signature and are silently dropped on the narrower port
    signature via TypeScript structural function subtyping."""
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    text = PORTS_FILE.read_text()
    m = re.search(
        r"export\s+interface\s+ExplorerRepository\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, (
        "ExplorerRepository interface must be declared in ports.ts."
    )
    block = m.group(0)
    # The signature may be single-line OR multi-line (the typical
    # prettier-formatted shape splits `fetchFileServe(\n  request:\n)`
    # across three lines). Match either form, tolerating whitespace
    # between tokens + an optional trailing comma inside the
    # parameter list. TypeScript allows both styles; the contract
    # only cares about the typed names + the parameter + return
    # shape, not the whitespace.
    assert re.search(
        r"\bfetchFileServe\s*\("
        r"\s*request\s*:\s*ExplorerFileServeRequest\s*,?\s*"
        r"\)"
        r"\s*:\s*Promise\s*<\s*ExplorerFileServeResult\s*>",
        block,
    ), (
        "ExplorerRepository.fetchFileServe must be declared "
        "`fetchFileServe(request: ExplorerFileServeRequest): "
        "Promise<ExplorerFileServeResult>` — maps 1:1 to "
        "GET /api/files/serve?path=... "
        "(api/server.py::serve_research_file)."
    )


def test_application_ports_declares_port_name_constant() -> None:
    """Stable string identity for DI containers / diagnostic guards
    — `EXPLORER_PORT_NAME` exports the literal `"ExplorerRepository"`
    so consumers can branch on the port identity without importing
    the interface directly (mirrors `TAXONOMY_PORT_NAME` in
    `tests/test_taxonomy_application.py::test_application_surface_contract`).
    The constant MUST be a string literal (not a computed value) so
    a future PR that renames the interface trips this guard."""
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    text = PORTS_FILE.read_text()
    m = re.search(
        r"export\s+const\s+EXPLORER_PORT_NAME\b[^;]*;",
        text,
    )
    assert m, (
        "ports.ts must export `EXPLORER_PORT_NAME` as a const so DI "
        "containers / diagnostic guards can branch on the port "
        "identity without importing the interface."
    )
    declaration = m.group(0)
    assert '"ExplorerRepository"' in declaration, (
        "EXPLORER_PORT_NAME must be the literal string "
        '"ExplorerRepository" so the constant matches the port '
        "interface name exactly."
    )


def test_application_ports_does_not_export_default() -> None:
    """TRIANGULATE — the application port file MUST NOT export a
    default symbol. The taxonomy port file
    (`tests/test_taxonomy_application.py::test_application_file_purity`)
    pins named exports only; a future PR that flips to
    `export default …` would silently break barrel re-exports and
    DI bindings. This guard catches the regression at review."""
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    text = PORTS_FILE.read_text()
    assert not re.search(r"^\s*export\s+default\b", text, re.MULTILINE), (
        "ports.ts must NOT export a default symbol — the W2 contract "
        "pins named exports only (EXPLORER_PORT_NAME, the three "
        "interfaces)."
    )


def test_application_ports_result_fields_are_readonly() -> None:
    """TRIANGULATE — every field on `ExplorerFileServeResult` MUST
    be declared `readonly` so the typed surface stays immutable
    end-to-end (mirrors `ExplorerState` / `ExplorerFileNode`
    readonly contract from W1 — `tests/test_research_domain.py::
    test_domain_file_explorer_state_fields_are_readonly`). A future
    PR that drops `readonly` on `content` would let a renderer
    mutate the byte buffer in place and silently corrupt concurrent
    consumers; the guard catches the regression at review."""
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    text = PORTS_FILE.read_text()
    m = re.search(
        r"export\s+interface\s+ExplorerFileServeResult\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, "ExplorerFileServeResult interface must be declared in ports.ts."
    block = m.group(0)
    for field in ("content", "contentType", "filename"):
        assert re.search(rf"\breadonly\s+{field}\b", block), (
            f"ExplorerFileServeResult.{field} must be declared `readonly` "
            f"so the typed output stays immutable end-to-end."
        )


def test_application_ports_request_field_is_readonly() -> None:
    """TRIANGULATE — the `path` field on `ExplorerFileServeRequest`
    MUST be declared `readonly` so a renderer / hook cannot mutate
    the request after construction (mirrors the readonly contract
    on `ExplorerState.openFilePath` from W1 — `tests/test_research_
    domain.py::test_domain_file_explorer_state_fields_are_readonly`).
    A future PR that drops `readonly` would let a caller overwrite
    the request path between construction and dispatch, breaking the
    wire-shaped contract that the FastAPI server relies on for the
    path-traversal-safety check."""
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    text = PORTS_FILE.read_text()
    m = re.search(
        r"export\s+interface\s+ExplorerFileServeRequest\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, "ExplorerFileServeRequest interface must be declared in ports.ts."
    block = m.group(0)
    assert re.search(r"\breadonly\s+path\b", block), (
        "ExplorerFileServeRequest.path must be declared `readonly` so "
        "the typed input stays immutable end-to-end."
    )


def test_application_ports_explorer_repository_methods_are_in_order() -> None:
    """TRIANGULATE — the two methods on `ExplorerRepository` MUST
    appear in the contract order `fetchFiles` then `fetchFileServe`.
    The order mirrors the FastAPI endpoint convention (the Browser
    tab fires `GET /api/files` first to load the tree, then
    `GET /api/files/serve?path=...` when the user opens a file —
    see `web/file_explorer.js::mount`). A future PR that reorders
    the methods has no runtime impact (TypeScript interfaces are
    unordered), but the order is part of the review-facing contract
    so the source reads top-to-bottom the same way the Browser tab
    consumes the endpoints."""
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
    text = PORTS_FILE.read_text()
    m = re.search(
        r"export\s+interface\s+ExplorerRepository\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, "ExplorerRepository interface must be declared in ports.ts."
    block = m.group(0)
    fetch_files_idx = block.find("fetchFiles")
    fetch_file_serve_idx = block.find("fetchFileServe")
    assert fetch_files_idx >= 0 and fetch_file_serve_idx >= 0, (
        "ExplorerRepository must declare both `fetchFiles` and "
        "`fetchFileServe` (see tests for the exact signatures)."
    )
    assert fetch_files_idx < fetch_file_serve_idx, (
        "ExplorerRepository must declare `fetchFiles` BEFORE "
        "`fetchFileServe` so the source reads in the same order "
        "the Browser tab consumes the endpoints (tree fetch → "
        "file open)."
    )


# ---------------------------------------------------------------------------
# Compile + runtime contract — strict mode, ES2022 only, no DOM.
# ---------------------------------------------------------------------------
def _run_tsc(
    out_dir: Path,
    sources: list[Path],
    extra: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Compile the W2 sources in isolation. Flags mirror project
    tsconfig + design.md §Interfaces/Contracts: `--strict`,
    `--target ES2022`, `--module commonjs` (so Node can `require`
    the output), `--lib ES2022` (no DOM — application must not
    depend on browser types). The `sources` list carries every
    file the harness depends on (domain + ports + port-compat
    fixture)."""
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


# Port-compat fixture — a minimal mock implementation of
# `ExplorerRepository` that proves the port's surface is
# implementable WITHOUT an explicit cast or annotation. Mirrors
# the ODD-NTP-001 / PR 5b port-compat pattern
# (`tests/test_taxonomy_application.py::_PORT_COMPAT_FIXTURE`).
# The mock carries exactly the two port methods; assigning it to
# `ExplorerRepository` exercises structural function subtyping so
# a future W3 infrastructure adapter can satisfy the port without
# importing the application layer (and without a coordinated
# application-layer change). The fixture compiles against the
# focused compile, so a port surface change is caught at the
# compile gate before the runtime harness runs.
_PORT_COMPAT_FIXTURE = r"""
import type { ExplorerTree } from "../domain/explorer";
import type {
  ExplorerRepository,
  ExplorerFileServeRequest,
  ExplorerFileServeResult,
} from "./ports";

/** Minimal port-compat mock — satisfies `ExplorerRepository`
 *  via TypeScript structural function subtyping. Mirrors the
 *  taxonomy port-compat fixture
 *  (`tests/test_taxonomy_application.py::_PORT_COMPAT_FIXTURE`):
 *  the assignment `const _port: ExplorerRepository = mockRepo`
 *  fails at the strict compile gate if the port signature drifts,
 *  so the contract stays honest at the typed boundary. */
const mockRepo: ExplorerRepository = {
  fetchFiles: async (): Promise<ExplorerTree> => ({
    exists: true,
    root: null,
    filesystem_path: "/tmp/research",
  }),
  fetchFileServe: async (
    _request: ExplorerFileServeRequest,
  ): Promise<ExplorerFileServeResult> => ({
    content: new Uint8Array([0x68, 0x69]),
    contentType: "text/plain",
    filename: "hi.txt",
  }),
};

/** Re-export the mock so the runtime harness can `require()` it
 *  after tsc emits the JS. The compile-time port-compat check
 *  fires on the assignment above. */
export const __port_compatible__ = mockRepo;
"""


# Runtime harness — loaded by Node after tsc has emitted the
# port-compat fixture. Exercises every externally observable
# contract: the port name constant, the W1-derived request /
# result shapes, and the structural subtyping check (the mock
# can be assigned to the port at runtime — every method is a
# function, every return value is the right shape).
_RUNTIME_HARNESS = r"""
// CJS does not support top-level await (only ESM does), so the
// harness wraps the async body in an IIFE. The IIFE returns a
// Promise; we `.catch` to surface unhandled rejections as a
// non-zero exit code (the test harness reads `returncode != 0`
// as the failure marker).
const path = require("path");
const ports = require(path.resolve(process.argv[2]));
const fixture = require(path.resolve(process.argv[3]));
const domain = require(path.resolve(process.argv[4]));

const eq = (g, w) => JSON.stringify(g) === JSON.stringify(w);
const fail = (l) => {
  process.stderr.write("FAIL " + l + "\n");
  process.exit(1);
};

(async () => {
  // 1. Port name constant — stable string identity for DI.
  if (ports.EXPLORER_PORT_NAME !== "ExplorerRepository") {
    fail("port_name_literal");
  }

  // 2. Port-compat fixture — the mock must be a usable repository
  //    (every method is a function, every method returns a Promise
  //    resolving to the right shape). The compile-time port check
  //    already proved structural compatibility; the runtime check
  //    proves the contract is wired correctly end-to-end.
  const repo = fixture.__port_compatible__;
  if (typeof repo.fetchFiles !== "function") fail("fetchFiles_is_function");
  if (typeof repo.fetchFileServe !== "function") fail("fetchFileServe_is_function");

  // 3. fetchFiles — returns an ExplorerTree-shaped object. The
  //    mock returns `{ exists: true, root: null, filesystem_path:
  //    "/tmp/research" }`; every ExplorerTree field must be present
  //    and typed correctly. Mirrors the W1 domain contract
  //    (`tests/test_research_domain.py::test_domain_file_explorer_
  //    state_fields_are_readonly`).
  const tree = await repo.fetchFiles();
  if (tree.exists !== true) fail("tree.exists");
  if (tree.root !== null) fail("tree.root");
  if (tree.filesystem_path !== "/tmp/research") fail("tree.filesystem_path");

  // 4. fetchFileServe — accepts a typed ExplorerFileServeRequest,
  //    returns a typed ExplorerFileServeResult. The mock returns the
  //    literal `Uint8Array([0x68, 0x69])` (= "hi"), `text/plain`, and
  //    `hi.txt`. The runtime harness asserts every field — a future
  //    port rename trips here at compile time (the fixture must
  //    reference the new names) and at runtime (the harness must
  //    reference the new names).
  const result = await repo.fetchFileServe({ path: "subdir/hi.txt" });
  if (!(result.content instanceof Uint8Array)) fail("result.content_is_uint8array");
  if (result.content.length !== 2) fail("result.content_length");
  if (result.content[0] !== 0x68) fail("result.content_byte_0");
  if (result.content[1] !== 0x69) fail("result.content_byte_1");
  if (result.contentType !== "text/plain") fail("result.contentType");
  if (result.filename !== "hi.txt") fail("result.filename");

  // 5. Domain type round-trip — `ExplorerTree` from W1 must be the
  //    same module the port depends on. Asserting the mock's
  //    fetchFiles return value passes `Object.keys(...)` against the
  //    W1 `ExplorerTree` shape (the three fields) catches a future
  //    PR that imports a DIFFERENT `ExplorerTree` (e.g. from a
  //    renamed domain file) into the application layer.
  const expectedTreeKeys = ["exists", "filesystem_path", "root"].sort();
  const actualTreeKeys = Object.keys(tree).sort();
  if (!eq(actualTreeKeys, expectedTreeKeys)) fail("tree_keys");

  // 6. Result type round-trip — same check for `ExplorerFileServeResult`.
  //    The three fields are `content`, `contentType`, `filename`.
  const expectedResultKeys = ["content", "contentType", "filename"].sort();
  const actualResultKeys = Object.keys(result).sort();
  if (!eq(actualResultKeys, expectedResultKeys)) fail("result_keys");

  // 7. Independence — calling `fetchFileServe` twice must return
  //    independent `Uint8Array` instances (the port contract is
  //    value-typed; a future implementation that returns a shared
  //    buffer would corrupt concurrent renderers). Mirrors the W1
  //    independence check on `createInitialExplorerState()`
  //    (`tests/test_research_domain.py::test_domain_file_initial_
  //    states_are_independent`).
  const a = await repo.fetchFileServe({ path: "a.bin" });
  const b = await repo.fetchFileServe({ path: "b.bin" });
  a.content[0] = 0xff;
  if (b.content[0] === 0xff) fail("content_independence");

  // 8. Domain import — the domain module's exported W1 surface
  //    (ExplorerState, ExplorerTree, etc.) MUST be reachable from the
  //    fixture's compile context (proves the W1 ↔ W2 dependency is
  //    wired correctly). The harness imports the domain module
  //    directly and asserts the ExplorerTree shape is the same
  //    one the fixture's compile-time port-compat check used.
  if (typeof domain.createInitialExplorerState !== "function") {
    fail("domain_initial_state_factory");
  }
  const initial = domain.createInitialExplorerState();
  if (initial.tree !== null) fail("domain_initial_tree_is_null");

  process.stdout.write("PASS\n");
})().catch((err) => {
  process.stderr.write("HARNESS_ERROR " + (err && err.message ? err.message : String(err)) + "\n");
  process.exit(1);
});
"""


@pytest.fixture()
def compiled_application(
    tmp_path: Path, require_toolchain: None,
) -> tuple[Path, Path, Path, Path]:
    """Compile the W2 sources (W1 domain + W2 ports + port-compat
    fixture) to CommonJS in `tmp_path/build/`, write the Node
    runtime harness, return (compiled-fixture path, harness path,
    compiled-ports path, compiled-domain path)."""
    for p in (DOMAIN_FILE, PORTS_FILE):
        if not p.is_file():
            pytest.skip(f"missing required source: {p}")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    fixture_path = APP_DIR / "__port_compat_fixture.ts"
    fixture_path.write_text(_PORT_COMPAT_FIXTURE)
    harness = tmp_path / "harness.cjs"
    harness.write_text(_RUNTIME_HARNESS)
    try:
        result = _run_tsc(
            out_dir,
            [DOMAIN_FILE, PORTS_FILE, fixture_path],
        )
        assert result.returncode == 0, (
            f"ports.ts failed to compile in isolated strict mode.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        compiled_fixture = out_dir / "application" / "__port_compat_fixture.js"
        compiled_ports = out_dir / "application" / "ports.js"
        compiled_domain = out_dir / "domain" / "explorer.js"
        assert compiled_fixture.is_file(), (
            f"tsc did not emit the port-compat fixture at {compiled_fixture}. "
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert compiled_ports.is_file(), (
            f"tsc did not emit the ports module at {compiled_ports}. "
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert compiled_domain.is_file(), (
            f"tsc did not emit the domain module at {compiled_domain}. "
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        return compiled_fixture, harness, compiled_ports, compiled_domain
    finally:
        if fixture_path.is_file():
            fixture_path.unlink()


def test_compiled_application_passes_runtime_contract(
    compiled_application: tuple[Path, Path, Path, Path],
) -> None:
    """Loaded under Node (ES2022 only, no DOM), the compiled W2
    application port + port-compat fixture + W1 domain contract
    together satisfy the W2 contract end-to-end:

      1. `EXPLORER_PORT_NAME` is the literal `"ExplorerRepository"`.
      2. The port-compat mock is a usable `ExplorerRepository` —
         every method is a function and every return value is
         the right shape (`ExplorerTree` for `fetchFiles`,
         `ExplorerFileServeResult` for `fetchFileServe`).
      3. `fetchFileServe` returns independent `Uint8Array`
         instances per call (the port contract is value-typed).
      4. The W1 domain module is reachable from the W2 compile
         context, and `createInitialExplorerState()` returns the
         canonical initial state — proves the W1 ↔ W2 dependency
         is wired correctly.

    The compile-time port-compat assignment (`const mockRepo:
    ExplorerRepository = …` in the fixture) fires BEFORE this
    runtime harness runs, so a port signature drift is caught at
    the compile gate (the fixture fails to assign) rather than
    at runtime. The runtime harness exists to catch type errors
    that pass strict mode but fail at runtime (e.g. a future PR
    that swaps the W1 `ExplorerTree` for a structurally similar
    but semantically different type)."""
    (
        compiled_fixture, harness, compiled_ports, compiled_domain,
    ) = compiled_application
    # The runtime harness loads the port-compat fixture (which
    # re-exports the mock that satisfied the port at compile
    # time), the ports module (to read EXPLORER_PORT_NAME), and
    # the W1 domain module (to round-trip the ExplorerTree
    # shape and confirm the W1 ↔ W2 wiring).
    result = subprocess.run(
        ["node", str(harness), str(compiled_ports), str(compiled_fixture), str(compiled_domain)],
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


# ---------------------------------------------------------------------------
# Project-wide strict typecheck — the W2 contract must compile
# against the project's tsconfig (not just the isolated strict
# flags the focused compile uses). A future PR that breaks a
# downstream consumer (presentation, infrastructure, design-system)
# is caught here.
# ---------------------------------------------------------------------------
def test_project_wide_strict_typecheck_for_research_application(
    require_toolchain: None,
) -> None:
    """Strict typecheck across `src/modules/research/` against
    the project's tsconfig flags (`strict`, `noUncheckedIndexedAccess`,
    `noUnusedLocals`, `noUnusedParameters`, `noImplicitReturns`,
    `noFallthroughCasesInSwitch`). The compile is `--noEmit` so
    no output touches the worktree; it only validates that the
    W2 port file (and every other Research file) compiles
    cleanly under the project's full strict mode flag set.

    `noEmit: true` in the project tsconfig prevents accidental
    writes; the focused compile flag set here adds the strict
    flags explicitly so a tsconfig regression that drops one
    does not silently weaken the gate. The test skips when
    node_modules is missing — the `next` plugin the project
    tsconfig pulls in needs `@types/next` / `next` installed
    (see `package.json`)."""
    if not PORTS_FILE.exists():
        pytest.skip("application ports file not present yet")
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
            str(DOMAIN_FILE), str(PORTS_FILE),
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
