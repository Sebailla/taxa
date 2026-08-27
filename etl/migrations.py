"""
etl/migrations.py — single source of truth for taxa.db schema versions.

Uses SQLite's PRAGMA user_version (a 32-bit integer purpose-built for
schema-version tracking) to record what's been applied. Each migration
is a numbered SQL file (schema_vN.sql) applied in order; after a
migration succeeds, PRAGMA user_version is bumped and committed.

Fresh DBs start at user_version=0 (SQLite's default). The base schema
(etl/schema.sql) is the v1 state and is applied separately by
parse_textree.py for fresh builds. This module covers v2+.

This module is the single source of truth for both:
  - The current expected version (CURRENT_SCHEMA_VERSION constant)
  - The list of migrations and their SQL files (MIGRATIONS list)

Adding a v5 migration:
  1. Create etl/schema_v5.sql with the additive changes.
  2. Append (5, "schema_v5.sql") to MIGRATIONS below.
  3. Bump CURRENT_SCHEMA_VERSION to 5.
  4. The next time any loader runs, v5 applies automatically.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# The schema version this codebase expects the DB to be at.
# Bump in lockstep with MIGRATIONS additions.
CURRENT_SCHEMA_VERSION = 5

# Ordered list of additive migrations, applied top-down. Each entry is
# (version, filename) where filename is a SQL file relative to the
# schema_dir passed to apply_pending_migrations.
MIGRATIONS: list[tuple[int, str]] = [
    (2, "schema_v2.sql"),
    (3, "schema_v3.sql"),
    (4, "schema_v4.sql"),
    (5, "schema_v5.sql"),
]


def get_applied_version(conn: sqlite3.Connection) -> int:
    """Return the schema version recorded in PRAGMA user_version.

    Returns 0 for fresh DBs (SQLite's default). Reflects only what the
    runner has explicitly recorded — does not introspect the actual
    schema (e.g. which columns exist on `taxon`).
    """
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _set_user_version(conn: sqlite3.Connection, version: int) -> None:
    """Set PRAGMA user_version. SQLite PRAGMA statements don't accept
    bound parameters (they're parsed before parameter binding), so we
    format the int directly. The isinstance guard above ensures the
    f-string is only ever reached with a non-negative int — `version`
    comes from the hardcoded MIGRATIONS tuple, never user input.
    """
    if not isinstance(version, int) or isinstance(version, bool) or version < 0:
        raise ValueError(f"PRAGMA user_version must be a non-negative int, got {version!r}")
    # nosemgrep
    # Safe: PRAGMA doesn't support bound params; `version` is validated as int above (line 65);
    # rule fires on the f-string pattern regardless of stdlib sqlite3 vs SQLAlchemy.
    conn.execute(f"PRAGMA user_version = {version}")


def apply_pending_migrations(
    conn: sqlite3.Connection,
    schema_dir: Path,
) -> list[int]:
    """Apply every migration whose version is greater than the current
    PRAGMA user_version, in order. Each migration is one executescript
    call plus a PRAGMA user_version bump at the end.

    We do NOT wrap each migration in an explicit BEGIN/COMMIT transaction
    because Python's sqlite3.executescript() implicitly commits any open
    transaction before running the script (see CPython sqlite3 module
    docs). Per-statement atomicity is enough for our case: each ALTER
    TABLE / CREATE INDEX is atomic in SQLite. If a migration fails
    partway, the previously-run statements are committed; recovery is
    "rebuild from schema.sql" (cheap for a research tool, ~10 min for
    the full pipeline).

    On failure (file missing, SQL error), the DB stays at the previous
    PRAGMA user_version (because the bump at the end never ran) and a
    RuntimeError is raised. The caller can retry after fixing the
    problem; previously-successful migrations will be skipped because
    their version is already recorded.

    Returns the list of versions applied in this call (empty if the
    DB was already at CURRENT_SCHEMA_VERSION).

    Idempotency note: SQL files are expected to contain idempotent
    CREATE statements (CREATE TABLE/INDEX IF NOT EXISTS) plus additive
    ALTER TABLE. The PRAGMA bump is the gate — once a migration's
    version is recorded, the SQL file will not be re-executed, so the
    non-idempotent ALTER statements inside it will not run twice.
    """
    current = get_applied_version(conn)
    applied: list[int] = []

    for version, filename in MIGRATIONS:
        if version <= current:
            continue
        sql_path = schema_dir / filename
        try:
            sql = sql_path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Migration v{version} requires {sql_path} but it does not exist"
            ) from e

        try:
            conn.executescript(sql)
            _set_user_version(conn, version)
            applied.append(version)
        except sqlite3.Error as e:
            raise RuntimeError(
                f"Migration v{version} ({filename}) failed: {e}. "
                f"DB stays at v{current}; fix the SQL and re-run."
            ) from e

    return applied
