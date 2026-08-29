"""
Domain purity guard tests (PR 2e).

Pins spec.md rule 4 as an executable guard over the
`src/modules/taxonomy/domain/` directory: the domain layer MUST stay
free of framework, I/O, browser, HTTP, and process tokens. The guard
runs against a *comment-stripped* view of the source so
author-friendly documentation never accidentally violates the rule.

Critically, comment stripping is exercised with **controlled input**
rather than incidentally by the current `taxon.ts` (which is compact
and does not contain every comment form). Each forbidden-token
category gets a synthetic file where the token lives ONLY in a
comment; the guard MUST accept it. A real violation (token in code)
MUST be flagged, and the diagnostic MUST preserve the original
un-stripped source line so a reviewer can find and fix it.

References:
    openspec/changes/migrate-nextjs-tailwind4/tasks.md            §Phase 2e
    openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md  Rule 4
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAIN_DIR = REPO_ROOT / "src" / "modules" / "taxonomy" / "domain"


# Forbidden tokens — verbatim categories from spec.md rule 4. The list
# mirrors the framing in `tests/test_taxonomy_domain.py`. Cross-module
# import paths are a Rule 5 (module-boundary) concern, not Rule 4
# (domain purity), so they are intentionally out of scope here. Order
# is the stable iteration order used by the parametrized diagnostics
# below.
FORBIDDEN_TOKENS: tuple[str, ...] = (
    # framework
    "react",
    "next",
    "nextjs",
    "fastapi",
    "starlette",
    "pydantic",
    # I/O / network
    "fetch(",
    # browser
    "localStorage",
    "document.",
    "window.",
    # node process
    "process.",
)


# Comment-stripping regexes. Block comments are matched first so a
# `//` inside a `/* ... */` is not treated as a line comment opener.
# JSDoc is just a block comment that starts with `**`, so the block
# pattern covers it. Each substitution replaces the matched comment
# with spaces (preserving line numbers and column alignment) so the
# diagnostic line numbers reported by `_find_forbidden` still match
# the original source.
_BLOCK_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/")
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def _blank_match(match: re.Match[str]) -> str:
    """Replace every character in a match with a space; keep newlines
    intact so line numbers stay aligned with the original source."""
    return re.sub(r"[^\n]", " ", match.group(0))


def _strip_ts_comments(text: str) -> str:
    """Remove line and block comments (including JSDoc) from `text`,
    preserving line numbers so caller diagnostics stay accurate.

    Block comments are stripped before line comments so a `//` token
    inside a `/* ... */` is not interpreted as a line-comment opener.
    The substitution replaces comment characters with spaces (newlines
    pass through unchanged), so line 42 of the stripped output
    corresponds to line 42 of the original source.
    """
    text = _BLOCK_COMMENT_RE.sub(_blank_match, text)
    text = _LINE_COMMENT_RE.sub(_blank_match, text)
    return text


def _direct_ts_files(root: Path) -> list[Path]:
    """Return direct `.ts` children of `root`, excluding `.gitkeep`.
    Stable order (sorted by name) so diagnostics are reproducible."""
    if not root.is_dir():
        return []
    return [
        p for p in sorted(root.iterdir())
        if p.is_file() and p.suffix == ".ts" and p.name != ".gitkeep"
    ]


def _find_forbidden(text: str) -> list[tuple[str, int, str]]:
    """Return (token, lineno, raw_line) for each forbidden match in
    `text`. The caller is responsible for stripping comments first so
    the diagnostic is not cluttered with false positives from JSDoc."""
    findings: list[tuple[str, int, str]] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        for token in FORBIDDEN_TOKENS:
            if token in raw_line:
                findings.append((token, lineno, raw_line))
    return findings


# ---------------------------------------------------------------------------
# Helper-level tests: prove comment stripping with controlled input.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "source,forbidden_in_comment,code_marker",
    [
        # Line comment carrying a forbidden token — line number preserved.
        ("// process.env.NODE_ENV\nconst x = 1;\n", "process.", "const x = 1;"),
        # JSDoc block carrying a forbidden token — JSDoc is just a block.
        ("/** calls window.alert */\nconst y = 2;\n", "window.", "const y = 2;"),
        # Plain block comment carrying a forbidden token.
        ("/* document.title */\nconst z = 3;\n", "document.", "const z = 3;"),
        # Trailing line comment after a clean line.
        ("const a = 4; // fetch('/api')\n", "fetch(", "const a = 4;"),
        # Multi-line block with code on its own line below.
        ("/* line 1\n   line 2\n   line 3 */\nconst b = 5;\n",
         None, "const b = 5;"),
        # Source with no comments — text is unchanged (no forbidden tokens).
        ("const c = 6;\nconst d = 7;\n", None, "const c = 6;"),
    ],
    ids=[
        "line_comment_strips_forbidden_token",
        "jsdoc_block_strips_forbidden_token",
        "plain_block_strips_forbidden_token",
        "trailing_line_comment_stripped",
        "multi_line_block_stripped",
        "no_comments_unchanged",
    ],
)
def test_strip_ts_comments_removes_comments(
    source: str, forbidden_in_comment: str | None, code_marker: str,
) -> None:
    """Controlled input: the comment stripper MUST remove line, block,
    and JSDoc comments. Asserts four contract properties:

      1. No `//`, `/*`, or `*/` markers survive in the stripped text.
      2. A forbidden token embedded in a comment is no longer present.
      3. Code content (non-comment text) is preserved verbatim.
      4. Line count is preserved so `_find_forbidden` line-number
         diagnostics remain aligned with the original source.

    Property 4 is the reason the helper blanks comments with spaces
    instead of removing them outright: a multi-line block comment that
    occupies lines 3-5 would otherwise shift every later line up by 3,
    silently corrupting the diagnostic.
    """
    cleaned = _strip_ts_comments(source)
    # 1. Comment markers gone. We test the *opener* and *closer*
    # explicitly so a regression on either end of a block fails fast.
    assert not re.search(r"//", cleaned), (
        f"line-comment opener `//` survived stripping: {cleaned!r}"
    )
    assert "/*" not in cleaned, (
        f"block-comment opener `/*` survived stripping: {cleaned!r}"
    )
    assert "*/" not in cleaned, (
        f"block-comment closer `*/` survived stripping: {cleaned!r}"
    )
    # 2. Forbidden token from the comment is gone.
    if forbidden_in_comment is not None:
        assert forbidden_in_comment not in cleaned, (
            f"forbidden token {forbidden_in_comment!r} from comment "
            f"survived stripping: {cleaned!r}"
        )
    # 3. Code content preserved.
    assert code_marker in cleaned, (
        f"code marker {code_marker!r} lost during stripping: {cleaned!r}"
    )
    # 4. Line count preserved for diagnostic alignment.
    assert cleaned.count("\n") == source.count("\n"), (
        f"line count shifted during stripping: source has "
        f"{source.count(chr(10))} lines, cleaned has "
        f"{cleaned.count(chr(10))} lines. Diagnostics would misalign."
    )


# ---------------------------------------------------------------------------
# Integration: scan the real domain directory.
# ---------------------------------------------------------------------------
def test_domain_dir_contains_at_least_one_real_ts_file() -> None:
    """`src/modules/taxonomy/domain/` MUST contain at least one real
    `.ts` source file (excluding `.gitkeep`). Otherwise the purity
    guard has nothing to guard and would silently pass on an empty
    directory — a future PR that drops every `.ts` file would slip
    through unnoticed."""
    files = _direct_ts_files(DOMAIN_DIR)
    assert files, (
        f"no real `.ts` files found in {DOMAIN_DIR}. The domain layer "
        f"needs at least one source file for the purity guard to be meaningful."
    )


def test_domain_dir_excludes_gitkeep_from_scan() -> None:
    """The scan MUST skip `.gitkeep` so a scaffold placeholder cannot
    accidentally satisfy the file-presence contract."""
    assert DOMAIN_DIR.is_dir(), (
        f"missing domain dir: {DOMAIN_DIR}. PR 2d creates this folder."
    )
    files = _direct_ts_files(DOMAIN_DIR)
    assert all(p.name != ".gitkeep" for p in files), (
        f"scan must exclude .gitkeep; got: {[p.name for p in files]}"
    )


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_domain_ts_files_have_no_forbidden_token(token: str) -> None:
    """Parametrized over every forbidden token from spec.md rule 4: the
    comment-stripped view of every real domain `.ts` file MUST contain
    zero matches. Diagnostics include the line number for any failure
    so the reviewer lands on the exact line they need to fix."""
    files = _direct_ts_files(DOMAIN_DIR)
    if not files:
        pytest.skip(
            "no real `.ts` files in domain — see "
            "test_domain_dir_contains_at_least_one_real_ts_file"
        )
    for path in files:
        original = path.read_text()
        cleaned = _strip_ts_comments(original)
        for tok, lineno, raw_line in _find_forbidden(cleaned):
            assert tok != token, (
                f"{path.name}: forbidden token {tok!r} found at line "
                f"{lineno} (comment-stripped view; line number "
                f"matches the original source). "
                f"Line content: {raw_line!r}"
            )


# ---------------------------------------------------------------------------
# Controlled input: a forbidden token ONLY in a comment MUST be allowed.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "comment_source",
    [
        "const ok: number = 1;\n// process.env.NODE_ENV\n",
        "const ok: number = 1;\n/** document.title here */\n",
        "const ok: number = 1;\n/* fetch('/api') lives here */\n",
        "const ok: number = 1; // window.alert('hi')\n",
        "const ok: number = 1;\n/*\n * localStorage.getItem('k')\n *\n */\n",
    ],
    ids=[
        "line_comment_with_process",
        "jsdoc_with_document",
        "block_with_fetch",
        "trailing_with_window",
        "multi_line_with_localStorage",
    ],
)
def test_forbidden_token_only_in_comment_is_allowed(
    tmp_path: Path, comment_source: str,
) -> None:
    """When a forbidden token appears ONLY in a comment, the guard
    MUST accept the file. The controlled-input half of the proof —
    the real `taxon.ts` is compact and does not cover every comment
    form, so this test pins the contract explicitly."""
    target = tmp_path / "synthetic.ts"
    target.write_text(comment_source)
    cleaned = _strip_ts_comments(target.read_text())
    findings = _find_forbidden(cleaned)
    assert findings == [], (
        f"comment-stripped view still reports forbidden matches: "
        f"{findings!r}. Comment stripping is broken — the helper is "
        f"either not removing comments or not removing all forms."
    )


def test_forbidden_token_in_code_is_rejected(tmp_path: Path) -> None:
    """Inverse of the previous test: a forbidden token in real code
    (not in a comment) MUST be flagged. The diagnostic line number
    must point at the offending line of code, not at a comment."""
    target = tmp_path / "violator.ts"
    target.write_text(
        "// perfectly fine comment\n"
        "const value = process.env.NODE_ENV;\n"  # `process.` in code
        "export { value };\n"
    )
    cleaned = _strip_ts_comments(target.read_text())
    findings = _find_forbidden(cleaned)
    assert findings, "expected at least one forbidden match in real code"
    tokens = {tok for tok, _, _ in findings}
    assert "process." in tokens, (
        f"expected 'process.' in findings; got: {tokens!r}"
    )
    bad_lines = [lineno for _, lineno, _ in findings]
    assert 2 in bad_lines, (
        f"expected violation on line 2 (the real code); got lines: {bad_lines}"
    )


def test_diagnostics_preserve_original_line(tmp_path: Path) -> None:
    """When the guard flags a real violation, the reported line MUST
    be the *original* un-stripped source (with comments intact) so the
    diagnostic is actionable for the reviewer."""
    target = tmp_path / "violator.ts"
    target.write_text(
        "// normal comment\n"
        "const value = window.alert;\n"  # `window.` in code
        "// trailing comment with process.env\n"
    )
    findings = _find_forbidden(_strip_ts_comments(target.read_text()))
    assert findings, "expected one forbidden match for `window.`"
    token, lineno, raw_line = findings[0]
    assert token == "window."
    assert lineno == 2, f"expected violation on line 2; got line {lineno}"
    assert "const value = window.alert;" in raw_line, (
        f"diagnostic must preserve original source line; got: {raw_line!r}"
    )
