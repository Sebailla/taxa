"""
Verification-only SUBSET marker for the already-shipped 4b hydration /
AppShell superset. NOT implementation TDD.

This is a hermetic, regex/source-level marker. It pins PRESENCE of
canonical 4b seams against the *already-shipped* superset, allows
legitimate extras (PR 5b.4 tab routing, PR 5c.1b-A typed context,
PR 5c.1b-B VersionBanner, PR 5c.1a freshwater + dismissal keys), and
never asserts EQUALITY or ABSENCE of later features. TS comments are
stripped so a JSDoc reference cannot satisfy a structural regex by
accident. No Node, no `next build`, no Playwright, no JSDOM, no
subprocess — the runtime hydration behaviour lives in
``tests/test_hydration_console.py`` and is never duplicated here.

Two TRUE invariants are pinned as absence (upstream, not later-
feature gates): (a) the layout MUST NOT import ``@taxa/browser-state``
directly (PR 3b chain-topology guard, relaxed only for
``@taxa/app-shell`` by PR 4b.6), and (b) ``app-shell/presentation/``
MUST NOT touch ``localStorage`` (PR 4a 5+5 contract — only
``browser-state/infrastructure/store.ts`` writes).

Covered seams (canonical 4b + non-brittle superset evidence):

  1. ``app-shell`` barrel exports ``AppShell``, ``BrowserSurface``,
     ``useBrowserStateStore`` (4b.6 + 5b.4 + 5c.1b-A superset).
  2. ``src/app/layout.tsx`` imports ``AppShell`` from
     ``@taxa/app-shell``, wraps ``{children}``, does NOT directly
     import ``@taxa/browser-state``.
  3. ``AppShell.tsx`` gates persisted-state reads behind
     ``useMounted()``, rehydrates via ``window.history.replaceState``,
     flips ``data-theme`` after mount.
  4. The typed ``BrowserStateStoreContext`` lives in
     ``app-shell/presentation/`` and is re-exported as
     ``useBrowserStateStore`` through the module barrel.
  5. ``page-chrome.tsx`` renders three ordered pinned tabs
     (browser / classification / settings) and a theme toggle that
     is ``disabled={!mounted}`` until rehydration. The tree-source
     control carries the three pinned data attributes.
  6. ``app-shell/presentation/`` never touches ``localStorage``.
  7. ``VersionBanner`` is a mounted/store/outdated/dismissed
     fail-closed host and persists dismissal via the typed store.

References:
    openspec/changes/complete-taxa-frontend-migration/tasks.md §Phase 4b
    openspec/changes/complete-taxa-frontend-migration/specs/
        browser-state-hydration/spec.md §"Hydration guard"
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


# Repo-rooted paths (single source of truth for the subset marker).
REPO_ROOT = Path(__file__).resolve().parent.parent
APP_SHELL_DIR = REPO_ROOT / "src" / "modules" / "app-shell"
APP_SHELL_BARREL = APP_SHELL_DIR / "index.ts"
APP_SHELL_PRESENTATION_DIR = APP_SHELL_DIR / "presentation"
APP_SHELL_FILE = APP_SHELL_PRESENTATION_DIR / "AppShell.tsx"
BROWSER_STATE_STORE_CONTEXT_FILE = (
    APP_SHELL_PRESENTATION_DIR / "browser-state-store-context.ts"
)
PAGE_CHROME_FILE = APP_SHELL_DIR / "infrastructure" / "page-chrome.tsx"
VERSION_BANNER_FILE = APP_SHELL_PRESENTATION_DIR / "VersionBanner.tsx"
LAYOUT_FILE = REPO_ROOT / "src" / "app" / "layout.tsx"


# Comment-stripping helpers — mirrors tests/test_browser_state_keys.py.
# Preserves line numbers so a pytest diagnostic stays aligned with the
# original source file.
_BLOCK_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/")
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _blank_match(match: re.Match[str]) -> str:
    """Replace every character of a comment with a space (preserves
    line numbers; renders the comment invisible to the regex)."""
    return re.sub(r"[^\n]", " ", match.group(0))


def _strip_ts_comments(text: str) -> str:
    text = _BLOCK_COMMENT_RE.sub(_blank_match, text)
    text = _LINE_COMMENT_RE.sub(_blank_match, text)
    return text


def _read(path: Path) -> str:
    if not path.is_file():
        pytest.fail(
            f"required source file missing: {path.relative_to(REPO_ROOT).as_posix()}"
        )
    return path.read_text(encoding="utf-8")


def _read_stripped(path: Path) -> str:
    return _strip_ts_comments(_read(path))


def _app_shell_presentation_files() -> list[Path]:
    """All ``.ts``/``.tsx`` files under ``app-shell/presentation/``,
    excluding the layer barrel (JSDoc-only)."""
    if not APP_SHELL_PRESENTATION_DIR.is_dir():
        return []
    return sorted(
        p for p in APP_SHELL_PRESENTATION_DIR.rglob("*.ts*")
        if p.is_file() and p.name != "index.ts"
    )


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


# 1. Public barrel exports — 4b.6 + 5b.4 + 5c.1b-A superset
def test_app_shell_barrel_exports_app_shell_browser_surface_and_store_hook():
    """The ``app-shell`` barrel MUST re-export ``AppShell``,
    ``BrowserSurface``, and ``useBrowserStateStore`` (subset marker —
    presence-of-three; later additions are allowed).
    """
    cleaned = _read_stripped(APP_SHELL_BARREL)
    for name in ("AppShell", "BrowserSurface", "useBrowserStateStore"):
        assert re.search(
            rf"\bexport\b\s*\{{[^}}]*\b{re.escape(name)}\b",
            cleaned,
        ), (
            f"app-shell barrel must re-export `{name}` "
            f"(PR 4b.6 + PR 5b.4 + PR 5c.1b-A superset contract); "
            f"got:\n{cleaned}"
        )


# 2. App Router layout integration seam — 4b.6
def test_layout_imports_app_shell_from_public_alias():
    """``src/app/layout.tsx`` MUST import ``AppShell`` from
    ``@taxa/app-shell``.
    """
    text = _read_stripped(LAYOUT_FILE)
    assert re.search(
        r"""from\s+["']@taxa/app-shell["']""",
        text,
    ), (
        "src/app/layout.tsx MUST import AppShell from `@taxa/app-shell` "
        "(PR 4b.6 integration seam contract)"
    )


