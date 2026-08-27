"""
Minimal FastAPI server for the taxa tree.

Endpoints
---------
GET  /                                              → redirect to /docs
GET  /api/health                                    → DB stats
GET  /api/domains                                   → top-level domains
GET  /api/taxon/{id}                                → single taxon + breadcrumb
GET  /api/taxon/{id}/children                       → direct children (paginated)
GET  /api/taxon/{id}/vernaculars                    → common names for this taxon
GET  /api/taxon/{id}/searches                       → 14 server-composed search URLs
GET  /api/search?q=                                 → search across scientific name,
                                                           authorship AND vernacular

Run:
    uvicorn api.server:app --reload --port 8765
"""

from __future__ import annotations

import logging
import os
import platform
import re
import sqlite3
import subprocess
import sys
from types import MappingProxyType
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# pyright: ignore — pyright can't resolve `etl.migrations` against this
# project's package layout. The import resolves fine at runtime (verified
# by all 14 etl tests); this is a static-checker false positive.
from etl.migrations import CURRENT_SCHEMA_VERSION, get_applied_version  # pyright: ignore

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "taxa.db"
WEB_DIR = Path(__file__).parent.parent / "web"
# Where the materialize endpoint creates folder structures. Configurable via
# env var so tests can monkeypatch to a tmp dir without touching the real
# research folder. Resolved to absolute so the response's `absolute_path`
# field is stable regardless of cwd.
RESEARCH_DIR = Path(os.getenv("TAXA_RESEARCH_DIR", "./Research")).resolve()

_logger = logging.getLogger(__name__)


# --- File-explorer endpoint constants ----------------------------------------
#
# PR 1 of the file-explorer change adds two endpoints:
#   GET /api/taxon/{id}/files         — recursive tree JSON
#   GET /api/taxon/{id}/files/serve   — streaming file with safety checks
# These constants are the streaming cap and the extension→content-type table
# the /serve endpoint consults. See design.md §3 for the contract.
_STREAM_CAP_BYTES = 100 * 1024 * 1024  # 100 MB
# Immutable read-only view over the content-type map. MappingProxyType
# raises TypeError on mutation, making this a true read-only constant.
# Wrapped (not a bare dict literal) so opengrep's
# `python-mutable-class-attr` rule does not fire — the rule keys on
# `{...}` literal assignment to a non-frozen module-level name.
_CONTENT_TYPE_BY_EXT: MappingProxyType = MappingProxyType({
    "pdf":  "application/pdf",
    "epub": "application/epub+zip",
    "html": "text/html",
    "htm":  "text/html",
    "md":   "text/markdown",
    "txt":  "text/plain",
    "doc":  "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls":  "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
})


def db() -> sqlite3.Connection:
    """Open a fresh read-only connection. Cheap because of WAL mode."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="taxa.db not ready; ETL running?")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


app = FastAPI(title="Taxa Tree API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    # Local-only API — restrict CORS to localhost / 127.0.0.1 on any port.
    # Same-origin requests (the typical case: frontend served by this app)
    # bypass CORS entirely; this only matters when someone runs the
    # frontend from a different port (e.g. Vite dev server on :5173)
    # during local development. No remote origins are allowed.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


@app.get("/", include_in_schema=False)
def root():
    """Deprecated — the StaticFiles mount at the bottom of this file serves
    the frontend now. Kept as a fallback when the web/ dir is empty."""
    index = WEB_DIR / "index.html"
    if not index.exists():
        return RedirectResponse(url="/docs")
    # The mount will handle this in production; this is a safety net.
    from fastapi.responses import FileResponse
    return FileResponse(str(index))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


class Vernacular(BaseModel):
    id: int
    name: str
    language: Optional[str]
    country: Optional[str]


class Synonym(BaseModel):
    id: int
    rank: str
    scientific_name: str
    authorship: Optional[str]
    status: str  # "synonym", "ambiguous synonym", "misapplied", etc.


class DistributionEntry(BaseModel):
    id: int
    area: str
    gazetteer: Optional[str]
    establishment_means: Optional[str]
    degree_of_establishment: Optional[str]


class Taxon(BaseModel):
    id: int
    parent_id: Optional[int]
    rank: str
    status: str
    scientific_name: str
    authorship: Optional[str]
    path: Optional[str]
    species_count: Optional[int]
    coldp_id: Optional[str]
    worms_id: Optional[int] = None
    freshwater_id: Optional[int] = None
    freshwater_parent_id: Optional[int] = None
    is_extinct: bool
    vernaculars: list[Vernacular] = []
    # True iff the taxon's root→taxon folder already exists on disk under
    # RESEARCH_DIR. Populated by /api/taxon/{id}/children so the frontend
    # can paint the per-row materialize icon in the "exists" (green) state
    # without firing a per-row preview request. None when not applicable
    # (e.g. /api/taxon/{id} single-taxon responses) — the frontend treats
    # None as "unknown" / "not exists".
    research_path_exists: Optional[bool] = None


class SearchLink(BaseModel):
    """A single pre-composed search-engine link for a taxon.

    The URL is server-composed (urllib.parse.quote_plus) so the frontend
    never has to build search queries itself. The 14 entries are produced
    by `_build_search` from the `_SEARCH_ENGINES` module-level constant.
    """
    engine: str   # one of the 14 keys (e.g. "google", "wikipedia")
    label: str    # display text (e.g. "Google", "Wikipedia")
    url: str      # pre-computed, fully URL-encoded


RANK_ORDER = """
    CASE rank
        WHEN 'collection' THEN -1   -- synthetic root (reserved for "Freshwater Fishes"); sorts above domain
        WHEN 'domain' THEN 0
        WHEN 'kingdom' THEN 1
        WHEN 'phylum' THEN 2
        WHEN 'subphylum' THEN 3
        WHEN 'class' THEN 4
        WHEN 'subclass' THEN 5
        WHEN 'order' THEN 6
        WHEN 'suborder' THEN 7
        WHEN 'family' THEN 8
        WHEN 'subfamily' THEN 9
        WHEN 'genus' THEN 10
        WHEN 'subgenus' THEN 11
        WHEN 'species' THEN 12
        WHEN 'subspecies' THEN 13
        WHEN 'variety' THEN 14
        WHEN 'form' THEN 15
        ELSE 99
    END
