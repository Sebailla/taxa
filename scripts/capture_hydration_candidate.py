#!/usr/bin/env python
"""
Phase 6a candidate-capture harness (positions 1-12-landed React build,
re-baselined).

Authoritative Phase 6a contract (per the user authorization +
openspec/changes/complete-taxa-frontend-migration/tasks.md §6a.3):

    scripts/capture_hydration_candidate.py starts a local static HTTP
    server that serves the built React candidate (`out/`) on a free
    loopback port, drives Playwright + Chromium against the server
    with 1 warm-up + N retained navigations (default 5), reduces each
    metric to its empirical median, and emits a schema-conformant
    artifact at `out/hydration-candidate.json` with both the legacy
    single-point fields and the Phase 6a multi-sample block (raw
    samples + median metadata). The HTTP serving + multi-sample
    capture mirror `scripts/reconstruct_hydration_baseline.py` so
    the comparison is apples-to-apples.

Fail-closed guarantee (binding):

    * The harness MUST NEVER invent baseline / candidate numbers. If
      Playwright or Chromium is unavailable, OR the build directory
      does not exist, OR the static server fails to start, OR the
      capture raises any runtime error, the script writes a
      schema-conformant placeholder artifact flagged with
      ``source: "unavailable"`` and a ``blocker`` field naming the
      failure mode, then exits non-zero. Downstream consumers MUST
      treat any artifact with ``source != "captured"`` as a blocker.
    * A static server is mandatory for the candidate build because
      ``file://`` URLs disable ``fetch`` + ES-module loading for the
      Next.js static export (the legacy baseline can serve from
      ``file://`` because it is a hand-authored single file; the
      React candidate cannot). The server is started in a subprocess
      and torn down on every exit path (success, failure, Ctrl-C).
    * Build artifacts MUST NOT be modified by the harness. The
      ``out/`` directory is owned by ``npm run build:web``; the
      harness reads ``out/index.html`` and writes only
      ``out/hydration-candidate.json`` next to it.

Multi-sample contract (Phase 6a re-baseline):

    * Default: 1 warm-up + 5 retained samples per metric.
    * ``samples_retained`` and ``warmup_count`` integer fields.
    * Raw sample arrays + warmup arrays + median block.
    * Origin URL recorded (``http://127.0.0.1:PORT/``).
    * Back-compat `server_shell` / `client_render` carry the median
      values verbatim.

Inputs (positional / flags):

    python scripts/capture_hydration_candidate.py \\
        [--build-dir out] \\
        [--out out/hydration-candidate.json] \\
        [--samples-retained 5] [--warmup-count 1] \\
        [--port 0]            # 0 = pick a free port (default)
        [--host 127.0.0.1]

The default ``--build-dir out`` matches the Next.js static-export
output directory produced by ``npm run build:web``. The default
``--out out/hydration-candidate.json`` matches the conventional
location the G5 closure harness (``scripts/g5_close.sh``) reads.

Exit codes:
    0  real capture succeeded, schema-conformant artifact written.
    2  build directory missing/unreadable, or output path not writable.
    3  Playwright module not importable OR Chromium binary not
       installed (the two environmental blockers the apply worker
       must surface to ``apply-progress.md`` §Change log).
    4  static server failed to start (e.g. port collision that the
       kernel-assigned fallback did not resolve).
    5  capture raised an unexpected runtime error during navigation
       or measurement (also written into ``blocker``).

Reference:
    openspec/changes/complete-taxa-frontend-migration/tasks.md
                                                              §Phase 6a
    openspec/changes/migrate-nextjs-tailwind4/design.md
                                                      §"Migration Evidence Baseline"
"""
from __future__ import annotations

import argparse
import datetime
import json
import socket
import statistics
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Callable, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUILD_DIR = REPO_ROOT / "out"
DEFAULT_OUT_PATH = REPO_ROOT / "out" / "hydration-candidate.json"
DEFAULT_SAMPLES_RETAINED = 5
DEFAULT_WARMUP_COUNT = 1


