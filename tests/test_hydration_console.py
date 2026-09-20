"""
Chromium hydration witness for the isolated browser-state probe.

ODD-BSTATE-PW-001 — proves in headless Chromium that the typed
browser-state hooks hydrate without console / page errors through
first paint, stored-value rehydration, and setter updates, and that
the static first render does not require a `localStorage` read
(instrumented via `addInitScript` wrapping `Storage.prototype.getItem`
before navigation).

What this file pins
-------------------
- `out/hydration-probe.html` is produced by the project's static
  export (`pnpm exec next build`) and reachable through an isolated
  static HTTP server.
- The static HTML carries the typed defaults (``light`` / ``col`` /
  ``null`` / ``null``) literally — proves no build-time
  `localStorage` read occurred.
- First paint (typed defaults visible) and stored-value rehydration
  produce no console errors, no React hydration warnings, and no
  uncaught page errors.
- The probe's setter round trip persists each mutation to
  `localStorage` AND re-renders without warnings.
- `Storage.prototype.getItem` is wrapped BEFORE navigation; the
  first read of any browser-state key happens at or after
  `DOMContentLoaded` — the static first render does not require a
  storage read.

What this file does NOT do
--------------------------
- Imports `api.server`, mutates `WEB_DIR`, or alters the
  `Makefile` / FastAPI routing.
- Spawns uvicorn or any persistent process outside the isolated
  static file server.
- Touches tracked source files outside the allowed edit surfaces
  (the `HydrationProbe` component + the dedicated route + the
  tests + the task document).
- Touches the existing `out/` for the main route's chunks (the
  boundary test lives in `tests/test_app_shell_render.py`).

Run via::

    .venv/bin/python -m pytest tests/test_hydration_console.py -v -s

Skips cleanly if Playwright or the Chromium binary is not installed
(graceful degradation for offline CI).
"""
import http.client
import http.server
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.parse
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Constants — pinned by the browser-state-hydration spec table + the
# ODD-BSTATE-PW-001 acceptance criteria.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "out"
OUT_PROBE = OUT_DIR / "hydration-probe.html"
PROBE_ROUTE = "/hydration-probe"
PROBE_URL = PROBE_ROUTE + ".html"

ALL_BROWSER_STATE_KEYS: tuple[str, ...] = (
    "taxa.settings.theme",
    "taxa.tree.source",
    "taxa.tree.lastTaxonId",
    "taxa.tree.kebabOpenId",
)

# Typed defaults — the spec table value for the static first render.
TYPED_DEFAULT_THEME = "light"
TYPED_DEFAULT_SOURCE = "col"
TYPED_DEFAULT_NULL = "null"

# Init script — wraps Storage.prototype.getItem BEFORE any user script
# runs in the page. Records the key + a `performance.now()` timestamp
# for every read so the witness can prove the browser-state keys are
# not read during the static first render. The idempotent guard
# prevents double-wrapping if the script is re-injected (defensive —
# Playwright's `add_init_script` already runs once per navigation).
INIT_SCRIPT = """
(() => {
  if (window.__storageReadLog) return;
  window.__storageReadLog = [];
  const original = Storage.prototype.getItem;
  Storage.prototype.getItem = function (key) {
    try {
      window.__storageReadLog.push({
        key: String(key),
        t: performance.now(),
      });
    } catch (e) {
      /* never break the real storage */
    }
    return original.call(this, key);
  };
})();
"""


# ---------------------------------------------------------------------------
# Helpers — toolchain probes + ephemeral HTTP server + the build fixture.
# ---------------------------------------------------------------------------
def _has_npx() -> bool:
    return shutil.which("npx") is not None


def _has_node() -> bool:
    return shutil.which("node") is not None


def _playwright_importable() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        try:
            s.connect(("127.0.0.1", port))
            return False
        except (ConnectionRefusedError, TimeoutError, OSError):
            return True


