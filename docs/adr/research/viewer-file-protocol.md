# A serverless viewer on `file://`

Tested 2026-10-06 by a research subagent in Google Chrome 153.0.8010.48 (`--headless=new`,
macOS, default file-access policy), driven over `--remote-debugging-pipe` (no port, no server),
and cross-checked without DevTools for tests 1–3.

| # | Test | Result |
|---|---|---|
| 1 | Classic `<script src="data.js">` setting `window.DATA` | Works. |
| 2 | Injected `<script src="data.js?t=123">` | Works: the file resolves, `onload` fires. |
| 3 | Rewrite `data.js` on disk, inject `data.js?t=2` | The new value is visible without a page reload, with or without a delay, also after an atomic temp-file-and-rename write. Re-injecting the same URL also returned fresh content (no stale cache seen); keep `?t=` anyway for other browsers. |
| 4 | `fetch('data.json')` | Fails: `TypeError: Failed to fetch`; CORS from origin `null`. XHR fails too. |
| 5 | `<script type="module">`, `import()` | Blocked by CORS. |
| 6 | `location.reload()` with `#tab=2` | The hash survives. |

Extra: a script tag with `crossorigin="anonymous"` is blocked too (do not add it). A classic
script from a sibling folder (`../t1/data.js`) loads.

Untested: Firefox, Safari, a headed Chrome profile with extensions,
`--allow-file-access-from-files`, `integrity` attributes, File System Access API on `file://`.

Consequence: a static shell plus generated classic-script data files, re-injected on a timer,
gives a live view with no server and no background process.

## Verified 2026-10-07: directory picker and other browsers

Tested by a research subagent. Chrome 154.0.8037.98 (`/Applications/Google Chrome.app`, headless,
driven by playwright-core with a persistent profile). Safari 26.6.2 (real app, opened with
`open -a Safari`, results read back through the tab title with `osascript`). Firefox is not installed
on this Mac; its rows come from docs only. Test pages: `scratchpad/p1`, `p2`, `br` (scratch dir, not in repo).

### Chrome on `file://`

| Fact | Evidence |
|---|---|
| `file://` is a secure context. | `isSecureContext === true`, `location.origin === "file://"`. |
| `window.showDirectoryPicker` and `showOpenFilePicker` exist. | `typeof` returns `"function"`. |
| The picker call itself is NOT confirmed to work. | Headless has no dialog. Call without gesture: `AbortError: The user aborted a request`. Call from a real `page.click()`: same `AbortError` after ~4 s. A headed run needs a human to pick a folder. |
| IndexedDB and `localStorage` work and are shared by all `file://` pages. | Wrote on `p1/index.html`. `p2/other.html` and `p1/sub/deep.html` read the same value and the same IndexedDB record. Origin is `file://` for all. This contradicts MDN, which says each `file:` URL "seems" to get its own `localStorage` ([MDN localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)); MDN calls the behavior undefined. Do not depend on either. |
| A `FileSystemDirectoryHandle` can be stored in IndexedDB on `file://` and read back after a browser relaunch. | Got a real directory handle by CDP `Input.dispatchDragEvent` with `files:[dir]` and `DataTransferItem.getAsFileSystemHandle()` (kind `directory`). `put` into IndexedDB worked. After killing Chrome and relaunching the same profile, `get` returned `directory:dropme`. A second `file://` page also read it. |
| After relaunch the stored handle has permission `prompt`. | `queryPermission({mode:'read'})` and `({mode:'readwrite'})` both returned `"prompt"`. `entries()` and `getFileHandle()` threw `NotAllowedError`. |
| `requestPermission` needs a real prompt. | Without a gesture it never resolves (no result in 3 s). With a real click it also stayed pending 5+ s: headless cannot show the bubble. The prompt result is therefore untested. |
| A drop-granted handle loses its grant on reload. | Right after the drop: read `"granted"`, readwrite `"prompt"`. After `page.reload()` in the same browser session: both `"prompt"`. This is for a dropped handle; a picker handle may behave differently (untested). |
| Persistent permission ("Allow on every visit", Chrome 122+) for `file://`: UNVERIFIED. | The Chrome blog describes it for handles in IndexedDB restored with `requestPermission()` and says nothing about `file://` ([developer.chrome.com](https://developer.chrome.com/blog/persistent-permissions-for-the-file-system-access-api)). In Chromium `chrome_file_system_access_permission_context.cc` (main, fetched 2026-10-07) I found no scheme check that excludes `file://`. The grant is keyed by `origin.GetURL()`, i.e. `file:///`. Whether the content-settings store accepts that key was not tested. |
| OPFS does not work on `file://`. | `navigator.storage.getDirectory()` on `file://`: `SecurityError: It was determined that certain files are unsafe...`. Same call on `http://localhost:8765` (python http.server): returns a directory. So there is no OPFS fallback for storage. |
| Headless Chrome instance has no user prompt UI. | See the `requestPermission` row. Use a headed run to settle persistent permission. |

### Safari 26.6.2 on `file://`

Page `br/t.html` in a folder with `data/x.js`; title read back by AppleScript.

| Fact | Evidence |
|---|---|
| Classic `<script src="data/x.js">` loads. | `X0: "v1"`. |
| Injected `<script src="data/x.js?t=123">` loads. The query string does not break it. | `inj1: "onload X=v1"`. |
| Rewriting the file and injecting `?t=456` shows the new content without reload. | I rewrote `x.js` to `v2` while the page was open. `inj2: "onload X=v2"`. |
| `localStorage` works, `indexedDB` exists, `isSecureContext` is true. | `ls: "v"`, `idb: "object"`, `secure: true`, `origin: "file://"`. |
| No File System Access picker. | `typeof showDirectoryPicker === "undefined"`. `DataTransferItem.prototype.getAsFileSystemHandle` is absent. MDN compat data (`api/Window.json`, main): Safari `version_added: false`. |

### Firefox (not installed, docs only)

| Fact | Source |
|---|---|
| No `showDirectoryPicker`. | MDN compat data: Firefox `version_added: false`. Chrome 86 is the first version; Edge and Opera mirror Chrome. |
| Classic script loading from the same folder should work. | Not tested. Reasoning: classic scripts load in no-cors mode, so no origin check applies. MDN says `file:` origins are opaque and sibling files "may trigger CORS errors"; this affects `fetch`/XHR/modules, which the viewer does not use ([MDN same-origin policy](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Same-origin_policy)). Chrome and Safari both load them. `security.fileuri.strict_origin_policy` was not mentioned on that page. |
| `localStorage` on `file:` is "undefined" behavior. | MDN localStorage page (quoted above). Untested. |

### Degrade path for the viewer

1. Feature-detect: `window.showDirectoryPicker` (or `showOpenFilePicker`). Do not sniff the user agent.
2. If present (Chrome, Edge, Opera): offer "Connect folder". Store the handle in IndexedDB. On load, `queryPermission`. If `prompt`, show a button that calls `requestPermission` from a click. Expect to ask again after every browser restart until persistent permission is verified for `file://`.
3. If absent (Safari, Firefox): the viewer stays read-only. Keep the live-reload by script injection (verified in Safari). Edit through a "Download JSON" button (`Blob` + `<a download>`) or a copy-to-clipboard button, and tell the user to save over the file. An `<input type="file">` can re-open the file for a one-time read.
4. Do not rely on OPFS (fails on `file://` in Chrome). Wrap `localStorage` and IndexedDB access in try/catch.
5. To close the open items, run one headed Chrome session: pick a folder, store the handle, reload, relaunch, and check whether "Allow on every visit" appears on a `file://` page.
