"""Toolchain-bootstrap contract tests for the Next.js migration (PR 3a).

Pins: engines.node literal, required deps + majors, legacy Tailwind 3.4 deps
absent, scripts, tsconfig.json path aliases per CAPABILITIES, .nvmrc literal.
"""
from __future__ import annotations
import json, re
from pathlib import Path
import pytest
from tests.test_module_layers import CAPABILITIES

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_JSON = REPO_ROOT / "package.json"
TSCONFIG_JSON = REPO_ROOT / "tsconfig.json"
NVMRC = REPO_ROOT / ".nvmrc"
REQUIRED_NODE_ENGINE = ">=20.9.0"
NVMRC_LITERAL = "20"
ALIAS_PREFIX = "@taxa/"
REQUIRED_DEPS = (
    ("next", "16", "dependencies"), ("react", "19", "dependencies"),
    ("react-dom", "19", "dependencies"), ("typescript", "5", "devDependencies"),
    ("@types/react", "19", "devDependencies"), ("@types/react-dom", "19", "devDependencies"),
    ("@types/node", None, "devDependencies"),
)
REQUIRED_DEPS_PRODUCTION = (("tailwindcss", "4"),)
FORBIDDEN_LEGACY_DEPS = ("autoprefixer", "postcss", "@tailwindcss/forms")
REQUIRED_SCRIPTS = ("check-runtime", "build:web")

def _pkg() -> dict:
    if not PACKAGE_JSON.is_file(): pytest.fail("package.json missing — PR 3a task 3a.2 must create it")
    return json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))

def _tsconfig() -> dict:
    """Read tsconfig.json accepting JSON-with-comments (`//` keys, `// foo`)."""
    if not TSCONFIG_JSON.is_file(): pytest.fail("tsconfig.json missing — PR 3a task 3a.4 must create it")
    raw = TSCONFIG_JSON.read_text(encoding="utf-8")
    out: list[str] = []; i = 0; in_string = False; escape = False
    while i < len(raw):
        ch = raw[i]
        if in_string:
            out.append(ch)
            if escape: escape = False
            elif ch == "\\": escape = True
            elif ch == '"': in_string = False
            i += 1; continue
        if ch == "/" and i + 1 < len(raw) and raw[i + 1] in ("/", "*"):
            if raw[i + 1] == "/":
                i += 2
                while i < len(raw) and raw[i] != "\n": i += 1
            else:
                i += 2
                while i + 1 < len(raw) and not (raw[i] == "*" and raw[i + 1] == "/"): i += 1
                i += 2
            continue
        if ch == '"': in_string = True
        out.append(ch); i += 1
    return json.loads("".join(out))

def _nvmrc() -> str:
    if not NVMRC.is_file(): pytest.fail(".nvmrc missing — PR 3a task 3a.5 must create it")
    return NVMRC.read_text(encoding="utf-8")

def _major_pinned(spec: str, expected: str) -> bool:
    if expected is None: return True
    s = spec.strip()
    if re.fullmatch(r"\d+(?:\.\d+(?:\.\d+)?)?", s):
        return s.split(".", 1)[0] == expected
    m = re.fullmatch(r"[\^~](\d+)(?:\.\d+(?:\.\d+)?)?", s)
    if m: return m.group(1) == expected
    m = re.match(r"^>=\s*(\d+)(?:\.\d+(?:\.\d+)?)?", s)
    return bool(m and m.group(1) == expected)


def test_engines_node_is_pinned_literal():
    spec = _pkg().get("engines", {}).get("node")
    assert spec == REQUIRED_NODE_ENGINE, (
        f"package.json::engines.node must equal {REQUIRED_NODE_ENGINE!r}; got {spec!r}"
    )

def test_engines_node_has_no_drift_tokens():
    spec = _pkg().get("engines", {}).get("node", "")
    for token in ("~", "^"):
        assert token not in spec, f"engines.node must not contain {token!r}; got {spec!r}"

@pytest.mark.parametrize("name,major,section", REQUIRED_DEPS)
def test_required_dep_present_with_pinned_major(name, major, section):
    spec = _pkg().get(section, {}).get(name)
    assert spec is not None, f"required dep {name!r} missing from package.json::{section}"
    if major is not None:
        assert _major_pinned(spec, major), f"{section}.{name} must pin major {major!r}; got {spec!r}"

@pytest.mark.parametrize("name,major", REQUIRED_DEPS_PRODUCTION)
def test_required_dep_present_in_dependencies(name, major):
    pkg = _pkg()
    spec = pkg.get("dependencies", {}).get(name)
    assert spec is not None, f"production dep {name!r} missing from dependencies"
    assert name not in (pkg.get("devDependencies") or {}), f"{name!r} must NOT live in devDependencies"
    assert _major_pinned(spec, major), f"dependencies.{name} must pin major {major!r}; got {spec!r}"

@pytest.mark.parametrize("name", FORBIDDEN_LEGACY_DEPS)
def test_legacy_tailwind_3_dep_absent(name):
    pkg = _pkg()
    leaked = [s for s in ("dependencies", "devDependencies") if name in (pkg.get(s) or {})]
    assert not leaked, f"legacy dep {name!r} present in {leaked}; PR 3a task 3a.2 must remove it"

