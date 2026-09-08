#!/usr/bin/env node
// tools/react-e2e-harness/scripts/chromium-driver.mjs — PR 5c.2-B.1b-i.
// Drives an EXPLICIT caller-provided already-running React export origin
// through Chromium and asserts the locked React data contracts. NO
// fixture API server, NO export HTTP server, NO production build
// orchestrator — those are deferred. Dynamic runner injection is kept
// so a future hermetic test slice can substitute `runFn`.
//
// React data contract (binding): harness root + surface + non-null
// taxon id + `[data-explorer="ready"]` + both `[data-pane]` slots +
// `input[data-search-input]` + at least one `[data-file-path]`.
// Fail-closed: any 5xx/network/navigation/contract error throws.

const SCHEMA = "taxa.react-e2e.capture/1";

export async function runCapture({ origin } = {}) {
  if (!origin || typeof origin !== "string") {
    throw new Error(`chromium-driver: origin must be a non-empty string`);
  }
  const playwright = await import("playwright");
  const browser = await playwright.chromium.launch({ headless: true });
  const trace = [];
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on("pageerror", (e) => trace.push({ kind: "pageerror", message: String(e) }));
    page.on("console", (m) => { if (m.type() === "error") trace.push({ kind: "console.error", text: m.text() }); });
    // 1. Navigate to the explicit origin.
    const response = await page.goto(origin, { waitUntil: "load", timeout: 30000 });
    if (!response) throw new Error(`chromium-driver: no response for ${origin}`);
    const status = response.status();
    trace.push({ kind: "navigation", url: origin, status });
    if (status === 0 || status >= 500) {
      throw new Error(`chromium-driver: navigation failure for ${origin}: status ${status}`);
    }
    // 2. Wait for FileExplorer to flip to ready.
    await page.waitForSelector('[data-explorer="ready"]', { timeout: 20000 });
    // 3. Assert every React data contract.
    const a = await page.evaluate(() => {
      const q = (s) => document.querySelector(s);
      const qa = (s) => Array.from(document.querySelectorAll(s));
      const surface = q('[data-harness-surface="file-explorer"]');
      const taxonId = surface ? surface.getAttribute("data-harness-taxon-id") : null;
      const filePaths = qa('[data-file-path]')
        .map((el) => el.getAttribute("data-file-path"))
        .filter((p) => typeof p === "string" && p.length > 0);
      return {
        rootPresent: !!q('[data-harness-root="react-e2e"]'),
        surfacePresent: !!surface,
        taxonId, taxonIdNonNull: taxonId !== null && taxonId !== "" && taxonId !== "0",
        explorerReady: !!q('[data-explorer="ready"]'),
        treePanePresent: !!q('[data-pane="tree"]'),
        viewerPanePresent: !!q('[data-pane="viewer"]'),
        searchInputPresent: !!q('input[data-search-input]'),
        filePathsCount: filePaths.length,
        firstFilePath: filePaths[0] ?? null,
      };
    });
    trace.push({ kind: "assertions", payload: a });
    const failed = [];
    if (!a.rootPresent) failed.push("harness root [data-harness-root]");
    if (!a.surfacePresent) failed.push("harness surface [data-harness-surface]");
    if (!a.taxonIdNonNull) failed.push("non-null data-harness-taxon-id");
    if (!a.explorerReady) failed.push('[data-explorer="ready"]');
    if (!a.treePanePresent) failed.push('[data-pane="tree"]');
    if (!a.viewerPanePresent) failed.push('[data-pane="viewer"]');
    if (!a.searchInputPresent) failed.push("input[data-search-input]");
    if (a.filePathsCount === 0) failed.push("at least one [data-file-path]");
    if (failed.length > 0) throw new Error(`react contract assertions failed: ${failed.join("; ")}`);
    return {
      schema: SCHEMA, origin, capturedAt: new Date().toISOString(),
      navigationStatus: status, taxonId: a.taxonId,
      filePathsCount: a.filePathsCount, firstFilePath: a.firstFilePath, trace,
    };
  } finally {
    // Close browser reliably — every code path lands here.
    try { await browser.close(); } catch { /* already closed */ }
  }
}
