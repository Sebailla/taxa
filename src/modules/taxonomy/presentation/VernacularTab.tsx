"use client";

/**
 * VernacularTab — native DetailPanel Vernaculars tab body (ODD-TDV-001).
 *
 * Renders the server-composed vernacular (common name) rows under
 * the native "Vernacular names" header + count badge, paints
 * loading / empty / error / retry states, and renders each row as
 * a `.detail-item` carrying the verbatim ISO language / country
 * chips plus the name. The wire payload is the canonical
 * `VernacularName` projection from `infrastructure/api.ts`; the
 * language + country codes round-trip verbatim (no client-side
 * encoding or coercion) so the React cutover matches the legacy
 * `web/detail.js::loadDetail` + `buildDetailSection` byte-for-byte.
 *
 * The component is a pure renderer: it receives a `status` union
 * (idle / loading / loaded / empty / error) + a `names` array + a
 * retry callback. The TaxonomyTree parent owns the cache + the
 * eager-fetch-on-selection contract (mirrors how the
 * `perTaxonActiveTab` memory and `searchesByTaxonId` cache are
 * owned upstream). Wiring the fetch in the parent means the
 * panel can mount `<VernacularTab status="loaded" />` on tab
 * activation with zero round-trip cost (the data is already in
 * the per-taxon cache by the time the user clicks the Vernaculars
 * tab).
 *
 * Source isolation: the vernaculars endpoint is source-AGNOSTIC
 * — `web/detail.js` and the FastAPI route share a single
 * `/api/taxon/{id}/vernaculars` projection regardless of the
 * active tree source. The parent cache therefore survives
 * source switches (the React contract mirrors the legacy
 * `state.detail.vernaculars` payload which is loaded once per
 * selection and is also source-agnostic).
 *
 * spec.md rule 4: presentation → taxonomy domain only. The
 * component imports the canonical `VernacularName` projection
 * from the infrastructure module + no React / Next / HTTP / fetch
 * / DOM tokens in the body (defensive — the file declares
 * `"use client"` because the parent TaxonomyTree island needs the
 * retry button + the per-row chip rendering to stay interactive,
 * but the VernacularTab body itself is a pure JSX renderer).
 */
import type { VernacularName } from "../infrastructure/api";

/** Status of the vernaculars fetch for the currently selected
 *  taxon. The parent (`TaxonomyTree`) owns the per-taxon cache
 *  and feeds the VernacularTab one of these discriminated-union
 *  states per render. `idle` means the parent hasn't started
 *  the fetch yet (defensive — the eager-fetch-on-selection
 *  contract fires the request the moment a taxon becomes the
 *  active selection, so `idle` is rare in practice). The shape
 *  mirrors `SearchTabStatus` byte-for-byte so the parent's
 *  cache-rebuild / retry wiring stays symmetric across the
 *  Vernaculars and Search tabs. */
export type VernacularTabStatus =
  | { readonly kind: "idle" }
  | { readonly kind: "loading" }
  | { readonly kind: "loaded"; readonly names: readonly VernacularName[] }
  | { readonly kind: "empty" }
  | { readonly kind: "error"; readonly message: string };

export interface VernacularTabProps {
  readonly status: VernacularTabStatus;
  /** Retry callback. Fires when the user clicks the "Retry"
   *  button on the error state. The parent maps this to a
   *  re-issuance of the canonical `fetchVernaculars` request. */
  readonly onRetry: () => void;
}

/** Public component. Renders one of: loading copy, empty copy
 *  ("No vernacular names available for this taxon."), error
 *  copy + Retry button, or the canonical native "Vernacular
 *  names" header + count badge + the per-row `.detail-item`
 *  list. The wrapper carries the canonical `.vernacular-tab`
 *  class so the existing `src/app/globals.css` cascade paints
 *  the section header, the count chip, the row chips, and the
 *  per-row hover affordance without a redesign pass (mirrors the
 *  legacy `web/detail.js::buildDetailSection("translate",
 *  "Vernacular names", d.vernaculars.length, items)` call site
 *  byte-for-byte except for the React component boundary). */
