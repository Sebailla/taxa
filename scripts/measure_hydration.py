#!/usr/bin/env python
"""
Validate and report a hydration-timing JSON artifact.

PR 1 (evidence-only slice) introduces this validation + reporting
tool. The actual Playwright + Lighthouse capture runs in PR 3; this
script reads whatever artifact PR 3 (or a developer's local
capture) produces and emits a human-readable summary that the
design phase cites verbatim when closing
`openspec/changes/migrate-nextjs-tailwind4/scope-decisions.md::§1`.

Schema (pinned by tests/test_hydration_timing.py):

    {
      "captured_at": "ISO-8601 timestamp",
      "build": "legacy" | "migrated",
      "route": "/",
      "server_shell": {
        "first_paint_ms":          float,
        "dom_content_loaded_ms":   float,
      },
      "client_render": {
        "tree_first_paint_ms":         float,
        "tree_first_interactive_ms":   float,
      },
      "console_warnings": [string, ...]
    }

Reported metrics:
    - delta_server_to_tree_first_paint_ms  = client.tree_first_paint_ms - server_shell.first_paint_ms
      (the legacy analogue of "hydration cost": how much latency the
       client-side render pipeline adds on top of the static shell)
    - delta_tree_first_paint_to_interactive_ms
      (time from first tree paint to click handlers wired up)
    - console_warnings count + verbatim list (PR 4's gate)

Usage:
    python scripts/measure_hydration.py <path-to-hydration.json>
    python scripts/measure_hydration.py \
        --baseline <baseline.json> --candidate <candidate.json> \
        [--report-out <report.json>]

Exit codes:
    0  valid artifact, summary printed (single-artifact mode)
       OR baseline==candidate, no regression (comparison mode)
    1  usage error (e.g. only --baseline supplied)
    2  artifact missing or unreadable
    3  artifact malformed (schema violation)
    4  baseline/candidate comparison detected regression (> 0 %
       on initial paint OR interaction latency). FAIL-CLOSED;
       the gate must NOT flip until both deltas are <= 0 %.

Regression semantics (Phase 6a):
    initial_paint       = client_render.tree_first_paint_ms
    interaction_latency = client_render.tree_first_interactive_ms

    The contract is: candidate may not regress > 0 % vs baseline on
    EITHER metric. Identical inputs (delta == 0 %) pass. An
    improvement (delta < 0 %) also passes. Only a strict positive
    delta on either metric fails closed.

Reference:
    openspec/changes/migrate-nextjs-tailwind4/tasks.md   §Phase 1 (1.3)
    openspec/changes/migrate-nextjs-tailwind4/design.md  §Open Questions
                                                  (Hydration cost on taxonomy/tree)
    openspec/changes/complete-taxa-frontend-migration/tasks.md
                                                      §Phase 6a (G5 closure)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_TOP_KEYS = (
    "captured_at",
    "build",
    "route",
    "server_shell",
    "client_render",
    "console_warnings",
)


def _fail(msg: str, code: int = 1) -> int:
    sys.stderr.write(f"[measure_hydration] {msg}\n")
    return code


def _validate(doc: dict) -> list[str]:
    """Return a list of schema violations. Empty list means valid.

    The validator accepts both the legacy single-point schema (top-level
    ``server_shell``/``client_render`` carry numeric metrics directly)
    AND the Phase 6a multi-sample schema (top-level ``samples``/
    ``median`` blocks with raw sample arrays + median metadata). When
    multi-sample fields are present, they MUST be consistent:

      * ``samples_retained`` is the length of each retained samples
        array and must be >= 3 (variance reduction requires ≥ 3
        observations per metric).
      * ``warmup_count`` is the length of each warmup_samples array.
      * The retained arrays under ``samples.{server_shell,client_render}``
        must all have length ``samples_retained``.
      * The warmup arrays under ``warmup_samples.{server_shell,client_render}``
        must all have length ``warmup_count``.
    """
    violations: list[str] = []
    for key in REQUIRED_TOP_KEYS:
        if key not in doc:
            violations.append(f"missing top-level key {key!r}")

    shell = doc.get("server_shell")
    if isinstance(shell, dict):
        for key in ("first_paint_ms", "dom_content_loaded_ms"):
            if key not in shell:
                violations.append(f"server_shell missing key {key!r}")
            elif not isinstance(shell[key], (int, float)) or shell[key] < 0:
                violations.append(
                    f"server_shell.{key} must be non-negative numeric; "
                    f"got {shell[key]!r}"
                )
    elif "server_shell" in doc:
        violations.append(
            f"server_shell must be a dict; got {type(shell).__name__}"
        )

    render = doc.get("client_render")
    if isinstance(render, dict):
        for key in ("tree_first_paint_ms", "tree_first_interactive_ms"):
            if key not in render:
                violations.append(f"client_render missing key {key!r}")
            elif not isinstance(render[key], (int, float)) or render[key] < 0:
                violations.append(
                    f"client_render.{key} must be non-negative numeric; "
                    f"got {render[key]!r}"
                )
    elif "client_render" in doc:
        violations.append(
            f"client_render must be a dict; got {type(render).__name__}"
        )

    warnings = doc.get("console_warnings")
    if warnings is not None and not isinstance(warnings, list):
        violations.append(
            f"console_warnings must be a list; "
            f"got {type(warnings).__name__}"
        )

    # ------------------------------------------------------------------
    # Phase 6a re-baseline — multi-sample contract
    # ------------------------------------------------------------------
    samples = doc.get("samples")
    if samples is not None:
        if not isinstance(samples, dict):
            violations.append(
                f"samples must be a dict; got {type(samples).__name__}"
            )
        else:
            for leg in ("server_shell", "client_render"):
                leg_samples = samples.get(leg)
                if not isinstance(leg_samples, dict):
                    violations.append(
                        f"samples.{leg} must be a dict; got "
                        f"{type(leg_samples).__name__}"
                    )

            samples_retained = doc.get("samples_retained")
            if isinstance(samples_retained, int) and samples_retained < 3:
                violations.append(
                    f"samples_retained must be >= 3 for variance "
                    f"reduction; got {samples_retained}"
                )
            # If samples_retained is declared, the retained arrays must
            # match its length exactly.
            if isinstance(samples, dict) and isinstance(
                samples_retained, int
            ):
                for leg, expected_keys in (
                    ("server_shell", ("first_paint_ms", "dom_content_loaded_ms")),
                    ("client_render", ("tree_first_paint_ms", "tree_first_interactive_ms")),
                ):
                    leg_samples = samples.get(leg)
                    if isinstance(leg_samples, dict):
                        for key in expected_keys:
                            arr = leg_samples.get(key)
                            if isinstance(arr, list):
                                if len(arr) != samples_retained:
                                    violations.append(
                                        f"samples.{leg}.{key} must have "
                                        f"length {samples_retained}; got "
                                        f"{len(arr)}"
                                    )

            warmup = doc.get("warmup_samples")
            if warmup is not None and isinstance(warmup, dict):
                warmup_count = doc.get("warmup_count")
                for leg, expected_keys in (
                    ("server_shell", ("first_paint_ms", "dom_content_loaded_ms")),
                    ("client_render", ("tree_first_paint_ms", "tree_first_interactive_ms")),
                ):
                    leg_warmup = warmup.get(leg)
                    if isinstance(leg_warmup, dict) and isinstance(
                        warmup_count, int
                    ):
                        for key in expected_keys:
                            arr = leg_warmup.get(key)
                            if isinstance(arr, list):
                                if len(arr) != warmup_count:
                                    violations.append(
                                        f"warmup_samples.{leg}.{key} "
                                        f"must have length {warmup_count}; "
                                        f"got {len(arr)}"
                                    )

    return violations


def _report(doc: dict) -> None:
    """Emit a human-readable summary to stdout."""
    shell = doc["server_shell"]
    render = doc["client_render"]
    warnings = doc["console_warnings"]

    delta_paint = render["tree_first_paint_ms"] - shell["first_paint_ms"]
    delta_interactive = (
        render["tree_first_interactive_ms"] - render["tree_first_paint_ms"]
    )

    sys.stdout.write(
        f"Hydration timing report\n"
        f"  build:                 {doc['build']}\n"
        f"  route:                 {doc['route']}\n"
        f"  captured_at:           {doc['captured_at']}\n"
        f"\n"
        f"  server_shell.first_paint_ms:           "
        f"{shell['first_paint_ms']:.1f}\n"
        f"  server_shell.dom_content_loaded_ms:    "
        f"{shell['dom_content_loaded_ms']:.1f}\n"
        f"  client_render.tree_first_paint_ms:     "
        f"{render['tree_first_paint_ms']:.1f}\n"
        f"  client_render.tree_first_interactive_ms: "
        f"{render['tree_first_interactive_ms']:.1f}\n"
        f"\n"
        f"  delta_server_to_tree_first_paint_ms:   {delta_paint:.1f}\n"
        f"  delta_tree_first_paint_to_interactive_ms: "
        f"{delta_interactive:.1f}\n"
        f"\n"
        f"  console_warnings: {len(warnings)}\n"
    )
    for w in warnings:
        # Surface every warning verbatim — PR 4's gate fails the
        # build if the list is non-empty for the migrated app.
        sys.stdout.write(f"    - {w}\n")


# ---------------------------------------------------------------------------
# Phase 6a - baseline / candidate regression comparison helpers
# ---------------------------------------------------------------------------
# Both legs are loaded + validated by `_load_and_validate` (the same
# schema path used by single-artifact mode). The comparison then
# reduces each leg to two numbers
# (initial_paint = client.tree_first_paint_ms,
#  interaction_latency = client.tree_first_interactive_ms)
# and computes the percentage delta. A delta > 0 % on either axis
# triggers exit 4 (regression). Identical inputs and improvements
# both exit 0.


def _load_and_validate(path):
    """Load a JSON artifact from `path` and run schema validation.

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


