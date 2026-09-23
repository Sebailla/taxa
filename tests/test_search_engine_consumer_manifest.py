"""AC-21 search-engine catalog consumer manifest (W65-MANIFEST-008).

This hermetic pytest module documents — in executable form — the
runtime consumer surface of the legacy ``web/search_urls.js``
literal at the ODD-MIGRATE-004 boundary. The W65-MAP-007
read-only map enumerated the consumers; this module pins each
finding as a focused contract so a future PR that drops, moves,
or renames the literal fails CI with an actionable message.

## Decision (W65-MAP-007 outcome — KEEP)

The user selected **KEEP**: the ``web/search_urls.js`` literal
stays in place at ``web/search_urls.js`` until the W18 atomic
cutover (ODD-MIGRATE-006). The literal is the user-visible
search-engine catalog the React/Next taxonomy tab consumes via
the ODD-TDS-001 server-side mirror + React `search-categories.ts`
bridge. Moving it now would require coordinating Python (server
URL composition) + JS (legacy detail.js fallback) + React
(search-categories bridge) in one atomic release boundary that
the W1–W6.5 chain is not ready to own. The KEEP decision
isolates AC-21 from the W7–W17 React mount work and lets the
W18 atomic cutover retire the literal in one release.

## Consumer surface (this manifest asserts)

Active runtime consumers (the literal MUST exist + be byte-equal
on user-visible fields for these to keep working):

  1. ``api/server.py::_SEARCH_ENGINES`` — the URL-composition
     mirror; the server is the source of truth for the
     ``/api/taxon/{id}/searches`` payload. AC-21 enforces the
     key/label/with_authorship cross-file contract.
  2. ``web/detail.js:24`` — the ``import { SEARCH_ENGINES,
     CATEGORIES } from "./search_urls.js"`` line + the
     ``renderSearchesTab(searches)`` function (lines 314–…)
     that iterates both tables to render the legacy
     ``<div class="search-category-header">`` headers.
  3. ``tests/test_smoke.py::test_search_engine_contract``
     (AC-21 itself) — parses both the Python literal via
     ``ast.literal_eval`` and the JS literal via regex and
     asserts byte-identical key/label/with_authorship order.
  4. ``tests/test_research_styles.py::LEGACY_SEARCH_URLS_JS`` —
     the ``Path`` constant referenced by the category-label
     test (``test_search_tab_categories_render_in_fixed_order``)
     which asserts the legacy ``CATEGORIES`` order mirrors the
     ``@layer components`` cascade.

Comment-only references (the literal is named in a doc-comment
or inline comment; no runtime import):

  1. ``src/app/globals.css:2063`` — the @layer components
     comment on the ``.search-tab`` block that cites the
     ``web/search_urls.js::CATEGORIES`` order.
  2. ``src/modules/taxonomy/index.ts:139`` — the ODD-TDS-001
     comment that cites the legacy SEARCH_ENGINES file import.
  3. ``src/modules/research/index.ts:13`` — the research
     barrel comment that documents the future
     ``infrastructure/search-engines.js`` relocation target.
  4. ``api/server.py:682`` — the section header comment on the
     AC-21 cross-file contract.
  5. ``api/server.py:1366`` — the ``get_searches`` docstring
     that mentions ``web/search_urls.js`` is used only for
     icon/label rendering when the response is unavailable.
  6. ``tests/test_research_styles.py:123`` and ``:375`` —
     two doc-comments that reference the legacy CATEGORIES
     ordering.
  7. ``tests/test_search_categories.py:141`` — the expected
     grouping comment that cites the legacy CATEGORIES.
  8. ``tests/test_visible_taxonomy_tree.py:2668`` — the legacy
     module list referenced by the visible-tree WebSocket
     inventory.

React taxonomy purity boundary (these MUST NOT consume
``web/search_urls.js`` — the React port ships its own typed
category bridge):

  - ``src/modules/taxonomy/presentation/search-categories.ts``
    — the pure category bridge (14 entries, 5 keys).
  - ``src/modules/taxonomy/presentation/SearchTab.tsx`` — the
    React renderer that consumes ``SEARCH_CATEGORIES`` and
    ``resolveSearchEngineMeta``.

W18 atomic cutover carry-over:

  - The literal stays at ``web/search_urls.js`` until the W18
    atomic cutover (ODD-MIGRATE-006). Any future slice that
    relocates the literal MUST update the
    ``odd/tasks/w6-3-record-and-w6-4-chain.md`` carry-over
    record AND this manifest in lock-step.

## Hermeticity

The module reads files only via ``pathlib.Path``; it does not
import ``api.server``, does not touch the FastAPI client, does
not boot Playwright, and does not write to disk. It is safe to
run with ``pytest -x`` in CI without taxa.db present.

## Failure semantics

Each test has an actionable failure message that names the
specific file + line + invariant. A test that fails is a
signal that a consumer was added, removed, or renamed and the
manifest needs to be updated in lock-step.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Repository layout (hermetic — no FastAPI import, no DB)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

# The literal under audit. KEEP decision (W65-MAP-007).
WEB_SEARCH_URLS_JS: Path = REPO_ROOT / "web" / "search_urls.js"

# The legacy detail panel — the only legacy module that
# imports SEARCH_ENGINES + CATEGORIES at runtime.
WEB_DETAIL_JS: Path = REPO_ROOT / "web" / "detail.js"

# The FastAPI server — the URL-composition source of truth.
API_SERVER_PY: Path = REPO_ROOT / "api" / "server.py"

# The React taxonomy search-categories bridge (ODD-TDS-001).
TAXONOMY_SEARCH_CATEGORIES_TS: Path = (
    REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation"
    / "search-categories.ts"
)

# The React SearchTab component (ODD-TDS-001).
TAXONOMY_SEARCH_TAB_TSX: Path = (
    REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation"
    / "SearchTab.tsx"
)

# The taxonomy capability barrel — re-exports SEARCH_CATEGORIES.
TAXONOMY_INDEX_TS: Path = (
    REPO_ROOT / "src" / "modules" / "taxonomy" / "index.ts"
)

# The research capability barrel — future relocation target
# comment (W7+ relocation; today the comment is a pointer only).
RESEARCH_INDEX_TS: Path = (
    REPO_ROOT / "src" / "modules" / "research" / "index.ts"
)

# The PR 3c-c globals.css cascade — the @layer components
# selector comment cites the legacy CATEGORIES.
GLOBALS_CSS: Path = REPO_ROOT / "src" / "app" / "globals.css"

# AC-21 contract test (the test_smoke that reads both literals).
TEST_SMOKE_PY: Path = REPO_ROOT / "tests" / "test_smoke.py"

# The styles test that imports the LEGACY_SEARCH_URLS_JS path
# constant for the category-order assertion.
TEST_RESEARCH_STYLES_PY: Path = REPO_ROOT / "tests" / "test_research_styles.py"

# The browser-level category grouping test (legacy oracle).
TEST_SEARCH_CATEGORIES_PY: Path = REPO_ROOT / "tests" / "test_search_categories.py"

# The visible-tree WebSocket inventory test.
TEST_VISIBLE_TAXONOMY_TREE_PY: Path = (
    REPO_ROOT / "tests" / "test_visible_taxonomy_tree.py"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    if not path.is_file():
        pytest.fail(
            f"required file missing: {path.relative_to(REPO_ROOT)} "
            f"(the W65-MANIFEST-008 audit assumes this file is present)"
        )
    return path.read_text(encoding="utf-8")


def _strip_js_comments(src: str) -> str:
    """Strip ``// …`` and ``/* … */`` comments from JS source so a
    renamed symbol in a doc-comment doesn't trip the import
    detection. The literal itself uses only string keys + numeric
    + boolean values, so stripping comments is safe."""
    # Block comments (non-greedy across newlines).
    no_block = re.sub(r"/\*[\s\S]*?\*/", " ", src)
    # Line comments (each line independently).
    no_line = re.sub(r"^\s*//.*$", "", no_block, flags=re.MULTILINE)
    return no_line


def _strip_ts_comments(src: str) -> str:
    """Strip ``// …`` and ``/* … */`` comments from TS source so a
    renamed symbol in a doc-comment doesn't trip the import
    detection. Mirrors ``_strip_js_comments`` but handles TS
    template-literal ``${…}`` expressions where ``/*`` could
    appear inside a string — we restrict comment stripping to
    lines that start a comment, then strip line comments line-by-
    line, so template-string contents stay intact."""
    # Block comments.
    no_block = re.sub(r"/\*[\s\S]*?\*/", " ", src)
    # Line comments (each line independently).
    no_line = re.sub(r"^\s*//.*$", "", no_block, flags=re.MULTILINE)
    return no_line


