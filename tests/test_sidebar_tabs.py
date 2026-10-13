"""Viewer sidebar, tab bar and tables: section labels, slim rows, pulsing phase dots, no
".tasks/done/" path, ten items per group, backlog folders, tab order, dimmed empty tabs, wrapping
Title and Summary cells.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [SIDEBAR-SECTIONS], [SIDEBAR-SLIM-ROWS], [SIDEBAR-ACTIVE-PULSE], [SIDEBAR-NO-DONE-PATH],
[SIDEBAR-SHOW-MORE], [SIDEBAR-BACKLOG-FOLDERS], [TAB-ORDER], [TABLE-WRAP].
"""

from __future__ import annotations

import re
import shutil
import unittest

from saetest import SKILL_DIR
from test_viewer_server import run_node

VIEWER = SKILL_DIR / "assets" / "viewer"

# app.js, task-views.js and settings.js in node; #side and #main keep what the page draws.
# argv: the three files, the data file ({idx, task, open_bl, more, findings_tab}).
PAGE_JS = r"""
const vm = require("vm"), fs = require("fs");
const el = () => new Proxy({innerHTML: "", hidden: true, scrollTop: 0, dataset: {}, style: {},
  classList: {toggle() {}, contains() { return false }}, querySelectorAll() { return [] }},
  {get: (t, k) => k in t ? t[k] : () => null});
const nodes = {"#side": el(), "#main": el()};
const ctx = {console, setTimeout: () => 0, clearTimeout() {}, setInterval() {}, addEventListener() {}, history: {replaceState() {}},
  location: {hash: ""}, localStorage: {getItem() { return null }, setItem() {}},
  document: {hidden: false, title: "", documentElement: {dataset: {}}, body: el(), activeElement: null,
    querySelector: s => nodes[s] || el(), querySelectorAll: () => [], addEventListener() {}, createElement: el}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 5)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
ctx.DATA = JSON.parse(fs.readFileSync(process.argv[5], "utf8"));
vm.runInContext(`readHash(); IDX = DATA.idx; S.repo = "R"; S.task = DATA.task; S.bl = DATA.open_bl || null;
  (DATA.more || []).forEach(k => { MORE[k] = 1 }); renderSide();
  if (DATA.task) { S.tab = "findings"; renderMain() }`, ctx);
const tabs = vm.runInContext("TABS.map(x => x[0])", ctx);
const findings = ctx.DATA.findings_tab ? vm.runInContext("TAB.findings()", ctx) : "";
console.log(JSON.stringify({side: nodes["#side"].innerHTML, main: nodes["#main"].innerHTML, tabs, findings}));
"""


def task(n: int, phase: str = "shaping", **extra) -> dict:
    t = {"id": f"2026-10-01-{n:04d}--task-{n:02d}", "title": f"Task {n:02d}", "phase": phase,
         "last_change": "2026-10-01T10:00:00Z", "counts": {"done": 1, "pending": 2}, "parked": 0, "holds": 0,
         "location": "home"}
    t.update(extra)
    return t


def index(tasks=(), backlog=(), findings=()) -> dict:
    return {"repo": "r", "root": "/r", "sae": "sae", "tasks": list(tasks), "backlog": list(backlog),
            "findings": list(findings), "drafts": [], "open_drafts": 0, "closed_findings": ""}


def backlog_item(file: str, title: str) -> dict:
    return {"file": file, "title": title, "created": "2026-10-01T10:00:00Z", "text": "# " + title}


def page(**data) -> dict:
    return run_node(PAGE_JS, "app.js", "task-views.js", "settings.js", data=data)


def rows(html: str) -> list[str]:
    """Each sidebar item button, in page order."""
    return re.findall(r'<button class="ti[^"]*"[\s\S]*?</button>', html)


