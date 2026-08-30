"""Strict-TDD contract tests for scripts/verify_build.py (G2 verifier).
See design.md §3.3.2.1. Synthetic fixtures + fake node/next — no install."""
import json, stat, subprocess, sys
from pathlib import Path
import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "verify_build.py"


def _x(p, body):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _fake_node(d, version="v20.10.0"):
    _x(d / "node",
       f'#!/usr/bin/env bash\n[ "$1" = "--version" ] && echo "{version}"\nexit 0\n')
    return d / "node"


def _next_body(out, nxt, *, fail=False, emit_app=False,
               index=True, js=True, css=True, errors=()):
    p = ["#!/usr/bin/env bash", "set -e", f"mkdir -p '{out}' '{nxt}'"]
    if index:
        p.append(f"printf '<html/>' > '{out}/index.html'")
    if js or css:
        p.append(f"mkdir -p '{out}/_next/static/chunks'")
    if js:
        p.append(f"printf 'JS' > '{out}/_next/static/chunks/app.js'")
    if css:
        p.append(f"printf 'CSS' > '{out}/_next/static/chunks/app.css'")
    for n in errors:
        p.append(f"printf '<{n}/>' > '{out}/{n}'")
    p.append(f"printf '{{}}' > '{nxt}/build-manifest.json'")
    if emit_app:
        p.append(f"printf '{{}}' > '{nxt}/app-build-manifest.json'")
    if fail:
        p.append("exit 7")
    p.append("echo 'fake next build done'")
    return "\n".join(p) + "\n"


def _install_next(c, b, **kw):
    _x(b / "next", _next_body(c / "out", c / ".next", **kw))
    return b / "next"


def _defaults(c, b):
    """Install default fakes + return standard argv."""
    _fake_node(b); _install_next(c, b)
    return ["--out", str(c / "out"), "--node-min", "20.9.0",
            "--node", str(b / "node"), "--next", str(b / "next")]


def _args(c, b):
    return ["--out", str(c / "out"), "--node-min", "20.9.0",
            "--node", str(b / "node"), "--next", str(b / "next")]


def _run(argv):
    return subprocess.run([sys.executable, str(SCRIPT), *argv],
                          capture_output=True, text=True, check=False)


def _inv(c):
    p = c / "out" / "BUILD-INVENTORY.json"
    assert p.is_file(), f"no inventory at {p}"
    return json.loads(p.read_text())


@pytest.fixture
def c(tmp_path):
    d = tmp_path / "candidate"; d.mkdir()
    (d / "node_modules" / ".bin").mkdir(parents=True)
    return d


@pytest.fixture
def b(tmp_path):
    d = tmp_path / "bin"; d.mkdir(); return d


def test_happy_path_emits_inventory(c, b):
    """All gates pass → inventory with all required classes + schema + sha256."""
    r = _run(_defaults(c, b))
    assert r.returncode == 0, r.stderr
    inv = _inv(c)
    classes = {a["class"] for a in inv["assets"]}
    assert {"application_route_html", "js_class", "css_class"} <= classes
    assert inv["missing_classes"] == []
    for k in ("node_version", "candidate_root", "build_command",
              "build_started_at", "build_finished_at", "exit_code",
              "assets", "missing_classes"):
        assert k in inv
    assert inv["exit_code"] == 0 and inv["node_version"].startswith("v")
    for a in inv["assets"]:
        if a["class"] in ("application_route_html", "js_class", "css_class"):
            assert a["bytes"] > 0 and len(a["sha256"]) == 64


def test_build_log_captured_and_cwd_is_candidate(c, b):
    """build.log captures stdout; build runs with cwd = candidate root."""
    marker = c / "pwd.marker"
    body = (_next_body(c / "out", c / ".next")
            + f"printf '%s' \"$PWD\" > '{marker}'\n")
    _fake_node(b); _x(b / "next", body)
    r = _run(_args(c, b))
    assert r.returncode == 0, r.stderr
    assert "fake next build done" in (c / "build.log").read_text()
    assert marker.read_text().rstrip("\n") == str(c)


def test_node_below_min_fails_before_build(c, b):
    """Node < min → verifier exits non-zero WITHOUT invoking the build."""
    argv = _args(c, b)
    _fake_node(b, version="v18.20.0")  # override the default fake
    r = _run(argv)
    assert r.returncode != 0
    assert not (c / "out" / "BUILD-INVENTORY.json").is_file()
    assert not (c / "build.log").is_file(), "build must NOT be invoked"


