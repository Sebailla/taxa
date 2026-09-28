"""G3 post-cut export contracts — reusable helpers for the future G3
executor against an isolated Next.js candidate export.

Follow-up 33 / Slice B replaces three legacy evidence-baseline
readers with three post-cut structural / export checks:

  #16 ``verify_root_shell(html_path)``
       The supplied HTML file must carry the AppShell
       ``data-app-shell`` marker AND a ``<main`` landmark, based on
       the source-backed surface in
       ``src/modules/app-shell/presentation/AppShell.tsx``.

  #17 ``verify_chunk_references(html_path, export_root)``
       Parse first-party root-relative ``/_next/static/chunks/*.js``
       references from the supplied HTML via the stdlib
       ``html.parser.HTMLParser``; require at least one reference;
       verify each referenced target resolves inside the supplied
       ``export_root`` to a non-empty file. The parser inspects
       only ``src`` / ``href`` attribute values — chunk-shaped
       substrings embedded in comments, inline scripts, or other
       non-attribute text are ignored. Each candidate URL is
       percent-decoded before segment validation so encoded
       traversal (``%2e%2e/``) cannot bypass the check. Forward
       integrity only: do not assert chunk count or an inverse
       "all files referenced" rule. Fail closed for malformed
       first-party URLs (query, fragment, decoded ``.`` / ``..``
       path segments, invalid filename, missing / empty target,
       resolved path escape). Ignore unrelated external /
       non-chunk assets; resolve + contain to avoid false path
       escapes.

  #19 ``verify_build_profile_inventory(export_dir, output_path)``
       Invoke the existing ``scripts/emit_build_profile.mjs``
       against ``export_dir``, writing the profile JSON exactly at
       the explicit ``output_path``. The synthetic tests pin
       ``output_path`` to pytest ``tmp_path``; the future
       ``test_consumer_build_profile_inventory`` node also writes
       to ``tmp_path`` so the export directory is never mutated
       (the profile is observed outside the export). Validate
       non-empty ``chunks`` / ``per_route_bytes``, integer
       non-negative totals/values, and the internal sums:
         ``total_bytes == sum(chunk.bytes) == sum(per_route_bytes.values())``
       Do not invent any size or chunk-count threshold. Any
       subprocess invocation strips ``BUILD_PROFILE_OUT_DIR`` so
       the explicit ``[2]`` argument is the only output
       destination. Two containment guards run BEFORE the emitter
       subprocess and fail closed via :class:`PostcutContractError`
       if the resolved ``output_path`` lies inside (or equals)
       the resolved ``export_dir`` (including symlinks resolving
       into the export tree) or anywhere inside the repo root. The
       intended caller destination is external pytest ``tmp_path``;
       no repo-owned or export-tree path is allowed. A
       JSON-root-object guard rejects profiles whose root is not
       an object (e.g. ``[]``, ``null``) so a malformed profile
       fails closed with :class:`PostcutContractError` instead of
       ``AttributeError``.

The three helpers are wrapped by
``tests/test_g3_postcut_export_contracts.py`` with two layers:

  * ``test_synthetic_*`` — selected by ``pytest -k 'synthetic_'``,
    run now against ``tmp_path`` synthetic inputs.
  * ``test_consumer_*`` — deselected by the same selector (NOT
    skipped), reserved for the future isolated candidate worktree
    that supplies ``Path.cwd()/out``. The ``test_script_exists``
    node is also deselected by the same selector; it is NOT a
    consumer node — it is a self-test that the script exists on
    disk for both the synthetic and the future consumer layers.

#18 (no accepted JavaScript/CSS size budget) and #20 (G5 evidence /
capture authorization unresolved) remain blocked in the manifest.
This module does not introduce them.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

# ---------------------------------------------------------------------------
# Repo root: parent of this file (``scripts/`` lives at the repo root).
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
EMIT_SCRIPT = REPO_ROOT / "scripts" / "emit_build_profile.mjs"


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
    scheme://host form) are silently ignored. The chunk contract
    also has one narrow CSS exception: the Next.js post-cut
    export injects ``/_next/static/chunks/<hash>.css`` via
    ``<link rel="stylesheet">``, which shares the chunk prefix
    but is a stylesheet, not a JS chunk. The exception is
    intentionally narrow — only the ``.css`` extension on the
    query/fragment-stripped base path is silently dropped, so a
    CSS asset with a query parameter
    (``/_next/static/chunks/<hash>.css?v=1``) is also out of
    contract. Every other chunk-shaped reference (``.jsx``,
    ``.map``, ``foo.js/`` with a trailing slash, or any other
    non-``.css`` extension) falls through to
    :func:`_validate_first_party_chunk` and fails closed via the
    existing query / fragment / traversal / invalid-filename /
    empty-segment checks. Malformed first-party JS URLs (query,
    fragment, decoded ``.`` / ``..`` path segments, invalid
    filename) fail closed via :class:`PostcutContractError`.
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

        # Narrow CSS-only exception: silently drop CSS-suffixed
        # stylesheet references. The Next.js post-cut export injects
        # ``/_next/static/chunks/<hash>.css`` via ``<link
        # rel="stylesheet">``; that asset is out of scope for the
        # JS-only chunk contract. Query / fragment is stripped
        # before the extension check so a CSS path with a query
        # parameter (``<hash>.css?v=1``) is also silently dropped.
        # Every other chunk-shaped reference — ``.map``, ``.jsx``,
        # a ``.js`` path with a trailing slash, or any non-``.css``
        # extension — falls through to
        # ``_validate_first_party_chunk`` and fails closed via the
        # existing invalid-filename / empty-segment / query /
        # fragment / traversal checks. The filter is intentionally
        # narrow: it does NOT silently skip malformed ``.js``
        # references.
        base_end = len(decoded)
        for sep in ("?", "#"):
            i = decoded.find(sep)
            if i != -1 and i < base_end:
                base_end = i
        base_path = decoded[:base_end]
        if base_path.endswith(".css"):
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


# ===========================================================================
# #19 — real-export build-profile inventory
#
# Wraps ``scripts/emit_build_profile.mjs``. The emitter walks an
# export directory recursively and writes a JSON profile with
# ``chunks``, ``total_bytes``, and ``per_route_bytes``. The wrapper
# invokes the emitter via ``subprocess.run([node, emit, export,
# output])`` so the explicit output path always wins over
# ``$BUILD_PROFILE_OUT_DIR`` and the repo-root default
# (``web/dist/build-profile.json``). The subprocess environment
# strips ``BUILD_PROFILE_OUT_DIR`` defensively; the profile is then
# re-read from disk and validated.
# ===========================================================================
def _emit_build_profile(
    export_dir: Path, output_path: Path, *, env: dict | None = None
) -> subprocess.CompletedProcess:
    """Run the emitter with explicit args. The caller supplies a
    clean ``env`` if it needs to strip ``BUILD_PROFILE_OUT_DIR``;
    the default keeps the env but the explicit ``[2]`` arg wins
    over the env-derived default inside the emitter (defense in
    depth).
    """
    if not EMIT_SCRIPT.is_file():
        raise PostcutContractError(f"emitter script not found: {EMIT_SCRIPT}")
    argv = ["node", str(EMIT_SCRIPT), str(export_dir), str(output_path)]
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
        env=env if env is not None else None,
        timeout=120,
    )


def _is_inside_or_equal(child: Path, parent: Path) -> bool:
    """Return True iff ``child`` is the same as ``parent`` OR
    resolves inside ``parent`` (after symlink resolution).

    Both inputs are expected to be already-resolved absolute paths;
    callers that have not yet resolved use
    ``Path(child).resolve()`` / ``Path(parent).resolve()`` first.
    ``Path.resolve(strict=False)`` resolves non-existent paths
    lexically and follows symlinks for existing components so the
    containment check is observable before any filesystem
    operation runs.
    """
    if child == parent:
        return True
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def verify_build_profile_inventory(export_dir: Path, output_path: Path) -> dict:
    """Invoke ``scripts/emit_build_profile.mjs`` against
    ``export_dir``, writing the profile JSON exactly at the explicit
    ``output_path``. The synthetic tests pin ``output_path`` to
    pytest ``tmp_path``; the future ``test_consumer_build_profile_inventory``
    node also writes to ``tmp_path`` so the export directory is
    never mutated. Validate non-empty ``chunks`` / ``per_route_bytes``,
    integer non-negative totals/values, and the internal sums:

        total_bytes == sum(chunk.bytes) == sum(per_route_bytes.values())

    Do not invent any size or chunk-count threshold. The subprocess
    environment strips ``BUILD_PROFILE_OUT_DIR`` so the explicit
    output argument is the only output destination.

    Containment guards (run BEFORE ``_emit_build_profile``):

      (i) The resolved ``output_path`` must NOT lie inside (or
          equal) the resolved ``export_dir``. ``Path.resolve()``
          follows symlinks for existing components; a symlink
          that resolves into the export tree is rejected too.
          The intended caller destination is external pytest
          ``tmp_path``; writing the profile into the export
          directory would mutate the candidate tree and
          contaminate the inventory surface.
      (ii) The resolved ``output_path`` must NOT lie anywhere
          inside the repo root. No repo-owned path is permitted
          for the profile. The prior ``web/dist/build-profile.json``
          collision check is subsumed by this stronger guard
          (any repo-owned path is rejected, not only the
          emitter's default destination).

    A JSON-root-object guard rejects profiles whose root is not an
    object (e.g. ``[]``, ``null``) so a malformed profile fails
    closed with :class:`PostcutContractError` instead of
    ``AttributeError`.

    Returns the validated profile dict. Raises
    :class:`PostcutContractError` on containment violation,
    subprocess failure, or invalid profile.
    """
    export_dir_resolved = Path(export_dir).resolve()
    output_path_resolved = Path(output_path).resolve()

    # Containment guard (i): ``output_path`` must not land inside
    # (or equal) the export tree. ``Path.resolve()`` follows
    # symlinks for existing components; non-existent paths resolve
    # lexically via ``strict=False``. The emitter's default output
    # is ``web/dist/build-profile.json`` (under REPO_ROOT, not
    # under export_dir), but a future caller might still pass an
    # ``output_path`` inside the export; we reject it before any
    # subprocess can write to disk.
    if _is_inside_or_equal(output_path_resolved, export_dir_resolved):
        raise PostcutContractError(
            f"output_path is inside export_dir; profile must be "
            f"written outside the export tree (use pytest tmp_path): "
            f"output_path={output_path}, export_dir={export_dir}"
        )

    # Containment guard (ii): ``output_path`` must not land
    # anywhere inside the repo root. The prior
    # ``web/dist/build-profile.json`` collision check is subsumed
    # by this stronger guard (any repo-owned path is rejected,
    # not only the emitter's default destination).
    if _is_inside_or_equal(output_path_resolved, REPO_ROOT):
        raise PostcutContractError(
            f"output_path is inside repo root; profile must be "
            f"written outside the repo (use pytest tmp_path): "
            f"output_path={output_path}, repo_root={REPO_ROOT}"
        )

    # Strip ``BUILD_PROFILE_OUT_DIR`` from the subprocess env so
    # the emitter cannot route output through the env override.
    # The emitter's explicit ``[2]`` arg would still win when both
    # are present, but stripping the env keeps the contract surface
    # explicit and observable.
    env = {k: v for k, v in os.environ.items() if k != "BUILD_PROFILE_OUT_DIR"}

    proc = _emit_build_profile(export_dir_resolved, output_path_resolved, env=env)
    if proc.returncode != 0:
        raise PostcutContractError(
            f"emit_build_profile.mjs exited {proc.returncode}; stderr={proc.stderr!r}"
        )
    if not output_path_resolved.is_file():
        raise PostcutContractError(
            f"profile not written at explicit output path: {output_path_resolved}"
        )

    try:
        profile = json.loads(output_path_resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PostcutContractError(
            f"cannot read profile JSON at {output_path_resolved}: {exc}"
        ) from exc

    # JSON-root-object guard. ``profile.get(...)`` would raise
    # ``AttributeError`` on a list / null / int / string root; the
    # contract surface requires a fail-closed
    # :class:`PostcutContractError` instead.
    if not isinstance(profile, dict):
        raise PostcutContractError(
            f"profile JSON root must be an object, got "
            f"{type(profile).__name__}: "
            f"{output_path_resolved.read_text(encoding='utf-8')[:200]!r}"
        )

    # ---- internal-sums validation (no size / count threshold) ----
    chunks = profile.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise PostcutContractError("profile.chunks must be a non-empty list")
    for c in chunks:
        if not isinstance(c, dict):
            raise PostcutContractError(f"profile.chunks entry must be an object: {c!r}")
        b = c.get("bytes")
        if not isinstance(b, int) or isinstance(b, bool) or b < 0:
            raise PostcutContractError(
                f"profile.chunks[].bytes must be non-negative int: {c!r}"
            )
        if not isinstance(c.get("path"), str):
            raise PostcutContractError(f"profile.chunks[].path must be string: {c!r}")

    total = profile.get("total_bytes")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        raise PostcutContractError("profile.total_bytes must be non-negative int")

    per_route = profile.get("per_route_bytes")
    if not isinstance(per_route, dict) or not per_route:
        raise PostcutContractError("profile.per_route_bytes must be a non-empty object")
    for route, val in per_route.items():
        if not isinstance(route, str):
            raise PostcutContractError(
                f"profile.per_route_bytes key must be string: {route!r}"
            )
        if not isinstance(val, int) or isinstance(val, bool) or val < 0:
            raise PostcutContractError(
                f"profile.per_route_bytes[{route!r}] must be "
                f"non-negative int: {val!r}"
            )

    chunk_sum = sum(c["bytes"] for c in chunks)
    per_route_sum = sum(per_route.values())
    if total != chunk_sum:
        raise PostcutContractError(
            f"profile.total_bytes ({total}) != sum(chunk.bytes) ({chunk_sum})"
        )
    if total != per_route_sum:
        raise PostcutContractError(
            f"profile.total_bytes ({total}) != "
            f"sum(per_route_bytes.values()) ({per_route_sum})"
        )

    return profile
