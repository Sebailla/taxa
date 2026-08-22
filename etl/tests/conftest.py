"""
Shared pytest fixtures for etl/tests/.

The loader tests run against an in-memory SQLite that mirrors the production
schema but with NO freshwater columns. The loader must:
- handle the missing columns (idempotent ALTER), and
- leave the CoL/WoRMS rows untouched when wiping prior freshwater rows.

Why in-memory: the production DB is 2.6 GB. Tests run in <1s against an
empty SQLite (a few rows + the synthetic root + maybe 5–10 fixture rows).

The schema mirrors etl/schema.sql + etl/schema_v2.sql + etl/schema_v3.sql
without the freshwater overlay columns. Those land in `etl/schema_v4.sql`.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

# Schema v1+v2+v3 (no freshwater overlay). Each test gets a fresh in-memory
# connection so they're fully isolated.
BASE_SCHEMA = """
CREATE TABLE taxon (
    id              INTEGER PRIMARY KEY,
    parent_id       INTEGER REFERENCES taxon(id) ON DELETE CASCADE,
    rank            TEXT    NOT NULL,
    status          TEXT    NOT NULL CHECK (status IN ('accepted', 'synonym')),
    scientific_name TEXT    NOT NULL,
    authorship      TEXT,
    path            TEXT,
    species_count   INTEGER,
    accepted_id     INTEGER REFERENCES taxon(id),
    is_extinct      INTEGER NOT NULL DEFAULT 0,
    coldp_id        TEXT,
    worms_id        INTEGER
);
"""


@pytest.fixture
def db_conn():
    """Fresh in-memory SQLite with the v1+v2+v3 schema (no freshwater cols)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(BASE_SCHEMA)
    yield conn
    conn.close()


@pytest.fixture
def write_csv(tmp_path):
    """Factory: write `rows` (list of lists) to a CSV file and return the path.

    Usage:
        csv_path = write_csv([
            ["10", "1", "order", "Characiformes", ""],
            ["11", "10", "family", "Characidae", ""],
        ])
    """
    def _write(rows, name="freshwater.csv", with_header=False):
        path = tmp_path / name
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            if with_header:
                w.writerow(["freshwater_id", "freshwater_parent_id", "rank",
                            "scientific_name", "authorship"])
            for r in rows:
                w.writerow(r)
        return path
    return _write


@pytest.fixture
def root_dir():
    """Path to the project root (etl/ + api/ + data/ live under here)."""
    return Path(__file__).resolve().parent.parent.parent
