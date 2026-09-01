"""Strict-TDD tests for scripts/capture_hydration.py (G5 raw Playwright
legacy collector). TEN browser samples, per-sample nav/paint/DOM-marker/
console + Chromium/Playwright/env provenance; in-memory + raw JSON;
fail-closed on iteration failure. No Lighthouse, no G5 launcher call,
no parity-reports emission. Hermetic via FakeBrowserAdapter.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.capture_hydration as ch


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "capture_hydration.py"
TARGET_URL = "http://127.0.0.1:8765/"


class FakeBrowserAdapter:
    """Hermetic test double. Records `calls` for fail-closed assertions."""
    def __init__(self, *, raise_on=None, raise_message="synthetic iteration failure"):
        self._raise_on, self._raise_message = raise_on, raise_message
        self.calls: list = []
    def chromium_provenance(self):
        return {"version": "fake-chromium-1.0", "executable_path": "/fake/chromium"}
    def playwright_provenance(self):
        return {"version": "fake-playwright-1.0"}
    def run_iteration(self, *, target_url, dom_marker_selector, iteration_index):
        self.calls.append((target_url, dom_marker_selector, iteration_index))
        if self._raise_on is not None and (iteration_index + 1) == self._raise_on:
            raise RuntimeError(self._raise_message)
        return {
            "iteration": iteration_index, "captured_at": "2026-01-01T00:00:00Z",
            "navigation": {"response_start_ms": 0.0, "dom_content_loaded_ms": 0.0,
                           "load_event_ms": 0.0, "redirect_count": 0, "status": 200},
            "paint": {"first_paint_ms": 0.0, "first_contentful_paint_ms": 0.0},
            "dom_marker": {"selector": dom_marker_selector, "found": True,
                           "count": 1, "first_text": "x", "wait_ms": 0.0},
            "console": [],
        }


def test_module_surface_constants_and_shebang():
    """Public surface + G5 contract constants + script presence + shebang."""
    for name in ("ITERATIONS", "SCHEMA", "PROVENANCE_SCHEMA",
                 "DEFAULT_DOM_MARKER_SELECTOR", "BrowserAdapter",
                 "PlaywrightBrowserAdapter", "collect_raw_samples",
                 "write_result", "main"):
        assert hasattr(ch, name), f"missing public symbol: {name}"
    assert ch.ITERATIONS == 10
    assert ch.SCHEMA == "taxa.g5-capture.legacy/1"
    assert ch.PROVENANCE_SCHEMA == "taxa.g5-capture.legacy-provenance/1"
    assert SCRIPT.is_file()
    assert SCRIPT.read_text(encoding="utf-8").startswith("#!/usr/bin/env python")


def test_collect_envelope_per_sample_schema_provenance_and_selector():
    """CORE: envelope + per-sample sub-block keys + provenance layout +
    custom selector passes through verbatim. The next chain child (G5
    joiner) reads these exact keys, so this test pins the contract."""
    adapter = FakeBrowserAdapter()
    selector = "#custom-marker"
    result = ch.collect_raw_samples(
        target_url=TARGET_URL, browser_adapter=adapter, dom_marker_selector=selector)
    for k in ("schema", "captured_at", "target_url", "iterations",
              "dom_marker_selector", "provenance", "samples"):
        assert k in result
    assert result["schema"] == ch.SCHEMA and result["iterations"] == 10
    assert result["target_url"] == TARGET_URL
    assert result["dom_marker_selector"] == selector
    assert result["captured_at"].endswith("Z")
    assert result["provenance"]["schema"] == ch.PROVENANCE_SCHEMA
    assert [s["iteration"] for s in result["samples"]] == list(range(10))
    for s in result["samples"]:
        for k in ("iteration", "captured_at", "navigation", "paint", "dom_marker", "console"):
            assert k in s
        for k in ("response_start_ms", "dom_content_loaded_ms", "load_event_ms", "redirect_count", "status"):
            assert k in s["navigation"]
        for k in ("first_paint_ms", "first_contentful_paint_ms"):
            assert k in s["paint"]
        for k in ("selector", "found", "count", "first_text", "wait_ms"):
            assert k in s["dom_marker"]
        assert isinstance(s["console"], list)
    p = result["provenance"]
    assert "version" in p["chromium"] and "executable_path" in p["chromium"]
    assert "version" in p["playwright"]
    assert "python_version" in p["environment"] and "platform" in p["environment"]
    assert p["target_url"] == TARGET_URL and p["iterations"] == 10
    assert len(adapter.calls) == 10
    assert all(sel == selector for _, sel, _ in adapter.calls)


def test_collect_iteration_failure_propagates_and_skips_remainder():
    """FAIL-CLOSED CORE: any iteration failure aborts with the same
    exception AND must NOT attempt iterations after the failure."""
    a = FakeBrowserAdapter(raise_on=5, raise_message="synthetic iter-5")
    with pytest.raises(RuntimeError, match="synthetic iter-5"):
        ch.collect_raw_samples(target_url=TARGET_URL, browser_adapter=a)
    assert [c[2] for c in a.calls] == [0, 1, 2, 3, 4]
    b = FakeBrowserAdapter(raise_on=1)
    with pytest.raises(RuntimeError):
        ch.collect_raw_samples(target_url=TARGET_URL, browser_adapter=b)
    assert [c[2] for c in b.calls] == [0]


def test_collect_input_validation():
    """G5 contract locks iterations to 10; target_url and selector
    must be non-empty. Each violation raises ValueError."""
    a = FakeBrowserAdapter()
    with pytest.raises(ValueError, match="10"):
        ch.collect_raw_samples(target_url=TARGET_URL, browser_adapter=a, iterations=5)
    with pytest.raises(ValueError, match="target_url"):
        ch.collect_raw_samples(target_url="", browser_adapter=a)
    with pytest.raises(ValueError, match="dom_marker_selector"):
        ch.collect_raw_samples(
            target_url=TARGET_URL, browser_adapter=a, dom_marker_selector="")


def test_cli_happy_path_dry_run_argparse_and_atomic_write(tmp_path, monkeypatch):
    """Happy CLI path: writes raw JSON to --out AND leaves no .tmp-
    sibling (atomic write contract). --dry-run prints to stdout and
    DOES NOT write --out. Argparse enforces --target-url + --out."""
    monkeypatch.setattr(ch, "PlaywrightBrowserAdapter", lambda: FakeBrowserAdapter())
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = ch.main(["capture_hydration.py", "--target-url", TARGET_URL,
                      "--out", str(tmp_path / "raw.json")])
    assert rc == 0, f"unexpected stderr: {err.getvalue()}"
    loaded = json.loads((tmp_path / "raw.json").read_text())
    assert loaded["schema"] == ch.SCHEMA and loaded["iterations"] == 10
    assert "wrote 10 raw samples" in out.getvalue()
    # Atomic write: no leftover .tmp- siblings.
    assert [p for p in tmp_path.iterdir() if p.name.startswith("raw.json.tmp-")] == []
    # Dry-run.
    dry_path = tmp_path / "dry.json"
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        rc = ch.main(["capture_hydration.py", "--target-url", TARGET_URL,
                      "--out", str(dry_path), "--dry-run"])
    assert rc == 0 and not dry_path.exists()
    # Subprocess argparse: missing flags → non-zero exit + stderr.
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=REPO_ROOT,
        capture_output=True, text=True, check=False)
    assert proc.returncode != 0 and proc.stderr.strip()
    assert "target-url" in proc.stderr.lower() or "out" in proc.stderr.lower()


def test_cli_iteration_failure_is_fail_closed_and_rejects_non_ten(tmp_path, monkeypatch):
    """FAIL-CLOSED CLI: iteration failure must NOT write --out and must
    exit non-zero with a stderr message naming fail-closed.
    --iterations must equal 10; any other value fails closed."""
    fake = FakeBrowserAdapter(raise_on=3, raise_message="synthetic cli iter-3")
    monkeypatch.setattr(ch, "PlaywrightBrowserAdapter", lambda: fake)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
        rc = ch.main(["capture_hydration.py", "--target-url", TARGET_URL,
                      "--out", str(tmp_path / "raw.json")])
    assert rc != 0 and not (tmp_path / "raw.json").exists()
    # --iterations=5 rejection.
    fake = FakeBrowserAdapter()
    monkeypatch.setattr(ch, "PlaywrightBrowserAdapter", lambda: fake)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
        rc = ch.main(["capture_hydration.py", "--target-url", TARGET_URL,
                      "--out", str(tmp_path / "raw2.json"), "--iterations", "5"])
    assert rc != 0 and "10" in err.getvalue()
    assert fake.calls == [], "adapter must not run when --iterations fails"
    assert not (tmp_path / "raw2.json").exists()


def test_module_decoupled_from_launcher_lighthouse_and_parity_reports():
    """Raw collector MUST stay decoupled from the G5 launcher and from
    parity-reports emission. AST-parsed so docstring mentions do not
    false-trigger."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported_modules: list = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
    for mod in imported_modules:
        assert "measure_hydration" not in mod, (
            f"must NOT import {mod} (later chain child owns that joiner)")
        assert "parity" not in mod.lower(), (
            f"must NOT import {mod} (publication is a later chain child)")
        assert "lighthouse" not in mod.lower(), (
            f"must NOT import {mod} (Lighthouse is a separate chain child)")


