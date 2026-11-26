# Intent: Reviews judge against the project's real use, not a worst-case threat model

## Problem

In a single-owner home app, the adversarial reviewer keeps raising findings for cases no real
user reaches: two app starts in the same instant over a stale lock, then a crash inside the
microsecond window of the fix for that. Each round added more locking machinery; the second fix
reintroduced the exact failure the owner had hit (a leftover file blocking every start). The
orchestrator passed the findings on as fix jobs instead of filtering them. The owner has said
several times that the app is "not a bank" and must simply work for a normal person, and the
project's AGENTS.md says "Keep it light"; the reviews did not weigh either.

## Desired outcome

- The reviewer reads the project's stated risk level (AGENTS.md, brief) and grades findings
  against it. A finding names a step a real user would take; theoretical races, hostile local
  users and tampered files are notes, not findings, unless the project says otherwise.
- The orchestrator triages each changes-required finding against the same bar before adding a
  fix job, and uses accept-review with a reason when a finding fails it.
- A fix that adds safeguard machinery is itself checked for new ways to fail in normal use.

## Evidence

A task in a private single-owner app (2026-11-16): review rounds 1 and 2 of a sign-in and lock job (2026-11-17).
