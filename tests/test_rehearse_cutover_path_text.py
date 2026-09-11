"""Strict-TDD contract tests for `scripts/rehearse_cutover_path_text.py`.

PR 2/5 ships exactly two pure stdlib helpers:

1. `validate_repo_relative_path(value: str) -> bool`
2. `parse_shell_text(value: str) -> bool`

Five contract tests pin their behaviour:

1. `test_validate_repo_relative_path_accepts_ordinary` — parametrized
   over ordinary repo-relative slash paths (with and without the
   optional numeric `:line[:column]` suffix).
2. `test_validate_repo_relative_path_rejects_malformed` — parametrized
   over empty, absolute Unix/Windows, drive prefixes, `..` components,
   shell metacharacters, null/newline, empty path components, and
   malformed numeric suffixes.
3. `test_parse_shell_text_accepts_parseable` — parametrized over
   ordinary shell text accepted by `shlex.split`.
4. `test_parse_shell_text_rejects_unparseable` — parametrized over
   empty / whitespace / null-byte / unclosed-quote inputs (rejected).
5. `test_import_has_no_side_effects` — import-time purity: no exec,
   no file write, no manifest read; public surface is exactly the two
   documented helpers.

Hermetic: in-process imports only, no subprocess, no network, no
service, no FastAPI, no port binding, no product-file mutation. The
canonical `cutover-manifest.json` is NOT consumed by PR 2/5.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


MODULE = "scripts.rehearse_cutover_path_text"
SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "rehearse_cutover_path_text.py"
)


@pytest.mark.parametrize(
    "value",
    [
        "src/foo/bar.ts",
        "a/b/c",
        "single.ts",
        "deep/nested/path/to/file.tsx",
        "src/foo.ts:12",
        "src/foo.ts:12:34",
        "src/foo.ts:1:1",
        "x/y:999:999",
        "path-with-dashes/file_123.ts",
        "src/file.min.ts",
    ],
)
def test_validate_repo_relative_path_accepts_ordinary(value):
    """Ordinary repo-relative slash paths and the optional numeric
    `:line[:column]` suffix MUST be accepted."""
    assert SCRIPT.is_file(), (
        f"missing {SCRIPT}; PR 2/5 must author "
        f"scripts/rehearse_cutover_path_text.py before this test can pass."
    )
    from scripts.rehearse_cutover_path_text import validate_repo_relative_path
    assert validate_repo_relative_path(value) is True, value


@pytest.mark.parametrize(
    "value",
    [
        "",                          # empty
        "/etc/passwd",               # absolute Unix
        "C:/Windows/System32",       # absolute Windows forward slash
        "C:\\Windows\\System32",     # absolute Windows backslash
        "D:foo",                     # drive prefix without separator
        "a/b/../c",                  # .. component in the middle
        "../etc/passwd",             # leading ..
        "a/..",                      # trailing ..
        "..",                        # bare ..
        "src/foo$bar.ts",            # shell metachar $
        "src/foo;rm.ts",             # shell metachar ;
        "src/foo|bar.ts",            # shell metachar |
        "src/foo&bar.ts",            # shell metachar &
        "src/foo`bar`.ts",           # shell metachar `
        "src/foo*.ts",               # shell metachar *
        "src/foo?.ts",               # shell metachar ?
        "src/foo~bar.ts",            # shell metachar ~ (home expansion)
        "src/foo#bar.ts",            # shell metachar # (comment)
        "src/foo\nbar.ts",           # newline
        "src/foo\rbar.ts",           # carriage return
        "src/foo\x00bar.ts",         # null byte
        "a//b",                      # empty component (double slash)
        "a/b/",                      # trailing slash (empty component)
        "src/foo.ts:",               # empty numeric suffix
        "src/foo.ts:abc",            # non-numeric suffix
        "src/foo.ts:-1",             # negative line
        "src/foo.ts:12:abc",         # non-numeric column
        "src/foo.ts:1.5",            # non-integer line
    ],
)
def test_validate_repo_relative_path_rejects_malformed(value):
    """Empty, absolute Unix/Windows, drive prefixes, `..` components,
    shell metacharacters, null/newline, empty path components, and
    malformed numeric suffixes MUST be rejected. MUST NOT raise."""
    assert SCRIPT.is_file(), (
        f"missing {SCRIPT}; PR 2/5 must author "
        f"scripts/rehearse_cutover_path_text.py before this test can pass."
    )
    from scripts.rehearse_cutover_path_text import validate_repo_relative_path
    assert validate_repo_relative_path(value) is False, value


@pytest.mark.parametrize(
    "value",
    [
        "echo ok",
        "echo 'hello world'",
        'echo "hello world"',
        "ls -la /tmp",
        "git status",
        "FOO=bar bash -c 'echo $FOO'",
        "echo $PATH",
        "echo a && echo b",
        "echo a; echo b",
    ],
)
def test_parse_shell_text_accepts_parseable(value):
    """Ordinary shell text — quoted strings, env-var references, and
    common operators — MUST be accepted by `shlex.split`. The helper
    MUST NOT execute the text; that contract is pinned by
    `test_import_has_no_side_effects`."""
    assert SCRIPT.is_file(), (
        f"missing {SCRIPT}; PR 2/5 must author "
        f"scripts/rehearse_cutover_path_text.py before this test can pass."
    )
    from scripts.rehearse_cutover_path_text import parse_shell_text
    assert parse_shell_text(value) is True, value


@pytest.mark.parametrize(
    "value",
    [
        "",                          # empty
        "   ",                       # whitespace only
        "\t\t",                      # tabs only
        "echo 'unclosed",            # unclosed single quote
        'echo "unclosed',            # unclosed double quote
        "echo a\x00b",               # null byte
    ],
)
def test_parse_shell_text_rejects_unparseable(value):
    """Empty, whitespace-only, null-byte, and unclosed-quote inputs
    MUST be rejected. MUST NOT raise — `ValueError` from `shlex.split`
    is caught and converted to False."""
    assert SCRIPT.is_file(), (
        f"missing {SCRIPT}; PR 2/5 must author "
        f"scripts/rehearse_cutover_path_text.py before this test can pass."
    )
    from scripts.rehearse_cutover_path_text import parse_shell_text
    assert parse_shell_text(value) is False, value


def test_import_has_no_side_effects(tmp_path):
    """Importing `scripts.rehearse_cutover_path_text` MUST NOT execute
    any shell text, write any file, spawn any subprocess, or read any
    manifest. Asserted by:

    1. Forcing a fresh import (defeat any prior cache state) and
       confirming no file appears under `tmp_path` from import-time
       side effects.
    2. Public surface is EXACTLY the two documented helpers — anything
       else (private I/O helpers, manifest readers, exec wrappers)
       would mean scope creep beyond PR 2/5.
    3. `__all__` (if declared) matches the public surface, signalling
       an intentional export boundary.
    """
    sys.modules.pop(MODULE, None)
    assert SCRIPT.is_file(), (
        f"missing {SCRIPT}; PR 2/5 must author "
        f"scripts/rehearse_cutover_path_text.py before this test can pass."
    )
    mod = importlib.import_module(MODULE)
    # `annotations` is a module-level dict added by
    # `from __future__ import annotations` (PEP 563); it is a Python
    # language artifact, not a helper. Every other non-underscore name
    # IS a helper and must match exactly.
    public = sorted(
        n for n in dir(mod)
        if not n.startswith("_") and n != "annotations"
    )
    assert public == ["parse_shell_text", "validate_repo_relative_path"], public
    dunder_all = getattr(mod, "__all__", None)
    if dunder_all is not None:
        assert sorted(dunder_all) == public, (
            f"__all__={dunder_all!r} must match the public surface "
            f"{public!r}"
        )
    leftovers = [p.name for p in tmp_path.rglob("*") if p.is_file()]
    assert not leftovers, (
        f"importing {MODULE} wrote to {tmp_path}; the module MUST be "
        f"side-effect free. Found: {leftovers}"
    )