export default function VernacularTab({
  status,
  onRetry,
}: VernacularTabProps): React.ReactElement {
  if (status.kind === "idle" || status.kind === "loading") {
    return (
      <div
        className="vernacular-tab"
        data-tab-content="vernaculars"
        data-vernacular-status={status.kind}
        role="status"
        aria-busy="true"
      >
        <h3
          className="vernacular-section-header"
          data-vernacular-section-header=""
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[16px]"
          >
            translate
          </span>
          <span>Vernacular names</span>
          <span
            className="vernacular-section-count"
            aria-label="0 vernacular names"
          >
            0
          </span>
        </h3>
        <p className="text-body-sm text-on-surface-variant px-2 py-4 text-center">
          Loading vernacular names…
        </p>
      </div>
    );
  }
  if (status.kind === "empty") {
    return (
      <div
        className="vernacular-tab"
        data-tab-content="vernaculars"
        data-vernacular-status="empty"
        data-vernacular-count="0"
        role="status"
      >
        <h3
          className="vernacular-section-header"
          data-vernacular-section-header=""
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[16px]"
          >
            translate
          </span>
          <span>Vernacular names</span>
          <span
            className="vernacular-section-count"
            aria-label="0 vernacular names"
          >
            0
          </span>
        </h3>
        <p className="text-body-sm text-on-surface-variant px-2 py-4 text-center">
          No vernacular names available for this taxon.
        </p>
      </div>
    );
  }
  if (status.kind === "error") {
    return (
      <div
        className="vernacular-tab"
        data-tab-content="vernaculars"
        data-vernacular-status="error"
        role="alert"
      >
        <h3
          className="vernacular-section-header"
          data-vernacular-section-header=""
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[16px]"
          >
            translate
          </span>
          <span>Vernacular names</span>
          <span
            className="vernacular-section-count"
            aria-label="0 vernacular names"
          >
            0
          </span>
        </h3>
        <p className="text-body-sm text-on-surface px-2 py-2 text-center">
          Could not load vernacular names.
        </p>
        <p className="text-caption text-on-surface-variant px-2 pb-2 text-center">
          {status.message}
        </p>
        <div className="flex justify-center pb-2">
          <button
            type="button"
            className="rounded-md border border-outline-variant bg-surface px-3 py-1.5 text-sm font-medium text-on-surface hover:bg-surface-container-low"
            data-action="retry-vernaculars"
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
      className="vernacular-tab"
      data-tab-content="vernaculars"
      data-vernacular-status="loaded"
      data-vernacular-count={String(status.names.length)}
    >
      <h3
        className="vernacular-section-header"
        data-vernacular-section-header=""
      >
        <span
          aria-hidden="true"
          className="material-symbols-outlined text-[16px]"
        >
          translate
        </span>
        <span>Vernacular names</span>
        <span
          className="vernacular-section-count"
          aria-label={`${status.names.length} vernacular names`}
        >
          {status.names.length}
        </span>
      </h3>
      <div
        className="vernacular-list"
        data-vernacular-list=""
      >
        {status.names.map((v) => (
          <div
            key={v.id}
            className="detail-item"
            data-vernacular-item-id={v.id}
            data-vernacular-item-language={v.language ?? undefined}
            data-vernacular-item-country={v.country ?? undefined}
          >
            {v.language ? (
              <span
                className="lang"
                data-vernacular-item-language-chip=""
              >
                {v.language}
              </span>
            ) : null}
            {v.country ? (
              <span
                className="country"
                data-vernacular-item-country-chip=""
              >
                {v.country}
              </span>
            ) : null}
            <span
              className="vernacular-name"
              data-vernacular-item-name=""
            >
              {v.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}