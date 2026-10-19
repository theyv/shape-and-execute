> **About this note.** A research subagent wrote it during the design session (2026-10-06).
> It evaluated a short summary of the design, before the draft existed, so "absent" below means
> "absent from that summary".
> What the design took from it: labelled router links, one sentence and one deliverable per job,
> pointers instead of pasted content, a role authority table, hard stops in every mode, `verify`
> re-run by `sae`, an explicit precedence rule, reminder lines in `sae next`.
> What it did not take, to avoid ceremony: per-role agent files with tool whitelists, a read-only
> planner whose output `sae` writes, a `conflicts:` field, sliced whole-system review by default.
> See [Follow PROSE without ceremony](../2026-10-06-follow-prose-without-ceremony.md).

# PROSE (Agentic SDLC Handbook, ch13) and an evaluation of the "shape-and-execute" skill design

Retrieved 2026-10-06. Purpose: give a skill-design agent the PROSE rules, how the author applies them to skills, and a scored evaluation of one design.

## 0. How to read this note

**Sources**

- `ch13` = Daniel Meppiel, "The PROSE Constraints", The Agentic SDLC Handbook, chapter 13 (slug `ch13-the-prose-specification`). https://danielmeppiel.github.io/agentic-sdlc-handbook/handbook/ch13-the-prose-specification.html . Licence CC BY-NC-ND 4.0, so the chapter is paraphrased here, with at most a few short terms.
- `G` = local Genesis skill v0.4.0, resolved commit `18e73c35e5cefaf431fbe4e080e8f125ebfece33`, at `apm_modules/danielmeppiel/genesis/`. Paths are relative to `skills/genesis/` unless they start with `site/` or `README`.
- `L` = a local note on APM usage (not kept).
- `D` = the design summary in the task brief. The real SKILL.md was not available, so "absent" means "absent from the summary".
- Secondary, checked once: https://danielmeppiel.github.io/awesome-ai-native/ . It defines nothing itself and points to the handbook as its in-depth reference for PROSE (paraphrase of the fetch result; page text not saved).

**Tags used on every claim**

- `[S x.y]` stated in ch13, section x.y. Anchor key below.
- `[G file:line]` stated in Genesis.
- `[L]` stated in a local file, `[D]` taken from the design summary.
- `[I]` my inference. Treat as a hypothesis, not source text.

**ch13 anchor key** (append to the ch13 URL). Intro = `#sec-prose` (unnumbered text above 13.1).
13.1 `#the-constraint-model` | 13.2 `#p-progressive-disclosure` | 13.2.1 `#implementation-patterns` | 13.2.2 `#anti-pattern-context-dumping` | 13.3 `#r-reduced-scope` | 13.3.1 `#implementation-patterns-1` | 13.3.2 `#anti-pattern-scope-creep` | 13.4 `#o-orchestrated-composition` | 13.4.1 `#implementation-patterns-2` | 13.4.2 `#anti-pattern-monolithic-prompt` | 13.5 `#s-safety-boundaries` | 13.5.1 `#standard-role-boundaries` | 13.5.2 `#implementation-patterns-3` | 13.5.3 `#anti-pattern-unbounded-agent` | 13.6 `#e-explicit-hierarchy` | 13.6.1 `#implementation-patterns-4` | 13.6.2 `#anti-pattern-flat-instructions` | 13.7 `#when-constraints-are-missing-three-failure-stories` | 13.8 `#applying-the-constraints-a-worked-example` (13.8.1 `#the-instruction-hierarchy`, 13.8.2 `#the-agent-configuration`, 13.8.3 `#the-task-decomposition`, 13.8.4 `#where-a-constraint-prevented-a-failure`) | 13.9 `#compliance-checklist` | footnote 2 `#footnotes`.

**ID convention.** ch13 checklist items are written `ch13/P1 ... ch13/E2`. Genesis also uses R1, R2, S4, S7, B4, B8, A5, A7, A9 and so on for its own patterns. They are unrelated. Never read a bare "R1" or "S1" without the prefix.

**Method and limits.** WebFetch declined to reproduce the chapter verbatim, so I downloaded the page HTML with curl, converted it to text and read all of it (the scratch copy was not kept). I did not read other handbook chapters: ch13 does not rely on them for a definition. It defers "engineering details" to ch15 and calls ch14, 15, 17 and 18 "the implementation" [S 13.6.2, 13.9].

## 1. Bottom line

1. PROSE = Progressive Disclosure, Reduced Scope, Orchestrated Composition, Safety Boundaries, Explicit Hierarchy [S 13.1; G SKILL.md:295-297 agrees].
2. It is a discipline, not a standard. The chapter says it is no standards body and no published spec [S intro], yet it ends by calling the five constraints the specification [S 13.9]. There is no MUST/SHOULD language. The normative core is five definitions plus an 11-question yes/no checklist [S 13.9].
3. ch13 says little that is skill-specific. It names skill frontmatter a "capability index" [S 13.2.1] and lists SKILL.md as one primitive type [S 13.4.1]. It says nothing about SKILL.md size, scripts, CLIs, worktrees or "subagents" by name. Those rules come from Genesis and agentskills.io, not from PROSE. Genesis itself says the handbook is not authoritative for the SKILL.md container surface [G site/src/content/docs/resources/external-corpus.md:49-92].
4. ch13's own priority rule: fix S1-S3 first, whatever the total score, then E1-E2, then P/R/O by the symptom you see [S 13.9].
5. Genesis grades PROSE as five one-line PASS rows [G SKILL.md:291-298; examples/04-pr-review-advisory.md:300-304] and never uses the 11 questions. Its examples read "Explicit Hierarchy" as a delegation chain, not as instruction-scope inheritance [G examples/04-pr-review-advisory.md:304]. A Genesis-style PASS is not ch13 compliance.
6. Verdict on the design: structurally strong on P, R and O and on deterministic truth anchoring (A1-A4 below), but the checklist-level status of P1, P2, R1, R2 and O2 is partial or unknown from the summary. Exposed on S (the axis ch13 ranks first) and on E semantics. See section 8.

