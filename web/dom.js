// DOM utilities: el() builder + the two scroll/ready helpers used by the
// search-result navigation path. Pure presentation; no API or tree state
// lives here. waitForDetailReady does read state.selected/state.detail to
// gate on the panel being populated — that's a single import and keeps the
// helper co-located with the scroll math that depends on the panel's final
// height.

import { state } from "./state.js";

// Build a DOM element from a spec. Every string child flows through
// textContent (XSS-safe), every attribute goes through setAttribute.
function el(tag, props, ...children) {
  const node = document.createElement(tag);
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (v == null || v === false) continue;
      if (k === "class" || k === "className") {
        node.className = v;
      } else if (k === "style" && typeof v === "string") {
        node.setAttribute("style", v);
      } else if (k.startsWith("on") && typeof v === "function") {
        node.addEventListener(k.slice(2).toLowerCase(), v);
      } else if (v === true) {
        node.setAttribute(k, "");
      } else {
        node.setAttribute(k, String(v));
      }
    }
  }
  for (const c of children.flat(Infinity)) {
    if (c == null || c === false) continue;
    if (c instanceof Node) {
      node.appendChild(c);
    } else {
      node.appendChild(document.createTextNode(String(c)));
    }
  }
  return node;
}

// Center a tree row in the area BELOW the sticky detail card.
// scrollIntoView({block: "center"}) centers in the viewport, which puts
// the row halfway under the card when the card is sticky at the top.
// We measure the card's bottom edge in viewport coords and scroll so the
// row's center matches the vertical center of the remaining space.
function scrollTaxonBelowCard(el) {
  const main = document.querySelector("main");
  if (!main) return;
  const card = document.querySelector(".detail-card");
  // No visible card → fall back to plain centering in the viewport.
  if (!card || card.closest(".hidden") !== null) {
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }
  const cardRect = card.getBoundingClientRect();
  const cardBottom = cardRect.bottom;
  const visibleTreeHeight = window.innerHeight - cardBottom;
  // If the card covers everything, there is no visible tree area —
  // skip the scroll instead of producing a wild negative delta.
  if (visibleTreeHeight <= 0) return;
  const visibleTreeCenter = cardBottom + visibleTreeHeight / 2;
  const taxonRect = el.getBoundingClientRect();
  const taxonCenter = taxonRect.top + taxonRect.height / 2;
  // Use scrollTo with an absolute target. scrollBy is relative to the
  // current scrollTop, which the browser silently adjusts when content
  // is inserted above the visible area (the sticky card lands in flow
  // when first rendered, pushing the tree down). Absolute scrollTo
  // ignores that drift and lands exactly where we want.
  const targetScroll = main.scrollTop + (taxonCenter - visibleTreeCenter);
  main.scrollTo({ top: targetScroll, behavior: "auto" });
}

// Wait for loadDetail to finish so the detail card is at its final height
// before we calculate the scroll position. loadDetail fetches the three
// sub-endpoints in parallel and then re-renders the card. While the fetch
// is in flight the card shows "Loading details…" (~100px); once it lands
// the card is at its full size (~300–500px). Scrolling against the stub
// leaves the taxon too low once the real content paints in.
function waitForDetailReady(id) {
  return new Promise((resolve) => {
    const tick = () => {
      // If the user navigated away, give up.
      if (state.selected !== id) return resolve();
      // detail populated + card actually rendered with content (not just
      // the loading stub). Checking for two or more detail-item rows
      // ensures the panel has real data, not the loading placeholder.
      const card = document.querySelector(".detail-card");
      const ready =
        state.detail &&
        card &&
        card.querySelectorAll(".detail-item").length > 0;
      if (ready) resolve();
      else setTimeout(tick, 40);
    };
    tick();
  });
}

