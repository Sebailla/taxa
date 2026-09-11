#!/usr/bin/env python
"""G6 cutover-rehearsal scaffold — hermetic, dry-run-only, fail-closed.

PR 1/6 ships the minimal scaffold:

- reads a JSON manifest from `--manifest`
- refuses to run unless `--dry-run` (no `--execute` variant is offered)
- never executes `verification.command` or `rollback`
- atomically writes a `cutover-rehearsal.json` artifact inside `<out>/`
  on success, or propagates a non-zero exit (and no artifact) on any
  failure

PR 4/6 extends the scaffold with fail-closed manifest-schema validation,
delegating path / shell checks to the PR 2/6 helpers
`validate_repo_relative_path` + `parse_shell_text` (no duplicated
logic). On any schema error the script exits non-zero and emits no
artifact; on full success the artifact carries `consumer_ids` (one
per consumer, in declaration order) and an empty `validation_errors: []`
list. The canonical normalized manifest is exercised end-to-end against
the PR 4/6 surface; see the
`test_canonical_happy_path_emits_artifact_for_all_26_consumers` pin.

Out of scope: G3 Tier-2, G4 / G5, and Approach A / B / C selection
(blocked / unselected per design.md::§3.3.6); updating apply-progress.md
or claiming full G6 closure (PR 5/6).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is on sys.path so the PR 2/6 helpers can be
# imported via the `scripts` package when invoked as
# `python scripts/rehearse_cutover.py`.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.rehearse_cutover_path_text import (  # noqa: E402
    parse_shell_text,
    validate_repo_relative_path,
)


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_SCHEMA = 4
EXIT_IO = 5


def _log(msg: str) -> None:
    sys.stderr.write(f"[rehearse_cutover] {msg}\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path: Path, body: bytes) -> None:
    """Write body to path atomically (temp file + os.replace). On any
    failure, remove the temp file and re-raise so the caller can
    propagate a non-zero exit and never leave a partial artifact.

    The parent directory is created when missing. If `path.parent` is
    a regular file (occupied slot), `mkdir(parents=True, exist_ok=True)`
    raises `NotADirectoryError`, which is propagated as a write
    failure (no partial artifact, no temp leftover)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        os.write(fd, body)
        os.close(fd)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_manifest(path: Path) -> dict:
    """Read + JSON-parse the manifest. PR 4/6 calls `_validate_manifest`
    immediately after this and fails closed before building the artifact."""
    return json.loads(path.read_text())


# PR 4/6 schema validation. Top-level + per-consumer required fields +
# unique IDs + path safety + shell-text parseability. Path / shell rules
# delegate to the PR 2/6 helpers; no duplicated logic.
REQUIRED_TOP = ("$schema_version", "change", "consumers")
REQUIRED_PER_CONSUMER = (
    "id", "ownership_edge", "current_path", "replacement",
    "verification", "activation_status", "rollback",
)
REQUIRED_PER_VERIFICATION = ("command", "expect")


