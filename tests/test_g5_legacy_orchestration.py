from __future__ import annotations
import subprocess
import time
from pathlib import Path
from typing import Sequence
import pytest
import scripts.orchestrate_g5_legacy as og
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / 'scripts' / 'orchestrate_g5_legacy.py'

class FakeProcess:
    """State: fresh → reap returns 0; stubborn raises TimeoutExpired
    until kill() resets to -9. Records every terminate/wait/kill call."""

    def __init__(self, *, pid=4321, reap=True, terminate_raises=False):
        self.pid: int = pid
        self.argv: Sequence[str] = ()
        self.returncode: int | None = None
        self.alive: bool = True
        self.terminate_calls: list[int] = []
        self.wait_calls: list[float] = []
        self.kill_calls: list[int] = []
        self._reap = reap
        self._killed = False
        self._terminate_raises = terminate_raises

    def terminate(self) -> None:
        self.terminate_calls.append(1)
        if self._terminate_raises:
            raise OSError('synthetic terminate failure')
        if self._reap:
            self.returncode, self.alive = (0, False)

    def wait(self, timeout_s: float) -> int:
        self.wait_calls.append(timeout_s)
        if self.alive and (not self._killed):
            raise subprocess.TimeoutExpired(cmd='fake', timeout=timeout_s)
        return self.returncode if self.returncode is not None else -9

    def kill(self) -> None:
        self.kill_calls.append(1)
        self._killed = True
        self.returncode, self.alive = (-9, False)

class FakeSpawn:

    def __init__(self, *, process=None, raises=None):
        self.process = process or FakeProcess()
        self.raises = raises
        self.calls: list[tuple[tuple[str, ...], Path]] = []

    def __call__(self, argv: Sequence[str], *, cwd: Path) -> og.SubprocessHandle:
        self.calls.append((tuple(argv), cwd))
        if self.raises is not None:
            raise self.raises
        self.process.argv = tuple(argv)
        return self.process

class FakeProbe:

    def __init__(self, *, results=(True,)):
        self.results = list(results)
        self.calls: list[tuple[str, int, str]] = []

    def __call__(self, host: str, port: int, path: str) -> bool:
        self.calls.append((host, port, path))
        return self.results.pop(0) if self.results else False

def _ten_samples():
    """10 samples with hand-computed medians: fps→55.0, fcps→155.0,
    dcls→60.0, waits→5.5, interactive(=dcl+wait)→65.5."""
    return [{'iteration': i, 'captured_at': f'2026-09-01T00:00:0{i % 10}Z', 'navigation': {'response_start_ms': float(10 + 10 * i), 'dom_content_loaded_ms': float(15 + 10 * i), 'load_event_ms': float(20 + 10 * i), 'redirect_count': 0, 'status': 200}, 'paint': {'first_paint_ms': float(10 + 10 * i), 'first_contentful_paint_ms': float(110 + 10 * i)}, 'dom_marker': {'selector': '#tree-view[data-state="ready"]', 'found': True, 'count': 1, 'first_text': 'ready', 'wait_ms': float(1 + i)}, 'console': []} for i in range(10)]

def test_module_surface_constants_and_shebang():
    for name in ('LEGACY_ASGI_APP_TARGET', 'DEFAULT_HEALTH_PATH', 'DEFAULT_HOST', 'DEFAULT_HEALTH_TIMEOUT_S', 'DEFAULT_TERMINATE_GRACE_S', 'LEGACY_HYDRATION_SCHEMA', 'SubprocessHandle', 'LifecycleSpawn', 'HealthProbe', 'spawn_legacy_subprocess', 'wait_for_health', 'terminate_legacy_subprocess', 'run_legacy_lifecycle', 'derive_legacy_hydration_metadata'):
        assert hasattr(og, name), f'missing public symbol: {name}'
    assert og.LEGACY_ASGI_APP_TARGET == 'tools.g3-legacy-fixture.scripts.g5_legacy_asgi:app'
    assert og.LEGACY_HYDRATION_SCHEMA == 'taxa.g5-orchestrator.legacy-hydration/1'
    text = SCRIPT.read_text(encoding='utf-8')
    assert SCRIPT.is_file() and text.startswith('#!/usr/bin/env python')
    assert '__main__' not in text, 'child A must not ship a full orchestration entry point; child B composes spawn + probe + capture + planner + publisher'

def test_spawn_builds_exact_uvicorn_argv():
    fake = FakeSpawn()
    handle = og.spawn_legacy_subprocess(spawn=fake, host='127.0.0.1', port=8765, cwd=REPO_ROOT)
    argv, cwd = fake.calls[0]
    assert argv == ('uvicorn', og.LEGACY_ASGI_APP_TARGET, '--host', '127.0.0.1', '--port', '8765', '--log-level', 'warning')
    assert cwd == REPO_ROOT and handle.pid == 4321

def test_spawn_propagates_spawn_failure_verbatim():
    fake = FakeSpawn(raises=FileNotFoundError(2, 'uvicorn not found'))
    with pytest.raises(FileNotFoundError, match='uvicorn not found'):
        og.spawn_legacy_subprocess(spawn=fake, host='127.0.0.1', port=8765, cwd=REPO_ROOT)

@pytest.mark.parametrize('results,expected_calls', [((True,), 1), ((False, False, True), 3)])
def test_wait_for_health_returns_after_ready_probe(results, expected_calls):
    probe = FakeProbe(results=list(results))
    og.wait_for_health(probe=probe, host='127.0.0.1', port=8765, path='/api/health', timeout_s=5.0, interval_s=0.001)
    assert len(probe.calls) == expected_calls

