"use client";

/**
 * Isolated hydration probe for the typed browser-state hooks.
 *
 * ODD-BSTATE-PW-001 — the dedicated witness component for the
 * static-export hydration contract. Lives inside the `browser-state`
 * presentation layer so the four typed hooks (`useTheme`,
 * `useTreeSource`, `useLastTaxonId`, `useKebabOpenId`) are exercised
 * end-to-end against a real Chromium build, isolated from the main
 * route's AppShell + TaxonomyTree consumers.
 *
 * Hydration contract (browser-state-hydration spec §"Hydration guard
 * against server / client mismatch"):
 *   - SSR renders the typed default for every value (the typed
 *     defaults are the `getServerSnapshot` for `useSyncExternalStore`
 *     + the initial value of `useState` / `useReducer` driven hooks).
 *   - The first client render agrees byte-for-byte because the
 *     initial in-memory cache is the typed default and React's
 *     `getSnapshot` returns the same value until `subscribe`
 *     fires after mount.
 *   - After mount, `useSyncExternalStore` calls `subscribeTheme` (and
 *     the three sibling subscribe functions). Each subscription
 *     triggers `ensureHydrated`, which reads `localStorage` through
 *     `safeGetItem` and updates the in-memory cache. React then
 *     commits the follow-up render with the rehydrated values.
 *
 * The probe exposes stable selectors (`data-testid`,
 * `data-test-value`, `data-action`) so the Chromium contract test
 * (`tests/test_hydration_console.py`) can drive first paint,
 * stored-value rehydration, and setter round-trip assertions without
 * a snapshot test.
 *
 * Scope discipline:
 *   - This component does NOT import `localStorage` directly; the
 *     typed hooks own every storage call. The
 *     `test_browser_state_keys.py::test_application_hook_can_import_react_but_not_localstorage`
 *     contract stays in force for the hook + store layers; the
 *     probe simply consumes them.
 *   - The probe is NOT used by the main route. The
 *     `tests/test_app_shell_render.py::test_out_index_html_chunks_reference_no_browser_state`
 *     boundary test pins the main route as browser-state free; only
 *     the `/hydration-probe` route bundles the typed store.
 */
import type { ReactElement } from "react";

import {
  useTheme,
  useTreeSource,
  useLastTaxonId,
  useKebabOpenId,
} from "../index";

/**
 * Render a stored `number | null` value as the literal `null` string
 * or the decimal representation of the number. Centralised so the
 * static HTML probe and the runtime DOM agree on the textual form
 * (the static HTML must carry the typed default verbatim — a `null`
 * stored value MUST render as the four-character string `null`).
 */
function renderNullableId(value: number | null): string {
  return value === null ? "null" : String(value);
}

export default function HydrationProbe(): ReactElement {
  const [theme, setTheme] = useTheme();
  const [source, setSource] = useTreeSource();
  const [lastTaxonId, setLastTaxonId] = useLastTaxonId();
  const [kebabOpenId, setKebabOpenId] = useKebabOpenId();

  return (
    <section
      data-testid="hydration-probe"
      aria-label="Browser-state hydration probe"
    >
      <h1>Browser-state hydration probe</h1>
      <p data-testid="probe-description">
        Isolated static-export witness for the four typed browser-state
        hooks. Storage keys are read AFTER React hydrates; the static
        first render carries the typed defaults verbatim.
      </p>
      <dl>
        <div data-row="theme">
          <dt>Theme</dt>
          <dd>
            <span data-test-value="theme">{theme}</span>
          </dd>
          <button
            type="button"
            data-action="set-theme-dark"
            onClick={() => setTheme("dark")}
          >
            Set theme=dark
          </button>
          <button
            type="button"
            data-action="set-theme-light"
            onClick={() => setTheme("light")}
          >
            Set theme=light
          </button>
        </div>

        <div data-row="source">
          <dt>Tree source</dt>
          <dd>
            <span data-test-value="source">{source}</span>
          </dd>
          <button
            type="button"
            data-action="set-source-col"
            onClick={() => setSource("col")}
          >
            Set source=col
          </button>
          <button
            type="button"
            data-action="set-source-worms"
            onClick={() => setSource("worms")}
          >
            Set source=worms
          </button>
          <button
            type="button"
            data-action="set-source-freshwater"
            onClick={() => setSource("freshwater")}
          >
            Set source=freshwater
          </button>
        </div>

        <div data-row="last-taxon-id">
          <dt>Last taxon id</dt>
          <dd>
            <span data-test-value="last-taxon-id">
              {renderNullableId(lastTaxonId)}
            </span>
          </dd>
          <button
            type="button"
            data-action="set-last-taxon-id"
            onClick={() => setLastTaxonId(42)}
          >
            Set lastTaxonId=42
          </button>
          <button
            type="button"
            data-action="clear-last-taxon-id"
            onClick={() => setLastTaxonId(null)}
          >
            Set lastTaxonId=null
          </button>
        </div>

        <div data-row="kebab-open-id">
          <dt>Kebab open id</dt>
          <dd>
            <span data-test-value="kebab-open-id">
              {renderNullableId(kebabOpenId)}
            </span>
          </dd>
          <button
            type="button"
            data-action="set-kebab-open-id"
            onClick={() => setKebabOpenId(7)}
          >
            Set kebabOpenId=7
          </button>
          <button
            type="button"
            data-action="clear-kebab-open-id"
            onClick={() => setKebabOpenId(null)}
          >
            Set kebabOpenId=null
          </button>
        </div>
      </dl>
    </section>
  );
}
