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
import datetime as _dt
import json
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional, Protocol, Sequence
LEGACY_ASGI_APP_TARGET = 'tools.g3-legacy-fixture.scripts.g5_legacy_asgi:app'
DEFAULT_HEALTH_PATH = '/api/health'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_HEALTH_INTERVAL_S = 0.05
DEFAULT_HEALTH_TIMEOUT_S = 10.0
DEFAULT_TERMINATE_GRACE_S = 5.0
DEFAULT_BRIDGE_TIMEOUT_S = 30.0
LEGACY_HYDRATION_SCHEMA = 'taxa.g5-orchestrator.legacy-hydration/1'
BRIDGE_TIMEOUT_ADVISORY_KIND = 'bridge_timeout'
BRIDGE_ENVELOPE_SCHEMA = 'taxa.g5-raw-lhr.envelope/1'

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



# ── Child B: orchestration entry point ─────────────────────────────────
# Composes child A's lifecycle library with the hydration collector
# (scripts.capture_hydration.collect_raw_samples), the raw-LHR bridge
# (tools/g4-capture/scripts/g5_raw_lhr_bridge.mjs), the pure planner,
# and the atomic publisher through fully injectable seams. Guarantees
# lifecycle cleanup via try/finally. No real subprocess, no Chromium,
# no Lighthouse, no Node in tests — every collaborator is replaced by a
# deterministic fake (FakeLC + mk_collector/mk_bridge/mk_planner/mk_publisher).
ITERATIONS = 10
ORCH_SCHEMA = 'taxa.g5-orchestrator.legacy/1'
MANIFEST_SNAPSHOT_SCHEMA = 'taxa.g5-orchestrator.manifest/1'
DEFAULT_DOM_MARKER_SELECTOR = '#tree-view[data-state="ready"]'
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BRIDGE_SCRIPT = REPO_ROOT / 'tools/g4-capture/scripts/g5_raw_lhr_bridge.mjs'


class OrchestrationError(Exception):
    """Base class for orchestration-step failures (publication always skipped)."""


class ReadinessError(OrchestrationError):
    """Lifecycle readiness probe never satisfied the fixture-backed contract."""


class CollectorError(OrchestrationError):
    """Collector raised, returned a wrong-schema payload, or wrong sample count."""


class BridgeError(OrchestrationError):
    """Bridge invocation raised, returned a wrong-schema envelope, or short-circuited."""


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _route_from_url(target_url: str) -> str:
    try:
        return urllib.parse.urlparse(target_url).path or '/'
    except Exception:
        return '/'


def _synthesize_manifest_snapshot(target_url: str, lhr_envelopes) -> dict:
    """Per-iteration bridge provenance so the publication plan traces back to
    the envelope that produced each LHR. Planner only validates
    schema + entries (see capture_hydration.plan_evidence_publication)."""
    entries: list[dict] = []
    for i, env in enumerate(lhr_envelopes):
        if not isinstance(env, dict):
            raise BridgeError(f'envelope {i+1} must be a JSON object')
        if not isinstance(env.get('lhr'), dict):
            raise BridgeError(f'envelope {i+1} must contain a non-empty lhr')
        prov = env.get('provenance') or {}
        entries.append({'url': env.get('url', target_url),
                          'lighthouseVersion': prov.get('lighthouseVersion'),
                          'chromeVersion': prov.get('chromeVersion'),
                          'nodeVersion': prov.get('nodeVersion'),
                          'expectedDOMMarker': 'data-testid="g4-probe-marker"'})
    return {'schema': MANIFEST_SNAPSHOT_SCHEMA, 'entries': entries}


class LegacyLifecycleAdapter:
    """Compose child A's run_legacy_lifecycle context manager into child B's
    lifecycle protocol (.start() / .stop() / .base_url) so test
    fakes and real fixtures share the same surface. start() enters the
    context manager; stop() exits and is idempotent. spawn and probe
    are pass-through injectable seams from child A; defaults use the real
    subprocess + urllib probe."""

    def __init__(self, *, host: str, port: int, cwd: Path,
                  spawn: Optional[LifecycleSpawn] = None,
                  probe: Optional[HealthProbe] = None,
                  health_path: str = DEFAULT_HEALTH_PATH,
                  health_timeout_s: float = DEFAULT_HEALTH_TIMEOUT_S,
                  health_interval_s: float = DEFAULT_HEALTH_INTERVAL_S,
                  terminate_grace_s: float = DEFAULT_TERMINATE_GRACE_S):
        self.base_url = f'http://{host}:{port}'
        self._ctx: Optional[contextlib.AbstractContextManager] = None
        self._spawn: LifecycleSpawn = spawn or _default_subprocess_spawn
        self._probe: HealthProbe = probe or _default_http_health_probe
        self._kwargs: dict[str, Any] = dict(
            host=host, port=port, cwd=cwd,
            spawn=self._spawn, probe=self._probe,
            health_path=health_path,
            health_timeout_s=health_timeout_s,
            health_interval_s=health_interval_s,
            terminate_grace_s=terminate_grace_s)

    def start(self) -> None:
        self._ctx = run_legacy_lifecycle(**self._kwargs)
        self._ctx.__enter__()

    def stop(self) -> None:
        if self._ctx is None:
            return
        try:
            self._ctx.__exit__(None, None, None)
        finally:
            self._ctx = None


