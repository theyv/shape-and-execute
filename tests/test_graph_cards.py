"""The Plan graph as stack cards: Shape and Plan cards, job cards with review and fix rows, one
Integration card, the jobs placeholder and Finish; the server's `steps` and `finish`; hover links,
faded cards, the added fill, tooltips and pinch zoom.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [GRAPH-EDGE-HOVER], [GRAPH-NOT-YET], [GRAPH-JOB-CARD], [GRAPH-INTEGRATION-CARD],
[GRAPH-PHASE-CARDS], [GRAPH-PLACEHOLDER-FINISH], [GRAPH-ADDED-FILL], [GRAPH-TOOLTIPS], [GRAPH-ZOOM],
[WAIT-FRAMES] (the red frame), [EDGE-OLD-TASKS], [EDGE-ACCEPTED-REVIEW].
"""

from __future__ import annotations

import math
import shutil
import sys
import unittest
from pathlib import Path

from saetest import SCRIPTS, SKILL_DIR
from test_reviews import ReviewFlowCase
from test_task_worktree import plan
from test_viewer_server import ViewerServerCase, request, run_node

sys.path.insert(0, str(SCRIPTS))

DONE = SKILL_DIR.parents[1] / ".tasks" / "done"
FINDINGS_DOCS = "2026-10-12-1846--sae-findings-docs"
DOGFOOD = "2026-10-08-1733--sae-dogfood-fixes"
NODE = shutil.which("node")

# app.js and task-views.js in node: the card model of graph(), its edges, and the Plan tab's HTML
CARDS_JS = r"""
const vm = require("vm"), fs = require("fs");
const el = () => new Proxy({innerHTML: "", hidden: true, dataset: {}, style: {}, classList: {toggle() {}, contains() { return false }}},
  {get: (t, k) => k in t ? t[k] : () => null});
const ctx = {console, setTimeout: () => 0, clearTimeout() {}, setInterval() {}, addEventListener() {}, history: {replaceState() {}},
  location: {hash: ""}, localStorage: {getItem() { return null }, setItem() {}},
  document: {hidden: false, documentElement: {dataset: {}}, body: el(), querySelector: el, querySelectorAll: () => [],
    addEventListener() {}, createElement: el}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 4)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
ctx.TASK = JSON.parse(fs.readFileSync(process.argv[4], "utf8"));
console.log(JSON.stringify(vm.runInContext(`readHash(); IDX = {sae: "sae", tasks: []}; S.task = TASK.state.task.id;
  var g = graph(TASK), plan = TAB.plan(TASK);
  ({cards: g.cards.map(c => ({id: c.id, st: c.st.text, v: c.v ? c.v[1] : null, tk: c.tk || "", cls: c.cls, l3: c.l3 || "", tip: c.tip,
      rows: c.rows.map(r => ({id: r.id, label: r.label, g: r.g, tone: r.tone, planned: !!r.planned, tip: r.tip}))})),
    edges: g.edges.map(e => e.slice(0, 3)), svg: g.svg, plan: plan,
    links: g.cards.map(c => [c.id, gvLinks(GE, c.id)])})`, ctx)));
"""

# task-views.js in node: the zoom factor of a wheel event, before ([GRAPH-ZOOM]: a fixed .0015) and now
ZOOM_JS = r"""
const vm = require("vm"), fs = require("fs");
const ctx = {console, document: {addEventListener() {}, querySelector() { return null }}, addEventListener() {}, setInterval() {},
  localStorage: {getItem() { return null }, setItem() {}}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 4)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
console.log(JSON.stringify(vm.runInContext(`({
  pinch: gvRate({ctrlKey: true, metaKey: false, deltaMode: 0, deltaY: -3}),
  cmd: gvRate({ctrlKey: false, metaKey: true, deltaMode: 0, deltaY: -40}),
  mouse: gvRate({ctrlKey: true, metaKey: false, deltaMode: 0, deltaY: -100}),
  lines: gvRate({ctrlKey: true, metaKey: false, deltaMode: 1, deltaY: -3})})`, ctx)));
"""


def card(out: dict, card_id: str) -> dict:
    found = [c for c in out["cards"] if c["id"] == card_id]
    if not found:
        raise AssertionError(f"no card {card_id}: {[c['id'] for c in out['cards']]}")
    return found[0]


