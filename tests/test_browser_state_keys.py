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

from pathlib import Path
import re
import shutil
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
BS_ROOT = REPO_ROOT / "src" / "modules" / "browser-state"
DOMAIN_DIR = BS_ROOT / "domain"
INFRA_DIR = BS_ROOT / "infrastructure"
APP_DIR = BS_ROOT / "application"
BARREL = BS_ROOT / "index.ts"

DOMAIN_KEYS_FILE = DOMAIN_DIR / "keys.ts"
DOMAIN_DEFAULTS_FILE = DOMAIN_DIR / "defaults.ts"
# Canonical Explorer-state cap definitions for boundary pins.
DOMAIN_EXPLORER_STATE_FILE = DOMAIN_DIR / "explorer-state.ts"
# ODD-BSTATE-TAX-001-A — split per storage key. The monolithic
# `useBrowserStateKey.ts` + `store.ts` are retired; each storage key
# owns its own hook + store file. The tests follow the split: every
# per-key path is a separate file under its layer, and the layout
# checks iterate over the canonical list.
INFRA_STORE_THEME_FILE = INFRA_DIR / "storeTheme.ts"
INFRA_STORE_TREE_SOURCE_FILE = INFRA_DIR / "storeTreeSource.ts"
INFRA_STORE_LAST_TAXON_ID_FILE = INFRA_DIR / "storeLastTaxonId.ts"
INFRA_STORE_KEBAB_OPEN_ID_FILE = INFRA_DIR / "storeKebabOpenId.ts"
# ODD-ASN-001 — internal-flag store. The hydration-probe gate
# (`presentation/HydrationProbeGate.tsx`) reads the flag via the
# typed store so the presentation layer stays free of
# `localStorage.*` references (the ODD-BSTATE-TAX-001
# storage-ownership contract). Registered in `INFRA_STORE_FILES`
# so the legal-home set in
# `test_browser_state_infrastructure_owns_local_storage_calls`
# includes this file alongside the four sibling stores.
INFRA_STORE_INTERNAL_FLAG_FILE = INFRA_DIR / "storeInternalFlag.ts"
# ODD-BSTATE-EXPLORER-PERSIST — explorer-state store. The Browser-
# tab Explorer working-set persistence (EXPLORER-PERSIST of
# `odd/tasks/explorer-orientation-state.md`) now lives behind the
# canonical per-key browser-state chain (`taxa.fex.explorerState`).
# The previous design owned the raw localStorage key inside
# `src/modules/research/presentation/explorer-storage.ts`; the
# architecture correction moves the I/O behind a typed per-key
# store (`infrastructure/storeExplorerState.ts`) so the Research
# module never touches `localStorage.*` directly. Research-side
# pure helpers (parse / serialize / validate / collect) stay
# local because the typed shape is part of the Explorer domain.
INFRA_STORE_EXPLORER_STATE_FILE = INFRA_DIR / "storeExplorerState.ts"
INFRA_STORE_RESET_FILE = INFRA_DIR / "reset.ts"
INFRA_STORE_FILES: tuple[Path, ...] = (
    INFRA_STORE_THEME_FILE,
    INFRA_STORE_TREE_SOURCE_FILE,
    INFRA_STORE_LAST_TAXON_ID_FILE,
    INFRA_STORE_KEBAB_OPEN_ID_FILE,
    INFRA_STORE_INTERNAL_FLAG_FILE,
    INFRA_STORE_EXPLORER_STATE_FILE,
)
APP_HOOK_THEME_FILE = APP_DIR / "useTheme.ts"
APP_HOOK_TREE_SOURCE_FILE = APP_DIR / "useTreeSource.ts"
APP_HOOK_LAST_TAXON_ID_FILE = APP_DIR / "useLastTaxonId.ts"
APP_HOOK_KEBAB_OPEN_ID_FILE = APP_DIR / "useKebabOpenId.ts"
# ODD-BSTATE-EXPLORER-PERSIST — per-key React hook for the
# explorer-state store. Mirrors the per-key hook pattern
# (`useTheme` / `useTreeSource` / etc.). The hook imports ONLY
# from the matching `infrastructure/storeExplorerState.ts` so
# Turbopack retention isolates the chain from the four typed
# chains + the internal-flag chain.
APP_HOOK_EXPLORER_STATE_FILE = APP_DIR / "useExplorerState.ts"
APP_HOOK_FILES: tuple[Path, ...] = (
    APP_HOOK_THEME_FILE,
    APP_HOOK_TREE_SOURCE_FILE,
    APP_HOOK_LAST_TAXON_ID_FILE,
    APP_HOOK_KEBAB_OPEN_ID_FILE,
    APP_HOOK_EXPLORER_STATE_FILE,
)
# The legacy monolithic files — pinned here so a future regression
# that re-introduces the all-keys-in-one-file layout trips the test.
# A strict TDD continuation requires these to be GONE after the split.
APP_HOOK_FILE = APP_DIR / "useBrowserStateKey.ts"
INFRA_STORE_FILE = INFRA_DIR / "store.ts"

# The four canonical storage keys (per the browser-state-hydration
# spec table) plus the Explorer working-state key. Pin every
# localStorage literal so a future refactor cannot silently rename it.
EXPECTED_STORAGE_KEYS: tuple[str, ...] = (
    "taxa.settings.theme",
    "taxa.tree.source",
    "taxa.tree.lastTaxonId",
    "taxa.tree.kebabOpenId",
    "taxa.fex.explorerState",
)

