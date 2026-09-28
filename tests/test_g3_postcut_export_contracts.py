"""Synthetic and future real-export consumer tests for G3 #16 and #17.

Synthetic HTML/export inputs use ``tmp_path``. Real ``out`` consumer nodes
remain separate and are not run as part of this contract slice.
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

def _make_chunk_file(
    export_root: Path, name: str, content: bytes = b"// chunk"
) -> Path:
    """Create a chunk file under export_root/_next/static/chunks/<name>."""
    p = export_root / "_next" / "static" / "chunks" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return p

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


# ===========================================================================
# #17 — verify_chunk_references
# ===========================================================================
def test_synthetic_chunk_references_accepts_single_valid_reference(tmp_path: Path):
    """An HTML with one first-party ``/_next/static/chunks/main.js``
    reference whose target exists and is non-empty must be accepted.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    _make_chunk_file(export_root, "main-app.js", b"console.log(1);" * 100)
    html = (
        "<html><body>"
        '<script src="/_next/static/chunks/main-app.js"></script>'
        "</body></html>"
    )
    f = tmp_path / "index.html"
    _write(f, html)
    refs = mod.verify_chunk_references(f, export_root)
    assert refs == ["/_next/static/chunks/main-app.js"]


def test_synthetic_chunk_references_accepts_multiple_valid_references(tmp_path: Path):
    """An HTML with multiple first-party references must be accepted
    when each target resolves to a non-empty file.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    for name in ("app.js", "framework.js", "main-app.js"):
        _make_chunk_file(export_root, name, b"// " + name.encode())
    html = (
        '<script src="/_next/static/chunks/framework.js"></script>'
        '<script src="/_next/static/chunks/main-app.js"></script>'
        '<script src="/_next/static/chunks/app.js"></script>'
    )
    f = tmp_path / "index.html"
    _write(f, html)
    refs = mod.verify_chunk_references(f, export_root)
    assert refs == sorted(
        [
            "/_next/static/chunks/app.js",
            "/_next/static/chunks/framework.js",
            "/_next/static/chunks/main-app.js",
        ]
    )


def test_synthetic_chunk_references_rejects_zero_references(tmp_path: Path):
    """An HTML with no first-party chunk references must fail closed."""
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    html = "<html><body>No chunks here</body></html>"
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_chunk_references(f, export_root)


def test_synthetic_chunk_references_rejects_missing_target(tmp_path: Path):
    """An HTML with a first-party reference whose target does NOT
    exist on disk must fail closed.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    html = '<script src="/_next/static/chunks/does-not-exist.js"></script>'
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_chunk_references(f, export_root)


def test_synthetic_chunk_references_rejects_empty_target(tmp_path: Path):
    """An HTML with a first-party reference whose target exists but
    is empty (zero bytes) must fail closed.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    _make_chunk_file(export_root, "empty.js", b"")
    html = '<script src="/_next/static/chunks/empty.js"></script>'
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_chunk_references(f, export_root)


def test_synthetic_chunk_references_rejects_traversal(tmp_path: Path):
    """An HTML containing a chunk-shaped path with traversal
    (``../``) must fail closed.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    html = '<script src="/_next/static/chunks/../escape.js"></script>'
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_chunk_references(f, export_root)


