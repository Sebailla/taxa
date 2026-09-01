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
from typing import Iterator, Optional, Protocol, Sequence
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


# ============================================================================
# G5 orchestration child B (composition) — injectable run function.
# ============================================================================
LEGACY_COMPOSITION_SCHEMA = 'taxa.g5-orchestrator.composition/1'
LEGACY_PW_SCHEMA = 'taxa.g5-capture.legacy/1'
LEGACY_LH_BRIDGE_SCHEMA = 'taxa.g5-raw-lhr.envelope/1'
COMPOSITION_ITERATIONS = 10


class PlaywrightCollector(Protocol):
    """Injectable Playwright collector. Returns the PW envelope (schema
    ``taxa.g5-capture.legacy/1``) with exactly ten samples."""
    def __call__(self, *, target_url: str) -> dict: ...


class LhrBridge(Protocol):
    """Injectable Node-bridge subprocess seam. Returns ONE LHR envelope
    (schema ``taxa.g5-raw-lhr.envelope/1``) per call."""
    def __call__(self, url: str) -> dict: ...


class ManifestSnapshotProvider(Protocol):
    """Injectable G4 manifest snapshot provider. Returns ``schema`` + ``entries``."""
    def __call__(self) -> dict: ...


class EvidencePlanner(Protocol):
    """Injectable pure planner. Defaults to ``scripts.capture_hydration.plan_evidence_publication``."""
    def __call__(self, *, playwright_raws: Sequence[dict], lighthouse_raws: Sequence[dict],
                 manifest_snapshot: dict, legacy_hydration_metadata: dict) -> dict: ...


class EvidencePublisher(Protocol):
    """Injectable atomic filesystem publisher (the SOLE writer). Defaults to
    ``scripts.capture_hydration.publish_evidence_atomic``."""
    def __call__(self, plan: dict, target_dir: Path) -> None: ...


def _default_evidence_planner(*, playwright_raws, lighthouse_raws,
                              manifest_snapshot, legacy_hydration_metadata):
    from scripts import capture_hydration as _ch
    return _ch.plan_evidence_publication(playwright_raws=playwright_raws, lighthouse_raws=lighthouse_raws,
                                          manifest_snapshot=manifest_snapshot,
                                          legacy_hydration_metadata=legacy_hydration_metadata)


def _default_evidence_publisher(plan, target_dir):
    from scripts import capture_hydration as _ch
    return _ch.publish_evidence_atomic(plan, target_dir)


def run_legacy_orchestration(
        *,
        host: str, port: int, cwd: Path, target_url: str, route: str, captured_at: str,
        spawn: LifecycleSpawn, probe: HealthProbe,
        collector: PlaywrightCollector, bridge: LhrBridge,
        manifest_provider: ManifestSnapshotProvider, publisher_target_dir: Path,
        planner: Optional[EvidencePlanner] = None, publisher: Optional[EvidencePublisher] = None,
        iterations: int = COMPOSITION_ITERATIONS,
        health_path: str = DEFAULT_HEALTH_PATH,
        health_timeout_s: float = DEFAULT_HEALTH_TIMEOUT_S,
        health_interval_s: float = DEFAULT_HEALTH_INTERVAL_S,
        terminate_grace_s: float = DEFAULT_TERMINATE_GRACE_S,
) -> dict:
    """Compose the full G5 legacy-infrastructure pipeline against ONE identical
    controlled URL. Order: spawn+health → 10 PW samples → derive hydration →
    bridge ×10 → manifest snapshot → pure planner → atomic publisher. On any
    failure (lifecycle, collector, bridge, schema, count, planner, publisher)
    planning and publication are SKIPPED and the failure is recorded. The
    lifecycle is ALWAYS reaped. No G5-pass / candidate verdict is emitted.
    """
    if iterations != COMPOSITION_ITERATIONS:
        raise ValueError(f'iterations must be {COMPOSITION_ITERATIONS} (G5 contract); got {iterations!r}')
    if not target_url:
        raise ValueError('target_url must be a non-empty string')
    actual_planner = planner or _default_evidence_planner
    actual_publisher = publisher or _default_evidence_publisher
    result = {'schema': LEGACY_COMPOSITION_SCHEMA, 'captured_at': captured_at, 'target_url': target_url,
              'route': route, 'iterations': iterations, 'playwright_samples_count': 0,
              'lighthouse_envelopes_count': 0, 'published': False, 'failure': None}
    try:
        with run_legacy_lifecycle(
            spawn=spawn, probe=probe, host=host, port=port, cwd=cwd,
            health_path=health_path, health_timeout_s=health_timeout_s,
            health_interval_s=health_interval_s, terminate_grace_s=terminate_grace_s,
):
            pw_envelope = collector(target_url=target_url)
            if pw_envelope.get('schema') != LEGACY_PW_SCHEMA:
                result['failure'] = f'playwright envelope schema mismatch: expected {LEGACY_PW_SCHEMA!r}, got {pw_envelope.get("schema")!r}'
                return result
            pw_samples = pw_envelope.get('samples')
            if not isinstance(pw_samples, list) or len(pw_samples) != COMPOSITION_ITERATIONS:
                actual = (len(pw_samples) if isinstance(pw_samples, list)
                          else f'non-list {type(pw_samples).__name__}')
                result['failure'] = f'playwright samples count mismatch: expected {COMPOSITION_ITERATIONS}, got {actual}'
                return result
            result['playwright_samples_count'] = len(pw_samples)
            result['playwright_provenance'] = pw_envelope.get('provenance')
            hydration_meta = derive_legacy_hydration_metadata(
                pw_samples, captured_at=captured_at, route=route)
            result['hydration_metadata'] = hydration_meta
            lh_envelopes: list[dict] = []
            for _ in range(COMPOSITION_ITERATIONS):
                env = bridge(target_url)
                if env.get('schema') != LEGACY_LH_BRIDGE_SCHEMA:
                    result['failure'] = f'bridge envelope schema mismatch: expected {LEGACY_LH_BRIDGE_SCHEMA!r}, got {env.get("schema")!r}'
                    return result
                if env.get('url') != target_url:
                    result['failure'] = f'bridge envelope url mismatch: expected {target_url!r}, got {env.get("url")!r}'
                    return result
                if not isinstance(env.get('lhr'), dict):
                    result['failure'] = (f'bridge envelope lhr is not a dict: {type(env.get("lhr")).__name__}')
                    return result
                lh_envelopes.append(env)
            result['lighthouse_envelopes_count'] = len(lh_envelopes)
            result['lighthouse_envelopes'] = lh_envelopes
            result['lighthouse_provenance'] = [e.get('provenance') for e in lh_envelopes]
            manifest_snapshot = manifest_provider()
            plan = actual_planner(playwright_raws=pw_samples,
                                  lighthouse_raws=[e['lhr'] for e in lh_envelopes],
                                  manifest_snapshot=manifest_snapshot,
                                  legacy_hydration_metadata=hydration_meta)
            result['plan'] = plan
            actual_publisher(plan, publisher_target_dir)
            result['published'] = True
    except Exception as e:
        result['failure'] = f'{type(e).__name__}: {e}'
    return result
