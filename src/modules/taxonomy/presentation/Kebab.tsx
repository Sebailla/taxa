"use client";

// Kebab — real per-row kebab menu (PR 5a.4).
//
// Replaces the inert `KebabStub` from 5a.2 with a click-to-open menu
// that exposes the "Search online" action. The action dispatches
// `onSearchOnline(taxonId)` so the parent (`page.tsx`) can flip the
// DetailPanel's force-search prop and force the Search tab active —
// even for top-level taxa where the default would otherwise be
// Overview.
//
// Item / trigger data-actions reuse the legacy `web/nav.js` values
// (`toggle-kebab` / `open-searches`) so the existing e2e harness
// (`tests/test_search_online_force_search.py`, the screenshot corpus,
// the G3 capture script) keeps matching without new branches.
//
// Cross-row coordination ("only one kebab open at a time") is
// delegated to a single window-level click listener installed in
// `Kebab.tsx`. Each row instance owns its open/close state via
// `useKebab`; the listener closes every other instance before
// opening its own.

import type { MouseEvent, ReactElement } from "react";
import { useEffect, useRef } from "react";

import { useKebab } from "./useKebab";

export interface KebabProps {
  readonly taxonId: number;
  readonly onSearchOnline?: (taxonId: number) => void;
}

/** CSS class for the menu — matched by `@layer components` selectors
 *  in `src/app/globals.css`. Kept here so the kebab menu styling can
 *  evolve in lockstep with the component (the legacy web/ CSS lives
 *  in `web/index.html`). */
const KEbab_CLASS = "kebab";
const KEbab_MENU_CLASS = "kebab-menu";

export function Kebab({ taxonId, onSearchOnline }: KebabProps): ReactElement {
  const { isOpen, toggle, close } = useKebab();
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Click-outside: close the menu when the user clicks anywhere
  // outside the kebab container. Matches the legacy `web/nav.js`
  // close-on-outside-click behaviour.
  useEffect(() => {
    if (!isOpen) return undefined;
    const onDocClick = (e: globalThis.MouseEvent): void => {
      const target = e.target;
      if (!(target instanceof Node)) return;
      if (containerRef.current && !containerRef.current.contains(target)) {
        close();
      }
    };
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, [isOpen, close]);

  const onTriggerClick = (e: MouseEvent<HTMLButtonElement>): void => {
    e.stopPropagation();
    toggle();
  };

  const onSearchOnlineClick = (e: MouseEvent<HTMLButtonElement>): void => {
    e.stopPropagation();
    if (onSearchOnline) onSearchOnline(taxonId);
    close();
  };

  return (
    <span className={KEbab_CLASS}>
      <button type="button"
              data-action="toggle-kebab"
              data-taxon-id={taxonId}
              aria-label="Row actions"
              aria-haspopup="menu"
              aria-expanded={isOpen ? "true" : "false"}
              onClick={onTriggerClick}>
        {"\u22EF"}
      </button>
      {isOpen ? (
        <div ref={containerRef}
             className={`${KEbab_MENU_CLASS} open`}
             role="menu">
          <button type="button"
                  className="kebab-item"
                  data-action="open-searches"
                  data-taxon-id={taxonId}
                  role="menuitem"
                  onClick={onSearchOnlineClick}>
            <span className="kebab-item-label">Search online</span>
          </button>
        </div>
      ) : null}
    </span>
  );
}