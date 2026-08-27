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
            # To open the detail panel for a non-species row, drive its
            # kebab menu: P1 #2 collapsed the per-row lupa into a kebab
            # dropdown, so the search action is now reached via the
            # `more_vert` trigger → "Search online" item.
            kebab = page.locator(
                f'[data-taxon-id="{fresh_id}"] [data-action="toggle-kebab"]'
            ).first
            expect(kebab).to_be_visible(timeout=5_000)
            kebab.click()
            # Kebab menu is now open — click the "Search online" item
            # which carries the legacy data-action="open-searches"
            # attribute. It selects the taxon AND opens the detail
            # panel on the Search tab.
            search_item = page.locator(
                f'[data-taxon-id="{fresh_id}"] [data-action="open-searches"]'
            ).first
            expect(search_item).to_be_visible(timeout=5_000)
            search_item.click()
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
            # P1 #2: open the per-row kebab first, then drive the
            # "Search online" item from the dropdown — the lupa lives
            # inside the kebab menu now, not inline on the row.
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
            # P1 #2: per-row lupa is inside the kebab menu now — open
            # the kebab, click the "Search online" item.
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
            # Click the FIRST family's kebab trigger, then its "Search
            # online" item. Families are rank=family (not species), so
            # their rows toggle-expand rather than select; the kebab
            # dropdown is the way to open the detail panel for a
            # non-species after P1 #2 collapsed the per-row lupa.
            # `kebab-trigger` always has a non-zero bounding box
            # (opacity-0 by default, but counts as visible for click
            # purposes), so Playwright clicks it without a hover step.
            first_kebab = page.locator(
                "#tree-view [data-action='toggle-kebab']"
            ).first
            expect(first_kebab).to_be_visible(timeout=5_000)
            first_kebab.click()
            first_search = page.locator(
                "#tree-view [data-action='open-searches']"
            ).first
            expect(first_search).to_be_visible(timeout=5_000)
            first_search.click()
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

@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason='playwright not installed (pip install playwright)',
)
def test_kebab_menu_toggles_on_repeated_trigger_click(api_server):
    """Clicking the kebab trigger must toggle the menu open/closed on
    each click.

    Regression: nav.js closed ALL open kebab menus BEFORE toggling
    the target. Since the kebab trigger is a sibling (not a child)
    of `.kebab-menu`, `e.target.closest('.kebab-menu.open')` returns
    null even when the trigger's own menu is open, so the global
    close-all ran first. By the time `toggleKebabMenu(trigger)`
    executed, the menu was already closed, so
    `opening = !menu.classList.contains('open')` flipped to `true`
    and the menu reopened. Net effect: clicking the trigger twice
    leaves the menu stuck open, and subsequent clicks feel
    unresponsive.

    This test exercises the closed -> open -> closed -> open cycle
    on the same trigger and asserts the `.open` class flips on
    every click.
    """
    import re

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
            # Hover the freshwater root row so its hover-gated
            # kebab-trigger becomes clickable (CSS opacity-0 -> 1).
            row = page.locator(f'[data-taxon-id="{fresh_id}"]').first
            expect(row).to_be_visible(timeout=5_000)
            row.hover()
            trigger = page.locator(
                f'[data-taxon-id="{fresh_id}"] button[data-action="toggle-kebab"]'
            ).first
            expect(trigger).to_be_attached(timeout=5_000)
            menu = page.locator(
                f'[data-taxon-id="{fresh_id}"] .kebab-menu'
            ).first

            # Click 1 — menu must open.
            trigger.click()
            expect(menu).to_have_class(re.compile(r"\bopen\b"), timeout=2_000)

            # Click 2 (same trigger) — menu must close. This is the
            # regression: nav.js's global close-all ran first and
            # closed the menu, then toggleKebabMenu reopened it
            # because by then `menu.classList.contains("open")` was
            # false. Before the fix this assertion fails.
            trigger.click()
            expect(menu).not_to_have_class(
                re.compile(r"\bopen\b"), timeout=2_000
            )

            # Click 3 — menu must open again. After the fix this is
            # the normal toggle path; we assert it so the test fails
            # loudly if a future change re-breaks the alternation.
            trigger.click()
            expect(menu).to_have_class(re.compile(r"\bopen\b"), timeout=2_000)
        finally:
            browser.close()





