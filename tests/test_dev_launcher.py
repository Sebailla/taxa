"""ODD-DEV single-command dev-launcher contract tests.

Hermetic: every test substitutes `spawn_fn` / `health_fn` / `sleep_fn`
and `install_signals_fn` on the `Supervisor` with no-op fakes, so no
real uvicorn / Next.js / pnpm / network port is touched. The CLI
defaults and the `CommandSpec` factories are exercised against
explicit, narrow contracts:

  * `build_api_spec` produces the same uvicorn invocation `make api`
    uses (`--host 127.0.0.1 --port 8765`) so the existing port
    contract is shared with `make api`.
  * `build_frontend_spec` exports
    `NEXT_PUBLIC_TAXA_API_ORIGIN=http://127.0.0.1:8765` into the
    child environment so `pnpm run dev:local` honors the contract
    without any shell-level `VAR=…` prefix.
  * `Supervisor.run()` starts FastAPI first, waits for health
    readiness, then starts the frontend — never the reverse order.
  * A health-readiness timeout returns non-zero AND the frontend is
    never spawned in that scenario.
  * A SIGINT / SIGTERM terminates both children and returns the
    POSIX convention `128 + signum`.
  * Either child exiting unexpectedly stops the surviving child and
    returns non-zero.

Reference: odd/tasks/single-command-dev-launcher.md.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import re
import signal

import pytest

from scripts.dev import (  # type: ignore[import-not-found]
    DEFAULT_API_HEALTH_URL,
    DEFAULT_NEXT_API_ORIGIN,
    HealthCheckTimeout,
    NEXT_API_ORIGIN_ENV,
    Supervisor,
    build_api_spec,
    build_frontend_spec,
    wait_for_health,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
DEV_SCRIPT = SCRIPTS_DIR / "dev.py"


# ── Fakes for hermetic supervisor testing ────────────────────────────────


def _make_proc(name: str, pid: int):
    """Return (ChildProcess, state) where state['returncode'] is mutable
    so a test can mark a fake child as exited mid-run."""
    from scripts.dev import ChildProcess  # type: ignore[import-not-found]

    state: dict[str, Any] = {
        "returncode": None,
        "stop_called": 0,
        "last_grace": None,
    }

    def poll() -> int | None:
        return state["returncode"]

    def stop(grace_s: float) -> int | None:
        state["stop_called"] += 1
        state["last_grace"] = grace_s
        return state["returncode"]

    proc = ChildProcess(name=name, pid=pid, poll_fn=poll, stop_fn=stop)
    return proc, state


def _spawn_recorder(spawned: list, procs_by_name: dict[str, Any]):
    def spawn_fn(spec):
        spawned.append(spec)
        return procs_by_name[spec.name]
    return spawn_fn


def _cmd(name: str, argv: list[str], env: dict[str, str] | None = None):
    from scripts.dev import CommandSpec  # type: ignore[import-not-found]
    return CommandSpec(name=name, argv=argv, env=env or {}, cwd=None)


def _make_supervisor(
    *,
    api_proc,
    fe_proc,
    health_fn: Callable[..., None] | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    install_signals_fn: Callable[[Callable[[int, Any], None]], None]
        | None = None,
):
    """Build a `Supervisor` with default fakes and the supplied children."""
    spawned: list = []
    return spawned, Supervisor(
        api_spec=_cmd("api", ["fake-api"], env={"FOO": "1"}),
        frontend_spec=_cmd("frontend", ["fake-fe"],
                           env={NEXT_API_ORIGIN_ENV: DEFAULT_NEXT_API_ORIGIN}),
        health_url=DEFAULT_API_HEALTH_URL,
        health_timeout_s=1.0,
        health_poll_s=0.01,
        poll_interval_s=0.01,
        spawn_fn=_spawn_recorder(spawned, {"api": api_proc, "frontend": fe_proc}),
        # Default fake accepts whatever kwargs Supervisor.run()
        # decides to pass; the real wait_for_health receives the
        # timer kwargs (timeout_s, poll_s) by keyword after `url`.
        health_fn=health_fn or (lambda url, **_kw: None),
        sleep_fn=sleep_fn or (lambda _s: None),
        install_signals_fn=install_signals_fn or (lambda _h: None),
    )


# ── File / script existence ───────────────────────────────────────────────


def test_dev_script_exists_at_scripts_dev_py():
    """The launcher source must live at scripts/dev.py so
    python3 scripts/dev.py resolves from the repo root, and must only
    import standard-library modules (no new runtime dependency)."""
    assert DEV_SCRIPT.exists(), (
        f"scripts/dev.py missing at {DEV_SCRIPT}"
    )
    text = DEV_SCRIPT.read_text()
    imports = re.findall(r"^(?:from|import)\s+([A-Za-z_][\w]*)",
                        text, re.MULTILINE)
    forbidden = {"requests", "httpx", "aiohttp", "uvicorn", "fastapi",
                 "next", "pnpm"}
    leaked = {m for m in imports if m in forbidden}
    assert not leaked, (
        f"non-stdlib imports leaked into scripts/dev.py: {sorted(leaked)}"
    )


# ── CommandSpec factories ────────────────────────────────────────────────


def test_default_health_url_targets_localhost_8765():
    """The readiness URL pins 127.0.0.1:8765; the frontend env value
    mirrors it."""
    assert DEFAULT_API_HEALTH_URL == "http://127.0.0.1:8765/api/health"
    assert DEFAULT_NEXT_API_ORIGIN == "http://127.0.0.1:8765"


def test_build_api_spec_matches_make_api_uvicorn_invocation():
    """The api CommandSpec argv MUST be exactly the make api recipe so
    the new launcher shares `make api`'s bind contract."""
    spec = build_api_spec()
    assert spec.argv == [
        ".venv/bin/python3",
        "-m", "uvicorn",
        "api.server:app",
        "--host", "127.0.0.1",
        "--port", "8765",
    ], f"api argv drifted from make api: {spec.argv}"
    assert spec.name == "api"