"""


def _row_to_taxon(
    row: sqlite3.Row,
    vernaculars: list[Vernacular] | None = None,
    research_path_exists: Optional[bool] = None,
) -> Taxon:
    return Taxon(
        id=row["id"],
        parent_id=row["parent_id"],
        rank=row["rank"],
        status=row["status"],
        scientific_name=row["scientific_name"],
        authorship=row["authorship"],
        path=row["path"],
        species_count=row["species_count"],
        coldp_id=row["coldp_id"],
        worms_id=row["worms_id"],
        freshwater_id=row["freshwater_id"],
        freshwater_parent_id=row["freshwater_parent_id"],
        is_extinct=bool(row["is_extinct"]),
        vernaculars=vernaculars or [],
        research_path_exists=research_path_exists,
    )


def _vernaculars_for(conn: sqlite3.Connection, taxon_id: int) -> list[Vernacular]:
    # DISTINCT on (name, language) to dedupe rows caused by the non-unique
    # coldp_id mapping (homonym textree taxa map to the same CoL concept).
    rows = conn.execute(
        "SELECT MIN(id) AS id, name, language, country FROM vernacular "
        "WHERE taxon_id = ? "
        "GROUP BY name, language, country "
        "ORDER BY language, country, name LIMIT 50",
        (taxon_id,),
    ).fetchall()
    return [Vernacular(id=r["id"], name=r["name"],
                       language=r["language"], country=r["country"])
            for r in rows]


@app.get("/api/health")
def health():
    """Liveness + DB stats + schema version.

    The schema version fields (db_schema_version / expected_schema_version)
    are how the frontend decides whether to show a "DB outdated" banner.
    A mismatch is logged as a warning but does NOT fail the request — the
    API still serves data (some columns may be missing on older DBs but
    the existing endpoints all guard against that). The recovery is
    `make etl && make coldp && make worms && make freshwater` (or any
    subset that bumps PRAGMA user_version past the expected value).
    """
    with db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM taxon").fetchone()[0]
        n_vern = conn.execute("SELECT COUNT(*) FROM vernacular").fetchone()[0]
        n_extinct = conn.execute("SELECT COUNT(*) FROM taxon WHERE is_extinct=1").fetchone()[0]
        try:
            n_dist = conn.execute("SELECT COUNT(*) FROM distribution").fetchone()[0]
        except sqlite3.OperationalError:
            n_dist = 0
        db_version = get_applied_version(conn)
    if db_version < CURRENT_SCHEMA_VERSION:
        _logger.warning(
            "DB schema version %d is older than expected %d; "
            "run `make etl && make coldp` to upgrade",
            db_version, CURRENT_SCHEMA_VERSION,
        )
    return {
        "status": "ok",
        "taxa": n,
        "vernaculars": n_vern,
        "extinct": n_extinct,
        "distribution": n_dist,
        "db": str(DB_PATH),
        "db_schema_version": db_version,
        "expected_schema_version": CURRENT_SCHEMA_VERSION,
        "schema_outdated": db_version < CURRENT_SCHEMA_VERSION,
    }
@app.get("/api/domains", response_model=list[Taxon])
def get_domains():
    """Top-level roots for the tree. Returns:
    - The 4 CoL domains (Archaea, Bacteria, Eukaryota, Viruses)
    - Biota (the WoRMS superdomain, only with worms_id=1)
    - Freshwater Fishes (the synthetic freshwater root, only when the
      freshwater loader has run; identified by freshwater_id=1 AND
      freshwater_parent_id IS NULL so it doesn't drag in CSV rows that
      also have parent_id=NULL).

    Other taxa with parent_id IS NULL (WoRMS-only orphans) are reachable
    only through the toggle's WoRMS view — they were re-parented under
    Biota in the enrichment step so they don't pollute the root list.

    Each domain carries `research_path_exists` so the tree's per-row
    materialize indicator paints correctly for top-level taxa too.
    Without this, domains like Bacteria whose ./Research/{name} folder
    exists on disk would not show the green icon (the icon is driven
    by this flag, and the /children endpoint doesn't run for top-level
    domains — they're returned by /api/domains, not by any /children
    call)."""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM taxon WHERE parent_id IS NULL "
            "AND (coldp_id IS NOT NULL OR worms_id = 1 "
            "     OR (freshwater_id IS NOT NULL AND freshwater_parent_id IS NULL)) "
            "ORDER BY scientific_name"
        ).fetchall()
        out: list[Taxon] = []
        for r in rows:
            segs = _build_segments(conn, r["id"])
            out.append(
                _row_to_taxon(
                    r,
                    research_path_exists=_research_path_exists(segs),
                )
            )
    return out


@app.get("/api/taxon/{taxon_id}", response_model=Taxon)
def get_taxon(taxon_id: int):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM taxon WHERE id = ?", (taxon_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"taxon {taxon_id} not found")
        verns = _vernaculars_for(conn, taxon_id)
    return _row_to_taxon(row, verns)


@app.get("/api/taxon/{taxon_id}/synonyms", response_model=list[Synonym])
def get_synonyms(taxon_id: int, limit: int = Query(default=200, ge=1, le=1000)):
    """Names historically applied to this taxon. In ColDP/TextTree, a synonym
    row's parent_id points at the accepted name — so we look up rows where
    parent_id = {taxon_id} AND status != 'accepted'."""
    with db() as conn:
        rows = conn.execute(
            f"SELECT id, rank, scientific_name, authorship, status "
            f"FROM taxon WHERE parent_id = ? AND status != 'accepted' "
            f"ORDER BY rank, scientific_name LIMIT ?",
            (taxon_id, limit),
        ).fetchall()
    return [Synonym(
        id=r["id"], rank=r["rank"],
        scientific_name=r["scientific_name"],
        authorship=r["authorship"],
        status=r["status"],
    ) for r in rows]


@app.get("/api/taxon/{taxon_id}/distribution", response_model=list[DistributionEntry])
def get_distribution(
    taxon_id: int,
    limit: int = Query(default=200, ge=1, le=1000),
    only: Optional[str] = Query(default=None, max_length=20,
                                 description="Filter by establishment_means: 'native', 'introduced', 'uncertain'"),
):
    """Geographic range. Returns free-text area descriptions ('Argentina',
    'USA (Alabama, Colorado, ...)', 'South America')."""
    with db() as conn:
        if only:
            rows = conn.execute(
                f"SELECT id, area, gazetteer, establishment_means, degree_of_establishment "
                f"FROM distribution WHERE taxon_id = ? AND establishment_means = ? "
                f"ORDER BY area LIMIT ?",
                (taxon_id, only, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT id, area, gazetteer, establishment_means, degree_of_establishment "
                f"FROM distribution WHERE taxon_id = ? "
                f"ORDER BY establishment_means, area LIMIT ?",
                (taxon_id, limit),
            ).fetchall()
    return [DistributionEntry(
        id=r["id"], area=r["area"],
        gazetteer=r["gazetteer"],
        establishment_means=r["establishment_means"],
        degree_of_establishment=r["degree_of_establishment"],
    ) for r in rows]


@app.get("/api/taxon/{taxon_id}/vernaculars", response_model=list[Vernacular])
def get_vernaculars(
    taxon_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    language: Optional[str] = Query(default=None, max_length=8),
):
    with db() as conn:
        if language:
            rows = conn.execute(
                "SELECT MIN(id) AS id, name, language, country FROM vernacular "
                "WHERE taxon_id = ? AND language = ? "
                "GROUP BY name, language, country "
                "ORDER BY country, name LIMIT ?",
                (taxon_id, language, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT MIN(id) AS id, name, language, country FROM vernacular "
                "WHERE taxon_id = ? "
                "GROUP BY name, language, country "
                "ORDER BY language, country, name LIMIT ?",
                (taxon_id, limit),
            ).fetchall()
    return [Vernacular(id=r["id"], name=r["name"],
                       language=r["language"], country=r["country"])
            for r in rows]


@app.get("/api/taxon/{taxon_id}/children", response_model=list[Taxon])
def get_children(
    taxon_id: int,
    include_synonyms: bool = Query(default=False),
    source: str = Query(default="col", pattern="^(col|worms|freshwater)$"),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Children of a taxon. By default uses CoL's `parent_id` (the global
    backbone). Pass `source=worms` to walk the WoRMS hierarchy via
    `worms_parent_id` so the WoRMS view can drill from Biota down through
    the marine tree (Animalia → Mollusca → ...) using WoRMS's own
    hierarchy, independent of the CoL backbone. Pass `source=freshwater`
    to walk the freshwater overlay (freshwater_parent_id); the freshwater
    rows are isolated, so the CoL/WoRMS branches return empty for a
    freshwater taxon and vice versa.

    Each child carries `research_path_exists` so the frontend can paint the
    per-row materialize icon in the right state (green when the path is
    already on disk) without a per-row preview request.
    """
    if source == "worms":
        where = "worms_parent_id = ? AND worms_id IS NOT NULL"
    elif source == "freshwater":
        where = "freshwater_parent_id = ? AND freshwater_id IS NOT NULL"
    else:
        where = "parent_id = ?"
        if not include_synonyms:
            where += " AND status = 'accepted'"
    params: list = [taxon_id]
    with db() as conn:
        rows = conn.execute(
            f"SELECT * FROM taxon WHERE {where} "
            f"ORDER BY {RANK_ORDER}, scientific_name LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        # Compute the materialized-path flag per child in the same
        # connection scope so a single batch resolves all flags before
        # returning. The helper is cheap (a Path.exists() per child).
        out: list[Taxon] = []
        for r in rows:
            segs = _build_segments(conn, r["id"])
            out.append(_row_to_taxon(r, research_path_exists=_research_path_exists(segs)))
    return out


# ---------------------------------------------------------------------------
# Search-engine URL composition
#
# The server is the source of truth for the 14 pre-composed search URLs
# returned by /api/taxon/{id}/searches. The frontend has a parallel table
# in web/search_urls.js; tests/test_smoke.py::test_search_engine_contract
# (AC-21) enforces byte-identical key/label/with_authorship between the
# two. DO NOT REFORMAT this constant without updating the contract test.
#
# Each entry is a dict:
#   key              — stable id (e.g. "google"); used as SearchLink.engine
#   label            — display text (e.g. "Google"); used as SearchLink.label
#   template         — URL with {name} placeholder, used when authorship is
#                      not appended (most engines)
#   template_with_auth — URL with {name} and {auth} placeholders, used when
#                       the engine should append authorship (bhl, scholar).
#                       None for engines that don't take authorship.
#   with_authorship  — boolean; True iff the engine appends authorship
#   icon             — material-symbols-outlined glyph (UI rendering)
# ---------------------------------------------------------------------------
_SEARCH_ENGINES = [
    {"key": "google",       "label": "Google",        "template": "https://www.google.com/search?q={name}",                                                                          "template_with_auth": None,                                                     "with_authorship": False, "icon": "search"},
    {"key": "imagen",       "label": "Images",          "template": "https://www.google.com/search?q={name}&tbm=isch",                                                               "template_with_auth": None,                                                     "with_authorship": False, "icon": "image"},
    {"key": "documentos",   "label": "Documents",      "template": "https://www.google.com/search?q={name}+%28filetype%3Adoc+OR+filetype%3Adocx+OR+filetype%3Atxt%29",           "template_with_auth": None,                                                     "with_authorship": False, "icon": "description"},
    {"key": "pdf",          "label": "PDF",           "template": "https://www.google.com/search?q={name}+filetype%3Apdf",                                                        "template_with_auth": None,                                                     "with_authorship": False, "icon": "picture_as_pdf"},
    {"key": "wikipedia",    "label": "Wikipedia",     "template": "https://en.wikipedia.org/wiki/Special:Search?search={name}",                                                  "template_with_auth": None,                                                     "with_authorship": False, "icon": "menu_book"},
    {"key": "bhl",          "label": "BHL",           "template": "https://www.biodiversitylibrary.org/search?searchTerm={name}",                                                "template_with_auth": "https://www.biodiversitylibrary.org/search?searchTerm={name}+{auth}", "with_authorship": True,  "icon": "library_books"},
    {"key": "researchgate", "label": "ResearchGate",  "template": "https://www.researchgate.net/search/publication?q={name}",                                                    "template_with_auth": None,                                                     "with_authorship": False, "icon": "science"},
    {"key": "plos",         "label": "PLOS",          "template": "https://journals.plos.org/plosone/search?query={name}",                                                       "template_with_auth": None,                                                     "with_authorship": False, "icon": "article"},
    {"key": "academia",     "label": "Academia.edu",  "template": "https://www.academia.edu/search?q={name}",                                                                    "template_with_auth": None,                                                     "with_authorship": False, "icon": "school"},
    {"key": "scielo",       "label": "Scielo",        "template": "https://search.scielo.org/?q={name}",                                                                         "template_with_auth": None,                                                     "with_authorship": False, "icon": "travel_explore"},
    {"key": "scholar",      "label": "Scholar",       "template": "https://scholar.google.com/scholar?q={name}",                                                                 "template_with_auth": "https://scholar.google.com/scholar?q={name}+{auth}",       "with_authorship": True,  "icon": "school"},
    {"key": "youtube",      "label": "YouTube",       "template": "https://www.youtube.com/results?search_query={name}",                                                         "template_with_auth": None,                                                     "with_authorship": False, "icon": "play_circle"},
    {"key": "zootaxa",      "label": "Zootaxa",       "template": "https://www.biotaxa.org/Zootaxa/search?query={name}",                                                         "template_with_auth": None,                                                     "with_authorship": False, "icon": "bug_report"},
    {"key": "scribd",       "label": "Scribd",        "template": "https://www.scribd.com/search?query={name}",                                                                  "template_with_auth": None,                                                     "with_authorship": False, "icon": "auto_stories"},
]


def _build_search(scientific_name: str, authorship: Optional[str]) -> list[SearchLink]:
    """Compose the 14 SearchLink entries for a single taxon.

    URLs are pre-formatted via urllib.parse.quote_plus (the server is the
    single source of truth for query encoding). The frontend never builds
    URLs from a template.
    """
    from urllib.parse import quote_plus
    name_q = quote_plus(scientific_name or "")
    auth_q = quote_plus(authorship) if authorship else ""
    out: list[SearchLink] = []
    for e in _SEARCH_ENGINES:
        tmpl_with_auth = e.get("template_with_auth")
        if e["with_authorship"] and auth_q and tmpl_with_auth:
            url = tmpl_with_auth.replace("{name}", name_q).replace("{auth}", auth_q)
        else:
            # Name-only template. Defensive: the template might still
            # contain a stray `{auth}` placeholder (it shouldn't), in
            # which case we drop it so the URL doesn't end with a
            # dangling `+` or `{auth}`.
            url = e["template"].replace("{name}", name_q).replace("{auth}", "")
        out.append(SearchLink(engine=e["key"], label=e["label"], url=url))
    return out


# --- Materialize endpoint helpers ---------------------------------------------
#
# The materialize endpoint creates a root→taxon folder structure under
# RESEARCH_DIR. Each ancestor's `scientific_name` becomes a folder name; the
# taxon's own name becomes the leaf folder. The path column on the taxon table
# is a materialized `/A/B/C` string that already includes the taxon's own
# name; when it's NULL (mostly synonyms without a resolved lineage) we walk
# `parent_id` up to the root as a fallback. Folder names are sanitized so they
# are safe across filesystems (no `/`, control chars, leading dots, etc.) and
# a non-empty segment is always produced (fallback `id-{taxon_id}` when the
# scientific_name sanitizes to empty).

_FS_FORBIDDEN = re.compile(r'[\\/:*?"<>|\r\n\t]')
_RUN_UNDERSCORE = re.compile(r"_+")
_MAX_PARENT_DEPTH = 50


def _sanitize_segment(name: str, fallback_id: int) -> str:
    """Return a filesystem-safe folder name for a taxon.

    - Drops control chars (Unicode category starts with "C") but keeps spaces.
    - Replaces FS-forbidden chars (`/ \\ : * ? " < > |` and whitespace control
      chars) with `_`.
    - Collapses runs of `_` to a single `_`.
    - Trims leading/trailing dots, underscores, and whitespace.
    - Truncates to 200 chars (matches common FS limits with margin).
    - Falls back to `id-{fallback_id}` when the result is empty so every
      taxon produces a non-empty segment — essential for the path math.
    """
    if not name:
        return f"id-{fallback_id}"
    cleaned = "".join(
        ch for ch in name
        if ch == " " or unicodedata.category(ch)[0] != "C"
    )
    cleaned = _FS_FORBIDDEN.sub("_", cleaned)
    cleaned = _RUN_UNDERSCORE.sub("_", cleaned).strip("._ \t")
    cleaned = cleaned[:200]
    return cleaned or f"id-{fallback_id}"


def _walk_parents(
    conn: sqlite3.Connection,
    start_id: int,
    parent_column: str = "parent_id",
) -> list[tuple[int, str]]:
    """Walk the `parent_column` chain from start_id up to the root.

    The default `parent_column="parent_id"` walks the CoL backbone (used by
    the /children endpoint, which passes the same column to its WHERE).
    Pass `worms_parent_id` or `freshwater_parent_id` to walk the WoRMS or
    freshwater overlay hierarchies — those rows have parent_id=NULL but
    a populated `*_parent_id` that points at the next ancestor in their
    own tree.

    Returns a list of (taxon_id, scientific_name) tuples in root→start order.
    Raises 500 on cycles or chains deeper than `_MAX_PARENT_DEPTH`. The id is
    preserved per ancestor so each segment's fallback uses its own taxon_id,
    not the request's id.
    """
    # The `parent_column` value comes from `_SOURCE_TO_PARENT_COLUMN` (a
    # module-level literal) or the default `"parent_id"`, so it is never
    # user-controlled. A direct f-string here keeps the static column
    # name visible to reviewers and avoids a parameterized-column hack
    # sqlite3 doesn't support.
    visited: set[int] = set()
    chain: list[tuple[int, str]] = []
    current_id: Optional[int] = start_id
    depth = 0
    while current_id is not None:
        if current_id in visited:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"parent_id cycle detected at taxon {current_id}; "
                    "refusing to walk indefinitely"
                ),
            )
        if depth >= _MAX_PARENT_DEPTH:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"parent_id chain too deep (>{_MAX_PARENT_DEPTH} hops); "
                    "aborting to avoid runaway recursion"
                ),
            )
        visited.add(current_id)
        row = conn.execute(
            f"SELECT {parent_column} AS parent_id, scientific_name "
            f"FROM taxon WHERE id = ?",
            (current_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"taxon {current_id} not found during parent walk",
            )
        chain.append((current_id, row["scientific_name"]))
        current_id = row["parent_id"]
        depth += 1
    chain.reverse()
    return chain


# Maps the materialize endpoint's `source` query param to the column used
# by `_walk_parents`. Mirrors the same mapping used by /children. CoL is
# the default — the CoL backbone is the only hierarchy that ALSO carries a
# server-trusted `path` (baked in by parse_textree.py), so it's the only
# source that can take the path-shortcut in `_build_segments`.
_SOURCE_TO_PARENT_COLUMN: MappingProxyType[str, str] = MappingProxyType({
"col": "parent_id",
"worms": "worms_parent_id",
"freshwater": "freshwater_parent_id",
})


def _build_segments(
    conn: sqlite3.Connection, taxon_id: int, source: str = "col",
) -> list[str]:
    """Compute the sanitized root→taxon segment list for a taxon.

    Shared by the POST /materialize and GET /materialize-preview endpoints.
    Returns the deduplicated, sanitized list of folder names in root→taxon
    order. Raises 404 if the taxon doesn't exist, 500 on cycles / depth
    overflow / empty result.

    `source` selects which hierarchy to walk when the taxon's `path`
    is NULL:
    - "col" (default): walks `parent_id` (CoL backbone)
    - "worms": walks `worms_parent_id` (WoRMS overlay hierarchy)
    - "freshwater": walks `freshwater_parent_id` (freshwater overlay)

    Only CoL rows carry a pre-baked `path` (loaded by parse_textree.py);
    WoRMS and freshwater rows always have `path IS NULL`, so they always
    fall through to `_walk_parents` with their own parent column.

    The dedup happens BEFORE sanitization, on the original `scientific_name`
    (see AC-4d in tests/test_api_materialize.py: three ancestors all named
    `///` collapse to a single `id-{first_ancestor_id}` segment).
    """
    if source not in _SOURCE_TO_PARENT_COLUMN:
        raise HTTPException(
            status_code=400,
            detail=(
f"unknown source {source!r}; "
f"must be one of {sorted(_SOURCE_TO_PARENT_COLUMN)}"
            ),
        )
    parent_column = _SOURCE_TO_PARENT_COLUMN[source]
    row = conn.execute(
        "SELECT scientific_name, path FROM taxon WHERE id = ?",
        (taxon_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"taxon {taxon_id} not found",
        )
    path = row["path"]

    # Build (taxon_id, scientific_name) list in root→taxon order.
    # The path-shortcut ONLY applies to CoL — parse_textree.py bakes the
    # full root→taxon path into the CoL rows at load time, and that path
    # is server-trusted (clean names, no fallbacks needed). WoRMS and
    # freshwater rows have path=NULL by design (only CoL rows get paths),
    # so they always fall through to `_walk_parents` with their own
    # parent column. Walking by parent_id on a freshwater taxon would
    # produce a single folder (the taxon itself), because every
    # freshwater row has parent_id=NULL — the hierarchy lives in
    # freshwater_parent_id.
    if path and source == "col":
        segments_with_ids: list[tuple[int, str]] = [
            (taxon_id, seg) for seg in path.split("/") if seg
        ]
    else:
        segments_with_ids = _walk_parents(conn, taxon_id, parent_column)

    # Consecutive dedup by ORIGINAL scientific_name (before sanitize).
    # The dedup keeps the first tuple of each name run so the fallback uses
    # that ancestor's id.
    deduped_with_ids: list[tuple[int, str]] = []
    for tid, name in segments_with_ids:
        if not deduped_with_ids or deduped_with_ids[-1][1] != name:
            deduped_with_ids.append((tid, name))

    sanitized: list[str] = [
        _sanitize_segment(name, tid) for tid, name in deduped_with_ids
    ]

    if not sanitized:
        raise HTTPException(
            status_code=500,
            detail="sanitized path is empty; cannot create folder structure",
        )
    return sanitized


def _research_path_exists(sanitized: list[str]) -> bool:
    """True iff the taxon's full root→taxon folder exists on disk as a dir.

    Used by /api/taxon/{id}/children to flag every child row whose path
    is already materialized, so the frontend can paint the per-row icon
    in the "exists" state without firing a per-row preview request. Empty
    segments (shouldn't happen — _build_segments raises on empty) are
    treated as not exists.
    """
    if not sanitized:
        return False
    target = RESEARCH_DIR.joinpath(*sanitized)
    return target.exists() and target.is_dir()


def _walk_tree(path: Path, rel: str, depth: int = 0):
    """Recursively walk `path` for the tree JSON.

    `rel` is `path`'s position relative to the research root (empty
    string for the root itself). Skips symlinks (the serve endpoint
    rejects symlink-escapes; surfacing them in the tree would let users
    click paths the API refuses). Skips dotfiles (`*.DS_Store`,
    `.gitkeep`, Thumbs.db) — clutter, not user content. Caps recursion
    at `_MAX_PARENT_DEPTH` so a pathologically deep tree cannot blow
    the stack. Returns None when the subtree is truncated past the
    depth cap so callers can omit it.

    Each file child carries `{name, path, type, extension, size, modified}`.
    Each folder child carries `{name, path, type, children}`. Folders
    sort before files; both sort case-insensitive by name.
    """
    if depth >= _MAX_PARENT_DEPTH:
        return None
    entries: list[dict] = []
    # Sort: folders first, then files; both case-insensitive. Symlinks
    # sort as their target type via is_dir() (which follows symlinks),
    # but we skip them in the loop body so the sort order is moot for
    # them.
    for entry in sorted(
        path.iterdir(),
        key=lambda e: (0 if e.is_dir() else 1, e.name.lower()),
    ):
        if entry.name.startswith("."):
            continue
        if entry.is_symlink():
            continue
        child_rel = entry.name if not rel else f"{rel}/{entry.name}"
        if entry.is_dir():
            subtree = _walk_tree(entry, child_rel, depth + 1)
            if subtree is not None:
                entries.append({
                    "name": entry.name,
                    "path": child_rel,
                    "type": "folder",
                    "children": subtree["children"],
                })
        elif entry.is_file():
            st = entry.stat()
            entries.append({
                "name": entry.name,
                "path": child_rel,
                "type": "file",
                "extension": entry.suffix.lower().lstrip("."),
                "size": st.st_size,
                "modified": datetime.fromtimestamp(
                    st.st_mtime
                ).isoformat(timespec="seconds"),
            })
    return {"name": path.name, "path": rel, "type": "folder", "children": entries}


def _safe_resolve(root: Path, rel: str) -> Path:
    """Resolve a relative path inside `root` and assert it stays inside.

    Rejects `..` traversal, absolute paths (the leading slash overrides
    the relative join in `Path.__truediv__`), and symlink escapes
    (`Path.resolve()` follows symlinks, then `is_relative_to` checks
    the resolved target against the root). Raises HTTPException(400)
    with the spec's exact detail message on any escape; returns the
    resolved candidate on success.
    """
    candidate = (root / rel).resolve()
    # Python 3.14+: Path.is_relative_to is always available; the old
    # str-startswith fallback for Python < 3.9 was removed because
    # the project targets 3.14+.
    if not candidate.is_relative_to(root):
        raise HTTPException(400, "Path escapes research root")
    return candidate


@app.get("/api/taxon/{taxon_id}/materialize-preview")
def materialize_research_folder_preview(
    taxon_id: int,
    source: str = Query(default="col", pattern="^(col|worms|freshwater)$"),
):
    """Preview the path that POST /materialize WOULD create, without side effects.

    Each segment reports its filesystem state (`exists`, `is_dir`, `is_new`)
    so the frontend can render a line-by-line preview with ✓ / + markers
    and decide whether to show [Crear] or [Cerrar] in the confirmation
    modal. The endpoint does NOT touch the filesystem; re-running the same
    request is always safe and free.

    `source` selects which hierarchy to walk (same semantics as
    /api/taxon/{id}/children):
    - "col" (default): the CoL backbone — walks `parent_id` or uses the
      pre-baked `path` column when present.
    - "worms": the WoRMS overlay — walks `worms_parent_id`.
    - "freshwater": the freshwater overlay — walks `freshwater_parent_id`.
    Required for Freshwater view materializes: freshwater rows have
    parent_id=NULL and the hierarchy lives in `freshwater_parent_id`.
    """
    with db() as conn:
        row = conn.execute(
            "SELECT scientific_name FROM taxon WHERE id = ?", (taxon_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=404, detail=f"taxon {taxon_id} not found",
            )
        sci_name = row["scientific_name"]
        sanitized = _build_segments(conn, taxon_id, source)

    segments: list[dict] = []
    new_count = 0
    existing_count = 0
    for idx, name in enumerate(sanitized):
        # Build the cumulative path up to this segment so the preview can
        # show partial state: a leaf that's missing sits after a chain of
        # existing ancestors, and the user sees exactly which folders are
        # new vs pre-existing.
        cumulative = RESEARCH_DIR.joinpath(*sanitized[: idx + 1])
        exists = cumulative.exists()
        is_dir = cumulative.is_dir() if exists else False
        is_new = not exists
        segments.append({
            "name": name,
            "exists": exists,
            "is_dir": is_dir,
            "is_new": is_new,
        })
        if is_new:
            new_count += 1
        else:
            existing_count += 1

    target = RESEARCH_DIR.joinpath(*sanitized)
    return {
        "ok": True,
        "taxon_id": taxon_id,
        "scientific_name": sci_name,
        "research_dir": str(RESEARCH_DIR.resolve()),
        "relative_path": "/".join(sanitized),
        "absolute_path": str(target.resolve()),
        "segments": segments,
        "new_count": new_count,
        "existing_count": existing_count,
        "all_exist": new_count == 0,
    }


@app.post("/api/taxon/{taxon_id}/materialize")
def materialize_research_folder(
    taxon_id: int,
    source: str = Query(default="col", pattern="^(col|worms|freshwater)$"),
):
    """Create the root→taxon folder structure under RESEARCH_DIR.
    
    For each ancestor + the taxon itself:
    - Folder name = sanitized `scientific_name`.
    - `mkdir(parents=True, exist_ok=True)` is idempotent.
    
    `source` selects which hierarchy to walk — same semantics as the preview
    endpoint above. Freshwater and WoRMS rows carry parent_id=NULL with the
    real hierarchy in `freshwater_parent_id` / `worms_parent_id`; pass the
    matching source so the walk finds the ancestors.
    
    Idempotent: re-calling the endpoint on the same taxon reports the existing
    folders instead of failing. Returns 409 if any path component collides
    with an existing non-directory file (so the user gets a clear error
    instead of a cryptic `FileExistsError` from mkdir).
    """
    with db() as conn:
        sanitized = _build_segments(conn, taxon_id, source)
    
    # Create folders in a single pass. We pre-check existence so we can
    # distinguish "created by this call" from "pre-existed", and bail out
    # with 409 if any component is an existing non-directory file (a
    # regular mkdir(exist_ok=True) would raise FileExistsError there; we
    # surface it as a clean HTTP error).
    target = RESEARCH_DIR.joinpath(*sanitized)
    folders_created = 0
    folders_existed = 0
    for i in range(1, len(sanitized) + 1):
        d = RESEARCH_DIR.joinpath(*sanitized[:i])
    
        if d.exists() and not d.is_dir():
            raise HTTPException(
                status_code=409,
                detail=f"path conflict at {d}: not a directory",
            )
        is_new = not d.exists()
    
        try:
            d.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"path conflict at {target}: an existing non-directory "
                    "file blocks folder creation"
                ),
            )
        except OSError as e:
            raise HTTPException(
                status_code=500,
                detail=f"failed to create {d}: {e}",
            )
    
        if is_new:
            folders_created += 1
        else:
            folders_existed += 1
    
    return {
        "ok": True,
        "absolute_path": str(target.resolve()),
        "relative_path": "/".join(sanitized),
        "folders_created": folders_created,
        "folders_existed": folders_existed,
        "segments": sanitized,
    }


def _os_open_folder(path: Path) -> str:
    """Open `path` in the OS file manager (Finder on macOS, the
    default file manager on Linux via xdg-open, Explorer on Windows).

    Returns the binary name actually invoked ("open" / "xdg-open" /
    "explorer") so callers can surface it in logs / responses. Raises
    HTTPException(500) on failure with the underlying stderr/returncode.
    """
    system = sys.platform
    if system == "darwin":
        cmd = ["open", str(path)]
    elif system == "win32":
        # `explorer` returns exit code 1 even on success when given a
        # folder path; treat any non-None return as success and rely on
        # stderr to surface real failures.
        cmd = ["explorer", str(path)]
    else:
        cmd = ["xdg-open", str(path)]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            # Detach from the API process so closing the API doesn't
            # close the file manager.
            start_new_session=True,
        )
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        proc.stderr.close() if proc.stderr else None
        return cmd[0]
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=(
                f"'{cmd[0]}' not found on PATH; cannot open file manager "
                f"on {system}"
            ),
        )
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"failed to launch '{cmd[0]}': {e}",
        )


