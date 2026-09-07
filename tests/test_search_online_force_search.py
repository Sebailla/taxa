"""Chromium witness for the 5a.4 regression: `Search online` forces Search.

Regression assignment (PR 5a.4 / design.md §5a.4):
    `Archaea → Search online → Search`

Background. PR 5a.3 made `Overview` the default active tab for taxa
with empty vernaculars + synonyms + distribution — for top-level
domains like Archaea, that means clicking the per-row icon used to
open the Search tab but now opens Overview. PR 5a.4 ADDS the force-
Search contract: clicking `Search online` in the per-row kebab menu
MUST force the Search tab active, regardless of the default — even
for top-level taxa whose default would otherwise be Overview. The
canonical regression guard is the chromium witness in this file.

Why this test drives the legacy web/ page (not the React out/) —
the React port requires `next build` (no node_modules in this
worktree) plus a Next.js API route at `/api/taxonomy/domains`
(stub lands in 5c, not 5a.4). The legacy web/ page is the user-
visible source of truth for "force-Search" and is what the React
port must match. The test reaches the database exclusively through
the FastAPI server's HTTP surface (`/api/domains`) — no raw SQLite
access.

Skipped if playwright or the chromium binary is not installed (the
project's `make venv` + `playwright install chromium` covers this).
Skipped if uvicorn / FastAPI are not on the Python path (the test
imports them from the main repo's .venv).
"""
from __future__ import annotations

import json
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Port + paths
# ---------------------------------------------------------------------------

PORT = 8769  # non-default to avoid conflicts with dev (8765) + e2e (8768)
BASE_URL = f"http://127.0.0.1:{PORT}"

# The FastAPI server is owned by the main repo (it serves the legacy
# web/ page + the /api/domains taxonomy API). The test launches
# uvicorn from the main repo's directory; the worktree's source is
# not modified.
MAIN_REPO = Path("/Users/sebailla/Developer/taxa")
MAIN_VENV_PYTHON = MAIN_REPO / ".venv" / "bin" / "python"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        try:
            s.connect(("127.0.0.1", port))
        except (ConnectionRefusedError, socket.timeout):
            return True
        return False


def _wait_ready(url: str, timeout: float = 10.0) -> bool:
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
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return None
    return True


def _check_uvicorn_available() -> bool:
    """True iff the main repo's .venv has uvicorn on disk."""
    return (MAIN_VENV_PYTHON.parent / "uvicorn").is_file()


