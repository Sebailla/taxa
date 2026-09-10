"""
Taxonomy infrastructure contract tests (PR 5a).

Pins `src/modules/taxonomy/infrastructure/api.ts` — the typed HTTP
adapter for FastAPI's `/api/taxon/{id}` and `/api/taxon/{id}/children`
endpoints. Asserts file presence, source purity (spec.md rule 4:
infrastructure → domain only; no React/Next/FastAPI), strict-mode
compile under `--lib ES2022` only, and runtime behaviour under Node
with a stubbed `fetch` so no real network is touched.

References:
    openspec/changes/migrate-nextjs-tailwind4/tasks.md  §Phase 5 (5.1, 5.2)
    openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md
        Rules 4 (inward deps), 5 (barrel export)
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
INFRA_FILE = REPO_ROOT / "src" / "modules" / "taxonomy" / "infrastructure" / "api.ts"


def _has_npx() -> bool:
    return shutil.which("npx") is not None


def _has_node() -> bool:
    return shutil.which("node") is not None


@pytest.fixture()
def require_toolchain() -> None:
    if not (_has_npx() and _has_node()):
        pytest.skip("npx + node required on PATH for compile/runtime test")


# ---------------------------------------------------------------------------
# File presence / source-level purity
# ---------------------------------------------------------------------------
def test_infra_file_exists() -> None:
    """RED marker for PR 5a."""
    assert INFRA_FILE.is_file(), (
        f"missing infrastructure file: {INFRA_FILE}. PR 5a ships this file."
    )


def test_infra_file_is_plain_typescript() -> None:
    """`.ts`, not `.tsx` — infrastructure has no JSX."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    assert INFRA_FILE.suffix == ".ts"


def test_infra_file_depends_on_domain_only() -> None:
    """Spec.md rule 4: infrastructure → domain is the only allowed inward edge. The optional `.js` extension covers both `from "../domain/taxon"` and Bundler/NodeNext spellings."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    assert re.search(r'from\s+["\']\.\./domain/taxon(?:\.js)?["\']', text), (
        "infra/api.ts must import from ../domain/taxon — spec.md rule 4."
    )
    for token in (
        "../presentation", "../application", "../index",
        "../../research", "../../design-system",
        "../../browser-state", "../../app-shell",
    ):
        assert token not in text, f"infra/api.ts must not import {token!r}."


def test_infra_file_has_no_framework_imports() -> None:
    """Infrastructure is leaf-level I/O glue: no React, Next, FastAPI, Starlette."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    for tok in (
        "from 'react'", 'from "react"',
        "from 'next'",   'from "next"',
        "from 'nextjs'", 'from "nextjs"',
        "from 'fastapi'", 'from "fastapi"',
        "from 'starlette'", 'from "starlette"',
    ):
        assert tok not in text, f"infra/api.ts must stay free of {tok!r}."


def test_infra_file_exports_named_fns() -> None:
    """PR 5a commits to two named exports: `fetchTaxon` and `fetchChildren`. The barrel re-export breaks on a default export."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    text = INFRA_FILE.read_text()
    for name in ("fetchTaxon", "fetchChildren"):
        pattern = rf"export\s+(?:async\s+)?function\s+{name}\b|export\s+const\s+{name}\b"
        assert re.search(pattern, text), (
            f"infra/api.ts must export `{name}` as a named function or const."
        )


# ---------------------------------------------------------------------------
# Compile + runtime contract (Node harness with injected fetch).
# ---------------------------------------------------------------------------
def _run_tsc_isolated(source: Path, out_dir: Path) -> subprocess.CompletedProcess:
    """Compile `api.ts` under `--strict`, `--target ES2022`,
    `--module commonjs`, `--lib ES2022` (no DOM — fetch must be
    injectable). `--rootDir` pins the output layout across transitive
    imports."""
    return subprocess.run(
        [
            "npx", "--yes", "-p", "typescript@5.7", "tsc",
            "--strict", "--target", "ES2022",
            "--module", "commonjs", "--lib", "ES2022",
            "--skipLibCheck", "--esModuleInterop",
            "--rootDir", "src/modules/taxonomy",
            "--outDir", str(out_dir),
            str(source),
        ],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )


_NODE_HARNESS = r"""
const path = require("path");
const assert = require("assert");
const api = require(path.resolve(process.argv[2]));

function makeFetch(responses) {
  const calls = [];
  const fn = async (input, init) => {
    calls.push({ input, init });
    const r = responses[calls.length - 1];
    if (!r) throw new Error("unexpected fetch call #" + calls.length);
    return {
      ok: r.ok, status: r.status, statusText: r.statusText || "",
      json: () => r.json,
    };
  };
  fn.calls = calls;
  return fn;
}

const ANIMALIA = { id: 5, scientific_name: "Animalia", rank: "kingdom", authorship: null, parent_id: null };
const CHORDATA = { id: 6, scientific_name: "Chordata", rank: "phylum", authorship: "Bateson, 1885", parent_id: 5 };

