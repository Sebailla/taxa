/**
 * `Card` — design-system primitive for chromed surfaces (detail panel,
 * search results dropdown, settings tiles).
 *
 * Server Component. Replaces the
 * `.detail-panel { border: 1px solid var(--outline-variant);
 * border-radius: 16px; box-shadow: ... }` cascade in `globals.css`
 * (Phase 3 deprecates the cascade once no consumer uses it; Phase 2
 * migrates the consumers).
 *
 * Variant map:
 *   - `default`  — `bg-surface border border-outline-variant rounded-md`
 *                   (the base look for bordered cards).
 *   - `elevated` — same as `default` + a layered Tailwind arbitrary
 *                   shadow cascade that mirrors the legacy
 *                   `.detail-panel` box-shadow:
 *                     0 1px 2px  rgba(0,0,0,0.04)
 *                     0 4px 12px rgba(0,0,0,0.06)
 *                     0 12px 32px rgba(0,0,0,0.04)
 *   - `subtle`   — `bg-surface-container-low rounded-md` (no border,
 *                   used for nested surfaces where the container-low
 *                   tone carries the chroming).
 */
import type { HTMLAttributes, ReactNode } from "react";

export type CardVariant = "default" | "elevated" | "subtle";

export interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "children"> {
  variant?: CardVariant;
  children?: ReactNode;
}

const ELEVATED_SHADOW =
  "shadow-[0_1px_2px_rgba(0,0,0,0.04),0_4px_12px_rgba(0,0,0,0.06),0_12px_32px_rgba(0,0,0,0.04)]";

const VARIANT_CLASSES: Record<CardVariant, string> = {
  default: "bg-surface border border-outline-variant rounded-md",
  elevated: `bg-surface border border-outline-variant rounded-md ${ELEVATED_SHADOW}`,
  subtle: "bg-surface-container-low rounded-md",
};

export default function Card({
  variant = "default",
  className,
  children,
  ...rest
}: CardProps) {
  const classes = `${VARIANT_CLASSES[variant]}${className ? ` ${className}` : ""}`;
  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  );
}