// Single source of truth for the 14 search engines (icon + label only).
// Mirrored in api/server.py::_SEARCH_ENGINES. The AC-21 contract test
// (tests/test_smoke.py::test_search_engine_contract) parses both files
// as text and asserts the keys, labels, and with_authorship flags match
// exactly. DO NOT REFORMAT this file — the test parses each entry via
// regex and a reformat will break the parse.
//
// The server is the source of truth for URLs. It composes the 14
// pre-formatted /api/taxon/{id}/searches links using
// urllib.parse.quote_plus. The frontend uses this file ONLY for icon
// and label rendering when the server response is unavailable
// (offline / 5xx fallback). The frontend never builds URLs locally,
// so there is no Python ↔ JavaScript URL-encoding parity concern.
//
// Field semantics:
//   key              — stable id (e.g. "google")
//   label            — display text (e.g. "Google")
//   template         — URL template with {name} placeholder; unused by
//                      the frontend (kept for the AC-21 contract test
//                      so server and frontend stay byte-identical on
//                      key/label/with_authorship)
//   template_with_auth — URL template with {name} and {auth}; null for
//                        engines that don't take authorship
//   with_authorship  — boolean; true iff the engine appends authorship
//   icon             — material-symbols-outlined glyph (UI rendering)
//   category         — one of the keys in CATEGORIES below; used by the
//                      frontend Search tab to group engines under a
//                      header so first-time users can tell which engines
//                      target taxonomic literature vs. general web
//                      (P1 #3 from the Impeccable critique). The
//                      server doesn't read this field.

export const SEARCH_ENGINES = [
  {
    key: "google",
    label: "Google",
    template: "https://www.google.com/search?q={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "search",
    category: "general",
  },
  {
    key: "imagen",
    label: "Images",
    template: "https://www.google.com/search?q={name}&tbm=isch",
    template_with_auth: null,
    with_authorship: false,
    icon: "image",
    category: "multimedia",
  },
  {
    key: "documentos",
    label: "Documents",
    template:
      "https://www.google.com/search?q={name}+%28filetype%3Adoc+OR+filetype%3Adocx+OR+filetype%3Atxt%29",
    template_with_auth: null,
    with_authorship: false,
    icon: "description",
    category: "documents",
  },
  {
    key: "pdf",
    label: "PDF",
    template: "https://www.google.com/search?q={name}+filetype%3Apdf",
    template_with_auth: null,
    with_authorship: false,
    icon: "picture_as_pdf",
    category: "documents",
  },
  {
    key: "wikipedia",
    label: "Wikipedia",
    template: "https://en.wikipedia.org/wiki/Special:Search?search={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "menu_book",
    category: "general",
  },
  {
    key: "bhl",
    label: "BHL",
    template: "https://www.biodiversitylibrary.org/search?searchTerm={name}",
    template_with_auth:
      "https://www.biodiversitylibrary.org/search?searchTerm={name}+{auth}",
    with_authorship: true,
    icon: "library_books",
    category: "taxonomic",
  },
  {
    key: "researchgate",
    label: "ResearchGate",
    template: "https://www.researchgate.net/search/publication?q={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "science",
    category: "academic",
  },
  {
    key: "plos",
    label: "PLOS",
    template: "https://journals.plos.org/plosone/search?query={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "article",
    category: "academic",
  },
  {
    key: "academia",
    label: "Academia.edu",
    template: "https://www.academia.edu/search?q={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "school",
    category: "academic",
  },
  {
    key: "scielo",
    label: "Scielo",
    template: "https://search.scielo.org/?q={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "travel_explore",
    category: "academic",
  },
  {
    key: "scholar",
    label: "Scholar",
    template: "https://scholar.google.com/scholar?q={name}",
    template_with_auth: "https://scholar.google.com/scholar?q={name}+{auth}",
    with_authorship: true,
    icon: "school",
    category: "academic",
  },
  {
    key: "youtube",
    label: "YouTube",
    template: "https://www.youtube.com/results?search_query={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "play_circle",
    category: "multimedia",
  },
  {
    key: "zootaxa",
    label: "Zootaxa",
    template: "https://www.biotaxa.org/Zootaxa/search?query={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "bug_report",
    category: "taxonomic",
  },
  {
    key: "scribd",
    label: "Scribd",
    template: "https://www.scribd.com/search?query={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "auto_stories",
    category: "documents",
  },
];

// Categories used to group the 14 search engines under headers in the
// Search tab (P1 #3). Order here drives render order — the first
// category is the topmost section. The `key` must match a `category`
// field on at least one entry in SEARCH_ENGINES; the renderer falls
// back to the engine's own `icon` if the category is missing.
export const CATEGORIES = [
  { key: "general", label: "General", icon: "public" },
  { key: "taxonomic", label: "Taxonomic", icon: "biotech" },
  { key: "academic", label: "Academic", icon: "school" },
  { key: "multimedia", label: "Multimedia", icon: "image" },
  { key: "documents", label: "Documents", icon: "description" },
];
