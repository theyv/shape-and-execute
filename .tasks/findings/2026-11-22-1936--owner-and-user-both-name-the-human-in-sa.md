---
type: follow-up
confidence: medium
source: 2026-11-17-2334--sae-routing-harness-permissions-and-revi/FIX-LOOP-TEXTS
paths: [skills/shape-and-execute/scripts/sae_lib]
---

# Owner and user both name the human in sae texts outside the fix loop

## Observation
FIX-LOOP-TEXTS made the fix-loop texts say "user", the word SKILL.md, the mode files and the role files use (mode files: about 90 "user", no "owner"). Printed texts outside the fix loop still say "owner": asks.py (ask reminder "Before you ask the owner anything", sae ask output and help), control.py and progress.py hold notices ("Report to the owner"), progress.py "Open asks (waiting for the owner)" and the dispatch help, launch.py harness-fallback rule and sae job park ("the owner's yes"), planning.py settings help, findings.py adr help, doctor.py help. Also APPROACH_PARAGRAPH in prompts.py ("{target} parks for the owner"): a [PROMPT-SAE] text that the spec quotes and that only a prompt-text job may reword, so FIX-LOOP-TEXTS left it. One word in all printed texts needs one pass over these, with the prompt-text owner's yes for APPROACH_PARAGRAPH.

## Evidence

## Cost
<!-- friction: what it cost (time, files read, tokens). defect: what breaks, for whom.
     follow-up: what is missing without this work, and for whom. -->

## Suggestion
