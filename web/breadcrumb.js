// Breadcrumb renderer. Walks the source-aware parent chain from
// state.focused up to the root, rendering clickable segments for each
// ancestor and plain text for the current position. Reads from
// state.cache only — never triggers a fetch itself.

import { state } from "./state.js";
import { el } from "./dom.js";
import { scientificNameClass } from "./format.js";

function renderBreadcrumb() {
  const nav = document.querySelector("#breadcrumb");
  if (!state.focused) {
    nav.replaceChildren();
    return;
  }
  // Walk up the source-aware parent chain. The three views use three
  // independent hierarchies (parent_id, worms_parent_id, freshwater_parent_id)
  // — walking parent_id for a freshwater taxon would return NULL on the
  // first step (CSV rows have parent_id IS NULL) and the breadcrumb would
  // render only the focused taxon with no ancestors. Same risk for WoRMS:
  // a CoL-matched WoRMS taxon's parent_id points at the CoL backbone, not
  // at the WoRMS chain.
  const src = state.treeSource;
  const parentIdOf = (t) => {
    if (src === "worms") return t.worms_parent_id;
    if (src === "freshwater") return t.freshwater_parent_id;
    return t.parent_id;
  };
  const pathSegments = [];
  let currentId = state.focused;
  let safety = 30; // hard cap to avoid infinite loops on data corruption
  while (currentId && safety-- > 0) {
    const node = state.cache.get(currentId);
    if (!node) break;
    pathSegments.unshift({
      id: currentId,
      name: node.taxon.scientific_name,
      rank: node.taxon.rank,
    });
    currentId = parentIdOf(node.taxon);
  }
  if (pathSegments.length === 0) {
    nav.replaceChildren();
    return;
  }

  const frag = document.createDocumentFragment();

  // Home icon (clickable — clears focus).
  frag.append(
    el(
      "button",
      {
        class: "hover:text-primary transition-colors flex items-center gap-1",
        "data-action": "focus-home",
        title: "Clear focus (go to tree root)",
      },
      el("span", { class: "material-symbols-outlined text-[16px]" }, "home"),
    ),
  );
  // Each path segment: intermediate ones are clickable buttons; the last is
  // the current position (rendered as text, not clickable).
  for (let i = 0; i < pathSegments.length; i++) {
    const seg = pathSegments[i];
    frag.append(
      el(
        "span",
        { class: "material-symbols-outlined text-[14px]" },
        "chevron_right",
      ),
    );
    if (i === pathSegments.length - 1) {
      frag.append(
        el("span", { class: `text-on-surface font-medium ${scientificNameClass(seg.rank)}` }, seg.name),
      );
    } else {
      frag.append(
        el(
          "button",
          {
            class: `hover:text-primary transition-colors ${scientificNameClass(seg.rank)}`,
            "data-action": "focus-segment",
            "data-taxon-id": seg.id,
          },
          seg.name,
        ),
      );
    }
  }
  nav.replaceChildren(frag);
}

export { renderBreadcrumb };
