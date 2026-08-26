// Global keyboard shortcuts. Owned by this module so the rest of the
// app doesn't have to coordinate keydown listeners. Three shortcuts:
//
//   /       — focus the search input (#search-input), unless the
//             user is already typing in a text field.
//   Esc     — close the detail panel (when open), close any open
//             kebab menu, close the help view (when open).
//             Cascades: the first open surface wins.
//   ArrowDown / ArrowUp — when the detail panel is open and a tab
//             strip is visible, cycle through the visible tabs.
//             (i.e., the same as clicking the next/previous tab.)
//
// Anything else is ignored. Text inputs (input, textarea, contenteditable)
// swallow all keys except Esc (so the user can always escape).
//
// Wired in `boot()` from web/app.js so the listener attaches once
// at app start and never re-attaches on render().

import { state } from "./state.js";

const TEXT_INPUT_TYPES = new Set([
  "text", "search", "email", "url", "password", "tel", "number",
]);

function isTextInput(el) {
  if (!el || el === document.body) return false;
  const tag = el.tagName;
  if (tag === "TEXTAREA") return true;
  if (tag === "INPUT" && TEXT_INPUT_TYPES.has(el.type)) return true;
  if (el.isContentEditable) return true;
  return false;
}

function focusSearch() {
  const input = document.querySelector("#search-input");
  if (input) {
    input.focus();
    input.select();
  }
}

function closeTopmostSurface() {
  // Cascade: help > detail > kebab menu. The first one wins.
  if (state.helpOpen) {
    // Help is rendered in main; clicking the Classification tab clears it.
    document.querySelector("#nav-classification")?.click();
    return true;
  }
  if (state.detailOpen) {
    document.querySelector("#close-detail")?.click();
    return true;
  }
  // `.kebab-menu.open` is the actual visibility class (see web/index.html
  // `.kebab-menu.open { display: flex }`). The original draft used
  // `:not(.hidden)`, which would always match (no kebab-menu ever carries
  // the `.hidden` class) and would force a spurious `document.body.click()`
  // on every Escape with no surface open — the body-click bubbles to nav.js's
  // delegation which would then close any open search dropdown.
  if (document.querySelector(".kebab-menu.open")) {
    // nav.js already registers a document-level Escape handler that closes
    // any open kebab menu. That listener fires BEFORE this one (registered
    // first, at module init), so by the time we get here the `.open` class
    // has typically already been removed and this branch is a defensive
    // no-op. The return-true keeps the cascade's "a surface was open"
    // semantics correct in case the order ever changes.
    return true;
  }
  return false;
}

function cycleDetailTab(direction) {
  // The detail panel's tab strip is `.detail-tabs` (see web/detail.js).
  // Each tab button carries `data-tab="<key>"` and `role="tab"`.
  // We pick the first tab button and walk up to its parent strip — the
  // selector chain in the original draft tried `[role="tablist"]` /
  // `.detail-tab-strip` first but neither exists in the rendered DOM,
  // so the working branch is `#detail-panel [data-tab]`.
  const firstTab = document.querySelector("#detail-panel [data-tab]");
  const strip = firstTab?.parentElement;
  if (!strip) return false;
  const tabs = [...strip.querySelectorAll("[data-tab]")];
  if (tabs.length === 0) return false;
  const currentIndex = tabs.findIndex((t) => t.classList.contains("active"));
  const nextIndex =
    currentIndex === -1
      ? 0
      : (currentIndex + direction + tabs.length) % tabs.length;
  tabs[nextIndex].click();
  tabs[nextIndex].focus();
  return true;
}

function onKeyDown(e) {
  // Allow Esc to always work, even from text inputs.
  if (e.key === "Escape") {
    if (closeTopmostSurface()) {
      e.preventDefault();
    }
    return;
  }

  // Skip everything else if the user is typing in a text field.
  if (isTextInput(e.target)) return;

  // Skip when modifier keys are pressed (let browser shortcuts work).
  if (e.metaKey || e.ctrlKey || e.altKey) return;

  if (e.key === "/") {
    focusSearch();
    e.preventDefault();
    return;
  }

  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    if (state.detailOpen) {
      const direction = e.key === "ArrowDown" ? 1 : -1;
      if (cycleDetailTab(direction)) {
        e.preventDefault();
      }
    }
    return;
  }
}

export function bootKeymap() {
  document.addEventListener("keydown", onKeyDown);
}