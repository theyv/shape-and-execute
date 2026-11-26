---
status: done
summary: Project Stakes lookup (profile, AGENTS.md, CLAUDE.md of the main worktree), one stakes block in every dispatch prompt, a status line, and the profile section writer
validation: pass
changes: made
resolved: []
---

# Result: STAKES-IN-PROMPTS

## Validation evidence
- `test -f tests/test_stakes.py`; `python3 tests/run.py test_stakes test_dispatch_pointers test_task_worktree`: OK. Also `test_retired_terms test_external_review_tokens test_reviews test_record_privacy test_sae_ask`: 104 tests OK in total.
- Smoke `test_worktrees_review_verify_and_finish`: OK.
- Covered by `tests/test_stakes.py` (26 tests): order of sources and "first with content wins"; empty test (five empty labels, comments only, nothing); "Not set by the owner" line and prose count as content; no fallback to `## Stakes`; one block per prompt kind (research, planning, worker, decision, review, review COMMAND, resumed prompt, not-set prompt); 15-line fallback; a task worktree reading and naming the home profile, with a stale copy in the task worktree ignored; a task made in a linked worktree (status names the main worktree's profile, a save there reaches the next dispatch); `sae status` writes nothing; the writer changes only the section (outside lines equal, midfile, last section, missing section, missing profile); AGENTS.md is never written.
- Commit a034d6e on the job branch.

## Interfaces for VIEWER-SURFACES (`scripts/sae_lib/stakes.py`)
- `profile_path(root) -> Path`: `.tasks/repo/profile.md` of the main worktree of `root`'s repository.
- `find_stakes(root) -> Stakes | None`: `Stakes(path, text)` with `.in_profile`. `path` is the file that won (profile, AGENTS.md or CLAUDE.md of the main worktree); `text` is the section without HTML comments and without empty label lines. `None` when no source has content. A viewer shows it read-only when `not in_profile` ("edit there").
- `section_text(path) -> str | None`: the Project Stakes section of any file with comments stripped (labels kept); `None` when the file or section is missing. For filling the edit box from the profile.
- `save_profile_stakes(root, text) -> Path`: replaces only the profile's `## Project Stakes` section, returns the profile path. Raises `ValueError` for text holding a level 1 or 2 heading.
- `status_line(root, found)` and `prompt_block(root)` are for status and prompts.
- `sae status <task> --json` has `stakes: {source: <path>|null, profile: <path>}`.

## Decisions taken
- [agent] Placement: the block sits right after the `Task: … Job: …` line of every prompt (one call site in `build_prompt`; the external review COMMAND and a RESUME prompt reuse it).
- [agent] The header and the not-set text are one line each (no embedded newline); the 15-line fallback is the header with its final `:` replaced by `.` plus the new constant `STAKES_LONG_SUFFIX` (" The section is longer than 15 lines: read it before you start."). The suffix is my wording; the owner may adjust it in PROMPT-TEXT style.
- [agent] Source paths in the block and in status are absolute paths of the main worktree. Section end: the next heading of level 1 or 2; deeper headings stay inside. A section counts as longer than 15 lines after blank-line collapsing and dropping empty label lines.
- [agent] Empty label lines are dropped from the pasted text, so a half-filled template does not show empty bullets.
- [agent] The writer keeps an HTML comment directly under the heading (the template's help and example). Not asked for; without it the first viewer save would delete the guidance. Everything outside the section is byte-equal.
- [agent] Status line format: `Project Stakes: <source path>` or `Project Stakes: not set (write them to <profile path>, section "Project Stakes")`.
- [agent] `tests/test_retired_terms.py` is outside the job's scope list, but the job's Scope text says to remove the retired-terms exemption of `STAKES_LINE`; I removed it and its test case's allowance.
- [agent] The profile pointer line `Repo profile — validation, hot files:` still points at the task checkout's copy, because it serves validation commands and hot files, not stakes. Only the stakes use the main worktree profile.
- `tests/saetest.py` needed no change.

## Risks
- A malformed profile whose Project Stakes heading sits inside a fenced block is not found (fenced code is skipped, like `md_section`).
- The "not set" line the template now tells agents to keep reads after the header as `- Not set by the owner. Set the bar yourself …`; the header's own text and that line say nearly the same, which is accepted (owner decision on the texts).

## Findings filed
None.
