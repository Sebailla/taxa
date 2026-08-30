"""G3 consumer-readiness verifier — fail-closed manifest contract test.

Per design.md §3.3.3 (G3) and the G3 manifest's `verifier_contract_summary`:
emit CONSUMER-READINESS.json only if every consumer is fully selected AND
every verification.command exits 0 against the candidate build; otherwise
exit non-zero and emit no CONSUMER-READINESS.json. No silent fallback to
legacy files is permitted under any branch.

Slice (PR3d reconstruction): adds opt-in controlled local-server lifecycle
(`--serve` → spawn uvicorn around checks, terminate on exit) and venv-aware
pytest command execution (`--venv` / `--repo-root` → rewrite leading
`pytest` tokens to the venv python). Both features are strictly opt-in;
the existing fail-closed contract is preserved.

Slice (PR3d fixture-serve reconstruction): adds a controlled **fixture-
serve** branch via `--serve --fixture-web-root <dir>`. Spawns
`python -m http.server <isolated_free_port> --directory <dir>` against
the merged self-contained fixture's web/ tree on an OS-picked free TCP
port (never the legacy 8765), and rewrites each consumer's
`verification.command` URL from `127.0.0.1:8765` to the picked port so
manifest consumers continue to validate against the fixture. The
`--serve` lifecycle remains strictly opt-in: without `--serve`,
`--fixture-web-root` is a silent no-op. The pre-existing
fail-closed contract is preserved across all branches.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.error import URLError


EXIT_OK = 0
EXIT_USAGE = 1
EXIT_MANIFEST = 4
EXIT_CHECK = 5
EXIT_SERVER = 6   # local server did not become ready within timeout

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


def find_venv_python(repo_root: Path) -> Path | None:
    """Return `<repo_root>/.venv/bin/python` (POSIX) or
    `<repo_root>/.venv/Scripts/python.exe` (Windows), or None if absent.
    Read-only: the verifier NEVER creates a venv."""
    for sub, name in (("bin", "python"), ("Scripts", "python.exe")):
        cand = (repo_root / ".venv" / sub / name).resolve()
        if cand.is_file():
            return cand
    return None


def rewrite_pytest_for_venv(cmd: str, venv_python: Path) -> str:
    """If `cmd` starts with the bare token `pytest` (followed by whitespace
    or end-of-string), rewrite to `"<venv_python>" -m pytest <rest>`. Else
    return cmd unchanged. Fail-closed: only the leading bare token triggers
    the rewrite; `pytest-foo`, `python -m pytest`, or mid-string mentions
    of `pytest` are left alone."""
    leading = cmd[:len(cmd) - len(cmd.lstrip())]
    body = cmd.lstrip()
    if not body.startswith("pytest"):
        return cmd
    rest = body[len("pytest"):]
    if rest and not rest[0].isspace():
        return cmd  # not a bare `pytest` token (e.g. `pytest-foo`)
    sep = " " if rest else ""
    quoted = f'"{venv_python}" -m pytest{sep}{rest}'
    return leading + quoted


def pick_free_port(host: str = "127.0.0.1") -> int:
    """Bind to (host, 0) so the OS picks a free TCP port, then release
    the socket and return the port. Idiomatic test-harness approach;
    there's an inherent race between close and the subsequent bind,
    but it's the standard pattern and good enough for a verifier
    fixture path that runs locally. Read-only: does NOT mutate state."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, 0))
        return s.getsockname()[1]
    finally:
        s.close()


def rewrite_command_port(cmd: str, old_port: int, new_port: int) -> str:
    """Replace literal `127.0.0.1:<old_port>` with `127.0.0.1:<new_port>`
    in `cmd`. Only the precise URL pattern is substituted; unrelated
    text is preserved (no regex, no tokenization). Used by the
    fixture-serve path to redirect manifest consumers from the legacy
    8765 to the isolated free port picked for the fixture."""
    return cmd.replace(f"127.0.0.1:{old_port}", f"127.0.0.1:{new_port}")