def test_wait_for_health_raises_on_timeout_without_blocking_past_budget():
    probe = FakeProbe(results=[False, False, False])
    t0 = time.monotonic()
    with pytest.raises(TimeoutError, match='health readiness'):
        og.wait_for_health(probe=probe, host='127.0.0.1', port=8765, path='/api/health', timeout_s=0.05, interval_s=0.01)
    assert time.monotonic() - t0 < 1.0

@pytest.mark.parametrize('scenario,expected_rc,exp_t,exp_k,exp_w_min', [('clean_reap', 0, 1, 0, 1), ('stubborn_escalates_to_kill', -9, 1, 1, 2), ('terminate_raises_escalates_to_kill', -9, 1, 1, 1), ('already_reaped_idempotent_noop', 0, 0, 0, 0)])
def test_terminate_legacy_subprocess_scenarios(scenario, expected_rc, exp_t, exp_k, exp_w_min):
    if scenario == 'clean_reap':
        proc = FakeProcess(reap=True)
    elif scenario == 'stubborn_escalates_to_kill':
        proc = FakeProcess(reap=False)
    elif scenario == 'terminate_raises_escalates_to_kill':
        proc = FakeProcess(reap=False, terminate_raises=True)
    else:
        proc = FakeProcess(reap=True)
        proc.returncode = 0
    assert og.terminate_legacy_subprocess(proc, grace_s=0.05) == expected_rc
    assert len(proc.terminate_calls) == exp_t
    assert len(proc.kill_calls) == exp_k
    assert len(proc.wait_calls) >= exp_w_min

@pytest.mark.parametrize('probe_results,user_raises,health_to,expect_yield', [((True,), False, 2.0, True), ((True,), True, 2.0, True), ((False, False, False), False, 0.05, False)])
def test_run_lifecycle_always_terminates_on_exit(probe_results, user_raises, health_to, expect_yield):
    spawn = FakeSpawn()
    probe = FakeProbe(results=list(probe_results))
    ctx = og.run_legacy_lifecycle(spawn=spawn, probe=probe, host='127.0.0.1', port=8765, cwd=REPO_ROOT, health_timeout_s=health_to, health_interval_s=0.001, terminate_grace_s=0.5)
    if expect_yield:
        with ctx as handle:
            assert handle.pid == 4321 and probe.calls
            if user_raises:
                with pytest.raises(RuntimeError, match='collector blew up'):
                    raise RuntimeError('collector blew up')
    else:
        with pytest.raises(TimeoutError):
            with ctx:
                pytest.fail('must not enter with-body when health times out')
    assert spawn.process.terminate_calls == [1]

def test_derive_requires_exactly_ten_samples():
    samples = _ten_samples()
    for bad in ([], samples[:1], samples[:9], samples + [samples[0]]):
        with pytest.raises(ValueError, match='exactly 10'):
            og.derive_legacy_hydration_metadata(bad, captured_at='2026-09-01T00:00:00Z', route='/')

def test_derive_validates_sample_shape_before_any_partial_derivation():
    samples = _ten_samples()
    for missing in ('paint', 'navigation', 'dom_marker', 'console'):
        broken = [dict(s) for s in samples]
        broken[3].pop(missing)
        with pytest.raises(ValueError, match=f"missing required key '{missing}'"):
            og.derive_legacy_hydration_metadata(broken, captured_at='2026-09-01T00:00:00Z', route='/')

def test_derive_computes_correct_medians_from_hand_built_samples():
    meta = og.derive_legacy_hydration_metadata(_ten_samples(), captured_at='2026-09-01T00:00:00Z', route='/')
    assert meta['server_shell']['first_paint_ms'] == 55.0
    assert meta['server_shell']['dom_content_loaded_ms'] == 60.0
    assert meta['client_render']['tree_first_paint_ms'] == 155.0
    assert meta['client_render']['tree_first_interactive_ms'] == 65.5
    assert meta['readiness_wait_ms'] == 5.5

def test_derive_preserves_verbatim_warning_records_with_provenance():
    samples = _ten_samples()
    samples[1]['console'] = [{'type': 'warning', 'text': 'hydration mismatch'}]
    samples[3]['console'] = [{'type': 'warning', 'text': 'deprecated keymap'}]
    samples[7]['console'] = [{'type': 'warning', 'text': 'first warning'}, {'type': 'error', 'text': 'second warning'}]
    meta = og.derive_legacy_hydration_metadata(samples, captured_at='2026-09-01T00:00:00Z', route='/')
    assert meta['console_warnings'] == [{'sample': 1, 'iteration': 1, 'type': 'warning', 'text': 'hydration mismatch'}, {'sample': 3, 'iteration': 3, 'type': 'warning', 'text': 'deprecated keymap'}, {'sample': 7, 'iteration': 7, 'type': 'warning', 'text': 'first warning'}, {'sample': 7, 'iteration': 7, 'type': 'error', 'text': 'second warning'}]

def test_derive_preserves_negative_wait_ms_verbatim():
    samples = _ten_samples()
    for i in (0, 2, 4, 6, 8):
        samples[i]['dom_marker']['wait_ms'] = -1.0
    meta = og.derive_legacy_hydration_metadata(samples, captured_at='2026-09-01T00:00:00Z', route='/')
    assert meta['readiness_wait_ms'] == 0.5
    assert meta['client_render']['tree_first_interactive_ms'] == 62.5
