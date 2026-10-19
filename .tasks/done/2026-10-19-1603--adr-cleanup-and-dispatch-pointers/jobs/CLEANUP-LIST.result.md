---
status: done
summary: Cleanup list for all 103 records and 8 research notes. Keep 25, code comment 14, directory AGENTS.md 2, remove 62. Notes: keep 5, remove 3.
validation: pass
changes: none
resolved: []
---

# Result: CLEANUP-LIST

## Cleanup list

### Owner changes at the hold (2026-10-19) [human]

These win over the rows and flags below.
- The two eval notes (`research/evals-landscape.md`, `research/superpowers-evals.md`): remove,
  as listed. Git keeps them.
- The two `sae_lib` rows: create `skills/shape-and-execute/scripts/sae_lib/AGENTS.md`, as listed.
- `research/prose-spec.md`: replace the long word-for-word handbook quotes with short
  paraphrases, and remove the local APM skill path (`~/.claude/skills/apm-primitives/SKILL.md`,
  "the user's APM rules").
- Narrow the broad path entries of the kept records: docs-keep-only-the-why to `docs/adr`
  (drop `skills/shape-and-execute` and `wip-docs`); follow-prose and one-skill-with-five-modes
  to the narrowest paths that still name the files the decision guards.
- Smooth the private machine details in `research/codex-facts.md`, as flagged.
- All other rows stand as listed.

**Counts.** Records: 103 = keep 25 + code comment 14 + directory `AGENTS.md` 2 + remove 62.
Research notes: 8 = keep 5 + remove 3.

How to read the reasons:
- **keep**: what an agent would "fix", or which rejected option it would bring back, without the record.
- **remove**: "the code shows it" means code, tests, a reference or an existing comment already
  states it. Sometimes `_intent.md` or the viewer's `README.md` states it instead.
- **code comment / directory AGENTS.md**: the knowledge concerns one file or one folder; the
  target is named.

### Records

