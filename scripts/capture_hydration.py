#!/usr/bin/env python
"""Raw Playwright legacy collector (G5 chain child).

Exactly TEN browser samples against a caller-provided controlled target
URL; per-sample navigation/paint/DOM-marker/console + Chromium/
Playwright/environment provenance; in-memory + raw JSON written
atomically; fail-closed on iteration failure. Out of scope (later
chain children): Lighthouse, G5 launcher invocation, parity-reports
emission, baseline/candidate comparison. Exit codes: 0/2/10.
"""
from __future__ import annotations

import argparse, datetime as _dt, json, os, platform, sys
from pathlib import Path
from typing import Any, Protocol


SCHEMA = "taxa.g5-capture.legacy/1"
PROVENANCE_SCHEMA = "taxa.g5-capture.legacy-provenance/1"
ITERATIONS = 10
DEFAULT_DOM_MARKER_SELECTOR = "#tree-view [data-taxon-id]"
EXIT_OK, EXIT_USAGE, EXIT_FAILURE = 0, 2, 10


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class BrowserAdapter(Protocol):
    """Pluggable browser seam. Real adapter wraps Playwright sync API;
    tests inject a deterministic subclass (no Chromium required)."""
    def chromium_provenance(self) -> dict: ...
    def playwright_provenance(self) -> dict: ...
    def run_iteration(self, *, target_url: str, dom_marker_selector: str,
                      iteration_index: int) -> dict: ...


def collect_raw_samples(
    *, target_url: str, browser_adapter: BrowserAdapter,
    iterations: int = ITERATIONS,
    dom_marker_selector: str = DEFAULT_DOM_MARKER_SELECTOR,
) -> dict:
    """Run exactly `iterations` raw samples. Fail-closed: any iteration
    exception propagates verbatim and NO partial result is returned."""
    if iterations != ITERATIONS:
        raise ValueError(f"iterations must be {ITERATIONS} (G5 contract); got {iterations!r}")
    if not target_url:
        raise ValueError("target_url must be a non-empty string")
    if not dom_marker_selector:
        raise ValueError("dom_marker_selector must be a non-empty string")
    samples: list[dict] = []
    for i in range(iterations):
        s = browser_adapter.run_iteration(
            target_url=target_url, dom_marker_selector=dom_marker_selector,
            iteration_index=i)
        s["iteration"] = i
        s.setdefault("captured_at", _now_iso())
        samples.append(s)
    # Provenance layout is pinned — the next chain child (G5 joiner)
    # pins its diff logic against this exact structure.
    provenance = {
        "schema": PROVENANCE_SCHEMA,
        "chromium": browser_adapter.chromium_provenance(),
        "playwright": browser_adapter.playwright_provenance(),
        "environment": {"python_version": platform.python_version(),
                        "platform": platform.platform(),
                        "captured_at_iso": _now_iso()},
        "target_url": target_url, "iterations": iterations,
    }
    return {
        "schema": SCHEMA, "captured_at": _now_iso(),
        "target_url": target_url, "iterations": iterations,
        "dom_marker_selector": dom_marker_selector,
        "provenance": provenance, "samples": samples,
    }


def write_result(result: dict, out_path: Path) -> None:
    """Atomic sibling-tmp write so a mid-write failure cannot corrupt
    an existing --out file."""
    tmp = out_path.with_name(f"{out_path.name}.tmp-{os.getpid()}-{id(out_path)}")
    tmp.write_text(json.dumps(result, indent=2), encoding="utf-8")
    tmp.replace(out_path)


