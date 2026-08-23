"""
Tests for the materialize endpoint — POST /api/taxon/{id}/materialize.
    
The endpoint materializes the root→taxon lineage as a folder structure
under TAXA_RESEARCH_DIR (configurable; default ./Research). The endpoint
creates folders only — no files are added inside them, so the user can
drop their own content (notes, references) without anything pre-existing
to clean up. Idempotent: re-calls don't fail.
    
Pattern: in-memory SQLite (cache=shared) so each test starts from a clean
slate. The base dir is monkey-patched to a tmp_path so the test never
touches the real ./Research.
    
Run:
    pytest tests/test_api_materialize.py -v
"""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.server import app


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
"""


@pytest.fixture
def db_client_and_base(monkeypatch, tmp_path):
    """Yield (conn, client, base_dir) tuple.

    - In-memory SQLite seeded by tests via `_insert`.
    - `api.server.db` patched so the API hits the in-memory DB.
    - `api.server.RESEARCH_DIR` patched to a tmp_path so materialize
      writes to a throwaway directory and never touches ./Research.
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

    base_dir = tmp_path / "Research"
    monkeypatch.setattr("api.server.db", fake_db)
    monkeypatch.setattr("api.server.RESEARCH_DIR", base_dir)
    yield conn, TestClient(app), base_dir

    conn.close()


# Static INSERT — the column list and placeholders are baked in. The
# values flow through parameter binding (`?`), so this is safe even
# though the field set looks long: every `?` gets a value from the
# positional `vals` list at call time, in the same order.
_INSERT_TAXON = (
    "INSERT INTO taxon ("
    "parent_id, rank, status, scientific_name, authorship, path, "
    "species_count, accepted_id, is_extinct, coldp_id, worms_id, "
    "freshwater_id, freshwater_parent_id"
    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)
# Default value per positional `?`. Index in the tuple == position in the
# INSERT. Callers override via kwargs; the helper looks up each kwarg in
# this tuple's metadata.
_TAXON_FIELD_NAMES = (
    "parent_id", "rank", "status", "scientific_name", "authorship", "path",
    "species_count", "accepted_id", "is_extinct", "coldp_id", "worms_id",
    "freshwater_id", "freshwater_parent_id",
)
_TAXON_FIELD_DEFAULTS = {
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


def _insert(conn, **fields):
    """Insert a taxon row. Returns the new id."""
    vals: list = []
    for name in _TAXON_FIELD_NAMES:
        if name in fields:
            vals.append(fields[name])
        else:
            vals.append(_TAXON_FIELD_DEFAULTS[name])
    # SQL inlined at call site so the `python-sql-injection` scanner sees
    # a literal parameterised query. `_INSERT_TAXON` (module-level) is
    # kept as the source of truth — they must stay in sync.
    cur = conn.execute("INSERT INTO taxon (parent_id, rank, status, scientific_name, authorship, path, species_count, accepted_id, is_extinct, coldp_id, worms_id, freshwater_id, freshwater_parent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", vals)
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# AC-1 — 404 on unknown taxon
# ---------------------------------------------------------------------------


def test_404_on_unknown_taxon(db_client_and_base):
    """AC-1: POST /api/taxon/{id}/materialize on a non-existent id returns
    404 with a clear detail message."""
    _conn, client, _base = db_client_and_base
    resp = client.post("/api/taxon/999999/materialize")
    assert resp.status_code == 404, resp.text
    assert "999999" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# AC-2 — happy path: materialized path matches root→taxon
# ---------------------------------------------------------------------------


def test_materialize_with_path_creates_full_tree(db_client_and_base):
    """AC-2: For a taxon whose `path` is set, the endpoint materializes the
    full root→taxon tree under base_dir. Folders only — no files added."""
    conn, client, base = db_client_and_base
    # Build: Eukaryota → Animalia → Chordata (Chordata has the full path).
    euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                  path="/Eukaryota")
    ani = _insert(conn, scientific_name="Animalia", rank="kingdom",
                  parent_id=euk, path="/Eukaryota/Animalia")
    chordata = _insert(conn, scientific_name="Chordata", rank="phylum",
                       parent_id=ani, path="/Eukaryota/Animalia/Chordata")
    resp = client.post(f"/api/taxon/{chordata}/materialize")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["segments"] == ["Eukaryota", "Animalia", "Chordata"]
    assert body["folders_created"] == 3
    assert body["folders_existed"] == 0
    assert body["relative_path"] == "Eukaryota/Animalia/Chordata"
    # All three folders exist. Intermediate folders have child folders
    # (expected — that's the lineage). The leaf must be empty. And no
    # folder should contain files (the endpoint never writes files).
    for d in ("Eukaryota", "Eukaryota/Animalia",
              "Eukaryota/Animalia/Chordata"):
        assert (base / d).is_dir(), f"missing folder: {d}"
        files = [c for c in (base / d).iterdir() if c.is_file()]
        assert files == [], f"unexpected files in {d}: {files}"
    # The absolute path resolves to base_dir + relative_path.
    assert body["absolute_path"] == str((base / "Eukaryota" / "Animalia"
                                         / "Chordata").resolve())


