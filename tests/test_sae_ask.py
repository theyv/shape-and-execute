"""sae ask: open asks, how a `--by human` log closes them, the ask-signal setting and the
reminder line of sae next; the owner-wait data for the viewer; the setting in the viewer.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [ASK-COMMAND], [ASK-SETTING], [ASK-REMINDER], [DECISION-SAE-ASK]; "Waiting for the owner".
"""

from __future__ import annotations

import shutil
import sys
import unittest

from saetest import SCRIPTS, SKILL_DIR, Sandbox, SaeTestCase, dispatch_workspace
from test_viewer_server import ViewerServerCase, request, run_node

ASK_LINE = "Before you ask the owner anything: sae ask"

# app.js, task-views.js and settings.js in node: the header card and the Task level of the
# Settings tab for one task's data (argv: the three files, then the data file).
SETTINGS_JS = r"""
const vm = require("vm"), fs = require("fs");
const el = () => new Proxy({innerHTML: "", hidden: true, dataset: {}, style: {},
  classList: {toggle() {}, contains() { return false }, add() {}, remove() {}}, addEventListener() {}, querySelectorAll() { return [] }},
  {get: (t, k) => k in t ? t[k] : () => null});
const ctx = {console, setTimeout: () => 0, clearTimeout() {}, setInterval() {}, addEventListener() {}, history: {replaceState() {}},
  location: {hash: ""}, localStorage: {getItem() { return null }, setItem() {}},
  document: {hidden: false, title: "", documentElement: {dataset: {}}, body: el(), activeElement: null,
    querySelector: el, querySelectorAll: () => [], addEventListener() {}, createElement: el}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 5)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
ctx.TASK = JSON.parse(fs.readFileSync(process.argv[5], "utf8"));
console.log(JSON.stringify(vm.runInContext(`readHash(); S.repo = "R"; S.task = TASK.state.task.id; TASKS[S.task] = TASK;
  ({card: headerCard(TASK), tab: sxDefaults("task")})`, ctx)));
"""


class AskCase(SaeTestCase):
    def started(self, sb: Sandbox, slug: str, jobs=("A", "B"), mode: str | None = None) -> str:
        task = sb.new_task(slug, slug)
        if mode:
            sb.sae("set", slug, f"interaction={mode}")
        for job in jobs:
            sb.sae("job", "add", slug, job, "--kind", "implementation")
            sb.job_file(task, job, objective=f"Build the {job.lower()} part.")
        sb.approve_plan(slug)
        sb.sae("start", slug)
        return task

    def open_numbers(self, sb: Sandbox, slug: str) -> list[tuple]:
        return [(a["n"], a["job"]) for a in sb.json("status", slug)["asks"]]

    def owner_wait(self, sb: Sandbox, task: str) -> dict:
        sys.path.insert(0, str(SCRIPTS))
        try:
            from sae_lib.asks import owner_wait
            from sae_lib.tasks import Task
        finally:
            sys.path.remove(str(SCRIPTS))
        loaded = Task(sb.task_dir(task).parents[1], task, sb.task_dir(task))
        loaded.load(read_only=True)
        return owner_wait(loaded)


