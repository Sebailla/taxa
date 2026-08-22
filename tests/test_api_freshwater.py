"""
Tests for the freshwater API extensions and /searches endpoint — AC-8..AC-19.

Each test runs against an in-memory SQLite (mirroring the production schema)
seeded with fixture rows. The `api.server.db` function is monkey-patched so
the API hits the in-memory DB instead of data/db/taxa.db.

The fixture uses SQLite's URI + cache=shared mode so the seeding connection
and the API's per-request connections all see the same in-memory database.
This is necessary because the real `db()` returns a fresh connection each
call, and `sqlite3.Connection.__exit__` closes the connection on block exit.

Run:
    pytest tests/test_api_freshwater.py -v
"""
from __future__ import annotations

import sqlite3
import uuid
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from api.server import app


# Schema mirrors etl/tests/conftest.py::BASE_SCHEMA (v1+v2+v3 with freshwater
# overlay columns). Kept inline so this file is self-contained and doesn't
# depend on the loader's test fixtures.
SCHEMA = """
CREATE TABLE taxon (
    id                   INTEGER PRIMARY KEY,
    parent_id            INTEGER REFERENCES taxon(id) ON DELETE CASCADE,
    rank                 TEXT    NOT NULL,
    status               TEXT    NOT NULL,
    scientific_name      TEXT    NOT NULL,
    authorship           TEXT,
    path                 TEXT,
    species_count        INTEGER,
    accepted_id          INTEGER REFERENCES taxon(id),
    is_extinct           INTEGER NOT NULL DEFAULT 0,
    coldp_id             TEXT,
    worms_id             INTEGER,
    worms_parent_id      INTEGER,
    freshwater_id        INTEGER,
    freshwater_parent_id INTEGER
);
CREATE TABLE vernacular (
    id        INTEGER PRIMARY KEY,
    taxon_id  INTEGER REFERENCES taxon(id) ON DELETE CASCADE,
    name      TEXT    NOT NULL,
    language  TEXT,
    country   TEXT
);
"""


