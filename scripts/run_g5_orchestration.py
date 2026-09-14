#!/usr/bin/env python
"""G5 legacy-orchestration CLI — Slice 1: parse + validate + dry-run.

Sibling to ``scripts/orchestrate_g5_legacy.py`` (Child B). Slice 1 owns
ONLY the bounded CLI surface that the seam-wiring slice and the
orchestrator slice compose on top of:

  - argparse contract (required flags, ``--help`` exit-code-0, defaults
    sourced from Child B's module-level constants)
  - per-flag validation (URL scheme, port range, iterations invariant,
    positive health / grace timings, existing ``--cwd`` /
    ``--bridge-script`` paths when supplied)
  - deterministic exit codes for the parse + validate path
    (EXIT_OK / EXIT_USAGE / EXIT_VALIDATION)
  - ``--dry-run``: parse + validate + resolve paths + emit a one-line
    summary, then exit 0 WITHOUT invoking any seam factory or
    ``run_orchestration``

Deferred to later slices (coverage preserved, not dropped): seam factories,
error-taxonomy mapping, ``run_orchestration`` invocation + lifecycle cleanup,
success-path assertions.

Exit codes (Slice 1 narrow contract):
  0   success (parse + validate + dry-run resolved)
  1   usage / argparse error
  2   validation error OR seam-wiring-deferred rejection when ``--dry-run``
      is omitted in Slice 1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the repo root importable so ``from scripts import ...`` works
# regardless of invocation (direct ``python scripts/...py``, ``-m``, pytest).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts import orchestrate_g5_legacy as og


# ── exit-code contract (Slice 1 narrow surface) ─────────────────────────────
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_VALIDATION = 2


# ── argparse defaults (sourced from Child B) ────────────────────────────────
DEFAULT_HOST = og.DEFAULT_HOST
DEFAULT_PORT = 8765
DEFAULT_HEALTH_PATH = og.DEFAULT_HEALTH_PATH
DEFAULT_HEALTH_TIMEOUT_S = og.DEFAULT_HEALTH_TIMEOUT_S
DEFAULT_HEALTH_INTERVAL_S = og.DEFAULT_HEALTH_INTERVAL_S
DEFAULT_TERMINATE_GRACE_S = og.DEFAULT_TERMINATE_GRACE_S
DEFAULT_ITERATIONS = og.ITERATIONS
DEFAULT_DOM_MARKER_SELECTOR = og.DEFAULT_DOM_MARKER_SELECTOR


def _default_cwd() -> Path:
    """Default spawn cwd = Child B's REPO_ROOT constant."""
    return og.REPO_ROOT


def _build_parser() -> argparse.ArgumentParser:
    """Argparse surface. ``add_help=False`` is intentionally NOT used —
    we want the standard ``--help`` exit-code-0 contract."""
    p = argparse.ArgumentParser(
        prog="run_g5_orchestration.py",
        description=("G5 legacy-orchestration CLI (Slice 1: parse + validate "
                     "+ dry-run). Seam wiring is delegated to later slices."),
    )
    p.add_argument("--target-url", required=True,
                   help="Controlled legacy FastAPI URL "
                        "(must start with http:// or https://)")
    p.add_argument("--out", required=True,
                   help="Output directory for the atomic evidence publication")
    p.add_argument("--host", default=DEFAULT_HOST,
                   help=f"Legacy ASGI bind host (default: {DEFAULT_HOST})")
    p.add_argument("--port", type=int, default=DEFAULT_PORT,
                   help=f"Legacy ASGI bind port (default: {DEFAULT_PORT})")
    p.add_argument("--cwd", default=None,
                   help=f"uvicorn spawn cwd (default: {_default_cwd()})")
    p.add_argument("--health-path", default=DEFAULT_HEALTH_PATH,
                   help=f"Health probe path (default: {DEFAULT_HEALTH_PATH})")
    p.add_argument("--health-timeout-s", type=float,
                   default=DEFAULT_HEALTH_TIMEOUT_S,
                   help="Health readiness timeout (seconds)")
    p.add_argument("--health-interval-s", type=float,
                   default=DEFAULT_HEALTH_INTERVAL_S,
                   help="Health probe interval (seconds)")
    p.add_argument("--terminate-grace-s", type=float,
                   default=DEFAULT_TERMINATE_GRACE_S,
                   help="SIGTERM → SIGKILL grace (seconds)")
    p.add_argument("--bridge-script", default=None,
                   help="Override the default bridge script path "
                        f"(default: {og.DEFAULT_BRIDGE_SCRIPT})")
    p.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS,
                   help=f"Must equal {DEFAULT_ITERATIONS} (G5 contract)")
    p.add_argument("--dom-marker-selector", default=DEFAULT_DOM_MARKER_SELECTOR,
                   help="DOM-marker selector for capture readiness wait")
    p.add_argument("--no-headless", action="store_true",
                   help="Run the browser in headed mode (debug only)")
    p.add_argument("--dry-run", action="store_true",
                   help="Parse + validate only; do not invoke run_orchestration")
    return p