def _metrics(doc):
    """Reduce a hydration artifact to (initial_paint, interaction_latency).

    Phase 6a precedence:

      1. If the artifact carries a ``median`` block, use the median
         values (variance-reduced contract for multi-sample captures).
      2. Otherwise fall back to the legacy ``client_render.*`` values
         (preserves PR 1b.3b's caller contract for single-point
         artifacts).
    """
    median = doc.get("median")
    if isinstance(median, dict):
        median_render = median.get("client_render")
        if isinstance(median_render, dict):
            initial = median_render.get("tree_first_paint_ms")
            interactive = median_render.get("tree_first_interactive_ms")
            if (
                isinstance(initial, (int, float))
                and isinstance(interactive, (int, float))
            ):
                return (float(initial), float(interactive))
    render = doc["client_render"]
    return (
        float(render["tree_first_paint_ms"]),
        float(render["tree_first_interactive_ms"]),
    )


def _origin(doc) -> str | None:
    """Best-effort extraction of the HTTP origin URL the artifact was
    captured against. Returns None for legacy single-point artifacts."""
    origin = doc.get("origin")
    if isinstance(origin, str) and origin:
        return origin
    # Legacy candidates may carry `candidate_origin` instead of the
    # unified `origin` field. Honour both for back-compat with the
    # partial Phase 6a harness.
    for key in ("candidate_origin", "baseline_origin"):
        value = doc.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _raw_samples(doc) -> dict | None:
    """Extract the raw client_render samples (if present).

    Returns a dict like
    ``{"tree_first_paint_ms": [...], "tree_first_interactive_ms": [...]}``
    or None for legacy single-point artifacts.
    """
    samples = doc.get("samples")
    if not isinstance(samples, dict):
        return None
    render_samples = samples.get("client_render")
    if not isinstance(render_samples, dict):
        return None
    out = {}
    for key in ("tree_first_paint_ms", "tree_first_interactive_ms"):
        arr = render_samples.get(key)
        if isinstance(arr, list):
            out[key] = list(arr)
    return out or None


