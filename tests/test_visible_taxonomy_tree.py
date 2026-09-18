"""Visible taxonomy tree contract tests (ODD-VTREE-002).

Pins the React cutover's first usable tree surface:
  - AppShell (server component) renders header + main + footer
  - TaxonomyTree ('use client') renders collapsed root rows on mount
  - TreeRow renders disclosure buttons with accurate ``aria-expanded``
  - Initial loading / error / empty states are accessible
  - The static export's ``out/index.html`` carries the SSR markup

The build-witness fixture (``built_index_html``) reuses the
``next build`` side-effect from ``test_app_shell_render.py`` when run
in the same session. When run alone the test runs its own
``next build`` to refresh ``out/``.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_SHELL_FILE = REPO_ROOT / "src" / "modules" / "app-shell" / "presentation" / "AppShell.tsx"
APP_SHELL_BARREL = REPO_ROOT / "src" / "modules" / "app-shell" / "index.ts"
TAXONOMY_TREE_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "TaxonomyTree.tsx"
TAXONOMY_TREE_ROW_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "presentation" / "TreeRow.tsx"
TAXONOMY_BARREL = REPO_ROOT / "src" / "modules" / "taxonomy" / "index.ts"
TAXONOMY_DOMAIN_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "domain" / "taxon.ts"
TAXONOMY_INFRA_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "infrastructure" / "api.ts"
SRC_PAGE = REPO_ROOT / "src" / "app" / "page.tsx"
SRC_LAYOUT = REPO_ROOT / "src" / "app" / "layout.tsx"
OUT_DIR = REPO_ROOT / "out"
OUT_INDEX = OUT_DIR / "index.html"


def _read_text(path: Path) -> str:
    if not path.is_file():
        pytest.fail(f"required file missing: {path}")
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# File presence + extension (RED gates for ODD-VTREE-002)
# ---------------------------------------------------------------------------

def test_app_shell_file_exists() -> None:
    assert APP_SHELL_FILE.is_file(), (
        f"missing {APP_SHELL_FILE} — ODD-VTREE-002 ships this server component."
    )
    assert APP_SHELL_FILE.suffix == ".tsx", "AppShell must be `.tsx`."


def test_app_shell_barrel_reexports_app_shell() -> None:
    text = _read_text(APP_SHELL_BARREL)
    assert re.search(r'export\s*\{[^}]*default\s+as\s+AppShell[^}]*\}\s*from', text, re.DOTALL), (
        "app-shell barrel must re-export `AppShell` as the default export"
    )
    assert re.search(r'export\s+type\s*\{\s*AppShellProps\s*\}', text), (
        "app-shell barrel must re-export `AppShellProps`"
    )


def test_taxonomy_tree_file_exists() -> None:
    assert TAXONOMY_TREE_FILE.is_file(), (
        f"missing {TAXONOMY_TREE_FILE} — ODD-VTREE-002 ships this client island."
    )
    assert TAXONOMY_TREE_FILE.suffix == ".tsx", "TaxonomyTree must be `.tsx`."


def test_tree_row_file_exists() -> None:
    assert TAXONOMY_TREE_ROW_FILE.is_file(), (
        f"missing {TAXONOMY_TREE_ROW_FILE} — ODD-VTREE-002 ships this row component."
    )
    assert TAXONOMY_TREE_ROW_FILE.suffix == ".tsx", "TreeRow must be `.tsx`."


def test_taxonomy_barrel_reexports_taxonomy_tree() -> None:
    text = _read_text(TAXONOMY_BARREL)
    assert re.search(r'export\s*\{[^}]*default\s+as\s+TaxonomyTree[^}]*\}\s*from', text, re.DOTALL), (
        "taxonomy barrel must re-export `TaxonomyTree` as the default export"
    )


# ---------------------------------------------------------------------------
# Source contracts (server vs client boundary, dependencies, accessibility)
# ---------------------------------------------------------------------------

def test_taxonomy_tree_is_a_client_component() -> None:
    text = _read_text(TAXONOMY_TREE_FILE)
    assert text.lstrip().startswith('"use client"') or text.lstrip().startswith("'use client'"), (
        "TaxonomyTree.tsx must declare the client boundary via 'use client'"
    )


def test_app_shell_is_a_server_component() -> None:
    """AppShell must NOT carry 'use client' — the brief mandates a server-component shell."""
    text = _read_text(APP_SHELL_FILE)
    assert "use client" not in text, (
        "AppShell.tsx is a server component; it MUST NOT carry the 'use client' directive"
    )


def test_app_shell_depends_only_on_react_types() -> None:
    """AppShell imports only React types per spec.md rule 4 (presentation purity)."""
    text = _read_text(APP_SHELL_FILE)
    for src in re.findall(r'from\s+["\']([^"\']+)["\']', text):
        assert src == "react", (
            f"AppShell.tsx must import only from 'react'; got {src!r}"
        )


def test_taxonomy_tree_uses_canonical_helpers_via_barrel() -> None:
    """ODD-VTREE-002 correction: TaxonomyTree consumes the canonical
    typed helpers (``fetchDomains``, ``fetchChildren``,
    ``TaxonomyApiError``) re-exported by the public
    ``@taxa/taxonomy`` barrel — never deep paths into the
    infrastructure layer. spec.md rule 5 forbids deep imports via the
    ESLint ``no-restricted-imports`` guard; rule 4 keeps the
    presentation layer free of duplicated wire projection.
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "fetchDomains" in text, (
        "TaxonomyTree.tsx must call the canonical fetchDomains helper"
    )
    assert "fetchChildren" in text, (
        "TaxonomyTree.tsx must call the canonical fetchChildren helper"
    )
    assert "from \"@taxa/taxonomy\"" in text or "from '@taxa/taxonomy'" in text, (
        "TaxonomyTree.tsx must import the helpers via the @taxa/taxonomy barrel"
    )
    # spec.md rule 5 + ESLint guard: no deep imports into the layer folders.
    for bad in (
        "../infrastructure/api",
        "../infrastructure/api.js",
        "@taxa/taxonomy/infrastructure",
        "@taxa/taxonomy/domain",
    ):
        assert bad not in text, (
            f"TaxonomyTree.tsx must not deep-import {bad!r} (rule 5 barrel guard)"
        )


