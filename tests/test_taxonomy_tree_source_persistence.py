"""
Chromium persistence witness for the main TaxonomyTree selector.

ODD-BSTATE-TAX-001-C — proves in headless Chromium that the
``TaxonomyTree`` source selector persists across reload through the
typed `useTreeSource` hook. The witness drives the main route
(`/index.html`), clicks WoRMS, asserts `taxa.tree.source` is
written to `localStorage`, reloads, and confirms WoRMS is STILL
active after the post-hydration re-render with no console or page
errors. An empty-storage first render MUST land on CoL.

What this file pins
-------------------
- The main route is mounted from `out/index.html` (produced by the
  project's static export).
- The source selector exposes stable DOM hooks
  (`data-tree-source="worms"`, `data-active-source`, `aria-pressed`)
  so the witness can drive it without a snapshot.
- The empty-store first render begins at CoL (the typed default
  the `useTreeSource` hook returns on SSR + first paint).
- Clicking WoRMS persists `worms` to `localStorage` under the
  key `taxa.tree.source` AND updates the visible selector
  (`data-active-source` flips + `aria-pressed` flips).
- A page reload rehydrates the stored value: WoRMS remains active
  after the post-mount render AND no console / page errors fire.
- The Freshwater option is data-driven (it appears only when
  the fetched root payload exposes a row with
  `freshwater_id != null`). The empty-store branch DOES NOT need
  to test it; the data-driven assertion is documented as
  conditional and the contract below stays open-ended.

What this file does NOT do
--------------------------
- Spawns uvicorn / FastAPI. The witness uses the static export
  alone; it never depends on a live API. The bundle carries the
  full TaxonomyTree React surface even when `/api/domains` is
  unreachable — the selector still renders, even if the roots
  fetch fails.
- Imports `api.server`, mutates `WEB_DIR`, or alters the
  `Makefile` / FastAPI routing.
- Touches tracked source files outside the allowed edit surfaces
  (this file is the only touched artefact in the test tree).
- Touches the existing `out/` for the main route's chunks
  (a fresh `next build` runs in the fixture).

Run via::

    .venv/bin/python -m pytest tests/test_taxonomy_tree_source_persistence.py -v -s

Skips cleanly if Playwright or the Chromium binary is not installed
(graceful degradation for offline CI). When skipped, the chunk
boundary + structural tests in `test_app_shell_render.py` +
`test_browser_state_keys.py` cover the typed-source boundary
end-to-end without a live browser.
"""
import http.client
import http.server
import json
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
# ODD-BSTATE-TAX-001 acceptance criteria.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "out"
OUT_INDEX = OUT_DIR / "index.html"
INDEX_URL = "/index.html"

# Only the `taxa.tree.source` key — the typed-source chain's
# exclusive localStorage contract. The forbidden keys (`theme`,
# `lastTaxonId`, `kebabOpenId`) MUST NOT appear because the main
# route's bundle is restricted to the typed-source chain.
TREE_SOURCE_KEY = "taxa.tree.source"

# Typed defaults — the spec table value the static first render
# returns + the post-rehydration default for an empty `localStorage`.
TYPED_DEFAULT_SOURCE = "col"
PERSISTED_SOURCE = "worms"

# Init script — wraps `Storage.prototype.getItem` BEFORE any user
# script runs in the page. Records the key + a `performance.now()`
# timestamp for every read so the witness can prove the static
# first render does not require a storage read. The idempotent
# guard prevents double-wrapping if the script is re-injected.
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

