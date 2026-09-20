#!/usr/bin/env python3
"""Single-command local development launcher.

Drives the FastAPI backend (`api/server.py`) and the Next.js frontend
(`pnpm run dev:local`) as supervised subprocesses from one process so
`make dev` replaces the two-terminal workflow.

Lifecycle:
    1. Spawn FastAPI via the same uvicorn command `make api` uses, so
       the bind contract (`--host 127.0.0.1 --port 8765`) is shared
       with the existing `make api` recipe.
    2. Poll ``http://127.0.0.1:8765/api/health`` until the endpoint
       returns 2xx, or fail non-zero with a clear readiness-timeout
       message.
    3. Spawn the Next.js dev server with
       ``NEXT_PUBLIC_TAXA_API_ORIGIN=http://127.0.0.1:8765`` exported
       into the child environment. The frontend uses the same env
       contract that ``pnpm dev:local`` already exposes.
    4. Forward SIGINT / SIGTERM to both children (SIGTERM to the
       process group, then SIGKILL after a grace period), wait for
       them to exit, and propagate a non-zero return on child failure.

All side effects (process spawn, readiness polling, sleep, signal
wiring) factor through small injectable callables so the contract
can be tested hermetically without uvicorn, Next, or a network port.
The CLI entry point wires real defaults.

This module deliberately uses only the Python standard library and
ships as a developer-experience launcher, NOT a runtime dependency of
the application.
"""
from __future__ import annotations

import argparse
import contextlib
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# ── Defaults ──────────────────────────────────────────────────────────────


DEFAULT_API_HEALTH_URL = "http://127.0.0.1:8765/api/health"
DEFAULT_NEXT_API_ORIGIN = "http://127.0.0.1:8765"
DEFAULT_HEALTH_TIMEOUT_S = 60.0
DEFAULT_HEALTH_POLL_S = 0.25
DEFAULT_SUPERVISE_POLL_S = 0.1
DEFAULT_CHILD_GRACE_S = 5.0

NEXT_API_ORIGIN_ENV = "NEXT_PUBLIC_TAXA_API_ORIGIN"


# ── Errors ────────────────────────────────────────────────────────────────


class LauncherError(Exception):
    """Base class for supervisor errors."""


class HealthCheckTimeout(LauncherError):
    """Readiness poll did not return 2xx within the configured timeout."""

    def __init__(self, url: str, timeout_s: float) -> None:
        super().__init__(
            f"Timed out after {timeout_s:.1f}s waiting for {url}"
        )
        self.url = url
        self.timeout_s = timeout_s


# ── Process handle ───────────────────────────────────────────────────────


@dataclass
class ChildProcess:
    """Supervisor-facing handle for one child process.

    The default real-process implementation derives `poll_fn` and
    `stop_fn` from a ``subprocess.Popen`` instance. Tests inject their
    own callables to exercise the contract without spawning real
    subprocesses.
    """

    name: str
    pid: int
    poll_fn: Callable[[], int | None]
    stop_fn: Callable[[float], int | None]
    stopped: bool = False

    @classmethod
    def from_popen(
        cls, name: str, proc: subprocess.Popen[bytes]
    ) -> ChildProcess:
        """Build a ChildProcess around a real subprocess.Popen."""

        def stop_fn(grace_s: float) -> int | None:
            return _terminate_process_group(proc, grace_s)

        return cls(
            name=name,
            pid=proc.pid,
            poll_fn=proc.poll,
            stop_fn=stop_fn,
        )

    @property
    def returncode(self) -> int | None:
        return self.poll_fn()

    @property
    def alive(self) -> bool:
        return self.poll_fn() is None

    def stop(self, grace_s: float = DEFAULT_CHILD_GRACE_S) -> int | None:
        """Send SIGTERM to the child's process group; SIGKILL after
        `grace_s`. Idempotent — calling on an already-dead child is
        harmless."""
        if self.poll_fn() is not None:
            return self.returncode
        result = self.stop_fn(grace_s)
        self.stopped = True
        return result


def _terminate_process_group(
    proc: subprocess.Popen[bytes], grace_s: float
) -> int | None:
    """SIGTERM the child's process group, then SIGKILL after `grace_s`.
    Targets the whole group (set up via ``start_new_session=True``) so
    descendants die alongside the child.
    """
    if proc.poll() is not None:
        return proc.returncode
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return proc.poll()
    try:
        return proc.wait(timeout=grace_s)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        try:
            return proc.wait(timeout=grace_s)
        except subprocess.TimeoutExpired:
            return proc.poll()


# ── Command specs ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CommandSpec:
    """argv + env + cwd describing one supervised child."""

    name: str
    argv: Sequence[str]
    env: Mapping[str, str]
    cwd: str | None = None


def build_api_spec(
    *,
    venv_python: str = ".venv/bin/python3",
    host: str = "127.0.0.1",
    port: int = 8765,
    cwd: str | None = None,
) -> CommandSpec:
    """Match the `make api` recipe exactly: uvicorn api.server:app
    --host 127.0.0.1 --port 8765, run from the repo .venv python."""
    return CommandSpec(
        name="api",
        argv=[
            venv_python,
            "-m", "uvicorn",
            "api.server:app",
            "--host", host,
            "--port", str(port),
        ],
        env=dict(os.environ),
        cwd=cwd,
    )


