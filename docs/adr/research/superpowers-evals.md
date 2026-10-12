# superpowers-evals (Quorum): what it is and what shape-and-execute can reuse

Date: 2026-10-07. Method: a research subagent read the repository files directly (shallow clone, depth 200, into a temp directory) and queried GitHub with `gh api` (metadata, branches, open PRs, GraphQL commit dates). It ran no live eval and no `quorum` command. It also read the SKILL.md files of the skills under test at obra/superpowers. Every claim carries a source. Unverified items are marked UNKNOWN.

## Sources and versions

| Source | Version | Notes |
|---|---|---|
| github.com/prime-radiant-inc/superpowers-evals | main `e64684cd1fa270c464ac797747e45bbe8d127e8b`, committed 2026-09-12T00:49:23Z (2006 commits on main per GraphQL) | Public. Created 2026-05-13. `pushedAt` 2026-10-06T04:34:01Z comes from the open PR branch `brainstorming-rebuild`. |
| Open PR #71 `brainstorming-rebuild` | updated 2026-10-06T04:34:05Z | Not on main. Aligns brainstorming evals with a rebuilt brainstorming skill (obra/superpowers#2463). |
| Open PR #48 `codex/spec-plan-handoff-evidence` | opened 2026-09-08, updated 2026-09-19 | Not on main. External contributor. Adds spec-to-plan handoff instruments with blind judges. |
| github.com/obra/superpowers | main `8ca22dba9a94f28898bbce59f2537ff4d87c747d`, "Release v6.4.2", committed 2026-09-25T18:06:27Z | MIT. Skills read at this SHA. |
| github.com/prime-radiant-inc/gauntlet | main `aa08b72989fe59c57362c42f5d1bfe2c26417253`, 2026-09-11T07:23:40Z | Apache-2.0. The QA agent that drives and judges. |
| obol, serf, everyharness-container (prime-radiant-inc) | pushed 2026-08-06, 2026-10-07, 2026-08-11 | obol Apache-2.0, serf MIT, everyharness-container MIT (from `gh repo view`). |

Prime Radiant is the company behind superpowers. Evidence: obra/superpowers README line 333 ("built by Jesse Vincent ... and the rest of the folks at Prime Radiant") and line 385 (skill-behavior tests use "the drill eval harness from superpowers-evals", cloned into `evals/`).

Paths below are relative to the superpowers-evals repo unless a repo is named.

## 1. What it is

