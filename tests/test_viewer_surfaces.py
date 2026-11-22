"""The viewer shows the data of this task's backend jobs: the Project Stakes in a new Project settings
section with their save route, the launch record of each COMMAND attempt, routing exceptions, the bypass
line in the settings card, the story of a park at the round limit, and dropped jobs.

Run from the repository root:  python3 tests/run.py test_viewer_surfaces
Spec: [STAKES-VIEWER], [STAKES-TEMPLATE], [LAUNCH-RECORD], [HARNESS-FALLBACK], [NO-SANDBOX-VISIBLE],
[PARK-STORY], [JOB-DROP], [AMEND-2].
"""

from __future__ import annotations

import re
import shutil
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from saetest import SCRIPTS, SKILL_DIR, Sandbox, SaeTestCase, dispatch_workspace
from test_fix_loop_exits import FixLoopCase
from test_fix_loop_guidance import GuidanceCase
from test_viewer_server import ViewerServerCase, request, run_node

sys.path.insert(0, str(SCRIPTS))
from sae_lib import server, stakes  # noqa: E402

NODE = shutil.which("node")
TEMPLATE = SKILL_DIR / "templates" / "repo" / "profile.md"

# app.js, task-views.js and settings.js in node; argv: the three files, the data file, then one expression.
# `#side` keeps what renderSide writes; TASK is the data; the expression's value is printed as JSON.
PAGE_JS = r"""
const vm = require("vm"), fs = require("fs");
const el = () => new Proxy({innerHTML: "", hidden: true, dataset: {}, style: {},
  classList: {toggle() {}, contains() { return false }, add() {}, remove() {}}, addEventListener() {}, querySelectorAll() { return [] }},
  {get: (t, k) => k in t ? t[k] : () => null});
const els = {};
const ctx = {console, setTimeout: () => 0, clearTimeout() {}, setInterval() {}, addEventListener() {}, history: {replaceState() {}},
  location: {hash: ""}, localStorage: {getItem() { return null }, setItem() {}},
  document: {hidden: false, title: "", documentElement: {dataset: {}}, body: el(), activeElement: null,
    querySelector: s => els[s] || (els[s] = el()), querySelectorAll: () => [], addEventListener() {}, createElement: el}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 5)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
ctx.DATA = JSON.parse(fs.readFileSync(process.argv[5], "utf8"));
ctx.TASK = ctx.DATA && ctx.DATA.state ? ctx.DATA : null;
console.log(JSON.stringify(vm.runInContext(`readHash(); IDX = {sae: "sae", root: "/r", tasks: [], repo: "r"};
  S.task = TASK ? TASK.state.task.id : null; S.repo = "R"; ` + process.argv[6], ctx)));
"""

# A Project Stakes save that stays pending: `post` keeps the callback, document listeners are kept so the
# test can type into the box, and `done` answers the save. Prints what was sent, the section while pending,
# the draft after the typing, the draft after success and the message.
PENDING_SAVE_JS = PAGE_JS.replace("addEventListener() {}, createElement: el}};",
                                  "addEventListener(t, f) { (L[t] = L[t] || []).push(f) }, createElement: el}};") \
    .replace("const els = {};", "const els = {}, L = {};").replace("ctx.window = ctx;", "ctx.window = ctx; ctx.L = L;") \
    .replace("process.argv[6], ctx)", """`
  SX.cur = {key: "R|null", proj: DATA}; var sent, done;
  post = (route, body) => { sent = body; return {then(f) { done = f }} }; sxLoad = () => {}; renderMain = () => {};
  SX.stk = {repo: "R", text: "first", base: ""}; sxStakesSave();
  var pending = sxStakesSec();
  L.input.forEach(f => f({target: {dataset: {act: "sxst"}, value: "first second", selectionStart: 12, selectionEnd: 12}}));
  var typed = SX.stk && SX.stk.text;
  done({ok: true, result: {stakes: DATA.stakes}});
  ({sent, pending, typed, after: SX.stk, msg: SX.msg})`, ctx)""")

CARD = "var g = graph(TASK), c = id => g.cards.find(x => x.id === id) || null;"


def page(data, expression: str):
    return run_node(PAGE_JS, "app.js", "task-views.js", "settings.js", data=data, args=(expression,))


def text(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html.replace("<br>", "\n").replace("</p>", "</p>\n")).replace("&#39;", "'").replace("&#60;", "<") \
        .replace("&#62;", ">").replace("&#34;", '"').replace("&#38;", "&")


