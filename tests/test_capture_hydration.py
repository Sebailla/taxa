"""Strict-TDD tests for scripts/capture_hydration.py (G5 raw Playwright
legacy collector). TEN browser samples, per-sample nav/paint/DOM-marker/
console + Chromium/Playwright/env provenance; in-memory + raw JSON;
fail-closed on iteration failure. No Lighthouse, no G5 launcher call,
no parity-reports emission. Hermetic via FakeBrowserAdapter.
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

import scripts.capture_hydration as ch


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "capture_hydration.py"
TARGET_URL = "http://127.0.0.1:8765/"


class FakeBrowserAdapter:
    """Hermetic test double. Records `calls` for fail-closed assertions."""
    def __init__(self, *, raise_on=None, raise_message="synthetic iteration failure"):
        self._raise_on, self._raise_message = raise_on, raise_message
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
            "dom_marker": {"selector": dom_marker_selector, "found": True,
                           "count": 1, "first_text": "x", "wait_ms": 0.0},
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
        return _StrictPage()

    def close(self):
        self._closed = True


class _StrictPage:
    def on(self, event, handler):
        pass

    def goto(self, url, wait_until=None):
        return _StrictResponse()

    def evaluate(self, script):
        return {}

    def wait_for_selector(self, sel, timeout=5000):
        pass

    @property
    def locator(self):
        return _StrictLocator()


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