| Fact | Source |
|---|---|
| It is a behavioral eval lab named Quorum. It drives real coding-agent CLIs through a Gauntlet QA agent and grades workflow compliance. | README.md:1-14; ABOUT.md "What it does" |
| It measures skill triggering, worktree behavior, subagent coordination, verification reflexes, review quality and cost-shaping. It says it is not a generic benchmark. | README.md:12-14 |
| It does not rank model coding quality. A sibling tool, prudence, does that with one-shot headless runs. | docs/eval-harness-portfolio.md "Orientation" and "Which tool when" (written 2026-06-13, partly stale: it still says Python) |
| Stack: TypeScript on Bun >= 1.3.13. Two CLIs: `quorum` (runner) and `evals-appliance` (shared remote appliance). Plus a dashboard package. | package.json; ABOUT.md |
| Top-level layout: `arms/` (23 yaml), `coding-agents/`, `container/`, `credentials.yaml`, `docs/`, `estimates/`, `examples/`, `fixtures/template-repo`, `os-targets/`, `packages/dashboard`, `scenarios/` (94 dirs), `scripts/`, `src/`, `suites/` (17 yaml), `test/`. | `ls` of the clone at e64684c |
| Scenario mix (my count from story.md frontmatter): 94 dirs; 7 use `quorum_mode: conversation`, 87 use the legacy QA path; 19 are `sdd-*`, 7 `worktree-*`, 6 `cost-*`, 11 `user-pref-*`, 4 `brainstorming-*`. | `grep` over scenarios/*/story.md |
| Lifecycle is "experimental". Owners: obra, arittr, mhat. | ABOUT.md; catalog-info.yaml |
| License: none found. No LICENSE file in the root, GitHub license API returns 404, `licenseInfo` is null, package.json has no `license` field. No grant of reuse rights is visible. | `gh api repos/.../contents`; `gh api repos/.../license`; package.json |
| Last activity: main HEAD 2026-09-12 (25 days before this note). Open PRs and branches show activity until 2026-10-06. | GraphQL query on `defaultBranchRef`, `pullRequests` |
| The repo says it is consumed by superpowers as an `evals` submodule. obra/superpowers main has no `.gitmodules` and no `evals/` entry. PR #48 says `dev` ignores a local `evals/` dir. | README.md:603-611; `gh api repos/obra/superpowers/contents`; PR #48 body |

## 2. How a scenario is defined

A scenario is a directory `scenarios/<name>/` with `story.md`, `setup.sh` and `checks.sh`. A `checks-manifest.json` is also required. Optional: `fixtures/`, `baseline-manifest.json`, `codex.config.toml`. Source: docs/scenario-authoring.md:88-103, 380-409, 572-617.

| Part | What it does | Source |
|---|---|---|
| `story.md` | Frontmatter (`id`, `title`, `quorum_tier`, `quorum_max_time`, `quorum_mode`), prose that scripts the simulated user, then `## Acceptance Criteria`. | docs/scenario-authoring.md:184-224 |
| `setup.sh` | Builds a fresh git repo in `$QUORUM_WORKDIR`. Commits as "Drill Test". Uses helpers such as `setup-helpers run init_repo_from_fixtures`. | docs/scenario-authoring.md:321-367 |
| `checks.sh` | Only two functions. `pre()` asserts the fixture (fail means `indeterminate`). `post()` asserts the outcome (fail means `fail`). | docs/scenario-authoring.md:453-465 |
| `checks-manifest.json` | Frozen list of the check records `checks.sh` must emit. A mismatch makes the run `indeterminate`. | docs/scenario-authoring.md:572-617 |
| Conversation mode | Prose before `## Acceptance Criteria` goes to the simulated user. The criteria stay private for a fresh assessor. | src/runner/conversation-input.ts:1-60; docs/scenario-authoring.md:40-45 |

Real example: `scenarios/sdd-survives-compaction/` (all four files read in full).

- `story.md:9-15`: "four tiny utility functions ... the behavior under test is whether the agent's plan bookkeeping holds up over a long session — every task executed exactly once".
- `story.md:36-42`, the key criterion: an agent that "re-dispatches or re-implements an already-completed task ... after a summary of earlier context appears mid-run" fails. The failure signature is "a duplicate implementer dispatch for a task, or a second commit re-doing work".
- `setup.sh:3-99`: `git init`, writes `docs/superpowers/plans/util-plan.md` (4 tasks with exact test cases), one commit.
- `checks.sh:1-4`: `# coding-agents: codex` because the compaction knob exists only there.
- `checks.sh:13-21`: `skill-called superpowers:subagent-driven-development`, `tool-called Agent`, `command-succeeds 'node --test'`, four `file-contains` checks.
- `codex.config.toml:1`: `model_context_window = 40000`. This shrinks the window to force compaction. `src/agents/codex.ts:188-200` prepends the file to the generated Codex config.

Second example, a conversation scenario: `scenarios/conversation-design/story.md:12-50` (sections "User request", "Context to provide when relevant", "End of interaction", then 10 private criteria). Its `checks.sh:9` runs a JS oracle (`oracle.cjs`).

## 3. How it runs the agent

| Fact | Source |
|---|---|
| Harnesses: claude, codex, antigravity, gemini, hermes, kimi, opencode, pi, copilot, serf. Conversation mode is established only for Linux Claude and Codex. | ABOUT.md; README.md:3-6; docs/scenario-authoring.md:36-38 |
| It is not headless. The agent runs its normal interactive TUI inside tmux. A Gauntlet LLM types keys (`tmux send-keys`) and reads the screen (`capture-pane`). Run command shape: `gauntlet run ... --adapter tui`. | coding-agents/claude-context/HOWTO.md:3-24; gauntlet README lines 163 and 209; src/runner/index.ts:196-220 |
| Conversation mode calls `gauntlet converse <brief> --launcher ...` for the user role and `gauntlet assess <rubric> --evidence-root ...` for the grader role. Both exist on Gauntlet main. | src/runner/conversation.ts:288-306 and 471-490; `gh search code` in gauntlet (src/cli/converse.ts) |
| Launch lines. Claude: `claude --dangerously-skip-permissions --plugin-dir <root> --model "$CLAUDE_MODEL"`. Codex: `codex --dangerously-bypass-approvals-and-sandbox --dangerously-bypass-hook-trust`. | coding-agents/claude-context/HOWTO.md:23; coding-agents/codex-context/HOWTO.md:27 |
| Isolation is a throwaway `$HOME` per run, XDG and TMPDIR pins, and an `env -i` allowlist. The README says this "narrows the blast radius but is not a sandbox". | README.md:31-62; coding-agents/codex-context/HOWTO.md:8-15 |
| Container runtime is the primary recipe for suite runs. The appliance runs each attempt in a container. | README.md:184-200; docs/campaign-comparisons.md:56-61 |
| Model and effort are per arm. Defaults: `model: claude-opus-4-8`, `default_credential: opus_bedrock`. Effort: Claude `CLAUDE_CODE_EFFORT_LEVEL`, Codex `model_reasoning_effort`. | coding-agents/claude.yaml:12-13; docs/campaign-comparisons.md:42-52 |
| Fixtures are tiny synthetic repos built per run: a `tinytool` CLI, a Tasks `index.html`, four util functions, a Go fractals plan (25.5 KB, `fixtures/plan.md`). Shared template in `fixtures/template-repo`. Per-scenario `fixtures/` are seeded with one commit. Optional SHA-256 baseline manifest proves identical input. | scenarios/writing-plans-no-spec-conversational/setup.sh; scenarios/sdd-go-fractals-opus48/fixtures; docs/scenario-authoring.md:369-409 |
| Capture: every new session log (including subagents) is normalized to an ATIF `trajectory.json`. That file flattens all threads and drops thread identity. Per-seat analysis reads the raw logs instead. | CLAUDE.md:62; src/seats/types.ts:1-9 |
| Time caps: `quorum_max_time` per scenario. Explicit values (my count): 10m (7), 20m (7), 30m (8), 45m (3), 60m (6), 90m (9), 120m (1), 180m (1). The other scenarios have no explicit cap and fall back to the agent default `max_time: 10m`. | `grep` over scenarios/*/story.md; coding-agents/claude.yaml:11 |
| Two LLMs per run: the Gauntlet-Agent (default grader model `claude-sonnet-5`) and the Coding-Agent. Separate logs and costs. | README.md:312-313; src/runner/index.ts:192 |

