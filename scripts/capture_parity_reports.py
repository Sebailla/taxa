#!/usr/bin/env python
"""G4 producer — combined navigation + /api/ capture (PR3d slice).

Opens one Playwright session against --url, records every main-frame
document response into navigation.json and every /api/ response into
api.json, atomically emitting both so the output exactly satisfies the
verify_parity.py schema (schema_version="1.0.0", captured_at=ISO-8601 UTC).
CLI: --url <url> --out-dir <dir>. Exit codes: 0 ok, 1 usage, 2 browser,
3 zero navigation, 4 write. Reference: design.md §3.3.4 (G4).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

EXIT_OK, EXIT_USAGE, EXIT_BROWSER, EXIT_NO_NAV, EXIT_WRITE, EXIT_QUERY = 0, 1, 2, 3, 4, 5
SCHEMA_VERSION = "1.0.0"
ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"
# JSON field names tried in order when extracting a result_count from an
# /api/search response body. Last-resort fallbacks are the lengths of common
# list fields. None of these match => fail-closed search capture.
_SEARCH_COUNT_KEYS = ("count", "total", "result_count")
_SEARCH_LIST_KEYS = ("results", "data", "items", "hits")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime(ISO_FMT)

def _atomic_write(path: Path, body: bytes) -> None:
    """Atomic write: temp file + ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        os.write(fd, body); os.close(fd); os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise

def _is_api(path: str) -> bool:
    return "/api/" in path


def _search_match_idx(rurl: str, queries: list[str]) -> int | None:
    """Return the index of the user query whose value equals the parsed
    ``q`` parameter of ``rurl``, or None when no exact match exists. Both
    sides are normalized via URL encoding/decoding so spaces, ``&``, etc.
    round-trip correctly without falling back to substring matching."""
    parsed = urlparse(rurl)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    captured = qs.get("q", [])
    for i, q in enumerate(queries):
        # Canonicalize the user query for the comparison (parse_qs already
        # URL-decodes the captured side).
        if q in captured or quote(q, safe="") in [
            quote(c, safe="") for c in captured
        ]:
            return i
    return None


def _search_count_from_body(body: bytes) -> int | None:
    """Best-effort extraction of an integer result_count from an /api/search
    JSON body. Looks for an integer field (``count``, ``total``,
    ``result_count``) then for the length of a common list field
    (``results``, ``data``, ``items``, ``hits``). Returns None when nothing
    matches — callers must fail closed."""
    try:
        obj = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(obj, dict):
        return None
    for key in _SEARCH_COUNT_KEYS:
        v = obj.get(key)
        if isinstance(v, int) and not isinstance(v, bool):
            return v
    for key in _SEARCH_LIST_KEYS:
        v = obj.get(key)
        if isinstance(v, list):
            return len(v)
    return None

