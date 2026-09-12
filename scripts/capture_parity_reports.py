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
from urllib.parse import urlparse

EXIT_OK, EXIT_USAGE, EXIT_BROWSER, EXIT_NO_NAV, EXIT_WRITE = 0, 1, 2, 3, 4
SCHEMA_VERSION = "1.0.0"
ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"


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

def _capture(url: str) -> tuple[list[dict], list[dict]]:
    """Single browser session: walk the page; accumulate (path, status)
    pairs for main-frame documents (navigation) and /api/ (api).
    Cross-origin /api/ calls keep netloc so the comparator can
    disambiguate them from same-origin ones."""
    from playwright.sync_api import sync_playwright

    nav_pairs: dict[tuple[str, int], None] = {}
    api_pairs: dict[tuple[str, int], None] = {}

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

            page.on("response", on_response)
            try:
                page.goto(url, wait_until="networkidle", timeout=20_000)
            except Exception as exc:
                raise RuntimeError(f"navigation failed: {exc!r}") from exc
            try:
                page.wait_for_timeout(500)  # late XHR
            except Exception:
                pass
        finally:
            browser.close()

    nav = [{"path": p, "status": s} for (p, s) in sorted(nav_pairs)]
    api = [{"path": p, "status": s} for (p, s) in sorted(api_pairs)]
    return nav, api

def _write_both(out_dir: Path, nav: list[dict], api: list[dict]) -> None:
    """Atomic dual-write. If the second write fails, the first is removed
    so no partial reports are left on disk."""
    ts = _now_iso()
    nav_doc = {"schema_version": SCHEMA_VERSION, "captured_at": ts, "paths": nav}
    api_doc = {"schema_version": SCHEMA_VERSION, "captured_at": ts, "endpoints": api}
    nav_path = out_dir / "navigation.json"
    api_path = out_dir / "api.json"
    _atomic_write(nav_path, json.dumps(nav_doc, indent=2, sort_keys=True).encode())
    try:
        _atomic_write(api_path, json.dumps(api_doc, indent=2, sort_keys=True).encode())
    except Exception:
        try: nav_path.unlink()
        except OSError: pass
        raise

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capture_parity_reports",
        description="Capture navigation + /api/ responses (one session) "
                    "and emit navigation.json + api.json for verify_parity.py.",
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
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
        nav, api = _capture(args.url)
    except Exception as exc:
        sys.stderr.write(f"[{prog}] capture failed: {exc}\n")
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
        _write_both(out_dir, nav, api)
    except OSError as exc:
        sys.stderr.write(f"[{prog}] write failed: {exc}\n")
        return EXIT_WRITE

    sys.stdout.write(
        f"[{prog}] emitted {len(nav)} navigation + {len(api)} api records "
        f"under {out_dir}\n"
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
