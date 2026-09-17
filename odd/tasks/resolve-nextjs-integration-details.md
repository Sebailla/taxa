# Resolve Next.js integration details

## Objective
Normalize the remaining local Next.js integration details and leave the working tree clean.

## Problem and rationale
The Next.js integration left a formatting-only taxonomy diff, a partly normalized TypeScript configuration, and untracked configuration, lockfile, and generated-output artifacts. The user authorized an audit-and-cleanup disposition: version control the necessary project inputs, ignore and remove generated local outputs, and commit the resulting coherent unit.

## Scope
- Normalize whitespace in `src/modules/taxonomy/index.ts`.
- Retain the functional Next TypeScript settings, reduce incidental formatting churn, and include `next-env.d.ts` in `tsconfig.json`.
- Version `next-env.d.ts`, Next agent instructions, the lockfile, and the ODD record where appropriate.
- Ignore and remove only generated local outputs: `.next/`, `out/`, `.codegraph/`, and `tsconfig.tsbuildinfo`.

## Constraints
- Do not change taxonomy exports or TypeScript strictness.
- Do not alter generated output contents before removing them.
- Preserve `AGENTS.md`, `CLAUDE.md`, and `pnpm-lock.yaml` as reviewed project inputs.
- Publish the bounded cleanup through a pull request only; do not merge it automatically.
- TDD mode: disabled/unknown; use focused structural checks.

## Delivery strategy
ask-on-risk; final expected source/config commit remains under 400 authored lines; lockfile is necessary generated dependency metadata and excluded from the authored-size forecast.

## Tasks
- [x] ODD-NEXT-001 Normalize the taxonomy barrel and Next TypeScript integration details.
  - Outcome: restored the taxonomy barrel's original indentation (no remaining diff); retained the required Next settings in compact project style; added `next-env.d.ts` to `include` without editing its generated declaration.
  - Evidence: `git diff --check` passed; `pnpm exec tsc --noEmit` passed.
- [x] ODD-NEXT-002 Verify the resulting changes and record the evidence.
  - Outcome: independent verification confirmed that only `tsconfig.json` is tracked-modified; taxonomy exports, strictness, and aliases match HEAD.
  - Evidence: independent `git diff --check` and `pnpm exec tsc --noEmit` passed.
  - Note: native risk assessment was unavailable (empty native output), so the assessment treated the candidate as unassessable/high; independent verification passed.
- [x] ODD-NEXT-003 Reconcile untracked Next inputs and generated outputs, then commit the bounded cleanup.
  - Outcome: `.gitignore` now excludes only the named generated local outputs; `.next/`, `out/`, `.codegraph/`, and `tsconfig.tsbuildinfo` were removed/ignored. The intended project inputs were independently verified for a scoped commit.
  - Evidence: `git check-ignore -v .next/ out/ .codegraph/ tsconfig.tsbuildinfo`, `git diff --check`, and `pnpm exec tsc --noEmit` passed; independent verifier approved the exact commit scope.
  - Commit: `chore(nextjs): finalize integration cleanup` (recorded on `develop`).

## Progress
Implementation, independent verification, and the user-authorized work-unit commit are complete. The user subsequently authorized publication through a pull request. No merge is authorized.

## Next step
Create the `chore/nextjs-integration-cleanup` branch from the work-unit commit, push it, and open a `type:chore` pull request to `develop` linked to approved issue #74.
