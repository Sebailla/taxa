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
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from pathlib import Path
from typing import cast
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


def _validate_base_and_blocked(manifest: dict) -> list[str]:
    """Validate manifest base structure and every blocked
    status/reason. Does NOT validate non-blocked non-HTTP
    `verification.assertions` schemas — that runs separately only
    after the blocked-gate preflight decides no valid blockers exist
    (Follow-up 31 reorder).

    Returns list of fail-closed error strings. Empty == pass.
    Malformed `verification.status`, missing/blank
    `verification.blocked_reason`, or any other base structural
    error MUST surface here so the verifier cannot bypass
    EXIT_MANIFEST by short-circuiting on a malformed blocker."""
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
        # Follow-up 30: optional `verification.status == "blocked"` with a
        # required non-empty trimmed `verification.blocked_reason`. Omitted
        # status preserves current behavior; any other status value
        # (including null) fails schema validation; a `blocked_reason`
        # without blocked status fails schema validation. Selected
        # `replacement.status` and `activation_status` checks above remain
        # unchanged. A valid blocked consumer is exempt from the non-HTTP
        # `verification.assertions` requirement (skipped below; the
        # Follow-up 31 reorder moves that check to a separate pass that
        # only runs when no valid blockers exist).
        ver_status = ver.get("status")
        if "status" in ver:
            if ver_status != "blocked":
                errs.append(f"consumers[{i}] ({cid}) verification.status must be "
                            f"'blocked' or omitted (got {ver_status!r})")
            elif (not isinstance(ver.get("blocked_reason"), str)
                    or not ver["blocked_reason"].strip()):
                errs.append(f"consumers[{i}] ({cid}) verification.blocked_reason "
                            f"must be non-empty trimmed string when "
                            f"verification.status is 'blocked'")
        elif "blocked_reason" in ver:
            errs.append(f"consumers[{i}] ({cid}) verification.blocked_reason "
                        f"requires verification.status == 'blocked'")
        for k in REQUIRED_PER_VERIFICATION:
            if k not in ver:
                errs.append(f"consumers[{i}] ({cid}) verification missing {k!r}")
        if not isinstance(ver.get("command"), str):
            errs.append(f"consumers[{i}] ({cid}) verification.command must be string")
        if not isinstance(ver.get("expect"), str):
            errs.append(f"consumers[{i}] ({cid}) verification.expect must be string")
    return errs


def _validate_unblocked_assertions(manifest: dict) -> list[str]:
    """Validate non-empty structured `verification.assertions` only
    for unblocked non-HTTP consumers. Skipped when the
    blocked-gate preflight short-circuits (Follow-up 31 reorder).

    Skipped categories: blocked consumers (exempt by contract),
    HTTP-shape `verification.expect` (route through the controlled
    helper instead)."""
    errs: list[str] = []
    consumers = manifest.get("consumers")
    if not isinstance(consumers, list):
        return errs  # base validation already reported
    for i, c in enumerate(consumers):
        if not isinstance(c, dict):
            continue
        ver = c.get("verification") or {}
        if not isinstance(ver, dict):
            continue  # base validation already reported
        cid = c.get("id")
        # Blocked consumers: exempt from assertion-schema.
        if ver.get("status") == "blocked":
            continue
        expected = ver.get("expect")
        if not isinstance(expected, str):
            continue  # base validation already reported
        # HTTP-shape expectations route through the helper; not
        # affected by the non-HTTP assertion-schema contract.
        if is_http_status_expectation(expected):
            continue
        errs.extend(_validate_assertions_schema(
            ver.get("assertions"),
            prefix=f"consumers[{i}] ({cid})"))
    return errs


def _validate_assertions_schema(assertions, *, prefix: str) -> list[str]:
    """Validate non-empty structured assertions for non-HTTP consumers.
    The two supported types have strict schemas; booleans are not integers
    for numeric bounds."""
    def _int_nn(v):
        return isinstance(v, int) and not isinstance(v, bool) and v >= 0
    errs: list[str] = []
    if not isinstance(assertions, list) or not assertions:
        errs.append(f"{prefix} verification.assertions must be "
                    f"non-empty list")
        return errs
    for j, a in enumerate(assertions):
        a_prefix = f"{prefix} verification.assertions[{j}]"
        if not isinstance(a, dict):
            errs.append(f"{a_prefix} must be an object")
            continue
        atype = a.get("type")
        if atype == "stdout_regex":
            p, mn, mx = a.get("pattern"), a.get("min_matches"), a.get("max_matches")
            if not isinstance(p, str):
                errs.append(f"{a_prefix}.pattern must be string")
            if not _int_nn(mn):
                errs.append(f"{a_prefix}.min_matches must be nonnegative int")
            if not _int_nn(mx):
                errs.append(f"{a_prefix}.max_matches must be nonnegative int")
            if (isinstance(mn, int) and not isinstance(mn, bool)
                    and isinstance(mx, int) and not isinstance(mx, bool)
                    and cast(int, mn) > cast(int, mx)):
                errs.append(f"{a_prefix}.min_matches > max_matches")
            if isinstance(p, str):
                try:
                    re.compile(p)
                except re.error as e:
                    errs.append(f"{a_prefix}.pattern invalid regex: {e}")
        elif atype == "pytest_summary":
            if not _int_nn(a.get("min_passed")):
                errs.append(f"{a_prefix}.min_passed must be nonnegative int")
            if not _int_nn(a.get("max_skipped")):
                errs.append(f"{a_prefix}.max_skipped must be nonnegative int")
        else:
            errs.append(f"{a_prefix} unknown type {atype!r}")
    return errs


