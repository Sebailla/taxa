"""Strict-TDD tests for `scripts/compare_hydration.py` (G5 candidate
comparison CLI). Joins a raw legacy capture
(`taxa.g5-capture.legacy/1`, `build: legacy`, 10 samples) and a raw
migrated capture (`taxa.g5-capture.migrated/1`, `build: migrated`,
10 samples) and emits a deterministic comparison artifact with three
explicit outcomes: `passed` / `threshold_failed` / `blocked/unassessable`.
Fail-closed: invalid inputs raise `ValueError` (caught by CLI,
never a traceback); no bundle-size result/claim emitted."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.compare_hydration as ch_comp

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "compare_hydration.py"
COMP_SCHEMA = "taxa.g5-hydration-comparison/1"
LEGACY_SCHEMA = "taxa.g5-capture.legacy/1"
MIGRATED_SCHEMA = "taxa.g5-capture.migrated/1"
INTERACTIVE = "client_render.tree_first_interactive_ms"


# ---------------------------------------------------------------------------
# Compact builders (shared by every test).
# ---------------------------------------------------------------------------


def _sample(*, fp=80.0, dcl=100.0, wait_ms=30.0, found=True, count=1,
            first_text="x", le=200.0, iteration=0):
    return {
        "iteration": iteration, "captured_at": "2026-01-01T00:00:00Z",
        "navigation": {"response_start_ms": 60.0,
                        "dom_content_loaded_ms": dcl, "load_event_ms": le,
                        "redirect_count": 0, "status": 200},
        "paint": {"first_paint_ms": fp,
                  "first_contentful_paint_ms": fp + 20.0},
        "dom_marker": {"selector": '#tree-view[data-state="ready"]',
                        "found": found, "count": count,
                        "first_text": first_text, "wait_ms": wait_ms},
        "console": [],
    }


def _ten_samples(**kw):
    return [_sample(iteration=i, **kw) for i in range(10)]


def _legacy_envelope(samples=None, **kw):
    if samples is None:
        samples = _ten_samples(**kw)
    return {
        "schema": LEGACY_SCHEMA, "captured_at": "2026-01-01T00:00:00Z",
        "target_url": "http://127.0.0.1:8765/", "iterations": 10,
        "dom_marker_selector": '#tree-view[data-state="ready"]',
        "provenance": _provenance("taxa.g5-capture.legacy-provenance/1",
                                   "http://127.0.0.1:8765/"),
        "samples": samples,
    }


def _provenance(schema, target_url, **extra):
    base = {
        "schema": schema,
        "chromium": {"version": "fake-1.0", "executable_path": "/fake"},
        "playwright": {"version": "fake-pw-1.0"},
        "environment": {"python_version": "3.14.0", "platform": "test",
                        "captured_at_iso": "t0"},
        "target_url": target_url, "iterations": 10,
    }
    base.update(extra)
    return base


def _candidate_root(tmp_path, *, body=None, include_static=True):
    """Materialise a minimal Next.js static-export root.

    Includes a representative `_next/static/chunks/main.js` asset AND
    an `index.html` referencing `/_next/static/` so the strengthened
    structural identity checks in both `capture_hydration.validate_candidate_root`
    and `compare_hydration.validate_capture` pass.
    """
    root = tmp_path / "candidate"
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_bytes(body or
        (b"<!doctype html><html><body>candidate fixture</body>\n"
         b'<script src="/_next/static/chunks/main.js"></script>\n'
         b'<link rel="stylesheet" href="/_next/static/css/app.css">\n'
         b"</html>\n"))
    if include_static:
        static_dir = root / "_next" / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        (static_dir / "chunks").mkdir(exist_ok=True)
        (static_dir / "chunks" / "main.js").write_bytes(b"// js\n")
    return root


def _migrated_envelope(root, samples=None, **kw):
    if samples is None:
        samples = _ten_samples(**kw)
    sha = hashlib.sha256((root / "index.html").read_bytes()).hexdigest()
    return {
        "schema": MIGRATED_SCHEMA, "captured_at": "2026-01-01T00:00:00Z",
        "target_url": "http://127.0.0.1:9000/index.html", "iterations": 10,
        "build": "migrated", "candidate_root": str(root.resolve()),
        "candidate_index_sha256": sha, "static_dir_present": True,
        "dom_marker_selector": '#tree-view[data-state="ready"]',
        "provenance": _provenance("taxa.g5-capture.migrated-provenance/1",
                                   "http://127.0.0.1:9000/index.html",
                                   candidate_root=str(root.resolve()),
                                   candidate_index_sha256=sha),
        "samples": samples,
    }


def _write_pair(tmp_path, *, legacy=None, migrated=None, **root_kw):
    """Build a root + legacy + migrated capture trio, write the
    legacy/migrated captures as JSON files, return
    ``(legacy_path, migrated_path, root)``."""
    root = _candidate_root(tmp_path / "next", **root_kw)
    legacy = legacy if legacy is not None else _legacy_envelope()
    migrated = migrated if migrated is not None else _migrated_envelope(root)
    legacy_path = tmp_path / "legacy.json"
    migrated_path = tmp_path / "migrated.json"
    legacy_path.write_text(json.dumps(legacy))
    migrated_path.write_text(json.dumps(migrated))
    return legacy_path, migrated_path, root


# ---------------------------------------------------------------------------
# Module surface + decoupling
# ---------------------------------------------------------------------------


def test_compare_module_surface():
    for name in ("COMP_SCHEMA", "LEGACY_SCHEMA", "MIGRATED_SCHEMA",
                 "validate_capture", "compute_medians",
                 "compute_delta_pct", "compare_captures", "main"):
        assert hasattr(ch_comp, name), f"missing public symbol: {name}"
    assert ch_comp.COMP_SCHEMA == COMP_SCHEMA
    assert ch_comp.LEGACY_SCHEMA == LEGACY_SCHEMA
    assert ch_comp.MIGRATED_SCHEMA == MIGRATED_SCHEMA
    assert SCRIPT.is_file()


def test_compare_module_decoupled_from_other_chain_children():
    """Comparator stays decoupled from the G5 launcher / parity /
    lighthouse / orchestration / measure_hydration chain children."""
    import ast as _ast
    imports: list[str] = []
    for node in _ast.walk(_ast.parse(SCRIPT.read_text(encoding="utf-8"))):
        if isinstance(node, _ast.Import):
            imports.extend(n.name for n in node.names)
        elif isinstance(node, _ast.ImportFrom) and node.module:
            imports.append(node.module)
    for mod in imports:
        assert "parity" not in mod.lower()
        assert "lighthouse" not in mod.lower()
        assert "orchestrate" not in mod.lower()
        assert "measure_hydration" not in mod


# ---------------------------------------------------------------------------
# Validation: accept happy paths
# ---------------------------------------------------------------------------


def test_validate_capture_accepts_legacy_envelope():
    legacy = _legacy_envelope()
    summary = ch_comp.validate_capture(legacy, role="legacy")
    for k in ("schema", "iterations", "samples",
              "server_shell.first_paint_ms", INTERACTIVE,
              "raw_first_paint_ms", "raw_dom_content_loaded_ms",
              "raw_readiness_wait_ms"):
        assert k in summary, f"missing summary key {k!r}"
    for vec in (summary["raw_first_paint_ms"],
                summary["raw_dom_content_loaded_ms"]):
        assert len(vec) == 10
        for v in vec:
            assert isinstance(v, float) and v > 0


def test_validate_capture_accepts_migrated_envelope(tmp_path):
    root = _candidate_root(tmp_path / "next")
    migrated = _migrated_envelope(root)
    summary = ch_comp.validate_capture(migrated, role="migrated",
                                        candidate_root=root)
    assert summary["candidate_root"] == str(root.resolve())
    assert summary["candidate_index_sha256"] == hashlib.sha256(
        (root / "index.html").read_bytes()).hexdigest()
    assert summary["static_dir_present"] is True


# ---------------------------------------------------------------------------
# Validation: reject paths (parametrized for compactness)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role,build_capture,match", [
    ("migrated", lambda root: _legacy_envelope(),
     "schema|migrated|legacy"),
    ("legacy", lambda root: _migrated_envelope(root),
     "schema|migrated|legacy"),
])
def test_validate_capture_rejects_wrong_schema(role, build_capture, match,
                                                tmp_path):
    root = _candidate_root(tmp_path / "next")
    cap = build_capture(root)
    with pytest.raises(ValueError, match=match):
        ch_comp.validate_capture(cap, role=role,
                                  candidate_root=root if role == "migrated" else None)


@pytest.mark.parametrize("role,mutate,match", [
    ("migrated", lambda root, leg, mig: {**mig, "build": "legacy"},
     "build|migrated"),
    ("legacy", lambda root, leg, mig: {**leg, "build": "migrated"},
     "build|legacy"),
])
def test_validate_capture_rejects_wrong_build_label(role, mutate, match,
                                                     tmp_path):
    root = _candidate_root(tmp_path / "next")
    leg, mig = _legacy_envelope(), _migrated_envelope(root)
    cap = mutate(root, leg, mig)
    with pytest.raises(ValueError, match=match):
        ch_comp.validate_capture(cap, role=role,
                                  candidate_root=root if role == "migrated" else None)


@pytest.mark.parametrize("role,count", [("migrated", 0), ("migrated", 9),
                                          ("migrated", 11), ("legacy", 5)])
def test_validate_capture_rejects_non_ten_samples(role, count, tmp_path):
    root = _candidate_root(tmp_path / "next")
    if role == "migrated":
        m = _migrated_envelope(root)
        cap = {**m, "samples": m["samples"][:count], "iterations": count}
        cr = root
    else:
        leg = _legacy_envelope()
        cap = {**leg, "samples": leg["samples"][:count], "iterations": count}
        cr = None
    with pytest.raises(ValueError, match="samples|10"):
        ch_comp.validate_capture(cap, role=role, candidate_root=cr)


@pytest.mark.parametrize("path,value,match", [
    (["paint", "first_paint_ms"], float("nan"), "first_paint|finite|positive"),
    (["paint", "first_paint_ms"], -1.0, "first_paint|positive"),
    (["navigation", "dom_content_loaded_ms"], float("nan"),
     "dcl|dom_content|finite"),
    (["dom_marker", "wait_ms"], float("nan"), "wait_ms|finite"),
])
def test_validate_capture_rejects_invalid_metrics(path, value, match,
                                                   tmp_path):
    root = _candidate_root(tmp_path / "next")
    m = _migrated_envelope(root)
    samples = [dict(s) for s in m["samples"]]
    target = samples[3]
    # Navigate into the nested dict along `path[:-1]` and assign
    # the value at the last key — shallow-copy each level so the
    # mutation doesn't leak into sibling samples that share the
    # same nested-dict reference.
    cursor = target
    for k in path[:-1]:
        cursor[k] = dict(cursor[k])
        cursor = cursor[k]
    cursor[path[-1]] = value
    with pytest.raises(ValueError, match=match):
        ch_comp.validate_capture({**m, "samples": samples},
                                  role="migrated", candidate_root=root)


def test_validate_migrated_capture_rejects_sha_mismatch(tmp_path):
    """Recorded `candidate_index_sha256` MUST match on-disk; a
    mutated root rejects the stale hash."""
    root = _candidate_root(tmp_path / "next")
    migrated = _migrated_envelope(root)
    # Mutate index.html body but keep the `/_next/static/` reference
    # so only the sha check fires (not the structural identity check).
    (root / "index.html").write_bytes(
        b'<!doctype html><html><body>DIFFERENT</body>\n'
        b'<script src="/_next/static/chunks/main.js"></script>\n'
        b"</html>\n")
    with pytest.raises(ValueError, match="sha256|hash|mismatch"):
        ch_comp.validate_capture(migrated, role="migrated",
                                  candidate_root=root)


def test_validate_migrated_capture_rejects_missing_static_dir(tmp_path):
    """Comparator MUST re-verify `_next/static`; missing static dir
    fails closed."""
    root = _candidate_root(tmp_path / "next")
    migrated = _migrated_envelope(root)
    # rmtree because the default fixture now populates the static dir
    # with a representative asset.
    shutil.rmtree(root / "_next" / "static")
    with pytest.raises(ValueError, match="_next/static|_next"):
        ch_comp.validate_capture(migrated, role="migrated",
                                  candidate_root=root)


# ---------------------------------------------------------------------------
# Computation: medians + delta_pct
# ---------------------------------------------------------------------------


def test_compute_medians_uses_paint_first_paint_and_dcl_plus_wait():
    import statistics as st
    fps = [80.0 + i for i in range(10)]
    dcls = [100.0 + i for i in range(10)]
    waits = [30.0 + i for i in range(10)]
    samples = [_sample(iteration=i, fp=fps[i], dcl=dcls[i], wait_ms=waits[i])
                for i in range(10)]
    legacy = _legacy_envelope(samples)
    medians = ch_comp.compute_medians(
        ch_comp.validate_capture(legacy, role="legacy"))
    assert medians["server_shell.first_paint_ms"] == st.median(fps)
    assert medians["server_shell.dom_content_loaded_ms"] == st.median(dcls)
    assert medians[INTERACTIVE] == st.median(
        [d + w for d, w in zip(dcls, waits, strict=True)])


def test_compute_delta_pct_passes_when_within_band_and_fails_outside():
    legacy = {"server_shell.first_paint_ms": 100.0,
              "server_shell.dom_content_loaded_ms": 100.0,
              INTERACTIVE: 100.0}
    cand_in = {"server_shell.first_paint_ms": 105.0,
               "server_shell.dom_content_loaded_ms": 110.0,
               INTERACTIVE: 95.0}
    delta = ch_comp.compute_delta_pct(cand_in, legacy)
    assert delta["server_shell.first_paint_ms"] == pytest.approx(0.05)
    assert delta["server_shell.dom_content_loaded_ms"] == pytest.approx(0.10)
    assert delta[INTERACTIVE] == pytest.approx(-0.05)
    assert ch_comp.passes(cand_in, legacy, threshold=0.10) is True
    # +20% fails on first paint.
    cand_out = {**cand_in, "server_shell.first_paint_ms": 120.0}
    assert ch_comp.compute_delta_pct(
        cand_out, legacy)["server_shell.first_paint_ms"] == pytest.approx(0.20)
    assert ch_comp.passes(cand_out, legacy, threshold=0.10) is False
    # Boundary ±10% inclusive.
    cand_edge = {"server_shell.first_paint_ms": 110.0,
                 "server_shell.dom_content_loaded_ms": 110.0,
                 INTERACTIVE: 90.0}
    assert ch_comp.passes(cand_edge, legacy, threshold=0.10) is True


# ---------------------------------------------------------------------------
# Ready marker → blocked/unassessable
# ---------------------------------------------------------------------------


def test_compare_blocks_when_any_sample_missing_readiness(tmp_path):
    root = _candidate_root(tmp_path / "next")
    migrated = _migrated_envelope(root, wait_ms=-1.0, found=False,
                                   count=0, first_text=None)
    legacy = _legacy_envelope()
    out = ch_comp.compare_captures(legacy, migrated, candidate_root=root)
    assert out["result"] == "blocked/unassessable"
    assert out["passed"] is False
    assert out["unassessable_reason"]
    assert "found" in out["unassessable_reason"].lower() or \
        "readiness" in out["unassessable_reason"].lower()
    assert "delta_pct" not in out
    assert out["legacy"]["metrics"]["server_shell.first_paint_ms"] > 0
    assert out["migrated"]["metrics"]["server_shell.first_paint_ms"] > 0


# ---------------------------------------------------------------------------
# compare_captures: pass / threshold / bundle / determinism / immutability
# ---------------------------------------------------------------------------


def test_compare_captures_pass_when_within_threshold(tmp_path):
    root = _candidate_root(tmp_path / "next")
    migrated = _migrated_envelope(root, fp=85.0, dcl=100.0, wait_ms=30.0)
    out = ch_comp.compare_captures(_legacy_envelope(), migrated,
                                     candidate_root=root)
    assert out["schema"] == COMP_SCHEMA
    assert out["result"] == "passed"
    assert out["passed"] is True
    assert out["threshold"] == 0.10
    assert "bundle" not in json.dumps(out).lower()
    for k in ("server_shell.first_paint_ms", INTERACTIVE):
        assert k in out["delta_pct"]
        assert abs(out["delta_pct"][k]) <= 0.10


def test_compare_captures_threshold_failed_when_outside_band(tmp_path):
    root = _candidate_root(tmp_path / "next")
    migrated = _migrated_envelope(root, fp=96.0)  # 80→96 = +20%
    out = ch_comp.compare_captures(_legacy_envelope(), migrated,
                                     candidate_root=root)
    assert out["result"] == "threshold_failed"
    assert out["passed"] is False
    assert out["delta_pct"]["server_shell.first_paint_ms"] == pytest.approx(0.20)
    assert abs(out["delta_pct"]["server_shell.first_paint_ms"]) > 0.10


@pytest.mark.parametrize("mutation", [
    lambda leg, mig, root: (leg, _migrated_envelope(root, wait_ms=-1.0, found=False,
                                                   count=0, first_text=None)),
    lambda leg, mig, root: (_legacy_envelope(wait_ms=-1.0, found=False,
                                             count=0, first_text=None), mig),
    lambda leg, mig, root: (leg, _migrated_envelope(root, fp=200.0)),
])
def test_compare_captures_does_not_emit_bundle_size_claim(mutation, tmp_path):
    root = _candidate_root(tmp_path / "next")
    leg, mig = _legacy_envelope(), _migrated_envelope(root)
    leg, mig = mutation(leg, mig, root)
    out = ch_comp.compare_captures(leg, mig, candidate_root=root)
    assert "bundle" not in json.dumps(out).lower()


def test_compare_captures_deterministic_except_captured_at(tmp_path):
    root = _candidate_root(tmp_path / "next")
    leg, mig = _legacy_envelope(), _migrated_envelope(root)
    a = json.dumps(ch_comp.compare_captures(leg, mig, candidate_root=root),
                    sort_keys=True)
    b = json.dumps(ch_comp.compare_captures(leg, mig, candidate_root=root),
                    sort_keys=True)
    a_norm, b_norm = json.loads(a), json.loads(b)
    assert a_norm["captured_at"] and b_norm["captured_at"]
    a_norm.pop("captured_at")
    b_norm.pop("captured_at")
    assert a_norm == b_norm


def test_compare_captures_does_not_mutate_inputs(tmp_path):
    """Comparator never writes / mutates the input files."""
    root = _candidate_root(tmp_path / "next")
    legacy_doc = _legacy_envelope()
    migrated_doc = _migrated_envelope(root)
    _ = root  # root is forwarded through _write_pair -> _migrated_envelope
    legacy_path, migrated_path, _ = _write_pair(
        tmp_path, legacy=legacy_doc, migrated=migrated_doc)
    legacy_sha = hashlib.sha256(legacy_path.read_bytes()).hexdigest()
    migrated_sha = hashlib.sha256(migrated_path.read_bytes()).hexdigest()
    legacy_loaded = json.loads(legacy_path.read_text())
    migrated_loaded = json.loads(migrated_path.read_text())
    ch_comp.compare_captures(legacy_loaded, migrated_loaded, candidate_root=root)
    assert hashlib.sha256(legacy_path.read_bytes()).hexdigest() == legacy_sha
    assert hashlib.sha256(migrated_path.read_bytes()).hexdigest() == migrated_sha
    assert legacy_loaded == legacy_doc
    assert migrated_loaded == migrated_doc


# ---------------------------------------------------------------------------
# CLI: happy path / failure exits / mislabel / argparse / stdout
# ---------------------------------------------------------------------------


def _cli_main(tmp_path, *, legacy=None, migrated=None, extra=(), **root_kw):
    legacy_path, migrated_path, root = _write_pair(
        tmp_path, legacy=legacy, migrated=migrated, **root_kw)
    out_path = tmp_path / "comparison.json"
    argv = ["compare_hydration.py", str(legacy_path), str(migrated_path),
            "--candidate-root", str(root), "--out", str(out_path), *extra]
    return ch_comp.main(argv), out_path


def test_cli_happy_path_writes_artifact_and_does_not_mutate_inputs(tmp_path):
    legacy_path, migrated_path, root = _write_pair(tmp_path)
    legacy_sha = hashlib.sha256(legacy_path.read_bytes()).hexdigest()
    migrated_sha = hashlib.sha256(migrated_path.read_bytes()).hexdigest()
    rc = ch_comp.main(["compare_hydration.py", str(legacy_path),
                        str(migrated_path), "--candidate-root", str(root),
                        "--out", str(tmp_path / "comparison.json")])
    assert rc == 0
    doc = json.loads((tmp_path / "comparison.json").read_text())
    assert doc["result"] == "passed" and doc["passed"] is True
    assert hashlib.sha256(legacy_path.read_bytes()).hexdigest() == legacy_sha
    assert hashlib.sha256(migrated_path.read_bytes()).hexdigest() == migrated_sha


def test_cli_threshold_failed_returns_nonzero_exit(tmp_path):
    root = _candidate_root(tmp_path / "next")
    rc, out_path = _cli_main(
        tmp_path, migrated=_migrated_envelope(root, fp=200.0))
    assert rc != 0
    assert out_path.is_file()
    assert json.loads(out_path.read_text())["result"] == "threshold_failed"


def test_cli_blocked_unassessable_returns_nonzero_exit(tmp_path):
    root = _candidate_root(tmp_path / "next")
    rc, out_path = _cli_main(
        tmp_path,
        migrated=_migrated_envelope(root, wait_ms=-1.0, found=False,
                                      count=0, first_text=None))
    assert rc != 0
    assert json.loads(out_path.read_text())["result"] == "blocked/unassessable"


def test_cli_rejects_mislabeled_candidate_with_fail_closed(tmp_path):
    rc, out_path = _cli_main(tmp_path,
        migrated=_legacy_envelope())  # legacy schema in migrated slot
    assert rc != 0 and not out_path.exists()


def test_cli_rejects_mislabeled_legacy_with_fail_closed(tmp_path):
    root = _candidate_root(tmp_path / "next")
    rc, out_path = _cli_main(tmp_path,
        legacy=_migrated_envelope(root),  # migrated schema in legacy slot
        migrated=_migrated_envelope(root))
    assert rc != 0 and not out_path.exists()


def test_cli_subprocess_argparse_missing_args():
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO_ROOT,
                          capture_output=True, text=True, check=False)
    assert proc.returncode != 0 and proc.stderr.strip()


def test_cli_stdout_output_when_no_out_flag(tmp_path, capsys):
    root = _candidate_root(tmp_path / "next")
    legacy_path, migrated_path, _ = _write_pair(tmp_path)
    rc = ch_comp.main(["compare_hydration.py", str(legacy_path),
                        str(migrated_path), "--candidate-root", str(root)])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out.strip())
    assert doc["result"] == "passed"


# ---------------------------------------------------------------------------
# Follow-up fail-closed edge cases (parent review)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [[], "not-a-dict", 42, None, ["schema", "build"]])
def test_validate_capture_non_dict_payload_raises_value_error(bad, tmp_path):
    """List / scalar / None payload at either slot → ValueError,
    never TypeError / AttributeError."""
    root = _candidate_root(tmp_path / "next")
    migrated = _migrated_envelope(root)
    legacy = _legacy_envelope()
    with pytest.raises(ValueError):
        ch_comp.validate_capture(bad, role="legacy")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ch_comp.validate_capture(bad, role="migrated",  # type: ignore[arg-type]
                                  candidate_root=root)
    with pytest.raises(ValueError):
        ch_comp.compare_captures([], migrated, candidate_root=root)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ch_comp.compare_captures(legacy, "not-a-dict",  # type: ignore[arg-type]
                                  candidate_root=root)


@pytest.mark.parametrize("bad", [{}, {"schema": None}, {"schema": 42},
                                  {"schema": ["x"]}])
def test_validate_capture_dict_missing_schema_raises_value_error(bad, tmp_path):
    """Dict without `schema` (or non-string schema) → ValueError,
    never KeyError from unguarded dict-key access."""
    root = _candidate_root(tmp_path / "next")
    with pytest.raises(ValueError):
        ch_comp.validate_capture(bad, role="legacy")
    with pytest.raises(ValueError):
        ch_comp.validate_capture(bad, role="migrated",
                                  candidate_root=root)


@pytest.mark.parametrize("role,key,bad_value", [
    ("legacy", "paint", [{"first_paint_ms": 80.0}]),
    ("legacy", "navigation", "not-a-dict"),
    ("legacy", "dom_marker", None),
    ("migrated", "paint", "not-a-dict"),
])
def test_validate_capture_malformed_nested_containers_raise_value_error(
        role, key, bad_value, tmp_path):
    """`_validate_legacy_envelope` MUST type-check paint /
    navigation / dom_marker BEFORE `.get`. Malformed nested value
    → ValueError, not AttributeError."""
    root = _candidate_root(tmp_path / "next")
    if role == "migrated":
        cap = _migrated_envelope(root)
    else:
        cap = _legacy_envelope()
    samples = [dict(s) for s in cap["samples"]]
    samples[3] = dict(samples[3])
    samples[3][key] = bad_value
    with pytest.raises(ValueError, match=f"{key}|dict|getattr"):
        ch_comp.validate_capture({**cap, "samples": samples}, role=role,
                                  candidate_root=root if role == "migrated" else None)


def test_validate_capture_malformed_nested_containers_in_samples_list():
    """A sample that is itself not a dict → ValueError, not TypeError."""
    legacy = _legacy_envelope()
    bad = list(legacy["samples"])
    bad[3] = "not-a-sample"
    with pytest.raises(ValueError, match="dict|samples"):
        ch_comp.validate_capture({**legacy, "samples": bad}, role="legacy")


def test_cli_routes_malformed_payload_as_validation_error_not_traceback(
        tmp_path, capsys):
    """CLI catches the controlled ValueError from malformed payloads,
    exits EXIT_VALIDATION, no Traceback in stderr, no --out written."""
    legacy_path = tmp_path / "legacy.json"
    migrated_path = tmp_path / "migrated.json"
    legacy_path.write_text(json.dumps([]))
    migrated_path.write_text(json.dumps({}))
    root = _candidate_root(tmp_path / "next")
    out_path = tmp_path / "comparison.json"
    rc = ch_comp.main(["compare_hydration.py", str(legacy_path),
                        str(migrated_path), "--candidate-root", str(root),
                        "--out", str(out_path)])
    assert rc == ch_comp.EXIT_VALIDATION
    assert not out_path.exists()
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "validation" in err.lower() or "dict" in err.lower()


def test_compare_blocks_when_legacy_side_has_missing_readiness(tmp_path):
    """Readiness check MUST run on BOTH legacy AND migrated. Legacy
    missing readiness blocks the comparison."""
    root = _candidate_root(tmp_path / "next")
    legacy = _legacy_envelope(wait_ms=-1.0, found=False,
                                count=0, first_text=None)
    migrated = _migrated_envelope(root)
    out = ch_comp.compare_captures(legacy, migrated, candidate_root=root)
    assert out["result"] == "blocked/unassessable"
    assert out["passed"] is False
    assert out["unassessable_reason"]
    assert ("legacy" in out["unassessable_reason"].lower()
            or "both" in out["unassessable_reason"].lower())


def test_blocked_result_does_not_expose_fabricated_interactive_metric(
        tmp_path):
    """When blocked, `tree_first_interactive_ms` MUST be null/omitted
    on the blocked side; raw sentinel stays in the input captures
    separately. No `delta_pct` is emitted when blocked."""
    root = _candidate_root(tmp_path / "next")
    migrated = _migrated_envelope(root, wait_ms=-1.0, found=False,
                                   count=0, first_text=None)
    out = ch_comp.compare_captures(_legacy_envelope(), migrated,
                                     candidate_root=root)
    assert out["result"] == "blocked/unassessable"
    m_metrics = out["migrated"]["metrics"]
    assert m_metrics.get(INTERACTIVE) in (None, "", "null") or \
        INTERACTIVE not in m_metrics
    assert "delta_pct" not in out
    assert "raw_captures" not in out["legacy"]
    assert "raw_captures" not in out["migrated"]


def test_blocked_result_still_keeps_deterministic_artifact_shape(tmp_path):
    """Blocked artifact still carries schema, captured_at, threshold,
    unassessable_reason, and per-side numeric first_paint + dcl.
    The interaction metric is null/absent."""
    root = _candidate_root(tmp_path / "next")
    migrated = _migrated_envelope(root, wait_ms=-1.0, found=False,
                                   count=0, first_text=None)
    out = ch_comp.compare_captures(_legacy_envelope(), migrated,
                                     candidate_root=root)
    assert out["schema"] == COMP_SCHEMA
    assert out["captured_at"].endswith("Z")
    assert out["threshold"] == 0.10
    assert out["unassessable_reason"]
    assert out["migrated"]["metrics"]["server_shell.first_paint_ms"] > 0
    assert out["migrated"]["metrics"]["server_shell.dom_content_loaded_ms"] > 0
    assert (out["migrated"]["metrics"].get(INTERACTIVE) is None
            or INTERACTIVE not in out["migrated"]["metrics"])


def test_cli_blocked_with_legacy_missing_readiness_returns_nonzero(tmp_path):
    """CLI path: legacy missing readiness → EXIT_BLOCKED, artifact
    has `result == "blocked/unassessable"` and no fabricated
    interaction metric."""
    rc, out_path = _cli_main(
        tmp_path,
        legacy=_legacy_envelope(wait_ms=-1.0, found=False,
                                  count=0, first_text=None))
    assert rc == ch_comp.EXIT_BLOCKED
    doc = json.loads(out_path.read_text())
    assert doc["result"] == "blocked/unassessable"
    assert (doc["migrated"]["metrics"].get(INTERACTIVE) is None
            or INTERACTIVE not in doc["migrated"]["metrics"])


# ---------------------------------------------------------------------------
# Parent-review hardening: capture's recorded `candidate_root` is
# path-bound provenance, not just a hash. The comparator MUST require
# it to be present, a non-empty string, and equal to the resolved
# `--candidate-root` path. This closes a stale-hash loophole where a
# capture recorded against a different root could still pass the
# on-disk sha check.
# ---------------------------------------------------------------------------


_MUTATIONS = {
    "missing": lambda m, _tp: {k: v for k, v in m.items()
                                if k != "candidate_root"},
    "non_string": lambda m, _tp: {**m, "candidate_root": 42},
    "different_path": lambda m, tp: {**m, "candidate_root":
        str(_candidate_root(tp / "other-root"))},
    "relative_path": lambda m, _tp: {**m, "candidate_root":
        "./not-resolved"},
    "empty_string": lambda m, _tp: {**m, "candidate_root": ""},
}


@pytest.mark.parametrize("label", list(_MUTATIONS.keys()))
def test_validate_capture_rejects_mismatched_candidate_root_path(
        label, tmp_path):
    """Recorded `candidate_root` MUST be a non-empty string AND
    equal to the resolved `--candidate-root` path. Any deviation
    (missing, non-string, different absolute path, relative path,
    empty string) rejects the capture fail-closed."""
    root = _candidate_root(tmp_path / "next")
    migrated = _migrated_envelope(root)
    bad = _MUTATIONS[label](migrated, tmp_path)
    with pytest.raises(ValueError,
                       match="candidate_root|migrated.*root|root.*path"):
        ch_comp.validate_capture(bad, role="migrated",
                                  candidate_root=root)


def test_validate_capture_rejects_candidate_root_path_with_symlink_resolution(
        tmp_path):
    """Even when a candidate_root path resolves to the same
    directory, the recorded string must match the resolved string
    exactly (no relative-path acceptance)."""
    root = _candidate_root(tmp_path / "next")
    migrated = _migrated_envelope(root)
    # Recorded path uses a non-canonical spelling; resolution would
    # normalise it. The comparator MUST reject the mismatch.
    bad = {**migrated, "candidate_root": str(root) + "/./"}
    with pytest.raises(ValueError, match="candidate_root|resolved|path"):
        ch_comp.validate_capture(bad, role="migrated",
                                  candidate_root=root)


# ---------------------------------------------------------------------------
# Parent-review hardening: the comparator must re-check the SAME two
# structural identity conditions that `capture_hydration.validate_candidate_root`
# enforces (non-empty `_next/static/` tree + `index.html` referencing
# `/_next/static/`). A hand-crafted `build=migrated` artifact pointing
# at a legacy root padded with an empty `_next/static/` directory must
# be rejected at the comparator, exactly as `--role migrated` would
# reject it at capture time. The path-bound root check stays.
# ---------------------------------------------------------------------------


def _build_migrated_envelope_for(root: Path) -> dict:
    """Build a migrated envelope whose recorded `candidate_root` and
    `candidate_index_sha256` already match `root` — so the only
    remaining rejection path is the structural identity checks."""
    sha = hashlib.sha256((root / "index.html").read_bytes()).hexdigest()
    return {
        "schema": MIGRATED_SCHEMA, "captured_at": "2026-01-01T00:00:00Z",
        "target_url": "http://127.0.0.1:9000/index.html", "iterations": 10,
        "build": "migrated", "candidate_root": str(root.resolve()),
        "candidate_index_sha256": sha, "static_dir_present": True,
        "dom_marker_selector": '#tree-view[data-state="ready"]',
        "provenance": _provenance("taxa.g5-capture.migrated-provenance/1",
                                   "http://127.0.0.1:9000/index.html",
                                   candidate_root=str(root.resolve()),
                                   candidate_index_sha256=sha),
        "samples": _ten_samples(),
    }


def test_validate_capture_rejects_empty_static_tree_in_migrated_root(tmp_path):
    """Comparator must reject a migrated artifact whose candidate root
    has an empty `_next/static/` directory. Root path + recorded
    `candidate_root` + sha256 are all otherwise valid — only the
    structural identity check should fire."""
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "index.html").write_bytes(
        b'<!doctype html><html><body><script src="/_next/static/chunks/main.js">'
        b'</script></body></html>\n')
    (root / "_next" / "static").mkdir(parents=True)  # empty
    migrated = _build_migrated_envelope_for(root)
    with pytest.raises(ValueError,
                       match="empty.*_next/static|_next/static.*file|asset"):
        ch_comp.validate_capture(migrated, role="migrated",
                                  candidate_root=root)


def test_validate_capture_rejects_index_without_next_static_reference_in_migrated_root(
        tmp_path):
    """Comparator must reject a migrated artifact whose `index.html`
    does NOT reference a `/_next/static/` asset. Static directory
    holds files (so the empty-tree check passes) but the index
    itself is arbitrary HTML — the structural identity contract
    closes this loophole too."""
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "index.html").write_bytes(
        b"<!doctype html><html><body>arbitrary legacy page</body></html>\n")
    static_dir = root / "_next" / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "chunks").mkdir()
    (static_dir / "chunks" / "main.js").write_bytes(b"// js")
    migrated = _build_migrated_envelope_for(root)
    with pytest.raises(ValueError,
                       match="index.html.*_next/static|reference.*_next"):
        ch_comp.validate_capture(migrated, role="migrated",
                                  candidate_root=root)


def test_cli_does_not_write_report_for_empty_static_tree_in_migrated_root(
        tmp_path, capsys):
    """CLI path: empty `_next/static/` → no `--out` written, no
    Traceback, controlled stderr diagnostic."""
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "index.html").write_bytes(
        b'<!doctype html><html><body><script src="/_next/static/chunks/main.js">'
        b'</script></body></html>\n')
    (root / "_next" / "static").mkdir(parents=True)
    migrated = _build_migrated_envelope_for(root)
    legacy_path = tmp_path / "legacy.json"
    migrated_path = tmp_path / "migrated.json"
    out_path = tmp_path / "comparison.json"
    legacy_path.write_text(json.dumps(_legacy_envelope()))
    migrated_path.write_text(json.dumps(migrated))
    rc = ch_comp.main(["compare_hydration.py", str(legacy_path),
                        str(migrated_path),
                        "--candidate-root", str(root),
                        "--out", str(out_path)])
    assert rc == ch_comp.EXIT_VALIDATION
    assert not out_path.exists()
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert ("empty" in err.lower() or "_next/static" in err.lower()
            or "asset" in err.lower())


def test_cli_does_not_write_report_for_index_without_next_static_reference(
        tmp_path, capsys):
    """CLI path: index without `/_next/static/` reference → no `--out`
    written, no Traceback, controlled stderr diagnostic."""
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "index.html").write_bytes(
        b"<!doctype html><html><body>arbitrary legacy page</body></html>\n")
    static_dir = root / "_next" / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "chunks").mkdir()
    (static_dir / "chunks" / "main.js").write_bytes(b"// js")
    migrated = _build_migrated_envelope_for(root)
    legacy_path = tmp_path / "legacy.json"
    migrated_path = tmp_path / "migrated.json"
    out_path = tmp_path / "comparison.json"
    legacy_path.write_text(json.dumps(_legacy_envelope()))
    migrated_path.write_text(json.dumps(migrated))
    rc = ch_comp.main(["compare_hydration.py", str(legacy_path),
                        str(migrated_path),
                        "--candidate-root", str(root),
                        "--out", str(out_path)])
    assert rc == ch_comp.EXIT_VALIDATION
    assert not out_path.exists()
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert ("index.html" in err.lower() or "_next/static" in err.lower()
            or "reference" in err.lower())


# ---------------------------------------------------------------------------
# Parent-review hardening: bool/int typing + iteration index contract.
#
# Python bool is an int subclass: `_is_finite_positive(True)` would
# currently accept True as 1.0 ms, and `_is_finite_sentinel_wait(True)`
# would accept True as 0.0 ms. `_readiness_all_found` accepts
# `found=1`/`found="false"` as truthy and `count=True` as a positive
# int. The `wait=-1.0` sentinel is only valid when the marker is
# MISSING — `found=True` + `wait=-1.0` is contradictory and must
# fail closed. Sample `iteration` fields must equal their zero-based
# position 0..9 (the capture producer emits this exact sequence).
# ---------------------------------------------------------------------------


# --- bool rejection in numeric fields ----------------------------------


@pytest.mark.parametrize("path,value", [
    (["paint", "first_paint_ms"], True),
    (["paint", "first_paint_ms"], False),
    (["navigation", "dom_content_loaded_ms"], True),
    (["navigation", "dom_content_loaded_ms"], False),
    (["dom_marker", "wait_ms"], True),
    (["dom_marker", "wait_ms"], False),
    (["dom_marker", "count"], True),
    (["dom_marker", "count"], False),
])
def test_validate_capture_rejects_bool_in_numeric_fields(path, value, tmp_path):
    """Booleans MUST NOT be accepted as numeric fields. Python bool
    is an int subclass; without explicit rejection, `True` would
    silently pass as 1 ms and `False` as 0 ms."""
    root = _candidate_root(tmp_path / "next")
    m = _migrated_envelope(root)
    samples = [dict(s) for s in m["samples"]]
    cursor = samples[3]
    for k in path[:-1]:
        cursor[k] = dict(cursor[k])
        cursor = cursor[k]
    cursor[path[-1]] = value
    with pytest.raises(ValueError, match="bool|finite|positive|non-negative"):
        ch_comp.validate_capture({**m, "samples": samples},
                                  role="migrated", candidate_root=root)


# --- found=True with wait=-1 sentinel is contradictory -----------------


def test_validate_capture_rejects_found_true_with_wait_sentinel(tmp_path):
    """`wait=-1.0` is the documented absent-marker sentinel. When
    `found=True` the marker WAS observed, so a sentinel wait is
    contradictory. Must fail closed at validation."""
    root = _candidate_root(tmp_path / "next")
    m = _migrated_envelope(root)
    samples = [dict(s) for s in m["samples"]]
    samples[3]["dom_marker"] = dict(samples[3]["dom_marker"])
    samples[3]["dom_marker"]["found"] = True
    samples[3]["dom_marker"]["count"] = 1
    samples[3]["dom_marker"]["wait_ms"] = -1.0
    with pytest.raises(ValueError,
                       match="found.*true.*wait|sentinel.*wait|contradictory"):
        ch_comp.validate_capture({**m, "samples": samples},
                                  role="migrated", candidate_root=root)


# --- documented missing-marker behavior preserved ----------------------


def test_validate_capture_accepts_documented_missing_marker_sentinel(tmp_path):
    """`found=False`, `count=0`, `wait=-1` is the documented
    absent-marker shape. It MUST pass validation (and be caught
    later by the readiness check as `blocked/unassessable`, not
    as malformed)."""
    root = _candidate_root(tmp_path / "next")
    m = _migrated_envelope(root)
    samples = [dict(s) for s in m["samples"]]
    for s in samples:
        s["dom_marker"] = dict(s["dom_marker"])
        s["dom_marker"]["found"] = False
        s["dom_marker"]["count"] = 0
        s["dom_marker"]["wait_ms"] = -1.0
    # Validation MUST succeed; the readiness block is compare_captures' job.
    ch_comp.validate_capture({**m, "samples": samples},
                              role="migrated", candidate_root=root)


# --- readiness_all_found type strictness -------------------------------


@pytest.mark.parametrize("found,count,expected", [
    (1, 1, False),            # found=1 is truthy but not is True
    (0, 1, False),            # found=0 is falsy
    ("true", 1, False),       # found="true" is truthy but not is True
    (True, True, False),      # count=True is truthy but not type(count) is int
    (True, "1", False),       # count="1" is truthy but not type(count) is int
    (True, -1, False),        # count=-1 is int but not > 0
    (True, 0, False),        # count=0 is int but not > 0
])
def test_readiness_all_found_rejects_non_bool_or_non_int(found, count,
                                                          expected):
    """`_readiness_all_found` requires `found is True` (not
    truthy) and `type(count) is int` with count > 0."""
    samples = [{"dom_marker": {"found": found, "count": count}}]
    assert ch_comp._readiness_all_found({"samples": samples}) is expected


# --- iteration index contract ------------------------------------------


@pytest.mark.parametrize("mutation,match", [
    ("wrong_index", "iteration|0\\.\\.9|zero-based"),
    ("duplicate", "duplicate|iteration"),
    ("missing", "iteration|missing"),
    ("out_of_order", "iteration|out.of.order|sequential"),
])
def test_validate_capture_rejects_bad_iteration_indices(mutation, match,
                                                        tmp_path):
    """Each sample's `iteration` MUST equal its zero-based position
    0..9. The capture producer emits this exact sequence, so
    duplicates / missing / out-of-order must fail closed."""
    root = _candidate_root(tmp_path / "next")
    m = _migrated_envelope(root)
    samples = [dict(s) for s in m["samples"]]
    if mutation == "wrong_index":
        samples[3]["iteration"] = 5
    elif mutation == "duplicate":
        samples[3]["iteration"] = 2  # duplicates sample[2]
    elif mutation == "missing":
        del samples[3]["iteration"]
    elif mutation == "out_of_order":
        # Swap two samples
        samples[3], samples[4] = samples[4], samples[3]
        # samples[3] now has iteration=4 (out of position 3), samples[4] has iteration=3
    with pytest.raises(ValueError, match=match):
        ch_comp.validate_capture({**m, "samples": samples},
                                  role="migrated", candidate_root=root)