def test_build_nonzero_no_inventory(c, b):
    _fake_node(b); _install_next(c, b, fail=True)
    r = _run(_args(c, b))
    assert r.returncode != 0
    assert not (c / "out" / "BUILD-INVENTORY.json").is_file()


def test_required_manifest_missing_fails(c, b):
    """No build-manifest.json in .next → staging fails, partial cleared."""
    body = _next_body(c / "out", c / ".next").replace(
        f"printf '{{}}' > '{c}/.next/build-manifest.json'\n", "")
    _fake_node(b); _x(b / "next", body)
    r = _run(_args(c, b))
    assert r.returncode != 0
    assert not (c / "out" / "BUILD-INVENTORY.json").is_file()
    out_next = c / "out" / ".next"
    if out_next.exists():
        assert not any(out_next.iterdir())


def test_optional_app_manifest_recorded_staged_or_not_emitted(c, b):
    """app-build-manifest.json absent → not_emitted; present → staged."""
    _fake_node(b); _install_next(c, b, emit_app=False)
    r = _run(_args(c, b)); assert r.returncode == 0, r.stderr
    opt = [a for a in _inv(c)["assets"]
           if a.get("class") == "staged_manifest"
           and a["path"].endswith("app-build-manifest.json")]
    assert len(opt) == 1 and opt[0]["staging"] == "not_emitted", opt
    # Triangulate: with emit_app=True, both manifests are staged.
    _fake_node(b); _install_next(c, b, emit_app=True)
    r = _run(_args(c, b)); assert r.returncode == 0, r.stderr
    staged = [a for a in _inv(c)["assets"]
              if a.get("class") == "staged_manifest"]
    assert len(staged) == 2 and all(
        a["staging"] == "staged" and a["bytes"] > 0 for a in staged)


@pytest.mark.parametrize("omit,label", [
    ("index", "application_route_html"),
    ("js", "js_class"),
    ("css", "css_class"),
])
def test_missing_required_class_fails(c, b, omit, label):
    _fake_node(b)
    kw = {"index": omit != "index", "js": omit != "js", "css": omit != "css"}
    _install_next(c, b, **kw)
    r = _run(_args(c, b))
    assert r.returncode != 0, (label, r.stderr)
    assert not (c / "out" / "BUILD-INVENTORY.json").is_file()


def test_404_classified_as_error_pages_not_application_route(c, b):
    _fake_node(b); _install_next(c, b, errors=("404.html",))
    r = _run(_args(c, b)); assert r.returncode == 0, r.stderr
    inv = _inv(c)
    app = [a for a in inv["assets"] if a["class"] == "application_route_html"]
    err = [a for a in inv["assets"] if a["class"] == "error_pages"]
    assert len(app) == 1 and app[0]["path"].endswith("index.html"), app
    assert any(e["path"].endswith("404.html") for e in err), err


def test_error_pages_alone_do_not_satisfy_application_route(c, b):
    """404.html/500.html but NO index.html → STILL missing-classes failure."""
    _fake_node(b); _install_next(c, b, index=False, errors=("404.html", "500.html"))
    r = _run(_args(c, b))
    assert r.returncode != 0, "error_pages are exempt, NOT promoted"
    assert not (c / "out" / "BUILD-INVENTORY.json").is_file()


def test_failure_leaves_no_temp_artifacts(c, b):
    _fake_node(b); _install_next(c, b, js=False)
    r = _run(_args(c, b)); assert r.returncode != 0
    leftovers = [p.name for p in (c / "out").rglob("*")
                 if p.is_file() and (".tmp" in p.name
                                     or p.name.startswith(".BUILD"))]
    assert not leftovers, leftovers


def test_default_next_path_resolves_under_candidate_node_modules(c, b):
    """Without --next, resolve <candidate>/node_modules/.bin/next (§3.3.2.1)."""
    _fake_node(b); _install_next(c, b)
    canonical = c / "node_modules" / ".bin" / "next"
    canonical.write_text((b / "next").read_text())
    canonical.chmod(canonical.stat().st_mode | stat.S_IXUSR)
    argv = ["--out", str(c / "out"), "--node-min", "20.9.0", "--node", str(b / "node")]
    r = _run(argv)
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert (c / "out" / "BUILD-INVENTORY.json").is_file()


def test_missing_out_arg_fails():
    r = _run(["--node-min", "20.9.0"])
    assert r.returncode != 0
    assert "out" in r.stderr.lower() or "usage" in r.stderr.lower()