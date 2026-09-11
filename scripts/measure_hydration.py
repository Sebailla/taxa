#!/usr/bin/env python
"""
Validate and capture a hydration-timing JSON artifact.

PR 1b.3a: positional `validate <artifact>` mode (exit codes 0/1/2/3
preserved verbatim — usage errors map to exit 1, not argparse's default
exit 2).

PR 1b.3c (G5 closure-path step 1): hermetic `--baseline --candidate
--iterations` capture mode. The legacy baseline artifact is reproducible
on disk without a live browser. Same candidate root → byte-identical
artifact modulo `captured_at`. The synthetic timing is NOT a substitute
for a real Playwright + Lighthouse capture — a future PR 3d replaces
it with measured numbers.

Validate mode:
    measure_hydration.py <artifact.json>

Capture mode:
    measure_hydration.py --baseline OUTPUT.json \\
        --candidate <legacy-server-root> \\
        --iterations N

Exit codes:
    0  valid artifact (validate) or baseline written (capture)
    1  invalid usage (no path, missing required flag, malformed argv)
    2  artifact missing / unreadable (validate) or candidate root
       unusable (capture)
    3  artifact malformed (schema violation)

Schema (pinned by tests/test_hydration_timing.py):

    {
      "captured_at": "ISO-8601",
      "build": "legacy" | "migrated",
      "route": "/",
      "candidate_root": "<absolute path>",          # capture only
      "server_shell": {
        "first_paint_ms":         float,
        "dom_content_loaded_ms":  float,
      },
      "client_render": {
        "tree_first_paint_ms":         float,
        "tree_first_interactive_ms":   float,
      },
      "console_warnings": [string, ...],
      "provenance": {                                # capture only
        "schema": "taxa.g5-hydration-baseline/1",
        "command_line": "<argv>",
        "iterations": int,
        "captured_at": "ISO-8601"
      }
    }

Reference:
  openspec/changes/migrate-nextjs-tailwind4/design.md §3.3.5 (G5)
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
    """Return schema violations (empty list means valid).

    Capture mode reuses this to self-check its written artifact.
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

    return violations


def _report(doc: dict) -> None:
    """Emit a human-readable summary to stdout (validate mode)."""
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
        sys.stdout.write(f"    - {w}\n")


# Capture mode (G5 closure-path step 1) is hermetic: no live browser,
# no network, no live FastAPI server. The legacy hydration timing is
# approximated from static source bytes (HTML / CSS / JS sizes) so the
# script is reproducible in CI without a chromium binary. The
# approximation is documented and stable: same input → same artifact
# bytes, modulo the wall-clock `captured_at` field which is normalised
# out of the byte-equality comparison by the regression test. The
# synthetic timing function is intentionally simple — NOT a substitute
# for a real Playwright measurement.
_BYTES_PER_MS = 32.0  # synthetic scaling factor (deterministic bytes→ms)


def _candidate_summary(root: Path) -> dict:
    """Walk the candidate web root, return source bytes per class.

    Classification is **extension-based** across the whole tree
    (`*.html / *.htm → html`, `*.css → css`, `*.js → js`,
    anything else → other`), regardless of the directory the file
    lives under. So inside `dist/` (when present) only files with
    the `.css` suffix count as css bytes — a `dist/*.js` file would
    count as js bytes and a `dist/*.html` file as html bytes; files
    without an `html / css / js` suffix land in `other`.
    """
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"candidate root not found: {root}")
    summary: dict[str, int] = {"html": 0, "css": 0, "js": 0, "other": 0}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        ext = path.suffix.lower()
        if ext in (".html", ".htm"):
            summary["html"] += size
        elif ext == ".css":
            summary["css"] += size
        elif ext == ".js":
            summary["js"] += size
        else:
            summary["other"] += size
    return summary


def _synthetic_timing(summary: dict) -> dict:
    """Deterministic synthetic timing (NOT a real Playwright substitute).

    Floors at 1.0 ms so a near-empty candidate does not produce 0.0/NaN.
    """
    total = float(
        summary.get("html", 0)
        + summary.get("css", 0)
        + summary.get("js", 0)
    )
    first_paint = total / _BYTES_PER_MS
    return {
        "first_paint_ms": max(1.0, first_paint),
        "dom_content_loaded_ms": max(1.0, first_paint),
        "tree_first_paint_ms": max(1.0, first_paint * 2.0),
        "tree_first_interactive_ms": max(1.0, first_paint * 3.0),
    }


def _now_iso() -> str:
    """Wall-clock ISO-8601 timestamp. The ONLY non-deterministic
    field in the artifact; the regression test normalises it out.
    """
    import datetime as _dt

    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_atomic(path: Path, doc: dict) -> None:
    """Atomic write (temp file + rename) so a partial write never
    leaves a half-written baseline on disk.
    """
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def _build_baseline_artifact(
    candidate_root: Path,
    iterations: int,
    argv: list[str],
) -> dict:
    """Construct the baseline artifact.

    Pure: same input → same artifact (modulo `captured_at`).
    """
    abs_root = candidate_root.resolve()
    timing = _synthetic_timing(_candidate_summary(abs_root))
    captured_at = _now_iso()
    r = round
    return {
        "captured_at": captured_at,
        "build": "legacy",
        "route": "/",
        "candidate_root": str(abs_root),
        "server_shell": {
            "first_paint_ms": r(timing["first_paint_ms"], 3),
            "dom_content_loaded_ms": r(timing["dom_content_loaded_ms"], 3),
        },
        "client_render": {
            "tree_first_paint_ms": r(timing["tree_first_paint_ms"], 3),
            "tree_first_interactive_ms": r(
                timing["tree_first_interactive_ms"], 3
            ),
        },
        "console_warnings": [],
        "provenance": {
            "schema": "taxa.g5-hydration-baseline/1",
            "command_line": " ".join(argv),
            "iterations": iterations,
            "captured_at": captured_at,
        },
    }