def template_example() -> list[str]:
    """The example lines of the template's Project Stakes comment, from its first line to "A toy."."""
    lines = [line.strip() for line in TEMPLATE.read_text().splitlines()]
    start = lines.index("Example, a small game for a kid:")
    end = next(i for i in range(start, len(lines)) if lines[i].startswith("- So build it like:"))
    return lines[start:end + 1]


PROFILE = """---
adr_folder: docs/adr
---

# Repo profile

<!-- Facts, and the owner's Project Stakes. -->

## Project Stakes
<!-- Why the project exists and how much care it needs. Every agent reads it. -->
- Who uses it and why:
- Acceptable breakage:   <!-- how much -->
- What matters now:
- Don't build:
- So build it like:

## Validation commands
- Smoke: `make smoke`

## Hot files
- lockfile
"""


@unittest.skipUnless(NODE, "node runs the viewer scripts")
class ViewerCase(ViewerServerCase):
    def served(self, sb: Sandbox, path: str) -> dict:
        view = getattr(self, "_view", None) or self.view(sb)
        self._view = view
        code, data, _ = request(view["port"], "GET", f"{path}{'&' if '?' in path else '?'}repo={view['repo']}")
        self.assertEqual(code, 200, data)
        return data

    def task(self, sb: Sandbox, task: str) -> dict:
        return self.served(sb, f"/api/task?task={task}")

    def save(self, sb: Sandbox, body: dict):
        view = self._view
        return self.post(view["port"], "stakes", {"repo": view["repo"], **body}, self.token(view["port"]))