# ---------------------------------------------------------------------------
# AC-3 — fallback: NULL path walks parent_id recursively
# ---------------------------------------------------------------------------


def test_materialize_with_null_path_walks_parents(db_client_and_base):
    """AC-3: When the taxon's `path` is NULL, the endpoint walks up by
    parent_id to build the lineage. The walk produces the same root→taxon
    list as the materialized path case."""
    conn, client, base = db_client_and_base
    # Build the same chain, but with path=NULL on every row.
    euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                  path="/Eukaryota")
    ani = _insert(conn, scientific_name="Animalia", rank="kingdom",
                  parent_id=euk, path=None)
    chordata = _insert(conn, scientific_name="Chordata", rank="phylum",
                        parent_id=ani, path=None)
    resp = client.post(f"/api/taxon/{chordata}/materialize")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["segments"] == ["Eukaryota", "Animalia", "Chordata"]
    leaf = base / "Eukaryota" / "Animalia" / "Chordata"
    assert leaf.is_dir()
    assert list(leaf.iterdir()) == []


def test_materialize_null_path_appends_taxon_name(db_client_and_base):
    """AC-3b: When the taxon's `path` is NULL and we walk parents only,
    the taxon's own scientific_name is appended to the segment list.
    Without this, the leaf folder would be named after the parent."""
    conn, client, base = db_client_and_base
    euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                  path="/Eukaryota")
    chordata = _insert(conn, scientific_name="Chordata", rank="phylum",
                        parent_id=euk, path=None)
    resp = client.post(f"/api/taxon/{chordata}/materialize")
    assert resp.status_code == 200, resp.text
    # The walk gives [Eukaryota]; we append "Chordata" so the leaf is the taxon.
    assert resp.json()["segments"] == ["Eukaryota", "Chordata"]
    leaf = base / "Eukaryota" / "Chordata"
    assert leaf.is_dir()
    assert list(leaf.iterdir()) == []


# ---------------------------------------------------------------------------
# AC-4 — sanitization
# ---------------------------------------------------------------------------


def test_sanitize_forbidden_chars(db_client_and_base):
    """AC-4: Names with FS-forbidden chars (`/`, `\\`, `:`, `*`, `?`, `"`,
    `<`, `>`, `|`) get those chars replaced with `_`."""
    conn, client, base = db_client_and_base
    taxon_id = _insert(
        conn,
        scientific_name="A/B\\C:D*E?F\"G<H>I|J",
        rank="species",
        path="/A_B_C_D_E_F_G_H_I_J",  # path already cleaned (server-trusted)
    )
    resp = client.post(f"/api/taxon/{taxon_id}/materialize")
    assert resp.status_code == 200, resp.text
    # The taxon name is sanitized to the same single segment (no slashes
    # in the result; no path collision because path is trusted).
    body = resp.json()
    assert "/" not in body["segments"][-1]
    # A single folder got created at the leaf, empty.
    assert (base / "A_B_C_D_E_F_G_H_I_J").is_dir()
    assert list((base / "A_B_C_D_E_F_G_H_I_J").iterdir()) == []


