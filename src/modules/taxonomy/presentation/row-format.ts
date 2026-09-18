// Taxonomy presentation — per-row pure format helpers (ODD-NTP-004).
//
// Port of `web/format.js::rankLabel`, `rankPlural`, `statusDot`,
// `speciesCountBadge`, `scientificNameClass`, and
// `realmForFolderPath` into the React presentation layer. Mirrors the
// legacy oracle byte-for-byte so the React tree's per-row
// affordances (rank badge typography, italic-vs-roman scientific
// names, status dot hue, species-count formatting, realm tint, and
// the source-info / WoRMS URL helpers) stay in lock-step with the
// legacy native tree.
//
// ODD-NTP-004 — native row identity and source affordances:
//   - `rankLabel` / `isItalicRank` / `scientificNameClass` /
//     `rankPluralFor` produce the rank-badge text, the ICZN
//     italic-vs-roman split, and the tier-group header plural.
//   - `realmForPath` derives the realm tint from the CoL-baked
//     `taxon.path` (e.g. "Bacteria/X" → "bacteria",
//     "Eukaryota/Animalia/X" → "animalia"). The CSS in
//     `src/app/globals.css` stamps `[data-realm="X"] .scientific-name`
//     with the canonical realm hue, so the helper's return value
//     feeds straight into a `data-realm` attribute on the row.
//   - `statusDotDescriptor` returns the CSS class + tooltip pair for
//     the row's status dot (accepted = green, synonym = amber,
//     unknown/default = outline). The legacy `web/format.js` builds
//     a DOM element directly; the React port returns the descriptor
//     so the row component composes its own JSX.
//   - `speciesCountBadge` formats the integer species count with the
//     same `5 spp.` / `3k spp.` / `2.5M spp.` boundaries the legacy
//     oracle used (integer-rounded thousands, single-decimal
//     millions with the trailing `.0` stripped).
//   - `sourceInfoTooltip` / `wormsUrlFor` drive the per-row source
//     affordance. CoL view shows the CoL-only info glyph when the
//     taxon has `coldp_id` and no `worms_id`; WoRMS view shows the
//     WoRMS-only or cross-link info glyph whenever the taxon carries
//     `worms_id`. The kebab menu's "View on WoRMS" item mirrors the
//     same `wormsUrlFor` so the URL stays canonical across both
//     surfaces.
//
// spec.md rule 4: this file depends only on the internal domain
// (`../domain/taxon`) and on the sibling `tree-state.ts` for the
// `TreeSource` literal. No React, no Next, no HTTP, no DOM, no
// framework imports. Pure: no I/O, no async, no state mutation.

import type { Rank, Taxon } from "../domain/taxon";
import type { TreeSource } from "./tree-state";

/** Latin plurals for the few ranks that don't follow English +s.
 *  Mirrors `web/format.js::RANK_PLURAL` byte-for-byte so the React
 *  tier-header copy ("Phyla (12)", "Families (8)") matches the
 *  legacy oracle. */
const RANK_PLURAL: Partial<Record<Rank, string>> = {
  domain: "domains",
  kingdom: "kingdoms",
  phylum: "phyla",
  class: "classes",
  family: "families",
  genus: "genera",
  species: "species",
  subspecies: "subspecies",
  variety: "varieties",
  subphylum: "subphyla",
  subclass: "subclasses",
  subfamily: "subfamilies",
  subgenus: "subgenera",
  suborder: "suborders",
  subkingdom: "subkingdoms",
  subvariety: "subvarieties",
};

/** Rank badge text — first letter uppercased. Mirrors
 *  `web/format.js::rankLabel`. */
export function rankLabel(rank: Rank): string {
  return rank.charAt(0).toUpperCase() + rank.slice(1);
}

/** Tier-group header text — `RANK_PLURAL[rank]` or
 *  `rankLabel(rank) + "s"`. Mirrors `web/format.js::rankPlural`. */
export function rankPluralFor(rank: Rank): string {
  return RANK_PLURAL[rank] ?? rankLabel(rank) + "s";
}

