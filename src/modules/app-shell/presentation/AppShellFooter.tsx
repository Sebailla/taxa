/**
 * AppShellFooter — the ODD-ASN-002 footer row.
 *
 * Server component (no `"use client"`): the three-column footer
 * is fully static (the brand mark + the static-export marker +
 * the keyboard-shortcut legend + the API origin / schema
 * version). No client-side concern lives here.
 *
 * ODD-EXP-002 — shortcut legend contract. The legend pairs the
 * four keyboard shortcuts with the action they trigger:
 *
 *   - `Cmd+K` → Search (focus the global search input).
 *   - `/`     → Search (same effect, alternate shortcut).
 *   - `?`     → Help (navigate to `/help` via
 *               `useRouter().push("/help")`).
 *   - `Esc`   → Close (blur the active element + clear the
 *               search query when non-empty).
 *
 * The `/` and `?` clusters are kept distinct — the pre-ODD-EXP-002
 * legend conflated them as `<kbd>/</kbd> Help` (the P0 the
 * re-critique identified). The current legend reads
 * `Cmd+K Search · / Search · ? Help · Esc Close` so the two
 * shortcuts are unambiguously separate.
 *
 * spec.md rule 4 / rule 5: this component depends only on React
 * + the design-system tokens in `globals.css`. No framework, no
 * HTTP, no browser-state.
 */
export interface AppShellFooterProps {
  /** API origin / schema version (right column). */
  readonly apiOrigin: string;
  /** Schema version literal (right column, defaults to
   *  `1` so the static export carries a deterministic value
   *  when the FastAPI `/api/health` is unavailable). */
  readonly schemaVersion?: string;
}

export default function AppShellFooter(
  props: AppShellFooterProps,
): React.ReactElement {
  const schemaVersion = props.schemaVersion ?? "1";
  return (
    <footer
      className="app-shell-footer border-t border-outline-variant bg-surface text-on-surface-variant"
      data-app-shell-footer=""
      role="contentinfo"
    >
      <div className="mx-auto grid w-full max-w-none grid-cols-3 items-center gap-4 px-6 py-3 text-xs">
        <div
          className="app-shell-footer-col app-shell-footer-col--left flex items-center gap-2"
          data-app-shell-footer-col="left"
        >
          <span className="app-shell-footer-brand font-semibold tracking-tight text-on-surface">
            taxa
          </span>
          <span aria-hidden="true">·</span>
          <span className="app-shell-footer-static-export">static export</span>
        </div>
        <div
          className="app-shell-footer-col app-shell-footer-col--center flex items-center justify-center font-mono"
          data-app-shell-footer-col="center"
        >
          <span className="app-shell-footer-shortcut-legend">
            <kbd>Cmd+K</kbd> Search · <kbd>/</kbd> Search · <kbd>?</kbd> Help · <kbd>Esc</kbd> Close
          </span>
        </div>
        <div
          className="app-shell-footer-col app-shell-footer-col--right flex items-center justify-end gap-2 font-mono"
          data-app-shell-footer-col="right"
        >
          <span>API</span>
          <code className="app-shell-footer-api-origin rounded bg-surface-container-low px-1.5 py-0.5 text-[11px]">
            {props.apiOrigin}
          </code>
          <span aria-hidden="true">·</span>
          <span className="app-shell-footer-schema-version">
            schema&nbsp;v{schemaVersion}
          </span>
        </div>
      </div>
    </footer>
  );
}