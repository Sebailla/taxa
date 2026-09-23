/**
 * `IconButton` — design-system primitive for icon-only `<button>`s.
 *
 * Server Component. Replaces the `material-symbols-outlined text-[14px]
 * text-on-surface-variant hover:text-primary transition-colors` pattern
 * that appears in `TreeRow` (kebab trigger), `AppShellHeader`
 * (search/close icons), and `DetailPanel` (close affordance).
 *
 * Variant map:
 *   - `default` — `text-on-surface-variant hover:text-primary` (the
 *     default look for icon buttons that mutate the focused row).
 *   - `subtle`  — `text-on-surface-variant hover:bg-surface-container-low`
 *     (for chrome buttons like the detail-panel close affordance that
 *     only swap the background tint on hover).
 *
 * `aria-label` is REQUIRED — icon-only buttons carry no accessible
 * name from their content. The TypeScript signature enforces this;
 * runtime callers that omit it are an a11y defect.
 *
 * The default class chain (`inline-flex items-center justify-center p-1
 * rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed`)
 * is constant across every variant.
 */
import type { ButtonHTMLAttributes, ReactNode } from "react";

export type IconButtonVariant = "default" | "subtle";

export interface IconButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children" | "aria-label"> {
  variant?: IconButtonVariant;
  type?: "button" | "submit" | "reset";
  "aria-label": string;
  children?: ReactNode;
}

const BASE_CLASSES =
  "inline-flex items-center justify-center p-1 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed";

const VARIANT_CLASSES: Record<IconButtonVariant, string> = {
  default: "text-on-surface-variant hover:text-primary",
  subtle: "text-on-surface-variant hover:bg-surface-container-low",
};

export default function IconButton({
  variant = "default",
  type = "button",
  className,
  children,
  ...rest
}: IconButtonProps) {
  const classes = `${BASE_CLASSES} ${VARIANT_CLASSES[variant]}${
    className ? ` ${className}` : ""
  }`;
  return (
    <button type={type} className={classes} {...rest}>
      {children}
    </button>
  );
}