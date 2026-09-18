/**
 * AppShell — quiet single-pane workstation frame (ODD-VTREE-002).
 *
 * Server component: no client boundary here. Renders a compact header
 * (product title), a single main pane, and an API-status footer. The
 * taxonomy tree (a client island) mounts in the main pane and owns its
 * own loading / error / empty / per-row affordances.
 *
 * Footer's API-status copy stays server-rendered (static export). The
 * live connection state surfaces inside the main pane via
 * `role="status"` / `role="alert"` regions so screen readers announce
 * the transition as the tree fetches.
 *
 * spec.md rule 4 / rule 5: AppShell depends on React types only — no
 * framework, no HTTP, no browser state. Reuses the existing Tailwind
 * `bg-surface` / `text-on-surface` / `border-outline-variant` utility
 * classes mapped onto the canonical @theme tokens in globals.css.
 */
import type { ReactNode } from "react";

export interface AppShellProps {
  readonly title: string;
  readonly apiOrigin: string;
  readonly children: ReactNode;
}

export default function AppShell({
  title,
  apiOrigin,
  children,
}: AppShellProps): React.ReactElement {
  return (
    <div className="flex min-h-screen flex-col bg-surface-container-lowest text-on-surface">
      <header className="border-b border-outline-variant bg-surface">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <h1 className="text-lg font-semibold tracking-tight text-on-surface">
            {title}
          </h1>
        </div>
      </header>
      <main className="flex-1">
        <div className="mx-auto w-full max-w-5xl px-6 py-6">{children}</div>
      </main>
      <footer className="border-t border-outline-variant bg-surface text-on-surface-variant">
        <div className="mx-auto flex max-w-5xl items-center gap-2 px-6 py-3 text-xs">
          <span>API</span>
          <code className="rounded bg-surface-container-low px-1.5 py-0.5 font-mono text-[11px]">
            {apiOrigin}
          </code>
          <span aria-hidden="true">·</span>
          <span>static export</span>
        </div>
      </footer>
    </div>
  );
}
