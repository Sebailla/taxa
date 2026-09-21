"use client";

/**
 * ExplorerErrorBoundary — component-level error boundary for the
 * Browser-tab Explorer client island (ODD-MIGRATE-003 / W6.1).
 *
 * Client component (boundary declared at the top of the file).
 * Wraps the Explorer mount so a renderer-side crash (e.g. an
 * unhandled exception inside `dispatchViewer`'s text decode or
 * an iframe load failure on a malformed URL) surfaces as a
 * recoverable `role="alert"` card with a "Try again" button
 * instead of unmounting the entire route.
 *
 * Mirrors the legacy `web/file_explorer.js::mount` catch branch:
 *  - The mount paints the placeholder via
 *    `renderPlaceholder(message, "error")` on a load failure.
 *  - The W6.1 mount paints the same shape (`role="alert"` +
 *    retry) so the React + legacy paths share the observable
 *    behavior at the boundary.
 *
 * W6.1 contract:
 *  - Component-level error state. The boundary catches errors
 *    from the wrapped tree so the user can recover without
 *    leaving the route.
 *  - Pure React class boundary (no Next 16 `<catchError>`
 *    wrapper — the React class boundary is the simpler, more
 *    portable shape and keeps the W6.1 mount framework-
 *    agnostic). A future migration to the Next 16
 *    `catchError` helper would land as a separately authorized
 *    follow-up slice.
 *
 * spec.md rule 4: presentation depends on the public barrel +
 * domain. The boundary is self-contained — no cross-module
 * imports.
 */

import { Component, type ReactNode } from "react";

/** Props for the `ExplorerErrorBoundary` component. Mirrors
 *  the React error boundary contract: children + an optional
 *  fallback. The W6.1 mount uses the inline fallback below so
 *  the consumer does not need to wire a custom one. */
export interface ExplorerErrorBoundaryProps {
  readonly children: ReactNode;
  readonly fallback?: (error: Error, retry: () => void) => ReactNode;
}

interface BoundaryState {
  readonly error: Error | null;
}

/** Classic React error boundary. `getDerivedStateFromError`
 *  flips the state to the captured error; `componentDidCatch`
 *  logs to the console so a developer can read the failure
 *  detail from the browser DevTools (mirrors the legacy
 *  `console.error("file_explorer mount failed", e)` line). */
export default class ExplorerErrorBoundary extends Component<
  ExplorerErrorBoundaryProps,
  BoundaryState
> {
  override state: BoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): BoundaryState {
    return { error };
  }

  override componentDidCatch(error: Error, info: { componentStack?: string }): void {
    // Diagnostic log — mirrors the legacy `console.error("file_explorer mount failed", e)`
    // so a developer can read the failure detail from the browser DevTools.
    // The componentStack is informational; a future iteration could
    // forward to a real error-reporting sink.
    if (typeof console !== "undefined" && typeof console.error === "function") {
      console.error("ExplorerErrorBoundary caught", error, info);
    }
  }

  retry = (): void => {
    this.setState({ error: null });
  };

  override render(): ReactNode {
    const { error } = this.state;
    const { children, fallback } = this.props;
    if (error === null) return children;
    if (fallback !== undefined) return fallback(error, this.retry);
    return (
      <div
        role="alert"
        className="fex-error-boundary p-6 text-on-surface"
        data-explorer-error-boundary=""
      >
        <p className="text-lg font-semibold">Explorer crashed</p>
        <p className="mt-2 text-body-sm text-on-surface-variant">
          {error.message || "An unexpected error occurred while rendering the explorer."}
        </p>
        <button
          type="button"
          className="fex-snippet-btn mt-4"
          onClick={this.retry}
          aria-label="Retry explorer"
        >
          Try again
        </button>
      </div>
    );
  }
}
