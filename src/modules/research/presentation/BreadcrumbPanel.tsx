"use client";

// BreadcrumbPanel — the research-path breadcrumb painted above the
// file explorer. One segment per folder the explorer has drilled into,
// each carrying `data-folder-path` so the parent can re-mount
// selection on click without rebuilding the chain. The component is a
// `<nav>` landmark with an `aria-label="Research path"` so screen
// readers announce the trail (WCAG 2.2 AA).

import type { ReactElement } from "react";

export interface BreadcrumbSegment {
  /** Display label (folder basename). */
  readonly label: string;
  /** Absolute path used by the explorer to select the folder. */
  readonly path: string;
}

export interface BreadcrumbPanelProps {
  /** Folder chain in display order (root first, leaf last). Empty
   *  array renders the empty-state landmark. */
  readonly segments: readonly BreadcrumbSegment[];
  /** Called when the user clicks a segment. */
  readonly onSelect: (path: string) => void;
}

export function BreadcrumbPanel({
  segments, onSelect,
}: BreadcrumbPanelProps): ReactElement {
  if (segments.length === 0) {
    return (
      <nav
        className="breadcrumb"
        aria-label="Research path"
        data-breadcrumb-empty=""
      />
    );
  }
  return (
    <nav
      className="breadcrumb"
      aria-label="Research path"
      data-breadcrumb=""
    >
      {segments.map((segment, index) => (
        <span key={segment.path} className="breadcrumb-segment">
          <button
            type="button"
            className="breadcrumb-link"
            data-folder-path={segment.path}
            onClick={() => onSelect(segment.path)}
          >
            <span className="authorship">{segment.label}</span>
          </button>
          {index < segments.length - 1
            ? <span className="authorship" aria-hidden="true">{">"}</span>
            : null}
        </span>
      ))}
    </nav>
  );
}
