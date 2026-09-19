"use client";

/**
 * SearchTab — native DetailPanel Search tab body (ODD-TDS-001).
 *
 * Renders the server-composed search-engine links under the five
 * native category headers (General / Taxonomic / Academic /
 * Multimedia / Documents), paints loading / empty / error /
 * retry states, and emits secure external anchors
 * (`target="_blank"` + `rel="noopener noreferrer"`). The URL is
 * preserved verbatim from the server payload — the component
 * never constructs / mutates / template-fills a search URL
 * client-side (ODD-TDS-001 user constraint: "preserve server
 * engine/label/url values and never construct URLs
 * client-side").
 *
 * The component is a pure renderer: it receives a `status`
 * union (idle / loading / loaded / error / empty) + a `links`
 * array + a retry callback. The TaxonomyTree parent owns the
 * cache + the eager-fetch-on-selection contract (mirrors how
 * `perTaxonActiveTab` memory is owned upstream). Wiring the
 * fetch in the parent means the panel can mount the
 * `<SearchTab status="loaded" />` body on tab activation with
 * zero round-trip cost (the data is already in the per-taxon
 * cache by the time the user clicks the Search tab).
 *
 * Source isolation: the panel already filters through the
 * active source upstream; the Search tab does not read
 * `activeSource` directly because the server-composed URLs are
 * the same for every source (the search engines are taxon-name
 * based, not source-based).
 *
 * spec.md rule 4: presentation → taxonomy domain only. The
 * component imports the canonical `SearchLink` projection +
 * the category bridge from sibling files in the presentation
 * layer; no React / Next / HTTP / fetch / DOM token lands in
 * this file's body (defensive — the file declares
 * `"use client"` at the top because the parent TaxonomyTree
 * island needs the per-taxon hover / focus behaviour to stay
 * interactive, but the SearchTab body itself is a pure
 * JSX renderer).
 */
import { Fragment } from "react";
import type { ReactNode } from "react";
import type { SearchLink } from "../infrastructure/api";
import {
  SEARCH_CATEGORIES,
  resolveSearchEngineMeta,
} from "./search-categories";
import type { SearchCategory, SearchCategoryKey } from "./search-categories";

/** Status of the search-link fetch for the currently selected
 *  taxon. The parent (`TaxonomyTree`) owns the per-taxon cache
 *  and feeds the SearchTab one of these discriminated-union
 *  states per render. `idle` means the parent hasn't started
 *  the fetch yet (defensive — the eager-fetch-on-selection
 *  contract fires the request the moment a taxon becomes the
 *  active selection, so `idle` is rare in practice). */
export type SearchTabStatus =
  | { readonly kind: "idle" }
  | { readonly kind: "loading" }
  | { readonly kind: "loaded"; readonly links: readonly SearchLink[] }
  | { readonly kind: "empty" }
  | { readonly kind: "error"; readonly message: string };

export interface SearchTabProps {
  readonly status: SearchTabStatus;
  /** Retry callback. Fires when the user clicks the "Retry"
   *  button on the error state. The parent maps this to a
   *  re-issuance of the canonical `fetchSearches` request. */
  readonly onRetry: () => void;
}

/** Public component. Renders one of: loading spinner + copy,
 *  empty copy ("No search links available for this taxon."),
 *  error copy + Retry button, or the category grouping of the
 *  14 mappable server-returned links. The wrapper carries the
 *  canonical `.search-tab` / `.search-category-section` /
 *  `.search-link-list` / `.search-link` / `.search-category-header`
 *  classes so the existing `src/app/globals.css` cascade paints
 *  the section headers, the grid, and the link cards without a
 *  redesign pass (mirrors the legacy `web/detail.js::renderSearchesTab`
 *  byte-for-byte except for the React component boundary). */
