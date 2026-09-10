#!/usr/bin/env python
"""
Phase 6a candidate-capture harness (G5 1+9 protocol).

Authoritative G5 1+9 contract (per the user authorization +
openspec/changes/complete-taxa-frontend-migration/design.md):

    scripts/capture_hydration_candidate.py starts a local static HTTP
    server that serves the built React candidate (``out/``) on a free
    loopback port, drives Playwright + Chromium against the server with
    1 warm-up + 9 retained navigations (G5 1+9 defaults), measures
    DOMContentLoaded via PerformanceNavigationTiming, reduces the
    retained values to an empirical median, and emits a schema-conformant
    candidate artifact with per-run provenance (browser_version,
    build_sha if available, route, capture timestamp/environment). The
    HTTP serving + multi-sample capture mirror
    ``scripts/reconstruct_hydration_baseline.py`` so the comparison is
    apples-to-apples.

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
      Next.js static export.
    * The fail-closed placeholder MUST honor the configured counts
      (default 9 retained + 1 warm-up). Hardcoding 5+1 (legacy
      multi-metric defaults) is forbidden.

G5 1+9 protocol contract:

    * Default: 1 warm-up + 9 retained DOMContentLoaded samples.
    * Per-run provenance (browser_version, build_sha if available,
      route, captured_at, capture_environment) on every sample.
    * ``median`` is the empirical median of retained
      ``dom_content_loaded_ms`` (warm-up excluded).
    * ``origin`` records the loopback HTTP origin URL.
    * Console warnings are recorded verbatim.

Inputs (positional / flags):

    python scripts/capture_hydration_candidate.py \\
        [--build-dir out] \\
        [--out out/hydration-candidate.json] \\
        [--samples-retained 9] [--warmup-count 1] \\
        [--port 0]            # 0 = pick a free port (default)
        [--host 127.0.0.1]

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
    openspec/changes/complete-taxa-frontend-migration/design.md
                                                       §"G5 — hydration baseline"
    openspec/changes/complete-taxa-frontend-migration/tasks.md
                                                       §Phase 6a
"""
from __future__ import annotations

import argparse
import datetime
import json
import socket
import statistics
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Callable, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUILD_DIR = REPO_ROOT / "out"
DEFAULT_OUT_PATH = REPO_ROOT / "out" / "hydration-candidate.json"

# G5 1+9 protocol defaults — see design.md §"G5 — hydration baseline".
DEFAULT_SAMPLES_RETAINED = 9
DEFAULT_WARMUP_COUNT = 1


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------
def _detect_browser_version(page) -> str:
    """Detect Chromium / browser version via the Playwright page.

    Falls back to ``"unknown"`` if the probe raises any error so the
    capture can stay fail-closed (provenance is recorded, the missing
    value is exposed).
    """
    try:
        return str(page.evaluate("() => navigator.userAgent"))
    except Exception as err:  # noqa: BLE001
        return f"unknown ({type(err).__name__}: {err})"