def rows(c: dict) -> list[tuple[str, str, str]]:
    return [(r["label"], r["g"], r["tone"]) for r in c["rows"]]


@unittest.skipUnless(NODE, "node runs the viewer scripts")
class GraphCardsCase(ViewerServerCase, ReviewFlowCase):
    def data(self, sb, task: str) -> dict:
        view = getattr(self, "_view", None) or self.view(sb, task)
        self._view = view
        code, data, _ = request(view["port"], "GET", f"/api/task?repo={view['repo']}&task={task}")
        self.assertEqual(code, 200, data)
        return data

    def cards(self, sb, task: str) -> dict:
        return run_node(CARDS_JS, "app.js", "task-views.js", data=self.data(sb, task))

    def copy_done(self, sb, *names: str) -> list[str]:
        """Copies of finished tasks of this repository into the sandbox's .tasks/done/."""
        found = [n for n in names if (DONE / n).is_dir()] if names else sorted(p.name for p in DONE.iterdir() if p.is_dir())
        if not found:
            self.skipTest("no finished task records in .tasks/done/")
        for name in found:
            shutil.copytree(DONE / name, sb.repo / ".tasks" / "done" / name)
        return found


class ServerDataTests(GraphCardsCase):
    def test_steps_and_finish_readiness_come_from_the_cli_code_and_write_nothing(self):
        """[GRAPH-PHASE-CARDS], [GRAPH-PLACEHOLDER-FINISH]: steps of the process map; Finish ready only
        when `sae finish` would pass its gates, blocked with its reason once every job is done."""
        from sae_lib.control import map_steps
        from sae_lib.tasks import Task
        sb = self.sandbox()
        shaping = sb.new_task("Shaping", "shaping")
        data = self.data(sb, shaping)
        loaded = Task(sb.repo, shaping)
        loaded.load()
        self.assertEqual(data["steps"], map_steps(loaded))
        self.assertEqual(data["finish"], {"state": "waiting", "reason": None})
        # a job review says changes-required: every job is done, `sae finish` refuses
        task = self.planned(sb, "blocked", [("CORE", "implementation", "", ["--review"])], settings=["review=selected-jobs"])
        self.run_writer(sb, task, "blocked", "CORE")
        self.review(sb, task, "blocked", "REVIEW-CORE", "CORE", "changes-required")
        state = (sb.task_dir(task) / "state.json").read_bytes()
        finish = self.data(sb, task)["finish"]
        self.assertEqual((sb.task_dir(task) / "state.json").read_bytes(), state, "the server's read writes nothing")
        self.assertEqual(finish["state"], "blocked")
        refused = sb.sae("finish", "blocked", code=3).stderr
        self.assertIn(finish["reason"].splitlines()[0], refused)
        # a pass: CORE merges, the gates pass; after `sae finish` the card says done
        ready = self.planned(sb, "ready", [("CORE", "implementation", "", ["--review"])], settings=["review=selected-jobs"])
        self.run_writer(sb, ready, "ready", "CORE")
        self.review(sb, ready, "ready", "REVIEW-CORE", "CORE", "pass")
        self.assertEqual(self.data(sb, ready)["finish"], {"state": "ready", "reason": None})
        sb.sae("finish", "ready")
        self.assertEqual(self.data(sb, ready)["finish"], {"state": "done", "reason": None})