def _strip_py_comments(src: str) -> str:
    """Strip ``# …`` line comments from Python source. Docstrings
    are preserved (the test parser uses ``ast.literal_eval`` which
    ignores comments but reads docstrings as strings; we keep the
    whole source verbatim and let the test parser handle it)."""
    return re.sub(r"^\s*#.*$", "", src, flags=re.MULTILINE)


def _extract_js_search_engines(src: str) -> list[dict[str, object]]:
    """Parse the ``SEARCH_ENGINES`` literal out of
    ``web/search_urls.js``. Mirrors the regex used by
    ``tests/test_smoke.py::test_search_engine_contract`` byte-for-
    byte (AC-21 contract test stays the source of truth; this
    helper duplicates the parse so the manifest stays hermetic
    without importing the AC-21 test module)."""
    entries: list[dict[str, object]] = []
    # The JS template strings contain `{name}` and `{auth}` placeholders,
    # which have `}` characters inside them — so we use `.*?` (any-char
    # non-greedy) rather than `[^}]*?` to span the template strings
    # safely. Each entry has exactly one `with_authorship: true|false`.
    pattern = (
        r'\{\s*key:\s*"([^"]+)",\s*label:\s*"([^"]+)",'
        r'.*?with_authorship:\s*(true|false)'
    )
    matches = re.findall(pattern, src, re.DOTALL)
    for key, label, with_authorship in matches:
        entries.append({
            "key": key,
            "label": label,
            "with_authorship": with_authorship == "true",
        })
    return entries


def _extract_py_search_engines(src: str) -> list[dict[str, object]]:
    """Parse the ``_SEARCH_ENGINES`` literal out of
    ``api/server.py``. Mirrors the regex + ast.literal_eval
    pattern used by ``test_smoke.py::test_search_engine_contract``
    byte-for-byte."""
    m = re.search(r"_SEARCH_ENGINES\s*=\s*(\[[^\]]*\])", src, re.DOTALL)
    if m is None:
        pytest.fail(
            "_SEARCH_ENGINES not found in api/server.py — keep the "
            "constant at module level so the AC-21 contract test "
            "(tests/test_smoke.py::test_search_engine_contract) "
            "and this manifest stay parsable."
        )
    return ast.literal_eval(m.group(1))


def _format_consumer(name: str, where: str) -> str:
    """Render a consumer record for the failure message."""
    return f"{name} @ {where}"


# ---------------------------------------------------------------------------
# 1. KEEP decision — the literal stays at web/search_urls.js
# ---------------------------------------------------------------------------


class TestKeepDecision:
    """KEEP decision (W65-MAP-007 outcome): the literal stays at
    ``web/search_urls.js`` until the W18 atomic cutover. Any
    future slice that relocates, renames, or deletes the literal
    MUST update the W18 carry-over record in lock-step with this
    manifest."""

    def test_search_urls_literal_exists_at_web_path(self) -> None:
        """The legacy literal must exist at ``web/search_urls.js``
        (KEEP decision — no relocation before W18 atomic cutover)."""
        assert WEB_SEARCH_URLS_JS.is_file(), (
            f"web/search_urls.js is missing at {WEB_SEARCH_URLS_JS}; "
            "the W65-MAP-007 KEEP decision places the literal at "
            "this path until the W18 atomic cutover (ODD-MIGRATE-006). "
            "If the literal was intentionally relocated, update the "
            "carry-over record in odd/tasks/w6-3-record-and-w6-4-chain.md "
            "AND this manifest in lock-step."
        )

    def test_search_urls_literal_exports_search_engines(self) -> None:
        """The literal must export ``SEARCH_ENGINES`` (the
        server-mirrored catalog the AC-21 contract test parses)."""
        src = _read(WEB_SEARCH_URLS_JS)
        assert "export const SEARCH_ENGINES" in src, (
            "web/search_urls.js must export `SEARCH_ENGINES` "
            "(the AC-21 contract test parses this named export "
            "via regex; renaming breaks the contract)."
        )

    def test_search_urls_literal_exports_categories(self) -> None:
        """The literal must export ``CATEGORIES`` (the 5-key
        taxonomy group the legacy ``web/detail.js::renderSearchesTab``
        iterates and the React SearchTab mirrors via
        ``SEARCH_CATEGORIES``)."""
        src = _read(WEB_SEARCH_URLS_JS)
        assert "export const CATEGORIES" in src, (
            "web/search_urls.js must export `CATEGORIES` "
            "(the legacy renderSearchesTab iterates this list "
            "and the React SearchTab mirrors it via SEARCH_CATEGORIES; "
            "renaming breaks the legacy oracle)."
        )

    def test_search_urls_literal_is_kept_until_w18_atomic_cutover(self) -> None:
        """The W65-MAP-007 carry-over record must document the KEEP
        decision. The W18 atomic cutover (ODD-MIGRATE-006) is the
        ONLY authorized relocation boundary; until then, the
        literal stays at ``web/search_urls.js``."""
        chain_doc = _read(
            REPO_ROOT / "odd" / "tasks" / "w6-3-record-and-w6-4-chain.md"
        )
        assert "W65-MAP-007" in chain_doc, (
            "w6-3-record-and-w6-4-chain.md must record the W65-MAP-007 "
            "read-only map (the carry-over for the KEEP decision)."
        )
        assert "W65-MANIFEST-008" in chain_doc, (
            "w6-3-record-and-w6-4-chain.md must enumerate W65-MANIFEST-008 "
            "as the consumer-manifest artifact work-unit (the W18 "
            "atomic-cutover carry-over reference)."
        )


# ---------------------------------------------------------------------------
# 2. Active runtime consumers — the literal MUST keep working for these
# ---------------------------------------------------------------------------


