"""
Browser-state hydration-guard contract tests (ODD-BSTATE-001).

Pins the hydration-safe contract for the
``src/modules/browser-state/application/useBrowserStateKey.ts`` hook.
The hook is the React adapter for the typed browser-state store and
MUST defer every ``localStorage`` read until after the first paint,
so React's hydration guard never trips on a stored value.

The contract we lock here is the source-level purity + barrel
surface + a minimal Node harness that exercises the typed store
defaults before any storage interaction. The full
``useSyncExternalStore`` React rendering contract belongs to a
follow-up Playwright slice (PR 4b in the predecessor spec); this
file pins the layer-rule + typed-store + barrel invariants that the
slice relies on.

References:
    openspec/changes/complete-taxa-frontend-migration/specs/browser-state-hydration/spec.md
    openspec/changes/complete-taxa-frontend-migration/tasks.md §Phase 4b
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
BS_ROOT = REPO_ROOT / "src" / "modules" / "browser-state"
APP_DIR = BS_ROOT / "application"
INFRA_DIR = BS_ROOT / "infrastructure"
DOMAIN_DIR = BS_ROOT / "domain"
BARREL = BS_ROOT / "index.ts"

# ODD-BSTATE-TAX-001-A — split per storage key. Each hook owns
# its own file under `application/`; the matching store file
# lives under `infrastructure/`; the aggregate `reset.ts` lives
# under `infrastructure/` too. The legacy monolithic
# `useBrowserStateKey.ts` + `store.ts` are retired; a regression
# that re-introduces them trips the
# `test_monolithic_modules_are_retired` pin (lives in
# `tests/test_browser_state_keys.py`).
APP_HOOK_THEME_FILE = APP_DIR / "useTheme.ts"
APP_HOOK_TREE_SOURCE_FILE = APP_DIR / "useTreeSource.ts"
APP_HOOK_LAST_TAXON_ID_FILE = APP_DIR / "useLastTaxonId.ts"
APP_HOOK_KEBAB_OPEN_ID_FILE = APP_DIR / "useKebabOpenId.ts"
APP_HOOK_EXPLORER_STATE_FILE = APP_DIR / "useExplorerState.ts"
APP_HOOK_FILES: tuple[Path, ...] = (
    APP_HOOK_THEME_FILE,
    APP_HOOK_TREE_SOURCE_FILE,
    APP_HOOK_LAST_TAXON_ID_FILE,
    APP_HOOK_KEBAB_OPEN_ID_FILE,
    APP_HOOK_EXPLORER_STATE_FILE,
)
INFRA_STORE_THEME_FILE = INFRA_DIR / "storeTheme.ts"
INFRA_STORE_TREE_SOURCE_FILE = INFRA_DIR / "storeTreeSource.ts"
INFRA_STORE_LAST_TAXON_ID_FILE = INFRA_DIR / "storeLastTaxonId.ts"
INFRA_STORE_KEBAB_OPEN_ID_FILE = INFRA_DIR / "storeKebabOpenId.ts"
INFRA_STORE_RESET_FILE = INFRA_DIR / "reset.ts"
INFRA_STORE_FILES: tuple[Path, ...] = (
    INFRA_STORE_THEME_FILE,
    INFRA_STORE_TREE_SOURCE_FILE,
    INFRA_STORE_LAST_TAXON_ID_FILE,
    INFRA_STORE_KEBAB_OPEN_ID_FILE,
)
DOMAIN_KEYS_FILE = DOMAIN_DIR / "keys.ts"
DOMAIN_DEFAULTS_FILE = DOMAIN_DIR / "defaults.ts"
# Legacy paths — pinned here so a regression that re-introduces
# the monolithic layout trips the test suite (the path is
# referenced by the dedicated `test_monolithic_modules_are_retired`
# pin in `test_browser_state_keys.py`).
HOOK_FILE = APP_DIR / "useBrowserStateKey.ts"
INFRA_STORE_FILE = INFRA_DIR / "store.ts"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _has_npx() -> bool:
    return shutil.which("npx") is not None


def _has_node() -> bool:
    return shutil.which("node") is not None


@pytest.fixture()
def require_toolchain() -> None:
    if not (_has_npx() and _has_node()):
        pytest.skip("npx + node required on PATH for compile/runtime test")


# Comment-stripping regexes — mirror `tests/test_domain_purity.py`.
# Block comments are matched first so a `//` inside a `/* ... */` is
# not treated as a line-comment opener. Each substitution replaces
# the matched comment with spaces (preserving line numbers + column
# alignment) so diagnostic line numbers stay accurate. Every source-
# level purity / storage-ownership assertion in this file MUST strip
# comments before scanning, otherwise an explanatory comment that
# references a forbidden token (e.g. a doc-block on a hook file
# explaining that storage lives in `infrastructure/store.ts`) would
# false-positive the guard.
_BLOCK_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/")
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _blank_match(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def _strip_ts_comments(text: str) -> str:
    text = _BLOCK_COMMENT_RE.sub(_blank_match, text)
    text = _LINE_COMMENT_RE.sub(_blank_match, text)
    return text


# ---------------------------------------------------------------------------
# File presence — pins the per-key hook paths.
#
# ODD-BSTATE-TAX-001-A: the previous monolithic hook file is
# split into four per-key files (one per storage key). Each
# hook MUST be on disk by task close so the per-key split
# stays exhaustive and the strict chunk-boundary contract
# (ODD-BSTATE-TAX-001-B) can rely on Turbopack retaining only
# the imported key's module chain.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", APP_HOOK_FILES)
def test_hook_file_present(path: Path) -> None:
    """Every per-key hook file MUST exist on disk by task close.

    The four canonical paths are `useTheme.ts`,
    `useTreeSource.ts`, `useLastTaxonId.ts`, and
    `useKebabOpenId.ts`. A future PR that drops one of them
    silently re-bundles the matching storage key into a
    sibling chunk, defeating the strict chunk-boundary contract.
    """
    assert path.is_file(), (
        f"missing per-key hook file: {path}. ODD-BSTATE-TAX-001-A "
        f"must split the typed hooks into per-key files."
    )


# ---------------------------------------------------------------------------
# Hook purity — every per-key hook is allowed to import React +
# the matching typed store, but MUST NOT touch `localStorage`
# or any storage primitive directly. Storage access lives in
# the matching `infrastructure/store<X>.ts` file.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", APP_HOOK_FILES)
def test_hook_does_not_touch_localstorage(path: Path) -> None:
    """Every per-key hook file MUST stay free of `localStorage.`
    tokens.

    ODD-BSTATE-TAX-001-A: with the per-key split, the storage
    helpers live in the matching store file
    (`storeTheme.ts` / `storeTreeSource.ts` / …) and reach the
    typed surface through the matching per-key read /
    subscribe imports. The hook itself is a thin React adapter
    on top of `useSyncExternalStore`. A regression that reaches
    for `localStorage.*` directly inside any per-key hook file
    trips this parametrized guard before review.
    """
    if not path.exists():
        pytest.skip(f"hook file not present yet: {path}")
    # Strip comments so a doc-block referencing `localStorage`
    # (explaining that storage lives in the matching per-key
    # store) is not a false positive.
    stripped = _strip_ts_comments(path.read_text(encoding="utf-8"))
    for token in (
        "localStorage", "sessionStorage",
        "fetch(", "document.", "window.localStorage",
        "process.", "globalThis.",
    ):
        assert token not in stripped, (
            f"{path.name} must NOT reference {token!r}; storage "
            f"access belongs to the matching per-key store file."
        )


@pytest.mark.parametrize("path", APP_HOOK_FILES)
def test_hook_uses_use_sync_external_store(path: Path) -> None:
    """Every per-key hook uses `useSyncExternalStore` (React 18+)
    so SSR returns the typed default, the first client render
    matches SSR, and the post-mount render returns the stored
    value. A future PR that switches to a less safe API (e.g.
    raw `useState` + `useEffect`) breaks the hydration contract.
    """
    if not path.exists():
        pytest.skip(f"hook file not present yet: {path}")
    text = path.read_text(encoding="utf-8")
    assert "useSyncExternalStore" in text, (
        f"{path.name} must use useSyncExternalStore so the "
        f"hydration guard never trips on a stored value."
    )


@pytest.mark.parametrize("path", APP_HOOK_FILES)
def test_hook_uses_client_directive(path: Path) -> None:
    """Every per-key hook is a Client Component hook. It MUST
    start with the `"use client";` directive so Next.js
    treats it as client-only code; without the directive the
    static export would try to evaluate the hook during the
    build's SSR pass.
    """
    if not path.exists():
        pytest.skip(f"hook file not present yet: {path}")
    text = path.read_text(encoding="utf-8")
    # The directive must be the first non-comment statement. Strip
    # leading comments so a doc-block at the top is allowed.
    block = re.compile(r"/\*[\s\S]*?\*/")
    line = re.compile(r"//[^\n]*")
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))  # noqa: E731
    stripped = block.sub(blank, text)
    stripped = line.sub(blank, stripped)
    head = stripped.lstrip()
    assert head.startswith(('"use client";', "'use client';")), (
        f"{path.name} must start with the `\"use client\";` "
        f"directive so Next.js treats it as a Client Component."
    )


# ---------------------------------------------------------------------------
# Per-key hook signatures — each per-key file MUST export exactly
# the typed hook for its key (no cross-key import leakage).
# ---------------------------------------------------------------------------
EXPECTED_PER_KEY_HOOKS: tuple[tuple[Path, str], ...] = (
    (APP_HOOK_THEME_FILE, "useTheme"),
    (APP_HOOK_TREE_SOURCE_FILE, "useTreeSource"),
    (APP_HOOK_LAST_TAXON_ID_FILE, "useLastTaxonId"),
    (APP_HOOK_KEBAB_OPEN_ID_FILE, "useKebabOpenId"),
    (APP_HOOK_EXPLORER_STATE_FILE, "useExplorerState"),
)


@pytest.mark.parametrize(
    ("path", "expected"),
    EXPECTED_PER_KEY_HOOKS,
    ids=[
        "theme",
        "tree_source",
        "last_taxon_id",
        "kebab_open_id",
        "explorer_state",
    ],
)
def test_per_key_hook_signature_returns_typed_value(
    path: Path, expected: str,
) -> None:
    """Each per-key file MUST export exactly its typed hook.

    The strict chunk-boundary contract (ODD-BSTATE-TAX-001-B)
    depends on each per-key hook file exporting only its own
    hook. A regression that re-introduces a cross-key export
    (e.g. `export { useTheme }` from `useTreeSource.ts`) would
    pull the wrong storage key into the wrong chunk and break
    the typed-source retention guarantee.

    Acceptance: the per-key file MUST export `export function
    <expected>(…)` exactly once — no other per-key hook name may
    appear as an export (cross-key leakage pin).
    """
    if not path.exists():
        pytest.skip(f"hook file not present yet: {path}")
    text = path.read_text(encoding="utf-8")
    assert re.search(
        rf"export\s+function\s+{expected}\b",
        text,
    ), (
        f"{path.name} must export `{expected}` (its per-key hook)."
    )
    # Reject every other per-key hook name — a future regression
    # that re-exports a sibling key would re-bundle the typed
    # surface beyond the strict boundary. The check has two
    # forms because the f-string substitution disallows literal
    # braces; we build the regex by string concatenation so the
    # `{` / `}` characters appear as literals (NOT as f-string
    # substitution markers).
    siblings = [
        name for other_path, name in EXPECTED_PER_KEY_HOOKS
        if other_path != path
    ]
    for sibling in siblings:
        # `export function <sibling>` declaration pin.
        function_pat = r"export\s+function\s+" + sibling + r"\b"
        # `export { …<sibling>… }` re-export object literal pin.
        brace_pat = (
            r"export\s*\{[^{}]*\b" + sibling + r"\b[^{}]*\}"
        )
        combined = "(?:" + function_pat + "|" + brace_pat + ")"
        assert not re.search(combined, text), (
            f"{path.name} must NOT re-export `{sibling}` — the "
            f"per-key boundary contract keeps each storage key's "
            f"hook + store in its own file so the strict chunk-"
            f"boundary witness can rely on Turbopack retention."
        )


# ---------------------------------------------------------------------------
# Barrel surface — the hook re-exports land on the public barrel so
# cross-module consumers can mount the typed hooks without a deep
# import.
# ---------------------------------------------------------------------------
def test_barrel_re_exports_per_key_hooks() -> None:
    """The public barrel re-exports every per-key hook so cross-
    module consumers can import through the public surface only.

    ODD-BSTATE-EXPLORER-PERSIST (slice 10) extends the per-key
    family by one entry (`useExplorerState`). The hook is the
    React adapter for the typed explorer-state store
    (`taxa.fex.explorerState`); the Browser-tab Explorer mount
    wires it through the public barrel so the React layer stays
    free of `localStorage.*` references and the typed chain
    stays hydration-safe. The barrel extension landed in PR
    #428 / commit `f4a5c0a`; the slice 10 source change
    consumes it via `import { useExplorerState } from
    "@taxa/browser-state"`.

    The assertion list mirrors the per-file rationale of the
    four sibling hooks — each per-key hook lives in its own
    file so Turbopack can drop the unrelated hooks from any
    consumer's chunk. The strict chunk-boundary contract
    (`tests/test_app_shell_render.py::
    test_out_index_html_chunks_permit_only_tree_source_key`)
    pins the contract end-to-end."""
    if not BARREL.exists():
        pytest.skip("barrel not present yet")
    text = BARREL.read_text(encoding="utf-8")
    for name in (
        "useTheme", "useTreeSource", "useLastTaxonId", "useKebabOpenId",
        "useExplorerState",
    ):
        assert name in text, (
            f"barrel must re-export `{name}` (the typed hook)."
        )


# ---------------------------------------------------------------------------
# Compile contract — strict mode, ES2022 + DOM, JSX react-jsx. The
# hook imports React, so the React types are required; we keep the
# runtime test focused on the typed store (which the hook re-exports
# through `useSyncExternalStore`'s subscribe / getSnapshot
# callbacks). React rendering itself belongs to a follow-up
# Playwright slice — that work unit stays in ODD-BSTATE-002.
# ---------------------------------------------------------------------------
def _tsc_inputs() -> list[Path]:
    return [
        p for p in (
            DOMAIN_KEYS_FILE,
            DOMAIN_DEFAULTS_FILE,
            INFRA_STORE_FILE,
            HOOK_FILE,
        ) if p.is_file()
    ]


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


def test_strict_tsc_passes_for_browser_state(tmp_path, require_toolchain: None) -> None:
    """ODD-BSTATE-001: every browser-state source file compiles in
    strict mode against the project tsconfig. A regression in any
    layer file fails this assertion before review.
    """
    out_dir = tmp_path / "bs-tg-out"
    result = _run_tsc(out_dir)
    assert result.returncode == 0, (
        f"tsc failed (exit {result.returncode}).\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# Runtime harness — drive the typed store's defaults + a single
# subscriber from the compiled output. The hydration safety itself
# (SSR snapshot == client first render) is exercised by React's
# `useSyncExternalStore`; we lock the underlying read defaults +
# the unsubscribe-on-cleanup contract here. The full React-
# renderer contract lives in the Playwright follow-up (PR 4b).
_HYDRATION_HARNESS = r"""
const path = require("path");
const fail = (l) => { process.stderr.write("FAIL " + l + "\n"); process.exit(1); };

