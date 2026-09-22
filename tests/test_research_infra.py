"""
Research infrastructure contract tests (W3 of `complete-frontend-migration`).

Pins `src/modules/research/infrastructure/api.ts` — the typed HTTP
adapter for FastAPI's `/api/files` and `/api/files/serve` endpoints
that satisfies `ExplorerRepository` (`src/modules/research/application/
ports.ts`) via TypeScript structural function subtyping. Asserts
file presence, source purity (spec.md rule 4: infrastructure → domain
only; no React/Next/FastAPI/Starlette), strict-mode compile under
`--lib ES2022` only, port-compat runtime mirror, and runtime
behaviour under Node with a stubbed `fetch` so no real network is
touched.

The W3 contract (verbatim from `odd/tasks/complete-frontend-
migration.md::ODD-MIGRATE-002 / W3`):

    "Ship the Research infrastructure adapter that satisfies
     `ExplorerRepository` structurally via TypeScript's function
     subtyping (the wider signatures with transport-level fetch /
     baseUrl are silently dropped on the narrower port signature,
     same as the merged taxonomy adapter satisfies
     `TaxonomyRepository`). Provide `fetchFiles` (GET /api/files
     → ExplorerTree) and `fetchFileServe` (GET /api/files/serve
     → typed bytes + Content-Type + filename), both with an
     injectable fetch + baseUrl. Add a named `ExplorerApiError`,
     validated wire projection, encoded path query, typed file
     bytes, verbatim Content-Type, parsed filename, and clear
     HTTP / malformed-response errors. Update the Research public
     barrel. Add focused hermetic pytest contract tests with
     injected fetch + strict isolated TypeScript/Node harness."

References:
    odd/tasks/complete-frontend-migration.md          §ODD-MIGRATE-002 / W3
    openspec/specs/research/spec.md                   §Recursive directory
                                                       listing endpoint,
                                                       §Path-traversal-safe
                                                       file streaming endpoint,
                                                       §Content-Type by extension
    api/server.py::list_research_root()               Tree-shape oracle
    api/server.py::_walk_tree()                       Per-node shape oracle
    api/server.py::serve_research_file()              File-serve oracle
    web/file_explorer.js::serveUrl()                  Legacy encodeURIComponent
                                                       builder
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INFRA_FILE = (
    REPO_ROOT / "src" / "modules" / "research" / "infrastructure" / "api.ts"
)
DOMAIN_FILE = REPO_ROOT / "src" / "modules" / "research" / "domain" / "explorer.ts"
PORTS_FILE = (
    REPO_ROOT / "src" / "modules" / "research" / "application" / "ports.ts"
)
BARREL_FILE = REPO_ROOT / "src" / "modules" / "research" / "index.ts"


def _has_npx() -> bool:
    return shutil.which("npx") is not None


def _has_node() -> bool:
    return shutil.which("node") is not None


@pytest.fixture()
def require_toolchain() -> None:
    """Skip when npx / node are not on PATH — the focused compile +
    runtime harness needs both to validate the W3 contract."""
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
def test_infra_file_exists() -> None:
    """RED marker for W3 — the focused compile + runtime harness also
    skips, so every downstream W3 contract test observes RED until
    `src/modules/research/infrastructure/api.ts` lands."""
    assert INFRA_FILE.is_file(), (
        f"missing infrastructure file: {INFRA_FILE}. W3 ships this "
        f"file as the typed HTTP adapter for the Browser-tab research "
        f"data source."
    )


def test_infra_file_is_plain_typescript() -> None:
    """`.ts`, not `.tsx` — infrastructure has no JSX (mirrors the
    taxonomy `api.ts` convention — spec.md rule 4: JSX belongs to
    presentation)."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    assert INFRA_FILE.suffix == ".ts", (
        f"infra file must be TypeScript; got suffix={INFRA_FILE.suffix}"
    )


def test_infra_file_depends_on_domain_and_application_only() -> None:
    """Spec.md rule 4 (inward deps): infrastructure depends on
    domain + application ONLY (no presentation, no cross-module
    deep imports, no public barrel reverse import). The optional
    `.js` extension covers both `from "../domain/explorer"` and
    Bundler/NodeNext spellings — mirrors the taxonomy adapter's
    `../domain/taxon` import. The application port is imported so
    the W3 adapter can type the `fetchFileServe` request shape
    against `ExplorerFileServeRequest` — but the import is the
    TYPE-only import (`import type { … }`), so the infrastructure
    layer never reaches into the application runtime (the port
    file has no runtime exports — only `EXPLORER_PORT_NAME` and
    the type interfaces)."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = _strip_ts_comments(INFRA_FILE.read_text())
    # Required: infrastructure imports the W1 domain contract
    # so the wire → domain projection stays typed against the
    # canonical `ExplorerTree` / `ExplorerTreeNode` /
    # `ExplorerFolderNode` / `ExplorerFileNode` interfaces.
    assert re.search(
        r'import\s+type\s*\{[^}]*ExplorerTree\b[^}]*\}\s*from\s*'
        r'["\']\.\./domain/explorer(?:\.js)?["\']',
        text,
    ), (
        "infra/api.ts must import the W1 ExplorerTree type from "
        "'../domain/explorer' so the wire projection stays anchored "
        "at the canonical domain contract."
    )
    # Required: infrastructure imports the W2 application port
    # TYPES so the `fetchFileServe` request / result shapes stay
    # typed against `ExplorerFileServeRequest` /
    # `ExplorerFileServeResult`. The import MUST be `import type`
    # so the infrastructure layer never reaches into the
    # application runtime (mirrors the spec.md rule 4 inward-only
    # contract — application has no runtime exports except the
    # `EXPLORER_PORT_NAME` constant, and infrastructure should not
    # depend on it either; the structural-subtyping proof lives in
    # the W3 port-compat fixture).
    assert re.search(
        r'import\s+type\s*\{[^}]*ExplorerFileServeRequest\b[^}]*\}\s*from\s*'
        r'["\']\.\./application/ports(?:\.js)?["\']',
        text,
    ), (
        "infra/api.ts must import the W2 ExplorerFileServeRequest type "
        "from '../application/ports' so the fetchFileServe request shape "
        "stays typed against the application port contract."
    )
    # Forbidden: any import from the future presentation layer
    # (W6+ React mount), the public barrel (consumers reach the
    # adapter through the barrel, not the reverse), or any
    # cross-module deep import.
    for forbidden in (
        "../presentation",
        "../index",
        "../../taxonomy",
        "../../design-system",
        "../../browser-state",
        "../../app-shell",
    ):
        assert forbidden not in text, (
            f"infra/api.ts must NOT import from {forbidden!r}; spec.md "
            f"rule 4 keeps infrastructure inward-only (domain + "
            f"application types only), and rule 5 forbids reverse "
            f"deep imports through the barrel."
        )


def test_infra_file_has_no_framework_imports() -> None:
    """Infrastructure is leaf-level I/O glue — no React, Next,
    FastAPI, Starlette, Pydantic. Mirrors the taxonomy adapter
    purity guard so a future PR that imports a framework is
    caught at review."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = _strip_ts_comments(INFRA_FILE.read_text())
    for tok in (
        "from 'react'", 'from "react"',
        "from 'next'",   'from "next"',
        "from 'nextjs'", 'from "nextjs"',
        "from 'fastapi'", 'from "fastapi"',
        "from 'starlette'", 'from "starlette"',
        "from 'pydantic'", 'from "pydantic"',
    ):
        assert tok not in text, (
            f"infra/api.ts must stay free of {tok!r}."
        )


