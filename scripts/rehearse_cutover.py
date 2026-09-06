#!/usr/bin/env python3
"""Phase 6b G6 cutover rehearsal — fail-closed dry-run of the atomic cutover unit.

Per design.md §"Atomic cutover unit" + §"G6 — cutover rehearsal" +
tasks.md §Phase 6b + the Phase 6b authorisation contract:

    scripts/rehearse_cutover.py exercises the atomic cutover unit
    end-to-end against an isolated clone (or against the on-disk
    working-copy manifest for the real rehearsal), runs the G3
    Tier-2 verifier (scripts/verify_consumers.py) through a SHARED
    `run_g3_tier2(manifest, out)` helper, emits versioned G6 evidence
    (`evidence/g6/cutover-rehearsal.json`) ONLY on a COMPLETE
    rehearsal, and updates `apply-progress.md` G6 footer ONLY if the
    REAL rehearsal (no test-mode flags) exits 0.

Strict-TDD contract (binding):
    - Fail-closed for every subset-only cutover (`web_dir_only` /
      `consumers_only` / `makefile_only` / `artifact_only`): exit
      non-zero with EXIT_SUBSET_ONLY, emit NO cutover-rehearsal.json,
      do NOT invoke the G3 verifier.
    - The rehearsal ALWAYS starts and owns a controlled local static
      server (python -m http.server on an OS-picked isolated free
      TCP port — NEVER the ambient port 8765 owned by FastAPI)
      serving the real ``out/`` candidate. The rehearsal rewrites
      each consumer's :8765 URL to the picked port in a tmp
      manifest copy; the verifier runs the rewritten commands
      against the rehearsal's controlled server. The verifier does
      NOT receive --serve or --fixture-web-root (the rehearsal owns
      the server lifecycle). The original on-disk manifest is
      NEVER modified.
    - Fail closed if the controlled server cannot start: EXIT_G3
      when ControlledStaticServer.__enter__ raises RuntimeError
      (missing / non-dir fixture-web-root, port bind failure, or
      non-ready-within-timeout). No cutover-rehearsal.json emitted,
      no apply-progress.md update, no silent fallback. The
      RuntimeError propagates from run_g3_tier2 to main() which
      maps it to EXIT_G3.
    - Tier-2 verifier invoked via `run_g3_tier2(manifest_path, out_dir)`
      shared helper (no edits to verify_consumers.py required; its
      existing `main(argv)` public interface is sufficient).
    - cutover-rehearsal.json carries `activation_complete: true`,
      `unselected_count: 0`, `silent_fallback_paths: []` on a complete
      rehearsal.
    - apply-progress.md G6 footer is updated ONLY when the real
      rehearsal (default working-copy manifest, no test-mode flags)
      exits 0. Test mode (`--no-update-apply-progress`), subset-only
      mode, G3 failure, controlled-server failure, and
      silent-fallback-path detection ALL leave the production
      apply-progress.md untouched.
    - NO production cutover, NO source/API/Makefile modification,
      NO commit, NO push. This script is a DRY-RUN that emits
      evidence + updates the gate-status footer; PR 3e performs the
      actual atomic cutover unit.

Exit codes:
    0   OK — full rehearsal succeeded; cutover-rehearsal.json emitted.
    1   EXIT_USAGE       — invalid arguments, missing manifest, or
                            invalid JSON in the manifest.
    2   EXIT_SUBSET_ONLY — subset-only cutover detected; rehearsal
                            must fail closed (atomic cutover is
                            forbidden in subset form).
    3   EXIT_G3          — G3 Tier-2 verifier failed; the activated
                            manifest is not yet ready for cutover.
    4   EXIT_REHEARSAL   — silent-fallback-path detection failed
                            closed; the atomic cutover unit carries
                            a forbidden fallback to the legacy
                            `web/` runtime.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.error import URLError


# Ensure the parent directory of `scripts/` (the repo root) is on
# `sys.path` so `import scripts.verify_consumers` works whether the
# script is invoked as `python scripts/rehearse_cutover.py` (no
# scripts/ on sys.path) or as a module (`python -m
# scripts.rehearse_cutover`, scripts/ on sys.path). Idempotent: only
# adds the path if it's not already present.
_REPO_ROOT_FROM_SCRIPT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT_FROM_SCRIPT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT_FROM_SCRIPT))


# ── ControlledStaticServer (owned by the rehearsal) ───────────────────────

class ControlledStaticServer:
    """Controlled local static server lifecycle OWNED BY THE REHEARSAL.

    Per the Phase 6b G6 controlled-server repair: the rehearsal
    starts and owns an isolated ``python -m http.server`` subprocess
    serving the candidate build (the post-cut React static export
    under ``<repo_root>/out/``). The verifier does NOT receive
    ``--serve`` or ``--fixture-web-root`` (it does not spawn its
    own server); instead, the verifier receives a tmp manifest
    copy whose consumer commands are port-rewritten from
    ``127.0.0.1:8765`` to the rehearsal's controlled port. The
    ambient port 8765 (owned by the production FastAPI mount) is
    NEVER used by the rehearsal's controlled server — the OS
    picks an isolated free TCP port via ``_pick_free_port``.

    Strict fail-closed:
      - On ``__enter__``: validate the web root exists and is a
        directory BEFORE spawn; pick an OS-assigned free port;
        spawn ``python -m http.server <port> --directory <root>``;
        poll the healthcheck (status 200 on
        ``<origin>/index.html``); raise ``RuntimeError`` on any
        failure (pre-spawn validation, spawn error, or
        non-ready-within-timeout). The RuntimeError propagates to
        ``main()`` which surfaces it as ``EXIT_G3 = 3``.
      - On ``__exit__``: ALWAYS terminate the subprocess (success
        or error). The exit is idempotent: calling ``_terminate``
        twice does nothing.

    Method hooks (``_spawn``, ``_wait_ready``, ``_terminate``)
    are exposed so tests can patch each step in isolation via
    ``monkeypatch``. The default ``_spawn`` calls
    ``subprocess.Popen``; the default ``_terminate`` issues
    ``SIGTERM`` then escalates to ``SIGKILL`` after a grace
    timeout.
    """
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_HEALTHCHECK_PATH = "/index.html"
    READY_TIMEOUT_S = 30.0
    TERMINATE_GRACE_S = 5.0
    AMBIENT_PORT_FASTAPI = 8765

    def __init__(self, *, web_root, host=DEFAULT_HOST,
                 ready_timeout=READY_TIMEOUT_S, log=None):
        self.web_root = Path(web_root).resolve()
        self.host = host
        self.ready_timeout = ready_timeout
        self.log = log or (lambda *a, **kw: None)
        self.port = None
        self.proc = None

    @property
    def origin(self):
        """Return the controlled server's origin URL. Raises
        ``RuntimeError`` if the server has not been started."""
        if self.port is None:
            raise RuntimeError(
                "controlled static server has not been started; "
                "port is unset")
        return f"http://{self.host}:{self.port}"

    def _pick_free_port(self):
        """Bind to (host, 0) so the OS picks a free TCP port, then
        release the socket and return the port. Read-only: does
        NOT mutate state beyond the ephemeral socket."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((self.host, 0))
            return s.getsockname()[1]
        finally:
            s.close()

    def _spawn(self, argv, **kwargs):
        return subprocess.Popen(argv, **kwargs)

    def _wait_ready(self):
        """Poll the healthcheck URL until ready or timeout.
        Returns True if ready, False on timeout or process death.
        Tests can monkeypatch this to short-circuit the wait."""
        deadline = time.monotonic() + self.ready_timeout
        url = f"{self.origin}{self.DEFAULT_HEALTHCHECK_PATH}"
        while time.monotonic() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                return False  # died during startup
            try:
                with urllib.request.urlopen(url, timeout=1) as r:
                    if r.status == 200:
                        return True
            except (URLError, OSError):
                time.sleep(0.1)
        return False

    def _terminate(self):
        """Terminate the subprocess (SIGTERM, then SIGKILL on
        grace-timeout). Idempotent: calling twice does nothing."""
        proc, self.proc = self.proc, None
        if proc is None:
            return
        try:
            proc.terminate()
        except OSError:
            pass
        try:
            proc.wait(timeout=self.TERMINATE_GRACE_S)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass
            try:
                proc.wait(timeout=2)
            except OSError:
                pass

    def __enter__(self):
        # Pre-spawn fail-closed validation: the web root MUST
        # exist and be a directory BEFORE we bind a port or
        # spawn a subprocess. The verifier-side RuntimeError
        # path can no longer catch this for us (the verifier
        # no longer owns the server).
        if not self.web_root.exists():
            raise RuntimeError(
                f"controlled static server: web_root path does "
                f"not exist: {self.web_root}")
        if not self.web_root.is_dir():
            raise RuntimeError(
                f"controlled static server: web_root is not a "
                f"directory: {self.web_root}")
        self.port = self._pick_free_port()
        # Refuse to bind the ambient port 8765 (the production
        # FastAPI mount owns that address). pick_free_port() should
        # never return 8765 unless explicitly forced, but guard
        # anyway.
        if self.port == self.AMBIENT_PORT_FASTAPI:
            raise RuntimeError(
                f"controlled static server picked ambient port "
                f"{self.AMBIENT_PORT_FASTAPI}; the production "
                f"FastAPI mount owns that address; refusing to "
                f"bind (no controlled server spawn)")
        argv = [sys.executable, "-m", "http.server",
                str(self.port), "--directory",
                str(self.web_root)]
        self.log("rehearse_cutover",
                 f"starting controlled static server "
                 f"(http.server): {argv}")
        self.proc = self._spawn(
            argv, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE)
        if not self._wait_ready():
            self._terminate()
            raise RuntimeError(
                f"controlled static server did not become ready "
                f"at {self.origin}{self.DEFAULT_HEALTHCHECK_PATH}"
                f" within {self.ready_timeout:.1f}s")
        return self

    def __exit__(self, exc_type, exc, tb):
        self._terminate()
        return False


