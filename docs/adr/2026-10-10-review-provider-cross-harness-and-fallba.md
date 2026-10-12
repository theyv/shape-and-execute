---
title: Review provider, cross-harness and fallback
type: architecture
status: accepted
date: 2026-10-10
source: DL-42, design interview 2026-10-06 (Q16, Q29); DL-77, genesis review 2026-10-07 (G5); DL-86, implementation 2026-10-07; DL-93, task 2026-10-08-1733--sae-dogfood-fixes (R4, R7, [REVIEW-PROVIDER-CROSS-HARNESS])
applies-to: [skills/shape-and-execute/scripts/sae_lib/prompts.py, skills/shape-and-execute/scripts/sae_lib/config.py, skills/shape-and-execute/scripts/sae_lib/reviews.py, skills/shape-and-execute/references/modes/execute.md, external_review_command, other_harness, provider_text, interpret_result, cross-harness]
---

# Review provider, cross-harness and fallback

## Context
A second model reviews more critically than the one that wrote the work. The owner has a Claude
and a Codex subscription, and the second one does not always have quota.

## Decision
- [human] Each task chooses the review provider: `claude`, `codex` or `cross-harness`.
  `cross-harness` means: Codex reviews when Claude orchestrates, Claude when Codex does. Setup
  proposes it as the default. The name is the owner's.
- [agent] A failed external review falls back to the orchestrator's own harness instead of
  stopping.
- [joint] Next to the command for the other harness, `sae dispatch` prints an `IF IT FAILS:`
  line with the complete fallback command. The mode references say this in one sentence.
- [agent] A review result counts only with a valid `verdict`. Without one, `sae collect` fails
  and points to the `IF IT FAILS:` line.

## Why
- The owner uses cross-model review for heavy tasks when the second subscription has quota.
- "Other harness" sounded as if it could be any harness.
- Three paragraphs of the mode references repeated the fallback (genesis finding G5).
- `claude -p` prints errors (for example a 401) on stdout, so an external reviewer's result file
  can be non-empty and still be a failure.

## Rejected options
- The name "other harness".
- Stopping the run when the external review fails.
- The values `same` and `cross`: setting values say what they do.
