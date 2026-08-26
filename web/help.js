// About / Help view — mounted when the user clicks the `?` nav tab in
// the header. Mirrors the shape of the Browser tab's mount/clear pair
// (see file_explorer.js):
//
//   renderHelp(host)    — replace `host`'s children with the help shell
//   clearHelpView(host) — drop the help shell out of `host`
//
// The renderer uses el() from dom.js so every string flows through
// textContent (XSS-safe; never innerHTML). The view is read-only — no
// API calls, no event delegation beyond the anchor links.

import { el } from "./dom.js";

// ---- Small helpers -------------------------------------------------------
// Section heading pattern — <h2> uses text-h4 (14px / 600 / 1px tracking)
// which matches the existing tier-header treatment in index.html.
// Inner content goes in the second slot; the caller controls its spacing.
function sectionHeading(text) {
  return el("h2", { class: "text-h4 font-h4 text-on-surface" }, text);
}

function paragraph(text, opts = {}) {
  return el(
    "p",
    {
      class: `text-body-md${opts.muted ? " text-on-surface-variant" : ""}`,
    },
    text,
  );
}

// External link — opens in a new tab with noopener + noreferrer for safety.
function extLink(href, text) {
  return el(
    "a",
    {
      class: "text-primary hover:underline break-all",
      href,
      target: "_blank",
      rel: "noopener noreferrer",
    },
    text,
  );
}

// Bulleted list of mixed-content items. Each item can be a string OR an
// element tree (e.g. a span wrapping <strong> + text + <a>).
function bulletList(items, { muted = false } = {}) {
  return el(
    "ul",
    {
      class: `list-disc pl-6 space-y-2 text-body-md${muted ? " text-on-surface-variant" : ""}`,
    },
    ...items.map((item) => el("li", null, item)),
  );
}

// ---- Sections -------------------------------------------------------------

// Data sources bullet list — each entry is a span mixing <strong>, plain
// text, and an external link to the upstream dataset. Span is the right
// wrapper so the bullet line stays one visual row.
function dataSourceItems() {
  return [
    el(
      "span",
      null,
      el("strong", null, "CoL (Catalogue of Life, 2024 release)"),
      " — the global backbone. 5M+ species, parent chains, ranks, authorship. ",
      extLink("https://www.checklistbank.org/dataset/315777", "Source"),
    ),
    el(
      "span",
      null,
      el("strong", null, "WoRMS (World Register of Marine Species)"),
      " — marine-only overlay with its own backbone (Biota → Animalia → ... → species). ",
      extLink("https://www.marinespecies.org", "Source"),
    ),
    el(
      "span",
      null,
      el("strong", null, "Freshwater"),
      " — isolated freshwater-only subset.",
    ),
  ];
}

// ---- Public API -----------------------------------------------------------

export function renderHelp(host) {
  host.replaceChildren(
    el(
      "div",
      {
        class: "max-w-3xl mx-auto px-row-padding-x lg:px-0 py-10 space-y-8",
      },

      // About ----------------------------------------------------------
      el(
        "section",
        { class: "space-y-3" },
        el("h1", { class: "text-h1 font-h1 text-on-surface" }, "About taxa"),
        paragraph(
          "taxa is a research-grade browser for the Catalogue of Life. Drill through the full taxonomic backbone (5M+ species), search by name, and read per-taxon detail with vernacular names, synonyms, and distribution.",
        ),
      ),

      // Data sources ----------------------------------------------------
      el(
        "section",
        { class: "space-y-3" },
        sectionHeading("Data sources"),
        paragraph(
          "The Classification tree combines three independent hierarchies. Switch via the toggle above the tree:",
        ),
        bulletList(dataSourceItems()),
      ),

      // Keyboard map ----------------------------------------------------
      el(
        "section",
        { class: "space-y-3" },
        sectionHeading("Keyboard map"),
        paragraph(
          "No keyboard shortcuts wired yet. This is a future iteration; for now all actions are mouse-driven. The cookie-cutter candidates are /, Esc, ↑/↓ for tab navigation, and Ctrl+K for command palette.",
          { muted: true },
        ),
      ),

      // Attribution -----------------------------------------------------
      el(
        "section",
        { class: "space-y-3" },
        sectionHeading("Attribution"),
        bulletList([
          el(
            "span",
            null,
            el("strong", null, "Catalogue of Life"),
            ": CC-BY 4.0",
          ),
          el("span", null, el("strong", null, "WoRMS"), ": CC-BY 4.0"),
          el(
            "span",
            null,
            el("strong", null, "Freshwater endemic subset"),
            ": per source",
          ),
        ]),
      ),

      // API docs --------------------------------------------------------
      el(
        "section",
        { class: "space-y-3" },
        sectionHeading("API docs"),
        bulletList([
          el(
            "span",
            null,
            "See openapi.json at ",
            el(
              "code",
              { class: "font-mono-data px-1 bg-surface-container-low rounded" },
              "/openapi.json",
            ),
            " on the running server.",
          ),
          el(
            "span",
            null,
            "Source code: ",
            extLink(
              "https://github.com/Sebailla/taxa",
              "github.com/Sebailla/taxa",
            ),
          ),
        ]),
      ),
    ),
  );
}

// Symmetric with file_explorer.clear() — kept as a no-op so the rest of
// the app can wire it into the same lifecycle as clearFileExplorer()
// without special-casing the help tab.
export function clearHelpView(host) {
  host.replaceChildren();
}
