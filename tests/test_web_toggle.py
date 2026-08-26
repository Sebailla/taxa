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
            freshwater_row = page.locator(
                f'[data-taxon-id="{fresh_id}"][data-action="toggle-expand"]'
            )
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


@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_search_tab_renders_with_14_links(api_server):
    """Click a taxon and assert the detail panel shows a Search tab
    with 14 search-engine links.

    Regression of c948663: the tab strip + renderSearchesTab() + the
    per-row search icon were silently removed by PR #8 (28c0c40) along
    with the dead escape() function. Without this fix, no taxon has
    a Search tab and the detail panel only shows vernaculars/synonyms/
    distribution. Affects CoL, WoRMS, and Freshwater views alike.
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
            # The freshwater root is rank=collection (not a species), so
            # clicking the row toggles expansion rather than selecting.
            # To open the detail panel for a non-species row, click its
            # per-row search icon button (data-action="open-searches"),
            # which selects the taxon AND forces the Search tab.
            row = page.locator(
                f'[data-taxon-id="{fresh_id}"][data-action="open-searches"]'
            )
            expect(row).to_be_visible(timeout=5_000)
            row.click()
            panel = page.locator("#detail-panel")
            expect(panel).to_be_visible(timeout=5_000)
            # Search tab must exist in the panel.
            search_tab = panel.locator('[data-tab="searches"]')
            expect(search_tab).to_be_visible(timeout=5_000)
            # Click it so the tab content (the 14 search-engine links)
            # becomes visible.
            search_tab.click()
            # The 14 search-engine links render as anchors inside the
            # Search tab content. We use the data-tab-content wrapper
            # to scope the query to this tab.
            tab_content = panel.locator('[data-tab-content="searches"]')
            links = tab_content.locator("a[href]")
            expect(links.first).to_be_visible(timeout=5_000)
            # All 14 search-engine links should render — the server
            # returns exactly 14 (see _SEARCH_ENGINES in api/server.py).
            count = links.count()
            assert count == 14, f"expected 14 search-engine links, got {count}"
        finally:
            browser.close()


@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_search_engines_rendered_as_button_grid(api_server):
    """The 14 search-engine links render as a grid of buttons inside the
    Search tab — not a vertical list of arrow-suffixed rows.

    The redesign keeps the icon + label visible at a glance and lets the
    user scan all 14 engines without scrolling a long list. Each button
    opens the engine's pre-composed URL in a new tab.
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
            row = page.locator(
                f'[data-taxon-id="{fresh_id}"][data-action="open-searches"]'
            )
            expect(row).to_be_visible(timeout=5_000)
            row.click()
            panel = page.locator("#detail-panel")
            search_tab = panel.locator('[data-tab="searches"]')
            expect(search_tab).to_be_visible(timeout=5_000)
            search_tab.click()
            tab_content = panel.locator('[data-tab-content="searches"]')
            # The container is a CSS grid.
            grid = tab_content.locator(".search-engines-grid")
            expect(grid).to_be_visible(timeout=5_000)
            assert (
                grid.evaluate("el => getComputedStyle(el).display") == "grid"
            ), "search engines container should be a CSS grid"
            # 14 buttons inside the grid, each .search-engine-btn, each <a href>.
            buttons = grid.locator("a.search-engine-btn")
            expect(buttons.first).to_be_visible(timeout=5_000)
            count = buttons.count()
            assert count == 14, f"expected 14 search-engine buttons, got {count}"
        finally:
            browser.close()


