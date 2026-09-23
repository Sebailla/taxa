"use client";

/**
 * DetailPanel — native-style selected-taxon detail panel (ODD-TDO-001).
 *
 * Client island rendered inside the existing `TaxonomyTree` surface.
 * Mounts when the user selects a tree taxon (via the kebab "Search
 * online" item, the leaf disclosure click, or the breadcrumb focus
 * handler), renders the native-style Overview tab, and clears when
 * the user closes the panel or switches sources.
 *
 * ODD-TDO-001 — port of the legacy `web/detail.js::renderDetailPanel`
 * into the React tree:
 *   - The Overview tab renders native identity (rank/name/authorship,
 *     status, species count, source-aware ancestor chain) and source
 *     affordances (CoL-only badge, WoRMS cross-link). The legacy
 *     `web/detail.js::renderOverview` is the byte-for-byte oracle;
 *     this component mirrors its visual + a11y contract while
 *     composing the canonical `Taxon` projection + the row-format +
 *     breadcrumb-path helpers.
 *   - The tab strip carries every legacy tab (`Overview` / `Search` /
 *     `Folder` / `Vernaculars` / `Synonyms` / `Distribution`) but
 *     only the Overview tab is rendered as a real body. The other
 *     tabs render as `disabled` + `aria-disabled="true"` buttons
 *     with a clearly unavailable label so the user sees the future
 *     surface without a fake action.
 *   - Per-taxon active-tab memory lives at the parent
 *     `TaxonomyTree` level; this component is the pure renderer.
 *     The parent owns the `Map<number, DetailTabKey>` so a future
 *     slice can grow the tab list without restructuring the
 *     detail panel contract.
 *   - Closing the panel calls `onClose()` which the parent maps to
 *     `setSelected(null)` (mirrors the legacy `close-detail`
 *     data-action handler in `web/nav.js`).
 *   - The Close button + the extinct treatment + the realm tint
 *     match the legacy oracle byte-for-byte; the parent chain is
 *     reconstructed from the canonical source-aware walker
 *     `walkBreadcrumbForSource` so the chain never crosses source
 *     boundaries (CoL ↔ WoRMS ↔ Freshwater).
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
 *   `.tab-button`, `.tab-button.active`, the `.detail-panel
 *   [data-realm="X"] .scientific-name` realm tint cascade) stay
 *   because they are still referenced.
 *
 *   The `.rank-badge` standalone rule + the `.authorship`
 *   standalone rule stay too — the former is still consumed by the
 *   `TaxonomyTree.tsx` search-dropdown rank chip, the latter is
 *   still consumed by `SynonymTab.tsx` synonym-item rows. They
 *   stay in the `TAXONOMY_OWNED_BY_3C_B` whitelist the
 *   chain-topology guard pins.
 *
 * spec.md rule 4: presentation → taxonomy domain. Imports stay inside
 * the presentation layer to avoid the barrel cycle (the barrel
 * re-exports `TaxonomyTree`, which mounts this component).
 */
import { Fragment } from "react";
import type { ReactNode } from "react";
import { Badge, Card, IconButton, Text } from "@taxa/design-system";
import type { Taxon } from "../domain/taxon";
import {
  rankLabel,
  realmForPath,
  scientificNameClass,
  speciesCountBadge,
  statusDotDescriptor,
} from "./row-format";
import SearchTab from "./SearchTab";
import type { SearchTabStatus } from "./SearchTab";
import SynonymTab from "./SynonymTab";
import type { SynonymTabStatus } from "./SynonymTab";
import VernacularTab from "./VernacularTab";
import type { VernacularTabStatus } from "./VernacularTab";
import DistributionTab from "./DistributionTab";
import type { DistributionTabStatus } from "./DistributionTab";
import FolderTab from "./FolderTab";
import type {
  FolderCopyStatus,
  FolderCreateStatus,
  FolderOpenStatus,
  FolderTabStatus,
} from "./FolderTab";
import { walkBreadcrumbForSource } from "./breadcrumb-path";
import type { BreadcrumbSegment } from "./breadcrumb-path";
import type { TreeSource, TreeState } from "./tree-state";