## 2. What PROSE is

### 2.1 Table of constraints [S 13.1]

| Constraint | Addresses | Induces |
|---|---|---|
| Progressive Disclosure | Context overload | Efficient context utilization |
| Reduced Scope | Scope creep | Manageable complexity |
| Orchestrated Composition | Monolithic collapse | Flexibility, reusability |
| Safety Boundaries | Unbounded autonomy | Reliability, verifiability |
| Explicit Hierarchy | Flat guidance | Modularity, domain adaptation |

Each constraint answers a model property: finite context, stateless reasoning, probabilistic output. They are separate as definitions but depend on each other in practice [S 13.1].

### 2.2 Interdependence and the three failure stories [S 13.7]

Figure 13.1 edges: P-E "controls attention"; R-S "constrains safety scope"; O-R "single source of truth"; P-R "loads what fits scope"; E-S "hierarchy defines boundaries"; O-P "composable units enable disclosure".

The chapter marks the stories as fictional composites. Each shows one constraint present and its partner missing:

1. E without P. Every instruction file was self-contained, so a 15-line token-validation fix loaded nearly 3,000 words. The agent also made an unrequested rate-limiting change and introduced a race condition.
2. R without O. Disciplined single-task sessions, but standards were pasted into prompt templates. After an error-format change, four stale copies produced two formats for two weeks.
3. S without R. Strict tool whitelists and gates, but one huge OAuth2 session. A security rule loaded at session start sat under about 40,000 tokens of context, and the agent later violated it.

Takeaway in the chapter: each constraint's partner catches the failures the first one misses.

## 3. The five constraints, precisely

### P - Progressive Disclosure [S 13.2]

- **Definition.** Reveal complexity progressively. Context arrives "just-in-time" rather than "just-in-case" [S 13.2].
- **Why.** The issue is attention, not capacity: the signal-to-noise ratio sets the quality [S 13.2].
- **Patterns** [S 13.2.1]:
  1. Markdown links as lazy-loading pointers. A link declares that deeper context exists, with a path.
  2. Descriptive labels. The link text states what the target contains so relevance can be judged without following it. Bad: a bare link labelled "docs". Good: link text that names the content and when it applies.
  3. Skill frontmatter as a capability index. The description says what the skill does and when to activate; the full body loads only when the task matches.
- **Anti-pattern: context dumping** [S 13.2.2]. One file inlines standards, API reference, auth guide, error taxonomy (the example totals 6,100 words). Fix: a file of labelled pointers, with the same information at a fraction of the context cost.
- **Checklist:** ch13/P1, ch13/P2.

### R - Reduced Scope [S 13.3]

- **Definition.** Fit the task size to the context capacity. Each sub-task runs with a fresh context and a narrow scope [S 13.3].
- **Sizing heuristic.** The best task is one the agent finishes without a follow-up question. If the agent must ask, the task is too large or the context is missing; both are scope problems. Adding context mid-session shows the scope was wrong from the start [S 13.3].
- **Three split examples** [S 13.3]: JWT auth into five sessions with one deliverable each; fixing the login bug and updating the session tests into two sessions with the fix committed first; payment-service refactor split by call site with only the old-to-new mapping and the target module in context.
- **Patterns** [S 13.3.1]: phase decomposition (diagnose, implement, validate; each phase gets a clean window and only its inputs); session splitting across domains (frontend, backend, database).
- **Anti-pattern: scope creep** [S 13.3.2]. Requests pile up mid-session and the newest task gets the worst output. Fix: each request becomes its own session.
- **Checklist:** ch13/R1, ch13/R2.

### O - Orchestrated Composition [S 13.4]

- **Definition.** Prefer small primitives that chain to monolithic frameworks [S 13.4].
- **Why.** In a mega-prompt, a small change in one section changes behavior in all the others. Each composed primitive is small enough to understand, test and debug on its own [S 13.4].
- **Patterns** [S 13.4.1]:
  1. Primitive types as atomic units: instruction files, skills, agents, prompts, specifications; one purpose each. The example tree has scoped instruction files, a planning mode that "cannot execute", an implementation mode with scoped tools, a workflow prompt and a SKILL.md "Auto-activated by relevance".
  2. Workflows as compositions. A prompt sequences existing files, does not repeat the coding standards, and ends in a STOP for human review.
- **Anti-pattern: monolithic prompt** [S 13.4.2]. You cannot tell which instruction failed or which rules conflict. Fix: one concern per primitive file, each testable, debuggable and versioned on its own.
- **Checklist:** ch13/O1, ch13/O2.

### S - Safety Boundaries [S 13.5]

- **Definition.** Every agent operates within explicit boundaries: tools (capability), loaded context (knowledge), and what requires human approval (authority) [S 13.5].
- **Why.** Output is probabilistic; with unbounded authority, variance in output becomes variance in effects. Boundaries "constrain its blast radius" [S 13.5].
- **Role table** [S 13.5.1], condensed:

