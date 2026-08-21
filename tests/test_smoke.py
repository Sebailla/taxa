"""
Smoke tests that don't require the taxa.db to be present.

Run:
    pytest tests/

These cover the parts of the API and static frontend that work without a
populated DB: the root redirect, the Swagger UI, the OpenAPI schema, and
the static asset mount. The DB-backed endpoints (/api/health,
/api/domains, etc.) are exercised separately by `make test` against a
locally running server.
"""
from __future__ import annotations

from fastapi.testclient import TestClient  # type: ignore[import-not-found]

from api.server import app  # type: ignore[import-not-found]


client = TestClient(app)


def test_root_serves_index_html():
    """GET / serves web/index.html (or redirects to /docs if web/ is empty).

    The root handler at server.py:53 has include_in_schema=False, so it's
    not part of the OpenAPI contract — it's a legacy fallback that the
    StaticFiles mount overrides in production.
    """
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (200, 307, 308)
    if resp.status_code in (307, 308):
        assert resp.headers["location"] == "/docs"
    else:
        # web/index.html was served directly.
        assert "<html" in resp.text or "<title>" in resp.text


def test_docs_serves_swagger_ui():
    """/docs is FastAPI's auto-generated Swagger UI."""
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "swagger" in resp.text.lower()


def test_openapi_schema_is_valid_json():
    """/openapi.json must be a valid OpenAPI 3.x schema."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["openapi"].startswith("3.")
    # The API exposes these paths — guard against accidental route removal.
    expected_paths = {
        # The "/" handler is intentionally excluded from the schema
        # (include_in_schema=False at server.py:53), so it's not asserted here.
        "/api/health",
        "/api/domains",
        "/api/taxon/{taxon_id}",
        "/api/taxon/{taxon_id}/children",
        "/api/taxon/{taxon_id}/vernaculars",
        "/api/taxon/{taxon_id}/synonyms",
        "/api/taxon/{taxon_id}/distribution",
        "/api/search",
    }
    assert expected_paths.issubset(set(schema["paths"].keys())), (
        f"missing routes: {expected_paths - set(schema['paths'].keys())}"
    )


def test_static_index_html_served():
    """The web/ directory is mounted as static files at root."""
    resp = client.get("/index.html")
    assert resp.status_code == 200
    assert "<title>" in resp.text or "<html" in resp.text


def test_static_app_js_served():
    """Frontend bundle is reachable from the same origin."""
    resp = client.get("/app.js")
    assert resp.status_code == 200
    assert len(resp.text) > 1000, "app.js looks suspiciously small"


def test_health_endpoint_returns_503_without_db():
    """
    Without taxa.db present, /api/health should return 503 with a clear
    message - not 500 or a crash. This is the expected behaviour for a
    fresh checkout before ETL has run.
    """
    resp = client.get("/api/health")
    assert resp.status_code in (200, 503)
    if resp.status_code == 503:
        assert "taxa.db" in resp.text or "ETL" in resp.text
