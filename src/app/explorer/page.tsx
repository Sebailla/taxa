/**
 * `/explorer` route — isolated Browser-tab file explorer
 * (ODD-MIGRATE-003 / W6.1).
 *
 * Server Component. Passes ONLY serializable props
 * (`apiOrigin: string`) to the `Explorer` client island —
 * a Server Component cannot pass repository functions to a
 * Client Component, so the W3 `fetchFiles` / `fetchFileServe`
 * adapter is constructed inside the client island through
 * the public `@taxa/research` barrel with the same-origin
 * base URL. The route stays free of `next/dynamic`, free of
 * CDN scripts, free of legacy `web/` mutation, free of
 * FastAPI imports, free of search / splitter / materialization,
 * free of browser-state expansion, and free of cutover work.
 *
 * spec.md rule 5 — the route imports only from the public
 * barrels (`@taxa/research`, `@taxa/app-shell`). The ESLint
 * `no-restricted-imports` guard rejects deep paths into the
 * layer folders of every capability module.
 *
 * The route is mounted under `src/app/explorer/page.tsx`
 * (NOT `src/app/page.tsx`) so the main index route stays
 * free of Research concerns — the static export preserves
 * the existing taxonomy single-screen entry point and adds
 * the isolated `/explorer` route alongside it. The route is
 * reachable through the static export at `/explorer.html`
 * (or `/explorer/` when served by FastAPI's
 * `StaticFiles(html=True)` mount).
 *
 * W6.1 contract — non-CDN Explorer/Viewer mount only. No
 * search, no splitter, no CDN viewers, no browser-state
 * expansion, no legacy mutation, no cutover. The route is
 * reviewable in isolation; future slices add search /
 * splitter / materialization / CDN viewers through
 * separately authorized follow-up PRs.
 */

import { AppShell } from "@taxa/app-shell";
import { Explorer } from "@taxa/research";

export const metadata = {
  title: "Research Explorer — taxa",
  description:
    "Isolated Browser-tab file explorer for the research folders served by the FastAPI backend.",
};

export default function ExplorerPage(): React.ReactElement {
  return (
    <AppShell title="Research Explorer" apiOrigin="/api" currentRoute="explorer">
      <Explorer apiOrigin="/api" />
    </AppShell>
  );
}