export default function SearchTab({
  status,
  onRetry,
}: SearchTabProps): React.ReactElement {
  if (status.kind === "idle" || status.kind === "loading") {
    return (
      <div
        className="search-tab"
        data-tab-content="searches"
        data-search-status={status.kind}
        role="status"
        aria-busy="true"
      >
        <p className="text-body-sm text-on-surface-variant px-2 py-4 text-center">
          Loading search links…
        </p>
      </div>
    );
  }
  if (status.kind === "empty") {
    return (
      <div
        className="search-tab"
        data-tab-content="searches"
        data-search-status="empty"
        role="status"
      >
        <p className="text-body-sm text-on-surface-variant px-2 py-4 text-center">
          No search links available for this taxon.
        </p>
      </div>
    );
  }
  if (status.kind === "error") {
    return (
      <div
        className="search-tab"
        data-tab-content="searches"
        data-search-status="error"
        role="alert"
      >
        <p className="text-body-sm text-on-surface px-2 py-2 text-center">
          Could not load search links.
        </p>
        <p className="text-caption text-on-surface-variant px-2 pb-3 text-center">
          {status.message}
        </p>
        <div className="flex justify-center pb-2">
          <button
            type="button"
            className="rounded-md border border-outline-variant bg-surface px-3 py-1.5 text-sm font-medium text-on-surface hover:bg-surface-container-low"
            data-action="retry-searches"
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
      className="search-tab"
      data-tab-content="searches"
      data-search-status="loaded"
      data-search-link-count={String(status.links.length)}
    >
      {renderSections(status.links)}
    </div>
  );
}

/** Group the server-returned `SearchLink[]` payload by category
 *  using the pure `resolveSearchEngineMeta` bridge. Engines the
 *  server returned but the bridge has no category for (the 3
 *  curated destinations — `threads_acipenser`,
 *  `facebook_acipenser_baerii`, `threads_shared_post`) are
 *  silently dropped, matching the legacy
 *  `test_search_categories.py` 5-category / 14-engine contract.
 *  Section order follows `SEARCH_CATEGORIES` byte-for-byte so
 *  the rendered headers land in the same native order the
 *  legacy oracle renders. Within a section, engines keep the
 *  server's response order so the wire payload drives the
 *  intra-section button order (the legacy oracle mirrors this
 *  by iterating `SEARCH_ENGINES` in source-file order and
 *  picking the matching `SearchLink` for each entry). */
function renderSections(links: readonly SearchLink[]): ReactNode {
  const grouped = groupLinksByCategory(links);
  return (
    <>
      {SEARCH_CATEGORIES.map((cat) => {
        const sectionLinks = grouped.get(cat.key) ?? [];
        if (sectionLinks.length === 0) return null;
        return renderSection(cat, sectionLinks);
      })}
    </>
  );
}

interface GroupedLink {
  readonly engine: string;
  readonly link: SearchLink;
}

function groupLinksByCategory(
  links: readonly SearchLink[],
): ReadonlyMap<SearchCategoryKey, readonly GroupedLink[]> {
  const out = new Map<SearchCategoryKey, GroupedLink[]>();
  for (const link of links) {
    const meta = resolveSearchEngineMeta(link.engine);
    if (!meta) continue; // unmapped engine (curated destination) — drop
    const bucket = out.get(meta.category);
    const entry: GroupedLink = { engine: link.engine, link };
    if (bucket) bucket.push(entry);
    else out.set(meta.category, [entry]);
  }
  return out;
}

function renderSection(
  cat: SearchCategory,
  sectionLinks: readonly GroupedLink[],
): ReactNode {
  return (
    <section
      key={cat.key}
      className="search-category-section"
      data-search-category-section={cat.key}
    >
      <h3
        className="search-category-header"
        data-category={cat.key}
      >
        <span
          aria-hidden="true"
          className="material-symbols-outlined text-[14px]"
        >
          {cat.icon}
        </span>
        <span>{cat.label}</span>
      </h3>
      <div
        className="search-link-list"
        data-search-link-list={cat.key}
      >
        {sectionLinks.map(({ engine, link }) => (
          <Fragment key={engine}>
            {renderLink(engine, link, cat.key)}
          </Fragment>
        ))}
      </div>
    </section>
  );
}

/** Render one secure anchor. The URL is the wire value verbatim;
 *  the icon glyph comes from the pure category bridge; the label
 *  comes from the server payload (so a future server-side label
 *  change flows through without a coordinated client update).
 *  The anchor carries `target="_blank"` + `rel="noopener
 *  noreferrer"` so the new tab can't reach back into the parent
 *  window's `window.opener` reference and the absence of
 *  `noreferrer` would let the destination see the referer. The
 *  link ALSO carries `data-engine-key` + `data-category` so the
 *  legacy selector + the parity test (which counts via
 *  `[data-engine-key]`) keep working without a redesign pass. */
function renderLink(
  engine: string,
  link: SearchLink,
  category: SearchCategoryKey,
): ReactNode {
  const meta = resolveSearchEngineMeta(engine);
  const icon = meta?.icon ?? "search";
  return (
    <a
      key={engine}
      className="search-link shadow-sm"
      href={link.url}
      target="_blank"
      rel="noopener noreferrer"
      data-engine-key={engine}
      data-category={category}
      title={`Open ${link.label} search for this taxon in a new tab`}
    >
      <span
        aria-hidden="true"
        className="material-symbols-outlined text-[20px]"
      >
        {icon}
      </span>
      <span>{link.label}</span>
    </a>
  );
}
