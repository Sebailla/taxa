/**
 * `InlineMessage` — design-system primitive for inline status text
 * (info, error, success).
 *
 * Server Component. Replaces the
 * `mt-2 rounded-md border border-outline-variant bg-surface px-3 py-2
 * text-sm text-on-surface-variant` inline status pattern that appears
 * in the search tabs + the explorer.
 *
 * Variant map:
 *   - `info`    — `bg-surface-container-low border-outline-variant
 *                  text-on-surface-variant` (default look; matches the
 *      legacy `border-outline-variant` neutral inline status).
 *   - `error`   — `bg-red-50 border-red-200 text-red-700`.
 *   - `success` — `bg-green-50 border-green-200 text-green-700`.
 *
 * Default class chain (`rounded-md border px-3 py-2 text-sm`) is
 * constant across every variant — only the colour tone + border tint
 * shift per variant.
 */
import type { HTMLAttributes, ReactNode } from "react";

export type InlineMessageVariant = "info" | "error" | "success";

export interface InlineMessageProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "children"> {
  variant?: InlineMessageVariant;
  children?: ReactNode;
}

const BASE_CLASSES = "rounded-md border px-3 py-2 text-sm";

const VARIANT_CLASSES: Record<InlineMessageVariant, string> = {
  info: "bg-surface-container-low border-outline-variant text-on-surface-variant",
  error: "bg-red-50 border-red-200 text-red-700",
  success: "bg-green-50 border-green-200 text-green-700",
};

export default function InlineMessage({
  variant = "info",
  className,
  children,
  ...rest
}: InlineMessageProps) {
  const classes = `${BASE_CLASSES} ${VARIANT_CLASSES[variant]}${
    className ? ` ${className}` : ""
  }`;
  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  );
}