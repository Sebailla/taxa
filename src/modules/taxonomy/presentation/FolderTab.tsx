"use client";

/**
 * FolderTab — native DetailPanel Folder tab body (ODD-TDFOLDER-001
 * + ODD-PHASE2 cutover).
 *
 * Renders the server-composed materialize-preview payload under the
 * native "Folder" header, paints loading / empty / error / retry
 * states, and surfaces the line-by-line path preview with ✓ / +
 * markers per segment (mirrors the legacy
 * `web/detail.js::renderFolderTab` byte-for-byte). The wire
 * payload is the canonical `MaterializePreview` projection from
 * `infrastructure/api.ts`; the `research_dir`, `relative_path`,
 * `absolute_path`, `segments[]`, `new_count`, `existing_count`,
 * `all_exist` values round-trip verbatim from the server so the
 * React port NEVER reconstructs / sanitises / joins paths
 * client-side (the FastAPI endpoint is the source of truth for
 * the materialized chain — the renderer is a for-each over the
 * response array, never sorts / groups / paginates client-side).
 *
 * Source isolation: the materialize-preview endpoint is
 * source-AWARE (`source=col|worms|freshwater` selects which
 * parent column the server walks). Mirrors how the legacy
 * `web/api.js::previewMaterialize(taxonId, state.treeSource)`
 * forwards `state.treeSource` so the WoRMS / Freshwater
 * hierarchies walk the right column. The parent cache therefore
 * MUST be invalidated on source switches (the path is source-
 * specific — a CoL preview under one taxon yields a different
 * chain under WoRMS when the parent_id columns diverge). The
 * `previewMaterialize` infra helper carries the source through
 * the wire shape; the FolderTab renderer is a pure consumer of
 * the per-taxon status discriminated union.
 *
 * Materialize UX contract: the create action requires an explicit
 * in-tab confirmation before POSTing `materializeResearch`. The
 * legacy `web/detail.js::renderFolderTab` clicks straight through
 * (no second-step confirmation), but the React port keeps the
 * `pendingCreate` gate so a stray Enter-key on the focused taxon
 * cannot spawn `mkdir` against an arbitrary path. The Open +
 * Copy pair only surfaces when `all_exist === true` (mirrors the
 * legacy `web/detail.js::renderFolderTab::pathActions` branch —
 * opening a not-yet-materialized folder yields a 404). Inline
 * success / error states replace the legacy toast helper so no
 * new transient-notification dependency is required (per the
 * ODD-TDFOLDER-001 user constraint: "Use inline success/error
 * states only; no new toast dependency or transient notification
 * system"). Clipboard failure is graceful — the renderer catches
 * the rejection and paints an inline error so the user can
 * retry, mirroring the legacy `showToast(`Could not copy: …`)`
 * affordance without the toast helper.
 *
 * ODD-PHASE2 (design-system cutover): the inline loading copy +
 * Material Symbols `progress_activity` glyph, the inline error
 * message, the success message, the info banner, the Create /
 * Confirm / Cancel / Open / Copy / Retry buttons now route
 * through three design-system primitives (Spinner + InlineMessage
 * + Button) imported from `@taxa/design-system` (the public
 * barrel). The legacy `<button className="folder-btn
 * folder-btn-primary …">` / `folder-btn-secondary` / `<div
 * className="folder-inline-message folder-inline-message-error
 * …">` / `folder-inline-message-success` / `folder-info-banner`
 * compositions are gone. Seven dead `.folder-tab .folder-*` CSS
 * rules collapse out of `src/app/globals.css` (`folder-btn` +
 * `folder-btn-primary` + `folder-btn-secondary` +
 * `folder-info-banner` + `folder-inline-message` +
 * `folder-inline-message-error` + `folder-inline-message-
 * success`) — the cascade now only owns the wrapper + the
 * specialized segment list + section header + counts summary +
 * create row wrapper + confirm step + path-actions row.
 *
 * spec.md rule 4: presentation → taxonomy module only. The
 * component imports the canonical `MaterializePreview` +
 * `MaterializePreviewSegment` projections from the infrastructure
 * layer; no React / Next / HTTP / fetch / DOM tokens land in the
 * body beyond the JSX the component is required to render (the
 * file declares `"use client"` because the parent TaxonomyTree
 * island needs the create / open / copy handlers + the
 * confirmation gate to stay interactive after hydration).
 */