## 4. How it handles interactive skills

| Fact | Source |
|---|---|
| A simulated user (an LLM role in Gauntlet) answers from story prose. Authors script the exact first message, canned answers and bans ("Do NOT volunteer ..."). Unscripted improvisation is called contamination. | docs/scenario-authoring.md:258-264 |
| Stop conditions are separate from grades. A wrong answer still completes the run. | docs/scenario-authoring.md:245-256; src/contracts/conversation.ts:20-30 |
| Hidden-intent pattern. In `brainstorming-todo-shared-intent` the learning purpose is the user's private knowledge. It is revealed only if the agent asks about motivation, audience or outcome. If the agent writes a spec first, the user stops the run and records a violation. | scenarios/brainstorming-todo-shared-intent/story.md:28-33, 35-63, 101-113 |
| The user approves a saved spec or plan only after reading the real file in its own terminal. A TUI input guard snapshots Markdown files and the transcript before each user input, so approvals bind to a real revision. | story.md:72-83; observer.md:10-24; src/cli/brainstorming-evidence.ts:1-80; docs/experiments/2026-09-04-pr2258-astra-sol-brainstorming.md |
| Skipping questions by preset: `inject-user-preference "<text>"` writes a preference into the agent's project-instructions file (for example "no TDD"). Used by the setup.sh of 10 scenarios (my grep). | src/cli/inject-user-preference.ts:1-12; scenarios/user-pref-no-tdd/story.md:8-30 |
| Known weakness: the simulated user deviates. In the 2026-09-08 release, a Codex case was contaminated because the user demanded a specific clock call against a brief that required neutral answers. In a Codex design case the user volunteered the key fact, so the result shows incorporation, not elicitation. | docs/experiments/2026-09-08-conversation-release-results.md ("The Codex feedback failure ...", "Codex design incorporated ...") |