/** Tab key literal set — every legacy tab carries an entry; the
 *  React slice ships only the `overview` body in this PR — the rest
 *  of the keys stay reserved so a future slice can grow the tab
 *  surface without a refactor of the per-taxon memory map.
 *  Declared before `DetailTabDef` so the type alias can reference
 *  the literal set without a circular dependency. */
export type DetailTabKey =
  | "overview"
  | "searches"
  | "folder"
  | "vernaculars"
  | "synonyms"
  | "distribution";

/** Static tab definition — used by the tab strip renderer. The
 *  `available` flag is `false` for tabs whose body has not shipped
 *  in the current slice so the user sees them as clearly
 *  unavailable rather than silently wired to a placeholder. */
export interface DetailTabDef {
  readonly key: DetailTabKey;
  readonly label: string;
  readonly icon: string;
  readonly available: boolean;
}

/** Canonical tab list. Mirrors the legacy `web/detail.js::tabs` array
 *  order byte-for-byte (Overview → Search → Folder → Vernaculars →
 *  Synonyms → Distribution) so the React cutover's tab strip matches
 *  the legacy oracle. ODD-TDS-001 enables the `searches` tab — the
 *  server-composed search-engine links body ships as a real
 *  rendering surface. ODD-TDV-001 enables `vernaculars`. ODD-TDSYN-001
 *  enables `synonyms` — the canonical Synonym tab body renders the
 *  server-composed historical-name rows (rank chip + scientific name
 *  + optional authorship) under the native "Synonyms" header.
 *  ODD-TDDIST-001 enables `distribution` — the canonical Distribution
 *  tab body renders the server-composed geographic-range rows
 *  (establishment-means chip + area) under the native "Distribution"
 *  header. ODD-TDFOLDER-001 enables `folder` — the canonical
 *  Folder tab body renders the server-composed materialize-
 *  preview payload (line-by-line segment list with ✓ / +
 *  markers, count summary, info banner, conditional Create
 *  row with explicit in-tab confirmation gate, conditional
 *  Open + Copy path-actions row, and inline success / error
 *  states — all wired through the canonical FolderTab
 *  presentation component). */
export const DETAIL_TABS: readonly DetailTabDef[] = [
  { key: "overview", label: "Overview", icon: "info", available: true },
  { key: "searches", label: "Search", icon: "travel_explore", available: true },
  { key: "folder", label: "Folder", icon: "create_new_folder", available: true },
  { key: "vernaculars", label: "Vernaculars", icon: "translate", available: true },
  { key: "synonyms", label: "Synonyms", icon: "history", available: true },
  { key: "distribution", label: "Distribution", icon: "public", available: true },
];

/** Default active tab key for any newly selected taxon. The legacy
 *  oracle picks Overview by default whenever the Overview tab is
 *  present; this slice always has it (the suppressed-data branch
 *  ships in a future PR), so the default is fixed to `"overview"`. */
export const DEFAULT_DETAIL_TAB: DetailTabKey = "overview";

