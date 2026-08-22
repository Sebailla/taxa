"""
Browser-side smoke test for the Freshwater toggle (R-2 from the
archive-report).

The other pytest tests in this repo are backend-only (TestClient +
in-memory SQLite). This file is the first browser-level test: it boots
a real uvicorn on a non-default port, opens the page in headless
chromium via Playwright, and asserts the dynamic toggle renders all
three source buttons and that clicking Freshwater drills into the
freshwater tree.

Skipped if playwright or the chromium binary is not installed (the
project's `make venv` + `playwright install chromium` covers this; the
skip is a graceful degradation for the offline CI case where neither is
available).

Usage:
    make api                                          # in another terminal
    .venv/bin/python -m pytest tests/test_web_toggle.py -v -s
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

PORT = 8767  # non-default to avoid conflicts with the dev API on 8765
BASE_URL = f"http://127.0.0.1:{PORT}"


def _port_free(port: int) -> bool:
    """Check if a TCP port is free (no listener)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        try:
            s.connect(("127.0.0.1", port))
        except (ConnectionRefusedError, socket.timeout):
            return True
        return False


def _wait_ready(url: str, timeout: float = 10.0) -> bool:
    """Poll the API until it responds or the timeout elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            # OSError covers socket.timeout (= TimeoutError in py3.10+)
            # which fires when the server accepts the connection but
            # doesn't respond in time.
            pass
        time.sleep(0.2)
    return False


@pytest.fixture(scope="module")
def api_server():
    """Spawn a fresh uvicorn on PORT for the duration of the module.

    Skips if the port is already in use (another test instance, the dev
    API, etc.) or if uvicorn fails to come up in 10s. Uses sys.executable
    so the fixture works in any environment that has uvicorn installed
    (local .venv, system pip, CI image, etc.) — the previous hardcoded
    .venv/bin/python3 path broke CI which installs packages globally.

    Yields a dict with `base_url` plus the discovered `freshwater_root_id`
    and `non_freshwater_root_names` (the roots that MUST be hidden in
    freshwater view, derived from /api/domains) so isolation tests stay
    DB-agnostic.
    """
    if not _port_free(PORT):
        pytest.skip(f"port {PORT} is in use; cannot start test API server")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.server:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not _wait_ready(f"{BASE_URL}/api/health"):
            proc.terminate()
            pytest.skip("test API server failed to come up within 10s")
        # Discover the freshwater root id from /api/domains so the
        # expand-to-families test stays valid if the DB reseeds with
        # different ids (it's only stable across loads of the same DB).
        domains = json.loads(
            urllib.request.urlopen(f"{BASE_URL}/api/domains", timeout=5).read()
        )
        freshwater = next(
            (d for d in domains if d.get("freshwater_id") is not None
            and d.get("freshwater_parent_id") is None),
            None,
        )
        non_freshwater_names = [
            d["scientific_name"] for d in domains
            if d.get("freshwater_id") is None
        ]
        yield {
            "base_url": BASE_URL,
            "freshwater_root_id": freshwater["id"] if freshwater else None,
            "non_freshwater_root_names": non_freshwater_names,
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _check_playwright_available():
    """Return the sync_playwright context manager, or None if not importable.

    Skips if playwright isn't installed; the project's Makefile target
    `make venv` installs it via requirements-dev.txt.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return None
    return True


