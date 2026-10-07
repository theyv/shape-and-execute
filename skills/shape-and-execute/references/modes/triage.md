# Triage mode

Turn the findings that agents left in `.tasks/findings/` into decisions: fix now, later, leave
open, or reject.

1. Read every open finding (all files except `closed.md`). Check `closed.md` for repeats: a
   finding that was already fixed or rejected is closed again with a pointer to the earlier
   line.
2. Merge duplicates: the same cause, reported by different agents.
3. Present the findings grouped by type (`defect`, `friction`, `follow-up`) and by area, in
   plain words: what is wrong, slow or missing, how sure we are, what it costs, what a fix
   could look like. Most valuable first. Friction often points at missing documentation, huge
   files or unclear structure; fixing it makes every later task cheaper, so say so when you
   rank.
4. Ask in the grill format ([grill.md](../grill.md)) what to do with each group: fix now (a new
   task), later (a backlog item), leave open, or reject (with a reason).
5. Fix now → start a new task with [shape.md](shape.md), with the findings as the note. The
   intent links the finding files.
   Later → `sae new "<title>" --backlog`, and write its intent from the findings: what should
   be true when it is done, with the finding files as evidence.
6. Close what was handled:
   `sae finding close <file> --outcome "fixed in <task-id>"` (when that task finishes),
   `--outcome "moved to backlog/<file>"`, `--outcome "rejected: <reason>"` or
   `--outcome "duplicate of <finding>"`.