class LocalServer:
    """Controlled local-server lifecycle for `verification.command` checks.
    Two controlled-server modes are supported, both opt-in via `--serve`:

    1. **uvicorn / FastAPI** (default, `fixture_web_root=None`): spawns
       `python -m uvicorn api.server:app` on `127.0.0.1:<port>` — the
       production-runtime branch. Healthcheck polls
       `http://127.0.0.1:<port>/api/health`.
    2. **python -m http.server / merged self-contained fixture**
       (`fixture_web_root=<dir>`): spawns `python -m http.server
       <isolated_free_port> --directory <dir>` against the merged
       self-contained fixture's web/ directory on an OS-picked free
       port (the "isolated port" — never the legacy 8765). Healthcheck
       polls `http://127.0.0.1:<picked_port>/index.html`.

    Strict fail-closed: only spawns when `enable=True`; always
    terminates on context exit (success or error); never falls back to
    a started server if the healthcheck fails. Fixture-serve path
    additionally validates that `<dir>` exists and is a directory
    before binding.

    Spawn / wait_ready / terminate are method hooks so tests can patch
    each step in isolation via monkeypatch.
    """
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 8765
    DEFAULT_HEALTHCHECK = "http://127.0.0.1:8765/api/health"
    DEFAULT_FIXTURE_HEALTHCHECK_PATH = "/index.html"
    READY_TIMEOUT_S = 30.0
    TERMINATE_GRACE_S = 5.0

    def __init__(self, *, enable: bool,
                 host: str = DEFAULT_HOST,
                 port: int = DEFAULT_PORT,
                 venv_python: Path | None = None,
                 repo_root: Path | None = None,
                 healthcheck: str = DEFAULT_HEALTHCHECK,
                 fixture_web_root: Path | None = None,
                 ready_timeout: float = READY_TIMEOUT_S,
                 log=_log) -> None:
        self.enable = enable
        self.host = host
        self.port = port
        self.venv_python = venv_python
        self.repo_root = repo_root
        self.healthcheck = healthcheck
        self.fixture_web_root = (Path(fixture_web_root).resolve()
                                 if fixture_web_root is not None else None)
        self.ready_timeout = ready_timeout
        self.log = log
        self.proc = None

    def _build_argv(self) -> list[str]:
        py = str(self.venv_python) if self.venv_python else sys.executable
        if self.fixture_web_root is not None:
            # Fixture-serve: python -m http.server <port> --directory <root>
            return [py, "-m", "http.server", str(self.port),
                    "--directory", str(self.fixture_web_root)]
        # Default: uvicorn + FastAPI on a fixed port.
        return [py, "-m", "uvicorn", "api.server:app",
                "--host", self.host, "--port", str(self.port),
                "--log-level", "warning"]

    def _spawn(self, argv, **kwargs):
        return subprocess.Popen(argv, **kwargs)

    def _wait_ready(self) -> bool:
        deadline = time.monotonic() + self.ready_timeout
        while time.monotonic() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                return False  # died during startup
            try:
                with urllib.request.urlopen(self.healthcheck, timeout=1) as r:
                    if r.status == 200:
                        return True
            except (URLError, OSError):
                time.sleep(0.1)
        return False

    def _terminate(self) -> None:
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
        if not self.enable:
            return self
        # Fixture-serve path: validate the web root, pick an isolated free
        # port, and point the healthcheck at the fixture's /index.html.
        # Fail-closed: any pre-spawn invariant failure aborts BEFORE spawn.
        if self.fixture_web_root is not None:
            if not self.fixture_web_root.exists():
                raise RuntimeError(
                    f"--fixture-web-root path does not exist: "
                    f"{self.fixture_web_root}")
            if not self.fixture_web_root.is_dir():
                raise RuntimeError(
                    f"--fixture-web-root is not a directory: "
                    f"{self.fixture_web_root}")
            self.port = pick_free_port(self.host)
            self.healthcheck = (
                f"http://{self.host}:{self.port}"
                f"{self.DEFAULT_FIXTURE_HEALTHCHECK_PATH}")
        argv = self._build_argv()
        cwd = str(self.repo_root) if self.repo_root else None
        label = ("http.server" if self.fixture_web_root is not None
                 else "uvicorn")
        self.log("verify_consumers",
                 f"starting local server ({label}) cwd={cwd}: {argv}")
        self.proc = self._spawn(argv, cwd=cwd,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE)
        if not self._wait_ready():
            self._terminate()
            raise RuntimeError(
                f"local server did not become ready at {self.healthcheck} "
                f"within {self.ready_timeout:.1f}s")
        return self

    def __exit__(self, exc_type, exc, tb):
        self._terminate()
        return False


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


