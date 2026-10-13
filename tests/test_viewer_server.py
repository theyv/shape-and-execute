"""The viewer server: start and reuse, security, idle stop, live task data, writes through `sae`.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [VIEWER-SERVER], [VIEWER-ALL-WORKTREES], [VIEWER-LINK-AT-NEW], [VIEWER-NEXT-UP],
[EDGE-NO-SOCKETS]. Every server runs on a port the OS picks, with its state in the sandbox
(SAE_STATE_DIR); tearDown stops it and checks that no process is left.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from saetest import SAE, SCRIPTS, SKILL_DIR, SaeTestCase, Sandbox
from test_reviews import ReviewFlowCase
from test_task_worktree import plan

sys.path.insert(0, str(SCRIPTS))


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # a zombie child of nobody is gone for our purpose; `ps` tells
    out = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(out) and not out.startswith("Z")


def request(port: int, method: str, path: str, body=None, headers=None, host: str | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    sent = {"Host": host or f"127.0.0.1:{port}", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        sent.setdefault("Content-Type", "application/json")
    conn.request(method, path, body=data, headers=sent)
    response = conn.getresponse()
    raw = response.read()
    conn.close()
    kind = response.getheader("Content-Type") or ""
    return response.status, (json.loads(raw) if kind.startswith("application/json") else raw), \
        {k.lower(): v for k, v in response.getheaders()}


class ViewerServerCase(SaeTestCase):
    """A sandbox whose viewer server tearDown stops; helpers for its routes."""

    def sandbox(self, idle: str | None = "60", **kwargs) -> Sandbox:
        sb = super().sandbox(**kwargs)
        if idle is not None:  # None: the built-in four hours, as for the owner
            sb.env["SAE_VIEWER_IDLE_S"] = idle
        self.sb = sb
        return sb

    def tearDown(self):
        sb = getattr(self, "sb", None)
        if sb is not None:
            pid_file = sb.viewer_state / "viewer.pid"
            pid = json.loads(pid_file.read_text())["pid"] if pid_file.exists() else None
            subprocess.run([sys.executable, str(SAE), "view", "--stop"], env=sb.env, cwd=sb.repo, capture_output=True)
            for started in getattr(self, "pids", set()) | ({pid} if pid else set()):
                deadline = time.time() + 5
                while alive(started) and time.time() < deadline:
                    time.sleep(0.05)
                if alive(started):
                    os.kill(started, signal.SIGKILL)
                    self.fail(f"viewer server {started} outlived its test")
        super().tearDown()

    def view(self, sb: Sandbox, *args, cwd: Path | None = None) -> dict:
        data = sb.json("view", *args, cwd=cwd)
        self.pids = getattr(self, "pids", set()) | {data["pid"]}
        return data

    def token(self, port: int) -> str:
        status, page, headers = request(port, "GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("frame-ancestors 'none'", headers["content-security-policy"])
        return re.search(rb'<meta name="sae-token" content="([^"]+)">', page).group(1).decode()

    def post(self, port: int, route: str, body: dict, token: str, origin: str | None = None):
        return request(port, "POST", f"/api/{route}", body,
                       {"X-SAE-Token": token, "Origin": origin or f"http://127.0.0.1:{port}"})

    def second_repo(self, sb: Sandbox) -> Path:
        other = sb.tmp / "other-repo"
        other.mkdir()
        for args in (["init", "-q", "-b", "main"], ["config", "core.hooksPath", str(sb.hooks)],
                     ["commit", "-q", "--allow-empty", "-m", "init"]):
            sb.git(*args, cwd=other)
        return other


class ViewerServerTests(ViewerServerCase):
    # ------------------------------------------------------------ start and reuse

    def test_second_view_from_another_repository_reuses_the_server_and_opens_its_project(self):
        sb = self.sandbox()
        task = sb.new_task("First", "first")
        one = self.view(sb, "first")
        other = self.second_repo(sb)
        two = self.view(sb, cwd=other)
        self.assertEqual((one["pid"], one["port"]), (two["pid"], two["port"]))
        self.assertNotEqual(one["repo"], two["repo"])
        self.assertTrue(one["url"].startswith(f"http://127.0.0.1:{one['port']}/#repo={one['repo']}&task={task}"))
        self.assertIn(f"#repo={two['repo']}", two["url"])
        status, projects, _ = request(one["port"], "GET", "/api/projects")
        self.assertEqual(status, 200)
        self.assertEqual({p["key"] for p in projects["projects"]}, {one["repo"], two["repo"]})
        for name in ("viewer.json", "viewer.pid", "repos.json"):
            self.assertEqual((sb.viewer_state / name).stat().st_mode & 0o777, 0o600, name)

    def test_writing_commands_make_the_repository_known_and_read_only_ones_do_not(self):
        sb = self.sandbox()
        sb.sae("status")
        self.assertFalse((sb.viewer_state / "repos.json").exists())
        sb.new_task("Known", "known")
        repos = json.loads((sb.viewer_state / "repos.json").read_text())["repos"]
        self.assertEqual([r["path"] for r in repos], [str(sb.repo.resolve())])

    def test_new_prints_the_viewer_link_or_the_start_command(self):
        sb = self.sandbox()
        out = sb.sae("new", "Off", "--slug", "off").stdout
        self.assertRegex(out, r"Viewer:\n  cd .+ && python3 .+sae\.py view \S+--off --open")
        del sb.env["SAE_VIEWER"]
        data = sb.json("new", "Linked", "--slug", "linked")
        self.assertRegex(data["viewer"], rf"^http://127\.0\.0\.1:\d+/#repo=\w+&task={data['task']}&tab=plan$")
        self.pids = {json.loads((sb.viewer_state / "viewer.pid").read_text())["pid"]}

    def test_server_starts_without_the_idle_variable(self):
        sb = self.sandbox(idle=None)
        self.assertNotIn("SAE_VIEWER_IDLE_S", sb.env)
        data = self.view(sb)
        self.assertTrue(alive(data["pid"]))
        self.assertEqual(request(data["port"], "GET", "/api/health")[1]["pid"], data["pid"])

    def test_a_startup_failure_removes_the_pid_file(self):
        from sae_lib import server
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"SAE_STATE_DIR": tmp}), \
                mock.patch.object(server, "idle_limit", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                server.serve()
            self.assertTrue((Path(tmp) / "viewer.json").exists())
            self.assertFalse((Path(tmp) / "viewer.pid").exists())

    @unittest.skipUnless(shutil.which("sandbox-exec"), "macOS sandbox-exec simulates a sandbox without sockets")
    def test_a_sandbox_without_sockets_or_state_folder_gets_the_start_command(self):
        sb = self.sandbox()
        task = sb.new_task("Boxed", "boxed")
        state = os.path.realpath(sb.viewer_state)
        before = {p.name: p.read_bytes() for p in sb.viewer_state.iterdir()}
        for profile in (f'(version 1)(allow default)(deny network-bind)(deny file-write* (subpath "{state}"))',
                        f'(version 1)(allow default)(deny file-write* (subpath "{state}"))'):
            proc = subprocess.run(["sandbox-exec", "-p", profile, "python3", str(SAE), "view", "boxed"],
                                  cwd=sb.repo, env=sb.env, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertIn(f"view {task} --open", proc.stderr)
            self.assertEqual({p.name: p.read_bytes() for p in sb.viewer_state.iterdir()}, before)

    @unittest.skipUnless(shutil.which("sandbox-exec"), "macOS sandbox-exec simulates a sandbox without sockets")
    def test_without_local_sockets_view_exits_1_with_the_start_command(self):
        sb = self.sandbox()
        task = sb.new_task("Boxed", "boxed")
        proc = subprocess.run(["sandbox-exec", "-p", "(version 1)(allow default)(deny network-bind)",
                               "python3", str(SAE), "view", "boxed"], cwd=sb.repo, env=sb.env,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn(f"view {task} --open", proc.stderr)
        self.assertFalse((sb.viewer_state / "viewer.pid").exists())

    # ------------------------------------------------------------ security

    def test_changes_need_the_token_and_the_same_origin(self):
        sb = self.sandbox()
        sb.new_task("Guarded", "guarded")
        port = self.view(sb)["port"]
        token = self.token(port)
        body = {"repo": self.view(sb)["repo"], "task": "guarded", "pairs": ["execution=economy"]}
        self.assertEqual(request(port, "POST", "/api/set", body, {"Origin": f"http://127.0.0.1:{port}"})[0], 403)
        self.assertEqual(self.post(port, "set", body, "x" * len(token))[0], 403)
        self.assertEqual(self.post(port, "set", body, token, origin="http://evil.example")[0], 403)
        self.assertEqual(request(port, "POST", "/api/set", body, {"X-SAE-Token": token})[0], 403)  # no Origin
        self.assertEqual(request(port, "GET", "/api/projects", host=f"evil.example:{port}")[0], 403)
        status, _, headers = request(port, "OPTIONS", "/api/set", None, {"Origin": "http://evil.example"})
        self.assertEqual(status, 405)
        self.assertNotIn("access-control-allow-origin", headers)
        self.assertEqual(json.loads((sb.task_dir(sb.json("status", "guarded")["task"]) / "settings.json")
                                    .read_text())["levels"]["execution"], "balanced")
        status, answer, _ = self.post(port, "set", body, token, origin=f"http://localhost:{port}")
        self.assertEqual(status, 403, "Origin must match the Host the page was loaded from")
        status, answer, _ = request(port, "POST", "/api/set", body, {"X-SAE-Token": token,
                                                                     "Origin": f"http://localhost:{port}"},
                                    host=f"localhost:{port}")
        self.assertEqual((status, answer["ok"]), (200, True))

    # ------------------------------------------------------------ idle stop and restart

    def test_idle_server_stops_removes_its_pid_file_and_restarts_on_the_same_port_and_token(self):
        sb = self.sandbox(idle="1")
        first = self.view(sb)
        token = self.token(first["port"])
        deadline = time.time() + 15
        while alive(first["pid"]) and time.time() < deadline:
            time.sleep(0.1)
        self.assertFalse(alive(first["pid"]), "the server outlived its idle limit")
        self.assertFalse((sb.viewer_state / "viewer.pid").exists())
        sb.env["SAE_VIEWER_IDLE_S"] = "60"
        second = self.view(sb)
        self.assertNotEqual(second["pid"], first["pid"])
        self.assertEqual(second["port"], first["port"])
        self.assertEqual(self.token(second["port"]), token)

    def test_stop(self):
        sb = self.sandbox()
        pid = self.view(sb)["pid"]
        self.assertTrue(sb.json("view", "--stop")["stopped"])
        self.assertFalse(alive(pid))
        self.assertFalse(sb.json("view", "--stop")["stopped"])

    # ------------------------------------------------------------ data

    def test_task_data_comes_live_from_the_task_worktree_and_the_done_folder(self):
        sb = self.sandbox()
        running = plan(sb, "running", [("ONE", ""), ("TWO", "ONE")])
        sb.sae("start", "running")
        old = sb.new_task("Old one", "old-one")
        (sb.repo / ".tasks" / "done").mkdir()
        shutil.move(str(sb.repo / ".tasks" / old), str(sb.repo / ".tasks" / "done" / old))
        proto = sb.task_worktree(running) / ".tasks" / running / "prototypes"
        (proto / "demo").mkdir(parents=True)
        (proto / "page.html").write_text("<p>proto</p>")
        (proto / "demo" / "index.html").write_text('<link rel="stylesheet" href="style.css"><p>demo</p>')
        (proto / "demo" / "style.css").write_text("p { color: red }")
        view = self.view(sb, cwd=sb.task_worktree(running))   # opened from the task worktree: same project
        port, key = view["port"], view["repo"]
        self.assertEqual(key, self.view(sb)["repo"])
        status, repo, _ = request(port, "GET", f"/api/repo?repo={key}")
        self.assertEqual(status, 200)
        where = {t["id"]: (t["location"], t["location_path"]) for t in repo["tasks"]}
        self.assertEqual(where[running], ("task worktree", str(sb.task_worktree(running))))
        self.assertEqual(where[old][0], "done")
        status, task, _ = request(port, "GET", f"/api/task?repo={key}&task={running}")
        self.assertEqual(status, 200)
        self.assertEqual(task["state"]["task"]["phase"], "executing")
        self.assertEqual(task["worktree"], str(sb.task_worktree(running)))
        self.assertEqual([r["id"] for r in task["next"]["ready"]], ["ONE"])     # as `sae next`
        self.assertEqual([r["id"] for r in sb.json("next", "running")["ready"]], ["ONE"])
        self.assertEqual((task["routing"]["ONE"]["model"], task["routing"]["ONE"]["effort"]), ("c-mid", "low"))
        self.assertIn("ONE", task["review_marks"])
        protos = {p["path"]: p["url"] for p in task["prototypes"]}
        self.assertEqual(list(protos), ["prototypes/demo/index.html", "prototypes/demo/style.css",
                                        "prototypes/page.html"])
        self.assertIn("claude", task["models"])
        status, body, headers = request(port, "GET", protos["prototypes/page.html"])
        self.assertEqual((status, body), (200, b"<p>proto</p>"))
        self.assertTrue(headers["content-security-policy"].startswith("sandbox"))
        # a prototype's relative asset resolves, as in a browser, to a file the server serves
        page = protos["prototypes/demo/index.html"]
        css = urllib.parse.urljoin(page, re.search(rb'href="([^"]+)"', request(port, "GET", page)[1]).group(1).decode())
        status, body, headers = request(port, "GET", css)
        self.assertEqual((status, body, headers["content-type"].split(";")[0]), (200, b"p { color: red }", "text/css"))
        self.assertTrue(headers["content-security-policy"].startswith("sandbox"))
        base = page.rsplit("/", 2)[0]
        for bad in (f"{base}/../state.json", f"{base}/%2e%2e/state.json", f"{base}/demo/../../state.json",
                    f"/proto/{key}/nope/page.html", f"/proto/nope/{running}/page.html"):
            self.assertEqual(request(port, "GET", bad)[0], 404, bad)
        # a folder's index.html that is a symlink out of prototypes/ is not served either
        (proto / "out").mkdir()
        (proto / "out" / "index.html").symlink_to(proto.parent / "state.json")
        self.assertEqual(request(port, "GET", f"{base}/out/")[0], 404)
        status, done, _ = request(port, "GET", f"/api/task?repo={key}&task={old}")
        self.assertEqual((status, done["location"]), (200, "done"))
        self.assertEqual(request(port, "GET", "/api/repo?repo=nope")[0], 404)

    def test_settings_written_in_the_viewer_show_in_status(self):
        sb = self.sandbox()
        task = sb.new_task("Tuned", "tuned")
        view = self.view(sb, "tuned")
        port, key = view["port"], view["repo"]
        token = self.token(port)
        status, answer, _ = self.post(port, "set", {"repo": key, "task": "tuned", "pairs": ["execution=cheap"]}, token)
        self.assertEqual((status, answer["ok"], answer["code"]), (422, False, 1))
        self.assertIn("levels.execution", answer["error"])
        status, answer, _ = self.post(port, "set", {"repo": key, "task": "tuned", "pairs": ["execution=economy"]}, token)
        self.assertEqual((status, answer["ok"]), (200, True))
        self.assertEqual(sb.json("status", "tuned")["settings"]["levels"]["execution"], "economy")
        last = sb.events(task)[-1]
        self.assertEqual((last["type"], last["by"]), ("settings.changed", "viewer"))
        self.assertEqual(self.post(port, "set", {"repo": key, "task": "tuned", "pairs": ["--harness"]}, token)[0], 400)
        status, settings, _ = request(port, "GET", f"/api/settings?repo={key}&task={task}")
        self.assertEqual(settings["sources"]["levels.execution"], "task")
        self.assertEqual(settings["sources"]["interaction"], "global")
        self.assertEqual(settings["routing"]["claude"]["tiers"]["L2"]["source"], "global")
        status, answer, _ = self.post(port, "project-set", {"repo": key, "pairs": ["execution=premium"]}, token)
        self.assertEqual((status, answer["ok"]), (200, True), answer)
        self.assertEqual(sb.json("project", "show")["values"], {"execution": "premium"})

    def test_a_hold_set_in_the_viewer_stops_the_next_dispatch(self):
        """[VIEWER-NEXT-UP], [HOLD-AFTER-JOB]: the hold route runs `sae hold`; dispatch refuses."""
        sb = self.sandbox()
        task = plan(sb, "held", [("ONE", ""), ("TWO", "ONE")])
        sb.sae("start", "held")
        view = self.view(sb, "held")
        port, key, token = view["port"], view["repo"], self.token(view["port"])
        self.assertEqual(self.post(port, "hold", {"repo": key, "task": "held", "job": "--release"}, token)[0], 400)
        status, answer, _ = self.post(port, "hold", {"repo": key, "task": "held", "job": "ONE",
                                                     "reason": "look first"}, token)
        self.assertEqual((status, answer["ok"]), (200, True), answer)
        self.assertEqual(answer["command"], "sae hold held ONE --reason look first")
        last = sb.events(task)[-1]
        self.assertEqual((last["type"], last["job"]), ("hold.set", "ONE"))
        status, data, _ = request(port, "GET", f"/api/task?repo={key}&task={task}")
        self.assertEqual([h["job"] for h in data["next"]["holds"]], ["ONE"])
        ws = Path(sb.json("dispatch", "held", "ONE")["workspace"])
        sb.work(ws, "one.txt", "one\n", "ONE: work")
        sb.result(task, "jobs/ONE.result.md", status="done", summary="ok", validation="pass", changes="made")
        sb.sae("collect", "held", "ONE")
        refused = sb.sae("dispatch", "held", "TWO", code=3).stderr
        self.assertIn("--release", refused)
        status, answer, _ = self.post(port, "hold", {"repo": key, "task": "held", "job": "ONE", "release": True}, token)
        self.assertEqual((status, answer["ok"]), (200, True), answer)
        self.assertEqual([r["id"] for r in sb.json("next", "held")["ready"]], ["TWO"])

# app.js in node with a stub DOM and a fetch whose answers the test releases one by one
SWITCH_RACE_JS = r"""
const vm = require("vm"), fs = require("fs");
const el = () => new Proxy({innerHTML: "", hidden: true, scrollTop: 0, dataset: {}, style: {},
  classList: {toggle() {}, contains() { return false }, add() {}, remove() {}},
  addEventListener() {}, querySelectorAll() { return [] }, focus() {}, appendChild() {}, closest() { return null }},
  {get: (t, k) => k in t ? t[k] : () => null});
