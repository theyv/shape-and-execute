---
status: done
summary: execute.md checks the round-limit park before fixes or acceptance, uses fresh fix IDs and reads a reported Approach proposal; execute, shape and plan cover the fallback for a reopened done job
validation: pass
changes: made
resolved: []
---

# Result: PROMPT-TEXT-FIX-1

## Validation evidence
- `python3 tests/run.py test_retired_terms test_findings test_sae_ask test_adr_rules test_resolves test_dispatch_pointers`: 71 tests OK.
- `grep -q "accept-review" .../execute.md`: OK. Smoke `test_worktrees_review_verify_and_finish`: OK. `git diff --check`: clean.
- Commit 9633af6.
- Each finding was checked against the code first:
  1. A fix job unparks its target: `planning.py` `cmd_job_add` sets a parked target to `done` when `--fix-of` names it. execute.md Loop step 3 now checks for a round-limit park first. While parked, it adds no fix job and accepts nothing, relays the story and waits for the user.
  2. `progress.py` `cmd_dispatch` reopens done research and planning jobs with `--resume`. `sae job park` per WRITER-LAUNCH covers only pending and running jobs. execute.md Loop step 2, shape.md step 7 (follow-up questions) and plan.md section 1 now say what happens to a reopened job outside `full-auto`: it stays done and is not parked, the user's yes is logged with `sae log … decision "harness fallback: <ID>: <why>" --by human --job <ID>`, and the fallback command keeps `--resume`.
  3. execute.md line 5 adds an exception: when `sae collect` reports an Approach proposal, read that section. Loop step 3 adds the matching outcome bullet, which says it is a decision.
  4. The fix command uses `<FIX-ID>`, with a fresh ID for each fix job (`<ID>-FIX-1`, then `<ID>-FIX-2`, …).

## Decisions taken
- [agent] The owner's approval for a reopened job is recorded with the existing `sae log … --by human`. I added no new command, so the prompt text names no CLI that does not exist yet. This follows execute.md's decision flow (ask, then log with `--by human`).
- [agent] The reopened-job rule is written out in shape.md and plan.md too, not only in execute.md. Those phases resume done jobs, and the orchestrator may not have loaded execute.md there.

## Contradictions
These are for the code jobs. The coordinator routes them.
- WRITER-LAUNCH (job file "Scope", and spec [HARNESS-FALLBACK]): the missing-CLI fallback command is specified for a pending job, without `--resume`, and `sae job park` only for pending or running jobs. A done research or planning job reopened with `--resume` (`progress.py` around line 382) needs two things: a printed fallback command that keeps `--resume`, and a printed rule that does not tell the orchestrator to park it. The prompt text now expects both.
- `reviews.py` `apply_review` (around line 693), non-parked message: it always prints `sae job add … {target}-FIX-1`, and `planning.py` rejects a duplicate ID on a second round. The parked message already uses `-FIX-<n>`.
- Still open from the PROMPT-TEXT result: `sae collect` does not report an `## Approach proposal`. execute.md now relies on that notice for its read-the-result exception. No job's scope names it yet; FIX-LOOP-GUIDANCE is the closest (`reviews.py`, the proposal pointer).
