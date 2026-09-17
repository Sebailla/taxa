"""Taxonomy tree-state presentation contract tests (ODD-VTREE-001).

Pins `src/modules/taxonomy/presentation/tree-state.ts` — the pure
framework-free state kernel for the visible taxonomy tree. The React
`TaxonomyTree` component (ODD-VTREE-002) consumes this helper.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_DIR = REPO_ROOT / "src" / "modules" / "taxonomy"
TREE_STATE_FILE = MODULE_DIR / "presentation" / "tree-state.ts"
BARREL_FILE = MODULE_DIR / "index.ts"
DOMAIN_FILE = MODULE_DIR / "domain" / "taxon.ts"


@pytest.fixture()
def require_toolchain() -> None:
    if not (shutil.which("npx") and shutil.which("node")):
        pytest.skip("npx + node required on PATH for compile/runtime test")


@pytest.fixture()
def tree_state_text(require_toolchain: None) -> str:
    if not TREE_STATE_FILE.exists():
        pytest.skip("tree-state.ts not present yet")
    return TREE_STATE_FILE.read_text()


_FORBIDDEN = (
    "from 'react'", 'from "react"',
    "from 'next'", 'from "next"',
    "from 'nextjs'", 'from "nextjs"',
    "from 'fastapi'", 'from "fastapi"',
    "from 'starlette'", 'from "starlette"',
    "fetch(", "localStorage", "sessionStorage",
    "document.", "window.", "process.", "globalThis",
    "../infrastructure", "../index.ts",
    "../research", "../design-system", "../browser-state", "../app-shell",
    "../../research", "../../design-system", "../../browser-state", "../../app-shell",
)


def test_tree_state_file_exists() -> None:
    assert TREE_STATE_FILE.is_file(), (
        f"missing tree-state helper: {TREE_STATE_FILE}. ODD-VTREE-001 ships this file."
    )
    assert TREE_STATE_FILE.suffix == ".ts", "tree-state must be `.ts` (no JSX)."


@pytest.mark.parametrize("token", _FORBIDDEN)
def test_tree_state_source_free_of_forbidden_tokens(token: str, tree_state_text: str) -> None:
    """spec.md rule 4: presentation → domain only."""
    assert token not in tree_state_text, (
        f"tree-state.ts must stay free of {token!r}; spec.md rule 4."
    )


def test_tree_state_imports_only_from_domain(tree_state_text: str) -> None:
    for src in re.findall(r'from\s+["\']([^"\']+)["\']', tree_state_text):
        assert src.startswith("../domain/"), (
            f"tree-state.ts imports from {src!r}; must be ../domain/ only."
        )


def test_tree_state_exports_required_helpers(tree_state_text: str) -> None:
    for name in (
        "EMPTY_TREE_STATE", "withRoots", "childIds", "isExpanded",
        "expand", "collapse", "toggleExpand", "attachChildren",
        "setLoadStatus", "loadStatus",
    ):
        pattern = rf"export\s+(?:async\s+)?function\s+{name}\b|export\s+const\s+{name}\b"
        assert re.search(pattern, tree_state_text), (
            f"tree-state.ts must export `{name}`."
        )


def test_barrel_reexports_tree_state() -> None:
    """spec.md rule 5: barrel re-exports the public surface."""
    if not BARREL_FILE.exists():
        pytest.skip("barrel not present yet")
    text = BARREL_FILE.read_text()
    for name in (
        "EMPTY_TREE_STATE", "withRoots", "childIds", "isExpanded",
        "expand", "collapse", "toggleExpand", "attachChildren",
        "setLoadStatus", "loadStatus", "TreeState", "NodeLoadStatus",
    ):
        assert name in text, f"barrel must re-export {name}."
    assert "tree-state" in text, "barrel must reference ./presentation/tree-state.js."


def _run_tsc(out_dir: Path) -> subprocess.CompletedProcess:
    sources: list[str] = []
    if DOMAIN_FILE.is_file():
        sources.append(str(DOMAIN_FILE))
    if TREE_STATE_FILE.is_file():
        sources.append(str(TREE_STATE_FILE))
    if not sources:
        pytest.skip("no source files to compile")
    return subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--strict", "--target", "ES2022",
            "--module", "commonjs", "--lib", "ES2022",
            "--skipLibCheck", "--esModuleInterop",
            "--rootDir", str(MODULE_DIR),
            "--outDir", str(out_dir),
            *sources,
        ],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )


_NODE_HARNESS = r"""
const path = require("path");
const assert = require("assert");
const ts = require(path.resolve(process.argv[2]));
const T = (id, name, rank, parentId) => ({ id, name, rank, authorship: null, parent_id: parentId });
const ANI = T(1, "Animalia", "kingdom", null);
const CHOR = T(2, "Chordata", "phylum", 1);
const MAMM = T(3, "Mammalia", "class", 2);
const CANIS = T(4, "Canis", "genus", 3);
const BIOTA = T(5, "Biota", "superdomain", null);
const FW = T(100, "Freshwater Fishes", "collection", null);