@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
@pytest.mark.parametrize("close_method", ["click_trigger", "click_outside", "press_escape", "kebab_item_action"])
def test_kebab_menu_reopens_after_each_close_method(
    api_server, close_method
):
    """After the kebab menu is closed (by ANY of the supported methods),
    clicking the trigger again MUST reopen the menu.

    Regression variants: the user's "it doesn\'t respond" complaint can
    mean different things depending on how they closed the menu. This
    parametrised test exercises every supported close path and asserts
    the next click on the trigger reopens the menu.

    Close methods covered:
      - click_trigger: click the trigger again (same trigger). Before
        the fix the trigger\'s sibling-of-menu layout made this leave
        the menu stuck open.
      - click_outside: click a non-kebab element. Fires the global
        close-all branch.
      - press_escape: keydown handler closes any open menu.
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
            row = page.locator(f'[data-taxon-id="{fresh_id}"]').first
            expect(row).to_be_visible(timeout=5_000)
            row.hover()
            trigger = page.locator(
                f'[data-taxon-id="{fresh_id}"] button[data-action="toggle-kebab"]'
            ).first
            expect(trigger).to_be_attached(timeout=5_000)
            menu = page.locator(
                f'[data-taxon-id="{fresh_id}"] .kebab-menu'
            ).first
            open_cls = __import__("re").compile(r"\bopen\b")

            # Open the menu.
            trigger.click()
            expect(menu).to_have_class(open_cls, timeout=2_000)

            # Close it using the method under test.
            if close_method == "click_trigger":
                trigger.click()
            elif close_method == "click_outside":
                # Click outside any kebab menu or trigger — the search
                # input is well outside #tree-view and has no data-action
                # so it doesn't dispatch any side-effect beyond closing
                # the search dropdown (which is already closed). Avoids
                # the source-toggle buttons because clicking those
                # switches the tree source and invalidates fresh_id.
                page.locator("#search-input").click()
            elif close_method == "press_escape":
                page.keyboard.press("Escape")
            elif close_method == "kebab_item_action":
                # Click an item inside the menu (e.g. "Search online").
                # The action handler dispatches selectTaxon() which
                # calls render(), replacing the entire tree DOM. The
                # kebab menu element is gone after the re-render — the
                # user must be able to click the NEW trigger and still
                # see a working kebab menu.
                search_item = page.locator(
                    f'[data-taxon-id="{fresh_id}"] [data-action="open-searches"]'
                ).first
                expect(search_item).to_be_visible(timeout=2_000)
                search_item.click()
                # selectTaxon has fired — the tree is rebuilt. The old
                # `menu` locator now points at a detached element. The
                # user observes the menu closed visually because the
                # new menu starts without `.open`.
                page.wait_for_function(
                    f"() => document.querySelector('[data-taxon-id=\"{fresh_id}\"] .kebab-menu.open') === null",
                    timeout=5_000,
                )
            else:
                raise AssertionError(f"unknown close_method {close_method!r}")

            expect(menu).not_to_have_class(open_cls, timeout=2_000)

            # Reopen by hovering + clicking the trigger. The hover
            # restores the trigger\'s opacity (it\'s hover-gated), so
            # the user can see and click it again.
            row.hover()
            trigger.click()
            expect(menu).to_have_class(open_cls, timeout=2_000)
        finally:
            browser.close()




@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_search_online_reopens_detail_panel_after_close(api_server):
    """Regression: clicking "Search online" on a row whose detail
    panel was previously closed must reopen the panel.

    Background: closeDetail() flips state.detailOpen = false but
    intentionally leaves state.selected set (the file explorer and
    URL hash stay rooted at that taxon). selectTaxon() had an
    `if (state.selected === id) return` early-exit that ignored
    detailOpen, so a subsequent "Search online" click on the same
    row was a silent no-op. Users reported the kebab item "no
    responde" after closing the panel.

    Test path:
      1. Open the kebab, click "Search online" -> panel opens.
      2. Close the panel via the X button.
      3. Open the kebab again, click "Search online" -> panel
         MUST reopen (this is what the user reported broken).
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

            row = page.locator(f'[data-taxon-id="{fresh_id}"]').first
            expect(row).to_be_visible(timeout=5_000)
            trigger = page.locator(
                f'[data-taxon-id="{fresh_id}"] button[data-action="toggle-kebab"]'
            ).first
            search_item = page.locator(
                f'[data-taxon-id="{fresh_id}"] [data-action="open-searches"]'
            ).first
            panel = page.locator("#detail-panel")
            close_btn = page.locator('[data-action="close-detail"]').first

            # Step 1: open the panel via Search online.
            row.hover()
            trigger.click()
            expect(search_item).to_be_visible(timeout=2_000)
            search_item.click()
            expect(panel).to_be_visible(timeout=5_000)

            # Step 2: close the panel via the X button. state.selected
            # stays set (by design — see closeDetail comment), so the
            # URL hash and file explorer context survive the close.
            expect(close_btn).to_be_visible(timeout=2_000)
            close_btn.click()
            expect(panel).not_to_be_visible(timeout=2_000)

            # Step 3: open the kebab again, click Search online. The
            # detail panel MUST reopen. Before the fix this was a
            # silent no-op because selectTaxon()'s early return saw
            # state.selected === id and returned without re-rendering.
            row.hover()
            trigger.click()
            expect(search_item).to_be_visible(timeout=2_000)
            search_item.click()
            expect(panel).to_be_visible(timeout=5_000)
        finally:
            browser.close()


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "db" / "taxa.db"


