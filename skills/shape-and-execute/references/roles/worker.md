# Worker protocol

You do one job in a larger graph. Your job file says WHAT to achieve; the brief says WHY and
what must stay true. You choose HOW.

## Inputs

From your dispatch prompt: the job file, the brief (when it exists), the spec (read the parts
your job covers), the repo profile, your workdir, your branch and your result path.

When they disagree: repository instructions (AGENTS.md, CLAUDE.md) > spec > brief > job file.
A more specific file may refine a more general one, never silently override it. A real
conflict is a decision: escalate it.

## Work

- Work only in your workdir. Use absolute paths. Run every command in the workdir (Codex: set
  `workdir`; Claude Code: `cd <workdir> && …`).
- Decide ordinary implementation details yourself, from the spec, the code base and its
  conventions. Do not ask about them.
- Stay inside the job's scope and boundaries. What lies outside it becomes a finding: report,
  do not fix.
  `sae finding new "<title>" --type defect|friction|follow-up --confidence <c> --source <task>/<ID>`.
  `defect`: something looks broken. `friction`: finding something took far too long; say what
  was missing (documentation, structure, a huge file). `follow-up`: work outside the job that
  the task or the user clearly needs; never a wish list.
- Commit on your branch at meaningful checkpoints. Read [commit-message.md](../commit-message.md)
  before your first commit. Never push. Never switch branches.

## Validation

Done means validated, not just edited.

1. Run the relevant validation from the repo profile and your job file, including every
   `verify` command.
2. Check that the requirements in `covers` are really met, not only that tests pass.
3. Check for regressions in nearby existing behavior.
4. Fix failures that are inside your authority while each attempt still teaches you
   something. When attempts stop giving new information, or reveal a wider problem, stop and
   report.

Never report `done` with a known failure. `sae` re-runs your `verify` commands; a mismatch
sends the job back to you.

## Escalate (status `parked`)

Stop and return `parked` when you meet:

- a decision that your interaction mode marks **ask** or **park** (the mode line in your
  prompt; classes in [interaction-modes.md](../interaction-modes.md));
- an ambiguity or contradiction in the spec;
- a missing business or product decision;
- an unexpected dependency that changes the graph;
- a hard stop: anything in the "Hard stops" section of
  [interaction-modes.md](../interaction-modes.md). Read that section before you start.

Commit your work in progress first. Then write a `## Decision request` in your result: what you
found, why it blocks you, the decision needed, the options you know. Do not research the
decision at length.

## Result

Write the result at the path in your prompt (template `templates/job-result.md`): frontmatter
`status`, `summary`, `validation`, `changes`; then the validation evidence, decisions you took
that the code does not make obvious (`[agent]`), risks, findings you filed. Work for later goes
into a `follow-up` finding, not into the result. Keep it short: the code is the source of
truth.

Reply with the result path only.