def row_of(html: str, title: str) -> str:
    return next(r for r in rows(html) if f"{title}</span>" in r)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class SidebarTests(unittest.TestCase):
    def test_section_labels_have_their_own_style_and_groups_are_indented(self):
        side = page(idx=index([task(1)]), task=None)["side"]
        for label in ("Tasks", "Backlog", "Decision drafts"):
            self.assertIn(f'<span class="sl">{label}</span>', side)
        css = (VIEWER / "app.css").read_text()
        self.assertRegex(css, r"\.sx\.top \.sl\{text-decoration:underline")
        self.assertRegex(css, r"\.sgrp\{[^}]*margin:4px 0 0 12px")

    def test_only_the_open_task_has_the_full_row(self):
        ts = [task(1, "executing"), task(2, "executing")]
        side = page(idx=index(ts), task=ts[0]["id"])["side"]
        opened, other = row_of(side, "Task 01"), row_of(side, "Task 02")
        self.assertIn('class="sbw"', opened)
        self.assertIn("in home", opened)
        self.assertIn(" slim", other)
        self.assertNotIn('class="sbw"', other)
        self.assertNotIn("in home", other)

    def test_tasks_in_progress_pulse_and_done_tasks_stay_still(self):
        ts = [task(1, "shaping"), task(2, "executing"), task(3, "planning"), task(4, "done"), task(5, "abandoned")]
        side = page(idx=index(ts), task=None, more=[])["side"]
        # done and abandoned groups fold above three tasks only, so all five rows show
        for n in (1, 2, 3):
            self.assertIn(" pulse", row_of(side, f"Task {n:02d}"))
        for n in (4, 5):
            self.assertNotIn(" pulse", row_of(side, f"Task {n:02d}"))
        css = (VIEWER / "app.css").read_text()
        self.assertIn(".ti.pulse .tt .pd{animation:", css)
        self.assertRegex(css, r"@media \(prefers-reduced-motion:reduce\)\{\.ti\.pulse \.tt \.pd\{animation:none\}\}")

    def test_done_tasks_do_not_say_where_they_are(self):
        ts = [task(1, "done", location="done", location_path="/r/.tasks/done/x")]
        side = page(idx=index(ts), task=ts[0]["id"])["side"]
        self.assertNotIn(".tasks/done", side)
        ts = [task(1, "done", location="done", location_path="/r/.tasks/done/x", worktree="/wt/x")]
        self.assertIn("worktree kept for testing", page(idx=index(ts), task=ts[0]["id"])["side"])

    def test_a_group_shows_ten_items_and_the_open_task(self):
        ts = [task(n) for n in range(12, 0, -1)]  # newest first, as the server sends them
        side = page(idx=index(ts), task=ts[-1]["id"])["side"]
        shown = [r for r in rows(side) if "Task " in r]
        self.assertEqual(len(shown), 11)  # ten newest and the open one
        self.assertIn("Task 01</span>", shown[-1])
        self.assertNotIn("Task 02</span>", side)
        self.assertIn('data-act="more" data-k="ph:shaping" data-nav>Show 1 more</button>', side)
        opened = page(idx=index(ts), task=ts[-1]["id"], more=["ph:shaping"])["side"]
        self.assertIn("Task 02</span>", opened)
        self.assertNotIn('data-act="more"', opened)

    def test_backlog_is_grouped_by_folder_top_level_first(self):
        bl = [backlog_item(f".tasks/backlog/mod/2026-10-01-{n:04d}--m.md", f"Mod {n:02d}") for n in range(11, 0, -1)]
        bl.insert(3, backlog_item(".tasks/backlog/2026-10-01-0500--top.md", "Top item"))
        bl.append(backlog_item(".tasks/backlog/other/2026-10-01-0001--o.md", "Other item"))
        side = page(idx=index(backlog=bl), task=None, open_bl=bl[-2]["file"])["side"]
        order = [re.search(r'<span class="tt">([^<]*)</span>', r).group(1) for r in rows(side)]
        self.assertEqual(order[0], "Top item")
        self.assertIn('data-k="blf:mod"', side)
        self.assertIn('data-k="blf:other"', side)
        self.assertLess(side.index('data-k="blf:mod"'), side.index('data-k="blf:other"'))
        # eleven items in the folder: ten newest and the open oldest one, nothing behind "Show more"
        self.assertEqual(sum(1 for t in order if t.startswith("Mod")), 11)
        side = page(idx=index(backlog=bl), task=None)["side"]
        self.assertIn('data-k="blf:mod" data-nav>Show 1 more</button>', side)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TabsAndTablesTests(unittest.TestCase):
    def test_tab_order_ends_with_settings(self):
        tabs = page(idx=index([task(1)]), task=None)["tabs"]
        self.assertEqual(tabs, ["plan", "spec", "reviews", "findings", "decisions", "overview", "timeline", "jobs",
                                "settings"])

    def test_a_tab_with_count_zero_is_dimmed_and_still_a_tab(self):
        ts = [task(1)]
        main = page(idx=index(ts), task=ts[0]["id"])["main"]
        findings = re.search(r'<button role="tab" id="tab-findings"[^>]*>[^<]*<i>0</i>', main)
        self.assertIsNotNone(findings, main)
        self.assertIn('class="zero"', findings.group(0))
        self.assertIn('data-act="tab" data-tab="findings"', findings.group(0))
        self.assertNotRegex(main, r'id="tab-plan" class="zero"')
        main = page(idx=index(ts, findings=[{"file": "f.md", "title": "x", "text": "", "source": ts[0]["id"]}]), task=ts[0]["id"])["main"]
        self.assertNotRegex(main, r'id="tab-findings" class="zero"')
        self.assertIn(".tabs button.zero{opacity:", (VIEWER / "app.css").read_text())

    def test_findings_title_and_decisions_summary_wrap(self):
        long = "a very long finding title " * 8
        html = page(idx=index(findings=[{"file": "f.md", "title": long, "text": ""}]), task=None,
                    findings_tab=True)["findings"]
        self.assertIn('<td class="long">' + long.replace("'", "&#39;"), html)
        css = (VIEWER / "app.css").read_text()
        self.assertRegex(css, r"td\.long\{[^}]*white-space:normal")
        views = (VIEWER / "task-views.js").read_text()
        decisions = views[views.index("TAB.decisions="):views.index("// [VIEWER-DECISIONS-AND-PROTOTYPES]")]
        self.assertIn('["long",esc(e.summary)', decisions)
        # the palette class .w (mono, no wrap) never lands on a table cell
        self.assertNotRegex(views, r'\["(?:[\w-]+ )*w"')


if __name__ == "__main__":
    unittest.main()
