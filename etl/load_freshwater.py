"""
Load the freshwater CSV into taxa.db as an isolated overlay.

Pipeline:
  1. Open taxa.db (WAL mode).
  2. Defensive check: verify the freshwater_id / freshwater_parent_id
     columns already exist. The schema migration is shipped in
     `etl/schema_v4.sql` (commit 3) and applied by the operator before
     running this loader on a fresh DB.
  3. Wipe any prior freshwater rows (`DELETE FROM taxon WHERE freshwater_id
     IS NOT NULL`); CoL and WoRMS rows are untouched.
  4. Insert the synthetic root ("Freshwater Fishes", rank="collection",
     freshwater_id=1, freshwater_parent_id=NULL).
  5. Stream the CSV row by row:
       - validate (non-empty name, known rank, parseable ints, parent resolves)
       - skip + log WARNING on any failure
       - INSERT with parent_id=NULL (kept out of CoL view by matchesTreeSource)
  6. Roll up the synthetic root's species_count via a recursive CTE.

Usage:
    python3 etl/load_freshwater.py <freshwater.csv> <taxa.db>

Idempotent: re-running clears all freshwater rows and re-inserts from
scratch. Schema migration is the operator's responsibility (apply
`etl/schema_v4.sql` before running this loader on a DB that doesn't
already have the overlay columns).

CSV format:
    freshwater_id,freshwater_parent_id,rank,scientific_name,authorship
    1,,collection,Freshwater Fishes,
    10,1,order,Characiformes,
    11,1,order,Siluriformes,
    100,10,family,Characidae,

Topological order is the user's responsibility in the CSV (parents appear
before children; the parent resolves to either the synthetic root or an
earlier CSV row inserted in the same pass).
"""
from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

DB_PATH_DEFAULT = "data/db/taxa.db"

# Mirrors RANK_ORDER in api/server.py + RANK_ORDER in web/app.js.
# `"collection"` is new for the synthetic root; it sorts above `"domain"`
# in the SQL CASE.
KNOWN_RANKS = {
    "collection",
    "domain",
    "superdomain",
    "kingdom",
    "subkingdom",
    "phylum",
    "subphylum",
    "class",
    "subclass",
    "order",
    "suborder",
    "family",
    "subfamily",
    "genus",
    "subgenus",
    "species",
    "subspecies",
    "variety",
    "subvariety",
    "form",
}


def _parse_int(s: str | None) -> int | None:
    """Parse a string as int; return None on empty/invalid input."""
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _is_header_row(row: list[str]) -> bool:
    """A row is treated as a header if the rank field isn't a known rank."""
    if len(row) < 3:
        return True
    rank = (row[2] or "").strip().lower()
    return rank not in KNOWN_RANKS


def _require_freshwater_columns(cur: sqlite3.Cursor) -> None:
    """Defensive check: the freshwater overlay columns must already exist.

    The migration is shipped in `etl/schema_v4.sql` (commit 3) and applied
    by the operator before running this loader. This guard exists so a
    missing column surfaces as a clear error instead of an obscure
    sqlite3.OperationalError at the first DELETE.
    """
    cols = {row[1] for row in cur.execute("PRAGMA table_info(taxon)")}
    if "freshwater_id" not in cols or "freshwater_parent_id" not in cols:
        missing = [
            c for c in ("freshwater_id", "freshwater_parent_id") if c not in cols
        ]
        raise sqlite3.OperationalError(
            f"taxon table is missing required columns: {missing}. "
            f"Apply etl/schema_v4.sql before running this loader."
        )


