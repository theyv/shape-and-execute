# Triage: decision-record drafts

Turn the drafts in `.tasks/adr/` into accepted records in the repository's documentation, or
reject them. A record explains why something is the way it is; only durable ones belong in
the repository.

1. Read every draft (all files except `closed.md`).
2. Check each against the repository: does it still hold? Does it pass the test, and does its
   reach call for a record, not a code comment or a directory `AGENTS.md` ([plan.md](plan.md)
   "Decision-record drafts")? Does it repeat a record already in the ADR folder?
3. Say briefly which drafts belong in the docs and which do not, with one reason each. Ask in
   the grill format ([grill.md](../grill.md)).
4. For each draft the user keeps: write the final text together with the user, in the draft
   file. Keep the user's quoted words where they carry the "why", smoothed
   (SKILL.md, "Smooth every quote"), and the "applies to" paths
   and code names, so that a code search finds the record.
5. `sae adr accept <draft>` moves it into the ADR folder and prints where.
   `sae adr reject <draft> --reason "<why>"` closes a rejected one with its reason.
6. When `sae adr accept` says this is the first record in the folder: propose one line for the
   repository's agent instructions (AGENTS.md or CLAUDE.md) that points to the folder, for
   example "Decision records (why the code is this way): `docs/decisions/`. Search them by
   path or code name before you change that code." Write it only after the user approves.
