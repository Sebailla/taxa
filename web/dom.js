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
    // `.append()` accepts both Node and string args, so no createTextNode
    // wrapper needed for the primitive branch.
    node.append(c instanceof Node ? c : String(c));
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

export { el, scrollTaxonBelowCard, waitForDetailReady, showToast };
