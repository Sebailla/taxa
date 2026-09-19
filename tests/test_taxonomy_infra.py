"""
Taxonomy infrastructure contract tests (PR 5a).

Pins `src/modules/taxonomy/infrastructure/api.ts` — the typed HTTP
adapter for FastAPI's `/api/taxon/{id}` and `/api/taxon/{id}/children`
endpoints. Asserts file presence, source purity (spec.md rule 4:
infrastructure → domain only; no React/Next/FastAPI), strict-mode
compile under `--lib ES2022` only, and runtime behaviour under Node
with a stubbed `fetch` so no real network is touched.

References:
    openspec/changes/migrate-nextjs-tailwind4/tasks.md  §Phase 5 (5.1, 5.2)
    openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md
        Rules 4 (inward deps), 5 (barrel export)
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INFRA_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "infrastructure" / "api.ts"


def _has_npx() -> bool:
    return shutil.which("npx") is not None


def _has_node() -> bool:
    return shutil.which("node") is not None


@pytest.fixture()
def require_toolchain() -> None:
    if not (_has_npx() and _has_node()):
        pytest.skip("npx + node required on PATH for compile/runtime test")


# ---------------------------------------------------------------------------
# File presence / source-level purity
# ---------------------------------------------------------------------------
def test_infra_file_exists() -> None:
    """RED marker for PR 5a."""
    assert INFRA_FILE.is_file(), (
        f"missing infrastructure file: {INFRA_FILE}. PR 5a ships this file."
    )


def test_infra_file_is_plain_typescript() -> None:
    """`.ts`, not `.tsx` — infrastructure has no JSX."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    assert INFRA_FILE.suffix == ".ts"


def test_infra_file_depends_on_domain_only() -> None:
    """Spec.md rule 4: infrastructure → domain is the only allowed inward edge. The optional `.js` extension covers both `from "../domain/taxon"` and Bundler/NodeNext spellings."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    assert re.search(r'from\s+["\']\.\./domain/taxon(?:\.js)?["\']', text), (
        "infra/api.ts must import from ../domain/taxon — spec.md rule 4."
    )
    for token in (
        "../presentation", "../application", "../index",
        "../../research", "../../design-system",
        "../../browser-state", "../../app-shell",
    ):
        assert token not in text, f"infra/api.ts must not import {token!r}."


def test_infra_file_has_no_framework_imports() -> None:
    """Infrastructure is leaf-level I/O glue: no React, Next, FastAPI, Starlette."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    for tok in (
        "from 'react'", 'from "react"',
        "from 'next'",   'from "next"',
        "from 'nextjs'", 'from "nextjs"',
        "from 'fastapi'", 'from "fastapi"',
        "from 'starlette'", 'from "starlette"',
    ):
        assert tok not in text, f"infra/api.ts must stay free of {tok!r}."


def test_infra_file_exports_named_fns() -> None:
    """PR 5a commits to two named exports: `fetchTaxon` and `fetchChildren`. ODD-VTREE-001 adds `fetchDomains`. ODD-TDS-001 adds `fetchSearches`. The barrel re-export breaks on a default export."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    for name in ("fetchTaxon", "fetchChildren", "fetchDomains", "fetchSearches"):
        pattern = rf"export\s+(?:async\s+)?function\s+{name}\b|export\s+const\s+{name}\b"
        assert re.search(pattern, text), (
            f"infra/api.ts must export `{name}` as a named function or const."
        )


def test_infra_file_exports_source_type_and_domains_options() -> None:
    """ODD-NTP-001: the public `TaxonomySource` type + `FetchDomainsOptions`
    interface are re-exported from the taxonomy barrel so React callers
    can type the source option on `fetchDomains` / `fetchChildren`
    without a deep import. A future PR that demotes the type to
    module-local breaks the source-aware API contract."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    assert re.search(
        r"export\s+type\s+TaxonomySource\b",
        text,
    ), "infra/api.ts must export `TaxonomySource` as a public type."
    assert re.search(
        r"export\s+interface\s+FetchDomainsOptions\b",
        text,
    ), "infra/api.ts must export `FetchDomainsOptions` as a public interface."
    # The source union must pin exactly the three FastAPI-accepted
    # values — same shape as the FastAPI `Query(pattern=...)` regex
    # in `api/server.py::get_children`.
    assert re.search(
        r"TaxonomySource\s*=\s*[\"\']col[\"\']\s*\|\s*[\"\']worms[\"\']\s*\|\s*[\"\']freshwater[\"\']",
        text,
    ), "TaxonomySource must enumerate exactly 'col' | 'worms' | 'freshwater'."