def _sample_counts(doc) -> tuple[int | None, int | None]:
    """Extract (samples_retained, warmup_count) from the artifact.

    Returns (None, None) for legacy single-point artifacts.
    """
    return (doc.get("samples_retained"), doc.get("warmup_count"))


def _pct_delta(baseline, candidate):
    """Percentage delta of candidate vs baseline.

    Defined as `(candidate - baseline) / baseline * 100`. Identical
    inputs => 0.0. Improvement => negative. Regression => positive.
    A baseline of exactly 0 is treated as "no measurable baseline";
    any positive candidate is then an infinite regression and any
    zero/negative candidate is no regression.
    """
    if baseline == 0:
        if candidate > 0:
            return float("inf")
        return 0.0
    return (candidate - baseline) / baseline * 100.0


def _report_comparison(
    baseline, candidate, bp, bi, cp, ci, dp, di,
    regression, regressing_axes,
):
    """Emit the human-readable baseline/candidate comparison report."""
    b_origin = _origin(baseline) or "-"
    c_origin = _origin(candidate) or "-"
    b_retained, b_warmup = _sample_counts(baseline)
    c_retained, c_warmup = _sample_counts(candidate)
    sys.stdout.write(
        f"Hydration regression report (Phase 6a)\n"
        f"  baseline_build:        {baseline['build']}\n"
        f"  candidate_build:       {candidate['build']}\n"
        f"  baseline_captured_at:  {baseline['captured_at']}\n"
        f"  candidate_captured_at: {candidate['captured_at']}\n"
        f"  baseline_origin:       {b_origin}\n"
        f"  candidate_origin:      {c_origin}\n"
    )
    if b_retained is not None or c_retained is not None:
        sys.stdout.write(
            f"  baseline_samples_retained:  "
            f"{b_retained if b_retained is not None else '-'}\n"
            f"  candidate_samples_retained: "
            f"{c_retained if c_retained is not None else '-'}\n"
            f"  baseline_warmup_count:      "
            f"{b_warmup if b_warmup is not None else '-'}\n"
            f"  candidate_warmup_count:     "
            f"{c_warmup if c_warmup is not None else '-'}\n"
        )
    sys.stdout.write(
        f"\n"
        f"  initial_paint baseline_ms:        {bp:.1f}\n"
        f"  initial_paint candidate_ms:       {cp:.1f}\n"
        f"  initial_paint delta_pct:          {dp:.2f}\n"
        f"\n"
        f"  interaction_latency baseline_ms:  {bi:.1f}\n"
        f"  interaction_latency candidate_ms: {ci:.1f}\n"
        f"  interaction_latency delta_pct:    {di:.2f}\n"
        f"\n"
        f"  regression: {str(regression).lower()}\n"
    )
    if regressing_axes:
        sys.stdout.write(
            f"  regressing_axes: {', '.join(regressing_axes)}\n"
        )