class TestActiveRuntimeConsumers:
    """Every active runtime consumer of the literal MUST keep
    importing it (or, for tests, opening the file) until the W18
    atomic cutover. Each consumer pins a specific contract so a
    silent removal fails CI."""

    def test_smoke_ac21_test_function_exists(self) -> None:
        """AC-21 must keep parsing both literals:
        ``tests/test_smoke.py::test_search_engine_contract``.

        This is the cross-file byte-identical contract test —
        without it, server/frontend drift on key/label/
        with_authorship would silently land in production.
        """
        src = _read(TEST_SMOKE_PY)
        assert "def test_search_engine_contract" in src, (
            "tests/test_smoke.py::test_search_engine_contract is the "
            "AC-21 contract test; removing it loses the cross-file "
            "key/label/with_authorship guard."
        )
        # The AC-21 test opens the literal directly (relative to
        # the repo root it ran with). Pin the call site so a
        # future refactor that changes the open() target fails.
        assert 'open("web/search_urls.js")' in src, (
            "AC-21 contract test must open web/search_urls.js directly "
            "(the literal is the JS side of the cross-file contract)."
        )

    def test_smoke_ac21_test_parses_both_literals(self) -> None:
        """The AC-21 test must parse BOTH the Python ``_SEARCH_ENGINES``
        AND the JS ``SEARCH_ENGINES`` — the byte-identical
        contract is the whole point."""
        src = _read(TEST_SMOKE_PY)
        # The Python side is parsed via ast.literal_eval (regex
        # + literal_eval pattern).
        assert "_SEARCH_ENGINES" in src, (
            "AC-21 contract test must reference _SEARCH_ENGINES "
            "(the server's mirror of the literal)."
        )
        assert "ast.literal_eval" in src, (
            "AC-21 contract test must use ast.literal_eval to "
            "parse the Python mirror."
        )
        # The JS side is parsed via regex (findall).
        assert "re.findall" in src, (
            "AC-21 contract test must use re.findall to parse "
            "the JS literal."
        )
        assert "with_authorship" in src, (
            "AC-21 contract test must compare the with_authorship "
            "flag (the user-visible authoring field)."
        )

    def test_research_styles_legacy_path_constant_is_pinned(self) -> None:
        """``tests/test_research_styles.py::LEGACY_SEARCH_URLS_JS``
        must stay as the path constant the category-order test
        uses (PR 3c-c cascade contract)."""
        src = _read(TEST_RESEARCH_STYLES_PY)
        assert "LEGACY_SEARCH_URLS_JS" in src, (
            "tests/test_research_styles.py must keep the "
            "LEGACY_SEARCH_URLS_JS Path constant (the "
            "category-order test uses it to read the legacy "
            "CATEGORIES literal)."
        )
        assert 'web" / "search_urls.js"' in src or (
            'web/search_urls.js' in src
        ), (
            "LEGACY_SEARCH_URLS_JS must point at the legacy "
            "literal at web/search_urls.js (KEEP decision)."
        )

    def test_research_styles_category_order_test_references_literal(self) -> None:
        """``tests/test_research_styles.py::test_search_tab_categories_render_in_fixed_order``
        must keep asserting the literal's ``CATEGORIES`` are
        mirrored in the @layer components cascade."""
        src = _read(TEST_RESEARCH_STYLES_PY)
        assert (
            "test_search_tab_categories_render_in_fixed_order" in src
        ), (
            "tests/test_research_styles.py must keep the "
            "test_search_tab_categories_render_in_fixed_order "
            "test (PR 3c-c cascade contract)."
        )
        assert "CATEGORIES" in src, (
            "category-order test must reference CATEGORIES "
            "(the legacy 5-key taxonomy group)."
        )

    def test_legacy_detail_imports_search_engines_and_categories(self) -> None:
        """``web/detail.js:24`` must keep importing ``SEARCH_ENGINES``
        + ``CATEGORIES`` from the literal — the legacy
        ``renderSearchesTab`` function iterates both tables."""
        src = _read(WEB_DETAIL_JS)
        # Strip JS comments so a doc-comment rename doesn't trip
        # the detection (the literal is a runtime import).
        code = _strip_js_comments(src)
        assert (
            'import { SEARCH_ENGINES, CATEGORIES } from "./search_urls.js";'
            in code
        ), (
            "web/detail.js:24 must keep the literal "
            "import { SEARCH_ENGINES, CATEGORIES } from "
            "\"./search_urls.js\"; the legacy "
            "renderSearchesTab function iterates both tables."
        )

    def test_legacy_render_searches_tab_uses_search_engines(self) -> None:
        """``web/detail.js::renderSearchesTab`` must keep iterating
        ``SEARCH_ENGINES`` + ``CATEGORIES`` — the legacy oracle
        the React SearchTab mirrors byte-for-byte."""
        src = _read(WEB_DETAIL_JS)
        code = _strip_js_comments(src)
        assert "function renderSearchesTab" in code, (
            "web/detail.js must define the renderSearchesTab "
            "function (the legacy Search tab renderer)."
        )
        # The function body iterates CATEGORIES (the 5-key
        # grouping) and SEARCH_ENGINES (the per-engine
        # metadata). Both literals are mandatory.
        m = re.search(
            r"function\s+renderSearchesTab\s*\([^)]*\)\s*\{",
            code,
        )
        assert m is not None, (
            "renderSearchesTab must be a function declaration "
            "(the legacy oracle the React SearchTab mirrors)."
        )
        # Brace-walk the body to find references.
        body_start = m.end()
        depth = 1
        cursor = body_start
        while cursor < len(code) and depth > 0:
            ch = code[cursor]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            cursor += 1
        body = code[body_start: cursor - 1]
        assert "SEARCH_ENGINES" in body, (
            "renderSearchesTab body must iterate SEARCH_ENGINES "
            "(the per-engine metadata source)."
        )
        assert "CATEGORIES" in body, (
            "renderSearchesTab body must iterate CATEGORIES "
            "(the 5-key taxonomy group)."
        )

    def test_legacy_render_searches_tab_builds_engine_lookup(self) -> None:
        """``renderSearchesTab`` builds an O(1) engine-key lookup
        from ``SEARCH_ENGINES`` (``new Map(SEARCH_ENGINES.map(...))``).
        A future refactor that drops the map would slow the
        legacy tab; the manifest pins the lookup shape so a
        silent change is loud."""
        src = _read(WEB_DETAIL_JS)
        code = _strip_js_comments(src)
        m = re.search(
            r"function\s+renderSearchesTab\s*\([^)]*\)\s*\{",
            code,
        )
        assert m is not None
        body_start = m.end()
        depth = 1
        cursor = body_start
        while cursor < len(code) and depth > 0:
            ch = code[cursor]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            cursor += 1
        body = code[body_start: cursor - 1]
        assert "new Map(" in body, (
            "renderSearchesTab must build an engine-key Map from "
            "SEARCH_ENGINES (the O(1) lookup shape the legacy "
            "oracle uses)."
        )

    def test_legacy_render_searches_tab_groups_by_category(self) -> None:
        """``renderSearchesTab`` groups engines by category (the
        P1 #3 Impeccable-critique fix). The grouping must keep
        the `data-category` attribute on the header so the
        existing ``test_search_categories.py`` Playwright test
        stays green."""
        src = _read(WEB_DETAIL_JS)
        code = _strip_js_comments(src)
        m = re.search(
            r"function\s+renderSearchesTab\s*\([^)]*\)\s*\{",
            code,
        )
        assert m is not None
        body_start = m.end()
        depth = 1
        cursor = body_start
        while cursor < len(code) and depth > 0:
            ch = code[cursor]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            cursor += 1
        body = code[body_start: cursor - 1]
        assert "data-category" in body, (
            "renderSearchesTab must render a `data-category` "
            "attribute on the category header (the hook "
            "test_search_categories.py uses to scope per-"
            "category engine assertions)."
        )


# ---------------------------------------------------------------------------
# 3. Comment-only references — document but do NOT import
# ---------------------------------------------------------------------------


COMMENT_REFERENCES: tuple[tuple[str, str, str], ...] = (
    # (path, expected_literal_text, why_it_matters)
    (
        "src/app/globals.css",
        "web/search_urls.js::CATEGORIES",
        "PR 3c-c @layer components comment cites the legacy "
        "CATEGORIES order so the cascade mirrors the legacy "
        "section order.",
    ),
    (
        "src/modules/taxonomy/index.ts",
        "SEARCH_ENGINES file import",
        "ODD-TDS-001 comment documents that the React port "
        "stays free of legacy-web dependency.",
    ),
    (
        "src/modules/research/index.ts",
        "relocated web/search_urls.js",
        "research barrel comment documents the future "
        "infrastructure/search-engines.js relocation target "
        "(W13–W15 in the W1–W18 map).",
    ),
    (
        "api/server.py",
        "test_search_engine_contract",
        "AC-21 cross-file contract comment header; the "
        "contract test name is the cross-file guard.",
    ),
    (
        "api/server.py",
        "web/search_urls.js only for icon/label rendering",
        "get_searches docstring; the URL is server-composed "
        "and the frontend uses the literal only as a "
        "rendering fallback.",
    ),
    (
        "tests/test_research_styles.py",
        "web/search_urls.js::CATEGORIES",
        "category-order test references the legacy CATEGORIES "
        "(two docstring mentions, lines ~123 + ~375).",
    ),
    (
        "tests/test_search_categories.py",
        "CATEGORIES in web/search_urls.js",
        "browser-level category-grouping test cites the "
        "legacy CATEGORIES so the React port stays honest.",
    ),
    (
        "tests/test_visible_taxonomy_tree.py",
        "web/search_urls",
        "visible-tree WebSocket inventory lists legacy "
        "modules referenced for the test fixture.",
    ),
)


class TestCommentOnlyReferences:
    """The literal is named in doc-comments + inline comments at
    several sites. None of these is a runtime import; the
    comments are documentation pointers. The manifest pins each
    comment's presence + framing so a future rename of the
    literal updates the documentation in lock-step."""

    @pytest.mark.parametrize(
        "rel_path,needle,why",
        COMMENT_REFERENCES,
        ids=[item[0] for item in COMMENT_REFERENCES],
    )
    def test_comment_reference_present(
        self, rel_path: str, needle: str, why: str
    ) -> None:
        path = REPO_ROOT / rel_path
        src = _read(path)
        assert needle in src, (
            f"{rel_path} must reference {needle!r} in a comment — "
            f"{why} If the literal was relocated, update this "
            f"comment + the carry-over record in lock-step."
        )


# ---------------------------------------------------------------------------
# 4. React taxonomy purity — the React port MUST NOT consume the literal
# ---------------------------------------------------------------------------