# Child A — G5 evidence-manifest plan (deterministic, pure, no-I/O).
_PW_BASE = {"captured_at": "2026-09-01T00:00:00Z",
            "navigation": {"response_start_ms": 0.0, "dom_content_loaded_ms": 0.0,
                           "load_event_ms": 0.0, "redirect_count": 0, "status": 200},
            "paint": {"first_paint_ms": 0.0, "first_contentful_paint_ms": 0.0},
            "dom_marker": {"selector": "#tree-view [data-taxon-id]", "found": True,
                           "count": 1, "first_text": "x", "wait_ms": 0.0}, "console": []}
_LH_BASE = {"lighthouseVersion": "12.2.1",
            "userAgent": "Mozilla/5.0 (Fake) Chrome/130.0.0.0",
            "finalUrl": "http://127.0.0.1:8765/",
            "categories": {"performance": {"score": 0.95}, "accessibility": {"score": 0.98},
                           "best-practices": {"score": 0.92}, "seo": {"score": 1.0}}}
_MANIFEST = {"schema": "taxa.g4-capture.manifest/1", "entries": [{
    "url": "http://127.0.0.1:8765/index.html", "path": "index.html",
    "expectedContentSha256": "bb1a2731f4ab7e710d7989c5d5bd17205154155cd18f08e3ffa245c4165ae401",
    "expectedStatus": 200, "expectedDOMMarker": "data-testid=\"g4-probe-marker\""}]}
