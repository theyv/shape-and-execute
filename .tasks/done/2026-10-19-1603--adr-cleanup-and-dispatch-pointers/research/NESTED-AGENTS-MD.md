---
status: done
confidence: medium
---

# Research: NESTED-AGENTS-MD

Checked 2026-10-19. Local: `claude --version` = 2.1.303, `codex --version` = 0.163.0. No model session was run.
Doc pages: Claude Code `memory`, `sub-agents`, `worktrees`, `tools-reference`, `large-codebases` at
code.claude.com/docs/en; Codex guide `agents-md` (developers.openai.com/codex/guides/agents-md, redirects to
learn.chatgpt.com/docs/agent-configuration/agents-md); Codex source, github.com/openai/codex `main`.

## Answers

### 1. Claude Code: does it read AGENTS.md?
**Answer:** Yes, natively, since v2.1.277, on by default. But only when there is no `CLAUDE.md`
(`CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md`) in the working directory or any directory above it.
If one exists anywhere on that path, Claude reads the `CLAUDE.md` files only and ignores `AGENTS.md`, unless the
user sets "Project instructions" to `claude-md-and-agents-md`. This repository has an `AGENTS.md` and no
`CLAUDE.md` (checked with `find`), so the default works here.
**Evidence:**
- "Reading `AGENTS.md` directly requires Claude Code v2.1.277 or later." Before v2.1.281 some sessions (Bedrock,
  telemetry off) read `CLAUDE.md` only. — memory#agents-md, #when-agents-md-support-is-unavailable [primary]
- Table: "An `AGENTS.md`, and no `CLAUDE.md` ... → Your `AGENTS.md`"; "An `AGENTS.md` and a `CLAUDE.md` ... → Your
  `CLAUDE.md` files only". — memory#agents-md [primary]
- Setting `instructionFiles`: `claude-md-or-agents-md` is the default; `claude-md-and-agents-md` loads both. —
  memory#choose-which-instruction-files-load [primary]
- Not read: `AGENTS.local.md`, `AGENTS.override.md`, anything under `.agents/`. — memory#when-claude-code-reads-agents-md [primary]
- This session received the root `AGENTS.md` as project instructions (system prompt of this run). [primary, local]
**Confidence:** high

### 2. Claude Code: when does a nested file load; subagents?
**Answer:**
- Root and ancestors of the working directory: at session start (`AGENTS.md` and `.claude/AGENTS.md`, or `CLAUDE.md`).
- Nested files in subdirectories under the working directory: on demand, not at launch.
  - Nested `CLAUDE.md`: loads "once Claude reads, writes, or edits another file in that subdirectory". A Bash
    `cat`/`head`/`tail`/`sed -n`/`grep`/`rg` on a single file counts as a read.
  - Nested `AGENTS.md`: narrower. It loads "when Claude opens a file there with the Read tool and that subdirectory
    has none of the three `CLAUDE.md` files of its own". The docs do not list Edit, Write or Bash reads for
    `AGENTS.md`. They do for `CLAUDE.md`. A gap is possible: a write to a new file, or an Edit of a file the model
    never read with `Read` (newer models may edit an unread file when reading needs no prompt).
- Subagents (Agent tool): each gets a fresh context. A non-Explore/Plan subagent loads "every level of the CLAUDE.md
  hierarchy the main conversation loads ... and any `AGENTS.md` files loaded as project instructions". Explore and Plan
  skip them. The docs say nested `CLAUDE.md` and path rules "still load when the subagent works with files there" only
  for Explore, Plan and `omitClaudeMd` subagents. They are silent on the same for ordinary subagents. Likely yes
  (the mechanism is the file tools, not the startup list), but not stated. UNKNOWN for nested `AGENTS.md` in a subagent.
- The `cd` of a subagent does not persist and a subagent starts in the main conversation's working directory.
- A subagent with `isolation: worktree` takes its startup instruction files "from your main conversation, not from its
  worktree". In `.claude/worktrees/` it does not load the worktree root's `CLAUDE.md` or `.claude/rules/` either.
**Evidence:**
- memory#how-claude-md-files-load ("Instead of loading them at launch, Claude Code loads each one once Claude reads,
  writes, or edits another file in that subdirectory.") [primary]
- memory#when-claude-code-reads-agents-md, bullets "At session start" and "As Claude works in subdirectories" [primary]
- tools-reference#edit-tool-behavior (Bash single-file view loads nested CLAUDE.md; unread-file edit rule) [primary]
- sub-agents#what-loads-at-startup and "Nested CLAUDE.md and path-scoped rules" [primary]
- sub-agents#configure-subagents ("A subagent starts in the main conversation's current working directory ... `cd` ...
  don't persist") [primary]