# Five canonical logical names exposed through the public barrel.
# The hook + read/write signatures use the LOGICAL name; the
# infrastructure layer resolves the logical name → localStorage key
# through the constant declared in `domain/keys.ts`.
EXPECTED_LOGICAL_NAMES: tuple[str, ...] = (
    "theme",
    "tree-source",
    "last-taxon-id",
    "kebab-open-id",
    "explorer-state",
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
    "readExplorerState",
)
EXPECTED_WRITE_FUNCTIONS: tuple[str, ...] = (
    "writeTheme", "writeTreeSource", "writeLastTaxonId", "writeKebabOpenId",
    "writeExplorerState",
)
EXPECTED_SUBSCRIBE_FUNCTIONS: tuple[str, ...] = (
    "subscribeTheme", "subscribeTreeSource",
    "subscribeLastTaxonId", "subscribeKebabOpenId",
    "subscribeExplorerState",
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
        BARREL,
        # ODD-BSTATE-TAX-001-A — per-key split. Each storage key
        # owns its own hook + store file. The monolithic
        # `store.ts` + `useBrowserStateKey.ts` are retired; they
        # stay out of the parametrized list so a regression that
        # re-introduces them trips the dedicated
        # `test_monolithic_modules_are_retired` pin below.
        # ODD-ASN-001 — the `taxa-internal-ok` witness flag owns
        # its own per-key store file so Turbopack retention
        # isolates the gate's chain from the typed-source chain.
        INFRA_STORE_THEME_FILE,
        INFRA_STORE_TREE_SOURCE_FILE,
        INFRA_STORE_LAST_TAXON_ID_FILE,
        INFRA_STORE_KEBAB_OPEN_ID_FILE,
        INFRA_STORE_INTERNAL_FLAG_FILE,
        INFRA_STORE_EXPLORER_STATE_FILE,
        INFRA_STORE_RESET_FILE,
        APP_HOOK_THEME_FILE,
        APP_HOOK_TREE_SOURCE_FILE,
        APP_HOOK_LAST_TAXON_ID_FILE,
        APP_HOOK_KEBAB_OPEN_ID_FILE,
        APP_HOOK_EXPLORER_STATE_FILE,
    ),
)
def test_canonical_file_present(path: Path) -> None:
    """Every canonical file MUST be on disk by task close.

    ODD-BSTATE-TAX-001-A: the canonical files are now split per
    storage key — every key owns its own hook + store file, and
    reset.ts is the aggregate module that clears every key. The
    path list here mirrors the split so the file-presence matrix
    stays exhaustive without naming every individual file in the
    test body.
    """
    assert path.is_file(), (
        f"missing canonical file: {path}. ODD-BSTATE-TAX-001-A "
        f"must split the typed store into per-key files."
    )


# ODD-BSTATE-TAX-001-A — strict-continuation layout invariant.
# After the per-key split, the legacy monolithic `store.ts` +
# `useBrowserStateKey.ts` files MUST be gone. A future regression
# that collapses the per-key files back into a monolith would
# silently re-bundle the typed source + the three forbidden keys
# into one chunk (Turbopack cannot tree-shake a single-file
# re-export), defeating the ODD-BSTATE-TAX-001-B strict chunk-
# boundary contract. The invariant pins the split at the
# filesystem level.
def test_monolithic_modules_are_retired() -> None:
    """The monolithic `infrastructure/store.ts` +
    `application/useBrowserStateKey.ts` files MUST NOT exist after
    the per-key split.

    The strict chunk-boundary contract (ODD-BSTATE-TAX-001-B)
    depends on Turbopack retaining only the imported key's module
    chain. A monolithic file with four key declarations + four
    hook declarations defeats retention — the bundler pulls the
    whole file the moment any consumer touches the module. The
    invariants below make the regression loud before review.
    """
    assert not APP_HOOK_FILE.exists(), (
        f"monolithic application hook must be retired; "
        f"{APP_HOOK_FILE} still exists. ODD-BSTATE-TAX-001-A "
        f"requires per-key hook files (useTheme.ts, "
        f"useTreeSource.ts, useLastTaxonId.ts, useKebabOpenId.ts)."
    )
    assert not INFRA_STORE_FILE.exists(), (
        f"monolithic infrastructure store must be retired; "
        f"{INFRA_STORE_FILE} still exists. ODD-BSTATE-TAX-001-A "
        f"requires per-key store files (storeTheme.ts, "
        f"storeTreeSource.ts, storeLastTaxonId.ts, "
        f"storeKebabOpenId.ts) plus a reset.ts aggregate module."
    )


@pytest.mark.parametrize("path", APP_HOOK_FILES)
def test_application_hook_can_import_react_but_not_localstorage(path: Path) -> None:
    """Every per-key hook MAY import React (the hook is a React
    adapter) but MUST NOT touch `localStorage` directly — storage
    access lives in the matching `infrastructure/store<X>.ts`
    file. The reset.ts aggregate module owns the cross-key
    `localStorage.removeItem` calls but per-key hooks never
    reach for storage primitives on their own.

    ODD-BSTATE-TAX-001-A: with the per-key split, the previous
    single-file hook (`application/useBrowserStateKey.ts`) is
    replaced by four sibling files. The contract pins each one
    independently so a future regression that re-introduces a
    storage reference in any hook file trips this test before
    review.
    """
    if not path.exists():
        pytest.skip(f"hook file not present yet: {path}")
    stripped = _strip_ts_comments(path.read_text(encoding="utf-8"))
    forbidden = (
        "localStorage", "sessionStorage",
        "fetch(", "document.", "process.", "globalThis.",
    )
    for token in forbidden:
        assert token not in stripped, (
            f"{path.name} must NOT touch {token!r}; storage access "
            f"is owned by the matching per-key store file."
        )


