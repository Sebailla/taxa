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
ROW_FORMAT_FILE = MODULE_DIR / "presentation" / "row-format.ts"
BARREL_FILE = MODULE_DIR / "index.ts"
DOMAIN_FILE = MODULE_DIR / "domain" / "taxon.ts"
FOLDER_TAB_FILE = MODULE_DIR / "presentation" / "FolderTab.tsx"


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
        "EMPTY_TREE_STATE", "withRoots", "withRootsForSource",
        "childIds", "isExpanded",
        "expand", "collapse", "toggleExpand",
        "attachChildren", "attachChildrenForSource",
        "setLoadStatus", "loadStatus",
        "sourceMatches", "filterChildrenForSource",
        "hasFreshwaterRoot", "availableSourcesFor",
        "resetSourceState",
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


# ---------------------------------------------------------------------------
# ODD-NTP-004 — row-format helper (per-row pure format functions).
#
# Pins the React port's per-row identity contract:
#   - rank label / italic classifier / scientific-name class
#   - realm tint derived from taxon.path
#   - status dot descriptor (accepted/synonym/unknown)
#   - species-count badge formatter
#   - source-info tooltip (CoL-only / WoRMS-only / cross-link)
#   - WoRMS URL builder
#   - materialized-folder predicate
# ---------------------------------------------------------------------------

def test_row_format_file_exists() -> None:
    assert ROW_FORMAT_FILE.is_file(), (
        f"missing row-format helper: {ROW_FORMAT_FILE}. ODD-NTP-004 ships this file."
    )
    assert ROW_FORMAT_FILE.suffix == ".ts", "row-format must be `.ts` (no JSX)."


def test_row_format_imports_only_from_domain_or_sibling() -> None:
    """ODD-NTP-004: row-format.ts depends only on the taxonomy
    domain (`../domain/taxon`) and on the sibling `tree-state.ts`
    for the `TreeSource` literal. spec.md rule 4 + ESLint
    `no-restricted-imports`. The helper stays framework-free."""
    if not ROW_FORMAT_FILE.is_file():
        pytest.skip("row-format.ts not present yet")
    text = ROW_FORMAT_FILE.read_text()
    for src in re.findall(r'from\s+["\']([^"\']+)["\']', text):
        assert src.startswith(("../domain/", "./tree-state")), (
            f"row-format.ts imports from {src!r}; must be ../domain/ or ./tree-state only."
        )


@pytest.mark.parametrize("token", _FORBIDDEN)
def test_row_format_source_free_of_forbidden_tokens(token: str, row_format_text: str) -> None:
    assert token not in row_format_text, (
        f"row-format.ts must stay free of {token!r}; spec.md rule 4."
    )


@pytest.fixture()
def row_format_text(require_toolchain: None) -> str:
    if not ROW_FORMAT_FILE.exists():
        pytest.skip("row-format.ts not present yet")
    return ROW_FORMAT_FILE.read_text()


def test_row_format_exports_required_helpers(row_format_text: str) -> None:
    """ODD-NTP-004: row-format.ts must export every per-row
    helper the React tree reads (rank label / italic classifier /
    scientific-name class / depth class / realm / status dot
    descriptor / species-count badge / WoRMS URL builder /
    materialized-folder predicate)."""
    for name in (
        "rankLabel", "rankPluralFor", "isItalicRank",
        "scientificNameClass", "scientificNameDepthClass",
        "realmForPath", "statusDotDescriptor", "speciesCountBadge",
        "wormsUrlFor", "hasMaterializedFolder",
    ):
        pattern = rf"export\s+(?:async\s+)?function\s+{name}\b|export\s+const\s+{name}\b"
        assert re.search(pattern, row_format_text), (
            f"row-format.ts must export `{name}`."
        )
    assert "export interface StatusDotDescriptor" in row_format_text, (
        "row-format.ts must export the StatusDotDescriptor interface."
    )


def test_barrel_reexports_row_format() -> None:
    """ODD-NTP-004: the public taxonomy barrel re-exports the
    row-format helpers so consumers can import them via
    `@taxa/taxonomy` (spec.md rule 5 — no deep imports)."""
    if not BARREL_FILE.exists():
        pytest.skip("barrel not present yet")
    text = BARREL_FILE.read_text()
    for name in (
        "rankLabel", "rankPluralFor", "isItalicRank",
        "scientificNameClass", "scientificNameDepthClass",
        "realmForPath", "statusDotDescriptor", "speciesCountBadge",
        "wormsUrlFor", "hasMaterializedFolder",
        "StatusDotDescriptor",
    ):
        assert name in text, f"barrel must re-export {name}."
    assert "row-format" in text, "barrel must reference ./presentation/row-format.js."


def _run_tsc(out_dir: Path) -> subprocess.CompletedProcess:
    sources: list[str] = []
    if DOMAIN_FILE.is_file():
        sources.append(str(DOMAIN_FILE))
    if TREE_STATE_FILE.is_file():
        sources.append(str(TREE_STATE_FILE))
    if ROW_FORMAT_FILE.is_file():
        sources.append(str(ROW_FORMAT_FILE))
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
const rf = require(path.resolve(process.argv[3]));
// Minimal Taxon-shaped fixture — every source-affordance field the
// ODD-NTP-002 helpers read is set explicitly so the source contract
// is reproducible from a hand-rolled constructor (the canonical
// `Taxon` carries more nullable fields; the unused ones default to
// `undefined` and the helpers never read them).
const T = (id, name, rank, parentId, sourceIds = {}) => ({
  id, name, rank, authorship: null, parent_id: parentId,
  coldp_id: null, worms_id: null, freshwater_id: null,
  freshwater_parent_id: null,
  ...sourceIds,
});
const ANI = T(1, "Animalia", "kingdom", null, { coldp_id: "K", worms_id: 2 });
const ARTH = T(7, "Arthropoda", "phylum", 1, { coldp_id: "64HXH" }); // CoL-only
const CHOR = T(2, "Chordata", "phylum", 1, { coldp_id: "64HXG", worms_id: 1821 });
const MAMM = T(3, "Mammalia", "class", 2, { coldp_id: "64HXJ", worms_id: 367 });
const CANIS = T(4, "Canis", "genus", 3, { coldp_id: "64HXM", worms_id: 137093 });
const BIOTA = T(5, "Biota", "superdomain", null, { worms_id: 1 });
const FW = T(100, "Freshwater Fishes", "collection", null, { freshwater_id: 1 });
const FW_FAM = T(101, "Cichlidae", "family", 100, { freshwater_id: 12 });

// A. Empty state.
const e = ts.EMPTY_TREE_STATE;
assert.strictEqual(e.rootIds.length, 0);
assert.strictEqual(e.nodes.size, 0);
assert.deepStrictEqual(ts.childIds(e, 999), []);
assert.strictEqual(ts.isExpanded(e, 1), false);
assert.strictEqual(ts.loadStatus(e, 1), "idle");
// ODD-NTP-003: empty state carries a `showAll` set (initially empty).
assert.ok(e.showAll instanceof Set, "EMPTY_TREE_STATE.showAll is a Set");
assert.strictEqual(e.showAll.size, 0, "EMPTY_TREE_STATE.showAll starts empty");
assert.strictEqual(ts.expandedTierCount(e), 0, "expandedTierCount == 0 on empty");
assert.strictEqual(ts.PAGE_SIZE, 5, "PAGE_SIZE == 5 (matches legacy oracle)");
assert.strictEqual(ts.isLeafRank("species"), true, "species is a leaf");
assert.strictEqual(ts.isLeafRank("subspecies"), true, "subspecies is a leaf");
assert.strictEqual(ts.isLeafRank("genus"), false, "genus is not a leaf");
assert.strictEqual(ts.isLeafRank("kingdom"), false, "kingdom is not a leaf");
assert.strictEqual(ts.isLeafRank("unranked"), false, "unranked is not a leaf");
assert.strictEqual(ts.isLeafRank("realm"), false, "realm is not a leaf");

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

