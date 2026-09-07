"use client";

// CDN-failure banner — surface for the FileViewer when `loadScriptOnce`
// rejects. Single source of truth for the literal "Viewer offline" copy
// the legacy `web/file_viewer.js::renderOfflineBanner` painted, so a
// future app-shell reuse (PR 5b.9 refactor) lands the same wording on
// every consumer. The banner rides on the production `.fex-banner` +
// `role="status"` chrome so screen readers announce the offline state
// when it appears.

import type { ReactElement } from "react";

export interface BannersProps {
  /** When true the banner is painted; when false the component renders
   *  nothing. Keeps callers from having to short-circuit the JSX. */
  readonly show: boolean;
  /** Override the displayed filename (defaults to "this file"). */
  readonly fileName?: string;
}

export function Banners({ show, fileName }: BannersProps): ReactElement | null {
  if (!show) return null;
  const target = fileName ?? "this file";
  return (
    <div className="fex-banner" role="status">
      <span
        className="material-symbols-outlined"
        style={{ fontSize: 20 }}
        aria-hidden="true"
      >
        cloud_off
      </span>
      <span>
        {`Viewer offline \u2014 raw download available for ${target}.`}
      </span>
    </div>
  );
}