import { Fragment, useEffect } from "react";
import type { ReactNode } from "react";
import { Button, InlineMessage, Spinner } from "@taxa/design-system";
import type {
  MaterializePreview,
  MaterializePreviewSegment,
  MaterializeResult,
  OpenFolderResult,
} from "../infrastructure/api";

/** W6.5-BRIDGE-006 — verbatim local constant for the
 *  FolderTab → Explorer refresh bridge event name. The
 *  Explorer route (in `@taxa/research/presentation/Explorer.tsx`)
 *  pins the same literal through a separate focused test;
 *  the kernel export `EXPLORER_REFRESH_EVENT_NAME` in
 *  `@taxa/research/presentation/explorer-state` is the
 *  canonical source for cross-module consumers. The
 *  FolderTab dispatches `new CustomEvent(EXPLORER_REFRESH_EVENT_NAME)`
 *  on `window` once `materializeResearch` or `openFolder`
 *  reaches the success state; the Explorer route listens
 *  on mount and re-fetches the `/api/files` tree so the
 *  tree mirrors the new folder structure without dropping
 *  the existing ExplorerLoadStatus / expanded set /
 *  selected-path / ViewerState. */
const EXPLORER_REFRESH_EVENT_NAME = "taxa:explorer:refresh";

/** Status of the materialize-preview fetch for the currently
 *  selected taxon. Mirrors `SearchTabStatus` + `VernacularTabStatus`
 *  + `SynonymTabStatus` + `DistributionTabStatus` byte-for-byte so
 *  the parent's per-taxon cache + retry wiring stays symmetric
 *  across every detail-panel tab. `idle` means the parent hasn't
 *  started the fetch yet (defensive — the eager-fetch-on-selection
 *  contract fires the preview request the moment a taxon becomes
 *  the active selection, so `idle` is rare in practice). `loaded`
 *  carries the canonical `MaterializePreview` projection so the
 *  renderer can branch on the wire `all_exist` flag without a
 *  client-side recomputation of the new-vs-existing segment
 *  counts. */
export type FolderTabStatus =
  | { readonly kind: "idle" }
  | { readonly kind: "loading" }
  | { readonly kind: "loaded"; readonly preview: MaterializePreview }
  | { readonly kind: "error"; readonly message: string };

/** Status of the materialize-create action for the currently
 *  selected taxon. Drives the inline "Creating… / Created /
 *  Error" copy under the path preview. The `idle` branch hides
 *  the create affordance (the user must click "Create" first);
 *  `creating` disables the create + confirm buttons so the user
 *  cannot double-submit; `created` carries the canonical
 *  `MaterializeResult` payload so the parent can refresh the
 *  preview cache (the next render sees a fresh `loaded` preview
 *  with `all_exist === true` and the path-actions row
 *  appears); `error` carries the failure message so the user can
 *  retry by clicking Create again. */
export type FolderCreateStatus =
  | { readonly kind: "idle" }
  | { readonly kind: "creating" }
  | { readonly kind: "created"; readonly result: MaterializeResult }
  | { readonly kind: "error"; readonly message: string };

/** Status of the open-folder action. Drives the inline "Opening… /
 *  Opened / Error" copy under the path-actions row. `idle` is the
 *  default; `opening` disables the button so the user cannot
 *  double-spawn the OS file manager; `opened` carries the
 *  canonical `OpenFolderResult` payload so the inline copy can
 *  surface the `opened_with` binary name; `error` carries the
 *  failure message so the user can retry. */
export type FolderOpenStatus =
  | { readonly kind: "idle" }
  | { readonly kind: "opening" }
  | { readonly kind: "opened"; readonly result: OpenFolderResult }
  | { readonly kind: "error"; readonly message: string };

/** Status of the copy-path action. `idle` is the default; `copied`
 *  triggers the brief label flip (mirrors the legacy
 *  `web/detail.js::renderFolderTab::copyBtn` `labelSpan.textContent
 *  = "Copied!"; setTimeout(…, 1200)` affordance); `error` shows
 *  the inline failure message without crashing the tab. */
export type FolderCopyStatus =
  | { readonly kind: "idle" }
  | { readonly kind: "copied" }
  | { readonly kind: "error"; readonly message: string };

