"""[NARROW-OUTPUT]: check text throughout a task with realistic long IDs."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from saetest import SCRIPTS, SaeTestCase, schema1_config, wide_lines

sys.path.insert(0, str(SCRIPTS))
from sae_lib.cli import build_parser  # noqa: E402
from sae_lib.common import emit, wrap, wrap_notice_lines  # noqa: E402
from sae_lib.prompts import external_review_command  # noqa: E402


def parser_commands(parser, prefix=()):
    """Enumerate executable CLI subcommands so new commands require width coverage."""
    children = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    if not children:
        return {prefix}
    return {path for action in children for name, child in action.choices.items()
            for path in parser_commands(child, prefix + (name,))}


OUTPUT_MODES = {"setup show: missing", "setup show: schema 1", "setup show: current", "new: backlog pickup",
                "start: backlog pickup", "view: unwritable state", "view: start", "view: stop",
                "view: no server", "new: missing config", "setup snippets: missing config",
                "hold: active", "finish: with open", "finish: override", "review: second changes-required",
                "merge: conflict", "verify: repeated failure", "abandon: dirty worktree"}


class OwnerOutputBoundaryTests(SaeTestCase):
    def test_emit_wraps_free_text_without_caller_opt_in(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            emit(argparse.Namespace(json=False), "  Owner notice: " + "long prose " * 20)
        self.assertEqual(wide_lines(output.getvalue()), [])
        self.assertEqual(output.getvalue().split(), ("Owner notice: " + "long prose " * 20).split())
        self.assertTrue(output.getvalue().splitlines()[1].startswith("    "))

    def test_wrap_keeps_labeled_commands_whole_with_arguments_and_quotes(self):
        commands = ["sae hold 2026-10-12-1000--owner-output-width-through-the-whole-tas SAE-HOLD-WRITER --release",
                    'sae log long-task decision "Keep spaces and a colon: here" --by agent',
                    'python3 "/tmp/skill with spaces/scripts/sae.py" view long-task --open',
                    "/shape-and-execute setup"]
        for command in commands:
            for formatter in (wrap, wrap_notice_lines):
                with self.subTest(command=command, formatter=formatter.__name__):
                    output = formatter("Next: " + command)
                    self.assertEqual(output, "Next:\n  " + command)
                    self.assertEqual(wide_lines(output), [])
                    self.assertEqual(formatter(command), "  " + command)

    def test_process_map_is_preserved_at_output_boundary(self):
        line = "🔨 " + "process map step | " * 12
        self.assertEqual(wrap_notice_lines(line), line)

    def test_verbatim_artifacts_and_short_tables_keep_their_spacing(self):
        snippet = json.dumps({"path": "/tmp/" + "long path " * 15}, indent=2)
        text = "  level     normal  hard\nSnippet:\n" + snippet + "\nNotice: " + "long prose " * 20
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            emit(argparse.Namespace(json=False), text, verbatim=(snippet,))
        self.assertTrue(output.getvalue().startswith("  level     normal  hard\n"))
        self.assertIn(snippet, output.getvalue())
        self.assertEqual(wide_lines(output.getvalue().replace(snippet, "")), [])

    def test_external_review_commands_copy_as_one_line_and_preserve_prompt(self):
        sb = self.sandbox()
        fake_bin = self.tmp / "fake-harness-bin"
        fake_bin.mkdir()
        script = (f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n"
                  "args = sys.argv[1:]\n"
                  "if '-o' in args:\n    Path(args[args.index('-o') + 1]).write_text(json.dumps(args))\n"
                  "else:\n    print(json.dumps(args))\n")
        for harness in ("claude", "codex"):
            executable = fake_bin / harness
            executable.write_text(script)
            executable.chmod(0o755)
        env = dict(sb.env, PATH=str(fake_bin) + os.pathsep + sb.env["PATH"])
        task = SimpleNamespace(root=sb.repo, dir=sb.repo / ".tasks" / "example task",
                               jobs={"REVIEW": {"kind": "review"}})
        prompt = "First line with 'quotes', \"quotes\", `touch injected`, $(touch injected) and \\literal\nSecond line\rThird"
        for harness in ("claude", "codex"):
            with self.subTest(harness=harness):
                command = external_review_command(task, "REVIEW", {"harness": harness, "model": "fake", "effort": "high"}, prompt)
                self.assertEqual(len(command.splitlines()), 1)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    emit(argparse.Namespace(json=False), "COMMAND:\n" + command, verbatim=(command,))
                self.assertEqual(output.getvalue(), "COMMAND:\n" + command + "\n")
                proc = subprocess.run(command, shell=True, cwd=sb.repo, env=env, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                args = json.loads((task.dir / "reviews" / "REVIEW.md").read_text())
                self.assertIn(prompt, args)
                self.assertFalse((sb.repo / "injected").exists())


class TaskOutputWidthTests(SaeTestCase):
    def test_every_owner_command_through_finish_fits_72_columns(self):
        """Include both streams and refusals; only dispatch's PROMPT is agent-facing."""
        sb = self.sandbox()
        home = self.tmp / "home"
        home.mkdir()
        sb.env.update({"HOME": str(home), "TMPDIR": str(self.tmp),
                       "XDG_CONFIG_HOME": str(home / "config"), "XDG_CACHE_HOME": str(home / "cache"),
                       "XDG_DATA_HOME": str(home / "data")})
        (sb.codex_home / "config.toml").write_text("[agents]\nmax_threads = 10\n")
        slug = "owner-output-width-through-the-whole-task"
        core, side = "SAE-WORKTREE-CLEANUP-FIX-1", "SAE-COLLECT-FAILURE-CHECK"
        final, late = "SAE-FINAL-VALIDATION-CHECK", "SAE-LATE-WORKTREE-ADDITION"
        captures = []
        driven, modes = set(), set()
        parser = build_parser()
        commands = parser_commands(parser)

        def command(*args, code=0, mode=None, stdin=None):
            self.assertFalse({"--json", "--help"}.intersection(args), "Coverage requires text mode")
            proc = sb.sae(*args, code=code, stdin=stdin)
            driven.update(path for path in commands if tuple(args[:len(path)]) == path)
            if mode:
                modes.add(mode)
            stdout = proc.stdout.split("\nPROMPT:\n", 1)[0] if args[0] == "dispatch" else proc.stdout
            if args[:2] == ("setup", "show"):
                stdout = stdout.split("\n{", 1)[0]  # JSON proposal to paste
            if args[:2] == ("setup", "snippets") and code == 0:
                stdout = re.sub(r'(?ms)^default_permissions = .*?^max_threads = \d+\n', '', stdout)
                stdout = stdout.split("\n{", 1)[0]  # JSON permissions to paste
            captures.append((" ".join(args), stdout + proc.stderr))
            return proc

        created = command("new", "Owner output across a whole task", "--slug", slug)
        task = re.search(r"^Task: (.+)$", created.stdout, re.M).group(1)
        slug = task.split("--", 1)[1]
        self.assertEqual(len(slug), 40)
        command("set", slug, "interaction=auto", "task-difficulty=hard")
        command("set", slug, "interaction=auto")
        command("setup", "show", mode="setup show: current")
        saved_config = sb.config.read_text()
        sb.config.unlink()
        command("setup", "show", mode="setup show: missing")
        command("new", "No config", "--slug", "no-config", code=2, mode="new: missing config")
        command("setup", "snippets", code=2, mode="setup snippets: missing config")
        sb.config.write_text(json.dumps(schema1_config(sb.worktrees)))
        command("setup", "show", mode="setup show: schema 1")
        sb.config.write_text(saved_config)
        command("setup", "save", stdin=saved_config)
        command("setup", "snippets")
        command("project", "set", "tier.claude.L2=c-big:high", "routing.claude.execution.balanced.hard=L4")
        command("project", "show")
        command("project", "unset", "tier.claude.L2", "routing.claude.execution.balanced.hard")
        command("job", "add", slug, "SAE-REMOVE-UNNEEDED-WRITER", "--kind", "implementation")
        command("job", "remove", slug, "SAE-REMOVE-UNNEEDED-WRITER", "--reason", "not needed")
        command("doctor", "--repo")
        command("job", "add", slug, core, "--kind", "implementation", "--review")
        sb.job_file(task, core, scope=["core.txt"])
        command("job", "add", slug, side, "--kind", "implementation")
        sb.job_file(task, side, verify=["test -f verify-ready"], scope=["side.txt", "verify-ready"])
        command("job", "add", slug, final, "--kind", "validation", "--final", "--needs", core)
        sb.job_file(task, final)
        command("job", "edit", slug, final, "--needs", f"{core},{side}", "--difficulty", "hard")
        command("job", "override", slug, core, "--harness", "claude", "--model", "c-big", "--effort", "high")
        command("job", "override", slug, core, "--clear")
        command("set", slug, "review=selected-jobs,integration")
        command("approve", slug, "spec")
        command("start", slug, code=3)
        command("check", slug)
        command("approve", slug, "plan")
        command("start", slug)
        command("start", slug, "--harness", "claude")
        command("next", slug)
        command("status", slug)
        command("status")
        command("dispatch", slug, final, code=1)
        command("finish", slug, code=3)

        def result(job, status="done", summary="Completed the requested work and validated the result."):
            sb.result(task, f"jobs/{job}.result.md", status=status, summary=summary,
                      validation="pass" if status == "done" else "fail",
                      changes="made" if job != final else "none")

        def review(job, target, verdict):
            command("dispatch", slug, job)
            sb.result(task, f"reviews/{job}.md", target=target, verdict=verdict)
            command("collect", slug, job)

        command("dispatch", slug, core)
        workspace = sb.task_worktree(task).parent / core
        sb.work(workspace, "core.txt", "core\n", f"{core}: work")
        command("dispatch", slug, core, code=1)
        command("finish", slug, code=3)
        result(core)
        command("collect", slug, core)
        command("merge", slug, core, code=3)
        review(f"REVIEW-{core}", core, "changes-required")
        command("merge", slug, core, code=3)
        command("finish", slug, "--with-open", code=3)
        command("merge", slug, core, "--accept-review", "owner accepts the review findings")
        command("hold", slug, core, "--reason", "Owner checks this writer.", mode="hold: active")
        command("next", slug)
        command("status", slug)
        command("dispatch", slug, side, code=3)
        command("hold", slug, core, "--release")

        command("dispatch", slug, side)
        workspace = sb.task_worktree(task).parent / side
        sb.work(workspace, "side.txt", "side\n", f"{side}: work")
        result(side, "failed", "The first attempt failed and needs another attempt.")
        command("collect", slug, side)
        command("doctor")
        command("dispatch", slug, side, "--resume", "--reason", "retry the failed attempt")
        result(side)
        command("collect", slug, side, code=5)
        command("dispatch", slug, side, "--resume", "--reason", "verify-failed")
        sb.work(workspace, "verify-ready", "ready\n", f"{side}: repair verification")
        command("collect", slug, side)
        review("REVIEW-INTEGRATION", "integration", "changes-required")
        command("dispatch", slug, final, code=1)
        command("next", slug)
        command("finish", slug, code=3)
        command("finish", slug, "--with-open", code=3)

        fix = "SAE-INTEGRATION-REPAIR-ONE"
        command("job", "add", slug, fix, "--kind", "implementation", "--fix-of", "REVIEW-INTEGRATION",
                "--reason", "repair the integration findings")
        sb.job_file(task, fix)
        command("dispatch", slug, fix)
        sb.work(sb.task_worktree(task).parent / fix, "fix.txt", "fix\n", f"{fix}: work")
        result(fix)
        command("collect", slug, fix)
        review("REVIEW-INTEGRATION-2", "integration", "pass")
        command("dispatch", slug, final)
        result(final)
        command("collect", slug, final)

        command("job", "add", slug, late, "--kind", "implementation", "--review", "--reason", "late work")
        sb.job_file(task, late)
        command("dispatch", slug, late)
        workspace = sb.task_worktree(task).parent / late
        sb.work(workspace, "late.txt", "late\n", f"{late}: work")
        (workspace / "notes.txt").write_text("notes to keep\n")
        result(late)
        command("collect", slug, late)
        review(f"REVIEW-{late}", late, "pass")
        self.assertEqual(sb.state(task)["jobs"][final]["status"], "pending")
        command("finish", slug, code=3)
        command("doctor")
        review("REVIEW-INTEGRATION-3", "integration", "pass")
        command("dispatch", slug, final)
        result(final)
        command("collect", slug, final)
        command("log", slug, "decision", "Keep the accepted result for the owner to review.",
                "--class", "clear-choice", "--by", "agent")
        command("finding", "new", "Output needs a regression guard", "--type", "defect", "--confidence", "high",
                "--source", f"{task}/{core}", "--body", "Observed only in this throwaway repository.")
        finding = next((sb.task_worktree(task) / ".tasks" / "findings").glob("*.md"))
        command("finding", "close", str(finding), "--outcome", "rejected: " + "expected behavior " * 8)
        command("adr", "new", slug, "Keep status lookups local to this task", "--type", "business")
        draft = next((sb.task_worktree(task) / ".tasks" / "adr").glob("*.md"))
        command("adr", "reject", str(draft), "--reason", "Visible in the implementation " * 6)
        command("adr", "new", slug, "Accept status lookups local to this task", "--type", "business")
        draft = next(p for p in (sb.task_worktree(task) / ".tasks" / "adr").glob("*.md") if p.name != "closed.md")
        command("adr", "accept", str(draft))
        command("triage")
        command("finish", slug)
        self.assertEqual(sb.state(task)["task"]["phase"], "done")
        command("doctor")
        command("status", slug)
        # Each path below has its own task; all state remains in this sandbox.
        command("new", "Output backlog pickup", "--backlog", "--slug", "owner-output-width-backlog-item-with-long-id")
        backlog_path = next((sb.repo / ".tasks" / "backlog").glob("*.md"))
        sb.git("add", str(backlog_path))
        sb.git("commit", "-q", "-m", "Keep backlog item for pickup")
        command("new", "Output backlog task", "--from", str(backlog_path), "--slug", "owner-output-width-backlog-task-with-long-id",
                mode="new: backlog pickup")
        backlog_task = re.search(r"^Task: (.+)$", captures[-1][1], re.M).group(1)
        parked = "SAE-PARKED-DECISION-WRITER"
        command("job", "add", backlog_task, parked, "--kind", "implementation")
        sb.job_file(backlog_task, parked)
        command("approve", backlog_task, "spec")
        command("approve", backlog_task, "plan")
        command("start", backlog_task, mode="start: backlog pickup")
        command("dispatch", backlog_task, parked)
        sb.result(backlog_task, f"jobs/{parked}.result.md", status="parked", summary="Owner decision required.",
                  validation="not-run", changes="none")
        command("collect", backlog_task, parked)
        command("decision", "new", backlog_task, "--from", parked)
        decision = f"DECISION-{parked}-1"
        command("dispatch", backlog_task, decision)
        sb.result(backlog_task, f"decisions/{decision}.md", status="done", summary="Decision recorded.",
                  validation="pass", changes="none", **{"class": "routine", "recommendation": "agent-decides"})
        command("collect", backlog_task, decision)
        command("dispatch", backlog_task, parked, "--resume", "--reason", "decision recorded")
        (sb.task_worktree(backlog_task) / "half.txt").write_text("keep\n")
        sb.result(backlog_task, f"jobs/{parked}.result.md", status="failed", summary="Needs more work.",
                  validation="fail", changes="none")
        command("collect", backlog_task, parked)
        command("abandon", backlog_task, "--reason", "Owner stopped this task.", mode="abandon: dirty worktree")

        def planned(suffix, jobs, settings=()):
            created = command("new", "Owner output in " + suffix, "--slug", "owner-output-width-case-" + suffix)
            task_id = re.search(r"^Task: (.+)$", created.stdout, re.M).group(1)
            if settings:
                command("set", task_id, *settings)
            for job_id, kind in jobs:
                command("job", "add", task_id, job_id, "--kind", kind)
                sb.job_file(task_id, job_id)
            command("approve", task_id, "spec")
            command("approve", task_id, "plan")
            command("start", task_id)
            return task_id

        open_task = planned("open-items", [("SAE-OPEN-VALIDATION-CHECK", "validation")])
        command("finish", open_task, "--with-open", mode="finish: with open")
        failed = "SAE-REPEATED-VERIFY-FAILURE"
        verify_task = planned("verify-failure", [(failed, "validation")], ("max-verify-failures=2",))
        sb.job_file(verify_task, failed, verify=["test -f missing-verify-input"])
        command("dispatch", verify_task, failed)
        sb.result(verify_task, f"jobs/{failed}.result.md", status="done", summary="Ready.", validation="pass", changes="none")
        command("collect", verify_task, failed, code=5)
        command("dispatch", verify_task, failed, "--resume", "--reason", "verify-failed")
        command("collect", verify_task, failed, mode="verify: repeated failure")

        writer = "SAE-REVIEWED-WRITER-ROUND-TWO"
        review_task = planned("review-rounds", [(writer, "implementation")], ("review=integration",))
        command("dispatch", review_task, writer)
        sb.work(sb.task_worktree(review_task), "round-one.txt", "one\n", "round one")
        sb.result(review_task, f"jobs/{writer}.result.md", status="done", summary="Ready.", validation="pass", changes="made")
        command("collect", review_task, writer)
        command("dispatch", review_task, "REVIEW-INTEGRATION")
        sb.result(review_task, "reviews/REVIEW-INTEGRATION.md", target="integration", verdict="changes-required")
        command("collect", review_task, "REVIEW-INTEGRATION")
        fix = "SAE-REPAIR-REVIEW-ROUND-ONE"
        command("job", "add", review_task, fix, "--kind", "implementation", "--fix-of", "REVIEW-INTEGRATION",
                "--reason", "repair the first review")
        sb.job_file(review_task, fix)
        command("dispatch", review_task, fix)
        sb.work(sb.task_worktree(review_task), "round-two.txt", "two\n", "round two")
        sb.result(review_task, f"jobs/{fix}.result.md", status="done", summary="Ready.", validation="pass", changes="made")
        command("collect", review_task, fix)
        command("dispatch", review_task, "REVIEW-INTEGRATION-2")
        sb.result(review_task, "reviews/REVIEW-INTEGRATION-2.md", target="integration", verdict="changes-required")
        command("collect", review_task, "REVIEW-INTEGRATION-2", mode="review: second changes-required")
        command("next", review_task)
        command("finish", review_task, "--override", "Owner accepts the remaining review findings.", mode="finish: override")

        left, right = "SAE-CONFLICT-LEFT-WRITER", "SAE-CONFLICT-RIGHT-WRITER"
        conflict_task = planned("merge-conflict", [(left, "implementation"), (right, "implementation")])
        for job_id in (left, right):
            command("dispatch", conflict_task, job_id)
            sb.work(sb.task_worktree(conflict_task).parent / job_id, "app.txt", job_id + "\n", job_id)
            sb.result(conflict_task, f"jobs/{job_id}.result.md", status="done", summary="Ready.", validation="pass", changes="made")
        command("collect", conflict_task, left)
        command("collect", conflict_task, right, code=4, mode="merge: conflict")

        command("view", "--stop", mode="view: no server")
        blocked = self.tmp / "unwritable-viewer-state"
        blocked.mkdir(mode=0o500)
        sb.env["SAE_STATE_DIR"] = str(blocked)
        try:
            command("view", slug, code=1, mode="view: unwritable state")
        finally:
            blocked.chmod(0o700)
        sb.env["SAE_STATE_DIR"] = str(sb.viewer_state)
        try:
            command("view", slug, mode="view: start")
        finally:
            command("view", "--stop", mode="view: stop")

        self.assertEqual(commands - driven, set(), f"Text-mode commands missing: {commands - driven}")
        self.assertEqual(OUTPUT_MODES - modes, set(), f"Text-mode modes missing: {OUTPUT_MODES - modes}")
        violations = [f"{label}: {len(line)} columns: {line}"
                      for label, output in captures for line in wide_lines(output)]
        with self.subTest("width"):
            self.assertEqual(violations, [], "\n" + "\n".join(violations))
        for label, output in captures:
            with self.subTest(command=label):
                self.assertNotRegex(output, r"\bsae\s*\n\s*(?:" + "|".join({p[0] for p in commands}) + r")\b")
            for line in output.splitlines():
                if re.search(r"\bsae\s+(?:" + "|".join({p[0] for p in commands}) + r")\b", line):
                    with self.subTest(command=label, line=line):
                        self.assertTrue(line.lstrip().startswith("sae "), "Command must have its own line")
                        tokens = shlex.split(line.strip())[1:]
                        # Templates still parse as complete invocations after choosing a harness.
                        tokens = ["claude" if t == "claude|codex" else t for t in tokens]
                        parser.parse_args(tokens)
                if line.lstrip().startswith(("python3 ", "cd ")):
                    with self.subTest(command=label, line=line):
                        tokens = shlex.split(line)
                        index = tokens.index("python3")
                        self.assertEqual(Path(tokens[index + 1]).name, "sae.py")
                        parser.parse_args(tokens[index + 2:])
                if re.search(r'(?<!\S|/)["`]?/shape-and-execute\b', line):
                    with self.subTest(command=label, line=line):
                        self.assertEqual(line.strip(), "/shape-and-execute setup")
