"""Strict-TDD tests for scripts/capture_hydration.py (G5 raw Playwright
legacy collector). TEN browser samples, per-sample nav/paint/DOM-marker/
console + Chromium/Playwright/env provenance; in-memory + raw JSON;
fail-closed on iteration failure. No Lighthouse, no G5 launcher call,
no parity-reports emission. Hermetic via FakeBrowserAdapter.
"""
from __future__ import annotations

import ast
import contextlib
import functools
import hashlib
import http.server
import io
import json
import os
import re
import subprocess
import sys
import threading
import types
import urllib.error
from pathlib import Path
from typing import Self

import pytest

import scripts.capture_hydration as ch

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "capture_hydration.py"
TARGET_URL = "http://127.0.0.1:8765/"


class FakeBrowserAdapter:
    """Hermetic test double. Records `calls` for fail-closed assertions."""
    def __init__(self, *, raise_on=None, raise_message="synthetic iteration failure",
                 wait_ms: float = 0.0, found: bool = True, count: int = 1,
                 first_text: str | None = "x"):
        self._raise_on, self._raise_message = raise_on, raise_message
        self._wait_ms: float = wait_ms
        self._found: bool = found
        self._count: int = count
        self._first_text: str | None = first_text
        self.calls: list = []
    def chromium_provenance(self):
        return {"version": "fake-chromium-1.0", "executable_path": "/fake/chromium"}
    def playwright_provenance(self):
        return {"version": "fake-playwright-1.0"}
    def run_iteration(self, *, target_url, dom_marker_selector, iteration_index):
        self.calls.append((target_url, dom_marker_selector, iteration_index))
        if self._raise_on is not None and (iteration_index + 1) == self._raise_on:
            raise RuntimeError(self._raise_message)
        return {
            "iteration": iteration_index, "captured_at": "2026-01-01T00:00:00Z",
            "navigation": {"response_start_ms": 0.0, "dom_content_loaded_ms": 0.0,
                           "load_event_ms": 0.0, "redirect_count": 0, "status": 200},
            "paint": {"first_paint_ms": 0.0, "first_contentful_paint_ms": 0.0},
            "dom_marker": {"selector": dom_marker_selector, "found": self._found,
                           "count": self._count, "first_text": self._first_text,
                           "wait_ms": self._wait_ms},
            "console": [],
        }


# ---------------------------------------------------------------------------
# Strict Playwright sync-API fake — used to exercise the REAL
# PlaywrightBrowserAdapter (not the FakeBrowserAdapter above, which
# bypasses Playwright entirely and would never catch a lifecycle bug).
#
# `sync_playwright()` returns a `_PlaywrightContextManager`. The actual
# Playwright instance that carries `.chromium` only exists inside the
# `with sync_playwright() as p:` block. Accessing `.chromium` on the
# un-entered context manager raises AttributeError on the real API and
# a "LIFECYCLE VIOLATION" RuntimeError on this strict fake.
# ---------------------------------------------------------------------------


class _StrictPlaywrightCM:
    """Fake sync_playwright() context manager. Records every chromium
    access and RAISES if chromium is touched outside `__enter__` /
    `__exit__`. Captures `chromium_outside_accesses` for the test
    assertion that the adapter always enters the context first."""

    def __init__(self):
        self._active = False
        self.chromium_outside_accesses = 0

    def __enter__(self):
        self._active = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self._active = False
        return False

    @property
    def chromium(self):
        if not self._active:
            self.chromium_outside_accesses += 1
            raise RuntimeError(
                "LIFECYCLE VIOLATION: .chromium accessed outside the "
                "sync_playwright() context manager "
                "(sync_playwright() returns a context manager; "
                "chromium is only valid inside `with sync_playwright() as p:`)."
            )
        return _StrictChromium(self)


class _StrictChromium:
    def __init__(self, cm):
        self._cm = cm
        self.executable_path = "/fake/playwright/exec"

    def launch(self, headless=True):
        return _StrictBrowser(self._cm)


# Module-level list of pages created by the strict fake browser so
# tests can inspect registered route handlers AFTER run_iteration
# returns (the page is local to the run, but the registration order
# proves the safety boundary was armed before any request could fire).
_LAST_BROWSER_PAGES: list = []


class _StrictBrowser:
    def __init__(self, cm):
        self._cm = cm
        self._closed = False
        self.new_page_calls = 0

    @property
    def version(self):
        if not self._cm._active or self._closed:
            raise RuntimeError(
                "LIFECYCLE VIOLATION: browser.version accessed outside "
                "active sync_playwright() context or after close().")
        return "fake-chromium-v0"

    def new_page(self):
        if not self._cm._active or self._closed:
            raise RuntimeError(
                "LIFECYCLE VIOLATION: browser.new_page() called outside "
                "active sync_playwright() context or after close().")
        self.new_page_calls += 1
        page = _StrictPage()
        _LAST_BROWSER_PAGES.append(page)
        return page

    def close(self):
        self._closed = True


class _StrictPage:
    def __init__(self):
        self.route_handlers: list = []
        # Ordered record of every page-level call. Tests assert the
        # `route(...)` → `goto(...)` ordering contract: the safety
        # boundary MUST be armed before navigation so requests are
        # intercepted before they hit the network/server. Capturing
        # just the registered handler count is insufficient — a
        # regression that registers the handler AFTER goto would
        # still leave at least one handler attached but every
        # request fired during the unfiltered goto would slip past
        # the boundary.
        self.event_log: list[tuple] = []

    def on(self, event, handler):
        self.event_log.append(("on", event))

    def route(self, *args, **kwargs):
        # Mirrors the real Playwright sync API:
        #   page.route(handler)              → intercept every URL
        #   page.route(url_pattern, handler) → intercept specific URL
        # Either form is a no-op stub for the handler storage; the
        # test asserts the handler is captured, not the URL pattern.
        self.event_log.append(("route", args, kwargs))
        for arg in args:
            if callable(arg):
                self.route_handlers.append(arg)

    def goto(self, url, wait_until=None):
        # Default navigation is GET. Drive the registered route
        # handlers so the safety boundary is exercised end-to-end.
        # Tests that need a mutating request subclass / monkeypatch
        # `goto` to swap in a different method — GET is the safe
        # baseline so the existing lifecycle tests still pass.
        self.event_log.append(("goto", url, wait_until))
        if self.route_handlers:
            route = _StrictRoute(method="GET", url=url)
            for h in self.route_handlers:
                h(route)
        return _StrictResponse()

    def evaluate(self, script):
        return {}

    def wait_for_selector(self, sel, timeout=5000):
        pass

    def locator(self, selector):
        return _StrictLocator()


class _StrictRoute:
    """Fake Playwright Route for unit tests of the safety boundary.

    Mirrors the real sync API surface used by the handler:
      - `route.request.method`  (str; the HTTP method)
      - `route.continue_()`     (continue the request to network)
      - `route.abort()`         (abort the request before network)

    Records `continued` / `aborted` so the test can verify which
    branch the handler chose.
    """
    def __init__(self, method="GET", url="http://127.0.0.1:8765/"):
        self.request = types.SimpleNamespace(method=method, url=url)
        self.continued = False
        self.aborted = False

    def continue_(self):
        self.continued = True

    def abort(self):
        self.aborted = True


class _StrictResponse:
    status = 200


class _StrictLocator:
    def count(self):
        return 1

    @property
    def first(self):
        return self

    def inner_text(self):
        return "x"


def test_module_surface_constants_and_shebang():
    """Public surface + G5 contract constants + script presence + shebang."""
    for name in ("ITERATIONS", "SCHEMA", "PROVENANCE_SCHEMA",
                 "DEFAULT_DOM_MARKER_SELECTOR", "BrowserAdapter",
                 "PlaywrightBrowserAdapter", "collect_raw_samples",
                 "write_result", "main"):
        assert hasattr(ch, name), f"missing public symbol: {name}"
    assert ch.ITERATIONS == 10
    assert ch.SCHEMA == "taxa.g5-capture.legacy/1"
    assert ch.PROVENANCE_SCHEMA == "taxa.g5-capture.legacy-provenance/1"
    assert SCRIPT.is_file()
    assert SCRIPT.read_text(encoding="utf-8").startswith("#!/usr/bin/env python")


def test_collect_envelope_per_sample_schema_provenance_and_selector():
    """CORE: envelope + per-sample sub-block keys + provenance layout +
    custom selector passes through verbatim. The next chain child (G5
    joiner) reads these exact keys, so this test pins the contract."""
    adapter = FakeBrowserAdapter()
    selector = "#custom-marker"
    result = ch.collect_raw_samples(
        target_url=TARGET_URL, browser_adapter=adapter, dom_marker_selector=selector)
    for k in ("schema", "captured_at", "target_url", "iterations",
              "dom_marker_selector", "provenance", "samples"):
        assert k in result
    assert result["schema"] == ch.SCHEMA and result["iterations"] == 10
    assert result["target_url"] == TARGET_URL
    assert result["dom_marker_selector"] == selector
    assert result["captured_at"].endswith("Z")
    assert result["provenance"]["schema"] == ch.PROVENANCE_SCHEMA
    assert [s["iteration"] for s in result["samples"]] == list(range(10))
    for s in result["samples"]:
        for k in ("iteration", "captured_at", "navigation", "paint", "dom_marker", "console"):
            assert k in s
        for k in ("response_start_ms", "dom_content_loaded_ms", "load_event_ms", "redirect_count", "status"):
            assert k in s["navigation"]
        for k in ("first_paint_ms", "first_contentful_paint_ms"):
            assert k in s["paint"]
        for k in ("selector", "found", "count", "first_text", "wait_ms"):
            assert k in s["dom_marker"]
        assert isinstance(s["console"], list)
    p = result["provenance"]
    assert "version" in p["chromium"] and "executable_path" in p["chromium"]
    assert "version" in p["playwright"]
    assert "python_version" in p["environment"] and "platform" in p["environment"]
    assert p["target_url"] == TARGET_URL and p["iterations"] == 10
    assert len(adapter.calls) == 10
    assert all(sel == selector for _, sel, _ in adapter.calls)


