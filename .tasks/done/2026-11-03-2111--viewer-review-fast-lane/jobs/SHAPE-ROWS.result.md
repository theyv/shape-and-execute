---
status: done
summary: Research rows use a compact override mark so labels and model controls stay distinct.
validation: pass
changes: made
resolved: []
---

# Result: SHAPE-ROWS

Commit: `92d0cad`.

## Validation evidence

- `python3 tests/run.py test_viewer_server`: passed, 19 tests.
- `python3 tests/run.py test_graph_cards`: passed, 20 tests, 2 skipped because finished-task fixtures are absent.
- `python3 -m unittest discover -s tests -p test_sae.py -k test_worktrees_review_verify_and_finish`: passed, 1 test.
- `git diff --check`: passed. Worktree clean after commit.
- The new regression builds twelve research rows at the existing 240px card width. Eleven have overrides. It checks long model names, six effort variants, label/control separation, card bounds, full model tooltips, focusable controls, a row without an override, and the unchanged review-row mark.
- Compared the reported screenshot with the width calculation: the full override suffix exceeded the available row space despite model truncation.

## Decisions taken

- [agent] Research rows display `*` for an override. The existing tooltip and accessible label still spell out the override and full model value. Review rows and other cards keep their current text and layout.

## Risks

- Browser preview could not run: the computer-use tool reported that the browser access host is unavailable. Geometry and accessibility markup passed automated checks. The integrated visual check in BATCH-VALIDATION remains with FINAL-CHECK.

## Findings filed

None.