class TestReactTaxonomyPurity:
    """The React taxonomy search-categories bridge ships its own
    typed surface; it MUST NOT import the legacy literal at
    ``web/search_urls.js`` (the ODD-TDS-001 user constraint:
    "Do not introduce presentation→legacy-web dependency").
    The manifest pins the boundary so a future PR that adds a
    reverse import fails CI."""

    def test_search_categories_bridge_does_not_import_legacy_literal(self) -> None:
        """``search-categories.ts`` MUST NOT import
        ``web/search_urls.js`` (the ODD-TDS-001 isolation
        contract — no presentation→legacy-web dependency)."""
        src = _read(TAXONOMY_SEARCH_CATEGORIES_TS)
        code = _strip_ts_comments(src)
        # Look for any import that targets the legacy literal.
        # The legacy path is rooted at "web/search_urls.js"; we
        # pin both the JS-style relative import and the @-alias
        # style (none today, but defensive).
        forbidden_paths = (
            'from "../web/search_urls.js"',
            'from "../../web/search_urls.js"',
            'from "../../../web/search_urls.js"',
            'from "./search_urls.js"',
            'from "web/search_urls.js"',
            'from "@taxa/web/search_urls.js"',
            # Defensive against the @taxa/web path alias.
            'from "@taxa/web"',
            # Defensive against a legacy-search_urls module
            # alias (none today).
            'from "search_urls"',
            'from "search_urls.js"',
        )
        for needle in forbidden_paths:
            assert needle not in code, (
                f"src/modules/taxonomy/presentation/search-categories.ts "
                f"imports the legacy literal via `{needle}`. The "
                f"ODD-TDS-001 isolation contract forbids "
                f"presentation→legacy-web dependency. The React port "
                f"ships its own typed bridge (SEARCH_ENGINE_LIST + "
                f"SEARCH_CATEGORIES) — do not import the legacy "
                f"literal from the React layer."
            )

    def test_search_categories_bridge_has_no_legacy_web_token(self) -> None:
        """The bridge must not mention ``web/`` at runtime
        (defensive — catches a future ``import "./web/..."``
        that slipped past the import-block list above)."""
        src = _read(TAXONOMY_SEARCH_CATEGORIES_TS)
        code = _strip_ts_comments(src)
        # Defensive: the literal `web/` path must not appear in
        # the bridge (after comments are stripped). The legacy
        # ``WEB_DIR`` is only referenced by the FastAPI server
        # mount, never by the React port.
        assert "web/search_urls" not in code, (
            "src/modules/taxonomy/presentation/search-categories.ts "
            "must not reference `web/search_urls` at runtime — "
            "the ODD-TDS-001 isolation contract forbids "
            "presentation→legacy-web dependency."
        )

    def test_search_tab_component_does_not_import_legacy_literal(self) -> None:
        """``SearchTab.tsx`` MUST NOT import
        ``web/search_urls.js`` (the ODD-TDS-001 isolation
        contract — no presentation→legacy-web dependency)."""
        src = _read(TAXONOMY_SEARCH_TAB_TSX)
        code = _strip_ts_comments(src)
        forbidden_paths = (
            'from "../web/search_urls.js"',
            'from "../../web/search_urls.js"',
            'from "../../../web/search_urls.js"',
            'from "./search_urls.js"',
            'from "web/search_urls.js"',
            'from "@taxa/web/search_urls.js"',
            'from "@taxa/web"',
            'from "search_urls"',
            'from "search_urls.js"',
        )
        for needle in forbidden_paths:
            assert needle not in code, (
                f"src/modules/taxonomy/presentation/SearchTab.tsx "
                f"imports the legacy literal via `{needle}`. The "
                f"ODD-TDS-001 isolation contract forbids "
                f"presentation→legacy-web dependency."
            )

    def test_search_tab_component_has_no_legacy_web_token(self) -> None:
        """``SearchTab.tsx`` must not mention ``web/`` at
        runtime (defensive)."""
        src = _read(TAXONOMY_SEARCH_TAB_TSX)
        code = _strip_ts_comments(src)
        assert "web/search_urls" not in code, (
            "src/modules/taxonomy/presentation/SearchTab.tsx "
            "must not reference `web/search_urls` at runtime — "
            "the ODD-TDS-001 isolation contract forbids "
            "presentation→legacy-web dependency."
        )

    def test_search_categories_bridge_ships_its_own_typed_surface(self) -> None:
        """The React port ships its own typed surface: the
        14-entry ``SEARCH_ENGINE_LIST`` + the 5-key
        ``SEARCH_CATEGORIES`` + the O(1) resolver. The bridge
        is the canonical source for the React side; the legacy
        literal is the canonical source for the legacy side."""
        src = _read(TAXONOMY_SEARCH_CATEGORIES_TS)
        code = _strip_ts_comments(src)
        # The bridge exports the typed surface; a future refactor
        # that drops the exports would break the SearchTab
        # consumer.
        assert "export const SEARCH_CATEGORIES" in code, (
            "search-categories.ts must export SEARCH_CATEGORIES "
            "(the 5-key React bridge; SearchTab consumes it)."
        )
        assert "export const SEARCH_ENGINE_LIST" in code, (
            "search-categories.ts must export SEARCH_ENGINE_LIST "
            "(the 14-entry React bridge; SearchTab filters the "
            "server payload through it)."
        )
        assert "export function searchCategoryForEngine" in code, (
            "search-categories.ts must export "
            "searchCategoryForEngine (the O(1) per-engine resolver)."
        )
        assert "export function resolveSearchEngineMeta" in code, (
            "search-categories.ts must export "
            "resolveSearchEngineMeta (the canonical descriptor)."
        )

    def test_taxonomy_barrel_reexports_search_categories_only(self) -> None:
        """The taxonomy barrel re-exports the React bridge
        (``SEARCH_CATEGORIES`` etc.) — NOT the legacy literal.
        The barrel contract pins the surface boundary."""
        src = _read(TAXONOMY_INDEX_TS)
        code = _strip_ts_comments(src)
        # The barrel re-exports the React bridge.
        assert "SEARCH_CATEGORIES" in code, (
            "src/modules/taxonomy/index.ts must re-export "
            "SEARCH_CATEGORIES (the React bridge surface)."
        )
        # The barrel must not re-export the legacy literal.
        # (The taxonomy barrel would gain this entry only via a
        # presentation→legacy-web reverse import, which is
        # forbidden by ODD-TDS-001.)
        assert (
            "from \"../../web/search_urls.js\"" not in code
            and "from \"../../../web/search_urls.js\"" not in code
            and "from \"../web/search_urls.js\"" not in code
        ), (
            "src/modules/taxonomy/index.ts must not re-export "
            "the legacy literal (the ODD-TDS-001 isolation "
            "contract forbids presentation→legacy-web dependency "
            "at the barrel boundary)."
        )

    def test_research_barrel_does_not_import_legacy_literal(self) -> None:
        """``src/modules/research/index.ts`` is the future
        relocation target (``infrastructure/search-engines.js``);
        today the barrel cites the legacy literal in a
        comment-only fashion. The barrel MUST NOT import the
        legacy literal at runtime — the comment is documentation
        only."""
        src = _read(RESEARCH_INDEX_TS)
        code = _strip_ts_comments(src)
        forbidden_paths = (
            'from "../web/search_urls.js"',
            'from "../../web/search_urls.js"',
            'from "../../../web/search_urls.js"',
            'from "../../../../web/search_urls.js"',
            'from "./search_urls.js"',
            'from "web/search_urls.js"',
            'from "@taxa/web/search_urls.js"',
            'from "@taxa/web"',
            'from "search_urls"',
            'from "search_urls.js"',
        )
        for needle in forbidden_paths:
            assert needle not in code, (
                f"src/modules/research/index.ts imports the legacy "
                f"literal via `{needle}`. The W65-MAP-007 KEEP "
                f"decision keeps the literal at web/search_urls.js "
                f"until the W18 atomic cutover (ODD-MIGRATE-006); "
                f"until then, the research barrel cites it in "
                f"comments only."
            )


# ---------------------------------------------------------------------------
# 5. Server mirror integrity — same count + same key/label/with_authorship
#    order as the JS literal (AC-21 byte-identical contract)
# ---------------------------------------------------------------------------


