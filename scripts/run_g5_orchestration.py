#!/usr/bin/env python
"""G5 legacy-orchestration CLI — Slice 13 (adapted from ``9c8219b``).

Composes ``scripts.orchestrate_g5_legacy.run_orchestration`` with fully
injectable seam factories (lifecycle, collector, bridge, planner,
publisher). Slice 13 adapts commit ``9c8219b``'s Slice 1A onto current
develop (Slices 1–12 ship CLI + lifecycle + orchestration entry + default
raw-Lighthouse bridge). The bounded ``--dry-run`` surface is preserved
verbatim; this slice wires CLI-local public seam factories
(``make_lifecycle`` / ``make_collector`` / ``make_bridge`` / ``make_planner``
/ ``make_publisher``) and re-routes ``build_default_seams`` through them so
the CLI no longer reaches into Child B private symbols.

Contract:
  * ``--dry-run``: parse + validate + one-line summary, exit 0
    WITHOUT invoking any seam factory or ``run_orchestration``.
  * (default): build defaults via ``build_default_seams(args)`` and call
    ``run_orchestration``.

Exit codes: 0 success, 1 usage, 2 validation, 3 runtime error.
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


# ── Slice 13: non-executing seam factories ─────────────────────────────
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
    argv: Sequence[str]
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


def _cli_default_subprocess_spawn(argv: Sequence[str], *, cwd: Path) -> "og.SubprocessHandle":
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
                ) -> Callable[[str], dict]:
    """Return a bridge callable (url) -> dict with envelope schema
    taxa.g5-raw-lhr.envelope/1. CLI-local default spawns node against
    Child B's public DEFAULT_BRIDGE_SCRIPT. Non-executing at construction;
    the closure spawns Node only when invoked later."""
    if bridge is not None:
        return bridge

    def _default_bridge(url: str) -> dict:
        node = shutil.which("node")
        if not node:
            raise og.BridgeError(
                "'node' binary not found on PATH; cannot invoke default bridge")
        proc = subprocess.run(
            [node, str(og.DEFAULT_BRIDGE_SCRIPT), "--url", url],
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


# ── Default seam assembly (monkey-patchable for hermetic tests) ─────────
def build_default_seams(args: argparse.Namespace) -> dict:
    """Build the default {lifecycle, collector, bridge, planner, publisher}
    seam dict consumed by ``run_orchestration`` by routing through the CLI-local
    public ``make_*()`` factories. Tests override this module-level function
    with deterministic fakes — no real subprocess, browser, or network is
    touched by the test suite."""
    cwd = Path(args.cwd).resolve() if args.cwd else _default_cwd()
    return {"lifecycle": make_lifecycle(
                host=args.host, port=args.port, cwd=cwd,
                health_path=args.health_path,
                health_timeout_s=args.health_timeout_s,
                health_interval_s=args.health_interval_s,
                terminate_grace_s=args.terminate_grace_s),
            "collector": make_collector(),
            "bridge": make_bridge(),
            "planner": make_planner(),
            "publisher": make_publisher()}


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