export interface FolderTabProps {
  readonly status: FolderTabStatus;
  /** Retry callback. Fires when the user clicks the "Retry"
   *  button on the error state. The parent maps this to a
   *  re-issuance of the canonical `previewMaterialize` request.
   *  The parent is responsible for invalidating the cache on
   *  source switch — the renderer never mutates the cache. */
  readonly onRetryPreview: () => void;
  /** Source-aware create callback. Fires when the user confirms
   *  the create action (after the in-tab confirmation gate has
   *  flipped). The parent maps this to a POST through the
   *  canonical `materializeResearch` helper + a follow-up
   *  `previewMaterialize` to refresh the cached preview. */
  readonly onCreate: () => void;
  /** Open-folder callback. Fires when the user clicks "Open in
   *  Finder" on the path-actions row. The parent maps this to a
   *  POST through the canonical `openFolder` helper. */
  readonly onOpen: () => void;
  /** Copy-path callback. Fires when the user clicks "Copy path"
   *  on the path-actions row. The parent maps this to
   *  `navigator.clipboard.writeText(preview.absolute_path)`
   *  with a graceful catch (the renderer never sees the
   *  clipboard API directly — the parent owns the transport so
   *  the renderer stays framework-free). */
  readonly onCopy: () => void;
  /** Create status discriminated union. Drives the inline
   *  creating / created / error copy + the disabled state on the
   *  create + confirm buttons. */
  readonly createStatus: FolderCreateStatus;
  /** Open status discriminated union. Drives the inline opening
   *  / opened / error copy + the disabled state on the open
   *  button. */
  readonly openStatus: FolderOpenStatus;
  /** Copy status discriminated union. Drives the inline copied /
   *  error copy + the brief label flip on the copy button. */
  readonly copyStatus: FolderCopyStatus;
  /** True iff the in-tab create confirmation is armed. The
   *  parent owns the gate state (so a source switch / taxon
   *  switch / cache eviction can clear it without race
   *  conditions). When true, the renderer paints the "Confirm
   *  create?" row; when false, it paints the bare "Create N
   *  folders" CTA. The renderer never sets the gate directly
   *  (mirrors the legacy `web/detail.js::renderFolderTab::btn
   *  click` flow that flipped straight to "Creating…"; the
   *  React port adds an explicit gate per the ODD-TDFOLDER-001
   *  user constraint). */
  readonly createArmed: boolean;
  /** Arm-create callback. Fires when the user clicks "Create N
   *  folders". The parent flips `createArmed` to true so the
   *  next render paints the confirmation row. */
  readonly onArmCreate: () => void;
  /** Disarm-create callback. Fires when the user clicks
   *  "Cancel" on the confirmation row OR when the user
   *  re-clicks the bare CTA. The parent flips `createArmed`
   *  back to false. */
  readonly onDisarmCreate: () => void;
}

/** Public component. Renders one of: loading spinner + copy,
 *  error copy + Retry button, or the loaded preview with the
 *  line-by-line segment list, the count summary, the info
 *  banner (when `all_exist === true`), the create row (when
 *  `all_exist === false`), and the path-actions row (when
 *  `all_exist === true`). The wrapper carries the canonical
 *  `.folder-tab` class so the existing `src/app/globals.css`
 *  cascade paints the section + the segment list + the create
 *  row + the path-actions row without a redesign pass
 *  (mirrors the legacy `.materialize-tab-content` /
 *  `.materialize-modal-list` / `.materialize-modal-marker` /
 *  `.materialize-modal-counts` / `.materialize-modal-info-banner`
 *  / `.materialize-modal-btn` / `.materialize-modal-path-actions`
 *  surface byte-for-byte, just renamed to the `.folder-tab`
 *  family to match the React cutover's `.search-tab` /
 *  `.distribution-tab` / `.synonym-tab` / `.vernacular-tab`
 *  convention so the chain-topology guard in
 *  `tests/test_research_styles.py` keeps whitelisting the
 *  base selector under the 3c-c research / chrome surface). */
