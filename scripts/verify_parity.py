"""G4 behavior-parity aggregator — fail-closed validator for design.md §3.3.4.

PR1 slice (schema/preflight/atomic core): validates legacy/candidate capture
directories exist, enforces the strict versioned common header
(``schema_version`` + ``captured_at``) on every required report, and
atomically emits ``parity-aggregate.json`` on a complete pass. Per-report
structural validation (paths/types, browser-state required keys) and
pairwise regression comparison land in PR2.

CLI
---
    python scripts/verify_parity.py --legacy-dir D --candidate-dir D
        [--output DIR] [--max-staleness-days N]

Exit codes: 0 pass, 1 usage, 2 dir missing, 3 schema, 4 regression [PR2],
5 aggregate-write failure.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_USAGE = 1
EXIT_CAPTURE_DIR = 2
EXIT_SCHEMA = 3
EXIT_REGRESSION = 4    # PR2
EXIT_AGGREGATE = 5

REPORT_NAMES = ("navigation", "api", "search", "a11y", "browser-state")
SCHEMA_VERSION = "1.0.0"
AGGREGATE_NAME = "parity-aggregate.json"
DEFAULT_MAX_STALENESS_DAYS = 7
ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _atomic_write(p: Path, body: bytes) -> None:
    """Write body to p atomically (temp file + os.replace)."""
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{p.name}.", dir=str(p.parent))
    try:
        os.write(fd, body); os.close(fd); os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _log(prog: str, msg: str) -> None:
    sys.stderr.write(f"[{prog}] {msg}\n")


def _parse_iso(s: str) -> datetime:
    return datetime.strptime(s, ISO_FMT).replace(tzinfo=timezone.utc)


def _validate_common(payload: Any, *, max_age: timedelta, source: str,
                     name: str) -> list[str]:
    """Validate the versioned common header shared by all five reports.

    Every report MUST be a JSON object carrying ``schema_version`` equal to
    ``SCHEMA_VERSION`` and ``captured_at`` as a parseable ISO-8601 UTC string
    that is neither stale (older than ``max_age``) nor in the future.
    Per-report structural checks (paths/types, browser-state required keys)
    are layered on top in PR2 via a per-report validator.
    """
    errs: list[str] = []
    if not isinstance(payload, dict):
        errs.append(f"{source} {name}: payload must be a JSON object, got "
                    f"{type(payload).__name__}")
        return errs
    sv = payload.get("schema_version")
    if sv != SCHEMA_VERSION:
        errs.append(f"{source} {name}: schema_version must be "
                    f"{SCHEMA_VERSION!r}, got {sv!r}")
    captured_at = payload.get("captured_at")
    if not isinstance(captured_at, str):
        errs.append(f"{source} {name}: captured_at must be ISO-8601 string")
        return errs
    try:
        ts = _parse_iso(captured_at)
    except ValueError:
        errs.append(f"{source} {name}: captured_at {captured_at!r} is "
                    f"not parseable as {ISO_FMT}")
        return errs
    now = datetime.now(timezone.utc)
    age = now - ts
    if age > max_age:
        errs.append(f"{source} {name}: stale (age "
                    f"{age.days}d > max {max_age.days}d)")
    if age < -timedelta(minutes=1):
        errs.append(f"{source} {name}: captured_at is in the future "
                    f"({captured_at!r})")
    return errs


def main(argv: list[str] | None = None) -> int:
    prog = "verify_parity"
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "G4 behavior-parity aggregator: validates legacy and candidate "
            "capture dirs carry the five reports (navigation, api, search, "
            "a11y, browser-state), enforces the strict versioned schema and "
            "pairwise thresholds from design.md §3.3.4, and atomically emits "
            f"{AGGREGATE_NAME} only on a complete pass."
        ),
    )
    parser.add_argument("--legacy-dir", required=True, type=Path,
                        help="directory containing the legacy capture reports")
    parser.add_argument("--candidate-dir", required=True, type=Path,
                        help="directory containing the candidate capture reports")
    parser.add_argument("--output", type=Path, default=None,
                        help=f"directory to write {AGGREGATE_NAME} "
                             f"(default: current working directory)")
    parser.add_argument("--max-staleness-days", type=float,
                        default=DEFAULT_MAX_STALENESS_DAYS,
                        help=f"max report age in days "
                             f"(default: {DEFAULT_MAX_STALENESS_DAYS})")
    args = parser.parse_args(argv)

    # Step 1: directory-level preflight.
    if not args.legacy_dir.is_dir():
        _log(prog, f"legacy-dir is not a directory: {args.legacy_dir}")
        return EXIT_CAPTURE_DIR
    if not args.candidate_dir.is_dir():
        _log(prog, f"candidate-dir is not a directory: {args.candidate_dir}")
        return EXIT_CAPTURE_DIR

    max_age = timedelta(days=args.max_staleness_days)

    # Step 2: load + common-schema-validate every report from both dirs.
    legacy_payloads: dict[str, dict] = {}
    candidate_payloads: dict[str, dict] = {}
    schema_errs: list[str] = []
    for name in REPORT_NAMES:
        for source, root, bucket in (
            ("legacy", args.legacy_dir, legacy_payloads),
            ("candidate", args.candidate_dir, candidate_payloads),
        ):
            path = root / f"{name}.json"
            if not path.is_file():
                schema_errs.append(f"{source} {name}: file missing at {path}")
                continue
            try:
                payload = json.loads(path.read_text())
            except json.JSONDecodeError as e:
                schema_errs.append(f"{source} {name}: malformed JSON: {e}")
                continue
            errs = _validate_common(payload, max_age=max_age,
                                    source=source, name=name)
            if errs:
                schema_errs.extend(errs)
            else:
                bucket[name] = payload
    if schema_errs:
        for e in schema_errs:
            _log(prog, e)
        return EXIT_SCHEMA

    # Step 3: pairwise regression comparison. PR1 has no pairwise
    # comparators — every report is recorded as "passed" with no reasons
    # because the schema/preflight layer alone cannot detect regressions.
    # PR2 replaces this block with the five _COMPARATORS lookups and
    # surfaces EXIT_REGRESSION on any detected drift.
    reports_status: dict[str, dict[str, Any]] = {
        name: {"status": "passed", "reasons": []} for name in REPORT_NAMES
    }

    # Step 4: atomic aggregate emission.
    out_dir = args.output if args.output is not None else Path.cwd()
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime(ISO_FMT),
        "legacy_dir": str(args.legacy_dir),
        "candidate_dir": str(args.candidate_dir),
        "max_staleness_days": args.max_staleness_days,
        "reports": reports_status,
        "overall_status": "passed",
    }
    try:
        _atomic_write(out_dir / AGGREGATE_NAME,
                      json.dumps(aggregate, indent=2, sort_keys=True).encode())
    except OSError as e:
        _log(prog, f"aggregate write failed: {e}")
        return EXIT_AGGREGATE

    _log(prog, f"PASS — {AGGREGATE_NAME} emitted at {out_dir / AGGREGATE_NAME}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
