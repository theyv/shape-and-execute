---
target: VIEWER-SURFACES
verdict: changes-required
---

# Review: REVIEW-VIEWER-SURFACES

## Findings

### 1. Saving Project Stakes can rewrite unrelated sections — major

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/stakes.py:144–161` reads the whole profile through `common.py:192–195`, which normalizes line endings, then writes it back. An in-memory check confirmed that saving new stakes converted an untouched `## Validation` section from CRLF to LF.

**Affects:** `STAKES-VIEWER`

**Why it matters:** The save must change only the Project Stakes section. On a CRLF profile it changes every section and produces an unrelated diff.

**Correction:** Preserve the original bytes outside the edited section and add a save test with a CRLF profile.

### 2. Typing during a save can silently discard edits — major

**Evidence:** `skills/shape-and-execute/assets/viewer/settings.js:180–184` clears the draft when the save succeeds if it is still the same object. The input handler at `settings.js:303–305` mutates that object while the request is pending. A Node check confirmed that after submitting `first` and typing `second`, success cleared the draft even though the request contained only `first`.

**Affects:** `STAKES-VIEWER`

**Why it matters:** The editor reports success and discards text entered after Save was pressed.

**Correction:** Track the submitted draft version and preserve later edits against the newly saved base, or disable editing while the save is pending.

### 3. Concurrent saves can both pass the stale-draft check — major

**Evidence:** `skills/shape-and-execute/scripts/sae_lib/server.py:640–649` checks the base before calling the writer. The server handles requests on separate threads at `server.py:684–685`. The writer reads and replaces the file separately at `stakes.py:144–161`.

**Affects:** `STAKES-VIEWER`

**Why it matters:** Two viewer tabs can save from the same base. Both requests can report success, and the last write wins. That breaks the stale-draft protection documented in the job result.

**Correction:** Serialize the check and write for each profile. Require a valid base and test that two overlapping saves from the same base yield one success and one conflict.

### 4. Review and fix rows lack a visible routing-exception mark — minor

**Evidence:** `skills/shape-and-execute/assets/viewer/task-views.js:98–109` places reviews and fixes inside other cards. The visible badge is added only by `jobCard` at `task-views.js:184–196`. For grouped rows, `rowTip` adds the exception to the tooltip at `task-views.js:134–137`, while `rowSvg` at `task-views.js:351–357` renders no indicator.

**Affects:** `HARNESS-FALLBACK`

**Why it matters:** A fallback review can look like an ordinary review on the Plan graph. The owner must hover over its row or open the job to discover the exception.

**Correction:** Add a visible indicator to any graph row with a routing exception. Keep the requested route, actual route, and reason in its tooltip. Cover a fallback review in the rendering test.

## Notes

`git diff --check` passed. The CRLF and delayed-save checks ran in memory. The full viewer suite requires writable fixtures and was outside this read-only review.