const pending = [];
const answer = (url) => { const i = pending.findIndex(p => p.url.startsWith(url)); if (i < 0) throw new Error("no request " + url + " in " + pending.map(p => p.url));
  return pending.splice(i, 1)[0] };
const ctx = {console, setTimeout: () => 0, clearTimeout() {}, setInterval() {}, addEventListener() {}, history: {replaceState() {}},
  location: {hash: "#repo=A"}, localStorage: {getItem() { return null }, setItem() {}},
  fetch: (url) => new Promise(resolve => pending.push({url, resolve})),
  document: {hidden: false, title: "", documentElement: {dataset: {}}, body: el(), activeElement: null,
    querySelector: el, querySelectorAll: () => [], addEventListener() {}, createElement: el}};
ctx.window = ctx; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), ctx);
const reply = (p, data) => p.resolve({ok: true, status: 200, json: () => Promise.resolve(data)});
const tick = () => new Promise(r => setImmediate(r));
const projects = {version: "p1", projects: [{key: "A", name: "a", path: "/a"}, {key: "B", name: "b", path: "/b"}]};
const repo = (k) => ({version: "v" + k, key: k, repo: k, root: "/" + k, sae: "sae", findings: [], backlog: [],
  tasks: [{id: "task-" + k, title: k, phase: "executing"}]});
