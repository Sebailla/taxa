"""
Tests for the file-explorer endpoints.

  GET /api/taxon/{taxon_id}/files         — recursive tree JSON
  GET /api/taxon/{taxon_id}/files/serve   — streaming file with safety checks

Mirrors tests/test_api_materialize.py's pattern: in-memory SQLite seeded by
tests via `_insert`, RESEARCH_DIR monkeypatched to tmp_path/"Research", db()
monkeypatched to a fake_db that opens a fresh connection to the in-memory DB.

The streaming endpoint's `_STREAM_CAP_BYTES` is a module-level constant
(currently 100 MB). The cap test creates a sparse 101 MB file via
`f.truncate()` — no actual disk usage on APFS / ext4, but `stat().st_size`
returns 101 MB so the cap check fires.

Run:
    pytest tests/test_api_file_explorer.py -v
"""
from __future__ import annotations

import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from api.server import app


# Same SCHEMA as test_api_materialize.py — kept locally to avoid coupling
# (tests can run independently of any future conftest; matches the existing
# materialize pattern).
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
    - `api.server.RESEARCH_DIR` patched to a tmp_path so the API never
      touches the real ./Research folder.
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


# Field name + default tuple — keep aligned with the SCHEMA above so
# `python-sql-injection` scanners see a literal parameterised query.
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
    """Insert a taxon row with sane defaults. Returns the new id."""
    defaults = dict(_TAXON_FIELD_DEFAULTS)
    defaults.update(fields)
    vals = tuple(defaults[k] for k in _TAXON_FIELD_NAMES)
    cur = conn.execute(
        "INSERT INTO taxon (parent_id, rank, status, scientific_name, authorship, path, species_count, accepted_id, is_extinct, coldp_id, worms_id, freshwater_id, freshwater_parent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        vals,
    )
    conn.commit()
    return cur.lastrowid


def _make_chain(conn):
    """Build Eukaryota → Animalia → Chordata with full paths. Returns the
    leaf taxon id (Chordata)."""
    _euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                   path="/Eukaryota")
    _ani = _insert(conn, scientific_name="Animalia", rank="kingdom",
                   parent_id=_euk, path="/Eukaryota/Animalia")
    chordata = _insert(conn, scientific_name="Chordata", rank="phylum",
                        parent_id=_ani, path="/Eukaryota/Animalia/Chordata")
    return chordata


def _materialize(client, taxon_id):
    """Materialize the taxon's research folder. Returns the response object."""
    resp = client.post(f"/api/taxon/{taxon_id}/materialize")
    assert resp.status_code == 200, resp.text
    return resp


# ---------------------------------------------------------------------------
# AC-1 — tree happy path: mixed folders + files, folders-first, case-insensitive
# ---------------------------------------------------------------------------


def test_tree_happy_path_mixed_children(db_client_and_base):
    """AC-1: A materialized taxon returns the recursive JSON tree. Folders
    appear before files; both are sorted alphabetically case-insensitive.
    Each file carries {name, path, type, extension, size, modified}; each
    folder carries {name, path, type, children}. The recursive walk
    descends into subfolders."""
    conn, client, base = db_client_and_base
    chordata = _make_chain(conn)
    _materialize(client, chordata)
    leaf = base / "Eukaryota" / "Animalia" / "Chordata"
    # Build a folder + mixed files with deliberate case-insensitive ordering.
    (leaf / "Papers").mkdir()
    (leaf / "Papers" / "lynx.pdf").write_bytes(b"%PDF-1.4\n")
    (leaf / "alpha-notes.md").write_text("# alpha")
    (leaf / "Zebra.txt").write_text("zebra")
    (leaf / "beta.md").write_text("beta")

    resp = client.get(f"/api/taxon/{chordata}/files")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["exists"] is True
    assert body["taxon_id"] == chordata
    assert body["taxon_name"] == "Chordata"
    assert body["taxon_path"] == "Eukaryota/Animalia/Chordata"
    # Absolute filesystem path under tmp RESEARCH_DIR.
    assert body["filesystem_path"].endswith("Research/Eukaryota/Animalia/Chordata")
    # The root node is the leaf folder.
    root = body["root"]
    assert root["name"] == "Chordata"
    assert root["type"] == "folder"
    assert root["path"] == ""
    # Folders first, then files; both sorted case-insensitive.
    children = root["children"]
    assert children[0]["name"] == "Papers" and children[0]["type"] == "folder"
    file_children = [c for c in children if c["type"] == "file"]
    file_names = [c["name"] for c in file_children]
    # alpha-notes.md < beta.md < Zebra.txt (case-insensitive on the basename).
    assert file_names == ["alpha-notes.md", "beta.md", "Zebra.txt"], file_names
    # Every file carries the spec fields.
    for c in file_children:
        assert "extension" in c
        assert "size" in c and c["size"] >= 0
        assert "modified" in c and "T" in c["modified"]  # ISO timestamp shape
        assert c["path"].endswith(c["name"])
    # Recursive walk: Papers/lynx.pdf is visible.
    papers = children[0]
    assert papers["type"] == "folder"
    assert papers["path"] == "Papers"
    assert len(papers["children"]) == 1
    grandchild = papers["children"][0]
    assert grandchild["name"] == "lynx.pdf"
    assert grandchild["type"] == "file"
    assert grandchild["extension"] == "pdf"
    assert grandchild["path"] == "Papers/lynx.pdf"


