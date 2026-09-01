#!/usr/bin/env python
"""Raw Playwright legacy collector (G5 chain child).

Exactly TEN browser samples against a caller-provided controlled target
URL; per-sample navigation/paint/DOM-marker/console + Chromium/
Playwright/environment provenance; in-memory + raw JSON written
atomically; fail-closed on iteration failure. Out of scope (later
chain children): Lighthouse, G5 launcher invocation, parity-reports
emission, baseline/candidate comparison. Exit codes: 0/2/10.
"""
from __future__ import annotations

import argparse, datetime as _dt, hashlib, json, os, platform, re, shutil, sys, time, uuid
from pathlib import Path
from typing import Any, Protocol


SCHEMA = "taxa.g5-capture.legacy/1"
PROVENANCE_SCHEMA = "taxa.g5-capture.legacy-provenance/1"
PUBLICATION_SCHEMA = "taxa.g5-publication.evidence-manifest/1"
ITERATIONS = 10
# G5 readiness contract: target the controlled G3 fixture's dynamic
# readiness marker (`#tree-view[data-state="ready"]`) flipped by
# `web/tree.js` after first paint. The legacy static selector
# (`#tree-view [data-taxon-id]`) was used by the pre-G3 collector and
# never matched the controlled runtime.
DEFAULT_DOM_MARKER_SELECTOR = '#tree-view[data-state="ready"]'
EXIT_OK, EXIT_USAGE, EXIT_FAILURE = 0, 2, 10


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class BrowserAdapter(Protocol):
    """Pluggable browser seam. Real adapter wraps Playwright sync API;
    tests inject a deterministic subclass (no Chromium required)."""
    def chromium_provenance(self) -> dict: ...
    def playwright_provenance(self) -> dict: ...
    def run_iteration(self, *, target_url: str, dom_marker_selector: str,
                      iteration_index: int) -> dict: ...


def collect_raw_samples(
    *, target_url: str, browser_adapter: BrowserAdapter,
    iterations: int = ITERATIONS,
    dom_marker_selector: str = DEFAULT_DOM_MARKER_SELECTOR,
) -> dict:
    """Run exactly `iterations` raw samples. Fail-closed: any iteration
    exception propagates verbatim and NO partial result is returned."""
    if iterations != ITERATIONS:
        raise ValueError(f"iterations must be {ITERATIONS} (G5 contract); got {iterations!r}")
    if not target_url:
        raise ValueError("target_url must be a non-empty string")
    if not dom_marker_selector:
        raise ValueError("dom_marker_selector must be a non-empty string")
    samples: list[dict] = []
    for i in range(iterations):
        s = browser_adapter.run_iteration(
            target_url=target_url, dom_marker_selector=dom_marker_selector,
            iteration_index=i)
        s["iteration"] = i
        s.setdefault("captured_at", _now_iso())
        samples.append(s)
    provenance = {
        "schema": PROVENANCE_SCHEMA,
        "chromium": browser_adapter.chromium_provenance(),
        "playwright": browser_adapter.playwright_provenance(),
        "environment": {"python_version": platform.python_version(),
                        "platform": platform.platform(),
                        "captured_at_iso": _now_iso()},
        "target_url": target_url, "iterations": iterations,
    }
    return {
        "schema": SCHEMA, "captured_at": _now_iso(),
        "target_url": target_url, "iterations": iterations,
        "dom_marker_selector": dom_marker_selector,
        "provenance": provenance, "samples": samples,
    }


def write_result(result: dict, out_path: Path) -> None:
    """Atomic sibling-tmp write so a mid-write failure cannot corrupt
    an existing --out file."""
    tmp = out_path.with_name(f"{out_path.name}.tmp-{os.getpid()}-{id(out_path)}")
    tmp.write_text(json.dumps(result, indent=2), encoding="utf-8")
    tmp.replace(out_path)


# --- G5 publication child A (deterministic, pure, no-I/O plan) -----------
def _plan_entry(kind, path, payload, iteration=None):
    encoded = json.dumps(payload, indent=2, sort_keys=True,
                         ensure_ascii=False).encode("utf-8")
    entry = {"kind": kind, "path": path, "bytes": len(encoded),
             "sha256": hashlib.sha256(encoded).hexdigest(),
             "canonical_json": encoded.decode("utf-8")}
    if iteration is not None:
        entry["iteration"] = iteration
    return entry


def _require(cond, msg):
    if not cond:
        raise ValueError(msg)


