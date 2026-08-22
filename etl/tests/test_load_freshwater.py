"""
Tests for etl/load_freshwater.py — AC-1 through AC-7.

Each test runs against an in-memory SQLite (see conftest.py::db_conn) seeded
with the v1+v2+v3 schema (no freshwater columns). The loader must add the
freshwater columns via idempotent ALTER, insert the synthetic root, validate
each row, skip bad rows, roll up species_count, and be idempotent across runs.

Run:
    pytest etl/tests/test_load_freshwater.py -v
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

# Path to the loader under test. It's run as a subprocess so each test
# inherits a clean Python module cache (no state bleeds across tests).
LOADER = Path(__file__).resolve().parent.parent / "load_freshwater.py"


def _run_loader(db_path: Path, csv_path: Path) -> subprocess.CompletedProcess:
    """Invoke the loader as a subprocess. Mirrors `make freshwater` usage."""
    return subprocess.run(
        [sys.executable, str(LOADER), str(csv_path), str(db_path)],
        capture_output=True,
        text=True,
    )


def _seed_col_and_worms(conn: sqlite3.Connection) -> None:
    """Insert 2 CoL rows + 1 WoRMS-only row + 1 CoL+WoRMS row for the
    idempotency test.

    The point is to assert these survive a wipe-and-reload run of the
    freshwater loader:
      - CoL-only rows: coldp_id set, worms_id NULL.
      - WoRMS-only row: coldp_id NULL, worms_id=1 (the Biota superdomain).
      - CoL+WoRMS row: both coldp_id and worms_id set (a CoL row enriched
        by the WoRMS loader).

    The freshwater loader only touches rows where freshwater_id IS NOT
    NULL, so all four must survive.
    """
    conn.execute(
        "INSERT INTO taxon (parent_id, rank, status, scientific_name, "
        "authorship, coldp_id, worms_id, is_extinct) "
        "VALUES (NULL, 'domain', 'accepted', 'Eukaryota', NULL, 'col-dom-1', "
        "NULL, 0)"
    )
    conn.execute(
        "INSERT INTO taxon (parent_id, rank, status, scientific_name, "
        "authorship, coldp_id, worms_id, is_extinct) "
        "VALUES (NULL, 'superdomain', 'accepted', 'Biota', NULL, NULL, 1, 0)"
    )
    conn.execute(
        "INSERT INTO taxon (parent_id, rank, status, scientific_name, "
        "authorship, coldp_id, worms_id, is_extinct) "
        "VALUES (1, 'kingdom', 'accepted', 'Animalia', NULL, 'col-anim-1', "
        "NULL, 0)"
    )
    conn.execute(
        "INSERT INTO taxon (parent_id, rank, status, scientific_name, "
        "authorship, coldp_id, worms_id, is_extinct) "
        "VALUES (1, 'kingdom', 'accepted', 'Chromista', NULL, 'col-chrom-1', "
        "2, 0)"
    )
    conn.commit()


def test_load_freshwater_inserts_synthetic_root_and_orders(bootstrapped_db, write_csv):
    """AC-1: CSV with 4 rows → 4 rows in taxon with freshwater_id set, root has
    rank='collection' and freshwater_parent_id IS NULL."""
    db_path = bootstrapped_db
    csv_path = write_csv([
        ["1", "", "collection", "Freshwater Fishes", ""],
        ["10", "1", "order", "Characiformes", ""],
        ["11", "1", "order", "Siluriformes", ""],
        ["12", "1", "order", "Cypriniformes", ""],
    ])
    result = _run_loader(db_path, csv_path)
    assert result.returncode == 0, (
        f"loader failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    # Open the persisted DB the loader wrote and verify.
    fresh = sqlite3.connect(db_path)
    fresh.row_factory = sqlite3.Row
    rows = fresh.execute(
        "SELECT id, parent_id, rank, scientific_name, freshwater_id, "
        "freshwater_parent_id FROM taxon WHERE freshwater_id IS NOT NULL "
        "ORDER BY freshwater_id"
    ).fetchall()
    assert len(rows) == 4, f"expected 4 freshwater rows, got {len(rows)}"
    # Root row is the synthetic root.
    root = rows[0]
    assert root["scientific_name"] == "Freshwater Fishes"
    assert root["rank"] == "collection"
    assert root["freshwater_parent_id"] is None
    assert root["freshwater_id"] == 1
    # CSV rows each have freshwater_id 10/11/12 with freshwater_parent_id=1.
    for r, expected_fw_id in zip(rows[1:], (10, 11, 12)):
        assert r["freshwater_id"] == expected_fw_id
        assert r["freshwater_parent_id"] == root["id"], (
            f"row {expected_fw_id} should point at root {root['id']}"
        )
    # All CSV rows have parent_id=NULL (kept out of the CoL hierarchy).
    for r in rows[1:]:
        assert r["parent_id"] is None, (
            f"freshwater row {r['freshwater_id']} should have parent_id=NULL "
            "to keep it out of the CoL view"
        )
    fresh.close()


def test_load_freshwater_skips_orphan_parents(bootstrapped_db, write_csv):
    """AC-2: Rows with freshwater_parent_id pointing at nothing in the file
    are skipped with a WARNING; valid rows are inserted."""
    csv_path = write_csv([
        ["1", "", "collection", "Freshwater Fishes", ""],
        ["10", "1", "order", "Characiformes", ""],
        ["11", "1", "order", "Siluriformes", ""],
        # orphan: parent 999 is not in the CSV and not the root (id 1)
        ["20", "999", "order", "OrphanOrder", ""],
        ["21", "999", "order", "OrphanOrder2", ""],
        ["30", "1", "family", "Characidae", ""],
    ])
    db_path = bootstrapped_db
    result = _run_loader(db_path, csv_path)
    assert result.returncode == 0, (
        f"loader failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    # Loader must have logged warnings on stderr for the 2 orphans.
    assert "999" in result.stderr, (
        f"orphan parent id 999 should appear in stderr, got: {result.stderr!r}"
    )
    assert "WARNING" in result.stderr.upper(), (
        f"loader should emit WARNING for orphans, got: {result.stderr!r}"
    )
    # Lines 5 and 6 of the CSV (1-indexed, after the root at line 1) are
    # the orphan rows. Loader should name them so the user can fix the file.
    assert "line 5" in result.stderr or "line5" in result.stderr.replace(" ", ""), (
        f"loader should report line numbers, got: {result.stderr!r}"
    )
    # Verify the DB: root + 3 valid rows (10, 11, 30), no orphan rows.
    fresh = sqlite3.connect(db_path)
    fresh.row_factory = sqlite3.Row
    rows = fresh.execute(
        "SELECT freshwater_id FROM taxon WHERE freshwater_id IS NOT NULL "
        "ORDER BY freshwater_id"
    ).fetchall()
    fw_ids = sorted(r["freshwater_id"] for r in rows)
    assert fw_ids == [1, 10, 11, 30], f"expected [1,10,11,30], got {fw_ids}"
    fresh.close()


def test_load_freshwater_skips_empty_scientific_name(bootstrapped_db, write_csv):
    """AC-3: Row with empty scientific_name is skipped with a WARNING; the
    rest of the file loads normally."""
    csv_path = write_csv([
        ["1", "", "collection", "Freshwater Fishes", ""],
        ["10", "1", "order", "Characiformes", ""],
        # empty scientific name → drop
        ["11", "1", "order", "", ""],
        ["12", "1", "order", "Cypriniformes", ""],
    ])
    db_path = bootstrapped_db
    result = _run_loader(db_path, csv_path)
    assert result.returncode == 0
    assert "WARNING" in result.stderr.upper()
    fresh = sqlite3.connect(db_path)
    fresh.row_factory = sqlite3.Row
    rows = fresh.execute(
        "SELECT freshwater_id FROM taxon WHERE freshwater_id IS NOT NULL "
        "ORDER BY freshwater_id"
    ).fetchall()
    fw_ids = sorted(r["freshwater_id"] for r in rows)
    assert fw_ids == [1, 10, 12], f"expected [1,10,12], got {fw_ids}"
    fresh.close()


def test_load_freshwater_skips_duplicate_freshwater_id(bootstrapped_db, write_csv):
    """AC-4: Duplicate freshwater_id → second occurrence is skipped; first
    wins. Loader logs a WARNING with the line number."""
    csv_path = write_csv([
        ["1", "", "collection", "Freshwater Fishes", ""],
        ["10", "1", "order", "Characiformes", ""],
        ["10", "1", "order", "Siluriformes_duplicate", ""],  # dup of 10
        ["11", "1", "order", "Siluriformes", ""],
    ])
    db_path = bootstrapped_db
    result = _run_loader(db_path, csv_path)
    assert result.returncode == 0
    assert "WARNING" in result.stderr.upper()
    assert "duplicate" in result.stderr.lower() or "10" in result.stderr, (
        f"duplicate warning should mention id 10, got: {result.stderr!r}"
    )
    # First row with id 10 wins; the second is skipped.
    fresh = sqlite3.connect(db_path)
    fresh.row_factory = sqlite3.Row
    rows = fresh.execute(
        "SELECT freshwater_id, scientific_name FROM taxon "
        "WHERE freshwater_id IS NOT NULL ORDER BY freshwater_id"
    ).fetchall()
    by_id = {r["freshwater_id"]: r["scientific_name"] for r in rows}
    assert by_id.get(10) == "Characiformes", (
        f"first write of id 10 should win, got {by_id.get(10)!r}"
    )
    assert 11 in by_id, "freshwater_id 11 should be inserted"
    fresh.close()


def test_load_freshwater_is_idempotent(bootstrapped_db, write_csv):
    """AC-5: Re-running the loader wipes prior freshwater rows; CoL and
    WoRMS rows survive untouched."""
    db_path = bootstrapped_db
    csv_path = write_csv([
        ["1", "", "collection", "Freshwater Fishes", ""],
        ["10", "1", "order", "Characiformes", ""],
    ])
    # Seed CoL + WoRMS rows in the same DB. We'll persist them via a direct
    # sqlite3 write so they survive the loader subprocess.
    bootstrap = sqlite3.connect(db_path)
    _seed_col_and_worms(bootstrap)
    bootstrap.commit()
    bootstrap.close()

    # First run.
    r1 = _run_loader(db_path, csv_path)
    assert r1.returncode == 0, f"first run failed: {r1.stderr}"
    after_first = sqlite3.connect(db_path)
    after_first.row_factory = sqlite3.Row
    n_fw1 = after_first.execute(
        "SELECT COUNT(*) FROM taxon WHERE freshwater_id IS NOT NULL"
    ).fetchone()[0]
    n_total1 = after_first.execute("SELECT COUNT(*) FROM taxon").fetchone()[0]
    # CoL/WoRMS rows: 4 (seeded). Freshwater rows: 2 (root + 1 order).
    assert n_fw1 == 2, f"first run: expected 2 freshwater rows, got {n_fw1}"
    assert n_total1 == 6, f"first run: expected 6 total, got {n_total1}"
    after_first.close()

    # Second run with a different CSV (different number of rows).
    csv_path2 = write_csv([
        ["1", "", "collection", "Freshwater Fishes", ""],
        ["10", "1", "order", "Characiformes", ""],
        ["11", "1", "order", "Siluriformes", ""],
        ["12", "1", "order", "Cypriniformes", ""],
    ], name="freshwater2.csv")
    r2 = _run_loader(db_path, csv_path2)
    assert r2.returncode == 0, f"second run failed: {r2.stderr}"
    after_second = sqlite3.connect(db_path)
    after_second.row_factory = sqlite3.Row
    n_fw2 = after_second.execute(
        "SELECT COUNT(*) FROM taxon WHERE freshwater_id IS NOT NULL"
    ).fetchone()[0]
    n_total2 = after_second.execute("SELECT COUNT(*) FROM taxon").fetchone()[0]
    # Freshwater count returned to the second run's count (4 rows incl. root).
    # CoL/WoRMS count (4) is unchanged.
    assert n_fw2 == 4, f"second run: expected 4 freshwater rows, got {n_fw2}"
    assert n_total2 == 8, (
        f"second run: CoL+WoRMS rows must survive — expected 8 total, "
        f"got {n_total2}"
    )
    # CoL/WoRMS rows unchanged: verify their counts.
    n_col = after_second.execute(
        "SELECT COUNT(*) FROM taxon WHERE coldp_id IS NOT NULL "
        "AND worms_id IS NULL"
    ).fetchone()[0]
    n_worms_only = after_second.execute(
        "SELECT COUNT(*) FROM taxon WHERE worms_id = 1"
    ).fetchone()[0]
    n_col_worms = after_second.execute(
        "SELECT COUNT(*) FROM taxon WHERE coldp_id IS NOT NULL "
        "AND worms_id IS NOT NULL"
    ).fetchone()[0]
    assert n_col == 2, f"CoL rows: expected 2, got {n_col}"
    assert n_worms_only == 1, f"WoRMS-only rows: expected 1, got {n_worms_only}"
    assert n_col_worms == 1, f"CoL+WoRMS rows: expected 1, got {n_col_worms}"
    after_second.close()


def test_load_freshwater_adds_columns_on_fresh_db(db_conn, write_csv, tmp_path):
    """AC-6: A fresh DB without freshwater_id columns → loader adds them via
    ALTER TABLE; a second run is a no-op on schema (idempotent)."""
    db_path = tmp_path / "taxa.db"
    # Bootstrap a DB with the v1+v2+v3 schema, no freshwater columns.
    bootstrap = sqlite3.connect(db_path)
    bootstrap.executescript(
        "CREATE TABLE taxon ("
        "id INTEGER PRIMARY KEY, parent_id INTEGER, rank TEXT NOT NULL, "
        "status TEXT NOT NULL, scientific_name TEXT NOT NULL, authorship TEXT, "
        "path TEXT, species_count INTEGER, accepted_id INTEGER, "
        "is_extinct INTEGER NOT NULL DEFAULT 0, coldp_id TEXT, worms_id INTEGER"
        ")"
    )
    bootstrap.commit()
    bootstrap.close()
    csv_path = write_csv([
        ["1", "", "collection", "Freshwater Fishes", ""],
        ["10", "1", "order", "Characiformes", ""],
    ])
    r1 = _run_loader(db_path, csv_path)
    assert r1.returncode == 0, f"first run failed: {r1.stderr}"
    # Confirm both columns now exist.
    fresh = sqlite3.connect(db_path)
    cols = {row[1] for row in fresh.execute("PRAGMA table_info(taxon)")}
    assert "freshwater_id" in cols, f"freshwater_id missing: {cols}"
    assert "freshwater_parent_id" in cols, (
        f"freshwater_parent_id missing: {cols}"
    )
    fresh.close()
    # Second run: idempotent on schema, no error.
    r2 = _run_loader(db_path, csv_path)
    assert r2.returncode == 0, (
        f"second run failed (should be idempotent): {r2.stderr}"
    )


def test_load_freshwater_rolls_up_species_count(bootstrapped_db, write_csv):
    """AC-7 + R-8: After loading, every freshwater node's species_count
    equals the count of species/subspecies rows in its subtree (not just
    the synthetic root's count)."""
    csv_path = write_csv([
        ["1", "", "collection", "Freshwater Fishes", ""],
        ["10", "1", "order", "Characiformes", ""],
        ["11", "1", "order", "Siluriformes", ""],
        # 3 species/subspecies under Characiformes (id 10)
        ["100", "10", "family", "Characidae", ""],
        ["101", "100", "genus", "Astyanax", ""],
        ["102", "101", "species", "Astyanax mexicanus", "(De Filippi, 1853)"],
        ["103", "101", "species", "Astyanax fasciatus", "(Cuvier, 1819)"],
        ["104", "101", "subspecies", "Astyanax fasciatus mexicanus", ""],
        # 1 species under Siluriformes (id 11)
        ["200", "11", "family", "Loricariidae", ""],
        ["201", "200", "genus", "Hypostomus", ""],
        ["202", "201", "species", "Hypostomus plecostomus", "(Linnaeus, 1758)"],
    ])
    db_path = bootstrapped_db
    result = _run_loader(db_path, csv_path)
    assert result.returncode == 0, (
        f"loader failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    fresh = sqlite3.connect(db_path)
    fresh.row_factory = sqlite3.Row
    # Each (scientific_name -> expected count) pair covers the entire
    # fixture: root sees the grand total; each intermediate node sees
    # only the species/subspecies in its own subtree.
    expected_counts = {
        "Freshwater Fishes": 4,    # root: 3 under Characiformes + 1 under Siluriformes
        "Characiformes":     3,    # mexicanus, fasciatus, mexicanus subsp.
        "Siluriformes":      1,    # plecostomus
        "Characidae":         3,    # same 3 as under Characiformes
        "Loricariidae":       1,    # same 1 as under Siluriformes
        "Astyanax":           3,    # 2 species + 1 subspecies
        "Hypostomus":         1,    # 1 species
    }
    rows = fresh.execute(
        "SELECT scientific_name, rank, species_count "
        "FROM taxon WHERE freshwater_id IS NOT NULL "
        "ORDER BY rank, scientific_name"
    ).fetchall()
    seen = {r["scientific_name"]: r["species_count"] for r in rows}
    for name, expected in expected_counts.items():
        assert name in seen, f"missing taxon {name!r} in freshwater rows"
        assert seen[name] == expected, (
            f"species_count on {name!r}: expected {expected}, got {seen[name]}"
        )
    fresh.close()
