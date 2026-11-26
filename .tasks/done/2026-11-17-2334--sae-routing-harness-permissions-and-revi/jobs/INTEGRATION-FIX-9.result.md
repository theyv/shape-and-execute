---
status: done
summary: Plan card and Reviews tab show an accepted integration round as accepted, with its reason; the verdict stays visible.
validation: python3 tests/run.py test_viewer_surfaces test_viewer_fixes passes (25 tests); the new test fails without the fix.
changes:
  - skills/shape-and-execute/assets/viewer/task-views.js
  - tests/test_viewer_surfaces.py
---

## Validation evidence
New `AcceptedIntegrationRoundTests` builds a changes-required integration round, checks the card shows
`✕ changes required`, runs `sae accept-review`, then checks: card badge `◆ accepted`, card and row tooltips carry
the reason, Reviews tab shows "Verdict: changes required · accepted: <reason>" and the numbered findings.
Run with the JS change stashed: fails (`✕ changes required != ◆ accepted`).

## Decisions taken
- [agent] No server.py change: the state's job record already holds `accepted` (reason, at, by).
