---
type: follow-up
confidence: medium
paths: [skills/shape-and-execute/scripts/sae_lib/prompts.py]
---

# Records match once at dispatch; files outside scope miss them

## Observation
`sae dispatch` matches decision records once, when it builds the prompt: a worker on its `scope`, else on its job file; a reviewer on the diff ([DECISION-MATCH] in `prompts.py`). A worker that ends up editing a file outside its declared scope never gets the records whose `applies-to` covers that file. The reviewer gets them later, on the diff, so the miss is caught after the code is written, not before.

Harness-native path-scoped loading works the other way round. Claude Code loads `.claude/rules/*.md` with `paths:` and nested `CLAUDE.md` files when the agent reads, writes or edits a matching file: once per trigger, and again only after `/compact` (repeated injection was a bug fixed in 2.1.89). OpenCode attaches nested `AGENTS.md` on Read and dedupes across turns (v1.19.4). So "it spams on every tool call" is no longer an argument against lazy loading.

The trade-off is upfront vs lazy, not spam vs no spam. sae's upfront match reaches the agent before it plans and works in Codex, which has no path-scoped loading. Lazy loading never misses a touched file, but arrives only when the file is touched, possibly after the plan is made.

## Evidence
- `sae_lib/prompts.py`, [DECISION-MATCH]: "a review on the diff, a worker on `scope`, else on its job file". The match runs while the prompt is built, not during the job.
- `.tasks/adr/2026-10-19-records-reach-agents-through-pointer-lin.md` and `2026-10-19-reviewers-get-matched-record-pointers-no.md` keep upfront pointer lines and note that wrong `applies-to` paths never reach a reviewer. Neither covers a worker that leaves its scope.
- Claude Code docs (code.claude.com/docs/en/memory, /context-window): path-scoped rules and nested CLAUDE.md load on Read, Write or Edit of a matching file and reload after compaction. CHANGELOG 2.1.89: "Fixed nested CLAUDE.md files being re-injected dozens of times in long sessions". One empirical run on 2.1.309 showed one injection per file, one more after `/compact`.
- Codex builds its AGENTS.md chain once at startup, root to cwd, and has no path-scoped rules.

## Cost
A worker that touches an unplanned file can break a decision before any record reaches it. The integration or job reviewer may catch it on the diff, but then the fix is a rework round instead of a correct first attempt. The gap grows with loose `scope` entries.

## Suggestion
Owner has not decided; options to weigh later:
- Keep the upfront match and add a cheap lazy layer where the harness has one: emit Claude Code path-scoped rules (or a deduped PreToolUse hook keyed by `session_id`) that point to records for files outside the job scope.
- At job finish, match records on the job's own diff and flag records that were not in the prompt, before the review starts.
- Leave Codex on upfront pointers only, since it has no lazy mechanism.