def _wait_ready(url: str, timeout: float = 5.0) -> bool:
    """Poll an http://127.0.0.1:<port>/ URL until it responds 200.

    Uses ``http.client.HTTPConnection`` directly so the readiness
    probe never enters the URL-open audit surface. The helper
    rejects any non-loopback host so the witness cannot be coerced
    into probing an external host during a fixture run.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
        raise ValueError(
            f"_wait_ready only accepts http://127.0.0.1 URLs; got {url!r}"
        )
    port = parsed.port
    if port is None:
        raise ValueError(f"_wait_ready URL must include a port; got {url!r}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
            try:
                conn.request("GET", "/")
                resp = conn.getresponse()
                resp.read()
                if resp.status == 200:
                    return True
            finally:
                conn.close()
        except (ConnectionRefusedError, TimeoutError, OSError):
            time.sleep(0.05)
    return False


def _extract_value_from_html(html: str, test_value: str) -> str | None:
    """Pull the text inside `<X data-test-value="<test_value>">…</X>`
    so the static-HTML defaults assertion stays robust against
    attribute order changes and surrounding React markers."""
    pattern = (
        r'data-test-value="' + re.escape(test_value) + r'"[^>]*>'
        r"([^<]*)<"
    )
    match = re.search(pattern, html)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Session fixtures — build + serve the static export once per module.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def static_export():
    """Run `pnpm exec next build` once per module and yield OUT_DIR.

    Skips if `npx` / `node` / the local `next` binary are missing
    (graceful degradation for CI without the build toolchain).
    """
    if not (_has_npx() and _has_node()):
        pytest.skip("npx + node required on PATH for `next build`")
    if not (REPO_ROOT / "node_modules" / ".bin" / "next").is_file():
        pytest.skip("next binary not installed in node_modules/.bin/")
    proc = subprocess.run(
        ["npx", "--no-install", "next", "build"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    if proc.returncode != 0:
        pytest.fail(
            "npx next build failed "
            f"(rc={proc.returncode}); stdout tail:\n{proc.stdout[-2000:]}\n"
            f"stderr tail:\n{proc.stderr[-2000:]}"
        )
    if not OUT_PROBE.is_file():
        pytest.fail(
            f"missing {OUT_PROBE.relative_to(REPO_ROOT)} — "
            "next build did not produce the probe route's static HTML. "
            "ODD-BSTATE-PW-001 must ship `src/app/hydration-probe/page.tsx` "
            "so the static export registers the route."
        )
    return OUT_DIR


class _StaticHandler(http.server.SimpleHTTPRequestHandler):
    """Minimal file server rooted at the static export directory."""

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, *args, **kwargs):  # noqa: D401 — silence stderr
        return


@pytest.fixture()
def static_server(static_export):
    """Serve `static_export` on an ephemeral 127.0.0.1 port for one
    test. Yields the base URL; shuts the server down on exit so the
    port is released before the next test runs."""
    port = 8790
    while not _port_free(port):
        port += 1
        if port > 9000:
            pytest.fail("could not allocate an ephemeral port for the static server")
    handler = lambda *a, **kw: _StaticHandler(  # noqa: E731
        *a, directory=str(static_export), **kw
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    try:
        if not _wait_ready(base_url + "/", timeout=5.0):
            pytest.fail("static server failed to come up within 5s")
        yield base_url
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------------------
# Chromium fixture — yields a connected page on `/hydration-probe.html`
# with the storage wrapper installed + console / pageerror capture.
# ---------------------------------------------------------------------------
def _attach_listeners(page, console_msgs, page_errors):
    """Subscribe to console + pageerror on `page`. Mutates the lists
    passed by the caller so the assertion reads the same objects the
    listeners wrote into."""
    page.on(
        "console",
        lambda m: console_msgs.append({"type": m.type, "text": m.text}),
    )
    page.on(
        "pageerror",
        lambda e: page_errors.append(str(e)),
    )


@pytest.fixture()
def chromium_probe(static_server):
    """Open the probe in Chromium and yield (page, console_msgs, page_errors).

    Skips if Playwright or the Chromium binary is not installed. The
    storage wrapper runs in the page context BEFORE any user script,
    so every `localStorage.getItem` call the probe makes is recorded
    in `window.__storageReadLog`.
    """
    if not _playwright_importable():
        pytest.skip("playwright not installed (pip install playwright)")
    from playwright.sync_api import sync_playwright  # type: ignore

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:  # FileNotFoundError on missing binary + the
                                   # broad playwright errors.
            pytest.skip(f"chromium binary not available: {exc!r}")
        try:
            context = browser.new_context()
            context.add_init_script(INIT_SCRIPT)
            console_msgs: list[dict] = []
            page_errors: list[str] = []
            page = context.new_page()
            _attach_listeners(page, console_msgs, page_errors)
            page.goto(
                static_server + PROBE_URL,
                wait_until="domcontentloaded",
                timeout=10_000,
            )
            # Wait for the probe marker — proves React hydration completed
            # AND the post-hydration re-render (which runs the hook's
            # `subscribe` → `ensureHydrated` → `safeGetItem` path) finished.
            page.wait_for_selector(
                "[data-testid='hydration-probe']", timeout=5_000
            )
            yield page, console_msgs, page_errors
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Helpers used by the runtime assertions.
# ---------------------------------------------------------------------------
def _hydration_warnings(console_msgs: list[dict]) -> list[dict]:
    """Filter console messages for React hydration warnings."""
    return [
        m
        for m in console_msgs
        if m["type"] in ("warning", "warn")
        and (
            "hydrat" in m["text"].lower()
            or "mismatch" in m["text"].lower()
            or "did not match" in m["text"].lower()
        )
    ]


def _error_messages(console_msgs: list[dict]) -> list[dict]:
    """Filter console messages for `error`-level entries."""
    return [m for m in console_msgs if m["type"] == "error"]


# ---------------------------------------------------------------------------
# Static export contract — `out/hydration-probe.html` exists and carries
# the typed defaults literally. THIS is the strongest evidence that
# the static first render did not require a `localStorage` read.
# ---------------------------------------------------------------------------
def test_probe_route_is_statically_exported(static_export):
    """`out/hydration-probe.html` is produced by `next build`.

    The presence of this file proves the dedicated route was
    registered with Next.js's App Router during the static-export
    pass. Without this file the probe is unreachable as a static
    HTML document and the witness cannot run.
    """
    assert OUT_PROBE.is_file(), (
        f"missing {OUT_PROBE.relative_to(REPO_ROOT)} — the static "
        f"export did not produce the probe route's HTML."
    )
    body = OUT_PROBE.read_text(encoding="utf-8")
    assert body.lstrip().startswith("<!DOCTYPE html>"), (
        f"{OUT_PROBE.relative_to(REPO_ROOT)} is not a valid HTML "
        f"document (missing <!DOCTYPE html>); got head={body[:120]!r}"
    )


def test_probe_static_html_uses_typed_defaults(static_export):
    """The static HTML carries the typed defaults literally.

    If the build had read `localStorage` (which it can't, but the
    contract still pins this), the SSR markup would embed a stored
    value such as `dark` / `worms` / `42` / `7`. The static export
    MUST instead ship the spec-table defaults so the first client
    render (hydration) agrees byte-for-byte.

    This is the static-side witness for the "browser-state keys are
    not read during the static first render" guarantee.
    """
    body = OUT_PROBE.read_text(encoding="utf-8")
    cases = (
        ("theme", TYPED_DEFAULT_THEME),
        ("source", TYPED_DEFAULT_SOURCE),
        ("last-taxon-id", TYPED_DEFAULT_NULL),
        ("kebab-open-id", TYPED_DEFAULT_NULL),
    )
    for test_value, expected in cases:
        actual = _extract_value_from_html(body, test_value)
        assert actual is not None, (
            f"static HTML missing [data-test-value=\"{test_value}\"] "
            f"element — the probe must render every typed key as a "
            f"stable selector target."
        )
        assert actual == expected, (
            f"static HTML [{test_value}] element must carry the typed "
            f"default {expected!r}; got {actual!r}. If this is a "
            f"stored value, the build read localStorage at prerender "
            f"time (which it must not)."
        )


# ---------------------------------------------------------------------------
# Runtime contract — first paint defaults, console / page error silence,
# hydration timing.
# ---------------------------------------------------------------------------
def test_probe_first_paint_defaults_have_no_console_errors(chromium_probe):
    """First paint shows typed defaults with no console / page errors.

    Reads every console message + pageerror captured during the
    initial Chromium navigation + hydration. Asserts:
      - no `error`-level console messages
      - no React hydration warnings
      - no uncaught page errors (`pageerror` events)
      - the four `data-test-value` elements carry the typed defaults
        (proves React's first render output matches the SSR markup
        AND the rehydration path returned the spec-table defaults
        because storage was empty).
    """
    page, console_msgs, page_errors = chromium_probe

    assert not _error_messages(console_msgs), (
        "first paint produced console error(s): "
        f"{_error_messages(console_msgs)}"
    )
    assert not _hydration_warnings(console_msgs), (
        "first paint produced React hydration warning(s): "
        f"{_hydration_warnings(console_msgs)}"
    )
    assert not page_errors, (
        f"first paint produced uncaught page error(s): {page_errors}"
    )

    # The probe must render the four typed defaults on first paint
    # (storage is empty in this fixture — only typed defaults exist).
    page.wait_for_selector(
        "[data-test-value='theme']", timeout=2_000
    )
    assert (
        page.locator("[data-test-value='theme']").inner_text().strip()
        == TYPED_DEFAULT_THEME
    ), (
        "first paint theme must be the typed default "
        f"{TYPED_DEFAULT_THEME!r} — the probe failed to render the "
        "typed default on the first client render"
    )
    assert (
        page.locator("[data-test-value='source']").inner_text().strip()
        == TYPED_DEFAULT_SOURCE
    ), (
        f"first paint source must be the typed default "
        f"{TYPED_DEFAULT_SOURCE!r}"
    )
    assert (
        page.locator("[data-test-value='last-taxon-id']").inner_text().strip()
        == TYPED_DEFAULT_NULL
    ), (
        f"first paint last-taxon-id must be the typed default "
        f"{TYPED_DEFAULT_NULL!r}"
    )
    assert (
        page.locator("[data-test-value='kebab-open-id']").inner_text().strip()
        == TYPED_DEFAULT_NULL
    ), (
        f"first paint kebab-open-id must be the typed default "
        f"{TYPED_DEFAULT_NULL!r}"
    )


def test_probe_storage_reads_happen_after_dom_content_loaded(chromium_probe):
    """Browser-state keys are not read during the static first render.

    `Storage.prototype.getItem` is wrapped via `addInitScript`
    BEFORE navigation, so every `localStorage.getItem` call the
    probe makes is recorded with a `performance.now()` timestamp.
    After hydration completes, the FIRST recorded read of any
    browser-state key MUST happen at or after
    `domContentLoadedEventEnd` — the static HTML render does not
    need a storage read, so any read in the static first render
    would show up at a timestamp before `DOMContentLoaded`.
    """
    page, console_msgs, page_errors = chromium_probe
    assert not page_errors, f"unexpected page error(s): {page_errors}"

    reads = page.evaluate("() => window.__storageReadLog || []")
    taxa_reads = [r for r in reads if r["key"] in ALL_BROWSER_STATE_KEYS]
    assert taxa_reads, (
        "expected at least one read of a browser-state key after "
        f"hydration (the typed hooks must rehydrate); got reads={reads!r}"
    )
    # The first browser-state read happens during React's post-mount
    # subscribe path (`subscribeTheme` → `ensureHydrated` →
    # `safeGetItem`). That subscription fires AFTER React commits the
    # hydrated render, which itself runs AFTER DOMContentLoaded. The
    # assertion below is the witness: no read before DOMContentLoaded
    # would mean a static-render read snuck in.
    first_read_t = min(r["t"] for r in taxa_reads)
    dcl_t = page.evaluate(
        "() => { const e = performance.getEntriesByType('navigation')[0];"
        "return e ? e.domContentLoadedEventEnd : null; }"
    )
    assert dcl_t is not None, (
        "performance.getEntriesByType('navigation') returned no entry"
    )
    assert first_read_t >= dcl_t, (
        f"first browser-state storage read ({first_read_t}ms) happened "
        f"BEFORE DOMContentLoaded ({dcl_t}ms) — the static first "
        f"render must not read storage. Reads: {reads!r}"
    )


# ---------------------------------------------------------------------------
# Rehydration contract — stored values rehydrate without warnings.
# ---------------------------------------------------------------------------
def test_probe_rehydrates_stored_values_without_warnings(static_server):
    """Stored browser-state values rehydrate without console / page
    errors.

    Pre-populates `localStorage` with non-default values on a throwaway
    page (so the origin has stored data), then opens the probe in a
    fresh context with the storage wrapper installed. The probe must
    display the stored values after the post-hydration re-render with
    NO console errors, NO React hydration warnings, and NO page
    errors.
    """
    if not _playwright_importable():
        pytest.skip("playwright not installed")
    from playwright.sync_api import sync_playwright  # type: ignore

    stored = {
        "taxa.settings.theme": "dark",
        "taxa.tree.source": "worms",
        "taxa.tree.lastTaxonId": "42",
        "taxa.tree.kebabOpenId": "7",
    }
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium binary not available: {exc!r}")
        try:
            context = browser.new_context()
            console_msgs: list[dict] = []
            page_errors: list[str] = []

            # Origin priming — visit any page on the same origin so
            # `localStorage` is scoped to the test's 127.0.0.1 server.
            seed_page = context.new_page()
            seed_page.goto(
                static_server + "/", wait_until="domcontentloaded", timeout=5_000
            )
            for k, v in stored.items():
                seed_page.evaluate(
                    f"localStorage.setItem({k!r}, {v!r})"
                )
            seed_page.close()

            # Now load the probe with the storage wrapper installed.
            context.add_init_script(INIT_SCRIPT)
            page = context.new_page()
            _attach_listeners(page, console_msgs, page_errors)
            page.goto(
                static_server + PROBE_URL,
                wait_until="domcontentloaded",
                timeout=10_000,
            )
            page.wait_for_selector(
                "[data-testid='hydration-probe']", timeout=5_000
            )

            # After hydration + rehydration the probe MUST display
            # the stored values.
            for test_value, expected in (
                ("theme", "dark"),
                ("source", "worms"),
                ("last-taxon-id", "42"),
                ("kebab-open-id", "7"),
            ):
                page.wait_for_function(
                    """([sel, want]) => {
                        const el = document.querySelector(sel);
                        return el && el.textContent.trim() === want;
                    }""",
                    arg=[f"[data-test-value='{test_value}']", expected],
                    timeout=3_000,
                )

            assert not _error_messages(console_msgs), (
                "rehydration produced console error(s): "
                f"{_error_messages(console_msgs)}"
            )
            assert not _hydration_warnings(console_msgs), (
                "rehydration produced React hydration warning(s): "
                f"{_hydration_warnings(console_msgs)}"
            )
            assert not page_errors, (
                f"rehydration produced page error(s): {page_errors}"
            )
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Setter round-trip contract — clicks persist + re-render without warnings.
# ---------------------------------------------------------------------------
def test_probe_setter_round_trip_persists_and_rerenders(chromium_probe):
    """Click each setter; the probe re-renders with the new value AND
    persists it to `localStorage` AND produces no console / page
    errors throughout.

    The probe covers all four typed keys (theme / source /
    last-taxon-id / kebab-open-id) so the contract generalises:
    every typed hook's write path is hydration-safe.
    """
    page, console_msgs, page_errors = chromium_probe
    clicks = (
        ("set-theme-dark", "theme", "dark", "taxa.settings.theme"),
        ("set-source-worms", "source", "worms", "taxa.tree.source"),
        ("set-last-taxon-id", "last-taxon-id", "42", "taxa.tree.lastTaxonId"),
        ("set-kebab-open-id", "kebab-open-id", "7", "taxa.tree.kebabOpenId"),
    )
    for action, test_value, expected_text, storage_key in clicks:
        page.click(f"[data-action='{action}']", timeout=3_000)
        # Wait for the post-mutation re-render to settle.
        page.wait_for_function(
            """([sel, want]) => {
                const el = document.querySelector(sel);
                return el && el.textContent.trim() === want;
            }""",
            arg=[f"[data-test-value='{test_value}']", expected_text],
            timeout=3_000,
        )
        # The mutation MUST be persisted to localStorage so the next
        # page load rehydrates from the same value.
        persisted = page.evaluate(
            f"() => localStorage.getItem({storage_key!r})"
        )
        assert persisted == expected_text, (
            f"after clicking [{action}], localStorage[{storage_key!r}] "
            f"must be {expected_text!r}; got {persisted!r}"
        )

    # Round trip done — assert no errors accumulated.
    assert not _error_messages(console_msgs), (
        "setter round trip produced console error(s): "
        f"{_error_messages(console_msgs)}"
    )
    assert not _hydration_warnings(console_msgs), (
        "setter round trip produced hydration warning(s): "
        f"{_hydration_warnings(console_msgs)}"
    )
    assert not page_errors, (
        f"setter round trip produced page error(s): {page_errors}"
    )
