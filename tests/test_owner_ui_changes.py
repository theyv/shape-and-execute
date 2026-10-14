"""The owner's UI changes from the gate ([AMEND-5]): section colors and row indent in the sidebar, the
title in the top bar only, the step bar below the graph, no graph legend, prototypes as a third
switch option, "this task / all" in Findings and Decisions, stats per phase first, a check for a
fixed spec review, the red hold frame, a collapsed sidebar that frees its width, the ask signal in
the Settings tab only.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [SIDEBAR-SECTION-COLORS], [SIDEBAR-ROW-INDENT], [HEADER-TOP-BAR], [GRAPH-NO-LEGEND],
[SPEC-PROTOTYPES-SWITCH], [SCOPE-TOGGLE], [OVERVIEW-STATS-FIRST], [GRAPH-FIXED-PHASE-REVIEW],
[WAIT-HOLD-FRAME], [SIDEBAR-COLLAPSE-WIDTH], [ASK-SETTING-TEXT].
"""

from __future__ import annotations

import re
import shutil
import sys
import unittest

from saetest import SCRIPTS, SKILL_DIR
from test_graph_cards import FINDINGS_DOCS, GraphCardsCase, card
from test_viewer_server import run_node

sys.path.insert(0, str(SCRIPTS))

from sae_lib.server import closed_findings_list  # noqa: E402

VIEWER = SKILL_DIR / "assets" / "viewer"
NODE = shutil.which("node")
TASK_ID = "2026-10-13-1000--polish"
OTHER = "2026-10-12-0900--other"

# the three viewer scripts in node; elements keep what the page writes. DATA: {idx, task (the task data or null),
# hash, js (an expression evaluated after the setup)}
PAGE_JS = r"""
const vm = require("vm"), fs = require("fs");
const els = {}, el = sel => els[sel] = els[sel] || new Proxy({innerHTML: "", hidden: true, scrollTop: 0, dataset: {}, style: {}, attrs: {},
  classList: {toggle() { return false }, contains() { return false }, add() {}, remove() {}}, addEventListener() {}, querySelectorAll() { return [] },
  getAttribute(k) { return this.attrs[k] }, setAttribute(k, v) { this.attrs[k] = v }},
  {get: (t, k) => k in t ? t[k] : () => null});
const ctx = {console, setTimeout: () => 0, clearTimeout() {}, setInterval() {}, addEventListener() {},
  history: {replaceState() {}}, location: {hash: ""}, localStorage: {getItem() { return null }, setItem() {}},
  fetch: () => new Promise(() => {}),
  document: {hidden: false, title: "", documentElement: {dataset: {}}, body: el("body"), activeElement: null,
    querySelector: el, querySelectorAll: () => [], addEventListener() {}, createElement: () => el("new" + Math.random())}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 5)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
ctx.DATA = JSON.parse(fs.readFileSync(process.argv[5], "utf8")); ctx.els = els;
ctx.location.hash = ctx.DATA.hash || "";
console.log(JSON.stringify(vm.runInContext(`readHash(); IDX = DATA.idx; S.repo = "R";
  if (DATA.task) { S.task = DATA.task.state.task.id; TASKS[S.task] = DATA.task }
  (function () { ${ctx.DATA.js} })()`, ctx)));
"""


def page(js: str, idx: dict, task: dict | None = None, hash_: str = "") -> dict:
    return run_node(PAGE_JS, "app.js", "task-views.js", "settings.js", data={"idx": idx, "task": task, "hash": hash_, "js": js})


