/**
 * Single-screen client entry for the App Router static export (PR 3b).
 *
 * Minimal semantic placeholder. The real single-screen app body — the
 * ``<AppShell>`` from ``@taxa/app-shell`` with the typed-store hydration
 * guard from ``@taxa/browser-state`` — lands with PR 4b. Tailwind 4 design
 * tokens (and the corresponding utility classes this markup would use)
 * land with PR 3c.
 *
 * Chain-topology guard: this file MUST NOT import
 *   - ``@taxa/app-shell``        (owned by PR 4b)
 *   - ``@taxa/browser-state``    (owned by PR 4a)
 *   - ``./globals.css``          (owned by PR 3c Tailwind tokens)
 *
 * The ``<main>`` landmark and the visible ``<h1>`` are the minimum semantic
 * content ``next build`` needs to render a non-empty page so the G2
 * ``out/index.html`` witness is satisfiable.
 */
export default function Page(): React.ReactElement {
  return (
    <main>
      <h1>taxa</h1>
    </main>
  );
}