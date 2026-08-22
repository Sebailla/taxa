-- taxa.db schema v4 — adds the freshwater source columns.
-- Idempotent: the loader applies this file via executescript, gated by a
-- PRAGMA table_info check (the ALTER TABLE statements are not idempotent on
-- their own — running them twice would fail with "duplicate column name").
-- Mirrors the load_worms.py / load_coldp.py migration pattern.

-- The FK constraint freshwater_parent_id -> taxon(id) is intentionally
-- OMITTED: SQLite ALTER TABLE does not support adding REFERENCES. The
-- loader and API enforce referential integrity instead. This matches the
-- worms_parent_id convention (also unenforced).

ALTER TABLE taxon ADD COLUMN freshwater_id        INTEGER;
ALTER TABLE taxon ADD COLUMN freshwater_parent_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_taxon_freshwater
    ON taxon(freshwater_id) WHERE freshwater_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_taxon_fw_parent
    ON taxon(freshwater_parent_id) WHERE freshwater_parent_id IS NOT NULL;
