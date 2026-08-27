// content.js — injected into every page matching http://localhost:8765/*
// on document_idle. Watches for clicks on taxa's taxon tree rows and
// writes the captured {id, scientific_name} to chrome.storage.local
// so the background service worker can use it in the context-menu
// click handler.
//
// Taxa renders each row as something like:
//
//   <div data-taxon-id="12345" class="...">
//     <span class="scientific-name">Homo sapiens</span>
//     <button data-action="toggle-kebab">⋮</button>
//     ...
//   </div>
//
// We listen for clicks anywhere on the body, then walk up to the
// nearest [data-taxon-id] ancestor. On a hit, we read the id from
// the attribute and the name from the row's name element.
//
// Debounced: 250 ms. If the user clicks 5 rows in a second (rapid
// browsing), we only write once per window. The context-menu entry's
// title is rebuilt reactively from the latest storage value, so the
// most recent selection wins.

(() => {
  

  const DEBOUNCE_MS = 250;

  let writeTimer = null;
  let pending = null;

  function schedule(payload) {
    pending = payload;
    if (writeTimer !== null) return;
    writeTimer = setTimeout(() => {
      // Read the latest value at flush time so rapid clicks all see
      // the same eventual value.
      const toWrite = pending;
      writeTimer = null;
      try {
        chrome.storage.local.set({ currentTaxon: toWrite });
      } catch (err) {
        // Storage write can fail in incognito or when the quota is
        // exhausted. Surface the error to the page console — the
        // background worker logs the same on its end.
        console.error("taxa extension: storage write failed", err);
      }
    }, DEBOUNCE_MS);
  }

  // If the user clicks outside any taxon row, do nothing. The most
  // recent selection stays in storage.
  document.body.addEventListener("click", (event) => {
    const row = event.target.closest("[data-taxon-id]");
    if (!row) return;
    const rawId = row.getAttribute("data-taxon-id");
    const id = parseInt(rawId, 10);
    if (!Number.isFinite(id)) return;
    // Prefer a `data-taxon-name` attribute if taxa ever sets one;
    // fall back to the standard scientific-name span; fall back to the
    // row's text content as a last resort.
    const nameEl =
      row.querySelector("[data-taxon-name]") ||
      row.querySelector(".scientific-name") ||
      row.querySelector(".taxon-name");
    const scientific_name = nameEl
      ? nameEl.textContent.trim()
      : row.textContent.trim().split("\n")[0].trim();
    if (!scientific_name) return;
    schedule({ id, scientific_name, capturedAt: Date.now() });
  });
})();