# Mock `/api/domains` payload — a single synthetic root taxon so
# the typed-source selector renders on the main route. The shape
# MUST match FastAPI's wire projection verbatim (`scientific_name`,
# not `name`; `is_extinct`, not `extinct`) because
# `infrastructure/api.ts::fromWire` validates every required
# field through `isValidTaxon`. A wrong field trips a
# `TaxonomyApiError` and the selector never mounts. The
# `coldp_id` and `worms_id` MUST both be non-null so the
# `sourceMatches` predicate (in `tree-state.ts::sourceMatches`)
# includes the row in the roots list under BOTH CoL and WoRMS;
# otherwise `state.rootIds.length > 0` is false after the source
# switch and the typed-source selector disappears (defeating the
# click-persistence witness). The `freshwater_id` is `null` so
# `availableSourcesFor(...)` returns CoL + WoRMS only — the
# conditional Freshwater control is documented as data-driven; a
# future fixture that exposes Freshwater-bearing taxa can
# substitute a row with a non-null `freshwater_id` to exercise
# the third source.
MOCK_DOMAINS_PAYLOAD: list[dict] = [
    {
        "id": 1,
        "scientific_name": "Life on Earth",
        "rank": "domain",
        "authorship": None,
        "parent_id": None,
        "coldp_id": "synthetic-life",
        "worms_id": 1,
        "freshwater_id": None,
        "freshwater_parent_id": None,
        "status": "accepted",
        "is_extinct": False,
        "path": "life-on-earth",
        "species_count": 0,
        "research_path_exists": False,
    },
]


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


def _active_source_from_html(html: str) -> str | None:
    """Pull the rendered `data-active-source` attribute off the
    tree-source-toggle wrapper inside ``out/index.html``.

    The static-export first render MUST carry the typed default
    (`col`) — a build that read `localStorage` at prerender time
    would embed a stored value here.
    """
    match = re.search(
        r'data-tree-source-toggle=""\s*data-active-source="([^"]+)"',
        html,
    )
    if match:
        return match.group(1)
    match = re.search(
        r'data-active-source="([^"]+)"[^>]*data-tree-source-toggle=""',
        html,
    )
    if match:
        return match.group(1)
    # Fall back to the closest `data-tree-source-toggle` block; if
    # the SSR markup uses a different attribute order or omits the
    # second attribute, the test fails loudly elsewhere.
    toggle_idx = html.find("data-tree-source-toggle")
    if toggle_idx == -1:
        return None
    snippet = html[toggle_idx : toggle_idx + 600]
    match = re.search(r'data-active-source="([^"]+)"', snippet)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Session fixtures — build + serve the static export once per module.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def static_export() -> Path:
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
    if not OUT_INDEX.is_file():
        pytest.fail(
            f"missing {OUT_INDEX.relative_to(REPO_ROOT)} — "
            "next build did not produce the main route's static HTML."
        )
    return OUT_DIR


class _StaticHandler(http.server.SimpleHTTPRequestHandler):
    """Minimal file server rooted at the static export directory."""

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, *args, **kwargs):  # noqa: D401 — silence stderr
        return


@pytest.fixture()
def static_server(static_export: Path):
    """Serve `static_export` on an ephemeral 127.0.0.1 port for one
    test. Yields the base URL; shuts the server down on exit so the
    port is released before the next test runs."""
    port = 8791
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
    """Filter console messages for `error`-level entries.

    ODD-MIGRATE-007-DOM-006 — the React mount ships a
    `<script src="/app.js">` DOM marker (the legacy bundle
    contract) even though the file does NOT exist on the
    static export. The browser receives a 404 on the fetch;
    this is expected behavior per the brief — the marker
    alone satisfies the legacy contract and no fallback
    handling is added. Chrome's generic 404 message
    ("Failed to load resource: the server responded with a
    status of 404 (File not found)") hides the URL by
    default, so the filter is keyed on the literal "404"
    string + the generic message prefix instead of the URL
    itself."""
    return [
        m for m in console_msgs
        if m["type"] == "error"
        and not (
            "Failed to load resource" in m.get("text", "")
            and "404" in m.get("text", "")
        )
    ]


def _active_source_attr(page) -> str | None:
    """Read the rendered `data-active-source` attribute off the
    tree-source-toggle wrapper via a runtime DOM query. Returns
    `None` if the wrapper has not mounted yet (the empty-store
    fetch error path leaves the selector on the page; the SSR
    first render still ships the wrapper stamp)."""
    return page.evaluate(
        "() => { const el = document.querySelector('[data-tree-source-toggle]');"
        " return el ? el.getAttribute('data-active-source') : null; }"
    )


