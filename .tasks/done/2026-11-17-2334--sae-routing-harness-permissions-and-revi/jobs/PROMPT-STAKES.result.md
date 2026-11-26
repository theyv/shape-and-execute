---
status: done
summary: Prompt findings 1, 6, 7, 8, 9 and 11 applied; the term is "Project Stakes" in all owned prompt text; old names retired in the test.
validation: pass
changes: made
resolved: []
---

# Result: PROMPT-STAKES

Commit `f48b0a4` on the job branch.

Per finding (lines after the change, in `skills/shape-and-execute/`):
- **1:** `SKILL.md:18-20`: third axis is **Project Stakes** ("how much care the project needs, in the section of that name; the task's settings follow them"). `references/modes/execute.md:55-58`: triage against the Project Stakes (the section `sae status` names), the bar the reviewer used; tag `[beyond Project Stakes]`.
- **6:** `references/roles/planner.md:26-28`: "your prompt gives them; when you plan inline, the section `sae status` names".
- **7:** `templates/review.md:12` ("a Project Stakes bullet") and `:18-19` (the Notes comment now uses "needs more care than the Project Stakes justify").
- **8:** `references/roles/reviewer.md:65-67`: the Project Stakes decide only where a finding goes, Findings or Notes, and it is never dropped. "Report everything you find" is gone.
- **9:** `scripts/sae_lib/prompts.py:33-35` `APPROACH_PARAGRAPH`: "{target} parks for the owner…", "earlier review rounds of {target}", answers go under "Decisions taken". The rest is unchanged.
- **11:** `references/modes/setup.md:172`: now only "A sandboxed setup waits in the backlog."
- **[AMEND-2]:** `references/modes/shape.md:29-32` (`Project Stakes: not set`, "the Project Stakes section"); `templates/repo/profile.md:10-25` (heading `## Project Stakes`, the comment, the "not set" line). `tests/test_retired_terms.py` now retires `[beyond stakes]`, `## Stakes` and `section "Stakes"`, exempts `STAKES_LINE` in `prompts.py`, and has a new test for the three terms and that exemption.

## Validation evidence
- `python3 tests/run.py test_retired_terms test_findings test_sae_ask test_adr_rules test_resolves test_dispatch_pointers`: 72 tests, OK.
- All six grep checks in `verify` pass.
- Smoke `test_worktrees_review_verify_and_finish`: OK.
- `grep -rni stakes skills/shape-and-execute` without "Project Stakes" finds only the code comment and the two constants in `prompts.py:26-28`, which STAKES-IN-PROMPTS owns. No file uses "stakes" for the task's settings.

## Decisions taken
- [agent] The `## Stakes` and `section "Stakes"` patterns are case-sensitive, inside a test whose other patterns ignore case. Without that, the lowercase prose ("the stakes") would also count as a hit.
- [agent] `STAKES_NOT_SET_LINE` needs no exemption: no retired pattern matches it. The exemption covers only the line that starts with `STAKES_LINE = `.
- [agent] Where the job gave suggested text, I smoothed it to the new name, for example "the section `sae status` names" in place of "Stakes section". The meaning is unchanged.

## Risks
- `sae` has no code yet that reads `## Stakes` or `## Project Stakes`. STAKES-IN-PROMPTS must look up `## Project Stakes` and print `Project Stakes:` in `sae status`, because `shape.md` now quotes that wording.
- The repository's own `.tasks/repo/profile.md` has no Stakes section yet, so the rename does not touch it.