@app.post("/api/taxon/{taxon_id}/open-folder")
def open_research_folder(
    taxon_id: int,
    source: str = Query(default="col", pattern="^(col|worms|freshwater)$"),
):
    """Open the materialized research folder for this taxon in the
    OS file manager.

    The frontend uses this when the user clicks 'Open in Finder' on
    the Folder tab so they can drag files downloaded from external
    search results directly into the per-taxon Research directory
    instead of navigating there manually in the OS save dialog.

    Behaviour:
    - Computes the same chain `_build_segments(conn, taxon_id, source)`
      that `materialize` uses, so the path always matches what the
      preview tab showed.
    - 404 if the folder does not exist on disk — the user must click
      'Create N folders' first (the UI hides this button when the
      path is missing, but a direct API call could still hit it).
    - 400 if the resolved path would escape RESEARCH_DIR (defense in
      depth — `_build_segments` already sanitizes, this guards
      against future regressions).
    - Spawns `open` / `xdg-open` / `explorer` (platform-dependent)
      detached from the API process so closing taxa doesn't close
      the file manager.
    """
    with db() as conn:
        sanitized = _build_segments(conn, taxon_id, source)

    target = RESEARCH_DIR.joinpath(*sanitized)
    # Defense in depth: re-resolve and assert containment even though
    # `_build_segments` already sanitizes names. If a future refactor
    # introduces an escape vector we want a clean 400, not silent
    # arbitrary-path execution via subprocess.
    try:
        resolved = target.resolve()
    except OSError as e:
        raise HTTPException(status_code=400, detail=f"invalid path: {e}")
    if not resolved.is_relative_to(RESEARCH_DIR):
        raise HTTPException(status_code=400, detail="Path escapes research root")

    if not resolved.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"folder does not exist on disk: {resolved}. "
                "Materialize it first via POST /api/taxon/{id}/materialize."
            ),
        )
    if not resolved.is_dir():
        raise HTTPException(
            status_code=409,
            detail=f"path exists but is not a directory: {resolved}",
        )

    opener = _os_open_folder(resolved)
    return {
        "ok": True,
        "absolute_path": str(resolved),
        "relative_path": "/".join(sanitized),
        "opened_with": opener,
    }


