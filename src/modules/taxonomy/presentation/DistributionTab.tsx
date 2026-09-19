"use client";

/**
 * DistributionTab — native DetailPanel Distribution tab body (ODD-TDDIST-001).
 *
 * Renders the server-composed distribution (geographic range) rows
 * under the native "Distribution" header + count badge, paints
 * loading / empty / error / retry states, and renders each row as
 * a `.detail-item` carrying the establishment-means chip (with
 * client fallback `unknown` for the `null` wire value) + the area
 * text. The wire payload is the canonical `DistributionEntry`
 * projection from `infrastructure/api.ts`; the area +
 * establishment_means values round-trip verbatim from the server
 * while the canonical projection ALSO carries the
 * gazetteer + degree_of_establishment fields so a future
 * server-composed affordance does not require a coordinated
 * React update (mirrors how `SynonymName.status` survives even
 * though `SynonymTab` does not render it — ODD-TDSYN-001).
 *
 * The component is a pure renderer: it receives a `status`
 * union (idle / loading / loaded / empty / error) + an
 * `entries` array + a retry callback. The TaxonomyTree parent
 * owns the cache + the eager-fetch-on-selection contract
 * (mirrors how the `perTaxonActiveTab` memory and the
 * `searchesByTaxonId` / `vernacularsByTaxonId` /
 * `synonymsByTaxonId` caches are owned upstream). Wiring the
 * fetch in the parent means the panel can mount
 * `<DistributionTab status="loaded" />` on tab activation
 * with zero round-trip cost (the data is already in the
 * per-taxon cache by the time the user clicks the
 * Distribution tab).
 *
 * Source isolation: the distribution endpoint is
 * source-AGNOSTIC — `web/detail.js` and the FastAPI route
 * share a single `/api/taxon/{id}/distribution?limit=200`
 * projection regardless of the active tree source. The
 * parent cache therefore survives source switches (the
 * React contract mirrors the legacy `state.detail.distribution`
 * payload which is loaded once per selection and is also
 * source-agnostic). The row ordering preserves the
 * server-side `ORDER BY establishment_means, area` (the
 * render loop is a for-each over the response array — the
 * UI does NOT sort / group / filter / paginate client-side,
 * per the ODD-TDDIST-001 user constraint).
 *
 * Client fallback for missing establishment means: the
 * legacy `web/detail.js::buildDetailSection` renders
 * `x.establishment_means || "unknown"` so a row with a
 * `null` wire `establishment_means` paints the chip with
 * `unknown` text + `means-unknown` styling. The React port
 * preserves that exact fallback: the projection surface
 * carries `establishment_means: string | null` (no client
 * coercion) and the renderer substitutes `"unknown"` at
 * render time only (the chip text + the `.means-unknown`
 * styling).
 *
 * spec.md rule 4: presentation → taxonomy domain only. The
 * component imports the canonical `DistributionEntry`
 * projection from the infrastructure module + the pure
 * `scientificNameClass` helper from the sibling row-format
 * module; no React / Next / HTTP / fetch / DOM tokens land
 * in this file's body (defensive — the file declares
 * `"use client"` because the parent TaxonomyTree island
 * needs the retry button + the per-row chip rendering to
 * stay interactive, but the DistributionTab body itself is a
 * pure JSX renderer).
 */
import type { DistributionEntry } from "../infrastructure/api";

/** Status of the distribution fetch for the currently
 *  selected taxon. The parent (`TaxonomyTree`) owns the
 *  per-taxon cache and feeds the DistributionTab one of
 *  these discriminated-union states per render. `idle`
 *  means the parent hasn't started the fetch yet
 *  (defensive — the eager-fetch-on-selection contract fires
 *  the request the moment a taxon becomes the active
 *  selection, so `idle` is rare in practice). The shape
 *  mirrors `SearchTabStatus` + `VernacularTabStatus` +
 *  `SynonymTabStatus` byte-for-byte so the parent's
 *  cache-rebuild / retry wiring stays symmetric across the
 *  Search, Vernaculars, Synonyms, and Distribution tabs. */
export type DistributionTabStatus =
  | { readonly kind: "idle" }
  | { readonly kind: "loading" }
  | { readonly kind: "loaded"; readonly entries: readonly DistributionEntry[] }
  | { readonly kind: "empty" }
  | { readonly kind: "error"; readonly message: string };

/** Client fallback for the missing establishment_means wire
 *  value. Mirrors the legacy `web/detail.js::buildDetailSection`
 *  `x.establishment_means || "unknown"` fallback so the React
 *  port renders identically when the wire carries
 *  `establishment_means: null`. The chip text + the
 *  `.means-unknown` styling both apply (the CSS rule lives
 *  at `src/app/globals.css::.distribution-tab > .distribution-list
 *  > .detail-item > .means-unknown`). */
const UNKNOWN_ESTABLISHMENT_MEANS = "unknown";

/** Build the client fallback means string from a wire value.
 *  Returns the wire string verbatim when present, the
 *  `UNKNOWN_ESTABLISHMENT_MEANS` literal otherwise. Mirrors
 *  the legacy `web/detail.js::buildDetailSection` `||` fallback
 *  so a `null` wire value paints `unknown` (the legacy oracle
 *  uses truthy-check `||`, which collapses `null` + `""` +
 *  `undefined` to the same fallback). The projection surface
 *  carries `establishment_means: string | null` (no client
 *  coercion), so the substitution happens here at render time
 *  only. */
