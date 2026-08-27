"""
Tests for the save-url endpoint — POST /api/taxon/{id}/save-url.

The endpoint fetches a URL server-side, validates it (SSRF defense,
content-type allowlist, size cap), sanitizes the filename, and writes
the response body to the materialized Research folder for the taxon.
The browser extension (browser-extension-save-to-research change) is
the primary caller; these tests pin the backend contract so the
extension and the endpoint can evolve independently.

Pattern: in-memory SQLite (cache=shared) + a small http.server running
in a thread that the API server's urllib fetches against. The base dir
is monkey-patched to a tmp_path so the test never touches the real
./Research.

Run:
    pytest tests/test_api_save_url.py -v
"""
from __future__ import annotations

import os
import socket
import sqlite3
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
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


# --- DB fixture ------------------------------------------------------------


@pytest.fixture
def db_client_and_base(monkeypatch, tmp_path):
    """Yield (conn, client, base_dir) tuple.

    - In-memory SQLite seeded by tests via `_insert`.
    - `api.server.db` patched so the API hits the in-memory DB.
    - `api.server.RESEARCH_DIR` patched to a tmp_path so save-url
      writes to a throwaway directory and never touches ./Research.
    - The SSRF check is ACTIVE (the production check). Tests that need
      to fetch from a 127.0.0.1 origin server should use the
      `db_client_and_base_loopback` fixture below instead.
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


@pytest.fixture
def db_client_and_base_loopback(monkeypatch, tmp_path):
    """Same as `db_client_and_base` but with the SSRF check disabled.

    The save-url endpoint rejects loopback / private IPs by default. The
    test origin server (`origin_server` fixture) binds to 127.0.0.1,
    which is exactly what the production check is supposed to reject. So
    tests that need to actually fetch from the fixture's origin server
    request this fixture to get the SSRF check bypassed for their
    duration. Tests that exercise the SSRF defense itself use the
    plain `db_client_and_base` fixture instead.
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
    monkeypatch.setattr(
        "api.server._is_private_or_reserved_ip", lambda _hostname: False
    )
    yield conn, TestClient(app), base_dir

    conn.close()


