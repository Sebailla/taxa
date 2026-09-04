// Domain barrel (5b.1) — pure types + predicates.
export type { FileFormat, ResearchFile } from "./research-file";
export { FILE_FORMATS, isValidFileFormat, isValidResearchFile } from "./research-file";
export type { Category, CategoryKey, Engine } from "./engine";
export { CATEGORY_KEYS, isValidCategory, isValidCategoryKey, isValidEngine } from "./engine";
export type { FileNode } from "./file-node";
export { FOLDER_FORMAT } from "./file-node";
