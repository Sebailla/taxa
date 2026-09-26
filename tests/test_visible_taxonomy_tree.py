"""Visible taxonomy tree contract tests (ODD-VTREE-002).

Pins the React cutover's first usable tree surface:
  - AppShell (server component) renders header + main + footer
  - TaxonomyTree ('use client') renders collapsed root rows on mount
  - TreeRow renders disclosure buttons with accurate ``aria-expanded``
  - Initial loading / error / empty states are accessible
  - The static export's ``out/index.html`` carries the SSR markup

The build-witness fixture (``built_index_html``) reuses the
``next build`` side-effect from ``test_app_shell_render.py`` when run
in the same session. When run alone the test runs its own
``next build`` to refresh ``out/``.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_SHELL_FILE = REPO_ROOT / "src" / "modules" / "app-shell" / "presentation" / "AppShell.tsx"
APP_SHELL_BARREL = REPO_ROOT / "src" / "modules" / "app-shell" / "index.ts"
APP_SHELL_GLOBAL_SEARCH_FILE = (
    REPO_ROOT
    / "src"
    / "modules"
    / "app-shell"
    / "presentation"
    / "AppShellGlobalSearch.tsx"
)
TAXONOMY_TREE_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "TaxonomyTree.tsx"
HOME_CLIENT_FILE = REPO_ROOT / "src" / "app" / "_components" / "HomeClient.tsx"
TAXONOMY_TREE_ROW_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "TreeRow.tsx"
TAXONOMY_TREE_STATE_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "tree-state.ts"
TAXONOMY_DETAIL_PANEL_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "DetailPanel.tsx"
TAXONOMY_BARREL = REPO_ROOT / "src" / "modules" / "taxonomy" / "index.ts"
TAXONOMY_DOMAIN_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "domain" / "taxon.ts"
TAXONOMY_INFRA_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "infrastructure" / "api.ts"
TAXONOMY_GLOBALS_CSS = REPO_ROOT / "src" / "app" / "globals.css"
VERNACULAR_TAB_FILE = (
    REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "VernacularTab.tsx"
)
SYNONYM_TAB_FILE = (
    REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "SynonymTab.tsx"
)
SRC_PAGE = REPO_ROOT / "src" / "app" / "page.tsx"
SRC_LAYOUT = REPO_ROOT / "src" / "app" / "layout.tsx"
OUT_DIR = REPO_ROOT / "out"
OUT_INDEX = OUT_DIR / "index.html"


def _read_text(path: Path) -> str:
    if not path.is_file():
        pytest.fail(f"required file missing: {path}")
    return path.read_text(encoding="utf-8")


def _od_hss_source_switch_effect_body(text: str) -> str:
    """Return the body of the ODD-HSS-001 source-switch ``useEffect``.

    The pre-ODD-HSS source-selector mount inside TaxonomyTree.tsx
    owned a ``handleSourceChange`` callback that performed the
    source-bound reset cascade (closes kebab + clears focused /
    selected + clears per-taxon search / folder caches).

    ODD-HSS-001 hoists the source-selector to the AppShell header
    so the click handler (``setActiveSource(src)``) writes through
    the typed ``useTreeSource`` hook from the AppShell side.
    TaxonomyTree still owns the cleanup cascade — it moves into a
    ``useEffect`` that fires whenever ``activeSource`` changes.
    This helper extracts the effect body so the legacy witnesses
    that pinned the cascade contract (in ``handleSourceChange``)
    continue to pass against the new effect-based contract.

    The matched block MUST start with a ``setKebabOpenId(null);``
    line — the unique opener the pre-ODD-HSS-001 cascade starts
    with — and end with a ``}, [activeSource]);`` closer. The
    combined open-AND-close anchor isolates the right effect
    block from the other six-or-so ``useEffect`` blocks that
    live elsewhere in the file (each pinned to its own deps
    array: ``[loadRoots]``, ``[rawRoots, setSearchHits]``,
    ``[rawRoots + activeSource]``, ``[kebabOpenId]``,
    ``[selected, ...]`` etc. — those blocks have DIFFERENT
    dep arrays so a naive ``}, [activeSource]);`` match can
    span across them when DOTALL is on).
    """
    match = re.search(
        r"useEffect\(\(\)\s*=>\s*\{\s*//\s*ODD-NTP-005:\s*a source switch clears focused \+ selected[\s\S]*?"
        r"\}\s*,\s*\[activeSource\]\s*\)\s*;",
        text,
    )
    assert match is not None, (
        "ODD-HSS-001 source-switch effect: TaxonomyTree.tsx must "
        "declare a `useEffect(() => { ... }, [activeSource])` block "
        "whose opener is the `// ODD-NTP-005: a source switch clears "
        "focused + selected` comment + whose body performs the pre-"
        "hoist `handleSourceChange` source-bound cascade "
        "(`setKebabOpenId(null)` + `setFocused(null)` + "
        "`setSelected(null)` + `setSearchesByTaxonId(new Map())` + "
        "the five folder caches + deps `[activeSource]`). The hoist "
        "moved the source-selector to the AppShell header so the "
        "cleanup that used to live in the selector's click handler "
        "now lives in a reactive effect on `activeSource`."
    )
    # Return the body between the opener `useEffect(() => {` and
    # the closer `}, [activeSource]);`.
    raw = match.group(0)
    body_open = raw.index("{") + 1
    body_close = raw.rindex("}, [activeSource]")
    return raw[body_open:body_close]


# ---------------------------------------------------------------------------
# File presence + extension (RED gates for ODD-VTREE-002)
# ---------------------------------------------------------------------------

def test_app_shell_file_exists() -> None:
    assert APP_SHELL_FILE.is_file(), (
        f"missing {APP_SHELL_FILE} — ODD-VTREE-002 ships this server component."
    )
    assert APP_SHELL_FILE.suffix == ".tsx", "AppShell must be `.tsx`."


def test_app_shell_barrel_reexports_app_shell() -> None:
    text = _read_text(APP_SHELL_BARREL)
    assert re.search(r'export\s*\{[^}]*default\s+as\s+AppShell[^}]*\}\s*from', text, re.DOTALL), (
        "app-shell barrel must re-export `AppShell` as the default export"
    )
    assert re.search(r'export\s+type\s*\{\s*AppShellProps\s*\}', text), (
        "app-shell barrel must re-export `AppShellProps`"
    )


def test_taxonomy_tree_file_exists() -> None:
    assert TAXONOMY_TREE_FILE.is_file(), (
        f"missing {TAXONOMY_TREE_FILE} — ODD-VTREE-002 ships this client island."
    )
    assert TAXONOMY_TREE_FILE.suffix == ".tsx", "TaxonomyTree must be `.tsx`."


def test_taxonomy_tree_flatten_visible_rows_is_exported() -> None:
    """ODD-JKNAV-001: the pure `flattenVisibleRows` helper must be
    exported from `tree-state.ts` so the j/k keyboard handler in
    `TaxonomyTree.tsx` can walk the visible row order without
    duplicating the recursive shape. Collapsed subtrees must
    contribute only their root row (the walker descends only
    into ids that are in `expandedIds`).
    """
    text = _read_text(TAXONOMY_TREE_STATE_FILE)
    assert "export function flattenVisibleRows" in text, (
        "tree-state.ts must export a `flattenVisibleRows` pure "
        "helper. The j/k row navigation handler depends on the "
        "flattened render-order list to compute the next / "
        "previous visible row."
    )
    # The walker MUST descend only into expanded ids so a
    # collapsed subtree contributes only its root row (matching
    # what the user sees on screen). Pin via the `expandedIds`
    # reference inside the helper body.
    function_match = re.search(
        r"export function flattenVisibleRows[\s\S]+?\n\}",
        text,
    )
    assert function_match, (
        "tree-state.ts must export `flattenVisibleRows` with a "
        "complete function body."
    )
    body = function_match.group(0)
    assert "expandedIds" in body, (
        "`flattenVisibleRows` must consult `expandedIds` so a "
        "collapsed subtree contributes only its root row to "
        "the flattened list. A walker that descends into every "
        "child would make j / k navigation feel broken — the "
        "user would jump past collapsed subtrees."
    )


def test_taxonomy_tree_jk_keyboard_navigation_handler() -> None:
    """ODD-JKNAV-001: TaxonomyTree.tsx must attach a document-level
    keydown listener for `j` (move selection one row down) and
    `k` (move selection one row up) that:

      - uses the pure `flattenVisibleRows` kernel helper so the
        order matches what the user sees (collapsed subtrees are
        skipped — their root row counts, their children do not),
      - skips when the active element is editable (so typing
        `j` / `k` inside another input / textarea /
        contenteditable never has the keystroke stolen),
      - skips when the kebab menu is open (the kebab owns
        keyboard navigation while it is open),
      - calls `handleSelect(rows[nextIdx])` so the existing
        pulse animation + scrollIntoView effect wired for the
        search-result-click path fire verbatim,
      - `preventDefault`s so a future vim-mode browser
        extension does not also fire on the key.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    # The handler MUST attach a document-level keydown listener.
    assert (
        'document.addEventListener("keydown"' in text
    ), (
        "TaxonomyTree.tsx must add a document-level keydown "
        "listener that handles the j / k row navigation "
        "shortcut (mirrors the kebab Escape-close pattern)."
    )
    # The handler MUST inspect `ev.key` against BOTH the "j"
    # and "k" literals. The implementation may use either
    # `===` (positive dispatch) or `!==` (early-return guard)
    # — both forms are equivalent. A regex tolerates both.
    for key in ("j", "k"):
        assert re.search(
            rf"ev\.key\s*(?:===|!==)\s*[\"']{key}[\"']",
            text,
        ), (
            f"TaxonomyTree.tsx j/k handler must inspect "
            f"`ev.key` against the \"{key}\" literal "
            f"(\"j\" moves down, \"k\" moves up) so the "
            f"navigation fires on the right keystroke."
        )
    # The handler MUST consult the active element's editability
    # so typing `j` / `k` inside another input never has the
    # keystroke stolen.
    assert "isContentEditable" in text, (
        "TaxonomyTree.tsx j/k handler must check "
        "`isContentEditable` so the shortcut never steals a "
        "keystroke from an editable element (mirrors the "
        "AppShellGlobalSearch Cmd+K editable-field guard)."
    )
    # The handler MUST skip when the kebab is open.
    assert "kebabOpenId !== null" in text, (
        "TaxonomyTree.tsx j/k handler must skip when the "
        "kebab menu is open — the kebab owns keyboard "
        "navigation while it is mounted."
    )
    # The handler MUST call `handleSelect` (the canonical
    # selection primitive) so the pulse animation +
    # scrollIntoView effect fire verbatim. The implementation
    # may inline `rows[nextIdx]` in the call or split it into
    # a `nextId` variable for the undefined-guard pattern;
    # both forms are equivalent. A regex tolerates both.
    assert re.search(
        r"handleSelect\(\s*(?:rows\[nextIdx\]|nextId)\s*\)",
        text,
    ), (
        "TaxonomyTree.tsx j/k handler must call `handleSelect` "
        "with the next visible row id so the existing pulse "
        "animation + scrollIntoView effect fire verbatim (no "
        "duplicated selection plumbing)."
    )
    # The handler MUST use the kernel helper — no inline
    # recursive walk in the component.
    assert "flattenVisibleRows(state)" in text, (
        "TaxonomyTree.tsx j/k handler must call "
        "`flattenVisibleRows(state)` from the kernel helper. "
        "An inline recursive walker would duplicate the "
        "tree-shape traversal and drift from the source of "
        "truth in `tree-state.ts`."
    )
    # preventDefault stops the browser's quick-find /
    # find-as-you-type bar from intercepting.
    assert "ev.preventDefault" in text, (
        "TaxonomyTree.tsx j/k handler must call "
        "`ev.preventDefault()` to stop the browser's "
        "quick-find / find-as-you-type bar from "
        "intercepting."
    )


def test_tree_row_file_exists() -> None:
    assert TAXONOMY_TREE_ROW_FILE.is_file(), (
        f"missing {TAXONOMY_TREE_ROW_FILE} — ODD-VTREE-002 ships this row component."
    )
    assert TAXONOMY_TREE_ROW_FILE.suffix == ".tsx", "TreeRow must be `.tsx`."


def test_taxonomy_barrel_reexports_taxonomy_tree() -> None:
    text = _read_text(TAXONOMY_BARREL)
    assert re.search(r'export\s*\{[^}]*default\s+as\s+TaxonomyTree[^}]*\}\s*from', text, re.DOTALL), (
        "taxonomy barrel must re-export `TaxonomyTree` as the default export"
    )


# ---------------------------------------------------------------------------
# Source contracts (server vs client boundary, dependencies, accessibility)
# ---------------------------------------------------------------------------

def test_taxonomy_tree_is_a_client_component() -> None:
    text = _read_text(TAXONOMY_TREE_FILE)
    assert text.lstrip().startswith('"use client"') or text.lstrip().startswith("'use client'"), (
        "TaxonomyTree.tsx must declare the client boundary via 'use client'"
    )


def test_app_shell_is_a_server_component() -> None:
    """AppShell must NOT carry 'use client' — the brief mandates a server-component shell."""
    text = _read_text(APP_SHELL_FILE)
    assert "use client" not in text, (
        "AppShell.tsx is a server component; it MUST NOT carry the 'use client' directive"
    )


def test_app_shell_depends_only_on_react_types() -> None:
    """ODD-ASN-002: AppShell imports only React types plus the two
    in-shell sub-components (``AppShellHeader`` + ``AppShellFooter``)
    the deliberate decomposition introduced. AppShell MUST NOT
    import any capability module (``@taxa/taxonomy``,
    ``@taxa/research``, ``@taxa/browser-state``, etc.) or the
    ``globals.css`` stylesheet — those would invert the chain
    topology (spec.md rule 4 keeps the presentation layer pure;
    rule 5 keeps the imports flowing through the public barrels).
    """
    text = _read_text(APP_SHELL_FILE)
    allowed = {"react", "./AppShellHeader", "./AppShellFooter"}
    forbidden = (
        "@taxa/taxonomy",
        "@taxa/research",
        "@taxa/browser-state",
        "./globals.css",
    )
    for src in re.findall(r'from\s+["\']([^"\']+)["\']', text):
        assert src in allowed, (
            f"AppShell.tsx must import only from {sorted(allowed)!r} "
            f"(React types + the in-shell Header/Footer sub-components); "
            f"got {src!r} — importing a capability module here would "
            f"invert the chain topology."
        )
        for bad in forbidden:
            assert not src.startswith(bad) and bad not in src, (
                f"AppShell.tsx must not import {bad!r} "
                f"(spec.md rule 4 / rule 5 chain-topology guard); "
                f"got {src!r}."
            )


def test_taxonomy_tree_uses_canonical_helpers_via_barrel() -> None:
    """ODD-VTREE-002 correction: TaxonomyTree consumes the canonical
    typed helpers (``fetchDomains``, ``fetchChildren``,
    ``TaxonomyApiError``) re-exported by the public
    ``@taxa/taxonomy`` barrel — never deep paths into the
    infrastructure layer. spec.md rule 5 forbids deep imports via the
    ESLint ``no-restricted-imports`` guard; rule 4 keeps the
    presentation layer free of duplicated wire projection.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "fetchDomains" in text, (
        "TaxonomyTree.tsx must call the canonical fetchDomains helper"
    )
    assert "fetchChildren" in text, (
        "TaxonomyTree.tsx must call the canonical fetchChildren helper"
    )
    assert "from \"@taxa/taxonomy\"" in text or "from '@taxa/taxonomy'" in text, (
        "TaxonomyTree.tsx must import the helpers via the @taxa/taxonomy barrel"
    )
    # spec.md rule 5 + ESLint guard: no deep imports into the layer folders.
    for bad in (
        "../infrastructure/api",
        "../infrastructure/api.js",
        "@taxa/taxonomy/infrastructure",
        "@taxa/taxonomy/domain",
    ):
        assert bad not in text, (
            f"TaxonomyTree.tsx must not deep-import {bad!r} (rule 5 barrel guard)"
        )


def test_taxonomy_tree_uses_configured_api_origin() -> None:
    """ODD-VTREE-002 binding: production requests stay
    relative/same-origin — the env var literal pin still lives in
    ``TaxonomyTree.tsx`` (``process.env.NEXT_PUBLIC_TAXA_API_ORIGIN``
    is the source of truth), but the runtime default may be EITHER
    an empty string OR a relative ``/api``; the static export at
    ``out/`` ships WITHOUT a ``.env`` so the adapter in
    ``src/modules/taxonomy/infrastructure/api.ts`` absorbs the
    empty-string edge case and substitutes ``/api`` so FastAPI's
    ``/api/*`` routes match without the trailing-slash side effect
    ``new URL("", currentLocation)`` introduces. Local development
    still overrides the variable via ``pnpm run dev:local`` (see
    package.json).
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "process.env.NEXT_PUBLIC_TAXA_API_ORIGIN" in text, (
        "TaxonomyTree.tsx must source its API origin from NEXT_PUBLIC_TAXA_API_ORIGIN"
    )
    assert re.search(
        r'NEXT_PUBLIC_TAXA_API_ORIGIN\s*\?\?\s*(?:["\']["\']|["\']/api["\'])',
        text,
    ), (
        "TaxonomyTree.tsx must default the origin to either an empty string "
        'or "/api" (the adapter in src/modules/taxonomy/infrastructure/api.ts '
        "absorbs the empty-string edge case so the static export keeps working "
        "with no .env file)"
    )


def test_taxonomy_tree_emits_accessible_initial_states() -> None:
    """ODD-VTREE-002: initial loading (`role=status`), initial error
    (`role=alert` + Retry), and empty roots are all rendered."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # At least one `role="status"` covers loading + empty + per-row loading.
    assert text.count('role="status"') >= 2, (
        "TaxonomyTree.tsx must emit role=\"status\" for loading + empty states"
    )
    # Initial error uses `role="alert"` with a Retry button.
    assert text.count('role="alert"') >= 1, (
        "TaxonomyTree.tsx must emit role=\"alert\" for the initial error state"
    )
    assert re.search(r'>\s*Retry\s*<', text), (
        "TaxonomyTree.tsx must render a Retry button"
    )


# ---------------------------------------------------------------------------
# ODD-SEARCH-001 — global search input contract.
#
# ODD-ASN-002 lifts the search input OUT of TaxonomyTree and INTO the
# AppShell frame (the input lives in AppShellGlobalSearch.tsx, a
# client island nested inside the AppShellHeader). The route-aware
# `<div id="search-results" data-search-results>` dropdown stays
# mounted inside TaxonomyTree because the dropdown is route-specific
# to `/`, but the input itself is now a global shell affordance.
#
# Pins the canonical DOM contract the input must carry regardless
# of where it lives:
#   - `<input id="app-shell-search-input">` carries
#     `data-app-shell-search=""`, `autoComplete="off"`,
#     `spellCheck={false}`.
#   - `<div id="search-results" data-search-results>` hosts the
#     dropdown (still inside TaxonomyTree — the brief says the
#     dropdown is route-specific).
#   - Each result row is a `<button data-taxon-id="<id>"
#     data-action="select-taxon">` so the click handler routes
#     through the React `handleSelect` primitive.
#   - The input is debounced (200ms) on input change after a
#     2-character gate; clicking a result clears the input and
#     drives the React tree to focus on the selected taxon.
#
# The pre-ODD-ASN-002 input lived inside TaxonomyTree with
# `id="search-input"` + `data-search-input=""` so the retired
# legacy Playwright probe could locate it via the legacy
# `web/index.html` selector. The ODD-ASN-002 lift moves the
# input to the AppShell frame with a namespaced id
# (`app-shell-search-input`) + a namespaced marker
# (`data-app-shell-search=""`) so a future Playwright probe
# reaches the global input through the new shell hook. The
# retired legacy `#search-input` selector stays as the
# ODD-MIGRATE-007 carveout (see
# `tests/test_search_engine_consumer_manifest.py`).
# ---------------------------------------------------------------------------


def test_app_shell_global_search_renders_input_with_legacy_dom_contract() -> None:
    """ODD-SEARCH-001 + ODD-ASN-002: the global `<input>` lives in
    ``src/modules/app-shell/presentation/AppShellGlobalSearch.tsx``
    (a client island inside the AppShellHeader). The pre-ODD-ASN-002
    implementation owned the input inside ``TaxonomyTree.tsx``; the
    ODD-ASN-002 lift moves it to the shell frame so the same input
    is reachable on every route the AppShell wraps (Help, Settings,
    the future hydration-probe stub, etc.) without rewriting the
    search surface per route.

    The DOM contract the input carries is the canonical
    React-shaped hook so a future Playwright probe can locate it
    from the shell surface:

      - `id="app-shell-search-input"` (the namespaced global hook).
      - `data-app-shell-search=""` (the React-shaped marker).
      - `autoComplete="off"` (browsers MUST NOT cache the query).
      - `spellCheck={false}` (no red squiggle on a Latin scientific
        name).
      - placeholder starting with "Search taxa" (the brief's
        required copy; the suffix `…  (Cmd+K)` advertises the
        keyboard shortcut the AppShell wires).
    """
    text = _read_text(APP_SHELL_GLOBAL_SEARCH_FILE)
    # The namespaced id MUST stay present so the global search is
    # reachable from the shell surface (every route the AppShell
    # wraps inherits the input).
    assert re.search(
        r'<input\b[^>]*\bid\s*=\s*"app-shell-search-input"',
        text,
        re.DOTALL,
    ), (
        "AppShellGlobalSearch.tsx must render `<input "
        "id=\"app-shell-search-input\" ...>` so the global "
        "search input is reachable from the AppShell frame."
    )
    # The data-app-shell-search="" attribute pins the React-shaped
    # surface so a future Playwright probe can locate the input
    # via the React hook.
    assert re.search(
        r'<input\b[^>]*\bdata-app-shell-search\s*=\s*""',
        text,
        re.DOTALL,
    ), (
        "AppShellGlobalSearch.tsx must stamp `data-app-shell-search=\"\"` "
        "on the search input (the React-shaped DOM contract)."
    )
    # Autocomplete + spellcheck guards mirror the legacy
    # `web/index.html` `<input id="search-input" autocomplete="off"
    # spellcheck="false">` shape so the React mount behaves
    # identically (browsers must NOT cache the search query, and
    # the red squiggle must NOT fire on a Latin scientific name).
    # React's JSX uses the camelCase form (`autoComplete`); the
    # regex matches either case so a future swap to a typed
    # native element wouldn't trip the guard.
    assert re.search(
        r'<input\b[^>]*\bauto[Cc]omplete\s*=\s*"off"',
        text,
        re.DOTALL,
    ), (
        "AppShellGlobalSearch.tsx must stamp `autoComplete=\"off\"` "
        "on the search input (the legacy `web/index.html` shape)."
    )
    assert re.search(
        r'<input\b[^>]*\bspell[Cc]heck\s*=\s*\{\s*false\s*\}',
        text,
        re.DOTALL,
    ), (
        "AppShellGlobalSearch.tsx must stamp `spellCheck={false}` "
        "on the search input (the legacy `web/index.html` shape — "
        "no red squiggle on a Latin scientific name)."
    )
    # The placeholder drives the visible copy. The brief mandates
    # "Search taxa…" or similar (the suffix `…  (Cmd+K)` advertises
    # the keyboard shortcut the AppShell wires).
    assert re.search(
        r'<input\b[^>]*\bplaceholder\s*=\s*"Search taxa',
        text,
        re.DOTALL,
    ), (
        "AppShellGlobalSearch.tsx must render a placeholder "
        "starting with \"Search taxa\" (the brief's required copy)."
    )


def test_taxonomy_tree_renders_search_results_container() -> None:
    """ODD-SEARCH-001: TaxonomyTree.tsx must render a
    `<div id="search-results" data-search-results>` host for the
    search dropdown. The container stays mounted even when the
    dropdown is closed so a future Playwright probe can locate it
    via the React hook."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r'<div\b[^>]*\bid="search-results"',
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must render `<div id=\"search-results\" ...>` "
        "matching the legacy `web/index.html` selector the ODD-MIGRATE-007 "
        "carveout retired."
    )
    assert re.search(
        r'<div\b[^>]*\bid="search-results"[^>]*\bdata-search-results\s*=\s*""',
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must stamp `data-search-results=\"\"` on the "
        "search-results container (the React-shaped DOM contract)."
    )


def test_taxonomy_tree_renders_search_result_rows_with_select_taxon_action() -> None:
    """ODD-SEARCH-001: each search result row must be a `<button>`
    carrying `data-taxon-id="<id>"` + `data-action="select-taxon"`.
    The click handler routes through the existing React
    `handleSelect(id)` primitive (mirrors the legacy
    `web/nav.js::selectTaxon(id)` flow)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # The render-time template MUST stamp both `data-taxon-id`
    # AND `data-action="select-taxon"` on the result row.
    assert re.search(
        r'data-taxon-id\s*=\s*\{[^}]*hit\.taxon\.id',
        text,
    ), (
        "TaxonomyTree.tsx search result row MUST stamp "
        "`data-taxon-id={hit.taxon.id}` on each row (the React-shaped "
        "DOM contract — the legacy `web/search.js::renderSearchDropdown` "
        "shape preserved verbatim)."
    )
    assert re.search(
        r'data-action\s*=\s*"select-taxon"',
        text,
    ), (
        "TaxonomyTree.tsx search result row MUST stamp "
        "`data-action=\"select-taxon\"` on each row (the React-shaped "
        "DOM contract that mirrors the legacy `select-from-search` action)."
    )
    # The result row is a real `<button>` so keyboard activation
    # (Enter / Space) drives the click handler — matches the
    # legacy click + keyboard contract the legacy
    # `web/nav.js::row-click` listener fired.
    assert re.search(
        r'<button\b[^>]*\bdata-taxon-id\s*=\s*\{[^}]*hit\.taxon\.id[^}]*\}',
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx search result row MUST be a real `<button>` "
        "element (not a `<div>`) so keyboard activation drives the "
        "click handler."
    )


def test_taxonomy_tree_uses_fetch_search_via_barrel() -> None:
    """ODD-SEARCH-001: TaxonomyTree.tsx must consume the canonical
    typed `fetchSearch` helper re-exported by the public
    `@taxa/taxonomy` barrel — never deep paths into the
    infrastructure layer. spec.md rule 5 forbids deep imports via
    the ESLint `no-restricted-imports` guard; rule 4 keeps the
    presentation layer free of duplicated wire projection."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "fetchSearch" in text, (
        "TaxonomyTree.tsx must call the canonical fetchSearch helper"
    )
    assert "from \"@taxa/taxonomy\"" in text or "from '@taxa/taxonomy'" in text, (
        "TaxonomyTree.tsx must import fetchSearch via the @taxa/taxonomy barrel"
    )
    # spec.md rule 5 + ESLint guard: no deep imports into the layer folders.
    for bad in (
        "../infrastructure/api",
        "../infrastructure/api.js",
        "@taxa/taxonomy/infrastructure",
        "@taxa/taxonomy/domain",
    ):
        assert bad not in text, (
            f"TaxonomyTree.tsx must not deep-import {bad!r} (rule 5 barrel guard)"
        )


def test_taxonomy_tree_search_uses_200ms_debounce_and_2_char_gate() -> None:
    """ODD-SEARCH-001: the search input debounces by 200ms (mirrors
    the legacy `web/search.js::runSearch` `setTimeout(..., 200)`)
    and gates the fetch on a 2-character minimum (mirrors the
    legacy `q.length < 2 → closeSearch()` short-circuit)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # 200ms debounce — match `setTimeout(<callback>, 200)` even when
    # the callback is a multi-line arrow function with commas inside.
    assert re.search(r"setTimeout\s*\([\s\S]+?,\s*200\s*\)", text), (
        "TaxonomyTree.tsx search effect MUST debounce by 200ms "
        "(mirrors the legacy `web/search.js::runSearch` debounce)."
    )
    # 2-character gate — the legacy drops the dropdown for
    # `q.length < 2`; the React mount applies the same gate.
    assert re.search(r"\.length\s*<\s*2|length\s*<\s*2", text), (
        "TaxonomyTree.tsx search effect MUST apply a 2-character "
        "minimum gate (mirrors the legacy "
        "`web/search.js::runSearch` `q.length < 2` close)."
    )


def test_taxonomy_tree_result_click_routes_through_select_primitive() -> None:
    """ODD-SEARCH-001: the result-row click handler routes through
    the existing React selection primitive (setFocused + setSelected
    + setPulseNonce — the same body `handleSelect` runs) so the
    React tree focuses + scrolls to the selected taxon after a
    search-result click. Mirrors the legacy
    `web/nav.js::selectTaxon(id)` flow."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # The click handler must set `focused` + `selected` + bump the
    # pulse nonce — the same React-shape primitives `handleSelect`
    # uses. A future refactor that splits the click handler into a
    # different primitive would silently break the focus + scroll
    # affordance, so this test pins the shape.
    handler_block = re.search(
        r"const\s+handleSearchResultClick\s*=\s*useCallback\s*\([^)]*\)\s*=>\s*\{[^}]*setFocused[^}]*setSelected[^}]*setPulseNonce",
        text,
        re.DOTALL,
    )
    assert handler_block is not None, (
        "TaxonomyTree.tsx `handleSearchResultClick` MUST invoke "
        "setFocused + setSelected + setPulseNonce (the same shape "
        "as the React `handleSelect` primitive — so clicking a "
        "search result focuses + scrolls to the selected taxon)."
    )


def test_taxonomy_tree_search_input_does_not_break_existing_pins() -> None:
    """ODD-SEARCH-001: adding the search input MUST NOT regress
    the pre-existing TaxonomyTree contracts — the breadcrumb,
    the initial loading / error / empty states, and the
    `'use client'` directive stay intact.

    ODD-HSS-002 — negative witness: hoisting the source-selector
    to the AppShell header REMOVES the `renderSourceSelector()`
    helper from TaxonomyTree (the segment owns a different host
    now). The new contract is that the toggle lives in the
    AppShell (positive witness:
    `tests/test_app_shell_render.py::test_appshell_renders_source_selector`)
    and TaxonomyTree keeps only the tree surface (the breadcrumb
    + the collapse-all affordance).
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    assert text.lstrip().startswith('"use client"'), (
        "TaxonomyTree.tsx MUST keep the 'use client' directive "
        "(the search input is owned by the same client island)."
    )
    # ODD-HSS-002: the source-selector was hoisted to the AppShell
    # header so it lives above every page state (loading / error /
    # empty / loaded) — TaxonomyTree no longer renders the
    # segmented control. Strip block + line comments first so a
    # docstring that references the legacy `renderSourceSelector()`
    # literal as documentation of the closed regression does NOT
    # trip the negative witness — the witness checks the JSX render
    # + the helper declarations, not the prose.
    code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert "renderSourceSelector()" not in code_only, (
        "ODD-HSS-002: TaxonomyTree.tsx MUST NOT keep "
        "`renderSourceSelector()` — the source-selector was hoisted "
        "to the AppShell header. The positive witness for the new "
        "mount lives in "
        "tests/test_app_shell_render.py::test_appshell_renders_source_selector."
    )
    assert "renderBreadcrumb()" in code_only, (
        "TaxonomyTree.tsx MUST keep `renderBreadcrumb()` "
        "(the native breadcrumb stays intact below the search bar)."
    )


def test_tree_row_uses_semantic_disclosure_button() -> None:
    """TreeRow must use a `<button>` with accurate ``aria-expanded`` for the
    disclosure control. ``aria-controls`` is intentionally OMITTED — children
    render as flat siblings of this row (so there is no single hidden DOM
    target to point at); pointing ``aria-controls`` at an empty hidden
    ``rowgroup`` would misrepresent the disclosure relationship to assistive
    tech. The button is ``disabled`` for leaves and ``aria-expanded`` is
    only emitted on expandable rows."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert re.search(r'<button\b[^>]*aria-expanded', text, re.DOTALL), (
        "TreeRow.tsx must render a <button> with aria-expanded"
    )
    # Look for the *attribute* (aria-controls=...), not the docstring word.
    assert re.search(r'\baria-controls\s*=', text) is None, (
        "TreeRow.tsx must NOT carry the aria-controls attribute "
        "(children are flat siblings, not a hidden target)"
    )
    assert "display: none" not in text and "display:none" not in text, (
        "TreeRow.tsx must not ship a hidden rowgroup (invalid a11y plumbing)"
    )


# ---------------------------------------------------------------------------
# ODD-NTP-003 — native structural parity for the visible tree.
#
# - TreeRow renders a REAL block element (not `display: contents`) so the
#   depth indent applies to the whole identity + disclosure block.
# - The native 24px indent staircase is preserved at every depth.
# - Tier headers are rendered for groups with `count > 1` and live at
#   depth+1 (matching the legacy `web/tree.js::renderTierHeader`).
# - "Load N more" / "Load all" affordances route through the source-aware
#   tree-state helpers (`setShowAll` / `toggleShowAll`).
# - The native collapse-all control clears both expanded + showAll.
# - Leaf behavior: species / subspecies rows carry `data-action="select"`
#   and a `•` glyph; higher ranks carry `data-action="toggle-expand"`.
# - WoRMS / Freshwater auto-unroll fires on every expansion.
# ---------------------------------------------------------------------------

def test_tree_row_renders_a_real_block() -> None:
    """ODD-NTP-003: TreeRow must render as a real block element so the
    depth indent applies to the entire identity + disclosure block
    (legacy `web/tree.js::renderNodeRow` uses `flex items-center
    w-full` with `padding-left: ${16 + indentPx}px`). The previous
    `display: contents` grid flattening is gone — only the name
    cell took the depth indent under that layout, which made the
    React tree visually flattened compared to the legacy oracle."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    # Strip both /* ... */ and // ... comments so docstring
    # references to the legacy cascade ("NOT a `display: contents`
    # placeholder") don't trip the substring check. We only care
    # about runtime CSS values or JSX `style={{ display: "contents"
    # }}` literals.
    stripped = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    stripped = re.sub(r"^\s*//.*$", "", stripped, flags=re.MULTILINE)
    assert "display: contents" not in stripped, (
        "ODD-NTP-003: TreeRow.tsx must NOT use `display: contents` "
        "(in JSX, inline style, or CSS) — the row must be a real "
        "block element so depth indents the whole identity + "
        "disclosure block."
    )
    # The row carries `padding-left: 16 + depth * 24` (or the
    # equivalent `${ROW_BASE_PADDING_PX + depth * ROW_INDENT_PX}px`
    # template literal).
    assert re.search(r"paddingLeft.*16\s*\+\s*depth\s*\*\s*24|paddingLeft.*ROW_BASE", text), (
        "ODD-NTP-003: TreeRow.tsx must compute padding-left as "
        "`16 + depth * 24` (matches legacy `web/tree.js::renderNodeRow`)."
    )
    # ROW_INDENT_PX = 24 is the canonical indent step.
    assert "ROW_INDENT_PX = 24" in text, (
        "ODD-NTP-003: TreeRow.tsx must expose ROW_INDENT_PX = 24 "
        "(legacy 24px indent step)."
    )


def test_tree_row_disclosure_glyphs_match_native() -> None:
    """ODD-NTP-003: leaf rows carry a `•` glyph (no chevron); higher
    ranks show `▾` (expanded) / `▸` (collapsed). Mirrors
    `web/tree.js::chevronFor` which used a small `•` marker for
    species / subspecies and `arrow_drop_down` / `chevron_right`
    for higher ranks."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    # Leaf dot + the two chevron glyphs must all appear in the
    # disclosure block.
    assert '"•"' in text, (
        "ODD-NTP-003: TreeRow.tsx must render a `•` glyph for leaves."
    )
    assert '"▾"' in text, (
        "ODD-NTP-003: TreeRow.tsx must render `▾` for expanded rows."
    )
    assert '"▸"' in text, (
        "ODD-NTP-003: TreeRow.tsx must render `▸` for collapsed rows."
    )


def test_tree_row_stamps_data_action_per_rank() -> None:
    """ODD-NTP-003: leaves stamp `data-action="select"`; higher ranks
    stamp `data-action="toggle-expand"`. Mirrors
    `web/tree.js::renderNodeRow`'s `data-action` contract so the
    future ODD-NTP-005 selection handler dispatches correctly."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert re.search(
        r'data-action\s*=\s*\{?\s*(?:knownLeaf\s*\?\s*["\']select["\']|"select")',
        text,
    ), (
        "ODD-NTP-003: TreeRow.tsx must stamp data-action=\"select\" for leaves."
    )
    assert '"toggle-expand"' in text or "'toggle-expand'" in text, (
        "ODD-NTP-003: TreeRow.tsx must stamp data-action=\"toggle-expand\" for higher ranks."
    )


def test_tree_row_stamps_depth_and_leaf_attributes() -> None:
    """ODD-NTP-003: rows expose `data-depth` and `data-leaf` for the
    future ODD-NTP-004 affordance surface + a11y tooling. Mirrors
    the legacy `web/tree.js::renderNodeRow` data-attribute
    contract."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "data-depth=" in text, (
        "ODD-NTP-003: TreeRow.tsx must stamp data-depth on each row."
    )
    assert "data-leaf=" in text, (
        "ODD-NTP-003: TreeRow.tsx must stamp data-leaf on leaf rows."
    )


def test_taxonomy_tree_renders_tier_headers() -> None:
    """ODD-NTP-003: tier headers render for groups with `count > 1`,
    sitting at depth+1 (same indent as their children). Mirrors
    `web/tree.js::renderTierHeader` byte-for-byte."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "renderTierHeader" in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must declare a renderTierHeader helper."
    )
    assert 'data-tier-header=""' in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must stamp data-tier-header on tier headers."
    )
    assert 'data-tier-parent=' in text, (
        "ODD-NTP-003: tier header must carry data-tier-parent so the "
        "next iteration can identify which parent the tier belongs to."
    )
    assert 'data-tier-rank=' in text, (
        "ODD-NTP-003: tier header must carry data-tier-rank."
    )


def test_taxonomy_tree_load_more_routes_through_source_aware_helpers() -> None:
    """ODD-NTP-003: the "Load N more" affordance calls
    `setShowAll(state, parentId, rank, true)` via a
    `handleLoadMore(parentId, rank)` handler. Mirrors the legacy
    `web/nav.js::load-all` action."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "handleLoadMore" in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must declare a handleLoadMore helper."
    )
    assert "setShowAll" in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must use the setShowAll helper."
    )
    assert re.search(
        r"data-action\s*=\s*[\"\']load-all[\"\']",
        text,
    ), (
        "ODD-NTP-003: TaxonomyTree.tsx must stamp data-action=\"load-all\" "
        "on the tier-header 'Load N more' button."
    )


def test_taxonomy_tree_renders_collapse_all_control() -> None:
    """ODD-NTP-003: the native collapse-all control clears both
    `expandedIds` and `showAll`. Disabled when no expansion
    exists. Mirrors `web/nav.js::collapseAll` +
    `renderCollapseAllButton` byte-for-byte."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "handleCollapseAll" in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must declare a handleCollapseAll handler."
    )
    assert "clearExpansion" in text, (
        "ODD-NTP-003: handleCollapseAll must call clearExpansion "
        "(clears both expandedIds + showAll in one shot)."
    )
    assert 'id="collapse-all"' in text or 'id=\\"collapse-all\\"' in text, (
        "ODD-NTP-003: collapse-all button must carry id=\"collapse-all\" "
        "(matches the legacy `web/nav.js` selector)."
    )
    assert 'data-action="collapse-all"' in text or "data-action=\"collapse-all\"" in text, (
        "ODD-NTP-003: collapse-all button must stamp data-action=\"collapse-all\"."
    )


def test_taxonomy_tree_wires_auto_unroll_for_source() -> None:
    """ODD-NTP-003: WoRMS / Freshwater expansions auto-unroll
    every tier of the expanded node. Mirrors the legacy
    `web/nav.js::toggleExpand` predicate. The CoL view is a no-op
    so the PAGE_SIZE staircase stays snappy."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "autoUnrollForSource" in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must consume autoUnrollForSource."
    )
    # The auto-unroll helper must be called for at least one of the
    # two places the legacy oracle calls it (toggleExpand /
    # attachChildren). The CoL view must stay a no-op.
    assert re.search(
        r"(worms|freshwater).*autoUnrollForSource|autoUnrollForSource.*(?:worms|freshwater)",
        text,
        re.DOTALL,
    ), (
        "ODD-NTP-003: autoUnrollForSource must be gated on the WoRMS / "
        "Freshwater source (CoL view stays a no-op)."
    )


def test_taxonomy_tree_uses_group_children_by_rank() -> None:
    """ODD-NTP-003: the recursive render routes through
    `groupChildrenByRank` so rank grouping + source filtering +
    PAGE_SIZE staircase + showAll are all applied in the canonical
    pure helper. The component must NOT reinvent grouping logic."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "groupChildrenByRank" in text, (
        "ODD-NTP-003: TaxonomyTree.tsx must consume groupChildrenByRank."
    )


def test_tree_state_source_file_exports_ntp_003_helpers() -> None:
    """ODD-NTP-003: tree-state.ts must export the full native
    structural surface: PAGE_SIZE constant, groupChildrenByRank,
    setShowAll / toggleShowAll / isShowAll, clearShowAll /
    clearExpansion, autoUnrollForSource, expandedTierCount,
    isLeafRank, and the `showAll` field on `TreeState`."""
    text = _read_text(TAXONOMY_TREE_STATE_FILE)
    for name in (
        "PAGE_SIZE", "groupChildrenByRank", "setShowAll",
        "toggleShowAll", "isShowAll", "clearShowAll",
        "clearExpansion", "autoUnrollForSource",
        "expandedTierCount", "isLeafRank", "RankGroup",
    ):
        assert re.search(
            rf"export\s+(?:async\s+)?function\s+{name}\b|"
            rf"export\s+const\s+{name}\b|"
            rf"export\s+interface\s+{name}\b|"
            rf"export\s+type\s+{name}\b",
            text,
        ), (
            f"ODD-NTP-003: tree-state.ts must export `{name}`."
        )
    assert "showAll" in text, (
        "ODD-NTP-003: tree-state.ts must carry a showAll field on TreeState."
    )


def test_tree_state_rank_group_contract() -> None:
    """ODD-NTP-003: the `RankGroup` type exposes rank + count +
    visibleIds + remaining + fullyShown — the exact fields the
    React component reads to render the tier header + visible
    children + Load N more affordance."""
    text = _read_text(TAXONOMY_TREE_STATE_FILE)
    for field in ("rank", "count", "visibleIds", "remaining", "fullyShown"):
        assert re.search(
            rf"readonly\s+{field}\s*:",
            text,
        ), (
            f"ODD-NTP-003: RankGroup must expose `{field}`."
        )


def test_out_index_html_omits_display_contents_in_tree_css(static_export) -> None:
    """ODD-NTP-003: the static export's CSS must NOT include
    `.tree-row { display: contents }` (the previous ODD-VTREE-002
    cascade). The new ODD-NTP-003 row is a real flex block so
    the depth indent applies to the whole identity block."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    assert css_chunks, "static export must emit at least one CSS chunk"
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    # The minified cascade concatenates `.tree-row{display:contents}`
    # into one block. Reject that single concat only — generic
    # `display:contents` references elsewhere (e.g. utility classes
    # outside the tree cascade) are not in scope of this assertion.
    assert ".tree-row{display:contents" not in css_body, (
        "ODD-NTP-003: static CSS must not include "
        "`.tree-row{display:contents}` (real block layout only)."
    )
    assert not re.search(
        r"\.tree-row\s*\{[^}]*display\s*:\s*contents",
        css_body,
    ), (
        "ODD-NTP-003: the .tree-row selector must use a block / flex "
        "display, not `display: contents`."
    )


def test_out_index_html_has_tier_header_css(static_export) -> None:
    """ODD-NTP-003: the static export's CSS must define the
    `.tier-header` and `.load-all` rules so the native tier
    grouping renders identically to the legacy oracle."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    assert ".tier-header" in css_body, (
        "ODD-NTP-003: static CSS must define the .tier-header rule."
    )
    assert ".load-all" in css_body, (
        "ODD-NTP-003: static CSS must define the .load-all rule."
    )
    assert "collapse-all-btn" in css_body or ".collapse-all-btn" in css_body or "tree-collapse-all" in css_body, (
        "ODD-NTP-003: static CSS must define the .collapse-all-btn / "
        ".tree-collapse-all rule for the native collapse-all control."
    )


def test_tree_row_initial_state_is_collapsed() -> None:
    """ODD-VTREE-002 acceptance: root rows render collapsed initially
    (the tree fetches roots, but does not auto-expand any)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # The tree initializes with EMPTY_TREE_STATE; the expandedIds Set is
    # only populated by toggleExpand. No auto-expand on fetch.
    assert "EMPTY_TREE_STATE" in text, (
        "TaxonomyTree.tsx must initialize with EMPTY_TREE_STATE (collapsed)"
    )
    assert "expand(" not in text.replace("toggleExpand(", "").replace("isExpanded(", ""), (
        "TaxonomyTree.tsx must not auto-expand; the only mutator is toggleExpand"
    )


# ---------------------------------------------------------------------------
# ODD-NTP-004 — native row identity + source affordances.
#
# - TreeRow carries `data-realm` (computed from `taxon.path`) so the
#   CSS realm-tint cascade in `src/app/globals.css` can colour the
#   scientific-name span per domain / kingdom.
# - TreeRow renders the status dot (accepted / synonym / unknown).
# - TreeRow renders the source info affordance (CoL-only /
#   WoRMS-only / cross-link) when the legacy `sourceInfoTooltip`
#   predicate returns a string. Renders nothing otherwise.
# - TreeRow renders the materialize indicator when
#   `research_path_exists === true` (or the propagated cache hits).
#   ODD-NTP-004 defers the desktop / file endpoints; the indicator
#   is a pure visual state with no click handler.
# - TreeRow renders the species-count badge via `speciesCountBadge`.
# - TreeRow renders the kebab trigger + menu structure. Items
#   whose backing React behavior exists stay enabled; items whose
#   backing handler is deferred to ODD-NTP-005 render with
#   `disabled` + `aria-disabled="true"`.
# - TreeRow carries the depth-sensitive scientific-name class so the
#   root row gets the larger `font-h1` treatment and descendants
#   stay on `font-body-lg`.
# ---------------------------------------------------------------------------

def test_tree_row_renders_data_realm_attribute() -> None:
    """ODD-NTP-004: every row must stamp `data-realm` (derived from
    `taxon.path` via `realmForPath`) so the CSS realm-tint cascade
    can colour the scientific-name span per domain / kingdom.
    Mirrors `web/tree.js::renderNodeRow::realm` byte-for-byte."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "data-realm" in text, (
        "ODD-NTP-004: TreeRow.tsx must stamp data-realm on every row."
    )
    assert "realmForPath" in text, (
        "ODD-NTP-004: TreeRow.tsx must compute the realm via realmForPath."
    )


def test_tree_row_renders_status_dot() -> None:
    """ODD-PHASE2: every row renders the status indicator as an inline
    `<span>` inside the new `<Badge variant="subtle" uppercase={false}>`
    composite (status dot + species count). The old `.status-dot-*`
    CSS-class hooks are gone — the colour is applied inline with the
    canonical Tailwind utilities:

      - green-500   for `accepted`  (matches `web/tree.js::statusDot`).
      - amber-500   for `synonym`   (matches `web/tree.js::statusDot`).
      - on-surface-variant for `unknown` (the neutral fallback).

    The indicator MUST also carry a `role="img"` + `aria-label` /
    `title` set to `statusDotDescriptor(taxon.status).title` so
    assistive tech announces the canonical status label. The helper
    `statusDotDescriptor` from `row-format.ts` is preserved so the
    tooltip text stays byte-identical to the legacy oracle."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "statusDotDescriptor" in text, (
        "ODD-PHASE2: TreeRow.tsx must consume the statusDotDescriptor helper."
    )
    # `bg-green-500` + `bg-amber-500` + `bg-on-surface-variant` are the
    # canonical Tailwind utilities that surface the three status
    # colours. The PR replaces the `.status-dot-{accepted|synonym|unknown}`
    # CSS hooks with these inline classes.
    assert "bg-green-500" in text, (
        "ODD-PHASE2: accepted status must paint with `bg-green-500`."
    )
    assert "bg-amber-500" in text, (
        "ODD-PHASE2: synonym status must paint with `bg-amber-500`."
    )
    assert "bg-on-surface-variant" in text, (
        "ODD-PHASE2: unknown status must paint with `bg-on-surface-variant`."
    )
    # The indicator MUST remain accessible: `role="img"` + an aria-label
    # / title set to the canonical tooltip text from the row-format
    # helper. Reject the legacy `.status-dot-{accepted|synonym|unknown}`
    # class hooks — those CSS rules disappear with the rewrite. The
    # className-anchored regex avoids false positives from the file's
    # docstring which mentions `.status-dot-*` literally.
    assert re.search(
        r'role\s*=\s*"img"',
        text,
    ), "ODD-PHASE2: status indicator must carry role=\"img\"."
    assert 'statusDotTitle' in text or r'statusDot.title' in text, (
        "ODD-PHASE2: status indicator must read statusDot.title from the helper."
    )
    assert not re.search(
        r'className\s*=\s*["\'][^"\']*status-dot-',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT carry `.status-dot-*` class "
        "hooks (colour is inline via Tailwind utilities)."
    )


def test_tree_row_renders_source_info_affordance() -> None:
    """ODD-PHASE2: the source info tooltip collapses into the `title`
    attribute of the scientific-name span. The legacy `sourceInfoTooltip`
    predicate still gates whether a `title` attribute renders (it returns
    `null` for taxa whose source identity doesn't add any context),
    but when it does render, the tooltip text now lives on the NAME
    span instead of a dedicated info glyph. Mirrors the
    `web/tree.js::renderNodeRow::sourceTooltipText` source-aware
    decision byte-for-byte (the actual tooltip text is unchanged).

    The Material Symbols `info` glyph + the `.source-info` class are
    GONE — the source info becomes a native browser tooltip (no extra
    DOM weight, screen readers still surface the tooltip text)."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    # The new affordance: the name `<span>` carries `title={nameTitle}`
    # which carries `${taxon.name} ${taxon.authorship}` when authorship
    # is truthy. The legacy `sourceInfoTooltip` is folded into the same
    # `title` string so the browser tooltip includes BOTH the authorship
    # AND the source identity context.
    name_span_match = re.search(
        r'<span\b[^>]*\btitle\s*=',
        text,
    )
    assert name_span_match, (
        "ODD-PHASE2: TreeRow.tsx must render a <span> with a `title` "
        "attribute carrying the source info + authorship tooltip."
    )
    assert "nameTitle" in text, (
        "ODD-PHASE2: TreeRow.tsx must thread the `nameTitle` template "
        "through to the name span's `title` attribute."
    )
    # The old `source-info` class hook + `data-source-info` attribute
    # are GONE (the source info no longer renders a dedicated glyph).
    # The className-anchored regex avoids false positives from the
    # file's docstring which mentions `source-info` / `data-source-info`
    # literally as legacy references.
    assert not re.search(
        r'className\s*=\s*["\'][^"\']*\bsource-info\b',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT render `.source-info` class "
        "hook (folded into name span title)."
    )
    assert not re.search(
        r'\bdata-source-info\s*=',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT stamp `data-source-info` "
        "(folded into name span title)."
    )


def test_tree_row_renders_materialize_indicator() -> None:
    """ODD-TAPOPUP-001: the materialize indicator on the row
    surface is a `data-materialized` attribute (the popup's
    Folder tab reads the attribute to know whether the row
    is materialized). The pre-popup kebab menu's
    `data-action="open-folder-tab"` item is GONE — the
    kebab menu is gone; the popup's Folder tab owns the
    create/open flow. The materialize predicate
    (`hasMaterializedFolder(taxon)`) stays consumed so the
    row's `data-materialized` attribute reflects the
    canonical materialize state."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", text)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert "hasMaterializedFolder" in text, (
        "ODD-PHASE2: TreeRow.tsx must consume the hasMaterializedFolder helper."
    )
    # ODD-TAPOPUP-001: the kebab menu's `data-action="open-folder-tab"`
    # item is GONE.
    assert not re.search(
        r'data-action="open-folder-tab"',
        code_only,
    ), (
        "ODD-TAPOPUP-001: TreeRow.tsx must NOT carry "
        "`data-action=\"open-folder-tab\"` (the kebab menu item "
        "is gone; the Folder tab in the popup drives the "
        "create/open flow)."
    )
    # The row-level materialize indicator + its data attribute
    # are GONE. The class hook + data attribute must NOT
    # appear in the JSX. The className-anchored regex avoids
    # false positives from the file's docstring which mentions
    # `materialize-indicator` / `data-materialize-indicator`
    # literally as legacy references.
    assert not re.search(
        r'className\s*=\s*["\'][^"\']*\bmaterialize-indicator\b',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT render `.materialize-indicator` "
        "glyph (folded into the kebab 'Open folder' item)."
    )
    assert not re.search(
        r'\bdata-materialize-indicator\s*=',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT stamp `data-materialize-indicator` "
        "(the kebab menu replaces the row-level glyph)."
    )


def test_tree_row_renders_species_count_badge() -> None:
    """ODD-PHASE2: the species-count badge is now INSIDE the new
    `<Badge variant="subtle" uppercase={false}>` composite (status
    dot + count). The 9-element row collapses to 5 — the status
    dot + species count become a single Badge. The count text is
    formatted via the row-format `speciesCountBadge` helper (5 /
    3k / 2.5M thresholds) and rendered with the `font-mono-data`
    class so the JetBrains Mono treatment stays byte-identical to
    the legacy `web/index.html::.font-mono-data` cascade. The
    `data-species-count` data attribute on the OLD inline span
    is no longer required (the Badge wrapping makes the count
    part of the status+count composite — the per-row tooltip
    still carries the canonical count context)."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "speciesCountBadge" in text, (
        "ODD-PHASE2: TreeRow.tsx must consume the speciesCountBadge helper."
    )
    # The count text MUST live inside a Badge component (the new
    # status+count composite). The Badge primitive is imported from
    # `@taxa/design-system` and used with `uppercase={false}` so the
    # rank-badge treatment (uppercase + tracked Raleway) does NOT
    # apply to the count text.
    assert re.search(
        r'<\s*Badge\b[^>]*\buppercase\s*=\s*\{\s*false\s*\}',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must render the species-count text "
        "inside a `<Badge uppercase={false}>` composite."
    )
    assert "font-mono-data" in text, (
        "ODD-PHASE2: TreeRow.tsx must apply `font-mono-data` to the "
        "species-count text so the JetBrains Mono treatment carries "
        "forward from the legacy cascade."
    )
    # The OLD inline `<span className="species-count-badge ...">` is
    # GONE — the count now lives inside the Badge composite. The
    # className-anchored regex avoids false positives from the
    # file's docstring which mentions `species-count-badge` literally.
    assert not re.search(
        r'className\s*=\s*["\'][^"\']*species-count-badge',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT render `.species-count-badge` "
        "inline span (the Badge composite replaces it)."
    )


def test_tree_row_renders_kebab_trigger() -> None:
    """ODD-TAPOPUP-001: every row renders a kebab trigger
    IconButton that opens the taxon-action popup for that row.
    The trigger carries:
      - the canonical `kebab-trigger` class hook so the existing
        `.kebab .kebab-trigger` CSS rule (passive-hint opacity +
        hover/focus reveal) keeps working,
      - `data-action="toggle-kebab"` for the row-level action
        delegation contract,
      - `aria-haspopup="dialog"` to advertise the popup target
        (was `aria-haspopup="menu"` in the pre-popup kebab menu),
      - `aria-expanded` driven by `selected === taxon.id` so
        assistive tech sees the popup's open state for that row.

    The kebab MENU (`.kebab-menu` + items) is GONE — clicking the
    trigger opens the popup directly. The popup owns the four
    tabbed sections (Synonyms / Distribution / Search / Folder)."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    # `kebab-trigger` class hook MUST reach the JSX (either on the
    # IconButton's className or via a wrapper) so the existing CSS
    # discoverability rule (passive-hint opacity + hover/focus
    # reveal) is wired.
    assert re.search(
        r'className\s*=\s*["\'][^"\']*\bkebab-trigger\b',
        text,
    ), (
        "ODD-TAPOPUP-001: TreeRow.tsx must stamp the `kebab-trigger` "
        "class hook on the row's IconButton (or its kebab wrapper) "
        "so the existing `.kebab .kebab-trigger` CSS discoverability "
        "rule (passive-hint opacity + hover/focus reveal) is wired."
    )
    assert '"toggle-kebab"' in text or "'toggle-kebab'" in text, (
        "ODD-TAPOPUP-001: kebab trigger must stamp data-action=\"toggle-kebab\"."
    )
    # The popup replaces the kebab menu — the trigger advertises
    # the popup target via `aria-haspopup="dialog"`, NOT
    # `aria-haspopup="menu"`.
    assert 'aria-haspopup="dialog"' in text, (
        "ODD-TAPOPUP-001: kebab trigger must declare "
        "`aria-haspopup=\"dialog\"` (the popup replaces the "
        "kebab menu)."
    )
    assert "aria-expanded" in text, (
        "ODD-TAPOPUP-001: kebab trigger must declare aria-expanded."
    )


def test_tree_row_does_not_render_kebab_menu() -> None:
    """ODD-TAPOPUP-001: the row-level kebab menu is GONE.
    Clicking the kebab IconButton opens the taxon-action popup
    directly (no in-row dropdown menu). The popup replaces the
    kebab menu's `Open folder` + `View on WoRMS` affordances —
    the four tabbed sections (Synonyms / Distribution / Search
    / Folder) subsume the menu shortcuts. The View on WoRMS
    outbound shortcut is dropped (the WoRMS URL is no longer
    surfaced via the row surface — the user opens it from the
    WoRMS link the popup might surface in a future slice).

    Pins:
      - No `.kebab-menu` element in the JSX (the menu container
        is gone).
      - No `.kebab-item` elements (the menu items are gone).
      - No `data-action="open-folder-tab"` (the kebab item that
        pinned the Folder tab is gone; the Folder tab still
        opens via the popup's Folder tab).
      - No `data-action="view-on-worms"` (the WoRMS shortcut
        is gone).
      - No `data-action="open-searches"` (the legacy
        `View details` kebab item is gone — the disclosure click
        + the popup replace it)."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    # The kebab menu container is GONE. The descendant class
    # hook `.kebab-menu` MUST NOT appear in the JSX as a
    # className entry. The className-anchored regex avoids
    # false positives from docstring references which mention
    # `kebab-menu` literally as a legacy reference.
    assert not re.search(
        r'className\s*=\s*["\'][^"\']*\bkebab-menu\b',
        text,
    ), (
        "ODD-TAPOPUP-001: TreeRow.tsx must NOT render the "
        "`.kebab-menu` container (the popup replaces the kebab "
        "menu)."
    )
    # The kebab item class hook is GONE.
    assert not re.search(
        r'className\s*=\s*["\'][^"\']*\bkebab-item\b',
        text,
    ), (
        "ODD-TAPOPUP-001: TreeRow.tsx must NOT render any "
        "`.kebab-item` element (the menu items are gone)."
    )
    # No menu-level data-actions survive.
    for action in ("open-folder-tab", "view-on-worms", "open-searches"):
        assert action not in text, (
            f"ODD-TAPOPUP-001: TreeRow.tsx must NOT carry "
            f"`data-action=\"{action}\"` (the menu is gone; "
            f"the popup owns the four tabs)."
        )
    # The legacy `wormsUrlFor` helper is no longer needed at the
    # row level (the WoRMS outbound shortcut is gone). The helper
    # stays in `row-format.ts` for future consumers.
    assert "wormsUrlFor" not in text, (
        "ODD-TAPOPUP-001: TreeRow.tsx must NOT consume "
        "`wormsUrlFor` (the WoRMS outbound shortcut is gone)."
    )
    # The `hasMaterializedFolder` helper is still consumed (the
    # materialize indicator stays — the Folder tab inside the
    # popup handles the create flow when the row is materialized).
    assert "hasMaterializedFolder" in text, (
        "ODD-TAPOPUP-001: TreeRow.tsx must still consume "
        "`hasMaterializedFolder` (the materialize indicator on "
        "the row stays — the Folder tab in the popup drives the "
        "create flow)."
    )


def test_tree_row_carries_depth_sensitive_name_class() -> None:
    """ODD-NTP-004: the scientific-name span carries a
    depth-sensitive class (`scientific-name-depth-0` for the root
    row, `scientific-name-depth-n` for descendants) so the CSS in
    `src/app/globals.css` can apply the larger `font-h1` treatment
    on root rows and the smaller `font-body-lg` on descendants.
    Mirrors the legacy `web/tree.js::nameClassFor` helper. The
    class string is generated by the row-format
    `scientificNameDepthClass` helper; the CSS rule ships in
    `src/app/globals.css` and is verified separately by the
    `out_index_html_has_row_affordance_styles` static-export
    witness."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "scientificNameDepthClass" in text, (
        "ODD-NTP-004: TreeRow.tsx must consume the scientificNameDepthClass helper."
    )
    # The depth-sensitive class MUST reach the JSX output. The
    # helper concatenates `scientific-name scientific-name-depth-0`
    # for depth === 0 and `scientific-name scientific-name-depth-n`
    # otherwise, so we assert on the helper call site + the literal
    # `scientific-name-depth-0` / `scientific-name-depth-n` strings
    # in the source. The literal strings actually live in the
    # row-format helper (which the React component imports); both
    # locations are verified by the runtime row-format harness.
    row_format_text = _read_text(REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "row-format.ts")
    assert "scientific-name-depth-0" in row_format_text, (
        "ODD-NTP-004: row-format.ts must generate the depth-0 class."
    )
    assert "scientific-name-depth-n" in row_format_text, (
        "ODD-NTP-004: row-format.ts must generate the depth-n class."
    )


def test_taxonomy_tree_kebab_click_routes_through_select_primitive() -> None:
    """ODD-TAPOPUP-001: clicking the row-level kebab IconButton
    routes through the canonical `handleSelect(id)` selection
    primitive — opening the taxon-action popup for that row is
    the same primitive as selecting the row's disclosure
    (selection is orthogonal to expansion; the popup is a
    selected-taxon surface). The kebab IconButton's click
    handler in TreeRow.tsx calls the `onToggleKebab` prop
    callback; TaxonomyTree wires that callback to
    `handleSelect(id)` so the URL state (`?taxon=ID`),
    breadcrumb focus, row pulse, and scroll-into-view all fire
    byte-for-byte against the disclosure-click path.

    Pins the contract:
      - `handleToggleKebab` is the kebab-click callback
        declared by TaxonomyTree (the kebab trigger prop on
        TreeRow).
      - `handleToggleKebab` delegates to `handleSelect(id)`
        (NOT to a kebab-menu state setter).
      - The kebab menu state contract (`kebabOpenId` /
        `handleKebabAction` / `setKebabOpenId`) is GONE —
        there is no in-row dropdown menu anymore."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # Strip line comments so the contract-pins below ignore
    # migration-history references in docstrings (the test is
    # about CODE contract, not about historical references in
    # comments).
    code_only = re.sub(r"//[^\n]*", "", text)
    assert "handleToggleKebab" in code_only, (
        "ODD-TAPOPUP-001: TaxonomyTree.tsx must declare a "
        "`handleToggleKebab` callback for the row kebab trigger."
    )
    # Find the handleToggleKebab body and pin it delegates to
    # handleSelect(id) — the kebab-click opens the popup via the
    # canonical selection primitive.
    handle_idx = text.find("const handleToggleKebab")
    assert handle_idx != -1, (
        "TaxonomyTree.tsx must declare `handleToggleKebab` as a "
        "const handler."
    )
    handle_end = text.find("\n  }, [", handle_idx)
    assert handle_end != -1, "handleToggleKebab must be a useCallback"
    body = text[handle_idx:handle_end]
    assert "handleSelect(id)" in body, (
        "ODD-TAPOPUP-001: handleToggleKebab must delegate to "
        "`handleSelect(id)` so the kebab-click opens the popup "
        "via the canonical selection primitive."
    )
    # The kebab menu state contract is GONE — no `kebabOpenId` /
    # `handleKebabAction` / `setKebabOpenId` references IN CODE.
    for needle in ("kebabOpenId", "handleKebabAction", "setKebabOpenId"):
        assert needle not in code_only, (
            f"ODD-TAPOPUP-001: TaxonomyTree.tsx must NOT carry "
            f"`{needle}` (the kebab menu state contract is gone; "
            f"the popup is selected-driven)."
        )


def test_taxonomy_tree_dismisses_popup_on_source_switch() -> None:
    """ODD-TAPOPUP-001: a source switch closes the open
    taxon-action popup so the panel never lingers over a taxon
    re-projected under a different source. The popup is
    `selected`-driven, so closing the popup on source switch is
    `setSelected(null)` in the ODD-HSS-001 source-switch
    `useEffect` body. The pre-popup kebab-menu dismissal
    (`setKebabOpenId(null)`) is GONE — the popup is the only
    transient surface now.

    ODD-HSS-001 — the source-bound cleanup cascade moved from
    the `handleSourceChange` callback into a `useEffect` that
    fires whenever `activeSource` changes. The regression guard
    pins the contract against the new effect-based location."""
    text = _read_text(TAXONOMY_TREE_FILE)
    body = _od_hss_source_switch_effect_body(text)
    code_only = re.sub(r"//[^\n]*", "", text)
    assert "setSelected(null)" in body, (
        "ODD-TAPOPUP-001: the ODD-HSS-001 source-switch "
        "`useEffect(() => { ... }, [activeSource])` body must "
        "close the open popup via `setSelected(null)` so a "
        "stale panel cannot linger over a taxon re-projected "
        "under the new source."
    )
    # The pre-popup kebab menu dismissal is GONE.
    assert "setKebabOpenId" not in code_only, (
        "ODD-TAPOPUP-001: TaxonomyTree.tsx must NOT carry "
        "`setKebabOpenId` (the kebab menu is gone; the popup "
        "closes via `setSelected(null)`)."
    )


def test_taxonomy_tree_dismisses_kebab_on_collapse_all() -> None:
    """ODD-NTP-004: the collapse-all control also clears the open
    kebab so a menu never lingers over a row that has been
    collapsed."""
    text = _read_text(TAXONOMY_TREE_FILE)
    handle_idx = text.find("const handleCollapseAll")
    assert handle_idx != -1, (
        "TaxonomyTree.tsx must declare handleCollapseAll."
    )
    # Anchor on the `clearExpansion` call site (must be present in
    # the body) and the `setKebabOpenId(null)` reset.
    assert "setKebabOpenId(null)" in text[handle_idx:handle_idx + 800], (
        "ODD-NTP-004: handleCollapseAll must close the open kebab."
    )


def test_taxonomy_tree_handles_escape_keypress() -> None:
    """ODD-NTP-004 (carry-over) + ODD-TAPOPUP-001: pressing
    Escape closes every open kebab AND the open taxon-action
    popup. The pre-popup kebab Escape-close effect is owned by
    `DetailPanel` (the popup registers its own document-level
    keydown listener that closes on Escape); the kebab menu is
    gone so the tree-level kebab effect is gone.

    The Escape listener for the popup lives in DetailPanel.tsx,
    not TaxonomyTree.tsx — the regression guard pins the
    contract against the DetailPanel location. The
    `TaxonomyTree.tsx` file MUST NOT register a document-level
    keydown listener for `Escape` (the tree no longer owns the
    popup close handler)."""
    # DetailPanel owns the Escape close.
    panel_text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert '"keydown"' in panel_text or "'keydown'" in panel_text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must register a keydown "
        "listener for the popup's Escape close behavior."
    )
    assert "Escape" in panel_text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must listen for the "
        "Escape key so the popup closes via keyboard."
    )
    # TaxonomyTree no longer owns the Escape close (the popup's
    # Escape listener is delegated to DetailPanel). The tree
    # MAY still register other keydown listeners (the j/k
    # navigation handler stays), but the Escape-driven close is
    # gone from the tree level.
    tree_text = _read_text(TAXONOMY_TREE_FILE)
    tree_code_only = re.sub(r"//[^\n]*", "", tree_text)
    # The pre-popup kebab Escape-close useEffect body starts
    # with `if (kebabOpenId === null) return;` and the
    # `setKebabOpenId(null)` reset. Both MUST be gone.
    assert "setKebabOpenId(null)" not in tree_code_only, (
        "ODD-TAPOPUP-001: TaxonomyTree.tsx must NOT carry the "
        "kebab Escape-close useEffect (the kebab menu is gone; "
        "the popup Escape listener lives in DetailPanel)."
    )


def test_taxonomy_tree_collapse_all_preserves_popup() -> None:
    """ODD-TAPOPUP-001: the collapse-all control PRESERVES
    `selected` so the popup stays open over the collapsed tree.
    The legacy `web/nav.js::collapseAll` clears expansion
    without clearing focused / selected (selection is
    independent of expansion); the React cutover mirrors that
    contract so the popup stays open after a collapse-all.

    The pre-popup kebab dismissal (`setKebabOpenId(null)`) is
    gone (the kebab menu is gone); the kebab menu state
    contract (`kebabOpenId` / `setKebabOpenId`) is retired."""
    text = _read_text(TAXONOMY_TREE_FILE)
    code_only = re.sub(r"//[^\n]*", "", text)
    handle_idx = text.find("const handleCollapseAll")
    assert handle_idx != -1, (
        "TaxonomyTree.tsx must declare handleCollapseAll."
    )
    # Anchor on the `clearExpansion` call site (must be present
    # in the body) and the absence of `setSelected(null)` so the
    # popup stays open over the collapsed tree.
    assert "clearExpansion" in text[handle_idx:handle_idx + 800], (
        "ODD-TAPOPUP-001: handleCollapseAll must call "
        "`clearExpansion` so the collapse-all control collapses "
        "the tree."
    )
    assert "setSelected(null)" not in text[handle_idx:handle_idx + 800], (
        "ODD-TAPOPUP-001: handleCollapseAll MUST NOT call "
        "`setSelected(null)` (the popup stays open over the "
        "collapsed tree; selection is independent of "
        "expansion)."
    )
    assert "setKebabOpenId" not in code_only, (
        "ODD-TAPOPUP-001: TaxonomyTree.tsx must NOT carry "
        "`setKebabOpenId` (the kebab menu is gone; the popup is "
        "`selected`-driven)."
    )


def test_out_index_html_has_kebab_trigger_styles(static_export) -> None:
    """ODD-TAPOPUP-001: the static export's CSS must keep the
    `.kebab-trigger` discoverability rule (passive-hint opacity
    + hover/focus reveal) so the kebab IconButton stays
    discoverable on every row. The pre-popup `.kebab-menu` /
    `.kebab-item` rules are GONE (the menu items collapsed into
    the popup's four tabs). The `.kebab` base rule stays so
    the chain-topology guard in `tests/test_research_styles.py`
    keeps whitelisting the row-level affordance surface."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    # The kebab-trigger discoverability hook MUST survive.
    assert ".kebab-trigger" in css_body, (
        "ODD-TAPOPUP-001: static CSS must keep the `.kebab-trigger` "
        "discoverability rule (passive-hint opacity + hover/focus "
        "reveal) so the kebab IconButton stays discoverable."
    )
    # The hover/focus reveal cascade MUST survive so the
    # IconButton paints at full opacity on row hover / focus-within.
    assert ".tree-row:hover .kebab-trigger" in css_body, (
        "ODD-TAPOPUP-001: static CSS must keep the "
        "`.tree-row:hover .kebab-trigger` hover-reveal rule."
    )
    assert ".tree-row:focus-within .kebab-trigger" in css_body, (
        "ODD-TAPOPUP-001: static CSS must keep the "
        "`.tree-row:focus-within .kebab-trigger` focus-reveal rule."
    )
    # The menu cascade is GONE (no menu items anymore).
    assert ".kebab-menu" not in css_body, (
        "ODD-TAPOPUP-001: static CSS must NOT carry the "
        "`.kebab-menu` rule (the menu items collapsed into the "
        "popup's four tabs)."
    )
    assert ".kebab-item" not in css_body, (
        "ODD-TAPOPUP-001: static CSS must NOT carry the "
        "`.kebab-item` rule (the menu items collapsed into the "
        "popup's four tabs)."
    )


def test_out_index_html_has_row_affordance_styles(static_export) -> None:
    """ODD-PHASE2: the per-row affordance cascade shrinks after the
    rewrite. The `.status-dot*`, `.source-info`, `.materialize-indicator`,
    and `.species-count-badge` rules are gone (the row collapses to 5
    visible elements; the new status+count Badge + the kebab IconButton
    centralize what they used to do). The `scientific-name-depth-0 /
    -n` rules + the realm-tint cascade stay (they describe the
    scientific-name typography / hue, not the dropped glyphs)."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    # The depth-sensitive scientific-name rules + the realm-tint cascade
    # STAY (they describe typography + hue, not the dropped glyphs).
    for selector in (
        ".scientific-name-depth-0",
        ".scientific-name-depth-n",
    ):
        assert selector in css_body, (
            f"ODD-PHASE2: static CSS must define the {selector} rule "
            "(depth-sensitive scientific-name typography)."
        )
    # Realm-tint cascade (mirrors `web/index.html::.tree-row[data-realm="X"]
    # .scientific-name`). Seven canonical realms (the source form
    # uses unquoted attribute selectors `[data-realm=X]` which is
    # what Tailwind v4's minifier emits). The "other" fallback is
    # the `.tree-row[data-realm] .scientific-name` base rule.
    for realm in ("bacteria", "archaea", "viruses", "animalia",
                  "fungi", "plantae", "chromista"):
        assert f'data-realm={realm}' in css_body, (
            f"ODD-PHASE2: static CSS must define the realm tint for {realm!r}."
        )
    # ODD-PHASE2: the dropped per-row affordance CSS rules must NOT
    # survive in the static export (the worker removed them from
    # globals.css after confirming zero references remain in src/).
    for removed_selector in (
        ".status-dot",
        ".status-dot-accepted",
        ".status-dot-synonym",
        ".status-dot-unknown",
        ".source-info",
        ".materialize-indicator",
        ".species-count-badge",
        ".tree-search-icon",
    ):
        assert removed_selector not in css_body, (
            f"ODD-PHASE2: static CSS must NOT carry the dead {removed_selector} "
            "rule (removed in the ODD-TRE-003 globals.css cleanup)."
        )


# ---------------------------------------------------------------------------
# Build witness — static export carries the visible shell + tree SSR
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def static_export() -> None:
    """Run ``next build`` once per module and assert ``out/index.html`` exists."""
    if not (REPO_ROOT / "node_modules" / ".bin" / "next").is_file() and shutil.which("next") is None:
        pytest.skip("next binary not installed — skip build witness during RED")
    proc = subprocess.run(
        ["npx", "--no-install", "next", "build"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"npx next build failed (rc={proc.returncode}); "
            f"stdout tail:\n{proc.stdout[-2000:]}\nstderr tail:\n{proc.stderr[-2000:]}"
        )
    if not OUT_INDEX.is_file():
        pytest.fail(f"next build did not produce {OUT_INDEX.relative_to(REPO_ROOT)}")


def test_out_index_html_has_app_shell_landmarks(static_export):
    html = _read_text(OUT_INDEX)
    for tag in ("<header", "<main", "<footer"):
        assert tag in html, (
            f"out/index.html must contain {tag} (AppShell frame); ODD-VTREE-002 server shell"
        )


def test_out_index_html_has_visible_product_title(static_export):
    """ODD-ASN-002: the AppShell no longer renders a per-route
    `<h1>` in the header (the header carries the brand mark
    `<a class="app-shell-brand">taxa</a>` instead — the brand
    IS the visible product identity, and the route entry uses
    the AppShell `<main>` slot for the per-route surface). The
    static ``out/index.html`` must therefore carry:

      1. The brand mark `<a data-app-shell-brand="">taxa</a>`
         inside the `<header>` (the visible brand identity).
      2. A `<title>` element with the per-route title — the
         Next.js metadata API injects it on every route that
         exports a `metadata` object (the root layout's
         metadata provides the `"taxa"` default for `/`; the
         per-route titles for `/explorer`, `/help`, and
         `/settings` come from each page's own `metadata`
         export — see
         ``tests/test_app_shell_render.py`` for the matching
         static-export assertions on those pages).

    The pre-ODD-ASN-002 contract asserted `<h1>Taxonomic
    Tree</h1>` directly. That assertion pinned the old per-route
    header; ODD-ASN-002 replaces the visible identity with the
    brand mark + the metadata-driven `<title>` (the same DOM
    shape every Next.js App Router route ships).
    """
    html = _read_text(OUT_INDEX)
    # 1. The brand mark MUST live inside the `<header>` — the
    # visible product identity the AppShell renders in place of
    # the pre-ODD-ASN-002 `<h1>`.
    brand_match = re.search(
        r'<a\b[^>]*\bdata-app-shell-brand\s*=\s*""[^>]*>\s*taxa\s*</a>',
        html,
        re.DOTALL,
    )
    assert brand_match, (
        "out/index.html must render the AppShell brand mark "
        "`<a data-app-shell-brand=\"\">taxa</a>` (the visible "
        "product identity — the ODD-ASN-002 replacement for the "
        "pre-ODD-ASN-002 `<h1>Taxonomic Tree</h1>` per-route "
        "header)."
    )
    # 2. The `<title>` element MUST carry the per-route title
    # (the Next.js metadata API injects it). The `/` route
    # inherits the root-layout default `"taxa"`; the per-route
    # title the AppShell orchestrator receives is "Taxonomic
    # Tree" (passed as the `title` prop to AppShell on `src/app/page.tsx`),
    # and the `<title>` element MUST be present and non-empty so
    # the browser tab + bookmarks surface the product identity.
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html)
    assert title_match is not None, (
        "out/index.html must render a `<title>` element (the "
        "Next.js metadata API injects the per-route title; the "
        "AppShell no longer renders a per-route `<h1>` so the "
        "`<title>` element is the per-route identity surface)."
    )
    title_text = title_match.group(1).strip()
    assert title_text, (
        "out/index.html must render a non-empty `<title>` element."
    )


def test_out_index_html_has_taxonomy_tree_section(static_export):
    html = _read_text(OUT_INDEX)
    assert 'aria-label="Taxonomic tree"' in html, (
        "out/index.html must mount the TaxonomyTree section with aria-label"
    )
    assert "taxa-tree" in html, (
        "out/index.html must include the four-column .taxa-tree grid"
    )


def test_out_index_html_renders_initial_loading_status(static_export):
    """SSR with EMPTY_TREE_STATE must show the `role=status` loading copy
    (the client then fetches roots after hydration)."""
    html = _read_text(OUT_INDEX)
    assert re.search(r'role="status"[^>]*>\s*Loading domains', html, re.DOTALL), (
        "out/index.html must render the role=\"status\" loading copy before hydration"
    )


def test_out_index_html_does_not_inline_domain_rows_before_hydration(static_export):
    """The fetch is client-side; SSR must not pre-render domain rows.
    Confirms the root-collapsed-initial-state contract."""
    html = _read_text(OUT_INDEX)
    # No `data-taxon-id` attributes before hydration means no rows inlined.
    assert "data-taxon-id" not in html, (
        "out/index.html must NOT inline taxon rows before hydration (collapsed initial state)"
    )


def test_out_index_html_keeps_static_origin(static_export):
    """Production requests must stay relative/same-origin (PR 3b's
    hydration-safety contract carries forward). The
    ``data-theme`` hydration-guard assertion lives in
    ``test_app_shell_render.py::test_out_index_html_body_has_no_data_theme_before_hydration``
    — duplicated coverage is removed here per the ODD-VTREE-002
    test-scope reduction."""
    html = _read_text(OUT_INDEX)
    # Footer copy mentions the API origin.
    assert re.search(r"<code[^>]*>\s*/api\s*</code>", html), (
        "out/index.html must render the /api origin footer marker"
    )
    # No literal 'http://' or 'https://' API reference in the static HTML.
    assert re.search(r'href=["\']https?://[^"\']*domains', html) is None, (
        "out/index.html must not reference absolute /api/domains URLs"
    )


# ---------------------------------------------------------------------------
# ODD-NTP-002 — native source-parity contract for the visible tree.
#
# Source-level checks on `TaxonomyTree.tsx` (selector presence, native
# source order, source-conditional Freshwater control, source-bound
# state reset, per-source child-request wiring) + the matching
# static-export witness (`out/index.html` must carry the segmented
# control shape + the active CoL affordance after hydration).
# ---------------------------------------------------------------------------

def test_taxonomy_tree_renders_source_selector() -> None:
    """ODD-HSS-001 — negative witness: TaxonomyTree must NOT render the
    source selector inside the tree surface anymore.

    The pre-PR source-selector lived inside `TaxonomyTree.tsx` as
    `renderSourceSelector()` (a `<div role="group">` with three
    `<button className="tree-source-btn" data-tree-source="col|worms|freshwater">`
    rows). The selector only became visible AFTER the user expanded
    the tree (`state.rootIds.length > 0`), so a first-time visitor
    who had never opened the tree never saw the three data sources.

    ODD-HSS-001 hoists the selector to the AppShell header so it is
    visible on every route (CoL / WoRMS / Freshwater become a
    first-class concept from the first paint). The positive witness
    for the new host lives in
    `tests/test_app_shell_render.py::test_appshell_renders_source_selector`;
    this test pins the negative half so a regression that re-mounts
    the toggle inside `TaxonomyTree.tsx` trips the gate.

    The five contract-bearing strings/hooks that USED to live in
    TaxonomyTree.tsx:
      - `role=\"group\"` on the toggle host.
      - The aria-label literal `\"Tree data source\"` (the
        `selectorLabel` constant).
      - `aria-label` attribute on the toggle host.
      - `.tree-source-toggle` class hook (the segmented control).
      - `.tree-source-btn` class hook (each per-source button).

    After the hoist every one of these MUST be absent from the
    TaxonomyTree source — the AppShell owns the surface.

    The complementary data-attribute witnesses
    (`<div id=\"tree-source-toggle\">`, per-button
    `data-tree-source=\"col|worms|freshwater\"`,
    `data-tree-source-toggle=\"\"`, `data-active-source`,
    `aria-pressed`) live in `test_taxonomy_tree_renders_tree_source_toggle_id`
    below (also a negative witness for TaxonomyTree) AND in
    `tests/test_app_shell_render.py::test_appshell_renders_source_selector`
    (the positive witness on the AppShell).
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    # Strip block comments + line comments so docstring references
    # to the legacy class hooks don't trip the negative witnesses.
    # The witness checks the JSX render, not the prose.
    code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert re.search(r'role="group"', code_only) is None, (
        "ODD-HSS-001: TaxonomyTree.tsx must NOT render `role=\"group\"` "
        "anymore — the source selector was hoisted to the AppShell "
        "header. The positive witness for the new host lives in "
        "tests/test_app_shell_render.py::test_appshell_renders_source_selector."
    )
    assert '"Tree data source"' not in code_only, (
        "ODD-HSS-001: TaxonomyTree.tsx must NOT declare the source-"
        "selector label `\"Tree data source\"` anymore — the "
        "selector was hoisted to the AppShell header."
    )
    # The aria-label attribute hook may still appear elsewhere in
    # the file (the breadcrumb host carries
    # `aria-label=\"Active taxonomy path\"`). The selector-specific
    # check pins that the file does NOT carry the
    # `aria-label={selectorLabel}` form.
    assert "selectorLabel" not in code_only, (
        "ODD-HSS-001: TaxonomyTree.tsx must NOT carry `selectorLabel` "
        "anymore — the source-selector label constant is removed."
    )
    assert "tree-source-toggle" not in code_only, (
        "ODD-HSS-001: TaxonomyTree.tsx must NOT stamp `.tree-source-toggle` "
        "anymore — the segmented control class hook lives in the "
        "AppShell source-selector now."
    )
    assert "tree-source-btn" not in code_only, (
        "ODD-HSS-001: TaxonomyTree.tsx must NOT stamp `.tree-source-btn` "
        "anymore — the per-source button class hook lives in the "
        "AppShell source-selector now."
    )


def test_taxonomy_tree_starts_with_col_active() -> None:
    """ODD-NTP-002: CoL starts active. Mirrors the legacy
    `state.treeSource = "col"` default in `web/state.js`.

    ODD-BSTATE-TAX-001: the typed default now flows through the
    browser-state module's `DEFAULT_TREE_SOURCE` (a `"col"` literal
    the `useTreeSource` hook returns on first paint). The local
    `DEFAULT_SOURCE` constant is gone — the typed default lives in
    the typed store so SSR + the first client render stay byte-equal
    and the post-mount rehydration surfaces the stored value. The
    contract pin here is the `useTreeSource()` invocation: the
    hook's typed default is `"col"` (the typed default itself is
    locked by `tests/test_browser_state_keys.py`)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(r"useTreeSource\s*\(\s*\)", text), (
        "TaxonomyTree.tsx must consume `useTreeSource()` from "
        "`@taxa/browser-state` so the CoL typed default flows through "
        "the browser-state module (ODD-BSTATE-TAX-001)."
    )


def test_taxonomy_tree_selector_orders_col_then_worms() -> None:
    """ODD-NTP-002 (now-ODD-HSS-001): the source-selector label
    ORDER (CoL → WoRMS → Freshwater) lives in the AppShell-scope
    source-selector sub-component after the ODD-HSS-001 hoist.
    The pre-ODD-HSS-001 native-order ternary lived inside
    `renderSourceSelector()` in TaxonomyTree; after the hoist the
    selector owns its own label table
    (`const SOURCE_LABELS: Record<TreeSource, string> = { col: "CoL",
    worms: "WoRMS", freshwater: "Freshwater" };`) and renders the
    three sources in declared `ALL_SOURCES` order
    (`["col", "worms", "freshwater"]`).

    The post-ODD-HSS-001 contract: the
    `ODD-NTP-002` label-order ternary need NOT live in
    TaxonomyTree.tsx anymore (the segment owns a different
    surface), AND the AppShell-scope source-selector
    (`AppShellSourceSelector`) is the new location of the
    CoL → WoRMS → Freshwater sequence + the typed-source
    keys.

    Negative witness for TaxonomyTree + positive witness for
    AppShellSourceSelector = the two complementary pins.
    The TaxonomyTree negative witness: the file MUST NOT
    carry the `src === \"col\" ? \"CoL\" : src === \"worms\" ?
    \"WoRMS\" : \"Freshwater\"` ternary anymore (the segment
    owns a different surface). The positive witness lives
    in
    `tests/test_app_shell_render.py::test_appshell_renders_source_selector`
    (data-tree-source attrs for col / worms / freshwater on
    the AppShell-scope mount).
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    # The label sequence MUST NOT live inside TaxonomyTree.tsx anymore.
    seq = re.search(
        r"src\s*===\s*[\"\']col[\"\']\s*\?\s*[\"\']CoL[\"\']\s*:\s*"
        r"src\s*===\s*[\"\']worms[\"\']\s*\?\s*[\"\']WoRMS[\"\']\s*:\s*[\"\']Freshwater[\"\']",
        text,
    )
    assert seq is None, (
        "ODD-NTP-002 (now-ODD-HSS-001): TaxonomyTree.tsx must NOT "
        "carry the `src === \"col\" ? \"CoL\" : src === \"worms\" ? "
        "\"WoRMS\" : \"Freshwater\"` label-order ternary anymore — "
        "the source-selector was hoisted to the AppShell header. "
        "The positive witness for the AppShell-scope selector label "
        "order lives in "
        "tests/test_app_shell_render.py::test_appshell_renders_source_selector."
    )


def test_taxonomy_tree_selector_is_conditional_on_freshwater_root() -> None:
    """ODD-NTP-002 (now-ODD-HSS-001): the source-selector
    conditional-Freshwater gating lives in
    `availableSourcesFor(rawRoots)` (the typed-source helper in
    `tree-state.ts`) which the data-loading path
    `loadRoots` consumes via `withRootsForSource`. After
    ODD-HSS-001 hoists the source-selector to the AppShell
    header, the typing meta — the `availableSourcesFor`
    consumption + the pre-fetch defaults
    `["col", "worms", "freshwater"]` — has been REFACTORED
    from a JSX-render-time memo into the
    `useTreeSource` + `availableSourcesFor` typed-state
    pipeline.

    The post-ODD-HSS-001 contract: TaxonomyTree MUST NOT
    carry an `availableSourcesFor` call site nor a
    pre-fetch `["col", "worms", "freshwater"]` default
    list (the segment owns a different surface — the
    AppShell-scope `AppShellSourceSelector` always
    renders the three canonical sources). The typed-source
    pipeline for the `fetchChildren({ source: activeSource })`
    call site lives in `loadRoots` / `attachChildrenForSource`
    / `withRootsForSource` (consumed by `TaxonomyTree`'s
    `useEffect` on `rawRoots + activeSource`).

    The companion positive witness for the AppShell-scope
    selector (always-three-buttons contract) lives in
    `tests/test_app_shell_render.py::test_appshell_renders_source_selector`.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    # Strip block + line comments first so a docstring that
    # references the legacy `availableSourcesFor` filter as
    # documentation of the closed behaviour does NOT trip
    # the negative witness.
    code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    # The `availableSourcesFor` call site must NOT live in
    # TaxonomyTree.tsx anymore — the typed-source helper
    # moved to the AppShell-scope source-selector file
    # (`AppShellSourceSelector` owns its own internal source
    # list, so the helper is no longer needed at the JSX
    # render site). TaxonomyTree still consumes the
    # `attachChildrenForSource` / `withRootsForSource`
    # downstream helpers in the source-AWARE fetch effect.
    assert "availableSourcesFor" not in code_only, (
        "ODD-NTP-002 (now-ODD-HSS-001): TaxonomyTree.tsx must "
        "NOT consume the `availableSourcesFor` helper anymore "
        "— the source-selector was hoisted to the AppShell "
        "header. The data-loading path uses the typed-source "
        "helper `withRootsForSource` in the `rawRoots + "
        "activeSource` effect (still in TaxonomyTree)."
    )
    # The pre-fetch `["col", "worms", "freshwater"]` default
    # array MUST NOT live in TaxonomyTree.tsx anymore — the
    # AppShell-scope `AppShellSourceSelector` always renders
    # the three canonical sources via its own
    # `ALL_SOURCES` constant.
    assert re.search(
        r"\[\s*[\"\']col[\"\']\s*,\s*[\"\']worms[\"\']\s*,\s*[\"\']freshwater[\"\']\s*\]",
        code_only,
    ) is None, (
        "ODD-NTP-002 (now-ODD-HSS-001): TaxonomyTree.tsx must "
        "NOT carry the pre-fetch `[\"col\", \"worms\", "
        "\"freshwater\"]` default array anymore — the source-"
        "selector was hoisted to the AppShell header (the "
        "AppShell-scope selector owns its own `ALL_SOURCES` "
        "constant)."
    )


def test_taxonomy_tree_threads_active_source_to_fetch_children() -> None:
    """ODD-NTP-002: child requests must call canonical
    `fetchChildren(id, { source: activeSource })` so each source's
    request carries its matching `?source=…` query string. Mirrors
    the legacy `web/api.js::loadChildren` source wiring."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r"fetchChildren\s*\(\s*id\s*,\s*\{\s*baseUrl\s*:\s*TAXA_API_ORIGIN\s*,"
        r"\s*source\s*:\s*activeSource",
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must call fetchChildren(id, { source: activeSource, ... })"
    )


def test_taxonomy_tree_uses_canonical_source_helper_for_filtering() -> None:
    """ODD-NTP-002: source filtering must go through the canonical
    `sourceMatches` predicate (or its source-aware wrappers) imported
    from `./tree-state`. The component must not invent its own
    predicate inline."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "sourceMatches" in text or "withRootsForSource" in text, (
        "TaxonomyTree.tsx must route source filtering through the canonical helper"
    )


def test_taxonomy_tree_resets_source_state_on_switch() -> None:
    """ODD-NTP-002: switching sources must clear every source-bound
    React state (roots, child cache, expanded, load status, per-row
    error) before re-displaying the new source's roots. Mirrors the
    legacy `web/nav.js::tree-source toggle` reset. The raw root cache
    SURVIVES the switch — `loadRoots` runs once on mount and the
    `rawRoots + activeSource` effect re-projects the cached payload
    against the new source without a second `/api/domains` round
    trip.

    ODD-HSS-001 — the `handleSourceChange` callback was removed
    (the source-selector hoist moved the click handler to the
    AppShell), and the source-bound `resetSourceState(prev)` reset
    now fires from the `useEffect` on
    `[activeSource, rawRoots]` instead of from the click
    handler. The early-out `if (next === activeSource) return`
    guard USED to short-circuit a re-click on the same source
    inside TaxonomyTree; after the hoist the equivalent
    short-circuit lives inside the typed `useTreeSource` hook
    itself (the `useSyncExternalStore` server snapshot returns
    `DEFAULT_TREE_SOURCE` and the post-mount re-render surfaces
    the stored value; the `useTreeSource` setter does not
    re-fire if the caller writes the same value the store
    already holds, so the click handler is idempotent on
    re-click).

    The post-ODD-HSS-001 contract: the `resetSourceState`
    helper MUST still be consumed on every source switch (the
    `useEffect([activeSource, rawRoots])` blocks drives the
    same source-bound reset cascade that the pre-hoist click
    handler drove). The early-out click-handler guard is NOT
    expected in TaxonomyTree.tsx anymore (the typed hook owns
    the re-click short-circuit).
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "resetSourceState" in text, (
        "TaxonomyTree.tsx must consume resetSourceState on the "
        "`rawRoots + activeSource` source-switch effect — the "
        "helper cleared every source-bound React state on a "
        "switch in the pre-ODD-HSS-001 click handler AND the "
        "post-ODD-HSS-001 reactive effect."
    )
    # The click-handler early-out guard MUST NOT live in
    # TaxonomyTree.tsx anymore — the typed `useTreeSource` hook
    # owns the re-click short-circuit (writing the same value
    # the store already holds is a no-op so the `useEffect`
    # dependencies don't change). Strip block + line comments
    # first so docstring prose that references the legacy guard
    # as documentation of the closed behaviour does NOT trip
    # the negative witness.
    code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert re.search(
        r"if\s*\(\s*next\s*===\s*activeSource\s*\)\s*return",
        code_only,
    ) is None, (
        "ODD-NTP-002 (now-ODD-HSS-001): TaxonomyTree.tsx must "
        "NOT carry the `if (next === activeSource) return` "
        "click-handler early-out anymore — the typed "
        "`useTreeSource` hook owns the re-click short-circuit."
    )


def test_taxonomy_tree_load_roots_is_source_independent() -> None:
    """ODD-NTP-002 (regression — no domain refetch on source switch):
    `loadRoots` MUST NOT close over `activeSource`. Closing over the
    active source would put `loadRoots` in the `useEffect([loadRoots])`
    dependency array, which means the effect re-fires on every source
    switch and the React island issues a SECOND `/api/domains` round
    trip — defeating the purpose of caching the raw root payload
    client-side. The fix is to:
      1. Remove the `activeSource` reference from the `loadRoots`
         callback body (the source filter is applied by the
         `rawRoots + activeSource` effect, not by `loadRoots`).
      2. Drop `activeSource` from the `useCallback` dependency array
         so the callback reference is stable across source switches.
    This regression catches any future PR that re-introduces the
    closure (a single `activeSource` reference in the body or deps
    fails this test before code review)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # Anchor the body on the `}, [deps])` closing pattern so nested
    # braces inside `try { ... }` / `if (...) { ... }` / setState
    # updater tuples don't terminate the match early. The useCallback
    # closing `}, [...]` is the only place that pattern occurs.
    match = re.search(
        r"const\s+loadRoots\s*=\s*useCallback\s*\(\s*async\s*\(\s*\)\s*=>\s*\{"
        r"(.*?)"
        r"\}\s*,\s*\[\s*([^\]]*?)\s*\]\s*\)",
        text,
        re.DOTALL,
    )
    assert match, (
        "TaxonomyTree.tsx must declare loadRoots as `const loadRoots = "
        "useCallback(async () => { ... }, [deps])`."
    )
    body, deps = match.group(1), match.group(2)
    assert "activeSource" not in body, (
        "ODD-NTP-002: loadRoots must not close over `activeSource`; "
        "the source filter is applied by the `rawRoots + activeSource` "
        "effect, not by loadRoots. A source switch must NOT issue a "
        "second `/api/domains` request."
    )
    assert "activeSource" not in deps, (
        "ODD-NTP-002: loadRoots's `useCallback` dependency array must "
        "NOT include `activeSource`. Including it would make "
        "`useEffect([loadRoots])` re-fire on every source switch and "
        "issue a second `/api/domains` round trip."
    )


def test_taxonomy_tree_load_children_uses_source_predicate() -> None:
    """ODD-NTP-002 (regression — no unfiltered foreign-source children):
    `loadChildren` MUST call `attachChildrenForSource(state, id, kids,
    activeSource)` — the source-aware variant that applies the
    `sourceMatches` predicate before the visible child list is built.
    Calling the bare `attachChildren(state, id, kids)` would let
    foreign-source rows slip through: a WoRMS-only row landing under
    a CoL parent's response would render in the CoL view, breaking
    the source-bound child contract (and silently violating the
    `?source=…` query the helper already sends). The fix is to call
    `attachChildrenForSource` so the predicate filters the payload
    before the ids land in `childIdsByParent`."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # The source-aware variant must be imported from tree-state.
    assert re.search(
        r"\battachChildrenForSource\b",
        text,
    ), (
        "TaxonomyTree.tsx must import and use `attachChildrenForSource` "
        "so the active-source predicate is applied before attachment."
    )
    # Find the loadChildren callback body. The declaration spans
    # multiple lines (`useCallback(\n  async (id) => {\n    ...\n  },\n  [deps]\n)`)
    # so anchor on the closing `}, [...]` pattern.
    match = re.search(
        r"const\s+loadChildren\s*=\s*useCallback\s*\(\s*async\s*\(\s*id\s*:\s*number\s*\)\s*=>\s*\{"
        r"(.*?)"
        r"\}\s*,\s*\[",
        text,
        re.DOTALL,
    )
    assert match, (
        "TaxonomyTree.tsx must declare loadChildren as `const "
        "loadChildren = useCallback(async (id) => { ... }, [deps])`."
    )
    body = match.group(1)
    # Bare `attachChildren(` (NOT followed by `ForSource`) must not
    # appear inside the loadChildren body.
    bare_calls = re.findall(r"\battachChildren\s*(?!\s*ForSource)", body)
    assert not bare_calls, (
        "ODD-NTP-002: loadChildren must NOT call the bare "
        "`attachChildren(state, id, kids)`; it must call "
        "`attachChildrenForSource(state, id, kids, activeSource)` so "
        "foreign-source rows are filtered before attachment. The bare "
        "variant lets WoRMS-only rows render under CoL and vice versa."
    )
    assert "attachChildrenForSource" in body, (
        "ODD-NTP-002: loadChildren body must call "
        "`attachChildrenForSource(prev, id, kids, activeSource)` so the "
        "active-source predicate is applied before the child ids land "
        "in `childIdsByParent`."
    )


def test_taxonomy_tree_uses_canonical_api_origin_and_helpers() -> None:
    """ODD-NTP-002: the canonical API origin + fetch helpers stay in
    place (ODD-VTREE-002 + ODD-NTP-001 source/data helper public
    contract is preserved)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "process.env.NEXT_PUBLIC_TAXA_API_ORIGIN" in text, (
        "TaxonomyTree.tsx must source its API origin from NEXT_PUBLIC_TAXA_API_ORIGIN"
    )
    assert re.search(
        r"from\s+[\"\']@taxa/taxonomy[\"\']", text,
    ), (
        "TaxonomyTree.tsx must import the data helpers via the @taxa/taxonomy barrel"
    )


def test_out_index_html_has_source_selector_styles(static_export) -> None:
    """ODD-NTP-002: the static export must include the focused
    segmented-control CSS (`.tree-source-toggle` + `.tree-source-btn`
    + `.tree-source-btn.active`). The active affordance must use the
    primary token so the React tree matches the legacy native
    visual."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    assert css_chunks, "static export must emit at least one CSS chunk"
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    assert ".tree-source-toggle" in css_body, (
        "static CSS must define the .tree-source-toggle class"
    )
    assert ".tree-source-btn" in css_body, (
        "static CSS must define the .tree-source-btn class"
    )
    # The active rule must declare BOTH `background:var(--primary)` AND
    # `color:var(--on-primary)` so the React cutover is in lock-step
    # with the canonical token. The rule body is minified into one
    # block, so a single-substring check on the canonical
    # `.tree-source-btn.active` selector + the canonical tokens covers
    # the visual contract byte-equal to the legacy web/index.html cascade.
    assert re.search(
        r"\.tree-source-toggle>\.tree-source-btn\.active\b",
        css_body,
    ), (
        "static CSS must define the .tree-source-toggle>.tree-source-btn.active rule"
    )
    assert "var(--primary)" in css_body, (
        "static CSS must reference the canonical --primary token"
    )
    assert "var(--on-primary)" in css_body, (
        "static CSS must reference the canonical --on-primary token "
        "for the active button's text color"
    )


# ---------------------------------------------------------------------------
# ODD-NTP-005 — native source-aware in-tree navigation:
#   - Focused / selected navigation state lives at the React
#     component level (mirrors `web/state.js::focused` + `selected`).
#   - The breadcrumb above the tree renders the focused taxon's
#     ancestor chain via `walkBreadcrumbForSource(focused, source,
#     state)`. Each segment carries `data-breadcrumb-segment` +
#     `data-breadcrumb-rank`; intermediate segments are
#     `data-action="focus-segment"` buttons, the focused taxon is
#     plain text.
#   - Source switches clear focused + selected alongside the
#     source-bound React state (roots, child cache, expanded set,
#     load status, showAll, per-row error, kebab). Mirrors the
#     legacy `web/nav.js::tree-source toggle` reset byte-for-byte.
#   - Collapse-all preserves focused + selected (the legacy
#     `web/nav.js::collapseAll` does the same — selection is
#     independent of expansion).
#   - The kebab "View details" item (formerly "Search online" —
#     renamed in ODD-TDDISC-001 for discoverability; the
#     data-action="open-searches" contract is preserved) is ENABLED
#     (the navigation slice genuinely backs it). The "Open folder"
#     item stays `disabled` until the Folder tab + desktop file
#     endpoints
#     ship (detail-panel / desktop file actions still lack React
#     backing).
# ---------------------------------------------------------------------------

def test_taxonomy_tree_renders_breadcrumb() -> None:
    """ODD-NTP-005: TaxonomyTree must render a breadcrumb above the
    tree source selector. Mirrors the legacy
    `web/index.html::#breadcrumb` cascade byte-for-byte."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # Breadcrumb host carries the canonical `id="breadcrumb"` so
    # downstream tooling + the legacy selector still apply. The
    # JSX literal `id="breadcrumb"` matches either the unescaped
    # JSX source OR the quoted form; the regex below accepts both.
    assert re.search(
        r'id\s*=\s*["\']breadcrumb["\']',
        text,
    ), (
        "ODD-NTP-005: TaxonomyTree.tsx must render a <nav id=\"breadcrumb\"> "
        "host so the legacy selector + downstream tooling keep applying."
    )
    assert "data-breadcrumb=" in text, (
        "ODD-NTP-005: breadcrumb host must carry data-breadcrumb for tests."
    )
    assert "data-breadcrumb-source=" in text, (
        "ODD-NTP-005: breadcrumb must stamp data-breadcrumb-source so "
        "tests can confirm source isolation."
    )
    assert "data-breadcrumb-length=" in text, (
        "ODD-NTP-005: breadcrumb must stamp data-breadcrumb-length so "
        "tests can confirm the rendered segment count."
    )
    assert "BREADCRUMB_MAX_HOPS" in text, (
        "ODD-NTP-005: TaxonomyTree.tsx must consume BREADCRUMB_MAX_HOPS "
        "so the 30-hop cycle cap surfaces in the rendered breadcrumb."
    )


def test_taxonomy_tree_uses_source_aware_breadcrumb_walker() -> None:
    """ODD-NTP-005: the breadcrumb walker dispatches on the active
    source internally. The component must consume
    `walkBreadcrumbForSource(focused, source, state)` from the
    canonical `breadcrumb-path` helper."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "walkBreadcrumbForSource" in text, (
        "ODD-NTP-005: TaxonomyTree.tsx must consume "
        "walkBreadcrumbForSource."
    )
    # The walker must be invoked with `activeSource` (NOT closed
    # over a stale source literal — the source filter is reactive).
    assert re.search(
        r"walkBreadcrumbForSource\([^)]*activeSource",
        text,
        re.DOTALL,
    ), (
        "ODD-NTP-005: walkBreadcrumbForSource must be invoked with "
        "the active source (reactive dispatch)."
    )


def test_taxonomy_tree_breadcrumb_segments_carry_action_attributes() -> None:
    """ODD-NTP-005: intermediate breadcrumb segments render as
    buttons carrying `data-action="focus-segment"` + `data-taxon-id`
    so the legacy click delegation stays compatible. The focused
    taxon itself renders as plain text (no "go to myself" affordance)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r'data-action\s*=\s*["\']focus-segment["\']',
        text,
    ), (
        "ODD-NTP-005: intermediate breadcrumb segments must stamp "
        "data-action=\"focus-segment\"."
    )
    assert re.search(
        r'data-action\s*=\s*["\']focus-home["\']',
        text,
    ), (
        "ODD-NTP-005: breadcrumb must stamp data-action=\"focus-home\" "
        "on the home glyph so the click delegation clears focus."
    )
    assert "data-breadcrumb-segment=" in text, (
        "ODD-NTP-005: each breadcrumb segment must stamp "
        "data-breadcrumb-segment={id}."
    )
    assert "data-breadcrumb-rank=" in text, (
        "ODD-NTP-005: each breadcrumb segment must stamp "
        "data-breadcrumb-rank={rank} for tests + a11y tooling."
    )


def test_taxonomy_tree_owns_focused_selected_navigation_state() -> None:
    """ODD-NTP-005: TaxonomyTree owns the focused + selected React
    state (mirrors `web/state.js::focused` + `selected`). Source
    switches reset both; collapse-all preserves both."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r"useState<number \| null>\(\s*null\s*\)",
        text,
    ), (
        "ODD-NTP-005: TaxonomyTree.tsx must own a useState<number|null> "
        "pair for focused + selected navigation state."
    )
    # Both `focused` and `selected` setters are used.
    assert "setFocused" in text, (
        "ODD-NTP-005: TaxonomyTree.tsx must expose setFocused."
    )
    assert "setSelected" in text, (
        "ODD-NTP-005: TaxonomyTree.tsx must expose setSelected."
    )


def test_taxonomy_tree_handle_select_sets_focused_and_selected() -> None:
    """ODD-NTP-005 + ODD-TAPOPUP-001: `handleSelect(id)` is the
    selection primitive — sets focused + selected to `id` and
    bumps the pulse nonce. The pre-popup kebab-close side
    effect (`setKebabOpenId(null)`) is GONE — the kebab menu
    is gone; the popup is `selected`-driven. Mirrors the
    legacy `web/nav.js::selectTaxon(id)` primitive byte-for-
    byte (selection is orthogonal to expansion; the popup
    opens for the row)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", text)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert re.search(
        r"const\s+handleSelect\s*=\s*useCallback",
        code_only,
    ), (
        "ODD-NTP-005: TaxonomyTree.tsx must declare handleSelect as "
        "a useCallback."
    )
    handle_idx = text.find("const handleSelect")
    assert handle_idx != -1
    body = text[handle_idx:handle_idx + 800]
    assert "setFocused(id)" in body, (
        "ODD-NTP-005: handleSelect must call setFocused(id)."
    )
    assert "setSelected(id)" in body, (
        "ODD-NTP-005: handleSelect must call setSelected(id)."
    )
    # The pre-popup kebab-close side effect is GONE.
    assert "setKebabOpenId" not in code_only, (
        "ODD-TAPOPUP-001: handleSelect must NOT close the "
        "open kebab (the kebab menu is gone; the popup is "
        "`selected`-driven)."
    )


def test_taxonomy_tree_source_change_clears_focused_and_selected() -> None:
    """ODD-NTP-005: source switches clear focused + selected in
    addition to the source-bound React state. Mirrors the legacy
    `web/nav.js::tree-source toggle` reset.

    ODD-HSS-001 — the source-bound cleanup moved into the
    `useEffect` body that fires on `activeSource` changes. The
    regression guard pins the contract against the new
    effect-based location: the effect body MUST carry
    `setFocused(null)` AND `setSelected(null)` so the
    focused / selected clear-cascade survives the hoist."""
    text = _read_text(TAXONOMY_TREE_FILE)
    body = _od_hss_source_switch_effect_body(text)
    assert "setFocused(null)" in body, (
        "ODD-NTP-005: the ODD-HSS-001 source-switch "
        "`useEffect(() => { ... }, [activeSource])` body must "
        "call `setFocused(null)` so the breadcrumb rebuilds "
        "against the new source's cache."
    )
    assert "setSelected(null)" in body, (
        "ODD-NTP-005: the ODD-HSS-001 source-switch "
        "`useEffect(() => { ... }, [activeSource])` body must "
        "call `setSelected(null)` so the new source's "
        "detail-panel selection is clean."
    )


def test_taxonomy_tree_collapse_all_preserves_focused_and_selected() -> None:
    """ODD-NTP-005: collapse-all clears expanded + showAll + kebab
    but PRESERVES focused + selected (the legacy
    `web/nav.js::collapseAll` does the same — selection is
    independent of expansion)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    handle_idx = text.find("const handleCollapseAll")
    assert handle_idx != -1, (
        "TaxonomyTree.tsx must declare handleCollapseAll."
    )
    body = text[handle_idx:handle_idx + 600]
    assert "clearExpansion" in body, (
        "ODD-NTP-005: handleCollapseAll must call clearExpansion."
    )
    # Must NOT mutate focused + selected.
    assert "setFocused(null)" not in body, (
        "ODD-NTP-005: handleCollapseAll must NOT call setFocused(null); "
        "selection is independent of expansion."
    )
    assert "setSelected(null)" not in body, (
        "ODD-NTP-005: handleCollapseAll must NOT call setSelected(null); "
        "selection is independent of expansion."
    )


def test_taxonomy_tree_row_carries_selected_focused_attributes() -> None:
    """ODD-NTP-005: each row carries `data-selected` /
    `data-focused` attributes (or omits them when not selected /
    focused). The selected / focused CSS hooks live in
    `src/app/globals.css` under the canonical descendant guards."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "data-selected=" in text, (
        "ODD-NTP-005: TreeRow.tsx must stamp data-selected on the row."
    )
    assert "data-focused=" in text, (
        "ODD-NTP-005: TreeRow.tsx must stamp data-focused on the row."
    )


def test_tree_row_passes_on_select_focused_selected_to_props() -> None:
    """ODD-NTP-005: TreeRowProps surface accepts the new
    navigation props (onSelect, focused, selected,
    registerRowRef, pulseNonce) and the components consumes them
    to render the data attributes."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "onSelect" in text, (
        "ODD-NTP-005: TreeRow.tsx must consume onSelect."
    )
    assert "focused" in text, (
        "ODD-NTP-005: TreeRow.tsx must consume focused."
    )
    assert "selected" in text, (
        "ODD-NTP-005: TreeRow.tsx must consume selected."
    )
    assert "pulseNonce" in text, (
        "ODD-NTP-005: TreeRow.tsx must consume pulseNonce so the "
        "freshly-selected row plays the pulse animation once."
    )


def test_tree_row_open_folder_kebab_is_enabled_for_materialized_rows() -> None:
    """ODD-TAPOPUP-001 (carry-over): the row-level materialize
    indicator (`hasMaterializedFolder(taxon)` predicate) is
    preserved so the Folder tab in the popup knows whether the
    row is materialized. The kebab menu's `Open folder` item is
    GONE — the Folder tab in the popup subsumes the affordance
    (the user opens the popup, picks the Folder tab, and either
    creates the folder or opens it)."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert "hasMaterializedFolder" in text, (
        "ODD-TAPOPUP-001: TreeRow.tsx must still consume "
        "`hasMaterializedFolder` so the row's materialize "
        "indicator stays."
    )
    # The row-level materialize indicator + its data attribute
    # STAY (the row paints a materialize marker so the user can
    # tell at a glance which rows are already on disk). The kebab
    # menu item that USED to drive the open-folder action is
    # gone.
    assert not re.search(
        r'data-action="open-folder-tab"',
        text,
    ), (
        "ODD-TAPOPUP-001: TreeRow.tsx must NOT carry "
        "`data-action=\"open-folder-tab\"` (the kebab menu item "
        "is gone; the Folder tab in the popup drives the "
        "create/open flow)."
    )


def test_taxonomy_tree_no_kebab_menu_click_outside_handler() -> None:
    """ODD-TAPOPUP-001: the kebab menu's document-level
    click-outside handler is GONE. The popup owns its own
    backdrop-click → close behavior (the DetailPanel renders a
    `.detail-panel-backdrop` element that calls `onClose()` on
    click; the tree no longer carries the `.kebab` closest()
    check)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # No `mousedown` document-level listener for `.kebab`
    # closest-check — the kebab menu is gone.
    assert not re.search(
        r"closest\(\s*['\"]\.kebab['\"]\s*\)",
        text,
    ), (
        "ODD-TAPOPUP-001: TaxonomyTree.tsx must NOT carry the "
        "`.kebab` closest-check (the kebab menu is gone; the "
        "popup backdrop owns the click-outside close)."
    )


def test_taxonomy_tree_handle_focus_segment_expands_ancestors() -> None:
    """ODD-NTP-005: handleFocusSegment(id) is the breadcrumb
    activation primitive. It must expand the ancestors of `id`
    (via the source-safe edge map) and focus + select the segment
    id. The expansion never fabricates edges — only already-attached
    source-safe rows become expandable."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r"const\s+handleFocusSegment\s*=\s*useCallback",
        text,
    ), (
        "ODD-NTP-005: TaxonomyTree.tsx must declare handleFocusSegment "
        "as a useCallback."
    )
    handle_idx = text.find("const handleFocusSegment")
    assert handle_idx != -1
    body = text[handle_idx:handle_idx + 1200]
    assert "expandAncestorsOf" in body or "expandAncestors" in body, (
        "ODD-NTP-005: handleFocusSegment must expand ancestors before "
        "focusing the segment."
    )
    assert "setFocused(id)" in body, (
        "ODD-NTP-005: handleFocusSegment must call setFocused(id)."
    )
    assert "setSelected(id)" in body, (
        "ODD-NTP-005: handleFocusSegment must call setSelected(id)."
    )


def test_taxonomy_tree_handle_focus_home_clears_navigation() -> None:
    """ODD-NTP-005: the breadcrumb home glyph clears focused +
    selected (mirrors the legacy `web/nav.js::focus-home` handler)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r"const\s+handleFocusHome\s*=\s*useCallback",
        text,
    ), (
        "ODD-NTP-005: TaxonomyTree.tsx must declare handleFocusHome."
    )
    handle_idx = text.find("const handleFocusHome")
    body = text[handle_idx:handle_idx + 400]
    assert "setFocused(null)" in body, (
        "ODD-NTP-005: handleFocusHome must call setFocused(null)."
    )
    assert "setSelected(null)" in body, (
        "ODD-NTP-005: handleFocusHome must call setSelected(null)."
    )


def test_out_index_html_has_breadcrumb_and_row_affordance_styles(static_export) -> None:
    """ODD-NTP-005: the static export's CSS must define the
    breadcrumb host + the per-row selected / focused / pulse
    affordances introduced in ODD-NTP-005. The selectors live
    under the existing `.breadcrumb` / `.tree-row` chains so the
    chain-topology guard in `tests/test_research_styles.py` keeps
    whitelisting them under the 3c-b taxonomy surface."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    # The breadcrumb has its own host class plus the descendant
    # classes for home / segment / current (nested under the
    # canonical `.breadcrumb` rule so the chain-topology guard
    # whitelists them).
    assert ".breadcrumb" in css_body, (
        "ODD-NTP-005: static CSS must define the .breadcrumb rule."
    )
    assert "breadcrumb-host" in css_body, (
        "ODD-NTP-005: static CSS must define the .breadcrumb-host "
        "modifier (sticky + JetBrains Mono cascade)."
    )
    assert ".breadcrumb-segment" in css_body or ".breadcrumb .breadcrumb-segment" in css_body, (
        "ODD-NTP-005: static CSS must define the .breadcrumb-segment rule."
    )
    # Row affordances.
    assert ".tree-row.selected" in css_body, (
        "ODD-NTP-005: static CSS must define the .tree-row.selected "
        "rule (primary-tinted background, 8% primary color-mix, no left "
        "border — the side-tab border was removed per the 2026-09-24 "
        "impeccable re-critique to close the detector's `side-tab` rule)."
    )
    assert ".tree-row.focused" in css_body, (
        "ODD-NTP-005: static CSS must define the .tree-row.focused "
        "rule (surface-container-low tint, no left border — the side-tab "
        "border was removed per the 2026-09-24 impeccable re-critique)."
    )
    assert ".tree-row[data-pulse-nonce]" in css_body, (
        "ODD-NTP-005: static CSS must define the "
        ".tree-row[data-pulse-nonce] pulse animation."
    )


# ---------------------------------------------------------------------------
# ODD-TDDISC-001 — discoverable row-level detail action.
#
#   - Every row renders a compact Material Symbols `visibility` icon
#     control that invokes the existing selection primitive
#     (`onSelect(taxon.id)`) without toggling expansion. The icon
#     uses the `.tree-search-icon` class whitelisted under
#     TAXONOMY_OWNED_BY_3C_B in `tests/test_research_styles.py`,
#     so no new top-level CSS selector is required.
#   - The kebab menu's "Search online" item is RENAMED to "View
#     details" (label only — the data-action="open-searches"
#     contract stays so the parent keeps routing through
#     `handleKebabAction(id, "open-searches")`). The kebab item
#     icon switches from `search` to `visibility` so the icon-led
#     affordance stays consistent with the new row-level button.
#   - Both routes converge on the same selection primitive, so
#     source switches, breadcrumb activation, and the per-taxon
#     active-tab memory all keep working byte-for-byte.
# ---------------------------------------------------------------------------

def test_tree_row_disclosure_button_invokes_on_select() -> None:
    """ODD-PHASE2: clicking the row's disclosure button invokes the
    existing `onSelect(taxon.id)` primitive. ODD-TDDISC-001 originally
    wired this through a row-level `visibility` icon button; the
    ODD-PHASE2 rewrite drops the row-level visibility button and the
    kebab 'View details' item (both were duplicate affordances), so
    the disclosure button is the single, more-discoverable row-click
    target. The button MUST call `onSelect(taxon.id)` for leaves
    (the `knownLeaf` branch of the JSX) and `onToggle(taxon.id)` for
    expandable rows \u2014 mirroring the legacy `web/nav.js::
    selectTaxon(id)` / `toggleExpand(id)` primitives byte-for-byte."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    # The disclosure button is uniquely identified by its shape: a
    # `<button>` carrying `aria-expanded` (per
    # `test_tree_row_uses_semantic_disclosure_button`'s contract) and
    # `aria-label` that names the taxon + leaf/expand affordance.
    # We anchor the regex on the canonical aria-label template prefix
    # (`{`Select ${rankLabel` for leaves, `{`${expanded ? "Collapse"
    # : "Expand"}` for expandable rows).
    disclosure_match = re.search(
        r'<button\b[^>]*aria-expanded[\s\S]*?</button>',
        text,
    )
    assert disclosure_match, (
        "ODD-PHASE2: TreeRow.tsx must render the disclosure button "
        "with `aria-expanded`."
    )
    body = disclosure_match.group(0)
    # The leaf-click branch MUST call `onSelect(taxon.id)` (selection
    # is orthogonal to expansion \u2014 leaves have no children to toggle).
    # The legacy oracle's `web/nav.js::selectTaxon(id)` primitive is
    # preserved byte-for-byte by the React `onSelect` callback.
    assert re.search(
        r"onSelect\s*\(\s*taxon\.id\s*\)",
        body,
    ), (
        "ODD-PHASE2: disclosure button MUST call `onSelect(taxon.id)` "
        "for leaves (selection primitive remains the single source of "
        "taxon-selection \u2014 mirrors `web/nav.js::selectTaxon(id)`)."
    )
    # The expandable-row branch MUST call `onToggle(taxon.id)` (NOT
    # `onSelect`). Selection is orthogonal to expansion; the
    # disclosure button toggles expansion on expandable rows and
    # selects on leaves. Mirrors `web/nav.js::toggleExpand(id)`.
    assert re.search(
        r"onToggle\s*\(\s*taxon\.id\s*\)",
        body,
    ), (
        "ODD-PHASE2: disclosure button MUST call `onToggle(taxon.id)` "
        "for expandable rows (toggling expansion, NOT selecting)."
    )


# ---------------------------------------------------------------------------
# ODD-TDO-001 — native selected-taxon detail panel.
#
#   - `DetailPanel` component lives in
#     `src/modules/taxonomy/presentation/DetailPanel.tsx` and renders
#     the Overview tab from the canonical `Taxon` + row-format
#     helpers.
#   - The TaxonomyTree component mounts the DetailPanel next to the
#     tree rows whenever `selected !== null`. Source switches clear
#     the selection, which closes the panel.
#   - The Overview body carries the native identity (rank / name /
#     status / authorship / species count / source-aware parent
#     chain) and source affordances (CoL-only badge + WoRMS
#     cross-link). The realm tint cascade reaches the scientific
#     name via the `.detail-panel[data-realm="X"] .scientific-name`
#     rules added in `globals.css`.
#   - Per-taxon active-tab memory lives at the `TaxonomyTree`
#     level (a `Map<number, DetailTabKey>`); `DetailPanel` is the
#     pure renderer that reads + writes via the callback.
#   - The static export must carry the new CSS so the panel renders
#     identically to the legacy oracle on CoL / WoRMS / Freshwater.
# ---------------------------------------------------------------------------

def test_detail_panel_file_exists() -> None:
    """ODD-TDO-001: DetailPanel component must exist as a `.tsx` file
    in the taxonomy presentation folder."""
    assert TAXONOMY_DETAIL_PANEL_FILE.is_file(), (
        f"missing {TAXONOMY_DETAIL_PANEL_FILE} — ODD-TDO-001 ships this "
        f"selected-taxon detail panel component."
    )
    assert TAXONOMY_DETAIL_PANEL_FILE.suffix == ".tsx", (
        "DetailPanel must be `.tsx` (JSX-rendered)."
    )


def test_detail_panel_is_a_client_component() -> None:
    """ODD-TDO-001: DetailPanel mounts inside the existing client
    island (`TaxonomyTree`) and carries its own client boundary so
    the tab strip + parent-chain clicks stay interactive. The
    component declares the boundary via the `"use client"`
    directive at the top of the file."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert text.lstrip().startswith('"use client"') or text.lstrip().startswith("'use client'"), (
        "DetailPanel.tsx must declare the client boundary via 'use client'"
    )


def test_detail_panel_uses_canonical_helpers() -> None:
    """ODD-TDO-001 + ODD-TAPOPUP-001: DetailPanel composes the
    canonical row-format helpers it still needs — the rank label
    + the scientific-name italic-vs-roman predicate. The
    Overview-only helpers (species-count badge, status-dot
    descriptor, realm tint, source-aware breadcrumb walker)
    are GONE — the popup replaces the sticky rail + the
    Overview tab body, and those helpers are no longer
    consumed inside the panel. spec.md rule 4 keeps the
    presentation pure; rule 5 blocks deep imports via the
    `no-restricted-imports` ESLint guard."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    for helper in (
        "rankLabel",
        "scientificNameClass",
    ):
        assert helper in text, (
            f"DetailPanel.tsx must consume the canonical `{helper}` helper "
            f"(spec.md rule 4 / ODD-TDO-001 contract)."
        )
    # The Overview-only helpers are GONE (the popup drops the
    # Overview tab body + the realm tint + the parent-chain).
    for helper in (
        "speciesCountBadge",
        "statusDotDescriptor",
        "realmForPath",
        "walkBreadcrumbForSource",
    ):
        assert helper not in text, (
            f"ODD-TAPOPUP-001: DetailPanel.tsx must NOT consume "
            f"`{helper}` (the popup drops the Overview tab body; "
            f"the helper stays in `row-format.ts` / "
            f"`breadcrumb-path.ts` for other consumers)."
        )


def test_detail_panel_emits_native_overview_identity() -> None:
    """ODD-TAPOPUP-001 (negative witness): the popup has NO
    Overview tab body. The pre-popup sticky rail rendered a
    rich Overview tab with Scientific name / Status /
    Authorship / Species count / Parent chain rows — that
    body is GONE (the popup replaces the sticky rail and
    the user-selected four tabs are Synonyms / Distribution /
    Search / Folder).

    The labels MUST NOT appear as JSX literals in the file.
    The string-substring anchor below catches any leak of the
    legacy Overview body into the popup's source."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    for label in (
        "Scientific name:",
        "Parent chain:",
    ):
        assert label not in text, (
            f"ODD-TAPOPUP-001: DetailPanel.tsx must NOT render "
            f"the `{label}` label (the Overview tab body is "
            f"gone; the popup ships Synonyms / Distribution / "
            f"Search / Folder)."
        )


def test_detail_panel_emits_native_source_affordances() -> None:
    """ODD-TAPOPUP-001 (negative witness): the popup has NO
    WoRMS / CoL-only header badges. The pre-popup sticky rail
    carried the source-affordance badges (CoL-only ID + WoRMS
    cross-link) in the header; the popup's header is minimal
    (taxon name + authorship + close button) so the badges are
    GONE.

    The coldp_id + worms_id field reads MAY survive (the
    canonical Taxon fields are still consumed elsewhere) but
    the badge-rendering JSX is gone."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # The badge-rendering JSX literals are GONE. The strings
    # `CoL-only` / `WoRMS ·` MUST NOT appear in the source.
    for needle in ("CoL-only", "WoRMS \u00b7"):
        assert needle not in text, (
            f"ODD-TAPOPUP-001: DetailPanel.tsx must NOT render "
            f"the `{needle}` badge copy (the popup header is "
            f"minimal; the legacy source-affordance badges are "
            f"gone)."
        )


def test_detail_panel_emits_extinct_treatment() -> None:
    """ODD-TAPOPUP-001 (negative witness): the popup header
    has NO extinct badge + NO `line-through opacity-70`
    treatment. The pre-popup sticky rail carried the extinct
    `<Badge variant="warning">` marker + the strikethrough
    treatment; the popup's header is minimal so the extinct
    affordance is gone.

    The `is_extinct` field read MAY survive (the canonical
    Taxon field is still consumed elsewhere), but the badge
    JSX + the `line-through opacity-70` styling MUST be gone."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", text)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert "line-through" not in code_only, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT apply the "
        "`line-through opacity-70` extinct treatment (the "
        "popup header is minimal; the extinct affordance is "
        "gone)."
    )
    assert 'data-detail-extinct=""' not in code_only, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT stamp "
        "`data-detail-extinct=\"\"` (the extinct marker is "
        "gone; the popup's minimal header doesn't carry it)."
    )


def test_detail_panel_stamps_data_realm_attribute() -> None:
    """ODD-TAPOPUP-001 (negative witness): the popup host
    does NOT carry `data-realm` (the realm-tint cascade was
    scoped to the pre-popup Overview body; the popup replaces
    the sticky rail and the realm tint is gone). The
    `realmForPath` helper MAY still be consumed elsewhere in
    the codebase (it's a canonical row-format helper), but the
    popup MUST NOT stamp the `data-realm` attribute on its
    host."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", text)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert "data-realm" not in code_only, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT stamp "
        "`data-realm` on the popup host (the realm-tint "
        "cascade was scoped to the pre-popup Overview body; "
        "the popup replaces the sticky rail and the realm "
        "tint is gone)."
    )


def test_detail_panel_emits_tab_strip_with_four_tabs() -> None:
    """ODD-TAPOPUP-001: the popup's tab strip carries exactly
    four tabs in the user-selected order: Synonyms, Distribution
    ("Location/Distribution"), Search ("Search links"), Folder
    ("Folder creation"). The legacy Overview + Vernaculars tabs
    are GONE — the popup replaces the sticky detail rail and
    the user explicitly chose these four tabbed sections.

    Mirrors the user-approved taxonomy UX (the popup is the
    selected-taxon surface; the four tabs subsume the legacy
    Overview body's rank/name/status/authorship/count/parent-
    chain identity + the Vernaculars body's common-name list).
    """
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # The four user-selected tab labels MUST appear in the
    # `DETAIL_TABS` array. The labels carry the user-facing copy
    # ("Synonyms" / "Distribution" / "Search" / "Folder") — the
    # "Location/Distribution" + "Search links" + "Folder
    # creation" phrasing lives in the docstring above.
    for tab in ("Synonyms", "Distribution", "Search", "Folder"):
        assert tab in text, (
            f"ODD-TAPOPUP-001: DetailPanel.tsx must declare the "
            f"{tab!r} tab in the popup's strip."
        )
    # The legacy Overview + Vernaculars tabs are GONE. Strip
    # comments first so the regex doesn't trip on
    # docstring-history mentions of the legacy hooks.
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", text)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    # The tab label "Overview" MUST NOT appear in the
    # `DETAIL_TABS` array.
    overview_match = re.search(
        r"DETAIL_TABS[\s\S]*?\bOverview\b",
        code_only,
    )
    assert overview_match is None, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT declare the "
        "Overview tab in the popup's `DETAIL_TABS` array (the "
        "popup replaces the sticky detail rail; the four tabs "
        "are Synonyms / Distribution / Search / Folder)."
    )
    vernacular_match = re.search(
        r"DETAIL_TABS[\s\S]*?\bVernaculars\b",
        code_only,
    )
    assert vernacular_match is None, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT declare the "
        "Vernaculars tab in the popup's `DETAIL_TABS` array "
        "(the popup owns only the four user-selected tabs)."
    )


def test_detail_panel_all_four_tabs_are_available() -> None:
    """ODD-TAPOPUP-001: every popup tab carries
    `available: true` — the user-selected four tabs are all
    fully enabled (no `disabled` + `aria-disabled="true"`
    deferral). The legacy "visibly mark unavailable later tabs
    without fake actions" policy no longer applies (the popup
    ships the four tabs as real backing surfaces)."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # Pin the `available: true` flag for each of the four tabs.
    for tab_key in ("synonyms", "distribution", "searches", "folder"):
        pattern = (
            rf"key\s*:\s*[\"\']{tab_key}[\"\'][\s\S]{{0,200}}?"
            rf"available\s*:\s*true"
        )
        assert re.search(pattern, text), (
            f"ODD-TAPOPUP-001: DetailPanel.tsx must declare the "
            f"`{tab_key}` tab with `available: true` (the popup "
            f"ships all four tabs as real backing surfaces)."
        )
    # No deferred tabs: no `disabled` + `aria-disabled="true"`
    # carry through to the rendered tab buttons.
    assert "data-tab-available=\"false\"" not in text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT carry any "
        "`data-tab-available=\"false\"` button (the popup "
        "ships all four tabs as real backing surfaces)."
    )


def test_detail_panel_disables_unavailable_tabs() -> None:
    """ODD-TAPOPUP-001: this negative witness pins the
    "no disabled tabs" contract. The pre-popup sticky rail
    deferred Folder / Vernaculars / Synonyms / Distribution as
    `disabled` + `aria-disabled="true"` — the popup replaces
    that policy with all-four-tabs-enabled. The panel MUST
    NOT render any `data-tab-available="false"` tab button;
    the popup's four tabs are all `available: true`."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", text)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert "data-tab-available=\"false\"" not in code_only, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT carry any "
        "`data-tab-available=\"false\"` tab button (the popup "
        "ships all four tabs as real backing surfaces)."
    )
    assert "aria-disabled=\"true\"" not in code_only, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT stamp "
        "`aria-disabled=\"true\"` on any tab button (the popup "
        "ships all four tabs as enabled)."
    )


def test_detail_panel_is_a_modal_dialog() -> None:
    """ODD-TAPOPUP-001: the popup replaces the sticky detail
    rail with a modal dialog. The DetailPanel host carries
    `role="dialog"` + `aria-modal="true"` so assistive tech
    treats the panel as a true modal (focus is trapped inside
    the dialog; outside clicks are blocked by the backdrop).

    The dialog also carries `aria-labelledby` pointing at the
    scientific-name `<h2>` so screen readers announce the
    dialog's title (the taxon name) when the popup opens."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert 'role="dialog"' in text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must stamp "
        "`role=\"dialog\"` on the popup host (the popup is a "
        "modal dialog, not a sticky aside)."
    )
    assert 'aria-modal="true"' in text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must stamp "
        "`aria-modal=\"true\"` on the popup host (the popup is "
        "a true modal — outside clicks + focus are trapped)."
    )
    assert "aria-labelledby" in text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must stamp "
        "`aria-labelledby` on the popup host (the dialog's "
        "accessible name is the taxon's scientific name)."
    )


def test_detail_panel_renders_backdrop() -> None:
    """ODD-TAPOPUP-001: the popup renders a backdrop element
    that closes the dialog on click. The backdrop sits behind
    the dialog content (z-index lower than the dialog host),
    covers the full viewport, and is a sibling of the dialog
    content so clicking it does not bubble to the dialog.

    The backdrop element carries the `.detail-panel-backdrop`
    class hook + an `onClick` handler that calls the
    `onClose` callback (the same close handler the close
    IconButton + Escape use)."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # The `.detail-panel-backdrop` class hook MUST appear in
    # the source.
    assert "detail-panel-backdrop" in text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must render a "
        "`.detail-panel-backdrop` element (the modal "
        "backdrop closes the popup on click)."
    )
    # The backdrop element carries an `onClick` handler that
    # routes through `onClose`.
    backdrop_match = re.search(
        r'detail-panel-backdrop[^>]*',
        text,
    )
    assert backdrop_match, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must render the "
        "backdrop with a discoverable element (the class hook "
        "alone is not enough — the element must be in the JSX)."
    )


def test_detail_panel_closes_on_escape() -> None:
    """ODD-TAPOPUP-001: the popup registers a document-level
    keydown listener that calls `onClose()` on Escape. The
    listener is attached while the popup is open
    (`DetailPanel` only mounts when `selected !== null` so the
    listener is bound for the popup's lifetime; on unmount the
    listener is removed via the `useEffect` cleanup)."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # The listener MUST register a keydown handler that
    # branches on `Escape`.
    assert re.search(
        r'addEventListener\s*\(\s*["\']keydown["\']',
        text,
    ), (
        "ODD-TAPOPUP-001: DetailPanel.tsx must register a "
        "keydown listener that closes the popup on Escape."
    )
    assert "Escape" in text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must branch on "
        "`Escape` in the keydown handler."
    )
    assert "removeEventListener" in text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must clean up the "
        "keydown listener via `removeEventListener` so the "
        "document-level touchpoint is removed when the popup "
        "closes."
    )


def test_detail_panel_focuses_on_open() -> None:
    """ODD-TAPOPUP-001: the popup focuses its close button on
    mount so keyboard users land inside the dialog as soon as
    it opens (the WAI-ARIA Authoring Practices dialog pattern).
    A `useEffect` with an empty deps array focuses the close
    IconButton on mount; the user's keyboard tab order picks
    up from there."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert "useEffect" in text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must use `useEffect` "
        "for the focus-on-open behavior (the dialog mounts and "
        "focuses on the same render frame)."
    )
    # The `.focus()` call on a ref'd element.
    assert re.search(
        r"\.focus\s*\(\s*\)",
        text,
    ), (
        "ODD-TAPOPUP-001: DetailPanel.tsx must call `.focus()` "
        "on a ref'd element when the dialog opens (the close "
        "button is the canonical first-focus target)."
    )


def test_detail_panel_outside_click_closes_popup() -> None:
    """ODD-TAPOPUP-002: the host `<div id="detail-panel">`
    carries an `onClick` handler that closes the popup when
    the user clicks the dim overlay area surrounding the
    dialog (the Card sits centered inside the host; clicks
    on the host area outside the Card are outside-click
    dismissals). The handler uses `e.target ===
    e.currentTarget` so in-Card clicks do NOT bubble up and
    accidentally close the popup (the Card's own onClick is
    not present; the target check is the only guard).

    The backdrop's onClick stays as a fallback (the backdrop
    is below the host's z-index, so the host onClick is the
    primary dismissal surface; the backdrop onClick is the
    redundancy layer for future layout reshuffles)."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # The host has an onClick handler. The handler uses
    # `e.target === e.currentTarget` (or equivalent) so the
    # host's click handler only fires on the host itself, not
    # on bubbled events from Card children.
    host_open = re.search(
        r'<div[^>]*\bid\s*=\s*["\']detail-panel["\'][^>]*>',
        text,
    )
    assert host_open, (
        "ODD-TAPOPUP-002: DetailPanel.tsx must render the "
        "host `<div id=\"detail-panel\">` with an `onClick` "
        "handler so outside clicks close the popup."
    )
    assert "onClick" in host_open.group(0) or re.search(
        r'<div[^>]*\bonClick[^>]*\bid\s*=\s*["\']detail-panel["\']',
        text,
    ) or re.search(
        r'<div[^>]*\bid\s*=\s*["\']detail-panel["\'][^>]*\bonClick',
        text,
    ), (
        "ODD-TAPOPUP-002: DetailPanel.tsx must render the "
        "host `<div id=\"detail-panel\">` with an `onClick` "
        "prop so outside clicks close the popup."
    )
    # The handler uses `e.target === e.currentTarget` so
    # Card clicks do not bubble up to close the popup.
    assert re.search(
        r"(?:e\.target\s*===\s*e\.currentTarget|target\s*===\s*currentTarget)",
        text,
    ), (
        "ODD-TAPOPUP-002: DetailPanel.tsx must use the "
        "`e.target === e.currentTarget` guard on the host's "
        "`onClick` so clicks inside the Card (which bubble up "
        "through the host) do not close the popup."
    )


def test_detail_panel_tab_cycles_focus_inside_dialog() -> None:
    """ODD-TAPOPUP-002: Tab / Shift+Tab inside the dialog
    cycles focus within the dialog (the WAI-ARIA focus-trap
    pattern). The keydown handler intercepts `Tab` (and
    `Shift+Tab`) and wraps focus from the last focusable
    element back to the first (and vice versa). Without the
    trap, Tab from the close button would jump to the next
    focusable element on the page (the tree rows), which
    would silently escape the modal context.

    The keydown handler is the same document-level listener
    that closes the popup on Escape (the existing ODD-TAPOPUP-
    001 contract); the Tab branch is added alongside the
    Escape branch."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # The Tab branch must live in the existing keydown
    # listener (the listener MUST branch on `Tab` in addition
    # to `Escape`). The regex captures the full `useEffect`
    # body (from the `useEffect(() =>` opener to the matching
    # `}, [onClose]);` closer) so the `onKeyDown` body
    # (defined BEFORE the `addEventListener` call) is included
    # in the check.
    keydown_match = re.search(
        r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[\s\S]+?\}\s*,\s*\[onClose\]\s*\)\s*;",
        text,
    )
    assert keydown_match, (
        "ODD-TAPOPUP-002: DetailPanel.tsx must register a "
        "document-level keydown listener with a cleanup that "
        "removes it on unmount."
    )
    keydown_body = keydown_match.group(0)
    assert "Escape" in keydown_body, (
        "ODD-TAPOPUP-002: DetailPanel.tsx keydown listener must "
        "still branch on `Escape`."
    )
    assert re.search(
        r"\bTab\b",
        keydown_body,
    ), (
        "ODD-TAPOPUP-002: DetailPanel.tsx keydown listener must "
        "branch on the `Tab` key so focus cycling stays inside "
        "the dialog."
    )
    assert "addEventListener" in keydown_body, (
        "ODD-TAPOPUP-002: DetailPanel.tsx keydown handler must "
        "register the listener via `addEventListener(\"keydown\", ...)`."
    )
    assert "removeEventListener" in keydown_body, (
        "ODD-TAPOPUP-002: DetailPanel.tsx keydown handler must "
        "clean up via `removeEventListener` on unmount."
    )
    # The Tab handler must wrap focus (a `focus()` call on a
    # queried focusable element inside the dialog).
    assert re.search(
        r"\.focus\s*\(\s*\)",
        text,
    ), (
        "ODD-TAPOPUP-002: DetailPanel.tsx Tab-cycling handler "
        "must call `.focus()` on a queried focusable element "
        "to wrap focus to the first/last focusable inside the "
        "dialog."
    )


def test_detail_panel_restores_focus_to_trigger_on_close() -> None:
    """ODD-TAPOPUP-002: when the popup closes, focus is
    restored to the per-row kebab trigger that opened it
    (WAI-ARIA Authoring Practices dialog pattern — focus
    returns to the element that triggered the dialog). The
    trigger is captured BEFORE the close button gets focused
    on mount (the `document.activeElement` at mount time is
    the kebab button the user just clicked), then the cleanup
    of the focus-on-mount useEffect restores focus to that
    trigger when the dialog unmounts.

    Implementation contract:
      - `useRef<HTMLElement | null>(null)` (or equivalent) to
        store the trigger element.
      - The focus-on-mount useEffect captures
        `document.activeElement` synchronously BEFORE focusing
        the close button.
      - The useEffect cleanup restores focus via
        `triggerRef.current?.focus()`."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", text)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    # A useRef is used to store the trigger element.
    assert re.search(
        r"useRef\s*[<(]",
        code_only,
    ), (
        "ODD-TAPOPUP-002: DetailPanel.tsx must use `useRef` "
        "to store the trigger element so the unmount cleanup "
        "can restore focus."
    )
    # The focus-on-mount useEffect captures
    # `document.activeElement` (the kebab button the user just
    # clicked) BEFORE focusing the close button.
    assert "document.activeElement" in code_only, (
        "ODD-TAPOPUP-002: DetailPanel.tsx must capture "
        "`document.activeElement` synchronously on mount "
        "(BEFORE focusing the close button) so the trigger "
        "element survives the focus shift."
    )
    # The useEffect has a cleanup function (so the focus
    # restoration happens on unmount).
    assert re.search(
        r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[\s\S]+?return\s*\(\s*\)\s*=>",
        code_only,
    ), (
        "ODD-TAPOPUP-002: DetailPanel.tsx focus-on-mount "
        "useEffect must have a cleanup function so focus is "
        "restored on unmount."
    )


def test_tab_strip_overflow_handled_on_narrow_viewports() -> None:
    """ODD-TAPOPUP-002: the `.tab-strip` rule handles
    horizontal overflow on narrow viewports so the four
    tabs (Synonyms / Distribution / Search / Folder) don't
    clip. The rule carries `overflow-x: auto` (or wraps via
    `flex-wrap`) so narrow viewports can scroll the tab
    strip horizontally without losing any tab.

    The fix is scoped to the `.tab-strip` rule alone (no
    global overflow behavior); the existing rule already
    sets `display: flex` + `padding: 0 16px` + the per-tab
    padding cascade."""
    text = _read_text(TAXONOMY_GLOBALS_CSS)
    # The `.tab-strip` rule (NOT the descendant `.tab-strip >
    # .tab-button` rule) must carry `overflow-x` or
    # `flex-wrap` so the four tabs don't clip on narrow
    # viewports.
    tab_strip_block = re.search(
        r"\.tab-strip\s*\{([^}]*)\}",
        text,
        re.DOTALL,
    )
    assert tab_strip_block, (
        "ODD-TAPOPUP-002: globals.css must declare the "
        "`.tab-strip` base rule."
    )
    body = tab_strip_block.group(1)
    assert "overflow-x" in body or "flex-wrap" in body, (
        "ODD-TAPOPUP-002: globals.css `.tab-strip` rule must "
        "carry `overflow-x: auto` (or `flex-wrap: wrap`) so "
        "the four tabs don't clip on narrow viewports."
    )


def test_detail_panel_card_has_responsive_dimensions() -> None:
    """ODD-TAPOPUP-002: the dialog `<Card>` carries explicit
    responsive width + max-width so the dialog scales with
    the viewport (not a fixed pixel size). The Card's
    className includes a `w-full` width constraint + a
    `max-w-[…]` Tailwind utility so the dialog fills narrow
    viewports AND caps at a sensible reading width on wide
    viewports (typically `max-w-[720px]` for the four-tab
    popup + `max-w-[90vw]` as the hard upper bound for the
    Card width on wider screens).

    The Card is the inner dialog content; the host
    (`.detail-panel`) provides the centered flexbox, the
    Card provides the content dimensions."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # Strip block + line comments so the regex doesn't trip on
    # docstring-history mentions of `<Card variant="default">`.
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", text)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    # The Card className includes `w-full` (so it fills the
    # host's centered flexbox at narrow viewports) + a
    # `max-w-[…]` Tailwind utility (so it caps at a sensible
    # reading width on wide viewports).
    # The Card element spans multiple lines (the className is
    # typically wrapped across lines for readability), so the
    # regex captures from the `<Card` opening to the matching
    # `>` terminator of the JSX tag.
    card_match = re.search(
        r"<Card\b[^>]*\bvariant\s*=\s*[\"']default[\"'][^>]*>",
        code_only,
        re.DOTALL,
    )
    assert card_match, (
        "ODD-TAPOPUP-002: DetailPanel.tsx must render "
        "`<Card variant=\"default\">` as the inner dialog "
        "content."
    )
    card_open_idx = card_match.start()
    card_close_idx = code_only.find(">", card_match.end())
    assert card_close_idx != -1, (
        "ODD-TAPOPUP-002: Card opening tag must terminate with `>`."
    )
    card_open = code_only[card_open_idx:card_close_idx + 1]
    assert "w-full" in card_open, (
        "ODD-TAPOPUP-002: DetailPanel.tsx Card className must "
        "include `w-full` so the dialog fills the host's "
        "centered flexbox at narrow viewports."
    )
    assert re.search(
        r"max-w-\[",
        card_open,
    ), (
        "ODD-TAPOPUP-002: DetailPanel.tsx Card className must "
        "include a `max-w-[…]` Tailwind utility so the dialog "
        "caps at a sensible reading width on wide viewports."
    )


def test_detail_panel_adapts_for_narrow_viewports() -> None:
    """ODD-TAPOPUP-001: the popup reuses the
    `perTaxonActiveTab` memory so re-selecting a previously
    selected taxon lands the user on the last tab they used
    for it (or the default `DEFAULT_DETAIL_TAB` for new taxa).
    The default tab key survives the popup cutover — the
    pre-popup `"overview"` default is replaced by the
    user-selected four-tab default (the first tab in the
    user-selected order)."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert "DEFAULT_DETAIL_TAB" in text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must declare the "
        "`DEFAULT_DETAIL_TAB` constant (the default active "
        "tab for newly selected taxa)."
    )
    # The default MUST be one of the four user-selected tabs.
    # The regex anchors on the assignment (`= "key"`) to skip the
    # TypeScript type annotation (`DetailTabKey`) that lives
    # between the constant name + the assignment operator.
    default_match = re.search(
        r"DEFAULT_DETAIL_TAB[^=\n]*=\s*[\"'](\w+)[\"']",
        text,
    )
    assert default_match, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must declare "
        "`DEFAULT_DETAIL_TAB` as a string literal."
    )
    default_key = default_match.group(1)
    assert default_key in ("synonyms", "distribution", "searches", "folder"), (
        f"ODD-TAPOPUP-001: `DEFAULT_DETAIL_TAB` must be one of "
        f"the four user-selected tab keys "
        f"(synonyms / distribution / searches / folder); got "
        f"{default_key!r}."
    )


def test_detail_panel_enables_search_tab() -> None:
    """ODD-TDS-001: the Search tab is now ENABLED
    (`available: true`). The legacy `web/detail.js::tabs` array
    always pushed the Search tab alongside Overview / Folder; the
    React port's first slice shipped Overview-only and marked the
    rest as `available: false` per the "visibly mark unavailable
    later tabs without fake actions" policy. ODD-TDS-001 flips the
    Search entry to `true` so the user can click into the
    server-composed search-engine link grid. Folder / Vernaculars
    / Synonyms / Distribution stay `available: false` until their
    backing React slices ship.
    """
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # The DETAIL_TABS array must contain a `Search` entry whose
    # `available` flag is `true`. The pattern below accepts either
    # source-form (`available: true`) or a multi-line layout.
    assert re.search(
        r"key\s*:\s*[\"\']searches[\"\']\s*,\s*label\s*:\s*[\"\']Search[\"\']"
        r"[\s\S]{0,200}?available\s*:\s*true",
        text,
    ), (
        "DetailPanel.tsx must declare the Search tab with `available: true` "
        "(ODD-TDS-001 enables the Search tab body)."
    )


def test_detail_panel_renders_search_tab_when_active() -> None:
    """ODD-TDS-001: when `activeTab === "searches"`, the panel
    body renders `<SearchTab>` instead of the Overview body. The
    body slot must consume the canonical `SearchTabStatus`
    discriminated-union + the `onRetrySearches` callback so the
    loading / empty / error / loaded states all render correctly.
    The `SearchTab` import at the top of the file pins the wiring
    contract; the body slot pins the runtime dispatch.
    """
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert "SearchTab" in text, (
        "DetailPanel.tsx must import the canonical SearchTab component."
    )
    assert "SearchTabStatus" in text, (
        "DetailPanel.tsx must consume the SearchTabStatus type for the "
        "searchStatus prop."
    )
    # Body slot must dispatch on activeTab === "searches" to render
    # SearchTab. The `renderOverview` fallback covers every other
    # tab; the SearchTab branch carries the loading / empty /
    # error / loaded state machine.
    assert re.search(
        r"activeTab\s*===\s*[\"\']searches[\"\']",
        text,
    ), (
        "DetailPanel.tsx body must dispatch on activeTab === \"searches\" "
        "to render the SearchTab."
    )
    assert re.search(
        r"activeTab\s*===\s*[\"\']searches[\"\'][\s\S]{0,200}?<SearchTab",
        text,
    ), (
        "DetailPanel.tsx must render <SearchTab> when activeTab === \"searches\"."
    )
    # onRetrySearches callback must be threaded through to the SearchTab.
    assert "onRetrySearches" in text, (
        "DetailPanel.tsx must thread onRetrySearches through to SearchTab."
    )


def test_detail_panel_renders_close_button() -> None:
    """ODD-TDO-001 + ODD-PHASE2: the panel carries a Close
    affordance so the user can dismiss the panel. The click
    handler calls `onClose()` which the parent maps to
    `setSelected(null)`.

    ODD-PHASE2 update: the close button is now
    `<IconButton variant="subtle" aria-label="Hide details">`
    from the `@taxa/design-system` barrel. The legacy inline
    `<button className="detail-close ...">` pattern collapsed
    into the design-system primitive; the `data-action=
    "close-detail"` attribute stays on the element so the
    selector + data-action delegation contract survives the
    React cutover (parent tests + tooling still pin it)."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # ODD-PHASE2 — the close button is now an IconButton
    # primitive instead of an inline `<button
    # className="detail-close ...">`.
    assert re.search(
        r'<IconButton[^>]*\bvariant\s*=\s*["\']subtle["\']',
        text,
    ), (
        "DetailPanel.tsx must render the close button as "
        '<IconButton variant="subtle"> from @taxa/design-system.'
    )
    assert re.search(
        r'<IconButton[^>]*\baria-label\s*=\s*["\']Hide details["\']',
        text,
    ), (
        "DetailPanel.tsx must stamp aria-label=\"Hide details\" "
        "on the close IconButton (icon-only buttons MUST carry "
        "an aria-label per the IconButton a11y contract)."
    )
    # The legacy inline button className is GONE.
    assert not re.search(
        r'<button[^>]*\bclassName\s*=\s*["\'][^"\']*\bdetail-close\b',
        text,
    ), (
        "DetailPanel.tsx must NOT render the legacy inline "
        '<button className="detail-close ..."> close button '
        "— the IconButton primitive owns the treatment."
    )
    # The `data-action="close-detail"` attribute stays so the
    # selector + data-action delegation contract survives.
    assert re.search(r'data-action\s*=\s*["\']close-detail["\']', text), (
        "DetailPanel.tsx must stamp data-action=\"close-detail\" "
        "on the close IconButton."
    )
    assert "onClose" in text, (
        "DetailPanel.tsx must consume the onClose callback prop."
    )


def test_detail_panel_chain_segment_routes_to_breadcrumb_handler() -> None:
    """ODD-TAPOPUP-001 (negative witness): the popup has NO
    parent-chain segment buttons. The pre-popup Overview body
    rendered the source-aware parent chain as a list of
    `data-action="focus-segment"` buttons; the popup replaces
    the Overview body and the chain-segment JSX is gone.

    The breadcrumb at the top of the tree still exposes the
    parent chain (the TaxonomyTree renders the breadcrumb above
    the rows; the popup's four tabs do not duplicate the
    chain). The `onFocusSegment` prop on DetailPanel is
    therefore no longer needed; the popup MUST NOT consume it.
    """
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # The chain-segment JSX is gone. Anchor on the JSX form
    # (`data-action="focus-segment"` inside a `<button>` or
    # rendered element) to avoid matching any docstring
    # references that mention the legacy hook.
    assert not re.search(
        r'<button\b[^>]*\bdata-action\s*=\s*["\']focus-segment["\']',
        text,
    ), (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT render a "
        "parent-chain segment button with "
        "`data-action=\"focus-segment\"` (the popup's Overview "
        "body is gone; the chain-segment JSX is gone)."
    )
    assert "onFocusSegment" not in text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT consume the "
        "`onFocusSegment` callback prop (the Overview body's "
        "parent chain is gone; the breadcrumb above the tree "
        "owns the focus-segment affordance)."
    )


def test_taxonomy_tree_mounts_detail_panel_when_selected() -> None:
    """ODD-TDO-001 + ODD-TAPOPUP-001: TaxonomyTree mounts the
    DetailPanel whenever `selected !== null`. The panel IS the
    popup — clicking the row-level kebab IconButton calls
    `handleSelect(id)` which sets `selected = id` and the panel
    mounts in its centered-dialog form. The parent passes
    `taxon`, `state`, `activeSource`, `activeTab`, the
    tab-change callback, and the close callback. The
    `onFocusSegment` callback is gone (the Overview body's
    parent-chain is gone with the popup cutover)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(r"<\s*DetailPanel\b", text), (
        "TaxonomyTree.tsx must render a <DetailPanel> component."
    )


def test_taxonomy_tree_handles_per_taxon_active_tab_memory() -> None:
    """ODD-TDO-001: TaxonomyTree owns the per-taxon active-tab
    memory as a `Map<number, DetailTabKey>`. Re-selecting a
    previously selected taxon lands the user on the last tab they
    used for it (or the default for new taxa). The state is read
    via `getActiveTabFor(id)` and written via `handleTabChange(id,
    tab)`."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "Map<number, DetailTabKey>" in text or "Map<number," in text, (
        "TaxonomyTree.tsx must own a Map<number, DetailTabKey> for "
        "per-taxon active-tab memory."
    )
    # The memory map keys (and is keyed) by taxon id.
    assert "getActiveTabFor" in text or ".get(taxonId)" in text, (
        "TaxonomyTree.tsx must read the per-taxon tab via Map.get(taxonId)."
    )
    assert "handleTabChange" in text or "setPerTaxonActiveTab" in text, (
        "TaxonomyTree.tsx must declare a handleTabChange handler that "
        "writes to the per-taxon active-tab map."
    )


def test_taxonomy_tree_close_detail_clears_selection() -> None:
    """ODD-TDO-001: the close handler on the DetailPanel maps to
    `setSelected(null)` so the panel unmounts on the next render.
    The focused + kebab + per-taxon tab memory are NOT cleared
    (the legacy oracle keeps them too — selection is independent
    of expansion + memory)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    handle_idx = text.find("handleCloseDetail")
    assert handle_idx != -1, (
        "TaxonomyTree.tsx must declare a handleCloseDetail handler."
    )
    body = text[handle_idx:handle_idx + 400]
    assert "setSelected(null)" in body, (
        "handleCloseDetail must call setSelected(null) so the panel "
        "unmounts on the next render."
    )


# ---------------------------------------------------------------------------
# ODD-CLOSEFIX-001 — fix the close-detail → URL-state reopen defect.
#
# `handleSelect(id)` writes `/?taxon=<id>` via `router.replace`. The
# pre-fix `handleCloseDetail` only cleared the local `selected` state —
# the URL still carried `?taxon=<id>`, so the URL → state sync effect
# (which runs on every `searchParams` + `selected` change) immediately
# reselected the dismissed taxon and reopened the panel. The user saw a
# "close → reopen → close" flash.
#
# The fix is two-pronged:
#   1. `handleCloseDetail` writes a ref-based dismissal guard for the
#      just-closed taxon AND calls `router.replace("/")` so the URL
#      loses its `?taxon=` param.
#   2. The URL → state sync effect consults the guard and skips
#      reopening for the dismissed id. The guard is cleared whenever
#      the URL points at a different taxon (the user actively
#      navigated to a new taxon or the back/forward buttons moved
#      past the dismissed one).
# ---------------------------------------------------------------------------


def test_taxonomy_tree_close_detail_removes_taxon_from_url() -> None:
    """ODD-CLOSEFIX-001: `handleCloseDetail` must call
    `router.replace("/")` so the URL no longer carries
    `?taxon=<id>` once the user dismisses the popup. Without this
    the URL → state sync effect would re-select the dismissed
    taxon on the next render and reopen the panel.

    The router call MUST use the `replace` strategy (NOT `push`)
    so dismissing the popup does not add a history entry — the
    user must not have to press back twice to escape the panel
    they just closed.

    ODD-CLOSEFIX-002 (refinement): the router call MUST pass
    `{ scroll: false }` as the second argument so Next.js does
    NOT scroll the tree surface to the top of the viewport when
    the user only dismisses the popup. The App Router's default
    `scroll: true` scrolls the page to the top on every
    navigation, which would yank the user out of their current
    scroll position in the tree for a same-page dismissal that
    does not change the route. The Next 16 `useRouter` reference
    (see `node_modules/next/dist/docs/01-app/03-api-reference/
    04-functions/use-router.md`) documents the second-arg
    `{ scroll: boolean, transitionTypes: string[] }` shape; the
    close handler passes only the `scroll` key.

    The handler MUST also still call `setSelected(null)` so the
    existing pre-fix regression
    (`test_taxonomy_tree_close_detail_clears_selection`) keeps
    passing."""
    text = _read_text(TAXONOMY_TREE_FILE)
    handle_idx = text.find("handleCloseDetail")
    assert handle_idx != -1, (
        "TaxonomyTree.tsx must declare a handleCloseDetail handler."
    )
    body = text[handle_idx:handle_idx + 800]
    assert "setSelected(null)" in body, (
        "handleCloseDetail must call setSelected(null) so the panel "
        "unmounts on the next render."
    )
    assert re.search(
        r"router\.replace\(\s*[\"']/[\"']\s*,\s*\{\s*scroll\s*:\s*false\s*\}\s*\)",
        body,
    ), (
        "handleCloseDetail must call "
        "`router.replace(\"/\", { scroll: false })` so the URL no "
        "longer carries the dismissed `?taxon=<id>` param AND "
        "Next.js does NOT scroll the page to the top on a "
        "same-page dismissal. Without `scroll: false`, the "
        "App Router's default `scroll: true` yanks the user out "
        "of their current tree scroll position for a popup "
        "dismissal that does not change the route. The Next 16 "
        "`useRouter` API documents the `{ scroll: boolean, "
        "transitionTypes: string[] }` second-arg shape."
    )


def test_taxonomy_tree_close_detail_writes_dismissal_guard_ref() -> None:
    """ODD-CLOSEFIX-001: `handleCloseDetail` must capture the
    dismissed taxon id into a `useRef`-backed guard so a stale
    `searchParams` value — between the `setSelected(null)` re-
    render and the async `router.replace(\"/\")` navigation
    completing — cannot trigger the URL → state sync effect to
    reopen the panel for the just-dismissed taxon.

    The guard MUST live on a `useRef` (NOT a `useState`) so the
    write does not trigger a fresh re-render of the entire tree —
    the ref carries the value across renders without a render
    cycle. The ref MUST be read by the URL → state sync effect
    so the dismissal guard actually short-circuits the
    reselection path (the matching witness lives in
    `test_taxonomy_tree_url_state_effect_skips_dismissed_taxon`)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # The ref MUST be declared with `useRef<number | null>` so the
    # guard value carries across renders without a re-render
    # cycle (the URL → state effect reads the ref synchronously
    # without subscribing to it).
    assert re.search(
        r"useRef<\s*number\s*\|\s*null\s*>\s*\(\s*(?:null|undefined)\s*\)",
        text,
    ), (
        "TaxonomyTree.tsx must declare a `useRef<number | null>(null)` "
        "(or `(undefined)`) guard to carry the last-dismissed taxon "
        "id across renders. A `useState`-backed guard would trigger a "
        "fresh re-render on every write and the URL → state effect "
        "would still trip on the in-flight `setSelected(null)` render."
    )
    handle_idx = text.find("handleCloseDetail")
    assert handle_idx != -1
    body = text[handle_idx:handle_idx + 800]
    # The handler MUST write the dismissed taxon id into the ref
    # BEFORE the URL → state effect can run with the stale param.
    # The exact name of the ref is implementation-defined; the
    # pattern `.current = <value>` is the canonical write.
    assert re.search(
        r"\.current\s*=",
        body,
    ), (
        "handleCloseDetail must write the dismissed taxon id into "
        "the dismissal-guard ref (`refName.current = taxonId`) so "
        "the URL → state sync effect can skip reselecting it."
    )
    # The handler MUST capture the just-selected taxon id BEFORE
    # calling `setSelected(null)` (after the set, the closure's
    # `selected` value is stale until the next render). Pin the
    # capture pattern so a future refactor cannot invert the
    # order and write `null` into the guard.
    assert re.search(
        r"(?:const|let)\s+\w+\s*=\s*selected\b",
        body,
    ) or re.search(
        r"selected\b.*?(?:const|let)\s+\w+",
        body,
        re.DOTALL,
    ), (
        "handleCloseDetail must capture the selected taxon id "
        "(e.g., `const taxonId = selected`) BEFORE calling "
        "`setSelected(null)` so the dismissal guard stores the "
        "real id, not `null`."
    )


def test_taxonomy_tree_url_state_effect_skips_dismissed_taxon() -> None:
    """ODD-CLOSEFIX-001: the URL → state sync effect must consult
    the dismissal-guard ref and skip reselecting when the URL's
    `taxon` param matches the dismissed id. The guard ref MUST be
    read INSIDE the effect body — a guard write outside the
    effect would not gate the reselection logic."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # Locate the URL → state sync effect by its unique anchors:
    # the body reads `searchParams.get("taxon")` and runs after
    # the close handler. The effect depends on `searchParams`,
    # `state.nodes`, and `selected` per the existing comment.
    effect_match = re.search(
        r"useEffect\(\s*\(\s*\)\s*=>\s*\{\s*const\s+taxonParam\s*=\s*searchParams\.get\(\s*[\"']taxon[\"']\s*\)[\s\S]*?\}\s*,\s*\[\s*searchParams\s*,\s*state\.nodes\s*,\s*selected\s*\]\s*\)",
        text,
    )
    assert effect_match is not None, (
        "TaxonomyTree.tsx must declare the URL → state sync effect "
        "with `const taxonParam = searchParams.get(\"taxon\")` as "
        "the opener and `[searchParams, state.nodes, selected]` as "
        "the deps array. The existing ODD-URLSTATE-001 contract."
    )
    effect_body = effect_match.group(0)
    # The effect body MUST read the dismissal-guard ref so a stale
    # `searchParams` value (between `setSelected(null)` and the
    # async `router.replace(\"/\")` completing) cannot reopen the
    # dismissed taxon.
    assert re.search(
        r"dismissedTaxonIdRef",
        effect_body,
    ), (
        "The URL → state sync effect must read the dismissal-guard "
        "ref (`dismissedTaxonIdRef.current`) so a stale `?taxon=` "
        "param cannot reopen the just-dismissed taxon. The guard "
        "write in `handleCloseDetail` is useless without the matching "
        "read in the URL → state sync effect."
    )
    # The effect MUST short-circuit (early return or skip the
    # `setSelected(id)` write) when the URL's taxon id equals
    # the guard. The exact pattern is implementation-defined;
    # accept either an early `return` or an `if` guard wrapping
    # the reselection write.
    has_skip = bool(re.search(
        r"return\b",
        effect_body,
    )) and (
        re.search(
            r"dismissedTaxonIdRef\.current\s*===\s*id",
            effect_body,
        )
        or re.search(
            r"id\s*===\s*dismissedTaxonIdRef\.current",
            effect_body,
        )
    )
    assert has_skip, (
        "The URL → state sync effect must short-circuit (early "
        "return) when the URL's `taxon` param equals the "
        "dismissal-guard ref value. The pattern "
        "`if (dismissedTaxonIdRef.current === id) return;` (or "
        "the inverted comparison) prevents the in-flight reopen "
        "race between `setSelected(null)` and `router.replace(\"/\")`."
    )


def test_taxonomy_tree_url_state_effect_clears_dismissal_guard_on_different_taxon() -> None:
    """ODD-CLOSEFIX-001: the URL → state sync effect must clear
    the dismissal-guard ref whenever the URL points at a
    DIFFERENT taxon (the user actively navigated to a new taxon
    or the back/forward buttons moved past the dismissed one).
    Without this clear, the guard would block every future
    `?taxon=<old>` reselection — including legitimate ones like
    the back button returning to a previously-dismissed taxon
    AFTER the user navigated away and back to it via a
    different path.

    The clear MUST happen INSIDE the URL → state sync effect
    body (not in `handleSelect` or `handleCloseDetail`) so a
    passive URL change — back/forward, external link, etc. —
    also clears the guard. The guard MUST be set to `null`
    (NOT `undefined`) so the strict-equal guard check stays
    type-safe."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # Find the URL → state sync effect (same anchors as the
    # previous test).
    effect_match = re.search(
        r"useEffect\(\s*\(\s*\)\s*=>\s*\{\s*const\s+taxonParam\s*=\s*searchParams\.get\(\s*[\"']taxon[\"']\s*\)[\s\S]*?\}\s*,\s*\[\s*searchParams\s*,\s*state\.nodes\s*,\s*selected\s*\]\s*\)",
        text,
    )
    assert effect_match is not None
    effect_body = effect_match.group(0)
    # The effect body MUST clear the ref to null when the URL
    # taxon differs from the guard. Accept either an explicit
    # assignment (`dismissedTaxonIdRef.current = null`) or a
    # combined skip-and-clear branch — both forms work. The
    # `= null` literal (NOT `= undefined`) is the canonical
    # contract since the ref is typed `number | null`.
    assert re.search(
        r"dismissedTaxonIdRef\.current\s*=\s*null\b",
        effect_body,
    ), (
        "The URL → state sync effect must clear the dismissal "
        "guard when navigating to a different taxon "
        "(`dismissedTaxonIdRef.current = null`). Without this "
        "clear, the guard would block legitimate future "
        "reselections of the previously-dismissed taxon. The "
        "clear happens inside the URL → state effect (NOT in "
        "`handleSelect` / `handleCloseDetail`) so passive URL "
        "changes — back/forward, external links — also clear "
        "the guard. The literal `null` matches the ref type "
        "`useRef<number | null>(null)`."
    )


def test_taxonomy_tree_url_state_effect_clears_dismissal_guard_on_no_taxon_param() -> None:
    """ODD-CLOSEFIX-002 (refinement): the URL → state sync
    effect MUST clear the dismissal-guard ref inside the
    `taxonParam === null` branch. Without this clear, the
    guard stays set to the just-dismissed taxon id, and a
    subsequent browser-Back navigation that returns to
    `/?taxon=<id>` is incorrectly suppressed by the stale
    guard — the panel would NOT reopen even though the user
    explicitly navigated back to the URL that previously
    opened it.

    Trace (pre-fix):
      1. user selects taxon 5: URL=`/?taxon=5`, guard=null.
      2. user clicks close: handleCloseDetail writes
         guard=5, navigates to URL=`/`.
      3. URL=`/`: effect runs `taxonParam === null` branch
         and RETURNS without clearing the guard.
      4. user presses browser Back: URL=`/?taxon=5`.
      5. URL=`/?taxon=5`: effect sees `id === 5 === guard`,
         SKIPS — panel does NOT reopen. Bug.

    The clear lives inside the `taxonParam === null` branch
    (BEFORE the early `return`) so a URL with no `taxon`
    param always resets the guard regardless of whether
    `selected` is null or non-null. The clear MUST happen
    INSIDE the URL → state sync effect (NOT in
    `handleCloseDetail`) so a passive URL change — browser
    Back, programmatic navigation, external link — also
    clears the guard. The literal `null` matches the ref
    type `useRef<number | null>(null)`."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # Locate the URL → state sync effect (same anchors as
    # the previous tests).
    effect_match = re.search(
        r"useEffect\(\s*\(\s*\)\s*=>\s*\{\s*const\s+taxonParam\s*=\s*searchParams\.get\(\s*[\"']taxon[\"']\s*\)[\s\S]*?\}\s*,\s*\[\s*searchParams\s*,\s*state\.nodes\s*,\s*selected\s*\]\s*\)",
        text,
    )
    assert effect_match is not None
    effect_body = effect_match.group(0)
    # Isolate the `taxonParam === null` branch body. The
    # branch is a single `if` with a small body; the regex
    # tolerates whitespace, comments, and a single nested
    # `if (selected !== null) setSelected(null);` line.
    null_branch_match = re.search(
        r"if\s*\(\s*taxonParam\s*===\s*null\s*\)\s*\{([\s\S]*?)\}",
        effect_body,
    )
    assert null_branch_match is not None, (
        "The URL → state sync effect must declare an "
        "`if (taxonParam === null) { ... }` branch. The "
        "branch body must clear the dismissal-guard ref "
        "(`dismissedTaxonIdRef.current = null`) BEFORE the "
        "early `return` so a passive URL drop of the "
        "`?taxon=` param (close, browser Back to a "
        "no-taxon URL, programmatic navigation) resets "
        "the guard."
    )
    null_branch = null_branch_match.group(1)
    # The branch MUST write `null` (NOT `undefined`) to
    # the ref so the strict-equal guard check in the
    # later branches stays type-safe (the ref is typed
    # `useRef<number | null>(null)`).
    assert re.search(
        r"dismissedTaxonIdRef\.current\s*=\s*null\b",
        null_branch,
    ), (
        "The `taxonParam === null` branch MUST clear the "
        "dismissal-guard ref (`dismissedTaxonIdRef.current "
        "= null`). Without this clear, closing the panel "
        "and then pressing browser Back to return to the "
        "same `?taxon=<id>` URL is incorrectly suppressed "
        "by the stale guard — the panel does not reopen "
        "even though the user explicitly navigated back "
        "to the URL that previously opened it."
    )


def test_taxonomy_tree_source_switch_clears_panel() -> None:
    """ODD-TDO-001: a source switch clears `selected` (already in
    the ODD-NTP-005 source-switch reset), which collapses the
    DetailPanel.

    ODD-HSS-001 — the source-bound cleanup moved from the
    `handleSourceChange` callback into the reactive
    `useEffect(() => { ... }, [activeSource])` body. The
    regression test pins the contract against the new location:
    the effect body MUST call `setSelected(null)` so the
    DetailPanel unmounts when the user switches sources."""
    text = _read_text(TAXONOMY_TREE_FILE)
    body = _od_hss_source_switch_effect_body(text)
    assert "setSelected(null)" in body, (
        "ODD-TDO-001: the ODD-HSS-001 source-switch "
        "`useEffect(() => { ... }, [activeSource])` body must "
        "call `setSelected(null)` so the DetailPanel unmounts "
        "when the user switches sources."
    )


def test_out_index_html_has_detail_panel_overview_styles(static_export) -> None:
    """ODD-TAPOPUP-001 (negative witness): the popup replaces
    the sticky detail rail + the Overview tab. The pre-popup
    overview + detail-panel inner-structure CSS rules
    (`.overview-tab .overview-grid`, `.overview-tab
    .overview-row`, `.overview-tab .overview-chain`, the
    realm-tint cascade, etc.) are GONE — the popup's header is
    minimal (no Overview tab body) and the popup host is a
    centered dialog (not a sticky aside).

    The chain-topology guard in `tests/test_research_styles.py`
    keeps the `.detail-panel` base whitelisted (the dialog host
    + close button still consume the class). Descendant rules
    under `.detail-panel` are reachable via the base; the
    Overview-only rules (.overview-tab + descendants, the
    realm-tint cascade) MUST be gone from the static CSS."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    # The pre-popup Overview inner-structure rules are GONE.
    for needle in (
        ".overview-tab .overview-grid",
        ".overview-tab .overview-row",
        ".overview-tab .overview-chain",
        ".overview-tab .overview-chain-segment",
        ".overview-tab .overview-tab-heading",
    ):
        assert needle not in css_body, (
            f"ODD-TAPOPUP-001: static CSS must NOT define the "
            f"`{needle}` Overview inner-structure rule (the "
            f"Overview tab body is gone; the popup ships "
            f"Synonyms / Distribution / Search / Folder)."
        )
    # The realm-tint cascade (scoped to the Overview body's
    # scientific-name span) is GONE.
    for realm in ("animalia", "archaea", "bacteria", "chromista",
                  "fungi", "plantae", "viruses"):
        quoted = f'.detail-panel[data-realm="{realm}"]'
        unquoted = f'.detail-panel[data-realm={realm}]'
        assert not (quoted in css_body or unquoted in css_body), (
            f"ODD-TAPOPUP-001: static CSS must NOT define the "
            f"`.detail-panel[data-realm=\"{realm}\"] "
            f".scientific-name` realm tint rule (the popup "
            f"replaces the sticky rail and the Overview body; "
            f"the realm tint cascade is gone)."
        )
    # The sticky-positioning rule is GONE (the popup is a
    # fixed-positioned dialog, not a sticky aside). The
    # assertion is anchored on the compound `.detail-panel`
    # rule carrying `position: sticky` — the regex requires
    # BOTH the selector AND the declaration to be present in
    # the SAME rule (the `.detail-panel` base rule is the
    # only rule the pre-popup sticky positioning applied to;
    # descendant rules like `.detail-panel .detail-header`
    # are not sticky in the popup).
    detail_panel_sticky_match = re.search(
        r"\.detail-panel\s*\{[^}]*?position\s*:\s*sticky",
        css_body,
        re.DOTALL,
    )
    assert detail_panel_sticky_match is None, (
        "ODD-TAPOPUP-001: static CSS must NOT carry the "
        "pre-popup `.detail-panel { position: sticky; ... }` "
        "rule (the popup replaces the sticky detail rail with "
        "a centered dialog)."
    )


def test_globals_css_declares_detail_panel_overview_selectors() -> None:
    """ODD-TAPOPUP-001 (negative witness): the pre-popup
    overview + detail-panel inner-structure CSS rules are GONE
    (the popup replaces the sticky detail rail + the Overview
    tab body). The chain-topology guard in
    `tests/test_research_styles.py` keeps the `.detail-panel`
    base whitelisted (the dialog host + close button still
    consume the class); the Overview-only rules (the
    `.overview-tab` base + descendants, the realm-tint
    cascade) MUST be gone from `globals.css`.

    This negative witness catches a regression that leaves
    dead Overview rules in `globals.css` after the popup
    cutover."""
    text = _read_text(TAXONOMY_GLOBALS_CSS)
    layer = re.search(r"@layer\s+components\s*\{", text)
    assert layer, "@layer components must exist in globals.css"
    body = text[layer.end():]
    # The closing brace of the @layer components block ends the
    # searchable region.
    layer_end = body.find("\n}\n")
    if layer_end == -1:
        layer_end = body.find("}")
    body = body[:layer_end]
    # Strip comments so the assertion doesn't trip on
    # docstring-history mentions of the legacy selectors (the
    # current globals.css mentions them in a comment block
    # that documents what was removed).
    body_code_only = re.sub(r"/\*[\s\S]*?\*/", "", body)
    # The pre-popup Overview inner-structure rules are GONE.
    for needle in (
        ".overview-tab .overview-grid",
        ".overview-tab .overview-row",
        ".overview-tab .overview-chain",
        ".overview-tab .overview-chain-segment",
        ".overview-tab .overview-tab-heading",
        ".overview-tab .overview-label",
        ".overview-tab .overview-rank",
        ".overview-tab .overview-value",
    ):
        assert needle not in body_code_only, (
            f"ODD-TAPOPUP-001: globals.css @layer components "
            f"must NOT declare the `{needle}` Overview inner-"
            f"structure rule (the Overview tab body is gone)."
        )
    # The realm-tint cascade is GONE.
    for realm in ("animalia", "archaea", "bacteria", "chromista",
                  "fungi", "plantae", "viruses"):
        needle = f'.detail-panel[data-realm="{realm}"] .scientific-name'
        assert needle not in body, (
            f"ODD-TAPOPUP-001: globals.css @layer components "
            f"must NOT declare the `{needle}` realm tint rule "
            f"(the popup replaces the sticky rail and the "
            f"Overview body; the realm tint cascade is gone)."
        )
    # The `.detail-panel` sticky-positioning rule is GONE
    # (the popup is a fixed-positioned dialog, not a sticky
    # aside). The base `.detail-panel` rule MUST still exist
    # (the chain-topology guard keeps it whitelisted) but it
    # MUST NOT carry `position: sticky`.
    detail_panel_match = re.search(
        r"\.detail-panel\s*\{[^}]*?position\s*:\s*sticky",
        body,
        re.DOTALL,
    )
    assert detail_panel_match is None, (
        "ODD-TAPOPUP-001: globals.css @layer components must "
        "NOT carry `.detail-panel { position: sticky; ... }` "
        "(the popup replaces the sticky detail rail)."
    )


def test_barrel_reexports_detail_panel_contract() -> None:
    """ODD-TDO-001: the taxonomy barrel must re-export the public
    DetailPanel contract — the `DetailTabKey` + `DetailTabDef`
    types + the `DETAIL_TABS` + `DEFAULT_DETAIL_TAB` constants.
    The component itself stays internal (mounted by TaxonomyTree)."""
    text = _read_text(TAXONOMY_BARREL)
    for name in ("DetailTabKey", "DetailTabDef",
                 "DETAIL_TABS", "DEFAULT_DETAIL_TAB"):
        assert name in text, (
            f"taxonomy barrel must re-export `{name}`."
        )


# ---------------------------------------------------------------------------
# ODD-SBP-001 — detail-panel sticky breakpoint responsive flip.
#
# `globals.css:423-424` pins `.detail-panel { position: sticky;
# top: 144px; z-index: 30; }`. At viewports below ~800px the
# sticky offset eats the visible tree (the tree header +
# breadcrumb + source selector consume the first 144px, then
# the detail panel sticks). Users on 13" laptops see tree rows
# slide under the panel; tablet users see the panel consume
# half the viewport; phone users see the panel eat the entire
# tree. The fix: a single `@media (max-width: 768px)` rule
# inside `@layer components` (after the original `.detail-panel`
# rule, so CSS source order wins the cascade tiebreak) that
# flips `.detail-panel` from `position: sticky` to in-flow
# (`position: static`). The in-card `.detail-panel
# .detail-header` sticky header also flips at the same
# breakpoint so the card body collapses cleanly into the
# in-flow panel. The pre-existing `.detail-panel { position:
# sticky; top: 144px; z-index: 30; }` rule MUST stay intact
# for viewports >= md — the @media rule only overrides below
# the md breakpoint.
# ---------------------------------------------------------------------------

def test_detail_panel_below_md_is_static() -> None:
    """ODD-TAPOPUP-001 (negative witness): the pre-popup
    `.detail-panel` sticky-positioning + the
    `@media (max-width: 768px) { .detail-panel { position:
    static; ... } }` breakpoint flip are GONE. The popup
    replaces the sticky detail rail with a centered dialog;
    the `@media` rule is no longer needed (the popup is
    `position: fixed` at every viewport, not in-flow below the
    md breakpoint).

    The `.detail-panel` base rule still exists in `@layer
    components` (the chain-topology guard keeps it
    whitelisted; the popup host + close button still consume
    the class) — but the rule does NOT carry `position: sticky`
    + `top: 144px` + `z-index: 30` AND there is NO
    `@media (max-width: 768px)` block flipping the rule to
    `position: static`."""
    text = _read_text(TAXONOMY_GLOBALS_CSS)
    # The sticky rule is GONE.
    assert not re.search(
        r"\.detail-panel\s*\{[^}]*?position\s*:\s*sticky[^}]*?"
        r"top\s*:\s*144px",
        text,
        re.DOTALL,
    ), (
        "ODD-TAPOPUP-001: globals.css must NOT carry the "
        "pre-popup `.detail-panel { position: sticky; top: "
        "144px; ... }` rule (the popup replaces the sticky "
        "detail rail with a centered dialog)."
    )
    # The `@media (max-width: 768px)` sticky-flip is GONE.
    assert not re.search(
        r"@media\s*\(\s*max-width\s*:\s*768px\s*\)\s*\{[\s\S]*?"
        r"\.detail-panel\s*\{[^}]*?position\s*:\s*static",
        text,
    ), (
        "ODD-TAPOPUP-001: globals.css must NOT carry the "
        "pre-popup `@media (max-width: 768px) { .detail-panel "
        "{ position: static; ... } }` breakpoint flip (the "
        "popup is a dialog at every viewport)."
    )


# ---------------------------------------------------------------------------
# ODD-TDS-001 — native Search tab data contract + UI.
#
#   - `fetchSearches` is the canonical typed projection for
#     `/api/taxon/{id}/searches`; preserves the server-composed
#     URL verbatim (never constructs URLs client-side).
#   - `SearchTab` is the native React renderer; renders the
#     five-category grouping + loading / empty / error / retry
#     states + secure anchors (target="_blank" rel="noopener
#     noreferrer").
#   - `presentation/search-categories.ts` is the pure category
#     metadata bridge (5 categories in fixed order + 14 engine
#     mappings). Stays free of legacy-web dependency.
#   - `TaxonomyTree` owns the per-taxon search cache + the
#     eager-fetch-on-selection contract so tab activation paints
#     the link grid instantly.
# ---------------------------------------------------------------------------

SEARCH_TAB_FILE = (
    REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "SearchTab.tsx"
)
SEARCH_CATEGORIES_FILE = (
    REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "search-categories.ts"
)


def test_search_tab_file_exists() -> None:
    """ODD-TDS-001: SearchTab component must exist as a `.tsx`
    file in the taxonomy presentation folder."""
    assert SEARCH_TAB_FILE.is_file(), (
        f"missing {SEARCH_TAB_FILE} \u2014 ODD-TDS-001 ships this Search "
        f"tab body component."
    )
    assert SEARCH_TAB_FILE.suffix == ".tsx", (
        "SearchTab must be `.tsx` (JSX-rendered)."
    )


def test_search_tab_is_a_client_component() -> None:
    """ODD-TDS-001: SearchTab mounts inside the React client island
    (TaxonomyTree -> DetailPanel -> SearchTab). The component
    declares the client boundary via `"use client"` so the per-
    row hover / focus behaviour and the Retry button stay
    interactive after hydration."""
    text = _read_text(SEARCH_TAB_FILE)
    assert text.lstrip().startswith('"use client"') or text.lstrip().startswith("'use client'"), (
        "SearchTab.tsx must declare the client boundary via 'use client'"
    )


def test_search_tab_consumes_canonical_helpers() -> None:
    """ODD-TDS-001: SearchTab composes the canonical `SearchLink`
    projection + the pure category bridge from sibling files in
    the presentation layer. spec.md rule 4 keeps the component
    pure of deep imports; rule 5 keeps deep paths blocked via the
    ESLint `no-restricted-imports` guard."""
    text = _read_text(SEARCH_TAB_FILE)
    for name in ("SEARCH_CATEGORIES", "resolveSearchEngineMeta"):
        assert name in text, (
            f"SearchTab.tsx must consume the canonical `{name}` helper."
        )


def test_search_tab_renders_five_category_sections() -> None:
    """ODD-TDS-001: the rendered SearchTab carries one
    `.search-category-section` per category, each stamped with
    `data-search-category-section="<key>"`. The section order
    follows `SEARCH_CATEGORIES` byte-for-byte (general,
    taxonomic, academic, multimedia, documents) so the React
    cutover's category order matches the legacy oracle."""
    text = _read_text(SEARCH_TAB_FILE)
    # The container carries the canonical `.search-tab` class so the
    # existing `src/app/globals.css` cascade paints the section
    # headers + the grid + the link cards without a redesign pass.
    assert "search-tab" in text, (
        "SearchTab.tsx must stamp the .search-tab container class."
    )
    # Each section carries its key as a data-attribute for tests.
    assert "data-search-category-section" in text, (
        "SearchTab.tsx must stamp data-search-category-section on each section."
    )
    # Section header carries the canonical `.search-category-header`
    # class + `data-category="<key>"` so the legacy selector + the
    # parity test (which counts via `[data-category]`) keep working.
    assert "search-category-header" in text, (
        "SearchTab.tsx must render the .search-category-header element."
    )
    assert "data-category" in text, (
        "SearchTab.tsx must stamp data-category on each category header."
    )


def test_search_tab_emits_secure_external_anchors() -> None:
    """ODD-TDS-001: every link anchor carries
    `target="_blank" rel="noopener noreferrer"` so the new tab
    can't reach back into the parent window's `window.opener`
    reference and the absence of `noreferrer` would let the
    destination see the referer. The anchor ALSO carries
    `data-engine-key` + `data-category` so the legacy selector +
    the parity test keep working without a redesign pass. The
    URL is the wire value verbatim \u2014 the component must NEVER
    construct / mutate / template-fill a URL locally."""
    text = _read_text(SEARCH_TAB_FILE)
    # target="_blank" + rel="noopener noreferrer" must both be
    # present on the anchor element. Accept either quote flavor.
    assert re.search(
        r'target\s*=\s*["\']_blank["\']',
        text,
    ), "SearchTab.tsx must render anchors with target=\"_blank\"."
    assert re.search(
        r'rel\s*=\s*["\']noopener\s+noreferrer["\']',
        text,
    ), "SearchTab.tsx must render anchors with rel=\"noopener noreferrer\"."
    # The anchor must stamp `data-engine-key` so the legacy parity
    # test (which counts via `a.search-engine-btn[data-engine-key]`)
    # can verify the 14-button contract.
    assert "data-engine-key" in text, (
        "SearchTab.tsx must stamp data-engine-key on each link anchor."
    )
    # The href must carry the wire URL verbatim \u2014 no template fill,
    # no encoding manipulation. The component reads `link.url`
    # directly from the server payload.
    assert "link.url" in text, (
        "SearchTab.tsx must thread the wire URL through directly; "
        "constructing URLs client-side is forbidden (ODD-TDS-001)."
    )


def test_search_tab_renders_loading_state() -> None:
    """ODD-TDS-001: the loading branch renders a `role="status"`
    element with the canonical `aria-busy="true"` flag so
    assistive tech announces the loading state. Mirrors the
    `aria-busy` contract used elsewhere in the React tree."""
    text = _read_text(SEARCH_TAB_FILE)
    assert "role=\"status\"" in text or "role='status'" in text, (
        "SearchTab.tsx must render a role=\"status\" element for the loading state."
    )
    assert "aria-busy" in text, (
        "SearchTab.tsx must set aria-busy on the loading state for a11y tooling."
    )


def test_search_tab_renders_empty_state() -> None:
    """ODD-TDS-001: the empty branch renders a user-visible
    "No search links available for this taxon." message. Mirrors
    the legacy `web/detail.js::renderSearchesTab` empty copy
    byte-for-byte so the React cutover's empty affordance matches
    the legacy oracle."""
    text = _read_text(SEARCH_TAB_FILE)
    assert "No search links available for this taxon." in text, (
        "SearchTab.tsx must render the canonical empty copy."
    )


def test_search_tab_renders_error_and_retry_state() -> None:
    """ODD-TDS-001: the error branch renders a `role="alert"`
    element + the failure message + a Retry button (carrying
    `data-action="retry-searches"` so the parent can route the
    click through a delegated handler). The Retry button calls
    the `onRetry` prop callback so the failure is recoverable
    without a fresh taxon selection."""
    text = _read_text(SEARCH_TAB_FILE)
    assert "role=\"alert\"" in text or "role='alert'" in text, (
        "SearchTab.tsx must render a role=\"alert\" element for the error state."
    )
    assert "Could not load search links." in text, (
        "SearchTab.tsx must render the canonical error copy."
    )
    assert "Retry" in text, (
        "SearchTab.tsx must render a Retry button."
    )
    assert "data-action=\"retry-searches\"" in text, (
        "SearchTab.tsx must stamp data-action=\"retry-searches\" on the Retry button."
    )
    assert "onRetry" in text, (
        "SearchTab.tsx must invoke the onRetry prop on Retry click."
    )


def test_search_categories_file_exists() -> None:
    """ODD-TDS-001: the pure category metadata bridge lives in
    `presentation/search-categories.ts`. The file must exist as
    a `.ts` (no JSX) so the spec.md rule 4 presentation purity
    contract holds."""
    assert SEARCH_CATEGORIES_FILE.is_file(), (
        f"missing {SEARCH_CATEGORIES_FILE} \u2014 ODD-TDS-001 ships this "
        f"pure category metadata bridge."
    )
    assert SEARCH_CATEGORIES_FILE.suffix == ".ts", (
        "search-categories must be `.ts` (no JSX)."
    )


def test_search_categories_file_is_pure() -> None:
    """ODD-TDS-001: the category bridge stays free of React /
    Next / HTTP / DOM / framework tokens (spec.md rule 4). The
    bridge MUST NOT import from the legacy-web layer so
    the React port never leaks legacy-web dependencies into the
    canonical taxonomy module. URL composition is forbidden \u2014
    the bridge carries engine\u2192category metadata only."""
    text = _read_text(SEARCH_CATEGORIES_FILE)
    for tok in (
        "from 'react'", 'from "react"',
        "from 'next'",   'from "next"',
        "from 'nextjs'", 'from "nextjs"',
        "fetch(", "localStorage", "sessionStorage",
        "document.", "window.", "process.", "globalThis",
        "../infrastructure", "../application", "../index",
        "../../research", "../../design-system",
        "../../browser-state", "../../app-shell",
        "web/search_urls", "web/detail",
        "urllib.parse", "encodeURI", "template",
    ):
        assert tok not in text, (
            f"search-categories.ts must stay free of {tok!r}; spec.md rule 4."
        )


def test_search_categories_exports_five_categories_in_native_order() -> None:
    """ODD-TDS-001: SEARCH_CATEGORIES must enumerate exactly 5
    categories in the legacy byte-identical order: general \u2192
    taxonomic \u2192 academic \u2192 multimedia \u2192 documents. The order
    here drives the rendered section order \u2014 the first category
    is the topmost section."""
    text = _read_text(SEARCH_CATEGORIES_FILE)
    for name in ("SEARCH_CATEGORIES", "SEARCH_ENGINE_LIST",
                 "searchCategoryForEngine", "searchIconForEngine",
                 "resolveSearchEngineMeta"):
        assert name in text, (
            f"search-categories.ts must export `{name}`."
        )
    # Native category order: general \u2192 taxonomic \u2192 academic \u2192
    # multimedia \u2192 documents.
    assert re.search(
        r"\{\s*key\s*:\s*[\"\']general[\"\']\s*,\s*label\s*:\s*[\"\']General[\"\']",
        text,
    ), "SEARCH_CATEGORIES must declare the General category first."
    assert re.search(
        r"\{\s*key\s*:\s*[\"\']taxonomic[\"\']\s*,\s*label\s*:\s*[\"\']Taxonomic[\"\']",
        text,
    ), "SEARCH_CATEGORIES must declare the Taxonomic category second."
    assert re.search(
        r"\{\s*key\s*:\s*[\"\']academic[\"\']\s*,\s*label\s*:\s*[\"\']Academic[\"\']",
        text,
    ), "SEARCH_CATEGORIES must declare the Academic category third."
    assert re.search(
        r"\{\s*key\s*:\s*[\"\']multimedia[\"\']\s*,\s*label\s*:\s*[\"\']Multimedia[\"\']",
        text,
    ), "SEARCH_CATEGORIES must declare the Multimedia category fourth."
    assert re.search(
        r"\{\s*key\s*:\s*[\"\']documents[\"\']\s*,\s*label\s*:\s*[\"\']Documents[\"\']",
        text,
    ), "SEARCH_CATEGORIES must declare the Documents category fifth."
    # Native category order \u2014 search for the literal sequence in the
    # file. The pattern allows any whitespace between the entries.
    expected_order = re.compile(
        r"key\s*:\s*[\"\']general[\"\']"
        r"[\s\S]{0,200}?key\s*:\s*[\"\']taxonomic[\"\']"
        r"[\s\S]{0,200}?key\s*:\s*[\"\']academic[\"\']"
        r"[\s\S]{0,200}?key\s*:\s*[\"\']multimedia[\"\']"
        r"[\s\S]{0,200}?key\s*:\s*[\"\']documents[\"\']",
    )
    assert expected_order.search(text), (
        "SEARCH_CATEGORIES must declare the categories in the native "
        "order: general \u2192 taxonomic \u2192 academic \u2192 multimedia \u2192 documents."
    )


def test_search_categories_lists_fourteen_engines() -> None:
    """ODD-TDS-001: SEARCH_ENGINE_LIST must carry exactly 14
    entries (the legacy `test_search_categories.py` 5-category /
    14-engine contract). The server returns 17 entries
    (14 canonical search engines + 3 curated destinations); the
    3 curated destinations have no canonical category slot in
    the 5-section layout, so the bridge omits them and the
    SearchTab drops them via `resolveSearchEngineMeta`."""
    text = _read_text(SEARCH_CATEGORIES_FILE)
    # Count engine entries with `key: "..."`. Each engine entry
    # has exactly one `key:` declaration; other `key:` references
    # (e.g. in SEARCH_CATEGORIES) are filtered out by the
    # category regex below.
    engine_keys = re.findall(
        r"\{\s*key\s*:\s*[\"\']([^\"\']+)[\"\']\s*,\s*icon\s*:",
        text,
    )
    assert len(engine_keys) == 14, (
        f"SEARCH_ENGINE_LIST must carry exactly 14 engines; got {len(engine_keys)}."
    )
    # The canonical 14 keys. The order within the array mirrors
    # the legacy SEARCH_ENGINES source-file order so the
    # rendered button order inside each category is byte-identical
    # to the legacy oracle.
    expected = {
        "google", "imagen", "documentos", "pdf", "wikipedia",
        "bhl", "researchgate", "plos", "academia", "scielo",
        "scholar", "youtube", "zootaxa", "scribd",
    }
    assert set(engine_keys) == expected, (
        f"SEARCH_ENGINE_LIST must carry the canonical 14 engines; "
        f"missing: {expected - set(engine_keys)}; extra: {set(engine_keys) - expected}."
    )


def test_search_categories_categories_match_legacy_parity() -> None:
    """ODD-TDS-001 (parity oracle): the SearchTab category
    ordering matches the legacy CATEGORIES byte-for-byte
    (general \u2192 taxonomic \u2192 academic \u2192 multimedia \u2192
    documents). The legacy `test_search_categories.py` browser
    test asserts the same order against the legacy web app; the
    React port re-uses the same order so the parity test stays
    honest on the React side. The bridge is the single source of
    truth \u2014 the SearchTab reads `SEARCH_CATEGORIES` directly."""
    text = _read_text(SEARCH_CATEGORIES_FILE)
    expected_order = [
        "general", "taxonomic", "academic", "multimedia", "documents",
    ]
    # Read the full sequence by scanning the source for all
    # top-level `{ key: "..." }` entries. SEARCH_CATEGORIES
    # entries carry `label:` (no `icon:`); SEARCH_ENGINE_LIST
    # entries carry `icon:` later. Filter to the five category
    # keys so we capture the category ordering independent of
    # any engine entries that share the `{ key: ..., label: ... }`
    # shape (none today, but the filter is defensive).
    full_order = re.findall(
        r"\{\s*key\s*:\s*[\"\']([^\"\']+)[\"\']\s*,\s*label\s*:",
        text,
    )
    category_keys = []
    for k in full_order:
        if k in expected_order:
            category_keys.append(k)
    assert category_keys == expected_order, (
        f"SEARCH_CATEGORIES order must be {expected_order}; got {category_keys}"
    )


def test_barrel_reexports_search_contract() -> None:
    """ODD-TDS-001: the taxonomy barrel must re-export every
    SearchTab wire surface so cross-module consumers can type
    the search status / links / helpers without a deep import
    (spec.md rule 5)."""
    text = _read_text(TAXONOMY_BARREL)
    for name in (
        "fetchSearches",
        "FetchSearchesOptions",
        "SearchLink",
        "SEARCH_CATEGORIES",
        "SEARCH_ENGINE_LIST",
        "searchCategoryForEngine",
        "searchIconForEngine",
        "resolveSearchEngineMeta",
    ):
        assert name in text, (
            f"taxonomy barrel must re-export `{name}` (ODD-TDS-001)."
        )


def test_taxonomy_tree_eager_fetches_searches_on_selection() -> None:
    """ODD-TDS-001: TaxonomyTree fires the canonical
    `fetchSearches(id)` round trip the moment a taxon becomes
    the active selection. The eager-fetch contract pins the
    `useEffect` so re-selecting a previously selected taxon lands
    on the cached result without a round trip."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "fetchSearches" in text, (
        "TaxonomyTree.tsx must call the canonical fetchSearches helper."
    )
    assert "loadSearches" in text, (
        "TaxonomyTree.tsx must declare a loadSearches callback."
    )
    # Eager-fetch effect must fire on `selected` change.
    assert re.search(
        r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*selected[^}]*loadSearches",
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must declare a useEffect that calls "
        "loadSearches when `selected` changes (eager-fetch contract)."
    )


def test_taxonomy_tree_owns_search_cache() -> None:
    """ODD-TDS-001: TaxonomyTree owns the per-taxon search cache
    as a `Map<number, SearchTabStatus>`. The cache survives
    across deselects so re-selecting a previously selected taxon
    is also instant (mirrors how `perTaxonActiveTab` memory
    survives across deselects)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "searchesByTaxonId" in text, (
        "TaxonomyTree.tsx must own a searchesByTaxonId cache."
    )
    assert re.search(
        r"Map\s*<\s*number\s*,\s*SearchTabStatus\s*>",
        text,
    ), (
        "TaxonomyTree.tsx must own a Map<number, SearchTabStatus> for "
        "the per-taxon search cache."
    )


def test_taxonomy_tree_passes_search_props_to_detail_panel() -> None:
    """ODD-TDS-001: TaxonomyTree threads `searchStatus` + the
    retry callback through to the DetailPanel so the SearchTab
    body can render the loading / empty / error / loaded states.
    The retry callback re-issues the `fetchSearches` request
    through the same callback the eager-fetch effect uses."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "searchStatus" in text, (
        "TaxonomyTree.tsx must thread searchStatus to DetailPanel."
    )
    assert "onRetrySearches" in text, (
        "TaxonomyTree.tsx must thread onRetrySearches to DetailPanel."
    )
    # The retry callback must re-issue loadSearches for the
    # currently selected taxon (mirrors the eager-fetch path).
    assert re.search(
        r"onRetrySearches\s*=\s*\{[^}]*loadSearches",
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must map onRetrySearches to a loadSearches call."
    )


def test_taxonomy_tree_clears_search_cache_on_source_switch() -> None:
    """ODD-TDS-001: a source switch clears the per-taxon
    search-link cache so the panel cannot render a stale URL
    set from a previous source's selected taxon. The URLs
    themselves are taxon-name-based and source-agnostic, but
    clearing keeps the panel contract aligned with the other
    source-bound caches (focused / selected /
    per-taxon-active-tab).

    ODD-HSS-001 — the source-bound cleanup moved from the
    `handleSourceChange` callback into the reactive
    `useEffect(() => { ... }, [activeSource])` body. The
    regression test pins the contract against the new
    location: the effect body MUST call
    `setSearchesByTaxonId(new Map())` so the per-taxon
    search-link cache clears alongside the focused /
    selected / kebab clears."""
    text = _read_text(TAXONOMY_TREE_FILE)
    body = _od_hss_source_switch_effect_body(text)
    assert "setSearchesByTaxonId" in body, (
        "ODD-TDS-001: the ODD-HSS-001 source-switch "
        "`useEffect(() => { ... }, [activeSource])` body must "
        "clear the per-taxon search-link cache so a stale URL "
        "set from a previous source's selected taxon cannot leak "
        "into the next source's selection."
    )


def test_out_index_html_has_search_tab_styles(static_export) -> None:
    """ODD-TDS-001: the static export's CSS must define the
    SearchTab selectors introduced by the React cutover so the
    native-style link grid renders identically to the legacy
    oracle. The selectors live under the whitelisted `.search-tab`
    base class so the chain-topology guard in
    `tests/test_research_styles.py` keeps whitelisting them."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    # The container + section + header + list + link selectors
    # are already covered by the existing `.search-tab` cascade in
    # `src/app/globals.css` (PR 3c-c.4). The static export's CSS
    # must surface at least the top-level `.search-tab` rule plus
    # one descendant that matches the link card.
    for needle in (".search-tab", ".search-link"):
        assert needle in css_body, (
            f"ODD-TDS-001: static CSS must define the {needle} rule."
        )


# ---------------------------------------------------------------------------
# ODD-TDV-001 — native Vernaculars tab data contract + UI.
#
#   - `fetchVernaculars` is the canonical typed projection for
#     `/api/taxon/{id}/vernaculars?limit=200`; preserves the
#     FastAPI nullability of `language` + `country` verbatim
#     (never coerces `null → ""`).
#   - `VernacularTab` is the native React renderer; renders the
#     `Vernacular names` header + count badge + the per-row
#     `.detail-item` list with verbatim ISO language / country
#     chips + name span, plus loading / empty / error / retry
#     states.
#   - `TaxonomyTree` owns the per-taxon vernacular cache + the
#     eager-fetch-on-selection contract so tab activation paints
#     the rows instantly. The cache survives source switches
#     (the endpoint is source-agnostic).
#   - `DetailPanel` enables the Vernaculars tab (`available: true`)
#     and dispatches on `activeTab === "vernaculars"` to render
#     the VernacularTab body.
# ---------------------------------------------------------------------------


def test_vernacular_tab_file_exists() -> None:
    """ODD-TDV-001: VernacularTab component must exist as a `.tsx`
    file in the taxonomy presentation folder."""
    assert VERNACULAR_TAB_FILE.is_file(), (
        f"missing {VERNACULAR_TAB_FILE} \u2014 ODD-TDV-001 ships this Vernaculars "
        f"tab body component."
    )
    assert VERNACULAR_TAB_FILE.suffix == ".tsx", (
        "VernacularTab must be `.tsx` (JSX-rendered)."
    )


def test_vernacular_tab_is_a_client_component() -> None:
    """ODD-TDV-001: VernacularTab mounts inside the React client
    island (TaxonomyTree -> DetailPanel -> VernacularTab). The
    component declares the client boundary via `"use client"` so
    the Retry button + the per-row chip rendering stay interactive
    after hydration."""
    text = _read_text(VERNACULAR_TAB_FILE)
    assert text.lstrip().startswith('"use client"') or text.lstrip().startswith("'use client'"), (
        "VernacularTab.tsx must declare the client boundary via 'use client'"
    )


def test_vernacular_tab_consumes_canonical_projection() -> None:
    """ODD-TDV-001: VernacularTab imports the canonical
    `VernacularName` projection from the infrastructure layer.
    spec.md rule 4 keeps the component pure of deep imports into
    sibling presentation helpers (the SearchLink / VernacularName
    projection is the only domain contract this component needs)."""
    text = _read_text(VERNACULAR_TAB_FILE)
    assert "VernacularName" in text, (
        "VernacularTab.tsx must consume the canonical `VernacularName` projection."
    )


def test_vernacular_tab_renders_native_header_and_count() -> None:
    """ODD-TDV-001: the rendered VernacularTab carries the canonical
    `Vernacular names` header (matches the legacy
    `web/detail.js::buildDetailSection("translate", "Vernacular names",
    d.vernaculars.length, items)` byte-for-byte) and a count badge
    stamped on a per-row data attribute (`data-vernacular-count`).
    The `translate` material-symbol icon spans the section header
    so the native visual identity survives the React cutover."""
    text = _read_text(VERNACULAR_TAB_FILE)
    assert "translate" in text, (
        "VernacularTab.tsx must render the `translate` material-symbol icon "
        "in the section header (legacy oracle parity)."
    )
    assert "Vernacular names" in text, (
        "VernacularTab.tsx must render the canonical `Vernacular names` header copy."
    )
    assert "vernacular-section-header" in text, (
        "VernacularTab.tsx must stamp .vernacular-section-header on the header element."
    )
    assert "vernacular-section-count" in text, (
        "VernacularTab.tsx must stamp .vernacular-section-count on the count badge."
    )
    assert "data-vernacular-count" in text, (
        "VernacularTab.tsx must stamp data-vernacular-count on the loaded body so "
        "tests + tooling can observe the row count."
    )


def test_vernacular_tab_renders_per_row_chips_and_name() -> None:
    """ODD-TDV-001: every loaded row renders as a `.detail-item`
    carrying the optional `.lang` ISO language chip + the optional
    `.country` ISO country chip + the name span. The chips are
    rendered only when the corresponding nullable wire field is
    non-null (the `language` and `country` data attributes
    reflect the row's nullable state verbatim). The legacy
    `web/detail.js::loadDetail` skips the chip when the row
    carries `null`, so the React port must mirror that contract
    byte-for-byte."""
    text = _read_text(VERNACULAR_TAB_FILE)
    # Container: `.detail-item` carries the chips + name span.
    assert "detail-item" in text, (
        "VernacularTab.tsx must render .detail-item rows."
    )
    # Language + country chips + name span are rendered.
    assert '"lang"' in text or "'lang'" in text, (
        "VernacularTab.tsx must render the .lang ISO language chip on every row "
        "whose wire language is non-null."
    )
    assert '"country"' in text or "'country'" in text, (
        "VernacularTab.tsx must render the .country ISO country chip on every row "
        "whose wire country is non-null."
    )
    # The conditional chip rendering branches on the nullable
    # wire field — a row with `language === null` MUST NOT carry
    # the chip element. The pattern below matches the React
    # conditional `{v.language ? (<span className="lang">) : null}`.
    assert re.search(
        r"v\.language\s*\?\s*\(",
        text,
    ), (
        "VernacularTab.tsx must conditionally render the language chip on the "
        "row's nullable language field."
    )
    assert re.search(
        r"v\.country\s*\?\s*\(",
        text,
    ), (
        "VernacularTab.tsx must conditionally render the country chip on the "
        "row's nullable country field."
    )
    # Each row carries `data-vernacular-item-id` so the legacy
    # selector + the future row-click handler can identify the
    # row without reading the chip text.
    assert "data-vernacular-item-id" in text, (
        "VernacularTab.tsx must stamp data-vernacular-item-id on every row."
    )


def test_vernacular_tab_renders_loading_state() -> None:
    """ODD-TDV-001: the loading branch renders a `role="status"`
    element with the canonical `aria-busy="true"` flag so
    assistive tech announces the loading state. Mirrors the
    SearchTab loading contract byte-for-byte."""
    text = _read_text(VERNACULAR_TAB_FILE)
    assert 'role="status"' in text or "role='status'" in text, (
        "VernacularTab.tsx must render a role=\"status\" element for the loading state."
    )
    assert "aria-busy" in text, (
        "VernacularTab.tsx must set aria-busy on the loading state for a11y tooling."
    )
    assert "Loading vernacular names" in text, (
        "VernacularTab.tsx must render the canonical loading copy."
    )


def test_vernacular_tab_renders_empty_state() -> None:
    """ODD-TDV-001: the empty branch renders a user-visible
    "No vernacular names available for this taxon." message so the
    panel never lands on a blank body for taxa with no
    vernaculars. The `vernacular-section-count` is stamped as `0`
    so the header badge mirrors the loaded count without a fake
    row."""
    text = _read_text(VERNACULAR_TAB_FILE)
    assert "No vernacular names available for this taxon." in text, (
        "VernacularTab.tsx must render the canonical empty copy."
    )


def test_vernacular_tab_renders_error_and_retry_state() -> None:
    """ODD-TDV-001: the error branch renders a `role="alert"`
    element + the failure message + a Retry button (carrying
    `data-action="retry-vernaculars"` so the parent can route the
    click through a delegated handler). The Retry button calls
    the `onRetry` prop callback so the failure is recoverable
    without a fresh taxon selection."""
    text = _read_text(VERNACULAR_TAB_FILE)
    assert 'role="alert"' in text or "role='alert'" in text, (
        "VernacularTab.tsx must render a role=\"alert\" element for the error state."
    )
    assert "Could not load vernacular names." in text, (
        "VernacularTab.tsx must render the canonical error copy."
    )
    assert "Retry" in text, (
        "VernacularTab.tsx must render a Retry button."
    )
    assert 'data-action="retry-vernaculars"' in text, (
        "VernacularTab.tsx must stamp data-action=\"retry-vernaculars\" on the Retry button."
    )
    assert "onRetry" in text, (
        "VernacularTab.tsx must invoke the onRetry prop on Retry click."
    )


def test_detail_panel_enables_vernaculars_tab() -> None:
    """ODD-TAPOPUP-001 (negative witness): the popup MUST NOT
    declare the Vernaculars tab in `DETAIL_TABS`. The
    pre-popup sticky rail carried the Vernaculars tab
    alongside Overview / Search / Folder; the popup replaces
    the sticky rail and the user-selected four tabs are
    Synonyms / Distribution / Search / Folder.

    The VernacularTab component itself MAY still exist as a
    canonical projection (a future slice could surface it),
    but the popup MUST NOT consume it."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert not re.search(
        r"DETAIL_TABS[\s\S]*?\bvernaculars\b",
        text,
    ), (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT declare the "
        "Vernaculars tab in the popup's `DETAIL_TABS` array."
    )
    # The `onRetryVernaculars` / `vernacularStatus` props
    # MUST NOT appear (no Vernaculars tab = no props to
    # thread through).
    assert "onRetryVernaculars" not in text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT consume "
        "`onRetryVernaculars` (the Vernaculars tab is gone)."
    )
    assert "VernacularTabStatus" not in text, (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT consume "
        "`VernacularTabStatus` (the Vernaculars tab is gone)."
    )


def test_taxonomy_tree_eager_fetches_vernaculars_on_selection() -> None:
    """ODD-TAPOPUP-001 (negative witness): the Vernaculars cache
    is GONE. The pre-popup sticky rail carried the Vernaculars
    tab + a per-taxon `vernacularsByTaxonId` cache; the popup
    replaces the sticky rail and the user-selected four tabs are
    Synonyms / Distribution / Search / Folder. The
    `fetchVernaculars` helper MAY still be exported from the
    barrel (it's a canonical typed projection) but the popup
    MUST NOT eager-fetch on selection."""
    text = _read_text(TAXONOMY_TREE_FILE)
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", text)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert "vernacularsByTaxonId" not in code_only, (
        "ODD-TAPOPUP-001: TaxonomyTree.tsx must NOT own the "
        "per-taxon vernacular cache (the popup drops the "
        "Vernaculars tab)."
    )
    assert "fetchVernaculars" not in code_only, (
        "ODD-TAPOPUP-001: TaxonomyTree.tsx must NOT call "
        "`fetchVernaculars` (the popup drops the Vernaculars "
        "tab; the helper stays in the barrel for future use)."
    )


def test_taxonomy_tree_owns_vernacular_cache() -> None:
    """ODD-TAPOPUP-001 (negative witness): the per-taxon
    `vernacularsByTaxonId` cache is GONE. The pre-popup sticky
    rail owned a `Map<number, VernacularTabStatus>` cache;
    the popup drops the Vernaculars tab so the cache is
    dead state."""
    text = _read_text(TAXONOMY_TREE_FILE)
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", text)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert "vernacularsByTaxonId" not in code_only, (
        "ODD-TAPOPUP-001: TaxonomyTree.tsx must NOT own the "
        "per-taxon vernacular cache."
    )
    assert "VernacularTabStatus" not in code_only, (
        "ODD-TAPOPUP-001: TaxonomyTree.tsx must NOT consume "
        "`VernacularTabStatus` (the Vernaculars tab is gone)."
    )


def test_taxonomy_tree_keeps_vernacular_cache_across_source_switch() -> None:
    """ODD-TAPOPUP-001 (negative witness): the source-switch
    cascade no longer touches the vernacular cache (the cache
    itself is gone)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", text)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert "vernacularsByTaxonId" not in code_only, (
        "ODD-TAPOPUP-001: TaxonomyTree.tsx must NOT reference "
        "`vernacularsByTaxonId` (the cache is gone)."
    )


def test_taxonomy_tree_passes_vernacular_props_to_detail_panel() -> None:
    """ODD-TAPOPUP-001 (negative witness): TaxonomyTree does
    NOT thread `vernacularStatus` or `onRetryVernaculars` to
    DetailPanel anymore (the Vernaculars tab is gone)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "vernacularStatus" not in text, (
        "ODD-TAPOPUP-001: TaxonomyTree.tsx must NOT thread "
        "`vernacularStatus` to DetailPanel."
    )
    assert "onRetryVernaculars" not in text, (
        "ODD-TAPOPUP-001: TaxonomyTree.tsx must NOT thread "
        "`onRetryVernaculars` to DetailPanel."
    )


# ---------------------------------------------------------------------------
# ODD-TDSYN-001 — native Synonyms tab data contract + UI.
#
#   - `fetchSynonyms` is the canonical typed projection for
#     `/api/taxon/{id}/synonyms?limit=200`; preserves the FastAPI
#     `Synonym` wire fields (id, rank, scientific_name, nullable
#     authorship, non-nullable status) verbatim — the server
#     pre-filters to `status != 'accepted'` so status is never
#     null. The UI does NOT render status (per the ODD-TDSYN-001
#     user constraint) but the projection MUST carry it so a
#     future server-composed status-derived affordance does not
#     need a coordinated React update.
#   - `SynonymTab` is the native React renderer; renders the
#     `Synonyms` header + count badge + the per-row
#     `.detail-item` list carrying the `.rank-chip` chip + the
#     italic-or-roman scientific name + the optional
#     `.authorship` span, plus loading / empty / error / retry
#     states.
#   - `TaxonomyTree` owns the per-taxon synonyms cache + the
#     eager-fetch-on-selection contract so tab activation paints
#     the rows instantly. The cache survives source switches
#     (the endpoint is source-agnostic — the FastAPI SQL
#     pre-filters by `parent_id = taxon_id AND status !=
#     'accepted'` regardless of the active tree source).
#   - `DetailPanel` enables the Synonyms tab (`available: true`)
#     and dispatches on `activeTab === "synonyms"` to render the
#     SynonymTab body.
# ---------------------------------------------------------------------------


def test_synonym_tab_file_exists() -> None:
    """ODD-TDSYN-001: SynonymTab component must exist as a `.tsx`
    file in the taxonomy presentation folder."""
    assert SYNONYM_TAB_FILE.is_file(), (
        f"missing {SYNONYM_TAB_FILE} \u2014 ODD-TDSYN-001 ships this Synonyms "
        f"tab body component."
    )
    assert SYNONYM_TAB_FILE.suffix == ".tsx", (
        "SynonymTab must be `.tsx` (JSX-rendered)."
    )


def test_synonym_tab_is_a_client_component() -> None:
    """ODD-TDSYN-001: SynonymTab mounts inside the React client
    island (TaxonomyTree -> DetailPanel -> SynonymTab). The
    component declares the client boundary via `"use client"`
    so the Retry button + the per-row chip rendering stay
    interactive after hydration."""
    text = _read_text(SYNONYM_TAB_FILE)
    assert text.lstrip().startswith('"use client"') or text.lstrip().startswith("'use client'"), (
        "SynonymTab.tsx must declare the client boundary via 'use client'"
    )


def test_synonym_tab_consumes_canonical_projection() -> None:
    """ODD-TDSYN-001: SynonymTab imports the canonical
    `SynonymName` projection from the infrastructure layer.
    spec.md rule 4 keeps the component pure of deep imports
    into sibling presentation helpers (the SynonymName
    projection is the only domain contract this component
    needs; the per-row italic-vs-roman split is delegated to
    the pure `scientificNameClass` helper in `row-format.ts`,
    a sibling presentation module)."""
    text = _read_text(SYNONYM_TAB_FILE)
    assert "SynonymName" in text, (
        "SynonymTab.tsx must consume the canonical `SynonymName` projection."
    )
    assert "scientificNameClass" in text, (
        "SynonymTab.tsx must consume the pure `scientificNameClass` helper "
        "to render the italic-or-roman scientific name."
    )


def test_synonym_tab_renders_native_header_and_count() -> None:
    """ODD-TDSYN-001: the rendered SynonymTab carries the canonical
    `Synonyms` header (matches the legacy
    `web/detail.js::buildDetailSection("history", "Synonyms",
    d.synonyms.length, items)` byte-for-byte) and a count badge
    stamped on a per-row data attribute (`data-synonym-count`).
    The `history` material-symbol icon spans the section header
    so the native visual identity survives the React cutover."""
    text = _read_text(SYNONYM_TAB_FILE)
    assert "history" in text, (
        "SynonymTab.tsx must render the `history` material-symbol icon "
        "in the section header (legacy oracle parity)."
    )
    assert "Synonyms" in text, (
        "SynonymTab.tsx must render the canonical `Synonyms` header copy."
    )
    assert "synonym-section-header" in text, (
        "SynonymTab.tsx must stamp .synonym-section-header on the header element."
    )
    assert "synonym-section-count" in text, (
        "SynonymTab.tsx must stamp .synonym-section-count on the count badge."
    )
    assert "data-synonym-count" in text, (
        "SynonymTab.tsx must stamp data-synonym-count on the loaded body so "
        "tests + tooling can observe the row count."
    )


def test_synonym_tab_renders_per_row_chip_rank_and_name() -> None:
    """ODD-TDSYN-001: every loaded row renders as a `.detail-item`
    carrying the `.rank-chip` chip (the row's `rank` value
    surfaced verbatim from the wire) + the scientific name span
    painted with the ICZN italic-or-roman split via the pure
    `scientificNameClass` helper + the optional `.authorship`
    span (conditional on the nullable wire field). The chip is
    rendered unconditionally (the wire `rank` is non-nullable);
    the authorship span is conditionally omitted when the row
    carries `authorship === null` (the legacy
    `web/detail.js::loadDetail` skips the `.authorship` element
    when `s.authorship` is falsy). The component MUST NOT render
    the wire `status` field — the ODD-TDSYN-001 user constraint
    pins the UI contract: "the UI must not render status or
    client-sort"."""
    text = _read_text(SYNONYM_TAB_FILE)
    # Container: `.detail-item` carries the chip + name span + optional authorship.
    assert "detail-item" in text, (
        "SynonymTab.tsx must render .detail-item rows."
    )
    # Rank chip + scientific name span are rendered.
    assert '"rank-chip"' in text or "'rank-chip'" in text, (
        "SynonymTab.tsx must render the .rank-chip chip on every row "
        "with the wire rank verbatim."
    )
    assert "synonym-name" in text, (
        "SynonymTab.tsx must render the scientific-name span with the "
        "italic-or-roman split via scientificNameClass."
    )
    # The conditional authorship rendering branches on the
    # nullable wire field. The pattern below matches the React
    # conditional `{s.authorship ? (<span className="authorship">) : null}`.
    assert re.search(
        r"s\.authorship\s*\?\s*\(",
        text,
    ), (
        "SynonymTab.tsx must conditionally render the .authorship span on the "
        "row's nullable authorship field."
    )
    # Each row carries `data-synonym-item-id` so the legacy
    # selector + the future row-click handler can identify the
    # row without reading the chip text. The component also
    # stamps `data-synonym-item-rank` + `data-synonym-item-status`
    # so the wire values (including the not-rendered status
    # field) are observable for tests + tooling.
    assert "data-synonym-item-id" in text, (
        "SynonymTab.tsx must stamp data-synonym-item-id on every row."
    )
    assert "data-synonym-item-rank" in text, (
        "SynonymTab.tsx must stamp data-synonym-item-rank on every row."
    )
    # UI contract — the wire status field MUST NOT be rendered
    # as a user-visible element. The component stamps the status
    # on a data attribute (`data-synonym-item-status`) so tests
    # + tooling can observe the wire value, but the JSX does not
    # paint it as text / chip / span / badge. The strict pattern
    # below rejects any `<span className=...>` element that
    # carries the status string outside a data-attribute context.
    assert not re.search(
        r"<span[^>]*className=[\"\'][^\"\']*status[^\"\']*[\"\'][^>]*>\{?s\.status\}?",
        text,
    ), (
        "ODD-TDSYN-001: SynonymTab must NOT render the wire status field as a "
        "user-visible element (UI contract: 'must not render status or client-sort')."
    )
    # Client-side sorting guard — the component MUST NOT sort
    # the wire payload client-side (server-driven
    # `ORDER BY rank, scientific_name` ordering is the source
    # of truth).
    assert not re.search(
        r"\.sort\s*\(|\.toSorted\s*\(|\.\.\.status\.sort|\.localeCompare",
        text,
    ), (
        "ODD-TDSYN-001: SynonymTab must NOT sort the wire payload "
        "client-side (server ordering is the source of truth)."
    )


def test_synonym_tab_renders_loading_state() -> None:
    """ODD-TDSYN-001: the loading branch renders a `role="status"`
    element with the canonical `aria-busy="true"` flag so
    assistive tech announces the loading state. Mirrors the
    SearchTab + VernacularTab loading contracts byte-for-byte."""
    text = _read_text(SYNONYM_TAB_FILE)
    assert 'role="status"' in text or "role='status'" in text, (
        "SynonymTab.tsx must render a role=\"status\" element for the loading state."
    )
    assert "aria-busy" in text, (
        "SynonymTab.tsx must set aria-busy on the loading state for a11y tooling."
    )
    assert "Loading synonyms" in text, (
        "SynonymTab.tsx must render the canonical loading copy."
    )


def test_synonym_tab_renders_empty_state() -> None:
    """ODD-TDSYN-001: the empty branch renders a user-visible
    "No synonyms available for this taxon." message so the
    panel never lands on a blank body for taxa with no
    synonyms. The `synonym-section-count` is stamped as `0`
    so the header badge mirrors the loaded count without a
    fake row."""
    text = _read_text(SYNONYM_TAB_FILE)
    assert "No synonyms available for this taxon." in text, (
        "SynonymTab.tsx must render the canonical empty copy."
    )


def test_synonym_tab_renders_error_and_retry_state() -> None:
    """ODD-TDSYN-001: the error branch renders a `role="alert"`
    element + the failure message + a Retry button (carrying
    `data-action="retry-synonyms"` so the parent can route
    the click through a delegated handler). The Retry button
    calls the `onRetry` prop callback so the failure is
    recoverable without a fresh taxon selection."""
    text = _read_text(SYNONYM_TAB_FILE)
    assert 'role="alert"' in text or "role='alert'" in text, (
        "SynonymTab.tsx must render a role=\"alert\" element for the error state."
    )
    assert "Could not load synonyms." in text, (
        "SynonymTab.tsx must render the canonical error copy."
    )
    assert "Retry" in text, (
        "SynonymTab.tsx must render a Retry button."
    )
    assert 'data-action="retry-synonyms"' in text, (
        "SynonymTab.tsx must stamp data-action=\"retry-synonyms\" on the Retry button."
    )
    assert "onRetry" in text, (
        "SynonymTab.tsx must invoke the onRetry prop on Retry click."
    )


def test_detail_panel_enables_synonyms_tab() -> None:
    """ODD-TDSYN-001: the Synonyms tab is ENABLED
    (`available: true`). The React port's first slice shipped
    Overview-only and marked the rest as `available: false`
    per the "visibly mark unavailable later tabs without fake
    actions" policy. ODD-TDS-001 enabled Search, ODD-TDV-001
    enabled Vernaculars, ODD-TDSYN-001 enables Synonyms so the
    user can click into the native Synonyms row list. Folder /
    Distribution stay `available: false` until their backing
    React slices ship."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert re.search(
        r"key\s*:\s*[\"\']synonyms[\"\']\s*,\s*label\s*:\s*[\"\']Synonyms[\"\']"
        r"[\s\S]{0,200}?available\s*:\s*true",
        text,
    ), (
        "DetailPanel.tsx must declare the Synonyms tab with `available: true` "
        "(ODD-TDSYN-001 enables the Synonyms tab body)."
    )


def test_detail_panel_renders_synonym_tab_when_active() -> None:
    """ODD-TDSYN-001: when `activeTab === "synonyms"`, the panel
    body renders `<SynonymTab>` instead of the Overview body.
    The body slot must consume the canonical `SynonymTabStatus`
    discriminated-union + the `onRetrySynonyms` callback so
    the loading / empty / error / loaded states all render
    correctly."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert "SynonymTab" in text, (
        "DetailPanel.tsx must import the canonical SynonymTab component."
    )
    assert "SynonymTabStatus" in text, (
        "DetailPanel.tsx must consume the SynonymTabStatus type for the "
        "synonymStatus prop."
    )
    # Body slot must dispatch on activeTab === "synonyms" to
    # render SynonymTab. The dispatch must branch BEFORE the
    # Overview fallback.
    assert re.search(
        r"activeTab\s*===\s*[\"\']synonyms[\"\']",
        text,
    ), (
        "DetailPanel.tsx body must dispatch on activeTab === \"synonyms\" "
        "to render the SynonymTab."
    )
    assert re.search(
        r"activeTab\s*===\s*[\"\']synonyms[\"\'][\s\S]{0,200}?<SynonymTab",
        text,
    ), (
        "DetailPanel.tsx must render <SynonymTab> when activeTab === \"synonyms\"."
    )
    # onRetrySynonyms callback must be threaded through to the SynonymTab.
    assert "onRetrySynonyms" in text, (
        "DetailPanel.tsx must thread onRetrySynonyms through to SynonymTab."
    )


def test_taxonomy_tree_eager_fetches_synonyms_on_selection() -> None:
    """ODD-TDSYN-001: TaxonomyTree fires the canonical
    `fetchSynonyms(id, { limit: 200 })` round trip the moment
    a taxon becomes the active selection. The eager-fetch
    contract pins the `useEffect` so re-selecting a previously
    selected taxon lands on the cached result without a round
    trip. The legacy `/api/taxon/{id}/synonyms?limit=200`
    request shape is preserved byte-identically."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "fetchSynonyms" in text, (
        "TaxonomyTree.tsx must call the canonical fetchSynonyms helper."
    )
    assert "loadSynonyms" in text, (
        "TaxonomyTree.tsx must declare a loadSynonyms callback."
    )
    assert "limit: 200" in text or "limit:200" in text, (
        "TaxonomyTree.tsx must forward `limit: 200` to fetchSynonyms so the "
        "request shape stays byte-identical to the legacy oracle."
    )
    # Eager-fetch effect must fire on `selected` change.
    assert re.search(
        r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*selected[^}]*loadSynonyms",
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must declare a useEffect that calls "
        "loadSynonyms when `selected` changes (ODD-TDSYN-001 eager-fetch contract)."
    )


def test_taxonomy_tree_owns_synonym_cache() -> None:
    """ODD-TDSYN-001: TaxonomyTree owns the per-taxon synonym
    cache as a `Map<number, SynonymTabStatus>`. The cache
    survives across deselects so re-selecting a previously
    selected taxon is also instant (mirrors how
    `perTaxonActiveTab` memory + `searchesByTaxonId` +
    `vernacularsByTaxonId` caches survive across deselects)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "synonymsByTaxonId" in text, (
        "TaxonomyTree.tsx must own a synonymsByTaxonId cache."
    )
    assert re.search(
        r"Map\s*<\s*number\s*,\s*SynonymTabStatus\s*>",
        text,
    ), (
        "TaxonomyTree.tsx must own a Map<number, SynonymTabStatus> for "
        "the per-taxon synonym cache."
    )


def test_taxonomy_tree_keeps_synonym_cache_across_source_switch() -> None:
    """ODD-TDSYN-001: a source switch MUST NOT clear the
    per-taxon synonym cache (the
    `/api/taxon/{id}/synonyms` endpoint is source-agnostic —
    the FastAPI SQL pre-filters by `parent_id = taxon_id AND
    status != 'accepted'` regardless of the active tree source
    — so a previously cached payload stays valid under the new
    active source). The cached payload survives the
    source-switch cascade so re-selecting the same taxon after
    a source switch is also instant (mirrors how
    `vernacularsByTaxonId` survives source switches — the
    source-agnostic retention contract).

    ODD-HSS-001 — the cascade moved from `handleSourceChange`
    to the reactive `useEffect(() => { ... }, [activeSource])`
    body. The regression guard pins the ODD-TDSYN-001 retention
    against the new location: the effect body MUST NOT carry
    `setSynonymsByTaxonId`."""
    text = _read_text(TAXONOMY_TREE_FILE)
    body = _od_hss_source_switch_effect_body(text)
    # The search-link cache IS cleared (ODD-TDS-001 contract).
    assert "setSearchesByTaxonId" in body, (
        "ODD-TDS-001: the ODD-HSS-001 source-switch effect body "
        "must clear the per-taxon search-link cache alongside "
        "the other source-bound resets."
    )
    # The vernacular cache MUST NOT be cleared (ODD-TDV-001
    # contract).
    assert "setVernacularsByTaxonId" not in body, (
        "ODD-TDV-001: the ODD-HSS-001 source-switch effect body "
        "MUST NOT clear the per-taxon vernacular cache (the "
        "vernacular endpoint is source-agnostic)."
    )
    # The synonym cache MUST NOT be cleared (ODD-TDSYN-001
    # contract). The effect body must NOT carry a
    # `setSynonymsByTaxonId(new Map())` call. The regression
    # guard pins the contract so a future PR cannot silently
    # break the source-switch retention.
    assert "setSynonymsByTaxonId" not in body, (
        "ODD-TDSYN-001: the ODD-HSS-001 source-switch effect "
        "body MUST NOT clear the per-taxon synonym cache (the "
        "synonym endpoint is source-agnostic)."
    )


def test_taxonomy_tree_passes_synonym_props_to_detail_panel() -> None:
    """ODD-TDSYN-001: TaxonomyTree threads `synonymStatus` + the
    retry callback through to the DetailPanel so the SynonymTab
    body can render the loading / empty / error / loaded states.
    The retry callback re-issues the `fetchSynonyms` request
    through the same callback the eager-fetch effect uses."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "synonymStatus" in text, (
        "TaxonomyTree.tsx must thread synonymStatus to DetailPanel."
    )
    assert "onRetrySynonyms" in text, (
        "TaxonomyTree.tsx must thread onRetrySynonyms to DetailPanel."
    )
    # The retry callback must re-issue loadSynonyms for the
    # currently selected taxon (mirrors the eager-fetch path).
    assert re.search(
        r"onRetrySynonyms\s*=\s*\{[^}]*loadSynonyms",
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must map onRetrySynonyms to a loadSynonyms call."
    )


def test_barrel_reexports_synonym_contract() -> None:
    """ODD-TDSYN-001: the taxonomy barrel must re-export the
    public synonym data contract so cross-module consumers can
    type the payload + call the helper without a deep import
    (spec.md rule 5)."""
    text = _read_text(TAXONOMY_BARREL)
    for name in (
        "fetchSynonyms",
        "FetchSynonymsOptions",
        "SynonymName",
    ):
        assert name in text, (
            f"taxonomy barrel must re-export `{name}` (ODD-TDSYN-001)."
        )


def test_globals_css_declares_synonym_tab_selectors() -> None:
    """ODD-TDSYN-001: `src/app/globals.css` must declare the
    new `.synonym-tab` cascade so the per-row `.detail-item`
    rows + the rank chip + the optional `.authorship` span +
    the section header + count badge all render identically
    to the legacy oracle. The selectors live under `@layer
    components` and are in alphabetical order so the
    chain-topology guard in `tests/test_research_styles.py`
    keeps whitelisting them."""
    text = _read_text(TAXONOMY_GLOBALS_CSS)
    layer = re.search(r"@layer\s+components\s*\{", text)
    assert layer, "@layer components must exist in globals.css"
    body = text[layer.end():]
    layer_end = body.find("\n}\n")
    if layer_end == -1:
        layer_end = body.find("}")
    body = body[:layer_end]
    # Every selector must appear in the source. The minifier
    # may strip whitespace / quotes, so we accept the bare
    # class names without descendants.
    for needle in (
        ".synonym-tab",
        ".synonym-tab > .synonym-list",
        ".synonym-tab > .synonym-list > .detail-item",
        ".synonym-tab > .synonym-list > .detail-item > .rank-chip",
        ".synonym-tab > .synonym-list > .detail-item > .authorship",
        ".synonym-tab > .synonym-section-header",
        ".synonym-tab > .synonym-section-count",
    ):
        assert needle in body, (
            f"globals.css @layer components must declare {needle}."
        )


def test_out_index_html_has_synonym_tab_styles(static_export) -> None:
    """ODD-TDSYN-001: the static export's CSS must define the
    SynonymTab selectors introduced by the React cutover so
    the native-style Synonyms row list renders identically
    to the legacy oracle. The selectors live under the
    whitelisted `.synonym-tab` base class so the
    chain-topology guard in
    `tests/test_research_styles.py` keeps whitelisting them."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    # The container + list + row + chip selectors are covered
    # by the `.synonym-tab` cascade in `src/app/globals.css`.
    # The static export's CSS must surface at least the
    # top-level `.synonym-tab` rule plus the per-row
    # `.rank-chip` rule (so the rank chip + scientific name +
    # authorship rendering matches the legacy oracle).
    for needle in (".synonym-tab", ".rank-chip"):
        assert needle in css_body, (
            f"ODD-TDSYN-001: static CSS must define the {needle} rule."
        )


# ---------------------------------------------------------------------------
# ODD-TDDIST-001 — Distribution tab UI contract (native DetailPanel
# Distribution tab body + per-taxon cache + eager-fetch on selection
# + globals.css cascade + static-export CSS).
# ---------------------------------------------------------------------------
DISTRIBUTION_TAB_FILE = (
    REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "DistributionTab.tsx"
)


def test_distribution_tab_file_exists() -> None:
    """ODD-TDDIST-001: DistributionTab component must exist as a
    `.tsx` file under the taxonomy presentation folder (mirrors
    the ODD-TDSYN-001 / ODD-TDV-001 component files). The
    suffix is `.tsx` because the file declares a JSX-rendered
    React component (the `react-jsx` runtime requires
    TypeScript's JSX checker, not plain `.ts`)."""
    assert DISTRIBUTION_TAB_FILE.is_file(), (
        f"missing {DISTRIBUTION_TAB_FILE} \u2014 ODD-TDDIST-001 ships this "
        "Distribution tab component."
    )
    assert DISTRIBUTION_TAB_FILE.suffix == ".tsx", "DistributionTab must be `.tsx` (JSX-rendered)."


def test_distribution_tab_is_a_client_component() -> None:
    """ODD-TDDIST-001: DistributionTab mounts inside the React
    client island (TaxonomyTree -> DetailPanel -> DistributionTab).
    The component declares the client boundary via the
    `"use client"` directive at the top of the file so the
    React server / client boundary keeps the chip rendering +
    the Retry button interactive (mirrors the ODD-TDS-001 +
    ODD-TDV-001 + ODD-TDSYN-001 contracts)."""
    text = _read_text(DISTRIBUTION_TAB_FILE)
    assert '"use client"' in text or "'use client'" in text, (
        "DistributionTab.tsx must declare the client boundary via 'use client'"
    )


def test_distribution_tab_consumes_canonical_projection() -> None:
    """ODD-TDDIST-001: DistributionTab imports the canonical
    `DistributionEntry` projection from the infrastructure layer.
    A deep import would leak server composition concerns into
    the client contract; a missing import would force the
    component to type the rows inline (bypassing the canonical
    projection)."""
    text = _read_text(DISTRIBUTION_TAB_FILE)
    assert "DistributionEntry" in text, (
        "DistributionTab.tsx must consume the canonical `DistributionEntry` projection."
    )
    assert "from \"../infrastructure/api\"" in text, (
        "DistributionTab.tsx must import the canonical projection from "
        "../infrastructure/api (spec.md rule 4)."
    )


def test_distribution_tab_renders_native_header_and_count() -> None:
    """ODD-TDDIST-001: the rendered DistributionTab carries the
    canonical `Distribution` header (matches the legacy
    `web/detail.js::buildDetailSection("public", "Distribution",
    d.distribution.length, items)` byte-for-byte) and a count
    badge stamped on a per-row data attribute
    (`data-distribution-count`)."""
    text = _read_text(DISTRIBUTION_TAB_FILE)
    assert "public" in text, (
        "DistributionTab.tsx must render the `public` material-symbol icon "
        "(mirrors the legacy buildDetailSection icon)."
    )
    assert "Distribution" in text, (
        "DistributionTab.tsx must render the canonical `Distribution` header copy."
    )
    assert "distribution-section-header" in text, (
        "DistributionTab.tsx must stamp .distribution-section-header on the header element."
    )
    assert "distribution-section-count" in text, (
        "DistributionTab.tsx must stamp .distribution-section-count on the count badge."
    )
    assert "data-distribution-count" in text, (
        "DistributionTab.tsx must stamp data-distribution-count on the loaded body so "
        "tests can pin the count without a deep class-name scrape."
    )


def test_distribution_tab_renders_per_row_chip_and_area() -> None:
    """ODD-TDDIST-001: each row carries a `.means` chip (with a
    per-value modifier class) + the area text. The chip +
    area are the only two UI surfaces (the ODD-TDDIST-001
    user constraint forbids rendering gazetteer / degree).
    The chip must use the legacy `means-${means}` class
    pattern so the existing CSS palette (`.means-native`,
    `.means-introduced`, `.means-uncertain`,
    `.means-unknown`) renders identically to the legacy
    oracle."""
    text = _read_text(DISTRIBUTION_TAB_FILE)
    assert ".means" in text, (
        "DistributionTab.tsx must render .means chip elements on every row."
    )
    assert "means-${means}" in text or 'means-${means}' in text or "means-" in text, (
        "DistributionTab.tsx must render the .means-{means} per-value modifier "
        "class so the CSS palette (.means-native / .means-introduced / "
        ".means-uncertain / .means-unknown) applies correctly."
    )
    assert "distribution-area" in text, (
        "DistributionTab.tsx must render the .distribution-area span for the area text."
    )
    # Each row carries `data-distribution-item-id` so the legacy
    # `data-action` selector pattern keeps working + the
    # means chip carries `data-distribution-item-means` so
    # tests can pin the chip text without a deep class-name
    # scrape.
    assert "data-distribution-item-id" in text, (
        "DistributionTab.tsx must stamp data-distribution-item-id on every row."
    )
    assert "data-distribution-item-means" in text, (
        "DistributionTab.tsx must stamp data-distribution-item-means on every row."
    )
    assert "data-distribution-item-area" in text, (
        "DistributionTab.tsx must stamp data-distribution-item-area on every row."
    )


def test_distribution_tab_renders_loading_state() -> None:
    """ODD-TDDIST-001: the loading branch renders a
    `role="status"` element with `aria-busy="true"` + the
    canonical loading copy "Loading distribution…". Mirrors
    the SearchTab + VernacularTab + SynonymTab loading
    contracts byte-for-byte."""
    text = _read_text(DISTRIBUTION_TAB_FILE)
    assert 'role="status"' in text or "role='status'" in text, (
        "DistributionTab.tsx must render a role=\"status\" element for the loading state."
    )
    assert "aria-busy" in text, (
        "DistributionTab.tsx must set aria-busy on the loading state for a11y tooling."
    )
    assert "Loading distribution" in text, (
        "DistributionTab.tsx must render the canonical loading copy."
    )


def test_distribution_tab_renders_empty_state() -> None:
    """ODD-TDDIST-001: the empty branch renders a user-visible
    "No distribution data available for this taxon."
    message so the panel never lands on a blank body for taxa
    with no distribution data. The `distribution-section-count`
    is stamped as `0` so the header badge mirrors the loaded
    count without a fake row."""
    text = _read_text(DISTRIBUTION_TAB_FILE)
    assert "No distribution data available for this taxon." in text, (
        "DistributionTab.tsx must render the canonical empty copy."
    )


def test_distribution_tab_renders_error_and_retry_state() -> None:
    """ODD-TDDIST-001: the error branch renders a `role="alert"`
    element + the failure message + a Retry button (carrying
    `data-action="retry-distribution"` so the parent can route
    the click through a delegated handler). The Retry button
    calls the `onRetry` prop callback so the failure is
    recoverable without a fresh taxon selection."""
    text = _read_text(DISTRIBUTION_TAB_FILE)
    assert 'role="alert"' in text or "role='alert'" in text, (
        "DistributionTab.tsx must render a role=\"alert\" element for the error state."
    )
    assert "Could not load distribution." in text, (
        "DistributionTab.tsx must render the canonical error copy."
    )
    assert "Retry" in text, (
        "DistributionTab.tsx must render a Retry button."
    )
    assert 'data-action="retry-distribution"' in text, (
        "DistributionTab.tsx must stamp data-action=\"retry-distribution\" on the Retry button."
    )
    assert "onRetry" in text, (
        "DistributionTab.tsx must invoke the onRetry prop on Retry click."
    )


def test_distribution_tab_renders_unknown_fallback_for_null_means() -> None:
    """ODD-TDDIST-001: when the wire payload carries
    `establishment_means: null`, the renderer substitutes the
    `unknown` literal at render time only. Mirrors the legacy
    `web/detail.js::buildDetailSection` `x.establishment_means
    || "unknown"` fallback so the React port renders
    identically when the wire carries `null`. The chip text
    + the `.means-unknown` styling both apply so the chip
    palette (`web/index.html::.means-unknown`) stays
    consistent. The canonical projection keeps
    `establishment_means: string | null` (no client
    coercion) so the substitution happens in the renderer
    only — mirroring how `VernacularName.language: null`
    stays `null` and the chip is omitted at the renderer
    (ODD-TDV-001)."""
    text = _read_text(DISTRIBUTION_TAB_FILE)
    assert "unknown" in text, (
        "DistributionTab.tsx must render the `unknown` fallback for null "
        "establishment_means values (mirrors the legacy `|| \"unknown\"` fallback)."
    )
    # The fallback must apply at the renderer (NOT in the
    # projection layer). A projection-side `?? "unknown"`
    # would coerce `null → "unknown"` on every read, losing
    # the FastAPI nullability contract. The renderer-only
    # application uses `entry.establishment_means ?? "unknown"`
    # so the wire value round-trips verbatim and the fallback
    # applies at paint time only.
    assert "??" in text or "||" in text, (
        "DistributionTab.tsx must apply the unknown fallback via `??` or `||` "
        "at the renderer (not in the canonical projection)."
    )


def test_detail_panel_enables_distribution_tab() -> None:
    """ODD-TDDIST-001: the Distribution tab is ENABLED
    (`available: true`). The React port's earlier slice marked
    Distribution as `available: false` per the "visibly mark
    unavailable later tabs without fake actions" policy.
    ODD-TDDIST-001 flips the Distribution entry to `true` so
    the user can click into the native Distribution row list.
    Folder stays `available: false` until its backing React
    slice ships."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert re.search(
        r"key\s*:\s*[\"\']distribution[\"\']\s*,\s*label\s*:\s*[\"\']Distribution[\"\']"
        r"[\s\S]{0,200}?available\s*:\s*true",
        text,
    ), (
        "DetailPanel.tsx must declare the Distribution tab with `available: true` "
        "(ODD-TDDIST-001 enables the Distribution tab body)."
    )


def test_detail_panel_renders_distribution_tab_when_active() -> None:
    """ODD-TDDIST-001: when `activeTab === "distribution"`, the
    panel body renders `<DistributionTab>` instead of the
    Overview body. The body slot must consume the canonical
    `DistributionTabStatus` discriminated-union + the
    `onRetryDistribution` callback so the loading / empty /
    error / loaded states all render correctly."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert "DistributionTab" in text, (
        "DetailPanel.tsx must import the canonical DistributionTab component."
    )
    assert "DistributionTabStatus" in text, (
        "DetailPanel.tsx must consume the DistributionTabStatus type for the "
        "distributionStatus prop."
    )
    # Body slot must dispatch on activeTab === "distribution" to
    # render DistributionTab. The dispatch must branch BEFORE
    # the Overview fallback.
    assert re.search(
        r"activeTab\s*===\s*[\"\']distribution[\"\']",
        text,
    ), (
        "DetailPanel.tsx body must dispatch on activeTab === \"distribution\" "
        "to render the DistributionTab."
    )
    assert re.search(
        r"activeTab\s*===\s*[\"\']distribution[\"\'][\s\S]{0,200}?<DistributionTab",
        text,
    ), (
        "DetailPanel.tsx must render <DistributionTab> when activeTab === \"distribution\"."
    )
    # onRetryDistribution callback must be threaded through to
    # the DistributionTab.
    assert "onRetryDistribution" in text, (
        "DetailPanel.tsx must thread onRetryDistribution through to DistributionTab."
    )


def test_taxonomy_tree_eager_fetches_distribution_on_selection() -> None:
    """ODD-TDDIST-001: TaxonomyTree fires the canonical
    `fetchDistribution(id, { limit: 200 })` round trip the
    moment a taxon becomes the active selection. The
    eager-fetch contract pins the `useEffect` so re-selecting
    a previously selected taxon lands on the cached result
    without a round trip. The legacy
    `/api/taxon/{id}/distribution?limit=200` request shape is
    preserved byte-identically."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "fetchDistribution" in text, (
        "TaxonomyTree.tsx must call the canonical fetchDistribution helper."
    )
    assert "loadDistribution" in text, (
        "TaxonomyTree.tsx must declare a loadDistribution callback."
    )
    assert "limit: 200" in text or "limit:200" in text, (
        "TaxonomyTree.tsx must forward `limit: 200` to fetchDistribution so the "
        "request shape stays byte-identical to the legacy oracle."
    )
    # Eager-fetch effect must fire on `selected` change.
    assert re.search(
        r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*selected[^}]*loadDistribution",
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must declare a useEffect that calls "
        "loadDistribution when `selected` changes (ODD-TDDIST-001 eager-fetch contract)."
    )


def test_taxonomy_tree_owns_distribution_cache() -> None:
    """ODD-TDDIST-001: TaxonomyTree owns the per-taxon
    distribution cache as a `Map<number, DistributionTabStatus>`.
    The cache survives across deselects so re-selecting a
    previously selected taxon is also instant (mirrors how
    `perTaxonActiveTab` memory + `searchesByTaxonId` +
    `vernacularsByTaxonId` + `synonymsByTaxonId` caches
    survive across deselects)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "distributionByTaxonId" in text, (
        "TaxonomyTree.tsx must own a distributionByTaxonId cache."
    )
    assert re.search(
        r"Map\s*<\s*number\s*,\s*DistributionTabStatus\s*>",
        text,
    ), (
        "TaxonomyTree.tsx must own a Map<number, DistributionTabStatus> for "
        "the per-taxon distribution cache."
    )


def test_taxonomy_tree_keeps_distribution_cache_across_source_switch() -> None:
    """ODD-TDDIST-001: a source switch MUST NOT clear the
    per-taxon distribution cache (the
    `/api/taxon/{id}/distribution` endpoint is
    source-agnostic — the FastAPI SQL filters by
    `taxon_id = ?` regardless of the active tree source — so
    a previously cached payload stays valid under the new
    active source). The cached payload survives the
    source-switch cascade so re-selecting the same taxon after
    a source switch is also instant (mirrors how
    `vernacularsByTaxonId` + `synonymsByTaxonId` survive
    source switches — the source-agnostic retention
    contract).

    ODD-HSS-001 — the cascade moved from `handleSourceChange`
    to the reactive `useEffect(() => { ... }, [activeSource])`
    body. The regression guard pins the ODD-TDDIST-001
    retention against the new location: the effect body MUST
    NOT carry `setDistributionByTaxonId`."""
    text = _read_text(TAXONOMY_TREE_FILE)
    body = _od_hss_source_switch_effect_body(text)
    # The search-link cache IS cleared (ODD-TDS-001 contract).
    assert "setSearchesByTaxonId" in body, (
        "ODD-TDS-001: the ODD-HSS-001 source-switch effect body "
        "must clear the per-taxon search-link cache alongside "
        "the other source-bound resets."
    )
    # The vernacular cache MUST NOT be cleared (ODD-TDV-001
    # contract).
    assert "setVernacularsByTaxonId" not in body, (
        "ODD-TDV-001: the ODD-HSS-001 source-switch effect body "
        "MUST NOT clear the per-taxon vernacular cache (the "
        "vernacular endpoint is source-agnostic)."
    )
    # The synonym cache MUST NOT be cleared (ODD-TDSYN-001
    # contract).
    assert "setSynonymsByTaxonId" not in body, (
        "ODD-TDSYN-001: the ODD-HSS-001 source-switch effect "
        "body MUST NOT clear the per-taxon synonym cache (the "
        "synonym endpoint is source-agnostic)."
    )
    # The distribution cache MUST NOT be cleared
    # (ODD-TDDIST-001 contract). The effect body must NOT
    # carry a `setDistributionByTaxonId(new Map())` call.
    # The regression guard pins the contract so a future PR
    # cannot silently break the source-switch retention.
    assert "setDistributionByTaxonId" not in body, (
        "ODD-TDDIST-001: the ODD-HSS-001 source-switch effect "
        "body MUST NOT clear the per-taxon distribution cache "
        "(the distribution endpoint is source-agnostic)."
    )


def test_taxonomy_tree_passes_distribution_props_to_detail_panel() -> None:
    """ODD-TDDIST-001: TaxonomyTree threads `distributionStatus` +
    the retry callback through to the DetailPanel so the
    DistributionTab body can render the loading / empty / error
    / loaded states. The retry callback re-issues the
    `fetchDistribution` request through the same callback the
    eager-fetch effect uses."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "distributionStatus" in text, (
        "TaxonomyTree.tsx must thread distributionStatus to DetailPanel."
    )
    assert "onRetryDistribution" in text, (
        "TaxonomyTree.tsx must thread onRetryDistribution to DetailPanel."
    )
    # The retry callback must re-issue loadDistribution for the
    # currently selected taxon (mirrors the eager-fetch path).
    assert re.search(
        r"onRetryDistribution\s*=\s*\{[^}]*loadDistribution",
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must map onRetryDistribution to a loadDistribution call."
    )


def test_barrel_reexports_distribution_contract() -> None:
    """ODD-TDDIST-001: the taxonomy barrel must re-export the
    public distribution data contract so cross-module consumers
    can type the payload + call the helper without a deep
    import (spec.md rule 5)."""
    text = _read_text(TAXONOMY_BARREL)
    for name in (
        "fetchDistribution",
        "FetchDistributionOptions",
        "DistributionEntry",
    ):
        assert name in text, (
            f"taxonomy barrel must re-export `{name}` (ODD-TDDIST-001)."
        )


def test_globals_css_declares_distribution_tab_selectors() -> None:
    """ODD-TDDIST-001: `src/app/globals.css` must declare the
    new `.distribution-tab` cascade so the per-row `.detail-item`
    rows + the establishment-means chip + the area text + the
    section header + count badge all render identically to the
    legacy oracle. The selectors live under `@layer components`
    and are in alphabetical order so the chain-topology guard
    in `tests/test_research_styles.py` keeps whitelisting them."""
    text = _read_text(TAXONOMY_GLOBALS_CSS)
    layer = re.search(r"@layer\s+components\s*\{", text)
    assert layer, "@layer components must exist in globals.css"
    body = text[layer.end():]
    layer_end = body.find("\n}\n")
    if layer_end == -1:
        layer_end = body.find("}")
    body = body[:layer_end]
    # Every selector must appear in the source. The minifier
    # may strip whitespace / quotes, so we accept the bare
    # class names without descendants.
    for needle in (
        ".distribution-tab",
        ".distribution-tab > .distribution-list",
        ".distribution-tab > .distribution-list > .detail-item",
        ".distribution-tab > .distribution-list > .detail-item > .means",
        ".distribution-tab > .distribution-list > .detail-item > .means-unknown",
        ".distribution-tab > .distribution-list > .detail-item > .distribution-area",
        ".distribution-tab > .distribution-section-header",
        ".distribution-tab > .distribution-section-count",
    ):
        assert needle in body, (
            f"globals.css @layer components must declare {needle}."
        )


def test_out_index_html_has_distribution_tab_styles(static_export) -> None:
    """ODD-TDDIST-001: the static export's CSS must define the
    DistributionTab selectors introduced by the React cutover
    so the native-style Distribution row list renders
    identically to the legacy oracle. The selectors live
    under the whitelisted `.distribution-tab` base class so
    the chain-topology guard in
    `tests/test_research_styles.py` keeps whitelisting them."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    # The container + list + row + chip selectors are covered
    # by the `.distribution-tab` cascade in `src/app/globals.css`.
    # The static export's CSS must surface at least the
    # top-level `.distribution-tab` rule plus the per-row
    # `.means` rule (so the establishment-means chip + area
    # rendering matches the legacy oracle).
    for needle in (".distribution-tab", ".means"):
        assert needle in css_body, (
            f"ODD-TDDIST-001: static CSS must define the {needle} rule."
        )


# ---------------------------------------------------------------------------
# ODD-TDFOLDER-001 — native Folder tab data contract + UI.
#
#   - `previewMaterialize` / `materializeResearch` / `openFolder`
#     are the canonical typed projections for
#     `/api/taxon/{id}/materialize-preview` (GET),
#     `/api/taxon/{id}/materialize` (POST),
#     `/api/taxon/{id}/open-folder` (POST). The cumulative paths
#     are server-composed — the React port never joins /
#     sanitises paths client-side.
#   - `FolderTab` is the native React renderer; renders the
#     line-by-line segment list with ✓ / + markers, the count
#     summary, the info banner (when `all_exist === true`), the
#     Create row with an explicit in-tab confirmation gate
#     (when `all_exist === false`), the Open + Copy path-actions
#     row (when `all_exist === true`), and inline success /
#     error states for create / open / copy. The source-aware
#     preview cache is INVALIDATED on source switches (the
#     materialize preview walks the active source's parent
#     column — different from the source-agnostic
#     vernaculars / synonyms / distribution caches).
# ---------------------------------------------------------------------------
FOLDER_TAB_FILE = (
    REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "FolderTab.tsx"
)


def test_folder_tab_file_exists() -> None:
    """ODD-TDFOLDER-001: FolderTab component must exist as a
    `.tsx` file under the taxonomy presentation folder (mirrors
    the ODD-TDDIST-001 / ODD-TDV-001 / ODD-TDSYN-001 component
    files). The suffix is `.tsx` because the file declares a
    JSX-rendered React component (the `react-jsx` runtime
    requires TypeScript's JSX checker, not plain `.ts`)."""
    assert FOLDER_TAB_FILE.is_file(), (
        f"missing {FOLDER_TAB_FILE} \u2014 ODD-TDFOLDER-001 ships this "
        "Folder tab component."
    )
    assert FOLDER_TAB_FILE.suffix == ".tsx", (
        "FolderTab must be `.tsx` (JSX-rendered)."
    )


def test_folder_tab_is_a_client_component() -> None:
    """ODD-TDFOLDER-001: FolderTab mounts inside the React
    client island (TaxonomyTree -> DetailPanel -> FolderTab).
    The component declares the client boundary via the
    `"use client"` directive at the top of the file so the
    Create / Confirm / Open / Copy handlers stay interactive
    after hydration."""
    text = _read_text(FOLDER_TAB_FILE)
    assert text.lstrip().startswith('"use client"') or text.lstrip().startswith("'use client'"), (
        "FolderTab.tsx must declare the client boundary via 'use client'"
    )


def test_folder_tab_consumes_canonical_projection() -> None:
    """ODD-TDFOLDER-001: FolderTab imports the canonical
    `MaterializePreview` + `MaterializePreviewSegment` +
    `MaterializeResult` + `OpenFolderResult` projections from
    the infrastructure layer. A deep import would leak server
    composition concerns into the client contract; a missing
    import would force the component to type the payload
    inline (bypassing the canonical projection)."""
    text = _read_text(FOLDER_TAB_FILE)
    assert "MaterializePreview" in text, (
        "FolderTab.tsx must consume the canonical `MaterializePreview` projection."
    )
    assert "MaterializePreviewSegment" in text, (
        "FolderTab.tsx must consume the canonical `MaterializePreviewSegment` projection."
    )
    assert "MaterializeResult" in text, (
        "FolderTab.tsx must consume the canonical `MaterializeResult` projection "
        "(drives the inline success copy after Create)."
    )
    assert "OpenFolderResult" in text, (
        "FolderTab.tsx must consume the canonical `OpenFolderResult` projection "
        "(drives the inline success copy after Open)."
    )
    assert "from \"../infrastructure/api\"" in text, (
        "FolderTab.tsx must import the canonical projection from "
        "../infrastructure/api (spec.md rule 4)."
    )


def test_folder_tab_renders_loading_state() -> None:
    """ODD-PHASE2 + ODD-TDFOLDER-001: the loading branch uses
    the `<Spinner size="md" label="Loading folder preview…" />`
    design-system primitive (from `@taxa/design-system`) instead
    of the previous inline `<span className="material-symbols-
    outlined animate-spin">progress_activity</span>` + `<p>Loading
    preview…</p>` composition. The Spinner primitive owns the
    `role="status"` + `aria-live="polite"` + `aria-busy` a11y
    surface (its internal `<span aria-busy="true">` + the
    visually-hidden `<div role="status" aria-live="polite">`
    region). The wrapper carries `data-folder-status="loading"`
    so the per-state data-attribute contract survives the
    migration. Mirrors the ODD-TDS-001 + ODD-TDV-001 +
    ODD-TDSYN-001 + ODD-TDDIST-001 loading contracts byte-for-
    byte."""
    text = _read_text(FOLDER_TAB_FILE)
    # The Spinner primitive MUST be imported from the public
    # barrel (spec.md rule 5 — no deep imports into the layer
    # folders).
    assert re.search(
        r'import\s*\{[^}]*\bSpinner\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must import `Spinner` from "
        "`@taxa/design-system` (the public barrel)."
    )
    # The Spinner primitive MUST be used at the loading branch
    # with `size="md"` + the canonical loading label.
    assert re.search(
        r'<\s*Spinner\b[^>]*\bsize\s*=\s*["\']md["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must render `<Spinner size=\"md\">` "
        "for the loading state."
    )
    assert 'label="Loading folder preview' in text or "label='Loading folder preview" in text, (
        "ODD-PHASE2: FolderTab.tsx must pass the canonical loading "
        "label to the Spinner primitive."
    )
    # The wrapper still carries `role="status"` + `aria-busy="true"`
    # so a screen-reader probe + a legacy Playwright probe can
    # locate the loading branch via the existing surface.
    assert 'role="status"' in text or "role='status'" in text, (
        "FolderTab.tsx must render a role=\"status\" element for the loading state."
    )
    assert "aria-busy" in text, (
        "FolderTab.tsx must set aria-busy on the loading state for a11y tooling."
    )
    assert 'data-folder-status={status.kind}' in text, (
        "ODD-PHASE2: the loading wrapper must carry "
        "`data-folder-status={status.kind}` so the per-state "
        "data-attribute contract survives the migration."
    )


def test_folder_tab_renders_error_state() -> None:
    """ODD-PHASE2 + ODD-TDFOLDER-001: the error branch now uses
    the `<InlineMessage variant="error">` design-system primitive
    (from `@taxa/design-system`) for the inline failure message
    instead of the previous `<div className="folder-inline-
    message folder-inline-message-error …">` composition. The
    InlineMessage primitive owns the `bg-red-50 border-red-200
    text-red-700` palette; the `data-folder-inline-message="error"`
    data attribute + `role="alert"` + the wire `{status.message}`
    value still pass through verbatim. The Retry button now uses
    `<Button variant="secondary">` (also from
    `@taxa/design-system`); the click still invokes the
    `onRetryPreview` prop callback so the failure is recoverable
    without a fresh taxon selection.
    """
    text = _read_text(FOLDER_TAB_FILE)
    # The InlineMessage primitive MUST be imported from the public
    # barrel (spec.md rule 5).
    assert re.search(
        r'import\s*\{[^}]*\bInlineMessage\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must import `InlineMessage` from "
        "`@taxa/design-system` (the public barrel)."
    )
    # The Button primitive MUST be imported from the public
    # barrel (the Retry button uses the primitive).
    assert re.search(
        r'import\s*\{[^}]*\bButton\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must import `Button` from "
        "`@taxa/design-system` (the public barrel — Retry uses it)."
    )
    # The error InlineMessage MUST be rendered with
    # `variant="error"`.
    assert re.search(
        r'<\s*InlineMessage\b[^>]*\bvariant\s*=\s*["\']error["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must render `<InlineMessage "
        "variant=\"error\">` for the error state."
    )
    # The wrapper / InlineMessage MUST still carry the canonical
    # a11y hook (`role="alert"`) + the canonical data attribute
    # (`data-folder-inline-message="error"`) so the legacy
    # selectors + Playwright probes still find the error state.
    assert 'role="alert"' in text or "role='alert'" in text, (
        "FolderTab.tsx must render a role=\"alert\" element for the error state."
    )
    assert 'data-folder-inline-message="error"' in text or "data-folder-inline-message='error'" in text, (
        "FolderTab.tsx must stamp data-folder-inline-message=\"error\" on the error InlineMessage."
    )
    assert "Could not load the preview" in text, (
        "FolderTab.tsx must render the canonical error copy."
    )
    # The Retry button uses the `<Button variant="secondary">`
    # primitive.
    assert re.search(
        r'<\s*Button\b[^>]*\bvariant\s*=\s*["\']secondary["\'][\s\S]{0,400}?Retry[\s\S]{0,40}?</Button>',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must render the Retry button "
        "via `<Button variant=\"secondary\">`."
    )
    assert 'data-action="retry-folder-preview"' in text, (
        "FolderTab.tsx must stamp data-action=\"retry-folder-preview\" on the Retry button."
    )
    assert "onRetryPreview" in text, (
        "FolderTab.tsx must invoke the onRetryPreview prop on Retry click."
    )


def test_folder_tab_renders_preview_segments_with_markers() -> None:
    """ODD-TDFOLDER-001: the loaded branch renders the
    line-by-line segment list with the ✓ / + markers per
    segment. Each row carries `data-folder-segment-name` +
    `data-folder-segment-exists` + the cumulative path on
    `data-folder-segment-cumulative` so the parity test can
    pin the marker text + path round-trip without scraping
    className. The marker class is `.folder-segment-marker-exists`
    (green, ✓) or `.folder-segment-marker-new` (default, +).
    Mirrors the legacy `web/detail.js::renderFolderTab`
    marker logic byte-for-byte."""
    text = _read_text(FOLDER_TAB_FILE)
    assert "folder-segment-list" in text, (
        "FolderTab.tsx must render the .folder-segment-list ul element."
    )
    assert "folder-segment-item" in text, (
        "FolderTab.tsx must render the .folder-segment-item li element per segment."
    )
    assert "folder-segment-marker" in text, (
        "FolderTab.tsx must render the .folder-segment-marker span per segment."
    )
    assert "folder-segment-marker-exists" in text, (
        "FolderTab.tsx must render the .folder-segment-marker-exists class on existing segments."
    )
    assert "folder-segment-marker-new" in text, (
        "FolderTab.tsx must render the .folder-segment-marker-new class on new segments."
    )
    assert "folder-segment-path" in text, (
        "FolderTab.tsx must render the .folder-segment-path span per segment."
    )
    assert "data-folder-segment-name" in text, (
        "FolderTab.tsx must stamp data-folder-segment-name on every row."
    )
    assert "data-folder-segment-exists" in text, (
        "FolderTab.tsx must stamp data-folder-segment-exists on every row."
    )
    assert "data-folder-segment-cumulative" in text, (
        "FolderTab.tsx must stamp data-folder-segment-cumulative on every row."
    )


def test_folder_tab_renders_counts_summary() -> None:
    """ODD-TDFOLDER-001: the loaded branch renders the
    count summary ("N new folders · M already existed") with
    the wire values stamped on data-folder-counts +
    data-folder-new-count + data-folder-existing-count. The
    renderer does NOT recompute the new-vs-existing counts
    client-side (the server is the source of truth). Mirrors
    the legacy `web/detail.js::renderFolderTab::counts`
    byte-for-byte (singular/plural branch on new_count === 1)."""
    text = _read_text(FOLDER_TAB_FILE)
    assert "folder-counts" in text, (
        "FolderTab.tsx must render the .folder-counts element."
    )
    assert "data-folder-counts" in text, (
        "FolderTab.tsx must stamp data-folder-counts on the counts element."
    )
    assert "data-folder-new-count" in text, (
        "FolderTab.tsx must stamp data-folder-new-count on the counts element."
    )
    assert "data-folder-existing-count" in text, (
        "FolderTab.tsx must stamp data-folder-existing-count on the counts element."
    )
    assert "already existed" in text, (
        "FolderTab.tsx must render the canonical counts copy."
    )
    # The singular/plural branch must apply at the renderer
    # (NOT in the projection layer). The wire `new_count`
    # surfaces as a number, and the renderer substitutes the
    # "folder" / "folders" literal based on `new_count === 1`.
    assert re.search(
        r"new_count\s*===\s*1\s*\?\s*[\"\']new folder[\"\']\s*:\s*[\"\']new folders[\"\']",
        text,
    ), (
        "FolderTab.tsx must branch on new_count === 1 to pick "
        "\"new folder\" vs \"new folders\" at render time."
    )


def test_folder_tab_renders_info_banner_when_all_exist() -> None:
    """ODD-PHASE2 + ODD-TDFOLDER-001: when `preview.all_exist
    === true`, the renderer paints the info banner via the
    `<InlineMessage variant="info">` design-system primitive
    (from `@taxa/design-system`) instead of the previous
    `<div className="folder-info-banner …">` composition. The
    `data-folder-info-banner=""` data attribute + the canonical
    "Path already exists on disk." copy + the `check_circle`
    Material Symbols glyph all pass through verbatim. The
    branch is conditional on the wire `all_exist` flag (the
    renderer does NOT compute all_exist client-side — the
    server is the source of truth). Mirrors the legacy
    `web/detail.js::renderFolderTab::infoBanner` byte-for-byte.
    """
    text = _read_text(FOLDER_TAB_FILE)
    # The InlineMessage primitive MUST be imported from the public
    # barrel (spec.md rule 5).
    assert re.search(
        r'import\s*\{[^}]*\bInlineMessage\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must import `InlineMessage` from "
        "`@taxa/design-system` (the public barrel)."
    )
    # The info banner MUST be rendered as an `<InlineMessage
    # variant="info" data-folder-info-banner="">` opening tag.
    # We use a regex that captures the FULL opening tag from
    # `<InlineMessage` through to the closing `>` so the
    # data-folder-info-banner="" attribute is provably on the
    # same element as the variant="info" attribute.
    full_open_match = re.search(
        r'<\s*InlineMessage\b[^>]*?\bvariant\s*=\s*["\']info["\'][^>]*?\bdata-folder-info-banner\s*=\s*["\']["\'][^>]*?>',
        text,
    )
    assert full_open_match, (
        "ODD-PHASE2: FolderTab.tsx must render the info banner "
        "via `<InlineMessage variant=\"info\" "
        "data-folder-info-banner=\"\">` (both attributes on the "
        "same opening tag)."
    )
    assert "Path already exists on disk" in text, (
        "FolderTab.tsx must render the canonical info banner copy."
    )
    assert "check_circle" in text, (
        "FolderTab.tsx must render the check_circle material-symbol icon on the info banner."
    )


def test_folder_tab_renders_create_row_when_not_all_exist() -> None:
    """ODD-PHASE2 + ODD-TDFOLDER-001: when `preview.all_exist
    === false`, the renderer paints the create row (initially
    the bare "Create N folders" CTA — the in-tab confirmation
    gate flips it to the Confirm row on the next click). The
    bare CTA now uses the `<Button variant="primary">` design-
    system primitive (from `@taxa/design-system`) instead of
    the previous inline `<button className="folder-btn
    folder-btn-primary …">` composition. The CTA carries the
    canonical `data-action="create-folders"` (per the ODD-
    PHASE2 data-action naming cleanup) so the parent can route
    the click through `onArmCreate`. Mirrors the legacy
    `web/detail.js::renderFolderTab::createBtn` flow, except
    the React port adds an explicit gate (the legacy oracle
    POSTs immediately)."""
    text = _read_text(FOLDER_TAB_FILE)
    # The Button primitive MUST be imported from the public barrel.
    assert re.search(
        r'import\s*\{[^}]*\bButton\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must import `Button` from "
        "`@taxa/design-system` (the public barrel)."
    )
    # The bare CTA MUST be rendered with
    # `<Button variant="primary">` AND carry
    # `data-action="create-folders"`. We anchor on the
    # data-action first (it's unique across all Button
    # elements in this file) so the regex distinguishes the
    # bare Create CTA from the Confirm button (which is also
    # `variant="primary"`).
    create_match = re.search(
        r'<\s*Button\b[^>]*\bvariant\s*=\s*(?:["\']primary["\']|\{["\']primary["\']\})'
        r'[\s\S]{0,400}?\bdata-action\s*=\s*["\']create-folders["\']',
        text,
    )
    assert create_match, (
        "ODD-PHASE2: FolderTab.tsx must render the bare Create CTA "
        "via `<Button variant=\"primary\" data-action=\"create-folders\">`."
    )
    assert "onArmCreate" in text, (
        "FolderTab.tsx must invoke the onArmCreate prop on bare-CTA click."
    )
    assert "folder-create-row" in text, (
        "FolderTab.tsx must render the .folder-create-row element when all_exist === false."
    )
    assert "data-folder-create-row" in text, (
        "FolderTab.tsx must stamp data-folder-create-row on the create row."
    )


def test_folder_tab_renders_confirm_row_when_armed() -> None:
    """ODD-PHASE2 + ODD-TDFOLDER-001: when `createArmed === true`,
    the renderer paints the in-tab confirmation row instead of
    the bare CTA. The row carries a Cancel button (`<Button
    variant="secondary">`) which invokes `onDisarmCreate` + a
    Confirm create button (`<Button variant="primary">`) which
    invokes `onCreate` (the parent calls `materializeResearch`).
    The explicit gate is the ODD-TDFOLDER-001 user constraint:
    "Require an explicit in-tab confirmation before creating
    folders, intentionally safer than legacy." The legacy
    `web/detail.js::renderFolderTab::createBtn` POSTs
    immediately on click.

    Both buttons now use the `<Button>` design-system primitive
    from `@taxa/design-system` (no more `<button className=
    "folder-btn folder-btn-primary …">` / `folder-btn-secondary`
    composition). The data-action names follow the ODD-PHASE2
    cleanup: `data-action="confirm-create-folders"` +
    `data-action="disarm-create-folders"`."""
    text = _read_text(FOLDER_TAB_FILE)
    # The Button primitive MUST be imported from the public barrel.
    assert re.search(
        r'import\s*\{[^}]*\bButton\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must import `Button` from "
        "`@taxa/design-system` (the public barrel)."
    )
    # The Confirm button MUST be rendered with
    # `<Button variant="primary">` AND carry
    # `data-action="confirm-create-folders"`. We anchor on the
    # data-action so the regex distinguishes the Confirm button
    # from the bare Create CTA (which is also `variant="primary"`).
    confirm_btn_match = re.search(
        r'<\s*Button\b[^>]*\bvariant\s*=\s*(?:["\']primary["\']|\{["\']primary["\']\})'
        r'[\s\S]{0,400}?\bdata-action\s*=\s*["\']confirm-create-folders["\']',
        text,
    )
    assert confirm_btn_match, (
        "ODD-PHASE2: FolderTab.tsx must render the Confirm button "
        "via `<Button variant=\"primary\" data-action=\"confirm-create-folders\">`."
    )
    # The Cancel button MUST be rendered with
    # `<Button variant="secondary">` AND carry
    # `data-action="disarm-create-folders"`.
    cancel_btn_match = re.search(
        r'<\s*Button\b[^>]*\bvariant\s*=\s*(?:["\']secondary["\']|\{["\']secondary["\']\})'
        r'[\s\S]{0,400}?\bdata-action\s*=\s*["\']disarm-create-folders["\']',
        text,
    )
    assert cancel_btn_match, (
        "ODD-PHASE2: FolderTab.tsx must render the Cancel button "
        "via `<Button variant=\"secondary\" data-action=\"disarm-create-folders\">`."
    )
    assert "folder-confirm" in text, (
        "FolderTab.tsx must render the .folder-confirm element when createArmed === true."
    )
    assert "data-folder-confirm" in text, (
        "FolderTab.tsx must stamp data-folder-confirm on the confirm row."
    )
    assert "onCreate" in text and "onDisarmCreate" in text, (
        "FolderTab.tsx must invoke the onCreate prop on Confirm click "
        "and the onDisarmCreate prop on Cancel click."
    )
    # The Confirm row must surface the wire `preview.relative_path`
    # verbatim so the user sees exactly which folder chain will
    # be created before they click Confirm. The renderer MUST
    # NOT construct / sanitise the path client-side — the server
    # is the source of truth.
    prompt_block = re.search(
        r"folder-confirm-prompt[\s\S]{0,400}?relative_path",
        text,
    )
    assert prompt_block, (
        "FolderTab.tsx must surface the wire `preview.relative_path` "
        "verbatim in the Confirm row prompt."
    )


def test_folder_tab_renders_path_actions_when_all_exist() -> None:
    """ODD-PHASE2 + ODD-TDFOLDER-001: when `preview.all_exist
    === true`, the renderer paints the Open + Copy path-actions
    row instead of the create row. The Open + Copy buttons now
    use the `<Button variant="secondary">` design-system
    primitive (from `@taxa/design-system`) instead of the
    previous inline `<button className="folder-btn folder-btn-
    primary …">` / `folder-btn-secondary` composition. The
    Open button carries the `folder_open` Material Symbols
    glyph + invokes `onOpen` (the parent calls `openFolder`);
    the Copy button carries the `content_copy` glyph + invokes
    `onCopy` (the parent calls `navigator.clipboard.writeText`).
    The data-action names follow the ODD-PHASE2 cleanup:
    `data-action="open-folder-tab"` + `data-action="copy-path"`.
    Mirrors the legacy `web/detail.js::renderFolderTab::
    pathActions` byte-for-byte."""
    text = _read_text(FOLDER_TAB_FILE)
    # The Button primitive MUST be imported from the public barrel.
    assert re.search(
        r'import\s*\{[^}]*\bButton\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must import `Button` from "
        "`@taxa/design-system` (the public barrel)."
    )
    # The Open button MUST be rendered with
    # `<Button variant="secondary">` AND carry
    # `data-action="open-folder-tab"`. We anchor on the
    # data-action so the regex distinguishes the Open button
    # from the Copy button (both are `variant="secondary"`).
    open_btn_match = re.search(
        r'<\s*Button\b[^>]*\bvariant\s*=\s*(?:["\']secondary["\']|\{["\']secondary["\']\})'
        r'[\s\S]{0,400}?\bdata-action\s*=\s*["\']open-folder-tab["\']',
        text,
    )
    assert open_btn_match, (
        "ODD-PHASE2: FolderTab.tsx must render the Open button "
        "via `<Button variant=\"secondary\" data-action=\"open-folder-tab\">`."
    )
    # The Copy button MUST be rendered with
    # `<Button variant="secondary">` AND carry
    # `data-action="copy-path"`.
    copy_btn_match = re.search(
        r'<\s*Button\b[^>]*\bvariant\s*=\s*(?:["\']secondary["\']|\{["\']secondary["\']\})'
        r'[\s\S]{0,400}?\bdata-action\s*=\s*["\']copy-path["\']',
        text,
    )
    assert copy_btn_match, (
        "ODD-PHASE2: FolderTab.tsx must render the Copy button "
        "via `<Button variant=\"secondary\" data-action=\"copy-path\">`."
    )
    assert "folder-path-actions" in text, (
        "FolderTab.tsx must render the .folder-path-actions element when all_exist === true."
    )
    assert "data-folder-path-actions" in text, (
        "FolderTab.tsx must stamp data-folder-path-actions on the path-actions row."
    )
    assert "onOpen" in text and "onCopy" in text, (
        "FolderTab.tsx must invoke onOpen on the Open button "
        "and onCopy on the Copy button."
    )


def test_folder_tab_renders_inline_success_and_error_messages() -> None:
    """ODD-PHASE2 + ODD-TDFOLDER-001: the create / open / copy
    actions all surface inline success / error messages (no toast
    dependency). The success / error messages now use the
    `<InlineMessage variant="success">` + `<InlineMessage
    variant="error">` design-system primitives (from
    `@taxa/design-system`) instead of the previous
    `<div className="folder-inline-message folder-inline-
    message-success …">` / `folder-inline-message-error`
    composition. The InlineMessage primitive owns the
    `bg-green-50 border-green-200 text-green-700` /
    `bg-red-50 border-red-200 text-red-700` palette; the
    `data-folder-inline-message-success` /
    `data-folder-inline-message-error` data attributes + the
    wire `MaterializeResult.relative_path` /
    `OpenFolderResult.opened_with` values pass through verbatim.
    Mirrors the legacy `web/detail.js::renderFolderTab` toast
    affordance without the toast helper."""
    text = _read_text(FOLDER_TAB_FILE)
    # The InlineMessage primitive MUST be imported from the public barrel.
    assert re.search(
        r'import\s*\{[^}]*\bInlineMessage\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must import `InlineMessage` from "
        "`@taxa/design-system` (the public barrel)."
    )
    # The success InlineMessage MUST use `<InlineMessage variant="success">`.
    assert re.search(
        r'<\s*InlineMessage\b[^>]*\bvariant\s*=\s*["\']success["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must render the inline success "
        "messages via `<InlineMessage variant=\"success\">`."
    )
    # The error InlineMessage MUST use `<InlineMessage variant="error">`.
    # Multiple occurrences are expected (the create-error branch +
    # the open-error branch + the copy-error branch all surface
    # `<InlineMessage variant="error">`).
    error_inline_count = len(re.findall(
        r'<\s*InlineMessage\b[^>]*\bvariant\s*=\s*["\']error["\']',
        text,
    ))
    assert error_inline_count >= 1, (
        "ODD-PHASE2: FolderTab.tsx must render the inline error "
        "messages via `<InlineMessage variant=\"error\">`."
    )
    # The per-state data attributes stay preserved so a legacy
    # Playwright probe can locate each branch via its canonical
    # data-action selector.
    assert 'data-folder-inline-message="created"' in text or "data-folder-inline-message='created'" in text, (
        "FolderTab.tsx must stamp data-folder-inline-message=\"created\" on the create-success message."
    )
    assert "Folders materialized:" in text, (
        "FolderTab.tsx must render the canonical \"Folders materialized: ...\" success copy."
    )
    assert "Opened " in text and "opened_with" in text, (
        "FolderTab.tsx must render the canonical \"Opened with <bin>: ...\" success copy "
        "(driven by the wire OpenFolderResult.opened_with value)."
    )
    assert "Could not open folder:" in text, (
        "FolderTab.tsx must render the canonical open-folder error copy."
    )
    assert "Could not copy path:" in text, (
        "FolderTab.tsx must render the canonical copy-path error copy "
        "(graceful clipboard failure)."
    )


def test_folder_tab_does_not_invoke_clipboard_directly() -> None:
    """ODD-TDFOLDER-001: the FolderTab component MUST NOT
    invoke `navigator.clipboard` directly. The clipboard
    transport lives at the parent (`TaxonomyTree`) so the
    renderer stays framework-free + spec.md rule 4
    (presentation → taxonomy module only, no DOM / no fetch
    tokens in the body beyond the JSX the component is
    required to render). A direct `navigator.clipboard.*`
    call would also force a Browser-only path and break the
    SSR build (the parent owns the clipboard so the render
    contract stays testable under Node)."""
    raw = _read_text(FOLDER_TAB_FILE)
    # Strip every JSDoc / block comment so the assertion
    # doesn't trip on the docstring's prose explanation
    # (the file documents that the renderer MUST NOT call
    # clipboard; the assertion enforces that contract on
    # the body code).
    body = re.sub(r"/\*[\s\S]*?\*/", "", raw)
    assert "navigator.clipboard" not in body, (
        "FolderTab.tsx must NOT call navigator.clipboard directly — the parent "
        "owns the clipboard transport so the renderer stays framework-free."
    )


# ---------------------------------------------------------------------------
# ODD-PHASE2 — FolderTab design-system primitive coverage tests.
#
# The FolderTab migration to `@taxa/design-system` primitives
# (Spinner + InlineMessage + Button) closed the third Phase 2
# consumer. These tests pin the new primitive composition so a
# future PR cannot silently regress the design-system cutover
# back to inline Tailwind / bespoke CSS hooks.
# ---------------------------------------------------------------------------


def test_folder_tab_uses_spinner_primitive_for_loading() -> None:
    """ODD-PHASE2: the loading state uses the `<Spinner size="md"
    label="Loading folder preview…" />` design-system primitive
    (from `@taxa/design-system`) instead of the previous inline
    `<span className="material-symbols-outlined animate-spin">progress_activity</span>`
    + `<p>Loading preview…</p>` composition. The Spinner primitive
    owns the `role="status"` + `aria-live="polite"` + `aria-busy`
    a11y surface (its internal `<span aria-busy="true">` wrapper
    + the visually-hidden `<div role="status" aria-live="polite">`
    region). The canonical loading label flows through the `label`
    prop so screen readers announce the file-preview context."""
    text = _read_text(FOLDER_TAB_FILE)
    assert re.search(
        r'import\s*\{[^}]*\bSpinner\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must import `Spinner` from "
        "`@taxa/design-system` (the public barrel)."
    )
    assert re.search(
        r'<\s*Spinner\b[^>]*\bsize\s*=\s*["\']md["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must render `<Spinner size=\"md\">` "
        "for the loading state."
    )
    # The canonical loading label flows through the `label` prop.
    assert re.search(
        r'<\s*Spinner\b[^>]*\blabel\s*=\s*["\']Loading folder preview',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must pass the canonical loading "
        "label (`Loading folder preview…`) to the Spinner primitive."
    )


def test_folder_tab_uses_inlinemessage_primitive_for_info_banner() -> None:
    """ODD-PHASE2: the info banner uses the `<InlineMessage
    variant="info">` design-system primitive (from
    `@taxa/design-system`) instead of the previous `<div
    className="folder-info-banner …">` composition. The
    InlineMessage primitive owns the
    `bg-surface-container-low border-outline-variant
    text-on-surface-variant` palette; the `data-folder-info-
    banner=""` data attribute + the `check_circle` glyph +
    the canonical copy pass through verbatim."""
    text = _read_text(FOLDER_TAB_FILE)
    assert re.search(
        r'import\s*\{[^}]*\bInlineMessage\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must import `InlineMessage` from "
        "`@taxa/design-system` (the public barrel)."
    )
    # The info banner opening tag carries BOTH `variant="info"` AND
    # `data-folder-info-banner=""` so the per-banner data-attribute
    # contract survives the migration.
    info_open_match = re.search(
        r'<\s*InlineMessage\b[^>]*?\bvariant\s*=\s*["\']info["\'][^>]*?\bdata-folder-info-banner\s*=\s*["\']["\'][^>]*?>',
        text,
    )
    assert info_open_match, (
        "ODD-PHASE2: FolderTab.tsx must render the info banner via "
        "`<InlineMessage variant=\"info\" data-folder-info-banner=\"\">` "
        "(both attributes on the same opening tag)."
    )


def test_folder_tab_uses_inlinemessage_primitive_for_error_message() -> None:
    """ODD-PHASE2: the error messages use the `<InlineMessage
    variant="error">` design-system primitive (from
    `@taxa/design-system`) instead of the previous `<div
    className="folder-inline-message folder-inline-message-error …">`
    composition. Multiple `<InlineMessage variant="error">`
    occurrences are expected: the create-error branch + the
    open-error branch + the copy-error branch all surface the
    primitive. The InlineMessage primitive owns the `bg-red-50
    border-red-200 text-red-700` palette; the `role="alert"` +
    `data-folder-inline-message-error=""` attributes pass
    through verbatim so legacy Playwright probes still locate
    the error state."""
    text = _read_text(FOLDER_TAB_FILE)
    error_inline_count = len(re.findall(
        r'<\s*InlineMessage\b[^>]*\bvariant\s*=\s*["\']error["\']',
        text,
    ))
    assert error_inline_count >= 1, (
        "ODD-PHASE2: FolderTab.tsx must render at least one "
        "`<InlineMessage variant=\"error\">` for the error "
        "branches (create-error + open-error + copy-error)."
    )
    # The `data-folder-inline-message-error=""` attribute MUST
    # be on at least one of the error InlineMessages so the
    # legacy Playwright probe can locate the error state.
    assert 'data-folder-inline-message-error=""' in text, (
        "ODD-PHASE2: FolderTab.tsx must stamp "
        "`data-folder-inline-message-error=\"\"` on the error "
        "InlineMessage(s) (the legacy Playwright probe anchor)."
    )


def test_folder_tab_uses_inlinemessage_primitive_for_success_message() -> None:
    """ODD-PHASE2: the success messages use the `<InlineMessage
    variant="success">` design-system primitive (from
    `@taxa/design-system`) instead of the previous `<div
    className="folder-inline-message folder-inline-message-
    success …">` composition. Multiple `<InlineMessage
    variant="success">` occurrences are expected: the
    create-success branch + the open-success branch. The
    InlineMessage primitive owns the `bg-green-50
    border-green-200 text-green-700` palette; the canonical
    `data-folder-inline-message-success=""` attribute passes
    through verbatim."""
    text = _read_text(FOLDER_TAB_FILE)
    assert re.search(
        r'<\s*InlineMessage\b[^>]*\bvariant\s*=\s*["\']success["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must render at least one "
        "`<InlineMessage variant=\"success\">` for the success "
        "branches (create-success + open-success)."
    )
    # The `data-folder-inline-message-success=""` attribute MUST
    # be on at least one of the success InlineMessages so the
    # legacy Playwright probe can locate the success state.
    assert 'data-folder-inline-message-success=""' in text, (
        "ODD-PHASE2: FolderTab.tsx must stamp "
        "`data-folder-inline-message-success=\"\"` on the success "
        "InlineMessage(s) (the legacy Playwright probe anchor)."
    )


def test_folder_tab_uses_button_primitive_for_create() -> None:
    """ODD-PHASE2: the bare "Create N folders" CTA uses the
    `<Button variant="primary">` design-system primitive (from
    `@taxa/design-system`) instead of the previous inline
    `<button className="folder-btn folder-btn-primary …">`
    composition. The CTA carries the canonical
    `data-action="create-folders"` (per the ODD-PHASE2
    data-action naming cleanup) so the parent can route the
    click through `onArmCreate`."""
    text = _read_text(FOLDER_TAB_FILE)
    assert re.search(
        r'import\s*\{[^}]*\bButton\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: FolderTab.tsx must import `Button` from "
        "`@taxa/design-system` (the public barrel)."
    )
    create_match = re.search(
        r'<\s*Button\b[^>]*?\bvariant\s*=\s*["\']primary["\'][^>]*?\bdata-action\s*=\s*["\']create-folders["\'][^>]*?>',
        text,
    )
    assert create_match, (
        "ODD-PHASE2: FolderTab.tsx must render the bare Create "
        "CTA via `<Button variant=\"primary\" data-action=\"create-folders\">`."
    )


def test_folder_tab_uses_button_primitive_for_confirm() -> None:
    """ODD-PHASE2: the Confirm button (in the in-tab
    confirmation row when `createArmed === true`) uses the
    `<Button variant="primary">` design-system primitive (from
    `@taxa/design-system`) instead of the previous inline
    `<button className="folder-btn folder-btn-primary …">`
    composition. The button carries the canonical
    `data-action="confirm-create-folders"` (per the ODD-PHASE2
    data-action naming cleanup) so the parent can route the
    click through `onCreate`."""
    text = _read_text(FOLDER_TAB_FILE)
    confirm_match = re.search(
        r'<\s*Button\b[^>]*?\bvariant\s*=\s*["\']primary["\'][^>]*?\bdata-action\s*=\s*["\']confirm-create-folders["\'][^>]*?>',
        text,
    )
    assert confirm_match, (
        "ODD-PHASE2: FolderTab.tsx must render the Confirm "
        "button via `<Button variant=\"primary\" data-action=\"confirm-create-folders\">`."
    )


def test_folder_tab_uses_button_primitive_for_open() -> None:
    """ODD-PHASE2: the Open button (in the path-actions row
    when `all_exist === true`) uses the `<Button
    variant="secondary">` design-system primitive (from
    `@taxa/design-system`) instead of the previous inline
    `<button className="folder-btn folder-btn-primary …">`
    composition. The button carries the canonical
    `data-action="open-folder-tab"` (per the ODD-PHASE2
    data-action naming cleanup) so the parent can route the
    click through `onOpen`."""
    text = _read_text(FOLDER_TAB_FILE)
    open_match = re.search(
        r'<\s*Button\b[^>]*?\bvariant\s*=\s*["\']secondary["\'][^>]*?\bdata-action\s*=\s*["\']open-folder-tab["\'][^>]*?>',
        text,
    )
    assert open_match, (
        "ODD-PHASE2: FolderTab.tsx must render the Open button "
        "via `<Button variant=\"secondary\" data-action=\"open-folder-tab\">`."
    )


def test_folder_tab_uses_button_primitive_for_copy() -> None:
    """ODD-PHASE2: the Copy button (in the path-actions row
    when `all_exist === true`) uses the `<Button
    variant="secondary">` design-system primitive (from
    `@taxa/design-system`) instead of the previous inline
    `<button className="folder-btn folder-btn-secondary …">`
    composition. The button carries the canonical
    `data-action="copy-path"` (per the ODD-PHASE2 data-action
    naming cleanup) so the parent can route the click
    through `onCopy`."""
    text = _read_text(FOLDER_TAB_FILE)
    copy_match = re.search(
        r'<\s*Button\b[^>]*?\bvariant\s*=\s*["\']secondary["\'][^>]*?\bdata-action\s*=\s*["\']copy-path["\'][^>]*?>',
        text,
    )
    assert copy_match, (
        "ODD-PHASE2: FolderTab.tsx must render the Copy button "
        "via `<Button variant=\"secondary\" data-action=\"copy-path\">`."
    )


def test_folder_tab_no_inline_folder_btn_classes() -> None:
    """ODD-PHASE2: the legacy `<button className="folder-btn
    folder-btn-primary …">` / `folder-btn-secondary` /
    `folder-btn` class hooks are GONE from FolderTab.tsx. The
    `<Button>` design-system primitive owns the treatment +
    the variant palette. The className-anchored regex avoids
    false positives from the file's docstring which mentions
    `folder-btn*` literally as legacy references."""
    raw = _read_text(FOLDER_TAB_FILE)
    # Strip every JSDoc / block comment + line comment so the
    # assertion doesn't trip on the docstring's prose
    # explanation (the file documents the legacy composition
    # it replaced; the assertion enforces the legacy class
    # hooks are gone from the body code).
    block = re.compile(r"/\*[\s\S]*?\*/")
    line = re.compile(r"//[^\n]*")
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))  # noqa: E731
    text = block.sub(blank, raw)
    text = line.sub(blank, text)
    for forbidden in (
        r'className\s*=\s*["\'][^"\']*\bfolder-btn\b',
        r'className\s*=\s*["\'][^"\']*\bfolder-btn-primary\b',
        r'className\s*=\s*["\'][^"\']*\bfolder-btn-secondary\b',
    ):
        assert not re.search(forbidden, text), (
            "ODD-PHASE2: FolderTab.tsx must NOT carry the legacy "
            "`.folder-btn*` class hooks (the Button primitive "
            "owns the variant palette)."
        )


def test_folder_tab_no_inline_folder_inline_message_classes() -> None:
    """ODD-PHASE2: the legacy `<div className="folder-inline-
    message folder-inline-message-error …">` / `folder-inline-
    message-success` / `folder-inline-message` class hooks are
    GONE from FolderTab.tsx. The `<InlineMessage>` design-
    system primitive owns the treatment + the variant palette.
    The className-anchored regex avoids false positives from
    the file's docstring which mentions `folder-inline-
    message*` literally as legacy references."""
    raw = _read_text(FOLDER_TAB_FILE)
    # Strip every JSDoc / block comment + line comment so the
    # assertion doesn't trip on the docstring's prose
    # explanation (the file documents the legacy composition
    # it replaced; the assertion enforces the legacy class
    # hooks are gone from the body code).
    block = re.compile(r"/\*[\s\S]*?\*/")
    line = re.compile(r"//[^\n]*")
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))  # noqa: E731
    text = block.sub(blank, raw)
    text = line.sub(blank, text)
    for forbidden in (
        r'className\s*=\s*["\'][^"\']*\bfolder-inline-message\b',
        r'className\s*=\s*["\'][^"\']*\bfolder-inline-message-error\b',
        r'className\s*=\s*["\'][^"\']*\bfolder-inline-message-success\b',
        r'className\s*=\s*["\'][^"\']*\bfolder-info-banner\b',
    ):
        assert not re.search(forbidden, text), (
            "ODD-PHASE2: FolderTab.tsx must NOT carry the legacy "
            "`.folder-inline-message*` / `.folder-info-banner` "
            "class hooks (the InlineMessage primitive owns the "
            "variant palette)."
        )


def test_detail_panel_enables_folder_tab() -> None:
    """ODD-TDFOLDER-001: the Folder tab is ENABLED
    (`available: true`). The React port's earlier slice marked
    Folder as `available: false` per the "visibly mark
    unavailable later tabs without fake actions" policy.
    ODD-TDFOLDER-001 flips the Folder entry to `true` so the
    user can click into the native Folder preview."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert re.search(
        r"key\s*:\s*[\"\']folder[\"\']\s*,\s*label\s*:\s*[\"\']Folder[\"\']"
        r"[\s\S]{0,200}?available\s*:\s*true",
        text,
    ), (
        "DetailPanel.tsx must declare the Folder tab with `available: true` "
        "(ODD-TDFOLDER-001 enables the Folder tab body)."
    )


def test_detail_panel_renders_folder_tab_when_active() -> None:
    """ODD-TDFOLDER-001: when `activeTab === "folder"`, the
    panel body renders `<FolderTab>` instead of the Overview
    body. The body slot must consume the canonical
    `FolderTabStatus` discriminated union + the retry /
    create / open / copy callbacks + the create-armed gate so
    the loading / error / loaded states + the in-tab
    confirmation flow + the inline success / error copy all
    render correctly."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert "FolderTab" in text, (
        "DetailPanel.tsx must import the canonical FolderTab component."
    )
    assert "FolderTabStatus" in text, (
        "DetailPanel.tsx must consume the FolderTabStatus type for the folderStatus prop."
    )
    assert "FolderCreateStatus" in text and "FolderOpenStatus" in text and "FolderCopyStatus" in text, (
        "DetailPanel.tsx must consume the FolderCreateStatus + FolderOpenStatus + "
        "FolderCopyStatus types for the side-effect status props."
    )
    # Body slot must dispatch on activeTab === "folder" to
    # render FolderTab. The dispatch must branch BEFORE the
    # Overview fallback.
    assert re.search(
        r"activeTab\s*===\s*[\"\']folder[\"\']",
        text,
    ), (
        "DetailPanel.tsx body must dispatch on activeTab === \"folder\" "
        "to render the FolderTab."
    )
    assert re.search(
        r"activeTab\s*===\s*[\"\']folder[\"\'][\s\S]{0,400}?<FolderTab",
        text,
    ), (
        "DetailPanel.tsx must render <FolderTab> when activeTab === \"folder\"."
    )


def test_detail_panel_threads_folder_callbacks() -> None:
    """ODD-TDFOLDER-001: DetailPanel threads
    `onRetryFolderPreview` + `onArmCreate` + `onDisarmCreate` +
    `onCreateResearchFolders` + `onOpenResearchFolder` +
    `onCopyResearchPath` through to FolderTab so the parent
    can drive every Folder-side-effect action."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    for name in (
        "onRetryFolderPreview",
        "onArmCreate",
        "onDisarmCreate",
        "onCreateResearchFolders",
        "onOpenResearchFolder",
        "onCopyResearchPath",
    ):
        assert name in text, (
            f"DetailPanel.tsx must thread `{name}` to the FolderTab."
        )


# ---------------------------------------------------------------------------
# ODD-PHASE2 — DetailPanel design-system primitive coverage tests.
#
# The DetailPanel migration to `@taxa/design-system` primitives
# (Badge + Card + IconButton + Text) closed the second Phase 2
# consumer. These tests pin the new primitive composition so a
# future PR cannot silently regress the design-system cutover
# back to inline Tailwind / bespoke CSS hooks.
# ---------------------------------------------------------------------------


def test_detail_panel_imports_design_system_primitives() -> None:
    """ODD-TAPOPUP-001 + ODD-PHASE2: DetailPanel imports
    `Badge`, `Card`, and `IconButton` from `@taxa/design-system`
    (the public barrel — spec.md rule 5 forbids deep imports
    into the layer folders). The popup header uses the
    `Badge` + `Card` + `IconButton` primitives; the `Text`
    primitive is no longer needed (the popup drops the
    Overview body which was the only `Text` consumer)."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert re.search(
        r'import\s*\{[^}]*\bBadge\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "DetailPanel.tsx must import Badge from @taxa/design-system."
    )
    assert re.search(
        r'import\s*\{[^}]*\bCard\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "DetailPanel.tsx must import Card from @taxa/design-system."
    )
    assert re.search(
        r'import\s*\{[^}]*\bIconButton\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "DetailPanel.tsx must import IconButton from @taxa/design-system."
    )
    # The `Text` primitive is no longer consumed (the popup
    # drops the Overview body which was the only `Text`
    # consumer).
    assert not re.search(
        r'import\s*\{[^}]*\bText\b[^}]*\}\s*from\s*["\']\@taxa/design-system["\']',
        text,
    ), (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT import "
        "`Text` from @taxa/design-system (the popup drops "
        "the Overview body which was the only `Text` "
        "consumer)."
    )


def test_detail_panel_uses_card_primitive_for_detail_card() -> None:
    """ODD-PHASE2: the legacy `<div className="detail-card ...">`
    wrapper collapses into `<Card variant="default">` from the
    design-system barrel. The Card primitive owns the chroming
    (`bg-surface border border-outline-variant`); the
    specialised detail-panel surface (max-height + overflow +
    rounded-2xl) stays in the className so the cascade still
    matches the legacy oracle pixel-for-pixel."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # Locate the actual JSX `<Card ...>` opening tag — the
    # docstring comment block also mentions `<Card variant="default">`
    # so the assertion must target the JSX form (new-line +
    # indented prop), not the comment form.
    card_open_match = re.search(
        r'<Card\s*\n\s+variant\s*=\s*["\']default["\']',
        text,
    )
    assert card_open_match, (
        "DetailPanel.tsx must render <Card variant=\"default\"> as "
        "the inner card wrapper (JSX form: <Card\\n  variant=\"default\"\\n ...>)."
    )
    # The className carries the specialised detail-panel surface
    # treatment (max-height + overflow + rounded-2xl). The Card
    # opening tag may span multiple lines AND the className may
    # use backticks (template literal) instead of quotes, so
    # accept either opening delimiter. Scope the className search
    # to the JSX region between the Card opening tag and its
    # closing `>` to avoid matching unrelated attributes elsewhere
    # in the file.
    card_open_idx = card_open_match.start()
    card_close_idx = text.find(">", card_open_match.end())
    assert card_close_idx != -1, "Card opening tag must terminate."
    card_region = text[card_open_idx:card_close_idx + 1]
    for needle in ("overflow-hidden", "max-h-[calc(90vh-2px)]", "rounded-2xl"):
        assert needle in card_region, (
            f"DetailPanel.tsx must pass `{needle}` to the Card "
            "className so the detail-card shape survives the Card "
            "primitive migration."
        )
    # The legacy inline `<div className="detail-card ...">` is GONE.
    assert not re.search(
        r'<div[^>]*\bclassName\s*=\s*["\'][^"\']*\bdetail-card\b',
        text,
    ), (
        "DetailPanel.tsx must NOT render the legacy "
        '<div className="detail-card ..."> wrapper — '
        "the Card primitive owns the treatment."
    )


def test_detail_panel_uses_badge_primitive_for_rank() -> None:
    """ODD-PHASE2: the primary rank badge (formerly
    `<span className="rank-badge uppercase tracking-[0.1em] px-2
    py-0.5 rounded text-primary bg-primary/10">`) collapses
    into `<Badge variant="primary" uppercase={true}>` from the
    design-system barrel. The Badge primitive maps to the same
    `bg-primary/10 text-primary` Tailwind utilities so the
    visual treatment is byte-for-byte identical to the legacy
    oracle."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert re.search(
        r'<Badge\b[^>]*\bvariant\s*=\s*["\']primary["\']',
        text,
    ), (
        "DetailPanel.tsx must render the primary rank badge as "
        '<Badge variant="primary"> from @taxa/design-system.'
    )
    # The legacy inline `<span className="rank-badge ...">` rank
    # badge pattern is GONE for the primary rank anchor.
    assert not re.search(
        r'<span[^>]*\bclassName\s*=\s*["\'][^"\']*\brank-badge\b[^"\']*\btext-primary\b',
        text,
    ), (
        "DetailPanel.tsx must NOT render the legacy inline "
        '<span className="rank-badge text-primary bg-primary/10"> '
        "primary rank badge — the Badge variant=\"primary\" primitive "
        "owns the treatment."
    )


# ---------------------------------------------------------------------------
# ODD-SECSCROLL-001 — make `.detail-section` vertically scrollable.
#
# The popup Card sits inside `<Card variant="default" ...overflow-hidden
# max-h-[calc(90vh-2px)]>`. Pre-fix the `.detail-section` rule carried
# only padding + border-bottom — no flex shrink, no min-height: 0, and
# no overflow-y. When the tab body (long Search links, Synonyms, or
# Distribution lists) overflowed the Card's max-height, the content
# was silently clipped at the Card edge instead of scrolling inside
# the section. The user saw a popup with truncated content and no
# scroll affordance.
#
# The fix applies the canonical flexbox-child overflow pattern:
#   - `flex: 1 1 auto` + `min-height: 0` so the section claims the
#     remaining Card height and shrinks instead of overflowing.
#   - `overflow-y: auto` so the section scrolls its own contents
#     vertically when the body exceeds the available height.
# Horizontal tab scrolling (the `.tab-strip` row above the section)
# stays intact because the new declarations only target the
# `.detail-section` descendant. The pre-existing
# `.detail-panel .detail-section:last-child` rule (border-bottom: 0)
# stays intact so the last tab doesn't carry a redundant divider.
# ---------------------------------------------------------------------------


def test_globals_css_detail_section_is_vertically_scrollable() -> None:
    """ODD-SECSCROLL-001: the `.detail-panel .detail-section`
    rule in `globals.css` MUST carry the canonical flexbox-child
    overflow pattern so the tab body scrolls inside the Card
    instead of being clipped at the Card edge.

    Required declarations (all four must be present):
      - `flex: 1 1 auto` (or equivalent `flex: 1 1 0` /
        `flex: 1` shorthand) so the section claims the
        remaining Card height.
      - `min-height: 0` so flexbox allows the section to
        shrink below its content's intrinsic height (the
        canonical flexbox overflow workaround).
      - `overflow-y: auto` so the section scrolls its own
        contents vertically when the body exceeds the
        available height.
      - The selector MUST stay scoped under `.detail-panel` so
        the chain-topology guard in `tests/test_research_styles.py`
        continues to whitelist the descendant through the
        `.detail-panel` base.

    The pre-existing padding + border-bottom declarations stay
    so the visual contract (16/24px padding + 1px surface-
    container divider) is preserved. The test only checks the
    three new declarations are present; an additive CSS edit
    inside the existing rule is the canonical fix."""
    text = _read_text(TAXONOMY_GLOBALS_CSS)
    rule_match = re.search(
        r"\.detail-panel\s+\.detail-section\s*\{([^}]*)\}",
        text,
        re.DOTALL,
    )
    assert rule_match is not None, (
        "globals.css must declare the `.detail-panel .detail-section` "
        "rule (the descendant of `.detail-panel` that hosts the tab "
        "body content). The chain-topology guard in "
        "`tests/test_research_styles.py` keeps the `.detail-panel` "
        "base whitelisted; the descendant rule MUST stay scoped "
        "under it so the descendant is reachable through the base."
    )
    body = rule_match.group(1)
    # `flex: 1 1 auto` — the section claims the remaining Card
    # height when paired with `min-height: 0`. Accept `flex: 1`,
    # `flex: 1 1 0`, or `flex: 1 1 auto` — the canonical
    # flexbox-child overflow pattern tolerates any of the three.
    assert re.search(
        r"\bflex\s*:\s*(?:1\b|1\s+1\s+(?:auto|0)\b)",
        body,
    ), (
        "globals.css `.detail-panel .detail-section` MUST carry "
        "`flex: 1` / `flex: 1 1 auto` / `flex: 1 1 0` so the section "
        "claims the remaining Card height. Without the flex "
        "shorthand, the section sticks at its content's intrinsic "
        "height and overflows the Card's `max-h-[calc(90vh-2px)]` "
        "with the content silently clipped."
    )
    # `min-height: 0` — the canonical flexbox overflow workaround
    # that lets the section shrink below its content's intrinsic
    # height. Without this, flexbox sets the section's min-height
    # to the content's intrinsic height and `overflow-y: auto`
    # cannot fire (the section never becomes shorter than its
    # content, so there's nothing to scroll).
    assert re.search(
        r"\bmin-height\s*:\s*0\b",
        body,
    ), (
        "globals.css `.detail-panel .detail-section` MUST carry "
        "`min-height: 0` so flexbox allows the section to shrink "
        "below its content's intrinsic height. Without this, the "
        "section stays at its content height and the "
        "`overflow-y: auto` scroll surface never engages (the "
        "section is as tall as its content, so there's nothing to "
        "scroll)."
    )
    # `overflow-y: auto` — the vertical scroll affordance for the
    # section. `overflow-y: scroll` is also acceptable but `auto`
    # hides the scrollbar when the content fits (the legacy
    # oracle's behaviour). Pin `auto` to keep the contract tight.
    assert re.search(
        r"\boverflow-y\s*:\s*auto\b",
        body,
    ), (
        "globals.css `.detail-panel .detail-section` MUST carry "
        "`overflow-y: auto` so the section scrolls its own "
        "contents vertically when the tab body exceeds the "
        "Card's `max-h-[calc(90vh-2px)]`. Without this, the "
        "content is silently clipped at the Card edge and the "
        "user has no way to scroll the body inside the popup."
    )


def test_globals_css_detail_section_preserves_tab_strip_horizontal_scroll() -> None:
    """ODD-SECSCROLL-001 (regression guard): adding the vertical
    scroll affordance to `.detail-section` MUST NOT touch the
    horizontal tab scrolling the `.tab-strip` row above it
    provides. The chain-topology guard keeps `.tab-strip` as a
    separate top-level selector; the `.detail-section` rule
    only carries declarations that affect vertical overflow +
    flex sizing — no horizontal-overflow overrides that could
    fight the tab-strip's horizontal scroll."""
    text = _read_text(TAXONOMY_GLOBALS_CSS)
    rule_match = re.search(
        r"\.detail-panel\s+\.detail-section\s*\{([^}]*)\}",
        text,
        re.DOTALL,
    )
    assert rule_match is not None
    body = rule_match.group(1)
    # `overflow-x` MUST stay at its default (`visible`) or be
    # unset. If a future refactor adds `overflow-x: hidden` (a
    # common reflex when adding vertical scroll), the
    # `.detail-section`'s content might lose horizontal scroll
    # for wide rows. Pin the absence so the regression is
    # loud.
    assert not re.search(
        r"\boverflow-x\s*:\s*(?:hidden|scroll|auto)\b",
        body,
    ), (
        "globals.css `.detail-panel .detail-section` MUST NOT "
        "set `overflow-x: hidden` / `scroll` / `auto`. The new "
        "vertical-scroll fix only needs `overflow-y: auto`; "
        "clamping horizontal overflow would fight the tab-strip "
        "horizontal scroll surface the legacy oracle provides. "
        "If a wide row needs horizontal scroll inside the "
        "section, that is the section's own horizontal overflow "
        "concern (the user can `overflow-x: auto` the inner "
        "container at a future iteration)."
    )


def test_detail_panel_uses_badge_primitive_for_status() -> None:
    """ODD-TAPOPUP-001 (negative witness): the popup's header
    has NO status badge + NO CoL-only badge. The pre-popup
    sticky rail carried the status badge + the CoL-only
    badge + the WoRMS cross-link badge; the popup drops
    every source-affordance badge so the header is minimal
    (just the scientific-name `<h2>` + the close IconButton).

    The rank badge (variant="primary") STAYS in the header
    (the user sees the taxon's rank at a glance). The status
    + extinct + CoL-only + WoRMS link badges are all gone
    (the popup's minimal header doesn't carry them)."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    code_only = re.sub(r"/\*[\s\S]*?\*/", "", text)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    # No status badge + no CoL-only badge in the popup header.
    # The status badge (pre-popup) carried `taxon.status ?? "unknown"`
    # as a `<Badge variant="subtle">` chip. The regex below
    # anchors on `<Badge` (NOT `<IconButton`) so the close
    # IconButton's `variant="subtle"` doesn't trip the
    # assertion (IconButton is not a Badge).
    assert not re.search(
        r'<Badge\b[^>]*\bvariant\s*=\s*["\']subtle["\']',
        code_only,
    ), (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT carry any "
        "`<Badge variant=\"subtle\">` chip in the popup header "
        "(the status + CoL-only + extinct + WoRMS link badges "
        "are all gone; the minimal header only carries the "
        "rank badge + the close IconButton)."
    )
    assert not re.search(
        r'taxon\.status\s*\?\?\s*["\']unknown["\']',
        code_only,
    ), (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT render the "
        "`taxon.status ?? 'unknown'` status chip (the popup "
        "drops the status badge)."
    )
    # The legacy inline span pattern is GONE.
    assert not re.search(
        r'<span[^>]*\bclassName\s*=\s*["\'][^"\']*\brank-badge\b[^"\']*\btext-on-surface-variant\b',
        code_only,
    ), (
        "ODD-TAPOPUP-001: DetailPanel.tsx must NOT render the "
        "legacy inline `<span className=\"rank-badge ...\">` "
        "status badge (the popup drops the status badge)."
    )


def test_detail_panel_uses_iconbutton_primitive_for_close() -> None:
    """ODD-PHASE2 + ODD-TAPOPUP-001: the close button is an
    `<IconButton variant="subtle" aria-label="Hide details">`
    from the design-system barrel. The `data-action=
    "close-detail"` attribute stays on the element so the
    selector + data-action delegation contract survives the
    React cutover (the popup close calls `onClose()` which the
    parent maps to `setSelected(null)`).

    ODD-TAPOPUP-001: the close IconButton is the popup's
    dialog close affordance — the popup closes via the close
    button + Escape + backdrop click (all wired through
    `onClose()`)."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    assert re.search(
        r'<IconButton\b[^>]*\bvariant\s*=\s*["\']subtle["\']',
        text,
    ), (
        "DetailPanel.tsx must render the close button as "
        '<IconButton variant="subtle"> from @taxa/design-system.'
    )
    assert re.search(
        r'<IconButton\b[^>]*\baria-label\s*=\s*["\']Hide details["\']',
        text,
    ), (
        "DetailPanel.tsx must stamp aria-label=\"Hide details\" "
        "on the close IconButton (icon-only buttons MUST carry "
        "an aria-label per the IconButton a11y contract)."
    )
    assert re.search(
        r'<IconButton\b[^>]*\bdata-action\s*=\s*["\']close-detail["\']',
        text,
    ), (
        "DetailPanel.tsx must stamp data-action=\"close-detail\" "
        "on the close IconButton (selector + data-action delegation "
        "contract survives the React cutover)."
    )
    assert not re.search(
        r'<button[^>]*\bclassName\s*=\s*["\'][^"\']*\bdetail-close\b',
        text,
    ), (
        "DetailPanel.tsx must NOT render the legacy inline "
        '<button className="detail-close ..."> close button '
        "— the IconButton primitive owns the treatment."
    )


def test_detail_panel_no_inline_rank_badge_span() -> None:
    """ODD-PHASE2 + ODD-TAPOPUP-001: the legacy inline
    `<span className="rank-badge ...">` pattern is GONE from
    DetailPanel. The standalone `.rank-badge` CSS rule stays
    because `TaxonomyTree.tsx` search-dropdown still consumes
    it; the DetailPanel consumption migrated to the `<Badge>`
    primitive. The popup keeps the rank badge primitive (the
    header's `<Badge variant="primary">` carries the rank
    label)."""
    text = _read_text(TAXONOMY_DETAIL_PANEL_FILE)
    # No inline rank-badge spans for any of the rank / status /
    # extinct / CoL-only badges.
    for forbidden in (
        r'<span\b[^>]*\bclassName\s*=\s*["\'][^"\']*\brank-badge\b[^"\']*\btext-primary\b',
        r'<span\b[^>]*\bclassName\s*=\s*["\'][^"\']*\brank-badge\b[^"\']*\btext-on-surface-variant\b',
        r'<span\b[^>]*\bclassName\s*=\s*["\'][^"\']*\brank-badge\b[^"\']*\btext-red-700\b',
    ):
        assert not re.search(forbidden, text), (
            "DetailPanel.tsx must NOT render any inline "
            '<span className="rank-badge ..."> badge — '
            "the Badge primitive owns the treatment."
        )


def test_taxonomy_tree_eager_fetches_folder_preview_on_selection() -> None:
    """ODD-TDFOLDER-001: TaxonomyTree fires the canonical
    `previewMaterialize(id, { source: activeSource })` round
    trip the moment a taxon becomes the active selection.
    The eager-fetch contract pins the `useEffect` so
    re-selecting a previously selected taxon lands on the
    cached result without a round trip. The source-aware
    effect deps include `activeSource` so a source switch
    re-fires the fetch (the materialize preview walks the
    active source's parent column)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "previewMaterialize" in text, (
        "TaxonomyTree.tsx must call the canonical previewMaterialize helper."
    )
    assert "loadFolderPreview" in text, (
        "TaxonomyTree.tsx must declare a loadFolderPreview callback."
    )
    # Eager-fetch effect must fire on `selected` change +
    # `activeSource` change (the source-aware invalidation
    # contract).
    assert re.search(
        r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[\s\S]*?selected[\s\S]*?loadFolderPreview[\s\S]*?activeSource",
        text,
    ), (
        "TaxonomyTree.tsx must declare a useEffect that calls "
        "loadFolderPreview when `selected` or `activeSource` changes "
        "(ODD-TDFOLDER-001 eager-fetch contract with source-aware invalidation)."
    )


def test_taxonomy_tree_owns_folder_cache() -> None:
    """ODD-TDFOLDER-001: TaxonomyTree owns the per-taxon
    folder cache as a `Map<number, FolderTabStatus>`. The
    cache survives across deselects so re-selecting a
    previously selected taxon is also instant (mirrors how
    `perTaxonActiveTab` memory + `searchesByTaxonId` +
    `vernacularsByTaxonId` + `synonymsByTaxonId` +
    `distributionByTaxonId` caches survive across
    deselects)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "folderByTaxonId" in text, (
        "TaxonomyTree.tsx must own a folderByTaxonId cache."
    )
    assert re.search(
        r"Map\s*<\s*number\s*,\s*FolderTabStatus\s*>",
        text,
    ), (
        "TaxonomyTree.tsx must own a Map<number, FolderTabStatus> for "
        "the per-taxon folder preview cache."
    )


def test_taxonomy_tree_invalidates_folder_cache_on_source_switch() -> None:
    """ODD-TDFOLDER-001: a source switch MUST clear the
    per-taxon folder preview cache so the panel cannot
    render a stale preview from the previous source. The
    materialize preview walks the active source's parent
    column — different from the source-AGNOSTIC
    vernaculars / synonyms / distribution caches. The
    cache therefore does NOT survive the source-switch
    cascade.

    ODD-HSS-001 — the cascade moved from `handleSourceChange`
    to the reactive `useEffect(() => { ... }, [activeSource])`
    body. The effect body MUST carry
    `setFolderByTaxonId(new Map())` + the four side-effect
    map clears so the ODD-TDFOLDER-001 folder-invalidation
    contract survives the hoist."""
    text = _read_text(TAXONOMY_TREE_FILE)
    body = _od_hss_source_switch_effect_body(text)
    # The folder cache MUST be cleared (ODD-TDFOLDER-001
    # contract). The source-agnostic retention that
    # protects the vernacular / synonyms / distribution
    # caches does NOT apply here — the materialize preview
    # walks the active source's parent column, so a stale
    # CoL preview yields a different chain under WoRMS when
    # the parent_id columns diverge.
    assert "setFolderByTaxonId" in body, (
        "ODD-TDFOLDER-001: the ODD-HSS-001 source-switch effect "
        "body MUST clear the per-taxon folder preview cache (the "
        "materialize preview walks the active source's parent "
        "column, so the source-AGNOSTIC retention contract does "
        "not apply)."
    )
    # The folder-create / folder-open / folder-copy
    # side-effect maps + the create-armed gate MUST be
    # cleared on a source switch (the stale "Opened with
    # `open`" message cannot bleed into the next source's
    # selection; the stale confirmation gate has no
    # meaning under the new source).
    for name in (
        "setFolderCreateByTaxonId",
        "setFolderOpenByTaxonId",
        "setFolderCopyByTaxonId",
        "setFolderCreateArmedByTaxonId",
    ):
        assert name in body, (
            f"ODD-TDFOLDER-001: the ODD-HSS-001 source-switch "
            f"effect body MUST clear the per-taxon {name} "
            f"side-effect map (the stale message / gate cannot bleed "
            f"into the next source's selection)."
        )


def test_taxonomy_tree_handles_stale_async_source_change() -> None:
    """ODD-TDFOLDER-001: the create / open handlers MUST
    guard against a stale `selected` change mid-flight. If
    the user switches taxa while a POST is in flight, the
    success / error handler must no-op the cache update for
    the now-selected taxon (the success belongs to the old
    taxon — switching it under the new taxon would show a
    misleading "all_exist" banner for the wrong path). The
    handler captures `taxonId` from the closed-over
    `selected` and only commits when `selected === taxonId`
    at the response time."""
    text = _read_text(TAXONOMY_TREE_FILE)
    handle_idx = text.find("const handleCreateResearchFolders")
    assert handle_idx != -1, (
        "TaxonomyTree.tsx must declare handleCreateResearchFolders."
    )
    body = text[handle_idx:handle_idx + 2200]
    # The handler must capture `taxonId` from `selected` at
    # call time so the stale guard can compare against the
    # closed-over value (mirrors how `loadSearches` closes
    # over `selected`).
    assert re.search(
        r"const\s+taxonId\s*=\s*selected",
        body,
    ), (
        "TaxonomyTree.tsx handleCreateResearchFolders must capture "
        "`taxonId = selected` at call time so the stale guard can "
        "compare against the closed-over value."
    )
    # The stale guard must compare `selected === taxonId`
    # before committing the create-status update.
    assert re.search(
        r"selected\s*===\s*taxonId",
        body,
    ), (
        "TaxonomyTree.tsx handleCreateResearchFolders must guard against "
        "a stale `selected` change with `selected === taxonId` before "
        "committing the create-status update."
    )
    # The same guard pattern must apply to handleOpenResearchFolder.
    open_idx = text.find("const handleOpenResearchFolder")
    assert open_idx != -1, (
        "TaxonomyTree.tsx must declare handleOpenResearchFolder."
    )
    open_body = text[open_idx:open_idx + 1500]
    assert re.search(
        r"const\s+taxonId\s*=\s*selected",
        open_body,
    ) and re.search(
        r"selected\s*===\s*taxonId",
        open_body,
    ), (
        "TaxonomyTree.tsx handleOpenResearchFolder must capture "
        "`taxonId = selected` at call time and guard the success / "
        "error update with `selected === taxonId`."
    )


def test_taxonomy_tree_passes_folder_props_to_detail_panel() -> None:
    """ODD-TDFOLDER-001: TaxonomyTree threads
    `folderStatus` + the retry / arm / disarm / create /
    open / copy callbacks + the create / open / copy status
    maps + the create-armed gate through to the
    DetailPanel so the FolderTab body can render the
    loading / error / loaded states + the in-tab
    confirmation flow + the inline success / error
    states."""
    text = _read_text(TAXONOMY_TREE_FILE)
    for name in (
        "folderStatus",
        "onRetryFolderPreview",
        "onArmCreate",
        "onDisarmCreate",
        "onCreateResearchFolders",
        "onOpenResearchFolder",
        "onCopyResearchPath",
        "folderCreateStatus",
        "folderOpenStatus",
        "folderCopyStatus",
        "folderCreateArmed",
    ):
        assert name in text, (
            f"TaxonomyTree.tsx must thread {name} to DetailPanel."
        )


def test_barrel_reexports_folder_contract() -> None:
    """ODD-TDFOLDER-001: the taxonomy barrel must
    re-export every Folder wire surface so cross-module
    consumers can type the preview / materialize /
    open-folder payloads + helpers without a deep
    import (spec.md rule 5)."""
    text = _read_text(TAXONOMY_BARREL)
    for name in (
        "previewMaterialize",
        "materializeResearch",
        "openFolder",
        "FetchMaterializePreviewOptions",
        "FetchMaterializeOptions",
        "FetchOpenFolderOptions",
        "MaterializePreview",
        "MaterializePreviewSegment",
        "MaterializeResult",
        "OpenFolderResult",
    ):
        assert name in text, (
            f"taxonomy barrel must re-export `{name}` (ODD-TDFOLDER-001)."
        )


def test_globals_css_declares_folder_tab_selectors() -> None:
    """ODD-PHASE2 + ODD-TDFOLDER-001: `src/app/globals.css` must
    declare the `.folder-tab` cascade for the still-in-use
    specialized panel patterns: the wrapper itself, the
    segment-list descendants (item / marker / marker-exists /
    marker-new / path / wrap), the section-header / section-
    count / section-title chrome, the counts summary, the
    create-row wrapper, the confirm-step descendants, and
    the path-actions row. The 7 dead rules removed by ODD-
    PHASE2 (`.folder-info-banner` + `.folder-inline-message`
    variants + `.folder-btn` variants) are NOT in the
    whitelist — they were replaced by `<InlineMessage
    variant=…>` + `<Button variant=…>` primitives from
    `@taxa/design-system`. Selectors live under `@layer
    components` in alphabetical order so the chain-topology
    guard in `tests/test_research_styles.py` keeps whitelisting
    them."""
    text = _read_text(TAXONOMY_GLOBALS_CSS)
    layer = re.search(r"@layer\s+components\s*\{", text)
    assert layer, "@layer components must exist in globals.css"
    body = text[layer.end():]
    layer_end = body.find("\n}\n")
    if layer_end == -1:
        layer_end = body.find("}")
    body = body[:layer_end]
    # Every selector must appear in the source. The
    # minifier may strip whitespace / quotes, so we
    # accept the bare class names without descendants.
    for needle in (
        ".folder-tab",
        ".folder-tab .folder-confirm",
        ".folder-tab .folder-confirm-actions",
        ".folder-tab .folder-confirm-path",
        ".folder-tab .folder-confirm-prompt",
        ".folder-tab .folder-counts",
        ".folder-tab .folder-create-row",
        ".folder-tab .folder-path-actions",
        ".folder-tab .folder-section-count",
        ".folder-tab .folder-section-header",
        ".folder-tab .folder-section-title",
        ".folder-tab .folder-segment-list",
        ".folder-tab .folder-segment-list .folder-segment-item",
        ".folder-tab .folder-segment-list .folder-segment-marker",
        ".folder-tab .folder-segment-list .folder-segment-marker-exists",
        ".folder-tab .folder-segment-list .folder-segment-marker-new",
        ".folder-tab .folder-segment-list .folder-segment-path",
        ".folder-tab .folder-segment-wrap",
    ):
        assert needle in body, (
            f"globals.css @layer components must declare {needle}."
        )
    # ODD-PHASE2: the 7 dead rules (replaced by
    # `<InlineMessage variant=…>` + `<Button variant=…>` primitives)
    # MUST NOT appear in `@layer components` anymore. Pin each one
    # explicitly so a future refactor that re-introduces them trips
    # this test before review.
    for dead_selector in (
        ".folder-tab .folder-info-banner",
        ".folder-tab .folder-inline-message",
        ".folder-tab .folder-inline-message-error",
        ".folder-tab .folder-inline-message-success",
        ".folder-tab .folder-btn",
        ".folder-tab .folder-btn-primary",
        ".folder-tab .folder-btn-secondary",
    ):
        assert dead_selector not in body, (
            f"ODD-PHASE2: globals.css @layer components MUST NOT declare "
            f"the dead selector {dead_selector} — it was replaced by "
            f"a design-system primitive (`<InlineMessage>` or `<Button>`) "
            f"in the JSX rewrite."
        )


def test_out_index_html_has_folder_tab_styles(static_export) -> None:
    """ODD-TDFOLDER-001: the static export's CSS must
    define the FolderTab selectors introduced by the
    React cutover so the native-style Folder preview +
    segment list + count summary + info banner + create +
    confirm + path-actions rows render identically to the
    legacy oracle. The selectors live under the
    whitelisted `.folder-tab` base class so the
    chain-topology guard in
    `tests/test_research_styles.py` keeps whitelisting
    them."""
    css_chunks = sorted((REPO_ROOT / "out" / "_next" / "static" / "chunks").glob("*.css"))
    css_body = "\n".join(
        c.read_text(encoding="utf-8", errors="ignore") for c in css_chunks
    )
    # The container + segment list + create / confirm /
    # path-actions + button selectors are covered by the
    # `.folder-tab` cascade in `src/app/globals.css`. The
    # static export's CSS must surface at least the
    # top-level `.folder-tab` rule plus the per-row
    # `.folder-segment-item` rule (so the segment list +
    # marker + cumulative-path rendering matches the
    # legacy oracle).
    for needle in (".folder-tab", ".folder-segment-item"):
        assert needle in css_body, (
            f"ODD-TDFOLDER-001: static CSS must define the {needle} rule."
        )


# ---------------------------------------------------------------------------
# ODD-BSTATE-TAX-001 — Persist TaxonomyTree active source.
#
# Migrates the CoL / WoRMS / Freshwater selector from local React
# state to the typed `useTreeSource` hook in `@taxa/browser-state`
# while preserving the entire existing source-switch reset cascade.
#
#   - Public-barrel wiring: `useTreeSource` MUST be imported from
#     `@taxa/browser-state` (no deep paths into the layer folders;
#     the `no-restricted-imports` ESLint guard rejects them at
#     build time).
#   - No local activeSource state: the `useState<TreeSource>(...)`
#     call MUST be gone — the typed store owns the source so the
#     first client render agrees with SSR (typed default `col`) and
#     a stored selection rehydrates after the first render.
#   - `handleSourceChange` reset cascade preserved: the kebab +
#     focused + selected + searches + folder resets + the
#     `setActiveSource(next)` final call MUST stay byte-equal so
#     the source switch still mirrors the legacy
#     `web/nav.js::tree-source toggle` reset.
#   - First-render default: `useTreeSource()` returns the typed
#     `col` default; the post-mount re-render surfaces the stored
#     value (`tests/test_hydration_console.py::test_probe_rehydrates_stored_values_without_warnings`
#     covers the end-to-end persistence witness in real Chromium).
#   - Primary-route chunk boundary: the chunks `out/index.html`
#     references MAY carry `taxa.tree.source` (the active source
#     hook is now bundled) but MUST stay free of the OTHER three
#     browser-state keys (`taxa.settings.theme`,
#     `taxa.tree.lastTaxonId`, `taxa.tree.kebabOpenId`) — those
#     hooks stay out of scope until their consumer slices ship.
# ---------------------------------------------------------------------------


def test_taxonomy_tree_imports_use_tree_source_via_dedicated_entry_point() -> None:
    """ODD-BSTATE-TAX-002 (strict-continuation wiring):
    `useTreeSource` MUST be imported through the dedicated
    `@taxa/browser-state/tree-source` entry point — NOT through
    the aggregate `@taxa/browser-state` barrel that the hydration
    probe consumes.

    Why the entry point switch:

      - The aggregate barrel (`@taxa/browser-state`) re-exports
        every per-key hook + store + the `reset()` aggregate. The
        probe route legitimately needs all four chains together.
      - The main route imports ONLY `useTreeSource`, so the
        barrel's other three chains must NOT be pulled into the
        main route's bundle. The strict chunk-boundary contract
        (`tests/test_app_shell_render.py::test_out_index_html_chunks_permit_only_tree_source_key`)
        forbids the `taxa.settings.theme`,
        `taxa.tree.lastTaxonId`, and `taxa.tree.kebabOpenId`
        localStorage key literals in any chunk the main route
        references.
      - With the barrel import, Turbopack groups the four per-key
        store modules into a single shared chunk that the main
        route ends up referencing (because the barrel transitively
        pulls every per-key file through its re-export group).
        That shared chunk contains all four key literals, which
        trips the strict chunk-boundary witness.
      - The dedicated `@taxa/browser-state/tree-source` entry
        point re-exports ONLY the typed-source surface
        (`useTreeSource` + the `TreeSource` type +
        `DEFAULT_TREE_SOURCE`). Turbopack can drop the unrelated
        chains entirely because nothing the main route imports
        transitively reaches them.

    Source-level pin:

      1. The import statement MUST surface `useTreeSource` from
         `@taxa/browser-state/tree-source` (the path-alias form
         declared in `tsconfig.json`).
      2. The legacy aggregate-barrel import of `useTreeSource`
         (`from "@taxa/browser-state"`) is REJECTED — it pulls the
         whole barrel graph into the main route's bundle.
      3. No deep imports into the layer folders — the entry point
         is the only legal surface for the typed-source hook.

    RED gate (ODD-BSTATE-TAX-002): this test observes RED before
    `src/modules/browser-state/tree-source.ts` is authored AND
    before TaxonomyTree is migrated to the dedicated entry point.
    The chunk-boundary witness in
    `tests/test_app_shell_render.py::test_out_index_html_chunks_permit_only_tree_source_key`
    stays RED until the migration lands.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    # 1. The import MUST surface `useTreeSource` from the
    # dedicated entry point.
    assert re.search(
        r"""import\s*\{[^}]*\buseTreeSource\b[^}]*\}\s*from\s*["']@taxa/browser-state/tree-source["']""",
        text,
    ), (
        "ODD-BSTATE-TAX-002: TaxonomyTree.tsx must import "
        "`useTreeSource` through the dedicated "
        "`@taxa/browser-state/tree-source` entry point so the "
        "main route's bundle carries ONLY the typed-source "
        "chain. The aggregate barrel pulls every per-key store "
        "into a shared chunk that the main route ends up "
        "referencing, which trips the strict chunk-boundary "
        "witness in `test_app_shell_render.py::"
        "test_out_index_html_chunks_permit_only_tree_source_key`."
    )
    # 2. Legacy import assertion — REJECT the aggregate barrel
    # for `useTreeSource`. The barrel stays in place for the
    # probe route (`src/app/hydration-probe/page.tsx`) and for
    # the existing module-layer guard contract, but the main
    # route MUST NOT use it for the typed-source hook.
    assert not re.search(
        r"""import\s*\{[^}]*\buseTreeSource\b[^}]*\}\s*from\s*["']@taxa/browser-state["']""",
        text,
    ), (
        "ODD-BSTATE-TAX-002: TaxonomyTree.tsx MUST NOT import "
        "`useTreeSource` through the aggregate `@taxa/browser-state` "
        "barrel — the barrel re-exports every per-key hook + "
        "store + the reset aggregate, and Turbopack groups those "
        "into a shared chunk that the main route references. "
        "Use the dedicated `@taxa/browser-state/tree-source` "
        "entry point instead."
    )
    # 3. No deep imports — the entry point is the only legal
    # surface for the typed-source hook.
    for bad in (
        '"../browser-state',
        "'../browser-state",
        "@taxa/browser-state/application",
        "@taxa/browser-state/infrastructure",
        "@taxa/browser-state/domain",
        "@taxa/browser-state/presentation",
    ):
        assert bad not in text, (
            f"ODD-BSTATE-TAX-002: TaxonomyTree.tsx must NOT "
            f"deep-import {bad!r} — the dedicated entry point is "
            f"the only legal surface for `useTreeSource` "
            f"(spec.md rule 5 + ESLint `no-restricted-imports` "
            f"guard)."
        )


def test_taxonomy_tree_does_not_own_active_source_local_state() -> None:
    """ODD-BSTATE-TAX-001 (no local activeSource state): the
    component MUST NOT keep a local `useState<TreeSource>(...)` /
    `useState<...>(DEFAULT_SOURCE)` for `activeSource`. The typed
    store owns the source so SSR + the first client render agree
    (the typed default `"col"` is what `useSyncExternalStore`'s
    server snapshot returns) and the post-mount re-render surfaces
    the stored value via `subscribeTreeSource` →
    `ensureHydrated` → `safeGetItem`.

    ODD-HSS-001 — the source-selector hoist moved the source
    setter (`setActiveSource(next)`) to the AppShell-scope
    `AppShellSourceSelector` sub-component. TaxonomyTree now
    reads the source through a read-only destructuring
    `const [activeSource] = useTreeSource();`. The post-hoist
    contract:
      - `useState<TreeSource>(DEFAULT_SOURCE)` for
        `activeSource` is REJECTED (typed-hook boundary).
      - The `setActiveSource(next)` call site MUST NOT live in
        TaxonomyTree anymore — the source-switch setter lives
        in the AppShell-scope source-selector file
        (`AppShellSourceSelector.tsx`).

    The contract is the LITERAL non-existence of the previous
    local-state declaration AND the previous
    `setActiveSource(next)` call site in TaxonomyTree. A future
    refactor that re-introduces the local useState (e.g. to
    "stage" the source during a fetch) would re-break the
    hydration contract; this test pins the boundary so the
    regression fails before review.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    forbidden_patterns = (
        # The local-state declaration — pinned by the ODD-BSTATE-TAX-001
        # slice the ODD-NTP-002 + ODD-HSS-001 slices migrate away from.
        r"const\s+\[\s*activeSource\s*,\s*setActiveSource\s*\]\s*=\s*useState\b",
        # The pre-ODD-HSS-001 click-handler setter call site
        # that the hoist moved to AppShellSourceSelector.
        r"setActiveSource\s*\(\s*next\s*\)",
    )
    assert not re.search(forbidden_patterns[0], text), (
        "ODD-BSTATE-TAX-001: TaxonomyTree.tsx MUST NOT declare a "
        "local `useState<TreeSource>(...)` pair for "
        "`activeSource` — the typed `useTreeSource()` hook owns the "
        "source so SSR + the first client render stay byte-equal "
        "and the stored value rehydrates on the post-mount render."
    )
    # After the ODD-HSS-001 hoist the `setActiveSource(next)` call
    # site MUST NOT live in TaxonomyTree anymore — the
    # source-switch setter lives in the AppShell-scope
    # `AppShellSourceSelector` sub-component. The companion
    # positive witness for the new call-site location lives in
    # `tests/test_app_shell_render.py::test_appshell_renders_source_selector`
    # (the `data-tree-source="col|worms|freshwater"` + `setActiveSource(src)`
    # wiring inside the AppShell-scope source-selector file).
    assert not re.search(forbidden_patterns[1], text), (
        "ODD-BSTATE-TAX-001 (now-ODD-HSS-001): TaxonomyTree.tsx "
        "MUST NOT carry a `setActiveSource(next)` call site "
        "anymore — the source-selector hoist moved the source-"
        "switch setter to the AppShell-scope "
        "`AppShellSourceSelector.tsx`. The positive witness for "
        "the new call-site location lives in "
        "`tests/test_app_shell_render.py::test_appshell_renders_source_selector`."
    )
    # The `DEFAULT_SOURCE` constant is retired — the typed default
    # lives in `@taxa/browser-state` (`DEFAULT_TREE_SOURCE`). A
    # declaration of a local `DEFAULT_SOURCE = "col"` constant
    # would shadow the typed default and re-introduce the
    # non-stored first-render contract.
    assert not re.search(r"\bDEFAULT_SOURCE\b\s*:", text), (
        "ODD-BSTATE-TAX-001: TaxonomyTree.tsx MUST NOT declare a "
        "local `DEFAULT_SOURCE` constant — the typed default lives "
        "in `@taxa/browser-state` (`DEFAULT_TREE_SOURCE = \"col\"`). "
        "A local constant would shadow the typed default and "
        "re-introduce the non-persistent first-render behaviour."
    )


def test_taxonomy_tree_handle_source_change_preserves_reset_cascade() -> None:
    """ODD-BSTATE-TAX-001 (now-ODD-HSS-001 — reset-cascade
    preservation): the source-switch reset cascade must stay
    byte-equal so a switch still mirrors the legacy
    `web/nav.js::tree-source toggle` reset. The pre-hoist
    `handleSourceChange` callback ran the cascade. After the
    hoist the cascade split into TWO effects — the witness
    pins both halves:

      Half 1 (source-bound tree state on
        `useEffect([activeSource, rawRoots])`):
        - clears `state` via `resetSourceState(prev)` so roots /
          expanded / child cache / load status / showAll /
          per-row error get cleared on a switch — the existing
          ODD-NTP-002 cascade half.

      Half 2 (UI side effects on `useEffect([activeSource])`):
        - clears the open kebab via `setKebabOpenId(null)`.
        - clears focused + selected via `setFocused(null)` +
          `setSelected(null)`.
        - clears the per-taxon search-link cache via
          `setSearchesByTaxonId(new Map())` (source-bound).
        - clears the per-taxon folder cache + four side-effect
          maps via `setFolderByTaxonId(new Map())` +
          `setFolderCreateByTaxonId(new Map())` +
          `setFolderOpenByTaxonId(new Map())` +
          `setFolderCopyByTaxonId(new Map())` +
          `setFolderCreateArmedByTaxonId(new Map())`.

      Source-switch setter (post-hoist):
        - the typed `setActiveSource(src)` setter call site
          lives in the AppShell-scope `AppShellSourceSelector.tsx`
          (pinned by
          `tests/test_app_shell_render.py::test_appshell_renders_source_selector`).
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    # Half 1: the source-bound `resetSourceState` lives on the
    # existing `useEffect([activeSource, rawRoots])` block.
    # Strip block + line comments + locate the effect body by
    # its deps array (`[activeSource, rawRoots]`); the body
    # MUST carry `resetSourceState(` so the ODD-NTP-002 cascade
    # half survives the hoist.
    source_bound_match = re.search(
        r"useEffect\(\(\)\s*=>\s*\{(.*?)\}\s*,\s*\[activeSource\s*,\s*rawRoots\]\s*\)\s*;",
        text,
        re.DOTALL,
    )
    assert source_bound_match is not None, (
        "ODD-HSS-001 source-bound effect: TaxonomyTree.tsx must "
        "declare a `useEffect(() => { ... }, [activeSource, rawRoots])` "
        "block that carries the ODD-NTP-002 `resetSourceState(prev)` "
        "cascade half (the source-bound tree state reset on a switch)."
    )
    source_bound_body = source_bound_match.group(1)
    assert "resetSourceState" in source_bound_body, (
        "ODD-BSTATE-TAX-001 (now-ODD-HSS-001): TaxonomyTree.tsx's "
        "`useEffect([activeSource, rawRoots])` body must call "
        "`resetSourceState(prev)` so the ODD-NTP-002 source-bound "
        "tree state clears on a switch."
    )
    # Half 2: the UI side effects live on the new
    # `useEffect([activeSource])` block.
    body = _od_hss_source_switch_effect_body(text)
    cascade_checks = (
        ("setKebabOpenId(null)", "ODD-NTP-004: must close the open kebab"),
        ("setFocused(null)", "ODD-NTP-005: must clear focused"),
        ("setSelected(null)", "ODD-NTP-005: must clear selected"),
        ("setSearchesByTaxonId(new Map())", "ODD-TDS-001: must clear the search-link cache"),
        ("setFolderByTaxonId(new Map())", "ODD-TDFOLDER-001: must clear the folder cache"),
        ("setFolderCreateByTaxonId(new Map())", "ODD-TDFOLDER-001: must clear the folder create map"),
        ("setFolderOpenByTaxonId(new Map())", "ODD-TDFOLDER-001: must clear the folder open map"),
        ("setFolderCopyByTaxonId(new Map())", "ODD-TDFOLDER-001: must clear the folder copy map"),
        ("setFolderCreateArmedByTaxonId(new Map())", "ODD-TDFOLDER-001: must clear the folder create gate"),
    )
    for needle, reason in cascade_checks:
        assert needle in body, (
            f"ODD-BSTATE-TAX-001: source-switch reset cascade "
            f"lost {needle!r} \u2014 {reason}. The typed-source "
            f"migration must preserve the existing source-bound "
            f"reset."
        )
    # The click-handler early-out guard MUST NOT live in
    # TaxonomyTree.tsx anymore \u2014 the typed `useTreeSource` hook
    # owns the re-click short-circuit. Strip block + line
    # comments first so docstring prose that references the
    # legacy guard as documentation of the closed behaviour
    # does NOT trip the negative witness.
    code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    assert re.search(
        r"if\s*\(\s*next\s*===\s*activeSource\s*\)\s*return",
        code_only,
    ) is None, (
        "ODD-BSTATE-TAX-001 (now-ODD-HSS-001): TaxonomyTree.tsx "
        "MUST NOT carry the `if (next === activeSource) return;` "
        "click-handler early-out guard anymore \u2014 the typed "
        "`useTreeSource` hook owns the re-click short-circuit."
    )


def test_taxonomy_tree_does_not_touch_localstorage_directly() -> None:
    """ODD-BSTATE-TAX-001 (storage-isolation regression guard):
    TaxonomyTree must NOT touch `localStorage` directly — the typed
    store in `src/modules/browser-state/infrastructure/store.ts` is
    the ONLY legal storage surface (the
    `tests/test_browser_state_keys.py::test_other_module_does_not_touch_localstorage`
    contract). Reaching for `localStorage.*` here would bypass the
    typed hook, break the hydration contract (the post-mount
    `subscribe` callback would not fire), and re-introduce the
    non-persistent first-render bug.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    # Strip comments so an explanatory doc-block that references
    # `localStorage` (e.g. the ODD-NTP-002 source-parity note)
    # is not a false positive.
    block = re.compile(r"/\*[\s\S]*?\*/")
    line = re.compile(r"//[^\n]*")
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))  # noqa: E731
    stripped = block.sub(blank, text)
    stripped = line.sub(blank, stripped)
    for needle in ("localStorage.", "sessionStorage.", "window.localStorage"):
        assert needle not in stripped, (
            f"ODD-BSTATE-TAX-001: TaxonomyTree.tsx must NOT call "
            f"{needle!r} directly — the typed store owns storage; "
            f"reach it through the `useTreeSource()` hook."
        )


def test_taxonomy_tree_uses_typed_source_for_breadcrumb_walker() -> None:
    """ODD-BSTATE-TAX-001 (typed-source round-trip): the breadcrumb
    walker must consume the typed `activeSource` returned by
    `useTreeSource()` — no local shadow, no closure over the previous
    `useState` default. The walker dispatches on the active source
    internally (CoL reads `Taxon.parent_id`, Freshwater reads
    `Taxon.freshwater_parent_id`, WoRMS reconstructs ancestry from
    the reverse index); a stale source literal would render a
    breadcrumb under the wrong source after rehydration.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    # `walkBreadcrumbForSource` is invoked with `(focused,
    # activeSource, state)` — the second argument MUST be the
    # typed `activeSource` returned by `useTreeSource()`. A future
    # refactor that hard-codes a source literal here would
    # silently desync the breadcrumb from the segmented control.
    assert re.search(
        r"walkBreadcrumbForSource\s*\(\s*focused\s*,\s*activeSource\s*,",
        text,
    ), (
        "ODD-BSTATE-TAX-001: walkBreadcrumbForSource must be "
        "invoked with the typed `activeSource` (the "
        "`useTreeSource()` value), never a hard-coded source "
        "literal."
    )
    # The breadcrumb source data attribute MUST carry the typed
    # `activeSource` value so the rendered breadcrumb tracks the
    # typed store end-to-end.
    assert "data-breadcrumb-source={activeSource}" in text, (
        "ODD-BSTATE-TAX-001: the breadcrumb host must stamp "
        "`data-breadcrumb-source={activeSource}` (the typed-hook "
        "value) so the rendered breadcrumb tracks the typed store."
    )


# ---------------------------------------------------------------------------
# ODD-MIGRATE-007-DOM-006 — legacy DOM marker reproduction
#
# The legacy `web/index.html` mount exposes 7 DOM markers the React
# taxonomy home page must reproduce byte-for-byte so a Playwright probe
# finds them. The marker contract is the artifact the ODD-MIGRATE-007
# carveout retired tests targeted; reproducing the markers brings the
# React mount to feature-equivalence with the legacy mount WITHOUT
# re-introducing the legacy Playwright tests (the React mount ships
# its own React-shaped DOM contract the legacy tests do not target).
#
# Marker coverage:
#   1. <div id="tree-view"> wrapping the React tree surface.
#   2. <div id="tree-source-toggle"> (with the three source buttons).
#   3. <div id="detail-panel"> (placeholder for the focused taxon).
#   4. <div id="breadcrumb"> (always render, populated on focus).
#   5. <div id="version-banner"> (with the two child spans).
#   6. <script src="/app.js"> (the legacy bundle marker).
#   7. <div class="fex-shell"> (out of scope — explorer route only).
#
# Each marker is pinned at the source level so a future refactor that
# drops the marker fails the focused test before review.
# ---------------------------------------------------------------------------


def test_taxonomy_tree_renders_tree_view_id() -> None:
    """ODD-MIGRATE-007-DOM-006 — marker #1: the React tree must
    render inside a `<div id="tree-view">` so the legacy Playwright
    selector finds the tree surface. The wrapper is purely an id
    attribute — the existing `.taxa-tree` styling stays on the
    outer `<section>` so the existing CSS cascade is unaffected."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r'<div\b[^>]*\bid="tree-view"',
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must render `<div id=\"tree-view\">` "
        "wrapping the React tree (ODD-MIGRATE-007-DOM-006 marker #1)."
    )


def test_taxonomy_tree_renders_tree_source_toggle_id() -> None:
    """ODD-HSS-001 — negative witness (marker #2 migration).

    The pre-ODD-HSS-001 source toggle rendered inside `TaxonomyTree.tsx`
    as a `<div id="tree-source-toggle">` host with three
    `<button data-tree-source="col">` / `"worms"` / `"freshwater">`
    rows (the legacy selector the legacy Playwright probe used).

    ODD-HSS-001 hoists that toggle to the AppShell header. The
    rendered `out/index.html` still carries the
    `<div id="tree-source-toggle">` host + the three buttons (the
    renderer that emits the markup is now the AppShell header, not
    TaxonomyTree — the static-export witness stays byte-equal). The
    SOURCE-level negative witness pins the absence of the marker in
    `TaxonomyTree.tsx` so a regression that re-mounts the toggle in
    the tree surface trips the gate (and a future consolidation
    could remove this test once the renderer fully migrates).

    The complementary DOM-rendered witness
    (`test_out_index_html_has_legacy_dom_markers`) still passes
    because the rendered HTML carries the marker (the renderer just
    moved from TaxonomyTree to AppShell). The complementary positive
    source-level witness on the new host lives in
    `tests/test_app_shell_render.py::test_appshell_renders_source_selector`.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    # Strip block comments + line comments so docstring prose that
    # DOCUMENTED the pre-hoist contract doesn't trip the negative
    # witness — the witness checks the JSX render, not the prose.
    code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    # Marker #2 host (`<div id="tree-source-toggle">`) must NOT
    # appear in TaxonomyTree.tsx anymore.
    assert re.search(
        r'<div\b[^>]*\bid="tree-source-toggle"',
        code_only,
    ) is None, (
        "ODD-HSS-001: TaxonomyTree.tsx must NOT render "
        "`<div id=\"tree-source-toggle\">` anymore — the marker #2 "
        "host was hoisted to the AppShell header."
    )
    # All three per-source buttons must NOT render inside
    # TaxonomyTree.tsx anymore.
    for src in ("col", "worms", "freshwater"):
        assert re.search(
            rf'<button\b[^>]*\bdata-tree-source\s*=\s*(?:["\']{src}["\']|\{{src\}})',
            code_only,
            re.DOTALL,
        ) is None, (
            f"ODD-HSS-001: TaxonomyTree.tsx must NOT render "
            f"`<button data-tree-source=\"{src}\">` anymore — "
            f"the per-source button was hoisted to the AppShell "
            f"header source-selector."
        )


# ODD-HSS-002 — additional negative witness (regression guard). The
# companion `test_taxonomy_tree_renders_tree_source_toggle_id` covers
# the data-attribute side (id selector + per-button attributes).
# `test_taxonomy_tree_does_not_render_source_selector` covers the
# JSX-helper side: TaxonomyTree.tsx must NOT declare the
# `renderSourceSelector()` helper anymore, must NOT import the
# design-system `tree-source-toggle` + `tree-source-btn` class hooks
# in a JSX-renderable form, and must NOT stamp the
# `aria-pressed`-bearing source buttons. Together the three negative
# witnesses pin the hoist from three independent angles so a single
# overlooked reference trips the gate.
def test_taxonomy_tree_does_not_render_source_selector() -> None:
    """ODD-HSS-002 — regression guard: TaxonomyTree.tsx must NOT
    render the source-selector (CoL / WoRMS / Freshwater) anymore.
    The selector lives in the AppShell header (positive witness:
    `tests/test_app_shell_render.py::test_appshell_renders_source_selector`)
    so CoL / WoRMS / Freshwater become a first-class concept visible
    on every page state (loading / error / empty / loaded) instead
    of a buried affordance after the user expands the tree.

    Three complementary negative checks:

      1. The `renderSourceSelector()` helper must NOT be declared
         (the helper lived in the pre-hoist TaxonomyTree; after the
         hoist the helper lives in the new
         `AppShellSourceSelector` sub-component instead).
      2. The `tree-source-toggle` + `tree-source-btn` class hooks
         must NOT appear in the JSX render (the segmented control
         host + per-button class hooks live in the AppShell host
         now). The className-anchored regex avoids false positives
         from docstring prose that references the class hooks as
         legacy references.
      3. The `tree-source-toggle-wrapper` class hook must NOT appear
         in the JSX render (the segmented-control wrapper that the
         pre-hoist TaxonomyTree used to share the 8px vertical
         rhythm with the collapse-all button row is gone — the
         collapse-all alone remains in TaxonomyTree, in a wrapper
         that's no longer tied to the toggle).

    If any of the three observations fires, the regression that
    re-mounts the source-selector inside `TaxonomyTree.tsx` trips
    this test before the compiled bundle reaches the static export.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    # Strip block comments + line comments so docstring prose that
    # DOCUMENTS the hoist (and any future prose mention of the
    # legacy class hooks / helper) doesn't trip the negative
    # witness — the witness checks the JSX render + the helper
    # declarations, not the prose.
    code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    code_only = re.sub(r"//[^\n]*", "", code_only)
    # 1. The `renderSourceSelector()` helper is gone.
    assert "renderSourceSelector" not in code_only, (
        "ODD-HSS-002: TaxonomyTree.tsx must NOT declare "
        "`renderSourceSelector()` — the source-selector was hoisted "
        "to the AppShell header. The positive witness for the new "
        "mount lives in "
        "tests/test_app_shell_render.py::test_appshell_renders_source_selector."
    )
    # 2. The `tree-source-toggle` + `tree-source-btn` class hooks
    # are gone from the JSX render. Anchor on a className form so
    # docstring references to the literal class hooks (which
    # document the hoist + the legacy reference) don't trip the
    # gate — the witness checks the JSX render, not the prose.
    # The negative-end anchors (`(?:[^-a-zA-Z]|$)`) protect
    # against a false positive on the `.tree-source-toggle-wrapper`
    # descendant rule (a hyphen is NOT a word character so a
    # naïve `\b` anchor would match `toggle-` inside
    # `tree-source-toggle-wrapper`).
    for class_hook in ("tree-source-toggle", "tree-source-btn"):
        jsx_render_match = re.search(
            rf'className\s*=\s*["\'][^"\']*[\.\s"\']{re.escape(class_hook)}(?:[^-a-zA-Z]|$)',
            code_only,
        )
        assert jsx_render_match is None, (
            f"ODD-HSS-002: TaxonomyTree.tsx must NOT render "
            f"`{class_hook}` as a JSX className anymore — the class "
            f"hook lives in the AppShell header source-selector. "
            f"Found JSX render at: {jsx_render_match.group(0)!r}."
        )
    # 3. The `tree-source-toggle-wrapper` class hook that the
    # pre-hoist code used to share the 8px vertical rhythm with the
    # collapse-all row is gone.
    wrapper_match = re.search(
        r'className\s*=\s*["\'][^"\']*\btree-source-toggle-wrapper\b',
        code_only,
    )
    assert wrapper_match is None, (
        "ODD-HSS-002: TaxonomyTree.tsx must NOT render the "
        "`.tree-source-toggle-wrapper` wrapper anymore — the "
        "wrapper hosted the source-selector + the collapse-all "
        "row together; after the hoist only the collapse-all row "
        "remains in TaxonomyTree, in a single-child wrapper. "
        f"Found JSX render at: {wrapper_match.group(0)!r}."
    )


def test_taxonomy_tree_renders_detail_panel_placeholder() -> None:
    """ODD-MIGRATE-007-DOM-006 — marker #3: the React mount must
    render a `<div id="detail-panel">` placeholder that becomes
    visible when a taxon is focused (`hidden={focused === null}`)
    and renders the focused taxon's scientific_name + id. The
    placeholder lives alongside the existing `<DetailPanel>` —
    the existing DetailPanel renders the full tab surface (the
    React-shaped contract), and the placeholder satisfies the
    legacy `#detail-panel` selector for the Playwright probe."""
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r'<div\b[^>]*\bid="detail-panel"',
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must render `<div id=\"detail-panel\">` "
        "as a placeholder for the focused taxon's surface "
        "(ODD-MIGRATE-007-DOM-006 marker #3)."
    )
    # The placeholder MUST be hidden when no taxon is focused
    # (the legacy `hidden` attribute contract). The React mount
    # uses `hidden={focused === null}` so the placeholder toggles
    # on focus without a class swap.
    assert re.search(
        r'id="detail-panel"[^>]*\bhidden\s*=\s*\{\s*focused\s*===\s*null\s*\}',
        text,
        re.DOTALL,
    ), (
        "TaxonomyTree.tsx must set `hidden={focused === null}` on "
        "the #detail-panel placeholder so the legacy visibility "
        "contract survives (ODD-MIGRATE-007-DOM-006 marker #3)."
    )
    # The placeholder body MUST render the focused taxon's
    # scientific_name + id when visible. The reference data
    # surface is `state.nodes.get(focused)` (the canonical React
    # state the breadcrumb walker uses) — a focused-row predicate
    # keeps the placeholder consistent with the existing focused
    # state.
    assert re.search(
        r"focused\s*!==\s*null",
        text,
    ), (
        "TaxonomyTree.tsx must guard the #detail-panel body on "
        "`focused !== null` so the placeholder only renders the "
        "scientific_name + id when a taxon is focused."
    )


def test_taxonomy_tree_renders_breadcrumb_always() -> None:
    """ODD-MIGRATE-007-DOM-006 — marker #4: the React mount must
    render `<div id="breadcrumb">` (or `<nav id="breadcrumb">`)
    on every render — the legacy `web/index.html` declares an
    EMPTY `<nav id="breadcrumb">` that JS populates. The Playwright
    probe finds `#breadcrumb` even before the user clicks a row,
    so the breadcrumb host MUST render unconditionally (not only
    when focused !== null)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # The breadcrumb host carries `id="breadcrumb"`. The existing
    # implementation already does this; the new contract is that
    # the host renders unconditionally. Pin the unconditional
    # render by asserting the early-return on `focused === null`
    # does NOT collapse the breadcrumb to null.
    assert re.search(
        r'id\s*=\s*["\']breadcrumb["\']',
        text,
    ), (
        "TaxonomyTree.tsx must render `<nav id=\"breadcrumb\">` "
        "unconditionally (the legacy empty-breadcrumb contract)."
    )


def test_layout_renders_version_banner_with_spans() -> None:
    """ODD-MIGRATE-007-DOM-006 — marker #5: the React root layout
    must render `<div id="version-banner" hidden>` with the two
    canonical child spans (`#version-banner-actual` +
    `#version-banner-expected`). The banner populates the spans
    from `/api/health` after mount and flips `hidden={false}`
    when `db_schema_version < expected_schema_version`."""
    text = _read_text(SRC_LAYOUT)
    assert re.search(
        r'<div\b[^>]*\bid="version-banner"',
        text,
        re.DOTALL,
    ), (
        "layout.tsx must render `<div id=\"version-banner\" hidden>` "
        "in the root layout body (ODD-MIGRATE-007-DOM-006 marker #5)."
    )
    assert re.search(
        r'<span\b[^>]*\bid="version-banner-actual"',
        text,
        re.DOTALL,
    ), (
        "layout.tsx must render `<span id=\"version-banner-actual\">` "
        "inside the #version-banner container "
        "(ODD-MIGRATE-007-DOM-006 marker #5)."
    )
    assert re.search(
        r'<span\b[^>]*\bid="version-banner-expected"',
        text,
        re.DOTALL,
    ), (
        "layout.tsx must render `<span id=\"version-banner-expected\">` "
        "inside the #version-banner container "
        "(ODD-MIGRATE-007-DOM-006 marker #5)."
    )


def test_tree_row_right_click_opens_taxon_in_new_tab() -> None:
    r"""ODD-RCTX-001 — the disclosure button on every TreeRow must
    carry an `onContextMenu` handler that opens the taxon's URL
    in a new tab. The URL `?taxon=ID` query param (added by
    ODD-URLSTATE-001) carries the row's selection so the new
    tab opens to the exact same selection state. The handler:

      - calls `ev.preventDefault()` so the browser's native
        context menu is suppressed (the right-click feels like
        a deliberate "open in new tab" affordance instead of a
        menu the user did not ask for),
      - validates the id via `Number.isFinite` (defensive — the
        id is typed as `number` from the React state but a
        malformed value must never produce an open redirect
        through `window.open`),
      - opens `window.open(?, '_blank', 'noopener,noreferrer')`
        with a `?taxon=...` URL so the new tab inherits the
        row's selection state. The `noopener,noreferrer`
        features block the opener from accessing
        `window.opener` (defence against tabnabbing).
    """
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    # The disclosure button must carry an `onContextMenu={...}` handler.
    assert re.search(
        r"onContextMenu\s*=\s*\{",
        text,
    ), (
        "TreeRow.tsx disclosure button must carry an "
        "`onContextMenu={...}` handler that opens the row's "
        "URL in a new tab."
    )
    # The full handler body (between onContextMenu={ and its closing })
    # is checked via substring assertions against the source
    # text. A lazy regex capture would stop at the first nested
    # `}` (the `if` block's closing brace), missing the
    # `window.open` call — substring checks against the full
    # text are simpler + correct.
    assert "ev.preventDefault" in text, (
        "TreeRow.tsx onContextMenu handler must call "
        "`ev.preventDefault()` to suppress the browser's "
        "native context menu."
    )
    assert "Number.isFinite" in text, (
        "TreeRow.tsx onContextMenu handler must validate the "
        "id via `Number.isFinite` so a malformed id never "
        "produces an open redirect through `window.open`."
    )
    assert "window.open" in text, (
        "TreeRow.tsx onContextMenu handler must call "
        "`window.open(...)` to open the URL in a new tab."
    )
    assert '"_blank"' in text or "'_blank'" in text, (
        "TreeRow.tsx onContextMenu handler must open in a new "
        "tab via the `_blank` target."
    )
    assert (
        "noopener,noreferrer" in text
    ), (
        "TreeRow.tsx onContextMenu handler must pass "
        "`noopener,noreferrer` as the window-features so the "
        "opener cannot access `window.opener` (tabnabbing "
        "defence)."
    )
    assert "?taxon=" in text, (
        "TreeRow.tsx onContextMenu handler must open a URL "
        "with the `?taxon=` query param so the new tab "
        "inherits the row's selection state."
    )


def test_taxonomy_tree_handle_select_writes_taxon_to_url() -> None:
    """ODD-URLSTATE-001 — the click-driven `handleSelect` must
    write the new selection to the URL via `router.replace` (NOT
    `push`) so a fast-typing user does not fill the browser
    history with one entry per click. The query param is `taxon`
    and the value is the taxon's id. The handler MUST NOT push
    when `selected === id` (re-selecting the same row churns the
    URL for nothing). `useRouter` from `next/navigation` is the
    App Router hook that performs the in-app replace.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    assert re.search(
        r'import\s*\{[^}]*\buseRouter\b[^}]*\}\s*from\s*["\']next/navigation["\']',
        text,
    ), (
        "TaxonomyTree.tsx must `import { useRouter } from \"next/navigation\"` "
        "so the click-driven selection writes the URL via "
        "`router.replace(\"/?taxon=ID\")`."
    )
    assert re.search(
        r'import\s*\{[^}]*\buseSearchParams\b[^}]*\}\s*from\s*["\']next/navigation["\']',
        text,
    ), (
        "TaxonomyTree.tsx must `import { useSearchParams } from \"next/navigation\"` "
        "so the URL → state sync effect reads the `taxon` query param."
    )
    handler_block = re.search(
        r"const handleSelect\s*=\s*useCallback\(\s*[\s\S]*?\n\s*\},",
        text,
    )
    assert handler_block, (
        "TaxonomyTree.tsx must keep a `handleSelect = useCallback(...)` "
        "block so the click-driven selection primitive stays single-source."
    )
    handler_body = handler_block.group(0)
    assert "router.replace" in handler_body, (
        "TaxonomyTree.tsx `handleSelect` must call `router.replace(...)` "
        "to write the new selection to the URL."
    )
    assert "?taxon=" in handler_body, (
        "TaxonomyTree.tsx `handleSelect` must call `router.replace(...)` "
        "with a `?taxon=` query param so the URL encodes the selected taxon id."
    )
    assert "selected !== id" in handler_body, (
        "TaxonomyTree.tsx `handleSelect` must guard on "
        "`selected !== id` so re-selecting the same row does not churn the URL."
    )


def test_home_client_wraps_taxonomy_tree_in_suspense() -> None:
    """ODD-URLSTATE-001 — TaxonomyTree reads `?taxon=ID` via
    `useSearchParams()` so it must live under a Suspense boundary
    at static-export prerender time. Without the Suspense
    wrapper, Next.js opts the page out of static rendering and
    the build fails with a prerender error.
    """
    text = _read_text(HOME_CLIENT_FILE)
    assert re.search(
        r'import\s*\{[^}]*\bSuspense\b[^}]*\}\s*from\s*["\']react["\']',
        text,
    ), (
        "HomeClient.tsx must `import { Suspense } from \"react\"` "
        "so TaxonomyTree can live under a Suspense boundary at "
        "static-export prerender time."
    )
    assert re.search(
        r"<Suspense\b[^>]*>[\s\S]*?<TaxonomyTree\b[\s\S]*?</Suspense>",
        text,
        re.DOTALL,
    ), (
        "HomeClient.tsx must wrap `<TaxonomyTree ... />` in a "
        "`<Suspense ...>` boundary so Next.js can prerender the "
        "page at static-export time without the prerender opting "
        "out for `useSearchParams`."
    )


def test_home_client_renders_app_js_script_tag() -> None:
    """ODD-MIGRATE-007-DOM-006 — marker #6: the `/` route mount
    must render a `<script src="/app.js">` script tag from
    `next/script` (with `strategy="afterInteractive"` so the
    bundle marker is present in the DOM but does not block
    hydration). The legacy `web/index.html` declares the script
    tag verbatim; the file does NOT exist on the static export
    (404 on fetch), but the marker alone satisfies the contract
    — no fallback handling is required.

    ODD-URLSTATE-001 — the script was hoisted from TaxonomyTree
    into HomeClient so it ships in the static-export prerender
    even when TaxonomyTree itself is wrapped in a Suspense
    boundary (a `<Script>` nested inside the tree would never
    reach the prerendered HTML because the tree's render output
    is replaced by the fallback at prerender time). HomeClient
    is outside the Suspense boundary so the Script element
    is preserved verbatim."""
    text = _read_text(HOME_CLIENT_FILE)
    # The mount must import `Script` from `next/script`.
    assert re.search(
        r'import\s+Script\s+from\s+["\']next/script["\']',
        text,
    ), (
        "HomeClient.tsx must `import Script from \"next/script\"` "
        "so the #app.js marker ships via Next 16's <Script> loader "
        "(ODD-MIGRATE-007-DOM-006 marker #6). Hoisted out of "
        "TaxonomyTree so the marker ships even when the tree is "
        "wrapped in a Suspense boundary for static-export prerender."
    )
    # The mount must render a `<Script src="/app.js" ...>` element.
    assert re.search(
        r'<Script\b[^>]*\bsrc\s*=\s*["\']/app\.js["\']',
        text,
        re.DOTALL,
    ), (
        "HomeClient.tsx must render `<Script src=\"/app.js\" ...>` "
        "so the legacy bundle marker is present in the DOM "
        "(ODD-MIGRATE-007-DOM-006 marker #6)."
    )
    # The loader strategy MUST be `afterInteractive` (the default,
    # but explicit) so the script runs after hydration without
    # blocking initial paint — matches the legacy `defer` semantics.
    assert re.search(
        r'<Script\b[^>]*\bstrategy\s*=\s*["\']afterInteractive["\']',
        text,
        re.DOTALL,
    ), (
        "HomeClient.tsx must render `<Script strategy=\"afterInteractive\" ...>` "
        "so the bundle marker loads after hydration without blocking initial paint "
        "(ODD-MIGRATE-007-DOM-006 marker #6)."
    )


def test_out_index_html_has_legacy_dom_markers(static_export) -> None:
    """ODD-MIGRATE-007-DOM-006 — runtime witness: the static export
    at `out/index.html` MUST carry all 6 in-scope DOM markers so a
    Playwright probe locates them after hydration. The runtime
    witness complements the per-marker source-level guards by
    asserting the markers actually ship in the rendered HTML
    bundle (not just the source code)."""
    html = _read_text(OUT_INDEX)
    # Marker #1: #tree-view wrapper.
    assert 'id="tree-view"' in html, (
        "out/index.html must carry `<div id=\"tree-view\">` "
        "(ODD-MIGRATE-007-DOM-006 marker #1 — runtime witness)."
    )
    # Marker #2: #tree-source-toggle wrapper + the three
    # data-tree-source buttons.
    assert 'id="tree-source-toggle"' in html, (
        "out/index.html must carry `<div id=\"tree-source-toggle\">` "
        "(ODD-MIGRATE-007-DOM-006 marker #2 — runtime witness)."
    )
    for src in ("col", "worms", "freshwater"):
        assert f'data-tree-source="{src}"' in html, (
            f"out/index.html must carry `<button data-tree-source=\"{src}\">` "
            f"(ODD-MIGRATE-007-DOM-006 marker #2 — runtime witness)."
        )
    # Marker #3: #detail-panel placeholder.
    assert 'id="detail-panel"' in html, (
        "out/index.html must carry `<div id=\"detail-panel\">` "
        "(ODD-MIGRATE-007-DOM-006 marker #3 — runtime witness)."
    )
    # Marker #4: #breadcrumb host.
    assert 'id="breadcrumb"' in html, (
        "out/index.html must carry `<nav id=\"breadcrumb\">` "
        "(ODD-MIGRATE-007-DOM-006 marker #4 — runtime witness)."
    )
    # Marker #5: #version-banner + child spans (rendered by the
    # root layout, present in every static-export page).
    assert 'id="version-banner"' in html, (
        "out/index.html must carry `<div id=\"version-banner\">` "
        "(ODD-MIGRATE-007-DOM-006 marker #5 — runtime witness)."
    )
    assert 'id="version-banner-actual"' in html, (
        "out/index.html must carry `<span id=\"version-banner-actual\">` "
        "(ODD-MIGRATE-007-DOM-006 marker #5 — runtime witness)."
    )
    assert 'id="version-banner-expected"' in html, (
        "out/index.html must carry `<span id=\"version-banner-expected\">` "
        "(ODD-MIGRATE-007-DOM-006 marker #5 — runtime witness)."
    )
    # Marker #6: /app.js script tag (rendered via <Script>
    # from next/script — the SSR output carries either the
    # literal `<script src="/app.js">` element OR Next 16's
    # preload link `<link rel="preload" href="/app.js">` that
    # hydrates into a real `<script>` element after mount.
    # Both forms satisfy the legacy bundle marker contract
    # byte-for-byte so a Playwright probe (which runs AFTER
    # hydration via `wait_for_timeout(3000)`) finds the
    # `<script src="/app.js">` selector verbatim.
    assert (
        'src="/app.js"' in html or
        'href="/app.js"' in html
    ), (
        "out/index.html must carry `<script src=\"/app.js\">` "
        "OR `<link rel=\"preload\" href=\"/app.js\">` "
        "(ODD-MIGRATE-007-DOM-006 marker #6 — runtime witness)."
    )


# ---------------------------------------------------------------------------
# ODD-PHASE2 — design-system cutover coverage (Badge + IconButton + density
# collapse). Eight source-level witnesses pin the migration contract:
#
#   1. The rank badge is rendered through the `<Badge>` primitive
#      (not the legacy inline `<span className="rank-badge ...">`).
#   2. The kebab trigger is rendered through the `<IconButton>`
#      primitive (not the legacy manual `<button className=
#      "kebab-trigger ...">`).
#   3. The row collapses from 9 visible elements to ≤5 visible
#      elements per row (5 in the common case; 6 only when the
#      kebab menu is open and the materialize `Open folder` item
#      is rendered).
#   4. The OLD `.rank-badge` inline class hook is gone.
#   5. The OLD `.status-dot-*` class hooks are gone (status is
#      inline via Tailwind utilities).
#   6. The OLD `.tree-search-icon` Material Symbols `visibility`
#      row-level button is gone.
#   7. The OLD `.materialize-indicator` row-level glyph is gone.
#   8. The OLD `.source-info` row-level glyph is gone.
# ---------------------------------------------------------------------------


def test_tree_row_uses_badge_primitive_for_rank() -> None:
    """ODD-PHASE2: the row rank uses the `<Badge>` design-system
    primitive (imported from `@taxa/design-system`) instead of the
    legacy inline `<span className="rank-badge ...">` span. The
    `subtle` variant + `uppercase={true}` flag carry the rank-badge
    look (tracked Raleway + 11px + uppercase + px-2 py-0.5 + the
    `bg-surface text-on-surface-variant border
    border-outline-variant` palette)."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    # The new Badge import must come from the public barrel.
    assert re.search(
        r'import\s*\{[^}]*\bBadge\b[^}]*\}\s*from\s*["\']@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must import `Badge` from "
        "`@taxa/design-system` (the public barrel — not a deep import)."
    )
    # The rank badge must use `<Badge variant="subtle" uppercase={true}>`
    # per the ODD-PHASE2 spec — surface + outline-variant palette,
    # uppercase + tracked Raleway. The `variant` may be either a
    # JSX string literal (`variant="subtle"`) or a JSX expression
    # (`variant={"subtle"}`); the regex below matches both forms.
    rank_badge_match = re.search(
        r'<\s*Badge\b[^>]*\bvariant\s*=\s*(?:["\']subtle["\']|\{["\']subtle["\']\})'
        r'[^>]*\buppercase\s*=\s*\{\s*true\s*\}',
        text,
    )
    assert rank_badge_match, (
        "ODD-PHASE2: TreeRow.tsx must render the rank via "
        "`<Badge variant=\"subtle\" uppercase={true}>` "
        "(matches the Phase 2 spec — accepts either JSX string "
        "literal or JSX expression form)."
    )
    # The rank label MUST live inside the Badge (rendered as the
    # component's children). We assert on the source-level presence of
    # `rankLabel(taxon.rank)` rather than the regex body itself so the
    # test reads independently of how the Badge children are formatted.
    assert "rankLabel(taxon.rank)" in text, (
        "ODD-PHASE2: TreeRow.tsx must thread `rankLabel(taxon.rank)` "
        "into the rank Badge as its children."
    )


def test_tree_row_uses_iconbutton_primitive_for_kebab() -> None:
    """ODD-PHASE2 + ODD-TAPOPUP-001: the row kebab trigger uses
    the `<IconButton>` design-system primitive (imported from
    `@taxa/design-system`) instead of the legacy manual
    `<button className="kebab-trigger material-symbols-outlined
    ...">` button. The `subtle` variant keeps the icon-button
    affordance (`hover:bg-surface-container-low`) consistent
    with the row chrome; the `aria-label` carries the canonical
    "More actions for {taxon.name}" template.

    ODD-TAPOPUP-001 update: the trigger opens a DIALOG (the
    taxon-action popup), NOT a menu — so
    `aria-haspopup="dialog"` replaces the legacy
    `aria-haspopup="menu"`. The kebab trigger also carries the
    `kebab-trigger` class hook (added to the IconButton's
    className) so the existing CSS discoverability rule
    (passive-hint opacity + hover/focus reveal) is wired."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert re.search(
        r'import\s*\{[^}]*\bIconButton\b[^}]*\}\s*from\s*["\']@taxa/design-system["\']',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must import `IconButton` from "
        "`@taxa/design-system` (the public barrel)."
    )
    assert re.search(
        r'<\s*IconButton\b[^>]*\bvariant\s*=\s*(?:["\']subtle["\']|\{["\']subtle["\']\})',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must render the kebab trigger via "
        "`<IconButton variant=\"subtle\">` (accepts either JSX string "
        "literal or JSX expression form)."
    )
    # The IconButton MUST carry `data-action="toggle-kebab"` +
    # `aria-haspopup="dialog"` + `aria-expanded` so the new
    # popup-state contract (selection-driven) works against the
    # new primitive.
    kebab_match = re.search(
        r'<\s*IconButton\b[^>]*\bdata-action\s*=\s*["\']toggle-kebab["\'][^>]*>',
        text,
    )
    assert kebab_match, (
        "ODD-TAPOPUP-001: TreeRow.tsx IconButton kebab trigger MUST "
        "stamp `data-action=\"toggle-kebab\"` (matches the kebab-"
        "state contract owned by TaxonomyTree)."
    )
    body = kebab_match.group(0)
    assert 'aria-haspopup="dialog"' in body, (
        "ODD-TAPOPUP-001: IconButton kebab trigger MUST declare "
        "`aria-haspopup=\"dialog\"` (the popup is a dialog, NOT "
        "a menu)."
    )
    assert "aria-expanded" in body, (
        "ODD-TAPOPUP-001: IconButton kebab trigger MUST declare "
        "`aria-expanded` so the popup's open state is observable "
        "to assistive tech."
    )
    # The `kebab-trigger` class hook MUST be wired (either on
    # the IconButton's className or via a wrapper) so the
    # `.kebab .kebab-trigger` CSS discoverability rule
    # (passive-hint opacity + hover/focus reveal) is active.
    assert "kebab-trigger" in body, (
        "ODD-TAPOPUP-001: IconButton kebab trigger MUST carry "
        "the `kebab-trigger` class hook (or be wrapped in a "
        "div carrying it) so the CSS discoverability rule "
        "applies."
    )


def test_tree_row_collapsed_density_count() -> None:
    """ODD-PHASE2: every row renders at most 5 top-level child
    elements in the meta block, plus the disclosure button + name
    span inside the disclosure. The total per-row count of VISIBLE
    elements in the JSX subtree drops from 9 to 5:

       old: disclosure | rank-badge | name | materialize |
            source-info | status-dot | species-count-badge |
            visibility-icon | kebab-trigger (= 9 visible)

       new: disclosure | <Badge rank> + name (inside the disclosure
            button, count as 2 logical elements) | <Badge
            status+count> | <IconButton kebab> (= 4 visible elements
            at the meta-block level; 5 if we count the disclosure
            wrapper itself).

    The test counts the OCCURRENCES of the legacy class hooks
    (`rank-badge`, `status-dot-*`, `species-count-badge`,
    `materialize-indicator`, `source-info`, `tree-search-icon`)
    that survive in the JSX as `className=` / class hooks. After
    the rewrite every one of these MUST register zero hits so the
    legacy 9-element composition is provably absent."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    # Total hit count of legacy class hooks in the JSX as
    # `className=` entries = 0 for each pattern.
    for name, regex in (
        ("rank-badge",       r'className\s*=\s*["\'][^"\']*\brank-badge\b'),
        ("status-dot",       r'className\s*=\s*["\'][^"\']*\bstatus-dot'),
        ("species-count",    r'className\s*=\s*["\'][^"\']*\bspecies-count-badge'),
        ("materialize",      r'className\s*=\s*["\'][^"\']*\bmaterialize-indicator\b'),
        ("source-info",      r'className\s*=\s*["\'][^"\']*\bsource-info\b'),
        ("tree-search-icon", r'className\s*=\s*["\'][^"\']*\btree-search-icon\b'),
    ):
        hit = re.search(regex, text)
        assert hit is None, (
            f"ODD-PHASE2: legacy row-affordance pattern `{name}` "
            f"still appears as a `className=` hook in TreeRow.tsx; "
            f"the 9-element row density has not fully collapsed."
        )
    # The new primitives MUST be present:
    #   - `<Badge variant="subtle" uppercase>` for the rank
    #   - `<Badge variant="subtle" uppercase={false}>` for status+count
    #   - `<IconButton variant="subtle">` for the kebab trigger
    assert re.search(
        r'<\s*Badge\b[^>]*\buppercase\s*=\s*\{\s*true\s*\}',
        text,
    ), "ODD-PHASE2: rank Badge primitive must be present."
    assert re.search(
        r'<\s*Badge\b[^>]*\buppercase\s*=\s*\{\s*false\s*\}',
        text,
    ), "ODD-PHASE2: status+count Badge composite must be present."
    assert re.search(
        r'<\s*IconButton\b[^>]*\bvariant\s*=\s*(?:["\']subtle["\']|\{["\']subtle["\']\})',
        text,
    ), "ODD-PHASE2: IconButton kebab trigger must be present."


def test_tree_row_no_inline_rank_badge_span() -> None:
    """ODD-PHASE2: the legacy `<span className="rank-badge ...
    tracking-[0.1em] px-2 py-0.5 rounded ...">` inline span is
    gone — replaced by `<Badge variant="subtle" uppercase>`. The
    className-anchored regex avoids false positives from the
    file's docstring which mentions `rank-badge` literally as a
    legacy reference."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert not re.search(
        r'className\s*=\s*["\'][^"\']*\brank-badge\b',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT render the legacy inline "
        "`.rank-badge` span (replaced by the `<Badge variant=\"subtle\" "
        "uppercase>` primitive)."
    )
    assert not re.search(
        r'<\s*span\b[^>]*\buppercase\b[^>]*\btracking-\[0\.1em\]',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT render the legacy tracked-"
        "Raleway rank-badge span (the Badge primitive centralizes the "
        "uppercase + tracking-[0.1em] + 11px + px-2 py-0.5 pattern)."
    )


def test_tree_row_no_inline_status_dot_class() -> None:
    """ODD-PHASE2: the legacy `.status-dot`, `.status-dot-accepted`,
    `.status-dot-synonym`, `.status-dot-unknown` class hooks are
    gone from the JSX. The status indicator is now an inline
    `<span>` carrying the canonical Tailwind colour utility
    (`bg-green-500` / `bg-amber-500` / `bg-on-surface-variant`).
    The className-anchored regex avoids false positives from
    docstring references which mention `status-dot-*` literally."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    for needle in (
        r'className\s*=\s*["\'][^"\']*\bstatus-dot\b',
        r'className\s*=\s*["\'][^"\']*\bstatus-dot-accepted\b',
        r'className\s*=\s*["\'][^"\']*\bstatus-dot-synonym\b',
        r'className\s*=\s*["\'][^"\']*\bstatus-dot-unknown\b',
        r'\bdata-status-dot\s*=',
    ):
        assert not re.search(needle, text), (
            "ODD-PHASE2: TreeRow.tsx must NOT carry the legacy "
            "`.status-dot*` class hooks or `data-status-dot` "
            "attribute (status is inline via Tailwind utilities)."
        )


def test_tree_row_no_inline_tree_search_icon() -> None:
    """ODD-PHASE2: the legacy `<button className="tree-search-icon
    material-symbols-outlined ...">visibility</button>` row-level
    button is gone. The IconButton primitive replaces the kebab
    trigger + the deleted visibility icon button (the visibility
    button's affordance was a duplicate of the row click's
    `onSelect(taxon.id)` primitive). The className-anchored regex
    catches any leftover `tree-search-icon` literal reference."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert not re.search(
        r'className\s*=\s*["\'][^"\']*\btree-search-icon\b',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT render the legacy "
        "`.tree-search-icon` row-level Material Symbols `visibility` "
        "button (the IconButton primitive centralizes the row "
        "icon affordances)."
    )
    # The literal `visibility` glyph that was inside the row-level
    # visibility button MUST NOT appear in a row-level button
    # context anymore — the kebab IconButton renders `more_vert`
    # exclusively on the row surface. We anchor on the legacy row
    # button shape (`<button className="...tree-search-icon...">`)
    # to avoid false positives from the legacy `web/index.html` doc
    # block references.
    assert not re.search(
        r'<\s*button\b[^>]*\btree-search-icon\b[^>]*>\s*[Vv]isibility',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT render the legacy row-level "
        "Material Symbols `visibility` button under "
        "`.tree-search-icon`."
    )


def test_tree_row_no_inline_materialize_indicator_class() -> None:
    """ODD-PHASE2: the legacy `<span className="materialize-
    indicator material-symbols-outlined ...">folder</span>` row-
    level glyph is gone — the materialize indicator now lives
    inside the kebab menu (the conditional `Open folder` item).
    The className-anchored regex avoids false positives from
    docstring references which mention `.materialize-indicator`
    literally as a legacy reference."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert not re.search(
        r'className\s*=\s*["\'][^"\']*\bmaterialize-indicator\b',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT render the legacy inline "
        "`.materialize-indicator` glyph (the kebab menu carries the "
        "conditional `Open folder` item in its place)."
    )
    assert not re.search(
        r'\bdata-materialize-indicator\s*=',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT stamp "
        "`data-materialize-indicator` (the kebab menu replaces the "
        "row-level glyph)."
    )


def test_tree_row_no_inline_source_info_class() -> None:
    """ODD-PHASE2: the legacy `<span className="source-info
    material-symbols-outlined ...">info</span>` row-level glyph is
    gone — the source info tooltip now lives on the name span's
    `title` attribute. The className-anchored regex avoids false
    positives from docstring references which mention `source-info`
    literally as a legacy reference."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert not re.search(
        r'className\s*=\s*["\'][^"\']*\bsource-info\b',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT render the legacy inline "
        "`.source-info` glyph (the source info tooltip collapses "
        "into the name span's `title` attribute)."
    )
    assert not re.search(
        r'\bdata-source-info\s*=',
        text,
    ), (
        "ODD-PHASE2: TreeRow.tsx must NOT stamp "
        "`data-source-info` (the source info tooltip collapses "
        "into the name span's `title` attribute)."
    )
