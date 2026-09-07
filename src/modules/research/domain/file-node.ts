// File-tree projection (5b.1). Pure FileNode type for the
// research module; tree construction lives elsewhere.

export const FOLDER_FORMAT = "folder";

export interface FileNode {
  readonly name: string;
  readonly path: string;
  readonly isFile: boolean;
  readonly size: number | null;
  readonly format: string;
  readonly url: string | null;
  readonly children: readonly FileNode[];
}