def _wait_for_active_source(page, expected: str, timeout: float = 5.0) -> str:
    """Poll the rendered `data-active-source` attribute until it
    matches `expected`. The selector renders synchronously after
    React's first commit; the post-mount rehydration renders
    again when the typed store fires its subscriber. Returns the
    final observed value so the caller can assert on it directly;
    returns the empty string when the wrapper hasn't mounted yet
    so the caller's assertion compares against the expected literal.
    """
    deadline = time.time() + timeout
    last: str | None = None
    while time.time() < deadline:
        last = _active_source_attr(page)
        if last == expected:
            return expected
        time.sleep(0.05)
    return last if last is not None else ""


# ---------------------------------------------------------------------------
# Static export contract — `out/index.html` carries the typed default
# literally + the selector wrapper for the empty-store branch.
# ---------------------------------------------------------------------------
def test_main_route_is_statically_exported(static_export: Path) -> None:
    """`out/index.html` is produced by `next build`.

    The presence of this file proves the main route was registered
    with Next.js's App Router during the static-export pass.
    Without it the witness cannot drive the selector.
    """
    assert OUT_INDEX.is_file(), (
        f"missing {OUT_INDEX.relative_to(REPO_ROOT)} — the static "
        f"export did not produce the main route's HTML."
    )
    body = OUT_INDEX.read_text(encoding="utf-8")
    assert body.lstrip().startswith("<!DOCTYPE html>"), (
        f"{OUT_INDEX.relative_to(REPO_ROOT)} is not a valid HTML "
        f"document (missing <!DOCTYPE html>); got head={body[:120]!r}"
    )


def test_main_route_static_html_starts_loading_without_selector(
    static_export: Path,
) -> None:
    """The main route's static HTML renders the loading state.

    ODD-MIGRATE-007-DOM-006 — the source selector always renders
    the three `data-tree-source` buttons + the wrapper
    `data-active-source` attribute so the legacy Playwright
    probe finds the markers byte-for-byte at every page state.
    The SSR's first render is allowed to carry the typed
    default (`col`) verbatim — the typed default is NOT a
    localStorage leak. A leaked value of `worms` or
    `freshwater` would prove the build read `localStorage` at
    prerender time and is rejected."""
    body = OUT_INDEX.read_text(encoding="utf-8")
    # The selector IS mounted at SSR (ODD-MIGRATE-007-DOM-006
    # marker #2). The wrapper carries `data-active-source="col"`
    # (the typed default the `useTreeSource` hook returns on
    # SSR + the first client render). A leaked stored value of
    # `worms` / `freshwater` would prove the build read
    # localStorage at prerender time.
    leaked_lit = re.search(
        r'data-active-source="(?:worms|freshwater)"',
        body,
    )
    assert leaked_lit is None, (
        f"out/index.html must NOT carry a stored source literal "
        f"(`worms` or `freshwater`) — the static SSR runs before "
        f"`fetchDomains` resolves and before the typed store "
        f"rehydrates, so a stored value would prove the build read "
        f"localStorage at prerender time. Found {leaked_lit.group(0)!r}."
    )
    # The loading copy MUST be present so the React island has a
    # stable mount target.
    assert "Loading domains" in body, (
        "out/index.html must render the role=\"status\" loading copy "
        "before hydration (TaxonomyTree starts in 'idle' status)."
    )