export default function FolderTab({
  status,
  onRetryPreview,
  onCreate,
  onOpen,
  onCopy,
  createStatus,
  openStatus,
  copyStatus,
  createArmed,
  onArmCreate,
  onDisarmCreate,
}: FolderTabProps): React.ReactElement {
  // W6.5-BRIDGE-006 — FolderTab → Explorer refresh bridge.
  // Two `useEffect`s dispatch a
  // `window.CustomEvent(EXPLORER_REFRESH_EVENT_NAME)` once
  // the create / open transitions reach their success
  // state. The Explorer route subscribes to that event on
  // mount and re-fetches the `/api/files` tree so the
  // right-pane tree mirrors the new folder structure
  // without dropping the existing ExplorerLoadStatus /
  // expanded set / selected-path / ViewerState / search
  // state (the Explorer handler calls ONLY `loadTree()`,
  // which flips `loadStatus` to `"loading"` then resolves
  // without touching the user's interactive state).
  //
  // Each effect is keyed on the discriminated union
  // (`createStatus` / `openStatus`) so React's
  // primitive-equality dedupe fires exactly once per status
  // transition. The pre-W6.5 contract never dispatched
  // the event — a mid-flight `"creating"` state MUST NOT
  // trigger the Explorer re-fetch (the folder structure
  // hasn't hit disk yet). The success transition is the
  // only dispatch surface, so the explorer refresh
  // mirrors the exact moment the side effect lands.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (createStatus.kind !== "created") return;
    window.dispatchEvent(
      new CustomEvent(EXPLORER_REFRESH_EVENT_NAME),
    );
  }, [createStatus]);
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (openStatus.kind !== "opened") return;
    window.dispatchEvent(
      new CustomEvent(EXPLORER_REFRESH_EVENT_NAME),
    );
  }, [openStatus]);
  if (status.kind === "idle" || status.kind === "loading") {
    return (
      <div
        className="folder-tab"
        data-tab-content="folder"
        data-folder-status={status.kind}
        role="status"
        aria-busy="true"
      >
        <h3
          className="folder-section-header"
          data-folder-section-header=""
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[16px]"
          >
            create_new_folder
          </span>
          <span>Folder</span>
          <span
            className="folder-section-count"
            aria-label="0 folder segments"
          >
            0
          </span>
        </h3>
        <Spinner size="md" label="Loading folder preview…" />
      </div>
    );
  }
  if (status.kind === "error") {
    return (
      <div
        className="folder-tab"
        data-tab-content="folder"
        data-folder-status="error"
        role="alert"
      >
        <h3
          className="folder-section-header"
          data-folder-section-header=""
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[16px]"
          >
            create_new_folder
          </span>
          <span>Folder</span>
          <span
            className="folder-section-count"
            aria-label="0 folder segments"
          >
            0
          </span>
        </h3>
        <InlineMessage
          variant="error"
          data-folder-inline-message="error"
          role="alert"
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[18px]"
          >
            error
          </span>
          <span>{status.message}</span>
        </InlineMessage>
        <p className="text-body-sm text-on-surface px-2 py-2 text-center">
          Could not load the preview.
        </p>
        <div className="flex justify-center pb-2">
          <Button
            variant="secondary"
            onClick={onRetryPreview}
            data-action="retry-folder-preview"
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }
  // Loaded — render the preview with the conditional create /
  // path-actions rows. The preview payload is the canonical
  // `MaterializePreview` projection; the renderer is a for-each
  // over `preview.segments` and never recomputes the new-vs-
  // existing counts (the server is the source of truth).
  return (
    <div
      className="folder-tab"
      data-tab-content="folder"
      data-folder-status="loaded"
      data-folder-all-exist={status.preview.all_exist ? "true" : "false"}
      data-folder-new-count={String(status.preview.new_count)}
      data-folder-existing-count={String(status.preview.existing_count)}
    >
      <h3
        className="folder-section-header"
        data-folder-section-header=""
      >
        <span
          aria-hidden="true"
          className="material-symbols-outlined text-[16px]"
        >
          create_new_folder
        </span>
        <span>Folder</span>
        <span
          className="folder-section-count"
          aria-label={`${status.preview.segments.length} folder segments`}
        >
          {status.preview.segments.length}
        </span>
      </h3>
      {renderPreviewWrap(status.preview)}
      {renderCounts(status.preview)}
      {status.preview.all_exist ? renderInfoBanner() : null}
      {status.preview.all_exist ? null : renderCreateRow(
        status.preview,
        createStatus,
        createArmed,
        onArmCreate,
        onDisarmCreate,
        onCreate,
      )}
      {status.preview.all_exist ? renderPathActionsRow(
        openStatus,
        copyStatus,
        onOpen,
        onCopy,
      ) : null}
    </div>
  );
}

