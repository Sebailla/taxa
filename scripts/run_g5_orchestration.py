#!/usr/bin/env python
"""G5 legacy-orchestration CLI — Slice 12 (adapted from ``7f01b9a``).

Composes ``scripts.orchestrate_g5_legacy.run_orchestration`` with fully
injectable seam factories (lifecycle, collector, bridge, planner,
publisher). Slice 12 adapts commit ``7f01b9a``'s Slice 1 onto the current
state where Slices 10–11 already ship the controlled legacy lifecycle +
orchestration entry + default raw-Lighthouse bridge. The original Slice 1
deferred non-dry-run invocation; Slice 12 fulfills that branch.

Contract:
  * ``--dry-run``: parse + validate + one-line summary, exit 0
    WITHOUT invoking any seam factory or ``run_orchestration``.
  * (default): build defaults via ``build_default_seams(args)`` and call
    ``run_orchestration``.

Exit codes: 0 success, 1 usage, 2 validation, 3 runtime error.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts import orchestrate_g5_legacy as og
from scripts import capture_hydration as ch


# ── exit-code contract ──────────────────────────────────────────────────
EXIT_OK, EXIT_USAGE, EXIT_VALIDATION, EXIT_RUNTIME = 0, 1, 2, 3


# ── argparse defaults (sourced from Child B) ────────────────────────────
DEFAULT_HOST = og.DEFAULT_HOST
DEFAULT_PORT = 8765
DEFAULT_HEALTH_PATH = og.DEFAULT_HEALTH_PATH
DEFAULT_HEALTH_TIMEOUT_S = og.DEFAULT_HEALTH_TIMEOUT_S
DEFAULT_HEALTH_INTERVAL_S = og.DEFAULT_HEALTH_INTERVAL_S
DEFAULT_TERMINATE_GRACE_S = og.DEFAULT_TERMINATE_GRACE_S
DEFAULT_ITERATIONS = og.ITERATIONS
DEFAULT_DOM_MARKER_SELECTOR = og.DEFAULT_DOM_MARKER_SELECTOR


def _default_cwd() -> Path:
    return og.REPO_ROOT


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="run_g5_orchestration.py",
        description="G5 legacy-orchestration CLI. Composes "
                    "scripts.orchestrate_g5_legacy.run_orchestration with "
                    "fully injectable seams; --dry-run stops at parse+validate.")
    p.add_argument("--target-url", required=True,
                   help="Controlled legacy FastAPI URL (http:// or https://)")
    p.add_argument("--out", required=True,
                   help="Output dir for atomic evidence publication")
    p.add_argument("--host", default=DEFAULT_HOST,
                   help=f"Legacy ASGI bind host (default {DEFAULT_HOST})")
    p.add_argument("--port", type=int, default=DEFAULT_PORT,
                   help=f"Legacy ASGI bind port (default {DEFAULT_PORT})")
    p.add_argument("--cwd", default=None,
                   help=f"uvicorn spawn cwd (default {_default_cwd()})")
    p.add_argument("--health-path", default=DEFAULT_HEALTH_PATH,
                   help=f"Health probe path (default {DEFAULT_HEALTH_PATH})")
    p.add_argument("--health-timeout-s", type=float,
                   default=DEFAULT_HEALTH_TIMEOUT_S, help="Health timeout (s)")
    p.add_argument("--health-interval-s", type=float,
                   default=DEFAULT_HEALTH_INTERVAL_S, help="Health interval (s)")
    p.add_argument("--terminate-grace-s", type=float,
                   default=DEFAULT_TERMINATE_GRACE_S, help="SIGTERM→SIGKILL grace (s)")
    p.add_argument("--bridge-script", default=None,
                   help=f"Override default bridge (default {og.DEFAULT_BRIDGE_SCRIPT})")
    p.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS,
                   help=f"Must equal {DEFAULT_ITERATIONS} (G5 contract)")
    p.add_argument("--dom-marker-selector", default=DEFAULT_DOM_MARKER_SELECTOR,
                   help="DOM-marker selector for capture readiness wait")
    p.add_argument("--no-headless", action="store_true",
                   help="Headed browser mode (debug only)")
    p.add_argument("--dry-run", action="store_true",
                   help="Parse+validate only; do not invoke run_orchestration")
    return p


def _validate_args(args: argparse.Namespace) -> str | None:
    if not (isinstance(args.target_url, str)
            and args.target_url.startswith(("http://", "https://"))):
        return f"--target-url must start with http:// or https://; got {args.target_url!r}"
    if not isinstance(args.port, int) or not (1 <= args.port <= 65535):
        return f"--port must be int in 1..65535; got {args.port!r}"
    if args.iterations != DEFAULT_ITERATIONS:
        return f"--iterations must be {DEFAULT_ITERATIONS} (G5 contract); got {args.iterations!r}"
    for name, val in (("health-timeout-s", args.health_timeout_s),
                      ("health-interval-s", args.health_interval_s),
                      ("terminate-grace-s", args.terminate_grace_s)):
        if not isinstance(val, (int, float)) or val <= 0:
            return f"--{name} must be positive; got {val!r}"
    if args.cwd is not None and not Path(args.cwd).is_dir():
        return f"--cwd must be an existing directory; got {args.cwd!r}"
    if args.bridge_script is not None and not Path(args.bridge_script).is_file():
        return f"--bridge-script must be an existing file; got {args.bridge_script!r}"
    return None


def _emit(msg: str) -> None:
    sys.stderr.write(f"[run_g5_orchestration] {msg}\n")


def _argparse_exit_code(exc: SystemExit) -> int:
    return EXIT_OK if exc.code == 0 else EXIT_USAGE


# ── Default seam factories (monkey-patchable for hermetic tests) ────────
def build_default_seams(args: argparse.Namespace) -> dict:
    """Build the default {lifecycle, collector, bridge, planner, publisher}
    seam dict consumed by ``run_orchestration``. Tests override this
    module-level function with deterministic fakes — no real subprocess,
    browser, or network is touched by the test suite."""
    cwd = Path(args.cwd).resolve() if args.cwd else _default_cwd()
    # Lazy-import so the CLI module is importable without playwright.
    from scripts.capture_hydration import PlaywrightBrowserAdapter

    def collector(*, target_url, iterations, dom_marker_selector):
        return ch.collect_raw_samples(
            target_url=target_url,
            browser_adapter=PlaywrightBrowserAdapter(headless=not args.no_headless),
            iterations=iterations, dom_marker_selector=dom_marker_selector)
    return {"lifecycle": og.LegacyLifecycleAdapter(
                host=args.host, port=args.port, cwd=cwd,
                health_path=args.health_path,
                health_timeout_s=args.health_timeout_s,
                health_interval_s=args.health_interval_s,
                terminate_grace_s=args.terminate_grace_s),
            "collector": collector,
            "bridge": og._default_subprocess_bridge(),
            "planner": ch.plan_evidence_publication,
            "publisher": ch.publish_evidence_atomic}


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return _argparse_exit_code(e)
    err = _validate_args(args)
    if err is not None:
        _emit(err)
        return EXIT_VALIDATION
    out_dir = Path(args.out).resolve()
    cwd = Path(args.cwd).resolve() if args.cwd else _default_cwd()
    if args.dry_run:
        sys.stdout.write(
            f"[run_g5_orchestration] dry-run OK: target={args.target_url} "
            f"out={out_dir} host={args.host} port={args.port} cwd={cwd}\n")
        return EXIT_OK
    try:
        seams = build_default_seams(args)
    except Exception as e:
        _emit(f"default-seam wiring failed: {type(e).__name__}: {e}")
        return EXIT_RUNTIME
    try:
        r = og.run_orchestration(target_url=args.target_url, out_dir=out_dir,
            dom_marker_selector=args.dom_marker_selector,
            iterations=args.iterations, **seams)
    except og.OrchestrationError as e:
        _emit(f"orchestration failed: {type(e).__name__}: {e}")
        return EXIT_RUNTIME
    sys.stdout.write(
        f"[run_g5_orchestration] OK: schema={r['schema']} "
        f"iterations={r['iterations']} out_dir={r['out_dir']} "
        f"plan_files={r['plan_files']}\n")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
