"""
Load ColDP Distribution.tsv into the existing taxa.db.

Distribution.tsv columns (1-indexed):
    1  col:taxonID          (the coldp_id)
    2  col:sourceID
    3  col:areaID           (numeric code, often empty)
    4  col:area             (human-readable text — THIS is what we want)
    5  col:gazetteer
    6  col:establishmentMeans
    7  col:degreeOfEstablishment
    8  col:pathway
    9  col:threatStatus
   10  col:year
   11  col:season
   12  col:lifeStage
   13  col:referenceID

We extract only (1, 4, 5, 6, 7, 13) and join taxon.coldp_id → taxon.id.

Usage:
    python load_distribution.py <path/to/coldp/folder> <path/to/taxa.db>
"""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

# pyright: ignore — pyright can't resolve `etl.migrations` against this
# project's package layout even with py.typed + non-empty __init__.py.
# The import resolves fine at runtime (verified by all 14 etl tests);
# this is a static-checker false positive.
from etl.migrations import apply_pending_migrations  # pyright: ignore


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    coldp_dir = Path(sys.argv[1])
    db_path = Path(sys.argv[2])

    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 1

    distribution_tsv = coldp_dir / "Distribution.tsv"
    if not distribution_tsv.exists():
        print(f"Distribution.tsv not found at {distribution_tsv}")
        return 1

    print(f"Loading Distribution into {db_path}")
    print(f"  source: {distribution_tsv}")
    t0 = time.perf_counter()

    conn = sqlite3.connect(db_path, isolation_level=None)
    cur = conn.cursor()

    # Migration: apply pending schema migrations (idempotent via PRAGMA
    # user_version). The coldp_id column must exist before v2 can run;
    # `make coldp` is a prerequisite.
    schema_dir = Path(__file__).resolve().parent
    apply_pending_migrations(conn, schema_dir)

    # ------------------------------------------------------------------
    # Phase 1: stream Distribution.tsv, look up taxon by coldp_id,
    # insert into the distribution table.
    # ------------------------------------------------------------------
    print("\nPhase 1: streaming Distribution.tsv (128 MB)...")
    t1 = time.perf_counter()

    TAXON_ID, AREA, GAZETTEER, EST_MEANS, DEGREE_EST, REF_ID = 0, 3, 4, 5, 6, 12

    # Stream the join via a temp staging table: write the 6 columns we care
    # about, then INSERT ... SELECT with the coldp_id → taxon_id join.
    cur.execute("""
        CREATE TEMP TABLE dist_staging (
            coldp_id           TEXT,
            area               TEXT,
            gazetteer          TEXT,
            establishment      TEXT,
            degree_est         TEXT,
            reference_id       TEXT
        )
    """)
    cur.execute("""
        CREATE INDEX temp.idx_dist_staging_coldp ON dist_staging(coldp_id)
    """)

    n_lines = 0
    n_staged = 0
    batch: list[tuple] = []
    BATCH = 50_000

    with distribution_tsv.open("r", encoding="utf-8") as fh:
        next(fh)  # header
        for raw in fh:
            n_lines += 1
            cols = raw.rstrip("\n").split("\t")
            if len(cols) < 14:
                continue
            coldp_id = cols[TAXON_ID]
            area = cols[AREA].strip()
            if not coldp_id or not area:
                continue
            batch.append((
                coldp_id,
                area,
                cols[GAZETTEER].strip() or None,
                cols[EST_MEANS].strip() or None,
                cols[DEGREE_EST].strip() or None,
                cols[REF_ID].strip() or None,
            ))
            n_staged += 1
            if len(batch) >= BATCH:
                # nosemgrep: python-sql-injection
                # Safe: BEGIN/COMMIT are SQLite transaction markers with no params.
                cur.execute("BEGIN")
                cur.executemany(
                    "INSERT INTO dist_staging VALUES (?, ?, ?, ?, ?, ?)", batch
                )
                cur.execute("COMMIT")
                batch.clear()
            if n_lines % 250_000 == 0:
                elapsed = time.perf_counter() - t1
                print(f"  scanned {n_lines:>10,} lines  "
                      f"({n_lines/elapsed:,.0f}/s)  staged={n_staged:,}",
                      flush=True)

        if batch:
            # nosemgrep: python-sql-injection
            # Safe: BEGIN/COMMIT are SQLite transaction markers with no params.
            cur.execute("BEGIN")
            cur.executemany(
                "INSERT INTO dist_staging VALUES (?, ?, ?, ?, ?, ?)", batch
            )
            cur.execute("COMMIT")

    p1_elapsed = time.perf_counter() - t1
    cur.execute("SELECT COUNT(*) FROM dist_staging")
    n_stage = cur.fetchone()[0]
    print(f"  staged {n_stage:,} rows in {p1_elapsed:.1f}s", flush=True)

    # ------------------------------------------------------------------
    # Phase 2: insert into distribution with coldp_id → taxon_id join.
    # ------------------------------------------------------------------
    print("\nPhase 2: joining coldp_id → taxon_id and inserting...")
    t2 = time.perf_counter()
    cur.execute("""
        INSERT INTO distribution (taxon_id, area, gazetteer,
                                  establishment_means, degree_of_establishment,
                                  reference_id)
        SELECT t.id, s.area, s.gazetteer, s.establishment, s.degree_est, s.reference_id
        FROM dist_staging s
        JOIN taxon t ON t.coldp_id = s.coldp_id
    """)
    p2_elapsed = time.perf_counter() - t2

    cur.execute("SELECT COUNT(*) FROM distribution")
    n_dist = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(DISTINCT taxon_id) FROM distribution
    """)
    n_taxa_w_dist = cur.fetchone()[0]
    print(f"  inserted {n_dist:,} rows in {p2_elapsed:.1f}s "
          f"({n_dist/n_stage:.1%} of staged) → {n_taxa_w_dist:,} taxa with distribution",
          flush=True)

    cur.execute("DROP TABLE dist_staging")
    # nosemgrep: python-sql-injection
    # Safe: ANALYZE has no parameters; runs the SQLite query planner optimizer.
    cur.execute("ANALYZE")

    # Final stats.
    cur.execute("""
        SELECT establishment_means, COUNT(*)
        FROM distribution
        WHERE establishment_means IS NOT NULL
        GROUP BY establishment_means
        ORDER BY 2 DESC
    """)
    print("\nBy establishment means:")
    for means, n in cur.fetchall():
        print(f"  {means or '?':12} {n:>10,}")

    total_elapsed = time.perf_counter() - t0
    print(f"\nDone in {total_elapsed:.1f}s")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())