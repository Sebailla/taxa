# sdd-init/taxa

Initialized: 2026-08-22 (by orchestrator; sdd-init subagent unavailable)

## Stack

- Python 3.x with `.venv`
- FastAPI backend at `api/server.py`
- SQLite (WAL mode) at `data/db/taxa.db`
- Vanilla JS + Tailwind CDN frontend at `web/index.html`, `web/app.js`
- pytest smoke tests at `tests/test_smoke.py` (offline, runs in CI in ~5s)
- Makefile-driven workflow (`make venv`, `make etl`, `make coldp`, `make worms`, `make api`, `make test`)

## ETL layout

- `etl/parse_textree.py` — CoL TextTree parser (in-memory, bulk insert, VACUUM)
- `etl/load_coldp.py` — CoL ColDP enrichments (coldp_id, vernaculars, extinct)
- `etl/load_worms.py` — WoRMS as enrichment over CoL (match by name+rank)
- `etl/load_distribution.py` — Distribution TSV loader
- Schemas: `etl/schema.sql` (v1), `etl/schema_v2.sql` (+coldp_id, vernacular), `etl/schema_v3.sql` (+distribution)
- Conventions: idempotent, WAL-mode, read-only API connections

## Frontend conventions

- Material Symbols Outlined for icons
- Segmented "tree-source-toggle" in header (CoL / WoRMS buttons, data-tree-source attribute)
- Tailwind via CDN; design tokens as CSS variables in `<style>` block
- Three named anchors in `<main>` nav: Browser (current), Classification, Settings
- Detail panel already exists with vernaculars/synonyms/distribution sections

## Project conventions

- Conventional commits, no AI attribution (Co-Authored-By forbidden)
- Strict TDD mode: enabled (preserve `strict_tdd: true` when launching sdd-apply / sdd-verify)
- Idempotent loaders
- WAL-mode SQLite, read-only API connections
- Test runner: `make test` → `pytest tests/ -v`

## Session preflight (cached)

- **Artifact store**: hybrid → effective `openspec-only` (Engram HTTP server at `127.0.0.1:7437` unreachable; `mem_*` tools fail with connection error)
- **Execution mode**: auto (gatekeeper validates between phases; only stop on real failure)
- **Delivery strategy**: ask-on-risk (prompt before chained PRs if size > 400 lines or high review risk)

## SDD phase routing

With artifact store = openspec-only:

- All SDD phases write artifacts under `openspec/changes/<change-name>/`
- Do NOT use `mem_search` / `mem_save` / `mem_get_observation` — Engram is down
- Phase result contract is unchanged: `status`, `executive_summary`, `artifacts`, `next_recommended`, `risks`, `skill_resolution`

## Notes

- `sdd-init` subagent model (`openai-codex/gpt-5.3-codex`) is unavailable in this environment; init was performed inline by the orchestrator.
- All other `sdd-*` subagents use `MiniMax-M3` and are reachable.
