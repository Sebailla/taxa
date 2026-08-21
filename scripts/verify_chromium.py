"""
Verify the integrity of the playwright chromium binary.

Background
----------
playwright==X.Y.Z is pip-pinned in requirements-dev.txt, but the chromium
binary that powers headless screenshots is downloaded separately via:

    .venv/bin/playwright install chromium

The binary is fetched from playwright.azureedge.net (Microsoft CDN) at
install time and is NOT pinned by pip. A future supply-chain compromise of
that CDN could ship a malicious chromium without any change to our
requirements file.

This script computes the SHA256 of the installed chromium binary so the
result can be:
  - recorded as the pinned value in this file's CHROMIUM_SHA256 constant
  - re-computed on each install and compared against the pinned value
  - audited by CI before running screenshot.py

Usage
-----
    .venv/bin/python scripts/verify_chromium.py           # print current SHA
    .venv/bin/python scripts/verify_chromium.py --check  # exit 1 if mismatch

The pinned value below was captured on the date noted. Bump it after a
deliberate playwright upgrade:

    .venv/bin/pip install --upgrade playwright
    .venv/bin/playwright install chromium
    .venv/bin/python scripts/verify_chromium.py     # copy the printed SHA
                                                    # into CHROMIUM_SHA256
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

# Pinned SHA256 of the chromium binary that ships with the playwright
# version pinned in requirements-dev.txt. Update together with that pin.
# Captured: see git log for the date of the most recent bump.
# Captured 2026-08-21 against playwright==1.62.0 (chromium-1234 launcher).
CHROMIUM_SHA256 = "a596b1cfc6353e987fcec8d71a23a28cd6a9e7a6b4e20b908e4c4fcffe51158e"


def find_chromium_binary() -> Path:
    """Locate the chromium binary that the installed playwright version uses.

    Uses playwright.chromium.executable_path as the source of truth — that
    property reflects the version pin inside playwright (each playwright
    release ships a specific chromium revision). Globbing the cache
    directory and picking a path is fragile: a developer machine can have
    multiple chromium revisions installed (one per playwright version
    ever installed), and the wrong one is easy to pick by accident.
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError as e:
        print(
            f"[error] playwright is not installed: {e}\n"
            "  pip install playwright && playwright install chromium"
        )
        sys.exit(1)
    with sync_playwright() as pw:
        return Path(pw.chromium.executable_path)


def sha256_of(path: Path) -> str:
    """Compute SHA256 hex digest of a file, streamed."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError as e:
        print(f"[error] could not read {path}: {e}")
        sys.exit(1)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if the installed binary's SHA256 doesn't match CHROMIUM_SHA256.",
    )
    args = ap.parse_args()

    binary = find_chromium_binary()
    digest = sha256_of(binary)

    print(f"binary:  {binary}")
    size_bytes = binary.stat().st_size
    if size_bytes < 1 << 20:
        size_str = f"{size_bytes // 1024} KB"
    else:
        size_str = f"{size_bytes / (1 << 20):.1f} MB"
    print(f"size:    {size_str}")
    print(f"sha256:  {digest}")

    if not CHROMIUM_SHA256:
        print(
            "\n[info] CHROMIUM_SHA256 is empty (first run). Copy the printed "
            "sha256 into the CHROMIUM_SHA256 constant in this script to pin it."
        )
        return 0

    if digest != CHROMIUM_SHA256:
        print(
            f"\n[FAIL] expected {CHROMIUM_SHA256}\n"
            f"        got      {digest}\n"
            "Run with --check or manually compare. If this is a deliberate "
            "playwright upgrade, update CHROMIUM_SHA256 in this script."
        )
        return 2 if args.check else 1

    print("\n[OK] SHA256 matches pinned value.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