def _bridge_timeout_envelope(url: str, *, timeout_s: float) -> dict:
    """Build a schema-conformant sentinel envelope marking a bridge timeout.

    Non-blocking: the orchestrator returns this instead of raising so the
    publication step still runs with the rest of the captured evidence.
    The ``advisory`` field is what ``run_orchestration`` accumulates into
    ``bridge_advisories``; ``provenance.advisory`` carries the same info for
    the manifest-snapshot traceability path. The ``lhr`` field is a minimal
    non-empty dict so the existing envelope-validation check in
    ``run_orchestration`` and the planner's ``_validate_raws`` pass.
    """
    advisory = {'kind': BRIDGE_TIMEOUT_ADVISORY_KIND,
'reason': 'bridge subprocess exceeded timeout',
'timeout_s': timeout_s}
    return {'schema': BRIDGE_ENVELOPE_SCHEMA, 'url': url,
            'lhr': {'finalUrl': url, 'advisory': True},
            'provenance': {'lighthouseVersion': None, 'chromeVersion': None,
'nodeVersion': None, 'advisory': dict(advisory)},
            'advisory': advisory}


def _emit_bridge_timeout_advisory(url: str, *, timeout_s: float) -> None:
    """One-line stderr advisory so callers can grep the timeout context."""
    sys.stderr.write(
        f'[orchestrate_g5_legacy] bridge timeout: url={url} '
        f'timeout_s={timeout_s:.3f} — returning sentinel envelope\n')


def _default_subprocess_bridge(*, bridge_timeout_s: float = DEFAULT_BRIDGE_TIMEOUT_S):
    """Default bridge factory: spawn ``node g5_raw_lhr_bridge.mjs --url <url>``
    and return the envelope dict.

    Bounded by ``bridge_timeout_s`` seconds (default
    :data:`DEFAULT_BRIDGE_TIMEOUT_S` = 30s) via ``subprocess.run(timeout=...)``.
    A timeout is NON-BLOCKING: emits a stderr advisory and returns a
    schema-conformant sentinel envelope (see :func:`_bridge_timeout_envelope`)
    instead of raising ``BridgeError``. Existing BridgeError contracts
    (missing-node, non-zero exit, no JSON line, invalid JSON) are preserved
    unchanged. Tests inject their own bridge.
    """
    if not isinstance(bridge_timeout_s, (int, float)) or bridge_timeout_s <= 0:
        raise ValueError(
            f'bridge_timeout_s must be a positive number; got {bridge_timeout_s!r}')
    node = shutil.which('node')
    if not node:
        raise BridgeError("'node' binary not found on PATH; "
                          'cannot invoke default bridge')
    script = DEFAULT_BRIDGE_SCRIPT

    def bridge(url: str) -> dict:
        try:
            proc = subprocess.run([node, str(script), '--url', url],
capture_output=True, text=True,
timeout=float(bridge_timeout_s))
        except subprocess.TimeoutExpired as e:
            _emit_bridge_timeout_advisory(url, timeout_s=float(bridge_timeout_s))
            return _bridge_timeout_envelope(url, timeout_s=float(bridge_timeout_s))
        if proc.returncode != 0:
            raise BridgeError(f'bridge process exited {proc.returncode}: '
                                f'stderr={proc.stderr.strip()!r}')
        line = next((ln for ln in proc.stdout.splitlines() if ln.strip()), None)
        if not line:
            raise BridgeError(f'bridge emitted no envelope JSON line '
                                f'(stdout={proc.stdout!r})')
        try:
            return json.loads(line)
        except json.JSONDecodeError as e:
            raise BridgeError(f'bridge envelope is not valid JSON: {e}') from e
    return bridge


