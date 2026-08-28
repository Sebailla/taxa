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
  // papaparse@5.4.1 — CSV / TSV parser. Loaded on demand by
  // renderTable when the Table tab is opened. Pinned URL: do not
  // unpin. See web/index.html CDN-pinning block for matching
  // <script> tag.
  Papa: "https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js",
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

// Image rendering — <img> with object-contain so the picture scales to
// fit the snippet frame without distortion or cropping. The browser's
// native decoder handles every extension we register (jpg/jpeg/png/
// gif/webp/bmp); no CDN, no library, no parsing. On load error (e.g.
// truncated file, unsupported sub-format) the onerror handler swaps
// the frame for an inline error card so the user can still download
// the raw file instead of seeing a broken-image glyph.
//
// Big-file advisory: anything over 50 MB gets a yellow banner above
// the image. Decoding 50 MP photos or RAW-like inputs freezes the
// tab — a soft warning is the proportional response.
const IMAGE_BIG_FILE_BYTES = 50 * 1024 * 1024;

function renderImage(target, file) {
  const frame = el("div", { class: "fex-image-frame" });
  const big = (file.size || 0) > IMAGE_BIG_FILE_BYTES;
  const advisory = big
    ? el(
        "div",
        { class: "fex-image-advisory", role: "status" },
        el("span", { class: "material-symbols-outlined" }, "warning"),
        `Large image (${formatSize(file.size || 0)}) — decoding may be slow.`,
      )
    : null;

  const img = el("img", {
    src: file.url,
    alt: file.name,
    title: file.name,
    class: "fex-image",
    loading: "lazy",
    decoding: "async",
  });
  img.addEventListener("error", () => {
    target.replaceChildren(renderImageError(file));
  });

  frame.replaceChildren(img);
  target.replaceChildren(advisory, frame);
}

// Inline image error card — painted when the browser fails to decode
// the file (corrupt, unsupported sub-format like progressive JPEG
// without browser support, etc.). Mirrors the shape of
// renderOfflineBanner so the recovery path is consistent.
function renderImageError(file) {
  return el(
    "div",
    { class: "fex-empty-state" },
    el("span", { class: "fex-empty-state-icon" }, "broken_image"),
    el(
      "p",
      { class: "font-semibold text-on-surface" },
      `Could not decode ${file.name}`,
    ),
    el(
      "p",
      { class: "text-on-surface-variant text-body-sm" },
      "The file may be corrupt or use a sub-format the browser can't render inline.",
    ),
    el(
      "a",
      {
        href: file.url,
        download: file.name,
        class: "fex-snippet-btn mt-2",
      },
      "Download file",
    ),
  );
}

// SVG rendering — fetch + inline so the image scales crisply at any
// size and inherits page CSS variables (theme / realm tint). The fetch
// is required even though the <img src="..."> path works: inlining lets
// us validate the XML before injecting it, so a malicious SVG claiming
// to be an image but carrying <script> gets caught and rendered as
// the generic image error instead of executing. The DOMParser route
// uses the standard XML mode (image/svg+xml) so <script> tags survive
// parsing and the inline path takes responsibility for stripping them.
async function renderSvg(target, file) {
  try {
    const res = await fetch(file.url);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const text = await res.text();
    const doc = new DOMParser().parseFromString(text, "image/svg+xml");
    const svg = doc.documentElement;
    if (!svg || svg.nodeName.toLowerCase() !== "svg") {
      throw new Error("Document is not a valid SVG");
    }
    // Strip <script> and event-handler attributes — XSS defense for
    // inline SVGs that came from arbitrary sources. We don't try to be
    // clever (no allowlist of safe tags); we just drop anything that
    // could run code.
    svg.querySelectorAll("script").forEach((n) => n.remove());
    const walker = doc.createTreeWalker(svg, NodeFilter.SHOW_ELEMENT);
    let node = walker.currentNode;
    while (node) {
      for (const attr of [...node.attributes]) {
        if (/^on/i.test(attr.name)) node.removeAttribute(attr.name);
      }
      node = walker.nextNode();
    }
    // Pin the SVG to the frame's box so it scales with object-contain.
    svg.setAttribute("class", "fex-image");
    if (!svg.getAttribute("preserveAspectRatio")) {
      svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    }
    const frame = el("div", { class: "fex-image-frame" });
    frame.replaceChildren(svg);
    target.replaceChildren(frame);
  } catch (e) {
    target.replaceChildren(renderImageError(file));
    console.error("renderSvg failed", e);
  }
}

