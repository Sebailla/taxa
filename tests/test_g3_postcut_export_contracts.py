"""Synthetic and future real-export consumer tests for G3 #16.

Synthetic tests use ``tmp_path``; the real ``out/index.html`` consumer
is retained for a separately authorized isolated candidate worktree.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "g3_postcut_export_contracts.py"


def _load_module():
    """Import ``scripts/g3_postcut_export_contracts.py`` via importlib
    so the test file does not depend on the repo being on sys.path.

    Mirrors the pattern used by ``tests/test_g4_hybrid_asgi.py`` and
    ``tests/test_g5_legacy_orchestration.py``. Caching the module
    in ``sys.modules`` keeps it a stable identity across calls
    without forcing a re-import on every test.
    """
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    cached = sys.modules.get("scripts.g3_postcut_export_contracts")
    if cached is not None:
        return cached
    if not SCRIPT.exists():
        raise RuntimeError(f"missing g3 contracts script: {SCRIPT}")
    return importlib.import_module("scripts.g3_postcut_export_contracts")


def test_script_exists():
    """The g3_postcut_export_contracts.py script must be created
    by Follow-up 33 / Slice B.
    """
    assert SCRIPT.exists(), (
        f"missing g3 contracts script: {SCRIPT}. "
        f"Follow-up 33 / Slice B requires this script to exist."
    )


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------
def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

# ===========================================================================
# #16 — verify_root_shell
# ===========================================================================
def test_synthetic_root_shell_accepts_minimal_index_html(tmp_path: Path):
    """A minimal HTML containing the ``data-app-shell`` marker and
    a ``<main`` landmark must be accepted.
    """
    mod = _load_module()
    html = '<html><body><div data-app-shell=""><main></main></div></body></html>'
    f = tmp_path / "index.html"
    _write(f, html)
    mod.verify_root_shell(f)  # must not raise


def test_synthetic_root_shell_accepts_realistic_appshell_html(tmp_path: Path):
    """A realistic Next.js export HTML carrying the actual AppShell
    output (``data-app-shell=""`` and ``<main class="app-shell-main ...">``)
    must be accepted.
    """
    mod = _load_module()
    html = """<!doctype html>
<html><head><title>Test</title></head>
<body>
<div class="app-shell flex min-h-screen flex-col bg-surface-container-lowest text-on-surface" data-app-shell="">
  <header>...</header>
  <main class="app-shell-main flex-1">
    <div id="main" class="app-shell-main-anchor mx-auto w-full max-w-none px-6 py-6">
      Hello
    </div>
  </main>
  <footer>...</footer>
</div>
</body></html>
"""
    f = tmp_path / "index.html"
    _write(f, html)
    mod.verify_root_shell(f)


def test_synthetic_root_shell_rejects_missing_marker(tmp_path: Path):
    """HTML missing the ``data-app-shell`` marker must fail closed."""
    mod = _load_module()
    html = "<html><body><main>No AppShell here</main></body></html>"
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_root_shell(f)


def test_synthetic_root_shell_rejects_missing_main(tmp_path: Path):
    """HTML missing the ``<main`` landmark must fail closed."""
    mod = _load_module()
    html = '<html><body><div data-app-shell="">No main</div></body></html>'
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_root_shell(f)


def test_synthetic_root_shell_rejects_missing_both(tmp_path: Path):
    """HTML missing both the marker AND the landmark must fail closed."""
    mod = _load_module()
    html = "<html><body><div>Empty</div></body></html>"
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_root_shell(f)


def test_synthetic_root_shell_rejects_empty_file(tmp_path: Path):
    """An empty HTML file must fail closed."""
    mod = _load_module()
    f = tmp_path / "index.html"
    f.write_bytes(b"")
    with pytest.raises(mod.PostcutContractError):
        mod.verify_root_shell(f)

def test_consumer_root_shell():
    """Future G3 consumer for #16: verify the AppShell markers in
    the real ``out/index.html`` when present in the isolated
    candidate worktree. Reads ``Path.cwd()/out/index.html``. NOT a
    G3 pass; NOT G3 evidence; NOT run in this slice.
    """
    mod = _load_module()
    out_index = Path.cwd() / "out" / "index.html"
    if not out_index.is_file():
        pytest.skip(
            "no out/index.html in current worktree; "
            "future isolated candidate worktree only"
        )
    mod.verify_root_shell(out_index)
