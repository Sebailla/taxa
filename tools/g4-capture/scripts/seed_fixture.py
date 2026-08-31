"""Seed the G4 SQLite fixture (taxon + vernacular). Idempotent.

Run: python tools/g4-capture/scripts/seed_fixture.py [path/to/taxa-fixture.db]
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


SCHEMA = """
CREATE TABLE taxon (
    id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES taxon(id) ON DELETE CASCADE,
    rank TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('accepted', 'synonym')),
    scientific_name TEXT NOT NULL, authorship TEXT, path TEXT, species_count INTEGER,
    accepted_id INTEGER REFERENCES taxon(id), is_extinct INTEGER NOT NULL DEFAULT 0,
    coldp_id TEXT, worms_id TEXT, worms_parent_id TEXT, freshwater_id TEXT, freshwater_parent_id TEXT
);
CREATE TABLE vernacular (
    id INTEGER PRIMARY KEY,
    taxon_id INTEGER NOT NULL REFERENCES taxon(id) ON DELETE CASCADE,
    name TEXT NOT NULL, transliteration TEXT, language TEXT, country TEXT,
    life_stage TEXT, sex TEXT, reference_id TEXT
);
"""

TAXON_ROWS = [
    (1, None, "domain",  "accepted", "Eukaryota",       None),
    (2, 1,    "kingdom", "accepted", "Animalia",        None),
    (3, 2,    "phylum",  "accepted", "Chordata",        None),
    (4, 3,    "class",   "accepted", "Mammalia",        "Linnaeus, 1758"),
    (5, 4,    "order",   "accepted", "Carnivora",       "Bowdich, 1821"),
    (6, 5,    "family",  "accepted", "Felidae",         "Fischer, 1817"),
    (7, 6,    "genus",   "accepted", "Panthera",        "Oken, 1816"),
    (8, 7,    "species", "accepted", "Panthera tigris", "(Linnaeus, 1758)"),
    (9, 7,    "species", "accepted", "Panthera leo",    "(Linnaeus, 1758)"),
    (10, 7,   "species", "accepted", "Panthera onca",   "(Linnaeus, 1758)"),
]

VERNACULAR_ROWS = [
    (1,  8, "Tiger",        "eng", "US"),
    (2,  8, "Bengal Tiger", "eng", "IN"),
    (3,  8, "Tigre",        "fra", "FR"),
    (4,  9, "Lion",         "eng", "US"),
    (5,  9, "Asiatic Lion", "eng", "IN"),
    (6,  9, "León",         "spa", "ES"),
    (7, 10, "Jaguar",       "eng", "US"),
    (8, 10, "El Jaguar",    "spa", "MX"),
]


def seed(db_path: Path) -> tuple[int, int]:
    if db_path.exists(): db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    taxon_insert = (
        "INSERT INTO taxon (id, parent_id, rank, status, scientific_name, authorship) "
        "VALUES (?, ?, ?, ?, ?, ?)"
    )
    vernacular_insert = (
        "INSERT INTO vernacular (id, taxon_id, name, language, country) "
        "VALUES (?, ?, ?, ?, ?)"
    )
    cursor = conn.cursor()
    for row in TAXON_ROWS:
        cursor.execute(taxon_insert, row)
    for row in VERNACULAR_ROWS:
        cursor.execute(vernacular_insert, row)
    cursor.execute("UPDATE taxon SET coldp_id = ? WHERE id = ?", ("Eukaryota", 1))
    conn.commit()
    n_t = conn.execute("SELECT COUNT(*) FROM taxon").fetchone()[0]
    n_v = conn.execute("SELECT COUNT(*) FROM vernacular").fetchone()[0]
    conn.close()
    return n_t, n_v


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1
               else "tests/fixtures/g4/sqlite/taxa-fixture.db")
    n_t, n_v = seed(out)
    print(f"seeded {n_t} taxon + {n_v} vernacular rows -> {out}")