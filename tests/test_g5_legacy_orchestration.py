from __future__ import annotations
import subprocess
import time
from pathlib import Path
from typing import Sequence
import pytest
import scripts.orchestrate_g5_legacy as og
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / 'scripts' / 'orchestrate_g5_legacy.py'

# Canonical schemas and ports used across composition tests.
CONTROLLED_URL = 'http://127.0.0.1:8765/'
PW_SCHEMA = 'taxa.g5-capture.legacy/1'
LH_BRIDGE_SCHEMA = 'taxa.g5-raw-lhr.envelope/1'
PUB_SCHEMA = 'taxa.g5-publication.evidence-manifest/1'
MANIFEST_SCHEMA = 'taxa.g4-capture.manifest/1'
PROVENANCE_PW_SCHEMA = 'taxa.g5-capture.legacy-provenance/1'
PROVENANCE_LH_SCHEMA = 'taxa.g4-capture.provenance/1'

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

# ===========================================================================
# G5 composition child B — injectable run function composing lifecycle +
# collector + Node LHR-bridge subprocess seam + metadata derivation + pure
# planner + atomic publisher against ONE identical controlled URL. Always
# reaps the lifecycle; skips plan/publish on any failure; publisher is the
# SOLE filesystem writer. No G5-pass / candidate verdict. Fully hermetic.
# ===========================================================================

class _PhaseRecorder:
    """Tiny mixin: appends ``(phase, *payload)`` to ``log`` when set."""
    def __init__(self, *, log=None):
        self.calls: list = []
        self._log = log
    def _phase(self, phase, *payload):
        if self._log is not None:
            self._log.append((phase, *payload))

class _FakeCollector(_PhaseRecorder):
    def __init__(self, *, envelope=None, raises=None, log=None):
        super().__init__(log=log)
        self.envelope_override = envelope
        self.raises = raises
    def __call__(self, *, target_url):
        self.calls.append(target_url)
        self._phase('collector', target_url)
        if self.raises is not None:
            raise self.raises
        if self.envelope_override is not None:
            return self.envelope_override
        return {'schema': PW_SCHEMA, 'target_url': target_url, 'iterations': 10,
                'samples': _ten_samples(),
                'provenance': {'schema': PROVENANCE_PW_SCHEMA, 'chromium': {'version': 'fake-cr'},
                               'playwright': {'version': 'fake-pw'},
                               'target_url': target_url, 'iterations': 10}}

class _FakeBridge(_PhaseRecorder):
    def __init__(self, *, envelopes=None, raises=None, url_mismatch=False,
                 schema_mismatch=False, bad_lhr=False, log=None):
        super().__init__(log=log)
        self.envelopes_override = envelopes
        self.raises = raises
        self.url_mismatch = url_mismatch
        self.schema_mismatch = schema_mismatch
        self.bad_lhr = bad_lhr
    def __call__(self, url):
        self.calls.append(url)
        self._phase('bridge', url)
        if self.raises is not None:
            raise self.raises
        i = len(self.calls) - 1
        if self.envelopes_override is not None:
            return self.envelopes_override[i]
        u = url if not self.url_mismatch else 'http://wrong/'
        lhr = 'not-a-dict' if self.bad_lhr else {'lighthouseVersion': '12.2.1', 'finalUrl': u, 'iterations': i}
        return {'schema': 'wrong/1' if self.schema_mismatch else LH_BRIDGE_SCHEMA, 'url': u, 'lhr': lhr,
                'provenance': {'schema': PROVENANCE_LH_SCHEMA, 'lighthouseVersion': '12.2.1'}}

class _FakeManifestProvider(_PhaseRecorder):
    def __init__(self, *, raises=None, log=None):
        super().__init__(log=log)
        self.snapshot = {'schema': MANIFEST_SCHEMA, 'entries': [{
            'url': CONTROLLED_URL + 'index.html', 'path': 'index.html',
            'expectedContentSha256': 'f' * 64, 'expectedStatus': 200,
            'expectedDOMMarker': 'data-testid="g4-probe-marker"'}]}
        self.raises = raises
    def __call__(self):
        self.calls.append(None)
        self._phase('manifest', None)
        if self.raises is not None:
            raise self.raises
        return self.snapshot

class _FakePlanner(_PhaseRecorder):
    def __init__(self, *, raises=None, log=None):
        super().__init__(log=log)
        self.plan = {'schema': PUB_SCHEMA, 'files': []}
        self.raises = raises
    def __call__(self, *, playwright_raws, lighthouse_raws, manifest_snapshot,
                 legacy_hydration_metadata):
        self.calls.append({'pw': list(playwright_raws), 'lh': list(lighthouse_raws),
                           'ms': manifest_snapshot, 'hm': legacy_hydration_metadata})
        self._phase('planner', len(playwright_raws), len(lighthouse_raws))
        if self.raises is not None:
            raise self.raises
        return self.plan

