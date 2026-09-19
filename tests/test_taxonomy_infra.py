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
    """PR 5a commits to two named exports: `fetchTaxon` and `fetchChildren`. ODD-VTREE-001 adds `fetchDomains`. ODD-TDS-001 adds `fetchSearches`. ODD-TDV-001 adds `fetchVernaculars`. ODD-TDSYN-001 adds `fetchSynonyms`. ODD-TDDIST-001 adds `fetchDistribution`. ODD-TDFOLDER-001 adds `previewMaterialize`, `materializeResearch`, `openFolder`. The barrel re-export breaks on a default export."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    for name in (
        "fetchTaxon", "fetchChildren", "fetchDomains",
        "fetchSearches", "fetchVernaculars", "fetchSynonyms",
        "fetchDistribution",
        "previewMaterialize", "materializeResearch", "openFolder",
    ):
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


def test_infra_file_exports_vernacular_type_and_options() -> None:
    """ODD-TDV-001: the public `VernacularName` type +
    `FetchVernacularsOptions` interface are exported from
    `infra/api.ts` so React callers can type the vernacular-rows
    payload without a deep import. The runtime helper
    `fetchVernaculars` mirrors the byte-identical `id` / `name`
    + nullable `language` + nullable `country` shape of the
    FastAPI `api/server.py::Vernacular` Pydantic model — the ISO
    language / country codes are server-preserved and must NEVER
    be coerced client-side. A future PR that drops either export
    breaks the React cutover's typed VernacularTab wiring.
    """
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    assert re.search(
        r"export\s+interface\s+VernacularName\b",
        text,
    ), "infra/api.ts must export `VernacularName` as a public interface."
    assert re.search(
        r"export\s+interface\s+FetchVernacularsOptions\b",
        text,
    ), "infra/api.ts must export `FetchVernacularsOptions` as a public interface."
    # The VernacularName interface must carry exactly `id` + `name`
    # + nullable `language` + nullable `country` — the FastAPI
    # Pydantic model field set. The `language` and `country`
    # fields MUST be typed `string | null` so the React port can
    # round-trip the server's nullable ISO codes verbatim (a wire
    # `null` projects as `null`, never coerced to empty string or
    # to a different language tag). The legacy
    # `web/detail.js::loadDetail` skips the language / country
    # chip when the row carries `null`, so coercing `null → ""`
    # would silently render an empty chip on every missing field.
    assert re.search(
        r"interface\s+VernacularName\b[^}]*readonly\s+id\s*:\s*number",
        text,
    ), "VernacularName must carry `readonly id: number`."
    assert re.search(
        r"interface\s+VernacularName\b[^}]*readonly\s+name\s*:\s*string",
        text,
    ), "VernacularName must carry `readonly name: string`."
    assert re.search(
        r"interface\s+VernacularName\b[^}]*readonly\s+language\s*:\s*string\s*\|\s*null",
        text,
    ), "VernacularName.language must be typed `string | null` (FastAPI nullability preserved)."
    assert re.search(
        r"interface\s+VernacularName\b[^}]*readonly\s+country\s*:\s*string\s*\|\s*null",
        text,
    ), "VernacularName.country must be typed `string | null` (FastAPI nullability preserved)."
    # The runtime helper must forward `?limit=N` verbatim. The
    # legacy `/api/taxon/{id}/vernaculars?limit=200` request is
    # the byte-identical default; omitting the option keeps the
    # React cutover's request shape aligned with the legacy oracle.
    fetch_block = re.search(
        r"export\s+async\s+function\s+fetchVernaculars\b.*?^}",
        text,
        re.DOTALL | re.MULTILINE,
    )
    assert fetch_block, "infra/api.ts must declare the fetchVernaculars async function."
    assert "limit" in fetch_block.group(0), (
        "fetchVernaculars must read `opts.limit` so React callers can override "
        "the legacy byte-identical `limit=200` default."
    )


def test_infra_file_exports_synonym_type_and_options() -> None:
    """ODD-TDSYN-001: the public `SynonymName` type +
    `FetchSynonymsOptions` interface are exported from
    `infra/api.ts` so React callers can type the synonym-rows
    payload without a deep import. The runtime helper
    `fetchSynonyms` mirrors the FastAPI `api/server.py::Synonym`
    Pydantic model field-for-field: `id`, `rank`,
    `scientific_name`, nullable `authorship`, `status`. The
    server pre-filters to rows where `status != 'accepted'`
    (`api/server.py::get_synonyms`), so `status` is
    server-guaranteed non-null. The React port preserves the
    wire rank / name / authorship / status values verbatim —
    the UI does NOT render the status field (per the
    ODD-TDSYN-001 user constraint) but the projection MUST
    carry it so a future server-composed status-derived
    affordance does not need a coordinated React update.
    """
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    assert re.search(
        r"export\s+interface\s+SynonymName\b",
        text,
    ), "infra/api.ts must export `SynonymName` as a public interface."
    assert re.search(
        r"export\s+interface\s+FetchSynonymsOptions\b",
        text,
    ), "infra/api.ts must export `FetchSynonymsOptions` as a public interface."
    # The SynonymName interface must carry exactly `id` + `rank`
    # + `scientific_name` + nullable `authorship` + `status` —
    # the FastAPI Pydantic model field set. `status` is typed
    # as a non-nullable `string` because the FastAPI SQL
    # pre-filters to rows where `status != 'accepted'`, so the
    # wire never carries `null`. `authorship` is typed as
    # `string | null` so the React port round-trips CoL's
    # nullable authorship verbatim (the legacy
    # `web/detail.js::loadDetail` skips the `.authorship` chip
    # when the row carries `null`, so coercing `null → ""`
    # would silently render an empty span on every missing
    # field).
    assert re.search(
        r"interface\s+SynonymName\b[^}]*readonly\s+id\s*:\s*number",
        text,
    ), "SynonymName must carry `readonly id: number`."
    assert re.search(
        r"interface\s+SynonymName\b[^}]*readonly\s+rank\s*:\s*string",
        text,
    ), "SynonymName must carry `readonly rank: string`."
    assert re.search(
        r"interface\s+SynonymName\b[^}]*readonly\s+scientific_name\s*:\s*string",
        text,
    ), "SynonymName must carry `readonly scientific_name: string` (not 'name')."
    assert re.search(
        r"interface\s+SynonymName\b[^}]*readonly\s+authorship\s*:\s*string\s*\|\s*null",
        text,
    ), "SynonymName.authorship must be typed `string | null` (FastAPI nullability preserved)."
    assert re.search(
        r"interface\s+SynonymName\b[^}]*readonly\s+status\s*:\s*string",
        text,
    ), "SynonymName.status must be typed `string` (non-nullable: server pre-filters status != 'accepted')."
    # The SynonymName projection must NOT carry any invented
    # field beyond the FastAPI wire shape. A canonical
    # SynonymName with extra fields (e.g. `parent_id`,
    # `taxon_id`, `source`, `is_ambiguous`) would leak server
    # composition concerns into the client contract and let
    # future drift slip past the projection layer.
    syn_block = re.search(
        r"interface\s+SynonymName\b[^}]*\}",
        text,
        re.DOTALL,
    )
    assert syn_block, "SynonymName interface must be syntactically well-formed."
    props = re.findall(r"readonly\s+(\w+)\s*:", syn_block.group(0))
    assert sorted(props) == sorted(["id", "rank", "scientific_name", "authorship", "status"]), (
        "ODD-TDSYN-001: canonical SynonymName must carry exactly "
        "{id, rank, scientific_name, authorship, status}; got " + str(props)
    )
    # The runtime helper must forward `?limit=N` verbatim. The
    # legacy `/api/taxon/{id}/synonyms?limit=200` request is
    # the byte-identical default; omitting the option keeps the
    # React cutover's request shape aligned with the legacy
    # oracle.
    fetch_block = re.search(
        r"export\s+async\s+function\s+fetchSynonyms\b.*?^}",
        text,
        re.DOTALL | re.MULTILINE,
    )
    assert fetch_block, "infra/api.ts must declare the fetchSynonyms async function."
    assert "limit" in fetch_block.group(0), (
        "fetchSynonyms must read `opts.limit` so React callers can override "
        "the legacy byte-identical `limit=200` default."
    )


def test_infra_file_exports_folder_types_and_options() -> None:
    """ODD-TDFOLDER-001: the public `MaterializePreview`,
    `MaterializePreviewSegment`, `MaterializeResult`,
    `OpenFolderResult` types + the
    `FetchMaterializePreviewOptions`, `FetchMaterializeOptions`,
    `FetchOpenFolderOptions` interfaces are exported from
    `infra/api.ts` so React callers can type the preview /
    materialize / open-folder payloads without a deep import.
    The runtime helpers `previewMaterialize` (GET),
    `materializeResearch` (POST), `openFolder` (POST) mirror
    the FastAPI `api/server.py::materialize_research_folder_preview`,
    `::materialize_research_folder`, `::open_research_folder`
    endpoints byte-for-byte: the cumulative `research_dir` /
    `relative_path` / `absolute_path` fields are server-composed
    and must NEVER be joined / sanitised client-side, and the
    runtime helpers use POST explicitly for the two
    side-effecting endpoints (mkdir + subprocess.Popen).
    A future PR that drops any export breaks the React cutover's
    typed FolderTab wiring."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    for name in (
        "MaterializePreview",
        "MaterializePreviewSegment",
        "MaterializeResult",
        "OpenFolderResult",
        "FetchMaterializePreviewOptions",
        "FetchMaterializeOptions",
        "FetchOpenFolderOptions",
    ):
        pattern = rf"export\s+(?:interface|type)\s+{name}\b"
        assert re.search(pattern, text), (
            f"infra/api.ts must export `{name}` as a public interface/type."
        )
    # The MaterializePreviewSegment interface must carry exactly
    # `name` + `exists` + `is_dir` + `is_new` — the FastAPI wire
    # shape. A future PR that adds a client-side `cumulative` or
    # `marker` field would leak server-composed concerns into
    # the client contract (the server already composes the
    # cumulative path on `relative_path` + `absolute_path`).
    assert re.search(
        r"interface\s+MaterializePreviewSegment\b[^}]*readonly\s+name\s*:\s*string",
        text,
    ), "MaterializePreviewSegment must carry `readonly name: string`."
    assert re.search(
        r"interface\s+MaterializePreviewSegment\b[^}]*readonly\s+exists\s*:\s*boolean",
        text,
    ), "MaterializePreviewSegment must carry `readonly exists: boolean`."
    assert re.search(
        r"interface\s+MaterializePreviewSegment\b[^}]*readonly\s+is_dir\s*:\s*boolean",
        text,
    ), "MaterializePreviewSegment must carry `readonly is_dir: boolean`."
    assert re.search(
        r"interface\s+MaterializePreviewSegment\b[^}]*readonly\s+is_new\s*:\s*boolean",
        text,
    ), "MaterializePreviewSegment must carry `readonly is_new: boolean`."
    seg_block = re.search(
        r"interface\s+MaterializePreviewSegment\b[^}]*\}",
        text,
        re.DOTALL,
    )
    assert seg_block, "MaterializePreviewSegment interface must be syntactically well-formed."
    seg_props = re.findall(r"readonly\s+(\w+)\s*:", seg_block.group(0))
    assert sorted(seg_props) == sorted(["name", "exists", "is_dir", "is_new"]), (
        "ODD-TDFOLDER-001: canonical MaterializePreviewSegment must carry exactly "
        "{name, exists, is_dir, is_new}; got " + str(seg_props)
    )
    # The MaterializePreview interface must carry every
    # server-returned field verbatim. The structural regression
    # blocks any invented field beyond the FastAPI wire shape.
    preview_block = re.search(
        r"interface\s+MaterializePreview\b[^}]*\}",
        text,
        re.DOTALL,
    )
    assert preview_block, "MaterializePreview interface must be syntactically well-formed."
    preview_props = re.findall(r"readonly\s+(\w+)\s*:", preview_block.group(0))
    assert sorted(preview_props) == sorted([
        "ok", "taxon_id", "scientific_name", "research_dir",
        "relative_path", "absolute_path", "segments",
        "new_count", "existing_count", "all_exist",
    ]), (
        "ODD-TDFOLDER-001: canonical MaterializePreview must carry exactly "
        "{ok, taxon_id, scientific_name, research_dir, relative_path, "
        "absolute_path, segments, new_count, existing_count, all_exist}; got "
        + str(preview_props)
    )
    # The MaterializeResult interface must carry exactly
    # `ok` + `absolute_path` + `relative_path` + `folders_created`
    # + `folders_existed` + `segments`. The segments field is
    # `readonly string[]` (NOT the per-segment object shape used
    # by the preview endpoint).
    mat_block = re.search(
        r"interface\s+MaterializeResult\b[^}]*\}",
        text,
        re.DOTALL,
    )
    assert mat_block, "MaterializeResult interface must be syntactically well-formed."
    mat_props = re.findall(r"readonly\s+(\w+)\s*:", mat_block.group(0))
    assert sorted(mat_props) == sorted([
        "ok", "absolute_path", "relative_path",
        "folders_created", "folders_existed", "segments",
    ]), (
        "ODD-TDFOLDER-001: canonical MaterializeResult must carry exactly "
        "{ok, absolute_path, relative_path, folders_created, "
        "folders_existed, segments}; got " + str(mat_props)
    )
    # The OpenFolderResult interface must carry exactly
    # `ok` + `absolute_path` + `relative_path` + `opened_with`.
    # The `opened_with` field is the OS-binary name the server
    # actually invoked.
    open_block = re.search(
        r"interface\s+OpenFolderResult\b[^}]*\}",
        text,
        re.DOTALL,
    )
    assert open_block, "OpenFolderResult interface must be syntactically well-formed."
    open_props = re.findall(r"readonly\s+(\w+)\s*:", open_block.group(0))
    assert sorted(open_props) == sorted([
        "ok", "absolute_path", "relative_path", "opened_with",
    ]), (
        "ODD-TDFOLDER-001: canonical OpenFolderResult must carry exactly "
        "{ok, absolute_path, relative_path, opened_with}; got " + str(open_props)
    )
    # The `previewMaterialize` runtime helper MUST use GET (no
    # `method: "POST"` init). The `materializeResearch` and
    # `openFolder` helpers MUST use POST explicitly — the two
    # side-effecting endpoints (mkdir + subprocess.Popen) need
    # to advertise their filesystem impact.
    for fn_name, expected_method in (
        ("previewMaterialize", None),
        ("materializeResearch", "POST"),
        ("openFolder", "POST"),
    ):
        fetch_block = re.search(
            rf"export\s+async\s+function\s+{fn_name}\b.*?^}}",
            text,
            re.DOTALL | re.MULTILINE,
        )
        assert fetch_block, f"infra/api.ts must declare the {fn_name} async function."
        body = fetch_block.group(0)
        if expected_method is None:
            assert 'method: "POST"' not in body and "method: 'POST'" not in body, (
                f"{fn_name} must NOT use POST (the preview is informational — no side "
                f"effects on the server filesystem)."
            )
        else:
            assert (
                f'method: "{expected_method}"' in body
                or f"method: '{expected_method}'" in body
            ), (
                f"{fn_name} must use {expected_method} (the endpoint mutates the "
                f"filesystem / spawns the OS file manager)."
            )


