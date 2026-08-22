#!/usr/bin/env python3
"""
Two-pass transform: convert the Freshwater Fishes Google Sheet CSV
(hierarchical: family, subfamily, genus, species, scientific_name,
author, year) into the flat format expected by
etl/load_freshwater.py
(freshwater_id, freshwater_parent_id, rank, scientific_name, authorship).

Pass 1: scan CSV, collect all distinct (rank, identifying-tuple) entries.
Pass 2: emit rows in topological order: families, then subfamilies,
        then genera, then species. Assign freshwater_id incrementally
        starting at 2 (1 is reserved for the synthetic root inserted by
        the loader).

Why this exists: the spreadsheet has no explicit parent IDs and no rank
column. Rank is inferred from which taxonomic columns are populated, and
the parent chain is reconstructed by tracking previously-seen tuples.

Output goes to /tmp/freshwater.flat.csv which is then passed to the
loader.
"""
from __future__ import annotations

import csv
import sys
from collections import OrderedDict
from pathlib import Path

SRC = Path("/Users/sebailla/Developer/taxa/data/raw/freshwater.csv")
DST = Path("/tmp/freshwater.flat.csv")


def main() -> int:
    if not SRC.exists():
        print(f"Source not found: {SRC}", file=sys.stderr)
        return 1

    # Pass 1: collect distinct entries.
    families: "OrderedDict[str, None]" = OrderedDict()
    subfamilies: "OrderedDict[tuple[str, str], None]" = OrderedDict()
    genera: "OrderedDict[tuple[str, str, str], None]" = OrderedDict()
    species: list[tuple[str, str, str, str, str]] = []  # (fam, sub, gen, sp, author)

    with SRC.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        for line_no, row in enumerate(reader, start=1):
            if not row or all((c or "").strip() == "" for c in row):
                continue
            if line_no == 1:
                continue
            if len(row) < 7:
                continue

            family = row[0].strip()
            subfamily = row[1].strip()
            genus = row[2].strip()
            sp = row[3].strip()
            author = row[5].strip()

            if family:
                families.setdefault(family, None)
            if family and subfamily:
                subfamilies.setdefault((family, subfamily), None)
            if family and genus:
                genera.setdefault((family, subfamily, genus), None)
            if family and genus and sp:
                species.append((family, subfamily, genus, sp, author))

    # Pass 2: emit rows in topological order.
    # Map tuple -> freshwater_id, assigned in order.
    family_id: dict[str, int] = {}
    subfamily_id: dict[tuple[str, str], int] = {}
    genus_id: dict[tuple[str, str, str], int] = {}

    out_rows: list[tuple[int, int, str, str, str]] = []
    next_fw_id = 2  # 1 reserved for synthetic root inserted by loader

    # 1. Family rows (parent = root, freshwater_id=1).
    for fam in families:
        fw_id = next_fw_id
        next_fw_id += 1
        family_id[fam] = fw_id
        out_rows.append((fw_id, 1, "family", fam, ""))

    # 2. Subfamily rows (parent = family row).
    for (fam, sub) in subfamilies:
        if fam not in family_id:
            # Family wasn't seen — skip this subfamily (orphan).
            continue
        fw_id = next_fw_id
        next_fw_id += 1
        subfamily_id[(fam, sub)] = fw_id
        out_rows.append((fw_id, family_id[fam], "subfamily", sub, ""))

    # 3. Genus rows (parent = subfamily if present, else family).
    for (fam, sub, gen) in genera:
        if fam not in family_id:
            continue
        if sub and (fam, sub) in subfamily_id:
            parent_id = subfamily_id[(fam, sub)]
        else:
            parent_id = family_id[fam]
        fw_id = next_fw_id
        next_fw_id += 1
        genus_id[(fam, sub, gen)] = fw_id
        out_rows.append((fw_id, parent_id, "genus", gen, ""))

    # 4. Species rows (parent = genus row).
    for (fam, sub, gen, sp, author) in species:
        if (fam, sub, gen) not in genus_id:
            continue
        fw_id = next_fw_id
        next_fw_id += 1
        # Species scientific_name is "Genus species".
        sci = f"{gen} {sp}"
        out_rows.append((fw_id, genus_id[(fam, sub, gen)], "species", sci, author))

    # Write output.
    DST.parent.mkdir(parents=True, exist_ok=True)
    with DST.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(("freshwater_id", "freshwater_parent_id", "rank",
                         "scientific_name", "authorship"))
        for row in out_rows:
            writer.writerow(row)

    # Summary.
    n_family = len(family_id)
    n_subfamily = len(subfamily_id)
    n_genus = len(genus_id)
    n_species = len(species)
    print(f"Transformed: {len(out_rows)} rows "
          f"({n_family} families, {n_subfamily} subfamilies, "
          f"{n_genus} genera, {n_species} species)")
    print(f"Output: {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())