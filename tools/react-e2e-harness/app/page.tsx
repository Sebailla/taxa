/**
 * Single-screen entry for the React E2E harness (PR 5c.2-B.1a).
 *
 * Mounts `FileExplorer` directly from the live `@taxa/research` barrel
 * (no AppShell, no BrowserSurface, no production page, no root
 * globals). The harness is intentionally decoupled from the
 * production `src/app/page.tsx` and `src/modules/app-shell/**` so the
 * future capture driver + fixture server can be authored in a fully
 * isolated workspace.
 *
 * Wiring (locked by the parent task brief):
 *   - `taxonId`: a deterministic synthetic non-null id (the harness
 *     never reaches a real backend during the build). The literal
 *     `1` is the smallest non-null taxon the FileExplorer hook
 *     accepts; the harness treats it as opaque.
 *   - `baseUrl`: read from the public harness env var
 *     `NEXT_PUBLIC_HARNESS_BASE_URL` and falls back to a localhost
 *     fixture URL so the static export never fails to inline the
 *     value at build time. The env var is the ONLY public harness
 *     variable; the production app exposes no variable of this name.
 *
 * No domain/keys.ts / store.ts changes; no FileExplorer implementation
 * changes; no production source changes; no build outputs in the
 * production `out/` directory (the harness owns its own `out/` under
 * `tools/react-e2e-harness/out/`).
 */
import type { ReactElement } from "react";

import { FileExplorer } from "@taxa/research";

/** Deterministic synthetic non-null taxon id for the harness build. */
const HARNESS_TAXON_ID = 1;

/** Default base URL the static export inlines when no env var is set. */
const DEFAULT_HARNESS_BASE_URL = "http://127.0.0.1:8765";

/**
 * Resolves the harness fixture base URL from the public harness env
 * var (inlined at build time by Next.js's static export pipeline).
 */
function resolveHarnessBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_HARNESS_BASE_URL;
  if (typeof raw === "string" && raw.trim().length > 0) {
    return raw.trim();
  }
  return DEFAULT_HARNESS_BASE_URL;
}

export default function HarnessPage(): ReactElement {
  const baseUrl = resolveHarnessBaseUrl();
  return (
    <section
      data-harness-surface="file-explorer"
      data-harness-taxon-id={HARNESS_TAXON_ID}
    >
      <FileExplorer taxonId={HARNESS_TAXON_ID} baseUrl={baseUrl} />
    </section>
  );
}
