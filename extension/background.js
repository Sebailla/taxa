// background.js — the MV3 service worker. Three responsibilities:
//
// 1. Register a context-menu entry whose title shows the current
//    captured taxon. Update reactively when storage changes.
// 2. On context-menu click, POST the active tab's URL (or the
//    right-clicked link URL) to the taxa backend's save-url endpoint.
// 3. Surface success / failure via chrome.notifications + a brief
//    toolbar badge (✓ green for 3 s on success, ✗ red on failure).
//
// All network calls target the user's local taxa instance. There is
// no remote-server fallback by design.

const TAXA_BASE = "http://localhost:8765";
const MENU_ID = "send-to-taxa";
const BADGE_OK_MS = 3000;

const NOTIF_ICON = "icons/icon-48.png";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function humanizeError(status, detail) {
  if (status === 400) return `URL rejected: ${detail || "check the URL."}`;
  if (status === 404) return `Folder not materialized: ${detail || "open taxa and click Create on the Folder tab first."}`;
  if (status === 413) return `File too large: ${detail || "the file exceeds 50 MB."}`;
  if (status === 415) return `File type rejected: ${detail || "the content-type is not in the allowlist."}`;
  if (status === 502) return `Source error: ${detail || "the origin returned an error."}`;
  if (status === 504) return `Timed out: ${detail || "the origin did not respond in time."}`;
  return `Error ${status}: ${detail || "unknown error."}`;
}

async function refreshMenu(currentTaxon) {
  const title = currentTaxon
    ? `Send to taxa: ${currentTaxon.scientific_name}`
    : "Send to taxa: (no taxon selected — open taxa and click a row)";
  try {
    await chrome.contextMenus.update(MENU_ID, {
      title,
      enabled: !!currentTaxon,
    });
  } catch (err) {
    // contextMenus.update throws if the menu doesn't exist yet (it
    // does — we create it on install) or if MV3 woke the worker up
    // before the install event finished. Either way, nothing to do.
    console.warn("taxa extension: contextMenus.update failed", err);
  }
}

function showBadge(text, color) {
  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color });
  setTimeout(() => chrome.action.setBadgeText({ text: "" }), BADGE_OK_MS);
}

function showNotification(title, message) {
  chrome.notifications.create({
    type: "basic",
    iconUrl: NOTIF_ICON,
    title,
    message,
  });
}

chrome.runtime.onInstalled.addListener(async () => {
  await chrome.contextMenus.create({
    id: MENU_ID,
    title: "Send to taxa: (no taxon selected)",
    contexts: ["link", "page", "image", "video", "audio"],
  });
  const { currentTaxon } = await chrome.storage.local.get("currentTaxon");
  await refreshMenu(currentTaxon);
});

chrome.runtime.onStartup.addListener(async () => {
  // Service worker re-hydrated after browser restart. Rebuild the menu
  // (MV3 wipes contextMenus on shutdown) and refresh the title.
  await chrome.contextMenus.create({
    id: MENU_ID,
    title: "Send to taxa: (no taxon selected)",
    contexts: ["link", "page", "image", "video", "audio"],
  });
  const { currentTaxon } = await chrome.storage.local.get("currentTaxon");
  await refreshMenu(currentTaxon);
});

chrome.storage.onChanged.addListener((changes) => {
  if (Object.hasOwn(changes, "currentTaxon")) {
    refreshMenu(changes.currentTaxon.newValue);
  }
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const { currentTaxon } = await chrome.storage.local.get("currentTaxon");
  if (!currentTaxon) {
    showNotification(
      "taxa: no taxon selected",
      "Open taxa and select a taxon first.",
    );
    return;
  }

  // Priority: right-clicked link URL > right-clicked image src >
  // right-clicked page URL > active tab's URL.
  const url = info.linkUrl || info.srcUrl || info.pageUrl || (tab && tab.url);
  if (!url) {
    showNotification("Cannot save", "No URL found for this context.");
    return;
  }

  // Best-effort filename suggestion. The backend sanitizes; this is a
  // hint only.
  const suggested =
    info.linkText ||
    (tab && tab.title) ||
    (() => {
      try {
        return new URL(url).pathname.split("/").pop() || "download";
      } catch {
        return "download";
      }
    })();

  try {
    const resp = await fetch(
      `${TAXA_BASE}/api/taxon/${currentTaxon.id}/save-url?source=col`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, suggested_filename: suggested }),
      },
    );
    const body = await resp.json().catch(() => ({}));
    if (resp.ok) {
      showNotification(
        `Saved to ${currentTaxon.scientific_name}`,
        `${body.absolute_path}\n(${formatSize(body.size || 0)}, ${body.content_type || "unknown"})`,
      );
      showBadge("✓", "#15803d");
    } else {
      showNotification("Cannot save", humanizeError(resp.status, body.detail));
      showBadge("✗", "#b91c1c");
    }
  } catch (err) {
    showNotification(
      "Cannot save",
      `taxa is not running at ${TAXA_BASE}. Start it and try again.`,
    );
    showBadge("✗", "#b91c1c");
  }
});
