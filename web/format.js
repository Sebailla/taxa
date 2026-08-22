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
  RANK_ORDER,
  RANK_PLURAL,
  RANK_INDEX,
};