class _FakePublisher(_PhaseRecorder):
    def __init__(self, *, raises=None, log=None):
        super().__init__(log=log)
        self.raises = raises
    def __call__(self, plan, target_dir):
        self.calls.append((plan, target_dir))
        self._phase('publish', target_dir)
        if self.raises is not None:
            raise self.raises

def _seams(*, raises_collector=None, raises_bridge=None, raises_manifest=None,
           raises_planner=None, raises_publisher=None, pw_envelope=None, bridge_envelopes=None,
           bridge_url_mismatch=False, bridge_schema_mismatch=False, bridge_bad_lhr=False,
           probe_results=(True,), log=None):
    return {'spawn': FakeSpawn(), 'probe': FakeProbe(results=list(probe_results)),
            'collector': _FakeCollector(envelope=pw_envelope, raises=raises_collector, log=log),
            'bridge': _FakeBridge(envelopes=bridge_envelopes, raises=raises_bridge,
                                  url_mismatch=bridge_url_mismatch, schema_mismatch=bridge_schema_mismatch,
                                  bad_lhr=bridge_bad_lhr, log=log),
            'manifest_provider': _FakeManifestProvider(raises=raises_manifest, log=log),
            'planner': _FakePlanner(raises=raises_planner, log=log),
            'publisher': _FakePublisher(raises=raises_publisher, log=log)}


def _run(seams, *, tmp_path, target_url=CONTROLLED_URL, route='/',
         captured_at='2026-09-01T00:00:00Z', iterations=10, **kwargs):
    return og.run_legacy_orchestration(
        host='127.0.0.1', port=8765, cwd=REPO_ROOT, target_url=target_url, route=route, captured_at=captured_at,
        spawn=seams['spawn'], probe=seams['probe'], collector=seams['collector'], bridge=seams['bridge'],
        manifest_provider=seams['manifest_provider'], publisher_target_dir=tmp_path / 'evidence',
        planner=seams['planner'], publisher=seams['publisher'], iterations=iterations,
        health_interval_s=0.001, terminate_grace_s=0.05, **kwargs)


def test_composition_module_surface_and_library_only():
    for name in ('LEGACY_COMPOSITION_SCHEMA', 'LEGACY_PW_SCHEMA',
                 'LEGACY_LH_BRIDGE_SCHEMA', 'COMPOSITION_ITERATIONS',
                 'PlaywrightCollector', 'LhrBridge', 'ManifestSnapshotProvider',
                 'EvidencePlanner', 'EvidencePublisher', 'run_legacy_orchestration'):
        assert hasattr(og, name), f'missing public symbol: {name}'
    assert og.LEGACY_COMPOSITION_SCHEMA == 'taxa.g5-orchestrator.composition/1'
    assert og.LEGACY_PW_SCHEMA == PW_SCHEMA
    assert og.LEGACY_LH_BRIDGE_SCHEMA == LH_BRIDGE_SCHEMA
    assert og.COMPOSITION_ITERATIONS == 10
    assert '__main__' not in SCRIPT.read_text(encoding='utf-8'), \
        'composition child stays library-only (no CLI)'

def test_composition_happy_path_full_ordering_and_identical_url(tmp_path):
    log: list = []
    seams = _seams(log=log)
    result = _run(seams, tmp_path=tmp_path)
    assert result['failure'] is None and result['published'] is True
    assert result['playwright_samples_count'] == 10
    assert result['lighthouse_envelopes_count'] == 10
    # Identical controlled URL everywhere.
    assert seams['collector'].calls == [CONTROLLED_URL]
    assert seams['bridge'].calls == [CONTROLLED_URL] * 10
    assert len(seams['manifest_provider'].calls) == 1
    # Planner invoked once with all four canonical inputs.
    assert len(seams['planner'].calls) == 1
    pc = seams['planner'].calls[0]
    assert len(pc['pw']) == 10 and len(pc['lh']) == 10
    assert pc['ms']['schema'] == MANIFEST_SCHEMA
    assert pc['hm']['schema'] == og.LEGACY_HYDRATION_SCHEMA
    # Publisher invoked once with the planner's plan + target dir.
    assert len(seams['publisher'].calls) == 1
    pub_plan, pub_dir = seams['publisher'].calls[0]
    assert pub_plan['schema'] == PUB_SCHEMA and pub_dir == tmp_path / 'evidence'
    # Strict ordering: collector → bridge ×10 → manifest → planner → publish.
    phases = [e[0] for e in log]
    assert phases == (['collector'] + ['bridge'] * 10 + ['manifest', 'planner', 'publish'])
    assert seams['spawn'].process.terminate_calls == [1]


def test_composition_forwards_metadata_and_provenance(tmp_path):
    seams = _seams()
    result = _run(seams, tmp_path=tmp_path,
                  captured_at='2026-09-01T12:34:56Z', route='/index.html')
    pc = seams['planner'].calls[0]
    for i, s in enumerate(pc['pw']):
        assert s['iteration'] == i and 'captured_at' in s
        for k in ('navigation', 'paint', 'dom_marker', 'console'):
            assert k in s
    assert len(pc['lh']) == 10 and all(isinstance(x, dict) for x in pc['lh'])
    assert pc['hm']['captured_at'] == '2026-09-01T12:34:56Z'
    assert pc['hm']['route'] == '/index.html' and pc['hm']['build'] == 'legacy'
    assert result['playwright_provenance']['schema'] == PROVENANCE_PW_SCHEMA
    assert len(result['lighthouse_provenance']) == 10
    assert result['lighthouse_provenance'][0]['schema'] == PROVENANCE_LH_SCHEMA