def _validate_raws(values, *, kind):
    _require(isinstance(values, list),
             f"{kind} raws must be a list; got {type(values).__name__}")
    _require(len(values) == ITERATIONS,
             f"{kind} raws must contain exactly {ITERATIONS} entries; got {len(values)}")
    for i, v in enumerate(values):
        _require(isinstance(v, dict),
                 f"{kind} raws[{i}] must be a dict; got {type(v).__name__}")


def _validate_manifest_snapshot(m):
    _require(isinstance(m, dict), f"manifest_snapshot must be a dict; got {type(m).__name__}")
    _require(isinstance(m.get("schema"), str), "manifest_snapshot.schema must be a string")
    _require(isinstance(m.get("entries"), list), "manifest_snapshot.entries must be a list")


_HYDRATION_KEYS = ("captured_at", "build", "route",
                   "server_shell", "client_render", "console_warnings")
_HYDRATION_TYPES = {"server_shell": dict, "client_render": dict, "console_warnings": list}


def _validate_legacy_hydration(h):
    _require(isinstance(h, dict),
             f"legacy_hydration_metadata must be a dict; got {type(h).__name__}")
    for key in _HYDRATION_KEYS:
        _require(key in h, f"legacy_hydration_metadata missing required key {key!r}")
    for key, typ in _HYDRATION_TYPES.items():
        _require(isinstance(h[key], typ),
                 f"legacy_hydration_metadata.{key} must be a {typ.__name__}")


def plan_evidence_publication(
    *, playwright_raws, lighthouse_raws,
    manifest_snapshot, legacy_hydration_metadata,
):
    """Deterministic, pure, no-I/O plan for G5 evidence publication.

    Accepts exactly 10 PW + 10 LH raws, a G4 manifest snapshot, and valid
    legacy hydration metadata. Returns the canonical relative-path plan.
    Does NOT touch the filesystem (child B executes the plan).
    """
    _validate_raws(playwright_raws, kind="playwright")
    _validate_raws(lighthouse_raws, kind="lighthouse")
    _validate_manifest_snapshot(manifest_snapshot)
    _validate_legacy_hydration(legacy_hydration_metadata)
    files = [_plan_entry("playwright", f"raw/playwright/iter-{i:02d}.json", s, i)
             for i, s in enumerate(playwright_raws)]
    files += [_plan_entry("lighthouse", f"raw/lighthouse/iter-{i:02d}.json", lhr, i)
              for i, lhr in enumerate(lighthouse_raws)]
    files.append(_plan_entry("manifest_snapshot", "raw/manifest-snapshot.json",
                             manifest_snapshot))
    files.append(_plan_entry("legacy_hydration", "raw/legacy-hydration.json",
                             legacy_hydration_metadata))
    return {"schema": PUBLICATION_SCHEMA, "files": files}


# --- G5 publication child B (atomic filesystem publisher) -------------
_PUBLISH_BACKUP_SUFFIX = ".bak"