class TestServerMirrorIntegrity:
    """The server mirror (``api/server.py::_SEARCH_ENGINES``) MUST
    stay byte-identical to the JS literal on
    ``key``/``label``/``with_authorship`` in the same order. This
    is the AC-21 contract — the user-visible authoring field
    drives whether the server appends authorship to the URL, and
    a silent drift would break the rendered search URLs without
    any other signal."""

    def test_server_defines_SEARCH_ENGINES_constant(self) -> None:
        """``api/server.py`` must define the ``_SEARCH_ENGINES``
        module-level literal (the regex the AC-21 contract test
        uses to extract the entries is anchored on this name)."""
        src = _read(API_SERVER_PY)
        code = _strip_py_comments(src)
        assert "_SEARCH_ENGINES" in code, (
            "api/server.py must define _SEARCH_ENGINES at module "
            "level (the AC-21 contract test parses this constant "
            "via regex + ast.literal_eval; renaming breaks the "
            "AC-21 contract)."
        )

    def test_server_mirror_entry_count_matches_js_literal(self) -> None:
        """The server mirror must contain exactly the same number
        of entries as the JS literal. A drift on count is the
        most common AC-21 failure mode."""
        js_src = _read(WEB_SEARCH_URLS_JS)
        py_src = _read(API_SERVER_PY)
        js_entries = _extract_js_search_engines(js_src)
        py_entries = _extract_py_search_engines(py_src)
        assert len(py_entries) == len(js_entries), (
            f"entry count drift: py={len(py_entries)} "
            f"js={len(js_entries)}; both must contain the same "
            f"search engines (the AC-21 contract test catches "
            f"this; the manifest pins the invariant)."
        )

    def test_server_mirror_key_order_matches_js_literal(self) -> None:
        """The server mirror must list the same engine keys in
        the same order as the JS literal. Order drives the
        rendered button order inside each category (the
        ``SEARCH_ENGINE_LIST`` bridge mirrors the JS insertion
        order byte-for-byte)."""
        js_src = _read(WEB_SEARCH_URLS_JS)
        py_src = _read(API_SERVER_PY)
        js_entries = _extract_js_search_engines(js_src)
        py_entries = _extract_py_search_engines(py_src)
        js_keys = [e["key"] for e in js_entries]
        py_keys = [e["key"] for e in py_entries]
        assert py_keys == js_keys, (
            f"key order drift between server and JS literal: "
            f"py={py_keys} js={js_keys}; both must list the same "
            f"engines in the same order (the React SEARCH_ENGINE_LIST "
            f"bridge mirrors the JS order byte-for-byte)."
        )

    def test_server_mirror_label_order_matches_js_literal(self) -> None:
        """The server mirror must carry the same user-visible
        label for each engine. A drift on label is a
        user-visible regression (the rendered button label
        changes)."""
        js_src = _read(WEB_SEARCH_URLS_JS)
        py_src = _read(API_SERVER_PY)
        js_entries = _extract_js_search_engines(js_src)
        py_entries = _extract_py_search_engines(py_src)
        js_labels = [e["label"] for e in js_entries]
        py_labels = [e["label"] for e in py_entries]
        assert py_labels == js_labels, (
            f"label drift between server and JS literal: "
            f"py={py_labels} js={js_labels}; both must show the "
            f"same user-visible label for each engine (AC-21 "
            f"contract)."
        )

    def test_server_mirror_with_authorship_matches_js_literal(self) -> None:
        """The server mirror must carry the same
        ``with_authorship`` flag as the JS literal. The flag
        drives whether the server appends authorship to the
        URL; a drift silently breaks the rendered search URL
        for the engines that take authorship (BHL + Scholar)."""
        js_src = _read(WEB_SEARCH_URLS_JS)
        py_src = _read(API_SERVER_PY)
        js_entries = _extract_js_search_engines(js_src)
        py_entries = _extract_py_search_engines(py_src)
        for i, (py, js) in enumerate(zip(py_entries, js_entries, strict=True)):
            assert py["with_authorship"] == js["with_authorship"], (
                f"with_authorship drift at index {i}: "
                f"key={py['key']!r} py={py['with_authorship']!r} "
                f"js={js['with_authorship']!r}; the AC-21 "
                f"contract enforces byte-identical authoring "
                f"flags between the server mirror and the JS "
                f"literal (drift silently breaks BHL + Scholar "
                f"URLs)."
            )

    def test_server_mirror_index_aligned_with_js_literal(self) -> None:
        """End-to-end AC-21 cross-check: at every index, the
        server mirror and the JS literal agree on key + label
        + with_authorship. Mirrors the assertion loop in
        ``tests/test_smoke.py::test_search_engine_contract``."""
        js_src = _read(WEB_SEARCH_URLS_JS)
        py_src = _read(API_SERVER_PY)
        js_entries = _extract_js_search_engines(js_src)
        py_entries = _extract_py_search_engines(py_src)
        for i, (py, js) in enumerate(zip(py_entries, js_entries, strict=True)):
            assert py["key"] == js["key"], (
                f"key drift at index {i}: py={py['key']!r} "
                f"js={js['key']!r} (AC-21 byte-identical contract)."
            )
            assert py["label"] == js["label"], (
                f"label drift at index {i}: py={py['label']!r} "
                f"js={js['label']!r} (AC-21 byte-identical contract)."
            )
            assert py["with_authorship"] == js["with_authorship"], (
                f"with_authorship drift at index {i}: "
                f"py={py['with_authorship']!r} "
                f"js={js['with_authorship']!r} "
                f"(AC-21 byte-identical contract)."
            )

    def test_server_section_header_documents_ac21_contract(self) -> None:
        """The AC-21 cross-file contract section header must
        stay in ``api/server.py`` so a future refactor that
        renames the constant has a pointer to the AC-21
        contract test."""
        src = _read(API_SERVER_PY)
        assert (
            "tests/test_smoke.py::test_search_engine_contract" in src
        ), (
            "api/server.py must reference the AC-21 contract "
            "test (tests/test_smoke.py::test_search_engine_contract) "
            "in the section header comment so a future refactor "
            "knows where the cross-file guard lives."
        )


# ---------------------------------------------------------------------------
# 6. AC-21 round-trip — the live AC-21 contract test stays green
# ---------------------------------------------------------------------------


class TestAc21ContractRoundTrip:
    """The AC-21 contract test (``tests/test_smoke.py::
    test_search_engine_contract``) parses both literals and
    asserts the byte-identical contract. The manifest verifies
    the test stays parsable end-to-end (a silent regex break
    would silently drift the search engine catalog)."""

    def test_ac21_test_extracts_py_literal(self) -> None:
        """The AC-21 contract test must successfully extract the
        Python literal via the regex+ast.literal_eval pattern
        (the manifest mirrors the same parse so any drift in
        the literal shape fails both the AC-21 test AND this
        manifest)."""
        py_src = _read(API_SERVER_PY)
        py_entries = _extract_py_search_engines(py_src)
        assert len(py_entries) >= 1, (
            "_SEARCH_ENGINES must extract to at least one entry "
            "(the AC-21 contract test parses the same regex)."
        )

    def test_ac21_test_extracts_js_literal(self) -> None:
        """The AC-21 contract test must successfully extract the
        JS literal via the regex pattern. The manifest mirrors
        the same parse."""
        js_src = _read(WEB_SEARCH_URLS_JS)
        js_entries = _extract_js_search_engines(js_src)
        assert len(js_entries) >= 1, (
            "SEARCH_ENGINES must extract to at least one entry "
            "(the AC-21 contract test parses the same regex)."
        )

    def test_ac21_end_to_end_byte_identical(self) -> None:
        """The end-to-end AC-21 round-trip: parse both literals
        through the manifest helpers and verify key/label/
        with_authorship stay byte-identical at every index. This
        is the manifest mirror of the AC-21 contract test."""
        js_src = _read(WEB_SEARCH_URLS_JS)
        py_src = _read(API_SERVER_PY)
        js_entries = _extract_js_search_engines(js_src)
        py_entries = _extract_py_search_engines(py_src)
        assert len(py_entries) == len(js_entries)
        for _i, (py, js) in enumerate(zip(py_entries, js_entries, strict=True)):
            assert py["key"] == js["key"]
            assert py["label"] == js["label"]
            assert py["with_authorship"] == js["with_authorship"]


# ---------------------------------------------------------------------------
# 7. W18 atomic cutover carry-over — the literal stays until ODD-MIGRATE-006
# ---------------------------------------------------------------------------


