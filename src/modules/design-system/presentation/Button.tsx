"use client";

// Button — design-system primitive (3c-iv-barrel.4).
// Thin wrapper over native `<button>` that defaults `type="button"`
// (the native default is `type="submit"` — a top-5 React a11y footgun
// inside a `<form>`) and stamps `.fex-snippet-btn` so the existing
// `.research-explorer` rules keep matching. Native spread forwards
// `aria-label` / `data-*` / `aria-pressed`.

import type { MouseEventHandler, ReactElement, ReactNode } from "react";

export interface ButtonProps {
  readonly onClick?: MouseEventHandler<HTMLButtonElement>;
  readonly disabled?: boolean;
  readonly type?: "button" | "submit" | "reset";
  readonly className?: string;
  readonly children: ReactNode;
  readonly "aria-label"?: string;
}

const BASE_CLASS = "fex-snippet-btn";

export function Button({
  onClick,
  disabled,
  type = "button",
  className,
  children,
  ...rest
}: ButtonProps): ReactElement {
  const cls = className ? `${BASE_CLASS} ${className}` : BASE_CLASS;
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={cls} {...rest}>
      {children}
    </button>
  );
}
