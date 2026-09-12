#!/usr/bin/env python
"""G4 a11y producer adapter — read tools/g4-capture evidence.json and emit
a11y.json atomically for scripts/verify_parity.py.

Consumes only the current tools/g4-capture/scripts/capture.mjs evidence.json
contract. Emits a11y.json matching verify_parity.py exactly:
  {"schema_version": "1.0.0", "captured_at": ISO-8601 UTC, "score": numeric}

User decisions (frozen):
  - Preserve Lighthouse's native 0-1 score with no scaling.
  - Copy evidence.capturedAt verbatim into a11y.captured_at. capture.mjs
    uses ``new Date().toISOString()`` which always emits ``.NNN`` fractional
    seconds; verify_parity.py's strict ``%Y-%m-%dT%H:%M:%SZ`` format rejects
    fractional seconds, so the adapter truncates ``.NNN``. The timestamp
    value itself (date + time + Z) is preserved verbatim.

Fail-closed: any failure exits non-zero WITHOUT leaving a partial a11y.json.

CLI: --evidence PATH --out-dir DIR.
  0 ok; 1 usage; 2 evidence missing/unreadable; 3 evidence malformed JSON;
  4 invalid accessibility score; 5 invalid timestamp; 6 write failure.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_EVIDENCE_MISSING = 2
EXIT_EVIDENCE_MALFORMED = 3
EXIT_INVALID_SCORE = 4
EXIT_INVALID_TIMESTAMP = 5
EXIT_WRITE = 6

SCHEMA_VERSION = "1.0.0"
ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _atomic_write(path: Path, body: bytes) -> None:
    """Atomic write: temp file + os.replace. Cleans up temp on any error."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        os.write(fd, body); os.close(fd); os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def _normalize_timestamp(raw: object) -> str:
    """Strip ``.NNN`` fractional seconds from an ISO-8601 UTC ``Z``-suffix
    timestamp and validate via ISO_FMT. Raises ValueError otherwise."""
    if not isinstance(raw, str) or not raw:
        raise ValueError("timestamp must be a non-empty string")
    if "." in raw:
        head, _, tail = raw.partition(".")
        if not tail.endswith("Z"):
            raise ValueError(f"timestamp not in UTC Z form: {raw!r}")
        normalized = head + "Z"
    elif not raw.endswith("Z"):
        raise ValueError(f"timestamp not in UTC Z form: {raw!r}")
    else:
        normalized = raw
    datetime.strptime(normalized, ISO_FMT)
    return normalized


def _die(code: int, msg: str) -> int:
    sys.stderr.write(f"[capture_a11y] {msg}\n")
    return code


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="capture_a11y_report",
        description="G4 a11y adapter: emit a11y.json from evidence.json.",
    )
    parser.add_argument("--evidence", required=True, type=Path,
                        help="path to evidence.json (capture.mjs output)")
    parser.add_argument("--out-dir", required=True, type=Path,
                        help="directory to write a11y.json")
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as err:
        if isinstance(err.code, int) and err.code != 0:
            return EXIT_USAGE
        return EXIT_OK

    evidence_path: Path = args.evidence
    if not evidence_path.is_file():
        return _die(EXIT_EVIDENCE_MISSING,
                    f"evidence not found: {evidence_path}")
    try:
        evidence_raw = evidence_path.read_text()
    except OSError as e:
        return _die(EXIT_EVIDENCE_MISSING, f"cannot read evidence: {e}")
    try:
        evidence = json.loads(evidence_raw)
    except json.JSONDecodeError as e:
        return _die(EXIT_EVIDENCE_MALFORMED, f"malformed evidence JSON: {e}")
    if not isinstance(evidence, dict):
        return _die(EXIT_EVIDENCE_MALFORMED,
                    "evidence must be a JSON object")

    lighthouse = evidence.get("lighthouse")
    if not isinstance(lighthouse, dict):
        return _die(EXIT_INVALID_SCORE,
                    "evidence.lighthouse must be an object")
    categories = lighthouse.get("categories")
    if not isinstance(categories, dict):
        return _die(EXIT_INVALID_SCORE,
                    "evidence.lighthouse.categories must be an object")
    a11y = categories.get("accessibility")
    if not isinstance(a11y, dict):
        return _die(EXIT_INVALID_SCORE,
                    "evidence.lighthouse.categories.accessibility must be an object")
    score = a11y.get("score")
    # Reject bool explicitly: Python treats True/False as int, but
    # verify_parity.py's _validate_a11y rejects bool too.
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return _die(EXIT_INVALID_SCORE,
                    f"accessibility score must be numeric, got "
                    f"{type(score).__name__}: {score!r}")

    raw_ts = evidence.get("capturedAt")
    if raw_ts is None:
        return _die(EXIT_INVALID_TIMESTAMP, "evidence.capturedAt missing")
    try:
        captured_at = _normalize_timestamp(raw_ts)
    except (ValueError, TypeError) as e:
        return _die(EXIT_INVALID_TIMESTAMP, f"invalid timestamp: {e}")

    doc = {"schema_version": SCHEMA_VERSION,
           "captured_at": captured_at, "score": score}
    try:
        _atomic_write(args.out_dir / "a11y.json",
                      json.dumps(doc, indent=2, sort_keys=True).encode())
    except OSError as e:
        return _die(EXIT_WRITE, f"atomic write failed: {e}")

    sys.stdout.write(
        f"[capture_a11y] emitted a11y.json with score={score} "
        f"captured_at={captured_at}\n"
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