def test_infra_file_exports_search_link_type_and_options() -> None:
    """ODD-TDS-001: the public `SearchLink` type + `FetchSearchesOptions`
    interface are exported from `infra/api.ts` so React callers can
    type the search-link payload without a deep import. The runtime
    helper `fetchSearches` mirrors the byte-identical `engine` /
    `label` / `url` shape of the FastAPI `api/server.py::SearchLink`
    Pydantic model — the URL is server-composed and must NEVER be
    reconstructed client-side. A future PR that drops either export
    breaks the React cutover's typed SearchTab wiring.
    """
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    assert re.search(
        r"export\s+interface\s+SearchLink\b",
        text,
    ), "infra/api.ts must export `SearchLink` as a public interface."
    assert re.search(
        r"export\s+interface\s+FetchSearchesOptions\b",
        text,
    ), "infra/api.ts must export `FetchSearchesOptions` as a public interface."
    # The SearchLink interface must carry exactly `engine` + `label`
    # + `url` — the FastAPI Pydantic model field set. A future PR
    # that adds a client-side `icon` or `category` field would leak
    # server composition concerns into the client contract.
    assert re.search(
        r"interface\s+SearchLink\b[^}]*readonly\s+engine\s*:\s*string",
        text,
    ), "SearchLink must carry `readonly engine: string`."
    assert re.search(
        r"interface\s+SearchLink\b[^}]*readonly\s+label\s*:\s*string",
        text,
    ), "SearchLink must carry `readonly label: string`."
    assert re.search(
        r"interface\s+SearchLink\b[^}]*readonly\s+url\s*:\s*string",
        text,
    ), "SearchLink must carry `readonly url: string`."


# ---------------------------------------------------------------------------
# Compile + runtime contract (Node harness with injected fetch).
# ---------------------------------------------------------------------------
def _run_tsc_isolated(source: Path, out_dir: Path) -> subprocess.CompletedProcess:
    """Compile `api.ts` under `--strict`, `--target ES2022`,
    `--module commonjs`, `--lib ES2022` (no DOM — fetch must be
    injectable). `--rootDir` pins the output layout across transitive
    imports."""
    return subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--strict", "--target", "ES2022",
            "--module", "commonjs", "--lib", "ES2022",
            "--skipLibCheck", "--esModuleInterop",
            "--rootDir", "src/modules/taxonomy",
            "--outDir", str(out_dir),
            str(source),
        ],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )


