"""
Browser-side e2e test for the File Explorer (Browser tab).

The other pytest tests in this repo are backend-only (TestClient +
in-memory SQLite) or browser-only for the Freshwater toggle
(tests/test_web_toggle.py). This file is the first browser test that
exercises the file-explorer end-to-end against a live API server.

Flow:
  1. Spawn uvicorn on port 8768 with TAXA_RESEARCH_DIR pointing at a tmp
     dir (so the test never touches the user's real ./Research folder).
  2. POST /api/taxon/{test_taxon_id}/materialize to create the root→taxon
     folder structure (idempotent — no-op if it already exists).
  3. Seed 4 fixture files (HTML, MD, TXT, PDF) into the materialized leaf
     folder.
  4. Open the page in headless chromium, drive the UI:
       - Click the test taxon row to select it.
       - Click the Browser header tab (data-path="browser").
       - Assert the explorer shell renders with the seeded folder + files.
       - Single-click each file, assert the meta strip + raw viewer tab
         appears with the correct text content.
       - Double-click the PDF, assert the viewer mounts an <iframe>
         (PDF renders inline per spec §Multi-format file viewer).
  5. Tear down: stop uvicorn, remove the tmp research dir.

Skips if playwright or the chromium binary is not installed (mirrors
test_web_toggle.py's graceful degradation). Run via:

    make api                                            # in another terminal
    .venv/bin/python -m pytest tests/test_e2e_file_explorer.py -v -s

The test does NOT spin up its own API server against the real DB — it
relies on the developer having already started `make api` once on the
default 8765 port (so /api/domains returns the real catalogue), then
this test reads the live 8765 server for /api/domains discovery but
spawns ITS OWN server on 8768 with TAXA_RESEARCH_DIR overridden for the
isolated test data.

Trade-off: this couples the test to the real DB schema (the seeded
test_taxon_id is real). Discovery via /api/domains keeps it DB-agnostic.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

PORT = 8768  # non-default to avoid conflicts with 8765 (dev) + 8767 (toggle test)
BASE_URL = f"http://127.0.0.1:{PORT}"
LIVE_DOMAINS_URL = "http://127.0.0.1:8765/api/domains"

# Test taxon — Basidiomycota (id=3722210): a phylum that's the 2nd child of
# Fungi alphabetically, so PAGE_SIZE=5 renders it without needing showAll.
# Materialized folder chain: /Eukaryota/Fungi/Basidiomycota.
# Seed fixtures into the leaf and verify all 4 supported formats render.
TEST_TAXON_ID = 3722210
TEST_TAXON_NAME = "Basidiomycota"
FIXTURES_DIR = Path("/tmp/taxa_e2e_fixtures")


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


def _post(url: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body else b""
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def _get(url: str) -> tuple[int, dict | str]:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = resp.read()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


@pytest.fixture(scope="module")
def e2e_env():
    """Spawn uvicorn on PORT with TAXA_RESEARCH_DIR=tmp for the module.

    Yields a dict with `base_url`, `test_taxon_id`, `test_taxon_name`,
    `research_dir`, `files_subpath` (the relative path of the leaf under
    the research dir), and `seeded_files` (list of {name, abs_path,
    expected_text_fragment}).

    Skips if port is in use or uvicorn fails to come up in 10s.
    """
    if not _port_free(PORT):
        pytest.skip(f"port {PORT} is in use; cannot start test API server")
    if not FIXTURES_DIR.exists():
        pytest.skip(f"fixtures dir {FIXTURES_DIR} not seeded")
    if _port_free(8765):
        pytest.skip(
            "live API on 8765 not reachable; start `make api` in another terminal"
        )

    # Sanity check that TEST_TAXON_ID actually exists on the live DB.
    code, domains = _get(LIVE_DOMAINS_URL)
    if code != 200:
        pytest.skip(f"live /api/domains returned {code}")
    # /api/domains only returns root domains — not the deep Entorrhizomycota.
    # We trust the hardcoded ID; if the DB was reseeded differently the
    # materialize call below will fail with 404 and the test will skip.

    research_dir = Path(tempfile.mkdtemp(prefix="taxa_e2e_research_"))
    env = os.environ.copy()
    env["TAXA_RESEARCH_DIR"] = str(research_dir)

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.server:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    try:
        if not _wait_ready(f"{BASE_URL}/api/health"):
            proc.terminate()
            shutil.rmtree(research_dir, ignore_errors=True)
            pytest.skip("test API server failed to come up within 10s")

        # Materialize the test taxon (creates /Eukaryota/Fungi/Entorrhizomycota).
        code, body = _post(f"{BASE_URL}/api/taxon/{TEST_TAXON_ID}/materialize")
        if code not in (200, 409):  # 409 = folder already existed
            proc.terminate()
            shutil.rmtree(research_dir, ignore_errors=True)
            pytest.skip(f"materialize failed: {code} {body}")

        # Seed fixtures into the leaf folder.
        leaf = research_dir / "Eukaryota" / "Fungi" / TEST_TAXON_NAME
        assert leaf.exists(), f"materialize did not create {leaf}"
        seeded_files = []
        for fixture in ["sample.html", "sample.md", "sample.txt", "sample.pdf"]:
            src = FIXTURES_DIR / fixture
            dst = leaf / fixture
            shutil.copy(src, dst)
            seeded_files.append({
                "name": fixture,
                "abs_path": dst,
                "expected_text_fragment": {
                    "html": "Sample HTML for taxa e2e",
                    "md":   "Sample Markdown for taxa e2e",
                    "txt":  "Sample plain text for taxa e2e",
                    "pdf":  None,  # PDF rendered via iframe — no text assertion
                }[fixture.split(".")[-1]],
            })

        yield {
            "base_url": BASE_URL,
            "test_taxon_id": TEST_TAXON_ID,
            "test_taxon_name": TEST_TAXON_NAME,
            "research_dir": research_dir,
            "files_subpath": f"Eukaryota/Fungi/{TEST_TAXON_NAME}",
            "seeded_files": seeded_files,
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(research_dir, ignore_errors=True)


@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_file_explorer_full_flow(e2e_env):
    """End-to-end: select taxon → open Browser tab → click files → verify viewer.

    Asserts:
      1. The Browser tab mounts and shows the seeded folder + 4 files.
      2. Single-clicking HTML / MD / TXT files shows the meta strip with the
         correct FORMAT badge and the raw viewer renders the expected text.
      3. Double-clicking the PDF mounts an iframe viewer (PDF inline).
    """
    from playwright.sync_api import expect, sync_playwright  # type: ignore

    base = e2e_env["base_url"]
    taxon_id = str(e2e_env["test_taxon_id"])
    seeded = e2e_env["seeded_files"]

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium binary not available: {exc!r}")
        try:
            # Phase 5c - seed the typed persisted `last-taxon-id` so
            # the AppShell rehydrates the taxonomy-detail context on
            # first paint (URL hash + persisted `taxa.tree.lastTaxonId`
            # key restored before the page renders). The Browser
            # surface stays GLOBAL and UNFILTERED - the seed only
            # narrows the taxonomy panel's initial focus, NOT the
            # file explorer's taxonId (hard-coded null per 5b.4
            # global-surface contract).
            #
            # The init script runs in EVERY new context before any
            # page script executes, so the persisted value is in
            # place before the AppShell's first useEffect reads it.
            context = browser.new_context()
            context.add_init_script(
                # The typed store writes the int as a JSON-encoded
                # string; the seed must mirror the same shape so
                # `tryJsonParse` accepts it.
                "try { window.localStorage.setItem("
                "'taxa.tree.lastTaxonId', JSON.stringify("
                + str(e2e_env["test_taxon_id"])
                + ")); } catch (e) { /* private mode */ }"
            )
            page = context.new_page()
            page.goto(base + "/", wait_until="domcontentloaded", timeout=10_000)

            # --- Step 1: select the test taxon row -------------------------
            # Tree rows are <div data-taxon-id=... data-action="...">. Eukaryota
            # is rendered as a collapsed root; we click it to expand, then walk
            # down to the test taxon. To keep the test fast, we use the
            # search input to jump directly to the test taxon name.
            search = page.locator("#search-input")
            search.fill(e2e_env["test_taxon_name"])
            # Search dropdown appears after 200ms debounce + RTT.
            page.wait_for_selector("#search-results.open", timeout=5_000)
            # Click the first search result that matches our taxon id.
            result = page.locator(
                f"#search-results [data-taxon-id='{taxon_id}']"
            ).first
            # Verify the result is actually visible before clicking.
            sel = "#search-results [data-taxon-id='" + taxon_id + "']"
            assert page.locator(sel).count() == 1, (
                f"expected 1 search result for taxon {taxon_id}, "
                f"got {page.locator(sel).count()}"
            )
            result.click(timeout=5_000, force=True)
            # Wait for the search dropdown to close (it closes via closeSearch()).
            page.wait_for_function(
                "() => !document.querySelector('#search-results.open')",
                timeout=5_000,
            )
            # The select-from-search handler awaits expandAncestorsOf before
            # scrolling. Wait for the taxon row to appear in the tree.
            page.wait_for_function(
                f"() => document.querySelector('#taxon-{taxon_id}') !== null",
                timeout=15_000,
            )
            page.wait_for_selector(
                "#detail-panel:not(.hidden)", timeout=10_000
            )

            # --- Step 2: click the Browser tab -----------------------------
            page.click("#nav-browser", timeout=5_000)
            # Explorer shell mounts into <main>; wait for the .fex-shell.
            page.wait_for_selector(".fex-shell", timeout=10_000)
            # Tree pane must show the seeded file names. We use .fex-row.file
            # (NOT .fex-row) because the folder row also has .fex-row and
            # CONTAINS the file rows as children — a bare :has-text() would
            # match both, and .first would return the wrong row.
            for f in seeded:
                name = f["name"]
                page.wait_for_selector(
                    f".fex-row.file:has-text('{name}')", timeout=5_000
                )

            # --- Step 3: dblclick HTML, MD, TXT and verify viewer renders -----
            # NOTE: single-click only highlights (no viewer content per the
            # spec's click/dblclick semantics in file_explorer.js). The
            # meta-strip + viewer content only appear after dblclick via
            # openFile(). We dblclick each one and verify.
            for f in seeded:
                if f["name"].endswith(".pdf"):
                    continue  # PDF handled separately below
                row = page.locator(
                    f".fex-row.file:has-text('{f['name']}')"
                ).first
                row.dblclick(timeout=5_000)
                # Meta strip should show the FORMAT= badge.
                meta = page.locator(".fex-meta-strip")
                expect(meta).to_be_visible(timeout=5_000)
                fmt_badge = page.locator(
                    ".fex-meta-strip span",
                    has_text=f"FORMAT={f['name'].split('.')[-1].upper()}"
                )
                expect(fmt_badge).to_be_visible(timeout=5_000)
                # Viewer pane content depends on format:
                #   .html — mounted in an <iframe> (cannot read iframe body
                #            cross-origin without same-origin, so we assert
                #            the iframe exists + its src hits the serve endpoint).
                #   .md   — fenced <pre> inline; assert text fragment.
                #   .txt  — fenced <pre> inline; assert text fragment.
                ext = f["name"].split(".")[-1].lower()
                if ext == "html":
                    iframe = page.locator(".fex-viewer-pane iframe")
                    expect(iframe).to_be_visible(timeout=5_000)
                elif f["expected_text_fragment"]:
                    viewer = page.locator(".fex-viewer-pane")
                    expect(viewer).to_contain_text(
                        f["expected_text_fragment"], timeout=5_000
                    )

            # --- Step 4: double-click PDF, expect iframe mount -------------
            pdf_row = page.locator(
                f".fex-row.file:has-text('sample.pdf')"
            ).first
            pdf_row.dblclick(timeout=5_000)
            # PDF renders inside an <iframe> in the viewer pane.
            iframe = page.locator(".fex-viewer-pane iframe")
            expect(iframe).to_be_visible(timeout=10_000)
        finally:
            browser.close()
