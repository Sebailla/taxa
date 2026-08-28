// Settings view — mounted when the user clicks the Settings nav tab
// in the header. Mirrors the shape of file_explorer.js and help.js
// (mount/clear pair):
//
//   renderSettings(host)    — replace `host`'s children with the
//                             settings shell
//   clearSettingsView(host) — drop the settings shell out of `host`
//
// Two controls in this iteration:
//
//   1. Theme toggle (light / dark). Persists the choice in
//      localStorage.taxa.settings.theme and stamps `data-theme` on
//      <html> so the CSS variables in index.html re-resolve. Default
//      theme is whatever the OS prefers via prefers-color-scheme,
//      falling back to light when the media query is unavailable.
//
//   2. Reset tree pane width. Clears localStorage.taxa.fex.treeWidth
//      and asks the file_explorer module to re-render with the CSS
//      default (30%). The tree-view mount is what writes the
//      per-mount width; clearing storage + re-mounting is the cleanest
//      way to drop back to the CSS rule.
//
// Theme dark mode is built on top of the existing CSS custom-property
// palette — `:root` defines the light values, `[data-theme="dark"]`
// redefines them in index.html. The toggle just stamps/unstamps the
// attribute; no JS owns the colour values.
//
// The view is read-only +1-click controls — no API calls, no event
// delegation beyond the buttons and the keyboard shortcut link.

import { el } from "./dom.js";

const THEME_STORAGE_KEY = "taxa.settings.theme";

function readStoredTheme() {
  try {
    const v = localStorage.getItem(THEME_STORAGE_KEY);
    if (v === "light" || v === "dark") return v;
  } catch {
    /* private browsing — fall through to OS preference */
  }
  try {
    if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
  } catch {
    /* matchMedia unavailable — fall through to light */
  }
  return "light";
}

function writeStoredTheme(value) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, value);
  } catch {
    /* swallow — see file_explorer's splitter for the same pattern */
  }
}

// Apply the theme by stamping `data-theme` on <html>. The CSS picks
// up the attribute and re-resolves the custom-property palette.
// `light` removes the attribute (matches the default :root rules)
// so the OS preference can take over again when the user clears
// their explicit choice.
export function applyTheme(theme) {
  const html = document.documentElement;
  if (theme === "dark") {
    html.setAttribute("data-theme", "dark");
  } else {
    html.removeAttribute("data-theme");
  }
  writeStoredTheme(theme);
  // Notify any open Settings view that the toggle moved — the radio
  // buttons need to re-paint their aria-checked state.
  document.dispatchEvent(
    new CustomEvent("taxa:theme-change", { detail: { theme } }),
  );
}

// One-time bootstrap from boot() so the theme survives a reload.
export function bootstrapTheme() {
  applyTheme(readStoredTheme());
}

function settingRow({ title, description, control }) {
  return el(
    "section",
    { class: "settings-row" },
    el(
      "div",
      { class: "settings-row-text" },
      el("h3", { class: "settings-row-title" }, title),
      el("p", { class: "settings-row-description" }, description),
    ),
    el("div", { class: "settings-row-control" }, control),
  );
}

function themeToggle(current) {
  // Two side-by-side buttons. The inactive one is a flat outline
  // button; the active one uses primary surface + on-primary text,
  // matching the rest of the app's toggle pattern (tree-source,
  // hide-empty, search mode).
  const lightBtn = el(
    "button",
    {
      type: "button",
      class:
        current === "light"
          ? "settings-theme-btn settings-theme-btn-active"
          : "settings-theme-btn",
      "aria-pressed": current === "light" ? "true" : "false",
      title: "Use the light theme",
      onclick: () => applyTheme("light"),
    },
    el("span", { class: "material-symbols-outlined" }, "light_mode"),
    "Light",
  );
  const darkBtn = el(
    "button",
    {
      type: "button",
      class:
        current === "dark"
          ? "settings-theme-btn settings-theme-btn-active"
          : "settings-theme-btn",
      "aria-pressed": current === "dark" ? "true" : "false",
      title: "Use the dark theme",
      onclick: () => applyTheme("dark"),
    },
    el("span", { class: "material-symbols-outlined" }, "dark_mode"),
    "Dark",
  );
  return el("div", { class: "settings-theme-toggle" }, lightBtn, darkBtn);
}