# ── HTTP-shape expectation helpers ─────────────────────────────────────
# The G3 manifest's `verification.expect` carries two semantic classes:
#   (1) HTTP-shape: pure 3-digit status code, optionally followed by
#       ' for each' (e.g. "200", "200 for each") — produced by
#       `curl -w '%{http_code}'` and a loop of curl calls. These MUST
#       be validated against the actual emitted status codes (not just
#       the shell exit code, which is always 0 when curl connected).
#   (2) Non-HTTP-shape: arbitrary descriptive text ("ok", "1 passed",
#       grep output, sed output, etc.) — the verifier requires structured
#       `verification.assertions` and evaluates them against captured
#       stdout; shell exit status alone is not sufficient.
_HTTP_STATUS_EXPECT_RE = re.compile(
    r"^\s*\d{3}(\s+for\s+each)?\s*$")


def is_http_status_expectation(expected: str) -> bool:
    """Return True iff `expected` looks like an HTTP-status assertion
    (3-digit code, optionally followed by ' for each'). The verifier
    uses this gate to decide whether the consumer's command needs to
    be routed through the controlled HTTP-status verifier helper
    instead of trusting the shell exit code alone."""
    return bool(_HTTP_STATUS_EXPECT_RE.match(expected.strip()))


def find_check_http_status_script(repo_root: Path) -> Path | None:
    """Return the absolute path to the controlled HTTP-status verifier
    helper (`tools/g3-legacy-fixture/scripts/check_http_status.py`),
    searching up from `repo_root`, else None. Read-only: the
    verifier NEVER creates the file. Discovery walks up the directory
    tree until it finds `tools/g3-legacy-fixture/scripts/check_http_status.py`
    OR the filesystem root is reached. This matches how the fixture
    tree is shipped in this repo and lets the verifier discover the
    helper even when `--repo-root` resolves to a sub-directory (e.g.
    the manifest's parent directory under
    `openspec/changes/migrate-nextjs-tailwind4/`). When the helper is
    absent (e.g. a CI runner without the fixture), the caller MUST
    treat HTTP-shape expectations as fail-closed."""
    cur = Path(repo_root).resolve()
    while True:
        cand = cur / "tools" / "g3-legacy-fixture" / "scripts" / "check_http_status.py"
        if cand.is_file():
            return cand
        parent = cur.parent
        if parent == cur:
            return None
        cur = parent


def find_venv_python(repo_root: Path) -> Path | None:
    """Return `<repo_root>/.venv/bin/python` (POSIX) or
    `<repo_root>/.venv/Scripts/python.exe` (Windows), or None if absent.
    Read-only: the verifier NEVER creates a venv."""
    for sub, name in (("bin", "python"), ("Scripts", "python.exe")):
        cand = repo_root / ".venv" / sub / name
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