class PlaywrightBrowserAdapter:
    """Real Chromium adapter. Lazy-imports playwright so the module is
    importable without it installed (CI uses a test fake)."""

    def __init__(self, *, headless: bool = True) -> None:
        self._headless: bool = headless
        self._pw: Any = None  # lazy: populated by _pw_obj() on first use
        self._cv: str | None = None
        self._ce: str | None = None

    def _pw_obj(self):
        if self._pw is None:
            try:
                from playwright.sync_api import sync_playwright  # type: ignore
            except ImportError as e:
                raise RuntimeError(
                    f"playwright not installed: {e}. Install with "
                    "`pip install playwright && playwright install chromium`."
                ) from e
            self._pw = sync_playwright()
        return self._pw

    def chromium_provenance(self) -> dict:
        if self._cv is None:
            b = self._pw_obj().chromium.launch(headless=self._headless)
            try:
                self._cv, self._ce = b.version, self._pw.chromium.executable_path
            finally:
                b.close()
        return {"version": self._cv or "unknown", "executable_path": self._ce}

    def playwright_provenance(self) -> dict:
        try:
            import playwright  # type: ignore
            return {"version": playwright.__version__}
        except ImportError:
            return {"version": "unknown"}

    def run_iteration(self, *, target_url, dom_marker_selector, iteration_index):
        browser = self._pw_obj().chromium.launch(headless=self._headless)
        try:
            page = browser.new_page()
            msgs: list[dict] = []
            page.on("console", lambda m: msgs.append({"type": m.type, "text": m.text}))
            resp = page.goto(target_url, wait_until="domcontentloaded")
            nav = page.evaluate(
                "() => { const e = performance.getEntriesByType('navigation')[0];"
                "return e ? {rs:e.responseStart,dcl:e.domContentLoadedEventEnd,"
                "le:e.loadEventEnd,rc:e.redirectCount} : null; }") or {}
            paint = page.evaluate(
                "() => { const o={};"
                "for(const e of performance.getEntriesByType('paint')){"
                " if(e.name==='first-paint')o.fp=e.startTime;"
                " if(e.name==='first-contentful-paint')o.fcp=e.startTime;}"
                "return o; }")
            try:
                page.wait_for_selector(dom_marker_selector, timeout=5000)
                loc = page.locator(dom_marker_selector)
                cnt = loc.count()
                dom = {"selector": dom_marker_selector, "found": bool(cnt),
                       "count": int(cnt),
                       "first_text": loc.first.inner_text() if cnt else None,
                       "wait_ms": 0.0}
            except Exception:
                dom = {"selector": dom_marker_selector, "found": False,
                       "count": 0, "first_text": None, "wait_ms": -1.0}
            return {"iteration": iteration_index, "captured_at": _now_iso(),
                    "navigation": {
                        "response_start_ms": float(nav.get("rs") or 0.0),
                        "dom_content_loaded_ms": float(nav.get("dcl") or 0.0),
                        "load_event_ms": float(nav.get("le") or 0.0),
                        "redirect_count": int(nav.get("rc") or 0),
                        "status": int(resp.status if resp else 0),
                    },
                    "paint": {"first_paint_ms": paint.get("fp"),
                              "first_contentful_paint_ms": paint.get("fcp")},
                    "dom_marker": dom, "console": list(msgs)}
        finally:
            browser.close()


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="capture_hydration.py",
        description="Raw Playwright legacy collector (G5 child; samples-only).")
    p.add_argument("--target-url", required=True, help="Controlled FastAPI target URL (PR #131).")
    p.add_argument("--out", required=True, help="Path to write the raw JSON result.")
    p.add_argument("--iterations", type=int, default=ITERATIONS,
                   help=f"Must equal {ITERATIONS} (G5 contract).")
    p.add_argument("--dom-marker-selector", default=DEFAULT_DOM_MARKER_SELECTOR)
    p.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing --out.")
    p.add_argument("--browser", default="playwright", choices=("playwright",))
    return p.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    if args.iterations != ITERATIONS:
        sys.stderr.write(f"[capture_hydration] --iterations must be {ITERATIONS} (G5 contract); got {args.iterations}\n")
        return EXIT_USAGE
    out_path = Path(args.out)
    try:
        result = collect_raw_samples(
            target_url=args.target_url, browser_adapter=PlaywrightBrowserAdapter(),
            iterations=args.iterations, dom_marker_selector=args.dom_marker_selector)
    except Exception as e:
        sys.stderr.write(f"[capture_hydration] capture failed (fail-closed; no --out written): {e}\n")
        return EXIT_FAILURE
    if args.dry_run:
        sys.stdout.write(json.dumps(result, indent=2) + "\n")
        return EXIT_OK
    try:
        write_result(result, out_path)
    except OSError as e:
        sys.stderr.write(f"[capture_hydration] cannot write --out: {e}\n")
        return EXIT_FAILURE
    sys.stdout.write(f"[capture_hydration] wrote {len(result['samples'])} raw samples to {out_path}\n")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))