"""G5 hydration comparator — joins a raw legacy capture against a raw
migrated (candidate) capture and emits a deterministic comparison
artifact with three explicit outcomes: ``passed`` (±10 % inclusive),
``threshold_failed`` (any metric outside ±10 %), and
``blocked/unassessable`` (readiness marker missing on EITHER side,
on-disk sha mismatch, static dir missing, role mislabel, non-10
samples, non-finite metrics, or malformed payloads).

Fail-closed contract: every invalid input raises ``ValueError`` and
the comparison artifact is NOT emitted. Legacy byte contracts of
``measure_hydration.py`` and ``capture_hydration.py`` are preserved
unchanged — this script reads their raw artifacts.

Exit codes: 0 (passed), 2 (usage), 4 (threshold_failed),
5 (blocked/unassessable), 10 (validation). Deterministic except
``captured_at``. No bundle-size result / claim is emitted.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import hashlib
import json
import math
import os
import statistics
import sys
from pathlib import Path
from typing import Any

COMP_SCHEMA = "taxa.g5-hydration-comparison/1"
LEGACY_SCHEMA = "taxa.g5-capture.legacy/1"
MIGRATED_SCHEMA = "taxa.g5-capture.migrated/1"
LEGACY_BUILD_LABEL = "legacy"
MIGRATED_BUILD_LABEL = "migrated"
THRESHOLD = 0.10
ITERATIONS = 10
METRIC_FIRST_PAINT = "server_shell.first_paint_ms"
METRIC_DCL = "server_shell.dom_content_loaded_ms"
METRIC_INTERACTIVE = "client_render.tree_first_interactive_ms"
METRIC_KEYS = (METRIC_FIRST_PAINT, METRIC_DCL, METRIC_INTERACTIVE)
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_THRESHOLD_FAILED = 4
EXIT_BLOCKED = 5
EXIT_VALIDATION = 10


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _is_finite_positive(value: Any) -> bool:
    """True iff `value` is a finite positive real number.

    Booleans are explicitly rejected: in Python, ``bool`` is an
    ``int`` subclass, so ``isinstance(True, (int, float))`` is True
    and ``True`` would silently pass as 1 ms. Per the parent-review
    typing contract, a capture that emits ``True`` for a timing
    field is malformed.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    f = float(value)
    return math.isfinite(f) and f > 0


def _is_finite_nonnegative(value: Any) -> bool:
    """True iff `value` is a finite non-negative real number (incl. 0)."""
    if not isinstance(value, (int, float)):
        return False
    f = float(value)
    return math.isfinite(f) and f >= 0


