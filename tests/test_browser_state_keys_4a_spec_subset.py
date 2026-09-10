"""
Verification-only marker for the canonical PR 4a browser-state contract.

The PR 4a spec authored four canonical keys — `theme`, `tree-source`,
`last-taxon-id`, `kebab-open-id` — with a typed store, one read + one
write per key, and a public barrel. PR 5c.1a legitimately extended the
contract to a five-key superset by adding `versionBannerDismissed` and
extending `TreeSource` to accept `freshwater`. This marker verifies the
canonical four-key contract HOLDS as a SUBSET of the shipped five-key
superset — extra entries are permitted, never asserted absent.

Hermetic: reads `.ts` files on disk, parses with regex. No Node, no
JSDOM, no imports of the typed store. Verification-only: no source
edits, no OpenSpec edits, no commit / push / PR / worktree activity.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_ROOT = REPO_ROOT / "src" / "modules" / "browser-state"
KEYS_FILE = MODULE_ROOT / "domain" / "keys.ts"
STORE_FILE = MODULE_ROOT / "infrastructure" / "store.ts"
SAFE_STORAGE_FILE = MODULE_ROOT / "infrastructure" / "safe-storage.ts"
BARREL = MODULE_ROOT / "index.ts"


# Canonical PR 4a four-key contract. PR 5c.1a extends the superset by
# adding `versionBannerDismissed` — this marker asserts SUBSET, not equality.
CANONICAL_KEYS: tuple[tuple[str, str, str], ...] = (
    ("theme",       "taxa.settings.theme",    '"light"'),
    ("treeSource",  "taxa.tree.source",       '"col"'),
    ("lastTaxonId", "taxa.tree.lastTaxonId",  "null"),
    ("kebabOpenId", "taxa.tree.kebabOpenId",  "null"),
)
SHORT_NAMES = [n for n, _, _ in CANONICAL_KEYS]


# Comment stripping mirrors tests/test_domain_purity.py so a JSDoc
# mention of `localStorage` in a docstring does not trip purity / barrel
# surfaces. Preserves line numbers so diagnostics stay aligned.
_BLOCK_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/")
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")
_blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))
_strip_ts_comments = lambda text: _LINE_COMMENT_RE.sub(
    _blank, _BLOCK_COMMENT_RE.sub(_blank, text)
)


def _read(path: Path) -> str:
    return path.read_text()


def _read_stripped(path: Path) -> str:
    return _strip_ts_comments(_read(path))


def _store_interface_body() -> str:
    block = re.search(
        r"interface\s+BrowserStateStore\s*\{([^}]+)\}", _read_stripped(STORE_FILE)
    )
    assert block, "BrowserStateStore interface declaration not found"
    return block.group(1)


# Layer presence — PR 4a shipped four files together; 5c retained the shape.
@pytest.mark.parametrize("path", [KEYS_FILE, SAFE_STORAGE_FILE, STORE_FILE, BARREL])
def test_pr4a_layer_files_present(path: Path) -> None:
    assert path.is_file(), (
        f"missing PR 4a file: {path.relative_to(REPO_ROOT).as_posix()}"
    )


# (1) Four canonical keys exist as a SUBSET of BROWSER_STATE_KEYS.
def test_browser_state_keys_includes_canonical_subset() -> None:
    block = re.search(
        r"BROWSER_STATE_KEYS\s*=\s*\{([^}]*)\}", _read(KEYS_FILE), flags=re.DOTALL
    )
    assert block, "BROWSER_STATE_KEYS object literal not found"
    body = block.group(1)
    for short_name, literal, _ in CANONICAL_KEYS:
        assert f'"{literal}"' in body, (
            f"BROWSER_STATE_KEYS missing canonical literal '{literal}' "
            f"(short name '{short_name}')"
        )
        assert re.search(rf"\b{re.escape(short_name)}\s*:", body), (
            f"BROWSER_STATE_KEYS missing short name '{short_name}'"
        )


# (2) Canonical defaults + type-guard validators reachable from `domain/keys.ts`.
@pytest.mark.parametrize(
    "short_name,default_literal",
    [(n, d) for n, _, d in CANONICAL_KEYS],
    ids=SHORT_NAMES,
)
def test_browser_state_defaults_canonical_value(
    short_name: str, default_literal: str,
) -> None:
    block = re.search(
        r"BROWSER_STATE_DEFAULTS\b[^=]*=\s*\{([^}]+)\}",
        _read(KEYS_FILE), flags=re.DOTALL,
    )
    assert block, "BROWSER_STATE_DEFAULTS object literal not found"
    m = re.search(rf"\b{re.escape(short_name)}\s*:\s*([^,\n]+)", block.group(1))
    assert m, f"BROWSER_STATE_DEFAULTS must declare a default for '{short_name}'"
    assert m.group(1).strip() == default_literal, (
        f"BROWSER_STATE_DEFAULTS.{short_name} canonical default is "
        f"{default_literal!r}; got {m.group(1).strip()!r}"
    )


@pytest.mark.parametrize(
    "short_name,guard_name",
    [
        ("theme",       "isValidTheme"),
        ("treeSource",  "isValidTreeSource"),
        ("lastTaxonId", "isValidTaxonId"),
        ("kebabOpenId", "isValidKebabOpenId"),
    ],
    ids=["theme_guard", "tree_source_guard",
         "last_taxon_id_guard", "kebab_open_id_guard"],
)
def test_canonical_key_has_typed_validator(
    short_name: str, guard_name: str,
) -> None:
    pattern = rf"\b{re.escape(guard_name)}\s*\([^)]*\)\s*:\s*value\s+is\s+"
    assert re.search(pattern, _read(KEYS_FILE)), (
        f"keys.ts must export `{guard_name}(value): value is …` "
        f"for canonical key '{short_name}' (PR 4a domain contract)."
    )


# (3) At least one typed read + one typed write per canonical key.
# Extra readers / writers permitted (5c adds versionBannerDismissed).
@pytest.mark.parametrize("short_name", SHORT_NAMES, ids=SHORT_NAMES)
def test_canonical_key_has_typed_getter(short_name: str) -> None:
    getter = f"get{short_name[0].upper()}{short_name[1:]}("
    assert getter in _read_stripped(STORE_FILE), (
        f"store.ts missing typed reader `{getter}` "
        f"for canonical key '{short_name}' (PR 4a store surface)."
    )


@pytest.mark.parametrize("short_name", SHORT_NAMES, ids=SHORT_NAMES)
def test_canonical_key_has_typed_setter(short_name: str) -> None:
    setter = f"set{short_name[0].upper()}{short_name[1:]}("
    assert setter in _read_stripped(STORE_FILE), (
        f"store.ts missing typed writer `{setter}` "
        f"for canonical key '{short_name}' (PR 4a store surface)."
    )


# (4) Domain purity — `domain/keys.ts` stays free of framework / I/O /
# browser / HTTP / process tokens (spec.md rule 4).
DOMAIN_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "react", "next", "nextjs", "fastapi", "starlette", "pydantic",
    "fetch(", "localStorage", "document.", "window.", "process.",
)


@pytest.mark.parametrize("token", DOMAIN_FORBIDDEN_TOKENS)
def test_domain_keys_have_no_forbidden_token(token: str) -> None:
    if not KEYS_FILE.is_file():
        pytest.skip("domain/keys.ts not present")
    for lineno, line in enumerate(
        _read_stripped(KEYS_FILE).splitlines(), start=1
    ):
        assert token not in line, (
            f"domain/keys.ts line {lineno} contains forbidden token "
            f"{token!r} (spec.md rule 4 — domain purity)."
        )


# (5) Safe-storage exception protection.
def test_safe_storage_helpers_guard_platform_and_json() -> None:
    text = _read(SAFE_STORAGE_FILE)
    for decl in ("getBrowserStorage", "tryJsonParse", "tryJsonStringify"):
        assert re.search(rf"\b{re.escape(decl)}\b", text), (
            f"safe-storage.ts must export `{decl}`."
        )


@pytest.mark.parametrize("token", ["getItem(", "setItem("])
def test_storage_callsites_in_store_are_try_catch_wrapped(token: str) -> None:
    lines = _read_stripped(STORE_FILE).splitlines()
    occurrences = [
        lineno for lineno, line in enumerate(lines, start=1)
        if token in line
    ]
    assert occurrences, (
        f"store.ts must contain at least one {token!r} callsite."
    )
    for lineno in occurrences:
        window = "\n".join(lines[max(0, lineno - 6):lineno + 1])
        assert "try" in window, (
            f"store.ts line {lineno}: {token!r} must live inside a `try` block."
        )


# (6) Public barrel surface — typed APIs only, no raw storage.
def test_barrel_reexports_typed_store_surface() -> None:
    body = _store_interface_body()
    assert "subscribe(" in body, (
        "BrowserStateStore must declare `subscribe(listener)`."
    )
    assert re.search(r"\breset\s*\(", body), (
        "BrowserStateStore must declare `reset()`."
    )
    for short_name in SHORT_NAMES:
        getter = f"get{short_name[0].upper()}{short_name[1:]}("
        setter = f"set{short_name[0].upper()}{short_name[1:]}("
        assert getter in body, f"BrowserStateStore must declare `{getter}`."
        assert setter in body, f"BrowserStateStore must declare `{setter}`."


def test_barrel_exposes_typed_store_interface() -> None:
    assert "BrowserStateStore" in _read_stripped(BARREL), (
        "index.ts must re-export `BrowserStateStore`."
    )


def test_barrel_does_not_expose_raw_storage() -> None:
    cleaned = _read_stripped(BARREL)
    assert "localStorage" not in cleaned, (
        "index.ts must not mention `localStorage`."
    )
    assert "getBrowserStorage" not in cleaned, (
        "index.ts must not re-export `getBrowserStorage`."
    )
    forbidden = re.findall(r"export\b[^;\n]*\b(getItem|setItem)\b", cleaned)
    assert not forbidden, (
        f"barrel must not export getItem/setItem; found: {forbidden!r}"
    )