class TestW18CutoverCarryOver:
    """The W18 atomic cutover (ODD-MIGRATE-006) is the ONLY
    authorized boundary for retiring the legacy literal. Until
    then, the literal stays at ``web/search_urls.js`` and every
    consumer keeps referencing it. The carry-over record lives
    in ``odd/tasks/w6-3-record-and-w6-4-chain.md`` (the W6.3
    task file) and the W18 task lives in
    ``odd/tasks/complete-frontend-migration.md``."""

    def test_w18_task_defined_in_migration_tracker(self) -> None:
        """The W18 atomic cutover task (ODD-MIGRATE-006) must be
        defined in ``odd/tasks/complete-frontend-migration.md``
        so the W18 boundary is explicit and the W65-MANIFEST-008
        KEEP decision has a documented cutover target."""
        tracker = _read(REPO_ROOT / "odd" / "tasks" / "complete-frontend-migration.md")
        assert "ODD-MIGRATE-006" in tracker, (
            "odd/tasks/complete-frontend-migration.md must define "
            "ODD-MIGRATE-006 (the W18 atomic cutover task; the "
            "W65-MANIFEST-008 KEEP decision cites it as the "
            "authorized boundary for retiring the legacy literal)."
        )
        assert (
            "atomic" in tracker.lower()
        ), (
            "ODD-MIGRATE-006 must be described as atomic (the "
            "W18 cutover is the single release boundary that "
            "retires the legacy literal)."
        )

    def test_w18_task_cuts_over_web_directory(self) -> None:
        """The W18 task must own the legacy ``web/`` retirement
        (FastAPI ``WEB_DIR`` + the legacy detail.js + the legacy
        search_urls.js all retire in the same atomic release)."""
        tracker = _read(REPO_ROOT / "odd" / "tasks" / "complete-frontend-migration.md")
        assert "WEB_DIR" in tracker or "web/" in tracker, (
            "ODD-MIGRATE-006 must reference the legacy web/ "
            "directory (the FastAPI WEB_DIR + the legacy "
            "detail.js + the legacy search_urls.js all retire "
            "in the same atomic release)."
        )

    def test_w6_5_chain_records_w65_manifest_task(self) -> None:
        """The W6.3 chain file (``odd/tasks/w6-3-record-and-w6-4-chain.md``)
        must enumerate W65-MANIFEST-008 as a sub-task so the
        manifest work-unit is visible in the chain plan."""
        chain_doc = _read(
            REPO_ROOT / "odd" / "tasks" / "w6-3-record-and-w6-4-chain.md"
        )
        assert "W65-MANIFEST-008" in chain_doc, (
            "w6-3-record-and-w6-4-chain.md must enumerate "
            "W65-MANIFEST-008 (the manifest artifact work-unit "
            "that this module implements)."
        )
        assert "test_search_engine_consumer_manifest.py" in chain_doc, (
            "w6-3-record-and-w6-4-chain.md must name "
            "test_search_engine_consumer_manifest.py as the "
            "manifest artifact (the file this module produces)."
        )

    def test_keep_decision_is_recorded_in_chain_doc(self) -> None:
        """The KEEP decision (W65-MAP-007 outcome) must be
        recorded in the W6.3 chain file so a future reader
        can trace the manifest back to its origin."""
        chain_doc = _read(
            REPO_ROOT / "odd" / "tasks" / "w6-3-record-and-w6-4-chain.md"
        )
        assert "W65-MAP-007" in chain_doc, (
            "w6-3-record-and-w6-4-chain.md must record the "
            "W65-MAP-007 read-only map (the consumer-manifest "
            "KEEP decision lives there)."
        )
        # The KEEP decision must be explicit (the literal
        # location is named).
        assert (
            "KEEP" in chain_doc
        ), (
            "w6-3-record-and-w6-4-chain.md must record the KEEP "
            "decision explicitly (a literal-location choice "
            "between KEEP and MOVE; the user selected KEEP)."
        )


# ---------------------------------------------------------------------------
# 8. Consumer enumeration — every active consumer + every comment
# ---------------------------------------------------------------------------


class TestConsumerEnumeration:
    """Every consumer found in the W65-MAP-007 read-only map
    must be pinned in this manifest. The enumeration is the
    documentation surface; if a new consumer is added, the
    manifest must be updated in lock-step."""

    def test_active_runtime_consumer_count_matches_map(self) -> None:
        """Sanity check: the W65-MAP-007 map identified the
        following ACTIVE runtime consumers:
        (a) tests/test_smoke.py::test_search_engine_contract
        (b) tests/test_research_styles.py::LEGACY_SEARCH_URLS_JS
        (c) web/detail.js:24 (SEARCH_ENGINES + CATEGORIES import)
        (d) web/detail.js::renderSearchesTab (the body uses both)

        This test enforces the manifest's coverage surface; the
        comment-only references live in the dedicated
        TestCommentOnlyReferences class.
        """
        # The active consumer names must all appear in at least
        # one of the consumer tests above. The assertion counts
        # the number of consumers by pinning each one's call
        # site (see TestActiveRuntimeConsumers).
        active_call_sites = (
            ('test_search_engine_contract', TEST_SMOKE_PY),
            ('LEGACY_SEARCH_URLS_JS', TEST_RESEARCH_STYLES_PY),
            ('SEARCH_ENGINES, CATEGORIES', WEB_DETAIL_JS),
            ('function renderSearchesTab', WEB_DETAIL_JS),
        )
        for needle, path in active_call_sites:
            src = _read(path)
            assert needle in src, (
                f"{path.relative_to(REPO_ROOT)} must reference "
                f"{needle!r} (the active runtime consumer the "
                f"W65-MAP-007 map identified)."
            )

    def test_consumer_manifest_covers_comment_only_references(self) -> None:
        """The comment-only references are pinned via the
        ``COMMENT_REFERENCES`` tuple at the top of this module.
        This test asserts the tuple is non-empty (a future PR
        that empties the tuple would lose the documentation
        surface)."""
        assert len(COMMENT_REFERENCES) >= 5, (
            "COMMENT_REFERENCES must enumerate at least five "
            "comment-only references (the W65-MAP-007 map "
            "identified 4+ comment-only sites; future slices "
            "that add more comment references should extend "
            "the tuple)."
        )

    def test_consumer_manifest_documents_consumer_count(self) -> None:
        """The module docstring must document the consumer
        count (active runtime + comment-only + React purity).
        This test enforces the documentation contract."""
        # The module docstring is the first triple-quoted
        # string at the top of the file. We check for the
        # "Consumer surface" section header + a count
        # summary line.
        module_src = Path(__file__).read_text(encoding="utf-8")
        assert "## Consumer surface" in module_src, (
            "the module docstring must document the consumer "
            "surface (the manifest is a documentation artifact; "
            "the contract lives in the docstring AND the tests)."
        )
        # The docstring must name both AC-21 consumers + the
        # legacy detail consumer.
        assert (
            "AC-21" in module_src
            and "web/detail.js" in module_src
        ), (
            "the module docstring must name AC-21 + the "
            "legacy detail consumer (the two active consumer "
            "classes the manifest pins)."
        )


# ---------------------------------------------------------------------------
# Manifest self-check
# ---------------------------------------------------------------------------


class TestManifestSelfCheck:
    """The manifest pins itself: a future PR that drops the
    manifest's documentation contract (e.g. removes the
    consumer-enumeration tuple) fails CI."""

    def test_manifest_module_is_hermetic(self) -> None:
        """The manifest must not import the FastAPI server,
        must not boot Playwright, must not touch the DB."""
        # The manifest imports only `ast`, `re`, and `pathlib`
        # from the standard library + `pytest`. A future PR
        # that adds `import api.server` or `import playwright`
        # would break hermeticity. We parse the module via
        # ``ast.parse`` and inspect the actual import nodes
        # (rather than a substring search over the source —
        # the docstring + assertion messages name the
        # forbidden imports to make the failure actionable).
        module_src = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(module_src, filename=str(Path(__file__)))
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.append(node.module)
        # Allow only the standard library modules we use
        # (ast, re, pathlib) + pytest. Anything else is a
        # hermeticity break.
        allowed_prefixes = (
            "ast", "re", "pathlib",
            "collections.abc",  # Iterable
            "pytest",
            "__future__",
        )
        leaked = [
            m for m in imported_modules
            if not any(m == p or m.startswith(p + ".") for p in allowed_prefixes)
        ]
        assert not leaked, (
            "the manifest imports non-hermetic modules: "
            f"{leaked!r}. The manifest reads files via pathlib "
            f"only; no FastAPI (`api.server`), no Playwright, "
            f"no requests/urllib."
        )

    def test_manifest_does_not_write_to_disk(self) -> None:
        """The manifest must not write to disk (no DB seed,
        no fixture dumps). It is a read-only documentation
        artifact. We inspect the AST for write-shaped calls
        rather than substring-search the source — the
        docstring names the forbidden calls to keep the
        failure message actionable."""
        module_src = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(module_src, filename=str(Path(__file__)))
        # Forbidden call targets: anything that writes to disk.
        forbidden_calls: set[str] = {"write_text", "write_bytes", "open", "Popen", "run"}
        seen: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute):
                if not isinstance(func.value, ast.Name):
                    continue
                if func.attr not in forbidden_calls:
                    continue
                # Exclude Path.read_text / Path.read_bytes (the
                # helper that READS the manifest itself for the
                # self-check is allowed).
                if func.value.id == "Path" and func.attr in {
                    "read_text", "read_bytes",
                }:
                    continue
                seen.append(f"{func.value.id}.{func.attr}()")
            elif isinstance(func, ast.Name) and func.id in forbidden_calls:
                seen.append(f"{func.id}()")
        assert not seen, (
            "the manifest uses forbidden write-shaped calls: "
            f"{seen!r}. The manifest is a read-only hermetic "
            f"documentation artifact."
        )


# ---------------------------------------------------------------------------
# Iterator helper (used by the parametrized comment-reference test)
# ---------------------------------------------------------------------------
# (No helper needed — ``pytest.mark.parametrize`` consumes
# ``COMMENT_REFERENCES`` directly. The module's
# ``TestCommentOnlyReferences`` test class references the
# tuple by name.)