_NODE_HARNESS = r"""
const path = require("path");
const assert = require("assert");
const api = require(path.resolve(process.argv[2]));

function makeFetch(responses) {
  const calls = [];
  const fn = async (input, init) => {
    calls.push({ input, init });
    const r = responses[calls.length - 1];
    if (!r) throw new Error("unexpected fetch call #" + calls.length);
    return {
      ok: r.ok, status: r.status, statusText: r.statusText || "",
      json: () => r.json,
    };
  };
  fn.calls = calls;
  return fn;
}

// ODD-NTP-001 — wire fixture for the native FastAPI `Taxon` payload.
// Every legacy tree field exposed on the public wire is present
// with realistic values (CoL + WoRMS identifiers + freshwater parent
// relation + UI metadata). `worms_parent_id` is intentionally
// absent — the FastAPI `Taxon` Pydantic model does not expose it,
// and the canonical projection must not invent a client-visible
// field for a private server column. The canonical projection
// must surface every wire field without coercion.
const ANIMALIA = { id: 5, scientific_name: "Animalia", rank: "kingdom",
  authorship: null, parent_id: null,
  coldp_id: "K", worms_id: 2, freshwater_id: null,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: "Animalia",
  species_count: 134, research_path_exists: true,
};
const CHORDATA = { id: 6, scientific_name: "Chordata", rank: "phylum",
  authorship: "Bateson, 1885", parent_id: 5,
  coldp_id: "64HXG", worms_id: 1821, freshwater_id: null,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: "Animalia|Chordata",
  species_count: 80, research_path_exists: null,
};
// ODD-NTP-001 — CoL-only wire row (no WoRMS / Freshwater match). The
// projection must surface null for every absent identifier / source
// parent — never coerced to zero, empty string, or another source.
const COL_ONLY = { id: 7, scientific_name: "Arthropoda", rank: "phylum",
  authorship: null, parent_id: 5,
  coldp_id: "64HXH", worms_id: null, freshwater_id: null,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: "Animalia|Arthropoda",
  species_count: 100, research_path_exists: false,
};
// ODD-NTP-001 — freshwater-overlay row. freshwater_parent_id is the
// real hierarchy; parent_id is null because the CSV rows don't carry
// a CoL backbone link. The projection must keep both fields distinct.
const FW_CICHLID = { id: 101, scientific_name: "Cichlidae", rank: "family",
  authorship: null, parent_id: null,
  coldp_id: null, worms_id: null, freshwater_id: 12,
  freshwater_parent_id: 100,
  status: "accepted", is_extinct: false, path: null,
  species_count: 50, research_path_exists: null,
};
// ODD-VTREE-001 — /api/domains fixture: Biota is a real superdomain
// returned by FastAPI (worms_id=1). Eukaryota is a CoL domain. The
// Freshwater Fishes row carries `rank="collection"` so the synthetic
// root is covered too.
const BIOTA = { id: 1, scientific_name: "Biota", rank: "superdomain",
  authorship: null, parent_id: null,
  coldp_id: null, worms_id: 1, freshwater_id: null,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: null,
  species_count: 250000, research_path_exists: true,
};
const EUKARYOTA = { id: 2, scientific_name: "Eukaryota", rank: "domain",
  authorship: null, parent_id: null,
  coldp_id: "D", worms_id: null, freshwater_id: null,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: "Eukaryota",
  species_count: 200000, research_path_exists: true,
};
const FW_ROOT = { id: 100, scientific_name: "Freshwater Fishes", rank: "collection",
  authorship: null, parent_id: null,
  coldp_id: null, worms_id: null, freshwater_id: 1,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: null,
  species_count: 18000, research_path_exists: true,
};
// ODD-VTREE-002 — live-API evidence: the live `Viruses` row carries
// `rank="unranked"` and the live child payload carries ICNV viral
// `realm` rows (Adnaviria, Riboviria, …). Both must survive the
// canonical fetchDomains / fetchChildren projection without coercion.
const VIRUSES = { id: 5392750, scientific_name: "Viruses", rank: "unranked",
  authorship: null, parent_id: null,
  coldp_id: "V", worms_id: null, freshwater_id: null,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: "Viruses",
  species_count: 9000, research_path_exists: null,
};
const ADNAVIRIA = { id: 10, scientific_name: "Adnaviria", rank: "realm",
  authorship: null, parent_id: 5392750,
  coldp_id: null, worms_id: null, freshwater_id: null,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: "Viruses|Adnaviria",
  species_count: 5, research_path_exists: null,
};
const RIBOVIRIA = { id: 11, scientific_name: "Riboviria", rank: "realm",
  authorship: null, parent_id: 5392750,
  coldp_id: null, worms_id: null, freshwater_id: null,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: "Viruses|Riboviria",
  species_count: 5000, research_path_exists: null,
};

// ODD-NTP-001 (regression — real `/source=worms` wire shape) — the
// actual `/api/taxon/5953123/children?source=worms` response captured
// against the live FastAPI server (see `docs/runbook-freshwater-…`
// + the ODD-NTP-001 correction log). The wire shape carries every
// FastAPI `Taxon` field EXCEPT `worms_parent_id` — the canonical
// `Taxon` projection MUST accept this shape, surface every wire
// field, and NOT invent a `worms_parent_id` slot. The runtime check
// below pins all three contracts in one assertion.
const REAL_WORMS_CHILD = {
  id: 41675, scientific_name: "Animalia", rank: "kingdom",
  authorship: "", parent_id: 41674,
  coldp_id: "N", worms_id: 2, freshwater_id: null,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: "/Eukaryota/Animalia",
  species_count: 1607192, research_path_exists: true,
};

(async () => {
  // fetchTaxon happy path — wire → domain, URL build.
  const f1 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: ANIMALIA }]);
  const t = await api.fetchTaxon(5, { fetch: f1, baseUrl: "http://x" });
  assert.strictEqual(f1.calls.length, 1);
  assert.strictEqual(f1.calls[0].input, "http://x/api/taxon/5");
  assert.strictEqual(t.id, 5);
  assert.strictEqual(t.name, "Animalia");
  assert.strictEqual(t.rank, "kingdom");
  assert.strictEqual(t.authorship, null);
  assert.strictEqual(t.parent_id, null);
  // ODD-NTP-001 — every legacy tree field exposed on the wire
  // survives projection with FastAPI nullability preserved (CoL +
  // WoRMS row, no freshwater). `worms_parent_id` is intentionally
  // absent — see REAL_WORMS_CHILD below for the regression check
  // that the canonical projection does NOT invent it.
  assert.strictEqual(t.coldp_id, "K");
  assert.strictEqual(t.worms_id, 2);
  assert.strictEqual(t.freshwater_id, null);
  assert.strictEqual(t.freshwater_parent_id, null);
  assert.strictEqual(t.status, "accepted");
  assert.strictEqual(t.is_extinct, false);
  assert.strictEqual(t.path, "Animalia");
  assert.strictEqual(t.species_count, 134);
  assert.strictEqual(t.research_path_exists, true);

  // ODD-NTP-001 — CoL-only wire payload: every absent source id /
  // source parent surfaces as null, never coerced to zero or empty
  // string or to another source's value.
  const f1b = makeFetch([{ ok: true, status: 200, statusText: "OK", json: COL_ONLY }]);
  const colOnly = await api.fetchTaxon(7, { fetch: f1b, baseUrl: "http://x" });
  assert.strictEqual(colOnly.coldp_id, "64HXH");
  assert.strictEqual(colOnly.worms_id, null);
  assert.strictEqual(colOnly.freshwater_id, null);
  assert.strictEqual(colOnly.freshwater_parent_id, null);
  assert.strictEqual(colOnly.research_path_exists, false);

  // ODD-NTP-001 — freshwater-overlay wire row: freshwater_parent_id
  // is the real hierarchy; parent_id is null. Both must survive
  // independently — coercing freshwater_parent_id → parent_id would
  // break the CoL walker, coercing parent_id → 0 would break the
  // CoL tree (the row would be re-parented under id=0).
  const f1c = makeFetch([{ ok: true, status: 200, statusText: "OK", json: FW_CICHLID }]);
  const fw = await api.fetchTaxon(101, { fetch: f1c, baseUrl: "http://x" });
  assert.strictEqual(fw.parent_id, null);
  assert.strictEqual(fw.freshwater_parent_id, 100);
  assert.strictEqual(fw.freshwater_id, 12);

  // ODD-NTP-001 (regression — real /source=worms wire shape) —
  // fetchTaxon against the live `/api/taxon/5953123/children?source=worms`
  // response (REAL_WORMS_CHILD above) must (a) succeed without
  // throwing, (b) surface every wire field, and (c) NOT invent a
  // `worms_parent_id` slot on the canonical `Taxon`. The last check
  // is the structural guard: a canonical Taxon has no
  // `worms_parent_id` property because the FastAPI wire does not
  // expose it. Inventing the field would (a) be unreachable from
  // any real fetch, (b) leak a private server column into the
  // client contract, and (c) require a future coordinated server +
  // client change to ever populate. WoRMS source-aware parent
  // ancestry must instead be built from attached tree edges (see
  // the domain `Taxon` JSDoc + the ODD-NTP-001 correction log).
  const fReal = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: REAL_WORMS_CHILD }]);
  const realWorms = await api.fetchTaxon(41675, { fetch: fReal, baseUrl: "http://x" });
  assert.strictEqual(realWorms.id, 41675);
  assert.strictEqual(realWorms.name, "Animalia");
  assert.strictEqual(realWorms.rank, "kingdom");
  assert.strictEqual(realWorms.parent_id, 41674);
  assert.strictEqual(realWorms.coldp_id, "N");
  assert.strictEqual(realWorms.worms_id, 2);
  assert.strictEqual(realWorms.freshwater_id, null);
  assert.strictEqual(realWorms.freshwater_parent_id, null);
  assert.strictEqual(realWorms.status, "accepted");
  assert.strictEqual(realWorms.is_extinct, false);
  assert.strictEqual(realWorms.path, "/Eukaryota/Animalia");
  assert.strictEqual(realWorms.species_count, 1607192);
  assert.strictEqual(realWorms.research_path_exists, true);
  // The structural regression: the canonical Taxon MUST NOT carry
  // a `worms_parent_id` property — confirming in one runtime check
  // that the projection does not invent the field.
  assert.strictEqual(Object.prototype.hasOwnProperty.call(realWorms, "worms_parent_id"), false,
    "ODD-NTP-001 regression: canonical Taxon must not carry a worms_parent_id property; " +
    "the FastAPI wire does not expose the field.");

  // fetchTaxon HTTP non-OK — throws with status in message.
  const f2 = makeFetch([{ ok: false, status: 404, statusText: "Not Found", json: { detail: "taxon 99 not found" } }]);
  await assert.rejects(
    () => api.fetchTaxon(99, { fetch: f2, baseUrl: "http://x" }),
    (err) => /404/.test(String(err && err.message || err)),
    "fetchTaxon must reject on non-OK with the status code in the message",
  );

  // fetchTaxon malformed JSON — throws.
  const f3 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: Promise.reject(new SyntaxError("Unexpected token < in JSON")) }]);
  await assert.rejects(
    () => api.fetchTaxon(5, { fetch: f3, baseUrl: "http://x" }),
    (err) => /json|JSON/i.test(String(err && err.message || err)),
  );

  // fetchTaxon schema-invalid payload ({}) — throws.
  const f4 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: {} }]);
  await assert.rejects(
    () => api.fetchTaxon(5, { fetch: f4, baseUrl: "http://x" }),
    (err) => /invalid|taxon/i.test(String(err && err.message || err)),
  );

  // fetchChildren happy path — array of mapped Taxons; the projection
  // carries every legacy tree field exposed on the wire (ODD-NTP-001).
  const f5 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [CHORDATA, COL_ONLY] }]);
  const kids = await api.fetchChildren(5, { fetch: f5, baseUrl: "http://x" });
  assert.ok(Array.isArray(kids));
  assert.strictEqual(kids.length, 2);
  assert.strictEqual(kids[0].name, "Chordata");
  assert.strictEqual(kids[0].rank, "phylum");
  // ODD-NTP-001 — Chordata carries worms_id because it has a WoRMS
  // match. The canonical Taxon does NOT carry worms_parent_id (the
  // FastAPI wire does not expose it) — see the structural regression
  // below for the guard.
  assert.strictEqual(kids[0].worms_id, 1821);
  assert.strictEqual(Object.prototype.hasOwnProperty.call(kids[0], "worms_parent_id"), false,
    "ODD-NTP-001 regression: canonical Taxon must not carry a worms_parent_id property.");
  // ODD-NTP-001 — Arthropoda is a CoL-only row. worms_id /
  // freshwater_id / freshwater_parent_id must all surface as null
  // (never coerced).
  assert.strictEqual(kids[1].coldp_id, "64HXH");
  assert.strictEqual(kids[1].worms_id, null);
  assert.strictEqual(kids[1].freshwater_id, null);
  assert.strictEqual(kids[1].freshwater_parent_id, null);

  // fetchChildren ?source=worms — query forwarded verbatim.
  const f6 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchChildren(5, { fetch: f6, baseUrl: "http://x", source: "worms" });
  assert.strictEqual(f6.calls[0].input, "http://x/api/taxon/5/children?source=worms",
    "fetchChildren must forward ?source=… verbatim: " + f6.calls[0].input);

  // fetchChildren ?source=freshwater — query forwarded verbatim.
  const f6b = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchChildren(5, { fetch: f6b, baseUrl: "http://x", source: "freshwater" });
  assert.strictEqual(f6b.calls[0].input, "http://x/api/taxon/5/children?source=freshwater");

  // fetchChildren ?source=col — explicit CoL query (default shape
  // also byte-identical to the pre-ODD-NTP-001 contract when no
  // source is supplied — see the assertion below).
  const f6c = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchChildren(5, { fetch: f6c, baseUrl: "http://x", source: "col" });
  assert.strictEqual(f6c.calls[0].input, "http://x/api/taxon/5/children?source=col");

  // fetchChildren with NO source — URL stays byte-identical to the
  // pre-ODD-NTP-001 contract (no trailing `?`, no empty fragment).
  const f6d = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchChildren(5, { fetch: f6d, baseUrl: "http://x" });
  assert.strictEqual(f6d.calls[0].input, "http://x/api/taxon/5/children",
    "fetchChildren without source must stay byte-identical to the pre-ODD-NTP-001 URL");

  // fetchChildren non-OK — throws.
  const f7 = makeFetch([{ ok: false, status: 500, statusText: "Server Error", json: { detail: "boom" } }]);
  await assert.rejects(
    () => api.fetchChildren(5, { fetch: f7, baseUrl: "http://x" }),
    (err) => /500/.test(String(err && err.message || err)),
  );

  // ODD-VTREE-001 — fetchDomains happy path with superdomain + domain +
  // synthetic-root payload. The shared `fromWireList` helper projects
  // every element through the same wire → domain mapping as
  // fetchTaxon / fetchChildren.
  const f8 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [BIOTA, EUKARYOTA, FW_ROOT] }]);
  const roots = await api.fetchDomains({ fetch: f8, baseUrl: "http://x" });
  assert.strictEqual(roots.length, 3);
  assert.strictEqual(f8.calls[0].input, "http://x/api/domains");
  assert.strictEqual(roots[0].rank, "superdomain");
  assert.strictEqual(roots[1].rank, "domain");
  assert.strictEqual(roots[2].rank, "collection");
  for (const r of roots) assert.strictEqual(r.parent_id, null);
  // ODD-NTP-001 — every legacy tree field exposed on the wire
  // survives the canonical /api/domains projection. The WoRMS Biota
  // row carries worms_id=1 (WoRMS root, but the wire has no
  // worms_parent_id field); the CoL Eukaryota row carries coldp_id
  // but no worms / freshwater match; the synthetic Freshwater
  // Fishes root carries freshwater_id=1 with freshwater_parent_id
  // null.
  const biota = roots.find((r) => r.id === 1);
  assert.strictEqual(biota.coldp_id, null);
  assert.strictEqual(biota.worms_id, 1);
  assert.strictEqual(biota.freshwater_id, null);
  assert.strictEqual(biota.freshwater_parent_id, null);
  assert.strictEqual(biota.status, "accepted");
  assert.strictEqual(biota.is_extinct, false);
  assert.strictEqual(biota.species_count, 250000);
  assert.strictEqual(biota.research_path_exists, true);
  // ODD-NTP-001 structural regression: the canonical Taxon does
  // NOT carry a `worms_parent_id` property — even for the Biota
  // root that has a WoRMS hierarchy in the legacy / Nav.js.
  assert.strictEqual(Object.prototype.hasOwnProperty.call(biota, "worms_parent_id"), false,
    "ODD-NTP-001 regression: canonical Taxon must not carry a worms_parent_id property.");
  const euk = roots.find((r) => r.id === 2);
  assert.strictEqual(euk.coldp_id, "D");
  assert.strictEqual(euk.worms_id, null);
  assert.strictEqual(euk.freshwater_id, null);
  assert.strictEqual(euk.research_path_exists, true);
  const fwRoot = roots.find((r) => r.id === 100);
  assert.strictEqual(fwRoot.freshwater_id, 1);
  assert.strictEqual(fwRoot.freshwater_parent_id, null);
  assert.strictEqual(fwRoot.coldp_id, null);
  assert.strictEqual(fwRoot.worms_id, null);

  // ODD-NTP-001 — fetchDomains ?source=col|worms|freshwater — query
  // forwarded verbatim. The FastAPI server may ignore the parameter
  // on this endpoint, but the React helper forwards it so future
  // server-side filtering lands without a coordinated React update.
  const f8s_col = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchDomains({ fetch: f8s_col, baseUrl: "http://x", source: "col" });
  assert.strictEqual(f8s_col.calls[0].input, "http://x/api/domains?source=col",
    "fetchDomains must forward ?source=col verbatim: " + f8s_col.calls[0].input);
  const f8s_worms = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchDomains({ fetch: f8s_worms, baseUrl: "http://x", source: "worms" });
  assert.strictEqual(f8s_worms.calls[0].input, "http://x/api/domains?source=worms",
    "fetchDomains must forward ?source=worms verbatim: " + f8s_worms.calls[0].input);
  const f8s_fw = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchDomains({ fetch: f8s_fw, baseUrl: "http://x", source: "freshwater" });
  assert.strictEqual(f8s_fw.calls[0].input, "http://x/api/domains?source=freshwater",
    "fetchDomains must forward ?source=freshwater verbatim: " + f8s_fw.calls[0].input);

  // fetchDomains empty payload — returns [], does not throw.
  const f9 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  assert.strictEqual((await api.fetchDomains({ fetch: f9, baseUrl: "http://x" })).length, 0);

  // fetchDomains HTTP non-OK — status code in message.
  const f10 = makeFetch([{ ok: false, status: 503, statusText: "Service Unavailable", json: { detail: "DB down" } }]);
  await assert.rejects(
    () => api.fetchDomains({ fetch: f10, baseUrl: "http://x" }),
    (err) => /503/.test(String(err && err.message || err)),
  );

  // fetchDomains non-array payload — `fromWireList` rejects.
  const f11 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: { detail: "wrong shape" } }]);
  await assert.rejects(
    () => api.fetchDomains({ fetch: f11, baseUrl: "http://x" }),
    (err) => /non-array/.test(String(err && err.message || err)),
  );

  // fetchDomains schema-invalid element — `fromWire` rejects.
  const f12 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [BIOTA, { id: 99 }] }]);
  await assert.rejects(
    () => api.fetchDomains({ fetch: f12, baseUrl: "http://x" }),
    (err) => /invalid|taxon/i.test(String(err && err.message || err)),
  );

  // ODD-VTREE-002 — `/api/domains`-style `unranked` row passes the
  // canonical projection. The live CoL data carries a `Viruses` row
  // whose rank is `unranked` (it is a CoL root with no asserted
  // kingdom). `fetchDomains` must project it without coercion, the
  // same way it projects `superdomain`, `domain`, and `collection`.
  const f13 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [BIOTA, EUKARYOTA, FW_ROOT, VIRUSES] }]);
  const liveRoots = await api.fetchDomains({ fetch: f13, baseUrl: "http://x" });
  assert.strictEqual(liveRoots.length, 4);
  assert.strictEqual(f13.calls[0].input, "http://x/api/domains");
  const virusesRow = liveRoots.find((r) => r.id === 5392750);
  assert.ok(virusesRow, "fetchDomains must surface the live unranked Viruses row");
  assert.strictEqual(virusesRow.rank, "unranked");
  assert.strictEqual(virusesRow.name, "Viruses");
  assert.strictEqual(virusesRow.parent_id, null);

  // ODD-VTREE-002 — child-list `realm` row passes the canonical
  // projection. The live payload returned by
  // `/api/taxon/{Viruses}/children` includes ICNV viral realms
  // (Adnaviria, Riboviria, …); `fetchChildren` must surface them
  // without coercion.
  const f14 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [ADNAVIRIA, RIBOVIRIA] }]);
  const viralChildren = await api.fetchChildren(5392750, { fetch: f14, baseUrl: "http://x" });
  assert.strictEqual(viralChildren.length, 2);
  assert.strictEqual(f14.calls[0].input, "http://x/api/taxon/5392750/children");
  assert.ok(viralChildren.every((c) => c.rank === "realm"),
    "fetchChildren must surface every viral realm row as rank=realm; got " +
    JSON.stringify(viralChildren.map((c) => c.rank)));
  assert.strictEqual(viralChildren[0].name, "Adnaviria");
  assert.strictEqual(viralChildren[0].parent_id, 5392750);
  assert.strictEqual(viralChildren[1].name, "Riboviria");
  assert.strictEqual(viralChildren[1].parent_id, 5392750);
  // ODD-NTP-001 — viral realm rows must surface every legacy tree
  // field exposed on the wire with FastAPI nullability preserved
  // (no CoL/WoRMS/FW id; no source-specific parent; path is
  // populated). The structural regression guards the
  // `worms_parent_id` non-invention contract on every projected row.
  for (const c of viralChildren) {
    assert.strictEqual(c.coldp_id, null);
    assert.strictEqual(c.worms_id, null);
    assert.strictEqual(c.freshwater_id, null);
    assert.strictEqual(c.freshwater_parent_id, null);
    assert.strictEqual(Object.prototype.hasOwnProperty.call(c, "worms_parent_id"), false,
      "ODD-NTP-001 regression: canonical Taxon must not carry a worms_parent_id property.");
    assert.strictEqual(c.status, "accepted");
    assert.strictEqual(c.is_extinct, false);
    assert.ok(typeof c.path === "string" && c.path.startsWith("Viruses|"),
      "viral realm path must be populated; got " + JSON.stringify(c.path));
    assert.strictEqual(typeof c.species_count, "number");
  }

  // ---- ODD-TDS-001 — fetchSearches wire → domain projection ----
  // The server returns 14 canonical search engines + 3 curated
  // destinations (the threads/facebook entries) — the wire
  // payload covers all 17. The React port's projection preserves
  // every wire field verbatim (the URL is server-composed and
  // must NOT be reconstructed client-side). The runtime check
  // pins the fetchSearches contract in one assertion block.
  const SFresh = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [
      { engine: "google",         label: "Google",          url: "https://www.google.com/search?q=Freshwater+Fishes" },
      { engine: "imagen",         label: "Images",          url: "https://www.google.com/search?q=Freshwater+Fishes&tbm=isch" },
      { engine: "documentos",     label: "Documents",       url: "https://www.google.com/search?q=Freshwater+Fishes+%28filetype%3Adoc+OR+filetype%3Adocx+OR+filetype%3Atxt%29" },
      { engine: "pdf",            label: "PDF",             url: "https://www.google.com/search?q=Freshwater+Fishes+filetype%3Apdf" },
      { engine: "wikipedia",      label: "Wikipedia",       url: "https://en.wikipedia.org/wiki/Special:Search?search=Freshwater+Fishes" },
      { engine: "bhl",            label: "BHL",             url: "https://www.biodiversitylibrary.org/search?searchTerm=Freshwater+Fishes" },
      { engine: "researchgate",   label: "ResearchGate",    url: "https://www.researchgate.net/search/publication?q=Freshwater+Fishes" },
      { engine: "plos",           label: "PLOS",            url: "https://journals.plos.org/plosone/search?query=Freshwater+Fishes" },
      { engine: "academia",       label: "Academia.edu",    url: "https://www.academia.edu/search?q=Freshwater+Fishes" },
      { engine: "scielo",         label: "Scielo",          url: "https://search.scielo.org/?q=Freshwater+Fishes" },
      { engine: "scholar",        label: "Scholar",         url: "https://scholar.google.com/scholar?q=Freshwater+Fishes" },
      { engine: "youtube",        label: "YouTube",         url: "https://www.youtube.com/results?search_query=Freshwater+Fishes" },
      { engine: "zootaxa",        label: "Zootaxa",         url: "https://www.biotaxa.org/Zootaxa/search?query=Freshwater+Fishes" },
      { engine: "scribd",         label: "Scribd",          url: "https://www.scribd.com/search?query=Freshwater+Fishes" },
      { engine: "threads_acipenser",         label: "Threads: Acipenser",          url: "https://www.threads.com/search?q=acipenser&serp_type=default&xmt=AQG0AC54-jrPT9LBkalK5Lx_FGM7VtC3KUhDTE2hJLKTAwE" },
      { engine: "facebook_acipenser_baerii", label: "Facebook: Acipenser baerii",  url: "https://www.facebook.com/search/top?q=acipenser%20baerii" },
      { engine: "threads_shared_post",       label: "Threads: Shared post",        url: "https://www.threads.com/share/BAnZDpDtPZ/" },
    ],
  }]);
  const links = await api.fetchSearches(100, { fetch: SFresh, baseUrl: "http://x" });
  assert.strictEqual(SFresh.calls.length, 1);
  assert.strictEqual(SFresh.calls[0].input, "http://x/api/taxon/100/searches",
    "fetchSearches must build the canonical /api/taxon/{id}/searches URL");
  assert.strictEqual(Array.isArray(links), true, "fetchSearches must return an array");
  assert.strictEqual(links.length, 17,
    "fetchSearches must surface every server-returned SearchLink (14 canonical + 3 curated destinations)");
  // URL preservation is the central ODD-TDS-001 contract — the
  // server-composed encoding must reach the React port verbatim.
  // We compare the exact google entry here so the test fails
  // loud-and-clear if a future PR ever strips encoding or tries
  // to template-fill a URL locally.
  assert.strictEqual(links[0].engine, "google");
  assert.strictEqual(links[0].label, "Google");
  assert.strictEqual(links[0].url, "https://www.google.com/search?q=Freshwater+Fishes",
    "URL preservation contract: server-composed URL must reach the client verbatim");
  // Every entry must carry non-empty engine + label + url strings.
  for (const l of links) {
    assert.strictEqual(typeof l.engine, "string");
    assert.strictEqual(typeof l.label, "string");
    assert.strictEqual(typeof l.url, "string");
    assert.ok(l.engine.length > 0, "engine key must be non-empty");
    assert.ok(l.label.length > 0, "label must be non-empty");
    assert.ok(l.url.length > 0, "url must be non-empty");
  }
  // The SearchLink projection must NOT carry any invented field.
  // The server payload has only `engine` + `label` + `url`; a
  // canonical SearchLink with extra fields (e.g. `icon`, `category`,
  // `template`) would leak server composition concerns into the
  // client contract and let future drift slip past the projection.
  for (const l of links) {
    const props = Object.keys(l).sort();
    assert.deepStrictEqual(props, ["engine", "label", "url"],
      "ODD-TDS-001: canonical SearchLink must carry exactly {engine,label,url}; got " + JSON.stringify(props));
  }
  // The three curated destinations (the threads/facebook entries)
  // must surface as ordinary SearchLink entries — the React
  // port's SearchTab filters them through the pure category
  // bridge so they don't render in the 5-category grid, but the
  // wire projection must preserve them so a future category slot
  // can carry them without a coordinated server change.
  const ac = links.find((l) => l.engine === "threads_acipenser");
  assert.ok(ac, "fetchSearches must surface the threads_acipenser curated destination");
  assert.strictEqual(ac.url, "https://www.threads.com/search?q=acipenser&serp_type=default&xmt=AQG0AC54-jrPT9LBkalK5Lx_FGM7VtC3KUhDTE2hJLKTAwE",
    "curated destination URL must round-trip verbatim (server is the source of truth)");

  // fetchSearches empty payload — returns [], does not throw.
  const SEmpty = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  assert.strictEqual((await api.fetchSearches(100, { fetch: SEmpty, baseUrl: "http://x" })).length, 0);

  // fetchSearches HTTP non-OK — status code in message.
  const SBad = makeFetch([{ ok: false, status: 503, statusText: "Service Unavailable", json: { detail: "DB down" } }]);
  await assert.rejects(
    () => api.fetchSearches(100, { fetch: SBad, baseUrl: "http://x" }),
    (err) => /503/.test(String(err && err.message || err)),
    "fetchSearches must reject on non-OK with the status code in the message",
  );

  // fetchSearches non-array payload — `fromWireSearchList` rejects.
  const SWrongShape = makeFetch([{ ok: true, status: 200, statusText: "OK", json: { detail: "wrong shape" } }]);
  await assert.rejects(
    () => api.fetchSearches(100, { fetch: SWrongShape, baseUrl: "http://x" }),
    (err) => /non-array/.test(String(err && err.message || err)),
    "fetchSearches must reject non-array payloads",
  );

  // fetchSearches schema-invalid element — `isValidSearchLink` rejects.
  const SBadElement = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ engine: "google", label: "Google" /* missing url */ }] }]);
  await assert.rejects(
    () => api.fetchSearches(100, { fetch: SBadElement, baseUrl: "http://x" }),
    (err) => /invalid|search/i.test(String(err && err.message || err)),
    "fetchSearches must reject per-element shape mismatches",
  );

  // fetchSearches negative id — id validation rejects.
  await assert.rejects(
    () => api.fetchSearches(-1, { fetch: makeFetch([]), baseUrl: "http://x" }),
    (err) => /non-negative integer/i.test(String(err && err.message || err)),
    "fetchSearches must reject negative ids",
  );

  // fetchSearches malformed JSON — throws.
  const SJsonFail = makeFetch([{ ok: true, status: 200, statusText: "OK", json: Promise.reject(new SyntaxError("Unexpected token < in JSON")) }]);
  await assert.rejects(
    () => api.fetchSearches(100, { fetch: SJsonFail, baseUrl: "http://x" }),
    (err) => /json|JSON/i.test(String(err && err.message || err)),
    "fetchSearches must reject malformed JSON",
  );

  process.stdout.write("PASS\n");
})().catch((err) => {
  process.stderr.write("HARNESS_FAILURE: " + (err && err.stack || err) + "\n");
  process.exit(1);
});
"""


