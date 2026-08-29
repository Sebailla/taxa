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

Exit codes:
    0  valid artifact, summary printed
    2  artifact missing or unreadable
    3  artifact malformed (schema violation)

Reference:
    openspec/changes/migrate-nextjs-tailwind4/tasks.md   §Phase 1 (1.3)
    openspec/changes/migrate-nextjs-tailwind4/design.md  §Open Questions
                                                  (Hydration cost on taxonomy/tree)
"""
from __future__ import annotations

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
    """Return a list of schema violations. Empty list means valid."""
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


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write(
            "usage: measure_hydration.py <path-to-hydration.json>\n"
        )
        return 1
    path = Path(argv[1])
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
        return _fail(f"artifact has {len(violations)} schema violation(s)", code=3)

    _report(doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))