"""Taxonomy foundation contract tests — PR 5a.1 (replan).

Pins slice 5a.1: source-aware parent-chain walker + typed fetch* +
typed application view-model surface. Domain EXTENDED; predecessor
exports stay byte-identical. No React hook (lands 5a.2).
"""
from __future__ import annotations
import re, shutil, subprocess
from pathlib import Path
import pytest

R = Path(__file__).resolve().parent.parent
T = R / "src" / "modules" / "taxonomy"
DOMAIN_FILE = T / "domain" / "taxon.ts"
API_FILE = T / "infrastructure" / "api.ts"
INFRA_INDEX = T / "infrastructure" / "index.ts"
APP_FILE = T / "application" / "useTaxonTree.ts"
APP_INDEX = T / "application" / "index.ts"
BARREL_FILE = T / "index.ts"


@pytest.mark.parametrize("path", [DOMAIN_FILE, API_FILE, INFRA_INDEX,
                                  APP_FILE, APP_INDEX])
def test_files_present(path: Path) -> None:
    assert path.is_file(), f"missing {path} (PR 5a.1 slice 1)"


def test_domain_keeps_predecessor() -> None:
    text = DOMAIN_FILE.read_text()
    for tok in ("Rank", "RANK_ORDER", "isValidRank", "isValidTaxon",
                "compareRanks", "Taxon"):
        assert re.search(rf"export\s+(?:type|interface|const|function)\s+{tok}\b",
                         text), f"domain must keep predecessor export {tok!r}"
    for field in ("id", "name", "rank", "authorship", "parent_id"):
        assert re.search(rf"\b{field}\b\s*:", text), \
            f"Taxon must keep field {field!r}"


def test_domain_stays_pure() -> None:
    text = DOMAIN_FILE.read_text()
    for tok in ("react", "fetch(", "localStorage", "document.", "window.",
                "infrastructure", "application"):
        assert tok not in text, f"domain must stay free of {tok!r}"


def test_domain_exposes_new_types() -> None:
    text = DOMAIN_FILE.read_text()
    for tok in ("TreeSource", "TaxonRecord", "parentIdOf",
                "walkParentChain", "BreadcrumbSegment"):
        assert re.search(rf"(?:export\s+)?(?:type|interface|function)\s+{tok}\b",
                         text), f"domain must declare {tok!r}"


def test_api_exports_typed_surface() -> None:
    text = API_FILE.read_text()
    for fn in ("fetchTaxon", "fetchChildren", "fetchDomains"):
        assert re.search(rf"export\s+async\s+function\s+{fn}\b", text), \
            f"api.ts must export async function {fn!r}"
    assert re.search(r"export\s+class\s+NetworkError\b", text), \
        "api.ts must export class NetworkError"
    assert "react" not in text, "infrastructure stays framework-free"
    assert "NetworkError" in INFRA_INDEX.read_text() and \
        "fetchTaxon" in INFRA_INDEX.read_text(), \
        "infrastructure/index.ts must re-export the typed surface"


def test_application_exposes_view_model_surface() -> None:
    text = APP_FILE.read_text()
    for tok in ("TaxonTreeNode", "BreadcrumbViewModel",
                "loadTaxonTree", "buildBreadcrumb"):
        assert re.search(
            rf"(?:export\s+)?(?:type|interface|function|async\s+function)\s+{tok}\b",
            text), f"application must declare {tok!r}"
    assert "from \"react\"" not in text and "from 'react'" not in text, \
        "application must not import React in 5a.1 (hook lands 5a.2)"


def test_barrel_re_exports_new_surface() -> None:
    text = BARREL_FILE.read_text()
    for tok in ("fetchTaxon", "fetchChildren", "fetchDomains",
                "NetworkError", "TaxonRecord", "TreeSource"):
        assert tok in text, f"public barrel must re-export {tok!r}"


_HARNESS = r"""
const path = require("path");
const d = require(path.resolve(process.argv[2]));
const make = (id, name, p, w=null, f=null) => ({
  id, scientific_name: name, rank: "kingdom",
  parent_id: p, worms_parent_id: w, freshwater_parent_id: f,
  status: "accepted", is_extinct: false, species_count: 0,
  path: null, coldp_id: null, worms_id: null, freshwater_id: null,
  vernaculars: [], research_path_exists: null,
});
const recs = [make(1, "Biota", null, null, null),
              make(2, "Animalia", 1, 1, null),
              make(3, "Orphan", 99, null, null)];
const cyc = [make(5, "X", 6, 6, 6), make(6, "Y", 5, 5, 5)];
const byId = new Map(recs.map(r => [r.id, r]));
const cycBy = new Map(cyc.map(r => [r.id, r]));
const cases = {
  root_terminates: d.walkParentChain(1, "col", byId).length === 1,
  mid_chain_col: (() => {
    const c = d.walkParentChain(2, "col", byId);
    return c.length === 2 && c[0].id === 1 && c[1].id === 2;
  })(),
  orphan_stops: d.walkParentChain(3, "col", byId).length === 1,
  cycle_caps: (() => {
    const c = d.walkParentChain(5, "col", cycBy);
    return c.length <= 30 && c.some(r => r.id === 6);
  })(),
  parent_id_col: d.parentIdOf(recs[1], "col") === 1,
  parent_id_worms: d.parentIdOf(recs[1], "worms") === 1,
  parent_id_freshwater_null: d.parentIdOf(recs[1], "freshwater") === null,
  parent_id_root_null: d.parentIdOf(recs[0], "col") === null,
  is_valid_source: ["col","worms","freshwater"].every(s => d.isValidTreeSource(s)),
  is_invalid_source: d.isValidTreeSource("bogus") === false,
};
const failed = Object.keys(cases).filter(k => cases[k] !== true);
if (failed.length > 0) {
  process.stderr.write("FAILED_CASES: " + JSON.stringify(failed) + "\n");
  process.stderr.write("ALL_CASES: " + JSON.stringify(cases) + "\n");
  process.exit(1);
}
process.stdout.write("PASS\n");
"""


def test_compiled_walker_passes_runtime_contract(tmp_path: Path) -> None:
    if not (shutil.which("npx") and shutil.which("node")):
        pytest.skip("npx + node required for compile/runtime harness")
    if not DOMAIN_FILE.is_file():
        pytest.skip("domain file not present yet")
    out_dir = tmp_path / "build"; out_dir.mkdir()
    proc = subprocess.run(
        ["npx", "tsc", "--ignoreConfig",
         "--strict", "--target", "ES2022", "--module", "commonjs",
         "--lib", "ES2022", "--skipLibCheck", "--esModuleInterop",
         "--outDir", str(out_dir), str(DOMAIN_FILE)],
        cwd=str(R), capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, \
        f"taxon.ts failed to compile.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    compiled = out_dir / "taxon.js"
    assert compiled.is_file(), "tsc emitted no taxon.js"
    harness = tmp_path / "harness.cjs"; harness.write_text(_HARNESS)
    proc = subprocess.run(["node", str(harness), str(compiled)],
                          cwd=str(R), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, \
        f"walker runtime failed.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    assert proc.stdout.strip() == "PASS"