class AskCommandTests(AskCase):
    def test_a_human_log_closes_the_asks_it_answers(self):
        """[ASK-COMMAND]: a `--by human --job A` log closes only A's ask; a task-level ask closes
        with a `--by human` log without --job; --answered closes the rest."""
        sb = self.sandbox()
        self.started(sb, "asks")
        out = sb.sae("ask", "asks", "Keep the old format?", "--job", "A").stdout
        self.assertIn("Ask 1 is open", out)
        self.assertIn("--by human --job A", out)
        sb.sae("ask", "asks", "Which colour for B?", "--job", "B")
        sb.sae("ask", "asks", "Release today?")
        self.assertEqual(self.open_numbers(sb, "asks"), [(1, "A"), (2, "B"), (3, None)])
        status = sb.sae("status", "asks").stdout
        self.assertIn("Open asks (waiting for the owner):\n  1. A: Keep the old format?\n  2. B: Which colour for B?\n"
                      "  3. Release today?", status)
        agent = sb.json("log", "asks", "decision", "Keep it", "--job", "A", "--by", "agent")
        self.assertEqual(agent["closed_asks"], [])  # an agent's decision answers nothing
        human = sb.sae("log", "asks", "decision", "Keep it", "--job", "A", "--by", "human").stdout
        self.assertEqual(human.strip(), "Logged decision. Closed ask 1.")
        self.assertEqual(self.open_numbers(sb, "asks"), [(2, "B"), (3, None)])
        self.assertEqual(sb.json("log", "asks", "decision", "Ship it", "--by", "human")["closed_asks"], [3])
        self.assertEqual(self.open_numbers(sb, "asks"), [(2, "B")])
        self.assertEqual(sb.sae("ask", "asks", "--answered").stdout.strip(), "Closed ask 2.")
        self.assertEqual(self.open_numbers(sb, "asks"), [])
        self.assertNotIn("Open asks", sb.sae("status", "asks").stdout)
        self.assertEqual(sb.sae("ask", "asks", "--answered").stdout.strip(), "No open ask.")
        events = [e for e in sb.events(sb.json("status", "asks")["task"]) if e["type"].startswith("ask.")]
        self.assertEqual([(e["type"], e.get("asks") or e.get("n")) for e in events],
                         [("ask.opened", 1), ("ask.opened", 2), ("ask.opened", 3), ("ask.closed", [1]),
                          ("ask.closed", [3]), ("ask.closed", [2])])

    def test_answered_closes_every_open_ask_and_with_job_only_its_own(self):
        """[ASK-COMMAND]: --answered closes the task-level asks too; --answered --job A only A's."""
        sb = self.sandbox()
        self.started(sb, "answered")
        sb.sae("ask", "answered", "One?", "--job", "A")
        sb.sae("ask", "answered", "Two?")
        sb.sae("ask", "answered", "Three?", "--job", "B")
        self.assertEqual(sb.json("ask", "answered", "--answered", "--job", "A")["closed"], [1])
        self.assertEqual(sb.json("ask", "answered", "--answered")["closed"], [2, 3])

    def test_status_calls_asks_waiting_only_in_executing(self):
        """"Waiting for the owner": an open ask outside executing is listed, not called waiting."""
        sb = self.sandbox()
        sb.new_task("Shape", "shape")
        sb.sae("ask", "shape", "Which scope?")
        status = sb.sae("status", "shape").stdout
        self.assertIn("Open asks:\n  1. Which scope?", status)
        self.assertNotIn("waiting for the owner", status)

    def test_unknown_job_and_missing_question_fail(self):
        """[ASK-COMMAND]: --job with an unknown job ID fails with exit 1; so does no question."""
        sb = self.sandbox()
        task = self.started(sb, "bad")
        self.assertIn("No job NOPE", sb.sae("ask", "bad", "Why?", "--job", "NOPE", code=1).stderr)
        sb.sae("ask", "bad", code=1)
        sb.sae("ask", "bad", "  ", code=1)
        sb.sae("ask", "bad", "Why?", "--answered", code=1)
        self.assertFalse([e for e in sb.events(task) if e["type"].startswith("ask.")])


class OwnerWaitTests(AskCase):
    def test_owner_wait_lists_asks_parked_jobs_and_holds_in_execution(self):
        """"Waiting for the owner": open asks, a parked job and an active hold, in executing only."""
        sb = self.sandbox()
        planning = sb.new_task("Plan", "plan")
        sb.sae("ask", "plan", "Shape question?")
        self.assertEqual(self.owner_wait(sb, planning)["waiting"], [])  # not in shaping
        self.assertEqual([a["question"] for a in self.owner_wait(sb, planning)["asks"]], ["Shape question?"])
        task = self.started(sb, "wait")
        self.assertEqual(self.owner_wait(sb, task), {"asks": [], "waiting": []})
        sb.sae("ask", "wait", "Keep A?", "--job", "A")
        sb.sae("hold", "wait", "A", "--reason", "look first")
        sb.sae("dispatch", "wait", "B")
        sb.result(task, "jobs/B.result.md", status="parked", summary="needs a decision", validation="not-run",
                  changes="none")
        sb.sae("collect", "wait", "B")
        data = self.owner_wait(sb, task)
        self.assertEqual(data["asks"][0]["job"], "A")
        self.assertEqual([(r["kind"], r["job"]) for r in data["waiting"]], [("ask", "A"), ("parked", "B")])
        self.assertEqual(data["waiting"][0]["text"], "Keep A?")
        self.assertIn("needs a decision", data["waiting"][1]["text"])

    def test_active_hold_waits_for_the_owner(self):
        sb = self.sandbox()
        task = self.started(sb, "held")
        sb.sae("hold", "held", "A", "--reason", "look first")
        ws = dispatch_workspace(sb, task, "A")
        sb.work(ws, "a.txt", "A\n", "A: work")
        sb.result(task, "jobs/A.result.md", status="done", summary="ok", validation="pass", changes="made")
        sb.sae("collect", "held", "A")
        self.assertEqual(self.owner_wait(sb, task)["waiting"],
                         [{"kind": "hold", "job": "A", "text": "Hold after A: look first"}])


