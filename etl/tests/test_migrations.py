"""
Tests for etl/migrations.py — the schema-version runner.

Strategy: copy the real schema_vN.sql files into a tmp dir so the runner
sees a self-contained schema directory. The runner doesn't know about the
real etl/ layout; it accepts any directory of schema files. Tests that
need "this is the current production schema" copy the real files;
tests that need "this schema fails" write their own broken file.

The runner uses PRAGMA user_version for tracking (SQLite's purpose-built
metadata for exactly this). Fresh DBs start at 0.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from etl.migrations import (
    CURRENT_SCHEMA_VERSION,
    MIGRATIONS,
    apply_pending_migrations,
    get_applied_version,
)


REAL_SCHEMA_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def schema_dir(tmp_path):
    """Copy the real etl/schema_v*.sql files into tmp_path so the runner
    operates on an isolated schema directory. Tests that need to inject
    a broken schema file can overwrite individual files in tmp_path."""
    for filename in ("schema_v2.sql", "schema_v3.sql", "schema_v4.sql"):
        shutil.copy(REAL_SCHEMA_DIR / filename, tmp_path / filename)
    return tmp_path


@pytest.fixture
def db():
    """In-memory SQLite with the minimal taxon table the v2-v4 SQL files
    need (coldp_id for v2's CREATE INDEX, no freshwater columns so v4's
    ALTER TABLE ADD COLUMN actually has work to do).

    The runner is what we're testing — the SQL files themselves are
    integration-tested by the per-loader suites. This fixture exists
    only so the runner doesn't crash on schema-file prerequisites.
    """
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE taxon (
            id          INTEGER PRIMARY KEY,
            parent_id   INTEGER,
            rank        TEXT    NOT NULL,
            status      TEXT    NOT NULL,
            scientific_name TEXT NOT NULL,
            authorship  TEXT,
            path        TEXT,
            species_count INTEGER,
            accepted_id INTEGER,
            is_extinct  INTEGER NOT NULL DEFAULT 0,
            coldp_id    TEXT,
            worms_id    INTEGER
            -- no freshwater_id / freshwater_parent_id — v4 adds them
        );
    """)
    yield conn
    conn.close()


def test_get_applied_version_default():
    """Fresh in-memory DB returns 0 (PRAGMA user_version default)."""
    conn = sqlite3.connect(":memory:")
    assert get_applied_version(conn) == 0
    conn.close()


def test_apply_pending_from_fresh(db, schema_dir):
    """Fresh DB (user_version=0) gets every migration applied in order."""
    applied = apply_pending_migrations(db, schema_dir)
    assert applied == [2, 3, 4]
    assert get_applied_version(db) == 4
    # v4's CREATE INDEX (the idempotent part after the ALTER TABLEs) should
    # have landed — proof the runner executed the SQL, not just bumped the
    # version. The ALTER TABLEs are confirmed by the version bump itself.
    idx_count = db.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name='idx_taxon_freshwater'"
    ).fetchone()[0]
    assert idx_count == 1, "v4's CREATE INDEX should have landed"


def test_apply_pending_from_v2(db, schema_dir):
    """DB at v2 gets only v3 and v4 applied — v2 is skipped."""
    db.execute("PRAGMA user_version = 2")
    applied = apply_pending_migrations(db, schema_dir)
    assert applied == [3, 4]
    assert get_applied_version(db) == 4


def test_apply_pending_already_current(db, schema_dir):
    """DB at CURRENT_SCHEMA_VERSION applies nothing and stays put."""
    db.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")
    applied = apply_pending_migrations(db, schema_dir)
    assert applied == []
    assert get_applied_version(db) == CURRENT_SCHEMA_VERSION


def test_apply_pending_idempotent(db, schema_dir):
    """Running twice in a row produces no extra work the second time."""
    first = apply_pending_migrations(db, schema_dir)
    assert first == [2, 3, 4]
    second = apply_pending_migrations(db, schema_dir)
    assert second == []
    assert get_applied_version(db) == CURRENT_SCHEMA_VERSION


def test_apply_pending_missing_file_raises(db, schema_dir):
    """If a migration's SQL file is absent, the runner raises and the
    version stays at the previous one (no partial bump)."""
    (schema_dir / "schema_v3.sql").unlink()
    with pytest.raises((FileNotFoundError, RuntimeError)):
        apply_pending_migrations(db, schema_dir)
    # v2 should have been applied successfully; v3 raises before it runs.
    assert get_applied_version(db) == 2


def test_migrations_list_is_ordered_and_complete():
    """MIGRATIONS is the single source of truth for what versions exist.
    Sanity-check it: starts at 2 (v1 is the base schema.sql), ends at
    CURRENT_SCHEMA_VERSION, and has no gaps."""
    versions = [v for v, _ in MIGRATIONS]
    assert versions[0] == 2
    assert versions[-1] == CURRENT_SCHEMA_VERSION
    # No gaps: consecutive ints
    assert versions == list(range(versions[0], versions[-1] + 1))
    # Every entry points to a file that actually exists on disk
    for _, filename in MIGRATIONS:
        assert (REAL_SCHEMA_DIR / filename).exists(), (
            f"MIGRATIONS references {filename} but it doesn't exist"
        )
