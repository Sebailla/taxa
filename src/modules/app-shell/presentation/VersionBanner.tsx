/**
     * VersionBanner — schema-outdated banner host (PR 5c.1b-B).
     *
     * Reads `/api/health` only AFTER the `useMounted()` flag flips
     * (SSR + initial CSR render with no network call so React's
     * hydration guard never trips on a server that doesn't reach
     * the API). The banner disappears when:
     *
     *   - the response is not OK;
     *   - either schema-version field is missing or non-numeric;
     *   - the fetch throws (network error / abort / parse error);
     *   - actual >= expected (DB is current);
     *   - the user previously dismissed the banner
     *     (`store.getVersionBannerDismissed() === true`).
     *
     * A failed-closed invariant: the banner MUST NEVER fabricate an
     * outdated state — the only path to visibility is a successful
     * response with both schema-version fields typed as numbers AND
     * `actual < expected`. Dismissal persists via the typed
     * `BrowserStateStore` exposed by the AppShell context
     * (`useBrowserStateStore`); the AppShell remains the sole
     * `createBrowserStateStore()` call site in the codebase.
     *
     * The host reuses the existing `data-slot="banner-host"` slot
     * — the `hidden` attribute flips based on the same
     * fail-closed visibility logic. The three legacy DOM ids
     * (`version-banner`, `version-banner-actual`,
     * `version-banner-expected`) are preserved verbatim.
     */

    "use client";

    import { useEffect, useState, useSyncExternalStore, type ReactElement } from "react";

    import { useMounted } from "@taxa/browser-state";

    import { useBrowserStateStore } from "./browser-state-store-context";

    interface SchemaPair {
      actual: number;
      expected: number;
    }

    /**
     * Type-guard pair extraction — returns `null` for any malformed
     * payload so the banner stays hidden on bad data (the
     * fail-closed invariant).
     */
    function readSchemaPair(data: unknown): SchemaPair | null {
      if (typeof data !== "object" || data === null) return null;
      const payload = data as Record<string, unknown>;
      const dbSchemaVersion = payload["db_schema_version"];
      const expectedSchemaVersion = payload["expected_schema_version"];
      if (typeof dbSchemaVersion !== "number") return null;
      if (typeof expectedSchemaVersion !== "number") return null;
      if (!Number.isFinite(dbSchemaVersion)) return null;
      if (!Number.isFinite(expectedSchemaVersion)) return null;
      return {
        actual: dbSchemaVersion,
        expected: expectedSchemaVersion,
      };
    }

    /**
     * The component owns the host (`data-slot="banner-host"`); the
     * `hidden` attribute flips based on the fail-closed visibility
     * logic. The host stays in the DOM whether or not the banner
     * has content so the slot can be addressed by the e2e harness
     * even on a fresh DB.
     */
    export function VersionBanner(): ReactElement {
      const mounted = useMounted();
      const store = useBrowserStateStore();
      const [pair, setPair] = useState<SchemaPair | null>(null);

      // Reactive dismissal snapshot — the dismiss click calls
      // `store.setVersionBannerDismissed(true)` which notifies the same
      // store's `subscribe` listener; `useSyncExternalStore` re-reads
      // the snapshot and the banner flips off on the same render. A
      // one-shot read would leave the banner visible after dismiss
      // until the next external re-render. The subscribe / snapshot /
      // server-snapshot trio mirrors the canonical pattern used for
      // `treeSource` in `infrastructure/page-chrome.tsx`; the no-op
      // subscribe fallback covers the pre-mount window so the hook
      // call stays unconditional.
      const dismissed: boolean = useSyncExternalStore(
        store ? store.subscribe : () => () => undefined,
        () => (store ? store.getVersionBannerDismissed() : false),
        () => false,
      );

      // Mounted-gated fetch — fires only AFTER the first `useEffect`.
      // Cancellation flag prevents a slow fetch from setting state on an
      // unmounted component, mirroring React 19 strict-mode safe patterns.
      useEffect(() => {
        if (!mounted) return;
        let cancelled = false;
        fetch("/api/health")
          .then((res) => (res.ok ? res.json() : null))
          .then((data) => {
            if (cancelled) return;
            setPair(readSchemaPair(data));
          })
          .catch(() => {
            if (cancelled) return;
            // Malformed / network failures keep the banner hidden.
            setPair(null);
          });
        return () => {
          cancelled = true;
        };
      }, [mounted]);

      // Visibility derivation — every guard fails closed.
      const outdated =
        pair !== null && pair.actual < pair.expected;
      const visible = mounted && store !== null && outdated && !dismissed;

      const onDismiss = (): void => {
        if (!store) return;
        store.setVersionBannerDismissed(true);
      };

      return (
        <div role="region" aria-label="Banner host"
             data-slot="banner-host" data-banner-active={visible ? "true" : "false"}
             hidden={!visible}>
          {visible && pair !== null ? (
            <div id="version-banner" role="alert"
                 data-banner="version-outdated"
                 data-actual={pair.actual}
                 data-expected={pair.expected}>
              <span id="version-banner-actual">{pair.actual}</span>
              <span id="version-banner-expected">{pair.expected}</span>
              <button type="button" data-action="dismiss-version-banner"
                      aria-label="Dismiss version banner"
                      onClick={onDismiss}>
                Dismiss
              </button>
            </div>
          ) : null}
        </div>
      );
    }
