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


# Pinned four-key contract. The full literal string is part of the public
# contract: a regression that drifts the namespace (e.g. `taxa.theme`
# instead of `taxa.settings.theme`) silently misroutes writes.
EXPECTED_KEYS: tuple[tuple[str, str], ...] = (
    ("theme",       "taxa.settings.theme"),
    ("treeSource",  "taxa.tree.source"),
    ("lastTaxonId", "taxa.tree.lastTaxonId"),
    ("kebabOpenId", "taxa.tree.kebabOpenId"),
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
# Four-key typed literals + defaults.
# ===========================================================================
def test_keys_object_declares_exactly_four_pinned_literals():
    """`BROWSER_STATE_KEYS` MUST have exactly the four pinned entries
    with the exact literal strings — a typo or rename here is silently
    data-corrupting on existing localStorage data."""
    text = _read(KEYS_FILE)
    block = re.search(r"BROWSER_STATE_KEYS\s*=\s*\{([^}]*)\}", text, flags=re.DOTALL)
    assert block, "BROWSER_STATE_KEYS object literal not found"
    quoted = re.findall(r'"([^"]+)"', block.group(1))
    expected = [literal for _, literal in EXPECTED_KEYS]
    assert len(quoted) == 4, f"expected 4 literals, got {quoted}"
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
# 4 + 4 call-site contract (tasks.md §Phase 4.1).
# ===========================================================================
def test_exactly_four_getitem_callsites_under_src():
    """Tasks.md §Phase 4.1: the store is the ONLY localStorage layer,
    with exactly four `getItem(` callsites, one per pinned key, all in
    `infrastructure/store.ts`. Splitting across files would break the
    4 + 4 invariant."""
    occurrences = _callsites(SRC_ROOT, "getItem(")
    assert len(occurrences) == 4, (
        f"expected exactly 4 getItem( callsites under src/; "
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


def test_exactly_four_setitem_callsites_under_src():
    """Mirror of the getItem contract — same 4 + 4 shape, same single-file
    location invariant."""
    occurrences = _callsites(SRC_ROOT, "setItem(")
    assert len(occurrences) == 4, (
        f"expected exactly 4 setItem( callsites under src/; "
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
# Store surface — 4 typed getters + 4 typed setters + subscribe + reset.
# ===========================================================================
def test_store_exposes_eight_mutators_and_listener():
    """Pins the public store surface: 4 typed getters, 4 typed setters,
    a `subscribe(listener)` registration, and a `reset()` action. The
    regex matches every `camelCase(` token; we filter the
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