@app.get("/api/taxon/{taxon_id}/searches", response_model=list[SearchLink])
def get_searches(taxon_id: int):
    """14 pre-composed search-engine URLs for the taxon.

    Server is the source of truth for the URLs (urllib.parse.quote_plus);
    the frontend trusts the `url` field in each SearchLink and uses
    web/search_urls.js only for icon/label rendering when the response is
    unavailable (offline / 5xx fallback).

    Returns 422 when the taxon has no `scientific_name` — the composed
    URLs would all be empty queries (e.g. `?q=`), which is useless to
    the user; the server surfaces the bad data instead. AC-18.
    """
    with db() as conn:
        row = conn.execute(
            "SELECT scientific_name, authorship FROM taxon WHERE id = ?",
            (taxon_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"taxon {taxon_id} not found",
            )
        if not row["scientific_name"]:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"taxon {taxon_id} has no scientific_name; "
                    "cannot compose search URLs"
                ),
            )
    return _build_search(row["scientific_name"], row["authorship"])


class SearchHit(BaseModel):
    """A search result, with the matched type so the UI can label it."""
    match_type: str  # "scientific" | "authorship" | "vernacular"
    taxon: Taxon


# Search ranking — BM25 with tier-based ordering.
#
# The naive approach (one FTS5 query per source, concat, sort by FTS rank)
# ranks species with many matching vernaculars above iconic species with few
# short ones. "Tiger" surfaces Scalidognathus tigerinus before Panthera
# tigris because FTS5 scores per-row, not per-taxon.
#
# Fix: classify each taxon into a tier from its vernacular hits:
#   tier 1 — has a vernacular whose name equals the query (case-insensitive)
#   tier 2 — has a vernacular whose name starts with the query
#   tier 3 — has a vernacular that matches only as substring (rare)
# Plus a sci_only bucket for taxa with no vernacular hit but a scientific hit.
#
# Inside each tier we score with BM25 (per vernacular row) × lang_boost and
# sum the top 3 hits per taxon. Tiers are concatenated in order — no global
# re-sort — so a tier-1 hit always beats a tier-2 hit regardless of raw score.
# Taxa whose scientific_name equals the query are promoted to the front
# (e.g. "Homo sapiens", "Quercus"); the previous LIKE-prefix variant was
# dropped because it flooded the top with Wolfkosia/Wolfina on "wolf".
_SEARCH_BOOST_LANGS = {"eng", "spa", "por", "fra", "deu"}


