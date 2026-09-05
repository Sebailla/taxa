/**
 * Public barrel for `research` (spec.md rule 5). PR 5b.2 adds
 * `export * from "./application"`; predecessor domain/infrastructure
 * re-exports stay unchanged.
 */
export * from "./domain";
export * from "./infrastructure";
export * from "./application";