def test_taxonomy_tree_uses_configured_api_origin() -> None:
    """ODD-VTREE-002 binding: production requests stay
    relative/same-origin (``process.env.NEXT_PUBLIC_TAXA_API_ORIGIN ?? ""``),
    while local development overrides the variable via
    ``pnpm run dev:local`` (see package.json).
    """
    text = _read_text(TAXONOMY_TREE_FILE)
    assert "process.env.NEXT_PUBLIC_TAXA_API_ORIGIN" in text, (
        "TaxonomyTree.tsx must source its API origin from NEXT_PUBLIC_TAXA_API_ORIGIN"
    )
    assert re.search(r'NEXT_PUBLIC_TAXA_API_ORIGIN\s*\?\?\s*["\']["\']', text), (
        "TaxonomyTree.tsx must default the origin to an empty string when unset"
    )


def test_taxonomy_tree_emits_accessible_initial_states() -> None:
    """ODD-VTREE-002: initial loading (`role=status`), initial error
    (`role=alert` + Retry), and empty roots are all rendered."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # At least one `role="status"` covers loading + empty + per-row loading.
    assert text.count('role="status"') >= 2, (
        "TaxonomyTree.tsx must emit role=\"status\" for loading + empty states"
    )
    # Initial error uses `role="alert"` with a Retry button.
    assert text.count('role="alert"') >= 1, (
        "TaxonomyTree.tsx must emit role=\"alert\" for the initial error state"
    )
    assert re.search(r'>\s*Retry\s*<', text), (
        "TaxonomyTree.tsx must render a Retry button"
    )


def test_tree_row_uses_semantic_disclosure_button() -> None:
    """TreeRow must use a `<button>` with accurate ``aria-expanded`` for the
    disclosure control. ``aria-controls`` is intentionally OMITTED — children
    render as flat siblings of this row (so there is no single hidden DOM
    target to point at); pointing ``aria-controls`` at an empty hidden
    ``rowgroup`` would misrepresent the disclosure relationship to assistive
    tech. The button is ``disabled`` for leaves and ``aria-expanded`` is
    only emitted on expandable rows."""
    text = _read_text(TAXONOMY_TREE_ROW_FILE)
    assert re.search(r'<button\b[^>]*aria-expanded', text, re.DOTALL), (
        "TreeRow.tsx must render a <button> with aria-expanded"
    )
    # Look for the *attribute* (aria-controls=...), not the docstring word.
    assert re.search(r'\baria-controls\s*=', text) is None, (
        "TreeRow.tsx must NOT carry the aria-controls attribute "
        "(children are flat siblings, not a hidden target)"
    )
    assert "display: none" not in text and "display:none" not in text, (
        "TreeRow.tsx must not ship a hidden rowgroup (invalid a11y plumbing)"
    )


def test_tree_row_initial_state_is_collapsed() -> None:
    """ODD-VTREE-002 acceptance: root rows render collapsed initially
    (the tree fetches roots, but does not auto-expand any)."""
    text = _read_text(TAXONOMY_TREE_FILE)
    # The tree initializes with EMPTY_TREE_STATE; the expandedIds Set is
    # only populated by toggleExpand. No auto-expand on fetch.
    assert "EMPTY_TREE_STATE" in text, (
        "TaxonomyTree.tsx must initialize with EMPTY_TREE_STATE (collapsed)"
    )
    assert "expand(" not in text.replace("toggleExpand(", "").replace("isExpanded(", ""), (
        "TaxonomyTree.tsx must not auto-expand; the only mutator is toggleExpand"
    )


# ---------------------------------------------------------------------------
# Build witness — static export carries the visible shell + tree SSR
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def static_export() -> None:
    """Run ``next build`` once per module and assert ``out/index.html`` exists."""
    if not (REPO_ROOT / "node_modules" / ".bin" / "next").is_file() and shutil.which("next") is None:
        pytest.skip("next binary not installed — skip build witness during RED")
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


def test_out_index_html_has_app_shell_landmarks(static_export):
    html = _read_text(OUT_INDEX)
    for tag in ("<header", "<main", "<footer"):
        assert tag in html, (
            f"out/index.html must contain {tag} (AppShell frame); ODD-VTREE-002 server shell"
        )


def test_out_index_html_has_visible_product_title(static_export):
    html = _read_text(OUT_INDEX)
    assert re.search(r"<h1[^>]*>Taxonomic Tree</h1>", html), (
        "out/index.html must render the visible <h1>Taxonomic Tree</h1>"
    )


def test_out_index_html_has_taxonomy_tree_section(static_export):
    html = _read_text(OUT_INDEX)
    assert 'aria-label="Taxonomic tree"' in html, (
        "out/index.html must mount the TaxonomyTree section with aria-label"
    )
    assert "taxa-tree" in html, (
        "out/index.html must include the four-column .taxa-tree grid"
    )


def test_out_index_html_renders_initial_loading_status(static_export):
    """SSR with EMPTY_TREE_STATE must show the `role=status` loading copy
    (the client then fetches roots after hydration)."""
    html = _read_text(OUT_INDEX)
    assert re.search(r'role="status"[^>]*>\s*Loading domains', html, re.DOTALL), (
        "out/index.html must render the role=\"status\" loading copy before hydration"
    )


def test_out_index_html_does_not_inline_domain_rows_before_hydration(static_export):
    """The fetch is client-side; SSR must not pre-render domain rows.
    Confirms the root-collapsed-initial-state contract."""
    html = _read_text(OUT_INDEX)
    # No `data-taxon-id` attributes before hydration means no rows inlined.
    assert "data-taxon-id" not in html, (
        "out/index.html must NOT inline taxon rows before hydration (collapsed initial state)"
    )


def test_out_index_html_keeps_static_origin(static_export):
    """Production requests must stay relative/same-origin (PR 3b's
    hydration-safety contract carries forward). The
    ``data-theme`` hydration-guard assertion lives in
    ``test_app_shell_render.py::test_out_index_html_body_has_no_data_theme_before_hydration``
    — duplicated coverage is removed here per the ODD-VTREE-002
    test-scope reduction."""
    html = _read_text(OUT_INDEX)
    # Footer copy mentions the API origin.
    assert re.search(r"<code[^>]*>\s*/api\s*</code>", html), (
        "out/index.html must render the /api origin footer marker"
    )
    # No literal 'http://' or 'https://' API reference in the static HTML.
    assert re.search(r'href=["\']https?://[^"\']*domains', html) is None, (
        "out/index.html must not reference absolute /api/domains URLs"
    )
