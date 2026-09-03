/**
 * `useMounted()` — SSR-safe client-only flag (PR 4b.5 refactor).
 *
 * Returns `false` during the first paint (SSR + initial client render)
 * and flips to `true` after the first `useEffect` runs. Consumers gate
 * `localStorage` reads behind the flag so React's hydration guard never
 * trips on persisted state that only exists on the client.
 *
 * Lives in the `browser-state` presentation layer (React is allowed
 * per spec.md rule 4) and is re-exported through the module's public
 * barrel so `app-shell` and every other module that needs the same
 * SSR-safe client-only switch can reuse it without a deep import
 * (spec.md rule 5).
 *
 * The hook is intentionally tiny — `useEffect` + `useState(false)` —
 * because any helper that reads from the typed store must call this
 * hook itself; keeping the surface narrow prevents accidental coupling
 * to the four-key storage contract.
 */

import { useEffect, useState } from "react";

export function useMounted(): boolean {
  const [mounted, setMounted] = useState<boolean>(false);
  useEffect(() => {
    setMounted(true);
  }, []);
  return mounted;
}