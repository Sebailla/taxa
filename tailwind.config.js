// Design tokens — flat, modern, vibrant. Inspired by the Ant
// Design language but with an original palette of our own.
// Mirrors the inline tailwind.config that was previously in
// web/index.html's <script id="tailwind-config"> block. Keep in
// sync with the inline <style> block's :root tokens.
module.exports = {
  content: ["./web/index.html", "./web/**/*.js"],
  theme: {
    extend: {
      colors: {
        // Primary blue, used for selected rows, focus, links.
        primary: "#1D7EA9",
        // Darker variant for hover / pressed states.
        accent: "#176587",
        // Page surface — clean white per the brief.
        surface: "#FFFFFF",
        // Slightly raised panels (search dropdown, tier header).
        elevated: "#BBBBBB",
        // Body and heading text.
        "on-surface": "#333333",
        // Captions, authorship, secondary text.
        "on-surface-variant": "#555555",
        // Strong divider lines.
        outline: "#BBBBBB",
        // Default borders — #D9D9D9 from the brief.
        "outline-variant": "#D9D9D9",
        // Neutral container tones used as the muted row bg.
        "surface-container-lowest": "#FFFFFF",
        "surface-container-low": "#FAFAFA",
        "surface-container": "#F5F5F5",
        "surface-container-high": "#EEEEEE",
        "surface-container-highest": "#E8E8E8",
        background: "#FFFFFF",
      },
      borderRadius: {
        DEFAULT: "0.5rem",
        lg: "0.5rem",
        xl: "0.5rem",
        full: "0.75rem",
      },
      spacing: {
        "indent-step": "1.5rem",
        "row-padding-y": "0.5rem",
        "margin-page": "2rem",
        gutter: "1rem",
        "row-padding-x": "1rem",
      },
      fontFamily: {
        // Raleway across the board — the only typeface the brief
        // asks for. mono-data stays monospaced for numerics.
        "mono-data": ["JetBrains Mono", "monospace"],
        "body-sm": ["Raleway", "sans-serif"],
        "body-md": ["Raleway", "sans-serif"],
        h1: ["Raleway", "sans-serif"],
        display: ["Raleway", "sans-serif"],
        "rank-label": ["Raleway", "sans-serif"],
      },
      fontSize: {
        "mono-data": ["12px", { lineHeight: "16px", fontWeight: "400" }],
        // Body — Raleway 13px / 1.46 (bumped from 11.9px for legibility
        // on a research tool; the detector flagged tiny-text).
        "body-sm": ["13px", { lineHeight: "19px", fontWeight: "400" }],
        "body-md": ["13px", { lineHeight: "19px", fontWeight: "400" }],
        // H3 — Raleway 16px / 1.4 (tier headers, section titles).
        h3: [
          "16px",
          { lineHeight: "22px", letterSpacing: "1px", fontWeight: "600" },
        ],
        // H4 — Raleway 14px / 1.4 (rank badges, sub-section labels).
        h4: [
          "14px",
          { lineHeight: "20px", letterSpacing: "1px", fontWeight: "600" },
        ],
        // h1 in the tree — 24px 600 with the negative tracking the
        // brief uses for hierarchy. Bumped from 18px to restore the
        // h1:body ratio (≈1.85) the detector flagged as flat.
        h1: [
          "24px",
          {
            lineHeight: "28px",
            letterSpacing: "-0.01em",
            fontWeight: "600",
          },
        ],
        // rank-label — Raleway 13px 600 1px tracking (RANK badge).
        // Bumped from 11px so the uppercase label stays legible.
        "rank-label": [
          "13px",
          {
            lineHeight: "16px",
            letterSpacing: "0.1em",
            fontWeight: "600",
          },
        ],
      },
    },
  },
};
