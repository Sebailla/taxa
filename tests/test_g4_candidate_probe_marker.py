"""G4 candidate probe-marker contract — approved issue #245.

The G4 capture tooling (see ``tests/fixtures/g4/corpus/manifest.json``
and ``scripts/orchestrate_g5_legacy.py``) requires every built candidate
page to expose an element carrying ``data-testid="g4-probe-marker"`` so
the capture producer's pre-runner DOM-marker gate can locate it. The
marker MUST be static and hydration-safe — neither the SSR output nor
the client re-render may diverge or React will warn. It MUST NOT change
visible layout, focus order, or accessible content.

This module pins the SOURCE-LEVEL contract for ``src/app/layout.tsx``.
Hermetic — does not invoke ``next build``. The build-witness version of
this contract (an assertion against ``out/index.html``) lands with the
dependent #246 follow-up so this slice stays scoped to the
source-level contract review.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_LAYOUT = REPO_ROOT / "src" / "app" / "layout.tsx"

# Exact probe-marker test-id the G4 capture manifest pins in
# ``tests/fixtures/g4/corpus/manifest.json`` and in
# ``scripts/orchestrate_g5_legacy.py::_synthesize_manifest_snapshot``.
PROBE_MARKER_TESTID = "g4-probe-marker"

# Matches a `<TAG ... data-testid="g4-probe-marker" ...>` opening tag,
# capturing: 1=tag name, 2=attributes before ``data-testid``, 3=attrs
# after, 4=self-closing slash. Handles attributes on either side of
# ``data-testid`` and both quote styles. A self-closing slash is
# optional so paired tags are matched too.
_MARKER_TAG_RE = re.compile(
    r"<([A-Za-z][A-Za-z0-9]*)((?:[^>]*?))\bdata-testid\s*=\s*"
    r"[\"']" + re.escape(PROBE_MARKER_TESTID) + r"[\"']((?:[^>]*?))(/)?\s*>",
    re.DOTALL,
)


def _read_layout() -> str:
    if not SRC_LAYOUT.is_file():
        pytest.fail(f"missing {SRC_LAYOUT}")
    return SRC_LAYOUT.read_text(encoding="utf-8")


def _find_marker_opening_tag(text: str) -> tuple[str, str]:
    """Return ``(element_text, tag_name)`` for the probe-marker opening
    tag, or ``pytest.fail`` if no such element exists. The returned
    ``element_text`` includes the surrounding ``<...>`` characters."""
    match = _MARKER_TAG_RE.search(text)
    assert match is not None, (
        f"src/app/layout.tsx MUST author a JSX element with "
        f"data-testid={PROBE_MARKER_TESTID!r}. The G4 capture "
        f"manifest pins the test-id; without it the capture producer "
        f"fails closed."
    )
    tag = match.group(1)
    element_text = match.group(0)
    return element_text, tag


# ---------------------------------------------------------------------------
# Source presence (RED gate)
# ---------------------------------------------------------------------------

def test_layout_exists() -> None:
    assert SRC_LAYOUT.is_file(), (
        f"missing {SRC_LAYOUT.relative_to(REPO_ROOT)} — the App Router "
        f"root layout is the agreed authoring surface for the G4 "
        f"candidate probe marker (issue #245)."
    )


def test_layout_authored_an_element_with_probe_marker_testid() -> None:
    """The App Router root layout MUST author at least one JSX element
    whose ``data-testid`` attribute is exactly ``"g4-probe-marker"``.
    The attribute MUST be a string literal — no expression, no
    ``{...}`` interpolation, no symbol. A dynamic value would break
    the G4 capture producer's pre-runner DOM-marker gate."""
    text = _read_layout()
    pattern = re.compile(
        r"""data-testid\s*=\s*["']""" + re.escape(PROBE_MARKER_TESTID) + r"""["']"""
    )
    assert pattern.search(text), (
        f"src/app/layout.tsx MUST author an element with "
        f"data-testid={PROBE_MARKER_TESTID!r}. The G4 capture manifest "
        f"pins the test-id; without it the capture producer fails "
        f"closed."
    )


def test_layout_marker_data_testid_is_a_string_literal() -> None:
    """The ``data-testid`` value MUST be a literal string, NOT an
    expression (``{...}``) or computed value. A dynamic value would
    diverge between SSR and CSR and break hydration safety; a
    non-string value (number, boolean, symbol) would also break the
    G4 capture gate that matches the literal test-id substring."""
    text = _read_layout()
    # Reject the expression form: `data-testid={"g4-probe-marker"}`.
    expression_form = re.compile(
        r"""data-testid\s*=\s*\{\s*["']"""
        + re.escape(PROBE_MARKER_TESTID)
        + r"""["']\s*\}"""
    )
    assert expression_form.search(text) is None, (
        "probe marker data-testid MUST be a string LITERAL, not a "
        "JSX expression — hydration safety requires identical SSR "
        "and CSR output."
    )


# ---------------------------------------------------------------------------
# Hydration safety (static, no dynamic content)
# ---------------------------------------------------------------------------

def test_layout_marker_is_static_with_no_handlers_or_hooks() -> None:
    """The probe marker MUST be a static, hydration-safe element. It
    MUST NOT carry event handlers (``onClick``, ``onLoad``, ...),
    React hooks (``useState``, ``useEffect``, ``useRef``, ...), or
    ``dangerouslySetInnerHTML``. A dynamic marker would cause
    SSR/CSR divergence and React would warn, which the G5 hydration
    collector surfaces as a console warning."""
    text = _read_layout()
    element_text, _ = _find_marker_opening_tag(text)
    forbidden = (
        "onClick", "onLoad", "onError", "onFocus", "onBlur",
        "onChange", "onMouseDown", "onMouseUp", "onKeyDown",
        "useState", "useEffect", "useRef", "useMemo", "useCallback",
        "dangerouslySetInnerHTML",
    )
    offenders = [needle for needle in forbidden if needle in element_text]
    assert not offenders, (
        f"probe marker element MUST NOT carry {offenders!r}; it must "
        f"stay static and hydration-safe. Got: {element_text!r}"
    )


