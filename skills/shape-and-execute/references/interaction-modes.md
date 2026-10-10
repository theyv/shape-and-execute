# Interaction modes, decision classes and hard stops

The interaction mode in `settings.json` decides when agents ask the user during execution. It
applies to every job and every decision. Shaping and the two gates always involve the user.

## Decision classes

| Class | Meaning | Example |
|---|---|---|
| `routine` | Follows from the spec, the repository conventions or the brief. | naming; local structure; a library the repository already uses |
| `clear-choice` | Not settled by spec or intent, but one option is clearly better given the artifacts. | pagination style consistent with existing endpoints |
| `open-tradeoff` | A real tradeoff; no option is clearly better. | cached data that may be stale vs. slower live reads |
| `consequential` | Commits the code base to something lasting or risky: architecture direction, public API or contract shape, data model or schema, a new dependency, security-sensitive logic, an irreversible step inside the plan. | a new table; a changed public endpoint |
| `spec-clarification` | Makes the spec more precise without changing user-visible behavior, business rules or scope. | the exact wording of an error the spec left vague |
| `spec-change` | Changes or relaxes a requirement, a rule, the scope or user-visible behavior. | dropping a requirement that turned out impossible |

## What each mode does

| Class | full-auto | auto | critical-only | collaborative | interactive |
|---|---|---|---|---|---|
| routine | decide | decide | decide | decide | decide |
| clear-choice | decide | decide | decide | decide | **ask** |
| open-tradeoff | decide | decide | decide | **ask** | **ask** |
| consequential | decide | decide | **ask** | **ask** | **ask** |
| spec-clarification | decide | decide | **ask** | **ask** | **ask** |
| spec-change | decide | **park** | **ask** | **ask** | **ask** |

- **decide** — the orchestrator decides (with a decision worker when analysis is needed),
  logs it with `--by agent`, and the final report lists it for review before merging.
- **ask** — ask the user now. Independent work continues meanwhile.
- **park** — the affected jobs wait; independent work continues; the question waits in the
  final report.

Workers escalate (return `parked`) every decision whose class their mode marks **ask** or
**park**, and every hard stop. They decide everything else themselves. In `interactive` mode a
worker may continue with other parts of its job and escalate several questions together.

## Hard stops — every mode, including full-auto

Never do these. Park the job and report instead.

- Push, publish, deploy or release; any change to remote or shared state.
- Read, copy or change secrets and credentials beyond the repository's normal development
  setup.
- Change CI/CD configuration, access permissions, or harness and agent configuration outside
  the approved plan.
- Delete or overwrite anything the job did not create, outside its own workdir; destructive
  operations on external systems or data (databases, cloud resources, shared folders).
- Install software outside the project's dependency manager (system-wide tools).
- Without git: delete a file that existed before the task, unless the spec asks for it.

Inside its own worktree a job may delete and rewrite freely: git can restore everything.

## Safety net for full-auto

Nothing reaches the base branch without the user. Every `[agent]` decision, settled disputed
finding and amendment appears in the final report, so the user reviews them before merging.
Two stops hold in every mode: a hold the user set after a job, and a second
`changes-required` round of a review (it parks the job, or the task for the integration
review).
