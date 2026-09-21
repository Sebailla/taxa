"use client";

/**
 * Explorer splitter — vertical separator + drag handle between
 * the tree pane and the viewer pane of the Browser-tab file
 * explorer (ODD-MIGRATE-003 / W6.3 of
 * `complete-frontend-migration`).
 *
 * Client Component (boundary declared at the top of the file).
 * Mirrors the legacy `web/file_explorer.js::renderSplitter()`
 * behavior byte-for-byte:
 *
 *   - Mouse drag adjusts the tree pane width in real time.
 *   - Drag state shows the `col-resize` cursor + adds the
 *     `dragging` class so the cascade paints the primary-
 *     color hover affordance (mirrors the legacy
 *     `.fex-splitter:hover, .fex-splitter.dragging` rule).
 *   - Width clamps to `MIN_TREE_WIDTH_PX` (12rem = 192px)
 *     minimum and `shellWidth - VIEWER_RESERVED_PX` (20rem
 *     = 320px) maximum. The clamp lives in the pure helper
 *     `clampTreeWidth(candidate, shellWidth)` so the focused
 *     test harness exercises it under Node without spinning
 *     up React + the DOM event system.
 *   - Mouseup persists the final tree-pane width to
 *     localStorage under the key `TREE_WIDTH_STORAGE_KEY`
 *     (= `"taxa.fex.treeWidth"`, pinned byte-for-byte against
 *     the legacy `web/file_explorer.js::TREE_WIDTH_STORAGE_KEY`).
 *   - Initial mount restores that value (and clears the
 *     legacy CSS `max-width` cap so the saved width isn't
 *     bounded by `min(60%, 50rem)`).
 *   - Double-click removes the key + clears the inline
 *     `width` + `maxWidth` so the legacy CSS default takes
 *     over again.
 *   - All localStorage failures are swallowed so the splitter
 *     still works in private-browsing / disabled-storage
 *     contexts — the only thing lost is persistence.
 *   - Accessibility: `role="separator"` + `aria-orientation="vertical"`
 *     + the legacy `title` literal
 *     `"Drag to resize · double-click to reset"`.
 *
 * The Splitter is intentionally DOM-bound (not the framework-
 * free kernel). It walks the DOM from its `parentElement`
 * (the `.fex-shell` two-pane layout) and manipulates the
 * `.fex-tree-pane` sibling via class selector, mirroring the
 * legacy `web/file_explorer.js::renderSplitter` shape
 * verbatim. The pure helpers (`clampTreeWidth`,
 * `readSavedTreeWidth`, `writeSavedTreeWidth`,
 * `clearSavedTreeWidth`) are named-exported alongside the
 * default component so the focused test harness exercises
 * them under Node without React or the DOM event system.
 *
 * spec.md rule 4 keeps presentation inward-only. The Splitter
 * imports from React (the framework), but the framework-free
 * helpers + storage key constant are reachable through the
 * same module so consumers can compose them without spinning
 * up the React event system. The public barrel
 * `src/modules/research/index.ts` re-exports the Splitter as
 * a default export so cross-module consumers (the W6.3 React
 * mount + integration tests) reach the W6.3 contract through
 * the barrel.
 *
 * The Splitter is storage-local: storage helpers only touch
 * the `TREE_WIDTH_STORAGE_KEY` localStorage key. No scope
 * creep into `@taxa/browser-state`, no domain state, no
 * settings reset, no server surface, no CDN viewers, no
 * materialization, no `web/` mutation, no `src/app/page.tsx`
 * edit, no `next-env.d.ts` edit, no
 * `odd/tasks/g4-integration-delivery.md` edit (the W6.3
 * isolation contract).
 */

import {
  useCallback,
  useEffect,
  useRef,
  type MouseEvent as ReactMouseEvent,
  type ReactNode,
} from "react";

/** localStorage key for the persisted tree-pane width.
 *  Pinned byte-for-byte against the legacy
 *  `web/file_explorer.js::TREE_WIDTH_STORAGE_KEY`. A focused
 *  test pins the literal so a future rename would be caught
 *  by the focused hermetic harness. Mirrors the legacy
 *  shape: a single global key (not namespaced into the
 *  `@taxa/browser-state` chunk) so the W6.3 splitter stays
 *  the legacy's "raw localStorage key" — the user-authorized
 *  decision documented in W6.1's tracker evidence. */
