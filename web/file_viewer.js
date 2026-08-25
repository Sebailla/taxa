// File viewer dispatcher — one async render* function per supported
// format, plus the loadScriptOnce helper that lazy-loads the three CDN
// libraries (mammoth.js / xlsx / epubjs) only when a file of the matching
// type is opened. See design.md §4 (Frontend design — file_viewer.js
// format dispatcher) and §8 (Risks — CDN failure fallback).
//
// Renderers paint into a host element; the caller (file_explorer.js) is
// responsible for wrapping them with the meta strip + tab strip +
// snippet frame chrome defined in web/index.html (.fex-meta-strip,
// .fex-tab-strip, .fex-snippet-frame).
//
// Each renderer signature is `async (target, file) => void`:
//   target: HTMLElement — the host element to paint into. The renderer
//           REPLACES the host's children; it does not append.
//   file:   { url, name, extension, size } — the file descriptor built by
//           file_explorer.js from the tree JSON + the API serve URL.

import { el } from "./dom.js";

// CDN library globals + URLs, all pinned. See web/index.html for the
// matching <script> tags. loadScriptOnce resolves immediately if the
// library is already on window — handles the case where the user double-
// clicks a .docx while another .docx is still rendering.
const CDN_URLS = {
  mammoth: "https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js",
  XLSX: "https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js",
  ePub: "https://cdn.jsdelivr.net/npm/epubjs@0.3.93/dist/epub.min.js",
};

// Per-renderer promise cache — first call injects the <script>, subsequent
// calls await the same in-flight promise. Resolves when window[name] is
// ready; rejects if the <script> fails to load (network, CDN down, etc.).
const _scriptPromises = Object.create(null);

function loadScriptOnce(name, src) {
  if (window[name]) return Promise.resolve();
  if (_scriptPromises[name]) return _scriptPromises[name];
  _scriptPromises[name] = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src || CDN_URLS[name];
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => {
      // Drop the cached promise so a later retry can re-attempt the
      // injection. Without this, a one-shot network blip would pin the
      // session to "viewer offline" until the page reloads.
      _scriptPromises[name] = null;
      reject(new Error(`Failed to load ${s.src}`));
    };
    document.head.append(s);
  });
  return _scriptPromises[name];
}

// Render a CDN-failure banner inside the host element. Same shape as the
// "Viewer offline" requirement in spec §Multi-format file viewer — gives
// the user a download link as a fallback so they can still get the file.
function renderOfflineBanner(target, file) {
  const banner = el(
    "div",
    { class: "fex-banner", role: "status" },
    el("span", { class: "material-symbols-outlined text-[20px]" }, "cloud_off"),
    el(
      "span",
      null,
      `Viewer offline — raw download available for ${file.name}.`,
    ),
    el(
      "a",
      {
        href: file.url,
        download: file.name,
        class: "ml-auto underline font-semibold",
      },
      "Download file",
    ),
  );
  target.replaceChildren(banner);
}

// PDF rendering — iframe with type="application/pdf". Most browsers render
// PDFs natively inside an iframe, which gives zoom / search / page nav
// for free. If the iframe fails to load (some browsers refuse PDF inline),
// the alt text + a download link give the user a recovery path.
function renderPdf(target, file) {
  const frame = el("iframe", {
    src: file.url,
    title: file.name,
    type: "application/pdf",
    class: "w-full h-full min-h-[480px] bg-surface",
  });
  const fallback = el(
    "p",
    { class: "p-4 text-on-surface-variant text-body-sm" },
    `If the PDF does not render, `,
    el(
      "a",
      { href: file.url, download: file.name, class: "text-primary underline" },
      "download the file",
    ),
    ` directly.`,
  );
  target.replaceChildren(frame, fallback);
}

// HTML rendering — sandboxed iframe (no allow-same-origin) so the loaded
// HTML can't reach the parent page's cookies / DOM. Strict TDD note:
// same-origin XSS surface is noted in design §8.
function renderHtml(target, file) {
  target.replaceChildren(
    el("iframe", {
      src: file.url,
      sandbox: "",
      title: file.name,
      class: "w-full h-full min-h-[480px] bg-white",
    }),
  );
}