def load_freshwater(csv_path: Path, db_path: Path) -> int:
    """Load `csv_path` into `db_path`. Returns 0 on success, 1 on failure.

    Idempotent on data (wipe-and-reload). The freshwater overlay columns
    must already exist on the `taxon` table; see `etl/schema_v4.sql`.
    """
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 1

    con = sqlite3.connect(str(db_path), isolation_level=None)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode = WAL")
    cur.execute("PRAGMA synchronous = NORMAL")

    # Defensive check: the overlay columns must already exist (applied via
    # etl/schema_v4.sql before this loader runs).
    _require_freshwater_columns(cur)

    # Wipe prior freshwater rows. CoL rows (freshwater_id IS NULL) and WoRMS
    # rows (worms_id IS NOT NULL, freshwater_id IS NULL) are untouched.
    cur.execute("SELECT COUNT(*) FROM taxon WHERE freshwater_id IS NOT NULL")
    prev = cur.fetchone()[0]
    if prev:
        print(f"Clearing {prev:,} previously-loaded freshwater rows...")
        cur.execute("DELETE FROM taxon WHERE freshwater_id IS NOT NULL")

    # Insert synthetic root first. Reserve freshwater_id=1 for it.
    print("Inserting synthetic root (Freshwater Fishes, rank=collection)...")
    cur.execute("BEGIN")
    cur.execute(
        "INSERT INTO taxon "
        "(parent_id, rank, status, scientific_name, authorship, "
        "freshwater_id, freshwater_parent_id, is_extinct) "
        "VALUES (NULL, 'collection', 'accepted', 'Freshwater Fishes', NULL, "
        "1, NULL, 0)"
    )
    root_db_id = cur.lastrowid
    if root_db_id is None:
        print("ERROR: synthetic root INSERT returned no rowid", file=sys.stderr)
        con.close()
        return 1
    # fw_map: freshwater_id (from CSV) -> taxon.id (real DB row).
    fw_map: dict[int, int] = {1: root_db_id}

    n_inserted = 0
    n_skipped = 0

    print(f"Reading {csv_path}...")
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        # 1-indexed line numbers (line 1 = first row of the file, header or data).
        for line_no, row in enumerate(reader, start=1):
            if not row or all((c or "").strip() == "" for c in row):
                # Blank line — silently skip.
                continue
            if line_no == 1 and _is_header_row(row):
                # First row looks like a header — skip it.
                continue

            if len(row) < 4:
                print(
                    f"WARNING line {line_no}: too few columns ({len(row)} < 4), "
                    f"skipping",
                    file=sys.stderr,
                )
                n_skipped += 1
                continue

            fw_id = _parse_int(row[0])
            fw_parent_id = _parse_int(row[1])
            rank = (row[2] or "").strip().lower()
            name = (row[3] or "").strip()
            authorship = (row[4] or "").strip() if len(row) >= 5 else ""

            if fw_id is None:
                print(
                    f"WARNING line {line_no}: missing/invalid freshwater_id "
                    f"{row[0]!r}, skipping",
                    file=sys.stderr,
                )
                n_skipped += 1
                continue
            if fw_id in fw_map:
                print(
                    f"WARNING line {line_no}: duplicate freshwater_id {fw_id}, "
                    f"skipping",
                    file=sys.stderr,
                )
                n_skipped += 1
                continue
            if not name:
                print(
                    f"WARNING line {line_no}: empty scientific_name, skipping",
                    file=sys.stderr,
                )
                n_skipped += 1
                continue
            if rank not in KNOWN_RANKS:
                print(
                    f"WARNING line {line_no}: unknown rank {rank!r}, skipping",
                    file=sys.stderr,
                )
                n_skipped += 1
                continue

            # Parent resolution: freshwater_parent_id must point at the
            # synthetic root (fw_id=1 -> root_db_id) or another row already
            # inserted earlier in this pass.
            if fw_parent_id is None:
                # No parent. fw_id=1 means CSV is also shipping a root row
                # (which we already inserted); silently skip it. Otherwise
                # the row has no anchor in the chain.
                if fw_id == 1:
                    continue
                print(
                    f"WARNING line {line_no}: orphan — no parent "
                    f"(freshwater_parent_id is empty), skipping",
                    file=sys.stderr,
                )
                n_skipped += 1
                continue

            parent_db_id = fw_map.get(fw_parent_id)
            if parent_db_id is None:
                # Parent is some other CSV row that hasn't been inserted yet
                # OR an id that's not in the file at all. Either way, the
                # chain breaks here — log + skip.
                print(
                    f"WARNING line {line_no}: orphan — parent freshwater_id "
                    f"{fw_parent_id} not found, skipping",
                    file=sys.stderr,
                )
                n_skipped += 1
                continue

            # Insert. parent_id is always NULL: freshwater rows live in their
            # own hierarchy and must not pollute the CoL view.
            cur.execute(
                "INSERT INTO taxon "
                "(parent_id, rank, status, scientific_name, authorship, "
                "freshwater_id, freshwater_parent_id, is_extinct) "
                "VALUES (NULL, ?, 'accepted', ?, ?, ?, ?, 0)",
                (rank, name, authorship, fw_id, parent_db_id),
            )
            rowid = cur.lastrowid
            if rowid is None:
                print(
                    f"ERROR line {line_no}: INSERT returned no rowid",
                    file=sys.stderr,
                )
                con.close()
                return 1
            fw_map[fw_id] = rowid
            n_inserted += 1

    cur.execute("COMMIT")

    # Post-load: roll up species_count on the synthetic root via recursive
    # CTE. Walk all descendants under the synthetic root and count rows
    # whose rank is species or subspecies.
    cur.execute(
        """
        UPDATE taxon SET species_count = (
            WITH RECURSIVE descendants(id) AS (
                SELECT id FROM taxon WHERE freshwater_parent_id = :root_db_id
                UNION ALL
                SELECT t.id FROM taxon t JOIN descendants d
                    ON t.freshwater_parent_id = d.id
            )
            SELECT COUNT(*) FROM descendants d
            JOIN taxon t ON t.id = d.id
            WHERE t.rank IN ('species', 'subspecies')
        )
        WHERE id = :root_db_id
        """,
        {"root_db_id": root_db_id},
    )

    con.close()

    total = n_inserted + n_skipped
    print(f"Inserted: {n_inserted}")
    print(f"Skipped by validation: {n_skipped}")
    print(f"Total CSV rows: {total}")
    if n_inserted == 0:
        print("WARNING: 0 rows loaded; check input CSV")
    print("Done.")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(
            f"Usage: {sys.argv[0]} <freshwater.csv> [taxa.db]",
            file=sys.stderr,
        )
        return 1
    csv_path = Path(sys.argv[1])
    db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(DB_PATH_DEFAULT)
    return load_freshwater(csv_path, db_path)


if __name__ == "__main__":
    sys.exit(main())