// H. ODD-NTP-002 — sourceMatches nullability contract.
assert.strictEqual(ts.sourceMatches(ANI, "col"), true, "CoL: coldp_id set");
assert.strictEqual(ts.sourceMatches(ARTH, "col"), true, "CoL: coldp_id-only row");
assert.strictEqual(ts.sourceMatches(BIOTA, "col"), false, "CoL: worms-only row excluded");
assert.strictEqual(ts.sourceMatches(ANI, "worms"), true, "WoRMS: worms_id set");
assert.strictEqual(ts.sourceMatches(ARTH, "worms"), false, "WoRMS: CoL-only row excluded");
assert.strictEqual(ts.sourceMatches(BIOTA, "worms"), true, "WoRMS: Biota row");
assert.strictEqual(ts.sourceMatches(FW, "worms"), false, "WoRMS: freshwater-only row excluded");
assert.strictEqual(ts.sourceMatches(FW, "freshwater"), true, "Freshwater: synthetic root");
assert.strictEqual(ts.sourceMatches(FW_FAM, "freshwater"), true, "Freshwater: family row");
assert.strictEqual(ts.sourceMatches(ANI, "freshwater"), false, "Freshwater: CoL+WoRMS row excluded");
assert.strictEqual(ts.sourceMatches(BIOTA, "freshwater"), false, "Freshwater: Biota excluded");

// I. ODD-NTP-002 — withRootsForSource preserves foreign ids on `nodes`,
// exposes only source-matching ids on `rootIds`.
let raws = [BIOTA, ANI, ARTH, FW];
const sCol = ts.withRootsForSource(e, raws, "col");
assert.deepStrictEqual([...sCol.rootIds], [1, 7], "CoL view: Animalia + Arthropoda only");
// `nodes` retains every fetched taxon so a later source switch can
// re-surface them without a re-fetch.
assert.strictEqual(sCol.nodes.size, 4);
assert.ok(sCol.nodes.has(5) && sCol.nodes.has(100));
const sWorms = ts.withRootsForSource(sCol, raws, "worms");
assert.deepStrictEqual([...sWorms.rootIds], [5, 1], "WoRMS view: Biota + Animalia");
// `nodes` carries the foreign ids across source switches (Biota +
// Freshwater remain on `nodes` even though they're hidden under CoL).
assert.strictEqual(sWorms.nodes.size, 4);
assert.ok(sWorms.nodes.has(5) && sWorms.nodes.has(100) && sWorms.nodes.has(7));
const sFresh = ts.withRootsForSource(sCol, raws, "freshwater");
assert.deepStrictEqual([...sFresh.rootIds], [100], "Freshwater view: synthetic root only");

// J. ODD-NTP-002 — filterChildrenForSource + attachChildrenForSource
// apply the source predicate before the visible child list is built.
// `attachChildren` records every row on `nodes` but `childIds` returns
// the source-filtered sequence (or via `attachChildrenForSource`
// directly).
const kids = [CHOR, ARTH, FW_FAM]; // CoL / WoRMS / Freshwater membership
const childSCol = ts.attachChildrenForSource(e, 1, kids, "col");
assert.deepStrictEqual([...ts.childIds(childSCol, 1)], [2, 7], "CoL child filter keeps Chordata + Arthropoda");
const childSWorms = ts.attachChildrenForSource(e, 1, kids, "worms");
assert.deepStrictEqual([...ts.childIds(childSWorms, 1)], [2], "WoRMS child filter keeps Chordata only");
const childSFresh = ts.attachChildrenForSource(e, 1, kids, "freshwater");
assert.deepStrictEqual([...ts.childIds(childSFresh, 1)], [101], "Freshwater child filter keeps Cichlidae only");
// Load status transitions to `loaded` regardless of how many children pass the filter.
assert.strictEqual(ts.loadStatus(childSCol, 1), "loaded");
assert.strictEqual(ts.loadStatus(childSWorms, 1), "loaded");
assert.strictEqual(ts.loadStatus(childSFresh, 1), "loaded");

// K. ODD-NTP-002 — hasFreshwaterRoot + availableSourcesFor.
assert.strictEqual(ts.hasFreshwaterRoot([BIOTA, ANI]), false, "no freshwater in CoL-only roots");
assert.strictEqual(ts.hasFreshwaterRoot([BIOTA, ANI, FW]), true, "Freshwater root detected");
assert.deepStrictEqual(ts.availableSourcesFor([BIOTA, ANI]), ["col", "worms"], "no Freshwater toggle");
assert.deepStrictEqual(ts.availableSourcesFor([BIOTA, ANI, FW]), ["col", "worms", "freshwater"], "Freshwater toggle appended");

// L. ODD-NTP-002 — resetSourceState clears every source-bound field
// while preserving `nodes` (the cached projections survive the reset
// so a later source switch can re-surface them without a re-fetch).
let sFilled = e;
sFilled = ts.withRoots(sFilled, [ANI, FW]);
sFilled = ts.attachChildren(sFilled, ANI.id, [CHOR, ARTH]);
sFilled = ts.expand(sFilled, ANI.id);
sFilled = ts.setLoadStatus(sFilled, ANI.id, "loaded");
sFilled = ts.setShowAll(sFilled, ANI.id, CHOR.rank, true); // ODD-NTP-003: showAll set
assert.strictEqual(sFilled.showAll.size, 1, "showAll populated before reset");
const reset = ts.resetSourceState(sFilled);
assert.deepStrictEqual([...reset.rootIds], [], "rootIds cleared");
assert.deepStrictEqual([...reset.expandedIds], [], "expanded set cleared");
assert.deepStrictEqual([...reset.childIdsByParent.keys()], [], "child cache cleared");
assert.deepStrictEqual([...reset.loadStatus.keys()], [], "load status cleared");
assert.deepStrictEqual([...reset.showAll], [], "showAll cleared (ODD-NTP-003)");
assert.strictEqual(reset.nodes, sFilled.nodes, "nodes map is preserved (identity-equal)");
// A subsequent source-aware merge re-surfaces the cached roots without
// re-fetching — the foreign-id preservation contract.
const recovered = ts.withRootsForSource(reset, [ANI, FW], "worms");
assert.deepStrictEqual([...recovered.rootIds], [1], "WoRMS view re-surfaces Animalia only");

// M. ODD-NTP-003 — groupChildrenByRank: rank order matches the
// canonical breadth axis (broadest first); source filter drops
// foreign rows; PAGE_SIZE caps the visible slice; showAll lifts
// the cap. Mirrors legacy `web/tree.js::renderNode` byte-for-byte.
let sG = e;
sG = ts.withRoots(sG, [ANI]);
sG = ts.attachChildren(sG, ANI.id, [CHOR, ARTH, MAMM]);
// Add two phyla + two classes so the PAGE_SIZE staircase has more
// than PAGE_SIZE rows to fan out across rank tiers.
const ARTH2 = T(8, "Brachiopoda", "phylum", 1, { coldp_id: "64HXK" });
const ARTH3 = T(9, "Bryozoa", "phylum", 1, { coldp_id: "64HXL" });
const MAMM2 = T(10, "Reptilia", "class", 2, { coldp_id: "64HXN" });
const MAMM3 = T(11, "Aves", "class", 2, { coldp_id: "64HXP" });
sG = ts.attachChildren(sG, ANI.id, [ARTH2, ARTH3, MAMM2, MAMM3]);