def test_build_frontend_spec_invokes_pnpm_dev_local():
    """Frontend uses pnpm run dev:local (the canonical command) and
    exports NEXT_PUBLIC_TAXA_API_ORIGIN=DEFAULT_NEXT_API_ORIGIN."""
    spec = build_frontend_spec()
    assert spec.argv[:2] == ["pnpm", "run"], (
        f"expected pnpm run …, got {spec.argv}"
    )
    assert spec.argv[-1] == "dev:local"
    assert spec.env[NEXT_API_ORIGIN_ENV] == DEFAULT_NEXT_API_ORIGIN
    assert spec.name == "frontend"


def test_build_frontend_spec_api_origin_is_overridable():
    """build_frontend_spec(api_origin=...) propagates to env."""
    spec = build_frontend_spec(api_origin="http://example.test:9999")
    assert spec.env[NEXT_API_ORIGIN_ENV] == "http://example.test:9999"


# ── Supervisor: spawn order & readiness ─────────────────────────────────


def test_supervisor_spawns_api_before_frontend():
    """Spawn order MUST be api → frontend, gated on health_fn success.
    Frontend is NEVER spawned before the API is healthy."""
    api_proc, _ = _make_proc("api", pid=1001)
    fe_proc, _ = _make_proc("frontend", pid=1002)
    spawned, sup = _make_supervisor(api_proc=api_proc, fe_proc=fe_proc)
    # Drive the loop with a sleep_fn that delivers SIGINT on tick 1.
    counter = {"ticks": 0}

    def sleeping(_s):
        counter["ticks"] += 1
        if counter["ticks"] >= 1:
            sup._on_signal(signal.SIGINT, None)

    sup.sleep_fn = sleeping
    sup.run()
    assert [s.name for s in spawned] == ["api", "frontend"], (
        f"spawn order violated: {[s.name for s in spawned]}"
    )
    assert api_proc.returncode is None
    assert fe_proc.returncode is None


def test_supervisor_returns_nonzero_when_health_times_out():
    """If health_fn raises HealthCheckTimeout, supervisor exits non-zero
    AND the frontend is never spawned (only the API)."""
    api_proc, _ = _make_proc("api", pid=2001)
    fe_proc, _ = _make_proc("frontend", pid=2002)

    def failing_health(url, **kw):
        # Match the keyword-only signature that
        # `Supervisor.run()` actually uses against the real default.
        raise HealthCheckTimeout(url, kw["timeout_s"])

    spawned, sup = _make_supervisor(
        api_proc=api_proc, fe_proc=fe_proc, health_fn=failing_health,
    )
    code = sup.run()
    assert code != 0, f"expected non-zero exit, got {code}"
    assert len(spawned) == 1, (
        f"frontend must not be spawned when health fails; "
        f"spawned={[s.name for s in spawned]}"
    )
    assert spawned[0].name == "api"


