"""Phase 3c-iv-barrel design-system purity guard tests.

Pins PR 3c-iv-barrel (openspec/changes/complete-taxa-frontend-migration/tasks.md
§"Phase 3c-iv-barrel"). The design-system module is the **single owner of
the theme-token table** — every other module MUST consume the typed token
from `@taxa/design-system`, never the literal hex value.
"""
from __future__ import annotations

import re
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src" / "modules"
DS = SRC / "design-system"
DS_INFRA = DS / "infrastructure"

SIBLING_MODULES: tuple[str, ...] = (
    "taxonomy", "research", "browser-state", "app-shell",
)

# Typed theme tokens (must match `THEME_TOKENS` in `infrastructure/index.ts`).
THEME_TOKEN_NAMES: tuple[str, ...] = (
    "--primary", "--accent", "--surface", "--elevated",
    "--on-surface", "--on-surface-variant",
    "--outline", "--outline-variant",
    "--surface-container-low", "--surface-container",
    "--surface-container-high", "--surface-container-highest",
    "--primary-fixed", "--on-primary-fixed",
    "--realm-bacteria", "--realm-archaea", "--realm-viruses",
    "--realm-animalia", "--realm-fungi", "--realm-plantae",
    "--realm-chromista", "--realm-other",
)

# Canonical 6-digit + 3-digit shorthand hex literals. 3-digit MUST end
# on a word boundary so the regex does not swallow `#foo` (CSS id
# selector) or `#abc` (HTML anchor).
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}\b")


def _scan_hex_literals(root: Path) -> list[tuple[Path, int, str, str]]:
    """Return `(path, lineno, raw_line, hex_match)` for every hex literal
    in `root` (recursive). Skips `.gitkeep`. Returns [] if the root
    does not exist. Only scans `.ts` / `.tsx` — Tailwind 4 + the global
    CSS own the literal cascade. Comment stripping is intentionally NOT
    applied: a hex literal in a comment is still a hex literal."""
    if not root.exists():
        return []
    findings: list[tuple[Path, int, str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        if path.suffix not in (".ts", ".tsx"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, raw_line in enumerate(text.splitlines(), start=1):
            m = HEX_RE.search(raw_line)
            if m:
                findings.append((path, lineno, raw_line, m.group(0)))
    return findings


def test_infrastructure_barrel_exists_and_reexports_components() -> None:
    """`infrastructure/index.ts` MUST exist + re-export `<Icon>` +
    `<Button>` so consumers can reach them via the typed-token barrel."""
    target = DS_INFRA / "index.ts"
    assert target.is_file(), f"missing {target.relative_to(REPO)}"
    src = target.read_text(encoding="utf-8")
    for tok in ("Icon", "Button"):
        assert tok in src, f"infrastructure/index.ts must re-export {tok!r}"


def test_infrastructure_barrel_reexports_every_typed_token() -> None:
    """The barrel MUST re-export every typed theme token. Token
    type-narrowing is what makes a downstream `#1d7ea9` leakage a
    TypeScript error."""
    src = (DS_INFRA / "index.ts").read_text(encoding="utf-8")
    missing = [t for t in THEME_TOKEN_NAMES if t not in src]
    assert not missing, (
        f"infrastructure/index.ts must re-export typed tokens: {missing!r}"
    )


def test_sibling_modules_have_no_hex_literals() -> None:
    """Every module outside the design-system MUST stay hex-literal-
    free. A leakage (e.g. `color: '#1d7ea9'` inside `taxonomy/`) is
    a contract violation."""
    all_findings: list[tuple[Path, int, str, str]] = []
    for module in SIBLING_MODULES:
        all_findings.extend(_scan_hex_literals(SRC / module))
    assert all_findings == [], (
        "hex literals leaked outside the design-system module. "
        "Consumers MUST import the typed token from "
        "`@taxa/design-system`, not the literal. Findings: "
        + "\n".join(
            f"  {p.relative_to(REPO)}:{lineno}  {hex_match}  {raw_line!r}"
            for p, lineno, raw_line, hex_match in all_findings
        )
    )
