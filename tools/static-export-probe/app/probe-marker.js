"use client";

// Disposable hydration marker: same text server-side and on first
// client paint; swaps to "hydrated" inside useEffect. No controls.
// capture.mjs waits for the text to include "hydrated" before
// recording hydration timing.

import { useEffect, useState } from "react";

export default function ProbeMarker() {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => { setHydrated(true); }, []);
  return (
    <p
      data-testid="probe-marker"
      style={{
        margin: "1rem 0 0 0",
        fontSize: "0.875rem",
        color: hydrated ? "#111111" : "#888888",
      }}
    >
      Hydration: {hydrated ? "hydrated" : "pending"}
    </p>
  );
}
