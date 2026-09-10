import type { Metadata, Viewport } from "next";
import type { ReactElement, ReactNode } from "react";

/**
 * Minimal semantic root layout for the React E2E harness
 * (PR 5c.2-B.1a).
 *
 * NOT a chrome / app-shell replica. Carries only:
 *   - `<html lang="en">` (the App Router static-export minimum)
 *   - a clear harness title that distinguishes the harness from the
 *     production frontend (so a Playwright session that lands on
 *     this page cannot be confused with `make api`'s root index).
 *   - the responsive viewport meta.
 *
 * The production `<AppShell>`, `BrowserSurface`, root `globals.css`,
 * Raleway `next/font/google` preload, and any chrome wrapper are
 * intentionally absent — the harness renders only the bare markup
 * the future capture driver needs. No `import "./globals.css"` line
 * (that import is owned by the production layout; the harness owns
 * no design tokens, no Tailwind 4 cascade, and no utility surface).
 */

export const metadata: Metadata = {
  title: "Taxa React E2E Harness — FileExplorer mount",
  description:
    "Isolated React 19 + Next 16 harness that mounts FileExplorer from @taxa/research against a synthetic taxon id. Diagnostic-only; not part of the production frontend.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function HarnessLayout({
  children,
}: {
  readonly children: ReactNode;
}): ReactElement {
  return (
    <html lang="en">
      <body>
        <main data-harness-root="react-e2e">{children}</main>
      </body>
    </html>
  );
}