def _utcnow_iso():
    """Return the current UTC time as an ISO-8601 string with a 'Z'
    suffix. Uses timezone-aware `datetime.now(UTC)` (the
    `datetime.utcnow()` API is deprecated as of Python 3.12 and slated
    for removal)."""
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


EXIT_OK = 0
EXIT_USAGE = 1
EXIT_SUBSET_ONLY = 2   # subset-only cutover must fail-closed
EXIT_G3 = 3            # G3 Tier-2 verifier failed
EXIT_REHEARSAL = 4     # silent-fallback-path detection failed closed


# The four cutover-unit subsets that the design (atomic cutover unit =
# four-set release: WEB_DIR repoint + 26 consumer updates + Makefile
# rewrite + out/ build artifact) explicitly forbids in subset form.
# A partial revert breaks the SPA shell or the AC-21 contract test.
CUTOVER_UNIT_SUBSETS = (
    "web_dir_only", "consumers_only", "makefile_only", "artifact_only",
)


# Default real paths. Tests override --manifest / --out /
# --rehearsal-out / --apply-progress to keep the production tree
# untouched. The defaults are the canonical production locations.
DEFAULT_MANIFEST = (
    "openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json"
)
DEFAULT_REHEARSAL_OUT = (
    "openspec/changes/complete-taxa-frontend-migration/evidence/g6/"
    "cutover-rehearsal.json"
)
DEFAULT_APPLY_PROGRESS = (
    "openspec/changes/complete-taxa-frontend-migration/apply-progress.md"
)


