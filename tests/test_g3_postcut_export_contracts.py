"""Strict-TDD contract tests for the G3 post-cut export contracts helper
(`scripts/g3_postcut_export_contracts.py`). Follow-up 33 / Slice B.

Two test layers:

1. ``test_synthetic_*`` — pure ``tmp_path``-based tests that exercise
   the helpers against synthetic HTML / build-dir inputs. Selected
   by ``pytest -k 'synthetic_'``. They never read ``Path.cwd()/out``
   and never depend on a real Next.js export.

2. ``test_consumer_*`` — future G3 consumer nodes that read
   ``Path.cwd()/out`` (the isolated candidate worktree's export).
   These are real assertions for the future manifest contract but
   MUST NOT be run in this slice. They are deselected by
   ``pytest -k 'synthetic_'`` (NOT skipped). They remain unrun
   until a separately authorized isolated candidate worktree
   supplies ``Path.cwd()/out/index.html`` + ``Path.cwd()/out``.

Coverage matrix (Follow-up 33 / Slice B acceptance):
  #16 ``verify_root_shell(html_path)``
        accept: minimal HTML + realistic AppShell HTML.
        reject: missing marker / missing landmark / missing both / empty file.
  #17 ``verify_chunk_references(html_path, export_root)``
        accept: single + multiple valid references that resolve
                to non-empty files.
        reject: zero references / missing target / empty target /
                traversal / query / fragment / foreign origin
                (silently ignored but zero valid references then
                fail closed).
  #19 ``verify_build_profile_inventory(export_dir, output_path)``
        accept: synthetic build dir + explicit tmp_path output.
        reject: missing export dir / empty export dir.

The synthetic tests do NOT prove real ``out/`` conformance —
that requires a separately authorized isolated candidate worktree.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "g3_postcut_export_contracts.py"
EMIT_SCRIPT = REPO_ROOT / "scripts" / "emit_build_profile.mjs"


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


# ===========================================================================
# #19 — verify_build_profile_inventory
# ===========================================================================
def _make_synthetic_build_dir(root: Path) -> Path:
    """Create a synthetic Next.js-like build directory in root/build/."""
    build = root / "build"
    chunks = build / "_next" / "static" / "chunks"
    chunks.mkdir(parents=True)
    (chunks / "app-abc.js").write_bytes(b"a" * 4096)
    (chunks / "app-def.js").write_bytes(b"b" * 2048)
    chunks_css = build / "_next" / "static" / "css"
    chunks_css.mkdir(parents=True)
    (chunks_css / "app-abc.css").write_bytes(b"c" * 1024)
    framework = chunks / "framework-ghi.js"
    framework.write_bytes(b"d" * 8192)
    (build / "index.html").write_bytes(b"<html>" + b"e" * 1014)
    return build


def test_synthetic_build_profile_inventory_accepts_valid_export(tmp_path: Path):
    """A valid synthetic build directory must produce a profile
    with non-empty ``chunks`` / ``per_route_bytes`` and consistent
    internal sums:
      ``total_bytes == sum(chunk.bytes) == sum(per_route_bytes.values())``.
    No size or chunk-count threshold is imposed.
    """
    mod = _load_module()
    build = _make_synthetic_build_dir(tmp_path)
    output = tmp_path / "build-profile.json"
    profile = mod.verify_build_profile_inventory(build, output)
    assert isinstance(profile, dict)
    assert isinstance(profile["chunks"], list) and profile["chunks"]
    assert isinstance(profile["per_route_bytes"], dict) and profile["per_route_bytes"]
    assert isinstance(profile["total_bytes"], int) and profile["total_bytes"] >= 0
    chunk_sum = sum(c["bytes"] for c in profile["chunks"])
    per_route_sum = sum(profile["per_route_bytes"].values())
    assert profile["total_bytes"] == chunk_sum
    assert profile["total_bytes"] == per_route_sum
    # Output must live under tmp_path, not the repo.
    assert output.is_file()
    assert str(output.resolve()).startswith(str(tmp_path.resolve()))


def test_synthetic_build_profile_inventory_explicit_output_under_tmp(tmp_path: Path):
    """The profile JSON must be written exactly at the supplied
    explicit output_path (not derived from env or repo defaults).
    """
    mod = _load_module()
    build = _make_synthetic_build_dir(tmp_path)
    explicit = tmp_path / "explicit" / "build-profile.json"
    mod.verify_build_profile_inventory(build, explicit)
    assert explicit.is_file(), f"explicit output path missing: {explicit}"


def test_synthetic_build_profile_inventory_rejects_missing_export_dir(tmp_path: Path):
    """A missing export directory must fail closed (subprocess non-zero)."""
    mod = _load_module()
    missing = tmp_path / "no-such-export"
    output = tmp_path / "build-profile.json"
    with pytest.raises(mod.PostcutContractError):
        mod.verify_build_profile_inventory(missing, output)


def test_synthetic_build_profile_inventory_rejects_empty_export_dir(tmp_path: Path):
    """An empty export directory must fail closed (emitter refuses)."""
    mod = _load_module()
    empty = tmp_path / "empty"
    empty.mkdir()
    output = tmp_path / "build-profile.json"
    with pytest.raises(mod.PostcutContractError):
        mod.verify_build_profile_inventory(empty, output)


def test_synthetic_build_profile_inventory_rejects_non_object_json_root(
    tmp_path: Path, monkeypatch
):
    """A profile JSON whose root is not an object (e.g. ``[]``,
    ``null``, an int, or a string) must fail closed with
    :class:`PostcutContractError` (NOT ``AttributeError``). The
    emitter is monkeypatched to write each non-object root directly
    to the ``tmp_path`` output so the helper's JSON parsing path is
    exercised without invoking Node.
    """
    mod = _load_module()
    build = _make_synthetic_build_dir(tmp_path)

    for bad_root in ("[]", "null", "42", '"a string"'):
        output_path = tmp_path / f"profile-{hash(bad_root) & 0xffffffff}.json"

        def _fake_emit(*args, _output=output_path, _body=bad_root, **kwargs):
            _output.write_text(_body)
            return subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )

        monkeypatch.setattr(mod, "_emit_build_profile", _fake_emit)
        with pytest.raises(mod.PostcutContractError):
            mod.verify_build_profile_inventory(build, output_path)


def _sentinel_fail_if_called(*args, **kwargs):
    """Sentinel replacement for ``_emit_build_profile`` that raises
    ``AssertionError`` if called. Used to prove the helper rejects
    disallowed output paths BEFORE invoking the emitter.
    """
    raise AssertionError(
        "_emit_build_profile MUST NOT be called when output_path "
        "is rejected by the containment guard"
    )


def test_synthetic_build_profile_inventory_rejects_output_inside_export(
    tmp_path: Path, monkeypatch
):
    """An explicit ``output_path`` that resolves inside (or equals)
    the resolved ``export_dir`` must fail closed with
    :class:`PostcutContractError` BEFORE the emitter subprocess
    is invoked. ``_emit_build_profile`` is monkeypatched to a
    sentinel that raises ``AssertionError`` if called so rejection
    proves containment happens first.
    """
    mod = _load_module()
    build = _make_synthetic_build_dir(tmp_path)
    # Direct containment: output inside export_dir/subpath
    output_path = build / "subpath" / "profile.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mod, "_emit_build_profile", _sentinel_fail_if_called)
    with pytest.raises(mod.PostcutContractError) as excinfo:
        mod.verify_build_profile_inventory(build, output_path)
    msg = str(excinfo.value).lower()
    assert "inside" in msg or "export_dir" in msg or "export" in msg, (
        f"expected containment-related error, got: {excinfo.value!r}"
    )


def test_synthetic_build_profile_inventory_rejects_output_equal_to_export_dir(
    tmp_path: Path, monkeypatch
):
    """An explicit ``output_path`` that equals the resolved
    ``export_dir`` (the directory itself, not a file inside it)
    must fail closed with :class:`PostcutContractError`. The
    emitter must NOT be called.
    """
    mod = _load_module()
    build = _make_synthetic_build_dir(tmp_path)
    output_path = build  # equal to export_dir itself
    monkeypatch.setattr(mod, "_emit_build_profile", _sentinel_fail_if_called)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_build_profile_inventory(build, output_path)


def test_synthetic_build_profile_inventory_rejects_symlink_resolving_inside_export(
    tmp_path: Path, monkeypatch
):
    """An explicit ``output_path`` that is a symlink resolving inside
    the export directory must fail closed with
    :class:`PostcutContractError` BEFORE the emitter subprocess is
    invoked. ``Path.resolve()`` follows the symlink so the
    containment guard sees the resolved target, not the link
    itself. The emitter must NOT be called.

    Skipped with an explicit reason when the platform cannot
    create symlinks (e.g. some Windows configurations).
    """
    if not hasattr(Path, "symlink_to"):
        pytest.skip("platform does not support Path.symlink_to")
    mod = _load_module()
    build = _make_synthetic_build_dir(tmp_path)

    # Create a symlink that resolves into the export tree.
    symlink_target = build / "subpath" / "target.json"
    symlink_target.parent.mkdir(parents=True, exist_ok=True)
    symlink_target.touch()
    symlink_path = tmp_path / "link.json"
    try:
        symlink_path.symlink_to(symlink_target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"platform cannot create symlinks: {exc}")

    monkeypatch.setattr(mod, "_emit_build_profile", _sentinel_fail_if_called)
    with pytest.raises(mod.PostcutContractError):
        mod.verify_build_profile_inventory(build, symlink_path)


def test_synthetic_build_profile_inventory_rejects_output_inside_repo_root(
    tmp_path: Path, monkeypatch
):
    """An explicit ``output_path`` that resolves anywhere inside the
    repo root must fail closed with :class:`PostcutContractError`
    BEFORE the emitter subprocess is invoked. The intended caller
    destination is external pytest ``tmp_path``; never write into
    repo-owned paths. ``_emit_build_profile`` is monkeypatched to a
    sentinel so rejection proves containment happens first.
    """
    mod = _load_module()
    build = _make_synthetic_build_dir(tmp_path)
    # A non-existent path inside the repo root. ``Path.resolve()``
    # handles non-existent paths via lexical resolution; the file
    # is NEVER created because the helper rejects before the
    # emitter subprocess runs.
    output_path = REPO_ROOT / "scripts" / "sneaky-profile.json"
    assert not output_path.exists(), (
        f"unexpected pre-existing file at {output_path}; pick a "
        f"different test path"
    )

    monkeypatch.setattr(mod, "_emit_build_profile", _sentinel_fail_if_called)
    with pytest.raises(mod.PostcutContractError) as excinfo:
        mod.verify_build_profile_inventory(build, output_path)
    msg = str(excinfo.value).lower()
    assert "repo" in msg or "repository" in msg, (
        f"expected repo-root-related error, got: {excinfo.value!r}"
    )
    # The file MUST NOT have been created by the rejected call.
    assert not output_path.exists(), (
        f"output_path was created despite containment rejection: "
        f"{output_path}"
    )


# ===========================================================================
# Future G3 consumer nodes (DESELECTED under -k 'synthetic_').
# MUST NOT be run in this slice. They are real assertions for the
# future isolated-candidate-worktree contract only.
# ===========================================================================
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


def test_consumer_build_profile_inventory(tmp_path: Path):
    """Future G3 consumer for #19: verify the build profile
    inventory of the real ``out/`` when present in the isolated
    candidate worktree. Reads ``Path.cwd()/out`` (emitter input)
    and writes the profile JSON to ``tmp_path/build-profile.json``
    (NOT ``Path.cwd()/out`` and NOT repo ``web/dist``) so the
    export directory is never mutated. NOT a G3 pass; NOT run in
    this slice.
    """
    mod = _load_module()
    out_dir = Path.cwd() / "out"
    if not out_dir.is_dir():
        pytest.skip(
            "no out/ in current worktree; future isolated candidate worktree only"
        )
    output_path = tmp_path / "build-profile.json"
    mod.verify_build_profile_inventory(out_dir, output_path)


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