export interface DetailPanelProps {
  readonly taxon: Taxon;
  readonly state: TreeState;
  readonly activeSource: TreeSource;
  /** Per-taxon active-tab memory. Owned by the parent
   *  `TaxonomyTree` so it survives across renders; this component
   *  reads + writes via the callbacks below. */
  readonly activeTab: DetailTabKey;
  readonly onTabChange: (tab: DetailTabKey) => void;
  /** Source-aware breadcrumb segment activation — wired through the
   *  canonical `handleFocusSegment` on the parent so the Overview
   *  chain shares the same breadcrumb walker + focus + select
   *  primitive the visible breadcrumb uses. */
  readonly onFocusSegment: (id: number) => void;
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
  /** ODD-TDV-001 — per-taxon vernaculars status + retry callback.
   *  Mirrors the search-link wiring byte-for-byte: the parent owns
   *  the cache so re-selecting a previously selected taxon lands
   *  on the cached result without a round trip; the eager-fetch-
   *  on-selection contract fires the request the moment a taxon
   *  becomes the active selection. The cache SURVIVES source
   *  switches (the `/api/taxon/{id}/vernaculars` endpoint is
   *  source-agnostic, so a stale cached payload remains valid
   *  under the new source). The retry callback re-issues the
   *  request and re-runs through the same status pipeline. */
  readonly vernacularStatus: VernacularTabStatus;
  readonly onRetryVernaculars: () => void;
  /** ODD-TDSYN-001 — per-taxon synonyms status + retry callback.
   *  Mirrors the search-link + vernaculars wiring byte-for-byte:
   *  the parent owns the cache so re-selecting a previously
   *  selected taxon lands on the cached result without a round
   *  trip; the eager-fetch-on-selection contract fires the
   *  request the moment a taxon becomes the active selection. The
   *  cache SURVIVES source switches (the
   *  `/api/taxon/{id}/synonyms` endpoint is source-agnostic — the
   *  FastAPI server filters by `parent_id = taxon_id AND status !=
   *  'accepted'` regardless of the active tree source — so a
   *  stale cached payload remains valid under the new source).
   *  The retry callback re-issues the request and re-runs through
   *  the same status pipeline. */
  readonly synonymStatus: SynonymTabStatus;
  readonly onRetrySynonyms: () => void;
  /** ODD-TDDIST-001 — per-taxon distribution status + retry
   *  callback. Mirrors the search-link + vernaculars +
   *  synonyms wiring byte-for-byte: the parent owns the cache
   *  so re-selecting a previously selected taxon lands on the
   *  cached result without a round trip; the
   *  eager-fetch-on-selection contract fires the request the
   *  moment a taxon becomes the active selection. The cache
   *  SURVIVES source switches (the
   *  `/api/taxon/{id}/distribution` endpoint is
   *  source-agnostic — the FastAPI SQL filters by
   *  `taxon_id = ?` regardless of the active tree source — so
   *  a stale cached payload remains valid under the new
   *  source). The retry callback re-issues the request and
   *  re-runs through the same status pipeline. */
  readonly distributionStatus: DistributionTabStatus;
  readonly onRetryDistribution: () => void;
  /** ODD-TDFOLDER-001 — per-taxon folder status + retry /
   *  create / open / copy callbacks. Mirrors the search-link +
   *  vernaculars + synonyms + distribution wiring byte-for-
   *  byte: the parent (`TaxonomyTree`) owns the cache so re-
   *  selecting a previously selected taxon lands on the cached
   *  result without a round trip; the eager-fetch-on-selection
   *  contract fires the request the moment a taxon becomes the
   *  active selection. Unlike the other tabs the preview cache
   *  is source-AWARE (the materialize-preview endpoint walks
   *  the active source's parent column) so a source switch
   *  INVALIDATES the cache (`handleSourceChange` clears the
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
  onFocusSegment,
  onClose,
  searchStatus,
  onRetrySearches,
  vernacularStatus,
  onRetryVernaculars,
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
  const realm = realmForPath(taxon.path);
  const extinctCls = taxon.is_extinct ? "line-through opacity-70" : "";
  const statusDot = statusDotDescriptor(taxon.status);
  const statusText =
    taxon.status === "accepted"
      ? "Accepted"
      : taxon.status === "synonym"
        ? "Synonym"
        : "Unknown";
  const countBadge = speciesCountBadge(taxon.species_count);
  const countDisplay =
    countBadge !== ""
      ? countBadge
      : taxon.species_count === null || taxon.species_count === undefined
        ? "—"
        : "0";
  // Source-aware ancestor chain — reuses the canonical walker so the
  // chain never crosses source boundaries and never fabricates
  // WoRMS-only edges. The walker reads from the cached `nodes`
  // map (the same source-aware projection the breadcrumb above the
  // tree uses), so a click on a segment expands the right
  // ancestors + focuses + selects that segment.
  const chainSegments = walkBreadcrumbForSource(taxon.id, activeSource, state);

  return (
    <aside
      id="detail-panel"
      className="detail-panel detail-panel-host"
      data-detail-panel=""
      data-detail-panel-source={activeSource}
      data-detail-panel-tab={activeTab}
      data-realm={realm}
      data-extinct={taxon.is_extinct ? "true" : undefined}
      aria-label={`Selected taxon: ${taxon.name}`}
    >
      <Card
        variant="default"
        className={`flex flex-col overflow-hidden h-auto max-h-[calc(90vh-2px)] rounded-2xl ${extinctCls}`.trim()}
      >
        <div className="detail-header">
          <div className="flex-1 min-w-0">
            <div className="detail-header-badges flex items-center gap-3 mb-1 flex-wrap">
              <Badge variant="primary" uppercase={true}>
                {rankLabel(taxon.rank)}
              </Badge>
              <Badge variant="subtle" uppercase={true}>
                {taxon.status ?? "unknown"}
              </Badge>
              {taxon.is_extinct ? (
                <Badge
                  variant="warning"
                  uppercase={true}
                  data-detail-extinct=""
                >
                  † Extinct
                </Badge>
              ) : null}
              {activeSource === "col" && taxon.coldp_id && !taxon.worms_id ? (
                <Badge
                  variant="subtle"
                  uppercase={true}
                  title={`CoL-only — ColDP ID ${taxon.coldp_id} (no WoRMS match).`}
                  data-detail-source-badge="col-only"
                >
                  CoL · {taxon.coldp_id}
                </Badge>
              ) : null}
              {taxon.worms_id && activeSource !== "col" ? (
                <a
                  href={`https://www.marinespecies.org/aphia.php?p=taxdetails&id=${taxon.worms_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rank-badge uppercase tracking-[0.1em] px-2 py-0.5 rounded text-accent bg-accent/10 hover:bg-accent/20 transition-colors no-underline"
                  title={`WoRMS AphiaID ${taxon.worms_id} — open in WoRMS`}
                  data-detail-source-badge="worms-link"
                >
                  WoRMS · {taxon.worms_id}
                </a>
              ) : null}
            </div>
            <h2
              className={`detail-header-title font-display text-display ${scientificNameClass(taxon.rank)} ${extinctCls}`.trim()}
              data-detail-title=""
            >
              {taxon.name}
            </h2>
            {taxon.authorship ? (
              <Text
                variant="body-sm"
                as="p"
                className="text-on-surface-variant mt-1"
                data-detail-authorship=""
              >
                {taxon.authorship}
              </Text>
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
            const labelAvail = t.available
              ? `Show ${t.label} tab`
              : `${t.label} tab (not yet implemented)`;
            return (
              <button
                key={t.key}
                type="button"
                className={`tab-button${isActive ? " active" : ""}`}
                data-tab={t.key}
                data-tab-available={t.available ? "true" : "false"}
                aria-pressed={isActive ? "true" : "false"}
                disabled={!t.available}
                aria-disabled={t.available ? undefined : "true"}
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
          className={`detail-section ${activeTab === "searches" ? "searches-tab" : activeTab === "folder" ? "folder-tab" : activeTab === "vernaculars" ? "vernaculars-tab" : activeTab === "synonyms" ? "synonyms-tab" : activeTab === "distribution" ? "distribution-tab" : "overview-tab"}`}
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
          ) : activeTab === "vernaculars" ? (
            <VernacularTab
              status={vernacularStatus}
              onRetry={onRetryVernaculars}
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
            renderOverview({
              taxon,
              chainSegments,
              statusText,
              statusDotClass: statusDot.className,
              statusTitle: statusDot.title,
              countDisplay,
              onFocusSegment,
            })
          )}
        </div>
      </Card>
    </aside>
  );
}

interface OverviewArgs {
  readonly taxon: Taxon;
  readonly chainSegments: readonly BreadcrumbSegment[];
  readonly statusText: string;
  readonly statusDotClass: string;
  readonly statusTitle: string;
  readonly countDisplay: string;
  readonly onFocusSegment: (id: number) => void;
}

function renderOverview(args: OverviewArgs): ReactNode {
  const {
    taxon,
    chainSegments,
    statusText,
    statusDotClass,
    statusTitle,
    countDisplay,
    onFocusSegment,
  } = args;

  return (
    <>
      <h3 className="overview-tab-heading">
        <span
          aria-hidden="true"
          className="material-symbols-outlined text-[16px]"
        >
          info
        </span>
        Overview
      </h3>
      <Badge
        variant="primary"
        uppercase={true}
        data-detail-overview-rank=""
      >
        {rankLabel(taxon.rank)}
      </Badge>
      <dl className="overview-grid" data-detail-overview-grid="">
        <div className="overview-row" data-detail-overview-row="scientific-name">
          <dt>
            <Text variant="caption" as="span">
              Scientific name:
            </Text>
          </dt>
          <dd data-detail-overview-field="scientific-name">
            <Text
              variant="body"
              as="span"
              className={`font-display text-display ${scientificNameClass(taxon.rank)}`}
            >
              {taxon.name}
            </Text>
          </dd>
        </div>
        <div className="overview-row" data-detail-overview-row="status">
          <dt>
            <Text variant="caption" as="span">
              Status:
            </Text>
          </dt>
          <dd
            className="inline-flex items-center gap-2"
            data-detail-overview-field="status"
          >
            <span
              className={`status-dot ${statusDotClass.replace(/^status-dot\s*/, "")}`}
              role="img"
              aria-label={statusTitle}
              title={statusTitle}
              data-detail-status-dot=""
            />
            <span data-detail-status-text="">{statusText}</span>
          </dd>
        </div>
        {taxon.authorship ? (
          <div className="overview-row" data-detail-overview-row="authorship">
            <dt>
              <Text variant="caption" as="span">
                Authorship:
              </Text>
            </dt>
            <dd data-detail-overview-field="authorship">
              <Text variant="body" as="span" className="text-on-surface-variant">
                ({taxon.authorship})
              </Text>
            </dd>
          </div>
        ) : null}
        <div className="overview-row" data-detail-overview-row="species-count">
          <dt>
            <Text variant="caption" as="span">
              Species count:
            </Text>
          </dt>
          <dd data-detail-overview-field="species-count">
            <Text variant="body" as="span">
              {countDisplay}
            </Text>
          </dd>
        </div>
        {chainSegments.length > 1 ? (
          <div className="overview-row" data-detail-overview-row="parent-chain">
            <dt>
              <Text variant="caption" as="span">
                Parent chain:
              </Text>
            </dt>
            <dd
              className="overview-chain"
              data-detail-overview-field="parent-chain"
            >
              {renderChain(chainSegments, onFocusSegment)}
            </dd>
          </div>
        ) : null}
      </dl>
    </>
  );
}

function renderChain(
  segments: readonly BreadcrumbSegment[],
  onFocusSegment: (id: number) => void,
): ReactNode {
  const items: ReactNode[] = [];
  segments.forEach((seg, i) => {
    items.push(
      <button
        key={`seg-${seg.id}`}
        type="button"
        className={`overview-chain-segment ${scientificNameClass(seg.rank)}`}
        data-action="focus-segment"
        data-taxon-id={seg.id}
        data-detail-chain-segment={seg.id}
        data-detail-chain-rank={seg.rank}
        onClick={() => onFocusSegment(seg.id)}
      >
        {seg.name}
      </button>,
    );
    if (i < segments.length - 1) {
      items.push(
        <span
          key={`chev-${seg.id}`}
          aria-hidden="true"
          className="material-symbols-outlined text-[14px] text-on-surface-variant"
        >
          chevron_right
        </span>,
      );
    }
  });
  return <Fragment>{items}</Fragment>;
}
