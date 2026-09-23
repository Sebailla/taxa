/**
 * `EmptyState` — design-system primitive for empty / no-result affordances.
 *
 * Server Component. Replaces the `.fex-empty-state` cascade +
 * the inline `flex flex-col items-center justify-center gap-2 px-2 py-6
 * text-center text-on-surface-variant` pattern in `Explorer.tsx` and
 * `DetailPanel.tsx`.
 *
 * Size map (padding + gap):
 *   - `sm` — `p-4 gap-2`
 *   - `md` — `p-6 gap-3`
 *   - `lg` — `p-8 gap-4`
 *
 * Title typography tracks the size:
 *   - `sm` — `text-base font-semibold text-on-surface`
 *   - `md` — `text-lg font-semibold text-on-surface`
 *   - `lg` — `text-xl font-semibold text-on-surface`
 *
 * Description uses `text-sm text-on-surface-variant` regardless of size.
 *
 * Layout: `flex flex-col items-center justify-center text-center`.
 *
 * The `children` slot is for CTA buttons (or other appendable content)
 * beneath the description — the parent passes `<Button variant="primary"
 * .../>` etc.
 */
import type { ReactNode } from "react";

export type EmptyStateSize = "sm" | "md" | "lg";

export interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  size?: EmptyStateSize;
  children?: ReactNode;
}

const BASE_LAYOUT =
  "flex flex-col items-center justify-center text-center";

const SIZE_CLASSES: Record<EmptyStateSize, string> = {
  sm: "p-4 gap-2",
  md: "p-6 gap-3",
  lg: "p-8 gap-4",
};

const TITLE_CLASSES: Record<EmptyStateSize, string> = {
  sm: "text-base font-semibold text-on-surface",
  md: "text-lg font-semibold text-on-surface",
  lg: "text-xl font-semibold text-on-surface",
};

const DESCRIPTION_CLASSES = "text-sm text-on-surface-variant";

export default function EmptyState({
  icon,
  title,
  description,
  size = "md",
  children,
}: EmptyStateProps) {
  return (
    <div
      className={`${BASE_LAYOUT} ${SIZE_CLASSES[size]}`}
      role="status"
    >
      {icon}
      <p className={TITLE_CLASSES[size]}>{title}</p>
      {description ? (
        <p className={DESCRIPTION_CLASSES}>{description}</p>
      ) : null}
      {children}
    </div>
  );
}