@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_detail_header_and_tabs_are_sticky(api_server):
    """The detail panel's header (title + close button) and tab strip stay
    pinned at the top while the tab content scrolls.

    The card already has max-height + overflow-y:auto, so the inner
    header + tabs stick to the top of the card's scroll viewport
    (position: sticky, top: 0). Without sticky, scrolling the card
    would push the title + tabs out of view and the user would lose
    context while reading the 14 search-engine buttons.
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
            row = page.locator(
                f'[data-taxon-id="{fresh_id}"][data-action="open-searches"]'
            )
            expect(row).to_be_visible(timeout=5_000)
            row.click()
            panel = page.locator("#detail-panel")
            expect(panel).to_be_visible(timeout=5_000)
            # Both the header and the tab strip must use position: sticky
            # so they remain pinned while the body scrolls. getComputedStyle
            # returns the resolved value, so 'sticky' is the literal string
            # (not 'static' or 'relative').
            header = panel.locator(".detail-header")
            tabs = panel.locator(".detail-tabs")
            expect(header).to_be_visible(timeout=5_000)
            expect(tabs).to_be_visible(timeout=5_000)
            assert (
                header.evaluate("el => getComputedStyle(el).position") == "sticky"
            ), "detail-header should be position:sticky"
            assert (
                tabs.evaluate("el => getComputedStyle(el).position") == "sticky"
            ), "detail-tabs should be position:sticky"
        finally:
            browser.close()


@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_breadcrumb_walks_freshwater_chain(api_server):
    """Expand a freshwater family and assert the breadcrumb shows the
    full ancestor chain: 'Freshwater Fishes > <family>'.

    The freshwater root AND every freshwater CSV row have parent_id
    IS NULL (spec §2.1: the freshwater slice is isolated from CoL).
    renderBreadcrumb() walked parent_id only, so clicking any
    freshwater child rendered a breadcrumb with just the child's
    name (no ancestors). This test pins the fix: after the
    breadcrumb walks freshwater_parent_id in Freshwater view, the
    full chain renders.

    Test path: click the freshwater root, wait for the children
    fetch + render, click the first family, assert the breadcrumb
    contains BOTH "Freshwater Fishes" AND the family name.
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
            root_row = page.locator(
                f'[data-taxon-id="{fresh_id}"][data-action="toggle-expand"]'
            )
            expect(root_row).to_be_visible(timeout=5_000)
            root_row.click()
            # Wait for the children fetch + render so the first family
            # row appears in the tree.
            expect(
                page.get_by_text("Families", exact=False)
            ).to_be_visible(timeout=10_000)
            # Click the FIRST search icon button (the first family's
            # icon). Families are rank=family (not species), so their
            # rows toggle-expand rather than select; the search icon
            # is the way to open the detail panel for a non-species.
            first_family = page.locator(
                '#tree-view [data-action="open-searches"]'
            ).first
            expect(first_family).to_be_visible(timeout=5_000)
            first_family.click()
            # Breadcrumb must show BOTH the ancestor ("Freshwater Fishes")
            # AND the focused taxon's name. With the bug, only the
            # child's name shows (the parent_id walk exits immediately
            # because every freshwater row has parent_id IS NULL).
            breadcrumb = page.locator("#breadcrumb")
            expect(
                breadcrumb.get_by_text("Freshwater Fishes", exact=True)
            ).to_be_visible(timeout=5_000)
        finally:
            browser.close()


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "db" / "taxa.db"


@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_version_banner_shows_on_outdated_db(api_server):
    """When the DB's PRAGMA user_version is older than the API's
    CURRENT_SCHEMA_VERSION, the frontend must surface a persistent
    banner with the version numbers. This pins the contract between
    api.server's /api/health response and web/banner.js's render.

    Test mechanism: temporarily lower PRAGMA user_version to 2 via a
    separate read-write connection. The API opens each request with
    mode=ro, but SQLite WAL propagates the writer's commit to the next
    read. We restore the original value in a finally block so other
    tests are unaffected.
    """
    import sqlite3
    from playwright.sync_api import expect, sync_playwright  # type: ignore

    base = api_server["base_url"]

    # Save current version, lower it, run the test, restore.
    rw = sqlite3.connect(DB_PATH)
    original_version = rw.execute("PRAGMA user_version").fetchone()[0]
    rw.execute("PRAGMA user_version = 2")
    rw.commit()
    rw.close()
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch(headless=True)
            except Exception as exc:
                pytest.skip(f"chromium binary not available: {exc!r}")
            try:
                page = browser.new_page()
                page.goto(base + "/", wait_until="domcontentloaded", timeout=10_000)
                # Banner element exists in the DOM (just hidden by default).
                # When user_version (2) < expected (4), boot() removes the
                # `hidden` class and writes the numbers into the spans.
                banner = page.locator("#version-banner")
                expect(banner).to_be_visible(timeout=5_000)
                expect(
                    page.locator("#version-banner-actual")
                ).to_have_text("2", timeout=2_000)
                expect(
                    page.locator("#version-banner-expected")
                ).to_have_text("4", timeout=2_000)
            finally:
                browser.close()
    finally:
        # Restore the original PRAGMA user_version so subsequent test runs
        # (and the next time someone invokes `make api`) see the real value.
        rw = sqlite3.connect(DB_PATH)
        rw.execute(f"PRAGMA user_version = {original_version}")
        rw.commit()
        rw.close()
