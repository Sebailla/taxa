"""G4-only ASGI launcher for controlled legacy capture.

It rewires api.server's module-local data paths without changing production code.
"""
from pathlib import Path

from api import server


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DB = REPO_ROOT / "tests/fixtures/g4/sqlite/taxa-fixture.db"
RESEARCH_DIR = REPO_ROOT / "tests/fixtures/g4/research"

if not FIXTURE_DB.is_file():
    raise RuntimeError(f"G4 fixture database missing: {FIXTURE_DB}")

server.DB_PATH = FIXTURE_DB
server.RESEARCH_DIR = RESEARCH_DIR
app = server.app