# Module-level SQL literal — used by `_insert`. Kept at module scope
# so the SQL is a single string the opengrep scanner can recognize as
# a literal (not constructed). Values are bound via `?` placeholders.
_INSERT_TAXON_SQL = (
    "INSERT INTO taxon ("
    "parent_id, rank, status, scientific_name, authorship, path, "
    "species_count, accepted_id, is_extinct, coldp_id, worms_id, "
    "freshwater_id, freshwater_parent_id"
    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def _insert(conn, **fields):
    """Insert a taxon row. Returns the new id."""
    defaults = {
            "parent_id": None, "rank": "species", "status": "accepted",
            "scientific_name": "Unknown", "authorship": None, "path": None,
            "species_count": None, "accepted_id": None, "is_extinct": 0,
            "coldp_id": None, "worms_id": None,
            "freshwater_id": None, "freshwater_parent_id": None,
    }
    defaults.update(fields)
    vals = list(defaults.values())
    cur = conn.execute(_INSERT_TAXON_SQL, vals)  # nosem: python.lang.security.audit.formatted-sql-query.formatted-sql-query
    conn.commit()
    return cur.lastrowid


# --- HTTP fixture (the "origin" the API server fetches) --------------------


class _OriginHandler(BaseHTTPRequestHandler):
    """Configurable origin server. Behaviour is controlled by the
    `_origin_behavior` module-level dict, which the test sets before
    the request fires.

    Keys:
        body (bytes): response body
        content_type (str): Content-Type header
        status (int): HTTP status code (default 200)
    """
    def do_GET(self):  # noqa: N802 — http.server convention
        behavior = _origin_behavior
        self.send_response(behavior.get("status", 200))
        self.send_header("Content-Type", behavior.get("content_type", "application/pdf"))
        self.send_header("Content-Length", str(len(behavior.get("body", b""))))
        self.end_headers()
        self.wfile.write(behavior.get("body", b""))

    # Silence the default access log; pytest output is enough.
    def log_message(self, format, *args):  # noqa: A002
        return


@pytest.fixture
def origin_server(monkeypatch):
    """Yield the base URL of a fresh in-process HTTP server. The
    handler's behaviour is controlled by the `_origin_behavior` dict;
    tests set keys on it before calling the save-url endpoint.
    """
    # Bind to 127.0.0.1 on an ephemeral port.
    server = HTTPServer(("127.0.0.1", 0), _OriginHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    yield base_url
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture(autouse=True)
def reset_origin_behavior():
    """Each test starts with a clean behaviour dict."""
    _origin_behavior.clear()
    _origin_behavior.update({"body": b"", "content_type": "application/pdf", "status": 200})
    yield
    _origin_behavior.clear()


# Module-level state the handler reads on each request.
_origin_behavior: dict = {}


# --- Tests -----------------------------------------------------------------


# AC: happy path — valid PDF URL → 200, file on disk, response shape.
def test_save_url_happy_path_pdf(db_client_and_base_loopback, origin_server):
    """AC: A valid public PDF URL returns 200, the file is on disk under
    Research/<chain>/<file>__<id>.pdf, and the response shape matches
    {ok, absolute_path, size, content_type}."""
    conn, client, base = db_client_and_base_loopback
    euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                  path="/Eukaryota")
    ani = _insert(conn, scientific_name="Animalia", rank="kingdom",
                  parent_id=euk, path="/Eukaryota/Animalia")
    homo = _insert(conn, scientific_name="Homo sapiens", rank="species",
                   parent_id=ani, path="/Eukaryota/Animalia/Homo sapiens")
    # Pre-materialize so the folder exists.
    materialize = client.post(f"/api/taxon/{homo}/materialize")
    assert materialize.status_code == 200, materialize.text

    pdf_body = b"%PDF-1.4 fake content for testing"
    _origin_behavior["body"] = pdf_body
    _origin_behavior["content_type"] = "application/pdf"

    resp = client.post(
        f"/api/taxon/{homo}/save-url",
        json={"url": f"{origin_server}/paper.pdf", "suggested_filename": "paper.pdf"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["content_type"] == "application/pdf"
    assert body["size"] == len(pdf_body)
    expected_path = base / "Eukaryota" / "Animalia" / "Homo sapiens" / f"paper__{homo}.pdf"
    assert Path(body["absolute_path"]) == expected_path
    assert expected_path.is_file()
    assert expected_path.read_bytes() == pdf_body


# AC: 404 when Research path not materialized.
def test_save_url_404_no_folder(db_client_and_base, origin_server):
    """AC: When the taxon's Research path doesn't exist on disk, the
    endpoint returns 404 with 'Materialize the folder first'."""
    conn, client, _base = db_client_and_base
    euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                  path="/Eukaryota")
    ani = _insert(conn, scientific_name="Animalia", rank="kingdom",
                  parent_id=euk, path="/Eukaryota/Animalia")
    homo = _insert(conn, scientific_name="Homo sapiens", rank="species",
                   parent_id=ani, path="/Eukaryota/Animalia/Homo sapiens")
    # Do NOT materialize. The folder doesn't exist on disk.

    _origin_behavior["body"] = b"irrelevant"
    resp = client.post(
        f"/api/taxon/{homo}/save-url",
        json={"url": f"{origin_server}/x.pdf"},
    )
    assert resp.status_code == 404, resp.text
    assert "Materialize" in resp.json()["detail"]


# AC: 404 for non-existent taxon.
def test_save_url_404_no_taxon(db_client_and_base, origin_server):
    """AC: POSTing to a non-existent taxon id returns 404."""
    _conn, client, _base = db_client_and_base
    resp = client.post(
        "/api/taxon/999999/save-url",
        json={"url": f"{origin_server}/x.pdf"},
    )
    assert resp.status_code == 404, resp.text
    assert "999999" in resp.json()["detail"]


# AC: 400 for private IP literal (RFC1918).
def test_save_url_400_private_ip_literal(db_client_and_base, origin_server):
    """AC: A URL with a literal RFC1918 host is rejected with 400 before
    the fetch is attempted. The SSRF check happens on the resolved IP;
    a literal 10.0.0.1 is unambiguous."""
    conn, client, _base = db_client_and_base
    euk = _insert(conn, scientific_name="Eukaryota", rank="domain",
                  path="/Eukaryota")
    _insert(conn, scientific_name="Animalia", rank="kingdom",
            parent_id=euk, path="/Eukaryota/Animalia")
    _insert(conn, scientific_name="Homo sapiens", rank="species",
            parent_id=euk, path="/Eukaryota/Animalia/Homo sapiens")
    client.post(f"/api/taxon/3/materialize")  # ignore status; just want folders

    resp = client.post(
        "/api/taxon/3/save-url",
        json={"url": "http://10.0.0.1/admin/x.pdf"},
    )
    assert resp.status_code == 400, resp.text
    assert "private" in resp.json()["detail"].lower() or "reserved" in resp.json()["detail"].lower()


# AC: 400 for loopback IP literal.
def test_save_url_400_loopback(db_client_and_base, origin_server):
    """AC: 127.0.0.1 is rejected (loopback is a private range)."""
    conn, client, _base = db_client_and_base
    _insert(conn, scientific_name="Eukaryota", rank="domain", path="/Eukaryota")
    _insert(conn, scientific_name="Animalia", rank="kingdom",
            parent_id=1, path="/Eukaryota/Animalia")
    _insert(conn, scientific_name="Homo sapiens", rank="species",
            parent_id=2, path="/Eukaryota/Animalia/Homo sapiens")
    client.post("/api/taxon/3/materialize")

    resp = client.post(
        "/api/taxon/3/save-url",
        json={"url": "http://127.0.0.1/x.pdf"},
    )
    assert resp.status_code == 400, resp.text


# AC: 400 for link-local IP literal (cloud metadata endpoint).
def test_save_url_400_link_local(db_client_and_base, origin_server):
    """AC: 169.254.169.254 is link-local; rejected."""
    conn, client, _base = db_client_and_base
    _insert(conn, scientific_name="Eukaryota", rank="domain", path="/Eukaryota")
    _insert(conn, scientific_name="Animalia", rank="kingdom",
            parent_id=1, path="/Eukaryota/Animalia")
    _insert(conn, scientific_name="Homo sapiens", rank="species",
            parent_id=2, path="/Eukaryota/Animalia/Homo sapiens")
    client.post("/api/taxon/3/materialize")

    resp = client.post(
        "/api/taxon/3/save-url",
        json={"url": "http://169.254.169.254/latest/meta-data/"},
    )
    assert resp.status_code == 400, resp.text


# AC: 400 for unresolvable hostname (fail closed).
def test_save_url_400_unresolvable(db_client_and_base, origin_server):
    """AC: Hostname that doesn't resolve fails closed (treated as private)."""
    conn, client, _base = db_client_and_base
    _insert(conn, scientific_name="Eukaryota", rank="domain", path="/Eukaryota")
    _insert(conn, scientific_name="Animalia", rank="kingdom",
            parent_id=1, path="/Eukaryota/Animalia")
    _insert(conn, scientific_name="Homo sapiens", rank="species",
            parent_id=2, path="/Eukaryota/Animalia/Homo sapiens")
    client.post("/api/taxon/3/materialize")

    resp = client.post(
        "/api/taxon/3/save-url",
        json={"url": "http://does-not-exist-xyz.invalid/x.pdf"},
    )
    assert resp.status_code == 400, resp.text


# AC: 413 when response exceeds size cap.
def test_save_url_413_size_cap(db_client_and_base_loopback, origin_server):
    """AC: A response body larger than 50 MB returns 413 and writes
    nothing (or deletes the partial)."""
    conn, client, base = db_client_and_base_loopback
    _insert(conn, scientific_name="Eukaryota", rank="domain", path="/Eukaryota")
    _insert(conn, scientific_name="Animalia", rank="kingdom",
            parent_id=1, path="/Eukaryota/Animalia")
    _insert(conn, scientific_name="Homo sapiens", rank="species",
            parent_id=2, path="/Eukaryota/Animalia/Homo sapiens")
    client.post("/api/taxon/3/materialize")

    # Send 60 MB. The cap is 50 MB. The endpoint should reject at the
    # cap and not write the file.
    _origin_behavior["body"] = b"X" * (60 * 1024 * 1024)
    _origin_behavior["content_type"] = "application/octet-stream"

    resp = client.post(
        "/api/taxon/3/save-url",
        json={"url": f"{origin_server}/huge.bin", "suggested_filename": "huge.bin"},
    )
    assert resp.status_code == 413, resp.text
    # No file should exist in the research dir.
    files = list(base.rglob("*"))
    real_files = [f for f in files if f.is_file()]
    assert real_files == [], f"unexpected files after 413: {real_files}"


# AC: 415 for disallowed content-type.
def test_save_url_415_disallowed_type(db_client_and_base_loopback, origin_server):
    """AC: A response with a non-allowlisted Content-Type (e.g. text/csv)
    returns 415 and writes nothing."""
    conn, client, base = db_client_and_base_loopback
    _insert(conn, scientific_name="Eukaryota", rank="domain", path="/Eukaryota")
    _insert(conn, scientific_name="Animalia", rank="kingdom",
            parent_id=1, path="/Eukaryota/Animalia")
    _insert(conn, scientific_name="Homo sapiens", rank="species",
            parent_id=2, path="/Eukaryota/Animalia/Homo sapiens")
    client.post("/api/taxon/3/materialize")

    _origin_behavior["body"] = b"col1,col2,col3\n1,2,3\n"
    _origin_behavior["content_type"] = "text/csv"

    resp = client.post(
        "/api/taxon/3/save-url",
        json={"url": f"{origin_server}/data.csv", "suggested_filename": "data.csv"},
    )
    assert resp.status_code == 415, resp.text
    real_files = [f for f in base.rglob("*") if f.is_file()]
    assert real_files == [], f"unexpected files after 415: {real_files}"


# AC: 502 when origin returns 401 (auth-required).
def test_save_url_502_origin_401(db_client_and_base_loopback, origin_server):
    """AC: Origin 401 → 502 with 'authentication required' in the
    detail. The endpoint surfaces auth-required clearly so the user
    gets an actionable error."""
    conn, client, _base = db_client_and_base_loopback
    _insert(conn, scientific_name="Eukaryota", rank="domain", path="/Eukaryota")
    _insert(conn, scientific_name="Animalia", rank="kingdom",
            parent_id=1, path="/Eukaryota/Animalia")
    _insert(conn, scientific_name="Homo sapiens", rank="species",
            parent_id=2, path="/Eukaryota/Animalia/Homo sapiens")
    client.post("/api/taxon/3/materialize")

    _origin_behavior["status"] = 401
    _origin_behavior["body"] = b"login required"

    resp = client.post(
        "/api/taxon/3/save-url",
        json={"url": f"{origin_server}/paper.pdf", "suggested_filename": "paper.pdf"},
    )
    assert resp.status_code == 502, resp.text
    detail = resp.json()["detail"]
    assert "401" in detail and "authentication" in detail.lower()


# AC: 502 when origin returns 404.
def test_save_url_502_origin_404(db_client_and_base_loopback, origin_server):
    """AC: Origin 404 → 502 with 'resource moved or deleted' in detail."""
    conn, client, _base = db_client_and_base_loopback
    _insert(conn, scientific_name="Eukaryota", rank="domain", path="/Eukaryota")
    _insert(conn, scientific_name="Animalia", rank="kingdom",
            parent_id=1, path="/Eukaryota/Animalia")
    _insert(conn, scientific_name="Homo sapiens", rank="species",
            parent_id=2, path="/Eukaryota/Animalia/Homo sapiens")
    client.post("/api/taxon/3/materialize")

    _origin_behavior["status"] = 404
    _origin_behavior["body"] = b"gone"

    resp = client.post(
        "/api/taxon/3/save-url",
        json={"url": f"{origin_server}/missing.pdf", "suggested_filename": "missing.pdf"},
    )
    assert resp.status_code == 502, resp.text
    detail = resp.json()["detail"]
    assert "404" in detail


# AC: Filename sanitization — path traversal in suggested_filename is stripped.
def test_save_url_sanitization_traversal(db_client_and_base_loopback, origin_server):
    """AC: `suggested_filename: "../../../etc/passwd"` is sanitized to
    'passwd' (no `..`, no path separators). The saved file is
    `passwd__<id>`."""
    conn, client, base = db_client_and_base_loopback
    _insert(conn, scientific_name="Eukaryota", rank="domain", path="/Eukaryota")
    _insert(conn, scientific_name="Animalia", rank="kingdom",
            parent_id=1, path="/Eukaryota/Animalia")
    _insert(conn, scientific_name="Homo sapiens", rank="species",
            parent_id=2, path="/Eukaryota/Animalia/Homo sapiens")
    client.post("/api/taxon/3/materialize")

    _origin_behavior["body"] = b"irrelevant"
    _origin_behavior["content_type"] = "application/pdf"

    resp = client.post(
        "/api/taxon/3/save-url",
        json={
            "url": f"{origin_server}/x.pdf",
            "suggested_filename": "../../../etc/passwd",
        },
    )
    assert resp.status_code == 200, resp.text
    saved_files = list(base.rglob("passwd*"))
    assert len(saved_files) == 1, f"expected one 'passwd' file, got: {saved_files}"
    assert ".." not in saved_files[0].name
    assert saved_files[0].name.startswith("passwd__")


# AC: Filename sanitization — special chars replaced with _.
def test_save_url_sanitization_special_chars(db_client_and_base_loopback, origin_server):
    """AC: Special characters in suggested_filename (slashes, pipes,
    asterisks, etc.) are replaced with `_`. Nothing dangerous survives."""
    conn, client, base = db_client_and_base_loopback
    _insert(conn, scientific_name="Eukaryota", rank="domain", path="/Eukaryota")
    _insert(conn, scientific_name="Animalia", rank="kingdom",
            parent_id=1, path="/Eukaryota/Animalia")
    _insert(conn, scientific_name="Homo sapiens", rank="species",
            parent_id=2, path="/Eukaryota/Animalia/Homo sapiens")
    client.post("/api/taxon/3/materialize")

    _origin_behavior["body"] = b"irrelevant"
    _origin_behavior["content_type"] = "application/pdf"

    resp = client.post(
        "/api/taxon/3/save-url",
        json={
            "url": f"{origin_server}/x.pdf",
            "suggested_filename": 'a/b\\c<d>e|f*g?.pdf',
        },
    )
    assert resp.status_code == 200, resp.text
    saved = list(base.rglob("*.pdf"))
    assert len(saved) == 1
    # None of the dangerous chars survive.
    for c in ('/', '\\', '<', '>', '|', '*', '?'):
        assert c not in saved[0].name, f"unsafe char {c!r} in {saved[0].name!r}"


# AC: Collision — two saves with same name → second is timestamp-suffixed.
def test_save_url_collision(db_client_and_base_loopback, origin_server):
    """AC: When the suggested filename produces an existing path on
    disk, the second save is written with a `__<timestamp>` suffix and
    the original file is untouched."""
    conn, client, base = db_client_and_base_loopback
    _insert(conn, scientific_name="Eukaryota", rank="domain", path="/Eukaryota")
    _insert(conn, scientific_name="Animalia", rank="kingdom",
            parent_id=1, path="/Eukaryota/Animalia")
    _insert(conn, scientific_name="Homo sapiens", rank="species",
            parent_id=2, path="/Eukaryota/Animalia/Homo sapiens")
    client.post("/api/taxon/3/materialize")

    _origin_behavior["body"] = b"first"
    _origin_behavior["content_type"] = "application/pdf"

    r1 = client.post(
        "/api/taxon/3/save-url",
        json={"url": f"{origin_server}/x.pdf", "suggested_filename": "dup.pdf"},
    )
    assert r1.status_code == 200, r1.text

    _origin_behavior["body"] = b"second"
    r2 = client.post(
        "/api/taxon/3/save-url",
        json={"url": f"{origin_server}/x.pdf", "suggested_filename": "dup.pdf"},
    )
    assert r2.status_code == 200, r2.text

    # Two files now exist: the original and the timestamp-suffixed second.
    pdfs = sorted(p for p in base.rglob("*.pdf"))
    assert len(pdfs) == 2, f"expected 2 PDFs, got: {pdfs}"
    # The original file (no timestamp suffix) should still have the
    # first body — the collision path must NEVER overwrite.
    original = next(
        p for p in pdfs
        if not any(
            # A timestamp segment is `__<at-least-8-digits>` (int(time.time())
            # returns a 10-digit number in 2026). The original has the
            # structure `<filename>__<taxon_id>` where the last segment
            # is the short taxon id, not a timestamp.
            part.isdigit() and len(part) >= 8
            for part in p.stem.split("__")
        )
    )
    assert original.read_bytes() == b"first"
    # The timestamped file should have the second body.
    timestamped = [p for p in pdfs if p != original][0]
    assert timestamped.read_bytes() == b"second"


# AC: ?source=freshwater works end-to-end.
def test_save_url_special_source(db_client_and_base_loopback, origin_server):
    """AC: When `?source=freshwater` is passed, the endpoint uses the
    freshwater hierarchy (freshwater_id / freshwater_parent_id) to build
    the path. The save-url flow must still resolve a target dir for
    taxa in the freshwater overlay."""
    conn, client, base = db_client_and_base_loopback
    # Single-taxon freshwater chain: Cyprinidae with freshwater_id set
    # and no parent. _build_segments with source=freshwater should
    # produce ["Cyprinidae"] (the sanitized scientific_name). The
    # materialize + save-url flow must then create the dir + file.
    fam = _insert(
        conn, scientific_name="Cyprinidae", rank="family",
        freshwater_id=200, freshwater_parent_id=None,
    )

    # Materialize via freshwater source.
    mat = client.post(f"/api/taxon/{fam}/materialize?source=freshwater")
    assert mat.status_code == 200, mat.text

    _origin_behavior["body"] = b"freshwater pdf"
    _origin_behavior["content_type"] = "application/pdf"

    resp = client.post(
        f"/api/taxon/{fam}/save-url?source=freshwater",
        json={"url": f"{origin_server}/paper.pdf", "suggested_filename": "paper.pdf"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    # The file lives under a freshwater-path-derived dir.
    saved = list(base.rglob("paper__*"))
    assert len(saved) == 1, f"expected one paper file, got: {saved}"