// Tiny toast for action feedback (e.g. "Carpetas creadas en ./Research",
// "Error: 404 not found"). Auto-dismisses after 4s by default. Calls in
// quick succession replace the previous toast instead of stacking — useful
// for click→click→click cycles where the user doesn't need to see every
// intermediate message.
let _toastNode = null;
let _toastTimer = null;
function showToast(message, opts = {}) {
  if (_toastNode) {
    _toastNode.remove();
    _toastNode = null;
  }
  if (_toastTimer) {
    clearTimeout(_toastTimer);
    _toastTimer = null;
  }
  const node = el(
    "div",
    {
      class: `toast${opts.error ? " toast-error" : ""}`,
      role: opts.error ? "alert" : "status",
      "aria-live": opts.error ? "assertive" : "polite",
    },
    message,
  );
  document.body.append(node);
  _toastNode = node;
  _toastTimer = setTimeout(() => {
    if (_toastNode === node) {
      node.remove();
      _toastNode = null;
    }
    _toastTimer = null;
  }, opts.duration ?? 4000);
}

// Modal for the materialize action. Opens a centered dialog that fetches
// the GET /api/taxon/{id}/materialize-preview and renders a line-by-line
// preview of the path with ✓ / + markers. The user can confirm (POST
// /materialize) or cancel. The promise resolves with:
//   {confirmed: true, response}  on confirm (response = POST payload)
//   {confirmed: false}            on cancel/close
//   {confirmed: false, error}      on POST failure (error = thrown Error)
// The caller is responsible for merging the response into state and
// re-rendering the tree.
//
// ESC and backdrop click close without firing the POST. Once the POST is
// in flight, ESC and close are ignored so the user can't double-fire.
async function openMaterializeModal(taxon) {
  const { previewMaterialize, materializeResearch } = await import("./api.js");
  // Lazy import keeps the api module's import graph out of the top-level
  // dependency cycle (dom.js ↔ api.js ↔ tree.js ↔ dom.js).

  return new Promise((resolve) => {
    let inFlight = false;
    let closed = false;

    const close = (result) => {
      if (closed) return;
      closed = true;
      // Detach handlers before removing the node so a stray backdrop click
      // during teardown can't try to resolve the same promise twice.
      document.removeEventListener("keydown", onKey);
      backdrop.remove();
      resolve(result);
    };

    const onKey = (e) => {
      if (e.key === "Escape" && !inFlight) close({ confirmed: false });
    };
    document.addEventListener("keydown", onKey);

    // Build the static shell. Body / footer are filled after the preview
    // fetch lands (loading → preview/error). The close button always
    // works unless a POST is in flight.
    const backdrop = el("div", {
      class: "materialize-modal-backdrop",
      "data-materialize-modal": "1",
    });
    const closeBtn = el(
      "button",
      {
        class: "materialize-modal-close",
        type: "button",
        "aria-label": "Cerrar",
        onClick: () => !inFlight && close({ confirmed: false }),
      },
      el("span", { class: "material-symbols-outlined text-[20px]" }, "close"),
    );
    const titleEl = el(
      "div",
      { class: "materialize-modal-title" },
      el("span", null, "Materializar carpeta"),
    );
    const taxonEl = el(
      "div",
      { class: "materialize-modal-taxon" },
      el("span", { class: "materialize-modal-taxon-label" }, "Taxon:"),
      el("span", { class: "materialize-modal-taxon-name" }, taxon.scientific_name),
    );
    const bodyEl = el("div", { class: "materialize-modal-body" });
    const footerEl = el("div", { class: "materialize-modal-footer" });

    const modal = el(
      "div",
      {
        class: "materialize-modal",
        role: "dialog",
        "aria-modal": "true",
        "aria-labelledby": "materialize-modal-title",
      },
      el(
        "div",
        { class: "materialize-modal-header" },
        titleEl,
        closeBtn,
      ),
      taxonEl,
      bodyEl,
      footerEl,
    );
    backdrop.append(modal);
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop && !inFlight) close({ confirmed: false });
    });
    document.body.append(backdrop);
    requestAnimationFrame(() => backdrop.classList.add("materialize-modal-open"));

    // Step 1: fetch the preview. Until it lands, the body shows a
    // "Cargando vista previa…" placeholder and the footer is empty.
    bodyEl.append(
      el(
        "div",
        { class: "materialize-modal-loading" },
        el(
          "span",
          { class: "material-symbols-outlined text-[20px] animate-spin" },
          "progress_activity",
        ),
        el("span", null, "Cargando vista previa…"),
      ),
    );
    // Async work inside the Promise executor is wrapped in an IIFE so a
    // thrown error doesn't get swallowed (a `new Promise(async ...)` would
    // silently drop rejections — the pi-lens `promise-async-executor` rule
    // blocks that pattern).
    (async () => {
      let preview;
      try {
        preview = await previewMaterialize(taxon.id);
      } catch (err) {
        bodyEl.innerHTML = "";
        bodyEl.append(
          el(
            "div",
            { class: "materialize-modal-error" },
            el(
              "span",
              { class: "material-symbols-outlined text-[20px]" },
              "error",
            ),
            el("span", null, `No se pudo cargar la vista previa: ${err.message}`),
          ),
        );
        footerEl.append(
          el(
            "button",
            {
              class: "materialize-modal-btn materialize-modal-btn-secondary",
              type: "button",
              onClick: () => close({ confirmed: false }),
            },
            "Cerrar",
          ),
        );
        return;
      }
      bodyEl.innerHTML = "";

      // Step 2: render the line-by-line preview. Each segment shows the
      // cumulative path (so the user can scan the tree visually) with a
      // marker (✓ for existing, + for new) on the right.
      const listEl = el("ul", { class: "materialize-modal-list" });
      let acc = preview.research_dir;
      for (const seg of preview.segments) {
        acc = `${acc}/${seg.name}`;
        const marker = seg.exists ? "✓" : "+";
        const markerCls = seg.exists
          ? "materialize-modal-marker-exists"
          : "materialize-modal-marker-new";
        listEl.append(
          el(
            "li",
            { class: "materialize-modal-list-item" },
            el("span", { class: `materialize-modal-marker ${markerCls}` }, marker),
            el("span", { class: "materialize-modal-segment-path" }, acc),
          ),
        );
      }
      bodyEl.append(
        el(
          "div",
          { class: "materialize-modal-preview-wrap" },
          el("div", { class: "materialize-modal-section-title" }, "Vista previa del path:"),
          listEl,
        ),
      );
      bodyEl.append(
        el(
          "div",
          { class: "materialize-modal-counts" },
          `${preview.new_count} ${preview.new_count === 1 ? "carpeta nueva" : "carpetas nuevas"} · ${preview.existing_count} ya existían`,
        ),
      );

      // Step 3: render the footer. Two modes:
      //  - all_exist: the path is fully materialized, show a green banner
      //    and a single [Cerrar] button (per product decision: no re-create).
      //  - mixed: [Cancelar] + [Crear N carpetas].
      if (preview.all_exist) {
        bodyEl.append(
          el(
            "div",
            { class: "materialize-modal-info-banner" },
            el(
              "span",
              { class: "material-symbols-outlined text-[20px]" },
              "check_circle",
            ),
            el("span", null, "Todo el path ya existe en el disco."),
          ),
        );
        footerEl.append(
          el(
            "button",
            {
              class: "materialize-modal-btn materialize-modal-btn-primary",
              type: "button",
              onClick: () => close({ confirmed: false }),
            },
            "Cerrar",
          ),
        );
        return;
      }
      footerEl.append(
        el(
          "button",
          {
            class: "materialize-modal-btn materialize-modal-btn-secondary",
            type: "button",
            onClick: () => close({ confirmed: false }),
          },
          "Cancelar",
        ),
      );
      const createLabel = `Crear ${preview.new_count} ${preview.new_count === 1 ? "carpeta" : "carpetas"}`;
      const createBtn = el(
        "button",
        {
          class: "materialize-modal-btn materialize-modal-btn-primary",
          type: "button",
        },
        createLabel,
      );
      createBtn.addEventListener("click", async () => {
        inFlight = true;
        createBtn.disabled = true;
        createBtn.textContent = "Creando…";
        // Visually freeze the rest of the dialog so the user can't change
        // their mind mid-flight (and we don't have to gate every other
        // control separately).
        closeBtn.disabled = true;
        const cancelBtn = footerEl.querySelector(
          ".materialize-modal-btn-secondary",
        );
        if (cancelBtn) cancelBtn.disabled = true;
        try {
          const response = await materializeResearch(taxon.id);
          close({ confirmed: true, response });
        } catch (err) {
          close({ confirmed: false, error: err });
        }
      });
      footerEl.append(createBtn);
    })();
  });
}

export {
  el,
  scrollTaxonBelowCard,
  waitForDetailReady,
  showToast,
  openMaterializeModal,
};
