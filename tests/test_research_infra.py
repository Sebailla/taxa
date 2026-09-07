"""Phase 5b.1 research foundation contract test.

Pins fetch URLs, NetworkError, CDN pins, search-engines re-export.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
R = REPO / "src" / "modules" / "research"
SE_C = REPO / "src" / "data" / "search-engines.js"
SE_R = R / "infrastructure" / "search-engines.js"


def read(rel):
    p = R / rel
    assert p.is_file(), f"missing research file: {p}"
    return p.read_text(encoding="utf-8")


# Same regex as tests/test_smoke.py::test_search_engine_contract.
AC21 = re.compile(
    r'\{\s*key:\s*"([^"]+)",\s*label:\s*"([^"]+)",.*?'
    r"with_authorship:\s*(true|false)", re.DOTALL,
)


def test_domain_layer_definitions():
    """Combined domain assertion: each module must declare its
    exports + the domain barrel must re-export them."""
    domain_src = read("domain/index.ts")
    exports = set()
    for body in re.findall(r"export(?:\s+type)?\s*\{([^}]*)\}", domain_src):
        for e in body.split(","):
            e = e.strip()
            if e:
                exports.add(e.split(" as ")[-1].strip())
    expected = {"ResearchFile", "FileFormat", "isValidResearchFile",
                "isValidFileFormat", "Engine", "Category",
                "isValidEngine", "isValidCategory", "FileNode"}
    assert not (expected - exports), (
        f"domain barrel missing {expected - exports}")
    modules = [
        ("domain/research-file.ts", ("FileFormat", "ResearchFile",
                                     "isValidResearchFile",
                                     "isValidFileFormat")),
        ("domain/engine.ts", ("Engine", "Category", "isValidEngine",
                              "isValidCategory")),
        ("domain/file-node.ts", ("FileNode",)),
    ]
    for rel, syms in modules:
        missing = [s for s in syms if s not in read(rel)]
        assert not missing, f"{rel} missing {missing}"


def test_layer_barrels_match_public_surface():
    domain_src = read("domain/index.ts")
    infra_src = read("infrastructure/index.ts")
    root_src = (R / "index.ts").read_text(encoding="utf-8")
    expected_infra = ("fetchFiles", "fetchServe", "NetworkError",
                      "defaultFetch", "FetchLike", "loadScriptOnce",
                      "CDN_LIBRARIES", "SEARCH_ENGINES", "CATEGORIES")
    missing = [s for s in expected_infra if s not in infra_src]
    assert not missing, f"infra barrel missing {missing}"
    public = ("ResearchFile", "FileFormat", "Engine", "Category", "FileNode",
              "fetchFiles", "fetchServe", "NetworkError", "loadScriptOnce",
              "SEARCH_ENGINES", "CATEGORIES")
    missing_public = [s for s in public
                      if (s not in domain_src) and (s not in infra_src)]
    assert not missing_public, f"public missing: {missing_public}"
    assert re.search(
        r"export\s*\*\s+from\s+[\"']\./domain[\"']", root_src,
    ), 'root barrel must `export * from "./domain"`'
    assert re.search(
        r"export\s*\*\s+from\s+[\"']\./infrastructure[\"']", root_src,
    ), 'root barrel must `export * from "./infrastructure"`'
    assert (R / "index.ts").is_file() and (R / "index.ts").suffix == ".ts"


def test_api_module_exports_required_symbols():
    api_src = read("infrastructure/api.ts")
    expected = ("fetchFiles", "fetchServe", "NetworkError", "defaultFetch",
                "FetchLike", "loadScriptOnce", "CDN_LIBRARIES")
    missing = [s for s in expected if s not in api_src]
    assert not missing, f"api.ts missing {missing}"


def test_fetch_files_url_template():
    src = read("infrastructure/api.ts")
    assert re.search(r"/api/taxon/\$\{[^}]+\}\s*/\s*files\b", src), (
        "fetchFiles URL must be `/api/taxon/${id}/files`")
    assert re.search(r"\$\{baseUrl\}/api/files[`/]", src) is None, (
        "fetchFiles must NOT use legacy `/api/files`")
    assert re.search(
        r"`\$\{baseUrl\}/api/taxon/\$\{taxonId\}/files\b", src,
    ), "fetchFiles must use `/api/taxon/${taxonId}/files` exactly"


def test_fetch_serve_url_uses_encoded_path():
    src = read("infrastructure/api.ts")
    assert re.search(
        r"/api/taxon/\$\{[^}]+\}\s*/\s*files/serve", src,
    ), "fetchServe URL must be `/api/taxon/${id}/files/serve`"
    assert "encodeURIComponent" in src
    assert re.search(r"path=\$\{encodeURIComponent\(", src), (
        "fetchServe must put encoded path on `path=`")


def test_non_2xx_raises_network_error():
    src = read("infrastructure/api.ts")
    assert "class NetworkError" in src
    assert re.search(r"if\s*\(\s*!\s*\w+\.ok\s*\)", src), (
        "non-2xx guard via `!<var>.ok` must be present")
    assert re.search(r"throw\s+new\s+NetworkError\(", src)


def test_load_script_once_pins_cdn_versions():
    """Pins must appear in api.ts, in the `CDN_URLS` const, and the
    `onerror` cache reset must keep the legacy offline-retry fix.
    5b.1 addendum: signature must accept `src?` override."""
    api_src = read("infrastructure/api.ts")
    pins = ("mammoth@1.8.0", "xlsx@0.18.5", "epubjs@0.3.93",
            "papaparse@5.4.1")
    missing = [p for p in pins if p not in api_src]
    assert not missing, f"pins missing from api.ts: {missing}"
    assert "cdn.jsdelivr.net" in api_src
    m = re.search(
        r"export\s+const\s+CDN_URLS[\s\S]*?=\s*\{([\s\S]*?)\};", api_src,
    )
    assert m is not None, "CDN_URLS const block missing"
    block_missing = [p for p in pins if p not in m.group(1)]
    assert not block_missing, f"CDN_URLS const must contain {block_missing}"
    assert re.search(
        r"onerror[\s\S]{0,200}_scriptPromises\.delete\(name\)", api_src,
    ), "loadScriptOnce onerror must `_scriptPromises.delete(name)`"
    m = re.search(r"function\s+loadScriptOnce\(([^)]*)\)", api_src)
    assert m and re.search(r"\bsrc\s*\?\s*:", m.group(1)), (
        "loadScriptOnce must accept an optional `src?` source override")


def test_reexport_module_imports_canonical():
    src = SE_R.read_text(encoding="utf-8")
    assert re.search(
        r'from\s+"\.\.\/\.\.\/\.\.\/data\/search-engines\.js"', src,
    ), "must re-export from `../../../data/search-engines.js`"
    assert "SEARCH_ENGINES" in src and "CATEGORIES" in src


def test_canonical_ac21_source_is_untouched():
    engines = AC21.findall(SE_C.read_text(encoding="utf-8"))
    assert len(engines) == 17, (
        f"AC-21 source must hold 17 engines; got {len(engines)}")
    assert engines[0][0] == "google"
    assert engines[-1][0] == "threads_shared_post"
    keys = [e[0] for e in engines]
    assert keys.index("wikipedia") < keys.index("bhl"), (
        f"engine order drifted: {keys!r}")


# 5b.1 addendum — behavior-level wire-contract fix: `isFilesBody`
# rejected the actual envelope `{exists, taxon_id, taxon_name, taxon_path,
# filesystem_path, subpath, root}` from `api/server.py::list_files`.
# Driver below imports a copy of `infrastructure/api.ts` via
# `node --experimental-strip-types`, feeds `fetchFiles` a fake `FetchLike`,
# and reports per-case behavior.
_DRIVER_JS = """\
import { fetchFiles, NetworkError } from "./api.ts";
const env = { exists: true, taxon_id: 42, taxon_name: "M", taxon_path: "x/y",
  filesystem_path: "/a", subpath: null,
  root: { name: "M", path: "", type: "folder", children: [] } };