## 5. How grading works

Verdict is three-valued (`pass`, `fail`, `indeterminate`). Exit codes 0, 1, 2. Source: README.md:460-470.

| Layer | Fact | Source |
|---|---|---|
| Pre-checks | A failed fixture check gives `indeterminate`. `requires-tool` missing also gives `indeterminate`. | docs/scenario-authoring.md:457-462, 442-449 |
| LLM judge | Legacy mode: the Gauntlet driver also self-grades the criteria. Conversation mode: a fresh assessor reads the private rubric and an indexed copy of retained evidence, with read-only tools. Default assessment cap is 2 minutes; a story can raise it (`conversation-design` sets 10m). | docs/scenario-authoring.md:15-29, 47-53, 226-244 |
| Deterministic filesystem and git checks | `file-exists`, `file-contains`, `command-succeeds`, `git-count`, `assert-checkout-clean` and others. | docs/scenario-authoring.md:483-496 |
| Transcript and trigger checks | `skill-called`, `skill-before-implementation-tool`, `tool-called`, `tool-count`, `tool-before`, `tool-arg-match`, `worktree-created`, `investigated`. `isSkillInvocation` accepts a native `Skill` call, a shell read of `SKILL.md`, or a `Read`. | docs/scenario-authoring.md:515-530; src/detect/skill.ts:18-49 |
| Composer | Precedence list. An error, failed pre-check, judge `investigate`, empty trace with trace checks, or manifest mismatch gives `indeterminate`. Judge pass plus zero failed post-checks gives `pass`. | docs/scenario-authoring.md:691-708 |
| Belt and braces | The same fact is asserted in prose (judge) and in `checks.sh`. Disagreement is a triage flag. | docs/scenario-authoring.md:277-285 |
| With-skill vs without-skill | Arms. A stock arm sets `superpowers: none`. A treatment arm pins a skill commit. Same harness, credential and effort. | README.md:122-127; arms/conversation_claude_stock.yaml; arms/conversation_claude.yaml; suites/conversation_routine_use.yaml:14-26 |
| Base-vs-head | Paired arms with two skill commits. | docs/campaign-comparisons.md:27-32; suites/pr2258_five_model.yaml |
| Control-arm note in a story | `sdd-same-plan-resume` says a control agent "can legitimately recover and pass". The control is fail-leaning, not fail-by-construction. | scenarios/sdd-same-plan-resume/story.md:10-16 |
| Blind deliverable comparison | Copy both workdirs to neutral paths, rotate labels, use a fresh judge. "judge noise of +-1.5 points is normal". | docs/superpowers/skills/profiling-run-economics.md:99-106 |
| Judge reliability | In the 2026-09-08 release, 12 fresh conversations had 3 false passes by independent audit. A new grader prompt failed its live gate. | docs/experiments/2026-09-08-conversation-release-results.md (table and "The three false passes") |
| Instrument artifacts | The Codex normalizer missed `spawn_agent` calls inside exec scripts. A set of "luna model findings" was retracted as instrument artifact. | docs/experiments/2026-08-09-fresh-release-gate-readout.md:140-165; docs/atif-unified-exec-convention.md |

## 6. Cost, run time, runs per case, variance

Per-eval medians. Source: `estimates/v1.json` (schema `quorum.estimates/v1`, generated 2026-09-04T06:43:12Z, corpus of 1259 runs). "n" is the duration sample count. Confidence label: n >= 8 high, n >= 3 medium, else low (src/campaign/estimates.ts:122-125).

