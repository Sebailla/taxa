// PR 3d: canonical JS mirror of api/server.py::_SEARCH_ENGINES. AC-21 contract
// test (tests/test_smoke.py::test_search_engine_contract) parses both files and
// asserts key/label/with_authorship byte-identical. `category` is consumed by
// the frontend Search tab and not asserted by AC-21. CATEGORIES drives render
// order; the renderer falls back to the engine's own icon if the category is
// missing.
export const SEARCH_ENGINES = [
  { key: "google",       label: "Google",                     template: "https://www.google.com/search?q={name}",                                                                                  template_with_auth: null,                                                                                with_authorship: false, icon: "search",         category: "general" },
  { key: "imagen",       label: "Images",                     template: "https://www.google.com/search?q={name}&tbm=isch",                                                                       template_with_auth: null,                                                                                with_authorship: false, icon: "image",          category: "multimedia" },
  { key: "documentos",   label: "Documents",                  template: "https://www.google.com/search?q={name}+%28filetype%3Adoc+OR+filetype%3Adocx+OR+filetype%3Atxt%29",                   template_with_auth: null,                                                                                with_authorship: false, icon: "description",    category: "documents" },
  { key: "pdf",          label: "PDF",                        template: "https://www.google.com/search?q={name}+filetype%3Apdf",                                                                template_with_auth: null,                                                                                with_authorship: false, icon: "picture_as_pdf", category: "documents" },
  { key: "wikipedia",    label: "Wikipedia",                  template: "https://en.wikipedia.org/wiki/Special:Search?search={name}",                                                            template_with_auth: null,                                                                                with_authorship: false, icon: "menu_book",      category: "general" },
  { key: "bhl",          label: "BHL",                        template: "https://www.biodiversitylibrary.org/search?searchTerm={name}",                                                          template_with_auth: "https://www.biodiversitylibrary.org/search?searchTerm={name}+{auth}",                  with_authorship: true,  icon: "library_books",  category: "taxonomic" },
  { key: "researchgate", label: "ResearchGate",               template: "https://www.researchgate.net/search/publication?q={name}",                                                            template_with_auth: null,                                                                                with_authorship: false, icon: "science",        category: "academic" },
  { key: "plos",         label: "PLOS",                       template: "https://journals.plos.org/plosone/search?query={name}",                                                               template_with_auth: null,                                                                                with_authorship: false, icon: "article",        category: "academic" },
  { key: "academia",     label: "Academia.edu",               template: "https://www.academia.edu/search?q={name}",                                                                            template_with_auth: null,                                                                                with_authorship: false, icon: "school",         category: "academic" },
  { key: "scielo",       label: "Scielo",                     template: "https://search.scielo.org/?q={name}",                                                                                 template_with_auth: null,                                                                                with_authorship: false, icon: "travel_explore", category: "academic" },
  { key: "scholar",      label: "Scholar",                    template: "https://scholar.google.com/scholar?q={name}",                                                                         template_with_auth: "https://scholar.google.com/scholar?q={name}+{auth}",                                     with_authorship: true,  icon: "school",         category: "academic" },
  { key: "youtube",      label: "YouTube",                    template: "https://www.youtube.com/results?search_query={name}",                                                                 template_with_auth: null,                                                                                with_authorship: false, icon: "play_circle",    category: "multimedia" },
  { key: "zootaxa",      label: "Zootaxa",                    template: "https://www.biotaxa.org/Zootaxa/search?query={name}",                                                                 template_with_auth: null,                                                                                with_authorship: false, icon: "bug_report",     category: "taxonomic" },
  { key: "scribd",       label: "Scribd",                     template: "https://www.scribd.com/search?query={name}",                                                                          template_with_auth: null,                                                                                with_authorship: false, icon: "auto_stories",   category: "documents" },
];

// PR 5c.2-A: the earlier 17-engine roster also declared three `general`
// social/share entries (`threads_acipenser`, `facebook_acipenser_baerii`,
// `threads_shared_post`) that targeted specific Acipenser queries and a
// shared-post URL — none of which fit the 5-category UI grouping pinned by
// `tests/test_search_categories.py::test_search_engines_grouped_by_category`.
// They are retired in this slice; the canonical roster is the 14 entries
// above, mirrored by `api/server.py::_SEARCH_ENGINES` and enforced by
// `tests/test_smoke.py::test_search_engine_contract`.

export const CATEGORIES = [
  { key: "general",    label: "General",    icon: "public" },
  { key: "taxonomic",  label: "Taxonomic",  icon: "biotech" },
  { key: "academic",   label: "Academic",   icon: "school" },
  { key: "multimedia", label: "Multimedia", icon: "image" },
  { key: "documents",  label: "Documents",  icon: "description" },
];