class AskSignalTests(AskCase):
    def reminded(self, sb: Sandbox, slug: str) -> bool:
        text = sb.sae("next", slug).stdout
        reminder = sb.json("next", slug)["reminder"]
        self.assertEqual(ASK_LINE in text, any(ASK_LINE in line for line in reminder))
        return ASK_LINE in text

    def test_unset_signal_follows_the_mode(self):
        """[ASK-SETTING], [ASK-REMINDER]: unset, the reminder shows in full-auto, auto and
        critical-only, not in collaborative and interactive, and follows a mode change."""
        sb = self.sandbox()
        self.started(sb, "modes", jobs=("A",), mode="full-auto")
        for mode, expected in (("full-auto", True), ("auto", True), ("critical-only", True),
                               ("collaborative", False), ("interactive", False), ("auto", True)):
            sb.sae("set", "modes", f"interaction={mode}")
            self.assertEqual(self.reminded(sb, "modes"), expected, mode)
            self.assertEqual(sb.json("status", "modes")["ask_signal"]["on"], expected, mode)
        line = next(l for l in sb.sae("next", "modes").stdout.splitlines() if ASK_LINE in l)
        task = sb.json("status", "modes")["task"]
        self.assertEqual(line, f'{ASK_LINE} {task} "<question>" [--job <ID>]. After the answer: sae log {task} '
                               f'decision "<answer>" --by human [--job <ID>], or sae ask {task} --answered.')

    def test_set_on_off_unset(self):
        """[ASK-SETTING]: on and off override the mode; unset follows it again; bad values fail."""
        sb = self.sandbox()
        task = self.started(sb, "explicit", jobs=("A",), mode="collaborative")
        self.assertFalse(self.reminded(sb, "explicit"))
        card = sb.sae("set", "explicit", "ask-signal=on").stdout
        self.assertIn("  ask signal       on", card)
        self.assertEqual(sb.json("status", "explicit")["settings"]["ask_signal"], "on")
        self.assertTrue(self.reminded(sb, "explicit"))
        sb.sae("set", "explicit", "interaction=full-auto", "ask-signal=off")
        self.assertFalse(self.reminded(sb, "explicit"))
        self.assertEqual(sb.json("status", "explicit")["ask_signal"], {"on": False, "set": "off", "text": "off"})
        unset = sb.sae("set", "explicit", "ask-signal=unset").stdout
        self.assertNotIn("ask signal", unset)
        self.assertNotIn("ask_signal", sb.json("status", "explicit")["settings"])
        self.assertTrue(self.reminded(sb, "explicit"))
        self.assertEqual(sb.json("status", "explicit")["ask_signal"]["text"], "on (mode default)")
        sb.sae("set", "explicit", "ask-signal=maybe", code=1)
        sb.sae("project", "set", "ask-signal=on", code=1)  # a task setting only
        changes = [e["changes"] for e in sb.events(task) if e["type"] == "settings.changed"]
        self.assertIn({"ask_signal": [None, "on"]}, changes)
        self.assertIn({"ask_signal": ["off", None]}, changes)

    def test_reminder_only_in_executing_and_nowhere_else(self):
        """[ASK-REMINDER]: not in shaping or planning; the dispatch prompt never mentions sae ask."""
        sb = self.sandbox()
        sb.new_task("Shape", "shape")
        sb.sae("set", "shape", "interaction=full-auto")
        self.assertFalse(self.reminded(sb, "shape"))
        sb.approve_spec("shape")
        self.assertFalse(self.reminded(sb, "shape"))
        task = self.started(sb, "prompt", jobs=("A",), mode="full-auto")
        self.assertTrue(self.reminded(sb, "prompt"))
        self.assertNotIn("sae ask", sb.json("dispatch", "prompt", "A")["prompt"])
        self.assertNotIn("sae ask", sb.sae("status", "prompt").stdout)
        self.assertTrue(task)

    def test_start_and_resume_never_show_the_reminder(self):
        """[ASK-REMINDER]: the sae ask line is in sae next only, not in a first or resumed sae start."""
        sb = self.sandbox()
        task = sb.new_task("Start", "start")
        sb.sae("set", "start", "interaction=full-auto")
        sb.sae("job", "add", "start", "A", "--kind", "implementation")
        sb.job_file(task, "A", objective="Build the a part.")
        sb.approve_plan("start")
        self.assertNotIn(ASK_LINE, sb.sae("start", "start").stdout)
        self.assertNotIn(ASK_LINE, sb.sae("start", "start").stdout)  # resumed: phase executing
        self.assertTrue(self.reminded(sb, "start"))

    def test_next_step_card_lists_the_signal_and_its_change(self):
        """[ASK-SETTING]: the next-step card's settings list has the effective ask signal; a mode
        change that flips it shows as a change since the last card."""
        sb = self.sandbox()
        task = self.started(sb, "card", jobs=("A",), mode="auto")
        self.assertEqual(sb.state(task)["task"]["last_card"]["settings"]["ask_signal"], "on (mode default)")
        sb.sae("set", "card", "interaction=collaborative")
        sys.path.insert(0, str(SCRIPTS))
        try:
            from sae_lib.control import change_lines, last_snapshot, settings_snapshot
            from sae_lib.tasks import Task
        finally:
            sys.path.remove(str(SCRIPTS))
        loaded = Task(sb.task_dir(task).parents[1], task, sb.task_dir(task))
        loaded.load(read_only=True)
        snap = settings_snapshot(loaded, None)
        changes = change_lines(last_snapshot(loaded.info["last_card"]["settings"], snap), snap)
        self.assertIn("ask_signal: on (mode default) → off (mode default)", changes)

    def test_old_recorded_card_without_the_signal_is_no_change(self):
        """A card recorded by an older sae has no ask_signal: that is no change."""
        sys.path.insert(0, str(SCRIPTS))
        try:
            from sae_lib.control import change_lines, last_snapshot
        finally:
            sys.path.remove(str(SCRIPTS))
        new = {"interaction": "auto", "ask_signal": "on (mode default)"}
        self.assertEqual(change_lines(last_snapshot({"interaction": "auto"}, new), new), [])