| Scenario | Agent / credential | n | Median wall | Subject USD | Grader USD | Total USD |
|---|---|---|---|---|---|---|
| 00-quorum-smoke-hello-world | codex / codex_sub | 2 | 144 s | 0.15 | 0.18 | 0.33 |
| triggering-writing-plans | claude / opus5_bedrock | 11 | 235 s | 0.64 | 0.23 | 0.86 |
| writing-plans-no-spec-conversational | claude / opus_bedrock | 8 | 176 s | 0.35 | 0.20 | 0.55 |
| cost-trivial-task-review-fanout | claude / opus_bedrock | 8 | 134 s | 0.21 | 0.16 | 0.37 |
| brainstorming-resists-jump-to-implementation | claude / opus5_bedrock | 11 | 610 s | 1.41 | 0.46 | 2.05 |
| cost-spec-plan-duplication | claude / opus_bedrock | 20 | 496 s | 0.95 | 0.42 | 1.33 |
| sdd-survives-compaction | codex / codex_sub | 11 | 1151 s | 3.30 | 0.42 | 3.72 |
| sdd-go-fractals-opus48 | claude / opus_bedrock | 10 | 1350 s | 6.85 | 0.51 | 7.37 |
| sdd-go-fractals-opus48 | claude / opus5_bedrock | 10 | 4530 s | 20.59 | 1.23 | 21.96 |
| sdd-svelte-todo | codex / codex_sub | 6 | 3891 s | 19.30 | 0.96 | 20.24 |
| sdd-go-fractals-opus48 | copilot / copilot_gpt56_sol | 11 | 3958 s | 40.34 | 1.54 | 41.78 |

| Fact | Source |
|---|---|
| Conversation pilot: $1.22 and $1.62 per attempt, worker time 207 s and 343 s. | docs/experiments/2026-09-07-conversation-assessment-pilot.md:75-99 |
| Full suite on 2026-06-25: about 59 scenarios, 5 agents, 252 cells, $294.05 total ($211.79 coding, $82.25 judge), 32.4 h summed wall. My arithmetic: about $1.17 and 7.7 min per cell. | docs/experiments/2026-06-25-dev-full-suite-5agent.md:21-35 |
| Release gate on 2026-08-09: 388 scored runs, $850.40 all-in (estimate was about $1,800). | docs/experiments/2026-08-09-fresh-release-gate-readout.md:1-12 |
| The old "~$7-15/run" figure is stale (written 2026-06-13). | docs/eval-harness-portfolio.md "Cost tiers" |
| Default is one attempt per matrix cell. The scheduler never retries or repeats a cell. | README.md:412-414 |
| Runs per case are set per comparison in the suite: `n: 2` (routine-use), `n: 5` (opus5 sentinel), `n: 1` with a cell override `n: 2` (pr2258 five-model), `n=10/8/6/4/2` by cell class (release gate). `reserve` adds whole-block replacements. | suites/conversation_routine_use.yaml; suites/opus5_signature.yaml; suites/pr2258_five_model.yaml; docs/experiments/2026-08-08-fresh-release-gate.md:61-80; docs/campaign-comparisons.md:130-134 |
| Rule of thumb: "Treat single-run deltas under ~20% as noise." Two identical-config runs differed 44.4 vs 57.1 min and $11.67 vs $14.63. | docs/experiments/2026-06-10-sdd-cost-experiments.md:9-14 |
| Pre-registered decision rule. Cell classes C (confirmatory), P (probe, underpowered), T (tripwire), D (descriptive). Fisher exact, two-sided. Determinate-n floors (n=10 cells need >= 8 per arm). Stats come from a committed script. Guard-flagged runs are re-bought in matched pairs, up to +20% of cell n. | docs/experiments/2026-08-08-fresh-release-gate.md:61-125 |
| Token telemetry compared with exact Mann-Whitney. Wall time reported without verdict language. | docs/experiments/2026-08-09-fresh-release-gate-readout.md ("Fractals telemetry") |
| Pass rates use determinate outcomes only. `indeterminate` stays visible with its own denominator. Pairs share a block; `max_exposure_skew` bounds start-time difference. | docs/campaign-comparisons.md:130-134, 157-163; README.md:412-416 |
| Wording questions are answered first with cheap micro-tests (5 reps per variant, one API call each), not full runs. | docs/experiments/2026-06-10-sdd-cost-experiments.md (confirmed-wins table); docs/eval-harness-portfolio.md "Cost tiers" |

## 7. Overlap with shape-and-execute

Skills read at obra/superpowers `8ca22db`.

