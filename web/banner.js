// Version-mismatch banner. Renders a persistent top-of-page warning when
// the DB's PRAGMA user_version is older than the API's
// CURRENT_SCHEMA_VERSION. Hidden when versions match (the common case).
//
// Wired from app.js boot() after the /api/health fetch:
//   renderVersionBanner(h.db_schema_version, h.expected_schema_version);
//
// The banner element (#version-banner) ships hidden in index.html so the
// layout is unaffected when there's nothing to report. This module is the
// single point that toggles its visibility.

export function renderVersionBanner(actual, expected) {
  const banner = document.querySelector("#version-banner");
  if (!banner) return;
  if (actual >= expected) {
    banner.classList.add("hidden");
    return;
  }
  const actualEl = document.querySelector("#version-banner-actual");
  const expectedEl = document.querySelector("#version-banner-expected");
  if (actualEl) actualEl.textContent = String(actual);
  if (expectedEl) expectedEl.textContent = String(expected);
  banner.classList.remove("hidden");
}