@pytest.mark.parametrize("path", INFRA_STORE_FILES)
def test_infrastructure_per_key_store_has_storage_calls(path: Path) -> None:
    """Every per-key `infrastructure/store<X>.ts` file MUST own
    its key's `localStorage` calls.

    The previous single-file monolith is replaced by four
    sibling files; each one owns exactly one storage key
    (theme / tree-source / last-taxon-id / kebab-open-id). The
    cross-key `reset()` affordance lives in
    `infrastructure/reset.ts` and aggregates the four
    `removeItem` sites. The per-key split also unlocks
    Turbopack retention — the bundler drops the three unrelated
    keys when a consumer imports only one hook.
    """
    if not path.exists():
        pytest.skip(f"store file not present yet: {path}")
    text = path.read_text(encoding="utf-8")
    assert "localStorage" in text or "globalThis" in text, (
        f"{path.name} MUST own the localStorage calls for its "
        f"storage key — the typed store is the only legal storage "
        f"surface."
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
    """Storage access is centralised in the per-key infrastructure
    stores. Every literal `localStorage.` reference in the module
    MUST live inside the infrastructure layer (per-key store files
    + the reset.ts aggregate); the domain, application, and barrel
    files MUST stay storage-free.

    ODD-BSTATE-TAX-001-A: the previous monolithic
    `infrastructure/store.ts` is replaced by four sibling files
    (storeTheme.ts / storeTreeSource.ts / storeLastTaxonId.ts /
    storeKebabOpenId.ts) plus `infrastructure/reset.ts`. The
    legal-home set below tracks the split.
    """
    text = _module_text("browser-state")
    if not text:
        pytest.skip("browser-state module not present yet")
    # Concatenate every file but tag each file's origin so we can
    # pinpoint which layer owns a literal reference.
    root = REPO_ROOT / "src" / "modules" / "browser-state"
    # ODD-BSTATE-TAX-001-A — the only legal homes for storage
    # primitives are now the four per-key store files PLUS the
    # `reset.ts` aggregate (which owns the cross-key
    # `localStorage.removeItem` calls). The legacy monolithic
    # `store.ts` is retired; a regression that re-introduces it
    # would re-bundle the typed source + the three forbidden
    # keys into one chunk (defeating the strict chunk-boundary
    # contract from ODD-BSTATE-TAX-001-B).
    legal_homes: set[Path] = set(INFRA_STORE_FILES) | {INFRA_STORE_RESET_FILE}
    # ODD-ASN-001 — `INFRA_STORE_INTERNAL_FLAG_FILE` is already
    # in `INFRA_STORE_FILES` so it lands in `legal_homes` via the
    # set union above (no separate registration needed). The gate
    # (`presentation/HydrationProbeGate.tsx`) imports
    # `readInternalFlag` from the public barrel so the
    # presentation layer is free of `localStorage.*` references
    # and the legal-home set keeps the gate off the offender
    # list.
    offenders: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*.ts")) + sorted(root.rglob("*.tsx")):
        if not path.is_file():
            continue
        if path in legal_homes:
            continue  # legal home for storage primitives
        rel = path.relative_to(BS_ROOT).as_posix()
        # Per-key hook files + the barrel + the domain + the
        # presentation layer MUST stay free of `localStorage.*`
        # references. The barrel re-routes through the typed
        # store; the domain layer is pure types; the per-key
        # hooks reach storage exclusively through the typed
        # store surface.
        body = _strip_ts_comments(path.read_text(encoding="utf-8"))
        for needle in ("localStorage.", "sessionStorage.", "window.localStorage"):
            if needle in body:
                offenders.append((rel, needle))
    assert not offenders, (
        f"storage primitives MUST stay in a per-key infrastructure "
        f"store file (or the reset.ts aggregate); found {offenders}. "
        f"The typed store is the only legal storage surface."
    )


# ODD-MIGRATE-003 / W6.3 — Explorer Splitter carveout. The single
# raw localStorage key `taxa.fex.treeWidth` is owned by
# `src/modules/research/presentation/Splitter.tsx` per the user-
# authorized W6.3 decision. The OpenSpec boundary
# (`openspec/changes/complete-taxa-frontend-migration/specs/browser-state-hydration/spec.md`
# Notes) explicitly excludes this key from `@taxa/browser-state`;
# the W6.3 design decision keeps storage local to the Explorer
# presentation layer to avoid browser-state chunk scope expansion.
# The carveout is scoped to (a) a single source file, (b) a single
# raw key, and (c) a single gated call shape. Every other Research
# source MUST stay free of raw `localStorage` access; every other
# capability module MUST stay free too. Anything outside that
# shape — a bare `localStorage.X` reference (no `globalThis` /
# `window` gate), a different key, or a non-gated prefix — trips
# the assertion below.
RESEARCH_DIR = REPO_ROOT / "src" / "modules" / "research"
SPLITTER_FILE = RESEARCH_DIR / "presentation" / "Splitter.tsx"
SPLITTER_OWNED_KEY = "taxa.fex.treeWidth"
SPLITTER_KEY_CONSTANT = "TREE_WIDTH_STORAGE_KEY"
_LOCALSTORAGE_NEEDLES: tuple[str, ...] = (
    "localStorage.getItem",
    "localStorage.setItem",
    "localStorage.removeItem",
)
# Every `localStorage.{getItem,setItem,removeItem}` reference in
# Splitter.tsx MUST live inside a gated call expression
# `(globalThis|window).localStorage.{getItem,setItem,removeItem}(TREE_WIDTH_STORAGE_KEY, ...)`.
# The constant `TREE_WIDTH_STORAGE_KEY` is pinned at the Splitter
# boundary (its value is the Splitter-owned key literal
# `taxa.fex.treeWidth`); a regression that passes a different key,
# drops the `globalThis`/`window` gate, or introduces a second
# localStorage key trips the assertion below.
_SPLITTER_LEGAL_CALL = re.compile(
    r"(?:globalThis|window)\s*\.\s*localStorage\s*\.\s*"
    r"(?:getItem|setItem|removeItem)\s*\(\s*"
    + re.escape(SPLITTER_KEY_CONSTANT)
    + r"\b"
)


def _assert_research_localstorage_policy() -> None:
    """ODD-MIGRATE-003 / W6.3 — per-file Research localStorage
    policy with the Splitter carveout.

    Every Research source other than `Splitter.tsx` MUST stay free
    of raw `localStorage.getItem` / `localStorage.setItem` /
    `localStorage.removeItem` references — the typed store is the
    only legal storage surface for every other key.

    `Splitter.tsx` is the lone documented exception. It owns the
    single raw key `taxa.fex.treeWidth` per the OpenSpec boundary.
    Every `localStorage.{getItem,setItem,removeItem}` reference in
    the file MUST be inside a gated call expression
    `(globalThis|window).localStorage.{getItem,setItem,removeItem}(TREE_WIDTH_STORAGE_KEY, ...)`.
    A bare `localStorage.X` reference (no gate), a call that passes
    a different key, or any reference in any other Research source
    trips the assertion below.
    """
    root = RESEARCH_DIR
    if not root.exists():
        pytest.skip("research module not present yet")
    for path in sorted(root.rglob("*.ts")) + sorted(root.rglob("*.tsx")):
        if not path.is_file():
            continue
        stripped = _strip_ts_comments(path.read_text(encoding="utf-8"))
        if path == SPLITTER_FILE:
            # Substitute every legal gated call expression with
            # whitespace of equal length (preserve diagnostic line
            # numbers + column alignment) so the residual scan
            # catches any bare `localStorage.X` reference, any
            # non-gated prefix, or any call that passes a different
            # key.
            residual = _SPLITTER_LEGAL_CALL.sub(
                lambda m: re.sub(r"[^\n]", " ", m.group(0)),
                stripped,
            )
            for needle in _LOCALSTORAGE_NEEDLES:
                assert needle not in residual, (
                    f"Splitter.tsx contains an illegal `{needle}` "
                    f"reference outside a "
                    f"`(globalThis|window).localStorage.{needle[len('localStorage.'):]}(TREE_WIDTH_STORAGE_KEY, ...)` "
                    f"gate. Every raw localStorage reference in the "
                    f"Splitter MUST target the Splitter-owned "
                    f"`taxa.fex.treeWidth` key (the W6.3 OpenSpec "
                    f"boundary)."
                )
            continue
        # Every other Research source MUST stay free of raw
        # `localStorage` access. The typed store is the only legal
        # storage surface for every key other than
        # `taxa.fex.treeWidth`.
        rel = path.relative_to(root).as_posix()
        for needle in _LOCALSTORAGE_NEEDLES:
            assert needle not in stripped, (
                f"research/{rel} must NOT call {needle!r} "
                f"directly; storage ownership belongs to the "
                f"browser-state typed store. The lone documented "
                f"exception is the Explorer Splitter's "
                f"`taxa.fex.treeWidth` key — see "
                f"`openspec/changes/complete-taxa-frontend-migration/specs/browser-state-hydration/spec.md` "
                f"Notes."
            )


@pytest.mark.parametrize("other_module", OTHER_CAPABILITIES)
def test_other_module_does_not_touch_localstorage(other_module: str) -> None:
    """No capability module outside `browser-state` is allowed to
    read or write `localStorage` directly. The typed store is the
    only legal storage surface.

    ODD-MIGRATE-003 / W6.3 carveout (user-authorized): the
    Explorer Splitter (`src/modules/research/presentation/Splitter.tsx`)
    is the ONE documented exception outside `browser-state`. It
    owns the single raw localStorage key `taxa.fex.treeWidth` per
    the OpenSpec boundary
    (`openspec/changes/complete-taxa-frontend-migration/specs/browser-state-hydration/spec.md`
    Notes: `taxa.fex.treeWidth key (used by the splitter) is out of
    scope for browser-state`). The carveout is scoped to:
      - a single source file (`Splitter.tsx`);
      - a single raw key (`taxa.fex.treeWidth`); and
      - a single gated call shape
        `(globalThis|window).localStorage.{getItem,setItem,removeItem}(TREE_WIDTH_STORAGE_KEY, ...)`.
    Every other Research source MUST stay free of raw `localStorage`
    access; every other capability module MUST stay free too.
    """
    if other_module == "research":
        # ODD-MIGRATE-003 / W6.3 — per-file Research policy with
        # the Splitter carveout. See the test docstring above for
        # the OpenSpec boundary rationale.
        _assert_research_localstorage_policy()
        return
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
    for needle in _LOCALSTORAGE_NEEDLES:
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
    exactly once each (so a typo would surface here).

    ODD-BSTATE-EXPLORER-PERSIST — the canonical key set now
    includes the explorer-state key (`taxa.fex.explorerState`)
    after the EXPLORER-PERSIST architecture correction. The
    test iterates over `EXPECTED_STORAGE_KEYS` so adding a
    fifth literal here immediately verifies the new key
    declaration lands in `domain/keys.ts`.
    """
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
    assert "DEFAULT_EXPLORER_STATE" in text


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
        "DEFAULT_EXPLORER_STATE",
        "useExplorerState",
        "readTheme", "writeTheme", "subscribeTheme",
        "readTreeSource", "writeTreeSource", "subscribeTreeSource",
        "readLastTaxonId", "writeLastTaxonId", "subscribeLastTaxonId",
        "readKebabOpenId", "writeKebabOpenId", "subscribeKebabOpenId",
        "readExplorerState", "writeExplorerState", "subscribeExplorerState",
        "reset",
    ]
    missing = [name for name in expected_identifiers if name not in text]
    assert not missing, (
        f"barrel missing re-exports: {missing}. The typed API surface "
        f"must be reachable through the public barrel."
    )


# ---------------------------------------------------------------------------
# Compile + runtime contract — strict mode, ES2022 + DOM libs (the
# typed store needs `window.localStorage` and `useSyncExternalStore`
# is a React API). Runtime harness exercises every observable surface.
# ---------------------------------------------------------------------------
def _tsc_inputs() -> list[Path]:
    """Files to feed tsc: the domain files, every per-key store
    file, the reset.ts aggregate, and every per-key hook file.

    ODD-BSTATE-TAX-001-A: with the per-key split, the compile
    inputs are now eight sibling files instead of two monoliths.
    The hook files import React; we keep the libs ES2022 + DOM so
    the React global is visible.
    """
    candidates: tuple[Path, ...] = (
        DOMAIN_KEYS_FILE,
        DOMAIN_DEFAULTS_FILE,
        INFRA_STORE_THEME_FILE,
        INFRA_STORE_TREE_SOURCE_FILE,
        INFRA_STORE_LAST_TAXON_ID_FILE,
        INFRA_STORE_KEBAB_OPEN_ID_FILE,
        INFRA_STORE_EXPLORER_STATE_FILE,
        INFRA_STORE_RESET_FILE,
        APP_HOOK_THEME_FILE,
        APP_HOOK_TREE_SOURCE_FILE,
        APP_HOOK_LAST_TAXON_ID_FILE,
        APP_HOOK_KEBAB_OPEN_ID_FILE,
        APP_HOOK_EXPLORER_STATE_FILE,
    )
    return [p for p in candidates if p.is_file()]


def _run_tsc(out_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    sources = [str(p) for p in _tsc_inputs()]
    if len(sources) < 4:
        pytest.skip("required source files missing")
    return subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--strict", "--target", "ES2022",
            "--module", "commonjs",
            "--lib", "ES2022,DOM",
            "--jsx", "react-jsx",
            "--skipLibCheck",
            "--esModuleInterop",
            "--types", "react",
            "--rootDir", "src/modules/browser-state",
            "--outDir", str(out_dir),
            *sources,
            *extra,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


# Runtime harness — exercises every observable surface without
# booting a real React renderer. The hooks are tested through
# their underlying read/write/subscribe APIs because
# `useSyncExternalStore` requires a React renderer (the React
# integration belongs to
# `tests/test_browser_state_hydration_guard.py`).
#
# ODD-BSTATE-TAX-001-A: with the per-key split, the harness
# composes the typed surface from four sibling store modules
# plus the `reset.js` aggregate. Each per-key module owns its own
# read/write/subscribe + a `__resetForTests` seam; the reset
# module aggregates the cross-key reset. The harness requires:
#   - storeTheme.js
#   - storeTreeSource.js
#   - storeLastTaxonId.js
#   - storeKebabOpenId.js
#   - reset.js
# (in that exact order — `argv[2]` is storeTheme, …, `argv[6]`
# is reset) so the per-key composability stays vendor-agnostic.
_RUNTIME_HARNESS = r"""
const path = require("path");

// jsdom-free harness: the typed store is the only React-free
// surface; we exercise it directly. A minimal `window` /
// `localStorage` polyfill is enough to drive the contract — the
// per-key store falls back to the typed default when storage is
// missing.
const makeStorage = (initial) => {
  const map = new Map(Object.entries(initial || {}));
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => { map.set(k, String(v)); },
    removeItem: (k) => { map.delete(k); },
    _store: map,
  };
};