def test_layout_marker_has_no_jsx_expression_in_opening_tag() -> None:
    """No ``{...}`` JSX expression may appear inside the probe marker's
    opening tag. Expressions are how hydration-unsafe values sneak
    into static markup (e.g. ``style={{...}}`` is acceptable because
    it's a static object literal — but anything reading runtime state
    is forbidden). The stricter ``element_text`` check below keeps the
    contract reviewable."""
    text = _read_layout()
    element_text, _ = _find_marker_opening_tag(text)
    assert "{" not in element_text and "}" not in element_text, (
        f"probe marker opening tag MUST NOT contain JSX expressions; "
        f"it must stay purely static. Got: {element_text!r}"
    )


# ---------------------------------------------------------------------------
# Visibility / accessibility / focus order
# ---------------------------------------------------------------------------

def test_layout_marker_is_hidden_from_visual_and_accessibility_tree() -> None:
    """The probe marker MUST NOT alter visible layout or accessible
    content. The cleanest hydration-safe contract is the HTML5
    ``hidden`` attribute (which sets ``display: none`` AND removes the
    element from the accessibility tree) OR ``aria-hidden="true"``.
    Either form keeps the marker in the DOM for the G4 capture gate
    while keeping it invisible to users and assistive tech."""
    text = _read_layout()
    element_text, _ = _find_marker_opening_tag(text)
    has_hidden_attr = re.search(r"""(?:^|\s)hidden(?:\s*=|\s|$)""", element_text) is not None
    has_aria_hidden = re.search(
        r"""aria-hidden\s*=\s*["']true["']""", element_text
    ) is not None
    assert has_hidden_attr or has_aria_hidden, (
        f"probe marker element MUST carry either the HTML `hidden` "
        f"attribute or `aria-hidden=\"true\"` to stay invisible. "
        f"Got: {element_text!r}"
    )


def test_layout_marker_is_not_focusable() -> None:
    """The probe marker MUST NOT appear in the focus order. A focusable
    marker would shift tab order and break the visible-layout
    contract. Native focusable tags (``a``, ``button``, ``input``,
    ``select``, ``textarea``) and any ``tabIndex`` attribute are
    forbidden."""
    text = _read_layout()
    element_text, tag = _find_marker_opening_tag(text)
    assert "tabIndex" not in element_text and "tabindex" not in element_text, (
        f"probe marker element MUST NOT carry a tabindex; it must "
        f"stay out of the focus order. Got: {element_text!r}"
    )
    forbidden_tags = {"a", "button", "input", "select", "textarea"}
    assert tag.lower() not in forbidden_tags, (
        f"probe marker tag <{tag}> is natively focusable; use a "
        f"non-focusable element (e.g. <span> or <div>) instead. "
        f"Got: {element_text!r}"
    )


def test_layout_marker_has_no_text_content() -> None:
    """The probe marker MUST NOT ship visible or screen-reader text.
    Any text content would alter accessible content even with
    ``aria-hidden``. Empty / whitespace-only content is allowed so
    the element can remain paired if the author prefers.

    Detection: capture the optional ``>...</TAG>`` inner text via the
    regex helper, then assert it's empty. A self-closing element
    yields no inner text and trivially passes."""
    text = _read_layout()
    match = _MARKER_TAG_RE.search(text)
    assert match is not None, "probe marker element not authored — RED gate"
    is_self_closing = match.group(4) == "/"
    if is_self_closing:
        return  # No inner content possible.
    # Paired form: locate the inner text via a follow-up search.
    tag = match.group(1)
    # Find the closing tag for the matched opening tag (handles the
    # only expected case: a paired <span data-testid=...>...</span>).
    open_end = match.end()
    close_re = re.compile(r"</" + re.escape(tag) + r"\s*>", re.DOTALL)
    close_match = close_re.search(text, open_end)
    assert close_match is not None, (
        f"probe marker opening tag is paired but no closing "
        f"</{tag}> was found — malformed JSX. Got: {match.group(0)!r}"
    )
    inner = text[open_end:close_match.start()].strip()
    assert inner == "", (
        f"probe marker element MUST NOT carry text content; "
        f"got {inner!r}. Use a self-closing element or an element "
        f"with only whitespace."
    )


# ---------------------------------------------------------------------------
# Topology guards — must remain intact after the marker ships
# ---------------------------------------------------------------------------

def test_layout_topology_guards_remain_intact() -> None:
    """The probe marker MUST NOT relax any chain-topology guard. PR
    3b pins the layout's import contract; the marker addition cannot
    import owners of later PRs (``@taxa/app-shell``,
    ``@taxa/browser-state``). The ``./globals.css`` import is
    already required by PR 3c and stays unchanged."""
    text = _read_layout()
    forbidden_imports = (
        (r"""from\s+["']@taxa/app-shell""", "@taxa/app-shell"),
        (r"""from\s+["']@taxa/browser-state""", "@taxa/browser-state"),
    )
    for pattern, owner in forbidden_imports:
        assert re.search(pattern, text) is None, (
            f"layout.tsx MUST NOT import {owner} — that module's "
            f"owner is a later PR in the chain."
        )