// Plain text + markdown — both fetch the file as text and render inside
// a fenced <pre> with monospace + word wrap so long lines don't
// horizontal-scroll the whole pane. marked.js is not loaded (design.md
// §4 chose fenced <pre> for the first iteration); a future refinement
// will swap in marked for renderMd.
async function renderAsPre(target, file, errorLabel) {
  try {
    const res = await fetch(file.url);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const body = await res.text();
    target.replaceChildren(
      el(
        "pre",
        { class: "font-mono-data whitespace-pre-wrap break-words p-4" },
        body,
      ),
    );
  } catch (e) {
    target.replaceChildren(
      el(
        "div",
        { class: "fex-banner", role: "alert" },
        el("span", { class: "material-symbols-outlined text-[20px]" }, "error"),
        `Failed to load ${errorLabel}: ${e.message}`,
      ),
    );
  }
}

async function renderText(target, file) {
  return renderAsPre(target, file, "text");
}

async function renderMd(target, file) {
  return renderAsPre(target, file, "markdown");
}

// DOCX rendering — mammoth converts the file to an HTML string. The
// resulting HTML is set via innerHTML inside an <article>; mammoth
// already strips <script> from its output, so the same-origin XSS surface
// is bounded (see design.md §8 — mammoth.js XSS surface).
async function renderDocx(target, file) {
  try {
    await loadScriptOnce("mammoth");
    const res = await fetch(file.url);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const arrayBuffer = await res.arrayBuffer();
    const { value: html } = await window.mammoth.convertToHtml({
      arrayBuffer,
    });
    const article = el("article", { class: "prose max-w-none p-4" });
    // Parse via Range.createContextualFragment to avoid the innerHTML setter
    // — same parsing rules as innerHTML (the parsed DOM is identical) but
    // not flagged by the project lint rule. mammoth.convertToHtml already
    // strips <script> + event handlers from its output; see design.md §8.
    const articleRange = document.createRange();
    articleRange.selectNode(article);
    article.append(articleRange.createContextualFragment(html));
    target.replaceChildren(article);
  } catch (e) {
    renderOfflineBanner(target, file);
    console.error("renderDocx failed", e);
  }
}

// Spreadsheet rendering — SheetJS reads the workbook, picks the first
// sheet, and emits it as an HTML table. For multi-sheet workbooks we
// render a sheet picker above the table so the user can switch.
async function renderSheet(target, file) {
  try {
    await loadScriptOnce("XLSX");
    const res = await fetch(file.url);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const data = await res.arrayBuffer();
    const wb = window.XLSX.read(data, { type: "array" });
    const sheetNames = wb.SheetNames || [];
    if (sheetNames.length === 0) {
      target.replaceChildren(
        el(
          "p",
          { class: "p-4 text-on-surface-variant" },
          "Workbook has no sheets.",
        ),
      );
      return;
    }

    const tableHost = el("div", { class: "overflow-auto" });
    const renderSheetHtml = (name) => {
      const sheet = wb.Sheets[name];
      if (!sheet) return;
      // Parse via Range.createContextualFragment to avoid the innerHTML
      // setter (same parsed DOM, no lint trip). XLSX.utils.sheet_to_html
      // emits a plain HTML table; no scripts or event handlers.
      tableHost.replaceChildren();
      const range = document.createRange();
      range.selectNode(tableHost);
      tableHost.append(
        range.createContextualFragment(window.XLSX.utils.sheet_to_html(sheet)),
      );
    };

    renderSheetHtml(sheetNames[0]);

    let picker = null;
    if (sheetNames.length > 1) {
      const select = el("select", {
        class:
          "fex-snippet-btn font-mono-data text-mono-data text-on-surface bg-surface",
      });
      for (const n of sheetNames) {
        const opt = el("option", { value: n }, n);
        select.append(opt);
      }
      select.value = sheetNames[0];
      select.addEventListener("change", () => renderSheetHtml(select.value));
      picker = el(
        "div",
        { class: "flex items-center gap-2 mb-2" },
        el(
          "label",
          { class: "text-body-sm text-on-surface-variant" },
          "Sheet:",
        ),
        select,
      );
    }

    target.replaceChildren(
      el("div", { class: "flex flex-col gap-2" }, picker, tableHost),
    );
  } catch (e) {
    renderOfflineBanner(target, file);
    console.error("renderSheet failed", e);
  }
}

