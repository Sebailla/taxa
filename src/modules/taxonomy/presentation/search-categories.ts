// Taxonomy presentation — search-engine category metadata bridge
// (ODD-TDS-001).
//
// The legacy frontend kept a single SEARCH_ENGINES constant that
// carried both URL definitions (mirrored into api/server.py) AND
// display-only metadata (icon, category). The server is the source
// of truth for URLs — `fetchSearches` returns `engine`, `label`,
// `url` per SearchLink. URLs are server-composed (URL-encoded at
// composition time on the server) and the client never builds a URL.
//
// The server payload carries NO category metadata, so the React port
// ships a tiny PURE bridge here that maps each engine key to its
// category (and icon for display). The bridge must:
//   - Be free of React / Next / HTTP imports (spec.md rule 4).
//   - Stay free of legacy-web dependency (ODD-TDS-001 user
//     constraint: "Do not introduce presentation→legacy-web
//     dependency").
//   - Stay free of URL definitions / query encoding — the server
//     owns URLs (ODD-TDS-001: "preserve server engine/label/url
//     values and never construct URLs client-side").
//
// The bridge carries 14 entries (the engines the legacy CATEGORIES
// taxonomy groups under 5 headers). The server additionally returns
// 3 "curated destination" links (the threads/facebook entries
// added after the 5-category split) that have no composable URL
// based on the taxon name. Those 3 are NOT mapped in
// `SEARCH_ENGINE_LIST`; the React port's SearchTab filters
// server-returned links through `searchCategoryForEngine` so the
// 3 curated destinations do NOT render in the category grouping
// (matching the legacy `test_search_categories.py` contract that
// asserts 14 buttons across 5 categories — see ODD-TDS-001
// acceptance: "enabled Search tab displays 14 server links in
// five native categories").
//
// If the server ever ships a new engine key that has no entry in
// `SEARCH_ENGINE_LIST`, `searchCategoryForEngine` returns `null`.
// The SearchTab treats unmapped keys the same way the legacy
// oracle treats them: the engine button is hidden from the visible
// grid (defense against server-side drift). The `data-tab="searches"`
// body still surfaces whatever subset is mappable so the visible
// count stays honest.

/** Canonical five-category order for the Search tab (mirrors the
 *  legacy CATEGORIES order byte-for-byte). The order here drives
 *  the rendered section order — the first category is the
 *  topmost section. Each entry maps to a header label, an icon
 *  glyph, and a stable key the SearchTab uses on
 *  `data-category="…"` so tests + a11y tooling can observe the
 *  category the user is reading. */
export interface SearchCategory {
  readonly key: SearchCategoryKey;
  readonly label: string;
  readonly icon: string;
}

/** The five canonical category keys. Re-declared as a literal set
 *  rather than a free-form string so a future caller that drifts
 *  on a typo fails at compile time. */
export type SearchCategoryKey =
  | "general"
  | "taxonomic"
  | "academic"
  | "multimedia"
  | "documents";

/** Five categories in fixed native order. Mirrors the legacy
 *  CATEGORIES order byte-for-byte so the React cutover's
 *  section order matches the legacy oracle. The
 *  `tests/test_search_categories.py` browser test asserts the
 *  exact category order in the legacy web app; the React port
 *  re-uses the same order so the same tests stay honest on the
 *  React side. */
export const SEARCH_CATEGORIES: readonly SearchCategory[] = [
  { key: "general", label: "General", icon: "public" },
  { key: "taxonomic", label: "Taxonomic", icon: "biotech" },
  { key: "academic", label: "Academic", icon: "school" },
  { key: "multimedia", label: "Multimedia", icon: "image" },
  { key: "documents", label: "Documents", icon: "description" },
];

/** Pure engine→category metadata. The `key` matches the
 *  `SearchLink.engine` field the server returns; `icon` is the
 *  material-symbols-outlined glyph used to render the link card.
 *  The list omits the 3 server-returned curated destinations
 *  (the threads/facebook entries) because they have no canonical
 *  category slot in the five-section layout — the legacy
 *  `test_search_categories.py` test pins the 5-category/14-engine
 *  contract. */
export interface SearchEngineMeta {
  readonly key: string;
  readonly icon: string;
  readonly category: SearchCategoryKey;
}