/** Render the path-preview wrapper — the section title + the
 *  line-by-line segment list. The cumulative path is built from
 *  the wire `preview.research_dir` + the per-segment `name`
 *  fields verbatim (the legacy `web/detail.js::renderFolderTab`
 *  used `acc = preview.research_dir; for (const seg of
 *  preview.segments) acc = `${acc}/${seg.name}``; the React
 *  port preserves the same join logic because the server
 *  intentionally separates the segments from the cumulative
 *  path so the client can render them incrementally — the
 *  FastAPI endpoint does NOT pre-join the cumulative path
 *  per segment, it joins `relative_path` once. The
 *  `data-folder-segment-cumulative` attribute carries the
 *  cumulative path so a future test can pin the segment order
 *  without a deep class-name scrape. */
function renderPreviewWrap(preview: MaterializePreview): ReactNode {
  return (
    <div
      className="folder-segment-wrap"
      data-folder-segment-wrap=""
    >
      <div className="folder-section-title">Path preview:</div>
      <ul
        className="folder-segment-list"
        data-folder-segment-list=""
      >
        {renderSegments(preview)}
      </ul>
    </div>
  );
}

/** Render one `<li>` per segment with the cumulative path +
 *  the ✓ / + marker. The marker uses the wire `exists` flag
 *  (the server pre-computes `is_new = not exists` and surfaces
 *  it as a separate field too — the renderer branches on
 *  `exists` because the legacy oracle uses the same predicate:
 *  `seg.exists ? "✓" : "+"`). The cumulative path is built by
 *  prepending `preview.research_dir` + a literal `/` separator
 *  to each segment `name` (mirrors the legacy
 *  `web/detail.js::renderFolderTab::acc = `${acc}/${seg.name}``
 *  byte-for-byte, just scoped to the React render function).
 *  The segment row stamps `data-folder-segment-name` +
 *  `data-folder-segment-exists` so the parity test can pin the
 *  marker text without scraping the marker glyph from the
 *  className. */
function renderSegments(preview: MaterializePreview): ReactNode {
  let acc = preview.research_dir;
  return preview.segments.map((seg, i) => {
    acc = `${acc}/${seg.name}`;
    return renderSegment(seg, acc, i);
  });
}

function renderSegment(
  seg: MaterializePreviewSegment,
  cumulative: string,
  index: number,
): ReactNode {
  const marker = seg.exists ? "✓" : "+";
  const markerCls = seg.exists
    ? "folder-segment-marker folder-segment-marker-exists"
    : "folder-segment-marker folder-segment-marker-new";
  return (
    <li
      key={`seg-${index}-${seg.name}`}
      className="folder-segment-item"
      data-folder-segment-exists={seg.exists ? "true" : "false"}
      data-folder-segment-name={seg.name}
    >
      <span
        className={markerCls}
        aria-hidden="true"
        data-folder-segment-marker={seg.exists ? "exists" : "new"}
      >
        {marker}
      </span>
      <span
        className="folder-segment-path"
        data-folder-segment-cumulative={cumulative}
      >
        {cumulative}
      </span>
    </li>
  );
}

/** Render the count summary — "N new folders · M already
 *  existed" copy mirroring the legacy
 *  `web/detail.js::renderFolderTab::counts` (with the legacy
 *  singular/plural branch on `new_count === 1`). The wire
 *  values are surfaced verbatim — the renderer does NOT
 *  recompute the new-vs-existing counts (the server is the
 *  source of truth). */
function renderCounts(preview: MaterializePreview): ReactNode {
  const newWord = preview.new_count === 1 ? "new folder" : "new folders";
  return (
    <div
      className="folder-counts"
      data-folder-counts=""
      data-folder-new-count={String(preview.new_count)}
      data-folder-existing-count={String(preview.existing_count)}
    >
      {`${preview.new_count} ${newWord} · ${preview.existing_count} already existed`}
    </div>
  );
}

