/**
 * Public barrel for `research` (spec.md rule 5). PR 5b.2 adds
 * `export * from "./application"`; predecessor domain/infrastructure
 * re-exports stay unchanged. PR 5b.3 ADDS `./presentation` so the
 * FileExplorer / FileViewer shell pair is reachable via
 * `@taxa/research` (no deep imports).
 */
export * from "./domain";
export * from "./infrastructure";
export * from "./application";
export * from "./presentation";