def test_collect_iteration_failure_propagates_and_skips_remainder():
    """FAIL-CLOSED CORE: any iteration failure aborts with the same
    exception AND must NOT attempt iterations after the failure."""
    a = FakeBrowserAdapter(raise_on=5, raise_message="synthetic iter-5")
    with pytest.raises(RuntimeError, match="synthetic iter-5"):
        ch.collect_raw_samples(target_url=TARGET_URL, browser_adapter=a)
    assert [c[2] for c in a.calls] == [0, 1, 2, 3, 4]
    b = FakeBrowserAdapter(raise_on=1)
    with pytest.raises(RuntimeError):
        ch.collect_raw_samples(target_url=TARGET_URL, browser_adapter=b)
    assert [c[2] for c in b.calls] == [0]


def test_collect_input_validation():
    """G5 contract locks iterations to 10; target_url and selector
    must be non-empty. Each violation raises ValueError."""
    a = FakeBrowserAdapter()
    with pytest.raises(ValueError, match="10"):
        ch.collect_raw_samples(target_url=TARGET_URL, browser_adapter=a, iterations=5)
    with pytest.raises(ValueError, match="target_url"):
        ch.collect_raw_samples(target_url="", browser_adapter=a)
    with pytest.raises(ValueError, match="dom_marker_selector"):
        ch.collect_raw_samples(
            target_url=TARGET_URL, browser_adapter=a, dom_marker_selector="")


def test_cli_happy_path_dry_run_argparse_and_atomic_write(tmp_path, monkeypatch):
    """Happy CLI path: writes raw JSON to --out AND leaves no .tmp-
    sibling (atomic write contract). --dry-run prints to stdout and
    DOES NOT write --out. Argparse enforces --target-url + --out."""
    monkeypatch.setattr(ch, "PlaywrightBrowserAdapter", lambda: FakeBrowserAdapter())
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = ch.main(["capture_hydration.py", "--target-url", TARGET_URL,
                      "--out", str(tmp_path / "raw.json")])
    assert rc == 0, f"unexpected stderr: {err.getvalue()}"
    loaded = json.loads((tmp_path / "raw.json").read_text())
    assert loaded["schema"] == ch.SCHEMA and loaded["iterations"] == 10
    assert "wrote 10 raw samples" in out.getvalue()
    # Atomic write: no leftover .tmp- siblings.
    assert [p for p in tmp_path.iterdir() if p.name.startswith("raw.json.tmp-")] == []
    # Dry-run.
    dry_path = tmp_path / "dry.json"
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        rc = ch.main(["capture_hydration.py", "--target-url", TARGET_URL,
                      "--out", str(dry_path), "--dry-run"])
    assert rc == 0 and not dry_path.exists()
    # Subprocess argparse: missing flags → non-zero exit + stderr.
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=REPO_ROOT,
        capture_output=True, text=True, check=False)
    assert proc.returncode != 0 and proc.stderr.strip()
    assert "target-url" in proc.stderr.lower() or "out" in proc.stderr.lower()


def test_cli_iteration_failure_is_fail_closed_and_rejects_non_ten(tmp_path, monkeypatch):
    """FAIL-CLOSED CLI: iteration failure must NOT write --out and must
    exit non-zero with a stderr message naming fail-closed.
    --iterations must equal 10; any other value fails closed."""
    fake = FakeBrowserAdapter(raise_on=3, raise_message="synthetic cli iter-3")
    monkeypatch.setattr(ch, "PlaywrightBrowserAdapter", lambda: fake)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
        rc = ch.main(["capture_hydration.py", "--target-url", TARGET_URL,
                      "--out", str(tmp_path / "raw.json")])
    assert rc != 0 and not (tmp_path / "raw.json").exists()
    # --iterations=5 rejection.
    fake = FakeBrowserAdapter()
    monkeypatch.setattr(ch, "PlaywrightBrowserAdapter", lambda: fake)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
        rc = ch.main(["capture_hydration.py", "--target-url", TARGET_URL,
                      "--out", str(tmp_path / "raw2.json"), "--iterations", "5"])
    assert rc != 0 and "10" in err.getvalue()
    assert fake.calls == [], "adapter must not run when --iterations fails"
    assert not (tmp_path / "raw2.json").exists()