// Stub `require("react")` BEFORE any module that imports it is
// loaded. The compiled hook module (`useBrowserStateKey.js`)
// does `require("react")` at module-load time; without this stub
// Node aborts with `MODULE_NOT_FOUND` because the test harness
// is run outside the project's `node_modules/` resolution tree.
const Module = require("module");
const realLoad = Module._load;
Module._load = function (request, parent, isMain) {
  if (request === "react") {
    return {
      useSyncExternalStore: (subscribe, getSnapshot, getServerSnapshot) => getSnapshot(),
      useCallback: (fn) => fn,
    };
  }
  return realLoad.call(this, request, parent, isMain);
};

const store = require(path.resolve(process.argv[2]));
const hook = require(path.resolve(process.argv[3]));
// tsc preserves the layer folder structure (--rootDir +
// per-source relative paths). Resolve `defaults.js` via
// `path.relative` from `store.js`'s directory.
const storeDir = path.dirname(path.resolve(process.argv[2]));
const defaults = require(path.resolve(storeDir, "../domain/defaults.js"));

const {
  DEFAULT_THEME, DEFAULT_TREE_SOURCE,
  DEFAULT_LAST_TAXON_ID, DEFAULT_KEBAB_OPEN_ID,
} = defaults;
const {
  readTheme, writeTheme, subscribeTheme,
  readTreeSource, writeTreeSource, subscribeTreeSource,
  readLastTaxonId, writeLastTaxonId, subscribeLastTaxonId,
  readKebabOpenId, writeKebabOpenId, subscribeKebabOpenId,
  reset,
} = store;