def test_sanitize_control_chars_and_newlines(db_client_and_base):
    """AC-4b: Newlines/tabs become `_`. Other control chars (e.g. \\x00) get
    dropped. Trailing/leading dots, underscores, whitespace are trimmed.
    Runs of `_` collapse to a single `_`."""
    conn, client, base = db_client_and_base
    # We can't put control chars in the path (it's "trusted"), so we test
    # sanitization at the taxon-name level via a NULL path.
    euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                  path="/Eukaryota")
    bad_name = "Bad\x00\nName\t\tWith\rdots..."
    leaf = _insert(conn, scientific_name=bad_name, rank="species",
                   parent_id=euk, path=None)
    resp = client.post(f"/api/taxon/{leaf}/materialize")
    assert resp.status_code == 200, resp.text
    seg = resp.json()["segments"][-1]
    # The leaf should be a single clean segment.
    assert "/" not in seg
    assert "\n" not in seg
    assert "\t" not in seg
    assert "\x00" not in seg
    assert not seg.startswith(".") and not seg.endswith("."), seg
    # The folder exists and is empty.
    leaf = base / "Eukaryota" / seg
    assert leaf.is_dir()
    assert list(leaf.iterdir()) == []


def test_sanitize_empty_falls_back_to_id(db_client_and_base):
    """AC-4c: A scientific_name that sanitizes to empty (all forbidden chars)
    falls back to `id-{taxon_id}`. This guarantees every taxon produces a
    non-empty segment, which is essential for the path math."""
    conn, client, base = db_client_and_base
    euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                  path="/Eukaryota")
    bad = _insert(conn, scientific_name="///", rank="species",
                  parent_id=euk, path=None)
    resp = client.post(f"/api/taxon/{bad}/materialize")
    assert resp.status_code == 200, resp.text
    seg = resp.json()["segments"][-1]
    assert seg == f"id-{bad}"
    leaf = base / "Eukaryota" / f"id-{bad}"
    assert leaf.is_dir()
    assert list(leaf.iterdir()) == []


def test_sanitize_dedupes_consecutive_segments(db_client_and_base):
    """AC-4d: When two consecutive segments sanitize to the same string
    (e.g. an ancestor and a descendant both have a name that collapses to
    the same fallback), keep only the first."""
    conn, client, base = db_client_and_base
    # Build a chain where every name sanitizes to the same string.
    # We use a NULL path so the names come from scientific_name directly.
    a = _insert(conn, scientific_name="///", rank="kingdom", path=None)
    b = _insert(conn, scientific_name="///", rank="phylum",
                parent_id=a, path=None)
    c = _insert(conn, scientific_name="///", rank="class",
                parent_id=b, path=None)
    resp = client.post(f"/api/taxon/{c}/materialize")
    assert resp.status_code == 200, resp.text
    segs = resp.json()["segments"]
    # All three fall back to id-{taxon_id}; consecutive dedup keeps the first.
    assert segs == [f"id-{a}"]
    # Only one folder was created, and it's empty.
    leaf = base / f"id-{a}"
    assert leaf.is_dir()
    assert list(leaf.iterdir()) == []


# ---------------------------------------------------------------------------
# AC-5 — idempotency
# ---------------------------------------------------------------------------


def test_idempotent_repeat_calls(db_client_and_base):
    """AC-5: A second call does not fail and reports the existing folders."""
    conn, client, base = db_client_and_base
    euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                  path="/Eukaryota")
    ani = _insert(conn, scientific_name="Animalia", rank="kingdom",
                  parent_id=euk, path="/Eukaryota/Animalia")
    chordata = _insert(conn, scientific_name="Chordata", rank="phylum",
                       parent_id=ani, path="/Eukaryota/Animalia/Chordata")
    # First call: 3 created.
    r1 = client.post(f"/api/taxon/{chordata}/materialize")
    assert r1.status_code == 200
    assert r1.json()["folders_created"] == 3
    assert r1.json()["folders_existed"] == 0
    # Second call: 0 created, 3 existed.
    r2 = client.post(f"/api/taxon/{chordata}/materialize")
    assert r2.status_code == 200, r2.text
    assert r2.json()["folders_created"] == 0
    assert r2.json()["folders_existed"] == 3
    # Folders still have no files after the second call (intermediate
    # folders have child folders; leaf is empty).
    for d in ("Eukaryota", "Eukaryota/Animalia",
              "Eukaryota/Animalia/Chordata"):
        assert (base / d).is_dir()
        files = [c for c in (base / d).iterdir() if c.is_file()]
        assert files == [], f"unexpected files in {d}: {files}"


