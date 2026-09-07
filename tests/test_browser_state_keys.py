"""
Browser-state key/store/barrel contract tests (PR 4a).

Static guard for the typed literals, the four-read / four-write
localStorage contract, and the module-boundary hygiene Phase 4a ships:

    src/modules/browser-state/domain/keys.ts          — typed literals + defaults + guards
    src/modules/browser-state/infrastructure/safe-storage.ts — safe platform-storage accessor
    src/modules/browser-state/infrastructure/store.ts        — 4 reads + 4 writes + subscribe + reset
    src/modules/browser-state/index.ts                — public barrel (typed APIs only)

References:
    openspec/changes/migrate-nextjs-tailwind4/tasks.md     §Phase 4 (4.1, 4.2)
    openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md  Rule 4
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_ROOT = REPO_ROOT / "src" / "modules" / "browser-state"
DOMAIN_DIR = MODULE_ROOT / "domain"
SRC_ROOT = REPO_ROOT / "src"
KEYS_FILE = DOMAIN_DIR / "keys.ts"
SAFE_STORAGE_FILE = MODULE_ROOT / "infrastructure" / "safe-storage.ts"
STORE_FILE = MODULE_ROOT / "infrastructure" / "store.ts"
BARREL = MODULE_ROOT / "index.ts"


# Pinned five-key contract (PR 5c.1a extends PR 4a's four-key contract by
# adding the typed boolean `versionBannerDismissed`). The full literal string
# is part of the public contract: a regression that drifts the namespace
# (e.g. `taxa.theme` instead of `taxa.settings.theme`) silently misroutes
# writes.
EXPECTED_KEYS: tuple[tuple[str, str], ...] = (
    ("theme",                  "taxa.settings.theme"),
    ("treeSource",             "taxa.tree.source"),
    ("lastTaxonId",            "taxa.tree.lastTaxonId"),
    ("kebabOpenId",            "taxa.tree.kebabOpenId"),
    ("versionBannerDismissed", "taxa.settings.versionBannerDismissed"),
)


# Comment stripping — mirrors tests/test_domain_purity.py. Preserves
# line numbers so diagnostics stay aligned with the original source.
_BLOCK_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/")
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _blank_match(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def _strip_ts_comments(text: str) -> str:
    text = _BLOCK_COMMENT_RE.sub(_blank_match, text)
    text = _LINE_COMMENT_RE.sub(_blank_match, text)
    return text


def _read(path: Path) -> str:
    return path.read_text()


def _read_stripped(path: Path) -> str:
    return _strip_ts_comments(_read(path))


def _ts_files(root: Path) -> list[Path]:
    """Recursive `.ts` files anywhere under `root`, excluding `.gitkeep`
    and any file named `index.ts` (barrels are JSDoc-only)."""
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.rglob("*.ts")
        if p.is_file() and p.name not in {".gitkeep", "index.ts"}
    )


def _callsites(root: Path, token: str) -> list[tuple[Path, int]]:
    """(path, line_no) for every `token(` in the comment-stripped view of
    every `.ts` file under `root`."""
    results: list[tuple[Path, int]] = []
    for path in _ts_files(root):
        cleaned = _read_stripped(path)
        for lineno, line in enumerate(cleaned.splitlines(), start=1):
            if token in line:
                results.append((path, lineno))
    return results


# ===========================================================================
# Layer presence — PR 4a ships all four files together.
# ===========================================================================
@pytest.mark.parametrize("path", [KEYS_FILE, SAFE_STORAGE_FILE, STORE_FILE])
def test_pr4a_layer_files_exist(path: Path):
    assert path.is_file(), (
        f"missing PR 4a file: {path.relative_to(REPO_ROOT).as_posix()}"
    )


# ===========================================================================
# Five-key typed literals + defaults (PR 5c.1a extends PR 4a).
# ===========================================================================
def test_keys_object_declares_exactly_five_pinned_literals():
    """`BROWSER_STATE_KEYS` MUST have exactly the five pinned entries
    (PR 5c.1a adds `versionBannerDismissed`) with the exact literal
    strings — a typo or rename here is silently data-corrupting on
    existing localStorage data."""
    text = _read(KEYS_FILE)
    block = re.search(r"BROWSER_STATE_KEYS\s*=\s*\{([^}]*)\}", text, flags=re.DOTALL)
    assert block, "BROWSER_STATE_KEYS object literal not found"
    quoted = re.findall(r'"([^"]+)"', block.group(1))
    expected = [literal for _, literal in EXPECTED_KEYS]
    assert len(quoted) == 5, f"expected 5 literals, got {quoted}"
    assert sorted(quoted) == sorted(expected), (
        f"BROWSER_STATE_KEYS literals drifted: expected {expected}, got {quoted}"
    )


def test_keys_short_names_match_pinned_mapping():
    """LHS short names must match the pinned four."""
    text = _read(KEYS_FILE)
    block = re.search(r"BROWSER_STATE_KEYS\s*=\s*\{([^}]*)\}", text, flags=re.DOTALL)
    assert block, "BROWSER_STATE_KEYS object literal not found"
    short_names = re.findall(r"^\s*([A-Za-z_]\w*)\s*:", block.group(1), flags=re.MULTILINE)
    expected = [name for name, _ in EXPECTED_KEYS]
    assert sorted(short_names) == sorted(expected), (
        f"short names drifted: expected {expected}, got {short_names}"
    )


def test_defaults_cover_every_key():
    """`BROWSER_STATE_DEFAULTS` MUST declare a default for every pinned key."""
    text = _read(KEYS_FILE)
    block = re.search(
        r"BROWSER_STATE_DEFAULTS\b[^=]*=\s*\{([^}]+)\}", text, flags=re.DOTALL
    )
    assert block, "BROWSER_STATE_DEFAULTS object literal not found"
    body = block.group(1)
    for short_name, _ in EXPECTED_KEYS:
        assert re.search(rf"\b{re.escape(short_name)}\s*:", body), (
            f"BROWSER_STATE_DEFAULTS must declare a default for '{short_name}'"
        )


def test_barrel_reexports_keys_and_defaults():
    text = _read(BARREL)
    assert "BROWSER_STATE_KEYS" in text, "barrel must re-export BROWSER_STATE_KEYS"
    assert "BROWSER_STATE_DEFAULTS" in text, (
        "barrel must re-export BROWSER_STATE_DEFAULTS"
    )


# ===========================================================================
# 5 + 5 call-site contract (PR 5c.1a extends PR 4a's 4 + 4 contract).
# ===========================================================================
def test_exactly_five_getitem_callsites_under_src():
    """Tasks.md §Phase 4.1 (extended by PR 5c.1a): the store is the
    ONLY localStorage layer, with exactly five `getItem(` callsites,
    one per pinned key, all in `infrastructure/store.ts`. Splitting
    across files would break the 5 + 5 invariant."""
    occurrences = _callsites(SRC_ROOT, "getItem(")
    assert len(occurrences) == 5, (
        f"expected exactly 5 getItem( callsites under src/; "
        f"found {len(occurrences)}: "
        f"{[(p.relative_to(REPO_ROOT).as_posix(), ln) for p, ln in occurrences]}"
    )
    for path, _ in occurrences:
        rel = path.relative_to(REPO_ROOT).as_posix()
        assert rel.endswith("browser-state/infrastructure/store.ts"), (
            f"getItem( callsite must live in store.ts; found in {rel}"
        )
    store_clean = _read_stripped(STORE_FILE)
    for short_name, _ in EXPECTED_KEYS:
        assert f"BROWSER_STATE_KEYS.{short_name}" in store_clean, (
            f"store.ts must reference BROWSER_STATE_KEYS.{short_name} in a read"
        )


def test_exactly_five_setitem_callsites_under_src():
    """Mirror of the getItem contract — same 5 + 5 shape, same single-file
    location invariant."""
    occurrences = _callsites(SRC_ROOT, "setItem(")
    assert len(occurrences) == 5, (
        f"expected exactly 5 setItem( callsites under src/; "
        f"found {len(occurrences)}: "
        f"{[(p.relative_to(REPO_ROOT).as_posix(), ln) for p, ln in occurrences]}"
    )
    for path, _ in occurrences:
        rel = path.relative_to(REPO_ROOT).as_posix()
        assert rel.endswith("browser-state/infrastructure/store.ts"), (
            f"setItem( callsite must live in store.ts; found in {rel}"
        )


# ===========================================================================
# Safe-storage purity — no direct localStorage call sites.
# ===========================================================================
def test_safe_storage_has_no_localstorage_callsites():
    """safe-storage.ts provides platform detection + JSON try/catch
    helpers but MUST NOT contain `getItem(` or `setItem(` call sites.
    Splitting the 4 + 4 count across two files would let either side
    silently drift past the contract; the call sites are concentrated
    in store.ts so the test owns one place."""
    cleaned = _read_stripped(SAFE_STORAGE_FILE)
    for token in ("getItem(", "setItem("):
        assert token not in cleaned, (
            f"safe-storage.ts must not call {token!r} directly; "
            f"that call site belongs to store.ts so the 4+4 contract "
            f"is enforceable from a single file."
        )


# ===========================================================================
# Domain purity (spec.md rule 4).
# ===========================================================================
DOMAIN_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "react", "next", "nextjs", "fastapi", "starlette", "pydantic",
    "fetch(",
    "localStorage", "document.", "window.",
    "process.",
)


@pytest.mark.parametrize("token", DOMAIN_FORBIDDEN_TOKENS)
def test_domain_has_no_forbidden_token(token: str):
    """spec.md rule 4: the browser-state domain layer stays free of
    React, I/O, browser, HTTP, and process tokens. Mirrors
    `tests/test_domain_purity.py` for the browser-state capability."""
    files = _ts_files(DOMAIN_DIR)
    if not files:
        pytest.skip("domain directory has no .ts files yet")
    for path in files:
        cleaned = _read_stripped(path)
        for lineno, line in enumerate(cleaned.splitlines(), start=1):
            assert token not in line, (
                f"{path.relative_to(REPO_ROOT).as_posix()}: forbidden token "
                f"{token!r} in domain layer at line {lineno}: {line!r}. "
                f"spec.md rule 4 forbids browser/I/O/framework tokens here."
            )


# ===========================================================================
# PR 5c.1a typed-foundation deltas — TreeSource extends to `freshwater` and
# the boolean `versionBannerDismissed` defaults to `false`.
# ===========================================================================
def test_tree_source_validator_accepts_freshwater():
    """PR 5c.1a extends `TreeSource` to `col | worms | freshwater`. The
    type guard in `domain/keys.ts` MUST accept `freshwater` so the React
    layer (PR 5c.1b) can persist the user's choice. Source-level check
    keeps the test hermetic — no need to import the TS module."""
    text = _read(KEYS_FILE)
    assert '"freshwater"' in text, (
        "keys.ts must extend the TreeSource union literal with 'freshwater'; "
        "PR 5c.1b's tree-source UI requires the validator to accept it."
    )
    # Validator body MUST include the new literal alongside `col` / `worms`.
    m = re.search(
        r"isValidTreeSource\s*\([^)]*\)\s*:\s*value\s+is\s+TreeSource\s*\{([\s\S]*?)\}",
        text,
    )
    validator_body = m.group(1) if m else ""
    assert "freshwater" in validator_body, (
        "isValidTreeSource must return true for the 'freshwater' literal; "
        "extending TreeSource without updating the validator is data-corrupting."
    )


def test_version_banner_dismissed_defaults_to_false():
    """PR 5c.1a adds the boolean `versionBannerDismissed` key. The default
    MUST be `false` so first-paint users see the banner (PR 5c.1b renders
    the UI). The literal name MUST be typed as a boolean field on the
    value map."""
    text = _read(KEYS_FILE)
    # Defaults row — must declare the boolean short name with `false`.
    defaults_block = re.search(
        r"BROWSER_STATE_DEFAULTS\b[^=]*=\s*\{([^}]+)\}", text, flags=re.DOTALL
    )
    assert defaults_block, "BROWSER_STATE_DEFAULTS object literal not found"
    body = defaults_block.group(1)
    m = re.search(
        r"\bversionBannerDismissed\s*:\s*([^,\n]+)", body
    )
    assert m, (
        "BROWSER_STATE_DEFAULTS must declare `versionBannerDismissed: false`"
    )
    assert m.group(1).strip() == "false", (
        f"versionBannerDismissed default must be literal `false`, got "
        f"{m.group(1).strip()!r}"
    )
    # Value map MUST type the field as boolean. The interface body sits
    # directly under `interface BrowserStateValueMap { ... }`; we anchor
    # on the `interface` keyword so we don't accidentally capture the
    # BROWSER_STATE_DEFAULTS annotation that ALSO carries the same name.
    value_map_block = re.search(
        r"interface\s+BrowserStateValueMap\s*\{([^}]+)\}",
        text,
        flags=re.DOTALL,
    )
    assert value_map_block, "BrowserStateValueMap interface literal not found"
    m = re.search(
        r"\bversionBannerDismissed\s*:\s*([^;\n]+)", value_map_block.group(1)
    )
    assert m, "BrowserStateValueMap must declare `versionBannerDismissed`"
    assert "boolean" in m.group(1), (
        f"versionBannerDismissed must be typed as boolean, got {m.group(1)!r}"
    )


# ===========================================================================
# Public barrel hygiene — typed APIs only, never raw localStorage.
# ===========================================================================
def test_barrel_does_not_mention_localstorage():
    """Barrel MUST NOT mention `localStorage` — the safe accessor is
    private to infrastructure/safe-storage.ts. A leak would let a
    cross-module consumer bypass the safe-storage wrapper."""
    text = _read(BARREL)
    assert "localStorage" not in text, (
        "index.ts must not mention `localStorage`; the safe accessor is "
        "private to infrastructure/safe-storage.ts."
    )


def test_barrel_does_not_export_getitem_or_setitem():
    """Barrel MUST NOT export anything named `getItem` / `setItem`."""
    cleaned = _read_stripped(BARREL)
    forbidden = re.findall(r"export\b[^;\n]*\b(getItem|setItem)\b", cleaned)
    assert not forbidden, (
        f"barrel must not export getItem/setItem; found: {forbidden!r}"
    )


# ===========================================================================
# Cross-capability hygiene — the panel-width key is research-owned.
# ===========================================================================
def test_fex_tree_width_is_not_a_browser_state_key():
    """`taxa.fex.treeWidth` is owned by the `research` module. Phase 4a
    MUST NOT adopt it into BROWSER_STATE_KEYS / BROWSER_STATE_DEFAULTS —
    doing so would couple the two capabilities across the barrel-only
    boundary and pull a research concern into browser-state."""
    keys_text = _read(KEYS_FILE)
    assert "treeWidth" not in keys_text, (
        "keys.ts must not declare a `treeWidth` key; that key is "
        "research-owned (taxa.fex.* namespace)."
    )
    assert "taxa.fex" not in keys_text, (
        "keys.ts must not use the `taxa.fex.*` namespace; that lives "
        "outside the browser-state module."
    )


# ===========================================================================
# Store surface — 5 typed getters + 5 typed setters + subscribe + reset.
# ===========================================================================
def test_store_exposes_ten_mutators_and_listener():
    """Pins the public store surface (PR 5c.1a): 5 typed getters, 5
    typed setters, a `subscribe(listener)` registration, and a `reset()`
    action. The regex matches every `camelCase(` token; we filter the
    infrastructure-internal helpers (`getBrowserStorage`, `getItem`,
`setItem`) so the assertion reflects the public surface, not the
    import list."""
    cleaned = _read_stripped(STORE_FILE)
    INFRA_HELPERS = {"getBrowserStorage(", "getItem(", "setItem("}
    raw_getters = sorted(set(re.findall(r"\bget[A-Z]\w*\s*\(", cleaned)))
    raw_setters = sorted(set(re.findall(r"\bset[A-Z]\w*\s*\(", cleaned)))
    getters = [g for g in raw_getters if g not in INFRA_HELPERS]
    setters = [s for s in raw_setters if s not in INFRA_HELPERS]
    expected_getters = sorted(
        f"get{name[0].upper()}{name[1:]}(" for name, _ in EXPECTED_KEYS
    )
    expected_setters = sorted(
        f"set{name[0].upper()}{name[1:]}(" for name, _ in EXPECTED_KEYS
    )
    assert getters == expected_getters, (
        f"store.ts getter surface drifted: expected {expected_getters}, got {getters}"
    )
    assert setters == expected_setters, (
        f"store.ts setter surface drifted: expected {expected_setters}, got {setters}"
    )
    assert "subscribe" in cleaned, "store.ts must define subscribe(listener)"
    assert "reset" in cleaned, "store.ts must define reset()"


# ===========================================================================
# PR 5c.1b-A — React tree-source UI + nav/breadcrumb identifiers + single-store
# context wiring. Source-contract tests only (no DOM, no JSDOM); keep the
# suite hermetic and consistent with the prior tests in this file. The
# production slices live in:
#     src/modules/app-shell/infrastructure/page-chrome.tsx
#     src/modules/app-shell/presentation/AppShell.tsx
#     src/modules/app-shell/presentation/browser-state-store-context.ts
#     src/modules/app-shell/index.ts
#     src/app/page.tsx
#     src/modules/taxonomy/presentation/Breadcrumb.tsx
# The legacy `#tree-source-toggle` / `#nav-*` / `#breadcrumb` DOM contract
# is preserved by stamping ids / data-tree-source on the existing
# React elements — NOT by restoring the legacy `<header>` /
# `<button>` / `<nav>` shape.
# ===========================================================================
APP_SHELL_DIR = REPO_ROOT / "src" / "modules" / "app-shell"
APP_SHELL_PRESENTATION = APP_SHELL_DIR / "presentation"
PAGE_CHROME_FILE = APP_SHELL_DIR / "infrastructure" / "page-chrome.tsx"
APP_SHELL_FILE = APP_SHELL_PRESENTATION / "AppShell.tsx"
APP_SHELL_BARREL = APP_SHELL_DIR / "index.ts"
PAGE_FILE = REPO_ROOT / "src" / "app" / "page.tsx"
BREADCRUMB_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "Breadcrumb.tsx"


def _app_shell_ts_files() -> list[Path]:
    """All `.tsx` / `.ts` files in the app-shell module, excluding the
    public barrel (JSDoc-only)."""
    if not APP_SHELL_DIR.is_dir():
        return []
    return sorted(
        p for p in APP_SHELL_DIR.rglob("*.ts*")
        if p.is_file() and p.name not in {".gitkeep", "index.ts"}
    )


def test_tree_source_toggle_renders_with_three_buttons():
        """PR 5c.1b-A: PageChrome MUST render the tree-source control
        with id `tree-source-toggle` and three buttons whose
        `data-tree-source` attributes are the three pinned literals
        (`col`, `worms`, `freshwater`) with `aria-pressed`."""
        text = _read_stripped(PAGE_CHROME_FILE)
        assert re.search(r'id\s*=\s*["{]tree-source-toggle["}]', text), (
            "page-chrome.tsx must render the tree-source toggle host with "
            "id=\"tree-source-toggle\" (legacy DOM contract preserved)."
        )
        for literal in ("col", "worms", "freshwater"):
            assert (
                f'data-tree-source="{literal}"' in text
                or ("data-tree-source={" in text
                    and f'"{literal}"' in text
                    and ("TREE_SOURCES" in text or "treeSource" in text))
            ), (
                f"page-chrome.tsx must render a button with "
                f"data-tree-source=\"{literal}\" inside #tree-source-toggle"
            )
        literal_count = text.count('data-tree-source="')
        expr_count = text.count("data-tree-source={")
        assert literal_count + expr_count == 3 or expr_count == 1, (
            f"page-chrome.tsx must render three tree-source buttons; "
            f"found literal={literal_count}, expression={expr_count}"
        )
        aria_literal = text.count('aria-pressed="')
        aria_expr = text.count("aria-pressed={")
        assert aria_literal >= 3 or aria_expr == 1, (
            f"page-chrome.tsx must stamp aria-pressed on every "
            f"data-tree-source button; found literal={aria_literal}, "
            f"expression={aria_expr}"
        )


def test_tree_source_toggle_persists_via_set_tree_source():
    """PR 5c.1b-A: toggle click MUST call the typed store's
    `setTreeSource(next)`; MUST NOT call `localStorage` directly."""
    text = _read_stripped(PAGE_CHROME_FILE)
    assert "setTreeSource" in text, (
        "page-chrome.tsx must call setTreeSource(next) on click so "
        "the typed store persists the choice (5 + 5 contract)."
    )
    assert "localStorage" not in text, (
        "page-chrome.tsx must not mention localStorage; the typed "
        "store is the only localStorage writer."
    )
    assert "TREE_SOURCES" in text, (
        "page-chrome.tsx must declare a TREE_SOURCES mapping that "
        "feeds the setTreeSource click handler"
    )


def test_app_shell_exposes_single_store_via_context():
    """PR 5c.1b-A: AppShell MUST construct the typed store exactly
    once AND MUST publish that single instance via a React context
    so page.tsx can read without constructing a second store."""
    callsites = []
    for path in _app_shell_ts_files():
        cleaned = _read_stripped(path)
        for lineno, line in enumerate(cleaned.splitlines(), start=1):
            if "createBrowserStateStore(" in line:
                callsites.append((path, lineno))
    assert len(callsites) == 1, (
        f"app-shell must construct the typed store exactly once; "
        f"found {len(callsites)} callsites"
    )
    assert callsites[0][0] == APP_SHELL_FILE, (
        f"createBrowserStateStore( must be called from AppShell.tsx; "
        f"found in {callsites[0][0].relative_to(REPO_ROOT).as_posix()}"
    )
    app_shell_text = _read_stripped(APP_SHELL_FILE)
    assert ".Provider" in app_shell_text, (
        "AppShell.tsx must wrap its subtree with the typed store's "
        "React context Provider so descendants see the single instance"
    )
    assert "createContext" in app_shell_text or "Context" in app_shell_text, (
        "AppShell.tsx must reference a React Context for the typed store"
    )
    barrel = _read_stripped(APP_SHELL_BARREL)
    assert "useBrowserStateStore" in barrel, (
        "app-shell barrel must re-export the useBrowserStateStore() "
        "hook so consumers read via the public boundary"
    )


def test_page_consumes_tree_source_via_app_shell_context():
    """PR 5c.1b-A: page.tsx MUST consume tree source from the
    AppShell-exposed store via the barrel; MUST NOT hard-code
    `source: "col"`; MUST subscribe via useSyncExternalStore."""
    text = _read_stripped(PAGE_FILE)
    assert 'source: "col"' not in text, (
        "src/app/page.tsx must not hard-code source: \"col\"; "
        "PR 5c.1b-A requires the source to flow from the AppShell-"
        "exposed store so user selection persists via setTreeSource."
    )
    assert "@taxa/app-shell" in text, (
        "src/app/page.tsx must import useBrowserStateStore from "
        "@taxa/app-shell (the public barrel) per spec.md rule 5."
    )
    assert "useBrowserStateStore" in text, (
        "src/app/page.tsx must call the useBrowserStateStore() hook "
        "to subscribe to the tree-source value"
    )
    assert "useSyncExternalStore" in text, (
        "src/app/page.tsx must subscribe via useSyncExternalStore "
        "so a setTreeSource click re-fetches the taxonomy tree"
    )
    assert "createBrowserStateStore" not in text, (
        "src/app/page.tsx must not construct a second store; "
        "the single store lives in AppShell.tsx."
    )


def test_nav_button_ids_match_legacy_contract():
    """PR 5c.1b-A: the three primary nav buttons MUST carry the
    legacy-compatible React ids `nav-browser`, `nav-classification`,
    `nav-settings`. Accept both JSX literal and JSX expression
    attribute syntaxes."""
    text = _read_stripped(PAGE_CHROME_FILE)
    literal_ok = all(f'id="nav-{p}"' in text for p in
                     ("browser", "classification", "settings"))
    expr_ok = (
        "id={`nav-${" in text
        and "NAV_TABS" in text
        and all(f'"{p}"' in text for p in
                ("browser", "classification", "settings"))
    )
    assert literal_ok or expr_ok, (
        "page-chrome.tsx must stamp id=\"nav-browser\", "
        "id=\"nav-classification\", id=\"nav-settings\" on the existing "
        "nav buttons (legacy DOM contract preserved)"
    )


def test_breadcrumb_renders_with_id_breadcrumb():
    """PR 5c.1b-A: the taxonomy Breadcrumb MUST stamp
    `id="breadcrumb"` on its `<nav>` element (both branches)."""
    text = _read_stripped(BREADCRUMB_FILE)
    assert 'id="breadcrumb"' in text, (
        "taxonomy/presentation/Breadcrumb.tsx must stamp "
        "id=\"breadcrumb\" on its <nav> element (legacy DOM "
        "contract preserved without restoring legacy architecture)"
    )
    assert text.count('id="breadcrumb"') >= 2, (
        "Breadcrumb.tsx must stamp id=\"breadcrumb\" on BOTH the "
        "empty-state and the populated-state <nav> branches"
    )

# ===========================================================================
# PR 5c.1b-B — VersionBanner render + DetailPanel close/sticky contract.
# Source-contract tests only (no DOM, no JSDOM); keep the suite hermetic.
# Production slices live in:
#     src/modules/app-shell/presentation/VersionBanner.tsx   (NEW)
#     src/modules/app-shell/infrastructure/page-chrome.tsx   (host mount)
#     src/modules/taxonomy/presentation/DetailPanel.tsx     (close/sticky)
#     src/app/globals.css                                    (sticky contract)
#
# NOTE: the `presentation/index.ts` barrel is intentionally NOT
# re-exporting `VersionBanner` in this slice — the component is
# mounted by `infrastructure/page-chrome.tsx` via a sibling-module
# import, and the public `app-shell/presentation/index.ts` barrel
# stays limited to `AppShell` + `BrowserSurface` (PR 4b + PR 5b.4
# surface). The earlier "(re-export)" annotation on the
# `presentation/index.ts` line was incorrect; corrected here so the
# production-slices list reflects the actual shipped contract.
# ===========================================================================
VERSION_BANNER_FILE = APP_SHELL_PRESENTATION / "VersionBanner.tsx"
DETAIL_PANEL_FILE = (
    REPO_ROOT / "src" / "modules" / "taxonomy"
    / "presentation" / "DetailPanel.tsx"
)
GLOBALS_CSS_FILE = REPO_ROOT / "src" / "app" / "globals.css"


def test_version_banner_preserves_legacy_dom_ids():
    """PR 5c.1b-B: VersionBanner MUST render the three legacy DOM
    ids `version-banner`, `version-banner-actual`,
    `version-banner-expected` on its visible children so legacy e2e
    + Playwright tests and the banner-host re-anchor continue to
    resolve."""
    if not VERSION_BANNER_FILE.is_file():
        pytest.skip("VersionBanner.tsx not yet authored")
    text = _read_stripped(VERSION_BANNER_FILE)
    for legacy_id in (
        '"version-banner"',
        '"version-banner-actual"',
        '"version-banner-expected"',
    ):
        assert legacy_id in text, (
            f"VersionBanner.tsx must stamp legacy DOM id {legacy_id!r}"
        )


def test_version_banner_is_mount_gated_and_fetches_health_only_after_mount():
    """PR 5c.1b-B: the /api/health fetch MUST fire only AFTER the
    `useMounted()` flag flips. SSR + initial CSR render with no
    network call so React's hydration guard never trips on a server
    that doesn't reach the API. Source-only check: the fetch lives
    inside `useEffect`, the effect early-returns when `mounted`
    is false, AND the component imports `useMounted` from
    `@taxa/browser-state`."""
    if not VERSION_BANNER_FILE.is_file():
        pytest.skip("VersionBanner.tsx not yet authored")
    text = _read_stripped(VERSION_BANNER_FILE)
    assert "useMounted" in text, (
        "VersionBanner.tsx must import and call useMounted() so the "
        "network fetch is mounted-gated (SSR-safe)"
    )
    assert "/api/health" in text, (
        "VersionBanner.tsx must fetch /api/health to read schema "
        "version fields (preserves legacy contract)"
    )
    assert re.search(r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{", text), (
        "VersionBanner.tsx must call useEffect for the health fetch"
    )
    effect_block = re.search(
        r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{([\s\S]*?)\}\s*,\s*\[",
        text,
    )
    assert effect_block, "useEffect block not parseable"
    effect_body = effect_block.group(1)
    assert "mounted" in effect_body, (
        "useEffect must reference `mounted` so the fetch is gated"
    )
    assert re.search(
        r"if\s*\(\s*!\s*mounted\s*\)\s*return", effect_body
    ), (
        "useEffect must early-return when mounted is false "
        "(`if (!mounted) return;`)"
    )


def test_version_banner_fails_closed_on_unavailable_or_malformed_health():
    """PR 5c.1b-B: VersionBanner MUST hide (return null / keep host
    hidden) on:
      - non-OK HTTP response
      - missing schema-version fields
      - non-numeric schema-version fields
      - exception during fetch
    It MUST NEVER fabricate an outdated state when health is
    unavailable."""
    if not VERSION_BANNER_FILE.is_file():
        pytest.skip("VersionBanner.tsx not yet authored")
    text = _read_stripped(VERSION_BANNER_FILE)
    assert re.search(
            r"typeof\s+\w+\s*[!=]==?\s*[\"\']number[\"\']", text
        ), (
            "VersionBanner.tsx must validate fetched payload fields "
            "with typeof number checks so malformed data fails closed"
        )
    assert ".catch(" in text, (
        "VersionBanner.tsx must attach a .catch() handler to fetch "
        "/ .json() so network errors fail closed"
    )


def test_version_banner_persists_dismiss_via_typed_store():
    """PR 5c.1b-B: the dismiss click MUST call
    `store.setVersionBannerDismissed(true)` on the SINGLE typed
    store instance (no localStorage access from the component) AND
    the visibility check MUST honour `getVersionBannerDismissed()`."""
    if not VERSION_BANNER_FILE.is_file():
        pytest.skip("VersionBanner.tsx not yet authored")
    text = _read_stripped(VERSION_BANNER_FILE)
    assert "setVersionBannerDismissed" in text, (
        "VersionBanner.tsx must call setVersionBannerDismissed(true) "
        "on the dismiss click (single-typed-store contract)"
    )
    assert "getVersionBannerDismissed" in text, (
        "VersionBanner.tsx must read getVersionBannerDismissed() to "
        "honour a previous dismissal across reloads"
    )
    assert "localStorage" not in text, (
        "VersionBanner.tsx must not touch localStorage directly; the "
        "typed store is the sole writer (5 + 5 contract intact)"
    )


def test_version_banner_does_not_construct_a_second_store():
    """PR 5c.1b-B: VersionBanner MUST NOT construct a second typed
    store. AppShell is the sole `createBrowserStateStore()` call
    site in the codebase; the banner consumes the SAME instance via
    the React Context exposed by `useBrowserStateStore`."""
    if not VERSION_BANNER_FILE.is_file():
        pytest.skip("VersionBanner.tsx not yet authored")
    text = _read_stripped(VERSION_BANNER_FILE)
    assert "createBrowserStateStore" not in text, (
        "VersionBanner.tsx must NOT call createBrowserStateStore(); "
        "AppShell owns the single instance."
    )
    assert "useBrowserStateStore" in text, (
        "VersionBanner.tsx must consume the typed store via the "
        "useBrowserStateStore() hook (AppShell-exposed context)."
    )


def test_version_banner_subscribes_to_dismissal_via_use_sync_external_store():
    """PR 5c.1b-B (corrective): VersionBanner MUST subscribe to the
    same typed store's dismissal snapshot via `useSyncExternalStore`
    (or an equivalent reactive selector) so the Dismiss click hides
    the banner IMMEDIATELY. A one-shot snapshot via plain
    `getVersionBannerDismissed()` would leave the banner visible
    after dismiss until the next external re-render; a parallel
    `createBrowserStateStore()` would silently bypass the
    AppShell-owned instance. The test pins three contracts:

      1. `useSyncExternalStore` is called inside the component
         (the standard React-19 reactive selector).
      2. The snapshot reader references
         `getVersionBannerDismissed` so a dismiss change flips the
         snapshot.
      3. The subscribe path references the SAME store the
         `useBrowserStateStore()` hook returns — `store.subscribe`
         (with a no-op fallback for the pre-mount window) — so
         notifications reach the banner.

    Source-only check: no JSDOM, no DOM, no React render."""
    if not VERSION_BANNER_FILE.is_file():
        pytest.skip("VersionBanner.tsx not yet authored")
    text = _read_stripped(VERSION_BANNER_FILE)
    # (1) The hook must be invoked.
    assert re.search(r"\buseSyncExternalStore\s*\(", text), (
        "VersionBanner.tsx must call useSyncExternalStore to "
        "subscribe to the typed store's dismissal snapshot so the "
        "Dismiss click hides the banner immediately (no parallel "
        "store, no one-shot snapshot)."
    )
    # (2) The snapshot reader must reference
    # `getVersionBannerDismissed` (either via `store.getVersionBannerDismissed()`
    # or `getVersionBannerDismissed()` directly inside the
    # `useSyncExternalStore` second argument).
    use_sync_block = re.search(
        r"useSyncExternalStore\s*\(\s*([\s\S]*?)\)\s*[;,\n]", text
    )
    assert use_sync_block, (
        "useSyncExternalStore call block not parseable in "
        "VersionBanner.tsx; expected a single multi-line call "
        "expression."
    )
    snapshot_arg = use_sync_block.group(1)
    assert "getVersionBannerDismissed" in snapshot_arg, (
        "useSyncExternalStore's snapshot arg must read "
        "getVersionBannerDismissed() so a setVersionBannerDismissed(true) "
        "call flips the banner off without a parallel store."
    )
    # (3) The subscribe arg must reference the typed store's
    # subscribe method (with a no-op fallback for the pre-mount
    # window). The `store ? store.subscribe : () => () => undefined`
    # ternary is the canonical pattern used in
    # `infrastructure/page-chrome.tsx` for tree-source — the banner
    # mirrors it for the dismissal key.
    assert re.search(
        r"\bstore\s*\?\s*[\s\S]*?store\s*\.\s*subscribe\b",
        snapshot_arg,
    ), (
        "useSyncExternalStore's subscribe arg must wire through "
        "the typed store's subscribe method (the same instance "
        "`useBrowserStateStore()` returns) so dismiss notifications "
        "reach the banner; a parallel store or one-shot snapshot "
        "is forbidden."
    )


def test_page_chrome_mounts_version_banner_without_duplicate_store():
    """PR 5c.1b-B: PageChrome MUST render `<VersionBanner />` in
    the existing `data-slot="banner-host"` slot AND MUST NOT
    construct a second browser-state store."""
    text = _read_stripped(PAGE_CHROME_FILE)
    assert "VersionBanner" in text, (
        "page-chrome.tsx must render <VersionBanner />"
    )
    assert "createBrowserStateStore" not in text, (
        "page-chrome.tsx must NOT call createBrowserStateStore(); "
        "the single store lives in AppShell.tsx."
    )


def test_detail_panel_renders_with_id_detail_panel():
    """PR 5c.1b-B: DetailPanel MUST stamp `id="detail-panel"` on
    its root element so legacy e2e / Playwright locators and CSS
    selectors keep resolving."""
    text = _read_stripped(DETAIL_PANEL_FILE)
    assert 'id="detail-panel"' in text, (
        "DetailPanel.tsx must stamp id=\"detail-panel\" on its root "
        "aside (legacy DOM contract preserved)"
    )


def test_detail_panel_close_uses_data_action_close_detail():
    """PR 5c.1b-B: DetailPanel MUST render a close button (or
    element) with `data-action="close-detail"` so the legacy
    Playwright binding keeps resolving."""
    text = _read_stripped(DETAIL_PANEL_FILE)
    assert 'data-action="close-detail"' in text, (
        "DetailPanel.tsx must render a close button with "
        "data-action=\"close-detail\""
    )
    assert "onClick" in text, (
        "data-action=\"close-detail\" must be wired to an onClick "
        "handler"
    )


def test_detail_panel_close_hides_panel_and_force_search_reopens():
    """PR 5c.1b-B: DetailPanel MUST track a `detailOpen` state.
    The close handler drops it to false; a later `forceOpenSearch`
    bump MUST reset it to true so the panel reopens (closes the
    legacy silent-no-op regression on re-selecting a previously
    closed taxon)."""
    text = _read_stripped(DETAIL_PANEL_FILE)
    assert "detailOpen" in text, (
        "DetailPanel.tsx must track a detailOpen state"
    )
    assert re.search(r"setDetailOpen\s*\(\s*true\s*\)", text), (
        "DetailPanel.tsx must reset detailOpen to true inside the "
        "forceOpenSearch effect so Search-online reopens the panel"
    )
    assert "forceOpenSearch" in text, (
        "DetailPanel.tsx must read the forceOpenSearch prop to "
        "trigger the reopen"
    )
    assert "data-detail-open=" in text, (
        "DetailPanel.tsx must stamp data-detail-open on the aside"
    )


def test_detail_panel_renders_detail_header_and_detail_tabs_hooks():
    """PR 5c.1b-B: DetailPanel MUST render `.detail-header` and
    `.detail-tabs` structural elements inside the root so the
    sticky CSS contract in `globals.css` can pin them while the
    panel body scrolls."""
    text = _read_stripped(DETAIL_PANEL_FILE)
    assert "detail-header" in text, (
        "DetailPanel.tsx must render a .detail-header structural "
        "hook"
    )
    assert "detail-tabs" in text, (
        "DetailPanel.tsx must render a .detail-tabs structural "
        "hook"
    )


def test_globals_css_pins_detail_header_and_detail_tabs_as_sticky():
    """PR 5c.1b-B: `globals.css` MUST declare `position: sticky`
    on BOTH `.detail-header` AND `.detail-tabs` (inside the
    `.detail-panel` scroll viewport) so the title + tabs stay
    pinned while the body scrolls. The `top` offsets MUST be
    pixel values that keep the header above the tabs.

    Coherence fix: the tab `top` offset and the header height MUST
    both resolve to the same pixel value so the two cannot drift.
    The source contract accepts EITHER a literal `<length>`
    (`49px` / `0` / `3rem` / …) OR a `var(--…)` reference that
    resolves to a `<length>`. When a `var(--…)` is used, the
    underlying token is asserted separately by
    `test_globals_css_detail_header_height_token_is_single_source_of_truth`
    so the contract is structurally enforced, not duplicated
    across two magic numbers."""
    # Accepts: literal px/rem/em/% AND var(--…) with optional
    # fallback. The var branch covers the coherence fix where
    # both selectors reference `--detail-header-height`.
    TOP_OFFSET_RE = (
        r"top\s*:\s*"
        r"(?:"
        r"-?\d+(?:\.\d+)?(?:px|rem|em|%)?"
        r"|"
        r"var\s*\(\s*--[\w-]+(?:\s*,[^)]*)?\)"
        r")"
    )
    text = _read(GLOBALS_CSS_FILE)
    for selector, label in (
        (".detail-header", "detail-header"),
        (".detail-tabs",   "detail-tabs"),
    ):
        block = re.search(
            rf"{re.escape(selector)}\s*\{{([^{{}}]+?)\}}", text
        )
        assert block, (
            f"globals.css must declare a {selector!r} rule block"
        )
        body = block.group(1)
        assert re.search(r"position\s*:\s*sticky", body), (
            f"{label}: globals.css rule body MUST include "
            f"`position: sticky` (verbatim)"
        )
        assert re.search(TOP_OFFSET_RE, body), (
            f"{label}: globals.css rule body MUST include a `top:` "
            f"offset (literal pixel/rem/em/% value OR a "
            f"`var(--<token>)` reference that resolves to one)"
        )
        assert re.search(r"\bz-index\s*:", body), (
            f"{label}: globals.css rule body MUST include `z-index` "
            f"so the sticky layer stacks above the body"
        )


def test_globals_css_detail_header_height_token_is_single_source_of_truth():
    """PR 5c.1b-B (coherence fix): the DetailPanel header height
    MUST live in ONE CSS custom property so the sticky
    `.detail-header` `min-height` and the sticky `.detail-tabs`
    `top` offset cannot drift when padding or font-size changes
    downstream. The token MUST live in the `:root` block inside
    `@layer components` (alongside the existing 3c-e1 /
    3c-e2 aliases), MUST be a `<length>` (px / rem / em / %), and
    BOTH selectors MUST reference it via `var(--…)`. A literal
    duplicate (`49px` in two places) would re-introduce the
    drift the coherence fix exists to remove."""
    text = _read(GLOBALS_CSS_FILE)
    # (1) The token must be declared exactly once, on `:root`,
    # inside the `@layer components` block (where the existing
    # aliases live). Anchor `:root` at line-start (after optional
    # indent) so the regex doesn't pick up `:root { … }` mentions
    # inside prose comments higher in the file.
    root_block = re.search(
        r"^\s*:root\s*\{([^{}]+)\}", text, flags=re.DOTALL | re.MULTILINE,
    )
    assert root_block, (
        "globals.css must declare a `:root { ... }` block inside "
        "@layer components for the detail-header-height token"
    )
    root_body = root_block.group(1)
    token_re = re.compile(
        r"(--detail-header-height\s*:\s*(-?\d+(?:\.\d+)?)(px|rem|em|%)\s*;)"
    )
    root_match = token_re.search(root_body)
    assert root_match, (
        "globals.css :root block must declare "
        "`--detail-header-height: <number><px|rem|em|%>` as the "
        "single source of truth for the DetailPanel header height"
    )
    assert len(token_re.findall(root_body)) == 1, (
        "the `--detail-header-height` token MUST be declared "
        "exactly once (in `:root`); a duplicate would re-introduce "
        "drift the coherence fix exists to remove"
    )
    token_value = root_match.group(2) + root_match.group(3)
    # (2) `.detail-header` MUST use the token via `var(--…)` for
    # its `min-height` so the header always renders at the same
    # height the tab offset expects.
    header_block = re.search(
        r"\.detail-header\s*\{([^{}]+)\}", text, flags=re.DOTALL,
    )
    assert header_block, (
        "globals.css must declare a `.detail-header` rule block"
    )
    header_body = header_block.group(1)
    assert re.search(
        r"min-height\s*:\s*var\s*\(\s*--detail-header-height(?:\s*,[^)]*)?\)",
        header_body,
    ), (
        "`.detail-header` MUST pin `min-height` to "
        "`var(--detail-header-height)` so the header always "
        "matches the tab `top` offset (no duplicate literal)"
    )
    # (3) `.detail-tabs` MUST use the SAME token via `var(--…)`
    # for its `top` offset so the two cannot drift.
    tabs_block = re.search(
        r"\.detail-tabs\s*\{([^{}]+)\}", text, flags=re.DOTALL,
    )
    assert tabs_block, (
        "globals.css must declare a `.detail-tabs` rule block"
    )
    tabs_body = tabs_block.group(1)
    assert re.search(
        r"top\s*:\s*var\s*\(\s*--detail-header-height(?:\s*,[^)]*)?\)",
        tabs_body,
    ), (
        "`.detail-tabs` MUST pin `top` to "
        "`var(--detail-header-height)` so the tab offset cannot "
        "drift away from the header height"
    )


def test_globals_css_minimal_version_banner_style_uses_tokens_only():
    """PR 5c.1b-B: `globals.css` MUST include a minimal
    `#version-banner` style block so the banner is visible when
    active. The block MUST NOT introduce raw hex literals — all
    colors route through `var(--…)` design tokens."""
    text = _read(GLOBALS_CSS_FILE)
    block = re.search(
        r"#version-banner\s*\{" + r"([^{}]+)" + r"\}", text
    )
    assert block, (
        "globals.css must include a minimal #version-banner rule "
        "block so the banner is visible when active"
    )
    body = block.group(1)
    raw_hex = re.findall(r"#[0-9a-fA-F]{3,8}\b", body)
    assert not raw_hex, (
        f"#version-banner rule body MUST NOT use raw hex literals; "
        f"all colors must route through var(--…) tokens. Found: "
        f"{raw_hex!r}"
    )