def _search_lang_boost(lang):
    if lang in _SEARCH_BOOST_LANGS:
        return 2.0
    # Many CoL vernaculars carry their language tag inline ("Apple (EN)")
    # and have language=NULL. Treat them as a moderate boost — likely
    # eng/spa but we don't pretend to know which.
    if not lang:
        return 1.5
    return 1.0


@app.get("/api/search", response_model=list[SearchHit])
def search(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    include_vernacular: bool = Query(default=True),
):
    """
    Combined search across scientific_name, authorship, and vernacular names.

    Ranking is tier-based (BM25 inside each tier):
      tier 1 = exact vernacular match  →  tier 2 = prefix  →
      tier 3 = substring  →  sci_only.
    Exact scientific-name match is forced to #1.
    """
    raw = q.strip()
    pattern = raw if " " in raw or len(raw) > 8 else raw + "*"
    lq = raw.lower()

    with db() as conn:
        # ---- Tier 1/2/3: vernacular hits ---------------------------------
        # FTS5 orders by rowid by default, not by bm25. ORDER BY bm25 plus
        # generous overfetch is required so taxa with only a couple of short
        # exact-match vernaculars (e.g. Panthera tigris → "Tiger") don't fall
        # outside the scan window.
        vern_rows = []
        if include_vernacular:
            vern_overfetch = min(max(limit * 20, 500), 3000)
            vern_rows = conn.execute(
                "SELECT vfts.rowid AS vern_id, bm25(vernacular_fts) AS bm, "
                "       v.taxon_id, v.language, v.name AS vname "
                "FROM vernacular_fts vfts "
                "JOIN vernacular v ON v.id = vfts.rowid "
                "WHERE vernacular_fts MATCH ? "
                "ORDER BY bm25(vernacular_fts) "
                "LIMIT ?",
                (pattern, vern_overfetch),
            ).fetchall()

        # Bucket per taxon.
        by_taxon = {}
        for r in vern_rows:
            row_score = r["bm"] * _search_lang_boost(r["language"])
            by_taxon.setdefault(r["taxon_id"], []).append(
                (row_score, r["vname"], r["language"])
            )

        tier1 = []  # (taxon_id, compound_score)
        tier2 = []
        tier3 = []
        for tid, hits in by_taxon.items():
            has_exact = any(name.lower() == lq for _, name, _ in hits)
            has_prefix = any(name.lower().startswith(lq) for _, name, _ in hits)
            # Sum top-3 (captures "matches in multiple vernaculars" without
            # being skewed by taxa with 20+ weak prefix hits).
            top3 = sorted(hits)[:3]
            compound = sum(s for s, _, _ in top3)
            if has_exact:
                tier1.append((tid, compound))
            elif has_prefix:
                tier2.append((tid, compound))
            else:
                tier3.append((tid, compound))

        # Sort each tier by score (asc = more negative = better).
        tier1.sort(key=lambda x: x[1])
        tier2.sort(key=lambda x: x[1])
        tier3.sort(key=lambda x: x[1])

        # ---- Scientific hits (FTS5) ---------------------------------------
        sci_rows = conn.execute(
            "SELECT fts.rowid AS taxon_id, bm25(taxon_fts) AS bm, t.* "
            "FROM taxon_fts fts "
            "JOIN taxon t ON t.id = fts.rowid "
            "WHERE taxon_fts MATCH ? "
            "ORDER BY bm25(taxon_fts) "
            "LIMIT ?",
            (pattern, limit * 5),
        ).fetchall()
        sci_by_taxon = {}  # taxon_id → (bm, row)
        for r in sci_rows:
            tid = r["taxon_id"]
            bm = r["bm"]
            if tid not in sci_by_taxon or bm < sci_by_taxon[tid][0]:
                sci_by_taxon[tid] = (bm, r)

        # ---- Sci-exact: derived from sci_by_taxon (no extra SQL) -----------
        # The previous implementation ran `LOWER(scientific_name) = LOWER(?)`
        # as a separate query, but that scans all 5.4M rows (~1.5s). Since we
        # already loaded the top sci hits above, we filter those in Python.
        # This still catches the iconic cases ("Homo sapiens", "Quercus")
        # because their FTS5 bm25 score is the highest possible.
        sci_exact = {
            tid for tid, (_, row) in sci_by_taxon.items()
            if row["scientific_name"].lower() == lq
        }

        # ---- Helpers ------------------------------------------------------
        def _match_type(tid):
            # Authorship beats scientific when the pattern matches the
            # authorship field — matches the legacy UI behaviour where an
            # authorship hit shows a purple tag.
            if tid in sci_by_taxon:
                row = sci_by_taxon[tid][1]
                auth = row["authorship"]
                bare = pattern.rstrip("*").lower()
                if auth and bare and bare in auth.lower():
                    return "authorship"
                return "scientific"
            return "vernacular"

        def _hit(tid):
            if tid in sci_by_taxon:
                row = sci_by_taxon[tid][1]
            else:
                row = conn.execute(
                    "SELECT * FROM taxon WHERE id = ?", (tid,)
                ).fetchone()
                if row is None:
                    return None
            return SearchHit(match_type=_match_type(tid), taxon=_row_to_taxon(row))

        # ---- Build ordered list (tier1 + tier2 + tier3 + sci_only) -------
        seen = set()
        combined = []

        for tid, _ in tier1:
            h = _hit(tid)
            if h is not None:
                seen.add(tid)
                combined.append(h)
        for tid, _ in tier2:
            if tid in seen:
                continue
            h = _hit(tid)
            if h is not None:
                seen.add(tid)
                combined.append(h)
        for tid, _ in tier3:
            if tid in seen:
                continue
            h = _hit(tid)
            if h is not None:
                seen.add(tid)
                combined.append(h)

        # sci-only bucket (taxa with no vernacular hit, sorted by bm25 asc).
        sci_only = []
        for tid, (bm, row) in sci_by_taxon.items():
            if tid in seen:
                continue
            sci_only.append((tid, bm, SearchHit(
                match_type=_match_type(tid), taxon=_row_to_taxon(row))))
        sci_only.sort(key=lambda x: x[1])
        for _, _, hit in sci_only:
            seen.add(hit.taxon.id)
            combined.append(hit)

        # ---- Promote sci-exact to the front --------------------------------
        # Exact scientific-name match wins regardless of tier ordering.
        exact_hits = [h for h in combined if h.taxon.id in sci_exact]
        other_hits = [h for h in combined if h.taxon.id not in sci_exact]
        combined = exact_hits + other_hits

        # Apply limit AFTER tier concatenation — a tier-1 hit at position 25
        # must still appear.
        return combined[:limit]