def _detect_build_sha() -> Optional[str]:
    """Best-effort detection of the current build's git SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            if sha:
                return sha
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass
    return None


def _per_sample(
    dom_content_loaded_ms: float,
    *,
    browser_version: str,
    build_sha: Optional[str],
    route: str,
    captured_at: str,
    capture_environment: str = "controlled-loopback",
) -> dict:
    """Build a single per-run provenance record (G5 1+9 schema)."""
    record = {
        "dom_content_loaded_ms": float(dom_content_loaded_ms),
        "browser_version": browser_version,
        "route": route,
        "captured_at": captured_at,
        "capture_environment": capture_environment,
    }
    if build_sha is not None:
        record["build_sha"] = build_sha
    return record


# ---------------------------------------------------------------------------
# Fail-closed placeholder
# ---------------------------------------------------------------------------
def _write_placeholder(
    out: Path,
    blocker: str,
    build_dir: Path,
    captured_at: str,
    samples_retained: int = DEFAULT_SAMPLES_RETAINED,
    warmup_count: int = DEFAULT_WARMUP_COUNT,
) -> dict:
    """Emit a schema-conformant fail-closed placeholder artifact.

    Honors the configured counts (default 9 retained + 1 warm-up;
    override via ``samples_retained`` / ``warmup_count``). The metrics
    are deliberately zero so a reviewer can tell at a glance that the
    values are placeholders rather than real measurements.
    """
    artifact = {
        "captured_at": captured_at,
        "build": "migrated",
        "route": "/",
        "samples": [
            _per_sample(
                0.0,
                browser_version="unavailable",
                build_sha=_detect_build_sha(),
                route="/",
                captured_at=captured_at,
                capture_environment="unavailable",
            )
            for _ in range(samples_retained)
        ],
        "warmup_samples": [
            _per_sample(
                0.0,
                browser_version="unavailable",
                build_sha=_detect_build_sha(),
                route="/",
                captured_at=captured_at,
                capture_environment="unavailable",
            )
            for _ in range(warmup_count)
        ],
        "samples_retained": samples_retained,
        "warmup_count": warmup_count,
        "median": 0.0,
        "origin": "http://127.0.0.1:0/",
        "console_warnings": [],
        "source": "unavailable",
        "blocker": blocker,
        "build_dir": str(build_dir),
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
        from playwright.sync_api import (  # type: ignore[import-not-found]
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
    except Exception as err:  # noqa: BLE001
        return False, (
            f"playwright chromium probe failed: {type(err).__name__}: {err}"
        )
    return True, ""


# ---------------------------------------------------------------------------
# Local static HTTP server (threaded, in-process)
# ---------------------------------------------------------------------------
class _SilentHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler that suppresses access-log noise."""

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