def test_module_decoupled_from_launcher_lighthouse_and_parity_reports():
    """Raw collector MUST stay decoupled from the G5 launcher and from
    parity-reports emission. AST-parsed so docstring mentions do not
    false-trigger."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported_modules: list = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
    for mod in imported_modules:
        assert "measure_hydration" not in mod, (
            f"must NOT import {mod} (later chain child owns that joiner)")
        assert "parity" not in mod.lower(), (
            f"must NOT import {mod} (publication is a later chain child)")
        assert "lighthouse" not in mod.lower(), (
            f"must NOT import {mod} (Lighthouse is a separate chain child)")


# ---------------------------------------------------------------------------
# LIFECYCLE SEAM tests — exercise the REAL PlaywrightBrowserAdapter
# against a strict sync_playwright() fake. The FakeBrowserAdapter above
# cannot catch this class of bug because it never instantiates the
# real adapter.
# ---------------------------------------------------------------------------


def test_playwright_adapter_chromium_only_inside_sync_playwright_context(monkeypatch):
    """LIFECYCLE SEAM (the one this slice exists to protect):
    `sync_playwright()` returns a `_PlaywrightContextManager`, NOT a
    Playwright instance. The Playwright instance that carries
    `.chromium` only exists inside `with sync_playwright() as p:`.

    Real bug shape: storing the un-entered context manager and calling
    `.chromium.launch(...)` on it raises AttributeError on the real
    Playwright sync API; our strict fake raises "LIFECYCLE VIOLATION"
    so the assertion is exact and self-explanatory.

    This test drives the REAL PlaywrightBrowserAdapter (no fake
    adapter in front of it) so any future regression that bypasses
    the context manager trips it.
    """
    cm = _StrictPlaywrightCM()
    fake_module = types.SimpleNamespace(sync_playwright=lambda: cm)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_module)

    adapter = ch.PlaywrightBrowserAdapter()

    # 1) chromium_provenance must enter the context before touching
    #    chromium; provenance layout must stay exact (G5 contract).
    prov = adapter.chromium_provenance()
    assert prov == {"version": "fake-chromium-v0",
                    "executable_path": "/fake/playwright/exec"}, (
        f"provenance layout drifted: {prov!r}")
    assert cm.chromium_outside_accesses == 0, (
        "chromium was accessed outside the active sync_playwright() "
        "context in chromium_provenance()")

    # 2) run_iteration must do the same; the sample shape and DOM
    #    marker fields must survive the lifecycle fix (G5 contract).
    sample = adapter.run_iteration(
        target_url=TARGET_URL,
        dom_marker_selector="#tree-view [data-taxon-id]",
        iteration_index=0,
    )
    assert sample["iteration"] == 0
    for k in ("navigation", "paint", "dom_marker", "console"):
        assert k in sample, f"missing sample key {k!r} after lifecycle fix"
    assert sample["navigation"]["status"] == 200
    assert sample["dom_marker"]["selector"] == "#tree-view [data-taxon-id]"
    assert isinstance(sample["console"], list)
    assert cm.chromium_outside_accesses == 0, (
        "chromium was accessed outside the active sync_playwright() "
        "context in run_iteration()")


def test_playwright_adapter_raises_clear_error_when_playwright_missing(monkeypatch):
    """LAZY-IMPORT CONTRACT: when playwright is not installed the
    adapter must raise `RuntimeError("playwright not installed: ...")`
    — the exact actionable message — instead of leaking an
    AttributeError on the un-entered context manager (the bug shape
    this slice fixes) or any other low-level import error."""
    # Block both names so `from playwright.sync_api import ...` fails
    # at the playwright step; `sys.modules[name] = None` is the
    # standard "import will raise ImportError" idiom.
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    adapter = ch.PlaywrightBrowserAdapter()
    with pytest.raises(RuntimeError, match="playwright not installed"):
        adapter.chromium_provenance()
    with pytest.raises(RuntimeError, match="playwright not installed"):
        adapter.run_iteration(target_url=TARGET_URL,
                              dom_marker_selector="#x",
                              iteration_index=0)
        # playwright_provenance() must stay hermetic: it does not touch
        # chromium and must still degrade to {"version": "unknown"} when
        # the top-level `playwright` package is unavailable.
        assert adapter.playwright_provenance() == {"version": "unknown"}


def test_default_dom_marker_selector_matches_g3_fixture():
    """G5 readiness contract: the raw collector's DEFAULT_DOM_MARKER_SELECTOR
    MUST target the controlled G3 fixture's dynamic readiness marker —
    `#tree-view[data-state="ready"]` — not the legacy static selector.
    Without this pin the collector cannot observe the G3 fixture's
    first-paint readiness flip emitted by `web/tree.js`."""
    assert ch.DEFAULT_DOM_MARKER_SELECTOR == '#tree-view[data-state="ready"]', (
        f"DEFAULT_DOM_MARKER_SELECTOR must match the G3 controlled fixture's "
        f"dynamic readiness marker (#tree-view[data-state=\"ready\"]); "
        f"got {ch.DEFAULT_DOM_MARKER_SELECTOR!r}"
    )


def test_collect_propagates_honest_elapsed_readiness_metric():
    """G5 readiness metric preservation: the raw collector MUST forward
    every adapter-provided `dom_marker.wait_ms` value verbatim into the
    sample envelope. The metric is the analogue of 'hydration cost' —
    how long the adapter waited for the readiness marker to become
    visible. A hard-coded zero would silently disable the candidate-vs-
    baseline delta the joiner relies on."""
    adapter = FakeBrowserAdapter(wait_ms=17.5)
    result = ch.collect_raw_samples(target_url=TARGET_URL, browser_adapter=adapter)
    assert len(result["samples"]) == 10
    for i, s in enumerate(result["samples"]):
        assert isinstance(s["dom_marker"], dict)
        assert s["dom_marker"]["wait_ms"] == 17.5, (
            f"sample[{i}].dom_marker.wait_ms must be preserved verbatim; "
            f"got {s['dom_marker']['wait_ms']!r}"
        )


def test_collect_missing_readiness_records_negative_one_and_not_found():
    """G5 readiness missing/invalid behavior: when the adapter reports the
    readiness marker was never observed, `wait_ms` MUST be -1.0 (the
    sentinel) AND `found` MUST be False. The collector must NOT coerce
    a missing marker into a zero or true — that would mask the failure
    in the candidate-vs-baseline diff."""
    adapter = FakeBrowserAdapter(wait_ms=-1.0, found=False, count=0,
                                 first_text=None)
    result = ch.collect_raw_samples(target_url=TARGET_URL, browser_adapter=adapter)
    assert len(result["samples"]) == 10
    for i, s in enumerate(result["samples"]):
        assert s["dom_marker"]["wait_ms"] == -1.0, (
            f"sample[{i}].dom_marker.wait_ms must be -1.0 when readiness "
            f"is missing; got {s['dom_marker']['wait_ms']!r}"
        )
        assert s["dom_marker"]["found"] is False, (
            f"sample[{i}].dom_marker.found must be False when readiness "
            f"is missing; got {s['dom_marker']['found']!r}"
        )
        assert s["dom_marker"]["count"] == 0
        assert s["dom_marker"]["first_text"] is None


def test_real_adapter_derives_wait_ms_from_wall_clock_inside_boundary(monkeypatch):
    """G5 readiness contract — REAL adapter: `wait_ms` MUST be derived
    from wall-clock elapsed time across `wait_for_selector` INSIDE the
    adapter boundary — not a hard-coded 0.0 literal. A regression that
    reverts to a literal would silently disable the candidate-vs-baseline
    delta.

    Hermetic: reuses the slice-7 strict sync_playwright() fake to skip
    the Playwright import + feeds a precise 17.5ms gap through
    `time.monotonic` (called once before, once after `wait_for_selector`).
    The error path (timeout) is covered by the FakeBrowserAdapter test
    above."""
    cm = _StrictPlaywrightCM()
    fake_module = types.SimpleNamespace(sync_playwright=lambda: cm)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_module)

    adapter = ch.PlaywrightBrowserAdapter()

    times = iter([1000.000, 1000.0175])
    monkeypatch.setattr(ch.time, "monotonic", lambda: next(times))

    result = adapter.run_iteration(
        target_url="http://127.0.0.1:8765/",
        dom_marker_selector='#tree-view[data-state="ready"]',
        iteration_index=0)
    assert result["dom_marker"]["wait_ms"] == pytest.approx(17.5), (
        f"REAL adapter wait_ms must derive from wall-clock elapsed time; "
        f"got {result['dom_marker']['wait_ms']!r} (expected ~17.5ms)"
    )
    assert result["dom_marker"]["found"] is True
    assert result["dom_marker"]["count"] == 1
    assert result["dom_marker"]["selector"] == '#tree-view[data-state="ready"]'
    assert cm.chromium_outside_accesses == 0, (
        "chromium was accessed outside the active sync_playwright() "
        "context in run_iteration()")


    # Child A — G5 evidence-manifest plan (deterministic, pure, no-I/O).
_PW_BASE = {"captured_at": "2026-09-01T00:00:00Z",
            "navigation": {"response_start_ms": 0.0, "dom_content_loaded_ms": 0.0,
                           "load_event_ms": 0.0, "redirect_count": 0, "status": 200},
            "paint": {"first_paint_ms": 0.0, "first_contentful_paint_ms": 0.0},
            "dom_marker": {"selector": "#tree-view [data-taxon-id]", "found": True,
                           "count": 1, "first_text": "x", "wait_ms": 0.0}, "console": []}
_LH_BASE = {"lighthouseVersion": "12.2.1",
            "userAgent": "Mozilla/5.0 (Fake) Chrome/130.0.0.0",
            "finalUrl": "http://127.0.0.1:8765/",
            "categories": {"performance": {"score": 0.95}, "accessibility": {"score": 0.98},
                           "best-practices": {"score": 0.92}, "seo": {"score": 1.0}}}
_MANIFEST = {"schema": "taxa.g4-capture.manifest/1", "entries": [{
    "url": "http://127.0.0.1:8765/index.html", "path": "index.html",
    "expectedContentSha256": "bb1a2731f4ab7e710d7989c5d5bd17205154155cd18f08e3ffa245c4165ae401",
    "expectedStatus": 200, "expectedDOMMarker": "data-testid=\"g4-probe-marker\""}]}
_HYDRATION = {"captured_at": "2026-08-28T00:00:00Z", "build": "legacy", "route": "/",
              "server_shell": {"first_paint_ms": 80.0, "dom_content_loaded_ms": 100.0},
              "client_render": {"tree_first_paint_ms": 220.0,
                                "tree_first_interactive_ms": 350.0},
              "console_warnings": []}


def _pw(i=0): return {**_PW_BASE, "iteration": i}
def _lh(i=0): return {**_LH_BASE, "iterations": i}
def _all_valid_inputs():
    return {"playwright_raws": [_pw(i) for i in range(10)],
            "lighthouse_raws": [_lh(i) for i in range(10)],
            "manifest_snapshot": _MANIFEST,
            "legacy_hydration_metadata": _HYDRATION}


def test_publication_plan_valid_inputs_yields_22_canonical_file_entries_no_io(tmp_path):
    """22 file entries (10 PW + 10 LH + 1 manifest + 1 hydration);
    path/sha256/bytes/canonical_json/kind per entry; sha256 hashes
    canonical_json; bytes == UTF-8 length; no I/O in tmp_path."""
    assert callable(getattr(ch, "plan_evidence_publication", None))
    pre = sorted(p.name for p in tmp_path.iterdir())
    plan = ch.plan_evidence_publication(**_all_valid_inputs())
    assert pre == sorted(p.name for p in tmp_path.iterdir()), \
        "must NOT touch the filesystem"
    assert plan["schema"] == ch.PUBLICATION_SCHEMA
    files = plan["files"]
    assert isinstance(files, list) and len(files) == 22
    by_kind = {"playwright": [], "lighthouse": [],
               "manifest_snapshot": [], "legacy_hydration": []}
    for f in files:
        by_kind[f["kind"]].append(f)
    assert [len(v) for v in by_kind.values()] == [10, 10, 1, 1]
    sha_re = re.compile(r"[0-9a-f]{64}")
    for f in files:
        for k in ("kind", "path", "bytes", "sha256", "canonical_json"):
            assert k in f
        assert not f["path"].startswith("/") and ".." not in f["path"].split("/")
        assert sha_re.fullmatch(f["sha256"])
        assert isinstance(f["bytes"], int) and f["bytes"] > 0
        encoded = f["canonical_json"].encode("utf-8")
        assert f["sha256"] == hashlib.sha256(encoded).hexdigest()
        assert f["bytes"] == len(encoded)


def test_publication_plan_deterministic_pure_and_unique_paths():
    """Two identical calls → byte-identical plans; inputs not mutated;
    iteration 0..9 + zero-padded iter-00..iter-09 paths."""
    inputs = _all_valid_inputs()
    pw0 = json.loads(json.dumps(inputs["playwright_raws"]))
    lh0 = json.loads(json.dumps(inputs["lighthouse_raws"]))
    ms0 = json.loads(json.dumps(inputs["manifest_snapshot"]))
    h0 = json.loads(json.dumps(inputs["legacy_hydration_metadata"]))
    p1 = ch.plan_evidence_publication(**inputs)
    p2 = ch.plan_evidence_publication(**inputs)
    assert (inputs["playwright_raws"], inputs["lighthouse_raws"],
            inputs["manifest_snapshot"], inputs["legacy_hydration_metadata"]) == (pw0, lh0, ms0, h0)
    b1 = {f["path"]: f["canonical_json"] for f in p1["files"]}
    b2 = {f["path"]: f["canonical_json"] for f in p2["files"]}
    assert b1 == b2, "canonical_json MUST be byte-identical across runs"
    by_kind = {"playwright": [], "lighthouse": []}
    for f in p1["files"]:
        if f["kind"] in by_kind:
            by_kind[f["kind"]].append(f)
    assert [f["iteration"] for f in by_kind["playwright"]] == list(range(10))
    assert [f["iteration"] for f in by_kind["lighthouse"]] == list(range(10))
    assert sorted(f["path"] for f in by_kind["playwright"]) == \
        [f"raw/playwright/iter-{i:02d}.json" for i in range(10)]
    assert sorted(f["path"] for f in by_kind["lighthouse"]) == \
        [f"raw/lighthouse/iter-{i:02d}.json" for i in range(10)]
    assert len({f["path"] for f in p1["files"]}) == 22


def test_publication_plan_wrong_counts_and_malformed_manifest_raise():
    """G5 contract: PW + LH raws must be exactly 10 each (0/9/11 + non-dict
    entries raise). Malformed manifest (missing schema/entries) raises."""
    b = _all_valid_inputs()
    for pw in ([], b["playwright_raws"][:9], b["playwright_raws"] + [_pw(10)]):
        with pytest.raises(ValueError, match="[Pp]laywright"):
            ch.plan_evidence_publication(
                playwright_raws=pw, lighthouse_raws=b["lighthouse_raws"],
                manifest_snapshot=b["manifest_snapshot"],
                legacy_hydration_metadata=b["legacy_hydration_metadata"])
    for lh in ([], b["lighthouse_raws"] + [_lh(10)]):
        with pytest.raises(ValueError, match="[Ll]ighthouse"):
            ch.plan_evidence_publication(
                playwright_raws=b["playwright_raws"], lighthouse_raws=lh,
                manifest_snapshot=b["manifest_snapshot"],
                legacy_hydration_metadata=b["legacy_hydration_metadata"])
    bad_pw = list(b["playwright_raws"]); bad_pw[3] = "not a dict"
    with pytest.raises(ValueError, match="[Pp]laywright"):
        ch.plan_evidence_publication(
            playwright_raws=bad_pw, lighthouse_raws=b["lighthouse_raws"],
            manifest_snapshot=b["manifest_snapshot"],
            legacy_hydration_metadata=b["legacy_hydration_metadata"])
    for bad_manifest in ({"schema": "wrong/1"}, {"entries": []}):
        with pytest.raises(ValueError, match="manifest"):
            ch.plan_evidence_publication(
                playwright_raws=b["playwright_raws"],
                lighthouse_raws=b["lighthouse_raws"],
                manifest_snapshot=bad_manifest,
                legacy_hydration_metadata=b["legacy_hydration_metadata"])


def test_publication_plan_malformed_hydration_metadata_raises():
    """Required keys (captured_at/build/route/server_shell/client_render/
    console_warnings) must all be present; server_shell+client_render must
    be dicts; console_warnings must be a list. Each violation raises."""
    b = _all_valid_inputs()
    for missing in ("captured_at", "build", "route", "server_shell",
                    "client_render", "console_warnings"):
        broken = {**_HYDRATION}; broken.pop(missing)
        with pytest.raises(ValueError, match=missing):
            ch.plan_evidence_publication(
                playwright_raws=b["playwright_raws"],
                lighthouse_raws=b["lighthouse_raws"],
                manifest_snapshot=b["manifest_snapshot"],
                legacy_hydration_metadata=broken)
    for bad_key, bad_val in (("server_shell", "x"), ("client_render", 42),
                              ("console_warnings", "x")):
        broken = {**_HYDRATION, bad_key: bad_val}
        with pytest.raises(ValueError, match=bad_key):
            ch.plan_evidence_publication(
                playwright_raws=b["playwright_raws"],
                lighthouse_raws=b["lighthouse_raws"],
                manifest_snapshot=b["manifest_snapshot"],
                legacy_hydration_metadata=broken)


def test_publication_plan_canonical_json_roundtrips_and_serialisable():
    """canonical_json MUST round-trip to original payload; full plan MUST be
    JSON-serialisable. Non-serialisable raw raises before any partial plan."""
    inputs = _all_valid_inputs()
    plan = ch.plan_evidence_publication(**inputs)
    by_kind = {"playwright": [], "lighthouse": [],
               "manifest_snapshot": [], "legacy_hydration": []}
    for f in plan["files"]:
        by_kind[f["kind"]].append(f)
    for entry, orig in zip(by_kind["playwright"], inputs["playwright_raws"]):
        assert json.loads(entry["canonical_json"]) == orig
    for entry, orig in zip(by_kind["lighthouse"], inputs["lighthouse_raws"]):
        assert json.loads(entry["canonical_json"]) == orig
    assert json.loads(by_kind["manifest_snapshot"][0]["canonical_json"]) == inputs["manifest_snapshot"]
    assert json.loads(by_kind["legacy_hydration"][0]["canonical_json"]) == inputs["legacy_hydration_metadata"]
    assert json.loads(json.dumps(plan, sort_keys=True)) == plan
    bad = list(inputs["playwright_raws"]); bad[2] = {"iteration": 2, "blob": b"\x00"}
    with pytest.raises((ValueError, TypeError)):
        ch.plan_evidence_publication(
            playwright_raws=bad, lighthouse_raws=inputs["lighthouse_raws"],
            manifest_snapshot=inputs["manifest_snapshot"],
            legacy_hydration_metadata=inputs["legacy_hydration_metadata"])


# --- Slice 16: bridge-advisories publication (optional file) ------------
# When the orchestrator captures bridge timeouts it accumulates
# ``bridge_advisories`` and threads them through the planner. The
# planner MUST persist them atomically as ``raw/bridge-advisories.json``
# when non-empty AND MUST produce a byte-identical plan when None or
# empty (backward compatibility contract for prior slices).
def test_publication_plan_without_advisories_byte_identical():
    """Backward compat: omitting / None / empty bridge_advisories must
    produce a plan whose JSON is byte-identical to the pre-Slice plan."""
    inputs = _all_valid_inputs()
    baseline = ch.plan_evidence_publication(**inputs)
    baseline_json = json.dumps(baseline, sort_keys=True, ensure_ascii=False)
    # omitted kwarg
    p_omitted = ch.plan_evidence_publication(**inputs)
    assert json.dumps(p_omitted, sort_keys=True,
                      ensure_ascii=False) == baseline_json
    # explicit None
    p_none = ch.plan_evidence_publication(**inputs, bridge_advisories=None)
    assert json.dumps(p_none, sort_keys=True,
                      ensure_ascii=False) == baseline_json
    # explicit empty list
    p_empty = ch.plan_evidence_publication(**inputs, bridge_advisories=[])
    assert json.dumps(p_empty, sort_keys=True,
                      ensure_ascii=False) == baseline_json
    # 22 entries unchanged; no ``raw/bridge-advisories.json`` entry
    assert len(baseline["files"]) == 22
    paths = {f["path"] for f in baseline["files"]}
    assert "raw/bridge-advisories.json" not in paths


def test_publication_plan_with_advisories_adds_single_entry():
    """Non-empty bridge_advisories appends exactly ONE
    ``raw/bridge-advisories.json`` entry (kind, path, bytes,
    canonical_json, sha256)."""
    inputs = _all_valid_inputs()
    advisories = [
        {"iteration": 1, "kind": "bridge_timeout",
         "reason": "bridge subprocess exceeded timeout",
         "timeout_s": 1.0, "url": "http://127.0.0.1:8765/"},
        {"iteration": 4, "kind": "bridge_timeout",
         "reason": "bridge subprocess exceeded timeout",
         "timeout_s": 1.0, "url": "http://127.0.0.1:8765/"},
    ]
    plan = ch.plan_evidence_publication(**inputs,
                    bridge_advisories=advisories)
    adv_entries = [f for f in plan["files"]
                   if f["kind"] == "bridge_advisories"]
    assert len(adv_entries) == 1
    entry = adv_entries[0]
    assert entry["path"] == "raw/bridge-advisories.json"
    # canonical_json is the wrapped payload (schema + advisories list)
    payload = json.loads(entry["canonical_json"])
    assert isinstance(payload, dict)
    assert isinstance(payload.get("schema"), str)
    assert payload["schema"].startswith("taxa.g5-publication.bridge-advisories")
    assert payload.get("advisories") == advisories
    # sha256 + bytes match canonical_json utf-8 encoding
    assert entry["sha256"] == hashlib.sha256(
        entry["canonical_json"].encode("utf-8")).hexdigest()
    assert entry["bytes"] == len(
        entry["canonical_json"].encode("utf-8"))
    # 22 base entries + 1 new entry = 23; previous files unchanged
    assert len(plan["files"]) == 23
    all_paths = {f["path"] for f in plan["files"]}
    assert "raw/bridge-advisories.json" in all_paths


def test_publication_plan_advisories_no_iteration_field():
    """The bridge-advisories file is a single bundled artifact (not per
    iteration). The entry MUST NOT carry an ``iteration`` field."""
    inputs = _all_valid_inputs()
    advisories = [{"iteration": 1, "kind": "bridge_timeout",
                   "reason": "x", "timeout_s": 1.0,
                   "url": "http://127.0.0.1:8765/"}]
    plan = ch.plan_evidence_publication(**inputs,
                    bridge_advisories=advisories)
    adv_entries = [f for f in plan["files"]
                   if f["kind"] == "bridge_advisories"]
    assert "iteration" not in adv_entries[0]


def test_publication_plan_advisories_deterministic_and_pure():
    """Calling twice with the same advisory list yields byte-identical
    plans; inputs are not mutated."""
    inputs = _all_valid_inputs()
    advisories = [{"iteration": 1, "kind": "bridge_timeout",
                   "reason": "x", "timeout_s": 1.0,
                   "url": "http://127.0.0.1:8765/"}]
    adv_snapshot = json.loads(json.dumps(advisories))
    p1 = ch.plan_evidence_publication(**inputs,
              bridge_advisories=advisories)
    p2 = ch.plan_evidence_publication(**inputs,
              bridge_advisories=advisories)
    assert advisories == adv_snapshot
    b1 = {f["path"]: f["canonical_json"] for f in p1["files"]}
    b2 = {f["path"]: f["canonical_json"] for f in p2["files"]}
    assert b1 == b2


def test_publication_plan_advisories_rejects_non_list_or_bad_entries():
    """Non-list bridge_advisories raises ValueError; list with non-dict
    entries raises ValueError. Only ``list`` of dicts is accepted."""
    inputs = _all_valid_inputs()
    for bad in ({"iteration": 1}, (1, 2), "x", 7):
        with pytest.raises(ValueError, match="bridge_advisories"):
            ch.plan_evidence_publication(**inputs,
                        bridge_advisories=bad)
    for bad_entry in (["x"], [1, 2], [{"kind": "x"}, "x"]):
        with pytest.raises(ValueError, match="bridge_advisories"):
            ch.plan_evidence_publication(**inputs,
                        bridge_advisories=bad_entry)


# --- G5 publication child B (atomic filesystem publisher) -----------
def _publisher_plan():
    return ch.plan_evidence_publication(**_all_valid_inputs())


def test_publish_happy_path_writes_files_and_validates_staged(tmp_path):
    target = tmp_path / "out"
    ch.publish_evidence_atomic(_publisher_plan(), target)
    assert target.is_dir()
    plan = _publisher_plan()
    actual = sorted(str(p.relative_to(target))
                    for p in target.rglob("*") if p.is_file())
    assert actual == sorted(f["path"] for f in plan["files"])
    for f in plan["files"]:
        data = (target / f["path"]).read_bytes()
        assert len(data) == f["bytes"]
        assert hashlib.sha256(data).hexdigest() == f["sha256"]
        assert data == f["canonical_json"].encode("utf-8")
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "out"]
    assert leftovers == [], f"unexpected residue: {leftovers}"


def test_publish_replaces_existing_target_and_removes_backup(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    (target / "stale.json").write_bytes(b'{"old": true}')
    ch.publish_evidence_atomic(_publisher_plan(), target)
    assert not (target / "stale.json").exists()
    assert (target / "raw" / "playwright" / "iter-00.json").is_file()
    assert (target / "raw" / "manifest-snapshot.json").is_file()
    assert not (tmp_path / "out.bak").exists()


def test_publish_write_seam_failure_preserves_prior_and_no_residue(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    prior = b'{"prior": "untouched"}'
    (target / "stale.json").write_bytes(prior)
    state = {"calls": 0}
    def flaky(path, data):
        state["calls"] += 1
        if state["calls"] == 1:
            path.write_bytes(data); return
        raise RuntimeError("synthetic write seam failure")
    with pytest.raises(RuntimeError, match="synthetic write seam failure"):
        ch.publish_evidence_atomic(_publisher_plan(), target, write_fn=flaky)
    assert (target / "stale.json").read_bytes() == prior
    assert sorted(p.name for p in target.iterdir()) == ["stale.json"]
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "out"]
    assert leftovers == [], f"unexpected residue: {leftovers}"


def test_publish_validation_mismatch_preserves_prior_and_no_residue(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    prior = b'{"prior": "untouched"}'
    (target / "stale.json").write_bytes(prior)
    def corrupting(path, data):
        path.write_bytes(b"corrupted" * 5)
    with pytest.raises(ValueError, match="sha256|bytes|path"):
        ch.publish_evidence_atomic(_publisher_plan(), target, write_fn=corrupting)
    assert (target / "stale.json").read_bytes() == prior
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "out"]
    assert leftovers == [], f"unexpected residue: {leftovers}"


def test_publish_final_rename_failure_restores_prior_and_no_residue(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    prior = b'{"prior": "untouched"}'
    (target / "stale.json").write_bytes(prior)
    real_replace = os.replace
    def selective(src, dst):
        if src.name.startswith("out.staging-"):
            raise OSError("synthetic final-rename failure")
        return real_replace(src, dst)
    with pytest.raises(OSError, match="synthetic final-rename failure"):
        ch.publish_evidence_atomic(_publisher_plan(), target, rename_fn=selective)
    assert (target / "stale.json").read_bytes() == prior
    assert sorted(p.name for p in target.iterdir()) == ["stale.json"]
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "out"]
    assert leftovers == [], f"unexpected residue: {leftovers}"


def test_publish_final_rename_and_restore_failure_leaves_backup_residue(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    prior = b'{"prior": "untouched"}'
    (target / "stale.json").write_bytes(prior)
    def allow_backup_only(src, dst):
        if src.name.startswith("out.staging-") or src.name.endswith(".bak"):
            raise OSError(f"synthetic rename failure on {src.name}->{dst.name}")
        return os.replace(src, dst)
    with pytest.raises(OSError, match="synthetic rename failure"):
        ch.publish_evidence_atomic(_publisher_plan(), target,
                                   rename_fn=allow_backup_only)
    backup = tmp_path / "out.bak"
    assert backup.is_dir()
    assert (backup / "stale.json").read_bytes() == prior
    leftovers = [p.name for p in tmp_path.iterdir()
                 if p.name not in ("out", "out.bak")]
    assert leftovers == [], f"unexpected non-backup residue: {leftovers}"


def test_publish_rejects_bad_plan_schema_and_paths_before_io(tmp_path):
    target = tmp_path / "out"
    valid = _publisher_plan()
    with pytest.raises(ValueError, match="schema"):
        ch.publish_evidence_atomic({**valid, "schema": "wrong/1"}, target)
    with pytest.raises(ValueError, match="files"):
        bad = {**valid}; bad.pop("files")
        ch.publish_evidence_atomic(bad, target)
    bad_files = list(valid["files"])
    bad_files[0] = {**bad_files[0], "path": "/abs/file.json"}
    with pytest.raises(ValueError, match="relative|path"):
        ch.publish_evidence_atomic({**valid, "files": bad_files}, target)
    bad_files = list(valid["files"])
    bad_files[0] = {**bad_files[0], "path": "../escape.json"}
    with pytest.raises(ValueError, match=r"\.\."):
        ch.publish_evidence_atomic({**valid, "files": bad_files}, target)
    bad_files = list(valid["files"]) + [dict(valid["files"][0])]
    with pytest.raises(ValueError, match="duplicate"):
        ch.publish_evidence_atomic({**valid, "files": bad_files}, target)
    bad_files = list(valid["files"])
    bad_files[0] = {**bad_files[0], "sha256": "not-hex"}
    with pytest.raises(ValueError, match="sha256"):
        ch.publish_evidence_atomic({**valid, "files": bad_files}, target)
    assert not target.exists()


def test_publish_rejects_existing_file_target(tmp_path):
    target = tmp_path / "out"
    target.write_bytes(b"not a directory")
    with pytest.raises(ValueError, match="file|directory"):
        ch.publish_evidence_atomic(_publisher_plan(), target)
    assert target.read_bytes() == b"not a directory"


def test_publish_rejects_orphan_backup_left_by_prior_failure(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    prior = b'{"prior": "untouched"}'
    (target / "stale.json").write_bytes(prior)
    orphan = tmp_path / "out.bak"
    orphan.mkdir()
    (orphan / "human-recovery-marker.txt").write_bytes(b"RECOVER ME")
    with pytest.raises((ValueError, FileExistsError), match="backup"):
        ch.publish_evidence_atomic(_publisher_plan(), target)
    assert (target / "stale.json").read_bytes() == prior
    assert (orphan / "human-recovery-marker.txt").read_bytes() == b"RECOVER ME"
    leftovers = [p.name for p in tmp_path.iterdir() if p.name not in ("out", "out.bak")]
    assert leftovers == [], f"unexpected residue: {leftovers}"


def test_publish_validation_catches_extra_files_in_staging(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    prior = b'{"prior": "untouched"}'
    (target / "stale.json").write_bytes(prior)
    plan = _publisher_plan()
    def sneaky(path, data):
        path.write_bytes(data)
        if path.name == "iter-09.json":
            (path.parent / "extra-unplanned.json").write_bytes(b"unplanned")
    with pytest.raises(ValueError, match="path"):
        ch.publish_evidence_atomic(plan, target, write_fn=sneaky)
    assert (target / "stale.json").read_bytes() == prior
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "out"]
    assert leftovers == [], f"unexpected residue: {leftovers}"


# ---------------------------------------------------------------------------
# G5 candidate role (`--role migrated`) — strict-TDD slice.
# Contract: `--role migrated` REQUIRES `--candidate-root`; legacy
# default REJECTS `--candidate-root`; pre-flight verifies Next.js
# static-export root + HTTP-200 no-redirect + sha256 equality BEFORE
# Chromium; output carries migrated schema/build/candidate_root/sha;
# legacy default output (schema/provenance/samples) is byte-pinned.
# ---------------------------------------------------------------------------


MIGRATED_SCHEMA = "taxa.g5-capture.migrated/1"
MIGRATED_PROVENANCE_SCHEMA = "taxa.g5-capture.migrated-provenance/1"


def _free_port() -> int:
    """Bind a free localhost port; immediately release."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _serve(handler_factory) -> tuple[str, threading.Thread,
                                       http.server.ThreadingHTTPServer]:
    """Bind a one-shot HTTP server on a free port. Returns
    ``(url, thread, httpd)``; caller must ``shutdown`` / ``join`` /
    ``server_close`` to release the port."""
    port = _free_port()
    httpd = http.server.ThreadingHTTPServer(
        ("127.0.0.1", port), handler_factory)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return f"http://127.0.0.1:{port}", t, httpd