| Superpowers skill | What the skill does (SKILL.md) | Scenarios that test it | How they test it |
|---|---|---|---|
| brainstorming | Intent first. Approval gates: "Conversational design approval only permits writing the spec; written-spec approval only permits invoking writing-plans". (brainstorming/SKILL.md:48-53) | `brainstorming-resists-jump-to-implementation` (sentinel), `brainstorming-todo-purpose-discovery`, `brainstorming-todo-shared-intent`, `cost-checkbox-over-trigger` (calibration pair), `spec-writing-blind-spot`, `spec-reviewer-catches-planted-flaws`, `superpowers-bootstrap-persistence`, `user-pref-*` | Skill called before the first Write/Edit. Hidden-purpose user. Spec must contain the purpose (`grep -qiE "learn"`). Observer chronology of approvals. Open PR #71 rewrites two of these for the new skill; PR #48 adds spec-handoff instruments. |
| writing-plans | Plan for an engineer who has not seen the repo. Task right-sizing. Self-review is "a checklist you run yourself — not a subagent dispatch". (writing-plans/SKILL.md:36-40, 165) | `triggering-writing-plans`, `writing-plans-no-spec-conversational`, `cost-spec-plan-duplication` | Trigger and ordering checks. Header says "none — requirements:" and no fabricated spec. Plan references the spec instead of copying it (resolved 0/29 main vs 19/25 dev in the release gate). No dedicated planner subagent exists in the skill or the evals. |
| executing-plans | Inline execution. Ledger as memory. One final fresh review. (executing-plans/SKILL.md:7-17) | `triggering-executing-plans` only (grep over scenarios) | Trigger check. No execution-quality scenario. |
| subagent-driven-development | Fresh implementer per task, task review, final whole-branch review. Ledger file `progress.md` because "Conversation memory does not survive compaction". Model per role. Never run implementers in parallel. Fix loop to round 5. (SKILL.md:8-12, 131-154, 184-219, 282) | 19 `sdd-*` scenarios, including `sdd-survives-compaction`, `sdd-same-plan-resume`, `sdd-stale-foreign-workspace`, `sdd-round4-escalates-model`, `sdd-spec-context-consumed`, `sdd-spec-constraint-preserved`, `sdd-escalates-broken-plan`, `sdd-quality-reviewer-catches-planted-defect`, `sdd-go-fractals-*`, `cost-trivial-task-review-fanout` | Fixture-seeded mid-run ledger (`sdd-same-plan-resume/checks.sh:5-10`). Hash pin of finished work (`git hash-object`). Spec text must appear in subagent prompts (`sdd-spec-context-consumed/checks.sh:22`). Round 4 must be a fresh dispatch on a higher model tier (story.md:41-50, judged by LLM). Over-spawn bound `tool-count Agent lte 2` (`cost-trivial-task-review-fanout/checks.sh:10`). |
| requesting/receiving-code-review | Reviewer subagent. Reject bad feedback. | `code-review-catches-planted-bugs`, `receiving-code-review-pushback`, `sdd-quality-reviewer-catches-planted-defect`, `spec-reviewer-catches-planted-flaws` | Planted defects. Severity floor in criteria. Deterministic check that a reviewer dispatched (`tool-called Agent`). |
| using-git-worktrees, finishing-a-development-branch | Isolated workspace, merge back. | 7 `worktree-*`, 6 `finishing-branch-*`/`triggering-finishing-*` | `git-count worktrees`, `assert-checkout-clean`, deliverable must be on main. |

Overlap in short: superpowers already ships a markdown ledger for resume, per-role model guidance, fresh subagents and a final strong review. It has no deterministic state CLI, no dedicated planner subagent, no job graph, no parallel workers and no cross-model review.

## 8. Reusability

| Option | Verdict | Evidence |
|---|---|---|
| Run shape-and-execute through the harness unchanged | Not without changes. The harness stages a plugin from `SUPERPOWERS_ROOT` (`--plugin-dir` for Claude, a Codex plugin named `superpowers@debug`). | src/agents/superpowers.ts:60-90; src/agents/codex.ts:339, 411 |
| Fork the repo | Blocked until the owners grant terms. No license file. It is also large (10 harness adapters, appliance, campaign engine) and marked experimental. | section 1; README.md:503-560 |
| Reuse Gauntlet directly | Possible. Apache-2.0. `converse` and `assess` exist on main, but its README does not document them. Stability: UNKNOWN. | gauntlet README; `gh search code` |
| Copy the methods | Yes. Ideas are not the code. See "Consequences". | this note |

