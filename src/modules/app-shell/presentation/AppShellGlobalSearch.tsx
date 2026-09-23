"use client";

/**
 * AppShellGlobalSearch — the global search input that lives in
 * the AppShell header (ODD-ASN-002).
 *
 * Client island: owns the search query state by default via
 * `useState`, renders the `<input id="app-shell-search-input">`
 * element, and wires the three keyboard shortcuts the brief
 * requires:
 *
 *   - `Cmd+K` / `Ctrl+K` → focus the global search input.
 *   - `/`              → focus the global search input (skip
 *                        when the user is already focused on
 *                        another `<input>` / `<textarea>` /
 *                        `[contenteditable]` element so typing
 *                        `/` inside a text field does not steal
 *                        focus).
 *   - `Escape`         → blur the currently focused element
 *                        (so the active element loses focus)
 *                        and clear the global search query when
 *                        non-empty.
 *
 * The component supports the ODD-ASN-002 lift-state contract:
 * callers MAY pass `searchQuery` + `onSearchQueryChange` to take
 * over the state (the `AppShell` orchestrator on the main `/`
 * route uses the lifted mode so the same query flows to
 * `TaxonomyTree`'s search dropdown). When no lifted props are
 * provided the component owns the state internally — the
 * `/explorer` route relies on the internal mode because
 * `Explorer.tsx` ignores the search props for now.
 *
 * spec.md rule 4 / rule 5: this component depends only on React
 * + DOM APIs + the design-system tokens in `globals.css`. No
 * framework, no HTTP, no browser-state module — the keyboard
 * shortcuts operate on the live DOM and the lifted / internal
 * state union the brief requires.
 */
import { useCallback, useEffect, useRef, useState } from "react";

export interface AppShellGlobalSearchProps {
  /** Optional lifted search query (ODD-ASN-002 controlled mode). */
  readonly searchQuery?: string;
  /** Optional lifted search-mutator (ODD-ASN-002 controlled mode). */
  readonly onSearchQueryChange?: (next: string) => void;
}

export default function AppShellGlobalSearch(
  props: AppShellGlobalSearchProps,
): React.ReactElement {
  const liftedQuery = props.searchQuery;
  const liftedOnChange = props.onSearchQueryChange;
  // Internal-mode state (only used when `liftedQuery` is undefined
  // so React's "controlled vs uncontrolled" warning never fires).
  const [internalQuery, setInternalQuery] = useState<string>("");
  const isLifted = liftedQuery !== undefined && liftedOnChange !== undefined;
  const value = isLifted ? (liftedQuery as string) : internalQuery;
  const setValue = useCallback(
    (next: string) => {
      if (isLifted) {
        (liftedOnChange as (next: string) => void)(next);
      } else {
        setInternalQuery(next);
      }
    },
    [isLifted, liftedOnChange],
  );
  const inputRef = useRef<HTMLInputElement | null>(null);

  // ODD-ASN-002 — global keyboard listener. Three shortcuts:
  //
  //   - `Cmd+K` / `Ctrl+K` → focus the global search input.
  //   - `/` → focus the global search input (skip when the
  //     user is already focused on another `<input>` /
  //     `<textarea>` / `[contenteditable]` element so typing `/`
  //     inside a text field does not steal focus).
  //   - `Escape` → blur the currently focused element (so the
  //     active element loses focus) and clear the global search
  //     query when non-empty.
  useEffect(() => {
    const onKeyDown = (ev: KeyboardEvent): void => {
      const target = ev.target;
      const isEditable = (el: EventTarget | null): boolean => {
        if (!(el instanceof HTMLElement)) return false;
        const tag = el.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
          return true;
        }
        return el.isContentEditable;
      };
      // Cmd+K / Ctrl+K — focus the global search input. Always
      // honoured, even when another input is focused (the
      // shortcut explicitly wins over the focused element so
      // keyboard users can always reach the global search).
      if ((ev.metaKey || ev.ctrlKey) && ev.key.toLowerCase() === "k") {
        ev.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
        return;
      }
      // `/` — focus the global search input. Skipped when the
      // user is already focused on another input / textarea /
      // contenteditable element so typing `/` inside a text
      // field does not steal focus.
      if (ev.key === "/" && !ev.metaKey && !ev.ctrlKey && !ev.altKey) {
        if (!isEditable(target)) {
          ev.preventDefault();
          inputRef.current?.focus();
          inputRef.current?.select();
        }
        return;
      }
      // Escape — blur the currently focused element so the
      // active element loses focus + clear the global search
      // query when non-empty (the same Escape contract the
      // legacy `web/search.js::keydown` listener implemented).
      if (ev.key === "Escape") {
        if (document.activeElement instanceof HTMLElement) {
          document.activeElement.blur();
        }
        if (value.length > 0) {
          setValue("");
        }
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [setValue, value]);

  return (
    <div className="app-shell-global-search flex items-center">
      <label className="sr-only" htmlFor="app-shell-search-input">
        Search taxa
      </label>
      <input
        ref={inputRef}
        id="app-shell-search-input"
        type="search"
        className="app-shell-global-search-input w-full rounded-md border border-outline-variant bg-surface px-3 py-1.5 text-body-sm text-on-surface placeholder:text-on-surface-variant focus:border-primary focus:outline-none"
        placeholder="Search taxa…  (Cmd+K)"
        autoComplete="off"
        spellCheck={false}
        data-app-shell-search=""
        data-app-shell-search-value-length={value.length}
        value={value}
        onChange={(ev) => {
          setValue(ev.currentTarget.value);
        }}
      />
    </div>
  );
}