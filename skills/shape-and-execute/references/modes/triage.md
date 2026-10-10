# Triage mode

Two queues wait for the user: **findings** that agents left in `.tasks/findings/`, and
**decision-record drafts** in `.tasks/adr/`.

1. `sae triage` prints a table of counts: findings by type, decision drafts, the oldest of
   each. Show it.
2. Ask which queue to work on. Load only that reference:
   - findings → [triage-findings.md](triage-findings.md) — fix now, later, leave open or
     reject;
   - decision drafts → [triage-decisions.md](triage-decisions.md) — accept into the
     repository's ADR folder, or reject.
3. After one queue, offer the other when it is not empty.

Triage commits nothing: tell the user which files changed; they commit them.
