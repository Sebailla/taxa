"use client";

/**
 * DetailPanel — modal-dialog popup for the selected taxon
 * (ODD-TAPOPUP-001). Replaces the pre-popup sticky detail rail.
 *
 * Client island rendered inside the existing `TaxonomyTree`
 * surface. Mounts when the user selects a tree taxon (via the
 * kebab IconButton on every row, the leaf disclosure click,
 * or the breadcrumb focus handler), renders the native-style
 * four-tab popup, and clears when the user closes the panel or
 * switches sources.
 *
 * ODD-TAPOPUP-001 — popup replaces the sticky detail rail:
 *   - The popup is a modal dialog (`role="dialog"`,
 *     `aria-modal="true"`, `aria-labelledby` pointing at the
 *     scientific-name `<h2>`). Clicking the row-level kebab
 *     IconButton opens the popup for that row; the popup is
 *     `selected`-driven so the same primitive that drives
 *     row selection drives the popup's open state.
 *   - The popup offers exactly four tabbed sections, one at a
 *     time: Synonyms, Distribution (the "Location/Distribution"
 *     tab), Search ("Search links"), and Folder ("Folder
 *     creation"). The legacy Overview + Vernaculars tabs are
 *     GONE — the user-selected four tabs subsume the legacy
 *     surface. The popup ships all four tabs as real backing
 *     surfaces (no `disabled` + `aria-disabled="true"`
 *     deferral; the pre-popup "visibly mark unavailable later
 *     tabs without fake actions" policy no longer applies).
 *   - The popup closes via its close IconButton + Escape key
 *     + backdrop click. All three routes share the same
 *     `onClose()` callback that the parent maps to
 *     `setSelected(null)`.
 *   - The popup focuses its close IconButton on mount so
 *     keyboard users land inside the dialog as soon as it
 *     opens (WAI-ARIA Authoring Practices dialog pattern).
 *   - The popup adapts for narrow viewports: at viewports
 *     `<= 768px` the centered dialog fills the viewport
 *     (the `@media` rule in `src/app/globals.css` overrides
 *     the centered dialog's fixed dimensions with
 *     viewport-filling dimensions).
 *   - The popup's header is minimal: the scientific-name
 *     `<h2>` + the close IconButton. No badges (the pre-popup
 *     sticky rail carried several source-affordance badges
 *     in the header; the popup drops them).
 *     No `data-realm` attribute (the pre-popup realm-tint
 *     cascade was scoped to the Overview body's
 *     scientific-name span; the popup drops the Overview
 *     body).
 *   - Per-taxon active-tab memory still lives at the parent
 *     `TaxonomyTree` level (the `Map<number, DetailTabKey>`
 *     map); `DetailPanel` is the pure renderer that reads +
 *     writes via the callback.
 *
 * ODD-PHASE2 — design-system cutover (post-PR #386):
 *   The inline rank badge spans in the header collapse into
 *   `<Badge variant="primary | subtle | warning">` primitives; the
 *   inline close button (formerly styled with the detail-close
 *   hook) collapses into
 *   `<IconButton variant="subtle" aria-label="Hide details">`;
 *   the inline div with the detail-card hook collapses into
 *   `<Card variant="default">`; the inline
 *   description-list label + value typography collapses into
 *   `<Text variant="caption | body">` primitives. The dead CSS
 *   rules (the detail-card wrapper rule, the three Overview-tab
 *   label / rank / value rules) collapse out of `globals.css`;
 *   the surviving rules (`.detail-panel`, `.detail-header`,
 *   `.detail-header-title`, `.detail-section`, `.tab-strip`,
 *   `.tab-button`, `.tab-button.active`, the
 *   `.detail-panel-backdrop` modal-backdrop rule) stay because
 *   they are still referenced.
 *
 * spec.md rule 4: presentation → taxonomy domain. Imports stay inside
 * the presentation layer to avoid the barrel cycle (the barrel
 * re-exports `TaxonomyTree`, which mounts this component).
 */