def test_infra_file_exports_distribution_type_and_options() -> None:
    """ODD-TDDIST-001: the public `DistributionEntry` type +
    `FetchDistributionOptions` interface are exported from
    `infra/api.ts` so React callers can type the distribution-rows
    payload without a deep import. The runtime helper
    `fetchDistribution` mirrors the FastAPI
    `api/server.py::DistributionEntry` Pydantic model field-for-
    field: `id`, `area`, nullable `gazetteer`, nullable
    `establishment_means`, nullable `degree_of_establishment`. The
    React port preserves the wire values verbatim (the UI only
    renders `establishment_means` + `area` per the ODD-TDDIST-001
    user constraint: "do not render gazetteer/degree or
    group/filter/sort") but the projection MUST carry every wire
    field so a future server-composed gazetteer tooltip or
    degree-derived affordance does not need a coordinated React
    update — mirroring how `SynonymName.status` survives even
    though `SynonymTab` does not render it (ODD-TDSYN-001).
    """
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    assert re.search(
        r"export\s+interface\s+DistributionEntry\b",
        text,
    ), "infra/api.ts must export `DistributionEntry` as a public interface."
    assert re.search(
        r"export\s+interface\s+FetchDistributionOptions\b",
        text,
    ), "infra/api.ts must export `FetchDistributionOptions` as a public interface."
    # The DistributionEntry interface must carry exactly `id` +
    # `area` + nullable `gazetteer` + nullable `establishment_means`
    # + nullable `degree_of_establishment` — the FastAPI Pydantic
    # model field set. `area` is server-guaranteed non-null +
    # non-empty (CoL NOT NULL constraint + the SQL pre-filters to
    # rows where `area IS NOT NULL AND area != ''`). The three
    # nullable fields MUST be typed `string | null` so the React
    # port round-trips CoL's nullable columns verbatim (the legacy
    # `web/detail.js::loadDetail` skips the chip when the row
    # carries `null`, so coercing `null → ""` would silently
    # render an empty chip on every missing field).
    assert re.search(
        r"interface\s+DistributionEntry\b[^}]*readonly\s+id\s*:\s*number",
        text,
    ), "DistributionEntry must carry `readonly id: number`."
    assert re.search(
        r"interface\s+DistributionEntry\b[^}]*readonly\s+area\s*:\s*string",
        text,
    ), "DistributionEntry must carry `readonly area: string`."
    assert re.search(
        r"interface\s+DistributionEntry\b[^}]*readonly\s+gazetteer\s*:\s*string\s*\|\s*null",
        text,
    ), "DistributionEntry.gazetteer must be typed `string | null` (FastAPI nullability preserved)."
    assert re.search(
        r"interface\s+DistributionEntry\b[^}]*readonly\s+establishment_means\s*:\s*string\s*\|\s*null",
        text,
    ), "DistributionEntry.establishment_means must be typed `string | null` (FastAPI nullability preserved)."
    assert re.search(
        r"interface\s+DistributionEntry\b[^}]*readonly\s+degree_of_establishment\s*:\s*string\s*\|\s*null",
        text,
    ), "DistributionEntry.degree_of_establishment must be typed `string | null` (FastAPI nullability preserved)."
    # The DistributionEntry projection must NOT carry any invented
    # field beyond the FastAPI wire shape. A canonical
    # DistributionEntry with extra fields (e.g. `taxon_id`,
    # `source`, `is_introduced`) would leak server composition
    # concerns into the client contract and let future drift slip
    # past the projection layer.
    dist_block = re.search(
        r"interface\s+DistributionEntry\b[^}]*\}",
        text,
        re.DOTALL,
    )
    assert dist_block, "DistributionEntry interface must be syntactically well-formed."
    props = re.findall(r"readonly\s+(\w+)\s*:", dist_block.group(0))
    assert sorted(props) == sorted([
        "id", "area", "gazetteer", "establishment_means", "degree_of_establishment",
    ]), (
        "ODD-TDDIST-001: canonical DistributionEntry must carry exactly "
        "{id, area, gazetteer, establishment_means, degree_of_establishment}; got " + str(props)
    )
    # The runtime helper must forward `?limit=N` verbatim. The
    # legacy `/api/taxon/{id}/distribution?limit=200` request is
    # the byte-identical default; omitting the option keeps the
    # React cutover's request shape aligned with the legacy oracle.
    fetch_block = re.search(
        r"export\s+async\s+function\s+fetchDistribution\b.*?^}",
        text,
        re.DOTALL | re.MULTILINE,
    )
    assert fetch_block, "infra/api.ts must declare the fetchDistribution async function."
    assert "limit" in fetch_block.group(0), (
        "fetchDistribution must read `opts.limit` so React callers can override "
        "the legacy byte-identical `limit=200` default."
    )


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

  // ---- ODD-TDV-001 — fetchVernaculars wire → domain projection ----
  // The server returns a JSON array of `Vernacular` records
  // (`id`, `name`, nullable `language`, nullable `country`). The
  // legacy `web/detail.js::loadDetail` fetches
  // `/api/taxon/{id}/vernaculars?limit=200` and reads the raw rows
  // into `buildDetailSection`; the React port's runtime helper
  // projects the same wire shape through the canonical
  // `VernacularName` interface so the byte-identical visual
  // rendering (`.lang` + `.country` chips + name span) survives
  // the cutover. The runtime check below pins every contract in
  // one assertion block.
  const VFresh = makeFetch([
    { ok: true, status: 200, statusText: "OK", json: [
      // CoL Homo sapiens fixture: full language + country + name.
      { id: 1, name: "Human", language: "EN", country: "US" },
      // Latin canonical row: language + country both null (the
      // server preserves FastAPI nullability — the React port must
      // surface `null`, never coerce to "" or to a default tag).
      { id: 2, name: "Homo", language: null, country: null },
      // Mixed-language row: language present, country missing.
      // The chip rendering branches on each field's nullability
      // independently so the country chip is omitted but the
      // language chip survives.
      { id: 3, name: "Mensch", language: "DE", country: null },
      // Country-only row: language missing (uncommon but legal
      // wire shape), country present.
      { id: 4, name: "Ser humano", language: null, country: "BR" },
      // Long-form ISO code: 3-letter language tag + 2-letter
      // country code — the canonical FastAPI shape preserves
      // them verbatim (the React port paints them through the
      // `.lang` + `.country` chips byte-identically).
      { id: 5, name: "Be\u0259\u0268\u0259\u01b9 nax\u0259\u0288", language: "AZE", country: "AZ" },
    ] },
  ]);
  const v = await api.fetchVernaculars(100, { fetch: VFresh, baseUrl: "http://x" });
  assert.strictEqual(VFresh.calls.length, 1);
  assert.strictEqual(VFresh.calls[0].input, "http://x/api/taxon/100/vernaculars?limit=200",
    "fetchVernaculars must build the canonical legacy /api/taxon/{id}/vernaculars?limit=200 URL by default");
  assert.strictEqual(Array.isArray(v), true, "fetchVernaculars must return an array");
  assert.strictEqual(v.length, 5,
    "fetchVernaculars must surface every server-returned VernacularName row");
  // FastAPI nullability must round-trip verbatim. The legacy
  // `web/detail.js::loadDetail` skips the language chip when
  // `v.language` is falsy, so coercing `null → ""` would silently
  // render an empty chip on every missing field. The runtime
  // check pins every nullable shape below.
  assert.strictEqual(v[0].id, 1);
  assert.strictEqual(v[0].name, "Human");
  assert.strictEqual(v[0].language, "EN");
  assert.strictEqual(v[0].country, "US");
  assert.strictEqual(v[1].name, "Homo");
  assert.strictEqual(v[1].language, null,
    "ODD-TDV-001: FastAPI nullability must round-trip verbatim (language=null stays null)");
  assert.strictEqual(v[1].country, null,
    "ODD-TDV-001: FastAPI nullability must round-trip verbatim (country=null stays null)");
  assert.strictEqual(v[2].name, "Mensch");
  assert.strictEqual(v[2].language, "DE");
  assert.strictEqual(v[2].country, null);
  assert.strictEqual(v[3].name, "Ser humano");
  assert.strictEqual(v[3].language, null);
  assert.strictEqual(v[3].country, "BR");
  // ISO code preservation — non-ASCII name + 3-letter language
  // code + 2-letter country code must all reach the client
  // untouched.
  assert.strictEqual(v[4].name, "Be\u0259\u0268\u0259\u01b9 nax\u0259\u0288");
  assert.strictEqual(v[4].language, "AZE");
  assert.strictEqual(v[4].country, "AZ");
  // The VernacularName projection must NOT carry any invented
  // field. The server payload has only `id` + `name` + nullable
  // `language` + nullable `country`; a canonical VernacularName
  // with extra fields (e.g. `rank`, `taxon_id`, `source`) would
  // leak server composition concerns into the client contract
  // and let future drift slip past the projection layer.
  for (const n of v) {
    const props = Object.keys(n).sort();
    assert.deepStrictEqual(props, ["country", "id", "language", "name"],
      "ODD-TDV-001: canonical VernacularName must carry exactly "
      + "{id, name, language, country}; got " + JSON.stringify(props));
  }

  // fetchVernaculars ?limit= override — query forwarded verbatim.
  const VLim50 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchVernaculars(100, { fetch: VLim50, baseUrl: "http://x", limit: 50 });
  assert.strictEqual(VLim50.calls[0].input, "http://x/api/taxon/100/vernaculars?limit=50",
    "fetchVernaculars must forward opts.limit verbatim: " + VLim50.calls[0].input);
  const VLim500 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchVernaculars(100, { fetch: VLim500, baseUrl: "http://x", limit: 500 });
  assert.strictEqual(VLim500.calls[0].input, "http://x/api/taxon/100/vernaculars?limit=500",
    "fetchVernaculars must forward opts.limit=500 verbatim");

  // fetchVernaculars empty payload — returns [], does not throw.
  const VEmpty = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  assert.strictEqual((await api.fetchVernaculars(100, { fetch: VEmpty, baseUrl: "http://x" })).length, 0);

  // fetchVernaculars HTTP non-OK — status code in message.
  const VBad = makeFetch([{ ok: false, status: 503, statusText: "Service Unavailable", json: { detail: "DB down" } }]);
  await assert.rejects(
    () => api.fetchVernaculars(100, { fetch: VBad, baseUrl: "http://x" }),
    (err) => /503/.test(String(err && err.message || err)),
    "fetchVernaculars must reject on non-OK with the status code in the message",
  );

  // fetchVernaculars non-array payload — rejects.
  const VWrongShape = makeFetch([{ ok: true, status: 200, statusText: "OK", json: { detail: "wrong shape" } }]);
  await assert.rejects(
    () => api.fetchVernaculars(100, { fetch: VWrongShape, baseUrl: "http://x" }),
    (err) => /non-array/.test(String(err && err.message || err)),
    "fetchVernaculars must reject non-array payloads",
  );

  // fetchVernaculars schema-invalid element — rejects.
  const VBadElement = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, name: "Human" /* language + country missing */ }] }]);
  await assert.rejects(
    () => api.fetchVernaculars(100, { fetch: VBadElement, baseUrl: "http://x" }),
    (err) => /invalid|vernacular/i.test(String(err && err.message || err)),
    "fetchVernaculars must reject per-element shape mismatches (missing nullable fields as undefined)",
  );

  // fetchVernaculars wrong type on nullable field — rejects.
  const VBadLanguageType = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, name: "Human", language: 123, country: null }] }]);
  await assert.rejects(
    () => api.fetchVernaculars(100, { fetch: VBadLanguageType, baseUrl: "http://x" }),
    (err) => /invalid|vernacular/i.test(String(err && err.message || err)),
    "fetchVernaculars must reject non-string language values",
  );

  // fetchVernaculars wrong type on name (number instead of string) — rejects.
  const VBadNameType = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, name: 42, language: null, country: null }] }]);
  await assert.rejects(
    () => api.fetchVernaculars(100, { fetch: VBadNameType, baseUrl: "http://x" }),
    (err) => /invalid|vernacular/i.test(String(err && err.message || err)),
    "fetchVernaculars must reject non-string name values",
  );

  // fetchVernaculars empty name — rejects (the legacy
  // `web/detail.js::loadDetail` would not produce an empty name
  // because CoL rows have a NOT NULL constraint, but the React
  // projection must still reject the wire shape so a future
  // server change cannot silently bypass the validation).
  const VEmptyName = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, name: "", language: null, country: null }] }]);
  await assert.rejects(
    () => api.fetchVernaculars(100, { fetch: VEmptyName, baseUrl: "http://x" }),
    (err) => /invalid|vernacular/i.test(String(err && err.message || err)),
    "fetchVernaculars must reject empty name values",
  );

  // fetchVernaculars negative id — id validation rejects.
  await assert.rejects(
    () => api.fetchVernaculars(-1, { fetch: makeFetch([]), baseUrl: "http://x" }),
    (err) => /non-negative integer/i.test(String(err && err.message || err)),
    "fetchVernaculars must reject negative ids",
  );

  // fetchVernaculars non-integer id — id validation rejects.
  await assert.rejects(
    () => api.fetchVernaculars(1.5, { fetch: makeFetch([]), baseUrl: "http://x" }),
    (err) => /non-negative integer/i.test(String(err && err.message || err)),
    "fetchVernaculars must reject non-integer ids",
  );

  // fetchVernaculars malformed JSON — throws.
  const VJsonFail = makeFetch([{ ok: true, status: 200, statusText: "OK", json: Promise.reject(new SyntaxError("Unexpected token < in JSON")) }]);
  await assert.rejects(
    () => api.fetchVernaculars(100, { fetch: VJsonFail, baseUrl: "http://x" }),
    (err) => /json|JSON/i.test(String(err && err.message || err)),
    "fetchVernaculars must reject malformed JSON",
  );

  // ---- ODD-TDSYN-001 — fetchSynonyms wire → domain projection ----
  // The server returns a JSON array of `Synonym` records
  // (`id`, `rank`, `scientific_name`, nullable `authorship`,
  // non-nullable `status`). The SQL pre-filters to rows where
  // `status != 'accepted'` so the wire payload never carries a
  // null status. The legacy `web/detail.js::loadDetail` fetches
  // `/api/taxon/{id}/synonyms?limit=200` and feeds the raw
  // rows into `buildDetailSection`; the React port's runtime
  // helper projects the same wire shape through the canonical
  // `SynonymName` interface so the byte-identical visual
  // rendering (rank chip + scientific name + optional
  // `.authorship` span) survives the cutover. The runtime
  // check below pins every contract in one assertion block.
  const SynFresh = makeFetch([
    { ok: true, status: 200, statusText: "OK", json: [
      // Accepted-rank row + full authorship — genus synonym with
      // a parenthetical author. The React port renders this as
      // a `.detail-item` carrying the `.rank-chip` chip with
      // "genus", the italic scientific name, and the `.authorship`
      // span.
      { id: 9001, rank: "genus", scientific_name: "Palaeocop",
        authorship: "Huxley, 1880", status: "synonym" },
      // Subgenus row without authorship — the `.authorship`
      // span is conditionally omitted (the UI must NOT render
      // an empty chip when the nullable field is null).
      { id: 9002, rank: "subgenus", scientific_name: "Neocop",
        authorship: null, status: "synonym" },
      // Higher-rank synonym — CoL species-level synonym with
      // a non-italic (roman) scientific name + the typical
      // "misapplied" status string the FastAPI Pydantic model
      // enumerates (`synonym`, `ambiguous synonym`, `misapplied`).
      { id: 9003, rank: "species", scientific_name: "Acipenser baeri",
        authorship: "Linnaeus, 1758", status: "ambiguous synonym" },
      // Family-level synonym — proves the wire ordering
      // (`ORDER BY rank, scientific_name`) reaches the React
      // port verbatim (the UI must NOT sort client-side).
      { id: 9004, rank: "family", scientific_name: "Palaeocopidae",
        authorship: null, status: "synonym" },
      // Unicode authorship — non-ASCII character must round-trip
      // verbatim (the legacy `web/detail.js::loadDetail` reads
      // `s.authorship` straight through).
      { id: 9005, rank: "subspecies", scientific_name: "Acipenser baerii baicalensis",
        authorship: "Georgi, 1775", status: "synonym" },
    ] },
  ]);
  const syn = await api.fetchSynonyms(100, { fetch: SynFresh, baseUrl: "http://x" });
  assert.strictEqual(SynFresh.calls.length, 1);
  assert.strictEqual(SynFresh.calls[0].input, "http://x/api/taxon/100/synonyms?limit=200",
    "fetchSynonyms must build the canonical legacy /api/taxon/{id}/synonyms?limit=200 URL by default");
  assert.strictEqual(Array.isArray(syn), true, "fetchSynonyms must return an array");
  assert.strictEqual(syn.length, 5,
    "fetchSynonyms must surface every server-returned SynonymName row");
  // Wire ordering preservation — the server returns rows
  // sorted by `rank, scientific_name` and the React port
  // preserves the order verbatim (the UI must NOT sort
  // client-side per the ODD-TDSYN-001 user constraint).
  assert.strictEqual(syn[0].id, 9001);
  assert.strictEqual(syn[0].rank, "genus");
  assert.strictEqual(syn[0].scientific_name, "Palaeocop");
  assert.strictEqual(syn[0].authorship, "Huxley, 1880");
  assert.strictEqual(syn[0].status, "synonym");
  // Nullable authorship must round-trip verbatim (the
  // legacy `web/detail.js::loadDetail` skips the
  // `.authorship` span when `s.authorship` is falsy, so
  // coercing `null → ""` would silently render an empty span
  // on every missing field).
  assert.strictEqual(syn[1].id, 9002);
  assert.strictEqual(syn[1].rank, "subgenus");
  assert.strictEqual(syn[1].scientific_name, "Neocop");
  assert.strictEqual(syn[1].authorship, null,
    "ODD-TDSYN-001: FastAPI nullability must round-trip verbatim (authorship=null stays null)");
  assert.strictEqual(syn[1].status, "synonym");
  // The non-default `status` values ("ambiguous synonym",
  // "misapplied") must surface verbatim — the server may
  // return any non-accepted status string the SQL captures.
  assert.strictEqual(syn[2].id, 9003);
  assert.strictEqual(syn[2].status, "ambiguous synonym",
    "ODD-TDSYN-001: status='ambiguous synonym' must round-trip verbatim");
  assert.strictEqual(syn[3].rank, "family",
    "ODD-TDSYN-001: server-ordered row (family) must surface in the order the wire returned it");
  // Non-ASCII characters in the authorship field must
  // round-trip verbatim — the legacy `web/detail.js::loadDetail`
  // reads the raw rows, so the React port must not decode /
  // re-encode the string.
  assert.strictEqual(syn[4].authorship, "Georgi, 1775");
  // The SynonymName projection must NOT carry any invented
  // field beyond the FastAPI wire shape.
  for (const n of syn) {
    const props = Object.keys(n).sort();
    assert.deepStrictEqual(props, ["authorship", "id", "rank", "scientific_name", "status"],
      "ODD-TDSYN-001: canonical SynonymName must carry exactly "
      + "{id, rank, scientific_name, authorship, status}; got " + JSON.stringify(props));
  }

  // fetchSynonyms ?limit= override — query forwarded verbatim.
  const SynLim50 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchSynonyms(100, { fetch: SynLim50, baseUrl: "http://x", limit: 50 });
  assert.strictEqual(SynLim50.calls[0].input, "http://x/api/taxon/100/synonyms?limit=50",
    "fetchSynonyms must forward opts.limit verbatim: " + SynLim50.calls[0].input);
  const SynLim1000 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchSynonyms(100, { fetch: SynLim1000, baseUrl: "http://x", limit: 1000 });
  assert.strictEqual(SynLim1000.calls[0].input, "http://x/api/taxon/100/synonyms?limit=1000",
    "fetchSynonyms must forward opts.limit=1000 verbatim");

  // fetchSynonyms empty payload — returns [], does not throw.
  const SynEmpty = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  assert.strictEqual((await api.fetchSynonyms(100, { fetch: SynEmpty, baseUrl: "http://x" })).length, 0);

  // fetchSynonyms HTTP non-OK — status code in message.
  const SynBad = makeFetch([{ ok: false, status: 503, statusText: "Service Unavailable", json: { detail: "DB down" } }]);
  await assert.rejects(
    () => api.fetchSynonyms(100, { fetch: SynBad, baseUrl: "http://x" }),
    (err) => /503/.test(String(err && err.message || err)),
    "fetchSynonyms must reject on non-OK with the status code in the message",
  );

  // fetchSynonyms non-array payload — rejects.
  const SynWrongShape = makeFetch([{ ok: true, status: 200, statusText: "OK", json: { detail: "wrong shape" } }]);
  await assert.rejects(
    () => api.fetchSynonyms(100, { fetch: SynWrongShape, baseUrl: "http://x" }),
    (err) => /non-array/.test(String(err && err.message || err)),
    "fetchSynonyms must reject non-array payloads",
  );

  // fetchSynonyms schema-invalid element — rejects.
  const SynBadElement = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, rank: "genus", scientific_name: "Palaeocop" /* authorship + status missing */ }] }]);
  await assert.rejects(
    () => api.fetchSynonyms(100, { fetch: SynBadElement, baseUrl: "http://x" }),
    (err) => /invalid|synonym/i.test(String(err && err.message || err)),
    "fetchSynonyms must reject per-element shape mismatches (missing authorship + status)",
  );

  // fetchSynonyms wrong type on nullable field — rejects.
  const SynBadAuthorshipType = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, rank: "genus", scientific_name: "Palaeocop",
             authorship: 42, status: "synonym" }] }]);
  await assert.rejects(
    () => api.fetchSynonyms(100, { fetch: SynBadAuthorshipType, baseUrl: "http://x" }),
    (err) => /invalid|synonym/i.test(String(err && err.message || err)),
    "fetchSynonyms must reject non-string authorship values",
  );

  // fetchSynonyms wrong type on status (number instead of string) — rejects.
  // The server pre-filters to rows where `status != 'accepted'`,
  // so the wire never carries a null status. The runtime check
  // pins the non-nullable contract on the client projection.
  const SynBadStatusType = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, rank: "genus", scientific_name: "Palaeocop",
             authorship: null, status: null }] }]);
  await assert.rejects(
    () => api.fetchSynonyms(100, { fetch: SynBadStatusType, baseUrl: "http://x" }),
    (err) => /invalid|synonym/i.test(String(err && err.message || err)),
    "fetchSynonyms must reject null status values (server pre-filters status != 'accepted')",
  );

  // fetchSynonyms empty scientific_name — rejects (the legacy
  // `web/detail.js::loadDetail` would not produce an empty
  // scientific_name because CoL rows have a NOT NULL constraint,
  // but the React projection must still reject the wire shape
  // so a future server change cannot silently bypass the
  // validation).
  const SynEmptyName = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, rank: "genus", scientific_name: "",
             authorship: null, status: "synonym" }] }]);
  await assert.rejects(
    () => api.fetchSynonyms(100, { fetch: SynEmptyName, baseUrl: "http://x" }),
    (err) => /invalid|synonym/i.test(String(err && err.message || err)),
    "fetchSynonyms must reject empty scientific_name values",
  );

  // fetchSynonyms empty rank — rejects.
  const SynEmptyRank = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, rank: "", scientific_name: "Palaeocop",
             authorship: null, status: "synonym" }] }]);
  await assert.rejects(
    () => api.fetchSynonyms(100, { fetch: SynEmptyRank, baseUrl: "http://x" }),
    (err) => /invalid|synonym/i.test(String(err && err.message || err)),
    "fetchSynonyms must reject empty rank values",
  );

  // fetchSynonyms empty status — rejects (the server
  // pre-filter requires non-accepted rows, so the wire never
  // carries an empty status string).
  const SynEmptyStatus = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, rank: "genus", scientific_name: "Palaeocop",
             authorship: null, status: "" }] }]);
  await assert.rejects(
    () => api.fetchSynonyms(100, { fetch: SynEmptyStatus, baseUrl: "http://x" }),
    (err) => /invalid|synonym/i.test(String(err && err.message || err)),
    "fetchSynonyms must reject empty status values",
  );

  // fetchSynonyms negative id — id validation rejects.
  await assert.rejects(
    () => api.fetchSynonyms(-1, { fetch: makeFetch([]), baseUrl: "http://x" }),
    (err) => /non-negative integer/i.test(String(err && err.message || err)),
    "fetchSynonyms must reject negative ids",
  );

  // fetchSynonyms non-integer id — id validation rejects.
  await assert.rejects(
    () => api.fetchSynonyms(1.5, { fetch: makeFetch([]), baseUrl: "http://x" }),
    (err) => /non-negative integer/i.test(String(err && err.message || err)),
    "fetchSynonyms must reject non-integer ids",
  );

  // fetchSynonyms malformed JSON — throws.
  const SynJsonFail = makeFetch([{ ok: true, status: 200, statusText: "OK", json: Promise.reject(new SyntaxError("Unexpected token < in JSON")) }]);
  await assert.rejects(
    () => api.fetchSynonyms(100, { fetch: SynJsonFail, baseUrl: "http://x" }),
    (err) => /json|JSON/i.test(String(err && err.message || err)),
    "fetchSynonyms must reject malformed JSON",
  );

  // ---- ODD-TDDIST-001 — fetchDistribution wire → domain projection ----
  // The server returns a JSON array of `DistributionEntry` records
  // (`id`, `area`, nullable `gazetteer`, nullable
  // `establishment_means`, nullable `degree_of_establishment`). The
  // legacy `web/detail.js::loadDetail` fetches
  // `/api/taxon/{id}/distribution?limit=200` and feeds the raw
  // rows into `buildDetailSection`; the React port's runtime
  // helper projects the same wire shape through the canonical
  // `DistributionEntry` interface so the byte-identical visual
  // rendering (establishment-means chip + area text) survives
  // the cutover. The runtime check below pins every contract
  // in one assertion block.
  const DistFresh = makeFetch([
    { ok: true, status: 200, statusText: "OK", json: [
      // Native row — all wire fields populated with the legacy
      // CoL verbatim values. The React port renders this as a
      // `.detail-item` carrying the `.means-native` chip + the
      // area text. The `gazetteer` + `degree_of_establishment`
      // fields are preserved verbatim on the projection surface
      // (the UI does NOT render them per the ODD-TDDIST-001
      // user constraint) so a future server-composed
      // gazetteer tooltip can land without a coordinated React
      // update.
      { id: 7001, area: "Argentina",
        gazetteer: "TDWG Level 4", establishment_means: "native",
        degree_of_establishment: "native" },
      // Introduced row — the chip rendering branches on the
      // `.means-introduced` modifier class via the wire
      // `establishment_means` value.
      { id: 7002, area: "USA (California)",
        gazetteer: "TDWG Level 4", establishment_means: "introduced",
        degree_of_establishment: "introduced" },
      // Uncertain row — all three nullable fields populated
      // with their canonical CoL string values.
      { id: 7003, area: "South America",
        gazetteer: "TDWG Level 2", establishment_means: "uncertain",
        degree_of_establishment: null },
      // Null establishment_means row — exercises the
      // ODD-TDDIST-001 client fallback `unknown` (the legacy
      // `web/detail.js::buildDetailSection` uses
      // `x.establishment_means || "unknown"` so a wire `null`
      // paints the `.means-unknown` chip). The
      // canonical projection MUST keep `null` (never coerced
      // to `""` or to the literal `unknown`) so the React
      // port's renderer applies the fallback at render time
      // only — mirroring how `VernacularName.language: null`
      // stays `null` and the chip is omitted at the renderer
      // (ODD-TDV-001).
      { id: 7004, area: "Brazil",
        gazetteer: "TDWG Level 4", establishment_means: null,
        degree_of_establishment: null },
      // All-nullables row — proves every nullable column
      // round-trips independently. The legacy oracle would
      // render this row with the `.means-unknown` chip and
      // the area text; the canonical projection MUST keep
      // `null` for every nullable field so the renderer can
      // apply the ODD-TDDIST-001 fallback deterministically.
      { id: 7005, area: "Eurasia",
        gazetteer: null, establishment_means: null,
        degree_of_establishment: null },
    ] },
  ]);
  const dist = await api.fetchDistribution(100, { fetch: DistFresh, baseUrl: "http://x" });
  assert.strictEqual(DistFresh.calls.length, 1);
  assert.strictEqual(DistFresh.calls[0].input, "http://x/api/taxon/100/distribution?limit=200",
    "fetchDistribution must build the canonical legacy /api/taxon/{id}/distribution?limit=200 URL by default");
  assert.strictEqual(Array.isArray(dist), true, "fetchDistribution must return an array");
  assert.strictEqual(dist.length, 5,
    "fetchDistribution must surface every server-returned DistributionEntry row");
  // Wire ordering preservation — the server returns rows
  // sorted by `establishment_means, area` and the React
  // port preserves the order verbatim (the UI must NOT sort
  // client-side per the ODD-TDDIST-001 user constraint).
  assert.strictEqual(dist[0].id, 7001);
  assert.strictEqual(dist[0].area, "Argentina");
  assert.strictEqual(dist[0].gazetteer, "TDWG Level 4");
  assert.strictEqual(dist[0].establishment_means, "native");
  assert.strictEqual(dist[0].degree_of_establishment, "native");
  assert.strictEqual(dist[1].id, 7002);
  assert.strictEqual(dist[1].establishment_means, "introduced");
  assert.strictEqual(dist[2].id, 7003);
  assert.strictEqual(dist[2].establishment_means, "uncertain");
  assert.strictEqual(dist[2].degree_of_establishment, null,
    "ODD-TDDIST-001: nullable degree_of_establishment must round-trip verbatim (null stays null)");
  // Nullable establishment_means must round-trip verbatim
  // (the legacy `web/detail.js::buildDetailSection` applies
  // the `|| "unknown"` fallback at render time, so coercing
  // `null → ""` or `null → "unknown"` client-side would
  // silently bypass the legacy fallback contract).
  assert.strictEqual(dist[3].id, 7004);
  assert.strictEqual(dist[3].area, "Brazil");
  assert.strictEqual(dist[3].gazetteer, "TDWG Level 4");
  assert.strictEqual(dist[3].establishment_means, null,
    "ODD-TDDIST-001: nullable establishment_means must round-trip verbatim (null stays null)");
  assert.strictEqual(dist[3].degree_of_establishment, null);
  // All-nullables row — every nullable column surfaces as
  // `null` independently so the renderer can branch on each
  // field's nullability independently.
  assert.strictEqual(dist[4].id, 7005);
  assert.strictEqual(dist[4].area, "Eurasia");
  assert.strictEqual(dist[4].gazetteer, null,
    "ODD-TDDIST-001: nullable gazetteer must round-trip verbatim (null stays null)");
  assert.strictEqual(dist[4].establishment_means, null);
  assert.strictEqual(dist[4].degree_of_establishment, null);
  // The DistributionEntry projection must NOT carry any
  // invented field beyond the FastAPI wire shape.
  for (const e of dist) {
    const props = Object.keys(e).sort();
    assert.deepStrictEqual(props,
      ["area", "degree_of_establishment", "establishment_means", "gazetteer", "id"],
      "ODD-TDDIST-001: canonical DistributionEntry must carry exactly "
      + "{id, area, gazetteer, establishment_means, degree_of_establishment}; got "
      + JSON.stringify(props));
  }

  // fetchDistribution ?limit= override — query forwarded verbatim.
  const DistLim50 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchDistribution(100, { fetch: DistLim50, baseUrl: "http://x", limit: 50 });
  assert.strictEqual(DistLim50.calls[0].input, "http://x/api/taxon/100/distribution?limit=50",
    "fetchDistribution must forward opts.limit verbatim: " + DistLim50.calls[0].input);
  const DistLim1000 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchDistribution(100, { fetch: DistLim1000, baseUrl: "http://x", limit: 1000 });
  assert.strictEqual(DistLim1000.calls[0].input, "http://x/api/taxon/100/distribution?limit=1000",
    "fetchDistribution must forward opts.limit=1000 verbatim");

  // fetchDistribution empty payload — returns [], does not throw.
  const DistEmpty = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  assert.strictEqual((await api.fetchDistribution(100, { fetch: DistEmpty, baseUrl: "http://x" })).length, 0);

  // fetchDistribution HTTP non-OK — status code in message.
  const DistBad = makeFetch([{ ok: false, status: 503, statusText: "Service Unavailable", json: { detail: "DB down" } }]);
  await assert.rejects(
    () => api.fetchDistribution(100, { fetch: DistBad, baseUrl: "http://x" }),
    (err) => /503/.test(String(err && err.message || err)),
    "fetchDistribution must reject on non-OK with the status code in the message",
  );

  // fetchDistribution non-array payload — rejects.
  const DistWrongShape = makeFetch([{ ok: true, status: 200, statusText: "OK", json: { detail: "wrong shape" } }]);
  await assert.rejects(
    () => api.fetchDistribution(100, { fetch: DistWrongShape, baseUrl: "http://x" }),
    (err) => /non-array/.test(String(err && err.message || err)),
    "fetchDistribution must reject non-array payloads",
  );

  // fetchDistribution schema-invalid element — rejects.
  const DistBadElement = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, area: "Argentina" /* all nullable fields missing */ }] }]);
  await assert.rejects(
    () => api.fetchDistribution(100, { fetch: DistBadElement, baseUrl: "http://x" }),
    (err) => /invalid|distribution/i.test(String(err && err.message || err)),
    "fetchDistribution must reject per-element shape mismatches (missing nullable fields as undefined)",
  );

  // fetchDistribution wrong type on nullable field — rejects.
  const DistBadGazType = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, area: "Argentina", gazetteer: 123,
             establishment_means: null, degree_of_establishment: null }] }]);
  await assert.rejects(
    () => api.fetchDistribution(100, { fetch: DistBadGazType, baseUrl: "http://x" }),
    (err) => /invalid|distribution/i.test(String(err && err.message || err)),
    "fetchDistribution must reject non-string gazetteer values",
  );

  // fetchDistribution wrong type on nullable field (means) — rejects.
  const DistBadMeansType = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, area: "Argentina", gazetteer: null,
             establishment_means: 7, degree_of_establishment: null }] }]);
  await assert.rejects(
    () => api.fetchDistribution(100, { fetch: DistBadMeansType, baseUrl: "http://x" }),
    (err) => /invalid|distribution/i.test(String(err && err.message || err)),
    "fetchDistribution must reject non-string establishment_means values",
  );

  // fetchDistribution wrong type on nullable field (degree) — rejects.
  const DistBadDegreeType = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, area: "Argentina", gazetteer: null,
             establishment_means: null, degree_of_establishment: {} }] }]);
  await assert.rejects(
    () => api.fetchDistribution(100, { fetch: DistBadDegreeType, baseUrl: "http://x" }),
    (err) => /invalid|distribution/i.test(String(err && err.message || err)),
    "fetchDistribution must reject non-string degree_of_establishment values",
  );

  // fetchDistribution wrong type on area (number instead of string) — rejects.
  const DistBadAreaType = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, area: 42, gazetteer: null,
             establishment_means: null, degree_of_establishment: null }] }]);
  await assert.rejects(
    () => api.fetchDistribution(100, { fetch: DistBadAreaType, baseUrl: "http://x" }),
    (err) => /invalid|distribution/i.test(String(err && err.message || err)),
    "fetchDistribution must reject non-string area values",
  );

  // fetchDistribution empty area — rejects (the legacy
  // `web/detail.js::loadDetail` would not produce an empty
  // area because CoL rows have a NOT NULL constraint, but the
  // React projection must still reject the wire shape so a
  // future server change cannot silently bypass the
  // validation).
  const DistEmptyArea = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [{ id: 1, area: "", gazetteer: null,
             establishment_means: null, degree_of_establishment: null }] }]);
  await assert.rejects(
    () => api.fetchDistribution(100, { fetch: DistEmptyArea, baseUrl: "http://x" }),
    (err) => /invalid|distribution/i.test(String(err && err.message || err)),
    "fetchDistribution must reject empty area values",
  );

  // fetchDistribution negative id — id validation rejects.
  await assert.rejects(
    () => api.fetchDistribution(-1, { fetch: makeFetch([]), baseUrl: "http://x" }),
    (err) => /non-negative integer/i.test(String(err && err.message || err)),
    "fetchDistribution must reject negative ids",
  );

  // fetchDistribution non-integer id — id validation rejects.
  await assert.rejects(
    () => api.fetchDistribution(1.5, { fetch: makeFetch([]), baseUrl: "http://x" }),
    (err) => /non-negative integer/i.test(String(err && err.message || err)),
    "fetchDistribution must reject non-integer ids",
  );

  // fetchDistribution malformed JSON — throws.
  const DistJsonFail = makeFetch([{ ok: true, status: 200, statusText: "OK", json: Promise.reject(new SyntaxError("Unexpected token < in JSON")) }]);
  await assert.rejects(
    () => api.fetchDistribution(100, { fetch: DistJsonFail, baseUrl: "http://x" }),
    (err) => /json|JSON/i.test(String(err && err.message || err)),
    "fetchDistribution must reject malformed JSON",
  );

  // ---- ODD-TDFOLDER-001 — previewMaterialize wire → domain projection ----
  // The server returns a single `MaterializePreview` object
  // carrying `ok`, `taxon_id`, `scientific_name`,
  // `research_dir`, `relative_path`, `absolute_path`,
  // `segments[]`, `new_count`, `existing_count`, `all_exist`.
  // The React port preserves every wire field verbatim (the
  // cumulative `relative_path` + `absolute_path` are
  // server-composed; the segments are the sanitized ancestor
  // chain + the taxon's own name) so the renderer never joins
  // or sanitises paths client-side.
  const PreviewFresh = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: {
      ok: true,
      taxon_id: 100,
      scientific_name: "Freshwater Fishes",
      research_dir: "/Users/sebailla/Research",
      relative_path: "Freshwater Fishes",
      absolute_path: "/Users/sebailla/Research/Freshwater Fishes",
      segments: [
        { name: "Freshwater Fishes", exists: true, is_dir: true, is_new: false },
      ],
      new_count: 0,
      existing_count: 1,
      all_exist: true,
    } },
  ]);
  const preview = await api.previewMaterialize(100, { fetch: PreviewFresh, baseUrl: "http://x" });
  assert.strictEqual(PreviewFresh.calls.length, 1);
  assert.strictEqual(PreviewFresh.calls[0].input, "http://x/api/taxon/100/materialize-preview",
    "previewMaterialize must build the canonical legacy /api/taxon/{id}/materialize-preview URL by default");
  // The runtime helper uses GET (no init) — the preview is
  // informational only (no side effects on disk).
  assert.strictEqual(PreviewFresh.calls[0].init, undefined,
    "previewMaterialize must use GET (no method= init) because the preview is informational");
  assert.strictEqual(preview.ok, true);
  assert.strictEqual(preview.taxon_id, 100);
  assert.strictEqual(preview.scientific_name, "Freshwater Fishes");
  // Cumulative path fields must round-trip verbatim — the
  // React port NEVER joins or sanitises paths client-side.
  assert.strictEqual(preview.research_dir, "/Users/sebailla/Research",
    "ODD-TDFOLDER-001: research_dir must round-trip verbatim (server-composed path)");
  assert.strictEqual(preview.relative_path, "Freshwater Fishes",
    "ODD-TDFOLDER-001: relative_path must round-trip verbatim (server-composed path)");
  assert.strictEqual(preview.absolute_path, "/Users/sebailla/Research/Freshwater Fishes",
    "ODD-TDFOLDER-001: absolute_path must round-trip verbatim (server-composed path)");
  assert.strictEqual(preview.new_count, 0);
  assert.strictEqual(preview.existing_count, 1);
  assert.strictEqual(preview.all_exist, true);
  // Segments must round-trip verbatim — every flag carries the
  // server-preserved boolean, the name carries the sanitized
  // label verbatim.
  assert.strictEqual(preview.segments.length, 1);
  assert.strictEqual(preview.segments[0].name, "Freshwater Fishes");
  assert.strictEqual(preview.segments[0].exists, true);
  assert.strictEqual(preview.segments[0].is_dir, true);
  assert.strictEqual(preview.segments[0].is_new, false);
  for (const seg of preview.segments) {
    const props = Object.keys(seg).sort();
    assert.deepStrictEqual(props, ["exists", "is_dir", "is_new", "name"],
      "ODD-TDFOLDER-001: canonical MaterializePreviewSegment must carry exactly "
      + "{name, exists, is_dir, is_new}; got " + JSON.stringify(props));
  }
  // The top-level projection must NOT carry any invented
  // field beyond the FastAPI wire shape.
  const previewKeys = Object.keys(preview).sort();
  assert.deepStrictEqual(previewKeys,
    ["absolute_path", "all_exist", "existing_count", "new_count",
     "ok", "relative_path", "research_dir", "scientific_name",
     "segments", "taxon_id"],
    "ODD-TDFOLDER-001: canonical MaterializePreview must carry exactly "
    + "{ok, taxon_id, scientific_name, research_dir, relative_path, "
    + "absolute_path, segments, new_count, existing_count, all_exist}; got "
    + JSON.stringify(previewKeys));

  // previewMaterialize — mixed new + existing segments. The
  // server's `new_count` + `existing_count` are surface
  // values; the renderer must NOT recompute them client-side.
  const PreviewMixed = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: {
      ok: true,
      taxon_id: 100,
      scientific_name: "Cichlidae",
      research_dir: "/Users/sebailla/Research",
      relative_path: "Eukaryota/Animalia/Chordata/Cichlidae",
      absolute_path: "/Users/sebailla/Research/Eukaryota/Animalia/Chordata/Cichlidae",
      segments: [
        { name: "Eukaryota", exists: true, is_dir: true, is_new: false },
        { name: "Animalia",  exists: true, is_dir: true, is_new: false },
        { name: "Chordata",  exists: false, is_dir: false, is_new: true },
        { name: "Cichlidae", exists: false, is_dir: false, is_new: true },
      ],
      new_count: 2,
      existing_count: 2,
      all_exist: false,
    } },
  ]);
  const previewMixed = await api.previewMaterialize(100, { fetch: PreviewMixed, baseUrl: "http://x" });
  assert.strictEqual(previewMixed.segments.length, 4);
  assert.strictEqual(previewMixed.segments[0].name, "Eukaryota");
  assert.strictEqual(previewMixed.segments[0].exists, true);
  assert.strictEqual(previewMixed.segments[2].name, "Chordata");
  assert.strictEqual(previewMixed.segments[2].exists, false);
  assert.strictEqual(previewMixed.segments[2].is_new, true);
  assert.strictEqual(previewMixed.new_count, 2);
  assert.strictEqual(previewMixed.existing_count, 2);
  assert.strictEqual(previewMixed.all_exist, false);

  // previewMaterialize ?source=col|worms|freshwater — query
  // forwarded verbatim. The FastAPI endpoint accepts the
  // same `source` query parameter as
  // `/api/taxon/{id}/children`, selecting which hierarchy to
  // walk.
  const PreviewSrcWorms = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { ok: true, taxon_id: 1, scientific_name: "Animalia",
      research_dir: "/r", relative_path: "Animalia", absolute_path: "/r/Animalia",
      segments: [{ name: "Animalia", exists: true, is_dir: true, is_new: false }],
      new_count: 0, existing_count: 1, all_exist: true } }]);
  await api.previewMaterialize(1, { fetch: PreviewSrcWorms, baseUrl: "http://x", source: "worms" });
  assert.strictEqual(PreviewSrcWorms.calls[0].input, "http://x/api/taxon/1/materialize-preview?source=worms",
    "previewMaterialize must forward ?source=worms verbatim: " + PreviewSrcWorms.calls[0].input);
  const PreviewSrcFw = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { ok: true, taxon_id: 1, scientific_name: "Animalia",
      research_dir: "/r", relative_path: "Animalia", absolute_path: "/r/Animalia",
      segments: [{ name: "Animalia", exists: true, is_dir: true, is_new: false }],
      new_count: 0, existing_count: 1, all_exist: true } }]);
  await api.previewMaterialize(1, { fetch: PreviewSrcFw, baseUrl: "http://x", source: "freshwater" });
  assert.strictEqual(PreviewSrcFw.calls[0].input, "http://x/api/taxon/1/materialize-preview?source=freshwater",
    "previewMaterialize must forward ?source=freshwater verbatim: " + PreviewSrcFw.calls[0].input);

  // previewMaterialize HTTP non-OK — status code in message.
  const PreviewBad = makeFetch([{ ok: false, status: 503, statusText: "Service Unavailable", json: { detail: "DB down" } }]);
  await assert.rejects(
    () => api.previewMaterialize(100, { fetch: PreviewBad, baseUrl: "http://x" }),
    (err) => /503/.test(String(err && err.message || err)),
    "previewMaterialize must reject on non-OK with the status code in the message",
  );

  // previewMaterialize schema-invalid top-level payload — rejects.
  const PreviewWrongShape = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { detail: "wrong shape" } }]);
  await assert.rejects(
    () => api.previewMaterialize(100, { fetch: PreviewWrongShape, baseUrl: "http://x" }),
    (err) => /invalid|materialize/i.test(String(err && err.message || err)),
    "previewMaterialize must reject non-object payloads",
  );

  // previewMaterialize schema-invalid segment — rejects.
  const PreviewBadSeg = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { ok: true, taxon_id: 1, scientific_name: "X", research_dir: "/r",
      relative_path: "X", absolute_path: "/r/X",
      segments: [{ name: "X" /* exists/is_dir/is_new missing */ }],
      new_count: 0, existing_count: 1, all_exist: true } }]);
  await assert.rejects(
    () => api.previewMaterialize(1, { fetch: PreviewBadSeg, baseUrl: "http://x" }),
    (err) => /invalid|materialize/i.test(String(err && err.message || err)),
    "previewMaterialize must reject per-segment shape mismatches",
  );

  // previewMaterialize wrong type on `ok` — rejects (string
  // instead of boolean).
  const PreviewBadOk = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { ok: "true", taxon_id: 1, scientific_name: "X",
      research_dir: "/r", relative_path: "X", absolute_path: "/r/X",
      segments: [{ name: "X", exists: true, is_dir: true, is_new: false }],
      new_count: 0, existing_count: 1, all_exist: true } }]);
  await assert.rejects(
    () => api.previewMaterialize(1, { fetch: PreviewBadOk, baseUrl: "http://x" }),
    (err) => /invalid|materialize/i.test(String(err && err.message || err)),
    "previewMaterialize must reject non-boolean `ok` values",
  );

  // previewMaterialize negative id — id validation rejects.
  await assert.rejects(
    () => api.previewMaterialize(-1, { fetch: makeFetch([]), baseUrl: "http://x" }),
    (err) => /non-negative integer/i.test(String(err && err.message || err)),
    "previewMaterialize must reject negative ids",
  );

  // previewMaterialize malformed JSON — throws.
  const PreviewJsonFail = makeFetch([{ ok: true, status: 200, statusText: "OK", json: Promise.reject(new SyntaxError("Unexpected token < in JSON")) }]);
  await assert.rejects(
    () => api.previewMaterialize(100, { fetch: PreviewJsonFail, baseUrl: "http://x" }),
    (err) => /json|JSON/i.test(String(err && err.message || err)),
    "previewMaterialize must reject malformed JSON",
  );

  // ---- ODD-TDFOLDER-001 — materializeResearch wire → domain projection ----
  // The server returns a single `MaterializeResult` object
  // carrying `ok`, `absolute_path`, `relative_path`,
  // `folders_created`, `folders_existed`, `segments[]`. The
  // segments array is a list of sanitized string names
  // (different shape from the preview's per-segment objects).
  // The runtime helper uses POST explicitly (the endpoint
  // mutates the server filesystem via `mkdir`).
  const MatFresh = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: {
      ok: true,
      absolute_path: "/Users/sebailla/Research/Eukaryota/Animalia/Chordata/Cichlidae",
      relative_path: "Eukaryota/Animalia/Chordata/Cichlidae",
      folders_created: 2,
      folders_existed: 2,
      segments: ["Eukaryota", "Animalia", "Chordata", "Cichlidae"],
    } },
  ]);
  const mat = await api.materializeResearch(100, { fetch: MatFresh, baseUrl: "http://x" });
  assert.strictEqual(MatFresh.calls.length, 1);
  assert.strictEqual(MatFresh.calls[0].input, "http://x/api/taxon/100/materialize",
    "materializeResearch must build the canonical legacy /api/taxon/{id}/materialize URL by default");
  assert.deepStrictEqual(MatFresh.calls[0].init, { method: "POST" },
    "materializeResearch must use POST (the endpoint mutates the filesystem)");
  assert.strictEqual(mat.ok, true);
  assert.strictEqual(mat.absolute_path, "/Users/sebailla/Research/Eukaryota/Animalia/Chordata/Cichlidae",
    "ODD-TDFOLDER-001: absolute_path must round-trip verbatim (server-composed path)");
  assert.strictEqual(mat.relative_path, "Eukaryota/Animalia/Chordata/Cichlidae",
    "ODD-TDFOLDER-001: relative_path must round-trip verbatim (server-composed path)");
  assert.strictEqual(mat.folders_created, 2);
  assert.strictEqual(mat.folders_existed, 2);
  assert.deepStrictEqual(mat.segments,
    ["Eukaryota", "Animalia", "Chordata", "Cichlidae"],
    "ODD-TDFOLDER-001: segments must round-trip verbatim as a string[]");
  // The MaterializeResult projection must NOT carry any
  // invented field beyond the FastAPI wire shape.
  const matKeys = Object.keys(mat).sort();
  assert.deepStrictEqual(matKeys,
    ["absolute_path", "folders_created", "folders_existed", "ok",
     "relative_path", "segments"],
    "ODD-TDFOLDER-001: canonical MaterializeResult must carry exactly "
    + "{ok, absolute_path, relative_path, folders_created, "
    + "folders_existed, segments}; got " + JSON.stringify(matKeys));

  // materializeResearch ?source=col|worms|freshwater — query
  // forwarded verbatim.
  const MatSrcWorms = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { ok: true, absolute_path: "/r/A", relative_path: "A",
      folders_created: 1, folders_existed: 0, segments: ["A"] } }]);
  await api.materializeResearch(1, { fetch: MatSrcWorms, baseUrl: "http://x", source: "worms" });
  assert.strictEqual(MatSrcWorms.calls[0].input, "http://x/api/taxon/1/materialize?source=worms",
    "materializeResearch must forward ?source=worms verbatim: " + MatSrcWorms.calls[0].input);

  // materializeResearch HTTP non-OK — status code in message.
  const MatBad = makeFetch([{ ok: false, status: 409, statusText: "Conflict",
    json: { detail: "path conflict at /r/A: not a directory" } }]);
  await assert.rejects(
    () => api.materializeResearch(100, { fetch: MatBad, baseUrl: "http://x" }),
    (err) => /409/.test(String(err && err.message || err)),
    "materializeResearch must reject on non-OK with the status code in the message",
  );

  // materializeResearch schema-invalid payload — rejects.
  const MatWrongShape = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { detail: "wrong shape" } }]);
  await assert.rejects(
    () => api.materializeResearch(100, { fetch: MatWrongShape, baseUrl: "http://x" }),
    (err) => /invalid|materialize/i.test(String(err && err.message || err)),
    "materializeResearch must reject non-object payloads",
  );

  // materializeResearch empty segments — rejects (the server
  // always returns the sanitized ancestor chain + the taxon's
  // own scientific_name).
  const MatEmptySegs = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { ok: true, absolute_path: "/r/A", relative_path: "A",
      folders_created: 1, folders_existed: 0, segments: [] } }]);
  await assert.rejects(
    () => api.materializeResearch(100, { fetch: MatEmptySegs, baseUrl: "http://x" }),
    (err) => /invalid|materialize/i.test(String(err && err.message || err)),
    "materializeResearch must reject empty segments arrays",
  );

  // materializeResearch negative folders_created — rejects.
  const MatNegCreated = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { ok: true, absolute_path: "/r/A", relative_path: "A",
      folders_created: -1, folders_existed: 0, segments: ["A"] } }]);
  await assert.rejects(
    () => api.materializeResearch(100, { fetch: MatNegCreated, baseUrl: "http://x" }),
    (err) => /invalid|materialize/i.test(String(err && err.message || err)),
    "materializeResearch must reject negative folders_created values",
  );

  // materializeResearch negative id — id validation rejects.
  await assert.rejects(
    () => api.materializeResearch(-1, { fetch: makeFetch([]), baseUrl: "http://x" }),
    (err) => /non-negative integer/i.test(String(err && err.message || err)),
    "materializeResearch must reject negative ids",
  );

  // materializeResearch malformed JSON — throws.
  const MatJsonFail = makeFetch([{ ok: true, status: 200, statusText: "OK", json: Promise.reject(new SyntaxError("Unexpected token < in JSON")) }]);
  await assert.rejects(
    () => api.materializeResearch(100, { fetch: MatJsonFail, baseUrl: "http://x" }),
    (err) => /json|JSON/i.test(String(err && err.message || err)),
    "materializeResearch must reject malformed JSON",
  );

  // ---- ODD-TDFOLDER-001 — openFolder wire → domain projection ----
  // The server returns a single `OpenFolderResult` object
  // carrying `ok`, `absolute_path`, `relative_path`,
  // `opened_with`. The `opened_with` field is the OS-binary
  // name the server actually invoked.
  const OpenFresh = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: {
      ok: true,
      absolute_path: "/Users/sebailla/Research/Freshwater Fishes",
      relative_path: "Freshwater Fishes",
      opened_with: "open",
    } },
  ]);
  const open = await api.openFolder(100, { fetch: OpenFresh, baseUrl: "http://x" });
  assert.strictEqual(OpenFresh.calls.length, 1);
  assert.strictEqual(OpenFresh.calls[0].input, "http://x/api/taxon/100/open-folder",
    "openFolder must build the canonical legacy /api/taxon/{id}/open-folder URL by default");
  assert.deepStrictEqual(OpenFresh.calls[0].init, { method: "POST" },
    "openFolder must use POST (the endpoint spawns the OS file manager)");
  assert.strictEqual(open.ok, true);
  assert.strictEqual(open.absolute_path, "/Users/sebailla/Research/Freshwater Fishes",
    "ODD-TDFOLDER-001: absolute_path must round-trip verbatim (server-composed path)");
  assert.strictEqual(open.relative_path, "Freshwater Fishes",
    "ODD-TDFOLDER-001: relative_path must round-trip verbatim (server-composed path)");
  assert.strictEqual(open.opened_with, "open",
    "ODD-TDFOLDER-001: opened_with must round-trip verbatim (server-preserved binary name)");
  // The OpenFolderResult projection must NOT carry any
  // invented field beyond the FastAPI wire shape.
  const openKeys = Object.keys(open).sort();
  assert.deepStrictEqual(openKeys,
    ["absolute_path", "ok", "opened_with", "relative_path"],
    "ODD-TDFOLDER-001: canonical OpenFolderResult must carry exactly "
    + "{ok, absolute_path, relative_path, opened_with}; got " + JSON.stringify(openKeys));

  // openFolder ?source=col|worms|freshwater — query forwarded verbatim.
  const OpenSrcFw = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { ok: true, absolute_path: "/r/A", relative_path: "A", opened_with: "open" } }]);
  await api.openFolder(1, { fetch: OpenSrcFw, baseUrl: "http://x", source: "freshwater" });
  assert.strictEqual(OpenSrcFw.calls[0].input, "http://x/api/taxon/1/open-folder?source=freshwater",
    "openFolder must forward ?source=freshwater verbatim: " + OpenSrcFw.calls[0].input);

  // openFolder HTTP non-OK — 404 when the folder has not
  // been materialized yet. The renderer hides the
  // path-actions row when `all_exist === false`, but a
  // defensive error path must still surface the status in
  // the message.
  const OpenNotFound = makeFetch([{ ok: false, status: 404, statusText: "Not Found",
    json: { detail: "folder does not exist on disk: /r/A" } }]);
  await assert.rejects(
    () => api.openFolder(100, { fetch: OpenNotFound, baseUrl: "http://x" }),
    (err) => /404/.test(String(err && err.message || err)),
    "openFolder must reject on non-OK with the status code in the message",
  );

  // openFolder schema-invalid payload — rejects.
  const OpenWrongShape = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { detail: "wrong shape" } }]);
  await assert.rejects(
    () => api.openFolder(100, { fetch: OpenWrongShape, baseUrl: "http://x" }),
    (err) => /invalid|open-folder/i.test(String(err && err.message || err)),
    "openFolder must reject non-object payloads",
  );

  // openFolder empty opened_with — rejects (the server
  // always returns the chosen binary name verbatim).
  const OpenEmptyBin = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { ok: true, absolute_path: "/r/A", relative_path: "A", opened_with: "" } }]);
  await assert.rejects(
    () => api.openFolder(100, { fetch: OpenEmptyBin, baseUrl: "http://x" }),
    (err) => /invalid|open-folder/i.test(String(err && err.message || err)),
    "openFolder must reject empty opened_with values",
  );

  // openFolder wrong type on `ok` — rejects (string instead
  // of boolean).
  const OpenBadOk = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: { ok: "true", absolute_path: "/r/A", relative_path: "A", opened_with: "open" } }]);
  await assert.rejects(
    () => api.openFolder(100, { fetch: OpenBadOk, baseUrl: "http://x" }),
    (err) => /invalid|open-folder/i.test(String(err && err.message || err)),
    "openFolder must reject non-boolean `ok` values",
  );

  // openFolder negative id — id validation rejects.
  await assert.rejects(
    () => api.openFolder(-1, { fetch: makeFetch([]), baseUrl: "http://x" }),
    (err) => /non-negative integer/i.test(String(err && err.message || err)),
    "openFolder must reject negative ids",
  );

  // openFolder non-integer id — id validation rejects.
  await assert.rejects(
    () => api.openFolder(1.5, { fetch: makeFetch([]), baseUrl: "http://x" }),
    (err) => /non-negative integer/i.test(String(err && err.message || err)),
    "openFolder must reject non-integer ids",
  );

  // openFolder malformed JSON — throws.
  const OpenJsonFail = makeFetch([{ ok: true, status: 200, statusText: "OK", json: Promise.reject(new SyntaxError("Unexpected token < in JSON")) }]);
  await assert.rejects(
    () => api.openFolder(100, { fetch: OpenJsonFail, baseUrl: "http://x" }),
    (err) => /json|JSON/i.test(String(err && err.message || err)),
    "openFolder must reject malformed JSON",
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
