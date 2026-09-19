"use client";

/**
 * SynonymTab — native DetailPanel Synonyms tab body (ODD-TDSYN-001).
 *
 * Renders the server-composed synonym (historical name) rows under
 * the native "Synonyms" header + count badge, paints loading /
 * empty / error / retry states, and renders each row as a
 * `.detail-item` carrying the rank chip + the italic-or-roman
 * scientific name + the optional `.authorship` span. The wire
 * payload is the canonical `SynonymName` projection from
 * `infrastructure/api.ts`; the rank / scientific_name /
 * authorship / status values round-trip verbatim from the server
 * (the UI does NOT render the wire `status` field — see the
 * ODD-TDSYN-001 user constraint: "preserve server
 * rank/name/authorship/status and ordering … the UI must not
 * render status or client-sort").
 *
 * The component is a pure renderer: it receives a `status`
 * union (idle / loading / loaded / empty / error) + a `names`
 * array + a retry callback. The TaxonomyTree parent owns the
 * cache + the eager-fetch-on-selection contract (mirrors how
 * `perTaxonActiveTab` memory and `searchesByTaxonId` /
 * `vernacularsByTaxonId` caches are owned upstream). Wiring the
 * fetch in the parent means the panel can mount
 * `<SynonymTab status="loaded" />` on tab activation with zero
 * round-trip cost (the data is already in the per-taxon cache
 * by the time the user clicks the Synonyms tab).
 *
 * Source isolation: the synonyms endpoint is source-AGNOSTIC —
 * `web/detail.js` and the FastAPI route share a single
 * `/api/taxon/{id}/synonyms?limit=200` projection regardless of
 * the active tree source. The parent cache therefore survives
 * source switches (the React contract mirrors the legacy
 * `state.detail.synonyms` payload which is loaded once per
 * selection and is also source-agnostic). The row ordering
 * preserves the server-side `ORDER BY rank, scientific_name`
 * (the render loop is a for-each over the response array — the
 * UI does not sort or paginate client-side, matching the
 * ODD-TDSYN-001 user constraint).
 *
 * spec.md rule 4: presentation → taxonomy domain only. The
 * component imports the canonical `SynonymName` projection from
 * the infrastructure module + the pure `scientificNameClass`
 * helper from the sibling row-format module; no React / Next /
 * HTTP / fetch / DOM tokens land in this file's body
 * (defensive — the file declares `"use client"` because the
 * parent TaxonomyTree island needs the retry button + the
 * per-row chip rendering to stay interactive, but the
 * SynonymTab body itself is a pure JSX renderer).
 */
import type { SynonymName } from "../infrastructure/api";
import type { Rank } from "../domain/taxon";
import { scientificNameClass } from "./row-format";

/** The wire `SynonymName.rank` is a `string` so the FastAPI
 *  nullability + arbitrary-row safety contract is preserved.
 *  In practice the FastAPI server only returns rows whose
 *  `rank` is one of the canonical `Rank` union members (the
 *  CoL / TextTree SQL schema constrains the column at write
 *  time), so the narrow cast below is safe. A future row that
 *  carries an off-list rank falls back to the ICZN-roman
 *  branch of `scientificNameClass` (`isItalicRank` returns
 *  `false` for the default case). */
function rankClass(rank: string): string {
  return scientificNameClass(rank as Rank);
}

/** Status of the synonyms fetch for the currently selected
 *  taxon. The parent (`TaxonomyTree`) owns the per-taxon cache
 *  and feeds the SynonymTab one of these discriminated-union
 *  states per render. `idle` means the parent hasn't started
 *  the fetch yet (defensive — the eager-fetch-on-selection
 *  contract fires the request the moment a taxon becomes the
 *  active selection, so `idle` is rare in practice). The shape
 *  mirrors `SearchTabStatus` + `VernacularTabStatus`
 *  byte-for-byte so the parent's cache-rebuild / retry wiring
 *  stays symmetric across the Search, Vernaculars, and
 *  Synonyms tabs. */
export type SynonymTabStatus =
  | { readonly kind: "idle" }
  | { readonly kind: "loading" }
  | { readonly kind: "loaded"; readonly names: readonly SynonymName[] }
  | { readonly kind: "empty" }
  | { readonly kind: "error"; readonly message: string };

export interface SynonymTabProps {
  readonly status: SynonymTabStatus;
  /** Retry callback. Fires when the user clicks the "Retry"
   *  button on the error state. The parent maps this to a
   *  re-issuance of the canonical `fetchSynonyms` request. */
  readonly onRetry: () => void;
}