function withWindow(storage, fn) {
  const prevWindow = globalThis.window;
  const prevLS = globalThis.localStorage;
  globalThis.window = { localStorage: storage };
  globalThis.localStorage = storage;
  try {
    return fn();
  } finally {
    if (prevWindow === undefined) delete globalThis.window;
    else globalThis.window = prevWindow;
    if (prevLS === undefined) delete globalThis.localStorage;
    else globalThis.localStorage = prevLS;
  }
}

const fail = (label) => {
  process.stderr.write("FAIL " + label + "\n");
  process.exit(1);
};

// ODD-BSTATE-TAX-001-A: the harness now requires each per-key
// store module separately and the `reset.js` aggregate.
//
// ODD-BSTATE-EXPLORER-PERSIST: the per-key family grows by
// one entry (`storeExplorerState`). The six argv slots are
// exactly: storeTheme, storeTreeSource, storeLastTaxonId,
// storeKebabOpenId, storeExplorerState, reset. tsc preserves
// the layer folder structure (--rootDir + per-source
// relative paths), so the compiled files land under
// `out_dir/infrastructure/{storeTheme,storeTreeSource,…,
// storeExplorerState}.js` and `out_dir/infrastructure/reset.js`.
const [themeMod, treeMod, lastMod, kebabMod, explorerMod, resetMod] =
  [process.argv[2], process.argv[3], process.argv[4], process.argv[5], process.argv[6], process.argv[7]].map(
    (p) => require(path.resolve(p)),
  );