def build_frontend_spec(
    *,
    api_origin: str = DEFAULT_NEXT_API_ORIGIN,
    package_manager: str = "pnpm",
    cwd: str | None = None,
) -> CommandSpec:
    """Use `pnpm run dev:local` (the existing package.json script).
    Exports NEXT_PUBLIC_TAXA_API_ORIGIN=api_origin into the child
    environment so the contract is honored even when the upstream
    package.json script mutates over time.
    """
    env = dict(os.environ)
    env[NEXT_API_ORIGIN_ENV] = api_origin
    return CommandSpec(
        name="frontend",
        argv=[package_manager, "run", "dev:local"],
        env=env,
        cwd=cwd,
    )


# ── Health check ─────────────────────────────────────────────────────────


def default_probe(url: str) -> bool:
    """urllib-backed readiness probe. 2xx -> ready, anything else ->
    not yet. Any exception is treated as 'not ready' so the poll
    continues until the deadline."""
    import http.client
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if parsed.scheme == "http" and parsed.hostname:
            conn = http.client.HTTPConnection(
                parsed.hostname,
                parsed.port or 80,
                timeout=2.0,
            )
        elif parsed.scheme == "https" and parsed.hostname:
            conn = http.client.HTTPSConnection(
                parsed.hostname,
                parsed.port or 443,
                timeout=2.0,
            )
        else:
            return False
        try:
            conn.request("GET", parsed.path or "/",
                         headers={"Host": parsed.netloc})
            resp = conn.getresponse()
            return 200 <= resp.status < 300
        finally:
            conn.close()
    except OSError:  # any network failure means not ready
        return False


# ── Default spawn / signal wiring (defined before Supervisor so it can
# default to them) ────────────────────────────────────────────────────────


def default_spawn(spec: CommandSpec) -> ChildProcess:
    """Spawn `spec.argv` in a fresh process group; return a ChildProcess.
    `start_new_session=True` puts the child in its own session/process
    group so signal forwarding can target the group.
    """
    proc = subprocess.Popen(
        list(spec.argv),
        env=dict(spec.env),
        cwd=spec.cwd,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
    )
    return ChildProcess.from_popen(spec.name, proc)


def install_signal_handlers(handler: Callable[[int, Any], None]) -> None:
    """Install SIGINT/SIGTERM handlers that set the supervisor flag."""
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def wait_for_health(
    url: str,
    *,
    timeout_s: float = DEFAULT_HEALTH_TIMEOUT_S,
    poll_s: float = DEFAULT_HEALTH_POLL_S,
    probe_fn: Callable[[str], bool] | None = None,
) -> None:
    """Poll `url` until the probe returns True or `timeout_s` elapses.

    `probe_fn` defaults to ``default_probe`` (urllib-backed 2xx check).
    Tests inject fakes so this stays hermetic.
    """
    deadline = time.monotonic() + timeout_s
    while True:
        if (probe_fn or default_probe)(url):
            return
        if time.monotonic() >= deadline:
            raise HealthCheckTimeout(url, timeout_s)
        time.sleep(poll_s)


# ── Supervisor ───────────────────────────────────────────────────────────


