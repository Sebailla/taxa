"""
One-shot cleanup of orphan Biota form/variety taxa.

Background
----------
This script targets a specific post-enrichment state of taxa.db. The lifecycle
that produces the rows we delete looks like this:

1. **TextTree parse** (etl/parse_textree.py): CoL TextTree assigns parent_id=NULL
   to short infraspecific names like "Biota orientalis f. ...". In this raw
   state they DO surface as roots under /api/domains — see api/server.py:188,
   which filters `parent_id IS NULL`.
2. **ColDP enrichment** (etl/load_coldp.py): matches each row to ColDP by
   (name, rank) and reparents it to the actual CoL parent (here, Platycladus
   orientalis, id=5315857) plus fills in coldp_id. After this step the rows
   are no longer roots in CoL view.
3. **WoRMS enrichment** (etl/load_worms.py): a small subset of these rows may
   be matched against WoRMS by name+rank and get a worms_id. Those are
   legitimate marine-overlay entries and must be kept.

This script runs at stage 3+, after WoRMS enrichment. It only deletes rows
that have neither coldp_id nor worms_id (i.e. orphan in both overlays) AND
are named "Biota" with rank in (form, variety). On a 2026-08-21 investigation
that matched 13 rows with zero vernaculars and zero distribution references,
all of which were the Platycladus orientalis infraspecific variants.

Usage
-----
    .venv/bin/python etl/cleanup_biota_variants.py
    .venv/bin/python etl/cleanup_biota_variants.py --dry-run

Idempotent
----------
Re-running after the rows are gone just reports zero affected rows and exits
cleanly. The safety check below runs against the live DB and refuses to
delete if any row has a vernacular, distribution, or accepted_id reference.

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

# Investigation that motivated this script:
#   date: 2026-08-21
#   match count: 13 rows named 'Biota' with rank in (form, variety)
#   post-load_coldp state: all parented to Platycladus orientalis (id=5315857),
#     zero vernaculars, zero distribution references.
# Hoisted to module scope so future readers can see the scope of the cleanup
# without grepping git history or running the script on the current DB.
INVESTIGATION_DATE = "2026-08-21"
INVESTIGATION_ROW_COUNT = 13


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
        # The worms_id IS NULL filter is load-bearing: it excludes any Biota
        # form/variety that the WoRMS overlay matched by (name, rank). Those
        # are legitimate marine-overlay entries — not orphans — and deleting
        # them would silently remove them from /api/taxon/{id} queries that
        # use source=worms.
        rows = conn.execute(
            "SELECT id, scientific_name, rank, parent_id, coldp_id, worms_id "
            "FROM taxon "
            "WHERE scientific_name = ? AND rank IN (?, ?) AND worms_id IS NULL",
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
        #
        # Three checks because SQLite's FK enforcement is off by default
        # (etl/cleanup_biota_variants.py connects without PRAGMA
        # foreign_keys=ON, so the ON DELETE CASCADE declared on
        # taxon.parent_id does NOT fire). Without these checks we could
        # silently orphan rows whose parent_id or accepted_id points at one
        # of our targets.
            if rows:
                # All four reference counts in one round-trip. The target filter
                # is constant (no user input) so the subquery is safe to inline.
                # All user-provided values flow through ? placeholders + params.
                #
                # Why four checks: SQLite's FK enforcement is off by default in
                # this script (no PRAGMA foreign_keys=ON at connect time), so
                # the ON DELETE CASCADE declared on taxon.parent_id does NOT
                # fire. Without these checks we could silently orphan rows whose
                # parent_id or accepted_id points at one of our targets.
                #   - vernacular / distribution: leaf tables pointing at us
                #   - taxon.parent_id: children whose parent we'd become
                #   - taxon.accepted_id: synonyms whose accepted name we'd
                #     dangle; accepted_id has no ON DELETE clause in
                #     etl/schema.sql:14
                #
                # Each ? placeholder is replaced by the same (TARGET_NAME, ranks)
                # tuple. The subquery has no FROM clause of its own so the outer
                # SELECT always returns exactly one row of four counts.
                row = conn.execute(
                    """
                    SELECT
                      (SELECT count(*) FROM vernacular WHERE taxon_id IN (
                         SELECT id FROM taxon
                         WHERE scientific_name = ? AND rank IN (?, ?) AND worms_id IS NULL
                      )),
                      (SELECT count(*) FROM distribution WHERE taxon_id IN (
                         SELECT id FROM taxon
                         WHERE scientific_name = ? AND rank IN (?, ?) AND worms_id IS NULL
                      )),
                      (SELECT count(*) FROM taxon WHERE parent_id IN (
                         SELECT id FROM taxon
                         WHERE scientific_name = ? AND rank IN (?, ?) AND worms_id IS NULL
                      )),
                      (SELECT count(*) FROM taxon WHERE accepted_id IN (
                         SELECT id FROM taxon
                         WHERE scientific_name = ? AND rank IN (?, ?) AND worms_id IS NULL
                      ))
                    """,
                    (TARGET_NAME, *TARGET_RANKS) * 4,
                ).fetchone()
                # Defensive: the outer SELECT has no FROM so it always returns
                # exactly one row. If somehow it returns None (DB corruption,
                # older SQLite, etc.) we abort rather than dereference None.
                if row is None:
                    print("[abort] reference-count query returned no row.")
                    return 2
                vern_count = row[0]
                dist_count = row[1]
                child_count = row[2]
                syn_count = row[3]
                refs = []
                if vern_count:
                    refs.append(f"vernacular={vern_count}")
                if dist_count:
                    refs.append(f"distribution={dist_count}")
                if child_count:
                    refs.append(f"taxon children (parent_id -> us)={child_count}")
                if syn_count:
                    refs.append(f"synonyms (accepted_id -> us)={syn_count}")
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