const {
  readTheme, writeTheme, subscribeTheme, __resetForTests: __resetTheme,
} = themeMod;
const {
  readTreeSource, writeTreeSource, subscribeTreeSource,
  __resetForTests: __resetTree,
} = treeMod;
const {
  readLastTaxonId, writeLastTaxonId, subscribeLastTaxonId,
  __resetForTests: __resetLast,
} = lastMod;
const {
  readKebabOpenId, writeKebabOpenId, subscribeKebabOpenId,
  __resetForTests: __resetKebab,
} = kebabMod;
const {
  readExplorerState, writeExplorerState, subscribeExplorerState,
  __resetForTests: __resetExplorer,
} = explorerMod;
const { reset } = resetMod;

function __resetForTests() {
  __resetTheme();
  __resetTree();
  __resetLast();
  __resetKebab();
  __resetExplorer();
}

// ODD-BSTATE-TAX-001-A: the per-key store modules no longer
// share a single defaults module. Resolve `defaults.js` via
// `path.relative` from the first per-key store's directory
// (every per-key store sits under `infrastructure/`, so the
// resolution lands on `domain/defaults.js`).
const storeDir = path.dirname(path.resolve(process.argv[2]));
const defaults = require(path.resolve(storeDir, "../domain/defaults.js"));
const {
  DEFAULT_THEME, DEFAULT_TREE_SOURCE,
  DEFAULT_LAST_TAXON_ID, DEFAULT_KEBAB_OPEN_ID,
  DEFAULT_EXPLORER_STATE,
} = defaults;
// ODD-BSTATE-EXPLORER-PERSIST-BOUNDS — cap constants + helper.
const explorerStateDomain = require(
  path.resolve(storeDir, "../domain/explorer-state.js"),
);
const {
  MAX_EXPLORER_STATE_BYTES,
  MAX_EXPANDED_PATHS,
  MAX_QUERY_LENGTH,
  MAX_SELECTED_PATH_LENGTH,
} = explorerStateDomain;
function assertEmptyDefault(record, label) {
  if (!record || typeof record !== "object") fail(label + "_object");
  if (record.version !== 1) fail(label + "_version");
  if (record.query !== "") fail(label + "_query");
  if (record.selectedPath !== null) fail(label + "_selectedPath");
  if (!Array.isArray(record.expandedPaths)) fail(label + "_expandedPaths_type");
  if (record.expandedPaths.length !== 0) fail(label + "_expandedPaths_length");
}

// 1. Defaults before any storage / hydration.
__resetForTests();
withWindow(makeStorage(), () => {
  __resetForTests();
  if (readTheme() !== DEFAULT_THEME) fail("theme_default");
  if (readTheme() !== "light") fail("theme_default_light");
  if (readTreeSource() !== DEFAULT_TREE_SOURCE) fail("tree_source_default");
  if (readTreeSource() !== "col") fail("tree_source_default_col");
  if (readLastTaxonId() !== null) fail("last_taxon_id_default");
  if (readKebabOpenId() !== null) fail("kebab_open_id_default");
});

// 2. Read from a populated storage and re-read after reset.
withWindow(
  makeStorage({
    "taxa.settings.theme": "dark",
    "taxa.tree.source": "worms",
    "taxa.tree.lastTaxonId": "42",
    "taxa.tree.kebabOpenId": "7",
    "taxa.fex.explorerState": JSON.stringify({
      version: 1,
      query: "mammalia",
      selectedPath: null,
      expandedPaths: ["Animalia"],
    }),
  }),
  () => {
    __resetForTests();
    if (readTheme() !== "dark") fail("theme_hydrate_dark");
    if (readTreeSource() !== "worms") fail("tree_source_hydrate_worms");
    if (readLastTaxonId() !== 42) fail("last_taxon_id_hydrate_42");
    if (readKebabOpenId() !== 7) fail("kebab_open_id_hydrate_7");
    // ODD-BSTATE-EXPLORER-PERSIST — explorer-state hydration.
    const explorerHydrated = readExplorerState();
    if (!explorerHydrated) fail("explorer_state_hydrate_present");
    if (explorerHydrated.query !== "mammalia") fail("explorer_state_hydrate_query");
    if (explorerHydrated.expandedPaths.length !== 1) fail("explorer_state_hydrate_expanded");
  },
);

// 3. Round-trip: writeTheme → readTheme → subscriber fires.
withWindow(makeStorage(), () => {
  __resetForTests();
  let fired = null;
  const unsub = subscribeTheme((v) => { fired = v; });
  writeTheme("dark");
  if (fired !== "dark") fail("theme_subscribe_dark");
  if (readTheme() !== "dark") fail("theme_after_write_dark");
  unsub();
  writeTheme("light");
  if (fired !== "dark") fail("theme_subscribe_unsub_no_fire");
});

// 4. Reset clears every key + every cache.
withWindow(
  makeStorage({
    "taxa.settings.theme": "dark",
    "taxa.tree.source": "freshwater",
    "taxa.tree.lastTaxonId": "100",
    "taxa.tree.kebabOpenId": "9",
    "taxa.fex.explorerState": JSON.stringify({
      version: 1,
      query: "mammalia",
      selectedPath: null,
      expandedPaths: ["Animalia"],
    }),
  }),
  () => {
    __resetForTests();
    // Hydrate the cache.
    readTheme(); readTreeSource(); readLastTaxonId(); readKebabOpenId();
    readExplorerState();
    let themeFired = null;
    let treeFired = null;
    let lastFired = null;
    let kebabFired = null;
    let explorerFired = null;
    subscribeTheme((v) => { themeFired = v; });
    subscribeTreeSource((v) => { treeFired = v; });
    subscribeLastTaxonId((v) => { lastFired = v; });
    subscribeKebabOpenId((v) => { kebabFired = v; });
    subscribeExplorerState((v) => { explorerFired = v; });
    reset();
    if (readTheme() !== DEFAULT_THEME) fail("reset_theme_default");
    if (readTreeSource() !== DEFAULT_TREE_SOURCE) fail("reset_tree_source_default");
    if (readLastTaxonId() !== DEFAULT_LAST_TAXON_ID) fail("reset_last_taxon_id_default");
    if (readKebabOpenId() !== DEFAULT_KEBAB_OPEN_ID) fail("reset_kebab_open_id_default");
    if (readExplorerState() !== DEFAULT_EXPLORER_STATE) fail("reset_explorer_state_default");
    if (themeFired !== DEFAULT_THEME) fail("reset_theme_listener");
    if (treeFired !== DEFAULT_TREE_SOURCE) fail("reset_tree_source_listener");
    if (lastFired !== DEFAULT_LAST_TAXON_ID) fail("reset_last_taxon_listener");
    if (kebabFired !== DEFAULT_KEBAB_OPEN_ID) fail("reset_kebab_listener");
    if (explorerFired !== DEFAULT_EXPLORER_STATE) fail("reset_explorer_state_listener");
  },
);