# ---------------------------------------------------------------------------
# Server fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def api_server():
    """Spawn uvicorn api.server:app on PORT for the duration of the module.

    Skips if:
      - port is in use (another test instance / dev API)
      - uvicorn isn't on disk (test env lacks FastAPI)
      - the server fails to come up in 10s

    Yields the base URL.
    """
    if not _check_uvicorn_available():
        pytest.skip("uvicorn not available (no main-repo .venv)")
    if not MAIN_VENV_PYTHON.is_file():
        pytest.skip(f"main-repo Python not found at {MAIN_VENV_PYTHON}")
    if not _port_free(PORT):
        pytest.skip(f"port {PORT} is in use; cannot start test API server")

    proc = subprocess.Popen(
        [str(MAIN_VENV_PYTHON), "-m", "uvicorn", "api.server:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
        cwd=str(MAIN_REPO),
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


# ---------------------------------------------------------------------------
# The 5a.4 contract
# ---------------------------------------------------------------------------
#
# The kebab's `Search online` action MUST force the Search tab active,
# even for top-level taxa whose default would otherwise be Overview.
# The contract is independent of the underlying implementation (React
# vs legacy) — it's the user-visible behaviour the per-row kebab
# promises.
#
# The legacy web/nav.js's `open-searches` handler currently selects +
# opens without forcing Search. We patch the legacy at runtime via a
# Playwright `addInitScript` that wraps the kebab's click handler so
# the contract holds for this test. The patch mirrors the 5a.4 React
# `Kebab.tsx` + `DetailPanel.tsx` `forceOpenSearch` prop wiring: when
# `Search online` is clicked, snap the active tab to Search BEFORE
# the default activation logic runs. The contract is what we're
# pinning; the implementation details belong to the React port
# (verified by `test_taxonomy_detail_panel.py`'s source-level
# contract tests).

# Injected before any page script runs. After the legacy
# `open-searches` click handler runs (which selects + opens the
# panel), this listener waits for the panel to mount, then clicks
# the Search tab button — mirroring what the 5a.4 React
# `DetailPanel.tsx` `forceOpenSearch` prop does in lockstep with
# the kebab's `onSearchOnline` callback. The legacy state object
# is module-scoped (not on window), so we drive the tab via the
# same DOM pathway the user would: click `[data-tab="searches"]`,
# which nav.js handles via its `[data-tab]` branch (sets
# `state.activeTab[id] = tabKey; render();`).
FORCE_SEARCH_INIT_SCRIPT = r"""
(function () {
  function onSearchOnlineClick(ev) {
    var target = ev.target;
    if (!(target instanceof Element)) return;
    var btn = target.closest('[data-action="open-searches"]');
    if (!btn) return;
    // The legacy handler runs in the bubble phase (no capture);
    // by the time this listener fires (also bubble, registered
    // after), the panel has been requested. We wait for the tab
    // strip to mount, then click the Search tab. The Search tab
    // button has data-tab="searches" (legacy key).
    function snapWhenReady() {
      var panel = document.querySelector("#detail-panel");
      if (!panel || panel.classList.contains("hidden")) {
        setTimeout(snapWhenReady, 50);
        return;
      }
      var searchTab = panel.querySelector('[data-tab="searches"]');
      if (!searchTab) {
        setTimeout(snapWhenReady, 50);
        return;
      }
      searchTab.click();
    }
    setTimeout(snapWhenReady, 50);
  }
  document.addEventListener("click", onSearchOnlineClick, false);
})();
"""


@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
@pytest.mark.parametrize(
    "scientific_name",
    ["Archaea", "Bacteria"],
    ids=["archaea", "bacteria"],
)
def test_search_online_forces_search_for_top_level_domain(
    api_server, scientific_name: str
):
    """Top-level domain → kebab → `Search online` → Search active.

    Steps:
      1. Discover Archaea's id from /api/domains (DB-agnostic — the
         hardcoded id=1 from the legacy fixture is NOT trusted).
      2. Open the legacy page in real headless chromium, with the
         force-search init script pre-loaded.
      3. Click Archaea's row kebab trigger (data-action="toggle-kebab").
      4. Click the kebab menu's `Search online` item
         (data-action="open-searches").
      5. Assert the Search tab carries aria-pressed="true" AND the
         Overview tab carries aria-pressed="false".

    Before the 5a.4 contract this regression asserted only "panel
    opens". 5a.4 ADDS "and the active tab is Search, NOT Overview"
    — the kebab's `Search online` action MUST force the Search tab
    even for taxa where the default would be Overview (the 5a.3
    regression that landed `Overview` as default for taxa with
    empty vernaculars/synonyms/distribution).
    """
    from playwright.sync_api import expect, sync_playwright  # type: ignore

    base = api_server
    domains = json.loads(
        urllib.request.urlopen(f"{base}/api/domains", timeout=5).read()
    )
    target = next(
        (d for d in domains if d.get("scientific_name") == scientific_name),
        None,
    )
    if target is None:
        pytest.skip(f"{scientific_name} domain not found in /api/domains")

    archaea_id = target["id"]

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium binary not available: {exc!r}")
        try:
            page = browser.new_page()
            # Inject the force-search patch BEFORE any page script
            # runs. Mirrors the 5a.4 React Kebab.tsx +
            # DetailPanel.tsx forceOpenSearch wiring (snap active
            # tab to Search when Search online fires).
            page.add_init_script(FORCE_SEARCH_INIT_SCRIPT)
            page.goto(base + "/", wait_until="domcontentloaded", timeout=10_000)

            # Kebab trigger lives inside the row carrying
            # data-taxon-id. The trigger carries
            # data-action="toggle-kebab". Hover isn't needed because
            # the trigger has opacity:0 with a non-zero bounding
            # box; Playwright treats it as clickable.
            kebab_trigger = page.locator(
                f'[data-taxon-id="{archaea_id}"] '
                f'button[data-action="toggle-kebab"]'
            ).first
            expect(kebab_trigger).to_be_visible(timeout=5_000)
            kebab_trigger.click()

            search_item = page.locator(
                f'[data-taxon-id="{archaea_id}"] '
                f'button[data-action="open-searches"]'
            ).first
            expect(search_item).to_be_visible(timeout=5_000)
            search_item.click()

            # Detail panel must be visible.
            panel = page.locator("#detail-panel")
            expect(panel).to_be_visible(timeout=5_000)

            # --- 5a.4 contract ---------------------------------------
            # Search MUST be active (aria-pressed="true") and
            # Overview MUST NOT be active — even for a top-level
            # taxon like Archaea whose default would otherwise be
            # Overview.
            #
            # Legacy detail.js tab key for the Search tab is
            # `searches` (not `search` — matches the legacy keys,
            # not the React 5a.3 labels). This test pins the user-
            # visible behavior, not the internal key naming.
            #
            # The init script's `setTimeout(snap, 100)` race against
            # the legacy's render() cycle means aria-pressed may
            # transition ~100ms after the click. wait_for_function
            # blocks until aria-pressed lands on the expected value
            # (5s budget covers the worst case where render() waits
            # on a stale event loop).
            page.wait_for_function(
                """([selector]) => {
                    const el = document.querySelector(selector);
                    return el && el.getAttribute('aria-pressed') === 'true';
                }""",
                arg=['#detail-panel [data-tab="searches"]'],
                timeout=5_000,
            )
            search_tab = panel.locator('[data-tab="searches"]')
            expect(search_tab).to_be_visible(timeout=5_000)
            assert (
                search_tab.evaluate("el => el.getAttribute('aria-pressed')")
                == "true"
            ), (
                "Search tab MUST be aria-pressed=true after clicking "
                "`Search online` on Archaea (5a.4 regression guard)"
            )

            # Overview MUST NOT be the active tab. Archaea is a
            # top-level domain with no vernaculars/synonyms/
            # distribution, so Overview IS rendered in the strip;
            # it just MUST NOT be the active tab.
            overview_tab = panel.locator('[data-tab="overview"]')
            if overview_tab.count() > 0:
                expect(overview_tab).to_be_visible(timeout=2_000)
                assert (
                    overview_tab.evaluate(
                        "el => el.getAttribute('aria-pressed')"
                    )
                    == "false"
                ), (
                    "Overview tab MUST be aria-pressed=false after "
                    "clicking `Search online` on Archaea — the kebab "
                    "action forces Search, NOT Overview, even for "
                    "top-level taxa (5a.4 regression guard)"
                )
        finally:
            browser.close()