# ---------------------------------------------------------------------------
# AC-2 — not-materialized taxon: 200 with exists: false, root: null
# ---------------------------------------------------------------------------


def test_tree_not_materialized_returns_exists_false(db_client_and_base):
    """AC-2: When the taxon exists in the DB but its research folder is NOT
    on disk, the endpoint returns 200 (not 404) with `exists: false` and
    `root: null`. The frontend renders the empty-state message from this
    state — it's distinct from the 404 'taxon not found' path."""
    conn, client, _base = db_client_and_base
    chordata = _make_chain(conn)
    # No materialize call.
    resp = client.get(f"/api/taxon/{chordata}/files")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["exists"] is False
    assert body["root"] is None
    assert body["taxon_id"] == chordata
    assert body["taxon_name"] == "Chordata"
    assert body["taxon_path"] == "Eukaryota/Animalia/Chordata"


# ---------------------------------------------------------------------------
# AC-3 — unknown taxon: 404 with detail
# ---------------------------------------------------------------------------


def test_tree_unknown_taxon_returns_404(db_client_and_base):
    """AC-3: GET /api/taxon/{id}/files on a non-existent id returns 404
    with a detail message containing the taxon id (mirrors the materialize
    endpoint's 404 contract)."""
    _conn, client, _base = db_client_and_base
    resp = client.get("/api/taxon/999999/files")
    assert resp.status_code == 404, resp.text
    assert "999999" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# AC-4 — synonym taxon (path=NULL) walks parent_id chain
# ---------------------------------------------------------------------------


def test_tree_synonym_walks_parents(db_client_and_base):
    """AC-4: A taxon with path=NULL falls back to the parent_id walk — same
    fallback as /materialize. The response's taxon_path reflects the
    walked sanitized segments, not null."""
    conn, client, base = db_client_and_base
    euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                  path="/Eukaryota")
    _ani = _insert(conn, scientific_name="Animalia", rank="kingdom",
                   parent_id=euk, path=None)  # path=NULL → walk
    chordata = _insert(conn, scientific_name="Chordata", rank="phylum",
                        parent_id=euk, path=None)  # path=NULL → walk
    # Pre-create the walked folder structure on disk (no POST /materialize).
    (base / "Eukaryota" / "Chordata").mkdir(parents=True)
    (base / "Eukaryota" / "Chordata" / "syn.txt").write_text("syn")

    resp = client.get(f"/api/taxon/{chordata}/files")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["exists"] is True
    # Walk produces [Eukaryota, Chordata]; Chordata is appended because the
    # taxon's own scientific_name is the leaf segment when path=NULL.
    assert body["taxon_path"] == "Eukaryota/Chordata"
    assert body["root"]["name"] == "Chordata"
    file_names = [c["name"] for c in body["root"]["children"] if c["type"] == "file"]
    assert "syn.txt" in file_names


# ---------------------------------------------------------------------------
# AC-5 — tree walk excludes symlinks
# ---------------------------------------------------------------------------


def test_tree_symlink_is_excluded(db_client_and_base):
    """AC-5: A symlink inside the taxon's research folder is SKIPPED during
    the tree walk. The serve endpoint rejects symlink-escapes anyway, so
    surfacing them in the tree would let users click paths the API refuses.
    Skipping at the walk layer is cheaper UX than failing at serve time."""
    conn, client, base = db_client_and_base
    chordata = _make_chain(conn)
    _materialize(client, chordata)
    leaf = base / "Eukaryota" / "Animalia" / "Chordata"
    # Real folder + real file so the tree isn't empty.
    (leaf / "Real").mkdir()
    (leaf / "notes.md").write_text("# notes")
    # Symlink to a real directory elsewhere (so the symlink isn't broken —
    # broken or not, we still skip it).
    target = base / "alias-outside"
    target.mkdir(exist_ok=True)
    (leaf / "Alias").symlink_to(target)

    resp = client.get(f"/api/taxon/{chordata}/files")
    assert resp.status_code == 200, resp.text
    root = resp.json()["root"]
    names = [c["name"] for c in root["children"]]
    # Symlink "Alias" must NOT appear; the real entries do.
    assert "Alias" not in names, f"symlink leaked into tree: {names}"
    assert "Real" in names
    assert "notes.md" in names


