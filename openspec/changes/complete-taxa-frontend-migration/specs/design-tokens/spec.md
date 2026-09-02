# Design Tokens Specification

> Domain: `design-tokens`. New domain. Authored under
> `complete-taxa-frontend-migration`. The canonical home is the change
> folder; archive copies this file verbatim into
> `openspec/specs/design-tokens/spec.md` at activation.

## Purpose

The Taxa visual identity is encoded as a Tailwind 4 `@theme` block
plus CSS variables, migrated **byte-equal** from the bespoke inline
`<style>` block of `web/index.html` and the legacy
`tailwind.config.js`. The tokens drive both Tailwind utility classes
and plain-CSS rules (e.g. bespoke selectors, `@keyframes`,
`.animate-spin`, `color-mix()` cascades). Cascade order must match
the legacy build so the visual diff against the chromium fixture
captured by the G4 Playwright harness is empty.

The contract preserved against the legacy build is **token parity**:
every `:root` token, every utility class, and every bespoke rule
resolves to a non-empty declaration.

## Requirements

### Requirement: Tailwind 4 `@theme` block in `globals.css`

The system MUST declare the full Tailwind 4 `@theme { ... }` block
inside `src/app/globals.css` (or the canonical
`src/modules/design-system/infrastructure/globals.css` per the
modular-architecture spec rule 3) under `@layer base`.

#### Scenario: Every legacy `:root` token migrated

- GIVEN the legacy `:root { … }` block in `web/index.html:24–`
  declares each token (e.g. `--primary: #1d7ea9`, `--accent:
  #176587`, `--surface: #ffffff`, `--elevated: #bbbbbb`,
  `--on-surface: #333333`, `--on-surface-variant: #555555`,
  `--outline: #bbbbbb`, `--outline-variant: #d9d9d9`,
  `--surface-container-low: #fafafa`, `--surface-container: #f5f5f5`,
  `--surface-container-high: #eeeeee`, the `--realm-*` family,
  the data-theme dark palette, etc.)
- WHEN the apply worker migrates the block into `globals.css`
- THEN every token is declared with the **same** name and the
  **same** value
- AND no token is renamed, deleted, or merged
- AND both the light (`:root`) and dark (`[data-theme="dark"]`)
  palettes are present

#### Scenario: Utility classes resolve

- GIVEN the legacy build uses utility classes
  (e.g. `bg-primary`, `text-on-surface`, `border-outline-variant`,
  `bg-surface-container-lowest`, `shadow-sm`, `rounded-r-md`,
  `bg-primary-fixed`, `text-on-primary-fixed`)
- WHEN the apply worker migrates to Tailwind 4 `@theme`
- THEN every legacy utility class resolves to a non-empty CSS
  declaration
- AND the `@theme` block aliases the existing names so
  `--color-primary` resolves to the legacy `--primary` value
- AND the same alias pattern applies for every legacy token the
  utility classes consume

#### Scenario: Bespoke rules in `@layer base`

- GIVEN the legacy build carries bespoke CSS rules in the inline
  `<style>` block of `web/index.html` — including `@keyframes`,
  `.animate-spin`, `color-mix()` selectors, font-family
  declarations, the `body { overscroll-behavior: none; … }` rule,
  and the `main > :first-child { margin-top: 0 !important; }`
  reset
- WHEN the apply worker migrates the rules into `globals.css`
- THEN the rules live under `@layer base`
- AND the source order matches the legacy block
- AND the cascade resolves identically (no visual diff in the
  chromium fixture)

### Requirement: Plain-CSS `var(--token)` references resolve

The system MUST keep every plain-CSS rule that reads a token via
`var(--name)` working without renaming or value drift.

#### Scenario: Bespoke selectors that consume tokens

- GIVEN the legacy build's bespoke CSS uses
  `var(--primary)`, `var(--accent)`, `var(--bg-surface)`,
  `var(--realm-coelenterata)`, etc.