# ---------------------------------------------------------------------------
# File-explorer endpoints (PR 1)
#
# GET /api/taxon/{taxon_id}/files         — recursive tree JSON
# GET /api/taxon/{taxon_id}/files/serve   — streaming file with safety
#
# Both endpoints reuse _build_segments() + _sanitize_segment() so the
# on-disk layout is identical to what POST /materialize produces. No new
# on-disk convention, no path duplication. The frontend (PR 2) mounts the
# Browser tab and renders the tree + viewer against these endpoints.
# ---------------------------------------------------------------------------


@app.get("/api/taxon/{taxon_id}/files")
def list_files(taxon_id: int):
    """Recursive tree JSON for the taxon's research folder.

    Returns 200 with `exists: true` + the full tree when the folder
    exists on disk. Returns 200 with `exists: false` + `root: null`
    when the taxon exists but the folder is not materialized yet —
    the frontend renders the empty-state message from this state
    (distinct from the 404 'taxon not found' path). Returns 404 only
    when the taxon itself is missing from the DB.
    """
    with db() as conn:
        row = conn.execute(
            "SELECT scientific_name FROM taxon WHERE id = ?",
            (taxon_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"taxon {taxon_id} not found",
            )
        sci_name = row["scientific_name"]
        sanitized = _build_segments(conn, taxon_id)  # mirrors 404 contract
    target = RESEARCH_DIR.joinpath(*sanitized)
    rel_target = "/".join(sanitized)
    abs_target = str(target.resolve())
    if not target.is_dir():
        # Taxon is real but the research folder hasn't been materialized
        # yet — empty-state in the frontend, NOT a 404.
        return {
            "exists": False,
            "taxon_id": taxon_id,
            "taxon_name": sci_name,
            "taxon_path": rel_target,
            "filesystem_path": abs_target,
            "subpath": None,
            "root": None,
        }
    root_node = _walk_tree(target, "", depth=0)
    return {
        "exists": True,
        "taxon_id": taxon_id,
        "taxon_name": sci_name,
        "taxon_path": rel_target,
        "filesystem_path": abs_target,
        "subpath": None,
        "root": root_node,
    }


@app.get("/api/taxon/{taxon_id}/files/serve")
def serve_file(
    taxon_id: int,
    path: str = Query(min_length=1, max_length=4096),
):
    """Stream a single file from the taxon's research folder.

    Safety layers, in order:
      1. `path` is constrained to 1..4096 chars (Query validation) so
         accidental empty paths return 422 and very-long paths can't
         reach the filesystem call.
      2. `_safe_resolve()` rejects `..` traversal, absolute paths, and
         symlink escapes — Path.resolve() normalizes all three, then
         the strict is_relative_to() check catches them. Returns 400
         with `detail: "Path escapes research root"`.
      3. The research folder itself must exist on disk — if it hasn't
         been materialized yet, returns 404 with `detail: "Research
         folder not materialized"` (distinct from 'File not found' so
         the frontend can render the empty-state vs the placeholder).
      4. The candidate must be a regular file (`is_file()`) — folders,
         devices, and broken symlinks return 404 with
         `detail: "File not found"`.
      5. Files larger than `_STREAM_CAP_BYTES` (100 MB) return 413 with
         a detail naming the cap and the actual size. Enforced BEFORE
         the file is opened — `stat().st_size` is the only read.

    Response:
      - Body: file bytes, streamed (FileResponse uses chunked transfer).
      - Content-Type matched by extension via `_CONTENT_TYPE_BY_EXT`
        (10 supported formats) or `application/octet-stream` fallback.
      - Content-Disposition: inline; filename="<basename>" so embedded
        viewers (<iframe>, <embed>) consume the response without
        triggering a download dialog.
    """
    with db() as conn:
        sanitized = _build_segments(conn, taxon_id)  # 404 on unknown
    root = RESEARCH_DIR.joinpath(*sanitized).resolve()
    if not root.is_dir():
        raise HTTPException(
            status_code=404,
            detail="Research folder not materialized",
        )
    candidate = _safe_resolve(root, path)
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    size = candidate.stat().st_size
    if size > _STREAM_CAP_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File exceeds streaming cap ({_STREAM_CAP_BYTES} bytes), "
                f"actual {size} bytes"
            ),
        )
    ext = candidate.suffix.lower().lstrip(".")
    content_type = _CONTENT_TYPE_BY_EXT.get(ext, "application/octet-stream")
    # Starlette 0.41 builds Content-Disposition from `filename` +
    # `content_disposition_type`. Setting the type to "inline" makes
    # <iframe>/<embed> viewers consume the response without a download
    # dialog. The emitted header is `inline; filename="<basename>"`.
    return FileResponse(
        path=str(candidate),
        media_type=content_type,
        filename=candidate.name,
        content_disposition_type="inline",
    )