_HYDRATION = {"captured_at": "2026-08-28T00:00:00Z", "build": "legacy", "route": "/",
              "server_shell": {"first_paint_ms": 80.0, "dom_content_loaded_ms": 100.0},
              "client_render": {"tree_first_paint_ms": 220.0,
                                "tree_first_interactive_ms": 350.0},
              "console_warnings": []}


def _pw(i=0): return {**_PW_BASE, "iteration": i}
def _lh(i=0): return {**_LH_BASE, "iterations": i}
def _all_valid_inputs():
    return {"playwright_raws": [_pw(i) for i in range(10)],
            "lighthouse_raws": [_lh(i) for i in range(10)],
            "manifest_snapshot": _MANIFEST,
            "legacy_hydration_metadata": _HYDRATION}


def test_publication_plan_valid_inputs_yields_22_canonical_file_entries_no_io(tmp_path):
    """22 file entries (10 PW + 10 LH + 1 manifest + 1 hydration);
    path/sha256/bytes/canonical_json/kind per entry; sha256 hashes
    canonical_json; bytes == UTF-8 length; no I/O in tmp_path."""
    assert callable(getattr(ch, "plan_evidence_publication", None))
    pre = sorted(p.name for p in tmp_path.iterdir())
    plan = ch.plan_evidence_publication(**_all_valid_inputs())
    assert pre == sorted(p.name for p in tmp_path.iterdir()), \
        "must NOT touch the filesystem"
    assert plan["schema"] == ch.PUBLICATION_SCHEMA
    files = plan["files"]
    assert isinstance(files, list) and len(files) == 22
    by_kind = {"playwright": [], "lighthouse": [],
               "manifest_snapshot": [], "legacy_hydration": []}
    for f in files:
        by_kind[f["kind"]].append(f)
    assert [len(v) for v in by_kind.values()] == [10, 10, 1, 1]
    sha_re = re.compile(r"[0-9a-f]{64}")
    for f in files:
        for k in ("kind", "path", "bytes", "sha256", "canonical_json"):
            assert k in f
        assert not f["path"].startswith("/") and ".." not in f["path"].split("/")
        assert sha_re.fullmatch(f["sha256"])
        assert isinstance(f["bytes"], int) and f["bytes"] > 0
        encoded = f["canonical_json"].encode("utf-8")
        assert f["sha256"] == hashlib.sha256(encoded).hexdigest()
        assert f["bytes"] == len(encoded)


