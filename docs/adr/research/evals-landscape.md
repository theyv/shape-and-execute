# Evals landscape for shape-and-execute: existing benchmarks, fixtures and harnesses

Question: which existing benchmarks, fixture projects or eval harnesses can be reused to show that
shape-and-execute beats a plain session (same model) on P1 scale, P2 decomposition, P3
resumability, P4 orchestration efficiency and P5 intent persistence? What must be built custom?

Date: 2026-10-07. Research subagent (Sonnet 5.5), read-only on the repo; this is the only file written.

## Method

- Candidates found by web search, then verified against primary sources only.
- Papers: arXiv PDFs downloaded and read as text (abstract, setup, tables, appendix).
- Repos: GitHub API (`gh api`) for license, last push, stars; README and adapter code read.
- All repo metadata is as of 2026-10-07. "Last push" means the default branch.
- Nothing was run. No cost below was measured by me. Costs are the papers' own numbers.
- Search-engine summaries were used to find leads only, never as a source for a claim.
- UNKNOWN means: not stated in the sources I read, or not verifiable. No guesses.
- Terms: P1..P5 are the owner's five problems (see the task brief). "CC" is Claude Code.

## Table 1: facts per candidate (large-task and interactive benchmarks)

| Candidate | Task size (exceeds one window?) | Grading | Local run with CC or Codex | Cost and time | License; maintenance |
|---|---|---|---|---|---|
| [RoadmapBench](https://arxiv.org/abs/2605.15846) ([repo](https://github.com/UniPat-AI/RoadmapBench)) | 115 tasks, 17 repos, 5 languages. Median oracle patch 3,700 lines in 51 files; 3 to 12 subtasks (median 5), no prescribed order. Exceeds one window: UNKNOWN (not stated). | Hidden per-target tests; weighted Completion Score plus Resolved Rate. No LLM judge. | Harbor task format, so `harbor run --agent claude-code` or `codex` works in principle ([Harbor](https://github.com/harbor-framework/harbor)). README shows only Terminus-2 and OpenHands. Docker. | 2 h wall-clock cap per task. Opus 4.7 averaged 140 turns and 44K output tokens. Dollar cost per task: UNKNOWN. | MIT. Last push 2026-05-19, 16 stars. Dataset 453 MB ([HF](https://huggingface.co/datasets/UnipatAI/RoadmapBench)). |
| [ProgramBench](https://arxiv.org/abs/2605.03546) ([repo](https://github.com/facebookresearch/ProgramBench)) | 200 tasks. Agent gets a compiled binary and docs, must rebuild the program. Median codebase 8,635 lines, 93 files; up to FFmpeg, SQLite, PHP (1.97M lines). Longest trajectory 1,978 turns. Exceeds one window: UNKNOWN (not stated). | Hidden behavioral tests from agent-driven fuzzing (median 770 per task). Pass rate plus Resolved plus Almost-resolved. No LLM judge. | Baseline is mini-SWE-agent. [Harbor adapter](https://github.com/harbor-framework/harbor/tree/main/adapters/programbench) exists. Internet blocked. | Limit 1,000 steps and 6 h. Avg per task with mini-SWE-agent: Opus 4.7 $3.81, Opus 4.6 $11.38, Sonnet 4.6 $27.09, Haiku 4.5 $0.80 (Table 2). | MIT per GitHub API. Last push 2026-09-29, 946 stars. |
| [NL2Repo-Bench](https://arxiv.org/abs/2512.12730) ([repo](https://github.com/multimodal-art-projection/NL2RepoBench)) | 104 tasks, empty workspace to installable Python library. Spec avg 18.8K tokens. Easy at most 1,500 lines (26), medium 1,500 to 4,000 (46), hard at least 4,000 (32). Paper: about 180 turns add about 90K tokens of history. | Original repo's pytest suite in Docker; average test pass rate. No LLM judge. | Paper ran CC (Sonnet 4.5: 40.2% avg, 3 of 104 fully passed). Released harness runs OpenHands only, local only. CC needs own driver. | Cost and time per task: UNKNOWN. | No license file found (GitHub API empty). Last push 2026-05-13, 181 stars. |
| [Commit0](https://arxiv.org/abs/2412.01769) ([repo](https://github.com/commit-0/commit0)) | Paper: 54 libraries; README says 57. Spec PDFs 10K to 300K tokens; up to 1,300 functions. Lite split: 16 libraries. Large specs exceed one window. | Visible unit tests, run interactively by the agent; final score is the pass rate in a clean clone. | Built-in agent is aider only. Test backend default Modal; local Docker added (CI commit 2026-02-18). CC/Codex need a driver. | 2024 numbers on Lite (16 libs), Claude 3.5 Sonnet: $1.55, $12.47, $99.39 for stages 1, 2, 3. Current models: UNKNOWN. | MIT. Last push 2026-02-24, 194 stars. Low activity. |
| [FeatureBench](https://arxiv.org/abs/2602.10975) ([repo](https://github.com/LiberCoders/FeatureBench)) | 200 tasks, 24 Python repos. Gold patch avg 790 lines, 15.7 files, 62.7 fail-to-pass test points. Splits: lite 30, fast 100 (no GPU). Exceeds one window: UNKNOWN. | F2P plus P2P tests in Docker; Passed % (partial) and Resolved %. No LLM judge. Test visibility to agent: UNKNOWN. | Yes, built in: `fb infer --agent` supports claude_code, codex, openhands, gemini_cli, mini_swe_agent. | Lite, CC plus Opus 4.5: 9.0M input and 35K output tokens per task. Gold eval avg 57.2 s per fast instance. Dollar cost: UNKNOWN. | MIT. Last push 2026-09-15, 95 stars. Dataset V1.1 on 2026-08-24. |
| [SWE-EVO](https://arxiv.org/abs/2512.18470) ([repo](https://github.com/SWE-EVO/SWE-EVO)) | 48 release-sized tasks, 7 Python projects. Avg 21 files, 610 lines edited (max 4,113), 874 tests. Exceeds one window: UNKNOWN. | F2P and P2P tests; Resolved Rate plus soft Fix Rate. LLM judge only for failure analysis. | Harness scores patches from OpenHands or SWE-agent trajectories. CC/Codex need own driver to produce patches. | UNKNOWN. | MIT. Last push 2026-05-03, 59 stars. |
| [ICAE-Bench](https://arxiv.org/abs/2607.21217) ([repo](https://github.com/ALEX-nlp/ICAE-EVAL)) | 480 tasks, 12 languages. Fuzzy PRD avg 276 tokens. Golden code avg 35,533 lines (full) vs 979 lines and 17 files (Lite, 50 tasks). | Four parts: black-box tests (native and enhanced), structural similarity, LLM critic (design quality), interaction quality (constraint coverage, fallback rate). | Yes: Claude Code is the default runner; OpenHands optional. Docker per language. | "Many model calls, long time" (README). Numbers: UNKNOWN. | README badge says Apache-2.0, but no LICENSE file in the repo root. Last push 2026-08-04, 7 stars. |
| [Hyper-tau-bench](https://arxiv.org/abs/2609.04611) ([repo](https://github.com/sierra-research/hyper-tau-bench)) | 53 tasks. Developer agent builds a customer-service agent from business records, a client REST API, an inherited codebase, with a serving-cost budget. Builds run 48 to 360 min. | The built agent is deployed against held-out simulated users (tau-bench inner loop), minus a budget penalty. Users and NL-assertion judges are LLMs (GPT-5.5 class). | Yes: `--developer-harness codex` or `claude-code` (also opencode, prime-agent). Docker. A new harness is one driver class. | Per task: CC plus Opus 5 216 min, $42.0 build cost at list price; Codex plus GPT-5.6-sol 47.9 min, $18.2. About $3,000 for one config over 53 tasks. | MIT. Last push 2026-09-07, 36 stars. New (paper 2026-09-04). |

## Table 2: fit to P1..P5 and user simulator

"yes" = the benchmark can measure it with little change. "partial" = gives a signal, needs extra work. "no" = not measurable.

| Candidate | P1 scale | P2 decomposition | P3 resume | P4 efficiency | P5 intent persistence | User simulator |
|---|---|---|---|---|---|---|
| RoadmapBench | yes (3,700-line median) | yes: per-target scores, free order, so plan quality shows in outcome | partial: you can interrupt a run yourself | partial: tokens and turns logged, cost not | no: spec is fully given, no business constraint | none; instruction.md is the whole spec |
| ProgramBench | yes (largest tasks) | partial: paper notes models write monolithic single files | no | partial: $ per task reported | no | none |
| NL2Repo-Bench | yes for the 32 hard tasks | partial | no | partial | no | none |
| Commit0 | yes (specs 10K to 300K tokens) | partial | no | partial | no | none |
| FeatureBench | partial: mid-size, may fit one window | partial | no | yes for mid-size cost curve; token I/O logged | no | none |
| SWE-EVO | partial | partial | no | no | no | none |
| ICAE-Bench | Lite no; full set partial | no | no | partial | partial: hidden constraints are revealed by the Oracle, tests check them at the end | yes: HTTP "Oracle" router over benchmark-authored records; 16-query budget; model default DeepSeek-V3.2 |
| Hyper-tau-bench | partial: hours-long builds | partial | no | partial: build cost and serve-cost budget reported | partial: client holds requirements that the records omit | yes: client simulator (GPT-5.5, low reasoning) via `talk_to_client` |

## Table 3: harnesses and infrastructure (not task sets)

| Candidate | What it is | Reuse value | License; maintenance |
|---|---|---|---|
| [Harbor](https://github.com/harbor-framework/harbor) | Runner for agent evals in Docker or cloud. Task format used by Terminal-Bench, RoadmapBench, SWE-bench Pro V2. Adapters for [swebenchpro, programbench, featurebench, featbench, cooperbench, swelancer, tau3-bench, deveval, locomo and more](https://github.com/harbor-framework/harbor/tree/main/adapters). | High. Installed agents include claude_code and codex. Both declare `skills=True`: Claude adapter copies `skills_dir` into `$CLAUDE_CONFIG_DIR/skills/` ([claude_code.py](https://github.com/harbor-framework/harbor/blob/main/src/harbor/agents/installed/claude_code.py)); Codex adapter copies to `$HOME/.agents/skills` ([codex.py](https://github.com/harbor-framework/harbor/blob/main/src/harbor/agents/installed/codex.py)). So the skill can be injected into any Harbor benchmark. Whether the skill's CLI, subagents and git worktrees work inside the container: UNKNOWN, not tested. | Apache-2.0. Last push 2026-10-07, 5,882 stars. |
| [superpowers-evals (Quorum)](https://github.com/prime-radiant-inc/superpowers-evals) | Behavioral eval lab. Drives real Claude Code and Codex CLIs. A "conversation" role plays the user; private acceptance criteria plus deterministic post-checks grade the run; treatment arm vs stock arm with the same model; campaign cost report ([README](https://github.com/prime-radiant-inc/superpowers-evals/blob/main/README.md), [authoring guide](https://github.com/prime-radiant-inc/superpowers-evals/blob/main/docs/scenario-authoring.md)). | High as a pattern and harness. Scenarios already named for our problems: [sdd-same-plan-resume](https://github.com/prime-radiant-inc/superpowers-evals/tree/main/scenarios/sdd-same-plan-resume) (P3, status draft), [sdd-survives-compaction](https://github.com/prime-radiant-inc/superpowers-evals/tree/main/scenarios/sdd-survives-compaction) (P1), [sdd-spec-constraint-preserved](https://github.com/prime-radiant-inc/superpowers-evals/tree/main/scenarios/sdd-spec-constraint-preserved) (P5), [cost-trivial-task-review-fanout](https://github.com/prime-radiant-inc/superpowers-evals/tree/main/scenarios/cost-trivial-task-review-fanout) (P4, over-spawning). Tasks are tiny (four utility functions; a one-line change). The largest are a Svelte todo app (15 to 40 min wall time per the scenario) and a Go fractals CLI; max-time caps go up to 120 min. Written for the Superpowers skill, not ours. | No LICENSE file found; GitHub API reports none. Lifecycle "experimental" ([ABOUT.md](https://github.com/prime-radiant-inc/superpowers-evals/blob/main/ABOUT.md)). Last push 2026-10-06, 128 stars. Depends on [Gauntlet](https://github.com/prime-radiant-inc/gauntlet) (Apache-2.0). Bun/TypeScript. |

## Table 4: smaller or off-target candidates (checked, not primary)

| Candidate | What and size | Why not primary | Links; license; maintenance |
|---|---|---|---|
| SWE-bench Pro | V2: 642 tasks, 11 repos, Harbor format; HARD-51 subset; offline agent phase; 50-minute budget; locked CC and Codex agents ship in `v2/tooling`. Paper: avg 107 lines in 4.1 files. | Tasks mostly fit one window (P1 no). Good negative control for P4: the skill must not over-spawn here. Dataset license UNKNOWN; public set uses GPL repos on purpose. | [paper](https://arxiv.org/abs/2509.16941), [repo](https://github.com/scaleapi/SWE-bench_Pro-os), [V2 README](https://github.com/scaleapi/SWE-bench_Pro-os/blob/main/v2/README.md). Repo MIT. Last push 2026-09-22, 538 stars. |
| SWE-Lancer | Diamond: 463 tasks (198 IC SWE, 265 Manager) in Harbor. IC tasks avg 2 files, 69 lines. Playwright E2E tests; Manager tasks graded against the real manager's pick. | Small tasks. 10 to 20 min and about 14 GB per task image build. No user simulator. | [paper](https://arxiv.org/abs/2502.12115), [code](https://github.com/openai/frontier-evals/tree/main/project/swelancer). Old repo archived. MIT. Last push 2026-04-21. |
| Terminal-Bench 2.x | 89 tasks (2.0); 2.1 fixed 28 tasks in May 2026; now a continuous benchmark. Most trials under 20 min; extremes 2 h and about 100M tokens. | Mostly short terminal tasks, not project-scale. Cost 1 to 100 USD per benchmark run (paper). | [paper](https://arxiv.org/abs/2601.11868), [repo](https://github.com/harbor-framework/terminal-bench), [2.1 note](https://www.tbench.ai/news/terminal-bench-2-1). Apache-2.0. Pushed 2026-10-07. |
| METR HCAST (public) and RE-Bench | HCAST public repo: 11 task directories (web server, SQL-injection CTF, symbolic regression, ...). RE-Bench: ML research-engineering tasks (count not checked). | Run through METR Task Standard plus Inspect, not CC or Codex CLI. Few repo-engineering tasks. Asks users to keep tasks out of training data. | [HCAST](https://github.com/METR/hcast-public) (MIT, pushed 2026-07-28), [RE-Bench](https://github.com/METR/RE-Bench) (MIT per README, pushed 2025-10-16). |
| LoCoBench-Agent (and LoCoBench) | 8,000 scenarios, 10K to 1M token contexts, up to 50 turns, own 8-tool harness. | Metrics are heuristic ("multi-session memory retention" = reference consistency plus topic coherence), not hidden tests. Own harness, not CC or Codex. Data on Google Drive. | [paper](https://arxiv.org/abs/2511.13998), [repo](https://github.com/SalesforceAIResearch/LoCoBench-Agent). Apache-2.0. Pushed 2026-06-02. |
| DevBench (now DevEval) | 22 repos, 4 languages; design (PRD, UML, architecture), setup, implementation, tests. Harbor adapter has 63 tasks. | GPT-4-era, ChatDev baseline. Repo last push 2024-05-30. Weak signal. | [paper](https://arxiv.org/abs/2403.08604), [repo](https://github.com/open-compass/DevEval). Apache-2.0. |
| ProjectEval | 20 project tasks, avg 402 lines canonical answer; simulated user interaction through a browser driver (Selenium-style) as the test. | Small. GPL-3.0 limits reuse. | [paper](https://arxiv.org/abs/2503.07010), [repo](https://github.com/RyanLoil/ProjectEval). GPL-3.0. Pushed 2026-07-03. |
| FeatBench (not FeatureBench) | 156 instances, 25 repos, natural-language feature requests only. | Size per task: UNKNOWN. Mentioned to avoid name mix-up. | [Harbor adapter](https://github.com/harbor-framework/harbor/tree/main/adapters/featbench), [repo](https://github.com/THU-Agent/FeatBench). MIT. |
| tau3-bench (tau2-bench) | Customer-service tool use with an LLM-simulated user; 375 tasks in the Harbor adapter; pass^k. | Not coding. Useful only as a user-simulator design reference. | [repo](https://github.com/sierra-research/tau2-bench), [adapter](https://github.com/harbor-framework/harbor/tree/main/adapters/tau3-bench). MIT. Pushed 2026-10-07. |

## Underspecified tasks with a simulated user (small tasks)

| Candidate | What | Simulator | Notes |
|---|---|---|---|
| [Ambig-SWE](https://arxiv.org/abs/2502.13069) ([repo](https://github.com/sani903/InteractiveSWEAgents)) | Underspecified variant of the 500 SWE-bench Verified issues (ICLR 2026). Three settings: Full, Hidden, Interaction. | GPT-4o proxy that holds the full issue and answers only from it; says "I don't have that information" otherwise. OpenHands agent. | Interaction lifts results up to 74% over Hidden. Models almost never ask without a prompt. Tasks are small. MIT, pushed 2026-09-21. |
| [Ask or Assume?](https://arxiv.org/abs/2603.26233) ([repo](https://github.com/nedwards99/ask-or-assume)) | Same SWE-bench Verified variant; multi-agent scaffold that splits detection from execution; 69.40% resolve rate. | GPT-5.1 simulated user with withheld context. | License NOASSERTION. |
| [ClarEval](https://arxiv.org/abs/2603.00187) ([repo](https://github.com/JialinLi13/ClarEval)) | 750 tasks (150 HumanEval, 600 LiveCodeBench) with injected ambiguity. | Scripted user simulator. | Function-level, not project-level. No license found. |
| [Dialogue-SWEBench](https://arxiv.org/abs/2606.13995) | SWE-bench Verified solved through dialogue only; persona-grounded user simulator. | LLM, persona per task. | Code release: UNKNOWN (no repo link in the paper). |

## Adjacent work: persistence, handoff, memory, orchestration

| Candidate | What | Use for us | Links; license |
|---|---|---|---|
| Handoff Debt | Interrupt a coding agent at deterministic points, freeze the repo, resume with a successor under 4 views (repo only, raw trace, summary notes, structured notes). 75 SWE-bench Verified tasks, 181 handoff points, 724 takeovers per model. Context-bearing handoffs cut median agent events 20 to 59% and prompt tokens 42 to 63% vs repo-only; solved-rate effect smaller. | The only measurement design for P3. Small tasks, OpenHands, open-weight models, same harness for predecessor and successor. Copy the protocol, not the data. | [paper](https://arxiv.org/abs/2606.02875), [repo](https://github.com/anjilab/agent-handoff-debt) (MIT, pushed 2026-08-30, 3 stars, EMNLP 2026). |
| Constraint Decay | 80 greenfield and 20 feature tasks over 8 web frameworks. Same API contract; constraints (architecture, database, ORM) added in levels. Deterministic static verifiers plus behavioral tests. Average drop 27.28 points from baseline to fully specified. | Pattern for a P5 verifier: a script that checks the constraint, separate from tests. Constraints are all in the prompt, so it does not test persistence over time. | [paper](https://arxiv.org/abs/2605.06445), [repo](https://github.com/francdente/constraint-decay) (no license found; pushed 2026-09-23). |
| PushBench (Quantitative Goal Persistence) | Does the agent keep going until a verifier confirms N valid work units. CC (Sonnet 4.6) and Codex CLI (gpt-5.4) solve many 50-artifact tasks but drop to 3 of 9 per condition at 100. | Persistence of a goal count, not of a business constraint. Code link is anonymous: availability UNKNOWN. | [paper](https://arxiv.org/abs/2605.23574). |
| LoCoEval | 128 samples, about 50 turns, 64K to 256K tokens; function-generation Pass@k plus topic awareness and information extraction. | Closest to "information loss in long context", but chat-level, not agentic. Code at an anonymous link: availability and license UNKNOWN. | [paper](https://arxiv.org/abs/2603.06358). |
| SWE-ContextBench and VibeMemBench | Cross-task experience reuse (1,100 base plus 376 related tasks; 111 targets with 3,634 history trajectories). | They test learning across tasks, not resuming one task. Not P3. | [SWE-ContextBench](https://arxiv.org/abs/2602.08316), [VibeMemBench](https://arxiv.org/abs/2609.23570) (code in [DAMO-ConvAI](https://github.com/AlibabaResearch/DAMO-ConvAI), MIT). |
| CooperBench | Two agents implement two features in one repo and must merge. Agents get on average 30% lower success when cooperating than when doing both tasks alone. | Warning for P2: parallel jobs can cost quality. Test merge-conflict rate on our job graphs. | [paper](https://arxiv.org/abs/2601.13295), [repo](https://github.com/cooperbench/CooperBench) (MIT badge, no license file detected via API), [Harbor adapter](https://github.com/harbor-framework/harbor/tree/main/adapters/cooperbench). |
| OrchBench | Scores an orchestration plan on a DAG with a deterministic simulator, without running workers. Correlates with CC execution quality at r = 0.816 using 1.3% of tokens. | Closest thing to grading a planner (P2). Code release: UNKNOWN (no link found). | [paper](https://arxiv.org/abs/2607.25656). |
| ClawArena-Team | 41 scenarios where a main model manages a fixed pool of subagents; execution-based, no LLM judge. API cost spans over 100x while score spans under 4x. | Evidence that cost and management quality are decoupled (P4). Not coding tasks; own harness. | [paper](https://arxiv.org/abs/2606.31174), [repo](https://github.com/aiming-lab/ClawArena) (MIT). |
| CliffCompaction | Compaction technique; API proxy for CC, Codex and others; never compacts a compaction. | A stronger plain baseline: "plain session plus better compaction". Optional. | [paper](https://arxiv.org/abs/2609.26779), [repo](https://github.com/nguyenvuthientrang/cliffcompaction) (MIT). |
| ContextEcho | Persona drift in long agentic-coding sessions; compaction does not reliably reset it (3,746 to 9,716 turns of CC sessions). | Evidence that long sessions drift. Not intent persistence. Release: UNKNOWN. | [paper](https://arxiv.org/abs/2605.24279). |

## UNKNOWN items

- Whether any RoadmapBench, FeatureBench or SWE-EVO task exceeds one context window. The papers do not say. Only NL2Repo gives token accounting (18.8K spec plus about 90K history per run).
- Dollar cost per task for RoadmapBench, NL2Repo, SWE-EVO, ICAE-Bench and FeatureBench (FeatureBench gives tokens only; cache share not stated). Commit0 cost with 2026 models.
- Whether Harbor's totals include subagent tokens. Its Claude adapter reads `subagents/*.jsonl` transcripts, but the cost roll-up was not checked.
- Whether the skill (its CLI, subagents, worktrees) runs inside Harbor, Quorum or Hyper-tau containers. Not tested.
- FeatureBench: whether fail-to-pass tests are hidden from the agent.
- Licenses: NL2Repo-Bench, superpowers-evals, Constraint Decay, ClarEval (no license file found); ICAE-Bench (badge only); SWE-bench Pro dataset.
- Code release of OrchBench, Dialogue-SWEBench, LoCoEval, PushBench, ContextEcho.
- Commit0: 54 libraries (paper) vs 57 (README); which is current.
- Terminal-Bench 4.x content (the README leaderboard link says 4-0-0; not read further).

## Recommendations

Best 4 for this skill, in order:

1. **RoadmapBench** for P1 and P2. Real version upgrades, median 3,700 changed lines, per-target hidden tests with weights, free ordering, MIT, Harbor format. Use the weighted Completion Score as the main metric, not Resolved Rate (best published Resolved Rate is 39.1%). Caveat: the spec is complete, so no grill; dollar cost is UNKNOWN, so run a 2-task pilot first.
2. **ICAE-Bench Lite** for P5 and for the grill phase. It already runs Claude Code, has a hidden-spec Oracle (benchmark-authored records, 16-query budget), black-box tests and a "constraint coverage" metric. Caveat: Lite tasks average 979 lines, so they likely fit one window; it tests recovering and applying a constraint, not carrying it over hours; license is a README badge only. Hyper-tau-bench is the richer but costlier alternative ($18 to $42 and 48 to 216 min per task).
3. **superpowers-evals (Quorum)** as the harness pattern for P3, P4 and P5 scenarios. Same-model arms, user-like conversation role, private criteria, deterministic checks, cost report, Claude and Codex. Caveat: no license file (ask the owners before copying code), experimental, tiny tasks, tuned to Superpowers. If unclear, re-implement the three-file scenario pattern (story, setup, checks).
4. **FeatureBench (lite 30 or fast 100)** as the mid-size control and for P4 cost proportionality. Claude Code and Codex adapters are built in; MIT; gold patches avg 790 lines. Use Passed % as the continuous metric (Resolved is 11 to 20% for the best published configs). Pair it with SWE-bench Pro V2 (small tasks, locked CC and Codex agents) as the negative control: the skill must not over-spawn there.

Optional stretch for P1: ProgramBench (largest tasks, 3% almost-resolved at best, so use % tests passed; cost up to $27 per task with mini-SWE-agent).

Patterns to borrow, not benchmarks to run: Handoff Debt (P3 protocol), Constraint Decay (P5 verifier), Ambig-SWE (user proxy that answers only from withheld text), CooperBench (merge conflicts from parallel jobs), CliffCompaction (stronger plain baseline).

## What no existing benchmark covers well (custom fixture needed)

- **P3 resumability on large tasks, across models or harnesses.** Handoff Debt covers only small SWE-bench tasks, one harness (OpenHands) and open-weight models. Quorum has one draft scenario (sdd-same-plan-resume) on a tiny plan. Nothing resumes a multi-hour project from files with a different model or harness.
- **P5 persistence of a constraint stated once.** ICAE tests recovering a constraint and applying it. Constraint Decay tests constraints given in the prompt. Quorum has one small scenario. None states one business constraint at the start, runs a long job with compaction, then checks it at the end with a deterministic verifier.
- **P4 cost proportional to task size, with model mix.** Benchmarks report cost or tokens. None scores over-spawning, cheaper-model share, or review catch rate. Quorum has only a one-line-change fan-out check.
- **P2 plan quality as such.** Outcome scores exist (RoadmapBench per target). Plan scoring on real repos does not (OrchBench is simulated on DAGs; code UNKNOWN).
- **P1 compaction attribution.** Benchmarks give task size, none counts compaction events or ties failures to them. This needs instrumentation of the plain arm.

## Consequences for shape-and-execute evals

General:

- Run arms as same model, same harness: plain session vs session with the skill. Harbor can inject the skill (`skills_dir`) for Claude Code and Codex. Sum subagent tokens yourself; Harbor's roll-up is UNKNOWN.
- Benchmarks with full specs have no human. The skill needs a non-interactive entry (spec from file, auto-approve) or a user-simulator hook, otherwise it cannot run headless. ICAE and Hyper-tau expose the simulator as an HTTP Oracle or a `talk_to_client` call; the grill step would have to call it.
- Use continuous metrics (Completion Score, % tests passed, Fix Rate). Binary Resolved Rates are near the floor for large tasks.
- One trial is noisy. For RoadmapBench, 12 tasks x 2 arms x 3 trials is 72 runs; at the 2 h cap that is at most 144 h of wall-clock (derived), parallelizable.
- Block network access to the upstream repos, as RoadmapBench and ProgramBench do. RoadmapBench tasks come from public releases.

Per problem:

- **P1 scale:** RoadmapBench (main), ProgramBench (stretch). Metric: Completion Score at equal model. Log compaction events in the plain arm (count of compact boundaries in the CC transcript) and report results split by "plain arm compacted at least k times". A task that fits one window is a negative control (SWE-bench Pro).
- **P2 decomposition:** RoadmapBench per-target scores. Compare the skill's planner vs the same model splitting and implementing at once. Extra metrics to add: target coverage in the plan, merge conflicts between parallel jobs (CooperBench motivates this), critical-path length, jobs per target.
- **P3 resumability:** custom, built on Handoff Debt's protocol. Take a RoadmapBench or FeatureBench task. Stop at a deterministic checkpoint (after N jobs done). Clear context. Resume with a fresh agent, then repeat with another model or harness (Claude Code to Codex). Compare final score and extra events and tokens against an uninterrupted run. Quorum's sdd-same-plan-resume is the scenario format to copy.
- **P4 efficiency:** record tokens, dollars, subagent count and model mix per run. Plot cost against gold-patch size over SWE-bench Pro (small), FeatureBench (mid) and RoadmapBench (large). Add Quorum-style fan-out scenarios on trivial tasks. Anchors for order of magnitude: CC Opus 4.5 on FeatureBench Lite 9.0M input and 35K output tokens per task; Hyper-tau CC builds $42 per task.
- **P5 intent persistence:** custom. Add one business constraint to the note or grill answers (for example "money is integer cents" or "no new dependencies"). Pick or build a task where a late job would naturally break it. Check with a Constraint-Decay-style static verifier plus a behavioral test. Variants: constraint stated in the note, revealed only through the simulated user (ICAE Oracle pattern), and stated once then followed by a forced context clear.

## Sources

Papers (arXiv):
- RoadmapBench https://arxiv.org/abs/2605.15846
- ProgramBench https://arxiv.org/abs/2605.03546
- NL2Repo-Bench https://arxiv.org/abs/2512.12730
- Commit0 https://arxiv.org/abs/2412.01769
- FeatureBench https://arxiv.org/abs/2602.10975
- SWE-EVO https://arxiv.org/abs/2512.18470
- ICAE-Bench https://arxiv.org/abs/2607.21217
- Hyper-tau-bench https://arxiv.org/abs/2609.04611
- SWE-bench Pro https://arxiv.org/abs/2509.16941
- SWE-Lancer https://arxiv.org/abs/2502.12115
- Terminal-Bench 2.0 https://arxiv.org/abs/2601.11868
- LoCoBench-Agent https://arxiv.org/abs/2511.13998
- DevBench https://arxiv.org/abs/2403.08604
- ProjectEval https://arxiv.org/abs/2503.07010
- Ambig-SWE https://arxiv.org/abs/2502.13069
- Ask or Assume https://arxiv.org/abs/2603.26233
- ClarEval https://arxiv.org/abs/2603.00187
- Dialogue-SWEBench https://arxiv.org/abs/2606.13995
- Handoff Debt https://arxiv.org/abs/2606.02875
- Constraint Decay https://arxiv.org/abs/2605.06445
- PushBench https://arxiv.org/abs/2605.23574
- LoCoEval https://arxiv.org/abs/2603.06358
- SWE-ContextBench https://arxiv.org/abs/2602.08316
- VibeMemBench https://arxiv.org/abs/2609.23570
- CooperBench https://arxiv.org/abs/2601.13295
- OrchBench https://arxiv.org/abs/2607.25656
- ClawArena-Team https://arxiv.org/abs/2606.31174
- CliffCompaction https://arxiv.org/abs/2609.26779
- ContextEcho https://arxiv.org/abs/2605.24279

Repos and docs (GitHub API metadata and READMEs read 2026-10-07):
- https://github.com/harbor-framework/harbor (and `src/harbor/agents/installed/claude_code.py`, `codex.py`, `adapters/`)
- https://github.com/prime-radiant-inc/superpowers-evals (README, ABOUT.md, docs/scenario-authoring.md, scenarios/)
- https://github.com/prime-radiant-inc/gauntlet
- https://github.com/UniPat-AI/RoadmapBench
- https://github.com/facebookresearch/ProgramBench
- https://github.com/multimodal-art-projection/NL2RepoBench
- https://github.com/commit-0/commit0
- https://github.com/LiberCoders/FeatureBench
- https://github.com/SWE-EVO/SWE-EVO
- https://github.com/ALEX-nlp/ICAE-EVAL
- https://github.com/sierra-research/hyper-tau-bench
- https://github.com/sierra-research/tau2-bench
- https://github.com/scaleapi/SWE-bench_Pro-os
- https://github.com/openai/frontier-evals
- https://github.com/harbor-framework/terminal-bench
- https://www.tbench.ai/news/terminal-bench-2-1
- https://github.com/METR/hcast-public
- https://github.com/METR/RE-Bench
- https://github.com/SalesforceAIResearch/LoCoBench-Agent
- https://github.com/open-compass/DevEval
- https://github.com/RyanLoil/ProjectEval
- https://github.com/THU-Agent/FeatBench
- https://github.com/sani903/InteractiveSWEAgents
- https://github.com/nedwards99/ask-or-assume
- https://github.com/JialinLi13/ClarEval
- https://github.com/anjilab/agent-handoff-debt
- https://github.com/francdente/constraint-decay
- https://github.com/cooperbench/CooperBench
- https://github.com/aiming-lab/ClawArena
- https://github.com/nguyenvuthientrang/cliffcompaction
- https://github.com/AlibabaResearch/DAMO-ConvAI
- https://huggingface.co/datasets/UnipatAI/RoadmapBench
