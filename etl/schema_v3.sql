-- taxa.db schema v3 — adds the distribution table.
-- Idempotent: the loader creates the table if missing, and the API
-- endpoints all guard against the table being absent.

-- Geographic range for a taxon, sourced from ColDP Distribution.tsv.
-- The `area` column is already human-readable text (e.g. "USA (Alabama,
-- Colorado, ...)" or "South America"), so no vocabulary join is needed.
CREATE TABLE IF NOT EXISTS distribution (
    id                       INTEGER PRIMARY KEY,
    taxon_id                 INTEGER NOT NULL REFERENCES taxon(id) ON DELETE CASCADE,
    area                     TEXT    NOT NULL,
    gazetteer                TEXT,        -- "text", "ISO", "TDWG", etc.
    establishment_means      TEXT,        -- "native", "introduced", "uncertain"
    degree_of_establishment  TEXT,        -- "native", "invasive", etc.
    reference_id             TEXT
);

CREATE INDEX IF NOT EXISTS idx_dist_taxon ON distribution(taxon_id);
CREATE INDEX IF NOT EXISTS idx_dist_means ON distribution(establishment_means);