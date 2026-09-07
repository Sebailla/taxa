/**
 * Public barrel for the `app-shell` capability module (PR 2a scaffold
 * + PR 4b integration seam + PR 5b.4 addendum).
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
 *   - `BrowserSurface` (PR 5b.4) — the global Research / file
 *     explorer host. Wraps `FileExplorer` with `taxonId={null}` so
 *     the explorer mounts its no-taxon idle state. Mounted by AppShell
 *     when the primary nav tab is `browser`. NOT taxon-scoped.
 *
 * `app-shell` is the host module for the single Next.js route
 * (`src/app/page.tsx`). It composes the other capability modules
 * through their public barrels — never by deep import.
 *
 * PR 5c.1b-A EXTENDS the public surface with:
 *   - `useBrowserStateStore` — React hook that reads the SINGLE typed
 *     store the AppShell owns, exposed via `BrowserStateStoreContext`.
 *     Cross-module consumers (currently only `src/app/page.tsx`, which
 *     subscribes to `treeSource` via `useSyncExternalStore`) read the
 *     current selection without constructing a parallel store. The
 *     AppShell is still the sole `createBrowserStateStore()` call
 *     site in the codebase.
 */

export { AppShell, BrowserSurface } from "./presentation";
export { useBrowserStateStore } from "./presentation/browser-state-store-context";