def _run_capture(
    out_path: Path, candidate_root: Path, iterations: int, argv: list[str]
) -> int:
    """Capture a baseline artifact and write it to `out_path`.

    Returns 0 on success. On failure, exits non-zero and writes a
    diagnostic to stderr; the output artifact is never written on
    failure (fail-closed).
    """
    try:
        summary = _candidate_summary(candidate_root)
    except FileNotFoundError as err:
        sys.stderr.write(f"[measure_hydration] capture: {err}\n")
        return 2
    except OSError as err:
        sys.stderr.write(
            f"[measure_hydration] capture: cannot read candidate root "
            f"{candidate_root}: {err}\n"
        )
        return 2

    artifact = _build_baseline_artifact(candidate_root, iterations, argv)
    # Self-check: re-validate the artifact before writing so a
    # corrupt build fails the call rather than leaving a half-
    # written baseline on disk.
    violations = _validate(artifact)
    if violations:
        sys.stderr.write(
            f"[measure_hydration] capture: built artifact violates "
            f"schema ({len(violations)} violation(s)):\n"
        )
        for v in violations:
            sys.stderr.write(f"  - {v}\n")
        return 3

    try:
        _write_atomic(out_path, artifact)
    except OSError as err:
        sys.stderr.write(
            f"[measure_hydration] capture: cannot write {out_path}: {err}\n"
        )
        return 2

    s = artifact["server_shell"]
    c = artifact["client_render"]
    sys.stdout.write(
        f"Hydration baseline capture\n"
        f"  output:                {out_path}\n"
        f"  candidate_root:        {candidate_root}\n"
        f"  iterations:            {iterations}\n"
        f"  build:                 legacy\n"
        f"  route:                 /\n"
        f"  captured_at:           {artifact['captured_at']}\n"
        f"\n"
        f"  server_shell.first_paint_ms:           {s['first_paint_ms']:.3f}\n"
        f"  server_shell.dom_content_loaded_ms:    {s['dom_content_loaded_ms']:.3f}\n"
        f"  client_render.tree_first_paint_ms:     {c['tree_first_paint_ms']:.3f}\n"
        f"  client_render.tree_first_interactive_ms: {c['tree_first_interactive_ms']:.3f}\n"
        f"\n"
        f"  source bytes (html/css/js/other): "
        f"{summary.get('html', 0)}/{summary.get('css', 0)}/"
        f"{summary.get('js', 0)}/{summary.get('other', 0)}\n"
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Argparse parser. Supports positional validate mode AND
    capture mode flags. Argparse's default error→exit-2 is
    overridden to exit 1 (the original PR 1b.3a contract).
    """
    parser = argparse.ArgumentParser(
        prog="measure_hydration",
        description=(
            "Validate or capture a hydration-timing JSON artifact. "
            "See design.md §3.3.5 for the G5 closure-path contract."
        ),
    )
    parser.add_argument(
        "artifact",
        nargs="?",
        help="Path to an existing hydration JSON artifact (validate mode).",
    )
    parser.add_argument(
        "--baseline",
        metavar="OUTPUT.json",
        help="Capture mode: write a baseline artifact at this path.",
    )
    parser.add_argument(
        "--candidate",
        metavar="ROOT",
        help="Capture mode: candidate web root to measure.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        metavar="N",
        help="Capture mode: iteration count (provenance metadata).",
    )
    return parser


def main(argv: list[str]) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as err:
        # argparse calls SystemExit on usage errors; map to exit 1
        # so the original PR 1 contract (no-argument → exit 1) is
        # preserved.
        code = err.code
        if isinstance(code, int) and code != 0:
            return 1
        return 0

    # Mutually-exclusive mode dispatch.
    mode_flags = sum(bool(x) for x in (args.baseline, args.artifact))
    if mode_flags == 0:
        sys.stderr.write(
            "usage: measure_hydration.py <path-to-hydration.json>\n"
            "       measure_hydration.py --baseline OUTPUT.json "
            "--candidate ROOT --iterations N\n"
        )
        return 1
    if mode_flags > 1:
        sys.stderr.write(
            "measure_hydration: error: artifact path and --baseline "
            "are mutually exclusive\n"
        )
        return 1

    # --- Validate mode (original PR 1 contract) -------------------
    if args.artifact:
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
                f"artifact has {len(violations)} schema violation(s)",
                code=3,
            )
        _report(doc)
        return 0

    # --- Capture mode (G5 closure-path step 1) ---------------------
    if not args.candidate:
        sys.stderr.write(
            "measure_hydration: error: --baseline requires --candidate\n"
        )
        return 1
    if args.iterations < 1:
        sys.stderr.write(
            "measure_hydration: error: --iterations must be a "
            "positive integer\n"
        )
        return 1
    return _run_capture(
        Path(args.baseline),
        Path(args.candidate),
        args.iterations,
        list(argv),
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))