"""The viewer shows that the task waits for the owner: the server's `asks` and `waiting`, the red
frame of a card an open ask names, the yellow pulsing frame and banner of the graph area, "● Needs
you" in the title, the favicon and its dot, and polling in a hidden tab.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [WAIT-FRAMES], [WAIT-TAB-TITLE], [FAVICON], [ASK-COMMAND] (the viewer shows open asks).
"""

from __future__ import annotations

import re
import shutil
import unittest

from saetest import SKILL_DIR, dispatch_workspace
from test_sae_ask import AskCase
from test_viewer_server import ViewerServerCase, request, run_node

VIEWER = SKILL_DIR / "assets" / "viewer"
LOGO_PATHS = ('d="M33 33H109L141 65V100H106V80L94 68H68V94H33Z"', 'd="M141 165H65L33 133V98H68V118L80 130H106V104H141Z"',
              'd="M104 87L160 100L104 113Z"')

# the three viewer scripts in node, with elements that keep what the page writes: render() one task's
# data, then report the title, the favicon, the Plan tab's HTML and the card classes and tooltips
# (argv: the three files, the data file, then "hidden" or "visible")
PAGE_JS = r"""
const vm = require("vm"), fs = require("fs");
const els = {}, el = sel => els[sel] = els[sel] || new Proxy({innerHTML: "", hidden: true, scrollTop: 0, dataset: {}, style: {}, attrs: {href: "favicon.svg"},
  classList: {toggle() {}, contains() { return false }, add() {}, remove() {}}, addEventListener() {}, querySelectorAll() { return [] },
  getAttribute(k) { return this.attrs[k] }, setAttribute(k, v) { this.attrs[k] = v }},
  {get: (t, k) => k in t ? t[k] : () => null});
const timers = [], fetched = [];
const ctx = {console, setTimeout: (f, ms) => { timers.push(ms); return 1 }, clearTimeout() {}, setInterval() {}, addEventListener() {},
  history: {replaceState() {}}, location: {hash: ""}, localStorage: {getItem() { return null }, setItem() {}},
  fetch: url => { fetched.push(url); return new Promise(() => {}) },
  document: {hidden: process.argv[6] === "hidden", title: "", documentElement: {dataset: {}}, body: el("body"), activeElement: null,
    querySelector: el, querySelectorAll: () => [], addEventListener() {}, createElement: () => el("new" + Math.random())}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 5)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
ctx.TASK = JSON.parse(fs.readFileSync(process.argv[5], "utf8"));
ctx.timers = timers; ctx.fetched = fetched; ctx.ICON = el("#icon");
console.log(JSON.stringify(vm.runInContext(`readHash(); var info = TASK.state.task;
  IDX = {sae: "sae", repo: "R", root: "/r", generated: "", tasks: [{id: info.id, title: info.title, phase: info.phase}]};
  S.repo = "R"; S.task = info.id; TASKS[S.task] = TASK; render();
  var g = graph(TASK), plan = TAB.plan(TASK);
  sched(); var delay = timers[timers.length - 1]; poll();
  ({title: document.title, icon: ICON.attrs.href, plan: plan, main: document.querySelector("#main").innerHTML,
    cards: g.cards.map(c => ({id: c.id, cls: c.cls, tip: c.tip})), delay: delay, fetched: fetched.slice()})`, ctx)));
"""


def card(out: dict, card_id: str) -> dict:
    return next(c for c in out["cards"] if c["id"] == card_id)


@unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
class WaitSignalsTests(ViewerServerCase, AskCase):
    def data(self, sb, task: str) -> dict:
        view = getattr(self, "_view", None) or self.view(sb, task)
        self._view = view
        code, data, _ = request(view["port"], "GET", f"/api/task?repo={view['repo']}&task={task}")
        self.assertEqual(code, 200, data)
        return data

    def page(self, data: dict, hidden: bool = False) -> dict:
        return run_node(PAGE_JS, "app.js", "task-views.js", "settings.js", data=data, args=("hidden" if hidden else "visible",))

    def test_asks_a_parked_job_and_a_hold_frame_the_cards_and_the_graph_and_mark_the_title(self):
        """[WAIT-FRAMES], [WAIT-TAB-TITLE], [ASK-COMMAND]: the server sends asks and waiting; the card an ask
        names and the parked card get the red frame; the graph area the yellow frame and the banner; the
        title "● Needs you" and the favicon its dot. Once nothing waits, all of it goes."""
        sb = self.sandbox()
        task = self.started(sb, "wait", jobs=("A", "B", "C"))
        out = self.page(self.data(sb, task))
        self.assertEqual(out["title"], "wait · R")
        self.assertEqual(out["icon"], "favicon.svg")
        self.assertNotIn('class="wbar"', out["plan"])
        self.assertNotIn("gwrap owner", out["plan"])
        self.assertFalse([c["id"] for c in out["cards"] if "wait" in c["cls"]])
        # a task-level ask, an ask for A, a parked job B and an active hold after C
        sb.sae("ask", "wait", "Release today?")
        sb.sae("ask", "wait", "Keep the v1 envelope?", "--job", "A")
        sb.sae("dispatch", "wait", "B")
        sb.result(task, "jobs/B.result.md", status="parked", summary="needs a decision", validation="not-run", changes="none")
        sb.sae("collect", "wait", "B")
        sb.sae("hold", "wait", "C", "--reason", "look first")
        ws = dispatch_workspace(sb, task, "C")
        sb.work(ws, "c.txt", "C\n", "C: work")
        sb.result(task, "jobs/C.result.md", status="done", summary="ok", validation="pass", changes="made")
        sb.sae("collect", "wait", "C")
        data = self.data(sb, task)
        self.assertEqual([(a["question"], a["job"]) for a in data["asks"]],
                         [("Release today?", None), ("Keep the v1 envelope?", "A")])
        self.assertEqual([(w["kind"], w["job"]) for w in data["waiting"]],
                         [("ask", None), ("ask", "A"), ("parked", "B"), ("hold", "C")])
        out = self.page(data)
        self.assertEqual(out["title"], "● Needs you · wait · R")
        self.assertEqual(out["icon"], "favicon-wait.svg")
        self.assertEqual(sorted(c["id"] for c in out["cards"] if "wait" in c["cls"]), ["A", "B"])
        self.assertIn("Asks the owner: Keep the v1 envelope?", card(out, "A")["tip"])
        self.assertIn('<div class="gwrap owner"', out["plan"])
        banner = re.search(r'<div class="wbar".*?</div>', out["plan"], re.S).group(0)
        self.assertIn("<b>● Needs you</b><span>Release today?</span><i> (+3 more)</i>", banner)
        for text in ("Keep the v1 envelope?", "B is parked: needs a decision", "Hold after C: look first"):
            self.assertIn(text, banner)  # the other reasons are in its tooltip
        self.assertIn('class="wbar"', out["main"], "render() draws the Plan tab with the banner")
        # the owner answers: A's ask by a human log for A, the rest with --answered; B and the hold stay
        sb.sae("log", "wait", "decision", "Keep v1", "--job", "A", "--by", "human")
        sb.sae("ask", "wait", "--answered")
        out = self.page(self.data(sb, task))
        self.assertEqual(sorted(c["id"] for c in out["cards"] if "wait" in c["cls"]), ["B"])
        self.assertEqual(out["title"], "● Needs you · wait · R")
        sb.sae("hold", "wait", "C", "--release")
        sb.sae("dispatch", "wait", "B", "--resume", "--reason", "owner decided")
        out = self.page(self.data(sb, task))
        self.assertEqual((out["title"], out["icon"]), ("wait · R", "favicon.svg"))
        self.assertNotIn('class="wbar"', out["plan"])
        self.assertFalse([c["id"] for c in out["cards"] if "wait" in c["cls"]])

    def test_no_frame_and_no_banner_in_shaping_or_planning(self):
        """[WAIT-FRAMES]: an open ask in shaping is listed (asks) but nothing waits; in shaping and planning
        neither an ask for a job nor a parked job draws a frame, a banner or "● Needs you"."""
        sb = self.sandbox()
        shaping = sb.new_task("Shape", "shape")
        sb.sae("ask", "shape", "Which scope?")
        data = self.data(sb, shaping)
        self.assertEqual([a["question"] for a in data["asks"]], ["Which scope?"])
        self.assertEqual(data["waiting"], [])
        out = self.page(data)
        self.assertEqual((out["title"], out["icon"]), ("Shape · R", "favicon.svg"))
        self.assertNotIn('class="wbar"', out["plan"])
        # the card data of a parked job and an ask for a job, drawn as if the task were back in shaping or planning
        task = self.started(sb, "early", jobs=("A", "B"))
        sb.sae("ask", "early", "Keep A?", "--job", "A")
        sb.sae("dispatch", "early", "B")
        sb.result(task, "jobs/B.result.md", status="parked", summary="needs a decision", validation="not-run", changes="none")
        sb.sae("collect", "early", "B")
        data = self.data(sb, task)
        self.assertEqual(sorted(c["id"] for c in self.page(data)["cards"] if "wait" in c["cls"]), ["A", "B"])
        for phase in ("shaping", "planning"):
            data["state"]["task"]["phase"], data["waiting"] = phase, []  # the server sends no reasons there
            out = self.page(data)
            self.assertEqual((out["title"], out["icon"]), ("early · R", "favicon.svg"))
            self.assertNotIn('class="wbar"', out["plan"])
            self.assertFalse([c["id"] for c in out["cards"] if "wait" in c["cls"]], phase)

    def test_a_hidden_tab_keeps_polling_slower(self):
        """[WAIT-TAB-TITLE]: a hidden tab polls at a slower rate instead of stopping, so the title and the
        favicon change while the owner looks at another tab."""
        sb = self.sandbox()
        task = self.started(sb, "poll", jobs=("A",))
        data = self.data(sb, task)
        data["state"]["task"]["phase"] = "executing"
        visible, hidden = self.page(data), self.page(data, hidden=True)
        self.assertEqual(visible["fetched"], ["/api/projects"])
        self.assertEqual(hidden["fetched"], ["/api/projects"], "a hidden tab still polls")
        self.assertGreater(hidden["delay"], visible["delay"])
        self.assertLessEqual(hidden["delay"], 60000)


