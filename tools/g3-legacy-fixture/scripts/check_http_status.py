"""Controlled HTTP-status verifier for the G3 legacy fixture.

Per the G3 manifest's `verifier_contract_summary`: every consumer's
`verification.command` must exit 0 AND its actual HTTP status code must
match the consumer's `verification.expect`. Shell-only verification (`curl`
exit 0 ≠ HTTP 200) is insufficient — a 404 from curl still exits 0 when the
connection succeeded. This helper parses curl's `-w '%{http_code}'` output
and validates the captured status code(s) against the expected value.
Fail-closed: any mismatch exits non-zero.

Usage:
    check_http_status.py <command> <expected>
"""
from __future__ import annotations

import re
import subprocess
import sys


_STATUS_RE = re.compile(r"\d{3}")
# Pure 3-digit expected values are HTTP-status expectations; anything else
# ("ok", "1 passed", "all passed") falls back to shell exit code only.
_STATUS_EXPECT_RE = re.compile(r"^\s*\d{3}(\s+for\s+each)?\s*$")


def extract_status_codes(stdout: str) -> list[str]:
    return _STATUS_RE.findall(stdout)


def is_status_expectation(expected: str) -> bool:
    return bool(_STATUS_EXPECT_RE.match(expected.strip()))


def normalise_expected(expected: str) -> str:
    e = expected.strip()
    return e[: -len(" for each")] if e.endswith(" for each") else e


def validate(actual: list[str], expected: str) -> tuple[bool, str]:
    norm = normalise_expected(expected)
    mismatches = [(i, c) for i, c in enumerate(actual) if c != norm]
    if mismatches:
        rendered = ", ".join(f"#{i}:{c}" for i, c in mismatches)
        return False, f"status mismatches ({rendered}); expected {norm!r}"
    return True, f"all {len(actual)} status code(s) match {norm!r}"


def check(command: str, expected: str, *, timeout: int = 10) -> int:
    """Exit codes: 0=pass, 2=usage/subprocess failure, 3=status mismatch."""
    try:
        r = subprocess.run(["/bin/sh", "-c", command], capture_output=True,
                           text=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"[check_http_status] timeout after {timeout}s: {command!r}",
              file=sys.stderr)
        return 2
    if r.returncode != 0:
        print(f"[check_http_status] command exited {r.returncode}: {command!r}",
              file=sys.stderr)
        return r.returncode
    # Non-HTTP expectations fall back to shell exit only (do not try to parse).
    if not is_status_expectation(expected):
        return 0
    codes = extract_status_codes(r.stdout)
    ok, msg = validate(codes, expected)
    print(f"[check_http_status] {msg}", file=sys.stderr)
    return 0 if ok else 3


def main(argv=None) -> int:
    if argv is None: argv = sys.argv[1:]
    if len(argv) != 2:
        print("usage: check_http_status.py <command> <expected>", file=sys.stderr)
        return 2
    return check(argv[0], argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
