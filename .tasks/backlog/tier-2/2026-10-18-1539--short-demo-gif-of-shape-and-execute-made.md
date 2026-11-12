# Intent: Short demo GIF of shape-and-execute made by an agent

## Problem
The README starts with static screenshots of the showcase (from the first public
release). A short moving demo would show the tool better. The owner will not record
by hand: on another project a manual video with subtitles took one day.

## Goal
An agent makes a short GIF for the README, with no manual recording. The owner also wants to
learn how agents do this: "Agents have improved at creating demos, so this is worth trying.".

## Proposed outcome
A short GIF at the top of the README, made and reproducible by an agent.

## Constraints
- No manual recording, no manual subtitles.

## Related tasks
Builds on the first public release — start after the public repository exists.

## Open questions
- What to show: the viewer while a task runs (the job graph filling in), a terminal session,
  or the showcase. The showcase has no animation, so a GIF of it would only scroll.
- Which tools: known at 2026-10-18 on the owner's machine are node, Playwright with its
  Chromium and its bundled ffmpeg; no system ffmpeg, vhs or asciinema.
