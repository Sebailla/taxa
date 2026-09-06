// Domain barrel (5b.1 + 5b.4). Pure types + predicates + the
// realm-mapping helper. PR 5b.4 ADDS the realm surface — never
// removes or reorders predecessors.

export type { FileFormat, ResearchFile, WireFileNode, FilesEnvelope } from "./research-file";
export { FILE_FORMATS, isValidFileFormat, isValidResearchFile, isValidFilesEnvelope } from "./research-file";
export type { Category, CategoryKey, Engine } from "./engine";
export { CATEGORY_KEYS, isValidCategory, isValidCategoryKey, isValidEngine } from "./engine";
export type { FileNode } from "./file-node";
export { FOLDER_FORMAT } from "./file-node";
export type { Realm } from "./realm";
export { REALMS, isRealm, realmForFolderPath } from "./realm";