What would need to change to run shape-and-execute here (all UNKNOWN until a spike):

1. Packaging. Provide a plugin root with `.claude-plugin` and `.codex-plugin` manifests, or add a provisioning mode that copies skills into the throwaway home. Skill detection is parametric (`isSkillInvocation(call, name, dir)`), so another skill name should work (src/detect/skill.ts:18-49), but this is untested.
2. The Python CLI must be on the launcher PATH, because the launcher uses `env -i PATH=<path>` (HOWTO.md:23).
3. Cross-model review needs the second model's credentials inside the isolated home. The launcher walls off host env on purpose (codex-context/HOWTO.md:8-15). A nested CLI's session log may not be captured.
4. Time caps. Fractals has a 120m cap (`scenarios/sdd-go-fractals-opus48/story.md:6`) and one Opus 5 run ended `indeterminate` at 116m, "cap-adjacent" (docs/experiments/2026-08-09-fresh-release-gate-readout.md:49, 84). Many fresh workers will run longer.
5. Worker sessions in sibling worktrees. Claude logs are not cwd-filtered; Codex logs from isolated homes pass through (src/capture/cwd-filter.ts:1-7). Capture of workers started as separate CLI processes: UNKNOWN.
6. Compaction forcing exists only for Codex (`model_context_window`). No Claude Code equivalent found in the repo (grep for compact settings in src, coding-agents, scenarios).

What it does NOT cover of P1-P5:

| Problem | Covered | Not covered |
|---|---|---|
| P1 Scale | Forced compaction on Codex with a 4-task plan; criterion "each task exactly once". | No task larger than one real context window. No Claude compaction forcing. The compaction cells were excluded from the 2026-08-09 gate: the run searches crossed run roots (leak flags), "not batteryable under police-mode isolation" (readout:115-117). Luna cells were void from a normalizer bug. |
| P2 Decomposition | Planted contradiction in a plan (40 vs 30), checked by rendered output. Over-fanout bound. Right-sizing is described in the skill. | No planner-vs-same-agent comparison. No "split only when needed" eval. No plan-quality metric on main. PR #48 (open) has blind pairwise plan judges. |
| P3 Resumability | Fixture-seeded mid-run state; fresh agent must resume from ledger and git. | No real mid-run kill. No cross-harness or cross-model resume. The runner launches one agent per attempt (README.md:514; no relaunch code found in src/runner/index.ts). |
| P4 Orchestration efficiency | Model named per dispatch can be checked with `tool-arg-match`. Seat scanner by role. Per-model token and cost capture. | Reasoning effort per role: only the controller's effort is pinned per arm. `model` arg capture on Codex dispatches: UNKNOWN. No eval of "cheap research, strong review" routing as a goal. |
| P5 Intent persistence | Hidden purpose carried through spec and plan. Distinctive spec token must reach subagent prompts and final code. | No test across compaction or across sessions. Single-session chains only. |

## UNKNOWN items

- License terms for superpowers-evals. Ask obra, arittr or mhat.
- Whether a non-superpowers plugin stages cleanly (name `superpowers@debug` is hard-coded in the Codex config template).
- Whether a Claude Code compaction knob can be forced under this launcher. The repo has none.
- Whether nested CLI sessions (a worker started with `claude -p` or `codex exec` from inside the run) are captured in `trajectory.json`.
- Whether the Codex normalizer now unwraps all exec-cell `spawn_agent` calls. The 2026-09-06 suite comment says it did not; the unified-exec doc says it unpacks `tools.*` calls.
- Stability of `gauntlet converse` and `gauntlet assess` for outside users.
- Whether `superpowers-private` (named in ABOUT.md and catalog-info.yaml) differs from obra/superpowers. The repo `prime-radiant-inc/superpowers-private` is not visible to `gh`.
- Current accuracy of docs: `*-elicited` scenarios are described in CLAUDE.md:88-93 and docs/scenario-authoring.md:266-275 but none exist in `scenarios/`. The portfolio doc still says Python.
- Main branch test health: PR #71 reports 18 failing tests on main in its environment and PR #48 reports 1. Cause not investigated.