@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_freshwater_toggle_renders_and_switches(api_server):
    """Open the page, assert the toggle has CoL/WoRMS/Freshwater, click
    Freshwater, assert the freshwater root appears in the tree.

    Skips if the chromium binary is not installed (CI doesn't ship it
    by default; local devs run `playwright install chromium` once).
    """
    from playwright.sync_api import expect, sync_playwright  # type: ignore

    base = api_server["base_url"] if isinstance(api_server, dict) else api_server

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:  # FileNotFoundError on missing binary, plus
                                   # the broad playwright errors.
            pytest.skip(f"chromium binary not available: {exc!r}")
        try:
            page = browser.new_page()
            page.goto(base + "/", wait_until="domcontentloaded", timeout=10_000)

            # Toggle should be present with the three source buttons.
            toggle = page.locator("#tree-source-toggle")
            expect(toggle).to_be_visible(timeout=5_000)
            buttons = toggle.locator("[data-tree-source]")
            expect(buttons).to_have_count(3, timeout=5_000)
            sources = [b.get_attribute("data-tree-source") for b in buttons.all()]
            assert sources == ["col", "worms", "freshwater"], (
                f"unexpected toggle order: {sources}"
            )

            # Click Freshwater and confirm the synthetic root appears.
            page.locator('[data-tree-source="freshwater"]').click()
            expect(
                page.get_by_text("Freshwater Fishes", exact=True)
            ).to_be_visible(timeout=5_000)
        finally:
            browser.close()

@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_freshwater_view_isolates_to_root(api_server):
    """Click Freshwater and assert ONLY the freshwater root renders.

    Without proper source filtering the tree renders the 5 CoL/WoRMS
    roots alongside Freshwater Fishes (the bug from "freshwater no
    aparece solo, aparece con todos mesclados"). This test pins the
    isolation: in freshwater view, no other domain root should be
    visible.
    """
    from playwright.sync_api import expect, sync_playwright  # type: ignore

    base = api_server["base_url"]
    other_names = api_server["non_freshwater_root_names"]
    assert other_names, "no non-freshwater roots discovered from /api/domains"

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium binary not available: {exc!r}")
        try:
            page = browser.new_page()
            page.goto(base + "/", wait_until="domcontentloaded", timeout=10_000)
            # Wait for boot to render the initial CoL roots so we know
            # the toggle has settled before clicking.
            page.locator('[data-tree-source="freshwater"]').wait_for(
                state="visible", timeout=5_000)
            page.locator('[data-tree-source="freshwater"]').click()
            # Freshwater root must be present.
            expect(
                page.get_by_text("Freshwater Fishes", exact=True)
            ).to_be_visible(timeout=5_000)
            # Every other domain root must be absent from the tree.
            # Scoped to #tree-view so we don't false-positive on any
            # stray text elsewhere on the page.
            tree = page.locator("#tree-view")
            for name in other_names:
                count = tree.get_by_text(name, exact=True).count()
                assert count == 0, (
f"in freshwater view, {name!r} should not render "
f"in the tree (got {count} matches)"
                )
        finally:
            browser.close()

@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_freshwater_view_expands_to_families(api_server):
    """Click Freshwater, expand the synthetic root, assert families
    tier header renders. Without `source=freshwater` on the children
    fetch, the expand call returns 0 rows and the tree appears flat
    ("no despliega arbol"). With the fix, clicking the freshwater
    root should produce a tier header for its 249 families.
    """
    from playwright.sync_api import expect, sync_playwright  # type: ignore

    base = api_server["base_url"]
    fresh_id = api_server["freshwater_root_id"]
    if fresh_id is None:
        pytest.skip("no freshwater root in /api/domains — freshwater not loaded")

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium binary not available: {exc!r}")
        try:
            page = browser.new_page()
            page.goto(base + "/", wait_until="domcontentloaded", timeout=10_000)
            page.locator('[data-tree-source="freshwater"]').click()
            freshwater_row = page.locator(f'[data-taxon-id="{fresh_id}"]')
            expect(freshwater_row).to_be_visible(timeout=5_000)
            freshwater_row.click()
            # Wait for the children fetch + render. The tier header
            # renders synchronously after the fetch resolves, so a
            # "Families" text appearing confirms the children loaded
            # with `source=freshwater` (otherwise we'd get 0 rows and
            # no tier header at all).
            expect(
                page.get_by_text("Families", exact=False)
            ).to_be_visible(timeout=10_000)
        finally:
            browser.close()
