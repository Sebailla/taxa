// G3 legacy fixture — minimal stub. The manifest's
// `mount-runtime-import-app-js-modules-005` consumer imports this file
// so the controlled verifier can resolve it.
//
// G5 hydration-readiness hook (chain PR 1): after tree.js's first
// render, mark `#tree-view[data-state="ready"]` so chain PR 2's
// Playwright capture can observe "tree first-paint reached". The marker
// is the analogue of a real hydration baseline signal — without it the
// capture cannot tell "tree drawn" apart from "tree pending".
export {};

// G5 readiness: flip the #tree-view placeholder's `data-state` to
// "ready" once the DOM is available. The G3 stub tree does not have a
// real render pipeline; we just stamp the marker so the capture can
// diff baseline vs. candidate against a deterministic signal. Scheduled
// on a microtask so the static `data-testid` is in place before the
// `data-state` lands.
if (typeof document !== "undefined") {
  const stamp = () => {
    const el = document.getElementById("tree-view");
    if (el) el.dataset.state = "ready";
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", stamp, { once: true });
  } else {
    stamp();
  }
}