| Role | Tools | Knowledge | STOP before |
|---|---|---|---|
| Code writer | edit, run commands, search, read, test runner | files in its domain; cannot see infra, CI/CD, deploy scripts | public API signature changes, DB schema changes, auth logic |
| Reviewer | read, search, read-only lint/test/type-check | full repo read; no write tools | none; output is commentary only |
| Test runner | run commands, read, test runner | test files and source under test; no deploy config, secrets, CI | deleting fixtures, changing shared test infra, skipping tests |
| Deployer | deploy scripts only, read | manifests, env config, release notes; no source write | every deployment action; a human approves each environment promotion |

- **Planning agent special case** [S 13.5.1]. Read and search only, with no write tools; it produces a plan, not code. A separate session implements.
- **Patterns** [S 13.5.2]:
  1. Per-agent tool whitelists in the agent's frontmatter.
  2. Validation gates: present the change with rationale, "STOP", wait for explicit approval. The chapter notes the gate lives in the instruction, not in an external enforcement mechanism, so ch13's own gates are prose-level.
  3. Knowledge scoping: instructions load only for matching files; `applyTo` doubles as a knowledge boundary.
  4. Deterministic tools as truth anchors: an agent claiming a test passes must actually run it and report the deterministic result.
- **Anti-pattern: unbounded agent** [S 13.5.3]. `tools: ["*"]`, no approvals; blast radius is the whole repository. Fix: copy the closest role row and tighten it; the minimum tool set is always smaller than one expects.
- **Checklist:** ch13/S1, S2, S3.
- **Internal inconsistency in ch13.** The role table says a code writer cannot see infra or CI config [S 13.5.1]. The worked example lets the backend agent read any file and restricts only writes [S 13.8.2]. Only a write-path boundary is checklist-mandatory (ch13/S3).

### E - Explicit Hierarchy [S 13.6]

- **Definition.** Instructions form a hierarchy from global to local; local context inherits global context and may override it. Agents resolve context from the most specific scope to the most general [S 13.6].
- **Why.** Global rules give consistency (naming, commits, docs); local rules give specialisation [S 13.6].
- **Patterns** [S 13.6.1]:
  1. Directory-scoped context files (AGENTS.md at root, `frontend/`, `backend/auth/` and so on). An agent editing a file walks up and loads each level.
  2. Pattern-scoped instruction files (`applyTo` globs); more specific patterns override or extend less specific ones.
  3. Compilation for portability. Author in tool-specific formats and compile to hierarchical AGENTS.md. The authored instructions stay the source of truth. Package managers such as APM automate this.
- **Anti-pattern: flat instructions** [S 13.6.2]. One root file with every domain's rules; all agents load all of it and unrelated rules interfere. Fix: split by scope.
- **Checklist:** ch13/E1, ch13/E2.

## 4. Compliance checklist [S 13.9]

All eleven questions are yes/no. Paraphrased.

| ID | Question |
|---|---|
| P1 | Does each instruction file over 100 lines link out to side topics instead of inlining them? |
| P2 | Does each cross-reference say what its target holds, not only its file name? |
| R1 | Is each agent task one sentence with one deliverable? |
| R2 | Does each phase of a multi-step workflow start with a fresh context? |
| O1 | Does each instruction file cover one concern, so its name can be that topic? |
| O2 | Do workflow prompts link shared instruction files instead of pasting them? |
| S1 | Does each agent configuration list its tools, with no wildcard? |
| S2 | Is there a STOP gate before each change to auth, database schemas or production config? |
| S3 | Does each agent have a list of the directories it may change? |
| E1 | Do instructions exist at three or more levels, such as root, domain and module? |
| E2 | Can module rules be added without editing a file above that module? |

Prioritisation [S 13.9]: S1-S3 first (highest blast radius, fastest to close, "one YAML change per agent"); then E1-E2 (hierarchy is the fastest architectural change); then P/R/O by symptom: scope creep, fix R1/R2; context dilution, fix P1/P2; debugging nightmares, fix O1/O2.

P1 is the only numeric threshold in ch13. It is stated for "instruction files"; applying it to SKILL.md and reference files is an inference [I].

## 5. Worked example (JWT in Express) [S 13.8]

- Hierarchy [S 13.8.1]: root AGENTS.md (global rules plus labelled links), `backend/AGENTS.md` ("Inherits: root"), `auth.instructions.md` scoped by `applyTo: "src/auth/**"` with a Validation Gate section. An agent editing billing code never sees the auth file.
- Agent config [S 13.8.2]: tool whitelist; a Boundaries section with MAY and MUST NOT lists naming exact directories (`src/auth/`, `tests/auth/`), read-anywhere, no CI/CD or env edits, no new dependencies without presenting a rationale; workflow ends in STOP.
- Decomposition [S 13.8.3]: five sessions, each with fresh context and one deliverable file. Session 5 (frontend) uses a different agent and receives only the API contract, not backend internals.
- Boundary in action [S 13.8.4]: the backend agent tried to edit `src/api/client.ts`; the path whitelist blocked it; the agent reported the suggestion in its summary and the frontend session handled it with the right context.
- Patterns worth copying into skill design [I, from the above]: (1) every agent definition carries an explicit Boundaries block; (2) sessions hand off through artifacts and contracts, not shared memory; (3) an out-of-scope idea is reported, never acted on.

## 6. How PROSE applies to skills