/** Render the "Path already exists on disk." info banner via
 *  the `<InlineMessage variant="info">` design-system primitive
 *  (from `@taxa/design-system`). Mirrors the legacy
 *  `web/detail.js::renderFolderTab::infoBanner` (check_circle
 *  glyph + green-tinted banner) byte-for-byte — the
 *  `InlineMessage` primitive owns the `bg-surface-container-low
 *  border-outline-variant text-on-surface-variant` palette +
 *  the `rounded-md border px-3 py-2 text-sm` shape; the
 *  `data-folder-info-banner=""` data attribute + the canonical
 *  copy stay preserved on the element. The renderer only
 *  paints the banner when `preview.all_exist === true`; the
 *  parent passes the loaded status through so the JSX branch
 *  lands exactly once. */
function renderInfoBanner(): ReactNode {
  return (
    <InlineMessage
      variant="info"
      data-folder-info-banner=""
      role="status"
    >
      <span
        aria-hidden="true"
        className="material-symbols-outlined text-[20px]"
      >
        check_circle
      </span>
      <span>Path already exists on disk.</span>
    </InlineMessage>
  );
}

/** Render the create row. When `createArmed === false`, paint
 *  the bare "Create N folders" CTA. When `createArmed === true`,
 *  paint the in-tab confirmation row with a "Confirm create?"
 *  prompt + a Confirm button (calls `onCreate`) + a Cancel
 *  button (calls `onDisarmCreate`). Both buttons now route
 *  through the `<Button variant="primary">` /
 *  `<Button variant="secondary">` design-system primitives
 *  (from `@taxa/design-system`) — the legacy `<button
 *  className="folder-btn folder-btn-primary …">` /
 *  `folder-btn-secondary` composition is gone. The create
 *  button's label flips to "Creating…" while `createStatus
 *  .kind === "creating"` (the parent owns the disabled-state
 *  transition). On success (`createStatus.kind === "created"`),
 *  the parent refreshes the preview cache so the next render
 *  sees a fresh `loaded` preview with `all_exist === true`
 *  and the path-actions row replaces the create row. On
 *  error (`createStatus.kind === "error"`), the renderer
 *  shows the failure message inline so the user can retry
 *  by clicking Create again. */
function renderCreateRow(
  preview: MaterializePreview,
  createStatus: FolderCreateStatus,
  createArmed: boolean,
  onArmCreate: () => void,
  onDisarmCreate: () => void,
  onCreate: () => void,
): ReactNode {
  const label = `Create ${preview.new_count} ${
    preview.new_count === 1 ? "folder" : "folders"
  }`;
  const isCreating = createStatus.kind === "creating";
  const isError = createStatus.kind === "error";
  return (
    <Fragment>
      <div
        className="folder-create-row"
        data-folder-create-row=""
        data-folder-create-armed={createArmed ? "true" : "false"}
      >
        {!createArmed ? (
          <Button
            variant="primary"
            disabled={isCreating}
            aria-disabled={isCreating}
            onClick={onArmCreate}
            data-action="create-folders"
          >
            {isCreating ? "Creating…" : label}
          </Button>
        ) : (
          <div
            className="folder-confirm"
            data-folder-confirm=""
            role="group"
            aria-label="Confirm folder creation"
          >
            <span className="folder-confirm-prompt">
              Create {preview.new_count} {preview.new_count === 1 ? "folder" : "folders"} under{" "}
              <code className="folder-confirm-path">{preview.relative_path}</code>?
            </span>
            <div className="folder-confirm-actions">
              <Button
                variant="secondary"
                disabled={isCreating}
                onClick={onDisarmCreate}
                data-action="disarm-create-folders"
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                disabled={isCreating}
                aria-disabled={isCreating}
                onClick={onCreate}
                data-action="confirm-create-folders"
              >
                {isCreating ? "Creating…" : "Confirm create"}
              </Button>
            </div>
          </div>
        )}
      </div>
      {createStatus.kind === "created" ? (
        <InlineMessage
          variant="success"
          data-folder-inline-message="created"
          data-folder-inline-message-success=""
          data-folder-created-path={createStatus.result.relative_path}
          data-folder-created-count={String(createStatus.result.folders_created)}
          data-folder-existed-count={String(createStatus.result.folders_existed)}
          role="status"
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[18px]"
          >
            check_circle
          </span>
          <span>
            {`Folders materialized: ${createStatus.result.relative_path} (${createStatus.result.folders_created} new, ${createStatus.result.folders_existed} already existed)`}
          </span>
        </InlineMessage>
      ) : null}
      {isError ? (
        <InlineMessage
          variant="error"
          data-folder-inline-message="create-error"
          data-folder-inline-message-error=""
          role="alert"
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[18px]"
          >
            error
          </span>
          <span>{`Error materializing: ${createStatus.message}`}</span>
        </InlineMessage>
      ) : null}
    </Fragment>
  );
}

