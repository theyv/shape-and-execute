---
title: A retired-terms test instead of a glossary
type: architecture
status: accepted
date: 2026-10-12
source: task 2026-10-12-1846--sae-findings-docs [DECISION-TERMS-TEST], [RETIRED-TERMS-TEST]
applies-to: [tests/test_retired_terms.py, skills/shape-and-execute]
---

# A retired-terms test instead of a glossary

## Context
The glossary in the design notes defined the skill's terms, yet old terms stayed in the compiled
`sae` code (finding "Old terms left in the compiled sae code", closed 2026-10-12).

## Decision
[joint] No glossary. `tests/test_retired_terms.py` holds a list of retired
terms and fails, with file and line, when one appears in the skill's files (`SKILL.md`,
references, templates, scripts, viewer assets). A term may be allowed in a named place where
it is still correct. Terms are defined in the skill where they are first used. When a term is
renamed, the old name goes into the test [human].

## Why
The glossary did not stop drift; a test runs. The owner: "A test is more effective than a glossary.".

## Rejected options
- A glossary.

## Consequences
- The test catches only known old names. A new synonym is caught by review.
