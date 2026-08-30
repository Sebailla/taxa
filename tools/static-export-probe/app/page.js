// Disposable static-export probe — diagnostic shell.
// Stitch project 11813286795400731874 · screen ec543a4cec974c2e82085a5e0406334a
// Single centered card, exactly one <h1>, one paragraph, three <li> items.
// Contrast: #111111 on #FFFFFF ≈ 16.1:1 (WCAG 2.1 AA).

import ProbeMarker from "./probe-marker.js";

const STITCH_PROJECT_ID = "11813286795400731874";
const STITCH_SCREEN_ID = "ec543a4cec974c2e82085a5e0406334a";

const cardStyle = {
  maxWidth: "32rem", margin: "4rem auto", padding: "2rem",
  border: "1px solid #111111", fontFamily: "system-ui, sans-serif",
  color: "#111111", background: "#FFFFFF",
};
const h1Style = { margin: "0 0 1rem 0", fontSize: "1.5rem", fontWeight: 600 };
const paragraphStyle = { margin: "0 0 1.25rem 0", lineHeight: 1.5 };
const listStyle = { margin: 0, paddingLeft: "1.25rem", lineHeight: 1.6 };
const provenanceStyle = {
  marginTop: "2rem", fontSize: "0.8125rem", color: "#555555",
  fontFamily: "ui-monospace, monospace",
};

export default function ProbePage() {
  return (
    <main style={cardStyle}>
      <h1 style={h1Style}>Static-export probe (diagnostic only)</h1>
      <p style={paragraphStyle}>
        This screen is a disposable diagnostic artifact produced to record
        the static-export profile of the taxa frontend. It is not part of
        the product, is unreachable from production, and does not collect
        any data.
      </p>
      <ul style={listStyle}>
        <li>Role: diagnostic</li>
        <li>Scope: evidence only</li>
        <li>Production: unreachable</li>
      </ul>
      <ProbeMarker />
      <p style={provenanceStyle} data-testid="probe-provenance">
        Stitch project {STITCH_PROJECT_ID} · screen {STITCH_SCREEN_ID}
      </p>
    </main>
  );
}