- worktrees#isolate-subagents-with-worktrees [primary]
- Changelog 2.1.293: "Fixed path-scoped rules and nested CLAUDE.md files not loading when Claude views a file with a
  single-file cat ... in the Bash tool instead of the Read tool" — raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
  (read via a summarizer; the page was cut off, so no other entries checked) [primary]
**Confidence:** high for the main session; medium for ordinary subagents.

### 3. Codex: which AGENTS.md files?
**Answer:** Only the chain from the project root down to the working directory, built once at session start.
Nested files below the working directory are not loaded when the agent touches them. At most one file per directory
(`AGENTS.override.md`, then `AGENTS.md`, then `project_doc_fallback_filenames`). The project root is the nearest ancestor
that has a `.git` entry (a marker probe by metadata, so the `.git` file of a git worktree counts). Without a marker,
only the working directory is read. Untrusted projects get no project `AGENTS.md`. A global `~/.codex` `AGENTS.md`
(override first) is added before the project files.
Subagents and `codex exec`: the code that discovers files has no mode switch. A subagent inherits only user and thread
instructions (`inherited_instructions`). It does not inherit the project snapshot, so it runs the same discovery from
its own working directory. `codex exec` runs the same session start. So workers behave like the main session, relative to
the cwd they are given. Not run locally.
**Evidence:**
- `codex-rs/core/src/agents_md.rs`, module doc: "concatenation of all files found along the path from the project root to
  the current working directory"; steps 1–3 ("We do **not** walk past the project root"). Functions `agents_md_paths`
  (walks `cursor` from cwd up to `root`, then reverses) and `candidate_filenames`. [primary]
- `codex-rs/file-system/src/find_up.rs`, `find_nearest_ancestor`: a marker matches when `get_metadata` succeeds (file or
  directory). Default marker `.git` ("When `project_root_markers` is unset, the default marker list is used (`.git`)"). [primary]
- `load_project_instructions`: `if config.active_project.is_untrusted() { return ... }` (no project docs). [primary]
- `codex-rs/core/src/agents_md_manager.rs`: `inherited_instructions` copies `user` and `thread` (and a shareable thread provider)
  with `..Default::default()`, so `project_snapshot` is empty for a subagent. `refresh` runs `load_project_instructions` per
  environment selection. [primary]
- Docs: "Codex builds an instruction chain when it starts (once per run; in the TUI this usually means once per launched
  session)"; "Starting at the project root ... walks down to your current working directory"; "at most one file per
  directory". The docs page says nothing on nested files below cwd or on subagents. — agents-md, "How Codex discovers
  guidance" [primary]
- No code path found for lazy loading of nested `AGENTS.md`. The GitHub code search is incomplete, so this absence is not
  proven repository-wide; the loader file and the docs agree. [primary]
**Confidence:** high for root→cwd and for no nested loading in the loader; medium for subagent behavior (read from code, not run).

### 4. Size limits and truncation
**Answer:**
- Codex: `project_doc_max_bytes`, default 32768 (32 KiB), counted over the combined project files of all environments.
  Files are added root first. A file that crosses the remaining budget is truncated at the byte limit with a warning, and
  later files (deeper ones, nearer to the cwd) are dropped. Global user instructions are outside this budget. So a long root
  file can push out a deeper `AGENTS.md`.
- Claude Code: no hard truncation of the combined text. Guidance is under 200 lines per file. A file over 4 MiB is skipped.
  A startup warning appears for a file over the recommended length, and for files that "add up past a combined limit"
  (the limit value is not stated). Auto memory `MEMORY.md` has its own 200 lines / 25 KB cap, which does not apply to
  `AGENTS.md`.
**Evidence:**
- `codex-rs/core/src/agents_md.rs` `read_agents_md` (`if size > remaining { data.truncate(...) }`, `tracing::warn!`);
  `codex-rs/config/src/config_toml.rs` `DEFAULT_PROJECT_DOC_MAX_BYTES = 32 * 1024`; `codex-rs/core/config.schema.json`
  ("Maximum total bytes of project instruction content across all selected environments", default 32768) [primary]
- Codex docs: "stops adding files once the combined size reaches the limit defined by `project_doc_max_bytes`", default 32 KiB [primary]
- memory#my-claude-md-is-too-large ("Files over 200 lines ... Claude Code skips a file over 4 MiB ... warning when files that
  are each within that length add up past a combined limit") and memory#write-effective-instructions ("target under 200 lines") [primary]
**Confidence:** high (Codex), medium (Claude combined limit value unknown).

