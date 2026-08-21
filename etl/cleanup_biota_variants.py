"""
One-shot cleanup of orphan Biota form/variety taxa.

Background
----------
The CoL TextTree parser sometimes assigns parent_id=NULL to short infraspecific
names ("Biota orientalis f. ..."), which then appear as roots under
/api/domains and confuse the tree with the legitimate Biota superdomain (WoRMS
root, worms_id=1) and the Biota genus (Platycladus synonym, id=5315856).

Investigation on 2026-08-21 found 13 such rows — all named "Biota" with rank
'form' or 'variety', all parented to id=5315857 (Platycladus orientalis), with
zero vernaculars and zero distribution rows. Safe to remove.

This script is idempotent: re-running after the rows are gone just reports
zero affected rows.

Usage
-----
    .venv/bin/python etl/cleanup_biota_variants.py
    .venv/bin/python etl/cleanup_biota_variants.py --dry-run

Why a script (not a SQL migration)
----------------------------------
The DB itself is git-ignored (data/db/*.db) — it's a build artifact, not
source. The cleanup logic must live in version control so any rebuild of the
DB from raw inputs can re-apply it.
"""
from __future__ import annotations
import argparse
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "db" / "taxa.db"
TARGET_RANKS = ("form", "variety")
TARGET_NAME = "Biota"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be deleted without touching the DB.",
    )
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"[error] DB not found at {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    try:
        # Snapshot first so the script can describe what it's about to remove.
        rows = conn.execute(
            "SELECT id, scientific_name, rank, parent_id, coldp_id, worms_id "
            "FROM taxon WHERE scientific_name = ? AND rank IN (?, ?)",
            (TARGET_NAME, *TARGET_RANKS),
        ).fetchall()
        print(f"Found {len(rows)} '{TARGET_NAME}' rows with rank in {TARGET_RANKS}:")
        for r in rows:
            print(
                f"  id={r[0]}  rank={r[2]:<8}  parent_id={r[3]}  "
                f"coldp_id={r[4]!r:<10}  worms_id={r[5]!r}"
            )

        # Safety: confirm no references in dependent tables. We use a static
        # subquery instead of building an IN-list from Python, so no dynamic
        # identifiers ever enter the SQL string.
        if rows:
            vern_count = conn.execute(
                "SELECT count(*) FROM vernacular WHERE taxon_id IN ("
                "  SELECT id FROM taxon WHERE scientific_name = ? AND rank IN (?, ?)"
                ")",
                (TARGET_NAME, *TARGET_RANKS),
            ).fetchone()[0]
            dist_count = conn.execute(
                "SELECT count(*) FROM distribution WHERE taxon_id IN ("
                "  SELECT id FROM taxon WHERE scientific_name = ? AND rank IN (?, ?)"
                ")",
                (TARGET_NAME, *TARGET_RANKS),
            ).fetchone()[0]
            refs = []
            if vern_count:
                refs.append(f"vernacular={vern_count}")
            if dist_count:
                refs.append(f"distribution={dist_count}")
            if refs:
                print(
                    f"[abort] refusing to delete: rows are referenced by {', '.join(refs)}"
                )
                return 2

        if args.dry_run:
            print("[dry-run] no changes applied.")
            return 0

        with conn:
            deleted = conn.execute(
                "DELETE FROM taxon WHERE scientific_name = ? AND rank IN (?, ?)",
                (TARGET_NAME, *TARGET_RANKS),
            ).rowcount
        print(f"Deleted {deleted} rows.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