ch13's examples use a `.github/` layout with `instructions`, `chatmodes`, `prompts`, `applyTo` globs and tool names such as editFiles and runCommands [S 13.4.1, 13.5.1]. These look like GitHub Copilot conventions (ch13 never says so; per the fetch result, the awesome-ai-native page describes itself as being about agentic primitives for GitHub Copilot) [I]. The constraints are harness-neutral; the mechanisms need mapping to Claude Code and Codex [I]. For those two harnesses the common scope mechanism appears to be directory-scoped AGENTS.md or CLAUDE.md [I]. Support: ch13 recommends compiling to AGENTS.md "for universal portability" [S 13.6.1]; the Genesis adapters say Claude Code has no glob predicate and Codex scopes by directory [G assets/runtime-affordances/per-harness/claude-code.md:47; assets/runtime-affordances/per-harness/codex.md:35], but both adapters are dated 2025-11-14, so verify.

**SKILL.md frontmatter `description`**
- [S 13.2.1] It is the capability index: what the skill does and when to activate; the body loads only when the task matches.
- [G] Genesis treats it as the dispatcher's "function signature": imperative, user-intent first, indirect triggers named, at most 1024 characters, and a name that matches the folder [G SKILL.md:107-120, 304-306; agents/genesis-architect.agent.md:245-250]. Those limits are attributed to agentskills.io and were not re-verified.
- [I] A skill with several entry points (shape, plan, execute) should say when each applies and when the skill should not activate at all.

**SKILL.md body**
- [S] ch13 gives no size limit for SKILL.md. Applicable rules: ch13/P1 (link out when over 100 lines), ch13/O1 (one concern), ch13/O2 (reference shared files, do not paste), and "workflows as compositions" with a STOP gate where a human decides [S 13.4.1, 13.9].
- [G] Body at most 500 lines and 5,000 tokens, overflow to `references/` with an explicit load trigger [G SKILL.md:307-311, 461-462; assets/primitives.md:85-88]. Calibrate prescriptiveness per section and include an inline template for structured output [G SKILL.md:447-454].
- [I] A thin router that only routes and links out is the shape P1, O1 and O2 point to.

**`references/`**
- [S 13.2.1] Links are lazy pointers; labels must say what the target contains (ch13/P2).
- [G] Every body link must state the condition that loads it [G SKILL.md:443-444]. C1 LAZY ASSET names the failure EAGER BLOAT [G assets/design-patterns.md:53-67]. S5 LAZY PROXY warns against "pointers to pointers to pointers" and says to materialise in a single hop [G assets/design-patterns.md:274-295].
- [I] Loading references per phase is coarser than loading when the current task needs them; split by branch.

**Templates and assets**
- [S] Silent apart from "file templates" for primitives [S 13.9 Try It].
- [G] Assets hold templates and data the skill emits or composes against [G SKILL.md:445-446].

**Scripts and CLIs**
- [S] Not discussed. Closest: deterministic tools as truth anchors [S 13.5.2] and the deployer limited to "deploy scripts only" [S 13.5.1].
- [G] Scripts must be non-interactive, version-pinned on one-off commands, document `--help`, put structured data on stdout and diagnostics on stderr, and be listed in the SKILL.md body [G SKILL.md:436-442]. S7 DETERMINISTIC TOOL BRIDGE: any fact that must be true or side effect that must happen crosses a tool; route 2 is a custom CLI with a documented contract [G assets/design-patterns.md:325-458].
- [I] A single-writer state CLI is what S and O ask for. The PROSE checks that still apply are on its callers: which agents may call it, and whether agent claims are verified rather than trusted.

**Subagents and agent definitions**
- [S] Explicit tools list (ch13/S1), file-path boundary (ch13/S3), STOP gates (ch13/S2), role table, planning-agent special case, fresh context per sub-task, different agent per domain [S 13.3, 13.5, 13.8].
- [G] A child thread has its own fresh window and is stateless across spawns; hand off by explicit artifacts [G assets/primitives.md:149-170]. A persona (file) and a thread (runtime unit) are orthogonal [G agents/genesis-architect.agent.md:200-208]. A7 requires reviewers to start cold and never receive the producer's reasoning trace [G assets/architectural-patterns.md:311-378]. A spawn brief carries only what that spawn needs; rationale stays in a separate human section [G SKILL.md:335-338; references/audience-boundary.md:46-124].

**Context loading and instruction hierarchy**
- [S 13.2, 13.6, 13.8.1] Directory-scoped or pattern-scoped files load only for matching work; labelled links defer detail.
- [L] APM compiles `.apm/skills/<name>/` and `.apm/agents/<name>.agent.md` to `.claude/`, `.agents/skills/` and `.codex/agents/`; harness directories are generated output and are never edited by hand [L]. This is the "compilation for portability" idea in practice [S 13.6.1].
- [L] The repo's `apm.yml` currently lists `targets: - claude` only; Codex output needs `codex` added [I].

**Orchestration, plans and state**
- [S 13.3.1, 13.4.1] Phases with clean context and artifact inputs; workflows that compose existing files.
- [G] B4 PLAN MEMENTO (plan outside the context, reloaded at each re-grounding boundary) [G assets/design-patterns.md:526-558]. B8 ATTENTION ANCHOR (re-inject goal and hard constraints at step starts, before and after spawns; IMPLICIT-ANCHOR is the named failure) [G assets/design-patterns.md:623-691]. A5 WAVE EXECUTION (gate between waves; WAVE-WITHOUT-GATE) [G assets/architectural-patterns.md:221-263]. A9 SUPERVISED EXECUTION (plan, deterministic execute, verify; VERIFY-WITH-LLM-ONLY is an anti-pattern) [G assets/architectural-patterns.md:439-558]. B10 HUMAN CHECKPOINT [G assets/design-patterns.md:728-762].

