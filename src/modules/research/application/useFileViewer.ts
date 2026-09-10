"use client";

// File-viewer application surface (PR 5b.2). Pure view-model
// helpers (extension→format dispatcher, byte-size formatter) + a
// React hook adapter that owns the `loadScriptOnce` promise cache
// for CDN libraries. Mirrors taxonomy `useTaxonTree` convention.

import { useEffect, useState } from "react";

import type { FileFormat } from "../domain/research-file";
import {
  CDN_LIBRARIES,
  fetchServe,
  loadScriptOnce,
  type FetchLike,
} from "../infrastructure/api";

// ---- CDN library selection + extension dispatcher ----------------

/** CDN library names — must match keys of `CDN_URLS`. `null` means
 *  browser-native (no script tag). */
export type CdnLibrary = "mammoth" | "XLSX" | "ePub" | "Papa" | null;

export interface FormatDescriptor {
  readonly format: FileFormat;
  readonly cdnLibrary: CdnLibrary;
}

/** File descriptor accepted by `resolveViewerDescriptor`. Mirrors
 *  `ResearchFile` minus the wire fields the dispatcher does not
 *  inspect. */
export interface ViewerFile {
  readonly name: string;
  readonly path: string;
  readonly extension: string;
  readonly size: number;
  readonly format?: FileFormat;
}

/** Map an extension (case-insensitive) to format + CDN library.
 *  Mirrors the `RENDERERS` table from legacy `web/file_viewer.js`. */
export function resolveViewerDescriptor(file: ViewerFile): FormatDescriptor {
  const ext = (file.extension || "").toLowerCase();
  switch (ext) {
    case "pdf":   return { format: "pdf",  cdnLibrary: null };
    case "html":  return { format: "html", cdnLibrary: null };
    case "htm":   return { format: "html", cdnLibrary: null };
    case "txt":   return { format: "txt",  cdnLibrary: null };
    case "md":    return { format: "md",   cdnLibrary: null };
    case "docx":  return { format: "docx", cdnLibrary: "mammoth" };
    case "doc":   return { format: "doc",  cdnLibrary: null };
    case "xls":   return { format: "xls",  cdnLibrary: "XLSX" };
    case "xlsx":  return { format: "xlsx", cdnLibrary: "XLSX" };
    case "epub":  return { format: "epub", cdnLibrary: "ePub" };
    case "csv":   return { format: "csv",  cdnLibrary: "Papa" };
    case "tsv":   return { format: "tsv",  cdnLibrary: "Papa" };
    case "json":  return { format: "json", cdnLibrary: null };
    case "jpg":
    case "jpeg":
    case "png":
    case "gif":
    case "webp":
    case "bmp":
    case "svg":   return { format: "image", cdnLibrary: null };
    case "mp4":
    case "webm":
    case "ogv":   return { format: "video", cdnLibrary: null };
    default:      return { format: "unknown", cdnLibrary: null };
  }
}

// ---- Human-readable byte-size formatter ---------------------------

/** Convert a byte count to a human-readable string. Returns "?" when
 *  input is null / non-finite (matches legacy `web/file_viewer.js`). */
export function formatSize(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "?";
  if (n < 0) return "?";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

// ---- React hook adapter (CDN script cache + serve URL) ------------

export interface UseFileViewerOptions {
  readonly baseUrl: string;
  readonly taxonId: number;
  readonly file: ViewerFile | null;
  readonly srcOverride?: string;
  readonly fetchFn?: FetchLike;
}

export interface FileViewerHookState {
  readonly descriptor: FormatDescriptor | null;
  readonly serveUrl: string | null;
  readonly cdnReady: boolean;
  readonly cdnError: Error | null;
}

const CDN_LIBRARY_SET: ReadonlySet<string> = new Set(CDN_LIBRARIES);

/** React adapter — owns the CDN script-load lifecycle for 5b.3.
 *  Resolves a `ViewerFile` into a `FormatDescriptor`, kicks off
 *  `loadScriptOnce` for the matching CDN library, and exposes a
 *  `cdnReady` flag the renderer awaits. When `file` is null the hook
 *  returns a fully null state (idle — the explorer pane shows no
 *  preview). */
export function useFileViewer(
  options: UseFileViewerOptions,
): FileViewerHookState {
  const { baseUrl, taxonId, file, srcOverride } = options;
  const descriptor: FormatDescriptor | null = file
    ? resolveViewerDescriptor(file) : null;
  const cdnLibrary = descriptor?.cdnLibrary ?? null;
  const serveUrl: string | null = file
    ? fetchServe(baseUrl, taxonId, file.path) : null;
  const [cdnReady, setCdnReady] = useState<boolean>(cdnLibrary === null);
  const [cdnError, setCdnError] = useState<Error | null>(null);

  useEffect(() => {
    setCdnReady(cdnLibrary === null);
    setCdnError(null);
    if (cdnLibrary === null || !CDN_LIBRARY_SET.has(cdnLibrary)) return;
    let cancelled = false;
    void (async () => {
      try {
        await loadScriptOnce(cdnLibrary, srcOverride);
        if (cancelled) return;
        setCdnReady(true);
      } catch (cause) {
        if (cancelled) return;
        setCdnError(cause instanceof Error ? cause : new Error(String(cause)));
        setCdnReady(false);
      }
    })();
    return () => { cancelled = true; };
  }, [cdnLibrary, srcOverride]);

  return { descriptor, serveUrl, cdnReady, cdnError };
}
