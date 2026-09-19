"""Taxonomy Breadcrumb presentation slice 1 contract tests (PR 5c).

Pins `src/modules/taxonomy/presentation/breadcrumb-path.ts` — the pure
parent-chain walker. The React `Breadcrumb` component, JSX render
contract, and DOM data attributes land in PR 5c slice 2; this slice
ships only the pure helper.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_DIR = REPO_ROOT / "src" / "modules" / "taxonomy"
BREADCRUMB_PATH_FILE = MODULE_DIR / "presentation" / "breadcrumb-path.ts"
BARREL_FILE = MODULE_DIR / "index.ts"
DOMAIN_FILE = MODULE_DIR / "domain" / "taxon.ts"


@pytest.fixture()
def require_toolchain() -> None:
    if not (shutil.which("npx") and shutil.which("node")):
        pytest.skip("npx + node required on PATH for compile/runtime test")


@pytest.fixture()
def breadcrumb_text(require_toolchain: None) -> str:
    """Read breadcrumb-path.ts; skip cleanly when missing (RED stage)."""
    if not BREADCRUMB_PATH_FILE.exists():
        pytest.skip("breadcrumb-path.ts not present yet")
    return BREADCRUMB_PATH_FILE.read_text()


# spec.md rule 4 — presentation → domain only. Literal tokens (not
# substrings) avoid false positives like `reactivity` matching `react`.
_FORBIDDEN = (
    'from \'react\'', 'from "react"',
    'from \'next\'',   'from "next"',
    'from \'nextjs\'', 'from "nextjs"',
    'from \'fastapi\'', 'from "fastapi"',
    'from \'starlette\'', 'from "starlette"',
    "fetch(", "localStorage", "sessionStorage",
    "document.", "window.", "process.", "globalThis",
    "../infrastructure", "../index.ts",
    "../research", "../design-system", "../browser-state", "../app-shell",
    "../../research", "../../design-system", "../../browser-state", "../../app-shell",
)


# ---------------------------------------------------------------------------
# File presence + source-level purity (no compiler required).
# ---------------------------------------------------------------------------
def test_breadcrumb_path_file_exists() -> None:
    """RED marker for PR 5c slice 1. File must be `.ts` (no JSX)."""
    assert BREADCRUMB_PATH_FILE.is_file(), (
        f"missing breadcrumb helper: {BREADCRUMB_PATH_FILE}. "
        f"PR 5c slice 1 ships this file."
    )
    assert BREADCRUMB_PATH_FILE.suffix == ".ts", (
        "breadcrumb-path must be `.ts` (no JSX in slice 1)."
    )


@pytest.mark.parametrize("token", _FORBIDDEN)
def test_breadcrumb_path_source_free_of_forbidden_tokens(token: str, breadcrumb_text: str) -> None:
    """Spec.md rule 4: presentation → domain only."""
    assert token not in breadcrumb_text, (
        f"breadcrumb-path.ts must stay free of {token!r}; spec.md rule 4."
    )


def test_breadcrumb_path_imports_only_from_domain(breadcrumb_text: str) -> None:
    """Imports only from `../domain/taxon` (spec.md rule 5)."""
    for src in re.findall(r'from\s+["\']([^"\']+)["\']', breadcrumb_text):
        assert src.startswith("../domain/"), (
            f"breadcrumb-path.ts imports from {src!r}; must be ../domain/ only."
        )


# ---------------------------------------------------------------------------
# Helper surface (source-level).
# ---------------------------------------------------------------------------
def test_walk_breadcrumb_path_is_named_export(breadcrumb_text: str) -> None:
    assert re.search(
        r"export\s+(?:async\s+)?function\s+walkBreadcrumbPath\b",
        breadcrumb_text,
    ), "breadcrumb-path.ts must export `walkBreadcrumbPath` as a named function."


def test_walk_breadcrumb_path_is_pure(breadcrumb_text: str) -> None:
    """Pure: no `await`, no DOM/IO tokens in the function body."""
    m = re.search(
        r"export\s+(?:async\s+)?function\s+walkBreadcrumbPath\b[\s\S]*?\n\}",
        breadcrumb_text,
    )
    assert m, "walkBreadcrumbPath function block not found."
    body = m.group(0)
    assert "await " not in body
    for tok in (
        "fetch(", "sessionStorage",
        "document.", "window.", "process.", "globalThis",
    ):
        assert tok not in body, f"walkBreadcrumbPath must stay pure; got {tok!r}."


def test_breadcrumb_source_union_pins_three_sources(breadcrumb_text: str) -> None:
    """Walker enumerates exactly `col | worms | freshwater`."""
    for src in ("\"col\"", "\"worms\"", "\"freshwater\""):
        assert src in breadcrumb_text, f"breadcrumb-path.ts must enumerate {src!r}."
    assert re.search(r"worms", breadcrumb_text), "walker must dispatch on 'worms'."
    assert re.search(r"freshwater", breadcrumb_text), "walker must dispatch on 'freshwater'."


def test_breadcrumb_caps_cycles_at_30(breadcrumb_text: str) -> None:
    """Hard cap of 30 hops. Legacy `safety = 30`."""
    assert "30" in breadcrumb_text, (
        "breadcrumb-path.ts must declare a 30-hop cycle cap."
    )


# ---------------------------------------------------------------------------
# Barrel contract.
# ---------------------------------------------------------------------------
def test_barrel_reexports_breadcrumb_path() -> None:
    """Barrel re-exports the helper + types + constant (spec.md rule 5)."""
    if not BARREL_FILE.exists():
        pytest.skip("barrel not present yet")
    text = BARREL_FILE.read_text()
    for name in (
        "walkBreadcrumbPath", "walkBreadcrumbForSource", "deriveWoRMSEdges",
        "BreadcrumbSegment", "BreadcrumbSource", "ParentIdResolver",
        "BreadcrumbTreeState", "BREADCRUMB_MAX_HOPS",
    ):
        assert name in text, f"barrel must re-export {name}."


def test_barrel_does_not_reexport_react_component() -> None:
    """Slice 1 is helper-only; the React `Breadcrumb` lands in slice 2."""
    if not BARREL_FILE.exists():
        pytest.skip("barrel not present yet")
    text = BARREL_FILE.read_text()
    assert not re.search(
        r"^export\s*(?:\{[^}]*\bBreadcrumb\b|\s+Breadcrumb\b)",
        text, re.MULTILINE,
    ), "barrel must NOT re-export the React Breadcrumb component in slice 1."


# ---------------------------------------------------------------------------
# Runtime contract under Node.
#
# Plain strict tsc (no `--jsx react` — the helper is `.ts`, no JSX).
# `breadcrumb-path.ts` imports only canonical `Taxon` + `Rank` from the
# domain layer; the compiled CJS module has no React dependency.
# ---------------------------------------------------------------------------
def _run_tsc(out_dir: Path) -> subprocess.CompletedProcess:
    sources: list[str] = []
    if DOMAIN_FILE.is_file():
        sources.append(str(DOMAIN_FILE))
    if BREADCRUMB_PATH_FILE.is_file():
        sources.append(str(BREADCRUMB_PATH_FILE))
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
const {
  walkBreadcrumbPath,
  walkBreadcrumbForSource,
  deriveWoRMSEdges,
} = require(path.resolve(process.argv[2]));

// Helper bindings — same names as the helper-tests elsewhere.
const walkForSource = walkBreadcrumbForSource;
const deriveEdges = deriveWoRMSEdges;
const emptyState = () => ({
  nodes: new Map(),
  childIdsByParent: new Map(),
});
const T = (id, name, rank, parentId) => ({
  id, name, rank, authorship: null, parent_id: parentId,
  worms_parent_id: null, freshwater_parent_id: null,
});

// A. Empty state — null + unknown focus.
assert.deepStrictEqual(
  walkBreadcrumbPath(null, "col", new Map(), (t) => t.parent_id), []);
assert.deepStrictEqual(
  walkBreadcrumbPath(99, "col", new Map(), (t) => t.parent_id), []);

// B. CoL chain — parent_id only, oldest-first.
const ani = T(1, "Animalia", "kingdom", null);
const chor = T(2, "Chordata", "phylum", 1);
const mamm = T(3, "Mammalia", "class", 2);
const canis = T(4, "Canis", "genus", 3);
const col = walkBreadcrumbPath(4, "col",
  new Map([[1, ani], [2, chor], [3, mamm], [4, canis]]),
  (t) => t.parent_id);
assert.strictEqual(col.length, 4, "col chain length");
assert.deepStrictEqual(col.map((s) => s.id), [1, 2, 3, 4], "oldest-first");
assert.strictEqual(col[0].name, "Animalia");
assert.strictEqual(col[3].rank, "genus");

// C. WoRMS chain — resolver reads worms_parent_id, not parent_id.
const wAni = T(1, "Animalia", "kingdom", null);
const wChor = T(2, "Chordata", "phylum", 999);
wChor.worms_parent_id = 1;
const worms = walkBreadcrumbPath(2, "worms",
  new Map([[1, wAni], [2, wChor]]),
  (t, src) => src === "worms" ? t.worms_parent_id : t.parent_id);
assert.strictEqual(worms.length, 2);
assert.strictEqual(worms[0].id, 1);
assert.strictEqual(worms[1].id, 2);

// D. Freshwater chain — freshwater_parent_id, parent_id is NULL.
const fRoot = T(100, "Freshwater Fishes", "kingdom", null);
const fFam = T(101, "Cichlidae", "family", null);
fFam.freshwater_parent_id = 100;
const fresh = walkBreadcrumbPath(101, "freshwater",
  new Map([[100, fRoot], [101, fFam]]),
  (t, src) => src === "freshwater" ? t.freshwater_parent_id : t.parent_id);
assert.strictEqual(fresh.length, 2);
assert.strictEqual(fresh[0].name, "Freshwater Fishes");
assert.strictEqual(fresh[1].name, "Cichlidae");

// E. Cycle cap — 30 hops max even when the chain loops back.
const ring = new Map();
for (let i = 0; i < 60; i++) ring.set(i, T(i, "n" + i, "genus", (i + 1) % 60));
assert.ok(
  walkBreadcrumbPath(0, "col", ring, (t) => t.parent_id).length <= 30);

// F. Partial cache — walker breaks at missing ancestor, does not throw.
const partial = new Map([[1, ani], [2, chor], [4, canis]]);
const partialResult = walkBreadcrumbPath(4, "col", partial, (t) => t.parent_id);
assert.strictEqual(partialResult.length, 1);
assert.strictEqual(partialResult[0].id, 4);

// G. Source discriminator — wrong source must break early.
const wrong = walkBreadcrumbPath(2, "col",
  new Map([[1, wAni], [2, wChor]]),
  (t, src) => src === "worms" ? t.worms_parent_id : t.parent_id);
// Under "col", the resolver reads parent_id = 999 (outside cache),
// so the walker breaks after the first segment.
assert.strictEqual(wrong.length, 1);

// H. Single-segment chain — focused is a root (parent_id null).
const rootSeg = walkBreadcrumbPath(1, "col",
  new Map([[1, ani]]), (t) => t.parent_id);
assert.strictEqual(rootSeg.length, 1);
assert.strictEqual(rootSeg[0].id, 1);

// I. Boundary — id 0 must be respected as a valid focus (legacy
// `while (currentId)` dropped id=0; the port fixes this).
const zeroRoot = T(0, "ZeroRoot", "kingdom", null);
const zero = walkBreadcrumbPath(0, "col",
  new Map([[0, zeroRoot]]), (t) => t.parent_id);
assert.strictEqual(zero.length, 1);
assert.strictEqual(zero[0].id, 0);

// J. Two-segment chain — focused + parent, oldest-first.
const two = walkBreadcrumbPath(2, "col",
  new Map([[1, ani], [2, chor]]), (t) => t.parent_id);
assert.strictEqual(two.length, 2);
assert.strictEqual(two[0].id, 1);
assert.strictEqual(two[1].id, 2);

// ====================================================================
// ODD-NTP-005 — TreeState-aware walkers + WoRMS edge reconstruction.
// ====================================================================

// Helper: build a fully-populated Taxon (coldp_id + worms_id +
// freshwater_id where applicable) so the source predicate + the
// breadcrumb walker can exercise every source in one harness.
const F = (id, name, rank, fields = {}) => ({
  id, name, rank, authorship: null,
  parent_id: fields.parent_id ?? null,
  worms_parent_id: fields.worms_parent_id ?? null,
  freshwater_parent_id: null,
  coldp_id: fields.coldp_id ?? null,
  worms_id: fields.worms_id ?? null,
  freshwater_id: fields.freshwater_id ?? null,
  freshwater_parent_id: fields.freshwater_parent_id ?? null,
  status: null, is_extinct: null, path: null,
  species_count: null, research_path_exists: null,
});

// K. deriveWoRMSEdges — empty cache → empty map.
assert.deepStrictEqual(
  [], [...walkForSource(null, "worms", emptyState()).map(s => s.id)]);
assert.deepStrictEqual(
  [], [...Object.keys(deriveEdges(emptyState()))]);

// L. deriveWoRMSEdges — CoL-only attachments never produce WoRMS
// edges (the source predicate drops them; WoRMS ancestry is
// reconstructed from WoRMS-passing attachments only).
const colOnlyState = {
  nodes: new Map([
    [1, F(1, "Animalia", "kingdom", { parent_id: null, coldp_id: "K" })],
    [2, F(2, "Chordata", "phylum", { parent_id: 1, coldp_id: "P" })],
  ]),
  childIdsByParent: new Map([[1, [2]]]),
};
assert.deepStrictEqual(
  [], [...Object.keys(deriveEdges(colOnlyState))]);

// M. deriveWoRMSEdges — WoRMS attachments build the reverse index
// (Animalia[worms_id=2] → children[Chordata, Arthropoda]; both are
// worms_id != null; reverse index maps Chordata → Animalia and
// Arthropoda → Animalia).
const wormState = {
  nodes: new Map([
    [1, F(1, "Biota", "superdomain", { worms_id: 1 })],
    [2, F(2, "Animalia", "kingdom", { parent_id: null, worms_id: 2 })],
    [3, F(3, "Chordata", "phylum", { parent_id: 2, worms_id: 1821 })],
    [4, F(4, "Arthropoda", "phylum", { parent_id: 2, worms_id: 1066 })],
    [5, F(5, "Mollusca", "phylum", { parent_id: 2, worms_id: 51 })],
  ]),
  childIdsByParent: new Map([[2, [3, 4, 5]]]),
};
const edges = deriveEdges(wormState);
assert.strictEqual(edges.get(3), 2, "Chordata → Animalia");
assert.strictEqual(edges.get(4), 2, "Arthropoda → Animalia");
assert.strictEqual(edges.get(5), 2, "Mollusca → Animalia");
assert.strictEqual(edges.has(1), false, "Biota has no cached WoRMS parent");
assert.strictEqual(edges.has(2), false, "Animalia itself has no cached WoRMS parent");

// N. walkBreadcrumbForSource — CoL chain via Taxon.parent_id.
// Reuses the CoL fixture from (B). Focused = Canis → Animalia, ...
// (using Taxon.parent_id + coldp_id != null guard).
const colState = {
  nodes: new Map([
    [1, F(1, "Animalia", "kingdom", { coldp_id: "K" })],
    [2, F(2, "Chordata", "phylum", { parent_id: 1, coldp_id: "P" })],
    [3, F(3, "Mammalia", "class", { parent_id: 2, coldp_id: "C" })],
    [4, F(4, "Canis", "genus", { parent_id: 3, coldp_id: "G" })],
  ]),
  childIdsByParent: new Map(),
};
const colWalk = walkForSource(4, "col", colState);
assert.deepStrictEqual(colWalk.map(s => s.id), [1, 2, 3, 4],
  "CoL chain oldest-first (Animalia → Canis)");

// O. walkBreadcrumbForSource — WoRMS chain via cached tree edges.
// Uses (M)'s wormState. Focused = Chordata (worms_id=1821) →
// Animalia (worms_id=2, cached as its WoRMS parent via childIds).
const wormsWalk = walkForSource(3, "worms", wormState);
assert.strictEqual(wormsWalk.length, 2);
assert.strictEqual(wormsWalk[0].id, 2, "WoRMS chain root = Animalia");
assert.strictEqual(wormsWalk[1].id, 3, "WoRMS chain focused = Chordata");

// P. walkBreadcrumbForSource — Freshwater chain via Taxon.freshwater_parent_id.
const freshState = {
  nodes: new Map([
    [100, F(100, "Freshwater Fishes", "collection",
            { freshwater_id: 1 })],
    [101, F(101, "Cichlidae", "family",
            { freshwater_id: 2, freshwater_parent_id: 100 })],
    [102, F(102, "Tilapia", "genus",
            { freshwater_id: 3, freshwater_parent_id: 101 })],
  ]),
  childIdsByParent: new Map(),
};
const freshWalk = walkForSource(102, "freshwater", freshState);
assert.deepStrictEqual(freshWalk.map(s => s.id), [100, 101, 102],
  "Freshwater chain oldest-first");

// Q. walkBreadcrumbForSource — source isolation. CoL ↔ WoRMS ↔
// Freshwater never cross. A taxon whose CoL parent_id points at a
// non-CoL row returns a 1-segment chain under CoL (the predicate
// stops the walk) but a full chain under the matching source.
const crossState = {
  nodes: new Map([
    [1, F(1, "Animalia", "kingdom", { worms_id: 2, coldp_id: null })],
    [2, F(2, "Chordata", "phylum",
          { parent_id: 1, coldp_id: "P", worms_id: 1821 })],
  ]),
  childIdsByParent: new Map(),
};
// Under CoL, Chordata's CoL parent (Animalia) fails the coldp_id
// != null guard → walker truncates to 1 segment.
const crossCol = walkForSource(2, "col", crossState);
assert.strictEqual(crossCol.length, 1, "CoL: Animalia drops out (coldp_id=null)");
// Under WoRMS, Chordata's cached edge finds Animalia via the
// childIdsByParent attachment (we add it here).
crossState.childIdsByParent.set(1, [2]);
const crossWorms = walkForSource(2, "worms", crossState);
assert.strictEqual(crossWorms.length, 2,
  "WoRMS: Animalia stays (worms_id=2) and Chordata appends");
assert.strictEqual(crossWorms[0].id, 1);
assert.strictEqual(crossWorms[1].id, 2);

// R. walkBreadcrumbForSource — cycle cap (BREADCRUMB_MAX_HOPS = 30).
// Build a 50-node WoRMS chain so the walker would loop forever;
// the cap truncates at 30 hops.
const ringState = {
  nodes: new Map(),
  childIdsByParent: new Map(),
};
for (let i = 0; i < 50; i++) {
  const id = i + 1;
  ringState.nodes.set(id, F(id, "n" + id, "genus", { worms_id: id + 1000 }));
}
// Build a chain 50→1 (i.e. n+1 → n) so focused id 50 walks back
// through 49 → 48 → ... → 1 (50 hops would loop).
for (let i = 1; i < 50; i++) {
  const next = i + 1;
  ringState.childIdsByParent.set(i, [next]);
}
// Last node chains back to first to force a loop.
ringState.childIdsByParent.set(50, [1]);
const ringWalk = walkForSource(50, "worms", ringState);
assert.ok(ringWalk.length <= 30, "WoRMS cycle cap at 30 hops");
assert.strictEqual(ringWalk.length, 30, "exactly 30 hops (cap hit)");

// S. walkBreadcrumbForSource — partial cache truncation. CoL row
// whose grandparent is NOT in the cache → walker breaks at the
// first missing ancestor instead of throwing.
const partialState = {
  nodes: new Map([
    [4, F(4, "Canis", "genus", { parent_id: 3, coldp_id: "G" })],
  ]),
  childIdsByParent: new Map(),
};
const partialWalk = walkForSource(4, "col", partialState);
assert.strictEqual(partialWalk.length, 1, "CoL: missing ancestors truncate");
assert.strictEqual(partialWalk[0].id, 4);

// T. walkBreadcrumbForSource — boundary: id 0 is a valid focus.
const zeroSourceState = {
  nodes: new Map([
    [0, F(0, "ZeroRoot", "kingdom", { coldp_id: "Z" })],
  ]),
  childIdsByParent: new Map(),
};
const zeroWalk = walkForSource(0, "col", zeroSourceState);
assert.strictEqual(zeroWalk.length, 1);
assert.strictEqual(zeroWalk[0].id, 0);

// U. walkBreadcrumbForSource — null focus → empty path.
assert.deepStrictEqual([], walkForSource(null, "col", colState));
assert.deepStrictEqual([], walkForSource(null, "worms", wormState));
assert.deepStrictEqual([], walkForSource(null, "freshwater", freshState));

// V. deriveWoRMSEdges — multi-level chain. Biota (worms_id=1) →
// Animalia (worms_id=2) → Chordata (worms_id=1821). All three are
// in the cache with cached parent → child attachments. The reverse
// index must record Chordata → Animalia and Animalia → Biota.
const deepWorms = {
  nodes: new Map([
    [1, F(1, "Biota", "superdomain", { worms_id: 1 })],
    [2, F(2, "Animalia", "kingdom",
          { parent_id: null, worms_id: 2 })],
    [3, F(3, "Chordata", "phylum",
          { parent_id: 2, worms_id: 1821 })],
    [4, F(4, "Mammalia", "class",
          { parent_id: 3, worms_id: 1837 })],
  ]),
  childIdsByParent: new Map([
    [1, [2]],
    [2, [3]],
    [3, [4]],
  ]),
};
const deepEdges = deriveEdges(deepWorms);
assert.strictEqual(deepEdges.get(2), 1, "Animalia → Biota");
assert.strictEqual(deepEdges.get(3), 2, "Chordata → Animalia");
assert.strictEqual(deepEdges.get(4), 3, "Mammalia → Chordata");
const deepWalk = walkForSource(4, "worms", deepWorms);
assert.deepStrictEqual(deepWalk.map(s => s.id), [1, 2, 3, 4],
  "Deep WoRMS chain oldest-first");

// W. deriveWoRMSEdges — mixed payload: child fails WoRMS source
// predicate (no worms_id) even though the parent is WoRMS-passing.
// Such attachments do NOT contribute to the reverse index (the
// walker must not back-walk through a non-WoRMS child into a
// WoRMS ancestor).
const mixedState = {
  nodes: new Map([
    [1, F(1, "Animalia", "kingdom",
          { parent_id: null, worms_id: 2 })],
    [2, F(2, "Chordata", "phylum",
          { parent_id: 1, worms_id: 1821 })],
    [3, F(3, "MolluscaCoL", "phylum",
          { parent_id: 1, coldp_id: "MC" })], // CoL-only, no worms_id
  ]),
  childIdsByParent: new Map([[1, [2, 3]]]),
};
const mixedEdges = deriveEdges(mixedState);
assert.strictEqual(mixedEdges.get(2), 1, "Chordata → Animalia (WoRMS)");
assert.ok(!mixedEdges.has(3), "MolluscaCoL excluded (no worms_id)");
// Walk Chordata via WoRMS: Animalia → Chordata (full chain).
const mixedWalk = walkForSource(2, "worms", mixedState);
assert.deepStrictEqual(mixedWalk.map(s => s.id), [1, 2]);
// Walk MolluscaCoL via WoRMS: worm predicate filters it out →
// walker returns single-segment (focused only) because the
// walker cannot back-walk through a non-WoRMS taxon.
const mixedFail = walkForSource(3, "worms", mixedState);
assert.strictEqual(mixedFail.length, 1, "CoL-only row under WoRMS: 1-segment truncation");

// X. walkBreadcrumbForSource — empty cache returns [].
const emptyChain = walkForSource(999, "col", {
  nodes: new Map(),
  childIdsByParent: new Map(),
});
assert.deepStrictEqual([], emptyChain);

// Y. deriveWoRMSEdges — first-source-safe-parent wins on duplicate
// child ids (deterministic; a corrupt cache can in principle
// have the same child id under two parents).
const dupState = {
  nodes: new Map([
    [1, F(1, "BiotaA", "superdomain", { worms_id: 1 })],
    [2, F(2, "BiotaB", "superdomain", { worms_id: 2 })],
    [3, F(3, "Child", "kingdom", { worms_id: 3 })],
  ]),
  childIdsByParent: new Map([
    [1, [3]],
    [2, [3]],
  ]),
};
const dupEdges = deriveEdges(dupState);
assert.strictEqual(dupEdges.get(3), 1,
  "first WoRMS-safe parent wins (insertion-order deterministic)");

process.stdout.write("PASS\n");
"""