## 7. Genesis: the author's own application

### 7.1 Where PROSE sits

- Step 5 of the 8-step process is "classic + PROSE + LLM-physics compliance check" [G SKILL.md:74, 291-298]. The chapter confirms the wording verbatim [S footnote 2]. Any BLOCKER sends the design back to step 2.
- Step 8 lint lists "PROSE 5-axis" beside size budget and ASCII [G SKILL.md:89-91].
- Primitive-to-axis map [G assets/primitives.md:230-239]: MODULE ENTRYPOINT with lazy assets = Progressive Disclosure; CHILD-THREAD SPAWN = Reduced Scope; module composition (inline, sibling, external) = Orchestrated Composition; TRIGGER ORCHESTRATOR with validation gates = Safety Boundaries; cascading SCOPE-ATTACHED RULE FILEs = Explicit Hierarchy. Also C1 LAZY ASSET is tied to Progressive Disclosure and C2 PERSONA PRELOAD to Reduced Scope [G assets/pattern-tradeoffs.md:101-103].

### 7.2 How the examples grade it

Examples 03, 04 and 05 give one PASS or OK line per axis [G examples/03-release-notes-single-skill.md:271-275; examples/04-pr-review-advisory.md:300-304; examples/05-pr-review-verdict.md:258-262]. Differences from ch13 [I, from reading those lines against ch13]:

- E is graded as topology ("Trigger -> orchestrator skill -> spawned lens threads -> arbiter -> tool") or as "SKILL.md body links to references/ and scripts/ with explicit load triggers". ch13's E is global-to-local instruction inheritance with override. Only primitives.md matches ch13.
- R is graded as "each lens has its own fresh context window". The sizing heuristic and the one-deliverable test are not graded.
- S is graded by tool deny-lists, single-writer interlocks and S7 bridges. ch13's capability/knowledge/authority triple and ch13/S1-S3 are not enumerated.
- The handbook's 11-question checklist does not appear anywhere in Genesis (searched for "compliance checklist", "ch13", "chapter 13").

### 7.3 Genesis rules adjacent to PROSE (not in ch13)

- Size budget and load triggers on every body link; script conventions [G SKILL.md:307-311, 436-444].
- Plan reload and attention anchors (B4, B8) [G assets/design-patterns.md:526-558, 623-691].
- S7: every fact and side effect crosses a deterministic tool [G assets/design-patterns.md:325-458].
- A7 cold readers [G assets/architectural-patterns.md:311-378].
- A9 weak versus strong supervision (prose-enforced versus runtime-enforced; "when the trigger surface offers strong-form A9, USE IT") [G assets/architectural-patterns.md:450-475]. ch13's own gates read as the weak form [S 13.5.2; I].
- Role classes rather than model SKUs [G agents/genesis-architect.agent.md:485-488].
- Evals: two to three content evals with and without the skill, about 20 trigger evals split 60/40 [G SKILL.md:339-349, 479-485].

### 7.4 Caveats about Genesis

- Truth count is inconsistent: "seven durable LLM truths" [G SKILL.md:297], "Eight durable truths" [G agents/genesis-architect.agent.md:98], "the five durable truths" [G agents/genesis-architect.agent.md:329].
- Genesis pattern IDs collide with ch13 checklist IDs (see ID convention).
- Per-harness adapters are dated "Verified on: 2025-11-14" [G assets/runtime-affordances/per-harness/claude-code.md:125; assets/runtime-affordances/per-harness/codex.md:107]. The Codex adapter says Codex has "No first-class child-thread primitive" [G assets/runtime-affordances/per-harness/codex.md:43]. A local APM note now lists `.codex/agents/*.toml` as an agent location [L], so that adapter claim is probably stale [I].
- Chapter numbers drift. awesome-ai-native links PROSE as `ch12-the-prose-specification`; Genesis docs cite ch11, ch12, ch14 [G site/src/content/docs/resources/external-corpus.md:74-76]. ch13 is the current PROSE chapter. The chapter footnote pins Genesis commit `613f2a64...`; the local copy is `18e73c35...` and the step-5 wording matches.

## 8. Evaluation of the "shape-and-execute" design

Order follows ch13's own priority rule: S first, then E, then R, O, P [S 13.9].

### 8.0 Scorecard against the 11 questions

| ID | Status | Reason |
|---|---|---|
| ch13/P1 | Unknown | A router with per-phase references [D] suggests links, but phase references over 100 lines are unverified. |
| ch13/P2 | Unknown | Link labels are not described. Phase-keyed loading ("references load per phase") implies a trigger, not a descriptive label. |
| ch13/R1 | Partial | `jobs/<ID>.md` per unit of work gives structure. The one-sentence, single-deliverable test is not stated or linted. |
| ch13/R2 | Partial | Planner, decision, integration and review agents are fresh [D]. The main thread across shape, plan, execute and the long orchestrator loop are not stated to reset. |
| ch13/O1 | Met (likely) | Router, per-phase references and separate protocols. Watch `brief.md` and the job protocol as catch-alls. |
| ch13/O2 | Partial | SKILL.md to references by link fits. CLI-generated dispatch prompts and the repo profile may carry pasted copies. |
| ch13/S1 | Not addressed | No role definitions with tool lists. `codex exec` and `claude -p` reviewers inherit whatever their CLI grants. |
| ch13/S2 | Unknown, at risk | The ladder includes `full-auto`. Nothing says auth, schema and prod-config classes are non-delegable. |
| ch13/S3 | Partial | Worktrees isolate parallel writers. There is no per-job write-path allowlist. |
| ch13/E1 | Met (likely) | Repo instruction files, skill and protocol, `brief.md`, `jobs/<ID>.md` is four levels, if workers inherit repo-level files. |
| ch13/E2 | Partial | A job file adds local rules without editing upstream files. Override precedence is not stated. |