def test_infra_file_uses_only_allowed_runtime_helpers() -> None:
    """The adapter is framework-free at the source level too —
    only standard ES2022 + DOM-free runtime helpers (`globalThis`,
    `encodeURIComponent`, `decodeURIComponent`) are allowed. A
    future PR that pulls in `Buffer.from(...)`, `path.resolve(...)`,
    or a third-party HTTP client (`axios`, `ky`) breaks the leaf-
    level I/O glue contract."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = _strip_ts_comments(INFRA_FILE.read_text())
    for forbidden in (
        # Node-only helpers — the adapter must work in both
        # browser + Node 18+ without a Buffer import.
        "Buffer.from", "Buffer.alloc",
        "require(", "module.exports",
        # Cross-module runtime helpers.
        "axios", "node-fetch", "ky",
    ):
        assert forbidden not in text, (
            f"infra/api.ts must stay free of {forbidden!r}."
        )


def test_infra_file_exports_named_fetch_files() -> None:
    """The W3 contract commits to a named export `fetchFiles` as an
    async function (mirrors the taxonomy adapter's named export
    `fetchTaxon` / `fetchChildren` convention). Dropping the export
    breaks every W6+ consumer that wires the typed adapter through
    the barrel; this assertion pins the named function so a
    future PR cannot silently rename it (e.g. `getExplorerTree`,
    `listResearchFiles`) without breaking this guard."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    assert re.search(
        r"export\s+async\s+function\s+fetchFiles\b",
        text,
    ), (
        "infra/api.ts must export `fetchFiles` as a named async function "
        "(maps to GET /api/files → ExplorerTree)."
    )


def test_infra_file_exports_named_fetch_file_serve() -> None:
    """The W3 contract commits to a named export `fetchFileServe`
    as an async function (mirrors the taxonomy adapter's named
    export convention). The function must accept a typed request
    argument (ExplorerFileServeRequest from W2) as the FIRST
    parameter — so the structural-subtyping proof against the
    narrower port signature `fetchFileServe(request)` lines up
    with the adapter's `fetchFileServe(request, opts?)` wider
    signature (extra optional parameter is silently dropped on
    the narrower port signature)."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    m = re.search(
        r"export\s+async\s+function\s+fetchFileServe\b[\s\S]*?\n\}",
        text,
        re.MULTILINE,
    )
    assert m, (
        "infra/api.ts must export `fetchFileServe` as a named async "
        "function (maps to GET /api/files/serve?path=…)."
    )
    signature = m.group(0)
    # The first parameter MUST be the typed request shape
    # (ExplorerFileServeRequest) so the structural-subtyping
    # proof against the narrower port signature lines up.
    assert re.search(
        r"fetchFileServe\s*\(\s*request\s*:\s*ExplorerFileServeRequest\b",
        signature,
    ), (
        "fetchFileServe must accept `request: ExplorerFileServeRequest` "
        "as the first parameter so the W2 port's narrower signature "
        "`fetchFileServe(request): Promise<ExplorerFileServeResult>` "
        "lines up via TypeScript function subtyping."
    )
    # The return type MUST be Promise<ExplorerFileServeResult>
    # — the same shape the W2 port expects.
    assert "Promise<ExplorerFileServeResult>" in signature, (
        "fetchFileServe must return Promise<ExplorerFileServeResult> "
        "so the W2 port's narrower return-type contract holds."
    )


def test_infra_file_exports_named_explorer_api_error() -> None:
    """The W3 contract commits to a named `ExplorerApiError` error
    class. Mirrors the taxonomy adapter's `TaxonomyApiError` shape
    so React consumers can `instanceof`-narrow against a single
    cross-module error shape. Dropping the export breaks every
    W4 renderer that branches on `instanceof ExplorerApiError`;
    this assertion pins the named class so a future PR cannot
    silently rename it (e.g. `ResearchApiError`,
    `ExplorerHttpError`) without breaking this guard."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    assert re.search(
        r"export\s+class\s+ExplorerApiError\b",
        text,
    ), (
        "infra/api.ts must export `ExplorerApiError` as a named class."
    )
    # The class MUST extend Error so `instanceof Error` narrows
    # correctly under React's error boundaries.
    assert re.search(
        r"class\s+ExplorerApiError\s+extends\s+Error\b",
        text,
    ), (
        "ExplorerApiError must extend Error so React error "
        "boundaries can narrow it correctly."
    )
    # The class MUST carry `readonly status: number | null` so
    # HTTP failures preserve the server's status code (renders
    # can branch on `err.status === 404` for "missing folder"
    # without parsing the message string).
    assert re.search(
        r"readonly\s+status\s*:\s*number\s*\|\s*null",
        text,
    ), (
        "ExplorerApiError must carry `readonly status: number | null` "
        "so HTTP failures preserve the server's status code."
    )
    # The constructor MUST accept an optional second `opts`
    # argument with `status` + `cause` so HTTP failures can
    # preserve both fields without breaking the throw call site.
    ctor = re.search(
        r"constructor\s*\([^)]*\)\s*\{[\s\S]*?\n\s*\}",
        text,
        re.MULTILINE,
    )
    assert ctor, "ExplorerApiError must declare an explicit constructor."
    assert "status" in ctor.group(0) and "cause" in ctor.group(0), (
        "ExplorerApiError constructor must accept an `opts` argument "
        "carrying `status` + `cause` so HTTP failures preserve both."
    )


def test_infra_file_exports_named_fetch_options() -> None:
    """ODD-MIGRATE-002 W3: the public `FetchOptions` interface
    must be exported so React consumers can type the transport-
    level `fetch` + `baseUrl` options without a deep import.
    A future PR that drops the export breaks the React cutover's
    typed `fetchFiles(opts)` / `fetchFileServe(request, opts)`
    wiring."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    assert re.search(
        r"export\s+interface\s+FetchOptions\b",
        text,
    ), (
        "infra/api.ts must export `FetchOptions` as a public interface."
    )
    # The interface must carry exactly `fetch` + `baseUrl` — the
    # two transport-level options the W3 contract commits to.
    block = re.search(
        r"interface\s+FetchOptions\b[^}]*\}",
        text,
        re.DOTALL,
    )
    assert block, "FetchOptions interface must be syntactically well-formed."
    props = re.findall(r"(\w+)\s*\?\s*:", block.group(0))
    assert sorted(props) == sorted(["fetch", "baseUrl"]), (
        "ODD-MIGRATE-002 W3: FetchOptions must carry exactly "
        "{fetch?, baseUrl?}; got " + str(props)
    )


def test_infra_file_does_not_export_default() -> None:
    """TRIANGULATE — the infrastructure file MUST NOT export a
    default symbol. The taxonomy infra file pins named exports
    only (`fetchTaxon`, `fetchChildren`, …); a future PR that
    flips to `export default …` would silently break barrel
    re-exports and DI bindings. This guard catches the regression
    at review."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    assert not re.search(r"^\s*export\s+default\b", text, re.MULTILINE), (
        "infra/api.ts must NOT export a default symbol — the W3 "
        "contract pins named exports only (fetchFiles, fetchFileServe, "
        "ExplorerApiError, FetchOptions)."
    )


