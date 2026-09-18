/**
 * Public barrel for the `app-shell` capability module.
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via the `@taxa/app-shell` path alias defined in
 * `tsconfig.json`). Direct imports into the layer folders below are
 * blocked by `.eslintrc.cjs::no-restricted-imports`.
 *
 * ODD-VTREE-002 ships the server-component `AppShell` (header /
 * footer frame). The taxonomy tree mounts inside `<AppShell>` via
 * the public `@taxa/taxonomy` barrel — never by deep import.
 */
export { default as AppShell } from "./presentation/AppShell";
export type { AppShellProps } from "./presentation/AppShell";