function establishmentMeansFor(entry: DistributionEntry): string {
  return entry.establishment_means ?? UNKNOWN_ESTABLISHMENT_MEANS;
}

export interface DistributionTabProps {
  readonly status: DistributionTabStatus;
  /** Retry callback. Fires when the user clicks the "Retry"
   *  button on the error state. The parent maps this to a
   *  re-issuance of the canonical `fetchDistribution`
   *  request. */
  readonly onRetry: () => void;
}

/** Public component. Renders one of: loading copy, empty
 *  copy ("No distribution data available for this taxon."),
 *  error copy + Retry button, or the canonical native
 *  "Distribution" header + count badge + the per-row
 *  `.detail-item` list. The wrapper carries the canonical
 *  `.distribution-tab` class so the existing
 *  `src/app/globals.css` cascade paints the section header,
 *  the count chip, the establishment-means chip + area
 *  text, and the per-row hover affordance without a
 *  redesign pass (mirrors the legacy
 *  `web/detail.js::buildDetailSection("public",
 *  "Distribution", d.distribution.length, items)` call site
 *  byte-for-byte except for the React component boundary +
 *  the scoped `.means` selector that names the
 *  establishment-means chip explicitly under
 *  `.distribution-tab > .distribution-list > .detail-item`).
 *  Each row carries `data-distribution-item-id` so the
 *  legacy `data-action` selector pattern keeps working +
 *  the establishment-means chip carries
 *  `data-distribution-item-means` + the area carries
 *  `data-distribution-item-area` so test fixtures can pin
 *  the row identity without a deep class-name scrape. */
export default function DistributionTab({
  status,
  onRetry,
}: DistributionTabProps): React.ReactElement {
  if (status.kind === "idle" || status.kind === "loading") {
    return (
      <div
        className="distribution-tab"
        data-tab-content="distribution"
        data-distribution-status={status.kind}
        role="status"
        aria-busy="true"
      >
        <h3
          className="distribution-section-header"
          data-distribution-section-header=""
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[16px]"
          >
            public
          </span>
          <span>Distribution</span>
          <span
            className="distribution-section-count"
            aria-label="0 distribution rows"
          >
            0
          </span>
        </h3>
        <p className="text-body-sm text-on-surface-variant px-2 py-4 text-center">
          Loading distribution…
        </p>
      </div>
    );
  }
  if (status.kind === "empty") {
    return (
      <div
        className="distribution-tab"
        data-tab-content="distribution"
        data-distribution-status="empty"
        data-distribution-count="0"
        role="status"
      >
        <h3
          className="distribution-section-header"
          data-distribution-section-header=""
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[16px]"
          >
            public
          </span>
          <span>Distribution</span>
          <span
            className="distribution-section-count"
            aria-label="0 distribution rows"
          >
            0
          </span>
        </h3>
        <p className="text-body-sm text-on-surface-variant px-2 py-4 text-center">
          No distribution data available for this taxon.
        </p>
      </div>
    );
  }
  if (status.kind === "error") {
    return (
      <div
        className="distribution-tab"
        data-tab-content="distribution"
        data-distribution-status="error"
        role="alert"
      >
        <h3
          className="distribution-section-header"
          data-distribution-section-header=""
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[16px]"
          >
            public
          </span>
          <span>Distribution</span>
          <span
            className="distribution-section-count"
            aria-label="0 distribution rows"
          >
            0
          </span>
        </h3>
        <p className="text-body-sm text-on-surface px-2 py-2 text-center">
          Could not load distribution.
        </p>
        <p className="text-caption text-on-surface-variant px-2 pb-2 text-center">
          {status.message}
        </p>
        <div className="flex justify-center pb-2">
          <button
            type="button"
            className="rounded-md border border-outline-variant bg-surface px-3 py-1.5 text-sm font-medium text-on-surface hover:bg-surface-container-low"
            data-action="retry-distribution"
            onClick={onRetry}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }
  return (
    <div
      className="distribution-tab"
      data-tab-content="distribution"
      data-distribution-status="loaded"
      data-distribution-count={String(status.entries.length)}
    >
      <h3
        className="distribution-section-header"
        data-distribution-section-header=""
      >
        <span
          aria-hidden="true"
          className="material-symbols-outlined text-[16px]"
        >
          public
        </span>
        <span>Distribution</span>
        <span
          className="distribution-section-count"
          aria-label={`${status.entries.length} distribution rows`}
        >
          {status.entries.length}
        </span>
      </h3>
      <div
        className="distribution-list"
        data-distribution-list=""
      >
        {status.entries.map((e) => {
          const means = establishmentMeansFor(e);
          return (
            <div
              key={e.id}
              className="detail-item"
              data-distribution-item-id={e.id}
              data-distribution-item-means={means}
            >
              <span
                className={`means means-${means}`}
                data-distribution-item-means-chip=""
              >
                {means}
              </span>
              <span
                className="distribution-area"
                data-distribution-item-area=""
              >
                {e.area}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}