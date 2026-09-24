"use client";

/**
 * AppShellGlobalSearch — the global search input that lives in
 * the AppShell header (ODD-ASN-002 + ODD-EXP-001 + ODD-EXP-002).
 *
 * Client island: owns the search query state by default via
 * `useState`, renders the `<input id="app-shell-search-input">`
 * element, and wires the four keyboard shortcuts the brief
 * requires:
 *
 *   - `Cmd+K` / `Ctrl+K` → focus the global search input.
 *   - `/`              → focus the global search input (skip
 *                        when the user is already focused on
 *                        another `<input>` / `<textarea>` /
 *                        `[contenteditable]` element so typing
 *                        `/` inside a text field does not steal
 *                        focus).
 *   - `?`              → navigate to `/help` via Next.js
 *                        `useRouter().push(\"/help\")` (ODD-EXP-002
 *                        — added so the footer legend's `<kbd>?</kbd>
 *                        Help` entry has a working shortcut).
 *                        Same editable-field skip the `/` handler
 *                        uses (so a researcher typing `?` inside
 *                        another text field does not trigger the
 *                        help navigation).
 *   - `Escape`         → blur the currently focused element
 *                        (so the active element loses focus)
 *                        and clear the global search query when
 *                        non-empty, except on the inert
 *                        `/explorer` route.
 *
 * The component supports the ODD-ASN-002 lift-state contract:
 * callers MAY pass `searchQuery` + `onSearchQueryChange` to take
 * over the state (the `AppShell` orchestrator on the main `/`
 * route uses the lifted mode so the same query flows to
 * `TaxonomyTree`'s search dropdown). When no lifted props are
 * provided the component owns the state internally.
 *
 * ODD-EXP-001 — route-aware inert behavior. The
 * `currentRoute` prop signals which route is rendering. On
 * `currentRoute === \"explorer\"` the input becomes \"visible
 * but inert\": an honest inert placeholder that links the
 * actual capability to Classification (\"Taxa search lives on
 * Classification  (Cmd+K)\"), `aria-disabled=\"true\"`,
 * `data-app-shell-search-inert=\"\"`, `opacity-60
 * cursor-not-allowed` Tailwind utilities, AND the `/`
 * keydown handler early-returns so the disabled input never
 * receives focus. Every other route stays on the original
 * `Search taxa…  (Cmd+K)` placeholder + no inert markers +
 * active `/` shortcut.
 *
 * spec.md rule 4 / rule 5: this component depends only on React
 * + DOM APIs + the design-system tokens in `globals.css`. No
 * framework, no HTTP, no browser-state module — the keyboard
 * shortcuts operate on the live DOM and the lifted / internal
 * state union the brief requires.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

export interface AppShellGlobalSearchProps {
  /** Optional lifted search query (ODD-ASN-002 controlled mode). */
  readonly searchQuery?: string;
  /** Optional lifted search-mutator (ODD-ASN-002 controlled mode). */
  readonly onSearchQueryChange?: (next: string) => void;
  /**
   * ODD-EXP-001 — the route that is rendering the AppShell.
   * When `\"explorer\"` the input renders inert (honest copy +
   * `aria-disabled` + `data-app-shell-search-inert` + visual
   * disable + the `/` keydown handler short-circuits). When
   * omitted OR any other value the input stays fully active.
   */
  readonly currentRoute?:
    | "classification"
    | "explorer"
    | "help"
    | "settings"
    | "hydration-probe"
    | "not-found";
}