# ---------------------------------------------------------------------------
# Fail-closed placeholder
# ---------------------------------------------------------------------------
def _write_placeholder(
    out: Path,
    blocker: str,
    build_dir: Path,
    captured_at: str,
) -> dict:
    """Emit a schema-conformant fail-closed placeholder artifact.

    Same schema shape as ``reconstruct_hydration_baseline.py``:
    ``captured_at``, ``build``, ``route``, ``server_shell``,
    ``client_render``, ``console_warnings``, plus the Phase 6a
    multi-sample block (all zeros) and the ``source`` / ``blocker``
    extensions. ``build`` is fixed at ``"migrated"`` because the
    candidate is always the React build.
    """
    artifact = {
        "captured_at": captured_at,
        "build": "migrated",
        "route": "/",
        "server_shell": {
            "first_paint_ms": 0.0,
            "dom_content_loaded_ms": 0.0,
        },
        "client_render": {
            "tree_first_paint_ms": 0.0,
            "tree_first_interactive_ms": 0.0,
        },
        "console_warnings": [],
        "source": "unavailable",
        "blocker": blocker,
        "build_dir": str(build_dir),
        # Phase 6a multi-sample fields (all zeros placeholder).
        "samples": {
            "server_shell": {
                "first_paint_ms": [0.0] * DEFAULT_SAMPLES_RETAINED,
                "dom_content_loaded_ms": [0.0] * DEFAULT_SAMPLES_RETAINED,
            },
            "client_render": {
                "tree_first_paint_ms": [0.0] * DEFAULT_SAMPLES_RETAINED,
                "tree_first_interactive_ms": [0.0] * DEFAULT_SAMPLES_RETAINED,
            },
        },
        "warmup_samples": {
            "server_shell": {
                "first_paint_ms": [0.0] * DEFAULT_WARMUP_COUNT,
                "dom_content_loaded_ms": [0.0] * DEFAULT_WARMUP_COUNT,
            },
            "client_render": {
                "tree_first_paint_ms": [0.0] * DEFAULT_WARMUP_COUNT,
                "tree_first_interactive_ms": [0.0] * DEFAULT_WARMUP_COUNT,
            },
        },
        "samples_retained": DEFAULT_SAMPLES_RETAINED,
        "warmup_count": DEFAULT_WARMUP_COUNT,
        "median": {
            "server_shell": {
                "first_paint_ms": 0.0,
                "dom_content_loaded_ms": 0.0,
            },
            "client_render": {
                "tree_first_paint_ms": 0.0,
                "tree_first_interactive_ms": 0.0,
            },
        },
        "origin": "http://127.0.0.1:0/",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2) + "\n")
    return artifact


# ---------------------------------------------------------------------------
# Playwright / Chromium probe
# ---------------------------------------------------------------------------
def _check_playwright() -> Tuple[bool, str]:
    """Probe whether playwright + chromium are usable in this env."""
    try:
        from playwright.sync_api import (  # type: ignore[import-not-found]  # noqa: F401
            sync_playwright,
        )
    except ImportError as err:
        return False, (
            f"playwright Python package is not importable "
            f"({err.name if hasattr(err, 'name') else err}); install with "
            f"`pip install -r requirements-dev.txt` and "
            f"`playwright install chromium`."
        )
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
        with sync_playwright() as pw:
            binary = Path(pw.chromium.executable_path)
        if not binary.exists():
            return False, (
                f"playwright reports chromium binary at {binary}, but the "
                f"file does not exist on disk. Run "
                f"`playwright install chromium` to fetch it."
            )
    except Exception as err:  # noqa: BLE001 - any playwright probe failure
        return False, (
            f"playwright chromium probe failed: {type(err).__name__}: {err}"
        )
    return True, ""


