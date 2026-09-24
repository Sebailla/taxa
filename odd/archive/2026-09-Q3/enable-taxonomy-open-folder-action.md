# Enable the taxonomy tree Open folder action

## Objective
Restore the enabled native kebab action that selects a materialized taxon and opens its Folder detail tab.

## Rationale
The React Folder tab and desktop folder handlers are complete, but the matching row kebab menu item remains artificially disabled. This diverges from the legacy behavior and hides an available workflow.

## Scope
- Enable the existing `open-folder-tab` menu item only for materialized taxa.
- Route the action through the existing selected-taxon and per-taxon active-tab state.
- Preserve menu dismissal, keyboard behavior, source resets, and the materialization predicate.
- Update focused structural/interaction evidence.

## Non-goals
- Folder API or renderer changes.
- New CSS, dependencies, icons, or client/server boundaries.
- Changing legacy sources, materialization propagation, or any other kebab action.

## Allowed edit surfaces
- `src/modules/taxonomy/presentation/TreeRow.tsx`
- `src/modules/taxonomy/presentation/TaxonomyTree.tsx`
- `tests/test_visible_taxonomy_tree.py`
- `odd/tasks/enable-taxonomy-open-folder-action.md`

## Tasks
- [x] ODD-OPENFOLDER-001 Enable and route the existing tree kebab action.
- [x] ODD-OPENFOLDER-002 Independently verify the focused behavior and record delivery evidence.

## Acceptance criteria
- Materialized rows expose an enabled, accessible Open folder menu item.
- Activating it closes the kebab, selects/focuses the taxon, and makes Folder the active detail tab.
- Non-materialized rows do not expose the action.
- Existing menu accessibility and dismissal behavior remain intact.
- Focused tests and static checks pass.

## Delivery evidence
- `src/modules/taxonomy/presentation/TreeRow.tsx`: removed `disabled` + `aria-disabled="true"` from the `data-action="open-folder-tab"` kebab item; kept the `isMaterialized ? ... : null` predicate intact so non-materialized rows do not expose the action; updated the surrounding docstring + per-row comment.
- `src/modules/taxonomy/presentation/TaxonomyTree.tsx`: added an `open-folder-tab` branch in `handleKebabAction` that pins `perTaxonActiveTab[id] = "folder"` via the functional updater, then calls `handleSelect(id)` to focus + select + close the kebab + bump the pulse nonce — mirroring `web/nav.js::open-folder-tab` byte-for-byte.
- `tests/test_visible_taxonomy_tree.py`: replaced the stale `test_tree_row_open_folder_is_still_deferred` with `test_tree_row_open_folder_kebab_is_enabled_for_materialized_rows`; added `test_taxonomy_tree_handle_kebab_action_routes_open_folder_tab`, whose dispatch assertion is anchored to the actual `open-folder-tab` branch.
- Independent verification approved the implementation: 11 focused kebab tests, the 194-test tree suite, 168 module-boundary/purity/import tests, and strict TypeScript all passed. The Impeccable detector found no UI issues and LSP diagnostics were clean for both changed components. Live runtime smoke was not run because it requires starting local services.
- Work-unit commit: `feat(taxonomy): enable tree open folder action`.
