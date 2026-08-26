// Pure formatting helpers + rank-order constants. No API or tree logic
// lives here. statusDot is the only function that touches the DOM — it
// imports el() from dom.js to build the colored dot span. (The task spec
// listed format.js as "no imports", but statusDot's body is unchanged
// from the original and it constructs elements via el(), so the import
// is required to preserve behavior.)

import { el } from "./dom.js";

function rankLabel(rank) {
  return rank.charAt(0).toUpperCase() + rank.slice(1);
}

// ICZN convention: genus and below are italic; higher ranks (and any
// rank we don't recognize) are roman. Sub-ranks follow their parent
// (subgenus → italic, subfamily → roman, etc.).
const ITALIC_RANKS = new Set([
  "genus",
  "subgenus",
  "species",
  "subspecies",
  "variety",
  "form",
]);

function isItalicRank(rank) {
  return ITALIC_RANKS.has(rank);
}

// Returns the full class string for a scientific-name element. Defaults
// to italic via the base .scientific-name rule; the --roman modifier
// flips it back to roman for higher ranks. Centralizing this avoids
// repeating the conditional at every render site.
function scientificNameClass(rank) {
  return `scientific-name${isItalicRank(rank) ? "" : " scientific-name--roman"}`;
}

// Latin plurals for the few ranks that don't follow English +s.
// Most ranks pluralize the same as English; these don't.
const RANK_PLURAL = {
  domain: "domains",
  kingdom: "kingdoms",
  phylum: "phyla",
  class: "classes",
  family: "families",
  genus: "genera",
  species: "species",
  subspecies: "subspecies",
  variety: "varieties",
  // sub-ranks follow the same irregularity as their parent
  subphylum: "subphyla",
  subclass: "subclasses",
  subfamily: "subfamilies",
  subgenus: "subgenera",
  suborder: "suborders",
  subkingdom: "subkingdoms",
  subvariety: "subvarieties",
  // remaining ranks (order, tribe, etc.) fall back to English +s
};
function rankPlural(rank) {
  return RANK_PLURAL[rank] || rankLabel(rank) + "s";
}

// Map a folder's relative path to the realm that should tint it.
// The research layout is always <domain>/[kingdom]/<...> (see
// server.py::_build_segments), so segment 0 is the domain and
// segment 1 is the kingdom when the domain is Eukaryota. The strip
// on each segment drops the `id-<n>_` prefix that _sanitize_segment
// prepends when a scientific name sanitized to empty, so a folder
// like "Eukaryota/id-7_Animalia/..." still matches "animalia".
// Returns one of: "bacteria" | "archaea" | "viruses" | "animalia"
// | "fungi" | "plantae" | "chromista" | "protozoa" | "other".
// "other" covers Eukaryota without a recognized kingdom in segment 1
// (e.g. "Eukaryota/Diaphoretickes/...") and anything whose first
// segment is not one of the four known domains.
//
// Lives in format.js (not file_explorer.js) because the Classification
// tree in tree.js also needs it — both views share the same path-based
// realm encoding (Browser folder paths == taxonomic backbone paths).
function realmForFolderPath(path) {
  if (!path) return "other";
  const segments = String(path).split("/").filter(Boolean);
  if (segments.length === 0) return "other";
  const stripPrefix = (s) => s.replace(/^id-\d+_/i, "");
  const domain = stripPrefix(segments[0]).toLowerCase();
  if (domain === "bacteria") return "bacteria";
  if (domain === "archaea") return "archaea";
  if (domain === "viruses") return "viruses";
  if (domain === "eukaryota" && segments.length >= 2) {
    const kingdom = stripPrefix(segments[1]).toLowerCase();
    if (kingdom.includes("animalia")) return "animalia";
    if (kingdom.includes("fungi")) return "fungi";
    if (kingdom.includes("plantae")) return "plantae";
    if (kingdom.includes("chromista")) return "chromista";
    if (kingdom.includes("protozoa")) return "protozoa";
    return "other";
  }
  return "other";
}

function statusDot(status) {
  if (status === "accepted")
    return el("span", {
      class: "w-2 h-2 rounded-full bg-green-500",
      title: "Accepted",
    });
  if (status === "synonym")
    return el("span", {
      class: "w-2 h-2 rounded-full bg-amber-500",
      title: "Synonym",
    });
  return el("span", {
    class: "w-2 h-2 rounded-full bg-outline",
    title: "Unknown",
  });
}

function speciesCountBadge(n) {
  if (n === null || n === undefined) return "";
  if (n >= 1_000_000) {
    const m = (n / 1_000_000).toFixed(1).replace(/\.0$/, "");
    return `${m}M spp.`;
  }
  if (n >= 1_000) {
    const k = Math.round(n / 1_000);
    return `${k}k spp.`;
  }
  return `${n} spp.`;
}

const RANK_ORDER = [
  "collection",
  "domain",
  "kingdom",
  "subkingdom",
  "phylum",
  "subphylum",
  "class",
  "subclass",
  "order",
  "suborder",
  "family",
  "subfamily",
  "genus",
  "subgenus",
  "species",
  "subspecies",
  "variety",
  "form",
];
const RANK_INDEX = new Map(RANK_ORDER.map((r, i) => [r, i]));

export {
  rankLabel,
  rankPlural,
  statusDot,
  speciesCountBadge,
  isItalicRank,
  scientificNameClass,
  realmForFolderPath,
  RANK_ORDER,
  RANK_PLURAL,
  RANK_INDEX,
  ITALIC_RANKS,
};
