"""Tests of [WRITER-COMMAND], [LAUNCH-RECORD], [NO-SANDBOX-VISIBLE] and [HARNESS-FALLBACK]: jobs routed to
the harness that does not orchestrate get a COMMAND without a sandbox, the attempt records the launch,
a missing CLI refuses before any state change, and the fallback rule is printed for the case at hand.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests
Fake `codex` and `claude` executables on the PATH record their arguments and working folder and print
small outputs in the shapes the harnesses use; no real harness runs.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saetest import Sandbox, SaeTestCase, write_fake_clis  # noqa: E402

CODEX_EVENTS = [
    {"type": "thread.started", "thread_id": "t-1"},
    {"type": "turn.completed", "usage": {"input_tokens": 900, "cached_input_tokens": 800, "output_tokens": 40}},
    {"type": "turn.completed", "usage": {"input_tokens": 1100, "cached_input_tokens": 1000, "output_tokens": 60}},
]
CODEX_TOKENS = 900 + 40 + 1100 + 60
CLAUDE_OUTPUT = {"type": "result", "subtype": "success", "is_error": False, "result": "done",
                 "usage": {"input_tokens": 10, "cache_creation_input_tokens": 2000,
                           "cache_read_input_tokens": 5000, "output_tokens": 300}}
CLAUDE_TOKENS = 10 + 2000 + 5000 + 300
# Both fakes append {name, argv, cwd} to $FAKE_HARNESS_LOG, then print their harness's output.
RECORDING_CLI = (f"#!{sys.executable}\nimport json, os, sys\n"
                 "name = os.path.basename(sys.argv[0])\n"
                 "with open(os.environ['FAKE_HARNESS_LOG'], 'a') as log:\n"
                 "    log.write(json.dumps({'name': name, 'argv': sys.argv[1:], 'cwd': os.getcwd()}) + '\\n')\n"
                 "if name == 'codex':\n"
                 f"    for event in {CODEX_EVENTS!r}:\n"
                 "        print(json.dumps(event))\n"
                 "else:\n"
                 f"    print(json.dumps({CLAUDE_OUTPUT!r}))\n")
OTHER = {"claude": "codex", "codex": "claude"}


class LaunchTestCase(SaeTestCase):
    def sandbox_for(self, orchestrator: str, name: str = "", max_writers: int = 3, **kwargs) -> Sandbox:
        folder = self.tmp / (name or orchestrator)
        folder.mkdir()
        sb = Sandbox(folder, **kwargs)
        sb.env["SAE_HARNESS"] = orchestrator
        if max_writers != 3:
            config = json.loads(sb.config.read_text())
            config["parallel"]["max_writers"] = max_writers
            sb.config.write_text(json.dumps(config))
        return sb

    def executing(self, sb: Sandbox, slug: str, jobs=("ONE",), settings=()) -> str:
        task = sb.new_task(slug, slug)
        if settings:
            sb.sae("set", slug, *settings)
        for job_id in jobs:
            sb.sae("job", "add", slug, job_id, "--kind", "implementation")
            sb.job_file(task, job_id)
        sb.approve_plan(slug)
        sb.sae("start", slug)
        return task

    def to_other(self, sb: Sandbox, slug: str, job: str, orchestrator: str) -> None:
        sb.sae("job", "override", slug, job, "--harness", OTHER[orchestrator], "--reason", "owner's choice")

    def frozen(self, sb: Sandbox, task: str) -> tuple[bytes, bytes]:
        folder = sb.task_dir(task)
        return (folder / "state.json").read_bytes(), (folder / "events.jsonl").read_bytes()

    def finish_writer(self, sb: Sandbox, task: str, slug: str, job: str, workdir: Path) -> str:
        sb.work(workdir, f"{job.lower()}.txt", f"{job}\n", f"{job}: work")
        sb.result(task, f"jobs/{job}.result.md", status="done", summary="s", validation="pass", changes="made")
        return sb.sae("collect", slug, job).stdout

    def run_command(self, sb: Sandbox, command: str) -> list[dict]:
        log = sb.tmp / "harness-log.jsonl"
        write_fake_clis(sb.harness_bin, script=RECORDING_CLI)
        proc = subprocess.run(command, shell=True, cwd=sb.repo, capture_output=True, text=True,
                              env=dict(sb.env, FAKE_HARNESS_LOG=str(log)))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return [json.loads(line) for line in log.read_text().splitlines()]


class WriterCommandTests(LaunchTestCase):
    def test_codex_writer_under_claude_runs_without_sandbox_and_records_tokens(self):
        sb = self.sandbox_for("claude")
        task = self.executing(sb, "cx")
        self.to_other(sb, "cx", "ONE", "claude")
        out = sb.sae("dispatch", "cx", "ONE").stdout
        self.assertIn("HARNESS: codex · MODEL: cx-2-core (core, newest) · EFFORT: low", out)
        self.assertNotIn("PROMPT:", out)
        lines = out.split("\n")
        command = lines[lines.index("COMMAND:") + 1]
        self.assertIn("codex exec -m cx-2-core -c model_reasoning_effort=low "
                      "--dangerously-bypass-approvals-and-sandbox -C ", command)
        self.assertNotIn(" -s ", command)
        self.assertNotIn(" -o ", command)  # the worker writes its own result file
        self.assertIn("When it exits: sae collect", lines[lines.index("COMMAND:") + 2])
        self.assertIn("not as a subagent", out)
        self.assertIn("no --tokens", out)
        calls = self.run_command(sb, command)
        self.assertEqual(calls[0]["name"], "codex")
        argv = calls[0]["argv"]
        workdir = Path(argv[argv.index("-C") + 1])
        self.assertTrue((workdir / ".git").exists())  # the job's workspace (chain layout: the task worktree)
        self.assertIn("Write your result to:", argv[argv.index("--json") + 1])  # the worker prompt, newlines kept
        output = sb.task_dir(task) / "jobs" / "ONE.result.codex.jsonl"
        self.assertTrue(output.exists())
        self.finish_writer(sb, task, "cx", "ONE", workdir)
        attempt = sb.state(task)["jobs"]["ONE"]["attempts"][-1]
        self.assertEqual((attempt["harness"], attempt["tokens"]), ("codex", CODEX_TOKENS))
        self.assertFalse(output.exists())  # [RECORD-PRIVACY]

    def test_claude_writer_under_codex_runs_in_the_workdir_with_bypass(self):
        sb = self.sandbox_for("codex")
        task = self.executing(sb, "cl")
        self.to_other(sb, "cl", "ONE", "codex")
        data = sb.json("dispatch", "cl", "ONE")
        self.assertEqual(data["harness"], "claude")
        command = data["command"]
        self.assertIn("claude -p ", command)
        self.assertIn("--permission-mode bypassPermissions", command)
        self.assertIn("--model c-mid --effort low", command)
        self.assertNotIn("--allowedTools", command)
        calls = self.run_command(sb, command)
        self.assertEqual(Path(calls[0]["cwd"]).resolve(), Path(data["workspace"]).resolve())
        argv = calls[0]["argv"]
        self.assertEqual(Path(argv[argv.index("--add-dir") + 1]).resolve(), sb.task_dir(task).resolve())
        self.finish_writer(sb, task, "cl", "ONE", Path(data["workspace"]))
        attempt = sb.state(task)["jobs"]["ONE"]["attempts"][-1]
        self.assertEqual((attempt["harness"], attempt["tokens"]), ("claude", CLAUDE_TOKENS))
        self.assertFalse((sb.task_dir(task) / "jobs" / "ONE.result.claude.json").exists())

    def test_jobs_on_the_orchestrator_keep_the_prompt(self):
        sb = self.sandbox_for("claude")
        task = self.executing(sb, "same")
        out = sb.sae("dispatch", "same", "ONE").stdout
        self.assertIn("PROMPT:", out)
        self.assertNotIn("COMMAND:", out)
        self.assertNotIn("launch", sb.state(task)["jobs"]["ONE"]["attempts"][0])
        self.assertNotIn("Bypass:", sb.sae("status", "same").stdout)

    def test_review_command_is_unchanged_and_records_a_read_only_request(self):
        sb = self.sandbox_for("claude", points=["all-jobs"], provider="codex")
        task = self.executing(sb, "rev")
        data = sb.json("dispatch", "rev", "ONE")
        self.finish_writer(sb, task, "rev", "ONE", Path(data["workspace"]))
        review = sb.json("dispatch", "rev", "REVIEW-ONE")
        root = sb.task_worktree(task)
        reviews = sb.task_dir(task) / "reviews"
        self.assertTrue(review["command"].startswith(f"rm -f {reviews / 'REVIEW-ONE.md'} "
                                                     f"{reviews / 'REVIEW-ONE.codex.jsonl'} && codex exec -m "
                                                     f"cx-2-core -c model_reasoning_effort=medium -s read-only "
                                                     f"-C {root} -o {reviews / 'REVIEW-ONE.md'} --ephemeral --json "))
        self.assertTrue(review["command"].endswith(f"< /dev/null > {reviews / 'REVIEW-ONE.codex.jsonl'}"))
        self.assertNotIn("bypass", review["command"])
        launch = sb.state(task)["jobs"]["REVIEW-ONE"]["attempts"][0]["launch"]
        self.assertEqual(launch["request"], "read-only requested")
        self.assertEqual(launch["command"], "rm -f <result> <output> && codex exec -m cx-2-core -c "
                                            "model_reasoning_effort=medium -s read-only -C <workdir> -o <result> "
                                            "--ephemeral --json <prompt> < /dev/null > <output>")
        self.assertNotIn("Bypass:", sb.sae("status", "rev").stdout)  # a review is not a bypass job


    def test_codex_writer_in_a_task_without_git_skips_the_repo_check(self):
        # Review WRITER-LAUNCH finding 3.
        sb = self.sandbox_for("claude", git=False)
        task = self.executing(sb, "nogit")
        self.to_other(sb, "nogit", "ONE", "claude")
        data = sb.json("dispatch", "nogit", "ONE")
        self.assertIn(" --skip-git-repo-check ", data["command"])
        self.assertIn(" --skip-git-repo-check ", sb.state(task)["jobs"]["ONE"]["attempts"][0]["launch"]["command"])
        argv = self.run_command(sb, data["command"])[0]["argv"]
        self.assertIn("--skip-git-repo-check", argv)
        # a task with git keeps the check
        git_sb = self.sandbox_for("claude", name="git")
        self.executing(git_sb, "withgit")
        self.to_other(git_sb, "withgit", "ONE", "claude")
        self.assertNotIn("--skip-git-repo-check", git_sb.json("dispatch", "withgit", "ONE")["command"])

    def test_collect_refuses_a_result_the_current_attempt_did_not_write(self):
        # Review WRITER-LAUNCH finding 2: a reopened research job whose COMMAND wrote nothing.
        sb = self.sandbox_for("claude")
        task = self.executing(sb, "stale")
        sb.sae("job", "add", "stale", "R", "--kind", "research", "--reason", "a question")
        self.to_other(sb, "stale", "R", "claude")
        sb.sae("dispatch", "stale", "R")
        sb.result(task, "research/R.md", status="done", confidence="high")
        sb.sae("collect", "stale", "R")
        report = sb.task_dir(task) / "research" / "R.md"
        old = report.stat().st_mtime - 60
        os.utime(report, (old, old))  # the first attempt wrote it a minute ago
        data = sb.json("dispatch", "stale", "R", "--resume", "--reason", "follow-up questions")
        self.run_command(sb, data["command"])  # exits 0 and writes no report
        before = self.frozen(sb, task)
        err = sb.sae("collect", "stale", "R", code=1).stderr
        self.assertIn("attempt 2 has not written or updated it", err)
        self.assertEqual(self.frozen(sb, task), before)
        self.assertTrue(report.exists())  # the earlier report stays for the retry
        self.assertEqual(sb.state(task)["jobs"]["R"]["status"], "running")
        sb.result(task, "research/R.md", status="done", confidence="high")
        self.assertIn("R: done", sb.sae("collect", "stale", "R").stdout)


class LaunchRecordTests(LaunchTestCase):
    def test_attempt_records_the_placeholder_command_and_the_request(self):
        for orchestrator in ("claude", "codex"):
            with self.subTest(orchestrator=orchestrator):
                sb = self.sandbox_for(orchestrator)
                task = self.executing(sb, "rec")
                self.to_other(sb, "rec", "ONE", orchestrator)
                sb.sae("dispatch", "rec", "ONE")
                attempt = sb.state(task)["jobs"]["ONE"]["attempts"][0]
                launch = attempt["launch"]
                self.assertEqual((launch["harness"], launch["model"], launch["effort"]),
                                 (attempt["harness"], attempt["model"], attempt["effort"]))
                self.assertEqual(launch["request"], "bypass requested")
                self.assertIn("<prompt>", launch["command"])
                self.assertIn("<workdir>", launch["command"])
                self.assertNotIn(str(sb.tmp), launch["command"])
                if orchestrator == "claude":
                    self.assertEqual(launch["command"],
                                     "rm -f <output> && codex exec -m cx-2-core -c model_reasoning_effort=low "
                                     "--dangerously-bypass-approvals-and-sandbox -C <workdir> --ephemeral --json "
                                     "<prompt> < /dev/null > <output>")
                else:
                    self.assertEqual(launch["command"],
                                     "cd <workdir> && rm -f <output> && claude -p <prompt> --output-format json "
                                     "--model c-mid --effort low --permission-mode bypassPermissions "
                                     "--add-dir <task-folder> > <output>")
                event = [e for e in sb.events(task) if e["type"] == "job.dispatched"][-1]
                self.assertEqual(event["launch"], launch)


class BypassLineTests(LaunchTestCase):
    def test_status_shows_one_bypass_line_for_a_job_sent_to_the_other_harness(self):
        sb = self.sandbox_for("claude")
        self.executing(sb, "by", jobs=("ONE", "TWO"))
        self.assertNotIn("Bypass:", sb.sae("status", "by").stdout)
        self.to_other(sb, "by", "TWO", "claude")
        out = sb.sae("status", "by").stdout
        bypass = [line for line in out.splitlines() if line.startswith("Bypass:")]
        self.assertEqual(bypass, ["Bypass: jobs on the other harness start with a bypass request "
                                  "(no sandbox, no approvals): TWO"])
        self.assertEqual(sb.json("status", "by")["bypass"], bypass[0])
        # a job dispatched once by a flag stays listed: its attempt requested a bypass
        sb.sae("job", "override", "by", "TWO", "--clear")
        sb.sae("dispatch", "by", "ONE", "--harness", "codex")
        self.assertIn("(no sandbox, no approvals): ONE", sb.sae("status", "by").stdout)


class HarnessFallbackTests(LaunchTestCase):
    def test_missing_cli_refuses_before_any_change_for_a_pending_job(self):
        for orchestrator in ("claude", "codex"):
            with self.subTest(orchestrator=orchestrator):
                sb = self.sandbox_for(orchestrator)
                task = self.executing(sb, "miss")
                self.to_other(sb, "miss", "ONE", orchestrator)
                other = OTHER[orchestrator]
                sb.without_cli(other)
                before = self.frozen(sb, task)
                err = sb.sae("dispatch", "miss", "ONE", code=1).stderr
                self.assertEqual(self.frozen(sb, task), before)
                self.assertFalse(any(sb.worktrees.glob(f"*/{task}/ONE")))  # no job worktree either
                self.assertIn(f"ONE routes to {other}, but the {other} CLI is not on the PATH. "
                              "Nothing was dispatched and nothing changed.", err)
                lines = err.splitlines()
                command = lines[lines.index("Fallback command:") + 1]
                self.assertIn(f"dispatch {task} ONE --harness {orchestrator} --reason \"harness fallback: "
                              f"requested {other} · ", command)
                self.assertIn(f"; {other} CLI not on PATH\"", command)
                self.assertNotIn("--resume", command)

    def test_missing_cli_branch_review_any_mode(self):
        sb = self.sandbox_for("claude", points=["spec"], provider="codex")
        task = sb.new_task("spec review", "specrev")
        sb.sae("set", "specrev", "interaction=collaborative")
        (sb.task_dir(task) / "specs.md").write_text("# Spec\n\n## Requirements\n\n### [A] One\nAcceptance:\n- [ ] x\n")
        self.assertIn("REVIEW-SPEC", sb.json("status", "specrev")["ready"])
        sb.without_cli("codex")
        before = self.frozen(sb, task)
        err = sb.sae("dispatch", "specrev", "REVIEW-SPEC", code=1).stderr
        self.assertEqual(self.frozen(sb, task), before)  # the due review was not added
        self.assertNotIn("REVIEW-SPEC", sb.state(task)["jobs"])
        lines = err.splitlines()
        command = lines[lines.index("Fallback command:") + 1]
        self.assertIn(f"dispatch {task} REVIEW-SPEC --provider claude --reason", command)
        self.assertEqual(lines[lines.index("Fallback command:") + 2],
                         "Rule (mode collaborative): a review falls back in every mode. Run it now; "
                         "sae records the routing exception.")
        # the printed command works for the due review
        data = sb.json(*self.args_of(command))
        self.assertEqual(data["harness"], "claude")
        self.assertIn("prompt", data)
        exception = sb.state(task)["jobs"]["REVIEW-SPEC"]["attempts"][0]["routing_exception"]
        self.assertEqual(exception["requested"]["harness"], "codex")
        self.assertEqual(exception["actual"]["harness"], "claude")
        self.assertEqual(exception["reason"], "codex CLI not on PATH")

    def test_missing_cli_branch_full_auto(self):
        sb = self.sandbox_for("claude")
        task = self.executing(sb, "auto", settings=("interaction=full-auto",))
        self.to_other(sb, "auto", "ONE", "claude")
        sb.without_cli("codex")
        err = sb.sae("dispatch", "auto", "ONE", code=1).stderr
        lines = err.splitlines()
        self.assertEqual(lines[lines.index("Fallback command:") + 2:],
                         ["Rule (mode full-auto): run it now; sae records the routing exception."])
        out = sb.sae(*self.args_of(lines[lines.index("Fallback command:") + 1])).stdout
        self.assertIn("HARNESS: claude ·", out)
        routing = next(line for line in out.splitlines() if line.startswith("ROUTING: "))
        self.assertTrue(routing.endswith(" · routing exception: requested codex · core · low, ran claude · c-mid · "
                                         "low — codex CLI not on PATH"), routing)
        self.assertEqual(sb.state(task)["jobs"]["ONE"]["attempts"][0]["routing_exception"]["requested"],
                         {"harness": "codex", "model": "core", "effort": "low"})

    def test_missing_cli_branch_other_mode_pending_job(self):
        sb = self.sandbox_for("claude")
        task = self.executing(sb, "ask", settings=("interaction=collaborative",))
        self.to_other(sb, "ask", "ONE", "claude")
        sb.without_cli("codex")
        lines = sb.sae("dispatch", "ask", "ONE", code=1).stderr.splitlines()
        at = lines.index("Fallback command:")
        command = lines[at + 1]
        resumed = command.replace(" --reason ", " --resume --reason ", 1)
        self.assertEqual(lines[at + 2:], [
            "Rule (mode collaborative): an implementation job falls back only on the owner's yes.",
            f"  1. sae job park {task} ONE --reason \"harness fallback: codex CLI not on PATH\" "
            "(it leaves the ready queue and frees its writer slot)",
            f"  2. sae ask {task} \"Run ONE on claude instead of codex? codex CLI not on PATH\" --job ONE",
            "  3. Continue with independent work.",
            f"  4. On the owner's yes: sae log {task} decision \"harness fallback: ONE: <answer>\" --by human "
            "--job ONE, then run:",
            f"     {resumed}"])

    def test_if_it_fails_branches_for_a_running_job(self):
        for mode in ("full-auto", "auto"):
            with self.subTest(mode=mode):
                sb = self.sandbox_for("claude", name=mode)
                task = self.executing(sb, "run", settings=(f"interaction={mode}",))
                self.to_other(sb, "run", "ONE", "claude")
                out = sb.sae("dispatch", "run", "ONE").stdout
                lines = out.splitlines()
                at = lines.index("IF IT FAILS:")
                command = lines[at + 1]
                self.assertIn(f"dispatch {task} ONE --harness claude --resume --reason \"harness fallback: requested "
                              f"codex · cx-2-core · low; COMMAND failed: <exit code or missing result>\"", command)
                if mode == "full-auto":
                    self.assertEqual(lines[at + 2:], ["Rule (mode full-auto): run it now; sae records the routing "
                                                      "exception."])
                else:
                    self.assertEqual(lines[at + 2:], [
                        "Rule (mode auto): an implementation job falls back only on the owner's yes.",
                        f"  1. sae job park {task} ONE --reason \"harness fallback: COMMAND failed: <exit code or "
                        "missing result>\" (it leaves the ready queue and frees its writer slot)",
                        f"  2. sae ask {task} \"Run ONE on claude instead of codex? COMMAND failed: <exit code or "
                        "missing result>\" --job ONE",
                        "  3. Continue with independent work.",
                        f"  4. On the owner's yes: sae log {task} decision \"harness fallback: ONE: <answer>\" --by "
                        "human --job ONE, then run:",
                        f"     {command}"])

    def test_review_if_it_fails_branch(self):
        sb = self.sandbox_for("claude", points=["all-jobs"], provider="codex")
        task = self.executing(sb, "revfail", settings=("interaction=interactive",))
        data = sb.json("dispatch", "revfail", "ONE")
        self.finish_writer(sb, task, "revfail", "ONE", Path(data["workspace"]))
        review = sb.json("dispatch", "revfail", "REVIEW-ONE")
        self.assertIn(f"REVIEW-ONE --provider claude --resume --reason \"harness fallback: requested codex · "
                      f"cx-2-core · medium; provider failed: <exit code or empty result>\"", review["if_it_fails"])
        self.assertEqual(review["rule"], ["Rule (mode interactive): a review falls back in every mode. Run it now; "
                                          "sae records the routing exception."])
        again = sb.json(*self.args_of(review["if_it_fails"].replace("<exit code or empty result>", "exit 1")))
        self.assertEqual(again["harness"], "claude")
        exception = sb.state(task)["jobs"]["REVIEW-ONE"]["attempts"][-1]["routing_exception"]
        self.assertEqual((exception["requested"]["harness"], exception["reason"]), ("codex", "provider failed: exit 1"))

    def test_missing_cli_branch_done_research_with_resume(self):
        sb = self.sandbox_for("claude")
        task = self.executing(sb, "res", settings=("interaction=critical-only",))
        sb.sae("job", "add", "res", "R", "--kind", "research", "--reason", "a question")
        self.to_other(sb, "res", "R", "claude")
        sb.sae("dispatch", "res", "R")
        sb.result(task, "research/R.md", status="done", confidence="high")
        sb.sae("collect", "res", "R")
        self.assertEqual(sb.state(task)["jobs"]["R"]["status"], "done")
        sb.without_cli("codex")
        before = self.frozen(sb, task)
        lines = sb.sae("dispatch", "res", "R", "--resume", "--reason", "follow-up questions", code=1).stderr.splitlines()
        self.assertEqual(self.frozen(sb, task), before)
        at = lines.index("Fallback command:")
        command = lines[at + 1]
        self.assertIn(f"dispatch {task} R --harness claude --resume --reason \"harness fallback: requested codex · ",
                      command)
        self.assertEqual(lines[at + 2:], [
            "Rule (mode critical-only): a research job falls back only on the owner's yes. The job stays done; "
            "do not park it.",
            f"  1. sae ask {task} \"Run R on claude instead of codex? codex CLI not on PATH\" --job R",
            "  2. Continue with independent work.",
            f"  3. On the owner's yes: sae log {task} decision \"harness fallback: R: <answer>\" --by human --job R, "
            "then run:",
            f"     {command}"])
        data = sb.json(*self.args_of(command))
        self.assertEqual((data["harness"], data["attempt"]), ("claude", 2))

    def test_park_frees_the_writer_slot_and_the_yes_resumes_on_the_orchestrator(self):
        sb = self.sandbox_for("claude", max_writers=1)
        task = self.executing(sb, "slot", jobs=("A", "B"))
        self.to_other(sb, "slot", "A", "claude")
        # 1. a failed COMMAND: A runs and holds the only writer slot
        out = sb.sae("dispatch", "slot", "A").stdout
        resume = out.splitlines()[out.splitlines().index("IF IT FAILS:") + 1]
        self.assertIn("all writer slots busy", sb.sae("dispatch", "slot", "B", code=1).stderr)
        parked = sb.sae("job", "park", "slot", "A", "--reason", "harness fallback: COMMAND failed: exit 1").stdout
        self.assertIn("frees its writer slot", parked)
        a = sb.state(task)["jobs"]["A"]
        self.assertEqual(a["status"], "parked")
        self.assertIsNotNone(a["attempts"][-1]["ended"])
        self.assertIn("A — harness fallback: COMMAND failed: exit 1", sb.sae("status", "slot").stdout)
        self.assertEqual([e["was"] for e in sb.events(task) if e["type"] == "job.parked"], ["running"])
        ws_b = Path(sb.json("dispatch", "slot", "B")["workspace"])
        self.finish_writer(sb, task, "slot", "B", ws_b)
        # the owner's yes: log it, then run the printed fallback
        sb.sae("ask", "slot", "Run A on claude instead of codex?", "--job", "A")
        sb.sae("log", "slot", "decision", "harness fallback: A: yes", "--by", "human", "--job", "A")
        data = sb.json(*self.args_of(resume.replace("<exit code or missing result>", "exit 1")))
        self.assertEqual(data["harness"], "claude")
        self.assertIn("prompt", data)
        attempt = sb.state(task)["jobs"]["A"]["attempts"][-1]
        self.assertNotIn("launch", attempt)
        self.assertEqual(attempt["routing_exception"]["requested"],
                         {"harness": "codex", "model": "cx-2-core", "effort": "low"})

    def test_park_after_a_missing_cli_lets_the_other_writer_run(self):
        sb = self.sandbox_for("claude", max_writers=1)
        task = self.executing(sb, "slot2", jobs=("A", "B"))
        self.to_other(sb, "slot2", "A", "claude")
        sb.without_cli("codex")
        lines = sb.sae("dispatch", "slot2", "A", code=1).stderr.splitlines()
        sb.sae("job", "park", "slot2", "A", "--reason", "harness fallback: codex CLI not on PATH")
        ready = [r["id"] for r in sb.json("next", "slot2")["ready"]]
        self.assertEqual(ready, ["B"])
        ws_b = Path(sb.json("dispatch", "slot2", "B")["workspace"])
        self.finish_writer(sb, task, "slot2", "B", ws_b)
        sb.sae("log", "slot2", "decision", "harness fallback: A: yes", "--by", "human", "--job", "A")
        resumed = lines[-1].strip()
        self.assertIn(" --resume --reason ", resumed)
        data = sb.json(*self.args_of(resumed))
        self.assertEqual(data["harness"], "claude")
        self.assertEqual(sb.state(task)["jobs"]["A"]["status"], "running")

    def test_route_requested_only_by_the_harness_flag(self):
        sb = self.sandbox_for("claude")
        task = self.executing(sb, "flag", settings=("interaction=full-auto",))
        sb.without_cli("codex")
        lines = sb.sae("dispatch", "flag", "ONE", "--harness", "codex", code=1).stderr.splitlines()
        command = lines[lines.index("Fallback command:") + 1]
        self.assertIn("--reason \"harness fallback: requested codex · core · low; codex CLI not on PATH\"", command)
        data = sb.json(*self.args_of(command))
        self.assertEqual(data["harness"], "claude")
        exception = sb.state(task)["jobs"]["ONE"]["attempts"][0]["routing_exception"]
        self.assertEqual(exception, {"requested": {"harness": "codex", "model": "core", "effort": "low"},
                                     "actual": {"harness": "claude", "model": "c-mid", "effort": "low"},
                                     "reason": "codex CLI not on PATH"})
        events = [e for e in sb.events(task) if e["type"] == "routing.exception"]
        self.assertEqual([(e["job"], e["attempt"], e["requested"]["harness"]) for e in events], [("ONE", 1, "codex")])
        # the next ordinary dispatch uses routing again: no flag, no exception
        again = sb.json("dispatch", "flag", "ONE", "--resume", "--reason", "verify-failed")
        self.assertEqual((again["harness"], again["routing_exception"]), ("claude", None))
        self.assertNotIn("routing_exception", sb.state(task)["jobs"]["ONE"]["attempts"][1])

    def test_override_route_returns_after_the_fallback_and_the_final_report_lists_it(self):
        sb = self.sandbox_for("claude")
        task = self.executing(sb, "back", settings=("interaction=full-auto",))
        self.to_other(sb, "back", "ONE", "claude")
        out = sb.sae("dispatch", "back", "ONE").stdout
        fallback = out.splitlines()[out.splitlines().index("IF IT FAILS:") + 1]
        data = sb.json(*self.args_of(fallback.replace("<exit code or missing result>", "exit 2")))
        self.assertEqual(data["harness"], "claude")
        self.assertIn("ROUTING: ", sb.sae("dispatch", "back", "ONE", "--resume", "--reason", "x").stdout)
        attempts = sb.state(task)["jobs"]["ONE"]["attempts"]
        self.assertEqual([a["harness"] for a in attempts], ["codex", "claude", "codex"])  # routing again
        self.assertEqual([bool(a.get("routing_exception")) for a in attempts], [False, True, False])
        self.finish_writer(sb, task, "back", "ONE", Path(data["workspace"]))
        report = sb.sae("finish", "back").stdout
        self.assertIn("## Routing exceptions\n- ONE attempt 2: requested codex · cx-2-core · low, ran claude · c-mid · "
                      "low. Reason: COMMAND failed: exit 2", report)

    def test_park_refuses_reviews_and_finished_jobs(self):
        sb = self.sandbox_for("claude", points=["all-jobs"], provider="codex")
        task = self.executing(sb, "pk")
        data = sb.json("dispatch", "pk", "ONE")
        self.finish_writer(sb, task, "pk", "ONE", Path(data["workspace"]))
        self.assertIn("is done", sb.sae("job", "park", "pk", "ONE", "--reason", "x", code=1).stderr)
        sb.sae("dispatch", "pk", "REVIEW-ONE")
        self.assertIn("falls back in every mode",
                      sb.sae("job", "park", "pk", "REVIEW-ONE", "--reason", "x", code=1).stderr)

    def test_parked_job_without_attempts_meets_an_active_hold_through_the_fallback(self):
        # Review WRITER-LAUNCH finding 1: --resume of a never-started parked job is a first dispatch.
        sb = self.sandbox_for("claude")
        task = self.executing(sb, "hold", jobs=("A", "B"), settings=("interaction=collaborative",))
        self.to_other(sb, "hold", "A", "claude")
        sb.without_cli("codex")
        resumed = sb.sae("dispatch", "hold", "A", code=1).stderr.splitlines()[-1].strip()
        sb.sae("job", "park", "hold", "A", "--reason", "harness fallback: codex CLI not on PATH")
        sb.sae("hold", "hold", "B")
        self.finish_writer(sb, task, "hold", "B", Path(sb.json("dispatch", "hold", "B")["workspace"]))
        before = self.frozen(sb, task)
        err = sb.sae(*self.args_of(resumed), code=3).stderr
        self.assertIn("Hold after B: nothing new is dispatched.", err)
        self.assertEqual(self.frozen(sb, task), before)
        sb.sae("hold", "hold", "B", "--release")
        self.assertEqual(sb.json(*self.args_of(resumed))["harness"], "claude")

    def test_fallback_closes_the_failed_command_attempt(self):
        # Review WRITER-LAUNCH finding 4.
        sb = self.sandbox_for("claude")
        task = self.executing(sb, "close", settings=("interaction=full-auto",))
        self.to_other(sb, "close", "ONE", "claude")
        out = sb.sae("dispatch", "close", "ONE").stdout
        fallback = out.splitlines()[out.splitlines().index("IF IT FAILS:") + 1]
        sb.json(*self.args_of(fallback.replace("<exit code or missing result>", "exit 1")))
        first, second = sb.state(task)["jobs"]["ONE"]["attempts"]
        self.assertIsNotNone(first["ended"])
        self.assertEqual(first["ended"], second["started"])
        self.assertIsNone(second["ended"])

    @staticmethod
    def args_of(command: str) -> list[str]:
        """The sae arguments of a printed `python3 <sae.py> …` command."""
        words = shlex.split(command)
        return words[words.index(next(w for w in words if w.endswith("sae.py"))) + 1:]


if __name__ == "__main__":
    unittest.main()
