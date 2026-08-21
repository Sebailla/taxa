"""
Headless screenshot helper for the taxa web UI.

Usage:
    .venv/bin/python scripts/screenshot.py

What it captures:
    - CoL view (default landing) at /
    - WoRMS view after toggling #tree-source-toggle to "worms"
    - Detail panel open with a known taxon

Requires:
    - playwright (pip install playwright)
    - chromium browser binary (playwright install chromium)
    - The FastAPI server running at http://127.0.0.1:8765
"""
from __future__ import annotations
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

BASE_URL = "http://127.0.0.1:8765"
OUT_DIR = Path(__file__).resolve().parent.parent / "screenshots"
OUT_DIR.mkdir(exist_ok=True)


def shot(page, name: str, full: bool = True) -> Path:
    """Save a PNG and print the path so the agent can attach it."""
    out = OUT_DIR / f"{name}.png"
    page.screenshot(path=str(out), full_page=full)
    print(f"  → {out}  ({out.stat().st_size // 1024} KB)")
    return out


def main() -> int:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        page.on("console", lambda msg: print(f"  [console.{msg.type}] {msg.text[:200]}"))
        page.on("pageerror", lambda err: print(f"  [pageerror] {err}"))

        print("[1/4] Cold load (CoL view, default)")
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_selector("#tree-view [data-taxon-id]")
        shot(page, "01-col-view-default")

        print("[2/4] Toggle to WoRMS view")
        page.click('#tree-source-toggle [data-tree-source="worms"]')
        page.wait_for_timeout(800)  # let the tree re-render
        shot(page, "02-worms-view")

        print("[3/4] Expand Biota → Animalia in WoRMS view")
        # Find the Biota root and click its chevron to expand
        biota = page.locator('[data-taxon-id="5413596"]').first
        if biota.count():
            biota.click()
            page.wait_for_timeout(1200)
            shot(page, "03-worms-biota-expanded")

        print("[4/4] Toggle back to CoL + navigate to a CoL-only taxon via hash")
        # Reload with hash to trigger boot's hash-based navigation path, which
        # calls selectTaxon() → loadDetail() → renders the detail panel with
        # the new "CoL" header badge for CoL-only taxa.
        # id=1578074 is Diaphorina citri (CoL-only species with 176 vernaculars
        # + 107 distribution rows) — exercises the full detail panel render.
        # Cache-buster query param forces a full reload — same-origin hash
        # navigation alone doesn't fire a new boot() pass.
        try:
            page.goto(
                f"{BASE_URL}/?nc={int(time.time())}#1578074",
                wait_until="networkidle",
                timeout=15000,
            )
        except Exception as e:
            print(f"  [warn] navigation to detail taxon failed: {e}")
            shot(page, "04-col-view-diaphorina-detail")
            browser.close()
            return 1
        # Give boot() time to expand ancestors + load detail (5-deep path).
        page.wait_for_timeout(5000)
        # Diagnostic: dump panel state + selected/detail values.
        panel_class = page.locator("#detail-panel").get_attribute("class")
        panel_html_len = page.evaluate("document.getElementById('detail-panel').innerHTML.length")
        # Probe app state via a known DOM element that depends on focused/selected.
        breadcrumb_text = page.locator("#breadcrumb").inner_text()
        url_hash = page.evaluate("location.hash")
        print(f"  detail-panel class='{panel_class}', innerHTML length={panel_html_len}")
        print(f"  breadcrumb='{breadcrumb_text.strip()[:80]}'  hash='{url_hash}'")
        shot(page, "04-col-view-diaphorina-detail")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