### 8.1 (a) Alignments

- **A1. Progressive loading by construction.** One router, references per phase, `research/` "cold, loaded on demand", "files appear only when they carry content", and a worker bundle of four named inputs [D]. Matches lazy-pointer disclosure and avoids context dumping at skill level [S 13.2.1, 13.2.2]. Genesis C1 LAZY ASSET [G assets/design-patterns.md:53-67].
- **A2. Right-sized units with fresh context.** `jobs/<ID>.md` with its result beside it; planner, decision-analysis, integration and adversarial-review run in fresh subagents; shape, plan, execute with files as handoff [D]. Matches phase decomposition and fresh sub-task context [S 13.3, 13.3.1] and planning separate from implementation [S 13.5.1]. Artifact handoff is what makes fresh contexts workable [I].
- **A3. One source of truth for shared worker context.** `brief.md` shared by all workers; `plan.md` holds rationale apart from worker prompts [D]. Matches the O-R "single source of truth" edge and failure story 2 [S 13.7]. It mirrors Genesis's rule that human rationale never goes into a spawn brief [G SKILL.md:335-338] [I on the mapping].
- **A4. Deterministic truth anchor.** `sae` is the only writer of `state.json` and `events.jsonl`, lints DAG and requirement coverage, and generates dispatch prompts [D]. Matches "deterministic tools as truth anchors" [S 13.5.2] and a small chainable primitive [S 13.4]. Genesis S7 route 2 [G assets/design-patterns.md:325-458].
- **A5. Explicit authority, and publishing removed.** A decision-class table per interaction mode, "never push", worktrees for parallel writers [D]. Matches the authority dimension [S 13.5]. The deployer role needs a STOP before every deployment action [S 13.5.1]; removing the capability is stronger than gating it [I]. Merging at dependency boundaries resembles Genesis's A5 gate between waves [G assets/architectural-patterns.md:221-263] [I].
- **A6. Reviewers are fresh, separate agents.** Adversarial review at three points, optionally cross-model [D]. Reviewer is commentary-only [S 13.5.1], fresh context [S 13.3], one concern per primitive [S 13.4]. Genesis A7 asks the same and bans handing the producer's reasoning to cold readers [G assets/architectural-patterns.md:311-378].
- **A7. A real hierarchy exists.** Repo-level instructions, skill, `brief.md` (task scope), `jobs/<ID>.md` (unit scope) [D, I]. Matches global-to-local with inheritance [S 13.6] and ch13/E1 [S 13.9].
- **A8. Shaping supplies missing context.** The shape phase (intent, optional research, grilled spec) exists so workers need no follow-up question. That is the missing-context half of the sizing heuristic [S 13.3] [I].

### 8.2 (b) Tensions or violations, each with a fix

**B1. Roles with no bounded agent definitions (ch13/S1, ch13/S3).**
- Design: protocols for workers and fresh subagents, per-phase model levels, and `codex exec` or `claude -p` for cross-model review. No tool lists or write paths [D].
- Rule: every agent config has an explicit tools list with no wildcards and an explicit list of directories it may modify [S 13.9, 13.5.3, 13.8.2].
- Why it matters: a headless `codex exec` or `claude -p` reviewer is a full agent with whatever tools and sandbox its CLI grants. Worktrees stop concurrent clobbering, not scope violations [I]. A local APM note says not to treat Codex `sandbox_mode` as a guardrail (no reason given there) [L], so a deterministic check is safer than relying on agent settings [I].
- Fix:
  1. Write a Role/Tools/Knowledge/Authority table [S 13.5.1] for researcher, planner, worker, integrator and reviewer, in-session and headless.
  2. Author each role once as `.apm/agents/<role>.agent.md` and let APM emit Claude and Codex files [L; S 13.6.1].
  3. Add `may_modify:` (and optionally `may_read:`) to the job template. Have `sae` audit `git diff --name-only` in the worktree against it before integration, and have `sae lint` require parallel jobs' `may_modify` sets to be disjoint or ordered by a dependency edge [I].
  4. For headless reviewers set read-only permissions explicitly (verify current flags per CLI; not checked here) and pass only artifacts, never the producer's reasoning [G A7 anti-pattern WARM-CONTEXT COLD READER, assets/architectural-patterns.md:373].