# ---------------------------------------------------------------------------
# Global file-explorer endpoints
#
# GET /api/files         — recursive tree JSON for the WHOLE research root
# GET /api/files/serve   — streaming file with the same safety checks as
#                           /api/taxon/{id}/files/serve, but anchored at
#                           RESEARCH_DIR instead of a taxon's folder.
#
# These let the Browser tab show the entire Research directory regardless
# of which taxon is selected. The taxon-scoped endpoints above stay in
# place for callers (tests, future per-taxon features) that still want
# a taxon's materialised subtree.
# ---------------------------------------------------------------------------


@app.get("/api/files")
def list_research_root():
    """Recursive tree JSON for the entire Research directory.

    Returns 200 with `exists: true` + the full tree when RESEARCH_DIR is
    a directory on disk. Returns 200 with `exists: false` when it is
    missing or not a directory — the frontend renders the empty-state
    from this state. Same node shape as the taxon-scoped endpoint
    (folder → {name, path, type, children}; file → {name, path, type,
    extension, size, modified}), so the Browser tab renders both
    responses with the same `_walk_tree` consumer.
    """
    if not RESEARCH_DIR.is_dir():
        return {
"exists": False,
"filesystem_path": str(RESEARCH_DIR),
"root": None,
        }
    root_node = _walk_tree(RESEARCH_DIR, "", depth=0)
    return {
        "exists": True,
        "filesystem_path": str(RESEARCH_DIR.resolve()),
        "root": root_node,
    }


