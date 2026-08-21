-- taxa.db schema
-- Stores the Catalogue of Life taxonomy as a flat, indexed tree.
-- All paths are materialized post-load so we don't pay a recursive CTE
-- on every query.

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456; -- 256 MB
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS taxon;
DROP TABLE IF EXISTS taxon_fts;

CREATE TABLE taxon (
    id              INTEGER PRIMARY KEY,
    parent_id       INTEGER REFERENCES taxon(id) ON DELETE CASCADE,
    rank            TEXT    NOT NULL,
    status          TEXT    NOT NULL CHECK (status IN ('accepted', 'synonym')),
    scientific_name TEXT    NOT NULL,
    authorship      TEXT,
    path            TEXT,              -- materialized post-load: '/Eukaryota/Animalia/...'
    species_count   INTEGER,             -- descendant leaf-species count (post-rollup)
    accepted_id     INTEGER REFERENCES taxon(id),  -- for synonyms: points to accepted name
    is_extinct      INTEGER NOT NULL DEFAULT 0  -- TextTree has no flag; filled later from ColDP
);

CREATE INDEX idx_taxon_parent      ON taxon(parent_id);
CREATE INDEX idx_taxon_rank        ON taxon(rank);
CREATE INDEX idx_taxon_status      ON taxon(status);
CREATE INDEX idx_taxon_accepted    ON taxon(accepted_id);

-- Full-text search on name + authorship.
-- Porter stemming; unicode61 handles accented names (Oren & Göker, Stetter, etc.).
CREATE VIRTUAL TABLE taxon_fts USING fts5(
    scientific_name,
    authorship,
    content='taxon',
    content_rowid='id',
    tokenize="unicode61 remove_diacritics 1"
);

-- Keep FTS in sync via triggers.
CREATE TRIGGER taxon_ai AFTER INSERT ON taxon BEGIN
    INSERT INTO taxon_fts(rowid, scientific_name, authorship)
    VALUES (new.id, new.scientific_name, COALESCE(new.authorship, ''));
END;

CREATE TRIGGER taxon_ad AFTER DELETE ON taxon BEGIN
    INSERT INTO taxon_fts(taxon_fts, rowid, scientific_name, authorship)
    VALUES ('delete', old.id, old.scientific_name, COALESCE(old.authorship, ''));
END;

CREATE TRIGGER taxon_au AFTER UPDATE ON taxon BEGIN
    INSERT INTO taxon_fts(taxon_fts, rowid, scientific_name, authorship)
    VALUES ('delete', old.id, old.scientific_name, COALESCE(old.authorship, ''));
    INSERT INTO taxon_fts(rowid, scientific_name, authorship)
    VALUES (new.id, new.scientific_name, COALESCE(new.authorship, ''));
END;