**B2. Tunable approval gates versus unconditional ones (ch13/S2).**
- Design: five interaction modes from `full-auto` to `interactive`, and "stakes -> rigor" [D].
- Rule: a STOP before every operation that modifies auth, database schemas or production config [S 13.9]. The writer role also stops before public API signature changes [S 13.5.1]. Critical decisions (architecture, security-sensitive changes, data migrations) require stop-and-present [S 13.5.2].
- Why it matters: if the decision-class table lets those classes be `auto`, the design fails exactly in the modes where nobody is watching [I].
- Fix: add a non-delegable hard-stop class that no mode can lower: auth and security logic, schema and migrations, prod, CI, deploy and env config, public API signatures, dependency installs, destructive deletes outside job paths, push or publish. In unattended modes mark the job `blocked: needs approval`, continue independent jobs, and list pending approvals at the end. `sae` refuses the transition without an approval event in `events.jsonl`. Classify risk by path globs in `sae`, not LLM judgement; Genesis makes the same call for risk classification [G examples/03-release-notes-single-skill.md:157-160] [I].

**B3. Agent-asserted results (ch13/S truth anchors).**
- Design: each worker "returns a result file with frontmatter"; the orchestrator updates state through `sae` [D].
- Rule: the agent must really run the test and report its deterministic result [S 13.5.2].
- Why it matters: if `sae` records `status: done` from agent-written frontmatter, single-writer protects file integrity, not the truth of the claim [I]. Genesis names this VERIFY-WITH-LLM-ONLY [G assets/architectural-patterns.md:530].
- Fix: the job template declares acceptance commands; `sae verify <job>` runs them in the worktree and records exit codes and a diff summary in `events.jsonl`. Frontmatter is a claim, not a fact.

**B4. Planner and reviewers that write files (planning-agent special case).**
- Design: planner subagent produces `brief.md`, `plan.md`, `jobs/<ID>.md`; reviews land in `reviews/` [D].
- Rule: a planning agent has read and search only, "no write tools at all", and a reviewer has no write tools [S 13.5.1].
- Fix: planner, researchers and reviewers return structured output; `sae plan apply` (lint first), `sae review add` and `sae research add` write the files. If agents must write, scope each to its single output path (ch13/S3). Severity medium-low, since the literal text concerns a plan "not code" [I].

**B5. Precedence, overrides and duplicated instructions (ch13/E1, E2).**
- Design: a "repo profile" goes to every worker; the mode ladder is defined by a table [D]. No stated precedence among job file, brief, protocol and repo rules.
- Rule: local context inherits global context and may override it [S 13.6]. Add module rules without editing upstream files (ch13/E2) [S 13.9]. Flat instructions let unrelated rules interfere [S 13.6.2], and pasted duplicates drift [S 13.7, story 2].
- Why it matters: both harnesses already load repo-level AGENTS.md or CLAUDE.md by directory [G assets/runtime-affordances/per-harness/claude-code.md:40-50; assets/runtime-affordances/per-harness/codex.md:30-41, dated]. A generated profile can duplicate or contradict them [I].
- Fix: one precedence line in the job protocol and brief template: more specific wins, except hard-stop classes (B2) which no layer may lower. Add `conflicts:` to result frontmatter instead of silent resolution. Make the repo profile facts-only (commands, layout) plus labelled links to instruction files. Let a task or repo override mode and decision classes through `intent.md` or `brief.md` frontmatter so no skill file is edited. Compile roles once for both harnesses via APM, adding `codex` to `targets` [L; I].

**B6. Long orchestrator and main-thread carry-over (ch13/R2, S-R pair).**
- Design: shaping includes "grilled with the user"; an "orchestrator loop" then runs; "never push" and mode rules are session-level [D].
- Rule: each phase starts with fresh context and no accumulated session state (ch13/R2) [S 13.9]. Failure story 3: a safety rule loaded at session start sits under about 40,000 tokens and is violated [S 13.7].
- Fix: make disk the only handoff. After shape and after plan, instruct a fresh session that starts with `sae status` (for unattended modes the loop could instead run headless through `claude -p` or `codex exec`). Have `sae next` print the active mode, hard-stop classes and ready jobs on every iteration (re-injection, Genesis B8 [G assets/design-patterns.md:623-691]). Checkpoint and restart at wave boundaries [G assets/architectural-patterns.md:221-263] [I].

**B7. No path for missing information, mid-run requests, or a too-big review (ch13/R).**
- Design: jobs and results exist; nothing says what a worker does when it lacks information; the whole-system review is a single review point [D].
- Rule: a good task completes without a follow-up question; adding context mid-session means the scope was wrong; each new request becomes its own session [S 13.3, 13.3.2]. Big tasks are split, for example by call site [S 13.3].
- Fix: the job protocol forbids mid-job context additions. A worker lacking information returns `status: blocked` with the question; the orchestrator amends the job or brief through `sae` and re-dispatches fresh, or escalates per decision class. A mid-run user request becomes an amendment to `intent.md` or `specs.md`, re-runs the requirement-coverage lint, and creates new jobs. Slice the whole-system review by requirement or area with fresh reviewers, then synthesise (Genesis B1 [G assets/design-patterns.md:460-490]) [I].

**B8. Paste risk (ch13/O2).**
- Design: the CLI "generates worker dispatch prompts"; one `brief.md` serves all workers; a planner writes every job file [D].
- Rule: prompts reference shared files "by link rather than pasting" [S 13.9]; failure story 2 [S 13.7].
- Nuance: prompts generated from canonical files at dispatch time are the same idea as compilation, where the authored source stays the truth [S 13.6.1]. Generated prompts are defensible if never edited or stored as a second source [I]. The real risk is planners restating shared constraints in every job file [I].
- Fix: dispatch prompt = labelled pointers plus the job file inline. The job template says "cite brief sections by heading, do not restate". `sae lint` flags paragraphs duplicated across job files and the brief.

