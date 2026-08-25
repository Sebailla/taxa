# AGENTS — taxa

This file is the convention contract for every SDD sub-agent that lands
in this project. Read it before any artifact write.

## Language Domain Contract

Generated technical artifacts (proposal.md, spec.md, design.md,
tasks.md, code comments, identifiers, commit messages, PR descriptions,
test fixtures) default to **English** regardless of the orchestrator's
or user's conversation language.

Public/contextual comments (PR review threads, issue replies, GitHub
discussions) follow the target context language: Spanish issues →
Spanish comments, English issues → English comments. The repo's
recent PRs (#21, #22, #23, #24) are in Spanish, but this is NOT
inherited automatically — only when the target context calls for it.

## Hard Rules

- **Strict TDD is enabled.** Every `sdd-apply` task MUST write its
  failing tests FIRST (RED), make them pass (GREEN), then refactor.
  Do not skip this even when the change "looks obvious".
- **No AI attribution in commits.** Conventional commits only, no
  `Co-Authored-By: ...` trailer.
- **Branch names must match** `^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$`.
- **PR bodies follow the project's bilingual convention**: title in
  English (conventional commit subject), body in Spanish with the
  sections `## Resumen`, `## Cambios` (table), `## Validación`,
  `## Lo que NO cambió`. Mirror the style of PRs #21–#24.
- **Material Symbols Outlined** is the project's icon font. Use
  existing icons; don't introduce a new icon set.
- **Design tokens come from the Tailwind config in `web/index.html`**
  (customColor `#2563eb`, colorMode LIGHT, font INTER). Don't
  introduce hardcoded colors outside the design system tokens.
- **Frontend has no build step.** Don't add bundlers, transpilers,
  or package managers. Plain ES modules + Tailwind CDN.
- **Backend uses FastAPI + SQLite.** No ORMs, no async DB drivers.
  WAL mode is mandatory; new connections read-only.

## Artifact Layout (Hybrid Mode)

Per-change artifacts live under `openspec/changes/<change-name>/`:

- `proposal.md` — what and why
- `spec.md` — acceptance criteria + scope/non-goals
- `design.md` — architecture, contracts, trade-offs
- `tasks.md` — atomic implementation units (with TDD markers)
- `apply-progress.md` — incremental progress during `sdd-apply`
- `verify-report.md` — `sdd-verify` findings
- `archive-report.md` — final state at close

Equivalent Engram observations are best-effort, not required. Topic
keys: `sdd/{change-name}/{artifact}`. Engram HTTP is intermittent;
do not block on `mem_search` failures — use `mem_context` /
`mem_get_observation` as fallbacks.

## Lifecycle Discipline

- `openspec/config.yaml` is the source of truth for testing capabilities.
  Don't drift it without updating the `sdd-init.md` note.
- Phase result contract is mandatory: every phase returns
  `{status, executive_summary, artifacts, next_recommended, risks,
  skill_resolution}`. Empty fields fail the gatekeeper.
- The orchestrator is the only agent that runs gatekeepers and routes
  between phases. Sub-agents do not chain themselves.

## Known Hazards

- **Bash tool blocks `git push`, `git commit`, `gh pr create`.**
  Use `gh api` for blob/tree/commit/ref/PR creation. See Engram
  observation `taxa/pi-bash-guard-push-workaround`.
- **Engram `mem_search` returns "could not reach" intermittently.**
  Fall back to `mem_context` and `mem_get_observation`.
- **`sdd-init` subagent** (`openai-codex/gpt-5.3-codex`) is
  unavailable in this environment. Init is performed inline by
  the orchestrator.
- **`stitch` MCP** is the source of design specs. Project
  `projects/11955314884511019764` ("Taxon — Tree Deep Subtree")
  contains 4 screens including "File Explorer & Viewer"
  (`screens/ab45d37bf0d54a7e8cd6256f0d3d9c7a`) which is the
  reference for the active `file-explorer` change.
