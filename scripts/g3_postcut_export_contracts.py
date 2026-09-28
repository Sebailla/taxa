"""G3 post-cut root-shell contract for the future isolated Next.js export.

#16 requires the supplied HTML to carry the AppShell ``data-app-shell``
marker and a ``<main`` landmark. The test module keeps its synthetic
``tmp_path`` checks separate from the future ``Path.cwd()/out`` consumer.
This helper does not inspect the main export or claim a G3 pass.
"""

from __future__ import annotations

import re
from pathlib import Path

class PostcutContractError(Exception):
    """Raised by the three helpers on any verification failure.

    The future G3 consumer (``tests/test_g3_postcut_export_contracts.py
    ::test_consumer_*``) propagates this exception to pytest so a
    structural / export regression is surfaced as a real test
    failure instead of a silent pass.
    """


# ===========================================================================
# #16 — root-shell structure (data-app-shell marker + <main landmark)
#
# Anchored to ``src/modules/app-shell/presentation/AppShell.tsx``:
#
#     <div
#       className="app-shell flex min-h-screen flex-col ..."
#       data-app-shell=""
#     >
#       ...
#       <main className="app-shell-main flex-1">
#         ...
#       </main>
#       ...
#     </div>
#
# After React rendering, ``className`` becomes ``class`` and the
# boolean-true (``=""``) data attribute becomes ``data-app-shell=""``.
# Both the marker substring and the landmark regex are intentionally
# permissive: the marker is a substring search, the landmark uses a
# word boundary so ``<mainland>`` / ``<maintenance>`` cannot satisfy
# the contract.
# ===========================================================================
ROOT_SHELL_MARKER = "data-app-shell"
# ``<main`` followed by a word boundary (``\b``), a non-word
# character such as whitespace, ``>``, or a quote. This rejects
# ``<mainland>`` / ``<maintenance>`` while still matching the
# React-rendered ``<main class="...">`` and a bare ``<main>``.
ROOT_SHELL_LANDMARK_RE = re.compile(r"<main\b")


def verify_root_shell(html_path: Path) -> None:
    """Verify that ``html_path`` carries the AppShell ``data-app-shell``
    marker AND a ``<main`` landmark, based on
    ``src/modules/app-shell/presentation/AppShell.tsx``.

    Raises :class:`PostcutContractError` if either is missing or
    the file is empty / unreadable.
    """
    p = Path(html_path)
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PostcutContractError(
            f"cannot read root-shell HTML at {p}: {exc}"
        ) from exc
    if not text:
        raise PostcutContractError(f"root-shell HTML is empty: {p}")
    if ROOT_SHELL_MARKER not in text:
        raise PostcutContractError(
            f"root-shell HTML missing {ROOT_SHELL_MARKER!r} marker: {p}"
        )
    if not ROOT_SHELL_LANDMARK_RE.search(text):
        raise PostcutContractError(f"root-shell HTML missing `<main` landmark: {p}")