@pytest.mark.parametrize("script", REQUIRED_SCRIPTS)
def test_required_script_defined(script):
    scripts = _pkg().get("scripts", {})
    assert script in scripts and scripts[script].strip(), (
        f"required script {script!r} missing or empty in package.json::scripts"
    )

def test_check_runtime_script_is_literal_node_invocation():
    raw = _pkg().get("scripts", {}).get("check-runtime", "")
    assert raw == "node scripts/check-runtime.mjs", (
        f"scripts.check-runtime must be the literal 'node scripts/check-runtime.mjs'; got {raw!r}"
    )

def test_tsconfig_exists_at_repo_root():
    assert TSCONFIG_JSON.is_file(), f"tsconfig.json missing at {TSCONFIG_JSON}"

def test_tsconfig_compiler_options_paths_defined():
    paths = _tsconfig().get("compilerOptions", {}).get("paths")
    assert isinstance(paths, dict) and paths, "compilerOptions.paths must be a non-empty object"

@pytest.mark.parametrize("capability", CAPABILITIES)
def test_tsconfig_path_alias_targets_capability(capability):
    paths = _tsconfig().get("compilerOptions", {}).get("paths", {})
    baseUrl = _tsconfig().get("compilerOptions", {}).get("baseUrl")
    barrel = paths.get(f"{ALIAS_PREFIX}{capability}")
    subpath = paths.get(f"{ALIAS_PREFIX}{capability}/*")
    assert barrel, f"tsconfig.json missing barrel alias @{capability}"
    assert subpath, f"tsconfig.json missing subpath alias @{capability}/*"
    barrel_clean = barrel[0].split("*", 1)[0].rstrip("/")
    subpath_clean = subpath[0].split("*", 1)[0].rstrip("/")
    assert barrel_clean.endswith(f"/{capability}") or barrel_clean.endswith(f"/{capability}/index.ts"), (
        f"barrel alias @{capability} target {barrel[0]!r} must point at {capability!r}"
    )
    assert subpath_clean.endswith(f"/{capability}"), (
        f"subpath alias @{capability}/* target {subpath[0]!r} must point at {capability!r}"
    )
    if baseUrl is not None:
        assert baseUrl in (".", ""), f"baseUrl, if present, must be '.'; got {baseUrl!r}"

def test_nvmrc_literal_is_single_line_20():
    raw = _nvmrc()
    if raw.startswith("\ufeff"): raw = raw[1:]
    assert raw == f"{NVMRC_LITERAL}\n", (
        f".nvmrc must equal {NVMRC_LITERAL!r} + single trailing newline; got {raw!r}"
    )
    assert "\r" not in raw and raw.count("\n") == 1, f".nvmrc must have exactly one LF; got {raw!r}"

def test_nvmrc_pins_node_major_floor_at_20():
    major = int(_nvmrc().strip().split(".", 1)[0])
    assert major >= 20, f".nvmrc pins major {major}, below {REQUIRED_NODE_ENGINE!r}"

def test_triangulate_engines_node_byte_exact():
    """engines.node MUST be exactly `>=20.9.0` byte-for-byte (no whitespace)."""
    raw = _pkg().get("engines", {}).get("node", "")
    assert raw == REQUIRED_NODE_ENGINE, f"engines.node must equal {REQUIRED_NODE_ENGINE!r}; got {raw!r}"

def test_triangulate_required_deps_have_caret_or_range_form():
    """Every pinned dep MUST use `^MAJOR` or a range form (not `*` or empty)."""
    pkg = _pkg()
    all_names = {n for n, _, _ in REQUIRED_DEPS} | {n for n, _ in REQUIRED_DEPS_PRODUCTION}
    for name in all_names:
        found = None
        for section in ("dependencies", "devDependencies"):
            m = pkg.get(section, {}) or {}
            if name in m: found = (section, m[name])
        assert found, f"required dep {name!r} missing"
        assert found[1].strip() and found[1].strip() != "*", (
            f"{name!r} must use a pinned spec; got {found[1]!r}"
        )

def test_triangulate_check_runtime_script_has_no_nodejs_alias():
    """scripts.check-runtime MUST NOT invoke `nodejs` (Debian alias)."""
    raw = _pkg().get("scripts", {}).get("check-runtime", "")
    assert raw == "node scripts/check-runtime.mjs", f"got {raw!r}"
    assert "nodejs" not in raw, f"check-runtime must not invoke 'nodejs'; got {raw!r}"

def test_triangulate_tsconfig_paths_covers_every_capability():
    """Every CAPABILITIES entry MUST have both barrel + subpath aliases."""
    paths = _tsconfig().get("compilerOptions", {}).get("paths", {})
    missing = []
    for c in CAPABILITIES:
        if f"{ALIAS_PREFIX}{c}" not in paths: missing.append(f"{ALIAS_PREFIX}{c}")
        if f"{ALIAS_PREFIX}{c}/*" not in paths: missing.append(f"{ALIAS_PREFIX}{c}/*")
    assert not missing, f"tsconfig.json::paths missing: {missing}"