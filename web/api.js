// Fetch helpers. Every server call goes through api(); the loader
// functions (loadTaxon, loadChildren) wrap api() with the shared cache so
// repeat renders don't re-hit the network.

import { state, API } from "./state.js";

async function api(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText} for ${path}`);
  return r.json();
}

async function loadTaxon(id) {
  const node = state.cache.get(id);
  if (node) return node.taxon;
  const taxon = await api(`/api/taxon/${id}`);
  state.cache.set(id, { taxon, children: null });
  return taxon;
}

async function loadChildren(id) {
  let node = state.cache.get(id);
  if (!node) {
    await loadTaxon(id);
    node = state.cache.get(id);
  }
  if (node.children === null) {
    // In WoRMS view the tree walks the WoRMS hierarchy (worms_parent_id),
    // which is independent of CoL's parent_id. This lets Biota → Animalia
    // → Mollusca → ... drill through the marine tree even though those
    // CoL rows have parent_id pointing at Eukaryota, not Biota.
    // In Freshwater view the tree walks the freshwater overlay
    // (freshwater_parent_id); the freshwater rows are isolated, so the
    // CoL/WoRMS branches return empty for a freshwater taxon and vice
    // versa. Without `source=freshwater` here, clicking the freshwater
    // root fetches its CoL children (zero matches) and the tree looks
    // empty.
    let src = "";
    if (state.treeSource === "worms") src = "&source=worms";
    else if (state.treeSource === "freshwater") src = "&source=freshwater";
    let children = await api(`/api/taxon/${id}/children?limit=200${src}`);
    if (state.extantOnly) children = children.filter((t) => !t.is_extinct);
    node.children = children;
    for (const c of children) {
      if (!state.cache.has(c.id)) {
        state.cache.set(c.id, { taxon: c, children: null });
      }
    }
  }
  return node.children;
}

export { api, loadTaxon, loadChildren };
