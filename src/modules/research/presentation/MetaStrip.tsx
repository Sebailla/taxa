"use client";

// Meta strip — the file metadata chrome painted at the top of the file
// viewer pane. Reproduces the legacy
// `web/file_explorer.js::openFile` `FORMAT | SIZE | ENCODING` row, but
// extracted into a single component (PR 5b.9 refactor) so future
// consumers (e.g. app-shell reuse) reuse the same labels. SIZE is
// formatted through the application-layer `formatSize(bytes)` helper
// (5b.2) — never a local bytes-to-string copy.

import type { ReactElement } from "react";

import { formatSize } from "@taxa/research";

export interface MetaStripProps {
  /** File extension (uppercased before the `FORMAT=` literal). */
  readonly format: string;
  /** Byte count (passed through `formatSize`). */
  readonly size: number | null | undefined;
  /** Encoding label (the legacy default is UTF-8). */
  readonly encoding?: string;
}

export function MetaStrip({ format, size, encoding }: MetaStripProps): ReactElement {
  const fmt = (format || "").toUpperCase() || "?";
  const sz = formatSize(size);
  const enc = encoding ?? "UTF-8";
  return (
    <div className="fex-meta-strip" data-meta-strip="">
      <span data-meta="format">{`FORMAT=${fmt}`}</span>
      <span data-meta="size">{`SIZE=${sz}`}</span>
      <span data-meta="encoding">{`ENCODING=${enc}`}</span>
    </div>
  );
}
