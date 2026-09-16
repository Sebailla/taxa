"""Hermetic strict-TDD tests for child B (orchestration entry point) in
``scripts/orchestrate_g5_legacy.py`` — FIRST SLICE.

Covers the essential hermetic contract: lifecycle adapter composition,
success path, cleanup-on-error, and primary error taxonomy. Deep bridge /
provenance / route / default-bridge-factory tests AND the foundational
sanity tests (module surface, error hierarchy, descriptor shape, script
budget guard) are deferred to the second follow-up slice without
deleting coverage from the overall plan.
"""
from __future__ import annotations
from pathlib import Path
import pytest
import scripts.orchestrate_g5_legacy as og


BASE = "http://127.0.0.1:8765"


def _pw(i=0, *, fp=80.0, dcl=100.0, wait_ms=30.0, le=200.0):
    return {
        "iteration": i, "captured_at": "t0",
        "navigation": {"response_start_ms": 60.0, "dom_content_loaded_ms": dcl,
                        "load_event_ms": le, "redirect_count": 0, "status": 200},
        "paint": {"first_paint_ms": fp, "first_contentful_paint_ms": 110.0},
        "dom_marker": {"selector": "#tree-view[data-state=\"ready\"]",
                        "found": True, "count": 1, "first_text": f"r{i}",
                        "wait_ms": wait_ms},
        "console": [],
    }


def _lhr(_=0):
    return {
        "schema": "taxa.g5-raw-lhr.envelope/1", "url": f"{BASE}/",
        "lhr": {"finalUrl": f"{BASE}/", "lighthouseVersion": "12.2.1",
                "userAgent": "...Chrome/120.0.6099.71",
                "fetchTime": "2025-01-01T00:00:00Z", "runWarnings": [],
                "categories": {"performance": {"score": 0.95}}, "audits": {}},
        "provenance": {"schema": "taxa.g4-capture.provenance/1",
                        "lighthouseVersion": "12.2.1",
                        "chromeVersion": "120.0.6099.71",
                        "nodeVersion": "v26.8.1"},
    }


def _collector(samples=None, *, raising=None, kw=None):
    def f(*, target_url, iterations, dom_marker_selector):
        if kw is not None:
            kw.update(target_url=target_url, iterations=iterations,
                      dom_marker_selector=dom_marker_selector)
        if raising is not None:
            raise raising
        s = list(samples) if samples else [_pw(i) for i in range(iterations)]
        return {"schema": "taxa.g5-capture.legacy/1", "captured_at": "t0",
                "target_url": target_url, "iterations": iterations,
                "dom_marker_selector": dom_marker_selector,
                "provenance": {"schema": "taxa.g5-capture.legacy-provenance/1"},
                "samples": s}
    return f


def _bridge(envelopes=None, *, raising=None, urls=None):
    log: list = []
    def f(url):
        log.append(url)
        if urls is not None:
            urls.append(url)
        if raising is not None:
            raise raising
        pool = envelopes or [_lhr()]
        return pool[min(len(log) - 1, len(pool) - 1)]
    return f


def _planner(*, raising=None, captured=None):
    def f(*, playwright_raws, lighthouse_raws, manifest_snapshot,
            legacy_hydration_metadata):
        if captured is not None:
            captured.update(pw=list(playwright_raws), lh=list(lighthouse_raws),
                             ms=dict(manifest_snapshot),
                             hm=dict(legacy_hydration_metadata))
        if raising is not None:
            raise raising
        return {"schema": "taxa.g5-publication.evidence-manifest/1",
                "files": [{"kind": "playwright", "path": "raw/playwright/iter-00.json",
                            "bytes": 100, "sha256": "0" * 64,
                            "canonical_json": "{}", "iteration": 0}]}
    return f


def _publisher(*, captured=None, raising=None):
    def f(plan, out_dir):
        if captured is not None:
            captured.update(plan=dict(plan), out_dir=str(out_dir))
        if raising is not None:
            raise raising
    return f


class FakeLC:
    """Lifecycle seam: Protocol-style duck-typed .start()/.stop()/.base_url."""
    def __init__(self, *, base_url=BASE, start_raises=None):
        self.base_url = base_url
        self.start_calls = 0
        self.stop_calls = 0
        self._sr = start_raises
    def start(self):
        self.start_calls += 1
        if self._sr is not None:
            raise self._sr
    def stop(self):
        self.stop_calls += 1


class _FakeProcess:
    def __init__(self, *, pid=4321):
        self.pid = pid
        self.argv = ()
        self.returncode = None
        self.alive = True
    def terminate(self):
        self.returncode, self.alive = (0, False)
    def wait(self, timeout_s):
        return 0
    def kill(self):
        self.returncode, self.alive = (-9, False)


class _FakeSpawn:
    def __init__(self, process=None):
        self.process = process or _FakeProcess()
        self.calls: list = []
    def __call__(self, argv, *, cwd):
        self.calls.append((tuple(argv), cwd))
        self.process.argv = tuple(argv)
        return self.process