class _CandidateServer:
    """Serve `root` over HTTP on a free localhost port. Threading
    server so concurrent fetches from the candidate pre-flight work
    without serialising. Each request maps to a fresh
    ``SimpleHTTPRequestHandler`` so concurrent reads are independent."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.port: int | None = None
        self._httpd: http.server.ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> Self:
        self.port = _free_port()
        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler,
            directory=str(self.root.resolve()),
        )
        self._httpd = http.server.ThreadingHTTPServer(
            ("127.0.0.1", self.port), handler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


def _make_candidate_root(root: Path, *, body: bytes | None = None,
                         include_static: bool = True) -> Path:
    """Materialise a minimal Next.js static-export root.

    Required shape per design.md §3.3.2.1 + parent-review identity
    hardening: a real Next static export carries (1) at least one
    file under `_next/static/` and (2) an `index.html` that references
    a `/_next/static/` asset. The default fixture satisfies both so
    happy-path tests pass without per-test setup.

    Pass `include_static=False` to omit `_next/static/` entirely
    (used by the fail-closed negative test).
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_bytes(
        body if body is not None
        else (b"<!doctype html><html><body>candidate fixture</body>\n"
              b'<script src="/_next/static/chunks/main.js"></script>\n'
              b'<link rel="stylesheet" href="/_next/static/css/app.css">\n'
              b"</html>\n"))
    if include_static:
        static_dir = root / "_next" / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        # One representative static asset so the identity check
        # (>= 1 file under _next/static) passes.
        (static_dir / "chunks").mkdir(exist_ok=True)
        (static_dir / "chunks" / "main.js").write_bytes(b"// js\n")
    return root


