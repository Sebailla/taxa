"""G5 legacy launcher: ASGI app that mounts the G3 legacy fixture in
front of `api.server.app` for chain PR 2's controlled FastAPI capture.

Chain PR 1 of the G5 hydration-readiness work. The launcher:

  * fail-closes at import time when the fixture DB or web dir is missing
    or empty (RuntimeError before any routes are registered);
  * rewires ONLY `api.server.DB_PATH` to the fixture SQLite so every
    DB-backed endpoint (`/api/health`, ...) hits the fixture — and
    leaves `api.server.WEB_DIR` untouched so the regression guard can
    verify it was not mutated;
  * inserts one `Mount("/", StaticFiles(...))` into
    `api.server.app.router.routes` JUST BEFORE the production root
    mount (the last route, registered at the bottom of `api/server.py`).
    Starlette matches routes in registration order, so this placement
    preserves every FastAPI `/api/*` route (they precede the fixture
    mount in the list) while still letting the fixture win for any
    static path that exists in both fixture and production web/.
    Inserting at index 0 would intercept `/api/health` (the catch-all
    `Mount("/")` wins before any APIRoute), which is why we insert
    just before the production mount instead;
  * exposes `app` as `api.server.app` (the launcher IS the production
    app with the fixture prepended + DB rewired).

Run with uvicorn:

    uvicorn tools.g3-legacy-fixture.scripts.g5_legacy_asgi:app
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `api.server` importable when the launcher is launched directly.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.routing import Mount  # noqa: E402

import api.server as _server  # noqa: E402

FIXTURE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DB = FIXTURE_ROOT / "taxa.db"
FIXTURE_WEB = FIXTURE_ROOT / "web"


def _require_nonempty_file(path: Path, label: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(
            f"G5 launcher fail-closed: {label} missing or empty: {path}"
        )


def _require_nonempty_dir(path: Path, label: str) -> None:
    if not path.is_dir() or not any(path.iterdir()):
        raise RuntimeError(
            f"G5 launcher fail-closed: {label} missing or empty: {path}"
        )


# Fail-closed before any route work — RuntimeError here aborts import so
# downstream code (uvicorn, tests) never sees a half-wired app.
_require_nonempty_file(FIXTURE_DB, "fixture DB")
_require_nonempty_dir(FIXTURE_WEB, "fixture web dir")

# Rewire ONLY DB_PATH; never touch WEB_DIR (test block guards this).
_server.DB_PATH = FIXTURE_DB

# Insert the fixture static mount JUST BEFORE the production root mount
# (the last route in api.server.app — added at the bottom of
# api/server.py). This order preserves the FastAPI `/api/*` routes
# (they come first in the list) and lets the fixture win for static
# paths that exist in BOTH the fixture and production web/.
# Inserting at index 0 would intercept `/api/health` (the catch-all
# Mount at "/" wins before any APIRoute), so we insert just before
# the production mount instead.
fixture_static = StaticFiles(directory=str(FIXTURE_WEB), html=True)
_routes = _server.app.router.routes
# The production mount is the last route; insert just before it.
_production_mount_idx = len(_routes) - 1
_routes.insert(
    _production_mount_idx,
    Mount("/", app=fixture_static, name="g5-legacy-fixture-static"),
)

# Expose the canonical ASGI app — same object as api.server.app, with
# the fixture mounted + DB rewired.
app = _server.app

__all__ = ["app", "FIXTURE_DB", "FIXTURE_WEB",
           "_require_nonempty_file", "_require_nonempty_dir"]
