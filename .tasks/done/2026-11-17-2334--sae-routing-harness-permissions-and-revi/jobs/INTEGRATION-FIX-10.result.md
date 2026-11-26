---
status: done
summary: More than one Project Stakes heading line makes the section ambiguous; save is refused, lookup says so.
validation: python3 tests/run.py test_stakes test_viewer_surfaces passed (53 tests)
changes:
  - skills/shape-and-execute/scripts/sae_lib/stakes.py
  - tests/test_stakes.py
---

## Validation
Verify command passes. New test `test_a_second_project_stakes_heading_makes_the_section_ambiguous` covers the review's case (fenced example heading before the real one): save raises naming "lines 5, 9", file byte-identical; one heading saves as before.

## Decisions taken
- [agent] Rule: more than one level-2 `Project Stakes` heading line (same match as the reader, case-insensitive) is ambiguous. `_find_section` returns None then (readers see "missing", revision ""), and `save_profile_stakes` raises ValueError first.
- [agent] Lookup path: `find_stakes` returns a Stakes for the profile whose text is the short ambiguity message (names the lines), so dispatch prompts and the viewer show it, and the viewer stays editable. server.py needed no change: the save's ValueError already becomes a 400 with the message. Only the profile is checked; AGENTS.md/CLAUDE.md are never written.