# ---------------------------------------------------------------------------
# AC-6 — streaming endpoint happy path, parametrized over 9 supported formats
# ---------------------------------------------------------------------------

SUPPORTED_EXTS = [
    "pdf", "epub", "html", "htm", "md", "txt", "doc", "docx", "xls", "xlsx",
]
EXPECTED_CT = {
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
}


@pytest.mark.parametrize("ext", SUPPORTED_EXTS)
def test_serve_happy_path_one_extension_per_format(db_client_and_base, ext):
    """AC-6: The streaming endpoint returns 200 + correct Content-Type +
    Content-Disposition: inline for each of the 10 supported extensions
    (parametrized — 10 focused cases, one per format)."""
    conn, client, base = db_client_and_base
    chordata = _make_chain(conn)
    _materialize(client, chordata)
    leaf = base / "Eukaryota" / "Animalia" / "Chordata"
    fname = f"sample.{ext}"
    (leaf / fname).write_bytes(b"sample content")

    resp = client.get(f"/api/taxon/{chordata}/files/serve?path={fname}")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith(EXPECTED_CT[ext]), (
        f"ext={ext} got content-type={resp.headers.get('content-type')!r}"
    )
    cd = resp.headers.get("content-disposition", "")
    assert cd.startswith("inline;"), f"ext={ext} content-disposition={cd!r}"
    assert f'filename="{fname}"' in cd
    assert resp.content == b"sample content"


# ---------------------------------------------------------------------------
# AC-7 — path traversal blocked (..)
# ---------------------------------------------------------------------------


def test_serve_path_traversal_dotdot(db_client_and_base):
    """AC-7: path='..' returns 400 with detail 'Path escapes research root'.
    The strict-parent assertion catches the resolved path outside the
    research root."""
    conn, client, base = db_client_and_base
    chordata = _make_chain(conn)
    _materialize(client, chordata)
    resp = client.get(f"/api/taxon/{chordata}/files/serve?path=..")
    assert resp.status_code == 400, resp.text
    assert "escapes" in resp.json()["detail"].lower()


def test_serve_path_traversal_multi(db_client_and_base):
    """AC-7b: path='../../etc/passwd' returns 400 with the same detail."""
    conn, client, base = db_client_and_base
    chordata = _make_chain(conn)
    _materialize(client, chordata)
    resp = client.get(f"/api/taxon/{chordata}/files/serve?path=../../etc/passwd")
    assert resp.status_code == 400, resp.text
    assert "escapes" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# AC-8 — absolute path blocked
# ---------------------------------------------------------------------------


def test_serve_absolute_path_blocked(db_client_and_base):
    """AC-8: path='/etc/passwd' returns 400 — Path.resolve() treats the
    leading slash as an absolute override on the relative join, so the
    candidate lands outside the research root."""
    conn, client, base = db_client_and_base
    chordata = _make_chain(conn)
    _materialize(client, chordata)
    # URL-encode the leading slash so the URL parser keeps it as a query value.
    resp = client.get(f"/api/taxon/{chordata}/files/serve?path=%2Fetc%2Fpasswd")
    assert resp.status_code == 400, resp.text
    assert "escapes" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# AC-9 — symlink escape blocked
# ---------------------------------------------------------------------------


def test_serve_symlink_escape_blocked(db_client_and_base):
    """AC-9: A symlink inside the research root pointing to a file OUTSIDE
    the root returns 400 — Path.resolve() follows the symlink, the
    strict-parent assertion rejects the resolved path."""
    conn, client, base = db_client_and_base
    chordata = _make_chain(conn)
    _materialize(client, chordata)
    leaf = base / "Eukaryota" / "Animalia" / "Chordata"
    # Real file outside the research root (in the test's tmp dir, but not
    # under RESEARCH_DIR). The symlink points to it from inside the leaf.
    outside = base.parent / "outside.txt"
    outside.write_text("SECRET")
    (leaf / "shortcut.txt").symlink_to(outside)

    resp = client.get(f"/api/taxon/{chordata}/files/serve?path=shortcut.txt")
    assert resp.status_code == 400, resp.text
    assert "escapes" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# AC-10 — file not found inside root
