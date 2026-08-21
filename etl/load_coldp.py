"""
Load ColDP enrichments into the existing taxa.db.

Pipeline:
  1. Apply schema_v2.sql (adds coldp_id column + vernacular table + FTS5).
  2. Stream NameUsage.tsv (1.8 GB) — extract only (ID, scientificName, rank,
     status) for accepted taxa into a temp table. Then UPDATE taxon.coldp_id
     via a single JOIN on (name, rank).
  3. Stream VernacularName.tsv (12 MB) — bulk insert vernacular rows with
     coldp_id → taxon_id resolved via JOIN.

Usage:
    python load_coldp.py <path/to/coldp/folder> <path/to/taxa.db>
"""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    coldp_dir = Path(sys.argv[1])
    db_path = Path(sys.argv[2])
    schema_v2 = Path(__file__).parent / "schema_v2.sql"

    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 1

    nameusage = coldp_dir / "NameUsage.tsv"
    vernacular = coldp_dir / "VernacularName.tsv"

    print(f"Loading CoL enrichments into {db_path}")
    print(f"  NameUsage:    {nameusage}")
    print(f"  Vernacular:   {vernacular}")
    t0 = time.perf_counter()

    conn = sqlite3.connect(db_path, isolation_level=None)
    cur = conn.cursor()

    # Idempotent migration: ensure coldp_id column exists. SQLite has no
    # ADD COLUMN IF NOT EXISTS; pragma_table_info is the portable check.
    cur.execute("PRAGMA table_info(taxon)")
    cols = {row[1] for row in cur.fetchall()}
    if "coldp_id" not in cols:
        cur.execute("ALTER TABLE taxon ADD COLUMN coldp_id TEXT")
        print("  migrated: added taxon.coldp_id")
    if "is_extinct" not in cols:
        cur.execute("ALTER TABLE taxon ADD COLUMN is_extinct INTEGER NOT NULL DEFAULT 0")
        print("  migrated: added taxon.is_extinct")

    conn.executescript(schema_v2.read_text())

    # ------------------------------------------------------------------
    # Phase 1: load NameUsage.tsv (coldp_id, name, rank) for accepted taxa.
    # We only need 4 columns out of 60+ — the file is huge so we stream
    # line-by-line and use a tab-based split (much faster than csv module).
    # ------------------------------------------------------------------
    print("\nPhase 1: streaming NameUsage.tsv (1.8 GB)...")
    t1 = time.perf_counter()

    # The matching UPDATE runs on the JOIN coldp_map(name,rank,status) ↔
    # taxon(scientific_name,rank). Build covering indexes BEFORE the
    # bulk insert so the join is O(N log N) instead of O(N²).

    cur.execute("""
        CREATE TEMP TABLE coldp_map (
            coldp_id TEXT PRIMARY KEY,
            name     TEXT    NOT NULL,
            rank     TEXT    NOT NULL,
            status   TEXT    NOT NULL
        ) WITHOUT ROWID
    """)
    cur.execute("""
        CREATE TEMP TABLE coldp_extinct (
            coldp_id TEXT PRIMARY KEY
        ) WITHOUT ROWID
    """)

    # Indexes for the (name, rank, status) UPDATE join in phase 2.
    cur.execute("CREATE INDEX temp.idx_coldp_map_nrs ON coldp_map(name, rank, status)")
    # Index on the real taxon table — needed for the UPDATE join in phase 2.
    # Idempotent: skip if already present from a previous run.
    cur.execute("""
        SELECT 1 FROM sqlite_master
        WHERE type='index' AND name='idx_taxon_name_rank_for_coldp'
    """)
    if not cur.fetchone():
        cur.execute("""
            CREATE INDEX idx_taxon_name_rank_for_coldp
            ON taxon(scientific_name, rank) WHERE coldp_id IS NULL
        """)

    ID, STATUS, NAME, RANK, EXTINCT = 0, 6, 7, 9, 45  # column indices in the TSV

    n_lines = 0
    n_accepted = 0
    n_synonym = 0
    n_extinct = 0
    batch: list[tuple] = []
    batch_extinct: list[tuple] = []
    BATCH = 50_000

    with nameusage.open("r", encoding="utf-8") as fh:
        # Header.
        next(fh)
        for raw in fh:
            n_lines += 1
            cols = raw.rstrip("\n").split("\t")
            if len(cols) < 73:
                continue
            coldp_id = cols[ID]
            name = cols[NAME]
            rank = cols[RANK]
            if not coldp_id or not name:
                continue
            if cols[STATUS] == "accepted":
                batch.append((coldp_id, name, rank, "accepted"))
                n_accepted += 1
            elif cols[STATUS] == "synonym":
                batch.append((coldp_id, name, rank, "synonym"))
                n_synonym += 1
            if cols[EXTINCT] == "true":
                batch_extinct.append((coldp_id,))
                n_extinct += 1
            if len(batch) >= BATCH:
                cur.execute("BEGIN")
                cur.executemany(
                    "INSERT OR IGNORE INTO coldp_map VALUES (?, ?, ?, ?)", batch
                )
                cur.execute("COMMIT")
                batch.clear()
            if len(batch_extinct) >= BATCH:
                cur.execute("BEGIN")
                cur.executemany(
                    "INSERT OR IGNORE INTO coldp_extinct VALUES (?)", batch_extinct
                )
                cur.execute("COMMIT")
                batch_extinct.clear()
            if n_lines % 1_000_000 == 0:
                elapsed = time.perf_counter() - t1
                print(f"  scanned {n_lines:>12,} lines  "
                      f"({n_lines/elapsed:,.0f}/s)  "
                      f"accepted={n_accepted:,}  synonym={n_synonym:,}  "
                      f"extinct={n_extinct:,}", flush=True)

        if batch:
            cur.execute("BEGIN")
            cur.executemany(
                "INSERT OR IGNORE INTO coldp_map VALUES (?, ?, ?, ?)", batch
            )
            cur.execute("COMMIT")
        if batch_extinct:
            cur.execute("BEGIN")
            cur.executemany(
                "INSERT OR IGNORE INTO coldp_extinct VALUES (?)", batch_extinct
            )
            cur.execute("COMMIT")

    p1_elapsed = time.perf_counter() - t1
    cur.execute("SELECT COUNT(*) FROM coldp_map")
    n_map = cur.fetchone()[0]
    print(f"  done in {p1_elapsed:.1f}s — {n_map:,} unique (coldp_id,name,rank,status) rows", flush=True)

    # ------------------------------------------------------------------
    # Phase 2: link coldp_id to our existing taxon rows.
    # Many scientific names are homonyms (e.g. "Aotus" = primate genus AND
    # plant genus). Disambiguate by (name, rank, status) — accepting on the
    # 'accepted' side resolves most collisions, since TextTree and CoL agree
    # on the canonical concept for a (name, rank).
    # ------------------------------------------------------------------
    print("\nPhase 2: linking coldp_id to taxon by (name, rank, status)...")
    t2 = time.perf_counter()
    # First pass: match accepted taxa in taxon ↔ accepted coldp rows.
    cur.execute("""
        UPDATE taxon SET coldp_id = (
            SELECT cm.coldp_id FROM coldp_map cm
            WHERE cm.name = taxon.scientific_name
              AND cm.rank = taxon.rank
              AND cm.status = 'accepted'
            LIMIT 1
        )
        WHERE coldp_id IS NULL
          AND status = 'accepted'
    """)
    p2a = time.perf_counter() - t2
    print(f"  accepted pass: {p2a:.1f}s", flush=True)
    # Second pass: synonym taxa ↔ synonym coldp rows (less common but free win).
    t2b = time.perf_counter()
    cur.execute("""
        UPDATE taxon SET coldp_id = (
            SELECT cm.coldp_id FROM coldp_map cm
            WHERE cm.name = taxon.scientific_name
              AND cm.rank = taxon.rank
              AND cm.status = 'synonym'
            LIMIT 1
        )
        WHERE coldp_id IS NULL
          AND status = 'synonym'
    """)
    p2b = time.perf_counter() - t2b
    print(f"  synonym pass:  {p2b:.1f}s", flush=True)
    p2_elapsed = p2a + p2b

    cur.execute("SELECT COUNT(*) FROM taxon WHERE coldp_id IS NOT NULL")
    n_linked = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM taxon")
    n_total = cur.fetchone()[0]
    print(f"  done in {p2_elapsed:.1f}s — linked {n_linked:,} / {n_total:,} "
          f"({n_linked/n_total:.1%})")

    cur.execute("DROP TABLE coldp_map")

    # Mark extinct taxa via coldp_id.
    cur.execute("""
        UPDATE taxon SET is_extinct = 1
        WHERE coldp_id IN (SELECT coldp_id FROM coldp_extinct)
    """)
    cur.execute("DROP TABLE coldp_extinct")
    cur.execute("SELECT COUNT(*) FROM taxon WHERE is_extinct = 1")
    n_extinct_total = cur.fetchone()[0]
    print(f"  marked {n_extinct_total:,} taxa as extinct")

    # ------------------------------------------------------------------
    # Phase 3: stream VernacularName.tsv into a temp staging table, then
    # bulk-insert into `vernacular` with coldp_id → taxon_id resolved via JOIN.
    # ------------------------------------------------------------------
    print("\nPhase 3: loading VernacularName.tsv (12 MB)...")
    t3 = time.perf_counter()

    cur.execute("""
        CREATE TEMP TABLE vernacular_staging (
            taxonID        TEXT,
            name           TEXT,
            language       TEXT,
            country        TEXT
        )
    """)

    TAXON_ID, NAME_V, LANG, COUNTRY = 0, 2, 4, 6
    n_vern = 0
    batch = []
    with vernacular.open("r", encoding="utf-8") as fh:
        next(fh)  # header
        for raw in fh:
            cols = raw.rstrip("\n").split("\t")
            if len(cols) < 7:
                continue
            batch.append((cols[TAXON_ID], cols[NAME_V], cols[LANG], cols[COUNTRY]))
            n_vern += 1
            if len(batch) >= BATCH:
                cur.execute("BEGIN")
                cur.executemany(
                    "INSERT INTO vernacular_staging VALUES (?, ?, ?, ?)", batch
                )
                cur.execute("COMMIT")
                batch.clear()

        if batch:
            cur.execute("BEGIN")
            cur.executemany(
                "INSERT INTO vernacular_staging VALUES (?, ?, ?, ?)", batch
            )
            cur.execute("COMMIT")

    p3_elapsed = time.perf_counter() - t3
    print(f"  staged {n_vern:,} vernacular rows in {p3_elapsed:.1f}s")

    # Resolve coldp_id → taxon_id, drop unresolved rows.
    t4 = time.perf_counter()
    cur.execute("""
        INSERT INTO vernacular (taxon_id, name, language, country)
        SELECT t.id, s.name, s.language, s.country
        FROM vernacular_staging s
        JOIN taxon t ON t.coldp_id = s.taxonID
        WHERE s.name <> ''
    """)
    p4_elapsed = time.perf_counter() - t4

    cur.execute("SELECT COUNT(*) FROM vernacular")
    n_vern_resolved = cur.fetchone()[0]
    print(f"  resolved {n_vern_resolved:,} vernacular rows "
          f"({n_vern_resolved/n_vern:.1%} of staged) in {p4_elapsed:.1f}s")

    cur.execute("DROP TABLE vernacular_staging")

    # ------------------------------------------------------------------
    # Phase 4: ANALYZE so the query planner has fresh stats.
    # ------------------------------------------------------------------
    cur.execute("ANALYZE")

    # Final stats.
    cur.execute("""
        SELECT language, COUNT(*) AS n
        FROM vernacular
        WHERE language IS NOT NULL AND language <> ''
        GROUP BY language
        ORDER BY n DESC
        LIMIT 10
    """)
    print("\nTop vernacular languages:")
    for lang, n in cur.fetchall():
        print(f"  {lang:6} {n:>10,}")

    total_elapsed = time.perf_counter() - t0
    print(f"\nDone in {total_elapsed:.1f}s")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())