# --- migrated role CLI contract --------------------------------------


def test_migrated_module_constants_and_parser_surface():
    for name in ("MIGRATED_SCHEMA", "MIGRATED_PROVENANCE_SCHEMA",
                 "MIGRATED_BUILD_LABEL", "collect_migrated_samples",
                 "validate_candidate_root"):
        assert hasattr(ch, name), f"missing migrated symbol: {name}"
    assert ch.MIGRATED_SCHEMA == MIGRATED_SCHEMA
    assert ch.MIGRATED_PROVENANCE_SCHEMA == MIGRATED_PROVENANCE_SCHEMA
    assert ch.MIGRATED_BUILD_LABEL == "migrated"


def test_cli_migrated_role_requires_candidate_root(tmp_path, monkeypatch,
                                                   capsys):
    """`--role migrated` without `--candidate-root` fails closed
    (exit != 0, no --out written, stderr mentions candidate-root)."""
    monkeypatch.setattr(ch, "PlaywrightBrowserAdapter", lambda: FakeBrowserAdapter())
    out = tmp_path / "out.json"
    rc = ch.main(["capture_hydration.py", "--target-url", TARGET_URL,
                  "--out", str(out), "--role", "migrated"])
    assert rc != 0
    assert not out.exists()
    err = capsys.readouterr().err
    assert "candidate-root" in err.lower() or "role" in err.lower()