const groupsCol = ts.groupChildrenByRank(sG, ANI.id, "col");
// CoL view: 4 phyla + 3 classes = 2 groups, broadest-first.
assert.strictEqual(groupsCol.length, 2, "CoL: phylum + class groups");
assert.strictEqual(groupsCol[0].rank, "phylum", "phylum tier first (broadest-first)");
assert.strictEqual(groupsCol[0].count, 4, "phylum tier has 4 children");
assert.strictEqual(groupsCol[1].rank, "class", "class tier second");
assert.strictEqual(groupsCol[1].count, 3, "class tier has 3 children");
// PAGE_SIZE=5 → all 4 phyla visible, 0 remaining.
assert.strictEqual(groupsCol[0].visibleIds.length, 4, "phylum tier fully visible (PAGE_SIZE=5)");
assert.strictEqual(groupsCol[0].remaining, 0, "phylum tier has 0 remaining");
assert.strictEqual(groupsCol[1].visibleIds.length, 3, "class tier fully visible (PAGE_SIZE=5)");
assert.strictEqual(groupsCol[1].remaining, 0, "class tier has 0 remaining");
assert.strictEqual(groupsCol[0].fullyShown, false, "phylum tier not fullyShown by default");
assert.strictEqual(groupsCol[1].fullyShown, false, "class tier not fullyShown by default");
// Children within a group preserve insertion order (no reshuffle).
assert.deepStrictEqual(
  [...groupsCol[0].visibleIds], [CHOR.id, ARTH.id, ARTH2.id, ARTH3.id],
  "phylum tier preserves insertion order",
);

// N. ODD-NTP-003 — PAGE_SIZE staircase activates when a tier carries
// more than PAGE_SIZE children. Build a 7-phylum family, confirm
// only PAGE_SIZE=5 visible until showAll flips.
const PHYLUM_LIST = [
  T(20, "P1", "phylum", 1, { coldp_id: "c1" }),
  T(21, "P2", "phylum", 1, { coldp_id: "c2" }),
  T(22, "P3", "phylum", 1, { coldp_id: "c3" }),
  T(23, "P4", "phylum", 1, { coldp_id: "c4" }),
  T(24, "P5", "phylum", 1, { coldp_id: "c5" }),
  T(25, "P6", "phylum", 1, { coldp_id: "c6" }),
  T(26, "P7", "phylum", 1, { coldp_id: "c7" }),
];
const PHYLUM_PARENT = T(27, "Parent", "domain", null, { coldp_id: "P" });
let sP = e;
sP = ts.withRoots(sP, [PHYLUM_PARENT]);
sP = ts.attachChildren(sP, PHYLUM_PARENT.id, PHYLUM_LIST);
const groupsP = ts.groupChildrenByRank(sP, PHYLUM_PARENT.id, "col");
assert.strictEqual(groupsP.length, 1, "single phylum tier");
assert.strictEqual(groupsP[0].count, 7, "tier has 7 children");
assert.strictEqual(groupsP[0].visibleIds.length, ts.PAGE_SIZE, "PAGE_SIZE cap honored");
assert.strictEqual(groupsP[0].remaining, 7 - ts.PAGE_SIZE, "remaining == count - visibleIds");
assert.strictEqual(groupsP[0].fullyShown, false, "not fullyShown before toggle");
// Toggle showAll and confirm the cap lifts.
const sPAll = ts.setShowAll(sP, PHYLUM_PARENT.id, "phylum", true);
const groupsPAll = ts.groupChildrenByRank(sPAll, PHYLUM_PARENT.id, "col");
assert.strictEqual(groupsPAll[0].visibleIds.length, 7, "showAll lifts the cap");
assert.strictEqual(groupsPAll[0].remaining, 0, "showAll drains the remaining count");
assert.strictEqual(groupsPAll[0].fullyShown, true, "fullyShown == true after setShowAll(true)");

// O. ODD-NTP-003 — setShowAll / toggleShowAll / isShowAll contract.
const key = `${PHYLUM_PARENT.id}::phylum`;
assert.strictEqual(ts.isShowAll(sP, PHYLUM_PARENT.id, "phylum"), false, "absent by default");
const sPSet = ts.setShowAll(sP, PHYLUM_PARENT.id, "phylum", true);
assert.strictEqual(ts.isShowAll(sPSet, PHYLUM_PARENT.id, "phylum"), true, "setShowAll(true) adds");
assert.strictEqual(sPSet.showAll.has(key), true, "showAll set contains key");
const sPSetIdem = ts.setShowAll(sPSet, PHYLUM_PARENT.id, "phylum", true);
assert.strictEqual(sPSetIdem, sPSet, "setShowAll(true) is idempotent (reference-equal)");
const sPClear = ts.setShowAll(sPSet, PHYLUM_PARENT.id, "phylum", false);
assert.strictEqual(ts.isShowAll(sPClear, PHYLUM_PARENT.id, "phylum"), false, "setShowAll(false) removes");
assert.strictEqual(sPClear.showAll.has(key), false, "showAll set drops key");
const sPClearIdem = ts.setShowAll(sPClear, PHYLUM_PARENT.id, "phylum", false);
assert.strictEqual(sPClearIdem, sPClear, "setShowAll(false) is idempotent (reference-equal)");
// toggleShowAll flips the flag both ways.
const sT1 = ts.toggleShowAll(sP, PHYLUM_PARENT.id, "phylum");
assert.strictEqual(ts.isShowAll(sT1, PHYLUM_PARENT.id, "phylum"), true, "toggle absent→present");
const sT2 = ts.toggleShowAll(sT1, PHYLUM_PARENT.id, "phylum");
assert.strictEqual(ts.isShowAll(sT2, PHYLUM_PARENT.id, "phylum"), false, "toggle present→absent");

// P. ODD-NTP-003 — source-aware groupChildrenByRank: WoRMS view
// drops CoL-only phyla (Arthropoda is CoL-only; Chordata + Brachiopoda
// are CoL+WoRMS; Bryozoa is CoL-only). Mixed payload → WoRMS view
// shows only the 2 with worms_id.
const ARTH_W = T(28, "Arthropoda-W", "phylum", 1, { coldp_id: "64HXH", worms_id: 1066 });
const BRAC_W = T(29, "Brachiopoda-W", "phylum", 1, { coldp_id: "64HXK", worms_id: 1806 });
const BRYO_W = T(30, "Bryozoa-W", "phylum", 1, { coldp_id: "64HXL" }); // CoL-only
const sWParent = T(31, "Animalia-W", "kingdom", null, { coldp_id: "K2", worms_id: 2 });
let sW = e;
sW = ts.withRoots(sW, [sWParent]);
sW = ts.attachChildren(sW, sWParent.id, [ARTH_W, BRAC_W, BRYO_W]);
const groupsWorms = ts.groupChildrenByRank(sW, sWParent.id, "worms");
assert.strictEqual(groupsWorms.length, 1, "WoRMS view: one phylum tier");
assert.strictEqual(groupsWorms[0].count, 2, "WoRMS view: only CoL+WoRMS rows pass");
assert.deepStrictEqual(
  [...groupsWorms[0].visibleIds], [ARTH_W.id, BRAC_W.id],
  "WoRMS view: phylum tier preserves source-filtered insertion order",
);
// CoL view of the same payload keeps all three.
const groupsWCol = ts.groupChildrenByRank(sW, sWParent.id, "col");
assert.strictEqual(groupsWCol[0].count, 3, "CoL view: all 3 phyla pass");