| File | Action | Target | Reason | Revisit when |
|---|---|---|---|---|
| 2026-10-06-backlog-files-go-into-git-like-findings.md | remove | | The code shows the commit rule (`sourced_items`, `commit_backlog_pickup`). Its rejected "commit the task folder at start" is also in the kept task-record record (overlap). | |
| 2026-10-06-big-work-goes-lazily-through-the-backlog.md | keep | | Without it, an agent would add an up-front series of full specs, or a wayfinder decision map, to shaping. | |
| 2026-10-06-claude-code-and-codex-only.md | remove | | `_intent.md` (Constraints, Principles) states "Claude Code and Codex only" and parity. Its "no Orca" part is reopened by the owner's backlog item `2026-10-14-1321--orca-integration-worktrees-and-browser`, so it no longer guards anything. | |
| 2026-10-06-codex-permission-profile.md | remove | | The code shows it: `setup_mode.py` prints the profile (hooks and config read-only) and why ("Without a permission profile Codex keeps .git read-only…"). | |
| 2026-10-06-explicit-invocation-only.md | keep | | Without it, an agent would turn on implicit invocation "for discoverability" in `SKILL.md` or `agents/openai.yaml`. The record ties both flags together. | |
| 2026-10-06-five-interaction-modes.md | remove | | `interaction-modes.md` and `INTERACTION_MODES` show the five modes; `_intent.md` ("What it must do") says why both ends exist. | |
| 2026-10-06-follow-prose-without-ceremony.md | keep | | Without it, an agent would add per-role agent files with tool allowlists, or a planner that cannot write files (both rejected as ceremony). `CREDITS.md` links it. | workers overstep their authority |
| 2026-10-06-hot-files-in-planning.md | remove | | `planner.md` and the profile template state the rule; nobody would undo it. | |
| 2026-10-06-intent-and-spec-have-separate-jobs-and-s.md | remove | | The templates and `sae check` coverage show it. A hand-kept traceability table is not a likely proposal. | |
| 2026-10-06-jobs-with-semantic-ids-instead-of-waves.md | remove | | The code shows it, and `tests/test_retired_terms.py` bans "wave". | |
| 2026-10-06-light-in-its-complexity.md | remove | | `_intent.md` Principles states it, "above every other one". Kept records that link it point to `_intent.md` instead. | |
| 2026-10-06-no-configuration-in-the-skill-and-sae-fa.md | keep | | Without it, an agent would ship defaults "for convenience", or add a config check at every start (both rejected). | |
| 2026-10-06-no-drift-check-mechanism.md | remove | | `shape.md` has the intake clause. It overlaps with big-work-goes-lazily (no up-front mechanism for backlog work). | |
| 2026-10-06-no-interrupted-status.md | code comment | `skills/shape-and-execute/scripts/sae_lib/progress.py` (the "last change" line of `sae status`) | One file: "last change N min ago", not "running for": a dead worker still shows `running`. | |
| 2026-10-06-one-flat-task-folder-with-files-only-for.md | remove | | The code shows the single layout; `_intent.md` says a file exists only when it carries content. | |
| 2026-10-06-one-skill-with-five-modes.md | keep | | Without it, an agent would split the skill into a pack, or split out setup or a "mini skill". The owner rejected that: it clutters the skill list, and separate skills cannot share `scripts/`. | the fast-lane backlog item (`2026-10-14-2150`) is shaped |
| 2026-10-06-provenance-on-every-decision.md | remove | | `SKILL.md` and the templates require the tags; `_intent.md` (assumptions) says why. | |
| 2026-10-06-relations-between-tasks-are-prose.md | keep | | Without it, an agent would add `origin`/`after` fields, a computed series or order checks. The viewer-v2 backlog item links it. | a GUI needs task relations |
| 2026-10-06-repository-facts-live-under-the-tasks-fo.md | keep | | Without it, an agent would add a file to the repository root (for example write a `.worktreeinclude`). The rule spans setup, workspaces and templates. | |
| 2026-10-06-sae-is-the-only-writer-of-state-and-even.md | remove | | The root `AGENTS.md`, `SKILL.md`, `_intent.md` and the CLI gates show it. Harness hooks were only deferred, not rejected. | |
| 2026-10-06-scale-by-uncertainty-breadth-and-stakes.md | remove | | `_intent.md` Principles states the three axes; `shape.md` and `plan.md` apply them. | |
| 2026-10-06-spec-review.md | remove | | The code, `shape.md` and `reviewer.md` ("Target `spec`") show it. The rejected options are minor. | |
| 2026-10-06-split-offer-one-question-and-never-force.md | keep | | Without it, an agent would make the planner flag size, or add a list of split signals (both rejected). | |
| 2026-10-06-task-ids-carry-date-and-time.md | remove | | The code shows the format; the reason against a counter is obvious. | |
| 2026-10-06-task-settings-in-their-own-file.md | remove | | The code shows it (the intent's own example). | |
| 2026-10-06-the-brief-instead-of-a-context-file.md | remove | | `tests/test_retired_terms.py` bans `context.md`. | |
| 2026-10-06-the-orchestrator-never-implements.md | keep | | Without it, an agent would "implement it yourself when it is small" in the main session. | the fast-lane backlog item (`2026-10-14-2150`) is shaped |
| 2026-10-06-the-task-record-is-untracked-while-it-ru.md | keep | | Without it, an agent would commit the task folder at `sae start`, or propose a compact record (both rejected). | committing the whole record turns out too heavy |
| 2026-10-06-two-languages-conversation-and-artifacts.md | remove | | The config and `SKILL.md` ("Smooth every quote") show it; its quote rule is already superseded. | |
| 2026-10-06-without-git-offer-git-init-and-no-snapsh.md | keep | | Without it, an agent improving no-git support would add automatic snapshots (rejected as too complex). | |
| 2026-10-06-workers-commit-on-their-branches.md | remove | | `worker.md`, `commit-message.md` and the dispatch trailers show it. | |
| 2026-10-06-worktrees-live-in-a-persistent-user-cach.md | keep | | Without it, an agent would move worktrees into the repository (`.tasks/.worktrees/`) or `/tmp`. The test-runner research says why not. | |
| 2026-10-07-a-dark-viewer-in-the-style-of-supabase.md | code comment | `skills/shape-and-execute/assets/viewer/app.css` (top) | One file: dark is the designed theme, in a Supabase style; light is a second token set; no equal themes by `prefers-color-scheme`. The viewer `README.md` already says "Dark theme first". | |
| 2026-10-07-codex-detection-by-its-thread-id-variabl.md | remove | | The comment at `CODEX_ENV_VARS` in `common.py` already says it, including why not `CODEX_SANDBOX`. | |
| 2026-10-07-evals-after-dogfood-and-before-the-publi.md | remove | | Superseded by the 2026-10-19 record. | |
| 2026-10-07-jobs-merge-into-the-task-branch-and-the.md | keep | | Without it, an agent would add a stop before each merge, or between dependency layers, in the interactive modes (both rejected). | |
| 2026-10-07-no-fits-one-session-prompt-at-intake.md | keep | | `_intent.md` says "a task that fits one context probably does not need the skill". Without the record, an agent would add a "this fits one session" prompt at intake. | the fast-lane backlog item (`2026-10-14-2150`) is shaped |
| 2026-10-07-one-list-of-hard-stops-for-every-mode.md | keep | | Without it, an agent writing a role protocol would paste a shorter copy of the hard stops again. The last copy had lost the no-git rule. | |
| 2026-10-07-references-split-into-modes-and-roles.md | remove | | The folder layout shows it; `agents/` is visibly taken. | |
| 2026-10-07-sae-checks-the-codex-subagent-cap.md | remove | | The comment in `common.py` (Codex caps open subagents…) and `codex_subagent_cap` show it. | |
| 2026-10-07-sae-re-runs-verify-up-to-a-per-task-limi.md | remove | | The code shows it. `reviews.py` already says why commits count since the first dispatch. The default living in code is in the no-configuration record. | |
| 2026-10-07-statuses-as-side-effects-and-generated-d.md | remove | | `prompts.py` and the CLI show it. It overlaps with follow-prose ("pointers, not pasted content") and with `_intent.md`. | |
| 2026-10-07-the-plan-gate-names-jobs-without-verify.md | code comment | `skills/shape-and-execute/scripts/sae_lib/graph.py` (`lint_plan`, the no-`verify` warning) | One file: a warning, not an error. Only judgement checks such jobs, and the plan gate lists them. A rule that every job must have `verify` was rejected. | |
| 2026-10-10-a-backlog-item-is-an-intent-file.md | remove | | The code shows it (`--backlog`, `--from`). Its pickup history is the start-is-atomic code. | |
| 2026-10-10-a-finding-always-has-a-body.md | remove | | The code refuses it; nobody would undo it. | |
| 2026-10-10-a-local-viewer-server-replaces-the-stati.md | code comment | `skills/shape-and-execute/scripts/sae_lib/server.py` (`run_write`) | One file: writes run `sae` as a subprocess, not the command functions in-process: they rely on the working folder and process state, and `sae` stays the only writer. The bind, token and idle stop are visible in the code. | |
| 2026-10-10-a-review-waits-for-its-target-to-be-done.md | code comment | `skills/shape-and-execute/scripts/sae_lib/graph.py` (`works_on_unmerged`) | One file: waiting for the merge would deadlock (round 2 waits for a merge that comes only after round 2). The docstring already links this record. | |
| 2026-10-10-backlog-pickup-at-start-and-start-is-ato.md | remove | | The code shows it: the undo stack in `cmd_start`, and `copy_untracked_repo_files` says why it copies and does not move. | |
| 2026-10-10-cheap-decisions-that-keep-the-door-open.md | keep | | Without it, an agent would write absolute paths into committed files, or drop `author`, the schema versions or the model trailers as unused. | the skill gets a team version |
| 2026-10-10-checks-always-cover-the-code-that-will-b.md | remove | | The code and tests show it (`stale_gate`, `reset_final_after_late_merge`). | |
| 2026-10-10-cleanup-never-destroys-unpreserved-work.md | remove | | The code shows it. `workspaces.py` already explains `branch -D` after the ancestry check. | |
| 2026-10-10-commands-never-write-into-a-finished-tas.md | remove | | `refuse_closed` and the read-only load in `tasks.py` show it; nobody would undo it. | |
| 2026-10-10-decision-records-are-drafted-where-the-c.md | keep | | Without it, an agent would write records straight into the ADR folder and skip the owner's triage gate. This task's writing rules build on it. | |
| 2026-10-10-every-setting-explains-itself-in-the-tab.md | code comment | `skills/shape-and-execute/assets/viewer/settings.js` ("texts behind every [?]") | One file: every setting gets a `[?]` for itself and each option; tabs in the order Task, Project, Global. | |
| 2026-10-10-every-subagent-gets-an-explicit-effort.md | keep | | Without it, an agent slimming `SKILL.md` or `prompts.py` would drop the explicit effort, and subagents would inherit the orchestrator's max effort. | |
| 2026-10-10-every-task-executes-in-its-own-task-work.md | keep | | Without it, an agent would add an in-place or `--worktree` option for small tasks (rejected: two paths). Code in `gitutil.py` and `tasks.py` links it. | |
| 2026-10-10-final-validation-is-a-planner-decision.md | remove | | `planner.md` states the criteria; nobody would undo it. | |
| 2026-10-10-finish-refuses-unresolved-review-finding.md | remove | | The code and tests show it; the rejected "warning only" is obviously weaker. | |
| 2026-10-10-finished-tasks-live-in-the-done-folder.md | remove | | The code shows it (the intent's own example). | |
| 2026-10-10-generated-reviews-carry-real-needs.md | remove | | The code shows it. The viewer `README.md` ("do not recompute them in the page") covers the rejected viewer-only placement. | |
| 2026-10-10-levels-per-phase-and-difficulty-per-job.md | remove | | The code shows it; the record is stale (`max` is now `premium`). | |
| 2026-10-10-one-job-or-its-review-can-run-on-another.md | code comment | `skills/shape-and-execute/scripts/sae_lib/routing.py` (`resolve_model`) | One file: an override applies only when the dispatch flag names its harness. A fallback must not send one harness's model to the other. | |
| 2026-10-10-planning-and-review-are-never-mechanical.md | code comment | `skills/shape-and-execute/scripts/sae_lib/routing.py` (`job_context`, "a review of a mechanical job") | One file: the existing comment states the rule. Add why: the owner rejected a weaker model for review. | |
| 2026-10-10-prototypes-live-in-the-task-folder.md | remove | | `shape.md` and `server.py` show it. | |
| 2026-10-10-read-only-commands-write-nothing.md | directory AGENTS.md | `skills/shape-and-execute/scripts/sae_lib/` | A rule for every command module: a read-only command takes no lock and writes nothing, and the writing command stores what it computed. A new command could break it. | |
| 2026-10-10-research-leaves-files-and-agents-are-res.md | remove | | The code (`--resume`) and `shape.md` show it. | |
| 2026-10-10-review-as-a-list-of-points.md | code comment | `skills/shape-and-execute/scripts/sae_lib/common.py` (`REVIEW_POINTS`) | One file: keep `selected-jobs` and `all-jobs`. One `jobs` value would need a migration of existing tasks. | |
| 2026-10-10-review-findings-are-claims.md | remove | | `worker.md`, `planner.md`, `execute.md` and the result template ("Disputed findings") show it. | |
| 2026-10-10-review-marks-show-the-review-that-will-r.md | remove | | The code and docstring (`review_mark`), tests and `planner.md` show it. | |
| 2026-10-10-review-provider-cross-harness-and-fallba.md | remove | | The code and `execute.md` show it; the verdict check's error message says why. | |
| 2026-10-10-routing-on-three-levels-global-project-a.md | remove | | The code shows it. "Project config stays outside the repository" is in the kept cheap-decisions record (overlap). | |
| 2026-10-10-routing-panel-with-one-dropdown-per-cell.md | remove | | The viewer `README.md` ("Rules for changing it") states the fixed, discrete colors; the code shows the layout. | |
| 2026-10-10-routing-tables-replace-rungs-and-level-m.md | remove | | The code shows it; `tests/test_retired_terms.py` bans "rung" and "level map". | |
| 2026-10-10-sae-creates-job-worktrees-from-the-task.md | keep | | Without it, an agent would switch to the harness's own worktree isolation. Claude Code bases it on the default branch, and Codex has none per subagent. | Claude Code bases subagent worktrees on the parent's HEAD and Codex gets per-subagent worktrees |
| 2026-10-10-sae-is-an-entry-point-plus-the-package-s.md | directory AGENTS.md | `skills/shape-and-execute/scripts/sae_lib/` | A folder rule: one module per area, none above about 1,000 lines. The entry point and Python 3.9 are already in `scripts/README.md` and the root `AGENTS.md`. | |
| 2026-10-10-sae-s-git-plumbing-skips-hooks.md | remove | | The comment at `HOOKS_OFF` in `gitutil.py` already says it, and why. | |
| 2026-10-10-settings-are-visible-and-change-only-on.md | remove | | `SKILL.md` and `_intent.md` ("agents change settings only on the owner's word") state it; the card diff is code. | |
| 2026-10-10-setup-files-come-from-the-main-worktree.md | remove | | The docstring of `copy_worktree_includes` already says it. | |
| 2026-10-10-the-graph-is-the-main-view.md | remove | | The code shows it (the Plan tab is the default). | |
| 2026-10-10-the-integration-review-has-rounds.md | remove | | The code and tests show it; the record is stale (`max_review_rounds`, default 3, replaced "a second round parks"). | |
| 2026-10-10-the-task-worktree-stays-until-the-task-b.md | remove | | The code shows it (the sweep, the final report). | |
| 2026-10-10-the-viewer-in-a-sandbox-without-a-file-f.md | code comment | `skills/shape-and-execute/scripts/sae_lib/viewer.py` (`check_sockets` / `cmd_view`) | One file: there is no `file://` fallback. A second viewer is a second code path for a rare case; `sae` prints the command for the owner's terminal. | |
| 2026-10-10-the-viewer-is-offered-at-task-creation-a.md | remove | | The code and `plan.md` show it. | |
| 2026-10-10-the-viewer-is-several-static-files.md | remove | | The viewer `README.md` states it: classic scripts, no build step, no external requests. | |
| 2026-10-12-a-process-map-starts-every-step.md | code comment | `skills/shape-and-execute/scripts/sae_lib/control.py` (`MAP_ARROW`) | One file: the `↓` line stays because a relaying agent drops blank lines; `⬥` for a pending gate read as done. | |
| 2026-10-12-a-retired-terms-test-instead-of-a-glossa.md | code comment | `tests/test_retired_terms.py` (docstring) | One file: the docstring has the mechanism; add "no glossary: it did not stop drift". | |
| 2026-10-12-agents-file-findings-and-the-owner-fills.md | keep | | Without it, an agent would let workers write backlog items or fix things on the side, or close findings in a triage step. The split between findings and backlog spans many files. | |
| 2026-10-12-decision-records-live-outside-the-skill.md | remove | | The root `AGENTS.md` ("Installs copy only this folder"; `docs/adr/`), the README and the ADR rules show it. | |
| 2026-10-12-docs-keep-only-the-why.md | keep | | Without it, an agent would bring back design docs or a CLI spec next to the code (four copies drifted). This task applies it. | |
| 2026-10-12-finish-removes-identical-untracked-copie.md | remove | | The docstring of `remove_identical_home_copies` already says it, and that a differing file stays. | |
| 2026-10-12-jobs-never-update-design-docs.md | keep | | Without it, a planner would add a docs-sync job, which biases the job toward confirming its own work. It overlaps with docs-keep-only-the-why, but this reason is distinct. | |
| 2026-10-12-model-lists-per-harness.md | remove | | The code and its validation show it (families, catalog checks). | |
| 2026-10-12-model-names-only-in-the-setup-proposal-a.md | keep | | Without it, an agent would hard-code a model name in a default or the viewer, or delete `CLAUDE_FAMILIES` as a "model name in code". The rule spans setup, server, viewer and tests. | |
| 2026-10-12-next-step-cards-and-holds-one-mechanism.md | remove | | The code shows it; the retired-terms test bans "launch card"; "`sae next` stays read-only" goes to the `sae_lib` `AGENTS.md`. | |
| 2026-10-12-one-format-for-decision-records-and-adr.md | remove | | The template, `adr_target_folder` and `tests/test_adr_rules.py` show it. | |
| 2026-10-12-owner-facing-output-is-english-and-sae-d.md | code comment | `skills/shape-and-execute/scripts/sae_lib/common.py` (`emit`) | One file: `emit` is where wrapping would come back. Add "wrapping prose to 72 columns failed three fix rounds". `SKILL.md` already has the relay rule. | |
| 2026-10-12-research-notes-follow-their-decisions.md | keep | | Without it, an agent would keep or add research notes that no record cites. This cleanup applies it ([DECISION-NOTES-FOLLOW]). | |
| 2026-10-12-setup-explains-itself-and-proposes-the-o.md | remove | | `setup.md` and `setup_mode.py` show it. | |
| 2026-10-12-tests-live-per-skill-at-the-repository-r.md | remove | | The root `AGENTS.md` names `tests/` and says installs copy only the skill folder. The record is stale ("one folder per skill"). | |
| 2026-10-12-the-sae-help-is-the-cli-reference.md | remove | | The retired-terms test bans `sae-cli.md`, `fill_missing_help` shows the help rule, and it overlaps with docs-keep-only-the-why. | |
| 2026-10-12-tiers-l1-to-l4-with-tiers-in-cells-on-by.md | code comment | `skills/shape-and-execute/scripts/sae_lib/setup_mode.py` (the `tiers_in_cells: True` proposal) | One file: the default stays on, although the owner works with it off. | |
| 2026-10-12-two-review-rounds-then-park.md | remove | | Stale: `max_review_rounds` (default 3) replaced the fixed two rounds; the code shows the rule. | |
| 2026-10-19-release-without-evals-evals-come-after-i.md | remove | | The release happened. The evals backlog item (`2026-10-18-1937`) carries the work; there is nothing for an agent to undo. | |

### Research notes

| File | Action | Kept records that link it |
|---|---|---|
| research/claude-code-facts.md | keep | explicit-invocation-only, every-subagent-gets-an-explicit-effort, sae-creates-job-worktrees-from-the-task |
| research/codex-facts.md | keep | explicit-invocation-only, sae-creates-job-worktrees-from-the-task |
| research/evals-landscape.md | remove | none (only the superseded evals record) |
| research/nested-worktrees-and-test-runners.md | keep | worktrees-live-in-a-persistent-user-cach |
| research/prose-spec.md | keep | follow-prose-without-ceremony |
| research/superpowers-evals.md | remove | none (only the superseded evals record) |
| research/viewer-file-protocol.md | remove | none (its record moves to a comment in `server.py`) |
| research/wayfinder.md | keep | big-work-goes-lazily-through-the-backlog |

### Links that a removal breaks

From outside `docs/adr/`:
- `README.md`, `AGENTS.md`: they link only the folder. Nothing breaks.
- `CREDITS.md`:21 (follow-prose) and :26 (`research/wayfinder.md`): both are kept. Nothing breaks.
- `.tasks/backlog/2026-10-18-1937--evals-mvp-and-a-non-interactive-entry-fo.md`:21 links three
  removed files: the evals-after-dogfood record, `research/superpowers-evals.md` and
  `research/evals-landscape.md`. Drop the links and say "removed from `docs/adr/`; see git
  history". Its link at :34 to `research/prose-spec.md` stays.
- `.tasks/backlog/2026-10-10-1136--github-sync.md`:55 links backlog-files-go-into-git-like-findings.
  Point it to `2026-10-10-cheap-decisions-that-keep-the-door-open.md`, which names claims and
  central storage as not addressed on purpose. Or drop the link.
- `.tasks/backlog/2026-10-13-1141--viewer-v2-…`:15 links relations-between-tasks (kept). Nothing breaks.
- Code comments that name a record:
  - `common.py`:71 (sae-re-runs-verify): drop the "(record …)" part.
  - `gitutil.py`:15 (git plumbing): drop it.
  - `lifecycle.py`:493 (done folder): drop it.
  - `workspaces.py`:114 (setup files): drop it.
  - `graph.py`:115 and `reviews.py`:311 (review-waits): replace the link with the moved reason.
  - `gitutil.py`:69 and `tasks.py`:85 link every-task-executes, which is kept.

Inside `docs/adr/` (for CLEANUP-APPLY):
- follow-prose links light-in-its-complexity: point to `_intent.md` (Principles).
- follow-prose links sae-re-runs-verify: drop the link; keep the words "`sae` re-runs `verify`".
- task-record-untracked links backlog-files: drop the link; the rejected option is stated in place.
- cheap-decisions links backlog-files: drop the link; "claims" is stated in place.
- docs-keep-only-the-why links the retired-terms record: point to `tests/test_retired_terms.py`.
- `research/wayfinder.md` links a-backlog-item-is-an-intent-file: drop the link, or point to
  `skills/shape-and-execute/templates/intent.md`.

### Path entries of kept records

Every path entry of the 25 kept records names an existing path; no correction is needed. Some
folder entries are broad, and under [WORKER-POINTERS] they will match almost every job in the
skill:
- docs-keep-only-the-why: `skills/shape-and-execute` (and the code name `wip-docs`, which never matches).
- follow-prose: `skills/shape-and-execute/references/roles`.
- one-skill-with-five-modes: `skills/shape-and-execute/references/modes`.

CLEANUP-APPLY may narrow them (for example docs-keep-only-the-why to `docs/adr`).

### Flags

Private data and quotes:
- `research/codex-facts.md` (kept) describes the owner's machine: the owner's live Codex
  catalog and model names, "the owner's default", the owner's `~/.codex/config.toml` and
  `max_threads = 8`. Smooth it to "a local catalog" and "a local config".
- `research/prose-spec.md` (kept) holds many word-for-word quotes from the handbook chapter.
  `CREDITS.md` says "No text is copied". It also names a local path to the owner's APM rules
  (`~/.claude/skills/apm-primitives/SKILL.md`, "the user's APM rules"). The owner decides
  whether to shorten the quotes and drop the path.
- Kept records with a stray `.` after a closing quote (`…children.".`): relations, split-offer,
  task-record, jobs-merge, no-fits, agents-file-findings, docs-keep-only-the-why,
  jobs-never-update-design-docs. All their quotes are in English and smoothed.
- The `source` field of every record still carries "design interview 2026-10-06 (Q…)" or
  "genesis review" references next to `DL-…`; [DECISION-DL-SOURCES] removes them.
- Kept records point to task records that this repository does not hold:
  - every-subagent-effort: `research/HARNESS-FACTS.md` of task 2026-10-08-1733.
  - research-notes-follow: `research/FORENSICS.md` of the same task.
  - docs-keep-only-the-why: the DESIGN-DOCS, DOCS-CHECK and DOCS-SYNC jobs.
  - decision-records-drafted: R3, R5.
  - jobs-merge: "Genesis A5".

  These are not private, but they lead nowhere; CLEANUP-APPLY may shorten them.
- Removing two-languages also removes the only "the owner talks to agents in Polish" line.

Decisions for the owner at the hold:
- The two eval notes (`evals-landscape.md`, `superpowers-evals.md`) are the basis of the evals
  backlog item. By the rule, they go, and git keeps them. If the owner wants them at hand, the
  other place is next to the backlog item (`.tasks/backlog/assets/` already exists). That is
  not an action this list can give.
- The "directory AGENTS.md" target `skills/shape-and-execute/scripts/sae_lib/` lies inside the
  skill, so it ships with every install. The other option is to move those two rows into code
  comments (`tasks.py` `open_task` for read-only commands; `scripts/README.md` for the module
  rule, which pointers do not find).
- The viewer's `assets/viewer/README.md` ("Rules for changing it") is that folder's
  instruction file in all but name. [DIR-POINTERS] finds only `AGENTS.md` / `CLAUDE.md`, so no
  prompt points to it. Several removals above lean on it.

## Validation evidence
- `git diff --quiet HEAD -- docs skills tests README.md CREDITS.md AGENTS.md`: exit 0. No
  repository file changed.
- Coverage: `ls docs/adr` gives 32 + 11 + 41 + 18 + 1 = 103 records. The table has 103 rows,
  one per file: 2026-10-06 (12 keep, 1 comment, 19 remove), 2026-10-07 (3, 2, 6),
  2026-10-10 (5 keep, 7 comment, 2 AGENTS.md, 27 remove), 2026-10-12 (5, 4, 9),
  2026-10-19 (1 remove). Totals: 25 + 14 + 2 + 62 = 103. Notes: 8 rows, 5 + 3.
- Every code-comment row names one file; every directory row names one folder.
- Every kept note is linked by at least one kept record (checked with a script over the
  `research/…` links of the kept records).
- A script checked every path entry of the kept records; all exist.
- Outside links: grep for `docs/adr` and record file names in `README.md`, `CREDITS.md`,
  `AGENTS.md`, `skills/`, `tests/` and `.tasks/`.
- Code claims behind "the code shows it" were checked in `sae_lib`:
  - existing comments at `HOOKS_OFF`, `CODEX_ENV_VARS`, `branch -D`, `copy_worktree_includes`,
    `remove_identical_home_copies` and `works_on_unmerged`;
  - `max_review_rounds` (default 3);
  - `LEVELS` uses `premium`;
  - `RETIRED` in `tests/test_retired_terms.py`.

## Decisions taken
- [agent] Where `_intent.md`, the root `AGENTS.md` or the viewer `README.md` already states a
  decision, the record counts as "shown" and is removed. Those files stay and are read.
- [agent] Records whose rule has since changed in the code (two review rounds, integration
  rounds, levels with `max`, tests "one folder per skill") are removed as stale, not corrected.
- [agent] Markdown references (`SKILL.md`, `references/…`) are not used as "code comment"
  targets: they ship and cost tokens in every run. A record whose only home would be such a
  file is kept or removed instead.
- [agent] revisit-when is filled only where the record itself names the condition, or where an
  open backlog item (fast lane, Orca) already proposes the change.

## Risks
- The line between keep and remove is judgement. The 62 removals assume the owner accepts
  "shown in `_intent.md` or a README" as shown.

## Findings filed
None.
