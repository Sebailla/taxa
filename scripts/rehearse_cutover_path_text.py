"""PR 2/5 G6 rehearsal path & shell-text validators — pure stdlib only.

Two pure stdlib helpers used by the cutover-rehearsal pipeline to
defensively validate user-supplied text BEFORE any shell parsing,
filesystem traversal, or subprocess execution. Both helpers return
bool, never raise for ordinary malformed input, never perform I/O,
and never invoke a subprocess.

Out of scope for this slice:
- canonical end-to-end validation against cutover-manifest.json (PR 4/5)
- extending `rehearse_cutover.py` to consume these helpers (PR 3/5)
- updating `apply-progress.md` or claiming full G6 closure (PR 5/5)
"""
from __future__ import annotations

import re as _re
import shlex as _shlex


# Denied in path bodies. `:` is allowed only as the numeric-suffix
# separator (handled separately by the regex below).
_PATH_METACHARS = frozenset("`$\\;&|<>()*?![]{}'\"~#")

# Colons are forbidden in the body so that "foo:abc" or "c:foo" cannot
# slip past as a "non-numeric suffix"; they MUST be either absent or
# followed by digits at the very end.
_BODY_RE = _re.compile(
    r"^(?P<body>[^:\n\r\x00]+)"
    r"(?::(?P<line>\d+)(?::(?P<col>\d+))?)?$"
)


def validate_repo_relative_path(value: str) -> bool:
    """Return True iff `value` is a safe repo-relative slash path.

    Accepts ordinary repo-relative paths (e.g. `src/foo/bar.ts`) and an
    optional numeric `:line` or `:line:column` suffix (e.g.
    `src/foo.ts:12` or `src/foo.ts:12:34`). Rejects empty values,
    absolute Unix (`/foo`) and Windows (`C:/foo`, `C:\\foo`) paths,
    drive prefixes (`c:foo`), any `..` path component, null bytes,
    newlines, shell metacharacters, and any other control-character /
    unprintable content. The returned bool is the ONLY contract.
    """
    if not isinstance(value, str) or not value:
        return False
    if "\x00" in value or "\n" in value or "\r" in value:
        return False
    m = _BODY_RE.match(value)
    if m is None:
        return False
    body = m.group("body")
    if not body or body[0] == "/":
        return False
    if any(c in _PATH_METACHARS for c in body):
        return False
    parts = body.split("/")
    if any(p == "" for p in parts):
        return False  # empty component (foo//bar or trailing /)
    if any(p == ".." for p in parts):
        return False
    for p in parts:
        if any(ord(c) < 0x20 or ord(c) == 0x7f for c in p):
            return False
    return True


def parse_shell_text(value: str) -> bool:
    """Return True iff `value` parses as nonblank shell text.

    Uses `shlex.split` (POSIX mode) for validation ONLY — the parsed
    tokens are discarded; this function never executes the shell text
    and never passes it to subprocess. Empty / whitespace-only strings
    and strings containing a null byte are rejected. `ValueError` from
    `shlex.split` (e.g. unmatched quotes) is caught and converted to
    False rather than propagated.
    """
    if not isinstance(value, str) or not value or "\x00" in value:
        return False
    try:
        tokens = _shlex.split(value, posix=True)
    except ValueError:
        return False
    return bool(tokens)
