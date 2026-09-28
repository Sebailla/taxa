"""G3 post-cut root-shell and first-party chunk-reference contracts.

#16 verifies the AppShell marker and ``<main`` landmark. #17 extracts
first-party ``/_next/static/chunks/*.js`` URLs only from HTML ``src`` and
``href`` attributes with stdlib ``HTMLParser``, decodes percent escapes
before traversal validation, and checks forward reference integrity inside
the supplied export root. Synthetic tests use ``tmp_path``; future real
export consumers are kept separate and do not establish a G3 pass.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

class PostcutContractError(Exception):
    """Raised by the three helpers on any verification failure.

    The future G3 consumer (``tests/test_g3_postcut_export_contracts.py
    ::test_consumer_*``) propagates this exception to pytest so a
    structural / export regression is surfaced as a real test
    failure instead of a silent pass.
    """


# ===========================================================================
# #16 — root-shell structure (data-app-shell marker + <main landmark)
#
# Anchored to ``src/modules/app-shell/presentation/AppShell.tsx``:
#
#     <div
#       className="app-shell flex min-h-screen flex-col ..."
#       data-app-shell=""
#     >
#       ...
#       <main className="app-shell-main flex-1">
#         ...
#       </main>
#       ...
#     </div>
#
# After React rendering, ``className`` becomes ``class`` and the
# boolean-true (``=""``) data attribute becomes ``data-app-shell=""``.
# Both the marker substring and the landmark regex are intentionally
# permissive: the marker is a substring search, the landmark uses a
# word boundary so ``<mainland>`` / ``<maintenance>`` cannot satisfy
# the contract.
# ===========================================================================
ROOT_SHELL_MARKER = "data-app-shell"
# ``<main`` followed by a word boundary (``\b``), a non-word
# character such as whitespace, ``>``, or a quote. This rejects
# ``<mainland>`` / ``<maintenance>`` while still matching the
# React-rendered ``<main class="...">`` and a bare ``<main>``.
ROOT_SHELL_LANDMARK_RE = re.compile(r"<main\b")


def verify_root_shell(html_path: Path) -> None:
    """Verify that ``html_path`` carries the AppShell ``data-app-shell``
    marker AND a ``<main`` landmark, based on
    ``src/modules/app-shell/presentation/AppShell.tsx``.

    Raises :class:`PostcutContractError` if either is missing or
    the file is empty / unreadable.
    """
    p = Path(html_path)
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PostcutContractError(
            f"cannot read root-shell HTML at {p}: {exc}"
        ) from exc
    if not text:
        raise PostcutContractError(f"root-shell HTML is empty: {p}")
    if ROOT_SHELL_MARKER not in text:
        raise PostcutContractError(
            f"root-shell HTML missing {ROOT_SHELL_MARKER!r} marker: {p}"
        )
    if not ROOT_SHELL_LANDMARK_RE.search(text):
        raise PostcutContractError(f"root-shell HTML missing `<main` landmark: {p}")


# ===========================================================================
# #17 — first-party chunk-reference forward integrity
#
# Anchored to Next.js's static export layout:
#   ``/_next/static/chunks/<name>.js``
# where ``<name>`` is alphanumeric + ``_-`` (no dots so traversal
# ``..`` cannot match the canonical shape).
#
# Implementation note: an stdlib ``HTMLParser`` collector extracts
# ``src`` / ``href`` attribute values only. Chunk-shaped substrings
# embedded in comments, inline scripts, CSS strings, or any other
# non-attribute text are ignored — the parser does not scan raw
# body text. Each candidate URL is percent-decoded before segment
# validation so encoded traversal (``%2e%2e/``, ``%2f``) cannot
# bypass the check.
# ===========================================================================


class _ChunkRefCollector(HTMLParser):
    """Collect ``src`` / ``href`` attribute values from HTML.

    Robust across quote styles, malformed input, and CDATA. The
    parser handles comment / script / style boundaries internally,
    so chunk-shaped substrings inside ``<!-- ... -->``,
    ``<script>...</script>``, or ``<style>...</style>`` blocks are
    never reported as attribute URLs.
    """

    # Attributes whose URL value we surface. ``srcset`` is a
    # comma-separated list of descriptors; it is out of scope for
    # the chunk-reference contract.
    _URL_ATTRS = frozenset({"src", "href"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        for name, value in attrs:
            if name in self._URL_ATTRS and value is not None:
                self.urls.append(value)

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        # Self-closing tags like ``<link href="..."/>``.
        self.handle_starttag(tag, attrs)


# A canonical first-party chunk filename is ``<name>.js`` where
# ``<name>`` is alphanumeric + ``_-``. No dots in the name prevent
# canonical acceptance of traversal (``..``); the segment check
# below still detects traversal so we can fail closed explicitly.
CHUNK_FILENAME_RE = re.compile(r"^[A-Za-z0-9_\-]+\.js$")
CHUNK_PATH_PREFIX = "/_next/static/chunks/"


def _is_first_party_root_relative(url: str) -> bool:
    """Return True iff ``url`` is a first-party root-relative URL
    (starts with a single ``/``, not a protocol-relative ``//``
    or any ``scheme://host`` form).
    """
    return url.startswith("/") and not url.startswith("//")


def _validate_first_party_chunk(decoded_url: str) -> str:
    """Validate a decoded first-party chunk URL and return the
    canonical (decoded, query/fragment-stripped) form. Raise
    :class:`PostcutContractError` on any failure.

    The caller has already confirmed the URL is first-party
    root-relative and that the chunk shape matches. This function
    enforces: no query, no fragment, no ``.`` / ``..`` / empty
    path segments, canonical ``<name>``.js`` filename.
    """
    if "?" in decoded_url:
        raise PostcutContractError(
            f"first-party chunk reference has query string: {decoded_url!r}"
        )
    if "#" in decoded_url:
        raise PostcutContractError(
            f"first-party chunk reference has fragment: {decoded_url!r}"
        )
    if not decoded_url.startswith(CHUNK_PATH_PREFIX):
        raise PostcutContractError(
            f"first-party chunk reference must be in "
            f"{CHUNK_PATH_PREFIX!r}: {decoded_url!r}"
        )
    rest = decoded_url[len(CHUNK_PATH_PREFIX) :]
    if not rest:
        raise PostcutContractError(
            f"first-party chunk reference must have a filename: "
            f"{decoded_url!r}"
        )
    segments = rest.split("/")
    if any(seg in (".", "..", "") for seg in segments):
        # Traversal in the percent-decoded form. Encoded
        # ``%2e%2e/`` and ``%2f`` are caught here because the URL
        # is decoded before segment validation.
        raise PostcutContractError(
            f"first-party chunk reference has traversal: {decoded_url!r}"
        )
    final = segments[-1]
    if not CHUNK_FILENAME_RE.fullmatch(final):
        raise PostcutContractError(
            f"first-party chunk reference has invalid filename: "
            f"{decoded_url!r}"
        )
    return decoded_url


def _find_first_party_chunk_references(html_text: str) -> list[str]:
    """Return sorted, deduplicated first-party chunk reference paths
    from ``html_text``.

    The stdlib ``HTMLParser`` is used to inspect only ``src`` /
    ``href`` attribute values; chunk-shaped substrings embedded in
    comments, inline scripts, or any other non-attribute text are
    silently dropped (NOT counted as malformed). Each candidate URL
    is percent-decoded via :func:`urllib.parse.unquote` before
    segment validation, so encoded traversal (``%2e%2e/``,
    ``%2f``) cannot bypass the check.

    Foreign-origin URLs (``https://...``, ``//cdn...``, any
    scheme://host form) are silently ignored. Malformed first-party
    URLs (query, fragment, decoded ``.`` / ``..`` path segments,
    invalid filename) fail closed via :class:`PostcutContractError`.
    """
    parser = _ChunkRefCollector()
    parser.feed(html_text)
    parser.close()

    seen: set[str] = set()
    found_any_chunk_shape = False

    for raw_url in parser.urls:
        # Percent-decode the URL. ``unquote`` leaves plain text
        # alone and decodes ``%2e`` / ``%2f`` so encoded traversal
        # ``%2e%2e/`` is normalized to ``../`` before segment
        # validation. ``unquote`` does not raise on malformed
        # sequences (it leaves them as-is), so a malformed
        # percent-sequence is silently passed through to the
        # segment check (which fails closed because the resulting
        # filename cannot match ``[A-Za-z0-9_-]+\.js``).
        decoded = unquote(raw_url)

        # Foreign-origin detection on the RAW URL — the scheme
        # syntax is never percent-encoded in a way that defeats
        # this check, and the raw URL preserves any malformed
        # ``%`` sequences that ``unquote`` would silently fix.
        if not _is_first_party_root_relative(raw_url):
            continue

        # Chunk shape detection on the DECODED URL — encoded
        # ``%2f`` separators and ``%2e%2e`` segments must not
        # bypass the shape check. The helper only considers
        # root-relative ``/_next/static/chunks/...`` URLs.
        if not decoded.startswith(CHUNK_PATH_PREFIX):
            continue
        rest = decoded[len(CHUNK_PATH_PREFIX) :]
        if not rest:
            continue
        found_any_chunk_shape = True

        canonical = _validate_first_party_chunk(decoded)
        seen.add(canonical)

    if not seen:
        if found_any_chunk_shape:
            raise PostcutContractError(
                "chunk-shaped references present but no valid "
                "first-party chunk reference"
            )
        raise PostcutContractError(
            "no first-party chunk references found in HTML (require >= 1)"
        )
    return sorted(seen)


def verify_chunk_references(html_path: Path, export_root: Path) -> list[str]:
    """Parse first-party root-relative ``/_next/static/chunks/*.js``
    references from the supplied HTML; require at least one
    reference; verify each referenced target resolves inside the
    supplied ``export_root`` to a non-empty file.

    Forward integrity only: do not assert chunk count or an inverse
    "all files referenced" rule. Foreign-origin URLs (``https://...``,
    ``//cdn...``) are ignored. Malformed first-party chunk-shaped
    substrings (query, fragment, traversal) fail closed. Resolved
    paths are confined to ``export_root`` via ``Path.resolve()`` +
    ``Path.relative_to()`` containment to avoid false path escapes.

    Returns the sorted, deduplicated list of validated reference
    paths. Raises :class:`PostcutContractError` on any failure.
    """
    p = Path(html_path)
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PostcutContractError(
            f"cannot read chunk-reference HTML at {p}: {exc}"
        ) from exc
    refs = _find_first_party_chunk_references(text)

    export_root_resolved = Path(export_root).resolve()

    for ref in refs:
        # Resolve the reference against ``export_root``. ``ref`` is
        # always a root-relative path; strip the leading ``/`` so
        # ``Path.joinpath`` does not reset to the filesystem root.
        target = (export_root_resolved / ref.lstrip("/")).resolve()
        try:
            target.relative_to(export_root_resolved)
        except ValueError as exc:
            raise PostcutContractError(
                f"chunk reference escapes export root: {ref} -> {target}"
            ) from exc
        if not target.is_file():
            raise PostcutContractError(f"chunk reference target missing: {ref}")
        if target.stat().st_size <= 0:
            raise PostcutContractError(f"chunk reference target empty: {ref}")

    return refs
