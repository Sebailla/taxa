"""G2 build verifier — design.md §3.3.2.1. Exit: 0 ok, 1 usage, 2 Node<min, 3 build!=0, 4 manifest, 5 missing class."""
import argparse, datetime as dt, hashlib, json, os, re
import subprocess, sys, tempfile
from pathlib import Path

_VER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")


def _semver(v):
    m = _VER.match(v.strip())
    if not m:
        raise ValueError(f"unparseable version {v!r}")
    return int(m[1]), int(m[2]), int(m[3])


def _atomic_write(p, body):
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{p.name}.", dir=str(p.parent))
    try:
        os.write(fd, body); os.close(fd); os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _asset(p, klass, root, **extra):
    body = p.read_bytes()
    entry = {"class": klass, "path": str(p.relative_to(root)),
             "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
    entry.update(extra)
    return entry


def _stage(src, dst, staged):
    """Atomically copy src→dst if src exists; clear staged on failure."""
    if not src.is_file():
        return False
    try:
        _atomic_write(dst, src.read_bytes())
    except OSError as exc:
        sys.stderr.write(f"[verify_build] stage {src}->{dst}: {exc}\n")
        _unstage(staged); raise
    staged.append(dst)
    return True


def _unstage(staged):
    for p in staged:
        try:
            p.unlink()
        except OSError:
            pass


def _check_node(node, minv):
    try:
        r = subprocess.run([node, "--version"], capture_output=True,
                            text=True, check=False, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        sys.stderr.write(f"[verify_build] node --version failed: {exc}\n")
        return 2, ""
    raw = (r.stdout or r.stderr or "").strip()
    if r.returncode != 0:
        sys.stderr.write(f"[verify_build] node --version non-zero: {raw}\n")
        return 2, raw
    try:
        if _semver(raw) < _semver(minv.lstrip("vV")):
            sys.stderr.write(f"[verify_build] Node {raw} below required {minv}\n")
            return 2, raw
    except ValueError as exc:
        sys.stderr.write(f"[verify_build] {exc}\n"); return 2, raw
    return 0, raw


def _run_build(nxt, cwd, log):
    started = dt.datetime.now(dt.timezone.utc)
    with log.open("ab") as f:
        proc = subprocess.run([nxt, "build"], cwd=cwd,
                              stdout=f, stderr=subprocess.STDOUT, check=False)
    finished = dt.datetime.now(dt.timezone.utc)
    return proc.returncode, f"{nxt} build (cwd={cwd})", started, finished


def _classify(out, inv):
    """Append asset entries to inv; return list of missing required classes."""
    missing = []
    idx = out / "index.html"
    if idx.is_file() and idx.stat().st_size > 0:
        inv["assets"].append(_asset(idx, "application_route_html", out))
    else:
        missing.append("application_route_html")
    chunks = out / "_next" / "static" / "chunks"
    for label, klass, pattern in (("js_class", "js_class", "*.js"),
                                  ("css_class", "css_class", "*.css")):
        files = sorted(chunks.rglob(pattern)) if chunks.is_dir() else []
        match = next((f for f in files
                      if f.is_file() and f.stat().st_size > 0), None)
        (inv["assets"].append(_asset(match, klass, out)) if match
         else missing.append(label))
    media = out / "_next" / "static" / "media"
    if media.is_dir():
        for f in sorted(media.rglob("*")):
            if f.is_file() and f.stat().st_size > 0:
                inv["assets"].append(_asset(f, "static_fonts", out)); break
    for name in ("404.html", "500.html"):
        p = out / name
        if p.is_file() and p.stat().st_size > 0:
            inv["assets"].append(_asset(p, "error_pages", out))
    return missing


def _emit(out, cand, raw_node, cmd, started, finished):
    inv = {"node_version": raw_node, "candidate_root": str(cand),
           "build_command": cmd, "build_started_at": started.isoformat(),
           "build_finished_at": finished.isoformat(), "exit_code": 0,
           "assets": [], "missing_classes": []}
    out.mkdir(parents=True, exist_ok=True)
    staged = []
    req = (cand / ".next" / "build-manifest.json",
           out / ".next" / "build-manifest.json")
    if not _stage(*req, staged):
        sys.stderr.write(f"[verify_build] required manifest missing: {req[0]}\n")
        _unstage(staged); return 4
    inv["assets"].append(_asset(req[1], "staged_manifest", out, staging="staged"))
    opt = (cand / ".next" / "app-build-manifest.json",
           out / ".next" / "app-build-manifest.json")
    if _stage(*opt, staged):
        inv["assets"].append(_asset(opt[1], "staged_manifest", out, staging="staged"))
    else:
        inv["assets"].append({"class": "staged_manifest",
                              "path": str(opt[1].relative_to(out)),
                              "staging": "not_emitted"})
    missing = _classify(out, inv)
    if missing:
        _unstage(staged); sys.stderr.write(f"[verify_build] missing classes: {missing}\n"); return 5
    inv["missing_classes"] = missing
    try:
        _atomic_write(out / "BUILD-INVENTORY.json",
                      json.dumps(inv, indent=2, sort_keys=True).encode())
    except OSError as exc:
        _unstage(staged); sys.stderr.write(f"[verify_build] inventory write failed: {exc}\n"); return 4
    return 0


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    p = argparse.ArgumentParser(prog="verify_build.py", add_help=False)
    p.add_argument("--out", required=True)
    p.add_argument("--node-min", required=True)
    p.add_argument("--candidate", default=None)
    p.add_argument("--node", default=None)
    p.add_argument("--next", default=None)
    try:
        ns = p.parse_args(argv)
    except SystemExit:
        sys.stderr.write(
            "usage: verify_build.py --out <path> --node-min <ver> "
            "[--candidate <path>] [--node <path>] [--next <path>]\n")
        return 1
    out = Path(ns.out).resolve()
    # Default --candidate to the parent of --out so the build output
    # lands under <candidate>/out/ per design.md §3.3.2.1.
    cand = Path(ns.candidate or out.parent).resolve()
    node = ns.node or "node"
    nxt = ns.next or str(cand / "node_modules" / ".bin" / "next")
    if not Path(nxt).is_file():
        sys.stderr.write(f"[verify_build] next not found: {nxt}\n"); return 1
    rc, raw_node = _check_node(node, ns.node_min)
    if rc != 0: return rc
    log = cand / "build.log"
    rc, cmd, started, finished = _run_build(nxt, cand, log)
    if rc != 0:
        sys.stderr.write(f"[verify_build] build exited {rc}; see {log}\n")
        return 3
    return _emit(out, cand, raw_node, cmd, started, finished)


if __name__ == "__main__":
    raise SystemExit(main())