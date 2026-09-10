"use client";

// SearchLinkList — single anchor presenter (5b.4).
//
// Renders one anchor per `Engine` in `engines`. Every anchor carries
// the security contract: `target="_blank"` + `rel="noopener noreferrer"`.
// The URL template resolver (`resolveSearchLink`) replaces `{name}`
// and `{auth}` tokens; engines with `with_authorship: true` use
// `template_with_auth` when an authorship string is supplied, falling
// back to the plain `template` otherwise.
//
// Decision #4: SearchLinkList does NOT declare its own hard-coded
// engine list. The caller (SearchTab) feeds `engines` from
// `SEARCH_ENGINES` (the canonical catalog at `src/data/search-engines.js`,
// re-exported via `@taxa/research`). The SearchLinkList is the
// reusable anchor surface — it can be consumed by future app-shell
// reuse (5b.9 refactor) without a separate hard-coded catalog.

import type { ReactElement } from "react";

import type { Engine } from "@taxa/research";

export interface SearchLinkListProps {
  readonly engines: readonly Engine[];
  /** Scientific name (substitutes `{name}` in the URL template). */
  readonly name: string;
  /** Optional authorship string (substitutes `{auth}` for engines
   *  with `with_authorship: true` and a non-empty `authorship`). */
  readonly authorship?: string | null;
  /** Optional className applied to each anchor (the production
   *  `.search-link` selector rides by default; the override is for
   *  non-card contexts that reuse the presenter). */
  readonly className?: string;
}

/** Resolve a single `Engine` to the URL the anchor renders.
 *  Framework-free so the test driver can exercise it under Node. */
export function resolveSearchLink(
  engine: Engine,
  name: string,
  authorship: string | null | undefined,
): string {
  const useAuthTemplate = engine.with_authorship
    && typeof engine.template_with_auth === "string"
    && typeof authorship === "string"
    && authorship.length > 0;
  const raw = useAuthTemplate
    ? (engine.template_with_auth as string)
    : engine.template;
  return raw
    .replace("{name}", name)
    .replace("{auth}", authorship ?? "");
}

export function SearchLinkList({
  engines, name, authorship, className,
}: SearchLinkListProps): ReactElement {
  const cls = className ?? "search-link";
  return (
    <div className="search-link-list" data-search-link-list="">
      {engines.map((engine) => {
        const href = resolveSearchLink(engine, name, authorship ?? null);
        return (
          <a key={engine.key}
             className={cls}
             data-search-link={engine.key}
             data-search-category={engine.category}
             href={href}
             target="_blank"
             rel="noopener noreferrer">
            <span className="material-symbols-outlined" aria-hidden="true">
              {engine.icon}
            </span>
            <span className="search-link-label">{engine.label}</span>
          </a>
        );
      })}
    </div>
  );
}
