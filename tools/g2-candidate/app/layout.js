import "./globals.css";

// Minimal root layout for the disposable G2 candidate workspace. See
// openspec/changes/migrate-nextjs-tailwind4/design.md §3.3.2.1.
// Deliberately no fonts (next/font is contractually out of scope here),
// no brand metadata, no navigation. Body styles live in globals.css so
// the build ships a real CSS bundle under out/_next/static/css/.

export const metadata = {
  title: "G2 candidate",
  description:
    "Disposable G2 candidate artifact. Not part of the product. Unreachable from production.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