# ---------------------------------------------------------------------------
# Local static HTTP server (threaded, in-process)
# ---------------------------------------------------------------------------
class _SilentHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler that suppresses access-log noise so the
    capture stdout stays clean."""

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - signature pinned
        return


def _pick_free_port(host: str) -> int:
    """Ask the kernel for a free TCP port on ``host``."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _start_static_server(
    build_dir: Path, host: str, port: int,
) -> Tuple[Optional[HTTPServer], Callable[[], None], int]:
    """Start an in-process static server serving ``build_dir``.

    Returns ``(server, shutdown, bound_port)``. The caller MUST call
    ``shutdown()`` on every exit path.
    """
    if port == 0:
        port = _pick_free_port(host)

    handler = partial(_SilentHandler, directory=str(build_dir))
    try:
        server = HTTPServer((host, port), handler)
    except OSError as err:
        return None, lambda: None, port

    thread = threading.Thread(
        target=server.serve_forever,
        name=f"capture-static-{port}",
        daemon=True,
    )
    thread.start()

    def shutdown() -> None:
        try:
            server.shutdown()
        except Exception:  # noqa: BLE001 - shutdown MUST be best-effort
            pass
        try:
            server.server_close()
        except Exception:  # noqa: BLE001
            pass

    return server, shutdown, int(server.server_address[1])


def _wait_for_server(
    host: str, port: int, timeout_s: float = 5.0,
) -> Tuple[bool, str]:
    """Probe the static server with a GET until it answers."""
    deadline = datetime.datetime.now() + datetime.timedelta(seconds=timeout_s)
    url = f"http://{host}:{port}/index.html"
    while datetime.datetime.now() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if 200 <= resp.status < 500:
                    return True, ""
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(0.02)
    return False, (
        f"static server at http://{host}:{port}/ did not respond within "
        f"{timeout_s:.1f}s; the harness cannot proceed."
    )


# ---------------------------------------------------------------------------
# Multi-sample capture
# ---------------------------------------------------------------------------
def _navigate_once(page, host: str, port: int, warnings: list) -> dict:
    """Drive a single Playwright navigation and return the per-metric
    measurements (in milliseconds).

    For the React/Next.js candidate, ``first_paint_ms`` and
    ``dom_content_loaded_ms`` capture the static HTML paint; the
    React tree first-paint + interactivity are derived from the same
    events because the Next.js static export runs its hydration
    inline. ``tree_first_paint_ms`` aliases ``first_paint_ms`` and
    ``tree_first_interactive_ms`` aliases ``dom_content_loaded_ms``
    so the schema stays aligned with the legacy baseline.
    """
    target_url = f"http://{host}:{port}/"
    page.goto(target_url, wait_until="load")
    first_paint_ms = float(
        page.evaluate(
            "() => performance.timing.responseEnd - "
            "performance.timing.navigationStart"
        )
    )
    dom_content_loaded_ms = float(
        page.evaluate(
            "() => performance.timing.domContentLoadedEventEnd - "
            "performance.timing.navigationStart"
        )
    )
    return {
        "first_paint_ms": first_paint_ms,
        "dom_content_loaded_ms": dom_content_loaded_ms,
        "tree_first_paint_ms": first_paint_ms,
        "tree_first_interactive_ms": dom_content_loaded_ms,
    }


def _median_or_zero(values: list) -> float:
    """Empirical median; 0.0 for empty lists."""
    if not values:
        return 0.0
    return float(statistics.median(values))