(async () => {
  vm.runInContext("readHash(); poll()", ctx);
  reply(answer("/api/projects"), projects); await tick(); await tick();
  const slowA = answer("/api/repo?repo=A");                  // A is still loading when the owner picks B
  vm.runInContext('go({repo: "B", task: null, job: null, bl: null})', ctx);
  reply(answer("/api/projects"), projects); await tick(); await tick();
  reply(answer("/api/repo?repo=B"), repo("B")); await tick(); await tick();
  reply(slowA, repo("A")); await tick(); await tick();       // A answers last
  console.log(JSON.stringify(vm.runInContext("({selected: S.repo, rendered: IDX && IDX.key, task: S.task})", ctx)));
})().catch(e => { console.error(e); process.exit(2) });
"""


# app.js and task-views.js in node: the Plan graph of a task shaped like the pilot-project case
GRAPH_JS = r"""
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
console.log(JSON.stringify(vm.runInContext(`readHash(); IDX = {sae: "sae", tasks: []};
  var g = graph(TASK), svg = g.svg;
  ({tab: S.tab, edges: g.edges.map(e => e.slice(0, 3)),
    marks: ["no review · forced by settings", "review · forced by settings"].filter(m => svg.includes(">" + m + "<")),
    planned: /class="nd k-planned[^"]*planned"[^>]*aria-label="REVIEW-INTEGRATION/.test(svg),
    override: svg.includes("override")})`, ctx)));