def _safe_rmtree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def _default_publish_write_bytes(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def publish_evidence_atomic(
    plan: dict, target_dir,
    *, write_fn=None, rename_fn=None, backup_suffix: str = _PUBLISH_BACKUP_SUFFIX,
):
    """Publish a G5 evidence plan atomically to ``target_dir``.

    Validates the plan shape, stages files into a sibling staging
    directory, recomputes/validates staged sha256/size/path-set against
    the plan, then atomically swaps the staging directory onto
    ``target_dir`` with backup/restore semantics.

    Failure contract: any failure during staging, validation, or the
    final rename preserves the prior ``target_dir`` byte-for-byte and
    leaves no tmp/bak residue, EXCEPT when restoration of the prior
    output itself fails — in that case the backup is left on disk for
    human recovery and the exception propagates.
    """
    target = Path(target_dir)
    files = _validate_publication_plan(plan)
    _require(not target.is_file(),
             f"target_dir must not be an existing file: {target}")
    actual_write = write_fn or _default_publish_write_bytes
    actual_rename = rename_fn or os.replace
    staging = _stage_and_validate_publish(target, files, actual_write)
    backup: Path | None = None
    if target.is_dir():
        backup = target.with_name(target.name + backup_suffix)
        if backup.exists():
            _safe_rmtree(staging)
            raise FileExistsError(f"backup path already exists: {backup}")
        try:
            actual_rename(target, backup)
        except Exception:
            _safe_rmtree(staging)
            raise
    try:
        actual_rename(staging, target)
    except Exception:
        _safe_rmtree(staging)
        if backup is not None:
            try:
                actual_rename(backup, target)
            except Exception:
                raise  # leave backup residue for human recovery
            backup = None  # restored successfully; nothing to clean later
        raise
    if backup is not None:
        try:
            if backup.is_dir():
                shutil.rmtree(backup)
            else:
                backup.unlink()
        except OSError:
            pass


def _stage_and_validate_publish(target: Path, files: list, write_fn) -> Path:
    staging = target.with_name(
        target.name + f".staging-{os.getpid()}-{uuid.uuid4().hex[:12]}")
    _safe_rmtree(staging)
    staging.mkdir(exist_ok=False)
    try:
        for f in files:
            dest = staging / f["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            write_fn(dest, f["canonical_json"].encode("utf-8"))
        _validate_publish_staging(staging, files)
    except Exception:
        _safe_rmtree(staging)
        raise
    return staging


def _validate_publication_plan(plan) -> list:
    _require(isinstance(plan, dict),
             f"plan must be a dict; got {type(plan).__name__}")
    _require(plan.get("schema") == PUBLICATION_SCHEMA,
             f"plan.schema must be {PUBLICATION_SCHEMA}; got {plan.get('schema')!r}")
    files = plan.get("files")
    _require(isinstance(files, list) and files,
             f"plan.files must be a non-empty list; got {type(files).__name__}")
    sha_re = re.compile(r"[0-9a-f]{64}")
    seen: set = set()
    for i, f in enumerate(files):
        _require(isinstance(f, dict),
                 f"plan.files[{i}] must be a dict; got {type(f).__name__}")
        for key in ("kind", "path", "bytes", "sha256", "canonical_json"):
            _require(key in f, f"plan.files[{i}] missing required key {key!r}")
        path = f["path"]
        _require(isinstance(path, str) and path and not path.startswith("/"),
                 f"plan.files[{i}].path must be a non-empty relative string")
        _require(".." not in Path(path).parts,
                 f"plan.files[{i}].path must not contain '..' segments: {path!r}")
        _require(isinstance(f["bytes"], int) and f["bytes"] >= 0,
                 f"plan.files[{i}].bytes must be a non-negative int; got {f['bytes']!r}")
        _require(isinstance(f["sha256"], str) and sha_re.fullmatch(f["sha256"]),
                 f"plan.files[{i}].sha256 must be a 64-char hex string; got {f['sha256']!r}")
        _require(path not in seen,
                 f"plan.files[{i}].path duplicates an earlier entry: {path!r}")
        seen.add(path)
    return files


def _validate_publish_staging(staging: Path, files: list) -> None:
    expected = {f["path"] for f in files}
    actual = {str(p.relative_to(staging))
              for p in staging.rglob("*") if p.is_file()}
    _require(actual == expected,
             f"staged path set mismatch; extra={actual - expected} "
             f"missing={expected - actual}")
    for f in files:
        data = (staging / f["path"]).read_bytes()
        _require(len(data) == f["bytes"],
                 f"staged bytes mismatch for {f['path']!r}: "
                 f"expected {f['bytes']}, got {len(data)}")
        _require(hashlib.sha256(data).hexdigest() == f["sha256"],
                 f"staged sha256 mismatch for {f['path']!r}")


class PlaywrightBrowserAdapter:
    """Real Chromium adapter. Lazy-imports playwright so the module is
    importable without it installed (CI uses a test fake)."""

    def __init__(self, *, headless: bool = True) -> None:
        self._headless: bool = headless
        self._pw: Any = None  # lazy: populated by _pw_obj() on first use
        self._cv: str | None = None
        self._ce: str | None = None

    def _pw_obj(self):
        if self._pw is None:
            try:
                from playwright.sync_api import sync_playwright  # type: ignore
            except ImportError as e:
                raise RuntimeError(
                    f"playwright not installed: {e}. Install with "
                    "`pip install playwright && playwright install chromium`."
                ) from e
            self._pw = sync_playwright()
        return self._pw

    def chromium_provenance(self) -> dict:
        if self._cv is None:
            b = self._pw_obj().chromium.launch(headless=self._headless)
            try:
                self._cv, self._ce = b.version, self._pw.chromium.executable_path
            finally:
                b.close()
        return {"version": self._cv or "unknown", "executable_path": self._ce}

    def playwright_provenance(self) -> dict:
        try:
            import playwright  # type: ignore
            return {"version": playwright.__version__}
        except ImportError:
            return {"version": "unknown"}

    def run_iteration(self, *, target_url, dom_marker_selector, iteration_index):
        browser = self._pw_obj().chromium.launch(headless=self._headless)
        try:
            page = browser.new_page()
            msgs: list[dict] = []
            page.on("console", lambda m: msgs.append({"type": m.type, "text": m.text}))
            resp = page.goto(target_url, wait_until="domcontentloaded")
            nav = page.evaluate(
                "() => { const e = performance.getEntriesByType('navigation')[0];"
                "return e ? {rs:e.responseStart,dcl:e.domContentLoadedEventEnd,"
                "le:e.loadEventEnd,rc:e.redirectCount} : null; }") or {}
            paint = page.evaluate(
                "() => { const o={};"
                "for(const e of performance.getEntriesByType('paint')){"
                " if(e.name==='first-paint')o.fp=e.startTime;"
                " if(e.name==='first-contentful-paint')o.fcp=e.startTime;}"
                "return o; }")
            try:
                # Honest elapsed-readiness metric: wall-clock time the
                # adapter waited for the G5 readiness marker
                # (`#tree-view[data-state="ready"]`) to become visible
                # after `goto`. Recorded inside the adapter boundary so
                # the candidate-vs-baseline joiner can diff a real
                # per-sample delta instead of a hard-coded 0.0.
                _wait_t0 = time.monotonic()
                page.wait_for_selector(dom_marker_selector, timeout=5000)
                wait_ms = (time.monotonic() - _wait_t0) * 1000.0
                loc = page.locator(dom_marker_selector)
                cnt = loc.count()
                dom = {"selector": dom_marker_selector, "found": bool(cnt),
                       "count": int(cnt),
                       "first_text": loc.first.inner_text() if cnt else None,
                       "wait_ms": wait_ms}
            except Exception:
                dom = {"selector": dom_marker_selector, "found": False,
                       "count": 0, "first_text": None, "wait_ms": -1.0}
            return {"iteration": iteration_index, "captured_at": _now_iso(),
                    "navigation": {
                        "response_start_ms": float(nav.get("rs") or 0.0),
                        "dom_content_loaded_ms": float(nav.get("dcl") or 0.0),
                        "load_event_ms": float(nav.get("le") or 0.0),
                        "redirect_count": int(nav.get("rc") or 0),
                        "status": int(resp.status if resp else 0),
                    },
                    "paint": {"first_paint_ms": paint.get("fp"),
                              "first_contentful_paint_ms": paint.get("fcp")},
                    "dom_marker": dom, "console": list(msgs)}
        finally:
            browser.close()


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="capture_hydration.py",
        description="Raw Playwright legacy collector (G5 child; samples-only).")
    p.add_argument("--target-url", required=True, help="Controlled FastAPI target URL (PR #131).")
    p.add_argument("--out", required=True, help="Path to write the raw JSON result.")
    p.add_argument("--iterations", type=int, default=ITERATIONS,
                   help=f"Must equal {ITERATIONS} (G5 contract).")
    p.add_argument("--dom-marker-selector", default=DEFAULT_DOM_MARKER_SELECTOR)
    p.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing --out.")
    p.add_argument("--browser", default="playwright", choices=("playwright",))
    return p.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    if args.iterations != ITERATIONS:
        sys.stderr.write(f"[capture_hydration] --iterations must be {ITERATIONS} (G5 contract); got {args.iterations}\n")
        return EXIT_USAGE
    out_path = Path(args.out)
    try:
        result = collect_raw_samples(
            target_url=args.target_url, browser_adapter=PlaywrightBrowserAdapter(),
            iterations=args.iterations, dom_marker_selector=args.dom_marker_selector)
    except Exception as e:
        sys.stderr.write(f"[capture_hydration] capture failed (fail-closed; no --out written): {e}\n")
        return EXIT_FAILURE
    if args.dry_run:
        sys.stdout.write(json.dumps(result, indent=2) + "\n")
        return EXIT_OK
    try:
        write_result(result, out_path)
    except OSError as e:
        sys.stderr.write(f"[capture_hydration] cannot write --out: {e}\n")
        return EXIT_FAILURE
    sys.stdout.write(f"[capture_hydration] wrote {len(result['samples'])} raw samples to {out_path}\n")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))