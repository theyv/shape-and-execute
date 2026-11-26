---
status: done
summary: Guide keeps a blank line before every heading, GUI note under "Routing tables (Tiers mode)", shaping asks Project Stakes bullet by bullet with the example
validation: pass
changes: made
resolved: []
---

# Result: INTEGRATION-FIX-5

## Validation evidence
- `python3 tests/run.py test_model_config test_retired_terms test_stakes`: 43 tests OK.
- Smoke (`test_worktrees_review_verify_and_finish`): OK.
- New tests: `test_model_config.SetupProposalTest.test_the_guide_keeps_a_blank_line_before_every_heading`,
  `test_the_gui_note_follows_the_routing_tables_heading`; `test_stakes.AskTests` (section path,
  "every agent reads it", five bullets, the five example lines taken from the template, the
  "not set" line).

Where each fix is:
1. Guide layout: `references/modes/setup.md` step 2, the line before the guide ("Keep its
   layout: one blank line before every heading, also after a list or a quote line"). The guide
   text already had a blank line before every heading; its wording is unchanged.
2. GUI note: `setup.md` step 3, right under the bold heading `**Routing tables (Tiers mode)**`,
   the line `!! YOU CAN CHANGE THIS MORE EASILY IN THE GUI LATER !!`, shown in the
   conversation language.
3. Project Stakes: `references/modes/shape.md` "2. First round": names the section of
   `.tasks/repo/profile.md`, says every agent reads it, asks the five template bullets one by
   one with a draft each, shows the template's example as a model answer; a skip writes the
   "not set" line.

## Decisions taken
- [agent] Setup step 7 does not ask for Project Stakes (it drafts the profile and shows it),
  so only shaping's question changed. `templates/repo/profile.md` needed no change.
- [agent] The Project Stakes question stays one item of the first round, with its five bullets
  numbered inside it, not five separate rounds.
- [agent] The example is quoted in `shape.md` (not only referenced) so the agent shows it; a
  test checks the quote against the template so they cannot drift.

## Risks
- The blank-line fix is an instruction; whether the terminal renderer keeps the spacing is
  only visible in a walkthrough.

## Findings filed
None.

## Round 2 (owner follow-up)
- Explanation, drafts and question now live in `stakes.ask_text` (`scripts/sae_lib/stakes.py`),
  printed by `sae status <task>` (`progress.py`) only while Project Stakes are not set.
- `shape.md` "2. First round" and `setup.md` step 7 each keep one short line pointing to the
  printed question; no second copy of the explanation (a test checks this). Round 1's quoted
  bullets and example were removed from `shape.md`.
- Tests: `test_stakes.AskTests` now checks the printed text (path, explanation, five bullets,
  template example, "not set" line, absent once set) and that both modes only point to it.
  `python3 tests/run.py test_model_config test_retired_terms test_stakes`: 44 OK.
- [agent] The example is duplicated in `stakes.py` from the template; a test keeps them equal.
- Risk: setup step 7 relies on a task existing for `sae status <task>`; setup runs "at the first task", so one should.
