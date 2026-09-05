/**
 * Public barrel for the `design-system` capability module.
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via the `@taxa/design-system` path alias defined in
 * `tsconfig.json`). Direct imports into the layer folders below
 * (`presentation`, `application`, `domain`, `infrastructure`) are
 * blocked by `.eslintrc.cjs::no-restricted-imports`.
 *
 * PR 2a (Phase 2 scaffold work unit) shipped an empty barrel.
 *
 * PR 5b.4 EXTENDS the public surface with the promoted `TabStrip`
 * primitive (verbatim port of the taxonomy local `TabStrip` from 5a.3
 * — see openspec/changes/complete-taxa-frontend-migration/tasks.md
 * §"Addendum — 2026-09-04: Phase 5a four-slice replan"). The promotion
 * closes the deferred TabStrip-to-design-system move the 5a.3 addendum
 * scheduled for the 5b slice.
 */

export {
  TabStrip,
  type TabDefinition,
  type TabStripProps,
} from "./presentation";
