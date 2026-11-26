---
status: done
summary: The viewer shows Project Stakes (editable from the profile, saved by a new route), launch records, routing exceptions, the bypass line, park stories and dropped jobs
validation: pass
changes: made
resolved: []
---

# Result: VIEWER-SURFACES

Commit `d9ec1b1` on `job/2026-11-17-2334--sae-routing-harness-permissions-and-revi/VIEWER-SURFACES`.

## Validation evidence
- `test -f tests/test_viewer_surfaces.py`: ok.
- `python3 tests/run.py test_viewer_surfaces test_viewer_server test_owner_ui_changes test_graph_cards test_viewer_fixes test_header_overview test_wait_signals test_sidebar_tabs`: 95 tests OK (3 skipped).
- Smoke `test_worktrees_review_verify_and_finish`: OK.
- Before that, also `test_easy_difficulty test_retired_terms` with the viewer modules: 101 tests OK. The last run (`test_viewer_surfaces test_stakes test_retired_terms test_record_privacy test_easy_difficulty test_writer_launch test_fix_loop_exits test_fix_loop_guidance test_review_rounds_setting test_sae_ask test_validation_gaps`) passed: 135 tests OK; `git diff --check` is clean.
- `tests/test_viewer_surfaces.py` (9 tests, node over app.js, task-views.js and settings.js, real server answers):
  - STAKES-VIEWER:
    - Served data when not set, from the profile, and from AGENTS.md or CLAUDE.md (read-only).
    - A save changes only the section: the head and tail of the profile stay byte-equal, and the comment under the heading stays. The next dispatch prompt holds the saved text.
    - Refusals leave every file unchanged: AGENTS.md or CLAUDE.md as the source (409), a stale `base` (409), a heading in the text (400), a non-string text (400).
    - Project settings comes before "Defaults for new tasks in".
    - The help holds the template's example lines word for word, read from `templates/repo/profile.md`.
  - LAUNCH-RECORD, HARNESS-FALLBACK, NO-SANDBOX-VISIBLE:
    - The job panel shows "Launch commands" with "bypass requested" and the placeholder command.
    - The card has the `mk rx` mark and a tooltip. The job panel names the routing exception.
    - The settings card carries the exact `bypass` line of `sae status`.
  - JOB-DROP:
    - Card "⊘ dropped" with no verdict badge. Its rows show ⊘.
    - Counts: "0 / 2" plus "4 dropped", in the slim header, the Overview, the Jobs, Reviews and sidebar views, the report and the timeline event.
    - After the other jobs finish, next() says "All jobs done." and the count reads "3 / 3".
  - PARK-STORY: the story of a job (N = 2, with a fix and its limit) in its panel and in the Overview. Every option command appears. The task's story is in the panel of the integration round that parked it.
- Checked in a browser: a scratch task with every surface, served by `sae view` and shown in headless Chrome over CDP. I took screenshots in dark and light mode of:
  - the Plan graph: the dropped card, the exception mark, the parked frame, and the bypass line in the settings card;
  - the Overview: the KPI with dropped, Needs you, and the story;
  - the CORE panel (story), the ONE panel (launch and exception) and the RIGHT panel (dropped);
  - the Project tab, and the help popover for Project Stakes;
  - the Timeline: dropped in the legend and the job.dropped event.

  Save in the real page: the button is disabled until an edit. After Save, the message appears, the source line reads "from .tasks/repo/profile.md", and only the section changed in the file. Found and fixed: the story used the class `.sx`, which the sidebar already uses. It is now `.sbd`.

## Decisions taken
- [agent] The stakes save is `DIRECT_ROUTES["stakes"]` in `server.py`. It calls `stakes.save_profile_stakes` in-process, because no `sae` command writes stakes. The module docstring and the README name this one exception.
- [agent] The save sends `base`, the profile section as the page read it. The server refuses when the section has changed since then, so an agent's write during shaping is never overwritten.
- [agent] "n / m done" leaves dropped jobs out of both numbers and shows "N dropped" next to it. `isFinal` in `app.js` treats done and dropped as final.
- [agent] The park story is drawn from the served dict (`status.park_stories`), not from `park_story_text`, so each command gets a copy button. The content is the same.
- [agent] `asks.py` needed no change.

## Risks
- The page shows the stakes with HTML comments stripped (`stakes.section_text`). So the first save drops the template's comments on each label line ("a toy | a tool for friends | …"). The comment under the heading, with the example, stays. The viewer help covers the same guidance.
- The timeline's job.dropped text lists the group in the event's order. The job panel lists it in state order. The two orders can differ.

## Findings filed
None.