// Provide a minimal `window` / `localStorage` polyfill. Without
// it the store returns the typed default — which is exactly the
// SSR / first-render contract the hook relies on.
const map = new Map();
const fakeStorage = {
  getItem: (k) => (map.has(k) ? map.get(k) : null),
  setItem: (k, v) => { map.set(k, String(v)); },
  removeItem: (k) => { map.delete(k); },
};
globalThis.window = { localStorage: fakeStorage };
globalThis.localStorage = fakeStorage;

// 1. SSR-shaped read (no prior mutations, no listeners yet) returns
//    the typed default — the hydration snapshot is the default.
if (readTheme() !== DEFAULT_THEME) fail("ssr.theme_default");
if (readTheme() !== "light") fail("ssr.theme_light_literal");
if (readTreeSource() !== DEFAULT_TREE_SOURCE) fail("ssr.tree_source_default");
if (readTreeSource() !== "col") fail("ssr.tree_source_col_literal");
if (readLastTaxonId() !== DEFAULT_LAST_TAXON_ID) fail("ssr.last_taxon_id_null");
if (readKebabOpenId() !== DEFAULT_KEBAB_OPEN_ID) fail("ssr.kebab_open_id_null");

// 2. After mutation the in-memory cache moves; subscribers fire.
//    This mirrors the `useSyncExternalStore` post-mount re-render.
let themeFires = 0;
let lastThemeValue = null;
const unsubTheme = subscribeTheme((v) => { themeFires += 1; lastThemeValue = v; });
writeTheme("dark");
if (themeFires !== 1) fail("post_mount.theme_subscribe_once");
if (lastThemeValue !== "dark") fail("post_mount.theme_subscribe_value");
if (readTheme() !== "dark") fail("post_mount.theme_read_dark");