# ---------------------------------------------------------------------------


def test_serve_file_not_found(db_client_and_base):
    """AC-10: A path that resolves INSIDE the research root but doesn't
    exist returns 404 with detail 'File not found'."""
    conn, client, base = db_client_and_base
    chordata = _make_chain(conn)
    _materialize(client, chordata)
    resp = client.get(f"/api/taxon/{chordata}/files/serve?path=missing.txt")
    assert resp.status_code == 404, resp.text
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# AC-11 — taxon not materialized (research folder absent)
# ---------------------------------------------------------------------------


def test_serve_research_folder_not_materialized(db_client_and_base):
    """AC-11: When the taxon's research folder does NOT exist on disk, the
    serve endpoint returns 404 with detail 'Research folder not
    materialized' — distinct from 'File not found' so the frontend can
    render the empty-state vs the placeholder."""
    conn, client, _base = db_client_and_base
    chordata = _make_chain(conn)
    # No materialize call — base dir is empty.
    resp = client.get(f"/api/taxon/{chordata}/files/serve?path=anything.txt")
    assert resp.status_code == 404, resp.text
    assert "not materialized" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# AC-12 — file exceeds streaming cap → 413
# ---------------------------------------------------------------------------


def test_serve_exceeds_streaming_cap(db_client_and_base):
    """AC-12: A file larger than _STREAM_CAP_BYTES (100 MB) returns 413
    with a detail message naming the cap and the actual size. The cap is
    enforced BEFORE the file is opened (stat().st_size is the only read).
    Uses a sparse file via f.truncate() so the test stays fast on
    APFS/ext4 — st_size reports the logical size, physical allocation
    is zero."""
    conn, client, base = db_client_and_base
    chordata = _make_chain(conn)
    _materialize(client, chordata)
    leaf = base / "Eukaryota" / "Animalia" / "Chordata"
    big = leaf / "huge.pdf"
    cap = 100 * 1024 * 1024
    # 100 MB + 1 MB — comfortably above the cap, well below the worst case
    # for sparse-file allocation failures.
    big_size = cap + 1024 * 1024
    with open(big, "wb") as f:
        f.truncate(big_size)

    resp = client.get(f"/api/taxon/{chordata}/files/serve?path=huge.pdf")
    assert resp.status_code == 413, resp.text
    detail = resp.json()["detail"]
    assert str(cap) in detail, f"cap not in detail: {detail!r}"
    assert str(big_size) in detail, f"actual size not in detail: {detail!r}"


# ---------------------------------------------------------------------------
# AC-13 — Content-Disposition: inline header
# ---------------------------------------------------------------------------


def test_serve_content_disposition_inline(db_client_and_base):
    """AC-13: Streaming response carries Content-Disposition: inline; filename="…"
    so embedded viewers (<iframe>, <embed>) consume the response without
    triggering a download dialog."""
    conn, client, base = db_client_and_base
    chordata = _make_chain(conn)
    _materialize(client, chordata)
    leaf = base / "Eukaryota" / "Animalia" / "Chordata"
    (leaf / "data.txt").write_text("hello")

    resp = client.get(f"/api/taxon/{chordata}/files/serve?path=data.txt")
    assert resp.status_code == 200
    cd = resp.headers.get("content-disposition", "")
    assert cd.startswith("inline;")
    assert 'filename="data.txt"' in cd


# ---------------------------------------------------------------------------
# AC-14 — unsupported extension returns application/octet-stream
# ---------------------------------------------------------------------------


def test_serve_unsupported_extension_returns_octet_stream(db_client_and_base):
    """AC-14: Files outside the 10 supported extensions get Content-Type:
    application/octet-stream so the browser can still download them.
    The endpoint remains a safe download route for unsupported formats."""
    conn, client, base = db_client_and_base
    chordata = _make_chain(conn)
    _materialize(client, chordata)
    leaf = base / "Eukaryota" / "Animalia" / "Chordata"
    (leaf / "archive.zip").write_bytes(b"PK\x03\x04")

    resp = client.get(f"/api/taxon/{chordata}/files/serve?path=archive.zip")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/octet-stream")
    # Content-Disposition: inline is still set so the download link works.
    cd = resp.headers.get("content-disposition", "")
    assert cd.startswith("inline;")
    assert 'filename="archive.zip"' in cd
