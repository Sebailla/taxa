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
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from playwright.sync_api import expect, sync_playwright  # type: ignore[import-not-found]

BASE_URL = "http://127.0.0.1:8765"
OUT_DIR = Path(__file__).resolve().parent.parent / "screenshots"
OUT_DIR.mkdir(exist_ok=True)

# Names of every screenshot the README claims this script produces. Used at
# the end of main() to fail loudly if any capture was skipped (e.g. when
# the hardcoded Biota id 5413596 is missing from a fresh DB build) instead
# of silently delivering 3 of 4.
EXPECTED = [
    "01-col-view-default",
    "02-worms-view",
    "03-worms-biota-expanded",
    "04-col-view-diaphorina-detail",
]


def shot(page, name: str, captured: list[str], full: bool = True) -> Path:
    """Save a PNG and record it as captured so the final check can verify."""
    out = OUT_DIR / f"{name}.png"
    page.screenshot(path=str(out), full_page=full)
    captured.append(name)
    print(f"  → {out}  ({out.stat().st_size // 1024} KB)")
    return out


def resolve_ids() -> tuple[int | None, int | None]:
    """Look up the Biota superdomain and Diaphorina citri species ids via
    the API rather than hardcoding them. Returns (biota_id, diaphorina_id);
    either may be None if the lookup fails (the caller falls back to a
    loud [error] message).

    This makes the script robust to DB rebuilds that re-assign ids.
    """
    biota_id: int | None = None
    diaphorina_id: int | None = None
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/domains", timeout=10) as r:
            for d in json.loads(r.read()):
                if d["scientific_name"] == "Biota" and d.get("worms_id") == 1:
                    biota_id = d["id"]
                    break
    except Exception as e:
        print(f"  [warn] could not resolve Biota id via /api/domains: {e}")
    try:
        with urllib.request.urlopen(
            f"{BASE_URL}/api/search?q={urllib.parse.quote('Diaphorina citri')}",
            timeout=10,
        ) as r:
            hits = json.loads(r.read())
            # Prefer the accepted-name hit (status='accepted') over synonyms.
            # The search endpoint ranks synonyms first when the query matches
            # the scientific name verbatim, so we can't just take hits[0].
            accepted_id: int | None = None
            for h in hits:
                taxon = h.get("taxon") or {}
                if (
                    taxon.get("scientific_name") == "Diaphorina citri"
                    and taxon.get("rank") == "species"
                    and taxon.get("status") == "accepted"
                ):
                    accepted_id = taxon["id"]
                    break
            if accepted_id is None:
                # Fallback: first species hit with the right name, even if
                # it's a synonym. The detail panel will still render the
                # selected taxon correctly.
                for h in hits:
                    taxon = h.get("taxon") or {}
                    if (
                        taxon.get("scientific_name") == "Diaphorina citri"
                        and taxon.get("rank") == "species"
                    ):
                        accepted_id = taxon["id"]
                        break
            diaphorina_id = accepted_id
    except Exception as e:
        print(f"  [warn] could not resolve Diaphorina citri id via /api/search: {e}")
    return biota_id, diaphorina_id


