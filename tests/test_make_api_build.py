"""Makefile::api build-chain contract tests (PR 3d).

Pins:
  make api → node scripts/check-runtime.mjs → npm ci → npm run build:web →
             uvicorn api.server:app --host 127.0.0.1 --port 8765
  make css → successful no-op (Tailwind 4 ships via next build, PR 3c)
  css / api both listed in .PHONY
  api does not depend on css
"""
from __future__ import annotations
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"


def _read_makefile() -> str:
    if not MAKEFILE.is_file():
        pytest.fail(f"Makefile missing at {MAKEFILE}")
    return MAKEFILE.read_text(encoding="utf-8")


def _target_body(target: str) -> list[str]:
    """Return the tab-indented recipe body of a Makefile target (no @echo banners stripped)."""
    lines = _read_makefile().splitlines()
    body: list[str] = []
    in_body = False
    for raw in lines:
        if not in_body:
            if re.match(rf"^{re.escape(target)}\s*:", raw):
                in_body = True
            continue
        if raw.startswith("\t"):
            body.append(raw[1:])
        elif raw.strip() == "":
            if body:
                break
        else:
            break
    return body


def _non_banner(body: list[str]) -> list[str]:
    return [line for line in body if not line.lstrip().startswith("@")]


def test_makefile_api_target_runs_check_runtime_first():
    """First non-banner step of `make api` MUST be the Node runtime guard."""
    body = _non_banner(_target_body("api"))
    assert body, "Makefile `api:` target has no non-banner steps"
    assert "node scripts/check-runtime.mjs" in body[0], (
        f"`make api` first non-banner step MUST be `node scripts/check-runtime.mjs`; "
        f"got {body[0]!r}"
    )


def test_makefile_api_target_ordering():
    """check-runtime.mjs → npm ci → npm run build:web → uvicorn (strict order)."""
    body = _non_banner(_target_body("api"))
    rt = next((i for i, l in enumerate(body) if "check-runtime" in l), None)
    ci = next((i for i, l in enumerate(body) if l.strip().startswith("npm ci")), None)
    bd = next((i for i, l in enumerate(body) if "build:web" in l), None)
    uv = next((i for i, l in enumerate(body) if "uvicorn" in l and "api.server:app" in l), None)
    assert rt is not None and ci is not None and bd is not None and uv is not None, (
        f"`make api` missing one of check-runtime/npm ci/build:web/uvicorn; "
        f"body={body!r}"
    )
    assert rt < ci < bd < uv, (
        f"`make api` step order wrong: check-runtime@{rt} npm ci@{ci} "
        f"build:web@{bd} uvicorn@{uv}; body={body!r}"
    )


def test_makefile_api_uvicorn_binds_localhost_8765():
    """uvicorn MUST bind 127.0.0.1:8765 (no LAN exposure, contract port)."""
    body = _non_banner(_target_body("api"))
    line = next((l for l in body if "uvicorn" in l and "api.server:app" in l), None)
    assert line is not None, f"`make api` missing uvicorn invocation; body={body!r}"
    assert "--host 127.0.0.1" in line, f"uvicorn must bind 127.0.0.1; got {line!r}"
    assert "--port 8765" in line, f"uvicorn must use --port 8765; got {line!r}"


def test_makefile_css_target_is_successful_noop():
    """`make css` MUST be a successful no-op (Tailwind 4 ships via next build)."""
    body = _target_body("css")
    assert body, "Makefile missing `css:` target"
    forbidden = (
        "npm install", "npm ci", "npm run build:css", "tailwindcss",
        "npm run watch:css", "web/index.css", "web/dist/tailwind.css",
    )
    leaks = [line for line in body if any(s in line for s in forbidden)]
    assert not leaks, (
        f"`make css` MUST be a no-op; legacy CSS pipeline calls found: {leaks!r}"
    )


def test_makefile_phony_includes_api_and_css():
    """`.PHONY` MUST include `api` and `css` so the recipes run every time."""
    m = re.search(r"^\.PHONY:\s*(.+?)\s*$", _read_makefile(), re.MULTILINE)
    assert m is not None, "Makefile missing `.PHONY:` declaration"
    targets = m.group(1).split()
    for t in ("api", "css"):
        assert t in targets, f"{t!r} MUST be in .PHONY; found {targets!r}"


def test_makefile_api_has_no_css_prerequisite():
    """`api:` MUST NOT list `css` as a prerequisite (CSS now ships via next build)."""
    m = re.search(r"^api\s*:[^\n]*$", _read_makefile(), re.MULTILINE)
    assert m is not None, "Makefile missing `api:` rule"
    prereqs = m.group(0).split(":", 1)[1].split()
    assert "css" not in prereqs, (
        f"`api:` MUST NOT depend on `css`; prereqs={prereqs!r}"
    )