/** ICZN convention: genus + below are italic; higher ranks (and any
 *  rank we don't recognise) are roman. Sub-ranks follow their parent
 *  (subgenus → italic, subfamily → roman, …). Mirrors
 *  `web/format.js::ITALIC_RANKS`. */
export function isItalicRank(rank: Rank): boolean {
  switch (rank) {
    case "genus":
    case "subgenus":
    case "species":
    case "subspecies":
    case "variety":
    case "subvariety":
    case "form":
      return true;
    default:
      return false;
  }
}

/** CSS class string for the row's scientific-name element. The base
 *  `.scientific-name` rule defaults to italic; the `--roman`
 *  modifier flips higher ranks back to roman. Mirrors
 *  `web/format.js::scientificNameClass`. */
export function scientificNameClass(rank: Rank): string {
  return isItalicRank(rank)
    ? "scientific-name"
    : "scientific-name scientific-name--roman";
}

/** Depth-sensitive scientific-name size + weight. Mirrors
 *  `web/tree.js::nameClassFor`:
 *    - depth === 0   → `scientific-name-depth-0` (larger, bolder;
 *      the root row identity)
 *    - depth > 0     → `scientific-name-depth-n` (smaller; descendant
 *      identity stays compact so the depth staircase reads cleanly)
 *  The CSS in `src/app/globals.css` carries the actual size/weight
 *  pair so the React port can adjust typography without touching the
 *  tree-state helpers. */
export function scientificNameDepthClass(depth: number): string {
  return depth === 0
    ? "scientific-name scientific-name-depth-0"
    : "scientific-name scientific-name-depth-n";
}

/** Map a folder-style path to the realm that should tint the row.
 *  Mirrors `web/format.js::realmForFolderPath`. The research layout
 *  is always `<domain>/[kingdom]/<...>` (see
 *  `api/server.py::_build_segments`), so segment 0 is the domain
 *  and segment 1 is the kingdom when the domain is Eukaryota. The
 *  strip on each segment drops the `id-<n>_` prefix that
 *  `_sanitize_segment` prepends when a scientific name sanitized to
 *  empty, so a folder like "Eukaryota/id-7_Animalia/..." still
 *  matches "animalia". Returns one of:
 *  `"bacteria" | "archaea" | "viruses" | "animalia" | "fungi" |
 *   "plantae" | "chromista" | "protozoa" | "other"`.
 *  `"other"` covers Eukaryota without a recognised kingdom in
 *  segment 1 (e.g. "Eukaryota/Diaphoretickes/...") and anything
 *  whose first segment is not one of the four known domains. A
 *  null / empty path also returns `"other"` (matches legacy
 * `web/format.js::realmForFolderPath`). */
export function realmForPath(path: string | null | undefined): string {
  if (!path) return "other";
  const segments = String(path).split("/").filter(Boolean);
  if (segments.length === 0) return "other";
  const stripPrefix = (s: string): string => s.replace(/^id-\d+_/i, "");
  const domain = stripPrefix(segments[0] ?? "").toLowerCase();
  if (domain === "bacteria") return "bacteria";
  if (domain === "archaea") return "archaea";
  if (domain === "viruses") return "viruses";
  if (domain === "eukaryota" && segments.length >= 2) {
    const kingdom = stripPrefix(segments[1] ?? "").toLowerCase();
    if (kingdom.includes("animalia")) return "animalia";
    if (kingdom.includes("fungi")) return "fungi";
    if (kingdom.includes("plantae")) return "plantae";
    if (kingdom.includes("chromista")) return "chromista";
    if (kingdom.includes("protozoa")) return "protozoa";
    return "other";
  }
  return "other";
}

/** Status dot descriptor. Mirrors `web/format.js::statusDot` —
 *  accepted → green, synonym → amber, anything else (including
 *  `null`) → outline grey. The descriptor returns the CSS class
 *  string + accessible tooltip pair so the row component composes
 *  its own JSX (the legacy helper builds a DOM element directly,
 *  which the React port can't reuse). */