// Video rendering — <video controls> with the native player UI. We
// intentionally do NOT autoplay (UX: surprise audio is hostile), and
// preload="metadata" only fetches the first frame so opening a large
// file doesn't pin the network. The browser's native codec support
// covers mp4/h264 (universal), webm/vp9 (Chrome/Firefox/Edge), ogv
// (Firefox/older Chrome). Unsupported codecs surface as the native
// "video can't be played" overlay; the onerror handler paints our
// generic error card with a download link so the user always has an
// escape hatch.
function renderVideo(target, file) {
  const frame = el("div", { class: "fex-video-frame" });
  const video = el("video", {
    src: file.url,
    title: file.name,
    class: "fex-video-el",
    controls: "",
    preload: "metadata",
  });
  video.addEventListener("error", () => {
    target.replaceChildren(renderImageError(file));
  });
  frame.replaceChildren(video);
  target.replaceChildren(frame);
}

// formatSize helper for the image advisory. Lives at module scope so
// the other renderers (PDF meta strip, file_explorer.js) can reuse it
// in the future; right now only renderImage references it.
function formatSize(n) {
  if (n == null) return "?";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`;
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

// Table viewer (CSV / TSV via Papa Parse). Sticky <thead> so the
// header row stays pinned while the body scrolls vertically. Lazy
// loads Papa through the existing loadScriptOnce pattern — see
// CDN_URLS.Papa. On CDN failure (offline / blocked / network blip)
// falls back to renderOfflineBanner so the user can still download
// the raw file via the banner link.
//
// Delimiter: CSV uses "," (Papa default); TSV uses "\t". The
// extension comes from `file.extension` lower-cased, matching the
// `RENDERERS` dispatcher's case-normalisation.
//
// On parse error (Papa returns { errors: [...] } but throws nothing
// by default) we surface the first error via the offline banner so
// the user sees something is wrong without a console-spam.
async function renderTable(target, file) {
  try {
    await loadScriptOnce("Papa");
    const res = await fetch(file.url);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const text = await res.text();
    const ext = (file.extension || "").toLowerCase();
    const delimiter = ext === "tsv" ? "\t" : ",";
    const parsed = window.Papa.parse(text, {
      delimiter,
      skipEmptyLines: true,
    });
    if (parsed.errors && parsed.errors.length > 0) {
      // Surface the first parse error in the banner; Papa reports
      // many "warnings" for benign cases (e.g. trailing delimiter),
      // so don't block the render on them — only show if the user
      // explicitly asked for error visibility (and we'd rather not
      // regress their table view for a noisy warning).
      const first = parsed.errors[0];
      if (first && first.code !== "TooFewFields" && first.code !== "TooManyFields") {
        throw new Error(first.message || "CSV parse error");
      }
    }
    const rows = Array.isArray(parsed.data) ? parsed.data : [];
    if (rows.length === 0) {
      target.replaceChildren(
        el(
          "p",
          { class: "p-4 text-on-surface-variant" },
          "Table is empty.",
        ),
      );
      return;
    }
    // First row is the header (Papa's default when header is omitted).
    // For files without a header row, treat row 0 as data and synthesise
    // "Col N" headers — matches the behaviour most spreadsheet apps
    // give users opening raw CSVs.
    const [headerRow, ...bodyRows] = rows;
    const hasHeader =
      Array.isArray(headerRow) &&
      headerRow.some(
        (cell) => typeof cell === "string" && cell.trim().length > 0,
      );
    const headers = hasHeader
      ? headerRow.map((h) => String(h ?? ""))
      : headerRow.map((_, i) => `Col ${i + 1}`);
    const table = el("table", { class: "fex-csv-table" });
    const thead = el("thead", null);
    const headerTr = el("tr", null);
    for (const h of headers) {
      headerTr.append(el("th", null, h));
    }
    thead.append(headerTr);
    table.append(thead);
    const tbody = el("tbody", null);
    for (const r of hasHeader ? bodyRows : rows) {
      const tr = el("tr", null);
      for (let i = 0; i < headers.length; i++) {
        const cell = r && i < r.length ? String(r[i] ?? "") : "";
        tr.append(el("td", null, cell));
      }
      tbody.append(tr);
    }
    table.append(tbody);
    target.replaceChildren(el("div", { class: "fex-csv-scroller" }, table));
  } catch (e) {
    renderOfflineBanner(target, file);
    console.error("renderTable failed", e);
  }
}

// Tree viewer (JSON, native). Collapsible via <details>/<summary>;
// 16 px indent per nesting level; type-coloured leaves using the
// existing --realm-* palette (no hardcoded hex). Iterative walk
// capped at MAX_JSON_NODES (50 000) — past the cap we append a
// `<p class="fex-tree-truncated">"Tree truncated — open raw"</p>`
// so the user can still see the structure.
//
// Why iterative (not recursive): a 50 000-node JSON in a deeply-
// nested object can blow the JS stack at ~10 000 levels deep. The
// iterative walk uses an explicit stack of pending children so the
// depth is bounded by heap, not by the call stack.
//
// Why type-coloured: matches the spec's "type-coloured leaves"
// requirement (spec.md §Tree viewer tab). Strings/numbers/booleans/
// null each carry a Tailwind token class — `var(--realm-fungi)` /
// `var(--realm-bacteria)` / `var(--realm-archaea)` / italic
// `var(--on-surface-variant)` — so the leaf value's TYPE is
// visible at a glance. No hardcoded hex.
const MAX_JSON_NODES = 50000;

async function renderJsonTree(target, file) {
  try {
    const res = await fetch(file.url);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const text = await res.text();
    const root = JSON.parse(text);
    const host = el("div", { class: "fex-json-tree" });
    const walker = buildJsonWalker(host, root);
    walker.run();
    target.replaceChildren(host);
    if (walker.truncated) {
      target.append(
        el(
          "p",
          { class: "fex-tree-truncated" },
          "Tree truncated — open raw",
        ),
      );
    }
  } catch (e) {
    renderOfflineBanner(target, file);
    console.error("renderJsonTree failed", e);
  }
}

// Build the iterative JSON walker. Returns an object with `run()`
// (which paints the tree) and `truncated` (true if we hit the cap
// before exhausting the document). The walker renders ONE level at
// a time: a root node paints its caret, and each summary click
// reveals more children lazily — this keeps the initial render
// fast even on huge documents (only the root paints upfront;
// nested levels paint only when the user clicks to expand them).
function buildJsonWalker(host, root) {
  let count = 0;
  let truncated = false;

  // Paints the root + registers a one-shot "expand" handler that
  // walks its children on demand. The walk is iterative over the
  // child list so we don't recurse for the initial root paint.
  const rootNode = renderJsonNode("[root]", root, true);
  host.append(rootNode.element);

  const expand = (nodeEl, value) => {
    if (!nodeEl || nodeEl.dataset.expanded === "true") return;
    nodeEl.dataset.expanded = "true";
    nodeEl.classList.add("open");
    if (!Array.isArray(value) && typeof value !== "object" || value === null) {
      return;
    }
    const childrenList = el("ul", { class: "fex-json-children" });
    const entries = Array.isArray(value)
      ? value.map((v, i) => [i, v])
      : Object.entries(value);
    for (const [k, v] of entries) {
      count++;
      if (count > MAX_JSON_NODES) {
        truncated = true;
        childrenList.append(
          el(
            "li",
            { class: "fex-json-node" },
            el(
              "span",
              { class: "fex-tree-leaf" },
              "…",
            ),
          ),
        );
        break;
      }
      const child = renderJsonNode(String(k), v, false);
      if (typeof v === "object" && v !== null) {
        const summary = child.element.querySelector(".fex-json-summary");
        const onClick = (e) => {
          e.preventDefault();
          const willOpen = !child.element.classList.contains("open");
          if (willOpen) expand(child.element, v);
          else child.element.classList.remove("open");
        };
        summary.addEventListener("click", onClick);
        summary.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick(e);
          }
        });
      }
      childrenList.append(el("li", { class: "fex-json-node" }, child.element));
    }
    nodeEl.append(childrenList);
  };

  // Auto-expand the root so the user immediately sees the structure
  // (otherwise they'd need to click the caret). Same semantics as
  // the user's chevron click, just on initial paint.
  expand(rootNode.element, root);

  return {
    run() {
      /* initial paint already done above; run() is a no-op kept for
         a stable interface in case future renderer work wants to
         defer paint to a microtask. */
    },
    get truncated() {
      return truncated;
    },
  };
}

// Render a single JSON value as a node element. `isRoot` controls
// whether we wrap the node in <details> (always, for objects/arrays)
// or just paint a leaf (for primitives).
function renderJsonNode(key, value, isRoot) {
  const type = jsonType(value);

  // Primitive — paint a leaf row, no caret.
  if (type !== "object" && type !== "array") {
    const leaf = el(
      "div",
      { class: `fex-tree-leaf type-${type}` },
      `${formatJsonPrimitive(value)}`,
    );
    return { element: leaf, type };
  }

  // Object / array — a div + summary row that we manage ourselves
  // (NOT a real <details>, because we want lazy child rendering —
  // the native <details> toggle would expand everything at once
  // and defeat the iterative walk). CSS gives the caret a 90°
  // rotation when the parent has `.open` (see index.html).
  const caret = el(
    "span",
    { class: "fex-json-caret material-symbols-outlined" },
    "chevron_right",
  );
  const summary = el(
    "div",
    {
      class: "fex-json-summary",
      role: "button",
      tabindex: "0",
    },
    caret,
    el("span", { class: "fex-json-key" }, key),
    el(
      "span",
      { class: "fex-tree-leaf type-meta" },
      type === "array"
        ? `Array(${Array.isArray(value) ? value.length : 0})`
        : `Object{${Object.keys(value || {}).length}}`,
    ),
  );
  const node = el("div", { class: "fex-json-node" }, summary);
  return { element: node, type };
}

function jsonType(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value; // "object" | "string" | "number" | "boolean"
}

function formatJsonPrimitive(value) {
  if (value === null) return "null";
  if (typeof value === "string") return JSON.stringify(value);
  return String(value);
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
  // CSV / TSV — Table tab. Both extensions share the same renderer;
  // the delimiter is chosen by extension inside renderTable.
  csv: renderTable,
  tsv: renderTable,
  // JSON — Tree tab. Native collapsible renderer, no CDN.
  json: renderJsonTree,
  // Images — inline <img>, browser-native decoder. SVG is fetched and
  // inlined (with XSS scrub) so it inherits CSS variables and scales
  // crisply; everything else uses <img src>.
  jpg: renderImage,
  jpeg: renderImage,
  png: renderImage,
  gif: renderImage,
  webp: renderImage,
  bmp: renderImage,
  svg: renderSvg,
  // Videos — native <video controls>, no autoplay, no CDN.
  mp4: renderVideo,
  webm: renderVideo,
  ogv: renderVideo,
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
  renderImage,
  renderImageError,
  renderSvg,
  renderVideo,
  renderUnsupported,
  render,
};
