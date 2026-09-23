/**
 * `Badge` — design-system primitive for rank badges + status pills.
 *
 * Server Component. Replaces the
 * `rank-badge uppercase tracking-[0.1em] px-2 py-0.5 rounded` pattern
 * in `TreeRow` + `DetailPanel` and the inline status pill pattern in
 * the research explorer tabs.
 *
 * Variant map:
 *   - `default` — `bg-surface-container-highest text-on-surface-variant`
 *                  (the base look for muted status pills).
 *   - `primary` — `bg-primary/10 text-primary` (rank badges that
 *                  highlight a domain or taxonomic rank).
 *   - `warning` — `bg-red-50 text-red-700` (conservation / risk pills).
 *   - `subtle`  — `bg-surface text-on-surface-variant border
 *                  border-outline-variant` (chromed pill with a thin
 *                  border).
 *
 * The default class chain (`inline-flex items-center uppercase
 * tracking-[0.1em] text-[11px] font-semibold px-2 py-0.5 rounded`) is
 * the rank-badge look. Pass `uppercase={false}` to drop the uppercase
 * + tracked-Raleway treatment for non-rank badges (e.g. count pills
 * in `TreeRow.species-count-badge`).
 */
import type { HTMLAttributes, ReactNode } from "react";

export type BadgeVariant = "default" | "primary" | "warning" | "subtle";

export interface BadgeProps extends Omit<HTMLAttributes<HTMLSpanElement>, "children"> {
  variant?: BadgeVariant;
  uppercase?: boolean;
  children?: ReactNode;
}

const BASE_CLASSES = "inline-flex items-center text-[11px] font-semibold px-2 py-0.5 rounded";
const UPPERCASE_CLASSES = "uppercase tracking-[0.1em]";

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  default: "bg-surface-container-highest text-on-surface-variant",
  primary: "bg-primary/10 text-primary",
  warning: "bg-red-50 text-red-700",
  subtle: "bg-surface text-on-surface-variant border border-outline-variant",
};

export default function Badge({
  variant = "default",
  uppercase = true,
  className,
  children,
  ...rest
}: BadgeProps) {
  const tracking = uppercase ? UPPERCASE_CLASSES : "";
  const classes = `${BASE_CLASSES} ${tracking} ${VARIANT_CLASSES[variant]}${
    className ? ` ${className}` : ""
  }`.replace(/\s+/g, " ").trim();
  return (
    <span className={classes} {...rest}>
      {children}
    </span>
  );
}