import { Fragment, useRef } from "react";
import { useEffect } from "react";
import { Badge, Card, IconButton } from "@taxa/design-system";
import type { Taxon } from "../domain/taxon";
import {
  rankLabel,
  scientificNameClass,
} from "./row-format";
import SearchTab from "./SearchTab";
import type { SearchTabStatus } from "./SearchTab";
import SynonymTab from "./SynonymTab";
import type { SynonymTabStatus } from "./SynonymTab";
import DistributionTab from "./DistributionTab";
import type { DistributionTabStatus } from "./DistributionTab";
import FolderTab from "./FolderTab";
import type {
  FolderCopyStatus,
  FolderCreateStatus,
  FolderOpenStatus,
  FolderTabStatus,
} from "./FolderTab";
import type { TreeSource, TreeState } from "./tree-state";

/** Tab key literal set — exactly four user-selected tabs.
 *  The pre-popup sticky rail carried six tabs (Overview +
 *  Search + Folder + Vernaculars + Synonyms + Distribution);
 *  the popup drops Overview + Vernaculars and reorders the
 *  remaining four to the user-selected order: Synonyms,
 *  Distribution, Search, Folder. */
export type DetailTabKey =
  | "synonyms"
  | "distribution"
  | "searches"
  | "folder";

/** Static tab definition — used by the tab strip renderer.
 *  Every popup tab is `available: true` (no deferred tabs in
 *  the popup; the four tabs are all real backing surfaces). */
export interface DetailTabDef {
  readonly key: DetailTabKey;
  readonly label: string;
  readonly icon: string;
  readonly available: boolean;
}

/** Canonical tab list. The user-selected order is:
 *  Synonyms → Distribution ("Location/Distribution") →
 *  Search ("Search links") → Folder ("Folder creation").
 *  All four tabs ship as real backing surfaces; the pre-popup
 *  "visibly mark unavailable later tabs without fake actions"
 *  policy no longer applies (the popup owns the four tabs as
 *  fully wired surfaces). */
export const DETAIL_TABS: readonly DetailTabDef[] = [
  { key: "synonyms", label: "Synonyms", icon: "history", available: true },
  { key: "distribution", label: "Distribution", icon: "public", available: true },
  { key: "searches", label: "Search", icon: "travel_explore", available: true },
  { key: "folder", label: "Folder", icon: "create_new_folder", available: true },
];

/** Default active tab key for any newly selected taxon.
 *  The pre-popup sticky rail picked Overview by default; the
 *  popup picks Synonyms (the first tab in the user-selected
 *  order) so a freshly selected taxon lands on the first
 *  user-selected tab. The legacy `web/state.js::activeTab` map
 *  still survives every selection; re-selecting a previously
 *  selected taxon lands the user on the last tab they used
 *  for it (or Synonyms for new taxa). */
export const DEFAULT_DETAIL_TAB: DetailTabKey = "synonyms";

