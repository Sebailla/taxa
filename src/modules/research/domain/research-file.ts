// Research file descriptor types (5b.1). Pure: no fetch, no React.

export type FileFormat =
  | "pdf" | "epub" | "html" | "md" | "txt" | "doc" | "docx"
  | "xls" | "xlsx" | "csv" | "tsv" | "json" | "image" | "video"
  | "unknown";

export const FILE_FORMATS: readonly FileFormat[] = [
  "pdf", "epub", "html", "md", "txt",
  "doc", "docx", "xls", "xlsx",
  "csv", "tsv", "json", "image", "video", "unknown",
] as const;

export function isValidFileFormat(value: unknown): value is FileFormat {
  return typeof value === "string"
    && (FILE_FORMATS as readonly string[]).includes(value);
}

/** Per-file descriptor (domain projection). Wire file children use `WireFileNode`. */
export interface ResearchFile {
  readonly name: string;
  readonly path: string;
  readonly extension: string;
  readonly size: number;
  readonly format: FileFormat;
  readonly url: string;
  readonly modified: string | null;
}

export function isValidResearchFile(value: unknown): value is ResearchFile {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return typeof v.name === "string" && v.name.length > 0
    && typeof v.path === "string" && typeof v.extension === "string"
    && typeof v.size === "number" && Number.isFinite(v.size) && v.size >= 0
    && isValidFileFormat(v.format) && typeof v.url === "string"
    && (v.modified === null || typeof v.modified === "string");
}

// 5b.1 addendum — wire envelope for `GET /api/taxon/{id}/files`.
// Mirrors `api/server.py::_walk_tree` plus
// `{exists, taxon_id, taxon_name, taxon_path, filesystem_path, subpath, root}`.
export type WireFileNode =
  | { type: "folder"; name: string; path: string; children: readonly WireFileNode[] }
  | { type: "file"; name: string; path: string; extension: string; size: number; modified: string };
export interface FilesEnvelope {
  exists: boolean; taxon_id: number; taxon_name: string;
  taxon_path: string; filesystem_path: string;
  subpath: string | null; root: WireFileNode | null;
}
function isWireFileNode(v: unknown): v is WireFileNode {
  const o = v as Record<string, unknown> | null;
  if (!o || typeof o.name !== "string" || typeof o.path !== "string") return false;
  if (o.type === "folder") return Array.isArray(o.children) && o.children.every(isWireFileNode);
  if (o.type === "file") return typeof o.extension === "string"
    && typeof o.size === "number" && Number.isFinite(o.size) && o.size >= 0
    && typeof o.modified === "string";
  return false;
}
export function isValidFilesEnvelope(v: unknown): v is FilesEnvelope {
  const o = v as Record<string, unknown> | null;
  if (!o) return false;
  return typeof o.exists === "boolean" && typeof o.taxon_id === "number"
    && typeof o.taxon_name === "string" && typeof o.taxon_path === "string"
    && typeof o.filesystem_path === "string"
    && (o.subpath === null || typeof o.subpath === "string")
    && (o.root === null || isWireFileNode(o.root));
}