**B9. Loading granularity (ch13/P1, P2).**
- Design: `brief.md` and the repo profile go to every worker; "References load per phase" [D].
- Rule: context loads only when the current task needs it [S 13.2]; links carry descriptive labels [S 13.2.1].
- Fix: cap `brief.md` to invariants plus an index. Give each job a `context:` list of brief headings or paths with descriptive labels. Split phase references by branch (research, spec, decision-analysis, integration, review) so an unused branch never loads. Put a descriptive label and load condition on every SKILL.md link. Add a mechanical P1/P2 check (every markdown file over 100 lines has links; no bare-filename link text); the checklist is yes/no, so it is lintable [I].

**B10. One skill spans shape, plan, execute, review, git and viewer (ch13/O1).**
- Rule: small chainable primitives; one concern per file [S 13.4, 13.9].
- Mitigations in the design: thin router, per-phase references, artifact contracts between phases [D].
- Fix: keep each phase enterable alone (shape only; execute from a hand-edited plan; review only) and say so in the description, which is the capability index [S 13.2.1]. Genesis would flag the "and" as a possible R1 SPLIT trigger but warns against PREMATURE SPLIT [G assets/refactor-patterns.md:16-76]. Low severity [I].

### 8.3 (c) PROSE requirements the design does not mention

"Ignored" means absent from the summary; confirm against the real SKILL.md.

- **C1. ch13/S1:** explicit per-agent tools list, no wildcards, and any agent definition files at all.
- **C2. ch13/S3:** explicit write-path boundary per agent.
- **C3. ch13/S2:** unconditional STOP classes (auth, schema, prod config).
- **C4. The role table** (Role, Tools, Knowledge, Authority) [S 13.5.1] as an artifact.
- **C5. ch13/R1 and the sizing heuristic:** one sentence and one deliverable per task; the no-follow-up-question test; the scope-creep rule [S 13.3, 13.3.2].
- **C6. ch13/R2:** fresh context at phase boundaries for the main thread.
- **C7. ch13/E:** inheritance and override semantics; extension without editing upstream files (ch13/E2); author once and compile for both harnesses [S 13.6.1].
- **C8. ch13/P1 and P2:** the 100-line rule and descriptive link labels.
- **C9. Independent testability, debuggability and versioning of each primitive** [S 13.4.2] (rationale text, not a checklist item). No per-protocol tests or versions in [D]. Genesis adds with-and-without-skill evals [G SKILL.md:339-349, 479-485].
- **C10. Report, do not act** on out-of-scope findings [S 13.8.4] (worked example, not a checklist item) [I mapping]; for example a `suggestions:` field in result frontmatter.

### 8.4 Outside PROSE: Genesis-only checks, low priority

- SKILL.md body at most 500 lines and 5,000 tokens with load triggers on every link [G SKILL.md:307-311, 443-444]; via agentskills.io, not re-verified.
- `sae` as a script: non-interactive, `--help`, JSON on stdout, diagnostics on stderr [G SKILL.md:436-442]. Stdlib-only helps pinning; the other points are unknown.
- Router, phase reference, protocol, template is three or more hops. Genesis calls this PROXY SPRAWL [G assets/design-patterns.md:293-294]. CLI-generated dispatch prompts can hand workers direct paths.
- Per-phase "model levels": Genesis wants role classes, not model names [G agents/genesis-architect.agent.md:485-488], and notes that mid-session model switches break caching [G agents/genesis-architect.agent.md:477-480].
- Plan reload at re-grounding boundaries [G SKILL.md:392-397] is the same point as B6.

### 8.5 Suggested change set, in priority order

1. Role table plus per-role agent definitions with explicit tools, authored once under `.apm/agents/` (B1, C1, C4).
2. `may_modify` in the job template, with `sae` disjointness lint and a diff audit before integration (B1, C2).
3. A non-delegable hard-stop decision class enforced by `sae` through approval events (B2, C3).
4. `sae verify` on declared acceptance commands (B3).
5. Planner and reviewers return output; `sae` writes the files (B4).
6. Precedence line, `conflicts:` field, task-level overrides, facts-only repo profile (B5, C7).
7. Fresh-session rule at phase boundaries; `sae status` and `sae next` re-injection (B6, C6).
8. Job lint for single deliverable, one-line goal, `context:` list and blocked path; change-request path; sliced whole-system review (B7, B9, C5).
9. P1/P2 lint and labelled links; split phase references by branch (B9, C8).
10. Phase-independent entry points; per-protocol evals and versions (B10, C9).

## 9. Open questions and limits

- Only the design summary was available. Every "not addressed" is relative to that summary.
- Not read, by the brief's scope rule: ch14 (load lifecycle), ch15 (attention and context economy, which holds sizing of each layer), ch17 (multi-agent orchestration), ch18 (execution meta-process). ch13 calls these the implementation of PROSE [S 13.9]. If the evaluation needs numeric budgets or orchestration rules for a DAG of workers, read ch15, ch17 and ch18 next [I; not verified to contain them].
- Harness mechanics were not verified against current docs: Claude Code subagent tool restrictions, `claude -p` permission flags, Codex `codex exec` sandbox and approval flags, `.codex/agents/*.toml` fields. Genesis adapters are from 2025-11-14.
- agentskills.io limits (500 lines, 5,000 tokens, 1,024-character description) are quoted via Genesis only.
- ch13 is a living page (copyright 2025-2026). Text above is as of 2026-10-06.
