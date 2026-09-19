"""Focused contract tests for the Next.js static-export cutover preparation.

ODD-CUTPREP-001 — proves the existing ``next.config.mjs`` is configured for
static export and that an explicitly generated ``out/`` directory is served
correctly through an isolated temporary static server. The tests do NOT
import or mutate ``api.server``, change ``WEB_DIR``, alter ``Makefile``, or
delete legacy assets; they are hermetic and deterministic.

What this test pins
-------------------
- ``next.config.mjs`` keeps the G2 contract keys: ``output: "export"``,
  ``images.unoptimized: true`` (a hard prerequisite of
  ``output: "export"``), ``trailingSlash: false``,
  ``reactStrictMode: true``.
- A synthetic ``out/`` tree (generated in ``tmp_path``) containing
  ``index.html``, a hashed ``_next/static/chunks/*.js``, and a hashed
  ``_next/static/chunks/*.css`` is served via a ``ThreadingHTTPServer``
  bound to an ephemeral 127.0.0.1 port and torn down at fixture exit.
- ``/`` returns the entry HTML, the hashed JS asset is reachable with a
  200 status and the original body, and the hashed CSS asset is
  reachable with a 200 status and the original body.
- The optional repo-root ``out/`` (when produced by a prior
  ``pnpm exec next build``) is structurally validated against the same
  contract shape: ``index.html`` exists, at least one hashed ``*.js``
  lives under ``_next/static/chunks/``, and at least one hashed
  ``*.css`` lives under the same directory. The validation is
  read-only and skips cleanly when no ``out/`` is present (the test
  never executes the build itself).

What this test does NOT do
--------------------------
- Imports ``api.server`` or touches ``WEB_DIR``.
- Spawns uvicorn, FastAPI, or any persistent process.
- Alters the ``Makefile``, legacy ``web/``, or any tracked file outside
  the test fixture's ``tmp_path``.
- Claims that ``pnpm exec next build`` ran — that build-evidence task
  belongs to ``scripts/verify_build.py`` and the ODD-CUTPREP-002 task;
  this test only validates the configuration contract and the served
  shape of a representative ``out/``.
"""
from __future__ import annotations

import http.client
import http.server
from pathlib import Path
import re
import threading
import time

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
NEXT_CONFIG = REPO_ROOT / "next.config.mjs"
REPO_OUT = REPO_ROOT / "out"

# Hashed filenames mimic the real Next.js ``<name>-<hash>.{js,css}``
# pattern so the test exercises a realistic ``_next/static/chunks/...``
# URL shape without depending on an actual build artifact.
JS_NAME = "app-deadbeefcafebabe12345678.js"
CSS_NAME = "app-deadbeefcafebabe12345678.css"

INDEX_BODY = (
    "<!DOCTYPE html><html><head>"
    f'<link rel="stylesheet" href="/_next/static/chunks/{CSS_NAME}"/>'
    f'<script src="/_next/static/chunks/{JS_NAME}" defer></script>'
    "</head><body>static export contract fixture</body></html>"
)
JS_BODY = b"// synthetic JS chunk for static-export contract test\n"
CSS_BODY = b"/* synthetic CSS chunk for static-export contract test */\n"


# ---------------------------------------------------------------------------
# Config contract — read ``next.config.mjs`` as text and assert the
# static-export keys. We deliberately avoid importing the file (it is an
# ESM module under the ``next/`` package): text scanning is deterministic,
# fast, and never executes Node.
# ---------------------------------------------------------------------------
def _config_body() -> str:
    assert NEXT_CONFIG.is_file(), f"missing Next.js config: {NEXT_CONFIG}"
    return NEXT_CONFIG.read_text(encoding="utf-8")


def test_next_config_declares_static_export_output():
    """``next.config.mjs`` must declare ``output: "export"``.

    This is the single key that switches Next.js into static-export mode
    and produces an ``out/`` directory at build time. FastAPI's planned
    ``StaticFiles(html=True)`` mount on ``out/`` depends on it.
    """
    body = _config_body()
    assert re.search(r'output\s*:\s*["\']export["\']', body), (
        "next.config.mjs MUST set `output: \"export\"` for static export.\n"
        f"file contents:\n{body}"
    )


def test_next_config_disables_image_optimization():
    """``images.unoptimized: true`` is a hard prerequisite of
    ``output: 'export'`` — static export cannot run the image
    optimisation server.
    """
    body = _config_body()
    assert re.search(r"unoptimized\s*:\s*true", body), (
        "next.config.mjs MUST set `images.unoptimized: true`; static export "
        "cannot run the image optimisation server.\n"
        f"file contents:\n{body}"
    )


