# Repair Tailwind and Next.js pipeline

## Objective
Restore a working Next.js 16 development pipeline using the repository's intended Tailwind CSS v4 configuration.

## Problem and rationale
`next dev` starts but `/` returns HTTP 500 because the installed top-level Tailwind package is stale v3 while `src/app/globals.css` uses v4 syntax. The project also lacks the Tailwind v4 PostCSS plugin and configuration required by the bundled Next 16 CSS documentation.

## Scope
- Align package metadata and lockfile on Tailwind v4.
- Add the official Tailwind v4 PostCSS configuration for Next.
- Remove obsolete v3-only Tailwind dependencies/configuration when they are not used by the migrated pipeline.
- Reinstall dependencies and verify `next dev` serves `/` successfully.
- Retain Next's current generated `next-env.d.ts` import paths after a successful static build.

## Constraints
- Preserve the existing Tailwind v4 token stylesheet and App Router imports.
- Do not change application behavior or mount additional UI shells.
- Do not alter backend/FastAPI code.
- Publish the verified repair through a pull request; do not merge it automatically.
- TDD mode: disabled/unknown; use focused runtime and build checks.

## Delivery strategy
ask-on-risk; forecast under 250 authored lines, excluding the lockfile.

## Tasks
- [x] ODD-TW-001 Align the Tailwind v4 dependencies and Next PostCSS configuration.
  - Outcome: removed the conflicting Tailwind v3 dependency and v3-only configuration; added `@tailwindcss/postcss` and `@tailwindcss/cli`; created the official `postcss.config.mjs`; regenerated the pnpm lockfile and removed the stale npm lockfile.
  - Evidence: `pnpm install` and `pnpm install --frozen-lockfile` passed. `next dev` served `/` with HTTP 200 and processed the v4 tokens.
- [x] ODD-TW-002 Verify the Next development server and static build.
  - Outcome: independent verification confirmed `next dev` serves `/` with HTTP 200, the processed Tailwind v4 CSS is served, and `next build` completes with static routes. App Router source files are unchanged.
  - Evidence: independent `pnpm install --frozen-lockfile`, `next dev` plus HTTP checks, `pnpm exec next build`, and `git diff --check` all passed.
  - Note: Next 16 rewrote `next-env.d.ts` from `.next/dev/types` paths to `.next/types` paths during the verified static build. This is a standard generated declaration update and is retained in the candidate.
- [x] ODD-TW-003 Commit and publish the verified repair.
  - Outcome: created `fix(tailwind): repair next pipeline` and opened PR #299 on `fix/tailwind-next-pipeline` to `develop`.
  - Evidence: local work-unit commit created after writer and independent verification; PR #299 links approved issue #74 and carries exactly `type:bug`. Smoke tests are pending; no automatic merge.

## Progress
The pipeline repair, verification, commit, and PR publication are complete. The app now serves the current migrated placeholder page (`<h1>taxa</h1>`); it does not mount the future application shell.

## Next step
Wait for PR #299 Smoke tests and human review; do not merge it automatically.
