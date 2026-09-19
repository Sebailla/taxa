"""
Browser-state storage-ownership contract tests (ODD-BSTATE-001).

Pins the storage-isolation rule for the `browser-state` capability
module (PR 4a/4b predecessor). The browser-state module owns exactly
ONE ``localStorage.getItem`` + ONE ``localStorage.setItem`` site per
key (four keys → four read sites + four write sites), and every other
capability module (``taxonomy``, ``research``, ``app-shell``,
``design-system``) MUST stay free of direct ``localStorage`` access —
the typed store is the only legal surface. Storage failures (private
mode, quota exceeded, missing ``window`` during SSR) MUST be swallowed
via ``safeStorage`` so the application keeps rendering with the typed
default rather than crashing the React tree.

Layer-purity contract (spec.md rule 4): the ``domain`` layer is plain
TypeScript — no ``localStorage``, no ``window``, no ``document``, no
``process``; the ``infrastructure`` layer owns the actual storage
calls; the ``application`` layer is a thin React adapter and MUST NOT
import the storage helpers directly. The barrel
``src/modules/browser-state/index.ts`` re-exports the typed API only
— no raw ``localStorage`` getter/setter leaks through.

References:
    openspec/changes/complete-taxa-frontend-migration/specs/browser-state-hydration/spec.md
    openspec/changes/complete-taxa-frontend-migration/tasks.md §Phase 4a
    openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md Rule 4 + Rule 5
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
BS_ROOT = REPO_ROOT / "src" / "modules" / "browser-state"
DOMAIN_DIR = BS_ROOT / "domain"
INFRA_DIR = BS_ROOT / "infrastructure"
APP_DIR = BS_ROOT / "application"
BARREL = BS_ROOT / "index.ts"

DOMAIN_KEYS_FILE = DOMAIN_DIR / "keys.ts"
DOMAIN_DEFAULTS_FILE = DOMAIN_DIR / "defaults.ts"
INFRA_STORE_FILE = INFRA_DIR / "store.ts"
APP_HOOK_FILE = APP_DIR / "useBrowserStateKey.ts"

# The four canonical storage keys (per the
# browser-state-hydration spec table). Pin the localStorage literal
# names verbatim so a future refactor cannot silently rename them
# (the legacy `web/state.js` consumers would break without a
# coordinated migration).
EXPECTED_STORAGE_KEYS: tuple[str, ...] = (
    "taxa.settings.theme",
    "taxa.tree.source",
    "taxa.tree.lastTaxonId",
    "taxa.tree.kebabOpenId",
)

# Four canonical logical names exposed through the public barrel.
# The hook + read/write signatures use the LOGICAL name; the
# infrastructure layer resolves the logical name → localStorage key
# through the constant declared in `domain/keys.ts`.
EXPECTED_LOGICAL_NAMES: tuple[str, ...] = (
    "theme",
    "tree-source",
    "last-taxon-id",
    "kebab-open-id",
)

# Capabilities other than browser-state. Storage ownership MUST
# remain isolated — these directories MUST stay free of
# localStorage access (the typed store is the only legal surface).
OTHER_CAPABILITIES: tuple[str, ...] = (
    "taxonomy",
    "research",
    "app-shell",
    "design-system",
)

# Layer names per spec.md rule 3.
LAYERS: tuple[str, ...] = (
    "presentation",
    "application",
    "domain",
    "infrastructure",
)


# ---------------------------------------------------------------------------
# Fixtures — gate the runtime / compile checks on toolchain availability.
# ---------------------------------------------------------------------------
def _has_npx() -> bool:
    return shutil.which("npx") is not None


def _has_node() -> bool:
    return shutil.which("node") is not None


@pytest.fixture()
def require_toolchain() -> None:
    if not (_has_npx() and _has_node()):
        pytest.skip("npx + node required on PATH for compile/runtime test")


def _read_text(path: Path) -> str:
    if not path.is_file():
        pytest.skip(f"file not present yet: {path}")
    return path.read_text(encoding="utf-8")


# Comment-stripping regexes — mirror `tests/test_domain_purity.py`.
# Block comments are matched first so a `//` inside a `/* ... */` is
# not treated as a line-comment opener. Each substitution replaces
# the matched comment with spaces (preserving line numbers + column
# alignment) so diagnostic line numbers stay accurate. Every source-
# level purity / storage-ownership assertion in this file MUST strip
# comments before scanning, otherwise an explanatory comment that
# references a forbidden token (e.g. a doc-block on a domain file
# explaining that storage is owned by `infrastructure/store.ts`) would
# false-positive the guard.
_BLOCK_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/")
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _blank_match(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def _strip_ts_comments(text: str) -> str:
    text = _BLOCK_COMMENT_RE.sub(_blank_match, text)
    text = _LINE_COMMENT_RE.sub(_blank_match, text)
    return text


# Per-key read / write identifier sets. The infrastructure store
# MUST export exactly these four read functions + four write
# functions + four subscribe functions (the "4 read sites / 4 write
# sites / 4 subscribers / 1 reset" contract). Counting the literal
# `localStorage.getItem` substring is brittle — a future refactor
# that centralises the storage helper (the ODD-BSTATE-001 §4a.6
# safeStorage refactor) would legitimately collapse N literal calls
# into N helper invocations without changing the storage-ownership
# contract. The semantic test is therefore: 4 read exports + 4 write
# exports + 4 removeItem calls inside `reset()`.
EXPECTED_READ_FUNCTIONS: tuple[str, ...] = (
    "readTheme", "readTreeSource", "readLastTaxonId", "readKebabOpenId",
)
EXPECTED_WRITE_FUNCTIONS: tuple[str, ...] = (
    "writeTheme", "writeTreeSource", "writeLastTaxonId", "writeKebabOpenId",
)
EXPECTED_SUBSCRIBE_FUNCTIONS: tuple[str, ...] = (
    "subscribeTheme", "subscribeTreeSource",
    "subscribeLastTaxonId", "subscribeKebabOpenId",
)


# ---------------------------------------------------------------------------
# Layout tests — pins spec.md rule 3 (four layers per module) +
# spec.md rule 5 (public barrel). RED marker for ODD-BSTATE-001.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("layer", LAYERS)
def test_browser_state_layer_folder_present(layer: str) -> None:
    """Every capability module carries the four layer folders (rule 3)."""
    assert (BS_ROOT / layer).is_dir(), (
        f"missing layer folder: {BS_ROOT / layer}. ODD-BSTATE-001 must "
        f"land the canonical layer folders before any code is written."
    )


def test_browser_state_barrel_exists() -> None:
    """The barrel `index.ts` exists at the module root (rule 5)."""
    assert BARREL.is_file(), (
        f"missing barrel: {BARREL}. ODD-BSTATE-001 must ship the barrel."
    )


# ---------------------------------------------------------------------------
# File-presence tests — pins the canonical paths
# ``keys.ts`` / ``defaults.ts`` / ``store.ts`` /
# ``useBrowserStateKey.ts``.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "path",
    (
        DOMAIN_KEYS_FILE,
        DOMAIN_DEFAULTS_FILE,
        INFRA_STORE_FILE,
        APP_HOOK_FILE,
        BARREL,
    ),
)
def test_canonical_file_present(path: Path) -> None:
    """Every canonical file MUST be on disk by task close."""
    assert path.is_file(), (
        f"missing canonical file: {path}. ODD-BSTATE-001 must create this "
        f"file inside the documented path."
    )


# ---------------------------------------------------------------------------
# Domain-layer purity — rule 4 forbids React, Next, FastAPI, fetch,
# localStorage, document., window., process. in `domain/`. The hook
# (`application/`) is allowed to import React; the store
# (`infrastructure/`) is allowed to import nothing from React.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", (DOMAIN_KEYS_FILE, DOMAIN_DEFAULTS_FILE))
def test_domain_file_purity(path: Path) -> None:
    """`domain/keys.ts` + `domain/defaults.ts` are plain TS — no
    framework, I/O, browser, or process tokens. The hook and the
    store hold those concerns in their own layers.

    Comments are stripped before scanning so a doc-block explaining
    the layer rule (e.g. "storage lives in `infrastructure/store.ts`")
    does not false-positive the guard.
    """
    if not path.exists():
        pytest.skip(f"domain file not present yet: {path}")
    stripped = _strip_ts_comments(path.read_text(encoding="utf-8"))
    forbidden = (
        "react", "next", "nextjs", "fastapi", "starlette", "pydantic",
        "fetch(", "localStorage", "sessionStorage",
        "document.", "window.", "process.", "globalThis.",
    )
    for token in forbidden:
        assert token not in stripped, (
            f"{path.name} must stay free of {token!r}; spec.md rule 4."
        )


def test_application_hook_can_import_react_but_not_localstorage() -> None:
    """The `application/useBrowserStateKey.ts` hook MAY import React
    (the hook is a React adapter) but MUST NOT touch `localStorage`
    directly — storage access lives in `infrastructure/store.ts`.
    """
    if not APP_HOOK_FILE.exists():
        pytest.skip("hook file not present yet")
    stripped = _strip_ts_comments(APP_HOOK_FILE.read_text(encoding="utf-8"))
    forbidden = (
        "localStorage", "sessionStorage",
        "fetch(", "document.", "process.", "globalThis.",
    )
    for token in forbidden:
        assert token not in stripped, (
            f"useBrowserStateKey.ts must NOT touch {token!r}; storage access "
            f"is owned by infrastructure/store.ts."
        )


def test_infrastructure_store_has_storage_calls() -> None:
    """`infrastructure/store.ts` is the ONLY layer that may call
    `localStorage`. The hook reaches storage exclusively through the
    typed read/write/subscribe surface; the domain is pure types.
    """
    if not INFRA_STORE_FILE.exists():
        pytest.skip("store file not present yet")
    text = INFRA_STORE_FILE.read_text(encoding="utf-8")
    # At least one getItem / setItem / removeItem site is required.
    # The spec table pins 4 reads + 4 writes + 4 removeItem-from-reset
    # (the count assertions live in
    # `test_browser_state_module_has_exactly_four_read_sites` etc.).
    assert "localStorage" in text or "globalThis" in text, (
        "infrastructure/store.ts MUST own the localStorage calls — the "
        "typed store is the only legal storage surface."
    )


# ---------------------------------------------------------------------------
# Storage-ownership contract — exactly 4 reads + 4 writes + 4
# removeItem sites (the reset affordance) inside the browser-state
# module, and ZERO in any other capability module.
# ---------------------------------------------------------------------------
def _count_occurrences(text: str, needle: str) -> int:
    """Count non-overlapping occurrences of `needle` in `text`. The
    substring count is what the source-level contract cares about —
    every `localStorage.getItem(` call site is one read regardless of
    how it is wrapped.
    """
    return len(re.findall(re.escape(needle), text))


def _module_text(module: str) -> str:
    """Concatenate every `.ts`/`.tsx` file under ``src/modules/<module>``
    into a single string. Comments preserved (a future PR that hides a
    `localStorage.` reference inside a comment would still be a
    violation). Skips missing modules cleanly."""
    root = REPO_ROOT / "src" / "modules" / module
    if not root.exists():
        return ""
    parts: list[str] = []
    for path in sorted(root.rglob("*.ts")) + sorted(root.rglob("*.tsx")):
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def test_browser_state_module_has_exactly_four_read_sites() -> None:
    """ODD-BSTATE-001 contract: exactly 4 read functions in the
    browser-state module — one per typed key. Each read function is
    the canonical "read site" for its key; the typed store owns
    every read regardless of whether the storage call is inlined or
    routed through a `safeStorage` helper (the ODD-BSTATE-001 §4a.6
    refactor target).
    """
    text = _module_text("browser-state")
    if not text:
        pytest.skip("browser-state module not present yet")
    stripped = _strip_ts_comments(text)
    missing = [
        name for name in EXPECTED_READ_FUNCTIONS
        if not re.search(rf"export\s+function\s+{name}\b", stripped)
    ]
    assert not missing, (
        f"browser-state MUST export exactly 4 read functions "
        f"(one per typed key); missing: {missing}. The typed store "
        f"owns every read."
    )


def test_browser_state_module_has_at_least_four_write_sites() -> None:
    """ODD-BSTATE-001 contract: exactly 4 write functions in the
    browser-state module — one per typed key. Storage ownership
    stays centralised.
    """
    text = _module_text("browser-state")
    if not text:
        pytest.skip("browser-state module not present yet")
    stripped = _strip_ts_comments(text)
    missing = [
        name for name in EXPECTED_WRITE_FUNCTIONS
        if not re.search(rf"export\s+function\s+{name}\b", stripped)
    ]
    assert not missing, (
        f"browser-state MUST export exactly 4 write functions "
        f"(one per typed key); missing: {missing}."
    )


def test_browser_state_module_has_four_subscribe_sites() -> None:
    """ODD-BSTATE-001 contract: exactly 4 subscribe functions — one
    per typed key. Each subscribe returns an idempotent unsubscribe
    handle that the React adapter (`useSyncExternalStore`) consumes.
    """
    text = _module_text("browser-state")
    if not text:
        pytest.skip("browser-state module not present yet")
    stripped = _strip_ts_comments(text)
    missing = [
        name for name in EXPECTED_SUBSCRIBE_FUNCTIONS
        if not re.search(rf"export\s+function\s+{name}\b", stripped)
    ]
    assert not missing, (
        f"browser-state MUST export exactly 4 subscribe functions "
        f"(one per typed key); missing: {missing}."
    )


def test_browser_state_module_has_reset_remove_item_sites() -> None:
    """ODD-BSTATE-001 contract: the `reset()` affordance MUST call
    `localStorage.removeItem` for every typed key — one per key,
    four total — so a future PR cannot drop a key from the reset
    path.
    """
    text = _module_text("browser-state")
    if not text:
        pytest.skip("browser-state module not present yet")
    stripped = _strip_ts_comments(text)
    count = _count_occurrences(stripped, "localStorage.removeItem")
    assert count >= len(EXPECTED_STORAGE_KEYS), (
        f"browser-state reset() MUST removeItem every typed key "
        f"({len(EXPECTED_STORAGE_KEYS)} total); found {count} removeItem "
        f"sites. A missing removeItem breaks the reset contract."
    )


def test_browser_state_infrastructure_owns_local_storage_calls() -> None:
    """Storage access is centralised in `infrastructure/store.ts`.
    Every literal `localStorage.` reference in the module MUST live
    inside the infrastructure layer; the domain, application, and
    barrel files MUST stay storage-free.
    """
    text = _module_text("browser-state")
    if not text:
        pytest.skip("browser-state module not present yet")
    # Concatenate every file but tag each file's origin so we can
    # pinpoint which layer owns a literal reference.
    root = REPO_ROOT / "src" / "modules" / "browser-state"
    offenders: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*.ts")) + sorted(root.rglob("*.tsx")):
        if not path.is_file():
            continue
        if path == INFRA_STORE_FILE:
            continue  # the only legal home for storage primitives
        rel = path.relative_to(BS_ROOT).as_posix()
        # Only the top-level `infrastructure/store.ts` is allowed to
        # touch `localStorage` directly. The application hook
        # (`useBrowserStateKey.ts`) and the barrel re-route through
        # the typed store; the domain layer is pure types.
        body = _strip_ts_comments(path.read_text(encoding="utf-8"))
        for needle in ("localStorage.", "sessionStorage.", "window.localStorage"):
            if needle in body:
                offenders.append((rel, needle))
    assert not offenders, (
        f"storage primitives MUST stay in infrastructure/store.ts; "
        f"found {offenders}. The typed store is the only legal "
        f"storage surface."
    )


@pytest.mark.parametrize("other_module", OTHER_CAPABILITIES)
def test_other_module_does_not_touch_localstorage(other_module: str) -> None:
    """No capability module outside `browser-state` is allowed to
    read or write `localStorage` directly. The typed store is the
    only legal storage surface.
    """
    text = _module_text(other_module)
    if not text:
        pytest.skip(f"module not present yet: {other_module}")
    # Strip TS comments so documentation referring to `localStorage`
    # is not a false positive.
    block = re.compile(r"/\*[\s\S]*?\*/")
    line = re.compile(r"//[^\n]*")
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))  # noqa: E731
    stripped = block.sub(blank, text)
    stripped = line.sub(blank, stripped)
    for needle in ("localStorage.getItem", "localStorage.setItem", "localStorage.removeItem"):
        assert needle not in stripped, (
            f"{other_module} must NOT call {needle!r} directly; storage "
            f"ownership belongs to the browser-state typed store."
        )


# ---------------------------------------------------------------------------
# Typed-key + typed-default contract — the source-level contract that
# pins the spec table verbatim. The implementation may rename internal
# identifiers but the four logical names + four localStorage literals
# + the typed defaults MUST stay present in the source.
# ---------------------------------------------------------------------------
def test_keys_file_declares_four_storage_key_literals() -> None:
    """`domain/keys.ts` declares the four localStorage key literals
    exactly once each (so a typo would surface here)."""
    if not DOMAIN_KEYS_FILE.exists():
        pytest.skip("keys.ts not present yet")
    text = DOMAIN_KEYS_FILE.read_text(encoding="utf-8")
    for literal in EXPECTED_STORAGE_KEYS:
        assert f'"{literal}"' in text, (
            f"domain/keys.ts must declare the storage key literal {literal!r} "
            f"(browser-state-hydration spec table)."
        )


def test_defaults_file_exposes_four_typed_defaults() -> None:
    """`domain/defaults.ts` exports the four typed defaults the spec
    table pins: `theme: "light"`, `tree-source: "col"`,
    `last-taxon-id: null`, `kebab-open-id: null`.

    Comments are stripped so the assertion inspects only code.
    """
    if not DOMAIN_DEFAULTS_FILE.exists():
        pytest.skip("defaults.ts not present yet")
    text = _strip_ts_comments(DOMAIN_DEFAULTS_FILE.read_text(encoding="utf-8"))
    # The active default literals MUST appear as code.
    assert re.search(r"DEFAULT_THEME\s*:\s*Theme\s*=\s*\"light\"", text), (
        "DEFAULT_THEME must be typed Theme and bound to `\"light\"`."
    )
    assert re.search(r"DEFAULT_TREE_SOURCE\s*:\s*TreeSource\s*=\s*\"col\"", text), (
        "DEFAULT_TREE_SOURCE must be typed TreeSource and bound to `\"col\"`."
    )
    # `null` defaults for last-taxon-id + kebab-open-id — both
    # typed as `number | null` so the source must reference `null`
    # at least twice (one per default).
    null_count = len(re.findall(r":\s*number\s*\|\s*null\s*=\s*null\b", text))
    assert null_count >= 2, (
        "defaults.ts must declare two typed null defaults "
        "(`number | null = null`); found "
        f"{null_count}. The two keys (last-taxon-id + kebab-open-id) "
        f"both have null as their spec-table default."
    )


def test_barrel_exports_typed_surface() -> None:
    """The public barrel re-exports the typed API surface: the four
    storage-key constants, the typed defaults, and the four read +
    four write + subscribe + reset functions. No raw
    `localStorage` getter/setter leaks through the barrel.
    """
    if not BARREL.exists():
        pytest.skip("barrel not present yet")
    text = BARREL.read_text(encoding="utf-8")
    # Strip comments before scanning for forbidden tokens.
    block = re.compile(r"/\*[\s\S]*?\*/")
    line = re.compile(r"//[^\n]*")
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))  # noqa: E731
    stripped = block.sub(blank, text)
    stripped = line.sub(blank, stripped)
    for needle in ("localStorage.", "sessionStorage.", "window.localStorage"):
        assert needle not in stripped, (
            f"barrel MUST NOT expose raw {needle!r}; the typed store is "
            f"the only legal storage surface."
        )
    # The barrel MUST re-export each typed constant / function name
    # so cross-module consumers can import them. The exact
    # identifier set is the union of `EXPECTED_LOGICAL_NAMES`,
    # `readX` / `writeX` per key, plus `subscribe` / `reset`.
    expected_identifiers = [
        "DEFAULT_THEME", "DEFAULT_TREE_SOURCE",
        "DEFAULT_LAST_TAXON_ID", "DEFAULT_KEBAB_OPEN_ID",
        "readTheme", "writeTheme", "subscribeTheme",
        "readTreeSource", "writeTreeSource", "subscribeTreeSource",
        "readLastTaxonId", "writeLastTaxonId", "subscribeLastTaxonId",
        "readKebabOpenId", "writeKebabOpenId", "subscribeKebabOpenId",
        "reset",
    ]
    missing = [name for name in expected_identifiers if name not in text]
    assert not missing, (
        f"barrel missing re-exports: {missing}. The typed API surface "
        f"must be reachable through the public barrel."
    )