// Q. ODD-NTP-003 — empty group rendering. No cached children → empty
// tiers list; tier header slot is dropped. Matches legacy oracle.
const emptyGroups = ts.groupChildrenByRank(e, 999, "col");
assert.deepStrictEqual([...emptyGroups], [], "no cached children → empty groups");
// Mixed payload with one source-filtered row → tier header count > 1
// suppressed (only renders when count > 1, per legacy renderTierHeader).
const solo = T(40, "Solo", "class", 1, { coldp_id: "x" });
const sSolo = ts.attachChildren(e, 1, [solo]);
const soloGroups = ts.groupChildrenByRank(sSolo, 1, "col");
assert.strictEqual(soloGroups.length, 1, "single-row group is still produced");
assert.strictEqual(soloGroups[0].count, 1, "single-row group has count=1");
assert.strictEqual(soloGroups[0].visibleIds.length, 1, "single-row group shows 1 child");
assert.strictEqual(soloGroups[0].remaining, 0, "single-row group has 0 remaining");

// R. ODD-NTP-003 — autoUnrollForSource: WoRMS / Freshwater view
// marks every tier of an expanded parent as showAll on expansion.
// CoL view is a no-op. Mirrors legacy `web/nav.js::toggleExpand`.
// Mixed payload → only the source-matching rank tiers are added.
const ARTH_W2 = T(50, "Arthropoda-W2", "phylum", 1, { coldp_id: "c", worms_id: 1066 });
const CHOR_W = T(51, "Chordata-W", "phylum", 1, { coldp_id: "d", worms_id: 1821 });
const sWormsParent = T(52, "Biota-W", "superdomain", null, { worms_id: 1 });
let sAuto = e;
sAuto = ts.withRoots(sAuto, [sWormsParent]);
sAuto = ts.attachChildren(sAuto, sWormsParent.id, [ARTH_W2, CHOR_W]);
// CoL source: no-op (no source-matching rows; nothing to unroll).
const sAutoCol = ts.autoUnrollForSource(sAuto, sWormsParent.id, "col");
assert.strictEqual(sAutoCol, sAuto, "CoL: autoUnrollForSource is identity-equal no-op");
// WoRMS source: both tiers added to showAll (single rank group of
// 2 phyla — one tier key for "phylum").
const sAutoWorms = ts.autoUnrollForSource(sAuto, sWormsParent.id, "worms");
assert.strictEqual(sAutoWorms.showAll.size, 1, "WoRMS: 1 tier key added");
assert.strictEqual(
  sAutoWorms.showAll.has(`${sWormsParent.id}::phylum`),
  true, "WoRMS: phylum tier unrolled",
);
// Mixed-rank WoRMS parent: every rank group gets its own key.
const BIOTA_KIDS = [
  T(60, "Animalia-K", "kingdom", 52, { coldp_id: "K", worms_id: 2 }),
  T(61, "Plantae-K", "kingdom", 52, { coldp_id: "P", worms_id: 3 }),
];
const sMix = ts.attachChildren(sAuto, sWormsParent.id, BIOTA_KIDS);
const sMixUnroll = ts.autoUnrollForSource(sMix, sWormsParent.id, "worms");
assert.strictEqual(sMixUnroll.showAll.size, 2, "WoRMS: phylum + kingdom tier keys added (2 ranks)");
assert.strictEqual(
  sMixUnroll.showAll.has(`${sWormsParent.id}::phylum`), true,
  "WoRMS: phylum tier unrolled",
);
assert.strictEqual(
  sMixUnroll.showAll.has(`${sWormsParent.id}::kingdom`), true,
  "WoRMS: kingdom tier unrolled",
);
// Idempotent: re-running autoUnrollForSource on a state where every
// tier is already unrolled returns reference-equal state.
const sMixReUnroll = ts.autoUnrollForSource(sMixUnroll, sWormsParent.id, "worms");
assert.strictEqual(sMixReUnroll, sMixUnroll, "autoUnrollForSource idempotent when fully unrolled");

// S. ODD-NTP-003 — clearShowAll + clearExpansion semantics.
// clearShowAll only drops showAll; expanded stays.
const sKept = ts.expand(sP, PHYLUM_PARENT.id);
const sShowCleared = ts.clearShowAll(ts.setShowAll(sKept, PHYLUM_PARENT.id, "phylum", true));
assert.strictEqual(sShowCleared.showAll.size, 0, "clearShowAll drops showAll");
assert.strictEqual(ts.isExpanded(sShowCleared, PHYLUM_PARENT.id), true, "clearShowAll preserves expansion");
// Identity-equal no-op when showAll is already empty — the legacy
// `web/nav.js::collapseAll` early-return at the start of the
// handler.
assert.strictEqual(ts.clearShowAll(sKept), sKept, "clearShowAll is identity-equal no-op on absent state");
// clearExpansion drops both expanded + showAll.
const sCleared = ts.clearExpansion(ts.setShowAll(sKept, PHYLUM_PARENT.id, "phylum", true));
assert.strictEqual(sCleared.expandedIds.size, 0, "clearExpansion drops expanded");
assert.strictEqual(sCleared.showAll.size, 0, "clearExpansion drops showAll");
assert.strictEqual(sCleared.childIdsByParent, sKept.childIdsByParent, "clearExpansion preserves child cache");
assert.strictEqual(sCleared.loadStatus, sKept.loadStatus, "clearExpansion preserves load status");
assert.strictEqual(sCleared.nodes, sKept.nodes, "clearExpansion preserves nodes");
assert.strictEqual(ts.clearExpansion(e), e, "clearExpansion identity-equal no-op on empty state");
// expandedTierCount tracks both sets.
assert.strictEqual(ts.expandedTierCount(sKept), 1, "expanded-only → 1");
const sBoth = ts.setShowAll(sKept, PHYLUM_PARENT.id, "phylum", true);
assert.strictEqual(ts.expandedTierCount(sBoth), 2, "expanded+showAll → 2");

// T. ODD-NTP-003 — groupChildrenByRank preserves insertion order
// inside a rank group even when the source filter removes rows.
// The fetched sequence drives the order; the source predicate
// never reshuffles rows the legacy tree would render sequentially.
const MIX = [
  T(70, "P-A", "phylum", 1, { coldp_id: "a", worms_id: 11 }),
  T(71, "P-B", "phylum", 1, { coldp_id: "b" }), // CoL-only — excluded in WoRMS
  T(72, "P-C", "phylum", 1, { coldp_id: "c", worms_id: 13 }),
];
const MIX_PARENT = T(73, "Mix-Parent", "kingdom", null, { coldp_id: "M", worms_id: 1 });
let sMix2 = e;
sMix2 = ts.withRoots(sMix2, [MIX_PARENT]);
sMix2 = ts.attachChildren(sMix2, MIX_PARENT.id, MIX);
const groupsMixWorms = ts.groupChildrenByRank(sMix2, MIX_PARENT.id, "worms");
assert.deepStrictEqual(
  [...groupsMixWorms[0].visibleIds], [70, 72],
  "WoRMS view: insertion order preserved within rank group (70, 72)",
);

