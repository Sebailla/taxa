"""
Hydration console contract tests for PR 4b — AppShell integration.

Pins the React hydration safety contract: when the migrated App Router
build loads in chromium, the browser console must NOT emit any of the
following React hydration warnings after the first paint + rehydration
cycle:

  - "Warning: Text content did not match."
  - "Warning: Expected server HTML to contain"
  - "Warning: Hydration failed"
  - "Warning: Hydration error"

Three witnesses in one file (PR 4b.1 / 4b.6 / 4b.4):

  1. `test_no_hydration_warnings_on_first_paint`
       Main RED gate (4b.1).
  2. `test_app_shell_renders_nav_tabs`
       Wiring witness — proves the integration seam is wired.
  3. `test_stored_dark_theme_rehydrates_with_zero_warnings`
       Triangulation (4b.4) — stored dark theme must flip <html>.

References:
  openspec/changes/complete-taxa-frontend-migration/tasks.md
      §Phase 4b (4b.1, 4b.4, 4b.6)
  openspec/changes/complete-taxa-frontend-migration/specs/
      browser-state-hydration/spec.md  §"Hydration guard"
"""
from __future__ import annotations

import functools
import http.server
import json
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "out"
OUT_INDEX = OUT_DIR / "index.html"
APP_SHELL_BARREL = REPO_ROOT / "src" / "modules" / "app-shell" / "index.ts"
BROWSER_STATE_BARREL = REPO_ROOT / "src" / "modules" / "browser-state" / "index.ts"
SRC_APP_LAYOUT = REPO_ROOT / "src" / "app" / "layout.tsx"
PORT = 8770  # non-default to avoid 8765 (dev) / 8767 (toggle) / 8768 (e2e)
BASE_URL = f"http://127.0.0.1:{PORT}"

# React 19 hydration warning signatures — pinned as regexes so a future
# React upgrade that prefixes a build tag still matches.
HYDRATION_WARNING_PATTERNS: tuple[str, ...] = (
    r"Warning:\s*Text content did not match",
    r"Warning:\s*Expected server HTML to contain",
    r"Warning:\s*Hydration failed",
    r"Warning:\s*Hydration error",
)


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


def _check_playwright_available():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return None
    return True


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


def _build_static_export() -> None:
    """Run `npx next build` and assert `out/index.html` is produced."""
    if not (REPO_ROOT / "node_modules" / ".bin" / "next").is_file() and shutil.which("next") is None:
        pytest.skip("next binary not installed — skip static-export build witness")
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
            f"npx next build failed (rc={proc.returncode}); "
            f"stdout tail:\n{proc.stdout[-2000:]}\nstderr tail:\n{proc.stderr[-2000:]}"
        )
    if not OUT_INDEX.is_file():
        pytest.fail(f"next build did not produce {OUT_INDEX.relative_to(REPO_ROOT)}")


