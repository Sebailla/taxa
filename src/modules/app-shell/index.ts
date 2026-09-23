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
 *
 * ODD-ASN-002 extends the barrel with the four sub-components the
 * ODD-ASN-002 AppShell rebuild decomposes into: `AppShellHeader`,
 * `AppShellFooter`, `AppShellNav`, `AppShellGlobalSearch`. The
 * sub-components stay optional re-exports — the default `AppShell`
 * remains the canonical entry point for cross-module consumers.
 * Test harnesses + future slices that need direct access to a
 * sub-component (e.g. an isolated render test) reach the typed
 * surface through this barrel.
 */
export { default as AppShell } from "./presentation/AppShell";
export type { AppShellProps } from "./presentation/AppShell";
export { default as AppShellHeader } from "./presentation/AppShellHeader";
export type { AppShellHeaderProps } from "./presentation/AppShellHeader";
export { default as AppShellFooter } from "./presentation/AppShellFooter";
export type { AppShellFooterProps } from "./presentation/AppShellFooter";
export { default as AppShellNav } from "./presentation/AppShellNav";
export type { AppShellNavProps } from "./presentation/AppShellNav";
export { default as AppShellGlobalSearch } from "./presentation/AppShellGlobalSearch";
export type { AppShellGlobalSearchProps } from "./presentation/AppShellGlobalSearch";