def _pick_free_port(host: str) -> int:
    """Ask the kernel for a free TCP port on ``host``."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _start_static_server(
    build_dir: Path, host: str, port: int,
) -> Tuple[Optional[HTTPServer], Callable[[], None], int]:
    """Start an in-process static server serving ``build_dir``."""
    if port == 0:
        port = _pick_free_port(host)

    handler = partial(_SilentHandler, directory=str(build_dir))
    try:
        server = HTTPServer((host, port), handler)
    except OSError:
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
        except Exception:  # noqa: BLE001
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
def _navigate_once(page, host: str, port: int) -> float:
    """Drive a single Playwright navigation and return the
    DOMContentLoaded delta in milliseconds.

    Per the G5 1+9 contract, only DOMContentLoaded is measured.
    PerformanceNavigationTiming is preferred (high-resolution); we fall
    back to ``performance.timing.domContentLoadedEventEnd`` for older
    browsers.
    """
    target_url = f"http://{host}:{port}/"
    page.goto(target_url, wait_until="load")
    return float(
        page.evaluate(
            "() => {\n"
            "  const nav = performance.getEntriesByType('navigation')[0];\n"
            "  if (nav && typeof nav.domContentLoadedEventEnd === 'number' "
            "      && typeof nav.startTime === 'number') {\n"
            "    return nav.domContentLoadedEventEnd - nav.startTime;\n"
            "  }\n"
            "  return performance.timing.domContentLoadedEventEnd -\n"
            "         performance.timing.navigationStart;\n"
            "}"
        )
    )


def _median_or_zero(values: List[float]) -> float:
    """Empirical median of a non-empty list of floats; 0.0 for empty."""
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
    """Real Playwright capture against the local static server."""
    captured_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if not build_dir.is_dir():
        blocker = (
            f"build_dir does not exist: {build_dir}. Run `npm ci` and "
            f"`npm run build:web` to produce the Next.js static export; "
            f"the candidate capture must serve a real build (not a "
            f"placeholder) so the comparison has real numbers."
        )
        sys.stderr.write(f"[capture_hydration_candidate] {blocker}\n")
        _write_placeholder(
            out, blocker, build_dir, captured_at,
            samples_retained=samples_retained,
            warmup_count=warmup_count,
        )
        return 2

    index_html = build_dir / "index.html"
    if not index_html.is_file():
        blocker = (
            f"build_dir is missing its index.html at {index_html}. The "
            f"`npm run build:web` step did not produce a static export; "
            f"the harness cannot capture an SPA that does not exist."
        )
        sys.stderr.write(f"[capture_hydration_candidate] {blocker}\n")
        _write_placeholder(
            out, blocker, build_dir, captured_at,
            samples_retained=samples_retained,
            warmup_count=warmup_count,
        )
        return 2

    ok, blocker = _check_playwright()
    if not ok:
        sys.stderr.write(
            f"[capture_hydration_candidate] environmental blocker: "
            f"{blocker}\n"
        )
        _write_placeholder(
            out, blocker, build_dir, captured_at,
            samples_retained=samples_retained,
            warmup_count=warmup_count,
        )
        return 3

    server, shutdown, bound_port = _start_static_server(build_dir, host, port)
    if server is None:
        blocker = (
            f"could not bind local static server on {host}:{port}; the "
            f"capture cannot proceed without an HTTP origin because the "
            f"Next.js static export's ES modules do not load over file://."
        )
        sys.stderr.write(f"[capture_hydration_candidate] {blocker}\n")
        _write_placeholder(
            out, blocker, build_dir, captured_at,
            samples_retained=samples_retained,
            warmup_count=warmup_count,
        )
        return 4

    origin_url = f"http://{host}:{bound_port}/"

    try:
        server_ok, wait_blocker = _wait_for_server(host, bound_port)
        if not server_ok:
            sys.stderr.write(
                f"[capture_hydration_candidate] {wait_blocker}\n"
            )
            _write_placeholder(
                out, wait_blocker, build_dir, captured_at,
                samples_retained=samples_retained,
                warmup_count=warmup_count,
            )
            return 4

        from playwright.sync_api import (  # type: ignore[import-not-found]
            sync_playwright,
        )

        warnings: List[str] = []
        warmup_values: List[float] = []
        retained_values: List[float] = []
        browser_version = "unknown"
        build_sha = _detect_build_sha()
        route = "/"

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                page.on(
                    "console",
                    lambda msg: warnings.append(msg.text)
                    if msg.type == "warning" else None,
                )
                browser_version = _detect_browser_version(page)

                for _ in range(max(0, warmup_count)):
                    warmup_values.append(
                        _navigate_once(page, host, bound_port)
                    )

                for _ in range(max(0, samples_retained)):
                    retained_values.append(
                        _navigate_once(page, host, bound_port)
                    )

                browser.close()
        except Exception as err:  # noqa: BLE001
            blocker = (
                f"capture raised {type(err).__name__}: {err}; traceback: "
                f"{traceback.format_exc(limit=4)}"
            )
            sys.stderr.write(
                f"[capture_hydration_candidate] capture failed: {blocker}\n"
            )
            _write_placeholder(
                out, blocker, build_dir, captured_at,
                samples_retained=samples_retained,
                warmup_count=warmup_count,
            )
            return 5

        median_ms = _median_or_zero(retained_values)
        # Pass provenance fields directly so each parameter receives its
        # own typed expression; building a single kwargs dict would
        # promote the value type to ``str | None`` (because ``build_sha``
        # is legitimately optional) and Pyright would then flag every
        # required ``str`` parameter.
        samples = [
            _per_sample(
                v,
                browser_version=browser_version,
                build_sha=build_sha,
                route=route,
                captured_at=captured_at,
                capture_environment="controlled-loopback",
            )
            for v in retained_values
        ]
        warmup_samples = [
            _per_sample(
                v,
                browser_version=browser_version,
                build_sha=build_sha,
                route=route,
                captured_at=captured_at,
                capture_environment="controlled-loopback",
            )
            for v in warmup_values
        ]

        artifact = {
            "captured_at": captured_at,
            "build": "migrated",
            "route": route,
            "samples": samples,
            "warmup_samples": warmup_samples,
            "samples_retained": len(retained_values),
            "warmup_count": len(warmup_values),
            "median": median_ms,
            "origin": origin_url,
            "console_warnings": warnings,
            "source": "captured",
            "build_dir": str(build_dir),
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
            "Output artifact path. Default: out/hydration-candidate.json"
        ),
    )
    ap.add_argument(
        "--samples-retained",
        type=int,
        default=DEFAULT_SAMPLES_RETAINED,
        help=(
            "Number of retained samples after the warm-up. "
            "Default: 9 (G5 1+9 protocol)."
        ),
    )
    ap.add_argument(
        "--warmup-count",
        type=int,
        default=DEFAULT_WARMUP_COUNT,
        help=(
            "Number of warm-up navigations discarded before retained "
            "samples. Default: 1 (G5 1+9 protocol)."
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


def main(argv: List[str]) -> int:
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