export interface DetailPanelProps {
  readonly taxon: Taxon;
  readonly state: TreeState;
  readonly activeSource: TreeSource;
  /** Per-taxon active-tab memory. Owned by the parent
   *  `TaxonomyTree` so it survives across renders; this component
   *  reads + writes via the callbacks below. */
  readonly activeTab: DetailTabKey;
  readonly onTabChange: (tab: DetailTabKey) => void;
  readonly onClose: () => void;
  /** ODD-TDS-001 — per-taxon search-link status + retry callback.
   *  The parent (`TaxonomyTree`) owns the cache so re-selecting a
   *  previously selected taxon lands on the cached result without
   *  a round trip; the eager-fetch-on-selection contract fires
   *  the request the moment a taxon becomes the active selection,
   *  so the Search tab activation paints the rendered link grid
   *  instantly when the user clicks the tab. The retry callback
   *  re-issues the request and re-runs through the same status
   *  pipeline. */
  readonly searchStatus: SearchTabStatus;
  readonly onRetrySearches: () => void;
  /** ODD-TDSYN-001 — per-taxon synonyms status + retry
   *  callback. Mirrors the search-link wiring byte-for-byte:
   *  the parent owns the cache so re-selecting a previously
   *  selected taxon lands on the cached result without a round
   *  trip; the eager-fetch-on-selection contract fires the
   *  request the moment a taxon becomes the active selection.
   *  The cache SURVIVES source switches (the
   *  `/api/taxon/{id}/synonyms` endpoint is source-agnostic — the
   *  FastAPI server filters by `parent_id = taxon_id AND status
   *  != 'accepted'` regardless of the active tree source — so
   *  a stale cached payload remains valid under the new source).
   *  The retry callback re-issues the request and re-runs through
   *  the same status pipeline. */
  readonly synonymStatus: SynonymTabStatus;
  readonly onRetrySynonyms: () => void;
  /** ODD-TDDIST-001 — per-taxon distribution status + retry
   *  callback. Mirrors the search-link + synonyms wiring
   *  byte-for-byte: the parent owns the cache so re-selecting a
   *  previously selected taxon lands on the cached result
   *  without a round trip; the eager-fetch-on-selection contract
   *  fires the request the moment a taxon becomes the active
   *  selection. The cache SURVIVES source switches (the
   *  `/api/taxon/{id}/distribution` endpoint is source-agnostic
   *  — the FastAPI SQL filters by `taxon_id = ?` regardless of
   *  the active tree source — so a stale cached payload remains
   *  valid under the new source). The retry callback re-issues
   *  the request and re-runs through the same status pipeline. */
  readonly distributionStatus: DistributionTabStatus;
  readonly onRetryDistribution: () => void;
  /** ODD-TDFOLDER-001 — per-taxon folder status + retry /
   *  create / open / copy callbacks. Mirrors the search-link +
   *  synonyms + distribution wiring byte-for-byte: the parent
   *  (`TaxonomyTree`) owns the cache so re-selecting a previously
   *  selected taxon lands on the cached result without a round
   *  trip; the eager-fetch-on-selection contract fires the
   *  request the moment a taxon becomes the active selection.
   *  Unlike the other tabs the preview cache is source-AWARE
   *  (the materialize-preview endpoint walks the active
   *  source's parent column) so a source switch INVALIDATES
   *  the cache (`handleSourceChange` clears the
   *  `folderByTaxonId` map alongside the other source-bound
   *  resets). The retry callback re-issues the preview request;
   *  the create / open / copy callbacks drive the POST + open +
   *  clipboard actions. The `createArmed` gate enforces the
   *  explicit in-tab confirmation before POST materialize (per
   *  the ODD-TDFOLDER-001 user constraint: "Require an explicit
   *  confirmation before creating folders, intentionally safer
   *  than legacy"). */
  readonly folderStatus: FolderTabStatus;
  readonly onRetryFolderPreview: () => void;
  readonly onArmCreate: () => void;
  readonly onDisarmCreate: () => void;
  readonly onCreateResearchFolders: () => void;
  readonly onOpenResearchFolder: () => void;
  readonly onCopyResearchPath: () => void;
  readonly folderCreateStatus: FolderCreateStatus;
  readonly folderOpenStatus: FolderOpenStatus;
  readonly folderCopyStatus: FolderCopyStatus;
  readonly folderCreateArmed: boolean;
}

