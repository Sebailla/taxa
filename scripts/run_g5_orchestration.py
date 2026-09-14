#!/usr/bin/env python
"""G5 legacy-orchestration CLI — Slices 1 + 1A + 2.

Sibling to ``scripts/orchestrate_g5_legacy.py`` (Child B). Slice 1 owns
argparse + validation + dry-run-only. Slice 1A adds 5 hermetic seam
factories binding real public contracts but never executing substrates
at construction. Slice 2 wires non-dry-run through every factory into
``scripts.orchestrate_g5_legacy.run_orchestration`` + adds orchestration
error-taxonomy exit-code mapping. Slice 2 closes the deferred surface.

Exit codes (CLI-wide contract):
  0   success (dry-run resolved OR orchestration succeeded)
  1   usage / argparse error
  2   validation error OR ``ValueError`` / unknown exception (fail closed)
  3   readiness failure (``og.ReadinessError`` or bare ``TimeoutError``)
  4   collector failure (``og.CollectorError``)
  5   bridge failure (``og.BridgeError``)
  6   other orchestration failure (other ``og.OrchestrationError``)
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional, Sequence

# Make the repo root importable so ``from scripts import ...`` works
# regardless of invocation (direct ``python scripts/...py``, ``-m``, pytest).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts import orchestrate_g5_legacy as og
from scripts import capture_hydration as ch


# ── exit-code contract (CLI-wide) ──────────────────────────────────────────
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_VALIDATION = 2
EXIT_READINESS = 3
EXIT_COLLECTOR = 4
EXIT_BRIDGE = 5
EXIT_ORCHESTRATION = 6


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


# ── Slice 1A: non-executing seam factories ─────────────────────────────
# Each factory: returns the right shape, threads injectable overrides
# through, and does NOT spawn / probe / browse / run-Node / invoke
# collection / publish output / call run_orchestration at construction.
# Defaults bind to the REAL public contracts from scripts.capture_hydration
# (collect_raw_samples / plan_evidence_publication / publish_evidence_atomic);
# only lifecycle spawn/probe + bridge are CLI-local because those are the
# seams this slice must own without reaching into Child B privates.


class _CLIPopenHandle:
    """CLI-local subprocess handle matching Child B's SubprocessHandle
    Protocol. Defined locally so the CLI does not import Child B's private
    subprocess handle."""
    pid: int
    argv: tuple
    returncode: Optional[int]
    alive: bool

    def __init__(self, proc: "subprocess.Popen", argv: Sequence[str]):
        self.pid = proc.pid
        self.argv = tuple(argv)
        self._proc = proc
        self.returncode = None
        self.alive = True

    def terminate(self) -> None:
        self._proc.terminate()

    def wait(self, timeout_s: float) -> int:
        return self._proc.wait(timeout=timeout_s)

    def kill(self) -> None:
        self._proc.kill()


def _cli_default_subprocess_spawn(argv: Sequence[str], *, cwd: Path) -> _CLIPopenHandle:
    """CLI-local default spawn. DEVNULL stdio, exact argv. Independent from
    Child B's default spawn so the CLI does not import a private symbol."""
    proc = subprocess.Popen(list(argv), cwd=str(cwd),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    return _CLIPopenHandle(proc, argv)


def _cli_default_http_health_probe(host: str, port: int, path: str) -> bool:
    """CLI-local default probe: HTTP 200 + JSON status=='ok'. Independent
    re-implementation so the CLI does not import Child B privates."""
    try:
        with urllib.request.urlopen(f"http://{host}:{port}{path}",
                                    timeout=2.0) as r:
            if r.status != 200:
                return False
            payload = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("status") == "ok"


def make_lifecycle(*, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                   cwd: Path,
                   spawn: Optional[Callable] = None,
                   probe: Optional[Callable] = None,
                   health_path: str = DEFAULT_HEALTH_PATH,
                   health_timeout_s: float = DEFAULT_HEALTH_TIMEOUT_S,
                   health_interval_s: float = DEFAULT_HEALTH_INTERVAL_S,
                   terminate_grace_s: float = DEFAULT_TERMINATE_GRACE_S,
                   ):
    """Construct a LegacyLifecycleAdapter with injectable spawn + probe
    seams. Non-executing: .start() is NOT called, no subprocess is spawned.
    The returned adapter exposes .start() / .stop() / .base_url."""
    return og.LegacyLifecycleAdapter(
        host=host, port=port, cwd=cwd,
        spawn=spawn if spawn is not None else _cli_default_subprocess_spawn,
        probe=probe if probe is not None else _cli_default_http_health_probe,
        health_path=health_path,
        health_timeout_s=health_timeout_s,
        health_interval_s=health_interval_s,
        terminate_grace_s=terminate_grace_s,
    )


def make_collector(*, collector: Optional[Callable[..., dict]] = None,
                   browser_adapter: Optional[ch.BrowserAdapter] = None,
                   ) -> Callable[..., dict]:
    """Return a collector callable. Default closure binds to the REAL public
    ``capture_hydration.collect_raw_samples``; if no ``browser_adapter`` is
    injected, the closure lazily constructs a real
    ``capture_hydration.PlaywrightBrowserAdapter`` only when invoked (never
    at factory construction). Caller overrides win."""
    if collector is not None:
        return collector

    def _default_collector(*, target_url: str, iterations: int,
                           dom_marker_selector: str) -> dict:
        adapter = (browser_adapter if browser_adapter is not None
                   else ch.PlaywrightBrowserAdapter())
        return ch.collect_raw_samples(
            target_url=target_url, browser_adapter=adapter,
            iterations=iterations,
            dom_marker_selector=dom_marker_selector)
    return _default_collector


def make_bridge(*, bridge: Optional[Callable[[str], dict]] = None,
        bridge_script: Optional[Path] = None,
        ) -> Callable[[str], dict]:
        """Return a bridge callable (url) -> dict with envelope schema
        taxa.g5-raw-lhr.envelope/1. CLI-local default spawns node against
        ``bridge_script`` (or ``og.DEFAULT_BRIDGE_SCRIPT`` when None).
        Non-executing at construction; the closure spawns Node only when
        invoked later, so ``bridge_script`` is captured at construction
        time and threaded into argv at invocation time only."""
        if bridge is not None:
            return bridge
        script_path = (Path(bridge_script) if bridge_script is not None
                       else og.DEFAULT_BRIDGE_SCRIPT)

        def _default_bridge(url: str) -> dict:
            node = shutil.which("node")
            if not node:
                raise og.BridgeError(
                    "'node' binary not found on PATH; cannot invoke default bridge")
            proc = subprocess.run(
                [node, str(script_path), "--url", url],
                capture_output=True, text=True)
            if proc.returncode != 0:
                raise og.BridgeError(
                    f"bridge process exited {proc.returncode}: "
                    f"stderr={proc.stderr.strip()!r}")
            line = next((ln for ln in proc.stdout.splitlines() if ln.strip()),
                        None)
            if not line:
                raise og.BridgeError(
                    f"bridge emitted no envelope JSON line "
                    f"(stdout={proc.stdout!r})")
            try:
                return json.loads(line)
            except json.JSONDecodeError as e:
                raise og.BridgeError(
                    f"bridge envelope is not valid JSON: {e}") from e
        return _default_bridge


def make_planner(*, planner: Optional[Callable[..., dict]] = None,
                 ) -> Callable[..., dict]:
    """Return a planner callable. Default binds to the REAL public
    ``capture_hydration.plan_evidence_publication`` (deterministic, pure,
    no-I/O). Caller overrides win."""
    if planner is not None:
        return planner
    return ch.plan_evidence_publication


def make_publisher(*, publisher: Optional[Callable[..., None]] = None,
                   ) -> Callable[..., None]:
    """Return a publisher callable. Default binds to the REAL public
    ``capture_hydration.publish_evidence_atomic`` (atomic filesystem publisher
    with backup/restore semantics). Caller overrides win."""
    if publisher is not None:
        return publisher
    return ch.publish_evidence_atomic


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

    # Side-effect-free path: --dry-run NEVER touches seam factories or
    # ``og.run_orchestration`` (see test_dry_run_never_constructs_or_calls_seams).
    if args.dry_run:
        sys.stdout.write(
            f"[run_g5_orchestration] dry-run OK: target={args.target_url} "
            f"out={out_dir} host={args.host} port={args.port} cwd={cwd}\n"
        )
        return EXIT_OK

    # Non-dry-run: build 5 factories + invoke the public orchestrator. The
    # orchestrator receives the EXACT instances returned by the factories
    # plus CLI-level kwargs (target_url / out_dir / iterations /
    # dom_marker_selector). See test_non_dry_run_threads_cli_values_*.
    bridge_script_path = (Path(args.bridge_script) if args.bridge_script
                          else None)
    lifecycle = make_lifecycle(host=args.host, port=args.port, cwd=cwd,
                               health_path=args.health_path,
                               health_timeout_s=args.health_timeout_s,
                               health_interval_s=args.health_interval_s,
                               terminate_grace_s=args.terminate_grace_s)
    collector = make_collector()
    bridge = make_bridge(bridge_script=bridge_script_path)
    planner = make_planner()
    publisher = make_publisher()

    # Error taxonomy: most specific first so Readiness/Collector/Bridge
    # never fall through to OrchestrationError (their parent). TimeoutError
    # is unrelated to OrchestrationError (it's an OSError); ValueError /
    # unknown fail closed to validation (2).
    try:
        descriptor = og.run_orchestration(
            lifecycle=lifecycle, collector=collector, bridge=bridge,
            planner=planner, publisher=publisher,
            target_url=args.target_url, out_dir=out_dir,
            dom_marker_selector=args.dom_marker_selector,
            iterations=args.iterations)
    except og.ReadinessError as e:
        _emit(f"readiness: {e}"); return EXIT_READINESS
    except TimeoutError as e:
        _emit(f"readiness timeout: {e}"); return EXIT_READINESS
    except og.CollectorError as e:
        _emit(f"collector: {e}"); return EXIT_COLLECTOR
    except og.BridgeError as e:
        _emit(f"bridge: {e}"); return EXIT_BRIDGE
    except og.OrchestrationError as e:
        _emit(f"orchestration: {e}"); return EXIT_ORCHESTRATION
    except ValueError as e:
        _emit(f"validation: {e}"); return EXIT_VALIDATION
    except Exception as e:
        _emit(f"unexpected: {type(e).__name__}: {e}"); return EXIT_VALIDATION

    # Concise success summary from the descriptor returned by the orchestrator.
    sys.stdout.write(
        f"[run_g5_orchestration] success: "
        f"target={descriptor.get('target_url')} "
        f"iterations={descriptor.get('iterations')} "
        f"out={descriptor.get('out_dir')} "
        f"published_at={descriptor.get('published_at')} "
        f"plan_files={descriptor.get('plan_files')}\n")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