def main() -> int:
    captured: list[str] = []
    biota_id, diaphorina_id = resolve_ids()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        page.on("console", lambda msg: print(f"  [console.{msg.type}] {msg.text[:200]}"))
        page.on("pageerror", lambda err: print(f"  [pageerror] {err}"))

        print("[1/4] Cold load (CoL view, default)")
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_selector("#tree-view [data-taxon-id]")
        shot(page, "01-col-view-default", captured)

        print("[2/4] Toggle to WoRMS view")
        # Wait for the toggle's aria-pressed to flip to 'true' as the
        # source of truth that the view switch completed (replaces a
        # 800ms magic wait that was the most likely source of CI flake).
        worms_toggle = page.locator('#tree-source-toggle [data-tree-source="worms"]')
        worms_toggle.click()
        expect(worms_toggle).to_have_attribute("aria-pressed", "true", timeout=5000)
        shot(page, "02-worms-view", captured)

        print("[3/4] Expand Biota → Animalia in WoRMS view")
        # Find the Biota root and click its chevron to expand.
        # The id is resolved via the API in resolve_ids() above (Biota
        # superdomain, worms_id=1). If the lookup failed, biota_id is
        # None and we skip with a loud [error] message.
        if biota_id is None:
            print(
                "  [error] could not resolve Biota id via /api/domains — "
                "skipping screenshot 03. Check the API is reachable."
            )
        else:
            biota = page.locator(f'[data-taxon-id="{biota_id}"]').first
            if biota.count():
                # Count BEFORE the click so the +N threshold measures the
                # children that the click actually adds. Threshold-based so
                # it works regardless of which other roots happen to be
                # expanded at this point.
                before_count = page.locator("#tree-view [data-taxon-id]").count()
                biota.click()
                # Wait for the tree to grow by at least 8 rows (Biota's
                # WoRMS kingdoms: Animalia, Archaea, Bacteria, Chromista,
                # Fungi, Plantae, Protozoa, Viruses).
                expect(page.locator("#tree-view [data-taxon-id]")).to_have_count(
                    before_count + 8, timeout=5000
                )
                shot(page, "03-worms-biota-expanded", captured)
            else:
                print(
                    f"  [error] data-taxon-id='{biota_id}' (Biota superdomain) not in "
                    "DOM after toggle — skipping screenshot 03."
                )

        print("[4/4] Toggle back to CoL + navigate to a CoL-only taxon via hash")
        # Reload with hash to trigger boot's hash-based navigation path, which
        # calls selectTaxon() → loadDetail() → renders the detail panel with
        # the new "CoL" header badge for CoL-only taxa.
        # The id is resolved via the API (Diaphorina citri, rank=species).
        # If the lookup failed, diaphorina_id is None and we skip with a
        # loud [error] message.
        if diaphorina_id is None:
            print(
                "  [error] could not resolve Diaphorina citri id via /api/search — "
                "skipping screenshot 04. Check the API is reachable."
            )
        else:
            # Cache-buster query param forces a full reload — same-origin hash
            # navigation alone doesn't fire a new boot() pass.
            try:
                page.goto(
                    f"{BASE_URL}/?nc={int(time.time())}#{diaphorina_id}",
                    wait_until="networkidle",
                    timeout=15000,
                )
            except Exception as e:
                print(f"  [warn] navigation to detail taxon failed: {e}")
                shot(page, "04-col-view-diaphorina-detail", captured)
                browser.close()
            else:
                # Wait for boot() to expand the 9-level ancestor chain AND
                # loadDetail() to populate the panel. The .detail-card class
                # is only added once renderDetailPanel() has actual content
                # (not the loading stub), so it's a true end-of-render signal
                # — no magic 5s wait needed.
                page.wait_for_selector(
                    "#detail-panel .detail-card", timeout=15000
                )
                # Diagnostic: dump panel state + selected/detail values.
                panel_class = page.locator("#detail-panel").get_attribute("class")
                panel_html_len = page.evaluate(
                    "document.getElementById('detail-panel').innerHTML.length"
                )
                # Probe app state via a known DOM element that depends on focused/selected.
                breadcrumb_text = page.locator("#breadcrumb").inner_text()
                url_hash = page.evaluate("location.hash")
                print(f"  detail-panel class='{panel_class}', innerHTML length={panel_html_len}")
                print(f"  breadcrumb='{breadcrumb_text.strip()[:80]}'  hash='{url_hash}'")
                shot(page, "04-col-view-diaphorina-detail", captured)
                browser.close()

    # Final check: every screenshot the README documents must have been captured.
    # Fail with non-zero exit if any are missing so CI / reviewers see the gap
    # instead of receiving a half-empty screenshots/ directory.
    missing = [n for n in EXPECTED if n not in captured]
    if missing:
        print(f"\n[FAIL] {len(missing)} expected screenshot(s) missing:")
        for name in missing:
            print(f"  - screenshots/{name}.png")
        return 1
    print(f"\n[OK] all {len(EXPECTED)} screenshots captured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