// U. ODD-NTP-003 — groupChildrenByRank returns groups sorted by
// canonical rank breadth (broadest-first). Mixed ranks under one
// parent → kingdom, phylum, class in that order.
const RANKS = [
  T(80, "Class-K", "class", 1, { coldp_id: "c" }),
  T(81, "Kingdom-K", "kingdom", 1, { coldp_id: "k" }),
  T(82, "Phylum-K", "phylum", 1, { coldp_id: "p" }),
];
let sRanks = e;
sRanks = ts.withRoots(sRanks, [T(83, "Root", "domain", null, { coldp_id: "r" })]);
sRanks = ts.attachChildren(sRanks, 83, RANKS);
const groupsRanks = ts.groupChildrenByRank(sRanks, 83, "col");
assert.strictEqual(groupsRanks.length, 3, "three rank groups");
assert.strictEqual(groupsRanks[0].rank, "kingdom", "kingdom first (broadest)");
assert.strictEqual(groupsRanks[1].rank, "phylum", "phylum second");
assert.strictEqual(groupsRanks[2].rank, "class", "class last (narrowest)");

// V. ODD-NTP-004 — row-format pure helpers (port of web/format.js
// + the source-info / wormsUrl / hasMaterialized helpers from
// web/tree.js).
assert.strictEqual(rf.rankLabel("genus"), "Genus", "rankLabel upper-cases the first letter");
assert.strictEqual(rf.rankLabel("species"), "Species", "rankLabel handles species too");
assert.strictEqual(rf.rankLabel("unranked"), "Unranked", "rankLabel handles unranked clade rank");
assert.strictEqual(rf.rankPluralFor("phylum"), "phyla", "rankPluralFor uses irregular plurals");
assert.strictEqual(rf.rankPluralFor("family"), "families", "rankPluralFor handles families");
assert.strictEqual(rf.rankPluralFor("order"), "Orders", "rankPluralFor falls back to English +s");
assert.strictEqual(rf.isItalicRank("genus"), true, "genus is italic");
assert.strictEqual(rf.isItalicRank("subgenus"), true, "subgenus is italic");
assert.strictEqual(rf.isItalicRank("species"), true, "species is italic");
assert.strictEqual(rf.isItalicRank("subspecies"), true, "subspecies is italic");
assert.strictEqual(rf.isItalicRank("variety"), true, "variety is italic");
assert.strictEqual(rf.isItalicRank("form"), true, "form is italic");
assert.strictEqual(rf.isItalicRank("kingdom"), false, "kingdom is roman");
assert.strictEqual(rf.isItalicRank("phylum"), false, "phylum is roman");
assert.strictEqual(rf.isItalicRank("order"), false, "order is roman");
assert.strictEqual(rf.isItalicRank("family"), false, "family is roman");
assert.strictEqual(rf.isItalicRank("subfamily"), false, "subfamily follows parent rank (roman)");
assert.strictEqual(rf.isItalicRank("unranked"), false, "unranked clade is roman");
assert.strictEqual(rf.scientificNameClass("genus"), "scientific-name", "italic by default for genus");
assert.strictEqual(rf.scientificNameClass("species"), "scientific-name", "italic by default for species");
assert.strictEqual(rf.scientificNameClass("kingdom"), "scientific-name scientific-name--roman", "kingdom gets the --roman modifier");
assert.strictEqual(rf.scientificNameClass("phylum"), "scientific-name scientific-name--roman", "phylum gets the --roman modifier");
assert.strictEqual(rf.scientificNameDepthClass(0), "scientific-name scientific-name-depth-0", "depth 0 → larger treatment");
assert.strictEqual(rf.scientificNameDepthClass(1), "scientific-name scientific-name-depth-n", "depth 1 → smaller treatment");
assert.strictEqual(rf.scientificNameDepthClass(5), "scientific-name scientific-name-depth-n", "depth 5 → smaller treatment");
assert.strictEqual(rf.realmForPath("Bacteria/Acidobacteria/X"), "bacteria", "bacteria domain tint");
assert.strictEqual(rf.realmForPath("Archaea/Euryarchaeota/X"), "archaea", "archaea domain tint");
assert.strictEqual(rf.realmForPath("Viruses/Adnaviria/X"), "viruses", "viruses domain tint");
assert.strictEqual(rf.realmForPath("Eukaryota/Animalia/Chordata/X"), "animalia", "animalia kingdom tint");
assert.strictEqual(rf.realmForPath("Eukaryota/Animalia"), "animalia", "animalia kingdom tint without trailing segments");
assert.strictEqual(rf.realmForPath("Eukaryota/Fungi/Basidiomycota/X"), "fungi", "fungi kingdom tint");
assert.strictEqual(rf.realmForPath("Eukaryota/Plantae/Magnoliophyta/X"), "plantae", "plantae kingdom tint");
assert.strictEqual(rf.realmForPath("Eukaryota/Chromista/X"), "chromista", "chromista kingdom tint");
assert.strictEqual(rf.realmForPath("Eukaryota/Protozoa/X"), "protozoa", "protozoa kingdom tint");
assert.strictEqual(rf.realmForPath("Eukaryota/Diaphoretickes/X"), "other", "unrecognised Eukaryota kingdom → other");
assert.strictEqual(rf.realmForPath("Eukaryota"), "other", "Eukaryota without kingdom → other");
assert.strictEqual(rf.realmForPath(""), "other", "empty path → other");
assert.strictEqual(rf.realmForPath(null), "other", "null path → other");
assert.strictEqual(rf.realmForPath(undefined), "other", "undefined path → other");
assert.strictEqual(rf.realmForPath("Eukaryota/id-7_Animalia/X"), "animalia", "strips id-N_ prefix from kingdom segment");
assert.strictEqual(rf.realmForPath("Bacteria/id-12_Acidobacteriota/X"), "bacteria", "strips id-N_ prefix from domain segment");
const dotAccepted = rf.statusDotDescriptor("accepted");
assert.strictEqual(dotAccepted.title, "Accepted", "status dot 'accepted' tooltip");
assert.ok(dotAccepted.className.includes("status-dot-accepted"), "status dot 'accepted' class");
const dotSynonym = rf.statusDotDescriptor("synonym");
assert.strictEqual(dotSynonym.title, "Synonym", "status dot 'synonym' tooltip");
assert.ok(dotSynonym.className.includes("status-dot-synonym"), "status dot 'synonym' class");
const dotUnknown = rf.statusDotDescriptor(null);
assert.strictEqual(dotUnknown.title, "Unknown", "status dot null tooltip → Unknown");
assert.ok(dotUnknown.className.includes("status-dot-unknown"), "status dot null class → unknown");
const dotAmbiguous = rf.statusDotDescriptor("ambiguous synonym");
assert.strictEqual(dotAmbiguous.title, "Unknown", "non-canonical status falls back to Unknown");
assert.ok(dotAmbiguous.className.includes("status-dot-unknown"), "non-canonical status class");
assert.strictEqual(rf.speciesCountBadge(5), "5 spp.", "single-digit count");
assert.strictEqual(rf.speciesCountBadge(999), "999 spp.", "999 upper bound");
assert.strictEqual(rf.speciesCountBadge(1000), "1k spp.", "1k threshold rounds to 1k");
assert.strictEqual(rf.speciesCountBadge(1500), "2k spp.", "1.5k rounds up to 2k");
assert.strictEqual(rf.speciesCountBadge(1234567), "1.2M spp.", "1.2M (7 digits hits the millions branch)");
assert.strictEqual(rf.speciesCountBadge(999999), "1000k spp.", "999,999 rounds up to 1000k");
assert.strictEqual(rf.speciesCountBadge(1000000), "1M spp.", "1M threshold");
assert.strictEqual(rf.speciesCountBadge(2500000), "2.5M spp.", "2.5M");
assert.strictEqual(rf.speciesCountBadge(1500000), "1.5M spp.", "1.5M");
assert.strictEqual(rf.speciesCountBadge(20000000), "20M spp.", "20M");
assert.strictEqual(rf.speciesCountBadge(null), "", "null → empty string");
assert.strictEqual(rf.speciesCountBadge(undefined), "", "undefined → empty string");
assert.strictEqual(rf.speciesCountBadge(0), "", "zero → empty string");
// ODD-NTP-004 — sourceInfoTooltip predicate (port of the legacy
// web/tree.js::sourceTooltipText branch).
const COL_ONLY = T(200, "ColOnly", "kingdom", null, { coldp_id: "abc" });
const WORMS_ONLY = T(201, "WormsOnly", "kingdom", null, { worms_id: 137093 });
const CROSS = T(202, "Cross", "kingdom", null, { coldp_id: "def", worms_id: 137094 });
assert.strictEqual(rf.sourceInfoTooltip(COL_ONLY, "col"), "CoL-only — ColDP ID abc (no WoRMS match).", "CoL-only tooltip in CoL view");
assert.strictEqual(rf.sourceInfoTooltip(COL_ONLY, "worms"), null, "CoL-only row in WoRMS view → no info glyph");
assert.strictEqual(rf.sourceInfoTooltip(WORMS_ONLY, "worms"), "WoRMS-only — AphiaID 137093 (no CoL match). Open in WoRMS.", "WoRMS-only tooltip in WoRMS view");
assert.strictEqual(rf.sourceInfoTooltip(WORMS_ONLY, "col"), null, "WoRMS-only row in CoL view → no info glyph");
assert.strictEqual(rf.sourceInfoTooltip(WORMS_ONLY, "freshwater"), "WoRMS-only — AphiaID 137093 (no CoL match). Open in WoRMS.", "WoRMS-only row in Freshwater view → WoRMS tooltip (legacy non-CoL branch)");
assert.strictEqual(rf.sourceInfoTooltip(CROSS, "worms"), "WoRMS cross-link — AphiaID 137094. Open in WoRMS.", "cross-link tooltip in WoRMS view");
assert.strictEqual(rf.sourceInfoTooltip(CROSS, "freshwater"), "WoRMS cross-link — AphiaID 137094. Open in WoRMS.", "cross-link tooltip in Freshwater view");
assert.strictEqual(rf.sourceInfoTooltip(CROSS, "col"), null, "cross-link row in CoL view → no info glyph (CoL identity already in badge context)");
// ODD-NTP-004 — wormsUrlFor builds the canonical marinespecies URL.
assert.strictEqual(rf.wormsUrlFor(WORMS_ONLY), "https://www.marinespecies.org/aphia.php?p=taxdetails&id=137093", "WoRMS URL format");
assert.strictEqual(rf.wormsUrlFor(CROSS), "https://www.marinespecies.org/aphia.php?p=taxdetails&id=137094", "WoRMS URL for cross-link");
const NO_WORMS = T(203, "NoWorms", "kingdom", null, { coldp_id: "z" });
assert.strictEqual(rf.wormsUrlFor(NO_WORMS), null, "No worms_id → null URL");
// ODD-NTP-004 — hasMaterializedFolder honours research_path_exists + materialized cache.
const NO_PATH = T(300, "NoPath", "kingdom", null, { coldp_id: "x" });
const WITH_PATH = T(301, "WithPath", "kingdom", null, { coldp_id: "y", research_path_exists: true });
assert.strictEqual(rf.hasMaterializedFolder(NO_PATH), false, "no research_path_exists → false");
assert.strictEqual(rf.hasMaterializedFolder(WITH_PATH), true, "research_path_exists=true → true");
// Propagated materialized cache wins for rows that have no wire signal yet.
const PROPAGATED = new Set([NO_PATH.id]);
assert.strictEqual(rf.hasMaterializedFolder(NO_PATH, PROPAGATED), true, "propagated materialized cache wins");
assert.strictEqual(rf.hasMaterializedFolder(WITH_PATH, PROPAGATED), true, "wire signal + propagated cache: wire signal wins (or ties)");
const EMPTY_PROPAGATED = new Set();
assert.strictEqual(rf.hasMaterializedFolder(NO_PATH, EMPTY_PROPAGATED), false, "no wire signal + empty cache → false");

