#!/usr/bin/env python
"""
Phase 6a hydration-baseline reconstruction harness (re-baselined).

Authoritative Phase 6a contract (per the user authorization +
openspec/changes/complete-taxa-frontend-migration/tasks.md):

    scripts/reconstruct_hydration_baseline.py starts a local static
    HTTP server that serves the FROZEN
    `tools/g3-legacy-fixture/web/` on a free loopback port, drives
    Playwright + Chromium against the server (1 warm-up + N retained
    navigations), reduces each metric to its empirical median, and
    emits a schema-conformant baseline artifact at
    `web/dist/evidence-baseline.json` with both the legacy single-
    point fields and the Phase 6a multi-sample block
    (raw samples + median metadata). The HTTP serving mirrors
    `scripts/capture_hydration_candidate.py` so the comparison is
    apples-to-apples (file:// navigation is forbidden because it
    disables fetch + ES-module loading for the React build's static
    export; the legacy baseline now uses the same loopback HTTP
    origin so neither leg has an unfair advantage).

Fail-closed guarantee (binding):

    * The harness MUST NEVER invent baseline numbers. If Playwright or
      Chromium is unavailable, the script writes a schema-conformant
      placeholder artifact flagged with `source: "unavailable"` and
      exits non-zero. The placeholder's metrics are deliberately zero
      so any downstream consumer can tell at a glance that the values
      are placeholders rather than real measurements.
    * A `blocker` field names the missing dependency so the apply
      worker can record the environmental reason in
      `apply-progress.md` without guessing.

Multi-sample contract (Phase 6a re-baseline):

    * Default: 1 warm-up + 5 retained samples per metric.
    * The retained samples block (`samples.*`) holds the raw observed
      values for each metric.
    * The warmup_samples block holds the discarded warm-up samples.
    * The `median` block holds the empirical median of the retained
      samples per metric.
    * `samples_retained` and `warmup_count` are integer counts.
    * The legacy back-compat `server_shell` / `client_render` blocks
      carry the median values verbatim so consumers that don't yet
      understand the multi-sample schema keep working.

Inputs (positional / flags):

    python scripts/reconstruct_hydration_baseline.py \\
        [--fixture-web-root tools/g3-legacy-fixture/web] \\
        [--out web/dist/evidence-baseline.json] \\
        [--samples-retained 5] [--warmup-count 1] \\
        [--host 127.0.0.1] [--port 0]

The frozen fixture root is the default; the flag exists so a developer
who wants to capture against a different legacy build can override it
without editing the script. The fixture path is validated to exist
before any capture attempt — a missing fixture root is also a
fail-closed blocker (the fixture is read-only per the Phase 6a spec).

Exit codes:
    0  real capture succeeded, schema-conformant artifact written.
    2  fixture root or output directory missing/unwritable.
    3  Playwright module not importable OR Chromium binary not
       installed (the two environmental blockers the apply worker
       must surface to apply-progress.md §Change log).
    4  static server failed to start, or capture raised an unexpected
       runtime error during navigation or measurement (also written
       into `blocker`).

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
DEFAULT_FIXTURE_WEB_ROOT = REPO_ROOT / "tools" / "g3-legacy-fixture" / "web"
DEFAULT_OUT_PATH = REPO_ROOT / "web" / "dist" / "evidence-baseline.json"
DEFAULT_SAMPLES_RETAINED = 5
DEFAULT_WARMUP_COUNT = 1


# ---------------------------------------------------------------------------
# Fail-closed placeholder
# ---------------------------------------------------------------------------
def _write_placeholder(
    out: Path,
    blocker: str,
    fixture_web_root: Path,
    captured_at: str,
) -> dict:
    """Emit a schema-conformant fail-closed placeholder artifact.

    The schema follows ``tests/test_hydration_timing.py`` (captured_at,
    build, route, server_shell, client_render, console_warnings) plus
    the Phase 6a multi-sample block (all zeros so a reviewer can tell
    at a glance that the values are placeholders rather than real
    measurements). Two extensions identify the placeholder:
    ``source`` (set to ``"unavailable"``) and ``blocker`` (a human-
    readable diagnostic).
    """
    artifact = {
        "captured_at": captured_at,
        "build": "legacy",
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
        "fixture_web_root": str(fixture_web_root),
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
    """Probe whether playwright + chromium are usable in this env.

    Returns ``(ok, blocker_message)``. ``ok=False`` implies the harness
    must take the fail-closed path; the message is suitable for
    writing into the placeholder's ``blocker`` field and stderr.
    """
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
# In-process loopback HTTP server (serves the frozen fixture)
# ---------------------------------------------------------------------------
class _SilentHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler that suppresses access-log noise so a
    reviewer reading the harness output sees only the artifact path,
    not dozens of GET lines."""

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


