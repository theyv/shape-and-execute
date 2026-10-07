# Commit messages

**Title:** `<JOB-ID>: <what changed, imperative, at most 72 characters>`

**Body — only what the code does not show.** The diff is the source of truth for WHAT; a later
agent reads it easily. Write the parts that the code cannot carry:

- a decision you took, and why, when it is not obvious;
- an alternative you rejected, and why;
- a trap or caveat for the next person;
- a follow-up this commit leaves open on purpose.

At most about five bullets. When nothing is non-obvious, write no body. Do not list files, do
not restate the diff, do not narrate your process.

**Trailers** — the last lines, exactly as given in your prompt:

    Task: <task-id>
    Job: <JOB-ID>
    Model: <model>

Example:

    STATUS-API: add claim status endpoint

    - Read status from claims-core, not the portal cache: the cache lags up to
      15 minutes, which breaks RULE-CLOSED-CLAIM.
    - Kept the v1 response envelope; v2 would force a portal release.

    Task: 2026-10-06-1430--claims-status
    Job: STATUS-API
    Model: <model>