def _run_comparison(baseline_path, candidate_path, report_out):
    """Baseline/candidate comparison mode. Returns process exit code."""
    try:
        baseline = _load_and_validate(baseline_path)
    except FileNotFoundError:
        return _fail(f"baseline artifact not found: {baseline_path}", code=2)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        return _fail(
            f"cannot parse baseline {baseline_path}: {err}", code=3
        )

    try:
        candidate = _load_and_validate(candidate_path)
    except FileNotFoundError:
        return _fail(f"candidate artifact not found: {candidate_path}", code=2)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        return _fail(
            f"cannot parse candidate {candidate_path}: {err}", code=3
        )

    bp, bi = _metrics(baseline)
    cp, ci = _metrics(candidate)
    dp = _pct_delta(bp, cp)
    di = _pct_delta(bi, ci)

    regressing_axes = []
    if dp > 0:
        regressing_axes.append("initial_paint")
    if di > 0:
        regressing_axes.append("interaction_latency")
    regression = bool(regressing_axes)

    _report_comparison(
        baseline, candidate, bp, bi, cp, ci, dp, di,
        regression, regressing_axes,
    )

    if report_out is not None:
        report = {
            "baseline_path": str(baseline_path),
            "candidate_path": str(candidate_path),
            "baseline_build": baseline["build"],
            "candidate_build": candidate["build"],
            "initial_paint_delta_pct": dp,
            "interaction_latency_delta_pct": di,
            "initial_paint_baseline_ms": bp,
            "initial_paint_candidate_ms": cp,
            "interaction_latency_baseline_ms": bi,
            "interaction_latency_candidate_ms": ci,
            "regression": regression,
            "regressing_axes": regressing_axes,
        }
        # Phase 6a re-baseline: include median metadata + raw
        # sample arrays + sample counts + origins so a reviewer
        # can audit the variance reduction (the whole point of
        # re-baselining).
        report["baseline_origin"] = _origin(baseline)
        report["candidate_origin"] = _origin(candidate)
        b_retained, b_warmup = _sample_counts(baseline)
        c_retained, c_warmup = _sample_counts(candidate)
        if b_retained is not None:
            report["baseline_samples_retained"] = b_retained
        if c_retained is not None:
            report["candidate_samples_retained"] = c_retained
        if b_warmup is not None:
            report["baseline_warmup_count"] = b_warmup
        if c_warmup is not None:
            report["candidate_warmup_count"] = c_warmup
        # Median values (the metrics actually used in the comparison).
        report["baseline_median_initial_paint_ms"] = bp
        report["baseline_median_interaction_latency_ms"] = bi
        report["candidate_median_initial_paint_ms"] = cp
        report["candidate_median_interaction_latency_ms"] = ci
        # Raw samples (when present on the source artifacts).
        b_samples = _raw_samples(baseline)
        c_samples = _raw_samples(candidate)
        if b_samples is not None:
            report["baseline"] = report.get("baseline", {})
            report["baseline"]["samples"] = b_samples
        if c_samples is not None:
            report["candidate"] = report.get("candidate", {})
            report["candidate"]["samples"] = c_samples
        try:
            report_out.write_text(json.dumps(report, indent=2) + "\n")
        except OSError as err:
            return _fail(
                f"cannot write report to {report_out}: {err}", code=2
            )

    if regression:
        sys.stderr.write(
            f"[measure_hydration] FAIL-CLOSED: regression detected on "
            f"{', '.join(regressing_axes)}; gate G5 must NOT flip until "
            f"both deltas are <= 0 %.\n"
        )
        return 4
    return 0


def _build_parser():
    ap = argparse.ArgumentParser(
        description=(
            "Validate and report a hydration-timing JSON artifact, or "
            "compare a baseline vs candidate for regression (Phase 6a)."
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
            "Baseline artifact path. Must be paired with --candidate. "
            "Phase 6a G5 closure mode."
        ),
    )
    ap.add_argument(
        "--candidate",
        type=Path,
        help=(
            "Candidate artifact path. Must be paired with --baseline. "
            "Phase 6a G5 closure mode."
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


def main(argv: list[str]) -> int:
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
        return _run_comparison(
            args.baseline, args.candidate, args.report_out
        )

    # Legacy single-artifact path (preserved exactly).
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