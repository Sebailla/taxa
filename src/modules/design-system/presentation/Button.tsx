/**
 * `Button` — design-system primitive for the three button styles the
 * app uses (primary CTA, secondary outline, ghost link) at two sizes.
 *
 * Server Component (no interactivity). Replaces the inline Tailwind
 * utility compositions in `AppShellHeader`, `TreeRow`, `DetailPanel`,
 * etc. — Phase 2 migrates the consumers; Phase 1 ships the primitive.
 *
 * Variant class maps mirror the documented contract pinned in
 * `tests/test_design_system_primitives.py::TestButton`:
 *   - `primary`   — `bg-primary text-on-primary hover:bg-accent`
 *   - `secondary` — `border border-outline-variant bg-surface
 *                    text-on-surface hover:bg-surface-container-low`
 *   - `ghost`     — `text-on-surface hover:bg-surface-container-low`
 *
 * Size map:
 *   - `sm` — `text-xs px-3 py-1.5`
 *   - `md` — `text-sm px-4 py-2`
 *
 * The default class chain (`rounded-md font-medium transition-colors
 * disabled:opacity-50 disabled:cursor-not-allowed`) is constant across
 * every variant + size.
 */
import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "sm" | "md";

export interface ButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  type?: "button" | "submit" | "reset";
  children?: ReactNode;
}

const BASE_CLASSES =
  "rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed";

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: "bg-primary text-on-primary hover:bg-accent",
  secondary:
    "border border-outline-variant bg-surface text-on-surface hover:bg-surface-container-low",
  ghost: "text-on-surface hover:bg-surface-container-low",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "text-xs px-3 py-1.5",
  md: "text-sm px-4 py-2",
};

export default function Button({
  variant = "secondary",
  size = "md",
  type = "button",
  className,
  children,
  ...rest
}: ButtonProps) {
  const classes = `${BASE_CLASSES} ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]}${
    className ? ` ${className}` : ""
  }`;
  return (
    <button type={type} className={classes} {...rest}>
      {children}
    </button>
  );
}