class _StaticExportHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the static export with cache disabled so reloads see the
    latest build (and the localStorage rehydration cycle is honest)."""

    def __init__(self, *args, directory: str | None = None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def end_headers(self) -> None:  # type: ignore[override]
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


@pytest.fixture(scope="module")
def static_export_server():
    """Yield a running static-export HTTP server rooted at `out/`.

    Builds the static export on demand. Skips when the port is busy,
    the build cannot run, or the server cannot come up.
    """
    if not _port_free(PORT):
        pytest.skip(f"port {PORT} is in use")
    if not OUT_INDEX.is_file():
        _build_static_export()
    if not OUT_INDEX.is_file():
        pytest.skip("out/index.html not produced")

    handler = functools.partial(_StaticExportHandler, directory=str(OUT_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    thread = threading.Thread(target=server.serve_forever, name="static-export")
    thread.daemon = True
    thread.start()
    try:
        if not _wait_ready(f"{BASE_URL}/index.html", timeout=10.0):
            pytest.skip(f"static-export server failed to respond on {PORT}")
        yield {"base_url": BASE_URL}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _launch_chromium(pw):
    try:
        return pw.chromium.launch(headless=True)
    except Exception as exc:  # noqa: BLE001 — Playwright raises broad exc
        pytest.skip(f"chromium binary not available: {exc!r}")


# ---------------------------------------------------------------------------
# Source-level witnesses — pin the public barrel + App Router integration
# ---------------------------------------------------------------------------
def test_browser_state_barrel_exports_use_mounted():
    """`browser-state` public barrel MUST re-export `useMounted`.

    PR 4b.5 (refactor) extracts the `mounted` flag into a reusable
    hook. Without the barrel export, cross-module consumers cannot
    reach the hook without a deep import — a spec.md rule 5 violation.
    """
    text = BROWSER_STATE_BARREL.read_text(encoding="utf-8")
    # Comment-strip so a future JSDoc reference to `useMounted` does not
    # satisfy the contract.
    stripped = re.sub(r"/\*[\s\S]*?\*/", "", text)
    stripped = re.sub(r"//[^\n]*", "", stripped)
    assert re.search(r"""export\s*\{\s*[^}]*\buseMounted\b""", stripped), (
        "src/modules/browser-state/index.ts MUST re-export `useMounted` "
        "(PR 4b.5 refactor contract); got:\n" + stripped
    )


def test_app_shell_barrel_exports_app_shell_component():
    """`app-shell` public barrel MUST re-export the `AppShell` component.

    PR 4b.6 integration seam: `src/app/layout.tsx` imports `AppShell`
    from `@taxa/app-shell` and wraps the body. Without the barrel
    export, the integration is unsatisfiable without a deep import.
    """
    text = APP_SHELL_BARREL.read_text(encoding="utf-8")
    # Comment-strip the barrel so a JSDoc mention of `AppShell` (the
    # legacy barrel that ships an empty `export {}` plus an explanatory
    # comment) does not satisfy the contract.
    stripped = re.sub(r"/\*[\s\S]*?\*/", "", text)
    stripped = re.sub(r"//[^\n]*", "", stripped)
    assert re.search(r"""export\s*\{\s*[^}]*\bAppShell\b""", stripped), (
        "src/modules/app-shell/index.ts MUST re-export the `AppShell` "
        "component (PR 4b.6 integration seam contract); got:\n"
        + stripped
    )


def test_app_layout_wraps_children_with_app_shell():
    """`src/app/layout.tsx` MUST import `AppShell` from `@taxa/app-shell`
    and wrap `{children}` with `<AppShell>...</AppShell>`.

    This is the App Router host integration seam the dependency-defect
    fix moved from PR 3b to PR 4b (PR 4b owns both the module AND the
    integration seam).
    """
    layout = SRC_APP_LAYOUT.read_text(encoding="utf-8")
    assert re.search(
        r"""from\s+["']@taxa/app-shell["']""",
        layout,
    ), (
        "src/app/layout.tsx MUST import AppShell from `@taxa/app-shell` "
        "(PR 4b.6 integration seam contract)"
    )
    assert re.search(
        r"""<AppShell\b[^>]*>\s*\{children\}\s*</AppShell>""",
        layout,
        re.DOTALL,
    ), (
        "src/app/layout.tsx MUST wrap `{children}` with `<AppShell>...</AppShell>` "
        "(PR 4b.6 integration seam contract)"
    )


