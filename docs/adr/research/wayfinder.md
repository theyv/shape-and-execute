# Wayfinder (mattpocock/skills)

Question: how does Matt Pocock's `wayfinder` skill handle work that is too big for one session,
drift, and newly discovered or out-of-scope work? The owner named it as a model for a loop for
big tasks.

Read 2026-10-06 by a research subagent from `mattpocock/skills`, branch `main` at commit
`6fd9479`. Sources: [S] `skills/engineering/wayfinder/SKILL.md`; [T] the "Wayfinding operations"
section of the tracker docs in `setup-matt-pocock-skills/`; [D] `docs/engineering/wayfinder.md`
(the author's commentary, not part of the skill). Unverified items are marked UNKNOWN.

| Topic | Fact | Source |
|---|---|---|
| Purpose | "A loose idea has arrived, too big for one agent session, and wrapped in fog". It charts "a shared map of decision tickets" and resolves them one at a time. | S |
| Output | "produce decisions, not deliverables". The destination is a spec to hand off, a decision to lock before planning, or an in-place change. The map's Notes can make it carry execution. | S |
| Trigger | User-invoked only. More than one agent session of work; each ticket "sized to one 100K token agent session". When the opening grill finds no fog: "you don't need a map". | S |
| Charting session | Name the destination (grilling, domain modeling) → map the frontier breadth-first → create the map issue → create the tickets that are already sharp, wire blocking edges in a second pass → fire research subagents → stop. Charting resolves nothing. | S |
| Work session | Load the map ("the low-res view") → take the named ticket or the first frontier ticket → claim it (assignee) → resolve it → answer as a comment, close, append a pointer to "Decisions so far" → add new tickets, graduate fog, rule items out of scope, update or delete tickets the decision invalidated. "never resolve more than one ticket per session", except research tickets. | S |
| Storage | Issue tracker. The map is one issue labelled `wayfinder:map` with Destination, Notes, Decisions so far, Not yet specified, Out of scope. A ticket is a child issue holding only `## Question`; the answer is a comment. GitHub: sub-issues, native blocking, claim = assignee. Fallback: `.scratch/<effort>/map.md` and `issues/NN-<slug>.md`. | S, T |
| Unit of decomposition | Decision tickets: "questions whose resolution is a decision, not slices of a build to execute". Types: research (unattended), prototype, grilling (default), task (manual work that unblocks a decision). Vertical slicing happens later, in `to-tickets`. | S, D |
| Lazy detail | "don't chart what you can't yet see". Only a sharp question becomes a ticket; fog stays in "Not yet specified" and graduates one item at a time: "Don't pre-slice the fog into ticket-sized pieces". | S |
| Drift | No separate re-plan phase: each resolution updates or deletes the tickets it invalidated. Reopening a closed decision: UNKNOWN (not stated). The author reports a 27-ticket map that went stale and advises a bounded destination and early prototypes. | S, D |
| Out of scope | One line in "Out of scope" (gist, why, link). "Out-of-scope work never graduates"; it returns only "as a fresh effort" when the destination is redrawn. There is no backlog. | S |
| Human in the loop | For grilling and prototype tickets "the agent never stands in for the human's side of it". The user starts every session. Approval before creating the map or tickets: UNKNOWN (not stated). The author reports an agent that picked a prototype variant itself and closed the ticket. | S, D |
| Done | "until the way to the destination is clear and no tickets remain". The hand-off is not named in the skill; the author's docs continue with `/to-spec`, `/to-tickets`, `/implement`. | S, D |
| Weight | `SKILL.md` 128 lines (about 2,000 words) plus `agents/openai.yaml`; it calls grilling, domain-modeling, research and prototype skills. The author calls it "the heaviest flow in the set". | S, D |

Consequences for the design:

- Wayfinder is a loop of decisions in front of execution. It matches this skill's shaping
  stretched over many sessions, not a series of execution tasks. Shaping here already resumes
  from files and runs research in parallel, so no decision map was added
  ([Big work goes lazily through the backlog](../2026-10-06-big-work-goes-lazily-through-the-backlog.md)).
- Its lazy rule supports giving deferred work a spec only when someone picks it up
  ([A backlog item is an intent file](../2026-10-10-a-backlog-item-is-an-intent-file.md)). The
  stale map argues against specifying a whole series up front and against a hand-kept map
  ([Relations between tasks are prose](../2026-10-06-relations-between-tasks-are-prose.md)).
- "Out-of-scope work never graduates" differs on purpose: here work the owner defers becomes a
  backlog item at once, because the owner wants to keep it
  ([Agents file findings and the owner fills the backlog](../2026-10-12-agents-file-findings-and-the-owner-fills.md)).
