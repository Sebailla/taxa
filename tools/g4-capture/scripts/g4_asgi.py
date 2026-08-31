"""G4-only ASGI launcher for controlled legacy capture.

It rewires api.server's module-local data paths without changing production
code, and serves the deterministic G4 corpus `index.html` at `/index.html`
so the capture producer never reaches the mutable production `web/` directory.

The corpus route is inserted BEFORE api.server's StaticFiles mount at the
root (declared at the bottom of api/server.py), so the static handler does
not swallow `/index.html` and return whatever happens to live in web/.
"""
from pathlib import Path

from fastapi.responses import FileResponse
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
app = server.app


async def serve_g4_corpus_index(request=None):
    """Serve the pinned G4 corpus index.html — always the fixture file,
    never anything from api.server.WEB_DIR. Content-Type is text/html so
    the capture producer's DOM marker check matches a real HTML payload.

    `request` is accepted to match FastAPI/Starlette's route signature
    expectation; it is unused. Defaulting to `None` keeps the function
    directly callable from tests if ever needed.
    """
    return FileResponse(CORPUS_INDEX, media_type="text/html")


# Insert /index.html BEFORE the first Mount on the app. The static mount at
# "/" (registered at the bottom of api/server.py) would otherwise serve
# web/index.html whenever it exists — that's exactly what the capture-3
# integrity guard rejects. Starlette's router matches in declaration order,
# so the explicit route wins for /index.html without affecting any other
# URL the static mount handles.
_corpus_route = Route("/index.html", endpoint=serve_g4_corpus_index, methods=["GET"])
_mount_idx = next(
    (i for i, r in enumerate(app.router.routes) if isinstance(r, Mount)),
    len(app.router.routes),
)
app.router.routes.insert(_mount_idx, _corpus_route)
