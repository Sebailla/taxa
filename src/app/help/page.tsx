/**
 * `/help` route — the ODD-ASN-002 in-app help destination.
 *
 * Server Component. Renders the help content inside the AppShell
 * frame so the four-destination navigation surface stays
 * consistent with every other route (the brief requires the
 * AppShell on every route).
 *
 * The page covers the five sections the brief mandates:
 *
 *   1. Data-source legend — Catalogue of Life (CoL) +
 *      WoRMS marine overlay + Freshwater mirror. Explains the
 *      three taxonomies the tree exposes and what each covers.
 *   2. Keyboard shortcut map — every shortcut the AppShell
 *      wires (`Cmd+K` / `Ctrl+K`, `/`, `Escape`) plus the
 *      shortcuts the TaxonomyTree kebab / breadcrumb / search
 *      dropdown own. Cross-references the footer legend.
 *   3. Realm color legend — the realm tint the TaxonomyTree
 *      applies to leaf rows (animal / plant / freshwater).
 *   4. API docs link — points the developer at the OpenAPI
 *      spec the FastAPI backend exposes + the relative-origin
 *      endpoint surface the React mount consumes.
 *   5. Attribution — credits Catalogue of Life + WoRMS +
 *      Freshwater as the upstream data sources the React
 *      shell surfaces.
 *
 * spec.md rule 5 — imports come only from the public barrels
 * (`@taxa/app-shell`). The ESLint `no-restricted-imports`
 * guard rejects deep paths into the layer folders of every
 * capability module.
 */
import { AppShell } from "@taxa/app-shell";

export const metadata = {
  title: "Help — taxa",
  description:
    "In-app help destination for the taxa shell: data-source legend, keyboard shortcut map, realm color legend, API docs link, and attribution.",
};