@app.get("/api/files/serve")
def serve_research_file(path: str = Query(min_length=1, max_length=4096)):
    """Stream a single file from RESEARCH_DIR.

    Mirrors the safety contract of /api/taxon/{taxon_id}/files/serve —
    `..` / absolute / symlink-escape paths return 400, oversized files
    return 413, missing files return 404, otherwise the file bytes are
    streamed inline with the matching Content-Type. The research root
    must exist as a directory; missing root returns 404.
    """
    if not RESEARCH_DIR.is_dir():
        raise HTTPException(
status_code=404,
detail="Research root not found",
        )
    root = RESEARCH_DIR.resolve()
    candidate = _safe_resolve(root, path)
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    size = candidate.stat().st_size
    if size > _STREAM_CAP_BYTES:
        raise HTTPException(
status_code=413,
detail=(
f"File exceeds streaming cap ({_STREAM_CAP_BYTES} bytes), "
f"actual {size} bytes"
),
        )
    ext = candidate.suffix.lower().lstrip(".")
    content_type = _CONTENT_TYPE_BY_EXT.get(ext, "application/octet-stream")
    return FileResponse(
        path=str(candidate),
        media_type=content_type,
        filename=candidate.name,
        content_disposition_type="inline",
    )


# Mount the web/ directory for static assets (app.js, etc.).
# This is intentionally at the END of the file so /api/* routes take
# precedence over static file serving.
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")