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

HOOK_FILE = APP_DIR / "useBrowserStateKey.ts"
INFRA_STORE_FILE = INFRA_DIR / "store.ts"
DOMAIN_KEYS_FILE = DOMAIN_DIR / "keys.ts"
DOMAIN_DEFAULTS_FILE = DOMAIN_DIR / "defaults.ts"


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
# File presence — pins the canonical hook path.
# ---------------------------------------------------------------------------
def test_hook_file_present() -> None:
    """`application/useBrowserStateKey.ts` is the canonical hook path.
    PR 4b predecessor ships it; ODD-BSTATE-001 keeps the same path.
    """
    assert HOOK_FILE.is_file(), (
        f"missing hook file: {HOOK_FILE}. ODD-BSTATE-001 must create "
        f"this file inside the canonical path."
    )


# ---------------------------------------------------------------------------
# Hook purity — the hook is allowed to import React + the typed
# store, but MUST NOT touch `localStorage` or any storage primitive
# directly. Storage access lives in `infrastructure/store.ts`.
# ---------------------------------------------------------------------------
def test_hook_does_not_touch_localstorage() -> None:
    if not HOOK_FILE.exists():
        pytest.skip("hook file not present yet")
    # Strip comments so a doc-block referencing `localStorage`
    # (explaining that storage lives in `infrastructure/store.ts`)
    # is not a false positive.
    stripped = _strip_ts_comments(HOOK_FILE.read_text(encoding="utf-8"))
    for token in (
        "localStorage", "sessionStorage",
        "fetch(", "document.", "window.localStorage",
        "process.", "globalThis.",
    ):
        assert token not in stripped, (
            f"useBrowserStateKey.ts must NOT reference {token!r}; storage "
            f"access belongs to infrastructure/store.ts."
        )


def test_hook_uses_use_sync_external_store() -> None:
    """The hydration-safe hook uses `useSyncExternalStore` (React 18+)
    so SSR returns the typed default, the first client render
    matches SSR, and the post-mount render returns the stored
    value. A future PR that switches to a less safe API (e.g.
    raw `useState` + `useEffect`) breaks the hydration contract.
    """
    if not HOOK_FILE.exists():
        pytest.skip("hook file not present yet")
    text = HOOK_FILE.read_text(encoding="utf-8")
    assert "useSyncExternalStore" in text, (
        "useBrowserStateKey.ts must use useSyncExternalStore so the "
        "hydration guard never trips on a stored value."
    )


def test_hook_uses_client_directive() -> None:
    """The hook is a Client Component hook (uses `useEffect`,
    `useSyncExternalStore`, browser APIs). It MUST start with the
    `"use client";` directive so Next.js treats it as client-only
    code; without the directive the static export would try to
    evaluate the hook during the build's SSR pass.
    """
    if not HOOK_FILE.exists():
        pytest.skip("hook file not present yet")
    text = HOOK_FILE.read_text(encoding="utf-8")
    # The directive must be the first non-comment statement. Strip
    # leading comments so a doc-block at the top is allowed.
    block = re.compile(r"/\*[\s\S]*?\*/")
    line = re.compile(r"//[^\n]*")
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))  # noqa: E731
    stripped = block.sub(blank, text)
    stripped = line.sub(blank, stripped)
    head = stripped.lstrip()
    assert head.startswith(('"use client";', "'use client';")), (
        "useBrowserStateKey.ts must start with the `\"use client\";` "
        "directive so Next.js treats it as a Client Component."
    )


def test_hook_signature_returns_typed_value_per_key() -> None:
    """The hook exposes per-key hooks (one per typed storage key) so
    TypeScript narrows the return type without a generic dispatch
    table. The four per-key hook names MUST exist.
    """
    if not HOOK_FILE.exists():
        pytest.skip("hook file not present yet")
    text = HOOK_FILE.read_text(encoding="utf-8")
    for name in (
        "useTheme", "useTreeSource", "useLastTaxonId", "useKebabOpenId",
    ):
        assert re.search(rf"export\s+function\s+{name}\b", text), (
            f"useBrowserStateKey.ts must export `{name}`."
        )


# ---------------------------------------------------------------------------
# Barrel surface — the hook re-exports land on the public barrel so
# cross-module consumers can mount the typed hooks without a deep
# import.
# ---------------------------------------------------------------------------
def test_barrel_re_exports_per_key_hooks() -> None:
    """The public barrel re-exports every per-key hook so cross-
    module consumers can import through the public surface only."""
    if not BARREL.exists():
        pytest.skip("barrel not present yet")
    text = BARREL.read_text(encoding="utf-8")
    for name in (
        "useTheme", "useTreeSource", "useLastTaxonId", "useKebabOpenId",
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
