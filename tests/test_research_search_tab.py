"""Phase 5b.4 research SearchTab + SearchLinkList contract tests.

Pins 5b.4:
  - `src/modules/research/presentation/SearchTab.tsx` renders the five
    category sections in fixed order: General → Taxonomic → Academic
    → Multimedia → Documents.
  - `SearchTab` consumes `SearchLinkList` for the anchor rendering
    (one presenter, reused per category).
  - `src/modules/research/presentation/SearchLinkList.tsx` maps each
    `Engine` (from `SEARCH_ENGINES`) to an anchor carrying
    `target="_blank"` + `rel="noopener noreferrer"` (security contract).
  - Decision #4: SearchTab resolves links ONLY from `SEARCH_ENGINES`
    — no inline list, no local ad-hoc engines, no fallback hard-codes.
  - URL template tokens `{name}` and `{auth}` MUST be replaced; engines
    with `with_authorship: true` and a present `authorship` use
    `template_with_auth`, otherwise the plain `template`.
  - Public barrel (`presentation/index.ts`) re-exports both surfaces.
  - Root barrel (`research/index.ts`) keeps `export * from "./presentation"`.

No CSS, no new dependencies, no app-shell / commit / push.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
R = REPO / "src" / "modules" / "research"
PRES = R / "presentation"
SEARCH_TAB = PRES / "SearchTab.tsx"
SEARCH_LINK_LIST = PRES / "SearchLinkList.tsx"
PRES_INDEX = PRES / "index.ts"
ROOT = R / "index.ts"


def read(rel: str) -> str:
    p = R / rel
    assert p.is_file(), f"missing research file: {p}"
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# File presence
# ---------------------------------------------------------------------------
def test_files_present() -> None:
    """Both 5b.4 components must land on disk."""
    assert SEARCH_TAB.is_file(), (
        f"missing {SEARCH_TAB.relative_to(REPO)} (PR 5b.4 SearchTab body)"
    )
    assert SEARCH_LINK_LIST.is_file(), (
        f"missing {SEARCH_LINK_LIST.relative_to(REPO)} (PR 5b.4 SearchLinkList)"
    )


# ---------------------------------------------------------------------------
# SearchTab — five sections in fixed order, consumes SearchLinkList
# ---------------------------------------------------------------------------
def test_search_tab_renders_five_category_sections_in_order() -> None:
    """The SearchTab MUST render one `.search-category-section` per
    category, in the canonical order (General / Taxonomic / Academic /
    Multimedia / Documents) — matching the legacy `web/search_urls.js`
    `CATEGORIES` ordering. The five labels MUST appear in the source
    in that exact order (descendant text check, not the CATEGORIES
    import — the test is order-sensitive)."""
    src = read("presentation/SearchTab.tsx")
    for label in ("General", "Taxonomic", "Academic", "Multimedia", "Documents"):
        assert label in src, (
            f"SearchTab must render category label {label!r}"
        )
    # Order check — every label must appear before the next, in source
    # code order.
    indices = [src.find(label) for label in
               ("General", "Taxonomic", "Academic", "Multimedia", "Documents")]
    assert all(idx >= 0 for idx in indices), (
        f"every category label must appear; got indices {indices!r}"
    )
    assert indices == sorted(indices), (
        f"category labels must appear in fixed order "
        f"General → Taxonomic → Academic → Multimedia → Documents; "
        f"got indices {indices!r}"
    )


def test_search_tab_emits_search_category_section_class() -> None:
    """Per the 3c-c `@layer components` selectors, each section MUST
    stamp `.search-category-section` so the existing production CSS
    styles the section (the rule rides on the direct-child combinator:
    `.search-tab > .search-category-section`)."""
    src = read("presentation/SearchTab.tsx")
    assert "search-category-section" in src, (
        "SearchTab must stamp `.search-category-section` on each section"
    )


def test_search_tab_uses_search_link_list() -> None:
    """SearchTab MUST delegate the anchor rendering to `SearchLinkList`
    (the single presenter). The category section MUST contain a
    `<SearchLinkList>` reference, NOT inline anchors."""
    src = read("presentation/SearchTab.tsx")
    assert "SearchLinkList" in src, (
        "SearchTab must compose <SearchLinkList> rather than inline anchors"
    )
    # SearchTab MUST NOT render raw `<a>` tags — the only anchor
    # surface in the module is the one in SearchLinkList.
    assert not re.search(r"<a\b", src), (
        "SearchTab must not inline raw `<a>` tags — "
        "delegate anchor rendering to SearchLinkList"
    )


def test_search_tab_consumes_search_engines_via_barrel() -> None:
    """Decision #4: SearchTab resolves links ONLY from `SEARCH_ENGINES`.
    It MUST import `SEARCH_ENGINES` from `@taxa/research` (the public
    barrel that re-exports the canonical catalog from
    `src/data/search-engines.js`). NO inline list, NO local hard-codes."""
    src = read("presentation/SearchTab.tsx")
    assert re.search(
        r'from\s+["\']@taxa/research["\']', src,
    ), "SearchTab must import from `@taxa/research` (barrel contract)"
    assert "SEARCH_ENGINES" in src, (
        "SearchTab must consume `SEARCH_ENGINES` from the research barrel"
    )


def test_search_tab_uses_search_tab_class() -> None:
    """SearchTab MUST ride the production `.search-tab` class
    (3c-c pinned the `@layer components` selectors on this class)."""
    src = read("presentation/SearchTab.tsx")
    assert "search-tab" in src, (
        "SearchTab must render the `.search-tab` wrapper class"
    )


# ---------------------------------------------------------------------------
# SearchLinkList — anchors with target + rel security contract
# ---------------------------------------------------------------------------
def test_search_link_list_renders_target_blank() -> None:
    """Every link rendered by SearchLinkList MUST carry
    `target="_blank"` so external searches open in a new tab
    (WCAG 2.2 AA: announce the new-tab behaviour + security)."""
    src = read("presentation/SearchLinkList.tsx")
    assert 'target="_blank"' in src, (
        "SearchLinkList must stamp `target=\"_blank\"` on every anchor"
    )


def test_search_link_list_renders_rel_noopener_noreferrer() -> None:
    """Every link MUST carry `rel="noopener noreferrer"` — the security
    contract that prevents the new tab from accessing
    `window.opener` and leaking the referrer URL."""
    src = read("presentation/SearchLinkList.tsx")
    assert 'rel="noopener noreferrer"' in src, (
        "SearchLinkList must stamp `rel=\"noopener noreferrer\"` on every anchor"
    )


def test_search_link_list_stamps_search_link_class() -> None:
    """Per the 3c-c selectors, every anchor MUST stamp `.search-link`
    so the production CSS grid lays them out as cards."""
    src = read("presentation/SearchLinkList.tsx")
    assert "search-link" in src, (
        "SearchLinkList must stamp `.search-link` on every anchor"
    )


def test_search_link_list_resolves_template_tokens() -> None:
    """The link presenter MUST resolve `{name}` (and `{auth}` when the
    engine has `with_authorship: true` and an authorship string is
    supplied) so the rendered URL never contains a literal
    `{name}` or `{auth}` token. Pins the URL-builder pure helper."""
    src = read("presentation/SearchLinkList.tsx")
    # The presenter must reference both tokens (encode, replace, etc.).
    assert "{name}" in src or "name" in src, (
        "SearchLinkList must reference the `{name}` template token"
    )
    # No unresolved `{name}` token must leak into the rendered href —
    # the resolver helper strips it.
    bad = re.search(r"href=[\s\S]{0,200}\{[ ]*name[ ]*\}", src)
    assert bad is None, (
        f"SearchLinkList must not leave a raw `{{name}}` in any "
        f"`href=` attribute; got {bad.group(0)!r}"
    )


def test_search_link_list_does_not_inline_engines() -> None:
    """Decision #4: SearchLinkList receives its `engines` from the
    caller (SearchTab). It MUST NOT declare its own hard-coded engine
    list — the search-engines catalog lives at `src/data/search-engines.js`
    and is reached via `@taxa/research`."""
    src = read("presentation/SearchLinkList.tsx")
    # The presenter must accept an `engines` prop and iterate it.
    assert re.search(r"\bengines\b", src), (
        "SearchLinkList must accept an `engines` prop"
    )


# ---------------------------------------------------------------------------
# Barrels — both surfaces reachable via @taxa/research
# ---------------------------------------------------------------------------
def test_presentation_barrel_reexports_search_surfaces() -> None:
    """`presentation/index.ts` MUST re-export both `SearchTab` and
    `SearchLinkList` so the DetailPanel can import via `@taxa/research`
    (5a.3 wired DetailPanel to the local taxonomy stubs; 5b.4 swaps
    the stubs for the real search bodies via the same barrel path)."""
    src = read("presentation/index.ts")
    for tok in ("SearchTab", "SearchLinkList"):
        assert tok in src, (
            f"presentation/index.ts must re-export {tok!r}"
        )


def test_root_barrel_keeps_presentation_surface() -> None:
    """Root barrel keeps `export * from "./presentation"` — the 5b.3
    addendum is preserved and the new SearchTab / SearchLinkList ride
    through it."""
    src = read("index.ts")
    assert re.search(
        r'export\s*\*\s+from\s+["\']\./presentation["\']', src,
    ), 'research/index.ts must keep `export * from "./presentation"`'


# ---------------------------------------------------------------------------
# Behaviour-level driver — exercise SearchLinkList's URL resolver via Node.
# The driver validates the *actual* function body, not just text presence.
# ---------------------------------------------------------------------------
_DRIVER_JS = """\
import { resolveSearchLink } from "./link-bundle.ts";
const engines = [
  { key: "google", template: "https://www.google.com/search?q={name}",
    template_with_auth: null, with_authorship: false, category: "general" },
  { key: "scholar", template: "https://scholar.google.com/scholar?q={name}",
    template_with_auth: "https://scholar.google.com/scholar?q={name}+{auth}",
    with_authorship: true, category: "academic" },
];
const noAuth = resolveSearchLink(engines[0], "Animalia", null);
const withAuth = resolveSearchLink(engines[1], "Animalia", "Linnaeus, 1758");
const withAuthEmpty = resolveSearchLink(engines[1], "Animalia", null);
const out = {
  noAuth, withAuth, withAuthEmpty,
};
console.log(JSON.stringify(out));
"""


def _run_driver() -> dict:
    d = tempfile.mkdtemp(prefix="taxa-search-")
    try:
        # Inline the SearchLinkList into the tmp dir. The driver
        # uses Node's --experimental-strip-types which only handles
        # TypeScript syntax — JSX is rejected. We extract ONLY the
        # `resolveSearchLink` function (the pure URL resolver) into a
        # separate `.ts` file the driver imports. The JSX surface
        # stays in the production source; the driver does not touch
        # it.
        src_text = SEARCH_LINK_LIST.read_text(encoding="utf-8")
        # Find the `export function resolveSearchLink` block — depth-scan
        # braces to find the matching close.
        m = re.search(r"\bexport\s+function\s+resolveSearchLink\s*\(", src_text)
        assert m is not None, (
            "SearchLinkList.tsx must export `resolveSearchLink`"
        )
        sig_end = src_text.find("{", m.end())
        depth, cursor = 1, sig_end + 1
        while cursor < len(src_text) and depth > 0:
            ch = src_text[cursor]
            if ch == "{": depth += 1
            elif ch == "}": depth -= 1
            cursor += 1
        resolver_body = src_text[m.start():cursor]
        # The resolver imports `Engine` from `@taxa/research`. Replace
        # the deep alias with a local stub the driver provides.
        stub = (
            "export type Engine = {\n"
            "  key: string; label: string; template: string;\n"
            "  template_with_auth: string | null;\n"
            "  with_authorship: boolean; icon: string; category: string;\n"
            "};\n"
        )
        (Path(d) / "engine-stub.ts").write_text(stub, encoding="utf-8")
        # Write the resolver body — it references the `Engine` type via
        # the `@taxa/research` alias. Strip the import line; the resolver
        # uses `Engine` only as a type annotation, and TS-strip-types
        # ignores types.
        resolver_body_no_import = re.sub(
            r'^\s*import\s+[^;]+;\s*\n', '', resolver_body, flags=re.MULTILINE,
        )
        (Path(d) / "link-list.ts").write_text(
            resolver_body_no_import, encoding="utf-8",
        )
        bundle = "export { resolveSearchLink } from \"./link-list.ts\";\n"
        (Path(d) / "link-bundle.ts").write_text(bundle, encoding="utf-8")
        (Path(d) / "d.mjs").write_text(_DRIVER_JS, encoding="utf-8")
        proc = subprocess.run(
            ["node", "--experimental-strip-types", f"{d}/d.mjs"],
            capture_output=True, text=True,
            env=dict(os.environ, NODE_NO_WARNINGS="1"), timeout=15,
        )
        assert proc.returncode == 0, (
            f"node driver rc={proc.returncode} stderr={proc.stderr[-400:]}"
        )
        return json.loads(proc.stdout.strip())
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def driver_output() -> dict:
    if not shutil.which("node"):
        pytest.skip("node required for runtime harness")
    return _run_driver()


def test_resolve_search_link_drops_name_token(driver_output: dict) -> None:
    """The resolver MUST drop the `{name}` token from the rendered URL."""
    o = driver_output
    assert "{name}" not in o["noAuth"], (
        f"`{{name}}` must be replaced; got {o['noAuth']!r}"
    )
    assert "Animalia" in o["noAuth"], (
        f"`Animalia` must be inserted in place of `{{name}}`; "
        f"got {o['noAuth']!r}"
    )


def test_resolve_search_link_uses_auth_template_when_available(
    driver_output: dict,
) -> None:
    """When `with_authorship: true` AND `auth` is non-empty, the resolver
    MUST use `template_with_auth` and drop BOTH tokens. The plain
    `template` would leak the `{auth}` token, which is wrong."""
    o = driver_output
    assert "{name}" not in o["withAuth"], (
        f"`{{name}}` must be replaced; got {o['withAuth']!r}"
    )
    assert "{auth}" not in o["withAuth"], (
        f"`{{auth}}` must be replaced when authorship is present; "
        f"got {o['withAuth']!r}"
    )
    assert "Animalia" in o["withAuth"] and "Linnaeus" in o["withAuth"], (
        f"both tokens must be substituted; got {o['withAuth']!r}"
    )


def test_resolve_search_link_falls_back_to_plain_when_auth_missing(
    driver_output: dict,
) -> None:
    """When `auth` is null/empty the resolver MUST fall back to the
    plain `template` (and drop `{name}` only). Otherwise the link
    would 404 on a literal `{auth}` token."""
    o = driver_output
    assert "{name}" not in o["withAuthEmpty"], (
        f"`{{name}}` must be replaced; got {o['withAuthEmpty']!r}"
    )
    assert "{auth}" not in o["withAuthEmpty"], (
        f"`{{auth}}` must NOT leak when authorship is missing; "
        f"got {o['withAuthEmpty']!r}"
    )