class AskViewerTests(ViewerServerCase, AskCase):
    @unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
    def test_header_card_and_settings_tab_show_and_change_the_signal(self):
        """[ASK-SETTING]: the settings card and the Settings tab show the effective signal; a save
        from the viewer runs sae set ask-signal=…"""
        sb = self.sandbox()
        task = self.started(sb, "viewer", jobs=("A",), mode="collaborative")
        view = self.view(sb, "viewer")
        _, data, _ = request(view["port"], "GET", f"/api/task?repo={view['repo']}&task={task}")
        self.assertEqual(data["status"]["ask_signal"], {"on": False, "set": None, "text": "off (mode default)"})
        out = run_node(SETTINGS_JS, "app.js", "task-views.js", "settings.js", data=data)
        self.assertIn('data-k="ask-signal"', out["card"])
        self.assertIn('<option value="unset" selected>mode default (off)</option>', out["card"])
        self.assertIn("Ask signal", out["tab"])
        self.assertIn('data-k="task|ask-signal" data-v="unset"', out["tab"])
        self.assertIn('aria-checked="true" data-act="sxv" data-k="task|ask-signal" data-v="unset"', out["tab"])
        self.assertIn("now off (interaction mode)", out["tab"])
        status, answer, _ = self.post(view["port"], "set", {"repo": view["repo"], "task": task,
                                                            "pairs": ["ask-signal=on"]}, self.token(view["port"]))
        self.assertEqual((status, answer["ok"]), (200, True), answer)
        _, data, _ = request(view["port"], "GET", f"/api/task?repo={view['repo']}&task={task}")
        out = run_node(SETTINGS_JS, "app.js", "task-views.js", "settings.js", data=data)
        self.assertIn('<option value="on" selected>on</option>', out["card"])
        self.assertIn('aria-checked="true" data-act="sxv" data-k="task|ask-signal" data-v="on"', out["tab"])
        self.assertIn("set here", out["tab"])


class SkillDocsTests(unittest.TestCase):
    def test_references_never_mention_sae_ask(self):
        """[ASK-REMINDER]: only sae next tells the orchestrator; SKILL.md and references/ do not."""
        files = [SKILL_DIR / "SKILL.md", *sorted((SKILL_DIR / "references").rglob("*.md"))]
        self.assertEqual([str(f) for f in files if "sae ask" in f.read_text()], [])


if __name__ == "__main__":
    unittest.main()