process.stdout.write("PASS\n");
"""


def test_compiled_tree_state_passes_runtime_contract(
    tmp_path: Path, require_toolchain: None,
) -> None:
    """A–L: empty state, withRoots, attachChildren (dedup + unknown parent),
    expand/collapse/toggleExpand (idempotent), load-status lifecycle,
    superdomain/collection roots round-trip, immutability of EMPTY_TREE_STATE,
    source predicate contract (CoL/WoRMS/Freshwater nullability checks),
    source-aware roots merge (foreign ids preserved on `nodes`),
    source-aware child attachment, Freshwater-root predicate + native
    source-order helper, and source-bound state reset (clear roots /
    expanded / child cache / load status while preserving the `nodes`
    projection cache). V: ODD-NTP-004 row-format pure helpers
    (rank label / plural / italic / realm / status dot /
    species-count badge / source-info tooltip / WoRMS URL /
    materialize predicate)."""
    for p in (TREE_STATE_FILE, ROW_FORMAT_FILE, DOMAIN_FILE):
        if not p.is_file():
            pytest.skip(f"missing required source: {p}")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    result = _run_tsc(out_dir)
    assert result.returncode == 0, (
        f"tree-state/row-format compilation failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    compiled_tree = out_dir / "presentation" / "tree-state.js"
    compiled_rf = out_dir / "presentation" / "row-format.js"
    assert compiled_tree.is_file(), f"tsc did not emit {compiled_tree}."
    assert compiled_rf.is_file(), f"tsc did not emit {compiled_rf}."
    harness = tmp_path / "harness.cjs"
    harness.write_text(_NODE_HARNESS)
    result = subprocess.run(
        ["node", str(harness), str(compiled_tree), str(compiled_rf)],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0 and result.stdout.strip() == "PASS", (
        f"tree-state runtime harness failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# W6.5-BRIDGE-006 — FolderTab → Explorer refresh bridge.
# The FolderTab dispatches a
# `window.CustomEvent("taxa:explorer:refresh")` when
# `materializeResearch` (or `openFolder`) succeeds in
# the React taxonomy detail panel. The Explorer route
# subscribes to that event on mount and re-fetches the
# /api/files tree so the tree mirrors the new folder
# structure without dropping the existing
# ExplorerLoadStatus / expanded set / selected-path /
# ViewerState.
#
# Acceptance (verbatim from the W6.5 task brief):
#  - Signal is a window-scoped CustomEvent named
#    `"taxa:explorer:refresh"` (verbatim).
#  - Dispatched from FolderTab once the create / open
#    transitions reach the success state
#    (`createStatus.kind === "created"` /
#    `openStatus.kind === "opened"`).
#  - No dispatch on `idle` / `creating` / `opening` /
#    `error` / `copied` states.
#  - Dispatch target is `window` (not `document`, not
#    a custom EventTarget).
#  - No @taxa/browser-state key expansion.
#  - No router-key re-mount.
#  - No legacy web/ mutation.
#
# The FolderTab contract surfaces through:
#  - Local `EXPLORER_REFRESH_EVENT_NAME = "taxa:explorer:refresh"`
#    constant (the verbatim canonical literal).
#  - Two `useEffect`s that watch `createStatus` +
#    `openStatus` and dispatch
#    `window.dispatchEvent(new CustomEvent(EXPLORER_REFRESH_EVENT_NAME))`
#    on the success transitions only.
# ---------------------------------------------------------------------------


def test_w65_folder_tab_defines_local_event_name_literal() -> None:
    """W6.5-BRIDGE-006 — FolderTab.tsx MUST define a local
    `EXPLORER_REFRESH_EVENT_NAME = "taxa:explorer:refresh"`
    constant so the FolderTab dispatches with the verbatim
    canonical literal. The constant is local (the
    FolderTab is in the taxonomy module — no cross-module
    import from `@taxa/research` is allowed for the
    cross-route event name). A future PR that renames the
    event MUST update the kernel constant + the
    Explorer.tsx literal + the FolderTab.tsx literal in
    lock-step."""
    if not FOLDER_TAB_FILE.is_file():
        pytest.skip("FolderTab.tsx not present yet")
    text = FOLDER_TAB_FILE.read_text()
    assert re.search(
        r'EXPLORER_REFRESH_EVENT_NAME\s*=\s*["\']taxa:explorer:refresh["\']',
        text,
    ), (
        "FolderTab.tsx MUST define a local "
        "`EXPLORER_REFRESH_EVENT_NAME = \"taxa:explorer:refresh\"` "
        "constant so the dispatch uses the verbatim canonical "
        "literal (W6.5-BRIDGE-006 contract)."
    )


def test_w65_folder_tab_dispatches_on_create_success() -> None:
    """W6.5-BRIDGE-006 — FolderTab.tsx MUST dispatch
    `window.dispatchEvent(new CustomEvent(EXPLORER_REFRESH_EVENT_NAME))`
    when `createStatus.kind === "created"` (i.e. the
    `materializeResearch` POST succeeded). The dispatch is
    bound to the success transition only — a mid-flight
    `"creating"` state MUST NOT fire the dispatch (the
    Explorer would refetch before the new folders hit
    disk).

    The implementation may use either:
      - `if (createStatus.kind === "created") { dispatch }`
      - `if (createStatus.kind !== "created") return; dispatch`
      - `if (!isFolderSuccessStatusKind(createStatus.kind)) return; dispatch`

    All three shapes satisfy the contract. The lenient
    match accepts any of them by looking for the
    success-status check + the dispatch within the same
    useEffect body (extracted via brace-counting)."""
    if not FOLDER_TAB_FILE.is_file():
        pytest.skip("FolderTab.tsx not present yet")
    text = FOLDER_TAB_FILE.read_text()
    # The useEffect keyed on `createStatus` MUST branch on
    # the success literal. Accept BOTH `=== "created"`
    # and `!== "created"` patterns (the implementation
    # uses early-return on the non-success branch).
    assert re.search(
        r"createStatus\.kind\s*(?:!==|===)\s*[\"']created[\"']",
        text,
    ), (
        "FolderTab.tsx MUST branch on "
        "`createStatus.kind (===|!==) \"created\"` so the "
        "dispatch fires ONLY on the materializeResearch "
        "success transition (W6.5-BRIDGE-006 contract)."
    )
    # Locate the useEffect that branches on
    # `createStatus` + extract its body via
    # brace-counting so the dispatch + the success-status
    # check both live in the same effect.
    effect_match = re.search(
        r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{", text,
    )
    assert effect_match, (
        "FolderTab.tsx MUST have a `useEffect` (W6.5 "
        "contract: the dispatch lifecycle lives in a "
        "useEffect so React dedupes per-status-instance)."
    )
    effect_open = effect_match.end() - 1  # the `{` index
    # Walk forward to find the matching `}`.
    depth = 0
    body_end = -1
    for i in range(effect_open, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                body_end = i + 1
                break
    assert body_end > effect_open, (
        "FolderTab.tsx's createStatus useEffect body MUST "
        "close with a matching `}` (brace-counting "
        "traversal failed — the effect body is malformed)."
    )
    body = text[effect_open:body_end]
    # The dispatch site MUST live in the same useEffect
    # block as the success-status check. The lenient
    # match tolerates whitespace / newlines around
    # `new CustomEvent(...)`.
    body_stripped = re.sub(r"\s+", "", body)
    assert (
        "createStatus.kind" in body
        and "newCustomEvent(EXPLORER_REFRESH_EVENT_NAME)" in body_stripped
        and "window.dispatchEvent" in body_stripped
    ), (
        "FolderTab.tsx's createStatus useEffect MUST call "
        "`window.dispatchEvent(new CustomEvent(EXPLORER_REFRESH_EVENT_NAME))` "
        "when `createStatus.kind === \"created\"` "
        "(W6.5-BRIDGE-006 contract: dispatch the typed "
        "CustomEvent on the success transition so the "
        "Explorer route re-fetches /api/files)."
    )


def test_w65_folder_tab_dispatches_on_open_success() -> None:
    """W6.5-BRIDGE-006 — FolderTab.tsx MUST dispatch
    `window.dispatchEvent(new CustomEvent(EXPLORER_REFRESH_EVENT_NAME))`
    when `openStatus.kind === "opened"` (i.e. the
    `openFolder` POST succeeded). The dispatch is
    bound to the success transition only — a mid-flight
    `"opening"` state MUST NOT fire the dispatch.

    The implementation may use either `=== "opened"` or
    `!== "opened"` patterns; the lenient match accepts
    any of them."""
    if not FOLDER_TAB_FILE.is_file():
        pytest.skip("FolderTab.tsx not present yet")
    text = FOLDER_TAB_FILE.read_text()
    # Accept BOTH `=== "opened"` and `!== "opened"`
    # patterns (the implementation uses early-return on
    # the non-success branch).
    assert re.search(
        r"openStatus\.kind\s*(?:!==|===)\s*[\"']opened[\"']",
        text,
    ), (
        "FolderTab.tsx MUST branch on "
        "`openStatus.kind (===|!==) \"opened\"` so the "
        "dispatch fires ONLY on the openFolder success "
        "transition (W6.5-BRIDGE-006 contract)."
    )
    # Find the SECOND useEffect in the file (the one
    # keyed on openStatus). Brace-counting extracts the
    # body so the dispatch + the success-status check
    # both live in the same effect.
    effect_matches = list(
        re.finditer(r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{", text),
    )
    assert len(effect_matches) >= 2, (
        "FolderTab.tsx MUST have at least two `useEffect` "
        "blocks (one for createStatus + one for openStatus "
        "— W6.5-BRIDGE-006 contract)."
    )
    # Use the LAST useEffect block (openStatus's
    # dispatch effect — it's defined AFTER createStatus's
    # in the implementation).
    last_effect = effect_matches[-1]
    effect_open = last_effect.end() - 1
    depth = 0
    body_end = -1
    for i in range(effect_open, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                body_end = i + 1
                break
    assert body_end > effect_open, (
        "FolderTab.tsx's openStatus useEffect body MUST "
        "close with a matching `}` (brace-counting "
        "traversal failed — the effect body is malformed)."
    )
    body = text[effect_open:body_end]
    body_stripped = re.sub(r"\s+", "", body)
    assert (
        "openStatus.kind" in body
        and "newCustomEvent(EXPLORER_REFRESH_EVENT_NAME)" in body_stripped
        and "window.dispatchEvent" in body_stripped
    ), (
        "FolderTab.tsx's openStatus useEffect MUST call "
        "`window.dispatchEvent(new CustomEvent(EXPLORER_REFRESH_EVENT_NAME))` "
        "when `openStatus.kind === \"opened\"` "
        "(W6.5-BRIDGE-006 contract: dispatch the typed "
        "CustomEvent on the success transition so the "
        "Explorer route re-fetches /api/files)."
    )


def test_w65_folder_tab_dispatches_via_window_only() -> None:
    """W6.5-BRIDGE-006 — FolderTab.tsx MUST dispatch the
    event on `window` (NOT `document`, NOT a custom
    EventTarget). The Explorer route subscribes on
    `window`; a different target would silently break
    the bridge."""
    if not FOLDER_TAB_FILE.is_file():
        pytest.skip("FolderTab.tsx not present yet")
    text = FOLDER_TAB_FILE.read_text()
    # The dispatch site MUST use `window.dispatchEvent(`.
    assert re.search(
        r"window\.dispatchEvent\s*\(\s*new\s+CustomEvent\s*\(\s*EXPLORER_REFRESH_EVENT_NAME",
        text,
    ), (
        "FolderTab.tsx MUST dispatch via "
        "`window.dispatchEvent(new CustomEvent(EXPLORER_REFRESH_EVENT_NAME))` "
        "— the W6.5-BRIDGE-006 contract pins `window` as "
        "the dispatch target so the Explorer route "
        "subscription site matches."
    )
    # The dispatch site MUST NOT use `document.dispatchEvent`
    # (the bridge target is window, not document).
    assert "document.dispatchEvent" not in text, (
        "FolderTab.tsx MUST NOT dispatch via "
        "`document.dispatchEvent(...)` — the W6.5-BRIDGE-006 "
        "contract pins `window` as the dispatch target "
        "(the Explorer route subscribes on `window`). "
        "A document-scoped dispatch would silently break "
        "the bridge."
    )


def test_w65_folder_tab_dispatch_uses_new_custom_event_with_canonical_name() -> None:
    """W6.5-BRIDGE-006 — FolderTab.tsx MUST construct the
    dispatch as `new CustomEvent(EXPLORER_REFRESH_EVENT_NAME)`
    so the event carries the verbatim canonical name. A
    bare `new Event(...)` would carry a different event
    type; a string-typed `new CustomEvent(\"some-other-name\")`
    would break the bridge."""
    if not FOLDER_TAB_FILE.is_file():
        pytest.skip("FolderTab.tsx not present yet")
    text = FOLDER_TAB_FILE.read_text()
    # The dispatch MUST use `new CustomEvent(EXPLORER_REFRESH_EVENT_NAME)`.
    # The literal `"taxa:explorer:refresh"` MUST NOT appear
    # inline in the dispatch — the W6.5 contract pins the
    # constant as the canonical source.
    assert re.search(
        r"new\s+CustomEvent\s*\(\s*EXPLORER_REFRESH_EVENT_NAME\b",
        text,
    ), (
        "FolderTab.tsx MUST construct the dispatch via "
        "`new CustomEvent(EXPLORER_REFRESH_EVENT_NAME)` "
        "so the event carries the verbatim canonical name "
        "(W6.5-BRIDGE-006 contract)."
    )
    # The dispatch MUST NOT inline `"taxa:explorer:refresh"`
    # (the canonical name flows through the constant so a
    # future rename updates one place).
    assert not re.search(
        r'new\s+CustomEvent\s*\(\s*["\']taxa:explorer:refresh["\']',
        text,
    ), (
        "FolderTab.tsx MUST construct "
        "`new CustomEvent(EXPLORER_REFRESH_EVENT_NAME)` (via "
        "the local constant) — NOT inline "
        "`new CustomEvent(\"taxa:explorer:refresh\")`. "
        "The W6.5-BRIDGE-006 contract pins the constant as "
        "the canonical source so a future rename updates "
        "one place."
    )


def test_w65_folder_tab_dispatch_is_idempotent_via_status_kind_change() -> None:
    """W6.5-BRIDGE-006 — the FolderTab dispatch MUST be
    idempotent per status transition: the `useEffect`
    keyed on `createStatus` (or `openStatus`) only re-
    fires when the discriminated union's `.kind`
    changes. A re-render with the SAME status (e.g. a
    parent re-render passing the same `createStatus`
    object reference) MUST NOT trigger a duplicate
    dispatch.

    React's `useEffect` primitive-equality dedupe on the
    dependency array handles this naturally when the
    parent passes a stable `createStatus` / `openStatus`
    reference. The FolderTab contract relies on the
    parent passing a discriminated union whose `.kind`
    is the dependency surface — the W6.5 implementation
    keys the effect on `createStatus` / `openStatus`
    directly (so React dedupes on reference equality).

    The lenient match tolerates whitespace / newlines
    between the useEffect body + the deps array (the
    implementation wraps the deps on their own line
    under Prettier's wrap heuristic)."""
    if not FOLDER_TAB_FILE.is_file():
        pytest.skip("FolderTab.tsx not present yet")
    text = FOLDER_TAB_FILE.read_text()
    stripped = re.sub(r"\s+", "", text)
    for dependency in ("createStatus", "openStatus"):
        # Match the deps array literal at the end of the
        # useEffect call: `}, [<dep>(.kind)?])`. The
        # stripped form collapses the implementation's
        # newline + indent wrap so the regex stays
        # robust. The `\[ ... \]` form rejects accidental
        # matches inside the effect body (e.g. an object
        # literal that mentions the dependency).
        assert re.search(
            rf",\[{re.escape(dependency)}(?:\.kind)?\]\)",
            stripped,
        ), (
            f"FolderTab.tsx MUST key the dispatch "
            f"`useEffect` on `{dependency}` (or "
            f"`{dependency}.kind`) so React dedupes "
            f"per-status-instance and a re-render with "
            f"the same status does NOT fire a duplicate "
            f"dispatch. W6.5-BRIDGE-006 contract."
        )


# ---------------------------------------------------------------------------
# ODD-MIGRATE-007-DOM-006 — legacy DOM marker reproduction
#
# Cross-module companion tests to the per-marker source guards in
# `tests/test_visible_taxonomy_tree.py`. The companion tests live
# here so the marker contract is enforced from BOTH the
# source-level pin (TaxonomyTree.tsx) AND the state-kernel level
# (tree-state.ts) — a future refactor that drops one half of the
# contract fails one or the other before review.
# ---------------------------------------------------------------------------


def test_tree_state_module_is_unchanged_by_dom_markers() -> None:
    """ODD-MIGRATE-007-DOM-006 — companion pin: `tree-state.ts`
    must STAY a pure framework-free state kernel (no DOM /
    HTML / fetch / React / Next tokens). The DOM-marker
    reproduction lives in `TaxonomyTree.tsx` (the client
    island) — the state kernel is untouched. This test pins
    the contract: any DOM-marker-related drift in
    `tree-state.ts` would silently couple the kernel to a
    framework, so the focused tests fail before review."""
    if not TREE_STATE_FILE.exists():
        pytest.skip("tree-state.ts not present yet")
    text = TREE_STATE_FILE.read_text()
    # Strip comments so an explanatory doc-block that references
    # `web/app.js` (the legacy bundle marker) is NOT a false
    # positive. The marker contract belongs to TaxonomyTree.tsx,
    # not the kernel's documentation.
    block = re.compile(r"/\*[\s\S]*?\*/")
    line = re.compile(r"//[^\n]*")
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))  # noqa: E731
    stripped = block.sub(blank, text)
    stripped = line.sub(blank, stripped)
    # No DOM-marker literals (the source-level guards live in
    # the client island, not the kernel). A literal id like
    # `"tree-view"` would leak the React surface into the
    # framework-free kernel.
    for marker in (
        '"tree-view"', "'tree-view'",
        '"tree-source-toggle"', "'tree-source-toggle'",
        '"detail-panel"', "'detail-panel'",
        '"breadcrumb"', "'breadcrumb'",
        '"version-banner"', "'version-banner'",
        "/app.js",
    ):
        assert marker not in stripped, (
            f"tree-state.ts must NOT carry the DOM-marker "
            f"literal {marker!r} — the marker contract belongs "
            f"to TaxonomyTree.tsx, not the framework-free kernel "
            f"(ODD-MIGRATE-007-DOM-006)."
        )
