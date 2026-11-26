---
id: INTEGRATION-FIX-5
covers: [SETUP-PROPOSAL]
verify:
  - python3 tests/run.py test_model_config test_retired_terms test_stakes
scope:
  - skills/shape-and-execute/references/modes/setup.md
  - skills/shape-and-execute/references/modes/shape.md
  - skills/shape-and-execute/templates/repo/profile.md
  - skills/shape-and-execute/scripts/sae_lib/stakes.py
  - skills/shape-and-execute/scripts/sae_lib/progress.py
  - tests/**
---

# INTEGRATION-FIX-5: Three fixes from the owner's first-run walkthrough

## Objective
Apply the three small fixes the owner found in the first-run walkthrough (AMEND-4).

## Inputs
- `prototypes/setup-guide.md` and `setup.md` step 2 (the guide), step 3 (the proposal),
  step 7 (the repo profile).
- `shape.md` "2. First round" (the Project Stakes question).
- `templates/repo/profile.md`, section "Project Stakes" (the five bullets and the example).

## Scope
1. Guide layout. In the walkthrough the agent showed the guide with no blank line before some
   headings ("Two ways to set routing" stuck to the list above it). Make the guide keep a blank
   line before every heading when it is shown: in the guide text itself and, if needed, one
   short instruction next to it in `setup.md`.
2. GUI note. Right after the heading of the routing tables in the step 3 proposal (shown to the
   user as "Routing tables (Tiers mode)"), the user sees this line, in the conversation
   language: `!! YOU CAN CHANGE THIS MORE EASILY IN THE GUI LATER !!`. It is for users who
   skipped the guide.
3. Project Stakes question. In the walkthrough the question was vague ("what is this project
   for and how much care does it need? ... one word is enough: toy, tool for friends, paid
   product, bank"). Make every place that asks for Project Stakes (shaping's first round, and
   setup step 7 if it asks) ask explicitly: say that the answer goes into the Project Stakes
   section of `.tasks/repo/profile.md`, that every agent reads it, and ask the template's
   bullets one by one (who uses it and why, acceptable breakage, what matters now, don't build
   (optional), so build it like), with the template's example as a model answer. A skip still
   writes the "not set" line.

## Boundaries
- No change to the dispatch prompt texts in `prompts.py`. A new problem becomes a finding.
- Keep the owner's guide wording; only the layout changes.

## Expected output
Commits on the job branch; the result names where each of the three fixes is.

## Validation
- [ ] The guide in `setup.md` has a blank line before every heading.
- [ ] The GUI note is right after the routing tables heading in step 3.
- [ ] The Project Stakes question lists the five bullets and the example, in every place
      that asks it.

## Owner follow-up (round 2)
The owner read the Project Stakes question and asked for three changes:
1. Explain first. Before the bullets, explain what Project Stakes are, in the style of the
   setup guide's intro: how much care this project needs; every worker builds to that bar and
   every reviewer judges the work against it (that is what they are for); set once per
   repository, kept in `.tasks/repo/profile.md`, editable later in the GUI or the file.
2. Drafts. The agent fills each bullet with a draft from AGENTS.md or CLAUDE.md and the README.
   Where they say nothing, the agent proposes its best guess for that bullet. The owner
   confirms or corrects.
3. Printed by `sae`, not in `shape.md`. Shaping runs often; this question is asked once per
   repository. Move the explanation and the question into the text `sae status` prints when
   Project Stakes are not set (`stakes.py` builds the "not set" line today). `shape.md` keeps
   one short line: when `sae status` shows that Project Stakes are not set, ask the question it
   prints, write the answer to the path it names, and on a skip the "not set" line. The text
   appears only while Project Stakes are not set.