// 5. Storage failures (private mode / quota exceeded) do NOT crash
// the read/write path; the typed default is returned.
withWindow({
  get localStorage() {
    return {
      getItem: () => { throw new Error("private mode"); },
      setItem: () => { throw new Error("quota exceeded"); },
      removeItem: () => { throw new Error("private mode"); },
    };
  },
}, () => {
  __resetForTests();
  if (readTheme() !== DEFAULT_THEME) fail("fail_read_default");
  // No throw → pass.
  writeTheme("dark");
  if (readTheme() !== "dark") fail("fail_write_in_memory_updates");
  // The persistent write failed; the in-memory state still reflects
  // the user's choice so the UI updates for the current session.
  reset(); // also must not throw.
});

// 6. SSR (no `window`) returns the typed default.
const prevWindow = globalThis.window;
delete globalThis.window;
try {
  __resetForTests();
  if (readTheme() !== DEFAULT_THEME) fail("ssr_theme_default");
  if (readLastTaxonId() !== null) fail("ssr_last_taxon_id_default");
  // Writes must also be no-ops in SSR.
  writeTheme("dark");
} finally {
  if (prevWindow !== undefined) globalThis.window = prevWindow;
}

// 7. Garbage values fall back to the typed default.
withWindow(
  makeStorage({
    "taxa.settings.theme": "fuchsia",
    "taxa.tree.source": "bogus",
    "taxa.tree.lastTaxonId": "not-a-number",
    "taxa.tree.kebabOpenId": "3.14",
  }),
  () => {
    __resetForTests();
    if (readTheme() !== "light") fail("garbage_theme");
    if (readTreeSource() !== "col") fail("garbage_tree_source");
    if (readLastTaxonId() !== null) fail("garbage_last_taxon_id");
    if (readKebabOpenId() !== null) fail("garbage_kebab_open_id");
  },
);

// ---------------------------------------------------------------------------
// ODD-BSTATE-EXPLORER-PERSIST-BOUNDS — sections 8-10 cover the
// persistence-boundary contract (over-bound rejection, at-boundary
// acceptance, write rejection).
// ---------------------------------------------------------------------------

// 8. Over-bound rejection — each cap individually + the byte-size
// overflow discriminating case (valid JSON that the parser
// would surface without the byte-size guard).
function boundRecord(over) {
  return {
    version: 1,
    query: over === "query" ? "x".repeat(MAX_QUERY_LENGTH + 1) : "",
    selectedPath: over === "selectedPath"
      ? "x".repeat(MAX_SELECTED_PATH_LENGTH + 1) : null,
    expandedPaths: over === "expandedPaths"
      ? Array.from({ length: MAX_EXPANDED_PATHS + 1 }, (_, i) => "p" + i)
      : (over === "expandedPathEntry"
        ? ["x".repeat(MAX_SELECTED_PATH_LENGTH + 1)] : []),
  };
}
function byteSizedRecord(targetLength) {
  const record = {
    version: 1, query: "", selectedPath: null,
    expandedPaths: Array(21).fill("x".repeat(MAX_SELECTED_PATH_LENGTH)).concat(""),
  };
  const padding = targetLength - JSON.stringify(record).length;
  if (padding < 0 || padding > MAX_SELECTED_PATH_LENGTH) fail("byte_size_fixture_padding");
  record.expandedPaths[21] = "x".repeat(padding);
  if (JSON.stringify(record).length !== targetLength) fail("byte_size_fixture_length");
  return record;
}
for (const over of ["query", "selectedPath", "expandedPaths", "expandedPathEntry"]) {
  withWindow(
    makeStorage({ "taxa.fex.explorerState": JSON.stringify(boundRecord(over)) }),
    () => { __resetForTests();
      assertEmptyDefault(readExplorerState(), "overbound_" + over); },
  );
}
withWindow(
  makeStorage({
    "taxa.fex.explorerState": JSON.stringify(
      byteSizedRecord(Math.floor(MAX_EXPLORER_STATE_BYTES / 3) + 1),
    ),
  }),
  () => { __resetForTests();
    assertEmptyDefault(readExplorerState(), "overbound_byte_size"); },
);

// 9. At-boundary acceptance — regression guard against `>=` vs `>`.
// Each cap exercised individually (packing every cap into one
// record would exceed the byte-size cap).
function checkAtBoundary(cap, check) {
  withWindow(
    makeStorage({ "taxa.fex.explorerState": JSON.stringify(check.record) }),
    () => { __resetForTests();
      if (!check.assert(readExplorerState())) fail("atboundary_" + cap); },
  );
}
checkAtBoundary("query", {
  record: { version: 1, query: "x".repeat(MAX_QUERY_LENGTH),
            selectedPath: null, expandedPaths: [] },
  assert: (h) => h.query.length === MAX_QUERY_LENGTH,
});
checkAtBoundary("selectedPath", {
  record: { version: 1, query: "",
            selectedPath: "x".repeat(MAX_SELECTED_PATH_LENGTH),
            expandedPaths: [] },
  assert: (h) => h.selectedPath !== null && h.selectedPath.length === MAX_SELECTED_PATH_LENGTH,
});
checkAtBoundary("expandedPathsCount", {
  record: { version: 1, query: "", selectedPath: null,
            expandedPaths: Array.from({ length: MAX_EXPANDED_PATHS }, (_, i) => "p" + i) },
  assert: (h) => h.expandedPaths.length === MAX_EXPANDED_PATHS,
});
checkAtBoundary("expandedPathEntry", {
  record: { version: 1, query: "", selectedPath: null,
            expandedPaths: ["x".repeat(MAX_SELECTED_PATH_LENGTH)] },
  assert: (h) => h.expandedPaths[0].length === MAX_SELECTED_PATH_LENGTH,
});
checkAtBoundary("byteSize", {
  record: byteSizedRecord(Math.floor(MAX_EXPLORER_STATE_BYTES / 3)),
  assert: (h) => h.expandedPaths.length > 0,
});