- WHEN the apply worker audits `globals.css`
- THEN every `var(--name)` reference resolves to a non-empty
  declaration
- AND no token name has been silently renamed (e.g. `--primary`
  has not been renamed to `--color-primary` in plain-CSS rules)

#### Scenario: Tailwind 4 namespace aliasing

- GIVEN Tailwind 4 derives its own `--color-*` namespace from the
  `@theme` block
- WHEN the apply worker authors the `@theme` block
- THEN the existing `--primary`, `--accent`, `--bg-surface`,
  `--realm-*` names resolve via an explicit alias so both
  utility-class generation and plain-CSS `var(--name)` references
  see the same value

### Requirement: Font and icon families preserved

The system MUST keep the legacy font and icon families unchanged.

#### Scenario: `next/font` resolves the legacy fonts

- GIVEN the legacy build ships Raleway (sans body),
  JetBrains Mono (monospace), and Material Symbols Outlined
  (icon set)
- WHEN the apply worker wires `next/font`
- THEN Raleway is the body family
- AND JetBrains Mono is the monospace family
- AND Material Symbols Outlined is the icon family
- AND no new icon set is introduced
- AND the icon glyphs the legacy build uses (e.g. `search`,
  `folder_open`, `folder`, `chevron_right`, `expand_more`,
  `close`, `settings`, `help`, `science`, `science_off`,
  `download`) keep their legacy glyph names

### Requirement: Token parity test

The system MUST include a focused test that enumerates every
`:root` token and every `var(--token)` reference in the legacy
build and asserts the new build resolves them to non-empty
declarations.

#### Scenario: Token enumeration test

- GIVEN `tests/test_design_tokens.py` is the focused test
- WHEN the apply worker runs the test against the new build
- THEN every legacy `:root` token is asserted to be present in
  `globals.css` with a non-empty declaration
- AND every `var(--name)` reference in the legacy build's bespoke
  CSS is asserted to resolve
- AND the test fails loudly if any token is renamed, removed, or
  left with an empty declaration

#### Scenario: Utility-class enumeration test

- GIVEN the legacy build's utility-class footprint is enumerable
- WHEN the apply worker runs the focused test
- THEN every utility class the legacy build emits (across every
  component file the legacy build ships) resolves to a non-empty
  CSS declaration in the new build
- AND the test fails loudly if Tailwind 4 silently drops a
  utility class the legacy build emits

### Requirement: Dark mode parity

The system MUST preserve the legacy dark-mode palette and the
`data-theme` toggle.

#### Scenario: `[data-theme="dark"]` palette

- GIVEN the legacy build redefines the palette under
  `[data-theme="dark"]` inside the inline `<style>` block
- WHEN the apply worker migrates the rule into `globals.css`
- THEN `[data-theme="dark"]` redefines every token the light
  `:root` declares
- AND the settings theme toggle stamps / unstamps `data-theme` on
  `<html>` via the typed store
- AND no token is dropped, renamed, or value-drifted in the dark
  palette

#### Scenario: OS preference fallback

- GIVEN the user has not picked a theme yet
- WHEN the application boots
- THEN the OS `prefers-color-scheme` media query is consulted
- AND `data-theme="dark"` is stamped if the OS prefers dark
- AND `data-theme` is **not** stamped (light default) otherwise
- AND no flicker fires before the stamp is applied (the stamp
  lives in the `<head>` so it precedes the first paint)

## Notes

- Tailwind 4's CSS-first config replaces `tailwind.config.js`; the
  legacy file is deleted at activation.
- `tailwindcss`, `@tailwindcss/forms`, `autoprefixer`, and
  `postcss` from the legacy `package.json` are removed; only the
  Tailwind 4 dependency is added to the new `package.json`.
- The bespoke `:root` block in `globals.css` MUST come **after**
  the Tailwind 4 utility layer so it keeps the final word in
  cascade order (matching the legacy `web/index.html` order:
  `<link rel="stylesheet" href="dist/tailwind.css" />` first,
  `<style>` second).