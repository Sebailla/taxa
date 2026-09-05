"""Phase 5b.4 research realm-mapping contract tests.

Pins the 5b.4 user-decision that pure `realmForFolderPath` belongs in the
research DOMAIN layer (not in the FileExplorer, not in application). The
FileExplorer folder rows now dispatch the realm via this helper; file
rows do NOT receive a `data-realm` attribute (decision #3 in the
parent orchestrator brief — folder rows only).

Pins:
  - `src/modules/research/domain/realm.ts` declares a pure
    `realmForFolderPath(path)` helper that returns one of the eight
    Realm literals (`bacteria`, `archaea`, `viruses`, `animalia`, `fungi`,
    `plantae`, `chromista`, `other`).
  - The domain barrel (`src/modules/research/domain/index.ts`)
    re-exports the `Realm` type + the `REALMS` tuple + the
    `realmForFolderPath` function + the `isRealm` predicate.
  - The realm helper is framework-free (no React, no DOM, no fetch).
  - The helper is exercised via `node --experimental-strip-types`
    against a tmp copy of the module — the test pins the *actual*
    function body, not just text presence.
  - The FileExplorer folder rows now stamp `data-realm` from the helper
    (NOT a hard-coded `"other"` — the 5b.3 placeholder contract is
    retired). File rows do NOT carry `data-realm` (decision #3).
  - No CSS, no new dependencies, no app-shell / commit / push.
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
DO_REALM = R / "domain" / "realm.ts"
DO_INDEX = R / "domain" / "index.ts"
ROOT = R / "index.ts"
PRES = R / "presentation"
PRES_INDEX = PRES / "index.ts"
FILE_EXPLORER = PRES / "FileExplorer.tsx"


def read(rel: str) -> str:
    p = R / rel
    assert p.is_file(), f"missing research file: {p}"
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# File presence — the new domain realm module lands on disk
# ---------------------------------------------------------------------------
def test_files_present() -> None:
    """5b.4: `src/modules/research/domain/realm.ts` MUST land (decision
    #1 — pure `realmForFolderPath` belongs in the research domain)."""
    assert DO_REALM.is_file(), (
        f"missing {DO_REALM.relative_to(REPO)} — 5b.4 must add the "
        f"pure realm helper"
    )


# ---------------------------------------------------------------------------
# Realm literal + predicate contract
# ---------------------------------------------------------------------------
def test_realm_module_declares_realm_literal() -> None:
    """`Realm` MUST be one of the eight canonical taxonomy realm literals
    (`bacteria`, `archaea`, `viruses`, `animalia`, `fungi`, `plantae`,
    `chromista`, `other`). The helper's behaviour depends on the closed
    union — adding a realm requires revisiting `realmForFolderPath`'s
    matching loop, so the test pins the literals as part of the contract."""
    src = read("domain/realm.ts")
    assert re.search(r"\bexport\s+type\s+Realm\b", src), (
        "domain/realm.ts must export a `Realm` type"
    )
    for realm in ("bacteria", "archaea", "viruses", "animalia",
                  "fungi", "plantae", "chromista", "other"):
        assert f'"{realm}"' in src, (
            f"Realm union must include the {realm!r} literal"
        )


def test_realm_module_declares_realms_tuple() -> None:
    """`REALMS` MUST be exported as an ordered tuple of all eight
    `Realm` literals. `realmForFolderPath` iterates the tuple; the
    ordering matters for the first-match-wins dispatch."""
    src = read("domain/realm.ts")
    m = re.search(r"\bexport\s+const\s+REALMS\s*:\s*readonly\s+Realm\[\]", src)
    assert m is not None, (
        "domain/realm.ts must `export const REALMS: readonly Realm[]`"
    )


def test_realm_module_declares_is_realm_predicate() -> None:
    """The `isRealm` predicate MUST exist so consumers can defensively
    narrow arbitrary strings into the `Realm` union."""
    src = read("domain/realm.ts")
    assert re.search(r"\bexport\s+function\s+isRealm\b", src), (
        "domain/realm.ts must export an `isRealm` predicate"
    )


def test_realm_module_declares_realm_for_folder_path() -> None:
    """The user-decision #1 surface: `realmForFolderPath(path)` MUST
    live in the domain layer. The function MUST accept a string and
    return one of the eight Realm literals."""
    src = read("domain/realm.ts")
    assert re.search(
        r"\bexport\s+function\s+realmForFolderPath\s*\(\s*path\s*:\s*string\s*\)",
        src,
    ), (
        "domain/realm.ts must export "
        "`realmForFolderPath(path: string): Realm`"
    )


def test_realm_module_is_framework_free() -> None:
    """The realm helper is pure. It MUST NOT import React, fetch, or
    DOM APIs — these are domain-layer guards inherited from the
    taxonomy `TaxonRecord` invariant tests."""
    src = read("domain/realm.ts")
    for forbidden in (
        "from \"react\"", "from 'react'",
        "fetch", "globalThis.fetch",
        "document.", "window.",
        "useState", "useEffect",
    ):
        assert forbidden not in src, (
            f"domain/realm.ts must stay framework-free; "
            f"forbidden token found: {forbidden!r}"
        )


# ---------------------------------------------------------------------------
# Domain barrel — re-exports every Realm surface
# ---------------------------------------------------------------------------
def test_domain_barrel_reexports_realm_surface() -> None:
    """`src/modules/research/domain/index.ts` MUST re-export the new
    `Realm` surface so consumers reach it via `@taxa/research`."""
    src = read("domain/index.ts")
    for tok in ("Realm", "REALMS", "isRealm", "realmForFolderPath"):
        assert tok in src, (
            f"domain/index.ts must re-export {tok!r}"
        )


def test_root_barrel_keeps_realm_surface_through_domain() -> None:
    """Root barrel re-exports `./domain`, which transitively surfaces
    `realmForFolderPath`. The test pins the chain so a future rename
    of the domain barrel doesn't accidentally drop the Realm surface."""
    src = read("index.ts")
    assert re.search(
        r'export\s*\*\s+from\s+["\']\./domain["\']', src,
    ), 'research/index.ts must keep `export * from "./domain"`'


# ---------------------------------------------------------------------------
# FileExplorer — folder rows dispatch realm via helper; file rows do NOT
# ---------------------------------------------------------------------------
def test_file_explorer_folder_rows_dispatch_realm_via_helper() -> None:
    """User decision #3 (file rows only NOT receive data-realm; folder
    rows DO receive data-realm dispatch). The explorer MUST call
    `realmForFolderPath` from `@taxa/research` (or an equivalent local
    binding) to compute the value, NOT a hard-coded `"other"` literal
    (the 5b.3 deferred-to-5b.4 placeholder is retired)."""
    src = read("presentation/FileExplorer.tsx")
    assert "realmForFolderPath" in src, (
        "FileExplorer must call `realmForFolderPath` to stamp "
        "`data-realm` on folder rows (5b.4 contract; 5b.3 placeholder retired)"
    )
    # The 5b.3 hard-coded `data-realm="other"` placeholder MUST be
    # replaced with a dynamic expression — not a literal `"other"`.
    bad = re.search(r'data-realm=["\']other["\']', src)
    assert bad is None, (
        f"FileExplorer must not hard-code `data-realm=\"other\"` "
        f"anymore; got {bad.group(0)!r}"
    )


def test_file_explorer_file_rows_do_not_carry_data_realm() -> None:
    """Decision #3: file rows do NOT receive `data-realm`. The file-row
    element MUST NOT stamp the attribute (folder rows only)."""
    src = read("presentation/FileExplorer.tsx")
    # Locate the FileRow JSX block: search for `data-file-path` then
    # assert no `data-realm` follows within the same block.
    m = re.search(
        r"data-file-path=[\s\S]{0,400}?</div>", src,
    )
    assert m is not None, (
        "FileExplorer must render a file-row <div data-file-path=...>"
    )
    block = m.group(0)
    assert "data-realm" not in block, (
        "file rows MUST NOT stamp `data-realm` (decision #3 — folder "
        "rows only)"
    )


def test_file_explorer_imports_realm_helper_via_barrel() -> None:
    """The realm helper MUST be consumed via `@taxa/research` (public
    barrel) — never via a deep import into `../domain/realm`."""
    src = read("presentation/FileExplorer.tsx")
    assert re.search(r'from\s+["\']@taxa/research["\']', src), (
        "FileExplorer must import via `@taxa/research` (barrel contract)"
    )
    bad = re.search(r'from\s+["\']\.\./domain/realm["\']', src)
    assert bad is None, (
        f"FileExplorer must not deep-import the domain realm helper; "
        f"got {bad.group(0)!r}"
    )


# ---------------------------------------------------------------------------
# Behaviour-level driver — exercise the pure helper via Node so the test
# pins the *actual* function body, not just text presence.
# ---------------------------------------------------------------------------
_DRIVER_JS = """\
import { realmForFolderPath, isRealm, REALMS }
  from "./realm-bundle.ts";
const out = {
  realms: REALMS.slice(),
  r_animalia:  realmForFolderPath("Animalia/Arthropoda/acr.pdf"),
  r_archaea:   realmForFolderPath("Archaea/Euryarchaeota"),
  r_bacteria:  realmForFolderPath("Bacteria/Firmicutes"),
  r_fungi:     realmForFolderPath("Fungi/Ascomycota"),
  r_plantae:   realmForFolderPath("Plantae/Magnoliopsida"),
  r_chromista: realmForFolderPath("Chromista/Ochrophyta"),
  r_viruses:   realmForFolderPath("Viruses"),
  r_other:     realmForFolderPath("Notes/scratch.txt"),
  r_empty:     realmForFolderPath(""),
  r_nested:    realmForFolderPath("notes/Archaea-journal.md"),
  is_animalia: isRealm("animalia"),
  is_unknown:  isRealm("bogus"),
  is_null:     isRealm(null),
  len:         REALMS.length,
};
console.log(JSON.stringify(out));
"""


def _run_driver() -> dict:
    d = tempfile.mkdtemp(prefix="taxa-realm-")
    try:
        src_text = (DO_REALM).read_text(encoding="utf-8")
        (Path(d) / "realm.ts").write_text(src_text, encoding="utf-8")
        bundle = (
            "export { realmForFolderPath, isRealm, REALMS } from \"./realm.ts\";\n"
        )
        (Path(d) / "realm-bundle.ts").write_text(bundle, encoding="utf-8")
        (Path(d) / "d.mjs").write_text(_DRIVER_JS, encoding="utf-8")
        proc = subprocess.run(
            ["node", "--experimental-strip-types", f"{d}/d.mjs"],
            capture_output=True, text=True,
            env=dict(os.environ, NODE_NO_WARNINGS="1"), timeout=15,
        )
        assert proc.returncode == 0, (
            f"node driver rc={proc.returncode} stderr={proc.stderr[-400:]}"
        )
        return json.loads(proc.stdout.strip())
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def driver_output() -> dict:
    if not shutil.which("node"):
        pytest.skip("node required for runtime harness")
    return _run_driver()


def test_realms_tuple_has_eight_literals(driver_output: dict) -> None:
    """The REALMS tuple MUST contain all eight canonical Realm literals."""
    assert driver_output["len"] == 8, (
        f"REALMS must hold 8 literals; got {driver_output['len']}"
    )
    for realm in ("bacteria", "archaea", "viruses", "animalia",
                  "fungi", "plantae", "chromista", "other"):
        assert realm in driver_output["realms"], (
            f"REALMS must include {realm!r}; got {driver_output['realms']!r}"
        )


def test_realm_for_folder_path_dispatches_each_realm(driver_output: dict) -> None:
    """Each canonical Realm literal must be returned for a path whose
    first matching segment is the corresponding lowercase string.

    NOTE: the loop walks the tuple in order. `other` is the last-resort
    literal and is checked last — the assertion below passes when the
    first matching realm literal in the tuple wins."""
    o = driver_output
    assert o["r_animalia"] == "animalia"
    assert o["r_archaea"] == "archaea"
    assert o["r_bacteria"] == "bacteria"
    assert o["r_fungi"] == "fungi"
    assert o["r_plantae"] == "plantae"
    assert o["r_chromista"] == "chromista"
    assert o["r_viruses"] == "viruses"


def test_realm_for_folder_path_returns_other_for_unknown(driver_output: dict) -> None:
    """Paths that contain no Realm literal fall through to `"other"`.
    Empty paths also return `"other"`."""
    o = driver_output
    assert o["r_other"] == "other", (
        f"`Notes/scratch.txt` should fall through to `other`; got {o['r_other']!r}"
    )
    assert o["r_empty"] == "other", (
        f"empty path must return `other`; got {o['r_empty']!r}"
    )


def test_realm_for_folder_path_is_case_insensitive(driver_output: dict) -> None:
    """The matching loop must be case-insensitive (matches the legacy
    `web/file_explorer.js::_folderRealm` resolver's `lowercase()` call)."""
    o = driver_output
    assert o["r_nested"] == "archaea", (
        "case-insensitive substring match must hit `Archaea` even "
        "when embedded in a longer path / different casing"
    )


def test_is_realm_predicate_accepts_canonical_only(driver_output: dict) -> None:
    """`isRealm` MUST accept the eight canonical literals and reject
    everything else (including `null`, undefined, unknown strings)."""
    o = driver_output
    assert o["is_animalia"] is True
    assert o["is_unknown"] is False
    assert o["is_null"] is False