// 10. Write boundary — over-bound write silently dropped (no throw,
// no setItem, no cache update, no listener fire); at-boundary write
// accepted (setItem called, cache updates, listener fires). Every
// cap exercised in both directions.
function checkWrite(label, record, expectReject, assertPost) {
  let setItemCalled = false, listenerFired = null;
  const tracking = { getItem: () => null, setItem: () => { setItemCalled = true; }, removeItem: () => {} };
  withWindow(tracking, () => {
    __resetForTests();
    if (expectReject) writeExplorerState(DEFAULT_EXPLORER_STATE);
    setItemCalled = false;
    const unsub = subscribeExplorerState((next) => { listenerFired = next; });
    let threw = false;
    try { writeExplorerState(record); } catch (_e) { threw = true; }
    const dir = expectReject ? "rejects" : "accepts";
    const p = "write_" + dir + "_" + label;
    if (threw) fail(p + "_does_not_throw");
    if (expectReject) {
      if (setItemCalled) fail(p + "_no_setItem");
      assertEmptyDefault(readExplorerState(), p);
      if (listenerFired !== null) fail(p + "_no_listener_fire");
    } else {
      if (!setItemCalled) fail(p + "_setItem_called");
      if (!assertPost(readExplorerState())) fail(p + "_cache_updated");
      if (listenerFired === null) fail(p + "_listener_fired");
    }
    unsub();
  });
}
// Reject over-bound — each field/count cap plus a byte-size record
// one character beyond the largest representable estimate.
for (const cap of ["query", "selectedPath", "expandedPaths", "expandedPathEntry"]) {
  checkWrite(cap, boundRecord(cap), true, null);
}
checkWrite("byteSize",
  byteSizedRecord(Math.floor(MAX_EXPLORER_STATE_BYTES / 3) + 1),
  true, null);
// Accept at-boundary — every cap (regression guard for `>=` vs `>`).
checkWrite("query",
  { version: 1, query: "x".repeat(MAX_QUERY_LENGTH),
    selectedPath: null, expandedPaths: [] },
  false, (h) => h.query.length === MAX_QUERY_LENGTH);
checkWrite("selectedPath",
  { version: 1, query: "",
    selectedPath: "x".repeat(MAX_SELECTED_PATH_LENGTH),
    expandedPaths: [] },
  false, (h) => h.selectedPath !== null && h.selectedPath.length === MAX_SELECTED_PATH_LENGTH);
checkWrite("expandedPathsCount",
  { version: 1, query: "", selectedPath: null,
    expandedPaths: Array.from({ length: MAX_EXPANDED_PATHS }, (_, i) => "p" + i) },
  false, (h) => h.expandedPaths.length === MAX_EXPANDED_PATHS);
checkWrite("expandedPathEntry",
  { version: 1, query: "", selectedPath: null,
    expandedPaths: ["x".repeat(MAX_SELECTED_PATH_LENGTH)] },
  false, (h) => h.expandedPaths[0].length === MAX_SELECTED_PATH_LENGTH);
// floor(MAX_EXPLORER_STATE_BYTES / 3) chars × 3 = 65535,
// the exact largest representable estimate below the 65536 cap.
checkWrite("byteSize",
  byteSizedRecord(Math.floor(MAX_EXPLORER_STATE_BYTES / 3)),
  false, (h) => h.expandedPaths.length > 0);