def test_publication_plan_deterministic_pure_and_unique_paths():
    """Two identical calls → byte-identical plans; inputs not mutated;
    iteration 0..9 + zero-padded iter-00..iter-09 paths."""
    inputs = _all_valid_inputs()
    pw0 = json.loads(json.dumps(inputs["playwright_raws"]))
    lh0 = json.loads(json.dumps(inputs["lighthouse_raws"]))
    ms0 = json.loads(json.dumps(inputs["manifest_snapshot"]))
    h0 = json.loads(json.dumps(inputs["legacy_hydration_metadata"]))
    p1 = ch.plan_evidence_publication(**inputs)
    p2 = ch.plan_evidence_publication(**inputs)
    assert (inputs["playwright_raws"], inputs["lighthouse_raws"],
            inputs["manifest_snapshot"], inputs["legacy_hydration_metadata"]) == (pw0, lh0, ms0, h0)
    b1 = {f["path"]: f["canonical_json"] for f in p1["files"]}
    b2 = {f["path"]: f["canonical_json"] for f in p2["files"]}
    assert b1 == b2, "canonical_json MUST be byte-identical across runs"
    by_kind = {"playwright": [], "lighthouse": []}
    for f in p1["files"]:
        if f["kind"] in by_kind:
            by_kind[f["kind"]].append(f)
    assert [f["iteration"] for f in by_kind["playwright"]] == list(range(10))
    assert [f["iteration"] for f in by_kind["lighthouse"]] == list(range(10))
    assert sorted(f["path"] for f in by_kind["playwright"]) == \
        [f"raw/playwright/iter-{i:02d}.json" for i in range(10)]
    assert sorted(f["path"] for f in by_kind["lighthouse"]) == \
        [f"raw/lighthouse/iter-{i:02d}.json" for i in range(10)]
    assert len({f["path"] for f in p1["files"]}) == 22