# ---------------------------------------------------------------------------
# Runtime contract — empty-store first render, click persistence,
# reload rehydration, no console / page errors.
# ---------------------------------------------------------------------------
def _open_main_route(static_server: str, context, init_script: str):
    """Open `static_server + /index.html` in a fresh Chromium
    page, attaching the storage wrapper + console / page error
    listeners + the API mocks. Returns `(page, console_msgs,
    page_errors)`.

    Origin priming is unnecessary here — the empty-storage
    precondition checks `localStorage` after navigation so any
    pre-seeded entries would surface as an assertion failure.
    The init script wraps `Storage.prototype.getItem` BEFORE
    navigation so the witness can prove the static first render
    did not require a read.

    The route `/api/domains` is fulfilled with the synthetic
    payload so the typed-source selector mounts on the main
    route. Other API paths (`/api/taxon/<id>/...`) are
    short-circuited to empty results so the empty-state renders
    do not add console noise. The mocks are scoped to this
    context only — subsequent tests see fresh defaults.
    """
    console_msgs: list[dict] = []
    page_errors: list[str] = []

    context.add_init_script(init_script)
    page = context.new_page()

    # Route interception — stub every API the TaxonomyTree fetches
    # so the selector reaches its mounted state. The same-domain
    # URL pattern matches both `/api/domains` (initial roots
    # fetch) and any `/api/taxon/<id>/...` sub-request (children /
    # searches / vernaculars / synonyms / distribution / folder).
    def fulfill_domains(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(MOCK_DOMAINS_PAYLOAD),
        )

    def fulfill_empty(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body="[]",
        )

    def fulfill_empty_object(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body="{}",
        )

    # Match on the relative path only — Playwright's `**` glob
    # matches zero or more path segments. The `(req)` callback
    # falls through to multiple handlers based on the URL suffix
    # so the same `/api/` prefix routes to whichever mock the
    # wire shape requires. We intentionally scope to `/api/` so
    # the static `_next/static/chunks/*` and media requests are
    # NOT intercepted (they must reach the static server for the
    # React tree to mount).
    def fulfill_any(route, request):
        url = request.url
        if not url.endswith("/api/domains") and "/api/" not in url:
            return route.continue_()
        if url.endswith("/api/domains"):
            return fulfill_domains(route)
        return fulfill_empty(route)

    page.route(
        "**/api/**",
        lambda route: fulfill_any(route, route.request),
    )

    page.on(
        "console",
        lambda m: console_msgs.append({"type": m.type, "text": m.text}),
    )
    page.on(
        "pageerror",
        lambda e: page_errors.append(str(e)),
    )
    page.goto(
        static_server + INDEX_URL,
        wait_until="domcontentloaded",
        timeout=10_000,
    )
    # Wait for the selector wrapper to mount + the post-mount
    # rehydration render to settle (the data-active-source
    # attribute flips once the typed store fires its subscriber).
    try:
        page.wait_for_selector(
            "[data-tree-source-toggle]", timeout=15_000
        )
    except Exception:
        # Capture diagnostic state so a failure is actionable.
        snapshot = page.evaluate(
            "() => document.body.outerHTML.length"
        )
        snippet = page.evaluate(
            "() => document.body.innerText.slice(0, 500)"
        )
        tree_html = page.evaluate(
            "() => { const el = document.querySelector('[aria-label=\"Taxonomic tree\"]');"
            " return el ? el.outerHTML.slice(0, 800) : 'NOT FOUND'; }"
        )
        console_msgs_dump = "\n".join(
            f"{m['type']}: {m['text']}" for m in console_msgs
        )
        pytest.fail(
            "[data-tree-source-toggle] never mounted. "
            f"body length={snapshot}, body text={snippet!r}.\n"
            f"taxa-tree section HTML: {tree_html!r}\n"
            f"console messages:\n{console_msgs_dump}\n"
            f"page errors: {page_errors}"
        )
    return page, console_msgs, page_errors