export const TREE_WIDTH_STORAGE_KEY = "taxa.fex.treeWidth";

/** Minimum tree-pane width in pixels. The legacy verbatim
 *  `12 * 16 = 192px = 12rem` shape. Kept as a `12 * 16`
 *  expression so the literal is visible at the call site
 *  (the legacy also reads `12 * 16`; the focus test asserts
 *  the expression's evaluated result is 192). */
export const MIN_TREE_WIDTH_PX = 12 * 16;

/** Reserved viewer-pane width in pixels. The legacy verbatim
 *  `20 * 16 = 320px = 20rem` shape. The splitter's upper
 *  bound is `shellWidth - VIEWER_RESERVED_PX` so the viewer
 *  always keeps at least 20rem for the meta strip + tab
 *  strip + snippet frame. */
export const VIEWER_RESERVED_PX = 20 * 16;

/** Pure helper: clamp a candidate tree-pane width against
 *  the legacy bounds. Mirrors the legacy
 *  `Math.max(MIN_WIDTH, Math.min(next, MAX_WIDTH))` shape
 *  verbatim, with one guard: the `max` is computed as
 *  `Math.max(min, shellWidth - VIEWER_RESERVED_PX)` so the
 *  splitter never returns a `max` smaller than the `min`
 *  (a too-narrow shell would otherwise produce a negative
 *  upper bound and the user could see the viewer vanish).
 *
 *  Pure function: same input always yields the same output.
 *  The component's drag handler calls this on every mousemove
 *  so a fast drag stays clamped. The helper is also reachable
 *  through the named export so the focused test harness
 *  exercises it under Node (no React, no DOM, no localStorage). */
export function clampTreeWidth(
  candidate: number,
  shellWidth: number,
): number {
  const min = MIN_TREE_WIDTH_PX;
  // The legacy reads `MAX_WIDTH = shellWidth - 20 * 16` and
  // then `Math.min(next, MAX_WIDTH)`. We mirror the same shape
  // but guard against a too-narrow shell where the viewer-
  // reserved width would exceed the shell itself (a negative
  // upper bound silently lets the user resize to "negative"
  // pixels). The `Math.max(min, …)` keeps the upper bound
  // at least equal to the lower bound so the candidate is
  // pinned to `min` in the degenerate case.
  const max = Math.max(min, shellWidth - VIEWER_RESERVED_PX);
  if (candidate < min) return min;
  if (candidate > max) return max;
  return candidate;
}

/** Pure helper: read the saved tree width from localStorage.
 *  Swallows all errors so the splitter still works in
 *  private-browsing / disabled-storage contexts — the only
 *  thing lost is persistence. Mirrors the legacy
 *  `web/file_explorer.js::readSavedTreeWidth()` shape
 *  byte-for-byte. Returns `null` when:
 *    - localStorage is undefined (SSR / Node harness).
 *    - `getItem` throws (private-browsing quota, etc.).
 *    - the key is absent.
 *
 *  Pure function (modulo localStorage I/O): same global state
 *  always yields the same return value. The component's mount
 *  effect calls this once on first render so the very first
 *  paint reflects the saved width. */
export function readSavedTreeWidth(): string | null {
  try {
    if (typeof globalThis.localStorage === "undefined") return null;
    return globalThis.localStorage.getItem(TREE_WIDTH_STORAGE_KEY);
  } catch {
    return null;
  }
}

/** Pure helper: persist the final tree-pane width to
 *  localStorage on drag end (mouseup). Swallows all errors.
 *  Mirrors the legacy
 *  `web/file_explorer.js::writeSavedTreeWidth()` shape
 *  byte-for-byte (the legacy passes `treePane.style.width`
 *  verbatim — typically a `"<n>px"` string). The W6.3 mount
 *  passes the inline `style.width` value so the stored
 *  format matches the legacy's verbatim `"<n>px"` shape.
 *
 *  Pure function (modulo localStorage I/O): no-op when
 *  localStorage is unavailable. The component's `mouseup`
 *  listener calls this with the inline `style.width` value. */