class ProjectStakesTests(ViewerCase):
    """[STAKES-VIEWER]: the data, the save route and the Project settings section."""

    def stakes(self, sb: Sandbox) -> dict:
        return self.served(sb, "/api/settings")["stakes"]

    def section(self, answer: dict) -> dict:
        return page(answer, """SX.cur = {key: "R|null", proj: DATA}; SX.tab = "project";
          ({sec: sxStakesSec(), tab: TAB.settings(null), help: HELP.stakes})""")

    def test_not_set_then_saved_to_the_profile_section_only(self):
        sb = self.sandbox()
        profile = sb.repo / ".tasks" / "repo" / "profile.md"
        profile.parent.mkdir(parents=True)
        profile.write_text(PROFILE)
        data = self.stakes(sb)
        self.assertEqual((data["source"], data["editable"], data["profile_name"]), (None, True, ".tasks/repo/profile.md"))
        self.assertEqual(data["draft"].splitlines()[0], "- Who uses it and why:")
        self.assertEqual(len(data["draft"].splitlines()), 5)
        # the Project tab: Project settings first, the edit box with the five labels, Save waits for a change
        out = self.section(self.served(sb, "/api/settings"))
        tab = out["tab"]
        self.assertLess(tab.index("<h3>Project settings</h3>"), tab.index("Defaults for new tasks in"))
        self.assertIn('<textarea class="stk" data-act="sxst"', out["sec"])
        self.assertIn("- Acceptable breakage:", out["sec"])
        self.assertIn("Project Stakes", out["sec"])
        self.assertIn("not set: agents estimate them", out["sec"])
        self.assertRegex(out["sec"], r'data-act="sxsv" data-k="save" disabled')
        # Save: only the section changes; the comment under the heading stays
        new = ("- Who uses it and why: A tool for the owner's own projects.\n- Acceptable breakage: Some.\n"
               "- What matters now: Fewer review rounds.\n- So build it like: A tool for friends.")
        code, answer, _ = self.save(sb, {"text": new, "base": data["base"]})
        self.assertEqual(code, 200, answer)
        self.assertTrue(answer["ok"])
        self.assertEqual(answer["result"]["stakes"]["source_name"], ".tasks/repo/profile.md")
        after = profile.read_text()
        head, tail = PROFILE.split("## Project Stakes\n")
        self.assertTrue(after.startswith(head + "## Project Stakes\n<!-- Why the project exists"))
        self.assertTrue(after.endswith("\n\n## Validation commands\n- Smoke: `make smoke`\n\n## Hot files\n- lockfile\n"))
        self.assertIn(new, after)
        self.assertNotIn("- Don't build:", after)
        data = self.stakes(sb)
        self.assertEqual((data["source_name"], data["editable"]), (".tasks/repo/profile.md", True))
        self.assertIn("Fewer review rounds", data["text"])
        out = self.section(self.served(sb, "/api/settings"))
        self.assertIn("from .tasks/repo/profile.md", out["sec"])
        # the next dispatch prompt reads the saved text ([STAKES-LOOKUP])
        task = sb.new_task("Uses stakes", "uses")
        sb.sae("job", "add", "uses", "R1", "--kind", "research")
        sb.job_file(task, "R1")
        self.assertIn("Fewer review rounds", sb.json("dispatch", "uses", "R1")["prompt"])

    def test_refusals_leave_every_file_as_it_was(self):
        sb = self.sandbox()
        profile = sb.repo / ".tasks" / "repo" / "profile.md"
        profile.parent.mkdir(parents=True)
        profile.write_text(PROFILE)
        data = self.stakes(sb)
        # a profile changed since the page read it
        profile.write_text(PROFILE.replace("- What matters now:", "- What matters now: Speed."))
        before = profile.read_text()
        code, answer, _ = self.save(sb, {"text": "- So build it like: A toy.", "base": data["base"]})
        self.assertEqual(code, 409, answer)
        self.assertIn("changed since this page read them", answer["error"])
        self.assertEqual(profile.read_text(), before)
        # a heading would split the section
        code, answer, _ = self.save(sb, {"text": "## Other\n- x", "base": self.stakes(sb)["base"]})
        self.assertEqual(code, 400, answer)
        self.assertEqual(profile.read_text(), before)
        code, answer, _ = self.save(sb, {"text": None})
        self.assertEqual(code, 400, answer)
        # a save without the section it started from could overwrite a newer one
        code, answer, _ = self.save(sb, {"text": "- So build it like: A toy."})
        self.assertEqual(code, 400, answer)
        self.assertIn("base", answer["error"])
        self.assertEqual(profile.read_text(), before)

    def test_stakes_from_agents_md_or_claude_md_are_read_only(self):
        sb = self.sandbox()
        for name in ("AGENTS.md", "CLAUDE.md"):
            with self.subTest(source=name):
                for old in ("AGENTS.md", "CLAUDE.md"):
                    (sb.repo / old).unlink(missing_ok=True)
                instructions = sb.repo / name
                instructions.write_text("# Rules\n\n## Project Stakes\n- Who uses it and why: A team tool.\n\n## Other\nx\n")
                before = instructions.read_text()
                data = self.stakes(sb)
                self.assertEqual((data["source_name"], data["editable"]), (name, False))
                self.assertEqual(data["text"], "- Who uses it and why: A team tool.")
                out = self.section(self.served(sb, "/api/settings"))
                self.assertNotIn("<textarea", out["sec"])
                self.assertIn('<pre class="stk ro">- Who uses it and why: A team tool.</pre>', out["sec"])
                self.assertIn(f"from {name} · edit there", out["sec"])
                code, answer, _ = self.save(sb, {"text": "- So build it like: A toy.", "base": data["base"]})
                self.assertEqual(code, 409, answer)
                self.assertIn(f"come from {name}: edit them there", answer["error"])
                self.assertEqual(instructions.read_text(), before)
                self.assertFalse((sb.repo / ".tasks" / "repo" / "profile.md").exists())

    def test_typing_is_blocked_while_a_save_is_pending(self):
        # post never answers until `done` runs: the draft "first" is submitted, the owner types, then the save succeeds
        stakes = {"editable": True, "draft": "", "base": "", "source": None, "source_name": None,
                  "profile_name": ".tasks/repo/profile.md", "text": None}
        out = run_node(PENDING_SAVE_JS, "app.js", "task-views.js", "settings.js", data={"stakes": stakes})
        self.assertEqual(out["sent"], {"repo": "R", "text": "first", "base": ""})
        self.assertRegex(out["pending"], r'<textarea class="stk"[^>]*aria-label="Project Stakes" disabled>')
        self.assertRegex(out["pending"], r'data-act="sxsv" data-k="save" disabled')
        self.assertRegex(out["pending"], r'data-act="sxsv" data-k="discard" disabled')
        self.assertEqual(out["typed"], "first", "an edit made while the save is pending must not enter the sent draft")
        self.assertIsNone(out["after"])
        self.assertIn("Saved the Project Stakes", out["msg"])

    def test_the_help_shows_the_template_example_word_for_word(self):
        help_text = text(page(None, "HELP.stakes"))
        example = template_example()
        self.assertEqual(len(example), 6)
        for line in example:
            self.assertIn(line, help_text.splitlines())
        self.assertIn("[beyond Project Stakes]", help_text)
        self.assertIn("Planners and workers size their work by them", help_text)
        self.assertIn("hard limits belong in the repository instructions", help_text)
        self.assertNotIn("[beyond stakes]", help_text)


