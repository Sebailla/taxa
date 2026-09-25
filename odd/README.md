# ODD — Organic Driven Development

This directory holds the ODD working drafts (the "what the work was supposed to be" notes) plus the archive of completed drafts.

## Structure

```
odd/
├── README.md           ← this file (the directory's canonical entry point)
├── tasks/              ← in-flight ODD working drafts only
│   ├── complete-frontend-migration.md
│   └── w6-3-record-and-w6-4-chain.md
└── archive/
    └── 2026-09-Q3/     ← every ODD draft whose work has merged to develop
                          (38 drafts + a README that documents each wave)
```

## Rules

### `odd/tasks/` — only in-flight work

Only ODD working drafts whose work has NOT yet merged to `develop` live here. Every draft must describe a single feature branch + PR cycle (the "local working draft" model). When the work merges, the draft moves to `odd/archive/<quarter>/`.

### `odd/archive/<quarter>/` — every merged draft

Every ODD draft whose work has merged (or which was explicitly abandoned) lives here. The `<quarter>/` directory carries a `README.md` that documents each wave with the PR + commit provenance for every archived draft.

### The 2 test-coupled exceptions in `odd/tasks/`

Two files stay in `odd/tasks/` even though their work has long merged:

- **`complete-frontend-migration.md`** — referenced by
  `tests/test_search_engine_consumer_manifest.py::TestW18CutoverCarryOver`
  (lines 1027-1038) to verify the W18 migration tracker carries the
  cutover task.
- **`w6-3-record-and-w6-4-chain.md`** — referenced by the same test
  (lines 321, 324, 328) to verify the W6.3 chain records the
  W65-MAP-007 carry-over + the W65-MANIFEST-008 audit tasks.

The audit references both files by their `odd/tasks/` path, and the
tests are smoke-blockers. Moving the files would require co-updating
the test, which is out of scope for the housekeeping passes. A future
cleanup can relocate these (and update the test in the same PR).

## Quarter naming

`<quarter>/` follows the calendar quarter convention (`YYYY-MM-Qn`).
The 2026 Q3 archive holds every ODD draft closed in that quarter
(38 drafts across waves 1 + 2 + 3 + 4).

## How to use

### To start a new ODD plan for an upcoming feature

1. Create `odd/tasks/<feature-name>.md` with the ODD plan structure
   (objective, why, scope, non-goals, strategy, allowed edit
   surfaces, acceptance criteria).
2. Reference the plan from the PR body so a reviewer sees the
   rationale.
3. The plan stays in `odd/tasks/` while the work is in-flight.

### When the work merges

1. Move the file to `odd/archive/<quarter>/` via `git mv`.
2. Add a row to `<quarter>/README.md` with the PR number + commit.
3. The plan is now a historical artifact; the PR + commit live in
   git history for the canonical record.

### When the work is explicitly abandoned

1. Move the file to `odd/archive/<quarter>/` via `git mv`.
2. Add a row to `<quarter>/README.md` flagged as "abandoned" with
   the rationale (e.g., "superseded by direct-to-develop ODD
   deliveries").

## Why ODD lives in git

The ODD drafts document the **why** behind every feature branch:
the constraint, the rejection of alternatives, the risk trade-off.
They are committed to git so the rationale survives across branches
+ rebases (a feature branch's draft is often deleted when the
branch is squashed + merged; archiving the draft before squash
preserves the rationale in the merge commit's metadata + the
archive directory).