"""


# app.js and task-views.js in node: a live refresh re-renders #main; the graph box keeps its scroll
REFRESH_JS = r"""
const vm = require("vm"), fs = require("fs");
const el = () => new Proxy({innerHTML: "", hidden: true, scrollTop: 0, scrollLeft: 0, dataset: {}, style: {},
  classList: {toggle() {}, contains() { return false }}, querySelectorAll() { return [] }},
  {get: (t, k) => k in t ? t[k] : () => null});
let gwrap = null;  // the browser's .gwrap: a new element whenever #main gets new HTML
const main = new Proxy(el(), {set(t, k, v) { t[k] = v; if (k === "innerHTML") { const m = /class="gwrap" data-task="([^"]*)"/.exec(v);
  gwrap = m ? el() : null; if (m) gwrap.dataset.task = m[1] } return true }});
const els = {};
const ctx = {console, setTimeout: () => 0, clearTimeout() {}, setInterval() {}, addEventListener() {}, history: {replaceState() {}},
  location: {hash: ""}, localStorage: {getItem() { return null }, setItem() {}},
  document: {hidden: false, title: "", documentElement: {dataset: {}}, body: el(), activeElement: null,
    querySelector: (s) => s === "#main" ? main : s === ".gwrap" ? gwrap : (els[s] = els[s] || el()),
    querySelectorAll: () => [], addEventListener() {}, createElement: el}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 5)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
