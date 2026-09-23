/**
 * `Text` — design-system primitive for the canonical typography
 * decisions in the app (`text-on-surface`, `text-on-surface-variant`,
 * `text-body-sm`, `font-mono-data`).
 *
 * Server Component. Centralises the small set of font-size + weight +
 * colour combinations the app actually uses, so consumers stop
 * scattering the same Tailwind utility compositions.
 *
 * Variant map:
 *   - `body`     — `text-base text-on-surface` (default body copy).
 *   - `body-sm`  — `text-sm text-on-surface` (secondary body copy,
 *                  like the detail panel authorship line).
 *   - `mono`     — `font-mono-data text-on-surface` (the file-tree
 *                  preview + JSON dumps).
 *   - `caption`  — `text-xs text-on-surface-variant` (small captions,
 *                  secondary metadata).
 *   - `label`    — `font-semibold text-on-surface` (form labels,
 *                  section headings in compact rows).
 *
 * The `as` prop selects the rendered element (`"p"` default, `"span"`,
 * `"div"`) so the same primitive can paint a paragraph, an inline run,
 * or a block container.
 */
import type { ElementType, ReactNode } from "react";

export type TextVariant = "body" | "body-sm" | "mono" | "caption" | "label";
export type TextAs = "p" | "span" | "div";

export interface TextProps {
  variant?: TextVariant;
  as?: TextAs;
  className?: string;
  children?: ReactNode;
}

const VARIANT_CLASSES: Record<TextVariant, string> = {
  body: "text-base text-on-surface",
  "body-sm": "text-sm text-on-surface",
  mono: "font-mono-data text-on-surface",
  caption: "text-xs text-on-surface-variant",
  label: "font-semibold text-on-surface",
};

export default function Text({
  variant = "body",
  as = "p",
  className,
  children,
}: TextProps) {
  const Component: ElementType = as;
  const classes = `${VARIANT_CLASSES[variant]}${className ? ` ${className}` : ""}`;
  return <Component className={classes}>{children}</Component>;
}