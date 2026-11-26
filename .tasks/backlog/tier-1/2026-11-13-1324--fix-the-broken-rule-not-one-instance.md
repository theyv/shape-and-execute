# Intent: Fix the broken rule, not one instance per review round

**Status: rough idea. Not shaped [human].**

## Problem

In a recent hard task the integration review needed four rounds. Rounds two to four all found
defects in the same area. Each round fixed one code path, and the next round found another path
that still broke the same rule.

[human] The owner observed the pattern: a review finds an edge case that comes from one specific
thing. The orchestrator writes a very specific job for the implementer. The implementer fixes it
in one specific way. The next round finds the next edge case from the same code, and this can go
on in circles. The owner asked whether each finding should be checked for a pattern, and whether
the same failure occurs in other places.

### What happened, in general terms [agent]

The spec held a **cross-cutting rule**: one rule that many code paths must respect. In the
example the rule was "a blocked item blocks only itself, not the whole session". Five paths
consumed it: starting a session, completing a step, a prerequisite check, a UI screen and a
stock update at the end. No single function owned the rule. Each path checked blocking in its own way, and
originally every path blocked the whole session.

The loop:

1. **The reviewer** finds one path that breaks the rule. It reproduces the failure and proposes
   a local correction.
2. **The orchestrator** turns the finding into a job: "fix finding N, add a regression test that
   reproduces it". The job file also said "fix only the named findings". This boundary actively
   kept the worker from looking at sibling paths.
3. **The worker** fixes exactly that path. The reproduction passes and `verify` is green.
4. **The reviewer of the next round** checks the fix, looks next to it, and finds the next path
   that still uses the old rule.

These were not new edge cases. They were a **finite list of consumers of one rule**, found one
per round because nobody listed them first. General names: fixing symptoms instead of the
cause ("whack-a-mole"); more precisely, an incomplete migration of a concept. The first fix
changed the meaning of "blocked" in one place, and the other consumers kept the old meaning.

The fourth round fixed it at the root: one shared function decides which items in a session are
blocked, every consumer calls it, and the worker searched the code for other consumers. That
round passed review.

### Refinements to the owner's diagnosis [agent]

- **Not every finding is a pattern.** In the first round, six of nine findings closed with one
  fix each. The signal for a pattern is a **second hit in the same area**: a finding that says
  it affects a finding of the previous round. That is the point to change approach.
- **The problem starts in planning, not in the fixes.** The planner split screens and logic into
  parallel jobs but gave the cross-cutting rule no single owner. Each job implemented its own
  version of the rule.
- **A second pattern: the orchestrator prescribes the solution.** In the same task the
  orchestrator wrote a wrong solution into a fix job file (how old data without a new flag should
  be read). The worker followed it, and the next review round found the defect. A job file should
  state what must become true, not how to make it true, unless the evidence already settles it.

### A second case: the approach cannot converge [agent]

A later task looped for seven review rounds with a different cause. The approach itself had no
finite end, so a consumer list would not have stopped it.

- **The rule:** code had to infer a structured value (a quantity and its unit) from free-form
  text written by people or agents. Every round, the reviewer wrote a new sentence that the
  inference read wrongly. The worker extended the inference. In one round a stronger worker
  reviewed all earlier rounds and rebuilt the rule as a whole. The next review still found a new
  sentence.
- **The signal differs from the first case.** In the first case the findings were new *code
  paths* of one rule, a finite list. Here the findings were new *inputs* to one function, an
  open set. Each fix grew the function: one module went from about 40 to about 320 lines, and
  the whole fix branch reached about 1,150 added lines for a one-line spec requirement.
- **The job file inflated the scope.** A checkpoint had proposed the smallest fix: a one-time
  data update that stores the value in a structured field. The orchestrator's job file ruled
  that out ("fixing only the examples does not meet the scope") and required the value to be
  inferred at run time. The spec did not ask for that. This is the second pattern above,
  "the orchestrator prescribes the solution", in a stronger form: it forbade the simple one.
- **The owner was never offered a change of approach.** Each park asked "authorize another
  round, or leave the task parked?". After the owner understood what the code did, they called
  the approach pointless at once. The cheap exit was a question nobody asked.

What would have caught it:

1. **Convergence check before another round.** Do the findings of the last two rounds name the
   same function with new inputs, and does the fix grow that function each time? Then the
   approach is suspect, not the fix. The next step is a short decision: can a structured field,
   a data update or an explicit choice replace the inference?
2. **The reviewer says when a defect class is open-ended.** Next to the reproduction: "this
   input space has no finite list, more rounds will find more cases". Free-form text
   interpretation in code is the typical example.
3. **A park question includes "change the approach" or "reduce the requirement"** as an option,
   with the smallest alternative in one sentence, next to "another round" and "stay parked".