export function writeSavedTreeWidth(value: string): void {
  try {
    if (typeof globalThis.localStorage === "undefined") return;
    globalThis.localStorage.setItem(TREE_WIDTH_STORAGE_KEY, value);
  } catch {
    /* swallow — see readSavedTreeWidth */
  }
}

/** Pure helper: remove the saved tree-width key from
 *  localStorage on double-click. Swallows all errors.
 *  Mirrors the legacy
 *  `web/file_explorer.js::clearSavedTreeWidth()` shape
 *  byte-for-byte. The component's `dblclick` listener calls
 *  this so a subsequent mount falls back to the legacy CSS
 *  default.
 *
 *  Pure function (modulo localStorage I/O): no-op when
 *  localStorage is unavailable. */
export function clearSavedTreeWidth(): void {
  try {
    if (typeof globalThis.localStorage === "undefined") return;
    globalThis.localStorage.removeItem(TREE_WIDTH_STORAGE_KEY);
  } catch {
    /* swallow — see readSavedTreeWidth */
  }
}

/** Props for the Splitter client component. The Splitter is
 *  intentionally zero-prop by default — it walks the DOM
 *  from its `parentElement` (the `.fex-shell` two-pane
 *  layout) and manipulates the `.fex-tree-pane` sibling via
 *  class selector, mirroring the legacy
 *  `web/file_explorer.js::renderSplitter()` shape verbatim
 *  (the legacy uses `splitter.parentElement?.querySelector(
 *  ".fex-tree-pane")` — no prop drilling). The component is
 *  mounted by `Explorer.tsx` between the tree pane + the
 *  viewer pane. */
export interface SplitterProps {
  // No props — the splitter reads from the DOM. This keeps
  // the W6.3 surface zero-prop so the Explorer.tsx render
  // surface stays minimal (no prop wiring for the splitter).
  readonly _unused?: never;
}

/** Default-exported client component. Renders the splitter
 *  `<div>` between the tree pane + the viewer pane. The
 *  handlers attach on mount; the mount-restore effect runs
 *  once on first render and clears the cleanup ref on
 *  unmount. */
