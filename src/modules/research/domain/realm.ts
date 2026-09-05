// Realm-mapping domain for the research module (5b.4).
//
// Pure: no React, no I/O, no DOM. The helper is the typed resolver
// the FileExplorer folder rows dispatch through (decision #1 in the
// 5b.4 brief — pure `realmForFolderPath` belongs in the research
// domain). The folder row stamps `data-realm={realmForFolderPath(path)}`
// and the resolver returns one of the eight canonical Realm literals.
//
// `Realm` mirrors the eight `--realm-*` tokens the 3c-a design system
// pinned in `globals.css` (`--realm-bacteria`, `--realm-archaea`,
// `--realm-viruses`, `--realm-animalia`, `--realm-fungi`,
// `--realm-plantae`, `--realm-chromista`, `--realm-other`).

export type Realm =
  | "bacteria" | "archaea" | "viruses" | "animalia"
  | "fungi" | "plantae" | "chromista" | "other";

export const REALMS: readonly Realm[] = [
  "bacteria", "archaea", "viruses", "animalia",
  "fungi", "plantae", "chromista", "other",
] as const;

export function isRealm(v: unknown): v is Realm {
  return typeof v === "string"
    && (REALMS as readonly string[]).includes(v);
}

/** Match a folder path or name to a Realm literal.
 *
 *  The first matching segment in `REALMS` order wins. The matcher is
 *  case-insensitive (the legacy `web/file_explorer.js::_folderRealm`
 *  resolver lowercased the haystack). Returns `"other"` when no
 *  segment matches — matches the legacy fall-through behaviour.
 *
 *  Notes:
 *    - `path` may be `""` (empty); the helper returns `"other"`.
 *    - `path` is matched as a substring; `/Animalia/foo` matches
 *      `"animalia"`, `Animals` matches `"animalia"` (case-insensitive),
 *      and `notes/Archaea-journal.md` matches `"archaea"`.
 *    - Order is significant: `REALMS` lists the seven non-`other`
 *      literals in declaration order so the first one whose substring
 *      appears wins. `other` is intentionally absent from the loop —
 *      it's the fall-through, not a candidate.
 */
export function realmForFolderPath(path: string): Realm {
  if (!path) return "other";
  const needle = path.toLowerCase();
  for (const realm of REALMS) {
    if (realm === "other") continue;
    if (needle.includes(realm)) return realm;
  }
  return "other";
}