@pytest.mark.skipif(
        _check_playwright_available() is None,
        reason="playwright not installed (pip install playwright)",
    )
@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_folder_tab_renders_for_unmaterialized_taxon(api_server):
    """Regression: the Folder tab must render without throwing when
    the preview's all_exist is false (taxon NOT yet materialized).

    Background: renderFolderTab() in web/detail.js declared the
    `createBtn` local with `const createBtn = null` but later tried
    to reassign it (`createBtn = btn`) inside the
    `if (!preview.all_exist)` branch. V8 raises
    `TypeError: Assignment to constant variable` and the tab caught
    the error, surfacing the "Could not render the Folder tab:
    Assignment to constant variable." message instead of the
    preview list + "Create N folders" button. Users reported
    "no folders" / "Folder tab broken" in the freshwater tree.

    Test path:
      1. Switch to the Freshwater tree source.
      2. Open the kebab on the freshwater root row and click Search
         online (the freshwater root has no searches/vern/syn/dist data,
         so a plain row click leaves the detail panel hidden — we have
         to use the kebab → Search online flow to force the panel open,
         same as test_search_online_reopens_detail_panel_after_close).
      3. Click the Folder tab.
      4. The error message must NOT be visible.
      5. The "Create N folders" button MUST be visible (proves the
         all_exist=false branch ran without throwing).
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

            row = page.locator(f'[data-taxon-id="{fresh_id}"]').first
            expect(row).to_be_visible(timeout=5_000)
            trigger = page.locator(
                f'[data-taxon-id="{fresh_id}"] button[data-action="toggle-kebab"]'
            ).first
            search_item = page.locator(
                f'[data-taxon-id="{fresh_id}"] [data-action="open-searches"]'
            ).first

            # Force the panel open via kebab → Search online.
            row.hover()
            trigger.click()
            expect(search_item).to_be_visible(timeout=2_000)
            search_item.click()

            panel = page.locator("#detail-panel")
            expect(panel).to_be_visible(timeout=5_000)

            folder_tab = panel.locator('[data-tab="folder"]')
            expect(folder_tab).to_be_visible(timeout=2_000)
            folder_tab.click()

            folder_content = panel.locator('[data-tab-content="folder"]')
            # The error wrapper from the catch-block: it contains
            # the literal "Could not render the Folder tab" string.
            # Without the fix this locator matches and the test fails.
            error_msg = folder_content.locator(
                "text=Could not render the Folder tab"
            )
            expect(error_msg).to_have_count(0, timeout=2_000)

            # Positive assertion: the all_exist=false branch must
            # have run to completion, rendering the Create button.
            create_btn = folder_content.locator(
                "button.materialize-modal-btn-primary"
            )
            expect(create_btn).to_be_visible(timeout=2_000)
        finally:
            browser.close()


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
                # When user_version (2) < expected (5), boot() removes the
                # `hidden` class and writes the numbers into the spans.
                banner = page.locator("#version-banner")
                expect(banner).to_be_visible(timeout=5_000)
                expect(
                    page.locator("#version-banner-actual")
                ).to_have_text("2", timeout=2_000)
                expect(
                    page.locator("#version-banner-expected")
                ).to_have_text("5", timeout=2_000)
            finally:
                browser.close()
    finally:
        # Restore the original PRAGMA user_version so subsequent test runs
        # (and the next time someone invokes `make api`) see the real value.
        rw = sqlite3.connect(DB_PATH)
        rw.execute(f"PRAGMA user_version = {original_version}")
        rw.commit()
        rw.close()
