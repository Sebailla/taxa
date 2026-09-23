/**
 * Global 404 page — the ODD-ASN-003 recovery surface.
 *
 * Server Component. Mounts the AppShell frame (so the four-
 * destination navigation surface stays consistent with every
 * other route) and renders a quiet "404 — Page not found"
 * card with a "Pick a destination" list linking to the four
 * top-level destinations the brief pins: Classification
 * (`/`), Browser (`/explorer`), Help (`/help`), Settings
 * (`/settings`).
 *
 * Next 16 file convention: this file lives at the root of
 * `src/app/` so Next.js renders it for any URL that does
 * NOT match a declared route (no `notFound()` throw needed
 * — the App Router's `not-found.tsx` boundary fires
 * automatically when the URL fails to resolve).
 *
 *   see `node_modules/next/dist/docs/01-app/03-api-reference/
 *   03-file-conventions/not-found.md`
 *
 * Notes:
 *
 *   - The root layout (`src/app/layout.tsx`) already emits
 *     the skip-to-main `<a href="#main">` link + the Raleway
 *     font + the version banner — this page inherits the
 *     cascade without re-declaring any of it.
 *
 *   - The AppShell orchestrator wraps the body in
 *     `<main id="main">` so the skip-link target resolves.
 *     The 404 page MUST NOT declare a second `<main>` — the
 *     landmark triple lives in the AppShell.
 *
 *   - The destination list uses `<Link>` from `next/link` for
 *     client-side navigation per the AppShell nav pattern.
 *     The static export serves plain `<a>` tags anyway so
 *     either form resolves the same URL.
 *
 * spec.md rule 5 — imports come only from the public barrels
 * (`@taxa/app-shell`). The ESLint `no-restricted-imports`
 * guard rejects deep paths into the layer folders of every
 * capability module.
 */
import Link from "next/link";

import { AppShell } from "@taxa/app-shell";

export const metadata = {
  title: "404 — taxa",
  description:
    "The requested page is not part of the Taxa product. Pick a destination from the list below.",
};

/**
 * The four recovery destinations the brief pins. Order is
 * locked: Classification / Browser / Help / Settings — the
 * same order the AppShellNav's `NAV_LINKS` array carries, so
 * the recovery surface is consistent with the header nav.
 */
const NOT_FOUND_DESTINATIONS: ReadonlyArray<{
  readonly href: string;
  readonly label: string;
}> = [
  { href: "/", label: "Classification" },
  { href: "/explorer", label: "Browser" },
  { href: "/help", label: "Help" },
  { href: "/settings", label: "Settings" },
];

export default function NotFound(): React.ReactElement {
  return (
    <AppShell title="404" apiOrigin="/api" schemaVersion="1">
      <article
        className="app-not-found flex flex-col gap-6"
        data-app-not-found=""
      >
        <header className="app-not-found-header">
          <h2 className="text-3xl font-bold tracking-tight text-primary">
            404 — Page not found
          </h2>
          <p className="mt-2 text-body-sm text-on-surface-variant">
            The page you requested is not part of the Taxa
            product.
          </p>
        </header>
        <section
          className="app-not-found-section app-not-found-section--destinations"
          data-app-not-found-section="destinations"
          aria-labelledby="app-not-found-destinations-heading"
        >
          <h3
            id="app-not-found-destinations-heading"
            className="text-base font-semibold tracking-tight text-on-surface"
          >
            Pick a destination
          </h3>
          <ul className="mt-2 flex flex-col gap-1 text-body-sm">
            {NOT_FOUND_DESTINATIONS.map((dest) => (
              <li key={dest.href}>
                <Link
                  href={dest.href}
                  className="app-not-found-link text-primary underline hover:no-underline"
                  data-app-not-found-link=""
                  data-app-not-found-link-href={dest.href}
                >
                  {dest.label}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </article>
    </AppShell>
  );
}