(async () => {
  // fetchTaxon happy path — wire → domain, URL build.
  const f1 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: ANIMALIA }]);
  const t = await api.fetchTaxon(5, { fetch: f1, baseUrl: "http://x" });
  assert.strictEqual(f1.calls.length, 1);
  assert.strictEqual(f1.calls[0].input, "http://x/api/taxon/5");
  assert.strictEqual(t.id, 5);
  assert.strictEqual(t.name, "Animalia");
  assert.strictEqual(t.rank, "kingdom");
  assert.strictEqual(t.authorship, null);
  assert.strictEqual(t.parent_id, null);

  // fetchTaxon HTTP non-OK — throws with status in message.
  const f2 = makeFetch([{ ok: false, status: 404, statusText: "Not Found", json: { detail: "taxon 99 not found" } }]);
  await assert.rejects(
    () => api.fetchTaxon(99, { fetch: f2, baseUrl: "http://x" }),
    (err) => /404/.test(String(err && err.message || err)),
    "fetchTaxon must reject on non-OK with the status code in the message",
  );

  // fetchTaxon malformed JSON — throws.
  const f3 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: Promise.reject(new SyntaxError("Unexpected token < in JSON")) }]);
  await assert.rejects(
    () => api.fetchTaxon(5, { fetch: f3, baseUrl: "http://x" }),
    (err) => /json|JSON/i.test(String(err && err.message || err)),
  );

  // fetchTaxon schema-invalid payload ({}) — throws.
  const f4 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: {} }]);
  await assert.rejects(
    () => api.fetchTaxon(5, { fetch: f4, baseUrl: "http://x" }),
    (err) => /invalid|taxon/i.test(String(err && err.message || err)),
  );

  // fetchChildren happy path — array of mapped Taxons.
  const f5 = makeFetch([{ ok: true, status: 200, statusText: "OK",
    json: [CHORDATA, { id: 7, scientific_name: "Arthropoda", rank: "phylum", authorship: null, parent_id: 5 }] }]);
  const kids = await api.fetchChildren(5, { fetch: f5, baseUrl: "http://x" });
  assert.ok(Array.isArray(kids));
  assert.strictEqual(kids.length, 2);
  assert.strictEqual(kids[0].name, "Chordata");
  assert.strictEqual(kids[0].rank, "phylum");

  // fetchChildren ?source=worms — query forwarded verbatim.
  const f6 = makeFetch([{ ok: true, status: 200, statusText: "OK", json: [] }]);
  await api.fetchChildren(5, { fetch: f6, baseUrl: "http://x", source: "worms" });
  assert.ok(f6.calls[0].input.includes("source=worms"),
    "fetchChildren must forward ?source=… verbatim: " + f6.calls[0].input);

  // fetchChildren non-OK — throws.
  const f7 = makeFetch([{ ok: false, status: 500, statusText: "Server Error", json: { detail: "boom" } }]);
  await assert.rejects(
    () => api.fetchChildren(5, { fetch: f7, baseUrl: "http://x" }),
    (err) => /500/.test(String(err && err.message || err)),
  );

  process.stdout.write("PASS\n");
})().catch((err) => {
  process.stderr.write("HARNESS_FAILURE: " + (err && err.stack || err) + "\n");
  process.exit(1);
});
"""


@pytest.fixture()
def compiled_infra(tmp_path: Path, require_toolchain: None) -> tuple[Path, Path]:
    """Compile api.ts to CommonJS and write the Node harness."""
    if not INFRA_FILE.exists():
        pytest.skip("infra file not present yet")
    out_dir = tmp_path / "build"
    out_dir.mkdir()
    result = _run_tsc_isolated(INFRA_FILE, out_dir)
    assert result.returncode == 0, (
        f"api.ts failed to compile in isolated strict mode.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    compiled = out_dir / "infrastructure" / "api.js"
    assert compiled.is_file(), (
        f"tsc did not emit a compiled module at {compiled}. "
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    harness = tmp_path / "harness.cjs"
    harness.write_text(_NODE_HARNESS)
    return compiled, harness


def test_compiled_module_passes_runtime_contract(
    compiled_infra: tuple[Path, Path],
) -> None:
    """Under Node (ES2022, no DOM, fetch injected) the compiled module
    proves:
      1. fetchTaxon maps wire `scientific_name` → domain `name` and
         builds `/api/taxon/{id}` relative to `baseUrl`.
      2. fetchTaxon rejects on HTTP non-OK (status in message).
      3. fetchTaxon rejects when the JSON cannot be parsed.
      4. fetchTaxon rejects when the projected record fails
         `isValidTaxon`.
      5. fetchChildren returns an array of mapped Taxons.
      6. fetchChildren forwards `?source=…` verbatim.
      7. fetchChildren rejects on a 500.
    """
    compiled, harness = compiled_infra
    result = subprocess.run(
        ["node", str(harness), str(compiled)],
        cwd=REPO_ROOT,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"runtime harness failed.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert result.stdout.strip() == "PASS", (
        f"unexpected harness output: {result.stdout!r}"
    )
