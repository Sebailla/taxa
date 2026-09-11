"""Taxonomy application contract tests (PR 5b application slice).

Pins: typed port compatible with merged adapter (`fetchTaxon`/`fetchChildren`)
+ pure readonly view-model builders for tree and detail. spec.md rule 4
inward deps + rule 5 barrel export. References: tasks.md §Phase 5 (5.2).
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "src" / "modules" / "taxonomy" / "application"
PORTS_FILE = APP_DIR / "ports.ts"
VIEW_MODELS_FILE = APP_DIR / "view-models.ts"
INFRA_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "infrastructure" / "api.ts"
DOMAIN_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "domain" / "taxon.ts"
BARREL_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "index.ts"

_FORBIDDEN = (
    "react", "next", "nextjs", "fastapi", "starlette", "pydantic",
    "fetch(", "localStorage", "document.", "window.", "process.",
    "require(", "globalThis",
    "../infrastructure", "../presentation", "../index",
    "../../research", "../../design-system", "../../browser-state", "../../app-shell",
)


@pytest.fixture()
def require_toolchain() -> None:
    if not (shutil.which("npx") and shutil.which("node")):
        pytest.skip("npx + node required on PATH")


# File presence + plain-TypeScript extension + spec.md rule 4 purity.
@pytest.mark.parametrize("path", (PORTS_FILE, VIEW_MODELS_FILE))
def test_application_file_purity(path: Path) -> None:
    assert path.is_file(), f"missing {path}. PR 5b application slice ships this file."
    assert path.suffix == ".ts", f"plain TS required; got {path}"
    text = path.read_text()
    for token in _FORBIDDEN:
        assert token not in text, f"{path.name} must stay free of {token!r}; spec.md rule 4."
    assert re.search(r'from\s+["\']\.\./domain/taxon(?:\.js)?["\']', text), (
        f"{path.name} must import from ../domain/taxon."
    )


# Port shape + view-model surface + barrel — source-level contracts.
def test_application_surface_contract() -> None:
    ports_text = PORTS_FILE.read_text() if PORTS_FILE.exists() else ""
    vm_text = VIEW_MODELS_FILE.read_text() if VIEW_MODELS_FILE.exists() else ""
    barrel_text = BARREL_FILE.read_text() if BARREL_FILE.exists() else ""
    assert re.search(r"export\s+interface\s+TaxonomyRepository\b", ports_text)
    assert "fetchTaxon" in ports_text and "fetchChildren" in ports_text
    assert re.search(r"\b(?:type|interface)\s+SourceFilter\b", ports_text)
    for name in (
        "TaxonNodeViewModel", "TaxonTreeViewModel",
        "TaxonDetailViewModel", "TaxonBreadcrumbSegment",
    ):
        block_re = re.compile(
            rf"export\s+(?:interface|type)\s+{name}\b[\s\S]*?\n\}}", re.MULTILINE,
        )
        m = block_re.search(vm_text)
        assert m, f"must export `{name}`."
        assert "readonly" in m.group(0), f"`{name}` must declare readonly fields."
    for name in ("buildTaxonTree", "buildTaxonDetail"):
        block_re = re.compile(rf"export\s+function\s+{name}\b[\s\S]*?\n\}}", re.MULTILINE)
        m = block_re.search(vm_text)
        assert m, f"must export `{name}`."
        assert "async" not in m.group(0) and "await " not in m.group(0), (
            f"`{name}` must be synchronous and pure."
        )
    for name in (
        "TaxonomyRepository", "SourceFilter",
        "TaxonNodeViewModel", "TaxonTreeViewModel",
        "TaxonDetailViewModel", "TaxonBreadcrumbSegment",
        "buildTaxonTree", "buildTaxonDetail",
    ):
        assert name in barrel_text, f"barrel must re-export `{name}`."


# Compile + runtime contract — strict mode, ES2022 only, no DOM.
def _run_tsc(out_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    sources = [str(p) for p in (DOMAIN_FILE, PORTS_FILE, VIEW_MODELS_FILE, INFRA_FILE)
               if p.is_file()]
    if len(sources) < 4:
        pytest.skip("required source files missing")
    return subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--strict", "--target", "ES2022",
            "--module", "commonjs", "--lib", "ES2022",
            "--skipLibCheck", "--esModuleInterop",
            "--rootDir", "src/modules/taxonomy",
            "--outDir", str(out_dir), *sources, *extra,
        ],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )


# Glue fixture: proves the merged infrastructure adapter structurally
# satisfies the application port (TS structural function subtyping).
_PORT_COMPAT_FIXTURE = r"""
import { fetchTaxon, fetchChildren } from "../infrastructure/api.js";
import type { TaxonomyRepository } from "./ports.js";
const _port: TaxonomyRepository = { fetchTaxon, fetchChildren };
export const __port_compatible__ = _port;
"""


_NODE_HARNESS = r"""
const path = require("path");
const vm = require(path.resolve(process.argv[2]));
const { buildTaxonTree, buildTaxonDetail } = vm;
const T = (id, name, rank, parentId) => ({ id, name, rank, authorship: null, parent_id: parentId });
const eq = (g, w) => JSON.stringify(g) === JSON.stringify(w);
const fail = (l) => { process.stderr.write("FAIL " + l + "\n"); process.exit(1); };