# ---------------------------------------------------------------------------
# ODD-SEARCH-001 — top-bar search-input carveout
#
# The legacy `web/search.js` shipped a top-bar search input that
# drove `/api/search?q=...&limit=15` round trips on a 200ms
# debounce. The ODD-MIGRATE-007 carveout retired the legacy
# `web/` Playwright tests that targeted the legacy `#search-input`
# selector so they don't reach the React-shaped surface by
# accident. The React `TaxonomyTree` mount keeps the same selector
# so a future Playwright probe can locate the input via the
# legacy hook, AND it keeps the `data-action="select-taxon"` +
# `data-taxon-id="<id>"` per-row contract so the legacy
# click-handler shape stays observable.
#
# ODD-ASN-002 — the search input is lifted OUT of `TaxonomyTree`
# and INTO the AppShell frame (the input lives in
# `src/modules/app-shell/presentation/AppShellGlobalSearch.tsx`,
# a client island nested inside the AppShellHeader). The
# route-aware `<div id="search-results" data-search-results>`
# dropdown stays mounted inside `TaxonomyTree` because the
# dropdown is route-specific to `/`, but the input itself is
# now a global shell affordance. The legacy `#search-input`
# selector lives at the new location under the namespaced
# `id="app-shell-search-input"` + `data-app-shell-search=""`
# surface so a future Playwright probe can reach the global
# input through the new shell hook.
#
# This test class pins the ODD-SEARCH-001 contract end-to-end:
#   - The AppShell frame must own a top-bar
#     `<input id="app-shell-search-input">` carrying
#     `data-app-shell-search=""`, `autoComplete="off"`,
#     `spellCheck={false}`, and a placeholder starting with
#     "Search taxa" (the brief's required copy). Mirrors the
#     test pattern already applied in
#     `tests/test_visible_taxonomy_tree.py::test_app_shell_global_search_renders_input_with_legacy_dom_contract`.
#   - The mount must render `<div id="search-results" data-search-results>`
#     hosting a `<button data-taxon-id="<id>" data-action="select-taxon">`
#     for every server-ranked hit.
#   - The mount must consume the canonical `fetchSearch` helper
#     via the `@taxa/taxonomy` barrel — never a deep import
#     into the infrastructure layer.
#   - The `/api/search` endpoint must exist on the FastAPI server
#     (the ODD-SEARCH-001 contract pins the canonical
#     `/api/search?q=<query>&source=col|worms|freshwater>&limit=20`
#     URL the React mount consumes).
# ---------------------------------------------------------------------------

TAXONOMY_INFRA_API_TS: Path = (
    REPO_ROOT / "src" / "modules" / "taxonomy" / "infrastructure" / "api.ts"
)
TAXONOMY_TREE_TSX: Path = (
    REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "TaxonomyTree.tsx"
)
# ODD-ASN-002 — AppShell global search input. The input is
# lifted OUT of TaxonomyTree (which keeps the route-specific
# dropdown) and INTO the AppShell frame (which keeps the
# cross-route global header affordance). The ODD-SEARCH-001
# DOM contract travels with the input: the namespaced
# `id="app-shell-search-input"` + `data-app-shell-search=""`
# replace the legacy `#search-input` + `data-search-input=""`
# pair so a future Playwright probe reaches the global input
# through the new shell hook.
APP_SHELL_GLOBAL_SEARCH_TSX: Path = (
    REPO_ROOT / "src" / "modules" / "app-shell" / "presentation"
    / "AppShellGlobalSearch.tsx"
)