def test_supervisor_does_not_spawn_frontend_when_api_exits_pre_health():
    """If the API exits before health is checked, supervisor returns
    non-zero and the frontend is never spawned."""
    api_proc, api_state = _make_proc("api", pid=3001)
    fe_proc, _ = _make_proc("frontend", pid=3002)
    api_state["returncode"] = 137  # api died fast
    spawned, sup = _make_supervisor(api_proc=api_proc, fe_proc=fe_proc)
    code = sup.run()
    assert code != 0
    assert len(spawned) == 1, (
        f"frontend must not be spawned after api dies; "
        f"spawned={[s.name for s in spawned]}"
    )
    assert spawned[0].name == "api"


# ── Supervisor: signal handling & cleanup ───────────────────────────────


def test_supervisor_stops_both_children_on_sigint_and_returns_130():
    """SIGINT terminates both children and returns 128 + SIGINT (= 130)."""
    api_proc, api_state = _make_proc("api", pid=4001)
    fe_proc, fe_state = _make_proc("frontend", pid=4002)
    spawned, sup = _make_supervisor(api_proc=api_proc, fe_proc=fe_proc)
    counter = {"ticks": 0}

    def sleeping(_s):
        counter["ticks"] += 1
        if counter["ticks"] >= 1:
            sup._on_signal(signal.SIGINT, None)

    sup.sleep_fn = sleeping
    code = sup.run()
    assert api_state["stop_called"] == 1
    assert fe_state["stop_called"] == 1
    assert code == 128 + signal.SIGINT, (
        f"expected 130 (128+SIGINT), got {code}"
    )


def test_supervisor_stops_both_children_on_sigterm_and_returns_143():
    """SIGTERM terminates both children and returns 128 + SIGTERM (= 143)."""
    api_proc, api_state = _make_proc("api", pid=5001)
    fe_proc, fe_state = _make_proc("frontend", pid=5002)
    spawned, sup = _make_supervisor(api_proc=api_proc, fe_proc=fe_proc)
    counter = {"ticks": 0}

    def sleeping(_s):
        counter["ticks"] += 1
        if counter["ticks"] >= 1:
            sup._on_signal(signal.SIGTERM, None)

    sup.sleep_fn = sleeping
    code = sup.run()
    assert api_state["stop_called"] == 1
    assert fe_state["stop_called"] == 1
    assert code == 128 + signal.SIGTERM, (
        f"expected 143 (128+SIGTERM), got {code}"
    )


# ── Supervisor: child failure propagation ────────────────────────────────


def test_supervisor_propagates_frontend_failure_to_nonzero():
    """If frontend exits unexpectedly, supervisor stops the surviving api
    and returns non-zero."""
    api_proc, api_state = _make_proc("api", pid=6001)
    fe_proc, fe_state = _make_proc("frontend", pid=6002)
    spawned, sup = _make_supervisor(api_proc=api_proc, fe_proc=fe_proc)

    def sleeping(_s):
        if fe_state["returncode"] is None:
            fe_state["returncode"] = 42  # frontend dies

    sup.sleep_fn = sleeping
    code = sup.run()
    assert fe_state["returncode"] == 42
    assert api_state["stop_called"] == 1, (
        f"api must be stopped when frontend dies; got {api_state}"
    )
    assert code != 0


def test_supervisor_propagates_api_failure_to_nonzero():
    """If api exits unexpectedly, supervisor stops the surviving frontend
    and returns non-zero."""
    api_proc, api_state = _make_proc("api", pid=7001)
    fe_proc, fe_state = _make_proc("frontend", pid=7002)
    spawned, sup = _make_supervisor(api_proc=api_proc, fe_proc=fe_proc)

    def sleeping(_s):
        if api_state["returncode"] is None:
            api_state["returncode"] = 17  # api dies

    sup.sleep_fn = sleeping
    code = sup.run()
    assert api_state["returncode"] == 17
    assert fe_state["stop_called"] == 1, (
        f"frontend must be stopped when api dies; got {fe_state}"
    )
    assert code != 0


def test_supervisor_does_not_stop_already_exited_child_twice():
    """If api already exited before health succeeded, supervisor must
    NOT spawn the frontend and must NOT re-stop the dead api."""
    api_proc, api_state = _make_proc("api", pid=8001)
    fe_proc, _ = _make_proc("frontend", pid=8002)
    api_state["returncode"] = 1  # died immediately
    spawned, sup = _make_supervisor(api_proc=api_proc, fe_proc=fe_proc)
    code = sup.run()
    assert code != 0
    assert api_state["stop_called"] == 0, (
        f"dead api should not be re-stopped; got {api_state}"
    )
    assert len(spawned) == 1


