// useKebab — local open/close state for the per-row kebab menu (PR 5a.4).
//
// Replaces the legacy `web/nav.js` close-on-outside-click + ESC ad-hoc
// handlers. Each row gets its own `useKebab` instance so opening one
// menu closes the others (one kebab at a time — see `toggle` below).
//
// Kept in `presentation/` rather than `application/` because the menu's
// open state is purely a DOM affordance, not part of the taxonomy
// view-model surface. Promotion to `design-system/` ships in 5b along
// with the rest of the per-row primitives.

import { useCallback, useEffect, useState } from "react";

export interface UseKebabResult {
  readonly isOpen: boolean;
  readonly open: () => void;
  readonly close: () => void;
  readonly toggle: () => void;
}

/**
 * Own the open/close state for a single per-row kebab menu.
 *
 * The hook is intentionally local-only — it does NOT coordinate
 * across rows. Cross-row coordination ("only one kebab open at a
 * time") is owned by the page-level click-outside listener in
 * `Kebab.tsx`, which closes every other instance before opening its
 * own. Keeping the cross-row coordination at the component level
 * lets `useKebab` stay pure local state that's trivial to test in
 * isolation.
 *
 * The `onEscape` handler attaches a window-level keydown listener
 * for the lifetime of the open menu and removes it on close — this
 * matches the legacy `web/nav.js` ESC-closes-menu behaviour.
 */
export function useKebab(): UseKebabResult {
  const [isOpen, setIsOpen] = useState<boolean>(false);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  useEffect(() => {
    if (!isOpen) return undefined;
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === "Escape") setIsOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen]);

  return { isOpen, open, close, toggle };
}