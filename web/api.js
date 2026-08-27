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

// POST /api/taxon/{id}/materialize — asks the server to create the
// root→taxon folder structure under RESEARCH_DIR (default ./Research). The
// endpoint is idempotent and returns how many folders it created vs found.
// We use POST (not GET) because the call has side effects on the server's
// filesystem. Errors are surfaced as a thrown Error so the caller (nav.js)
// can show them in a toast.
//
// `source` selects which hierarchy to walk — same semantics as
// `loadChildren` below and `/api/taxon/{id}/children?source=...`. The
// caller passes `state.treeSource` (always one of "col" | "worms" |
// "freshwater"); api.js doesn't import state so it stays pure. For WoRMS
// and Freshwater views, the rows have parent_id=NULL with the real
// hierarchy in `worms_parent_id` / `freshwater_parent_id` — passing the
// matching source lets the server walk the right column.
async function materializeResearch(taxonId, source = "col") {
  const r = await fetch(
    API +
      `/api/taxon/${taxonId}/materialize?source=${encodeURIComponent(source)}`,
    { method: "POST" },
  );
  if (!r.ok) {
    let detail = "";
    try {
      const body = await r.json();
      detail = body.detail || "";
    } catch {
      // body wasn't JSON — fall back to statusText.
    }
    throw new Error(
      `materialize ${taxonId} failed: ${r.status}${detail ? " " + detail : ""}`,
    );
  }
  return r.json();
}

// GET /api/taxon/{id}/materialize-preview — reports what the corresponding
// POST WOULD do, without side effects. The frontend uses it to render the
// line-by-line preview inside the materialize modal BEFORE the user
// confirms; the server side does not touch the filesystem. We use GET
// (not POST) because the call is purely informational. Errors are
// surfaced as a thrown Error so the caller (dom.js::openMaterializeModal)
// can show them in the modal.
//
// `source` mirrors the POST argument — see `materializeResearch` above.
async function previewMaterialize(taxonId, source = "col") {
  const r = await fetch(
    API +
      `/api/taxon/${taxonId}/materialize-preview?source=${encodeURIComponent(source)}`,
  );
  if (!r.ok) {
    let detail = "";
    try {
      const body = await r.json();
      detail = body.detail || "";
    } catch {
      // body wasn't JSON — fall back to statusText.
    }
    throw new Error(
      `materialize-preview ${taxonId} failed: ${r.status}${detail ? " " + detail : ""}`,
    );
  }
  return r.json();
}

// POST /api/taxon/{id}/open-folder — asks the server to launch the OS
// file manager (Finder / xdg-open / explorer) pointed at the materialized
// Research folder for this taxon. The endpoint is fire-and-forget from
// the UI's point of view: a 200 means the OS subprocess was spawned, not
// that the folder actually opened (no portable way to check). 404 means
// the user hasn't materialized yet — the UI is expected to hide this
// button until all_exist is true, but defensive error handling keeps the
// toast useful if a stale preview slips through.
//
// `source` mirrors the materialize arguments — the materialized path
// differs across sources (CoL vs WoRMS vs Freshwater walk different
// parent columns).
async function openFolder(taxonId, source = "col") {
  const r = await fetch(
    API +
      `/api/taxon/${taxonId}/open-folder?source=${encodeURIComponent(source)}`,
    { method: "POST" },
  );
  if (!r.ok) {
    let detail = "";
    try {
      const body = await r.json();
      detail = body.detail || "";
    } catch {
      // body wasn't JSON — fall back to statusText.
    }
    throw new Error(
      `open-folder ${taxonId} failed: ${r.status}${detail ? " " + detail : ""}`,
    );
  }
  return r.json();
}

export {
  api,
  loadTaxon,
  loadChildren,
  materializeResearch,
  previewMaterialize,
  openFolder,
};
// openFolder intentionally not used inside this module yet — it's
// consumed by the Folder tab in web/detail.js. Suppressed the unused
// export hint because removing it would break the import on detail.js
// (verified — see `openFolder(taxon.id, state.treeSource)` in
// renderFolderTab).