// A. Empty state.
const e = ts.EMPTY_TREE_STATE;
assert.strictEqual(e.rootIds.length, 0);
assert.strictEqual(e.nodes.size, 0);
assert.deepStrictEqual(ts.childIds(e, 999), []);
assert.strictEqual(ts.isExpanded(e, 1), false);
assert.strictEqual(ts.loadStatus(e, 1), "idle");

// B. withRoots + attachChildren + dedup + load status.
let s = ts.withRoots(e, [ANI]);
assert.deepStrictEqual([...s.rootIds], [1]);
s = ts.attachChildren(s, ANI.id, [CHOR, MAMM, CHOR]); // CHOR dup
assert.deepStrictEqual([...ts.childIds(s, ANI.id)], [2, 3], "dup collapsed");
assert.strictEqual(ts.loadStatus(s, ANI.id), "loaded", "load → loaded on attach");
s = ts.attachChildren(s, ANI.id, [CANIS]);
assert.deepStrictEqual([...ts.childIds(s, ANI.id)], [2, 3, 4], "append not replace");

// C. attachChildren under unknown parent still records the bucket.
const s2 = ts.attachChildren(e, 999, [CHOR]);
assert.deepStrictEqual([...ts.childIds(s2, 999)], [2]);

// D. expand/collapse/toggleExpand idempotent.
let s3 = e;
s3 = ts.expand(s3, 1);
assert.strictEqual(ts.isExpanded(s3, 1), true);
s3 = ts.expand(s3, 1); // idempotent
assert.strictEqual(ts.isExpanded(s3, 1), true);
s3 = ts.collapse(s3, 1);
s3 = ts.collapse(s3, 1); // idempotent
assert.strictEqual(ts.isExpanded(s3, 1), false);
s3 = ts.toggleExpand(s3, 1);
s3 = ts.toggleExpand(s3, 1);
assert.strictEqual(ts.isExpanded(s3, 1), false);

// E. load status lifecycle (loading → error; attachChildren resets).
let s4 = ts.setLoadStatus(e, 5, "loading");
assert.strictEqual(ts.loadStatus(s4, 5), "loading");
s4 = ts.setLoadStatus(s4, 5, "error");
assert.strictEqual(ts.loadStatus(s4, 5), "error");
s4 = ts.attachChildren(s4, 5, []);
assert.strictEqual(ts.loadStatus(s4, 5), "loaded");

// F. superdomain + collection roots round-trip (ODD-VTREE-001).
let s5 = ts.withRoots(e, [BIOTA, ANI, FW]);
assert.deepStrictEqual([...s5.rootIds], [5, 1, 100]);
assert.strictEqual(s5.nodes.get(5).rank, "superdomain");
assert.strictEqual(s5.nodes.get(100).rank, "collection");

// G. Mutators do not write through EMPTY_TREE_STATE.
let s6 = e;
const frozen = ts.EMPTY_TREE_STATE;
s6 = ts.expand(s6, 1);
s6 = ts.withRoots(s6, [ANI]);
s6 = ts.attachChildren(s6, 1, [CHOR]);
assert.strictEqual(ts.isExpanded(frozen, 1), false);
assert.strictEqual(frozen.rootIds.length, 0);
assert.deepStrictEqual(ts.childIds(frozen, 1), []);

process.stdout.write("PASS\n");
"""


def test_compiled_tree_state_passes_runtime_contract(
    tmp_path: Path, require_toolchain: None,
) -> None:
    """A–G: empty state, withRoots, attachChildren (dedup + unknown parent),
    expand/collapse/toggleExpand (idempotent), load-status lifecycle,
    superdomain/collection roots round-trip, immutability of EMPTY_TREE_STATE."""
    for p in (TREE_STATE_FILE, DOMAIN_FILE):
        if not p.is_file():
            pytest.skip(f"missing required source: {p}")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    result = _run_tsc(out_dir)
    assert result.returncode == 0, (
        f"tree-state.ts failed to compile.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    compiled = out_dir / "presentation" / "tree-state.js"
    assert compiled.is_file(), f"tsc did not emit {compiled}."
    harness = tmp_path / "harness.cjs"
    harness.write_text(_NODE_HARNESS)
    result = subprocess.run(
        ["node", str(harness), str(compiled)],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0 and result.stdout.strip() == "PASS", (
        f"tree-state runtime harness failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