class FinishedTaskTests(GraphCardsCase):
    def test_findings_docs_job_card_and_integration_card(self):
        """[GRAPH-JOB-CARD], [GRAPH-INTEGRATION-CARD], [GRAPH-PHASE-CARDS], on a copy of sae-findings-docs."""
        sb = self.sandbox()
        self.copy_done(sb, FINDINGS_DOCS)
        out = self.cards(sb, FINDINGS_DOCS)
        ids = [c["id"] for c in out["cards"]]
        for row_job in ("REVIEW-FINDINGS-RESOLVE", "FINDINGS-RESOLVE-FIX-1", "REVIEW-FINDINGS-RESOLVE-2",
                        "REVIEW-INTEGRATION", "INTEGRATION-FIX-1", "REVIEW-INTEGRATION-2", "REVIEW-SPEC", "REVIEW-PLAN", "PLAN"):
            self.assertNotIn(row_job, ids, "a review, a fix and the planner are rows or phase cards, not cards")
        fr = card(out, "FINDINGS-RESOLVE")
        self.assertEqual(rows(fr), [("Review 1", "✕", "mut"), ("Fix", "●", "done"), ("Review 2", "✓", "pass")])
        self.assertEqual(fr["v"], "✓ pass · 2nd round")
        self.assertIn("REVIEW-FINDINGS-RESOLVE · changes required, fixed", fr["rows"][0]["tip"])
        it = card(out, "@integration")
        self.assertEqual(rows(it), [("Review 1", "✕", "mut"), ("Fix", "●", "done"), ("Review 2", "✓", "pass")])
        self.assertEqual(it["v"], "✓ pass · 2nd round")
        self.assertTrue(it["tip"].startswith("Integration — "))
        # the jobs that need the reviewed jobs get their edges from the cards; the planner's first jobs from Plan
        edges = {(a, b) for a, b, _ in out["edges"]}
        self.assertIn(("FINDINGS-RESOLVE", "FINDINGS-CLOSE"), edges)
        self.assertIn(("@integration", "FINAL-VALIDATION"), edges)
        self.assertIn(("@shape", "@plan"), edges)
        self.assertIn(("@plan", "SKILLS-MOVE"), edges)
        self.assertIn(("FINAL-VALIDATION", "@finish"), edges)
        for phase in ("@shape", "@plan"):
            self.assertEqual(card(out, phase)["st"], "✓ approved")
        self.assertEqual(card(out, "@plan")["tk"], "293k tk · 26m")  # the planner and the plan review
        self.assertEqual(card(out, "@finish")["st"], "✓ done")
        self.assertIn('data-card="@finish"', out["svg"])
        self.assertNotIn("Shaping and planning", out["plan"], "the phase cards replace the chips")

    def test_every_finished_task_renders_and_hover_links_only_its_own_edges(self):
        """[EDGE-OLD-TASKS], [GRAPH-EDGE-HOVER]: every task in .tasks/done/ draws; on the 50 jobs of
        sae-dogfood-fixes each card's links are its own edges and the cards at their ends."""
        sb = self.sandbox()
        names = self.copy_done(sb)
        for name in names:
            with self.subTest(task=name):
                out = self.cards(sb, name)
                self.assertNotIn("undefined", out["svg"])
                self.assertNotIn("NaN", out["svg"])
                self.assertEqual(card(out, "@finish")["st"], "✓ done")
                if name == DOGFOOD:
                    self.assertTrue(card(out, "@shape")["tk"] and card(out, "@plan")["tk"])
                    for card_id, ln in out["links"]:
                        own = [i for i, e in enumerate(out["edges"]) if card_id in e[:2]]
                        self.assertEqual(ln["edges"], own)
                        ends = {card_id} | {x for e in out["edges"] if card_id in e[:2] for x in e[:2]}
                        self.assertEqual(set(ln["cards"]), ends)


