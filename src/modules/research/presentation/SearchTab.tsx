"use client";

// SearchTab — categorized outbound-link body (5b.4).
//
// Renders the five category sections in the canonical order
// (`General` / `Taxonomic` / `Academic` / `Multimedia` / `Documents`)
// matching the legacy `web/search_urls.js::CATEGORIES` ordering. Each
// section delegates anchor rendering to the `<SearchLinkList>`
// presenter; SearchTab owns ONLY the section layout + the canonical
// `SEARCH_ENGINES` consumption.
//
// Decision #4: SearchTab resolves links ONLY from `SEARCH_ENGINES`.
// No inline list, no local hard-codes, no fallback engines. The
// catalog lives at `src/data/search-engines.js` (Phase 3d shipped it
// for the research module's barrel) and is reached via
// `@taxa/research`.
//
// The five category sections ride the production `.search-tab` /
// `.search-category-section` / `.search-link-list` selectors the 3c-c
// `@layer components` block already declares — no new CSS.
//
// The TabStrip's data attribute contract (3c-c pinning) is preserved:
// the section / link elements carry `data-search-category` so e2e /
// screenshot harnesses can pin the section without text-matching.

import type { ReactElement } from "react";

import {
  CATEGORIES,
  SEARCH_ENGINES,
  type CategoryKey,
  type Engine,
} from "@taxa/research";

import { SearchLinkList } from "./SearchLinkList";

export interface SearchTabProps {
  /** Currently selected taxon id. `null` means the tree has no
   *  selection yet (the tab still renders the section chrome so the
   *  panel never collapses to an empty box). */
  readonly taxonId: number | null;
  /** Scientific name substituted into the URL templates. Falls back
   *  to an empty string when no taxon is selected (the anchors
   *  render with `{name}` already resolved, so no token leaks). */
  readonly name?: string;
  /** Optional authorship string — only consumed by engines whose
   *  `with_authorship: true`. Empty / null falls back to the plain
   *  template. */
  readonly authorship?: string | null;
}

const CATEGORY_ORDER: readonly CategoryKey[] = [
  "general", "taxonomic", "academic", "multimedia", "documents",
] as const;

const CATEGORY_LABEL: Record<CategoryKey, string> = {
  general: "General",
  taxonomic: "Taxonomic",
  academic: "Academic",
  multimedia: "Multimedia",
  documents: "Documents",
};

function enginesForCategory(category: CategoryKey): readonly Engine[] {
  return SEARCH_ENGINES.filter((engine) => engine.category === category);
}

export function SearchTab({
  taxonId, name, authorship,
}: SearchTabProps): ReactElement {
  const resolvedName = (name ?? "").trim();
  return (
    <div className="search-tab" data-tab-content="search"
         data-taxon-id={taxonId ?? ""}>
      {CATEGORY_ORDER.map((categoryKey) => {
        const engines = enginesForCategory(categoryKey);
        if (engines.length === 0) return null;
        const categoryMeta = CATEGORIES.find((c) => c.key === categoryKey);
        const icon = categoryMeta?.icon ?? "public";
        return (
          <section key={categoryKey}
                   className="search-category-section"
                   data-search-category={categoryKey}
                   data-search-section={categoryKey}>
            <header className="search-category-header">
              <span className="material-symbols-outlined" aria-hidden="true">
                {icon}
              </span>
              <span>{CATEGORY_LABEL[categoryKey]}</span>
            </header>
            <SearchLinkList engines={engines}
                            name={resolvedName}
                            authorship={authorship ?? null} />
          </section>
        );
      })}
    </div>
  );
}