# ---------------------------------------------------------------------------
# Hydration console witnesses — the main RED gate
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_no_hydration_warnings_on_first_paint(static_export_server):
    """PR 4b.1 — load migrated build in chromium, assert zero hydration
    warnings after first paint + rehydration.

    BEFORE the AppShell integration lands, the page renders the bare
    `<main><h1>taxa</h1></main>` placeholder and the contract is
    trivially satisfied. The GREEN phase wires `<AppShell>` into the
    layout; the contract must STILL hold even though the AppShell now
    reads the typed `browser-state` store behind the `useMounted()` flag.
    """
    from playwright.sync_api import sync_playwright  # type: ignore

    base = static_export_server["base_url"]
    with sync_playwright() as pw:
        browser = _launch_chromium(pw)
        try:
            page = browser.new_page()
            warnings: list[str] = []
            page.on(
                "console",
                lambda msg: warnings.append(msg.text)
                if msg.type in ("warning", "error")
                else None,
            )
            page.goto(base + "/", wait_until="domcontentloaded", timeout=10_000)
            # 500ms > React 19's hydration deadline so any deferred
            # `useEffect` from the AppShell has time to run.
            page.wait_for_timeout(500)

            offenders = [
                w for w in warnings
                if any(re.search(pat, w) for pat in HYDRATION_WARNING_PATTERNS)
            ]
            assert not offenders, (
                f"hydration warnings fired on first paint: {offenders!r}\n"
                f"all warnings captured: {warnings!r}"
            )
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Wiring witness — proves the integration seam is wired
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_app_shell_renders_nav_tabs(static_export_server):
    """PR 4b wiring witness — AppShell's nav tabs must be in the DOM.

    BEFORE the integration: the page is the bare placeholder, zero nav
    tabs. GREEN: PR 4b's `page-chrome.tsx` renders three nav tabs
    (Browser / Classification / Settings) with the pinned
    `data-action="nav-tab"` / `data-path` contract.
    """
    from playwright.sync_api import sync_playwright  # type: ignore

    base = static_export_server["base_url"]
    with sync_playwright() as pw:
        browser = _launch_chromium(pw)
        try:
            page = browser.new_page()
            page.goto(base + "/", wait_until="domcontentloaded", timeout=10_000)
            page.wait_for_selector('[data-action="nav-tab"]', timeout=5_000)
            tabs = page.locator('[data-action="nav-tab"]')
            count = tabs.count()
            assert count >= 3, f"AppShell must render >= 3 nav tabs; got {count}"
            paths = [tabs.nth(i).get_attribute("data-path") or "" for i in range(count)]
            for required in ("browser", "classification", "settings"):
                assert required in paths, (
                    f"AppShell nav tabs must include `data-path={required!r}`; "
                    f"got {paths!r}"
                )
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Triangulation (4b.4) — rehydration with a stored theme must flip <html>
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    _check_playwright_available() is None,
    reason="playwright not installed (pip install playwright)",
)
def test_stored_dark_theme_rehydrates_with_zero_warnings(static_export_server):
    """PR 4b.4 triangulation — seed
    `localStorage.taxa.settings.theme = "dark"`, reload, assert zero
    hydration warnings AND `<html data-theme="dark">` after the
    rehydration cycle.

    Proves the typed store rehydrates from `localStorage` without
    falling out of sync with the SSR shell — the
    `useEffect`-behind-`useMounted()` pattern in the AppShell must
    flip `<html data-theme>` AFTER the first paint, never before.
    """
    from playwright.sync_api import sync_playwright  # type: ignore

    base = static_export_server["base_url"]
    with sync_playwright() as pw:
        browser = _launch_chromium(pw)
        try:
            context = browser.new_context()
            page = context.new_page()

            # First visit: seed localStorage with a stored dark theme.
            page.goto(base + "/", wait_until="domcontentloaded", timeout=10_000)
            page.evaluate(
                """({key, value}) => window.localStorage.setItem(key, value)""",
                {"key": "taxa.settings.theme", "value": json.dumps("dark")},
            )

            warnings: list[str] = []
            page.on(
                "console",
                lambda msg: warnings.append(msg.text)
                if msg.type in ("warning", "error")
                else None,
            )

            # Reload: rehydration cycle. The AppShell reads the typed
            # store inside `useEffect`, so the first paint ships the
            # SSR default (light) and the rehydration flips
            # `<html data-theme="dark">` post-mount.
            page.reload(wait_until="domcontentloaded", timeout=10_000)
            page.wait_for_timeout(500)

            data_theme = page.evaluate(
                "() => document.documentElement.dataset.theme || null"
            )
            offenders = [
                w for w in warnings
                if any(re.search(pat, w) for pat in HYDRATION_WARNING_PATTERNS)
            ]
            assert not offenders, (
                f"hydration warnings fired on rehydration: {offenders!r}\n"
                f"all warnings captured: {warnings!r}"
            )
            assert data_theme == "dark", (
                f"AppShell must stamp data-theme='dark' on <html> after "
                f"rehydrating localStorage.taxa.settings.theme='dark'; "
                f"got {data_theme!r}"
            )
        finally:
            browser.close()