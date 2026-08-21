"""
Parse the Catalogue of Life TextTree into a local SQLite database.

TextTree format (per line):
    <indent><name> <authorship> [<rank>]

- Indentation: 2 spaces per depth level.
- Leading '=' marks a synonym.
- Rank is the last bracketed token: [domain|kingdom|phylum|class|order|family|genus|species|subspecies]

Examples:
    Archaea Woese et al., 2024 [domain]
      =Halobacteriota Chuvochina et al., 2024 [phylum]
        Homo sapiens Linnaeus, 1758 [species]

Usage:
    python parse_textree.py <path/to/dataset-*.txtree> <path/to/taxa.db>
"""

from __future__ import annotations

import re
import sqlite3
import sys
import time
from pathlib import Path

LINE_RE = re.compile(
    r"^(?P<indent>\s*)(?P<syn>=)?"
    r"(?P<body>.+?) \[(?P<rank>\w+)\]\s*$"
)

BINOMIAL_RANKS = {"species", "subspecies"}

# How often to print progress (rows).
PROGRESS_INTERVAL = 500_000


def parse_line(raw: str):
    """Return (depth, status, name, authorship, rank) or None on malformed line."""
    m = LINE_RE.match(raw)
    if not m:
        return None
    depth = len(m.group("indent")) // 2
    is_syn = m.group("syn") is not None
    body = m.group("body").strip()
    rank = m.group("rank").lower()

    if rank in BINOMIAL_RANKS:
        tokens = body.split(maxsplit=2)
        if len(tokens) >= 3:
            name, authorship = tokens[0] + " " + tokens[1], tokens[2]
        elif len(tokens) == 2:
            name, authorship = tokens[0], tokens[1]
        else:
            name, authorship = body, ""
    else:
        tokens = body.split(maxsplit=1)
        name = tokens[0]
        authorship = tokens[1] if len(tokens) == 2 else ""

    return depth, ("synonym" if is_syn else "accepted"), name, authorship, rank


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    schema = Path(__file__).parent / "schema.sql"

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()

    print(f"Parsing {src} -> {dst}")
    t0 = time.perf_counter()

    # ------------------------------------------------------------------
    # Phase 1: walk the file.
    # We build (in memory):
    #   depth_stack: list of (depth, idx) of current ancestors. Top is the
    #                immediate parent. Used to resolve parent_idx.
    #   path_stack:  list of name strings aligned with depth_stack. Top is
    #                the parent path. Used to materialize the current path.
    #
    #   rows[]:    (parent_idx, rank, status, name, authorship, path, descendant_species_count)
    #              path and descendant_species_count are derived here, NOT
    #              later via expensive recursive CTEs.
    #
    # Memory: ~150 bytes per row. For 5.4M rows ≈ 800 MB peak.
    # ------------------------------------------------------------------
    depth_stack: list[tuple[int, int]] = []   # (depth, row_idx)
    path_stack: list[str] = []                # names aligned with depth_stack
    rows: list[tuple[int, str, str, str, str | None, str, int]] = []
    n_synonyms = 0
    n_malformed = 0
    n_species_leaves = 0

    with src.open("r", encoding="utf-8") as fh:
        for raw in fh:
            parsed = parse_line(raw)
            if parsed is None:
                n_malformed += 1
                continue
            depth, status, name, authorship, rank = parsed
            if status == "synonym":
                n_synonyms += 1

            # Pop stacks to current depth.
            while depth_stack and depth_stack[-1][0] >= depth:
                depth_stack.pop()
                path_stack.pop()

            parent_idx = depth_stack[-1][1] if depth_stack else -1
            current_path = "/" + "/".join(path_stack + [name]) if path_stack or True \
                else "/" + name
            # The above always produces "/a/b/c" — even for root.

            idx = len(rows)
            # Initial descendant species count: 1 if this row is itself an
            # accepted species, else 0. We'll add the children's contributions
            # later via the species-pass walk.
            initial_count = 1 if (rank == "species" and status == "accepted") else 0
            if initial_count:
                n_species_leaves += 1

            rows.append((parent_idx, rank, status, name, authorship,
                         current_path, initial_count))

            depth_stack.append((depth, idx))
            path_stack.append(name)

            if (idx + 1) % PROGRESS_INTERVAL == 0:
                elapsed = time.perf_counter() - t0
                print(f"  parsed {idx+1:>10,} rows  "
                      f"({(idx+1)/elapsed:,.0f}/s)  "
                      f"[{n_synonyms:,} synonyms]")

    parse_elapsed = time.perf_counter() - t0
    print(f"\nParsed {len(rows):,} rows in {parse_elapsed:.1f}s "
          f"({n_synonyms:,} synonyms, {n_malformed:,} malformed, "
          f"{n_species_leaves:,} accepted species leaves)")

    # ------------------------------------------------------------------
    # Phase 2: roll up descendant_species_count.
    # For each accepted species, walk up the parent chain and add 1 to each
    # ancestor's counter. This is O(N * depth) — for 5.4M rows with avg
    # depth ~12, that's ~65M ops in Python. Takes ~30s.
    # ------------------------------------------------------------------
    print("Rolling up species counts...")
    t1 = time.perf_counter()
    counts = [r[6] for r in rows]  # mutable copy
    parents = [r[0] for r in rows]
    # For each row that is an accepted species (counts[i] == 1), walk up.
    for i in range(len(rows)):
        if counts[i] != 1:
            continue
        p = parents[i]
        while p >= 0:
            counts[p] += 1
            p = parents[p]
    # Replace initial counts with rolled-up counts.
    rows = [(*r[:6], counts[i]) for i, r in enumerate(rows)]
    del counts
    rollup_elapsed = time.perf_counter() - t1
    print(f"  done in {rollup_elapsed:.1f}s")

    # ------------------------------------------------------------------
    # Phase 3: bulk insert into SQLite.
    # We do TWO bulk operations:
    #   (a) INSERT all rows with parent_id = NULL (executemany).
    #   (b) UPDATE parent_id from the in-memory array.
    # This avoids the O(N²) UPDATE-with-subquery pattern.
    # ------------------------------------------------------------------
    print("Inserting into SQLite...")
    t2 = time.perf_counter()

    conn = sqlite3.connect(dst, isolation_level=None)
    conn.executescript(schema.read_text())
    cur = conn.cursor()

    ids: list[int] = [0] * len(rows)

    with conn:
        cur.execute("BEGIN")
        cur.executemany(
            "INSERT INTO taxon (parent_id, rank, status, scientific_name, "
            "authorship, path, species_count) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(None, r[1], r[2], r[3], r[4], r[5], r[6]) for r in rows],
        )
        # Without AUTOINCREMENT and with no concurrent writes, rowids are
        # 1..N. Read them back in id order.
        cur.execute("SELECT id FROM taxon ORDER BY id")
        new_ids = [row[0] for row in cur.fetchall()]
        assert len(new_ids) == len(rows)
        for i, nid in enumerate(new_ids):
            ids[i] = nid
        cur.execute("COMMIT")

    print(f"  inserted {len(ids):,} rows, linking parents...")
    with conn:
        cur.execute("BEGIN")
        cur.executemany(
            "UPDATE taxon SET parent_id = ? WHERE id = ?",
            [(ids[r[0]] if r[0] >= 0 else None, ids[i])
             for i, r in enumerate(rows)],
        )
        cur.execute("COMMIT")

    insert_elapsed = time.perf_counter() - t2
    print(f"  done in {insert_elapsed:.1f}s")

    # ------------------------------------------------------------------
    # Phase 4: VACUUM + ANALYZE for query performance.
    # ------------------------------------------------------------------
    cur.execute("VACUUM")
    cur.execute("ANALYZE")

    # Stats.
    cur.execute("SELECT COUNT(*) FROM taxon")
    total = cur.fetchone()[0]
    cur.execute("SELECT rank, COUNT(*) FROM taxon GROUP BY rank ORDER BY 2 DESC")
    print(f"\nTotal taxa: {total:,}")
    print("By rank:")
    for rank, count in cur.fetchall():
        print(f"  {rank:15} {count:>12,}")

    total_elapsed = time.perf_counter() - t0
    print(f"\nDone in {total_elapsed:.1f}s")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())