/** Render the path-actions row — the "Open in Finder" + "Copy
 *  path" pair that surfaces when `preview.all_exist === true`.
 *  Both buttons now route through the `<Button variant="secondary">`
 *  design-system primitive (from `@taxa/design-system`) — the
 *  legacy `<button className="folder-btn folder-btn-primary …">`
 *  / `folder-btn-secondary` composition is gone. The Open
 *  button carries the `folder_open` Material Symbols glyph +
 *  invokes `onOpen` (the parent calls `openFolder`); the Copy
 *  button carries the `content_copy` glyph + invokes `onCopy`
 *  (the parent calls `navigator.clipboard.writeText`). Mirrors
 *  the legacy `web/detail.js::renderFolderTab::pathActions`
 *  byte-for-byte. The Open button's label flips to "Opening…"
 *  while `openStatus.kind === "opening"`; on success
 *  (`openStatus.kind === "opened"`) the renderer shows inline
 *  "Opened with `open`: <relative_path>" copy. The Copy button
 *  label flips to "Copied!" while `copyStatus.kind === "copied"`
 *  (mirrors the legacy
 *  `web/detail.js::renderFolderTab::copyBtn` `labelSpan.textContent
 *  = "Copied!"; setTimeout(…, 1200)` affordance — the parent
 *  owns the timer so the renderer stays pure). On error, the
 *  renderer shows the failure message inline so the user can
 *  retry without a tab refresh. */
function renderPathActionsRow(
  openStatus: FolderOpenStatus,
  copyStatus: FolderCopyStatus,
  onOpen: () => void,
  onCopy: () => void,
): ReactNode {
  const isOpening = openStatus.kind === "opening";
  const isOpened = openStatus.kind === "opened";
  const isOpenError = openStatus.kind === "error";
  const isCopied = copyStatus.kind === "copied";
  const isCopyError = copyStatus.kind === "error";
  return (
    <Fragment>
      <div
        className="folder-path-actions"
        data-folder-path-actions=""
      >
        <Button
          variant="secondary"
          disabled={isOpening}
          aria-disabled={isOpening}
          onClick={onOpen}
          data-action="open-folder-tab"
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[18px]"
          >
            folder_open
          </span>
          <span>{isOpening ? "Opening…" : "Open in Finder"}</span>
        </Button>
        <Button
          variant="secondary"
          onClick={onCopy}
          data-action="copy-path"
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[18px]"
          >
            content_copy
          </span>
          <span>{isCopied ? "Copied!" : "Copy path"}</span>
        </Button>
      </div>
      {isOpened ? (
        <InlineMessage
          variant="success"
          data-folder-inline-message="opened"
          data-folder-inline-message-success=""
          data-folder-opened-with={openStatus.result.opened_with}
          data-folder-opened-path={openStatus.result.relative_path}
          role="status"
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[18px]"
          >
            folder_open
          </span>
          <span>
            {`Opened ${openStatus.result.opened_with}: ${openStatus.result.relative_path}`}
          </span>
        </InlineMessage>
      ) : null}
      {isOpenError ? (
        <InlineMessage
          variant="error"
          data-folder-inline-message="open-error"
          data-folder-inline-message-error=""
          role="alert"
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[18px]"
          >
            error
          </span>
          <span>{`Could not open folder: ${openStatus.message}`}</span>
        </InlineMessage>
      ) : null}
      {isCopyError ? (
        <InlineMessage
          variant="error"
          data-folder-inline-message="copy-error"
          data-folder-inline-message-error=""
          role="alert"
        >
          <span
            aria-hidden="true"
            className="material-symbols-outlined text-[18px]"
          >
            error
          </span>
          <span>{`Could not copy path: ${copyStatus.message}`}</span>
        </InlineMessage>
      ) : null}
    </Fragment>
  );
}