class Supervisor:
    """Lifecycle supervisor for two child processes.

    All side effects (process spawn, readiness polling, sleep, signal
    installation) ride through small injectable callables so the
    contract can be exercised without uvicorn, Next, or a network
    port. Real defaults wire to ``subprocess.Popen``,
    ``wait_for_health``, ``time.sleep`` and the system signal
    installers.

    `spawn_fn`, `health_fn`, `sleep_fn`, and `install_signals_fn` are
    keyword-only. Tests inject fakes via those parameters; the CLI
    wires the real defaults.
    """

    def __init__(
        self,
        api_spec: CommandSpec,
        frontend_spec: CommandSpec,
        *,
        health_url: str = DEFAULT_API_HEALTH_URL,
        health_timeout_s: float = DEFAULT_HEALTH_TIMEOUT_S,
        health_poll_s: float = DEFAULT_HEALTH_POLL_S,
        poll_interval_s: float = DEFAULT_SUPERVISE_POLL_S,
        spawn_fn: Callable[[CommandSpec], ChildProcess] = default_spawn,
        health_fn: Callable[..., None] = wait_for_health,
        sleep_fn: Callable[[float], None] = time.sleep,
        install_signals_fn: Callable[
            [Callable[[int, Any], None]], None
        ] = install_signal_handlers,
    ) -> None:
        self.api_spec = api_spec
        self.frontend_spec = frontend_spec
        self.health_url = health_url
        self.health_timeout_s = health_timeout_s
        self.health_poll_s = health_poll_s
        self.poll_interval_s = poll_interval_s
        self.spawn_fn = spawn_fn
        self.health_fn = health_fn
        self.sleep_fn = sleep_fn
        self.install_signals_fn = install_signals_fn
        self.api_proc: ChildProcess | None = None
        self.frontend_proc: ChildProcess | None = None
        self._received_signal: int | None = None

    def _on_signal(self, signum: int, _frame: Any) -> None:
        """Signal handler installed by `install_signals_fn`."""
        self._received_signal = signum

    def run(self) -> int:
        """Start api, wait for readiness, start frontend, supervise.

        Returns the process exit code:
          - ``128 + signum`` for SIGINT/SIGTERM-driven shutdown
          - ``1`` on readiness timeout, API pre-health crash, or
            unexpected child exit
          - ``0`` only on a clean shutdown initiated by a child
            exiting with rc=0 (rare; SIGINT is the typical path).
        """
        self.install_signals_fn(self._on_signal)
        self.api_proc = self.spawn_fn(self.api_spec)
        try:
            # `wait_for_health()` declares `timeout_s` and `poll_s` as
            # keyword-only (after `*`), so we MUST pass them by keyword.
            # Positional invocation raises TypeError before the
            # readiness loop runs; the fakes used in tests have a
            # positional signature, so they masked this bug. Tests use
            # a `lambda url, **kw: None` style that accepts either.
            self.health_fn(
                self.health_url,
                timeout_s=self.health_timeout_s,
                poll_s=self.health_poll_s,
            )
        except HealthCheckTimeout as e:
            sys.stderr.write(f"dev: {e}\n")
            self._stop_all()
            return 1
        # If the API exited during the readiness window, propagate.
        if self.api_proc is None or not self.api_proc.alive:
            rc = self.api_proc.returncode if self.api_proc else None
            sys.stderr.write(
                f"dev: api exited with code {rc} before frontend "
                f"started\n"
            )
            self._stop_all()
            return 1
        self.frontend_proc = self.spawn_fn(self.frontend_spec)
        return self._supervise_loop()

    def _supervise_loop(self) -> int:
        """Poll children + signal flag until something terminates the
        supervisor. Returns the supervisor exit code."""
        while True:
            # 1. Signals win (POSIX convention: 128 + signum).
            if self._received_signal is not None:
                sig = self._received_signal
                self._stop_all()
                return 128 + sig
            # 2. Did a child exit?
            api_rc = self.api_proc.returncode if self.api_proc else None
            fe_rc = (
                self.frontend_proc.returncode if self.frontend_proc else None
            )
            if api_rc is not None or fe_rc is not None:
                if api_rc is not None:
                    label, rc = "api", api_rc
                else:
                    label, rc = "frontend", fe_rc
                sys.stderr.write(
                    f"dev: {label} exited with code {rc}; stopping the "
                    f"other child\n"
                )
                self._stop_all()
                # Non-zero propagation: any signaled child exits non-zero;
                # a child that exits 0 is possible but treated as fine.
                return 1 if rc != 0 else 0
            self.sleep_fn(self.poll_interval_s)

    def _stop_all(self) -> None:
        """Stop every still-alive child. Idempotent; logs failures."""
        for proc in (self.frontend_proc, self.api_proc):
            if proc is None:
                continue
            try:
                proc.stop()
            except Exception as e:  # pragma: no cover - defensive
                sys.stderr.write(
                    f"dev: failed to stop {proc.name}: {e}\n"
                )


# ── CLI entry point ──────────────────────────────────────────────────────


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: parse args, build specs, run the supervisor."""
    parser = argparse.ArgumentParser(
        prog="dev",
        description=(
            "Local development launcher: starts FastAPI, waits for "
            "/api/health, then starts Next with the API origin env var."
        ),
    )
    parser.add_argument(
        "--health-url",
        default=DEFAULT_API_HEALTH_URL,
        metavar="URL",
        help=(
            "Readiness URL polled after the API child starts. Default: "
            "%(default)s"
        ),
    )
    parser.add_argument(
        "--api-origin",
        default=DEFAULT_NEXT_API_ORIGIN,
        metavar="URL",
        help=(
            f"Value exposed to the frontend as {NEXT_API_ORIGIN_ENV}. "
            "Default: %(default)s"
        ),
    )
    parser.add_argument(
        "--health-timeout",
        type=float,
        default=DEFAULT_HEALTH_TIMEOUT_S,
        metavar="SECONDS",
        help=(
            "Maximum seconds to wait for /api/health. Default: "
            "%(default).0f"
        ),
    )
    parser.add_argument(
        "--api-cwd",
        default=None,
        metavar="DIR",
        help="Working directory for uvicorn (default: cwd at launch).",
    )
    parser.add_argument(
        "--frontend-cwd",
        default=None,
        metavar="DIR",
        help="Working directory for pnpm run dev:local (default: cwd).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    sup = Supervisor(
        api_spec=build_api_spec(cwd=args.api_cwd),
        frontend_spec=build_frontend_spec(
            api_origin=args.api_origin,
            cwd=args.frontend_cwd,
        ),
        health_url=args.health_url,
        health_timeout_s=args.health_timeout,
    )
    return sup.run()


if __name__ == "__main__":
    sys.exit(main())