# ── Health-check primitive (no real network) ─────────────────────────────


def test_wait_for_health_returns_immediately_when_probe_succeeds():
    """wait_for_health exits as soon as the probe returns True."""
    calls = {"n": 0}

    def probe(_url: str) -> bool:
        calls["n"] += 1
        return True

    wait_for_health("http://x/api/health",
                    timeout_s=1.0, poll_s=0.0, probe_fn=probe)
    assert calls["n"] == 1


def test_wait_for_health_raises_after_timeout_when_probe_never_succeeds():
    """wait_for_health raises HealthCheckTimeout after the deadline."""
    def probe(_url: str) -> bool:
        return False

    with pytest.raises(HealthCheckTimeout) as exc:
        wait_for_health("http://x/api/health",
                        timeout_s=0.05, poll_s=0.01, probe_fn=probe)
    assert "http://x/api/health" in str(exc.value)


# ── Regression: keyword-only health_fn signature --------------------------


def test_supervisor_with_real_default_health_does_not_raise_typeerror():
    """End-to-end regression: `Supervisor.run()` invoking the real
    `wait_for_health` callable MUST NOT raise TypeError. `wait_for_health`
    declares `timeout_s` and `poll_s` as keyword-only (after `*`); the
    buggy call site passed them positionally, which raised
    `TypeError: wait_for_health() takes 1 positional argument but 3
    were given` before the readiness loop even ran. The fakes used in
    the other tests masked this by having a positional signature.

    Forces readiness to fail fast: the API is fake (poll never
    returns 2xx), so the deadline expires and the supervisor exits 1
    after raising `HealthCheckTimeout`. The point of the assertion is
    that we reach that branch at all instead of crashing from
    TypeError.
    """
    api_proc, _ = _make_proc("api", pid=9101)
    fe_proc, _ = _make_proc("frontend", pid=9102)
    spawned, sup = _make_supervisor(
        api_proc=api_proc, fe_proc=fe_proc,
        health_fn=wait_for_health,  # real default
    )
    # Force readiness to fail fast: deadline expires on first iteration.
    sup.health_timeout_s = 0.01
    sup.health_poll_s = 0.001
    # Before the fix, this raised TypeError before the loop ran.
    code = sup.run()
    assert code != 0, (
        f"expected non-zero exit on readiness timeout; got {code}"
    )
    assert len(spawned) == 1, (
        f"frontend must not be spawned when readiness fails; "
        f"spawned={[s.name for s in spawned]}"
    )
    assert spawned[0].name == "api"


def test_supervisor_passes_health_timeout_and_poll_as_keyword_only():
    """Focused regression: `Supervisor.run()` MUST invoke `health_fn`
    with `timeout_s` and `poll_s` as keyword arguments. Captures the
    call kwargs and asserts the default-timeout-and-poll values
    arrived by name. The contract is exactly what the real
    `wait_for_health` signature accepts.
    """
    api_proc, _ = _make_proc("api", pid=9201)
    fe_proc, _ = _make_proc("frontend", pid=9202)
    recorded: dict = {}

    def recording_health(url, *, timeout_s, poll_s):
        recorded["url"] = url
        recorded["timeout_s"] = timeout_s
        recorded["poll_s"] = poll_s
        return None  # success → spawn frontend

    spawned, sup = _make_supervisor(
        api_proc=api_proc, fe_proc=fe_proc,
        health_fn=recording_health,
    )
    # Deliver SIGINT after one tick so the loop exits cleanly.
    counter = {"ticks": 0}

    def sleeping(_s):
        counter["ticks"] += 1
        if counter["ticks"] >= 1:
            sup._on_signal(signal.SIGINT, None)

    sup.sleep_fn = sleeping
    code = sup.run()
    assert code == 128 + signal.SIGINT
    assert recorded.get("url") == DEFAULT_API_HEALTH_URL, recorded
    assert recorded.get("timeout_s") == 1.0, (
        f"expected timeout_s passed by keyword; recorded={recorded}"
    )
    assert recorded.get("poll_s") == 0.01, (
        f"expected poll_s passed by keyword; recorded={recorded}"
    )