4. **A fix job may not exclude a smaller fix that a checkpoint or review proposed** unless the
   spec requires the larger behavior. Scope that goes beyond the spec is a decision for the
   owner, not a job-file line.

### Why a stronger model did not break the loop [agent]

In round six the owner asked for a stronger model and a fix "that looks at the whole thing". The
orchestrator dispatched it, but the job file kept the old frame:

- **The objective named the solution:** "fix the entire quantity interpretation rule … choose a
  coherent quantity attachment rule". "Whole" became "the whole parser", not "the whole problem".
- **The boundaries closed the exits:** no new fields, no live data. Those were the two ways out:
  store the unit, or convert the data once.
- **The inherited scope stayed:** it was a `--fix-of` job on the same branch, under the parent
  job file that ruled out the data fix.
- **The root-cause step was scoped inside the frame:** "explain why the qualifier inventory still
  missed …". The worker did that well, and its root cause was correct about the parser. Nothing
  asked whether the parser should exist.
- **The worker had no expected way out.** It could have parked with "this approach cannot
  converge", but its job asked for a green result and a commit, and it delivered one: 4,350
  matrix checks, all suites green. The next review found a new sentence in three minutes.

So the model was not the limit. The job file decided the answer space, and a stronger worker
searched the same space more thoroughly.

More candidate changes from this case:

5. **The owner's own words go into the fix job.** When the owner asks for a different or a
   holistic approach, the job file quotes that request (smoothed) as the objective's source. The
   orchestrator does not translate it into a narrower technical objective.
6. **After a non-converging loop, the next job is new, not `--fix-of`.** It starts from the spec
   requirement and the evidence of the failed rounds, on a fresh branch, and its objective states
   the outcome ("snacks counted in pieces plan in whole pieces"), not the mechanism.
7. **The worker role has an explicit approach check.** Before a fix in round three or later, the
   worker answers in its result: "Can a simpler approach make this class of findings impossible?"
   If yes, and the job boundaries forbid it, the worker parks with a decision request instead of
   another patch.
8. **Boundaries in a late fix job are reviewed.** From round three, each "do not" line in a fix
   job must cite the spec or an owner decision. An unsourced boundary is removed.

## Goal

[human] Change the SaE instructions so that agents recognize such patterns and fix the rule,
instead of fixing one instance per review round.

### Success means

- A finding that breaks a cross-cutting rule leads to one fix job for the whole rule, with the
  list of consumers, in the first or second round, not the fourth.
- A second finding in the same area triggers a root-cause step before another fix.
- Fix jobs do not tell the worker to ignore sibling paths of the rule they fix.
- Fix job files state the required outcome and do not prescribe an unverified solution.
- When rounds keep growing one function with new inputs, the orchestrator stops and offers the
  owner a different approach, at the latest by the third round.

## Proposed outcome

Candidate instruction changes, cheapest and most effective first [agent proposal]:

1. **The reviewer names the rule, not only the instance.** For each finding: which rule of the
   spec is broken, which code paths consume that rule (found by search), and which of them the
   reviewer checked. The first round then returns the full list instead of one example.
   (`references/roles/reviewer.md`, `templates/review.md`.)
2. **The orchestrator groups findings by the broken rule, not by file.** The fix job's objective
   becomes "rule X holds everywhere". Its first scope step is "list every consumer of the rule".
   Such jobs have no "fix only the named findings" boundary. (`references/modes/execute.md`,
   "job review changes-required" and "integration review changes-required".)
3. **Second-hit rule.** When a finding concerns an area that the previous round already fixed,
   do not add another patch. First run a short root-cause step (a decision or research job): why
   did the previous fix miss this, and who else shares the rule? Then fix at the source.
4. **The worker looks for siblings of the defect.** Before it stops, it asks where else the same
   rule applies, and fixes those paths in scope or files findings. Prefer one table-driven test:
   every consumer times the failing scenario. (`references/roles/worker.md`.)
5. **The planner finds cross-cutting rules in the spec** and gives each one a single owner: one
   function with contract tests, built before the parallel jobs that consume it.
   (`references/roles/planner.md`.)

[agent] Items 1–3 would have caught the example in round one or two. Item 5 would have prevented
it, but it changes how plans are made, so it is the most expensive.

## Affected users and systems

- Reviewer, worker and planner role protocols; the execute mode reference; the review template.
- Tasks with several review rounds, mostly integration reviews of hard tasks.

## Constraints

- Keep findings concrete: a reproduction stays the evidence. The rule and the consumer list are
  added to it, not a replacement.
- Do not make every fix job a refactor. The broader scope applies only to findings that break a
  cross-cutting rule, or to a second hit in the same area.

## Open questions

- Where the second-hit check lives: in `sae` (it can see that a finding names a previous round's
  finding) or only in the orchestrator's instructions.
- Whether the reviewer's consumer list needs a fixed format so the orchestrator can group
  findings mechanically.
- How to keep the extra review work affordable on small tasks.
