"use client";

// Icon — design-system primitive (3c-iv-barrel.3).
// Thin wrapper over `<span class="material-symbols-outlined">` so the
// existing `globals.css` font + sizing rules keep matching. `IconName`
// is a frozen literal union — a typo at the call site is a compile-time
// error.

import type { ReactElement } from "react";

export type IconName =
  | "search"
  | "folder_open"
  | "folder"
  | "chevron_right"
  | "expand_more"
  | "close"
  | "settings"
  | "help"
  | "science"
  | "science_off"
  | "download";

export interface IconProps {
  readonly name: IconName;
  readonly className?: string;
      /** When supplied, the icon promotes to `role="img"`. Otherwise it
       *  is decorative (`aria-hidden="true"`). */
  readonly "aria-label"?: string;
}

const BASE_CLASS = "material-symbols-outlined";

export function Icon({ name, className, "aria-label": ariaLabel }: IconProps): ReactElement {
  const labelled = typeof ariaLabel === "string" && ariaLabel.length > 0;
  const a11y = labelled
    ? { role: "img" as const, "aria-label": ariaLabel }
    : { "aria-hidden": "true" as const };
  const cls = className ? `${BASE_CLASS} ${className}` : BASE_CLASS;
  return (
    <span className={cls} {...a11y}>
      {name}
    </span>
  );
}
