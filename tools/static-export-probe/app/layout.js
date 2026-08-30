// Minimal root layout for the disposable static-export probe.
// No fonts, no brand metadata, no navigation. Body explicitly sets
// `background: #FFFFFF` so the rendered HTML's default paint matches
// the contract.

export const metadata = {
  title: "Static-export probe",
  description:
    "Disposable diagnostic artifact. Not part of the product. Unreachable from production.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: "#FFFFFF", color: "#111111" }}>
        {children}
      </body>
    </html>
  );
}