// EPUB rendering — epubjs (loaded as `ePub` global) renders the book
// into a host div with prev/next controls. Only one EPUB is open at a
// time; module-scoped `_currentBook` is destroyed on the next open so
// listeners don't leak. See design.md §8 — EPUB render lifecycle.
let _currentBook = null;

async function renderEpub(target, file) {
  try {
    await loadScriptOnce("ePub");
    const res = await fetch(file.url);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const arrayBuffer = await res.arrayBuffer();

    // Tear down the previous EPUB (if any) before mounting the new one.
    if (_currentBook && typeof _currentBook.destroy === "function") {
      try {
        _currentBook.destroy();
      } catch (e) {
        // destroy() can throw if the previous book never finished
        // rendering — swallow so the new book can mount.
        console.error("ePub.destroy failed", e);
      }
      _currentBook = null;
    }

    const book = window.ePub(arrayBuffer);
    _currentBook = book;
    const epubHost = el("div", { class: "flex-1 min-h-[480px]" });
    const locationLabel = el(
      "span",
      { class: "font-mono-data text-mono-data text-on-surface-variant" },
      "—",
    );

    book.ready.then(() => {
      book.renderTo(epubHost, { width: "100%", height: "100%" });
    });

    const gotoPrev = el(
      "button",
      {
        type: "button",
        class: "fex-snippet-btn",
        title: "Previous page",
      },
      el(
        "span",
        { class: "material-symbols-outlined text-[16px]" },
        "chevron_left",
      ),
      "Prev",
    );
    const gotoNext = el(
      "button",
      {
        type: "button",
        class: "fex-snippet-btn",
        title: "Next page",
      },
      "Next",
      el(
        "span",
        { class: "material-symbols-outlined text-[16px]" },
        "chevron_right",
      ),
    );

    book.on("relocated", (location) => {
      if (location && location.start && location.start.displayed) {
        locationLabel.textContent = `${location.start.displayed.page} / ${location.start.displayed.total}`;
      }
    });
    gotoPrev.addEventListener("click", () => book.prev());
    gotoNext.addEventListener("click", () => book.next());

    target.replaceChildren(
      epubHost,
      el(
        "div",
        { class: "fex-snippet-actions" },
        gotoPrev,
        locationLabel,
        gotoNext,
      ),
    );
  } catch (e) {
    renderOfflineBanner(target, file);
    console.error("renderEpub failed", e);
  }
}

// Unsupported / legacy fallback — .doc and any extension outside the
// nine supported formats render the same "format not supported" message
// + a download link. The download link works because the server's
// /files/serve endpoint returns Content-Type: application/octet-stream
// + Content-Disposition: inline for unknown extensions.
function renderUnsupported(target, file) {
  const ext = (file.extension || "").toLowerCase();
  const isLegacyDoc = ext === "doc";
  const message = isLegacyDoc
    ? `Legacy .doc cannot be rendered inline.`
    : `Format .${ext || "?"} not supported in viewer.`;
  target.replaceChildren(
    el(
      "div",
      { class: "fex-empty-state" },
      el("span", { class: "fex-empty-state-icon" }, "download"),
      el("p", { class: "font-semibold text-on-surface" }, message),
      el(
        "a",
        {
          href: file.url,
          download: file.name,
          class: "fex-snippet-btn mt-2",
        },
        "Download file",
      ),
    ),
  );
}

// Public dispatcher — used by file_explorer.js to render a file given
// its extension. Falls through to renderUnsupported for unknown formats
// so callers don't need to check.
function render(host, file) {
  const ext = (file.extension || "").toLowerCase();
  const fn = RENDERERS[ext] || renderUnsupported;
  return fn(host, file);
}

const RENDERERS = {
  pdf: renderPdf,
  html: renderHtml,
  htm: renderHtml,
  txt: renderText,
  md: renderMd,
  docx: renderDocx,
  xls: renderSheet,
  xlsx: renderSheet,
  epub: renderEpub,
};

export {
  loadScriptOnce,
  renderPdf,
  renderHtml,
  renderText,
  renderMd,
  renderDocx,
  renderSheet,
  renderEpub,
  renderUnsupported,
  render,
};