@pytest.mark.parametrize("role", ["", "legacy"])
def test_cli_legacy_role_rejects_candidate_root(role, tmp_path, monkeypatch,
                                                  capsys):
    """Legacy default AND explicit `--role legacy` must REJECT
    `--candidate-root` (candidate-only flag)."""
    monkeypatch.setattr(ch, "PlaywrightBrowserAdapter", lambda: FakeBrowserAdapter())
    out = tmp_path / "out.json"
    argv = ["capture_hydration.py", "--target-url", TARGET_URL,
            "--out", str(out)]
    if role:
        argv.extend(["--role", role])
    argv.extend(["--candidate-root", str(tmp_path / "cr")])
    rc = ch.main(argv)
    assert rc != 0
    assert not out.exists()
    assert "candidate" in capsys.readouterr().err.lower()


# --- migrated candidate-root pre-flight (filesystem) -----------------


def test_validate_candidate_root_happy(tmp_path):
    root = _make_candidate_root(tmp_path / "next")
    result = ch.validate_candidate_root(root)
    assert result["candidate_root"] == str(root.resolve())
    assert result["candidate_index_sha256"] == hashlib.sha256(
        (root / "index.html").read_bytes()).hexdigest()
    assert result["static_dir_present"] is True


@pytest.mark.parametrize("setup,match", [
    ("missing_dir", "not found|candidate-root|exists"),
    ("missing_index", "index.html"),
    ("missing_static", "_next/static|_next"),
    ("file_not_dir", "directory|dir"),
])
def test_validate_candidate_root_rejects_malformed(setup, match, tmp_path):
    """All four pre-flight failure shapes fail closed with a clear
    ValueError before Chromium is ever launched."""
    if setup == "missing_dir":
        target = tmp_path / "does-not-exist"
    elif setup == "missing_index":
        target = tmp_path / "no-index"
        target.mkdir()
        (target / "_next" / "static").mkdir(parents=True)
    elif setup == "missing_static":
        target = tmp_path / "no-static"
        target.mkdir()
        (target / "index.html").write_bytes(b"<html></html>")
    else:
        assert setup == "file_not_dir", f"unknown setup: {setup}"
        target = tmp_path / "file-as-root"
        target.write_bytes(b"x")
    with pytest.raises(ValueError, match=match):
        ch.validate_candidate_root(target)


# --- migrated HTTP pre-flight (no auto-redirect, 200, sha match) -----


def test_http_get_index_returns_body_status_on_200(tmp_path):
    root = _make_candidate_root(tmp_path / "next")
    expected = (root / "index.html").read_bytes()
    with _CandidateServer(root) as srv:
        status, body = ch._http_get_index(srv.url + "/index.html")
    assert status == 200 and body == expected