function resetTreeWidthButton() {
  const btn = el(
    "button",
    {
      type: "button",
      class: "settings-action-btn",
      title: "Reset the Browser tab tree pane to its default 30% width",
      onclick: async () => {
        try {
          localStorage.removeItem("taxa.fex.treeWidth");
        } catch {
          /* swallow */
        }
        // Re-mount the tree so the CSS default (30%) wins the cascade.
        // renderTree() rebuilds from state.tree and the splitter reads
        // the absence ( now → falls back to CSS default.
        try {
          const { renderTree } = await import("./tree.js");
          renderTree();
        } catch (err) {
          console.error("tree.js import failed during reset", err);
        }
        btn.textContent = "Reset — done";
        setTimeout(() => {
          btn.replaceChildren(
            el(
              "span",
              { class: "material-symbols-outlined" },
              "restart_alt",
            ),
            "Reset",
          );
        }, 1500);
      },
    },
    el("span", { class: "material-symbols-outlined" }, "restart_alt"),
    "Reset",
  );
  return btn;
}

// Keep the theme buttons in sync when applyTheme() is called from
// elsewhere (a future keyboard shortcut, for example). Re-paint every
// .settings-theme-btn on the page so the active state stays correct.
document.addEventListener("taxa:theme-change", (e) => {
  const theme = e.detail?.theme;
  if (theme !== "light" && theme !== "dark") return;
  document.querySelectorAll(".settings-theme-btn").forEach((btn) => {
    const isLight = btn.querySelector(":scope > .material-symbols-outlined")
      ?.textContent === "light_mode";
    const active = (theme === "light" && isLight) || (theme === "dark" && !isLight);
    btn.classList.toggle("settings-theme-btn-active", active);
    btn.setAttribute("aria-pressed", active ? "true" : "false");
  });
});

// ---- Mount / clear -------------------------------------------------------

let _currentHost = null;

export function renderSettings(host) {
  _currentHost = host;
  const current = readStoredTheme();
  host.replaceChildren(
    el(
      "div",
      { class: "settings-shell" },
      el(
        "header",
        { class: "settings-header" },
        el("h2", { class: "settings-title" }, "Settings"),
        el(
          "p",
          { class: "settings-subtitle" },
          "Preferences for the taxa web app.",
        ),
      ),
      el(
        "div",
        { class: "settings-list" },
        settingRow({
          title: "Theme",
          description:
            "Switches the page colour palette. Your choice is remembered for future visits; clearing browser storage reverts to your operating system's preference.",
          control: themeToggle(current),
        }),
        settingRow({
          title: "Browser tree pane width",
          description:
            "The Browser tab's left pane defaults to 30% of the available width. You can drag the splitter at any time; this button resets the width to that default.",
          control: resetTreeWidthButton(),
        }),
        settingRow({
          title: "Keyboard shortcuts",
          description:
            "Press ? in the page header to open the keyboard reference. Shortcuts are also listed in the About view.",
          control: el(
            "a",
            {
              href: "#",
              "data-action": "open-help",
              class: "settings-link-btn",
              onclick: (e) => {
                e.preventDefault();
                document.querySelector('[data-path="help"]')?.click();
              },
            },
            el("span", { class: "material-symbols-outlined" }, "help"),
            "Open shortcuts",
          ),
        }),
      ),
    ),
  );
}

export function clearSettingsView() {
  if (!_currentHost) return;
  _currentHost.replaceChildren();
  _currentHost = null;
}

export function isMounted() {
  return _currentHost !== null;
}