@pytest.fixture
def db_and_client(monkeypatch):
    """Yield a (conn, client) pair. The conn is the in-memory DB the API uses.

    Tests seed `conn` directly via `_insert`, then exercise `client` to hit
    the API. The patched `db()` returns a fresh connection to the same
    shared-cache in-memory DB on every call, so the API's per-request
    connection lifecycle (open → query → close) doesn't strand the seed data.

    SQLite URI + cache=shared is the documented way to share an in-memory
    database across multiple connections: see https://www.sqlite.org/inmemorydb.html
    """
    db_uri = f"file:test_db_{uuid.uuid4().hex}?mode=memory&cache=shared"
    conn = sqlite3.connect(db_uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()

    def fake_db():
        c = sqlite3.connect(db_uri, uri=True)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr("api.server.db", fake_db)
    yield conn, TestClient(app)

    conn.close()


def _insert(conn, **fields):
    """Insert a taxon row with explicit field defaults. Returns the new id."""
    defaults = {
        "parent_id": None,
        "rank": "species",
        "status": "accepted",
        "scientific_name": "Unknown",
        "authorship": None,
        "path": None,
        "species_count": None,
        "accepted_id": None,
        "is_extinct": 0,
        "coldp_id": None,
        "worms_id": None,
        "freshwater_id": None,
        "freshwater_parent_id": None,
    }
    defaults.update(fields)
    cols = ", ".join(defaults.keys())
    placeholders = ", ".join("?" * len(defaults))
    cur = conn.execute(
        f"INSERT INTO taxon ({cols}) VALUES ({placeholders})",
        list(defaults.values()),
    )
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# AC-8 / AC-9 — /api/domains
# ---------------------------------------------------------------------------


def test_domains_without_freshwater(db_and_client):
    """AC-8: GET /api/domains against a DB with CoL+WoRMS only (no freshwater)
    returns the 5 known roots and no row with freshwater_id set."""
    conn, client = db_and_client
    _insert(conn, scientific_name="Archaea", rank="domain", coldp_id="col-arch")
    _insert(conn, scientific_name="Bacteria", rank="domain", coldp_id="col-bact")
    _insert(conn, scientific_name="Biota", rank="superdomain", worms_id=1)
    _insert(conn, scientific_name="Eukaryota", rank="domain", coldp_id="col-euk")
    _insert(conn, scientific_name="Viruses", rank="domain", coldp_id="col-vir")
    resp = client.get("/api/domains")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 5, f"expected 5 roots, got {len(body)}: {body}"
    names = {t["scientific_name"] for t in body}
    assert names == {"Archaea", "Bacteria", "Biota", "Eukaryota", "Viruses"}
    # No row should have freshwater_id set.
    assert all(t["freshwater_id"] is None for t in body), (
        f"no domain row should have freshwater_id set: {body}"
    )


def test_domains_with_freshwater(db_and_client):
    """AC-9: GET /api/domains against a DB with the synthetic root inserted
    returns 6 roots including 'Freshwater Fishes'."""
    conn, client = db_and_client
    _insert(conn, scientific_name="Archaea", rank="domain", coldp_id="col-arch")
    _insert(conn, scientific_name="Bacteria", rank="domain", coldp_id="col-bact")
    _insert(conn, scientific_name="Biota", rank="superdomain", worms_id=1)
    _insert(conn, scientific_name="Eukaryota", rank="domain", coldp_id="col-euk")
    _insert(conn, scientific_name="Viruses", rank="domain", coldp_id="col-vir")
    _insert(
        conn,
        scientific_name="Freshwater Fishes",
        rank="collection",
        freshwater_id=1,
        freshwater_parent_id=None,
    )
    resp = client.get("/api/domains")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 6, f"expected 6 roots, got {len(body)}: {body}"
    names = {t["scientific_name"] for t in body}
    assert "Freshwater Fishes" in names, (
        f"Freshwater Fishes missing from roots: {names}"
    )
    fw_row = next(t for t in body if t["scientific_name"] == "Freshwater Fishes")
    assert fw_row["freshwater_id"] == 1
    assert fw_row["freshwater_parent_id"] is None
    assert fw_row["rank"] == "collection"


# ---------------------------------------------------------------------------
# AC-10 / AC-11 / AC-12 — /api/taxon/{id}/children source filter
# ---------------------------------------------------------------------------


def test_children_source_freshwater(db_and_client):
    """AC-10: GET /api/taxon/{root_id}/children?source=freshwater returns the
    freshwater children of the synthetic root, ordered by RANK_ORDER then name.
    Every returned row has freshwater_id IS NOT NULL and freshwater_parent_id
    equal to the synthetic root's id."""
    conn, client = db_and_client
    root_id = _insert(
        conn,
        scientific_name="Freshwater Fishes",
        rank="collection",
        freshwater_id=1,
    )
    _insert(
        conn,
        scientific_name="Characiformes",
        rank="order",
        freshwater_id=10,
        freshwater_parent_id=root_id,
    )
    _insert(
        conn,
        scientific_name="Siluriformes",
        rank="order",
        freshwater_id=11,
        freshwater_parent_id=root_id,
    )
    resp = client.get(f"/api/taxon/{root_id}/children?source=freshwater&limit=200")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 2, f"expected 2 children, got {len(body)}: {body}"
    names = [t["scientific_name"] for t in body]
    # Both are rank=order, same RANK_ORDER value — sorted by name.
    assert names == ["Characiformes", "Siluriformes"], names
    for t in body:
        assert t["freshwater_id"] is not None, (
            f"freshwater child must have freshwater_id set: {t}"
        )
        assert t["freshwater_parent_id"] == root_id, (
            f"freshwater child must point at root: {t}"
        )


def test_children_source_col_with_freshwater_root(db_and_client):
    """AC-11: source=col on the synthetic freshwater root returns an empty list
    (the root has parent_id IS NULL, so there are no CoL children to walk)."""
    conn, client = db_and_client
    root_id = _insert(
        conn,
        scientific_name="Freshwater Fishes",
        rank="collection",
        freshwater_id=1,
    )
    resp = client.get(f"/api/taxon/{root_id}/children?source=col&limit=200")
    assert resp.status_code == 200
    assert resp.json() == []


def test_children_source_worms_with_freshwater_root(db_and_client):
    """AC-12: source=worms on the synthetic freshwater root returns an empty
    list (the root has no worms_parent_id)."""
    conn, client = db_and_client
    root_id = _insert(
        conn,
        scientific_name="Freshwater Fishes",
        rank="collection",
        freshwater_id=1,
    )
    resp = client.get(f"/api/taxon/{root_id}/children?source=worms&limit=200")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# AC-13 / AC-14 — /api/taxon/{id} includes new optional fields
# ---------------------------------------------------------------------------


def test_taxon_includes_freshwater_id(db_and_client):
    """AC-13: GET /api/taxon/{id} for a freshwater-loaded species returns
    freshwater_id and freshwater_parent_id set; parent_id is None (freshwater
    rows live in their own hierarchy, not in the CoL backbone)."""
    conn, client = db_and_client
    root_id = _insert(
        conn,
        scientific_name="Freshwater Fishes",
        rank="collection",
        freshwater_id=1,
    )
    family_id = _insert(
        conn,
        scientific_name="Characidae",
        rank="family",
        freshwater_id=100,
        freshwater_parent_id=root_id,
    )
    species_id = _insert(
        conn,
        scientific_name="Astyanax mexicanus",
        authorship="(De Filippi, 1853)",
        rank="species",
        freshwater_id=42,
        freshwater_parent_id=family_id,
    )
    resp = client.get(f"/api/taxon/{species_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["freshwater_id"] == 42, body
    assert body["freshwater_parent_id"] == family_id, body
    assert body["parent_id"] is None, (
        f"freshwater rows must have parent_id=NULL: {body}"
    )


def test_taxon_without_freshwater_id(db_and_client):
    """AC-14: GET /api/taxon/{id} for a CoL-only taxon returns
    freshwater_id=None and freshwater_parent_id=None (the new optional fields
    default to null for legacy rows)."""
    conn, client = db_and_client
    col_id = _insert(
        conn,
        scientific_name="Homo sapiens",
        authorship="Linnaeus, 1758",
        rank="species",
        coldp_id="col-homo-sapiens",
    )
    resp = client.get(f"/api/taxon/{col_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["freshwater_id"] is None, body
    assert body["freshwater_parent_id"] is None, body


# ---------------------------------------------------------------------------
# AC-15 / AC-16 / AC-17 / AC-18 / AC-19 — /api/taxon/{id}/searches
# ---------------------------------------------------------------------------


def test_searches_returns_14_entries(db_and_client):
    """AC-15: GET /api/taxon/{homo_sapiens_id}/searches returns exactly 14
    entries in the fixed order from spec.md §6.1. Every entry has engine,
    label, and url fields."""
    conn, client = db_and_client
    homo_id = _insert(
        conn,
        scientific_name="Homo sapiens",
        authorship="Linnaeus, 1758",
        rank="species",
        coldp_id="col-homo-sapiens",
    )
    resp = client.get(f"/api/taxon/{homo_id}/searches")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 14, f"expected 14 entries, got {len(body)}"
    expected_keys = [
        "google", "imagen", "documentos", "pdf", "wikipedia", "bhl",
        "researchgate", "plos", "academia", "scielo", "scholar",
        "youtube", "zootaxa", "scribd",
    ]
    actual_keys = [e["engine"] for e in body]
    assert actual_keys == expected_keys, (
        f"engine order drift:\n  expected: {expected_keys}\n  actual:   {actual_keys}"
    )
    # Every entry has the three required fields.
    for e in body:
        assert "engine" in e and e["engine"], f"missing engine: {e}"
        assert "label" in e and e["label"], f"missing label: {e}"
        assert "url" in e and e["url"], f"missing url: {e}"


def test_searches_urls_are_well_formed(db_and_client):
    """AC-16: All 14 URLs parse cleanly with urlparse (scheme is http/https,
    host is non-empty) and the scientific_name appears somewhere in the URL."""
    conn, client = db_and_client
    homo_id = _insert(
        conn,
        scientific_name="Homo sapiens",
        rank="species",
        coldp_id="col-homo",
    )
    resp = client.get(f"/api/taxon/{homo_id}/searches")
    assert resp.status_code == 200
    for entry in resp.json():
        u = urlparse(entry["url"])
        assert u.scheme in ("http", "https"), (
            f"bad scheme for {entry['engine']}: {entry['url']}"
        )
        assert u.netloc, f"missing host for {entry['engine']}: {entry['url']}"
        # The server uses urllib.parse.quote_plus, so spaces are encoded
        # as `+` (form-urlencoded style). Either `+` or `%20` is technically
        # valid; we accept both because the spec is loose on this.
        encoded = "Homo+sapiens"
        assert encoded in entry["url"] or "Homo%20sapiens" in entry["url"], (
            f"scientific_name missing from URL for {entry['engine']}: {entry['url']}"
        )


def test_searches_with_authorship(db_and_client):
    """AC-17: For 'Astyanax mexicanus (De Filippi, 1853)':
    - bhl.url contains the authorship substring (De+Filippi or De%20Filippi)
    - scholar.url contains the authorship substring
    - google.url does NOT contain the authorship substring
    """
    conn, client = db_and_client
    asty_id = _insert(
        conn,
        scientific_name="Astyanax mexicanus",
        authorship="(De Filippi, 1853)",
        rank="species",
        freshwater_id=42,
    )
    resp = client.get(f"/api/taxon/{asty_id}/searches")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    by_engine = {e["engine"]: e["url"] for e in body}
    # The server uses urllib.parse.quote_plus, so spaces become `+`. The
    # authorship substring is either `De+Filippi` or `De%20Filippi`.
    auth_marker = "De+Filippi"
    assert auth_marker in by_engine["bhl"] or "De%20Filippi" in by_engine["bhl"], (
        f"bhl URL should contain authorship: {by_engine['bhl']}"
    )
    assert auth_marker in by_engine["scholar"] or "De%20Filippi" in by_engine["scholar"], (
        f"scholar URL should contain authorship: {by_engine['scholar']}"
    )
    assert auth_marker not in by_engine["google"], (
        f"google URL should NOT contain authorship: {by_engine['google']}"
    )
    assert "De%20Filippi" not in by_engine["google"], (
        f"google URL should NOT contain authorship: {by_engine['google']}"
    )


def test_searches_url_encoding(db_and_client):
    """AC-18: Special characters in scientific_name (spaces, dots, parentheses)
    are URL-encoded correctly in every entry. The plain ASCII name with
    spaces and a period is the canonical test (the API uses quote_plus,
    so spaces become `+`)."""
    conn, client = db_and_client
    weird_id = _insert(
        conn,
        scientific_name="Homo sapiens subsp. typicus",
        rank="subspecies",
        coldp_id="col-weird",
    )
    resp = client.get(f"/api/taxon/{weird_id}/searches")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    by_engine = {e["engine"]: e["url"] for e in body}
    # The server uses urllib.parse.quote_plus, so spaces → `+`, dots preserved.
    expected_plus = "Homo+sapiens+subsp.+typicus"
    expected_pct = "Homo%20sapiens%20subsp.%20typicus"
    assert expected_plus in by_engine["google"] or expected_pct in by_engine["google"], (
        f"google URL should encode spaces: {by_engine['google']}"
    )
    # bhl URL should also have the same encoding for the name portion.
    assert expected_plus in by_engine["bhl"] or expected_pct in by_engine["bhl"], (
        f"bhl URL should encode spaces: {by_engine['bhl']}"
    )


def test_searches_404_for_unknown_taxon(db_and_client):
    """AC-19: GET /api/taxon/999999999/searches returns 404 with a 'detail'
    field that names the missing id (consistent shape with the rest of the
    API: detail mentions the taxon id)."""
    conn, client = db_and_client
    resp = client.get("/api/taxon/999999999/searches")
    assert resp.status_code == 404
    body = resp.json()
    assert "999999999" in body.get("detail", ""), (
        f"detail should name the missing taxon id: {body}"
    )
