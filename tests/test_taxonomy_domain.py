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

# Eight Linnaean ranks, verbatim from design.md §Interfaces/Contracts.
EXPECTED_RANKS: tuple[str, ...] = (
    "kingdom", "phylum", "class", "order",
    "family", "genus", "species", "subspecies",
)

# Pinned Taxon field set, verbatim from design.md §Interfaces/Contracts.
EXPECTED_TAXON_FIELDS: tuple[str, ...] = (
    "id", "name", "rank", "authorship", "parent_id",
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
    silently drops e.g. `parent_id` fails this test before review."""
    if not DOMAIN_FILE.exists():
        pytest.skip("domain file not present yet")
    text = DOMAIN_FILE.read_text()
    for field in EXPECTED_TAXON_FIELDS:
        assert re.search(rf"\b{re.escape(field)}\b\s*:", text), (
            f"taxon.ts is missing required field '{field}' (design.md)."
        )


def test_domain_file_declares_all_eight_ranks() -> None:
    """Each of the eight Linnaean ranks MUST appear as a string
    literal. A future PR that drops e.g. `subspecies` fails here."""
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
# `compareRanks` (the sort-order contract).
_HARNESS_SOURCE = r"""
const path = require("path");
const domain = require(path.resolve(process.argv[2]));
const validTaxon = {
  id: 1, name: "Animalia", rank: "kingdom",
  authorship: null, parent_id: null,
};
const cases = {
  rank_order_is_array: Array.isArray(domain.RANK_ORDER),
  rank_order_length_is_eight: domain.RANK_ORDER.length === 8,
  rank_order_first_is_kingdom: domain.RANK_ORDER[0] === "kingdom",
  rank_order_last_is_subspecies:
    domain.RANK_ORDER[domain.RANK_ORDER.length - 1] === "subspecies",
  rank_order_matches_pinned_sequence:
    JSON.stringify([...domain.RANK_ORDER]) === JSON.stringify([
      "kingdom", "phylum", "class", "order",
      "family", "genus", "species", "subspecies",
    ]),
  rank_accepts_kingdom:    domain.isValidRank("kingdom") === true,
  rank_accepts_phylum:     domain.isValidRank("phylum") === true,
  rank_accepts_class:      domain.isValidRank("class") === true,
  rank_accepts_order:      domain.isValidRank("order") === true,
  rank_accepts_family:     domain.isValidRank("family") === true,
  rank_accepts_genus:      domain.isValidRank("genus") === true,
  rank_accepts_species:    domain.isValidRank("species") === true,
  rank_accepts_subspecies: domain.isValidRank("subspecies") === true,
  rank_rejects_superfamily: domain.isValidRank("superfamily") === false,
  rank_rejects_unknown:     domain.isValidRank("taxon") === false,
  rank_rejects_empty:       domain.isValidRank("") === false,
  rank_rejects_uppercase:   domain.isValidRank("KINGDOM") === false,
  rank_rejects_null:        domain.isValidRank(null) === false,
  rank_rejects_undefined:   domain.isValidRank(undefined) === false,
  rank_rejects_number:      domain.isValidRank(0) === false,
  rank_rejects_object:      domain.isValidRank({}) === false,
  taxon_accepts_complete:   domain.isValidTaxon(validTaxon) === true,
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
  taxon_rejects_null:   domain.isValidTaxon(null) === false,
  taxon_rejects_string: domain.isValidTaxon("Animalia") === false,
  compare_kingdom_vs_species_negative:
    domain.compareRanks("kingdom", "species") < 0,
  compare_species_vs_subspecies_negative:
    domain.compareRanks("species", "subspecies") < 0,
  compare_genus_vs_family_positive:
    domain.compareRanks("genus", "family") > 0,
  compare_equal_zero:
    domain.compareRanks("genus", "genus") === 0,
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
def compiled_domain(tmp_path: Path, require_toolchain: None) -> Path:
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