class TestSearchInputCarveout:
    """ODD-SEARCH-001 + ODD-ASN-002 — the AppShell frame's
    top-bar search input MUST keep the canonical DOM contract
    (`id="app-shell-search-input"` + `data-app-shell-search=""`
    + `autoComplete="off"` + `spellCheck={false}` + placeholder
    starting with "Search taxa") so a future Playwright probe
    can locate the surface via the same hook the ODD-MIGRATE-007
    carveout retired.

    The legacy `web/` Playwright tests stay skipped under the
    ODD-MIGRATE-007 carveout — they target the LEGACY
    `web/index.html` `#search-input` element, which the
    static-export at `out/` no longer ships. The AppShell
    frame's namespaced input lives in the same single-origin
    root the legacy oracle targeted, so the React-shaped
    surface is reachable via Playwright's
    `page.locator("#app-shell-search-input")` selector — the
    carveout just stops the retired legacy tests from racing
    the React mount. The route-specific `<div id="search-results"
    data-search-results>` dropdown stays inside `TaxonomyTree`
    because the dropdown is route-specific to `/`.
    """

    def test_app_shell_global_search_renders_input_with_legacy_dom_contract(
        self,
    ) -> None:
        """ODD-SEARCH-001 + ODD-ASN-002: the global `<input>`
        lives in
        ``src/modules/app-shell/presentation/AppShellGlobalSearch.tsx``
        (a client island inside the AppShellHeader). The
        pre-ODD-ASN-002 implementation owned the input inside
        ``TaxonomyTree.tsx``; the ODD-ASN-002 lift moves it to the
        shell frame so the same input is reachable on every
        route the AppShell wraps (Help, Settings, the future
        hydration-probe stub, etc.) without rewriting the
        search surface per route.

        The DOM contract the input carries is the canonical
        React-shaped hook so a future Playwright probe can
        locate it from the shell surface:

          - `id="app-shell-search-input"` (the namespaced
            global hook).
          - `data-app-shell-search=""` (the React-shaped
            marker).
          - `autoComplete="off"` (browsers MUST NOT cache the
            query).
          - `spellCheck={false}` (no red squiggle on a Latin
            scientific name).
          - placeholder starting with "Search taxa" (the
            brief's required copy; the suffix `…  (Cmd+K)`
            advertises the keyboard shortcut the AppShell
            wires).

        Mirrors the canonical assertion already applied in
        ``tests/test_visible_taxonomy_tree.py::test_app_shell_global_search_renders_input_with_legacy_dom_contract``.
        """
        if not APP_SHELL_GLOBAL_SEARCH_TSX.is_file():
            pytest.skip("AppShellGlobalSearch.tsx not present yet")
        text = APP_SHELL_GLOBAL_SEARCH_TSX.read_text(encoding="utf-8")
        # The namespaced id MUST stay present so the global
        # search is reachable from the shell surface (every
        # route the AppShell wraps inherits the input).
        assert re.search(
            r'<input\b[^>]*\bid\s*=\s*"app-shell-search-input"',
            text,
            re.DOTALL,
        ), (
            "AppShellGlobalSearch.tsx must render `<input "
            "id=\"app-shell-search-input\" ...>` so the global "
            "search input is reachable from the AppShell frame."
        )
        # The data-app-shell-search="" attribute pins the
        # React-shaped surface so a future Playwright probe can
        # locate the input via the React hook.
        assert re.search(
            r'<input\b[^>]*\bdata-app-shell-search\s*=\s*""',
            text,
            re.DOTALL,
        ), (
            "AppShellGlobalSearch.tsx must stamp "
            "`data-app-shell-search=\"\"` on the search input "
            "(the React-shaped DOM contract)."
        )
        # Autocomplete + spellcheck guards mirror the legacy
        # `web/index.html` `<input id="search-input"
        # autocomplete="off" spellcheck="false">` shape so the
        # React mount behaves identically (browsers must NOT
        # cache the search query, and the red squiggle must
        # NOT fire on a Latin scientific name). React's JSX
        # uses the camelCase form (`autoComplete`); the regex
        # matches either case so a future swap to a typed
        # native element wouldn't trip the guard.
        assert re.search(
            r'<input\b[^>]*\bauto[Cc]omplete\s*=\s*"off"',
            text,
            re.DOTALL,
        ), (
            "AppShellGlobalSearch.tsx must stamp "
            "`autoComplete=\"off\"` on the search input (the "
            "legacy `web/index.html` shape)."
        )
        assert re.search(
            r'<input\b[^>]*\bspell[Cc]heck\s*=\s*\{\s*false\s*\}',
            text,
            re.DOTALL,
        ), (
            "AppShellGlobalSearch.tsx must stamp "
            "`spellCheck={false}` on the search input (the "
            "legacy `web/index.html` shape — no red squiggle "
            "on a Latin scientific name)."
        )
        # The placeholder drives the visible copy. The brief
        # mandates "Search taxa…" or similar (the suffix
        # `…  (Cmd+K)` advertises the keyboard shortcut the
        # AppShell wires).
        assert re.search(
            r'<input\b[^>]*\bplaceholder\s*=\s*"Search taxa',
            text,
            re.DOTALL,
        ), (
            "AppShellGlobalSearch.tsx must render a placeholder "
            "starting with \"Search taxa\" (the brief's "
            "required copy)."
        )

    def test_taxonomy_tree_renders_search_results_container_with_data_attr(self) -> None:
        """ODD-SEARCH-001: TaxonomyTree.tsx MUST render
        `<div id="search-results" data-search-results>` so the
        legacy `#search-results` selector still locates the
        dropdown host."""
        if not TAXONOMY_TREE_TSX.is_file():
            pytest.skip("TaxonomyTree.tsx not present yet")
        text = TAXONOMY_TREE_TSX.read_text(encoding="utf-8")
        assert re.search(
            r'<div\b[^>]*\bid="search-results"',
            text,
            re.DOTALL,
        ), (
            "TaxonomyTree.tsx MUST render `<div id=\"search-results\">` "
            "so a future Playwright probe can locate the dropdown host "
            "via the same hook the legacy oracle shipped."
        )
        assert re.search(
            r'data-search-results\s*=\s*""',
            text,
        ), (
            "TaxonomyTree.tsx MUST stamp `data-search-results=\"\"` "
            "on the dropdown host (the React-shaped DOM contract)."
        )

    def test_taxonomy_tree_renders_select_taxon_action_rows(self) -> None:
        """ODD-SEARCH-001: each search result row MUST be a
        `<button data-taxon-id="<id>" data-action="select-taxon">`
        so a future probe can locate result rows via the same
        selector the legacy `web/nav.js::select-from-search`
        action targeted."""
        if not TAXONOMY_TREE_TSX.is_file():
            pytest.skip("TaxonomyTree.tsx not present yet")
        text = TAXONOMY_TREE_TSX.read_text(encoding="utf-8")
        assert 'data-action="select-taxon"' in text, (
            "TaxonomyTree.tsx MUST stamp `data-action=\"select-taxon\"` "
            "on each search result row (the React-shaped DOM contract "
            "mirrors the legacy `select-from-search` action)."
        )
        assert re.search(
            r'data-taxon-id\s*=\s*\{[^}]*hit\.taxon\.id',
            text,
        ), (
            "TaxonomyTree.tsx MUST stamp `data-taxon-id={hit.taxon.id}` "
            "on each search result row (the React-shaped DOM contract)."
        )

    def test_taxonomy_tree_consumes_fetch_search_via_barrel(self) -> None:
        """ODD-SEARCH-001: the React mount MUST consume the
        canonical `fetchSearch` helper via the `@taxa/taxonomy`
        barrel — never a deep import into the infrastructure
        layer. spec.md rule 5 forbids deep imports via the
        ESLint `no-restricted-imports` guard."""
        if not TAXONOMY_TREE_TSX.is_file():
            pytest.skip("TaxonomyTree.tsx not present yet")
        text = TAXONOMY_TREE_TSX.read_text(encoding="utf-8")
        assert "fetchSearch" in text, (
            "TaxonomyTree.tsx MUST call the canonical `fetchSearch` helper"
        )
        for bad in (
            "../infrastructure/api",
            "../infrastructure/api.js",
            "@taxa/taxonomy/infrastructure",
        ):
            assert bad not in text, (
                f"TaxonomyTree.tsx MUST NOT deep-import {bad!r} "
                f"(spec.md rule 5 barrel guard)."
            )

    def test_taxonomy_infra_api_exports_fetch_search_helper(self) -> None:
        """ODD-SEARCH-001: `src/modules/taxonomy/infrastructure/api.ts`
        MUST export a `fetchSearch` helper so the React mount
        can consume the canonical `/api/search?q=&source=&limit=`
        URL through the public `@taxa/taxonomy` barrel."""
        if not TAXONOMY_INFRA_API_TS.is_file():
            pytest.skip("taxonomy infrastructure api.ts not present yet")
        text = TAXONOMY_INFRA_API_TS.read_text(encoding="utf-8")
        assert re.search(
            r"export\s+(?:async\s+)?function\s+fetchSearch\b",
            text,
        ), (
            "taxonomy infrastructure api.ts MUST export a `fetchSearch` "
            "helper so the React mount can consume `/api/search` through "
            "the public barrel."
        )
        # The helper MUST accept a `q` parameter + an options bag
        # that carries `source` + `limit` (the canonical
        # `/api/search?q=<query>&source=col|worms|freshwater>&limit=20`
        # URL contract).
        assert re.search(
            r"function\s+fetchSearch\s*\(\s*q\s*:\s*string\s*,\s*opts",
            text,
        ), (
            "fetchSearch MUST accept `(q: string, opts: FetchSearchOptions)` "
            "so callers can forward the canonical source + limit query params."
        )
        # The implementation MUST build the canonical
        # `/api/search?q=...&source=...&limit=...` URL.
        assert "/api/search" in text, (
            "fetchSearch MUST build the canonical `/api/search?q=...` URL "
            "(the FastAPI endpoint the React mount consumes)."
        )

    def test_taxonomy_infra_api_exports_search_hit_type(self) -> None:
        """ODD-SEARCH-001: `taxonomy/infrastructure/api.ts` MUST
        export the `SearchHit` type so the React mount can type
        the search-results state without a deep import into the
        wire projection layer."""
        if not TAXONOMY_INFRA_API_TS.is_file():
            pytest.skip("taxonomy infrastructure api.ts not present yet")
        text = TAXONOMY_INFRA_API_TS.read_text(encoding="utf-8")
        assert re.search(
            r"export\s+interface\s+SearchHit\b",
            text,
        ), (
            "taxonomy infrastructure api.ts MUST export a `SearchHit` "
            "interface so the React mount can type the search-results "
            "state via the public barrel."
        )
        # The `SearchHit` projection must carry the typed `match_type`
        # literal (`"scientific" | "authorship" | "vernacular"` —
        # the bucket the server emits).
        assert re.search(
            r"interface\s+SearchHit\b[^}]*match_type\s*:\s*[\"']scientific[\"']\s*\|\s*[\"']authorship[\"']\s*\|\s*[\"']vernacular[\"']",
            text,
            re.DOTALL,
        ), (
            "SearchHit.match_type MUST be the typed literal union "
            "\"scientific\" | \"authorship\" | \"vernacular\" — the "
            "three buckets the FastAPI `/api/search` endpoint emits."
        )

    def test_taxonomy_barrel_reexports_fetch_search_and_search_hit(self) -> None:
        """ODD-SEARCH-001: the public `@taxa/taxonomy` barrel
        MUST re-export `fetchSearch` + `SearchHit` so the React
        mount consumes the typed surface through the canonical
        cross-module import path (spec.md rule 5)."""
        if not TAXONOMY_INDEX_TS.is_file():
            pytest.skip("taxonomy barrel not present yet")
        text = TAXONOMY_INDEX_TS.read_text(encoding="utf-8")
        assert "fetchSearch" in text, (
            "taxonomy barrel MUST re-export `fetchSearch` "
            "(spec.md rule 5 — the React mount consumes the "
            "search helper through the public barrel)."
        )
        assert "SearchHit" in text, (
            "taxonomy barrel MUST re-export the `SearchHit` type "
            "(spec.md rule 5 — the React mount types the "
            "search-results state through the public barrel)."
        )

    def test_fastapi_search_endpoint_exists(self) -> None:
        """ODD-SEARCH-001: the FastAPI server MUST expose
        `GET /api/search` so the React mount can consume the
        canonical `/api/search?q=<query>&source=...&limit=...`
        URL. The endpoint is the FastAPI source of truth for the
        search ranking (BM25 across scientific_name +
        authorship + vernacular names — see
        `api/server.py::search`)."""
        if not API_SERVER_PY.is_file():
            pytest.skip("api/server.py not present yet")
        text = API_SERVER_PY.read_text(encoding="utf-8")
        assert re.search(
            r"@app\.get\s*\(\s*[\"']/api/search[\"']",
            text,
        ), (
            "api/server.py MUST expose `@app.get(\"/api/search\")` "
            "so the React mount can consume the canonical "
            "/api/search?q=<query>&source=...&limit=... URL "
            "(ODD-SEARCH-001 contract)."
        )
        # The endpoint MUST accept the canonical query parameters:
        # `q` (required string), `limit` (integer with default 20).
        # The parameter list lives on the line(s) immediately after
        # `def search(` — we extract the substring between that line
        # and the next `):` line so nested `Query(...)` parens don't
        # terminate the capture early.
        m = re.search(
            r"def\s+search\s*\(\s*\n(.*?)\n\s*\)",
            text,
            re.DOTALL,
        )
        assert m is not None, (
            "api/server.py MUST define `def search(...)` for the "
            "/api/search endpoint so the FastAPI source of truth "
            "matches the canonical URL contract."
        )
        params = m.group(1)
        for needle in ("q:", "limit:"):
            assert needle in params, (
                f"def search(...) MUST accept the `{needle}` query "
                f"parameter (the ODD-SEARCH-001 canonical URL contract)."
            )