def _capture(url: str, queries: list[str]) -> tuple[list[dict], list[dict], list[dict]]:
    """Single browser session: walk the page; accumulate (path, status)
    pairs for main-frame documents (navigation) and /api/ (api).
    Cross-origin /api/ calls keep netloc so the comparator can
    disambiguate them from same-origin ones. When ``queries`` is non-empty,
    additionally read each /api/ response body, match the parsed ``q``
    parameter against the user queries, and return ``[{query, result_count}]``
    in user order; missing matches raise RuntimeError (fail-closed)."""
    from playwright.sync_api import sync_playwright

    nav_pairs: dict[tuple[str, int], None] = {}
    api_pairs: dict[tuple[str, int], None] = {}
    # (rurl, response) for every /api/ response — needed to read bodies for
    # search matching AFTER the navigation settles (response.body() is safe
    # post-navigation; doing it inside the response handler is racy).
    api_responses: list[tuple[str, object]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            base_parsed = urlparse(url)

            def on_response(response):
                try:
                    status = response.status
                    rurl = response.url
                except Exception:
                    return
                parsed = urlparse(rurl)
                rpath = parsed.path or "/"
                if (response.request.resource_type == "document"
                        and response.frame is page.main_frame):
                    nav_pairs[(rpath, status)] = None
                if not _is_api(rpath):
                    return
                if parsed.netloc and parsed.netloc != base_parsed.netloc:
                    api_pairs[(f"{parsed.netloc}{rpath}", status)] = None
                else:
                    api_pairs[(rpath, status)] = None
                # Keep the FULL rurl (with query string) for search matching —
                # rpath alone strips the ?q=… we need to match against.
                api_responses.append((rurl, response))

            page.on("response", on_response)
            try:
                page.goto(url, wait_until="networkidle", timeout=20_000)
            except Exception as exc:
                raise RuntimeError(f"navigation failed: {exc!r}") from exc
            try:
                page.wait_for_timeout(500)  # late XHR
            except Exception:
                pass
            # Read /api/ response bodies for search matching WHILE the browser
            # is still open — response.body() requires a live browser context.
            # On search-mismatch RuntimeError the finally below still closes
            # the browser cleanly.
            search = _collect_search(api_responses, queries)
        finally:
            browser.close()

    nav = [{"path": p, "status": s} for (p, s) in sorted(nav_pairs)]
    api = [{"path": p, "status": s} for (p, s) in sorted(api_pairs)]
    return nav, api, search


def _collect_search(api_responses: list[tuple[str, object]],
                    queries: list[str]) -> list[dict]:
    """Match each user query against the parsed ``q`` parameter of every
    captured /api/ response, extract result_count from the body, and
    return ``[{query, result_count}]`` in user order. Fails closed (raises
    RuntimeError) when any user query has no exact match — caller's atomic
    write layer must then skip all three reports. Returns [] when queries
    is empty (PR #223 behavior preserved)."""
    if not queries:
        return []
    counts: dict[str, int] = {}
    seen_query_value: set[str] = set()
    for rurl, response in api_responses:
        idx = _search_match_idx(rurl, queries)
        if idx is None:
            continue
        q = queries[idx]
        if q in seen_query_value:
            continue  # de-dupe duplicate user queries on the same value
        try:
            body = response.body()  # type: ignore[attr-defined]
        except Exception:
            continue
        if not isinstance(body, (bytes, bytearray)):
            continue
        count = _search_count_from_body(bytes(body))
        if count is None:
            continue
        counts[q] = count
        seen_query_value.add(q)
    missing = [q for q in queries if q not in counts]
    if missing:
        raise RuntimeError(
            f"search queries without /api/ match: {missing!r}")
    return [{"query": q, "result_count": counts[q]} for q in queries]

def _write_all(out_dir: Path, nav: list[dict], api: list[dict],
               search: list[dict]) -> None:
    """Atomic multi-report write. Emits navigation.json + api.json always;
    additionally emits search.json when ``search`` is non-empty (i.e.,
    --queries was provided). If any write fails, every previously-written
    report is removed so no partial report set is left on disk."""
    ts = _now_iso()
    nav_doc = {"schema_version": SCHEMA_VERSION, "captured_at": ts, "paths": nav}
    api_doc = {"schema_version": SCHEMA_VERSION, "captured_at": ts, "endpoints": api}
    nav_path = out_dir / "navigation.json"
    api_path = out_dir / "api.json"
    search_path = out_dir / "search.json" if search else None
    written: list[Path] = []
    try:
        _atomic_write(nav_path,
                      json.dumps(nav_doc, indent=2, sort_keys=True).encode())
        written.append(nav_path)
        _atomic_write(api_path,
                      json.dumps(api_doc, indent=2, sort_keys=True).encode())
        written.append(api_path)
        if search_path is not None:
            search_doc = {"schema_version": SCHEMA_VERSION,
                          "captured_at": ts, "queries": search}
            _atomic_write(search_path,
                          json.dumps(search_doc, indent=2, sort_keys=True).encode())
            written.append(search_path)
    except Exception:
        for p in written:
            try: p.unlink()
            except OSError: pass
        raise

def _build_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="capture_parity_reports",
            description="Capture navigation + /api/ responses (one session) "
                        "and emit navigation.json + api.json for verify_parity.py. "
                        "When --queries is provided, additionally emit search.json "
                        "with each query's parsed /api/ result_count.",
        )
        parser.add_argument("--url", required=True)
        parser.add_argument("--out-dir", required=True, type=Path)
        parser.add_argument("--queries", nargs="+", default=[],
                            help="optional space-separated list of search "
                                 "queries; each must match an /api/ response "
                                 "by exact parsed-q parameter (URL-encoded). "
                                 "When provided, search.json is emitted; when "
                                 "omitted, PR #223 behavior is preserved exactly.")
        return parser

def main(argv: list[str]) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as err:
        if isinstance(err.code, int) and err.code != 0:
            sys.stderr.write("usage: capture_parity_reports.py "
                             "--url <url> --out-dir <dir>\n")
            return EXIT_USAGE
        return EXIT_OK

    prog = "capture_parity_reports"
    try:
        nav, api, search = _capture(args.url, args.queries)
    except Exception as exc:
        sys.stderr.write(f"[{prog}] capture failed: {exc}\n")
        # Search mismatch is a distinct failure mode from generic capture
        # failure: the browser worked but a user-supplied query had no
        # /api/ response — surface that as a dedicated exit code so callers
        # can distinguish the two without parsing stderr.
        if args.queries and "search queries without" in str(exc):
            return EXIT_QUERY
        return EXIT_BROWSER

    if not nav:
        sys.stderr.write(f"[{prog}] zero navigation captured for {args.url}\n")
        return EXIT_NO_NAV

    out_dir: Path = args.out_dir
    if out_dir.exists() and not out_dir.is_dir():
        sys.stderr.write(f"[{prog}] out-dir is not a directory: {out_dir}\n")
        return EXIT_WRITE
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_all(out_dir, nav, api, search)
    except OSError as exc:
        sys.stderr.write(f"[{prog}] write failed: {exc}\n")
        return EXIT_WRITE

    sys.stdout.write(
        f"[{prog}] emitted {len(nav)} navigation + {len(api)} api records"
        + (f" + {len(search)} search queries" if search else "")
        + f" under {out_dir}\n"
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
