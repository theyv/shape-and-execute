---
status: done
summary: Plain `sae status` prints the Project Stakes question while not set; the question now says the owner may skip.
validation: passed
changes:
  - skills/shape-and-execute/scripts/sae_lib/progress.py
  - skills/shape-and-execute/scripts/sae_lib/stakes.py
  - skills/shape-and-execute/references/modes/setup.md
  - tests/test_stakes.py
---

## Validation
`python3 tests/run.py test_stakes` OK (32 tests). Full suite also run (see commit).
New tests: `test_status_without_a_task_prints_the_question_only_while_stakes_are_not_set`,
`test_the_question_says_the_owner_may_skip`.

## Decisions taken
- [agent] Plain status JSON gains a `stakes` key (source, profile), like the task status.
- setup.md step 7 now says "plain `sae status`"; shape.md pointer stays true (task status prints it too).
- Owner addition (coordinator message): added the skip line to `stakes.ask_text`, before "Write the answer to ...". No other question text changed.