class OverlappingStakesSaveTests(SaeTestCase):
    """[STAKES-VIEWER]: two saves from the same base, on two request threads, give one success and one conflict."""

    def test_overlapping_saves_from_one_base(self):
        sb = self.sandbox()
        profile = sb.repo / ".tasks" / "repo" / "profile.md"
        profile.parent.mkdir(parents=True)
        profile.write_text(PROFILE)
        base = stakes.section_text(profile) or ""
        write = stakes.save_profile_stakes

        def slow_write(root, text):  # the first writer holds the window between check and write open
            time.sleep(0.3)
            return write(root, text)

        answers = []
        with mock.patch.object(server, "repo_by_key", return_value=sb.repo), \
                mock.patch.object(stakes, "save_profile_stakes", slow_write):
            threads = [threading.Thread(target=lambda t=t: answers.append(
                server.save_stakes({"repo": "R", "text": f"- So build it like: {t}.", "base": base})))
                for t in ("A toy", "A tool")]
            for thread in threads:
                thread.start()
                time.sleep(0.05)
            for thread in threads:
                thread.join()
        self.assertEqual(sorted(code for code, _ in answers), [200, 409], answers)
        saved = next(a for code, a in answers if code == 200)["result"]["stakes"]["text"]
        self.assertEqual(stakes.section_text(profile), saved)
        self.assertIn("changed since this page read them", next(a for code, a in answers if code == 409)["error"])


class LaunchAndExceptionTests(ViewerCase):
    """[LAUNCH-RECORD], [HARNESS-FALLBACK], [NO-SANDBOX-VISIBLE] in the job panel, the card and the settings card."""

    def test_command_attempt_shows_its_launch_and_the_card_marks_the_exception(self):
        sb = self.sandbox()
        task = sb.new_task("Launch", "launch")
        for job in ("ONE", "TWO"):
            sb.sae("job", "add", "launch", job, "--kind", "implementation")
            sb.job_file(task, job)
        sb.approve_plan("launch")
        sb.sae("start", "launch")
        data = self.task(sb, task)
        out = page(data, "headerCard(TASK)")
        self.assertNotIn("byp", out)
        # ONE goes to the other harness by a dispatch flag: a COMMAND attempt and a routing exception
        sb.sae("dispatch", "launch", "ONE", "--harness", "codex")
        data = self.task(sb, task)
        self.assertEqual([(e["job"], e["attempt"]) for e in data["routing_exceptions"]], [("ONE", 1)])
        self.assertTrue(data["routing_exceptions"][0]["text"].startswith("routing exception: requested claude"))
        out = page(data, CARD + """({card: c("ONE"), two: c("TWO"), svg: g.svg, body: jobBody(TASK, "ONE"),
          head: headerCard(TASK), ev: (TASK.events || []).filter(e => e.type === "job.dispatched").map(e => evText(TASK, e))})""")
        body = text(out["body"])
        launch = data["state"]["jobs"]["ONE"]["attempts"][0]["launch"]
        self.assertIn("Launch commands", body)
        self.assertIn("what the command requested; the launch environment can still restrict the job", body)
        self.assertIn("bypass requested", body)
        self.assertIn(launch["command"], body)
        self.assertIn("<workdir>", body)
        self.assertNotIn(str(sb.tmp), body)
        self.assertIn("Routing exception⇄ ran on another route than routing chose", body)
        self.assertIn("Attempt 1: requested claude", body)
        self.assertIn("ran codex", body)
        self.assertIn('class="mk rx"', out["svg"])
        self.assertIn("Routing exception — Attempt 1: requested claude", out["card"]["tip"])
        self.assertNotIn("rx", out["two"] or {})
        self.assertIn("bypass requested", out["ev"][0])
        # [NO-SANDBOX-VISIBLE]: the settings card carries the line of `sae status`
        self.assertEqual(text(re.search(r'<div class="byp" role="note">(.*?)</div>', out["head"]).group(1)),
                         "⚠ " + data["status"]["bypass"])
        self.assertIn("(no sandbox, no approvals): ONE", data["status"]["bypass"])
        self.assertIn(data["status"]["bypass"], sb.sae("status", "launch").stdout)


