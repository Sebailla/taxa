"""G3 consumer-readiness verifier — fail-closed manifest contract test.

Per design.md §3.3.3 (G3) and the G3 manifest's `verifier_contract_summary`:
emit CONSUMER-READINESS.json only if every consumer is fully selected AND
every verification.command exits 0 against the candidate build; otherwise
exit non-zero and emit no CONSUMER-READINESS.json. No silent fallback to
legacy files is permitted under any branch.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


EXIT_OK = 0
EXIT_USAGE = 1
EXIT_MANIFEST = 4
EXIT_CHECK = 5

REQUIRED_TOP = ("$schema_version", "change", "planning_artifact",
                "consumers", "edges")
REQUIRED_PER_CONSUMER = ("id", "ownership_edge", "current_path",
                         "replacement", "verification",
                         "activation_status", "rollback")
REQUIRED_PER_VERIFICATION = ("command", "expect")
SELECTED = "selected"


def _atomic_write(p: Path, body: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{p.name}.", dir=str(p.parent))
    try:
        os.write(fd, body); os.close(fd); os.replace(tmp, p)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def _log(prog: str, msg: str) -> None:
    sys.stderr.write(f"[{prog}] {msg}\n")


def _validate_schema(manifest: dict) -> list[str]:
    """Return list of fail-closed error strings. Empty list == pass."""
    errs: list[str] = []
    for k in REQUIRED_TOP:
        if k not in manifest:
            errs.append(f"manifest missing top-level field {k!r}")
    if not isinstance(manifest.get("consumers"), list):
        errs.append("manifest.consumers must be a list")
        return errs
    seen: set[str] = set()
    for i, c in enumerate(manifest["consumers"]):
        if not isinstance(c, dict):
            errs.append(f"consumers[{i}] must be an object")
            continue
        cid = c.get("id")
        for k in REQUIRED_PER_CONSUMER:
            if k not in c:
                errs.append(f"consumers[{i}] missing required field {k!r}")
        if isinstance(cid, str):
            if cid in seen:
                errs.append(f"duplicate consumer id {cid!r}")
            seen.add(cid)
        repl = c.get("replacement")
        if not isinstance(repl, dict):
            errs.append(f"consumers[{i}] ({cid}) replacement must be an object")
        elif repl.get("status") != SELECTED:
            errs.append(f"consumers[{i}] ({cid}) replacement.status unselected")
        if c.get("activation_status") != SELECTED:
            errs.append(f"consumers[{i}] ({cid}) activation_status unselected")
        ver = c.get("verification")
        if not isinstance(ver, dict):
            errs.append(f"consumers[{i}] ({cid}) verification must be an object")
            continue
        for k in REQUIRED_PER_VERIFICATION:
            if k not in ver:
                errs.append(f"consumers[{i}] ({cid}) verification missing {k!r}")
        if not isinstance(ver.get("command"), str):
            errs.append(f"consumers[{i}] ({cid}) verification.command must be string")
        if not isinstance(ver.get("expect"), str):
            errs.append(f"consumers[{i}] ({cid}) verification.expect must be string")
    return errs


def _run_check(cmd: str, timeout: int = 60) -> int:
    """Run verification.command via shell; return exit code only.
    Synthetic tests use benign commands (e.g. ':') that exit 0 cleanly."""
    try:
        r = subprocess.run(["/bin/sh", "-c", cmd], capture_output=True,
                           text=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124
    except OSError:
        return 2
    return r.returncode


def _check_all(consumers: list[dict]) -> list[tuple[str, str]]:
    """Return [(id, reason)] for every consumer whose check failed."""
    failures: list[tuple[str, str]] = []
    for c in consumers:
        if not isinstance(c, dict): continue
        ver = c.get("verification") or {}
        cmd = ver.get("command")
        if not isinstance(cmd, str):
            failures.append((str(c.get("id")), "verification.command not string"))
            continue
        rc = _run_check(cmd)
        if rc != 0:
            failures.append((str(c.get("id")),
                             f"verification.command exited {rc}"))
    return failures


def _emit_readiness(out: Path, manifest: dict, consumers: list[dict]) -> None:
    body = {
        "schema_version": manifest.get("$schema_version"),
        "change": manifest.get("change"),
        "consumers": [
            {"id": c.get("id"), "replacement": c.get("replacement"),
             "verification": c.get("verification")}
            for c in consumers if isinstance(c, dict)
        ],
        "all_selected": True,
    }
    _atomic_write(out / "CONSUMER-READINESS.json",
                  json.dumps(body, indent=2, sort_keys=True).encode())


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    ap = argparse.ArgumentParser(prog="verify_consumers.py", add_help=False)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    try:
        ns = ap.parse_args(argv)
    except SystemExit:
        _log("verify_consumers",
             "usage: verify_consumers.py --manifest <path> --out <path>")
        return EXIT_USAGE
    mp = Path(ns.manifest).resolve()
    out = Path(ns.out).resolve()
    if not mp.is_file():
        _log("verify_consumers", f"manifest missing: {mp}")
        return EXIT_USAGE
    try:
        manifest = json.loads(mp.read_text())
    except json.JSONDecodeError as exc:
        _log("verify_consumers", f"manifest invalid JSON: {exc}")
        return EXIT_MANIFEST
    errs = _validate_schema(manifest)
    if errs:
        for e in errs:
            _log("verify_consumers", e)
        return EXIT_MANIFEST
    consumers = manifest["consumers"]
    failures = _check_all(consumers)
    if failures:
        for cid, msg in failures:
            _log("verify_consumers", f"check failed: {cid}: {msg}")
        return EXIT_CHECK
    try:
        _emit_readiness(out, manifest, consumers)
    except OSError as exc:
        _log("verify_consumers", f"emit failed: {exc}")
        return EXIT_MANIFEST
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