export default function DetailPanel({
  taxon,
  state,
  activeSource,
  activeTab,
  onTabChange,
  onClose,
  searchStatus,
  onRetrySearches,
  synonymStatus,
  onRetrySynonyms,
  distributionStatus,
  onRetryDistribution,
  folderStatus,
  onRetryFolderPreview,
  onArmCreate,
  onDisarmCreate,
  onCreateResearchFolders,
  onOpenResearchFolder,
  onCopyResearchPath,
  folderCreateStatus,
  folderOpenStatus,
  folderCopyStatus,
  folderCreateArmed,
}: DetailPanelProps): React.ReactElement {
  // ODD-TAPOPUP-001 — the popup's header is minimal: the
  // scientific-name `<h2>` + the close IconButton. The
  // pre-popup sticky rail carried the `line-through
  // opacity-70` extinct treatment on the taxon name; the
  // popup drops the extinct affordance (the popup header is
  // minimal + the extinct classification is a downstream
  // concern; the future slice can re-add the affordance as
  // a header badge if needed).

  // ODD-TAPOPUP-002 — capture the trigger element so the
  // unmount cleanup can restore focus to the per-row kebab
  // button that opened the popup (WAI-ARIA Authoring
  // Practices dialog pattern). The trigger is captured
  // BEFORE the close button steals focus, so the cleanup
  // restores the user's original focus target on close.
  const triggerRef = useRef<HTMLElement | null>(null);

  // ODD-TAPOPUP-002 — focus on open (close button is the
  // canonical WAI-ARIA first-focus target) + restore focus
  // on unmount. The IconButton primitive does not forward
  // refs, so the focus call queries the DOM via the
  // `data-action="close-detail"` selector (the close button
  // is the only element with that attribute in the popup, so
  // the query is unambiguous). The query runs inside
  // `useEffect` so the button is in the DOM when the effect
  // fires; the cleanup runs on unmount and restores focus to
  // the trigger element captured at mount time.
  useEffect(() => {
    triggerRef.current = document.activeElement as HTMLElement | null;
    const closeButton = document.querySelector<HTMLButtonElement>(
      '[data-action="close-detail"]',
    );
    closeButton?.focus();
    return () => {
      triggerRef.current?.focus();
    };
  }, []);

  // ODD-TAPOPUP-002 — Escape closes the popup + Tab / Shift+Tab
  // cycles focus inside the dialog (WAI-ARIA focus-trap
  // pattern). The Tab branch queries the dialog for focusable
  // elements and wraps focus from the last back to the first
  // (and vice versa for Shift+Tab) so the user's keyboard
  // tab order stays inside the popup (Tab from the close
  // button would otherwise jump to the next focusable
  // element on the page — the tree rows — silently escaping
  // the modal context).
  useEffect(() => {
    const onKeyDown = (ev: KeyboardEvent): void => {
      if (ev.key === "Escape") {
        onClose();
        return;
      }
      if (ev.key === "Tab") {
        const dialog = document.getElementById("detail-panel");
        if (!dialog) return;
        const focusables = dialog.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        );
        if (focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (!first || !last) return;
        const active = document.activeElement as HTMLElement | null;
        if (ev.shiftKey) {
          if (active === first || !dialog.contains(active)) {
            ev.preventDefault();
            last.focus();
          }
        } else {
          if (active === last || !dialog.contains(active)) {
            ev.preventDefault();
            first.focus();
          }
        }
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  // The `state` prop is consumed by the Folder tab's preview
  // payload (the materialize preview walks the source-aware
  // parent chain); the unused-vars lint would flag it so we
  // reference it in a no-op to keep the prop wired.
  void state;

  return (
    <>
      {/* ODD-TAPOPUP-001 — modal backdrop. The backdrop sits
          behind the dialog content (z-index lower than the
          dialog host), covers the full viewport, and is a
          sibling of the dialog content so clicking it does
          not bubble to the dialog. Clicking the backdrop
          closes the popup (the same `onClose()` callback the
          close IconButton + Escape use). */}
      <div
        className="detail-panel-backdrop"
        onClick={onClose}
        aria-hidden="true"
        data-detail-panel-backdrop=""
      />
      <div
        id="detail-panel"
        className="detail-panel detail-panel-dialog-host"
        data-detail-panel=""
        data-detail-panel-source={activeSource}
        data-detail-panel-tab={activeTab}
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-panel-title"
        aria-label={`Selected taxon: ${taxon.name}`}
        // ODD-TAPOPUP-002 — outside-click dismissal. The host
        // covers the full viewport (`position: fixed; inset: 0`)
        // and the Card is centered inside; clicks on the host
        // area OUTSIDE the Card close the popup. The
        // `e.target === e.currentTarget` guard ensures clicks
        // INSIDE the Card (which bubble up to the host via
        // React's synthetic event system) do NOT close the
        // popup — the only legitimate dismissal surfaces are
        // the close IconButton + Escape + this outside-click
        // handler.
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <Card
          variant="default"
          // ODD-TAPOPUP-002 — responsive Card dimensions.
          // `w-full` makes the Card fill the host's centered
          // flexbox at narrow viewports (so the dialog touches
          // the viewport edges via the narrow-viewport
          // `@media (max-width: 768px) { .detail-panel { padding: 0; } }`
          // override); `max-w-[720px]` caps the Card width at a
          // sensible reading width on wide viewports; the
          // existing `max-h-[calc(90vh-2px)]` keeps the Card
          // inside the viewport vertically.
          className="flex flex-col overflow-hidden w-full max-w-[720px] h-auto max-h-[calc(90vh-2px)] rounded-2xl"
        >
          <div className="detail-header">
            <div className="flex-1 min-w-0">
              <div className="detail-header-badges flex items-center gap-3 mb-1 flex-wrap">
                <Badge variant="primary" uppercase={true}>
                  {rankLabel(taxon.rank)}
                </Badge>
              </div>
              <h2
                id="detail-panel-title"
                className={`detail-header-title font-display text-display ${scientificNameClass(taxon.rank)}`.trim()}
                data-detail-title=""
              >
                {taxon.name}
              </h2>
              {taxon.authorship ? (
                <p
                  className="text-on-surface-variant mt-1 text-body-sm"
                  data-detail-authorship=""
                >
                  {taxon.authorship}
                </p>
              ) : null}
            </div>
            <IconButton
              variant="subtle"
              aria-label="Hide details"
              title="Hide details"
              data-action="close-detail"
              onClick={onClose}
            >
              <span aria-hidden="true" className="material-symbols-outlined">
                close
              </span>
            </IconButton>
          </div>
          <div
            className="tab-strip"
            role="tablist"
            aria-label="Taxon detail tabs"
            data-detail-tab-strip=""
          >
            {DETAIL_TABS.map((t) => {
              const isActive = t.key === activeTab;
              const labelAvail = `Show ${t.label} tab`;
              return (
                <button
                  key={t.key}
                  type="button"
                  className={`tab-button${isActive ? " active" : ""}`}
                  data-tab={t.key}
                  data-tab-available={t.available ? "true" : "false"}
                  aria-pressed={isActive ? "true" : "false"}
                  role="tab"
                  title={labelAvail}
                  aria-label={labelAvail}
                  onClick={() => {
                    if (t.available) onTabChange(t.key);
                  }}
                >
                  <span
                    aria-hidden="true"
                    className="material-symbols-outlined text-[16px]"
                  >
                    {t.icon}
                  </span>
                  {t.label}
                </button>
              );
            })}
          </div>
          <div
            className={`detail-section ${activeTab === "searches" ? "searches-tab" : activeTab === "folder" ? "folder-tab" : activeTab === "synonyms" ? "synonyms-tab" : activeTab === "distribution" ? "distribution-tab" : "overview-tab"}`}
            data-tab-content={activeTab}
          >
            {activeTab === "searches" ? (
              <SearchTab status={searchStatus} onRetry={onRetrySearches} />
            ) : activeTab === "folder" ? (
              <FolderTab
                status={folderStatus}
                onRetryPreview={onRetryFolderPreview}
                onCreate={onCreateResearchFolders}
                onOpen={onOpenResearchFolder}
                onCopy={onCopyResearchPath}
                createStatus={folderCreateStatus}
                openStatus={folderOpenStatus}
                copyStatus={folderCopyStatus}
                createArmed={folderCreateArmed}
                onArmCreate={onArmCreate}
                onDisarmCreate={onDisarmCreate}
              />
            ) : activeTab === "synonyms" ? (
              <SynonymTab
                status={synonymStatus}
                onRetry={onRetrySynonyms}
              />
            ) : activeTab === "distribution" ? (
              <DistributionTab
                status={distributionStatus}
                onRetry={onRetryDistribution}
              />
            ) : (
              // Unreachable — the four `available: true` tabs
              // cover every branch — but TypeScript needs the
              // fallback so the discriminated union is
              // exhausted.
              null
            )}
          </div>
        </Card>
      </div>
    </>
  );
}

// `Fragment` is imported above for future use (the popup's
// backdrop + dialog sibling structure is already inlined
// inside `DetailPanel`; the import is preserved so a future
// slice can compose additional siblings without re-importing
// the primitive).
void Fragment;
