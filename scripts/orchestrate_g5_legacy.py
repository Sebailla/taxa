#!/usr/bin/env python
"""Split G5 orchestration child A — controlled legacy lifecycle + honest
hydration metadata derivation. Scope: injectable ASGI subprocess lifecycle
(exact uvicorn argv, fixture-backed health readiness, guaranteed terminate/
reap) and honest hydration metadata derivation from ten Playwright samples
using medians, real readiness waits, and verbatim warning records. Library-
only — child B owns the orchestration entry point.
"""
from __future__ import annotations
import contextlib
import json
import statistics
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Protocol, Sequence
LEGACY_ASGI_APP_TARGET = 'tools.g3-legacy-fixture.scripts.g5_legacy_asgi:app'
DEFAULT_HEALTH_PATH = '/api/health'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_HEALTH_INTERVAL_S = 0.05
DEFAULT_HEALTH_TIMEOUT_S = 10.0
DEFAULT_TERMINATE_GRACE_S = 5.0
LEGACY_HYDRATION_SCHEMA = 'taxa.g5-orchestrator.legacy-hydration/1'

class SubprocessHandle(Protocol):
    pid: int
    argv: Sequence[str]
    returncode: int | None
    alive: bool

    def terminate(self) -> None:
        ...

    def wait(self, timeout_s: float) -> int:
        ...

    def kill(self) -> None:
        ...

class LifecycleSpawn(Protocol):
    """Injectable subprocess spawner."""

    def __call__(self, argv: Sequence[str], *, cwd: Path) -> SubprocessHandle:
        ...

class HealthProbe(Protocol):
    """True iff the service is healthy right now."""

    def __call__(self, host: str, port: int, path: str) -> bool:
        ...

@dataclass
class _PopenHandle:
    pid: int
    argv: Sequence[str]
    _proc: subprocess.Popen
    returncode: int | None = None
    alive: bool = True

    def terminate(self) -> None:
        self._proc.terminate()

    def wait(self, timeout_s: float) -> int:
        return self._proc.wait(timeout=timeout_s)

    def kill(self) -> None:
        self._proc.kill()

def _default_subprocess_spawn(argv: Sequence[str], *, cwd: Path) -> _PopenHandle:
    """Spawn the legacy ASGI subprocess with exact uvicorn argv (DEVNULL stdio)."""
    proc = subprocess.Popen(list(argv), cwd=str(cwd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return _PopenHandle(pid=proc.pid, argv=tuple(argv), _proc=proc)

def _default_http_health_probe(host: str, port: int, path: str) -> bool:
    """True iff status==200 and JSON body has ``status == "ok"`` (the G3
    fixture's ``/api/health`` contract)."""
    try:
        with urllib.request.urlopen(f'http://{host}:{port}{path}', timeout=2.0) as r:
            if r.status != 200:
                return False
            payload = json.loads(r.read().decode('utf-8'))
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get('status') == 'ok'

def spawn_legacy_subprocess(*, spawn: LifecycleSpawn, host: str, port: int, cwd: Path, app_target: str=LEGACY_ASGI_APP_TARGET) -> SubprocessHandle:
    argv = ('uvicorn', app_target, '--host', host, '--port', str(port), '--log-level', 'warning')
    return spawn(argv, cwd=cwd)

def wait_for_health(*, probe: HealthProbe, host: str, port: int, path: str, timeout_s: float, interval_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    attempt = 0
    while True:
        attempt += 1
        if probe(host, port, path):
            return
        if time.monotonic() >= deadline:
            raise TimeoutError(f'health readiness not achieved after {attempt} probe(s) in {timeout_s:.2f}s on http://{host}:{port}{path}')
        time.sleep(interval_s)

def terminate_legacy_subprocess(handle: SubprocessHandle, *, grace_s: float) -> int:
    if handle.returncode is not None:
        return handle.returncode
    try:
        try:
            handle.terminate()
        except OSError:
            handle.kill()
            handle.returncode = handle.wait(grace_s)
            handle.alive = False
            return handle.returncode
        handle.returncode = handle.wait(grace_s)
        handle.alive = False
        return handle.returncode
    except subprocess.TimeoutExpired:
        handle.kill()
        handle.returncode = handle.wait(grace_s)
        handle.alive = False
        return handle.returncode

@contextlib.contextmanager
def run_legacy_lifecycle(*, spawn: LifecycleSpawn, probe: HealthProbe, host: str, port: int, cwd: Path, health_path: str=DEFAULT_HEALTH_PATH, health_timeout_s: float=DEFAULT_HEALTH_TIMEOUT_S, health_interval_s: float=DEFAULT_HEALTH_INTERVAL_S, terminate_grace_s: float=DEFAULT_TERMINATE_GRACE_S) -> Iterator[SubprocessHandle]:
    handle = spawn_legacy_subprocess(spawn=spawn, host=host, port=port, cwd=cwd)
    try:
        wait_for_health(probe=probe, host=host, port=port, path=health_path, timeout_s=health_timeout_s, interval_s=health_interval_s)
        yield handle
    finally:
        terminate_legacy_subprocess(handle, grace_s=terminate_grace_s)

def _median(values: Sequence[float]) -> float:
    if not values:
        raise ValueError('cannot compute median of empty sequence')
    return float(statistics.median(values))

def derive_legacy_hydration_metadata(samples: Sequence[dict], *, captured_at: str, route: str) -> dict:
    if len(samples) != 10:
        raise ValueError(f'legacy hydration metadata requires exactly 10 samples; got {len(samples)}')
    for i, s in enumerate(samples):
        if not isinstance(s, dict):
            raise ValueError(f'sample {i} must be a dict; got {type(s).__name__}')
        for k in ('paint', 'navigation', 'dom_marker', 'console'):
            if k not in s:
                raise ValueError(f'sample {i} missing required key {k!r}')
    fps = [float(s['paint']['first_paint_ms']) for s in samples]
    fcps = [float(s['paint']['first_contentful_paint_ms']) for s in samples]
    dcls = [float(s['navigation']['dom_content_loaded_ms']) for s in samples]
    waits = [float(s['dom_marker']['wait_ms']) for s in samples]
    interactive = [d + w for d, w in zip(dcls, waits)]
    console_warnings: list[dict] = []
    for i, s in enumerate(samples):
        for msg in s.get('console', []):
            console_warnings.append({'sample': i, 'iteration': int(s.get('iteration', i)), **msg})
    return {'schema': LEGACY_HYDRATION_SCHEMA, 'captured_at': captured_at, 'build': 'legacy', 'route': route, 'server_shell': {'first_paint_ms': _median(fps), 'dom_content_loaded_ms': _median(dcls)}, 'client_render': {'tree_first_paint_ms': _median(fcps), 'tree_first_interactive_ms': _median(interactive)}, 'console_warnings': console_warnings, 'readiness_wait_ms': _median(waits)}