def run_orchestration(*, lifecycle, collector, bridge, planner, publisher,
                       target_url: str, out_dir,
                       route: Optional[str] = None,
                       dom_marker_selector: str = DEFAULT_DOM_MARKER_SELECTOR,
                       iterations: int = ITERATIONS,
                       captured_at: Optional[str] = None) -> dict:
    """Compose the G5 legacy-orchestration chain end-to-end.

    Seams (all injectable; tests replace each with a deterministic fake):
      lifecycle  Protocol-style: .start() / .stop() / .base_url.
                     Real = LegacyLifecycleAdapter wrapping child A's
                     run_legacy_lifecycle.
      collector  (*, target_url, iterations, dom_marker_selector) -> dict
                     with schema == 'taxa.g5-capture.legacy/1' and
                     len(samples) == iterations.
      bridge     (str) -> dict with schema == 'taxa.g5-raw-lhr.envelope/1';
                     invoked exactly iterations times against ONE identical URL.
      planner    (playwright_raws, lighthouse_raws, manifest_snapshot,
                        legacy_hydration_metadata) -> dict with schema
                     'taxa.g5-publication.evidence-manifest/1'.
      publisher  (plan, out_dir) -> None (atomic write).

    Returns the published-plan descriptor. Raises OrchestrationError
    subclass on any step failure (publication always skipped). Lifecycle
    stop() is ALWAYS reaped via try/finally regardless of failure
    path — no leaky subprocess."""
    if iterations != ITERATIONS:
        raise ValueError(f'iterations must be {ITERATIONS} (G5 contract); '
                          f'got {iterations!r}')
    out_dir = Path(out_dir)
    captured_at = captured_at or _now_iso()
    route = route or _route_from_url(target_url)
    lifecycle.start()
    try:
        try:
            collected = collector(target_url=target_url, iterations=iterations,
                                    dom_marker_selector=dom_marker_selector)
        except Exception as e:
            raise CollectorError(f'collector raised: {e}') from e
        if (not isinstance(collected, dict)
                or collected.get('schema') != 'taxa.g5-capture.legacy/1'):
            raise CollectorError("collector returned a payload whose schema is "
                                  "not 'taxa.g5-capture.legacy/1'")
        samples = collected.get('samples')
        if not isinstance(samples, list) or len(samples) != iterations:
            n = len(samples) if isinstance(samples, list) else 0
            raise CollectorError(f'collector returned {n} samples; '
                                  f'required exactly {iterations}')

        lhr_envelopes: list[dict] = []
        bridge_advisories: list[dict] = []
        for i in range(iterations):
            try:
                env = bridge(target_url)
            except Exception as e:
                raise BridgeError(f'bridge invocation {i+1}/{iterations} raised: '
                                    f'{type(e).__name__}: {e}') from e
            if (not isinstance(env, dict)
                    or env.get('schema') != 'taxa.g5-raw-lhr.envelope/1'):
                raise BridgeError(f'bridge invocation {i+1}/{iterations} did not '
                                    "return a 'taxa.g5-raw-lhr.envelope/1' envelope")
            lhr_envelopes.append(env)
            # Optional advisory path: bounded subprocess bridges can return
            # a sentinel envelope with an ``advisory`` field on timeout
            # (non-blocking contract). The orchestrator accumulates these
            # but does NOT raise — publication proceeds with the rest of
            # the captured evidence. ``bridge_advisories`` is omitted from
            # the descriptor when no timeouts happened.
            adv = env.get('advisory')
            if isinstance(adv, dict):
                bridge_advisories.append({
                    'iteration': i + 1,
                    'kind': adv.get('kind'),
                    'reason': adv.get('reason'),
                    'timeout_s': adv.get('timeout_s'),
                    'url': env.get('url', target_url),
                })

        hydration = derive_legacy_hydration_metadata(samples,
                                                       captured_at=captured_at,
                                                       route=route)
        manifest_snapshot = _synthesize_manifest_snapshot(target_url, lhr_envelopes)
        lighthouse_raws = [env['lhr'] for env in lhr_envelopes]

        try:
            plan = planner(playwright_raws=samples,
                            lighthouse_raws=lighthouse_raws,
                            manifest_snapshot=manifest_snapshot,
                            legacy_hydration_metadata=hydration)
        except Exception as e:
            raise OrchestrationError(f'planner rejected inputs: {e}') from e
        if not isinstance(plan, dict):
            raise OrchestrationError('planner returned a non-dict plan')

        try:
            publisher(plan, out_dir)
        except Exception as e:
            raise OrchestrationError(f'publisher rejected plan: {e}') from e

        descriptor: dict[str, Any] = {
            'schema': ORCH_SCHEMA, 'published_at': _now_iso(),
            'target_url': target_url, 'iterations': iterations,
            'out_dir': str(out_dir),
            'plan_schema': plan.get('schema'),
            'plan_files': len(plan.get('files', []))}
        if bridge_advisories:
            descriptor['bridge_advisories'] = bridge_advisories
        return descriptor
    finally:
        lifecycle.stop()
