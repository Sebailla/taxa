#!/usr/bin/env python
"""
Validate and report a hydration-timing JSON artifact.

Phase 6a (G5 1+9 protocol, user-approved):

    The comparator observable is DOMContentLoaded only, measured with
    PerformanceNavigationTiming where available and recorded in
    milliseconds. The artifact schema is the G5 1+9 DOMContentLoaded
    schema (raw sample list + per-run provenance + median as float).
    The gate is ``candidate_median - baseline_median <= 10 ms`` — an
    absolute millisecond tolerance that supersedes the unstable
    percentage rule.

    Percent / initial-paint / interaction-latency semantics are
    intentionally eliminated from the new comparator/status path; the
    legacy positional validation (single-artifact invocation, no flags)
    is preserved compatibly — it still validates a single artifact and
    prints a human-readable summary, just using the new schema.

Schema (G5 1+9 / DOMContentLoaded):

    {
      "captured_at":        "ISO-8601 timestamp",
      "build":              "legacy" | "migrated",
      "route":              "/",
      "samples": [
        {
          "dom_content_loaded_ms": float,
          "browser_version":        "Chromium <version>",
          "build_sha":              "<sha or absent>",
          "route":                  "/",
          "captured_at":            "ISO-8601 timestamp",
          "capture_environment":    "controlled-loopback"
        },
        ... (9 entries by default)
      ],
      "warmup_samples": [ ... same shape, 1 entry by default ],
      "samples_retained": 9,
      "warmup_count":      1,
      "median":          float  (median of dom_content_loaded_ms across
                                 retained samples; warm-up excluded),
      "origin":          "http://127.0.0.1:<port>/",
      "source":          "captured" | "unavailable",
      "console_warnings": [string, ...],
      "blocker":         "..."   (when source == "unavailable"),
    }

Usage:

    python scripts/measure_hydration.py <path-to-hydration.json>
    python scripts/measure_hydration.py \\
        --baseline <baseline.json> --candidate <candidate.json> \\
        [--report-out <report.json>]

Exit codes:

    0  valid artifact, summary printed (single-artifact mode)
       OR baseline == candidate, delta_ms <= 10 ms (comparison mode)
    1  usage error (e.g. only --baseline supplied)
    2  artifact missing or unreadable
    3  artifact malformed (schema violation)
    4  baseline vs candidate comparison exits 4 (delta_ms > 10 ms).
       FAIL-CLOSED; G5 must NOT flip until delta_ms <= 10 ms.

Regression semantics (Phase 6a G5 1+9 protocol):

    delta_ms = candidate_median - baseline_median
    pass     = (delta_ms <= 10.0)

    The contract is: candidate median may not regress more than 10 ms
    absolute vs baseline median. Identical inputs (delta_ms == 0)
    pass. An improvement (delta_ms < 0) also passes. Only a strict
    delta_ms > 10 fails closed.

Reference:
    openspec/changes/complete-taxa-frontend-migration/design.md
                                                      §"G5 — hydration baseline"
    openspec/changes/complete-taxa-frontend-migration/tasks.md
                                                      §Phase 6a
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import List


# G5 1+9 protocol defaults — see design.md §"G5 — hydration baseline".
G5_DEFAULT_SAMPLES_RETAINED = 9
G5_DEFAULT_WARMUP_COUNT = 1
G5_THRESHOLD_MS = 10.0

REQUIRED_TOP_KEYS = (
    "captured_at",
    "build",
    "route",
    "samples",
    "warmup_samples",
    "samples_retained",
    "warmup_count",
    "median",
    "origin",
    "console_warnings",
)


def _fail(msg: str, code: int = 1) -> int:
    sys.stderr.write(f"[measure_hydration] {msg}\n")
    return code


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------
def _validate(doc: dict) -> List[str]:
    """Return a list of schema violations. Empty list means valid.

    G5 1+9 schema:
      * ``samples`` is a list of per-run objects; each entry has
        ``dom_content_loaded_ms`` (numeric, non-negative) and provenance
        (browser_version, route, captured_at, capture_environment);
        ``build_sha`` is optional.
      * ``warmup_samples`` is a list of objects with the same shape.
      * ``samples_retained`` == len(samples).
      * ``warmup_count``      == len(warmup_samples).
      * ``median`` is a non-negative number, the empirical median of
        ``samples[*].dom_content_loaded_ms`` (warm-up excluded).
      * ``console_warnings`` is a list of strings (possibly empty).
    """
    violations: List[str] = []
    for key in REQUIRED_TOP_KEYS:
        if key not in doc:
            violations.append(f"missing top-level key {key!r}")

    samples = doc.get("samples")
    if samples is not None and not isinstance(samples, list):
        violations.append(
            f"samples must be a list of per-run objects; got "
            f"{type(samples).__name__}"
        )
    if isinstance(samples, list):
        for i, sample in enumerate(samples):
            if not isinstance(sample, dict):
                violations.append(
                    f"samples[{i}] must be a dict; got {type(sample).__name__}"
                )
                continue
            ms = sample.get("dom_content_loaded_ms")
            if not isinstance(ms, (int, float)) or ms < 0:
                violations.append(
                    f"samples[{i}].dom_content_loaded_ms must be a "
                    f"non-negative numeric; got {ms!r}"
                )
            for k in ("browser_version", "route", "captured_at",
                      "capture_environment"):
                if k not in sample:
                    violations.append(
                        f"samples[{i}] missing provenance key {k!r}"
                    )

    warmup = doc.get("warmup_samples")
    if warmup is not None and not isinstance(warmup, list):
        violations.append(
            f"warmup_samples must be a list; got {type(warmup).__name__}"
        )
    if isinstance(warmup, list):
        for i, sample in enumerate(warmup):
            if not isinstance(sample, dict):
                violations.append(
                    f"warmup_samples[{i}] must be a dict; got "
                    f"{type(sample).__name__}"
                )
                continue
            ms = sample.get("dom_content_loaded_ms")
            if not isinstance(ms, (int, float)) or ms < 0:
                violations.append(
                    f"warmup_samples[{i}].dom_content_loaded_ms must be "
                    f"a non-negative numeric; got {ms!r}"
                )

    # Count consistency (samples_retained == len(samples),
    # warmup_count == len(warmup_samples)).
    sr = doc.get("samples_retained")
    wc = doc.get("warmup_count")
    if isinstance(samples, list) and isinstance(sr, int) and len(samples) != sr:
        violations.append(
            f"samples_retained must equal len(samples); "
            f"samples_retained={sr} but len(samples)={len(samples)}"
        )
    if isinstance(warmup, list) and isinstance(wc, int) and len(warmup) != wc:
        violations.append(
            f"warmup_count must equal len(warmup_samples); "
            f"warmup_count={wc} but len(warmup_samples)={len(warmup)}"
        )

    median = doc.get("median")
    if not isinstance(median, (int, float)) or median < 0:
        violations.append(
            f"median must be a non-negative numeric; got {median!r}"
        )

    warnings = doc.get("console_warnings")
    if warnings is not None and not isinstance(warnings, list):
        violations.append(
            f"console_warnings must be a list; "
            f"got {type(warnings).__name__}"
        )
    elif isinstance(warnings, list):
        for i, w in enumerate(warnings):
            if not isinstance(w, str):
                violations.append(
                    f"console_warnings[{i}] must be a string; got {w!r}"
                )

    return violations


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def _report(doc: dict) -> None:
    """Emit a human-readable summary to stdout (G5 1+9 schema)."""
    samples = doc["samples"]
    warmup = doc["warmup_samples"]
    warnings = doc["console_warnings"]

    sample_values = [
        s["dom_content_loaded_ms"]
        for s in samples
        if isinstance(s, dict) and "dom_content_loaded_ms" in s
    ]
    warmup_values = [
        w["dom_content_loaded_ms"]
        for w in warmup
        if isinstance(w, dict) and "dom_content_loaded_ms" in w
    ]

    sys.stdout.write(
        f"Hydration timing report (G5 1+9 / DOMContentLoaded)\n"
        f"  build:                 {doc['build']}\n"
        f"  route:                 {doc['route']}\n"
        f"  captured_at:           {doc['captured_at']}\n"
        f"  origin:                {doc.get('origin', '-')}\n"
        f"  samples_retained:      {doc['samples_retained']}\n"
        f"  warmup_count:          {doc['warmup_count']}\n"
        f"  threshold_ms:          {G5_THRESHOLD_MS}\n"
        f"\n"
        f"  samples.dom_content_loaded_ms: "
        f"{[float(v) for v in sample_values]}\n"
        f"  warmup_samples.dom_content_loaded_ms: "
        f"{[float(v) for v in warmup_values]}\n"
        f"  median_ms:             {float(doc['median']):.3f}\n"
        f"\n"
        f"  console_warnings: {len(warnings)}\n"
    )
    for w in warnings:
        sys.stdout.write(f"    - {w}\n")


# ---------------------------------------------------------------------------
# Comparator helpers
# ---------------------------------------------------------------------------
def _load_and_validate(path: Path) -> dict:
    """Load a JSON artifact from ``path`` and run schema validation.

    Raises FileNotFoundError / OSError / json.JSONDecodeError /
    ValueError on the underlying read so the caller can map them to
    exit codes 2/3. Returns the parsed dict on success.
    """
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(
            f"artifact root must be a JSON object; got "
            f"{type(doc).__name__}"
        )
    violations = _validate(doc)
    if violations:
        raise ValueError(
            f"artifact has {len(violations)} schema violation(s): "
            + "; ".join(violations)
        )
    return doc


def _median_ms(doc: dict) -> float:
    """Extract the canonical G5 median (float, milliseconds)."""
    return float(doc["median"])


def _raw_samples(doc: dict) -> List[float]:
    """Extract the raw DOMContentLoaded values from retained samples."""
    return [
        float(s["dom_content_loaded_ms"])
        for s in doc.get("samples", [])
        if isinstance(s, dict) and "dom_content_loaded_ms" in s
    ]


def _warmup_samples(doc: dict) -> List[float]:
    """Extract the raw DOMContentLoaded values from warm-up samples."""
    return [
        float(w["dom_content_loaded_ms"])
        for w in doc.get("warmup_samples", [])
        if isinstance(w, dict) and "dom_content_loaded_ms" in w
    ]


def _origin(doc: dict) -> str | None:
    """Best-effort extraction of the HTTP origin URL."""
    origin = doc.get("origin")
    return origin if isinstance(origin, str) and origin else None


def _report_comparison(
    baseline, candidate, baseline_median, candidate_median, delta_ms,
    passes, threshold_ms,
) -> None:
    """Emit the human-readable baseline/candidate comparison report."""
    sys.stdout.write(
        f"G5 hydration comparison report (1+9 / DOMContentLoaded)\n"
        f"  baseline_build:        {baseline['build']}\n"
        f"  candidate_build:       {candidate['build']}\n"
        f"  baseline_captured_at:  {baseline['captured_at']}\n"
        f"  candidate_captured_at: {candidate['captured_at']}\n"
        f"  baseline_origin:       {_origin(baseline) or '-'}\n"
        f"  candidate_origin:      {_origin(candidate) or '-'}\n"
        f"  baseline_samples_retained: {baseline['samples_retained']}\n"
        f"  candidate_samples_retained: {candidate['samples_retained']}\n"
        f"  baseline_warmup_count: {baseline['warmup_count']}\n"
        f"  candidate_warmup_count: {candidate['warmup_count']}\n"
        f"\n"
        f"  baseline_median_ms:    {baseline_median:.3f}\n"
        f"  candidate_median_ms:   {candidate_median:.3f}\n"
        f"  delta_ms:              {delta_ms:.3f}\n"
        f"  threshold_ms:          {threshold_ms:.3f}\n"
        f"\n"
        f"  pass: {str(passes).lower()}\n"
    )


def _run_comparison(
    baseline_path: Path,
    candidate_path: Path,
    report_out: Path | None,
) -> int:
    """Baseline/candidate comparison mode. Returns process exit code.

    G5 1+9 contract:
      * delta_ms = candidate_median - baseline_median
      * pass = (delta_ms <= 10.0)
      * exit 0 when pass, exit 4 when fail (delta_ms > 10).
    """
    try:
        baseline = _load_and_validate(baseline_path)
    except FileNotFoundError:
        return _fail(f"baseline artifact not found: {baseline_path}", code=2)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        return _fail(f"cannot parse baseline {baseline_path}: {err}", code=3)

    try:
        candidate = _load_and_validate(candidate_path)
    except FileNotFoundError:
        return _fail(
            f"candidate artifact not found: {candidate_path}", code=2
        )
    except (OSError, json.JSONDecodeError, ValueError) as err:
        return _fail(
            f"cannot parse candidate {candidate_path}: {err}", code=3
        )

    baseline_median = _median_ms(baseline)
    candidate_median = _median_ms(candidate)
    delta_ms = candidate_median - baseline_median
    passes = delta_ms <= G5_THRESHOLD_MS

    _report_comparison(
        baseline, candidate, baseline_median, candidate_median,
        delta_ms, passes, G5_THRESHOLD_MS,
    )

    if report_out is not None:
        report = {
            "baseline_path": str(baseline_path),
            "candidate_path": str(candidate_path),
            "baseline_build": baseline["build"],
            "candidate_build": candidate["build"],
            "baseline_origin": _origin(baseline),
            "candidate_origin": _origin(candidate),
            "baseline_samples_retained": baseline["samples_retained"],
            "candidate_samples_retained": candidate["samples_retained"],
            "baseline_warmup_count": baseline["warmup_count"],
            "candidate_warmup_count": candidate["warmup_count"],
            "threshold_ms": G5_THRESHOLD_MS,
            "baseline_median_ms": baseline_median,
            "candidate_median_ms": candidate_median,
            "delta_ms": delta_ms,
            "pass": passes,
            # Raw sample arrays for reviewer audit.
            "baseline": {
                "samples": _raw_samples(baseline),
                "warmup_samples": _warmup_samples(baseline),
            },
            "candidate": {
                "samples": _raw_samples(candidate),
                "warmup_samples": _warmup_samples(candidate),
            },
        }
        try:
            report_out.write_text(json.dumps(report, indent=2) + "\n")
        except OSError as err:
            return _fail(
                f"cannot write report to {report_out}: {err}", code=2
            )

    if not passes:
        sys.stderr.write(
            f"[measure_hydration] FAIL-CLOSED: delta_ms={delta_ms:.3f} "
            f"exceeds threshold {G5_THRESHOLD_MS} ms; G5 must NOT flip "
            f"until delta_ms <= {G5_THRESHOLD_MS} ms.\n"
        )
        return 4
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=(
            "Validate and report a G5 1+9 / DOMContentLoaded hydration "
            "artifact, or compare a baseline vs candidate for the "
            f"<= {G5_THRESHOLD_MS:.0f} ms gate."
        ),
    )
    ap.add_argument(
        "artifact",
        nargs="?",
        help=(
            "Single-artifact path (legacy mode). Mutually exclusive "
            "with --baseline/--candidate."
        ),
    )
    ap.add_argument(
        "--baseline",
        type=Path,
        help=(
            "Baseline artifact path. Must be paired with --candidate."
        ),
    )
    ap.add_argument(
        "--candidate",
        type=Path,
        help=(
            "Candidate artifact path. Must be paired with --baseline."
        ),
    )
    ap.add_argument(
        "--report-out",
        type=Path,
        default=None,
        help=(
            "When comparing baseline vs candidate, write a "
            "machine-readable JSON report to this path."
        ),
    )
    return ap


def main(argv: List[str]) -> int:
    ap = _build_parser()
    args = ap.parse_args(argv[1:])

    has_flags = args.baseline is not None or args.candidate is not None
    has_positional = args.artifact is not None

    if has_flags and has_positional:
        sys.stderr.write(
            "usage: measure_hydration.py <path>\n"
            "       measure_hydration.py --baseline <b> --candidate <c> "
            "[--report-out <r>]\n"
        )
        return 1
    if has_flags and (args.baseline is None or args.candidate is None):
        sys.stderr.write(
            "measure_hydration: --baseline and --candidate must be "
            "supplied together.\n"
        )
        return 1
    if not has_flags and not has_positional:
        sys.stderr.write(
            "usage: measure_hydration.py <path>\n"
            "       measure_hydration.py --baseline <b> --candidate <c> "
            "[--report-out <r>]\n"
        )
        return 1

    if has_flags:
        # The earlier `has_flags and (... is None)` guard guarantees
        # both paths are populated here; narrow for the type checker.
        assert (
            args.baseline is not None and args.candidate is not None
        ), "baseline and candidate must be supplied together"
        return _run_comparison(
            args.baseline, args.candidate, args.report_out
        )

    # Legacy single-artifact path (preserved compatibly).
    path = Path(args.artifact)
    if not path.exists() or not path.is_file():
        return _fail(f"artifact not found: {path}", code=2)

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        return _fail(f"cannot parse {path}: {err}", code=3)

    if not isinstance(doc, dict):
        return _fail(
            f"artifact root must be a JSON object; got "
            f"{type(doc).__name__}",
            code=3,
        )

    violations = _validate(doc)
    if violations:
        for v in violations:
            sys.stderr.write(f"[measure_hydration] schema: {v}\n")
        return _fail(
            f"artifact has {len(violations)} schema violation(s)", code=3
        )

    _report(doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))