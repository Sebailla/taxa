"""Regression contract: `fetchDomains` must hit FastAPI `/api/domains`.

Slice 5a.1 (replan) shipped the typed `fetchDomains` in
`src/modules/taxonomy/infrastructure/api.ts`. Its implementation pointed
the request at `${baseUrl}/api/taxonomy/domains` — a path that does NOT
exist on the FastAPI backend. The canonical domain listing lives at
`GET /api/domains` (see `etl/cleanup_biota_variants.py:11`,
`api/server.py:188`, and `tests/test_e2e_file_explorer.py:60`). With the
wrong path, the legacy static-export migration breaks the tree bootstrap
on first paint.

Two executable layers guard the contract:

    1. Source-level — fail fast on a literal `/api/taxonomy/domains`
       substring inside the `fetchDomains` body. Cheap, no toolchain.
    2. Behavioral — Node's native `--experimental-strip-types` loads
       api.ts in-place without tsc, drives `fetchDomains` with a stub
       FetchLike, and asserts the URL ends with `/api/domains`.

References:
    openspec/changes/migrate-nextjs-tailwind4/tasks.md   §5a.1
    openspec/changes/migrate-nextjs-tailwind4/design.md  §Interfaces/Contracts
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
API_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "infrastructure" / "api.ts"

# Canonical FastAPI surface — single source of truth.
CORRECT_PATH = "/api/domains"
WRONG_PATH = "/api/taxonomy/domains"


def _fetch_domains_body(text: str) -> str:
    """Return the source text inside the `fetchDomains` function body.

    Walks past the parameter list and the optional return type (which
    may itself contain `<...>`, `{...}`, and `(...)`), then lands on
    the body's opening `{` and walks to its matching `}`. Used to scope
    the static check to the function that owns the bug — the rest of
    api.ts (fetchTaxon / fetchChildren) legitimately names other paths
    and must not be over-constrained.
    """
    sig = text.find("function fetchDomains")
    assert sig >= 0, (
        "api.ts must export `fetchDomains`; source-level guard cannot "
        "locate the function signature to inspect."
    )
    i = sig + len("function fetchDomains")

    # Step 1: walk past the `(...)` parameter list.
    paren = 0
    in_str: str | None = None
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_str is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch == "/" and nxt == "/":
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":
            i += 2
            while i < len(text) and not (text[i] == "*" and text[i + 1 : i + 2] == "/"):
                i += 1
            i += 2
            continue
        if ch in ('"', "'", "`"):
            in_str = ch
            i += 1
            continue
        if ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
            if paren == 0:
                i += 1
                break
        i += 1

    # Step 2: skip optional return type. The body's `{` is the first
    # `{` at paren==0 AND angle==0 AND brace==0.
    angle = 0
    brace = 0
    paren = 0
    in_str = None
    in_line = False
    in_block = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_line:
            if ch == "\n":
                in_line = False
            i += 1
            continue
        if in_block:
            if ch == "*" and nxt == "/":
                in_block = False
                i += 2
                continue
            i += 1
            continue
        if in_str is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block = True
            i += 2
            continue
        if ch in ('"', "'", "`"):
            in_str = ch
            i += 1
            continue
        if ch == "{" and paren == 0 and angle == 0 and brace == 0:
            break
        if ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
        elif ch == "<":
            angle += 1
        elif ch == ">":
            angle -= 1
        elif ch == "{":
            brace += 1
        elif ch == "}":
            brace -= 1
        i += 1

    body_start = i
    # Step 3: walk the body to its matching `}` at brace depth 0.
    depth = 0
    in_str = None
    in_line = False
    in_block = False
    j = body_start
    while j < len(text):
        ch = text[j]
        nxt = text[j + 1] if j + 1 < len(text) else ""
        if in_line:
            if ch == "\n":
                in_line = False
            j += 1
            continue
        if in_block:
            if ch == "*" and nxt == "/":
                in_block = False
                j += 2
                continue
            j += 1
            continue
        if in_str is not None:
            if ch == "\\":
                j += 2
                continue
            if ch == in_str:
                in_str = None
            j += 1
            continue
        if ch == "/" and nxt == "/":
            in_line = True
            j += 2
            continue
        if ch == "/" and nxt == "*":
            in_block = True
            j += 2
            continue
        if ch in ('"', "'", "`"):
            in_str = ch
            j += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[body_start : j + 1]
        j += 1
    raise AssertionError("could not find closing brace of fetchDomains")


# ---------------------------------------------------------------------------
# Source-level guard — no compiler required.
# ---------------------------------------------------------------------------
def test_fetch_domains_does_not_call_taxonomy_domains_path() -> None:
    """`fetchDomains` MUST NOT request `/api/taxonomy/domains` —
    that path does not exist on FastAPI."""
    if not API_FILE.is_file():
        pytest.skip("api.ts not present yet")
    body = _fetch_domains_body(API_FILE.read_text())
    assert WRONG_PATH not in body, (
        f"fetchDomains must not call {WRONG_PATH}; "
        f"FastAPI exposes the domain listing at {CORRECT_PATH}. "
        "See api/server.py and tests/test_e2e_file_explorer.py."
    )


def test_fetch_domains_calls_fastapi_domains_path() -> None:
    """`fetchDomains` MUST issue a request whose path is exactly
    `${baseUrl}/api/domains`."""
    if not API_FILE.is_file():
        pytest.skip("api.ts not present yet")
    body = _fetch_domains_body(API_FILE.read_text())
    pattern = re.compile(rf"`\$\{{\s*baseUrl\s*\}}{re.escape(CORRECT_PATH)}`")
    assert pattern.search(body), (
        f"fetchDomains must build its URL as "
        f"`${{baseUrl}}{CORRECT_PATH}`; FastAPI exposes the domain "
        f"listing at {CORRECT_PATH}, not at {WRONG_PATH}."
    )


# ---------------------------------------------------------------------------
# Behavioral guard — Node strips types natively, no tsc needed.
# ---------------------------------------------------------------------------
_HARNESS_SOURCE = r"""
// Drive fetchDomains against a stub FetchLike, capture the URL the
// function actually built, and emit a one-line JSON verdict. Runs
// under Node 22+ with --experimental-strip-types (no tsc required).
import { pathToFileURL } from "node:url";

