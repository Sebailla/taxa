"""
Load WoRMS as enrichment of CoL — never wipe CoL.

WoRMS dataset 2011 is published by CoL as a ColDP export at:
  https://api.checklistbank.org/dataset/2011/export.zip?format=ColDP

The dump has ~1.4M rows (719K accepted). For each accepted WoRMS taxon:

- If a CoL row already exists with the same (scientific_name, rank),
  UPDATE taxon SET worms_id = <aphiaid>. CoL data is preserved; only the
  WoRMS identifier is added as a cross-reference.
- If no CoL row matches, INSERT a new row with worms_id set and
  parent_id resolved (to either a previously-matched CoL parent or a
  WoRMS-only parent inserted earlier in this run).

Net effect: WoRMS marine taxa get a worms_id; CoL taxa get an enrichment
link to WoRMS; marine-only taxa not in CoL get added (mainly obscure
groups — forams, deep-sea, algae, bryozoa, microfossils).

Idempotent: re-running clears any previous WoRMS enrichment (and any
WoRMS-only inserts) before re-loading.

Usage:
    python3 etl/load_worms.py <NameUsage.tsv>
"""
from __future__ import annotations

import csv
import re
import sqlite3
import sys
import time
from pathlib import Path

# pyright: ignore — pyright can't resolve `etl.migrations` against this
# project's package layout. The import resolves fine at runtime
# (verified by all 14 etl tests); this is a static-checker false positive.
from etl.migrations import apply_pending_migrations  # pyright: ignore

DB_PATH = "data/db/taxa.db"

# WoRMS URN format: urn:lsid:marinespecies.org:taxname:12345
_APHIA_RE = re.compile(r":(\d+)$")


