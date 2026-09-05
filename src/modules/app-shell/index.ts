/**
 * Public barrel for the `app-shell` capability module (PR 2a scaffold
 * + PR 4b integration seam).
 *
 * spec.md rule 5: cross-module consumers MUST import only from this
 * file (or via the `@taxa/app-shell` path alias defined in
 * `tsconfig.json`). Direct imports into the layer folders below are
 * blocked by `.eslintrc.cjs::no-restricted-imports`.
 *
 * Exports:
 *   - `AppShell` (PR 4b.2 + PR 4b.6) — the root chrome shell. Owns the
 *     typed `browser-state` store, gates every persisted-state read
 *     behind `useMounted()`, and rehydrates `last-taxon-id` into the
 *     URL after the first paint. Consumed by `src/app/layout.tsx`
 *     which wraps `{children}` in `<AppShell>...</AppShell>`.
 *
 * `app-shell` is the host module for the single Next.js route
 * (`src/app/page.tsx`). It composes the other capability modules
 * through their public barrels — never by deep import.
 */

export { AppShell } from "./presentation/AppShell";
