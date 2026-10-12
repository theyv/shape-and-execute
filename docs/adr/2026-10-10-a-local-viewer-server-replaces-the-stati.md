---
title: A local viewer server replaces the static viewer
type: architecture
status: accepted
date: 2026-10-10
source: DL-119, DL-120, DL-145, task 2026-10-08-1733--sae-dogfood-fixes (R2 Q5, R4, R5, [VIEWER-SERVER], [DECISION-VIEWER-SERVER], VIEWER-SERVER); DL-25, design interview 2026-10-06 (Q25)
applies-to: [skills/shape-and-execute/scripts/sae_lib/server.py, skills/shape-and-execute/scripts/sae_lib/viewer.py, skills/shape-and-execute/assets/viewer, ViewerHandler, run_write, ensure_server, idle_limit, cmd_view, known_repos, SAE_CHANGED_BY]
---

# A local viewer server replaces the static viewer

## Context
The first viewer was a static page on `file://`, fed by generated data files
([research/viewer-file-protocol.md](research/viewer-file-protocol.md)). The viewer then became
a control panel: routing, holds, settings. Picking folders in the browser every session was
friction (item 6), and per-checkout data files were two sources of truth (items 14, 18).

## Decision
- [joint] `sae view` starts the viewer server, or reuses the running one. It reads task data
  live from every worktree; no data files are generated. It binds `127.0.0.1` only, checks
  `Host`, and accepts changes only with its token and a same-origin `Origin`. It stops by
  itself after hours without requests and removes its state file.
- [human] The viewer edits task settings through the server.
- [human] One server serves every repository in which `sae` has run, with a project switcher.
  It keeps its last port and token across restarts, so an old link usually keeps working.
- [agent] Writes run `sae <cmd> --json` as a subprocess, marked as coming from the viewer, so
  `sae` stays the only writer. Reads need no token. Prototypes are served in a sandbox
  (`Content-Security-Policy: sandbox`).

## Why
- A control panel needs live data and a safe way to write.
- No folder picking, and one source of truth.
- The idle stop prevents orphaned processes, the owner's explicit pain with servers.
- The command functions rely on the working folder and process state, so the server runs `sae`
  instead of calling them.

## Rejected options
- A static offline viewer on `file://` for all tasks (the first design: no server, no Node, no
  orphaned processes; classic scripts plus polling worked on `file://`), and with it the
  constraint "no servers or background processes" of the first intent.
- The File System Access API, with a copied `sae set` command as fallback: the folder picker
  could not reach the hidden `.tasks`. Its saving, IndexedDB and "Reconnect folder" are gone.
- A `.tasks/.viewer/` data folder.
- Calling the command functions inside the server process.
- The old `/api/file` route.
