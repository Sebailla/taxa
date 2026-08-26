"""
Browser-level tests for the Overview section added to the detail panel
(P1 #1 from the Impeccable critique).

The Overview renders BEFORE the Search/Folder tabs when the selected
taxon has empty vernaculars + synonyms + distribution data. For taxa
where ANY of those three has data, the Overview is suppressed entirely —
the existing data tabs are more useful than a generic summary.

These tests boot a real uvicorn on a non-default port, open the page
in headless chromium via Playwright, and assert the Overview behaviour
for both the "all empty" case (Archaea, a top-level domain) and the
"vernaculars present" case (Homo sapiens).

Skipped if playwright or the chromium binary is not installed (the
project's `make venv` + `playwright install chromium` covers this; the
skip is a graceful degradation for the offline CI case where neither is
available).

Usage:
    make api                                          # in another terminal
    .venv/bin/python -m pytest tests/test_detail_overview.py -v -s
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

PORT = 8768  # non-default to avoid conflicts with dev API (8765) and the
             # web toggle test fixture (8767).
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

    Yields the base URL.
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
        yield BASE_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _check_playwright_available():
    """Return True if playwright is importable, else None.

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
def test_overview_renders_for_top_level_taxon_without_data(api_server):
    """Archaea (a top-level domain with no vernaculars/synonyms/distribution)
    renders an Overview section in the detail panel — so the user sees the
    rank, status, authorship, species count, and parent chain instead of
    just the Search + Folder tabs.

    P1 #1 from the Impeccable critique: the detail panel used to be
    search-grid-first even for top-level taxa, which is pedagogically
    empty. This test pins the Overview behaviour for taxa whose vernacular
    + synonym + distribution data is all empty.

    Test mechanism: discover Archaea's id from /api/domains (its id is
    stable across loads of the same DB but we don't hardcode it), click
    the per-row search icon to open the detail panel, then assert the
    Overview section + tab render and that Overview is the active tab
    by default (since no other data exists).
    """
    from playwright.sync_api import expect, sync_playwright  # type: ignore

    base = api_server
    domains = json.loads(
        urllib.request.urlopen(f"{base}/api/domains", timeout=5).read()
    )
    archaea = next(
        (d for d in domains if d.get("scientific_name") == "Archaea"), None
    )
    if archaea is None:
        pytest.skip("Archaea domain not found in /api/domains")

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium binary not available: {exc!r}")
        try:
            page = browser.new_page()
            page.goto(
                base + "/", wait_until="domcontentloaded", timeout=10_000
            )
            # Archaea is rank=domain (not a species), so its row toggles
            # expansion rather than selecting. P1 #2 collapsed the
            # per-row lupa into a kebab dropdown, so to open the
            # detail panel for a non-species row we drive the kebab
            # menu's "Search online" item. The kebab trigger has
            # `opacity: 0` by default but a non-zero bounding box —
            # Playwright treats it as clickable, so no hover step
            # is needed (real users will see it appear on row hover).
            kebab = page.locator(
                f'[data-taxon-id="{archaea["id"]}"] [data-action="toggle-kebab"]'
            ).first
            expect(kebab).to_be_visible(timeout=5_000)
            kebab.click()
            search_item = page.locator(
                f'[data-taxon-id="{archaea["id"]}"] [data-action="open-searches"]'
            ).first
            expect(search_item).to_be_visible(timeout=5_000)
            search_item.click()
            panel = page.locator("#detail-panel")
            expect(panel).to_be_visible(timeout=5_000)
            # Overview tab must render in the tab strip.
            overview_tab = panel.locator('[data-tab="overview"]')
            expect(overview_tab).to_be_visible(timeout=5_000)
            # Overview tab must be the active default when no other
            # data exists (P1 #1 spec: "Make Overview the default
            # active tab"). aria-pressed=true is what renderDetailPanel
            # sets on the active tab.
            assert (
                overview_tab.evaluate(
                    "el => el.getAttribute('aria-pressed')"
                )
                == "true"
            ), "Overview tab should be active by default for taxa with no vernacular/synonym/distribution data"
            # Overview content must render too (not just the tab button).
            overview_content = panel.locator(
                '[data-tab-content="overview"]'
            )
            expect(overview_content).to_be_visible(timeout=5_000)
            # The Overview rows should at minimum show the scientific
            # name and status — both are mandatory fields.
            assert (
                overview_content.get_by_text("Scientific name:").count() == 1
            ), "Overview should show a 'Scientific name:' label"
            assert (
                overview_content.get_by_text("Status:").count() == 1
            ), "Overview should show a 'Status:' label"
        finally:
            browser.close()


@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_overview_suppressed_when_vernaculars_exist(api_server):
    """When the taxon has vernaculars (or synonyms or distribution),
    the Overview section is suppressed — the existing data tabs are
    more useful than an Overview summary, and the spec explicitly
    states "Overview section must NOT show when there's vernacular/
    synonym/distribution data — only when ALL THREE are empty."

    Test mechanism: search for "sapiens" to find Homo sapiens, click
    the first Homo sapiens result (which has 3 vernaculars), and
    assert that the Overview tab is absent from the tab strip and
    the Overview content is absent from the panel. The Vernaculars
    tab must still be present.
    """
    from playwright.sync_api import expect, sync_playwright  # type: ignore

    base = api_server

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium binary not available: {exc!r}")
        try:
            page = browser.new_page()
            page.goto(
                base + "/", wait_until="domcontentloaded", timeout=10_000
            )
            # Drive the search input. Search is debounced (200ms in
            # web/search.js) so the .open class lands after a beat.
            page.fill("#search-input", "sapiens")
            expect(
                page.locator("#search-results.open")
            ).to_be_visible(timeout=5_000)
            # Click the first Homo sapiens row in the dropdown.
            # The dropdown carries multiple "sapiens" matches; we
            # filter on the scientific name to disambiguate.
            homo = page.locator(
                "#search-results [data-taxon-id]"
            ).filter(has_text="Homo sapiens").first
            expect(homo).to_be_visible(timeout=5_000)
            homo.click()
            # Wait for the detail panel + vernacular fetch to land.
            panel = page.locator("#detail-panel")
            expect(panel).to_be_visible(timeout=5_000)
            # Sanity check: Vernaculars tab must be present (the test
            # would be vacuous otherwise). Wait for it explicitly
            # because the vernacular fetch + re-render happens after
            # the panel first paints with "Loading details…".
            vern_tab = panel.locator('[data-tab="vernaculars"]')
            expect(vern_tab).to_be_visible(timeout=5_000)
            # Overview tab MUST NOT be in the tab strip.
            overview_tab_count = panel.locator(
                '[data-tab="overview"]'
            ).count()
            assert overview_tab_count == 0, (
                f"Overview tab should not render when vernaculars exist "
                f"(got {overview_tab_count} matches)"
            )
            # Overview content MUST NOT be in the panel.
            overview_content_count = panel.locator(
                '[data-tab-content="overview"]'
            ).count()
            assert overview_content_count == 0, (
                f"Overview content should not render when vernaculars exist "
                f"(got {overview_content_count} matches)"
            )
        finally:
            browser.close()