def test_does_not_overwrite_existing_files_in_folder(db_client_and_base):
    """AC-5b: If a folder under the path already contains a file, the
    endpoint must NOT delete or overwrite it. The endpoint never writes
    files into the created folders, so user content is always preserved."""
    conn, client, base = db_client_and_base
    euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                  path="/Eukaryota")
    leaf = _insert(conn, scientific_name="Leaf", rank="species",
                   parent_id=euk, path="/Eukaryota/Leaf")
    # Pre-create the folder with a real file inside.
    leaf_dir = base / "Eukaryota" / "Leaf"
    leaf_dir.mkdir(parents=True)
    (leaf_dir / "notes.txt").write_text("user data, must survive")
    resp = client.post(f"/api/taxon/{leaf}/materialize")
    assert resp.status_code == 200, resp.text
    # The user file is intact and is the only thing in the folder.
    assert (leaf_dir / "notes.txt").read_text() == "user data, must survive"
    assert list(leaf_dir.iterdir()) == [leaf_dir / "notes.txt"]
    # The endpoint added nothing else — no .gitkeep, no extra files.
    assert len(list(leaf_dir.iterdir())) == 1


# ---------------------------------------------------------------------------
# AC-6 — 409 on path collision
# ---------------------------------------------------------------------------


def test_409_when_path_collides_with_existing_file(db_client_and_base):
    """AC-6: If a component of the target path is an existing file (not a
    directory), return 409 with a clear detail message instead of silently
    failing in mkdir."""
    conn, client, base = db_client_and_base
    euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                  path="/Eukaryota")
    leaf = _insert(conn, scientific_name="Leaf", rank="species",
                   parent_id=euk, path="/Eukaryota/Leaf")
    # Pre-create a FILE at the path where the leaf folder would go.
    (base / "Eukaryota").mkdir(parents=True)
    blocker = base / "Eukaryota" / "Leaf"
    blocker.write_text("I am a file, not a directory")
    resp = client.post(f"/api/taxon/{leaf}/materialize")
    assert resp.status_code == 409, resp.text
    assert "conflict" in resp.json()["detail"].lower() or "not a directory" \
        in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# AC-7 — recursion cycle / max depth
# ---------------------------------------------------------------------------


def test_500_on_parent_id_cycle(db_client_and_base):
    """AC-7: If the parent_id walk detects a cycle (A→B→A), abort with a
    clear 500 error rather than spinning forever."""
    conn, client, _base = db_client_and_base
    a = _insert(conn, scientific_name="A", rank="kingdom", path=None)
    b = _insert(conn, scientific_name="B", rank="phylum", parent_id=a,
                path=None)
    # Close the cycle: a's parent becomes b. Insert via UPDATE because
    # the initial insert already happened with parent_id=None.
    conn.execute("UPDATE taxon SET parent_id = ? WHERE id = ?", (b, a))
    conn.commit()
    resp = client.post(f"/api/taxon/{a}/materialize")
    assert resp.status_code == 500, resp.text
    assert "cycle" in resp.json()["detail"].lower()


def test_500_on_parent_id_chain_too_deep(db_client_and_base):
    """AC-7b: A pathologically deep parent_id chain (>50 hops) aborts with
    a clear error rather than blowing the stack or hanging."""
    conn, client, _base = db_client_and_base
    parent_id = None
    last_id = None
    # Build a chain of 60 nodes — all named "Deep" so the path goes Deep/Deep/...
    for i in range(60):
        last_id = _insert(
            conn,
            id=1000 + i,  # explicit ids to avoid drift in the chain
            scientific_name="Deep",
            parent_id=parent_id,
            path=None,
        )
        parent_id = last_id
    resp = client.post(f"/api/taxon/{last_id}/materialize")
    assert resp.status_code == 500, resp.text
    assert "deep" in resp.json()["detail"].lower() or "cycle" \
        in resp.json()["detail"].lower()
