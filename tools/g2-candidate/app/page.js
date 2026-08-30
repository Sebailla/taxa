// Minimal page for the disposable G2 candidate workspace. Single h1,
// one paragraph, no product wiring. Intentionally excludes next/font,
// client components, hooks, and external assets so the build output is
// the contracted normal application-route + JS chunks + CSS only.

const containerStyle = {
  maxWidth: "32rem",
  margin: "4rem auto",
  padding: "2rem",
  border: "1px solid #111111",
};

const h1Style = { margin: "0 0 1rem 0", fontSize: "1.5rem", fontWeight: 600 };
const paragraphStyle = { margin: 0, lineHeight: 1.5 };

export default function CandidatePage() {
  return (
    <main style={containerStyle}>
      <h1 style={h1Style}>G2 candidate (diagnostic only)</h1>
      <p style={paragraphStyle}>
        This screen is a disposable G2 candidate artifact. It exists to
        exercise the build contract defined in design.md §3.3.2.1. It is
        not part of the product, is unreachable from production, and does
        not collect any data.
      </p>
    </main>
  );
}