# ── Shared Tier-2 invocation helper ──────────────────────────────────────

def run_g3_tier2(manifest_path, out_dir, *, repo_root=None,
                 fixture_web_root=None):
    """Shared G3 Tier-2 invocation. Both this rehearsal script AND the
    apply worker's PR 3e verification call this helper so the rehearsal
    contract and the cutover contract share one code path.

    Per the Phase 6b G6 controlled-server repair (revised): the
    rehearsal ALWAYS starts and owns an isolated
    ``python -m http.server`` subprocess serving the supplied
    ``fixture_web_root`` (the post-cut React candidate build under
    ``<repo_root>/out/``). The verifier does NOT receive
    ``--serve`` or ``--fixture-web-root`` (the rehearsal owns the
    server; the verifier just runs the rewritten commands in a
    tmp manifest copy). The OS picks the controlled server's port
    via ``ControlledStaticServer._pick_free_port``; the ambient
    port 8765 (the production FastAPI mount) is NEVER used.

    Per the Phase 6b orchestrator contract: do NOT edit
    ``verify_consumers.py`` — its existing ``main(argv)`` function
    (public, returns int) accepts ``--manifest``, ``--out``,
    ``--repo-root`` etc. and runs each consumer's
    ``verification.command`` as-is. The tmp manifest carries
    port-rewritten commands (``127.0.0.1:8765`` → the rehearsal's
    controlled port), so the verifier's HTTP-shape checks hit the
    controlled server without needing a server-spawn flag of its
    own. Verified by the strict-TDD contract tests in
    ``tests/test_rehearse_cutover.py``.

    Strict fail-closed:
      - Raises ``RuntimeError`` (which the caller maps to
        ``EXIT_G3 = 3``) if the controlled server cannot start
        (missing/non-dir web root, port bind failure, or
        non-ready-within-timeout). The original on-disk manifest
        is NEVER modified — only the tmp copy has its commands
        port-rewritten.
      - The tmp manifest copy is removed in a ``finally`` block
        after the verifier returns (no dot-prefixed leftover).
      - The controlled server is ALWAYS terminated on context
        exit (success or error).

    Returns the verifier's exit code (0 = PASS).
    """
    # Late import so the module is importable even when verify_consumers
    # is unavailable (e.g. before scripts/ is on PYTHONPATH).
    import scripts.verify_consumers as vc

    if fixture_web_root is None:
        raise ValueError(
            "run_g3_tier2: fixture_web_root is required "
            "(the rehearsal's controlled static server needs a "
            "web root to serve)")
    fixture_web_root = Path(fixture_web_root).resolve()
    manifest_path = Path(manifest_path).resolve()

    with ControlledStaticServer(web_root=fixture_web_root) as srv:
        # Build a tmp manifest copy with port-rewritten commands.
        # The on-disk manifest is NEVER modified.
        try:
            manifest_obj = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"could not load manifest for tmp-copy rewrite: "
                f"{manifest_path}: {exc}") from exc
        old_port = ControlledStaticServer.AMBIENT_PORT_FASTAPI
        new_port = srv.port
        for c in manifest_obj.get("consumers", []):
            if not isinstance(c, dict):
                continue
            ver = c.get("verification")
            if not isinstance(ver, dict):
                continue
            cmd = ver.get("command")
            if not isinstance(cmd, str):
                continue
            ver["command"] = cmd.replace(
                f"127.0.0.1:{old_port}",
                f"127.0.0.1:{new_port}")
        # Atomic write to a tmp file (dot-prefixed for audit
        # visibility; cleaned up in the finally block).
        fd, tmp_manifest_path = tempfile.mkstemp(
            prefix=".tmp-rehearsal-manifest-",
            suffix=".json", dir="/tmp")
        try:
            os.write(fd, json.dumps(
                manifest_obj, indent=2,
                sort_keys=True).encode() + b"\n")
            os.close(fd)
            argv = ["--manifest", tmp_manifest_path,
                    "--out", str(out_dir)]
            if repo_root is not None:
                argv.extend(["--repo-root", str(repo_root)])
            # NOTE: --serve and --fixture-web-root are
            # intentionally ABSENT — the rehearsal owns the
            # controlled static server; the verifier just runs the
            # rewritten commands in the tmp manifest.
            return int(vc.main(argv))
        finally:
            try:
                os.unlink(tmp_manifest_path)
            except OSError:
                pass