export default function Splitter(_props: SplitterProps): ReactNode {
  // ref to the rendered splitter element — the mount-restore
  // effect uses it to walk the parent shell + find the tree
  // pane via the legacy `querySelector(".fex-tree-pane")`
  // shape (the Explorer renders the two panes as siblings
  // under the `.fex-shell` flex container so the query is
  // scoped to the splitter's parent — the W6.1 mount shape).
  const splitterRef = useRef<HTMLDivElement | null>(null);
  // ref to the in-flight drag cleanup. The mousedown handler
  // attaches document-level mousemove + mouseup listeners and
  // stores the cleanup here so the unmount effect can drop
  // them if the user drags across the route's unmount (rare
  // but possible if the user navigates mid-drag). Mirrors
  // the legacy's `splitter.classList.remove("dragging")` +
  // body-style reset shape — the legacy doesn't track this
  // in a ref but the React mount needs a way to clean up on
  // unmount without restarting the drag.
  const dragCleanupRef = useRef<(() => void) | null>(null);

  // Mount-restore effect — reads the saved tree width from
  // localStorage on first render and applies it to the tree
  // pane (the Explorer renders the tree pane as a sibling of
  // the splitter under the `.fex-shell` flex container).
  // Also clears `max-width` so the saved width isn't capped
  // by the legacy CSS `max-width: min(60%, 50rem)` rule —
  // once the user has dragged, we honor their explicit choice.
  // The effect runs once on mount (empty deps) so a
  // remount-without-drag does not re-apply a stale width.
  // Mirrors the legacy `rerender()` preamble verbatim:
  //
  //   const savedWidth = readSavedTreeWidth();
  //   if (savedWidth) {
  //     treePane.style.width = savedWidth;
  //     treePane.style.maxWidth = "none";
  //   }
  useEffect(() => {
    const savedWidth = readSavedTreeWidth();
    if (!savedWidth) return;
    const splitter = splitterRef.current;
    if (!splitter) return;
    const shell = splitter.parentElement;
    const treePane = shell?.querySelector<HTMLElement>(".fex-tree-pane");
    if (!treePane) return;
    treePane.style.width = savedWidth;
    treePane.style.maxWidth = "none";
  }, []);

  // Unmount-cleanup effect — drops any in-flight drag
  // listeners so a mid-drag route change doesn't leak
  // document-level listeners. The cleanup runs on every
  // dep change (the deps are stable — `[]` — so this is
  // effectively an unmount-only cleanup).
  useEffect(() => {
    return () => {
      dragCleanupRef.current?.();
      dragCleanupRef.current = null;
    };
  }, []);

  // Memoised mousedown handler. Mirrors the legacy
  // `web/file_explorer.js::renderSplitter()` `mousedown`
  // branch verbatim:
  //
  //   1. preventDefault so the mousedown doesn't trigger
  //      text selection drag (the legacy explicitly calls
  //      this so a user accidentally clicking on a row of
  //      text inside the splitter doesn't start a text
  //      selection that fights the drag).
  //   2. Read the startX + startWidth + shellWidth so the
  //      mousemove handler computes the delta against a
  //      stable baseline (a wobbly baseline would make
  //      the drag feel laggy).
  //   3. Add `dragging` class + set `document.body.style.cursor
  //      = "col-resize"` + `user-select: none` so the drag
  //      cursor stays col-resize across the whole document
  //      (the user can drag outside the splitter's element
  //      bounding box).
  //   4. Attach document-level mousemove + mouseup so the
  //      drag follows the mouse anywhere on the page.
  //   5. Mouseup tears down the listeners + clears the body
  //      styles + persists the final `treePane.style.width`
  //      to localStorage.
  const handleMouseDown = useCallback(
    (e: ReactMouseEvent<HTMLDivElement>): void => {
      e.preventDefault();
      const splitter = splitterRef.current;
      if (!splitter) return;
      const shell = splitter.parentElement;
      const treePane = shell?.querySelector<HTMLElement>(".fex-tree-pane");
      if (!treePane || !shell) return;
      const startX = e.clientX;
      const startWidth = treePane.getBoundingClientRect().width;
      const shellWidth = shell.getBoundingClientRect().width;

      splitter.classList.add("dragging");
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";

      const onMove = (ev: MouseEvent): void => {
        const next = startWidth + (ev.clientX - startX);
        const clamped = clampTreeWidth(next, shellWidth);
        treePane.style.width = `${clamped}px`;
        // The CSS rule `max-width: min(60%, 50rem)` would
        // otherwise cap the inline width at 50rem; clearing
        // max-width lets the user pick any size within
        // [MIN_TREE_WIDTH_PX, shellWidth - VIEWER_RESERVED_PX].
        // Cleared again on dblclick (reset) below.
        treePane.style.maxWidth = "none";
      };

      const onUp = (): void => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        splitter.classList.remove("dragging");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        writeSavedTreeWidth(treePane.style.width);
        dragCleanupRef.current = null;
      };

      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      dragCleanupRef.current = () => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        splitter.classList.remove("dragging");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };
    },
    [],
  );

  // Memoised double-click handler. Mirrors the legacy
  // `web/file_explorer.js::renderSplitter()` `dblclick`
  // branch verbatim:
  //
  //   1. Clear the inline `width` + `maxWidth` so the CSS
  //      default (`width: max-content` with
  //      `max-width: min(60%, 50rem)`) takes over again.
  //   2. Remove the localStorage key so a subsequent mount
  //      falls back to the legacy CSS default.
  const handleDoubleClick = useCallback((): void => {
    const splitter = splitterRef.current;
    if (!splitter) return;
    const shell = splitter.parentElement;
    const treePane = shell?.querySelector<HTMLElement>(".fex-tree-pane");
    if (!treePane) return;
    treePane.style.width = "";
    treePane.style.maxWidth = "";
    clearSavedTreeWidth();
  }, []);

  return (
    <div
      ref={splitterRef}
      className="fex-splitter"
      role="separator"
      aria-orientation="vertical"
      title="Drag to resize · double-click to reset"
      data-explorer-splitter=""
      onMouseDown={handleMouseDown}
      onDoubleClick={handleDoubleClick}
    />
  );
}