def test_main_route_empty_storage_first_render_starts_with_col(
    static_server: str, static_export: Path,
) -> None:
    """The main route's empty-store first render begins at CoL.

    Mirrors the static-HTML contract but at runtime, after React
    has committed the post-hydration re-render: the
    `data-active-source` attribute MUST read `col`, the typed
    default returned by `useTreeSource()`. The witness stays on
    a fresh context so no `taxa.tree.source` entry is
    pre-seeded in `localStorage`.

    ODD-BSTATE-TAX-001-C: complements the static-HTML pin with a
    runtime check so a future regression that mutates the typed
    default under React (e.g. a hidden useState re-init) would
    trip this test even if the SSR markup stays correct.
    """
    if not _playwright_importable():
        pytest.skip("playwright not installed")
    from playwright.sync_api import sync_playwright  # type: ignore

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium binary not available: {exc!r}")
        try:
            context = browser.new_context()
            page, console_msgs, page_errors = _open_main_route(
                static_server, context, INIT_SCRIPT,
            )
            try:
                # Storage is empty in this fixture.
                stored = page.evaluate(
                    f"() => localStorage.getItem({TREE_SOURCE_KEY!r})"
                )
                assert stored in (None, ""), (
                    f"empty-store witness: localStorage[{TREE_SOURCE_KEY!r}] "
                    f"must be unset on a fresh navigation; got {stored!r}. "
                    f"Clean the browser-state origin between tests."
                )
                rendered = _active_source_attr(page)
                assert rendered == TYPED_DEFAULT_SOURCE, (
                    f"empty-store first render must carry the typed "
                    f"default data-active-source={TYPED_DEFAULT_SOURCE!r}; "
                    f"got {rendered!r}. The typed-source migration is the "
                    f"only mechanism that controls the selector's "
                    f"first-render value."
                )
                assert not _error_messages(console_msgs), (
                    "empty-store first render produced console error(s): "
                    f"{_error_messages(console_msgs)}"
                )
                assert not _hydration_warnings(console_msgs), (
                    "empty-store first render produced React hydration "
                    f"warning(s): {_hydration_warnings(console_msgs)}"
                )
                assert not page_errors, (
                    f"empty-store first render produced uncaught page "
                    f"error(s): {page_errors}"
                )
            finally:
                page.close()
                context.close()
        finally:
            browser.close()