# ── Silent-fallback-path scan ────────────────────────────────────────────

# A silent fallback to the legacy `web/` runtime is forbidden by the
# design risk register (subset-only is forbidden; partial reverts break
# the SPA shell). The scan looks for code lines (not comments) that
# carry a real fallback signature:
#   - WEB_DIR reassigned to a "web" path (legacy), OR
#   - a Makefile target that falls back to the `web/` directory.
# Comments mentioning "fallback" or `web/` are intentionally excluded;
# they document the predecessor and are not actionable code paths.
def scan_silent_fallback_paths(repo_root):
    """Return a list of `path:line: <text>` strings for any silent
    fallback paths detected in `Makefile` + `api/server.py`. Empty
    list == no silent fallback paths.

    Detection patterns (code-only):
      1. api/server.py: any non-comment line that contains `WEB_DIR`
         AND a literal path containing the legacy `web` directory.
      2. Makefile: any non-comment line that contains `web/` AND a
         fallback construct (`fallback`, `else`, `||`).

    The current source tree (Phase 6a) returns [] — the atomic cutover
    unit does not carry a silent fallback to the legacy runtime. Any
    deviation MUST fail closed so PR 3e cannot ship with a forbidden
    fallback path.
    """
    fallback_paths = []

    server_py = repo_root / "api" / "server.py"
    if server_py.is_file():
        for i, line in enumerate(server_py.read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue  # skip comments — predecessor documentation
            if "WEB_DIR" not in line:
                continue
            # The legacy path signature: WEB_DIR <reassigned to> "web"
            # or 'web' (or with subdirectory like "web/dist"). The
            # current post-cut line uses "/out" and is excluded.
            if re.search(r"""WEB_DIR\s*=.*["']web(/|["'])""", line):
                fallback_paths.append(
                    f"{server_py}:{i}: {line.strip()}")

    makefile = repo_root / "Makefile"
    if makefile.is_file():
        for i, line in enumerate(makefile.read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            low = line.lower()
            # Makefile fallback signature: a `web/` reference combined
            # with a fallback construct.
            if "web/" in line and (
                "fallback" in low or re.search(r"\|\||else", low)
            ):
                fallback_paths.append(
                    f"{makefile}:{i}: {line.strip()}")

    return fallback_paths


# ── Subset-only detection ────────────────────────────────────────────────

def detect_subset_only(manifest):
    """Return the subset name if the manifest declares a subset-only
    cutover, else None.

    A subset-only cutover is detected when ANY of the 26 §3.1
    consumers still carries Tier-1 (legacy pre-cut) selection:
    `replacement.path` equals the on-disk legacy `current_path`. The
    activated working-copy manifest (Tier-2) carries
    `replacement.path != current_path` for every consumer; the
    predecessor (Tier-1) carries the legacy pre-cut selection where
    `replacement.path == current_path` for every consumer.

    The four subset names map to specific failure signatures:
      - `web_dir_only`: every consumer still Tier-1 (the manifest
        has not been flipped at all; the operator only repointed
        WEB_DIR).
      - `consumers_only`: a partial flip — some consumers are
        Tier-2, others are still Tier-1. Forbidden by the atomic
        invariant.
      - `makefile_only`: same surface as `web_dir_only` from the
        manifest's perspective (manifest unchanged); distinct only
        in the on-disk state, not detectable from the manifest.
      - `artifact_only`: same as `web_dir_only` (manifest unchanged).

    Returns the subset name to surface in stderr, or None when the
    manifest is fully activated (every consumer is Tier-2).
    """
    consumers = manifest.get("consumers", [])
    if not isinstance(consumers, list) or not consumers:
        return None

    legacy_count = 0
    post_cut_count = 0
    for c in consumers:
        if not isinstance(c, dict):
            continue
        repl = c.get("replacement")
        if not isinstance(repl, dict):
            continue
        if repl.get("status") != "selected":
            legacy_count += 1
            continue
        path = repl.get("path", "")
        current = c.get("current_path", "")
        # Tier-2 signature: replacement.path differs from
        # current_path (post-cut selection points at the build
        # artifact, not the legacy on-disk path).
        if (isinstance(path, str) and path
                and isinstance(current, str) and current
                and path != current):
            post_cut_count += 1
        else:
            legacy_count += 1

    if post_cut_count == len(consumers):
        return None  # fully activated
    if legacy_count == len(consumers):
        return "web_dir_only"  # no consumers flipped → subset
    # Mixed: partial activation. Both `consumers_only` and
    # `artifact_only` surface this; we name `consumers_only` because
    # the manifest IS partially flipped (mixed Tier-1 / Tier-2).
    return "consumers_only"


# ── cutover-rehearsal.json emit ──────────────────────────────────────────

def emit_rehearsal_artifact(rehearsal_out, *, manifest_path, captured_at,
                            silent_fallback_paths, g3_exit,
                            consumer_readiness):
    """Atomically write cutover-rehearsal.json with the G6 contract.

    Required fields (pinned by tests/test_rehearse_cutover.py):
      - gate: "G6"
      - status: "ready" iff g3_exit == 0 and silent_fallback_paths == [],
                else "blocked"
      - captured_at: ISO-8601 UTC timestamp (YYYY-MM-DDTHH:MM:SSZ)
      - manifest_path: absolute path to the activated working-copy manifest
      - activation_complete: g3_exit == 0 and silent_fallback_paths == []
      - unselected_count: from CONSUMER-READINESS.json (default 0)
      - silent_fallback_paths: list (empty for clean source)
      - g3_tier2_exit_code: int (0 on pass)
      - consumer_readiness: dict or None (the G3 verifier's artifact)
    """
    activation_complete = g3_exit == 0 and not silent_fallback_paths
    status = "ready" if activation_complete else "blocked"

    if isinstance(consumer_readiness, dict):
        unselected = consumer_readiness.get("unselected_count", 0)
    else:
        unselected = 0

    payload = {
        "schema_version": "1.0.0",
        "gate": "G6",
        "status": status,
        "captured_at": captured_at,
        "manifest_path": str(manifest_path),
        "activation_complete": activation_complete,
        "unselected_count": int(unselected) if unselected is not None else 0,
        "silent_fallback_paths": list(silent_fallback_paths),
        "g3_tier2_exit_code": int(g3_exit),
        "consumer_readiness": consumer_readiness,
    }
    _atomic_write(rehearsal_out,
                  json.dumps(payload, indent=2, sort_keys=True).encode() + b"\n")


# ── apply-progress.md G6 footer flip ─────────────────────────────────────

_G6_FOOTER_RE = re.compile(
    r"G6 \(cutover rehearsal\) \*\*[^*]+\*\*",
    flags=re.MULTILINE,
)


def update_apply_progress_g6(apply_progress_path, *, captured_at,
                             rehearsal_out, silent_fallback_paths):
    """Flip the G6 footer in apply-progress.md to PASS recorded.

    Strict-TDD contract — this function is ONLY called when the real
    rehearsal exits 0 with no silent fallback paths. Test mode
    (`--no-update-apply-progress`), subset-only mode, G3 failure, and
    silent-fallback detection ALL skip this path entirely. The apply
    worker is the human-side authority that may flip G6; this
    function performs the line-level edit on its behalf when the
    runtime conditions are met.

    Conservative flip rule:
      - The current footer line MUST start with
        "G6 (cutover rehearsal) **".
      - The current G6 footer MUST NOT already contain
        "PASS recorded" (idempotent: a second invocation is a no-op).
        NOTE: the rest of the file may contain "PASS recorded" for
        other gates (G1, G2, G3 Tier-1); only the G6 footer line
        itself is checked.
      - On match, the entire `**...**` body is replaced with the
        "PASS recorded" wording; the rest of the document is
        preserved byte-identically.
    Returns True if a flip was made, False otherwise.
    """
    if not apply_progress_path.is_file():
        return False
    text = apply_progress_path.read_text()
    match = _G6_FOOTER_RE.search(text)
    if not match:
        return False  # no G6 footer to flip
    current_body = match.group(0)
    if "PASS recorded" in current_body:
        return False  # already flipped — idempotent

    new_body = (
        f"PASS recorded — `cutover-rehearsal.json` captured at "
        f"`{captured_at}` (see `{rehearsal_out}`); atomic cutover unit "
        f"+ rollback unit consistent; "
        f"{len(silent_fallback_paths)} silent fallback paths detected; "
        f"apply worker may proceed to PR 3e."
    )
    new_text, n = _G6_FOOTER_RE.subn(
        f"G6 (cutover rehearsal) **{new_body}**", text, count=1)
    if n == 0:
        return False
    _atomic_write(apply_progress_path, new_text.encode())
    return True


# ── Atomic write helper ──────────────────────────────────────────────────

def _atomic_write(path, body):
    """Atomic write: write to <path>.<pid>.tmp, fsync-replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.",
                               dir=str(path.parent))
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


# ── Argument parsing + main entry point ──────────────────────────────────

def _build_arg_parser():
    ap = argparse.ArgumentParser(
        prog="rehearse_cutover.py",
        description=(
            "Phase 6b G6 cutover rehearsal — fail-closed dry-run of "
            "the atomic cutover unit. Exercises the G3 Tier-2 verifier "
            "via the shared run_g3_tier2 helper, emits versioned G6 "
            "evidence only on a complete rehearsal, and updates "
            "apply-progress.md G6 footer only if the real rehearsal "
            "exits 0. The rehearsal ALWAYS starts and owns an isolated "
            "static server (python -m http.server on an OS-picked "
            "free TCP port — never the ambient port 8765 owned by "
            "FastAPI) serving the real `out/` candidate; it never "
            "relies on an ambient port 8765 (the production FastAPI "
            "mount owns that address)."
        ),
    )
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST,
                    help="path to the activated working-copy manifest "
                         "(default: openspec/.../complete-taxa-frontend-"
                         "migration/cutover-manifest.json)")
    ap.add_argument("--out", default=None,
                    help="output directory for the G3 Tier-2 verifier; "
                         "default: a fresh tmp dir under /tmp. "
                         "CONSUMER-READINESS.json is written here.")
    ap.add_argument("--fixture-web-root", default=None,
                    help="candidate build directory the rehearsal's "
                         "controlled local static server serves. "
                         "Default: <repo_root>/out (the post-cut "
                         "React build). The script fails closed with "
                         "EXIT_G3 if the path does not exist or is "
                         "not a directory; the controlled server is "
                         "never bound to the ambient port 8765.")
    ap.add_argument("--rehearsal-out", default=None,
                    help="path to write cutover-rehearsal.json "
                         "(default: openspec/.../evidence/g6/"
                         "cutover-rehearsal.json; tests override to "
                         "keep production evidence untouched)")
    ap.add_argument("--apply-progress", default=None,
                    help="path to apply-progress.md for the G6 footer "
                         "flip (default: openspec/.../apply-progress.md; "
                         "tests use --no-update-apply-progress)")
    ap.add_argument("--repo-root", default=None,
                    help="repo root for venv + tools/ auto-detection; "
                         "default: parent.parent.parent.parent of "
                         "--manifest")
    ap.add_argument("--subset", default=None, choices=CUTOVER_UNIT_SUBSETS,
                    help="TEST MODE: simulate a subset-only cutover; "
                         "the script MUST fail closed (atomic cutover "
                         "is forbidden in subset form).")
    ap.add_argument("--no-update-apply-progress", action="store_true",
                    help="TEST MODE: do NOT modify apply-progress.md "
                         "even on success. Used by tests to keep the "
                         "production gate-status footer untouched.")
    return ap


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    ap = _build_arg_parser()
    try:
        ns = ap.parse_args(argv)
    except SystemExit:
        return EXIT_USAGE

    manifest_path = Path(ns.manifest).resolve()
    if not manifest_path.is_file():
        print(f"[rehearse_cutover] manifest missing: {manifest_path}",
              file=sys.stderr)
        return EXIT_USAGE
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        print(f"[rehearse_cutover] manifest invalid JSON: {exc}",
              file=sys.stderr)
        return EXIT_USAGE

    # ── Step 1: subset-only detection (fail-closed) ────────────────────
    subset_name = ns.subset or detect_subset_only(manifest)
    if subset_name is not None:
        print(
            f"[rehearse_cutover] subset-only cutover detected: "
            f"{subset_name!r} — atomic cutover is forbidden; "
            f"rehearsal exits non-zero (no cutover-rehearsal.json, "
            f"no apply-progress.md update, no G3 verifier run).",
            file=sys.stderr,
        )
        return EXIT_SUBSET_ONLY

    # ── Resolve repo root for the silent-fallback scan ─────────────────
    if ns.repo_root:
        repo_root = Path(ns.repo_root).resolve()
    else:
        # Default: walk up from the manifest. The manifest lives at
        #   openspec/changes/<change>/cutover-manifest.json
        # so the repo root is 4 levels up.
        repo_root = manifest_path.parent.parent.parent.parent

    # ── Resolve the controlled static server's fixture-web-root ──────
    # The rehearsal ALWAYS owns a controlled local static server
    # serving the candidate build (the post-cut React build under
    # ``out/``); it never relies on the production-runtime uvicorn
    # path (which would bind the ambient port 8765 owned by
    # FastAPI). The default fixture-web-root is ``<repo_root>/out``;
    # the ControlledStaticServer class validates the path before
    # spawn and raises RuntimeError on missing / non-dir paths
    # (which the shared run_g3_tier2 helper surfaces as EXIT_G3).
    if ns.fixture_web_root:
        fixture_web_root = Path(ns.fixture_web_root).resolve()
    else:
        fixture_web_root = (repo_root / "out").resolve()

    # ── Step 2: silent-fallback-path scan (fail-closed) ────────────────
    silent_fallback_paths = scan_silent_fallback_paths(repo_root)
    if silent_fallback_paths:
        print(
            f"[rehearse_cutover] FAIL-CLOSED: {len(silent_fallback_paths)} "
            f"silent fallback path(s) detected:",
            file=sys.stderr,
        )
        for p in silent_fallback_paths:
            print(f"  {p}", file=sys.stderr)
        return EXIT_REHEARSAL

    # ── Step 3: run G3 Tier-2 verifier through the shared helper ───────
    if ns.out:
        out_dir = Path(ns.out).resolve()
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="rehearse-cutover-"))
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        g3_exit = run_g3_tier2(
            manifest_path=manifest_path,
            out_dir=out_dir,
            repo_root=repo_root,
            fixture_web_root=fixture_web_root,
        )
    except RuntimeError as exc:
        # Controlled-static-server lifecycle failure (missing /
        # non-dir web root, bind error, non-ready-within-timeout,
        # or any other RuntimeError raised by
        # ControlledStaticServer.__enter__ / run_g3_tier2).
        # Fail-closed: no cutover-rehearsal.json emitted, no
        # apply-progress.md update.
        print(
            f"[rehearse_cutover] controlled static server / G3 "
            f"Tier-2 verifier failed: {exc}; fail-closed (no "
            f"cutover-rehearsal.json emitted, no "
            f"apply-progress.md update).",
            file=sys.stderr,
        )
        return EXIT_G3
    if g3_exit != 0:
        print(
            f"[rehearse_cutover] G3 Tier-2 verifier exited {g3_exit}; "
            f"no CONSUMER-READINESS.json → fail-closed (no "
            f"cutover-rehearsal.json emitted, no apply-progress.md "
            f"update).",
            file=sys.stderr,
        )
        return EXIT_G3

    consumer_readiness_path = out_dir / "CONSUMER-READINESS.json"
    consumer_readiness = None
    if consumer_readiness_path.is_file():
        try:
            consumer_readiness = json.loads(
                consumer_readiness_path.read_text())
        except json.JSONDecodeError:
            consumer_readiness = None

    # ── Step 4: emit versioned G6 evidence (only on complete rehearsal) ─
    captured_at = _utcnow_iso()

    if ns.rehearsal_out:
        rehearsal_out = Path(ns.rehearsal_out).resolve()
    else:
        rehearsal_out = (repo_root / DEFAULT_REHEARSAL_OUT).resolve()

    emit_rehearsal_artifact(
        rehearsal_out,
        manifest_path=manifest_path,
        captured_at=captured_at,
        silent_fallback_paths=silent_fallback_paths,
        g3_exit=g3_exit,
        consumer_readiness=consumer_readiness,
    )

    # ── Step 5: update apply-progress.md G6 footer ONLY on real rehearsal
    if not ns.no_update_apply_progress:
        if ns.apply_progress:
            apply_progress_path = Path(ns.apply_progress).resolve()
        else:
            apply_progress_path = (
                repo_root / DEFAULT_APPLY_PROGRESS).resolve()
        update_apply_progress_g6(
            apply_progress_path,
            captured_at=captured_at,
            rehearsal_out=rehearsal_out,
            silent_fallback_paths=silent_fallback_paths,
        )

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())