/** Pure canonical engine-list (14 entries). The order within this
 *  list mirrors the legacy SEARCH_ENGINES insertion order so the
 *  rendered button order within each category is byte-identical
 *  to the legacy oracle (search engines are listed in their
 *  source-file declaration order; categories are layered above so
 *  engines land in the order `google, wikipedia` inside the
 *  General section, `bhl, zootaxa` inside Taxonomic, etc.). */
export const SEARCH_ENGINE_LIST: readonly SearchEngineMeta[] = [
  { key: "google", icon: "search", category: "general" },
  { key: "imagen", icon: "image", category: "multimedia" },
  { key: "documentos", icon: "description", category: "documents" },
  { key: "pdf", icon: "picture_as_pdf", category: "documents" },
  { key: "wikipedia", icon: "menu_book", category: "general" },
  { key: "bhl", icon: "library_books", category: "taxonomic" },
  { key: "researchgate", icon: "science", category: "academic" },
  { key: "plos", icon: "article", category: "academic" },
  { key: "academia", icon: "school", category: "academic" },
  { key: "scielo", icon: "travel_explore", category: "academic" },
  { key: "scholar", icon: "school", category: "academic" },
  { key: "youtube", icon: "play_circle", category: "multimedia" },
  { key: "zootaxa", icon: "bug_report", category: "taxonomic" },
  { key: "scribd", icon: "auto_stories", category: "documents" },
];

/** Pre-indexed `Map<engineKey, SearchEngineMeta>` for O(1) lookups
 *  inside the SearchTab render loop. Built once on first access
 *  (lazy memoization pattern) so the cold-start cost is paid only
 *  when the Search tab actually opens. */
let _engineMetaByKeyCache: ReadonlyMap<string, SearchEngineMeta> | null = null;
function engineMetaByKey(): ReadonlyMap<string, SearchEngineMeta> {
  if (_engineMetaByKeyCache === null) {
    const m = new Map<string, SearchEngineMeta>();
    for (const e of SEARCH_ENGINE_LIST) m.set(e.key, e);
    _engineMetaByKeyCache = m;
  }
  return _engineMetaByKeyCache;
}

/** Pure lookup: return the category key for a server-returned
 *  engine key, or `null` if the engine has no canonical category
 *  slot (e.g. one of the 3 server-returned curated destinations).
 *  Used by the SearchTab to filter the server payload before
 *  rendering — engines without a mapping are silently dropped so
 *  the rendered grid stays coherent with the 5-category layout.
 *
 *  Pure: no I/O, no side effects, no module-local mutation beyond
 *  the lazy `engineMetaByKey` cache (which is content-addressed —
 *  re-builds only on first access). */
export function searchCategoryForEngine(engineKey: string): SearchCategoryKey | null {
  return engineMetaByKey().get(engineKey)?.category ?? null;
}

/** Pure lookup: return the material-symbols-outlined glyph for a
 *  server-returned engine key, or `null` if the engine has no
 *  canonical icon. SearchTab falls back to the generic `search`
 *  glyph when this returns `null` (defense against server drift).
 *
 *  Pure: same cache contract as `searchCategoryForEngine`. */
export function searchIconForEngine(engineKey: string): string | null {
  return engineMetaByKey().get(engineKey)?.icon ?? null;
}

/** Convenience: a single descriptor for a server-returned engine,
 *  or `null` if the engine has no canonical metadata. Lets the
 *  SearchTab renderer pair engine + meta in one O(1) lookup. */
export interface SearchEngineResolved {
  readonly engine: string;
  readonly category: SearchCategoryKey;
  readonly icon: string;
}

/** Pure resolver: return the canonical category + icon for a
 *  server-returned engine, or `null` when the engine is unmapped.
 *  Equivalent to two `searchCategoryForEngine` /
 *  `searchIconForEngine` calls but expressed as one helper so the
 *  SearchTab's render loop can branch on a single `null` check. */
export function resolveSearchEngineMeta(
  engineKey: string,
): SearchEngineResolved | null {
  const meta = engineMetaByKey().get(engineKey);
  if (!meta) return null;
  return { engine: meta.key, category: meta.category, icon: meta.icon };
}
