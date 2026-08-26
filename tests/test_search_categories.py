"""
Browser-level tests for the category grouping of search engines (P1 #3
from the Impeccable critique).

The Search tab used to render 14 engine buttons as a flat grid with no
visual hierarchy. First-time users couldn't tell which engines target
taxonomic literature vs. general web. The fix groups them into 5
categories: general, taxonomic, academic, multimedia, documents.

These tests boot a real uvicorn on a non-default port, open the page in
headless chromium via Playwright, and assert:
- 5 .search-category-header elements render in the expected order.
- Each header shows the expected icon + label.
- Each category contains the expected set of engine buttons.
- All 14 buttons remain queryable in the DOM (existing tests stay green).

Skipped if playwright or the chromium binary is not installed (the
project's `make venv` + `playwright install chromium` covers this; the
skip is a graceful degradation for the offline CI case where neither is
available).

Usage:
    make api                                          # in another terminal
    .venv/bin/python -m pytest tests/test_search_categories.py -v -s
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

PORT = 8769  # non-default to avoid conflicts with dev API (8765), web
             # toggle test fixture (8767), and detail overview test
             # fixture (8768).
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
            pass
        time.sleep(0.2)
    return False


def _check_playwright_available():
    """Skip the module if playwright isn't importable."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return None
    return True


@pytest.fixture(scope="module")
def api_server():
    """Spawn a fresh uvicorn on PORT for the duration of the module.

    Skips if the port is in use or uvicorn fails to come up in 10s.
    Yields the base URL plus the discovered freshwater root id (needed
    to drive the per-row kebab → "Search online" item flow).
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
        domains = json.loads(
            urllib.request.urlopen(f"{BASE_URL}/api/domains", timeout=5).read()
        )
        freshwater = next(
            (d for d in domains if d.get("freshwater_id") is not None
             and d.get("freshwater_parent_id") is None),
            None,
        )
        yield {
            "base_url": BASE_URL,
            "freshwater_root_id": freshwater["id"] if freshwater else None,
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_search_engines_grouped_by_category(api_server):
    """The 14 search-engine buttons are grouped under 5 category headers
    inside the Search tab.

    P1 #3 from the Impeccable critique: the Search tab used to be a
    flat grid of 14 buttons with no visual hierarchy, so first-time
    users couldn't tell which engines target taxonomic literature vs.
    general web. This test pins the new grouping contract:

    - 5 .search-category-header elements render, in this exact order:
      general, taxonomic, academic, multimedia, documents.
    - Each header shows the expected user-visible label.
    - Each category contains exactly the expected set of engine
      buttons, scoped via a `data-category` attribute so the test
      doesn't depend on DOM ordering of siblings.
    - The existing single .search-engines-grid still wraps all 14
      buttons (test_search_engines_rendered_as_button_grid continues
      to pass without modification).

    Expected grouping (matches CATEGORIES in web/search_urls.js):
        general     -> google, wikipedia
        taxonomic   -> bhl, zootaxa
        academic    -> researchgate, plos, academia, scielo, scholar
        multimedia  -> imagen, youtube
        documents   -> documentos, pdf, scribd
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
            kebab = page.locator(
                f'[data-taxon-id="{fresh_id}"] [data-action="toggle-kebab"]'
            ).first
            expect(kebab).to_be_visible(timeout=5_000)
            kebab.click()
            search_item = page.locator(
                f'[data-taxon-id="{fresh_id}"] [data-action="open-searches"]'
            ).first
            expect(search_item).to_be_visible(timeout=5_000)
            search_item.click()
            panel = page.locator("#detail-panel")
            search_tab = panel.locator('[data-tab="searches"]')
            expect(search_tab).to_be_visible(timeout=5_000)
            search_tab.click()
            tab_content = panel.locator('[data-tab-content="searches"]')

            # 5 headers, exact category order, exact labels.
            headers = tab_content.locator(".search-category-header")
            expect(headers.first).to_be_visible(timeout=5_000)
            header_count = headers.count()
            assert header_count == 5, (
                f"expected 5 category headers, got {header_count}"
            )
            cats = [h.get_attribute("data-category") for h in headers.all()]
            assert cats == [
                "general", "taxonomic", "academic", "multimedia", "documents",
            ], f"unexpected category order: {cats}"
            header_texts = [
                # The label is the LAST <span> child of the header —
                # the first <span.material-symbols-outlined> carries the
                # icon glyph (rendered as a Material ligature) which
                # would leak into inner_text(). Use text_content() so
                # the CSS text-transform: uppercase doesn't render the
                # label as ALL CAPS in the assertion.
                h.locator("span:last-child").text_content().strip()  # type: ignore[union-attr]
                for h in headers.all()
            ]
            assert header_texts == [
                "General", "Taxonomic", "Academic",
                "Multimedia", "Documents",
            ], f"unexpected header labels: {header_texts}"

            # Each category has the expected engines, scoped via
            # data-category on the button. This avoids counting siblings
            # across headers (the grid is one flat list).
            expected = {
                "general":    {"google", "wikipedia"},
                "taxonomic":  {"bhl", "zootaxa"},
                "academic":   {"researchgate", "plos", "academia", "scielo", "scholar"},
                "multimedia": {"imagen", "youtube"},
                "documents":  {"documentos", "pdf", "scribd"},
            }
            total = 0
            for cat, expected_keys in expected.items():
                cat_btns = tab_content.locator(
                    f'a.search-engine-btn[data-category="{cat}"]'
                )
                expect(cat_btns.first).to_be_visible(timeout=2_000)
                keys = {
                    b.get_attribute("data-engine-key")
                    for b in cat_btns.all()
                }
                assert keys == expected_keys, (
                    f"category {cat!r}: expected {expected_keys}, "
                    f"got {keys}"
                )
                total += len(keys)
            assert total == 14, (
                f"all categories together must contain 14 buttons, got {total}"
            )

            # The single .search-engines-grid still wraps everything
            # (test_search_engines_rendered_as_button_grid pins this).
            grid = tab_content.locator(".search-engines-grid")
            expect(grid).to_be_visible(timeout=5_000)
            assert (
                grid.evaluate("el => getComputedStyle(el).display") == "grid"
            ), "search engines container should remain a CSS grid"
        finally:
            browser.close()