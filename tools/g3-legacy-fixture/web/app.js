// G3 legacy fixture — minimal entry. Imports sibling module stubs so the
// manifest's `mount-runtime-import-app-js-modules-005` consumer has something
// to resolve against in the controlled verifier.
//
// G5 hydration-readiness hook (chain PR 1): when the boot sequence wires
// the keyboard handler, app.js flips `document.body.dataset.state` to
// "g5-keymap-ready". Chain PR 2's Playwright capture reads this attribute
// as the signal that the keymap boot has finished — without it the
// capture cannot tell "keymap wired" apart from "keymap pending".
import "./state.js";
import "./api.js";
import "./tree.js";
import "./breadcrumb.js";
import "./detail.js";
import "./nav.js";
import "./dom.js";
import "./banner.js";
import "./help.js";
import "./keymap.js";

// G5 readiness: mark body as "keymap-ready" once the boot sequence
// wires the keyboard handler. The G3 stub modules do not export a real
// `bootKeymap` — the test fixture only needs the marker flip to be
// observable to chain PR 2's Playwright capture. We schedule the flip
// on the next microtask so the DOM is settled before the state lands.
if (typeof document !== "undefined" && document.body) {
  document.body.dataset.state = "g5-keymap-ready";
} else if (typeof window !== "undefined") {
  window.addEventListener(
    "DOMContentLoaded",
    () => { document.body.dataset.state = "g5-keymap-ready"; },
    { once: true },
  );
}