def test_infra_file_url_builder_encodes_path_query() -> None:
    """TRIANGULATE — the `fetchFileServe` runtime helper must
    URL-encode the request path with `encodeURIComponent` so paths
    with spaces / unicode / quotes (taxon names can include
    accents — see `web/file_explorer.js::serveUrl`'s
    `encodeURIComponent(relativePath)` call) round-trip cleanly
    through FastAPI's `Query(min_length=1, max_length=4096)`
    validator. The runtime check below pins the URL building
    contract in one assertion block. Mirrors the legacy oracle
    byte-for-byte (the React cutover's serve URL must be
    byte-identical to `web/file_explorer.js::serveUrl`'s
    `encodeURIComponent` invocation)."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    fetch_block = re.search(
        r"export\s+async\s+function\s+fetchFileServe\b.*?^\s*\}",
        text,
        re.DOTALL | re.MULTILINE,
    )
    assert fetch_block, "infra/api.ts must declare the fetchFileServe async function."
    body = fetch_block.group(0)
    assert "encodeURIComponent" in body, (
        "fetchFileServe must URL-encode the request path with "
        "encodeURIComponent so paths with spaces / accents round-trip "
        "through FastAPI's Query(min_length=1, max_length=4096) "
        "validator (mirrors web/file_explorer.js::serveUrl)."
    )
    # The encoded path MUST be forwarded as `?path=<encoded>` — the
    # legacy oracle's URL shape. A future PR that switches to a
    # different query key (e.g. `?file=…`) breaks the FastAPI
    # server's Query() binding silently.
    assert "?path=" in body or "?path\u003d" in body, (
        "fetchFileServe must build `?path=<encoded>` so the "
        "FastAPI server's Query() binding resolves correctly."
    )


def test_infra_file_url_builder_absorbs_relative_baseurl_literals() -> None:
    """ODD-MIGRATE-006 (symmetric to taxonomy PR #378): the
    `url(baseUrl, path)` helper MUST absorb BOTH the empty-string
    edge case AND the literal `"/api"` baseUrl as equivalent
    relative-baseUrl indicators, returning `path` as-is for
    either. The carveout pins the contract that the React mount's
    `?? "/api"` fallback (post-f708a15) and the legacy empty-
    string fallback both compose `/api/files` instead of the
    would-be `/api/api/files` concatenation that 404s against
    FastAPI's `/api/files` route. Mirrors the taxonomy infra
    helper's `if (baseUrl === "" || baseUrl === "/api") return
    path;` carveout byte-for-byte so the React port sees the
    same URL-construction convention across adapters. A future
    PR that drops either literal OR changes the concat to a
    different normalisation breaks the Explorer route's
    `/api/files` fetch — see `src/modules/taxonomy/infrastructure/
    api.ts::url` for the matching carveout."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    # The carveout branch must be present verbatim. The two
    # relative-baseUrl literals (empty string + "/api") MUST be
    # checked together so a future PR can't drop one without
    # dropping the other — they're equivalent indicators, not
    # two distinct carveouts.
    url_block = re.search(
        r"function\s+url\s*\(\s*baseUrl\s*:\s*string\s*,\s*path\s*:\s*string\s*\)\s*:\s*string\s*\{[^}]*\}",
        text,
        re.DOTALL,
    )
    assert url_block, (
        "infra/api.ts must declare the `url(baseUrl, path)` helper "
        "with the typed signature `(baseUrl: string, path: string): string`."
    )
    body = url_block.group(0)
    # Both literals MUST be absorbed (in either order) and the
    # helper MUST short-circuit on either match by returning
    # `path` as-is. The regex tolerates the order so a future
    # refactor that swaps the `||` operands doesn't break the
    # pin.
    assert re.search(
        r"""(?:baseUrl\s*===\s*(?:["']["']|["']/api["'])\s*\|\|\s*baseUrl\s*===\s*(?:["']["']|["']/api["']))""",
        body,
    ), (
        "ODD-MIGRATE-006 (symmetric to taxonomy PR #378): the "
        "url() helper MUST absorb BOTH `baseUrl === ''` AND "
        "`baseUrl === '/api'` as equivalent relative-baseUrl "
        "indicators. Got body: " + body
    )
    # The carveout branch MUST return `path` as-is — the literal
    # `/api/files` route must NOT be doubled into `/api/api/files`.
    assert re.search(
        r"""(?:baseUrl\s*===\s*["']["']\s*\|\|\s*baseUrl\s*===\s*["']/api["']|baseUrl\s*===\s*["']/api["']\s*\|\|\s*baseUrl\s*===\s*["']["'])""",
        body,
    ), (
        "ODD-MIGRATE-006 (symmetric to taxonomy PR #378): the "
        "url() helper MUST absorb BOTH `baseUrl === ''` AND "
        "`baseUrl === '/api'` as equivalent relative-baseUrl "
        "indicators. Got body: " + body
    )
    # The carveout branch MUST return `path` as-is — the literal
    # `/api/files` route must NOT be doubled into `/api/api/files`.
    # The regex tolerates the order of the `||` operands so a
    # future refactor that swaps them doesn't break the pin.
    assert re.search(
        r"""if\s*\(\s*(?:baseUrl\s*===\s*["']["']\s*\|\|\s*baseUrl\s*===\s*["']/api["']|baseUrl\s*===\s*["']/api["']\s*\|\|\s*baseUrl\s*===\s*["']["'])\s*\)\s*return\s+path\s*;""",
        body,
    ), (
        "ODD-MIGRATE-006: the `url()` carveout branch MUST "
        "`return path;` for both literals so the resulting URL "
        "stays `/api/files` instead of the would-be "
        "`/api/api/files` concatenation. Got body: " + body
    )


# ---------------------------------------------------------------------------
# Public barrel — W3 must re-export the adapter surface through the
# module's barrel so cross-module consumers (W6 React mount,
# integration tests) reach the W3 contract through the public surface
# (spec.md rule 5).
# ---------------------------------------------------------------------------
def test_barrel_reexports_research_infra_surface() -> None:
    """ODD-MIGRATE-002 W3: the public barrel must re-export
    `fetchFiles`, `fetchFileServe`, `ExplorerApiError` (as
    values) and `FetchOptions` (as a type). Consumers reach the
    adapter through the barrel — spec.md rule 5. A future PR
    that drops any of these re-exports breaks every W6+
    consumer that wires the typed adapter through the barrel.
    Mirrors `tests/test_taxonomy_infra.py` barrel coverage."""
    if not BARREL_FILE.exists():
        pytest.skip("research barrel not present yet")
    text = BARREL_FILE.read_text()
    for name in ("fetchFiles", "fetchFileServe", "ExplorerApiError"):
        pattern = (
            rf"export\s*\{{\s*[^}}]*\b{name}\b[^}}]*\s*\}}\s*from\s*"
            rf'["\']\./infrastructure/api(?:\.js)?["\']'
        )
        assert re.search(pattern, text), (
            f"research barrel must re-export `{name}` from "
            f"'./infrastructure/api' so cross-module consumers reach "
            f"the W3 adapter through the barrel (spec.md rule 5)."
        )
    # The FetchOptions type re-export uses `export type { … }`
    # form (mirrors the taxonomy barrel).
    assert re.search(
        r"export\s+type\s*\{\s*[^}]*\bFetchOptions\b[^}]*\}\s*from\s*"
        r'["\']\./infrastructure/api(?:\.js)?["\']',
        text,
    ), (
        "research barrel must re-export `FetchOptions` as a type so "
        "React consumers can type the transport-level options without "
        "a deep import."
    )


def test_barrel_reexports_research_application_port() -> None:
    """ODD-MIGRATE-002 W3: the public barrel must re-export the
    W2 application port (`ExplorerRepository`,
    `ExplorerFileServeRequest`, `ExplorerFileServeResult`) +
    the `EXPLORER_PORT_NAME` constant so W6+ consumers can wire
    the typed surface through one barrel import. Mirrors the
    taxonomy barrel's
    `export { TAXONOMY_PORT_NAME } from "./application/ports"` +
    `export type { TaxonomyRepository } from "./application/ports"`."""
    if not BARREL_FILE.exists():
        pytest.skip("research barrel not present yet")
    text = BARREL_FILE.read_text()
    # The ExplorerRepository / ExplorerFileServeRequest /
    # ExplorerFileServeResult types are re-exported via
    # `export type { … } from "./application/ports"`.
    for name in (
        "ExplorerRepository",
        "ExplorerFileServeRequest",
        "ExplorerFileServeResult",
    ):
        pattern = (
            rf"export\s+type\s*\{{\s*[^}}]*\b{name}\b[^}}]*\}}\s*from\s*"
            rf'["\']\./application/ports(?:\.js)?["\']'
        )
        assert re.search(pattern, text), (
            f"research barrel must re-export `{name}` as a type so "
            f"React consumers can wire the W2 port surface through "
            f"the barrel (spec.md rule 5)."
        )
    # EXPLORER_PORT_NAME is re-exported as a value.
    pattern = (
        r"export\s*\{\s*[^}]*\bEXPLORER_PORT_NAME\b[^}]*\}\s*from\s*"
        r'["\']\./application/ports(?:\.js)?["\']'
    )
    assert re.search(pattern, text), (
        "research barrel must re-export `EXPLORER_PORT_NAME` so "
        "DI containers / diagnostic guards can branch on the port "
        "identity through the barrel."
    )


# ---------------------------------------------------------------------------
# Compile + runtime contract — strict mode, ES2022 only, no DOM.
# ---------------------------------------------------------------------------
def _run_tsc_isolated(source: Path, out_dir: Path) -> subprocess.CompletedProcess:
    """Compile `api.ts` under `--strict`, `--target ES2022`,
    `--module commonjs`, `--lib ES2022` (no DOM — fetch must be
    injectable). `--rootDir` pins the output layout across
    transitive imports. Mirrors `tests/test_taxonomy_infra.py::
    _run_tsc_isolated`."""
    return subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--strict", "--target", "ES2022",
            "--module", "commonjs", "--lib", "ES2022",
            "--skipLibCheck", "--esModuleInterop",
            "--rootDir", "src/modules/research",
            "--outDir", str(out_dir),
            str(source),
        ],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )


def _run_tsc_isolated_multi(
    sources: list[Path], out_dir: Path,
) -> subprocess.CompletedProcess:
    """Compile multiple W3 sources (domain + ports + infra +
    port-compat fixture) in strict isolated mode. Mirrors the
    `_run_tsc` helper in `tests/test_research_application.py`."""
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


# Port-compat fixture — proves the W3 adapter satisfies
# `ExplorerRepository` via TypeScript structural function subtyping.
# The assignment below fires at the strict compile gate: a port
# signature drift (e.g. an extra required parameter) breaks the
# assignment before the runtime harness runs.
_PORT_COMPAT_FIXTURE = r"""
import type { ExplorerRepository } from "../application/ports";
import { fetchFiles, fetchFileServe } from "./api";

/** Structural-subtyping proof — the adapter's wider transport
 *  signatures (`fetchFiles(opts?: FetchOptions)` and
 *  `fetchFileServe(request, opts?: FetchOptions)`) satisfy the
 *  narrower application port signatures (`fetchFiles(): Promise<
 *  ExplorerTree>` and `fetchFileServe(request): Promise<
 *  ExplorerFileServeResult>`) via TypeScript's function-subtyping
 *  contract. The extra optional `opts` parameter is silently
 *  dropped on the narrower port signature — callers of the port
 *  omit it.
 *
 *  The compile-time port-compat assignment below fires BEFORE
 *  the runtime harness runs, so a port signature drift is caught
 *  at the compile gate (the assignment fails to typecheck) rather
 *  than at runtime (where the contract would still pass a weak
 *  structural check). */
const _fetchFiles: ExplorerRepository["fetchFiles"] = fetchFiles;
const _fetchFileServe: ExplorerRepository["fetchFileServe"] = fetchFileServe;

/** Re-export a port-compat object so the runtime harness can
 *  drive the adapter through the narrower port surface and
 *  confirm end-to-end behaviour (HTTP error branch, wire
 *  projection, independence of returned Uint8Arrays, etc.). */
export const __port_compatible__ = {
  fetchFiles: _fetchFiles,
  fetchFileServe: _fetchFileServe,
};
"""


# Runtime harness — loaded by Node after tsc has emitted the
# port-compat fixture. Exercises every externally observable
# contract: the W3 adapter's URL building, wire projection, HTTP
# error mapping, Content-Type / Content-Disposition parsing,
# `encodeURIComponent` path query, and the structural-subtyping
# mirror (calling the adapter through the narrower port
# signatures yields the same end-to-end behaviour).
_RUNTIME_HARNESS = r"""
// CJS does not support top-level await (only ESM does), so the
// harness wraps the async body in an IIFE. The IIFE returns a
// Promise; we `.catch` to surface unhandled rejections as a
// non-zero exit code (the test harness reads `returncode != 0`
// as the failure marker).
const path = require("path");
const assert = require("assert");
const api = require(path.resolve(process.argv[2]));
const port = require(path.resolve(process.argv[3]));

function makeFetch(responses) {
  const calls = [];
  const fn = async (input, init) => {
    calls.push({ input, init });
    const r = responses[calls.length - 1];
    if (!r) throw new Error("unexpected fetch call #" + calls.length);
    return {
      ok: r.ok,
      status: r.status,
      statusText: r.statusText || "",
      headers: {
        get(name) {
          if (!r.headers) return null;
          const lower = String(name).toLowerCase();
          for (const k of Object.keys(r.headers)) {
            if (k.toLowerCase() === lower) return r.headers[k];
          }
          return null;
        },
      },
      json: () => r.json,
      arrayBuffer: () => r.arrayBuffer,
    };
  };
  fn.calls = calls;
  return fn;
}

// ---- fetchFiles fixtures -----------------------------------------
// Tree-shape oracle mirrors api/server.py::_walk_tree byte-for-
// byte: folder → {name, path, type, "folder", children}; file →
// {name, path, type, "file", extension, size, modified}. A wire
// null extension projects as `null` (the wire-shape contract —
// never coerced to "other" — see the runtime check below).
const FULL_TREE = {
  exists: true,
  filesystem_path: "/Users/x/Research",
  root: {
    name: "Research",
    path: "",
    type: "folder",
    children: [
      { name: "Animalia", path: "Animalia", type: "folder", children: [
        { name: "Chordata", path: "Animalia/Chordata", type: "folder", children: [
          { name: "Mammalia.pdf", path: "Animalia/Chordata/Mammalia.pdf",
            type: "file", extension: "pdf", size: 12345,
            modified: "2024-01-01T12:00:00" },
          { name: "Aves.md", path: "Animalia/Chordata/Aves.md",
            type: "file", extension: "md", size: 678,
            modified: "2024-01-02T12:00:00" },
        ] },
      ] },
      { name: "Plantae", path: "Plantae", type: "folder", children: [] },
      { name: "Fungi.csv", path: "Fungi.csv", type: "file",
        extension: "csv", size: 4096,
        modified: "2024-02-01T09:30:00" },
      { name: "README.txt", path: "README.txt", type: "file",
        extension: "txt", size: 12,
        modified: "2024-03-01T00:00:00" },
    ],
  },
};

// Empty-state payload — `exists: false` + `root: null` (the
// FastAPI server returns 200 with this shape when the research
// root is missing or not a directory).
const EMPTY_TREE = {
  exists: false,
  filesystem_path: "/Users/x/Research",
  root: null,
};

(async () => {
  // ---- fetchFiles — happy path with full tree ---------------
  const f1 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: FULL_TREE }]);
  const tree = await api.fetchFiles({ fetch: f1, baseUrl: "http://x" });
  assert.strictEqual(f1.calls.length, 1);
  assert.strictEqual(f1.calls[0].input, "http://x/api/files",
    "fetchFiles must build /api/files relative to baseUrl: " +
    f1.calls[0].input);
  assert.strictEqual(tree.exists, true);
  assert.strictEqual(tree.filesystem_path, "/Users/x/Research");
  assert.strictEqual(tree.root.type, "folder");
  assert.strictEqual(tree.root.name, "Research");
  assert.strictEqual(tree.root.path, "");
  assert.ok(Array.isArray(tree.root.children));
  assert.strictEqual(tree.root.children.length, 4);
  // First folder — verify nested children survive verbatim.
  const animalia = tree.root.children[0];
  assert.strictEqual(animalia.name, "Animalia");
  assert.strictEqual(animalia.path, "Animalia");
  assert.strictEqual(animalia.type, "folder");
  assert.strictEqual(animalia.children.length, 1);
  const chordata = animalia.children[0];
  assert.strictEqual(chordata.name, "Chordata");
  assert.strictEqual(chordata.path, "Animalia/Chordata");
  assert.strictEqual(chordata.children.length, 2);
  // File children — every wire field projects verbatim.
  const pdf = chordata.children[0];
  assert.strictEqual(pdf.name, "Mammalia.pdf");
  assert.strictEqual(pdf.path, "Animalia/Chordata/Mammalia.pdf");
  assert.strictEqual(pdf.type, "file");
  assert.strictEqual(pdf.extension, "pdf");
  assert.strictEqual(pdf.size, 12345);
  assert.strictEqual(pdf.modified, "2024-01-01T12:00:00");
  // Structural guard — the canonical ExplorerFileNode does NOT
  // carry any invented field beyond the wire shape. Mirrors the
  // taxonomy adapter's structural-regression guard.
  const fileKeys = Object.keys(pdf).sort();
  assert.deepStrictEqual(fileKeys,
    ["extension", "modified", "name", "path", "size", "type"],
    "ODD-MIGRATE-002 W3: canonical ExplorerFileNode must carry exactly "
    + "{name, path, type, extension, size, modified}; got " +
    JSON.stringify(fileKeys));
  // Second folder — verify empty children survive verbatim.
  const plantae = tree.root.children[1];
  assert.strictEqual(plantae.name, "Plantae");
  assert.strictEqual(plantae.path, "Plantae");
  assert.deepStrictEqual(plantae.children, []);
  // Root-level file + second file child — verify all file
  // fields project without coercion.
  const csv = tree.root.children[2];
  assert.strictEqual(csv.name, "Fungi.csv");
  assert.strictEqual(csv.extension, "csv");
  assert.strictEqual(csv.size, 4096);
  assert.strictEqual(csv.modified, "2024-02-01T09:30:00");
  const md = chordata.children[1];
  assert.strictEqual(md.name, "Aves.md");
  assert.strictEqual(md.extension, "md");
  assert.strictEqual(md.size, 678);

  // ---- fetchFiles — exists: false (empty-state path) --------
  const f2 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: EMPTY_TREE }]);
  const empty = await api.fetchFiles({ fetch: f2, baseUrl: "http://x" });
  assert.strictEqual(empty.exists, false);
  assert.strictEqual(empty.root, null);
  assert.strictEqual(empty.filesystem_path, "/Users/x/Research");

  // ---- fetchFiles — baseUrl join ----------------------------
  const f3 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: EMPTY_TREE }]);
  await api.fetchFiles({ fetch: f3, baseUrl: "http://api.example.com/" });
  assert.strictEqual(f3.calls[0].input, "http://api.example.com/api/files",
    "fetchFiles must trim trailing slash from baseUrl: " +
    f3.calls[0].input);
  // baseUrl="" (relative origin) — URL stays /api/files.
  const f4 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: EMPTY_TREE }]);
  await api.fetchFiles({ fetch: f4 });
  assert.strictEqual(f4.calls[0].input, "/api/files",
    "fetchFiles without baseUrl must stay relative-origin: " +
    f4.calls[0].input);
  // baseUrl="/api" (post-f708a15 relative-origin alias) — URL
  // must also stay /api/files, NOT /api/api/files. Mirrors the
  // ODD-MIGRATE-006 carveout in the taxonomy infra helper (PR
  // #378) so the React mount's `?? "/api"` fallback composes
  // the canonical /api/files route byte-for-byte.
  const f4api = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: EMPTY_TREE }]);
  await api.fetchFiles({ fetch: f4api, baseUrl: "/api" });
  assert.strictEqual(f4api.calls[0].input, "/api/files",
    "fetchFiles with baseUrl=/api must stay relative-origin (no /api/api duplication): " +
    f4api.calls[0].input);

  // ---- fetchFiles — HTTP non-OK (404) -----------------------
  const f5 = makeFetch([{ ok: false, status: 404, statusText: "Not Found",
    json: { detail: "boom" } }]);
  await assert.rejects(
    () => api.fetchFiles({ fetch: f5, baseUrl: "http://x" }),
    (err) => /404/.test(String(err && err.message || err)),
    "fetchFiles must reject on non-OK with the status code in the message",
  );

  // ---- fetchFiles — HTTP non-OK (500) -----------------------
  const f5b = makeFetch([{ ok: false, status: 500, statusText: "Server Error",
    json: { detail: "boom" } }]);
  await assert.rejects(
    () => api.fetchFiles({ fetch: f5b, baseUrl: "http://x" }),
    (err) => /500/.test(String(err && err.message || err)),
  );

  // ---- fetchFiles — error carries status code --------------
  const f6 = makeFetch([{ ok: false, status: 404, statusText: "Not Found",
    json: { detail: "boom" } }]);
  try {
    await api.fetchFiles({ fetch: f6, baseUrl: "http://x" });
    assert.fail("fetchFiles must reject on 404");
  } catch (err) {
    assert.strictEqual(err.status, 404,
      "ExplorerApiError.status must surface the HTTP status code: got " +
      err.status);
    assert.strictEqual(err.name, "ExplorerApiError");
  }

  // ---- fetchFiles — malformed JSON --------------------------
  const f7 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: Promise.reject(new SyntaxError("Unexpected token < in JSON")) }]);
  await assert.rejects(
    () => api.fetchFiles({ fetch: f7, baseUrl: "http://x" }),
    (err) => /json|JSON/.test(String(err && err.message || err)),
    "fetchFiles must reject malformed JSON with an ExplorerApiError",
  );

  // ---- fetchFiles — non-object payload ----------------------
  const f8 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: "wrong" }]);
  await assert.rejects(
    () => api.fetchFiles({ fetch: f8, baseUrl: "http://x" }),
    (err) => /non-object/.test(String(err && err.message || err)),
    "fetchFiles must reject non-object payloads",
  );

  // ---- fetchFiles — null payload ----------------------------
  const f9 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: null }]);
  await assert.rejects(
    () => api.fetchFiles({ fetch: f9, baseUrl: "http://x" }),
    (err) => /null|non-object/.test(String(err && err.message || err)),
    "fetchFiles must reject null payloads",
  );

  // ---- fetchFiles — schema-invalid payload (missing exists) -
  const f10 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { filesystem_path: "/x", root: null } }]);
  await assert.rejects(
    () => api.fetchFiles({ fetch: f10, baseUrl: "http://x" }),
    (err) => /exists|invalid/i.test(String(err && err.message || err)),
    "fetchFiles must reject payloads missing the `exists` boolean",
  );

  // ---- fetchFiles — schema-invalid payload (exists=true, root=null) -
  const f11 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { exists: true, filesystem_path: "/x", root: null } }]);
  await assert.rejects(
    () => api.fetchFiles({ fetch: f11, baseUrl: "http://x" }),
    (err) => /root|invalid/i.test(String(err && err.message || err)),
    "fetchFiles must reject exists=true with root=null",
  );

  // ---- fetchFiles — schema-invalid payload (exists=false, root!=null) -
  const f12 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { exists: false, filesystem_path: "/x",
      root: { name: "x", path: "", type: "folder", children: [] } } }]);
  await assert.rejects(
    () => api.fetchFiles({ fetch: f12, baseUrl: "http://x" }),
    (err) => /root|invalid/i.test(String(err && err.message || err)),
    "fetchFiles must reject exists=false with a non-null root",
  );

  // ---- fetchFiles — node has unknown type -------------------
  const f13 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { exists: true, filesystem_path: "/x",
      root: { name: "x", path: "", type: "symlink", children: [] } } }]);
  await assert.rejects(
    () => api.fetchFiles({ fetch: f13, baseUrl: "http://x" }),
    (err) => /unknown type|invalid/i.test(String(err && err.message || err)),
    "fetchFiles must reject nodes with unknown type",
  );

  // ---- fetchFiles — file node missing extension -------------
  const f14 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { exists: true, filesystem_path: "/x",
      root: { name: "x", path: "", type: "folder", children: [
        { name: "no-ext", path: "no-ext", type: "file",
          size: 0, modified: "2024-01-01T00:00:00" },
      ] } } }]);
  await assert.rejects(
    () => api.fetchFiles({ fetch: f14, baseUrl: "http://x" }),
    (err) => /extension|invalid/i.test(String(err && err.message || err)),
    "fetchFiles must reject file nodes missing the extension field",
  );

  // ---- fetchFileServe — happy path with bytes + Content-Type +
  // Content-Disposition. Mirrors the legacy oracle
  // (web/file_explorer.js::openInNewTab uses file.url +
  // file.name from the wire tree; the W3 adapter reads the
  // server's Content-Disposition verbatim).
  const f15 = makeFetch([{
    ok: true, status: 200, statusText: "OK",
    headers: {
      "content-type": "application/pdf",
      "content-disposition": 'inline; filename="Mammalia.pdf"',
    },
    arrayBuffer: Promise.resolve(new TextEncoder().encode("%PDF-1.4 hello").buffer),
  }]);
  const served = await api.fetchFileServe(
    { path: "Animalia/Chordata/Mammalia.pdf" },
    { fetch: f15, baseUrl: "http://x" },
  );
  assert.strictEqual(f15.calls.length, 1);
  assert.strictEqual(f15.calls[0].input,
    "http://x/api/files/serve?path=Animalia%2FChordata%2FMammalia.pdf",
    "fetchFileServe must build /api/files/serve?path=<encoded> with "
    + "encodeURIComponent on the path: " + f15.calls[0].input);
  assert.ok(served.content instanceof Uint8Array,
    "fetchFileServe must return a Uint8Array");
  // The wire bytes are verbatim; UTF-8 round-trips through
  // TextEncoder/TextDecoder for the assertion.
  const decoded = new TextDecoder().decode(served.content);
  assert.strictEqual(decoded, "%PDF-1.4 hello",
    "fetchFileServe must preserve the wire bytes verbatim");
  assert.strictEqual(served.contentType, "application/pdf",
    "fetchFileServe must surface the verbatim Content-Type header");
  assert.strictEqual(served.filename, "Mammalia.pdf",
    "fetchFileServe must parse the basename from Content-Disposition");

  // ---- fetchFileServe — path with spaces + accents (encodeURIComponent)
  // Mirrors the legacy oracle
  // (web/file_explorer.js::serveUrl(relativePath) calls
  // encodeURIComponent verbatim). Taxon names can include
  // accents (Animalia, Plantae, …) — the URL must round-trip
  // through FastAPI's Query() validator.
  const f16 = makeFetch([{
    ok: true, status: 200, statusText: "OK",
    headers: {
      "content-type": "text/markdown",
      "content-disposition": 'inline; filename="Aves.md"',
    },
    arrayBuffer: Promise.resolve(new TextEncoder().encode("# Aves").buffer),
  }]);
  await api.fetchFileServe(
    { path: "Animalia/Chordata/Aves.md" },
    { fetch: f16, baseUrl: "http://x" },
  );
  assert.strictEqual(f16.calls[0].input,
    "http://x/api/files/serve?path=Animalia%2FChordata%2FAves.md",
    "fetchFileServe must URL-encode forward slashes in the path");

  // ---- fetchFileServe — RFC 5987 filename fallback ----------
  // Starlette emits filename*=UTF-8''<encoded> for non-ASCII
  // basenames. The W3 parser must fall back to the RFC 5987
  // form when the simple `filename="X"` is absent.
  const f17 = makeFetch([{
    ok: true, status: 200, statusText: "OK",
    headers: {
      "content-type": "text/plain",
      "content-disposition":
        "inline; filename*=utf-8''Hola%20mundo%20%E2%9C%93.txt",
    },
    arrayBuffer: Promise.resolve(new TextEncoder().encode("hi").buffer),
  }]);
  const rfc = await api.fetchFileServe(
    { path: "x.txt" },
    { fetch: f17, baseUrl: "http://x" },
  );
  assert.strictEqual(rfc.filename, "Hola mundo \u2713.txt",
    "fetchFileServe must decode the RFC 5987 filename: got " +
    JSON.stringify(rfc.filename));

  // ---- fetchFileServe — verbatim Content-Type (no coercion) -
  // The server is the source of truth for the MIME — a future
  // server change adding a new extension lands without a
  // coordinated React update.
  const f18 = makeFetch([{
    ok: true, status: 200, statusText: "OK",
    headers: {
      "content-type": "application/x-custom-binary; charset=binary",
      "content-disposition": 'inline; filename="x.bin"',
    },
    arrayBuffer: Promise.resolve(new Uint8Array([1, 2, 3]).buffer),
  }]);
  const verbatim = await api.fetchFileServe(
    { path: "x.bin" },
    { fetch: f18, baseUrl: "http://x" },
  );
  assert.strictEqual(verbatim.contentType,
    "application/x-custom-binary; charset=binary",
    "fetchFileServe must preserve the verbatim Content-Type header");

  // ---- fetchFileServe — independence of Uint8Array ---------
  // The W2 port contract is value-typed — a future
  // implementation that returns a shared buffer would corrupt
  // concurrent consumers. Mirrors the W2 independence check
  // (`tests/test_research_application.py::test_compiled_
  // application_passes_runtime_contract` step 7).
  const f19 = makeFetch([
    { ok: true, status: 200, statusText: "OK",
      headers: { "content-type": "text/plain" },
      arrayBuffer: Promise.resolve(new Uint8Array([1, 2, 3]).buffer) },
    { ok: true, status: 200, statusText: "OK",
      headers: { "content-type": "text/plain" },
      arrayBuffer: Promise.resolve(new Uint8Array([4, 5, 6]).buffer) },
  ]);
  const a = await api.fetchFileServe({ path: "a.bin" },
    { fetch: f19, baseUrl: "http://x" });
  const b = await api.fetchFileServe({ path: "b.bin" },
    { fetch: f19, baseUrl: "http://x" });
  assert.notStrictEqual(a.content, b.content,
    "fetchFileServe must return independent Uint8Array instances");
  a.content[0] = 0xff;
  assert.strictEqual(b.content[0], 4,
    "fetchFileServe must return INDEPENDENT Uint8Arrays — mutating "
    + "one must not corrupt a concurrent consumer");

  // ---- fetchFileServe — HTTP non-OK (400 path-escape) -------
  const f20 = makeFetch([{ ok: false, status: 400, statusText: "Bad Request",
    json: { detail: "Path escapes research root" } }]);
  try {
    await api.fetchFileServe(
      { path: "../../etc/passwd" },
      { fetch: f20, baseUrl: "http://x" },
    );
    assert.fail("fetchFileServe must reject on 400 path-escape");
  } catch (err) {
    assert.strictEqual(err.status, 400,
      "ExplorerApiError.status must surface the HTTP status code: got " +
      err.status);
    assert(/400/.test(String(err.message)),
      "ExplorerApiError message must contain the status code: " +
      err.message);
  }

  // ---- fetchFileServe — HTTP non-OK (404 not found) ---------
  const f21 = makeFetch([{ ok: false, status: 404, statusText: "Not Found",
    json: { detail: "File not found" } }]);
  await assert.rejects(
    () => api.fetchFileServe({ path: "missing.pdf" },
      { fetch: f21, baseUrl: "http://x" }),
    (err) => /404/.test(String(err && err.message || err)),
    "fetchFileServe must reject on 404 with the status code in the message",
  );

  // ---- fetchFileServe — HTTP non-OK (413 oversized) ---------
  const f22 = makeFetch([{ ok: false, status: 413, statusText: "Payload Too Large",
    json: { detail: "File exceeds streaming cap" } }]);
  try {
    await api.fetchFileServe({ path: "huge.bin" },
      { fetch: f22, baseUrl: "http://x" });
    assert.fail("fetchFileServe must reject on 413");
  } catch (err) {
    assert.strictEqual(err.status, 413,
      "ExplorerApiError.status must surface the 413 status code");
  }

  // ---- fetchFileServe — baseUrl join ------------------------
  const f23 = makeFetch([{
    ok: true, status: 200, statusText: "OK",
    headers: { "content-type": "text/plain" },
    arrayBuffer: Promise.resolve(new Uint8Array([0]).buffer),
  }]);
  await api.fetchFileServe(
    { path: "x.txt" },
    { fetch: f23, baseUrl: "https://api.example.com/research/" },
  );
  assert.strictEqual(f23.calls[0].input,
    "https://api.example.com/research/api/files/serve?path=x.txt",
    "fetchFileServe must trim trailing slash from baseUrl");

  // ---- fetchFileServe — relative origin (no baseUrl) --------
  const f24 = makeFetch([{
    ok: true, status: 200, statusText: "OK",
    headers: { "content-type": "text/plain" },
    arrayBuffer: Promise.resolve(new Uint8Array([0]).buffer),
  }]);
  await api.fetchFileServe({ path: "x.txt" }, { fetch: f24 });
  assert.strictEqual(f24.calls[0].input,
    "/api/files/serve?path=x.txt",
    "fetchFileServe without baseUrl must stay relative-origin");

  // ---- port-compat runtime mirror ---------------------------
  // Calling the adapter through the narrower port surface
  // (after the structural-subtyping assignment) yields the
  // same end-to-end behaviour. This is the runtime mirror of
  // the compile-time port-compat fixture.
  //
  // The narrower port signature `fetchFiles(): Promise<ExplorerTree>`
  // carries NO `opts` argument — when the adapter is called
  // through the port, `opts.fetch` is undefined and
  // `defaultFetch()` falls back to `globalThis.fetch`. Node
  // 18+'s WHATWG fetch rejects relative URLs, so we install a
  // stub on `globalThis.fetch` for the duration of the mirror
  // test, then restore the original descriptor (the missing-
  // fetch guard test below relies on a clean override of
  // `globalThis.fetch`).
  const repo = port.__port_compatible__;
  assert.strictEqual(typeof repo.fetchFiles, "function",
    "port-compat __port_compatible__.fetchFiles must be a function");
  assert.strictEqual(typeof repo.fetchFileServe, "function",
    "port-compat __port_compatible__.fetchFileServe must be a function");

  const f25 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: EMPTY_TREE }]);
  const origFetchMirror = Object.getOwnPropertyDescriptor(
    globalThis, "fetch",
  );
  Object.defineProperty(globalThis, "fetch", {
    configurable: true,
    writable: true,
    value: f25,
  });
  try {
    // Call through the narrower port signature — no opts argument.
    const portTree = await repo.fetchFiles();
    assert.strictEqual(portTree.exists, false,
      "port-compat fetchFiles() must return the same shape as fetchFiles({}): got " +
      JSON.stringify(portTree));
    assert.strictEqual(f25.calls.length, 1,
      "port-compat fetchFiles() must route through the installed globalThis.fetch");
    assert.strictEqual(f25.calls[0].input, "/api/files",
      "port-compat fetchFiles() must build the canonical /api/files URL");
    // fetchFileServe through the narrower port signature — only
    // the request argument, no opts. The adapter's wider
    // signature is silently dropped on the narrower port
    // signature, so the installed globalThis.fetch is the fetch
    // the adapter reaches.
    const f26 = makeFetch([{
      ok: true, status: 200, statusText: "OK",
      headers: {
        "content-type": "text/plain",
        "content-disposition": 'inline; filename="x.txt"',
      },
      arrayBuffer: Promise.resolve(new Uint8Array([0x68, 0x69]).buffer),
    }]);
    Object.defineProperty(globalThis, "fetch", {
      configurable: true,
      writable: true,
      value: f26,
    });
    const portServed = await repo.fetchFileServe({ path: "x.txt" });
    assert.strictEqual(f26.calls.length, 1,
      "port-compat fetchFileServe({path}) must route through the installed globalThis.fetch");
    assert.strictEqual(portServed.filename, "x.txt",
      "port-compat fetchFileServe({path}) must return the same shape as "
      + "fetchFileServe({path}, {fetch, baseUrl})");
    assert.ok(portServed.content instanceof Uint8Array,
      "port-compat fetchFileServe({path}) must return a Uint8Array");
  } finally {
    if (origFetchMirror) {
      Object.defineProperty(globalThis, "fetch", origFetchMirror);
    } else {
      delete globalThis.fetch;
    }
  }

  // ---- default-fetch missing-error guard ---------------------
  // When no fetch is available on globalThis (Node ≤17 or a
  // strict CSP browser), the adapter throws ExplorerApiError
  // with an explanatory message. Mirrors the taxonomy adapter
  // helper. We override `globalThis.fetch` with `undefined`
  // (Node 18+ ships `fetch` as a non-configurable property, so
  // `delete globalThis.fetch` is a no-op — `Object.defineProperty`
  // with `configurable: true` is required to swap the value).
  const origDescriptor = Object.getOwnPropertyDescriptor(globalThis, "fetch");
  Object.defineProperty(globalThis, "fetch", {
    configurable: true,
    writable: true,
    value: undefined,
  });
  try {
    let caught = null;
    try {
      await api.fetchFiles();
    } catch (err) {
      caught = err;
    }
    assert.ok(caught, "fetchFiles must throw when globalThis.fetch is missing");
    assert.strictEqual(caught.name, "ExplorerApiError");
    assert(/no fetch implementation|pass opts\.fetch/i.test(caught.message),
      "missing-fetch error message must explain the fix: got " +
      caught.message);
  } finally {
    if (origDescriptor) {
      Object.defineProperty(globalThis, "fetch", origDescriptor);
    } else {
      delete globalThis.fetch;
    }
  }

  process.stdout.write("PASS\n");
})().catch((err) => {
  process.stderr.write("HARNESS_FAILURE: " + (err && err.stack || err) + "\n");
  process.exit(1);
});
"""


@pytest.fixture()
def compiled_infra(tmp_path: Path, require_toolchain: None) -> tuple[Path, Path]:
    """Compile api.ts to CommonJS, write the port-compat fixture
    + the Node harness, and return (compiled-infra path, harness
    path, compiled-fixture path). Mirrors the
    `test_taxonomy_infra.py::compiled_infra` fixture."""
    for p in (INFRA_FILE, DOMAIN_FILE, PORTS_FILE):
        if not p.is_file():
            pytest.skip(f"missing required source: {p}")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    # Write the port-compat fixture next to the infra file so
    # the relative imports resolve correctly. The fixture is
    # cleaned up in the fixture's teardown (via try/finally
    # below) so the worktree is not polluted.
    fixture_path = INFRA_FILE.parent / "__port_compat_fixture.ts"
    fixture_path.write_text(_PORT_COMPAT_FIXTURE)
    harness = tmp_path / "harness.cjs"
    harness.write_text(_RUNTIME_HARNESS)
    try:
        result = _run_tsc_isolated_multi(
            [INFRA_FILE, DOMAIN_FILE, PORTS_FILE, fixture_path],
            out_dir,
        )
        assert result.returncode == 0, (
            f"infra/api.ts failed to compile in isolated strict mode.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        compiled_infra_path = (
            out_dir / "infrastructure" / "api.js"
        )
        compiled_fixture = (
            out_dir / "infrastructure" / "__port_compat_fixture.js"
        )
        compiled_ports = out_dir / "application" / "ports.js"
        compiled_domain = out_dir / "domain" / "explorer.js"
        for path, label in (
            (compiled_infra_path, "infrastructure/api.js"),
            (compiled_fixture, "infrastructure/__port_compat_fixture.js"),
            (compiled_ports, "application/ports.js"),
            (compiled_domain, "domain/explorer.js"),
        ):
            assert path.is_file(), (
                f"tsc did not emit `{label}` at {path}. "
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        # Symlink the compiled port-compat fixture next to the
        # compiled infra so the harness's `require()` resolves
        # relative to the infra directory. (Node's require
        # resolves relative to the file doing the require, not
        # the entry point — and the port-compat fixture imports
        # `./api`, so it must live next to the compiled api.js.)
        target = compiled_infra_path.parent / "__port_compat_fixture.js"
        if not target.exists():
            target.write_bytes(compiled_fixture.read_bytes())
        return compiled_infra_path, harness
    finally:
        if fixture_path.is_file():
            fixture_path.unlink()


def test_compiled_infra_passes_runtime_contract(
    compiled_infra: tuple[Path, Path],
) -> None:
    """Under Node (ES2022, no DOM, fetch injected) the compiled
    W3 module + the W2 port-compat fixture + the W1 domain
    contract together satisfy the W3 contract end-to-end:

      1. `fetchFiles` builds `/api/files` relative to `baseUrl`.
      2. `fetchFiles` projects every wire field verbatim — both
         folder + file shapes, with no coercion, no synthesized
         fields, and a structural-regression guard on
         ExplorerFileNode.
      3. `fetchFiles` handles the `exists: false` + `root: null`
         empty-state path (the FastAPI server returns 200 with
         this shape when the research root is missing).
      4. `fetchFiles` rejects on HTTP non-OK with the status code
         in the message + on `ExplorerApiError.status`.
      5. `fetchFiles` rejects on malformed JSON, non-object
         payloads, null payloads, schema-invalid payloads
         (missing `exists`, exists=true with root=null,
         exists=false with non-null root, unknown node type,
         file node missing extension).
      6. `fetchFileServe` builds
         `/api/files/serve?path=<encodeURIComponent>` so paths
         with spaces / accents / forward slashes round-trip
         through FastAPI's Query() validator.
      7. `fetchFileServe` returns Uint8Array bytes (verbatim
         from `response.arrayBuffer()`), verbatim Content-Type,
         and the parsed basename from the Content-Disposition
         header (both the simple `filename="X"` form and the
         RFC 5987 `filename*=UTF-8''<encoded>` form).
      8. `fetchFileServe` rejects on HTTP non-OK (400 path-
         escape, 404 not-found, 413 oversized) with the status
         code in `ExplorerApiError.status`.
      9. `fetchFileServe` returns INDEPENDENT Uint8Array
        instances per call (the W2 port contract is value-typed;
        a future implementation that returns a shared buffer
        would corrupt concurrent consumers).
     10. The compile-time port-compat assignment (`const
        _fetchFiles: ExplorerRepository["fetchFiles"] = fetchFiles`)
        fires BEFORE this runtime harness runs, so a port
        signature drift is caught at the compile gate (the
        fixture fails to typecheck) rather than at runtime.
     11. The runtime port-compat mirror exercises the adapter
        through the narrower port surface (no `opts` argument)
        and confirms end-to-end behaviour.
     12. The default-fetch missing-error guard throws
        `ExplorerApiError` with an explanatory message when
        `globalThis.fetch` is unavailable (Node ≤17 / strict
        CSP browser).
    """
    compiled, harness = compiled_infra
    # The runtime harness loads the compiled infra module + the
    # compiled port-compat fixture (which re-exports the
    # narrower port-shaped reference to the adapter).
    result = subprocess.run(
        ["node", str(harness), str(compiled),
         str(compiled.parent / "__port_compat_fixture.js")],
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
# Project-wide strict typecheck — the W3 contract must compile
# against the project's tsconfig (not just the isolated strict
# flags the focused compile uses). A future PR that breaks a
# downstream consumer (presentation, infrastructure, design-system)
# is caught here.
# ---------------------------------------------------------------------------
def test_project_wide_strict_typecheck_for_research_infra(
    require_toolchain: None,
) -> None:
    """Strict typecheck across `src/modules/research/` against
    the project's tsconfig flags (`strict`, `noUncheckedIndexedAccess`,
    `noUnusedLocals`, `noUnusedParameters`, `noImplicitReturns`,
    `noFallthroughCasesInSwitch`). The compile is `--noEmit` so
    no output touches the worktree; it only validates that the
    W3 infra file (and every other Research file) compiles
    cleanly under the project's full strict mode flag set.

    `noEmit: true` in the project tsconfig prevents accidental
    writes; the focused compile flag set here adds the strict
    flags explicitly so a tsconfig regression that drops one
    does not silently weaken the gate. The test skips when
    `node_modules` is missing — the `next` plugin the project
    tsconfig pulls in needs `@types/next` / `next` installed
    (see `package.json`)."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
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
            str(DOMAIN_FILE), str(PORTS_FILE), str(INFRA_FILE),
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