def text(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


def job(kind="implementation", status="pending", **extra) -> dict:
    j = {"kind": kind, "status": status, "needs": [], "attempts": [], "difficulty": "normal", "last_change": "2026-10-13T10:00:00Z"}
    j.update(extra)
    return j


def task_data(jobs=None, phase="executing", events=(), **extra) -> dict:
    """The /api/task answer of a small task, as far as the page reads it."""
    jobs = jobs if jobs is not None else {"A": job()}
    t = {"state": {"task": {"id": TASK_ID, "title": "Polish", "phase": phase, "branch": f"task/{TASK_ID}",
                            "worktree": f"/w/{TASK_ID}/task", "approvals": {}, "holds": {}}, "jobs": jobs},
         "events": list(events), "files": {}, "waits": {k: [] for k in jobs}, "settings": None, "steps": [],
         "planned_reviews": [], "routing": {}, "review_marks": {}, "difficulty": {}, "models": {}, "asks": [], "waiting": [],
         "version": "v1"}
    t.update(extra)
    return t


def index(**extra) -> dict:
    idx = {"repo": "r", "root": "/r", "sae": "sae", "generated": "2026-10-13T10:00:00Z",
           "tasks": [{"id": TASK_ID, "title": "Polish", "phase": "executing", "last_change": "2026-10-13T10:00:00Z",
                      "counts": {"pending": 1}, "parked": 0, "holds": 0, "branch": f"task/{TASK_ID}",
                      "worktree": f"/w/{TASK_ID}/task", "location": "task worktree", "location_path": f"/w/{TASK_ID}/task"}],
           "backlog": [], "findings": [], "drafts": [], "open_drafts": 0, "closed_findings": "", "closed_list": []}
    idx.update(extra)
    return idx


def finding(stem: str, source: str | None) -> dict:
    return {"file": f".tasks/findings/{stem}.md", "title": f"Title {stem}", "type": "defect", "confidence": "high",
            "source": source, "created": "2026-10-13T10:00:00Z", "text": "# x"}


def closed(stem: str, outcome: str) -> dict:
    return closed_findings_list(f"- 2026-10-13 · {stem} · Title {stem} · {outcome}\n")[0]


def draft(name: str, source: str | None, status="proposed") -> dict:
    return {"file": f".tasks/adr/{name}.md", "title": f"Draft {name}", "type": "architecture", "status": status,
            "source": source, "date": "2026-10-13", "text": "# d"}


class ServerTests(unittest.TestCase):
    def test_closed_findings_name_the_task_and_job_that_closed_them(self):
        """[SCOPE-TOGGLE]: the server's closed_list parses closed.md; `fixed in <task> [by <JOB>]` names the closer."""
        text = ("# Closed findings\n\n- 2026-10-12 · s1 · A title · with · dots · fixed in 2026-10-12-0900--x by FIX-1\n"
                "- 2026-10-12 · s2 · B · fixed in 2026-10-12-0900--x\n- 2026-10-13 · s3 · C · rejected: not a bug\n"
                "- odd line\nnot a list line\n")
        got = closed_findings_list(text)
        self.assertEqual([(c["stem"], c["title"], c["task"], c["job"]) for c in got],
                         [("s1", "A title · with · dots", "2026-10-12-0900--x", "FIX-1"), ("s2", "B", "2026-10-12-0900--x", None),
                          ("s3", "C", None, None), ("", "odd line", None, None)])
        self.assertEqual(got[2]["outcome"], "rejected: not a bug")


@unittest.skipUnless(NODE, "node runs the viewer scripts")
class SidebarAndHeaderTests(unittest.TestCase):
    def test_section_labels_have_their_own_color_and_a_thin_underline(self):
        """[SIDEBAR-SECTION-COLORS]: each section label its own class and color token, in both themes; 1px underline."""
        out = page("renderSide(); return els['#side'].innerHTML", index())
        for cls, label in (("s-tasks", "Tasks"), ("s-backlog", "Backlog"), ("s-drafts", "Decision drafts")):
            self.assertRegex(out, rf'class="sx top {cls}"[^>]*>.*?<span class="sl">{label}</span>')
        css = (VIEWER / "app.css").read_text()
        for token in ("--sec-tasks:", "--sec-backlog:", "--sec-drafts:"):
            self.assertEqual(css.count(token), 2, f"{token} in dark and light")
        self.assertEqual(len({m for m in re.findall(r"--sec-\w+:(#[0-9a-f]+)", css)}), 6, "six distinct colors")
        rule = re.search(r"\.sx\.top \.sl\{([^}]*)\}", css).group(1)
        self.assertIn("text-decoration-thickness:1px", rule)
        self.assertIn("var(--sc", rule)

    def test_task_rows_start_at_the_group_labels_text(self):
        """[SIDEBAR-ROW-INDENT]: a task row's padding is at least the label's text offset (8 + 10 + 2 + 6 + 10 + 6)."""
        css = (VIEWER / "app.css").read_text()
        sx = re.search(r"\.sx\{([^}]*)\}", css).group(1)
        self.assertIn("gap:6px", sx)
        self.assertIn("padding:0 8px", sx)
        pad = int(re.search(r"\.sgrp \.ti\.dot\{padding-left:(\d+)px\}", css).group(1))
        self.assertGreaterEqual(pad, 8 + 10 + 2 + 6 + 10 + 6)
        self.assertLessEqual(pad, 50, "slightly further right, not far")

    def test_the_title_and_phase_live_in_the_top_bar_only(self):
        """[HEADER-TOP-BAR]: the top bar has the title and "· executing"; the page has no second title, no phase
        pill, no "active … ago"; branch and worktree are in the Overview; step bar and stats below the graph."""
        t = task_data(next={"ready": [], "running": [], "holds": [], "holds_active": []})
        out = page("render(); return {top: els['#top'].innerHTML, main: els['#main'].innerHTML, ov: TAB.overview(T()), plan: TAB.plan(T())}",
                   index(), t)
        self.assertIn('<h1 class="t" title="' + TASK_ID + '">Polish</h1><span class="tp p-executing">· executing</span>', out["top"])
        self.assertNotIn("<h1", out["main"])
        self.assertNotIn('class="php', out["main"])
        self.assertNotIn("active ", text(out["main"]))
        self.assertNotIn("branch", text(out["main"]))
        self.assertIn('data-tab="settings">All settings</button>', out["main"])
        self.assertNotIn('class="slim"', out["main"].split('class="tc"')[0], "no step bar in the header")
        self.assertIn(f"branch task/{TASK_ID}", text(out["ov"]))
        self.assertIn("task worktree …/" + TASK_ID + "/task", text(out["ov"]))
        self.assertIn(f'data-copy="/w/{TASK_ID}/task"', out["ov"])
        plan = out["plan"]
        self.assertLess(plan.index('class="gwrap'), plan.index('class="slim"'))
        self.assertLess(plan.index('class="slim"'), plan.index("Next up"))

    def test_overview_puts_the_phase_stats_right_after_needs_you(self):
        """[OVERVIEW-STATS-FIRST]."""
        t = task_data(phase_stats=[{"phase": "shape", "started": "2026-10-13T09:00:00Z", "main_tokens": 10, "subagent_tokens": 5,
                                    "tokens": 15, "subagent_s": 60, "jobs": 1, "attempts": 1, "wall_s": 120}],
                      files={"plan.md": "# Plan\n\n## Riskiest assumptions\n- one\n"})
        ov = text(page("return TAB.overview(T())", index(), t))
        order = [ov.index(h) for h in ("Needs you", "Stats per phase", "To check before you merge", "Riskiest assumptions")]
        self.assertEqual(order, sorted(order), ov)

    def test_rendering_the_overview_keeps_the_page_note(self):
        """The phase table's notes are its own: rendering the Overview leaves note() of holds and overrides alone."""
        t = task_data(phase_stats=[{"phase": "shape", "started": "2026-10-13T09:00:00Z", "main_tokens": None, "main_note": "x",
                                    "subagent_tokens": 5, "tokens": None, "subagent_s": 0, "jobs": 0, "attempts": 0, "wall_s": 1}])
        out = page("var before = note; TAB.overview(T()); return note === before", index(), t)
        self.assertTrue(out)

    def test_a_collapsed_sidebar_frees_its_width_and_the_graph_fits_again(self):
        """[SIDEBAR-COLLAPSE-WIDTH]: no max width on the content; collapse() drops the stored graph view and redraws
        the main area (the graph fits the new width, the timeline is drawn for it)."""
        css = (VIEWER / "app.css").read_text()
        self.assertNotRegex(re.search(r"\.wrap\{([^}]*)\}", css).group(1), r"max-width")
        self.assertIn(".app.sc{grid-template-columns:0 minmax(0,1fr)}", css)
        self.assertNotIn("1280", (VIEWER / "task-views.js").read_text(), "the timeline is not capped either")
        out = page("render(); GV[S.task] = {x: 1, y: 2, k: .5}; els['#main'].innerHTML = ''; collapse(); "
                   "return {gv: GV[S.task] || null, main: els['#main'].innerHTML.length > 0}", index(), task_data())
        self.assertEqual(out, {"gv": None, "main": True})


@unittest.skipUnless(NODE, "node runs the viewer scripts")
class TabTests(unittest.TestCase):
    def test_the_graph_has_no_legend_and_its_rules_are_in_tooltips(self):
        """[GRAPH-NO-LEGEND]: no status legend above the graph (the legend of kinds and marks below it stays, as the
        owner asked); the Integration card's tooltip says where a review lives; an added card's tooltip names its fill."""
        jobs = {"A": job(status="done", merged=True), "LATE": job(),
                "REVIEW-INTEGRATION": job("review", target="integration", needs=["A"])}
        t = task_data(jobs, events=[{"type": "job.added", "job": "A", "kind": "implementation", "needs": []},
                                    {"type": "plan.approved", "by": "owner"},
                                    {"type": "job.added", "job": "LATE", "kind": "implementation", "needs": [], "reason": "asked"},
                                    {"type": "job.added", "job": "REVIEW-INTEGRATION", "kind": "review", "needs": ["A"]}])
        out = page("var g = graph(T()); return {plan: TAB.plan(T()), cards: g.cards.map(c => ({id: c.id, tip: c.tip}))}", index(), t)
        self.assertNotIn('class="legend"', out["plan"])
        self.assertNotIn('class="lgr"', out["plan"])
        self.assertNotIn("Rows:", out["plan"])
        self.assertNotIn('class="pill k-pending"', out["plan"])
        below = out["plan"].index('<div class="legend kinds"')
        self.assertGreater(below, out["plan"].index('class="gwrap'))
        self.assertLess(below, out["plan"].index('class="slim"'))
        self.assertNotIn("✓ merged</span>", out["plan"])
        tips = {c["id"]: c["tip"] for c in out["cards"]}
        self.assertIn("A review lives in the card of what it reviews; the integration review reviews the whole task",
                      tips["@integration"])
        self.assertIn("Added after plan approval (the hatched fill): asked", tips["LATE"])

    def test_prototypes_are_a_third_option_of_the_document_switch(self):
        """[SPEC-PROTOTYPES-SWITCH]: "prototypes (N)" after intent.md and specs.md; specs.md stays the default; the
        option shows the list; no option without prototypes."""
        protos = [{"path": "prototypes/a.html", "url": "/proto/R/x/a.html", "size": 10},
                  {"path": "prototypes/b.html", "url": "/proto/R/x/b.html", "size": 20}]
        files = {"intent.md": "# Intent\n\nWhy.\n", "specs.md": "# Spec\n\nThe spec text.\n"}
        t = task_data(files=files, prototypes=protos)
        spec = page("return TAB.spec(T())", index(), t, "#tab=spec")
        self.assertRegex(spec, r'data-d="intent">intent\.md</button><button role="radio" aria-checked="true" data-act="doc" '
                               r'data-d="spec">specs\.md</button><button role="radio" aria-checked="false" data-act="doc" '
                               r'data-d="proto">prototypes \(2\)</button>')
        self.assertIn("The spec text.", spec)
        self.assertNotIn("a.html", spec, "the list opens only through its option")
        listed = page("return TAB.spec(T())", index(), t, "#tab=spec&doc=proto")
        self.assertIn('aria-checked="true" data-act="doc" data-d="proto"', listed)
        self.assertIn('href="/proto/R/x/a.html"', listed)
        self.assertNotIn("The spec text.", listed)
        none = page("return TAB.spec(T())", index(), task_data(files=files, prototypes=[]), "#tab=spec")
        self.assertNotIn('data-d="proto"', none)

    def test_findings_show_this_task_or_all_and_the_count_follows(self):
        """[SCOPE-TOGGLE]: "this task" (default): findings filed from it (source or finding.created) or closed by it
        (closed.md outcome or finding.closed), open and closed alike; "all": everything. The tab count follows."""
        idx = index(findings=[finding("f-mine", f"{TASK_ID}/A"), finding("f-event", None), finding("f-other", f"{OTHER}/B")],
                    closed_list=[closed("c-mine", f"fixed in {TASK_ID} by FIX"), closed("c-filed", f"fixed in {OTHER}"),
                                 closed("c-event", "rejected: duplicate"), closed("c-other", f"fixed in {OTHER} by X")])
        t = task_data(events=[{"type": "finding.created", "finding": ".tasks/findings/f-event.md"},
                              {"type": "finding.created", "finding": ".tasks/findings/c-filed.md"},
                              {"type": "finding.closed", "finding": "c-event", "job": "A"}])
        js = "S.tab = 'findings'; render(); return {main: els['#main'].innerHTML, tab: TAB.findings(T())}"
        mine = page(js, idx, t)
        self.assertIn('aria-checked="true" data-act="scope" data-v="task">this task</button>', mine["tab"])
        for stem in ("f-mine", "f-event", "c-mine", "c-filed", "c-event"):
            self.assertIn(f"Title {stem}", mine["tab"])
        for stem in ("f-other", "c-other"):
            self.assertNotIn(f"Title {stem}", mine["tab"])
        self.assertRegex(mine["main"], r'id="tab-findings"[^>]*>Findings<i>2</i>')
        every = page(js, idx, t, "#scope=all")
        self.assertIn('aria-checked="true" data-act="scope" data-v="all">all</button>', every["tab"])
        for stem in ("f-mine", "f-event", "f-other", "c-mine", "c-other"):
            self.assertIn(f"Title {stem}", every["tab"])
        self.assertRegex(every["main"], r'id="tab-findings"[^>]*>Findings<i>3</i>')

    def test_decisions_show_this_task_or_all_and_the_count_follows(self):
        """[SCOPE-TOGGLE]: drafts from this task (source or adr.created) in "this task"; all drafts in "all"; the count
        of decision jobs, decision events and drafts follows."""
        idx = index(drafts=[draft("d-mine", TASK_ID), draft("d-event", None), draft("d-other", OTHER)], open_drafts=3)
        t = task_data({"A": job(), "DECISION-A": job("decision", target="A")},
                      events=[{"type": "adr.created", "file": ".tasks/adr/d-event.md"},
                              {"type": "decision", "by": "agent", "summary": "keep v1", "at": "2026-10-13T10:00:00Z"}])
        js = "S.tab = 'decisions'; render(); return {main: els['#main'].innerHTML, tab: TAB.decisions(T())}"
        mine = page(js, idx, t)
        self.assertIn("Draft d-mine", mine["tab"])
        self.assertIn("Draft d-event", mine["tab"])
        self.assertNotIn("Draft d-other", mine["tab"])
        self.assertRegex(mine["main"], r'id="tab-decisions"[^>]*>Decisions<i>4</i>')  # 1 job + 1 event + 2 drafts
        every = page(js, idx, t, "#scope=all")
        self.assertIn("Draft d-other", every["tab"])
        self.assertRegex(every["main"], r'id="tab-decisions"[^>]*>Decisions<i>5</i>')

    def test_the_scope_switch_is_kept_in_the_url(self):
        """[SCOPE-TOGGLE]: "all" is in the hash; "this task" is the default and needs none."""
        out = page("var h = []; history.replaceState = (a, b, x) => h.push(x); go({sc: 'all'}); go({tab: 'decisions'});"
                   "go({sc: 'task'}); return h", index(), task_data())
        self.assertIn("scope=all", out[0])
        self.assertIn("scope=all", out[1])
        self.assertNotIn("scope", out[2])

    def test_an_active_hold_turns_the_frame_and_banner_red_and_carries_release(self):
        """[WAIT-HOLD-FRAME]: a hold alone: one red banner with the hold, what it stops and "Release hold"; no hold bar.
        Without a hold the frame stays yellow."""
        t = task_data({"C": job(status="done"), "D": job()}, waiting=[{"kind": "hold", "job": "C", "text": "Hold after C: look"}],
                      holds_active=["C"], next={"ready": [], "running": [], "holds": [], "holds_active": ["C"]})
        t["state"]["task"]["holds"] = {"C": {"reason": "look"}}
        plan = page("return TAB.plan(T())", index(), t)
        self.assertEqual(plan.count('class="wbar'), 1)
        self.assertIn('<div class="wbar hold"', plan)
        self.assertIn('<div class="gwrap owner hold"', plan)
        self.assertIn("<b>⏸ Hold active</b><span>Hold after C: look. Nothing new is dispatched until you release it", plan)
        self.assertNotIn("Also needs you", plan)
        self.assertIn('data-act="hold" data-id="C" data-v="release"', plan)
        self.assertNotIn("hbar", plan)
        t["waiting"] = [{"kind": "parked", "job": "D", "text": "D is parked: why"}]
        t["holds_active"], t["state"]["task"]["holds"] = [], {}
        plan = page("return TAB.plan(T())", index(), t)
        self.assertIn('<div class="gwrap owner"', plan)
        self.assertNotIn("owner hold", plan)
        css = (VIEWER / "task-views.css").read_text()
        self.assertIn(".gwrap.owner.hold::after{border-color:var(--frame-wait)}", css)
        self.assertNotIn(".hbar", css)

    def test_the_ask_signal_is_in_the_settings_tab_only_with_the_owners_text(self):
        """[ASK-SETTING-TEXT]: not in the settings card; the unset option reads "default (on)"; the help speaks to the
        owner: what the viewer shows, the cost per question, the defaults, parked jobs and holds without it."""
        settings = {"interaction": "full-auto", "levels": {"research": "balanced", "planning": "balanced", "execution": "balanced",
                                                           "review": "balanced"},
                    "review": {"points": [], "provider": "claude"}, "max_verify_failures": 3}
        t = task_data(settings=settings, status={"ask_signal": {"on": True, "set": None, "text": "on (mode default)"}})
        out = page("render(); SX.cur = {key: S.repo + '|' + S.task, task: {}, proj: {}}; "
                   "return {card: headerCard(T()), main: els['#main'].innerHTML, row: sxAskRow(false), help: HELP.ask}", index(), t)
        for where in (out["card"], out["main"]):
            self.assertNotIn("ask-signal", where)
            self.assertNotIn("ask signal", where.lower())
        self.assertIn('data-v="unset">default (on)</button>', out["row"])
        self.assertNotIn("mode default", out["row"])
        help_ = text(out["help"])
        for words in ("the viewer tells you when a question waits for you", "red frame", "Needs you", "one extra call",
                      "on in full-auto, auto and critical-only", "off in collaborative and interactive",
                      "Parked jobs and holds show without it."):
            self.assertIn(words, help_)
        self.assertNotIn("reminds the orchestrator", help_)


@unittest.skipUnless(NODE, "node runs the viewer scripts")
class FixedPhaseReviewTests(GraphCardsCase):
    def test_a_fixed_and_approved_spec_review_ends_with_a_check(self):
        """[GRAPH-FIXED-PHASE-REVIEW]: sae-findings-docs: REVIEW-SPEC said changes-required, the spec was fixed and
        approved, no later round: ✓ in the pass color, tooltip "changes required, fixed, approved <date>"."""
        sb = self.sandbox()
        self.copy_done(sb, FINDINGS_DOCS)
        out = self.cards(sb, FINDINGS_DOCS)
        review = next(r for r in card(out, "@shape")["rows"] if r["id"] == "REVIEW-SPEC")
        self.assertEqual((review["g"], review["tone"]), ("✓", "pass"))
        self.assertRegex(review["tip"], r"^REVIEW-SPEC · changes required, fixed, approved \w{3} \d+ \d\d:\d\d")
        # job cards keep their grey ✕ under a later passing round ([GRAPH-JOB-CARD])
        self.assertEqual([g for _, g, _ in [(r["label"], r["g"], r["tone"]) for r in card(out, "FINDINGS-RESOLVE")["rows"]]],
                         ["✕", "●", "✓"])

    def test_a_later_round_keeps_the_grey_cross(self):
        """[GRAPH-FIXED-PHASE-REVIEW]: a changes-required round with a later round keeps today's grey ✕."""
        jobs = {"REVIEW-SPEC": job("review", "done", target="spec", verdict="changes-required"),
                "REVIEW-SPEC-2": job("review", "done", target="spec", verdict="pass")}
        t = task_data(jobs, phase="planning", events=[{"type": "job.added", "job": "REVIEW-SPEC", "kind": "review"},
                                                      {"type": "job.added", "job": "REVIEW-SPEC-2", "kind": "review"},
                                                      {"type": "spec.approved", "by": "owner", "at": "2026-10-13T10:00:00Z"}])
        out = page("var c = graph(T()).cards.find(c => c.id === '@shape'); return c.rows.map(r => [r.id, r.g, r.tone])", index(), t)
        self.assertEqual(out, [["REVIEW-SPEC", "✕", "mut"], ["REVIEW-SPEC-2", "✓", "pass"]])
        # without the approval the open round stays red
        t["events"] = t["events"][:1]
        t["state"]["jobs"] = {"REVIEW-SPEC": jobs["REVIEW-SPEC"]}
        t["state"]["task"]["phase"] = "shaping"
        out = page("var c = graph(T()).cards.find(c => c.id === '@shape'); return c.rows.map(r => [r.id, r.g, r.tone])", index(), t)
        self.assertEqual(out, [["REVIEW-SPEC", "✕", "fail"]])


if __name__ == "__main__":
    unittest.main()
