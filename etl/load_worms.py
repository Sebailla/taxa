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

# Biota is the WoRMS superdomain (worms_id = 1, parent_id IS NULL) — the
# root of the entire WoRMS tree, rendered by /api/domains as one of the
# top-level toggles (alongside the 4 CoL domains and Freshwater Fishes).
# We re-parent WoRMS-only orphans under Biota when their TSV parent isn't
# resolvable (see Pass 2); this guarantees every WoRMS-only row is reachable
# in the WoRMS view without polluting the root list (per /api/domains which
# filters by parent_id IS NULL AND worms_id = 1).
#
# The value 5413596 is the current DB row id; the runtime code derives it
# from `SELECT id FROM taxon WHERE worms_id=1` so a re-seed never produces
# a stale literal.
BIOTA_ID = 5413596

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

    # Migration: worms_id + worms_parent_id columns + indexes. Idempotent.
    # Kept for legacy DBs that predate schema versioning — new DBs get
    # these from schema.sql / the v5 migration runner. The Python-side
    # check is required because SQLite has no `ALTER TABLE ADD COLUMN
    # IF NOT EXISTS`, and legacy DBs (e.g. taxa.db.bak.* snapshots built
    # by external tooling) carry the columns with user_version=0. A real
    # ALTER in schema_v5.sql would fail on those; the Python check makes
    # the loader the single source of truth for the column existence.
    cols = {row[1] for row in cur.execute("PRAGMA table_info(taxon)")}
    if "worms_id" not in cols:
        cur.execute("ALTER TABLE taxon ADD COLUMN worms_id INTEGER")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_taxon_worms "
            "ON taxon(worms_id) WHERE worms_id IS NOT NULL"
        )
    if "worms_parent_id" not in cols:
        cur.execute("ALTER TABLE taxon ADD COLUMN worms_parent_id INTEGER")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_taxon_worms_parent "
            "ON taxon(worms_parent_id) WHERE worms_parent_id IS NOT NULL"
        )

    # Resolve Biota's row id at startup so the literal 5413596 never leaks
    # into INSERT/UPDATE statements. If the Biota row is missing the loader
    # can't safely re-parent WoRMS-only orphans under anything; fail fast.
    biota_row = cur.execute(
        "SELECT id FROM taxon WHERE worms_id = 1"
    ).fetchone()
    if biota_row is None:
        raise RuntimeError(
            "Biota row not found (worms_id=1). WoRMS enrichment requires "
            "Biota as the synthetic root for orphan re-parenting. Run CoL "
            "+ WoRMS loaders first so the Biota superdomain exists."
        )
    biota_id = biota_row[0]

    # Migration: apply pending schema migrations (idempotent via PRAGMA
    # user_version). For a freshly-built DB the runner is a no-op; for a
    # DB that's somehow behind (e.g. partial build) this catches up.
    #
    # Legacy-bak compatibility: taxa.db.bak.* snapshots were built by
    # external tooling that bypassed the migration runner. They carry
    # every column the migrations would add (coldp_id, worms_id,
    # worms_parent_id, freshwater_id, freshwater_parent_id) plus the
    # vernacular + distribution tables, but PRAGMA user_version is 0.
    # Running apply_pending_migrations on such a DB would fail on the
    # first ALTER with "duplicate column name" (SQLite has no ADD
    # COLUMN IF NOT EXISTS). Detect this state and bump the version
    # directly so the runner is a no-op.
    existing_cols = {
        row[1] for row in cur.execute("PRAGMA table_info(taxon)")
    }
    all_v5_columns = {
        "coldp_id", "worms_id", "worms_parent_id",
        "freshwater_id", "freshwater_parent_id",
    } <= existing_cols
    existing_tables = {
        row[0]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    current_version = con.execute("PRAGMA user_version").fetchone()[0]
    if (
        current_version < 5
        and all_v5_columns
        and "vernacular" in existing_tables
        and "distribution" in existing_tables
    ):
        print(
            f"Legacy bak detected (schema at v5 state, user_version={current_version}). "
            "Bumping to 5 to skip migrations."
        )
        con.execute("PRAGMA user_version = 5")

    schema_dir = Path(__file__).resolve().parent
    apply_pending_migrations(con, schema_dir)

    # Wipe any previous WoRMS enrichment so re-running is idempotent.
    # ONLY WoRMS-only rows (coldp_id IS NULL) — NOT CoL backbone rows
    # that Pass 1 stamped with worms_id. The original DELETE used
    # `WHERE worms_id IS NOT NULL` which silently wiped CoL rows whose
    # worms_id had been stamped by an earlier run, breaking the CoL
    # backbone on every re-run. The coldp_id IS NULL filter keeps CoL
    # rows in place so Pass 1 can UPDATE them in situ instead of
    # having to re-insert them as WoRMS-only orphans.
    #
    # WoRMS-only rows get fresh autoincrement ids on every run, but
    # they're referenced externally via worms_id (the aphiaid), not
    # via local db_id, so the id churn is invisible to callers.
    cur.execute(
        "SELECT COUNT(*) FROM taxon "
        "WHERE worms_id IS NOT NULL AND coldp_id IS NULL"
    )
    prev = cur.fetchone()[0]
    if prev:
        print(f"Clearing {prev:,} previously-enriched WoRMS-only rows...")
        cur.execute(
            "DELETE FROM taxon "
            "WHERE worms_id IS NOT NULL AND coldp_id IS NULL"
        )

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
    # Builds aphia_to_db for every matched CoL row; worms_parent_id is
    # resolved later in Pass 3 once every WoRMS row has been processed (a
    # CoL-matched row's parent might itself be a WoRMS-only row inserted
    # in Pass 2, which only lands in aphia_to_db at the end of Pass 2).
    print("\nPass 1: matching WoRMS to CoL by (name, rank)...")
    t0 = time.time()
    aphia_to_db: dict[int, int] = {}
    col_matched_aids: set[int] = set()
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
            col_matched_aids.add(aid)
    cur.execute("COMMIT")
    print(f"  Matched {updates:,} CoL taxa; worms_id set ({time.time() - t0:.1f}s)")

    # ---- Pass 2: insert WoRMS-only taxa (parent_id + worms_parent_id) ----
    # Two parent columns so the CoL view and the WoRMS view can walk
    # different hierarchies. parent_id keeps its current semantic (NULL
    # for WoRMS-only rows so they stay out of the CoL view); worms_parent_id
    # resolves the row's position in the WoRMS tree, falling back to Biota
    # when the parent is given in the TSV but hasn't been processed yet
    # (TSV ordering issue: parent isn't a CoL row and lands later in Pass 2).
    # Pass 3 fixes those fallback rows once every aphiaid has been seen.
    print("\nPass 2: inserting WoRMS-only taxa...")
    t0 = time.time()
    inserts = 0
    parent_resolved = 0
    parent_fallback_biota = 0

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

        # Resolve both parent columns. parent_id stays NULL for orphans
        # and for unresolved TSV parents (kept out of the CoL view).
        # worms_parent_id uses the Biota fallback so the row is reachable
        # in the WoRMS view per /api/domains' contract.
        parent_db_id = aphia_to_db.get(parent_aid) if parent_aid else None
        worms_parent_db_id: int | None
        if parent_aid is None:
            worms_parent_db_id = None  # genuine orphan — no anchor
        elif parent_db_id is not None:
            worms_parent_db_id = parent_db_id
            parent_resolved += 1
        else:
            # Parent_aid given but not yet in aphia_to_db — should land
            # later in Pass 2 (TSV order). Pass 3 will re-resolve.
            worms_parent_db_id = biota_id
            parent_fallback_biota += 1

        cur.execute(
            "INSERT INTO taxon "
            "(parent_id, rank, status, scientific_name, authorship, "
            "worms_id, worms_parent_id, is_extinct) "
            "VALUES (?, ?, 'accepted', ?, ?, ?, ?, 0)",
            (parent_db_id, rank, name, authorship, aid, worms_parent_db_id),
        )
        # lastrowid is int|None in the stubs but always int after a successful
        # INSERT. Guard so the dict assignment never sees None.
        rowid = cur.lastrowid
        if rowid is None:
            raise RuntimeError("INSERT into taxon returned no rowid")
        aphia_to_db[aid] = rowid
        inserts += 1
    cur.execute("COMMIT")

    elapsed = time.time() - t0
    print(f"  Inserted {inserts:,} WoRMS-only taxa ({elapsed:.1f}s)")
    if parent_fallback_biota:
        print(
            f"  {parent_fallback_biota:,} taxa re-parented under Biota "
            f"(TSV parent not yet seen); Pass 3 will re-resolve."
        )

    # ---- Pass 3: backfill worms_parent_id for CoL-matched rows and fix
    # WoRMS-only rows that got the Biota fallback in Pass 2 but whose
    # parent is now in aphia_to_db (because Pass 2 inserted it later). ----
    print("\nPass 3: backfilling worms_parent_id...")
    t0 = time.time()
    col_updates = 0
    fallback_fixes = 0

    cur.execute("BEGIN")
    for r in worms_rows:
        aid = aphia_from_urn(r.get("col:ID", ""))
        if aid is None or aid not in aphia_to_db:
            continue
        parent_aid = aphia_from_urn(r.get("col:parentID", ""))
        resolved_parent = aphia_to_db.get(parent_aid) if parent_aid else None
        local_rowid = aphia_to_db[aid]

        if aid in col_matched_aids:
            # CoL row — set worms_parent_id on the matched taxon. The CoL
            # row was NOT deleted by the pre-Pass wipe (the fix limits
            # the DELETE to WoRMS-only rows via `coldp_id IS NULL`), so
            # this UPDATE re-stamps worms_parent_id in place. Pass 1
            # already set worms_id on the same row in this same run.
            if parent_aid is not None and resolved_parent is None:
                # CoL row's WoRMS parent isn't in our aphia_to_db — the
                # parent is outside the WoRMS accepted set or wasn't in
                # the TSV. Leave worms_parent_id NULL (orphan CoL row).
                continue
            cur.execute(
                "UPDATE taxon SET worms_parent_id = ? WHERE id = ?",
                (resolved_parent, local_rowid),
            )
            if cur.rowcount > 0:
                col_updates += 1
        else:
            # WoRMS-only row. If Pass 2 gave it Biota as fallback but the
            # real parent is now in aphia_to_db, fix it. Genuine orphans
            # (parent_aid None) are left alone.
            cur.execute(
                "UPDATE taxon SET worms_parent_id = ? "
                "WHERE id = ? AND worms_parent_id = ? AND ? IS NOT NULL",
                (resolved_parent, local_rowid, biota_id, resolved_parent),
            )
            if cur.rowcount > 0:
                fallback_fixes += 1
    cur.execute("COMMIT")
    elapsed = time.time() - t0
    print(
        f"  Backfilled {col_updates:,} CoL taxa + "
        f"{fallback_fixes:,} WoRMS-only fallback rows ({elapsed:.1f}s)"
    )

    con.commit()

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
