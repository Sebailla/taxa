"use client";

/**
 * `Spinner` — design-system primitive for loading affordances.
 *
 * Client Component. Uses `useEffect` to keep the `aria-live="polite"`
 * announcement region in sync with the optional `label` prop (e.g.
 * "Loading taxonomy…" when a long-running fetch begins). The default
 * label is `"Loading…"`.
 *
 * Glyph: the Material Symbols `progress_activity` glyph painted with
 * `material-symbols-outlined animate-spin`. The `animate-spin` utility
 * applies the `spin` keyframe defined in the `@layer base` block of
 * `globals.css` (the rotate-0 → rotate-360 global affordance).
 *
 * Size map:
 *   - `sm` — `text-[16px]`
 *   - `md` — `text-[20px]` (default)
 *
 * Layout: the glyph + a visually-hidden `role="status" aria-live="polite"`
 * region. The region is announced once on mount + on every `label`
 * change, giving screen-reader users a polite progress hint.
 */
import { useEffect, useState, type ReactElement } from "react";

export type SpinnerSize = "sm" | "md";

export interface SpinnerProps {
  size?: SpinnerSize;
  label?: string;
}

const BASE_CLASSES = "text-on-surface-variant animate-spin material-symbols-outlined";

const SIZE_CLASSES: Record<SpinnerSize, string> = {
  sm: "text-[16px]",
  md: "text-[20px]",
};

export default function Spinner({
  size = "md",
  label = "Loading…",
}: SpinnerProps): ReactElement {
  const [announced, setAnnounced] = useState<string>("");

  // Mirror the label into the live region on mount + whenever it
  // changes. The empty initial state ensures the region announces
  // exactly once per label change instead of re-announcing the same
  // string on every render.
  useEffect(() => {
    setAnnounced(label);
  }, [label]);

  return (
    <span className="inline-flex items-center gap-2" aria-busy="true">
      <span
        className={`${BASE_CLASSES} ${SIZE_CLASSES[size]}`}
        aria-hidden="true"
      >
        progress_activity
      </span>
      <div role="status" aria-live="polite" className="sr-only">
        {announced}
      </div>
    </span>
  );
}