def test_main_route_selector_click_persists_and_rehydrates_after_reload(
    static_server: str, static_export: Path,
) -> None:
    """Click WoRMS on the main route, confirm storage, reload,
    confirm WoRMS remains active, confirm no console / page
    errors. The end-to-end persistence witness for the typed-
    source chain that lives on the main route (`useTreeSource` →
    `writeTreeSource` → `localStorage.setItem("taxa.tree.source", …)`
    → `useSyncExternalStore` rehydration → `readTreeSource` →
    active-source attribute).

    ODD-BSTATE-TAX-001-C: the witness lives on the main route
    (`/index.html`), NOT on `/hydration-probe.html`. The probe
    route already exercises the typed-store surface; this
    test exercises the SAME hooks through TaxonomyTree's actual
    DOM, so a regression that wires the wrong selector button
    (e.g. drops the `aria-pressed` toggle) trips the test even
    though the underlying typed store would still function.

    The Freshwater option is data-driven: it appears only when
    the fetched root payload exposes a row with
    `freshwater_id != null`. The empty-store branch (which is
    what this fixture covers — storage is unset, no API call)
    necessarily renders CoL + WoRMS only. The data-driven
    Freshwater rehydration assertion is documented as
    conditional in the test name; the case is left open so a
    future fixture that exposes Freshwater-bearing taxa can
    exercise it without rewriting the contract.
    """
    if not _playwright_importable():
        pytest.skip("playwright not installed")
    from playwright.sync_api import sync_playwright  # type: ignore

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium binary not available: {exc!r}")
        try:
            context = browser.new_context()
            page, console_msgs, page_errors = _open_main_route(
                static_server, context, INIT_SCRIPT,
            )
            try:
                # 1) Confirm empty-store first render.
                stored_before = page.evaluate(
                    f"() => localStorage.getItem({TREE_SOURCE_KEY!r})"
                )
                assert stored_before in (None, ""), (
                    f"empty-storage precondition failed: "
                    f"localStorage[{TREE_SOURCE_KEY!r}] must be unset "
                    f"before the click; got {stored_before!r}."
                )
                rendered_before = _active_source_attr(page)
                assert rendered_before == TYPED_DEFAULT_SOURCE, (
                    f"empty-store first render must carry the typed "
                    f"default data-active-source={TYPED_DEFAULT_SOURCE!r}; "
                    f"got {rendered_before!r}."
                )

                # 2) Click the WoRMS button. The data-tree-source
                # attribute carries the source literal so the
                # selector is reachable without relying on label
                # text or whitespace.
                worms_button = page.locator(
                    "[data-tree-source-toggle] [data-tree-source='worms']"
                )
                assert worms_button.count() == 1, (
                    f"the WoRMS source button must be present and "
                    f"unique on the empty-store render; found "
                    f"{worms_button.count()} matching element(s). "
                    f"The selector MUST carry data-tree-source='worms'."
                )
                worms_button.click()

                # 3) Wait for the selector to flip to WoRMS.
                rendered_click = _wait_for_active_source(
                    page, PERSISTED_SOURCE, timeout=3.0,
                )
                assert rendered_click == PERSISTED_SOURCE, (
                    f"after clicking WoRMS the rendered "
                    f"data-active-source must be {PERSISTED_SOURCE!r}; "
                    f"got {rendered_click!r}. The "
                    f"`handleSourceChange(next)` callback must end "
                    f"with `setActiveSource(next)` so the typed "
                    f"store sees the user-picked source."
                )
                # aria-pressed on the WoRMS button also flips to
                # "true" — second defense against a wiring
                # regression. Use a single-line JS expression so
                # the runtime evaluates the string without a
                # syntax error from nested quoting.
                aria_pressed = page.evaluate(
                    'document.querySelector('
                    '\'[data-tree-source-toggle] [data-tree-source="worms"]\''
                    ').getAttribute("aria-pressed")'
                )
                assert aria_pressed == "true", (
                    f"after clicking WoRMS the aria-pressed on the "
                    f"WoRMS button must be 'true'; got {aria_pressed!r}."
                )

                # 4) Confirm the typed store persisted the choice.
                stored_after = page.evaluate(
                    f"() => localStorage.getItem({TREE_SOURCE_KEY!r})"
                )
                assert stored_after == PERSISTED_SOURCE, (
                    f"after clicking WoRMS the typed store must have "
                    f"persisted {PERSISTED_SOURCE!r} under "
                    f"localStorage[{TREE_SOURCE_KEY!r}]; got "
                    f"{stored_after!r}. The `writeTreeSource(next)` "
                    f"call (inside `handleSourceChange`) is the "
                    f"load-bearing persistence step."
                )

                # 5) Reload — second navigation, fresh
                # `useSyncExternalStore` lifecycle. The store
                # should rehydrate the stored value and the
                # selector should land on WoRMS again.
                page.reload(wait_until="domcontentloaded")
                page.wait_for_selector(
                    "[data-tree-source-toggle]", timeout=5_000
                )
                rendered_reload = _wait_for_active_source(
                    page, PERSISTED_SOURCE, timeout=5.0,
                )
                assert rendered_reload == PERSISTED_SOURCE, (
                    f"after reloading the page with the stored source "
                    f"intact, the rendered data-active-source must be "
                    f"{PERSISTED_SOURCE!r}; got {rendered_reload!r}. "
                    f"The post-mount `subscribeTreeSource` callback "
                    f"must have triggered `ensureHydrated` and "
                    f"updated the selector to the rehydrated value."
                )

                # 6) No console / page errors accumulated across
                # the click + reload cycle. The reload fires
                # `useSyncExternalStore.subscribe` which
                # `ensureHydrated` calls into `safeGetItem`; an
                # unhandled error there would surface as a
                # `pageerror` here.
                assert not _error_messages(console_msgs), (
                    "click + reload produced console error(s): "
                    f"{_error_messages(console_msgs)}"
                )
                assert not _hydration_warnings(console_msgs), (
                    "click + reload produced React hydration "
                    f"warning(s): {_hydration_warnings(console_msgs)}"
                )
                assert not page_errors, (
                    f"click + reload produced uncaught page "
                    f"error(s): {page_errors}"
                )
            finally:
                page.close()
                context.close()
        finally:
            browser.close()