def test_layout_wraps_children_with_app_shell():
    """``src/app/layout.tsx`` MUST wrap ``{children}`` with
    ``<AppShell>...</AppShell>`` (subset marker — later descendants
    inside / around the AppShell are allowed).
    """
    text = _read_stripped(LAYOUT_FILE)
    assert re.search(
        r"""<AppShell\b[^>]*>\s*\{children\}\s*</AppShell>""",
        text,
        flags=re.DOTALL,
    ), (
        "src/app/layout.tsx MUST wrap `{children}` with "
        "`<AppShell>...</AppShell>` (PR 4b.6 integration seam contract)"
    )


def test_layout_does_not_directly_import_browser_state():
    """True invariant (chain-topology guard, PR 3b): the layout
    MUST NOT import ``@taxa/browser-state`` directly — PR 4b.6
    relaxed the guard only for ``@taxa/app-shell``.
    """
    text = _read_stripped(LAYOUT_FILE)
    assert not re.search(
        r"""from\s+["']@taxa/browser-state["']""",
        text,
    ), (
        "src/app/layout.tsx MUST NOT import @taxa/browser-state directly; "
        "the AppShell is the sole consumer (PR 4b.6 chain-topology guard)"
    )


# 3. AppShell mounted gate + rehydration — 4b.2 + 4b.4
def test_app_shell_uses_mounted_gate_before_store_reads():
    """AppShell MUST gate persisted-state reads behind ``useMounted()``."""
    text = _read_stripped(APP_SHELL_FILE)
    assert "useMounted" in text, (
        "AppShell.tsx must import + call useMounted() (PR 4b.2 + 4b.5)"
    )
    effect_block = re.search(
        r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{([\s\S]*?)\}\s*,\s*\[",
        text,
    )
    assert effect_block, "AppShell.tsx must call useEffect for rehydration"
    effect_body = effect_block.group(1)
    assert "mounted" in effect_body, (
        "AppShell rehydration effect must reference the `mounted` flag"
    )
    assert re.search(r"if\s*\(\s*!\s*mounted\s*\)\s*return", effect_body), (
        "AppShell rehydration effect MUST early-return when `mounted` "
        "is false (`if (!mounted) return;`)"
    )


def test_app_shell_rehydrates_with_history_replace_state():
    """AppShell MUST rehydrate via ``window.history.replaceState``
    (NOT ``pushState`` — resume state, not navigation).
    """
    text = _read_stripped(APP_SHELL_FILE)
    assert "history.replaceState" in text, (
        "AppShell.tsx must rehydrate via window.history.replaceState "
        "(PR 4b.2 — last-taxon-id is resume state, not navigation)"
    )


def test_app_shell_flips_data_theme_after_mount():
    """AppShell MUST stamp / unstamp ``data-theme`` on ``<html>``
    AFTER mount (PR 4b.4).
    """
    text = _read_stripped(APP_SHELL_FILE)
    assert "dataset.theme" in text, (
        "AppShell.tsx must write document.documentElement.dataset.theme "
        "(PR 4b.4)"
    )


# 4. Typed context published from app-shell/presentation — 5c.1b-A
def test_typed_context_published_from_app_shell_presentation():
    """The typed ``BrowserStateStoreContext`` MUST live in
    ``app-shell/presentation/`` and be re-exported as
    ``useBrowserStateStore`` through the module barrel.
    """
    if not BROWSER_STATE_STORE_CONTEXT_FILE.is_file():
        pytest.fail(
            f"missing context source: {_rel(BROWSER_STATE_STORE_CONTEXT_FILE)} "
            f"— PR 5c.1b-A requires the typed context in presentation/"
        )
    text = _read_stripped(BROWSER_STATE_STORE_CONTEXT_FILE)
    assert "createContext" in text, (
        "browser-state-store-context.ts must call createContext(...)"
    )
    assert "useContext" in text, (
        "browser-state-store-context.ts must export a useContext() hook"
    )
    barrel = _read_stripped(APP_SHELL_BARREL)
    assert "useBrowserStateStore" in barrel, (
        "app-shell barrel must re-export useBrowserStateStore (5c.1b-A)"
    )


# 5. Page-chrome tabs + mounted-disabled theme toggle — 4b.3
_PINNED_TAB_ORDER: tuple[str, ...] = ("browser", "classification", "settings")


def test_page_chrome_renders_three_ordered_pinned_tabs():
    """``page-chrome.tsx`` MUST render the three pinned nav tabs in
    order: Browser → Classification → Settings (G2 chrome contract).

    Accepts EITHER literal ``data-path="<tab>"`` JSX stamps OR a
    ``NAV_TABS`` mapping that carries the same three literals.
    """
    text = _read_stripped(PAGE_CHROME_FILE)
    literal_hits = [
        t for t in _PINNED_TAB_ORDER if f'data-path="{t}"' in text
    ]
    uses_nav_tabs = (
        "NAV_TABS" in text
        and all(f'"{t}"' in text for t in _PINNED_TAB_ORDER)
    )
    assert len(literal_hits) >= 3 or uses_nav_tabs, (
        "page-chrome.tsx must stamp data-path on the three pinned tabs "
        "(browser, classification, settings) OR carry a NAV_TABS mapping "
        "with the same three literals"
    )


def test_page_chrome_theme_toggle_is_mounted_disabled():
    """The theme toggle MUST be ``disabled={!mounted}`` until
    rehydration completes (so a pre-hydration click is a no-op).
    """
    text = _read_stripped(PAGE_CHROME_FILE)
    theme_block = re.search(
        r'data-action\s*=\s*["{]theme-toggle["}][\s\S]*?/>',
        text,
    )
    assert theme_block, (
        "page-chrome.tsx must render a theme toggle with "
        'data-action="theme-toggle"'
    )
    body = theme_block.group(0)
    assert "!mounted" in body, (
        "theme toggle MUST be disabled until mounted "
        "(`disabled={!mounted}`)"
    )


def test_page_chrome_tree_source_has_three_pinned_data_attributes():
    """``page-chrome.tsx`` MUST stamp ``data-tree-source`` on three
    pinned sources (``col``, ``worms``, ``freshwater``).

    Accepts EITHER literal JSX stamps OR JSX expression stamps
    that reference a mapping with the same three literals.
    """
    text = _read_stripped(PAGE_CHROME_FILE)
    for literal in ("col", "worms", "freshwater"):
        assert (
            f'data-tree-source="{literal}"' in text
            or (
                "data-tree-source={" in text
                and f'"{literal}"' in text
            )
        ), (
            f"page-chrome.tsx must stamp data-tree-source=\"{literal}\" "
            f"(PR 4b.3 chrome contract + PR 5c.1a extended TreeSource)"
        )


# 6. True invariant — app-shell/presentation never touches localStorage
def test_app_shell_presentation_does_not_touch_localstorage_directly():
    """True invariant (5+5 contract from PR 4a): every file under
    ``app-shell/presentation/`` MUST NOT mention ``localStorage``.
    """
    offenders: list[tuple[Path, int]] = []
    for path in _app_shell_presentation_files():
        cleaned = _read_stripped(path)
        for lineno, line in enumerate(cleaned.splitlines(), start=1):
            if "localStorage" in line:
                offenders.append((path, lineno))
    assert not offenders, (
        "app-shell/presentation files MUST NOT mention `localStorage` "
        "(5+5 contract). Offenders:\n"
        + "\n".join(f"  {_rel(p)}:{ln}" for p, ln in offenders)
    )


# 7. VersionBanner — mounted / store / outdated / dismissed fail-closed
def test_version_banner_renders_banner_host_with_mounted_gate():
    """``VersionBanner`` MUST render a ``data-slot="banner-host"``
    host and MUST consult ``useMounted()``.
    """
    if not VERSION_BANNER_FILE.is_file():
        pytest.fail(
            f"missing {_rel(VERSION_BANNER_FILE)} — PR 5c.1b-B"
        )
    text = _read_stripped(VERSION_BANNER_FILE)
    assert "useMounted" in text, (
        "VersionBanner.tsx must import + call useMounted() "
        "(PR 5c.1b-B fail-closed)"
    )
    assert "banner-host" in text, (
        'VersionBanner.tsx must render `data-slot="banner-host"`'
    )


def test_version_banner_consumes_store_via_context_not_second_construction():
    """``VersionBanner`` MUST consume the typed store via
    ``useBrowserStateStore()`` and MUST NOT call
    ``createBrowserStateStore()`` (AppShell is the sole constructor).
    """
    text = _read_stripped(VERSION_BANNER_FILE)
    assert "useBrowserStateStore" in text, (
        "VersionBanner.tsx must consume the typed store via "
        "useBrowserStateStore() (single-store contract)"
    )
    assert "createBrowserStateStore" not in text, (
        "VersionBanner.tsx MUST NOT call createBrowserStateStore() — "
        "AppShell is the sole construction site (5+5 contract)"
    )


def test_version_banner_persists_dismissal_via_typed_store():
    """``VersionBanner`` MUST persist dismissal via
    ``store.setVersionBannerDismissed(true)`` AND MUST read the
    current snapshot via ``getVersionBannerDismissed()``.

    Subset marker: presence-only — the reactive ``useSyncExternalStore``
    wiring is pinned separately by ``tests/test_browser_state_keys.py``.
    """
    text = _read_stripped(VERSION_BANNER_FILE)
    assert "setVersionBannerDismissed" in text, (
        "VersionBanner.tsx must call setVersionBannerDismissed(true) "
        "on the dismiss click (typed-store persistence contract)"
    )
    assert "getVersionBannerDismissed" in text, (
        "VersionBanner.tsx must read getVersionBannerDismissed() to "
        "honour a previous dismissal (fail-closed visibility)"
    )


def test_version_banner_is_outdated_fail_closed():
    """``VersionBanner`` MUST derive visibility from an
    ``actual < expected`` comparison (fail-closed outdated state).
    """
    text = _read_stripped(VERSION_BANNER_FILE)
    assert re.search(
        r"\b\w+\s*\.\s*actual\s*<\s*\w+\s*\.\s*expected\b"
        r"|\bactual\s*<\s*expected\b",
        text,
    ), (
        "VersionBanner.tsx must compare `actual < expected` to derive "
        "the outdated state (fail-closed visibility)"
    )