class DroppedJobTests(ViewerCase, FixLoopCase):
    """[JOB-DROP]: cards, rows, the job panel, lists and counts; dropped counts as final."""

    def test_a_dropped_group_in_every_view(self):
        sb = self.sandbox()
        task = self.planned(sb, "drop", [
            ("LEFT", "implementation", "", []),
            ("RIGHT", "implementation", "", ["--review"]),
            ("FINAL", "validation", "LEFT,RIGHT", ["--final"]),
        ], settings=["review=selected-jobs,integration"])
        self.run_writer(sb, task, "drop", "RIGHT")
        self.review_with(sb, task, "drop", "REVIEW-RIGHT", "RIGHT", "changes-required", ["Wrong approach"])
        sb.sae("job", "add", "drop", "RIGHT-FIX-1", "--kind", "implementation", "--fix-of", "RIGHT", "--reason", "round 1")
        sb.job_file(task, "RIGHT-FIX-1")
        self.run_writer(sb, task, "drop", "RIGHT-FIX-1")
        sb.sae("job", "edit", "drop", "FINAL", "--needs", "LEFT", "--reason", "RIGHT is dropped")
        sb.sae("job", "drop", "drop", "RIGHT", "--reason", "owner: wrong approach")
        data = self.task(sb, task)
        out = page(data, CARD + """({card: c("RIGHT"), head: slimHead(TASK), overview: TAB.overview(TASK), jobs: TAB.jobs(TASK),
          body: jobBody(TASK, "RIGHT"), fix: jobBody(TASK, "RIGHT-FIX-1"), reviews: TAB.reviews(TASK), report: report(TASK),
          ev: (TASK.events || []).filter(e => e.type === "job.dropped").map(e => evText(TASK, e)), next: next(TASK)})""")
        card = out["card"]
        self.assertEqual(card["st"]["text"], "⊘ dropped")
        self.assertIn("dropped", card["cls"])
        self.assertIsNone(card.get("v"))
        self.assertIn("Dropped on the owner's word: owner: wrong approach. It never merges.", card["tip"])
        self.assertEqual({r["id"]: (r["g"], r["tone"]) for r in card["rows"]},
                         {"REVIEW-RIGHT": ("⊘", "dropped"), "RIGHT-FIX-1": ("⊘", "dropped"), "REVIEW-RIGHT-2": ("⊘", "dropped")})
        # counts: dropped jobs leave the done numbers and are counted on their own
        self.assertIn("<b>0 / 2</b> jobs done", out["head"])
        self.assertIn("<b>4</b> dropped", out["head"])
        self.assertIn("0<span> / 2 · 4 dropped</span>", out["overview"])
        self.assertEqual(text(out["jobs"]).count("⊘dropped"), 4)
        self.assertIn("⊘dropped", text(out["reviews"]))
        self.assertNotIn("changes-required", text(out["reviews"]))
        body = text(out["body"])
        self.assertIn("Droppedowner: wrong approach · on the owner's word", body)
        self.assertIn("Dropped with it: REVIEW-RIGHT, RIGHT-FIX-1, REVIEW-RIGHT-2", body)
        self.assertIn("It never merges; its branch and files stay.", body)
        self.assertIn("Dropped with RIGHT, REVIEW-RIGHT, REVIEW-RIGHT-2", text(out["fix"]))
        self.assertIn("RIGHT with REVIEW-RIGHT, RIGHT-FIX-1, REVIEW-RIGHT-2 — owner: wrong approach", text(out["report"]))
        self.assertEqual(text(out["ev"][0]), "Dropped RIGHT with RIGHT-FIX-1, REVIEW-RIGHT, REVIEW-RIGHT-2 — owner: wrong approach")
        # the sidebar's bar: done of the jobs that are not dropped
        repo = self.served(sb, "/api/repo")
        side = page(repo, """IDX = DATA; S.task = DATA.tasks[0].id; renderSide(); document.querySelector("#side").innerHTML""")
        self.assertIn('<i class="k-dropped" style="flex:4">', side)
        self.assertIn("<b>0/2</b>", side)
        # dropped is final: once the rest is done, all jobs are done
        self.run_writer(sb, task, "drop", "LEFT")
        self.review_with(sb, task, "drop", "REVIEW-INTEGRATION", "integration", "pass", [])
        self.final(sb, task, "drop")
        out = page(self.task(sb, task), "({next: next(TASK), head: slimHead(TASK)})")
        self.assertEqual(out["next"][0], "All jobs done.")
        self.assertIn("<b>3 / 3</b> jobs done", out["head"])