def _http_fault_handler(status_code: int, *, location: str | None = None):
    """Factory for a BaseHTTPRequestHandler that replies with
    `status_code` to every GET. Inline import keeps the helper local
    to this module."""
    import http.server as _hs

    class _Handler(_hs.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(status_code)
            if location:
                self.send_header("Location", location)
            self.end_headers()
            if status_code == 404:
                self.wfile.write(b"nope")

        def log_message(self, *args, **kwargs):
            return

    return _Handler


@pytest.mark.parametrize("status_code,location,expected_exc,match", [
    (302, "http://127.0.0.1:1/", urllib.error.HTTPError, None),
    (404, None, ValueError, "200|404|status"),
])
def test_http_get_index_redirect_and_404_fail_closed(status_code, location,
                                                      expected_exc, match,
                                                      tmp_path):
    """`_http_get_index` MUST NOT auto-follow redirects (a legacy
    8765 → migrated path would silently pass the SHA check against
    the wrong root) and MUST treat 4xx as fail-closed."""
    url, _, httpd = _serve(
        _http_fault_handler(status_code, location=location))
    try:
        with pytest.raises(expected_exc, match=match):
            ch._http_get_index(url + "/index.html")
    finally:
        httpd.shutdown()
        httpd.server_close()


# --- migrated collect_migrated_samples -------------------------------


def test_collect_migrated_samples_writes_migrated_schema_and_metadata(
    tmp_path):
    """Happy path: candidate-root passes pre-flight, samples carry
    the migrated schema/build/candidate_root/candidate_index_sha256,
    provenance identifies the migrated capture, Chromium runs after
    pre-flight, and `found:false` data is preserved verbatim."""
    root = _make_candidate_root(tmp_path / "next")
    adapter = FakeBrowserAdapter()
    with _CandidateServer(root) as srv:
        target = srv.url + "/index.html"
        result = ch.collect_migrated_samples(
            target_url=target, browser_adapter=adapter, candidate_root=root)
    assert result["schema"] == MIGRATED_SCHEMA
    assert result["build"] == "migrated"
    assert result["candidate_root"] == str(root.resolve())
    expected_hash = hashlib.sha256(
        (root / "index.html").read_bytes()).hexdigest()
    assert result["candidate_index_sha256"] == expected_hash
    assert result["static_dir_present"] is True
    assert result["provenance"]["schema"] == MIGRATED_PROVENANCE_SCHEMA
    assert result["provenance"]["candidate_root"] == str(root.resolve())
    assert result["provenance"]["candidate_index_sha256"] == expected_hash
    assert result["iterations"] == 10
    assert len(result["samples"]) == 10
    for s in result["samples"]:
        assert s["dom_marker"]["selector"] == ch.DEFAULT_DOM_MARKER_SELECTOR
    assert result["target_url"] == target


def test_collect_migrated_samples_fails_closed_on_sha_mismatch(tmp_path):
    """Served index.html body differs from `<candidate-root>/index.html`
    → fail closed BEFORE Chromium launches."""
    root = _make_candidate_root(tmp_path / "next")
    fake_root = _make_candidate_root(
        tmp_path / "fake", body=b"<html>DIFFERENT CONTENT</html>\n")
    adapter = FakeBrowserAdapter()
    adapter.calls = []
    with _CandidateServer(fake_root) as srv, \
            pytest.raises(ValueError, match="sha256|hash|mismatch"):
        ch.collect_migrated_samples(
            target_url=srv.url + "/index.html",
            browser_adapter=adapter, candidate_root=root)
    assert adapter.calls == []


def test_collect_migrated_samples_fails_closed_on_missing_static_dir(
    tmp_path):
    """Candidate-root missing `_next/static` fails closed BEFORE
    the HTTP fetch / Chromium launch."""
    root = _make_candidate_root(tmp_path / "next", include_static=False)
    adapter = FakeBrowserAdapter()
    with pytest.raises(ValueError, match="_next/static|_next"):
        ch.collect_migrated_samples(
            target_url="http://127.0.0.1:1/index.html",
            browser_adapter=adapter, candidate_root=root)
    assert adapter.calls == []


def test_collect_migrated_samples_fails_closed_on_url_unreachable(tmp_path):
    """`<target-url>/index.html` unreachable → fail closed BEFORE
    Chromium launches."""
    root = _make_candidate_root(tmp_path / "next")
    adapter = FakeBrowserAdapter()
    with pytest.raises((ValueError, OSError, urllib.error.URLError)):
        ch.collect_migrated_samples(
            target_url=f"http://127.0.0.1:{_free_port()}/index.html",
            browser_adapter=adapter, candidate_root=root)
    assert adapter.calls == []


def test_collect_migrated_samples_preserves_found_false_data(tmp_path):
    """Migrated role MUST preserve `found:false` + `wait_ms:-1`
    verbatim — never coerce a missing readiness marker into 0."""
    root = _make_candidate_root(tmp_path / "next")
    adapter = FakeBrowserAdapter(wait_ms=-1.0, found=False, count=0,
                                  first_text=None)
    with _CandidateServer(root) as srv:
        result = ch.collect_migrated_samples(
            target_url=srv.url + "/index.html",
            browser_adapter=adapter, candidate_root=root)
    for s in result["samples"]:
        assert s["dom_marker"]["found"] is False
        assert s["dom_marker"]["count"] == 0
        assert s["dom_marker"]["wait_ms"] == -1.0
        assert s["dom_marker"]["first_text"] is None


# --- legacy default output remains pinned -----------------------------


def test_legacy_default_output_schema_and_build_label_unchanged(tmp_path,
                                                                 monkeypatch):
    """Legacy default (no `--role`, no `--candidate-root`) MUST
    continue to emit the legacy schema + provenance with NO
    migrated fields. The legacy byte contract is preserved verbatim."""
    monkeypatch.setattr(ch, "PlaywrightBrowserAdapter", lambda: FakeBrowserAdapter())
    out = tmp_path / "out.json"
    rc = ch.main(["capture_hydration.py", "--target-url", TARGET_URL,
                  "--out", str(out)])
    assert rc == 0
    doc = json.loads(out.read_text())
    assert doc["schema"] == ch.SCHEMA
    assert doc["provenance"]["schema"] == ch.PROVENANCE_SCHEMA
    for forbidden in ("candidate_root", "candidate_index_sha256",
                      "static_dir_present", "build"):
        assert forbidden not in doc, (
            f"legacy output must NOT carry migrated field {forbidden!r}")
    assert "build" not in doc["provenance"]
    assert doc["dom_marker_selector"] == ch.DEFAULT_DOM_MARKER_SELECTOR
    assert len(doc["samples"]) == 10


# ---------------------------------------------------------------------------
# Parent-review hardening: `validate_candidate_root` must reject a
# legacy `web/` root that has been padded with an empty `_next/static`
# directory. Real Next.js static export carries at least one file
# under `_next/static/` and `index.html` references a `/_next/static/`
# asset. Strengthen identity minimally:
#   1. require at least one actual file below `_next/static/`
#   2. require `index.html` to reference a `/_next/static/` asset
# ---------------------------------------------------------------------------


def test_validate_candidate_root_rejects_empty_static_dir(tmp_path):
    """An empty `_next/static/` directory is NOT a real Next static
    export. A legacy `web/` root padded with an empty directory
    must fail closed so `--role migrated` cannot pass against it."""
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "index.html").write_bytes(b"<html></html>\n")
    (root / "_next" / "static").mkdir(parents=True)  # empty
    with pytest.raises(ValueError, match="empty _next/static|empty.*static"):
        ch.validate_candidate_root(root)


def test_validate_candidate_root_rejects_index_without_next_static_ref(
        tmp_path):
    """`index.html` MUST reference a `/_next/static/` asset. A legacy
    `web/` root with an arbitrary HTML document and a populated
    `_next/static/` directory must still fail closed — the index
    itself must reference the static asset to be a real Next export."""
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "index.html").write_bytes(
        b"<!doctype html><html><body>legacy page</body></html>\n")
    static_dir = root / "_next" / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "chunks").mkdir()
    (static_dir / "chunks" / "main.js").write_bytes(b"// js")
    with pytest.raises(ValueError,
                       match="index.html.*_next/static|reference.*_next"):
        ch.validate_candidate_root(root)


def test_validate_candidate_root_accepts_real_next_static_export(tmp_path):
    """A real Next.js static export root passes: non-empty
    `_next/static/` directory AND `index.html` references
    `/_next/static/`."""
    root = _make_candidate_root(tmp_path / "candidate")
    result = ch.validate_candidate_root(root)
    assert result["static_dir_present"] is True
    assert result["candidate_root"] == str(root.resolve())


# ---------------------------------------------------------------------------
# Task 15 — Client-side HTTP safety boundary.
#
# Context: a previous G5 capture run exercised a target that exposed
# mutators (no mutating method was actually observed, but this was a
# procedure deviation). This slice adds a CLIENT-SIDE boundary in the
# Playwright adapter that permits only GET/HEAD/OPTIONS; every other
# request MUST be aborted BEFORE network/server and MUST fail the
# capture closed (no partial output publication).
#
# Tested via the strict Playwright sync-API fake (page/route seam).
# No real browser, no real server.
# ---------------------------------------------------------------------------


def test_route_handler_permits_only_get_head_options():
    """Client-side safety boundary: GET / HEAD / OPTIONS are the only
    HTTP methods the adapter permits. Each safe method MUST call
    `route.continue_()` and MUST NOT call `route.abort()`."""
    adapter = ch.PlaywrightBrowserAdapter()
    for method in ("GET", "HEAD", "OPTIONS"):
        route = _StrictRoute(method=method)
        adapter.route_handler(route)
        assert route.continued, (
            f"{method} must call route.continue_()")
        assert not route.aborted, (
            f"{method} must NOT call route.abort()")


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_route_handler_blocks_mutating_method_and_fails_capture(method):
    """Every mutating method MUST be aborted AND raise to fail the
    capture closed. The handler aborts the request before network and
    then raises — `collect_raw_samples` propagates and the CLI never
    writes `--out` (no partial publication)."""
    adapter = ch.PlaywrightBrowserAdapter()
    route = _StrictRoute(method=method)
    with pytest.raises(RuntimeError, match="blocked unsafe HTTP method"):
        adapter.route_handler(route)
    assert route.aborted, (
        f"{method} MUST call route.abort() before raising")
    assert not route.continued, (
        f"{method} MUST NOT call route.continue_()")


@pytest.mark.parametrize("bad_method", ["TRACE", "CONNECT", "FOOBAR", "", None])
def test_route_handler_blocks_unknown_or_non_string_method(bad_method):
    """Defensive: unknown, empty, or non-string methods MUST fail
    closed (treated as mutating). An empty / missing method MUST NOT
    silently pass through as if it were GET."""
    adapter = ch.PlaywrightBrowserAdapter()
    route = _StrictRoute(method=bad_method)
    with pytest.raises(RuntimeError, match="blocked unsafe HTTP method"):
        adapter.route_handler(route)
    assert route.aborted
    assert not route.continued


def test_route_handler_method_match_is_case_insensitive():
    """Method matching is case-insensitive. HTTP method names are
    conventionally uppercase but defensive parsing accepts lowercase
    so a misbehaving server or proxy cannot smuggle a mutating verb
    past the boundary."""
    adapter = ch.PlaywrightBrowserAdapter()
    for method in ("get", "head", "options"):
        route = _StrictRoute(method=method)
        adapter.route_handler(route)
        assert route.continued, f"lowercase {method} must be allowed"
        assert not route.aborted
    for method in ("post", "put", "delete", "patch"):
        route = _StrictRoute(method=method)
        with pytest.raises(RuntimeError, match="blocked unsafe"):
            adapter.route_handler(route)
        assert route.aborted
        assert not route.continued