class LiveStateTests(GraphCardsCase):
    def test_a_running_job_with_a_planned_review_then_a_running_fix_then_a_parked_fix(self):
        """[GRAPH-JOB-CARD], [GRAPH-NOT-YET], [WAIT-FRAMES]: one planned row with a clickable model;
        while the fix runs "◐ fixing", Review 1 red ✕, Fix ◐, Review 2 ◌; a parked row: the red frame."""
        sb = self.sandbox()
        task = self.planned(sb, "flow", [("CORE", "implementation", "", ["--review"]), ("SIDE", "implementation", "CORE", [])],
                            settings=["review=selected-jobs"])
        ws = Path(sb.json("dispatch", "flow", "CORE")["workspace"])
        out = self.cards(sb, task)
        core = card(out, "CORE")
        self.assertEqual([(r["label"], r["g"], r["planned"]) for r in core["rows"]], [("Review", "◌", True)])
        self.assertRegex(out["svg"], r'class="rw t-planned planned"[^>]*>.*?data-act="ovr" data-id="REVIEW-CORE"')
        self.assertIn("nyet", card(out, "SIDE")["cls"])
        self.assertIn(["CORE", "SIDE", ""], out["edges"])
        self.assertRegex(out["svg"], r'class="e  ny" data-i="\d+"')  # the edge into the faded card
        self.assertNotIn("nyet", core["cls"])
        # round 1 requires changes; the fix runs
        sb.work(ws, "core.txt", "core\n", "CORE: work")
        sb.result(task, "jobs/CORE.result.md", status="done", summary="core", validation="pass", changes="made")
        sb.sae("collect", "flow", "CORE")
        self.review(sb, task, "flow", "REVIEW-CORE", "CORE", "changes-required")
        sb.sae("job", "add", "flow", "CORE-FIX-1", "--kind", "implementation", "--fix-of", "CORE", "--reason", "finding 1")
        sb.job_file(task, "CORE-FIX-1")
        fix_ws = Path(sb.json("dispatch", "flow", "CORE-FIX-1")["workspace"])
        out = self.cards(sb, task)
        core = card(out, "CORE")
        self.assertEqual(core["st"], "◐ fixing")
        self.assertEqual(rows(core), [("Review 1", "✕", "fail"), ("Fix", "◐", "running"), ("Review 2", "◌", "planned")])
        self.assertNotIn("CORE-FIX-1", [c["id"] for c in out["cards"]])
        self.assertNotIn("added", core["cls"], "a fix row is no added job")
        # the fix parks: the card's badge and its red frame
        sb.work(fix_ws, "fix.txt", "fix\n", "CORE-FIX-1: work")
        sb.result(task, "jobs/CORE-FIX-1.result.md", status="parked", summary="needs a decision", validation="pass", changes="made")
        sb.sae("collect", "flow", "CORE-FIX-1")
        core = card(self.cards(sb, task), "CORE")
        self.assertEqual(core["st"], "‖ parked")
        self.assertIn("wait", core["cls"])
        self.assertEqual(core["rows"][1]["g"], "‖")

    def test_moment_zero_a_task_in_shaping_with_its_spec_review_running(self):
        """[GRAPH-PHASE-CARDS], [GRAPH-PLACEHOLDER-FINISH], prototype moment 0."""
        sb = self.sandbox(points=["spec", "plan", "selected-jobs", "integration"])
        task = sb.new_task("Moment zero", "zero")
        sb.sae("job", "add", "zero", "RESEARCH-X", "--kind", "research")
        sb.json("dispatch", "zero", "RESEARCH-X")
        sb.result(task, "research/RESEARCH-X.md", status="done", summary="facts")
        sb.sae("collect", "zero", "RESEARCH-X", "--tokens", "38000", "--duration-s", "420")
        (sb.task_dir(task) / "specs.md").write_text("# Spec\n\n## Requirements\n\n### [ZERO] It works\nAcceptance:\n- [ ] yes\n")
        sb.json("dispatch", "zero", "REVIEW-SPEC")
        out = self.cards(sb, task)
        shape, plan_card = card(out, "@shape"), card(out, "@plan")
        self.assertEqual(shape["st"], "◐ running")
        self.assertEqual([(r["label"], r["g"]) for r in shape["rows"]], [("Research", "●"), ("Review", "◐")])
        self.assertEqual(shape["tk"], "38k tk · 7m")
        self.assertEqual(shape["l3"], "subagents only")
        self.assertIn("Steps: intake ✓", shape["tip"])
        self.assertEqual(plan_card["st"], "○ waiting")
        self.assertIn("nyet", plan_card["cls"])
        self.assertEqual([(r["label"], r["g"]) for r in plan_card["rows"]], [("Review", "◌")])
        self.assertIn("nyet", card(out, "@jobs")["cls"])
        self.assertEqual(card(out, "@finish")["st"], "○ waiting")
        self.assertEqual([e[:2] for e in out["edges"]], [["@shape", "@plan"], ["@plan", "@jobs"], ["@jobs", "@finish"]])
        self.assertNotIn("@integration", [c["id"] for c in out["cards"]])

    def test_integration_card_only_with_its_review_point_and_a_ready_job_is_not_faded(self):
        """[GRAPH-INTEGRATION-CARD], [GRAPH-NOT-YET]."""
        sb = self.sandbox()
        off = plan(sb, "off", [("ONE", ""), ("TWO", "ONE")])
        sb.sae("set", "off", "review=spec")
        sb.sae("start", "off")
        out = self.cards(sb, off)
        self.assertNotIn("@integration", [c["id"] for c in out["cards"]])
        self.assertIn("nyet", card(out, "TWO")["cls"])
        self.run_writer(sb, off, "off", "ONE")
        self.assertNotIn("nyet", card(self.cards(sb, off), "TWO")["cls"])
        on = self.integration_task(sb, "on")  # REVIEW-INTEGRATION exists, not run yet
        it = card(self.cards(sb, on), "@integration")
        self.assertEqual(rows(it), [("Review", "▷", "ready")])

    def test_added_job_fill_tooltip_with_title_objective_and_result(self):
        """[GRAPH-ADDED-FILL], [GRAPH-TOOLTIPS]."""
        sb = self.sandbox()
        task = plan(sb, "added", [("ONE", "")])
        sb.sae("start", "added")
        sb.sae("job", "add", "added", "LATE", "--kind", "implementation", "--reason", "the owner asked for it")
        sb.job_file(task, "LATE", objective="Add the late part.")
        self.run_writer(sb, task, "added", "ONE")
        out = self.cards(sb, task)
        late, one = card(out, "LATE"), card(out, "ONE")
        self.assertIn("added", late["cls"])
        self.assertIn("Added after plan approval: the owner asked for it", late["tip"])
        self.assertIn("Objective: Add the late part.", late["tip"])
        self.assertIn("test job", late["tip"])  # the title of its job file
        self.assertNotIn("added", one["cls"])
        self.assertIn("Result: ONE", one["tip"])
        self.assertIn('class="ks hatch"', out["plan"])

    def test_a_merge_despite_changes_required_is_accepted(self):
        """[EDGE-ACCEPTED-REVIEW]."""
        sb = self.sandbox()
        task = self.planned(sb, "accept", [("CORE", "implementation", "", ["--review"])], settings=["review=selected-jobs"])
        self.run_writer(sb, task, "accept", "CORE")
        self.review(sb, task, "accept", "REVIEW-CORE", "CORE", "changes-required")
        sb.sae("merge", "accept", "CORE", "--accept-review", "remaining finding is cosmetic")
        core = card(self.cards(sb, task), "CORE")
        self.assertEqual(core["v"], "◆ accepted")
        self.assertEqual(rows(core), [("Review", "✕", "park")])
        self.assertIn("remaining finding is cosmetic", core["rows"][0]["tip"])