class FaviconTests(ViewerServerCase):
    def test_the_server_serves_the_favicon_and_the_page_links_it(self):
        """[FAVICON]: the owner's icon, in assets/viewer/, served as SVG; the page links it."""
        sb = self.sandbox()
        view = self.view(sb)
        status, page, _ = request(view["port"], "GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b'<link rel="icon" id="icon" type="image/svg+xml" href="favicon.svg">', page)
        for name in ("favicon.svg", "favicon-wait.svg"):
            status, body, headers = request(view["port"], "GET", "/" + name)
            self.assertEqual((status, headers["content-type"]), (200, "image/svg+xml"))
            self.assertEqual(body, (VIEWER / name).read_bytes())

    def test_the_icon_is_the_owners_logo_and_its_dark_half_is_visible_on_a_dark_tab_bar(self):
        """[FAVICON]: the paths of prototypes/logo/logo-icon.svg; the dark half (#17252B) turns light under
        prefers-color-scheme: dark; the waiting variant adds a dot."""
        plain, wait = ((VIEWER / n).read_text() for n in ("favicon.svg", "favicon-wait.svg"))
        for svg in (plain, wait):
            for path in LOGO_PATHS:
                self.assertIn(path, svg)
            self.assertIn('class="d" d="M141 165H65', svg)
            self.assertIn(".d{fill:#17252B}", svg)
            self.assertIn("@media (prefers-color-scheme:dark){.d{fill:#C9D6DB}", svg)
        self.assertNotIn("<circle", plain)
        self.assertIn("<circle", wait)

    def test_the_wait_frame_pulses_softly_and_stops_with_reduced_motion(self):
        """[WAIT-FRAMES]: a thin frame, no fill over the graph, no pulse with prefers-reduced-motion."""
        css = (VIEWER / "task-views.css").read_text()
        self.assertIn(".gwrap.owner::after{", css)
        rule = re.search(r"\.gwrap\.owner::after\{([^}]*)\}", css).group(1)
        self.assertIn("border:1px solid var(--frame-ask)", rule)
        self.assertIn("pointer-events:none", rule)
        self.assertNotIn("background", rule)
        self.assertIn("@media (prefers-reduced-motion:reduce){.gwrap.owner::after{animation:none}}", css)
        self.assertEqual((VIEWER / "app.css").read_text().count("--frame-ask:"), 2, "dark and light")


if __name__ == "__main__":
    unittest.main()