const apiUrl = pathToFileURL(process.argv[2]).href;
const mod = await import(apiUrl);

const captured = [];
const stub = (url) => {
  captured.push(url);
  return Promise.resolve({
    ok: true, status: 200,
    json: () => Promise.resolve([
      { id: 1, name: "Biota" },
      { id: 2, name: "Animalia" },
      { id: 3, name: "Archaea" },
    ]),
  });
};

const out = await mod.fetchDomains("https://api.example.com/base", stub);

const verdict = {
  captured_urls: captured,
  ends_with_correct: captured.length === 1
    && captured[0] === "https://api.example.com/base/api/domains",
  ends_with_wrong: captured.some((u) => u.endsWith("/api/taxonomy/domains")),
  payload_length: out.length,
  payload_first_id: out[0].id,
  payload_first_name: out[0].name,
};
process.stdout.write(JSON.stringify(verdict) + "\n");
"""


@pytest.fixture()
def require_node() -> None:
    if shutil.which("node") is None:
        pytest.skip("node required on PATH for behavioral test")


def _run_harness() -> dict:
    harness = REPO_ROOT / "tests" / "_taxonomy_domains_harness.mjs"
    harness.write_text(_HARNESS_SOURCE)
    try:
        result = subprocess.run(
            [
                "node",
                "--experimental-strip-types",
                "--no-warnings",
                str(harness),
                str(API_FILE),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        harness.unlink(missing_ok=True)
    assert result.returncode == 0, (
        f"node harness failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_fetch_domains_runtime_contract(require_node: None) -> None:
    """`fetchDomains` MUST (a) build the URL `${baseUrl}/api/domains`,
    (b) NEVER request `/api/taxonomy/domains`, and (c) preserve the
    `{id, name}[]` payload contract. Executed via Node's native type
    stripping so the test runs without `tsc` or `node_modules`."""
    if not API_FILE.is_file():
        pytest.skip("api.ts not present yet")
    verdict = _run_harness()

    # (1) Correct path requested, exactly once, with the configured
    #     baseUrl prefix and FastAPI's `/api/domains` suffix.
    assert verdict["ends_with_correct"], (
        f"fetchDomains must request "
        f"'https://api.example.com/base/api/domains' exactly once; "
        f"captured={verdict['captured_urls']!r}"
    )
    # (2) Wrong path NEVER requested — the regression under test.
    assert not verdict["ends_with_wrong"], (
        f"fetchDomains must never request '/api/taxonomy/domains'; "
        f"captured={verdict['captured_urls']!r}"
    )
    # (3) Payload contract preserved — FastAPI shape is `{id, name}[]`,
    #     in order. A regression that broadens the contract fails here.
    assert verdict["payload_length"] == 3, (
        f"expected 3 entries, got {verdict['payload_length']}"
    )
    assert verdict["payload_first_id"] == 1, verdict["payload_first_id"]
    assert verdict["payload_first_name"] == "Biota", verdict["payload_first_name"]