/** Public component. Renders one of: loading copy, empty copy
 *  ("No synonyms available for this taxon."), error copy +
 *  Retry button, or the canonical native "Synonyms" header +
 *  count badge + the per-row `.detail-item` list. The wrapper
 *  carries the canonical `.synonym-tab` class so the existing
 *  `src/app/globals.css` cascade paints the section header, the
 *  count chip, the per-row rank chip + scientific name + the
 *  optional authorship span, and the per-row hover affordance
 *  without a redesign pass (mirrors the legacy
 *  `web/detail.js::buildDetailSection("history", "Synonyms",
 *  d.synonyms.length, items)` call site byte-for-byte except
 *  for the React component boundary + the scoped `.rank-chip`
 *  selector that names the rank badge explicitly). */
export default function SynonymTab({
  status,
  onRetry,
}: SynonymTabProps): React.ReactElement {
  if (status.kind === "idle" || status.kind === "loading") {
    return (
      <div
        className="synonym-tab"
        data-tab-content="synonyms"
        data-synonym-status={status.kind}
        role="status"
        aria-busy="true"
      >
        <h3
          className="synonym-section-header"
          data-synonym-section-header=""
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[16px]"
          >
            history
          </span>
          <span>Synonyms</span>
          <span
            className="synonym-section-count"
            aria-label="0 synonyms"
          >
            0
          </span>
        </h3>
        <p className="text-body-sm text-on-surface-variant px-2 py-4 text-center">
          Loading synonyms…
        </p>
      </div>
    );
  }
  if (status.kind === "empty") {
    return (
      <div
        className="synonym-tab"
        data-tab-content="synonyms"
        data-synonym-status="empty"
        data-synonym-count="0"
        role="status"
      >
        <h3
          className="synonym-section-header"
          data-synonym-section-header=""
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[16px]"
          >
            history
          </span>
          <span>Synonyms</span>
          <span
            className="synonym-section-count"
            aria-label="0 synonyms"
          >
            0
          </span>
        </h3>
        <p className="text-body-sm text-on-surface-variant px-2 py-4 text-center">
          No synonyms available for this taxon.
        </p>
      </div>
    );
  }
  if (status.kind === "error") {
    return (
      <div
        className="synonym-tab"
        data-tab-content="synonyms"
        data-synonym-status="error"
        role="alert"
      >
        <h3
          className="synonym-section-header"
          data-synonym-section-header=""
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[16px]"
          >
            history
          </span>
          <span>Synonyms</span>
          <span
            className="synonym-section-count"
            aria-label="0 synonyms"
          >
            0
          </span>
        </h3>
        <p className="text-body-sm text-on-surface px-2 py-2 text-center">
          Could not load synonyms.
        </p>
        <p className="text-caption text-on-surface-variant px-2 pb-2 text-center">
          {status.message}
        </p>
        <div className="flex justify-center pb-2">
          <button
            type="button"
            className="rounded-md border border-outline-variant bg-surface px-3 py-1.5 text-sm font-medium text-on-surface hover:bg-surface-container-low"
            data-action="retry-synonyms"
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
      className="synonym-tab"
      data-tab-content="synonyms"
      data-synonym-status="loaded"
      data-synonym-count={String(status.names.length)}
    >
      <h3
        className="synonym-section-header"
        data-synonym-section-header=""
      >
        <span
          aria-hidden="true"
          className="material-symbols-outlined text-[16px]"
        >
          history
        </span>
        <span>Synonyms</span>
        <span
          className="synonym-section-count"
          aria-label={`${status.names.length} synonyms`}
        >
          {status.names.length}
        </span>
      </h3>
      <div
        className="synonym-list"
        data-synonym-list=""
      >
        {status.names.map((s) => (
          <div
            key={s.id}
            className="detail-item"
            data-synonym-item-id={s.id}
            data-synonym-item-rank={s.rank}
            data-synonym-item-status={s.status}
          >
            <span
              className="rank-chip"
              data-synonym-item-rank-chip=""
            >
              {s.rank}
            </span>
            <span
              className={`synonym-name ${rankClass(s.rank)}`.trim()}
              data-synonym-item-name=""
            >
              {s.scientific_name}
            </span>
            {s.authorship ? (
              <span
                className="authorship"
                data-synonym-item-authorship=""
              >
                {s.authorship}
              </span>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}