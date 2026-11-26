---
id: FIX-LOOP-GUIDANCE
covers: [APPROACH-CHECK, PARK-STORY, FIX-WORKER]
verify:
  - test -f tests/test_fix_loop_guidance.py
  - python3 tests/run.py test_fix_loop_guidance test_reviews test_review_rounds_setting test_dispatch_pointers test_integration_fixes
  - python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish
scope:
  - skills/shape-and-execute/scripts/sae_lib/park_story.py
  - skills/shape-and-execute/scripts/sae_lib/prompts.py
  - skills/shape-and-execute/scripts/sae_lib/progress.py
  - skills/shape-and-execute/scripts/sae_lib/reviews.py
  - tests/test_fix_loop_guidance.py
  - tests/saetest.py
---

# FIX-LOOP-GUIDANCE: Approach check near the limit, the Approach proposal pointer, the park story

## Objective
Put the approach paragraph into late fix prompts, point the next review at an Approach proposal,
and print a plain story when a job or the task parks at the round limit.

## Inputs
- `specs.md` [APPROACH-CHECK], [PARK-STORY], [FIX-WORKER], [DECISION-APPROACH-CHECK-N-1].
- The approach paragraph and pointer constants in `prompts.py` (from `PROMPT-TEXT`);
  `templates/review.md` and `templates/job-result.md` as `PROMPT-TEXT` wrote them.
- `brief.md` "How": the drop and accept commands the story's options name.
- `jobs/FIX-LOOP-EXITS.result.md`: the `dropped` status and the accept command as built.
- `prompts.py` `build_prompt`, `earlier_round`; `graph.py` `review_rounds`, `fix_target`,
  `integration_parked`; `reviews.py` `apply_review`, `apply_integration_review`;
  `progress.py` status and next.
- `research/PROMPT-LEAN-AUDIT.md` proposals 2 and 3, the block "Paste into FIX-LOOP-GUIDANCE
  Inputs" (owner accepted): the round-limit park text opens every park message and story, and
  `sae collect` reports an `## Approach proposal`. execute.md, as `PROMPT-LEAN` left it, relies
  on both.

## Scope
- A fix job that answers changes-required round k of its target (a job or the integration),
  with k ≥ N − 1 and N = `max-review-rounds` at dispatch, gets the approach paragraph in its
  dispatch prompt, filled in. With N = 3: not after round 1, yes after round 2; with N = 1:
  every fix. Once a fix of a target got the paragraph, or the target parked at its limit,
  every later fix of that target gets it, whatever the limit is raised to.
- The next review round's prompt points to the "Approach proposal" of a fix result of the
  previous round when that section has content.
- The park story for a job parked at the round limit and for the task parked on the
  integration: built only from job files, result summaries, review finding titles and
  suggested fixes, and the fix jobs' "do not" limits with their reasons; then the options
  (change the approach, with `sae job drop`; reduce the requirement; another round). The
  orchestrator adds its recommendation; the story says so.
- `sae next` and `sae status` print the story; the park message of `sae collect` points to it.
  A function returns it for the server (`VIEWER-SURFACES`).

## Boundaries
- Do not reword the constants; a wording problem goes into your result.
- Gate logic: `FIX-LOOP-EXITS`. The viewer: `VIEWER-SURFACES`. Prompt text files: `PROMPT-TEXT`, `PROMPT-LEAN`.
- No transcripts and no harness logs in the story.
- Read-only commands stay lock-free and write nothing.

## Expected output
Code, `tests/test_fix_loop_guidance.py`. In the result, name the story function and its data
shape, for `VIEWER-SURFACES`.

## Validation
- [ ] The fix right after the owner raises the limit on a parked round (3 → 5) gets the
      paragraph.
- [ ] Tests for N = 3 and N = 1, for a job and for the integration, for the pointer with and
      without an Approach proposal, and for the story of a job parked at the limit.
- [ ] Reading the story of a test fixture, a reader who did not follow the task can tell what
      happened in each round and what the options are.
- [ ] Audit proposals 2–3: tests assert the round-limit opening line ("Add no fix job and accept
      nothing before the user answers") for a parked job and a parked task, and the `sae collect`
      Approach proposal line with and without the section.