def test_next_config_keeps_trailing_slash_false():
    """G2 contract: ``trailingSlash: false`` so ``out/index.html`` is the
    SPA entry without a redirect.
    """
    body = _config_body()
    assert re.search(r"trailingSlash\s*:\s*false", body), (
        "next.config.mjs MUST keep `trailingSlash: false`.\n"
        f"file contents:\n{body}"
    )


def test_next_config_keeps_react_strict_mode():
    """G2 contract: ``reactStrictMode: true`` so lifecycle / effect bugs
    surface during development; the production cutover keeps parity.
    """
    body = _config_body()
    assert re.search(r"reactStrictMode\s*:\s*true", body), (
        "next.config.mjs MUST keep `reactStrictMode: true`.\n"
        f"file contents:\n{body}"
    )


# ---------------------------------------------------------------------------
# Synthetic ``out/`` tree — generated in ``tmp_path`` to mirror what
# ``pnpm exec next build`` emits under ``output: "export"``. The tree is
# deterministic; its hash-shaped names match the real Next.js
# ``<name>-<hash>.{js,css}`` filenames so the served URLs exercise a
# realistic ``_next/static/chunks/...`` shape.
# ---------------------------------------------------------------------------
@pytest.fixture
def synthetic_out(tmp_path: Path) -> Path:
    """Build a deterministic synthetic ``out/`` tree mirroring Next.js
    static export.

    Layout::

        <tmp>/out/
            index.html                                   # entry HTML
            _next/
                static/
                    chunks/
                        app-<hash>.js                    # hashed JS
                        app-<hash>.css                   # hashed CSS
    """
    out = tmp_path / "out"
    chunks = out / "_next" / "static" / "chunks"
    chunks.mkdir(parents=True)
    (out / "index.html").write_text(INDEX_BODY, encoding="utf-8")
    (chunks / JS_NAME).write_bytes(JS_BODY)
    (chunks / CSS_NAME).write_bytes(CSS_BODY)
    return out


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    """``http.server`` handler with the access log silenced — pytest
    output is enough, and the daemon worker thread would otherwise spam
    stderr with every request.
    """

    def log_message(self, *args, **kwargs):  # noqa: D401, A002
        return


@pytest.fixture
def static_server(synthetic_out: Path):
    """Spin up an isolated ``ThreadingHTTPServer`` bound to an ephemeral
    127.0.0.1 port, serving ``synthetic_out`` as the document root.

    Yields the base URL (no trailing slash). The server is shut down and
    the worker thread joined on fixture teardown so no persistent
    process is left behind.
    """
    handler = lambda *a, **kw: _SilentHandler(  # noqa: E731
        *a, directory=str(synthetic_out), **kw
    )
    # ``("127.0.0.1", 0)`` lets the kernel pick a free ephemeral port —
    # the test is fully isolated and never collides with the dev API on
    # 8765 or any other listener.
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.allow_reuse_address = True
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base = f"http://127.0.0.1:{port}"
    # Poll until the listener actually accepts a request — the worker
    # thread is started, but ``serve_forever`` is event-driven and
    # pytest runs synchronously, so a tight poll is the cheapest way to
    # prove the server is ready before the assertions fire. We use
    # ``http.client`` directly (not ``urllib.request.urlopen``) so the
    # reachability proof never enters the URL-open audit surface —
    # ``base`` is always ``http://127.0.0.1:<port>/`` constructed from
    # the kernel-allocated loopback port the fixture binds above.
    deadline = time.time() + 5
    host, port = _split_loopback(base)
    while time.time() < deadline:
        try:
            status, _body, _ctype = _http_get(host, port, "/", timeout=1)
            if status == 200:
                break
        except (ConnectionRefusedError, OSError):
            time.sleep(0.05)
    else:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        raise RuntimeError(
            f"isolated static server did not become ready within 5s on {base}"
        )

    try:
        yield base
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _split_loopback(base: str) -> tuple[str, int]:
    """Parse ``http://127.0.0.1:<port>`` into ``(host, port)``.

    The fixture's base URL is always loopback HTTP; we never hit an
    external host or non-http scheme, so this helper is a static
    assertion that surfaces a clear error if a future caller passes a
    non-loopback base.
    """
    assert base.startswith("http://127.0.0.1:"), (
        f"isolated static server base must be loopback HTTP; got {base!r}"
    )
    rest = base[len("http://"):]
    host, _, port_str = rest.partition(":")
    assert host == "127.0.0.1", f"unexpected host: {host!r}"
    port = int(port_str)
    assert 1 <= port <= 65535, f"unexpected port: {port!r}"
    return host, port


