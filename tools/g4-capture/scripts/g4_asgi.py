"""G4-only ASGI launcher for controlled legacy capture.

It rewires api.server's module-local data paths without changing production
code, and serves the deterministic G4 corpus `index.html` at `/index.html`
so the capture producer never reaches the mutable production `web/`
directory.

The corpus route is inserted BEFORE api.server's StaticFiles mount at the
root (declared at the bottom of api/server.py), so the static handler does
not swallow `/index.html` and return whatever happens to live in web/.

Slice A — environment-selected static root (`G4_STATIC_ROOT`)
--------------------------------------------------------------
When set to an absolute existing directory under the repo root, server.WEB_DIR
is rewired to that directory and the existing StaticFiles mount at "/" is
repurposed in place to serve it (the pinned corpus route is NOT inserted).
When unset, the launcher behaves exactly as before. DB_PATH and RESEARCH_DIR
are rewired to G4 fixtures in BOTH modes. Validation fails closed at import:
relative / missing / file (not dir) / outside-repo / symlink-escape paths
all raise RuntimeError.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.routing import Mount, Route

from api import server


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DB = REPO_ROOT / "tests/fixtures/g4/sqlite/taxa-fixture.db"
RESEARCH_DIR = REPO_ROOT / "tests/fixtures/g4/research"
CORPUS_INDEX = REPO_ROOT / "tests/fixtures/g4/corpus/index.html"

if not FIXTURE_DB.is_file():
    raise RuntimeError(f"G4 fixture database missing: {FIXTURE_DB}")
if not CORPUS_INDEX.is_file():
    raise RuntimeError(f"G4 corpus index.html missing: {CORPUS_INDEX}")

server.DB_PATH = FIXTURE_DB
server.RESEARCH_DIR = RESEARCH_DIR


_STATIC_ROOT_ENV = "G4_STATIC_ROOT"


def _resolve_static_root(raw: str) -> Path:
    """Validate G4_STATIC_ROOT strictly. Order: absolute → exists → is_dir
    → resolved containment under REPO_ROOT. `Path.resolve()` follows
    symlinks, so a symlink inside the repo that resolves outside is caught
    by the containment check (no separate symlink-escape step needed).
    """
    p = Path(raw)
    if not p.is_absolute():
        raise RuntimeError(
            f"{_STATIC_ROOT_ENV} must be an absolute path; got relative: {raw!r}"
        )
    if not p.exists():
        raise RuntimeError(f"{_STATIC_ROOT_ENV} path does not exist: {raw!r}")
    if not p.is_dir():
        raise RuntimeError(
            f"{_STATIC_ROOT_ENV} must be an existing directory (not a file): {raw!r}"
        )
    resolved = p.resolve()
    repo_resolved = REPO_ROOT.resolve()
    try:
        resolved.relative_to(repo_resolved)
    except ValueError:
        raise RuntimeError(
            f"{_STATIC_ROOT_ENV} resolves outside the repo root "
            f"(repo={repo_resolved}, resolved={resolved}); out-of-tree or "
            f"symlink-escape paths are not permitted"
        )
    return resolved


_configured_root_raw = os.environ.get(_STATIC_ROOT_ENV)
_configured_root: Path | None = None
if _configured_root_raw:
    # Configured mode: validate, rewire WEB_DIR, repurpose the static mount.
    _configured_root = _resolve_static_root(_configured_root_raw)
    server.WEB_DIR = _configured_root
    # Find the existing "/" StaticFiles mount (Starlette's Mount.rstrip("/")
    # turns "/" into "" on the stored path, so identify by name) and
    # mutate its StaticFiles in place to honor the "through the existing
    # static mount" contract without re-ordering the route table.
    _existing_static_mount: Mount | None = None
    for _r in server.app.router.routes:
        if isinstance(_r, Mount) and getattr(_r, "name", None) == "web":
            _existing_static_mount = _r
            break
    if _existing_static_mount is not None:
        _sf = _existing_static_mount.app
        _sf.directory = str(_configured_root)
        # `all_directories` is what Starlette's lookup_path iterates; both
        # `directory` and `all_directories` must reflect the new path.
        _sf.all_directories = [_configured_root]
    else:
        # No pre-existing mount (production WEB_DIR did not exist at
        # api/server import time). Append a fresh mount at the end.
        server.app.router.routes.append(
            Mount("/", app=StaticFiles(directory=str(_configured_root), html=True), name="web")
        )

app = server.app


if _configured_root is None:
    # Default mode: insert the corpus /index.html route BEFORE the first
    # Mount. Starlette matches routes in declaration order, so the explicit
    # route wins for /index.html regardless of what api.server.WEB_DIR holds.
    async def serve_g4_corpus_index(request=None):
        """Serve the pinned G4 corpus index.html — always the fixture file,
        never anything from api.server.WEB_DIR. `request` is accepted to
        match FastAPI/Starlette's route signature; it is unused."""
        return FileResponse(CORPUS_INDEX, media_type="text/html")

    _corpus_route = Route("/index.html", endpoint=serve_g4_corpus_index, methods=["GET"])
    _mount_idx = next(
        (i for i, r in enumerate(app.router.routes) if isinstance(r, Mount)),
        len(app.router.routes),
    )
    app.router.routes.insert(_mount_idx, _corpus_route)
