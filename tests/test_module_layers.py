"""
Modular-monolith layer-folder contract tests for the Next.js migration.

PR 2 (Phase 2 scaffold work unit) introduces the *layout* of the
modular monolith: 5 capability modules, each with 4 layer folders
(presentation, application, domain, infrastructure) and a public
barrel `index.ts`. These tests pin the layout so a future PR cannot
silently drop a layer or rename a capability.

Reference:
    openspec/changes/migrate-nextjs-tailwind4/tasks.md  §Phase 2  (2.1)
    openspec/changes/migrate-nextjs-tailwind4/design.md §Module layout row
    openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md
        Rules 2 (capability-aligned modules) and 3 (four layers per module)
        and 5 (public barrel per module)

The capability list comes verbatim from design.md §Architecture
Decisions, "Module layout" row, plus the §File Changes table which
adds `app-shell` for the header / nav / footer host:

    taxonomy, research, design-system, browser-state, app-shell

The four layer folder names are pinned by spec.md rule 3:

    presentation, application, domain, infrastructure

The barrel is `index.ts` per spec.md rule 5. Cross-module imports
MUST go through the barrel; deep imports are blocked by ESLint
(tested separately by `tests/test_no_restricted_imports.py`).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Constants pinned by design.md + spec.md (test must break if either changes).
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
MODULES_ROOT = REPO_ROOT / "src" / "modules"

# Capability list — verbatim from design.md §Architecture Decisions, "Module
# layout" row, plus `app-shell` from §File Changes.
CAPABILITIES: tuple[str, ...] = (
    "taxonomy",
    "research",
    "design-system",
    "browser-state",
    "app-shell",
)

# Layer names — verbatim from spec.md rule 3.
LAYERS: tuple[str, ...] = (
    "presentation",
    "application",
    "domain",
    "infrastructure",
)

# Barrel name — verbatim from spec.md rule 5 ("barrel export, index.ts, or
# equivalent"). The design commits to `index.ts` explicitly.
BARREL_NAME = "index.ts"

# Branch-name regex from openspec/config.yaml::conventions.branch_regex —
# copied here to keep this test self-contained without an openspec import.
_BRANCH_REGEX = re.compile(
    r"^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$"
)


# ---------------------------------------------------------------------------
# RED fixtures: each is the *minimum* on-disk evidence that proves the
# scaffold landed. Until 2.2 ships the directories, these fixtures resolve
# to missing paths and the corresponding tests fail.
# ---------------------------------------------------------------------------
def _module_dir(capability: str) -> Path:
    return MODULES_ROOT / capability


def _layer_dir(capability: str, layer: str) -> Path:
    return MODULES_ROOT / capability / layer


def _barrel(capability: str) -> Path:
    return MODULES_ROOT / capability / BARREL_NAME


# ---------------------------------------------------------------------------
# Layout tests — one per spec.md rule.
# ---------------------------------------------------------------------------
def test_modules_root_exists():
    """`src/modules/` exists as the modular-monolith root.

    spec.md rule 2: capability-aligned modules live here. This is the
    root folder every other assertion in this file is anchored to.
    """
    assert MODULES_ROOT.is_dir(), (
        f"missing modules root: {MODULES_ROOT}. PR 2 task 2.2 creates this folder."
    )


@pytest.mark.parametrize("capability", CAPABILITIES)
def test_capability_module_exists(capability: str):
    """Each capability module has its own folder under `src/modules/`.

    spec.md rule 2: every top-level module name is a business capability
    (no `utils`, `shared`, `controllers`, etc.).
    """
    assert _module_dir(capability).is_dir(), (
        f"missing capability module folder: {_module_dir(capability)}. "
        f"PR 2 task 2.2 must create one folder per capability in {CAPABILITIES}."
    )


@pytest.mark.parametrize("capability", CAPABILITIES)
@pytest.mark.parametrize("layer", LAYERS)
def test_layer_folder_exists(capability: str, layer: str):
    """Every capability module carries the four required layer folders.

    spec.md rule 3: presentation, application, domain, infrastructure are
    each represented per module — "no layer is silently merged into
    another". The parameterize gives us 5 × 4 = 20 assertions.
    """
    layer_dir = _layer_dir(capability, layer)
    assert layer_dir.is_dir(), (
        f"missing layer folder: {layer_dir}. "
        f"PR 2 task 2.2 must create all 4 layers per capability."
    )


@pytest.mark.parametrize("capability", CAPABILITIES)
def test_barrel_index_ts_exists(capability: str):
    """Every capability module exposes an `index.ts` public barrel.

    spec.md rule 5: "barrel export, index.ts, or equivalent per module.
    Non-exported symbols are private. Cross-module deep imports
    rejected at build time via path-alias config or equivalent lint
    guard." PR 2 task 2.2 ships the barrels; this test pins the
    filename so a future PR cannot rename it to e.g. `barrel.ts`
    without breaking the lint guard contract.
    """
    barrel = _barrel(capability)
    assert barrel.is_file(), (
        f"missing barrel file: {barrel}. PR 2 task 2.2 must ship "
        f"`{BARREL_NAME}` at the module root."
    )


@pytest.mark.parametrize("capability", CAPABILITIES)
def test_barrel_is_typescript_not_javascript(capability: str):
    """The barrel is `*.ts`, not `*.js` — guards against accidentally
    shipping an empty JS barrel when the migration starts moving real
    code into the modules.

    design.md commits to TypeScript (`src/modules/{capability}/index.ts`);
    the test pins that filename and extension.
    """
    barrel = _barrel(capability)
    if not barrel.exists():
        pytest.skip(f"barrel not present yet — see {test_barrel_index_ts_exists.__name__}")
    assert barrel.suffix == ".ts", (
        f"barrel must be a `.ts` file per design.md; got {barrel}"
    )


def test_no_top_level_technical_dump_folders():
    """spec.md rule 2 forbids technical dumping-ground names at the top
    level of `src/modules/`. Any folder matching a forbidden technical
    name MUST NOT exist.

    The forbidden set mirrors the rule's enumerated examples. Adding
    one to the set must be an explicit decision; the test fails
    loudly if such a folder accidentally reappears.
    """
    if not MODULES_ROOT.exists():
        pytest.skip("modules root not present yet — see test_modules_root_exists")
    forbidden = {
        "utils", "shared", "common", "helpers", "misc",
        "controllers", "services", "repositories",
        "components", "hooks", "lib",
    }
    actual = {p.name for p in MODULES_ROOT.iterdir() if p.is_dir()}
    leak = actual & forbidden
    assert not leak, (
        f"top-level technical dumping ground not allowed by spec.md rule 2: "
        f"{sorted(leak)}. Rename to a capability-aligned name."
    )


def test_every_module_root_is_capability_aligned():
    """Inverse guard of `test_no_top_level_technical_dump_folders`: every
    direct child of `src/modules/` MUST be one of the pinned capability
    names (or, in the future, an extension explicitly added by a new
    spec revision).

    Catches stray `src/modules/staging/` or `src/modules/old/` folders
    that a future refactor might leave behind.
    """
    if not MODULES_ROOT.exists():
        pytest.skip("modules root not present yet")
    actual = {p.name for p in MODULES_ROOT.iterdir() if p.is_dir()}
    extra = actual - set(CAPABILITIES)
    assert not extra, (
        f"unknown top-level module folders (not in CAPABILITIES): "
        f"{sorted(extra)}. Either add to CAPABILITIES by spec revision, "
        f"or remove the folder."
    )


def test_total_module_count_matches_pinned_5():
    """Hard cap on the capability count: exactly 5 modules exist.

    design.md enumerates 5 capabilities. If a future spec revision adds
    a 6th, the change must update both this test and `CAPABILITIES`.
    """
    if not MODULES_ROOT.exists():
        pytest.skip("modules root not present yet")
    module_dirs = [p for p in MODULES_ROOT.iterdir() if p.is_dir()]
    assert len(module_dirs) == len(CAPABILITIES), (
        f"expected exactly {len(CAPABILITIES)} capability modules, "
        f"found {len(module_dirs)}: {[p.name for p in module_dirs]}"
    )


def test_no_forbidden_layer_name_per_module():
    """Inverse guard of `test_layer_folder_exists`: every direct child of
    a capability module MUST be one of the 4 pinned layer folders, the
    barrel, or a `.gitkeep` (used by the scaffold before any real file
    lands). Anything else is a layer-renaming violation.

    spec.md rule 3 enumerates the four required layer names; nothing
    else is allowed.
    """
    if not MODULES_ROOT.exists():
        pytest.skip("modules root not present yet")
    allowed = set(LAYERS) | {BARREL_NAME, ".gitkeep"}
    for capability in CAPABILITIES:
        module_dir = _module_dir(capability)
        if not module_dir.exists():
            continue
        children = {p.name for p in module_dir.iterdir()}
        unexpected = children - allowed
        assert not unexpected, (
            f"module '{capability}' has unexpected children: {sorted(unexpected)}. "
            f"Only these are allowed: {sorted(allowed)}."
        )
