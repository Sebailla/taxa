"""Static-mount contract tests for the FastAPI WEB_DIR repoint (PR 3d).

PR 3d repoints api/server.py::WEB_DIR from `web/` to `out/` (Next 16 static
export target). The mount signature MUST stay byte-identical so the FastAPI
OpenAPI schema and Starlette route resolution are unchanged, and so a future
reviewer can read the mount change as a one-line repoint (not a rewrite).
"""
from __future__ import annotations
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_PY = REPO_ROOT / "api" / "server.py"

EXPECTED_MOUNT_LINE = (
    '    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")'
)


def _read_server_py() -> str:
    if not SERVER_PY.is_file():
        pytest.fail(f"api/server.py missing at {SERVER_PY}")
    return SERVER_PY.read_text(encoding="utf-8")


def test_web_dir_constant_points_to_out():
    """WEB_DIR MUST resolve to `<repo>/out/`, NOT `<repo>/web/`."""
    text = _read_server_py()
    m = re.search(
        r'^WEB_DIR\s*=\s*Path\(__file__\)\.parent\.parent\s*/\s*"([^"]+)"',
        text, re.MULTILINE,
    )
    assert m is not None, "WEB_DIR assignment missing or non-PatternLiteral"
    assert m.group(1) == "out", (
        f"WEB_DIR must point to \"out\" (Next static export target); "
        f"got {m.group(1)!r}"
    )
    assert m.group(1) != "web", (
        f"WEB_DIR MUST NOT point at \"web\" (legacy target); got {m.group(1)!r}"
    )


def test_static_mount_signature_is_byte_identical():
    """The mount call MUST stay byte-identical across the WEB_DIR repoint."""
    text = _read_server_py()
    assert EXPECTED_MOUNT_LINE in text, (
        f"mount line drifted from byte-exact contract; expected\n"
        f"  {EXPECTED_MOUNT_LINE!r}\n"
        f"PR 3d only repoints WEB_DIR; the mount signature is pinned."
    )


def test_static_mount_appears_after_api_routes():
    """The mount MUST be the LAST `app.mount(` call, AFTER the last @app.* decorator.

    Moving the mount above the API routes breaks /api/* precedence (Starlette's
    mount swallows unmatched paths, returning 404 instead of routing to FastAPI).
    """
    lines = _read_server_py().splitlines()
    mount_idx = max(
        (i for i, l in enumerate(lines) if re.match(r"^\s*app\.mount\(", l)),
        default=-1,
    )
    assert mount_idx > -1, "no app.mount( in api/server.py"
    decorator_idx = max(
        (i for i, l in enumerate(lines) if re.match(r"^@app\.(get|post|put|delete|patch)\(", l)),
        default=-1,
    )
    assert decorator_idx > -1, "no @app.* decorators in api/server.py"
    assert mount_idx > decorator_idx, (
        f"app.mount (line {mount_idx + 1}) MUST come after the last @app.* "
        f"decorator (line {decorator_idx + 1})"
    )


def test_static_mount_only_one_app_mount_call():
    """Exactly ONE `app.mount(` call. Multiple mounts = split route ownership regression."""
    mounts = re.findall(r"^\s*app\.mount\(", _read_server_py(), re.MULTILINE)
    assert len(mounts) == 1, (
        f"api/server.py MUST have exactly one `app.mount(` call; found {len(mounts)}"
    )