@unittest.skipUnless(NODE, "node runs the viewer scripts")
class CanvasTests(unittest.TestCase):
    def test_a_pinch_zooms_at_least_twice_as_far_as_before_and_the_fit_button_is_an_icon(self):
        """[GRAPH-ZOOM]: Chromium sends a pinch as Ctrl + wheel with deltaY ≈ -100·ln(scale); a pinch
        that spreads the fingers to twice their distance (23 events of -3) zoomed 1.11× before."""
        out = run_node(ZOOM_JS, "app.js", "task-views.js")
        before, now = math.exp(69 * 0.0015), math.exp(69 * out["pinch"])
        self.assertGreaterEqual(math.log(now), 2 * math.log(before))
        self.assertAlmostEqual(now, 2.0, delta=0.05)
        self.assertEqual(out["cmd"], 0.0015)  # Cmd + scroll keeps its speed
        self.assertEqual(out["mouse"], 0.0015)  # a mouse wheel notch with Ctrl is no pinch
        self.assertGreater(out["lines"], out["mouse"])
        js = (SKILL_DIR / "assets" / "viewer" / "task-views.js").read_text()
        self.assertIn('data-gz="fit" aria-label="Fit the whole graph"', js)
        self.assertNotIn('">fit</button>', js)

    def test_the_css_highlights_dims_fades_and_stops_the_pulse_for_reduced_motion(self):
        """[GRAPH-EDGE-HOVER], [GRAPH-NOT-YET], [GRAPH-JOB-CARD]: the styles the page's classes need."""
        css = (SKILL_DIR / "assets" / "viewer" / "task-views.css").read_text()
        for rule in (".gv.hov .e.on{", ".gv.hov .nd{", ".gv.hov .nd.on{opacity:1}", ".nd.nyet{", ".e.ny{",
                     ".nd.added>.nb{fill:url(#g-added)}", ".nd.wait>.wf{"):
            self.assertIn(rule, css)
        reduced = css[css.index("@media (prefers-reduced-motion:reduce){.nd.k-running"):]
        self.assertIn(".rw .rg.pulse{animation:none}", reduced.split("\n")[0])
        app = (SKILL_DIR / "assets" / "viewer" / "app.css").read_text()
        self.assertEqual(app.count("--edge-hi:"), 2, "a highlight color in the dark and the light theme")


if __name__ == "__main__":
    unittest.main()