def test_publication_plan_wrong_counts_and_malformed_manifest_raise():
    """G5 contract: PW + LH raws must be exactly 10 each (0/9/11 + non-dict
    entries raise). Malformed manifest (missing schema/entries) raises."""
    b = _all_valid_inputs()
    for pw in ([], b["playwright_raws"][:9], b["playwright_raws"] + [_pw(10)]):
        with pytest.raises(ValueError, match="[Pp]laywright"):
            ch.plan_evidence_publication(
                playwright_raws=pw, lighthouse_raws=b["lighthouse_raws"],
                manifest_snapshot=b["manifest_snapshot"],
                legacy_hydration_metadata=b["legacy_hydration_metadata"])
    for lh in ([], b["lighthouse_raws"] + [_lh(10)]):
        with pytest.raises(ValueError, match="[Ll]ighthouse"):
            ch.plan_evidence_publication(
                playwright_raws=b["playwright_raws"], lighthouse_raws=lh,
                manifest_snapshot=b["manifest_snapshot"],
                legacy_hydration_metadata=b["legacy_hydration_metadata"])
    bad_pw = list(b["playwright_raws"]); bad_pw[3] = "not a dict"
    with pytest.raises(ValueError, match="[Pp]laywright"):
        ch.plan_evidence_publication(
            playwright_raws=bad_pw, lighthouse_raws=b["lighthouse_raws"],
            manifest_snapshot=b["manifest_snapshot"],
            legacy_hydration_metadata=b["legacy_hydration_metadata"])
    for bad_manifest in ({"schema": "wrong/1"}, {"entries": []}):
        with pytest.raises(ValueError, match="manifest"):
            ch.plan_evidence_publication(
                playwright_raws=b["playwright_raws"],
                lighthouse_raws=b["lighthouse_raws"],
                manifest_snapshot=bad_manifest,
                legacy_hydration_metadata=b["legacy_hydration_metadata"])


def test_publication_plan_malformed_hydration_metadata_raises():
    """Required keys (captured_at/build/route/server_shell/client_render/
    console_warnings) must all be present; server_shell+client_render must
    be dicts; console_warnings must be a list. Each violation raises."""
    b = _all_valid_inputs()
    for missing in ("captured_at", "build", "route", "server_shell",
                    "client_render", "console_warnings"):
        broken = {**_HYDRATION}; broken.pop(missing)
        with pytest.raises(ValueError, match=missing):
            ch.plan_evidence_publication(
                playwright_raws=b["playwright_raws"],
                lighthouse_raws=b["lighthouse_raws"],
                manifest_snapshot=b["manifest_snapshot"],
                legacy_hydration_metadata=broken)
    for bad_key, bad_val in (("server_shell", "x"), ("client_render", 42),
                              ("console_warnings", "x")):
        broken = {**_HYDRATION, bad_key: bad_val}
        with pytest.raises(ValueError, match=bad_key):
            ch.plan_evidence_publication(
                playwright_raws=b["playwright_raws"],
                lighthouse_raws=b["lighthouse_raws"],
                manifest_snapshot=b["manifest_snapshot"],
                legacy_hydration_metadata=broken)


def test_publication_plan_canonical_json_roundtrips_and_serialisable():
    """canonical_json MUST round-trip to original payload; full plan MUST be
    JSON-serialisable. Non-serialisable raw raises before any partial plan."""
    inputs = _all_valid_inputs()
    plan = ch.plan_evidence_publication(**inputs)
    by_kind = {"playwright": [], "lighthouse": [],
               "manifest_snapshot": [], "legacy_hydration": []}
    for f in plan["files"]:
        by_kind[f["kind"]].append(f)
    for entry, orig in zip(by_kind["playwright"], inputs["playwright_raws"]):
        assert json.loads(entry["canonical_json"]) == orig
    for entry, orig in zip(by_kind["lighthouse"], inputs["lighthouse_raws"]):
        assert json.loads(entry["canonical_json"]) == orig
    assert json.loads(by_kind["manifest_snapshot"][0]["canonical_json"]) == inputs["manifest_snapshot"]
    assert json.loads(by_kind["legacy_hydration"][0]["canonical_json"]) == inputs["legacy_hydration_metadata"]
    assert json.loads(json.dumps(plan, sort_keys=True)) == plan
    bad = list(inputs["playwright_raws"]); bad[2] = {"iteration": 2, "blob": b"\x00"}
    with pytest.raises((ValueError, TypeError)):
        ch.plan_evidence_publication(
            playwright_raws=bad, lighthouse_raws=inputs["lighthouse_raws"],
            manifest_snapshot=inputs["manifest_snapshot"],
            legacy_hydration_metadata=inputs["legacy_hydration_metadata"])