export default function HelpPage(): React.ReactElement {
  return (
    <AppShell title="Help" apiOrigin="/api" schemaVersion="1" currentRoute="help">
      <article
        className="app-help flex flex-col gap-8"
        data-app-help=""
        data-app-help-section-count={5}
      >
        <header className="app-help-header">
          <h1 className="text-2xl font-semibold tracking-tight text-on-surface">
            Help
          </h1>
          <p className="mt-1 text-sm text-on-surface-variant">
            Everything you need to drive the taxa shell from the
            keyboard + the data sources the tree surfaces.
          </p>
        </header>

        {/* Section 1 — Data-source legend. */}
        <section
          className="app-help-section app-help-section--data-source"
          data-app-help-section="data-source"
          aria-labelledby="help-data-source-heading"
        >
          <h2
            id="help-data-source-heading"
            className="text-lg font-semibold tracking-tight text-on-surface"
          >
            Data sources
          </h2>
          <ul className="mt-2 flex flex-col gap-2 text-body-sm text-on-surface-variant">
            <li>
              <strong className="text-on-surface">Catalogue of Life (CoL).</strong>{" "}
              The taxonomic backbone. Most rows resolve to CoL
              ids; the source selector defaults to this view.
            </li>
            <li>
              <strong className="text-on-surface">WoRMS marine overlay.</strong>{" "}
              Marine-only overlay for shallow-water taxa. Cross-
              links the CoL id to the WoRMS AphiaID; the kebab
              menu exposes a "View on WoRMS" anchor.
            </li>
            <li>
              <strong className="text-on-surface">Freshwater mirror.</strong>{" "}
              Freshwater-specific subset surfaced when at least
              one root row carries a non-null `freshwater_id`.
              Toggle via the source selector in the tree header.
            </li>
          </ul>
        </section>

        {/* Section 2 — Keyboard shortcut map. */}
        <section
          className="app-help-section app-help-section--shortcut"
          data-app-help-section="shortcut"
          aria-labelledby="help-shortcut-heading"
        >
          <h2
            id="help-shortcut-heading"
            className="text-lg font-semibold tracking-tight text-on-surface"
          >
            Keyboard shortcuts
          </h2>
          <dl className="mt-2 grid grid-cols-[8rem_1fr] gap-x-4 gap-y-1 text-body-sm">
            <dt className="font-mono text-on-surface">
              <kbd>Cmd</kbd>+<kbd>K</kbd> / <kbd>Ctrl</kbd>+<kbd>K</kbd>
            </dt>
            <dd className="text-on-surface-variant">
              Focus the global search input (always honoured,
              even when another field has focus).
            </dd>
            <dt className="font-mono text-on-surface">
              <kbd>/</kbd>
            </dt>
            <dd className="text-on-surface-variant">
              Focus the global search input — skipped when you
              are already typing inside another input /
              textarea / contenteditable element.
            </dd>
            <dt className="font-mono text-on-surface">
              <kbd>Esc</kbd>
            </dt>
            <dd className="text-on-surface-variant">
              Blur the current focus and clear the global
              search query when non-empty. The TaxonomyTree
              also uses <kbd>Esc</kbd> to dismiss an open kebab
              menu.
            </dd>
            {/* ODD-EXP-002 — `?` opens the help page (the
                navigation is a `useRouter().push("/help")`
                call inside the AppShellGlobalSearch keydown
                listener; same editable-field skip the `/`
                shortcut uses). */}
            <dt className="font-mono text-on-surface">
              <kbd>?</kbd>
            </dt>
            <dd className="text-on-surface-variant">
              Open this help page. Skipped when you are already
              typing inside another input / textarea /
              contenteditable element so the `?` key stays
              available for normal typing.
            </dd>
            <dt className="font-mono text-on-surface">
              <kbd>Enter</kbd> / <kbd>Space</kbd>
            </dt>
            <dd className="text-on-surface-variant">
              Activate the focused row in the taxonomy tree or
              the focused search-result row in the dropdown.
            </dd>
          </dl>
        </section>

        {/* Section 3 — Realm color legend. */}
        <section
          className="app-help-section app-help-section--realm"
          data-app-help-section="realm"
          aria-labelledby="help-realm-heading"
        >
          <h2
            id="help-realm-heading"
            className="text-lg font-semibold tracking-tight text-on-surface"
          >
            Realm color legend
          </h2>
          <ul className="mt-2 flex flex-col gap-1 text-body-sm text-on-surface-variant">
            <li>
              <span className="mr-2 inline-block h-3 w-3 rounded-sm bg-[color:var(--realm-animal)]" />
              <strong className="text-on-surface">Animal.</strong>{" "}
              The row belongs to the WoRMS / CoL animal
              kingdom branch.
            </li>
            <li>
              <span className="mr-2 inline-block h-3 w-3 rounded-sm bg-[color:var(--realm-plant)]" />
              <strong className="text-on-surface">Plant.</strong>{" "}
              The row belongs to the CoL plant branch.
            </li>
            <li>
              <span className="mr-2 inline-block h-3 w-3 rounded-sm bg-[color:var(--realm-freshwater)]" />
              <strong className="text-on-surface">Freshwater.</strong>{" "}
              The row carries a non-null `freshwater_id` and
              belongs to the Freshwater mirror.
            </li>
          </ul>
        </section>

        {/* Section 4 — API docs link. */}
        <section
          className="app-help-section app-help-section--api"
          data-app-help-section="api"
          aria-labelledby="help-api-heading"
        >
          <h2
            id="help-api-heading"
            className="text-lg font-semibold tracking-tight text-on-surface"
          >
            API docs
          </h2>
          <p className="mt-2 text-body-sm text-on-surface-variant">
            The FastAPI backend serves an OpenAPI schema at{" "}
            <code className="rounded bg-surface-container-low px-1.5 py-0.5 font-mono text-[12px]">
              /api/openapi.json
            </code>{" "}
            + an interactive Swagger UI at{" "}
            <code className="rounded bg-surface-container-low px-1.5 py-0.5 font-mono text-[12px]">
              /api/docs
            </code>
            . The React shell consumes the same-origin surface
            at <code className="rounded bg-surface-container-low px-1.5 py-0.5 font-mono text-[12px]">
              /api/domains
            </code>
            ,{" "}
            <code className="rounded bg-surface-container-low px-1.5 py-0.5 font-mono text-[12px]">
              /api/children
            </code>
            ,{" "}
            <code className="rounded bg-surface-container-low px-1.5 py-0.5 font-mono text-[12px]">
              /api/search
            </code>
            , and{" "}
            <code className="rounded bg-surface-container-low px-1.5 py-0.5 font-mono text-[12px]">
              /api/health
            </code>
            .
          </p>
        </section>

        {/* Section 5 — Attribution. */}
        <section
          className="app-help-section app-help-section--attribution"
          data-app-help-section="attribution"
          aria-labelledby="help-attribution-heading"
        >
          <h2
            id="help-attribution-heading"
            className="text-lg font-semibold tracking-tight text-on-surface"
          >
            Attribution
          </h2>
          <p className="mt-2 text-body-sm text-on-surface-variant">
            Taxonomic backbone data is sourced from the{" "}
            <strong>Catalogue of Life</strong>{" "}
            (<a
              href="https://www.catalogueoflife.org/"
              className="text-primary underline"
              rel="noreferrer"
              target="_blank"
            >
              catalogueoflife.org
            </a>
            ) + the{" "}
            <strong>World Register of Marine Species (WoRMS)</strong>{" "}
            (<a
              href="https://www.marinespecies.org/"
              className="text-primary underline"
              rel="noreferrer"
              target="_blank"
            >
              marinespecies.org
            </a>
            ) + the{" "}
            <strong>Freshwater Biodiversity</strong> mirror.
            Realm colors + the kebab / breadcrumb / search affordances
            are an original React port of the legacy native shell.
          </p>
        </section>
      </article>
    </AppShell>
  );
}