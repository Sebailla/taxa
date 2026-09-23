/**
 * `/settings` route — the ODD-ASN-002 settings stub.
 *
 * Server Component. Mounts the AppShell frame (so the four-
 * destination navigation surface stays consistent with every
 * other route) and renders a quiet "Coming soon" placeholder.
 * The settings surface (theme switcher, tree-source default,
 * any reset affordances, etc.) ships with a future slice;
 * ODD-ASN-002 ships only the navigation surface + the route
 * entry so the destination is reachable from day 1.
 *
 * spec.md rule 5 — imports come only from the public barrels
 * (`@taxa/app-shell`). The ESLint `no-restricted-imports`
 * guard rejects deep paths into the layer folders of every
 * capability module.
 */
import { AppShell } from "@taxa/app-shell";

export const metadata = {
  title: "Settings — taxa",
  description:
    "Quiet stub for the settings route — the AppShell navigation surface is real on day 1, the settings content ships with a future slice.",
};

export default function SettingsPage(): React.ReactElement {
  return (
    <AppShell title="Settings" apiOrigin="/api" schemaVersion="1" currentRoute="settings">
      <article
        className="app-settings flex flex-col items-start gap-4"
        data-app-settings=""
        data-app-settings-status="coming-soon"
      >
        <header className="app-settings-header">
          <h1 className="text-2xl font-semibold tracking-tight text-on-surface">
            Settings
          </h1>
          <p className="mt-1 text-sm text-on-surface-variant">
            The settings surface is reserved for a future slice.
          </p>
        </header>
        <p
          className="app-settings-coming-soon rounded-md border border-outline-variant bg-surface px-4 py-3 text-body-sm text-on-surface-variant"
          data-app-settings-coming-soon=""
        >
          Coming soon — the destination exists so the navigation
          surface is real on day 1, but the settings content
          (theme switcher, tree-source default, reset
          affordances, …) lands with a follow-up slice.
        </p>
      </article>
    </AppShell>
  );
}