class _FakeProbe:
    def __init__(self, *, results=(True,)):
        self.results = list(results)
        self.calls: list = []
    def __call__(self, host, port, path):
        self.calls.append((host, port, path))
        return self.results.pop(0) if self.results else False


def _run(out_dir, *, lc=None, coll=None, br=None, pl=None, pub=None,
           iterations=10, target_url=None, route=None):
    return og.run_orchestration(
        lifecycle=lc or FakeLC(),
        collector=coll or _collector(),
        bridge=br or _bridge(),
        planner=pl or _planner(),
        publisher=pub or _publisher(),
        target_url=target_url or f"{BASE}/",
        out_dir=out_dir, iterations=iterations, route=route,
    )


# ── Happy path / success ────────────────────────────────────────────────
def test_run_orchestration_happy_path_composes_all_seams(tmp_path):
    out = tmp_path / "out"
    pub: dict = {}
    ck: dict = {}
    urls: list = []
    lc = FakeLC()
    r = _run(out, lc=lc, coll=_collector(kw=ck), br=_bridge(urls=urls),
              pl=_planner(captured=pub), pub=_publisher(captured=pub))
    assert r["schema"] == og.ORCH_SCHEMA
    assert Path(r["out_dir"]) == out
    assert r["iterations"] == 10
    assert lc.start_calls == 1 and lc.stop_calls == 1
    assert pub["plan"]["schema"] == "taxa.g5-publication.evidence-manifest/1"
    assert Path(pub["out_dir"]) == out
    assert len(pub["pw"]) == 10 and len(pub["lh"]) == 10
    assert pub["ms"]["schema"] == "taxa.g5-orchestrator.manifest/1"
    assert len(pub["ms"]["entries"]) == 10
    # Collector + bridge contract: 10 calls, ONE identical URL.
    assert ck["target_url"] == f"{BASE}/" and ck["iterations"] == 10
    assert len(urls) == 10 and all(u == f"{BASE}/" for u in urls)


# ── Primary errors + cleanup ────────────────────────────────────────────
def test_collector_exception_skips_publication_and_reaps(tmp_path):
    pub: dict = {}
    lc = FakeLC()
    with pytest.raises(og.CollectorError, match="collector"):
        _run(tmp_path / "out", lc=lc,
              coll=_collector(raising=RuntimeError("boom")),
              pub=_publisher(captured=pub))
    assert pub == {} and lc.stop_calls == 1


def test_publisher_failure_still_reaps_lifecycle(tmp_path):
    lc = FakeLC()
    with pytest.raises(og.OrchestrationError, match="publisher"):
        _run(tmp_path / "out", lc=lc,
              pub=_publisher(raising=OSError("FS full")))
    assert lc.stop_calls == 1


def test_iterations_mismatch_rejects_before_lifecycle(tmp_path):
    lc = FakeLC()
    pub: dict = {}
    with pytest.raises(ValueError, match="iterations"):
        _run(tmp_path / "out", lc=lc, iterations=5, pub=_publisher(captured=pub))
    assert lc.start_calls == 0 and pub == {}


# ── LegacyLifecycleAdapter ──────────────────────────────────────────────
def test_legacy_lifecycle_adapter_composes_run_legacy_lifecycle(tmp_path):
    spawn = _FakeSpawn()
    probe = _FakeProbe(results=[True])
    lc = og.LegacyLifecycleAdapter(host="127.0.0.1", port=8123, cwd=tmp_path,
                                     spawn=spawn, probe=probe,
                                     health_timeout_s=2.0,
                                     health_interval_s=0.001,
                                     terminate_grace_s=0.5)
    assert lc.base_url == "http://127.0.0.1:8123"
    lc.start()
    try:
        assert spawn.calls and probe.calls
        argv, _ = spawn.calls[0]
        assert argv == ("uvicorn", og.LEGACY_ASGI_APP_TARGET,
                         "--host", "127.0.0.1", "--port", "8123",
                         "--log-level", "warning")
    finally:
        lc.stop()


def test_legacy_lifecycle_adapter_stop_is_idempotent(tmp_path):
    lc = og.LegacyLifecycleAdapter(host="127.0.0.1", port=8123, cwd=tmp_path,
                                     spawn=_FakeSpawn(),
                                     probe=_FakeProbe(results=[True]),
                                     health_timeout_s=2.0,
                                     health_interval_s=0.001,
                                     terminate_grace_s=0.5)
    lc.start()
    lc.stop()
    lc.stop()  # MUST NOT raise


def test_legacy_lifecycle_adapter_stop_without_start_is_safe(tmp_path):
    lc = og.LegacyLifecycleAdapter(host="127.0.0.1", port=8123, cwd=tmp_path,
                                     spawn=_FakeSpawn(),
                                     probe=_FakeProbe(results=[True]))
    lc.stop()  # MUST NOT raise