ctx.TASK = JSON.parse(fs.readFileSync(process.argv[5], "utf8"));
vm.runInContext(`readHash(); IDX = {sae: "sae", tasks: [{id: "t", title: "t", phase: "executing"}]};
  S.task = "t"; TASKS.t = TASK; render()`, ctx);
vm.runInContext("GV.t = {x: -640, y: -30, k: 0.5}; render()", ctx);
const kept = /class="gv" transform="([^"]*)"/.exec(main.innerHTML);
console.log(JSON.stringify(vm.runInContext(`({kept: ${JSON.stringify(kept && kept[1])}, view: GV.t,
  fit: gvFit(1032, 400, 2000, 368), zoom: gvZoom({x: 0, y: 0, k: 1}, 100, 50, 2), min: gvZoom({x: 0, y: 0, k: 0.25}, 0, 0, 0.1).k,
  layer: (({VERIFY, VERDICT, LATE}) => ({VERIFY, VERDICT, LATE}))(graph(TASK).layer)})`, ctx)));
"""


def run_node(script_text: str, *viewer_files: str, data=None, args=()) -> dict:
    """Run a node script over viewer files (argv[2:]: the files, then the JSON data file, then args)."""
    viewer = SKILL_DIR / "assets" / "viewer"
    with tempfile.TemporaryDirectory() as tmp:
        script, path = Path(tmp) / "page.js", Path(tmp) / "data.json"
        script.write_text(script_text)
        path.write_text(json.dumps(data))
        proc = subprocess.run(["node", str(script), *(str(viewer / f) for f in viewer_files), str(path), *args],
                              capture_output=True, text=True, timeout=30)
    if proc.returncode:
        raise AssertionError(proc.stderr)
    return json.loads(proc.stdout.strip().splitlines()[-1])


# app.js and task-views.js in node: status, waiting reasons and the node tooltip of one job
GRAPH_STATUS_JS = r"""
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
ctx.ID = process.argv[5];
console.log(JSON.stringify(vm.runInContext(`readHash(); IDX = {sae: "sae", tasks: []};
  var w = waits(TASK, ID), svg = graph(TASK).svg;
  ({status: stOf(TASK, ID), waits: w, tip: !!w.length && svg.includes(esc("Waits for: " + w.join("; ")))})`, ctx)));