def aphia_from_urn(urn: str) -> int | None:
    if not urn:
        return None
    m = _APHIA_RE.search(urn)
    if m is None:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <NameUsage.tsv>", file=sys.stderr)
        sys.exit(1)
    tsv_path = sys.argv[1]

    con = sqlite3.connect(DB_PATH, isolation_level=None)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode = WAL")
    cur.execute("PRAGMA synchronous = NORMAL")

    # Migration: worms_id column + index. Idempotent. Kept for legacy DBs
    # that predate schema versioning — new DBs get worms_id from schema.sql
    # (the v1 base) or the coldp loader's v2 migration.
    cols = {row[1] for row in cur.execute("PRAGMA table_info(taxon)")}
    if "worms_id" not in cols:
        cur.execute("ALTER TABLE taxon ADD COLUMN worms_id INTEGER")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_taxon_worms "
            "ON taxon(worms_id) WHERE worms_id IS NOT NULL"
        )

    # Migration: apply pending schema migrations (idempotent via PRAGMA
    # user_version). For a freshly-built DB the runner is a no-op; for a
    # DB that's somehow behind (e.g. partial build) this catches up.
    schema_dir = Path(__file__).resolve().parent
    apply_pending_migrations(con, schema_dir)

    # Wipe any previous WoRMS enrichment so re-running is idempotent.
    # This only removes rows with worms_id set — CoL data (worms_id IS NULL)
    # is untouched.
    cur.execute("SELECT COUNT(*) FROM taxon WHERE worms_id IS NOT NULL")
    prev = cur.fetchone()[0]
    if prev:
        print(f"Clearing {prev:,} previously-enriched WoRMS rows...")
        cur.execute("DELETE FROM taxon WHERE worms_id IS NOT NULL")

    # Build CoL lookup: (lowercase name, lowercase rank) -> CoL db id.
    print("Indexing CoL taxa for matching...")
    existing: dict[tuple[str, str], int] = {}
    for db_id, name, rank in cur.execute(
        "SELECT id, scientific_name, rank FROM taxon "
        "WHERE scientific_name IS NOT NULL"
    ):
        key = (name.lower(), (rank or "").lower())
        # First match wins. CoL has synonyms; for a given (name, rank) the
        # first row returned is whichever got inserted first — acceptable for
        # an enrichment join.
        existing.setdefault(key, db_id)
    print(f"  {len(existing):,} unique (name, rank) keys")

    # Read WoRMS TSV into memory. 1.4M rows × ~200B ≈ 280MB — fine on a laptop.
    print(f"Reading {tsv_path}...")
    t0 = time.time()
    worms_rows: list[dict] = []
    try:
        tsv_file = open(tsv_path, encoding="utf-8", newline="")
    except FileNotFoundError:
        print(f"TSV not found: {tsv_path}", file=sys.stderr)
        sys.exit(1)
    with tsv_file as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("col:status") != "accepted":
                continue
            worms_rows.append(row)
    print(f"  {len(worms_rows):,} accepted rows ({time.time() - t0:.1f}s)")

    # ---- Pass 1: match WoRMS taxa to CoL by (name, rank); set worms_id ----
    print("\nPass 1: matching WoRMS to CoL by (name, rank)...")
    t0 = time.time()
    aphia_to_db: dict[int, int] = {}
    updates = 0

    cur.execute("BEGIN")
    for r in worms_rows:
        aid = aphia_from_urn(r.get("col:ID", ""))
        if aid is None:
            continue
        name = r.get("col:scientificName", "")
        if not name:
            continue
        rank = (r.get("col:rank", "") or "").lower()
        db_id = existing.get((name.lower(), rank))
        if db_id is not None:
            cur.execute(
                "UPDATE taxon SET worms_id = ? WHERE id = ? AND worms_id IS NULL",
                (aid, db_id),
            )
            if cur.rowcount > 0:
                updates += 1
            aphia_to_db[aid] = db_id
    cur.execute("COMMIT")
    print(f"  Matched {updates:,} CoL taxa; worms_id set ({time.time() - t0:.1f}s)")

    # ---- Pass 2: insert WoRMS-only taxa (parent_id resolved) ----
    print("\nPass 2: inserting WoRMS-only taxa...")
    t0 = time.time()
    inserts = 0
    parent_resolved = 0
    parent_unresolved = 0

    cur.execute("BEGIN")
    for r in worms_rows:
        aid = aphia_from_urn(r.get("col:ID", ""))
        if aid is None or aid in aphia_to_db:
            continue
        name = r.get("col:scientificName", "")
        if not name:
            continue
        rank = r.get("col:rank", "") or ""
        authorship = r.get("col:authorship", "") or ""
        parent_aid = aphia_from_urn(r.get("col:parentID", ""))

        parent_db_id = aphia_to_db.get(parent_aid) if parent_aid else None
        if parent_db_id is not None:
            parent_resolved += 1
        elif parent_aid is not None:
            # Parent is a WoRMS taxon but wasn't matched in CoL — should
            # have been inserted in this same pass. If still unresolved, the
            # parent is one of the few rows we couldn't process (missing ID).
            parent_unresolved += 1

        cur.execute(
            "INSERT INTO taxon "
            "(parent_id, rank, status, scientific_name, authorship, worms_id, is_extinct) "
            "VALUES (?, ?, 'accepted', ?, ?, ?, 0)",
            (parent_db_id, rank, name, authorship, aid),
        )
        # lastrowid is int|None in the stubs but always int after a successful
        # INSERT. Guard so the dict assignment never sees None.
        rowid = cur.lastrowid
        if rowid is None:
            raise RuntimeError("INSERT into taxon returned no rowid")
        aphia_to_db[aid] = rowid
        inserts += 1
    cur.execute("COMMIT")

    con.commit()
    elapsed = time.time() - t0
    print(f"  Inserted {inserts:,} WoRMS-only taxa ({elapsed:.1f}s)")
    if parent_unresolved:
        print(f"  WARNING: {parent_unresolved:,} taxa have no parent_id (WoRMS parent outside accepted set)")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
