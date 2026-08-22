// Single source of truth for the 14 search engines. Mirrored in
// api/server.py::_SEARCH_ENGINES. The AC-21 contract test
// (tests/test_smoke.py::test_search_engine_contract_byte_identical) parses
// both files as text and asserts the keys, labels, and with_authorship
// flags match exactly. DO NOT REFORMAT this file — the test parses each
// entry via regex and a reformat will break the parse.
//
// The server is the source of truth for URLs (urllib.parse.quote_plus);
// this file is used by the frontend only for icon/label rendering when
// the server response is unavailable (offline / 5xx fallback) and as the
// contract-test fixture.
//
// Field semantics:
//   key              — stable id (e.g. "google")
//   label            — display text (e.g. "Google")
//   template         — URL with {name} placeholder (name-only queries)
//   template_with_auth — URL with {name} and {auth} placeholders; null
//                        for engines that don't take authorship
//   with_authorship  — boolean; true iff the engine appends authorship
//   icon             — material-symbols-outlined glyph (UI rendering)

export const SEARCH_ENGINES = [
  {
    key: "google",
    label: "Google",
    template: "https://www.google.com/search?q={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "search",
  },
  {
    key: "imagen",
    label: "Imágenes",
    template: "https://www.google.com/search?q={name}&tbm=isch",
    template_with_auth: null,
    with_authorship: false,
    icon: "image",
  },
  {
    key: "documentos",
    label: "Documentos",
    template:
      "https://www.google.com/search?q={name}+%28filetype%3Adoc+OR+filetype%3Adocx+OR+filetype%3Atxt%29",
    template_with_auth: null,
    with_authorship: false,
    icon: "description",
  },
  {
    key: "pdf",
    label: "PDF",
    template: "https://www.google.com/search?q={name}+filetype%3Apdf",
    template_with_auth: null,
    with_authorship: false,
    icon: "picture_as_pdf",
  },
  {
    key: "wikipedia",
    label: "Wikipedia",
    template: "https://en.wikipedia.org/wiki/Special:Search?search={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "menu_book",
  },
  {
    key: "bhl",
    label: "BHL",
    template: "https://www.biodiversitylibrary.org/search?searchTerm={name}",
    template_with_auth:
      "https://www.biodiversitylibrary.org/search?searchTerm={name}+{auth}",
    with_authorship: true,
    icon: "library_books",
  },
  {
    key: "researchgate",
    label: "ResearchGate",
    template: "https://www.researchgate.net/search/publication?q={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "science",
  },
  {
    key: "plos",
    label: "PLOS",
    template: "https://journals.plos.org/plosone/search?query={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "article",
  },
  {
    key: "academia",
    label: "Academia.edu",
    template: "https://www.academia.edu/search?q={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "school",
  },
  {
    key: "scielo",
    label: "Scielo",
    template: "https://search.scielo.org/?q={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "travel_explore",
  },
  {
    key: "scholar",
    label: "Scholar",
    template: "https://scholar.google.com/scholar?q={name}",
    template_with_auth: "https://scholar.google.com/scholar?q={name}+{auth}",
    with_authorship: true,
    icon: "school",
  },
  {
    key: "youtube",
    label: "YouTube",
    template: "https://www.youtube.com/results?search_query={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "play_circle",
  },
  {
    key: "zootaxa",
    label: "Zootaxa",
    template: "https://www.biotaxa.org/Zootaxa/search?query={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "bug_report",
  },
  {
    key: "scribd",
    label: "Scribd",
    template: "https://www.scribd.com/search?query={name}",
    template_with_auth: null,
    with_authorship: false,
    icon: "auto_stories",
  },
];

// Pure helper: build the 14 search URLs for a scientific_name + authorship.
// Mirrors api/server.py::_build_search byte-for-byte (URLs are identical for
// the same inputs because both sides use the same templates + encoding).
//
// Returns [{engine, label, url}, ...] in the same order as SEARCH_ENGINES.
export function buildSearchUrls(scientificName, authorship) {
  const nameQ = encodeURIComponent(scientificName || "");
  const authQ = authorship ? encodeURIComponent(authorship) : "";
  return SEARCH_ENGINES.map((e) => {
    let url;
    if (e.with_authorship && authQ && e.template_with_auth) {
      url = e.template_with_auth
        .replace("{name}", nameQ)
        .replace("{auth}", authQ);
    } else {
      url = e.template.replace("{name}", nameQ).replace("{auth}", "");
    }
    return { engine: e.key, label: e.label, url };
  });
}