def _pick_free_port(host: str) -> int:
    """Ask the kernel for a free TCP port on ``host``."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _start_static_server(
    serve_root: Path, host: str, port: int,
) -> Tuple[Optional[HTTPServer], Callable[[], None], int]:
    """Start an in-process static server serving ``serve_root``.

    Returns ``(server, shutdown, bound_port)``. The caller MUST call
    ``shutdown()`` on every exit path so the listening socket is
    released before the Python process exits.
    """
    if port == 0:
        port = _pick_free_port(host)

    handler = partial(_SilentHandler, directory=str(serve_root))
    try:
        server = HTTPServer((host, port), handler)
    except OSError as err:
        return None, lambda: None, port

    thread = threading.Thread(
        target=server.serve_forever,
        name=f"reconstruct-static-{port}",
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
    """Probe the static server with a HEAD-equivalent GET until it
    answers. Returns ``(ok, blocker)``."""
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
    measurements (in milliseconds) plus the running warnings list.

    Returns a dict like
    ``{"first_paint_ms": ..., "dom_content_loaded_ms": ...,
       "tree_first_paint_ms": ..., "tree_first_interactive_ms": ...}``.

    The legacy fixture has no React tree or interactive handlers, so
    ``tree_first_paint_ms`` and ``first_paint_ms`` collapse to the
    same value (the static body paint); the same applies to
    ``tree_first_interactive_ms`` and ``dom_content_loaded_ms``. The
    distinction is preserved so the legacy schema stays comparable to
    the React candidate's schema.
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
    """Empirical median of a non-empty list of floats; 0.0 for empty.

    statistics.median returns the average of the two middle values
    for even-length lists, which matches the ``median(samples)``
    contract in the multi-sample schema.
    """
    if not values:
        return 0.0
    return float(statistics.median(values))


def _capture(
    fixture_web_root: Path,
    out: Path,
    samples_retained: int = DEFAULT_SAMPLES_RETAINED,
    warmup_count: int = DEFAULT_WARMUP_COUNT,
    host: str = "127.0.0.1",
    port: int = 0,
) -> int:
    """Attempt a real Playwright capture against ``fixture_web_root``.

    The capture serves the fixture over a loopback HTTP server (so the
    baseline mirrors the React candidate's HTTP origin), runs
    ``warmup_count + samples_retained`` navigations, discards the
    warm-up, reduces the retained samples to a per-metric median, and
    writes a schema-conformant artifact with both the legacy single-
    point fields (set to the median) and the Phase 6a multi-sample
    block (raw samples + warmup + median metadata + origin URL).

    On any failure, the script writes a placeholder artifact and exits
    non-zero — it MUST NEVER invent baseline numbers.
    """
    captured_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Pre-flight checks (fail-closed before spinning up the server)
    # ------------------------------------------------------------------
    if not fixture_web_root.is_dir():
        blocker = (
            f"fixture_web_root does not exist: {fixture_web_root} "
            f"(the G3 legacy fixture is read-only per Phase 6a spec)"
        )
        sys.stderr.write(f"[reconstruct_hydration_baseline] {blocker}\n")
        _write_placeholder(
            out, blocker, fixture_web_root, captured_at,
        )
        return 2

    index_html = fixture_web_root / "index.html"
    if not index_html.is_file():
        blocker = (
            f"fixture_web_root is missing its index.html at "
            f"{index_html}; the legacy baseline requires the frozen "
            f"G3 fixture to be byte-identical."
        )
        sys.stderr.write(f"[reconstruct_hydration_baseline] {blocker}\n")
        _write_placeholder(
            out, blocker, fixture_web_root, captured_at,
        )
        return 2

    ok, blocker = _check_playwright()
    if not ok:
        sys.stderr.write(
            f"[reconstruct_hydration_baseline] environmental blocker: "
            f"{blocker}\n"
        )
        _write_placeholder(
            out, blocker, fixture_web_root, captured_at,
        )
        return 3

    # ------------------------------------------------------------------
    # Start loopback static HTTP server
    # ------------------------------------------------------------------
    server, shutdown, bound_port = _start_static_server(
        fixture_web_root, host, port,
    )
    if server is None:
        blocker = (
            f"could not bind local static server on {host}:{port}; the "
            f"capture cannot proceed without an HTTP origin (file:// "
            f"navigation is forbidden because it would diverge from the "
            f"candidate's HTTP origin contract)."
        )
        sys.stderr.write(f"[reconstruct_hydration_baseline] {blocker}\n")
        _write_placeholder(
            out, blocker, fixture_web_root, captured_at,
        )
        return 4

    origin_url = f"http://{host}:{bound_port}/"

    try:
        server_ok, wait_blocker = _wait_for_server(host, bound_port)
        if not server_ok:
            sys.stderr.write(
                f"[reconstruct_hydration_baseline] {wait_blocker}\n"
            )
            _write_placeholder(
                out, wait_blocker, fixture_web_root, captured_at,
            )
            return 4

        # ------------------------------------------------------------------
        # Real capture: 1 warm-up + N retained navigations
        # ------------------------------------------------------------------
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

                # Warm-up navigations (discarded).
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

                # Retained navigations (the canonical samples).
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
                f"[reconstruct_hydration_baseline] capture failed: {blocker}\n"
            )
            _write_placeholder(
                out, blocker, fixture_web_root, captured_at,
            )
            return 4

        # ------------------------------------------------------------------
        # Reduce to median + emit artifact
        # ------------------------------------------------------------------
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
            "build": "legacy",
            "route": "/",
            # Legacy back-compat single-point fields (== median).
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
            "fixture_web_root": str(fixture_web_root),
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
        # ALWAYS tear down the server — success, failure, exception —
        # so a leftover listener never blocks the next capture.
        shutdown()


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--fixture-web-root",
        type=Path,
        default=DEFAULT_FIXTURE_WEB_ROOT,
        help=(
            "Frozen legacy fixture web root to capture against. "
            "Default: tools/g3-legacy-fixture/web/"
        ),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_PATH,
        help=(
            "Output artifact path (schema-pinned by "
            "tests/test_hydration_timing.py). Default: "
            "web/dist/evidence-baseline.json"
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
        args.fixture_web_root,
        args.out,
        samples_retained=args.samples_retained,
        warmup_count=args.warmup_count,
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