def _check_all(consumers: list[dict],
               *, venv_python: Path | None = None,
               port_rewrite: tuple[int, int] | None = None
               ) -> list[tuple[str, str]]:
    """Return [(id, reason)] for every consumer whose check failed.

    Two opt-in rewrites are applied (both strictly opt-in):

    - `venv_python` set: `pytest`-prefixed commands are rewritten to
      use the venv python (controlled, opt-in via `--venv` /
      `--repo-root`).
    - `port_rewrite=(old, new)` set: literal `127.0.0.1:<old>` URLs in
      each command are rewritten to `127.0.0.1:<new>`. Used by the
      fixture-serve path to redirect manifest consumers from the
      legacy 8765 to the isolated free port picked at server spawn."""
    failures: list[tuple[str, str]] = []
    for c in consumers:
        if not isinstance(c, dict):
            continue
        ver = c.get("verification") or {}
        cmd = ver.get("command")
        if not isinstance(cmd, str):
            failures.append((str(c.get("id")), "verification.command not string"))
            continue
        if venv_python is not None:
            cmd = rewrite_pytest_for_venv(cmd, venv_python)
        if port_rewrite is not None:
            cmd = rewrite_command_port(cmd, port_rewrite[0], port_rewrite[1])
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
    ap.add_argument("--serve", action="store_true",
                    help="controlled local-server lifecycle: spawn uvicorn "
                         "before checks, terminate after.")
    ap.add_argument("--fixture-web-root", default=None,
                    help="merged self-contained fixture path: spawn "
                         "python -m http.server against <dir> on an "
                         "isolated free port (must be combined with "
                         "--serve). Each consumer's verification.command "
                         "is rewritten from 127.0.0.1:<legacy> to the "
                         "picked port. <dir> must exist and be a "
                         "directory (fail-closed otherwise).")
    ap.add_argument("--venv", default=None,
                    help="python executable to use when a "
                         "verification.command starts with `pytest` "
                         "(rewrites to `<venv> -m pytest ...`).")
    ap.add_argument("--repo-root", default=None,
                    help="repo root for `.venv/bin/python` auto-detection; "
                         "defaults to the manifest's directory.")
    try:
        ns = ap.parse_args(argv)
    except SystemExit:
        _log("verify_consumers",
             "usage: verify_consumers.py --manifest <path> --out <path> "
             "[--serve] [--fixture-web-root <dir>] [--venv <python>] "
             "[--repo-root <dir>]")
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

    # Resolve venv (opt-in: explicit --venv wins; else auto-detect from
    # --repo-root, falling back to the manifest's parent directory).
    repo_root = (Path(ns.repo_root).resolve() if ns.repo_root
                 else mp.parent)
    venv_python = (Path(ns.venv).resolve() if ns.venv
                   else find_venv_python(repo_root))

    # Fixture-serve: opt-in via `--serve --fixture-web-root <dir>`.
    # `--fixture-web-root` alone (without `--serve`) is a SILENT no-op:
    # the verifier behaves exactly as if `--fixture-web-root` were
    # absent (no server spawn, no port rewriting). This keeps the
    # controlled lifecycle strictly opt-in via `--serve` without
    # rejecting valid manifest checks that don't need a server.
    fixture_root_arg = (Path(ns.fixture_web_root).resolve()
                        if ns.fixture_web_root else None)
    if fixture_root_arg is not None and not ns.serve:
        fixture_root_arg = None  # silent no-op

    # Legacy port the manifest commands target. The fixture-serve path
    # rewrites `:8765` → isolated free port. This is the source port for
    # rewrite_command_port; uvicorn + FastAPI mode (default) keeps 8765.
    legacy_port = LocalServer.DEFAULT_PORT  # 8765

    try:
        with LocalServer(enable=ns.serve,
                         venv_python=venv_python,
                         repo_root=repo_root,
                         fixture_web_root=fixture_root_arg) as srv:
            # If fixture-serve picked an isolated port, rewrite consumer
            # commands from the legacy 8765 to the picked port. Otherwise
            # (uvicorn on 8765 or --serve disabled), no rewrite.
            port_rewrite: tuple[int, int] | None = None
            if (srv.fixture_web_root is not None
                    and srv.port != legacy_port):
                port_rewrite = (legacy_port, srv.port)
            failures = _check_all(consumers, venv_python=venv_python,
                                   port_rewrite=port_rewrite)
    except RuntimeError as exc:
        _log("verify_consumers", f"server lifecycle error: {exc}")
        return EXIT_SERVER
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