const ani = T(1, "Animalia", "kingdom", null);
const chor = T(2, "Chordata", "phylum", 1);
const arth = T(3, "Arthropoda", "phylum", 1);
const canis = T(4, "Canis", "genus", 2);

// buildTaxonTree: empty → empty; single root → depth 0, counts, sibling
// order, depth propagation; multi-root sort; orphan absorption; cycle break.
const e = buildTaxonTree([]);
if (!eq(e.roots, []) || e.totalNodeCount !== 0) fail("empty");
const tr = buildTaxonTree([ani, chor, arth, canis]);
const r = tr.roots[0];
if (tr.roots.length !== 1 || r.depth !== 0 || r.childCount !== 2 || r.descendantCount !== 3 || r.isLeaf !== false) fail("single");
if (!eq(r.children.map((c) => c.taxon.name), ["Arthropoda", "Chordata"])) fail("sibling.order");
if (r.children[0].depth !== 1 || r.children[1].children[0].depth !== 2 || !r.children[1].children[0].isLeaf) fail("depth");
if (tr.totalNodeCount !== 4) fail("total");
const fr = buildTaxonTree([ani, T(10, "Plantae", "kingdom", null), T(11, "Rosa", "genus", 10)]);
if (fr.roots.length !== 2 || !eq(fr.roots.map((x) => x.taxon.name), ["Animalia", "Plantae"]) || fr.totalNodeCount !== 3) fail("forest");
const mix = buildTaxonTree([T(30, "ValidRoot", "kingdom", null), T(31, "OrphanChild", "phylum", 30), T(32, "OrphanGrandchild", "class", 31)]);
if (mix.roots.length !== 1 || mix.totalNodeCount !== 3) fail("orphan");
const cyc = buildTaxonTree([T(20, "A", "kingdom", 21), T(21, "B", "phylum", 20)]);
if (!eq(cyc.roots, []) || cyc.totalNodeCount !== 0) fail("cycle");

// buildTaxonDetail: focused, root (no ancestors), leaf.
const det = buildTaxonDetail({ taxon: chor, ancestors: [ani], childCount: 1, allDescendants: [canis] });
if (det.taxon.id !== 2 || det.childCount !== 1 || !det.hasChildren || det.descendantCount !== 1 || det.rankIndex !== 1) fail("detail.focused");
if (!eq(det.breadcrumb.map((s) => s.id), [1, 2]) || det.breadcrumb[1].rank !== "phylum") fail("detail.breadcrumb");
const rd = buildTaxonDetail({ taxon: ani, ancestors: [], childCount: 2 });
if (rd.breadcrumb.length !== 1 || !rd.hasChildren || rd.descendantCount !== 0 || rd.rankIndex !== 0) fail("root.detail");
const ld = buildTaxonDetail({ taxon: canis, ancestors: [ani, chor], childCount: 0 });
if (ld.hasChildren || ld.breadcrumb.length !== 3 || ld.breadcrumb[2].id !== 4 || ld.rankIndex !== 5) fail("leaf.detail");

process.stdout.write("PASS\n");
"""


def test_compiled_application_passes_runtime_contract(
    tmp_path: Path, require_toolchain: None,
) -> None:
    """Runtime contract under Node (ES2022, no DOM): buildTaxonTree
    (empty, single-root counts, sibling order, depth, multi-root sort,
    orphan absorption, cycle break) + buildTaxonDetail (focused,
    breadcrumb, summary, root, leaf). Port-compat fixture compiled
    alongside proves the merged adapter satisfies the port."""
    for p in (DOMAIN_FILE, PORTS_FILE, VIEW_MODELS_FILE, INFRA_FILE):
        if not p.is_file():
            pytest.skip(f"missing required source: {p}")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    fixture = APP_DIR / "__port_compat_fixture.ts"
    fixture.write_text(_PORT_COMPAT_FIXTURE)
    harness = tmp_path / "harness.cjs"
    harness.write_text(_NODE_HARNESS)
    try:
        result = _run_tsc(out_dir, str(fixture))
        assert result.returncode == 0, (
            f"compile failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        compiled = out_dir / "application" / "view-models.js"
        assert compiled.is_file()
        result = subprocess.run(
            ["node", str(harness), str(compiled)],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0 and result.stdout.strip() == "PASS", (
            f"runtime harness failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    finally:
        if fixture.is_file():
            fixture.unlink()