### 5. Worker at the worktree root, job edits `skills/x/assets/viewer/app.css`: does `skills/x/assets/viewer/AGENTS.md` reach it?
sae creates worktrees outside the repository, under the worktree root (default macOS
`~/Library/Caches/shape-and-execute/worktrees/`, Linux `${XDG_CACHE_HOME:-~/.cache}/shape-and-execute/worktrees/`) —
`skills/shape-and-execute/scripts/sae_lib/setup_mode.py:62-67`, `references/modes/setup.md:136-138`. The worker prompt tells a
Claude Code worker to `cd <workdir> && …` (`references/roles/worker.md:17-18`).

- **Codex: NO.** The cwd is the worktree root. The loader reads root→cwd only (root `AGENTS.md`, found through the `.git` file).
  A nested `viewer/AGENTS.md` is below the cwd and is never read by the loader. The worker would see it only if it opens it
  itself (for example through `ls` or `cat`). Evidence: Q3. Confidence: high.
- **Claude Code: UNKNOWN, probably NO for sae's setup; yes only in a narrow case.** Three facts:
  1. On-demand loading is documented for "subdirectories under your current working directory". A subagent's cwd is the main
     conversation's (the main checkout), and the sae worktree is outside it. The docs do not say whether the on-demand
     loader fires for a file outside the cwd tree. Nothing in the docs says it does.
  2. For `isolation: worktree` subagents the docs say startup files come from the main conversation, and that in the default
     `.claude/worktrees/` location the worktree root's `CLAUDE.md` is not loaded as the subagent reads files there. That is
     a documented case where the worktree's own tree is not used. It is not sae's setup (sae creates its own worktrees), so
     it only hints at behavior.
  3. Even inside the cwd tree, nested `AGENTS.md` loads on the Read tool only. An Edit without a prior Read, or a Write of a
     new file, may not trigger it. (A `CLAUDE.md` is more reliable: read, write and edit all trigger it.)
  Evidence: memory#how-claude-md-files-load, #when-claude-code-reads-agents-md; worktrees#isolate-subagents-with-worktrees;
  sub-agents#configure-subagents. Not tested locally: a probe needs a model call, which the job's limits exclude.
  Confidence: medium that it is not reliable; the exact behavior is UNKNOWN.
- A `CLAUDE.md` next to the file does not fix Claude Code cleanly: any `CLAUDE.md` on the path above the cwd makes Claude Code
  ignore every `AGENTS.md`, including the root one of this repository.

## Options and tradeoffs
Not requested (no design proposals beyond Q5). Facts that bear on the choice are below.

## Open questions
- Does Claude Code's on-demand loader fire for a file outside the subagent's cwd (worktree elsewhere on disk)? A cheap
  `claude -p --model haiku` probe from a directory with a nested `AGENTS.md` and a worktree path outside it would settle it.
  It needs a model call, so it was not run. The `InstructionsLoaded` hook (not fired for `AGENTS.md` read via the setting)
  cannot observe it; `/memory` or the "Loaded" line would.
- Whether an ordinary (non-Explore/Plan) subagent loads nested `AGENTS.md` after a Read: not stated in the docs.
- The combined-size warning limit for Claude Code is not documented.
- Codex subagent and `codex exec` behavior is from source reading, not from a run.

## Implications for the spec
- Root `AGENTS.md` reaches workers in both harnesses (Claude Code: from the main conversation; Codex: through discovery in the
  worktree, which carries its own committed copy). Do not rely on this when a `CLAUDE.md` exists on the path in Claude Code.
- A directory `AGENTS.md` below the repository root does not reliably reach a sae worker in either harness: Codex never loads it
  below the cwd; Claude Code's on-demand load is documented for the Read tool and for subdirectories under the cwd, and sae's
  worktrees are outside the cwd.
- So dispatch pointers for directory `AGENTS.md` files would not duplicate harness loading in Codex, and would at most duplicate
  it in Claude Code in the cases where it works. The harness cannot be counted on to cover them.
- If pointers are added, a pointer line costs a Read by the worker, and in Claude Code a Read of a file in that directory may also
  load the nested `AGENTS.md` itself (documented trigger), which is a possible duplicate, not a problem.
- Sizes: Codex stops adding `AGENTS.md` text at 32 KiB combined (root first), so a long root file squeezes deeper ones out; the
  repository's root `AGENTS.md` is far below that.
- Claude Code version facts: native `AGENTS.md` needs v2.1.277+; sessions on v2.1.276 or older, or some Bedrock/telemetry-off
  sessions before v2.1.281, read `CLAUDE.md` only.
- Codex ignores an untrusted project: a worker in an untrusted worktree gets no project `AGENTS.md` at all.

## Follow-up questions
