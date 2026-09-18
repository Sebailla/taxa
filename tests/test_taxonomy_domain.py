"""
Taxonomy domain contract tests (PR 2d).

Pins the externally meaningful contract of
`src/modules/taxonomy/domain/taxon.ts` (the pure domain file PR 2d
ships). Asserts (1) the canonical file path exists, (2) the source
stays free of framework / I/O tokens (spec.md rule 4), (3) the file
compiles in strict mode against the ES2022 library only (no DOM, no
React, no Next, no FastAPI), and (4) the compiled module returns the
correct observable behaviour at runtime under Node.

References:
    openspec/changes/migrate-nextjs-tailwind4/tasks.md   §Phase 2 (2d)
    openspec/changes/migrate-nextjs-tailwind4/design.md  §Interfaces/Contracts
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAIN_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "domain" / "taxon.ts"

# Twenty-three ranks the FastAPI taxonomy endpoints + committed test
# fixtures can return (ODD-VTREE-001 grew to 21; ODD-VTREE-002 added
# `realm` between `superdomain` and `kingdom`, plus `unranked` AFTER
# the named ranked sequence because it carries no asserted taxonomic
# breadth). Ordered broadest-first so
# `RANK_ORDER.indexOf(a) < RANK_ORDER.indexOf(b)` exactly when `a`
# is broader than `b`; mirrors `web/format.js::RANK_ORDER` and the
# FastAPI SQL `RANK_ORDER` CASE in `api/server.py`. Consumers that
# need a positional handle (e.g. `TaxonDetailViewModel.rankIndex`)
# must read it from `RANK_ORDER` at runtime — these indexes do NOT
# match the pre-ODD-VTREE-001 legacy eight.
EXPECTED_RANKS: tuple[str, ...] = (
    "collection", "root", "domain", "superdomain",
    "realm",
    "kingdom", "subkingdom",
    "phylum", "subphylum",
    "class", "subclass",
    "order", "suborder",
    "family", "subfamily",
    "genus", "subgenus",
    "species", "subspecies",
    "variety", "subvariety",
    "form",
    "unranked",
)

# Pinned Taxon field set. design.md §Interfaces/Contracts commits to
# the legacy CoL backbone fields; ODD-NTP-001 grew the canonical
# projection so every legacy tree field from the FastAPI `Taxon`
# payload survives — source identifiers, source-specific parent
# relations (`freshwater_parent_id` only — `worms_parent_id` is NOT
# on the public wire shape), and UI metadata (status / extinction /
# path / counts / research-path indicator). A future PR that
# silently drops any of these fails
# `test_domain_file_declares_expected_taxon_fields` before review.
EXPECTED_TAXON_FIELDS: tuple[str, ...] = (
    "id", "name", "rank", "authorship", "parent_id",
    "coldp_id", "worms_id", "freshwater_id",
    "freshwater_parent_id",
    "status", "is_extinct", "path",
    "species_count", "research_path_exists",
)


# ---------------------------------------------------------------------------
def _has_npx() -> bool:
    return shutil.which("npx") is not None


def _has_node() -> bool:
    return shutil.which("node") is not None


@pytest.fixture()
def require_toolchain() -> None:
    if not (_has_npx() and _has_node()):
        pytest.skip("npx + node required on PATH for compile/runtime test")


# ---------------------------------------------------------------------------
# File presence / source-level purity — no compiler required
# ---------------------------------------------------------------------------
def test_domain_file_exists() -> None:
    """`src/modules/taxonomy/domain/taxon.ts` exists at the canonical
    path design.md commits to. RED marker for PR 2d: before the impl
    lands, this assertion fails outright."""
    assert DOMAIN_FILE.is_file(), (
        f"missing domain file: {DOMAIN_FILE}. PR 2d ships this file."
    )


def test_domain_file_is_plain_typescript() -> None:
    """`.ts`, not `.tsx` — domain stays plain types (design.md).
    JSX belongs to presentation, not domain."""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    assert DOMAIN_FILE.suffix == ".ts", (
        f"domain file must be TypeScript; got suffix={DOMAIN_FILE.suffix}"
    )


def test_domain_file_has_no_framework_imports() -> None:
    """Spec.md rule 4: domain stays free of presentation,
    application, browser, HTTP, framework, or infrastructure. The
    source-level guard catches accidental `from 'react'` /
    `from 'next/...'` / `from 'fastapi'` lines that would slip past
    a runtime-only check."""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    forbidden_tokens = (
        "react", "next", "nextjs",
        "fastapi", "starlette", "pydantic",
        "fetch(", "localStorage", "document.", "window.", "process.",
    )
    for token in forbidden_tokens:
        assert token not in text, (
            f"taxon.ts must stay free of {token!r}; spec.md rule 4 forbids "
            f"framework / I/O references in the domain layer."
        )


def test_domain_file_declares_expected_taxon_fields() -> None:
    """Every pinned field MUST appear in the source — a future PR that
    silently drops e.g. `parent_id` fails this test before review.
    ODD-NTP-001: the canonical projection carries every legacy tree
    field from the FastAPI `Taxon` payload (identifiers, source-specific
    parent relations, UI metadata); this assertion pins the source-level
    declaration so a future PR cannot silently drop one of them."""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    for field in EXPECTED_TAXON_FIELDS:
        assert re.search(rf"\b{re.escape(field)}\b\s*:", text), (
            f"taxon.ts is missing required field '{field}' (design.md + ODD-NTP-001)."
        )


def test_domain_file_does_not_invent_worms_parent_id() -> None:
    """ODD-NTP-001 (regression — no invented client field): the
    canonical `Taxon` interface MUST NOT declare `worms_parent_id`.
    The FastAPI `Taxon` Pydantic model (`api/server.py`) exposes
    `parent_id` + `freshwater_parent_id` but does NOT expose
    `worms_parent_id`; the WoRMS overlay column is used internally
    by `api/server.py::get_children` but is not on the public wire
    shape. A canonical `Taxon` carrying an invented `worms_parent_id`
    would (a) be unreachable from any real fetch, (b) leak a private
    server column into the client contract, and (c) require a
    future coordinated server + client change to ever populate.
    This source-level guard catches a future PR that re-introduces
    the field before it reaches review. The runtime equivalent
    (asserting `fromWire` doesn't surface the field on a real wire
    payload) lives in `tests/test_taxonomy_infra.py`."""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    # Restrict the search to the `Taxon` interface body so a comment
    # reference (e.g. "WoRMS overlay … `worms_parent_id` … is not
    # on the canonical projection") does not trip the guard. We match
    # a TypeScript field declaration (`readonly worms_parent_id:` or
    # `worms_parent_id:`) so an explanatory comment is allowed.
    taxon_block_re = re.compile(
        r"export\s+interface\s+Taxon\b[\s\S]*?\n\}",
        re.MULTILINE,
    )
    m = taxon_block_re.search(text)
    assert m, "Taxon interface block not found in taxon.ts."
    block = m.group(0)
    assert not re.search(r"\bworms_parent_id\s*:", block), (
        "ODD-NTP-001: the canonical `Taxon` interface MUST NOT "
        "declare `worms_parent_id` — the FastAPI wire does not "
        "expose it. WoRMS source-aware parent ancestry must be "
        "built from attached tree edges (or a separately "
        "authorized backend change)."
    )


def test_domain_file_declares_all_eight_ranks() -> None:
    """Each of the eight Linnaean ranks MUST appear as a string
    literal. A future PR that drops e.g. `subspecies` fails here.
    (The function name is a legacy leftover from the pre-ODD-VTREE-001
    contract; the assertion iterates the full `EXPECTED_RANKS` tuple,
    so the live ranks (`realm`, `unranked`) are covered too.)"""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    for rank in EXPECTED_RANKS:
        assert f'"{rank}"' in text, (
            f"taxon.ts Rank union must include {rank!r} (design.md)."
        )


# ---------------------------------------------------------------------------
# Compile in isolation — single file, strict mode, ES2022 only.
# ---------------------------------------------------------------------------
def _run_tsc_isolated(source: Path, out_dir: Path) -> subprocess.CompletedProcess:
    """Compile `taxon.ts` in isolation. Flags mirror project tsconfig +
    design.md §Interfaces/Contracts: `--strict`, `--target ES2022`,
    `--module commonjs` (so Node can `require` the output), `--lib
    ES2022` (no DOM — task requirement)."""
    return subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--strict",
            "--target", "ES2022",
            "--module", "commonjs",
            "--lib", "ES2022",
            "--skipLibCheck",
            "--esModuleInterop",
            "--outDir", str(out_dir),
            str(source),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


# Runtime harness — loaded by Node after tsc has emitted taxon.js.
# Exercises every externally observable helper. Strict equality on the
# `is*` predicates (the type-narrowing contract) and sign-checks on
# `compareRanks` (the sort-order contract). ODD-VTREE-001 expands the
# rank universe; the harness mirrors `EXPECTED_RANKS` exactly so a
# future PR that drops any rank fails here.
#
# ODD-NTP-001 (native-tree-parity data layer): the harness exercises
# the ODD-NTP-001 contract that every legacy tree field from the
# FastAPI `Taxon` payload survives the canonical projection, with
# FastAPI nullability preserved (null stays null; never coerced to
# zero / empty string / another source). A minimal test-taxonomy
# constructor that omits the optional wire properties still passes
# — the optional-wire validation runs ONLY WHEN PRESENT, so
# existing fixtures (PR 5b / ODD-VTREE-001) keep working.
#
# ODD-NTP-001 (no invented client field): `worms_parent_id` is
# deliberately absent from the canonical projection because the
# FastAPI wire does not expose it. A wire payload matching the real
# `/api/taxon/{id}/children?source=worms` shape (no `worms_parent_id`)
# must validate cleanly without an invented client field.
_HARNESS_SOURCE = r"""
const path = require("path");
const domain = require(path.resolve(process.argv[2]));
// ODD-NTP-001: minimal constructor — no optional wire properties.
// isValidTaxon must still accept it; the optional-wire validation
// only fires when the property is present.
const validTaxon = {
  id: 1, name: "Animalia", rank: "kingdom",
  authorship: null, parent_id: null,
};
// ODD-NTP-001: fully populated Taxon — every legacy tree field set
// with realistic values. isValidTaxon must accept it.
const fullTaxon = {
  id: 5, name: "Animalia", rank: "kingdom",
  authorship: null, parent_id: null,
  coldp_id: "K", worms_id: 2, freshwater_id: null,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: "Animalia",
  species_count: 134, research_path_exists: true,
};
// ODD-NTP-001: every optional field null — CoL-only row (no worms
// match, no freshwater match). isValidTaxon must accept it and
// every source id / source-specific parent must stay null.
const colOnlyTaxon = {
  id: 6, name: "Arthropoda", rank: "phylum",
  authorship: null, parent_id: 5,
  coldp_id: "64HXG", worms_id: null, freshwater_id: null,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: "Animalia|Arthropoda",
  species_count: 100, research_path_exists: null,
};
// ODD-NTP-001 (regression — no invented client field): the real
// `/api/taxon/{id}/children?source=worms` wire shape carries every
// FastAPI `Taxon` field EXCEPT `worms_parent_id` (confirmed against
// the live FastAPI Pydantic model + a real
// `/api/taxon/5953123/children?source=worms` response). A canonical
// `Taxon` matching this shape — optional wire fields set or unset
// per the wire — must validate cleanly. This is the regression
// assertion that catches a future PR which invents a
// `worms_parent_id` field on the canonical domain.
const realWormsChildren = {
  id: 41675, name: "Animalia", rank: "kingdom",
  authorship: "", parent_id: 41674,
  coldp_id: "N", worms_id: 2, freshwater_id: null,
  freshwater_parent_id: null,
  status: "accepted", is_extinct: false, path: "/Eukaryota/Animalia",
  species_count: 1607192, research_path_exists: true,
};
// Broadest-first ordering mirrors web/format.js::RANK_ORDER and the
// FastAPI SQL RANK_ORDER CASE (api/server.py). `RANK_ORDER.indexOf(a)
// < RANK_ORDER.indexOf(b)` exactly when `a` is broader than `b`.
// ODD-VTREE-002 adds `realm` (viral clade between superdomain and
// kingdom) and `unranked` (breadth-less tail — sorts after every
// named rank because CoL surfaces unranked clades at the root when
// no kingdom has been asserted; ordering between two `unranked`
// rows falls back to name).
const expectedRanks = [
  "collection", "root", "domain", "superdomain",
  "realm",
  "kingdom", "subkingdom",
  "phylum", "subphylum",
  "class", "subclass",
  "order", "suborder",
  "family", "subfamily",
  "genus", "subgenus",
  "species", "subspecies",
  "variety", "subvariety", "form",
  "unranked",
];
const newRanks = [
  "collection", "root", "domain", "superdomain", "realm",
  "subkingdom", "subphylum", "subclass", "suborder",
  "subfamily", "subgenus",
  "variety", "subvariety", "form", "unranked",
];
const cases = {
  rank_order_is_array: Array.isArray(domain.RANK_ORDER),
  rank_order_length_is_twenty_three: domain.RANK_ORDER.length === 23,
  rank_order_first_is_collection:
    domain.RANK_ORDER[0] === "collection",
  rank_order_fifth_is_realm:
    domain.RANK_ORDER[4] === "realm",
  rank_order_sixth_is_kingdom:
    domain.RANK_ORDER[5] === "kingdom",
  rank_order_eighth_is_phylum: domain.RANK_ORDER[7] === "phylum",
  rank_order_ninth_is_subphylum: domain.RANK_ORDER[8] === "subphylum",
  rank_order_last_is_unranked:
    domain.RANK_ORDER[domain.RANK_ORDER.length - 1] === "unranked",
  rank_order_matches_pinned_sequence:
    JSON.stringify([...domain.RANK_ORDER]) === JSON.stringify(expectedRanks),
  // Every rank in the union must round-trip through isValidRank.
  rank_accepts_all_23:
    expectedRanks.every((r) => domain.isValidRank(r) === true),
  rank_accepts_superdomain: domain.isValidRank("superdomain") === true,
  rank_accepts_realm: domain.isValidRank("realm") === true,
  rank_accepts_unranked: domain.isValidRank("unranked") === true,
  rank_rejects_superfamily: domain.isValidRank("superfamily") === false,
  rank_rejects_tribe: domain.isValidRank("tribe") === false,
  rank_rejects_unknown: domain.isValidRank("taxon") === false,
  rank_rejects_empty: domain.isValidRank("") === false,
  rank_rejects_uppercase: domain.isValidRank("KINGDOM") === false,
  rank_rejects_null: domain.isValidRank(null) === false,
  rank_rejects_undefined: domain.isValidRank(undefined) === false,
  rank_rejects_number: domain.isValidRank(0) === false,
  rank_rejects_object: domain.isValidRank({}) === false,
  // isValidTaxon: full + every new rank survives; every rejector fails.
  taxon_accepts_complete: domain.isValidTaxon(validTaxon) === true,
  taxon_accepts_new_ranks:
    newRanks.every((r) =>
      domain.isValidTaxon(Object.assign({}, validTaxon, { rank: r })) === true),
  taxon_accepts_realm:
    domain.isValidTaxon(Object.assign({}, validTaxon, {
      id: 40, name: "Adnaviria", rank: "realm", parent_id: null,
    })) === true,
  taxon_accepts_unranked:
    domain.isValidTaxon(Object.assign({}, validTaxon, {
      id: 41, name: "Viruses", rank: "unranked", parent_id: null,
    })) === true,
  taxon_rejects_missing_parent_id: (() => {
    const { parent_id, ...rest } = validTaxon;
    return domain.isValidTaxon(rest) === false;
  })(),
  taxon_rejects_bad_rank: domain.isValidTaxon(
    Object.assign({}, validTaxon, { rank: "superfamily" })
  ) === false,
  taxon_rejects_string_id: domain.isValidTaxon(
    Object.assign({}, validTaxon, { id: "1" })
  ) === false,
  taxon_rejects_float_id: domain.isValidTaxon(
    Object.assign({}, validTaxon, { id: 1.5 })
  ) === false,
  taxon_rejects_empty_name: domain.isValidTaxon(
    Object.assign({}, validTaxon, { name: "" })
  ) === false,
  taxon_rejects_number_authorship: domain.isValidTaxon(
    Object.assign({}, validTaxon, { authorship: 42 })
  ) === false,
  taxon_rejects_string_parent_id: domain.isValidTaxon(
    Object.assign({}, validTaxon, { parent_id: "x" })
  ) === false,
  taxon_rejects_null: domain.isValidTaxon(null) === false,
  taxon_rejects_string: domain.isValidTaxon("Animalia") === false,
  // ODD-NTP-001 — fully populated Taxon (every legacy tree field)
  // passes validation, with the new integer fields properly typed
  // and the boolean `is_extinct` / `research_path_exists` honored.
  taxon_accepts_full: domain.isValidTaxon(fullTaxon) === true,
  // ODD-NTP-001 — every optional field null survives validation;
  // preserves FastAPI nullability for CoL-only / WoRMS-only /
  // freshwater-only rows.
  taxon_accepts_col_only: domain.isValidTaxon(colOnlyTaxon) === true,
  // ODD-NTP-001 — null is the canonical "not in this source" sentinel
  // for every optional id / parent-id. A null worms_id must NOT be
  // rejected; coercing null to zero would break the source-aware
  // parent chain in web/nav.js (legacy parity oracle).
  taxon_accepts_null_coldp_id: domain.isValidTaxon(
    Object.assign({}, validTaxon, { coldp_id: null })
  ) === true,
  taxon_accepts_null_worms_id: domain.isValidTaxon(
    Object.assign({}, validTaxon, { worms_id: null })
  ) === true,
  taxon_accepts_null_freshwater_id: domain.isValidTaxon(
    Object.assign({}, validTaxon, { freshwater_id: null })
  ) === true,
  taxon_accepts_null_freshwater_parent_id: domain.isValidTaxon(
    Object.assign({}, validTaxon, { freshwater_parent_id: null })
  ) === true,
  taxon_accepts_null_status: domain.isValidTaxon(
    Object.assign({}, validTaxon, { status: null })
  ) === true,
  taxon_accepts_null_is_extinct: domain.isValidTaxon(
    Object.assign({}, validTaxon, { is_extinct: null })
  ) === true,
  taxon_accepts_null_path: domain.isValidTaxon(
    Object.assign({}, validTaxon, { path: null })
  ) === true,
  taxon_accepts_null_species_count: domain.isValidTaxon(
    Object.assign({}, validTaxon, { species_count: null })
  ) === true,
  taxon_accepts_null_research_path_exists: domain.isValidTaxon(
    Object.assign({}, validTaxon, { research_path_exists: null })
  ) === true,
  // ODD-NTP-001 — when an optional wire property IS present, its type
  // must match (no coercion). String ids stay strings; integer ids
  // stay integers; boolean flags stay booleans.
  taxon_rejects_string_worms_id: domain.isValidTaxon(
    Object.assign({}, validTaxon, { worms_id: "42" })
  ) === false,
  taxon_rejects_float_worms_id: domain.isValidTaxon(
    Object.assign({}, validTaxon, { worms_id: 1.5 })
  ) === false,
  taxon_rejects_float_species_count: domain.isValidTaxon(
    Object.assign({}, validTaxon, { species_count: 12.5 })
  ) === false,
  taxon_rejects_string_freshwater_parent_id: domain.isValidTaxon(
    Object.assign({}, validTaxon, { freshwater_parent_id: "x" })
  ) === false,
  taxon_rejects_number_coldp_id: domain.isValidTaxon(
    Object.assign({}, validTaxon, { coldp_id: 42 })
  ) === false,
  taxon_rejects_number_status: domain.isValidTaxon(
    Object.assign({}, validTaxon, { status: 42 })
  ) === false,
  taxon_rejects_string_is_extinct: domain.isValidTaxon(
    Object.assign({}, validTaxon, { is_extinct: "false" })
  ) === false,
  taxon_rejects_string_research_path_exists: domain.isValidTaxon(
    Object.assign({}, validTaxon, { research_path_exists: "true" })
  ) === false,
  taxon_rejects_number_research_path_exists: domain.isValidTaxon(
    Object.assign({}, validTaxon, { research_path_exists: 1 })
  ) === false,
  // ODD-NTP-001 — a missing source id is NOT coerced into another
  // source. `worms_id` left absent while `freshwater_id` is set must
  // still pass (the two are independent; coercion would silently
  // break the source-aware parent chain).
  taxon_accepts_mixed_source_ids: domain.isValidTaxon(
    Object.assign({}, validTaxon, { freshwater_id: 7 })
  ) === true,
  // ODD-NTP-001 (regression — real /source=worms wire shape) — a
  // Taxon matching the live `/api/taxon/{id}/children?source=worms`
  // response (no `worms_parent_id`) must validate. This guards
  // against a future PR that invents a `worms_parent_id` field on
  // the canonical `Taxon` and starts rejecting real wire payloads.
  taxon_accepts_real_worms_wire_shape:
    domain.isValidTaxon(realWormsChildren) === true,
  // ODD-NTP-001 (regression — canonical Taxon has no
  // `worms_parent_id` slot). Adding the field to a record must
  // not change `isValidTaxon`'s verdict, because the canonical
  // projection does not declare the property — the optional
  // "validate only when present" loop is the single validation
  // entry point and it iterates a closed key list. The runtime
  // projection regression (asserting the projected Taxon carries
  // no `worms_parent_id`) lives in the infra harness, where
  // `fromWire` actually runs against a wire payload.
  taxon_accepts_record_with_invented_worms_parent_id: (() => {
    const withInvented = Object.assign({}, validTaxon, { worms_parent_id: 1 });
    return domain.isValidTaxon(withInvented) === true;
  })(),
  // compareRanks: broadest-first contract — synthetic / overlay
  // roots must compare broader than every Linnaean rank.
  compare_kingdom_vs_species_negative:
    domain.compareRanks("kingdom", "species") < 0,
  compare_species_vs_subspecies_negative:
    domain.compareRanks("species", "subspecies") < 0,
  compare_genus_vs_family_positive:
    domain.compareRanks("genus", "family") > 0,
  compare_superdomain_vs_kingdom_negative:
    domain.compareRanks("superdomain", "kingdom") < 0,
  compare_domain_vs_kingdom_negative:
    domain.compareRanks("domain", "kingdom") < 0,
  compare_collection_vs_kingdom_negative:
    domain.compareRanks("collection", "kingdom") < 0,
  // ODD-VTREE-002: realm is broader than kingdom, narrower than superdomain.
  compare_realm_vs_kingdom_negative:
    domain.compareRanks("realm", "kingdom") < 0,
  compare_realm_vs_superdomain_positive:
    domain.compareRanks("realm", "superdomain") > 0,
  compare_realm_vs_form_negative:
    domain.compareRanks("realm", "form") < 0,
  // ODD-VTREE-002: unranked sorts after every named rank (no asserted
  // taxonomic breadth — see RANK_ORDER JSDoc).
  compare_unranked_vs_form_positive:
    domain.compareRanks("unranked", "form") > 0,
  compare_unranked_vs_kingdom_positive:
    domain.compareRanks("unranked", "kingdom") > 0,
  compare_unranked_vs_collection_positive:
    domain.compareRanks("unranked", "collection") > 0,
  compare_phylum_index_is_seven:
    domain.RANK_ORDER.indexOf("phylum") === 7,
  compare_genus_index_is_fifteen:
    domain.RANK_ORDER.indexOf("genus") === 15,
  compare_realm_index_is_four:
    domain.RANK_ORDER.indexOf("realm") === 4,
  compare_unranked_index_is_twenty_two:
    domain.RANK_ORDER.indexOf("unranked") === 22,
  compare_collection_vs_form_negative:
    domain.compareRanks("collection", "form") < 0,
  compare_equal_zero: domain.compareRanks("genus", "genus") === 0,
};
const failed = Object.keys(cases).filter((k) => cases[k] !== true);
if (failed.length > 0) {
  process.stderr.write(
    "FAILED_CASES: " + JSON.stringify(failed) + "\n" +
    "ALL_CASES: " + JSON.stringify(cases) + "\n"
  );
  process.exit(1);
}
process.stdout.write("PASS\n");
"""


@pytest.fixture()
def compiled_domain(tmp_path: Path, require_toolchain: None) -> tuple[Path, Path]:
    """Compile `taxon.ts` to CommonJS in `tmp_path/build/`, write the
    Node harness, return the (compiled-module path, harness path)."""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    result = _run_tsc_isolated(DOMAIN_FILE, out_dir)
    assert result.returncode == 0, (
        f"taxon.ts failed to compile in isolated strict mode.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    compiled = out_dir / "taxon.js"
    assert compiled.is_file(), (
        f"tsc did not emit a compiled module at {compiled}. "
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    harness = tmp_path / "harness.cjs"
    harness.write_text(_HARNESS_SOURCE)
    return compiled, harness


def test_compiled_module_passes_runtime_contract(
    compiled_domain: tuple[Path, Path],
) -> None:
    """Loaded under Node (ES2022 only, no DOM), the compiled module
    returns the correct observable behaviour for every helper —
    catching type errors that become runtime exceptions, shape errors
    that pass strict mode but fail at runtime, and helpers that
    compile cleanly but return the wrong value."""
    compiled, harness = compiled_domain
    result = subprocess.run(
        ["node", str(harness), str(compiled)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"runtime harness failed.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected harness output: {result.stdout!r}"
    )