class ParkStoryTests(ViewerCase, GuidanceCase):
    """[PARK-STORY]: the story on the parked job, on the round that parked the task, and in the Overview."""

    def test_a_job_parked_at_the_round_limit_shows_its_story(self):
        sb = self.sandbox()
        task = self.job_task(sb, "story", 2)
        self.review_round(sb, task, "story", "REVIEW-CORE", "CORE", [("Stale status after an update", "Clear the cache on write")])
        self.fix(sb, task, "story", "CORE-FIX-1", "CORE",
                 limits=["Do not touch the portal, because the portal is out of scope."], summary="clears on write")
        self.review_round(sb, task, "story", "REVIEW-CORE-2", "CORE", [("Stale status after a delete", "Clear it on delete too")])
        data = self.task(sb, task)
        self.assertEqual([s["target"] for s in data["status"]["park_stories"]], ["CORE"])
        story = data["status"]["park_stories"][0]
        out = page(data, """({body: jobBody(TASK, "CORE"), fix: jobBody(TASK, "CORE-FIX-1"), overview: TAB.overview(TASK)})""")
        body = text(out["body"])
        self.assertIn("Parked at the round limit", body)
        self.assertIn(story["opening"], body)
        self.assertIn("Rounds2 required changes · max-review-rounds 2", body)
        self.assertIn("ObjectiveCache the claim status for the portal.", body)
        self.assertIn("First resultCORE", body)
        self.assertIn("Round 1 · REVIEW-CORE", body)
        self.assertIn("Finding 1: Stale status after an update", body)
        self.assertIn("Suggested fix: Clear the cache on write", body)
        self.assertIn("Fix CORE-FIX-1 ●done clears on write", body)
        self.assertIn("Limit: Do not touch the portal, because the portal is out of scope.", body)
        self.assertIn("Round 2 · REVIEW-CORE-2", body)
        for choice in ("another round", "change the approach", "reduce the requirement", "accept"):
            self.assertIn(choice, body)
        for option in story["options"]:
            for command in option["commands"]:
                self.assertIn(command, body)
        self.assertIn(story["wait"], body)
        self.assertIn('data-act="copy"', out["body"])
        self.assertNotIn("Parked at the round limit", text(out["fix"]))
        overview = text(out["overview"])
        self.assertIn("Parked at the review-round limit: its story is below.", overview)
        self.assertIn("Parked at the round limit · CORE", overview)

    def test_the_parked_task_shows_its_story_on_the_round_that_parked_it(self):
        sb = self.sandbox()
        task = self.planned(sb, "taskpark", [("LEFT", "implementation", "", []), ("FINAL", "validation", "LEFT", ["--final"])],
                            settings=["review=integration", "max-review-rounds=1"])
        self.run_writer(sb, task, "taskpark", "LEFT")
        self.review_round(sb, task, "taskpark", "REVIEW-INTEGRATION", "integration", [("Two caches disagree", "Keep one cache")])
        data = self.task(sb, task)
        self.assertEqual([s["target"] for s in data["status"]["park_stories"]], ["integration"])
        out = page(data, """({body: jobBody(TASK, "REVIEW-INTEGRATION"), overview: TAB.overview(TASK)})""")
        body = text(out["body"])
        self.assertIn("Parkedthe task: REVIEW-INTEGRATION still requires changes after a fix round.", body)
        self.assertIn("Tasktaskpark", body)
        self.assertIn("Finding 1: Two caches disagree", body)
        self.assertIn("close anyway", body)
        self.assertIn("Parked at the round limit · the task", text(out["overview"]))


class ReadmeTests(unittest.TestCase):
    def test_the_readme_names_the_new_server_data_and_the_section(self):
        readme = (SKILL_DIR / "assets" / "viewer" / "README.md").read_text()
        for name in ("stakes_data", "Project settings", "POST /api/stakes", "routing_exceptions", "park_stories",
                     "bypass", "launch", "dropped"):
            self.assertIn(name, readme)


if __name__ == "__main__":
    unittest.main()