"""


# app.js and settings.js in node: saves queued for project A leave for A after a switch to B
QUEUED_WRITE_JS = r"""
const vm = require("vm"), fs = require("fs");
const el = () => new Proxy({innerHTML: "", hidden: true, scrollTop: 0, dataset: {}, style: {},
  classList: {toggle() {}, contains() { return false }, add() {}, remove() {}},
  addEventListener() {}, querySelectorAll() { return [] }, focus() {}, appendChild() {}, closest() { return null }},
  {get: (t, k) => k in t ? t[k] : () => null});
const sent = [];
const ctx = {console, setTimeout: () => 0, clearTimeout() {}, setInterval() {}, addEventListener() {}, history: {replaceState() {}},
  location: {hash: ""}, localStorage: {getItem() { return null }, setItem() {}},
  fetch: (url, opt) => new Promise(resolve => sent.push({url, body: opt && opt.body, resolve})),
  document: {hidden: false, title: "", documentElement: {dataset: {}}, body: el(), activeElement: null,
    querySelector: el, querySelectorAll: () => [], addEventListener() {}, createElement: el}};
ctx.window = ctx; vm.createContext(ctx);
for (const f of process.argv.slice(2, 5)) vm.runInContext(fs.readFileSync(f, "utf8"), ctx);
const tick = () => new Promise(r => setImmediate(r));
const posts = () => sent.filter(p => p.body);
(async () => {
  vm.runInContext(`S.repo = "A"; S.task = "task-A";
    sxSave("project", ["execution=max"]); sxSave("project", ["review=spec"]); sxSave("task", ["execution=economy"])`, ctx);
  await tick();
  vm.runInContext(`S.repo = "B"; S.task = "task-B"`, ctx);  // the owner switches while two saves wait
  for (let n = 0; n < 3; n++) {
    const p = posts()[n];
    if (!p) throw new Error("missing POST " + n + " in " + sent.map(x => x.url));
    p.resolve({ok: true, status: 200, json: () => Promise.resolve({ok: true})});
    for (let k = 0; k < 4; k++) await tick();
  }
  console.log(JSON.stringify(posts().map(p => [p.url, JSON.parse(p.body)])));
})().catch(e => { console.error(e); process.exit(2) });
"""

def job(kind, needs=(), status="done", **extra):
    return {"kind": kind, "needs": list(needs), "difficulty": "normal", "review": False, "final": False, "fix_of": None,
            "target": None, "status": status, "merged": status == "done" and kind in ("implementation", "integration"),
            "attempts": [], "commits": [], "last_change": "2026-10-08T15:00:00+02:00", **extra}


def pilot_project_task(old_sae: bool) -> dict:
    """The pilot-project graph: two flagged writers without selected-jobs, an integration job, the
    final validation; with the old sae the integration review was added without needs."""
    writers = ["VERDICT", "STAGE-SCRIPTS", "DOC-INDEX", "SCAN-CHECKS"]
    jobs = {"VERIFY": job("research"),
            **{w: job("implementation", ["VERIFY"], review=w in ("VERDICT", "STAGE-SCRIPTS")) for w in writers},
            "FINDINGS-CLOSE": job("integration", writers),
            "FINAL-VALIDATION": job("validation", ["FINDINGS-CLOSE"], status="pending", final=True)}
    events = [{"type": "job.added", "job": k, "kind": j["kind"], "needs": j["needs"]} for k, j in jobs.items()]
    events.append({"type": "plan.approved", "by": "owner"})
    review_needs = [] if old_sae else writers + ["FINDINGS-CLOSE"]
    jobs["REVIEW-INTEGRATION"] = job("review", review_needs, target="integration", generated=not old_sae)
    events.append({"type": "job.added", "job": "REVIEW-INTEGRATION", "kind": "review", "needs": review_needs, "by": "sae"})
    marks = {w: {"mark": "no review · forced by settings", "reviewed": False, "forced": True, "reason": "flagged"}
             for w in ("VERDICT", "STAGE-SCRIPTS")}
    if not old_sae:  # the new sae puts the final validation after the review, with a generated edge
        final = jobs["FINAL-VALIDATION"]
        final["needs"], final["generated_needs"] = ["FINDINGS-CLOSE", "REVIEW-INTEGRATION"], ["REVIEW-INTEGRATION"]
        events.append({"type": "job.changed", "job": "FINAL-VALIDATION", "by": "sae",
                       "changes": {"needs": [["FINDINGS-CLOSE"], final["needs"]]}})
        marks["DOC-INDEX"] = {"mark": "review · forced by settings", "reviewed": True, "forced": True, "reason": "all-jobs"}
    return {"state": {"task": {"id": "t", "phase": "executing", "git": True, "layout": "worktrees"}, "jobs": jobs},
            "events": events, "files": {}, "review_marks": marks, "models": {"claude": [{"model": "c-mid", "efforts": ["low"]}]},
            "routing": {"FINAL-VALIDATION": {"harness": "claude", "model_entry": "c-mid", "model": "c-mid", "effort": "low",
                                             "override": {"model": "c-mid"}, "routed": None, "source": "override"}},
            "planned_reviews": []}


class ViewerReadinessTests(ViewerServerCase, ReviewFlowCase):
    @unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
    def test_the_graph_shows_the_readiness_sae_computes(self):
        """[VIEWER-NEXT-UP], [HOLD-AFTER-JOB], [FIX-REVIEW-NO-DEADLOCK]: /api/task carries the waiting
        reasons of `sae next`; the graph shows them, with no rules of its own."""
        sb = self.sandbox()
        # an active hold after ONE: TWO waits, although its need is done and merged
        held = plan(sb, "held", [("ONE", ""), ("TWO", "ONE")])
        sb.sae("start", "held")
        sb.sae("hold", "held", "ONE", "--reason", "look first")
        self.run_writer(sb, held, "held", "ONE")
        # a second changes-required integration round parks the task: FINAL waits
        parked = self.integration_task(sb, "parked")
        sb.sae("set", "parked", "max-review-rounds=2")
        self.review(sb, parked, "parked", "REVIEW-INTEGRATION", "integration", "changes-required")
        sb.sae("job", "add", "parked", "INTEGRATION-FIX-1", "--kind", "implementation",
               "--fix-of", "REVIEW-INTEGRATION", "--reason", "finding 1")
        sb.job_file(parked, "INTEGRATION-FIX-1")
        self.run_writer(sb, parked, "parked", "INTEGRATION-FIX-1")
        self.review(sb, parked, "parked", "REVIEW-INTEGRATION-2", "integration", "changes-required")
        # a job review after its done, unmerged fix job: ready
        fixed = self.planned(sb, "fixed", [("CORE", "implementation", "", ["--review"]), ("SIDE", "implementation", "", [])],
                             settings=["review=selected-jobs"])
        self.assertEqual(sb.json("status", "fixed")["layout"], "worktrees")
        self.run_writer(sb, fixed, "fixed", "CORE")
        self.review(sb, fixed, "fixed", "REVIEW-CORE", "CORE", "changes-required")
        sb.sae("job", "add", "fixed", "CORE-FIX-1", "--kind", "implementation", "--fix-of", "CORE", "--reason", "fix")
        sb.job_file(fixed, "CORE-FIX-1")
        self.run_writer(sb, fixed, "fixed", "CORE-FIX-1")
        self.assertFalse(sb.state(fixed)["jobs"]["CORE-FIX-1"]["merged"])
        view = self.view(sb, "held")
        cases = [(held, "TWO", "pending", "hold after ONE"),
                 (parked, "FINAL", "pending", "the task is parked: REVIEW-INTEGRATION-2 requires changes again"),
                 (fixed, "REVIEW-CORE-2", "ready", None)]
        for task, job_id, status, reason in cases:
            with self.subTest(job=job_id):
                code, data, _ = request(view["port"], "GET", f"/api/task?repo={view['repo']}&task={task}")
                self.assertEqual(code, 200)
                cli = sb.json("next", task)
                self.assertEqual(job_id in [r["id"] for r in cli["ready"]], status == "ready")
                if reason:
                    self.assertIn(reason, data["waits"][job_id])
                out = run_node(GRAPH_STATUS_JS, "app.js", "task-views.js", data=data, args=[job_id])
                self.assertEqual(out["status"], status, out)
                self.assertEqual(out["waits"], data["waits"][job_id])
                if reason:
                    self.assertTrue(out["tip"], "the node's tooltip names what it waits for")

class ViewerPageTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
    def test_plan_graph_places_the_integration_review_and_shows_effective_marks(self):
        """[GENERATED-JOB-EDGES], [JOB-REVIEW-FLAG-HONESTY], [VIEWER-PLAN-FIRST], [JOB-MODEL-OVERRIDE]."""
        viewer = SKILL_DIR / "assets" / "viewer"
        for old_sae in (True, False):
            with tempfile.TemporaryDirectory() as tmp:
                script, data = Path(tmp) / "graph.js", Path(tmp) / "task.json"
                script.write_text(GRAPH_JS)
                data.write_text(json.dumps(pilot_project_task(old_sae)))
                proc = subprocess.run(["node", str(script), str(viewer / "app.js"), str(viewer / "task-views.js"), str(data)],
                                      capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout.strip().splitlines()[-1])
            self.assertEqual(out["tab"], "plan")  # a task opens on Plan
            edges = {(a, b): cls for a, b, cls in out["edges"]}
            # after the last writer only (the others reach it through FINDINGS-CLOSE), then the final validation
            self.assertEqual(edges.get(("FINDINGS-CLOSE", "REVIEW-INTEGRATION")), "gen", out)
            self.assertNotIn(("VERDICT", "REVIEW-INTEGRATION"), edges)
            self.assertEqual(edges.get(("REVIEW-INTEGRATION", "FINAL-VALIDATION")), "gen", out)
            self.assertFalse([e for e, cls in edges.items() if "new" in cls.split()], "generated edges are no plan change")
            self.assertIn("no review · forced by settings", out["marks"])
            self.assertEqual("review · forced by settings" in out["marks"], not old_sae)
            self.assertTrue(out["override"])

    @unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
    def test_planned_integration_review_is_a_planned_node_before_the_final_validation(self):
        """[GENERATED-JOB-EDGES]: a review sae will add is drawn in its final place, dotted."""
        task = pilot_project_task(True)
        del task["state"]["jobs"]["REVIEW-INTEGRATION"]
        task["planned_reviews"] = [{"id": "REVIEW-INTEGRATION", "target": "integration", "round": 1,
                                    "needs": ["VERDICT", "STAGE-SCRIPTS", "DOC-INDEX", "SCAN-CHECKS", "FINDINGS-CLOSE"],
                                    "needed_by": ["FINAL-VALIDATION"], "harness": "claude", "model": "c-mid", "effort": "low"}]
        viewer = SKILL_DIR / "assets" / "viewer"
        with tempfile.TemporaryDirectory() as tmp:
            script, data = Path(tmp) / "graph.js", Path(tmp) / "task.json"
            script.write_text(GRAPH_JS)
            data.write_text(json.dumps(task))
            proc = subprocess.run(["node", str(script), str(viewer / "app.js"), str(viewer / "task-views.js"), str(data)],
                                  capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout.strip().splitlines()[-1])
        edges = {(a, b): cls for a, b, cls in out["edges"]}
        self.assertTrue(out["planned"])
        self.assertEqual(edges.get(("FINDINGS-CLOSE", "REVIEW-INTEGRATION")), "pl")
        self.assertEqual(edges.get(("REVIEW-INTEGRATION", "FINAL-VALIDATION")), "pl")


    @unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
    def test_the_plan_graph_canvas_keeps_its_view_fits_zooms_and_places_late_jobs(self):
        """[AMEND-4]: pan and zoom survive a refresh; fit, zoom around a point; late jobs' column."""
        viewer = SKILL_DIR / "assets" / "viewer"
        with tempfile.TemporaryDirectory() as tmp:
            script, data = Path(tmp) / "refresh.js", Path(tmp) / "task.json"
            script.write_text(REFRESH_JS)
            task = pilot_project_task(False)
            # LATE is added without needs while VERDICT runs; FINDINGS-CLOSE starts after it
            task["state"]["jobs"]["LATE"] = job("implementation", status="pending")
            task["events"] += [{"type": "job.dispatched", "job": "VERIFY"}, {"type": "job.dispatched", "job": "VERDICT"},
                               {"type": "job.added", "job": "LATE", "kind": "implementation", "needs": []},
                               {"type": "job.dispatched", "job": "FINDINGS-CLOSE"}]
            data.write_text(json.dumps(task))
            proc = subprocess.run(["node", str(script), *(str(viewer / f) for f in ("app.js", "task-views.js", "settings.js")), str(data)],
                                  capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(out["kept"], "translate(-640 -30) scale(0.5)")  # the new element gets the stored view
        self.assertEqual(out["view"], {"x": -640, "y": -30, "k": 0.5})
        self.assertEqual(out["fit"], {"x": 16, "y": 108, "k": 0.5})  # whole graph, centered
        self.assertEqual(out["zoom"], {"x": -100, "y": -50, "k": 2})  # the point under the pointer stays
        self.assertEqual(out["min"], 0.2)
        # planned without needs: first column; added later: the column of the rightmost dispatched job
        self.assertEqual(out["layer"], {"VERIFY": 0, "VERDICT": 1, "LATE": 1})

    @unittest.skipUnless(shutil.which("node"), "node runs app.js")
    def test_a_late_answer_for_the_previous_project_is_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "race.js"
            script.write_text(SWITCH_RACE_JS)
            proc = subprocess.run(["node", str(script), str(SKILL_DIR / "assets" / "viewer" / "app.js")],
                                  capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout.strip().splitlines()[-1]),
                         {"selected": "B", "rendered": "B", "task": "task-B"})


    @unittest.skipUnless(shutil.which("node"), "node runs the viewer scripts")
    def test_a_save_queued_for_one_project_goes_there_after_a_switch(self):
        """[VIEWER-SERVER], [PROJECT-DEFAULTS]: each queued write names the repository it was made for."""
        out = run_node(QUEUED_WRITE_JS, "app.js", "task-views.js", "settings.js")
        self.assertEqual(out, [["/api/project-set", {"repo": "A", "pairs": ["execution=max"]}],
                               ["/api/project-set", {"repo": "A", "pairs": ["review=spec"]}],
                               ["/api/set", {"repo": "A", "task": "task-A", "pairs": ["execution=economy"]}]])

if __name__ == "__main__":
    unittest.main()