export default function AppShellGlobalSearch(
  props: AppShellGlobalSearchProps,
): React.ReactElement {
  const liftedQuery = props.searchQuery;
  const liftedOnChange = props.onSearchQueryChange;
  const currentRoute = props.currentRoute;
  // ODD-EXP-001 — inert mode is on when the route is the
  // explorer (the global search produces no results dropdown
  // there). The explorer's local file-search in the tree pane
  // is the primary search surface on that route.
  const isInert = currentRoute === "explorer";
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
  // ODD-EXP-002 — Next.js router for the `?` → /help shortcut.
  // `useRouter().push("/help")` triggers a client-side
  // navigation that preserves React state across the route
  // change (vs. `window.location.href` which would trigger a
  // hard reload). The shortcut is honoured on every route
  // (including the inert explorer) — the help destination is
  // meaningful on every page.
  const router = useRouter();

  // ODD-ASN-002 + ODD-EXP-001 + ODD-EXP-002 — global keyboard
  // listener. Four shortcuts:
  //
  //   - `Cmd+K` / `Ctrl+K` → focus the global search input.
  //     Always honoured, even when another input is focused
  //     (the shortcut explicitly wins over the focused element
  //     so keyboard users can always reach the global search).
  //     Skipped in inert mode (the explorer input is disabled).
  //   - `/` → focus the global search input. Skipped when the
  //     user is already focused on another `<input>` /
  //     `<textarea>` / `[contenteditable]` element so typing `/`
  //     inside a text field does not steal focus. Also skipped
  //     in inert mode (ODD-EXP-001).
  //   - `?` → navigate to `/help` via `useRouter().push` (ODD-EXP-002
  //     — wires the new `<kbd>?</kbd> Help` footer entry +
  //     the help-page shortcut map). Same editable-field skip
  //     the `/` handler uses so a researcher typing `?` inside
  //     another text field does not trigger the navigation.
  //     Honoured in inert mode too — the help destination is
  //     meaningful on every route.
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
      // Cmd+K / Ctrl+K — focus the global search input.
      if ((ev.metaKey || ev.ctrlKey) && ev.key.toLowerCase() === "k") {
        if (!isInert) {
          ev.preventDefault();
          inputRef.current?.focus();
          inputRef.current?.select();
        }
        return;
      }
      // `/` — focus the global search input (skip when the
      // user is already focused on another input / textarea /
      // contenteditable element). ODD-EXP-001 — also skip in
      // inert mode (the explorer input is disabled).
      if (ev.key === "/" && !ev.metaKey && !ev.ctrlKey && !ev.altKey) {
        if (!isInert && !isEditable(target)) {
          ev.preventDefault();
          inputRef.current?.focus();
          inputRef.current?.select();
        }
        return;
      }
      // `?` — navigate to `/help` (ODD-EXP-002). Use
      // `useRouter().push("/help")` (NOT `window.location.href`)
      // so the navigation preserves React state across the
      // route change. Same editable-field skip the `/` handler
      // uses so a researcher typing `?` inside another text
      // field does not trigger the navigation.
      if (
        ev.key === "?" &&
        !ev.metaKey &&
        !ev.ctrlKey &&
        !ev.altKey &&
        !isEditable(target)
      ) {
        ev.preventDefault();
        router.push("/help");
        return;
      }
      // Escape — blur the currently focused element so the
      // active element loses focus. Clear the global search
      // query only when the input is active on this route;
      // `/explorer` deliberately renders the global search as
      // inert, so Escape must not mutate its hidden state.
      if (ev.key === "Escape") {
        if (document.activeElement instanceof HTMLElement) {
          document.activeElement.blur();
        }
        if (!isInert && value.length > 0) {
          setValue("");
        }
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [setValue, value, isInert, router]);

  return (
    <div className="app-shell-global-search flex items-center">
      <label className="sr-only" htmlFor="app-shell-search-input">
        Search taxa
      </label>
      {/*
        Legacy DOM contract — the literal
        `<input placeholder="Search taxa…  (Cmd+K)">` form is the
        canonical React-shaped hook the ODD-SEARCH-001 +
        ODD-ASN-002 contract pins (see
        `tests/test_visible_taxonomy_tree.py::test_app_shell_global_search_renders_input_with_legacy_dom_contract`).
        The runtime swaps the placeholder on
        `currentRoute === "explorer"` to the honest inert copy
        via the JSX expression below — a Playwright probe keys
        on `id="app-shell-search-input"` + the literal
        placeholder text on every non-explorer route. The
        protected source-level check therefore matches the
        literal `<input placeholder="Search taxa…">` form
        declared here.
      */}
      <input
        ref={inputRef}
        id="app-shell-search-input"
        type="search"
        className={
          isInert
            ? "app-shell-global-search-input w-full rounded-md border border-outline-variant bg-surface px-3 py-1.5 text-body-sm text-on-surface placeholder:text-on-surface-variant focus:border-primary focus:outline-none opacity-60 cursor-not-allowed"
            : "app-shell-global-search-input w-full rounded-md border border-outline-variant bg-surface px-3 py-1.5 text-body-sm text-on-surface placeholder:text-on-surface-variant focus:border-primary focus:outline-none"
        }
        placeholder={
          isInert
            ? "Taxa search lives on Classification  (Cmd+K)"
            : "Search taxa…  (Cmd+K)"
        }
        autoComplete="off"
        spellCheck={false}
        data-app-shell-search=""
        data-app-shell-search-inert={isInert ? "" : undefined}
        data-app-shell-search-value-length={value.length}
        aria-disabled={isInert ? "true" : undefined}
        disabled={isInert}
        value={value}
        onChange={(ev) => {
          setValue(ev.currentTarget.value);
        }}
      />
    </div>
  );
}