def _run_check(cmd: str, *, cwd: Path | None = None,
               timeout: int = 60) -> int:
    """Run verification.command via shell; return exit code only.
    HTTP-shape expectations route through the helper script and
    discard stdout (the helper does its own validation)."""
    try:
        r = subprocess.run(["/bin/sh", "-c", cmd], cwd=cwd,
                           capture_output=True, text=True, check=False,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124
    except OSError:
        return 2
    return r.returncode


def _run_check_with_stdout(cmd: str, *, cwd: Path | None = None,
                            timeout: int = 60) -> tuple[int, str]:
    """Run verification.command via shell; return (rc, stdout).
    Used for non-HTTP expectations where the verifier evaluates
    `verification.assertions` against captured stdout. Always
    returns a `str` for stdout: bytes (observed in hosted CI run
    36424915843 even though the verifier requests `text=True`) are
    decoded UTF-8 with replacement so `_evaluate_assertions` never
    sees bytes and downstream `re.findall(str, stdout)` cannot raise
    TypeError."""
    try:
        r = subprocess.run(["/bin/sh", "-c", cmd], cwd=cwd,
                           capture_output=True, text=True, check=False,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return (124, "")
    except OSError:
        return (2, "")
    out = r.stdout
    if isinstance(out, bytes):
        out = out.decode("utf-8", errors="replace")
    return (r.returncode, out)


def _check_all(consumers: list[dict],
               *, venv_python: Path | None = None,
               port_rewrite: tuple[int, int] | None = None,
               check_http_script: Path | None = None,
               check_cwd: Path | None = None,
               ) -> list[tuple[str, str]]:
    """Return [(id, reason)] for every consumer whose check failed.

    Opt-in rewrites: `venv_python` rewrites pytest-prefixed commands
    to use the venv python; `port_rewrite=(old, new)` rewrites
    127.0.0.1:<old> URLs (fixture-serve port redirection).

    HTTP-shape expects route through the controlled helper
    (`<check_http_script>`); missing helper fails closed.

    Non-HTTP expects run with `check_cwd` (None = inherit verifier's
    CWD; explicit --repo-root becomes subprocess CWD). Stdout is
    captured and evaluated against structured assertions (AND).
    Nonzero exit ALWAYS fails (assertions complement, never replace,
    the shell-exit gate).
    """
    failures: list[tuple[str, str]] = []
    for c in consumers:
        if not isinstance(c, dict):
            continue
        ver = c.get("verification") or {}
        cmd = ver.get("command")
        expected = ver.get("expect")
        cid = str(c.get("id"))
        if not isinstance(cmd, str):
            failures.append((cid, "verification.command not string"))
            continue
        if venv_python is not None:
            cmd = rewrite_pytest_for_venv(cmd, venv_python)
        if port_rewrite is not None:
            cmd = rewrite_command_port(cmd, port_rewrite[0], port_rewrite[1])
        is_http = (isinstance(expected, str)
                   and is_http_status_expectation(expected))
        if is_http:
            if check_http_script is None:
                failures.append((cid,
                    "HTTP-shape expect requires the controlled "
                    "tools/g3-legacy-fixture/scripts/check_http_status.py "
                    "helper (not discoverable; fail-closed to avoid "
                    "silently trusting shell exit on a 404)"))
                continue
            run_cmd = (f'{shlex.quote(sys.executable)} '
                       f'{shlex.quote(str(check_http_script))} '
                       f'{shlex.quote(cmd)} '
                       f'{shlex.quote(cast(str, expected))}')
            rc = _run_check(run_cmd, cwd=check_cwd)
            if rc != 0:
                failures.append((cid,
                    f"verification.command exited {rc}"))
        else:
            rc, stdout = _run_check_with_stdout(cmd, cwd=check_cwd)
            if rc != 0:
                failures.append((cid, f"verification.command exited {rc}"))
                continue
            for err in _evaluate_assertions(
                    ver.get("assertions") or [], stdout):
                failures.append((cid, err))
    return failures


def _evaluate_assertions(assertions, stdout: str) -> list[str]:
    """Evaluate stdout_regex and real pytest-summary assertions with AND semantics.
    Command exit status is enforced separately by `_check_all`."""
    errs: list[str] = []
    for a in assertions:
        if not isinstance(a, dict):
            continue  # schema validation already reported
        atype = a.get("type")
        if atype == "stdout_regex":
            pattern = a.get("pattern")
            min_m = a.get("min_matches")
            max_m = a.get("max_matches")
            if not (isinstance(pattern, str)
                    and isinstance(min_m, int) and not isinstance(min_m, bool)
                    and isinstance(max_m, int) and not isinstance(max_m, bool)):
                continue  # schema validation already reported
            try:
                matches = re.findall(pattern, stdout)
            except re.error:
                continue
            count = len(matches)
            if not (min_m <= count <= max_m):
                errs.append(
                    f"stdout_regex failed: {count} matches not in "
                    f"[{min_m}, {max_m}]")
        elif atype == "pytest_summary":
            min_p = a.get("min_passed")
            max_s = a.get("max_skipped")
            if not (isinstance(min_p, int) and not isinstance(min_p, bool)
                    and isinstance(max_s, int) and not isinstance(max_s, bool)):
                continue  # schema validation already reported
            m_summary = re.search(
                r"(?m)^[ \t]*=*[ \t]*(\d+)[ \t]+passed\b([^\n]*)$",
                stdout)
            tail = m_summary.group(2) if m_summary else ""
            if (not m_summary or not re.search(
                    r"\bin[ \t]+[0-9]+(?:\.[0-9]+)?s\b", tail)):
                errs.append("pytest_summary failed: no pytest summary "
                            "line in stdout")
                continue
            passed_n = int(m_summary.group(1))
            m_skipped = re.search(r"(\d+)\s+skipped\b", tail)
            skipped_n = int(m_skipped.group(1)) if m_skipped else 0
            if passed_n < min_p:
                errs.append(f"pytest_summary failed: {passed_n} passed "
                            f"< {min_p}")
            if skipped_n > max_s:
                errs.append(f"pytest_summary failed: {skipped_n} skipped "
                            f"> {max_s}")
    return errs


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
                         "defaults to the manifest's directory. When "
                         "supplied, verification commands run with this "
                         "dir as CWD; when omitted, subprocess inherits "
                         "caller CWD (legacy).")
    ap.add_argument("--http-status-script", default=None,
                    help="explicit path to the controlled HTTP-status "
                         "helper (overrides repo auto-discovery). "
                         "Absolute paths used as-is; relative paths "
                         "resolve against --repo-root or caller CWD. "
                         "Must exist (fail-closed if missing).")
    try:
        ns = ap.parse_args(argv)
    except SystemExit:
        _log("verify_consumers",
             "usage: verify_consumers.py --manifest <path> --out <path> "
             "[--serve] [--fixture-web-root <dir>] [--venv <py>] "
             "[--repo-root <dir>] [--http-status-script <path>] "
             "(HTTP-shape auto-routes via controlled helper; "
             "non-HTTP expects require structured assertions; "
             "fail-closed on missing/malformed assertions or "
             "absent HTTP helper)")
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
    errs = _validate_base_and_blocked(manifest)
    if errs:
        for e in errs:
            _log("verify_consumers", e)
        return EXIT_MANIFEST
    consumers = manifest["consumers"]

    # Blocked-gate preflight (Follow-up 30 + 31 reorder): every
    # consumer with verification.status == "blocked" short-circuits
    # the entire run BEFORE non-HTTP assertion-schema validation,
    # venv/helper discovery, server construction, or any consumer
    # command. The diagnostic carries the consumer ID and the
    # human-supplied blocked_reason; readiness is never emitted;
    # EXIT_CHECK is returned so existing fail-closed exit semantics
    # are preserved, and no other selected check runs.
    #
    # Follow-up 31 explicitly reorders this BEFORE full assertion-
    # schema validation so an unrelated missing/malformed assertion
    # on an unblocked consumer cannot bypass a valid blocker and
    # force EXIT_MANIFEST. Base manifest structure + every blocked
    # status/reason has already been validated above; here we only
    # confirm the consumers carry the keys needed to read their
    # blocked_reason.
    blockers = [(str(c["id"]), str(c["verification"]["blocked_reason"]).strip())
                for c in consumers
                if c["verification"].get("status") == "blocked"]
    if blockers:
        for cid, reason in blockers:
            _log("verify_consumers", f"blocked: {cid}: {reason}")
        return EXIT_CHECK

    # No valid blockers: run full non-HTTP assertion-schema
    # validation only for unblocked non-HTTP consumers. Blocked
    # consumers and HTTP-shape expectations are skipped (Follow-up 31
    # reorder — the short-circuit above already handled blockers).
    unblocked_errs = _validate_unblocked_assertions(manifest)
    if unblocked_errs:
        for e in unblocked_errs:
            _log("verify_consumers", e)
        return EXIT_MANIFEST

    # Resolve venv (opt-in: explicit --venv wins; else auto-detect from
    # --repo-root, falling back to the manifest's parent directory).
    repo_root = (Path(ns.repo_root).resolve() if ns.repo_root
                 else mp.parent)
    venv_python = (Path(ns.venv).expanduser() if ns.venv
                   else find_venv_python(repo_root))

    # Resolve the controlled HTTP-status verifier script. Explicit
    # --http-status-script wins; else auto-detect under repo_root.
    explicit_http_script: Path | None = None
    if ns.http_status_script is not None:
        sp = Path(ns.http_status_script)
        if not sp.is_absolute():
            sp = (Path(ns.repo_root).resolve() if ns.repo_root
                  else Path(os.getcwd())) / sp
        sp = sp.resolve()
        if not sp.is_file():
            _log("verify_consumers", f"--http-status-script not found: {sp}")
            return EXIT_USAGE
        explicit_http_script = sp
    check_http_script = (explicit_http_script
                         or find_check_http_status_script(repo_root))
    check_cwd: Path | None = (Path(ns.repo_root).resolve()
                              if ns.repo_root else None)

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
                                   port_rewrite=port_rewrite,
                                   check_http_script=check_http_script,
                                   check_cwd=check_cwd)
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