def _is_finite_sentinel_wait(value: Any) -> bool:
    """True iff `value` is a finite non-negative real number OR the
    documented ``-1.0`` absent-marker sentinel.

    Booleans are explicitly rejected (same rationale as
    ``_is_finite_positive``: ``bool`` is an ``int`` subclass).
    The legacy / migrated capture contract pins ``wait_ms: -1.0``
    as the per-sample sentinel for "dom_marker not observed within
    timeout". Validation accepts the sentinel so the comparator can
    detect it explicitly and emit ``blocked/unassessable`` rather
    than coercing it into a valid metric.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    f = float(value)
    if f == -1.0:
        return True
    return math.isfinite(f) and f >= 0


def _is_strict_true(value: Any) -> bool:
    """True iff `value` is exactly the Python boolean True (not
    truthy, not ``1``, not ``"true"``).

    Centralises the strict-identity check required by the parent-review
    typing contract. Uses ``type(value) is bool and value`` instead
    of ``value is True`` to satisfy both the contract (exact identity)
    and the lint rule against identity comparisons with literals.
    """
    return type(value) is bool and value


def _validate_legacy_envelope(capture: dict) -> None:
    """Shared per-role shape validation. Fail-closed: any deviation
    raises ``ValueError`` and the comparator never claims a result.

    Order matters: a top-level dict check runs first so a list /
    scalar / None payload never reaches a dict-key access; nested
    ``paint`` / ``navigation`` / ``dom_marker`` are checked for
    ``isinstance(dict)`` BEFORE any ``.get`` call so a malformed
    nested value (e.g., a list) raises a controlled ``ValueError``
    instead of ``AttributeError``.
    """
    _require(isinstance(capture, dict),
             f"capture must be a dict; got {type(capture).__name__}")
    _require(isinstance(capture.get("schema"), str),
             f"capture.schema must be a string; got {type(capture.get('schema')).__name__}")
    _require(capture.get("iterations") == ITERATIONS,
             f"capture.iterations must be {ITERATIONS}; got {capture.get('iterations')!r}")
    samples = capture.get("samples")
    _require(isinstance(samples, list),
             f"capture.samples must be a list; got {type(samples).__name__}")
    samples_list: list[Any] = samples  # type: ignore[assignment]
    n_samples = len(samples_list)
    _require(n_samples == ITERATIONS,
             f"capture.samples must contain exactly {ITERATIONS} entries; "
             f"got {n_samples}")
    for i, s in enumerate(samples_list):
        _require(isinstance(s, dict),
                 f"samples[{i}] must be a dict; got {type(s).__name__}")
        # Iteration index contract (parent review): the capture
        # producer emits iteration 0..9 in zero-based order. Each
        # sample's `iteration` MUST equal its zero-based position
        # so duplicates, missing entries, and out-of-order samples
        # fail closed before any downstream arithmetic.
        _require("iteration" in s,
                 f"samples[{i}] missing required key 'iteration'")
        iter_value = s["iteration"]
        _require(iter_value == i,
                 f"samples[{i}].iteration must equal its zero-based "
                 f"position {i} (capture producer emits 0..9 in order); "
                 f"got {iter_value!r}")
        for key in ("paint", "navigation", "dom_marker"):
            _require(key in s,
                     f"samples[{i}] missing required key {key!r}")
            value = s[key]
            _require(isinstance(value, dict),
                     f"samples[{i}].{key} must be a dict; "
                     f"got {type(value).__name__}")
        paint = s["paint"]
        navigation = s["navigation"]
        dom_marker = s["dom_marker"]
        # `first_paint_ms` is required as a KEY. An explicit JSON
        # null (`None`) is the migrated capture's documented
        # "unavailable metric" sentinel — the field is present
        # but holds null because the underlying metric could not
        # be captured for that sample. The validator MUST NOT
        # conflate the null sentinel with a malformed value:
        #
        #   * explicit null  → accepted (caller decides how to
        #                       represent it in the artifact);
        #   * any other non-finite-positive value (bool, string,
        #     NaN, zero, negative) → fail closed here;
        #   * absent key (`"first_paint_ms" not in paint`) →
        #     fail closed here. Missing the key is NOT the
        #     same thing as the value being null.
        #
        # `_is_finite_positive` is left untouched so the OTHER
        # `_is_finite_positive` call below (`dom_content_loaded_ms`)
        # still rejects null exactly as before — only
        # `first_paint_ms` widens to permit null.
        _require("first_paint_ms" in paint,
                 f"samples[{i}].paint.first_paint_ms is a required key "
                 f"(absent; pass null explicitly to mark the metric "
                 f"unavailable); got no first_paint_ms key")
        fp = paint["first_paint_ms"]
        if fp is not None:
            _require(_is_finite_positive(fp),
                     f"samples[{i}].paint.first_paint_ms must be finite "
                     f"positive or null (unavailable metric); got {fp!r}")
        dcl = navigation.get("dom_content_loaded_ms")
        _require(_is_finite_positive(dcl),
                 f"samples[{i}].navigation.dom_content_loaded_ms must be "
                 f"finite positive; got {dcl!r}")
        wait = dom_marker.get("wait_ms")
        _require(_is_finite_sentinel_wait(wait),
                 f"samples[{i}].dom_marker.wait_ms must be finite non-negative "
                 f"or the -1.0 absent-marker sentinel; got {wait!r}")
        found = dom_marker.get("found")
        # Cross-field contradiction (parent review): the -1.0 wait
        # sentinel is ONLY valid when the marker was MISSING
        # (`found` is exactly False). `found is True` + `wait == -1.0`
        # is contradictory and fails closed at validation (not
        # deferred to the readiness check).
        _require(not (_is_strict_true(found) and wait == -1.0),
                 f"samples[{i}].dom_marker: found=True with wait_ms=-1.0 "
                 f"is contradictory (the -1.0 sentinel is only valid "
                 f"when the marker is missing)")
        # `count` MUST be a strictly-positive int WHEN the marker was
        # observed (`found is True`). Python bool is an int subclass,
        # so `isinstance(True, int)` is True and `True` would silently
        # pass as count=1 — use `type(count) is int` for strict
        # exclusion. The documented missing-marker shape
        # (`found=False, count=0, wait=-1`) is preserved and is
        # caught later by the readiness check as `blocked/unassessable`,
        # NOT as malformed here.
        cnt = dom_marker.get("count")
        if _is_strict_true(found):
            _require(type(cnt) is int and cnt > 0,
                     f"samples[{i}].dom_marker.count must be a strictly "
                     f"positive int (not bool) when found=True; got {cnt!r}")


def _check_role_mislabel(capture: dict, *, role: str) -> None:
    """Reject cross-role pollution.

    The legacy slot MUST carry `schema == LEGACY_SCHEMA` and (if
    present) `build: legacy`. The migrated slot MUST carry
    `schema == MIGRATED_SCHEMA` and `build: migrated`. A capture
    carrying the OPPOSITE label is rejected even if its other
    fields validate — the role is a first-class contract input.

    Fail-closed: every malformed input (non-dict, missing schema,
    non-string schema, missing build on migrated) raises
    ``ValueError``. Dict-key access is guarded by ``isinstance``
    checks so a list / scalar payload never reaches
    ``capture["schema"]``.
    """
    _require(isinstance(capture, dict),
             f"capture must be a dict; got {type(capture).__name__}")
    schema = capture.get("schema")
    _require(isinstance(schema, str),
             f"capture.schema must be a string; got {type(schema).__name__}")
    if role == LEGACY_BUILD_LABEL:
        _require(schema == LEGACY_SCHEMA,
                 f"legacy slot must carry schema={LEGACY_SCHEMA}; "
                 f"got {schema!r}")
        # `build` is optional on legacy captures (legacy did not
        # emit it); if it IS present it must say legacy.
        if "build" in capture:
            build = capture["build"]
            _require(build == LEGACY_BUILD_LABEL,
                     f"legacy slot must carry build={LEGACY_BUILD_LABEL!r} "
                     f"when build is present; got {build!r}")
    else:
        _require(schema == MIGRATED_SCHEMA,
                 f"migrated slot must carry schema={MIGRATED_SCHEMA}; "
                 f"got {schema!r}")
        build = capture.get("build")
        _require(build == MIGRATED_BUILD_LABEL,
                 f"migrated slot must carry build={MIGRATED_BUILD_LABEL!r}; "
                 f"got {build!r}")


def _readiness_all_found(capture: dict) -> bool:
    """True iff every sample reports exactly ``found=True`` and a
    strictly-positive ``count`` typed as ``int``.

    The comparator runs this check on BOTH legacy and migrated
    captures: if either side has any sample with ``found`` not
    exactly True, ``count`` not a positive int, or an invalid
    readiness marker (non-dict dom_marker / missing fields), the
    comparison cannot honestly derive ``tree_first_interactive_ms``
    (which is ``median(DCL + wait_ms)``) for that side. The
    comparison emits ``blocked/unassessable`` rather than coerce
    the absent sentinel into a numeric.

    Parent-review strictness: ``found is True`` (not truthy) and
    ``type(count) is int`` (not ``isinstance(count, int)`` — which
    would accept ``bool`` because ``bool`` is an ``int`` subclass).
    """
    for s in capture["samples"]:
        if not isinstance(s, dict):
            return False
        dom = s.get("dom_marker")
        if not isinstance(dom, dict):
            return False
        if not _is_strict_true(dom.get("found")):
            return False
        cnt = dom.get("count")
        if type(cnt) is not int or cnt <= 0:
            return False
    return True


def validate_capture(capture: dict, *, role: str,
                     candidate_root=None) -> dict:
    """Validate one capture envelope and return a summary dict.

    The summary exposes the raw per-sample vectors AND the computed
    medians so the comparator can read either representation
    directly. Validation runs BEFORE any computation so a malformed
    capture can never feed downstream arithmetic.
    """
    _require(role in (LEGACY_BUILD_LABEL, MIGRATED_BUILD_LABEL),
             f"role must be one of {{'legacy', 'migrated'}}; got {role!r}")
    _check_role_mislabel(capture, role=role)
    _validate_legacy_envelope(capture)
    # `first_paint_ms: null` is the documented "unavailable metric"
    # sentinel — preserve None in the raw vector for fidelity and
    # track the indices so the comparator can produce a
    # first_paint-specific unassessable reason. Even ONE null
    # sample disables the median (the comparator never computes a
    # partial-sample median) — the stored METRIC_FIRST_PAINT is
    # then None and `first_paint_unavailable` is True.
    fps: list[float | None] = []
    fp_unavailable_idx: list[int] = []
    for i, s in enumerate(capture["samples"]):
        value = s["paint"]["first_paint_ms"]
        if value is None:
            fps.append(None)
            fp_unavailable_idx.append(i)
        else:
            fps.append(float(value))
    dcls = [float(s["navigation"]["dom_content_loaded_ms"])
            for s in capture["samples"]]
    waits = [float(s["dom_marker"]["wait_ms"]) for s in capture["samples"]]
    interactive = [d + w for d, w in zip(dcls, waits, strict=True)]
    first_paint_unavailable = bool(fp_unavailable_idx)
    if first_paint_unavailable:
        first_paint_median: Any = None
    else:
        # At this point every entry is `float` (no None leaked past
        # `_validate_legacy_envelope`'s explicit-null acceptance);
        # `statistics.median` over all-floats is the contracted
        # ±10 %-comparison input.
        first_paint_median = float(statistics.median(
            [v for v in fps if v is not None]))
    summary: dict[str, Any] = {
        "schema": capture["schema"],
        "iterations": capture["iterations"],
        "samples": capture["samples"],
        "raw_first_paint_ms": fps,
        "raw_dom_content_loaded_ms": dcls,
        "raw_readiness_wait_ms": waits,
        "first_paint_unavailable": first_paint_unavailable,
        "first_paint_unavailable_indices": list(fp_unavailable_idx),
        METRIC_FIRST_PAINT: first_paint_median,
        METRIC_DCL: float(statistics.median(dcls)),
        METRIC_INTERACTIVE: float(statistics.median(interactive)),
    }
    if role == MIGRATED_BUILD_LABEL:
        _require(candidate_root is not None,
                 "migrated slot requires --candidate-root for on-disk re-verification")
        root_str = str(candidate_root)
        root = Path(root_str)
        _require(root.exists() and root.is_dir(),
                 f"--candidate-root does not exist or is not a directory: {root}")
        index_html = root / "index.html"
        _require(index_html.is_file(),
                 f"--candidate-root is missing Next.js index.html: {index_html}")
        static_dir = root / "_next" / "static"
        _require(static_dir.is_dir(),
                 f"--candidate-root is missing Next.js _next/static: {static_dir}")
        # Structural identity (parent review): the comparator must
        # enforce the SAME two identity conditions that
        # `capture_hydration.validate_candidate_root` enforces, so a
        # hand-crafted `build=migrated` artifact pointing at a
        # legacy root padded with an empty `_next/static/` directory
        # is rejected here exactly as `--role migrated` would reject
        # it at capture time. Duplicated intentionally (rather than
        # imported) to preserve the import-decoupling contract —
        # the comparator must remain independent of the capture
        # chain child.
        static_files = [p for p in static_dir.rglob("*") if p.is_file()]
        _require(bool(static_files),
                 f"--candidate-root has empty _next/static directory: "
                 f"{static_dir} (a real Next.js static export carries "
                 f"at least one asset)")
        index_body = index_html.read_bytes()
        _require(b"/_next/static/" in index_body,
                 "--candidate-root/index.html does not reference any "
                 "`/_next/static/` asset (a real Next.js static "
                 "export index links its JS/CSS chunks under "
                 "_next/static/)")
        on_disk_hash = hashlib.sha256(
            index_html.read_bytes()).hexdigest()
        # Path-bound provenance (parent review): the capture's
        # recorded `candidate_root` is a first-class identity
        # field, not just a hash. It MUST be present, a non-empty
        # string, and exactly equal to the resolved --candidate-root
        # path. A capture recorded against a different root can no
        # longer pass the on-disk sha check alone.
        recorded_root = capture.get("candidate_root")
        _require(bool(isinstance(recorded_root, str) and recorded_root),
                 "migrated capture is missing a non-empty "
                 "candidate_root path (path-bound provenance)")
        resolved_root = str(root.resolve())
        _require(recorded_root == resolved_root,
                 f"migrated capture's recorded candidate_root does "
                 f"not match the resolved --candidate-root path: "
                 f"recorded={recorded_root!r} resolved={resolved_root!r}")
        recorded_hash = capture.get("candidate_index_sha256")
        _require(isinstance(recorded_hash, str)
                 and len(recorded_hash) == 64,
                 "migrated capture is missing candidate_index_sha256 "
                 "(sha256 hex)")
        _require(recorded_hash == on_disk_hash,
                 f"migrated capture's candidate_index_sha256 does not "
                 f"match the on-disk <candidate-root>/index.html: "
                 f"recorded={recorded_hash} on_disk={on_disk_hash}")
        summary["candidate_root"] = resolved_root
        summary["candidate_index_sha256"] = on_disk_hash
        summary["static_dir_present"] = True
    return summary


def compute_medians(summary: dict) -> dict[str, float | None]:
    """Read the medians the summary already carries.

    `validate_capture` computes the medians once at validation time
    so the comparator never recomputes them. This helper is the
    canonical accessor — kept for symmetry with the test surface.

    When the summary flags `first_paint_unavailable`, the stored
    `server_shell.first_paint_ms` is `None` and this helper
    surfaces it as-is; downstream `compare_captures` translates
    that to `blocked/unassessable` rather than passing a partial
    median into the ±10 %-comparison primitive.
    """
    return {
        METRIC_FIRST_PAINT: summary[METRIC_FIRST_PAINT],
        METRIC_DCL: float(summary[METRIC_DCL]),
        METRIC_INTERACTIVE: float(summary[METRIC_INTERACTIVE]),
    }


def compute_delta_pct(candidate: dict, legacy: dict) -> dict[str, float]:
    """`delta_pct = (candidate/legacy) - 1` per metric. Caller MUST
    have validated both sides already (zero legacy metric → ZeroDivisionError
    is the caller's responsibility, not this function's)."""
    out: dict[str, float] = {}
    for key in METRIC_KEYS:
        legacy_val = float(legacy[key])
        cand_val = float(candidate[key])
        out[key] = (cand_val / legacy_val) - 1.0
    return out


def passes(candidate: dict, legacy: dict, *, threshold: float = THRESHOLD
           ) -> bool:
    """True iff every metric's `abs(delta_pct) <= threshold`.

    Floating-point tolerance: the ±10 % boundary is an inclusive
    contract; `(110/100) - 1` evaluates to `0.10000000000000009`
    under IEEE 754 even though the math says 0.10. A small
    epsilon (``1e-9``) keeps the boundary inclusive without
    masking a real +10.5 % failure (which is ~0.105, well outside
    the epsilon). Tests pin the boundary behaviour precisely.
    """
    epsilon = 1e-9
    delta = compute_delta_pct(candidate, legacy)
    return all(abs(delta[k]) <= threshold + epsilon for k in METRIC_KEYS)


def compare_captures(legacy_capture: dict, migrated_capture: dict,
                      *, candidate_root) -> dict:
    """End-to-end comparison. Returns the deterministic comparison
    artifact. Never mutates the input dicts. Does not write to disk —
    the caller (CLI / orchestrator) decides where the artifact goes.

    Fail-closed contract: there are two independent blocked paths.

    1. **Readiness block** — when the readiness check fails on
       EITHER side, the result is ``blocked/unassessable`` and
       the fabricated ``tree_first_interactive_ms`` metric (which
       is derived from the readiness wait) is omitted from BOTH
       sides' metrics sections (set explicitly to ``None``).

    2. **First-paint-unavailable block** — when ANY sample on
       EITHER role carries ``first_paint_ms: null``, the
       ``server_shell.first_paint_ms`` metric is reported as
       ``None`` on BOTH sides' metrics (artifact symmetry — the
       comparator never claims a number on one side and null on
       the other, and never computes a partial-sample median over
       the 9 remaining valid samples). Other raw metrics
       (``dom_content_loaded_ms`` when all 10 DCL values are
       present) remain truthful.

    When BOTH blocks fire on the same artifact, both reasons are
    concatenated into ``unassessable_reason`` and BOTH metrics
    (``tree_first_interactive_ms`` AND ``server_shell.first_paint_ms``)
    are reported as ``None`` on BOTH sides. ``delta_pct`` is
    NEVER emitted on a blocked artifact and ``passed`` is always
    ``False``.

    Threshold / passed branch: ``delta_pct`` is computed from the
    numeric medians and emitted ONLY when neither block fires.
    """
    legacy_summary = validate_capture(legacy_capture, role=LEGACY_BUILD_LABEL)
    migrated_summary = validate_capture(
        migrated_capture, role=MIGRATED_BUILD_LABEL,
        candidate_root=candidate_root)
    legacy_medians = compute_medians(legacy_summary)
    migrated_medians = compute_medians(migrated_summary)

    legacy_ready = _readiness_all_found(legacy_capture)
    migrated_ready = _readiness_all_found(migrated_capture)
    # Symmetric contract: the shared validator permits null
    # first_paint_ms on EITHER role, so the comparator must check
    # BOTH sides. Computed once here, reused in both the
    # decision and the reason-string branches.
    legacy_unav_fp = bool(legacy_summary.get("first_paint_unavailable", False))
    migrated_unav_fp = bool(
        migrated_summary.get("first_paint_unavailable", False))

    legacy_metrics: dict[str, Any] = dict(legacy_medians)
    migrated_metrics: dict[str, Any] = dict(migrated_medians)

    artifact: dict[str, Any] = {
        "schema": COMP_SCHEMA,
        "captured_at": _now_iso(),
        "result": None,
        "passed": False,
        "threshold": THRESHOLD,
        "legacy": {
            "schema": legacy_summary["schema"],
            "iterations": legacy_summary["iterations"],
            "build": LEGACY_BUILD_LABEL,
            "metrics": legacy_metrics,
        },
        "migrated": {
            "schema": migrated_summary["schema"],
            "iterations": migrated_summary["iterations"],
            "build": MIGRATED_BUILD_LABEL,
            "candidate_root": migrated_summary["candidate_root"],
            "candidate_index_sha256": migrated_summary["candidate_index_sha256"],
            "static_dir_present": migrated_summary["static_dir_present"],
            "metrics": migrated_metrics,
        },
    }

    blocked_reasons: list[str] = []

    if not (legacy_ready and migrated_ready):
        # Honest fail-closed: drop the fabricated interaction
        # metric on BOTH sides so the artifact cannot be read as
        # a numeric readiness claim. The caller still has the
        # raw input captures (with their -1.0 sentinels) on
        # disk; the comparator never duplicates that data here.
        legacy_metrics.pop(METRIC_INTERACTIVE, None)
        migrated_metrics.pop(METRIC_INTERACTIVE, None)
        legacy_metrics[METRIC_INTERACTIVE] = None
        migrated_metrics[METRIC_INTERACTIVE] = None
        if not legacy_ready and not migrated_ready:
            blocked_reasons.append(
                "both captures have at least one sample with "
                "dom_marker.found=false (or count<=0); the readiness "
                "metric is required for ±10 % assessment and the "
                "comparator never invents equivalence for an absent "
                "marker."
            )
        elif not legacy_ready:
            blocked_reasons.append(
                "legacy capture has at least one sample with "
                "dom_marker.found=false (or count<=0); the readiness "
                "metric is required for ±10 % assessment and the "
                "comparator never invents equivalence for an absent "
                "marker. Migrated side remains valid for inspection."
            )
        else:
            blocked_reasons.append(
                "migrated capture has at least one sample with "
                "dom_marker.found=false (or count<=0); the readiness "
                "metric is required for ±10 % assessment and the "
                "comparator never invents equivalence for an absent "
                "marker. Legacy side remains valid for inspection."
            )

    if legacy_unav_fp or migrated_unav_fp:
        # Honest fail-closed: drop `server_shell.first_paint_ms`
        # on BOTH sides so the artifact never claims a number on
        # one side and null on the other. The comparator never
        # computes a partial-sample median (the contract permits
        # all-10 or none-at-all), never synthesises a missing
        # value, and keeps other raw captured metrics
        # (e.g. `dom_content_loaded_ms`) truthful.
        legacy_metrics.pop(METRIC_FIRST_PAINT, None)
        migrated_metrics.pop(METRIC_FIRST_PAINT, None)
        legacy_metrics[METRIC_FIRST_PAINT] = None
        migrated_metrics[METRIC_FIRST_PAINT] = None
        legacy_idx = legacy_summary.get(
            "first_paint_unavailable_indices", [])
        migrated_idx = migrated_summary.get(
            "first_paint_unavailable_indices", [])
        if legacy_unav_fp and migrated_unav_fp:
            blocked_reasons.append(
                f"both captures have at least one sample with "
                f"first_paint_ms: null (legacy sample indices="
                f"{legacy_idx}, migrated sample indices={migrated_idx}); "
                f"the comparator never computes a median over partial "
                f"samples and never synthesises missing values."
            )
        elif legacy_unav_fp:
            blocked_reasons.append(
                f"legacy capture has at least one sample with "
                f"first_paint_ms: null (sample indices={legacy_idx}); "
                f"the comparator never computes a median over partial "
                f"samples and never synthesises missing values. Migrated "
                f"side remains valid for inspection."
            )
        else:
            blocked_reasons.append(
                f"migrated capture has at least one sample with "
                f"first_paint_ms: null (sample indices={migrated_idx}); "
                f"the comparator never computes a median over partial "
                f"samples and never synthesises missing values. Legacy "
                f"side remains valid for inspection."
            )

    if blocked_reasons:
        artifact["unassessable_reason"] = " ".join(blocked_reasons)
        artifact["result"] = "blocked/unassessable"
        artifact["passed"] = False
        return artifact

    delta = compute_delta_pct(migrated_medians, legacy_medians)
    artifact["delta_pct"] = {k: float(delta[k]) for k in METRIC_KEYS}
    if passes(migrated_medians, legacy_medians, threshold=THRESHOLD):
        artifact["result"] = "passed"
        artifact["passed"] = True
    else:
        artifact["result"] = "threshold_failed"
        artifact["passed"] = False
        artifact["failure_metrics"] = [
            k for k in METRIC_KEYS
            if abs(delta[k]) > THRESHOLD
        ]
    return artifact


def _write_artifact_atomic(path: Path, payload: dict) -> None:
    """Atomic write: temp + rename. Failure leaves the previous file
    untouched (the comparator never destroys an existing artifact on
    failure)."""
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}-{id(path)}")
    try:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True,
                                    ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="compare_hydration.py",
        description=("Compare a raw legacy capture against a raw "
                     "migrated (candidate) capture and emit a "
                     "deterministic ±10 % comparison artifact."))
    p.add_argument("legacy", help="Path to the raw legacy capture "
                   "(schema=taxa.g5-capture.legacy/1, build=legacy).")
    p.add_argument("migrated", help="Path to the raw migrated capture "
                   "(schema=taxa.g5-capture.migrated/1, build=migrated).")
    p.add_argument("--candidate-root", required=True,
                   help="Path to the Next.js static export root "
                        "(must contain index.html + _next/static); "
                        "re-verified against the migrated capture's "
                        "candidate_index_sha256.")
    p.add_argument("--out", default=None,
                   help="Write the comparison artifact to this path. "
                        "Defaults to stdout (the JSON payload is the "
                        "last non-empty line).")
    return p.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    legacy_path = Path(args.legacy)
    migrated_path = Path(args.migrated)
    if not legacy_path.is_file():
        sys.stderr.write(
            f"[compare_hydration] legacy capture not found: {legacy_path}\n"
        )
        return EXIT_VALIDATION
    if not migrated_path.is_file():
        sys.stderr.write(
            f"[compare_hydration] migrated capture not found: {migrated_path}\n"
        )
        return EXIT_VALIDATION
    try:
        legacy_capture = json.loads(legacy_path.read_text(encoding="utf-8"))
        migrated_capture = json.loads(migrated_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"[compare_hydration] cannot parse input: {e}\n")
        return EXIT_VALIDATION
    try:
        artifact = compare_captures(
            legacy_capture, migrated_capture,
            candidate_root=args.candidate_root,
        )
    except ValueError as e:
        sys.stderr.write(f"[compare_hydration] validation: {e}\n")
        return EXIT_VALIDATION
    if args.out:
        try:
            _write_artifact_atomic(Path(args.out), artifact)
        except OSError as e:
            sys.stderr.write(f"[compare_hydration] cannot write --out: {e}\n")
            return EXIT_VALIDATION
        sys.stdout.write(
            f"[compare_hydration] wrote {artifact['result']} "
            f"artifact to {args.out}\n"
        )
    else:
        sys.stdout.write(json.dumps(artifact, indent=2,
                                     sort_keys=True, ensure_ascii=False) + "\n")
    if artifact["result"] == "passed":
        return EXIT_OK
    if artifact["result"] == "threshold_failed":
        return EXIT_THRESHOLD_FAILED
    if artifact["result"] == "blocked/unassessable":
        return EXIT_BLOCKED
    return EXIT_VALIDATION


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