export interface StatusDotDescriptor {
  readonly className: string;
  readonly title: string;
}

export function statusDotDescriptor(
  status: string | null | undefined,
): StatusDotDescriptor {
  if (status === "accepted") {
    return {
      className: "status-dot status-dot-accepted",
      title: "Accepted",
    };
  }
  if (status === "synonym") {
    return {
      className: "status-dot status-dot-synonym",
      title: "Synonym",
    };
  }
  return {
    className: "status-dot status-dot-unknown",
    title: "Unknown",
  };
}

/** Format the species count with the legacy boundaries:
 *  - `null` / `undefined` / 0  → "" (no badge)
 *  - 1..999                     → "{n} spp."
 *  - 1_000..999_999             → "{round(n/1000)}k spp."
 *  - ≥ 1_000_000                → "{n/1_000_000.toFixed(1)}M spp."
 *                                 with the trailing ".0" stripped.
 *  Mirrors `web/format.js::speciesCountBadge`. The renderer pairs
 *  this with a tooltip (`"X spp. under {name}"`) so users who want
 *  context can still get it without opening the detail panel. */
export function speciesCountBadge(n: number | null | undefined): string {
  if (n === null || n === undefined || n === 0) return "";
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

/** Source info affordance tooltip. Returns `null` when no tooltip
 *  applies (the row does not need the info glyph). Mirrors the
 *  legacy `web/tree.js::renderNodeRow::sourceTooltipText` branch
 *  byte-for-byte so the React port's tooltip text stays canonical.
 *
 *  - CoL view AND taxon is CoL-only (coldp_id set, worms_id NULL):
 *    "CoL-only — ColDP ID {coldp_id} (no WoRMS match)."
 *  - WoRMS view AND taxon has worms_id:
 *    - WoRMS-only (no coldp_id):
 *      "WoRMS-only — AphiaID {worms_id} (no CoL match). Open in WoRMS."
 *    - CoL + WoRMS cross-link:
 *      "WoRMS cross-link — AphiaID {worms_id}. Open in WoRMS."
 *  - Every other case: null (no icon). */
export function sourceInfoTooltip(
  taxon: Taxon,
  source: TreeSource,
): string | null {
  if (source === "col" && taxon.coldp_id && !taxon.worms_id) {
    return `CoL-only — ColDP ID ${taxon.coldp_id} (no WoRMS match).`;
  }
  if (taxon.worms_id && source !== "col") {
    const isWormsOnly = !taxon.coldp_id;
    return isWormsOnly
      ? `WoRMS-only — AphiaID ${taxon.worms_id} (no CoL match). Open in WoRMS.`
      : `WoRMS cross-link — AphiaID ${taxon.worms_id}. Open in WoRMS.`;
  }
  return null;
}

/** Build the canonical WoRMS URL for a taxon. Returns `null` when
 *  no `worms_id` is present so the kebab menu item / external link
 *  can decide to skip rendering. Mirrors the legacy
 *  `web/tree.js::sourceWormsUrl` branch. */
export function wormsUrlFor(taxon: Taxon): string | null {
  if (taxon.worms_id === null) return null;
  return `https://www.marinespecies.org/aphia.php?p=taxdetails&id=${taxon.worms_id}`;
}

/** True iff the taxon's root→taxon folder exists on disk. Mirrors
 *  the legacy `web/tree.js::hasFolder` branch. The
 *  `research_path_exists` wire field is the source of truth — the
 *  legacy state.materialized Set (populated by
 *  `propagateMaterialized`) is omitted on purpose because the React
 *  port does not yet invoke desktop / file endpoints (ODD-NTP-004
 *  explicitly defers them). The function signature takes a
 *  ReadonlySet<number> so a future caller can pass a propagated
 *  cache without changing the helper. */
export function hasMaterializedFolder(
  taxon: Taxon,
  materialized: ReadonlySet<number> = new Set<number>(),
): boolean {
  if (taxon.research_path_exists === true) return true;
  return materialized.has(taxon.id);
}