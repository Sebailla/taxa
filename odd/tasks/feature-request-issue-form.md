# Feature request issue form

## Objective
Add a repository-native YAML issue form for proposing user-facing features, then use its reviewed structure to prepare the Explorer orientation/state-persistence issue.

## Scope and constraints
- Add one feature-request form under `.github/ISSUE_TEMPLATE/`.
- Preserve existing Bug report, Documentation, and Migration forms.
- Use the existing `type:feature` label; do not apply protected `status:approved`.
- Follow the new form's required fields exactly when preparing the Explorer issue.
- Do not publish the issue until the user reviews and approves the exact title and materialized body.
- Keep issue-form content in private temporary files during the eventual publication workflow.

## Tasks

### Add feature request issue form
- **Status:** done.
- **Authorized by:** user explicitly approved adding a YAML feature-request form.
- **File:** `.github/ISSUE_TEMPLATE/feature.yml`.
- **Acceptance:** GitHub-compatible YAML, clear required prompts for problem, proposed behavior, scope/non-goals, acceptance criteria, and validation plan; exactly the existing `type:feature` label.
- **Verification:** YAML parsed with PyYAML 6.0.3; top-level GitHub form structure, unique IDs, required textarea controls, and existing non-protected `type:feature` label validated by `gentle-ai-verify`.
- **Commit:** `c2ce9a4 feat(issues): add feature request form`.

### Validate the form and draft the Explorer issue
- **Status:** in progress.
- **Acceptance:** produce a title and body that follow the form's controls; user reviews exact content before publication.

### Create the issue
- **Status:** pending; blocked on user review of exact title/body.
- **Acceptance:** one create attempt and target-host readback; never add `status:approved` on the user's behalf.

## Target
- Host: `github.com`
- Repository: `Sebailla/taxa`
- Duplicate search: current-session open/closed search found no matching Explorer orientation/persistence issue.
