# taxa: Save to Research — Browser Extension

A Manifest V3 browser extension that adds a right-click **"Send to taxa: &lt;scientific_name&gt;"** entry to any browser tab. When invoked, the extension posts the active tab's URL (or the right-clicked link's URL) to a local `taxa` backend, which fetches the resource server-side and writes it to the active taxon's Research folder.

This is the **Camino B** flow described in the [save-to-research design](../../openspec/changes/browser-extension-save-to-research/design.md): it removes the 4-6 manual clicks (Save as → paste path → confirm) that Camino A still requires.

## Requirements

- **Chrome 120+** (Manifest V3 only). Firefox is not yet supported (the manifest tweaks are trivial; a port is tracked as a follow-up).
- A running `taxa` instance on `http://localhost:8765` (the default dev port). The extension is hard-coded to that base URL; there is no remote-server fallback.
- A taxon selected in the taxa tree. The context-menu entry is disabled until you select a row.

## Install

The extension is not on the Chrome Web Store yet. To install it locally:

1. Clone this repository and `cd` into it.
2. Open `chrome://extensions` in Chrome.
3. Enable **Developer mode** (toggle in the top-right corner).
4. Click **Load unpacked** and select the `extension/` directory from this repo.
5. The extension's toolbar icon appears. No permissions are requested at install time (Chrome asks for `activeTab` and `notifications` on first use, not on install).

To update after a code change: click the extension's **Reload** button on `chrome://extensions`.

## Use

1. Open `taxa` in a browser tab at `http://localhost:8765`.
2. Click a taxon row in the tree (e.g. "Homo sapiens"). The selection propagates to the extension via a content script; no extra action needed.
3. Switch to any other tab (a paper on Scholar, an image, a PDF, etc.) and right-click. The context menu shows **"Send to taxa: Homo sapiens"** (or whatever taxon you last selected).
4. Click the entry. A notification appears within ~2-3 s:
   - **Success**: the absolute path of the saved file, plus its size and content-type.
   - **Failure**: a human-readable reason (auth-required, size cap, etc.).
5. The toolbar icon shows a green check (success) or red cross (failure) for 3 s.

If you select a different taxon in taxa's tree, the context-menu entry updates automatically — the most recent selection wins.

## Permissions

| Permission | Why |
| --- | --- |
| `activeTab` | Read the URL of the tab the user is interacting with. |
| `contextMenus` | Add the right-click entry. |
| `storage` | Persist the current taxon between service-worker suspensions. |
| `scripting` | Inject the content script into the taxa tab. |
| `notifications` | Show the save result. |
| `host_permissions: http://localhost:8765/*` | Talk to the local taxa backend. |

No `<all_urls>`, no remote scripts, no `webRequest` / `declarativeNetRequest`. The extension cannot read or modify any page outside `localhost:8765`.

## Filename pattern

Files are saved as:

```
<sanitized-name>__<taxon-id>.<extension>
```

For example, a PDF from Scholar saved to Homo sapiens (id 9606):

```
Research/Homo sapiens/paper__9606.pdf
```

- `<sanitized-name>` is the page title, link `<a download>` attr, or URL's last segment (whichever the user clicked on). The backend sanitizes it: any character outside `[A-Za-z0-9._-]` is replaced with `_`, leading dots are dropped, and any extension is stripped (the extension comes from the response's `Content-Type`).
- `<taxon-id>` is mandatory. The reasoning: if the user is collecting baseline papers for several host species, the suffix keeps the per-taxon destination unambiguous even when suggested names collide.
- If the path already exists on disk, a `__<timestamp>` suffix is appended and the original file is **never** overwritten.

## Known limitations (v1)

- **No paywall bypass.** If a paper is behind a paywall or requires auth, the server-side fetch returns 401/403 and the extension surfaces an actionable error. No workaround attempted.
- **No Chrome Web Store publishing yet.** Local install only (developer mode). Publishing is a follow-up.
- **No Firefox port.** Manifest V3 is supported in Firefox 109+, but a Firefox-specific manifest is needed (the `"background"` field uses `"scripts"` instead of `"service_worker"`). Trivial port; not done.
- **No bidirectional sync.** The extension captures which taxon is current; taxa does not learn which other tabs the user has open.
- **MV3 service-worker lifecycle.** The worker can be killed by the browser between clicks. The extension re-hydrates on the next context-menu open, but an in-flight save can be lost. v1 accepts this limitation.
- **DNS rebinding has a small race window.** The backend resolves the hostname once and checks the IP; a clever rebinding attack could re-resolve between the check and the actual connection. Document the limit; a proper fix requires a custom socket-level connect.

## Manual smoke checklist

After installing:

- [ ] Open `taxa` and click a taxon. The context menu in another tab shows "Send to taxa: &lt;name&gt;".
- [ ] Right-click a PDF link on a search results page → click the entry → file lands in `Research/&lt;chain&gt;/&lt;name&gt;__&lt;id&gt;.pdf`.
- [ ] Right-click a JPG image on a page → file lands in `Research/&lt;chain&gt;/&lt;name&gt;__&lt;id&gt;.jpg` (or `.jpeg`).
- [ ] Right-click a page background (no link) → uses the tab's URL.
- [ ] Right-click without a taxon selected → menu entry is disabled.
- [ ] Right-click when `taxa` is not running → notification: "Cannot save: taxa is not running at <http://localhost:8765>."
- [ ] Right-click a paywalled PDF → notification: "Cannot save: ... authentication required."

## FAQ

**The context-menu entry is greyed out.**
Either no taxon is selected, or the content script didn't load. Reload the taxa tab and try again.

**"Cannot save: taxa is not running at <http://localhost:8765>."**
Start taxa (`make api` in the repo root) and try again. The extension has no remote-server fallback.

**The saved file is named `paper__1234.pdf` — why the double extension?**
This is the design contract: the `__&lt;id&gt;` suffix is always there to disambiguate per-taxon destinations. The `paper` part is the sanitized suggested name; the `.pdf` comes from the response's `Content-Type`. The full prefix `paper__1234` is the filename; `.pdf` is the extension.

**Can I save from a different computer?**
No. The extension only talks to `localhost:8765` on the machine where Chrome is running. For a remote-instance setup, you'd need to change `TAXA_BASE` in `background.js` and re-load the unpacked extension.

**Does this work with Chrome's enterprise policies?**
Yes, as long as the user can install unpacked extensions. Some enterprise policies block developer-mode extensions entirely; the extension is not (yet) on the Chrome Web Store.
