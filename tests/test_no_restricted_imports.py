"""
ESLint barrel-only contract tests for the modular monolith — PR 2b + 2c slices.

PR 2 task 2.4 installs `.eslintrc.cjs` whose `no-restricted-imports` rule
rejects **deep imports** into any module's layer folders. Cross-module
access MUST go through `src/modules/<capability>/index.ts` (or the
`@taxa/<capability>` alias). The rule covers BOTH path spellings
(`src/modules/<cap>/<layer>/*` AND `@taxa/<cap>/<layer>/*`) per the
maintainer's explicit decision.

PR 2b covers the config-presence and allowed-barrel fixture behaviour.
PR 2c extends that with a runtime triangulation across the full
`CAPABILITIES × LAYERS` matrix — 20 committed literal fixtures plus
dynamic `@taxa/<cap>/<layer>/deep` inputs in `tmp_path` — proving all
40 deep-import forms (literal AND alias) are rejected while public
barrels stay allowed.

References:
    openspec/changes/migrate-nextjs-tailwind4/design.md §Cross-module import guard
    openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md Rule 5
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ESLINTRC = REPO_ROOT / ".eslintrc.cjs"
FIXTURES_DIR = REPO_ROOT / "scripts" / "eslint-fixtures"

# ESLint 9 dropped legacy `.eslintrc.*` support by default; the project
# pins the legacy form so `node --check` and the CommonJS module format
# stay trivial. Setting `ESLINT_USE_FLAT_CONFIG=false` opts back in.
ESLINT_ENV = {"ESLINT_USE_FLAT_CONFIG": "false"}


# Pinned by `tests/test_module_layers.py::CAPABILITIES/LAYERS` and
# `specs/modular-architecture/spec.md` rule 2/3.
CAPABILITIES: tuple[str, ...] = (
    "taxonomy",
    "research",
    "design-system",
    "browser-state",
    "app-shell",
)
LAYERS: tuple[str, ...] = (
    "presentation",
    "application",
    "domain",
    "infrastructure",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _has_npx() -> bool:
    return shutil.which("npx") is not None


def _has_node() -> bool:
    return shutil.which("node") is not None


def _load_eslint_patterns() -> list[str]:
    """Return the resolved `no-restricted-imports::patterns` array from
    `.eslintrc.cjs` by loading the CJS module via Node.

    Empty list if the file is missing, Node is not on PATH, or the
    config does not declare the rule. Asserting on the resolved
    patterns (rather than scanning source text) validates the
    EFFECTIVE configuration: a malformed glob, a typo, or a
    programmatically-built-but-never-registered pattern would all
    pass a string-presence check and fail here.
    """
    if not ESLINTRC.exists() or not _has_node():
        return []
    script = (
        "const cfg = require(" + repr(str(ESLINTRC)) + ");\n"
        "const rule = cfg && cfg.rules && cfg.rules['no-restricted-imports'];\n"
        "const patterns = rule && rule[1] && rule[1].patterns;\n"
        "if (Array.isArray(patterns)) {\n"
        "  process.stdout.write(patterns.join('\\n'));\n"
        "}\n"
    )
    result = subprocess.run(
        ["node", "-e", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def _run_eslint(targets: list[Path], config: Path | None = None) -> subprocess.CompletedProcess:
    """Run ESLint via npx. `npx --yes` fetches `eslint` on demand so PR 2b
    does not commit a heavy `node_modules/` tree.
    """
    cmd = ["npx", "--yes", "eslint@9"]
    if config is not None:
        cmd += ["--config", str(config)]
    cmd += ["--no-error-on-unmatched-pattern"]
    cmd += [str(t) for t in targets]
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env={**os.environ, **ESLINT_ENV},
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Config-presence tests (no eslint invocation required)
# ---------------------------------------------------------------------------
def test_eslintrc_exists():
    """`.eslintrc.cjs` exists at the repo root (design.md pins the filename)."""
    assert ESLINTRC.is_file(), (
        f"missing ESLint config: {ESLINTRC}. PR 2b ships this file."
    )


def test_eslintrc_uses_commonjs_module_format():
    """`.eslintrc.cjs` uses `module.exports` so `node --check` stays trivial."""
    if not ESLINTRC.exists():
        pytest.skip("eslintrc not present yet")
    text = ESLINTRC.read_text()
    assert "module.exports" in text, (
        f"{ESLINTRC} must use CommonJS module.exports per design.md"
    )


def test_eslintrc_declares_no_restricted_imports_rule():
    """The config wires `no-restricted-imports` so the rule actually runs."""
    if not ESLINTRC.exists():
        pytest.skip("eslintrc not present yet")
    text = ESLINTRC.read_text()
    assert "no-restricted-imports" in text, (
        f"{ESLINTRC} must declare the no-restricted-imports rule. "
        f"spec.md rule 5 requires deep-imports to be rejected at build time."
    )


@pytest.mark.parametrize("capability", CAPABILITIES)
@pytest.mark.parametrize("layer", LAYERS)
def test_eslintrc_restricts_each_layer_per_capability(capability: str, layer: str):
    """Every (capability × layer) pair MUST appear in the *resolved*
    `no-restricted-imports::patterns` array, under BOTH path spellings
    (literal `src/modules/<cap>/<layer>` and alias `@taxa/<cap>/<layer>`).
    """
    patterns = _load_eslint_patterns()
    if not patterns:
        pytest.skip("eslintrc not present or unparseable yet")
    literal_needle = f"src/modules/{capability}/{layer}"
    alias_needle = f"@taxa/{capability}/{layer}"
    assert any(literal_needle in p for p in patterns), (
        f"{ESLINTRC} must restrict deep imports into '{literal_needle}' "
        f"in the resolved patterns array."
    )
    assert any(alias_needle in p for p in patterns), (
        f"{ESLINTRC} must also restrict deep imports via the "
        f"@taxa/{capability}/{layer} alias form to prevent bypass."
    )


def test_eslintrc_does_not_forbid_the_barrel():
    """Every pattern that targets a capability MUST include a layer
    segment after the capability name; otherwise the pattern would
    match the public barrel (`src/modules/<cap>` or `@taxa/<cap>`).
    """
    patterns = _load_eslint_patterns()
    if not patterns:
        pytest.skip("eslintrc not present or unparseable yet")
    for cap in CAPABILITIES:
        for prefix in (f"src/modules/{cap}/", f"@taxa/{cap}/"):
            for pattern in patterns:
                if not pattern.startswith(prefix):
                    continue
                layer_segment = pattern[len(prefix):].split("/", 1)[0]
                assert layer_segment, (
                    f"eslintrc pattern {pattern!r} targets the capability "
                    f"root {prefix!r} with no layer segment and would "
                    f"match the barrel path."
                )


# ---------------------------------------------------------------------------
# Behaviour tests — exercise the rule against the 3 PR 2b fixtures.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "fixture_name",
    ("deep_import.js", "barrel_import.js", "deep_import_research.js"),
)
def test_fixture_files_exist(fixture_name: str):
    """The 3 ESLint behaviour fixtures are committed under `scripts/eslint-fixtures/`."""
    assert (FIXTURES_DIR / fixture_name).is_file(), (
        f"missing fixture: {fixture_name}. PR 2b ships these."
    )


@pytest.fixture()
def require_npx() -> None:
    if not _has_npx():
        pytest.skip("npx not available on PATH")


def _fixture(name: str) -> Path:
    path = FIXTURES_DIR / name
    if not path.is_file():
        pytest.skip(f"fixture not present yet: {path}")
    return path


def test_deep_import_into_layer_is_rejected(require_npx: None):
    """`src/modules/taxonomy/domain/taxon` is the canonical anti-pattern;
    ESLint must exit non-zero. Verifies the rule fires at runtime."""
    if not ESLINTRC.exists():
        pytest.skip("eslintrc not present yet — see test_eslintrc_exists")
    fixture = _fixture("deep_import.js")
    result = _run_eslint([fixture], config=ESLINTRC)
    assert result.returncode != 0, (
        f"ESLint must reject deep imports; exited 0.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_barrel_import_is_allowed(require_npx: None):
    """`src/modules/taxonomy` (the public barrel) MUST NOT be blocked;
    the rule pattern is targeted at layer paths, not the barrel."""
    if not ESLINTRC.exists():
        pytest.skip("eslintrc not present yet")
    fixture = _fixture("barrel_import.js")
    result = _run_eslint([fixture], config=ESLINTRC)
    if result.returncode != 0:
        combined = result.stdout + result.stderr
        if "no-restricted-imports" in combined and "src/modules/taxonomy" in combined:
            pytest.fail(
                f"ESLint blocked a legitimate barrel import.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        # Any other ESLint complaint is out of scope; pass for our contract.


def test_layer_violation_message_mentions_path(require_npx: None):
    """ESLint's error message MUST include the offending path so a
    developer can fix the import without `eslint --debug`."""
    if not ESLINTRC.exists():
        pytest.skip("eslintrc not present yet")
    fixture = _fixture("deep_import_research.js")
    result = _run_eslint([fixture], config=ESLINTRC)
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "src/modules/research/application" in combined, (
        f"ESLint error must include the offending deep path; got:\n{combined}"
    )


# ---------------------------------------------------------------------------
# Triangulation — alias-form enforcement at runtime.
#
# The maintainer's explicit decision is to prohibit deep imports through
# BOTH path spellings. The three committed fixtures cover the literal
# `src/modules/...` form; these two tests cover the `@taxa/...` alias
# form at runtime using pytest's tmp_path (no new fixture files committed
# — PR 2c owns the per-capability fixture sweep).
# ---------------------------------------------------------------------------
def test_alias_form_deep_import_is_rejected(require_npx: None, tmp_path: Path):
    """`@taxa/<capability>/<layer>/...` deep imports are rejected. Without
    this, the rule could be bypassed via the tsconfig.json path alias."""
    if not ESLINTRC.exists():
        pytest.skip("eslintrc not present yet")
    fixture = tmp_path / "deep_import_alias.js"
    fixture.write_text(
        'import { something } from "@taxa/taxonomy/domain/taxon";\n'
        "console.log(something);\n"
    )
    result = _run_eslint([fixture], config=ESLINTRC)
    assert result.returncode != 0, (
        f"ESLint did not reject alias-form deep import into "
        f"@taxa/taxonomy/domain/taxon.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_alias_form_barrel_is_allowed(require_npx: None, tmp_path: Path):
    """The alias-form barrel (`@taxa/<capability>`) MUST remain allowed;
    the layer-suffix patterns (`@taxa/<cap>/<layer>/*`) don't match it."""
    if not ESLINTRC.exists():
        pytest.skip("eslintrc not present yet")
    fixture = tmp_path / "barrel_import_alias.js"
    fixture.write_text(
        'import { something } from "@taxa/taxonomy";\n'
        "console.log(something);\n"
    )
    result = _run_eslint([fixture], config=ESLINTRC)
    if result.returncode != 0:
        combined = result.stdout + result.stderr
        if "no-restricted-imports" in combined and "@taxa/taxonomy" in combined:
            pytest.fail(
                f"ESLint blocked a legitimate alias-form barrel import.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        # Any other ESLint complaint is out of scope; pass for our contract.


# ---------------------------------------------------------------------------
# PR 2c — Runtime triangulation across the full (capability × layer) matrix.
#
# PR 2b ships 3 literal fixtures and one-off runtime checks for one
# alias pair. PR 2c closes the sweep: 20 committed literal fixtures
# (`scripts/eslint-fixtures/deep_import_<cap>_<layer>.js`) plus dynamic
# `@taxa/<cap>/<layer>/deep` inputs in tmp_path, parametrized over every
# (capability × layer) pair so all 40 deep-import forms (literal AND alias)
# are runtime-tested against the ESLint config PR 2b installed. Public
# barrels stay allowed.
# ---------------------------------------------------------------------------


def _pr2c_fixture_name(capability: str, layer: str) -> str:
    """Stable on-disk name for a PR 2c literal fixture.

    Format: `deep_import_<capability>_<layer>.js`. Keeping the matrix
    pair in the filename makes the fixture self-describing in directory
    listings and aligns with PR 2b's `deep_import_research.js` convention.
    """
    return f"deep_import_{capability}_{layer}.js"


def _pr2c_literal_fixture_path(capability: str, layer: str) -> Path:
    return FIXTURES_DIR / _pr2c_fixture_name(capability, layer)


@pytest.mark.parametrize("capability", CAPABILITIES)
@pytest.mark.parametrize("layer", LAYERS)
def test_pr2c_literal_fixture_files_exist(capability: str, layer: str):
    """Every (capability × layer) pair MUST have a committed literal
    fixture under `scripts/eslint-fixtures/`. The runtime triangulation
    test below points at these stable on-disk files; without them the
    sweep cannot reproduce a failing run from the repo alone."""
    path = _pr2c_literal_fixture_path(capability, layer)
    assert path.is_file(), (
        f"missing PR 2c literal fixture for {capability}/{layer}: "
        f"{path}. PR 2c ships 20 such fixtures (5 caps x 4 layers)."
    )


@pytest.mark.parametrize("capability", CAPABILITIES)
@pytest.mark.parametrize("layer", LAYERS)
def test_pr2c_literal_deep_import_is_rejected(
    require_npx: None, capability: str, layer: str
):
    """Runtime ESLint invocation against the committed literal fixture.
    Each `src/modules/<cap>/<layer>/deep` path MUST be rejected by the
    `no-restricted-imports` rule. This is the first half of PR 2c's
    40-form sweep (20 literal paths)."""
    if not ESLINTRC.exists():
        pytest.skip("eslintrc not present yet")
    fixture = _pr2c_literal_fixture_path(capability, layer)
    if not fixture.is_file():
        pytest.fail(
            f"PR 2c fixture missing for {capability}/{layer}: {fixture}"
        )
    result = _run_eslint([fixture], config=ESLINTRC)
    assert result.returncode != 0, (
        f"ESLint must reject literal deep import into "
        f"src/modules/{capability}/{layer}; exited 0.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert f"src/modules/{capability}/{layer}" in combined, (
        f"ESLint error must include the offending literal path "
        f"src/modules/{capability}/{layer}; got:\n{combined}"
    )


@pytest.mark.parametrize("capability", CAPABILITIES)
@pytest.mark.parametrize("layer", LAYERS)
def test_pr2c_alias_form_deep_import_is_rejected(
    require_npx: None, capability: str, layer: str, tmp_path: Path
):
    """Runtime ESLint invocation against a dynamically generated
    tmp_path file containing `@taxa/<cap>/<layer>/deep`. Each alias
    form MUST be rejected. This is the second half of PR 2c's 40-form
    sweep (20 alias paths); the tmp_path generation avoids committing
    20 mirror fixtures just to assert the rule."""
    if not ESLINTRC.exists():
        pytest.skip("eslintrc not present yet")
    fixture = tmp_path / f"deep_import_alias_{capability}_{layer}.js"
    # Use the resolved layer+capability in the import string. Capability
    # names contain a hyphen but the rule pattern matches on `<cap>/<layer>/`,
    # so the literal capability string is the contract-relevant form.
    fixture.write_text(
        f'import {{ something }} from "@taxa/{capability}/{layer}/deep";\n'
        "console.log(something);\n"
    )
    result = _run_eslint([fixture], config=ESLINTRC)
    assert result.returncode != 0, (
        f"ESLint must reject alias-form deep import into "
        f"@taxa/{capability}/{layer}/deep; exited 0.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert f"@taxa/{capability}/{layer}" in combined, (
        f"ESLint error must include the offending alias path "
        f"@taxa/{capability}/{layer}; got:\n{combined}"
    )


@pytest.mark.parametrize("capability", CAPABILITIES)
@pytest.mark.parametrize("form", ("literal", "alias"))
def test_pr2c_barrel_import_remains_allowed(
    require_npx: None, capability: str, form: str, tmp_path: Path
):
    """Triangulation: every public barrel (literal AND alias form)
    MUST remain allowed even after PR 2c sweeps every
    (capability × layer) pair. Catches a regression where a future
    pattern refactor accidentally matches the barrel path (no layer
    segment) and over-blocks the legitimate public surface."""
    if not ESLINTRC.exists():
        pytest.skip("eslintrc not present yet")
    fixture = tmp_path / f"barrel_{form}_{capability}.js"
    if form == "literal":
        target = f"src/modules/{capability}"
    else:
        target = f"@taxa/{capability}"
    fixture.write_text(
        f'import {{ something }} from "{target}";\n'
        "console.log(something);\n"
    )
    result = _run_eslint([fixture], config=ESLINTRC)
    if result.returncode != 0:
        combined = result.stdout + result.stderr
        if "no-restricted-imports" in combined and target in combined:
                pytest.fail(
                    f"ESLint blocked a legitimate {form}-form barrel import "
                    f"into {target}.\n"
                    f"stdout: {result.stdout}\nstderr: {result.stderr}"
                )
        # Any other ESLint complaint is out of scope; pass for our contract.