def _validate_args(args: argparse.Namespace) -> str | None:
    """Return ``None`` on success or an error string on validation failure."""
    if not (isinstance(args.target_url, str)
            and args.target_url.startswith(("http://", "https://"))):
        return (f"--target-url must start with http:// or https://; "
                f"got {args.target_url!r}")
    if not isinstance(args.port, int) or not (1 <= args.port <= 65535):
        return f"--port must be an int in 1..65535; got {args.port!r}"
    if args.iterations != DEFAULT_ITERATIONS:
        return (f"--iterations must be {DEFAULT_ITERATIONS} (G5 contract); "
                f"got {args.iterations!r}")
    for name, val in (("health-timeout-s", args.health_timeout_s),
                      ("health-interval-s", args.health_interval_s),
                      ("terminate-grace-s", args.terminate_grace_s)):
        if not isinstance(val, (int, float)) or val <= 0:
            return f"--{name} must be a positive number; got {val!r}"
    if args.cwd is not None and not Path(args.cwd).is_dir():
        return f"--cwd must be an existing directory; got {args.cwd!r}"
    if args.bridge_script is not None and not Path(args.bridge_script).is_file():
        return (f"--bridge-script must be an existing file; "
                f"got {args.bridge_script!r}")
    return None


def _emit(msg: str) -> None:
    """One-line stderr log so callers can grep the CLI's preflight noise."""
    sys.stderr.write(f"[run_g5_orchestration] {msg}\n")


def _handle_argparse_exit(exc: SystemExit) -> int:
    """Map argparse's ``SystemExit`` to our bounded CLI exit-code contract.

    argparse calls ``sys.exit(0)`` for ``--help`` and ``sys.exit(2)`` for
    usage errors. We map both to controlled CLI codes so a caller never
    sees a raw ``SystemExit`` propagate from ``main``.
    """
    return EXIT_OK if exc.code == 0 else EXIT_USAGE


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return _handle_argparse_exit(e)

    validation_error = _validate_args(args)
    if validation_error is not None:
        _emit(validation_error)
        return EXIT_VALIDATION

    out_dir = Path(args.out).resolve()
    cwd = Path(args.cwd).resolve() if args.cwd else _default_cwd()

    # Slice 1 contract: --dry-run is the only wired path; non-dry-run is
    # rejected with EXIT_VALIDATION. The seam-wiring slice replaces this
    # branch with the real run_orchestration invocation.
    if not args.dry_run:
        _emit("--dry-run is required in Slice 1; "
              "seam wiring + run_orchestration are deferred to later slices")
        return EXIT_VALIDATION

    sys.stdout.write(
        f"[run_g5_orchestration] dry-run OK: target={args.target_url} "
        f"out={out_dir} host={args.host} port={args.port} cwd={cwd}\n"
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
