#!/usr/bin/env python3
"""End-to-end smoke test: start the API, hit freshwater endpoints, stop."""
import json
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

PORT = 8766  # non-default port to avoid conflicts with the dev API

DB_PATH = "data/db/taxa.db"

def start_api():
    return subprocess.Popen(
        [".venv/bin/python3", "-m", "uvicorn", "api.server:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def wait_ready(timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False

def get(path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=5) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        print(f"FAIL: GET {path}: {exc}", file=sys.stderr)
        raise

def main():
    proc = start_api()
    try:
        if not wait_ready():
            print("API failed to start within 10s")
            return 1

        # 1. /api/health
        h = get("/api/health")
        print(f"/api/health: taxa={h['taxa']:,} freshwater_loaded={'?'}")

        # 2. /api/domains should include the freshwater root.
        domains = get("/api/domains")
        fw_roots = [d for d in domains if d.get("freshwater_id") == 1]
        print(f"/api/domains: {len(domains)} roots total, "
              f"{len(fw_roots)} freshwater_root(s)")
        for d in fw_roots:
            print(f"  → id={d['id']} name={d['scientific_name']!r} "
                  f"rank={d['rank']!r} fw_id={d['freshwater_id']} "
                  f"fw_parent_id={d['freshwater_parent_id']}")
        if not fw_roots:
            print("FAIL: no freshwater root in /api/domains")
            return 1

        # 3. /api/taxon/{root}/children?source=freshwater — first level (families).
        root_id = fw_roots[0]["id"]
        families = get(f"/api/taxon/{root_id}/children?source=freshwater&limit=5")
        print(f"/api/taxon/{root_id}/children?source=freshwater (first 5):")
        for f in families:
            print(f"  → {f['scientific_name']!r} (rank={f['rank']}, "
                  f"fw_id={f['freshwater_id']}, fw_parent_id={f['freshwater_parent_id']})")
        if not families:
            print("FAIL: no families returned under freshwater root")
            return 1

        # 4. Drill one level deeper (pick the first family).
        first_fam_id = families[0]["id"]
        genera = get(f"/api/taxon/{first_fam_id}/children?source=freshwater&limit=5")
        print(f"/api/taxon/{first_fam_id}/children?source=freshwater (first 5):")
        for g in genera:
            print(f"  → {g['scientific_name']!r} (rank={g['rank']})")

        # 5. Pick a species and test /searches.
        if genera:
            species = get(f"/api/taxon/{genera[0]['id']}/children?source=freshwater&limit=1")
            if species:
                sp_id = species[0]["id"]
                sp_name = species[0]["scientific_name"]
                searches = get(f"/api/taxon/{sp_id}/searches")
                print(f"/api/taxon/{sp_id}/searches ({sp_name!r}): "
                      f"{len(searches)} engine links")
                for s in searches[:3]:
                    print(f"  → {s['engine']}: {s['url']}")
                if len(searches) != 14:
                    print(f"FAIL: expected 14 engines, got {len(searches)}")
                    return 1
            else:
                print("  (no species under first genus — skipping /searches test)")

        print("\n✅ Smoke test PASSED")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())