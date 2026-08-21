-- taxa.db schema v2 — adds coldp_id mapping and vernacular names.
-- For a fresh DB: apply schema.sql first, then this file.
-- For an existing v1 DB: the loader (load_coldp.py) handles migration
-- via PRAGMA-detected column checks BEFORE this script runs.

-- CoL's short ID index (column itself added by the loader's migration step).
-- Non-unique: homonyms in TextTree (different taxa with the same
-- scientific name) may share a coldp_id. The join from vernacular still
-- works because each VernacularName row's coldp_id points to a single
-- CoL concept, and the matching taxon is resolved via (coldp_id, name).
CREATE INDEX IF NOT EXISTS idx_taxon_coldp ON taxon(coldp_id) WHERE coldp_id IS NOT NULL;

-- Vernacular (common) names linked to a taxon.
CREATE TABLE IF NOT EXISTS vernacular (
    id              INTEGER PRIMARY KEY,
    taxon_id        INTEGER NOT NULL REFERENCES taxon(id) ON DELETE CASCADE,
    name            TEXT    NOT NULL,
    transliteration TEXT,
    language        TEXT,        -- ISO 639-3 (eng, spa, fra, deu, jpn...)
    country         TEXT,        -- ISO 3166-1 alpha-2
    life_stage      TEXT,
    sex             TEXT,
    reference_id    TEXT
);

CREATE INDEX IF NOT EXISTS idx_vern_taxon   ON vernacular(taxon_id);
CREATE INDEX IF NOT EXISTS idx_vern_lang    ON vernacular(language);
CREATE INDEX IF NOT EXISTS idx_vern_country ON vernacular(country);

-- FTS5 over the vernacular name so "tiger" finds Panthera tigris.
CREATE VIRTUAL TABLE IF NOT EXISTS vernacular_fts USING fts5(
    name,
    content='vernacular',
    content_rowid='id',
    tokenize="unicode61 remove_diacritics 1"
);

CREATE TRIGGER IF NOT EXISTS vernacular_ai AFTER INSERT ON vernacular BEGIN
    INSERT INTO vernacular_fts(rowid, name) VALUES (new.id, new.name);
END;

CREATE TRIGGER IF NOT EXISTS vernacular_ad AFTER DELETE ON vernacular BEGIN
    INSERT INTO vernacular_fts(vernacular_fts, rowid, name)
    VALUES ('delete', old.id, old.name);
END;

CREATE TRIGGER IF NOT EXISTS vernacular_au AFTER UPDATE ON vernacular BEGIN
    INSERT INTO vernacular_fts(vernacular_fts, rowid, name)
    VALUES ('delete', old.id, old.name);
    INSERT INTO vernacular_fts(rowid, name) VALUES (new.id, new.name);
END;