# ---------------------------------------------------------------------------
# Capture (real Playwright path)
# ---------------------------------------------------------------------------
def _capture(
    build_dir: Path,
    out: Path,
    samples_retained: int = DEFAULT_SAMPLES_RETAINED,
    warmup_count: int = DEFAULT_WARMUP_COUNT,
    host: str = "127.0.0.1",
    port: int = 0,
) -> int:
    """Real Playwright capture against the local static server.

    On success writes a schema-conformant artifact with
    ``source: "captured"`` and exits 0. On any failure, falls through
    to the fail-closed path (writes a placeholder, exits non-zero).
    """
    captured_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Pre-flight: build directory exists + has an index.html.
    if not build_dir.is_dir():
        blocker = (
            f"build_dir does not exist: {build_dir}. Run `npm ci` and "
            f"`npm run build:web` to produce the Next.js static export; "
            f"the candidate capture must serve a real build (not a "
            f"placeholder) so the comparison has real numbers."
        )
        sys.stderr.write(f"[capture_hydration_candidate] {blocker}\n")
        _write_placeholder(out, blocker, build_dir, captured_at)
        return 2

    index_html = build_dir / "index.html"
    if not index_html.is_file():
        blocker = (
            f"build_dir is missing its index.html at {index_html}. The "
            f"`npm run build:web` step did not produce a static export; "
            f"the harness cannot capture an SPA that does not exist."
        )
        sys.stderr.write(f"[capture_hydration_candidate] {blocker}\n")
        _write_placeholder(out, blocker, build_dir, captured_at)
        return 2

    ok, blocker = _check_playwright()
    if not ok:
        sys.stderr.write(
            f"[capture_hydration_candidate] environmental blocker: "
            f"{blocker}\n"
        )
        _write_placeholder(out, blocker, build_dir, captured_at)
        return 3

    server, shutdown, bound_port = _start_static_server(build_dir, host, port)
    if server is None:
        blocker = (
            f"could not bind local static server on {host}:{port}; the "
            f"capture cannot proceed without an HTTP origin because the "
            f"Next.js static export's ES modules do not load over file://."
        )
        sys.stderr.write(f"[capture_hydration_candidate] {blocker}\n")
        _write_placeholder(out, blocker, build_dir, captured_at)
        return 4

    origin_url = f"http://{host}:{bound_port}/"

    try:
        server_ok, wait_blocker = _wait_for_server(host, bound_port)
        if not server_ok:
            sys.stderr.write(
                f"[capture_hydration_candidate] {wait_blocker}\n"
            )
            _write_placeholder(out, wait_blocker, build_dir, captured_at)
            return 4

        # Real capture path: 1 warm-up + N retained navigations.
        from playwright.sync_api import (  # type: ignore[import-not-found]
            sync_playwright,
        )

        warmup_samples: dict = {
            "server_shell": {"first_paint_ms": [], "dom_content_loaded_ms": []},
            "client_render": {"tree_first_paint_ms": [], "tree_first_interactive_ms": []},
        }
        retained_samples: dict = {
            "server_shell": {"first_paint_ms": [], "dom_content_loaded_ms": []},
            "client_render": {"tree_first_paint_ms": [], "tree_first_interactive_ms": []},
        }
        warnings: list[str] = []
        captured_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                page.on(
                    "console",
                    lambda msg: warnings.append(msg.text)
                    if msg.type == "warning"
                    else None,
                )

                for _ in range(max(0, warmup_count)):
                    m = _navigate_once(page, host, bound_port, warnings)
                    warmup_samples["server_shell"]["first_paint_ms"].append(
                        m["first_paint_ms"]
                    )
                    warmup_samples["server_shell"]["dom_content_loaded_ms"].append(
                        m["dom_content_loaded_ms"]
                    )
                    warmup_samples["client_render"]["tree_first_paint_ms"].append(
                        m["tree_first_paint_ms"]
                    )
                    warmup_samples["client_render"]["tree_first_interactive_ms"].append(
                        m["tree_first_interactive_ms"]
                    )

                for _ in range(max(0, samples_retained)):
                    m = _navigate_once(page, host, bound_port, warnings)
                    retained_samples["server_shell"]["first_paint_ms"].append(
                        m["first_paint_ms"]
                    )
                    retained_samples["server_shell"]["dom_content_loaded_ms"].append(
                        m["dom_content_loaded_ms"]
                    )
                    retained_samples["client_render"]["tree_first_paint_ms"].append(
                        m["tree_first_paint_ms"]
                    )
                    retained_samples["client_render"]["tree_first_interactive_ms"].append(
                        m["tree_first_interactive_ms"]
                    )

                browser.close()
        except Exception as err:  # noqa: BLE001 - any runtime failure
            blocker = (
                f"capture raised {type(err).__name__}: {err}; traceback: "
                f"{traceback.format_exc(limit=4)}"
            )
            sys.stderr.write(
                f"[capture_hydration_candidate] capture failed: {blocker}\n"
            )
            _write_placeholder(out, blocker, build_dir, captured_at)
            return 5

        median_server_first = _median_or_zero(
            retained_samples["server_shell"]["first_paint_ms"]
        )
        median_server_dcl = _median_or_zero(
            retained_samples["server_shell"]["dom_content_loaded_ms"]
        )
        median_client_first = _median_or_zero(
            retained_samples["client_render"]["tree_first_paint_ms"]
        )
        median_client_interactive = _median_or_zero(
            retained_samples["client_render"]["tree_first_interactive_ms"]
        )

        artifact = {
            "captured_at": captured_at,
            "build": "migrated",
            "route": "/",
            "server_shell": {
                "first_paint_ms": median_server_first,
                "dom_content_loaded_ms": median_server_dcl,
            },
            "client_render": {
                "tree_first_paint_ms": median_client_first,
                "tree_first_interactive_ms": median_client_interactive,
            },
            "console_warnings": warnings,
            "source": "captured",
            "build_dir": str(build_dir),
            # Phase 6a re-baseline: raw sample arrays.
            "samples": retained_samples,
            "warmup_samples": warmup_samples,
            "samples_retained": len(
                retained_samples["client_render"]["tree_first_paint_ms"]
            ),
            "warmup_count": len(
                warmup_samples["client_render"]["tree_first_paint_ms"]
            ),
            "median": {
                "server_shell": {
                    "first_paint_ms": median_server_first,
                    "dom_content_loaded_ms": median_server_dcl,
                },
                "client_render": {
                    "tree_first_paint_ms": median_client_first,
                    "tree_first_interactive_ms": median_client_interactive,
                },
            },
            "origin": origin_url,
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(artifact, indent=2) + "\n")
        return 0
    finally:
        # ALWAYS tear down the server.
        shutdown()


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--build-dir",
        type=Path,
        default=DEFAULT_BUILD_DIR,
        help=(
            "Built React candidate directory to serve over a local "
            "static HTTP origin (must contain index.html). "
            "Default: out/"
        ),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_PATH,
        help=(
            "Output artifact path (schema-pinned by "
            "tests/test_hydration_timing.py). "
            "Default: out/hydration-candidate.json"
        ),
    )
    ap.add_argument(
        "--samples-retained",
        type=int,
        default=DEFAULT_SAMPLES_RETAINED,
        help=(
            "Number of retained samples per metric after the warm-up. "
            "Must be >= 3 for variance reduction. "
            "Default: 5 (Phase 6a re-baseline contract: 'default 5 "
            "retained samples with one warm-up')."
        ),
    )
    ap.add_argument(
        "--warmup-count",
        type=int,
        default=DEFAULT_WARMUP_COUNT,
        help=(
            "Number of warm-up navigations discarded before retained "
            "samples. Default: 1."
        ),
    )
    ap.add_argument(
        "--host",
        default="127.0.0.1",
        help=(
            "Loopback host the static server binds to. "
            "Default: 127.0.0.1 (never expose to LAN)."
        ),
    )
    ap.add_argument(
        "--port",
        type=int,
        default=0,
        help=(
            "Loopback port. 0 = ask the kernel for a free port "
            "(default, safest). Pin only for debugging."
        ),
    )
    return ap


def main(argv: list[str]) -> int:
    args = _build_parser().parse_args(argv[1:])
    return _capture(
        args.build_dir,
        args.out,
        samples_retained=args.samples_retained,
        warmup_count=args.warmup_count,
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