// 3. Unsubscribe prevents future fires.
unsubTheme();
writeTheme("light");
if (themeFires !== 1) fail("unsub.theme_no_further_fires");

// 4. Reset returns every cache to the typed default.
let resetFires = 0;
subscribeTheme(() => { resetFires += 1; });
subscribeTreeSource(() => { resetFires += 1; });
subscribeLastTaxonId(() => { resetFires += 1; });
subscribeKebabOpenId(() => { resetFires += 1; });
writeTheme("dark");
writeTreeSource("freshwater");
writeLastTaxonId(42);
writeKebabOpenId(9);
reset();
if (readTheme() !== DEFAULT_THEME) fail("reset.theme");
if (readTreeSource() !== DEFAULT_TREE_SOURCE) fail("reset.tree_source");
if (readLastTaxonId() !== DEFAULT_LAST_TAXON_ID) fail("reset.last_taxon_id");
if (readKebabOpenId() !== DEFAULT_KEBAB_OPEN_ID) fail("reset.kebab_open_id");
if (resetFires < 4) fail("reset.every_subscriber_fired");

// 5. Hook module exposes the per-key hooks (the runtime smoke we
//    can drive without a React renderer). The actual rendering
//    contract lives in the React layer; here we only assert that
//    the per-key hooks are present and are functions.
for (const name of ["useTheme", "useTreeSource", "useLastTaxonId", "useKebabOpenId"]) {
  if (typeof hook[name] !== "function") fail("hook." + name + "_is_function");
}