def _validate_manifest(manifest: dict) -> list[str]:
    """Return list of fail-closed error strings (empty == pass).

    Path / shell semantics delegate to the PR 2/6 helpers. Errors are
    collected (not raised) so the caller can log every problem and
    choose a single non-zero exit code.
    """
    errs: list[str] = []
    for k in REQUIRED_TOP:
        if k not in manifest:
            errs.append(f"manifest missing top-level field {k!r}")
    consumers = manifest.get("consumers")
    if "consumers" in manifest and not isinstance(consumers, list):
        errs.append("manifest.consumers must be a list")
    if not isinstance(consumers, list):
        return errs

    seen: set[str] = set()
    for i, c in enumerate(consumers):
        if not isinstance(c, dict):
            errs.append(f"consumers[{i}] must be an object")
            continue
        cid = c.get("id")
        label = cid if isinstance(cid, str) else f"<index {i}>"
        for k in REQUIRED_PER_CONSUMER:
            if k not in c:
                errs.append(f"consumers[{i}] missing required field {k!r}")
        if isinstance(cid, str):
            if cid in seen:
                errs.append(f"consumers[{i}] duplicate consumer id {cid!r}")
            seen.add(cid)
        cp = c.get("current_path")
        if "current_path" in c and cp is not None and (
            not isinstance(cp, str) or not validate_repo_relative_path(cp)
        ):
            errs.append(f"consumers[{i}] ({label}) current_path failed validate_repo_relative_path: {cp!r}")
        repl = c.get("replacement")
        if "replacement" in c and repl is not None:
            if not isinstance(repl, dict):
                errs.append(f"consumers[{i}] ({label}) replacement must be an object")
            elif not isinstance(repl.get("path"), str) or not validate_repo_relative_path(repl["path"]):
                errs.append(f"consumers[{i}] ({label}) replacement.path failed validate_repo_relative_path: {repl.get('path')!r}")
        ver = c.get("verification")
        if "verification" in c and ver is not None:
            if not isinstance(ver, dict):
                errs.append(f"consumers[{i}] ({label}) verification must be an object")
            else:
                for k in REQUIRED_PER_VERIFICATION:
                    if k not in ver:
                        errs.append(f"consumers[{i}] ({label}) verification.{k} missing")
                vcmd = ver.get("command")
                if isinstance(vcmd, str) and not parse_shell_text(vcmd):
                    errs.append(f"consumers[{i}] ({label}) verification.command failed parse_shell_text: {vcmd!r}")
        rb = c.get("rollback")
        if "rollback" in c and rb is not None and (
            not isinstance(rb, str) or not parse_shell_text(rb)
        ):
            errs.append(f"consumers[{i}] ({label}) rollback failed parse_shell_text: {rb!r}")
    return errs


def _build_artifact(args: argparse.Namespace, manifest: dict) -> dict:
    consumers = manifest.get("consumers", [])
    consumer_ids = (
        [c["id"] for c in consumers
         if isinstance(c, dict) and isinstance(c.get("id"), str)]
        if isinstance(consumers, list) else []
    )
    return {
        "manifest_path": str(args.manifest),
        "manifest_sha256": _sha256(args.manifest),
        "validated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "mode": "dry-run",
        "out_dir": str(args.out),
        "consumer_count": len(consumers) if isinstance(consumers, list) else 0,
        "consumer_ids": consumer_ids,
        "validation_errors": [],
        "verification_executed": False,
        "rollback_executed": False,
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="rehearse_cutover",
        description=(
            "G6 cutover-rehearsal scaffold (PR 1/6 + PR 4/6). Hermetic, "
            "dry-run-only: no --execute variant is offered; "
            "verification.command and rollback are NEVER executed."
        ),
    )
    p.add_argument("--manifest", required=True, type=Path,
                   help="Path to the JSON manifest to validate.")
    p.add_argument("--out", required=True, type=Path,
                   help="Output directory; cutover-rehearsal.json is "
                        "atomically written inside it on success.")
    p.add_argument("--dry-run", action="store_true",
                   help="Required: validate the manifest statically and "
                        "emit a minimal rehearsal artifact. This is the "
                        "ONLY mode offered in the PR 1/6 + PR 4/6 slice.")
    args = p.parse_args(argv)

    if not args.dry_run:
        _log("refusing to run without --dry-run; this slice is hermetic "
             "and dry-run-only (no --execute variant is offered)")
        return EXIT_USAGE

    try:
        manifest = _read_manifest(args.manifest)
    except (OSError, json.JSONDecodeError) as e:
        _log(f"could not read or parse manifest {args.manifest}: {e}")
        return EXIT_IO

    # PR 4/6 fail-closed schema validation: any schema error aborts
    # before artifact build / atomic write.
    errs = _validate_manifest(manifest)
    if errs:
        for e in errs:
            _log(e)
        _log(f"manifest schema validation failed with {len(errs)} error(s); "
             f"refusing to emit rehearsal artifact")
        return EXIT_SCHEMA

    artifact = _build_artifact(args, manifest)
    body = json.dumps(artifact, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    out_path = args.out / "cutover-rehearsal.json"

    try:
        _atomic_write(out_path, body)
    except OSError as e:
        _log(f"failed to atomically write {out_path}: {e}")
        return EXIT_IO

    _log(f"dry-run scaffold OK: {artifact['consumer_count']} consumers "
         f"seen; artifact emitted at {out_path}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