@pytest.mark.parametrize('failure_kw,failure_fragment', [
    ({'raises_collector': RuntimeError('synthetic collector fail')}, 'collector fail'),
    ({'raises_bridge': RuntimeError('synthetic bridge fail')}, 'bridge fail'),
    ({'raises_manifest': RuntimeError('synthetic manifest fail')}, 'manifest fail'),
    ({'pw_envelope': {'schema': 'wrong/1', 'samples': _ten_samples(), 'target_url': CONTROLLED_URL,
                      'iterations': 10, 'provenance': {'schema': PROVENANCE_PW_SCHEMA}}},
     'playwright envelope schema mismatch'),
    ({'pw_envelope': {'schema': PW_SCHEMA, 'samples': _ten_samples()[:7], 'target_url': CONTROLLED_URL,
                      'iterations': 7, 'provenance': {'schema': PROVENANCE_PW_SCHEMA}}},
     'count mismatch'),
    ({'bridge_schema_mismatch': True}, 'bridge envelope schema mismatch'),
    ({'bridge_url_mismatch': True}, 'bridge envelope url mismatch'),
])
def test_composition_skips_planner_and_publisher_on_step_failure(
        tmp_path, failure_kw, failure_fragment):
    seams = _seams(**failure_kw)
    result = _run(seams, tmp_path=tmp_path)
    assert seams['planner'].calls == [] and seams['publisher'].calls == []
    assert result['published'] is False
    assert result['failure'] is not None and failure_fragment in result['failure']
    assert seams['spawn'].process.terminate_calls == [1]


@pytest.mark.parametrize('failure_kw,failure_fragment', [
    ({'raises_planner': ValueError('synthetic planner fail')}, 'planner fail'),
    ({'raises_publisher': OSError('synthetic publisher fail')}, 'publisher fail'),
])
def test_composition_skip_or_record_failure_at_writer(tmp_path, failure_kw, failure_fragment):
    seams = _seams(**failure_kw)
    result = _run(seams, tmp_path=tmp_path)
    assert result['published'] is False
    assert result['failure'] is not None and failure_fragment in result['failure']
    assert seams['spawn'].process.terminate_calls == [1]
    assert seams['planner'].calls
    if 'publisher' in failure_fragment:
        assert len(seams['publisher'].calls) == 1
    else:
        assert seams['publisher'].calls == []


def test_composition_always_reaps_lifecycle_on_lifecycle_failure(tmp_path):
    seams = _seams(probe_results=[False, False, False])
    result = _run(seams, tmp_path=tmp_path, health_timeout_s=0.05)
    assert seams['collector'].calls == seams['bridge'].calls == []
    assert seams['planner'].calls == seams['publisher'].calls == []
    assert result['published'] is False and result['failure'] is not None
    assert seams['spawn'].process.terminate_calls == [1]


def test_composition_rejects_non_ten_iterations_and_empty_url(tmp_path):
    seams = _seams()
    with pytest.raises(ValueError, match='10'):
        _run(seams, tmp_path=tmp_path, iterations=5)
    with pytest.raises(ValueError, match='target_url'):
        _run(seams, tmp_path=tmp_path, target_url='')


def test_composition_publisher_is_sole_writer_and_no_g5_pass_in_envelope(tmp_path):
        seams = _seams()
        before = {p.name for p in tmp_path.iterdir()}
        result = _run(seams, tmp_path=tmp_path)
        new_names = {p.name for p in tmp_path.iterdir()} - before
        assert new_names == set(), f'composition leaked entries: {new_names!r}'
        pub_plan, pub_dir = seams['publisher'].calls[0]
        assert pub_dir == tmp_path / 'evidence' and pub_plan['schema'] == PUB_SCHEMA
        for forbidden in ('passed', 'pass', 'candidate', 'verdict', 'approved',
                          'equivalent', 'parity', 'comparison', 'winner',
                          'baseline_diff'):
            assert forbidden not in result
        # Default planner seam resolves to ``scripts.capture_hydration`` at
        # call-time (no top-level import keeps the composition child decoupled
        # from the capture module's CLI surface).
        import scripts.capture_hydration as ch
        plan = og._default_evidence_planner(
            playwright_raws=_ten_samples(), lighthouse_raws=[{'lighthouseVersion': '12.2.1'}] * 10,
            manifest_snapshot={'schema': MANIFEST_SCHEMA, 'entries': []},
            legacy_hydration_metadata={'captured_at': 't', 'build': 'legacy', 'route': '/',
                                       'server_shell': {}, 'client_render': {}, 'console_warnings': []})
        assert plan['schema'] == ch.PUBLICATION_SCHEMA