process.stdout.write("PASS\n");
"""


def test_compiled_hook_passes_runtime_contract(
    tmp_path, require_toolchain: None,
) -> None:
    """Compile `keys.ts`, `defaults.ts`, `store.ts`, the hook, and run
    the hydration harness under Node. The harness pins:
      - SSR-shaped read returns the typed default
      - Subscriber fires once per mutation
      - Unsubscribe stops further fires
      - Reset returns every cache to the default
      - Per-key hooks are exported as functions
    """
    out_dir = tmp_path / "bs-hg-out"
    result = _run_tsc(out_dir)
    assert result.returncode == 0, (
        f"tsc failed (exit {result.returncode}).\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # tsc preserves the layer folder structure (--rootDir + per-source
    # relative paths), so the compiled files land under
    # `out_dir/infrastructure/store.js` and
    # `out_dir/application/useBrowserStateKey.js`.
    compiled_store = out_dir / "infrastructure" / "store.js"
    compiled_hook = out_dir / "application" / "useBrowserStateKey.js"
    if not (compiled_store.is_file() and compiled_hook.is_file()):
        found = sorted(p.name for p in out_dir.rglob("*.js")) if out_dir.exists() else []
        pytest.fail(
            f"expected compiled store.js + useBrowserStateKey.js under {out_dir}; "
            f"found compiled files: {found}"
        )
    harness_file = tmp_path / "harness.js"
    harness_file.write_text(_HYDRATION_HARNESS, encoding="utf-8")
    node = subprocess.run(
        ["node", str(harness_file), str(compiled_store), str(compiled_hook)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert node.returncode == 0, (
        f"hydration harness failed (exit {node.returncode}).\n"
        f"stdout: {node.stdout}\nstderr: {node.stderr}"
    )
    assert "PASS" in node.stdout, (
        f"hydration harness did not emit PASS; stdout={node.stdout!r}"
    )