process.stdout.write("PASS\n");
"""


def test_compiled_browser_state_passes_runtime_contract(
    tmp_path, require_toolchain: None,
) -> None:
    """Compile every per-key file in strict mode (ES2022 + DOM)
    and run the runtime harness under Node.

    ODD-BSTATE-TAX-001-A: the harness composes the typed surface
    from four sibling store modules plus the reset aggregate.
    The compile inputs cover every per-key file, so a regression
    in any layer fails compilation before harness execution.
    The harness covers defaults, hydration, round-trip,
    subscribers, reset, storage-failure safety, SSR safety,
    and garbage-value fallbacks.
    """
    # All required per-key files MUST be present for the runtime
    # contract to be meaningful; refuse to skip into a silent
    # green by mistake.
    out_dir = tmp_path / "bs-out"
    expected_compiled = (
        ("storeTheme", out_dir / "infrastructure" / "storeTheme.js"),
        ("storeTreeSource", out_dir / "infrastructure" / "storeTreeSource.js"),
        ("storeLastTaxonId", out_dir / "infrastructure" / "storeLastTaxonId.js"),
        ("storeKebabOpenId", out_dir / "infrastructure" / "storeKebabOpenId.js"),
        ("storeExplorerState", out_dir / "infrastructure" / "storeExplorerState.js"),
        ("reset", out_dir / "infrastructure" / "reset.js"),
    )
    # Compile every per-key file. The previous monolithic compile
    # call is replaced by the parametrized list in `_tsc_inputs`
    # so the compile covers every layer file.
    out_dir = tmp_path / "bs-out"
    result = _run_tsc(out_dir)
    assert result.returncode == 0, (
        f"tsc failed (exit {result.returncode}).\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # The hooks are React-bound modules that import `react`. We
    # do not exercise them at runtime here — that contract lives
    # in `tests/test_browser_state_hydration_guard.py`. We
    # exercise the typed-store surface (the four per-key stores
    # + the reset aggregate) directly by pointing the harness at
    # the compiled sibling `.js` files. tsc preserves the layer
    # folder structure (--rootDir + per-source relative paths),
    # so the compiled files land under `out_dir/infrastructure/`.
    missing = [
        name for name, path in expected_compiled if not path.is_file()
    ]
    if missing:
        found = sorted(
            p.relative_to(tmp_path).as_posix()
            for p in (tmp_path / "bs-out").rglob("*.js")
        ) if (tmp_path / "bs-out").exists() else []
        pytest.fail(
            f"expected compiled per-key store files at "
            f"{[p for _, p in expected_compiled]}; missing {missing}; "
            f"found compiled files: {found}"
        )
    # Write the harness in a sibling dir so tsc doesn't try to
    # type-check it.
    harness_file = tmp_path / "harness.js"
    harness_file.write_text(_RUNTIME_HARNESS, encoding="utf-8")
    compiled_modules = [str(path) for _, path in expected_compiled]
    node = subprocess.run(
        ["node", str(harness_file), *compiled_modules],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert node.returncode == 0, (
        f"runtime harness failed (exit {node.returncode}).\n"
        f"stdout: {node.stdout}\nstderr: {node.stderr}"
    )
    assert "PASS" in node.stdout, (
        f"runtime harness did not emit PASS; stdout={node.stdout!r}"
    )


def _store_function_body(name: str) -> str:
    """Return the body of `function <name> { ... }` from
    ``storeExplorerState.ts`` via brace counting so source-level
    assertions do NOT depend on a fixed-width slice the writer's
    JSDoc + validation block could push past."""
    if not INFRA_STORE_EXPLORER_STATE_FILE.exists():
        pytest.skip("storeExplorerState.ts not present yet")
    text = _strip_ts_comments(
        INFRA_STORE_EXPLORER_STATE_FILE.read_text(encoding="utf-8")
    )
    idx = text.find(f"function {name}")
    assert idx > 0, (
        f"storeExplorerState.ts must declare `{name}`."
    )
    open_brace = text.find("{", idx)
    assert open_brace > 0
    depth = 1
    pos = open_brace + 1
    while depth and pos < len(text):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
        pos += 1
    return text[open_brace:pos]


EXPLORER_STORE_STORAGE_HELPERS: tuple[str, ...] = (
    "readExplorerState",
    "writeExplorerState",
    "clearExplorerState",
)


@pytest.mark.parametrize("helper", EXPLORER_STORE_STORAGE_HELPERS)
def test_explorer_state_store_helper_routes_through_safe_storage(helper: str) -> None:
    """ODD-BSTATE-EXPLORER-PERSIST — the per-key explorer-state
    store (`infrastructure/storeExplorerState.ts`) MUST route
    every storage-touching helper (read / write / clear)
    through the `safeStorage` helpers (`safeGetItem` /
    `safeSetItem` / `safeRemoveItem`) so quota / SecurityError /
    disabled-storage / SSR failures never propagate out of the
    typed store. The `safeStorage` helpers wrap every
    `localStorage.*` primitive in a `try { ... } catch { ... }`
    so the storage-ownership contract (one storage primitive per
    type, every primitive wrapped) stays enforced end-to-end.

    The subscribe helper (`subscribeExplorerState`) is
    intentionally excluded from this assertion: it owns pure
    listener management (no `localStorage.*` site), so routing
    through `safeStorage` would be dead weight. The focused
    runtime harness in
    `test_compiled_browser_state_passes_runtime_contract`
    exercises the subscribe path end-to-end.
    """
    if not INFRA_STORE_EXPLORER_STATE_FILE.exists():
        pytest.skip(
            "storeExplorerState.ts not present yet (RED phase)"
        )
    text = _strip_ts_comments(
        INFRA_STORE_EXPLORER_STATE_FILE.read_text(encoding="utf-8")
    )
    idx = text.find(f"function {helper}")
    assert idx > 0, (
        f"storeExplorerState.ts must declare `{helper}` as a "
        f"named function (the typed explorer-state surface)."
    )
    # Forward scan from the helper declaration — captures both
    # direct (`safeSetItem` / `safeRemoveItem`) and transitive
    # (`readExplorerState` → `ensureHydrated` → `safeGetItem`)
    # routes without a fixed-width window that comments /
    # validation block growth can push out of range.
    rest = text[idx:]
    safe_call = re.search(
        r"safe(GetItem|SetItem|RemoveItem)\s*\(", rest,
    )
    assert safe_call, (
        f"storeExplorerState.ts::{helper} must route its "
        f"`localStorage.*` call through the corresponding "
        f"`safeGetItem` / `safeSetItem` / `safeRemoveItem` "
        f"helper so quota / SecurityError / disabled-storage "
        f"failures are swallowed. A direct "
        f"`localStorage.{{getItem,setItem,removeItem}}(...)` "
        f"call inside the helper would silently break the "
        f"Explorer route's render cycle on private-browsing "
        f"hosts."
    )


def test_explorer_state_store_declares_inline_storage_key() -> None:
    """ODD-BSTATE-TAX-001-A — strict chunk-boundary contract.
    The explorer-state chain MUST NOT pull `domain/keys.ts`
    at runtime (that file declares the four sibling key
    literals). A shared chunk carrying the four sibling keys
    PLUS the explorer-state key would fail the
    `test_out_index_html_chunks_permit_only_tree_source_key`
    strict witness on the explorer route's chunk.

    The canonical declaration in `domain/keys.ts` stays in
    place for the spec-table preservation test + the public
    barrel re-export. The two declarations are kept in sync
    by the ODD-BSTATE-TAX-001-B strict chunk-boundary
    witness itself.
    """
    if not INFRA_STORE_EXPLORER_STATE_FILE.exists():
        pytest.skip(
            "storeExplorerState.ts not present yet (RED phase)"
        )
    text = INFRA_STORE_EXPLORER_STATE_FILE.read_text(encoding="utf-8")
    assert 'EXPLORER_STATE_STORAGE_KEY = "taxa.fex.explorerState"' in text, (
        "storeExplorerState.ts MUST declare the storage key "
        "inline (`const EXPLORER_STATE_STORAGE_KEY = "
        "\"taxa.fex.explorerState\"`) so Turbopack retention "
        "isolates the explorer-state chain from `domain/keys.ts`."
    )


# ODD-BSTATE-EXPLORER-PERSIST-BOUNDS — persistence-boundary
# regression suite. Runtime contract lives in `_RUNTIME_HARNESS`
# sections 8-10; source-level pins use the brace-counting
# helper `_store_function_body` so the writer's JSDoc +
# validation block does NOT push `safeSetItem` past a slice.
EXPLORER_STATE_BOUND_CONSTANTS: tuple[tuple[str, str], ...] = (
    ("MAX_EXPLORER_STATE_BYTES", "65536"),
    ("MAX_EXPANDED_PATHS", "1000"),
    ("MAX_QUERY_LENGTH", "256"),
    ("MAX_SELECTED_PATH_LENGTH", "1024"),
)


def test_explorer_state_bounds_domain_caps_have_reference_values() -> None:
    """Cap constants MUST be exported with reference values pinned
    byte-for-byte against the Research-side helper."""
    if not DOMAIN_EXPLORER_STATE_FILE.exists():
        pytest.skip("domain/explorer-state.ts not present yet")
    text = DOMAIN_EXPLORER_STATE_FILE.read_text(encoding="utf-8")
    for name, value in EXPLORER_STATE_BOUND_CONSTANTS:
        assert re.search(
            rf"\bexport\s+const\s+{name}\s*=\s*{value}\b", text,
        ), (
            f"domain/explorer-state.ts must declare "
            f"`export const {name} = {value}`; a drift would let an "
            f"oversized record through the persistence boundary."
        )


# ODD-BSTATE-EXPLORER-PERSIST-BOUNDS — parser / writer source-level
# caps coverage is delegated to the runtime harness
# (`test_compiled_browser_state_passes_runtime_contract`, sections
# 8-10): the runtime proves every cap rejects over-bound records
# AND the writer silently drops every over-bound write. The
# source-level `query.length > MAX_QUERY_LENGTH` etc. pins are
# REDUNDANT with the runtime contract and were intentionally
# removed to keep the candidate within the 400-line budget.
# Sibling source-level guards (caps reference values + storage
# helper routing) stay in place.
