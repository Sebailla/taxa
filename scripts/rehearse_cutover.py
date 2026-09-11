#!/usr/bin/env python
"""PR 1/5 G6 cutover-rehearsal scaffold — hermetic, dry-run-only.

This is the PR 1/5 minimal scaffold per the all-under-400 chain in the
approved migration plan. It is intentionally small:

- reads a JSON manifest from `--manifest`
- refuses to run unless `--dry-run` is supplied (no `--execute` variant
  is offered in this slice)
- never executes `verification.command` or `rollback`
- atomically writes a minimal `cutover-rehearsal.json` artifact inside
  `<out>/` on success, or propagates a non-zero exit (and no artifact)
  on any write failure

It does NOT in this slice:

- validate the manifest schema (PR 2/5)
- enforce path safety on `current_path` / `replacement.path` (PR 2/5)
- parse `verification.command` / `rollback` as shell (PR 2/5)
- run a canonical end-to-end validation against
  `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
  (PR 4/5)
- update `apply-progress.md` or claim full G6 closure (PR 5/5)

G3 Tier-2, G4 / G5, and Approach A / B / C selection remain blocked /
unselected per `openspec/changes/migrate-nextjs-tailwind4/design.md::§3.3.6`.
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


EXIT_OK = 0
EXIT_USAGE = 2
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
    """Read + JSON-parse the manifest. PR 1/5 performs no schema
    validation here; that belongs to PR 2/5."""
    return json.loads(path.read_text())


def _build_artifact(args: argparse.Namespace, manifest: dict) -> dict:
    consumers = manifest.get("consumers", [])
    return {
        "manifest_path": str(args.manifest),
        "manifest_sha256": _sha256(args.manifest),
        "validated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "mode": "dry-run",
        "out_dir": str(args.out),
        "consumer_count": len(consumers) if isinstance(consumers, list) else 0,
        "verification_executed": False,
        "rollback_executed": False,
        # PR 1/5 records the invariants the scaffold promises; PR 2–5
        # extend this object with consumer-id lists, edge enumeration,
        # and validation-error rows.
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="rehearse_cutover",
        description=(
            "PR 1/5 G6 cutover-rehearsal scaffold. Hermetic, dry-run-only: "
            "no --execute variant is offered; verification.command and "
            "rollback are NEVER executed."
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
                        "ONLY mode offered in the PR 1/5 slice.")
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