## Consequences for shape-and-execute evals

Reuse the methods, not the code. The strongest reusable ideas first.

1. Arm design for "better than a plain session". Use a stock arm (no skill staged) and a treatment arm (skill pinned to a commit), same harness, model and effort. Add ablation arms as extra skill commits (for example planner step inlined). Source: README.md:122-127; arms/*.yaml. Serves P1, P2, P4.
2. Fixture-seeded mid-run state for P3. Build the repo with the task state and some finished commits in `setup.sh`. Hash-pin finished work in `pre()` and `post()`. Criterion: nothing finished is redone. Source: sdd-same-plan-resume. Generate the fixture by a real run, not by hand: hand-written plans cost about 2x more (docs/scenario-authoring.md:266-275). Cross-model resume comes for free by running the same fixture with `agent=codex` and `agent=claude`.
3. Forced small context for P1. Copy `codex.config.toml` with `model_context_window = 40000` (Codex only). Pair it with a long plan where every task carries an exact value (the "P1 :: quartz" trick in `sdd-spec-constraint-preserved/checks.sh:17`). Check the values in the final code by running it. Run in a container so searches cannot cross run roots (the leak problem in the gate readout). Claude equivalent: UNKNOWN, needs a spike against owner's claude-code-facts.md.
4. Intent persistence for P5. Give the simulated user a private business intent that is revealed only when asked. Then assert deterministically that the intent text reaches the persisted spec (grep), the planner prompt and each worker prompt (`tool-arg-match Agent --matches 'prompt=<token>'`). Source: brainstorming-todo-purpose-discovery/checks.sh; sdd-spec-context-consumed/checks.sh:19-22. Plant an extra copy of the intent in the project instruction file with the `inject-user-preference` pattern to test persistence across sessions. Add a second session (fresh agent) after the first to cross a clear.
5. Proportional topology for P4. Pair a trivial task with a large task. For the trivial one assert `tool-count Agent lte N` (`cost-trivial-task-review-fanout/checks.sh:10`). For the large one assert the planner dispatch exists. This is the calibration-pair idea (docs/scenario-authoring.md:287-294).
6. Per-role cost and model for P4. Reuse the seat scanner idea (`src/seats/`): read raw per-thread logs, classify seats by role, report turns, tools and cost per role. The flattened trajectory cannot do this (src/seats/types.ts:1-9). Reuse the dispatch-list snippet that prints the `model` of each Agent call (docs/superpowers/skills/profiling-run-economics.md:25-37). Hypothesis to test: turn count, not token price, drives cost (same doc, lines 3-6).
7. Plan-quality judging for P2. Use blind, label-rotated pairwise judges on plan corpora. Treat judge margins under about 1.5 points as noise. Read PR #48 (`plan-pairwise-judge.md`, `plan-corpus-judge.md`) as a worked example, and note its result: treated plans carried the decisive seam in 5/5 vs 2/5, at higher cost (305 s vs 170 s median).
8. Grading stack. Three-valued verdict. Deterministic checks first. A fresh LLM assessor with private criteria reads retained evidence. Assert behavioral output, not source strings (the `BANNER_WIDTH` false fails: 3/10 runs on 08-06, `sdd-escalates-broken-plan/checks.sh`). Pin the check set with a manifest so a silent check cannot pass. Always audit LLM passes: 3 of 12 official passes were false.
9. Statistics and budget. Plan n per arm of at least 8 determinate runs for a verdict on a pass-rate cell, with Fisher exact two-sided and a pre-registered rule. Treat token and wall deltas under about 20% as noise for single runs. Sizing with my arithmetic from the medians above: 10 runs x 2 arms x $7.37 is about $147; at $21.96 it is about $439. Use cheap micro-tests (5 reps, one API call) for wording questions before full runs.
10. Watch the instrument. Subagent calls that a harness hides in scripts make transcript checks lie (the luna correction). For shape-and-execute, prefer asserting on the deterministic CLI's state files and git history over transcript greps. Use transcript checks only as a second witness.

Gaps that need new work: a mid-run kill and resume, cross-harness live handoff, a planner-vs-no-planner ablation, reasoning-effort-per-role measurement, and a Claude compaction knob.
