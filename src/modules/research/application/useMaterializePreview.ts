"use client";

// Typed materialize-preview + folder-creation hook (5b.4).
//
// `useMaterializePreview({ baseUrl, taxonId, fetchFn })` is the single
// React adapter for the FolderTab body. It owns:
//   - the network boundary for `fetchMaterializePreview` (read)
//   - the network boundary for `createMaterializeFolder` (write)
//   - the closed `MaterializeStatus` state machine:
//     `idle` → `loading` → (`ready` | `error`)
//
// Decision #2: FolderTab delegates the loading / error state machine
// to this hook. No inline `fetch`, no local `useState` ladder.
//
// Decision #5: `createFolder()` flips the status to `loading` and
// resolves either to `ready` (the new preview envelope) or to `error`
// (typed `Error`). The FolderTab component reads the status via
// `state.status` and stamps `data-folder-tab-status={status}` so the
// e2e / screenshot harnesses can pin the state without text-matching.
//
// The hook is framework-aware (it owns the network boundary) but the
// pure view-model surface (`projectMaterializePreview`) lives
// alongside it so consumers / tests can exercise the projection
// without React.

import { useEffect, useState } from "react";

import {
  createMaterializeFolder,
  fetchMaterializePreview,
  NetworkError as InfraNetworkError,
  type FetchLike,
  type MaterializePreviewEnvelope,
} from "../infrastructure/api";

/** Closed union of the materialize status state machine.
 *
 *  `idle`    — initial / never-loaded state (rendered as a
 *               "not materialized" empty surface)
 *  `loading` — a fetch is in flight (either the initial preview or
 *               the user-initiated folder creation)
 *  `ready`   — a preview envelope is available (the typed
 *               `preview` field is non-null)
 *  `error`   — the last fetch / create threw a typed `Error`
 *               (the typed `error` field is non-null)
 */
export type MaterializeStatus = "idle" | "loading" | "ready" | "error";

export function isMaterializeStatus(v: unknown): v is MaterializeStatus {
  return v === "idle" || v === "loading" || v === "ready" || v === "error";
}

/** Typed input to `createFolder()`. Caller-side shape (no React / no
 *  network concerns) — the hook projects it into the typed fetch. */
export interface FolderCreateInput {
  /** Display label (currently the taxon's scientific name; the field
   *  is shaped for forward-compat — a future caller may want a
   *  different folder display name). */
  readonly label: string;
}

export interface MaterializePreviewViewModel {
  readonly taxonId: number;
  readonly exists: boolean;
  readonly status: "ready" | "pending" | "absent";
  readonly filesystemPath: string | null;
  readonly pendingJobs: readonly { readonly id: string; readonly startedAt: string }[];
}

/** Project a wire `MaterializePreviewEnvelope` into the
 *  presentation-ready view model. Framework-free. */
export function projectMaterializePreview(
  envelope: MaterializePreviewEnvelope,
): MaterializePreviewViewModel {
  return {
    taxonId: envelope.taxon_id,
    exists: envelope.exists,
    status: envelope.status,
    filesystemPath: envelope.filesystem_path,
    pendingJobs: envelope.pending_jobs.map((j) => ({
      id: j.id, startedAt: j.started_at,
    })),
  };
}

export interface UseMaterializePreviewOptions {
  readonly baseUrl: string;
  readonly taxonId: number | null;
  readonly fetchFn?: FetchLike;
}

export interface MaterializePreviewHookState {
  readonly status: MaterializeStatus;
  readonly preview: MaterializePreviewViewModel | null;
  readonly error: Error | null;
  /** Triggers a folder creation. Returns the new preview envelope
   *  on success or throws a typed `Error` on failure. The caller
   *  can also observe the status via `state.status`. */
  readonly createFolder: (input: FolderCreateInput) => Promise<MaterializePreviewViewModel>;
}

/** React adapter for the materialize-preview + folder-creation flow. */
export function useMaterializePreview(
  options: UseMaterializePreviewOptions,
): MaterializePreviewHookState {
  const { baseUrl, taxonId, fetchFn } = options;
  const [status, setStatus] = useState<MaterializeStatus>("idle");
  const [preview, setPreview] = useState<MaterializePreviewViewModel | null>(null);
  const [error, setError] = useState<Error | null>(null);

  // Read: mount + taxonId change → fetch the preview. When `taxonId`
  // is null the hook stays idle (no fetch).
  useEffect(() => {
    if (taxonId === null) {
      setStatus("idle"); setPreview(null); setError(null);
      return;
    }
    let cancelled = false;
    setStatus("loading"); setError(null);
    void (async () => {
      try {
        const env = await fetchMaterializePreview(baseUrl, taxonId, fetchFn);
        if (cancelled) return;
        setPreview(projectMaterializePreview(env));
        setStatus("ready");
      } catch (cause) {
        if (cancelled) return;
        setError(cause instanceof Error ? cause : new Error(String(cause)));
        setStatus("error");
      }
    })();
    return () => { cancelled = true; };
  }, [baseUrl, taxonId, fetchFn]);

  /** Folder creation (decision #5). Returns the new envelope on
   *  success or throws on failure. */
  const createFolder = async (
    _input: FolderCreateInput,
  ): Promise<MaterializePreviewViewModel> => {
    if (taxonId === null) {
      throw new Error("createFolder requires a non-null taxonId");
    }
    setStatus("loading"); setError(null);
    try {
      const env = await createMaterializeFolder(baseUrl, taxonId, fetchFn);
      const vm = projectMaterializePreview(env);
      setPreview(vm);
      setStatus("ready");
      return vm;
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
      setStatus("error");
      throw cause instanceof Error ? cause : new Error(String(cause));
    }
  };

  return { status, preview, error, createFolder };
}

// Re-export the infra `NetworkError` so consumers can `instanceof`
// against the typed shape the hook raises (decision #2 contract —
// typed hook surfaces typed errors).
export { InfraNetworkError as NetworkError };