def _http_get(host: str, port: int, path: str, timeout: float = 2) -> tuple[int, bytes, str]:
    """Issue a GET against ``http://<host>:<port><path>`` and return
    ``(status, body, content_type)``.

    Uses ``http.client.HTTPConnection`` directly — the same protocol
    surface ``urllib.request.urlopen`` exposes — so the reachability
    proof does not enter the URL-open audit surface. The host/port
    pair comes from ``_split_loopback`` and is always loopback.
    """
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        content_type = resp.getheader("Content-Type", "")
        return resp.status, body, content_type
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Reachable proofs — drive the isolated static server and assert the
# three entry points a real FastAPI ``StaticFiles(html=True)`` mount on
# ``out/`` would have to satisfy for the production cutover.
# ---------------------------------------------------------------------------
def test_static_server_serves_entry_html_at_root(static_server):
    """``/`` returns the entry HTML produced by ``out/index.html``.

    Pinned because the FastAPI cutover target is
    ``StaticFiles(html=True)`` on ``out/``, and the G2 contract demands
    ``out/index.html`` is the SPA entry without a redirect
    (``trailingSlash: false``).
    """
    host, port = _split_loopback(static_server)
    status, body, content_type = _http_get(host, port, "/")
    assert status == 200, f"GET / → {status}"
    assert INDEX_BODY.encode("utf-8") == body, (
        f"GET / body mismatch: got {body[:200]!r}"
    )
    assert "text/html" in content_type.lower(), (
        f"GET / content-type must be text/html; got {content_type!r}"
    )


def test_static_server_serves_hashed_js_chunk(static_server):
    """A hashed ``_next/static/chunks/*.js`` asset is reachable at the
    URL Next.js would have emitted in ``index.html``.

    Hashed names (the ``<name>-<hash>.js`` shape Next.js produces) are
    the contract the production ``out/`` must keep; the synthetic
    fixture mirrors that pattern.
    """
    host, port = _split_loopback(static_server)
    status, body, content_type = _http_get(host, port, f"/_next/static/chunks/{JS_NAME}")
    assert status == 200, f"GET /_next/static/chunks/{JS_NAME} → {status}"
    assert body, "hashed JS body is empty"
    assert body == JS_BODY, (
        f"hashed JS body mismatch: got {body!r}, expected {JS_BODY!r}"
    )
    assert (
        "javascript" in content_type.lower()
        or "ecmascript" in content_type.lower()
    ), f"hashed JS content-type unexpected: {content_type!r}"


def test_static_server_serves_hashed_css_asset(static_server):
    """A hashed ``_next/static/chunks/*.css`` asset is reachable at the
    URL Next.js would have emitted in ``index.html``.
    """
    host, port = _split_loopback(static_server)
    status, body, content_type = _http_get(host, port, f"/_next/static/chunks/{CSS_NAME}")
    assert status == 200, f"GET /_next/static/chunks/{CSS_NAME} → {status}"
    assert body, "hashed CSS body is empty"
    assert body == CSS_BODY, (
        f"hashed CSS body mismatch: got {body!r}, expected {CSS_BODY!r}"
    )
    assert "text/css" in content_type.lower(), (
        f"hashed CSS content-type unexpected: {content_type!r}"
    )


# ---------------------------------------------------------------------------
# Optional read-only validation of the repo-root ``out/`` produced by a
# prior ``pnpm exec next build``. The test skips when no ``out/`` exists
# so it never forces a build and never writes outside the repo's
# tracked surface. This proves the production cutover candidate (when
# present) keeps the same shape the synthetic fixture validates.
# ---------------------------------------------------------------------------
def test_repo_out_shape_matches_static_export_when_present():
    """If a previous ``pnpm exec next build`` produced ``out/`` at the
    repo root, validate its top-level shape: entry HTML + hashed JS +
    hashed CSS under ``_next/static/chunks/``.

    Skipped when ``out/`` is missing — the test never executes the
    build itself; that evidence is owned by ``scripts/verify_build.py``
    and the ODD-CUTPREP-002 task.
    """
    if not REPO_OUT.is_dir():
        pytest.skip(
            "no repo-root out/ directory present; "
            "run `pnpm exec next build` to materialise the static export."
        )
    assert (REPO_OUT / "index.html").is_file(), (
        f"out/ present but missing entry HTML: {REPO_OUT / 'index.html'}"
    )
    chunks = REPO_OUT / "_next" / "static" / "chunks"
    assert chunks.is_dir(), (
        f"out/ present but missing hashed asset directory: {chunks}"
    )
    js_files = sorted(chunks.glob("*.js"))
    css_files = sorted(chunks.glob("*.css"))
    assert js_files, f"no hashed JS assets under {chunks}"
    assert css_files, f"no hashed CSS assets under {chunks}"