async function main() {
  const out = {};
  for (const [k, f, expectThrow] of [
    ["happy", async () => ({ ok: true, status: 200, json: async () => env }), false],
    ["bad", async () => ({ ok: true, status: 200, json: async () => ({}) }), true],
    ["non2xx", async () => ({ ok: false, status: 503, json: async () => ({}) }), true],
  ]) {
    try { const r = await fetchFiles("http://x", 42, f); out[k] = { threw: false, existsType: typeof r.exists }; }
    catch (err) { out[k] = { threw: true, isNE: err instanceof NetworkError, status: err && err.status }; }
    out[k].matches = (out[k].threw === expectThrow)
      && (expectThrow ? out[k].isNE === true : out[k].existsType === "boolean");
  }
  console.log(JSON.stringify(out));
}
main().catch(e => { console.error("FAIL", e); process.exit(2); });
"""


def _exercise_fetch_files():
    src_dir = REPO / "src" / "modules" / "research"
    d = tempfile.mkdtemp(prefix="taxa-fetch-")
    try:
        api = (src_dir / "infrastructure" / "api.ts").read_text(encoding="utf-8")
        api = api.replace('"../domain/research-file"', '"./research-file.ts"')
        (Path(d) / "api.ts").write_text(api, encoding="utf-8")
        (Path(d) / "research-file.ts").write_text(
            (src_dir / "domain" / "research-file.ts").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (Path(d) / "d.mjs").write_text(_DRIVER_JS, encoding="utf-8")
        proc = subprocess.run(
            ["node", "--experimental-strip-types", f"{d}/d.mjs"],
            capture_output=True, text=True,
            env=dict(os.environ, NODE_NO_WARNINGS="1"), timeout=15)
        assert proc.returncode == 0, (
            f"node driver rc={proc.returncode} stderr={proc.stderr[-400:]}")
        return json.loads(proc.stdout.strip())
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_fetch_files_accepts_actual_envelope():
    """fetchFiles must accept the wire envelope from /api/taxon/{id}/files."""
    out = _exercise_fetch_files()
    h, b, n = out["happy"], out["bad"], out["non2xx"]
    assert h["matches"] and not h["threw"] and h["existsType"] == "boolean", h
    assert b["matches"] and b["threw"] and b["isNE"], b
    assert n["matches"] and n["threw"] and n["isNE"] and n["status"] == 503, n