def test_compiled_walker_passes_runtime_contract(
    tmp_path: Path, require_toolchain: None,
) -> None:
    """Under Node (ES2022 + CJS), `walkBreadcrumbPath` covers A–J:
    null+unknown focus, CoL/WoRMS/freshwater chains, cycle cap, partial
    cache, source discriminator, root focus, id 0 boundary, two-segment.
    `walkBreadcrumbForSource` covers K–X: empty / CoL / WoRMS / Freshwater
    chains, source isolation (CoL ↔ WoRMS ↔ Freshwater never cross),
    cycle cap per source, partial cache truncation, id 0 boundary,
    null focus, multi-level chains, mixed-payload filtering.
    `deriveWoRMSEdges` covers K–Y: empty / CoL-only / WoRMS-only /
    deep chains / mixed payloads / duplicate-child determinism."""
    for p in (BREADCRUMB_PATH_FILE, DOMAIN_FILE):
        if not p.is_file():
            pytest.skip(f"missing required source: {p}")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    result = _run_tsc(out_dir)
    assert result.returncode == 0, (
        f"breadcrumb-path.ts failed to compile under strict tsc.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    compiled = out_dir / "presentation" / "breadcrumb-path.js"
    assert compiled.is_file(), (
        f"tsc did not emit a compiled module at {compiled}. "
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    harness = tmp_path / "harness.cjs"
    harness.write_text(_NODE_HARNESS)
    result = subprocess.run(
        ["node", str(harness), str(compiled)],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0 and result.stdout.strip() == "PASS", (
        f"walkBreadcrumbPath runtime harness failed.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