@pytest.fixture()
def compiled_infra(tmp_path: Path, require_toolchain: None) -> tuple[Path, Path]:
    """Compile api.ts to CommonJS and write the Node harness."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    result = _run_tsc_isolated(INFRA_FILE, out_dir)
    assert result.returncode == 0, (
        f"api.ts failed to compile in isolated strict mode.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    compiled = out_dir / "infrastructure" / "api.js"
    assert compiled.is_file(), (
        f"tsc did not emit a compiled module at {compiled}. "
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    harness = tmp_path / "harness.cjs"
    harness.write_text(_NODE_HARNESS)
    return compiled, harness


def test_compiled_module_passes_runtime_contract(
    compiled_infra: tuple[Path, Path],
) -> None:
    """Under Node (ES2022, no DOM, fetch injected) the compiled module
    proves:
      1. fetchTaxon maps wire `scientific_name` → domain `name` and
         builds `/api/taxon/{id}` relative to `baseUrl`.
      2. fetchTaxon rejects on HTTP non-OK (status in message).
      3. fetchTaxon rejects when the JSON cannot be parsed.
      4. fetchTaxon rejects when the projected record fails
         `isValidTaxon`.
      5. fetchChildren returns an array of mapped Taxons.
      6. fetchChildren forwards `?source=…` verbatim.
      7. fetchChildren rejects on a 500.
      8. fetchDomains returns a mapped array including a WoRMS
         superdomain, a CoL domain, and a `collection` synthetic root
         (ODD-VTREE-001).
      9. fetchDomains returns an empty array for an empty payload.
     10. fetchDomains rejects on HTTP non-OK with the status code in
         the message.
     11. fetchDomains rejects non-array payloads via `fromWireList`.
     12. fetchDomains rejects schema-invalid elements via `fromWire`.
     13. ODD-VTREE-002: `/api/domains`-style `unranked` row passes the
         canonical `fetchDomains` projection without coercion.
     14. ODD-VTREE-002: child-list `realm` rows pass the canonical
         `fetchChildren` projection without coercion.
    """
    compiled, harness = compiled_infra
    result = subprocess.run(
        ["node", str(harness), str(compiled)],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"runtime harness failed.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected harness output: {result.stdout!r}"
    )
