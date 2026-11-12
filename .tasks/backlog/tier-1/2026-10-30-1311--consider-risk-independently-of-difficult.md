# Intent: Consider risk independently of difficulty in review

## Problem

The difficulty of making a change does not necessarily reflect the consequences of a mistake.
A three-line authorization change may be mechanical but high risk. A 500-line refactor of test
code may be difficult but have low consequences. The owner considers risk-based review more
important than choosing individual models.

## Ideas to explore

- Consider a separate `risk` parameter that affects review independently of `difficulty`.
- Explore how risk should influence the choice and strength of review.
- Consider how a reviewer can independently assess the diff, specification, and test results,
  rather than only approving the implementer's reasoning.

As an illustration, a small authorization middleware change might be mechanical difficulty
and high risk, with Terra Medium for execution and Sol High for review. This is an example to
examine, not a decided policy.

## Open questions

- How should risk be assessed, and who should assess it?
- How should risk and difficulty jointly affect review and model selection?
- What evidence and separation does an independent review need?

This is a proposal for consideration and investigation. Its design and adoption are undecided.
