// Search engine record contract (5b.1). Full SEARCH_ENGINES /
// CATEGORIES arrays re-exported from infrastructure/search-engines.js;
// this file pins the typed SHAPE.

export type CategoryKey =
  | "general" | "taxonomic" | "academic" | "multimedia" | "documents";

export const CATEGORY_KEYS: readonly CategoryKey[] = [
  "general", "taxonomic", "academic", "multimedia", "documents",
] as const;

export interface Category { readonly key: CategoryKey; readonly label: string; readonly icon: string; }
export interface Engine {
  readonly key: string; readonly label: string;
  readonly template: string; readonly template_with_auth: string | null;
  readonly with_authorship: boolean; readonly icon: string;
  readonly category: CategoryKey;
}

export function isValidCategoryKey(v: unknown): v is CategoryKey {
  return typeof v === "string"
    && (CATEGORY_KEYS as readonly string[]).includes(v);
}
export function isValidCategory(v: unknown): v is Category {
  if (typeof v !== "object" || v === null) return false;
  const o = v as Record<string, unknown>;
  return isValidCategoryKey(o.key)
    && typeof o.label === "string" && o.label.length > 0
    && typeof o.icon === "string";
}
export function isValidEngine(v: unknown): v is Engine {
  if (typeof v !== "object" || v === null) return false;
  const o = v as Record<string, unknown>;
  return typeof o.key === "string" && o.key.length > 0
    && typeof o.label === "string" && o.label.length > 0
    && typeof o.template === "string"
    && (o.template_with_auth === null || typeof o.template_with_auth === "string")
    && typeof o.with_authorship === "boolean"
    && typeof o.icon === "string"
    && isValidCategoryKey(o.category);
}
