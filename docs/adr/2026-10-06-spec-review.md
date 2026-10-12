---
title: Spec review
type: architecture
status: accepted
date: 2026-10-06
source: DL-69, second design interview 2026-10-06 (S2-Q16, S2-Q17, S2-Q18, S2-D9)
applies-to: [skills/shape-and-execute/references/modes/shape.md, skills/shape-and-execute/references/roles/reviewer.md, skills/shape-and-execute/templates/review.md, skills/shape-and-execute/scripts/sae_lib/graph.py, due_reviews, add_due_review, REVIEW-SPEC]
---

# Spec review

## Context
An error in the spec multiplies in the plan and in every job. The grill rounds are the owner's
check; a second model could also attack the spec before the gate.

## Decision
Idea [human], design [joint]: a review point `spec`. When it is on and `specs.md` exists,
`REVIEW-SPEC` runs after the grill rounds, before the spec gate, with the same level, provider
and fallback as the other reviews. Setup proposes it as on by default. Its findings become the
last grill round; the owner decides; there is no automatic second round. The reviewer reads the
intent, the spec, the research reports the spec links and the code area. The reviewer protocol
(`references/roles/reviewer.md`, section "Target `spec`") tells it to attack the design against
the intent, not implementation detail.

## Why
- The owner: "This could have a substantial effect at the right point in the process.".
- On timing: "The draft spec is an outline; the questioning process refines it.".
- On the lens: "Focus on the architecture and the approach to implementing the intent rather than detailed implementation steps."; "I will refine it through use.".
- A second model is strongest on documents (agent).

## Rejected options
- A review right after the first draft (the agent's proposal): the draft is too rough.
- Always on, without a setting.
- An ad hoc offer.
- A separate `review-spec.md` (the owner's first idea): a section in the file the reviewer
  already reads is lighter.