def test_synthetic_chunk_references_rejects_query(tmp_path: Path):
    """An HTML containing a chunk-shaped path with a query string
    (``?v=1``) must fail closed.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    _make_chunk_file(export_root, "main.js", b"x")
    html = '<script src="/_next/static/chunks/main.js?v=1"></script>'
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_chunk_references(f, export_root)


def test_synthetic_chunk_references_rejects_fragment(tmp_path: Path):
    """An HTML containing a chunk-shaped path with a fragment
    (``#frag``) must fail closed.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    _make_chunk_file(export_root, "main.js", b"x")
    html = '<script src="/_next/static/chunks/main.js#frag"></script>'
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_chunk_references(f, export_root)


def test_synthetic_chunk_references_ignores_foreign_origin(tmp_path: Path):
    """Foreign-origin URLs (``https://...``, ``//cdn...``) must be
    ignored without failing closed; the absence of valid first-party
    references must still fail closed.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    html = (
        '<script src="https://cdn.example.com/_next/static/chunks/cdn.js">'
        "</script>"
        '<script src="//cdn.example.com/_next/static/chunks/cdn2.js">'
        "</script>"
    )
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_chunk_references(f, export_root)


def test_synthetic_chunk_references_accepts_real_attribute_ref_ignores_comment_ref(
    tmp_path: Path,
):
    """An HTML with one valid attribute ref AND a chunk-shaped
    substring inside a comment must accept only the real attribute
    ref. The comment text is ignored — the parser only inspects
    ``src`` / ``href`` attribute values, not arbitrary body text.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    _make_chunk_file(export_root, "real.js", b"// real chunk")
    html = (
        "<!-- /_next/static/chunks/commented-out.js -->\n"
        '<script src="/_next/static/chunks/real.js"></script>\n'
    )
    f = tmp_path / "index.html"
    _write(f, html)
    refs = mod.verify_chunk_references(f, export_root)
    assert refs == ["/_next/static/chunks/real.js"]


def test_synthetic_chunk_references_rejects_encoded_traversal(tmp_path: Path):
    """An HTML containing a percent-encoded chunk-shaped path with
    traversal (``%2e%2e/`` decodes to ``../``) must fail closed
    with a traversal-specific :class:`PostcutContractError`. The
    helper must percent-decode each candidate URL before segment
    validation so encoded traversal cannot bypass the check.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    html = '<script src="/_next/static/chunks/%2e%2e/escape.js"></script>'
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError) as excinfo:
        mod.verify_chunk_references(f, export_root)
    # The error message must mention traversal specifically (not the
    # generic "no first-party references" failure that the prior
    # regex produced by silently dropping the encoded shape).
    assert "traversal" in str(excinfo.value).lower(), (
        f"expected traversal-specific error, got: {excinfo.value!r}"
    )


def test_synthetic_chunk_references_accepts_mixed_foreign_and_first_party(
    tmp_path: Path,
):
    """An HTML with both a foreign URL AND a valid first-party ref
    must accept only the first-party ref. Foreign-origin URLs
    remain ignored even when a valid first-party ref is also
    present (forward-only rule, no false failure).
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    _make_chunk_file(export_root, "real.js", b"// real chunk")
    html = (
        '<script src="https://cdn.example.com/_next/static/chunks/cdn.js">'
        "</script>"
        '<script src="//cdn.example.com/_next/static/chunks/cdn2.js">'
        "</script>"
        '<script src="/_next/static/chunks/real.js"></script>'
    )
    f = tmp_path / "index.html"
    _write(f, html)
    refs = mod.verify_chunk_references(f, export_root)
    assert refs == ["/_next/static/chunks/real.js"]

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

def test_consumer_chunk_references():
    """Future G3 consumer for #17: verify first-party chunk
    references in the real ``out/index.html`` when present in the
    isolated candidate worktree. NOT a G3 pass; NOT run in this slice.
    """
    mod = _load_module()
    out_index = Path.cwd() / "out" / "index.html"
    out_dir = Path.cwd() / "out"
    if not out_index.is_file() or not out_dir.is_dir():
        pytest.skip(
            "no out/ in current worktree; future isolated candidate worktree only"
        )
    mod.verify_chunk_references(out_index, out_dir)


def test_synthetic_chunk_references_ignores_stylesheet_refs(tmp_path: Path):
    """An HTML carrying a Next.js ``<link rel="stylesheet">`` reference
    under the same ``/_next/static/chunks/`` prefix AND a valid first-party
    JS reference must verify only the JS reference. The stylesheet
    reference is out of scope for the JS-only chunk contract and must be
    silently dropped (no fail-closed on the ``.css`` extension), while
    the valid JS reference continues to be verified.

    Regression: PR #458 / CI run 36473147141 — the post-cut Next.js
    static export injects ``/_next/static/chunks/<hash>.css`` as a
    stylesheet via ``<link rel="stylesheet" href="...">``. That asset
    shares the chunk prefix but is not a JS chunk and must not be
    treated as a malformed chunk reference; only the matching ``.js``
    reference is part of the chunk contract.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    _make_chunk_file(export_root, "real.js", b"// real chunk")
    html = (
        '<link rel="stylesheet" '
        'href="/_next/static/chunks/10l7g2zktrg2x.css">'
        '<script src="/_next/static/chunks/real.js"></script>'
    )
    f = tmp_path / "index.html"
    _write(f, html)
    refs = mod.verify_chunk_references(f, export_root)
    assert refs == ["/_next/static/chunks/real.js"]


def test_synthetic_chunk_references_rejects_unsupported_extension(tmp_path: Path):
    """An HTML with a valid first-party JS reference AND a chunk-shaped
    reference with an unsupported extension (``foo.jsx``) must fail
    closed. The CSS-only exception is narrow: only ``.css``-suffixed
    stylesheet references are silently dropped — every other chunk-shaped
    extension must reach ``_validate_first_party_chunk`` and fail the
    canonical ``[A-Za-z0-9_-]+\\.js$`` filename regex. A reference with
    ``.jsx`` extension is NOT a CSS stylesheet and must not be
    silently skipped.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    _make_chunk_file(export_root, "real.js", b"// real chunk")
    html = (
        '<script src="/_next/static/chunks/real.js"></script>'
        '<script src="/_next/static/chunks/foo.jsx"></script>'
    )
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_chunk_references(f, export_root)


def test_synthetic_chunk_references_rejects_js_trailing_slash(tmp_path: Path):
    """An HTML with a valid first-party JS reference AND a chunk-shaped
    reference with a trailing slash (``foo.js/``) must fail closed. The
    CSS-only exception is narrow: a non-CSS chunk-shaped path with an
    empty trailing segment must NOT be silently dropped — it must reach
    ``_validate_first_party_chunk`` and fail the existing empty-segment
    check.
    """
    mod = _load_module()
    export_root = tmp_path / "export"
    export_root.mkdir()
    _make_chunk_file(export_root, "real.js", b"// real chunk")
    html = (
        '<script src="/_next/static/chunks/real.js"></script>'
        '<script src="/_next/static/chunks/foo.js/"></script>'
    )
    f = tmp_path / "index.html"
    _write(f, html)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_chunk_references(f, export_root)
