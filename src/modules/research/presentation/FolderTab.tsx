"use client";

// FolderTab — per-taxon materialize body (5b.4).
//
// Renders the per-taxon materialize indicator + the typed folder
// creation affordance. Delegates the loading / error state machine
// to `useMaterializePreview` (decision #2). Surfaces the state via
// `data-folder-tab-status` (decision #5) so e2e / screenshot
// harnesses can pin the state without text-matching.
//
// The body rides the production `.folder-tab` selector the 3c-c
// `@layer components` block already declares. No new CSS.
//
// States:
//   - `idle`    — no taxon is selected (or no fetch has fired yet);
//                 the body renders a "no taxon selected" empty state
//   - `loading` — a fetch / create is in flight; the body renders a
//                 typed progress indicator
//   - `ready`   — a preview envelope is available; the body renders
//                 the materialize indicator + the folder-creation button
//   - `error`   — the last fetch / create threw; the body surfaces a
//                 typed error region (role="status")

import type { ReactElement } from "react";
import { useState } from "react";

import { useMaterializePreview, type FolderCreateInput } from "@taxa/research";

export interface FolderTabProps {
  /** Currently selected taxon id. `null` means the tree has no
   *  selection yet — the tab renders the idle empty state. */
  readonly taxonId: number | null;
  /** Display label used when the user triggers folder creation
   *  (the folder's display name in the typed create-input). When
   *  omitted the hook defaults to an empty label. */
  readonly folderLabel?: string;
}

export function FolderTab({ taxonId, folderLabel }: FolderTabProps): ReactElement {
  // The hook is unconditionally declared (rules of hooks) — when
  // `taxonId` is null the hook short-circuits to the idle state and
  // never fires a network request.
  const { status, preview, error, createFolder } = useMaterializePreview({
    baseUrl: "",
    taxonId,
  });

  // Local "create in flight" flag — distinct from the hook's
  // status (which covers both initial load and create). The hook's
  // status flips to `loading` during the create fetch; we surface a
  // slightly different button label so the user knows the action is
  // in flight.
  const [creating, setCreating] = useState<boolean>(false);

  const onCreate = async (): Promise<void> => {
    if (taxonId === null || creating) return;
    const input: FolderCreateInput = { label: folderLabel ?? "" };
    setCreating(true);
    try {
      await createFolder(input);
    } catch {
      // The hook's status is already `error`; the error region
      // surfaces the typed message below.
    } finally {
      setCreating(false);
    }
  };

  if (taxonId === null) {
    return (
      <div className="folder-tab" data-tab-content="folder"
           data-folder-tab-status="idle">
        <p className="authorship">
          Folder preview opens once you pick a taxon.
        </p>
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="folder-tab" data-tab-content="folder"
           data-folder-tab-status="loading"
           data-taxon-id={taxonId}
           aria-busy="true">
        <span className="material-symbols-outlined animate-spin"
              aria-hidden="true">progress_activity</span>
        <p className="authorship">Materializing corpus…</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="folder-tab" data-tab-content="folder"
           data-folder-tab-status="error"
           data-taxon-id={taxonId}
           role="status" aria-live="assertive">
        <span className="material-symbols-outlined" aria-hidden="true">error</span>
        <p className="authorship">
          {`Could not load materialize preview: ${error?.message ?? "unknown error"}`}
        </p>
        <button type="button"
                className="folder-tab-retry"
                data-action="folder-tab-retry"
                onClick={() => { /* hook re-runs on next effect */ }}>
          Retry
        </button>
      </div>
    );
  }

  // status === "ready"
  const exists = preview?.exists === true;
  const pending = (preview?.pendingJobs.length ?? 0) > 0;
  return (
    <div className="folder-tab" data-tab-content="folder"
         data-folder-tab-status="ready"
         data-taxon-id={taxonId}
         data-folder-exists={exists ? "true" : "false"}
         data-folder-pending={pending ? "true" : "false"}>
      <span className="materialize-indicator"
            aria-label={exists ? "Materialized" : "Not materialized"}
            data-materialize-state={exists ? "ready" : "absent"}>
        <span className="material-symbols-outlined" aria-hidden="true">
          {exists ? "check_circle" : pending ? "schedule" : "folder_off"}
        </span>
      </span>
      <p className="authorship">
        {exists
          ? `Corpus ready at ${preview?.filesystemPath ?? "(unknown path)"}.`
          : pending
            ? "Materialization queued — check back shortly."
            : "No corpus materialized yet."}
      </p>
      {exists ? null : (
        <button type="button"
                className="folder-tab-create"
                data-action="folder-tab-create"
                disabled={creating}
                onClick={() => { void onCreate(); }}>
          {creating ? "Creating…" : "Create folder"}
        </button>
      )}
    </div>
  );
}