def test_route_handler_aborts_before_attempting_continue(monkeypatch):
    """The unsafe-method branch MUST call abort() and never
    continue_() — aborting BEFORE attempting continue is the
    safety-boundary invariant (the request must NOT be allowed to
    reach the network/server)."""
    adapter = ch.PlaywrightBrowserAdapter()
    route = _StrictRoute(method="POST")
    calls: list = []
    monkeypatch.setattr(route, "abort", lambda: calls.append("abort"))
    monkeypatch.setattr(route, "continue_", lambda: calls.append("continue"))
    with pytest.raises(RuntimeError, match="blocked unsafe HTTP method"):
        adapter.route_handler(route)
    assert calls == ["abort"], (
        f"unsafe-method branch MUST call abort() only; got {calls!r}")


def test_run_iteration_registers_route_handler_before_goto(monkeypatch):
    """`page.route(handler)` MUST be called inside `run_iteration`
    BEFORE `page.goto()` so the safety boundary intercepts requests
    before they hit the network/server."""
    _LAST_BROWSER_PAGES.clear()
    cm = _StrictPlaywrightCM()
    fake_module = types.SimpleNamespace(sync_playwright=lambda: cm)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_module)

    adapter = ch.PlaywrightBrowserAdapter()
    adapter.run_iteration(
        target_url=TARGET_URL,
        dom_marker_selector=ch.DEFAULT_DOM_MARKER_SELECTOR,
        iteration_index=0,
    )

    assert len(_LAST_BROWSER_PAGES) == 1, (
        "expected exactly one page from run_iteration")
    page = _LAST_BROWSER_PAGES[0]
    assert len(page.route_handlers) >= 1, (
        "page.route(handler) MUST be registered before page.goto() so the "
        "client-side safety boundary is in place")
    # PIN THE ORDER: `page.route(...)` MUST precede `page.goto(...)`.
    # The mere presence of a registered handler is NOT enough — a
    # regression that arms the boundary AFTER navigation would still
    # leave at least one handler attached, but every request fired
    # during the unfiltered goto would slip past the safety boundary
    # to the network/server. The first relevant page event MUST
    # therefore be a `route` registration, NOT a `goto`.
    relevant_kinds = [
        kind for kind, *_ in page.event_log if kind in ("route", "goto")
    ]
    assert relevant_kinds, (
        f"page.event_log must record at least one route/goto event; "
        f"got {page.event_log!r}")
    assert relevant_kinds[0] == "route", (
        f"page.route(...) MUST be called BEFORE page.goto(...); "
        f"first relevant page event was {relevant_kinds[0]!r}; "
        f"full event_log: {page.event_log!r}")


def test_run_iteration_fails_closed_when_route_blocks_mutating_request(
        monkeypatch):
    """Integration via the page/route seam: when the page's goto
    drives a mutating method through the registered route handler,
    the handler aborts the request AND raises to fail the iteration
    closed (no partial sample returned)."""
    _LAST_BROWSER_PAGES.clear()
    cm = _StrictPlaywrightCM()
    fake_module = types.SimpleNamespace(sync_playwright=lambda: cm)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_module)

    # Wrap `_StrictBrowser.new_page` so the page's goto fires a POST
    # through the registered route handlers (the seam is local to
    # the run — no real browser, no real server).
    original_new_page = _StrictBrowser.new_page

    def post_new_page(self):
        page = original_new_page(self)

        def post_goto(url, wait_until=None):
            if page.route_handlers:
                route = _StrictRoute(method="POST", url=url)
                for h in page.route_handlers:
                    h(route)
            return _StrictResponse()

        page.goto = post_goto
        return page

    monkeypatch.setattr(_StrictBrowser, "new_page", post_new_page)

    adapter = ch.PlaywrightBrowserAdapter()
    with pytest.raises(RuntimeError, match="blocked unsafe HTTP method"):
        adapter.run_iteration(
            target_url=TARGET_URL,
            dom_marker_selector=ch.DEFAULT_DOM_MARKER_SELECTOR,
            iteration_index=0,
        )


def test_collect_raw_samples_propagates_blocked_mutating_request(
        monkeypatch):
    """End-to-end: when the safety boundary aborts a mutating request,
    `collect_raw_samples` MUST propagate the exception — NO partial
    sample, NO partial publication. The CLI never writes `--out` when
    `collect_raw_samples` raises."""
    _LAST_BROWSER_PAGES.clear()
    cm = _StrictPlaywrightCM()
    fake_module = types.SimpleNamespace(sync_playwright=lambda: cm)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_module)

    original_new_page = _StrictBrowser.new_page

    def post_new_page(self):
        page = original_new_page(self)

        def post_goto(url, wait_until=None):
            if page.route_handlers:
                route = _StrictRoute(method="POST", url=url)
                for h in page.route_handlers:
                    h(route)
            return _StrictResponse()

        page.goto = post_goto
        return page

    monkeypatch.setattr(_StrictBrowser, "new_page", post_new_page)

    adapter = ch.PlaywrightBrowserAdapter()
    with pytest.raises(RuntimeError, match="blocked unsafe HTTP method"):
        ch.collect_raw_samples(
            target_url=TARGET_URL, browser_adapter=adapter,
        )
    # The adapter must have attempted exactly one iteration before
    # the boundary aborted and raised — no samples were emitted.
    assert len(_LAST_BROWSER_PAGES) == 1


def test_playwright_adapter_has_public_safe_methods_contract():
    """Contract surface: the adapter MUST expose the safe-method set
    so tests, reviewers, and downstream tools can read what the
    boundary permits without scraping source code."""
    adapter = ch.PlaywrightBrowserAdapter()
    safe = getattr(adapter, "_SAFE_HTTP_METHODS", None) \
        or getattr(ch, "_SAFE_HTTP_METHODS", None)
    assert safe is not None, (
        "PlaywrightBrowserAdapter / module MUST expose "
        "_SAFE_HTTP_METHODS for the safety boundary contract")
    assert set(safe) == {"GET", "HEAD", "OPTIONS"}, (
        f"_SAFE_HTTP_METHODS MUST be exactly GET/HEAD/OPTIONS; got {set(safe)!r}"
    )


# ---------------------------------------------------------------------------
# Task 15 — `validate_candidate_root` docstring + read-once contract.
#
# The docstring MUST be aligned with caller-supplied `target_url`
# behavior: this function NEVER fetches `<target-url>/index.html`
# (that role belongs to `_http_get_index`, called separately by
# `collect_migrated_samples`). The function MUST also read
# `<root>/index.html` exactly once and reuse the same bytes for
# both the static-reference check AND the SHA-256 hash so a writer
# racing the validation cannot split the trust contract.
# ---------------------------------------------------------------------------


def test_validate_candidate_root_docstring_does_not_claim_url_fetch():
    """`validate_candidate_root` is strictly local. The docstring MUST
    NOT claim that it fetches `<target-url>/index.html` (the served-body
    pre-flight lives in `_http_get_index`, called separately by
    `collect_migrated_samples`)."""
    doc = ch.validate_candidate_root.__doc__ or ""
    # Must NOT reference `<target-url>` — this function is local-only.
    assert "<target-url>" not in doc, (
        f"validate_candidate_root is local-only; docstring must NOT "
        f"reference `<target-url>` (URL fetching is `_http_get_index`'s "
        f"role, called by `collect_migrated_samples`). Got:\n{doc!r}")
    # Must NOT contain phrasing that implies this function performs an
    # HTTP fetch on its own.
    assert "Pre-flight fetches" not in doc, (
        f"docstring must NOT claim this function 'Pre-flight fetches' "
        f"the served URL. Got:\n{doc!r}")
    # Must clearly identify itself as a local / on-disk validation so
    # callers understand the trust boundary.
    assert "local" in doc.lower() or "on disk" in doc.lower() \
        or "on-disk" in doc.lower(), (
        f"docstring must clearly identify this function as local-only "
        f"(mention 'local' / 'on disk' / 'on-disk'). Got:\n{doc!r}")


def test_validate_candidate_root_reads_index_html_bytes_once(
        tmp_path, monkeypatch):
    """`validate_candidate_root` MUST read `<root>/index.html` exactly
    once and reuse the same bytes for BOTH the static-reference check
    AND the SHA-256 hash. Reading the file twice could race a writer
    that swaps the file mid-validation, silently inverting the trust
    contract (the static-reference check would see one revision and
    the SHA-256 would be pinned to a different one)."""
    root = _make_candidate_root(tmp_path / "candidate")
    read_calls: list = []
    real_read_bytes = Path.read_bytes

    def tracking_read_bytes(self):
        # Track only the candidate-root index.html (other Paths in the
        # validation flow stay unobserved).
        try:
            if self.name == "index.html" and \
                    self.parent.resolve() == root.resolve():
                read_calls.append(self)
        except (OSError, ValueError):
            pass
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", tracking_read_bytes)
    result = ch.validate_candidate_root(root)
    assert read_calls == [root / "index.html"], (
        f"index.html must be read exactly once; got {len(read_calls)} "
        f"calls: {[str(p) for p in read_calls]}")
    expected_hash = hashlib.sha256(
        (root / "index.html").read_bytes()).hexdigest()
    assert result["candidate_index_sha256"] == expected_hash
    assert result["static_dir_present"] is True
