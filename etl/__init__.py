"""etl: schema migrations, ETL loaders, and tests for taxa.db.

Public submodules:
    migrations — single source of truth for taxa.db schema versions
                 (CURRENT_SCHEMA_VERSION + apply_pending_migrations runner).
                 Uses PRAGMA user_version (SQLite's purpose-built metadata).
    load_freshwater, load_coldp, load_worms, load_distribution — per-source
                 loaders. Each calls `apply_pending_migrations` at the start
                 so the DB is at CURRENT_SCHEMA_VERSION before data loads.

The empty `py.typed` marker in this directory (PEP 561) tells type checkers
that this package is fully typed and should be checked normally. Without
it, pyright treats the package as untyped and may fail to resolve
cross-module imports between siblings under this package (e.g.
`from etl.migrations import ...`).
"""
