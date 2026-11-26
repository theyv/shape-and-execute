---
id: PROMPT-TEXT
covers: [DIFF-GUIDANCE, EASY-UPGRADE, SETUP-PROPOSAL, TIERS-FOLLOW-DIFFICULTY, STAKES-TEMPLATE, STAKES-ASK, FINDING-SHAPE, STAKES-GRADING, TRIAGE, FIX-WORKER, RESULT-SECTIONS, PROMPT-JOB, SHARED-RULE-OWNER, LET-GO-REPORT, DECISION-ANYTIME, JOB-DROP, HARNESS-FALLBACK, APPROACH-CHECK]
verify:
  - python3 tests/run.py test_retired_terms test_findings test_sae_ask test_adr_rules test_resolves test_dispatch_pointers
  - grep -q "walking skeleton" skills/shape-and-execute/references/roles/planner.md
  - grep -q "Approach proposal" skills/shape-and-execute/templates/job-result.md
  - grep -q "Suggested fix" skills/shape-and-execute/templates/review.md
  - "! grep -q 'Correction:' skills/shape-and-execute/templates/review.md"
  - grep -q "## Stakes" skills/shape-and-execute/templates/repo/profile.md
  - grep -q "accept-review" skills/shape-and-execute/references/modes/execute.md
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/SKILL.md
  - skills/shape-and-execute/references/**
  - skills/shape-and-execute/templates/**
  - skills/shape-and-execute/scripts/sae_lib/prompts.py
  - tests/test_retired_terms.py
  - tests/test_findings.py
  - tests/test_sae_ask.py
  - tests/test_adr_rules.py
  - tests/test_resolves.py
resolves:
  - .tasks/findings/2026-11-20-1339--job-results-keep-empty-sections-such-as.md
---

# PROMPT-TEXT: Every prompt change of the task, in one diff the owner reads

## Objective
Apply the spec's prompt-text drafts to the skill, add the [PROMPT-SAE] texts as constants, and
report every contradiction the new text creates elsewhere.

## Inputs
- `specs.md` "Prompt text" (every subsection) and [PROMPT-JOB]; the requirements each draft
  names.
- `brief.md` "How": the command names fixed by the plan. Use them where a draft has a
  placeholder (`<accept command>`) or names a command.
- `intent.md` "Decisions of 2026-11-20" for the meaning behind the drafts.
- AGENTS.md (prompt text stays lean); the `agentic-systems-guidelines` skill, if available.

## Scope
- Apply each draft to its file. Keep the meaning of the four texts the owner approved as worded:
  the planner rule, the approach paragraph, the stakes template, the finding fields. Tighten the
  rest where it helps; add nothing the drafts do not ask for.
- `references/modes/setup.md` ([PROMPT-SETUP]): Claude tiers are renumbered (old L2 → L3, old
  L3 → L4, old L4 → L4, sonnet · high is the new L2). Codex tiers are redefined by the owner's
  table, not renumbered: execution and research cells are balanced L1–L4 by difficulty,
  economy one tier down (floor L1), premium one tier up (cap L4), each cell with its tier's
  model · effort; planning and review cells keep their model · effort and take the tier with
  the nearest pair. Add explicit steps for upgrading an existing configuration: add the `easy`
  column ([EASY-UPGRADE] cells), relabel the tiers as above, and keep every existing cell's
  model · effort.
- `templates/repo/profile.md`: the Stakes section and its example exactly as in
  [PROMPT-PROFILE]; the example is the one the viewer help will show.
- `shape.md`: the stakes answer goes to the profile path that `sae status` names (the main
  worktree's), not to the local checkout's copy.
- `execute.md`: the triage step, the fallback rule (outside `full-auto`: `sae job park`, then
  `sae ask`; the owner's yes runs the printed fallback command), the decision flow, the drop command (only
  on the owner's word), the accept command, the let-go logging form, and "Finish" step 3.
- `references/roles/decision-worker.md`: only if it assumes that every decision job answers a
  parked job's request; a decision job may now start from a question or a review round.
- [PROMPT-SAE]: the stakes line, the "not set" line, the Approach proposal pointer and the
  approach paragraph as named module-level constants in `prompts.py`, with placeholders for the
  values. Nothing calls them yet; `STAKES-IN-PROMPTS` and `FIX-LOOP-GUIDANCE` wire them.
- Read the rest of SKILL.md, `references/` and `templates/`, and `sae --help` with the help of
  each command the new text names. Fix contradictions inside prompt files. List the ones in CLI
  help or other code in your result.

## Boundaries
- No behaviour change in `sae` and no CLI help edits: the code jobs own them.
- Do not touch this repository's AGENTS.md or `.tasks/repo/profile.md`.
- The viewer's help text belongs to `VIEWER-SURFACES`.

## Expected output
- The changed prompt files and the unwired constants.
- `jobs/PROMPT-TEXT.result.md` with two extra sections, for the owner at the hold:
  - `## Changes for the owner`: one line per changed file: what changed and which requirement.
  - `## Contradictions`: each contradiction in CLI help or code (file, the text, what conflicts),
    or "None found".

## Validation
- [ ] Every changed line traces to a draft, a fixed interface, or a contradiction fix.
- [ ] The four approved texts keep their meaning; the profile example matches [PROMPT-PROFILE].
- [ ] `planner.md` and `shape.md` name four difficulties; nothing asks for a reason for one.
- [ ] Every cell of the setup proposal has a tier and a model · effort; Claude balanced
      `mechanical`, `normal` and `hard` keep their model · effort with tiers in cells on.
- [ ] Codex balanced execution with tiers on: `mechanical` L1 terra · medium, `easy` L2 sol ·
      medium, `normal` L3 sol · high, `hard` L4 sol · xhigh; `normal` and `hard` differ.
- [ ] The upgrade steps keep every existing cell's model · effort.
- [ ] The `review.md` fields and the `job-result.md` sections match [PROMPT-REVIEW] and
      [PROMPT-WORKER]; optional result sections say "Delete when it does not apply."
